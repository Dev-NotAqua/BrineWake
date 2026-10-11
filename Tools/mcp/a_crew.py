# Brinewake crew and outpost folk, sculpted in the open Blender (run through bl_run.py).
# Bodies are metaball sculpts (one family per layer: skin, trousers, boots, shirt, sleeves, hair) so forms blend like clay;
# coats, hats, belts and gear are modelled on top. Figures face -y, stand on z = 0, metres. Their right hand is at -x.
from mathutils import Quaternion

MB_K = 0.57                       # a metaball of radius 1 polygonises at 0.57
_mb = [0]
GOLD_LO, GOLD_HI, OCHRE, BONE = (0.55, 0.36, 0.10), (1.0, 0.82, 0.36), (0.90, 0.64, 0.20), (0.90, 0.82, 0.62)
LEATHER, LEATHER_D = (0.42, 0.25, 0.13), (0.22, 0.13, 0.08)
ROPE_C = (0.70, 0.57, 0.36)


def lin(c):
    return (clamp01(c[0]), clamp01(c[1]), clamp01(c[2]), 1.0)


def soft(base, lo=0.62, warm=0.0):
    """Clay-like paint: lit from above, earthier than the raw swatch, blotchy wear, grime toward the ground."""
    base = lerp(base, (0.42, 0.35, 0.29), 0.16)
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
            faces.append(p.bm.faces.new((A[k], A[(k + 1) % sides], B[(k + 1) % sides], B[k])))
    if not closed:
        faces.append(p.bm.faces.new(loops[-1]))
        faces.append(p.bm.faces.new(list(reversed(loops[0]))))
    for f in faces:
        f.smooth = True
        f.normal_update()
        for loop in f.loops:
            loop[p.col] = lin(colour(loop.vert.co, f.normal) if callable(colour) else colour)


def sculpt(p, elements, colour, res=0.03):
    """Polygonise a family of metaball elements and add the skin to the prop, painted per vertex.
    ('E', centre, semi-axes[, quaternion]) is an ellipsoid, ('C', a, b, radius) a capsule."""
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
    made = [p.bm.verts.new(v.co) for v in me.vertices]
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
    p = Prop(name)
    g = sp.get
    sw, cw, cd = g('sw', 0.23), g('cw', 0.20), g('cd', 0.14)
    bw, bd, hw = g('bw', 0.17), g('bd', 0.14), g('hw', 0.12)
    ar, fr, lr, kr = g('ar', 0.068), g('fr', 0.060), g('lr', 0.095), g('kr', 0.072)
    hs, hand = g('hs', 1.0), g('hand', 1.25)
    skin, shirt, trousers, boots, hair = g('skin', (0.86, 0.62, 0.47)), g('shirt', BONE), g('trousers', (0.25, 0.22, 0.20)), g('boots', LEATHER_D), g('hair', (0.20, 0.13, 0.08))
    stoop = g('stoop', 0.0)
    head_c = Vector((0, -stoop * 0.5, 1.75 - stoop * 0.3))

    def hp(dx, dy, dz):
        return head_c + Vector((dx, dy, dz)) * hs

    arms = {}
    for side in (-1, 1):
        sh = Vector((side * sw, -stoop * 0.3, 1.49 - stoop * 0.2))
        el, wr = Vector((side * (sw + 0.13), 0.02, 1.21)), Vector((side * (sw + 0.19), -0.07, 0.97))
        if g('arm%d' % side):
            el, wr = (Vector(v) for v in g('arm%d' % side))
        arms[side] = (sh, el, wr)
    legs = {side: (Vector((side * hw, 0, 0.95)), Vector((side * (hw + 0.012), -0.025, 0.52)), Vector((side * (hw + 0.018), 0.02, 0.10))) for side in (-1, 1)}
    peg, hook, bare_arms, barefoot = g('peg', 0), g('hook', 0), g('bare_arms', False), g('barefoot', False)
    # --- trousers
    el = [('E', (0, 0.005, 0.97), (hw + 0.09, max(bd * 0.9, 0.12), 0.14))]
    for side in (-1, 1):
        hip, knee, ankle = legs[side]
        el.append(('C', hip, knee, lr))
        if side != peg:
            el.append(('C', knee, ankle.lerp(knee, 0.25), kr))
    stripes_t = g('trouser_stripes')
    sculpt(p, el, (lambda co, nrm: soft(trousers if int(co.x * 26 + 100) % 2 else stripes_t)(co, nrm)) if stripes_t else soft(trousers))
    # --- boots, bare feet or a peg
    for side in (-1, 1):
        hip, knee, ankle = legs[side]
        if side == peg:
            p.tube([(knee + Vector((0, 0, -0.04)), 0.075, Vector((0, 0, 1))), (knee + Vector((0, 0, 0.05)), 0.09, Vector((0, 0, 1)))], soft(LEATHER), sides=10, smooth=False)
            pipe(p, [knee + Vector((0, 0, -0.03)), Vector((knee.x, knee.y + 0.01, 0.25)), Vector((knee.x, knee.y + 0.02, 0.0))], [0.055, 0.042, 0.032], soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.5)), sides=8,
                 up=Vector((0, 1, 0)))
            p.tube([(Vector((knee.x, knee.y + 0.02, 0.0)), 0.04, Vector((0, 0, 1))), (Vector((knee.x, knee.y + 0.02, 0.04)), 0.04, Vector((0, 0, 1)))], soft(IRON_LIGHT), sides=8, smooth=False)
            continue
        if barefoot:
            sculpt(p, [('C', ankle + Vector((0, 0, 0.06)), ankle + Vector((0, 0, -0.03)), kr * 0.8), ('E', (ankle.x, -0.07, 0.045), (0.05, 0.12, 0.04)),
                       ('E', (ankle.x, -0.17, 0.035), (0.055, 0.035, 0.03))], soft(skin, 0.7, 0.05), res=0.022)
            continue
        top = ankle.lerp(knee, g('boot_h', 0.62))
        sculpt(p, [('C', ankle + Vector((0, 0, -0.03)), top, kr + 0.02), ('E', (ankle.x, -0.075, 0.055), (0.068, 0.145, 0.055)), ('E', (ankle.x, 0.03, 0.05), (0.06, 0.06, 0.05))],
               soft(boots, 0.55), res=0.025)
        p.tube([(top + Vector((0, 0, -0.02)), kr + 0.035, Vector((0, 0, 1))), (top + Vector((0, 0, 0.06)), kr + 0.065, Vector((0, 0, 1)))], soft(lerp(boots, LEATHER, 0.5)), sides=12, smooth=False, cap=False)
        p.box((ankle.x, -0.105, 0.105), (0.07, 0.03, 0.05), soft(GOLD_HI, 0.5), bevel=0.01)
    # --- torso (shirt) with shoulders; sleeves or bare arms
    torso = [('E', (0, -stoop * 0.25, 1.34 - stoop * 0.15), (cw, cd, 0.19)), ('E', (0, -0.02 - bd * 0.12, 1.10), (bw, bd, 0.18)), ('E', (0, 0.01 - stoop * 0.3, 1.50 - stoop * 0.2), (0.11, 0.09, 0.07))]
    for side in (-1, 1):
        sh, elb, wr = arms[side]
        torso.append(('E', sh, (ar + 0.025, ar + 0.02, ar + 0.02)))
        torso.append(('C', sh, elb if not bare_arms else sh.lerp(elb, 0.45), ar))
        if not bare_arms and not g('rolled', False):
            torso.append(('C', elb, wr.lerp(elb, 0.12), fr))
    stripes = g('shirt_stripes')
    sculpt(p, torso, (lambda co, nrm: soft(shirt if int(co.z * 22) % 2 else stripes)(co, nrm)) if stripes else soft(shirt, 0.66))
    # --- skin: head, neck, hands, bare forearms
    jw, ns = g('jaw', 1.0), g('nose', 1.0)
    face = [('C', (0, 0.01 - stoop * 0.3, 1.50 - stoop * 0.2), hp(0, 0.01, -0.12), 0.055 * g('neck', 1.0)),
            ('E', hp(0, 0.012, 0.012), (0.108 * hs, 0.125 * hs, 0.125 * hs)), ('E', hp(0, -0.035, -0.06), (0.090 * hs * jw, 0.095 * hs, 0.078 * hs * jw)),
            ('E', hp(0, -0.098, -0.105 * jw), (0.046 * jw * hs, 0.04 * hs, 0.036 * hs)), ('E', hp(0, -0.138, -0.012), (0.030 * ns * hs, 0.046 * ns * hs, 0.036 * ns * hs)),
            ('E', hp(0, -0.108, 0.036), (0.086 * hs, 0.03 * hs, 0.022 * hs))]
    for side in (-1, 1):
        face.append(('E', hp(side * 0.062, -0.088, -0.035), (0.04 * hs, 0.04 * hs, 0.04 * hs)))
        face.append(('E', hp(side * 0.112, 0.015, -0.005), (0.018 * hs, 0.03 * hs, 0.042 * hs)))
    nose_tip = hp(0, -0.17, -0.012)

    def skin_paint(co, nrm):
        c = soft(skin, 0.70, 0.06)(co, nrm)
        blush = clamp01(1.0 - (co - nose_tip).length / (0.075 * hs))
        cheek = max(clamp01(1.0 - (co - hp(0.065, -0.11, -0.04)).length / (0.05 * hs)), clamp01(1.0 - (co - hp(-0.065, -0.11, -0.04)).length / (0.05 * hs)))
        return lerp(c, (0.86, 0.44, 0.36), 0.40 * blush + 0.28 * cheek)

    sculpt(p, face, skin_paint, res=0.016)
    for side in (-1, 1):
        sh, elb, wr = arms[side]
        d = (wr - elb).normalized()
        parts = []
        if bare_arms or g('rolled', False):
            parts += [('C', sh.lerp(elb, 0.4) if bare_arms else elb, elb, ar * 0.95), ('C', elb, wr, fr)] if bare_arms else [('C', elb, wr, fr)]
        if side == hook:
            if parts:
                sculpt(p, parts, soft(skin, 0.70, 0.06), res=0.02)
            p.tube([(wr + d * -0.03, fr + 0.02, d), (wr + d * 0.07, fr + 0.005, d)], soft(IRON_LIGHT, 0.5), sides=10, smooth=False)
            c0 = wr + d * 0.16
            pipe(p, [wr + d * 0.07, wr + d * 0.14] + [c0 + (d * math.cos(a) + Vector((0, -1, 0)) * math.sin(a)) * 0.055 for a in (math.radians(q) for q in (150, 90, 30, -30, -80))],
                 [0.022, 0.02, 0.019, 0.018, 0.016, 0.013, 0.008], soft(IRON_LIGHT, 0.5), sides=6, up=Vector((1, 0, 0)))
            continue
        q = Vector((0, 0, 1)).rotation_difference(d)
        hc = wr + d * 0.075 * hand
        parts += [('C', wr.lerp(elb, 0.08), wr + d * 0.02, fr * 0.85), ('E', hc, (0.046 * hand, 0.03 * hand, 0.062 * hand), q),
                  ('E', hc + d * 0.062 * hand, (0.04 * hand, 0.026 * hand, 0.045 * hand), q),
                  ('C', hc + Vector((0, -0.02, 0)), hc + Vector((0, -0.055 * hand, 0)) + d * 0.045 * hand, 0.016 * hand)]
        sculpt(p, parts, soft(skin, 0.70, 0.06), res=0.018)
    # --- eyes, brows, mouth
    for side in (-1, 1):
        if side == g('patch', 0):
            p.blob(hp(side * 0.047, -0.118, 0.008), (0.032 * hs, 0.014 * hs, 0.03 * hs), soft((0.07, 0.06, 0.06)), 1, 0.0, 2, smooth=True)
            continue
        p.blob(hp(side * 0.046, -0.112, 0.006), (0.021 * hs, 0.016 * hs, 0.021 * hs), lambda co, nrm: (0.96, 0.95, 0.90), 1, 0.0, 2, smooth=True)
        p.blob(hp(side * 0.046, -0.127, 0.004), (0.011 * hs, 0.006 * hs, 0.012 * hs), lambda co, nrm: g('eye', (0.16, 0.10, 0.06)), 1, 0.0, 2, smooth=True)
    if g('patch', 0):
        s = g('patch')
        pipe(p, [hp(s * 0.047, -0.125, 0.03), hp(s * 0.10, -0.06, 0.07), hp(s * 0.06, 0.12, 0.09), hp(-s * 0.08, 0.10, 0.06), hp(-s * 0.105, -0.03, 0.01), hp(-s * 0.02, -0.13, 0.015)],
             0.007, (0.07, 0.06, 0.06), sides=4, up=Vector((0, 0, 1)), closed=True)
    hairs = []
    for side in (-1, 1):
        hairs.append(('E', hp(side * 0.05, -0.122, 0.04 + 0.006 * g('brow', 1.0)), (0.03 * hs, 0.012 * hs, 0.011 * hs * g('brow', 1.0)), Quaternion((0, 1, 0), side * -0.25)))
    style = g('hair_style', 'short')
    if style == 'short':
        hairs += [('E', hp(0, 0.03, 0.05), (0.112 * hs, 0.125 * hs, 0.105 * hs))]
    elif style == 'long':
        hairs += [('E', hp(0, 0.04, 0.045), (0.115 * hs, 0.125 * hs, 0.11 * hs)), ('E', hp(0, 0.10, -0.10), (0.10 * hs, 0.06 * hs, 0.14 * hs)), ('E', hp(0, 0.11, -0.22), (0.07, 0.045, 0.09))]
    elif style == 'tuft':
        hairs += [('E', hp(side * 0.10, 0.03, -0.01), (0.03, 0.07, 0.05)) for side in (-1, 1)] + [('E', hp(0, 0.10, -0.02), (0.09, 0.04, 0.06))]
    beard = g('beard', 'none')
    if beard in ('full', 'long'):
        hairs += [('E', hp(0, -0.075, -0.115), (0.085 * jw, 0.06, 0.07)), ('E', hp(0, -0.07, -0.17 if beard == 'full' else -0.24), (0.06 * jw, 0.045, 0.06 if beard == 'full' else 0.12))]
        hairs += [('E', hp(side * 0.085, -0.03, -0.075), (0.03, 0.06, 0.07)) for side in (-1, 1)]
    if beard in ('full', 'long', 'moustache'):
        hairs += [('E', hp(side * 0.035, -0.132, -0.052), (0.04, 0.02, 0.018), Quaternion((0, 1, 0), side * 0.35)) for side in (-1, 1)]
        if beard == 'moustache':
            hairs += [('E', hp(side * 0.075, -0.115, -0.075), (0.022, 0.016, 0.03)) for side in (-1, 1)]
    if beard == 'stubble':
        p.box(tuple(hp(0, -0.128, -0.06)), (0.05 * hs, 0.012, 0.01), lambda co, nrm: (0.35, 0.16, 0.14))
    elif beard == 'none':
        p.box(tuple(hp(0, -0.127, -0.062)), (0.055 * hs, 0.012, 0.012), lambda co, nrm: (0.40, 0.17, 0.15))
    sculpt(p, hairs, soft(hair, 0.55), res=0.014)
    # --- belt, buckle, sash
    wr_x, wr_y = max(bw, cw * 0.82) + 0.012, bd + 0.02
    belt = [v for v in ring(wr_x, wr_y, 1.02, 0, 2 * math.pi, 20, yoff=-0.02 - bd * 0.12)][:-1]
    pipe(p, belt, 0.032, soft(g('belt', LEATHER), 0.55), sides=6, closed=True)
    p.box((0, -wr_y - 0.045 - bd * 0.12, 1.02), (0.085, 0.03, 0.085), soft(GOLD_HI, 0.5), bevel=0.012)
    if g('sash'):
        sc = g('sash')
        sash = ring(wr_x + 0.012, wr_y + 0.012, 1.09, 0, 2 * math.pi, 20, yoff=-0.02 - bd * 0.12)
        low = [v + Vector((0, 0, -0.10)) for v in sash]
        for k in range(20):
            fquad(p, [low[k], low[k + 1], sash[k + 1], sash[k]], soft(sc), smooth=True)
        x0 = wr_x * 0.8
        fquad(p, [Vector((x0, -wr_y * 0.6, 1.0)), Vector((x0 + 0.07, -wr_y * 0.5, 1.0)), Vector((x0 + 0.10, -wr_y * 0.45, 0.66)), Vector((x0 + 0.02, -wr_y * 0.62, 0.70))], soft(sc, 0.5))
    # --- coat or vest: an open-fronted shell with collar, lapels, trim and cuffs
    coat = g('coat')
    if coat:
        cc, ctrim, bottom = coat['col'], coat.get('trim', OCHRE), coat.get('bottom', 0.60)
        levels = [(1.555, 0.125, 0.105, 0.30), (1.50, sw + 0.01, cd * 0.85, 0.34), (1.36, cw + 0.035, cd + 0.035, 0.42), (1.18, max(bw, cw * 0.86) + 0.035, bd + 0.04, 0.50),
                  (1.02, max(bw, cw * 0.84) + 0.04, bd + 0.045, 0.55)]
        if bottom < 1.0:
            for k in range(1, 5):
                z = 1.02 - (1.02 - bottom) * k / 4
                fl = 0.035 * k
                levels.append((z, max(bw, cw * 0.84) + 0.04 + fl, bd + 0.045 + fl * 1.3, 0.55 + 0.07 * k))
        rings_ = [ring(rx, ry, z - stoop * 0.15 * max(0.0, z - 1.1), a0, 2 * math.pi - a0, 22, yoff=-0.02 - (bd * 0.12 if z < 1.25 else stoop * 0.25)) for z, rx, ry, a0 in levels]
        for a, b in zip(rings_, rings_[1:]):
            for k in range(22):
                fquad(p, [a[k], b[k], b[k + 1], a[k + 1]], soft(cc, 0.6), smooth=True)
        for edge in (0, -1):                                        # trim down both front edges, buttons on one
            pipe(p, [r[edge] for r in rings_], 0.012, soft(ctrim, 0.55), sides=4, up=Vector((1, 0, 0)))
        for k in range(1, 4):
            q = rings_[1][0].lerp(rings_[4][0], k / 4)
            p.blob((q.x + 0.03, q.y - 0.012, q.z), (0.014, 0.008, 0.014), soft(GOLD_HI, 0.5), k, 0.0, 1, smooth=True)
        for side, edge in ((1, 0), (-1, -1)):                       # lapels
            a, b = rings_[1][edge], rings_[3][edge]
            fquad(p, [a, a + Vector((side * 0.085, -0.03, -0.06)), b], soft(lerp(cc, ctrim, 0.25), 0.6))
        pipe(p, ring(0.105, 0.09, 1.575 - stoop * 0.2, 0.5, 2 * math.pi - 0.5, 12, yoff=0.01 - stoop * 0.3), 0.028, soft(lerp(cc, (0, 0, 0), 0.15), 0.6), sides=5)
        sleeves = []
        for side in (-1, 1):
            sh, elb, wr = arms[side]
            sleeves += [('E', sh, (ar + 0.04, ar + 0.035, ar + 0.035)), ('C', sh, elb, ar + 0.018), ('C', elb, wr.lerp(elb, 0.18), fr + 0.018)]
        sculpt(p, sleeves, soft(cc, 0.6))
        for side in (-1, 1):
            sh, elb, wr = arms[side]
            d = (wr - elb).normalized()
            c = wr.lerp(elb, 0.2)
            p.tube([(c - d * 0.03, fr + 0.03, d), (c + d * 0.05, fr + 0.05, d)], soft(ctrim, 0.55), sides=10, smooth=False, cap=False)
    # --- apron
    if g('apron'):
        ac = g('apron')
        rows = [(1.36, cw * 0.62, cd + 0.03), (1.18, max(bw, cw * 0.8) * 0.8, bd + 0.045), (1.02, max(bw, cw * 0.8) * 0.9, bd + 0.05), (0.80, hw + 0.13, bd * 0.8 + 0.05), (0.56, hw + 0.15, 0.13)]
        grid = [[Vector((hwid * u, -ry * math.cos(u * 0.9) - 0.02 - (bd * 0.12 if z < 1.25 else 0.0), z)) for u in (-1, -0.5, 0, 0.5, 1)] for z, hwid, ry in rows]
        for a, b in zip(grid, grid[1:]):
            for k in range(4):
                fquad(p, [a[k], b[k], b[k + 1], a[k + 1]], soft(ac, 0.6), smooth=True)
        for side in (-1, 1):
            pipe(p, [grid[0][0 if side < 0 else 4], Vector((side * 0.09, -0.02, 1.53)), Vector((side * 0.05, 0.09, 1.55))], 0.012, soft(lerp(ac, LEATHER_D, 0.5)), sides=4, up=Vector((1, 0, 0)))
    # --- headwear
    hat = g('hat', 'none')
    hc = g('hat_col', (0.12, 0.10, 0.10))
    hz = hp(0, 0, 0.085).z
    if hat == 'tricorn':
        sculpt(p, [('E', hp(0, 0.015, 0.105), (0.118 * hs, 0.13 * hs, 0.075 * hs))], soft(hc, 0.6), res=0.018)
        n = 30
        inner = [Vector((head_c.x + 0.125 * hs * math.sin(a), head_c.y + 0.015 - 0.135 * hs * math.cos(a), hz)) for a in (2 * math.pi * k / n for k in range(n + 1))]
        outer = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            c3 = math.cos(3 * a)                                     # 1 at the three corners (one over the brow), -1 mid-side
            r = (0.275 + 0.085 * c3) * hs
            outer.append(Vector((head_c.x + r * math.sin(a), head_c.y + 0.015 - r * math.cos(a), hz + 0.02 + 0.115 * hs * (1 - c3) / 2)))
        for k in range(n):
            fquad(p, [inner[k], outer[k], outer[k + 1], inner[k + 1]], soft(hc, 0.55), smooth=True)
        pipe(p, outer[:-1], 0.012, soft(g('hat_trim', OCHRE), 0.55), sides=4, up=Vector((0, 0, 1)), closed=True)
    elif hat == 'bandana':
        sculpt(p, [('E', hp(0, 0.02, 0.06), (0.116 * hs, 0.132 * hs, 0.095 * hs)), ('E', hp(0.03, 0.14, 0.02), (0.035, 0.03, 0.03))], soft(hc, 0.6), res=0.016)
        for k in (0, 1):
            a = hp(0.03, 0.15, 0.01)
            fquad(p, [a, a + Vector((0.05 + 0.05 * k, 0.05, -0.16)), a + Vector((0.0 + 0.05 * k, 0.07, -0.20))], soft(hc, 0.5))
    elif hat == 'widebrim':
        sculpt(p, [('E', hp(0, 0.015, 0.13), (0.112 * hs, 0.125 * hs, 0.10 * hs))], soft(hc, 0.6), res=0.018)
        n = 28
        inner = [Vector((head_c.x + 0.12 * hs * math.sin(a), head_c.y + 0.015 - 0.13 * hs * math.cos(a), hz + 0.01)) for a in (2 * math.pi * k / n for k in range(n + 1))]
        outer = [Vector((head_c.x + 0.33 * hs * math.sin(a), head_c.y + 0.015 - 0.34 * hs * math.cos(a), hz - 0.02 + 0.035 * math.sin(a * 2 + 1.0) - 0.03 * math.cos(a)))
                 for a in (2 * math.pi * k / n for k in range(n + 1))]
        for k in range(n):
            fquad(p, [inner[k], outer[k], outer[k + 1], inner[k + 1]], soft(hc, 0.55), smooth=True)
        pipe(p, [v + Vector((0, 0, 0.012)) for v in inner[:-1]], 0.016, soft(g('hat_trim', OCHRE), 0.55), sides=4, closed=True)
    elif hat == 'cap':
        sculpt(p, [('E', hp(0, 0.02, 0.07), (0.117 * hs, 0.133 * hs, 0.09 * hs)), ('E', hp(0, -0.10, 0.045), (0.085, 0.07, 0.014))], soft(hc, 0.6), res=0.016)
    elif hat == 'hood':
        sculpt(p, [('E', hp(0, 0.035, 0.03), (0.135 * hs, 0.14 * hs, 0.15 * hs)), ('E', hp(0, 0.06, -0.12), (0.13, 0.10, 0.10)), ('E', hp(0, -0.03, 0.14), (0.10, 0.11, 0.05))],
               soft(hc, 0.55), res=0.018)
    extra = g('extra')
    if extra:
        extra(p, arms, legs, hp, sp)
    for v in p.bm.verts:                                            # longer thighs: less doll, more swagger
        v.co.z += 0.07 * smooth_step(0.45, 0.95, v.co.z)
    if g('scale', 1.0) != 1.0:
        for v in p.bm.verts:
            v.co *= g('scale')
    p.export()


def held(arms, side):
    """Palm position of a hand, to put something in it."""
    sh, elb, wr = arms[side]
    return wr + (wr - elb).normalized() * 0.09


# ----- gear -----
def gear_mug(p, arms, legs, hp, sp):
    h = held(arms, -1) + Vector((0, -0.03, 0.03))
    p.tube([(h + Vector((0, 0, -0.07)), 0.055, Vector((0, 0, 1))), (h + Vector((0, 0, 0.09)), 0.062, Vector((0, 0, 1)))], soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.6)), sides=12, smooth=False)
    p.blob(h + Vector((0, 0, 0.10)), (0.058, 0.058, 0.03), lambda co, nrm: (0.97, 0.94, 0.86), 1, 0.25, 2, smooth=True)
    pipe(p, [h + Vector((0.055, 0, 0.06)), h + Vector((0.10, 0, 0.04)), h + Vector((0.10, 0, -0.02)), h + Vector((0.055, 0, -0.04))], 0.012, soft(IRON_LIGHT, 0.5), sides=5, up=Vector((0, 1, 0)))
    fquad(p, [Vector((0.02, -0.02, 1.02)), Vector((0.16, 0.0, 1.02)), Vector((0.20, 0.02, 0.72)), Vector((0.04, -0.03, 0.74))], soft((0.86, 0.84, 0.78), 0.6))   # bar towel


def gear_mallet(p, arms, legs, hp, sp):
    h = held(arms, -1)
    spar(p, h + Vector((0, 0.05, -0.28)), h + Vector((0, -0.12, 0.34)), 0.022, 0.02, 3, sides=6)
    m = Matrix.Translation(h + Vector((0, -0.13, 0.36))) @ Matrix.Rotation(0.35, 4, 'X')
    p.box((0, 0, 0), (0.24, 0.12, 0.12), soft(lerp(WOOD_DARK, WOOD_LIGHT, 0.55)), bevel=0.02, xform=m)
    for k in range(3):                                              # chisels in the apron pocket
        p.box((-0.07 + 0.05 * k, -sp.get('bd', 0.14) - 0.09, 1.0), (0.02, 0.015, 0.14), soft(IRON_LIGHT, 0.5))


def gear_lantern_staff(p, arms, legs, hp, sp):
    h = held(arms, -1)
    top = Vector((h.x - 0.02, h.y - 0.05, 2.45))
    spar(p, Vector((h.x + 0.01, h.y + 0.02, 0.0)), top, 0.024, 0.02, 5, sides=6)
    pipe(p, [top, top + Vector((0.0, -0.16, 0.10)), top + Vector((0.0, -0.26, 0.0))], 0.014, soft(IRON_LIGHT, 0.5), sides=5, up=Vector((1, 0, 0)))
    lantern(p, tuple(top + Vector((0.0, -0.26, -0.22))))
    for k in range(3):                                              # storm charms on the belt
        p.blob((0.12 + 0.045 * k, -sp.get('bd', 0.14) - 0.05, 0.93), (0.016, 0.016, 0.03), soft((0.75, 0.86, 0.90)), k, 0.0, 1, smooth=True)


def gear_ledger(p, arms, legs, hp, sp):
    h = held(arms, 1)
    m = Matrix.Translation(h + Vector((-0.06, -0.06, 0.04))) @ Matrix.Rotation(0.5, 4, 'X') @ Matrix.Rotation(0.2, 4, 'Z')
    p.box((0, 0, 0), (0.24, 0.05, 0.30), soft((0.45, 0.14, 0.12), 0.6), bevel=0.01, xform=m)
    p.box((0, 0, 0), (0.22, 0.04, 0.28), lambda co, nrm: BONE, xform=m @ Matrix.Translation((0, 0.012, 0)))
    for side in (-1, 1):                                            # spectacles
        pipe(p, [hp(side * 0.046, -0.135, 0.006) + Vector((math.cos(a) * 0.026, 0, math.sin(a) * 0.024)) for a in (2 * math.pi * k / 10 for k in range(10))], 0.004,
             soft(GOLD_HI, 0.5), sides=4, up=Vector((0, 1, 0)), closed=True)
    hx = held(arms, -1)
    pipe(p, [hx + Vector((0, 0, 0.12)), hx + Vector((0, 0, -0.02))], 0.006, soft(IRON_LIGHT, 0.5), sides=4)                 # scales
    pipe(p, [hx + Vector((-0.12, 0, 0.11)), hx + Vector((0.12, 0, 0.11))], 0.006, soft(GOLD_HI, 0.5), sides=4, up=Vector((0, 1, 0)))
    for s in (-1, 1):
        p.tube([(hx + Vector((s * 0.12, 0, -0.02)), 0.05, Vector((0, 0, 1))), (hx + Vector((s * 0.12, 0, 0.0)), 0.055, Vector((0, 0, 1)))], soft(GOLD_HI, 0.5), sides=10, smooth=False)
        pipe(p, [hx + Vector((s * 0.12, 0, 0.11)), hx + Vector((s * 0.12, 0, 0.0))], 0.003, soft(ROPE_C), sides=3)


def gear_diver(p, arms, legs, hp, sp):
    for side in (-1, 1):                                            # goggles pushed up on the brow
        pipe(p, [hp(side * 0.048, -0.118, 0.075) + Vector((math.cos(a) * 0.03, 0, math.sin(a) * 0.026)) for a in (2 * math.pi * k / 10 for k in range(10))], 0.008,
             soft(GOLD_HI, 0.5), sides=5, up=Vector((0, 1, 0)), closed=True)
        p.blob(hp(side * 0.048, -0.116, 0.075), (0.024, 0.006, 0.02), lambda co, nrm: (0.55, 0.80, 0.85), 1, 0.0, 1, smooth=True)
    sh = arms[1][0]
    for k in range(4):                                              # rope coil over the shoulder
        c = sh + Vector((-0.10, 0.0, -0.22))
        pipe(p, [c + Vector((math.sin(a) * 0.05 + 0.012 * k, math.cos(a) * 0.20, math.sin(a + 0.4) * 0.30)) for a in (2 * math.pi * q / 14 for q in range(14))], 0.016, soft(ROPE_C), sides=5,
             up=Vector((1, 0, 0)), closed=True)
    p.box((-0.20, -0.02, 0.86), (0.035, 0.05, 0.26), soft(LEATHER, 0.55), bevel=0.01)       # sheathed knife
    p.box((-0.20, -0.02, 1.02), (0.03, 0.035, 0.09), soft(BONE))


def gear_cutlass(p, arms, legs, hp, sp):
    bd = sp.get('bd', 0.14)
    m = Matrix.Translation((0.24, 0.0, 0.78)) @ Matrix.Rotation(0.5, 4, 'X')
    p.box((0, 0, 0), (0.035, 0.07, 0.62), soft(LEATHER_D, 0.6), bevel=0.012, xform=m)
    p.box((0, 0, 0), (0.05, 0.13, 0.03), soft(GOLD_HI, 0.5), bevel=0.01, xform=m @ Matrix.Translation((0, 0, 0.33)))
    p.box((0, 0, 0), (0.03, 0.035, 0.13), soft(LEATHER, 0.6), bevel=0.01, xform=m @ Matrix.Translation((0, 0, 0.41)))
    pipe(p, ring(max(sp.get('bw', 0.17), sp.get('cw', 0.2) * 0.84) + 0.06, bd + 0.07, 1.25, 0, 2 * math.pi, 16, yoff=-0.03)[:-1], 0.02, soft(LEATHER, 0.55), sides=5, closed=True) if False else None


RED, NAVY, MOSS, SAND = (0.60, 0.11, 0.10), (0.10, 0.17, 0.36), (0.20, 0.34, 0.20), (0.80, 0.70, 0.52)
figure("SM_BW_Pirate_Captain", dict(sw=0.26, cw=0.23, cd=0.16, bw=0.19, bd=0.16, ar=0.075, fr=0.066, shirt=BONE, trousers=(0.20, 0.18, 0.20), hair=(0.16, 0.10, 0.07),
                                    beard='full', hat='tricorn', coat=dict(col=NAVY, bottom=0.58), sash=RED, extra=gear_cutlass))
figure("SM_BW_Pirate_Deckhand", dict(sw=0.22, cw=0.19, cd=0.13, bw=0.15, bd=0.12, ar=0.066, fr=0.06, shirt=BONE, shirt_stripes=(0.14, 0.30, 0.42), bare_arms=True,
                                     trousers=(0.42, 0.32, 0.22), barefoot=True, skin=(0.62, 0.42, 0.30), hair=(0.08, 0.06, 0.05), beard='stubble', hat='bandana', hat_col=RED, sash=(0.86, 0.66, 0.24)))
figure("SM_BW_Pirate_OldSalt", dict(sw=0.23, cw=0.21, cd=0.16, bw=0.21, bd=0.19, stoop=0.10, shirt=(0.70, 0.66, 0.56), trousers=(0.30, 0.24, 0.18), hair=(0.82, 0.80, 0.76), hair_style='tuft',
                                    beard='long', nose=1.35, patch=1, peg=-1, hook=1, hat='cap', hat_col=(0.24, 0.20, 0.30), coat=dict(col=(0.38, 0.26, 0.18), bottom=0.80, trim=LEATHER_D)))
figure("SM_BW_NPC_Deepfinder", dict(sw=0.21, cw=0.17, cd=0.12, bw=0.14, bd=0.11, ar=0.058, fr=0.054, lr=0.085, kr=0.066, shirt=(0.16, 0.36, 0.50), bare_arms=True, trousers=(0.22, 0.26, 0.30),
                                    skin=(0.74, 0.52, 0.38), hair=(0.10, 0.08, 0.07), hair_style='long', beard='none', jaw=0.92, hat='none', sash=(0.84, 0.48, 0.24), extra=gear_diver, scale=1.03))
figure("SM_BW_NPC_Saltmarket", dict(sw=0.25, cw=0.24, cd=0.19, bw=0.31, bd=0.29, hw=0.15, ar=0.08, fr=0.068, lr=0.115, kr=0.082, jaw=1.2, neck=1.3, shirt=(0.88, 0.84, 0.74),
                                    trousers=(0.34, 0.26, 0.38), trouser_stripes=(0.44, 0.36, 0.48), hair=(0.30, 0.18, 0.10), beard='moustache', hat='widebrim', hat_col=(0.36, 0.24, 0.14),
                                    coat=dict(col=(0.16, 0.44, 0.44), bottom=1.0, trim=GOLD_HI), arm1=((0.40, -0.06, 1.22), (0.30, -0.26, 1.16)), arm_1=None,
                                    extra=gear_ledger, scale=0.96, **{'arm-1': ((-0.40, -0.04, 1.24), (-0.36, -0.24, 1.34))}))
figure("SM_BW_NPC_Warden", dict(sw=0.22, cw=0.18, cd=0.12, bw=0.15, bd=0.12, ar=0.06, fr=0.054, lr=0.085, kr=0.066, hs=0.96, jaw=0.9, nose=1.2, shirt=(0.30, 0.30, 0.34), trousers=(0.16, 0.16, 0.20),
                                skin=(0.90, 0.74, 0.62), hair=(0.70, 0.70, 0.72), hair_style='long', beard='long', hat='hood', hat_col=(0.48, 0.12, 0.12),
                                coat=dict(col=(0.50, 0.13, 0.13), bottom=0.34, trim=(0.86, 0.80, 0.62)), extra=gear_lantern_staff, scale=1.10,
                                **{'arm-1': ((-0.34, -0.10, 1.24), (-0.30, -0.30, 1.36))}))
figure("SM_BW_NPC_Keelwright", dict(sw=0.30, cw=0.27, cd=0.19, bw=0.23, bd=0.19, hw=0.14, ar=0.10, fr=0.092, lr=0.115, kr=0.085, neck=1.5, jaw=1.2, hand=1.5, shirt=(0.78, 0.72, 0.60), rolled=True,
                                    trousers=(0.30, 0.26, 0.22), skin=(0.80, 0.56, 0.42), hair=(0.55, 0.26, 0.10), beard='full', hat='cap', hat_col=(0.30, 0.22, 0.14), apron=LEATHER,
                                    extra=gear_mallet, scale=0.93, **{'arm-1': ((-0.46, -0.04, 1.26), (-0.40, -0.28, 1.34))}))
figure("SM_BW_NPC_Alekeeper", dict(sw=0.28, cw=0.25, cd=0.19, bw=0.27, bd=0.25, hw=0.14, ar=0.088, fr=0.075, lr=0.11, kr=0.08, jaw=1.15, neck=1.3, shirt=(0.86, 0.80, 0.66), rolled=True,
                                   trousers=(0.26, 0.20, 0.16), hair=(0.18, 0.12, 0.08), hair_style='tuft', beard='moustache', hat='none', apron=(0.82, 0.78, 0.70),
                                   extra=gear_mug, **{'arm-1': ((-0.42, -0.06, 1.24), (-0.34, -0.30, 1.30))}))
for old in ("SM_BW_Pirate_Red", "SM_BW_Pirate_Blue", "SM_BW_Pirate_Green"):
    ob = bpy.data.objects.get(old)
    if ob is not None:
        bpy.data.objects.remove(ob)
