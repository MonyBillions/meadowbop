"""Shared song timeline helpers (2D and 3D pipelines)."""
import json, os, subprocess
import music


def full_song(ep, meta_path=None):
    song = music.build_song(ep)
    if meta_path and os.path.exists(meta_path):
        import eleven
        eleven.retime(song, json.load(open(meta_path)))
    return song


def short_song(ep, full):
    """Verse 1 + chorus 1, re-timed from the full (sung) song."""
    vi = next(i for i, s in enumerate(ep["sections"]) if s["type"] == "verse")
    ci = next(i for i, s in enumerate(ep["sections"]) if s["type"] == "chorus")
    short = music.build_song(ep, [vi, ci], intro_beats=8, outro_beats=4)
    v1 = next(s for s in full["sections"] if s["kind"] == "verse")
    c1 = next(s for s in full["sections"] if s["kind"] == "chorus")
    shift = v1["start"] - 8
    fl = [n for n in full["notes"] if n["kind"] == "lyric" and n["line"] in (full["sections"].index(v1), full["sections"].index(c1))]
    for a, b in zip([n for n in short["notes"] if n["kind"] == "lyric"], fl):
        a["beat"] = b["beat"] - shift; a["dur"] = b["dur"]
    beat = 60.0 / full["bpm"]
    short["_audio_window"] = ((v1["start"] - 8) * beat, (c1["end"] + 4) * beat)
    return short


def cut_audio(src, start, end, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", src,
                    "-af", f"afade=t=out:st={end - start - 2.0:.3f}:d=2", "-ar", "44100", out], check=True)
    return out
