"""Meadowbop character rig: shaded vector characters with jointed arms, legs, head tilt and props.

Pose keys (all optional):
  t, mouth (0..1), blink (bool), look (-1..1), happy (0..1 brow lift),
  tilt (rad head), lean (rad body), squash (scale y),
  armL/armR = (raise, elbow)  raise: 0 = hanging, pi = straight up (outward); elbow: + bends up/out, - bends inward
  legL/legR = (lift_px, swing_rad)
  propR / propL = 'toothbrush' | 'spoon' | 'cup' | 'book' | 'ball' | 'teddy' | 'flower' | None
"""
import math

TAU = 2 * math.pi


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c, k):
    """k>0 lighten towards white, k<0 darken towards black."""
    if k >= 0:
        return tuple(c[i] + (1 - c[i]) * k for i in range(3)) + (c[3],)
    return tuple(c[i] * (1 + k) for i in range(3)) + (c[3],)


OUT = hexc("3b2a20")
LW = 4.0


def ellipse(ctx, cx, cy, rx, ry):
    ctx.save(); ctx.translate(cx, cy); ctx.scale(max(rx, .01), max(ry, .01))
    ctx.arc(0, 0, 1, 0, TAU); ctx.restore()


def rrect(ctx, x, y, w, h, r):
    r = max(0.01, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def shade(ctx, color, lw=LW, outline=True, light=0.22, dark=-0.14):
    """Fill current path with a soft radial gradient + outline."""
    import cairo
    x0, y0, x1, y1 = ctx.fill_extents()
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    g = cairo.RadialGradient(x0 + w * 0.35, y0 + h * 0.28, 0, x0 + w * 0.5, y0 + h * 0.5, max(w, h) * 0.75)
    g.add_color_stop_rgba(0, *mix(color, light)); g.add_color_stop_rgba(0.55, *color)
    g.add_color_stop_rgba(1, *mix(color, dark))
    ctx.set_source(g)
    if outline:
        ctx.fill_preserve(); ctx.set_source_rgba(*OUT); ctx.set_line_width(lw)
        ctx.set_line_join(1); ctx.stroke()
    else:
        ctx.fill()


def flat(ctx, color, lw=LW, outline=True):
    ctx.set_source_rgba(*color)
    if outline:
        ctx.fill_preserve(); ctx.set_source_rgba(*OUT); ctx.set_line_width(lw); ctx.stroke()
    else:
        ctx.fill()


# ------------------------------------------------------------- face parts
def eye(ctx, x, y, p, s=1.0):
    s *= 1.17  # big, friendly eyes
    if p.get("blink"):
        ctx.set_source_rgba(*OUT); ctx.set_line_width(4 * s); ctx.set_line_cap(1)
        ctx.arc(x, y - 2 * s, 10 * s, 0.15 * math.pi, 0.85 * math.pi); ctx.stroke()
        return
    ellipse(ctx, x, y, 12 * s, 15 * s); flat(ctx, hexc("ffffff"), lw=3 * s)
    lk = p.get("look", 0.0)
    ellipse(ctx, x + lk * 4 * s, y + 2 * s, 7.5 * s, 9.5 * s); ctx.set_source_rgba(*hexc("241a14")); ctx.fill()
    ctx.arc(x + lk * 4 * s + 2.8 * s, y - 2 * s, 3.2 * s, 0, TAU); ctx.set_source_rgba(1, 1, 1, 1); ctx.fill()
    ctx.arc(x + lk * 4 * s - 2.5 * s, y + 5 * s, 1.5 * s, 0, TAU); ctx.fill()


def brows(ctx, x1, x2, y, p, s=1.0, color=OUT):
    lift = p.get("happy", 0.4) * 5 * s
    ctx.set_source_rgba(*color); ctx.set_line_width(4 * s); ctx.set_line_cap(1)
    for x, d in ((x1, -1), (x2, 1)):
        ctx.move_to(x - 9 * s, y - lift + 2 * s * d * 0); ctx.curve_to(x - 3 * s, y - 5 * s - lift, x + 3 * s, y - 5 * s - lift, x + 9 * s, y - lift)
        ctx.stroke()


def mouth(ctx, x, y, p, s=1.0, w=20):
    m = p.get("mouth", 0.0)
    if m > 0.08:
        h = (6 + 20 * m) * s
        ellipse(ctx, x, y + h / 2 - 2 * s, w * 0.6 * s * (1 - 0.15 * m), h / 2 + 1)
        flat(ctx, hexc("8a1c2b"), lw=3 * s)
        ctx.save(); ellipse(ctx, x, y + h / 2 - 2 * s, w * 0.6 * s, h / 2 + 1); ctx.clip()
        ellipse(ctx, x, y + h - 2 * s, w * 0.45 * s, h * 0.35); ctx.set_source_rgba(*hexc("ff7b8a")); ctx.fill()
        rrect(ctx, x - w * 0.35 * s, y - 3 * s, w * 0.7 * s, 5 * s, 2 * s); ctx.set_source_rgba(1, 1, 1, 1); ctx.fill()
        ctx.restore()
    else:
        ctx.set_source_rgba(*OUT); ctx.set_line_width(4 * s); ctx.set_line_cap(1)
        ctx.arc(x, y - 6 * s, w * 0.55 * s, 0.2 * math.pi, 0.8 * math.pi); ctx.stroke()


def blush(ctx, x, y, s=1.0):
    ellipse(ctx, x, y, 10 * s, 6 * s); ctx.set_source_rgba(*hexc("ff6f91", 0.45)); ctx.fill()


# ------------------------------------------------------------- props
def prop(ctx, kind, t):
    if not kind:
        return
    if kind == "toothbrush":
        rrect(ctx, -5, -46, 10, 50, 5); flat(ctx, hexc("3a86ff"), lw=3)
        rrect(ctx, -8, -64, 16, 20, 4); flat(ctx, hexc("ffffff"), lw=3)
        for k in range(3):
            ctx.arc(-6 + k * 6 + 2 * math.sin(t * 20 + k), -70 - k % 2 * 3, 6, 0, TAU)
            ctx.set_source_rgba(1, 1, 1, .9); ctx.fill()
    elif kind == "spoon":
        rrect(ctx, -3, -40, 6, 44, 3); flat(ctx, hexc("d9d9e0"), lw=2.5)
        ellipse(ctx, 0, -48, 10, 13); flat(ctx, hexc("d9d9e0"), lw=2.5)
        ellipse(ctx, 0, -50, 7, 8); ctx.set_source_rgba(*hexc("f6c945")); ctx.fill()
    elif kind == "cup":
        rrect(ctx, -16, -36, 32, 36, 6); flat(ctx, hexc("ff8fab"), lw=3)
        rrect(ctx, -12, -34, 24, 8, 3); ctx.set_source_rgba(1, 1, 1, .95); ctx.fill()
    elif kind == "book":
        ctx.save(); ctx.rotate(-0.2)
        rrect(ctx, -30, -46, 60, 44, 4); flat(ctx, hexc("ef476f"), lw=3)
        ctx.move_to(0, -46); ctx.line_to(0, -2); ctx.set_source_rgba(*OUT); ctx.set_line_width(3); ctx.stroke()
        ctx.restore()
    elif kind == "ball":
        ctx.arc(0, -22, 22, 0, TAU); shade(ctx, hexc("ff595e"), lw=3)
        ctx.arc(0, -22, 22, -0.6, 0.6); ctx.set_source_rgba(1, 1, 1, .9); ctx.set_line_width(5); ctx.stroke()
    elif kind == "teddy":
        for dx in (-14, 14):
            ctx.arc(dx, -52, 9, 0, TAU); flat(ctx, hexc("b07d56"), lw=3)
        ctx.arc(0, -38, 20, 0, TAU); shade(ctx, hexc("b07d56"), lw=3)
        for dx in (-7, 7):
            ctx.arc(dx, -42, 3, 0, TAU); ctx.set_source_rgba(*OUT); ctx.fill()
    elif kind == "flower":
        ctx.move_to(0, 0); ctx.line_to(0, -50); ctx.set_source_rgba(*hexc("43a047")); ctx.set_line_width(5); ctx.stroke()
        for k in range(6):
            a = k * TAU / 6 + t
            ctx.arc(10 * math.cos(a), -56 + 10 * math.sin(a), 8, 0, TAU); flat(ctx, hexc("ff8fab"), lw=2)
        ctx.arc(0, -56, 7, 0, TAU); flat(ctx, hexc("ffd23f"), lw=2)
    elif kind == "towel":
        rrect(ctx, -26, -40, 52, 70, 8); flat(ctx, hexc("4cc9f0"), lw=3)
        for k in range(3):
            ctx.move_to(-26, 18 + k * 4); ctx.line_to(26, 18 + k * 4)
        ctx.set_source_rgba(1, 1, 1, .8); ctx.set_line_width(2); ctx.stroke()


# ------------------------------------------------------------- limbs
def arm(ctx, x, y, side, pose, L1, L2, w, sleeve, skin, hand="hand", propkind=None, t=0.0):
    """side: -1 = screen-left arm, +1 = screen-right arm."""
    raise_, elbow = pose
    ctx.save(); ctx.translate(x, y); ctx.rotate(-side * raise_)
    rrect(ctx, -w / 2, -w * 0.3, w, L1 + w * 0.5, w / 2); shade(ctx, sleeve)
    ctx.translate(0, L1); ctx.rotate(-side * elbow)
    rrect(ctx, -w * 0.42, -w * 0.3, w * 0.84, L2 + w * 0.3, w * 0.42); shade(ctx, skin if hand != "wing" else sleeve)
    ctx.translate(0, L2)
    if hand == "hand":
        ctx.arc(0, 2, w * 0.58, 0, TAU); shade(ctx, skin)
    elif hand == "hoof":
        rrect(ctx, -w * 0.55, -2, w * 1.1, w * 0.7, w * 0.3); flat(ctx, hexc("2d2a2a"))
    if propkind:
        ctx.save(); ctx.rotate(math.pi + side * (raise_ + elbow) * 0.0)
        # keep props roughly upright: undo accumulated rotation
        ctx.rotate(side * (raise_ + elbow) - math.pi)
        prop(ctx, propkind, t)
        ctx.restore()
    ctx.restore()


def leg(ctx, x, y, side, pose, L, w, color, shoe, shoe_w=None, shoe_kind="shoe"):
    lift, swing = pose
    ctx.save(); ctx.translate(x, y - lift); ctx.rotate(swing)
    rrect(ctx, -w / 2, -6, w, L + 6, w / 2.2); shade(ctx, color)
    sw = shoe_w or w * 1.5
    if shoe_kind == "shoe":
        rrect(ctx, -sw / 2 + side * 5, L - 6, sw, w * 0.9, w * 0.45); shade(ctx, shoe)
    elif shoe_kind == "hoof":
        rrect(ctx, -w * 0.58, L - 10, w * 1.16, 20, 7); flat(ctx, shoe)
    elif shoe_kind == "webbed":
        ellipse(ctx, side * 6, L, 26, 9); shade(ctx, shoe)
    ctx.restore()


def head_at(ctx, x, y, tilt):
    ctx.save(); ctx.translate(x, y); ctx.rotate(tilt); ctx.translate(-x, -y)


def P(p, k, d):
    return p.get(k, d)


# ------------------------------------------------------------- characters
def draw_lily(ctx, p):
    skin, dress = hexc("6b3e26"), hexc("ffd23f")
    t = p.get("t", 0)
    leg(ctx, -18, -78, -1, P(p, "legL", (0, 0)), 66, 16, skin, hexc("e94f87"))
    leg(ctx, 18, -78, 1, P(p, "legR", (0, 0)), 66, 16, skin, hexc("e94f87"))
    arm(ctx, -34, -146, -1, P(p, "armL", (0.3, 0)), 34, 30, 17, dress, skin, propkind=p.get("propL"), t=t)
    ctx.move_to(-30, -158); ctx.line_to(30, -158); ctx.line_to(64, -64)
    ctx.curve_to(22, -52, -22, -52, -64, -64); ctx.close_path(); shade(ctx, dress)
    for k in range(4):
        ctx.arc(-30 + k * 20, -86, 5, 0, TAU); ctx.set_source_rgba(1, 1, 1, .9); ctx.fill()
    arm(ctx, 34, -146, 1, P(p, "armR", (0.3, 0)), 34, 30, 17, dress, skin, propkind=p.get("propR"), t=t)
    hx, hy = 0, -205
    head_at(ctx, hx, hy + 40, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.arc(hx + sx * 50, hy - 40, 28, 0, TAU); shade(ctx, hexc("2b1b14"))
        ctx.save(); ctx.translate(hx + sx * 36, hy - 58)
        for d in (-1, 1):
            ctx.move_to(0, 0); ctx.line_to(d * 18, -10); ctx.line_to(d * 18, 10); ctx.close_path()
        flat(ctx, hexc("ff5fa2"), lw=3); ctx.restore()
    ctx.arc(hx, hy - 8, 54, math.pi, TAU); flat(ctx, hexc("2b1b14"))
    ctx.arc(hx, hy, 48, 0, TAU); shade(ctx, skin)
    ctx.arc(hx, hy - 10, 49, 1.1 * math.pi, 1.9 * math.pi); ctx.set_source_rgba(*hexc("2b1b14")); ctx.fill()
    eye(ctx, hx - 17, hy + 2, p, 0.85); eye(ctx, hx + 17, hy + 2, p, 0.85)
    brows(ctx, hx - 17, hx + 17, hy - 16, p, 0.7, hexc("2b1b14"))
    blush(ctx, hx - 30, hy + 20); blush(ctx, hx + 30, hy + 20)
    mouth(ctx, hx, hy + 27, p, 0.8)
    ctx.restore()


def draw_leo(ctx, p):
    skin, shirt, shorts = hexc("c68642"), hexc("2ec4b6"), hexc("3a6ea5")
    t = p.get("t", 0)
    leg(ctx, -18, -86, -1, P(p, "legL", (0, 0)), 74, 18, skin, hexc("ff595e"))
    leg(ctx, 18, -86, 1, P(p, "legR", (0, 0)), 74, 18, skin, hexc("ff595e"))
    rrect(ctx, -36, -104, 72, 34, 12); shade(ctx, shorts)
    arm(ctx, -40, -160, -1, P(p, "armL", (0.3, 0)), 34, 32, 18, shirt, skin, propkind=p.get("propL"), t=t)
    rrect(ctx, -42, -172, 84, 78, 22); shade(ctx, shirt)
    # star on shirt
    ctx.save(); ctx.translate(0, -134); ctx.move_to(0, -14)
    for k in range(1, 10):
        r = 14 if k % 2 == 0 else 6
        a = -math.pi / 2 + k * math.pi / 5
        ctx.line_to(r * math.cos(a), r * math.sin(a))
    ctx.close_path(); flat(ctx, hexc("ffd23f"), lw=2.5); ctx.restore()
    arm(ctx, 40, -160, 1, P(p, "armR", (0.3, 0)), 34, 32, 18, shirt, skin, propkind=p.get("propR"), t=t)
    hx, hy = 0, -222
    head_at(ctx, hx, hy + 45, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.arc(hx + sx * 50, hy + 4, 12, 0, TAU); shade(ctx, skin)
    ctx.arc(hx, hy, 50, 0, TAU); shade(ctx, skin)
    for k in range(9):  # curly hair
        a = math.pi * (1.05 + k * 0.1)
        ctx.arc(hx + 46 * math.cos(a), hy - 4 + 46 * math.sin(a), 15, 0, TAU)
        flat(ctx, hexc("2b1b14"), lw=2)
    ellipse(ctx, hx, hy - 38, 40, 16); ctx.set_source_rgba(*hexc("2b1b14")); ctx.fill()
    eye(ctx, hx - 18, hy + 2, p, 0.85); eye(ctx, hx + 18, hy + 2, p, 0.85)
    ctx.set_source_rgba(*OUT); ctx.set_line_width(3)
    for sx in (-1, 1):
        ctx.arc(hx + sx * 18, hy + 2, 17, 0, TAU); ctx.stroke()
    ctx.move_to(hx - 2, hy + 2); ctx.line_to(hx + 2, hy + 2); ctx.stroke()
    blush(ctx, hx - 32, hy + 22); blush(ctx, hx + 32, hy + 22)
    mouth(ctx, hx, hy + 30, p, 0.8)
    ctx.restore()


def draw_grandpa(ctx, p):
    skin, shirt, denim = hexc("8d5a3b"), hexc("e63946"), hexc("3a6ea5")
    t = p.get("t", 0)
    leg(ctx, -26, -112, -1, P(p, "legL", (0, 0)), 100, 30, denim, hexc("6b4226"))
    leg(ctx, 26, -112, 1, P(p, "legR", (0, 0)), 100, 30, denim, hexc("6b4226"))
    arm(ctx, -56, -200, -1, P(p, "armL", (0.2, 0)), 48, 42, 26, shirt, skin, propkind=p.get("propL"), t=t)
    rrect(ctx, -62, -215, 124, 125, 30); shade(ctx, shirt)
    rrect(ctx, -46, -175, 92, 90, 14); shade(ctx, denim)
    for sx in (-1, 1):
        ctx.move_to(sx * 36, -172); ctx.line_to(sx * 44, -212)
        ctx.set_source_rgba(*denim); ctx.set_line_width(12); ctx.stroke()
        ctx.arc(sx * 32, -160, 6, 0, TAU); flat(ctx, hexc("f6c945"), lw=2)
    arm(ctx, 56, -200, 1, P(p, "armR", (0.2, 0)), 48, 42, 26, shirt, skin, propkind=p.get("propR"), t=t)
    hx, hy = 0, -268
    head_at(ctx, hx, hy + 55, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.arc(hx + sx * 56, hy + 6, 14, 0, TAU); shade(ctx, skin)
    ctx.arc(hx, hy, 58, 0, TAU); shade(ctx, skin)
    ctx.move_to(hx - 52, hy + 4); ctx.curve_to(hx - 55, hy + 70, hx + 55, hy + 70, hx + 52, hy + 4)
    ctx.curve_to(hx + 30, hy + 22, hx - 30, hy + 22, hx - 52, hy + 4); shade(ctx, hexc("f4f1ea"), lw=3)
    eye(ctx, hx - 20, hy - 10, p, 0.95); eye(ctx, hx + 20, hy - 10, p, 0.95)
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 21, hy - 31 - P(p, "happy", .4) * 4, 15, 6); flat(ctx, hexc("f4f1ea"), lw=2)
    ellipse(ctx, hx, hy + 6, 13, 11); shade(ctx, hexc("a8694a"), lw=3)
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 14, hy + 18, 16, 8); flat(ctx, hexc("f4f1ea"), lw=2)
    mouth(ctx, hx, hy + 30, p, 0.9)
    ellipse(ctx, hx, hy - 44, 98, 20); shade(ctx, hexc("f2c14e"))
    rrect(ctx, hx - 50, hy - 95, 100, 55, 22); shade(ctx, hexc("f2c14e"))
    rrect(ctx, hx - 50, hy - 60, 100, 14, 4); flat(ctx, hexc("e63946"), lw=3)
    ctx.restore()


def draw_daisy(ctx, p):
    white, black, pink = hexc("fbfaf5"), hexc("2d2a2a"), hexc("f7a1b5")
    t = p.get("t", 0)
    leg(ctx, -30, -100, -1, P(p, "legL", (0, 0)), 92, 34, white, black, shoe_kind="hoof")
    leg(ctx, 30, -100, 1, P(p, "legR", (0, 0)), 92, 34, white, black, shoe_kind="hoof")
    arm(ctx, -66, -205, -1, P(p, "armL", (0.35, 0)), 44, 38, 28, white, white, hand="hoof", propkind=p.get("propL"), t=t)
    ellipse(ctx, 0, -150, 78, 95); shade(ctx, white, light=0.0, dark=-0.08)
    ctx.save(); ellipse(ctx, 0, -150, 78, 95); ctx.clip()
    for (x, y, rx, ry) in [(-50, -200, 30, 22), (45, -120, 28, 34), (-30, -80, 22, 16)]:
        ellipse(ctx, x, y, rx, ry); ctx.set_source_rgba(*black); ctx.fill()
    ctx.restore()
    ellipse(ctx, 0, -125, 42, 50); shade(ctx, pink, lw=3)
    arm(ctx, 66, -205, 1, P(p, "armR", (0.35, 0)), 44, 38, 28, white, white, hand="hoof", propkind=p.get("propR"), t=t)
    ctx.move_to(-48, -236); ctx.line_to(48, -236); ctx.line_to(0, -195); ctx.close_path(); shade(ctx, hexc("e63946"))
    ctx.arc(0, -200, 13, 0, TAU); shade(ctx, hexc("f6c945"))
    hx, hy = 0, -285
    head_at(ctx, hx, hy + 50, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.save(); ctx.translate(hx + sx * 38, hy - 45); ctx.rotate(sx * 0.4)
        rrect(ctx, -9, -28, 18, 32, 9); shade(ctx, hexc("f3e3b5")); ctx.restore()
        ctx.save(); ctx.translate(hx + sx * 70, hy - 15); ctx.rotate(sx * (0.3 + 0.15 * math.sin(t * 3)))
        ellipse(ctx, 0, 0, 30, 14); flat(ctx, white); ellipse(ctx, sx * 4, 0, 18, 7)
        ctx.set_source_rgba(*pink); ctx.fill(); ctx.restore()
    ellipse(ctx, hx, hy, 64, 58); shade(ctx, white, light=0.0, dark=-0.08)
    ellipse(ctx, hx + 28, hy - 30, 22, 16); ctx.set_source_rgba(*black); ctx.fill()
    eye(ctx, hx - 22, hy - 14, p); eye(ctx, hx + 22, hy - 14, p)
    ellipse(ctx, hx, hy + 30, 52, 32); shade(ctx, pink)
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 18, hy + 22, 6, 8); ctx.set_source_rgba(*hexc("b2506a")); ctx.fill()
    mouth(ctx, hx, hy + 42, p, 0.9)
    ctx.restore()


def draw_pip(ctx, p):
    yel, ora = hexc("ffd84d"), hexc("ff9f1c")
    t = p.get("t", 0)
    leg(ctx, -22, -48, -1, P(p, "legL", (0, 0)), 42, 10, ora, ora, shoe_kind="webbed")
    leg(ctx, 22, -48, 1, P(p, "legR", (0, 0)), 42, 10, ora, ora, shoe_kind="webbed")
    arm(ctx, -58, -150, -1, P(p, "armL", (0.5, 0)), 36, 30, 30, yel, yel, hand="wing", propkind=p.get("propL"), t=t)
    ellipse(ctx, 0, -110, 70, 75); shade(ctx, yel)
    ellipse(ctx, 0, -95, 40, 45); ctx.set_source_rgba(*hexc("fff1a8")); ctx.fill()
    arm(ctx, 58, -150, 1, P(p, "armR", (0.5, 0)), 36, 30, 30, yel, yel, hand="wing", propkind=p.get("propR"), t=t)
    for d in (-1, 1):
        ctx.move_to(0, -172); ctx.line_to(d * 28, -186); ctx.line_to(d * 28, -158); ctx.close_path()
        flat(ctx, hexc("3a86ff"), lw=3)
    ctx.arc(0, -172, 8, 0, TAU); flat(ctx, hexc("3a86ff"), lw=3)
    hx, hy = 0, -232
    head_at(ctx, hx, hy + 45, P(p, "tilt", 0))
    ctx.arc(hx, hy, 55, 0, TAU); shade(ctx, yel)
    for k in range(3):
        ellipse(ctx, hx - 8 + k * 8, hy - 58, 6, 14); flat(ctx, yel, lw=3)
    eye(ctx, hx - 20, hy - 14, p); eye(ctx, hx + 20, hy - 14, p)
    blush(ctx, hx - 36, hy + 10); blush(ctx, hx + 36, hy + 10)
    m = p.get("mouth", 0)
    ellipse(ctx, hx, hy + 22 + m * 16, 30, 11); shade(ctx, hexc("e07a00"))
    if m > 0.08:
        ellipse(ctx, hx, hy + 20 + m * 8, 20, 4 + m * 8); ctx.set_source_rgba(*hexc("8a1c2b")); ctx.fill()
    ellipse(ctx, hx, hy + 12, 36, 13); shade(ctx, ora)
    ctx.restore()


def draw_rosie(ctx, p):
    pink, dark, green = hexc("ffb3c6"), hexc("f08ca8"), hexc("4caf50")
    t = p.get("t", 0)
    ctx.set_source_rgba(*OUT); ctx.set_line_width(9)
    ctx.move_to(60, -110); ctx.curve_to(110, -120, 110, -160, 90, -150); ctx.curve_to(70, -140, 95, -120, 115, -135)
    ctx.stroke_preserve(); ctx.set_source_rgba(*pink); ctx.set_line_width(5); ctx.stroke()
    leg(ctx, -28, -88, -1, P(p, "legL", (0, 0)), 80, 30, pink, hexc("8a5a44"))
    leg(ctx, 28, -88, 1, P(p, "legR", (0, 0)), 80, 30, pink, hexc("8a5a44"))
    arm(ctx, -64, -178, -1, P(p, "armL", (0.35, 0)), 36, 32, 26, pink, pink, propkind=p.get("propL"), t=t)
    ellipse(ctx, 0, -130, 75, 80); shade(ctx, pink)
    ctx.save(); ellipse(ctx, 0, -130, 75, 80); ctx.clip()
    rrect(ctx, -80, -120, 160, 120, 0); ctx.set_source_rgba(*green); ctx.fill()
    rrect(ctx, -38, -165, 76, 60, 10); ctx.fill(); ctx.restore()
    ellipse(ctx, 0, -130, 75, 80); ctx.set_source_rgba(*OUT); ctx.set_line_width(LW); ctx.stroke()
    for sx in (-1, 1):
        ctx.arc(sx * 26, -150, 6, 0, TAU); flat(ctx, hexc("f6c945"), lw=2)
    arm(ctx, 64, -178, 1, P(p, "armR", (0.35, 0)), 36, 32, 26, pink, pink, propkind=p.get("propR"), t=t)
    hx, hy = 0, -248
    head_at(ctx, hx, hy + 50, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.save(); ctx.translate(hx + sx * 40, hy - 45); ctx.rotate(sx * (0.35 + 0.1 * math.sin(t * 3)))
        ctx.move_to(-18, 10); ctx.line_to(0, -30); ctx.line_to(18, 10); ctx.close_path(); shade(ctx, dark); ctx.restore()
    ctx.arc(hx, hy, 62, 0, TAU); shade(ctx, pink)
    eye(ctx, hx - 24, hy - 18, p); eye(ctx, hx + 24, hy - 18, p)
    blush(ctx, hx - 42, hy + 14); blush(ctx, hx + 42, hy + 14)
    ellipse(ctx, hx, hy + 12, 28, 20); shade(ctx, dark)
    for sx in (-1, 1):
        ellipse(ctx, hx + sx * 10, hy + 12, 5, 8); ctx.set_source_rgba(*hexc("b04a6a")); ctx.fill()
    mouth(ctx, hx, hy + 42, p, 0.85)
    ctx.restore()


def draw_fluff(ctx, p):
    wool, face = hexc("fffdf7"), hexc("5c5470")
    t = p.get("t", 0)
    leg(ctx, -26, -84, -1, P(p, "legL", (0, 0)), 76, 20, face, hexc("2d2a3a"))
    leg(ctx, 26, -84, 1, P(p, "legR", (0, 0)), 76, 20, face, hexc("2d2a3a"))
    arm(ctx, -62, -170, -1, P(p, "armL", (0.4, 0)), 34, 30, 20, face, face, propkind=p.get("propL"), t=t)
    for a in [i * math.pi / 5 for i in range(10)]:
        ctx.arc(math.cos(a) * 62, -130 + math.sin(a) * 66, 26, 0, TAU); shade(ctx, wool, lw=3, light=0, dark=-0.07)
    ctx.arc(0, -130, 72, 0, TAU); ctx.set_source_rgba(*wool); ctx.fill()
    arm(ctx, 62, -170, 1, P(p, "armR", (0.4, 0)), 34, 30, 20, face, face, propkind=p.get("propR"), t=t)
    rrect(ctx, -46, -200, 92, 22, 10); shade(ctx, hexc("9b5de5"))
    rrect(ctx, 18, -190, 22, 48, 8); shade(ctx, hexc("9b5de5"))
    hx, hy = 0, -250
    head_at(ctx, hx, hy + 45, P(p, "tilt", 0))
    for sx in (-1, 1):
        ctx.save(); ctx.translate(hx + sx * 46, hy - 8); ctx.rotate(sx * 0.3)
        ellipse(ctx, 0, 0, 26, 11); shade(ctx, face); ctx.restore()
    ellipse(ctx, hx, hy, 44, 52); shade(ctx, face)
    for k in range(5):
        ctx.arc(hx - 32 + k * 16, hy - 48 + (k % 2) * -6, 16, 0, TAU); shade(ctx, wool, lw=3, light=0, dark=-0.07)
    eye(ctx, hx - 17, hy - 6, p, 0.95); eye(ctx, hx + 17, hy - 6, p, 0.95)
    blush(ctx, hx - 28, hy + 16); blush(ctx, hx + 28, hy + 16)
    mouth(ctx, hx, hy + 28, p, 0.8)
    ctx.restore()


CHARACTERS = {
    "lily": dict(fn=draw_lily, name="Lily", kind="girl", height=260),
    "leo": dict(fn=draw_leo, name="Leo", kind="boy", height=280),
    "grandpa": dict(fn=draw_grandpa, name="Grandpa Bo", kind="grandpa", height=370),
    "daisy": dict(fn=draw_daisy, name="Daisy the Cow", kind="cow", height=360),
    "pip": dict(fn=draw_pip, name="Pip the Duck", kind="duck", height=300),
    "rosie": dict(fn=draw_rosie, name="Rosie the Pig", kind="pig", height=320),
    "fluff": dict(fn=draw_fluff, name="Fluff the Sheep", kind="sheep", height=310),
}
