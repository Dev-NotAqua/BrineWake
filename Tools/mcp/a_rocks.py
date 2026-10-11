# Brinewake rocks: angular chunks stacked in beds, clustered, arched and piled. Run after a_lib.py through bl_run.py.
# Palettes follow the sea zones: shore (Sunlit Shallows), verdant (Verdant Reach), ash (Ashen Narrows), ember (Ember Deeps), grey (open sea).
WANT = globals().get("BW_ONLY")


def want(name):
    return not WANT or any(k in name for k in WANT)


def beds(p, centre, half, seed, pal, layers=3, moss=0.0, sub=2, zr=None, shrink=0.12, drift=0.07, boxy=0.9, prof=None, core=0.84, core_taper=0.9, lean=0.0):
    """Layered, wave-cut stone: a solid core with flat angular beds wrapped round it, each a little off the one below."""
    rnd = random.Random(seed)
    cx, cy, cz = centre
    z0 = cz - half[2]
    H = 2.0 * half[2]
    zr = zr or (z0, cz + half[2])
    kc = prof(0.5) if prof else 1.0 - shrink * 0.5
    chunk(p, (cx + lean * H * 0.25, cy, cz), (half[0] * core * kc, half[1] * core * kc, half[2] * 1.02), seed + 999, pal, pts=22, boxy=0.9, bevel=0.10, sub=sub, zrange=zr, moss=moss,
          taper=core_taper, tilt=(0.0, -lean * 0.8))
    step = H / layers
    for i in range(layers):
        t = (i + 0.5) / layers
        k = prof(t) if prof else 1.0 - shrink * t
        ox, oy = rnd.uniform(-drift, drift) * half[0], rnd.uniform(-drift, drift) * half[1]
        chunk(p, (cx + ox + lean * H * t * t, cy + oy, z0 + step * (i + 0.5)), (half[0] * k * rnd.uniform(0.94, 1.08), half[1] * k * rnd.uniform(0.94, 1.08), step * rnd.uniform(0.66, 0.80)),
              seed + i * 11, pal, pts=22, boxy=boxy, bevel=0.16, sub=sub, turn=rnd.uniform(-0.25, 0.25), moss=moss if i == layers - 1 else moss * 0.35, zrange=zr,
              flat=0.06 if i == layers - 1 else 0.0, tilt=(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05)))


def rock(name, half, seed, pal='shore', moss=0.0, boxy=0.55, extra=2, flat=0.0, pts=13, sub=2):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    zr = (0.0, half[2] * 1.75)
    chunk(p, (0, 0, half[2] * 0.76), half, seed, pal, pts=pts, boxy=boxy, moss=moss, sub=sub, flat=flat, zrange=zr, turn=rnd.uniform(0, 3.0))
    for k in range(extra):
        a = rnd.uniform(0, 6.28)
        s = rnd.uniform(0.30, 0.52)
        hs = (half[0] * s, half[1] * s * rnd.uniform(0.8, 1.2), half[2] * s * rnd.uniform(0.7, 1.0))
        chunk(p, (math.cos(a) * half[0] * 0.88, math.sin(a) * half[1] * 0.88, hs[2] * 0.68), hs, seed + 17 + k * 5, pal, pts=11, boxy=boxy, moss=moss, sub=1, zrange=zr,
              turn=rnd.uniform(0, 3.0))
    p.export()


def slab(name, half, seed, pal='shore', moss=0.0):
    if not want(name):
        return
    p = Prop(name)
    layers = max(1, int(round(half[2] * 2 / 2.0)))
    beds(p, (0, 0, half[2] * 0.94), half, seed, pal, layers=max(2, layers + 1), moss=moss, sub=2 if layers < 3 else 1)
    p.export()


def pebbles(name, seed, radius, count, pal='shore', size=(0.07, 0.22)):
    if not want(name):
        return
    p = Prop(name)
    stones(p, (0, 0, 0), radius, count, seed, pal, size=size, ring=False)
    p.export()


def rock_pile(name, seed, pal='shore', moss=0.0):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    zr = (0.0, 2.4)
    for k in range(11):
        a = rnd.uniform(0, 6.28)
        d = 1.9 * math.sqrt(rnd.random()) if k > 2 else 0.5 * k
        s = rnd.uniform(0.45, 0.95) * (1.0 - 0.25 * d / 1.9)
        z = s * 0.5 + (0.9 if k < 2 else 0.0) * (1 - d / 1.9)
        chunk(p, (math.cos(a) * d, math.sin(a) * d, z), (s * rnd.uniform(0.9, 1.4), s, s * rnd.uniform(0.6, 0.9)), seed + k * 3, pal, pts=11, boxy=0.5, sub=1, moss=moss, zrange=zr,
              turn=rnd.uniform(0, 3), tilt=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))
    p.export()


def sea_stack(name, seed, radius, height, pal='shore', moss=0.5, layers=6):
    """Wave-cut stack: narrow waist near the water, heavy overhanging head, green cap."""
    if not want(name):
        return
    p = Prop(name)
    prof = lambda t: 0.78 - 0.30 * math.sin(math.pi * min(1.0, t * 2.2)) * (1.0 if t < 0.45 else 0.0) + (0.34 * smooth_step(0.35, 0.8, t)) - 0.20 * smooth_step(0.85, 1.0, t)
    beds(p, (0, 0, height / 2 - 0.4), (radius, radius * 0.86, height / 2), seed, pal, layers=layers, moss=moss, sub=2, drift=0.14, prof=prof)
    rnd = random.Random(seed)
    for k in range(4):
        a = rnd.uniform(0, 6.28)
        s = rnd.uniform(0.5, 1.1)
        chunk(p, (math.cos(a) * radius * 0.95, math.sin(a) * radius * 0.85, s * 0.3), (s * 1.3, s, s * 0.7), seed + 50 + k, pal, pts=11, sub=1, zrange=(-0.4, height), turn=rnd.uniform(0, 3))
    p.export()


def spire(name, seed, radius, height, pal='shore', moss=0.0, lean=0.12):
    if not want(name):
        return
    p = Prop(name)
    beds(p, (0, 0, height / 2 - 0.3), (radius, radius * 0.85, height / 2), seed, pal, layers=max(3, int(height / 2.2)), moss=moss, sub=1, drift=0.05,
         prof=lambda t: 1.0 - 0.80 * t ** 0.85, core=1.0, core_taper=0.30, lean=lean)
    rnd = random.Random(seed)
    for k in range(3):
        a = rnd.uniform(0, 6.28)
        s = rnd.uniform(0.4, 0.8) * radius * 0.5
        chunk(p, (math.cos(a) * radius, math.sin(a) * radius * 0.85, s * 0.3), (s * 1.3, s, s * 0.8), seed + 50 + k, pal, pts=12, sub=1, zrange=(-0.3, height), turn=rnd.uniform(0, 3))
    p.export()


def arch(name, seed, span, height, depth, pal='shore', moss=0.3, cave=False):
    """A natural arch you can walk or sail through: two piers and a bridge of wedged blocks."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    zr = (0.0, height + depth * 0.5)
    n = 11
    R = span / 2 + depth * 0.45
    arc = math.pi * (R + height) / 2 / (n - 1)
    for k in range(n):
        a = math.pi * k / (n - 1)
        t = math.sin(a)
        thick = depth * (0.72 - 0.20 * t)
        elev = math.atan2(math.cos(a) * height, max(t, 1e-3) * R)
        chunk(p, (-math.cos(a) * R, rnd.uniform(-0.08, 0.08) * depth, t * height), (arc * rnd.uniform(0.9, 1.1), depth * rnd.uniform(0.85, 1.05), thick * rnd.uniform(0.95, 1.2)),
              seed + k * 5, pal, pts=20, boxy=0.9, sub=2 if k % 2 == 0 else 1, zrange=zr, tilt=(rnd.uniform(-0.08, 0.08), -elev), moss=moss if t > 0.6 else 0.0, bevel=0.16)
    for sgn in (-1, 1):
        chunk(p, (sgn * R, 0, height * 0.12), (depth * 0.95, depth * 1.05, height * 0.42), seed + 60 + sgn, pal, pts=20, boxy=0.85, sub=2, zrange=zr, turn=rnd.uniform(-0.3, 0.3), taper=0.8)
        chunk(p, (sgn * (R + depth * 1.0), rnd.uniform(-0.3, 0.3) * depth, height * 0.10), (depth * 0.7, depth * 0.8, height * 0.22), seed + 70 + sgn, pal, pts=14, sub=1, zrange=zr,
              turn=rnd.uniform(0, 3))
    if cave:
        back = depth * 0.95
        faces = p.blob((0, back, height * 0.42), (span * 0.62, depth * 0.5, height * 0.62), const((0, 0, 0)), seed, rough=0.2, subdiv=3, smooth=True)
        p.paint(faces, lambda co, nrm: lerp((0.02, 0.02, 0.04), (0.10, 0.09, 0.12), clamp01(co.z / height)))
        for k in range(5):
            a = math.pi * (k + 0.5) / 5
            chunk(p, (-math.cos(a) * span * 0.72, back, math.sin(a) * height * 0.9 + 0.5), (depth * 0.75, depth * 0.7, height * 0.42), seed + 80 + k, pal, pts=13, sub=1, zrange=zr,
                  turn=rnd.uniform(0, 3), moss=moss)
    p.export()


def cliff(name, seed, width, depth, height, pal='shore', moss=0.4):
    """A wall section: columns of beds of uneven height with a walkable top and rubble at the foot. Faces -y."""
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    cols = max(2, int(round(width / 4.5)))
    zr = (0.0, height)
    for c in range(cols):
        x = -width / 2 + width * (c + 0.5) / cols
        h = height * rnd.uniform(0.72, 1.0)
        beds(p, (x + rnd.uniform(-0.4, 0.4), rnd.uniform(-0.12, 0.12) * depth, h / 2 - 0.3), (width / cols * 0.66, depth / 2, h / 2), seed + c * 31, pal, layers=max(2, int(round(h / 2.6))),
             moss=moss, sub=1, zr=zr, drift=0.12, shrink=0.10)
    for k in range(cols + 2):
        x = rnd.uniform(-0.5, 0.5) * width
        s = rnd.uniform(0.6, 1.3)
        chunk(p, (x, -depth / 2 - s * 0.5, s * 0.4), (s * 1.3, s, s * 0.8), seed + 200 + k, pal, pts=11, sub=1, zrange=zr, turn=rnd.uniform(0, 3))
    p.export()


def step_stones(name, seed, count=5, pal='shore', moss=0.2):
    if not want(name):
        return
    p = Prop(name)
    rnd = random.Random(seed)
    x = 0.0
    for k in range(count):
        r = rnd.uniform(0.55, 0.85)
        chunk(p, (x, rnd.uniform(-0.35, 0.35), 0.02), (r, r * rnd.uniform(0.75, 1.0), 0.20), seed + k * 3, pal, pts=14, boxy=0.8, flat=0.25, sub=1, turn=rnd.uniform(0, 3), moss=moss,
              zrange=(-0.2, 0.5))
        x += r * 2.1
    for v in p.bm.verts:
        v.co.x -= x / 2 - 0.6
    p.export()


for i, (nm, half, sd) in enumerate((("A", (1.55, 1.4, 1.25), 3), ("B", (3.6, 2.4, 2.7), 8), ("C", (1.1, 1.3, 0.7), 12), ("D", (2.2, 1.8, 2.3), 21), ("E", (2.8, 2.6, 1.4), 27), ("F", (1.0, 0.9, 1.3), 33))):
    rock("SM_BW_Rock_" + nm, half, sd, 'shore', boxy=0.5 + 0.08 * (i % 3), flat=0.12 if nm == "E" else 0.0)
rock("SM_BW_Boulder_A", (2.1, 1.85, 1.7), 41, 'shore', boxy=0.30, extra=1, pts=18)
rock("SM_BW_Boulder_B", (3.7, 2.5, 2.2), 44, 'shore', boxy=0.30, extra=2, pts=18)
rock("SM_BW_Boulder_C", (1.3, 1.2, 1.0), 47, 'grey', boxy=0.25, extra=0, pts=18)
for nm, half, sd in (("A", (1.8, 1.5, 1.3), 51), ("B", (3.0, 2.2, 2.4), 54), ("C", (1.2, 1.0, 0.8), 57)):
    rock("SM_BW_Rock_Moss_" + nm, half, sd, 'verdant', moss=0.75)
    rock("SM_BW_Rock_Ash_" + nm, half, sd + 100, 'ash')
    rock("SM_BW_Rock_Ember_" + nm, half, sd + 200, 'ember', boxy=0.7)
    rock("SM_BW_Rock_Grey_" + nm, half, sd + 300, 'grey')
rock("SM_BW_Rock_Flat_A", (2.2, 1.8, 0.45), 61, 'shore', boxy=0.8, flat=0.22, extra=1)
rock("SM_BW_Rock_Flat_B", (3.4, 2.6, 0.6), 64, 'shore', boxy=0.8, flat=0.22, extra=2, moss=0.3)
rock_pile("SM_BW_Rock_Pile_A", 71)
rock_pile("SM_BW_Rock_Pile_Moss", 74, 'verdant', 0.7)
rock_pile("SM_BW_Rock_Pile_Ember", 77, 'ember')
pebbles("SM_BW_Pebbles_A", 81, 1.3, 16)
pebbles("SM_BW_Pebbles_B", 84, 2.2, 26, 'grey', (0.06, 0.30))
step_stones("SM_BW_Step_Stones", 87)
for k, (nm, half, cuts, sh, tp) in enumerate(SLABS):
    slab(nm, half, 300 + k * 7, 'shore', moss=0.35 if k % 3 == 0 else 0.0)
sea_stack("SM_BW_SeaStack", 91, 3.4, 15.5)
sea_stack("SM_BW_SeaStack_B", 94, 2.4, 9.0, layers=4)
sea_stack("SM_BW_SeaStack_Ember", 97, 3.0, 12.0, 'ember', 0.0, layers=5)
spire("SM_BW_Spire_A", 101, 2.2, 11.0)
spire("SM_BW_Spire_B", 104, 1.5, 6.5, lean=0.2)
spire("SM_BW_Spire_Ash", 107, 2.0, 9.0, 'ash', lean=0.05)
arch("SM_BW_Rock_Arch", 111, 7.0, 6.5, 2.6)
arch("SM_BW_Cave_Mouth", 114, 4.2, 4.2, 2.4, 'verdant', 0.6, cave=True)
cliff("SM_BW_Cliff_A", 121, 14.0, 6.0, 10.0)
cliff("SM_BW_Cliff_B", 124, 9.0, 5.0, 6.5)
cliff("SM_BW_Cliff_Moss", 127, 12.0, 6.0, 8.5, 'verdant', 0.75)
