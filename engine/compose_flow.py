"""Assemble AI-generated scene clips (Google Flow / Veo / Omni) with the ElevenLabs song + Meadowbop overlays.

plan JSON: {"episode": "...json", "song_mp3": "...", "meta": "..._song_meta.json",
            "shots": [{"clip": "clip1.mp4", "section": 1, "line": 0, "lines": 2}, ...],
            "outro_seconds": 2.0}
Each shot covers `lines` lyric lines (8 beats each) of song section `section` (index in the full song's
section list) starting at `line`; the clip is time-stretched to fit exactly.
usage: python3 compose_flow.py PLAN.json OUT_BASENAME [land|vert|both]
"""
import json, math, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cairo
import timeline
from render import Episode, FPS


def run(*a):
    subprocess.run(list(a), check=True)


def build(plan, out_base, layouts):
    ep = json.load(open(plan["episode"]))
    full = timeline.full_song(ep, plan.get("meta"))
    beat = 60.0 / full["bpm"]
    secs = full["sections"]
    tmp = tempfile.mkdtemp()
    # --- timeline of shots
    notes, cur, segs, sections = [], 0.0, [], []
    for i, sh in enumerate(plan["shots"]):
        s = secs[sh["section"]]
        b0 = s["start"] + 8 * sh["line"]; nb = 8 * sh["lines"]
        segs.append((b0 * beat, nb * beat))
        for n in full["notes"]:
            if n["kind"] == "lyric" and b0 <= n["beat"] < b0 + nb:
                m = dict(n); m["beat"] = n["beat"] - b0 + cur; m["line"] = 100 + i; notes.append(m)
        sections.append(dict(kind=s["kind"], start=cur, end=cur + nb, scene=s.get("scene")))
        cur += nb
    outro_b = plan.get("outro_seconds", 2.0) / beat
    sections.append(dict(kind="outro", start=cur, end=cur + outro_b))
    song = dict(notes=notes, sections=sections, total=cur + outro_b, bpm=full["bpm"], chords=[], root=full["root"])
    # --- audio: concatenate song segments (tiny crossfades), fade the tail
    parts = []
    for k, (a, d) in enumerate(segs):
        p = os.path.join(tmp, f"a{k}.wav"); parts.append(p)
        run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-t", f"{d + (plan.get('outro_seconds', 2.0) if k == len(segs) - 1 else 0):.3f}",
            "-i", plan["song_mp3"], "-ar", "44100", "-ac", "2", p)
    audio = os.path.join(tmp, "audio.wav")
    if len(parts) == 1:
        os.replace(parts[0], audio)
    else:
        inputs = sum([["-i", p] for p in parts], [])
        chain, last = [], "[0:a]"
        for k in range(1, len(parts)):
            out = f"[x{k}]"
            chain.append(f"{last}[{k}:a]acrossfade=d=0.04:c1=tri:c2=tri{out}"); last = out
        run("ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain), "-map", last, audio)
    total_s = song["total"] * beat
    fadeaud = os.path.join(tmp, "audio_f.wav")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", audio, "-af", f"afade=t=out:st={max(0, total_s - 1.5):.3f}:d=1.5", fadeaud)
    # --- base video: each clip stretched to its slot, last frame held for the outro
    vparts = []
    for k, sh in enumerate(plan["shots"]):
        d = segs[k][1] + (plan.get("outro_seconds", 2.0) if k == len(segs) - 1 else 0)
        clipd = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", sh["clip"]]))
        f = segs[k][1] / clipd
        p = os.path.join(tmp, f"v{k}.mp4"); vparts.append(p)
        vf = f"setpts={f:.5f}*PTS,fps={FPS},scale=1280:720,tpad=stop_mode=clone:stop_duration={d:.3f}"
        run("ffmpeg", "-y", "-loglevel", "error", "-i", sh["clip"], "-an", "-vf", vf, "-t", f"{d:.3f}", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "16", p)
    lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in vparts))
    base = os.path.join(tmp, "base.mp4")
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base)
    outs = []
    for layout in layouts:
        E = Episode(ep, song, layout)
        W, H = E.L["W"], E.L["H"]
        out = f"{out_base}_{layout}.mp4"
        dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", base, "-f", "rawvideo", "-pix_fmt", "bgra",
                                "-s", "1280x720", "-r", str(FPS), "-"], stdout=subprocess.PIPE)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-i", fadeaud, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                               stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
        n = int(total_s * FPS)
        fsz = 1280 * 720 * 4
        for i in range(n):
            buf = dec.stdout.read(fsz)
            if len(buf) < fsz:
                break
            img = cairo.ImageSurface.create_for_data(bytearray(buf), cairo.FORMAT_ARGB32, 1280, 720)
            t = i / FPS
            if layout == "land":
                c.set_source_surface(img, 0, 0); c.paint()
            else:
                # blurred, zoomed background + full frame in the middle
                c.save(); sc = H / 720 * 1.02; c.translate(W / 2, H / 2); c.scale(sc, sc); c.translate(-640, -360)
                c.set_source_surface(img, 0, 0); c.get_source().set_filter(cairo.FILTER_FAST); c.paint(); c.restore()
                c.set_source_rgba(0.12, 0.08, 0.2, 0.55); c.paint()
                c.save(); s2 = W / 1280; y = (H - 720 * s2) / 2 - 40; c.translate(0, y); c.scale(s2, s2)
                c.set_source_surface(img, 0, 0); c.get_source().set_filter(cairo.FILTER_GOOD); c.paint(); c.restore()
            b = t / beat
            s = E.section(min(b, song["total"] - 1e-3))
            E.logo(c, t)
            if s["kind"] == "outro":
                E.outro_card(c, t, b - s["start"])
            elif layout == "vert" and t < 3.0:
                E.title_card(c, t, b + 8)
            E.karaoke(c, t)
            if t < 0.4:
                c.set_source_rgba(0, 0, 0, 1 - t / 0.4); c.paint()
            if t > total_s - 0.8:
                c.set_source_rgba(0, 0, 0, min(1, (t - (total_s - 0.8)) / 0.8)); c.paint()
            surf.flush(); enc.stdin.write(bytes(surf.get_data()))
        dec.stdout.close(); dec.wait(); enc.stdin.close(); enc.wait()
        outs.append(out)
    return outs


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1]))
    lay = sys.argv[3] if len(sys.argv) > 3 else "both"
    print(build(plan, sys.argv[2], ["land", "vert"] if lay == "both" else [lay]))
