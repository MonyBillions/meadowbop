"""ElevenLabs Music: sung vocals + arrangement for an episode, aligned to our section timeline.

We send a composition plan whose section durations match our beat timeline (music_v2+ enforces
section durations), so scenes/karaoke stay in sync. If word timestamps come back, lyrics are re-timed
to the real singing.

Auth: preferably a cloud-environment "Network secret" for host api.elevenlabs.io with custom header
`xi-api-key` (no prefix) — the agent proxy injects the key, sessions never see it.
Fallback: env ELEVENLABS_API_KEY (local runs only).
"""
import base64, email, json, os, re, sys
from email.policy import default as email_policy
import urllib.request, urllib.error

API = "https://api.elevenlabs.io/v1/music/detailed"
MODEL = os.environ.get("MEADOWBOP_MUSIC_MODEL", "music_v2_5")

VOICE_STYLE = {
    "lily": "solo cheerful little girl voice, sweet and bright, clear diction",
    "leo": "solo playful young boy voice, bright and friendly, clear diction",
    "grandpa": "warm friendly grandpa voice singing gently",
    "daisy": "sweet warm cartoon voice, gentle",
    "pip": "high playful cartoon kid voice, bouncy",
    "rosie": "giggly cheerful cartoon kid voice",
    "fluff": "soft gentle kid voice",
}
MOOD_STYLE = {
    "bouncy": ["upbeat", "ukulele", "glockenspiel", "hand claps", "bouncy bass", "light drums"],
    "gentle": ["lullaby", "soft piano", "music box", "warm strings", "calm"],
    "march": ["marching band feel", "snare drum", "tuba", "whistle", "cheerful"],
}


def plan_for(ep, song):
    beat = 60.0 / song["bpm"]
    mood = ep.get("mood", "bouncy")
    g = ["children's song", "preschool sing-along", "kids pop", "nursery rhyme style",
         "bright cheerful child-like vocals", "clear simple English lyrics", "catchy melody",
         f"{song['bpm']} bpm", f"key of {ep.get('key', 'C')} major"] + MOOD_STYLE.get(mood, MOOD_STYLE["bouncy"])
    neg = ["adult deep vocals", "rap", "autotune", "distortion", "heavy rock", "explicit", "sad", "dark", "spoken word"]
    secs = []
    for s in song["sections"]:
        dur = int(round((s["end"] - s["start"]) * beat * 1000))
        if s["kind"] == "intro":
            secs.append(dict(section_name="Intro", positive_local_styles=["instrumental", "playful intro", "no vocals"],
                             negative_local_styles=["vocals"], duration_ms=dur, lines=[]))
        elif s["kind"] == "outro":
            secs.append(dict(section_name="Outro", positive_local_styles=["happy ending", "short instrumental tag"],
                             negative_local_styles=["vocals"], duration_ms=dur, lines=[]))
        elif s["kind"] == "chorus":
            secs.append(dict(section_name="Chorus", positive_local_styles=[
                "kids choir singing together", "big happy hook", "everyone sings", "claps on 2 and 4"],
                negative_local_styles=["solo adult"], duration_ms=dur, lines=s["lines"]))
        else:
            who = s.get("singer", "lily")
            secs.append(dict(section_name="Verse", positive_local_styles=[VOICE_STYLE.get(who, VOICE_STYLE["lily"]),
                                                                          "storytelling verse"],
                             negative_local_styles=["choir"], duration_ms=dur, lines=s["lines"]))
    return dict(positive_global_styles=g, negative_global_styles=neg, sections=secs)


def _parse(body, ctype):
    """Return (audio_bytes, meta_json) from multipart/mixed or JSON."""
    if ctype.startswith("multipart"):
        msg = email.message_from_bytes(b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body, policy=email_policy)
        audio, meta = None, {}
        for part in msg.iter_parts():
            ct = part.get_content_type()
            data = part.get_payload(decode=True)
            if ct == "application/json":
                meta = json.loads(data)
            elif ct.startswith("audio") or ct == "application/octet-stream":
                audio = data
        return audio, meta
    if ctype.startswith("application/json"):
        j = json.loads(body)
        a = j.pop("audio", None) or j.pop("audio_base64", None)
        return (base64.b64decode(a) if isinstance(a, str) else None), j
    return body, {}


def compose(ep, song, out_path, key=None):
    key = key or os.environ.get("ELEVENLABS_API_KEY")
    plan = plan_for(ep, song)
    payload = dict(composition_plan=plan, model_id=MODEL, with_timestamps=True,
                   seed=int(ep.get("seed", 1)) % 2147483647)
    req = urllib.request.Request(API + "?output_format=mp3_44100_192", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **({"xi-api-key": key} if key else {})}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=900)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ElevenLabs HTTP {e.code}: {e.read()[:800].decode('utf-8', 'replace')}")
    with r:
        body, ctype = r.read(), r.headers.get("Content-Type", "")
        song_id = r.headers.get("song-id")
    audio, meta = _parse(body, ctype)
    if not audio:
        raise RuntimeError(f"no audio in response ({ctype}, {len(body)} bytes)")
    open(out_path, "wb").write(audio)
    meta["song_id"] = song_id
    meta["plan_sent"] = plan
    json.dump(meta, open(os.path.splitext(out_path)[0] + "_meta.json", "w"), indent=2)
    return meta


def _norm(w):
    return re.sub(r"[^a-z']", "", w.lower())


def find_words(meta):
    """Best-effort: locate a list of {word,start,end} (seconds) anywhere in the metadata."""
    best = []

    def walk(x):
        nonlocal best
        if isinstance(x, list) and x and isinstance(x[0], dict):
            keys = set(x[0])
            wk = next((k for k in ("word", "text", "token") if k in keys), None)
            sk = next((k for k in ("start", "start_s", "start_time", "start_ms") if k in keys), None)
            ek = next((k for k in ("end", "end_s", "end_time", "end_ms") if k in keys), None)
            if wk and sk and len(x) > len(best):
                scale = 1000.0 if sk.endswith("ms") else 1.0
                best = [dict(word=d[wk], start=d[sk] / scale, end=(d.get(ek, d[sk]) if ek else d[sk]) / scale) for d in x]
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(meta)
    return best


def retime(song, meta):
    """Move our lyric notes onto the sung word timestamps (sequential greedy match)."""
    words = find_words(meta)
    if not words:
        return 0
    beat = 60.0 / song["bpm"]
    groups = {}
    for n in song["notes"]:
        if n["kind"] == "lyric":
            groups.setdefault((n["line"], n["li"], n["word"]), []).append(n)
    order = sorted(groups, key=lambda k: groups[k][0]["beat"])
    j, matched = 0, 0
    for k in order:
        ns = groups[k]
        target = _norm(ns[0]["text"])
        for look in range(j, min(j + 6, len(words))):
            if _norm(words[look]["word"]) == target:
                w = words[look]
                st, en = w["start"] / beat, max(w["end"], w["start"] + 0.12) / beat
                step = (en - st) / len(ns)
                for i, n in enumerate(ns):
                    n["beat"] = st + i * step; n["dur"] = step
                j = look + 1; matched += 1
                break
    return matched


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import music
    ep = json.load(open(sys.argv[1]))
    print(json.dumps(plan_for(ep, music.build_song(ep)), indent=1)[:1500])
