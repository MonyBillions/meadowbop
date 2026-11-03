"""Singing voice: Kokoro TTS (open-source, Apache-2.0) per word -> WORLD vocoder re-pitched to the
melody notes, re-timed to the rhythm, with vibrato, portamento and a per-character timbre.

Model files (downloaded from the kokoro-onnx GitHub releases) live in $MEADOWBOP_MODELS (default ~/models/kokoro).
"""
import os, re, math
import numpy as np
import pyworld as pw

SR = 24000
FP = 5.0  # WORLD frame period (ms)
MODELS = os.environ.get("MEADOWBOP_MODELS", os.path.expanduser("~/models/kokoro"))

# character -> (kokoro voice, formant warp >1 = younger/smaller, octave shift semitones, breathiness)
VOICES = {
    "lily": ("af_heart", 1.12, 0, 0.0),
    "leo": ("am_puck", 1.18, 0, 0.0),
    "grandpa": ("am_michael", 0.98, -12, 0.0),
    "daisy": ("af_bella", 1.02, 0, 0.0),
    "pip": ("af_sky", 1.22, 0, 0.0),
    "rosie": ("af_nicole", 1.14, 0, 0.0),
    "fluff": ("bf_emma", 1.10, 0, 0.0),
    "all": ("af_heart", 1.10, 0, 0.0),
}

_tts = None


def tts():
    global _tts
    if _tts is None:
        from kokoro_onnx import Kokoro
        _tts = Kokoro(os.path.join(MODELS, "kokoro-v1.0.int8.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    return _tts


_cache = {}


def say(word, voice):
    key = (word.lower(), voice)
    if key not in _cache:
        s, sr = tts().create(word, voice=voice, speed=1.0, lang="en-us")
        s = np.asarray(s, dtype=np.float64)
        # trim silence
        env = np.convolve(np.abs(s), np.ones(240) / 240, mode="same")
        idx = np.where(env > env.max() * 0.04)[0]
        if len(idx):
            s = s[max(0, idx[0] - 120): idx[-1] + 240]
        _cache[key] = s
    return _cache[key]


_ana = {}


def analyse(word, voice, x):
    key = (word.lower(), voice)
    if key not in _ana:
        f0, t = pw.dio(x, SR, f0_floor=70, f0_ceil=600, frame_period=FP)
        f0 = pw.stonemask(x, f0, t, SR)
        _ana[key] = (f0, t, pw.cheaptrick(x, f0, t, SR), pw.d4c(x, f0, t, SR))
    return _ana[key]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def warp_env(sp, alpha):
    """Formant shift: scale spectral envelope along frequency by alpha."""
    if abs(alpha - 1) < 1e-3:
        return sp
    n = sp.shape[1]
    src = np.clip(np.arange(n) / alpha, 0, n - 1)
    lo = np.floor(src).astype(int); hi = np.minimum(lo + 1, n - 1); fr = src - lo
    return sp[:, lo] * (1 - fr) + sp[:, hi] * fr


def sing_word(word, notes, beat, voice, alpha, shift, prev_hz):
    """notes: list of dicts with dur (beats) and pitch (midi) for each syllable of this word."""
    clean = re.sub(r"[^A-Za-z']", "", word) or word
    x = say(clean, voice)
    f0, t, sp, ap = analyse(clean, voice, x)
    nfr = len(f0)
    n = len(notes)
    # syllable boundaries in source frames: split voiced region evenly, keep onset consonant
    voiced = np.where(f0 > 0)[0]
    v0 = voiced[0] if len(voiced) else 0
    v1 = voiced[-1] + 1 if len(voiced) else nfr
    bounds = [0] + [int(v0 + (v1 - v0) * k / n) for k in range(1, n)] + [nfr]
    out_f0, out_sp, out_ap = [], [], []
    for k, nt in enumerate(notes):
        a, b = bounds[k], bounds[k + 1]
        a = min(a, nfr - 1); b = max(b, a + 1)
        tgt_frames = max(4, int(nt["dur"] * beat * 0.94 * 1000 / FP))
        src_len = b - a
        # keep consonant onset natural (first ~50ms unstretched), stretch the vowel part
        on = min(int(50 / FP), src_len // 3) if k == 0 else 0
        body_src = np.arange(a + on, b)
        body_n = max(1, tgt_frames - on)
        if len(body_src) == 0:
            body_src = np.array([b - 1])
        # stretch with the last 25% (vowel tail) held longest
        u = np.linspace(0, 1, body_n) ** 0.8
        idx = np.concatenate([np.arange(a, a + on), body_src[np.minimum((u * (len(body_src) - 1)).round().astype(int), len(body_src) - 1)]])
        idx = idx[:tgt_frames] if len(idx) > tgt_frames else idx
        hz = midi_hz(nt["pitch"] + shift)
        seg_f0 = np.zeros(len(idx))
        for j, i in enumerate(idx):
            if f0[i] > 0:
                tt = j * FP / 1000
                vib = 0.0 if tt < 0.22 else 0.28 * math.sin(2 * math.pi * 5.6 * tt) * min(1, (tt - 0.22) / 0.15)
                h = hz * 2 ** (vib / 12)
                if prev_hz and tt < 0.045:  # portamento from previous note
                    h = prev_hz * (h / prev_hz) ** (tt / 0.045)
                seg_f0[j] = h
        # fill tiny unvoiced gaps inside the vowel so sustained notes stay sung
        if (seg_f0 > 0).sum() > 3:
            first = np.argmax(seg_f0 > 0)
            seg_f0[first:] = np.where(seg_f0[first:] > 0, seg_f0[first:], hz)
        out_f0.append(seg_f0); out_sp.append(sp[idx]); out_ap.append(ap[idx])
        prev_hz = hz
    F0 = np.concatenate(out_f0); SP = warp_env(np.concatenate(out_sp), alpha); AP = np.concatenate(out_ap)
    y = pw.synthesize(np.ascontiguousarray(F0), np.ascontiguousarray(SP), np.ascontiguousarray(AP), SR, FP)
    fade = min(len(y) // 4, int(0.02 * SR))
    if fade > 0:
        y[:fade] *= np.linspace(0, 1, fade); y[-fade:] *= np.linspace(1, 0, fade)
    return y, prev_hz


def render_vocals(song, total_seconds, singer_of_section, out_sr=44100):
    """Return mono float32 vocal track at out_sr for all lyric notes in the song."""
    beat = 60.0 / song["bpm"]
    track = np.zeros(int((total_seconds + 1) * SR))
    words = {}
    for n in song["notes"]:
        if n["kind"] != "lyric":
            continue
        words.setdefault((n["line"], n["li"], n["word"]), []).append(n)
    prev_hz = None
    last_line = None
    for key in sorted(words, key=lambda k: words[k][0]["beat"]):
        ns = words[key]
        who = singer_of_section(ns[0])
        voices = who if isinstance(who, list) else [who]
        if key[:2] != last_line:
            prev_hz = None; last_line = key[:2]
        for vi, w in enumerate(voices):
            voice, alpha, shift, _ = VOICES.get(w, VOICES["all"])
            y, ph = sing_word(ns[0]["text"], ns, beat, voice, alpha, shift, prev_hz)
            start = int(ns[0]["beat"] * beat * SR) + int(vi * 0.012 * SR)
            end = min(len(track), start + len(y))
            gain = 1.0 / math.sqrt(len(voices))
            track[start:end] += y[: end - start] * gain
        prev_hz = ph
    # gentle compression + normalize
    peak = np.max(np.abs(track)) or 1
    track = np.tanh(track / peak * 1.6) / np.tanh(1.6)
    # resample to out_sr
    n_out = int(len(track) * out_sr / SR)
    xs = np.linspace(0, len(track) - 1, n_out)
    return np.interp(xs, np.arange(len(track)), track).astype(np.float32)
