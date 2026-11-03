"""Action library: maps an action name + musical time to a pose for the rig."""
import math

ACTIONS = ["idle", "groove", "wave", "clap", "dance", "jump", "brush", "eat", "drink", "wash", "stretch",
           "yawn", "sleep", "march", "read", "ball", "point", "hug", "tidy", "spin", "flower", "towel", "teddy"]


def pose_for(action, beat, t, phase=0.0):
    """Return (pose dict, bounce_px, extra) for an action at musical beat (float)."""
    b = beat + phase
    s = math.sin(b * math.pi)          # one hump per beat
    s2 = math.sin(b * math.pi / 2)     # one swing per 2 beats
    p = dict(armL=(0.25 + 0.08 * s2, 0.1), armR=(0.25 - 0.08 * s2, 0.1), legL=(0, 0), legR=(0, 0),
             tilt=0.06 * s2, lean=0.03 * s2, happy=0.5)
    bounce = 10 * abs(s)
    fx = None
    if action == "idle":
        bounce = 4 * abs(s)
    elif action == "groove":
        p["armL"] = (0.5 + 0.25 * s2, 0.6); p["armR"] = (0.5 - 0.25 * s2, 0.6)
        p["legL"] = (6 * max(0, s2), 0); p["legR"] = (6 * max(0, -s2), 0)
    elif action == "wave":
        p["armR"] = (2.3 + 0.2 * math.sin(t * 9), 0.5 * math.sin(t * 9))
        p["tilt"] = 0.1; p["happy"] = 1
    elif action == "clap":
        k = abs(math.cos(b * math.pi))
        p["armL"] = (0.9, -1.5 - 0.5 * k); p["armR"] = (0.9, -1.5 - 0.5 * k)
        p["happy"] = 1; fx = "sparkle" if k > 0.95 else None
    elif action == "dance":
        up = math.sin(b * math.pi / 2) > 0
        p["armL"] = (2.7, 0.3) if up else (0.9, 1.2)
        p["armR"] = (0.9, 1.2) if up else (2.7, 0.3)
        p["legL"] = (18 * max(0, s2), -0.15 * max(0, s2)); p["legR"] = (18 * max(0, -s2), 0.15 * max(0, -s2))
        p["lean"] = 0.08 * s2; p["tilt"] = 0.12 * s2; p["happy"] = 1
        bounce = 16 * abs(s); fx = "notes"
    elif action == "jump":
        p["armL"] = (2.6, 0.2); p["armR"] = (2.6, 0.2); bounce = 45 * abs(s)
        p["legL"] = (10 * abs(s), -0.2); p["legR"] = (10 * abs(s), 0.2); p["happy"] = 1
    elif action == "brush":
        p["armR"] = (0.35, -2.55 + 0.18 * math.sin(t * 22)); p["propR"] = "toothbrush"
        p["armL"] = (0.2, 0.1); p["tilt"] = -0.06; fx = "foam"
    elif action == "eat":
        k = 0.5 + 0.5 * math.sin(b * math.pi)
        p["armR"] = (0.35, -1.0 - 1.5 * k); p["propR"] = "spoon"; p["happy"] = 0.8
    elif action == "drink":
        p["armR"] = (0.4, -2.3); p["propR"] = "cup"; p["tilt"] = -0.15
    elif action == "wash":
        r = 0.25 * math.sin(t * 14)
        p["armL"] = (0.7, -1.9 + r); p["armR"] = (0.7, -1.9 - r); fx = "bubbles"
    elif action == "stretch":
        k = 0.5 + 0.5 * math.sin(b * math.pi / 4)
        p["armL"] = (1.6 + 1.3 * k, 0.2); p["armR"] = (1.6 + 1.3 * k, 0.2)
        p["lean"] = 0.06 * math.sin(b * math.pi / 4); p["happy"] = 0.9
    elif action == "yawn":
        p["armL"] = (2.6, 0.5); p["armR"] = (0.4, -2.4); p["tilt"] = -0.12; p["happy"] = 0.2
    elif action == "sleep":
        p["armL"] = (0.6, -1.4); p["propL"] = "teddy"; p["armR"] = (0.6, -1.6)
        p["tilt"] = 0.25 + 0.03 * math.sin(t * 1.5); p["blink"] = True; bounce = 0; fx = "zzz"
    elif action == "march":
        p["legL"] = (22 * max(0, s2), 0); p["legR"] = (22 * max(0, -s2), 0)
        p["armL"] = (0.5 + 0.6 * s2, 0.5); p["armR"] = (0.5 - 0.6 * s2, 0.5)
    elif action == "read":
        p["armL"] = (0.5, -1.6); p["armR"] = (0.5, -1.6); p["propR"] = "book"; p["tilt"] = 0.1
        p["look"] = 0.5 * math.sin(t * 0.8); bounce = 3 * abs(s)
    elif action == "ball":
        p["armR"] = (0.8 + 0.4 * abs(s), -0.4); p["propR"] = "ball"; bounce = 14 * abs(s)
    elif action == "point":
        p["armR"] = (1.65, 0.0); p["happy"] = 1; p["look"] = 1
    elif action == "hug":
        p["armL"] = (1.1, -1.9); p["armR"] = (1.1, -1.9); p["tilt"] = 0.12; p["happy"] = 1
    elif action == "tidy":
        k = math.sin(b * math.pi / 2)
        p["armR"] = (0.4 + 0.9 * max(0, k), -0.5); p["armL"] = (0.4 + 0.9 * max(0, -k), -0.5)
        p["lean"] = 0.12 * k; p["propR"] = "ball" if k > 0 else None
    elif action == "spin":
        p["armL"] = (1.6, 0.2); p["armR"] = (1.6, 0.2); p["lean"] = 0.18 * math.sin(b * math.pi); p["happy"] = 1
        fx = "sparkle"
    elif action == "flower":
        p["armR"] = (0.6, -1.4); p["propR"] = "flower"; p["happy"] = 1
    elif action == "towel":
        r = 0.3 * math.sin(t * 8)
        p["armL"] = (1.0, -1.7 + r); p["armR"] = (1.0, -1.7 - r); p["propR"] = "towel"
    elif action == "teddy":
        p["armL"] = (0.6, -1.4); p["propL"] = "teddy"; p["armR"] = (0.6, -1.6); p["happy"] = 1
    return p, bounce, fx
