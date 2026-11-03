"""Turn an episode's lyrics into an original song: rhythm from syllables, seeded melody, chords,
arrangement, and FluidSynth audio. Every episode gets its own melody (seeded) and its own key/tempo."""
import math, random, re
import numpy as np

SR = 44100
SF2 = "/usr/share/sounds/sf2/TimGM6mb.sf2"
MAJOR = [0, 2, 4, 5, 7, 9, 11]
ROOTS ={"C": 60, "D": 62, "Eb": 63, "E": 64, "F": 65, "G": 55, "A": 57, "Bb": 58}

PALETTES = {
    "bouncy": dict(lead=[73, 12, 79, 71, 13], bell=[9, 10, 11], chord=[24, 0, 21, 4], bass=[32, 33, 58], drums=True),
    "gentle": dict(lead=[10, 11, 73, 74], bell=[9, 10], chord=[0, 46, 24], bass=[32], drums=False),
    "march": dict(lead=[56, 71, 73], bell=[9, 13], chord=[21, 0], bass=[58, 33], drums=True),
}

VERSE_CHORDS = [[1, 5], [6, 4], [1, 5], [4, 1]]
CHORUS_CHORDS = [[4, 5], [1, 6], [4, 5], [1, 1]]
TRIAD = {1: [0, 2, 4], 4: [3, 5, 0], 5: [4, 6, 1], 6: [5, 0, 2], 2: [1, 3, 5]}


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    if w.endswith(("ed",)) and not w.endswith(("ted", "ded")) and n > 1:
        n -= 1
    return max(1, n)


def split_line(line):
    """-> list of words, each word = (display_text, n_syllables)."""
    words = line.split()
    return [(w, syllables(w)) for w in words if syllables(w) > 0] or [(line, 1)]


def rhythm(n, rng, variant):
    """Durations (beats) for n syllables within an 8-beat (2-bar) line."""
    if n <= 3:
        d = [2.0] * (n - 1) + [8 - 2.0 * (n - 1) - 1]
    elif n <= 6:
        d = [1.0] * (n - 1); d.append(max(1.0, 7 - sum(d)))
        if variant % 2 and n <= 5:  # long-short feel
            d[0] = 1.5; d[1] = 0.5
    elif n <= 13:
        k = n - 1
        d = [0.5] * k
        extra = 7 - 0.5 * k - 1.5
        i = 1
        while extra >= 0.5 and i < k:  # stretch strong syllables
            d[i] += 0.5; extra -= 0.5; i += 2
        d.append(1.5)
    else:
        d = [0.5] * (n - 1) + [1.0]
    return d


def degree_to_midi(deg, root):
    o, k = divmod(deg, 7)
    return root + 12 * o + MAJOR[k]


def contour(u, kind, rng):
    if kind == "rise":
        return 0 + 4 * u
    if kind == "arch":
        return 2 + 3 * math.sin(math.pi * u)
    if kind == "fall":
        return 4 - 4 * u
    if kind == "hook":
        return 4 + 1.5 * math.sin(2 * math.pi * u)
    return 2


def line_melody(n_syl, durs, line_idx, section_type, seed, chords):
    rng = random.Random(f"{seed}-{section_type}-{line_idx}")
    kinds = {"verse": ["rise", "arch", "rise", "fall"], "chorus": ["hook", "arch", "hook", "fall"]}
    kind = kinds.get(section_type, kinds["verse"])[line_idx % 4]
    endings = {"verse": [4, 1, 4, 0], "chorus": [4, 4, 4, 0]}
    end = endings.get(section_type, endings["verse"])[line_idx % 4]
    shift = 2 if section_type == "chorus" else 0
    out, beat, prev = [], 0.0, None
    for k in range(n_syl):
        u = k / max(1, n_syl - 1)
        target = contour(u, kind, rng) + shift + rng.choice([0, 0, 1, -1])
        bar = 0 if beat < 4 else 1
        chord = chords[bar]
        if beat % 2 == 0:  # strong beat -> nearest chord tone
            tones = [t + 7 * o for t in TRIAD[chord] for o in (-1, 0, 1)]
            target = min(tones, key=lambda x: abs(x - target))
        d = int(round(target))
        if prev is not None and abs(d - prev) > 4:
            d = prev + (4 if d > prev else -4)
        if k == n_syl - 1:
            d = end + (7 if section_type == "chorus" and end == 0 and line_idx % 4 != 3 else 0)
        out.append(d); prev = d; beat += durs[k]
    return out


def build_song(ep, section_ids=None, intro_beats=16, outro_beats=8):
    """Return timeline dict with notes (lyrics), chords, sections (beat ranges)."""
    seed = ep.get("seed", 1)
    root = ROOTS.get(ep.get("key", "C"), 60)
    secs = ep["sections"]
    order = section_ids if section_ids is not None else list(range(len(secs)))
    notes, chords, sections = [], [], []
    rng = random.Random(seed)
    # intro uses chorus melody instrumentally
    chorus = next((s for s in secs if s["type"] == "chorus"), secs[0])
    pos = 0.0
    sections.append(dict(kind="intro", start=0, end=intro_beats, scene=ep.get("intro_scene", secs[0].get("scene", "meadow"))))
    for li in range(intro_beats // 8):
        line = chorus["lines"][li % len(chorus["lines"])]
        syl = sum(n for _, n in split_line(line))
        durs = rhythm(syl, rng, li)
        prog = CHORUS_CHORDS[li % 4]
        mel = line_melody(syl, durs, li, "chorus", seed, prog)
        b = pos + li * 8
        for d, deg in zip(durs, mel):
            notes.append(dict(beat=b, dur=d, pitch=degree_to_midi(deg, root), text="", kind="inst"))
            b += d
        for bar in range(2):
            chords.append((pos + li * 8 + bar * 4, prog[bar]))
    pos += intro_beats
    for si in order:
        s = secs[si]
        stype = s["type"]
        progs = CHORUS_CHORDS if stype == "chorus" else VERSE_CHORDS
        start = pos
        for li, line in enumerate(s["lines"]):
            words = split_line(line)
            syl = sum(n for _, n in words)
            durs = rhythm(syl, random.Random(f"{seed}-{stype}-r{li}"), li)
            prog = progs[li % 4]
            mel = line_melody(syl, durs, li, stype, seed, prog)
            b = pos
            k = 0
            for wi, (w, n) in enumerate(words):
                for j in range(n):
                    notes.append(dict(beat=b, dur=durs[k], pitch=degree_to_midi(mel[k], root),
                                      text=w if j == 0 else "", word=wi, syl=j, nsyl=n,
                                      line=len(sections), li=li, kind="lyric", singer=s.get("singer")))
                    b += durs[k]; k += 1
            for bar in range(2):
                chords.append((pos + bar * 4, prog[bar]))
            pos += 8
        sections.append(dict(kind=stype, start=start, end=pos, idx=si, **{k: v for k, v in s.items() if k != "type"}))
    for bar in range(outro_beats // 4):
        chords.append((pos + bar * 4, 1))
    sections.append(dict(kind="outro", start=pos, end=pos + outro_beats, scene=ep.get("outro_scene", secs[-1].get("scene"))))
    pos += outro_beats
    return dict(notes=notes, chords=chords, sections=sections, total=pos, root=root, bpm=ep.get("bpm", 112))


def render_audio(song, ep, path):
    import fluidsynth
    from scipy.io import wavfile
    beat = 60.0 / song["bpm"]
    rng = random.Random(ep.get("seed", 1) * 7)
    pal = PALETTES.get(ep.get("mood", "bouncy"), PALETTES["bouncy"])
    lead, bell = rng.choice(pal["lead"]), rng.choice(pal["bell"])
    chordp, bassp = rng.choice(pal["chord"]), rng.choice(pal["bass"])
    fs = fluidsynth.Synth(samplerate=float(SR), gain=0.6)
    sf = fs.sfload(SF2)
    for ch, prog in ((0, lead), (1, bell), (2, chordp), (3, bassp)):
        fs.program_select(ch, sf, 0, prog)
    fs.program_select(9, sf, 128, 0)
    msgs = []

    def note(t, d, ch, n, v):
        msgs.append((t, 1, ch, n, v)); msgs.append((t + d, 0, ch, n, 0))

    root = song["root"]
    for n in song["notes"]:
        t, d = n["beat"] * beat, n["dur"] * beat * 0.9
        note(t, d, 0, n["pitch"], 108 if n["kind"] == "lyric" else 92)
        note(t, d, 1, n["pitch"] + 12, 45)
    for b, deg in song["chords"]:
        t = b * beat
        tones = [degree_to_midi(TRIAD[deg][i] - 7, root) for i in range(3)]
        style = rng.random() if False else (b // 4) % 2
        if pal["drums"]:
            for k in range(4):  # oom-pah: bass on 1/3, chord on 2/4
                if k % 2 == 0:
                    note(t + k * beat, beat * 0.9, 3, degree_to_midi(TRIAD[deg][0] - 14, root) + (7 if k == 2 else 0), 92)
                else:
                    for i, tn in enumerate(tones):
                        note(t + k * beat + i * 0.01, beat * 0.7, 2, tn, 62)
        else:
            for i, tn in enumerate(tones):  # gentle arpeggio
                for k in range(4):
                    note(t + k * beat + i * beat / 3, beat * 1.5, 2, tones[(k + i) % 3] + 12 * (k == 3), 50)
            note(t, beat * 3.8, 3, degree_to_midi(TRIAD[deg][0] - 14, root), 70)
    if pal["drums"]:
        lyric_start = song["sections"][1]["start"] if len(song["sections"]) > 1 else 0
        for i in range(int(song["total"])):
            t = i * beat
            note(t, 0.1, 9, 36 if i % 2 == 0 else 38, 75 if i % 2 == 0 else 52)
            note(t, 0.05, 9, 42, 38); note(t + beat / 2, 0.05, 9, 42, 26)
            if i % 16 == 0:
                note(t, 1.0, 9, 49, 55)
        for s in song["sections"]:
            if s["kind"] == "chorus":
                for k in range(int(s["end"] - s["start"])):
                    note((s["start"] + k + 0.5) * beat, 0.05, 9, 39 if k % 2 else 42, 50 if k % 2 else 0)
    msgs.sort(key=lambda m: (m[0], m[1]))
    out, cur = [], 0
    for t, on, ch, n, v in msgs:
        tgt = int(max(t, 0) * SR)
        if tgt > cur:
            out.append(fs.get_samples(tgt - cur)); cur = tgt
        fs.noteon(ch, n, v) if on else fs.noteoff(ch, n)
    end = song["total"] * beat
    out.append(fs.get_samples(max(0, int((end + 2.0) * SR) - cur)))
    fs.delete()
    pcm = np.concatenate(out).astype(np.float32).reshape(-1, 2)
    pcm *= 29000 / max(1.0, np.abs(pcm).max())
    fade = int(1.5 * SR); pcm[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(path, SR, pcm.astype(np.int16))
    return len(pcm) / SR, dict(lead=lead, bell=bell, chord=chordp, bass=bassp)
