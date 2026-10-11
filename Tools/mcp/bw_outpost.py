"""Brinewake outpost island, second take (see Docs/SoT-Reference-Notes.md).

blender -b --python bw_outpost.py -- <out_dir>
Low lobed sand island with a wide shallow shelf; height comes from piles of worn rock slabs (cut boxes with wide soft
bevels). Writes SM_BW_Isle_A (terrain), SM_BW_Isle_A_Cliffs, SM_BW_Isle_A_Detail (no collision), SM_BW_Isle_A_Falls
(UV mapped) and SM_BW_Isle_A.json (placements in metres, z up, island pivot at the origin). Sea level z = 0. North = +y.
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()
NAME = "SM_BW_Isle_A"
# land lobes: (x, y, radius). The shoreline is where their summed falloff crosses LEVEL.
LOBES = [(0, 0, 60), (54, -4, 36), (-8, -62, 24), (-46, 26, 17), (-80, 44, 21), (30, 52, 20), (74, -60, 13), (-52, -44, 12)]
LEVEL = 0.5
PEAK = Vector((-4.0, 24.0))        # main rock massif
PEAK2 = Vector((56.0, 4.0))        # eastern stack
OUTPOST = Vector((2.0, -30.0))
BOX = (-125.0, 125.0, -110.0, 105.0)   # x0, x1, y0, y1 of the modelled patch
STEP = 1.0
SUN = Vector((0.35, -0.50, 0.80)).normalized()


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lin(c):
    return (max(c[0], 0.0) ** 1.6, max(c[1], 0.0) ** 1.6, max(c[2], 0.0) ** 1.6, 1.0)


def land(x, y):
    """> 0 on land, < 0 at sea, about +1 deep inland."""
    f = 0.0
    for cx, cy, r in LOBES:
        q = math.hypot(x - cx, y - cy) / r
        f += math.exp(-q * q * 1.25)
    f += 0.07 * noise.noise(Vector((x * 0.03, y * 0.03, 0.7))) + 0.03 * noise.noise(Vector((x * 0.09, y * 0.09, 4.1)))
    return f - LEVEL


def rel(x, y):
    """1 at the waterline, smaller inland, larger out to sea (kept for scatter rules)."""
    return 1.0 - land(x, y) * 1.25


def height(x, y):
    e = land(x, y)
    if e < 0:
        return -2.0 * smooth(0.0, -0.20, e) - 9.5 * smooth(-0.20, -0.47, e)       # wide shallow shelf, then the drop
    n = noise.noise(Vector((x * 0.035, y * 0.035, 3.1)))
    z = 1.5 * smooth(0.0, 0.16, e) + 0.9 * smooth(0.16, 0.7, e) * (1.0 + 0.5 * n)   # low beach, barely rising inland
    for c, rad, h in ((PEAK, 30.0, 5.0), (PEAK2, 17.0, 2.5)):
        q = (Vector((x, y)) - c).length / rad
        z += h * math.exp(-q * q * 1.6) * smooth(0.0, 0.25, e)
    return z


def slope(x, y):
    d = 0.6
    return math.hypot(height(x + d, y) - height(x - d, y), height(x, y + d) - height(x, y - d)) / (2 * d)


SAND_WET, SAND_DRY, SAND_SEA = (0.74, 0.66, 0.50), (0.99, 0.96, 0.84), (0.80, 0.86, 0.74)
GRASS_RIM, GRASS_A, GRASS_B = (0.20, 0.44, 0.12), (0.30, 0.62, 0.14), (0.52, 0.78, 0.20)
ROCK_SUN, ROCK_SHADE, ROCK_FOOT = (0.97, 0.89, 0.72), (0.44, 0.48, 0.60), (0.36, 0.38, 0.32)
VINE_DARK, VINE_LIT = (0.10, 0.36, 0.12), (0.50, 0.78, 0.22)


def grass_amount(x, y):
    e = land(x, y)
    patch = noise.noise(Vector((x * 0.028, y * 0.028, 6.3)))                      # big soft meadows, bare sand between
    g = smooth(0.24, 0.42, e + 0.10 * patch) * smooth(-0.22, 0.10, patch + 0.25 * e)
    return g * smooth(12.0, 22.0, (Vector((x, y)) - OUTPOST).length)               # trodden sand round the outpost


def colour(x, y, z):
    n2 = noise.noise(Vector((x * 0.2, y * 0.2, 5.5)))
    n = noise.noise(Vector((x * 0.06, y * 0.06, 1.7)))
    if z < 0:
        c = lerp(SAND_WET, SAND_SEA, -z / 0.8)
        c = lerp(c, (0.55, 0.66, 0.60), smooth(-2.2, -7.0, z))
    else:
        c = lerp(SAND_WET, SAND_DRY, smooth(0.0, 0.7, z + 0.15 * n2))
        c = lerp(c, (0.93, 0.86, 0.70), 0.18 * smooth(-0.2, 0.5, n))               # soft tonal drifts, no speckle
    g = grass_amount(x, y)
    gc = lerp(GRASS_A, GRASS_B, 0.5 + 0.8 * n)
    gc = lerp(GRASS_RIM, gc, smooth(0.15, 0.75, g))                                # darker rim, bright heart
    return lerp(c, gc, smooth(0.25, 0.5, g))


def export_mesh(bm, name, uv=False):
    mesh = bpy.data.meshes.new(name)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(bpy.data.materials.new("BW_Falls" if uv else "BW_Painted"))
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, mesh_smooth_type='FACE',
                             colors_type='LINEAR', add_leaf_bones=False, bake_space_transform=True,
                             axis_forward='-Y', axis_up='Z')
    print("BW exported", name, len(mesh.polygons), "tris")


def build_terrain():
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")
    nx, ny = int((BOX[1] - BOX[0]) / STEP), int((BOX[3] - BOX[2]) / STEP)
    grid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x, y = BOX[0] + i * STEP, BOX[2] + j * STEP
            if land(x, y) > -0.50:
                grid[i, j] = bm.verts.new((x, y, height(x, y)))
    for i in range(nx):
        for j in range(ny):
            q = [grid.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if all(q):
                bm.faces.new(q).smooth = True
    bm.normal_update()
    for f in bm.faces:
        for loop in f.loops:
            loop[col] = lin(colour(*loop.vert.co))
    export_mesh(bm, NAME)


# --- rock: a box cut by a few planes, then bevelled wide so every edge is a soft worn shoulder -------------------
LEDGES = []      # (top centre, radius) of slabs whose top is close to level


ROCKS = []       # kit instances: the cliffs are stacked from SM_BW_Slab_* meshes, not baked
KIT = {"SM_BW_Slab_01": (3.0, 2.6, 5.0), "SM_BW_Slab_02": (4.0, 3.4, 2.4), "SM_BW_Slab_03": (3.5, 2.4, 3.2), "SM_BW_Slab_04": (4.5, 3.6, 1.2),
       "SM_BW_Slab_05": (1.8, 1.6, 6.0), "SM_BW_Slab_06": (3.0, 3.0, 3.0), "SM_BW_Slab_07": (5.5, 2.4, 2.2), "SM_BW_Slab_08": (2.6, 2.2, 4.4),
       "SM_BW_Slab_09": (4.2, 3.8, 3.0), "SM_BW_Slab_10": (1.6, 1.3, 1.1), "SM_BW_Slab_11": (2.4, 2.0, 7.5), "SM_BW_Slab_12": (5.0, 4.4, 4.0)}


def slab(bm, col, rnd, centre, size, tilt=0.0, heading=None, warm=0.0, cuts=4):
    """Picks the kit slab closest in proportion to the wanted block and records a scaled, tilted instance."""
    wide = max(size[0], size[1])
    ratio = size[2] / wide
    if cuts <= 2 and tilt < 0.05:
        pick = ["SM_BW_Slab_09"]
    elif ratio > 1.7:
        pick = ["SM_BW_Slab_05", "SM_BW_Slab_11"]
    elif ratio > 1.05:
        pick = ["SM_BW_Slab_01", "SM_BW_Slab_08", "SM_BW_Slab_03"]
    elif ratio > 0.6:
        pick = ["SM_BW_Slab_06", "SM_BW_Slab_02", "SM_BW_Slab_12", "SM_BW_Slab_10"]
    else:
        pick = ["SM_BW_Slab_04", "SM_BW_Slab_07"]
    mesh = rnd.choice(pick)
    hx, hy, hz = KIT[mesh]
    h = heading if heading is not None else rnd.uniform(0, 2 * math.pi)
    deg = math.degrees(tilt)
    ROCKS.append({"mesh": mesh, "x": round(centre[0], 2), "y": round(centre[1], 2), "z": round(centre[2] - size[2] * 0.98, 2),
                  "yaw": round(rnd.uniform(0, 360), 1), "pitch": round(deg * math.cos(h), 1), "roll": round(deg * math.sin(h), 1),
                  "sx": round(size[0] / hx, 3), "sy": round(size[1] / hy, 3), "sz": round(size[2] / hz, 3), "scale": 1.0})
    if tilt < 0.05 and min(size[0], size[1]) > 3.5:
        LEDGES.append((Vector((centre[0], centre[1], centre[2] + size[2] * 0.94)), min(size[0], size[1]) * 0.62))


def build_cliffs():
    rnd = random.Random(21)
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")

    def pile(c, tiers):
        for count, ring, wide, deep, tall, z0, tilt in tiers:
            for k in range(count):
                a = 2 * math.pi * k / count + rnd.uniform(-0.35, 0.35)
                r = ring * rnd.uniform(0.75, 1.1)
                x, y = c.x + math.cos(a) * r, c.y + math.sin(a) * r * 0.85
                s = (rnd.uniform(*wide), rnd.uniform(*deep), rnd.uniform(*tall))
                # lean in toward the middle of the pile, the way stacked slabs settle
                slab(bm, col, rnd, (x, y, z0 + s[2] * 0.55 + rnd.uniform(-1.5, 1.5)), s,
                     tilt=rnd.uniform(0.3, 1.0) * tilt, heading=a + math.pi / 2)

    pile(PEAK, ((11, 22.0, (8, 12), (7, 10), (7, 11), -1.0, 0.30), (8, 14.0, (8, 11), (7, 9), (11, 15), 8.0, 0.25),
                (6, 8.0, (7, 9), (6, 8), (11, 14), 22.0, 0.22), (4, 4.0, (5.5, 7), (5, 6.5), (10, 13), 36.0, 0.18)))
    for z, s, off in ((54.0, (5.0, 4.4, 9.0), 0.8), (66.0, (3.8, 3.3, 7.5), 1.8), (75.0, (2.6, 2.3, 6.0), 2.6)):       # the spire
        slab(bm, col, rnd, (PEAK.x + off, PEAK.y - off * 0.5, z), s, tilt=0.10, cuts=3)
    for k in range(5):                                              # flat-topped terraces: grass and falls start here
        a = -1.9 + k * 0.55
        slab(bm, col, rnd, (PEAK.x + math.cos(a) * 15.0, PEAK.y + math.sin(a) * 13.0, 9.0 + k * 4.5), (7.5, 6.5, 6.0 + k), tilt=0.0, cuts=2)
    pile(PEAK2, ((7, 11.0, (6, 9), (5, 7.5), (5, 8), -1.0, 0.30), (4, 5.5, (5.5, 7.5), (5, 6.5), (8, 11), 5.0, 0.22),
                 (2, 2.0, (4, 5.5), (3.6, 4.6), (7, 9), 15.0, 0.15)))
    slab(bm, col, rnd, (PEAK2.x + 1.0, PEAK2.y, 28.0), (3.0, 2.6, 7.0), tilt=0.08, cuts=3)
    for cx, cy, n in ((-30, -14, 3), (34, -22, 3), (-18, -58, 3), (62, -30, 3), (-70, 34, 4), (20, 44, 3), (-44, 10, 3),
                      (70, -56, 3), (8, -76, 2), (-58, -40, 3), (44, 30, 3), (-92, 50, 2)):                             # beach rocks in threes
        for k in range(n):
            x, y = cx + rnd.uniform(-5, 5), cy + rnd.uniform(-5, 5)
            s = rnd.uniform(1.4, 3.4) * (1.6 if k == 0 else 1.0)
            slab(bm, col, rnd, (x, y, height(x, y) + s * 0.18), (s * rnd.uniform(1.0, 1.5), s, s * rnd.uniform(0.55, 0.9)),
                 tilt=rnd.uniform(0.0, 0.35), warm=0.5, cuts=3)
    bm.free()
    print("BW rocks", len(ROCKS), "instances")


def build_detail():
    """Grass, flowers, pebbles on the ground; grass caps, leafy mats and vine curtains on the rock. No collision."""
    rnd = random.Random(5)
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")

    def put(pts, cols):
        f = bm.faces.new([bm.verts.new(v) for v in pts])
        for loop, c in zip(f.loops, cols):
            loop[col] = lin(c)

    def tuft(x, y, z, scale, base):
        for k in range(rnd.randint(5, 8)):
            a = rnd.uniform(0, 2 * math.pi)
            lean, h, w = rnd.uniform(0.15, 0.6), scale * rnd.uniform(0.28, 0.62), scale * rnd.uniform(0.035, 0.06)
            out = Vector((math.cos(a), math.sin(a), 0))
            sidev = Vector((-math.sin(a), math.cos(a), 0)) * w
            root = Vector((x, y, z - 0.03)) + out * rnd.uniform(0.0, 0.10) * scale
            mid = root + out * lean * h * 0.35 + Vector((0, 0, h * 0.6))
            tip = root + out * lean * h + Vector((0, 0, h))
            dark = lerp(base, (0.16, 0.44, 0.12), 0.30)
            lit = lerp(lerp(base, (0.66, 0.92, 0.28), 0.75), (0.92, 0.94, 0.42), rnd.uniform(0.0, 0.5))
            midc = lerp(dark, lit, 0.55)
            put([root - sidev, root + sidev, mid + sidev * 0.7, mid - sidev * 0.7], [dark, dark, midc, midc])
            put([mid - sidev * 0.7, mid + sidev * 0.7, tip], [midc, midc, lit])

    def flower(x, y, z, petal):
        top = Vector((x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.05, 0.05), z + rnd.uniform(0.25, 0.5)))
        stem = (0.20, 0.45, 0.14)
        put([Vector((x - 0.012, y, z)), Vector((x + 0.012, y, z)), top], [stem, stem, stem])
        r = rnd.uniform(0.07, 0.11)
        for k in range(5):
            a0, a1 = 2 * math.pi * k / 5, 2 * math.pi * (k + 0.8) / 5
            put([top, top + Vector((math.cos(a0) * r, math.sin(a0) * r, 0.03)),
                 top + Vector((math.cos(a1) * r, math.sin(a1) * r, 0.03))], [(0.98, 0.82, 0.25), petal, petal])

    def lump(centre, size, c_low, c_high, subdiv=2, soft=True):
        geo = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        off = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), 0))
        for v in geo["verts"]:
            k = 1.0 + 0.22 * noise.noise(v.co * 1.5 + off)
            v.co = Vector((v.co.x * size[0] * k, v.co.y * size[1] * k, v.co.z * size[2] * k)) + Vector(centre)
        faces = {f for v in geo["verts"] for f in v.link_faces}
        for f in faces:
            f.smooth = soft
            f.normal_update()
        for f in faces:
            for loop in f.loops:
                n = (loop.vert.co - Vector(centre))
                n = Vector((n.x / size[0], n.y / size[1], n.z / size[2])).normalized()
                loop[col] = lin(lerp(c_low, c_high, max(0.0, n.dot(SUN)) * 0.9 + 0.1 * n.z + 0.1))

    def curtain(start, out, length, width):
        """A leafy vine curtain: overlapping leaf rows hanging down a rock face."""
        side = Vector((-out.y, out.x, 0)).normalized()
        rows = max(3, int(length / 0.9))
        for r in range(rows):
            t = r / rows
            w = width * (1.0 - 0.55 * t)
            for k in range(max(2, int(w / 0.7))):
                u = (k + rnd.uniform(0.1, 0.9)) / max(2, int(w / 0.7)) - 0.5
                p = start + side * (u * w) + out * (0.25 + 0.2 * math.sin(r * 1.7 + k)) + Vector((0, 0, -length * t))
                s = rnd.uniform(0.45, 0.85)
                a, b = p + side * s * 0.5, p - side * s * 0.5
                tip = p + out * 0.3 + Vector((0, 0, -s * 1.5))
                c0 = lerp(VINE_LIT, VINE_DARK, t * 0.7 + rnd.uniform(0, 0.25))
                put([a, b, tip], [c0, c0, lerp(c0, (0.70, 0.90, 0.30), 0.6)])

    tufts = flowers = stones = 0
    petals = [(0.98, 0.96, 0.90), (0.98, 0.45, 0.55), (0.95, 0.30, 0.20), (0.70, 0.50, 0.95), (1.0, 0.78, 0.20)]
    for _ in range(140000):
        x, y = rnd.uniform(BOX[0], BOX[1]), rnd.uniform(BOX[2], BOX[3])
        if land(x, y) < 0.03 or (Vector((x, y)) - PEAK).length < 21 or (Vector((x, y)) - PEAK2).length < 10:
            continue
        z = height(x, y)
        g = grass_amount(x, y)
        if g > 0.3 and tufts < 11000 and rnd.random() < g:
            tuft(x, y, z, rnd.uniform(0.8, 1.6) * (0.55 + 0.6 * g), colour(x, y, z))
            tufts += 1
            if rnd.random() < 0.05 and flowers < 500:
                flower(x + 0.1, y + 0.05, z, rnd.choice(petals))
                flowers += 1
        elif g < 0.1 and stones < 500 and rnd.random() < 0.03:
            shell = rnd.random() < 0.4
            s = rnd.uniform(0.04, 0.09) if shell else rnd.uniform(0.07, 0.2)
            c = rnd.choice([(0.98, 0.93, 0.86), (0.96, 0.72, 0.62), (0.90, 0.84, 0.95)]) if shell else (0.80, 0.74, 0.62)
            lump((x, y, z), (s, s * rnd.uniform(0.8, 1.2), s * 0.5), (c[0] * 0.7, c[1] * 0.7, c[2] * 0.75), c, subdiv=1)
            stones += 1
    caps = curtains = 0
    for top, radius in LEDGES:
        base = lerp(GRASS_A, GRASS_B, rnd.uniform(0.3, 0.9))
        lump((top.x, top.y, top.z - 0.25), (radius * 1.05, radius * 1.05, 0.75), GRASS_RIM, base)          # grass cap
        caps += 1
        for _ in range(int(10 + radius * radius * 1.5)):
            a, r = rnd.uniform(0, 6.28), radius * math.sqrt(rnd.uniform(0, 0.8))
            tuft(top.x + math.cos(a) * r, top.y + math.sin(a) * r, top.z + 0.35, rnd.uniform(1.0, 1.9), base)
        centre = PEAK2 if (Vector((top.x, top.y)) - PEAK2).length < 20 else PEAK
        out = Vector((top.x - centre.x, top.y - centre.y, 0))
        out = out.normalized() if out.length > 0.5 else Vector((0, -1, 0))
        for k in range(rnd.randint(2, 4)):
            turn = Matrix.Rotation(rnd.uniform(-1.1, 1.1), 3, 'Z')
            d = turn @ out
            curtain(top + d * radius * 0.95 + Vector((0, 0, 0.1)), d, rnd.uniform(3.0, 8.0), rnd.uniform(2.0, 4.5))
            curtains += 1
    bm.normal_update()
    print("BW detail", tufts, "tufts", flowers, "flowers", stones, "stones", caps, "caps", curtains, "curtains")
    export_mesh(bm, NAME + "_Detail")


def build_falls():
    """Waterfall ribbons off the south-facing terraces, UV mapped so the material can scroll them."""
    rnd = random.Random(8)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    col = bm.loops.layers.color.new("Col")
    picks = sorted([l for l in LEDGES if l[0].y < PEAK.y - 3 and 12 < l[0].z < 40 and (Vector((l[0].x, l[0].y)) - PEAK).length < 24],
                   key=lambda l: -l[0].z)[:2]
    made = []
    for top, radius in picks:
        out = Vector((top.x - PEAK.x, top.y - PEAK.y, 0)).normalized()
        start = top + out * radius
        foot = height(start.x + out.x * 5, start.y + out.y * 5) + 0.3
        side = Vector((-out.y, out.x, 0))
        width = rnd.uniform(1.8, 2.8)
        rows = []
        for i in range(15):
            t = i / 14
            p = start + out * (1.0 * t + 3.5 * t * t) + Vector((0, 0, -(start.z - foot) * (0.15 * t + 0.85 * t * t)))
            w = width * (0.8 + 0.5 * t)
            rows.append((bm.verts.new(p - side * w / 2), bm.verts.new(p + side * w / 2), t))
        length = (start.z - foot) / 6.0
        for (a0, b0, t0), (a1, b1, t1) in zip(rows, rows[1:]):
            f = bm.faces.new((a0, b0, b1, a1))
            for loop, uv in zip(f.loops, ((0, t0 * length), (1, t0 * length), (1, t1 * length), (0, t1 * length))):
                loop[uvl].uv = uv
                loop[col] = (1, 1, 1, 1)
        made.append({"x": round(start.x + out.x * 4.5, 2), "y": round(start.y + out.y * 4.5, 2), "z": round(foot, 2)})
    if not made:                                                    # keep the asset valid if no terrace qualified
        f = bm.faces.new([bm.verts.new(v) for v in ((0, 0, -30), (0.1, 0, -30), (0, 0.1, -30))])
        for loop in f.loops:
            loop[uvl].uv = (0, 0)
    bm.normal_update()
    export_mesh(bm, NAME + "_Falls", uv=True)
    return made


def scatter(falls):
    rnd = random.Random(11)
    out = []
    builds = [{"mesh": "SM_BW_Alehouse", "x": -6.0, "y": -22.0, "yaw": 95.0}, {"mesh": "SM_BW_WardenHut", "x": -26.0, "y": -34.0, "yaw": 60.0},
              {"mesh": "SM_BW_SalvageTent", "x": 18.0, "y": -46.0, "yaw": 120.0}, {"mesh": "SM_BW_Hut_A", "x": 22.0, "y": -22.0, "yaw": 150.0},
              {"mesh": "SM_BW_Tower", "x": 34.0, "y": -36.0, "yaw": 15.0}]
    for b in builds:
        b["z"] = round(height(b["x"], b["y"]) - 0.05, 2)
        b["scale"] = 1.0
    # dock: walk out from the outpost toward the south-east until the shelf, start a little inland
    a = math.radians(-52.0)
    d = 0.0
    while land(OUTPOST.x + math.cos(a) * d, OUTPOST.y + math.sin(a) * d) > 0.06 and d < 90:
        d += 0.5
    dock = {"mesh": "SM_BW_Dock", "x": round(OUTPOST.x + math.cos(a) * d, 2), "y": round(OUTPOST.y + math.sin(a) * d, 2), "z": 0.0,
            "yaw": round(math.degrees(a), 1), "scale": 1.0}
    builds.append(dock)
    builds.append({"mesh": "SM_BW_Keelwright", "x": round(dock["x"] + math.cos(a) * 20 - math.sin(a) * 7.5, 2),
                   "y": round(dock["y"] + math.sin(a) * 20 + math.cos(a) * 7.5, 2), "z": 0.0, "yaw": round(math.degrees(a) + 90, 1), "scale": 1.0})
    builds.append({"mesh": "SM_BW_MarketStall", "x": round(dock["x"] + math.cos(a) * 33, 2), "y": round(dock["y"] + math.sin(a) * 33, 2),
                   "z": 1.3, "yaw": round(math.degrees(a), 1), "scale": 1.0})
    ca, sa = math.cos(a), math.sin(a)

    def along(dist, side, mesh, yaw_off=0.0, z=0.0):
        return {"mesh": mesh, "x": round(dock["x"] + ca * dist - sa * side, 2), "y": round(dock["y"] + sa * dist + ca * side, 2),
                "z": z, "yaw": round(math.degrees(a) + yaw_off, 1), "scale": 1.0}

    builds += [along(46.0, 0.0, "SM_BW_DockEnd"), along(38.0, -7.0, "SM_BW_Sloop", 180.0), along(22.0, -11.0, "SM_BW_Brigantine", 0.0),
               along(10.0, 2.2, "SM_BW_MooringPost"), along(28.0, -2.2, "SM_BW_MooringPost"), along(44.0, 2.4, "SM_BW_MooringPost"),
               along(30.0, 1.9, "SM_BW_Ladder", 90.0, -2.0), along(48.0, 1.0, "SM_BW_Capstan", 0.0, 1.3)]
    for mesh, x, y, yaw in (("SM_BW_Rowboat", 30.0, -44.0, 20.0), ("SM_BW_Rowboat", -22.0, -50.0, 140.0), ("SM_BW_NetRack", 26.0, -40.0, 100.0),
                            ("SM_BW_Anchor", 12.0, -48.0, 30.0), ("SM_BW_BannerPole", 2.0, -36.0, 90.0), ("SM_BW_BannerPole", -14.0, -30.0, 70.0),
                            ("SM_BW_Bench", -2.0, -32.0, 5.0), ("SM_BW_Bench", 8.0, -30.0, 200.0), ("SM_BW_LanternPost", 4.0, -40.0, 0.0),
                            ("SM_BW_LanternPost", -12.0, -38.0, 180.0), ("SM_BW_LanternPost", 16.0, -30.0, 90.0), ("SM_BW_LanternPost", 26.0, -30.0, 270.0),
                            ("SM_BW_Pirate_Red", -4.0, -31.0, 110.0), ("SM_BW_Pirate_Blue", 17.0, -44.0, 300.0), ("SM_BW_Pirate_Green", -24.0, -30.0, 80.0),
                            ("SM_BW_Cannon", 30.0, -34.0, 60.0)):
        builds.append({"mesh": mesh, "x": x, "y": y, "z": round(max(height(x, y), 0.0), 2), "yaw": yaw, "scale": 1.0})
    keep = [(b["x"], b["y"], 9.0) for b in builds[:5]] + [(dock["x"] + math.cos(a) * k, dock["y"] + math.sin(a) * k, 5.0) for k in (0, 8, 16)]

    def place(mesh, count, emin, emax, scale, sink=0.15, gap=3.0, near=None, reach=0.0, grass=None):
        made, tries = 0, 0
        while made < count and tries < 9000:
            tries += 1
            if near is not None:
                ang, rad = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.0, reach)
                x, y = near[0] + math.cos(ang) * rad, near[1] + math.sin(ang) * rad
            else:
                x, y = rnd.uniform(BOX[0], BOX[1]), rnd.uniform(BOX[2], BOX[3])
            e = land(x, y)
            if not emin <= e <= emax or (Vector((x, y)) - PEAK).length < 24 or (Vector((x, y)) - PEAK2).length < 12:
                continue
            if grass is not None and not grass[0] <= grass_amount(x, y) <= grass[1]:
                continue
            if any(math.hypot(x - o["x"], y - o["y"]) < gap for o in out) or any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep):
                continue
            s = rnd.uniform(*scale)
            out.append({"mesh": rnd.choice(mesh) if isinstance(mesh, list) else mesh, "x": round(x, 2), "y": round(y, 2),
                        "z": round(height(x, y) - sink * s, 2), "yaw": round(rnd.uniform(0, 360), 1), "scale": round(s, 2)})
            made += 1

    palms = ["SM_BW_Palm_A", "SM_BW_Palm_B", "SM_BW_Palm_C"]
    groves = [(-34, -8), (30, -12), (44, 20), (-20, 48), (-62, 30), (-80, 46), (58, -18), (-6, -58), (10, 40), (72, -58), (-48, -42), (26, 54)]
    for g in groves:                                                # palms stand in clumps, with bushes at their feet
        place(palms, rnd.randint(4, 7), 0.08, 2.0, (0.95, 1.4), sink=0.3, gap=3.6, near=g, reach=11.0)
        place("SM_BW_Bush_A", rnd.randint(3, 6), 0.08, 2.0, (1.1, 2.2), gap=2.4, near=g, reach=10.0)
        place("SM_BW_Fern_A", rnd.randint(4, 7), 0.08, 2.0, (1.0, 2.0), gap=1.8, near=g, reach=12.0)
    place(palms, 10, 0.1, 0.5, (0.9, 1.3), sink=0.3, gap=6.0, near=(OUTPOST.x, OUTPOST.y), reach=34.0)
    place("SM_BW_Bush_A", 26, 0.2, 2.0, (1.0, 2.0), gap=2.6, grass=(0.4, 1.0))
    place("SM_BW_Fern_A", 34, 0.2, 2.0, (0.9, 1.8), gap=2.0, grass=(0.3, 1.0))
    place("SM_BW_Barrel", 6, 0.12, 1.0, (1.0, 1.0), sink=0.0, gap=1.2, near=(OUTPOST.x, OUTPOST.y), reach=15.0)
    place("SM_BW_Crate", 6, 0.12, 1.0, (1.0, 1.0), sink=0.0, gap=1.3, near=(OUTPOST.x, OUTPOST.y), reach=15.0)
    start = {"x": 6.0, "y": -40.0, "yaw": 110.0}
    start["z"] = round(height(start["x"], start["y"]), 2)
    json.dump({"props": builds + ROCKS + out, "start": start, "falls": falls, "peak": [PEAK.x, PEAK.y]},
              open(os.path.join(OUT, NAME + ".json"), "w"), indent=0)
    print("BW scatter", len(out), "props", len(builds), "builds", "dock", dock)


bpy.ops.wm.read_factory_settings(use_empty=True)
build_terrain()
build_cliffs()
build_detail()
scatter(build_falls())
if "--blend" in sys.argv:
    bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index("--blend") + 1])      # Gullrest.blend
    print("BW saved island blend")
