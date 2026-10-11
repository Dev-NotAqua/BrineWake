# Brinewake outpost dressing: lamps, posts, signs, dock gear, goods and furniture. Run after a_lib.py through bl_run.py.
WANT = globals().get("BW_ONLY")


def want(name):
    return not WANT or any(k in name for k in WANT)


def star_alpha(u, v):
    """Brinewake's mark: a four-point guiding star inside a ring (u, v in 0..1)."""
    x, y = u - 0.5, v - 0.5
    d = math.hypot(x, y)
    a = clamp01((0.045 - abs(d - 0.34)) / 0.02)
    return max(a, clamp01((0.27 ** 0.62 * 1.52 - (abs(x) ** 0.62 + abs(y) ** 0.62)) / 0.06))


def uvsheet(p, pos, col, nu, nv):
    """A cloth: pos(u, v) gives the point, col(u, v, normal) the paint."""
    vs = [[p.bm.verts.new(pos(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = p.bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            f.smooth = True
            f.normal_update()
            for loop, (uu, vv) in zip(f.loops, ((i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv))):
                loop[p.col] = lin(col(uu, vv, f.normal))


def cloth_col(base, trim=OCHRE, mark=None, border=0.07, grime=0.5):
    def col(u, v, nrm):
        c = base
        if trim and (u < border or u > 1 - border or v < border * 0.6):
            c = trim
        if mark:
            c = lerp(c, mark, star_alpha(u, 0.5 + (v - 0.36) * 1.8) * 0.95)
        c = lerp(mul(c, 0.55), c, clamp01(0.55 + 0.6 * abs(nrm.dot(SUN_DIR))))
        return lerp(c, (0.36, 0.30, 0.24), clamp01((v - 0.6) * 1.6) * grime)
    return col


def banner_cloth(p, a, b, drop, base, trim=OCHRE, mark=None, tails=2, wave=0.10, nu=24, nv=40):
    """A banner hung from the bar a-b, its foot cut into tails."""
    a, b = Vector(a), Vector(b)
    side = (b - a).normalized().cross(UP)

    def pos(u, v):
        foot = drop * (1.0 - 0.16 * abs(math.sin(math.pi * u * tails)))
        q = a.lerp(b, u) + Vector((0, 0, -foot * v))
        return q + side * (wave * v * math.sin(u * 7.0 + v * 5.0)) + side * (0.25 * wave * math.sin(u * 19.0))
    uvsheet(p, pos, cloth_col(base, trim, mark), nu, nv)


def bracket_lamp(p, root, out, s=1.0):
    """Wrought iron arm curling out from `root`, with a lantern on a short chain."""
    root, out = Vector(root), Vector(out).normalized()
    iron = metal(rust=0.3)
    pts = [root + out * (0.62 * t) + Vector((0, 0, 0.22 * math.sin(math.pi * t * 0.85))) for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
    pipe(p, pts, [0.03, 0.028, 0.026, 0.024, 0.022, 0.02], iron, sides=5, up=out.cross(UP))
    tip = pts[-1]
    pipe(p, [tip + out * (math.cos(q) * 0.07) + Vector((0, 0, math.sin(q) * 0.07 - 0.07)) for q in (math.radians(a) for a in (90, 30, -40, -110, -170, -230))],
         [0.02, 0.019, 0.018, 0.016, 0.014, 0.01], iron, sides=5, up=out.cross(UP))
    pipe(p, [root + Vector((0, 0, -0.42)), root + out * 0.22 + Vector((0, 0, -0.12)), root + out * 0.42 + Vector((0, 0, 0.13))], 0.02, iron, sides=5, up=out.cross(UP))
    hook = tip + Vector((0, 0, -0.14))
    chain(p, hook + Vector((0, 0, 0.02)), hook + Vector((0, 0, -0.2)))
    lamp(p, tuple(hook + Vector((0, 0, -0.18))), s)


def lantern_post(name, seed, arms=1, height=3.7, pennant=None):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    lx, ly = rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03)
    top = Vector((lx * height, ly * height, height))
    log(p, (0, 0, -0.2), top, 0.18, 0.125, seed, sides=8, foot=0.55, point=0.22)
    stones(p, (0, 0, 0), 0.30, 6, seed + 1)
    lash(p, (lx * 1.0, ly * 1.0, 1.0), 0.165, 4, 0.02)
    for k in range(arms):
        sgn = 1.0 if k == 0 else -1.0
        za = height - 0.62 - 0.12 * k
        root = Vector((lx * za, ly * za, za))
        tip = root + Vector((sgn * 1.0, 0, 0.12))
        beam(p, root - Vector((sgn * 0.26, 0, 0.03)), tip, 0.11, 0.13, seed + 10 + k, grey=0.35, bevel=0.025)
        beam(p, root + Vector((sgn * 0.11, 0, -0.78)), root + Vector((sgn * 0.74, 0, 0.02)), 0.085, 0.10, seed + 20 + k, grey=0.4)
        lash(p, root + Vector((0, 0, -0.10)), 0.15, 3, 0.02)
        ibox(p, Matrix.Translation(tip + Vector((-sgn * 0.14, 0, 0.0))), (0.05, 0.15, 0.17), metal(), 0.01)
        hook = tip + Vector((-sgn * 0.14, 0, -0.085))
        chain(p, hook, hook + Vector((0, 0, -0.24)))
        lamp(p, tuple(hook + Vector((0, 0, -0.22))), 1.2)
    if pennant:
        a = top + Vector((0, 0, -0.30))
        uvsheet(p, lambda u, v: a + Vector((-1.25 * u, 0.10 * math.sin(u * 6.0) * u, -0.42 * v * (1.0 - 0.75 * u) - 0.12 * u)), cloth_col(pennant, None, None, grime=0.2), 8, 4)
    p.export()


def lantern_wall(name):
    if not want(name):
        return
    p = Prop(name)                                                   # origin on the wall, the lamp hangs out toward -y
    ibox(p, Matrix.Translation((0, -0.02, -0.12)), (0.16, 0.04, 0.72), metal(), 0.012)
    for z in (0.16, -0.40):
        lathe(p, [(0.03, 0.0), (0.03, 0.03), (0.012, 0.04)], metal(), sides=6, m=zto((0, -0.04, z), (0, -1, 0)), smooth=False)
    bracket_lamp(p, (0, -0.04, 0.0), (0, -1, 0), 1.1)
    p.export()


def lantern_hanging(name):
    if not want(name):
        return
    p = Prop(name)                                                   # origin at the hook, everything hangs below
    chain(p, (0, 0, 0), (0, 0, -0.42))
    lamp(p, (0, 0, -0.40), 1.25)
    p.export()


def lantern_ground(name):
    if not want(name):
        return
    p = Prop(name)
    lamp(p, (0, 0, 0.0), 1.3, hang=False)
    p.export()


def brazier(name, seed=3):
    if not want(name):
        return
    p = Prop(name)
    iron = metal(rust=0.45)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        pipe(p, [Vector((math.cos(a) * 0.52, math.sin(a) * 0.52, 0)), Vector((math.cos(a) * 0.22, math.sin(a) * 0.22, 0.72)), Vector((math.cos(a) * 0.36, math.sin(a) * 0.36, 1.08))],
             [0.034, 0.03, 0.028], iron, sides=5, up=Vector((-math.sin(a), math.cos(a), 0)))
    lathe(p, [(0.24, 0.66), (0.27, 0.68), (0.24, 0.70)], iron, sides=10, smooth=False, cap=False)
    lathe(p, [(0.20, 0.98), (0.36, 1.04), (0.47, 1.22), (0.50, 1.40), (0.53, 1.42), (0.53, 1.45), (0.46, 1.45), (0.43, 1.24), (0.33, 1.09), (0.20, 1.04), (0.004, 1.03)], iron, sides=12,
          smooth=False, cap=False)
    disc(p, (0, 0, 0.98), 0.20, IRON_DARK, 12, down=True)
    for k in range(12):
        a = 2 * math.pi * k / 12
        pipe(p, [Vector((math.cos(a) * r, math.sin(a) * r, z)) for r, z in ((0.37, 1.04), (0.485, 1.22), (0.54, 1.44))], 0.014, iron, sides=4)
    faces = p.blob((0, 0, 1.33), (0.42, 0.42, 0.14), const((0, 0, 0)), seed, rough=0.35, subdiv=2)
    p.paint(faces, lambda co, nrm: lerp((0.10, 0.06, 0.05), (1.0, 0.42, 0.06), clamp01(noise.noise(co * 9.0) * 1.3 + 0.35)))
    flame(p, (0, 0, 1.38), 0.95, seed)
    p.export()


def tiki_torch(name, seed=5):
    if not want(name):
        return
    p = Prop(name)
    cane = (0.72, 0.62, 0.30)
    prof = []
    for k in range(7):
        z0 = 2.1 * k / 7
        prof += [(0.048, z0), (0.040, z0 + 0.04), (0.040, z0 + 0.26), (0.048, z0 + 0.30)]
    m = at_m(0, 0, 0, 0, 0.05, 0.04)
    lathe(p, prof, lambda co, nrm: lerp(mul(cane, 0.5), cane, clamp01(0.3 + co.z / 2.0 + 0.2 * noise.noise(co * 12.0))), sides=8, m=m)
    head = m @ Vector((0, 0, 2.1))
    weave = lambda co, nrm: lerp(mul(ROPE_C, 0.45), ROPE_C, clamp01(0.5 + 0.5 * math.sin(co.z * 70.0) * math.sin(math.atan2(co.y - head.y, co.x - head.x) * 9.0) + nrm.z * 0.3))
    lathe(p, [(0.05, 0.0), (0.12, 0.10), (0.17, 0.30), (0.19, 0.36), (0.16, 0.36), (0.10, 0.20), (0.004, 0.18)], weave, at=head, sides=10, cap=False)
    lash(p, head + Vector((0, 0, 0.02)), 0.07, 3, 0.016)
    flame(p, head + Vector((0, 0, 0.26)), 0.55, seed, tongues=4)
    stones(p, (0, 0, 0), 0.16, 4, seed, size=(0.07, 0.12))
    p.export()


def torch_wall(name, seed=8):
    if not want(name):
        return
    p = Prop(name)
    iron = metal()
    ibox(p, Matrix.Translation((0, -0.015, 0)), (0.12, 0.03, 0.34), iron, 0.01)
    pipe(p, [Vector((0, -0.03, -0.08)), Vector((0, -0.16, -0.10)), Vector((0, -0.22, -0.02))], 0.02, iron, sides=5, up=Vector((1, 0, 0)))
    lathe(p, [(0.06, 0.0), (0.065, 0.05)], iron, sides=8, m=zto((0, -0.24, -0.04), (0, -0.35, 1)), smooth=False, cap=False)
    a, b = Vector((0, -0.14, -0.34)), Vector((0, -0.36, 0.30))
    log(p, a, b, 0.034, 0.045, seed, sides=6, grey=0.2, wob=0.0)
    d = (b - a).normalized()
    lathe(p, [(0.05, 0.0), (0.075, 0.05), (0.08, 0.18), (0.05, 0.24)], lambda co, nrm: lerp((0.10, 0.08, 0.07), (0.42, 0.30, 0.20), clamp01(noise.noise(co * 30.0) + 0.4)), sides=8,
          m=zto(b - d * 0.02, d))
    flame(p, b + d * 0.16, 0.42, seed, tongues=3)
    p.export()


def campfire(name, seed=4, spit=False):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    stones(p, (0, 0, 0), 0.62, 9, seed, size=(0.14, 0.22))
    faces = p.blob((0, 0, 0.0), (0.52, 0.52, 0.07), const((0, 0, 0)), seed, rough=0.25, subdiv=2)
    p.paint(faces, lambda co, nrm: lerp((0.08, 0.07, 0.07), (0.80, 0.30, 0.05) if (co.x ** 2 + co.y ** 2) < 0.06 else (0.36, 0.33, 0.31), clamp01(noise.noise(co * 8.0) + 0.45)))
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.2, 0.2)
        o = Vector((math.cos(a) * 0.46, math.sin(a) * 0.46, 0.06))
        t = Vector((math.cos(a + 2.6) * 0.07, math.sin(a + 2.6) * 0.07, 0.44 + rnd.uniform(-0.05, 0.06)))
        log(p, o, t, 0.07, 0.055, seed + k, sides=6, grey=0.15, wob=0.1)
    flame(p, (0, 0, 0.14), 0.95, seed, tongues=6)
    if spit:
        for sgn in (-1, 1):
            log(p, (sgn * 0.95, 0, -0.05), (sgn * 0.90, 0, 1.25), 0.05, 0.04, seed + 20 + sgn, sides=6, wob=0.2)
            for dy in (-1, 1):
                log(p, (sgn * 0.90, 0, 1.18), (sgn * 0.90, dy * 0.11, 1.42), 0.03, 0.024, seed + 30 + dy, sides=5, wob=0.0)
        log(p, (-1.08, 0, 1.30), (1.08, 0, 1.30), 0.028, 0.028, seed + 40, sides=6, wob=0.05)
        iron = metal(rust=0.3)
        chain(p, (0, 0, 1.28), (0, 0, 1.06), 0.07, 0.011)
        pipe(p, [Vector((math.cos(q) * 0.23, 0, 0.82 + math.sin(q) * 0.24)) for q in (math.radians(a) for a in (0, 30, 60, 90, 120, 150, 180))], 0.012, iron, sides=4, up=Vector((0, 1, 0)))
        lathe(p, [(0.10, 0.55), (0.22, 0.60), (0.26, 0.72), (0.23, 0.84), (0.25, 0.86), (0.25, 0.88), (0.20, 0.86), (0.21, 0.74), (0.16, 0.65), (0.004, 0.63)], iron, sides=12, cap=False)
        disc(p, (0, 0, 0.82), 0.205, (0.62, 0.36, 0.16), 12)
    p.export()


def mooring_post(name, seed, piles=1, height=4.3):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    spots = [(0.0, 0.0, 0.0)] if piles == 1 else [(0.0, 0.0, 0.0), (0.42, 0.10, -0.5), (-0.20, 0.38, -0.8)]
    for k, (x, y, dh) in enumerate(spots):
        lx, ly = (rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02)) if piles == 1 else (-x * 0.07, -y * 0.07)
        h = height + dh
        log(p, (x, y, 0), (x + lx * h, y + ly * h, h), 0.25, 0.21, seed + k, sides=9, grey=0.5, foot=1.5, segs=5, wob=0.12)
        top = Vector((x + lx * h, y + ly * h, h))
        lathe(p, [(0.235, -0.16), (0.24, -0.02), (0.20, 0.03), (0.004, 0.05)], metal(rust=0.55), at=top, sides=9, smooth=False, cap=False)
        for j in range(8):                                           # barnacles and weed at the tide line
            a = rnd.uniform(0, 6.28)
            z = rnd.uniform(0.6, 1.5)
            p.blob((x + lx * z + math.cos(a) * 0.245, y + ly * z + math.sin(a) * 0.245, z), (0.05, 0.05, 0.04), const((0.80, 0.80, 0.70) if j % 2 else (0.20, 0.36, 0.20)), j, 0.2, 1)
    c = Vector((0, 0, height - 0.9)) if piles == 1 else Vector((0.07, 0.16, height - 1.3))
    lash(p, c, 0.245 if piles == 1 else 0.50, 5, 0.032)
    hang = c + Vector((0.27 if piles == 1 else 0.52, 0, 0.05))
    for k in range(3):
        pipe(p, [hang + Vector((0.035 * k, math.sin(q) * 0.20, -0.36 + math.cos(q) * 0.40)) for q in (2 * math.pi * j / 12 for j in range(12))], 0.03, rope_paint(), sides=5,
             up=Vector((1, 0, 0)), closed=True)
    p.export()


def banner_pole(name, seed, base=RED, height=6.5):
    if not want(name):
        return
    p = Prop(name)
    log(p, (0, 0, -0.2), (0.04, 0.02, height), 0.12, 0.075, seed, sides=8, foot=0.5, segs=6, wob=0.2)
    stones(p, (0, 0, 0), 0.24, 5, seed)
    zb = height - 0.5
    log(p, (-1.05, -0.09, zb), (1.05, -0.09, zb + 0.03), 0.05, 0.045, seed + 1, sides=7, wob=0.05)
    lash(p, (0.03, -0.04, zb - 0.06), 0.11, 3, 0.02, axis=(0, 0.3, 1))
    for sgn in (-1, 1):
        rope(p, (sgn * 0.98, -0.09, zb), (0.04, 0.0, height - 0.05), 0.014)
        lathe(p, [(0.03, -0.03), (0.06, 0.0), (0.03, 0.03)], gilt, sides=8, m=zto((sgn * 1.06, -0.09, zb + (0.03 if sgn > 0 else 0.0)), (sgn, 0, 0)))
    banner_cloth(p, (-0.86, -0.13, zb - 0.05), (0.86, -0.13, zb - 0.05), 3.1, base, OCHRE, (0.95, 0.86, 0.60), tails=2)
    lathe(p, [(0.05, 0.0), (0.10, 0.07), (0.07, 0.15), (0.03, 0.2), (0.07, 0.27), (0.004, 0.42)], gilt, at=(0.04, 0.02, height - 0.02), sides=8)
    p.export()


def flag_pole(name, seed, base=NAVY, height=9.5):
    if not want(name):
        return
    p = Prop(name)
    log(p, (0, 0, -0.3), (0.0, 0.0, height), 0.17, 0.08, seed, sides=9, foot=0.5, segs=7, wob=0.12)
    for k in range(4):
        a = math.pi / 4 + math.pi * k / 2
        beam(p, (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.05), (math.cos(a) * 0.14, math.sin(a) * 0.14, 1.25), 0.10, 0.10, seed + k, grey=0.4)
    chunk(p, (0, 0, 0.12), (0.85, 0.85, 0.22), seed, 'ruin', pts=16, boxy=0.9, flat=0.2, sub=1)
    lathe(p, [(0.09, 0.0), (0.14, 0.08), (0.004, 0.2)], gilt, at=(0, 0, height), sides=8)
    a = Vector((0.08, 0, height - 0.25))

    def pos(u, v):
        return a + Vector((2.9 * u, 0.28 * math.sin(u * 7.5 + v * 1.5) * (0.25 + u) + 0.3 * u * u, -1.75 * v - 0.42 * u * u + 0.06 * math.sin(u * 9.0)))
    uvsheet(p, pos, lambda u, v, nrm: cloth_col(base, OCHRE, None, border=0.08, grime=0.0)(v, u * 0.5, nrm) if star_alpha(0.5 + (u - 0.45) * 1.55, v) <= 0.0
            else lerp(base, (0.95, 0.86, 0.60), star_alpha(0.5 + (u - 0.45) * 1.55, v)), 22, 14)
    rope(p, (0.10, 0, height - 0.2), (0.16, 0, 1.3), 0.012)
    p.export()


def signpost(name, seed, hanging=False):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    log(p, (0, 0, -0.2), (0.05, -0.03, 3.1), 0.13, 0.10, seed, sides=8, foot=0.5, point=0.18)
    stones(p, (0, 0, 0), 0.24, 5, seed + 2)
    if hanging:
        beam(p, (-0.2, 0, 2.72), (1.45, 0, 2.80), 0.10, 0.12, seed + 3, grey=0.35)
        beam(p, (0.10, 0, 1.95), (0.80, 0, 2.70), 0.08, 0.09, seed + 4)
        m = at_m(0.82, 0, 1.92, 0.0, 0.0, 0.05)
        for k in range(4):
            board(p, m @ Matrix.Translation((0, 0, -0.27 + 0.19 * k)), (1.05 - 0.10 * abs(k - 1.5), 0.05, 0.18), seed + 10 + k, 0.3)
        for sx in (-0.38, 0.38):
            chain(p, (0.82 + sx, 0, 2.72), (0.82 + sx, 0, 2.32), 0.07, 0.011)
            ibox(p, m @ Matrix.Translation((sx, 0, 0.36)), (0.05, 0.07, 0.10), metal(), 0.008)
        for sgn in (-1, 1):                                          # a painted star on both faces
            for k in range(4):
                a = math.pi / 2 * k
                c = m @ Vector((0, sgn * 0.031, 0.02))
                d1, d2 = m.to_3x3() @ Vector((math.cos(a), 0, math.sin(a))), m.to_3x3() @ Vector((math.cos(a + math.pi / 4), 0, math.sin(a + math.pi / 4)))
                d0 = m.to_3x3() @ Vector((math.cos(a - math.pi / 4), 0, math.sin(a - math.pi / 4)))
                tri = [c + d0 * 0.09, c + d1 * 0.30, c + d2 * 0.09, c]
                fquad(p, tri if sgn < 0 else tri[::-1], OCHRE)
        bracket_lamp(p, (-0.10, 0, 2.2), (-1, 0, 0), 0.95)
    else:
        for k in range(3):
            yaw = rnd.uniform(0, 6.28)
            z = 2.72 - 0.42 * k
            m = at_m(0.04, -0.02, z, yaw, rnd.uniform(-0.07, 0.07))
            L = rnd.uniform(1.0, 1.35)
            board(p, m @ Matrix.Translation((L * 0.5 - 0.18, -0.14, 0)), (L, 0.045, 0.27), seed + 20 + k, rnd.uniform(0.2, 0.5), bevel=0.015)
            tip = [m @ Vector(v) for v in ((L - 0.18, -0.14 - 0.0225, 0.135), (L + 0.05, -0.14 - 0.0225, 0.0), (L - 0.18, -0.14 - 0.0225, -0.135))]
            tip2 = [v + m.to_3x3() @ Vector((0, 0.045, 0)) for v in tip]
            tint = lerp(wood_tint(seed + 20 + k), WEATHER, 0.35)
            fquad(p, tip[::-1], tint)
            fquad(p, tip2, mul(tint, 0.8))
            fquad(p, [tip[0], tip[1], tip2[1], tip2[0]], lerp(tint, EDGE_LIT, 0.3))
            fquad(p, [tip[1], tip[2], tip2[2], tip2[1]], mul(tint, 0.7))
            for dx in (0.0, 0.12):
                lathe(p, [(0.022, 0.0), (0.022, 0.012), (0.008, 0.02)], metal(), sides=6, m=m @ zto((dx - 0.03, -0.165, 0.05 - dx * 0.8), (0, -1, 0)), smooth=False)
    p.export()


def fence_rope(name, seed, length=4.0, posts=3):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    tops = []
    for k in range(posts):
        x = -length / 2 + length * k / (posts - 1)
        h = rnd.uniform(1.05, 1.25)
        lx = rnd.uniform(-0.06, 0.06)
        log(p, (x, 0, -0.2), (x + lx * h, rnd.uniform(-0.05, 0.05), h), 0.095, 0.08, seed + k, sides=7, foot=0.3, point=0.10)
        tops.append(Vector((x + lx * h * 0.8, 0, h * 0.8)))
        lash(p, (x + lx * h * 0.76, 0, h * 0.76), 0.088, 2, 0.02)
        lash(p, (x + lx * h * 0.42, 0, h * 0.42), 0.092, 2, 0.02)
    for a, b in zip(tops, tops[1:]):
        rope(p, a, b, 0.024, sag=0.16)
        rope(p, a * 0.53 + Vector((a.x * 0.47, 0, 0)), b * 0.53 + Vector((b.x * 0.47, 0, 0)), 0.024, sag=0.12)
    p.export()


def fence_plank(name, seed, length=4.0):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for k in range(3):
        x = -length / 2 + 0.15 + (length - 0.3) * k / 2
        log(p, (x, 0.07, -0.2), (x, 0.07, 1.25 + rnd.uniform(-0.1, 0.1)), 0.09, 0.08, seed + k, sides=7, foot=0.3)
    for z in (0.42, 0.95):
        beam(p, (-length / 2, 0, z + rnd.uniform(-0.03, 0.03)), (length / 2, 0, z + rnd.uniform(-0.03, 0.03)), 0.05, 0.13, seed + 5 + int(z * 10), grey=0.5)
    x = -length / 2 + 0.12
    k = 0
    while x < length / 2 - 0.1:
        w = rnd.uniform(0.16, 0.24)
        if rnd.random() > 0.14:
            h = rnd.uniform(1.0, 1.45) if rnd.random() > 0.15 else rnd.uniform(0.5, 0.8)
            m = at_m(x, -0.05, h / 2 + 0.05, 0, 0, 0) @ Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, 'Y')
            board(p, m, (w * 0.92, 0.035, h), seed + 20 + k, rnd.uniform(0.35, 0.65))
        x += w
        k += 1
    p.export()


def ladder(name, seed, height=3.2):
    if not want(name):
        return
    p = Prop(name)
    for sgn in (-1, 1):
        log(p, (sgn * 0.33, 0, 0), (sgn * 0.27, 0, height), 0.05, 0.042, seed + sgn, sides=7, wob=0.15, grey=0.4)
    n = int(height / 0.34)
    for k in range(n):
        z = 0.28 + (height - 0.5) * k / (n - 1)
        w = 0.33 - 0.06 * z / height
        log(p, (-w - 0.07, 0, z), (w + 0.07, 0, z + 0.01), 0.032, 0.03, seed + 10 + k, sides=6, wob=0.05, grey=0.4)
        for sgn in (-1, 1):
            lash(p, (sgn * w - 0.03, 0, z), 0.036, 2, 0.011, axis=(1, 0, 0))
    p.export()


def bench(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for sgn in (-1, 1):
        log(p, (sgn * 0.68, 0, 0), (sgn * 0.68, 0, 0.44), 0.17, 0.16, seed + sgn, sides=9, grey=0.4, wob=0.0)
        log(p, (sgn * 0.74, 0.20, 0.3), (sgn * 0.76, 0.33, 1.02), 0.045, 0.04, seed + 5 + sgn, sides=6, grey=0.4, wob=0.1)
    for k, y in enumerate((-0.15, 0.06)):
        board(p, at_m(0, y, 0.475 + 0.008 * k, 0.02 * (k - 0.5)), (1.95, 0.20, 0.06), seed + 10 + k, 0.4, bevel=0.016)
    board(p, at_m(0, 0.305, 0.86) @ Matrix.Rotation(-0.18, 4, 'X'), (1.85, 0.045, 0.22), seed + 14, 0.45, bevel=0.014)
    p.export()


def fish(p, m, s=1.0, tint=(0.56, 0.66, 0.70)):
    """A fish hanging by the tail: nose at the origin of m pointing down -z... body runs up +z."""
    prof = [(0.004, 0.0), (0.035, 0.03), (0.06, 0.10), (0.062, 0.20), (0.045, 0.30), (0.02, 0.38), (0.012, 0.42)]
    loops = [[m @ Vector((math.cos(q) * r * s * 0.55, math.sin(q) * r * s, z * s)) for q in (2 * math.pi * k / 8 for k in range(8))] for r, z in prof]
    mi = m.inverted()
    skin(p, loops, lambda co, nrm: lerp(lerp(tint, (0.95, 0.93, 0.85), 0.6), mul(tint, 0.6), clamp01((mi @ co).y / (0.05 * s) * 0.5 + 0.5)), cap=False)
    tail = [m @ Vector(v) * 1.0 for v in ((0, 0.0, 0.41 * s), (0, 0.08 * s, 0.52 * s), (0, 0.0, 0.47 * s), (0, -0.08 * s, 0.52 * s))]
    fquad(p, tail, mul(tint, 0.7))
    fquad(p, tail[::-1], mul(tint, 0.7))


def net(p, a, b, c, d, nu=9, nv=7, sag=0.12, r=0.007):
    """Diagonal mesh of cord across the quad a b c d (a-b top edge, d-c bottom edge)."""
    a, b, c, d = Vector(a), Vector(b), Vector(c), Vector(d)
    nrm = (b - a).cross(d - a).normalized()

    def pt(u, v):
        return a.lerp(b, u).lerp(d.lerp(c, u), v) + nrm * (sag * math.sin(math.pi * u) * math.sin(math.pi * v))
    cord = rope_paint((0.50, 0.44, 0.32))
    for k in range(-nv, nu + 1):
        for sgn in (1, -1):
            pts = []
            for j in range(nv + 1):
                i = k + j if sgn > 0 else nu - k - j
                if 0 <= i <= nu:
                    pts.append(pt(i / nu, j / nv))
            if len(pts) > 1:
                pipe(p, pts, r, cord, sides=3, up=nrm, cap=False)


def net_rack(name, seed, fishy=False):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for sgn in (-1, 1):
        log(p, (sgn * 1.45, 0, -0.2), (sgn * 1.40, 0, 2.55), 0.085, 0.07, seed + sgn, sides=7, foot=0.3, wob=0.2)
        log(p, (sgn * 1.42, 0.55, -0.1), (sgn * 1.42, 0.02, 1.7), 0.05, 0.045, seed + 3 + sgn, sides=6, wob=0.1)
    log(p, (-1.62, 0, 2.36), (1.62, 0, 2.40), 0.06, 0.055, seed + 6, sides=7, wob=0.08)
    for sgn in (-1, 1):
        lash(p, (sgn * 1.40 - 0.03, 0, 2.36), 0.07, 3, 0.016, axis=(1, 0, 0))
    if fishy:
        log(p, (-1.5, 0, 1.55), (1.5, 0, 1.58), 0.04, 0.04, seed + 7, sides=6, wob=0.05)
        for row, (z, n) in enumerate(((2.30, 7), (1.50, 6))):
            for k in range(n):
                x = -1.15 + 2.3 * k / (n - 1) + rnd.uniform(-0.05, 0.05)
                s = rnd.uniform(0.9, 1.5)
                rope(p, (x, 0, z + 0.05), (x, 0, z - 0.06), 0.008)
                fish(p, at_m(x, 0, z - 0.06 - 0.52 * s, rnd.uniform(0, 3.1)), s, lerp((0.56, 0.66, 0.70), (0.80, 0.52, 0.36), rnd.random()))
    else:
        net(p, (-1.3, -0.03, 2.33), (1.3, -0.03, 2.33), (1.25, -0.03, 0.55), (-1.2, -0.03, 0.45), 11, 8)
        for k in range(6):
            x = -1.2 + 2.4 * k / 5
            lathe(p, [(0.03, -0.05), (0.07, -0.02), (0.07, 0.02), (0.03, 0.05)], const((0.70, 0.50, 0.30) if k % 2 else (0.72, 0.20, 0.14)), sides=7, m=zto((x, -0.04, 2.28), (1, 0, 0)))
    p.export()


def anchor_geo(p, s, seed):
    """An anchor standing on its crown, ring at the top, 1.0 * s tall."""
    iron = metal(rust=0.55)
    pipe(p, [Vector((0, 0, 0.10 * s)), Vector((0, 0, 0.5 * s)), Vector((0, 0, 0.92 * s))], [0.055 * s, 0.048 * s, 0.04 * s], iron, sides=6, smooth=False)
    arc = [Vector((math.sin(a) * 0.40 * s, 0, 0.42 * s - math.cos(a) * 0.40 * s)) for a in (math.radians(q) for q in (-78, -55, -30, 0, 30, 55, 78))]
    pipe(p, arc, [0.03 * s, 0.045 * s, 0.055 * s, 0.065 * s, 0.055 * s, 0.045 * s, 0.03 * s], iron, sides=6, up=Vector((0, 1, 0)), smooth=False)
    for sgn in (-1, 1):
        tip = arc[0] if sgn < 0 else arc[-1]
        pts = [tip + Vector((sgn * 0.03 * s, 0, 0.13 * s)), tip + Vector((-sgn * 0.10 * s, 0, -0.02 * s)), tip + Vector((sgn * 0.02 * s, 0, -0.10 * s)), tip + Vector((sgn * 0.12 * s, 0, 0.04 * s))]
        for dy in (-0.022 * s, 0.022 * s):
            q = [v + Vector((0, dy, 0)) for v in pts]
            fquad(p, q if dy * sgn > 0 else q[::-1], iron)
    log(p, (-0.36 * s, 0, 0.86 * s), (0.36 * s, 0, 0.86 * s), 0.045 * s, 0.04 * s, seed, sides=7, grey=0.5, wob=0.05)
    for sx in (-0.2, 0.2):
        lathe(p, [(0.05 * s, -0.02 * s), (0.05 * s, 0.02 * s)], iron, sides=7, m=zto((sx * s, 0, 0.86 * s), (1, 0, 0)), smooth=False, cap=False)
    c = Vector((0, 0, 1.0 * s))
    pipe(p, [c + Vector((0, math.cos(q) * 0.085 * s, math.sin(q) * 0.085 * s)) for q in (2 * math.pi * k / 10 for k in range(10))], 0.022 * s, iron, sides=5, up=Vector((1, 0, 0)), closed=True)


def anchor(name, seed, s=2.4, buried=False):
    if not want(name):
        return
    p = Prop(name)
    anchor_geo(p, s, seed)
    if buried:
        xf_all(p, at_m(0, 0, -0.16 * s, 0.4, 0.5, 0.25))
        rope(p, (0.42 * s, 0.18 * s, 0.72 * s), (1.0 * s, 0.5 * s, 0.03), 0.04, sag=0.15)
        coil(p, (1.05 * s, 0.55 * s, 0.0), 0.34, 2, 0.04)
        stones(p, (0.1, 0, 0), 0.5 * s, 4, seed, ring=False)
    else:
        xf_all(p, at_m(0, 0, 0.02, 0.3, 1.02, 0.0) @ Matrix.Translation((0, 0, 0.0)))
        low = min(v.co.z for v in p.bm.verts)
        xf_all(p, Matrix.Translation((0, 0, -low)))
        hi = max(p.bm.verts, key=lambda v: v.co.x).co.copy()
        rope(p, hi, hi + Vector((0.5, 0.4, -hi.z + 0.03)), 0.035, sag=0.1)
        coil(p, tuple(hi + Vector((0.55, 0.5, -hi.z))), 0.30, 3, 0.035)
    p.export()


def wheel_solid(p, c, axis, r, w, seed):
    m = zto(c, axis)
    tint = wood_tint(seed)
    lathe(p, [(0.004, -w / 2), (r * 0.25, -w * 0.62), (r * 0.25, -w / 2), (r, -w / 2), (r, w / 2), (r * 0.25, w / 2), (r * 0.25, w * 0.62), (0.004, w * 0.62)],
          lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.6), tint, clamp01(0.5 + 0.5 * noise.noise(co * 6.0))), sides=12, m=m, smooth=False, cap=False)
    lathe(p, [(r + 0.012, -w * 0.4), (r + 0.012, w * 0.4)], metal(rust=0.4), sides=12, m=m, smooth=False, cap=False)


def cannon_geo(p, m, seed):
    """Naval gun on a stepped truck carriage, muzzle toward +x of m."""
    for sgn in (-1, 1):
        for k, (x0, x1, h) in enumerate(((-0.75, 0.55, 0.20), (-0.75, 0.10, 0.36), (-0.75, -0.30, 0.50))):
            board(p, m @ Matrix.Translation(((x0 + x1) / 2, sgn * 0.27, 0.24 + h / 2)), (x1 - x0, 0.10, h), seed + k + sgn * 3, 0.25, bevel=0.02)
    board(p, m @ Matrix.Translation((-0.10, 0, 0.26)), (1.25, 0.46, 0.08), seed + 9, 0.3)
    for x in (-0.50, 0.32):
        log(p, m @ Vector((x, -0.42, 0.20)), m @ Vector((x, 0.42, 0.20)), 0.055, 0.055, seed + 12, sides=7, wob=0.0, grey=0.2)
        for sgn in (-1, 1):
            wheel_solid(p, m @ Vector((x, sgn * 0.40, 0.20)), m.to_3x3() @ Vector((0, sgn, 0)), 0.20 if x > 0 else 0.17, 0.10, seed + 14)
    bore = [(0.004, -0.74), (0.07, -0.72), (0.085, -0.66), (0.06, -0.60), (0.15, -0.56), (0.185, -0.50), (0.19, -0.42), (0.175, -0.40), (0.17, -0.05), (0.185, -0.03), (0.185, 0.02),
            (0.165, 0.04), (0.15, 0.50), (0.165, 0.52), (0.165, 0.56), (0.14, 0.58), (0.125, 0.90), (0.16, 0.95), (0.17, 1.02), (0.15, 1.05), (0.085, 1.05), (0.08, 0.80)]
    gm = m @ Matrix.Translation((-0.05, 0, 0.60)) @ Matrix.Rotation(math.radians(86), 4, 'Y')
    lathe(p, bore, lambda co, nrm: lerp((0.07, 0.07, 0.08), (0.36, 0.36, 0.40), clamp01(0.18 + 0.82 * nrm.z) ** 1.2), sides=12, m=gm, cap=False)
    disc(p, (0, 0, 0.80), 0.082, (0.02, 0.02, 0.02), 12, gm)
    log(p, m @ Vector((-0.02, -0.33, 0.61)), m @ Vector((-0.02, 0.33, 0.61)), 0.05, 0.05, seed + 30, sides=7, wob=0.0, grey=0.0)
    for sgn in (-1, 1):
        ibox(p, m @ Matrix.Translation((-0.02, sgn * 0.27, 0.69)), (0.20, 0.11, 0.04), metal(), 0.01)
    board(p, m @ Matrix.Translation((-0.52, 0, 0.42)) @ Matrix.Rotation(-0.25, 4, 'Y'), (0.36, 0.14, 0.09), seed + 33, 0.2)
    pts = [m @ Vector(v) for v in ((-0.80, 0.0, 0.62), (-0.74, 0.30, 0.52), (-0.20, 0.36, 0.42), (0.40, 0.40, 0.35))]
    pipe(p, pts, 0.022, rope_paint(), sides=5)
    pipe(p, [Vector((v.x, v.y, v.z)) for v in [m @ Vector(q) for q in ((-0.80, 0.0, 0.62), (-0.74, -0.30, 0.52), (-0.20, -0.36, 0.42), (0.40, -0.40, 0.35))]], 0.022, rope_paint(), sides=5)


def cannon(name, seed):
    if not want(name):
        return
    p = Prop(name)
    cannon_geo(p, Matrix.Identity(4), seed)
    p.export()


def shot_pile(p, at, r=0.085, base=3):
    x, y, z = at
    ball = lambda co, nrm: lerp((0.06, 0.06, 0.07), (0.36, 0.36, 0.40), clamp01(0.15 + 0.85 * nrm.z) ** 1.3)
    for layer in range(base):
        n = base - layer
        for i in range(n):
            for j in range(n):
                p.blob((x + (i - (n - 1) / 2) * 2 * r, y + (j - (n - 1) / 2) * 2 * r, z + r + layer * r * 1.42), (r, r, r), ball, 1, 0.0, 2, smooth=True)


def cannonballs(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for k in range(4):
        a = math.pi / 2 * k
        m = Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0.30, 0, 0.04))
        board(p, m, (0.07, 0.67, 0.08), seed + k, 0.3)
    board(p, Matrix.Translation((0, 0, 0.015)), (0.56, 0.56, 0.03), seed + 5, 0.4)
    shot_pile(p, (0, 0, 0.03), 0.088, 3)
    p.blob((0.46, 0.2, 0.088), (0.088, 0.088, 0.088), lambda co, nrm: lerp((0.06, 0.06, 0.07), (0.36, 0.36, 0.40), clamp01(0.15 + 0.85 * nrm.z)), 1, 0.0, 2, smooth=True)
    p.export()


def capstan(name, seed):
    if not want(name):
        return
    p = Prop(name)
    tint = wood_tint(seed)
    wood = lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.6), lerp(tint, EDGE_LIT, 0.25), clamp01(0.35 + 0.5 * nrm.z + 0.25 * noise.noise(co * 5.0)))
    lathe(p, [(0.62, 0.0), (0.62, 0.07), (0.50, 0.11), (0.30, 0.13), (0.24, 0.50), (0.22, 0.80), (0.36, 0.86), (0.44, 0.90), (0.44, 1.08), (0.38, 1.12), (0.12, 1.14), (0.10, 1.2), (0.004, 1.22)],
          wood, sides=12, smooth=False)
    for k in range(6):
        a = math.pi / 3 * k
        m = Matrix.Rotation(a, 4, 'Z')
        board(p, m @ Matrix.Translation((0.31, 0, 0.47)) @ Matrix.Rotation(-0.10, 4, 'Y'), (0.13, 0.10, 0.66), seed + k, 0.2, bevel=0.02)
        log(p, m @ Vector((0.30, 0, 0.99)), m @ Vector((1.35, 0, 0.99)), 0.045, 0.036, seed + 10 + k, sides=7, wob=0.03, grey=0.25)
        ibox(p, m @ Matrix.Translation((0.445, 0, 0.99)), (0.02, 0.15, 0.15), metal(), 0.005)
    for zz in (0.885, 1.085):
        lathe(p, [(0.448, zz - 0.02), (0.448, zz + 0.02)], metal(rust=0.3), sides=12, smooth=False, cap=False)
    for k in range(4):
        zz = 0.22 + 0.07 * k
        pipe(p, [Vector((math.cos(q) * (0.385 - 0.01 * k), math.sin(q) * (0.385 - 0.01 * k), zz + 0.01 * math.sin(q))) for q in (2 * math.pi * j / 12 for j in range(12))], 0.034, rope_paint(),
             sides=5, closed=True)
    rope(p, (0.39, 0.0, 0.26), (1.5, 0.5, 0.035), 0.034, sag=0.05)
    p.export()


def powder_keg(name, seed):
    if not want(name):
        return
    p = Prop(name)
    cask(p, Matrix.Identity(4), 0.72, seed)
    lathe(p, [(0.238, 0.30), (0.25, 0.34), (0.238, 0.38)], const((0.60, 0.10, 0.08)), sides=14, smooth=False, cap=False)
    pipe(p, [Vector((0.0, 0, 0.655)), Vector((0.03, 0.02, 0.74)), Vector((0.10, 0.05, 0.78)), Vector((0.16, 0.03, 0.74))], 0.012, rope_paint((0.86, 0.80, 0.62)), sides=4)
    pipe(p, [Vector((-0.2, 0.0, 0.60)), Vector((-0.12, 0.0, 0.80)), Vector((0.12, 0.0, 0.80)), Vector((0.2, 0.0, 0.60))], 0.018, rope_paint(), sides=5, up=Vector((0, 1, 0)))
    p.export()


def rope_coil(name, seed):
    if not want(name):
        return
    p = Prop(name)
    coil(p, (0, 0, 0), 0.46, 4, 0.045)
    p.export()


def buoy(name, seed):
    if not want(name):
        return
    p = Prop(name)
    m = at_m(0, 0, 0.36, 0.3, 1.25, 0.0)
    mi = m.inverted()
    lathe(p, [(0.004, -0.55), (0.16, -0.50), (0.34, -0.25), (0.40, 0.0), (0.34, 0.24), (0.16, 0.42), (0.07, 0.48), (0.07, 0.62), (0.004, 0.63)],
          lambda co, nrm: mul((0.74, 0.18, 0.12) if abs((mi @ co).z + 0.02) > 0.16 else (0.92, 0.88, 0.78), 0.6 + 0.4 * clamp01(nrm.z * 0.7 + 0.5 + 0.2 * noise.noise(co * 7.0))), sides=12, m=m)
    for zz in (-0.26, 0.25):
        lathe(p, [(0.35, zz - 0.02), (0.365, zz), (0.35, zz + 0.02)], rope_paint(), sides=12, m=m, cap=False)
    c = m @ Vector((0, 0, 0.68))
    ax = m.to_3x3() @ Vector((1, 0, 0))
    az = m.to_3x3() @ UP
    pipe(p, [c + ax * (math.cos(q) * 0.07) + az * (math.sin(q) * 0.07) for q in (2 * math.pi * k / 8 for k in range(8))], 0.016, metal(), sides=4, up=m.to_3x3() @ Vector((0, 1, 0)), closed=True)
    rope(p, c, (c.x + 0.6, c.y + 0.35, 0.03), 0.026, sag=0.05)
    coil(p, (c.x + 0.75, c.y + 0.45, 0.0), 0.22, 2, 0.028)
    p.export()


def crab_pot(name, seed):
    if not want(name):
        return
    p = Prop(name)
    cane = lambda co, nrm: lerp((0.30, 0.20, 0.10), (0.70, 0.54, 0.30), clamp01(nrm.z * 0.5 + 0.5 + 0.2 * noise.noise(co * 15.0)))
    for k in range(5):
        board(p, Matrix.Translation((0, -0.26 + 0.13 * k, 0.02)), (0.95, 0.11, 0.035), seed + k, 0.5)
    for k in range(5):
        x = -0.44 + 0.22 * k
        pipe(p, [Vector((x, math.cos(q) * 0.30, 0.03 + math.sin(q) * 0.42)) for q in (math.pi * j / 8 for j in range(9))], 0.016, cane, sides=4, up=Vector((1, 0, 0)))
    for j in range(1, 8):
        q = math.pi * j / 8
        pipe(p, [Vector((-0.45, math.cos(q) * 0.31, 0.03 + math.sin(q) * 0.43)), Vector((0.45, math.cos(q) * 0.31, 0.03 + math.sin(q) * 0.43))], 0.009, cane, sides=3, cap=False)
    for sgn in (-1, 1):
        for j in range(5):
            q = math.pi * (j + 0.5) / 5
            pipe(p, [Vector((sgn * 0.44, math.cos(q) * 0.29, 0.03 + math.sin(q) * 0.41)), Vector((sgn * 0.20, 0, 0.20))], 0.007, cane, sides=3, cap=False)
    rope(p, (0.0, 0, 0.45), (0.5, 0.45, 0.03), 0.018, sag=0.05)
    lathe(p, [(0.03, -0.08), (0.09, -0.04), (0.09, 0.04), (0.03, 0.08)], const((0.80, 0.30, 0.14)), sides=8, m=zto((0.62, 0.52, 0.09), (1, 0.4, 0)))
    p.export()


def tarp(p, x0, x1, y0, y1, top, drop, tint, seed):
    """Canvas thrown over a stack: flat on top, hanging down the sides in folds."""
    def pos(u, v):
        uu, vv = u * 2 - 1, v * 2 - 1
        e = max(abs(uu), abs(vv))
        k = clamp01((e - 0.62) / 0.38)
        x = (x0 + x1) / 2 + uu * (x1 - x0) / 2 * (1.0 + 0.10 * k)
        y = (y0 + y1) / 2 + vv * (y1 - y0) / 2 * (1.0 + 0.10 * k)
        fold = 0.05 * math.sin((u + v) * 23.0 + seed) * k
        return Vector((x + fold, y + fold, top + 0.03 - drop * k ** 1.6 * (0.8 + 0.2 * math.sin(u * 9.0 + v * 7.0 + seed))))
    uvsheet(p, pos, lambda u, v, nrm: lerp(mul(tint, 0.5), tint, clamp01(0.35 + 0.65 * nrm.z + 0.12 * noise.noise(Vector((u * 9, v * 9, seed))))), 14, 14)


def barrel_stack(name, seed, n=3):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    if n == 3:
        cask(p, at_m(-0.34, 0.05, 0, 0.3), 1.0, seed)
        cask(p, at_m(0.36, -0.08, 0, 1.1), 1.05, seed + 1)
        cask(p, at_m(0.02, 0.60, 0, 2.0), 0.92, seed + 2)
        cask(p, at_m(0.0, 0.16, 0.96, 0.7), 0.8, seed + 3)
        coil(p, (0.03, 0.14, 1.69), 0.2, 2, 0.026)
    else:
        for k in range(3):
            cask(p, Matrix.Translation((-0.62 + 0.62 * k, 0.48, 0.30)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), 1.0, seed + k)
        for k in range(2):
            cask(p, Matrix.Translation((-0.31 + 0.62 * k, 0.48, 0.83)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), 1.0, seed + 5 + k)
        for sgn in (-1, 1):
            board(p, at_m(sgn * 0.98, 0.0, 0.07, 0, 0, 0), (0.12, 0.9, 0.14), seed + 9 + sgn, 0.4)
            xs = sgn * 0.98
            fquad(p, [Vector((xs - 0.06, -0.3, 0.14)), Vector((xs + 0.06, -0.3, 0.14)), Vector((xs + 0.06, 0.3, 0.14)), Vector((xs - 0.06, 0.3, 0.14))], WOOD_LIGHT)
        cask(p, at_m(1.45, -0.1, 0, 0.5), 1.0, seed + 12, lid=False)
        disc(p, (1.45, -0.1, 0.80), 0.30, (0.20, 0.42, 0.50), 14)
    p.export()


def crate_stack(name, seed, tarped=False):
    if not want(name):
        return
    p = Prop(name)
    case(p, at_m(0, 0, 0, 0.08), (1.0, 0.9, 0.8), seed)
    case(p, at_m(1.0, 0.12, 0, -0.12), (0.8, 0.8, 0.6), seed + 1, 0.45)
    case(p, at_m(0.1, 0.02, 0.84, 0.4), (0.7, 0.6, 0.5), seed + 2, 0.2)
    if tarped:
        tarp(p, -0.62, 1.50, -0.56, 0.62, 0.86, 0.62, CANVAS, seed)
        rope(p, (-0.66, -0.2, 0.42), (1.52, -0.2, 0.40), 0.02, sag=-0.52)
    else:
        sack(p, (1.02, 0.1, 0.63), 0.8, seed + 4)
        coil(p, (0.12, 0.02, 1.37), 0.2, 2, 0.026)
    p.export()


def sack_pile(name, seed, n=4):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    spots = [(0, 0, 0, 0.0), (0.56, 0.1, 0, 0.12), (0.26, 0.5, 0, -0.1), (0.28, 0.2, 0.42, 0.05)][:n]
    for k, (x, y, z, lean) in enumerate(spots):
        sack(p, (x, y, z), rnd.uniform(0.9, 1.15), seed + k, lerp((0.72, 0.60, 0.40), (0.60, 0.52, 0.42), rnd.random()), lean)
    p.export()


def basket_geo(p, m, s=1.0):
    mi = m.inverted()
    weave = lambda co, nrm: lerp((0.32, 0.20, 0.10), (0.78, 0.60, 0.32), clamp01(0.5 + 0.5 * math.sin((mi @ co).z * 60.0 / s) * math.sin(math.atan2((mi @ co).y, (mi @ co).x) * 12.0) * 0.8 + 0.25 * nrm.z))
    lathe(p, [(0.004, 0.0), (0.24 * s, 0.0), (0.33 * s, 0.14 * s), (0.36 * s, 0.30 * s), (0.38 * s, 0.31 * s), (0.38 * s, 0.34 * s), (0.33 * s, 0.33 * s), (0.30 * s, 0.15 * s), (0.22 * s, 0.04 * s),
              (0.004, 0.04 * s)], weave, sides=14, m=m, cap=False)


def basket(name, seed, fill='fruit'):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    basket_geo(p, Matrix.Identity(4), 1.0)
    for k in range(11):
        a, d = rnd.uniform(0, 6.28), 0.22 * math.sqrt(rnd.random())
        z = 0.26 + 0.10 * (1 - d / 0.22) + rnd.uniform(0, 0.03)
        if fill == 'fruit':
            tint = ((0.92, 0.72, 0.14), (0.86, 0.36, 0.10), (0.56, 0.72, 0.16), (0.74, 0.14, 0.12))[k % 4]
            p.blob((math.cos(a) * d, math.sin(a) * d, z), (0.075, 0.075, 0.07), lambda co, nrm, tint=tint: lerp(mul(tint, 0.55), tint, clamp01(nrm.z * 0.6 + 0.5)), k, 0.06, 2, smooth=True)
        else:
            fish(p, at_m(math.cos(a) * d * 0.5, math.sin(a) * d * 0.5, z - 0.04, a, 1.45), 1.0, lerp((0.56, 0.66, 0.70), (0.80, 0.52, 0.36), rnd.random()))
    p.export()


def table_geo(p, m, seed, L=1.8, W=0.9, H=0.82):
    for k in range(4):
        board(p, m @ Matrix.Translation((0, -W / 2 + W * (k + 0.5) / 4, H)) @ Matrix.Rotation(0.01 * (k - 1.5), 4, 'Z'), (L + 0.03 * (k % 2), W / 4 - 0.012, 0.055), seed + k, 0.35, bevel=0.014)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a, b = m @ Vector((sx * (L / 2 - 0.2), sy * (W / 2 - 0.02), 0)), m @ Vector((sx * (L / 2 - 0.25), -sy * (W / 2 - 0.16), H - 0.05))
            beam(p, a, b, 0.07, 0.09, seed + 6 + sx + sy * 2, grey=0.35)
        beam(p, m @ Vector((sx * (L / 2 - 0.22), -W / 2 + 0.08, H - 0.08)), m @ Vector((sx * (L / 2 - 0.22), W / 2 - 0.08, H - 0.08)), 0.07, 0.08, seed + 12, grey=0.35)
    beam(p, m @ Vector((-L / 2 + 0.22, 0, 0.36)), m @ Vector((L / 2 - 0.22, 0, 0.36)), 0.06, 0.09, seed + 14, grey=0.35)


def stool_geo(p, m, seed, h=0.48):
    tint = wood_tint(seed)
    lathe(p, [(0.004, h - 0.06), (0.19, h - 0.06), (0.20, h - 0.02), (0.19, h), (0.004, h)], lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.5), lerp(tint, EDGE_LIT, 0.3), clamp01(nrm.z)), sides=10,
          m=m, smooth=False, cap=False)
    for k in range(3):
        a = 2 * math.pi * k / 3 + seed
        log(p, m @ Vector((math.cos(a) * 0.22, math.sin(a) * 0.22, 0)), m @ Vector((math.cos(a) * 0.11, math.sin(a) * 0.11, h - 0.05)), 0.03, 0.035, seed + k, sides=6, wob=0.0, grey=0.3)


def candle(p, at, h=0.14, lit=True):
    x, y, z = at
    wax = lambda co, nrm: lerp((0.72, 0.66, 0.50), (0.98, 0.94, 0.80), clamp01((co.z - z) / h))
    lathe(p, [(0.04, 0.0), (0.03, 0.012), (0.024, 0.02), (0.022, h), (0.004, h + 0.004)], wax, at=at, sides=7)
    if lit:
        lathe(p, [(0.004, 0.0), (0.016, 0.02), (0.012, 0.045), (0.003, 0.08)], lambda co, nrm: lerp((1.0, 0.95, 0.6), (1.0, 0.5, 0.1), clamp01((co.z - z - h) / 0.08)), at=(x, y, z + h + 0.008),
              sides=6)


def table(name, seed, dressed=False):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    table_geo(p, Matrix.Identity(4), seed)
    if dressed:
        z = 0.85
        fquad(p, [Vector((-0.55, -0.30, z)), Vector((0.20, -0.36, z)), Vector((0.26, 0.24, z)), Vector((-0.50, 0.30, z))],
              lambda co, nrm: lerp((0.93, 0.85, 0.62), (0.70, 0.56, 0.36), clamp01(abs(co.x + 0.15) * 1.8 + abs(co.y) * 1.2 - 0.3)))
        for a, b in (((-0.42, -0.2), (0.12, 0.16)), ((-0.42, 0.18), (0.10, -0.22))):
            fquad(p, [Vector((a[0], a[1], z + 0.002)), Vector((a[0] + 0.03, a[1], z + 0.002)), Vector((b[0] + 0.03, b[1], z + 0.002)), Vector((b[0], b[1], z + 0.002))], (0.62, 0.12, 0.10))
        bottle(p, at_m(0.62, 0.22, z), 1.0)
        bottle(p, at_m(0.50, 0.30, z), 0.85, (0.42, 0.26, 0.10))
        bottle(p, at_m(0.70, -0.25, z + 0.055, 0.8, 1.5708), 0.9, (0.10, 0.24, 0.34))
        tankard(p, at_m(0.38, -0.12, z, 0.6), 1.0, seed)
        tankard(p, at_m(-0.72, 0.22, z, 2.6), 1.0, seed + 1)
        candle(p, (-0.70, -0.25, z), 0.16)
        candle(p, (-0.62, -0.30, z), 0.09)
        coins(p, (0.05, 0.30, z), 0.10, 0.03, seed, n=14)
        stool_geo(p, at_m(0.2, -0.85, 0), seed + 3)
        stool_geo(p, at_m(-0.5, 0.9, 0) @ Matrix.Rotation(0.2, 4, 'X'), seed + 4)
    p.export()


def stool(name, seed):
    if not want(name):
        return
    p = Prop(name)
    stool_geo(p, Matrix.Identity(4), seed)
    p.export()


def chair(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for sx in (-1, 1):
        beam(p, (sx * 0.22, 0.20, 0), (sx * 0.24, 0.27, 1.10), 0.055, 0.055, seed + sx, grey=0.3)
        beam(p, (sx * 0.22, -0.20, 0), (sx * 0.22, -0.20, 0.46), 0.055, 0.055, seed + 3 + sx, grey=0.3)
        beam(p, (sx * 0.22, -0.20, 0.20), (sx * 0.22, 0.22, 0.20), 0.035, 0.045, seed + 6 + sx, grey=0.3)
    for k in range(3):
        board(p, Matrix.Translation((0, -0.15 + 0.15 * k, 0.47)), (0.52, 0.14, 0.035), seed + 10 + k, 0.3)
    for k, z in enumerate((0.72, 0.98)):
        board(p, Matrix.Translation((0, 0.245 + 0.03 * k, z)) @ Matrix.Rotation(-0.06, 4, 'X'), (0.46, 0.03, 0.16), seed + 14 + k, 0.3)
    p.export()


def chest_geo(p, m, seed, L=1.0, W=0.62, H=0.42, open_=0.0, gold=False):
    R = W / 2
    grey = 0.15
    for k in range(3):
        zc = H * (k + 0.5) / 3
        for sgn in (-1, 1):
            board(p, m @ Matrix.Translation((0, sgn * (W / 2 - 0.02), zc)), (L, 0.04, H / 3 - 0.008), seed + k + sgn * 5, grey)
            board(p, m @ Matrix.Translation((sgn * (L / 2 - 0.02), 0, zc)), (0.04, W - 0.08, H / 3 - 0.008), seed + 20 + k + sgn * 5, grey)
    board(p, m @ Matrix.Translation((0, 0, 0.02)), (L - 0.06, W - 0.06, 0.04), seed + 40, grey)
    hinge = m @ Matrix.Translation((0, W / 2, H)) @ Matrix.Rotation(-open_, 4, 'X') @ Matrix.Translation((0, -W / 2, 0))
    n = 7
    iron = metal(rust=0.3)
    for k in range(n):
        a = math.pi * (k + 0.5) / n
        mm = hinge @ Matrix.Translation((0, math.cos(a) * (R - 0.02), math.sin(a) * (R - 0.02) * 0.72)) @ Matrix.Rotation(math.atan2(math.sin(a) * 0.72, math.cos(a)) - math.pi / 2, 4, 'X')
        board(p, mm, (L, 2 * R * math.sin(math.pi / (2 * n)) * 1.06, 0.035), seed + 50 + k, grey)
        for sx in (-0.36, 0.0, 0.36):
            ibox(p, mm @ Matrix.Translation((sx * L, 0, 0.022)), (0.075, 2 * R * math.sin(math.pi / (2 * n)) * 1.1, 0.014), iron)
    tint = lerp(wood_tint(seed + 60), WOOD_DARK, 0.2)
    for sgn in (-1, 1):
        ring = [hinge @ Vector((sgn * (L / 2 - 0.02), math.cos(a) * (R - 0.02), math.sin(a) * (R - 0.02) * 0.72)) for a in (math.pi * k / 10 for k in range(11))]
        fan(p, ring[:-1] + [ring[-1]], hinge @ Vector((sgn * (L / 2 - 0.02), 0, 0)), hinge.to_3x3() @ Vector((sgn, 0, 0)), tint)
        for a in (0.5, 1.2, 1.94, 2.64):
            pass
    for sx in (-0.36, 0.0, 0.36):
        for sgn in (-1, 1):
            ibox(p, m @ Matrix.Translation((sx * L, sgn * (W / 2 + 0.003), H / 2)), (0.075, 0.014, H), iron)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ibox(p, m @ Matrix.Translation((sx * (L / 2 - 0.03), sy * (W / 2 - 0.03), H / 2)), (0.085, 0.085, H + 0.01), iron, 0.01)
        hm = m @ Matrix.Translation((sx * (L / 2 + 0.005), 0, H * 0.62))
        pipe(p, [hm @ Vector((sx * 0.0, -0.11, 0)), hm @ Vector((sx * 0.07, -0.09, -0.05)), hm @ Vector((sx * 0.07, 0.09, -0.05)), hm @ Vector((sx * 0.0, 0.11, 0))], 0.014, iron, sides=4,
             up=m.to_3x3() @ Vector((0, 0, 1)))
    ibox(p, m @ Matrix.Translation((0, -W / 2 - 0.012, H - 0.06)), (0.15, 0.03, 0.17), gilt, 0.012)
    ibox(p, m @ Matrix.Translation((0, -W / 2 - 0.03, H - 0.08)), (0.03, 0.01, 0.06), (0.05, 0.04, 0.04))
    if open_ > 0.3:
        inner = m @ Matrix.Translation((0, 0, H * 0.55))
        if gold:
            c = m @ Vector((0, 0, H * 0.62))
            faces = p.blob(tuple(c), (L / 2 - 0.07, W / 2 - 0.07, 0.16), const((0, 0, 0)), seed, rough=0.22, subdiv=2)
            p.paint(faces, lambda co, nrm: lerp(GOLD_LO, GOLD_HI, clamp01(nrm.z * 0.6 + 0.3 + 0.45 * noise.noise(co * 20.0))))
            rnd = random.Random(seed)
            for k in range(26):
                q = m @ Vector((rnd.uniform(-0.38, 0.38) * L, rnd.uniform(-0.3, 0.3) * W, H * 0.62 + 0.14 + rnd.uniform(0.0, 0.03)))
                lathe(p, [(0.032, 0.0), (0.032, 0.008)], gilt, sides=7, smooth=False, m=Matrix.Translation(q) @ Matrix.Rotation(rnd.uniform(-0.7, 0.7), 4, 'X') @ Matrix.Rotation(rnd.uniform(-0.7, 0.7), 4, 'Y'))
            for k, tint in enumerate(((0.75, 0.10, 0.14), (0.12, 0.55, 0.36), (0.16, 0.36, 0.80))):
                q = m @ Vector((-0.25 + 0.25 * k, 0.05 - 0.08 * k, H * 0.62 + 0.18))
                p.blob(tuple(q), (0.05, 0.05, 0.06), lambda co, nrm, tint=tint: lerp(mul(tint, 0.5), lerp(tint, (1, 1, 1), 0.5), clamp01(nrm.z)), k, 0.0, 1)
        else:
            ibox(p, inner, (L - 0.10, W - 0.10, 0.02), (0.07, 0.05, 0.04))


def chest(name, seed, open_=0.0, gold=False):
    if not want(name):
        return
    p = Prop(name)
    chest_geo(p, Matrix.Identity(4), seed, open_=open_, gold=gold)
    if gold:
        coins(p, (0.75, -0.25, 0), 0.22, 0.07, seed, n=22)
    p.export()


def goblet(p, m, s=1.0):
    lathe(p, [(0.05 * s, 0.0), (0.055 * s, 0.012 * s), (0.016 * s, 0.03 * s), (0.014 * s, 0.10 * s), (0.03 * s, 0.12 * s), (0.06 * s, 0.17 * s), (0.065 * s, 0.24 * s), (0.055 * s, 0.24 * s),
              (0.05 * s, 0.18 * s), (0.004, 0.14 * s)], gilt, sides=10, m=m, cap=False)


def gold_pile(name, seed, big=True):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    coins(p, (0, 0, 0), 0.75 if big else 0.42, 0.42 if big else 0.2, seed, n=70 if big else 34)
    if big:
        coins(p, (0.7, 0.3, 0), 0.4, 0.2, seed + 1, n=24)
        goblet(p, at_m(0.35, -0.42, 0.20, 0.5, 0.5), 1.3)
        goblet(p, at_m(-0.52, 0.2, 0.14, 2.0, 1.3), 1.2)
        lathe(p, [(0.14, 0.0), (0.145, 0.07), (0.16, 0.075), (0.15, 0.13), (0.135, 0.075), (0.13, 0.0)], gilt, sides=10, m=at_m(-0.1, 0.1, 0.50, 0.2, 0.25), cap=False, smooth=False)
        for k, tint in enumerate(((0.75, 0.10, 0.14), (0.12, 0.55, 0.36), (0.16, 0.36, 0.80), (0.60, 0.20, 0.70), (0.75, 0.10, 0.14))):
            a = rnd.uniform(0, 6.28)
            p.blob((math.cos(a) * 0.4, math.sin(a) * 0.4, 0.30), (0.06, 0.06, 0.075), lambda co, nrm, tint=tint: lerp(mul(tint, 0.5), lerp(tint, (1, 1, 1), 0.5), clamp01(nrm.z)), k, 0.0, 1)
        m = at_m(-0.3, -0.5, 0.20, 0.8, -0.9)
        ibox(p, m @ Matrix.Translation((0, 0, 0.42)), (0.05, 0.012, 0.85), lambda co, nrm: lerp((0.45, 0.47, 0.52), (0.92, 0.94, 0.96), clamp01(nrm.z + 0.5)), 0.004)
        ibox(p, m @ Matrix.Translation((0, 0, -0.01)), (0.20, 0.04, 0.03), gilt, 0.008)
        ibox(p, m @ Matrix.Translation((0, 0, -0.09)), (0.035, 0.035, 0.14), LEATHER_D, 0.008)
    p.export()


def wheel_spoked(p, c, axis, r, seed, spokes=8):
    m = zto(c, axis)
    tint = wood_tint(seed)
    wood = lambda co, nrm: lerp(lerp(tint, WOOD_DARK, 0.55), tint, clamp01(0.5 + 0.5 * noise.noise(co * 5.0)))
    lathe(p, [(r - 0.09, -0.04), (r, -0.04), (r, 0.04), (r - 0.09, 0.04), (r - 0.09, -0.04)], wood, sides=14, m=m, smooth=False, cap=False)
    lathe(p, [(r + 0.01, -0.045), (r + 0.01, 0.045)], metal(rust=0.45), sides=14, m=m, smooth=False, cap=False)
    lathe(p, [(0.004, -0.09), (0.07, -0.09), (0.10, -0.05), (0.10, 0.05), (0.07, 0.09), (0.004, 0.09)], wood, sides=8, m=m, smooth=False, cap=False)
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        log(p, m @ Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0)), m @ Vector((math.cos(a) * (r - 0.07), math.sin(a) * (r - 0.07), 0)), 0.03, 0.026, seed + k, sides=5, wob=0.0, grey=0.2)


def cart(name, seed, load=True):
    if not want(name):
        return
    p = Prop(name)
    tilt = Matrix.Translation((0, 0, 0.62)) @ Matrix.Rotation(-0.13, 4, 'Y')
    for k in range(5):
        board(p, tilt @ Matrix.Translation((0, -0.44 + 0.22 * k, 0)), (1.9, 0.20, 0.04), seed + k, 0.4)
    for sgn in (-1, 1):
        for k in range(2):
            board(p, tilt @ Matrix.Translation((0, sgn * 0.56, 0.14 + 0.19 * k)), (1.9, 0.035, 0.17), seed + 10 + k + sgn, 0.4)
        beam(p, tilt @ Vector((-0.95, sgn * 0.52, -0.05)), tilt @ Vector((2.0, sgn * 0.42, -0.05)), 0.07, 0.07, seed + 20 + sgn, grey=0.35)
        for x in (-0.9, 0.0, 0.9):
            board(p, tilt @ Matrix.Translation((x, sgn * 0.585, 0.2)), (0.06, 0.04, 0.46), seed + 30, 0.3)
        wheel_spoked(p, (0.0, sgn * 0.68, 0.52), (0, sgn, 0), 0.52, seed + 40 + sgn)
    for x in (-0.94, 0.94):
        for k in range(2):
            board(p, tilt @ Matrix.Translation((x, 0, 0.14 + 0.19 * k)), (0.035, 1.1, 0.17), seed + 50 + k, 0.4)
    log(p, (0, -0.72, 0.52), (0, 0.72, 0.52), 0.05, 0.05, seed + 60, sides=7, wob=0.0, grey=0.2)
    beam(p, tilt @ Vector((1.45, 0, -0.06)), (1.6, 0, 0.0), 0.07, 0.07, seed + 61, grey=0.3)
    if load:
        cask(p, tilt @ at_m(-0.45, 0.12, 0.02, 0.4), 0.85, seed + 70)
        case(p, tilt @ at_m(0.45, -0.1, 0.02, 0.2), (0.6, 0.6, 0.45), seed + 71)
        sack(p, tuple(tilt @ Vector((0.42, 0.0, 0.47))), 0.75, seed + 72)
    p.export()


def well(name, seed):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    for layer in range(3):
        n = 9
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * layer) / n
            chunk(p, (math.cos(a) * 0.92, math.sin(a) * 0.92, 0.17 + 0.32 * layer), (0.30, 0.22, 0.17), seed + layer * 20 + k, 'ruin', pts=14, boxy=0.9, bevel=0.22, sub=0,
                  turn=a + math.pi / 2, moss=0.25 if layer == 2 else 0.0)
    disc(p, (0, 0, 0.35), 0.80, (0.07, 0.16, 0.20), 14)
    for sgn in (-1, 1):
        log(p, (sgn * 1.08, 0, -0.1), (sgn * 1.05, 0, 2.5), 0.085, 0.07, seed + sgn, sides=7, foot=0.4, wob=0.15)
        for sy in (-1, 1):
            beam(p, (sgn * 1.05, sy * 0.85, 2.30), (sgn * 1.05, 0, 2.95), 0.07, 0.09, seed + 5 + sy, grey=0.4, over=0.2)
    beam(p, (-1.25, 0, 2.95), (1.25, 0, 2.95), 0.08, 0.10, seed + 9, grey=0.4)
    for sy in (-1, 1):
        for k in range(5):
            t = (k + 0.5) / 5
            m = Matrix.Translation((0, sy * 0.88 * (1 - t), 2.28 + 0.68 * t)) @ Matrix.Rotation(sy * 0.655, 4, 'X')
            board(p, m, (2.7 + 0.04 * (k % 2), 0.26, 0.03), seed + 20 + k + sy, rnd.uniform(0.35, 0.6))
    log(p, (-1.25, 0, 1.75), (1.45, 0, 1.75), 0.05, 0.05, seed + 30, sides=7, wob=0.0)
    pipe(p, [Vector((1.45, 0, 1.75)), Vector((1.62, 0, 1.75)), Vector((1.62, 0, 1.50)), Vector((1.85, 0, 1.50))], 0.022, metal(), sides=5, up=Vector((0, 1, 0)))
    for k in range(5):
        pipe(p, [Vector((-0.2 + 0.07 * k, math.cos(q) * 0.075, 1.75 + math.sin(q) * 0.075)) for q in (2 * math.pi * j / 8 for j in range(8))], 0.02, rope_paint(), sides=4,
             up=Vector((1, 0, 0)), closed=True)
    rope(p, (0.0, 0.07, 1.75), (0.0, 0.07, 1.22), 0.018)
    cask(p, at_m(0.0, 0.07, 0.86), 0.36, seed + 40, lid=False)
    pipe(p, [Vector((-0.10, 0.07, 1.18)), Vector((0, 0.07, 1.26)), Vector((0.10, 0.07, 1.18))], 0.008, metal(), sides=4, up=Vector((0, 1, 0)))
    p.export()


def tent(name, seed, tint=CANVAS):
    if not want(name):
        return
    p = Prop(name)
    L, W, H = 2.8, 1.25, 1.75
    for x in (-L / 2, L / 2):
        for sy in (-1, 1):
            log(p, (x, sy * W, -0.05), (x, -sy * 0.08, H + 0.22), 0.045, 0.038, seed + int(x) + sy, sides=6, wob=0.1)
        lash(p, (x, 0, H - 0.02), 0.06, 3, 0.014)
    log(p, (-L / 2 - 0.35, 0, H + 0.06), (L / 2 + 0.35, 0, H + 0.06), 0.045, 0.04, seed + 9, sides=6, wob=0.05)
    for sy in (-1, 1):
        def pos(u, v, sy=sy):
            sagx = math.sin(math.pi * u)
            return Vector((-L / 2 - 0.12 + (L + 0.24) * u, sy * (W + 0.25) * v + sy * 0.04 * sagx * math.sin(math.pi * v), H + 0.10 - (H + 0.02) * v - 0.10 * sagx * math.sin(math.pi * v)
                           + 0.015 * math.sin(u * 23.0)))
        uvsheet(p, lambda u, v, pos=pos: pos(u, v) if sy > 0 else pos(1 - u, v),
                lambda u, v, nrm: lerp(lerp(mul(tint, 0.5), tint, clamp01(0.45 + 0.55 * nrm.z + 0.1 * noise.noise(Vector((u * 8, v * 8, seed))))), (0.42, 0.36, 0.28), clamp01((v - 0.7) * 1.4) * 0.6),
                12, 8)
        for x in (-L / 2 - 0.1, 0.0, L / 2 + 0.1):
            a = Vector((x, sy * (W + 0.25), 0.09))
            rope(p, a, a + Vector((0, sy * 0.45, -0.07)), 0.012)
            log(p, a + Vector((0, sy * 0.40, -0.14)), a + Vector((0, sy * 0.50, 0.14)), 0.022, 0.018, seed + 20, sides=5, wob=0.0)
    faces = p.blob((0.1, 0, 0.05), (1.0, 0.36, 0.06), const((0, 0, 0)), seed, rough=0.1, subdiv=2, smooth=True)
    p.paint(faces, lambda co, nrm: lerp((0.36, 0.14, 0.12), (0.62, 0.20, 0.16), clamp01(nrm.z + 0.2 * math.sin(co.x * 30.0))))
    lathe(p, [(0.004, -0.33), (0.15, -0.33), (0.16, 0.0), (0.15, 0.33), (0.004, 0.33)], const((0.50, 0.42, 0.30)), sides=10, m=zto((-0.9, 0, 0.17), (0, 1, 0)), cap=False)
    p.export()


def hammock(name, seed):
    if not want(name):
        return
    p = Prop(name)
    for sgn in (-1, 1):
        log(p, (sgn * 1.9, 0, -0.2), (sgn * 2.05, 0, 2.1), 0.10, 0.08, seed + sgn, sides=8, foot=0.4, wob=0.2)
        lash(p, (sgn * 2.02, 0, 1.62), 0.092, 3, 0.018)
        beam(p, (sgn * 1.2, 0, 0.0), (sgn * 1.96, 0, 1.1), 0.07, 0.08, seed + 4 + sgn, grey=0.4)

    def pos(u, v):
        x = -1.35 + 2.7 * u
        w = 0.48 * math.sin(math.pi * (0.12 + 0.76 * u)) ** 0.6
        return Vector((x, (v - 0.5) * 2 * w, 1.50 - 0.72 * math.sin(math.pi * u) ** 0.9 + 0.30 * (2 * v - 1) ** 2 * math.sin(math.pi * u)))
    uvsheet(p, pos, lambda u, v, nrm: lerp(mul(CANVAS, 0.5), CANVAS if int(v * 9) % 3 else (0.62, 0.20, 0.16), clamp01(0.4 + 0.6 * abs(nrm.z))), 16, 8)
    for sgn in (-1, 1):
        for v in (0.0, 0.5, 1.0):
            rope(p, pos(0.0 if sgn < 0 else 1.0, v), (sgn * 2.0, 0, 1.66), 0.012)
    p.export()


def dig_spot(name, seed):
    if not want(name):
        return
    p = Prop(name)
    sand = lambda co, nrm: lerp((0.62, 0.50, 0.32), (0.94, 0.84, 0.60), clamp01(nrm.z * 0.7 + 0.2 + 0.2 * noise.noise(co * 4.0)))
    faces = p.blob((0.9, 0.2, -0.05), (0.75, 0.6, 0.42), const((0, 0, 0)), seed, rough=0.22, subdiv=3, smooth=True)
    p.paint(faces, sand)
    lathe(p, [(0.75, 0.0), (0.62, -0.06), (0.5, -0.22), (0.3, -0.3), (0.004, -0.32)][::-1], lambda co, nrm: lerp((0.36, 0.28, 0.18), (0.80, 0.68, 0.46), clamp01(1.0 + co.z * 3.0)), sides=12, cap=False, inside=True)
    chest_geo(p, at_m(-0.02, 0.02, -0.34, 0.5, 0.0, 0.16, 0.8), seed)
    m = at_m(0.95, 0.15, 0.22, 0.7, 0.0, 0.0) @ Matrix.Rotation(-0.25, 4, 'Y')
    log(p, m @ Vector((0, 0, 0.1)), m @ Vector((0, 0, 1.25)), 0.025, 0.022, seed, sides=6, wob=0.05, grey=0.3)
    log(p, m @ Vector((-0.09, 0, 1.25)), m @ Vector((0.09, 0, 1.25)), 0.022, 0.022, seed + 1, sides=6, wob=0.0, grey=0.3)
    blade = [m @ Vector(v) for v in ((-0.10, 0, 0.12), (0.10, 0, 0.12), (0.11, 0.02, -0.10), (0.0, 0.03, -0.22), (-0.11, 0.02, -0.10))]
    fquad(p, blade, metal(rust=0.3))
    fquad(p, blade[::-1], metal(rust=0.5))
    p.export()


if want("LanternPost"):
    lantern_post("SM_BW_LanternPost", 3, 1)
    lantern_post("SM_BW_LanternPost_B", 7, 2, 4.2)
    lantern_post("SM_BW_LanternPost_C", 12, 1, 5.0, pennant=RED)
lantern_wall("SM_BW_Lantern_Wall")
lantern_hanging("SM_BW_Lantern_Hanging")
lantern_ground("SM_BW_Lantern_Ground")
brazier("SM_BW_Brazier")
tiki_torch("SM_BW_TikiTorch")
torch_wall("SM_BW_Torch_Wall")
campfire("SM_BW_Campfire")
campfire("SM_BW_Campfire_Spit", 9, spit=True)
mooring_post("SM_BW_MooringPost", 5)
mooring_post("SM_BW_MooringPost_B", 6, piles=3)
banner_pole("SM_BW_BannerPole", 4)
banner_pole("SM_BW_BannerPole_B", 14, TEAL, 5.4)
flag_pole("SM_BW_FlagPole", 2)
signpost("SM_BW_Signpost", 8)
signpost("SM_BW_Signpost_Hanging", 10, hanging=True)
fence_rope("SM_BW_Fence_Rope", 3)
fence_plank("SM_BW_Fence_Plank", 5)
ladder("SM_BW_Ladder", 4)
bench("SM_BW_Bench", 6)
net_rack("SM_BW_NetRack", 2)
net_rack("SM_BW_FishRack", 9, fishy=True)
anchor("SM_BW_Anchor", 3)
anchor("SM_BW_Anchor_Buried", 5, 3.0, buried=True)
cannon("SM_BW_Cannon", 4)
cannonballs("SM_BW_Cannonballs", 2)
capstan("SM_BW_Capstan", 5)
powder_keg("SM_BW_PowderKeg", 7)
rope_coil("SM_BW_RopeCoil", 1)
buoy("SM_BW_Buoy", 2)
crab_pot("SM_BW_CrabPot", 3)
barrel_stack("SM_BW_Barrel_Stack", 4)
barrel_stack("SM_BW_Barrel_Rack", 8, n=5)
crate_stack("SM_BW_Crate_Stack", 3)
crate_stack("SM_BW_Crate_Stack_Tarp", 6, tarped=True)
sack_pile("SM_BW_Sack_Pile", 2)
basket("SM_BW_Basket_Fruit", 3)
basket("SM_BW_Basket_Fish", 5, 'fish')
table("SM_BW_Table", 4)
table("SM_BW_Table_Set", 7, dressed=True)
stool("SM_BW_Stool", 2)
chair("SM_BW_Chair", 3)
chest("SM_BW_Chest", 5)
chest("SM_BW_Chest_Open", 6, open_=1.85, gold=True)
gold_pile("SM_BW_Gold_Pile", 3)
gold_pile("SM_BW_Gold_Small", 4, big=False)
cart("SM_BW_Cart", 6)
well("SM_BW_Well", 2)
tent("SM_BW_Tent", 5)
hammock("SM_BW_Hammock", 3)
dig_spot("SM_BW_DigSpot", 4)
