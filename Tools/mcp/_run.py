"""Brinewake prop kit for Unreal: chunky shapes, colour painted per vertex (gradients, no textures).

blender -b --python bw_kit.py -- <out_dir>
Units are metres (1 m -> 100 cm in Unreal). Every prop sits on z = 0 with its pivot at the base.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()



def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def clamp01(x):
    return max(0.0, min(1.0, x))


SHELF = []


class Prop:
    """Collects painted geometry in one bmesh, then exports it as a single mesh."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Col")

    def paint(self, faces, fn):
        for f in faces:
            for loop in f.loops:
                c = fn(loop.vert.co, f.normal)
                loop[self.col] = (c[0] ** 1.0, c[1] ** 1.0, c[2] ** 1.0, 1.0)  # palette is display colour, Unreal reads linear

    def tube(self, rings, colour, smooth=True, cap=True, sides=10):
        """rings: list of (centre Vector, radius, axis Vector). Returns the new faces."""
        loops = []
        for centre, radius, axis in rings:
            axis = axis.normalized()
            side = axis.cross(Vector((0, 1, 0)))
            if side.length < 1e-4:
                side = axis.cross(Vector((1, 0, 0)))
            side.normalize()
            up = side.cross(axis)
            loops.append([self.bm.verts.new(centre + (side * math.cos(a) + up * math.sin(a)) * radius)
                          for a in (2 * math.pi * k / sides for k in range(sides))])
        faces = []
        for a, b in zip(loops, loops[1:]):
            for k in range(sides):
                faces.append(self.bm.faces.new((a[(k + 1) % sides], a[k], b[k], b[(k + 1) % sides])))
        if cap:
            faces.append(self.bm.faces.new(list(reversed(loops[-1]))))
            faces.append(self.bm.faces.new(loops[0]))
        for f in faces:
            f.smooth = smooth
        self.bm.normal_update()
        self.paint(faces, colour)
        return faces

    def blob(self, centre, size, colour, seed=0, rough=0.28, subdiv=2, strata=0.0, smooth=False):
        """A lumpy rock / foliage mass. size is a 3-vector of radii."""
        geo = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=1.0)
        verts = geo["verts"]
        off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
        for v in verts:
            n = noise.noise(v.co * 1.3 + off) * rough + noise.noise(v.co * 3.1 + off) * rough * 0.35
            v.co *= 1.0 + n
            if strata:
                # squash toward horizontal ledges so the rock reads as bedded stone
                z = v.co.z
                step = round(z / strata) * strata
                v.co.z = z + (step - z) * 0.55
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(centre)
        faces = list({f for v in verts for f in v.link_faces})
        for f in faces:
            f.smooth = smooth
        self.bm.normal_update()
        self.paint(faces, colour)
        return faces

    def blade(self, root, direction, length, width, droop, colour, segs=7, fold=0.35):
        """A folded palm frond / leaf: a spine that droops, two halves angled up like a V."""
        direction = direction.normalized()
        side = direction.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        spine, left, right = [], [], []
        for i in range(segs + 1):
            t = i / segs
            p = root + direction * (length * t) + Vector((0, 0, -droop * length * t * t))
            w = width * math.sin(math.pi * (0.08 + 0.92 * t)) ** 0.6 * (1.0 - 0.25 * t)
            lift = Vector((0, 0, w * fold))
            jag = 1.0 if i % 2 == 0 else 0.72
            spine.append(self.bm.verts.new(p))
            left.append(self.bm.verts.new(p + side * w * jag + lift))
            right.append(self.bm.verts.new(p - side * w * jag + lift))
        faces = []
        for i in range(segs):
            faces.append(self.bm.faces.new((spine[i], spine[i + 1], left[i + 1], left[i])))
            faces.append(self.bm.faces.new((spine[i], right[i], right[i + 1], spine[i + 1])))
        for f in faces:
            f.smooth = False
        self.bm.normal_update()
        self.paint(faces, lambda co, n: colour((co - root).length / max(length, 1e-4)))
        return faces

    def box(self, centre, size, colour, bevel=0.0, xform=None, local_paint=None):
        """Axis-aligned box, optionally chamfered, then moved by xform (local_paint runs before the move)."""
        geo = bmesh.ops.create_cube(self.bm, size=1.0)
        verts = geo["verts"]
        for v in verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(centre)
        faces = list({f for v in verts for f in v.link_faces})
        if bevel:
            edges = list({e for f in faces for e in f.edges})
            res = bmesh.ops.bevel(self.bm, geom=edges, offset=bevel, segments=1, affect='EDGES')
            faces = list({f for v in res["verts"] for f in v.link_faces} | set(f for f in faces if f.is_valid))
        for f in faces:
            f.smooth = False
        self.bm.normal_update()
        if local_paint:
            self.paint(faces, local_paint)
        if xform is not None:
            for v in {v for f in faces for v in f.verts}:
                v.co = xform @ v.co
            self.bm.normal_update()
        if not local_paint:
            self.paint(faces, colour)
        return faces

    def export(self):
        mesh = bpy.data.meshes.new(self.name)
        bmesh.ops.triangulate(self.bm, faces=self.bm.faces[:])
        self.bm.to_mesh(mesh)
        self.bm.free()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        mat = bpy.data.materials.get("BW_Painted")
        if mat is None:
            mat = bpy.data.materials.new("BW_Painted")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            attr = nodes.new("ShaderNodeVertexColor")
            attr.layer_name = "Col"
            bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
            mat.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
            bsdf.inputs["Roughness"].default_value = 0.82
        mesh.materials.append(mat)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(OUT, self.name + ".fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, mesh_smooth_type='FACE',
                                 colors_type='LINEAR', add_leaf_bones=False, bake_space_transform=True,
                                 axis_forward='-Y', axis_up='Z')
        print("BW exported", self.name, len(mesh.polygons), "tris")
        slot = len(SHELF)
        obj.location = ((slot % 10) * 26.0, -(slot // 10) * 30.0, 0.0)       # exported at the origin, shelved afterwards
        obj.select_set(False)
        SHELF.append(obj.name)


# --- palette: warm lit tops, cool purple-brown shadows, saturated greens ---------------------
BARK_DARK, BARK_LIGHT, BARK_RING = (0.20, 0.11, 0.07), (0.62, 0.44, 0.24), (0.13, 0.07, 0.06)
LEAF_DEEP, LEAF_MID, LEAF_TIP = (0.03, 0.22, 0.10), (0.10, 0.48, 0.14), (0.55, 0.72, 0.16)
ROCK_TOP, ROCK_MID, ROCK_LOW = (0.66, 0.58, 0.46), (0.40, 0.34, 0.31), (0.17, 0.14, 0.19)
MOSS = (0.25, 0.42, 0.14)
WOOD_DARK, WOOD_LIGHT, IRON = (0.22, 0.12, 0.07), (0.58, 0.38, 0.20), (0.10, 0.10, 0.12)


def leaf_colour(t):
    return lerp(LEAF_DEEP, LEAF_MID, clamp01(t * 2.2)) if t < 0.45 else lerp(LEAF_MID, LEAF_TIP, clamp01((t - 0.45) / 0.55))


def rock(name, size, seed, moss=0.0, pieces=1):
    rnd = random.Random(seed)
    p = Prop(name)
    height = size[2] * 2

    def colour(co, nrm):
        t = clamp01(co.z / height)
        base = lerp(ROCK_LOW, ROCK_MID, clamp01(t * 1.8))
        base = lerp(base, ROCK_TOP, clamp01(nrm.z) ** 1.5 * (0.35 + 0.65 * t))
        band = 0.5 + 0.5 * math.sin(co.z * 9.0 + noise.noise(co * 0.8) * 3.0)
        base = lerp(base, ROCK_LOW, 0.16 * band)
        if moss and nrm.z > 0.55:
            base = lerp(base, MOSS, moss * clamp01((nrm.z - 0.55) * 3) * clamp01(noise.noise(co * 0.9 + Vector((seed, 0, 0))) + 0.6))
        return base

    for i in range(pieces):
        s = 1.0 if i == 0 else rnd.uniform(0.35, 0.6)
        ang = rnd.uniform(0, 2 * math.pi)
        off = Vector((0, 0, 0)) if i == 0 else Vector((math.cos(ang) * size[0] * 0.9, math.sin(ang) * size[1] * 0.9, 0))
        p.blob(off + Vector((0, 0, size[2] * s * 0.82)), (size[0] * s, size[1] * s, size[2] * s), colour,
               seed + i * 5, 0.32, 3, strata=0.34)
    p.export()


def bush(name, seed, leaves=14, scale=1.0):
    rnd = random.Random(seed)
    p = Prop(name)
    for k in range(leaves):
        a = 2 * math.pi * k / leaves + rnd.uniform(-0.25, 0.25)
        rise = rnd.uniform(0.3, 1.3)
        d = Vector((math.cos(a), math.sin(a), rise))
        p.blade(Vector((0, 0, 0.05)), d, rnd.uniform(0.9, 1.5) * scale, rnd.uniform(0.2, 0.32) * scale,
                rnd.uniform(0.35, 0.8), leaf_colour, segs=5, fold=0.3)
    p.export()


# --- crafted wooden props: separate staves / planks, chamfer highlights, warm iron -------------
IRON_DARK, IRON_LIGHT, RUST = (0.13, 0.11, 0.10), (0.40, 0.36, 0.31), (0.36, 0.19, 0.10)
GAP = (0.07, 0.04, 0.035)
EDGE_LIT = (0.80, 0.62, 0.38)


def wood_tint(seed):
    """One board's colour: every board gets its own warmth so the piece reads as hand built."""
    rnd = random.Random(seed)
    k = rnd.uniform(0.30, 0.72)
    warm = rnd.uniform(-0.04, 0.05)
    base = lerp(WOOD_DARK, WOOD_LIGHT, k)
    return (clamp01(base[0] + warm), base[1], clamp01(base[2] - warm * 0.5))


def is_chamfer(nrm):
    return max(abs(nrm.x), abs(nrm.y), abs(nrm.z)) < 0.93


def strip(p, a, b, colour, smooth=False):
    """Quads between two polylines of equal length, on fresh vertices so the edges stay hard."""
    va = [p.bm.verts.new(v) for v in a]
    vb = [p.bm.verts.new(v) for v in b]
    faces = [p.bm.faces.new((va[i], va[i + 1], vb[i + 1], vb[i])) for i in range(len(a) - 1)]
    for f in faces:
        f.smooth = smooth
    p.bm.normal_update()
    p.paint(faces, colour)
    return faces


def ngon(p, pts, colour):
    f = p.bm.faces.new([p.bm.verts.new(v) for v in pts])
    p.bm.normal_update()
    p.paint([f], colour)
    return f


def circle(r, z, seg):
    return [Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z)) for k in range(seg + 1)]


def hoop(p, z, r_in, height, thick, seed):
    """Iron band: flat outer face, chamfered top and bottom lips, a riveted lap plate."""
    seg = 32
    ch = thick * 0.45
    prof = [(r_in, z - height / 2), (r_in + thick - ch, z - height / 2), (r_in + thick, z - height / 2 + ch),
            (r_in + thick, z + height / 2 - ch), (r_in + thick - ch, z + height / 2), (r_in, z + height / 2)]
    rnd = random.Random(seed)
    rust_at = rnd.uniform(0, 2 * math.pi)

    def iron(co, nrm):
        a = math.atan2(co.y, co.x)
        c = lerp(IRON_DARK, IRON_LIGHT, clamp01(0.25 + 0.75 * nrm.z))          # lips catch the sky
        return lerp(c, RUST, 0.45 * clamp01(math.cos(a - rust_at)) ** 3)

    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        strip(p, circle(r1, z1, seg), circle(r0, z0, seg), iron, smooth=True)
    rot = Matrix.Rotation(rnd.uniform(0, 2 * math.pi), 4, 'Z')
    p.box((r_in + thick, 0, z), (thick * 1.2, 0.11, height * 0.82),
          lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, 0.55), bevel=0.006, xform=rot)
    for dy in (-0.03, 0.03):
        p.box((r_in + thick * 1.6, dy, z), (0.018, 0.022, 0.022), lambda co, nrm: IRON_LIGHT, xform=rot)


TRUNK_LOW, TRUNK_HIGH, TRUNK_SCAR = (0.36, 0.24, 0.15), (0.74, 0.58, 0.36), (0.22, 0.14, 0.10)
FROND_DRY = (0.62, 0.50, 0.16)


def frond(p, root, direction, length, droop, colour, leaflets=13, width=0.95, rnd=None):
    """Feather frond: an arching rib with a row of drooping leaflets down each side."""
    direction = direction.normalized()
    side = direction.cross(Vector((0, 0, 1)))
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()

    def spine(t):
        return root + direction * (length * t) + Vector((0, 0, -droop * length * t * t))

    pts = [spine(i / 8) for i in range(9)]
    # rib: a thin three-sided strip so it reads from every angle
    for off in (side * 0.035, -side * 0.035, Vector((0, 0, 0.04))):
        strip(p, pts, [q + off * (1.0 - 0.8 * i / 8) for i, q in enumerate(pts)],
              lambda co, nrm: colour(clamp01((co - root).length / length) * 0.5), smooth=False)
    for i in range(leaflets):
        t = 0.12 + 0.88 * (i + 0.5) / leaflets
        a, b = spine(t - 0.42 / leaflets), spine(t + 0.42 / leaflets)
        along = (b - a).normalized()
        reach = width * math.sin(math.pi * (0.10 + 0.86 * t)) ** 0.65
        sag = Vector((0, 0, -reach * (0.38 + 0.25 * t)))
        jitter = rnd.uniform(0.86, 1.1) if rnd else 1.0
        for sgn in (-1, 1):
            out = side * sgn * reach * jitter + along * reach * 0.38 + sag
            mid_a, mid_b = a + out * 0.55 + Vector((0, 0, reach * 0.10)), b + out * 0.55 + Vector((0, 0, reach * 0.10))
            tip = (a + b) / 2 + out
            verts = [p.bm.verts.new(v) for v in (a, b, mid_b, mid_a, tip)]
            faces = [p.bm.faces.new((verts[0], verts[1], verts[2], verts[3])), p.bm.faces.new((verts[3], verts[2], verts[4]))]
            p.bm.normal_update()
            base_t = t

            def leaf(co, nrm, base_t=base_t, a=a, reach=reach):
                u = clamp01((co - a).length / max(reach, 1e-4))
                return colour(clamp01(0.15 + 0.55 * base_t + 0.45 * u))

            p.paint(faces, leaf)


def palm(name, height, lean, bend, seed, fronds=9):
    rnd = random.Random(seed)
    p = Prop(name)
    heading = rnd.uniform(0, 2 * math.pi)
    ldir = Vector((math.cos(heading), math.sin(heading), 0))
    segs = int(height * 3.2)

    def centre(t):
        return ldir * (lean * t + bend * math.sin(math.pi * t)) + Vector((0, 0, height * t))

    def girth(t):
        return (0.34 - 0.16 * t) * (1.0 + 0.9 * (1 - t) ** 7)      # flared foot

    # stacked collars: each segment is wider at its top lip, like old frond scars
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        axis = centre(min(t1 + 0.02, 1.0)) - centre(max(t0 - 0.02, 0.0))
        tint = rnd.uniform(-0.08, 0.10)

        def bark(co, nrm, t0=t0, t1=t1, tint=tint):
            t = clamp01(co.z / height)
            u = clamp01((t - t0) / max(t1 - t0, 1e-4))
            c = lerp(TRUNK_LOW, TRUNK_HIGH, clamp01(t ** 0.7 + tint))
            return lerp(TRUNK_SCAR, c, clamp01(0.25 + 1.3 * u))      # dark crease under every lip

        p.tube([(centre(t0), girth(t0) * 0.90, axis), (centre(t0 * 0.3 + t1 * 0.7), girth(t1) * 1.07, axis),
                (centre(t1), girth(t1) * 0.97, axis)], bark, sides=12, cap=(i == 0))
    top = centre(1.0)
    p.blob(top + Vector((0, 0, 0.10)), (0.40, 0.40, 0.36),
           lambda co, nrm: lerp((0.30, 0.22, 0.10), LEAF_MID, clamp01((co.z - top.z) * 2.2 + 0.35)), seed, 0.12, 2, smooth=True)
    crown = top + Vector((0, 0, 0.22))
    n = fronds + 5
    for k in range(n):                                              # upper, living fronds
        a = heading + 2 * math.pi * k / n + rnd.uniform(-0.18, 0.18)
        rise = rnd.uniform(0.35, 0.95) if k % 2 else rnd.uniform(0.0, 0.4)
        frond(p, crown, Vector((math.cos(a), math.sin(a), rise)), rnd.uniform(3.0, 3.9), rnd.uniform(0.55, 0.85),
              leaf_colour, rnd=rnd)
    for k in range(fronds - 2):                                     # hanging skirt, yellowing
        a = heading + 2 * math.pi * (k + 0.5) / (fronds - 2) + rnd.uniform(-0.2, 0.2)
        dry = rnd.uniform(0.25, 0.9)
        frond(p, top, Vector((math.cos(a), math.sin(a), rnd.uniform(-0.55, -0.15))), rnd.uniform(2.3, 3.0),
              rnd.uniform(0.45, 0.7), lambda t, dry=dry: lerp(leaf_colour(t), FROND_DRY, dry * (0.35 + 0.65 * t)),
              leaflets=10, width=0.8, rnd=rnd)
    for k in range(rnd.randint(4, 6)):                              # coconuts
        a = heading + 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        p.blob(top + Vector((math.cos(a) * 0.36, math.sin(a) * 0.36, -0.20 - rnd.uniform(0, 0.12))), (0.19, 0.19, 0.22),
               lambda co, nrm: lerp((0.20, 0.12, 0.05), (0.56, 0.40, 0.17), clamp01(nrm.z * 0.6 + 0.5)), seed + k, 0.05, 2, smooth=True)
    p.export()


def barrel(name):
    p = Prop(name)
    h, staves, segs, thick = 1.1, 14, 10, 0.035

    def radius(z):
        return 0.36 + 0.09 * math.sin(math.pi * clamp01(z / h)) ** 0.85

    def pt(a, z, inset=0.0):
        return Vector(((radius(z) - inset) * math.cos(a), (radius(z) - inset) * math.sin(a), z))

    # dark core fills the joints between staves
    core = [0.03 + (h - 0.06) * i / 6 for i in range(7)]
    p.tube([(Vector((0, 0, z)), radius(z) - 0.012, Vector((0, 0, 1))) for z in core], lambda co, nrm: GAP, sides=20)
    zs = [h * i / segs for i in range(segs + 1)]
    for k in range(staves):
        tint = wood_tint(k * 7 + 1)
        a0 = 2 * math.pi * k / staves + 0.012
        a1 = 2 * math.pi * (k + 1) / staves - 0.012
        am = (a0 + a1) / 2

        def wood(co, nrm, tint=tint):
            t = clamp01(co.z / h)
            c = lerp(lerp(tint, WOOD_DARK, 0.45), tint, clamp01(0.25 + 1.1 * t))   # grounded base, lit top
            c = lerp(WOOD_DARK, c, clamp01(0.55 + min(t, 1 - t) * 6))              # worn dark ends
            if nrm.z > 0.7:
                c = lerp(c, EDGE_LIT, 0.55)                                         # sun-bleached rim
            return c

        def side(co, nrm, tint=tint):
            return lerp(tint, GAP, 0.7)

        def inside(co, nrm, tint=tint):
            return lerp(tint, WOOD_DARK, 0.6)

        outer0, outerm, outer1 = [pt(a0, z, 0.006) for z in zs], [pt(am, z) for z in zs], [pt(a1, z, 0.006) for z in zs]
        inner0, inner1 = [pt(a0, z, thick) for z in zs], [pt(a1, z, thick) for z in zs]
        # outer face in two facets so each stave has a soft crown
        va = [p.bm.verts.new(v) for v in outer0]
        vm = [p.bm.verts.new(v) for v in outerm]
        vb = [p.bm.verts.new(v) for v in outer1]
        faces = []
        for i in range(segs):
            faces.append(p.bm.faces.new((va[i], vm[i], vm[i + 1], va[i + 1])))
            faces.append(p.bm.faces.new((vm[i], vb[i], vb[i + 1], vm[i + 1])))
        for f in faces:
            f.smooth = True
        p.bm.normal_update()
        p.paint(faces, wood)
        strip(p, outer0, inner0, side)
        strip(p, inner1, outer1, side)
        strip(p, inner0, inner1, inside, smooth=True)
        ngon(p, [outer0[-1], outerm[-1], outer1[-1], inner1[-1], inner0[-1]], wood)
        ngon(p, [inner0[0], inner1[0], outer1[0], outerm[0], outer0[0]], wood)
    # lids: five boards each, set in below the rim
    for z, up in ((h - 0.07, True), (0.07, False)):
        r, n = radius(z) - thick + 0.004, 5
        for b in range(n):
            x0, x1 = -r + 2 * r * b / n + 0.006, -r + 2 * r * (b + 1) / n - 0.006
            xs = [x0 + (x1 - x0) * i / 4 for i in range(5)]
            top = [Vector((x, math.sqrt(max(r * r - x * x, 0.0)), z)) for x in xs]
            bot = [Vector((x, -math.sqrt(max(r * r - x * x, 0.0)), z)) for x in reversed(xs)]
            pts = top + bot
            if up:
                pts.reverse()
            tint = wood_tint(100 + b + (7 if up else 0))
            ngon(p, pts, lambda co, nrm, tint=tint, r=r: lerp(tint, WOOD_DARK, 0.25 + 0.5 * (Vector((co.x, co.y)).length / r) ** 4))
    for i, z in enumerate((0.10, 0.34, 0.76, 1.00)):
        hoop(p, z, max(radius(z - 0.03), radius(z + 0.03)) + 0.001, 0.07 if i in (0, 3) else 0.055, 0.016, 40 + i)
    # bung
    p.tube([(Vector((radius(0.55) - 0.01, 0, 0.55)), 0.045, Vector((1, 0, 0))),
            (Vector((radius(0.55) + 0.03, 0, 0.55)), 0.038, Vector((1, 0, 0)))],
           lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.2 + 0.6 * clamp01(nrm.x)), sides=10, smooth=False)
    p.export()


def crate(name):
    p = Prop(name)
    s, beam, board = 0.9, 0.105, 0.03
    e = s / 2

    def painted(tint, lo):
        def fn(co, nrm):
            c = lerp(lerp(tint, WOOD_DARK, lo), tint, clamp01(0.2 + co.z / s))
            if is_chamfer(nrm):
                c = lerp(c, EDGE_LIT, 0.5)                             # chamfers read as worn, lit edges
            elif nrm.z > 0.9:
                c = lerp(c, EDGE_LIT, 0.18)
            elif nrm.z < -0.9:
                c = lerp(c, WOOD_DARK, 0.5)
            return c
        return fn

    p.box((0, 0, e), (s - 0.07, s - 0.07, s - 0.07), lambda co, nrm: GAP)
    # four boards per face, running a different way on neighbouring faces
    n, inner = 4, s - 2 * beam + 0.02
    w = inner / n
    seed = 0
    for axis in range(3):
        run = 0 if axis == 2 else 2
        across = 3 - axis - run
        for sign in (-1, 1):
            for b in range(n):
                seed += 1
                centre, size = [0, 0, e], [0, 0, 0]
                centre[axis] += sign * (e - board / 2 - 0.012)
                centre[across] += -inner / 2 + w * (b + 0.5)
                size[axis], size[across], size[run] = board, w - 0.012, inner
                p.box(centre, size, painted(wood_tint(seed * 3), 0.35), bevel=0.006)
    # frame: uprights full height, rails between them a touch slimmer
    i = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            i += 1
            p.box((sx * (e - beam / 2), sy * (e - beam / 2), e), (beam, beam, s),
                  painted(lerp(wood_tint(500 + i), WOOD_DARK, 0.28), 0.4), bevel=0.012)
    rail = beam - 0.012
    for z in (rail / 2, s - rail / 2):
        for sgn in (-1, 1):
            i += 1
            p.box((sgn * (e - rail / 2 - 0.006), 0, z), (rail, s - 2 * beam, rail),
                  painted(lerp(wood_tint(500 + i), WOOD_DARK, 0.28), 0.4), bevel=0.01)
            i += 1
            p.box((0, sgn * (e - rail / 2 - 0.006), z), (s - 2 * beam, rail, rail),
                  painted(lerp(wood_tint(500 + i), WOOD_DARK, 0.28), 0.4), bevel=0.01)
    # diagonal brace on the four sides
    span = s - 2 * beam + 0.03
    for k in range(4):
        tint = lerp(wood_tint(600 + k), WOOD_DARK, 0.2)
        rot = (Matrix.Rotation(k * math.pi / 2, 4, 'Z') @ Matrix.Translation((e - 0.018, 0, e))
               @ Matrix.Rotation(math.radians(45 if k % 2 else -45), 4, 'X'))
        p.box((0, 0, 0), (0.03, 0.085, span * 1.36), None, bevel=0.008, xform=rot,
              local_paint=lambda co, nrm, t=tint: lerp(t, EDGE_LIT, 0.5 if is_chamfer(nrm) else 0.0))
    # iron corner caps with a rivet on each visible face
    cap = 0.135

    def iron(co, nrm):
        c = lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.6 * nrm.z))
        if is_chamfer(nrm):
            c = lerp(c, (0.62, 0.56, 0.48), 0.6)
        return lerp(c, RUST, 0.25 * clamp01(noise.noise(co * 6.0) + 0.3))

    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                c = Vector((sx * (e - cap / 2 + 0.01), sy * (e - cap / 2 + 0.01), e + sz * (e - cap / 2 + 0.01)))
                p.box(c, (cap, cap, cap), iron, bevel=0.014)
                for d in (Vector((sx, 0, 0)), Vector((0, sy, 0)), Vector((0, 0, sz))):
                    p.box(c + d * (cap / 2), (0.03, 0.03, 0.03), lambda co, nrm: (0.55, 0.50, 0.43), bevel=0.008)
    p.export()


# --- outpost buildings: weathered planks, chunky posts, nothing quite straight ------------------
WEATHER = (0.47, 0.40, 0.33)
THATCH_A, THATCH_B = (0.42, 0.33, 0.20), (0.70, 0.58, 0.32)


def plank(p, centre, size, seed, rot=None, grey=0.45, bevel=0.012, lift=0.0):
    """One weathered board. Painted in its own space so chamfers stay highlighted after it is turned."""
    tint = lerp(wood_tint(seed), WEATHER, grey)
    lo = min(size)
    span = max(size[2], 0.01)

    def paint(co, nrm, tint=tint):
        k = clamp01((co.z - centre[2]) / span + 0.5)
        c = lerp(lerp(tint, WOOD_DARK, 0.35), tint, 0.35 + 0.65 * k)
        if is_chamfer(nrm):
            c = lerp(c, EDGE_LIT, 0.45)
        elif nrm.z > 0.9:
            c = lerp(c, EDGE_LIT, 0.15 + lift)
        return c

    return p.box(centre, size, None, bevel=min(bevel, lo * 0.3), xform=rot, local_paint=paint)


def post(p, x, y, z0, z1, r, seed, lean=(0.0, 0.0)):
    """Round timber post with a darker waterline foot and a lit top."""
    tint = lerp(wood_tint(seed), WEATHER, 0.35)
    axis = Vector((lean[0], lean[1], 1.0))
    rings = [(Vector((x + lean[0] * (z - z0), y + lean[1] * (z - z0), z)), r * (1.0 + 0.06 * math.sin(i * 2.1)), axis)
             for i, z in enumerate([z0 + (z1 - z0) * k / 4 for k in range(5)])]

    def paint(co, nrm):
        k = clamp01((co.z - z0) / max(z1 - z0, 0.01))
        c = lerp(lerp(tint, (0.16, 0.14, 0.12), 0.6), tint, clamp01(0.15 + 1.4 * k))
        return lerp(c, EDGE_LIT, 0.5) if nrm.z > 0.8 else c

    p.tube(rings, paint, sides=8, smooth=False)


def roof_side(p, ridge_a, ridge_b, drop, out, rows, seed, thatch=True):
    """Rows of overlapping shingle boards from the ridge down one slope."""
    rnd = random.Random(seed)
    along = ridge_b - ridge_a
    length = along.length
    along.normalize()
    down = (out * 1.0 + Vector((0, 0, -drop))).normalized()
    slope_len = math.hypot(out.length, drop)
    normal = along.cross(down).normalized()
    if normal.z < 0:
        normal = -normal
    rot3 = Matrix((along, down, normal)).transposed().to_4x4()
    for r in range(rows):
        t0 = r / rows
        n = max(3, int(length / 0.55))
        for k in range(n):
            w = length / n
            c = ridge_a + along * (w * (k + 0.5)) + down * (slope_len * (t0 + 0.6 / rows)) + normal * (0.03 + 0.05 * (rows - r) / rows)
            base = lerp(THATCH_A, THATCH_B, rnd.uniform(0.0, 1.0)) if thatch else lerp(wood_tint(seed + k + r * 31), WEATHER, 0.6)
            size = (w * rnd.uniform(0.86, 0.98), slope_len / rows * 1.35, 0.05)

            def paint(co, nrm, base=base, sy=size[1]):
                k2 = clamp01(co.y / sy + 0.5)
                c = lerp(base, lerp(base, (0.18, 0.13, 0.09), 0.6), k2 ** 2)     # dark lower lip
                return lerp(c, EDGE_LIT, 0.4) if is_chamfer(nrm) else c

            m = Matrix.Translation(c) @ rot3 @ Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, 'Z')
            p.box((0, 0, 0), size, None, bevel=0.012, xform=m, local_paint=paint)


def hut(name, w, d, wall, stilts, seed, thatch=True, finish=True):
    """Plank hut on posts: gapped vertical boards, a door and window, a steep overhanging roof."""
    rnd = random.Random(seed)
    p = Prop(name)
    hx, hy = w / 2, d / 2
    z0 = stilts
    for sx in (-1, 1):
        for sy in (-1, 0, 1):
            post(p, sx * (hx - 0.12), sy * (hy - 0.12), -0.6, z0 + wall + 0.15, 0.14, seed + sx * 3 + sy,
                 lean=(rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02)))
    n = int(d / 0.34)
    for k in range(n):                                              # floor boards
        y = -hy + d * (k + 0.5) / n
        plank(p, (0, y, z0 - 0.05), (w + 0.5, d / n * 0.93, 0.07), seed * 7 + k, grey=0.5)
    for sx in (-1, 1):
        plank(p, (sx * (hx - 0.1), 0, z0 - 0.18), (0.16, d + 0.3, 0.2), seed + 90 + sx, grey=0.3)
    door_x = rnd.uniform(-hx * 0.4, hx * 0.2)
    for side, (ax, half, fixed) in enumerate(((0, hx, -hy), (0, hx, hy), (1, hy, -hx), (1, hy, hx))):
        m = int(2 * half / 0.30)
        for k in range(m):
            u = -half + 2 * half * (k + 0.5) / m
            top = wall * rnd.uniform(0.94, 1.03)
            bottom = 0.0
            if side == 0 and abs(u - door_x) < 0.55:
                bottom = 2.05                                       # doorway
            if side == 2 and abs(u) < 0.5:
                bottom, top = 0.0, 0.95                             # window sill
            if side == 2 and abs(u) < 0.5:
                plank(p, (fixed, u, z0 + 1.95 + (wall - 1.95) / 2) if ax else (u, fixed, z0 + 1.6),
                      (0.05, 2 * half / m * 0.9, wall - 1.95) if ax else (2 * half / m * 0.9, 0.05, wall - 1.95), seed * 13 + side * 100 + k + 500)
            if top - bottom < 0.2:
                continue
            c = (u, fixed, z0 + (top + bottom) / 2) if ax == 0 else (fixed, u, z0 + (top + bottom) / 2)
            s = (2 * half / m * 0.9, 0.05, top - bottom) if ax == 0 else (0.05, 2 * half / m * 0.9, top - bottom)
            plank(p, c, s, seed * 13 + side * 100 + k, rot=None, grey=rnd.uniform(0.3, 0.6))
        for z in (0.25, wall - 0.2):                                # rails tying the boards together
            c = (0, fixed * 1.0 + (0.05 if fixed > 0 else -0.05), z0 + z) if ax == 0 else (fixed + (0.05 if fixed > 0 else -0.05), 0, z0 + z)
            s = (2 * half, 0.07, 0.13) if ax == 0 else (0.07, 2 * half, 0.13)
            if not (side == 0 and z < 1.0):
                plank(p, c, s, seed + 200 + side * 2 + int(z * 10), grey=0.25)
    rise, over = w * 0.52, 0.55
    ridge_a, ridge_b = Vector((0, -hy - over, z0 + wall + rise)), Vector((0, hy + over, z0 + wall + rise))
    roof_side(p, ridge_a, ridge_b, rise + 0.35, Vector((hx + over, 0, 0)), 5, seed + 1, thatch)
    roof_side(p, ridge_b, ridge_a, rise + 0.35, Vector((-hx - over, 0, 0)), 5, seed + 2, thatch)
    plank(p, (0, 0, z0 + wall + rise + 0.06), (0.2, d + 2 * over + 0.2, 0.18), seed + 300, grey=0.2)
    for sy in (-1, 1):                                              # gable infill
        for k in range(int(w / 0.3)):
            u = -hx + w * (k + 0.5) / int(w / 0.3)
            hgt = rise * (1 - abs(u) / hx) - 0.05
            if hgt > 0.12:
                plank(p, (u, sy * hy, z0 + wall + hgt / 2), (w / int(w / 0.3) * 0.9, 0.05, hgt), seed * 17 + k + (50 if sy > 0 else 0), grey=0.5)
    if stilts > 0.4:                                                # steps up to the door
        steps = int(stilts / 0.22)
        for k in range(steps):
            plank(p, (door_x, -hy - 0.25 - 0.28 * (steps - k), 0.22 * (k + 0.5)), (1.0, 0.26, 0.06), seed + 400 + k, grey=0.4)
        for sx in (-1, 1):
            rot = Matrix.Translation((door_x + sx * 0.52, -hy - 0.25 - 0.14 * steps, stilts / 2)) @ Matrix.Rotation(math.atan2(stilts, 0.28 * steps), 4, 'X')
            plank(p, (0, 0, 0), (0.07, math.hypot(stilts, 0.28 * steps) + 0.3, 0.14), seed + 450 + sx, rot=rot, grey=0.3)
    if finish:
        p.export()
    return p


def tower(name, seed):
    """Lookout: splayed legs, cross braces, a round plank cabin under a conical roof."""
    rnd = random.Random(seed)
    p = Prop(name)
    deck, foot, top = 9.0, 2.3, 1.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            lean = ((top - foot) * sx / (deck + 0.6), (top - foot) * sy / (deck + 0.6))
            post(p, sx * foot, sy * foot, -0.6, deck, 0.17, seed + sx + 2 * sy, lean=lean)
    for level in range(3):
        z0, z1 = 0.6 + level * 2.8, 0.6 + (level + 1) * 2.8
        r0 = foot + (top - foot) * z0 / deck
        r1 = foot + (top - foot) * z1 / deck
        for side in range(4):
            turn = Matrix.Rotation(side * math.pi / 2, 4, 'Z')
            for flip in (-1, 1):
                a, b = Vector((-flip * r0, -(r0 + r1) / 2, z0)), Vector((flip * r1, -(r0 + r1) / 2, z1))
                d = b - a
                m = turn @ Matrix.Translation((a + b) / 2) @ Matrix.Rotation(math.atan2(d.z, d.x) * -1, 4, 'Y')
                plank(p, (0, 0, 0), (d.length, 0.06, 0.13), seed + level * 20 + side * 3 + flip, rot=m, grey=0.3)
            plank(p, (0, 0, 0), (2 * r1 + 0.3, 0.09, 0.14), seed + 70 + level * 4 + side, rot=turn @ Matrix.Translation((0, -r1, z1)), grey=0.2)
    for k in range(12):                                             # deck
        x = -2.4 + 4.8 * (k + 0.5) / 12
        half = math.sqrt(max(2.5 ** 2 - x * x, 0.2))
        plank(p, (x, 0, deck + 0.04), (0.37, 2 * half, 0.07), seed + 100 + k, grey=0.5)
    n, r, h = 18, 1.75, 2.7
    for k in range(n):                                              # cabin staves, one gap for the door
        if k in (4, 5):
            continue
        a = 2 * math.pi * k / n
        m = Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((r, 0, deck + 0.08 + h / 2))
        plank(p, (0, 0, 0), (0.06, 2 * math.pi * r / n * 0.92, h * rnd.uniform(0.95, 1.0)), seed + 130 + k, rot=m, grey=rnd.uniform(0.2, 0.5))
    for z in (deck + 0.5, deck + h - 0.3):
        rings = [(Vector((0, 0, z - 0.06)), r + 0.05, Vector((0, 0, 1))), (Vector((0, 0, z + 0.06)), r + 0.05, Vector((0, 0, 1)))]
        p.tube(rings, lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + nrm.z)), sides=18, cap=False)
    roof = [(Vector((0, 0, deck + h + 0.0)), 2.55, Vector((0, 0, 1))), (Vector((0, 0, deck + h + 0.55)), 1.75, Vector((0, 0, 1))),
            (Vector((0, 0, deck + h + 1.25)), 0.85, Vector((0, 0, 1))), (Vector((0, 0, deck + h + 1.9)), 0.12, Vector((0, 0, 1)))]

    def thatch(co, nrm):
        a = math.atan2(co.y, co.x)
        k = clamp01((co.z - deck - h) / 1.9)
        return lerp(lerp(THATCH_A, THATCH_B, 0.5 + 0.5 * math.sin(a * 9)), (0.86, 0.72, 0.42), 0.5 * k)

    p.tube(roof, thatch, sides=18, smooth=False)
    for k in range(int(deck / 0.42)):                               # ladder
        plank(p, (0, -foot - 0.25 + (foot - top) * (0.42 * k) / deck, 0.42 * (k + 0.6)), (0.6, 0.06, 0.06), seed + 300 + k, grey=0.3, bevel=0.0)
    p.export()


def dock(name, length, seed):
    """Pier running along +x from the beach: sagging boards, post pairs, a few braces."""
    rnd = random.Random(seed)
    p = Prop(name)
    width, deck = 3.0, 1.25
    n = int(length / 0.42)
    for k in range(n):
        if rnd.random() < 0.04:
            continue                                                # a missing board
        x = length * (k + 0.5) / n
        m = Matrix.Translation((x, rnd.uniform(-0.06, 0.06), deck + rnd.uniform(-0.02, 0.02))) @ Matrix.Rotation(rnd.uniform(-0.03, 0.03), 4, 'Z')
        plank(p, (0, 0, 0), (0.37, width + rnd.uniform(-0.15, 0.25), 0.07), seed * 5 + k, rot=m, grey=rnd.uniform(0.35, 0.65))
    for sy in (-1, 1):
        plank(p, (length / 2, sy * (width / 2 - 0.25), deck - 0.14), (length, 0.16, 0.2), seed + 500 + sy, grey=0.25)
    for k in range(int(length / 4.5) + 1):
        x = min(length - 0.3, 0.4 + k * 4.5)
        for sy in (-1, 1):
            tall = deck + rnd.uniform(0.5, 1.5)
            post(p, x, sy * (width / 2 + 0.05), -5.5, tall, 0.16, seed + 600 + k * 2 + sy,
                 lean=(rnd.uniform(-0.015, 0.015), sy * rnd.uniform(0.0, 0.02)))
        plank(p, (x, 0, deck - 0.32), (0.14, width + 0.5, 0.16), seed + 700 + k, grey=0.2)
        if k % 2 == 0:
            m = Matrix.Translation((x, 0, deck - 1.3)) @ Matrix.Rotation(0.6, 4, 'X')
            plank(p, (0, 0, 0), (0.08, width + 1.2, 0.12), seed + 800 + k, rot=m, grey=0.2)
    p.export()


def boulder(name, size, seed):
    """Sun-warmed beach boulder: big soft facets, pale top, rosy shadow side."""
    p = Prop(name)
    rnd = random.Random(seed)

    def colour(co, nrm):
        k = clamp01(nrm.z * 0.6 + 0.45)
        c = lerp((0.50, 0.34, 0.30), (0.93, 0.76, 0.58), k)
        return lerp(c, (0.36, 0.26, 0.26), clamp01(0.5 - co.z / size[2]) * 0.6)

    p.blob((0, 0, size[2] * 0.42), size, colour, seed, rough=0.22, subdiv=3, strata=0.0, smooth=False)
    if rnd.random() < 0.7:
        p.blob((size[0] * 0.7, size[1] * 0.3, size[2] * 0.22), (size[0] * 0.45, size[1] * 0.5, size[2] * 0.4), colour, seed + 3, rough=0.2, subdiv=2)
    p.export()


# --- outpost landmarks (see Docs/SoT-Reference-Notes.md): tavern, order hut, hoarder tent, shipwright, dock stall ---
CLOTH_CREAM, CLOTH_SHADE = (0.93, 0.88, 0.74), (0.62, 0.58, 0.52)


def cloth(p, pts, colour, shade=None):
    """A sheet of canvas through the given corner points, lighter at the top."""
    shade = shade or tuple(c * 0.6 for c in colour)
    zs = [v.z for v in pts]
    lo, hi = min(zs), max(zs)
    ngon(p, [Vector(v) for v in pts], lambda co, nrm: lerp(shade, colour, clamp01((co.z - lo) / max(hi - lo, 0.01))))


def lantern(p, at):
    p.box(at, (0.22, 0.22, 0.30), lambda co, nrm: lerp((1.0, 0.55, 0.12), (1.0, 0.86, 0.40), clamp01((co.z - at[2]) * 4 + 0.5)), bevel=0.03)
    p.box((at[0], at[1], at[2] + 0.2), (0.28, 0.28, 0.06), lambda co, nrm: IRON_DARK)


def alehouse(name):
    """The big one: plank hall, a keel beam riding the ridge and curling up like a prow, a sail canopy over the door."""
    w, d, wall, stilts = 8.5, 12.0, 3.3, 0.5
    p = hut(name, w, d, wall, stilts, 31, thatch=False, finish=False)
    ridge = stilts + wall + w * 0.52
    rings = []
    for i in range(15):                                             # keel: along the ridge, then sweeping up past the front gable
        t = i / 14
        y = d / 2 + 1.2 - (d + 4.6) * t
        lift = 2.6 * max(0.0, (-y - d / 2) / 3.4) ** 1.0
        rings.append((Vector((0, y, ridge + 0.25 + lift)), 0.24 - 0.10 * max(0.0, (-y - d / 2) / 3.4), Vector((0, -1, 0.6 * lift))))
    p.tube(rings, lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, clamp01(0.35 + 0.5 * nrm.z)), sides=8, smooth=False)
    prow = rings[-1][0]
    for sx in (-1, 1):                                              # canopy poles and the sail slung between them
        post(p, sx * 3.4, -d / 2 - 3.6, -0.5, 3.0, 0.11, 77 + sx)
    cloth(p, [prow, Vector((-3.4, -d / 2 - 3.6, 3.0)), Vector((0, -d / 2 - 4.2, 2.6)), Vector((3.4, -d / 2 - 3.6, 3.0))], CLOTH_CREAM, CLOTH_SHADE)
    cloth(p, [prow, Vector((0.9, -d / 2 - 0.3, ridge - 0.8)), Vector((3.4, -d / 2 - 3.6, 3.0))], (0.86, 0.80, 0.66), CLOTH_SHADE)
    cloth(p, [prow, Vector((-3.4, -d / 2 - 3.6, 3.0)), Vector((-0.9, -d / 2 - 0.3, ridge - 0.8))], (0.86, 0.80, 0.66), CLOTH_SHADE)
    sign = [(Vector((0, -d / 2 - 0.22, stilts + wall + 0.9)), 0.95, Vector((0, 1, 0))), (Vector((0, -d / 2 - 0.10, stilts + wall + 0.9)), 0.95, Vector((0, 1, 0)))]
    p.tube(sign, lambda co, nrm: (0.72, 0.38, 0.22) if nrm.y < -0.5 else IRON_DARK, sides=14, smooth=False)
    p.box((0, -d / 2 - 0.26, stilts + wall + 0.9), (1.1, 0.05, 0.16), lambda co, nrm: (0.95, 0.82, 0.50), xform=None)
    p.box((0, -d / 2 - 0.26, stilts + wall + 0.9), (0.16, 0.05, 1.1), lambda co, nrm: (0.95, 0.82, 0.50), xform=None)
    for sx in (-1, 1):
        lantern(p, (sx * 1.5, -d / 2 - 0.25, stilts + 2.1))
        lantern(p, (sx * (w / 2 + 0.2), d * 0.2, stilts + 2.3))
    for k in range(3):                                              # benches out front
        plank(p, (-2.2 + k * 2.2, -d / 2 - 2.4, 0.45), (1.6, 0.4, 0.07), 900 + k, grey=0.3)
        for sx in (-0.6, 0.6):
            plank(p, (-2.2 + k * 2.2 + sx, -d / 2 - 2.4, 0.22), (0.08, 0.34, 0.44), 920 + k, grey=0.3, bevel=0.0)
    p.export()


def warden_hut(name):
    """Lantern Wardens: leaning plank watch hut on a tall deck, crimson storm cloths."""
    w, d, wall, stilts = 4.8, 5.2, 2.8, 1.7
    p = hut(name, w, d, wall, stilts, 47, thatch=False, finish=False)
    for v in p.bm.verts:                                            # settle the whole cabin to one side
        if v.co.z > stilts:
            v.co.x += 0.09 * (v.co.z - stilts) ** 1.15
            v.co.y += 0.03 * (v.co.z - stilts)
    purple, deep = (0.70, 0.16, 0.14), (0.26, 0.05, 0.07)
    cloth(p, [Vector((-w / 2 - 0.1, -d / 2 - 0.12, stilts + wall)), Vector((-w / 2 + 1.3, -d / 2 - 0.12, stilts + wall)),
              Vector((-w / 2 + 1.1, -d / 2 - 0.16, stilts + 0.5)), Vector((-w / 2 - 0.2, -d / 2 - 0.16, stilts + 0.2))], purple, deep)
    cloth(p, [Vector((w / 2 + 0.1, -d / 2 + 0.4, stilts + wall - 0.2)), Vector((w / 2 + 0.1, d / 2 - 0.6, stilts + wall - 0.2)),
              Vector((w / 2 + 0.16, d / 2 - 0.9, stilts + 0.6)), Vector((w / 2 + 0.16, -d / 2 + 0.7, stilts + 0.9))], purple, deep)
    post(p, -w / 2 - 1.3, -d / 2 - 1.6, -0.5, 4.6, 0.09, 61, lean=(0.02, 0.0))
    plank(p, (-w / 2 - 0.8, -d / 2 - 1.6, 4.3), (1.3, 0.07, 0.09), 62, grey=0.2, bevel=0.0)
    cloth(p, [Vector((-w / 2 - 1.3, -d / 2 - 1.62, 4.25)), Vector((-w / 2 - 0.3, -d / 2 - 1.62, 4.25)),
              Vector((-w / 2 - 0.35, -d / 2 - 1.62, 2.9)), Vector((-w / 2 - 0.8, -d / 2 - 1.62, 2.55)), Vector((-w / 2 - 1.25, -d / 2 - 1.62, 2.9))], purple, deep)
    for k, c in enumerate(((0.40, 0.85, 0.75), (0.95, 0.80, 0.30), (0.70, 0.40, 0.90))):                       # hanging bottles
        p.blob((-0.9 + k * 0.9, -d / 2 - 0.5, stilts + wall - 0.55), (0.11, 0.11, 0.16), lambda co, nrm, c=c: lerp(tuple(x * 0.5 for x in c), c, clamp01(nrm.z + 0.6)),
               k, 0.02, 1, smooth=True)
    lantern(p, (1.2, -d / 2 - 0.25, stilts + 2.0))
    p.export()


def salvage_tent(name):
    """Deepfinders: sea-blue salvage tent on a ring of poles, open at the front, copper hem, rug and banner."""
    p = Prop(name)
    apex, r, n = Vector((0, 0, 4.3)), 3.5, 9
    green, deep, gold = (0.12, 0.30, 0.46), (0.04, 0.10, 0.20), (0.84, 0.48, 0.24)
    base = [Vector((math.cos(2 * math.pi * k / n - math.pi / 2) * r, math.sin(2 * math.pi * k / n - math.pi / 2) * r, 0.0)) for k in range(n)]
    eave = [Vector((b.x * 0.92, b.y * 0.92, 1.9)) for b in base]
    for k in range(n):
        a, b = k, (k + 1) % n
        tone = 0.85 + 0.3 * ((k * 7) % 3) / 2
        gcol = tuple(c * tone for c in green)
        ngon(p, [apex, eave[a], eave[b]], lambda co, nrm, gcol=gcol: lerp(deep, gcol, clamp01((co.z - 1.9) / 2.4 * 0.7 + 0.3)))
        if k not in (0, n - 1):                                     # walls, with the front two left open
            hem_a, hem_b = base[a] + Vector((0, 0, 0.32)), base[b] + Vector((0, 0, 0.32))
            ngon(p, [eave[a], hem_a, hem_b, eave[b]], lambda co, nrm, gcol=gcol: lerp(deep, gcol, clamp01(co.z / 1.9)))
            ngon(p, [hem_a, base[a], base[b], hem_b], lambda co, nrm: gold)
        post(p, base[a].x * 0.98, base[a].y * 0.98, -0.3, 2.0, 0.07, 500 + k, lean=(-base[a].x * 0.03, -base[a].y * 0.03))
    for k in (0, n - 1):                                            # door flaps tied back
        a, b = k, (k + 1) % n
        mid = (base[a] + base[b]) / 2
        hinge = eave[b] if k == 0 else eave[a]
        foot = base[b] if k == 0 else base[a]
        ngon(p, [hinge, foot, mid * 0.9 + Vector((0, 0, 0.9))], lambda co, nrm: lerp(deep, green, clamp01(co.z / 1.9)))
    post(p, 0, 0, 0.0, 4.5, 0.09, 520)
    ngon(p, [Vector((-1.5, -0.6, 0.03)), Vector((1.5, -0.6, 0.03)), Vector((1.5, -3.8, 0.03)), Vector((-1.5, -3.8, 0.03))],
         lambda co, nrm: lerp((0.62, 0.12, 0.10), (0.86, 0.68, 0.22), 1.0 if abs(co.x) > 1.25 or co.y < -3.55 or co.y > -0.85 else 0.0))
    for k in range(3):                                              # chests of loot
        plank(p, (-1.6 + k * 1.3, 1.2, 0.3), (0.8, 0.55, 0.55), 540 + k, grey=0.1)
        p.box((-1.6 + k * 1.3, 1.2, 0.6), (0.86, 0.6, 0.08), lambda co, nrm: gold, bevel=0.02)
    post(p, 4.3, -3.2, -0.5, 6.2, 0.11, 560, lean=(0.01, 0.01))
    plank(p, (5.2, -3.2, 5.8), (2.3, 0.1, 0.12), 561, grey=0.2, bevel=0.0)
    navy = (0.07, 0.10, 0.20)
    cloth(p, [Vector((4.5, -3.22, 5.72)), Vector((6.2, -3.22, 5.72)), Vector((6.2, -3.22, 3.7)), Vector((5.35, -3.22, 3.3)), Vector((4.5, -3.22, 3.7))], navy, (0.03, 0.04, 0.09))
    p.box((5.35, -3.25, 4.75), (0.55, 0.03, 0.55), lambda co, nrm: gold, xform=Matrix.Translation((5.35, -3.25, 4.75)) @ Matrix.Rotation(0.785, 4, 'Y') @ Matrix.Translation((-5.35, 3.25, -4.75)))
    lantern(p, (-1.9, -3.4, 1.6))
    p.export()


def smooth_step(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def keelwright(name):
    """Open workshop on stilts over the water: deck, corner posts, tiled roof, lifting boom, stairs down to the dock."""
    rnd = random.Random(71)
    p = Prop(name)
    w, d, deck, eave = 7.0, 6.0, 2.3, 5.2
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            tall = eave if sx != 0 and sy != 0 else deck
            post(p, sx * (w / 2 - 0.15), sy * (d / 2 - 0.15), -5.5, tall, 0.16, 300 + sx * 3 + sy, lean=(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01)))
    n = int(w / 0.36)
    for k in range(n):
        plank(p, (-w / 2 + w * (k + 0.5) / n, 0, deck), (w / n * 0.92, d + 0.4, 0.08), 320 + k, grey=rnd.uniform(0.3, 0.55))
    for sy in (-1, 1):
        plank(p, (0, sy * (d / 2 - 0.15), eave), (w + 0.6, 0.18, 0.2), 360 + sy, grey=0.2)
        plank(p, (0, sy * (d / 2 - 0.15), deck + 1.0), (w, 0.08, 0.1), 364 + sy, grey=0.3, bevel=0.0)
    for sx in (-1, 1):
        plank(p, (sx * (w / 2 - 0.15), 0, eave), (0.18, d + 0.6, 0.2), 370 + sx, grey=0.2)
    rise = 1.9
    a, b = Vector((-w / 2 - 0.6, 0, eave + rise)), Vector((w / 2 + 0.6, 0, eave + rise))
    global THATCH_A, THATCH_B
    keep = (THATCH_A, THATCH_B)
    THATCH_A, THATCH_B = (0.42, 0.16, 0.10), (0.74, 0.34, 0.20)                 # fired clay tiles
    roof_side(p, a, b, rise + 0.3, Vector((0, -d / 2 - 0.7, 0)), 5, 81, True)
    roof_side(p, b, a, rise + 0.3, Vector((0, d / 2 + 0.7, 0)), 5, 82, True)
    THATCH_A, THATCH_B = keep
    plank(p, (0, 0, eave + rise + 0.05), (w + 1.4, 0.2, 0.2), 390, grey=0.2)
    plank(p, (w / 2 + 1.2, 0.8, eave - 0.3), (3.4, 0.16, 0.18), 391, grey=0.2)                # lifting boom
    p.box((w / 2 + 2.6, 0.8, eave - 1.3), (0.05, 0.05, 1.8), lambda co, nrm: (0.50, 0.42, 0.30))
    p.box((w / 2 + 2.6, 0.8, eave - 2.3), (0.22, 0.08, 0.26), lambda co, nrm: IRON_LIGHT, bevel=0.03)
    plank(p, (-1.6, 1.4, deck + 0.5), (2.2, 0.9, 0.9), 395, grey=0.25)                         # workbench
    plank(p, (-1.6, 1.4, deck + 1.0), (2.5, 1.1, 0.08), 396, grey=0.4)
    steps = 5                                                       # stairs toward -y, down to dock height
    for k in range(steps):
        plank(p, (1.8, -d / 2 - 0.2 - 0.32 * (k + 0.5), deck - 0.21 * (k + 1)), (1.5, 0.3, 0.07), 400 + k, grey=0.4)
    lantern(p, (-w / 2 + 0.3, -d / 2 + 0.3, eave - 0.6))
    lantern(p, (w / 2 - 0.3, d / 2 - 0.3, eave - 0.6))
    p.export()


def market_stall(name):
    """Merchant stand for the dock: striped awning on four poles, counter, ledger board, stacked crates."""
    p = Prop(name)
    w, d = 3.6, 2.4
    for sx in (-1, 1):
        post(p, sx * w / 2, -d / 2, 0.0, 2.9, 0.07, 700 + sx)
        post(p, sx * w / 2, d / 2, 0.0, 2.3, 0.07, 704 + sx)
    stripes = 8
    for k in range(stripes):
        x0, x1 = -w / 2 - 0.3 + (w + 0.6) * k / stripes, -w / 2 - 0.3 + (w + 0.6) * (k + 1) / stripes
        c = (0.93, 0.86, 0.66) if k % 2 else (0.16, 0.50, 0.50)
        cloth(p, [Vector((x0, -d / 2 - 0.4, 3.0)), Vector((x1, -d / 2 - 0.4, 3.0)), Vector((x1, d / 2 + 0.5, 2.25)), Vector((x0, d / 2 + 0.5, 2.25))], c)
        cloth(p, [Vector((x0, d / 2 + 0.5, 2.25)), Vector((x1, d / 2 + 0.5, 2.25)), Vector(((x0 + x1) / 2, d / 2 + 0.55, 1.95))], c)
    plank(p, (0, 0.2, 0.95), (w - 0.3, 0.8, 0.08), 710, grey=0.3)
    for sx in (-1, 1):
        plank(p, (sx * (w / 2 - 0.4), 0.2, 0.47), (0.1, 0.7, 0.9), 712 + sx, grey=0.3, bevel=0.0)
    board = Matrix.Translation((w / 2 + 0.7, 0.6, 0.85)) @ Matrix.Rotation(-0.28, 4, 'X')
    p.box((0, 0, 0), (1.1, 0.06, 1.6), None, bevel=0.02, xform=board, local_paint=lambda co, nrm: (0.10, 0.20, 0.18) if abs(co.x) < 0.48 and abs(co.z) < 0.72 else (0.50, 0.36, 0.20))
    for k, (x, y, s) in enumerate(((-1.2, -0.7, 0.7), (-0.5, -0.8, 0.55), (-1.1, -0.75, 0.5))):
        plank(p, (x, y, s / 2 + (0.7 if k == 2 else 0.0)), (s, s, s), 730 + k, grey=0.2)
    lantern(p, (w / 2 - 0.2, -d / 2 + 0.1, 2.3))
    p.export()


# --- rock kit: worn slabs. One mesh per shape; islands are built by stacking scaled, tilted instances -------------
SLAB_SUN, SLAB_SHADE, SLAB_FOOT = (0.97, 0.89, 0.72), (0.46, 0.50, 0.61), (0.36, 0.38, 0.32)
#            name            half extents (m)   cuts  shear  taper
SLABS = [("SM_BW_Slab_01", (3.0, 2.6, 5.0), 4, 0.20, (0.62, 0.90)),      # tall block
         ("SM_BW_Slab_02", (4.0, 3.4, 2.4), 4, 0.18, (0.70, 0.95)),      # squat block
         ("SM_BW_Slab_03", (3.5, 2.4, 3.2), 5, 0.38, (0.50, 0.75)),      # wedge
         ("SM_BW_Slab_04", (4.5, 3.6, 1.2), 3, 0.12, (0.80, 0.98)),      # plate
         ("SM_BW_Slab_05", (1.8, 1.6, 6.0), 4, 0.16, (0.55, 0.85)),      # pillar
         ("SM_BW_Slab_06", (3.0, 3.0, 3.0), 5, 0.22, (0.65, 0.92)),      # cube
         ("SM_BW_Slab_07", (5.5, 2.4, 2.2), 4, 0.20, (0.70, 0.95)),      # long bar
         ("SM_BW_Slab_08", (2.6, 2.2, 4.4), 5, 0.34, (0.55, 0.80)),      # leaning tooth
         ("SM_BW_Slab_09", (4.2, 3.8, 3.0), 1, 0.06, (0.88, 0.98)),      # flat-topped terrace
         ("SM_BW_Slab_10", (1.6, 1.3, 1.1), 3, 0.20, (0.65, 0.92)),      # beach boulder
         ("SM_BW_Slab_11", (2.4, 2.0, 7.5), 3, 0.10, (0.35, 0.55)),      # spire tip
         ("SM_BW_Slab_12", (5.0, 4.4, 4.0), 6, 0.25, (0.60, 0.85))]      # broken mass


def slab_rock(name, half, cuts, shear_amount, taper_range, seed):
    """A box cut by a few planes, then bevelled wide: broad faces, soft worn shoulders. Pivot at the base centre."""
    rnd = random.Random(seed)
    p = Prop(name)
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=2.0)
    taper = rnd.uniform(*taper_range)
    shear = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * shear_amount
    for v in tmp.verts:
        if v.co.z > 0:
            v.co.x = v.co.x * taper + shear.x
            v.co.y = v.co.y * taper + shear.y
    for _ in range(cuts):
        nrm = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 0.9))).normalized()
        res = bmesh.ops.bisect_plane(tmp, geom=tmp.verts[:] + tmp.edges[:] + tmp.faces[:], dist=1e-5,
                                     plane_co=nrm * rnd.uniform(0.78, 1.05), plane_no=nrm, clear_outer=True)
        edges = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
        if len(edges) >= 3:
            bmesh.ops.edgeloop_fill(tmp, edges=edges)
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces[:])
    bmesh.ops.bevel(tmp, geom=tmp.edges[:], offset=rnd.uniform(0.17, 0.25), segments=3, profile=0.5, affect='EDGES',
                    clamp_overlap=True)
    for v in tmp.verts:
        v.co = Vector((v.co.x * half[0], v.co.y * half[1], v.co.z * half[2]))
    low = min(v.co.z for v in tmp.verts)
    for v in tmp.verts:
        v.co.z -= low
    tmp.normal_update()
    tall = max(v.co.z for v in tmp.verts)
    sun = Vector((0.30, -0.42, 0.86)).normalized()
    made = {v: p.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        try:
            nf = p.bm.faces.new([made[v] for v in f.verts])
        except ValueError:
            continue
        nf.smooth = True
        for loop, src in zip(nf.loops, f.verts):
            n, z = src.normal, src.co.z
            lit = max(0.0, n.dot(sun)) ** 0.8
            c = lerp(SLAB_SHADE, SLAB_SUN, lit * 0.90 + 0.08)
            band = 0.5 + 0.5 * math.sin(z * 1.2 + seed)
            c = lerp(c, (c[0] * 0.90, c[1] * 0.90, c[2] * 0.93), 0.5 * band * (1.0 - abs(n.z)))     # faint bedding
            c = lerp(SLAB_FOOT, c, clamp01(0.25 + z / max(tall * 0.35, 0.5)))                          # damp green foot
            if n.z < -0.2:
                c = lerp(c, (0.20, 0.23, 0.32), 0.6)
            loop[p.col] = (c[0] ** 1.0, c[1] ** 1.0, c[2] ** 1.0, 1.0)
    tmp.free()
    p.export()


# --- library, part two: ships and their parts, dock pieces, outpost dressing, a pirate figure ----------------------
SAIL_LIGHT, SAIL_DARK = (0.95, 0.90, 0.76), (0.66, 0.60, 0.50)
ROPE = (0.62, 0.50, 0.30)


def spar(p, a, b, r0, r1, seed, sides=8):
    """Round timber from a to b, tapering."""
    a, b = Vector(a), Vector(b)
    axis = b - a
    tint = lerp(wood_tint(seed), WOOD_DARK, 0.25)
    rings = [(a + axis * (k / 4), r0 + (r1 - r0) * k / 4, axis) for k in range(5)]
    p.tube(rings, lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.5), lerp(tint, EDGE_LIT, 0.35), clamp01(nrm.z * 0.5 + 0.5)), sides=sides, smooth=True)


def sail_cloth(p, top_a, top_b, bot_a, bot_b, billow, stripe=None):
    """A sail between a yard (top) and a boom (bottom), bellied out along `billow`."""
    nu, nv = 8, 7
    grid = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu + 1):
            u = i / nu
            pt = (Vector(top_a).lerp(Vector(top_b), u)).lerp(Vector(bot_a).lerp(Vector(bot_b), u), v)
            row.append(pt + Vector(billow) * (math.sin(math.pi * u) * math.sin(math.pi * (0.15 + 0.8 * v))))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            base = SAIL_LIGHT if stripe is None or i % 2 == 0 else stripe
            shade = 0.25 + 0.5 * j / nv

            def paint(co, nrm, base=base, shade=shade):
                return lerp(base, lerp(base, SAIL_DARK, 0.7), shade * 0.6)

            f = p.bm.faces.new([p.bm.verts.new(v) for v in (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])])
            f.smooth = True
            p.bm.normal_update()
            p.paint([f], paint)


def mast_rig(p, x, deck, height, yard, seed, stripe=None, nest=False):
    """Mast with one square sail: yard up top, boom below, cloth bellied toward the bow (+x)."""
    spar(p, (x, 0, deck - 0.4), (x, 0, deck + height), 0.24, 0.11, seed)
    top, bot = deck + height * 0.86, deck + height * 0.26
    spar(p, (x + 0.25, -yard / 2, top), (x + 0.25, yard / 2, top), 0.10, 0.10, seed + 1, sides=6)
    spar(p, (x + 0.25, -yard * 0.46, bot), (x + 0.25, yard * 0.46, bot), 0.09, 0.09, seed + 2, sides=6)
    sail_cloth(p, (x + 0.3, -yard / 2, top), (x + 0.3, yard / 2, top), (x + 0.3, -yard * 0.46, bot), (x + 0.3, yard * 0.46, bot),
               (height * 0.14, 0, 0), stripe)
    if nest:
        rings = [(Vector((x, 0, deck + height * 0.92)), 0.55, Vector((0, 0, 1))), (Vector((x, 0, deck + height * 0.92 + 0.5)), 0.65, Vector((0, 0, 1)))]
        p.tube(rings, lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.5), sides=10, smooth=False)
    cloth(p, [Vector((x, 0, deck + height + 0.05)), Vector((x - 1.1, 0.05, deck + height - 0.15)), Vector((x, 0, deck + height - 0.45))],
          stripe or (0.75, 0.16, 0.14))


def cannon_at(p, x, y, z, yaw, seed):
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, 'Z')
    plank(p, (0, 0, 0), (0.95, 0.6, 0.3), seed, rot=m @ Matrix.Translation((0, 0, 0.3)), grey=0.15)
    for sx in (-0.3, 0.3):
        for sy in (-0.36, 0.36):
            c = m @ Vector((sx, sy, 0.17))
            ax = m.to_3x3() @ Vector((0, 1, 0))
            p.tube([(c - ax * 0.05, 0.17, ax), (c + ax * 0.05, 0.17, ax)], lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.3), sides=10, smooth=False)
    ax = m.to_3x3() @ Vector((1, 0, 0.08))
    o = m @ Vector((-0.45, 0, 0.62))
    rings = [(o, 0.20, ax), (o + ax * 0.25, 0.19, ax), (o + ax * 1.25, 0.14, ax), (o + ax * 1.32, 0.17, ax), (o + ax * 1.45, 0.16, ax)]
    p.tube(rings, lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.2 + 0.8 * nrm.z)), sides=10, smooth=True)


def wheel_at(p, x, y, z, seed):
    post(p, x, y, z, z + 0.95, 0.09, seed)
    c = Vector((x - 0.14, y, z + 1.05))
    for k in range(8):
        a = math.pi * k / 4
        d = Vector((0, math.cos(a), math.sin(a)))
        spar(p, c, c + d * 0.62, 0.035, 0.03, seed + k, sides=5)
    ax = Vector((1, 0, 0))
    p.tube([(c - ax * 0.04, 0.47, ax), (c + ax * 0.04, 0.47, ax)], lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.55), sides=16, cap=False, smooth=False)
    p.tube([(c - ax * 0.04, 0.40, ax), (c + ax * 0.04, 0.40, ax)], lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.3), sides=16, cap=False, smooth=False)


def hull(p, length, beam, draft, free, seed, trim):
    """Lofted clinker hull along x (bow at +x). Returns (deck_z(t), half_beam_at_deck(t), x(t))."""
    n, rows = 18, 7

    def x_at(t):
        return -length / 2 + length * t

    def half(t):
        return beam / 2 * min(1.0, 0.70 + 0.95 * t) * (1.0 - t ** 3.4)

    def sheer(t):
        return free + 1.05 * (2 * t - 1) ** 2 * (1.35 if t > 0.5 else 0.9)

    def keel(t):
        return -draft * (1.0 - t ** 5) * (0.8 + 0.2 * min(1.0, t * 4))

    def pt(t, s, side):
        return Vector((x_at(t), side * half(t) * s ** 0.55, keel(t) + (sheer(t) - keel(t)) * s ** 1.5))

    ts = [i / n for i in range(n + 1)]
    for k in range(rows):
        s0, s1 = k / rows, (k + 1) / rows
        tint = lerp(wood_tint(seed + k * 5), WOOD_DARK, 0.30 if k < rows - 1 else 0.0)
        if k == rows - 1:
            tint = trim
        if k == 3:
            tint = (0.90, 0.86, 0.72)                                # painted waterline strake
        for side in (-1, 1):
            a = [pt(t, s0, side) for t in ts]
            b = [pt(t, s1 * 1.0, side) + Vector((0, side * 0.035, 0)) for t in ts]     # each strake laps the one below
            strip(p, a, b, lambda co, nrm, tint=tint: lerp(lerp(tint, WOOD_DARK, 0.45), tint, clamp01(0.35 + (co.z + draft) / (free + draft))))
    ngon(p, [pt(0, k / rows, -1) for k in range(rows + 1)] + [pt(0, k / rows, 1) for k in range(rows, -1, -1)],
         lambda co, nrm: lerp(WOOD_DARK, wood_tint(seed + 60), clamp01(0.3 + co.z / free)))

    def deck_z(t):
        return sheer(t) - 0.62

    def deck_half(t):
        s = clamp01((deck_z(t) - keel(t)) / max(sheer(t) - keel(t), 0.01)) ** (1 / 1.5)
        return half(t) * s ** 0.55

    lanes = 7
    for lane in range(lanes):
        u0, u1 = -1 + 2 * lane / lanes, -1 + 2 * (lane + 1) / lanes
        tint = lerp(wood_tint(seed + 200 + lane), (0.80, 0.66, 0.44), 0.45)
        a = [Vector((x_at(t), deck_half(t) * u0, deck_z(t))) for t in ts]
        b = [Vector((x_at(t), deck_half(t) * u1, deck_z(t))) for t in ts]
        strip(p, b, a, lambda co, nrm, tint=tint: tint)
    for side in (-1, 1):                                            # gunwale rail and stanchions
        rings = [(pt(t, 1.0, side) + Vector((0, 0, 0.06)), 0.09, pt(min(t + 0.05, 1), 1.0, side) - pt(max(t - 0.05, 0), 1.0, side)) for t in ts]
        p.tube(rings, lambda co, nrm: lerp(lerp(trim, WOOD_DARK, 0.4), lerp(trim, EDGE_LIT, 0.3), clamp01(nrm.z)), sides=6, smooth=True)
    stem = [(Vector((x_at(t), 0, keel(t) - 0.12)), 0.13, Vector((1, 0, 0.2))) for t in (0.0, 0.3, 0.6, 0.85)]
    stem += [(Vector((x_at(1.0) + 0.1, 0, z)), 0.12, Vector((0.3, 0, 1))) for z in (keel(1.0) * 0.4, sheer(1.0) * 0.5, sheer(1.0) + 0.7)]
    p.tube(stem, lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, 0.3), sides=6, smooth=True)
    return deck_z, deck_half, x_at


def ship(name, length, beam, masts, guns, seed, trim, stripe=None, cabin=False):
    p = Prop(name)
    deck_z, deck_half, x_at = hull(p, length, beam, 1.7 + length * 0.02, 1.9 + length * 0.03, seed, trim)
    for i, t in enumerate(masts):
        mast_rig(p, x_at(t), deck_z(t), length * (0.78 if len(masts) == 1 else 0.62 + 0.1 * (i == 0)), beam * 1.25, seed + 300 + i * 10,
                 stripe, nest=(i == 0 and len(masts) > 1))
    spar(p, (x_at(0.93), 0, deck_z(0.93) + 0.5), (x_at(1.0) + length * 0.16, 0, deck_z(1.0) + 1.9), 0.13, 0.06, seed + 400)     # bowsprit
    for i in range(guns):
        t = 0.34 + 0.34 * (i // 2) / max(1, guns // 2 - 1) if guns > 2 else 0.5
        side = -1 if i % 2 == 0 else 1
        cannon_at(p, x_at(t), side * (deck_half(t) - 0.75), deck_z(t), side * math.pi / 2, seed + 500 + i)
    wheel_at(p, x_at(0.12), 0, deck_z(0.12) + (1.3 if cabin else 0.0), seed + 600)
    if cabin:                                                       # raised quarterdeck with a lit stern cabin
        t0, t1 = 0.02, 0.22
        z0 = deck_z(0.1)
        for k in range(6):
            t = t0 + (t1 - t0) * (k + 0.5) / 6
            plank(p, (x_at(t), 0, z0 + 1.3), ((t1 - t0) * length / 6 * 0.95, deck_half(t) * 1.9, 0.08), seed + 700 + k, grey=0.3)
        for k in range(int(deck_half(t1) * 2 / 0.32)):
            y = -deck_half(t1) + 0.16 + k * 0.32
            if abs(y) > 0.5:
                plank(p, (x_at(t1), y, z0 + 0.65), (0.06, 0.29, 1.3), seed + 720 + k, grey=0.3)
        for y in (-0.9, 0.0, 0.9):
            p.box((x_at(0.0) - 0.04, y, deck_z(0.0) - 0.2), (0.05, 0.5, 0.55), lambda co, nrm: (1.0, 0.78, 0.30), bevel=0.02)
        for k in range(5):
            plank(p, (x_at(t1) + 0.2 + 0.26 * k, deck_half(t1) - 0.9, z0 + 1.3 - 0.24 * (k + 0.5)), (0.25, 0.9, 0.06), seed + 760 + k, grey=0.4)
    lantern(p, (x_at(0.01), 0, deck_z(0.0) + (2.6 if cabin else 1.5)))
    post(p, x_at(0.01), 0, deck_z(0.0), deck_z(0.0) + (2.5 if cabin else 1.4), 0.05, seed + 800)
    for k in range(3):
        cx = x_at(0.55 + 0.05 * k)
        p.blob((cx, (-1) ** k * 0.9, deck_z(0.6) + 0.3), (0.34, 0.34, 0.36), lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, clamp01(nrm.z * 0.5 + 0.4)), k, 0.05, 2)
    p.export()


def ship_part(name, kind):
    p = Prop(name)
    if kind == "mast":
        mast_rig(p, 0, 0.4, 11.0, 6.0, 5)
    elif kind == "sail":
        sail_cloth(p, (0, -3, 7), (0, 3, 7), (0, -2.8, 0.6), (0, 2.8, 0.6), (1.4, 0, 0), (0.16, 0.50, 0.50))
    elif kind == "wheel":
        wheel_at(p, 0, 0, 0, 3)
    elif kind == "cannon":
        cannon_at(p, 0, 0, 0, 0, 3)
    elif kind == "capstan":
        rings = [(Vector((0, 0, z)), r, Vector((0, 0, 1))) for z, r in ((0, 0.42), (0.12, 0.42), (0.2, 0.30), (0.75, 0.24), (0.85, 0.36), (1.0, 0.36))]
        p.tube(rings, lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, clamp01(0.3 + 0.4 * nrm.z + co.z * 0.3)), sides=10, smooth=False)
        for k in range(6):
            a = math.pi * k / 3
            spar(p, (0, 0, 0.92), (math.cos(a) * 1.15, math.sin(a) * 1.15, 0.92), 0.05, 0.04, k, sides=5)
    p.export()


def rowboat(name):
    p = Prop(name)
    deck_z, deck_half, x_at = hull(p, 4.6, 1.7, 0.35, 0.45, 12, (0.16, 0.45, 0.48))
    for t in (0.3, 0.6):
        plank(p, (x_at(t), 0, deck_z(t) + 0.28), (0.3, deck_half(t) * 2.0, 0.05), 40 + int(t * 10), grey=0.3)
    for side in (-1, 1):
        spar(p, (x_at(0.45), side * 0.6, deck_z(0.45) + 0.5), (x_at(0.45) - 0.5, side * 2.3, 0.05), 0.035, 0.03, 50 + side, sides=5)
    for v in p.bm.verts:
        v.co.z += 0.36
    p.export()


def dressing(name, kind):
    p = Prop(name)
    if kind == "lantern_post":
        post(p, 0, 0, -0.4, 3.1, 0.09, 3, lean=(0.015, 0.0))
        plank(p, (0.45, 0, 2.95), (1.0, 0.08, 0.09), 4, grey=0.2, bevel=0.0)
        p.box((0.85, 0, 2.72), (0.02, 0.02, 0.4), lambda co, nrm: IRON_DARK)
        lantern(p, (0.85, 0, 2.4))
    elif kind == "banner_pole":
        post(p, 0, 0, -0.5, 6.0, 0.11, 5, lean=(0.01, 0.0))
        plank(p, (0.9, 0, 5.6), (2.2, 0.1, 0.12), 6, grey=0.2, bevel=0.0)
        teal = (0.10, 0.42, 0.44)
        cloth(p, [Vector((0.15, -0.02, 5.52)), Vector((1.85, -0.02, 5.52)), Vector((1.85, -0.02, 3.6)), Vector((1.0, -0.02, 3.1)), Vector((0.15, -0.02, 3.6))], teal, (0.03, 0.14, 0.16))
        p.box((1.0, -0.05, 4.6), (0.9, 0.03, 0.12), lambda co, nrm: (0.95, 0.82, 0.50))
        p.box((1.0, -0.05, 4.3), (0.5, 0.03, 0.12), lambda co, nrm: (0.95, 0.82, 0.50))
    elif kind == "bench":
        plank(p, (0, 0, 0.46), (1.8, 0.42, 0.07), 7, grey=0.3)
        plank(p, (0, 0.2, 0.8), (1.8, 0.06, 0.3), 8, grey=0.3)
        for sx in (-0.75, 0.75):
            plank(p, (sx, 0, 0.23), (0.09, 0.38, 0.46), 9, grey=0.3, bevel=0.0)
            plank(p, (sx, 0.2, 0.62), (0.07, 0.06, 0.4), 10, grey=0.3, bevel=0.0)
    elif kind == "net_rack":
        for sx in (-1.4, 1.4):
            post(p, sx, 0, -0.3, 2.2, 0.07, 11, lean=(0.0, 0.03))
        plank(p, (0, 0.07, 2.1), (3.1, 0.07, 0.08), 12, grey=0.2, bevel=0.0)
        for i in range(9):                                          # net: a lattice of thin cords
            x = -1.3 + 2.6 * i / 8
            p.box((x, 0.06, 1.2), (0.02, 0.02, 1.75), lambda co, nrm: ROPE)
        for j in range(6):
            p.box((0, 0.06, 0.45 + j * 0.3), (2.6, 0.02, 0.02), lambda co, nrm: ROPE)
        for k in range(4):
            p.blob((-1.0 + k * 0.7, 0.08, 0.38), (0.11, 0.11, 0.11), lambda co, nrm: lerp((0.45, 0.20, 0.10), (0.90, 0.55, 0.25), clamp01(nrm.z + 0.5)), k, 0.03, 1, smooth=True)
    elif kind == "anchor":
        iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
        m = Matrix.Rotation(1.15, 4, 'Y')
        p.box((0, 0, 0), (0.14, 0.14, 2.2), iron, bevel=0.03, xform=Matrix.Translation((0, 0, 0.55)) @ m)
        p.box((0, 0, 0), (0.12, 1.2, 0.12), iron, bevel=0.03, xform=Matrix.Translation((0, 0, 0.55)) @ m @ Matrix.Translation((0, 0, 0.9)))
        for s in (-1, 1):
            p.box((0, 0, 0), (0.14, 0.9, 0.16), iron, bevel=0.03,
                  xform=Matrix.Translation((0, 0, 0.55)) @ m @ Matrix.Translation((0, s * 0.38, -1.0)) @ Matrix.Rotation(s * 0.7, 4, 'X'))
    elif kind == "mooring_post":
        post(p, 0, 0, -3.0, 1.3, 0.2, 13)
        p.tube([(Vector((0, 0, 0.95)), 0.24, Vector((0, 0, 1))), (Vector((0, 0, 1.12)), 0.24, Vector((0, 0, 1)))], lambda co, nrm: ROPE, sides=10, cap=False)
    elif kind == "ladder":
        for sx in (-0.3, 0.3):
            plank(p, (sx, 0, 1.6), (0.07, 0.07, 3.2), 14, grey=0.3, bevel=0.0)
        for k in range(9):
            plank(p, (0, 0, 0.3 + k * 0.34), (0.62, 0.06, 0.05), 15 + k, grey=0.3, bevel=0.0)
    elif kind in ("dock_end", "dock_corner"):
        rnd = random.Random(17)
        size = 5.0
        for k in range(int(size / 0.42)):
            plank(p, (size * (k + 0.5) / int(size / 0.42), 0, 1.25), (0.37, size, 0.07), 300 + k, grey=rnd.uniform(0.35, 0.65))
        for sx in (0.2, size - 0.2):
            for sy in (-size / 2 + 0.1, size / 2 - 0.1):
                post(p, sx, sy, -5.5, 1.25 + rnd.uniform(0.5, 1.4), 0.17, 320 + int(sx + sy))
        for sy in (-size / 2 + 0.3, size / 2 - 0.3):
            plank(p, (size / 2, sy, 1.1), (size, 0.16, 0.2), 340, grey=0.25)
        if kind == "dock_end":
            for k, (x, y) in enumerate(((3.9, 1.5), (3.3, -1.6), (4.2, -0.4))):
                plank(p, (x, y, 1.55 + (0.5 if k == 2 else 0)), (0.6, 0.6, 0.55), 360 + k, grey=0.2)
    p.export()


def pirate(name, coat):
    """A chunky stand-in pirate: big hands and boots, small hat, coat in the crew colour."""
    p = Prop(name)
    skin, boot, trouser = (0.86, 0.62, 0.46), (0.20, 0.12, 0.08), (0.30, 0.26, 0.22)
    soft = lambda base: (lambda co, nrm: lerp(tuple(c * 0.55 for c in base), base, clamp01(nrm.z * 0.5 + 0.6)))
    up = Vector((0, 0, 1))
    for sx in (-1, 1):
        p.tube([(Vector((sx * 0.17, 0, 0.42)), 0.13, up), (Vector((sx * 0.16, 0, 0.95)), 0.15, up)], soft(trouser), sides=8)
        p.tube([(Vector((sx * 0.18, 0.02, 0.0)), 0.16, up), (Vector((sx * 0.18, 0, 0.30)), 0.15, up), (Vector((sx * 0.17, 0, 0.46)), 0.18, up)], soft(boot), sides=8)
        p.blob((sx * 0.18, -0.12, 0.08), (0.13, 0.2, 0.09), soft(boot), 1, 0.02, 1, smooth=True)
        a, b = Vector((sx * 0.36, 0, 1.46)), Vector((sx * 0.52, -0.04, 0.98))
        p.tube([(a, 0.12, b - a), (a.lerp(b, 0.55), 0.11, b - a), (b, 0.10, b - a)], soft(coat), sides=8)
        p.blob((b.x + sx * 0.02, b.y, b.z - 0.1), (0.10, 0.10, 0.12), soft(skin), 2, 0.02, 1, smooth=True)
    p.tube([(Vector((0, 0, 0.82)), 0.34, up), (Vector((0, 0, 1.05)), 0.30, up), (Vector((0, 0, 1.38)), 0.34, up), (Vector((0, 0, 1.56)), 0.26, up)], soft(coat), sides=10)
    p.tube([(Vector((0, 0, 0.98)), 0.325, up), (Vector((0, 0, 1.08)), 0.315, up)], soft((0.22, 0.13, 0.08)), sides=10, cap=False)
    p.box((0, -0.32, 1.03), (0.12, 0.04, 0.12), lambda co, nrm: (0.92, 0.74, 0.30), bevel=0.02)
    p.blob((0, 0, 1.78), (0.20, 0.21, 0.23), soft(skin), 3, 0.03, 2, smooth=True)
    p.blob((0, -0.19, 1.74), (0.05, 0.06, 0.05), soft((0.80, 0.52, 0.40)), 4, 0.0, 1, smooth=True)
    p.blob((0, 0.02, 1.96), (0.30, 0.30, 0.09), soft((0.12, 0.10, 0.10)), 5, 0.02, 2, smooth=True)
    p.blob((0, 0.02, 2.04), (0.17, 0.17, 0.12), soft((0.12, 0.10, 0.10)), 6, 0.02, 2, smooth=True)
    p.export()




def _bw_finish(self):
    """Replace or create the kit object for this prop, keep its place on the shelf, show its paint."""
    coll = bpy.data.collections.get("Brinewake Kit")
    if coll is None:
        coll = bpy.data.collections.new("Brinewake Kit")
        bpy.context.scene.collection.children.link(coll)
    mesh = bpy.data.meshes.new(self.name)
    bmesh.ops.triangulate(self.bm, faces=self.bm.faces[:])
    self.bm.to_mesh(mesh)
    self.bm.free()
    mat = bpy.data.materials.get("BW_Painted")
    if mat is not None:
        mesh.materials.append(mat)
    col = mesh.color_attributes.get("Col")
    if col is not None:
        mesh.color_attributes.active_color = col
        mesh.color_attributes.render_color_index = list(mesh.color_attributes).index(col)
    obj = bpy.data.objects.get(self.name)
    if obj is None:
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        n = len(coll.objects) - 1
        obj.location = ((n % 10) * 26.0, -(n // 10) * 30.0, 0.0)
    else:
        old = obj.data
        obj.data = mesh
        if old.users == 0:
            bpy.data.meshes.remove(old)
    for key in ("bw_ao", "bw_sculpted"):
        if key in obj:
            del obj[key]
    obj["bw_srgb"] = True
    _bw_occlude(obj)
    BW_BUILT.append((self.name, len(mesh.polygons)))


def _bw_occlude(obj, rays=14):
    """Ambient occlusion by ray casting against the asset itself, multiplied into the paint (cavities darker and cooler)."""
    from mathutils.bvhtree import BVHTree
    mesh = obj.data
    col = mesh.color_attributes.get("Col")
    if col is None or len(mesh.polygons) == 0:
        return
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [tuple(q.vertices) for q in mesh.polygons])
    reach = max(0.5, min(2.0, max(obj.dimensions) * 0.12))
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
            loc, _, _, dist = tree.ray_cast(origin, d if d.dot(n) > 0 else -d, reach)
            if loc is not None:
                hit += 1.0 - dist / reach
        ao.append(1.0 - hit / rays)
    n = len(col.data)
    buf = [0.0] * (n * 4)
    col.data.foreach_get("color", buf)
    for loop in mesh.loops:
        a = ao[loop.vertex_index]
        k = 0.30 + 0.70 * a ** 1.2
        i = loop.index * 4
        buf[i] *= k * (1.0 - 0.10 * (1.0 - a))
        buf[i + 1] *= k * (1.0 - 0.04 * (1.0 - a))
        buf[i + 2] *= k * (1.0 + 0.08 * (1.0 - a))
    col.data.foreach_set("color", buf)
    mesh.update()
    obj["bw_ao"] = True


BW_BUILT = []
Prop.export = _bw_finish

# Shared modelling helpers for the Brinewake asset scripts. Prepend to an asset script and run through bl_run.py:
#   cat a_lib.py a_props.py > _combo.py && python bl_run.py _combo.py
# Everything is painted per vertex (palette colour stored as is). Metres, z up, pivot on the ground at the origin.
from mathutils import Quaternion

GOLD_LO, GOLD_HI, OCHRE = (0.55, 0.36, 0.10), (1.0, 0.82, 0.36), (0.90, 0.64, 0.20)
BONE_HI, BONE_LO = (0.92, 0.87, 0.70), (0.50, 0.42, 0.29)
LEATHER, LEATHER_D = (0.42, 0.25, 0.13), (0.22, 0.13, 0.08)
ROPE_C, ROPE_D = (0.74, 0.60, 0.38), (0.40, 0.30, 0.18)
CANVAS, CANVAS_D = (0.90, 0.84, 0.68), (0.56, 0.50, 0.40)
RED, NAVY, TEAL = (0.62, 0.12, 0.10), (0.11, 0.18, 0.36), (0.13, 0.42, 0.46)
UP = Vector((0, 0, 1))
SUN_DIR = Vector((0.30, -0.42, 0.86)).normalized()


def lin(c):
    return (clamp01(c[0]), clamp01(c[1]), clamp01(c[2]), 1.0)


def col_of(colour, co, nrm):
    return lin(colour(co, nrm) if callable(colour) else colour)


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def fquad(p, pts, colour, smooth=False):
    """One face on fresh vertices, painted at once."""
    f = p.bm.faces.new([p.bm.verts.new(Vector(v)) for v in pts])
    f.smooth = smooth
    f.normal_update()
    for loop in f.loops:
        loop[p.col] = col_of(colour, loop.vert.co, f.normal)
    return f


def skin(p, loops, colour, smooth=True, cap=True, closed=True, inside=False):
    """Faces between successive rings of points (equal length). Closed rings are turned to face outward."""
    n = len(loops[0])
    vl = [[p.bm.verts.new(v) for v in loop] for loop in loops]
    faces = []
    for A, B in zip(vl, vl[1:]):
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            faces.append(p.bm.faces.new((A[k], A[k2], B[k2], B[k])))
    if cap and closed:
        faces.append(p.bm.faces.new(vl[-1]))
        faces.append(p.bm.faces.new(vl[0][::-1]))
    for f in faces:
        f.normal_update()
    if closed and len(loops) > 1:                                   # signed volume says which way the skin faces
        mid = sum((v for loop in loops for v in loop), Vector()) / (n * len(loops))
        if (sum(f.normal.dot(f.calc_center_median() - mid) * f.calc_area() for f in faces) < 0.0) != inside:
            bmesh.ops.reverse_faces(p.bm, faces=faces)
            for f in faces:
                f.normal_update()
    for f in faces:
        f.smooth = smooth
        for loop in f.loops:
            loop[p.col] = col_of(colour, loop.vert.co, f.normal)
    return faces


def pipe(p, pts, radii, colour, sides=6, up=UP, closed=False, smooth=True, cap=True):
    """Round section swept along a path. `up` keeps the section from twisting (for a loop: the normal of its plane)."""
    pts = [Vector(v) for v in pts]
    n = len(pts)
    loops = []
    for i in range(n):
        a = (pts[(i + 1) % n] - pts[(i - 1) % n]) if closed else (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        a.normalize()
        s = a.cross(up)
        if s.length < 1e-4:
            s = a.cross(Vector((1, 0, 0)))
        if s.length < 1e-4:
            s = a.cross(Vector((0, 1, 0)))
        s.normalize()
        u = s.cross(a)
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        loops.append([pts[i] + (s * math.cos(q) + u * math.sin(q)) * max(r, 0.002) for q in (2 * math.pi * k / sides for k in range(sides))])
    if closed:
        loops.append(loops[0])
    return skin(p, loops, colour, smooth=smooth, cap=cap and not closed)


def lathe(p, prof, colour, at=(0, 0, 0), sides=12, smooth=True, m=None, cap=True, turn=0.0, inside=False):
    """prof: (radius, height) pairs from the bottom up, spun round z at `at`. m moves the result afterwards."""
    at = Vector(at)
    loops = []
    for r, z in prof:
        ring = [at + Vector((math.cos(q) * max(r, 0.002), math.sin(q) * max(r, 0.002), z)) for q in (turn + 2 * math.pi * k / sides for k in range(sides))]
        loops.append([m @ v for v in ring] if m is not None else ring)
    return skin(p, loops, colour, smooth=smooth, cap=cap, inside=inside)


def sheet(p, grid, colour, smooth=True, flip=False):
    """Quads through a grid of points grid[j][i]."""
    vs = [[p.bm.verts.new(Vector(v)) for v in row] for row in grid]
    faces = []
    for j in range(len(vs) - 1):
        for i in range(len(vs[0]) - 1):
            q = (vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i])
            faces.append(p.bm.faces.new(q[::-1] if flip else q))
    for f in faces:
        f.smooth = smooth
        f.normal_update()
        for loop in f.loops:
            loop[p.col] = col_of(colour, loop.vert.co, f.normal)
    return faces


def fan(p, ring, centre, out, colour):
    """Triangles from a ring to a centre point, facing `out`."""
    n = len(ring)
    for k in range(n):
        a, b = ring[k], ring[(k + 1) % n]
        tri = [a, b, centre]
        if (b - a).cross(centre - b).dot(out) < 0.0:
            tri = [b, a, centre]
        fquad(p, tri, colour)


def disc(p, at, r, colour, sides=12, m=None, down=False):
    """A flat round face at `at`, facing up (or down) in the space of m."""
    at = Vector(at)
    ring = [at + Vector((math.cos(q) * r, math.sin(q) * r, 0)) for q in (2 * math.pi * k / sides for k in range(sides))]
    out = UP
    if m is not None:
        ring, at, out = [m @ v for v in ring], m @ at, (m.to_3x3() @ UP).normalized()
    fan(p, ring, at, -out if down else out, colour)


def const(c):
    return lambda co, nrm: c


def ibox(p, m, size, colour, bevel=0.0):
    """A box of the given full size centred on the origin of m."""
    return p.box((0, 0, 0), size, colour if callable(colour) else const(colour), bevel=bevel, xform=m)


def zto(c, axis):
    """Matrix that puts the origin at c and turns z onto the axis."""
    return Matrix.Translation(Vector(c)) @ UP.rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()


def xf_all(p, m):
    for v in p.bm.verts:
        v.co = m @ v.co


def shade(base, lo=0.55):
    """Lit from above, darker and cooler underneath."""
    dark = (base[0] * lo, base[1] * lo, base[2] * (lo + 0.04))
    return lambda co, nrm: lerp(dark, base, clamp01(nrm.z * 0.5 + 0.62))


def metal(light=IRON_LIGHT, dark=IRON_DARK, rust=0.35):
    def paint(co, nrm):
        c = lerp(dark, light, clamp01(0.22 + 0.78 * nrm.z))
        return lerp(c, RUST, rust * clamp01(noise.noise(co * 9.0) * 1.4 + 0.15))
    return paint


def gilt(co, nrm):
    return lerp(GOLD_LO, GOLD_HI, clamp01(nrm.z * 0.5 + 0.55 + 0.25 * noise.noise(co * 14.0)))


def aim(a, b, roll=0.0):
    """Matrix whose x axis runs from a to b, with its origin half way between them."""
    a, b = Vector(a), Vector(b)
    x = (b - a).normalized()
    ref = UP if abs(x.z) < 0.95 else Vector((0, 1, 0))
    y = ref.cross(x).normalized()
    z = x.cross(y)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (a + b) / 2
    return m @ Matrix.Rotation(roll, 4, 'X')


def at_m(x, y, z, yaw=0.0, pitch=0.0, roll=0.0, s=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'Y') @ Matrix.Rotation(roll, 4, 'X') @ Matrix.Scale(s, 4)


def beam(p, a, b, w, h, seed, grey=0.4, bevel=0.02, roll=0.0, over=0.0):
    """A sawn timber from a to b, w wide and h deep."""
    a, b = Vector(a), Vector(b)
    return plank(p, (0, 0, 0), ((b - a).length + over, w, h), seed, rot=aim(a, b, roll), grey=grey, bevel=bevel)


def board(p, m, size, seed, grey=0.4, bevel=0.012):
    return plank(p, (0, 0, 0), size, seed, rot=m, grey=grey, bevel=bevel)


def log(p, a, b, r0, r1, seed, sides=9, grey=0.35, segs=4, wob=0.25, foot=0.0, point=0.0):
    """A hewn round timber from a to b: flat axe facets, each its own tone, streaks of grain, pale end grain.
    foot = height of the damp dark band at the lower end, point = length of a sharpened tip at b."""
    a, b = Vector(a), Vector(b)
    ax = b - a
    L = ax.length
    ax = ax / L
    s = ax.cross(Vector((0, 1, 0)))
    if s.length < 1e-3:
        s = ax.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(ax)
    rnd = random.Random(seed)
    tint = lerp(wood_tint(seed), WEATHER, grey)
    ph = rnd.uniform(0, 6.28)
    jit = [rnd.uniform(0.90, 1.08) for _ in range(sides)]
    tone = [rnd.uniform(0.0, 1.0) for _ in range(sides)]
    loops = []
    for i in range(segs + 1):
        t = i / segs
        r = r0 + (r1 - r0) * t
        c = a + ax * (L * t) + (s * math.sin(ph + t * 3.1) + u * math.cos(ph * 1.7 + t * 2.3)) * (wob * r * math.sin(math.pi * t))
        loops.append([c + (s * math.cos(q) + u * math.sin(q)) * (r * jit[k]) for k, q in enumerate(2 * math.pi * k / sides for k in range(sides))])
    zlow = min(a.z, b.z)

    def paint(co, nrm):
        t = clamp01((co - a).dot(ax) / L)
        ang = math.atan2(nrm.dot(u), nrm.dot(s))
        c = lerp(lerp(tint, WOOD_DARK, 0.5), tint, 0.30 + 0.70 * tone[int((ang / (2 * math.pi) + 1.0) * sides) % sides])
        g = noise.noise(Vector((ang * 2.0 + seed, t * L * 0.45, seed * 0.37)))
        c = lerp(c, lerp(tint, WOOD_DARK, 0.8), clamp01(g * 1.7 - 0.25) * 0.6)
        c = lerp(c, lerp(c, EDGE_LIT, 0.5), clamp01(nrm.z) * 0.7)
        if foot > 0.0:
            c = lerp((0.12, 0.15, 0.11), c, clamp01((co.z - zlow) / foot) ** 0.7)
        return c

    skin(p, loops, paint, smooth=False, cap=False)
    grain_lo, grain_hi = lerp(tint, WOOD_DARK, 0.25), lerp(tint, EDGE_LIT, 0.6)
    for end, ring, sgn in ((b, loops[-1], 1.0), (a, loops[0], -1.0)):
        mid = sum(ring, Vector()) / sides
        if sgn > 0 and point > 0.0:
            fan(p, ring, mid + ax * point, ax, lambda co, nrm, mid=mid: lerp(grain_lo, grain_hi, clamp01((co - mid).dot(ax) / point)))
            continue
        inner = [mid + (v - mid) * 0.55 for v in ring]
        for k in range(sides):
            q = [ring[k], ring[(k + 1) % sides], inner[(k + 1) % sides], inner[k]]
            if (q[1] - q[0]).cross(q[2] - q[1]).dot(ax * sgn) < 0.0:
                q.reverse()
            fquad(p, q, lerp(grain_lo, grain_hi, 0.35 + 0.3 * tone[k]))
        fan(p, inner, mid, ax * sgn, lambda co, nrm, mid=mid: lerp(grain_hi, grain_lo, clamp01(1.0 - (co - mid).length / max(r0, r1))))


def rope_paint(tint=ROPE_C):
    return lambda co, nrm: lerp(lerp(tint, ROPE_D, 0.75), tint, clamp01(nrm.z * 0.5 + 0.6 + 0.3 * math.sin((co.x + co.y + co.z) * 90.0)))


def rope(p, a, b, r=0.022, sag=0.0, tint=ROPE_C, n=8):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, k / n) + Vector((0, 0, -sag * math.sin(math.pi * k / n))) for k in range(n + 1)] if sag else [a, b]
    pipe(p, pts, r, rope_paint(tint), sides=5, up=Vector((0.31, 0.95, 0.05)))


def lash(p, c, r, turns=4, rr=0.022, axis=UP, tint=ROPE_C):
    """Rope lashing wound round a post of radius r, starting at c and climbing along the axis."""
    c, axis = Vector(c), Vector(axis).normalized()
    s = axis.cross(Vector((0, 1, 0)))
    if s.length < 1e-3:
        s = axis.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(axis)
    for k in range(turns):
        cc = c + axis * (k * rr * 1.75)
        pipe(p, [cc + (s * math.cos(q) + u * math.sin(q)) * (r + rr * 0.55) for q in (2 * math.pi * j / 10 + k for j in range(10))], rr,
             rope_paint(lerp(tint, ROPE_D, 0.25 * (k % 2))), sides=5, up=axis, closed=True)


def coil(p, at, r=0.30, layers=3, rr=0.035, tint=ROPE_C):
    x, y, z = at
    for layer in range(layers):
        rad = r - rr * 0.9 * layer
        pipe(p, [Vector((x + math.cos(a) * rad, y + math.sin(a) * rad, z + rr + rr * 1.8 * layer)) for a in (2 * math.pi * k / 14 for k in range(14))],
             rr, rope_paint(tint), sides=5, closed=True)
    pipe(p, [Vector((x + r * 0.9, y - 0.02, z + rr)), Vector((x + r * 1.3, y + 0.10, z + rr)), Vector((x + r * 1.75, y + 0.02, z + rr * 0.9))], rr, rope_paint(tint), sides=5)


def chain(p, a, b, link=0.085, r=0.014):
    a, b = Vector(a), Vector(b)
    d = b - a
    n = max(2, int(d.length / (link * 1.25)))
    ax = d.normalized()
    s = ax.cross(Vector((0, 1, 0)))
    if s.length < 1e-3:
        s = ax.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(ax)
    for k in range(n):
        c = a + d * ((k + 0.5) / n)
        w, nrm = (s, u) if k % 2 else (u, s)
        pipe(p, [c + ax * (math.cos(q) * link * 0.78) + w * (math.sin(q) * link * 0.42) for q in (2 * math.pi * j / 8 for j in range(8))], r, metal(rust=0.5),
             sides=4, up=nrm, closed=True)


def glow(z0, z1):
    zm, zh = (z0 + z1) / 2, max((z1 - z0) / 2, 1e-3)
    return lambda co, nrm: lerp((1.0, 0.46, 0.08), (1.0, 0.93, 0.56), clamp01(1.0 - abs(co.z - zm) / zh) ** 1.3)


def lamp(p, at, s=1.0, hang=True):
    """A six-sided ship's lantern: iron foot, cage bars, glowing glass, pitched cap and carrying ring.
    `at` is the hook point when it hangs, otherwise the middle of its foot."""
    x, y, z = at
    h, w = 0.36 * s, 0.115 * s
    zb = z - 0.13 * s - 0.24 * s - h if hang else z + 0.05 * s
    zt = zb + h
    iron = metal(rust=0.25)
    lathe(p, [(w * 1.05, zb - 0.05 * s), (w * 1.28, zb - 0.035 * s), (w * 1.28, zb - 0.01 * s), (w * 1.08, zb)], iron, at=(x, y, 0), sides=6, smooth=False)
    lathe(p, [(w, zb), (w * 1.16, zb + h * 0.55), (w * 1.08, zt)], glow(zb, zt), at=(x, y, 0), sides=6, smooth=False, cap=False)
    for k in range(6):
        q = 2 * math.pi * k / 6
        pipe(p, [Vector((x + math.cos(q) * w * f, y + math.sin(q) * w * f, zz)) for f, zz in ((1.04, zb), (1.20, zb + h * 0.55), (1.12, zt))], 0.013 * s, iron, sides=4)
    lathe(p, [(w * 1.21, zb + h * 0.53), (w * 1.24, zb + h * 0.55), (w * 1.21, zb + h * 0.58)], iron, at=(x, y, 0), sides=6, smooth=False, cap=False)
    lathe(p, [(w * 1.12, zt - 0.01 * s), (w * 1.42, zt), (w * 1.46, zt + 0.02 * s), (w * 0.80, zt + 0.12 * s), (w * 0.34, zt + 0.17 * s), (w * 0.34, zt + 0.21 * s),
              (w * 0.14, zt + 0.235 * s)], iron, at=(x, y, 0), sides=6, smooth=False)
    c = Vector((x, y, zt + 0.235 * s + 0.055 * s))
    pipe(p, [c + Vector((math.cos(q) * 0.055 * s, 0, math.sin(q) * 0.055 * s)) for q in (2 * math.pi * k / 10 for k in range(10))], 0.011 * s, iron, sides=4,
         up=Vector((0, 1, 0)), closed=True)
    return zt + 0.235 * s + 0.11 * s


def flame(p, at, s=1.0, seed=0, tongues=5):
    """Stylised fire: leaning teardrop tongues, yellow core to red tip."""
    rnd = random.Random(seed)
    at = Vector(at)
    for k in range(tongues):
        a = 2 * math.pi * k / max(tongues - 1, 1) + rnd.uniform(-0.3, 0.3)
        off = Vector((math.cos(a), math.sin(a), 0)) * (0.16 * s if k else 0.0)
        hgt = s * (1.0 if k == 0 else rnd.uniform(0.5, 0.78))
        lean = Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0)) * hgt
        prof = [(0.05, 0.0), (0.20, 0.10), (0.25, 0.26), (0.20, 0.46), (0.12, 0.66), (0.05, 0.86), (0.004, 1.0)]
        base = at + off
        loops = []
        for r, t in prof:
            c = base + Vector((0, 0, hgt * t)) + lean * t * t + Vector((math.sin(t * 5.0 + k), math.cos(t * 4.0 + k * 2), 0)) * 0.03 * s
            loops.append([c + Vector((math.cos(q) * r * hgt * 0.62, math.sin(q) * r * hgt * 0.62, 0)) for q in (2 * math.pi * j / 7 for j in range(7))])
        z0 = base.z

        def paint(co, nrm, z0=z0, hgt=hgt):
            t = clamp01((co.z - z0) / hgt)
            return lerp((1.0, 0.93, 0.50), (1.0, 0.52, 0.08), clamp01(t * 2.0)) if t < 0.5 else lerp((1.0, 0.52, 0.08), (0.86, 0.17, 0.04), clamp01((t - 0.5) * 2.0))
        skin(p, loops, paint, smooth=True, cap=True)


# --- rock: angular chunks (a convex hull of a few points, worn edges), stacked and clustered ----------------------
ROCK_PAL = {
    'shore': dict(top=(0.82, 0.73, 0.57), mid=(0.52, 0.44, 0.40), low=(0.25, 0.21, 0.27), band=(0.64, 0.46, 0.35), moss=(0.36, 0.48, 0.16)),
    'grey': dict(top=(0.76, 0.77, 0.74), mid=(0.47, 0.48, 0.53), low=(0.22, 0.22, 0.29), band=(0.56, 0.52, 0.50), moss=(0.30, 0.44, 0.18)),
    'verdant': dict(top=(0.62, 0.64, 0.48), mid=(0.38, 0.42, 0.37), low=(0.15, 0.20, 0.21), band=(0.47, 0.44, 0.34), moss=(0.21, 0.47, 0.11)),
    'ash': dict(top=(0.90, 0.88, 0.83), mid=(0.63, 0.61, 0.62), low=(0.35, 0.33, 0.38), band=(0.74, 0.69, 0.64), moss=(0.52, 0.54, 0.40)),
    'ember': dict(top=(0.34, 0.29, 0.29), mid=(0.19, 0.15, 0.16), low=(0.08, 0.06, 0.07), band=(0.27, 0.17, 0.13), moss=(0.25, 0.20, 0.14), glow=(1.0, 0.44, 0.07)),
    'ruin': dict(top=(0.80, 0.78, 0.68), mid=(0.56, 0.55, 0.50), low=(0.28, 0.29, 0.30), band=(0.62, 0.60, 0.52), moss=(0.30, 0.46, 0.16)),
}


def rock_paint(pal, seed, zbase, ztop, moss=0.0, bed=0.9):
    P = ROCK_PAL[pal] if isinstance(pal, str) else pal
    off = Vector((seed * 3.7, seed * 1.3, seed * 2.9))
    span = max(ztop - zbase, 0.2)

    def paint(co, n):
        t = clamp01((co.z - zbase) / span)
        up = clamp01(n.z)
        c = lerp(P['low'], P['mid'], clamp01(t * 1.5 + 0.12))
        band = 0.5 + 0.5 * math.sin(co.z * 6.283 / bed + noise.noise(Vector((co.x * 0.22, co.y * 0.22, seed))) * 2.6)
        c = lerp(c, P['band'], 0.50 * band * (1.0 - up) * (0.4 + 0.6 * t))
        c = lerp(c, P['top'], up ** 1.2 * (0.50 + 0.50 * t))
        k = 0.84 + 0.26 * clamp01(n.dot(SUN_DIR)) + 0.09 * noise.noise(co * 0.8 + off)
        c = mul(c, k)
        crack = abs(noise.noise(co * 1.25 + off * 2.0))
        if crack < 0.055:
            c = lerp(c, P.get('glow', P['low']), (0.85 if 'glow' in P else 0.55) * (1.0 - crack / 0.055))
        if moss > 0.0:
            m = clamp01((n.z - 0.35) * 2.2) * clamp01(noise.noise(co * 0.55 + off * 0.5) * 1.6 + moss)
            c = lerp(c, lerp(P['moss'], mul(P['moss'], 1.45), clamp01(noise.noise(co * 2.0) + 0.4)), clamp01(m * 1.15))
        return lerp(lerp(P['low'], (0.17, 0.22, 0.17), 0.35), c, clamp01(0.30 + (co.z - zbase) / 0.55))
    return paint


def chunk(p, centre, size, seed, pal='shore', pts=16, bevel=0.14, boxy=0.55, moss=0.0, sub=2, turn=0.0, flat=0.0, lump=0.05, taper=1.0, zrange=None,
          tilt=(0.0, 0.0)):
    """One angular stone: hull of random points pushed toward a box, bevelled edges, soft lumps. size = half extents.
    flat cuts the top level (0.3 = top 30 % sliced off); zrange = (ground, top) for the paint gradient of a whole pile."""
    rnd = random.Random(seed)
    tmp = bmesh.new()
    for i in range(pts):
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if v.length < 0.2:
            v = Vector((1, 0.3, 0.2))
        m = max(abs(v.x), abs(v.y), abs(v.z))
        v = v.normalized().lerp(v / m, boxy) * rnd.uniform(0.84, 1.0)
        if flat and v.z > 1.0 - 2.0 * flat:
            v.z = 1.0 - 2.0 * flat
        if v.z > 0:
            v.x *= taper
            v.y *= taper
        tmp.verts.new(v)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = list({g for key in ('geom_interior', 'geom_unused') for g in res.get(key, []) if isinstance(g, bmesh.types.BMVert) and g.is_valid})
    if junk:
        bmesh.ops.delete(tmp, geom=junk, context='VERTS')
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces[:])
    rot = Matrix.Rotation(turn, 3, 'Z') @ Matrix.Rotation(tilt[0], 3, 'X') @ Matrix.Rotation(tilt[1], 3, 'Y')
    for v in tmp.verts:
        v.co = rot @ Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bmesh.ops.triangulate(tmp, faces=tmp.faces[:])
    for _ in range(sub):
        bmesh.ops.subdivide_edges(tmp, edges=tmp.edges[:], cuts=1, use_grid_fill=True)
    tmp.normal_update()
    sharp = [e for e in tmp.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > 0.12]
    if sharp and bevel > 0.0:
        bmesh.ops.bevel(tmp, geom=sharp, offset=bevel * min(size), segments=2, profile=0.55, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(tmp, faces=[f for f in tmp.faces if len(f.verts) > 4])
    tmp.normal_update()
    off = Vector((seed * 5.1, seed * 2.3, seed * 7.7))
    amp = lump * min(size)
    freq = 1.6 / max(max(size), 0.3)
    for v in tmp.verts:
        v.co += v.normal * (amp * (noise.noise(v.co * freq + off) + 0.45 * noise.noise(v.co * freq * 2.7 + off)))
    tmp.normal_update()
    centre = Vector(centre)
    zs = [v.co.z for v in tmp.verts]
    zr = zrange or (centre.z + min(zs) * 0.75, centre.z + max(zs))
    paint = rock_paint(pal, seed, zr[0], zr[1], moss)
    made = {v: p.bm.verts.new(v.co + centre) for v in tmp.verts}
    for f in tmp.faces:
        try:
            nf = p.bm.faces.new([made[v] for v in f.verts])
        except ValueError:
            continue
        nf.smooth = True
        for loop, src in zip(nf.loops, f.verts):
            loop[p.col] = lin(paint(src.co + centre, src.normal))
    tmp.free()


def stones(p, centre, radius, count, seed, pal='shore', size=(0.14, 0.26), moss=0.0, ring=True):
    """Small stones round a foot or scattered on a patch."""
    rnd = random.Random(seed)
    for k in range(count):
        a = 2 * math.pi * k / count + rnd.uniform(-0.3, 0.3)
        d = radius * (rnd.uniform(0.85, 1.1) if ring else math.sqrt(rnd.uniform(0.02, 1.0)))
        r = rnd.uniform(*size)
        chunk(p, (centre[0] + math.cos(a) * d, centre[1] + math.sin(a) * d, centre[2] + r * 0.35), (r * rnd.uniform(0.9, 1.4), r, r * rnd.uniform(0.6, 0.9)), seed + k * 7, pal,
              pts=9, bevel=0.2, sub=0, turn=rnd.uniform(0, 3.1), moss=moss)


# --- small goods used inside bigger props ---------------------------------------------------------------------
def cask(p, m, s=1.0, seed=0, lid=True):
    """A stave barrel, 0.95 tall at s = 1, standing on the origin of m."""
    rnd = random.Random(seed)
    tint = wood_tint(seed)
    tone = [rnd.uniform(0.0, 1.0) for _ in range(14)]

    mi, m3 = m.inverted(), m.to_3x3().inverted()

    def stave(co, nrm):
        lc = mi @ co
        ln = m3 @ nrm
        ang = math.atan2(ln.y, ln.x)
        c = lerp(lerp(tint, WOOD_DARK, 0.55), tint, 0.3 + 0.7 * tone[int((ang / (2 * math.pi) + 1.0) * 14) % 14])
        return lerp(lerp(c, WOOD_DARK, 0.5), c, clamp01(0.25 + lc.z / (0.9 * s)))

    prof = [(s * (0.27 + 0.075 * math.sin(math.pi * k / 6)), s * 0.95 * k / 6) for k in range(7)]
    lathe(p, prof, stave, sides=14, smooth=False, m=m, cap=False)
    disc(p, (0, 0, 0), s * 0.27, lerp(tint, WOOD_DARK, 0.6), 14, m, down=True)
    disc(p, (0, 0, s * 0.905), s * 0.268, lerp(tint, WOOD_DARK, 0.30 if lid else 0.85), 14, m)
    for k in (1, 3, 5):
        zz = 0.95 * k / 6
        rr = 0.27 + 0.075 * math.sin(math.pi * k / 6) + 0.008
        lathe(p, [(s * rr, s * (zz - 0.028)), (s * (rr + 0.006), s * zz), (s * rr, s * (zz + 0.028))], metal(rust=0.4), sides=14, smooth=False, m=m, cap=False)


def case(p, m, size, seed, grey=0.3):
    """A slatted crate with corner battens. size = full extents, standing on the origin of m."""
    sx, sy, sz = size
    dark = lerp(WOOD_DARK, (0.05, 0.04, 0.04), 0.4)
    p.box((0, 0, sz / 2), (sx * 0.94, sy * 0.94, sz * 0.94), lambda co, nrm: dark, xform=m)
    n = max(2, int(round(sz / 0.2)))
    for k in range(n):
        zc = sz * (k + 0.5) / n
        for sgn in (-1, 1):
            board(p, m @ Matrix.Translation((0, sgn * sy / 2, zc)), (sx, 0.035, sz / n * 0.9), seed + k * 3 + sgn, grey)
            board(p, m @ Matrix.Translation((sgn * sx / 2, 0, zc)), (0.035, sy, sz / n * 0.9), seed + k * 5 + sgn + 40, grey)
    ny = max(2, int(round(sy / 0.2)))
    for k in range(ny):
        board(p, m @ Matrix.Translation((0, -sy / 2 + sy * (k + 0.5) / ny, sz)), (sx, sy / ny * 0.9, 0.035), seed + 80 + k, grey)
    for ax in (-1, 1):
        for ay in (-1, 1):
            board(p, m @ Matrix.Translation((ax * sx / 2, ay * sy / 2, sz / 2)), (0.07, 0.07, sz + 0.04), seed + 90 + ax + ay * 2, grey * 0.5, bevel=0.015)


def sack(p, at, s=1.0, seed=0, tint=(0.72, 0.60, 0.40), lean=0.0):
    x, y, z = at
    faces = p.blob((x, y, z + 0.30 * s), (0.30 * s, 0.24 * s, 0.34 * s), lambda co, nrm: (0, 0, 0), seed, rough=0.16, subdiv=2, smooth=True)
    verts = {v for f in faces for v in f.verts}
    for v in verts:
        k = clamp01((v.co.z - z) / (0.6 * s))
        v.co.x += lean * (v.co.z - z)
        if v.co.z < z + 0.05 * s:
            v.co.z = z + 0.02 * s
        if k > 0.82:
            pull = (k - 0.82) / 0.18
            v.co.x = x + lean * (v.co.z - z) + (v.co.x - x - lean * (v.co.z - z)) * (1.0 - 0.65 * pull)
            v.co.y = y + (v.co.y - y) * (1.0 - 0.65 * pull)
    for f in faces:
        f.normal_update()
    p.paint(faces, lambda co, nrm: lerp(mul(tint, 0.52), tint, clamp01(nrm.z * 0.5 + 0.55 + 0.25 * noise.noise(co * 6.0))))
    top = Vector((x + lean * 0.62 * s, y, z + 0.60 * s))
    lash(p, top, 0.085 * s, 2, 0.014 * s)
    lathe(p, [(0.085 * s, 0.0), (0.13 * s, 0.07 * s), (0.10 * s, 0.10 * s)], lambda co, nrm: lerp(mul(tint, 0.6), tint, clamp01(nrm.z + 0.5)), at=top + Vector((0, 0, 0.03 * s)), sides=8,
          smooth=True)


def bottle(p, m, s=1.0, tint=(0.12, 0.32, 0.18)):
    def glass(co, nrm):
        return lerp(mul(tint, 0.55), lerp(tint, (0.85, 0.95, 0.80), 0.35), clamp01(nrm.z * 0.4 + 0.45 + 0.5 * max(0.0, nrm.dot(SUN_DIR)) ** 3))
    lathe(p, [(0.045 * s, 0.0), (0.055 * s, 0.015 * s), (0.055 * s, 0.15 * s), (0.022 * s, 0.21 * s), (0.02 * s, 0.29 * s), (0.026 * s, 0.295 * s), (0.026 * s, 0.31 * s)], glass, sides=8,
          smooth=True, m=m)
    lathe(p, [(0.018 * s, 0.31 * s), (0.016 * s, 0.335 * s)], (0.62, 0.46, 0.28), sides=6, smooth=False, m=m)


def tankard(p, m, s=1.0, seed=0):
    tint = wood_tint(seed)
    lathe(p, [(0.055 * s, 0.0), (0.06 * s, 0.16 * s)], lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.5), tint, clamp01(0.5 + 0.5 * math.sin(math.atan2(nrm.y, nrm.x) * 5))), sides=10,
          smooth=False, m=m)
    for zz in (0.03, 0.13):
        lathe(p, [(0.063 * s, (zz - 0.012) * s), (0.063 * s, (zz + 0.012) * s)], metal(rust=0.2), sides=10, smooth=False, m=m, cap=False)
    lathe(p, [(0.052 * s, 0.158 * s), (0.03 * s, 0.175 * s), (0.004, 0.18 * s)], (0.96, 0.93, 0.84), sides=10, smooth=True, m=m, cap=False)
    pipe(p, [m @ Vector(v) * 1.0 for v in ((0.06 * s, 0, 0.13 * s), (0.10 * s, 0, 0.12 * s), (0.105 * s, 0, 0.06 * s), (0.06 * s, 0, 0.04 * s))], 0.011 * s, metal(rust=0.2), sides=5,
         up=m.to_3x3() @ Vector((0, 1, 0)))


def coins(p, at, r, h, seed, n=40):
    """A heap of gold: a glittering mound with loose coins and little stacks all over it."""
    x, y, z = at
    rnd = random.Random(seed)
    faces = p.blob((x, y, z), (r, r, h), lambda co, nrm: (0, 0, 0), seed, rough=0.10, subdiv=3, smooth=True)
    for v in {v for f in faces for v in f.verts}:
        if v.co.z < z:
            v.co.z = z
    for f in faces:
        f.normal_update()
    p.paint(faces, lambda co, nrm: lerp(GOLD_LO, GOLD_HI, clamp01(0.30 + 0.35 * nrm.z + 0.55 * noise.noise(co * 42.0))))
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), r * math.sqrt(rnd.uniform(0, 1.25))
        zz = z + (h * math.sqrt(max(0.0, 1.0 - (d / r) ** 2)) if d < r else 0.0) + 0.012
        tall = 0.012 if k % 5 else rnd.uniform(0.05, 0.12)
        tilt = 0.75 if k % 5 else 0.12
        m = Matrix.Translation((x + math.cos(a) * d, y + math.sin(a) * d, zz)) @ Matrix.Rotation(rnd.uniform(-tilt, tilt), 4, 'X') @ Matrix.Rotation(rnd.uniform(-tilt, tilt), 4, 'Y')
        lathe(p, [(0.045, 0.0), (0.045, tall)], gilt, sides=8, smooth=False, m=m)
# Brinewake set dressing, part two: skeletons and bones, graves, wrecks, ruins, idols, bridges, platforms, cranes, racks.
# Run after a_lib.py through bl_run.py.
WANT = globals().get("BW_ONLY")


def want(name):
    return not WANT or any(k in name for k in WANT)


def mark(p):
    return len(p.bm.verts)


def move_since(p, start, m):
    """Move everything built since mark() by m: lets a part be modelled upright at the origin, then posed."""
    p.bm.verts.ensure_lookup_table()
    for i in range(start, len(p.bm.verts)):
        v = p.bm.verts[i]
        v.co = m @ v.co


def frame(origin, up, fwd):
    """Matrix with z along `up` and the face (-y) turned toward `fwd`."""
    z = Vector(up).normalized()
    f = Vector(fwd)
    f = f - z * f.dot(z)
    if f.length < 1e-4:
        f = Vector((1, 0, 0)) - z * z.x
    y = -f.normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def bone_paint(age=0.35, seed=0, moss=0.0):
    off = Vector((seed * 1.7, seed * 0.9, seed * 2.3))

    def paint(co, nrm):
        c = lerp(BONE_LO, BONE_HI, clamp01(0.42 + 0.5 * nrm.z + 0.22 * noise.noise(co * 13.0 + off)))
        c = lerp(c, (0.44, 0.40, 0.25), age * clamp01(noise.noise(co * 3.5 + off) + 0.35))
        if moss:
            c = lerp(c, (0.26, 0.42, 0.14), moss * clamp01(nrm.z * 0.9 + noise.noise(co * 2.0 + off) * 0.8))
        return c
    return paint


def bone(p, a, b, r, paint, knob=1.55):
    a, b = Vector(a), Vector(b)
    pipe(p, [a, a.lerp(b, 0.10), a.lerp(b, 0.5), a.lerp(b, 0.90), b], [r * knob, r * 1.05, r * 0.78, r * 1.05, r * knob], paint, sides=6, up=Vector((0.31, 0.95, 0.07)))


def skull(p, m, s=1.0, paint=None, jaw=True, gape=0.25):
    """Skull with its base at the origin of m, looking along -y."""
    paint = paint or bone_paint()
    start = mark(p)
    eyes = [Vector((sx * 0.040 * s, -0.088 * s, 0.108 * s)) for sx in (-1, 1)]
    nose = Vector((0, -0.105 * s, 0.062 * s))
    faces = p.blob((0, 0, 0.118 * s), (0.094 * s, 0.110 * s, 0.100 * s), const((0, 0, 0)), 1, rough=0.0, subdiv=3, smooth=True)
    for v in {v for f in faces for v in f.verts}:
        if v.co.z < 0.07 * s:                                        # cheeks and jaw line narrower than the brain case
            v.co.x *= 0.74 + 0.26 * clamp01(v.co.z / (0.07 * s))
        for e in eyes:
            d = (v.co - e).length
            if d < 0.046 * s:
                v.co += Vector((0, 0.034 * s, 0)) * (1.0 - d / (0.046 * s)) ** 0.7
        d = (v.co - nose).length
        if d < 0.028 * s:
            v.co += Vector((0, 0.02 * s, 0)) * (1.0 - d / (0.028 * s))
    for f in faces:
        f.normal_update()
    dark = (0.05, 0.04, 0.05)

    def face_paint(co, nrm):
        c = paint(co, nrm)
        k = max(clamp01(1.25 - (co - e).length / (0.030 * s)) for e in eyes)
        k = max(k, clamp01(1.3 - (Vector((co.x * 1.5, co.y, co.z)) - nose).length / (0.020 * s)))
        return lerp(c, dark, clamp01(k * 1.4))
    p.paint(faces, face_paint)
    p.box((0, -0.072 * s, 0.022 * s), (0.092 * s, 0.062 * s, 0.045 * s), paint, bevel=0.012 * s)
    for k in range(6):
        p.box(((-0.0325 + 0.013 * k) * s, -0.104 * s, 0.000 * s), (0.011 * s, 0.008 * s, 0.022 * s), const((0.96, 0.93, 0.80)))
    if jaw:
        js = mark(p)
        p.box((0, -0.060 * s, -0.030 * s), (0.086 * s, 0.078 * s, 0.022 * s), paint, bevel=0.009 * s)
        for sx in (-1, 1):
            p.box((sx * 0.042 * s, -0.012 * s, -0.005 * s), (0.012 * s, 0.024 * s, 0.06 * s), paint, bevel=0.004 * s)
        for k in range(6):
            p.box(((-0.0325 + 0.013 * k) * s, -0.096 * s, -0.012 * s), (0.011 * s, 0.008 * s, 0.018 * s), const((0.94, 0.90, 0.76)))
        move_since(p, js, Matrix.Translation((0, -0.01 * s, 0.01 * s)) @ Matrix.Rotation(-gape, 4, 'X') @ Matrix.Translation((0, 0.01 * s, -0.01 * s)))
    move_since(p, start, m)


def ribcage(p, m, s=1.0, paint=None, ribs=8):
    """Spine and ribs. Origin at the bottom of the spine, neck at z = 0.52 s, chest toward -y."""
    paint = paint or bone_paint()
    start = mark(p)
    pts = [Vector((0, 0.035 * s * math.sin(t * 3.4 - 0.4), 0.52 * s * t)) for t in (k / 14 for k in range(15))]
    pipe(p, pts, [(0.030 if k % 2 == 0 else 0.019) * s for k in range(15)], paint, sides=6, up=Vector((1, 0, 0)))
    for k in range(ribs):
        z = (0.19 + 0.29 * k / (ribs - 1)) * s
        rx = (0.125 + 0.045 * math.sin(math.pi * (k + 1.5) / (ribs + 1.5))) * s
        end = math.pi * (0.62 if k < 2 else 0.97)
        for sx in (-1, 1):
            arc = []
            for j in range(7):
                q = end * j / 6
                arc.append(Vector((sx * math.sin(q) * rx, 0.02 * s - (1 - math.cos(q)) * 0.068 * s, z - 0.055 * s * math.sin(q * 0.8))))
            pipe(p, arc, [0.012 * s, 0.013 * s, 0.013 * s, 0.012 * s, 0.011 * s, 0.010 * s, 0.008 * s], paint, sides=5, up=UP)
    p.box((0, -0.118 * s, 0.335 * s), (0.042 * s, 0.016 * s, 0.22 * s), paint, bevel=0.006 * s)
    for sx in (-1, 1):
        bone(p, (sx * 0.02 * s, -0.11 * s, 0.475 * s), (sx * 0.185 * s, -0.01 * s, 0.485 * s), 0.011 * s, paint, 1.3)
        tri = [Vector((sx * 0.06 * s, 0.085 * s, 0.46 * s)), Vector((sx * 0.17 * s, 0.07 * s, 0.47 * s)), Vector((sx * 0.085 * s, 0.10 * s, 0.30 * s))]
        fquad(p, tri if sx > 0 else tri[::-1], paint)
        fquad(p, tri[::-1] if sx > 0 else tri, paint)
    move_since(p, start, m)


def pelvis(p, m, s=1.0, paint=None):
    paint = paint or bone_paint()
    lathe(p, [(0.035 * s, -0.085 * s), (0.085 * s, -0.045 * s), (0.130 * s, 0.02 * s), (0.142 * s, 0.075 * s), (0.118 * s, 0.085 * s), (0.10 * s, 0.03 * s), (0.06 * s, -0.02 * s),
              (0.03 * s, -0.055 * s)], paint, sides=8, m=m @ Matrix.Diagonal((1.0, 0.66, 1.0, 1.0)), cap=False)


def hand(p, wrist, d, s, paint, curl=0.3):
    wrist, d = Vector(wrist), Vector(d).normalized()
    side = d.cross(UP)
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    nrm = side.cross(d)
    for k in range(4):
        o = side * ((k - 1.5) * 0.017 * s)
        a = wrist + o * 0.6
        b = a + (d + o.normalized() * 0.12 * (k - 1.5)).normalized() * 0.075 * s
        c = b + (d - nrm * curl).normalized() * 0.07 * s
        pipe(p, [a, b, c], [0.008 * s, 0.007 * s, 0.005 * s], paint, sides=4)
    pipe(p, [wrist, wrist + (d + side * 1.2).normalized() * 0.06 * s], [0.008 * s, 0.006 * s], paint, sides=4)


def skeleton(p, J, s=1.0, seed=0, age=0.35, moss=0.0, legs=True, arms=(1, 1)):
    """J: pelvis, up (spine direction), fwd (chest direction), head_up, head_fwd, and limb points
    la/ra = (elbow, wrist), ll/rl = (knee, ankle, toe). l = +x side of the body."""
    paint = bone_paint(age, seed, moss)
    pv = Vector(J['pelvis'])
    body = frame(pv, J['up'], J['fwd'])
    pelvis(p, body, s, paint)
    ribcage(p, body @ Matrix.Translation((0, 0, 0.06 * s)), s, paint)
    neck = body @ Vector((0, 0, 0.60 * s))
    hm = frame(neck, J.get('head_up', J['up']), J.get('head_fwd', J['fwd']))
    skull(p, hm, s, paint, gape=J.get('gape', 0.25))
    for key, sx, on in (('la', 1, arms[0]), ('ra', -1, arms[1])):
        if not on or key not in J:
            continue
        sh = body @ Vector((sx * 0.20 * s, 0.0, 0.545 * s))
        el, wr = Vector(J[key][0]), Vector(J[key][1])
        bone(p, sh, el, 0.020 * s, paint)
        off = (wr - el).normalized().cross(Vector((0.3, 0.2, 0.9))).normalized() * 0.014 * s
        bone(p, el + off, wr + off, 0.012 * s, paint, 1.4)
        bone(p, el - off, wr - off, 0.011 * s, paint, 1.4)
        hand(p, wr, wr - el, s, paint)
    if legs:
        for key, sx in (('ll', 1), ('rl', -1)):
            if key not in J:
                continue
            hip = body @ Vector((sx * 0.095 * s, 0.0, -0.045 * s))
            kn, an, toe = (Vector(v) for v in J[key])
            bone(p, hip, kn, 0.025 * s, paint)
            bone(p, kn, an, 0.020 * s, paint, 1.4)
            off = (an - kn).normalized().cross(Vector((0.3, 0.9, 0.2))).normalized() * 0.022 * s
            bone(p, kn + off, an + off, 0.009 * s, paint, 1.2)
            side = (toe - an).normalized().cross(UP)
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            side.normalize()
            for k in range(4):
                pipe(p, [an, an.lerp(toe, 0.6) + side * (k - 1.5) * 0.016 * s, toe + side * (k - 1.5) * 0.026 * s], [0.011 * s, 0.008 * s, 0.006 * s], paint, sides=4)
    return body, hm


def tricorn(p, m, s=1.0, col=(0.13, 0.11, 0.11), trim=OCHRE):
    start = mark(p)
    faces = p.blob((0, 0.01, 0.045 * s), (0.118 * s, 0.13 * s, 0.085 * s), shade(col, 0.6), 1, 0.0, 2, smooth=True)
    n = 24
    inner = [Vector((0.122 * s * math.sin(a), 0.01 - 0.134 * s * math.cos(a), 0.0)) for a in (2 * math.pi * k / n for k in range(n + 1))]
    outer = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        c3 = math.cos(3 * a)
        r = (0.275 + 0.085 * c3) * s
        outer.append(Vector((r * math.sin(a), 0.01 - r * math.cos(a), 0.02 * s + 0.115 * s * (1 - c3) / 2)))
    for k in range(n):
        fquad(p, [inner[k], outer[k], outer[k + 1], inner[k + 1]], shade(col, 0.55), smooth=True)
        fquad(p, [inner[k + 1], outer[k + 1], outer[k], inner[k]], shade(mul(col, 0.7), 0.6), smooth=True)
    pipe(p, outer[:-1], 0.011 * s, shade(trim, 0.55), sides=4, closed=True)
    move_since(p, start, m)


def cutlass(p, m, s=1.0):
    """Curved blade, point toward +z of m, grip at the origin."""
    start = mark(p)
    steel = lambda co, nrm: lerp((0.36, 0.38, 0.44), (0.92, 0.94, 0.97), clamp01(0.3 + 0.7 * abs(nrm.x) + 0.2 * noise.noise(co * 20.0)))
    spine, edge = [], []
    for k in range(7):
        t = k / 6
        z = (0.12 + 0.72 * t) * s
        bend = 0.10 * s * t * t
        w = (0.035 + 0.02 * math.sin(math.pi * t * 0.9)) * s * (1.0 if k < 6 else 0.1)
        spine.append(Vector((0, bend + w, z)))
        edge.append(Vector((0, bend - w, z)))
    for a0, a1, b0, b1 in zip(spine, spine[1:], edge, edge[1:]):
        fquad(p, [a0 + Vector((0.006 * s, 0, 0)), b0, b1, a1 + Vector((0.006 * s, 0, 0))], steel)
        fquad(p, [a1 - Vector((0.006 * s, 0, 0)), b1, b0, a0 - Vector((0.006 * s, 0, 0))], steel)
        fquad(p, [a0 - Vector((0.006 * s, 0, 0)), a0 + Vector((0.006 * s, 0, 0)), a1 + Vector((0.006 * s, 0, 0)), a1 - Vector((0.006 * s, 0, 0))], (0.30, 0.32, 0.36))
    lathe(p, [(0.018 * s, -0.01 * s), (0.02 * s, 0.05 * s), (0.017 * s, 0.11 * s)], shade(LEATHER_D, 0.6), sides=6)
    lathe(p, [(0.004, -0.045 * s), (0.026 * s, -0.03 * s), (0.016 * s, -0.01 * s)], gilt, sides=6)
    p.box((0, 0, 0.118 * s), (0.03 * s, 0.14 * s, 0.018 * s), gilt, bevel=0.005 * s)
    pipe(p, [Vector((0, -0.07 * s, 0.118 * s)), Vector((0, -0.085 * s, 0.05 * s)), Vector((0, -0.03 * s, -0.03 * s))], 0.008 * s, gilt, sides=4, up=Vector((1, 0, 0)))
    move_since(p, start, m)


def sand_mound(p, at, size, seed):
    faces = p.blob(at, size, const((0, 0, 0)), seed, rough=0.2, subdiv=3, smooth=True)
    for v in {v for f in faces for v in f.verts}:
        if v.co.z < at[2] - size[2] * 0.2:
            v.co.z = at[2] - size[2] * 0.2
    for f in faces:
        f.normal_update()
    p.paint(faces, lambda co, nrm: lerp((0.60, 0.48, 0.30), (0.95, 0.85, 0.62), clamp01(nrm.z * 0.75 + 0.15 + 0.2 * noise.noise(co * 3.0))))


# ------------------------------------------------------------------ skeletons
def skeleton_sit(name, seed, captain=True):
    if not want(name):
        return
    p = Prop(name)
    J = dict(pelvis=(0, 0.10, 0.11), up=(0, 0.34, 1), fwd=(0, -1, 0), head_up=(0.30, 0.18, 1), head_fwd=(0.2, -1, -0.25), gape=0.5,
             la=((0.30, 0.10, 0.36), (0.34, -0.20, 0.06)), ra=((-0.29, 0.02, 0.38), (-0.20, -0.26, 0.20)),
             ll=((0.16, -0.38, 0.07), (0.22, -0.80, 0.05), (0.26, -0.86, 0.22)), rl=((-0.17, -0.26, 0.36), (-0.19, -0.52, 0.05), (-0.20, -0.70, 0.07)))
    body, hm = skeleton(p, J, 1.0, seed)
    if captain:
        tricorn(p, hm @ Matrix.Translation((0, 0, 0.165)) @ Matrix.Rotation(0.18, 4, 'Y'), 1.0)
        bottle(p, at_m(-0.26, -0.33, 0.0), 1.0, (0.14, 0.34, 0.20))
        cutlass(p, at_m(0.52, -0.10, 0.50, 0.4, 0.0, math.pi - 0.22), 1.0)
        for k in range(3):                                           # rags of a coat still on the shoulders
            a = body @ Vector((-0.20 + 0.20 * k, 0.09, 0.56))
            fquad(p, [a, a + Vector((0.16, 0.03, -0.02)), a + Vector((0.20, 0.10, -0.46 - 0.05 * k)), a + Vector((0.02, 0.12, -0.40))], shade(NAVY, 0.5))
            fquad(p, [a + Vector((0.02, 0.12, -0.40)), a + Vector((0.20, 0.10, -0.46 - 0.05 * k)), a + Vector((0.16, 0.03, -0.02)), a], shade(mul(NAVY, 0.6), 0.5))
    sand_mound(p, (0, 0.05, -0.04), (0.55, 0.75, 0.10), seed)
    p.export()


def skeleton_lie(name, seed):
    if not want(name):
        return
    p = Prop(name)
    J = dict(pelvis=(0, 0, 0.09), up=(0.08, 1, 0.03), fwd=(0, 0, 1), head_up=(0.5, 1, 0.1), head_fwd=(0.5, 0, 1), gape=0.6,
             la=((0.42, 0.50, 0.05), (0.72, 0.72, 0.04)), ra=((-0.36, 0.34, 0.05), (-0.42, 0.02, 0.05)),
             ll=((0.14, -0.44, 0.07), (0.20, -0.86, 0.05), (0.30, -0.98, 0.05)), rl=((-0.20, -0.30, 0.34), (-0.26, -0.62, 0.05), (-0.30, -0.78, 0.05)))
    skeleton(p, J, 1.0, seed, age=0.5, moss=0.25)
    cutlass(p, at_m(0.80, 0.84, 0.03, 0.9, 1.5708, 0.0), 1.0)
    sand_mound(p, (0, 0.2, -0.05), (0.75, 1.15, 0.10), seed)
    p.export()


def skeleton_buried(name, seed):
    if not want(name):
        return
    p = Prop(name)
    J = dict(pelvis=(0, 0.10, -0.30), up=(0.18, -0.30, 1), fwd=(0, -1, 0.3), head_up=(0.1, 0.5, 1), head_fwd=(0, -1, 0.9), gape=0.7,
             la=((0.30, -0.26, 0.42), (0.26, -0.44, 0.78)), ra=((-0.30, -0.22, 0.10), (-0.46, -0.50, 0.06)))
    skeleton(p, J, 1.0, seed, legs=False)
    sand_mound(p, (0, 0.0, -0.02), (0.75, 0.75, 0.16), seed)
    p.export()


def skeleton_chest(name, seed):
    if not want(name):
        return
    p = Prop(name)
    chest_geo(p, at_m(0, -0.25, 0, 0.1), seed)
    J = dict(pelvis=(0.02, 0.50, 0.12), up=(0, -0.62, 0.78), fwd=(0, -0.78, -0.62), head_up=(0.3, -0.9, 0.3), head_fwd=(0.2, -0.4, -1), gape=0.3,
             la=((0.32, 0.02, 0.50), (0.36, -0.36, 0.52)), ra=((-0.30, 0.0, 0.50), (-0.30, -0.40, 0.46)),
             ll=((0.36, 0.30, 0.07), (0.58, -0.06, 0.05), (0.66, -0.20, 0.05)), rl=((-0.34, 0.34, 0.07), (-0.60, 0.02, 0.05), (-0.70, -0.10, 0.05)))
    skeleton(p, J, 1.0, seed, age=0.3)
    coins(p, (0.75, -0.55, 0), 0.18, 0.06, seed, n=16)
    p.export()


def skull_prop(name, seed, moss=0.0):
    if not want(name):
        return
    p = Prop(name)
    skull(p, at_m(0, 0, 0.035, 0.3, 0.0, 0.25), 1.15, bone_paint(0.4, seed, moss), gape=0.2)
    p.export()


def skull_pile(name, seed, n=9):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), 0.42 * math.sqrt(rnd.random()) * (1 if k > 2 else 0.3)
        z = 0.03 + (0.20 if k < 3 else 0.0) + (0.2 if k == 0 else 0.0)
        skull(p, at_m(math.cos(a) * d, math.sin(a) * d, z, rnd.uniform(0, 6.28), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5)), rnd.uniform(0.95, 1.2), bone_paint(rnd.uniform(0.2, 0.6), seed + k),
              jaw=k % 3 != 0)
    paint = bone_paint(0.4, seed)
    for k in range(8):
        a, d = rnd.uniform(0, 6.28), rnd.uniform(0.3, 0.75)
        c = Vector((math.cos(a) * d, math.sin(a) * d, 0.03))
        q = rnd.uniform(0, 3.14)
        bone(p, c - Vector((math.cos(q), math.sin(q), 0)) * 0.2, c + Vector((math.cos(q), math.sin(q), rnd.uniform(0, 0.3))) * 0.2, 0.02, paint)
    candle(p, (0.05, -0.02, 0.50), 0.10)
    p.export()


def candle(p, at, h=0.14):
    x, y, z = at
    lathe(p, [(0.045, -0.01), (0.03, 0.012), (0.024, 0.02), (0.022, h), (0.004, h + 0.004)], lambda co, nrm: lerp((0.72, 0.66, 0.50), (0.98, 0.94, 0.80), clamp01((co.z - z) / h)), at=at, sides=7)
    lathe(p, [(0.004, 0.0), (0.016, 0.02), (0.012, 0.045), (0.003, 0.08)], lambda co, nrm: lerp((1.0, 0.95, 0.6), (1.0, 0.5, 0.1), clamp01((co.z - z - h) / 0.08)), at=(x, y, z + h + 0.008), sides=6)


def skull_pike(name, seed, n=1):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(n):
        x = (k - (n - 1) / 2) * 0.7
        h = rnd.uniform(1.7, 2.3)
        lx, ly = rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08)
        log(p, (x, 0, -0.2), (x + lx * h, ly * h, h), 0.05, 0.035, seed + k, sides=6, foot=0.3, wob=0.2, point=0.10)
        skull(p, at_m(x + lx * h, ly * h, h - 0.08, rnd.uniform(-0.5, 0.5), 0.0, rnd.uniform(-0.2, 0.2)), 1.15, bone_paint(0.45, seed + k), jaw=k % 2 == 0)
        lash(p, (x + lx * (h - 0.25), ly * (h - 0.25), h - 0.25), 0.045, 3, 0.012)
        for j in range(2):
            a = Vector((x + lx * (h - 0.22), ly * (h - 0.22), h - 0.22))
            fquad(p, [a, a + Vector((0.07, 0.02 + 0.05 * j, -0.10)), a + Vector((0.10, 0.04 + 0.08 * j, -0.50 - 0.1 * j)), a + Vector((0.02, 0.03, -0.42))], shade(RED, 0.5))
            fquad(p, [a + Vector((0.02, 0.03, -0.42)), a + Vector((0.10, 0.04 + 0.08 * j, -0.50 - 0.1 * j)), a + Vector((0.07, 0.02 + 0.05 * j, -0.10)), a], shade(mul(RED, 0.6), 0.5))
    stones(p, (0, 0, 0), 0.22 + 0.3 * (n - 1), 4 + n, seed)
    p.export()


def bone_pile(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    paint = bone_paint(0.5, seed, 0.2)
    ribcage(p, at_m(0.1, 0.1, 0.13, 0.5, 1.45, 0.2), 1.0, paint, ribs=6)
    pelvis(p, at_m(-0.35, -0.2, 0.08, 0.3, 0.4, 0.2), 1.0, paint)
    skull(p, at_m(0.38, -0.36, 0.03, 2.4, 0.0, 0.5), 1.1, paint, jaw=False)
    for k in range(9):
        a, d = rnd.uniform(0, 6.28), rnd.uniform(0.15, 0.7)
        c = Vector((math.cos(a) * d, math.sin(a) * d, 0.03))
        q = rnd.uniform(0, 3.14)
        L = rnd.uniform(0.14, 0.24)
        bone(p, c - Vector((math.cos(q), math.sin(q), 0)) * L, c + Vector((math.cos(q), math.sin(q), rnd.uniform(0, 0.25))) * L, rnd.uniform(0.014, 0.024), paint)
    p.export()


def leviathan(name, seed):
    """The picked ribs and skull of a sea beast, half sunk in the sand: a landmark to walk through."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    paint = bone_paint(0.5, seed, 0.3)
    n = 8
    for k in range(n):
        x = -5.0 + 9.0 * k / (n - 1)
        size = 1.0 - 0.45 * abs(k - 2.5) / n * 2
        lathe(p, [(0.15, -0.26), (0.34, -0.20), (0.24, 0.0), (0.34, 0.20), (0.15, 0.26)], paint, sides=8, m=zto((x, 0.1 * math.sin(k), 0.22 * size), (1, 0, 0.03)) @ Matrix.Scale(size, 4))
        for sy in (-1, 1):
            if rnd.random() < 0.12:
                continue
            H, W = 3.3 * size, 2.3 * size
            arc = [Vector((x + 0.25 * math.sin(q), sy * (0.2 + W * math.sin(q) ** 0.8), 0.2 + H * (1 - math.cos(q)) * 0.62)) for q in (math.pi * 0.86 * j / 8 for j in range(9))]
            snap = rnd.random() < 0.25
            if snap:
                arc = arc[:5]
            pipe(p, arc, [0.16 * size * (1.0 - 0.07 * j) for j in range(len(arc))], paint, sides=7, up=Vector((1, 0, 0)))
    sm = at_m(5.6, 0.0, 0.25, 0.0, -0.12)
    start = mark(p)
    faces = p.blob((0.9, 0, 0.55), (1.6, 0.85, 0.62), const((0, 0, 0)), seed, rough=0.10, subdiv=3, smooth=True)
    eyes = [Vector((0.55, sy * 0.72, 0.72)) for sy in (-1, 1)]
    for v in {v for f in faces for v in f.verts}:
        if v.co.x > 0.9:
            k = (v.co.x - 0.9) / 1.6
            v.co.y *= 1.0 - 0.6 * k
            v.co.z = 0.55 + (v.co.z - 0.55) * (1.0 - 0.45 * k)
        for e in eyes:
            d = (v.co - e).length
            if d < 0.36:
                v.co.y -= math.copysign(0.24, e.y) * (1.0 - d / 0.36)
    for f in faces:
        f.normal_update()
    p.paint(faces, lambda co, nrm: lerp(paint(co, nrm), (0.05, 0.04, 0.05), max(clamp01(1.2 - (co - e).length / 0.26) for e in eyes)))
    for sy in (-1, 1):
        pipe(p, [Vector((0.0, sy * 0.62, 0.2)), Vector((1.2, sy * 0.5, 0.04)), Vector((2.5, sy * 0.16, 0.05))], [0.16, 0.13, 0.07], paint, sides=6)
        for k in range(7):
            xx = 1.0 + 0.24 * k
            yy = sy * (0.72 - 0.085 * k)
            lathe(p, [(0.05, 0.0), (0.035, 0.12), (0.004, 0.26)], const((0.96, 0.93, 0.80)), sides=5, m=zto((xx, yy, 0.30 - 0.02 * k), (0, sy * 0.25, -1)))
    move_since(p, start, sm)
    sand_mound(p, (0, 0, -0.1), (6.5, 2.6, 0.3), seed)
    p.export()


def cage_geo(p, m, r=0.48, h=1.55, bars=10):
    iron = metal(rust=0.6)
    for z in (0.0, h * 0.5, h):
        lathe(p, [(r - 0.02, z - 0.025), (r + 0.02, z - 0.025), (r + 0.02, z + 0.025), (r - 0.02, z + 0.025), (r - 0.02, z - 0.025)], iron, sides=bars, m=m, smooth=False, cap=False)
    for k in range(bars):
        a = 2 * math.pi * k / bars
        pipe(p, [m @ Vector((math.cos(a) * r, math.sin(a) * r, 0)), m @ Vector((math.cos(a) * r, math.sin(a) * r, h)), m @ Vector((math.cos(a) * r * 0.5, math.sin(a) * r * 0.5, h + 0.30)),
                 m @ Vector((0, 0, h + 0.38))], 0.016, iron, sides=4)
        pipe(p, [m @ Vector((math.cos(a) * r, math.sin(a) * r, 0)), m @ Vector((0, 0, -0.02))], 0.014, iron, sides=4)
    c = m @ Vector((0, 0, h + 0.45))
    pipe(p, [c + Vector((math.cos(q) * 0.07, 0, math.sin(q) * 0.07)) for q in (2 * math.pi * k / 8 for k in range(8))], 0.016, iron, sides=4, up=Vector((0, 1, 0)), closed=True)
    return c


def gibbet(name, seed, body=True):
    if not want(name):
        return
    p = Prop(name)
    log(p, (0, 0, -0.3), (0.05, 0, 5.2), 0.17, 0.14, seed, sides=8, foot=0.5, segs=5)
    beam(p, (-0.3, 0, 4.9), (1.75, 0, 4.98), 0.14, 0.16, seed + 1, grey=0.4)
    beam(p, (0.10, 0, 3.9), (1.0, 0, 4.85), 0.10, 0.12, seed + 2, grey=0.4)
    stones(p, (0, 0, 0), 0.32, 6, seed)
    lash(p, (0.04, 0, 4.6), 0.15, 3, 0.022)
    m = at_m(1.5, 0, 2.55, 0.4, 0.04)
    top = cage_geo(p, m)
    chain(p, top + Vector((0, 0, 0.07)), (1.5, 0, 4.9), 0.10, 0.018)
    if body:
        mm = m.to_3x3()
        o = m.translation
        J = dict(pelvis=o + mm @ Vector((0, 0.05, 0.50)), up=mm @ Vector((0.05, -0.10, 1)), fwd=mm @ Vector((0, -1, 0)), head_up=mm @ Vector((0.2, -0.7, 0.7)), head_fwd=mm @ Vector((0, -0.7, -0.8)),
                 la=(o + mm @ Vector((0.26, -0.05, 0.78)), o + mm @ Vector((0.50, -0.20, 0.62))), ra=(o + mm @ Vector((-0.24, 0.0, 0.76)), o + mm @ Vector((-0.20, -0.10, 0.46))),
                 ll=(o + mm @ Vector((0.14, -0.20, 0.16)), o + mm @ Vector((0.20, -0.52, -0.10)), o + mm @ Vector((0.22, -0.60, -0.26))),
                 rl=(o + mm @ Vector((-0.12, -0.16, 0.14)), o + mm @ Vector((-0.10, -0.08, -0.26)), o + mm @ Vector((-0.10, -0.2, -0.42))))
        skeleton(p, J, 0.95, seed, age=0.5)
    p.export()


def cage(name, seed):
    if not want(name):
        return
    p = Prop(name)
    cage_geo(p, at_m(0, 0, 0.03), 0.6, 1.7, 12)
    p.export()


# ------------------------------------------------------------------ graves
def gravestone(name, seed, kind='slab'):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    sand_mound(p, (0, -0.85, -0.05), (0.55, 1.05, 0.22), seed)
    if kind == 'slab':
        tilt = (rnd.uniform(-0.12, 0.12), rnd.uniform(-0.1, 0.1))
        chunk(p, (0, 0.2, 0.52), (0.36, 0.11, 0.68), seed, 'ruin', pts=22, boxy=0.95, bevel=0.3, sub=2, moss=0.45, tilt=tilt, taper=0.86)
        for k in range(4):
            a = math.pi / 2 * k
            fquad(p, [Vector((0, 0.085, 0.80)), Vector((math.cos(a - 0.4) * 0.05, 0.085, 0.80 + math.sin(a - 0.4) * 0.05)), Vector((math.cos(a) * 0.17, 0.085, 0.80 + math.sin(a) * 0.17)),
                      Vector((math.cos(a + 0.4) * 0.05, 0.085, 0.80 + math.sin(a + 0.4) * 0.05))][::-1], (0.20, 0.19, 0.20))
    else:
        log(p, (0, 0.2, -0.2), (0.04, 0.2, 1.45), 0.07, 0.06, seed, sides=7, foot=0.3, wob=0.15)
        log(p, (-0.42, 0.15, 1.02), (0.42, 0.15, 1.08), 0.055, 0.05, seed + 1, sides=7, wob=0.1)
        lash(p, (0.03, 0.17, 0.98), 0.085, 4, 0.016)
        tricorn(p, at_m(0.04, 0.2, 1.44, 0.6, 0.25), 1.0, (0.20, 0.13, 0.10))
    stones(p, (0, 0.2, 0), 0.32, 6, seed + 3, 'ruin', moss=0.3)
    flowerish = ((0.86, 0.14, 0.16), (0.97, 0.95, 0.90))
    for k in range(4):
        x, y = rnd.uniform(-0.3, 0.3), rnd.uniform(-0.25, 0.0)
        pipe(p, [Vector((x, y, 0.1)), Vector((x + 0.03, y - 0.02, 0.26))], 0.008, const((0.2, 0.44, 0.14)), sides=3)
        p.blob((x + 0.03, y - 0.02, 0.28), (0.035, 0.035, 0.03), const(flowerish[k % 2]), k, 0.2, 1)
    p.export()


# ------------------------------------------------------------------ wrecks
def wreck_hull(name, seed, length=13.0, beam_w=4.6, depth=3.2, planked=0.55):
    """Ribs and broken planking of a beached hull, heeled over and sunk into the sand."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    start = mark(p)
    n = 11
    ribs = {}
    for i in range(n):
        t = i / (n - 1)
        x = -length / 2 + length * t
        w = beam_w / 2 * (1.0 - abs(2 * t - 1) ** 2.4 * 0.85)
        h = depth * (1.0 + 0.35 * (2 * t - 1) ** 2)
        for sy in (-1, 1):
            keep = 1.0 if rnd.random() > 0.25 else rnd.uniform(0.35, 0.7)
            arc = [Vector((x, sy * w * (j / 8) ** 0.5, h * (j / 8) ** 1.5)) for j in range(int(8 * keep) + 1)]
            ribs[(i, sy)] = arc
            if len(arc) > 2:
                tint = lerp(wood_tint(seed + i), WEATHER, 0.6)
                pipe(p, arc, [0.13 - 0.006 * j for j in range(len(arc))], lambda co, nrm, tint=tint: lerp(lerp(tint, (0.16, 0.20, 0.14), 0.55), tint, clamp01(co.z / 1.2 + 0.2 * nrm.z)),
                     sides=6, up=Vector((1, 0, 0)), smooth=False)
    beam(p, (-length / 2 - 0.3, 0, -0.06), (length / 2 + 0.2, 0, -0.06), 0.34, 0.36, seed + 50, grey=0.6)
    beam(p, (length / 2 - 0.1, 0, -0.1), (length / 2 + 1.0, 0, depth * 1.3), 0.30, 0.30, seed + 51, grey=0.6)
    for i in range(n - 1):
        for sy in (-1, 1):
            a, b = ribs[(i, sy)], ribs[(i + 1, sy)]
            for j in range(1, min(len(a), len(b)) - 1):
                if rnd.random() > (planked if sy < 0 else planked * 0.35):
                    continue
                roll = sy * 1.0 * (1 - j / 8)
                beam(p, a[j] + Vector((0, sy * 0.10, 0)), b[j] + Vector((rnd.uniform(-0.5, 0.0), sy * 0.10, 0)), 0.05, 0.36, seed + i * 9 + j, grey=rnd.uniform(0.5, 0.8), roll=roll, bevel=0.012)
    for i in (2, 5, 8):
        a, b = ribs[(i, -1)], ribs[(i, 1)]
        if len(a) > 6 and len(b) > 6:
            beam(p, a[6], b[6], 0.2, 0.22, seed + 80 + i, grey=0.6)
    move_since(p, start, at_m(0, 0, -0.7, 0.0, 0.05, 0.38))
    sand_mound(p, (0, 0.5, -0.25), (length * 0.52, beam_w * 0.6, 0.45), seed)
    for k in range(5):
        a = rnd.uniform(0, 6.28)
        chunk(p, (rnd.uniform(-0.45, 0.45) * length, rnd.uniform(-2.2, 2.2), 0.1), (0.45, 0.35, 0.25), seed + k, 'shore', pts=10, sub=0, turn=a)
    p.export()


def wreck_mast(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    a, b = Vector((-3.6, 0, 0.18)), Vector((3.4, 0.5, 2.5))
    log(p, a, b, 0.26, 0.16, seed, sides=9, grey=0.55, segs=6, wob=0.1, foot=0.4)
    d = (b - a).normalized()
    for k in range(5):                                               # splintered end
        o = Vector((0, rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12)))
        log(p, b - d * 0.1 + o, b + d * rnd.uniform(0.3, 0.8) + o * 1.6, 0.05, 0.01, seed + k, sides=4, grey=0.4, wob=0.0)
    c = a.lerp(b, 0.62)
    log(p, c + Vector((0.1, -2.3, -0.5)), c + Vector((-0.1, 2.0, 0.6)), 0.10, 0.07, seed + 9, sides=7, grey=0.5)
    lash(p, c - d * 0.1, 0.22, 4, 0.03, axis=d)

    def pos(u, v):
        top = (c + Vector((0.1, -2.3, -0.5))).lerp(c + Vector((-0.1, 2.0, 0.6)), u)
        fall = 1.9 * (0.55 + 0.45 * abs(math.sin(u * 7.0 + 1.0)))
        return Vector((top.x - 0.5 * v + 0.15 * math.sin(u * 9.0) * v, top.y, max(0.03, top.z - fall * v) + 0.03 * math.sin(u * 30.0) * v))
    uvsheet(p, pos, lambda u, v, nrm: lerp(lerp(mul(CANVAS, 0.5), CANVAS, clamp01(0.4 + 0.6 * abs(nrm.x))), (0.36, 0.34, 0.26), clamp01(v * 1.1 - 0.2 + 0.3 * math.sin(u * 13.0))), 16, 8)
    rope(p, c + Vector((0.1, -2.3, -0.5)), (0.4, -3.2, 0.03), 0.025, sag=0.2)
    rope(p, b - d * 1.0, (2.0, 2.4, 0.03), 0.025, sag=0.3)
    stones(p, (3.0, 0.5, 0), 0.9, 4, seed, size=(0.3, 0.6), ring=False)
    cask(p, at_m(-1.2, 1.2, 0.26, 0.5, 1.5708), 0.9, seed + 3)
    sand_mound(p, (-2.6, 0.1, -0.1), (1.6, 1.0, 0.3), seed)
    p.export()


def uvsheet(p, pos, col, nu, nv):
    vs = [[p.bm.verts.new(pos(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = p.bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            f.smooth = True
            f.normal_update()
            for loop, (uu, vv) in zip(f.loops, ((i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv))):
                loop[p.col] = lin(col(uu, vv, f.normal))


def chest_geo(p, m, seed, L=1.0, W=0.62, H=0.42):
    """Closed sea chest (the full version with a working lid lives in a_props.py)."""
    R = W / 2
    iron = metal(rust=0.4)
    for k in range(3):
        zc = H * (k + 0.5) / 3
        for sgn in (-1, 1):
            board(p, m @ Matrix.Translation((0, sgn * (W / 2 - 0.02), zc)), (L, 0.04, H / 3 - 0.008), seed + k + sgn * 5, 0.2)
            board(p, m @ Matrix.Translation((sgn * (L / 2 - 0.02), 0, zc)), (0.04, W - 0.08, H / 3 - 0.008), seed + 20 + k + sgn * 5, 0.2)
    n = 7
    for k in range(n):
        a = math.pi * (k + 0.5) / n
        mm = m @ Matrix.Translation((0, math.cos(a) * (R - 0.02), H + math.sin(a) * (R - 0.02) * 0.72)) @ Matrix.Rotation(math.atan2(math.sin(a) * 0.72, math.cos(a)) - math.pi / 2, 4, 'X')
        board(p, mm, (L, 2 * R * math.sin(math.pi / (2 * n)) * 1.06, 0.035), seed + 50 + k, 0.2)
        for sx in (-0.36, 0.36):
            ibox(p, mm @ Matrix.Translation((sx * L, 0, 0.022)), (0.075, 2 * R * math.sin(math.pi / (2 * n)) * 1.1, 0.014), iron)
    tint = lerp(wood_tint(seed + 60), WOOD_DARK, 0.2)
    for sgn in (-1, 1):
        ring = [m @ Vector((sgn * (L / 2 - 0.02), math.cos(a) * (R - 0.02), H + math.sin(a) * (R - 0.02) * 0.72)) for a in (math.pi * k / 10 for k in range(11))]
        fan(p, ring, m @ Vector((sgn * (L / 2 - 0.02), 0, H)), m.to_3x3() @ Vector((sgn, 0, 0)), tint)
        for sy in (-1, 1):
            ibox(p, m @ Matrix.Translation((sgn * 0.36 * L, sy * (W / 2 + 0.003), H / 2)), (0.075, 0.014, H), iron)
    ibox(p, m @ Matrix.Translation((0, -W / 2 - 0.012, H - 0.06)), (0.15, 0.03, 0.17), gilt, 0.012)


def rowboat_wreck(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    start = mark(p)
    L, W, H = 4.6, 1.7, 0.75
    n = 9
    tint = wood_tint(seed)
    for row in range(4):
        s0, s1 = row / 4, (row + 1) / 4
        for sy in (-1, 1):
            for i in range(n - 1):
                if rnd.random() < (0.10 if sy < 0 else 0.45) + 0.1 * row:
                    continue
                pts = []
                for t, s in ((i / (n - 1), s0), ((i + 1) / (n - 1), s0), ((i + 1) / (n - 1), s1), (i / (n - 1), s1)):
                    w = W / 2 * (1.0 - abs(2 * t - 1) ** 2.2)
                    pts.append(Vector((-L / 2 + L * t, sy * w * s ** 0.5, H * s ** 1.4 * (1 + 0.3 * (2 * t - 1) ** 2))))
                c = lerp(lerp(tint, WEATHER, 0.6), WOOD_DARK, 0.3 * rnd.random())
                fquad(p, pts if sy > 0 else pts[::-1], lerp(c, EDGE_LIT, 0.2))
                fquad(p, pts[::-1] if sy > 0 else pts, mul(c, 0.7))
    for i in range(1, n - 1, 2):
        t = i / (n - 1)
        w = W / 2 * (1.0 - abs(2 * t - 1) ** 2.2)
        for sy in (-1, 1):
            pipe(p, [Vector((-L / 2 + L * t, sy * w * (j / 5) ** 0.5 * 0.97, H * (j / 5) ** 1.4 * (1 + 0.3 * (2 * t - 1) ** 2) + 0.02)) for j in range(6)], 0.035,
                 shade(lerp(tint, WOOD_DARK, 0.4)), sides=4, up=Vector((1, 0, 0)), smooth=False)
    beam(p, (-L / 2, 0, 0), (L / 2, 0, 0), 0.10, 0.10, seed + 5, grey=0.6)
    for x in (-0.9, 0.6):
        board(p, Matrix.Translation((x, 0, H * 0.62)), (0.28, W * 0.86, 0.04), seed + 8, 0.6)
    move_since(p, start, at_m(0, 0, 0.05, 0.0, 0.0, 2.2))
    log(p, (-1.2, -1.1, 0.05), (1.3, -1.5, 0.08), 0.03, 0.025, seed + 20, sides=6, grey=0.5)
    board(p, at_m(1.55, -1.54, 0.08, -0.13), (0.5, 0.16, 0.025), seed + 21, 0.5)
    sand_mound(p, (0, 0.2, -0.15), (2.4, 1.3, 0.3), seed)
    p.export()


# ------------------------------------------------------------------ ruins and idols
def column_geo(p, m, h, r, seed, moss=0.4, broken=0.0):
    paint0 = rock_paint('ruin', seed, 0.0, h, moss)
    mi = m.inverted()
    paint = lambda co, nrm: paint0(mi @ co, nrm)
    prof = [(r * 1.5, 0.0), (r * 1.5, 0.16), (r * 1.25, 0.20), (r * 1.25, 0.30), (r * 1.02, 0.36)]
    top = h * (1.0 - broken)
    prof += [(r * (1.0 - 0.10 * z / h), z) for z in (0.36 + (top - 0.36) * k / 5 for k in range(1, 6))]
    if broken:
        prof += [(r * 0.5, top + 0.12), (0.004, top + 0.05)]
    else:
        prof += [(r * 1.2, h + 0.05), (r * 1.25, h + 0.16), (r * 1.5, h + 0.2), (r * 1.5, h + 0.36), (0.004, h + 0.36)]
    lathe(p, prof, paint, sides=10, m=m, smooth=False, cap=False)
    disc(p, (0, 0, 0), r * 1.5, (0.2, 0.2, 0.2), 10, m, down=True)


def ruin_pillar(name, seed, h=4.2, r=0.34, broken=0.0, fallen=False):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    column_geo(p, at_m(0, 0, -0.05, 0.0, rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04)), h, r, seed, broken=broken)
    if fallen or broken:
        for k in range(3 if broken else 2):
            L = rnd.uniform(0.5, 1.1)
            m = at_m(0.9 + 0.95 * k, rnd.uniform(-0.5, 0.5), r * 0.92, rnd.uniform(-0.5, 0.5), 1.5708)
            paint0 = rock_paint('ruin', seed + k, 0.0, 1.0, 0.5)
            lathe(p, [(0.004, 0.0), (r * 0.96, 0.0), (r * 0.94, L), (0.004, L - 0.05)], lambda co, nrm, paint0=paint0: paint0(Vector((co.x, co.y, co.z * 1.5)), nrm), sides=10, m=m, smooth=False, cap=False)
    stones(p, (0, 0, 0), 0.75, 5, seed, 'ruin', moss=0.3, size=(0.12, 0.26))
    p.export()


def ruin_arch(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for sx in (-1, 1):
        column_geo(p, at_m(sx * 1.6, 0, -0.05), 3.6, 0.36, seed + sx)
    zr = (0.0, 5.0)
    for k in range(5):
        chunk(p, (-1.7 + 0.85 * k, rnd.uniform(-0.04, 0.04), 4.22 + (0.10 if k == 2 else 0.0)), (0.46, 0.44, 0.30 + (0.10 if k == 2 else 0.0)), seed + 10 + k, 'ruin', pts=24, boxy=1.0, bevel=0.22,
              sub=1, zrange=zr, moss=0.5, turn=rnd.uniform(-0.05, 0.05))
    chunk(p, (2.3, 0.8, 0.22), (0.5, 0.42, 0.3), seed + 30, 'ruin', pts=24, boxy=1.0, bevel=0.22, sub=1, zrange=zr, moss=0.4, turn=0.6, tilt=(0.2, 0.1))
    for k in range(4):                                               # the Brinewake star cut into the keystone
        a = math.pi / 2 * k
        fquad(p, [Vector((0, -0.455, 4.32)), Vector((math.cos(a - 0.5) * 0.06, -0.455, 4.32 + math.sin(a - 0.5) * 0.06)), Vector((math.cos(a) * 0.22, -0.455, 4.32 + math.sin(a) * 0.22)),
                  Vector((math.cos(a + 0.5) * 0.06, -0.455, 4.32 + math.sin(a + 0.5) * 0.06))], GOLD_HI)
    p.export()


def ruin_wall(name, seed, length=6.0, height=3.0):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    bw, bh = 0.95, 0.5
    rows = int(height / bh)
    zr = (0.0, height)
    for r_ in range(rows):
        cut = (r_ / rows) ** 1.6 * length * 0.75 * rnd.uniform(0.7, 1.1)
        x = -length / 2 + (bw / 2 if r_ % 2 else 0.0)
        k = 0
        while x < length / 2 - cut:
            if rnd.random() > 0.05:
                ibox(p, at_m(x + rnd.uniform(-0.03, 0.03), rnd.uniform(-0.05, 0.05), bh * (r_ + 0.5), rnd.uniform(-0.04, 0.04), rnd.uniform(-0.02, 0.02)),
                     (bw * rnd.uniform(0.93, 0.99), 0.72 * rnd.uniform(0.9, 1.06), bh * 0.96), rock_paint('ruin', seed + r_ * 17 + k, 0.0, height, 0.25 + 0.6 * (r_ / rows)), 0.06)
            x += bw
            k += 1
    for k in range(6):
        chunk(p, (rnd.uniform(0.0, length / 2 + 0.8), rnd.uniform(-1.3, 1.3), 0.2), (0.45, 0.34, 0.25), seed + 300 + k, 'ruin', pts=24, boxy=1.0, bevel=0.2, sub=0, zrange=zr, moss=0.4,
              turn=rnd.uniform(0, 3), tilt=(rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4)))
    p.export()


def idol(name, seed, h=3.4, pal='ruin'):
    """A weathered stone head: heavy brow, long nose, deep eyes with gold set in them."""
    if not want(name):
        return
    p = Prop(name)
    zr = (0.0, h)
    w = h * 0.30
    chunk(p, (0, 0, h * 0.46), (w, w * 0.92, h * 0.56), seed, pal, pts=26, boxy=0.92, bevel=0.2, sub=2, zrange=zr, moss=0.6, taper=0.85, tilt=(0.06, 0.03))
    chunk(p, (0, -w * 0.80, h * 0.70), (w * 0.98, w * 0.34, h * 0.07), seed + 1, pal, pts=20, boxy=1.0, bevel=0.3, sub=1, zrange=zr, moss=0.5)
    chunk(p, (0, -w * 0.96, h * 0.50), (w * 0.20, w * 0.26, h * 0.17), seed + 2, pal, pts=18, boxy=0.9, bevel=0.3, sub=1, zrange=zr, taper=0.6)
    chunk(p, (0, -w * 0.84, h * 0.24), (w * 0.52, w * 0.24, h * 0.045), seed + 3, pal, pts=18, boxy=1.0, bevel=0.3, sub=1, zrange=zr)
    for sx in (-1, 1):
        ibox(p, Matrix.Translation((sx * w * 0.45, -w * 0.86, h * 0.60)), (w * 0.34, w * 0.12, h * 0.07), (0.05, 0.05, 0.07), 0.02)
        p.blob((sx * w * 0.45, -w * 0.90, h * 0.60), (w * 0.09, w * 0.05, w * 0.09), gilt, 1, 0.0, 2, smooth=True)
        chunk(p, (sx * w * 1.02, 0.0, h * 0.50), (w * 0.14, w * 0.30, h * 0.20), seed + 5 + sx, pal, pts=18, boxy=1.0, bevel=0.3, sub=1, zrange=zr, moss=0.3)
    ibox(p, Matrix.Translation((0, -w * 0.93, h * 0.165)), (w * 0.8, w * 0.1, h * 0.022), (0.06, 0.06, 0.08))
    stones(p, (0, 0, 0), w * 1.5, 7, seed, pal, moss=0.5, size=(0.15, 0.35))
    p.export()


def totem(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    log(p, (0, 0, -0.3), (0.04, 0.02, 4.4), 0.30, 0.26, seed, sides=10, foot=0.5, segs=6, wob=0.05)
    paints = (RED, TEAL, OCHRE, (0.92, 0.88, 0.76))
    for k in range(3):
        z = 0.9 + 1.15 * k
        tint = paints[k % 4]
        board(p, Matrix.Translation((0, -0.29, z + 0.34)), (0.66, 0.10, 0.12), seed + k, 0.1, bevel=0.03)
        ibox(p, Matrix.Translation((0, -0.31, z + 0.06)), (0.13, 0.14, 0.40), shade(tint, 0.6), 0.03)
        for sx in (-1, 1):
            ibox(p, Matrix.Translation((sx * 0.16, -0.30, z + 0.18)), (0.13, 0.06, 0.09), (0.06, 0.05, 0.05), 0.015)
            p.blob((sx * 0.16, -0.325, z + 0.18), (0.035, 0.02, 0.035), const(paints[(k + 1) % 4]), 1, 0.0, 1, smooth=True)
            board(p, Matrix.Translation((sx * 0.5, -0.05, z + 0.25)) @ Matrix.Rotation(sx * 0.25, 4, 'Y'), (0.5, 0.05, 0.26), seed + 10 + k, 0.2)
        ibox(p, Matrix.Translation((0, -0.30, z - 0.20)), (0.36, 0.05, 0.07), (0.06, 0.05, 0.05), 0.01)
        for j in range(5):
            ibox(p, Matrix.Translation((-0.13 + 0.065 * j, -0.33, z - 0.20)), (0.04, 0.02, 0.06), (0.95, 0.92, 0.80))
        lathe(p, [(0.30, z - 0.42), (0.33, z - 0.40), (0.30, z - 0.38)], shade(tint, 0.6), sides=10, smooth=False, cap=False)
    stones(p, (0, 0, 0), 0.5, 7, seed)
    p.export()


# ------------------------------------------------------------------ walkways and structures
def bridge_rope(name, seed, span=8.0, width=1.5, sag=0.7):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)

    def deck(t):
        return -sag * math.sin(math.pi * t)
    for sx in (-1, 1):
        x = sx * span / 2
        for sy in (-1, 1):
            log(p, (x + sx * 0.25, sy * (width / 2 + 0.12), -0.6), (x + sx * 0.2, sy * (width / 2 + 0.10), 1.35), 0.11, 0.09, seed + sx + sy * 2, sides=8, foot=0.3, point=0.12)
            lash(p, (x + sx * 0.2, sy * (width / 2 + 0.10), 1.02), 0.10, 3, 0.022)
            lash(p, (x + sx * 0.22, sy * (width / 2 + 0.10), 0.0), 0.11, 3, 0.022)
    n = 24
    for sy in (-1, 1):
        y = sy * (width / 2 + 0.10)
        lower = [Vector((-span / 2 - 0.2 + (span + 0.4) * k / n, y * 0.92, deck(k / n) + 0.02)) for k in range(n + 1)]
        upper = [Vector((-span / 2 - 0.2 + (span + 0.4) * k / n, y, deck(k / n) * 0.8 + 1.08)) for k in range(n + 1)]
        pipe(p, lower, 0.035, rope_paint(), sides=5, up=Vector((0, 1, 0)))
        pipe(p, upper, 0.03, rope_paint(), sides=5, up=Vector((0, 1, 0)))
        for k in range(1, n, 2):
            pipe(p, [lower[k], upper[k]], 0.014, rope_paint(), sides=4)
    k = 0
    x = -span / 2 + 0.1
    while x < span / 2 - 0.1:
        w = rnd.uniform(0.20, 0.30)
        t = (x + span / 2) / span
        if rnd.random() > 0.07:
            slope = -sag * math.pi * math.cos(math.pi * t) / span
            board(p, at_m(x + w / 2, rnd.uniform(-0.04, 0.04), deck(t) + 0.06, rnd.uniform(-0.04, 0.04), -math.atan(slope)), (w * 0.9, width * rnd.uniform(0.94, 1.04), 0.045), seed + 30 + k,
                  rnd.uniform(0.35, 0.65))
        x += w
        k += 1
    p.export()


def walkway(name, seed, length=6.0, width=2.2, height=1.6, rail=True):
    """A dock or boardwalk section on piles. Deck top at z = height, runs along x."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for x in (-length / 2 + 0.35, length / 2 - 0.35):
        for sy in (-1, 1):
            log(p, (x, sy * (width / 2 - 0.12), -1.5), (x + rnd.uniform(-0.04, 0.04), sy * (width / 2 - 0.12), height + (1.1 if rail and sy > 0 else 0.25)), 0.13, 0.11, seed + int(x * 3) + sy,
                sides=8, foot=1.9, segs=5)
        beam(p, (x, -width / 2 - 0.15, height - 0.2), (x, width / 2 + 0.15, height - 0.2), 0.14, 0.16, seed + 9, grey=0.5)
        beam(p, (x, -width / 2 + 0.1, -0.3), (x, width / 2 - 0.1, height - 0.45), 0.07, 0.10, seed + 10, grey=0.55)
    for sy in (-1, 0, 1):
        beam(p, (-length / 2, sy * (width / 2 - 0.2), height - 0.08), (length / 2, sy * (width / 2 - 0.2), height - 0.08), 0.10, 0.12, seed + 12 + sy, grey=0.5)
    x = -length / 2
    k = 0
    while x < length / 2 - 0.05:
        w = min(rnd.uniform(0.22, 0.32), length / 2 - x)
        if rnd.random() > 0.03:
            board(p, at_m(x + w / 2, rnd.uniform(-0.03, 0.03), height + 0.005 + rnd.uniform(0, 0.012), rnd.uniform(-0.02, 0.02)), (w - 0.014, width + rnd.uniform(-0.06, 0.10), 0.05), seed + 40 + k,
                  rnd.uniform(0.35, 0.65))
        x += w
        k += 1
    if rail:
        y = width / 2 - 0.12
        rope(p, (-length / 2 + 0.35, y, height + 0.95), (length / 2 - 0.35, y, height + 0.95), 0.028, sag=0.22)
        rope(p, (-length / 2 + 0.35, y, height + 0.50), (length / 2 - 0.35, y, height + 0.50), 0.028, sag=0.18)
        for x in (-length / 2 + 0.35, length / 2 - 0.35):
            lash(p, (x, y, height + 0.88), 0.11, 3, 0.02)
    p.export()


def stairs_wood(name, seed, rise=2.4, run=3.2, width=1.6):
    if not want(name):
        return
    p = Prop(name)
    n = int(round(rise / 0.2))
    for sy in (-1, 1):
        beam(p, (0, sy * (width / 2 - 0.04), 0.0), (run, sy * (width / 2 - 0.04), rise), 0.07, 0.26, seed + sy, grey=0.45)
        log(p, (run - 0.1, sy * (width / 2 + 0.06), -0.2), (run - 0.1, sy * (width / 2 + 0.06), rise + 1.0), 0.08, 0.07, seed + 4 + sy, sides=7, foot=0.4)
        log(p, (0.15, sy * (width / 2 + 0.06), -0.2), (0.15, sy * (width / 2 + 0.06), 1.05), 0.08, 0.07, seed + 6 + sy, sides=7, foot=0.3)
        rope(p, (0.15, sy * (width / 2 + 0.06), 0.95), (run - 0.1, sy * (width / 2 + 0.06), rise + 0.92), 0.026, sag=0.15)
    for k in range(n):
        t = (k + 0.5) / n
        board(p, Matrix.Translation((run * t, 0, rise * (k + 1) / n)), (run / n + 0.06, width, 0.05), seed + 10 + k, 0.45)
    p.export()


def platform(name, seed, size=3.2, height=4.2):
    """A lookout stage on four braced legs with a ladder and a railing."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    h2 = size / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            log(p, (sx * (h2 + 0.25), sy * (h2 + 0.25), -0.3), (sx * (h2 - 0.12), sy * (h2 - 0.12), height + 1.05), 0.13, 0.10, seed + sx + sy * 2, sides=8, foot=0.5, segs=5)
        beam(p, (sx * (h2 - 0.1), -h2, height - 0.14), (sx * (h2 - 0.1), h2, height - 0.14), 0.12, 0.16, seed + 8 + sx, grey=0.45, over=0.3)
        beam(p, (sx * (h2 + 0.05), -h2 - 0.1, 0.6), (sx * (h2 - 0.05), h2 - 0.2, height - 0.5), 0.07, 0.10, seed + 12 + sx, grey=0.5)
        beam(p, (-h2 - 0.1, sx * (h2 + 0.05), height - 0.5), (h2 - 0.2, sx * (h2 - 0.05), 0.6), 0.07, 0.10, seed + 14 + sx, grey=0.5)
    k = 0
    y = -h2 - 0.1
    while y < h2 + 0.1:
        w = rnd.uniform(0.22, 0.3)
        board(p, at_m(0, y + w / 2, height, rnd.uniform(-0.015, 0.015)), (size + 0.3 + rnd.uniform(-0.08, 0.08), w - 0.014, 0.05), seed + 20 + k, rnd.uniform(0.35, 0.6))
        y += w
        k += 1
    for sy in (-1, 1):
        beam(p, (-h2 + 0.1, sy * (h2 - 0.12), height + 0.95), (h2 - 0.1, sy * (h2 - 0.12), height + 0.95), 0.07, 0.09, seed + 30 + sy, grey=0.45)
    beam(p, (h2 - 0.12, -h2 + 0.1, height + 0.95), (h2 - 0.12, h2 - 0.1, height + 0.95), 0.07, 0.09, seed + 33, grey=0.45)
    for sgn in (-1, 1):
        log(p, (-h2 - 0.75, sgn * 0.3, 0), (-h2 - 0.05, sgn * 0.27, height + 0.6), 0.05, 0.045, seed + 40 + sgn, sides=6, grey=0.4)
    n = int(height / 0.36)
    for j in range(n):
        t = (j + 0.8) / (n + 0.8)
        log(p, (-h2 - 0.75 + 0.70 * t, -0.36, height * t), (-h2 - 0.75 + 0.70 * t, 0.36, height * t), 0.03, 0.03, seed + 50 + j, sides=6, wob=0.0, grey=0.4)
    lamp(p, (h2 - 0.12, h2 - 0.12, height + 1.05 + 0.02), 1.1, hang=False)
    case(p, at_m(0.6, -0.5, height + 0.03, 0.3), (0.6, 0.6, 0.5), seed + 60)
    p.export()


def crane(name, seed):
    if not want(name):
        return
    p = Prop(name)
    log(p, (0, 0, -0.3), (0, 0, 5.0), 0.20, 0.16, seed, sides=9, foot=0.5, segs=5)
    for k in range(4):
        a = math.pi / 4 + math.pi * k / 2
        beam(p, (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.08), (math.cos(a) * 0.15, math.sin(a) * 0.15, 1.9), 0.12, 0.12, seed + k, grey=0.4)
        beam(p, (math.cos(a) * 1.7, math.sin(a) * 1.7, 0.08), (math.cos(a) * -0.2, math.sin(a) * -0.2, 0.08), 0.14, 0.14, seed + 5 + k, grey=0.45)
    a, b = Vector((-0.9, 0, 4.1)), Vector((3.4, 0, 5.6))
    beam(p, a, b, 0.16, 0.18, seed + 10, grey=0.4)
    beam(p, (0.1, 0, 3.0), (1.7, 0, 4.9), 0.11, 0.12, seed + 11, grey=0.4)
    lash(p, (0, 0, 4.25), 0.19, 4, 0.03)
    rope(p, (0.0, 0, 5.0), b, 0.024)
    lathe(p, [(0.004, -0.05), (0.14, -0.05), (0.16, 0.0), (0.14, 0.05), (0.004, 0.05)], shade(WOOD_LIGHT, 0.5), sides=10, m=zto(b + Vector((-0.15, 0, -0.22)), (0, 1, 0)), smooth=False, cap=False)
    hook = b + Vector((-0.15, 0, -1.9))
    rope(p, b + Vector((-0.15, 0, -0.3)), hook, 0.024)
    rope(p, b + Vector((-0.3, 0, -0.22)), (-0.6, 0.2, 1.3), 0.02, sag=0.3)
    pipe(p, [hook, hook + Vector((0, 0, -0.14)), hook + Vector((0.07, 0, -0.22)), hook + Vector((0.12, 0, -0.15))], 0.022, metal(), sides=5, up=Vector((0, 1, 0)))
    net_c = hook + Vector((0, 0, -0.75))
    case(p, at_m(net_c.x, net_c.y, net_c.z - 0.3, 0.5, 0.06), (0.75, 0.75, 0.6), seed + 20)
    for k in range(4):
        q = math.pi / 4 + math.pi * k / 2
        rope(p, hook + Vector((0, 0, -0.2)), net_c + Vector((math.cos(q + 0.5) * 0.52, math.sin(q + 0.5) * 0.52, -0.28)), 0.014)
    lathe(p, [(0.004, -0.12), (0.2, -0.12), (0.2, 0.12), (0.004, 0.12)], shade(WOOD_LIGHT, 0.5), sides=10, m=zto((-0.22, 0.0, 1.3), (0, 1, 0)), smooth=False, cap=False)
    pipe(p, [Vector((-0.22, 0.14, 1.3)), Vector((-0.22, 0.26, 1.3)), Vector((-0.22, 0.26, 1.05)), Vector((-0.22, 0.44, 1.05))], 0.02, metal(), sides=5, up=Vector((1, 0, 0)))
    p.export()


def weapon_rack(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for sgn in (-1, 1):
        log(p, (sgn * 0.85, 0.12, 0), (sgn * 0.82, -0.12, 1.5), 0.05, 0.045, seed + sgn, sides=6, grey=0.35)
        beam(p, (sgn * 0.85, -0.28, 0.03), (sgn * 0.85, 0.34, 0.03), 0.08, 0.07, seed + 3 + sgn, grey=0.4)
    for z, y in ((0.30, 0.07), (1.25, -0.08)):
        beam(p, (-0.95, y, z), (0.95, y, z), 0.07, 0.09, seed + 6, grey=0.35)
    for k in range(4):
        x = -0.6 + 0.4 * k
        cutlass(p, at_m(x, -0.06, 0.38, 1.5708, 0.0, 0.16), 1.1)
    for k in range(2):                                               # muskets
        x = 0.72 - 1.44 * k
        m = at_m(x * 0.55, 0.11, 0.05, 0.0, 0.0, 0.17)
        ibox(p, m @ Matrix.Translation((0, 0, 0.30)), (0.05, 0.07, 0.6), shade(lerp(WOOD_DARK, WOOD_LIGHT, 0.4), 0.6), 0.015)
        lathe(p, [(0.016, 0.5), (0.014, 1.45)], metal(rust=0.2), sides=6, m=m)
        ibox(p, m @ Matrix.Translation((0, -0.04, 0.55)), (0.02, 0.05, 0.08), gilt, 0.006)
    p.export()


def bell_post(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for sgn in (-1, 1):
        log(p, (sgn * 0.5, 0, -0.2), (sgn * 0.46, 0, 2.3), 0.09, 0.075, seed + sgn, sides=8, foot=0.4)
    beam(p, (-0.72, 0, 2.2), (0.72, 0, 2.2), 0.12, 0.13, seed + 3, grey=0.35)
    for sgn in (-1, 1):
        beam(p, (sgn * 0.46, 0, 1.72), (sgn * 0.14, 0, 2.14), 0.07, 0.07, seed + 5 + sgn, grey=0.4)
    brass = lambda co, nrm: lerp((0.42, 0.28, 0.08), (0.98, 0.80, 0.34), clamp01(0.3 + 0.5 * nrm.z + 0.4 * max(0.0, nrm.dot(SUN_DIR)) ** 2))
    lathe(p, [(0.25, 1.52), (0.27, 1.54), (0.24, 1.60), (0.17, 1.74), (0.13, 1.90), (0.10, 1.98), (0.05, 2.02), (0.05, 2.08), (0.004, 2.09)], brass, sides=12)
    disc(p, (0, 0, 1.56), 0.24, (0.16, 0.10, 0.04), 12, down=True)
    p.blob((0, 0, 1.50), (0.045, 0.045, 0.045), brass, 1, 0.0, 1, smooth=True)
    rope(p, (0, 0, 1.50), (0.05, 0, 1.05), 0.014)
    stones(p, (0, 0, 0), 0.62, 6, seed)
    p.export()


def bunting(name, seed, span=8.0, height=3.4):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    tops = []
    for sgn in (-1, 1):
        log(p, (sgn * span / 2, 0, -0.2), (sgn * (span / 2 + 0.1), 0, height), 0.085, 0.06, seed + sgn, sides=7, foot=0.4, point=0.12)
        tops.append(Vector((sgn * (span / 2 + 0.09), 0, height - 0.2)))
        stones(p, (sgn * span / 2, 0, 0), 0.2, 4, seed + sgn)
    n = 26
    line = [tops[0].lerp(tops[1], k / n) + Vector((0, 0, -0.55 * math.sin(math.pi * k / n))) for k in range(n + 1)]
    pipe(p, line, 0.014, rope_paint(), sides=4, up=Vector((0, 1, 0)))
    tints = (RED, CANVAS, TEAL, OCHRE, NAVY)
    for k in range(1, n - 1, 2):
        a, b = line[k], line[k + 1]
        tint = tints[(k // 2) % len(tints)]
        tip = (a + b) / 2 + Vector((0, rnd.uniform(-0.08, 0.08), -0.46))
        fquad(p, [a, b, tip], shade(tint, 0.6))
        fquad(p, [b, a, tip], shade(mul(tint, 0.75), 0.6))
    lamp(p, tuple(line[n // 2] + Vector((0, 0, -0.02))), 1.0)
    p.export()


def spyglass_stand(name, seed):
    if not want(name):
        return
    p = Prop(name)
    top = Vector((0, 0, 1.35))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        log(p, (math.cos(a) * 0.55, math.sin(a) * 0.55, 0), top + Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0)), 0.035, 0.03, seed + k, sides=6, wob=0.0, grey=0.2)
    lathe(p, [(0.07, -0.05), (0.08, 0.0), (0.05, 0.05), (0.03, 0.12)], gilt, at=top, sides=8)
    m = Matrix.Translation(top + Vector((0, 0, 0.17))) @ Matrix.Rotation(0.4, 4, 'Z') @ Matrix.Rotation(1.35, 4, 'Y')
    brass = lambda co, nrm: lerp((0.42, 0.28, 0.08), (0.98, 0.80, 0.34), clamp01(0.3 + 0.6 * nrm.z))
    lathe(p, [(0.065, -0.50), (0.07, -0.48), (0.065, -0.46), (0.06, -0.10), (0.065, -0.08), (0.05, -0.08), (0.05, 0.22), (0.055, 0.24), (0.04, 0.24), (0.04, 0.5), (0.05, 0.52), (0.03, 0.56)], brass,
          sides=10, m=m)
    disc(p, (0, 0, -0.50), 0.058, (0.55, 0.80, 0.90), 10, m, down=True)
    p.export()


def bottles(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    tints = ((0.12, 0.32, 0.18), (0.42, 0.26, 0.10), (0.10, 0.24, 0.34))
    for k in range(6):
        a, d = rnd.uniform(0, 6.28), 0.28 * math.sqrt(rnd.random())
        if k < 4:
            bottle(p, at_m(math.cos(a) * d, math.sin(a) * d, 0, rnd.uniform(0, 6.28)), rnd.uniform(0.85, 1.15), tints[k % 3])
        else:
            bottle(p, at_m(math.cos(a) * 0.4, math.sin(a) * 0.4, 0.055, rnd.uniform(0, 6.28), 1.5708), 1.0, tints[k % 3])
    tankard(p, at_m(0.34, 0.1, 0, 1.0), 1.0, seed)
    p.export()


def sword_stuck(name, seed):
    if not want(name):
        return
    p = Prop(name)
    cutlass(p, at_m(0, 0, 0.78, 0.3, 0.0, math.pi + 0.14), 1.15)
    tricorn(p, at_m(0.01, 0.02, 0.86, 0.8, 0.3, 0.1), 0.95, (0.16, 0.12, 0.10))
    sand_mound(p, (0, 0, -0.06), (0.45, 0.45, 0.14), seed)
    p.export()


def dock_set():
    walkway("SM_BW_Walkway_6m", 3)
    walkway("SM_BW_Walkway_6m_Plain", 5, rail=False)
    walkway("SM_BW_Walkway_3m", 7, 3.0)
    walkway("SM_BW_Pier_Wide", 9, 6.0, 4.4)


skeleton_sit("SM_BW_Skeleton_Captain", 3)
skeleton_sit("SM_BW_Skeleton_Sit", 7, captain=False)
skeleton_lie("SM_BW_Skeleton_Lie", 4)
skeleton_buried("SM_BW_Skeleton_Buried", 5)
skeleton_chest("SM_BW_Skeleton_Chest", 6)
skull_prop("SM_BW_Skull", 2)
skull_prop("SM_BW_Skull_Moss", 9, 0.7)
skull_pile("SM_BW_Skull_Pile", 3)
skull_pike("SM_BW_Skull_Pike", 4)
skull_pike("SM_BW_Skull_Pikes", 8, 3)
bone_pile("SM_BW_Bone_Pile", 5)
leviathan("SM_BW_Leviathan_Bones", 6)
gibbet("SM_BW_Gibbet", 7)
gibbet("SM_BW_Gibbet_Empty", 11, body=False)
cage("SM_BW_Cage", 3)
gravestone("SM_BW_Grave_Stone", 4)
gravestone("SM_BW_Grave_Stone_B", 14)
gravestone("SM_BW_Grave_Cross", 5, 'cross')
wreck_hull("SM_BW_Wreck_Hull", 6)
wreck_hull("SM_BW_Wreck_Hull_Small", 12, 8.0, 3.2, 2.2, 0.75)
wreck_mast("SM_BW_Wreck_Mast", 7)
rowboat_wreck("SM_BW_Wreck_Rowboat", 8)
ruin_pillar("SM_BW_Ruin_Pillar", 3)
ruin_pillar("SM_BW_Ruin_Pillar_Broken", 6, broken=0.55)
ruin_pillar("SM_BW_Ruin_Pillar_Stub", 9, 4.2, 0.34, broken=0.8)
ruin_arch("SM_BW_Ruin_Arch", 4)
ruin_wall("SM_BW_Ruin_Wall", 5)
ruin_wall("SM_BW_Ruin_Wall_Low", 8, 4.0, 1.5)
idol("SM_BW_Idol_Head", 6)
idol("SM_BW_Idol_Head_Ember", 12, 2.6, 'ember')
totem("SM_BW_Totem", 7)
bridge_rope("SM_BW_Bridge_Rope", 3)
bridge_rope("SM_BW_Bridge_Rope_Long", 6, 14.0, 1.5, 1.3)
dock_set()
stairs_wood("SM_BW_Stairs_Wood", 4)
platform("SM_BW_Lookout_Platform", 5)
crane("SM_BW_Dock_Crane", 6)
weapon_rack("SM_BW_Weapon_Rack", 7)
bell_post("SM_BW_Bell_Post", 8)
bunting("SM_BW_Bunting", 9)
spyglass_stand("SM_BW_Spyglass_Stand", 10)
bottles("SM_BW_Bottles", 11)
sword_stuck("SM_BW_Sword_Stuck", 12)

result = {'built': BW_BUILT}
