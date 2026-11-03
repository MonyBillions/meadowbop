"""Meadowbop renderer: episode JSON -> 16:9 sing-along video and 9:16 Short.

usage: python3 render.py EPISODE.json OUTDIR [--preview t1,t2,...] [--only land|vert]
"""
import json, math, os, random, subprocess, sys
import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rig import CHARACTERS, hexc, rrect, ellipse, OUT, mix
from actions import pose_for
from scenes import make_layer, draw_sky, Y0, NIGHT, _star
import music

FONT = "Be Vietnam Pro"
FPS = 25
LAYOUTS = {
    "land": dict(W=1280, H=720, zoom=1.0, cy=360, kfont=46, box_h=86),
    "vert": dict(W=1080, H=1920, zoom=1.9, cy=390, kfont=58, box_h=190),
}
POS = {"land": {1: [640], 2: [450, 830], 3: [320, 640, 960], 4: [250, 510, 770, 1030], 5: [190, 410, 640, 870, 1090]},
       "vert": {1: [640], 2: [500, 790], 3: [420, 640, 860], 4: [400, 560, 720, 880], 5: [380, 510, 640, 770, 900]}}


def text(c, s, x, y, size, fill, lw=8, anchor="center", stroke=OUT):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    ext = c.text_extents(s)
    if anchor == "center":
        x -= ext.x_advance / 2
    c.move_to(x, y); c.text_path(s); c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_source_rgba(*stroke); c.set_line_width(lw); c.stroke_preserve(); c.set_source_rgba(*fill); c.fill()
    return ext.x_advance


def ease_back(x):
    x = max(0, min(1, x)); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


class Episode:
    def __init__(self, ep, song, layout):
        self.ep, self.song, self.L = ep, song, LAYOUTS[layout]
        self.layout = layout
        self.beat = 60.0 / song["bpm"]
        self.dur = song["total"] * self.beat + 1.5
        self.layers = {}
        rng = random.Random(ep.get("seed", 1))
        self.blinks = {k: sorted(rng.uniform(0, self.dur) for _ in range(int(self.dur / 3))) for k in CHARACTERS}
        self.lines = {}
        for n in song["notes"]:
            if n["kind"] == "lyric":
                self.lines.setdefault((n["line"], n["li"]), []).append(n)
        self.line_keys = sorted(self.lines, key=lambda k: self.lines[k][0]["beat"])

    def layer(self, name):
        if name not in self.layers:
            self.layers[name] = make_layer(name)
        return self.layers[name]

    def section(self, b):
        for s in self.song["sections"]:
            if s["start"] <= b < s["end"]:
                return s
        return self.song["sections"][-1]

    def cast_of(self, s):
        return s.get("cast") or self.ep["cast"]

    def mouth(self, who, t, s):
        b = t / self.beat
        best = 0.0
        if s["kind"] in ("intro",):
            return 0.0
        singer = s.get("singer", "all")
        if s["kind"] == "outro":
            return 0.0
        if singer not in ("all", who) and s["kind"] != "chorus":
            return 0.0
        for n in self.song["notes"]:
            if n["kind"] != "lyric" or not (s["start"] <= n["beat"] < s["end"]):
                continue
            if n["beat"] <= b < n["beat"] + n["dur"] * 0.92:
                k = (b - n["beat"]) / max(n["dur"], 1e-3)
                best = max(best, 0.95 * (1 - 0.45 * k) * (0.85 + 0.15 * math.sin(t * 30)))
        return best

    def blinking(self, who, t):
        return any(x <= t < x + 0.13 for x in self.blinks[who])

    # ------------------------------------------------------------ frame
    def frame(self, c, t):
        L = self.L; W, H = L["W"], L["H"]
        b = t / self.beat
        s = self.section(min(b, self.song["total"] - 1e-3))
        scene = s.get("scene") or "meadow"
        cast = self.cast_of(s)
        singer = s.get("singer", "all")
        # camera
        prog = (b - s["start"]) / max(1, s["end"] - s["start"])
        zoom = L["zoom"] * (1.0 + 0.06 * prog)
        if s["kind"] == "chorus":
            zoom *= 1 + 0.012 * max(0, math.cos(b * math.pi * 2)) ** 8
        xs = POS[self.layout][min(len(cast), 5)]
        focus = 640
        if singer in cast and s["kind"] == "verse":
            focus = 640 + (xs[cast.index(singer)] - 640) * 0.35 * prog
        half = W / 2 / zoom
        cx = min(max(focus, half), 1280 - half)
        c.save()
        c.translate(W / 2, H / 2); c.scale(zoom, zoom); c.translate(-cx, -L["cy"])
        rain = s.get("weather") == "rain"
        draw_sky(c, t, night=scene in NIGHT, rain=rain)
        c.set_source_surface(self.layer(scene), 0, Y0); c.paint()
        # characters
        fxs = []
        for i, who in enumerate(cast[:5]):
            x = xs[i]
            if s["kind"] == "intro" or s["kind"] == "outro":
                act = "wave" if s["kind"] == "intro" else "dance"
            elif s["kind"] == "chorus":
                act = s.get("action", "dance")
            else:
                act = s.get("action", "groove") if who == singer or singer == "all" else s.get("others", "groove")
            p, bounce, fx = pose_for(act, b, t, phase=i * 0.37)
            p["t"] = t
            p["mouth"] = self.mouth(who, t, s)
            if not p.get("blink"):
                p["blink"] = self.blinking(who, t)
            if singer in cast and who != singer and s["kind"] == "verse":
                p["look"] = 1 if xs[cast.index(singer)] > x else -1
            h = CHARACTERS[who]["height"]
            sc = 0.92 if h < 300 else 0.86
            # entrance hop at start of section for new scenes
            ent = 0
            if s["kind"] != "intro" and b - s["start"] < 1.5 and self.prev_scene(s) != scene:
                ent = (1 - (b - s["start"]) / 1.5) ** 2 * 120
            y = 612
            ellipse(c, x, y + 2, 64 * sc * (1 - bounce / 250), 12 * sc); c.set_source_rgba(0, 0, 0, .2); c.fill()
            sq = 1 + 0.03 * math.cos(b * 2 * math.pi)
            c.save(); c.translate(x, y - bounce - ent); c.rotate(p.get("lean", 0)); c.scale(sc / sq ** .5, sc * sq)
            CHARACTERS[who]["fn"](c, p)
            c.restore()
            if fx:
                fxs.append((fx, x, y - h * sc, i))
        for fx, x, y, i in fxs:
            self.particles(c, fx, x, y, t, i)
        if rain:
            self.rain(c, t)
        c.restore()
        # overlays (screen space)
        self.logo(c, t)
        if s["kind"] == "intro":
            self.title_card(c, t, b - s["start"])
        elif s["kind"] == "outro":
            self.outro_card(c, t, b - s["start"])
        self.karaoke(c, t)
        self.iris(c, t)
        if t < 0.5:
            c.set_source_rgba(0, 0, 0, 1 - t / 0.5); c.paint()
        if t > self.dur - 1.2:
            c.set_source_rgba(0, 0, 0, min(1, (t - (self.dur - 1.2)) / 1.2)); c.paint()

    def prev_scene(self, s):
        secs = self.song["sections"]
        i = secs.index(s)
        return secs[i - 1].get("scene") if i > 0 else None

    def iris(self, c, t):
        W, H = self.L["W"], self.L["H"]
        secs = self.song["sections"]
        for i in range(1, len(secs)):
            if secs[i].get("scene") == secs[i - 1].get("scene"):
                continue
            T = secs[i]["start"] * self.beat
            d = 0.35
            if T - d <= t < T + d:
                k = abs(t - T) / d
                r = (W ** 2 + H ** 2) ** .5 / 2 * k
                c.save(); c.rectangle(0, 0, W, H); c.arc(W / 2, H / 2, max(r, 0.1), 0, 2 * math.pi)
                c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.set_source_rgba(*hexc("2b2d42")); c.fill(); c.restore()
                if k < 0.35:
                    _star(c, W / 2, H / 2, 60 * (1 - k / 0.35) + 10); c.set_source_rgba(*hexc("ffd23f")); c.fill()

    def particles(self, c, fx, x, y, t, i):
        rng = random.Random(i * 97 + hash(fx) % 1000)
        if fx == "foam" or fx == "bubbles":
            for k in range(12):
                ph = rng.uniform(0, 3); life = 1.6
                a = ((t + ph) % life) / life
                bx = x + rng.uniform(-50, 50) + 12 * math.sin(t * 3 + k)
                by = y + (60 if fx == "foam" else 120) - a * 160
                r = rng.uniform(6, 16) * (0.6 + a)
                c.arc(bx, by, r, 0, 2 * math.pi); c.set_source_rgba(1, 1, 1, .75 * (1 - a)); c.fill_preserve()
                c.set_source_rgba(.4, .7, .95, .6 * (1 - a)); c.set_line_width(2); c.stroke()
        elif fx == "zzz":
            for k in range(3):
                a = ((t * 0.5 + k / 3) % 1)
                text(c, "z", x + 50 + a * 60, y - a * 100, 30 + 20 * a, (0.8, 0.85, 1, 1 - a), lw=4,
                     stroke=(0.2, 0.2, 0.4, 1 - a))
        elif fx in ("notes", "sparkle"):
            for k in range(6):
                ph = rng.uniform(0, 2); life = 2.0
                a = ((t + ph) % life) / life
                bx = x + rng.uniform(-90, 90) + 20 * math.sin(t * 2 + k)
                by = y + 20 - a * 140
                col = hexc(rng.choice(["ff595e", "ffca3a", "8ac926", "1982c4", "6a4c93"]))
                if fx == "notes":
                    c.save(); c.translate(bx, by); c.set_source_rgba(*col[:3], 1 - a)
                    ellipse(c, 0, 0, 9, 7); c.fill(); c.rectangle(6, -30, 4, 30); c.fill(); c.restore()
                else:
                    _star(c, bx, by, 12 * (1 - a) + 4); c.set_source_rgba(*col[:3], 1 - a); c.fill()

    def rain(self, c, t):
        rng = random.Random(4)
        c.set_source_rgba(.6, .75, .95, .7); c.set_line_width(3)
        for k in range(120):
            x = rng.uniform(0, 1280); sp = rng.uniform(600, 900)
            y = (rng.uniform(0, 1500) + t * sp) % 1500 - 400
            c.move_to(x, y); c.line_to(x - 6, y + 22)
        c.stroke()

    def logo(self, c, t):
        s = 1.0 if self.layout == "land" else 1.5
        c.save(); c.translate(24 * s, 22 * s); c.scale(s, s)
        rrect(c, 0, 0, 210, 52, 26); c.set_source_rgba(1, 1, 1, .85); c.fill_preserve()
        c.set_source_rgba(*hexc("ff8fab")); c.set_line_width(4); c.stroke()
        cols = ["ff595e", "ff924c", "ffca3a", "8ac926", "1982c4", "4267ac", "6a4c93", "ff595e", "ff924c"]
        x = 18
        for i, ch in enumerate("Meadowbop"):
            x += text(c, ch, x, 37 - 3 * math.sin(t * 4 - i * .6), 28, hexc(cols[i]), lw=5, anchor="left")
        c.restore()

    def title_card(self, c, t, sb):
        W, H = self.L["W"], self.L["H"]
        big = 74 if self.layout == "land" else 92
        y0 = 150 if self.layout == "land" else 420
        title = self.ep["title"]
        appear = min(1, sb / 2)
        words = title.split()
        rows, row = [], ""
        maxw = W - 120
        c.select_font_face(FONT, 0, 1); c.set_font_size(big)
        for w in words:
            tr = (row + " " + w).strip()
            if c.text_extents(tr).x_advance > maxw and row:
                rows.append(row); row = w
            else:
                row = tr
        rows.append(row)
        cols = ["ff4d6d", "ffd23f", "4cc9f0", "80ed99", "c77dff", "ff9f1c"]
        ci = 0
        for ri, r in enumerate(rows):
            c.set_font_size(big)
            total = c.text_extents(r).x_advance
            x = W / 2 - total / 2
            for i, ch in enumerate(r):
                c.set_font_size(big); adv = c.text_extents(ch).x_advance
                y = y0 + ri * big * 1.1 - 12 * math.sin(t * 5 - i * .45) - (1 - ease_back(appear)) * 500
                if ch != " ":
                    text(c, ch, x, y, big, hexc(cols[ci % len(cols)]), lw=12, anchor="left"); ci += 1
                x += adv
        sub = self.ep.get("subtitle", "")
        if sub:
            text(c, sub, W / 2, y0 + len(rows) * big * 1.1 + 10, big * 0.48, hexc("ffffff"), lw=8)

    def outro_card(self, c, t, sb):
        W = self.L["W"]
        y0 = 140 if self.layout == "land" else 420
        big = 76 if self.layout == "land" else 88
        msg = self.ep.get("outro_text", "See you tomorrow!")
        if self.layout == "vert":
            msg = self.ep.get("short_outro", "Full song on Meadowbop!")
        sc = ease_back(min(1, sb / 1.2))
        c.select_font_face(FONT, 0, 1); c.set_font_size(big)
        wdt = c.text_extents(msg).x_advance
        if wdt > W - 80:
            big *= (W - 80) / wdt
        c.save(); c.translate(W / 2, y0); c.scale(sc, sc)
        text(c, msg, 0, 0, big, hexc("ffd23f"), lw=12)
        c.restore()

    def karaoke(self, c, t):
        L = self.L; W, H = L["W"], L["H"]
        b = t / self.beat
        cur = None
        for i, k in enumerate(self.line_keys):
            st = self.lines[k][0]["beat"] - 1.0
            nx = self.lines[self.line_keys[i + 1]][0]["beat"] - 1.0 if i + 1 < len(self.line_keys) else \
                self.lines[k][-1]["beat"] + self.lines[k][-1]["dur"] + 1.5
            if st <= b < nx:
                cur = k
        if cur is None:
            return
        notes = self.lines[cur]
        words = {}
        for n in notes:
            words.setdefault(n["word"], []).append(n)
        wl = [(ws[0]["text"], ws) for _, ws in sorted(words.items())]
        size = L["kfont"]
        c.select_font_face(FONT, 0, 1); c.set_font_size(size)
        space = c.text_extents("a a").x_advance - 2 * c.text_extents("a").x_advance
        widths = [c.text_extents(w).x_advance for w, _ in wl]
        maxw = W - 200
        rows = [[]]; rw = 0
        for i, wdt in enumerate(widths):
            if rw + wdt > maxw and rows[-1] and self.layout == "vert":
                rows.append([]); rw = 0
            rows[-1].append(i); rw += wdt + space
        if self.layout == "land" and rw > maxw:
            size = size * maxw / rw; c.set_font_size(size)
            widths = [c.text_extents(w).x_advance for w, _ in wl]; space *= maxw / rw
        box_h = L["box_h"] if len(rows) > 1 or self.layout == "land" else L["box_h"] * 0.6
        by = H - box_h - (18 if self.layout == "land" else 260)
        rrect(c, 70, by, W - 140, box_h, 40); c.set_source_rgba(1, 1, 1, .9); c.fill_preserve()
        c.set_source_rgba(*hexc("ff9f1c")); c.set_line_width(5); c.stroke()
        line_h = size * 1.25
        y = by + box_h / 2 - (len(rows) - 1) * line_h / 2 + size * 0.36
        for row in rows:
            total = sum(widths[i] for i in row) + space * (len(row) - 1)
            x = W / 2 - total / 2
            for i in row:
                w, ws = wl[i]
                t0 = ws[0]["beat"]; t1 = ws[-1]["beat"] + ws[-1]["dur"]
                active = t0 <= b < t1; done = b >= t0
                lift = -6 * math.sin(min(1, (b - t0) / max(t1 - t0, .1)) * math.pi) if active else 0
                c.set_font_size(size * (1.05 if active else 1))
                c.move_to(x - (widths[i] * .025 if active else 0), y + lift); c.text_path(w)
                c.set_source_rgba(*(hexc("ff6b00") if done else hexc("3b2a20"))); c.fill()
                c.set_font_size(size)
                for n in ws:  # bouncing ball per syllable
                    if n["beat"] <= b < n["beat"] + n["dur"]:
                        k = (b - n["beat"]) / n["dur"]
                        bx = x + widths[i] * (n["syl"] + 0.5) / n["nsyl"]
                        bby = y - size * 0.95 - 22 * math.sin(k * math.pi)
                        c.arc(bx, bby, size * 0.2, 0, 2 * math.pi); c.set_source_rgba(*hexc("ffd23f")); c.fill_preserve()
                        c.set_source_rgba(*OUT); c.set_line_width(3); c.stroke()
                x += widths[i] + space
            y += line_h


def render(ep, song, layout, wav, out, preview=None):
    E = Episode(ep, song, layout)
    W, H = E.L["W"], E.L["H"]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    if preview:
        for ts in preview:
            c.save(); E.frame(c, ts); c.restore(); surf.write_to_png(f"{out}_{ts:06.2f}.png")
        return
    n = int(E.dur * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    for i in range(n):
        c.save(); E.frame(c, i / FPS); c.restore(); surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if i % 500 == 0:
            print(f"[{layout}] {i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    return E.dur


def main():
    ep = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    preview = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")] if "--preview" in sys.argv else None
    slug = ep["slug"]
    full = music.build_song(ep)
    vi = next(i for i, s in enumerate(ep["sections"]) if s["type"] == "verse")
    ci = next(i for i, s in enumerate(ep["sections"]) if s["type"] == "chorus")
    short = music.build_song(ep, [vi, ci], intro_beats=8, outro_beats=8)
    res = {}
    for layout, song in (("land", full), ("vert", short)):
        if only and only != layout:
            continue
        base = os.path.join(outdir, f"{slug}_{'video' if layout == 'land' else 'short'}")
        if preview:
            render(ep, song, layout, None, base, preview); continue
        dur_a, inst = music.render_audio(song, ep, base + ".wav")
        dur = render(ep, song, layout, base + ".wav", base + ".mp4")
        os.remove(base + ".wav")
        res[layout] = dict(file=base + ".mp4", seconds=round(dur, 1), instruments=inst)
        print("done", base + ".mp4", round(dur, 1))
    if res:
        json.dump(res, open(os.path.join(outdir, f"{slug}_render.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
