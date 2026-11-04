"""Compose 3D frames + Meadowbop overlays (logo, title, karaoke) + audio into the final MP4.

python3 compose3d.py EPISODE.json OUTDIR --layout land|vert [--audio song.mp3]
"""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import cairo
import timeline
from render import Episode, FPS

ARG = sys.argv


def arg(n, d=None):
    return ARG[ARG.index(n) + 1] if n in ARG else d


def main():
    ep = json.load(open(ARG[1])); outdir = ARG[2]
    layout = arg("--layout", "land"); slug = ep["slug"]
    meta = os.path.join(outdir, f"{slug}_song_meta.json")
    audio = arg("--audio", os.path.join(outdir, f"{slug}_song.mp3"))
    full = timeline.full_song(ep, meta)
    song = full if layout == "land" else timeline.short_song(ep, full)
    if layout == "vert":
        a, b = song["_audio_window"]
        audio = timeline.cut_audio(audio, a, b, os.path.join(outdir, f"{slug}_short_cut.wav"))
    fdir = os.path.join(outdir, f"frames_{layout}")
    info = json.load(open(os.path.join(fdir, "info.json")))
    rfps, nfr = info["fps"], info["nframes"]
    E = Episode(ep, song, layout)
    W, H = E.L["W"], E.L["H"]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    out = os.path.join(outdir, f"{slug}_{'video' if layout == 'land' else 'short'}.mp4")
    n = int(E.dur * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", audio, "-af", "apad", "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    cache = {}
    beat = 60.0 / song["bpm"]
    for i in range(n):
        t = i / FPS
        k = min(int(t * rfps), nfr - 1)
        if k not in cache:
            cache.clear()
            p = os.path.join(fdir, f"f_{k:05d}.png")
            while not os.path.exists(p) and k > 0:
                k -= 1; p = os.path.join(fdir, f"f_{k:05d}.png")
            cache[k] = cairo.ImageSurface.create_from_png(p)
        img = next(iter(cache.values()))
        c.save(); c.scale(W / img.get_width(), H / img.get_height()); c.set_source_surface(img, 0, 0)
        c.get_source().set_filter(cairo.FILTER_GOOD); c.paint(); c.restore()
        b = t / beat
        s = E.section(min(b, song["total"] - 1e-3))
        E.logo(c, t)
        if s["kind"] == "intro":
            E.title_card(c, t, b - s["start"])
        elif s["kind"] == "outro":
            E.outro_card(c, t, b - s["start"])
        E.karaoke(c, t)
        if t < 0.5:
            c.set_source_rgba(0, 0, 0, 1 - t / 0.5); c.paint()
        if t > E.dur - 1.2:
            c.set_source_rgba(0, 0, 0, min(1, (t - (E.dur - 1.2)) / 1.2)); c.paint()
        surf.flush(); ff.stdin.write(bytes(surf.get_data()))
    ff.stdin.close(); ff.wait()
    print("done", out, round(E.dur, 1))


if __name__ == "__main__":
    main()
