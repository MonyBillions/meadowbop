"""Long-form episode composer: full ElevenLabs song + word timestamps (Scribe) + AI scene clips.

plan JSON:
{"episode": "...json", "song": "song.mp3", "words": "words.json", "lines": [[...lyric lines in order...]],
 "title_until": 7.5, "outro_from": 173.5,
 "shots": [{"start": 0, "end": 8, "clip": "a.mp4", "mirror": false, "zoom": 1.0, "offset": 0}, ...]}
Clips are slowed (down to 0.6x) to fill their slot; if still short they ping-pong.
usage: python3 compose_long.py PLAN.json OUT.mp4 [land|vert] [t0 t1]
"""
import json, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cairo
from render import Episode, FPS


def run(*a):
    subprocess.run(list(a), check=True)


def norm(w):
    return re.sub(r"[^a-z']", "", w.lower())


def build_notes(words, lines):
    """Map transcript words onto the known lyric lines (keeps our spelling/punctuation)."""
    seq = [(li, wi, w) for li, line in enumerate(lines) for wi, w in enumerate(line.split())]
    tw = [w for w in words if w.get("type", "word") == "word"]
    notes, j = [], 0
    for li, wi, w in seq:
        k = j
        while k < len(tw) and k < j + 6 and norm(tw[k]["text"]) != norm(w):
            k += 1
        if k < len(tw) and norm(tw[k]["text"]) == norm(w):
            s, e = tw[k]["start"], tw[k]["end"]; j = k + 1
        else:  # not found: interpolate after previous word
            s = notes[-1]["beat"] + notes[-1]["dur"] + 0.05 if notes else 0; e = s + 0.3
        notes.append(dict(kind="lyric", beat=s, dur=max(0.18, e - s), text=w, word=wi, syl=0, nsyl=1,
                          line=li, li=0))
    return notes


def clip_dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", p]))


def render_shot(sh, out):
    d = sh["end"] - sh["start"]
    cd = clip_dur(sh["clip"]) - sh.get("offset", 0)
    speed = max(0.6, min(1.0, cd / d))
    z = sh.get("zoom", 1.0)
    f = [f"trim=start={sh.get('offset', 0)},setpts=PTS-STARTPTS"]
    if cd / speed < d:  # ping-pong to fill
        f.append("split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0")
    f.append(f"setpts={1 / speed:.4f}*PTS,fps={FPS},scale=1280:720")
    if z > 1.001:
        f.append(f"crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})/2.4,scale=1280:720")
    if sh.get("mirror"):
        f.append("hflip")
    f.append(f"tpad=stop_mode=clone:stop_duration={d}")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", sh["clip"], "-an", "-filter_complex", ",".join(f),
        "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", out)


def build(plan, out, layout="land", t0=None, t1=None):
    ep = json.load(open(plan["episode"]))
    words = json.load(open(plan["words"]))
    words = words.get("words", words)
    notes = build_notes(words, plan["lines"])
    total = plan.get("total", clip_dur(plan["song"]))
    song = dict(notes=notes, bpm=60, total=total, chords=[], root=0,
                sections=[dict(kind="intro", start=0, end=plan["title_until"]),
                          dict(kind="body", start=plan["title_until"], end=plan["outro_from"]),
                          dict(kind="outro", start=plan["outro_from"], end=total + 5)])
    tmp = tempfile.mkdtemp()
    parts = []
    for i, sh in enumerate(plan["shots"]):
        p = os.path.join(tmp, f"s{i:02d}.mp4"); render_shot(sh, p); parts.append(p)
    lst = os.path.join(tmp, "l.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    base = os.path.join(tmp, "base.mp4")
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base)
    t0 = t0 or 0.0; t1 = t1 or total
    E = Episode(ep, song, layout); W, H = E.L["W"], E.L["H"]
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t0}", "-i", base, "-f", "rawvideo",
                            "-pix_fmt", "bgra", "-s", "1280x720", "-r", str(FPS), "-"], stdout=subprocess.PIPE)
    af = f"afade=t=in:st=0:d=0.3,afade=t=out:st={max(0, t1 - t0 - 2.5):.2f}:d=2.5"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-ss", f"{t0}", "-t", f"{t1 - t0}",
                            "-i", plan["song"], "-af", af, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    fsz = 1280 * 720 * 4
    for i in range(int((t1 - t0) * FPS)):
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        img = cairo.ImageSurface.create_for_data(bytearray(buf), cairo.FORMAT_ARGB32, 1280, 720)
        t = t0 + i / FPS
        if layout == "land":
            c.set_source_surface(img, 0, 0); c.paint()
        else:
            c.save(); sc = H / 720 * 1.02; c.translate(W / 2, H / 2); c.scale(sc, sc); c.translate(-640, -360)
            c.set_source_surface(img, 0, 0); c.paint(); c.restore()
            c.set_source_rgba(0.12, 0.08, 0.2, 0.55); c.paint()
            c.save(); s2 = W / 1280; y = (H - 720 * s2) / 2 - 40; c.translate(0, y); c.scale(s2, s2)
            c.set_source_surface(img, 0, 0); c.paint(); c.restore()
        E.logo(c, t)
        if t < plan["title_until"] and (layout == "land" or t0 == 0):
            E.title_card(c, t, t + 0.5)
        elif layout == "vert" and t - t0 < 3:
            E.title_card(c, t, t - t0 + 0.5)
        if t >= plan["outro_from"]:
            E.outro_card(c, t, t - plan["outro_from"])
        E.karaoke(c, t)
        lt = t - t0
        if lt < 0.4:
            c.set_source_rgba(0, 0, 0, 1 - lt / 0.4); c.paint()
        if lt > (t1 - t0) - 1.0:
            c.set_source_rgba(0, 0, 0, min(1, (lt - (t1 - t0 - 1.0)))); c.paint()
        surf.flush(); enc.stdin.write(bytes(surf.get_data()))
    dec.stdout.close(); dec.wait(); enc.stdin.close(); enc.wait()
    return out


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1]))
    lay = sys.argv[3] if len(sys.argv) > 3 else "land"
    t0 = float(sys.argv[4]) if len(sys.argv) > 4 else None
    t1 = float(sys.argv[5]) if len(sys.argv) > 5 else None
    print(build(plan, sys.argv[2], lay, t0, t1))
