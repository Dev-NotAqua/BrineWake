# Brinewake vegetation: palms, broad-leaf jungle plants, bushes, ferns, grasses, flowers, vines, trees, deadwood, reef growth.
# Run after a_lib.py through bl_run.py. Leaves are single-sided cards: give foliage a two-sided material in the engine.
WANT = globals().get("BW_ONLY")
G_DEEP, G_MID, G_TIP = (0.03, 0.20, 0.09), (0.11, 0.46, 0.13), (0.56, 0.74, 0.17)
G_BLUE = ((0.05, 0.22, 0.18), (0.16, 0.44, 0.34), (0.50, 0.70, 0.46))
G_DRY = ((0.30, 0.24, 0.08), (0.62, 0.52, 0.20), (0.86, 0.78, 0.42))
G_DARK = ((0.02, 0.13, 0.07), (0.06, 0.30, 0.12), (0.26, 0.52, 0.16))
G_LIME = ((0.08, 0.28, 0.06), (0.30, 0.58, 0.10), (0.78, 0.86, 0.26))
BARK_A, BARK_B = (0.17, 0.11, 0.08), (0.52, 0.38, 0.25)


def want(name):
    return not WANT or any(k in name for k in WANT)


def tface(p, items, col, smooth=True):
    """A face from (position, t, u) corners, painted by col(t, u, normal)."""
    f = p.bm.faces.new([p.bm.verts.new(it[0]) for it in items])
    f.smooth = smooth
    f.normal_update()
    for loop, it in zip(f.loops, items):
        loop[p.col] = lin(col(it[1], it[2], f.normal))
    return f


def leafcol(pal=(G_DEEP, G_MID, G_TIP), rib=0.30, k=1.0, dry=0.0):
    deep, mid, tip = pal

    def col(t, u, nrm):
        c = lerp(deep, mid, clamp01(t * 2.0)) if t < 0.5 else lerp(mid, tip, clamp01((t - 0.5) * 2.0))
        c = lerp(lerp(c, tip, rib), c, u)
        if dry:
            c = lerp(c, (0.66, 0.52, 0.18), dry * clamp01(t * 1.4 - 0.2 + u * 0.4))
        return mul(c, k * (0.70 + 0.30 * clamp01(abs(nrm.z) + 0.25)))
    return col


def leaf(p, root, d, length, width, col, droop=0.3, segs=6, fold=0.25, peak=0.4, jag=0.0, twist=0.0, rnd=None, lift=0.0, wave=0.0):
    """Broad leaf: a curving midrib with the two halves folded up in a V. peak = where it is widest (0..1)."""
    root, d = Vector(root), Vector(d).normalized()
    side = d.cross(UP)
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    if twist:
        side = Quaternion(d, twist) @ side
    upv = side.cross(d)
    rows = []
    for i in range(segs + 1):
        t = i / segs
        c = root + d * (length * t) + UP * (lift * length * math.sin(math.pi * t * 0.5) - droop * length * t * t) + side * (wave * width * math.sin(t * 9.0))
        w = max(0.0, math.sin(math.pi / 2 * t / peak)) ** 0.7 if t < peak else max(0.0, math.cos(math.pi / 2 * (t - peak) / (1 - peak))) ** 0.9
        w = width * max(w, 0.04)
        if jag and i % 2 == 1:
            w *= 1.0 - jag * (rnd.uniform(0.4, 1.0) if rnd else 1.0)
        rows.append((c, c + side * w + upv * (fold * w), c - side * w + upv * (fold * w), t))
    for (c0, l0, r0, t0), (c1, l1, r1, t1) in zip(rows, rows[1:]):
        tface(p, [(c0, t0, 0), (l0, t0, 1), (l1, t1, 1), (c1, t1, 0)], col)
        tface(p, [(c0, t0, 0), (c1, t1, 0), (r1, t1, 1), (r0, t0, 1)], col)


def blade(p, root, d, length, width, col, bend=0.3, segs=3, face=None):
    """A grass blade: a tapering strip that bows over."""
    root, d = Vector(root), Vector(d).normalized()
    side = (face or d.cross(UP))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side = side.normalized()
    over = side.cross(UP).normalized() if abs(d.z) > 0.99 else Vector((d.x, d.y, 0)).normalized()
    rows = []
    for i in range(segs + 1):
        t = i / segs
        c = root + d * (length * t) + over * (bend * length * t * t) - UP * (bend * 0.5 * length * t ** 3)
        w = width * (1.0 - t) ** 0.7 + 0.004
        rows.append((c - side * w, c + side * w, t))
    for (a0, b0, t0), (a1, b1, t1) in zip(rows, rows[1:]):
        tface(p, [(a0, t0, 1), (b0, t0, 1), (b1, t1, 1), (a1, t1, 1)], col)


def bark(seed=0, lo=BARK_A, hi=BARK_B, moss=0.0, height=3.0):
    def paint(co, nrm):
        g = noise.noise(Vector((co.x * 3.0 + seed, co.y * 3.0, co.z * 0.55)))
        c = lerp(lo, hi, clamp01(0.45 + 0.6 * g + 0.25 * nrm.z))
        if moss:
            c = lerp(c, (0.20, 0.38, 0.12), moss * clamp01(nrm.z * 0.8 + 0.5 - co.z / height + 0.4 * noise.noise(co * 1.3)))
        return lerp((0.10, 0.09, 0.07), c, clamp01(0.35 + co.z / 0.5))
    return paint


def stalk(p, pts, radii, colour, sides=5):
    pipe(p, pts, radii, colour, sides=sides, up=Vector((0.37, 0.91, 0.1)))


def tuft(p, centre, radius, seed, n, pal, leaf_len=0.5, leaf_w=0.16, up=0.5, fold=0.3, rib=0.3, droop=0.35, peak=0.45):
    """Leaves bursting out of a ball: roots just inside the surface, tips well outside."""
    rnd = random.Random(seed)
    centre = Vector(centre)
    for k in range(n):
        z = rnd.uniform(-0.15, 1.0) ** 1.0
        a = rnd.uniform(0, 6.28)
        rr = math.sqrt(max(0.0, 1.0 - min(1.0, abs(z)) ** 2))
        d = Vector((math.cos(a) * rr, math.sin(a) * rr, z * (0.75 + up)))
        d.normalize()
        root = centre + Vector((d.x * radius, d.y * radius, d.z * radius * 0.8)) * 0.72
        leaf(p, root, d + Vector((0, 0, rnd.uniform(-0.1, 0.3))), leaf_len * rnd.uniform(0.75, 1.25), leaf_w * rnd.uniform(0.8, 1.2), leafcol(pal, rib, rnd.uniform(0.82, 1.12)),
             droop=droop * rnd.uniform(0.6, 1.4), segs=4, fold=fold, peak=peak, twist=rnd.uniform(-0.5, 0.5))


def mass(p, centre, size, seed, pal, rough=0.30, subdiv=2):
    """The dark leafy body inside a bush or tree crown, so nothing shows through."""
    deep, mid, tip = pal
    z0, zh = centre[2] - size[2], 2.0 * size[2]
    faces = p.blob(centre, size, const((0, 0, 0)), seed, rough=rough, subdiv=subdiv, smooth=True)
    p.paint(faces, lambda co, nrm: lerp(mul(deep, 0.75), lerp(mid, tip, 0.25), clamp01((co.z - z0) / zh * 0.75 + 0.30 * nrm.z + 0.22 * noise.noise(co * 2.2))))


def flower(p, at, d, r, petal, heart=(0.98, 0.80, 0.20), petals=5, cup=0.35):
    at, d = Vector(at), Vector(d).normalized()
    s = d.cross(UP)
    if s.length < 1e-3:
        s = Vector((1, 0, 0))
    s.normalize()
    u = s.cross(d)
    for k in range(petals):
        a = 2 * math.pi * k / petals
        out = s * math.cos(a) + u * math.sin(a)
        tan = d.cross(out)
        tip = at + out * r + d * (r * cup)
        mid_l, mid_r = at + out * (r * 0.55) + tan * (r * 0.34) + d * (r * cup * 0.4), at + out * (r * 0.55) - tan * (r * 0.34) + d * (r * cup * 0.4)
        tface(p, [(at, 0, 0), (mid_r, 0.6, 1), (tip, 1, 1), (mid_l, 0.6, 1)], lambda t, uu, nrm: lerp(mul(petal, 0.62), petal, clamp01(t * 1.2)), smooth=False)
    p.blob(tuple(at + d * (r * 0.14)), (r * 0.2, r * 0.2, r * 0.2), const(heart), 1, 0.0, 1, smooth=True)


# ------------------------------------------------------------------ palms and big leaves
def banana(name, seed, height=2.6, leaves=8, fruit=True):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    lean = Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0))
    stem = lambda co, nrm: lerp((0.30, 0.24, 0.10), (0.50, 0.62, 0.24), clamp01(co.z / height + 0.25 * math.sin(co.z * 9.0) + 0.2 * noise.noise(co * 5.0)))
    pts = [lean * (height * t * t) + Vector((0, 0, height * t)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
    pipe(p, pts, [0.20, 0.17, 0.15, 0.13, 0.10], stem, sides=9)
    top = pts[-1]
    for k in range(leaves):
        a = 2 * math.pi * k / leaves + rnd.uniform(-0.3, 0.3)
        rise = rnd.uniform(0.25, 1.3) if k % 2 else rnd.uniform(-0.1, 0.5)
        d = Vector((math.cos(a), math.sin(a), rise))
        L = rnd.uniform(1.7, 2.5) * height / 2.6
        leaf(p, top + Vector((0, 0, -0.05)), d, L, L * 0.20, leafcol((G_DEEP, G_MID, G_TIP) if k % 3 else G_LIME, 0.4, rnd.uniform(0.85, 1.1), dry=0.5 if rise < 0.1 else 0.0),
             droop=rnd.uniform(0.35, 0.7), segs=10, fold=0.22, peak=0.45, jag=0.32, rnd=rnd, lift=0.25)
    leaf(p, top, Vector((0.1, 0.1, 1)), height * 0.55, 0.12, leafcol(G_LIME, 0.3), droop=0.05, segs=5, fold=0.8, peak=0.5)
    if fruit:
        a = rnd.uniform(0, 6.28)
        hang = [top + Vector((0, 0, -0.1)), top + Vector((math.cos(a) * 0.35, math.sin(a) * 0.35, -0.15)), top + Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, -0.75))]
        stalk(p, hang, [0.04, 0.035, 0.03], const((0.34, 0.40, 0.16)))
        for row in range(3):
            c = hang[1].lerp(hang[2], 0.35 + 0.25 * row)
            for j in range(7):
                q = 2 * math.pi * j / 7 + row
                o = Vector((math.cos(q), math.sin(q), 0))
                stalk(p, [c + o * 0.04, c + o * 0.13 + Vector((0, 0, 0.04)), c + o * 0.15 + Vector((0, 0, 0.17))], [0.03, 0.036, 0.02],
                      lambda co, nrm, row=row: lerp((0.42, 0.56, 0.14), (0.96, 0.82, 0.20), 0.3 + 0.3 * row), 5)
        p.blob(tuple(hang[2] + Vector((0, 0, -0.12))), (0.07, 0.07, 0.14), const((0.46, 0.14, 0.30)), 1, 0.05, 2, smooth=True)
    p.export()


def big_leaf(name, seed, n=7, size=1.0, pal=None):
    """Elephant-ear plant: heart-shaped leaves on long arching stalks."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or (G_DEEP, G_MID, G_TIP)
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.35, 0.35)
        out = Vector((math.cos(a), math.sin(a), 0))
        h = rnd.uniform(0.7, 1.5) * size
        reach = rnd.uniform(0.35, 0.8) * size
        top = out * reach + Vector((0, 0, h))
        stalk(p, [out * 0.05, out * (reach * 0.35) + Vector((0, 0, h * 0.6)), top], [0.035 * size, 0.028 * size, 0.02 * size], const(lerp(pal[1], (0.42, 0.50, 0.20), 0.5)))
        L = rnd.uniform(0.7, 1.1) * size
        leaf(p, top - out * (L * 0.18), out + Vector((0, 0, rnd.uniform(-0.75, -0.2))), L, L * 0.40, leafcol(pal, 0.45, rnd.uniform(0.85, 1.12)), droop=0.12, segs=6, fold=0.16,
             peak=0.26, twist=rnd.uniform(-0.3, 0.3), wave=0.03)
    p.export()


def fern(name, seed, n=12, size=1.0, pal=None):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or (G_DEEP, G_MID, G_TIP)

    def colour(t):
        return lerp(pal[0], pal[1], clamp01(t * 2.2)) if t < 0.45 else lerp(pal[1], pal[2], clamp01((t - 0.45) / 0.55))
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        rise = rnd.uniform(0.5, 1.5) if k % 2 else rnd.uniform(0.15, 0.7)
        frond(p, Vector((0, 0, 0.04)), Vector((math.cos(a), math.sin(a), rise)), rnd.uniform(0.9, 1.5) * size, rnd.uniform(0.5, 0.95), colour, leaflets=11, width=0.26 * size, rnd=rnd)
    for k in range(3):                                               # curled young fiddleheads
        a = rnd.uniform(0, 6.28)
        o = Vector((math.cos(a), math.sin(a), 0))
        pts = [o * 0.04, o * 0.08 + Vector((0, 0, 0.3 * size))] + [o * 0.08 + Vector((0, 0, 0.36 * size)) + (o * math.cos(q) + UP * math.sin(q)) * 0.06 * size for q in (2.6, 1.6, 0.6, -0.6, -1.8)]
        stalk(p, pts, [0.018, 0.016, 0.014, 0.012, 0.011, 0.01, 0.008], const(lerp(pal[1], pal[2], 0.6)), 4)
    p.export()


def bush(name, seed, radius=0.9, leaves=70, pal=None, bloom=None, lumps=3, leaf_len=0.5, leaf_w=0.17):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or (G_DEEP, G_MID, G_TIP)
    spots = [(0.0, 0.0, radius * 0.55, radius)]
    for k in range(lumps - 1):
        a = rnd.uniform(0, 6.28)
        r = radius * rnd.uniform(0.5, 0.75)
        spots.append((math.cos(a) * radius * 0.75, math.sin(a) * radius * 0.75, r * 0.55, r))
    for k, (x, y, z, r) in enumerate(spots):
        mass(p, (x, y, z), (r * 0.80, r * 0.80, r * 0.62), seed + k, pal)
        tuft(p, (x, y, z), r * 0.9, seed + 10 + k, int(leaves * r / radius / (1 + 0.5 * (lumps - 1))) + 8, pal, leaf_len * r / 0.9, leaf_w * r / 0.9)
        if bloom:
            for j in range(int(6 * r / radius) + 2):
                a, zz = rnd.uniform(0, 6.28), rnd.uniform(0.15, 1.0)
                rr = math.sqrt(1 - zz * zz)
                d = Vector((math.cos(a) * rr, math.sin(a) * rr, zz))
                flower(p, Vector((x, y, z)) + Vector((d.x * r, d.y * r, d.z * r * 0.72)) * 1.02, d, 0.12 * r / 0.9 + 0.03, bloom[j % len(bloom)])
    p.export()


def grass(name, seed, blades=26, height=0.55, spread=0.32, pal=None, heads=False, width=0.035):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or ((0.06, 0.26, 0.08), (0.24, 0.56, 0.14), (0.66, 0.80, 0.24))
    for k in range(blades):
        a, d = rnd.uniform(0, 6.28), spread * math.sqrt(rnd.random())
        root = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        out = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.05, 0.55) * (0.4 + d / spread)
        h = height * rnd.uniform(0.55, 1.2)
        kk = rnd.uniform(0.8, 1.15)
        blade(p, root, out + UP, h, width * rnd.uniform(0.7, 1.3), lambda t, u, nrm, kk=kk: mul(lerp(pal[0], pal[1], clamp01(t * 2)) if t < 0.5 else lerp(pal[1], pal[2], (t - 0.5) * 2), kk),
              bend=rnd.uniform(0.15, 0.5), segs=3, face=Vector((math.cos(a + 1.57 + rnd.uniform(-0.6, 0.6)), math.sin(a + 1.57), 0)))
        if heads and k % 4 == 0:
            top = root + (out + UP).normalized() * h * 1.05
            stalk(p, [root, root.lerp(top, 0.6), top], 0.006, const(pal[1]), 3)
            lathe(p, [(0.004, 0.0), (0.02, 0.03), (0.022, 0.12), (0.004, 0.17)], const((0.80, 0.70, 0.38)), at=top, sides=5)
    p.export()


def flowers(name, seed, n=9, petal=((0.86, 0.14, 0.16),), height=0.5, spread=0.4):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), spread * math.sqrt(rnd.random())
        root = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        h = height * rnd.uniform(0.6, 1.2)
        top = root + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), h))
        stalk(p, [root, root.lerp(top, 0.5) + Vector((0.02, 0.02, 0)), top], 0.01, const((0.20, 0.44, 0.14)), 4)
        flower(p, top, Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 1)), rnd.uniform(0.07, 0.11), petal[k % len(petal)], petals=5 + k % 2)
        for j in range(2):
            q = rnd.uniform(0, 6.28)
            leaf(p, root.lerp(top, 0.25 + 0.2 * j), Vector((math.cos(q), math.sin(q), 0.5)), 0.2, 0.05, leafcol(), droop=0.5, segs=3)
    for k in range(10):
        a, d = rnd.uniform(0, 6.28), spread * math.sqrt(rnd.random())
        blade(p, (math.cos(a) * d, math.sin(a) * d, 0), Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)), height * 0.6, 0.03, lambda t, u, nrm: lerp((0.06, 0.26, 0.08), (0.44, 0.68, 0.18), t))
    p.export()


def reeds(name, seed, n=14, height=1.9, spread=0.5):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), spread * math.sqrt(rnd.random())
        root = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        h = height * rnd.uniform(0.6, 1.1)
        top = root + Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), h))
        if k % 2 == 0:
            stalk(p, [root, root.lerp(top, 0.5), top], [0.014, 0.012, 0.008], const((0.36, 0.48, 0.18)), 4)
            lathe(p, [(0.004, 0.0), (0.03, 0.02), (0.032, 0.22), (0.01, 0.24), (0.006, 0.34)], lambda co, nrm: lerp((0.20, 0.11, 0.06), (0.50, 0.30, 0.14), clamp01(nrm.z + 0.5)),
                  at=top.lerp(root, 0.12), sides=6)
        else:
            blade(p, root, top - root, h, 0.03, lambda t, u, nrm: lerp((0.10, 0.28, 0.10), (0.56, 0.70, 0.26), t), bend=rnd.uniform(0.05, 0.3), segs=4)
    p.export()


def vines(name, seed, width=3.0, drop=3.2, strands=11, pal=None):
    """A curtain of hanging creepers. Origin on the ledge they hang from, everything below it."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or (G_DEEP, G_MID, G_TIP)
    for k in range(strands):
        x = -width / 2 + width * (k + rnd.uniform(0.2, 0.8)) / strands
        L = drop * rnd.uniform(0.35, 1.0)
        y0 = rnd.uniform(-0.15, 0.15)
        pts = [Vector((x + 0.10 * math.sin(t * 5.0 + k), y0 - 0.12 * math.sin(t * 3.1 + k * 2), -L * t)) for t in (j / 7 for j in range(8))]
        stalk(p, pts, [0.024 - 0.002 * j for j in range(8)], lambda co, nrm: lerp((0.14, 0.20, 0.08), (0.34, 0.42, 0.16), clamp01(nrm.z + 0.5)), 4)
        for j in range(1, 8):
            for sgn in (-1, 1):
                d = Vector((sgn * rnd.uniform(0.5, 1.0), rnd.uniform(-1.0, 0.2), rnd.uniform(-0.6, 0.1)))
                leaf(p, pts[j], d, rnd.uniform(0.16, 0.28), 0.08, leafcol(pal, 0.3, rnd.uniform(0.8, 1.15)), droop=0.5, segs=3, fold=0.2, peak=0.35)
        if k % 3 == 0:
            flower(p, pts[-1], Vector((0, -1, -0.4)), 0.08, (0.80, 0.30, 0.62))
    p.export()


def creeper(name, seed, radius=1.4, runners=7):
    """Ground ivy patch."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(runners):
        a = 2 * math.pi * k / runners + rnd.uniform(-0.3, 0.3)
        pts = []
        for j in range(7):
            t = j / 6
            aa = a + 0.5 * math.sin(t * 4.0 + k)
            pts.append(Vector((math.cos(aa) * radius * t, math.sin(aa) * radius * t, 0.03 + 0.04 * math.sin(t * 9.0))))
        stalk(p, pts, 0.014, const((0.20, 0.28, 0.10)), 3)
        for j in range(1, 7):
            for sgn in (-1, 1):
                q = a + sgn * rnd.uniform(0.6, 1.6)
                leaf(p, pts[j], Vector((math.cos(q), math.sin(q), 0.35)), rnd.uniform(0.16, 0.26), 0.09, leafcol(G_DARK if (j + k) % 3 else G_LIME, 0.35, rnd.uniform(0.85, 1.15)),
                     droop=0.4, segs=3, peak=0.35)
    p.export()


# ------------------------------------------------------------------ trees and deadwood
def limb(p, a, d, length, r, depth, rnd, paint, tips, spread=0.75, rise=0.15, forks=(2, 3)):
    pts = [Vector(a)]
    dd = Vector(d).normalized()
    for i in range(3):
        dd = (dd + Vector((rnd.uniform(-0.28, 0.28), rnd.uniform(-0.28, 0.28), rnd.uniform(-0.05, 0.22)))).normalized()
        pts.append(pts[-1] + dd * (length / 3))
    pipe(p, pts, [r, r * 0.86, r * 0.72, r * 0.58], paint, sides=7 if depth > 1 else 5, up=Vector((0.37, 0.91, 0.1)))
    if depth > 0:
        for k in range(rnd.randint(*forks)):
            nd = (dd + Vector((rnd.uniform(-spread, spread), rnd.uniform(-spread, spread), rnd.uniform(-0.1, 0.5) + rise))).normalized()
            limb(p, pts[rnd.choice((2, 3))], nd, length * rnd.uniform(0.62, 0.8), r * 0.56, depth - 1, rnd, paint, tips, spread, rise, forks)
    else:
        tips.append(pts[-1])


def roots(p, r, seed, paint, n=6, reach=1.6):
    rnd = random.Random(seed)
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        o = Vector((math.cos(a), math.sin(a), 0))
        L = reach * rnd.uniform(0.6, 1.1)
        pipe(p, [o * (r * 0.5) + Vector((0, 0, r * 2.2)), o * (r * 1.1) + Vector((0, 0, r * 1.0)), o * (r + L * 0.5) + Vector((0, 0, r * 0.35)), o * (r + L) + Vector((0, 0, -0.08))],
             [r * 0.62, r * 0.5, r * 0.34, r * 0.14], paint, sides=6, up=Vector((-o.y, o.x, 0)))


def tree(name, seed, height=7.0, r=0.45, pal=None, crowns=True, depth=2, lean=0.15, charred=False, moss=0.4):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or G_DARK
    paint = bark(seed, (0.06, 0.05, 0.05), (0.24, 0.20, 0.19), 0.0, height) if charred else bark(seed, moss=moss, height=height)
    a = rnd.uniform(0, 6.28)
    ld = Vector((math.cos(a), math.sin(a), 0)) * lean
    trunk_h = height * (0.42 if crowns else 0.5)
    pts = [ld * (trunk_h * t * t) + Vector((0.12 * math.sin(t * 5.0 + seed), 0.12 * math.cos(t * 4.0 + seed), trunk_h * t - 0.15)) for t in (j / 5 for j in range(6))]
    pipe(p, pts, [r * 1.25, r * 1.0, r * 0.88, r * 0.80, r * 0.74, r * 0.70], paint, sides=9)
    roots(p, r, seed, paint, 6, r * 3.2)
    tips = []
    for k in range(4 if crowns else 3):
        q = a + 2 * math.pi * k / 4 + rnd.uniform(-0.4, 0.4)
        limb(p, pts[-1] - Vector((0, 0, rnd.uniform(0.0, trunk_h * 0.25))), Vector((math.cos(q), math.sin(q), rnd.uniform(0.5, 1.2))), height * rnd.uniform(0.34, 0.46), r * 0.55, depth, rnd,
             paint, tips)
    if crowns:
        chosen = tips[::max(1, len(tips) // 7)]
        for k, tip in enumerate(chosen):
            cr = height * rnd.uniform(0.15, 0.21)
            mass(p, tuple(tip + Vector((0, 0, cr * 0.2))), (cr, cr, cr * 0.66), seed + k * 3, pal, rough=0.34, subdiv=3)
            tuft(p, tuple(tip + Vector((0, 0, cr * 0.2))), cr * 1.05, seed + 40 + k, 34, pal, leaf_len=cr * 0.55, leaf_w=cr * 0.19, up=0.2)
        for k in range(3):                                            # a few creepers hanging off the boughs
            tip = chosen[k % len(chosen)]
            L = rnd.uniform(1.0, 2.4)
            pts2 = [tip + Vector((0.1 * math.sin(j), 0.1 * math.cos(j * 1.3), -L * j / 5)) for j in range(6)]
            stalk(p, pts2, 0.015, const((0.20, 0.30, 0.10)), 3)
            for j in range(1, 6):
                leaf(p, pts2[j], Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), -0.3)), 0.2, 0.07, leafcol(G_LIME, 0.3), droop=0.4, segs=3)
    elif charred:
        for tip in tips[::3]:
            p.blob(tuple(tip), (0.06, 0.06, 0.06), const((1.0, 0.45, 0.08)), 1, 0.2, 1)
    p.export()


def mangrove(name, seed, height=4.5):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    paint = bark(seed, (0.20, 0.15, 0.12), (0.55, 0.46, 0.36), 0.2, height)
    hub = Vector((0, 0, 1.5))
    for k in range(9):
        a = 2 * math.pi * k / 9 + rnd.uniform(-0.2, 0.2)
        o = Vector((math.cos(a), math.sin(a), 0))
        reach = rnd.uniform(1.0, 1.9)
        pipe(p, [hub + Vector((0, 0, 0.2)), hub + o * (reach * 0.45) + Vector((0, 0, 0.25)), o * (reach * 0.9) + Vector((0, 0, 0.75)), o * reach + Vector((0, 0, -0.3))], [0.13, 0.11, 0.09, 0.06],
             paint, sides=6, up=Vector((-o.y, o.x, 0)))
    pipe(p, [hub, hub + Vector((0.15, 0.1, 1.0)), hub + Vector((0.05, 0.25, 2.0))], [0.26, 0.21, 0.17], paint, sides=8)
    tips = []
    for k in range(4):
        q = 2 * math.pi * k / 4 + rnd.uniform(-0.4, 0.4)
        limb(p, hub + Vector((0.05, 0.25, 1.9)), Vector((math.cos(q), math.sin(q), 0.7)), height * 0.42, 0.13, 1, rnd, paint, tips)
    for k, tip in enumerate(tips[::2]):
        cr = rnd.uniform(0.8, 1.15)
        mass(p, tuple(tip), (cr, cr, cr * 0.55), seed + k, (G_DEEP, G_MID, G_TIP), subdiv=2)
        tuft(p, tuple(tip), cr, seed + 30 + k, 26, (G_DEEP, G_MID, G_TIP), leaf_len=0.5, leaf_w=0.15, up=0.1)
    p.export()


def stump(name, seed, r=0.5, h=0.7, shrooms=True):
    if not want(name):
        return
    p = Prop(name)
    paint = bark(seed, moss=0.5, height=h * 1.5)
    rnd = random.Random(seed)
    loops = []
    for i, (rr, z) in enumerate(((1.45, -0.1), (1.12, 0.12), (1.0, 0.4), (0.96, 1.0))):
        loops.append([Vector((math.cos(q) * r * rr * (1 + 0.10 * math.sin(k * 2.3 + seed)), math.sin(q) * r * rr * (1 + 0.10 * math.cos(k * 1.7 + seed)), z * h + (0.06 * math.sin(k * 1.9) if i == 3 else 0)))
                      for k, q in enumerate(2 * math.pi * k / 11 for k in range(11))])
    skin(p, loops, paint, smooth=True, cap=False)
    top = loops[-1]
    mid = sum(top, Vector()) / 11
    fan(p, top, mid, UP, lambda co, nrm: lerp((0.78, 0.62, 0.38), (0.48, 0.34, 0.20), clamp01(abs(math.sin((co - mid).length * 26.0)) * 0.7 + 0.15)))
    roots(p, r * 0.85, seed, paint, 5, r * 2.0)
    if shrooms:
        for k in range(5):
            a = rnd.uniform(0, 6.28)
            mushroom(p, (math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, rnd.uniform(0.1, h * 0.7)), rnd.uniform(0.08, 0.16), (math.cos(a), math.sin(a), 0.7), (0.86, 0.60, 0.26))
    p.export()


def mushroom(p, at, s, d=(0, 0, 1), cap_col=(0.74, 0.16, 0.12), spots=False):
    m = zto(at, d)
    lathe(p, [(0.22 * s, 0.0), (0.16 * s, 0.25 * s), (0.14 * s, 0.9 * s)], lambda co, nrm: lerp((0.62, 0.56, 0.44), (0.96, 0.92, 0.80), clamp01(nrm.z + 0.6)), sides=7, m=m, cap=False)
    lathe(p, [(0.15 * s, 0.86 * s), (0.72 * s, 0.82 * s), (0.78 * s, 0.94 * s), (0.60 * s, 1.20 * s), (0.30 * s, 1.36 * s), (0.004, 1.40 * s)],
          lambda co, nrm: lerp(mul(cap_col, 0.5), lerp(cap_col, (1, 0.9, 0.7), 0.25), clamp01(nrm.z * 0.8 + 0.3)), sides=9, m=m, cap=False)
    if spots:
        for k in range(5):
            a = 2 * math.pi * k / 5
            q = m @ Vector((math.cos(a) * 0.48 * s, math.sin(a) * 0.48 * s, 1.24 * s))
            p.blob(tuple(q), (0.09 * s, 0.09 * s, 0.05 * s), const((0.98, 0.95, 0.86)), k, 0.0, 1, smooth=True)


def mushrooms(name, seed, n=7, cap_col=(0.74, 0.16, 0.12), spots=True, size=0.3):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), 0.45 * math.sqrt(rnd.random()) * (0 if k == 0 else 1)
        mushroom(p, (math.cos(a) * d, math.sin(a) * d, 0), size * (1.0 if k == 0 else rnd.uniform(0.3, 0.75)), (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 1), cap_col, spots)
    p.export()


def fallen_log(name, seed, length=4.2, r=0.38, moss=0.6):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    paint0 = bark(seed, moss=0.0, height=1.0)

    def paint(co, nrm):
        c = paint0(Vector((co.x, co.y, 1.0)), nrm)
        return lerp(c, lerp((0.16, 0.34, 0.10), (0.42, 0.58, 0.18), clamp01(noise.noise(co * 2.0) + 0.5)), moss * clamp01(nrm.z * 1.6 - 0.2 + 0.5 * noise.noise(co * 0.9)))
    pts = [Vector((-length / 2 + length * t, 0.25 * math.sin(t * 3.0 + seed), r * 0.85 + 0.08 * math.sin(t * 4.0))) for t in (j / 6 for j in range(7))]
    rad = [r * (1.0 + 0.10 * math.sin(j * 1.7)) * (1.0 - 0.18 * j / 6) for j in range(7)]
    pipe(p, pts, rad, paint, sides=10, up=UP, cap=False)
    for end, rr, sgn in ((pts[0], rad[0], -1), (pts[-1], rad[-1], 1)):
        ring = [end + Vector((0, math.cos(q) * rr, math.sin(q) * rr)) for q in (2 * math.pi * k / 10 for k in range(10))]
        fan(p, ring, end + Vector((sgn * 0.05, 0, 0)), Vector((sgn, 0, 0)), lambda co, nrm, end=end: lerp((0.20, 0.12, 0.07), (0.70, 0.54, 0.32), clamp01((co - end).length / rr * 0.9)))
    for k in range(3):
        t = rnd.uniform(0.2, 0.8)
        c = pts[int(t * 6)]
        q = rnd.uniform(0.3, 2.8)
        pipe(p, [c, c + Vector((rnd.uniform(-0.2, 0.2), math.cos(q) * 0.7, math.sin(q) * 0.7))], [r * 0.3, r * 0.2], paint0, sides=6)
    for k in range(4):
        t = rnd.uniform(0.15, 0.85)
        c = pts[int(t * 6)]
        mushroom(p, (c.x + rnd.uniform(-0.2, 0.2), c.y - r * 0.8, c.z + rnd.uniform(-0.1, 0.2)), rnd.uniform(0.10, 0.2), (0, -1, 0.5), (0.88, 0.66, 0.30))
    p.export()


def driftwood(name, seed, length=2.6):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pale = lambda co, nrm: lerp((0.42, 0.38, 0.33), (0.86, 0.82, 0.74), clamp01(0.4 + 0.5 * nrm.z + 0.3 * noise.noise(Vector((co.x * 0.8, co.y * 6.0, co.z * 6.0)))))
    pts = [Vector((-length / 2 + length * t, 0.3 * math.sin(t * 3.5 + seed), 0.14 + 0.16 * math.sin(t * 2.5 + seed))) for t in (j / 6 for j in range(7))]
    pipe(p, pts, [0.16, 0.15, 0.13, 0.12, 0.10, 0.08, 0.04], pale, sides=7, up=UP)
    tips = []
    for k in range(3):
        c = pts[2 + k]
        limb(p, c, Vector((rnd.uniform(-0.3, 0.6), rnd.uniform(-1, 1), rnd.uniform(0.2, 1.0))), length * 0.34, 0.07, 1, rnd, pale, tips, forks=(1, 2))
    p.export()


def agave(name, seed, n=16, size=1.0, pal=None):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = pal or G_BLUE
    for k in range(n):
        a = k * 2.399 + rnd.uniform(-0.15, 0.15)
        rise = 0.25 + 1.6 * (k / n) ** 1.5
        L = size * (1.0 - 0.45 * k / n) * rnd.uniform(0.85, 1.1)
        leaf(p, Vector((0, 0, 0.05 + 0.2 * size * k / n)), Vector((math.cos(a), math.sin(a), rise)), L, L * 0.13, leafcol(pal, 0.15, rnd.uniform(0.85, 1.1)), droop=0.12, segs=5, fold=0.55,
             peak=0.22)
    p.export()


def bamboo(name, seed, stalks=7, height=6.0):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(stalks):
        a, d = rnd.uniform(0, 6.28), 0.55 * math.sqrt(rnd.random())
        h = height * rnd.uniform(0.55, 1.0)
        r = rnd.uniform(0.035, 0.06)
        lean = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.02, 0.14)
        base = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        tint = lerp((0.36, 0.52, 0.16), (0.74, 0.70, 0.30), rnd.random())
        segs = int(h / 0.55)
        prof = []
        for j in range(segs):
            z0 = h * j / segs
            prof += [(r * 1.18, z0), (r, z0 + 0.03), (r, z0 + h / segs - 0.03)]
        m = Matrix.Translation(base) @ Matrix.Shear('XY', 4, (lean.x, lean.y))
        lathe(p, prof, lambda co, nrm, tint=tint: lerp(mul(tint, 0.5), tint, clamp01(0.55 + 0.4 * nrm.x + 0.3 * math.sin(co.z * 11.4))), sides=6, m=m)
        for j in range(segs // 2, segs):
            c = m @ Vector((0, 0, h * j / segs))
            for i in range(3):
                q = rnd.uniform(0, 6.28)
                dd = Vector((math.cos(q), math.sin(q), rnd.uniform(-0.1, 0.5)))
                stalk(p, [c, c + dd * 0.35], 0.008, const(tint), 3)
                for e in range(3):
                    leaf(p, c + dd * 0.35, dd + Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), -0.3)), rnd.uniform(0.35, 0.55), 0.05, leafcol(G_LIME, 0.2, rnd.uniform(0.8, 1.1)),
                         droop=0.4, segs=3, peak=0.3)
    p.export()


# ------------------------------------------------------------------ reef and shore life
def seaweed(name, seed, n=9, height=1.6, tint=None):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    pal = tint or ((0.05, 0.16, 0.08), (0.14, 0.36, 0.16), (0.42, 0.58, 0.22))
    for k in range(n):
        a, d = rnd.uniform(0, 6.28), 0.3 * math.sqrt(rnd.random())
        leaf(p, (math.cos(a) * d, math.sin(a) * d, 0), Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 1)), height * rnd.uniform(0.5, 1.1), 0.09, leafcol(pal, 0.2, rnd.uniform(0.8, 1.1)),
             droop=-0.02, segs=8, fold=0.1, peak=0.5, wave=1.4, twist=rnd.uniform(0, 3))
    p.export()


def coral(name, seed, kind='branch', tint=(0.90, 0.36, 0.34), size=1.0):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    col = lambda co, nrm: lerp(mul(tint, 0.45), lerp(tint, (1.0, 0.92, 0.84), clamp01(co.z / (1.1 * size) - 0.35)), clamp01(0.45 + 0.5 * nrm.z + 0.2 * noise.noise(co * 6.0)))
    chunk(p, (0, 0, 0.05), (0.42 * size, 0.36 * size, 0.16 * size), seed, 'grey', pts=10, sub=0)
    if kind == 'branch':
        tips = []
        for k in range(5):
            a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
            limb(p, (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.1), Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1)), 0.9 * size, 0.07 * size, 2, rnd, col, tips, spread=0.6, rise=0.3)
        for tip in tips:
            p.blob(tuple(tip), (0.035 * size, 0.035 * size, 0.035 * size), const(lerp(tint, (1, 1, 0.9), 0.6)), 1, 0.0, 1, smooth=True)
    elif kind == 'fan':
        for k in range(15):
            a = math.pi * (0.1 + 0.8 * k / 14)
            pts = [Vector((0, 0, 0.1))]
            for j in range(1, 6):
                t = j / 5
                pts.append(Vector((math.cos(a) * 0.9 * size * t ** 0.85, 0.05 * math.sin(t * 6 + k), 0.1 + math.sin(a) * 1.1 * size * t ** 0.85)))
            pipe(p, pts, [0.035 * size * (1 - 0.7 * j / 5) for j in range(6)], col, sides=4, up=Vector((0, 1, 0)))
        for j in range(1, 5):
            rr = 1.0 * size * j / 5
            pipe(p, [Vector((math.cos(a) * rr * 0.9, 0, 0.1 + math.sin(a) * rr * 1.1)) for a in (math.pi * (0.12 + 0.76 * q / 10) for q in range(11))], 0.012 * size, col, sides=3, up=Vector((0, 1, 0)))
    elif kind == 'brain':
        faces = p.blob((0, 0, 0.3 * size), (0.55 * size, 0.5 * size, 0.42 * size), const((0, 0, 0)), seed, rough=0.12, subdiv=3, smooth=True)
        p.paint(faces, lambda co, nrm: lerp(mul(tint, 0.5), tint, clamp01(0.5 + 0.5 * math.sin(noise.noise(co * 3.0) * 22.0)) * 0.7 + 0.3 * clamp01(nrm.z)))
    else:                                                            # tubes
        for k in range(8):
            a, d = rnd.uniform(0, 6.28), 0.3 * size * math.sqrt(rnd.random())
            h = size * rnd.uniform(0.35, 1.0)
            r = size * rnd.uniform(0.05, 0.09)
            lathe(p, [(r * 0.7, 0.0), (r, h * 0.7), (r * 1.35, h), (r * 1.0, h), (r * 0.6, h * 0.7), (0.004, h * 0.5)], col, at=(math.cos(a) * d, math.sin(a) * d, 0.08), sides=7,
                  m=None, cap=False)
    p.export()


def shells(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(4):                                               # scallops
        a, d = rnd.uniform(0, 6.28), 0.5 * math.sqrt(rnd.random())
        tint = lerp((0.96, 0.84, 0.74), (0.92, 0.56, 0.46), rnd.random())
        m = at_m(math.cos(a) * d, math.sin(a) * d, 0.01, rnd.uniform(0, 6.28), rnd.uniform(-0.2, 0.2))
        for j in range(8):
            q0, q1 = math.pi * (0.1 + 0.8 * j / 8), math.pi * (0.1 + 0.8 * (j + 1) / 8)
            pts = [m @ Vector((0, 0, 0)), m @ Vector((math.cos(q0) * 0.12, math.sin(q0) * 0.12, 0.0)), m @ Vector((math.cos((q0 + q1) / 2) * 0.10, math.sin((q0 + q1) / 2) * 0.10, 0.045)),
                   m @ Vector((math.cos(q1) * 0.12, math.sin(q1) * 0.12, 0.0))]
            fquad(p, [pts[0], pts[1], pts[2]], tint)
            fquad(p, [pts[0], pts[2], pts[3]], mul(tint, 0.82))
    m = at_m(0.3, -0.2, 0.06, 0.6, 1.3)                               # a conch
    lathe(p, [(0.004, -0.02), (0.05, 0.02), (0.085, 0.09), (0.07, 0.16), (0.045, 0.21), (0.05, 0.23), (0.03, 0.28), (0.034, 0.30), (0.012, 0.36), (0.004, 0.40)],
          lambda co, nrm: lerp((0.82, 0.50, 0.44), (0.99, 0.90, 0.80), clamp01(nrm.z * 0.6 + 0.5)), sides=8, m=m)
    for k in range(2):                                               # starfish
        c = Vector((-0.35 + 0.5 * k, 0.3 - 0.5 * k, 0.015))
        for j in range(5):
            q = 2 * math.pi * j / 5 + k
            o = Vector((math.cos(q), math.sin(q), 0))
            pipe(p, [c, c + o * 0.09 + Vector((0, 0, 0.015)), c + o * 0.18], [0.04, 0.028, 0.008], lambda co, nrm: lerp((0.70, 0.24, 0.10), (0.98, 0.56, 0.20), clamp01(nrm.z + 0.3)), sides=5)
    p.export()


def frond_ground(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(3):
        a = rnd.uniform(0, 6.28)
        frond(p, Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0.08)), Vector((math.cos(a), math.sin(a), 0.06)), rnd.uniform(2.4, 3.2), 0.03,
              lambda t: lerp(leaf_colour(t), FROND_DRY, 0.75), leaflets=12, width=0.7, rnd=rnd)
    for k in range(4):
        a = rnd.uniform(0, 6.28)
        p.blob((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.14), (0.16, 0.16, 0.19), lambda co, nrm: lerp((0.20, 0.12, 0.05), (0.56, 0.40, 0.17), clamp01(nrm.z * 0.6 + 0.5)), k, 0.05, 2, smooth=True)
    p.export()


RED_F, YEL_F, WHT_F, PNK_F, BLU_F = (0.86, 0.14, 0.16), (0.98, 0.78, 0.14), (0.97, 0.95, 0.90), (0.92, 0.42, 0.62), (0.34, 0.46, 0.90)
if want("Palm"):
    for nm, h, lean, bend, sd, fr in (("A", 7.0, 1.6, 0.6, 3, 9), ("B", 9.5, 2.4, 1.1, 8, 9), ("C", 5.2, 0.9, 0.3, 14, 8), ("D", 11.5, 4.6, 1.8, 21, 10), ("E", 3.4, 0.4, 0.15, 27, 7),
                                      ("F", 8.0, 5.2, 0.8, 33, 9)):
        if want("SM_BW_Palm_" + nm):
            palm("SM_BW_Palm_" + nm, h, lean, bend, sd, fr)
banana("SM_BW_Banana_A", 3)
banana("SM_BW_Banana_B", 9, 3.4, 10)
banana("SM_BW_Banana_Young", 15, 1.5, 6, fruit=False)
big_leaf("SM_BW_BigLeaf_A", 4)
big_leaf("SM_BW_BigLeaf_B", 11, 9, 1.5)
big_leaf("SM_BW_BigLeaf_Dark", 17, 6, 1.1, G_DARK)
fern("SM_BW_Fern_A", 5)
fern("SM_BW_Fern_B", 12, 15, 1.5)
fern("SM_BW_Fern_C", 19, 9, 0.7, G_LIME)
bush("SM_BW_Bush_A", 6)
bush("SM_BW_Bush_B", 13, 1.4, 90, G_DARK)
bush("SM_BW_Bush_C", 20, 0.6, 50, G_LIME, lumps=2)
bush("SM_BW_Bush_Flower_A", 23, 1.0, 70, bloom=(RED_F, PNK_F))
bush("SM_BW_Bush_Flower_B", 26, 0.8, 60, G_DARK, bloom=(YEL_F, WHT_F))
bush("SM_BW_Bush_Dry", 29, 0.8, 60, G_DRY, lumps=2)
bush("SM_BW_Hedge_Long", 31, 1.1, 120, lumps=5)
grass("SM_BW_Grass_A", 7)
grass("SM_BW_Grass_B", 14, 40, 0.8, 0.5)
grass("SM_BW_Grass_Tall", 21, 30, 1.4, 0.45, heads=True)
grass("SM_BW_Grass_Dry", 28, 30, 0.9, 0.45, G_DRY, heads=True)
grass("SM_BW_Grass_Short", 35, 34, 0.28, 0.5, width=0.03)
flowers("SM_BW_Flowers_Red", 8, 9, (RED_F,))
flowers("SM_BW_Flowers_Mixed", 15, 12, (YEL_F, WHT_F, PNK_F, BLU_F))
flowers("SM_BW_Flowers_Blue", 22, 8, (BLU_F, WHT_F), 0.7)
reeds("SM_BW_Reeds_A", 9)
reeds("SM_BW_Reeds_B", 16, 22, 2.4, 0.8)
vines("SM_BW_Vines_Hang_A", 10)
vines("SM_BW_Vines_Hang_B", 17, 5.0, 4.5, 17, G_DARK)
creeper("SM_BW_Creeper_A", 24)
tree("SM_BW_Tree_Jungle_A", 11)
tree("SM_BW_Tree_Jungle_B", 18, 9.5, 0.6, (G_DEEP, G_MID, G_TIP), lean=0.3)
tree("SM_BW_Tree_Jungle_C", 25, 5.0, 0.34, G_LIME)
tree("SM_BW_Tree_Dead_A", 32, 6.0, 0.36, crowns=False, depth=3, moss=0.0)
tree("SM_BW_Tree_Dead_B", 39, 4.2, 0.28, crowns=False, depth=2, lean=0.4, moss=0.0)
tree("SM_BW_Tree_Charred", 46, 6.5, 0.40, crowns=False, depth=2, charred=True)
mangrove("SM_BW_Mangrove_A", 12)
mangrove("SM_BW_Mangrove_B", 19, 5.5)
stump("SM_BW_Stump_A", 13)
stump("SM_BW_Stump_B", 20, 0.36, 0.45, shrooms=False)
mushrooms("SM_BW_Mushrooms_Red", 6)
mushrooms("SM_BW_Mushrooms_Brown", 9, 9, (0.62, 0.40, 0.20), False, 0.22)
mushrooms("SM_BW_Mushrooms_Glow", 12, 8, (0.30, 0.86, 0.80), False, 0.26)
fallen_log("SM_BW_Log_Fallen", 14)
fallen_log("SM_BW_Log_Short", 21, 2.2, 0.30, 0.3)
driftwood("SM_BW_Driftwood_A", 15)
driftwood("SM_BW_Driftwood_B", 22, 3.6)
agave("SM_BW_Agave_A", 16)
agave("SM_BW_Agave_B", 23, 22, 1.5, (G_DEEP, G_MID, G_TIP))
bamboo("SM_BW_Bamboo_A", 17)
bamboo("SM_BW_Bamboo_B", 24, 11, 7.5)
seaweed("SM_BW_Seaweed_A", 18)
seaweed("SM_BW_Kelp_A", 25, 7, 3.4, ((0.10, 0.12, 0.04), (0.34, 0.32, 0.10), (0.66, 0.58, 0.20)))
coral("SM_BW_Coral_Branch", 19, 'branch')
coral("SM_BW_Coral_Fan", 26, 'fan', (0.66, 0.30, 0.74))
coral("SM_BW_Coral_Brain", 33, 'brain', (0.94, 0.72, 0.30))
coral("SM_BW_Coral_Tubes", 40, 'tubes', (0.20, 0.66, 0.74))
coral("SM_BW_Coral_Branch_Blue", 47, 'branch', (0.24, 0.44, 0.90), 1.5)
shells("SM_BW_Shells_A", 20)
frond_ground("SM_BW_Palm_Frond_Fallen", 27)
