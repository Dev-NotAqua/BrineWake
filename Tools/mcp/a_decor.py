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
