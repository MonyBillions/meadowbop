"""Procedural scenes. World is 1280 wide; floor line ~600. Layers cover y in [-420, 1140]
so the same world can be framed for 16:9 and 9:16. Transparent areas show the animated sky."""
import math, random
import cairo
from rig import hexc, mix, ellipse, rrect, shade, flat, OUT

W = 1280
Y0, Y1 = -420, 1140
SCENES = ["bedroom", "bedroom_night", "bathroom", "kitchen", "park", "classroom", "meadow", "beach"]


def _clear(c, x, y, w, h, r=0):
    c.save(); c.set_operator(cairo.OPERATOR_CLEAR)
    rrect(c, x, y, w, h, r) if r else c.rectangle(x, y, w, h)
    c.fill(); c.restore()


def _window(c, x, y, w, h, frame="ffffff"):
    _clear(c, x, y, w, h)
    rrect(c, x - 12, y - 12, w + 24, h + 24, 10); c.rectangle(x, y, w, h)
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); flat(c, hexc(frame)); c.set_fill_rule(cairo.FILL_RULE_WINDING)
    c.move_to(x + w / 2, y); c.line_to(x + w / 2, y + h); c.move_to(x, y + h / 2); c.line_to(x + w, y + h / 2)
    c.set_source_rgba(*hexc(frame)); c.set_line_width(10); c.stroke()
    # curtains
    for sx, cx in ((-1, x - 20), (1, x + w + 20)):
        c.move_to(cx, y - 30); c.curve_to(cx + sx * -40, y + h * .4, cx + sx * 10, y + h * .7, cx + sx * -30, y + h + 30)
        c.line_to(cx + sx * 40, y + h + 30); c.line_to(cx + sx * 40, y - 30); c.close_path(); shade(c, hexc("ff8fab"))
    rrect(c, x - 70, y - 44, w + 140, 16, 8); flat(c, hexc("b07d56"))


def _floor_wood(c, top, col="d9a66b"):
    g = cairo.LinearGradient(0, top, 0, Y1); g.add_color_stop_rgba(0, *hexc(col)); g.add_color_stop_rgba(1, *mix(hexc(col), -0.25))
    c.rectangle(0, top, W, Y1 - top); c.set_source(g); c.fill()
    c.set_source_rgba(*mix(hexc(col), -0.18)); c.set_line_width(2)
    y = top + 30
    while y < Y1:
        c.move_to(0, y); c.line_to(W, y); y += 34 + (y - top) * 0.05
    c.stroke()
    c.rectangle(0, top - 14, W, 16); c.set_source_rgba(*hexc("ffffff")); c.fill()


def _wall(c, col, pattern="dots", top=Y0, bottom=600):
    c.rectangle(0, top, W, bottom - top); c.set_source_rgba(*hexc(col)); c.fill()
    r = random.Random(3)
    if pattern == "dots":
        for y in range(top, bottom, 60):
            for x in range(0, W, 60):
                c.new_sub_path(); c.arc(x + (30 if (y // 60) % 2 else 0), y, 6, 0, 2 * math.pi)
        c.set_source_rgba(1, 1, 1, .35); c.fill()
    elif pattern == "stripes":
        for x in range(0, W, 80):
            c.rectangle(x, top, 40, bottom - top)
        c.set_source_rgba(1, 1, 1, .18); c.fill()
    elif pattern == "stars":
        for _ in range(60):
            x, y = r.uniform(0, W), r.uniform(top, bottom - 100)
            _star(c, x, y, r.uniform(5, 10)); c.set_source_rgba(1, 1, .7, .55); c.fill()


def _star(c, x, y, R, r=None):
    r = r or R * 0.45
    c.move_to(x, y - R)
    for k in range(1, 10):
        rad = R if k % 2 == 0 else r
        a = -math.pi / 2 + k * math.pi / 5
        c.line_to(x + rad * math.cos(a), y + rad * math.sin(a))
    c.close_path()


def bedroom(c, night=False):
    _wall(c, "27306b" if night else "bde0fe", "stars" if night else "dots")
    _window(c, 520, 110, 260, 220)
    # bed
    rrect(c, 40, 380, 360, 200, 20); shade(c, hexc("8ecae6" if not night else "4361ee"))
    rrect(c, 30, 300, 40, 300, 12); shade(c, hexc("b07d56")); rrect(c, 390, 420, 30, 180, 10); shade(c, hexc("b07d56"))
    rrect(c, 80, 350, 130, 60, 26); shade(c, hexc("ffffff"))
    rrect(c, 160, 420, 240, 150, 20); shade(c, hexc("ffafcc"))
    for k in range(4):
        c.arc(200 + k * 50, 470 + (k % 2) * 30, 9, 0, 2 * math.pi); c.set_source_rgba(1, 1, 1, .7); c.fill()
    # shelf + toys
    rrect(c, 900, 230, 300, 18, 6); flat(c, hexc("b07d56"))
    rrect(c, 920, 170, 50, 60, 8); shade(c, hexc("ff595e")); rrect(c, 980, 190, 40, 40, 6); shade(c, hexc("ffca3a"))
    c.arc(1070, 205, 25, 0, 2 * math.pi); shade(c, hexc("8ac926"))
    rrect(c, 1110, 150, 70, 80, 8); shade(c, hexc("6a4c93"))
    # lamp
    rrect(c, 1130, 420, 20, 170, 6); flat(c, hexc("b07d56"))
    c.move_to(1090, 420); c.line_to(1190, 420); c.line_to(1165, 360); c.line_to(1115, 360); c.close_path()
    shade(c, hexc("ffd166"))
    if night:
        g = cairo.RadialGradient(1140, 420, 10, 1140, 420, 260)
        g.add_color_stop_rgba(0, 1, .9, .5, .45); g.add_color_stop_rgba(1, 1, .9, .5, 0)
        c.arc(1140, 420, 260, 0, 2 * math.pi); c.set_source(g); c.fill()
    _floor_wood(c, 600)
    ellipse(c, 700, 690, 330, 60); shade(c, hexc("cdb4db"), outline=False)


def bathroom(c):
    c.rectangle(0, Y0, W, 600 - Y0); c.set_source_rgba(*hexc("caf0f8")); c.fill()
    c.set_source_rgba(1, 1, 1, .7); c.set_line_width(3)
    for x in range(0, W, 64):
        c.move_to(x, Y0); c.line_to(x, 600)
    for y in range(Y0, 600, 64):
        c.move_to(0, y); c.line_to(W, y)
    c.stroke()
    _window(c, 980, 90, 200, 170, frame="ffffff")
    # mirror + sink
    rrect(c, 520, 120, 240, 200, 100); shade(c, hexc("e0fbfc")); rrect(c, 545, 145, 190, 150, 80)
    c.set_source_rgba(1, 1, 1, .5); c.fill()
    rrect(c, 500, 360, 280, 50, 20); shade(c, hexc("ffffff"))
    rrect(c, 600, 410, 80, 190, 10); shade(c, hexc("ffffff"))
    rrect(c, 620, 330, 40, 30, 6); flat(c, hexc("adb5bd"))
    # tub with bubbles
    rrect(c, 20, 400, 380, 200, 60); shade(c, hexc("ffffff"))
    r = random.Random(5)
    for _ in range(18):
        c.arc(r.uniform(50, 370), r.uniform(370, 420), r.uniform(14, 30), 0, 2 * math.pi)
        shade(c, hexc("f1faff"), lw=2)
    # towel rack
    rrect(c, 840, 300, 150, 12, 6); flat(c, hexc("adb5bd"))
    rrect(c, 860, 306, 110, 150, 10); shade(c, hexc("ffafcc"))
    c.rectangle(0, 600, W, Y1 - 600); c.set_source_rgba(*hexc("90e0ef")); c.fill()
    for y in range(600, Y1, 70):
        for x in range(0, W, 70):
            if ((x // 70) + (y // 70)) % 2 == 0:
                c.rectangle(x, y, 70, 70)
    c.set_source_rgba(1, 1, 1, .45); c.fill()


def kitchen(c):
    _wall(c, "fff3b0", "stripes")
    _window(c, 120, 100, 260, 200)
    # cabinets
    for x in (560, 760):
        rrect(c, x, 80, 180, 150, 14); shade(c, hexc("80ed99"))
        c.arc(x + 150, 160, 8, 0, 2 * math.pi); flat(c, hexc("ffffff"), lw=2)
    # fridge
    rrect(c, 1030, 150, 200, 450, 26); shade(c, hexc("e0fbfc"))
    c.move_to(1030, 320); c.line_to(1230, 320); c.set_source_rgba(*OUT); c.set_line_width(4); c.stroke()
    for y in (240, 400):
        rrect(c, 1050, y, 14, 60, 7); flat(c, hexc("adb5bd"), lw=2)
    for k, col in enumerate(["ff595e", "ffca3a", "8ac926"]):
        c.arc(1110 + k * 30, 190, 10, 0, 2 * math.pi); flat(c, hexc(col), lw=2)
    _floor_wood(c, 600, "e9c46a")
    # table front
    rrect(c, 380, 470, 520, 34, 12); shade(c, hexc("b07d56"))
    for x in (410, 840):
        rrect(c, x, 500, 26, 110, 8); shade(c, hexc("8d5a3b"))
    ellipse(c, 520, 460, 60, 18); shade(c, hexc("ff8fab")); ellipse(c, 520, 452, 44, 10); c.set_source_rgba(*hexc("ffe8a3")); c.fill()
    for k, col in enumerate(["ff595e", "ffca3a", "8ac926", "ff924c"]):
        c.arc(720 + k * 34, 448 - (k % 2) * 10, 17, 0, 2 * math.pi); shade(c, hexc(col), lw=3)


def _outdoor_ground(c, top=560, col1="8fd16a", col2="4c9a2a"):
    g = cairo.LinearGradient(0, top, 0, Y1); g.add_color_stop_rgba(0, *hexc(col1)); g.add_color_stop_rgba(1, *hexc(col2))
    c.move_to(0, top)
    for x in range(0, W + 20, 20):
        c.line_to(x, top + 8 * math.sin(x / 120))
    c.line_to(W, Y1); c.line_to(0, Y1); c.close_path(); c.set_source(g); c.fill()


def _hills(c, base=470):
    for (b, amp, col, ph) in [(base - 40, 40, "a7dd8a", 0.3), (base, 30, "86c86a", 1.7)]:
        c.move_to(0, Y1)
        for x in range(0, W + 20, 20):
            c.line_to(x, b - amp * math.sin(x / 210 + ph) - 15 * math.sin(x / 90 + ph * 2))
        c.line_to(W, Y1); c.close_path(); c.set_source_rgba(*hexc(col)); c.fill()


def _tree(c, x, y, s=1.0):
    rrect(c, x - 14 * s, y - 140 * s, 28 * s, 150 * s, 10 * s); shade(c, hexc("8d5a3b"))
    for (dx, dy, r) in [(0, -190, 70), (-55, -150, 52), (55, -150, 52), (0, -130, 50)]:
        c.arc(x + dx * s, y + dy * s, r * s, 0, 2 * math.pi); shade(c, hexc("52b788"), lw=3)


def _flowers(c, seed, y0=580, y1=1100, n=60):
    r = random.Random(seed)
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(y0, y1)
        col = r.choice(["ffffff", "ffd23f", "ff5fa2", "c77dff"])
        for k in range(5):
            a = k * 2 * math.pi / 5
            c.arc(x + 5 * math.cos(a), y + 5 * math.sin(a), 4, 0, 2 * math.pi); c.set_source_rgba(*hexc(col)); c.fill()
        c.arc(x, y, 3, 0, 2 * math.pi); c.set_source_rgba(*hexc("ff9f1c")); c.fill()


def park(c):
    _hills(c)
    _tree(c, 120, 560, 1.2); _tree(c, 1180, 540, 1.0)
    # slide
    rrect(c, 860, 330, 20, 250, 6); flat(c, hexc("adb5bd")); rrect(c, 960, 330, 20, 250, 6); flat(c, hexc("adb5bd"))
    for y in range(360, 580, 40):
        c.move_to(860, y); c.line_to(980, y)
    c.set_source_rgba(*OUT); c.set_line_width(4); c.stroke()
    rrect(c, 850, 320, 140, 22, 8); flat(c, hexc("ff595e"))
    c.move_to(980, 330); c.curve_to(1060, 360, 1080, 560, 1160, 580); c.line_to(1160, 600)
    c.curve_to(1060, 580, 1040, 380, 980, 360); c.close_path(); shade(c, hexc("ffca3a"))
    # swing
    c.move_to(320, 600); c.line_to(370, 330); c.line_to(560, 330); c.line_to(610, 600)
    c.set_source_rgba(*hexc("ff924c")); c.set_line_width(14); c.stroke_preserve(); c.set_source_rgba(*OUT); c.set_line_width(3); c.stroke()
    _outdoor_ground(c, 580)
    c.move_to(-50, 1140); c.curve_to(400, 800, 700, 700, 1330, 640); c.line_to(1330, 700)
    c.curve_to(760, 760, 480, 860, 120, 1140); c.close_path(); c.set_source_rgba(*hexc("f1dca7")); c.fill()
    _flowers(c, 11)


def classroom(c):
    _wall(c, "ffe5ec", "stripes")
    rrect(c, 300, 90, 680, 300, 12); shade(c, hexc("2d6a4f"))
    rrect(c, 290, 80, 700, 320, 16); c.set_source_rgba(*hexc("b07d56")); c.set_line_width(14); c.stroke()
    c.select_font_face("Be Vietnam Pro", 0, 1); c.set_font_size(90)
    for i, ch in enumerate("ABC"):
        c.move_to(350 + i * 110, 230); c.set_source_rgba(*hexc(["ffd166", "ffafcc", "a0e7e5"][i])); c.show_text(ch)
    c.set_font_size(80)
    for i, ch in enumerate("123"):
        c.move_to(720 + i * 80, 330); c.set_source_rgba(1, 1, 1, .9); c.show_text(ch)
    # bunting
    for k in range(14):
        x = 20 + k * 92
        c.move_to(x, 30); c.line_to(x + 80, 30); c.line_to(x + 40, 80); c.close_path()
        flat(c, hexc(["ff595e", "ffca3a", "8ac926", "1982c4", "6a4c93"][k % 5]), lw=2)
    # clock
    c.arc(1150, 170, 60, 0, 2 * math.pi); shade(c, hexc("ffffff"))
    c.move_to(1150, 170); c.line_to(1150, 130); c.move_to(1150, 170); c.line_to(1180, 180)
    c.set_source_rgba(*OUT); c.set_line_width(5); c.stroke()
    _window(c, 40, 150, 180, 200)
    _floor_wood(c, 600, "caa472")
    for x in (180, 1050):
        rrect(c, x - 90, 480, 180, 26, 8); shade(c, hexc("ff924c"))
        for dx in (-70, 70):
            rrect(c, x + dx - 8, 500, 16, 110, 6); flat(c, hexc("adb5bd"))


def meadow(c):
    _hills(c, 470)
    bx, by = 60, 300
    c.move_to(bx - 10, by + 60); c.line_to(bx + 95, by - 10); c.line_to(bx + 200, by + 60); c.close_path(); shade(c, hexc("8f2d2d"))
    rrect(c, bx, by + 55, 190, 170, 4); shade(c, hexc("c0392b"))
    rrect(c, bx + 60, by + 120, 70, 105, 3); flat(c, hexc("f4f1ea"))
    _outdoor_ground(c, 520)
    for x in range(250, W, 70):
        rrect(c, x, 455, 16, 85, 4); flat(c, hexc("f4e1c1"), lw=3)
    for y in (472, 505):
        rrect(c, 245, y, W - 245, 12, 4); flat(c, hexc("f4e1c1"), lw=3)
    _tree(c, 1180, 520, 0.9)
    _flowers(c, 7)


def beach(c):
    c.rectangle(0, 380, W, 140); g = cairo.LinearGradient(0, 380, 0, 520)
    g.add_color_stop_rgba(0, *hexc("48cae4")); g.add_color_stop_rgba(1, *hexc("0096c7")); c.set_source(g); c.fill()
    for k in range(10):
        c.arc(60 + k * 130, 450 + (k % 3) * 20, 18, math.pi, 2 * math.pi); c.set_source_rgba(1, 1, 1, .7); c.set_line_width(4); c.stroke()
    g = cairo.LinearGradient(0, 520, 0, Y1); g.add_color_stop_rgba(0, *hexc("ffe8a3")); g.add_color_stop_rgba(1, *hexc("f4c56a"))
    c.move_to(0, 520)
    for x in range(0, W + 20, 20):
        c.line_to(x, 520 + 10 * math.sin(x / 90))
    c.line_to(W, Y1); c.line_to(0, Y1); c.close_path(); c.set_source(g); c.fill()
    # umbrella + bucket
    c.move_to(1100, 640); c.line_to(1060, 380); c.set_source_rgba(*OUT); c.set_line_width(6); c.stroke()
    c.move_to(920, 420); c.curve_to(980, 300, 1150, 300, 1210, 360); c.close_path(); shade(c, hexc("ff595e"))
    rrect(c, 150, 560, 70, 70, 10); shade(c, hexc("1982c4"))
    for k in range(5):
        _star(c, 300 + k * 220, 700 + (k % 2) * 160, 20); flat(c, hexc("ff924c"), lw=3)


DRAWERS = dict(bedroom=lambda c: bedroom(c, False), bedroom_night=lambda c: bedroom(c, True), bathroom=bathroom,
               kitchen=kitchen, park=park, classroom=classroom, meadow=meadow, beach=beach)
NIGHT = {"bedroom_night"}


def make_layer(name):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, Y1 - Y0)
    c = cairo.Context(s); c.translate(0, -Y0)
    DRAWERS[name](c)
    return s


def draw_sky(c, t, night=False, rain=False):
    """Animated sky in world coords (drawn under the scene layer)."""
    g = cairo.LinearGradient(0, Y0, 0, 560)
    if night:
        g.add_color_stop_rgb(0, .05, .07, .2); g.add_color_stop_rgb(1, .18, .2, .45)
    elif rain:
        g.add_color_stop_rgb(0, .55, .62, .72); g.add_color_stop_rgb(1, .78, .83, .88)
    else:
        g.add_color_stop_rgb(0, .38, .72, .98); g.add_color_stop_rgb(1, .84, .95, 1.0)
    c.rectangle(0, Y0, W, Y1 - Y0); c.set_source(g); c.fill()
    if night:
        r = random.Random(1)
        for _ in range(90):
            x, y = r.uniform(0, W), r.uniform(Y0, 500)
            a = 0.5 + 0.5 * math.sin(t * r.uniform(1, 3) + x)
            _star(c, x, y, r.uniform(3, 7)); c.set_source_rgba(1, 1, .8, a); c.fill()
        c.arc(650, 180, 48, 0, 2 * math.pi); c.set_source_rgba(*hexc("fff3b0")); c.fill()
        c.arc(672, 165, 44, 0, 2 * math.pi); c.set_source_rgba(.12, .14, .34, 1); c.fill()
    elif not rain:
        sx, sy = 1120, 80
        c.save(); c.translate(sx, sy); c.rotate(t * 0.4)
        for k in range(12):
            c.rotate(math.pi / 6); rrect(c, -6, -88, 12, 26, 6); c.set_source_rgba(*hexc("ffd23f")); c.fill()
        c.restore()
        c.arc(sx, sy, 52, 0, 2 * math.pi); shade(c, hexc("ffd23f"), lw=5)
        for dx in (-17, 17):
            c.arc(sx + dx, sy - 6, 5, 0, 2 * math.pi); c.set_source_rgba(*OUT); c.fill()
        c.arc(sx, sy + 8, 18, 0.15 * math.pi, 0.85 * math.pi); c.set_line_width(4); c.stroke()
    for i, (y, sp, sc) in enumerate([(90, 18, 1.0), (190, 12, .75), (-120, 9, .9), (20, 14, .6)]):
        x = (i * 470 + t * sp) % (W + 300) - 150
        c.save(); c.translate(x, y); c.scale(sc, sc)
        for (dx, dy, r) in [(0, 0, 40), (45, -18, 48), (95, 0, 38), (48, 12, 40)]:
            c.arc(dx, dy, r, 0, 2 * math.pi)
            c.set_source_rgba(*((.85, .87, .92, .95) if rain else (1, 1, 1, .95 if not night else .15))); c.fill()
        c.restore()
