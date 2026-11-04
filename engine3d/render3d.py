"""Render an episode in 3D with Blender (Cycles CPU), frame by frame, resumable in chunks.

python3 render3d.py EPISODE.json OUTDIR --layout land|vert [--fps 12] [--start N --end M] [--samples 8]
Frames -> OUTDIR/frames_<layout>/f_00001.png ; compose3d.py adds karaoke/overlays + audio afterwards.
"""
import json, math, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import bpy
from mathutils import Vector

import music
from actions import pose_for
from b3d import mat
from chars3d import BUILDERS
from sets3d import build_sets, OUTDOOR

ARG = sys.argv


def arg(name, default=None, cast=str):
    return cast(ARG[ARG.index(name) + 1]) if name in ARG else default


def get_song(ep, layout, meta_path):
    import timeline
    full = timeline.full_song(ep, meta_path)
    return full if layout == "land" else timeline.short_song(ep, full)


POS = {1: [0.0], 2: [-0.6, 0.6], 3: [-1.05, 0.0, 1.05], 4: [-1.45, -0.5, 0.5, 1.45], 5: [-1.8, -0.9, 0.0, 0.9, 1.8]}
POS_V = {1: [0.0], 2: [-0.45, 0.45], 3: [-0.75, 0.0, 0.75], 4: [-0.9, -0.3, 0.3, 0.9], 5: [-1.0, -0.5, 0.0, 0.5, 1.0]}


class Show:
    def __init__(self, ep, song, layout, samples):
        self.ep, self.song, self.layout = ep, song, layout
        self.beat = 60.0 / song["bpm"]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        scenes = sorted({s.get("scene") or "meadow" for s in song["sections"]})
        self.sets = build_sets(scenes)
        chars = sorted({c for s in ep["sections"] for c in (s.get("cast") or ep["cast"])} | set(ep["cast"]))
        cc = bpy.data.collections.new("cast"); sc.collection.children.link(cc)
        bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children["cast"]
        self.rigs = {k: BUILDERS[k](0) for k in chars}
        for r in self.rigs.values():
            r["root"].location = (0, 60, 0)
            r["pupil_base"] = [(p, p.location.copy()) for p, _ in r["pupils"]]
        # lights
        bpy.ops.object.light_add(type="SUN", location=(0, 0, 6)); self.sun = bpy.context.object
        self.sun.data.angle = math.radians(10)
        bpy.ops.object.light_add(type="AREA", location=(0, -5, 3.5)); self.fill = bpy.context.object
        self.fill.data.size = 7; self.fill.rotation_euler = (math.radians(62), 0, 0)
        w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
        self.bg = w.node_tree.nodes["Background"]
        # camera
        cam = bpy.data.cameras.new("cam"); self.cam = bpy.data.objects.new("cam", cam); sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        self.tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(self.tgt)
        tc = self.cam.constraints.new("TRACK_TO"); tc.target = self.tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
        cam.sensor_width = 36
        # render settings
        sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
        sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
        sc.cycles.max_bounces = 2; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 1
        sc.cycles.transmission_bounces = 0; sc.cycles.volume_bounces = 0; sc.cycles.caustics_reflective = False
        sc.cycles.caustics_refractive = False; sc.cycles.blur_glossy = 2.0
        sc.cycles.denoiser = "OPENIMAGEDENOISE"; sc.cycles.adaptive_threshold = 0.05
        for k, v in (("denoising_prefilter", "FAST"), ("denoising_quality", "FAST"), ("denoising_input_passes", "RGB_ALBEDO_NORMAL")):
            try:
                setattr(sc.cycles, k, v)
            except Exception as e:
                print("skip", k, e)
        sc.render.threads_mode = "AUTO"
        sc.cycles.transparent_max_bounces = 6; sc.render.use_persistent_data = True
        sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
        sc.view_settings.exposure = 0.0
        if layout == "land":
            sc.render.resolution_x, sc.render.resolution_y = 960, 540
        else:
            sc.render.resolution_x, sc.render.resolution_y = 540, 960
        sc.render.image_settings.file_format = "PNG"
        if os.environ.get("MB_NO_OUTLINE"):
            for o in bpy.data.objects:
                for m in o.modifiers:
                    if m.name == "outline":
                        m.show_render = False
        if os.environ.get("MB_NO_DENOISE"):
            sc.cycles.use_denoising = False
        rng = random.Random(ep.get("seed", 1))
        n = len(song["sections"])
        self.shot_seed = [rng.random() for _ in range(n * 8 + 8)]
        self.blinks = {k: sorted(rng.uniform(0, 400) for _ in range(150)) for k in self.rigs}

    def section(self, b):
        for s in self.song["sections"]:
            if s["start"] <= b < s["end"]:
                return s
        return self.song["sections"][-1]

    def mouth(self, who, b, s):
        if s["kind"] in ("intro", "outro"):
            return 0.0
        singer = s.get("singer", "all")
        if s["kind"] != "chorus" and singer not in ("all", who):
            return 0.0
        best = 0.0
        for n in self.song["notes"]:
            if n["kind"] == "lyric" and s["start"] <= n["beat"] < s["end"] and n["beat"] <= b < n["beat"] + n["dur"] * 0.92:
                k = (b - n["beat"]) / max(n["dur"], 1e-3)
                best = max(best, 0.95 * (1 - 0.4 * k))
        return best

    def apply_pose(self, r, p, bounce, t, mouthv):
        body = r["body"]
        body.location.z = bounce * 0.0035
        body.rotation_euler.y = p.get("lean", 0)
        sq = 1 + 0.03 * math.cos(t * 2 * math.pi / self.beat)
        body.scale = (1 / math.sqrt(sq), 1 / math.sqrt(sq), sq)
        for key, side in (("armL", -1), ("armR", 1)):
            sh, el, hd = r["arms"][key[-1]]
            raise_, elbow = p.get(key, (0.25, 0.1))
            sh.rotation_euler.y = -side * raise_
            el.rotation_euler.y = -side * elbow
            fwd = -0.55 if elbow < -1.2 else -0.1 * abs(math.sin(t * 2))
            sh.rotation_euler.x = fwd
        for key, side in (("legL", -1), ("legR", 1)):
            lift, swing = p.get(key, (0, 0))
            hip = r["legs"][key[-1]]
            hip.location.z = hip.get("z0", hip.location.z) + lift * 0.004
            if "z0" not in hip:
                hip["z0"] = hip.location.z
            hip.rotation_euler.x = -lift * 0.025
            hip.rotation_euler.y = swing
        hd = r["head"]
        hd.rotation_euler.y = p.get("tilt", 0)
        hd.rotation_euler.x = 0.06 * math.sin(t * 2 * math.pi / self.beat)
        hd.rotation_euler.z = p.get("look", 0) * 0.25
        for o, base in r["pupil_base"]:
            o.location.x = base.x + p.get("look", 0) * 0.012
        blink = p.get("blink", False)
        for lid in r["lids"]:
            lid.hide_render = not blink
        if "beak" in r:
            lo, base = r["beak"]
            lo.location.z = base.z - mouthv * 0.06
        else:
            mo, mc = r["mouth_open"], r["mouth_closed"]
            mo.hide_render = mouthv < 0.08
            mo.scale.z = 0.3 + mouthv * 0.9
            mc.hide_render = mouthv >= 0.08
        want = p.get("propR") or p.get("propL")
        for name, obj in r["props"].items():
            vis = name == want
            if obj.get("vis") != vis:
                obj.hide_render = not vis
                for ch in obj.children_recursive:
                    ch.hide_render = not vis
                obj["vis"] = vis

    def frame(self, t):
        b = t / self.beat
        s = self.section(min(b, self.song["total"] - 1e-3))
        scene = s.get("scene") or "meadow"
        for n, c in self.sets.items():
            c.hide_render = n != scene
        night = scene == "bedroom_night"
        outdoor = scene in OUTDOOR
        self.bg.inputs[0].default_value = (0.04, 0.05, 0.16, 1) if night else (0.55, 0.78, 1.0, 1)
        self.bg.inputs[1].default_value = 0.35 if night else (1.0 if outdoor else 0.7)
        self.sun.data.energy = 0.6 if night else 3.2
        self.sun.rotation_euler = (math.radians(48), 0, math.radians(-30))
        self.fill.data.energy = 220 if night else 380
        cast = (s.get("cast") or self.ep["cast"])[:5]
        xs = (POS if self.layout == "land" else POS_V)[len(cast)]
        singer = s.get("singer", "all")
        for k, r in self.rigs.items():
            if k not in cast:
                r["root"].location = (0, 60, 0)
        prev = self.song["sections"][max(0, self.song["sections"].index(s) - 1)]
        entering = s is not self.song["sections"][0] and prev.get("scene") != scene and b - s["start"] < 2
        for i, who in enumerate(cast):
            r = self.rigs[who]
            if s["kind"] == "intro":
                act = "wave"
            elif s["kind"] == "outro":
                act = "dance"
            elif s["kind"] == "chorus":
                act = s.get("action", "dance")
            else:
                act = s.get("action", "groove") if who == singer or singer == "all" else s.get("others", "groove")
            p, bounce, fx = pose_for(act, b, t, phase=i * 0.37)
            m = self.mouth(who, b, s)
            p["blink"] = p.get("blink") or any(x <= t < x + 0.12 for x in self.blinks[who])
            x = xs[i]
            if singer in cast and who != singer and s["kind"] == "verse":
                p["look"] = 1 if xs[cast.index(singer)] > x else -1
            yaw = 0.0
            if entering:
                k = 1 - (b - s["start"]) / 2
                x += (-1 if x < 0 else 1) * 3.5 * k * k
                bounce += 60 * abs(math.sin(b * math.pi * 2)) * k
            if act in ("dance", "spin"):
                yaw = 0.35 * math.sin(b * math.pi / 2 + i)
            r["root"].location = (x, 0.15 * (i % 2), 0)
            r["root"].rotation_euler.z = yaw
            self.apply_pose(r, p, bounce, t, m)
        self.camera(s, b, cast, xs, singer)

    def camera(self, s, b, cast, xs, singer):
        li = int((b - s["start"]) // 8)
        lp = ((b - s["start"]) % 8) / 8
        idx = self.song["sections"].index(s) * 8 + li
        rnd = self.shot_seed[idx % len(self.shot_seed)]
        if s["kind"] in ("intro", "outro"):
            shot = "wide_push" if s["kind"] == "intro" else "orbit"
        elif s["kind"] == "verse":
            shot = ["wide", "medium", "close", "low"][li % 4] if rnd < 0.6 else ["side", "medium", "close", "over"][li % 4]
        else:
            shot = ["wide_push", "orbit", "high", "group"][li % 4] if rnd < 0.6 else ["orbit", "low", "wide_push", "side"][li % 4]
        tgt_who = singer if singer in cast else cast[li % len(cast)]
        tx = xs[cast.index(tgt_who)] if tgt_who in cast else 0
        h = self.rigs[tgt_who]["height"] if tgt_who in self.rigs else 1.2
        vert = self.layout == "vert"
        D = 1.0 if not vert else 0.8
        e = lp
        if shot == "wide":
            pos, look, lens = (0.3 * (e - 0.5), -5.4 * D, 1.15), (0, 0, 0.7), 30
        elif shot == "wide_push":
            pos, look, lens = (0, (-6.5 + 1.3 * e) * D, 1.3 - 0.2 * e), (0, 0, 0.7), 30
        elif shot == "medium":
            pos, look, lens = (tx * 0.7 + 0.4 - 0.3 * e, -3.0 * D, h * 0.75), (tx, 0, h * 0.62), 35
        elif shot == "close":
            pos, look, lens = (tx + 0.25 - 0.2 * e, -1.75 * D, h * 0.85), (tx, 0, h * 0.8), 45
        elif shot == "low":
            pos, look, lens = (tx - 0.7, -2.4 * D, 0.28), (tx, 0, h * 0.7), 26
        elif shot == "side":
            a = math.radians(-50 + 15 * e)
            pos, look, lens = (tx + 2.9 * math.sin(-a), -2.9 * math.cos(a) * D, 1.0), (tx, 0, h * 0.6), 32
        elif shot == "over":
            pos, look, lens = (tx + 1.6, -1.9 * D, h * 1.05), (tx - 0.3, 0, h * 0.6), 30
        elif shot == "orbit":
            a = math.radians(-35 + 70 * e)
            pos, look, lens = (4.6 * math.sin(a), -4.6 * math.cos(a) * D, 1.3), (0, 0, 0.7), 30
        elif shot == "high":
            pos, look, lens = (0.5 * (e - 0.5), -3.6 * D, 3.0), (0, 0.2, 0.5), 30
        else:  # group
            pos, look, lens = (0, -3.8 * D, 1.0), (0, 0, 0.75), 32
        self.cam.location = pos
        self.tgt.location = look
        self.cam.data.lens = lens * (1.05 if vert else 1.0)


def main():
    ep = json.load(open(ARG[1]))
    outdir = ARG[2]
    layout = arg("--layout", "land")
    fps = arg("--fps", 12, int)
    samples = arg("--samples", 8, int)
    meta = arg("--meta", os.path.join(outdir, f"{ep['slug']}_song_meta.json"))
    song = get_song(ep, layout, meta)
    show = Show(ep, song, layout, samples)
    total = song["total"] * 60.0 / song["bpm"] + 1.5
    nframes = int(total * fps)
    start, end = arg("--start", 0, int), arg("--end", nframes, int)
    fdir = os.path.join(outdir, f"frames_{layout}")
    os.makedirs(fdir, exist_ok=True)
    json.dump(dict(fps=fps, nframes=nframes), open(os.path.join(fdir, "info.json"), "w"))
    only = arg("--only")
    t0 = time.time()
    if only:
        for f in [int(float(x) * fps) for x in only.split(",")]:
            show.frame(f / fps)
            show.sc.render.filepath = os.path.join(fdir, f"f_{f:05d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"frame {f}/{nframes} {time.time() - t0:.0f}s", flush=True)
        return
    # animation render: persistent data is reused between frames (much faster than one render() per frame)
    todo = [f for f in range(start, min(end, nframes)) if not os.path.exists(os.path.join(fdir, f"f_{f:05d}.png"))]
    if not todo:
        return
    sc = show.sc
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = todo[0] + 1, todo[-1] + 1   # blender frames are 1-based: file f_{N} <- frame N+1

    def handler(scene, depsgraph=None):
        show.frame((scene.frame_current - 1) / fps)
    bpy.app.handlers.frame_change_pre.append(handler)
    sc.render.filepath = os.path.join(fdir, "b_")
    sc.render.use_file_extension = True
    bpy.ops.render.render(animation=True)
    # rename b_0001.png (frame N) -> f_{N-1}.png
    for fn in os.listdir(fdir):
        if fn.startswith("b_") and fn.endswith(".png"):
            n = int(fn[2:-4]) - 1
            os.replace(os.path.join(fdir, fn), os.path.join(fdir, f"f_{n:05d}.png"))
    print(f"rendered {len(todo)} frames in {time.time() - t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
