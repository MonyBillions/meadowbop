"""Meadowbop cast in 3D (Blender), built from smooth primitives with cartoon outlines.

Each builder returns a rig dict:
  root (feet), body (bounce/lean/squash), head (neck pivot), arms {L,R: (shoulder, elbow, hand)},
  legs {L,R: hip}, lids [eyelids], pupils [..], mouth_open, mouth_closed, props {name: obj}, height
Camera looks along +Y, characters face -Y.
"""
import math
from b3d import mat, sphere, capsule, cone, box, torus, empty

OUT = 0.010


def face_y(R, x, z):
    return -math.sqrt(max(R * R - x * x - z * z, 0.0001))


def add_eyes(head, R, ex, ez, er, skin, rig, look_scale=1.0):
    W, K, Wh = mat("ffffff", 0.15), mat("1c1410", 0.08), mat("ffffff", 0.1, emit=2.0)
    for sx in (-1, 1):
        x = sx * ex
        y = face_y(R, x, ez) + er * 0.25
        sphere(f"{head.name}_eye{sx}", (x, y, ez), er, W, scale=(1, 0.55, 1.25), parent=head, outline=OUT * 0.6)
        p = sphere(f"{head.name}_pupil{sx}", (x, y - er * 0.42, ez - er * 0.1), er * 0.62, K, scale=(1, 0.5, 1.2),
                   parent=head, outline=0)
        sphere(f"{head.name}_hi{sx}", (x + er * 0.25, y - er * 0.62, ez + er * 0.28), er * 0.2, Wh, parent=head, outline=0)
        lid = sphere(f"{head.name}_lid{sx}", (x, y + er * 0.02, ez), er * 1.08, skin, scale=(1.05, 0.62, 1.3),
                     parent=head, outline=0)
        lid.hide_render = True
        rig["lids"].append(lid)
        rig["pupils"].append((p, p.location.copy()))


def add_mouth(head, R, mz, mw, rig, color="7a1626"):
    y = face_y(R, 0, mz)
    mo = sphere(f"{head.name}_mouthO", (0, y + 0.006, mz), mw, mat(color, 0.4), scale=(1.35, 0.3, 0.55), parent=head, outline=0)
    sphere(f"{head.name}_tongue", (0, y - mw * 0.05, mz - mw * 0.35), mw * 0.55, mat("ff7b8a", 0.4),
           scale=(1, 0.3, 0.5), parent=mo, outline=0)
    mc = torus(f"{head.name}_smile", (0, y - 0.004, mz + mw * 0.35), mw * 0.85, mw * 0.12, mat("3b1a14", 0.4),
               parent=head, rot=(math.radians(90), 0, math.radians(180)), arc=math.radians(150))
    rig["mouth_open"], rig["mouth_closed"] = mo, mc


def add_blush(head, R, x, z, r):
    for sx in (-1, 1):
        sphere(f"{head.name}_blush{sx}", (sx * x, face_y(R, sx * x, z) + 0.006, z), r, mat("ff7f9e", 0.6),
               scale=(1, 0.2, 0.6), parent=head, outline=0)


def arm(name, parent, side, loc, L1, L2, r, sleeve, handm, hand="hand", rig=None):
    sh = empty(f"{name}_sh{side}", loc, parent)
    capsule(f"{name}_up{side}", (0, 0, 0), (0, 0, -L1), r, sleeve, parent=sh, outline=OUT)
    el = empty(f"{name}_el{side}", (0, 0, -L1), sh)
    capsule(f"{name}_lo{side}", (0, 0, 0), (0, 0, -L2), r * 0.88, sleeve if hand == "wing" else handm, parent=el, outline=OUT)
    hd = empty(f"{name}_hand{side}", (0, 0, -L2), el)
    if hand == "hand":
        sphere(f"{name}_palm{side}", (0, 0, -r * 0.4), r * 1.3, handm, parent=hd, outline=OUT, seg=24)
    elif hand == "hoof":
        sphere(f"{name}_hoof{side}", (0, 0, -r * 0.3), r * 1.15, mat("2d2a2a", 0.4), parent=hd, outline=OUT, seg=24)
    rig["arms"]["L" if side < 0 else "R"] = (sh, el, hd)
    return sh


def leg(name, parent, side, loc, L, r, color, shoe, kind="shoe", rig=None):
    hip = empty(f"{name}_hip{side}", loc, parent)
    capsule(f"{name}_leg{side}", (0, 0, 0), (0, 0, -L), r, color, parent=hip, outline=OUT)
    if kind == "shoe":
        sphere(f"{name}_shoe{side}", (0, -r * 0.6, -L - r * 0.2), r * 1.45, shoe, scale=(1, 1.45, 0.75), parent=hip, outline=OUT)
    elif kind == "hoof":
        cone(f"{name}_hoofL{side}", (0, 0, -L - r * 0.3), r * 1.15, r * 1.05, r * 0.8, shoe, parent=hip, outline=OUT)
    elif kind == "web":
        sphere(f"{name}_foot{side}", (0, -r * 1.2, -L), r * 2.2, shoe, scale=(1, 1.5, 0.35), parent=hip, outline=OUT)
    rig["legs"]["L" if side < 0 else "R"] = hip


def props_for(hand, rig, name):
    """Small props parented to the right hand, hidden by default."""
    P = {}
    g = empty(f"{name}_tb", (0, 0, 0), hand)
    capsule(f"{name}_tbh", (0, 0, 0), (0, 0, 0.22), 0.012, mat("3a86ff", 0.3), parent=g, outline=0.004)
    box(f"{name}_tbb", (0, -0.01, 0.24), (0.03, 0.02, 0.05), mat("ffffff", 0.3), parent=g, bevel=0.005)
    sphere(f"{name}_foam", (0, -0.03, 0.27), 0.03, mat("ffffff", 0.2), parent=g, outline=0)
    P["toothbrush"] = g
    g = empty(f"{name}_sp", (0, 0, 0), hand)
    capsule(f"{name}_sph", (0, 0, 0), (0, 0, 0.16), 0.01, mat("d9d9e0", 0.2), parent=g, outline=0.004)
    sphere(f"{name}_spb", (0, 0, 0.19), 0.035, mat("d9d9e0", 0.2), scale=(1, 0.5, 1.3), parent=g, outline=0.004)
    P["spoon"] = g
    g = empty(f"{name}_cup", (0, 0, 0), hand)
    cone(f"{name}_cupb", (0, 0, 0.06), 0.05, 0.06, 0.12, mat("ff8fab", 0.4), parent=g, outline=0.004)
    P["cup"] = g
    g = empty(f"{name}_book", (0, 0, 0), hand)
    box(f"{name}_bk", (0, -0.03, 0.08), (0.2, 0.03, 0.15), mat("ef476f", 0.5), parent=g, bevel=0.008)
    P["book"] = g
    g = empty(f"{name}_ball", (0, 0, 0), hand)
    sphere(f"{name}_bl", (0, -0.02, 0.12), 0.11, mat("ff595e", 0.35), parent=g, outline=0.006)
    P["ball"] = g
    g = empty(f"{name}_teddy", (0, 0, 0), hand)
    sphere(f"{name}_tdb", (0, -0.05, 0.1), 0.09, mat("b07d56", 0.7), parent=g, outline=0.005)
    sphere(f"{name}_tdh", (0, -0.05, 0.22), 0.07, mat("b07d56", 0.7), parent=g, outline=0.005)
    P["teddy"] = g
    g = empty(f"{name}_flower", (0, 0, 0), hand)
    capsule(f"{name}_fs", (0, 0, 0), (0, 0, 0.2), 0.008, mat("43a047", 0.5), parent=g, outline=0)
    for k in range(6):
        a = k * math.tau / 6
        sphere(f"{name}_fp{k}", (0.03 * math.cos(a), -0.01, 0.22 + 0.03 * math.sin(a)), 0.022, mat("ff8fab", 0.5), parent=g, outline=0)
    sphere(f"{name}_fc", (0, -0.02, 0.22), 0.02, mat("ffd23f", 0.4), parent=g, outline=0)
    P["flower"] = g
    for o in P.values():
        o.hide_render = True
        for ch in o.children_recursive:
            ch.hide_render = True
    rig["props"] = P


def new_rig(name, x, height):
    root = empty(f"{name}_root", (x, 0, 0))
    body = empty(f"{name}_body", (0, 0, 0), root)
    return dict(name=name, root=root, body=body, arms={}, legs={}, lids=[], pupils=[], props={}, height=height)


# ------------------------------------------------------------------ humans
def build_lily(x=0, name="lily"):
    rig = new_rig(name, x, 1.15)
    skin, dress, hair = mat("6b3e26", 0.5, sss=0.15), mat("ffd23f", 0.6), mat("2b1b14", 0.8)
    b = rig["body"]
    leg(name, b, -1, (-0.08, 0, 0.42), 0.34, 0.045, skin, mat("e94f87", 0.4), rig=rig)
    leg(name, b, 1, (0.08, 0, 0.42), 0.34, 0.045, skin, mat("e94f87", 0.4), rig=rig)
    cone(f"{name}_dress", (0, 0, 0.56), 0.28, 0.13, 0.36, dress, parent=b)
    for k in range(4):
        sphere(f"{name}_dot{k}", (-0.12 + k * 0.08, -0.215, 0.47), 0.018, mat("ffffff", 0.4), scale=(1, 0.4, 1), parent=b, outline=0)
    arm(name, b, -1, (-0.15, 0, 0.71), 0.15, 0.14, 0.04, dress, skin, rig=rig)
    arm(name, b, 1, (0.15, 0, 0.71), 0.15, 0.14, 0.04, dress, skin, rig=rig)
    head = empty(f"{name}_head", (0, 0, 0.76), b); rig["head"] = head
    R = 0.24
    sphere(f"{name}_neck", (0, 0, 0.0), 0.05, skin, parent=head, outline=0)
    sphere(f"{name}_skull", (0, 0, R * 0.95), R, skin, parent=head)
    sphere(f"{name}_hair", (0, 0.03, R * 1.05), R * 1.04, hair, scale=(1, 1, 0.92), parent=head)
    for sx in (-1, 1):
        sphere(f"{name}_puff{sx}", (sx * 0.24, 0.02, R * 1.65), 0.12, hair, parent=head)
        sphere(f"{name}_bow{sx}", (sx * 0.17, -0.06, R * 1.75), 0.05, mat("ff5fa2", 0.4), scale=(1.6, 0.6, 0.8), parent=head)
    hz = R * 0.95
    add_eyes(head, R, 0.08, 0.0, 0.045, skin, rig)
    add_blush(head, R, 0.14, -0.07, 0.035)
    add_mouth(head, R, -0.13, 0.042, rig)
    sphere(f"{name}_nose", (0, face_y(R, 0, -0.04) - 0.01, -0.04 + hz), 0.025, skin, parent=head, outline=0)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


def _fix_face_offsets(head, R, hz):
    """Face features were computed for a sphere centred at z=0; shift z by hz."""
    for o in head.children:
        if any(t in o.name for t in ("_eye", "_pupil", "_hi", "_lid", "_blush", "_mouthO", "_smile", "_glass")):
            o.location.z += hz


def build_leo(x=0, name="leo"):
    rig = new_rig(name, x, 1.22)
    skin, shirt, shorts = mat("c68642", 0.5, sss=0.15), mat("2ec4b6", 0.6), mat("3a6ea5", 0.6)
    b = rig["body"]
    leg(name, b, -1, (-0.08, 0, 0.42), 0.36, 0.05, skin, mat("ff595e", 0.4), rig=rig)
    leg(name, b, 1, (0.08, 0, 0.42), 0.36, 0.05, skin, mat("ff595e", 0.4), rig=rig)
    sphere(f"{name}_shorts", (0, 0, 0.45), 0.17, shorts, scale=(1.05, 0.85, 0.55), parent=b)
    sphere(f"{name}_torso", (0, 0, 0.6), 0.18, shirt, scale=(1, 0.8, 1.05), parent=b)
    sphere(f"{name}_star", (0, -0.145, 0.62), 0.04, mat("ffd23f", 0.4), scale=(1, 0.3, 1), parent=b, outline=0)
    arm(name, b, -1, (-0.17, 0, 0.73), 0.16, 0.15, 0.045, shirt, skin, rig=rig)
    arm(name, b, 1, (0.17, 0, 0.73), 0.16, 0.15, 0.045, shirt, skin, rig=rig)
    head = empty(f"{name}_head", (0, 0, 0.78), b); rig["head"] = head
    R = 0.25; hz = R * 0.95
    sphere(f"{name}_skull", (0, 0, hz), R, skin, parent=head)
    for k in range(14):
        a = math.pi * (0.05 + k * 0.065)
        sphere(f"{name}_curl{k}", (R * 0.98 * math.cos(a), 0.05, hz + R * 0.9 * math.sin(a)), 0.07, mat("2b1b14", 0.8), parent=head)
    sphere(f"{name}_hairtop", (0, 0.04, hz + 0.1), R * 0.98, mat("2b1b14", 0.8), scale=(1, 1, 0.75), parent=head)
    for sx in (-1, 1):
        sphere(f"{name}_ear{sx}", (sx * R * 0.98, 0.0, hz), 0.05, skin, parent=head)
    add_eyes(head, R, 0.085, 0.0, 0.045, skin, rig)
    for sx in (-1, 1):
        torus(f"{name}_glass{sx}", (sx * 0.085, face_y(R, 0.085, 0) - 0.02, 0), 0.06, 0.006, mat("3b2a20", 0.3),
              parent=head, rot=(math.radians(90), 0, 0))
    add_blush(head, R, 0.15, -0.07, 0.035)
    add_mouth(head, R, -0.13, 0.044, rig)
    sphere(f"{name}_nose", (0, face_y(R, 0, -0.04) - 0.01, -0.04 + hz), 0.026, skin, parent=head, outline=0)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


def build_grandpa(x=0, name="grandpa"):
    rig = new_rig(name, x, 1.75)
    skin, shirt, denim = mat("8d5a3b", 0.5, sss=0.15), mat("e63946", 0.6), mat("3a6ea5", 0.6)
    b = rig["body"]
    leg(name, b, -1, (-0.12, 0, 0.62), 0.55, 0.08, denim, mat("6b4226", 0.5), rig=rig)
    leg(name, b, 1, (0.12, 0, 0.62), 0.55, 0.08, denim, mat("6b4226", 0.5), rig=rig)
    sphere(f"{name}_torso", (0, 0, 0.9), 0.3, shirt, scale=(1, 0.8, 1.15), parent=b)
    sphere(f"{name}_bib", (0, -0.03, 0.8), 0.27, denim, scale=(0.9, 0.82, 0.8), parent=b)
    arm(name, b, -1, (-0.28, 0, 1.12), 0.25, 0.23, 0.065, shirt, skin, rig=rig)
    arm(name, b, 1, (0.28, 0, 1.12), 0.25, 0.23, 0.065, shirt, skin, rig=rig)
    head = empty(f"{name}_head", (0, 0, 1.2), b); rig["head"] = head
    R = 0.27; hz = R * 0.95
    sphere(f"{name}_skull", (0, 0, hz), R, skin, parent=head)
    sphere(f"{name}_beard", (0, -0.06, hz - 0.12), R * 0.85, mat("f4f1ea", 0.9), scale=(1, 0.8, 0.75), parent=head)
    sphere(f"{name}_nose", (0, -R - 0.02, hz - 0.03), 0.06, mat("a8694a", 0.5), parent=head)
    for sx in (-1, 1):
        sphere(f"{name}_brow{sx}", (sx * 0.1, face_y(R, 0.1, 0.12) - 0.02, hz + 0.12), 0.05, mat("f4f1ea", 0.9),
               scale=(1.4, 0.6, 0.5), parent=head)
        sphere(f"{name}_mous{sx}", (sx * 0.07, -R + 0.0, hz - 0.08), 0.06, mat("f4f1ea", 0.9), scale=(1.4, 0.7, 0.6), parent=head)
    cone(f"{name}_brim", (0, 0, hz + 0.2), 0.48, 0.48, 0.03, mat("f2c14e", 0.7), parent=head)
    cone(f"{name}_crown", (0, 0, hz + 0.31), 0.24, 0.22, 0.2, mat("f2c14e", 0.7), parent=head)
    cone(f"{name}_band", (0, 0, hz + 0.25), 0.245, 0.245, 0.05, mat("e63946", 0.5), parent=head)
    add_eyes(head, R, 0.09, 0.04, 0.045, skin, rig)
    add_mouth(head, R, -0.15, 0.045, rig)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


# ------------------------------------------------------------------ animals
def build_pip(x=0, name="pip"):
    rig = new_rig(name, x, 1.0)
    yel, ora = mat("ffd84d", 0.5), mat("ff9f1c", 0.45)
    b = rig["body"]
    leg(name, b, -1, (-0.09, 0, 0.18), 0.15, 0.025, ora, ora, kind="web", rig=rig)
    leg(name, b, 1, (0.09, 0, 0.18), 0.15, 0.025, ora, ora, kind="web", rig=rig)
    sphere(f"{name}_body", (0, 0, 0.42), 0.28, yel, scale=(1, 0.9, 1.05), parent=b)
    sphere(f"{name}_belly", (0, -0.12, 0.38), 0.19, mat("fff1a8", 0.6), scale=(1, 0.7, 1.1), parent=b, outline=0)
    arm(name, b, -1, (-0.25, 0, 0.55), 0.13, 0.11, 0.07, yel, yel, hand="wing", rig=rig)
    arm(name, b, 1, (0.25, 0, 0.55), 0.13, 0.11, 0.07, yel, yel, hand="wing", rig=rig)
    sphere(f"{name}_bow", (0, -0.2, 0.66), 0.06, mat("3a86ff", 0.4), scale=(2.0, 0.6, 0.9), parent=b)
    head = empty(f"{name}_head", (0, 0, 0.68), b); rig["head"] = head
    R = 0.22; hz = R * 0.95
    sphere(f"{name}_skull", (0, 0, hz), R, yel, parent=head)
    for k in range(3):
        sphere(f"{name}_tuft{k}", (-0.03 + k * 0.03, 0.02, hz + R + 0.03), 0.03, yel, scale=(0.7, 0.7, 1.6), parent=head)
    add_eyes(head, R, 0.08, 0.05, 0.048, yel, rig)
    add_blush(head, R, 0.15, -0.03, 0.035)
    sphere(f"{name}_beakU", (0, -R - 0.03, -0.04), 0.11, ora, scale=(1, 0.75, 0.38), parent=head)
    lo = sphere(f"{name}_beakL", (0, -R - 0.02, -0.08), 0.1, mat("e07a00", 0.45), scale=(1, 0.7, 0.3), parent=head)
    rig["beak"] = (lo, lo.location.copy())
    sphere(f"{name}_mouthIn", (0, -R - 0.01, -0.065), 0.07, mat("7a1626", 0.4), scale=(1, 0.5, 0.3), parent=head, outline=0)
    _fix_face_offsets(head, R, hz)
    for o in head.children:
        if "_beak" in o.name or "_mouthIn" in o.name:
            o.location.z += hz
    rig["beak"] = (lo, lo.location.copy())
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


def build_rosie(x=0, name="rosie"):
    rig = new_rig(name, x, 1.05)
    pink, dark, green = mat("ffb3c6", 0.5, sss=0.1), mat("f08ca8", 0.5), mat("4caf50", 0.6)
    b = rig["body"]
    leg(name, b, -1, (-0.1, 0, 0.3), 0.24, 0.06, pink, mat("8a5a44", 0.5), kind="hoof", rig=rig)
    leg(name, b, 1, (0.1, 0, 0.3), 0.24, 0.06, pink, mat("8a5a44", 0.5), kind="hoof", rig=rig)
    sphere(f"{name}_body", (0, 0, 0.47), 0.28, pink, scale=(1, 0.9, 1.0), parent=b)
    sphere(f"{name}_overall", (0, -0.03, 0.4), 0.27, green, scale=(1.02, 0.9, 0.7), parent=b)
    torus(f"{name}_tail", (0, 0.27, 0.45), 0.05, 0.015, pink, parent=b, rot=(0, math.radians(90), 0))
    arm(name, b, -1, (-0.25, 0, 0.6), 0.13, 0.12, 0.055, pink, pink, hand="hoof", rig=rig)
    arm(name, b, 1, (0.25, 0, 0.6), 0.13, 0.12, 0.055, pink, pink, hand="hoof", rig=rig)
    head = empty(f"{name}_head", (0, 0, 0.7), b); rig["head"] = head
    R = 0.24; hz = R * 0.95
    sphere(f"{name}_skull", (0, 0, hz), R, pink, parent=head)
    for sx in (-1, 1):
        cone(f"{name}_ear{sx}", (sx * 0.15, 0.02, hz + 0.21), 0.07, 0.0, 0.12, dark, parent=head,
             rot=(0, sx * math.radians(-25), 0))
    cone(f"{name}_snout", (0, -R - 0.02, hz - 0.03), 0.085, 0.08, 0.07, dark, parent=head, rot=(math.radians(90), 0, 0))
    for sx in (-1, 1):
        sphere(f"{name}_nost{sx}", (sx * 0.03, -R - 0.06, hz - 0.03), 0.016, mat("b04a6a", 0.4), scale=(1, 0.4, 1.4), parent=head, outline=0)
    add_eyes(head, R, 0.09, 0.07, 0.045, pink, rig)
    add_blush(head, R, 0.16, -0.03, 0.035)
    add_mouth(head, R, -0.13, 0.04, rig)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


def build_daisy(x=0, name="daisy"):
    rig = new_rig(name, x, 1.35)
    white, black, pink = mat("fbfaf5", 0.6), mat("2d2a2a", 0.5), mat("f7a1b5", 0.5)
    b = rig["body"]
    leg(name, b, -1, (-0.12, 0, 0.36), 0.3, 0.08, white, black, kind="hoof", rig=rig)
    leg(name, b, 1, (0.12, 0, 0.36), 0.3, 0.08, white, black, kind="hoof", rig=rig)
    sphere(f"{name}_body", (0, 0, 0.62), 0.33, white, scale=(1, 0.85, 1.1), parent=b)
    for i, (sx, sz, r) in enumerate([(-0.2, 0.8, 0.12), (0.22, 0.55, 0.14), (-0.1, 0.42, 0.09)]):
        sphere(f"{name}_spot{i}", (sx, -0.22, sz), r, black, scale=(1, 0.4, 0.8), parent=b, outline=0)
    sphere(f"{name}_belly", (0, -0.2, 0.55), 0.18, pink, scale=(1, 0.5, 1.2), parent=b, outline=0)
    arm(name, b, -1, (-0.3, 0, 0.85), 0.17, 0.15, 0.07, white, white, hand="hoof", rig=rig)
    arm(name, b, 1, (0.3, 0, 0.85), 0.17, 0.15, 0.07, white, white, hand="hoof", rig=rig)
    sphere(f"{name}_bell", (0, -0.24, 0.92), 0.05, mat("f6c945", 0.3), parent=b)
    head = empty(f"{name}_head", (0, 0, 0.95), b); rig["head"] = head
    R = 0.26; hz = R * 0.95
    sphere(f"{name}_skull", (0, 0, hz), R, white, scale=(1.05, 1, 0.95), parent=head)
    sphere(f"{name}_muzzle", (0, -R * 0.75, hz - 0.1), 0.17, pink, scale=(1.25, 0.8, 0.75), parent=head)
    for sx in (-1, 1):
        sphere(f"{name}_nost{sx}", (sx * 0.06, -R * 0.75 - 0.13, hz - 0.08), 0.022, mat("b2506a", 0.4), scale=(1, 0.4, 1.3), parent=head, outline=0)
        cone(f"{name}_horn{sx}", (sx * 0.14, 0.0, hz + 0.25), 0.035, 0.015, 0.12, mat("f3e3b5", 0.5), parent=head,
             rot=(0, sx * math.radians(-30), 0))
        sphere(f"{name}_ear{sx}", (sx * 0.3, 0.0, hz + 0.08), 0.1, white, scale=(1.4, 0.6, 0.55), parent=head)
    sphere(f"{name}_hspot", (0.12, -0.12, hz + 0.16), 0.08, black, scale=(1, 0.5, 0.7), parent=head, outline=0)
    add_eyes(head, R, 0.1, 0.06, 0.05, white, rig)
    add_mouth(head, R * 1.18, -0.17, 0.045, rig)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


def build_fluff(x=0, name="fluff"):
    rig = new_rig(name, x, 1.05)
    wool, face = mat("fffdf7", 0.9), mat("5c5470", 0.55)
    b = rig["body"]
    leg(name, b, -1, (-0.1, 0, 0.3), 0.26, 0.04, face, mat("2d2a3a", 0.5), kind="hoof", rig=rig)
    leg(name, b, 1, (0.1, 0, 0.3), 0.26, 0.04, face, mat("2d2a3a", 0.5), kind="hoof", rig=rig)
    sphere(f"{name}_core", (0, 0, 0.48), 0.27, wool, parent=b)
    for k in range(12):
        a = k * math.tau / 12
        sphere(f"{name}_puff{k}", (0.24 * math.cos(a), 0.02 * math.sin(a * 3), 0.48 + 0.25 * math.sin(a)), 0.11, wool, parent=b)
    for k in range(6):
        a = k * math.tau / 6
        sphere(f"{name}_fp{k}", (0.12 * math.cos(a), -0.2, 0.48 + 0.13 * math.sin(a)), 0.1, wool, parent=b)
    arm(name, b, -1, (-0.26, 0, 0.6), 0.12, 0.11, 0.035, face, face, hand="hoof", rig=rig)
    arm(name, b, 1, (0.26, 0, 0.6), 0.12, 0.11, 0.035, face, face, hand="hoof", rig=rig)
    sphere(f"{name}_scarf", (0, -0.02, 0.73), 0.17, mat("9b5de5", 0.6), scale=(1, 1, 0.35), parent=b)
    head = empty(f"{name}_head", (0, 0, 0.74), b); rig["head"] = head
    R = 0.2; hz = R * 1.0
    sphere(f"{name}_skull", (0, 0, hz), R, face, scale=(1, 1, 1.15), parent=head)
    for k in range(5):
        sphere(f"{name}_tuft{k}", (-0.12 + k * 0.06, 0.02, hz + 0.21 + (k % 2) * 0.03), 0.07, wool, parent=head)
    for sx in (-1, 1):
        sphere(f"{name}_ear{sx}", (sx * 0.24, 0.02, hz + 0.02), 0.08, face, scale=(1.5, 0.5, 0.6), parent=head)
    add_eyes(head, R, 0.075, 0.03, 0.045, face, rig)
    add_blush(head, R, 0.12, -0.06, 0.03)
    add_mouth(head, R, -0.12, 0.035, rig)
    _fix_face_offsets(head, R, hz)
    props_for(rig["arms"]["R"][2], rig, name)
    return rig


BUILDERS = dict(lily=build_lily, leo=build_leo, grandpa=build_grandpa, pip=build_pip,
                rosie=build_rosie, daisy=build_daisy, fluff=build_fluff)
