# Brinewake crew and outpost folk, second pass (run through bl_run.py; a_rig.py then adds the skeleton and the animations).
# Caricature build: big head and jaw, bull neck, barrel chest or belly, heavy forearms, huge hands, short legs, big boots.
# Every figure stands in the same rest pose (arms hanging out from the body) and is skinned while it is built: each
# sculpted element names its bone, clothing and gear are tagged as they are added. Figures face -y, right hand at -x, metres.
from mathutils import Quaternion

MB_K = 0.57
_mb = [0]
GOLD_LO, GOLD_HI, OCHRE, BONE = (0.55, 0.36, 0.10), (1.0, 0.82, 0.36), (0.90, 0.64, 0.20), (0.90, 0.82, 0.62)
LEATHER, LEATHER_D = (0.42, 0.25, 0.13), (0.22, 0.13, 0.08)
ROPE_C = (0.70, 0.57, 0.36)
BONES = ['root', 'pelvis', 'spine_01', 'spine_02', 'neck', 'head', 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
         'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r']
BI = {n: i for i, n in enumerate(BONES)}
WANT = globals().get("BW_ONLY")


def sfx(side):
    return '_l' if side > 0 else '_r'


def lin(c):
    return (clamp01(c[0]), clamp01(c[1]), clamp01(c[2]), 1.0)


def setw(p, v, w):
    d = v[p.dl]
    d.clear()
    tot = sum(w.values())
    for b, x in w.items():
        if x / tot > 0.03:
            d[BI[b]] = x / tot


def mark(p):
    return len(p.bm.verts)


def tag(p, start, how):
    """Skin everything built since mark(): to one bone, or by a function of the position."""
    p.bm.verts.ensure_lookup_table()
    for i in range(start, len(p.bm.verts)):
        v = p.bm.verts[i]
        setw(p, v, how(v.co) if callable(how) else {how: 1.0})


def torso_w(co):
    z = co.z
    if z >= 1.36:
        return {'spine_02': 1.0}
    if z >= 1.14:
        t = (z - 1.14) / 0.22
        return {'spine_02': t, 'spine_01': 1.0 - t + 1e-4}
    if z >= 0.98:
        t = (z - 0.98) / 0.16
        return {'spine_01': t, 'pelvis': 1.0 - t + 1e-4}
    t = clamp01((0.98 - z) / 0.25)
    return {'pelvis': 1.0 - 0.6 * t, 'thigh' + ('_l' if co.x > 0 else '_r'): 0.6 * t + 1e-4}


def soft(base, lo=0.62, warm=0.0):
    """Clay-like paint: lit from above, earthier than the raw swatch, blotchy wear, grime toward the ground."""
    base = lerp(base, (0.42, 0.35, 0.29), 0.14)
    dark = (base[0] * (lo + warm), base[1] * lo, base[2] * (lo - warm * 0.5))

    def paint(co, nrm):
        c = lerp(dark, base, clamp01(nrm.z * 0.45 + 0.62 - nrm.y * 0.12))
        wear = noise.noise(co * 7.0) * 0.5 + noise.noise(co * 19.0) * 0.25
        c = lerp(c, (c[0] * 0.78, c[1] * 0.76, c[2] * 0.74), clamp01(wear + 0.25))
        return lerp(c, (c[0] * 0.72, c[1] * 0.68, c[2] * 0.62), clamp01((0.42 - co.z) / 0.42) * 0.5)
    return paint


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


def _prep(e):
    if e[0] == 'C':
        a, b = Vector(e[1]), Vector(e[2])
        return ('C', a, b - a, max((b - a).length_squared, 1e-9), e[3])
    return ('E', Vector(e[1]), e[2], e[3].inverted() if len(e) > 3 else None, min(e[2]))


def _dist(e, co):
    if e[0] == 'C':
        t = clamp01((co - e[1]).dot(e[2]) / e[3])
        return (co - (e[1] + e[2] * t)).length - e[4]
    l = co - e[1]
    if e[3] is not None:
        l = e[3] @ l
    r = e[2]
    return (math.sqrt((l.x / r[0]) ** 2 + (l.y / r[1]) ** 2 + (l.z / r[2]) ** 2) - 1.0) * e[4]


def sculpt(p, elements, colour, res=0.03, bones=None, soft_w=0.03):
    """Polygonise a family of metaball elements and add the skin to the prop, painted and skinned per vertex.
    ('E', centre, semi-axes[, quaternion]) is an ellipsoid, ('C', a, b, radius) a capsule; bones names one bone per element."""
    _mb[0] += 1
    mb = bpy.data.metaballs.new("BWmb%d" % _mb[0])
    mb.resolution = res
    for e in elements:
        if e[0] == 'E':
            el = mb.elements.new(type='ELLIPSOID')
            el.co, el.radius = Vector(e[1]), 1.0
            el.size_x, el.size_y, el.size_z = e[2][0] / MB_K, e[2][1] / MB_K, e[2][2] / MB_K
            if len(e) > 3:
                el.rotation = e[3]
        else:
            a, b = Vector(e[1]), Vector(e[2])
            el = mb.elements.new(type='CAPSULE')
            el.co, el.radius = (a + b) / 2, e[3] / MB_K
            el.size_x = max((b - a).length / 2, 0.001)
            el.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())
    ob = bpy.data.objects.new(mb.name, mb)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    prepped = [_prep(e) for e in elements]
    made = []
    for v in me.vertices:
        nv = p.bm.verts.new(v.co)
        made.append(nv)
        if isinstance(bones, str):
            setw(p, nv, {bones: 1.0})
        else:
            ds = [_dist(e, v.co) for e in prepped]
            dmin = min(ds)
            w = {}
            for d, b in zip(ds, bones):
                if d - dmin < 4.0 * soft_w:
                    w[b] = w.get(b, 0.0) + math.exp(-(d - dmin) / soft_w)
            setw(p, nv, w)
    for poly in me.polygons:
        try:
            f = p.bm.faces.new([made[i] for i in poly.vertices])
        except ValueError:
            continue
        f.smooth = True
        for loop, vi in zip(f.loops, poly.vertices):
            v = me.vertices[vi]
            loop[p.col] = lin(colour(v.co, v.normal))
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)


def ring(rx, ry, z, a0, a1, n, yoff=0.0):
    """Points round an ellipse, angle measured from the front (-y), from a0 to a1."""
    return [Vector((rx * math.sin(a0 + (a1 - a0) * k / n), -ry * math.cos(a0 + (a1 - a0) * k / n) + yoff, z)) for k in range(n + 1)]


def figure(name, sp):
    if WANT and not any(k in name for k in WANT):
        return
    p = Prop(name)
    p.dl = p.bm.verts.layers.deform.verify()
    g = sp.get
    sw, cw, cd = g('sw', 0.26), g('cw', 0.23), g('cd', 0.165)
    bw, bd, hw = g('bw', 0.20), g('bd', 0.17), g('hw', 0.14)
    ar, fr, lr, kr = g('ar', 0.078), g('fr', 0.082), g('lr', 0.105), g('kr', 0.082)
    hs, hand, boot = g('hs', 1.2), g('hand', 1.7), g('boot', 1.25)
    skin, shirt, trousers, boots, hair = g('skin', (0.86, 0.62, 0.47)), g('shirt', BONE), g('trousers', (0.25, 0.22, 0.20)), g('boots', LEATHER_D), g('hair', (0.20, 0.13, 0.08))
    stoop = g('stoop', 0.0)
    head_c = Vector((0, -stoop * 0.5, 1.79 - stoop * 0.3))

    def hp(dx, dy, dz):
        return head_c + Vector((dx, dy, dz)) * hs

    arms = {side: (Vector((side * sw, -stoop * 0.3, 1.49 - stoop * 0.2)), Vector((side * 0.40, 0.03, 1.20)), Vector((side * 0.45, -0.10, 0.96))) for side in (-1, 1)}
    legs = {side: (Vector((side * hw, 0, 0.95)), Vector((side * (hw + 0.015), -0.025, 0.52)), Vector((side * (hw + 0.03), 0.02, 0.10))) for side in (-1, 1)}
    peg, hook, bare_arms, barefoot = g('peg', 0), g('hook', 0), g('bare_arms', False), g('barefoot', False)
    # --- trousers
    el, bn = [('E', (0, 0.005, 0.97), (hw + 0.09 + g('hip', 0.0), max(bd * 0.9, 0.12), 0.14))], ['pelvis']
    for side in (-1, 1):
        hip, knee, ankle = legs[side]
        el.append(('C', hip, knee, lr))
        bn.append('thigh' + sfx(side))
        if side != peg:
            el.append(('C', knee, ankle.lerp(knee, 0.25), kr))
            bn.append('calf' + sfx(side))
    stripes_t = g('trouser_stripes')
    sculpt(p, el, (lambda co, nrm: soft(trousers if int(co.x * 26 + 100) % 2 else stripes_t)(co, nrm)) if stripes_t else soft(trousers), bones=bn)
    if g('patch_knee', True):                                        # a sewn patch on one knee
        k0 = legs[1][1]
        st = mark(p)
        fquad(p, [k0 + Vector((-0.06, -lr - 0.012, 0.10)), k0 + Vector((-0.06, -lr - 0.012, -0.03)), k0 + Vector((0.055, -lr - 0.006, -0.04)), k0 + Vector((0.06, -lr - 0.006, 0.09))],
              soft(lerp(trousers, (0.62, 0.50, 0.34), 0.6), 0.6))
        tag(p, st, 'thigh_l')
    # --- boots, bare feet or a peg
    for side in (-1, 1):
        hip, knee, ankle = legs[side]
        if side == peg:
            st = mark(p)
            p.tube([(knee + Vector((0, 0, -0.04)), 0.085, Vector((0, 0, 1))), (knee + Vector((0, 0, 0.05)), 0.10, Vector((0, 0, 1)))], soft(LEATHER), sides=10, smooth=False)
            pipe(p, [knee + Vector((0, 0, -0.03)), Vector((knee.x, knee.y + 0.01, 0.25)), Vector((knee.x, knee.y + 0.02, 0.0))], [0.062, 0.048, 0.038], soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.5)), sides=8,
                 up=Vector((0, 1, 0)))
            p.tube([(Vector((knee.x, knee.y + 0.02, 0.0)), 0.046, Vector((0, 0, 1))), (Vector((knee.x, knee.y + 0.02, 0.04)), 0.046, Vector((0, 0, 1)))], soft(IRON_LIGHT), sides=8, smooth=False)
            tag(p, st, 'calf' + sfx(side))
            continue
        if barefoot:
            sculpt(p, [('C', ankle + Vector((0, 0, 0.06)), ankle + Vector((0, 0, -0.03)), kr * 0.8), ('E', (ankle.x, -0.08, 0.05), (0.062, 0.15, 0.046)),
                       ('E', (ankle.x, -0.20, 0.04), (0.068, 0.045, 0.034))], soft(skin, 0.7, 0.05), res=0.022, bones=['calf' + sfx(side), 'foot' + sfx(side), 'foot' + sfx(side)])
            continue
        top = ankle.lerp(knee, g('boot_h', 0.64))
        sculpt(p, [('C', ankle + Vector((0, 0, -0.03)), top, kr + 0.024), ('E', (ankle.x, -0.085 * boot, 0.062), (0.074 * boot, 0.150 * boot, 0.062 * boot)),
                   ('E', (ankle.x, 0.03, 0.055), (0.066 * boot, 0.066 * boot, 0.055))], soft(boots, 0.55), res=0.025, bones=['calf' + sfx(side), 'foot' + sfx(side), 'foot' + sfx(side)])
        st = mark(p)
        p.tube([(top + Vector((0, 0, -0.03)), kr + 0.04, Vector((0, 0, 1))), (top + Vector((0, 0, 0.03)), kr + 0.075, Vector((0, 0, 1))), (top + Vector((0, 0, 0.09)), kr + 0.095, Vector((0, 0, 1)))],
               soft(lerp(boots, LEATHER, 0.55)), sides=12, smooth=False, cap=False)
        p.tube([(ankle + Vector((0, -0.01, 0.07)), kr + 0.036, Vector((0, 0, 1))), (ankle + Vector((0, -0.01, 0.12)), kr + 0.034, Vector((0, 0, 1)))], soft(LEATHER, 0.55), sides=12, smooth=False, cap=False)
        tag(p, st, 'calf' + sfx(side))
        st = mark(p)
        p.box((ankle.x, -0.115 * boot, 0.125), (0.085, 0.035, 0.06), soft(GOLD_HI, 0.5), bevel=0.012)
        tag(p, st, 'foot' + sfx(side))
    # --- torso (shirt) with shoulders; sleeves or bare arms
    torso = [('E', (0, -stoop * 0.25, 1.34 - stoop * 0.15), (cw, cd, 0.20)), ('E', (0, -0.02 - bd * 0.12, 1.10), (bw, bd, 0.18)), ('E', (0, 0.01 - stoop * 0.3, 1.50 - stoop * 0.2), (0.125, 0.10, 0.075))]
    tb = ['spine_02', 'spine_01', 'spine_02']
    if g('bust', 0.0):
        for side in (-1, 1):
            torso.append(('E', (side * 0.078, -cd * 0.78, 1.365), (g('bust'), g('bust'), g('bust'))))
            tb.append('spine_02')
    for side in (-1, 1):
        sh, elb, wr = arms[side]
        torso.append(('E', sh, (ar + 0.03, ar + 0.025, ar + 0.025)))
        tb.append('upperarm' + sfx(side))
        torso.append(('C', sh, elb if not bare_arms else sh.lerp(elb, 0.45), ar))
        tb.append('upperarm' + sfx(side))
        if not bare_arms and not g('rolled', False):
            torso.append(('C', elb, wr.lerp(elb, 0.12), fr))
            tb.append('lowerarm' + sfx(side))
    stripes = g('shirt_stripes')
    sculpt(p, torso, (lambda co, nrm: soft(shirt if int(co.z * 22) % 2 else stripes)(co, nrm)) if stripes else soft(shirt, 0.66), bones=tb)
    # --- skin: head, neck, hands, bare forearms
    jw, ns = g('jaw', 1.1), g('nose', 1.2)
    face = [('C', (0, 0.01 - stoop * 0.3, 1.50 - stoop * 0.2), hp(0, 0.01, -0.12), 0.058 * g('neck', 1.25)),
            ('E', hp(0, 0.012, 0.012), (0.108 * hs, 0.125 * hs, 0.125 * hs)), ('E', hp(0, -0.035, -0.06), (0.092 * hs * jw, 0.097 * hs, 0.080 * hs * jw)),
            ('E', hp(0, -0.098, -0.108 * jw), (0.050 * jw * hs, 0.042 * hs, 0.038 * hs)), ('E', hp(0, -0.140, -0.014), (0.032 * ns * hs, 0.048 * ns * hs, 0.038 * ns * hs)),
            ('E', hp(0, -0.108, 0.038), (0.090 * hs, 0.034 * hs, 0.025 * hs)), ('E', hp(0, -0.118, -0.078), (0.040 * hs, 0.020 * hs, 0.014 * hs))]
    for side in (-1, 1):
        face.append(('E', hp(side * 0.064, -0.088, -0.035), (0.042 * hs, 0.042 * hs, 0.042 * hs)))
        face.append(('E', hp(side * 0.114, 0.015, -0.008), (0.022 * hs, 0.034 * hs, 0.050 * hs)))
    nose_tip = hp(0, -0.17, -0.012)

    def skin_paint(co, nrm):
        c = soft(skin, 0.70, 0.06)(co, nrm)
        blush = clamp01(1.0 - (co - nose_tip).length / (0.08 * hs))
        cheek = max(clamp01(1.0 - (co - hp(0.065, -0.11, -0.04)).length / (0.05 * hs)), clamp01(1.0 - (co - hp(-0.065, -0.11, -0.04)).length / (0.05 * hs)))
        return lerp(c, (0.86, 0.44, 0.36), 0.42 * blush + 0.28 * cheek)

    sculpt(p, face, skin_paint, res=0.016, bones=['neck'] + ['head'] * (len(face) - 1))
    for side in (-1, 1):
        sh, elb, wr = arms[side]
        d = (wr - elb).normalized()
        parts, pb = [], []
        if bare_arms:
            parts += [('C', sh.lerp(elb, 0.4), elb, ar * 0.97), ('C', elb, wr, fr)]
            pb += ['upperarm' + sfx(side), 'lowerarm' + sfx(side)]
        elif g('rolled', False):
            parts += [('C', elb, wr, fr)]
            pb += ['lowerarm' + sfx(side)]
        if side == hook:
            if parts:
                sculpt(p, parts, soft(skin, 0.70, 0.06), res=0.02, bones=pb)
            st = mark(p)
            p.tube([(wr + d * -0.03, fr + 0.02, d), (wr + d * 0.07, fr + 0.005, d)], soft(IRON_LIGHT, 0.5), sides=10, smooth=False)
            c0 = wr + d * 0.18
            pipe(p, [wr + d * 0.07, wr + d * 0.15] + [c0 + (d * math.cos(a) + Vector((0, -1, 0)) * math.sin(a)) * 0.07 for a in (math.radians(q) for q in (150, 90, 30, -30, -80))],
                 [0.026, 0.024, 0.023, 0.022, 0.019, 0.015, 0.009], soft(IRON_LIGHT, 0.5), sides=6, up=Vector((1, 0, 0)))
            tag(p, st, 'hand' + sfx(side))
            continue
        q = Vector((0, 0, 1)).rotation_difference(d)
        hc = wr + d * 0.07 * hand
        parts += [('C', wr.lerp(elb, 0.08), wr + d * 0.02, fr * 0.88), ('E', hc, (0.046 * hand, 0.031 * hand, 0.060 * hand), q),
                  ('E', hc + d * 0.058 * hand, (0.041 * hand, 0.027 * hand, 0.044 * hand), q),
                  ('C', hc + Vector((0, -0.02, 0)), hc + Vector((0, -0.055 * hand, 0)) + d * 0.045 * hand, 0.017 * hand)]
        pb += ['lowerarm' + sfx(side), 'hand' + sfx(side), 'hand' + sfx(side), 'hand' + sfx(side)]
        sculpt(p, parts, soft(skin, 0.70, 0.06), res=0.018, bones=pb)
    # --- eyes, brows, mouth, ear rings
    st = mark(p)
    for side in (-1, 1):
        if side == g('patch', 0):
            p.blob(hp(side * 0.047, -0.118, 0.008), (0.034 * hs, 0.014 * hs, 0.032 * hs), soft((0.07, 0.06, 0.06)), 1, 0.0, 2, smooth=True)
            continue
        p.blob(hp(side * 0.046, -0.112, 0.006), (0.020 * hs, 0.016 * hs, 0.019 * hs), lambda co, nrm: (0.96, 0.95, 0.90), 1, 0.0, 2, smooth=True)
        p.blob(hp(side * 0.046, -0.127, 0.004), (0.011 * hs, 0.006 * hs, 0.012 * hs), lambda co, nrm: g('eye', (0.16, 0.10, 0.06)), 1, 0.0, 2, smooth=True)
    if g('patch', 0):
        s = g('patch')
        pipe(p, [hp(s * 0.047, -0.125, 0.03), hp(s * 0.10, -0.06, 0.07), hp(s * 0.06, 0.12, 0.09), hp(-s * 0.08, 0.10, 0.06), hp(-s * 0.105, -0.03, 0.01), hp(-s * 0.02, -0.13, 0.015)],
             0.008, (0.07, 0.06, 0.06), sides=4, up=Vector((0, 0, 1)), closed=True)
    for side in g('earring', (1,)):
        c = hp(side * 0.128, 0.018, -0.075)
        pipe(p, [c + Vector((0, math.cos(a) * 0.024, math.sin(a) * 0.024)) for a in (2 * math.pi * k / 8 for k in range(8))], 0.006, soft(GOLD_HI, 0.5), sides=4, up=Vector((1, 0, 0)), closed=True)
    hairs = []
    for side in (-1, 1):
        hairs.append(('E', hp(side * 0.05, -0.124, 0.042 + 0.006 * g('brow', 1.3)), (0.033 * hs, 0.013 * hs, 0.012 * hs * g('brow', 1.3)), Quaternion((0, 1, 0), side * -0.25)))
    style = g('hair_style', 'short')
    if style == 'short':
        hairs += [('E', hp(0, 0.03, 0.05), (0.112 * hs, 0.125 * hs, 0.105 * hs))]
    elif style == 'long':
        hairs += [('E', hp(0, 0.04, 0.045), (0.115 * hs, 0.125 * hs, 0.11 * hs)), ('E', hp(0, 0.10, -0.10), (0.10 * hs, 0.06 * hs, 0.14 * hs)), ('E', hp(0, 0.11, -0.22), (0.075, 0.05, 0.10))]
    elif style == 'tuft':
        hairs += [('E', hp(side * 0.10, 0.03, -0.01), (0.03 * hs, 0.07 * hs, 0.05 * hs)) for side in (-1, 1)] + [('E', hp(0, 0.10, -0.02), (0.09 * hs, 0.04 * hs, 0.06 * hs))]
    elif style == 'bun':
        hairs += [('E', hp(0, 0.035, 0.05), (0.113 * hs, 0.126 * hs, 0.106 * hs)), ('E', hp(0, 0.13, 0.09), (0.055 * hs, 0.055 * hs, 0.055 * hs))]
    elif style == 'mohawk':
        hairs += [('E', hp(0, 0.01 + 0.035 * k, 0.12 - 0.012 * k * k * 0.4), (0.022 * hs, 0.04 * hs, 0.05 * hs)) for k in range(-2, 4)]
    elif style == 'braid':
        hairs += [('E', hp(0, 0.04, 0.045), (0.115 * hs, 0.125 * hs, 0.11 * hs))] + [('E', hp(0.07, 0.10, -0.08 - 0.07 * k), (0.034, 0.034, 0.042)) for k in range(5)]
    beard = g('beard', 'none')
    if beard in ('full', 'long'):
        hairs += [('E', hp(0, -0.075, -0.115), (0.090 * jw * hs, 0.064 * hs, 0.074 * hs)), ('E', hp(0, -0.07, -0.17 if beard == 'full' else -0.25), (0.064 * jw * hs, 0.048 * hs, (0.064 if beard == 'full' else 0.13) * hs))]
        hairs += [('E', hp(side * 0.088, -0.03, -0.075), (0.032 * hs, 0.064 * hs, 0.074 * hs)) for side in (-1, 1)]
    if beard in ('full', 'long', 'moustache'):
        hairs += [('E', hp(side * 0.037, -0.134, -0.054), (0.044 * hs, 0.022 * hs, 0.020 * hs), Quaternion((0, 1, 0), side * 0.35)) for side in (-1, 1)]
        if beard == 'moustache':
            hairs += [('E', hp(side * 0.078, -0.117, -0.078), (0.024 * hs, 0.018 * hs, 0.034 * hs)) for side in (-1, 1)]
    if beard == 'chops':
        hairs += [('E', hp(side * 0.092, -0.04, -0.07), (0.03 * hs, 0.06 * hs, 0.08 * hs)) for side in (-1, 1)]
    if beard == 'stubble':
        p.box(tuple(hp(0, -0.130, -0.062)), (0.055 * hs, 0.012, 0.011), lambda co, nrm: (0.35, 0.16, 0.14))
    elif beard in ('none', 'chops'):
        p.box(tuple(hp(0, -0.129, -0.064)), (0.06 * hs, 0.012, 0.013), lambda co, nrm: g('lips', (0.40, 0.17, 0.15)))
    tag(p, st, 'head')
    sculpt(p, hairs, soft(hair, 0.55), res=0.014, bones='head')
    # --- belt, buckle, sash, bandolier
    st = mark(p)
    wr_x, wr_y = max(bw, cw * 0.82) + 0.012, bd + 0.02
    belt = [v for v in ring(wr_x, wr_y, 1.02, 0, 2 * math.pi, 20, yoff=-0.02 - bd * 0.12)][:-1]
    pipe(p, belt, 0.040, soft(g('belt', LEATHER), 0.55), sides=6, closed=True)
    p.box((0, -wr_y - 0.050 - bd * 0.12, 1.02), (0.12, 0.035, 0.115), soft(GOLD_HI, 0.5), bevel=0.016)
    p.box((0, -wr_y - 0.062 - bd * 0.12, 1.02), (0.06, 0.02, 0.055), soft(LEATHER_D, 0.5))
    if g('sash'):
        sc = g('sash')
        sash = ring(wr_x + 0.014, wr_y + 0.014, 1.10, 0, 2 * math.pi, 20, yoff=-0.02 - bd * 0.12)
        low = [v + Vector((0, 0, -0.11)) for v in sash]
        for k in range(20):
            fquad(p, [low[k], low[k + 1], sash[k + 1], sash[k]], soft(sc), smooth=True)
        x0 = wr_x * 0.8
        fquad(p, [Vector((x0, -wr_y * 0.6, 1.0)), Vector((x0 + 0.08, -wr_y * 0.5, 1.0)), Vector((x0 + 0.13, -wr_y * 0.45, 0.62)), Vector((x0 + 0.02, -wr_y * 0.62, 0.68))], soft(sc, 0.5))
        fquad(p, [Vector((x0 + 0.02, -wr_y * 0.62, 0.68)), Vector((x0 + 0.13, -wr_y * 0.45, 0.62)), Vector((x0 + 0.08, -wr_y * 0.5, 1.0)), Vector((x0, -wr_y * 0.6, 1.0))], soft(sc, 0.45))
    if g('bandolier'):
        rx, ry = cw + 0.03, cd + 0.035
        strap = []
        for k in range(18):
            a = 2 * math.pi * k / 18
            x = rx * math.sin(a)
            strap.append(Vector((x, -ry * math.cos(a) - stoop * 0.2, 1.27 + 0.95 * x)))
        pipe(p, strap, 0.030, soft(g('bandolier'), 0.55), sides=5, closed=True)
        p.box((0.02, -ry - 0.035 - stoop * 0.2, 1.29), (0.085, 0.03, 0.085), soft(GOLD_HI, 0.5), bevel=0.012)
    tag(p, st, torso_w)
    # --- coat or vest: an open-fronted shell with collar, lapels, trim, a ragged hem and cuffs
    coat = g('coat')
    if coat:
        st = mark(p)
        cc, ctrim, bottom = coat['col'], coat.get('trim', OCHRE), coat.get('bottom', 0.60)
        levels = [(1.555, 0.135, 0.112, 0.30), (1.50, sw + 0.012, cd * 0.88, 0.34), (1.36, cw + 0.038, cd + 0.038, 0.42), (1.18, max(bw, cw * 0.86) + 0.038, bd + 0.042, 0.50),
                  (1.02, max(bw, cw * 0.84) + 0.045, bd + 0.05, 0.55)]
        if bottom < 1.0:
            for k in range(1, 5):
                z = 1.02 - (1.02 - bottom) * k / 4
                fl = 0.04 * k
                levels.append((z, max(bw, cw * 0.84) + 0.045 + fl, bd + 0.05 + fl * 1.3, 0.55 + 0.07 * k))
        rings_ = [ring(rx, ry, z - stoop * 0.15 * max(0.0, z - 1.1), a0, 2 * math.pi - a0, 22, yoff=-0.02 - (bd * 0.12 if z < 1.25 else stoop * 0.25)) for z, rx, ry, a0 in levels]
        if bottom < 1.0:
            for k, v in enumerate(rings_[-1]):
                v.z += 0.045 * math.sin(k * 2.7) - 0.02 * (k % 2)
        for a, b in zip(rings_, rings_[1:]):
            for k in range(22):
                fquad(p, [a[k], b[k], b[k + 1], a[k + 1]], soft(cc, 0.6), smooth=True)
                fquad(p, [a[k + 1], b[k + 1], b[k], a[k]], soft(lerp(cc, (0.1, 0.08, 0.08), 0.45), 0.6), smooth=True)
        for edge in (0, -1):                                        # trim down both front edges, buttons on one
            pipe(p, [r[edge] for r in rings_], 0.014, soft(ctrim, 0.55), sides=4, up=Vector((1, 0, 0)))
        for k in range(1, 4):
            q = rings_[1][0].lerp(rings_[4][0], k / 4)
            p.blob((q.x + 0.035, q.y - 0.014, q.z), (0.018, 0.01, 0.018), soft(GOLD_HI, 0.5), k, 0.0, 1, smooth=True)
        for side, edge in ((1, 0), (-1, -1)):                       # lapels
            a, b = rings_[1][edge], rings_[3][edge]
            fquad(p, [a, a + Vector((side * 0.095, -0.035, -0.06)), b], soft(lerp(cc, ctrim, 0.25), 0.6))
        pipe(p, ring(0.115, 0.098, 1.585 - stoop * 0.2, 0.5, 2 * math.pi - 0.5, 12, yoff=0.01 - stoop * 0.3), 0.032, soft(lerp(cc, (0, 0, 0), 0.15), 0.6), sides=5)
        tag(p, st, torso_w)
        sleeves, sb = [], []
        for side in (-1, 1):
            sh, elb, wr = arms[side]
            sleeves += [('E', sh, (ar + 0.045, ar + 0.04, ar + 0.04)), ('C', sh, elb, ar + 0.02), ('C', elb, wr.lerp(elb, 0.18), fr + 0.02)]
            sb += ['upperarm' + sfx(side), 'upperarm' + sfx(side), 'lowerarm' + sfx(side)]
        sculpt(p, sleeves, soft(cc, 0.6), bones=sb)
        for side in (-1, 1):
            sh, elb, wr = arms[side]
            d = (wr - elb).normalized()
            c = wr.lerp(elb, 0.2)
            st = mark(p)
            p.tube([(c - d * 0.04, fr + 0.03, d), (c + d * 0.05, fr + 0.062, d)], soft(ctrim, 0.55), sides=10, smooth=False, cap=False)
            tag(p, st, 'lowerarm' + sfx(side))
            if coat.get('epaulettes'):
                st = mark(p)
                top = sh + Vector((side * 0.02, 0, ar + 0.035))
                p.tube([(top, 0.10, Vector((side * 0.3, 0, 1))), (top + Vector((0, 0, 0.022)), 0.085, Vector((side * 0.3, 0, 1)))], soft(GOLD_HI, 0.5), sides=10, smooth=False)
                for k in range(8):
                    a = math.pi * 2 * k / 8
                    q = top + Vector((math.cos(a) * 0.095, math.sin(a) * 0.095, 0))
                    pipe(p, [q, q + Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, -0.07))], 0.01, soft(GOLD_HI, 0.5), sides=4)
                tag(p, st, 'upperarm' + sfx(side))
    # --- apron
    if g('apron'):
        st = mark(p)
        ac = g('apron')
        rows = [(1.36, cw * 0.62, cd + 0.03), (1.18, max(bw, cw * 0.8) * 0.8, bd + 0.045), (1.02, max(bw, cw * 0.8) * 0.9, bd + 0.05), (0.80, hw + 0.13, bd * 0.8 + 0.05), (0.56, hw + 0.15, 0.13)]
        grid = [[Vector((hwid * u, -ry * math.cos(u * 0.9) - 0.02 - (bd * 0.12 if z < 1.25 else 0.0), z)) for u in (-1, -0.5, 0, 0.5, 1)] for z, hwid, ry in rows]
        for a, b in zip(grid, grid[1:]):
            for k in range(4):
                fquad(p, [a[k], b[k], b[k + 1], a[k + 1]], soft(ac, 0.6), smooth=True)
        for side in (-1, 1):
            pipe(p, [grid[0][0 if side < 0 else 4], Vector((side * 0.09, -0.02, 1.53)), Vector((side * 0.05, 0.09, 1.55))], 0.012, soft(lerp(ac, LEATHER_D, 0.5)), sides=4, up=Vector((1, 0, 0)))
        tag(p, st, torso_w)
    # --- headwear
    hat = g('hat', 'none')
    hc = g('hat_col', (0.12, 0.10, 0.10))
    hz = hp(0, 0, 0.085).z
    st = mark(p)
    if hat == 'tricorn':
        sculpt(p, [('E', hp(0, 0.015, 0.105), (0.118 * hs, 0.13 * hs, 0.075 * hs))], soft(hc, 0.6), res=0.018, bones='head')
        n = 30
        inner = [Vector((head_c.x + 0.125 * hs * math.sin(a), head_c.y + 0.015 - 0.135 * hs * math.cos(a), hz)) for a in (2 * math.pi * k / n for k in range(n + 1))]
        outer = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            c3 = math.cos(3 * a)                                     # 1 at the three corners (one over the brow), -1 mid-side
            r = (0.285 + 0.09 * c3) * hs
            outer.append(Vector((head_c.x + r * math.sin(a), head_c.y + 0.015 - r * math.cos(a), hz + 0.02 + 0.125 * hs * (1 - c3) / 2)))
        for k in range(n):
            fquad(p, [inner[k], outer[k], outer[k + 1], inner[k + 1]], soft(hc, 0.55), smooth=True)
            fquad(p, [inner[k + 1], outer[k + 1], outer[k], inner[k]], soft(hc, 0.45), smooth=True)
        pipe(p, outer[:-1], 0.014, soft(g('hat_trim', OCHRE), 0.55), sides=4, up=Vector((0, 0, 1)), closed=True)
        if g('feather'):
            f0 = hp(0.10, 0.06, 0.15)
            pts = [f0 + Vector((0.02 * k, 0.045 * k, 0.05 * k - 0.006 * k * k)) for k in range(7)]
            for a, b, k in zip(pts, pts[1:], range(6)):
                w = 0.05 * math.sin(math.pi * (k + 0.7) / 7)
                fquad(p, [a + Vector((w, 0, 0)), b + Vector((w, 0, 0)), b - Vector((w, 0, 0)), a - Vector((w, 0, 0))], soft(g('feather'), 0.6))
                fquad(p, [a - Vector((w, 0, 0)), b - Vector((w, 0, 0)), b + Vector((w, 0, 0)), a + Vector((w, 0, 0))], soft(g('feather'), 0.5))
    elif hat == 'bandana':
        sculpt(p, [('E', hp(0, 0.02, 0.06), (0.116 * hs, 0.132 * hs, 0.095 * hs)), ('E', hp(0.03, 0.14, 0.02), (0.038, 0.034, 0.034))], soft(hc, 0.6), res=0.016, bones='head')
        for k in (0, 1):
            a = hp(0.03, 0.15, 0.01)
            tri = [a, a + Vector((0.06 + 0.05 * k, 0.06, -0.18)), a + Vector((0.0 + 0.05 * k, 0.08, -0.23))]
            fquad(p, tri, soft(hc, 0.5))
            fquad(p, tri[::-1], soft(hc, 0.45))
    elif hat == 'widebrim':
        sculpt(p, [('E', hp(0, 0.015, 0.13), (0.112 * hs, 0.125 * hs, 0.10 * hs))], soft(hc, 0.6), res=0.018, bones='head')
        n = 28
        inner = [Vector((head_c.x + 0.12 * hs * math.sin(a), head_c.y + 0.015 - 0.13 * hs * math.cos(a), hz + 0.01)) for a in (2 * math.pi * k / n for k in range(n + 1))]
        outer = [Vector((head_c.x + 0.33 * hs * math.sin(a), head_c.y + 0.015 - 0.34 * hs * math.cos(a), hz - 0.02 + 0.035 * math.sin(a * 2 + 1.0) - 0.03 * math.cos(a)))
                 for a in (2 * math.pi * k / n for k in range(n + 1))]
        for k in range(n):
            fquad(p, [inner[k], outer[k], outer[k + 1], inner[k + 1]], soft(hc, 0.55), smooth=True)
            fquad(p, [inner[k + 1], outer[k + 1], outer[k], inner[k]], soft(hc, 0.45), smooth=True)
        pipe(p, [v + Vector((0, 0, 0.012)) for v in inner[:-1]], 0.018, soft(g('hat_trim', OCHRE), 0.55), sides=4, closed=True)
    elif hat == 'cap':
        sculpt(p, [('E', hp(0, 0.02, 0.07), (0.117 * hs, 0.133 * hs, 0.09 * hs)), ('E', hp(0, -0.10, 0.045), (0.09 * hs, 0.075 * hs, 0.014))], soft(hc, 0.6), res=0.016, bones='head')
    elif hat == 'hood':
        sculpt(p, [('E', hp(0, 0.035, 0.03), (0.135 * hs, 0.14 * hs, 0.15 * hs)), ('E', hp(0, 0.06, -0.12), (0.14, 0.11, 0.10)), ('E', hp(0, -0.03, 0.14), (0.10 * hs, 0.11 * hs, 0.05 * hs))],
               soft(hc, 0.55), res=0.018, bones='head')
    elif hat == 'chef':
        sculpt(p, [('E', hp(0, 0.02, 0.10), (0.112 * hs, 0.125 * hs, 0.05 * hs)), ('E', hp(0, 0.03, 0.20), (0.14 * hs, 0.14 * hs, 0.085 * hs))], soft(hc, 0.7), res=0.018, bones='head')
    tag(p, st, 'head')
    extra = g('extra')
    if extra:
        extra(p, arms, legs, hp, sp)
    p.export()
    ob = bpy.data.objects[name]
    for b in BONES:
        ob.vertex_groups.new(name=b)
    ob["bw_rig"] = True


def held(arms, side):
    """Palm position of a hand, to put something in it."""
    sh, elb, wr = arms[side]
    return wr + (wr - elb).normalized() * 0.13


# ----- gear: each piece is tagged to the bone that carries it -----
def gear_mug(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, -1) + Vector((0, -0.07, -0.02))
    p.tube([(h + Vector((0, 0, -0.09)), 0.068, Vector((0, 0, 1))), (h + Vector((0, 0, 0.10)), 0.076, Vector((0, 0, 1)))], soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.6)), sides=12, smooth=False)
    p.blob(h + Vector((0, 0, 0.11)), (0.07, 0.07, 0.035), lambda co, nrm: (0.97, 0.94, 0.86), 1, 0.25, 2, smooth=True)
    for zz in (-0.06, 0.07):
        p.tube([(h + Vector((0, 0, zz - 0.012)), 0.08, Vector((0, 0, 1))), (h + Vector((0, 0, zz + 0.012)), 0.08, Vector((0, 0, 1)))], soft(IRON_LIGHT, 0.5), sides=12, smooth=False, cap=False)
    tag(p, st, 'hand_r')
    st = mark(p)
    q = [Vector((0.03, -0.03, 1.02)), Vector((0.18, -0.01, 1.02)), Vector((0.22, 0.0, 0.70)), Vector((0.05, -0.04, 0.72))]
    fquad(p, q, soft((0.86, 0.84, 0.78), 0.6))
    fquad(p, q[::-1], soft((0.80, 0.78, 0.72), 0.6))
    tag(p, st, 'pelvis')


def gear_mallet(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, -1)
    spar(p, h + Vector((0, 0.10, 0.10)), h + Vector((0, -0.34, -0.14)), 0.026, 0.024, 3, sides=6)
    m = Matrix.Translation(h + Vector((0, -0.38, -0.16))) @ Matrix.Rotation(0.35, 4, 'X')
    p.box((0, 0, 0), (0.15, 0.16, 0.30), soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.55)), bevel=0.025, xform=m)
    tag(p, st, 'hand_r')
    st = mark(p)
    for k in range(3):                                              # chisels in the apron pocket
        p.box((-0.07 + 0.05 * k, -sp.get('bd', 0.17) - 0.09, 1.0), (0.022, 0.016, 0.15), soft(IRON_LIGHT, 0.5))
    tag(p, st, 'spine_01')


def gear_lantern_staff(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, -1)
    top = Vector((h.x, h.y, 2.55))
    spar(p, Vector((h.x, h.y, 0.02)), top, 0.028, 0.022, 5, sides=6)
    pipe(p, [top, top + Vector((0.0, -0.18, 0.11)), top + Vector((0.0, -0.29, 0.0))], 0.016, soft(IRON_LIGHT, 0.5), sides=5, up=Vector((1, 0, 0)))
    lantern(p, tuple(top + Vector((0.0, -0.29, -0.24))))
    tag(p, st, 'hand_r')
    st = mark(p)
    for k in range(3):                                              # storm charms on the belt
        p.blob((0.12 + 0.05 * k, -sp.get('bd', 0.17) - 0.05, 0.93), (0.018, 0.018, 0.034), soft((0.75, 0.86, 0.90)), k, 0.0, 1, smooth=True)
    tag(p, st, 'pelvis')


def gear_ledger(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, 1)
    m = Matrix.Translation(h + Vector((0.02, -0.04, -0.06))) @ Matrix.Rotation(0.2, 4, 'Z')
    p.box((0, 0, 0), (0.06, 0.26, 0.34), soft((0.45, 0.14, 0.12), 0.6), bevel=0.012, xform=m)
    p.box((0, 0, 0), (0.045, 0.24, 0.32), lambda co, nrm: BONE, xform=m @ Matrix.Translation((0, -0.012, 0)))
    tag(p, st, 'hand_l')
    st = mark(p)
    for side in (-1, 1):                                            # spectacles
        pipe(p, [hp(side * 0.046, -0.137, 0.006) + Vector((math.cos(a) * 0.027, 0, math.sin(a) * 0.025)) for a in (2 * math.pi * k / 10 for k in range(10))], 0.0045,
             soft(GOLD_HI, 0.5), sides=4, up=Vector((0, 1, 0)), closed=True)
    tag(p, st, 'head')
    st = mark(p)
    bd = sp.get('bd', 0.17)
    p.blob((-0.2, -bd - 0.03, 0.93), (0.07, 0.06, 0.085), soft(LEATHER, 0.55), 3, 0.15, 2, smooth=True)       # fat coin purse
    p.box((-0.2, -bd - 0.03, 1.0), (0.05, 0.05, 0.03), soft(GOLD_HI, 0.5))
    tag(p, st, 'pelvis')


def gear_diver(p, arms, legs, hp, sp):
    st = mark(p)
    for side in (-1, 1):                                            # goggles pushed up on the brow
        pipe(p, [hp(side * 0.048, -0.120, 0.078) + Vector((math.cos(a) * 0.032, 0, math.sin(a) * 0.028)) for a in (2 * math.pi * k / 10 for k in range(10))], 0.009,
             soft(GOLD_HI, 0.5), sides=5, up=Vector((0, 1, 0)), closed=True)
        p.blob(hp(side * 0.048, -0.118, 0.078), (0.026, 0.006, 0.022), lambda co, nrm: (0.55, 0.80, 0.85), 1, 0.0, 1, smooth=True)
    tag(p, st, 'head')
    st = mark(p)
    sh = arms[1][0]
    for k in range(4):                                              # rope coil over the shoulder
        c = sh + Vector((-0.12, 0.0, -0.22))
        pipe(p, [c + Vector((math.sin(a) * 0.05 + 0.014 * k, math.cos(a) * 0.22, math.sin(a + 0.4) * 0.32)) for a in (2 * math.pi * q / 14 for q in range(14))], 0.018, soft(ROPE_C), sides=5,
             up=Vector((1, 0, 0)), closed=True)
    tag(p, st, 'spine_02')
    st = mark(p)
    p.box((-0.23, -0.02, 0.86), (0.04, 0.055, 0.28), soft(LEATHER, 0.55), bevel=0.01)       # sheathed knife
    p.box((-0.23, -0.02, 1.03), (0.034, 0.04, 0.10), soft(BONE))
    tag(p, st, 'pelvis')


def blade(p, m, length=0.72):
    steel = lambda co, nrm: lerp((0.36, 0.38, 0.44), (0.92, 0.94, 0.97), clamp01(0.4 + 0.6 * abs(nrm.x)))
    p.box((0, 0.02, length / 2 + 0.07), (0.014, 0.075, length), steel, bevel=0.006, xform=m)
    p.box((0, 0, 0.065), (0.035, 0.17, 0.028), soft(GOLD_HI, 0.5), bevel=0.01, xform=m)
    p.box((0, 0, -0.01), (0.034, 0.04, 0.14), soft(LEATHER_D, 0.6), bevel=0.01, xform=m)
    p.blob(tuple(m @ Vector((0, 0, -0.09))), (0.028, 0.028, 0.028), soft(GOLD_HI, 0.5), 1, 0.0, 1, smooth=True)


def gear_cutlass(p, arms, legs, hp, sp):
    st = mark(p)
    x = max(sp.get('bw', 0.20), sp.get('cw', 0.23) * 0.84) + 0.07
    m = Matrix.Translation((x, 0.02, 0.98)) @ Matrix.Rotation(math.pi - 0.45, 4, 'X')
    p.box((0, 0.02, 0.44), (0.04, 0.095, 0.74), soft(LEATHER_D, 0.6), bevel=0.012, xform=m)                      # scabbard
    p.box((0, 0.02, 0.80), (0.046, 0.075, 0.06), soft(GOLD_HI, 0.5), bevel=0.01, xform=m)
    p.box((0, 0, 0.065), (0.035, 0.17, 0.028), soft(GOLD_HI, 0.5), bevel=0.01, xform=m)
    p.box((0, 0, -0.01), (0.034, 0.04, 0.14), soft(LEATHER, 0.6), bevel=0.01, xform=m)
    tag(p, st, 'pelvis')


def gear_pistols(p, arms, legs, hp, sp):
    st = mark(p)
    bd = sp.get('bd', 0.17)
    for side in (-1, 1):
        m = Matrix.Translation((side * 0.10, -bd - 0.06, 1.03)) @ Matrix.Rotation(side * 0.5, 4, 'Y')
        p.box((0, 0, -0.10), (0.04, 0.045, 0.24), soft(IRON_LIGHT, 0.5), bevel=0.01, xform=m)
        p.box((side * 0.03, 0, 0.06), (0.10, 0.045, 0.06), soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.5), 0.6), bevel=0.014, xform=m)
        p.box((0, -0.01, 0.02), (0.02, 0.03, 0.05), soft(GOLD_HI, 0.5), xform=m)
    tag(p, st, 'pelvis')


def gear_spyglass(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, -1)
    d = Vector((0.0, -1.0, -0.25)).normalized()
    brass = lambda co, nrm: lerp((0.42, 0.28, 0.08), (0.98, 0.80, 0.34), clamp01(0.4 + 0.6 * nrm.z))
    p.tube([(h - d * 0.14, 0.03, d), (h + d * 0.10, 0.03, d), (h + d * 0.10, 0.038, d), (h + d * 0.34, 0.04, d), (h + d * 0.34, 0.048, d), (h + d * 0.50, 0.052, d)], brass, sides=10, smooth=False)
    tag(p, st, 'hand_r')


def gear_ladle(p, arms, legs, hp, sp):
    st = mark(p)
    h = held(arms, -1)
    iron = soft(IRON_LIGHT, 0.5)
    pipe(p, [h + Vector((0, 0.08, 0.10)), h + Vector((0, -0.10, -0.10)), h + Vector((0, -0.30, -0.26))], 0.014, iron, sides=5, up=Vector((1, 0, 0)))
    p.blob(h + Vector((0, -0.35, -0.30)), (0.075, 0.075, 0.05), iron, 1, 0.0, 2, smooth=True)
    tag(p, st, 'hand_r')
    st = mark(p)
    bd = sp.get('bd', 0.17)
    p.box((0.16, -bd - 0.07, 0.86), (0.02, 0.012, 0.30), lambda co, nrm: lerp((0.36, 0.38, 0.44), (0.92, 0.94, 0.97), clamp01(nrm.z + 0.5)))    # cleaver in the belt
    p.box((0.16, -bd - 0.07, 1.04), (0.03, 0.03, 0.11), soft(LEATHER_D, 0.6), bevel=0.008)
    tag(p, st, 'pelvis')


def gear_greatblade(p, arms, legs, hp, sp):
    st = mark(p)
    m = Matrix.Translation((0.20, sp.get('cd', 0.165) + 0.09, 0.95)) @ Matrix.Rotation(0.45, 4, 'Y')
    blade(p, m, 0.95)
    tag(p, st, 'spine_02')
    st = mark(p)
    for side in (-1, 1):                                            # iron wrist bands
        sh, elb, wr = arms[side]
        d = (wr - elb).normalized()
        p.tube([(wr - d * 0.10, sp.get('fr', 0.082) + 0.012, d), (wr - d * 0.02, sp.get('fr', 0.082) + 0.01, d)], soft(IRON_LIGHT, 0.5), sides=10, smooth=False, cap=False)
        tag(p, st, 'lowerarm' + sfx(side))
        st = mark(p)


RED, NAVY, MOSS, SAND = (0.60, 0.11, 0.10), (0.10, 0.17, 0.36), (0.20, 0.34, 0.20), (0.80, 0.70, 0.52)
PLUM, TEALC = (0.36, 0.14, 0.30), (0.12, 0.38, 0.40)
figure("SM_BW_Pirate_Captain", dict(sw=0.29, cw=0.26, cd=0.18, bw=0.22, bd=0.19, ar=0.085, fr=0.09, shirt=BONE, trousers=(0.20, 0.18, 0.20), hair=(0.16, 0.10, 0.07), jaw=1.2,
                                    beard='full', hat='tricorn', feather=(0.86, 0.20, 0.16), coat=dict(col=NAVY, bottom=0.56, epaulettes=True), sash=RED, bandolier=LEATHER, extra=gear_cutlass))
figure("SM_BW_Pirate_Deckhand", dict(sw=0.25, cw=0.22, cd=0.15, bw=0.17, bd=0.14, ar=0.074, fr=0.082, shirt=BONE, shirt_stripes=(0.14, 0.30, 0.42), bare_arms=True,
                                     trousers=(0.42, 0.32, 0.22), barefoot=True, skin=(0.62, 0.42, 0.30), hair=(0.08, 0.06, 0.05), beard='stubble', hat='bandana', hat_col=RED, sash=(0.86, 0.66, 0.24),
                                     earring=(1, -1)))
figure("SM_BW_Pirate_OldSalt", dict(sw=0.25, cw=0.23, cd=0.18, bw=0.24, bd=0.22, stoop=0.10, shirt=(0.70, 0.66, 0.56), trousers=(0.30, 0.24, 0.18), hair=(0.82, 0.80, 0.76), hair_style='tuft',
                                    beard='long', nose=1.6, patch=1, peg=-1, hook=1, hat='cap', hat_col=(0.24, 0.20, 0.30), coat=dict(col=(0.38, 0.26, 0.18), bottom=0.80, trim=LEATHER_D)))
figure("SM_BW_Pirate_Brute", dict(sw=0.34, cw=0.31, cd=0.21, bw=0.25, bd=0.21, hw=0.16, ar=0.11, fr=0.115, lr=0.12, kr=0.09, hs=1.08, hand=2.0, neck=1.7, jaw=1.4, nose=1.3, brow=1.8,
                                  shirt=(0.30, 0.20, 0.16), bare_arms=True, trousers=(0.22, 0.20, 0.18), skin=(0.74, 0.50, 0.38), hair=(0.10, 0.08, 0.07), hair_style='mohawk', beard='chops',
                                  bandolier=LEATHER_D, sash=(0.24, 0.26, 0.30), extra=gear_greatblade, earring=(1, -1)))
figure("SM_BW_Pirate_Gunner", dict(sw=0.23, cw=0.20, cd=0.15, bw=0.165, bd=0.15, hw=0.15, hip=0.035, ar=0.066, fr=0.072, lr=0.105, hand=1.5, neck=1.0, jaw=0.95, nose=1.0, brow=0.9, bust=0.07,
                                   shirt=(0.90, 0.86, 0.76), rolled=True, trousers=(0.36, 0.16, 0.14), skin=(0.56, 0.38, 0.28), hair=(0.07, 0.05, 0.05), hair_style='braid', hat='bandana',
                                   hat_col=TEALC, coat=dict(col=(0.30, 0.20, 0.14), bottom=1.0, trim=GOLD_HI), sash=TEALC, extra=gear_pistols, lips=(0.56, 0.16, 0.18), earring=(1, -1)))
figure("SM_BW_Pirate_Lookout", dict(sw=0.23, cw=0.19, cd=0.135, bw=0.15, bd=0.13, hw=0.125, ar=0.062, fr=0.068, lr=0.088, kr=0.072, hs=1.16, hand=1.6, neck=1.0, jaw=0.95, nose=1.5,
                                    shirt=(0.88, 0.84, 0.74), shirt_stripes=(0.62, 0.14, 0.12), trousers=(0.20, 0.24, 0.32), skin=(0.90, 0.70, 0.56), hair=(0.62, 0.30, 0.10), hair_style='long',
                                    beard='moustache', hat='cap', hat_col=(0.16, 0.20, 0.30), bandolier=LEATHER, extra=gear_spyglass))
figure("SM_BW_Pirate_Cook", dict(sw=0.27, cw=0.27, cd=0.22, bw=0.34, bd=0.32, hw=0.16, ar=0.092, fr=0.09, lr=0.125, kr=0.09, jaw=1.3, neck=1.5, shirt=(0.86, 0.82, 0.72), rolled=True,
                                 trousers=(0.24, 0.22, 0.26), trouser_stripes=(0.32, 0.30, 0.34), skin=(0.88, 0.64, 0.52), hair=(0.14, 0.10, 0.08), hair_style='tuft', beard='moustache',
                                 hat='chef', hat_col=(0.94, 0.92, 0.86), apron=(0.84, 0.80, 0.72), extra=gear_ladle))
figure("SM_BW_Pirate_Quartermaster", dict(sw=0.24, cw=0.21, cd=0.16, bw=0.18, bd=0.16, hw=0.15, hip=0.03, ar=0.07, fr=0.075, hand=1.5, neck=1.05, jaw=1.0, nose=1.05, brow=1.0, bust=0.075,
                                          shirt=(0.92, 0.88, 0.80), trousers=(0.18, 0.16, 0.18), skin=(0.92, 0.72, 0.60), hair=(0.70, 0.18, 0.10), hair_style='long', hat='tricorn',
                                          hat_col=(0.30, 0.10, 0.12), feather=(0.94, 0.90, 0.80), coat=dict(col=PLUM, bottom=0.62, trim=GOLD_HI), sash=(0.86, 0.66, 0.24), extra=gear_cutlass,
                                          lips=(0.62, 0.14, 0.16), patch=-1))
figure("SM_BW_NPC_Deepfinder", dict(sw=0.24, cw=0.20, cd=0.14, bw=0.16, bd=0.13, ar=0.066, fr=0.074, lr=0.095, kr=0.074, shirt=(0.16, 0.36, 0.50), bare_arms=True, trousers=(0.22, 0.26, 0.30),
                                    skin=(0.74, 0.52, 0.38), hair=(0.10, 0.08, 0.07), hair_style='long', beard='none', jaw=1.0, hat='none', sash=(0.84, 0.48, 0.24), extra=gear_diver))
figure("SM_BW_NPC_Saltmarket", dict(sw=0.27, cw=0.26, cd=0.21, bw=0.34, bd=0.32, hw=0.16, ar=0.088, fr=0.085, lr=0.125, kr=0.09, jaw=1.3, neck=1.5, shirt=(0.88, 0.84, 0.74),
                                    trousers=(0.34, 0.26, 0.38), trouser_stripes=(0.44, 0.36, 0.48), hair=(0.30, 0.18, 0.10), beard='moustache', hat='widebrim', hat_col=(0.36, 0.24, 0.14),
                                    coat=dict(col=(0.16, 0.44, 0.44), bottom=1.0, trim=GOLD_HI), extra=gear_ledger))
figure("SM_BW_NPC_Warden", dict(sw=0.24, cw=0.20, cd=0.14, bw=0.17, bd=0.14, ar=0.066, fr=0.07, lr=0.092, kr=0.072, hs=1.14, jaw=1.0, nose=1.5, shirt=(0.30, 0.30, 0.34), trousers=(0.16, 0.16, 0.20),
                                skin=(0.90, 0.74, 0.62), hair=(0.70, 0.70, 0.72), hair_style='long', beard='long', hat='hood', hat_col=(0.48, 0.12, 0.12),
                                coat=dict(col=(0.50, 0.13, 0.13), bottom=0.34, trim=(0.86, 0.80, 0.62)), extra=gear_lantern_staff))
figure("SM_BW_NPC_Keelwright", dict(sw=0.32, cw=0.29, cd=0.21, bw=0.25, bd=0.21, hw=0.155, ar=0.11, fr=0.115, lr=0.125, kr=0.092, neck=1.7, jaw=1.35, hand=2.0, shirt=(0.78, 0.72, 0.60), rolled=True,
                                    trousers=(0.30, 0.26, 0.22), skin=(0.80, 0.56, 0.42), hair=(0.55, 0.26, 0.10), beard='full', hat='cap', hat_col=(0.30, 0.22, 0.14), apron=LEATHER,
                                    extra=gear_mallet))
figure("SM_BW_NPC_Alekeeper", dict(sw=0.29, cw=0.27, cd=0.21, bw=0.30, bd=0.28, hw=0.155, ar=0.095, fr=0.095, lr=0.12, kr=0.088, jaw=1.3, neck=1.5, shirt=(0.86, 0.80, 0.66), rolled=True,
                                   trousers=(0.26, 0.20, 0.16), hair=(0.18, 0.12, 0.08), hair_style='tuft', beard='moustache', hat='none', apron=(0.82, 0.78, 0.70), extra=gear_mug))
