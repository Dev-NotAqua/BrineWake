# Brinewake ships, built in the open Blender (run through bl_run.py).
# Walkable everywhere: thick hull with ribs, main deck, hatch and companion stairs to a hold, raised quarterdeck over a
# stern cabin, canvas awning over the helm, crow's nest, standing and running rigging. Bow is +x, waterline z = 0, metres.
TAR, WEED, BOOT = (0.17, 0.12, 0.10), (0.24, 0.34, 0.18), (0.90, 0.85, 0.70)
DECK_A, DECK_B = (0.60, 0.45, 0.28), (0.84, 0.69, 0.46)
OCHRE, BONE, ROPE_C = (0.90, 0.64, 0.20), (0.90, 0.82, 0.62), (0.70, 0.57, 0.36)
GOLD_LO, GOLD_HI = (0.55, 0.36, 0.10), (1.0, 0.82, 0.36)


def lin(c):
    return (clamp01(c[0]), clamp01(c[1]), clamp01(c[2]), 1.0)


def fquad(p, pts, colour, smooth=False):
    """One face on fresh vertices, painted at once (cheap: no whole-mesh normal update)."""
    f = p.bm.faces.new([p.bm.verts.new(v) for v in pts])
    f.smooth = smooth
    f.normal_update()
    for loop in f.loops:
        loop[p.col] = lin(colour(loop.vert.co, f.normal) if callable(colour) else colour)
    return f


def pipe(p, pts, radii, colour, sides=6, up=Vector((0, 0, 1)), closed=False):
    """Round section swept along a path. `up` keeps the section from twisting."""
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


def rope(p, a, b, r=0.028, sag=0.0):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, k / 6) + Vector((0, 0, -sag * math.sin(math.pi * k / 6))) for k in range(7)] if sag else [a, b]
    pipe(p, pts, r, shade(ROPE_C), sides=5)


def coil(p, x, y, z):
    for layer in range(3):
        r = 0.30 - 0.035 * layer
        pipe(p, [Vector((x + math.cos(a) * r, y + math.sin(a) * r, z + 0.035 + 0.062 * layer)) for a in (2 * math.pi * k / 12 for k in range(12))],
             0.034, shade(ROPE_C), sides=5, closed=True)


def keg(p, x, y, z, s, seed):
    tint = wood_tint(seed)
    rings = [(Vector((x, y, z + s * 0.9 * k / 6)), s * (0.30 + 0.07 * math.sin(math.pi * k / 6)), Vector((0, 0, 1))) for k in range(7)]
    p.tube(rings, lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.5), tint, clamp01(0.3 + (co.z - z) / s) * (0.8 + 0.2 * math.cos(math.atan2(co.y - y, co.x - x) * 10))), sides=12, smooth=False)
    for k in (1, 5):
        zz = z + s * 0.9 * k / 6
        rr = s * (0.30 + 0.07 * math.sin(math.pi * k / 6)) + 0.012
        p.tube([(Vector((x, y, zz - 0.03)), rr, Vector((0, 0, 1))), (Vector((x, y, zz + 0.03)), rr, Vector((0, 0, 1)))],
               lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(nrm.z + 0.4)), sides=12, cap=False, smooth=False)


def star_mark(colour):
    """Brinewake's sail mark: a four-point guiding star inside a ring."""
    def mark(u, v):
        x, y = (u - 0.5) * 1.0, (v - 0.46) * 1.25
        d = math.hypot(x, y)
        a = clamp01((0.045 - abs(d - 0.30)) / 0.022)                  # soft edges: the paint is per vertex
        a = max(a, clamp01((0.235 ** 0.62 * 1.52 - (abs(x) ** 0.62 + abs(y) ** 0.62)) / 0.07))
        return (colour, a) if a > 0.0 else None
    return mark


def sail2(p, ta, tb, ba, bb, billow, base, mark=None, stripe=None, nu=38, nv=32, seams=7):
    """Square sail: sewn panels that puff between the seams, a deep belly, a rising foot, grime toward the bottom."""
    ta, tb, ba, bb, billow = Vector(ta), Vector(tb), Vector(ba), Vector(bb), Vector(billow)
    bdir = billow.normalized()

    def point(u, v):
        pt = ta.lerp(tb, u).lerp(ba.lerp(bb, u), v)
        belly = math.sin(math.pi * u) ** 0.8 * math.sin(math.pi * (0.10 + 0.84 * v)) ** 0.9
        puff = 0.09 * abs(math.sin(math.pi * u * seams)) * math.sin(math.pi * v)
        pt = pt + billow * belly + bdir * puff
        pt.z += 0.45 * math.sin(math.pi * u) * v ** 3
        return pt

    def colour(u, v):
        c = base if stripe is None or int(u * seams) % 2 == 0 else stripe
        seam = abs(math.sin(math.pi * u * seams))
        c = lerp(lerp(c, SAIL_DARK, 0.45), c, clamp01(seam * 3.2))
        c = lerp(c, (1.0, 0.97, 0.88), 0.22 * math.sin(math.pi * u) * math.sin(math.pi * v))
        if mark:
            m = mark(u, v)
            if m:
                c = lerp(c, m[0], m[1] * 0.92)
        c = lerp(c, (0.50, 0.43, 0.33), clamp01((v - 0.72) * 1.5) * 0.55)
        n = noise.noise(Vector((u * 7.0, v * 7.0, 3.3)))
        return lerp(c, (c[0] * 0.84, c[1] * 0.83, c[2] * 0.80), clamp01(n * 1.1))

    verts = [[p.bm.verts.new(point(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = p.bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            f.smooth = True
            for loop, (uu, vv) in zip(f.loops, ((i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv))):
                loop[p.col] = lin(colour(uu, vv))
    return point


def crows_nest(p, x, z, seed):
    r = 0.80
    ngon(p, [Vector((x + math.cos(a) * r, math.sin(a) * r, z)) for a in (2 * math.pi * k / 14 for k in range(14))], lambda co, nrm: lerp(DECK_A, DECK_B, 0.4))
    ngon(p, [Vector((x + math.cos(a) * r, math.sin(a) * r, z - 0.06)) for a in (2 * math.pi * k / 14 for k in range(13, -1, -1))], lambda co, nrm: lerp(DECK_A, WOOD_DARK, 0.6))
    for k in range(14):
        a = 2 * math.pi * (k + 0.5) / 14
        m = Matrix.Rotation(a, 4, 'Z')
        plank(p, (0, 0, 0), (0.05, 2 * math.pi * r / 14 * 0.84, 0.78), seed + k, rot=Matrix.Translation((x, 0, z + 0.36)) @ m @ Matrix.Translation((r, 0, 0)), grey=0.2)
    for zz in (z + 0.12, z + 0.70):
        pipe(p, [Vector((x + math.cos(a) * (r + 0.04), math.sin(a) * (r + 0.04), zz)) for a in (2 * math.pi * k / 14 for k in range(14))], 0.035,
             lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(nrm.z + 0.4)), closed=True)
    for k in range(4):
        a = math.pi / 4 + math.pi * k / 2
        spar(p, (x, 0, z - 1.0), (x + math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, z - 0.05), 0.05, 0.04, seed + 30 + k, sides=5)


def ship3(name, length, beam, masts, guns, seed, trim, sail_base, mark_col, stripe=None, free=3.0, sheer_amp=1.15, bulge=0.22,
          bluff=3.0, step=0.85, qd=1.55, mast_k=None):
    """free = rail height amidships, sheer_amp = how far bow and stern sweep up, bulge = belly and tumblehome of the sides,
    bluff = fullness of the bow, step = extra bulwark round the quarterdeck, qd = quarterdeck height over the main deck."""
    rnd = random.Random(seed)
    p = Prop(name)
    draft, th = 1.55 + length * 0.011 + (free - 2.15) * 0.6, 0.15
    n, rows = 32, 10
    zd = free - 0.78                     # main deck, level so it is easy to walk
    zh = zd - 2.10                       # hold floor
    zq = zd + qd                         # quarterdeck
    zc = zd - 0.70                       # stern cabin floor, stepped down for headroom
    tq = 0.25                            # quarterdeck runs from the stern to here

    def x_at(t):
        return -length / 2 + length * t

    def half(t):
        stern = 1.0 - 0.30 * (1.0 - min(1.0, (t + 0.06) / 0.38)) ** 2.0
        bow = 1.0 - max(0.0, (t - 0.60) / 0.40) ** bluff
        return beam / 2 * stern * bow

    def wprof(s):                                                    # fat belly above the waterline, sides lean back in to the rail
        return s ** 0.36 * (1.0 + bulge * math.sin(math.pi * s)) if s > 0.0 else 0.0

    def sheer0(t):
        return free + sheer_amp * (2 * t - 1) ** 2 * (1.35 if t > 0.5 else 1.0)

    def sheer(t):                                                    # the rail steps up round the quarterdeck
        return sheer0(t) + step * (1.0 - smooth_step(tq - 0.035, tq + 0.035, t))

    def keel(t):
        return -draft * (1.0 - max(0.0, (t - 0.72) / 0.28) ** 2.0)

    def outer(t, s, side):
        return Vector((x_at(t), side * half(t) * wprof(s), keel(t) + (sheer0(t) - keel(t)) * s ** 1.5 + (sheer(t) - sheer0(t)) * smooth_step(0.74, 1.0, s)))

    def inner(t, s, side):
        o = outer(t, s, side)
        return Vector((o.x, side * max(0.0, abs(o.y) - th), o.z + th * (1.0 - s)))

    def s_at(t, z):
        return clamp01((z - keel(t)) / max(sheer0(t) - keel(t), 0.01)) ** (1 / 1.5)

    def inside(t, z):
        return max(0.0, half(t) * wprof(s_at(t, z)) - th)

    def t_of(x):
        return (x + length / 2) / length

    ts = [i / n for i in range(n + 1)]
    gun_list = []
    for gi in range(guns):
        gt = (0.40 + 0.26 * (gi // 2) / max(1, guns // 2 - 1)) if guns > 2 else 0.42
        gun_list.append((round(gt * n) / n, -1 if gi % 2 == 0 else 1))

    def port(i, side):
        return any(sd == side and abs((i + 0.5) / n - tg) < 1.05 / n for tg, sd in gun_list)

    # --- planking: lapped strakes outside, ceiling planks inside, rubbing wales, a broad cap rail
    for k in range(rows):
        s0, s1 = k / rows, (k + 1) / rows
        zmid = keel(0.4) + (sheer0(0.4) - keel(0.4)) * ((s0 + s1) / 2) ** 1.5
        if zmid < -0.25:
            tint = lerp(TAR, WEED, clamp01((zmid + 0.9) / 0.7) * 0.6)
        elif zmid < 0.30:
            tint = BOOT
        elif k >= rows - 2:
            tint = trim
        else:
            tint = lerp(wood_tint(seed + k * 5), (0.50, 0.30, 0.16), 0.35)
        for side in (-1, 1):
            a = [outer(t, s0, side) + Vector((0, side * 0.032, 0)) for t in ts]
            b = [outer(t, s1, side) for t in ts]
            for i in range(n):
                if k == rows - 1 and port(i, side):
                    continue
                grain = 0.5 + 0.5 * math.sin(i * 1.7 + k * 2.3)
                c = lerp(lerp(tint, WOOD_DARK, 0.30), tint, 0.55 + 0.45 * grain)
                fquad(p, [a[i], a[i + 1], b[i + 1], b[i]] if side > 0 else [a[i + 1], a[i], b[i], b[i + 1]],
                      lambda co, nrm, c=c: lerp(c, lerp(c, EDGE_LIT, 0.35), clamp01(nrm.z * 1.5)), smooth=True)
                fquad(p, [a[i] + Vector((0, 0, -0.04)), a[i + 1] + Vector((0, 0, -0.04)), a[i + 1], a[i]], lerp(tint, (0.04, 0.03, 0.03), 0.75))
            tin = lerp(wood_tint(seed + 40 + k), (0.76, 0.62, 0.44), 0.45)
            ia, ib = [inner(t, s0, side) for t in ts], [inner(t, s1, side) for t in ts]
            for i in range(n):
                if k == rows - 1 and port(i, side):
                    continue
                fquad(p, [ib[i], ib[i + 1], ia[i + 1], ia[i]] if side > 0 else [ib[i + 1], ib[i], ia[i], ia[i + 1]],
                      lambda co, nrm, tin=tin: lerp(lerp(tin, WOOD_DARK, 0.45), tin, clamp01((co.z - zh) / 2.4)), smooth=True)
    for side in (-1, 1):
        for sw, rad in ((0.60, 0.085), (0.84, 0.07)):
            pipe(p, [outer(t, sw, side) + Vector((0, side * 0.035, 0)) for t in ts[:-1]] + [outer(0.995, sw, side)], rad,
                 lambda co, nrm: lerp(lerp(OCHRE, WOOD_DARK, 0.5), lerp(OCHRE, (1.0, 0.86, 0.5), 0.3), clamp01(nrm.z * 0.6 + 0.55)), sides=6)
        o = [outer(t, 1.0, side) + Vector((0, side * 0.11, 0.07)) for t in ts]
        i_ = [inner(t, 1.0, side) + Vector((0, -side * 0.09, 0.07)) for t in ts]
        for i in range(n):
            if port(i, side):
                continue
            fquad(p, [i_[i], i_[i + 1], o[i + 1], o[i]] if side < 0 else [o[i], o[i + 1], i_[i + 1], i_[i]], lerp(BONE, (1.0, 0.95, 0.80), 0.3))
            for edge in (o, i_):
                fquad(p, [edge[i] + Vector((0, 0, -0.11)), edge[i + 1] + Vector((0, 0, -0.11)), edge[i + 1], edge[i]], lerp(BONE, WOOD_DARK, 0.35))
    s9 = (rows - 1) / rows
    for tg, side in gun_list:                                        # port jambs and sill close the wall thickness
        t0, t1 = tg - 1 / n, tg + 1 / n
        jamb = lerp(trim, WOOD_DARK, 0.45)
        for te in (t0, t1):
            fquad(p, [outer(te, s9, side), outer(te, 1.0, side), inner(te, 1.0, side), inner(te, s9, side)], jamb)
        fquad(p, [outer(t0, s9, side), outer(t1, s9, side), inner(t1, s9, side), inner(t0, s9, side)], lerp(OCHRE, WOOD_DARK, 0.3))
    pts = [inner(0, k / rows, -1) + Vector((th, 0, 0)) for k in range(rows + 1)] + [inner(0, k / rows, 1) + Vector((th, 0, 0)) for k in range(rows, -1, -1)]
    ngon(p, list(reversed(pts)), lambda co, nrm: lerp(WOOD_DARK, lerp(wood_tint(seed + 60), (0.5, 0.3, 0.16), 0.3), clamp01(0.35 + co.z / free)))
    for k in range(rows):                                            # transom planked in the same strakes as the sides
        zmid = keel(0.4) + (sheer0(0.4) - keel(0.4)) * ((k + 0.5) / rows) ** 1.5
        if zmid < -0.25:
            tint = lerp(TAR, WEED, clamp01((zmid + 0.9) / 0.7) * 0.6)
        elif zmid < 0.30:
            tint = BOOT
        elif k >= rows - 2:
            tint = trim
        else:
            tint = lerp(wood_tint(seed + k * 5 + 3), (0.50, 0.30, 0.16), 0.35)
        lo_a, lo_b, hi_a, hi_b = outer(0, k / rows, -1), outer(0, k / rows, 1), outer(0, (k + 1) / rows, -1), outer(0, (k + 1) / rows, 1)
        for j in range(8):
            c = lerp(lerp(tint, WOOD_DARK, 0.30), tint, 0.55 + 0.45 * (0.5 + 0.5 * math.sin(j * 2.1 + k * 1.3)))
            fquad(p, [lo_a.lerp(lo_b, j / 8), hi_a.lerp(hi_b, j / 8), hi_a.lerp(hi_b, (j + 1) / 8), lo_a.lerp(lo_b, (j + 1) / 8)], c)
        fquad(p, [lo_a + Vector((-0.03, 0, 0)), lo_a + Vector((-0.03, 0, 0.05)), lo_b + Vector((-0.03, 0, 0.05)), lo_b + Vector((-0.03, 0, 0))], lerp(tint, (0.04, 0.03, 0.03), 0.75))
    gilt = lambda co, nrm: lerp(lerp(OCHRE, WOOD_DARK, 0.45), lerp(OCHRE, (1.0, 0.86, 0.5), 0.35), clamp01(nrm.z * 0.6 + 0.55))
    frame = [outer(0, 0.50 + 0.05 * k, -1) + Vector((-0.05, 0, 0)) for k in range(11)] + [outer(0, 1.0 - 0.05 * k, 1) + Vector((-0.05, 0, 0)) for k in range(11)]
    pipe(p, frame, 0.10, gilt, sides=6, up=Vector((1, 0, 0)))
    wz = zd + 1.42
    wy = max(0.0, half(0) * wprof(s_at(0, wz)) - 0.12)
    pipe(p, [Vector((x_at(0) - 0.06, -wy + 2 * wy * k / 8, wz + 0.16 * math.sin(math.pi * k / 8))) for k in range(9)], 0.085, gilt, sides=6, up=Vector((1, 0, 0)))
    wy = max(0.0, half(0) * wprof(s_at(0, zd + 0.02)) - 0.12)
    pipe(p, [Vector((x_at(0) - 0.06, -wy, zd + 0.02)), Vector((x_at(0) - 0.06, wy, zd + 0.02))], 0.085, gilt, sides=6, up=Vector((1, 0, 0)))
    # stem post sweeping up past the rail into a carved, gilded scroll
    path = [Vector((x_at(t) + 0.05, 0, keel(t) - 0.10)) for t in (0.72, 0.80, 0.88, 0.94, 0.98)]
    xb, zb = x_at(1.0) + 0.16, sheer(1.0)
    path += [Vector((xb, 0, keel(1.0) * 0.5 + 0.1)), Vector((xb + 0.10, 0, zb * 0.5)), Vector((xb + 0.22, 0, zb + 0.2)), Vector((xb + 0.30, 0, zb + 0.75))]
    pipe(p, path, [0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.19, 0.18, 0.16], shade(lerp(WOOD_DARK, WOOD_LIGHT, 0.35)), sides=8, up=Vector((0, 1, 0)))
    c0 = Vector((xb + 0.12, 0, zb + 1.05))
    spiral = [c0 + Vector((math.cos(a), 0, math.sin(a))) * (0.36 - 0.05 * k) for k, a in enumerate(math.radians(-55 + 62 * k) for k in range(7))]
    pipe(p, [Vector((xb + 0.30, 0, zb + 0.75))] + spiral, [0.16, 0.15, 0.14, 0.13, 0.12, 0.10, 0.08, 0.06],
         lambda co, nrm: lerp(GOLD_LO, GOLD_HI, clamp01(nrm.z * 0.5 + 0.55)), sides=8, up=Vector((0, 1, 0)))
    # --- frames: a rib every other station, standing proud of the ceiling
    for i in range(2, n - 1, 2):
        t = ts[i]
        tint = lerp(wood_tint(seed + 300 + i), WOOD_DARK, 0.30)
        for side in (-1, 1):
            a = [inner(t, 0.04 + 0.92 * j / 9, side) for j in range(10)]
            b = [v + Vector((0, -side * 0.11, 0.02)) for v in a]
            for j in range(9):
                for dx in (-0.065, 0.065):
                    fquad(p, [a[j] + Vector((dx, 0, 0)), a[j + 1] + Vector((dx, 0, 0)), b[j + 1] + Vector((dx, 0, 0)), b[j] + Vector((dx, 0, 0))], tint)
                fquad(p, [b[j] + Vector((-0.065, 0, 0)), b[j + 1] + Vector((-0.065, 0, 0)), b[j + 1] + Vector((0.065, 0, 0)), b[j] + Vector((0.065, 0, 0))], lerp(tint, EDGE_LIT, 0.3))

    # --- decks: separate boards with staggered butts, a waterway against the hull, beams underneath
    def deck(z, t0, t1, dseed, hole=None, beams=True):
        w = 0.27
        nl = int(beam / w / 2) + 1
        for lane in range(-nl, nl + 1):
            y = lane * w
            x = x_at(t0)
            nxt = x + rnd.uniform(0.5, 3.0)
            while x < x_at(t1) - 0.02:
                xe = min(x_at(t1), nxt)
                tint = lerp(DECK_A, DECK_B, rnd.uniform(0.0, 1.0))
                xs = x
                while xs < xe - 1e-4:
                    x2 = min(xe, xs + 0.7)
                    tm = t_of((xs + x2) / 2)
                    lim = inside(tm, z) - 0.01
                    ya, yb = max(-lim, y - w / 2 + 0.009), min(lim, y + w / 2 - 0.009)
                    if yb - ya > 0.03 and not (hole and hole[0] < tm < hole[1] and abs(y - hole[2]) < hole[3]):
                        g0, g1 = (0.009 if xs == x else 0.0), (0.009 if x2 == xe else 0.0)
                        fquad(p, [Vector((xs + g0, ya, z)), Vector((x2 - g1, ya, z)), Vector((x2 - g1, yb, z)), Vector((xs + g0, yb, z))],
                              lambda co, nrm, tint=tint, lim=lim: lerp(lerp(tint, (tint[0] * 0.8, tint[1] * 0.78, tint[2] * 0.74), 0.5 + 0.5 * math.sin(co.x * 6.0 + co.y * 31.0)),
                                                                     WOOD_DARK, 0.4 * clamp01((abs(co.y) - lim + 0.55) / 0.55)))
                        fquad(p, [Vector((xs, yb + 0.009, z - 0.05)), Vector((x2, yb + 0.009, z - 0.05)), Vector((x2, ya - 0.009, z - 0.05)), Vector((xs, ya - 0.009, z - 0.05))],
                              lerp(tint, WOOD_DARK, 0.7))
                    xs = x2
                x = xe
                nxt = x + rnd.uniform(2.0, 3.4)
        tr = [t0 + (t1 - t0) * k / 24 for k in range(25)]
        for side in (-1, 1):                                        # waterway plank hides the stepped board ends
            a = [Vector((x_at(t), side * (inside(t, z) + 0.03), z + 0.014)) for t in tr]
            b = [Vector((x_at(t), side * max(0.0, inside(t, z) - 0.22), z + 0.014)) for t in tr]
            for k in range(24):
                fquad(p, [a[k], a[k + 1], b[k + 1], b[k]] if side < 0 else [b[k], b[k + 1], a[k + 1], a[k]], lerp(DECK_A, WOOD_DARK, 0.35))
        if beams:
            x = x_at(t0) + 0.5
            while x < x_at(t1) - 0.3:
                tm = t_of(x)
                wdt = inside(tm, z - 0.16) * 2
                if wdt > 0.6 and not (hole and hole[0] - 0.012 < tm < hole[1] + 0.012):
                    plank(p, (x, 0, z - 0.16), (0.17, wdt, 0.20), dseed + int(x * 10) % 97, grey=0.15)
                x += 1.2

    hatch = (0.555, 0.645, 0.95, 0.52)
    deck(zd, tq - 0.004, 0.985, seed + 400, hole=hatch)
    deck(zh, 0.10, 0.86, seed + 500, beams=False)
    deck(zq, 0.0, tq, seed + 600)
    deck(zc, 0.0, tq, seed + 650, beams=False)                      # stern cabin floor, three steps down from the main deck
    hx0, hx1, hyc, hw = x_at(hatch[0]), x_at(hatch[1]), hatch[2], hatch[3]
    for (cx, cy, sx, sy) in (((hx0 + hx1) / 2, hyc + hw, hx1 - hx0 + 0.2, 0.1), ((hx0 + hx1) / 2, hyc - hw, hx1 - hx0 + 0.2, 0.1),
                             (hx0, hyc, 0.1, 2 * hw), (hx1, hyc, 0.1, 2 * hw)):
        plank(p, (cx, cy, zd + 0.10), (sx, sy, 0.20), seed + 700 + int(cx * 3 + cy), grey=0.15)
    steps = 9
    run = (hx1 - hx0 + 1.2) / steps
    for k in range(steps):
        plank(p, (hx1 - 0.15 - run * (k + 0.5), hyc, zd - (zd - zh) * (k + 1) / (steps + 1)), (run * 0.95, 0.92, 0.06), seed + 720 + k, grey=0.3)
    for sy in (-0.5, 0.5):
        ax, bx = Vector((hx1 - 0.1, hyc + sy, zd - 0.1)), Vector((hx1 - 0.15 - run * steps, hyc + sy, zh + 0.05))
        m = Matrix.Translation((ax + bx) / 2) @ Matrix.Rotation(-math.atan2(bx.z - ax.z, bx.x - ax.x), 4, 'Y')
        plank(p, (0, 0, 0), ((bx - ax).length, 0.06, 0.2), seed + 740, rot=m, grey=0.2)
    # --- quarterdeck: bulkhead with a doorway, a stair each side, rails all round
    xq = x_at(tq)
    wq = inside(tq, zd + 0.5)
    k, y = 0, -wq + 0.13
    while y < wq - 0.1:
        if abs(y) > 0.52:
            plank(p, (xq, y, zc + (zq - zc) / 2), (0.06, 0.25, zq - zc), seed + 800 + k, grey=rnd.uniform(0.2, 0.45))
        k += 1
        y += 0.27
    plank(p, (xq, 0, zq - 0.10), (0.14, 2 * wq, 0.20), seed + 830, grey=0.1)
    for k in range(3):
        plank(p, (xq - 0.20 - 0.27 * k, 0, zd - 0.175 * (k + 1)), (0.27, 1.0, 0.06), seed + 832 + k, grey=0.3)
    fquad(p, [Vector((xq - 0.03, -0.52, zc)), Vector((xq - 0.03, 0.52, zc)), Vector((xq - 0.03, 0.52, zd)), Vector((xq - 0.03, -0.52, zd))], lerp(DECK_A, WOOD_DARK, 0.5))
    for side in (-1, 1):
        for sidx in range(6):
            plank(p, (xq + 0.15 + 0.25 * sidx, side * (wq - 0.62), zq - (zq - zd) * (sidx + 0.5) / 6.5), (0.25, 0.85, 0.06), seed + 840 + sidx, grey=0.3)
        lantern(p, (xq + 0.14, side * 0.80, zd + 0.86))

    def rail(pts, hgt, rseed):
        for j, q in enumerate(pts):
            post(p, q.x, q.y, q.z, q.z + hgt, 0.05, rseed + j)
        pipe(p, [q + Vector((0, 0, hgt)) for q in pts], 0.05, shade(BONE), sides=6)

    half_gap = wq - 1.12
    rail([Vector((xq, -half_gap + 2 * half_gap * j / 5, zq)) for j in range(6)], 0.9, seed + 860)
    for side in (-1, 1):
        rail([Vector((x_at(t), side * (inside(t, zq + 0.3) - 0.02), zq)) for t in (0.012, 0.07, 0.13, 0.19, tq - 0.004)], 0.9, seed + 870)
    rail([Vector((x_at(0.012), -inside(0.012, zq + 0.3) + 0.02 + (2 * inside(0.012, zq + 0.3) - 0.04) * j / 5, zq)) for j in range(6)], 0.9, seed + 880)
    # canvas awning over the helm, on four posts and arched ribs
    ax0, ax1, top = x_at(0.045), x_at(tq) - 0.25, zq + 2.15
    aw0, aw1 = inside(0.045, zq + 0.3) - 0.12, inside(tq, zq + 0.3) - 0.12
    for xx, ww in ((ax0, aw0), (ax1, aw1)):
        for side in (-1, 1):
            post(p, xx, side * ww, zq, top, 0.07, seed + 890)
    nu, nv, ribs = 12, 10, 4

    def canvas(u, v):
        ww = aw0 + (aw1 - aw0) * u + 0.12
        yy = -ww + 2 * ww * v
        return Vector((ax0 - 0.15 + (ax1 - ax0 + 0.3) * u, yy, top + 0.42 * math.cos(math.pi * (v - 0.5)) - 0.07 * abs(math.sin(math.pi * u * (ribs - 1)))))

    for i in range(nu):
        for j in range(nv):
            band = lerp(BONE, trim, 0.55) if j % 2 == 0 else BONE
            fquad(p, [canvas(i / nu, j / nv), canvas((i + 1) / nu, j / nv), canvas((i + 1) / nu, (j + 1) / nv), canvas(i / nu, (j + 1) / nv)],
                  lambda co, nrm, band=band: lerp(lerp(band, (0.45, 0.40, 0.32), 0.35), band, clamp01((co.z - top) / 0.4 + 0.3)), smooth=True)
    for r_ in range(ribs):
        u = r_ / (ribs - 1)
        pipe(p, [canvas(u, v / 8) + Vector((0, 0, -0.05)) for v in range(9)], 0.04, shade(lerp(WOOD_DARK, WOOD_LIGHT, 0.4)), sides=5, up=Vector((1, 0, 0)))
    # --- stern: windows, lantern, rudder
    for y in (-4.4, -3.3, -2.2, -1.1, 0.0, 1.1, 2.2, 3.3, 4.4):          # tall leaded stern windows, lit from the cabin
        if abs(y) < half(0) * wprof(s_at(0, zd + 0.3)) - 0.60:
            p.box((x_at(0) - 0.03, y, zd + 0.72), (0.05, 0.84, 1.04), lambda co, nrm: lerp((1.0, 0.56, 0.14), (1.0, 0.93, 0.58), clamp01((co.z - zd - 0.25) * 1.2)), bevel=0.02)
            for dz in (0.17, 0.72, 1.27):
                p.box((x_at(0) - 0.08, y, zd + dz), (0.07, 1.0, 0.09), lerp_const(OCHRE, 0.2), bevel=0.015)
            for dy in (-0.46, 0.0, 0.46):
                p.box((x_at(0) - 0.08, y + dy, zd + 0.72), (0.07, 0.07 if dy else 0.045, 1.14), lerp_const(OCHRE, 0.2), bevel=0.015)
            for dz in (0.45, 1.0):
                p.box((x_at(0) - 0.075, y, zd + dz), (0.04, 0.86, 0.035), lerp_const(OCHRE, 0.35))
    post(p, x_at(0) + 0.12, 0, zq, zq + 2.85, 0.055, seed + 900)
    lantern(p, (x_at(0) + 0.12, 0, zq + 3.0))
    plank(p, (x_at(0) - 0.34, 0, (keel(0) + 0.6) / 2), (0.66, 0.10, 0.6 - keel(0)), seed + 910, grey=0.1)
    for zz in (keel(0) * 0.6, -0.1):
        p.box((x_at(0) - 0.1, 0, zz), (0.3, 0.16, 0.10), lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(nrm.z + 0.3)), bevel=0.02)
    # --- helm, binnacle, capstan, guns, anchor, deck clutter, side ladder
    wheel_at(p, x_at(0.11), 0, zq, seed + 920)
    plank(p, (x_at(0.11) + 0.78, 0, zq + 0.42), (0.36, 0.36, 0.84), seed + 930, grey=0.1)
    p.blob((x_at(0.11) + 0.78, 0, zq + 0.9), (0.15, 0.15, 0.09), lambda co, nrm: lerp(GOLD_LO, GOLD_HI, clamp01(nrm.z + 0.4)), 3, 0.0, 2, smooth=True)
    cx = x_at(0.84)
    rings = [(Vector((cx, 0, zd + z)), r, Vector((0, 0, 1))) for z, r in ((0, 0.44), (0.12, 0.44), (0.2, 0.30), (0.75, 0.24), (0.85, 0.38), (1.0, 0.38))]
    p.tube(rings, lambda co, nrm: lerp(WOOD_DARK, WOOD_LIGHT, clamp01(0.3 + 0.4 * nrm.z + (co.z - zd) * 0.3)), sides=10, smooth=False)
    for j in range(6):
        a = math.pi * j / 3
        spar(p, (cx, 0, zd + 0.92), (cx + math.cos(a) * 1.05, math.sin(a) * 1.05, zd + 0.92), 0.045, 0.035, seed + 940 + j, sides=5)
    for i, (t, side) in enumerate(gun_list):
        cannon_at(p, x_at(t), side * (inside(t, zd + 0.3) - 0.9), zd, side * math.pi / 2, seed + 950 + i)
        for j in range(4):
            p.blob((x_at(t) + 0.6 + 0.19 * (j % 2), side * (inside(t, zd + 0.2) - 0.3 - 0.19 * (j // 2)), zd + 0.09), (0.085, 0.085, 0.085),
                   lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(nrm.z * 0.7 + 0.2)), j, 0.0, 2, smooth=True)
    iron = lambda co, nrm: lerp(IRON_DARK, IRON_LIGHT, clamp01(0.3 + 0.7 * nrm.z))
    am = Matrix.Translation((x_at(0.90), -(half(0.90) + 0.20), sheer(0.90) - 1.0)) @ Matrix.Rotation(0.15, 4, 'X')
    p.box((0, 0, 0), (0.12, 0.12, 1.7), iron, bevel=0.03, xform=am)
    p.box((0, 0, 0), (0.9, 0.1, 0.1), iron, bevel=0.03, xform=am @ Matrix.Translation((0, 0, 0.75)))
    for s in (-1, 1):
        p.box((0, 0, 0), (0.7, 0.12, 0.14), iron, bevel=0.03, xform=am @ Matrix.Translation((s * 0.3, 0, -0.75)) @ Matrix.Rotation(s * 0.7, 4, 'Y'))
    rope(p, (x_at(0.90), -(half(0.90) + 0.20), sheer(0.90) - 0.15), (x_at(0.90), -(inside(0.90, zd + 0.9)), sheer(0.90) + 0.12), 0.04)
    rope(p, (x_at(0.90), -(inside(0.90, zd + 0.9)), sheer(0.90) + 0.12), (cx, -0.3, zd + 0.45), 0.04, sag=0.25)
    coil(p, x_at(0.72), -(inside(0.72, zd) - 0.55), zd)
    coil(p, x_at(0.30), inside(0.30, zd) - 0.5, zd)
    for (t, yf) in ((0.76, 0.55), (0.33, -0.6)):
        bx, by = x_at(t), yf * inside(t, zd)
        p.tube([(Vector((bx, by, zd)), 0.15, Vector((0, 0, 1))), (Vector((bx, by, zd + 0.32)), 0.19, Vector((0, 0, 1)))], shade(wood_tint(seed + int(t * 50))), sides=10, smooth=False)
    keg(p, x_at(0.68), inside(0.68, zd) - 0.5, zd, 1.0, seed + 960)
    keg(p, x_at(0.70), inside(0.70, zd) - 1.15, zd, 0.85, seed + 961)
    tl = 0.36
    for j in range(6):
        s = s_at(tl, 0.25) + (0.93 - s_at(tl, 0.25)) * j / 5
        q = outer(tl, s, 1)
        plank(p, (q.x, q.y + 0.07, q.z), (0.46, 0.12, 0.07), seed + 970 + j, grey=0.1)
    # --- rig: masts stepped on the keel, crow's nest, yards, sewn sails, shrouds with ratlines, stays and braces
    tip = Vector((x_at(1.0) + length * 0.18, 0, sheer(1.0) + 1.7))
    spar(p, (x_at(0.90), 0, zd + 0.5), tip, 0.15, 0.06, seed + 1000)
    stern_top = Vector((x_at(0) + 0.12, 0, zq + 2.85))
    top_prev = None
    for i, t in enumerate(masts):
        h = length * (mast_k[i] if mast_k else (0.86 if len(masts) == 1 else 0.68 - 0.07 * i))
        mx = x_at(t)
        mr = 0.30 + length * 0.004
        spar(p, (mx, 0, keel(t) + 0.2), (mx, 0, zd + h), mr, 0.12, seed + 1100 + i * 10, sides=10)
        for zz in (zd + 0.07, zd + h * 0.24, zd + h * 0.62):
            rr = mr + 0.04 - (zz - zd) * (mr - 0.12) / h
            p.tube([(Vector((mx, 0, zz - 0.06)), rr, Vector((0, 0, 1))), (Vector((mx, 0, zz + 0.06)), rr, Vector((0, 0, 1)))], iron, sides=10, cap=False, smooth=False)
        crows_nest(p, mx, zd + h * 0.80, seed + 1150 + i * 40)
        yard = beam * 1.34
        phi = math.radians(26.0)
        cph, sph = math.cos(phi), math.sin(phi)

        def br(x, y, z):
            return Vector((mx + (x - mx) * cph - y * sph, (x - mx) * sph + y * cph, z))

        top, bot = zd + h * 0.74, zd + h * 0.23
        spar(p, br(mx + 0.30, -yard / 2, top), br(mx + 0.30, yard / 2, top), 0.11, 0.08, seed + 1101 + i, sides=7)
        spar(p, br(mx + 0.30, -yard * 0.47, bot), br(mx + 0.30, yard * 0.47, bot), 0.09, 0.08, seed + 1102 + i, sides=6)
        sail2(p, br(mx + 0.36, -yard * 0.48, top - 0.06), br(mx + 0.36, yard * 0.48, top - 0.06), br(mx + 0.36, -yard * 0.46, bot + 0.05), br(mx + 0.36, yard * 0.46, bot + 0.05),
              (h * 0.14 * cph, h * 0.14 * sph, 0), sail_base, mark=star_mark(mark_col) if i == len(masts) // 2 else None, stripe=stripe,
              nu=64 if i == len(masts) // 2 else 38, nv=52 if i == len(masts) // 2 else 32)
        for k in range(9):                                          # robands lashing the sail head to the yard
            yy = -yard * 0.46 + yard * 0.92 * k / 8
            pipe(p, [br(mx + 0.30 + math.cos(a) * 0.13, yy, top + math.sin(a) * 0.13) for a in (2 * math.pi * q / 8 for q in range(8))], 0.02, shade(ROPE_C), sides=4,
                 up=Vector((-sph, cph, 0)), closed=True)
        head = Vector((mx, 0, zd + h * 0.78))
        for side in (-1, 1):
            foot = [Vector((mx + dx, side * (half(t) + 0.06), sheer(t) + 0.1)) for dx in (-1.0, -0.1, 0.8)]
            for f in foot:
                rope(p, f, head + Vector((0, side * 0.14, 0)), 0.03)
                p.box((f.x, f.y, f.z + 0.1), (0.1, 0.07, 0.2), shade(WOOD_DARK, 0.7), bevel=0.02)
            for j in range(1, 10):
                u = j / 11
                rope(p, foot[0].lerp(head, u), foot[2].lerp(head, u), 0.016)
            rope(p, br(mx + 0.30, side * yard * 0.47, bot), Vector((mx - 2.4, side * (half(t - 0.14) + 0.03), sheer(t - 0.14) + 0.12)), 0.022, sag=0.2)
            rope(p, br(mx + 0.30, side * yard / 2, top), Vector((mx - 3.2, side * (half(t - 0.2) + 0.03), sheer(t - 0.2) + 0.12)), 0.02, sag=0.35)
            rope(p, br(mx + 0.30, side * yard / 2, top), Vector((mx, 0, zd + h * 0.97)), 0.02)
        masthead = Vector((mx, 0, zd + h))
        if i == 0:
            rope(p, masthead + Vector((0, 0, -0.5)), tip, 0.03)
            rope(p, Vector((mx, 0, zd + h * 0.62)), tip.lerp(Vector((x_at(0.90), 0, zd + 0.5)), 0.45), 0.026)
        if top_prev is not None:
            rope(p, masthead, top_prev, 0.026)
        top_prev = masthead
        fl = masthead + Vector((0, 0, 0.1))
        post(p, mx, 0, zd + h - 0.1, zd + h + 0.9, 0.03, seed + 1190)
        cloth(p, [fl + Vector((0, 0, 0.75)), fl + Vector((-1.9, 0.05, 0.62)), fl + Vector((-1.35, 0.03, 0.42)), fl + Vector((-1.9, 0.05, 0.22)), fl + Vector((0, 0, 0.1))], mark_col)
    rope(p, top_prev, stern_top, 0.026)
    fm = x_at(masts[0])
    fh = length * (mast_k[0] if mast_k else (0.86 if len(masts) == 1 else 0.68))
    head = Vector((fm + 0.35, 0, zd + fh * 0.90))
    sail2(p, head, head, tip + Vector((-0.5, 0, 0.05)), Vector((fm + 1.4, 1.1, zd + 2.0)), (0.0, 0.85, 0.0), sail_base, nu=16, nv=20, seams=4)
    rope(p, Vector((fm + 1.4, 1.1, zd + 2.0)), Vector((fm - 1.0, inside(masts[0] - 0.06, zd + 0.5), zd + 0.9)), 0.022, sag=0.15)
    # --- hold: casks, crates, chart table, hammocks, galley stove, hanging lamps
    for j, (t, yf) in enumerate(((0.30, -0.5), (0.34, 0.45), (0.38, -0.55), (0.70, 0.5), (0.74, -0.4), (0.46, -0.62))):
        keg(p, x_at(t), yf * inside(t, zh + 0.4), zh, rnd.uniform(0.95, 1.2), seed + 1300 + j)
    for j, (t, yf, s) in enumerate(((0.66, -0.55, 0.7), (0.62, -0.5, 0.6), (0.665, -0.5, 0.5))):
        plank(p, (x_at(t), yf * inside(t, zh + 0.4), zh + s / 2 + (0.7 if j == 2 else 0.0)), (s, s, s), seed + 1320 + j, grey=0.2)
    tx = x_at(0.20)
    plank(p, (tx, 0, zh + 0.82), (1.5, 1.0, 0.07), seed + 1340, grey=0.25)
    for sx in (-0.62, 0.62):
        for sy in (-0.4, 0.4):
            plank(p, (tx + sx, sy, zh + 0.4), (0.09, 0.09, 0.8), seed + 1341, grey=0.25, bevel=0.0)
    fquad(p, [Vector((tx - 0.5, -0.35, zh + 0.865)), Vector((tx + 0.5, -0.35, zh + 0.865)), Vector((tx + 0.5, 0.35, zh + 0.865)), Vector((tx - 0.5, 0.35, zh + 0.865))],
          lambda co, nrm: lerp((0.92, 0.84, 0.64), (0.72, 0.60, 0.40), clamp01(abs(co.x - tx) * 1.6)))
    for (t0, yc) in ((0.40, -1.0), (0.50, -1.05)):                    # hammocks slung between the frames
        xa, xb2 = x_at(t0), x_at(t0) + 1.9
        hang = zd - 0.55
        a = [Vector((xa + (xb2 - xa) * u / 8, yc - 0.32 * math.sin(math.pi * u / 8), hang - 0.55 * math.sin(math.pi * u / 8))) for u in range(9)]
        b = [Vector((v.x, yc + 0.32 * math.sin(math.pi * u / 8), v.z)) for u, v in enumerate(a)]
        strip(p, a, b, lambda co, nrm: lerp((0.55, 0.46, 0.34), BONE, clamp01((co.z - hang + 0.55) / 0.55)), smooth=True)
        rope(p, a[0], a[0] + Vector((-0.25, 0, 0.5)), 0.02)
        rope(p, a[-1], a[-1] + Vector((0.25, 0, 0.5)), 0.02)
    sx_ = x_at(0.79)
    p.box((sx_, 0.0, zh + 0.45), (0.7, 0.7, 0.6), iron, bevel=0.05)
    p.box((sx_ - 0.36, 0.0, zh + 0.42), (0.03, 0.34, 0.26), lambda co, nrm: lerp((1.0, 0.42, 0.08), (1.0, 0.86, 0.35), clamp01((co.z - zh - 0.3) * 4)))
    for q in ((-0.28, -0.28), (0.28, -0.28), (-0.28, 0.28), (0.28, 0.28)):
        p.box((sx_ + q[0], q[1], zh + 0.08), (0.08, 0.08, 0.16), iron)
    pipe(p, [Vector((sx_ + 0.2, 0.2, zh + 0.75)), Vector((sx_ + 0.2, 0.2, zd - 0.3)), Vector((sx_ + 0.45, 0.2, zd + 0.9))], 0.08, iron, sides=7, up=Vector((0, 1, 0)))
    p.tube([(Vector((sx_ - 0.05, -0.05, zh + 0.76)), 0.17, Vector((0, 0, 1))), (Vector((sx_ - 0.05, -0.05, zh + 0.98)), 0.20, Vector((0, 0, 1)))], iron, sides=10, smooth=False)
    for t in (0.30, 0.48, 0.70):
        p.box((x_at(t), -1.0, zd - 0.44), (0.02, 0.02, 0.36), lambda co, nrm: IRON_DARK)
        lantern(p, (x_at(t), -1.0, zd - 0.74))
    # stern cabin: bunk, sea chest, desk
    plank(p, (x_at(0.05), -(inside(0.05, zc + 0.4) - 0.5), zc + 0.35), (1.9, 0.8, 0.14), seed + 1400, grey=0.2)
    fquad(p, [Vector((x_at(0.05) - 0.9, -(inside(0.05, zc + 0.4) - 0.14), zc + 0.43)), Vector((x_at(0.05) + 0.9, -(inside(0.05, zc + 0.4) - 0.14), zc + 0.43)),
              Vector((x_at(0.05) + 0.9, -(inside(0.05, zc + 0.4) - 0.86), zc + 0.43)), Vector((x_at(0.05) - 0.9, -(inside(0.05, zc + 0.4) - 0.86), zc + 0.43))], lerp(trim, BONE, 0.35))
    plank(p, (x_at(0.16), inside(0.16, zc + 0.4) - 0.5, zc + 0.28), (0.9, 0.55, 0.55), seed + 1410, grey=0.1)
    p.box((x_at(0.16), inside(0.16, zc + 0.4) - 0.5, zc + 0.58), (0.96, 0.6, 0.07), shade(OCHRE), bevel=0.02)
    plank(p, (x_at(0.06), inside(0.06, zc + 0.4) - 0.55, zc + 0.78), (1.2, 0.7, 0.07), seed + 1420, grey=0.2)
    for sx in (-0.5, 0.5):
        plank(p, (x_at(0.06) + sx, inside(0.06, zc + 0.4) - 0.55, zc + 0.38), (0.08, 0.6, 0.76), seed + 1421, grey=0.2, bevel=0.0)
    p.export()


def lerp_const(c, dark):
    return lambda co, nrm: lerp(c, WOOD_DARK, dark)


# Short, broad and high-sided: length is about 2.4 to 3 beams, so the hulls read as chunky rather than stretched.
ONLY = globals().get("BW_ONLY")
if not ONLY or "Sloop" in ONLY:
    ship3("SM_BW_Sloop", 19.0, 8.0, (0.50,), 2, 11, (0.13, 0.42, 0.46), SAIL_LIGHT, (0.10, 0.34, 0.40), free=3.0)
if not ONLY or "Brigantine" in ONLY:
    ship3("SM_BW_Brigantine", 27.5, 9.8, (0.66, 0.38), 4, 23, (0.58, 0.13, 0.11), SAIL_LIGHT, (0.52, 0.10, 0.09), stripe=(0.80, 0.30, 0.22), free=3.3, qd=1.7)
if not ONLY or "Galleon" in ONLY:
    ship3("SM_BW_Galleon", 37.0, 12.6, (0.76, 0.52, 0.31), 8, 37, (0.15, 0.20, 0.36), SAIL_LIGHT, (0.80, 0.60, 0.16), free=3.9, sheer_amp=1.5, step=1.1, qd=1.9,
          mast_k=(0.56, 0.66, 0.50))
