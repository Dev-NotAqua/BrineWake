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
