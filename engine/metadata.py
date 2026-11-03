"""YouTube metadata (title, description, tags, hashtags) for the video and the Short.

Follows YouTube's own limits: title <= 100 chars, tags <= 500 chars total, <= 15 hashtags
(more than 15 makes YouTube ignore all of them), no misleading or unrelated keywords.
usage: python3 metadata.py EPISODE.json OUTDIR
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music

BASE_TAGS = ["kids songs", "nursery rhymes", "songs for kids", "toddler songs", "preschool songs",
             "children's songs", "sing along songs", "kids music", "baby songs", "Meadowbop",
             "learning songs for kids", "cartoon songs", "kindergarten songs", "family friendly"]
BASE_HASH = ["#KidsSongs", "#NurseryRhymes", "#Meadowbop"]
CAST_NAMES = {"lily": "Lily", "leo": "Leo", "grandpa": "Grandpa Bo", "daisy": "Daisy the Cow",
              "pip": "Pip the Duck", "rosie": "Rosie the Pig", "fluff": "Fluff the Sheep"}


def ts(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def chapters(ep, song):
    beat = 60.0 / song["bpm"]
    out = [("0:00", "Intro")]
    vcount = 0
    for s in song["sections"]:
        if s["kind"] == "verse":
            vcount += 1
            label = s.get("chapter") or s["lines"][0].rstrip(",.!?")
            out.append((ts(s["start"] * beat), label))
        elif s["kind"] == "chorus" and vcount == 1 and not any(c[1] == "Chorus" for c in out):
            out.append((ts(s["start"] * beat), "Chorus: " + s["lines"][0].rstrip(",.!?")))
    return out


def build(ep):
    seo = ep.get("seo", {})
    kw = seo.get("keywords", [])
    title = ep["title"]
    sub = ep.get("subtitle", "Song for Kids")
    emoji = seo.get("emoji", "")
    vt = f"{title} {emoji} {sub} | Meadowbop Kids Songs".replace("  ", " ")
    if len(vt) > 100:
        vt = f"{title} {emoji} {sub}".replace("  ", " ")[:100]
    st = f"{title} {emoji} #shorts #kidssongs".replace("  ", " ")[:100]
    song = music.build_song(ep)
    chap = chapters(ep, song)
    cast = sorted({c for s in ep["sections"] for c in (s.get("cast") or ep["cast"])}, key=list(CAST_NAMES).index)
    names = ", ".join(CAST_NAMES[c] for c in cast)
    lyrics, seen = [], set()
    for s in ep["sections"]:
        block = "\n".join(s["lines"])
        if s["type"] == "chorus" and block in seen:
            lyrics.append("[Chorus]")
            continue
        seen.add(block)
        lyrics.append(("[Chorus]\n" if s["type"] == "chorus" else "") + block)
    hashtags = (seo.get("hashtags", []) + BASE_HASH)[:3]
    extra_hash = [h for h in seo.get("hashtags", [])[3:] + ["#SingAlong", "#ToddlerSongs", "#PreschoolSongs",
                                                             "#KidsMusic", "#LearningSongs"]][:8]
    hook = seo.get('hook', title + ' Sing along with ' + names + '!')
    summary = seo.get('summary', 'A happy, original sing-along song about ' + ep.get('theme', "a child's day") + '.')
    desc = f"""{hook}

{summary} Follow the bouncing ball and sing every word with {names}. Perfect for toddlers, preschoolers and kindergarten kids (ages 2-6) learning daily routines and English words.

⏱️ Chapters
""" + "\n".join(f"{a} {b}" for a, b in chap) + f"""

🎵 Lyrics
""" + "\n\n".join(lyrics) + f"""

🌼 About Meadowbop
Meadowbop makes brand-new, original sing-along songs about a kid's everyday life: waking up, brushing teeth, eating breakfast, going to school, playing, bath time and bedtime. Every song is family friendly, easy to sing, and made to help little ones learn routines, words and good habits with music.

New songs every day. Original music and lyrics © Meadowbop. Animated with computer tools.

{' '.join(hashtags + extra_hash)}"""
    tags, total = [], 0
    for t in kw + BASE_TAGS + [title.lower().rstrip("!"), sub.lower()]:
        t = t.strip()
        if t and t.lower() not in [x.lower() for x in tags] and total + len(t) + 2 <= 480:
            tags.append(t); total += len(t) + 2
    short_desc = f"""{title} {emoji} Sing along with {names}! Full song on the Meadowbop channel.

{chr(10).join(ep['sections'][next(i for i, s in enumerate(ep['sections']) if s['type'] == 'chorus')]['lines'])}

#shorts {' '.join(hashtags)} #SingAlong #ToddlerSongs"""
    return dict(video=dict(title=vt, description=desc, tags=tags, category="EDUCATION", madeForKids=True),
                short=dict(title=st, description=short_desc, tags=tags[:15], category="EDUCATION", madeForKids=True))


if __name__ == "__main__":
    ep = json.load(open(sys.argv[1]))
    md = build(ep)
    os.makedirs(sys.argv[2], exist_ok=True)
    p = os.path.join(sys.argv[2], f"{ep['slug']}_metadata.json")
    json.dump(md, open(p, "w"), indent=2, ensure_ascii=False)
    print(md["video"]["title"]); print(len(md["video"]["title"]), "chars;", sum(len(t) for t in md["video"]["tags"]), "tag chars")
