"""Runs inside the open Blender. Quality pass over the 'Brinewake Kit' collection:
1. rocks are re-sculpted (voxel remesh, soft displacement, smoothing, decimate) and repainted;
2. every asset gets ambient occlusion and a ground-contact shade worked into its vertex paint;
3. the collection is written to Art/Brinewake_Kit.blend.
"""
import math
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/Brinewake_Kit.blend"
coll = bpy.data.collections["Brinewake Kit"]
deps = bpy.context.evaluated_depsgraph_get()
SUN, SHADE, FOOT = (0.97, 0.89, 0.72), (0.50, 0.53, 0.62), (0.38, 0.40, 0.33)
LIGHT = Vector((0.30, -0.42, 0.86)).normalized()
report = {}


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def resculpt(obj, seed):
    """Turn the hard cut box into a worn boulder: fused volume, lumpy faces, soft shoulders."""
    if obj.get("bw_sculpted"):
        return
    size = max(obj.dimensions)
    tex = bpy.data.textures.new(obj.name + "_lumps", 'CLOUDS')
    tex.noise_scale = size * 0.42
    tex.noise_depth = 1
    fine = bpy.data.textures.new(obj.name + "_grain", 'CLOUDS')
    fine.noise_scale = size * 0.09
    m = obj.modifiers.new("Remesh", 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = max(0.07, size / 60.0)
    m.use_smooth_shade = True
    d = obj.modifiers.new("Lumps", 'DISPLACE')
    d.texture, d.strength, d.mid_level, d.texture_coords = tex, size * 0.045, 0.5, 'LOCAL'
    g = obj.modifiers.new("Grain", 'DISPLACE')
    g.texture, g.strength, g.mid_level, g.texture_coords = fine, size * 0.010, 0.5, 'LOCAL'
    s = obj.modifiers.new("Soften", 'SMOOTH')
    s.factor, s.iterations = 0.5, 5
    deps.update()
    dense = len(obj.evaluated_get(deps).data.polygons)
    dec = obj.modifiers.new("Decimate", 'DECIMATE')
    dec.ratio = min(1.0, 4200.0 / max(dense * 2, 1))
    deps.update()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    mesh.name = old.name
    for mat in old.materials:
        mesh.materials.append(mat)
    low = min(v.co.z for v in mesh.vertices)
    for v in mesh.vertices:
        v.co.z -= low
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.update()
    tall = max(v.co.z for v in mesh.vertices)
    col = mesh.color_attributes.get("Col") or mesh.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
    rnd = random.Random(seed)
    phase = rnd.uniform(0, 6.28)
    for loop in mesh.loops:
        v = mesh.vertices[loop.vertex_index]
        n, z = v.normal, v.co.z
        lit = max(0.0, n.dot(LIGHT)) ** 0.8
        c = lerp(SHADE, SUN, 0.16 + 0.84 * (0.55 * lit + 0.45 * max(0.0, n.z)))      # mostly top light, so turned copies still read
        band = 0.5 + 0.5 * math.sin(z * 1.3 + phase)
        c = lerp(c, (c[0] * 0.90, c[1] * 0.90, c[2] * 0.93), 0.45 * band * (1.0 - abs(n.z)))
        c = lerp(FOOT, c, 0.25 + z / max(tall * 0.32, 0.5))
        col.data[loop.index].color = (c[0] ** 1.6, c[1] ** 1.6, c[2] ** 1.6, 1.0)
    mesh.color_attributes.active_color = col
    obj["bw_sculpted"] = True
    report[obj.name] = len(mesh.polygons)


def occlude(obj, rays=14):
    """Per-vertex ambient occlusion by ray casting against the asset itself, multiplied into the paint."""
    if obj.get("bw_ao"):
        return
    mesh = obj.data
    col = mesh.color_attributes.get("Col")
    if col is None or len(mesh.polygons) == 0:
        return
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [tuple(p.vertices) for p in mesh.polygons])
    reach = max(0.5, min(2.2, max(obj.dimensions) * 0.16))
    rnd = random.Random(7)
    dirs = []
    while len(dirs) < rays:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.1 < d.length < 1.0:
            dirs.append(d.normalized())
    ao = []
    for v in mesh.vertices:
        n = v.normal
        origin = v.co + n * 0.02
        hit = 0.0
        for d in dirs:
            ray = d if d.dot(n) > 0 else -d
            loc, _, _, dist = tree.ray_cast(origin, ray, reach)
            if loc is not None:
                hit += 1.0 - dist / reach
        ao.append(1.0 - hit / rays)
    low = min(v.co.z for v in mesh.vertices)
    for loop in mesh.loops:
        a = ao[loop.vertex_index]
        z = mesh.vertices[loop.vertex_index].co.z - low
        k = (0.42 + 0.58 * a ** 1.3) * (0.82 + 0.18 * min(1.0, z / 0.6))          # cavities and the foot go darker
        c = col.data[loop.index].color
        cool = 1.0 - a                                                             # shadowed paint leans cool, like bounced sky
        col.data[loop.index].color = (c[0] * k * (1.0 - 0.10 * cool), c[1] * k * (1.0 - 0.04 * cool), c[2] * k * (1.0 + 0.10 * cool), 1.0)
    obj["bw_ao"] = True


for i, obj in enumerate(sorted(coll.objects, key=lambda o: o.name)):
    if obj.type != 'MESH':
        continue
    if "Slab" in obj.name or "Boulder" in obj.name or "Rock" in obj.name or "SeaStack" in obj.name:
        resculpt(obj, i)
    occlude(obj)
bpy.data.libraries.write(OUT, set(coll.objects), fake_user=True)
result = {"resculpted": report, "assets": len(coll.objects), "saved": OUT}
