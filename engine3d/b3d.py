"""Small Blender helpers: toon-ish materials, primitives with smooth shading, cartoon outlines."""
import math
import bpy

_mats = {}


def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # sRGB -> linear
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(hexcol, rough=0.55, sss=0.0, emit=0.0, spec=0.35, name=None):
    key = (hexcol, rough, sss, emit, spec)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name or f"m_{hexcol}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    col = hexrgb(hexcol)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    for k in ("Specular IOR Level", "Specular"):
        if k in b.inputs:
            b.inputs[k].default_value = spec
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.3, 0.12, 0.08)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.02
    if emit:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*col, 1)
    _mats[key] = m
    return m


def outline_mat():
    if "outline" in _mats:
        return _mats["outline"]
    m = bpy.data.materials.new("outline")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.04, 0.025, 0.02, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(lp.outputs["Is Camera Ray"], inv.inputs[1])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(geo.outputs["Backfacing"], mx.inputs[0]); nt.links.new(inv.outputs[0], mx.inputs[1])
    nt.links.new(mx.outputs[0], mix.inputs["Fac"])  # 0 -> dark rim (camera rays only), 1 -> invisible
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    # flipped shell: faces toward camera are "backfacing" -> transparent; rim beyond silhouette -> dark
    _mats["outline"] = m
    return m


def _finish(o, m, outline, parent, smooth=True, subsurf=0):
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if subsurf:
        s = o.modifiers.new("sub", "SUBSURF"); s.levels = subsurf; s.render_levels = subsurf
    o.data.materials.append(m)
    if outline:
        o.data.materials.append(outline_mat())
        sol = o.modifiers.new("outline", "SOLIDIFY")
        sol.thickness = outline
        sol.offset = 1.0
        sol.use_flip_normals = True
        sol.material_offset = 1
        sol.use_rim = False
    if parent is not None:
        o.parent = parent
    return o


def sphere(name, loc, r, m, scale=(1, 1, 1), parent=None, outline=0.012, seg=40, rot=(0, 0, 0)):
    mesh = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc; o.scale = scale; o.rotation_euler = rot
    return _finish(o, m, outline, parent)


def capsule(name, start, end, r, m, parent=None, outline=0.012, r2=None):
    """Rounded limb from start to end (local coords of parent)."""
    import bmesh
    from mathutils import Vector
    r2 = r2 or r
    a, b = Vector(start), Vector(end)
    L = (b - a).length
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r2, depth=L)
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    for v in bm.verts:
        pass
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    # cone centred at origin along z; move so it spans a->b
    d = (b - a).normalized()
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.location = (a + b) / 2
    _finish(o, m, outline, parent)
    # end caps as separate spheres for roundness
    sphere(name + "_capA", tuple(a), r, m, parent=parent, outline=outline, seg=24)
    sphere(name + "_capB", tuple(b), r2, m, parent=parent, outline=outline, seg=24)
    return o


def cone(name, loc, r1, r2, depth, m, parent=None, outline=0.012, rot=(0, 0, 0), seg=40, scale=(1, 1, 1)):
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=depth)
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; o.scale = scale
    _finish(o, m, outline, parent)
    o.modifiers.new("bevel", "BEVEL").width = min(r1, r2, depth) * 0.25 if min(r1, r2) > 0 else 0.01
    return o


def box(name, loc, size, m, parent=None, outline=0.0, bevel=0.02, rot=(0, 0, 0)):
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc; o.scale = size; o.rotation_euler = rot
    if bevel:
        bv = o.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 3
        bv.use_clamp_overlap = True
    _finish(o, m, outline, parent, smooth=False)
    return o


def torus(name, loc, R, r, m, parent=None, rot=(0, 0, 0), outline=0.0, arc=None):
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    seg = 32
    verts = []
    ang = arc or 2 * math.pi
    nseg = seg if arc is None else seg // 2
    for i in range(nseg + (0 if arc is None else 1)):
        a = -ang / 2 + ang * i / nseg if arc else ang * i / seg
        ring = []
        for j in range(12):
            b = 2 * math.pi * j / 12
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        verts.append(ring)
    rng = range(len(verts)) if arc is None else range(len(verts) - 1)
    for i in rng:
        a, b2 = verts[i], verts[(i + 1) % len(verts)]
        for j in range(12):
            bm.faces.new((a[j], a[(j + 1) % 12], b2[(j + 1) % 12], b2[j]))
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    return _finish(o, m, outline, parent)


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o
