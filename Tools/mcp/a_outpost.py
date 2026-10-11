# Gullrest outpost buildings, built in the open Blender (run through bl_run.py).
# Real carpentry and real sizes: stone piers, sill beams, corner posts, lapped weatherboards, framed doors (0.95 x 2.05 m)
# and windows, rafters, shingled roofs at 45 degrees, stairs at 0.18 m rise. Front of a building faces -y. Metres.
STONE_A, STONE_B, MOSS_C = (0.66, 0.62, 0.55), (0.42, 0.41, 0.40), (0.34, 0.42, 0.22)
GLOW_LO, GLOW_HI = (1.0, 0.56, 0.16), (1.0, 0.92, 0.56)
OCHRE, BONE, ROPE_C = (0.90, 0.64, 0.20), (0.90, 0.82, 0.62), (0.70, 0.57, 0.36)
CRIMSON, SEA, TEAL = (0.62, 0.13, 0.12), (0.12, 0.30, 0.46), (0.13, 0.42, 0.46)


def lin(c):
    return (clamp01(c[0]), clamp01(c[1]), clamp01(c[2]), 1.0)


def fquad(p, pts, colour, smooth=False):
    f = p.bm.faces.new([p.bm.verts.new(v) for v in pts])
    f.smooth = smooth
    f.normal_update()
    for loop in f.loops:
        loop[p.col] = lin(colour(loop.vert.co, f.normal) if callable(colour) else colour)
    return f


def pipe(p, pts, radii, colour, sides=6, up=Vector((0, 0, 1)), closed=False):
    n = len(pts)
    loops = []
    for i in range(n):
        a = (pts[(i + 1) % n] - pts[(i - 1) % n]) if closed else (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        a.normalize()
        s = a.cross(up)
        if s.length < 1e-4:
            s = a.cross(Vector((1, 0, 0)))
        s.normalize()
        u = s.cross(a)
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        loops.append([p.bm.verts.new(pts[i] + (s * math.cos(q) + u * math.sin(q)) * r) for q in (2 * math.pi * k / sides for k in range(sides))])
    faces = []
    for i in range(n if closed else n - 1):
        A, B = loops[i], loops[(i + 1) % n]
        for k in range(sides):
            faces.append(p.bm.faces.new((A[(k + 1) % sides], A[k], B[k], B[(k + 1) % sides])))
    if not closed:
        faces.append(p.bm.faces.new(list(reversed(loops[-1]))))
        faces.append(p.bm.faces.new(loops[0]))
    for f in faces:
        f.smooth = True
        f.normal_update()
        for loop in f.loops:
            loop[p.col] = lin(colour(loop.vert.co, f.normal) if callable(colour) else colour)


def shade(base, lo=0.55):
    dark = tuple(c * lo for c in base)
    return lambda co, nrm: lerp(dark, base, clamp01(nrm.z * 0.5 + 0.62))


def rope(p, a, b, r=0.022, sag=0.0):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, k / 6) + Vector((0, 0, -sag * math.sin(math.pi * k / 6))) for k in range(7)] if sag else [a, b]
    pipe(p, pts, r, shade(ROPE_C), sides=5)


def beam(p, a, b, w, h, seed, grey=0.3, bevel=0.012):
    """Squared timber from a to b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    m = Matrix.Translation((a + b) / 2) @ Vector((1, 0, 0)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    plank(p, (0, 0, 0), (d.length, w, h), seed, rot=m, grey=grey, bevel=bevel)


def stone(p, c, size, seed):
    base = lerp(STONE_B, STONE_A, random.Random(seed).uniform(0, 1))
    p.box(c, size, lambda co, nrm: lerp(lerp(base, MOSS_C, 0.4 * clamp01(0.5 - co.z)), lerp(base, (1.0, 0.98, 0.92), 0.2), clamp01(nrm.z)), bevel=min(size) * 0.2)


def keg(p, x, y, z, s, seed):
    tint = wood_tint(seed)
    rings = [(Vector((x, y, z + s * 0.9 * k / 6)), s * (0.30 + 0.07 * math.sin(math.pi * k / 6)), Vector((0, 0, 1))) for k in range(7)]
    p.tube(rings, lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.5), tint, clamp01(0.3 + (co.z - z) / s) * (0.8 + 0.2 * math.cos(math.atan2(co.y - y, co.x - x) * 10))), sides=12, smooth=False)
    for k in (1, 5):
        zz = z + s * 0.9 * k / 6
        rr = s * (0.30 + 0.07 * math.sin(math.pi * k / 6)) + 0.012
        p.tube([(Vector((x, y, zz - 0.03)), rr, Vector((0, 0, 1))), (Vector((x, y, zz + 0.03)), rr, Vector((0, 0, 1)))],
               lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(nrm.z + 0.4)), sides=12, cap=False, smooth=False)


def crate(p, x, y, z, s, seed):
    plank(p, (x, y, z + s / 2), (s, s, s), seed, grey=0.25)
    for sx in (-1, 1):
        plank(p, (x + sx * (s / 2 - 0.04), y, z + s / 2), (0.07, s + 0.03, s + 0.03), seed + 1, grey=0.15)


def clad(p, a, b, z0, z1, seed, holes=(), gable=0.0, tone=0.45):
    """Lapped horizontal weatherboards from plan point a to b (outside is on the right of a->b), with openings and an
    optional triangular gable of the given height on top."""
    a, b = Vector((a[0], a[1])), Vector((b[0], b[1]))
    d = b - a
    length = d.length
    d.normalize()
    out = Vector((d.y, -d.x))
    rnd = random.Random(seed)
    bh = 0.20
    yaw = math.atan2(d.y, d.x)
    z = z0
    r = 0
    while z < z1 + gable - 0.03:
        top = min(z + bh, z1 + gable)
        if z >= z1 - 1e-6:
            f = 1.0 - (z + bh / 2 - z1) / gable
            if f < 0.05:
                break
            spans = [(length / 2 * (1 - f), length / 2 * (1 + f))]
        else:
            spans = [(0.0, length)]
        for u0, u1, h0, h1 in holes:
            if h0 < top - 0.02 and h1 > z + 0.02:
                cut = []
                for s0, s1 in spans:
                    if u1 <= s0 or u0 >= s1:
                        cut.append((s0, s1))
                    else:
                        if u0 - s0 > 0.05:
                            cut.append((s0, u0))
                        if s1 - u1 > 0.05:
                            cut.append((u1, s1))
                spans = cut
        for s0, s1 in spans:
            u = s0
            while u < s1 - 0.02:
                e = min(s1, u + rnd.uniform(2.4, 4.4))
                if s1 - e < 0.5:
                    e = s1
                mid = a + d * ((u + e) / 2) + out * 0.02
                m = Matrix.Translation((mid.x, mid.y, (z + top) / 2)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(-0.10, 4, 'X')
                plank(p, (0, 0, 0), (e - u - 0.012, 0.028, top - z + 0.035), seed * 31 + r * 7 + int(u * 10), rot=m, grey=rnd.uniform(tone - 0.15, tone + 0.2), bevel=0.006)
                u = e
        z += bh
        r += 1


def wall_axes(a, b):
    d = Vector((b[0] - a[0], b[1] - a[1], 0)).normalized()
    return Vector((a[0], a[1], 0)), d, Vector((d.y, -d.x, 0))


def window(p, a, b, u, z, w, h, seed, shutters=True, glow=True):
    o, d, out = wall_axes(a, b)
    rnd = random.Random(seed)
    c = o + d * u
    q = [c + d * (-w / 2) + Vector((0, 0, z)), c + d * (w / 2) + Vector((0, 0, z)), c + d * (w / 2) + Vector((0, 0, z + h)), c + d * (-w / 2) + Vector((0, 0, z + h))]
    fquad(p, q, (lambda co, nrm: lerp(GLOW_LO, GLOW_HI, clamp01((co.z - z) / h))) if glow else (0.10, 0.12, 0.16))
    for p0, p1 in ((q[0] - d * 0.07, q[1] + d * 0.07), (q[3] - d * 0.07, q[2] + d * 0.07)):
        beam(p, p0 + out * 0.03, p1 + out * 0.03, 0.08, 0.10, seed, grey=0.12)
    for p0, p1 in ((q[0], q[3]), (q[1], q[2])):
        beam(p, p0 + out * 0.03, p1 + out * 0.03, 0.08, 0.10, seed + 1, grey=0.12)
    beam(p, (q[0] + q[1]) / 2 + out * 0.02, (q[3] + q[2]) / 2 + out * 0.02, 0.035, 0.04, seed + 2, grey=0.1, bevel=0.0)
    beam(p, (q[0] + q[3]) / 2 + out * 0.02, (q[1] + q[2]) / 2 + out * 0.02, 0.035, 0.04, seed + 3, grey=0.1, bevel=0.0)
    beam(p, q[0] - d * 0.12 + out * 0.07 + Vector((0, 0, -0.05)), q[1] + d * 0.12 + out * 0.07 + Vector((0, 0, -0.05)), 0.14, 0.05, seed + 4, grey=0.2)      # sill
    if shutters:
        for sgn in (-1, 1):
            ang = rnd.uniform(0.25, 1.15)
            hinge = c + d * (sgn * (w / 2 + 0.05)) + out * 0.06 + Vector((0, 0, z + h / 2))
            swing = d * (sgn * math.cos(ang)) + out * math.sin(ang)
            beam(p, hinge, hinge + swing * (w / 2), 0.03, h, seed + 5 + sgn, grey=0.35, bevel=0.006)
            for dz in (-h * 0.32, h * 0.32):
                beam(p, hinge + swing * 0.03 + Vector((0, 0, dz)) + out * 0.01, hinge + swing * (w / 2 - 0.03) + Vector((0, 0, dz)) + out * 0.01, 0.06, 0.07, seed + 8, grey=0.15, bevel=0.0)


def door(p, a, b, u, z, w, h, seed, ajar=0.45):
    o, d, out = wall_axes(a, b)
    c = o + d * u
    for sgn in (-1, 1):
        beam(p, c + d * (sgn * (w / 2 + 0.05)) + out * 0.02 + Vector((0, 0, z)), c + d * (sgn * (w / 2 + 0.05)) + out * 0.02 + Vector((0, 0, z + h + 0.1)), 0.10, 0.12, seed + sgn, grey=0.12)
    beam(p, c - d * (w / 2 + 0.16) + out * 0.02 + Vector((0, 0, z + h + 0.07)), c + d * (w / 2 + 0.16) + out * 0.02 + Vector((0, 0, z + h + 0.07)), 0.14, 0.12, seed + 3, grey=0.12)
    hinge = c - d * (w / 2) + out * 0.03
    swing = d * math.cos(ajar) + out * math.sin(ajar)
    yaw = math.atan2(swing.y, swing.x)
    n = 5
    for k in range(n):
        q = hinge + swing * ((k + 0.5) * w / n) + Vector((0, 0, z + h / 2))
        plank(p, (0, 0, 0), (w / n * 0.95, 0.04, h - 0.03), seed + 10 + k, rot=Matrix.Translation(q) @ Matrix.Rotation(yaw, 4, 'Z'), grey=0.3, bevel=0.008)
    side = Vector((swing.y, -swing.x, 0))
    for dz in (0.35, h - 0.35):
        beam(p, hinge + swing * 0.04 + side * 0.035 + Vector((0, 0, z + dz)), hinge + swing * (w - 0.04) + side * 0.035 + Vector((0, 0, z + dz)), 0.03, 0.12, seed + 20, grey=0.15, bevel=0.006)
    pipe(p, [hinge + swing * (w - 0.12) + side * 0.06 + Vector((0, math.cos(t) * 0.0, z + 1.0 + math.sin(t) * 0.05)) + swing * (math.cos(t) * 0.05) for t in (2 * math.pi * k / 8 for k in range(8))],
         0.012, shade(IRON_LIGHT), sides=4, up=side, closed=True)


def floor(p, x0, x1, y0, y1, z, seed):
    rnd = random.Random(seed)
    w = 0.22
    y = y0
    while y < y1 - 0.01:
        yb = min(y1, y + w)
        x = x0
        while x < x1 - 0.01:
            xe = min(x1, x + rnd.uniform(1.8, 3.6))
            tint = lerp((0.55, 0.42, 0.28), (0.78, 0.64, 0.44), rnd.uniform(0, 1))
            fquad(p, [Vector((x + 0.006, y + 0.006, z)), Vector((xe - 0.006, y + 0.006, z)), Vector((xe - 0.006, yb - 0.006, z)), Vector((x + 0.006, yb - 0.006, z))],
                  lambda co, nrm, tint=tint: lerp(tint, (tint[0] * 0.8, tint[1] * 0.78, tint[2] * 0.75), 0.5 + 0.5 * math.sin(co.x * 6 + co.y * 29)))
            x = xe
        y = yb
    fquad(p, [Vector((x0, y1, z - 0.04)), Vector((x1, y1, z - 0.04)), Vector((x1, y0, z - 0.04)), Vector((x0, y0, z - 0.04))], (0.16, 0.11, 0.08))


def stairs(p, foot, head, width, seed):
    """Straight flight from a foot point on the ground to the edge of a landing."""
    foot, head = Vector(foot), Vector(head)
    rise = head.z - foot.z
    n = max(2, int(round(rise / 0.185)))
    run = Vector((head.x - foot.x, head.y - foot.y, 0))
    yaw = math.atan2(run.y, run.x)
    side = Vector((-run.normalized().y, run.normalized().x, 0))
    for k in range(n):
        c = foot + run * ((k + 0.5) / n) + Vector((0, 0, rise * (k + 1) / n - 0.03))
        plank(p, (0, 0, 0), (run.length / n * 1.08, width, 0.05), seed + k, rot=Matrix.Translation(c) @ Matrix.Rotation(yaw, 4, 'Z'), grey=0.35)
    for s in (-1, 1):
        beam(p, foot + side * (s * (width / 2 - 0.04)) + Vector((0, 0, -0.05)), head + side * (s * (width / 2 - 0.04)) + Vector((0, 0, -0.16)), 0.06, 0.24, seed + 30 + s, grey=0.2)


def rail(p, pts, h, seed, mid=True):
    pts = [Vector(q) for q in pts]
    for k, q in enumerate(pts):
        beam(p, q, q + Vector((0, 0, h)), 0.09, 0.09, seed + k, grey=0.2)
    for a, b in zip(pts, pts[1:]):
        beam(p, a + Vector((0, 0, h)), b + Vector((0, 0, h)), 0.10, 0.06, seed + 20, grey=0.15)
        if mid:
            beam(p, a + Vector((0, 0, h * 0.5)), b + Vector((0, 0, h * 0.5)), 0.05, 0.07, seed + 21, grey=0.25, bevel=0.006)


def bunting(p, a, b, n, cols, sag=0.4):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, k / n) + Vector((0, 0, -sag * math.sin(math.pi * k / n))) for k in range(n + 1)]
    pipe(p, pts, 0.012, shade(ROPE_C), sides=4)
    d = (b - a).normalized()
    for k in range(n):
        fquad(p, [pts[k] + d * 0.04, pts[k + 1] - d * 0.04, (pts[k] + pts[k + 1]) / 2 + Vector((0, 0, -0.34))], shade(cols[k % len(cols)], 0.7))


def shingles(p, a, b, drop, out, rows, seed, thatch=False):
    """Roof covering: sun-silvered cedar shingles, or straw-gold palm thatch."""
    global THATCH_A, THATCH_B
    keep = (THATCH_A, THATCH_B)
    THATCH_A, THATCH_B = ((0.58, 0.46, 0.24), (0.86, 0.74, 0.42)) if thatch else ((0.44, 0.37, 0.31), (0.72, 0.64, 0.54))
    roof_side(p, a, b, drop, out, rows, seed, True)
    THATCH_A, THATCH_B = keep


def roof(p, cx, cy, w, d, zt, seed, pitch=45.0, eave=0.45, over=0.40, thatch=False):
    """Gable roof with its ridge along x over a w by d plan whose wall tops are at zt. Returns the ridge height."""
    t = math.tan(math.radians(pitch))
    zr = zt + d / 2 * t
    drop = (d / 2 + eave) * t
    A, B = Vector((cx - w / 2 - over, cy, zr)), Vector((cx + w / 2 + over, cy, zr))
    rows = max(4, int(math.hypot(d / 2 + eave, drop) / 0.30))
    shingles(p, A, B, drop, Vector((0, -(d / 2 + eave), 0)), rows, seed + 1, thatch)
    shingles(p, B, A, drop, Vector((0, d / 2 + eave, 0)), rows, seed + 2, thatch)
    beam(p, A + Vector((0, 0, -0.16)), B + Vector((0, 0, -0.16)), 0.14, 0.18, seed + 3, grey=0.15)
    beam(p, A + Vector((-0.05, 0, 0.09)), B + Vector((0.05, 0, 0.09)), 0.30, 0.05, seed + 4, grey=0.3)
    x = cx - w / 2
    while x <= cx + w / 2 + 0.01:                                    # rafters, tails showing under the eaves
        for sgn in (-1, 1):
            beam(p, (x, cy, zr - 0.13), (x, cy + sgn * (d / 2 + eave - 0.03), zr - 0.13 - (d / 2 + eave - 0.03) * t), 0.07, 0.13, seed + 5, grey=0.2)
        x += 0.9
    for xx in (cx - w / 2 - over + 0.03, cx + w / 2 + over - 0.03):   # barge boards
        for sgn in (-1, 1):
            beam(p, (xx, cy, zr + 0.03), (xx, cy + sgn * (d / 2 + eave), zr + 0.03 - drop), 0.05, 0.22, seed + 6, grey=0.15)
    return zr


def cabin(p, cx, cy, w, d, z0, wall, seed, openings, pitch=45.0, thatch=False, tone=0.45, piers=True):
    """A framed timber building. openings: {'S'|'E'|'N'|'W': [(kind, offset from wall centre, width, sill above floor, height)]}"""
    corners = {'S': ((cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2)), 'E': ((cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2)),
               'N': ((cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)), 'W': ((cx - w / 2, cy + d / 2), (cx - w / 2, cy - d / 2))}
    rise = d / 2 * math.tan(math.radians(pitch))
    for k, (name, (a, b)) in enumerate(corners.items()):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        holes = []
        for kind, off, ow, sill, oh in openings.get(name, []):
            u = length / 2 + off
            holes.append((u - ow / 2, u + ow / 2, z0 + sill, z0 + sill + oh))
            if kind == 'door':
                door(p, a, b, u, z0 + sill, ow, oh, seed + 100 * k + int(off * 10))
            else:
                window(p, a, b, u, z0 + sill, ow, oh, seed + 100 * k + int(off * 10) + 7, shutters=(kind == 'window'))
        clad(p, a, b, z0, z0 + wall, seed + k, holes=holes, gable=rise if name in ('E', 'W') else 0.0, tone=tone)
        beam(p, (a[0], a[1], z0 - 0.09), (b[0], b[1], z0 - 0.09), 0.22, 0.20, seed + 40 + k, grey=0.2)                  # sill beam
        beam(p, (a[0], a[1], z0 + wall - 0.08), (b[0], b[1], z0 + wall - 0.08), 0.16, 0.16, seed + 44 + k, grey=0.2)    # top plate
        o, dv, out = wall_axes(a, b)
        beam(p, o + out * 0.03 + Vector((0, 0, z0 - 0.2)), o + out * 0.03 + Vector((0, 0, z0 + wall + 0.02)), 0.22, 0.22, seed + 50 + k, grey=0.15)   # corner post
        n = max(1, int(length / 2.2))
        for j in range(1, n):                                        # studs between, standing proud inside
            q = o + dv * (length * j / n) - out * 0.07
            if not any(h0 - 0.1 < length * j / n < h1 + 0.1 for h0, h1, _, _ in holes):
                beam(p, q + Vector((0, 0, z0)), q + Vector((0, 0, z0 + wall)), 0.12, 0.12, seed + 60 + j, grey=0.25)
        if piers:
            for j in range(n + 1):
                q = o + dv * (length * j / n)
                if z0 > 0.25:
                    stone(p, (q.x, q.y, (z0 - 0.19) / 2 - 0.05), (0.55, 0.55, z0 - 0.19 + 0.1), seed + 70 + j + k * 9)
    floor(p, cx - w / 2 + 0.03, cx + w / 2 - 0.03, cy - d / 2 + 0.03, cy + d / 2 - 0.03, z0, seed + 80)
    x = cx - w / 2 + 2.2
    while x < cx + w / 2 - 1.0:
        beam(p, (x, cy - d / 2, z0 + wall - 0.08), (x, cy + d / 2, z0 + wall - 0.08), 0.15, 0.18, seed + 90, grey=0.2)   # tie beams
        x += 2.4
    return roof(p, cx, cy, w, d, z0 + wall, seed + 95, pitch=pitch, thatch=thatch)


def chimney(p, x, y, top, seed):
    rnd = random.Random(seed)
    z = 0.0
    while z < top:
        taper = 1.0 - 0.25 * clamp01(z / top)
        for k in range(2):
            sx = rnd.uniform(0.40, 0.55) * taper
            stone(p, (x + (k - 0.5) * 0.46 * taper + rnd.uniform(-0.03, 0.03), y + rnd.uniform(-0.05, 0.05), z + 0.16), (sx, 0.78 * taper, 0.34), seed + int(z * 10) + k)
        z += 0.30
    stone(p, (x, y, top + 0.1), (1.0 * 0.78, 0.9 * 0.78, 0.16), seed + 999)


def table(p, x, y, z, seed, stools=3):
    p.tube([(Vector((x, y, z + 0.74)), 0.55, Vector((0, 0, 1))), (Vector((x, y, z + 0.80)), 0.55, Vector((0, 0, 1)))], shade(wood_tint(seed)), sides=12, smooth=False)
    keg(p, x, y, z, 0.82, seed + 1)
    for k in range(stools):
        a = 2 * math.pi * k / stools + seed
        sx, sy = x + math.cos(a) * 0.95, y + math.sin(a) * 0.95
        p.tube([(Vector((sx, sy, z)), 0.17, Vector((0, 0, 1))), (Vector((sx, sy, z + 0.45)), 0.19, Vector((0, 0, 1)))], shade(wood_tint(seed + 5 + k)), sides=10, smooth=False)


def sign(p, post_top, out_dir, emblem, seed):
    """Bracket and a hanging board; emblem(p, centre, right, up) paints the mark on both faces."""
    a = Vector(post_top)
    o = Vector(out_dir).normalized()
    beam(p, a, a + o * 1.15, 0.09, 0.10, seed, grey=0.15)
    beam(p, a + Vector((0, 0, -0.5)), a + o * 0.55, 0.06, 0.07, seed + 1, grey=0.15)
    c = a + o * 0.68 + Vector((0, 0, -0.62))
    plank(p, (0, 0, 0), (0.86, 0.05, 0.62), seed + 2, rot=Matrix.Translation(c) @ Matrix.Rotation(math.atan2(o.y, o.x), 4, 'Z'), grey=0.2)
    for s in (-0.33, 0.33):
        rope(p, a + o * (0.68 + s), c + o * s + Vector((0, 0, 0.31)), 0.012)
    side = Vector((-o.y, o.x, 0))
    for s in (-1, 1):
        emblem(p, c + side * (s * 0.032), o, s)


def lantern_mark(p, c, right, s):
    side = Vector((-right.y, right.x, 0)) * s
    for dz, w, col in ((0.0, 0.20, GLOW_HI), (0.16, 0.26, (0.12, 0.10, 0.10)), (-0.15, 0.26, (0.12, 0.10, 0.10))):
        q = c + Vector((0, 0, dz))
        hh = 0.13 if dz == 0.0 else 0.03
        fquad(p, [q - right * w / 2 + Vector((0, 0, -hh)) + side * 0.004, q + right * w / 2 + Vector((0, 0, -hh)) + side * 0.004,
                  q + right * w / 2 + Vector((0, 0, hh)) + side * 0.004, q - right * w / 2 + Vector((0, 0, hh)) + side * 0.004], col)


def alehouse(name):
    """The Leaky Lantern: an eleven by seven metre hall on stone piers, full-width porch, stone chimney, store at the back."""
    p = Prop(name)
    w, d, z0, wall = 11.0, 7.0, 0.55, 3.0
    zr = cabin(p, 0, 0, w, d, z0, wall, 3, {
        'S': [('door', 0.0, 1.5, 0.0, 2.15), ('window', -3.5, 1.1, 0.95, 1.2), ('window', 3.5, 1.1, 0.95, 1.2)],
        'N': [('window', -2.6, 1.0, 0.95, 1.15), ('window', 1.2, 1.0, 0.95, 1.15), ('door', 4.3, 0.95, 0.0, 2.05)],
        'W': [('window', -1.7, 1.0, 0.95, 1.15), ('window', 1.7, 1.0, 0.95, 1.15), ('loft', 0.0, 0.8, 3.6, 0.9)],
        'E': [('loft', 2.2, 0.7, 3.4, 0.8)]})
    chimney(p, w / 2 + 0.45, -0.6, zr + 0.9, 11)
    # porch: deck, posts, lean-to roof, rail, steps
    py0, py1 = -d / 2 - 2.5, -d / 2
    floor(p, -w / 2, w / 2, py0, py1, z0, 21)
    posts = [-5.35, -2.9, -1.0, 1.0, 2.9, 5.35]
    for k, x in enumerate(posts):
        stone(p, (x, py0 + 0.12, (z0 - 0.15) / 2 - 0.05), (0.5, 0.5, z0 - 0.15 + 0.1), 30 + k)
        beam(p, (x, py0 + 0.12, z0 - 0.2), (x, py0 + 0.12, z0 + 2.42), 0.18, 0.18, 40 + k, grey=0.2)
        beam(p, (x, py0 + 0.12, z0 + 2.05), (x + (0.45 if k < 5 else -0.45), py0 + 0.12, z0 + 2.42), 0.08, 0.10, 46 + k, grey=0.2)      # knee brace
        if k not in (2, 3):
            lantern(p, (x, py0 - 0.02, z0 + 1.9)) if k % 2 == 0 else None
    beam(p, (-w / 2 - 0.2, py0 + 0.12, z0 + 2.5), (w / 2 + 0.2, py0 + 0.12, z0 + 2.5), 0.18, 0.18, 50, grey=0.15)
    beam(p, (-w / 2, py0 + 0.1, z0 - 0.09), (w / 2, py0 + 0.1, z0 - 0.09), 0.2, 0.2, 51, grey=0.2)
    shingles(p, Vector((-w / 2 - 0.4, py1 + 0.05, z0 + 3.12)), Vector((w / 2 + 0.4, py1 + 0.05, z0 + 3.12)), 0.72, Vector((0, -2.95, 0)), 9, 52, False)
    x = -w / 2
    while x <= w / 2 + 0.01:
        beam(p, (x, py1, z0 + 3.0), (x, py0 - 0.3, z0 + 2.34), 0.07, 0.12, 53, grey=0.2)
        x += 1.1
    for a, b in ((0, 1), (1, 2), (3, 4), (4, 5)):
        rail(p, [(posts[a], py0 + 0.12, z0), ((posts[a] + posts[b]) / 2, py0 + 0.12, z0), (posts[b], py0 + 0.12, z0)], 0.95, 60 + a)
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        rail(p, [(x, py0 + 0.12, z0), (x, (py0 + py1) / 2, z0), (x, py1 - 0.1, z0)], 0.95, 70)
    stairs(p, (0, py0 - 0.85, 0), (0, py0, z0), 1.9, 80)
    sign(p, (posts[3], py0 + 0.05, z0 + 2.3), (0, -1, 0), lantern_mark, 90)
    # pirate dressing: a ship's wheel over the door, an anchor by the wall, casks, benches, bunting, a jutting spar with a lamp
    c = Vector((0, py1 - 0.09, z0 + 2.72))
    pipe(p, [c + Vector((math.cos(a) * 0.42, 0, math.sin(a) * 0.42)) for a in (2 * math.pi * k / 16 for k in range(16))], 0.04, shade(wood_tint(5)), sides=6, up=Vector((0, 1, 0)), closed=True)
    for k in range(8):
        a = math.pi * k / 4
        pipe(p, [c, c + Vector((math.cos(a) * 0.58, 0, math.sin(a) * 0.58))], 0.025, shade(wood_tint(6)), sides=5, up=Vector((0, 1, 0)))
    iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
    am = Matrix.Translation((-4.6, py1 - 0.35, z0 + 0.85)) @ Matrix.Rotation(-0.22, 4, 'X')
    p.box((0, 0, 0), (0.12, 0.12, 1.7), iron, bevel=0.03, xform=am)
    p.box((0, 0, 0), (0.9, 0.1, 0.1), iron, bevel=0.03, xform=am @ Matrix.Translation((0, 0, 0.75)))
    for s in (-1, 1):
        p.box((0, 0, 0), (0.7, 0.12, 0.14), iron, bevel=0.03, xform=am @ Matrix.Translation((s * 0.3, 0, -0.75)) @ Matrix.Rotation(s * 0.7, 4, 'Y'))
    for k, (x, y, s) in enumerate(((4.4, py1 - 0.5, 1.0), (5.0, py1 - 0.55, 0.9), (4.7, py1 - 1.05, 0.8), (-5.9, -1.0, 1.1), (-6.0, 0.0, 1.0))):
        keg(p, x, y, z0 if k < 3 else 0.0, s, 100 + k)
    for x in (-3.5, 2.6):
        plank(p, (x, py1 - 0.55, z0 + 0.45), (1.8, 0.4, 0.07), 110, grey=0.3)
        for sx in (-0.7, 0.7):
            plank(p, (x + sx, py1 - 0.55, z0 + 0.22), (0.08, 0.36, 0.44), 111, grey=0.3, bevel=0.0)
    bunting(p, (posts[0], py0 + 0.12, z0 + 2.3), (posts[2], py0 + 0.12, z0 + 2.3), 9, (CRIMSON, BONE, TEAL, OCHRE), 0.3)
    bunting(p, (posts[3] + 0.4, py0 + 0.12, z0 + 2.3), (posts[5], py0 + 0.12, z0 + 2.3), 9, (TEAL, OCHRE, CRIMSON, BONE), 0.3)
    beam(p, (-w / 2 - 0.3, 0, zr - 0.25), (-w / 2 - 2.3, 0, zr + 0.35), 0.12, 0.12, 120, grey=0.15)
    rope(p, (-w / 2 - 2.2, 0, zr + 0.3), (-w / 2 - 2.2, 0, zr - 0.25), 0.012)
    lantern(p, (-w / 2 - 2.2, 0, zr - 0.42))
    # store at the back, under a lean-to roof
    cabin(p, -3.2, d / 2 + 1.35, 4.0, 2.7, 0.35, 2.1, 130, {'N': [('door', 0.6, 0.95, 0.0, 1.95)], 'W': [('loft', 0.0, 0.6, 1.0, 0.6)]}, pitch=32.0)
    # inside: bar along the back wall, shelves, tables, hearth
    bx0, bx1, by = -4.6, 0.6, d / 2 - 1.5
    plank(p, ((bx0 + bx1) / 2, by, z0 + 0.52), (bx1 - bx0, 0.55, 1.04), 140, grey=0.2)
    plank(p, ((bx0 + bx1) / 2, by - 0.05, z0 + 1.07), (bx1 - bx0 + 0.2, 0.75, 0.07), 141, grey=0.1)
    for zz in (1.5, 2.0):
        plank(p, ((bx0 + bx1) / 2, d / 2 - 0.2, z0 + zz), (bx1 - bx0, 0.28, 0.04), 142, grey=0.25)
        for k in range(7):
            keg(p, bx0 + 0.4 + k * 0.72, d / 2 - 0.2, z0 + zz + 0.02, 0.36, 150 + k)
    keg(p, bx1 + 0.6, d / 2 - 0.75, z0, 1.3, 160)
    for k, (x, y) in enumerate(((-3.4, -1.4), (-0.4, -1.9), (2.6, -1.2), (3.6, 1.4))):
        table(p, x, y, z0, 170 + k * 9)
    for k in range(3):
        stone(p, (w / 2 - 0.35, -0.6 + (k - 1) * 0.55, z0 + 0.2), (0.55, 0.5, 0.4), 200 + k)
    stone(p, (w / 2 - 0.35, -0.6, z0 + 1.45), (0.6, 1.9, 0.3), 204)
    fquad(p, [Vector((w / 2 - 0.62, -1.1, z0 + 0.4)), Vector((w / 2 - 0.62, -0.1, z0 + 0.4)), Vector((w / 2 - 0.62, -0.1, z0 + 1.3)), Vector((w / 2 - 0.62, -1.1, z0 + 1.3))],
          lambda co, nrm: lerp((1.0, 0.36, 0.06), (0.25, 0.08, 0.04), clamp01((co.z - z0 - 0.4) / 0.9)))
    p.export()


def warden_hut(name):
    """Lantern Wardens' watch house: a square cabin on tall braced stilts, gallery all round, great lantern on the roof."""
    p = Prop(name)
    z0, wd, gal = 2.7, 3.6, 0.85
    half = wd / 2 + gal
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(p, (sx * (half - 0.15), sy * (half - 0.15), -0.6), (sx * (half - 0.45), sy * (half - 0.45), z0 - 0.1), 0.26, 0.26, 3 + sx + 2 * sy, grey=0.2)
            stone(p, (sx * (half - 0.12), sy * (half - 0.12), 0.12), (0.7, 0.7, 0.34), 10 + sx + 2 * sy)
    for k in range(4):
        m = Matrix.Rotation(k * math.pi / 2, 4, 'Z')
        for flip in (-1, 1):
            a, b = m @ Vector((-flip * (half - 0.2), -(half - 0.22), 0.25)), m @ Vector((flip * (half - 0.42), -(half - 0.40), z0 - 0.45))
            beam(p, a, b, 0.09, 0.14, 20 + k * 2 + flip, grey=0.25)
        beam(p, m @ Vector((-half, -half + 0.1, z0 - 0.12)), m @ Vector((half, -half + 0.1, z0 - 0.12)), 0.2, 0.22, 30 + k, grey=0.2)
        rail(p, [m @ Vector((-half + 0.08, -half + 0.08, z0)), m @ Vector((-half / 2, -half + 0.08, z0)), m @ Vector((0.55 if k == 0 else 0.0, -half + 0.08, z0)),
                 m @ Vector((half / 2 if k else half - 0.08, -half + 0.08, z0))] + ([m @ Vector((half - 0.08, -half + 0.08, z0))] if k else []), 1.0, 40 + k * 5) if k else None
    rail(p, [(-half + 0.08, -half + 0.08, z0), (-half / 2 - 0.2, -half + 0.08, z0), (-0.55, -half + 0.08, z0)], 1.0, 60)
    rail(p, [(0.55, -half + 0.08, z0), (half / 2 + 0.2, -half + 0.08, z0), (half - 0.08, -half + 0.08, z0)], 1.0, 62)
    floor(p, -half, half, -half, half, z0, 70)
    zr = cabin(p, 0, 0, wd, wd, z0, 2.5, 80, {'S': [('door', 0.0, 0.95, 0.0, 2.05)], 'E': [('window', 0.0, 0.9, 0.95, 1.1)], 'W': [('window', 0.0, 0.9, 0.95, 1.1)],
                                              'N': [('window', 0.0, 0.9, 0.95, 1.1)]}, pitch=52.0, piers=False, tone=0.35)
    stairs(p, (0, -half - 3.9, 0), (0, -half, z0), 1.0, 90)
    for s in (-1, 1):
        rail(p, [(s * 0.5, -half - 3.9, 0.0), (s * 0.5, -half - 1.95, z0 / 2), (s * 0.5, -half - 0.05, z0)], 0.95, 95 + s, mid=False)
    # the great lantern: iron cage on a king post above the ridge
    iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
    beam(p, (0, 0, zr - 0.2), (0, 0, zr + 0.75), 0.16, 0.16, 100, grey=0.15)
    p.box((0, 0, zr + 1.25), (0.62, 0.62, 0.86), lambda co, nrm: lerp(GLOW_LO, GLOW_HI, clamp01((co.z - zr - 0.8) / 0.9)), bevel=0.05)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((sx * 0.36, sy * 0.36, zr + 1.25), (0.06, 0.06, 1.0), iron)
    for zz in (0.78, 1.72):
        p.box((0, 0, zr + zz), (0.9, 0.9, 0.08), iron, bevel=0.02)
    p.tube([(Vector((0, 0, zr + 1.76)), 0.52, Vector((0, 0, 1))), (Vector((0, 0, zr + 2.15)), 0.08, Vector((0, 0, 1)))], iron, sides=8, smooth=False)
    beam(p, (0, 0, zr + 2.1), (0, 0, zr + 2.9), 0.05, 0.05, 101, grey=0.1)
    fquad(p, [Vector((0, 0, zr + 2.85)), Vector((0.75, 0.05, zr + 2.72)), Vector((0, 0, zr + 2.55))], shade(CRIMSON, 0.7))
    bunting(p, (0.3, -0.3, zr + 0.7), (half - 0.1, -half + 0.1, z0 + 1.0), 8, (CRIMSON, BONE), 0.35)
    bunting(p, (-0.3, -0.3, zr + 0.7), (-half + 0.1, -half + 0.1, z0 + 1.0), 8, (CRIMSON, BONE), 0.35)
    p.tube([(Vector((1.2, -wd / 2 - 0.3, z0 + 2.0)), 0.16, Vector((0, 0, 1))), (Vector((1.2, -wd / 2 - 0.3, z0 + 2.25)), 0.07, Vector((0, 0, 1)))], shade(OCHRE), sides=10, smooth=False)   # storm bell
    lantern(p, (-1.1, -wd / 2 - 0.2, z0 + 1.9))
    keg(p, half - 0.5, half - 0.5, z0, 0.9, 110)
    crate(p, -half + 0.5, half - 0.5, z0, 0.6, 111)
    p.export()


def salvage_camp(name):
    """Deepfinders' camp: patched ridge tent on lashed A-frames, a diving bell slung from a tripod, the day's finds laid out."""
    p = Prop(name)
    L, W, H = 5.2, 4.0, 3.0
    for x in (-L / 2, L / 2):
        for s in (-1, 1):
            beam(p, (x, s * W / 2, -0.3), (x, -s * 0.12, H + 0.25), 0.11, 0.11, 3 + s, grey=0.25)
        pipe(p, [Vector((x + 0.07 * math.cos(a), 0.07 * math.sin(a) * 2.2, H + 0.02 + 0.02 * k)) for k in range(4) for a in (2 * math.pi * q / 6 for q in range(6))], 0.016, shade(ROPE_C), sides=4)
    beam(p, (-L / 2 - 0.45, 0, H), (L / 2 + 0.45, 0, H), 0.12, 0.12, 9, grey=0.2)
    nu, nv = 14, 8
    for s in (-1, 1):
        def pt(u, v, s=s):
            x = -L / 2 - 0.15 + (L + 0.3) * u
            sag = 0.10 * math.sin(math.pi * u) * math.sin(math.pi * v)
            return Vector((x, s * (W / 2 + 0.25) * v, H - (H - 0.55) * v - sag + 0.03))
        for i in range(nu):
            for j in range(nv):
                uc, vc = (i + 0.5) / nu, (j + 0.5) / nv
                patch = any(abs(uc - pu) < 0.09 and abs(vc - pv) < 0.14 for pu, pv in ((0.22, 0.35), (0.63, 0.62), (0.84, 0.25) if s < 0 else (0.40, 0.75)))
                wear = noise.noise(Vector((uc * 4.0, vc * 3.0, s * 2.0)))
                base = lerp(SEA, BONE, 0.50) if patch else lerp(lerp(SEA, (0.22, 0.44, 0.56), 0.5 + 0.9 * wear), (0.55, 0.60, 0.58), 0.25 * clamp01(vc * 1.4 - 0.5))
                fquad(p, [pt(i / nu, j / nv), pt((i + 1) / nu, j / nv), pt((i + 1) / nu, (j + 1) / nv), pt(i / nu, (j + 1) / nv)],
                      lambda co, nrm, base=base: lerp(lerp(base, (0.10, 0.14, 0.20), 0.45), base, clamp01(co.z / H + 0.15)), smooth=True)
        for k in range(5):
            x = -L / 2 + L * k / 4
            rope(p, (x, s * (W / 2 + 0.25), 0.58), (x, s * (W / 2 + 0.95), 0.0), 0.016)
        pipe(p, [pt(u / 8, 1.0) for u in range(9)], 0.02, shade((0.84, 0.48, 0.24)), sides=4, up=Vector((0, 0, 1)))
    for k in range(int(L / 0.24)):
        plank(p, (-L / 2 + 0.12 + k * 0.24, 0, 0.09), (0.22, W - 0.4, 0.05), 20 + k, grey=0.4)
    for y in (-1.2, 0, 1.2):
        beam(p, (-L / 2, y, 0.035), (L / 2, y, 0.035), 0.1, 0.07, 40, grey=0.3)
    plank(p, (0.8, 0.9, 0.5), (1.9, 0.75, 0.07), 50, grey=0.3)                                                           # finds table
    for sx in (-0.8, 0.8):
        plank(p, (0.8 + sx, 0.9, 0.3), (0.08, 0.65, 0.4), 51, grey=0.3, bevel=0.0)
    for k, (dx, c) in enumerate(((-0.6, (0.70, 0.42, 0.26)), (-0.15, (0.62, 0.70, 0.62)), (0.35, (0.80, 0.50, 0.30)))):
        p.tube([(Vector((0.8 + dx, 0.9, 0.54)), 0.07, Vector((0, 0, 1))), (Vector((0.8 + dx, 0.9, 0.70)), 0.13, Vector((0, 0, 1))), (Vector((0.8 + dx, 0.9, 0.92)), 0.06, Vector((0, 0, 1))),
                (Vector((0.8 + dx, 0.9, 0.98)), 0.08, Vector((0, 0, 1)))], shade(c), sides=10)
    p.blob((1.45, 0.9, 0.60), (0.16, 0.12, 0.07), shade((1.0, 0.82, 0.36)), 3, 0.3, 2, smooth=True)
    crate(p, -1.6, 1.0, 0.11, 0.7, 60)
    keg(p, -1.7, -1.1, 0.11, 1.0, 61)
    plank(p, (0.2, -1.2, 0.33), (1.9, 0.8, 0.12), 62, grey=0.3)                                                          # cot
    fquad(p, [Vector((-0.7, -1.55, 0.40)), Vector((1.1, -1.55, 0.40)), Vector((1.1, -0.85, 0.40)), Vector((-0.7, -0.85, 0.40))], shade(lerp(SEA, BONE, 0.6)))
    lantern(p, (L / 2 - 0.3, 0, H - 0.5))
    # tripod hoist with the diving bell
    bx, by = L / 2 + 3.2, -0.6
    iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
    copper = lambda co, nrm: lerp((0.42, 0.22, 0.12), (0.92, 0.58, 0.34), clamp01(nrm.z * 0.5 + 0.55))
    apex = Vector((bx, by, 4.6))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        beam(p, (bx + math.cos(a) * 2.1, by + math.sin(a) * 2.1, -0.3), apex + Vector((math.cos(a) * 0.1, math.sin(a) * 0.1, 0.25)), 0.14, 0.14, 70 + k, grey=0.25)
    pipe(p, [apex + Vector((0.16 * math.cos(a), 0.16 * math.sin(a), -0.05 + 0.03 * k)) for k in range(4) for a in (2 * math.pi * q / 6 for q in range(6))], 0.02, shade(ROPE_C), sides=4)
    rope(p, apex, (bx, by, 2.95), 0.03)
    p.tube([(Vector((bx, by, 1.15)), 0.62, Vector((0, 0, 1))), (Vector((bx, by, 1.30)), 0.64, Vector((0, 0, 1))), (Vector((bx, by, 2.2)), 0.58, Vector((0, 0, 1))),
            (Vector((bx, by, 2.65)), 0.40, Vector((0, 0, 1))), (Vector((bx, by, 2.88)), 0.14, Vector((0, 0, 1)))], copper, sides=14)
    for zz in (1.22, 2.2):
        pipe(p, [Vector((bx + math.cos(a) * 0.66, by + math.sin(a) * 0.66, zz)) for a in (2 * math.pi * k / 14 for k in range(14))], 0.04, iron, sides=5, closed=True)
    for k in range(3):
        a = 2 * math.pi * k / 3 - 0.8
        c = Vector((bx + math.cos(a) * 0.60, by + math.sin(a) * 0.60, 1.8))
        pipe(p, [c + Vector((-math.sin(a) * math.cos(t) * 0.17, math.cos(a) * math.cos(t) * 0.17, math.sin(t) * 0.17)) for t in (2 * math.pi * q / 10 for q in range(10))], 0.03, iron, sides=5,
             up=Vector((math.cos(a), math.sin(a), 0)), closed=True)
        p.blob(tuple(c), (0.15, 0.15, 0.15), lambda co, nrm: (0.50, 0.78, 0.84), k, 0.0, 2, smooth=True)
    for k in range(4):
        a = math.pi / 4 + math.pi * k / 2
        p.box((bx + math.cos(a) * 0.62, by + math.sin(a) * 0.62, 1.0), (0.2, 0.2, 0.3), iron, bevel=0.04)
        rope(p, (bx + math.cos(a) * 0.62, by + math.sin(a) * 0.62, 1.15), (bx + math.cos(a) * 0.62, by + math.sin(a) * 0.62, 1.0), 0.02)
    keg(p, bx - 1.5, by + 1.6, 0.0, 1.1, 80)                                                                              # air pump
    pipe(p, [Vector((bx - 1.5, by + 1.6, 1.0)), Vector((bx - 1.2, by + 1.2, 1.25)), Vector((bx - 0.7, by + 0.6, 0.6)), Vector((bx - 0.45, by + 0.3, 1.3))], 0.035, shade((0.30, 0.22, 0.16)), sides=6)
    beam(p, (bx - 1.5, by + 1.6, 1.0), (bx - 1.5, by + 1.6, 1.6), 0.05, 0.05, 81, grey=0.1)
    beam(p, (bx - 1.9, by + 1.6, 1.6), (bx - 1.1, by + 1.6, 1.6), 0.05, 0.05, 82, grey=0.1)
    post(p, -L / 2 - 1.2, -W / 2 - 0.6, -0.4, 4.6, 0.08, 90)
    fquad(p, [Vector((-L / 2 - 1.2, -W / 2 - 0.6, 4.5)), Vector((-L / 2 - 0.1, -W / 2 - 0.62, 4.35)), Vector((-L / 2 - 0.45, -W / 2 - 0.61, 4.1)), Vector((-L / 2 - 0.1, -W / 2 - 0.62, 3.85)),
              Vector((-L / 2 - 1.2, -W / 2 - 0.6, 3.7))], shade(SEA, 0.6))
    p.export()


def keelwright_yard(name):
    """Keelwrights' yard: an open-sided shed with benches and timber, and a hull in frame on the building slip."""
    p = Prop(name)
    w, d, wall = 8.0, 5.5, 3.1
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.15), sy * (d / 2 - 0.15)
            stone(p, (x, y, 0.1), (0.6, 0.6, 0.3), 3 + sx + sy)
            beam(p, (x, y, 0.2), (x, y, wall), 0.22, 0.22, 10 + sx * 3 + sy, grey=0.2)
            beam(p, (x, y, wall - 0.75), (x + (0.7 if sx <= 0 else -0.7), y, wall - 0.05), 0.09, 0.12, 20 + sx, grey=0.2)
    for sy in (-1, 1):
        beam(p, (-w / 2 - 0.2, sy * (d / 2 - 0.15), wall + 0.02), (w / 2 + 0.2, sy * (d / 2 - 0.15), wall + 0.02), 0.2, 0.2, 30 + sy, grey=0.15)
    for sx in (-1, 0, 1):
        beam(p, (sx * (w / 2 - 0.15), -d / 2, wall + 0.05), (sx * (w / 2 - 0.15), d / 2, wall + 0.05), 0.16, 0.18, 34 + sx, grey=0.2)
    roof(p, 0, 0, w, d, wall + 0.12, 40, pitch=38.0)
    clad(p, (w / 2, d / 2 - 0.15), (-w / 2, d / 2 - 0.15), 0.25, wall, 50, holes=[(2.6, 3.7, 1.1, 2.2)])                    # back wall with a tool hatch
    for k in range(int(w / 0.24)):
        plank(p, (-w / 2 + 0.12 + k * 0.24, 0, 0.06), (0.22, d - 0.5, 0.05), 60 + k, grey=0.45)
    plank(p, (-1.8, d / 2 - 0.75, 0.86), (3.0, 0.8, 0.09), 80, grey=0.2)                                                   # workbench with vice and tools
    for sx in (-1.3, 1.3):
        plank(p, (-1.8 + sx, d / 2 - 0.75, 0.45), (0.12, 0.7, 0.8), 81, grey=0.2, bevel=0.0)
    iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
    p.box((-2.9, d / 2 - 0.9, 1.0), (0.22, 0.3, 0.2), iron, bevel=0.03)
    for k in range(6):
        beam(p, (-2.4 + k * 0.32, d / 2 - 0.22, 1.3), (-2.4 + k * 0.32, d / 2 - 0.22, 1.3 + 0.35 + 0.1 * (k % 3)), 0.035, 0.035, 90 + k, grey=0.1, bevel=0.0)
        p.box((-2.4 + k * 0.32, d / 2 - 0.22, 1.72 + 0.1 * (k % 3)), (0.12 + 0.05 * (k % 2), 0.04, 0.10), iron, bevel=0.01)
    for row in range(3):                                            # seasoned planks stacked on bearers
        for k in range(6 - row):
            plank(p, (2.2, -1.6 + k * 0.33 + row * 0.16, 0.25 + row * 0.13), (3.6, 0.28, 0.07), 100 + row * 9 + k, grey=0.35)
    keg(p, 3.3, 1.6, 0.09, 1.0, 120)
    lantern(p, (0, 0, wall - 0.35))
    # the slip: keel on blocks, stem and sternpost raised, nine pairs of frames, the first strakes hung
    sx0, sy0, hl = -5.2, -d / 2 - 3.6, 10.4

    def half(t):
        return 1.75 * (1.0 - 0.3 * (1.0 - min(1.0, (t + 0.05) / 0.4)) ** 2) * (1.0 - max(0.0, (t - 0.55) / 0.45) ** 2.4)

    def hx(t):
        return sx0 + hl * t

    for k in range(6):
        stone(p, (hx(0.08 + 0.168 * k), sy0, 0.22), (0.5, 0.9, 0.44), 130 + k)
    beam(p, (hx(0.02), sy0, 0.56), (hx(0.9), sy0, 0.56), 0.24, 0.26, 140, grey=0.15)
    pipe(p, [Vector((hx(0.88), sy0, 0.56)), Vector((hx(0.96), sy0, 0.9)), Vector((hx(1.0), sy0, 1.6)), Vector((hx(1.02), sy0, 2.5))], 0.13, shade(wood_tint(141)), sides=6, up=Vector((0, 1, 0)))
    beam(p, (hx(0.02), sy0, 0.56), (hx(0.0), sy0, 2.2), 0.2, 0.22, 142, grey=0.15)
    for k in range(9):
        t = 0.08 + 0.095 * k
        hb = half(t)
        tint = wood_tint(150 + k)
        for s in (-1, 1):
            pipe(p, [Vector((hx(t), sy0 + s * hb * (j / 6) ** 0.5, 0.7 + 1.9 * (j / 6) ** 1.5)) for j in range(7)], 0.07, shade(tint), sides=5, up=Vector((1, 0, 0)))
        beam(p, (hx(t), sy0 - hb, 2.62), (hx(t), sy0 + hb, 2.62), 0.07, 0.09, 160 + k, grey=0.3)
    for j in (1, 2, 3):
        for s in (-1, 1):
            pts = [Vector((hx(t), sy0 + s * (half(t) * (j / 6) ** 0.5 + 0.06), 0.7 + 1.9 * (j / 6) ** 1.5)) for t in (0.08 + 0.095 * k for k in range(9))]
            for a, b in zip(pts, pts[1:]):
                fquad(p, [a + Vector((0, 0, -0.16)), b + Vector((0, 0, -0.16)), b + Vector((0, 0, 0.16)), a + Vector((0, 0, 0.16))], shade(lerp(wood_tint(170 + j), BONE, 0.2), 0.7))
    for k in range(4):                                              # shores holding her upright
        t = 0.15 + 0.22 * k
        for s in (-1, 1):
            beam(p, (hx(t), sy0 + s * (half(t) + 1.5), 0.0), (hx(t), sy0 + s * (half(t) * 0.8), 1.7), 0.09, 0.09, 180 + k, grey=0.3)
    stairs(p, (hx(0.5), sy0 + 3.2, 0.0), (hx(0.5), sy0 + 2.0, 1.1), 0.8, 190)
    p.export()


def market_stall(name):
    """Saltmarket stall: counter, back shelves, striped awning on a timber frame, scales, sacks and crates."""
    p = Prop(name)
    w, d = 4.2, 2.6
    for sx in (-1, 1):
        beam(p, (sx * w / 2, -d / 2, 0), (sx * w / 2, -d / 2, 2.35), 0.13, 0.13, 3 + sx, grey=0.2)
        beam(p, (sx * w / 2, d / 2, 0), (sx * w / 2, d / 2, 2.95), 0.13, 0.13, 5 + sx, grey=0.2)
        beam(p, (sx * w / 2, -d / 2 - 0.5, 2.22), (sx * w / 2, d / 2 + 0.2, 3.02), 0.08, 0.11, 7 + sx, grey=0.2)
    for y, z in ((-d / 2 - 0.5, 2.22), (0.0, 2.68), (d / 2 + 0.2, 3.02)):
        beam(p, (-w / 2 - 0.3, y, z), (w / 2 + 0.3, y, z), 0.07, 0.09, 10, grey=0.2)
    stripes = 9
    for k in range(stripes):
        x0, x1 = -w / 2 - 0.3 + (w + 0.6) * k / stripes, -w / 2 - 0.3 + (w + 0.6) * (k + 1) / stripes
        c = BONE if k % 2 else TEAL
        for j in range(6):
            v0, v1 = j / 6, (j + 1) / 6
            f = lambda x, v: Vector((x, -d / 2 - 0.55 + (d + 0.8) * v, 2.28 + 0.80 * v - 0.05 * math.sin(math.pi * v)))
            fquad(p, [f(x0, v0), f(x1, v0), f(x1, v1), f(x0, v1)], shade(c, 0.7), smooth=True)
        fquad(p, [Vector((x0, -d / 2 - 0.55, 2.28)), Vector((x1, -d / 2 - 0.55, 2.28)), Vector(((x0 + x1) / 2, -d / 2 - 0.6, 1.98))], shade(c, 0.6))
    plank(p, (0, -d / 2 + 0.25, 0.47), (w - 0.2, 0.5, 0.94), 20, grey=0.25)
    plank(p, (0, -d / 2 + 0.2, 0.98), (w + 0.1, 0.72, 0.07), 21, grey=0.12)
    clad(p, (w / 2, d / 2), (-w / 2, d / 2), 0.0, 2.2, 30)
    for zz in (1.0, 1.55):
        plank(p, (0, d / 2 - 0.2, zz), (w - 0.3, 0.32, 0.04), 40, grey=0.25)
    for k in range(5):
        keg(p, -1.6 + k * 0.8, d / 2 - 0.2, 1.02, 0.42, 50 + k)
        crate(p, -1.5 + k * 0.75, d / 2 - 0.2, 1.57, 0.32, 60 + k)
    for k, (x, y, s) in enumerate(((-1.4, 0.2, 0.6), (-0.7, 0.4, 0.5), (1.5, 0.3, 0.65))):
        crate(p, x, y, 0.0, s, 70 + k)
    for k, (x, c) in enumerate(((-1.3, (0.86, 0.78, 0.58)), (-0.8, (0.80, 0.70, 0.50)), (1.2, (0.84, 0.74, 0.54)))):                # sacks on the counter front
        p.blob((x, -d / 2 - 0.25, 0.28), (0.26, 0.22, 0.30), shade(c, 0.6), k, 0.18, 2, smooth=True)
    hx_ = Vector((0.9, -d / 2 + 0.2, 1.02))                                                                                 # scales
    pipe(p, [hx_, hx_ + Vector((0, 0, 0.45))], 0.014, shade((1.0, 0.82, 0.36)), sides=5)
    pipe(p, [hx_ + Vector((-0.25, 0, 0.43)), hx_ + Vector((0.25, 0, 0.43))], 0.01, shade((1.0, 0.82, 0.36)), sides=4, up=Vector((0, 1, 0)))
    for s in (-1, 1):
        p.tube([(hx_ + Vector((s * 0.25, 0, 0.18)), 0.085, Vector((0, 0, 1))), (hx_ + Vector((s * 0.25, 0, 0.20)), 0.10, Vector((0, 0, 1)))], shade((1.0, 0.82, 0.36)), sides=10, smooth=False)
        rope(p, hx_ + Vector((s * 0.25, 0, 0.43)), hx_ + Vector((s * 0.25, 0, 0.20)), 0.005)
    for k in range(4):                                              # the catch, hung to dry
        fx = -1.7 + k * 0.32
        rope(p, (fx, -d / 2 - 0.45, 2.2), (fx, -d / 2 - 0.45, 1.95), 0.006)
        p.blob((fx, -d / 2 - 0.45, 1.78), (0.045, 0.02, 0.17), shade((0.62, 0.70, 0.74), 0.6), k, 0.0, 2, smooth=True)
    lantern(p, (w / 2 - 0.25, -d / 2 - 0.3, 1.95))
    plank(p, (0, -d / 2 - 0.52, 2.5), (1.5, 0.05, 0.42), 80, grey=0.2)
    for s in (-1, 1):
        fquad(p, [Vector((s * 0.15 - 0.12, -d / 2 - 0.55, 2.42)), Vector((s * 0.15 + 0.12, -d / 2 - 0.55, 2.42)), Vector((s * 0.15, -d / 2 - 0.55, 2.62))], (1.0, 0.86, 0.45))
    p.export()


def lookout(name):
    """Gull's Perch: a braced timber tower with a roofed platform, ladder, signal bell."""
    p = Prop(name)
    foot, top, deck = 2.0, 1.25, 9.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            stone(p, (sx * foot, sy * foot, 0.12), (0.7, 0.7, 0.34), 3 + sx + 2 * sy)
            beam(p, (sx * foot, sy * foot, 0.0), (sx * top, sy * top, deck + 2.3), 0.22, 0.22, 10 + sx + 2 * sy, grey=0.2)
    for level in range(3):
        z0, z1 = 0.4 + level * 3.0, 0.4 + (level + 1) * 3.0
        r0 = foot + (top - foot) * z0 / (deck + 2.3)
        r1 = foot + (top - foot) * z1 / (deck + 2.3)
        for k in range(4):
            m = Matrix.Rotation(k * math.pi / 2, 4, 'Z')
            for flip in (-1, 1):
                beam(p, m @ Vector((-flip * r0, -r0, z0)), m @ Vector((flip * r1, -r1, z1)), 0.07, 0.13, 20 + level * 9 + k * 2 + flip, grey=0.25)
            beam(p, m @ Vector((-r1 - 0.1, -r1, z1)), m @ Vector((r1 + 0.1, -r1, z1)), 0.12, 0.15, 60 + level * 4 + k, grey=0.2)
    hd = 1.9
    for k in range(int(2 * hd / 0.24)):
        plank(p, (-hd + 0.12 + k * 0.24, 0, deck), (0.22, 2 * hd, 0.06), 80 + k, grey=0.4)
    for k in range(4):
        m = Matrix.Rotation(k * math.pi / 2, 4, 'Z')
        beam(p, m @ Vector((-hd, -hd + 0.1, deck - 0.12)), m @ Vector((hd, -hd + 0.1, deck - 0.12)), 0.14, 0.16, 100 + k, grey=0.2)
        pts = [m @ Vector((-hd + 0.08, -hd + 0.08, deck)), m @ Vector((-hd / 3, -hd + 0.08, deck)), m @ Vector((hd / 3, -hd + 0.08, deck)), m @ Vector((hd - 0.08, -hd + 0.08, deck))]
        rail(p, pts if k else pts[1:], 1.0, 110 + k * 5)
    roof(p, 0, 0, 2 * top + 0.5, 2 * top + 0.5, deck + 2.3, 130, pitch=40.0, eave=0.5, over=0.5, thatch=True)
    for k in range(int(deck / 0.3)):                                # ladder up through the corner gap
        beam(p, (-hd + 0.35, -hd - 0.05 + 0.0, 0.3 * (k + 1)), (-hd + 0.95, -hd - 0.05, 0.3 * (k + 1)), 0.05, 0.05, 140, grey=0.3, bevel=0.0)
    for sx in (0.35, 0.95):
        beam(p, (-hd + sx, -hd - 0.05 - 1.3, 0.0), (-hd + sx, -hd - 0.05, deck + 1.0), 0.07, 0.07, 150, grey=0.2)
    p.tube([(Vector((0.6, 0.6, deck + 1.75)), 0.2, Vector((0, 0, 1))), (Vector((0.6, 0.6, deck + 2.05)), 0.08, Vector((0, 0, 1)))], shade(OCHRE), sides=10, smooth=False)
    rope(p, (0.6, 0.6, deck + 2.25), (0.6, 0.6, deck + 2.05), 0.012)
    lantern(p, (-0.7, 0.7, deck + 1.9))
    keg(p, 1.2, -1.2, deck + 0.03, 0.8, 160)
    post(p, 0, 0, deck + 2.3 + 1.2, deck + 5.2, 0.05, 170)
    fquad(p, [Vector((0, 0, deck + 5.15)), Vector((1.3, 0.05, deck + 4.95)), Vector((0.9, 0.03, deck + 4.75)), Vector((1.3, 0.05, deck + 4.55)), Vector((0, 0, deck + 4.4))], shade(TEAL, 0.7))
    p.export()


def hut(name, w, d, seed, thatch):
    """A store hut: one room, a door and two windows, three steps up."""
    p = Prop(name)
    z0 = 0.5
    cabin(p, 0, 0, w, d, z0, 2.45, seed, {'S': [('door', -w * 0.15, 0.95, 0.0, 2.05), ('window', w * 0.26, 0.85, 0.95, 1.05)], 'E': [('window', 0.0, 0.85, 0.95, 1.05)],
                                          'W': [('loft', 0.0, 0.6, 2.7, 0.6)]}, pitch=44.0, thatch=thatch, tone=0.4)
    stairs(p, (-w * 0.15, -d / 2 - 0.85, 0), (-w * 0.15, -d / 2, z0), 1.2, seed + 5)
    keg(p, w / 2 + 0.5, -d / 2 + 0.6, 0.0, 1.0, seed + 6)
    crate(p, w / 2 + 0.45, -d / 2 + 1.5, 0.0, 0.7, seed + 7)
    lantern(p, (-w * 0.15 + 0.75, -d / 2 - 0.12, z0 + 1.9))
    crate(p, -1.0, 0.8, z0, 0.7, seed + 8)
    keg(p, 1.2, 1.0, z0, 0.95, seed + 9)
    p.export()


alehouse("SM_BW_Alehouse")
warden_hut("SM_BW_WardenHut")
salvage_camp("SM_BW_SalvageTent")
keelwright_yard("SM_BW_Keelwright")
market_stall("SM_BW_MarketStall")
lookout("SM_BW_Tower")
hut("SM_BW_Hut_A", 4.2, 5.0, 301, True)
hut("SM_BW_Hut_B", 5.4, 6.2, 401, False)
