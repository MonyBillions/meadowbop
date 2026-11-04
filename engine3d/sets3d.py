"""3D sets. Characters stand around y=0, x in [-2, 2]; back wall at y=2.6; camera on -Y side.
Each set lives in its own collection so it can be toggled per section."""
import math, random
import bpy
from b3d import mat, sphere, capsule, cone, box, torus, empty

SETS = ["bedroom", "bedroom_night", "bathroom", "kitchen", "park", "classroom", "meadow", "beach"]
OUT = 0.0


def _coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    lc = bpy.context.view_layer.layer_collection.children[name]
    bpy.context.view_layer.active_layer_collection = lc
    return c


def _room(wall, floor, night=False):
    box("floor", (0, -4, -0.05), (20, 14, 0.1), mat(floor, 0.6), bevel=0)
    box("backwall", (0, 2.7, 4.5), (16, 0.2, 9.2), mat(wall, 0.85), bevel=0)
    for sx in (-1, 1):
        box(f"sidewall{sx}", (sx * 4.2, -3.5, 4.5), (0.2, 12.5, 9.2), mat(wall, 0.85), bevel=0)
    box("skirting", (0, 2.58, 0.06), (16, 0.06, 0.12), mat("ffffff", 0.4), bevel=0)


def _window(x, z, w, h, night=False, y=2.58):
    sky = "1d2b6b" if night else "8fd3ff"
    box("glass", (x, y + 0.03, z), (w, 0.02, h), mat(sky, 0.3, emit=1.2 if not night else 0.6), bevel=0)
    for dx, dz, sw, sh in [(0, h / 2, w + 0.14, 0.08), (0, -h / 2, w + 0.14, 0.08), (-w / 2, 0, 0.08, h), (w / 2, 0, 0.08, h),
                           (0, 0, w, 0.05), (0, 0, 0.05, h)]:
        box("wframe", (x + dx, y - 0.02, z + dz), (sw, 0.08, sh), mat("ffffff", 0.4), bevel=0.01)
    for sx in (-1, 1):
        box("curtain", (x + sx * (w / 2 + 0.2), y - 0.08, z), (0.35, 0.06, h + 0.4), mat("ff8fab", 0.8), bevel=0.05)
    if night:
        sphere("moon", (x + w * 0.2, y + 0.01, z + h * 0.2), 0.18, mat("fff3b0", 0.5, emit=3.0), scale=(1, 0.1, 1), outline=0)
    else:
        sphere("cloud", (x - w * 0.2, y + 0.01, z + h * 0.15), 0.15, mat("ffffff", 0.5, emit=1.5), scale=(1.8, 0.1, 0.8), outline=0)


def bedroom(night=False):
    _room("27306b" if night else "bde0fe", "d9a66b")
    _window(0.2, 2.1, 1.6, 1.2, night)
    box("bedframe", (-2.6, 1.4, 0.3), (1.3, 2.2, 0.5), mat("b07d56", 0.6), bevel=0.06)
    box("mattress", (-2.6, 1.4, 0.62), (1.2, 2.1, 0.22), mat("ffffff", 0.7), bevel=0.08)
    box("blanket", (-2.6, 1.1, 0.75), (1.25, 1.5, 0.08), mat("ffafcc" if not night else "4361ee", 0.8), bevel=0.04)
    box("pillow", (-2.6, 2.15, 0.82), (0.8, 0.4, 0.18), mat("ffffff", 0.7), bevel=0.08)
    box("headboard", (-2.6, 2.5, 0.9), (1.4, 0.12, 1.2), mat("b07d56", 0.6), bevel=0.06)
    box("shelf", (2.4, 2.5, 1.6), (1.6, 0.3, 0.06), mat("b07d56", 0.6), bevel=0.01)
    for i, (c, sz) in enumerate([("ff595e", 0.25), ("ffca3a", 0.2), ("6a4c93", 0.3)]):
        box(f"toy{i}", (1.9 + i * 0.5, 2.5, 1.63 + sz / 2), (sz, sz, sz), mat(c, 0.5), bevel=0.03)
    sphere("toyball", (2.9, 2.5, 1.78), 0.13, mat("8ac926", 0.4))
    cone("rug", (0, 0.2, 0.005), 1.8, 1.8, 0.01, mat("cdb4db", 0.9), scale=(1.3, 0.8, 1))
    capsule("lamppole", (3.3, 1.8, 0), (3.3, 1.8, 1.3), 0.03, mat("b07d56", 0.5))
    cone("lampshade", (3.3, 1.8, 1.4), 0.28, 0.15, 0.3, mat("ffd166", 0.6, emit=2.5 if night else 0.3))
    if night:
        bpy.ops.object.light_add(type="POINT", location=(3.3, 1.6, 1.4)); L = bpy.context.object
        L.data.energy = 120; L.data.color = (1, 0.8, 0.5); L.data.shadow_soft_size = 0.3
    for i in range(3):
        sphere(f"star{i}", (-1.5 + i * 1.2, 2.58, 3.4 + (i % 2) * 0.3), 0.08, mat("fff3b0", 0.5, emit=2.0 if night else 0.0),
               scale=(1, 0.2, 1), outline=0)


def bathroom():
    _room("caf0f8", "90e0ef")
    for i in range(12):
        box(f"tileline{i}", (-4 + i * 0.7, 2.59, 1.6), (0.02, 0.01, 3.2), mat("ffffff", 0.3), bevel=0)
    _window(2.6, 2.4, 1.0, 0.8)
    box("tub", (-2.6, 1.4, 0.35), (1.6, 1.0, 0.7), mat("ffffff", 0.25), bevel=0.2)
    r = random.Random(3)
    for i in range(14):
        sphere(f"bubble{i}", (-2.6 + r.uniform(-0.7, 0.7), 1.4 + r.uniform(-0.4, 0.4), 0.75 + r.uniform(0, 0.15)),
               r.uniform(0.08, 0.16), mat("f1faff", 0.15))
    capsule("sinkpole", (0.4, 2.2, 0), (0.4, 2.2, 0.8), 0.1, mat("ffffff", 0.3))
    cone("sink", (0.4, 2.15, 0.88), 0.32, 0.22, 0.16, mat("ffffff", 0.25), rot=(math.pi, 0, 0))
    capsule("tap", (0.4, 2.45, 0.95), (0.4, 2.3, 1.05), 0.025, mat("adb5bd", 0.2))
    box("mirror", (0.4, 2.58, 1.7), (0.8, 0.04, 0.9), mat("e0fbfc", 0.05, emit=0.4), bevel=0.06)
    box("towelbar", (1.6, 2.55, 1.3), (0.7, 0.04, 0.04), mat("adb5bd", 0.2), bevel=0)
    box("towel", (1.6, 2.5, 1.05), (0.6, 0.06, 0.55), mat("ffafcc", 0.9), bevel=0.04)
    cone("bathmat", (-0.8, 0.6, 0.005), 0.6, 0.6, 0.01, mat("ffd6a5", 0.9), scale=(1.4, 0.7, 1))


def kitchen():
    _room("fff3b0", "e9c46a")
    _window(-2.2, 2.2, 1.4, 1.0)
    for x in (0.6, 1.6):
        box("cabinet", (x, 2.45, 2.4), (0.9, 0.35, 0.8), mat("80ed99", 0.5), bevel=0.04)
        sphere("knob", (x + 0.3, 2.25, 2.3), 0.035, mat("ffffff", 0.3))
    box("counter", (1.1, 2.3, 0.45), (2.2, 0.6, 0.9), mat("80ed99", 0.5), bevel=0.04)
    box("countertop", (1.1, 2.3, 0.92), (2.3, 0.65, 0.06), mat("f4f1ea", 0.3), bevel=0.01)
    box("fridge", (3.2, 2.1, 1.0), (0.9, 0.8, 2.0), mat("e0fbfc", 0.25), bevel=0.1)
    capsule("fridgeh", (2.8, 1.68, 0.9), (2.8, 1.68, 1.4), 0.025, mat("adb5bd", 0.2))
    # table in front of characters, a little to the side so it does not hide them
    box("tabletop", (-2.4, 0.6, 0.62), (1.4, 0.9, 0.06), mat("b07d56", 0.5), bevel=0.02)
    for dx in (-0.6, 0.6):
        for dy in (-0.35, 0.35):
            capsule("tleg", (-2.4 + dx, 0.6 + dy, 0), (-2.4 + dx, 0.6 + dy, 0.6), 0.03, mat("8d5a3b", 0.5))
    cone("bowl", (-2.6, 0.6, 0.7), 0.16, 0.1, 0.1, mat("ff8fab", 0.4), rot=(math.pi, 0, 0))
    for i, c in enumerate(["ff595e", "ffca3a", "8ac926", "ff924c"]):
        sphere(f"fruit{i}", (-2.2 + i * 0.12, 0.75, 0.72), 0.06, mat(c, 0.4))
    cone("plate", (-2.0, 0.45, 0.66), 0.14, 0.14, 0.015, mat("ffffff", 0.3))
    for i in range(3):
        cone(f"pancake{i}", (-2.0, 0.45, 0.68 + i * 0.022), 0.1, 0.1, 0.02, mat("e9a23b", 0.6))


def _ground(col1="8fd16a"):
    box("ground", (0, 10, -0.05), (60, 40, 0.1), mat(col1, 0.85), bevel=0)


def _hills():
    for x, y, r, c in [(-8, 18, 7, "a7dd8a"), (3, 22, 9, "86c86a"), (12, 17, 6, "a7dd8a")]:
        sphere("hill", (x, y, -r * 0.55), r, mat(c, 0.9), scale=(1.6, 1, 1), outline=0)


def _tree(x, y, s=1.0):
    capsule("trunk", (x, y, 0), (x, y, 1.4 * s), 0.12 * s, mat("8d5a3b", 0.7))
    for dx, dz, r in [(0, 1.9, 0.75), (-0.5, 1.5, 0.55), (0.55, 1.55, 0.55), (0, 1.35, 0.5)]:
        sphere("leaves", (x + dx * s, y, dz * s), r * s, mat("52b788", 0.7))


def _flowers(seed, n=60, spread=(-6, 6, -2, 8)):
    r = random.Random(seed)
    for i in range(n):
        x, y = r.uniform(spread[0], spread[1]), r.uniform(spread[2], spread[3])
        if abs(x) < 2.2 and -1.2 < y < 1.0:
            continue
        c = r.choice(["ffffff", "ffd23f", "ff5fa2", "c77dff"])
        sphere(f"flower{i}", (x, y, 0.04), 0.05, mat(c, 0.6), scale=(1, 1, 0.5), outline=0)


def park():
    _ground(); _hills()
    _tree(-3.6, 3.5, 1.3); _tree(4.2, 4.5, 1.1); _tree(-6, 7, 1.4)
    box("slideplat", (2.6, 2.4, 1.2), (0.7, 0.7, 0.08), mat("ff595e", 0.5), bevel=0.02)
    for dx in (-0.3, 0.3):
        for dy in (-0.3, 0.3):
            capsule("slidepost", (2.6 + dx, 2.4 + dy, 0), (2.6 + dx, 2.4 + dy, 1.2), 0.035, mat("adb5bd", 0.3))
    box("slide", (3.5, 2.4, 0.62), (1.9, 0.5, 0.06), mat("ffca3a", 0.4), rot=(0, math.radians(35), 0), bevel=0.02)
    for x in (-2.4, -1.0):
        capsule("swingpost", (x, 3.0, 0), (x, 3.0, 1.9), 0.05, mat("ff924c", 0.5))
    capsule("swingtop", (-2.4, 3.0, 1.9), (-1.0, 3.0, 1.9), 0.05, mat("ff924c", 0.5))
    box("swingseat", (-1.7, 3.0, 0.5), (0.4, 0.2, 0.04), mat("3a86ff", 0.5), bevel=0.01)
    box("path", (0, 0.5, 0.002), (2.4, 30, 0.004), mat("f1dca7", 0.9), rot=(0, 0, math.radians(20)), bevel=0)
    _flowers(11)


def classroom():
    _room("ffe5ec", "caa472")
    box("board", (0, 2.58, 1.9), (3.2, 0.06, 1.4), mat("2d6a4f", 0.7), bevel=0.02)
    box("boardframe", (0, 2.6, 1.9), (3.4, 0.04, 1.6), mat("b07d56", 0.6), bevel=0.02)
    for i, (ch, c) in enumerate(zip("ABC123", ["ffd166", "ffafcc", "a0e7e5", "ffffff", "ffffff", "ffffff"])):
        cu = bpy.data.curves.new(f"t{i}", "FONT"); cu.body = ch; cu.extrude = 0.01; cu.size = 0.55
        o = bpy.data.objects.new(f"txt{i}", cu); bpy.context.collection.objects.link(o)
        o.location = (-1.25 + i * 0.5, 2.54, 1.75 + (0.15 if i < 3 else -0.35)); o.rotation_euler = (math.pi / 2, 0, 0)
        o.data.materials.append(mat(c, 0.6, emit=0.3))
    for i in range(12):
        c = ["ff595e", "ffca3a", "8ac926", "1982c4", "6a4c93"][i % 5]
        cone(f"flag{i}", (-3.6 + i * 0.65, 2.55, 3.2), 0.2, 0.0, 0.3, mat(c, 0.6), rot=(math.pi, 0, 0), seg=3)
    _window(-3.0, 2.0, 0.9, 1.0)
    sphere("clock", (2.8, 2.57, 2.8), 0.3, mat("ffffff", 0.4), scale=(1, 0.15, 1))
    for x in (-2.8, 2.8):
        box("desk", (x, 0.9, 0.55), (1.0, 0.6, 0.05), mat("ff924c", 0.5), bevel=0.02)
        for dx in (-0.4, 0.4):
            capsule("dleg", (x + dx, 0.9, 0), (x + dx, 0.9, 0.53), 0.025, mat("adb5bd", 0.3))


def meadow():
    _ground(); _hills()
    box("barn", (-4.5, 6, 1.4), (3, 2.5, 2.8), mat("c0392b", 0.7), bevel=0.05)
    box("roofL", (-5.3, 6, 3.2), (1.9, 2.7, 0.15), mat("8f2d2d", 0.7), rot=(0, math.radians(35), 0), bevel=0.02)
    box("roofR", (-3.7, 6, 3.2), (1.9, 2.7, 0.15), mat("8f2d2d", 0.7), rot=(0, math.radians(-35), 0), bevel=0.02)
    box("barndoor", (-4.5, 4.72, 0.9), (1.0, 0.05, 1.6), mat("f4f1ea", 0.6), bevel=0.02)
    for x in [i * 0.7 - 5 for i in range(16)]:
        box("post", (x, 2.8, 0.4), (0.1, 0.1, 0.8), mat("f4e1c1", 0.7), bevel=0.02)
    for z in (0.3, 0.6):
        box("rail", (0.3, 2.8, z), (11, 0.06, 0.08), mat("f4e1c1", 0.7), bevel=0.01)
    _tree(4.5, 5, 1.2)
    _flowers(7, 90)


def beach():
    box("sand", (0, 5, -0.05), (60, 20, 0.1), mat("ffe8a3", 0.9), bevel=0)
    box("sea", (0, 22, -0.02), (80, 20, 0.05), mat("2bb8e0", 0.08, emit=0.15), bevel=0)
    capsule("umbpole", (3.2, 2.0, 0), (3.0, 2.0, 2.0), 0.03, mat("ffffff", 0.4))
    cone("umbrella", (3.0, 2.0, 2.05), 1.1, 0.05, 0.4, mat("ff595e", 0.5))
    cone("bucket", (-2.6, 0.8, 0.12), 0.12, 0.16, 0.24, mat("1982c4", 0.4))
    for i in range(4):
        sphere(f"shell{i}", (-3 + i * 1.7, -0.6 + (i % 2) * 0.8, 0.03), 0.06, mat("ff924c", 0.5), scale=(1, 1, 0.5))
    sphere("sandcastle", (-3.2, 1.6, 0.0), 0.35, mat("e9c46a", 0.9), scale=(1, 1, 0.8))


BUILD = dict(bedroom=lambda: bedroom(False), bedroom_night=lambda: bedroom(True), bathroom=bathroom, kitchen=kitchen,
             park=park, classroom=classroom, meadow=meadow, beach=beach)
OUTDOOR = {"park", "meadow", "beach"}


def build_sets(names):
    out = {}
    root = bpy.context.view_layer.active_layer_collection
    for n in names:
        c = _coll("set_" + n)
        BUILD[n]()
        out[n] = c
        bpy.context.view_layer.active_layer_collection = root
    return out
