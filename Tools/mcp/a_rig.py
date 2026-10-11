# Brinewake pirate rig and animation pack. Runs inside the open Blender (python bl.py a_rig.py), after a_crew2.py.
# One skeleton (20 bones, Unreal-style names) is shared by every figure: each gets its own armature object on the same
# armature data, so a single set of actions drives them all. Actions are keyed on every frame at 30 fps, in place.
import math

import bpy
from mathutils import Euler, Matrix, Vector

FPS = 30
J = {'root': ((0, 0, 0), (0, 0, 0.25), None),
     'pelvis': ((0, 0, 0.97), (0, 0, 1.10), 'root'),
     'spine_01': ((0, -0.01, 1.10), (0, 0, 1.30), 'pelvis'),
     'spine_02': ((0, 0, 1.30), (0, 0.01, 1.52), 'spine_01'),
     'neck': ((0, 0.01, 1.52), (0, 0, 1.64), 'spine_02'),
     'head': ((0, 0, 1.64), (0, 0, 1.96), 'neck')}
for s, x in (('_l', 1.0), ('_r', -1.0)):
    J['clavicle' + s] = ((x * 0.03, 0, 1.47), (x * 0.25, 0, 1.49), 'spine_02')
    J['upperarm' + s] = ((x * 0.25, 0, 1.49), (x * 0.40, 0.03, 1.20), 'clavicle' + s)
    J['lowerarm' + s] = ((x * 0.40, 0.03, 1.20), (x * 0.45, -0.10, 0.96), 'upperarm' + s)
    J['hand' + s] = ((x * 0.45, -0.10, 0.96), (x * 0.48, -0.15, 0.78), 'lowerarm' + s)
    J['thigh' + s] = ((x * 0.14, 0, 0.95), (x * 0.155, -0.025, 0.52), 'pelvis')
    J['calf' + s] = ((x * 0.155, -0.025, 0.52), (x * 0.17, 0.02, 0.10), 'thigh' + s)
    J['foot' + s] = ((x * 0.17, 0.02, 0.10), (x * 0.17, -0.20, 0.03), 'calf' + s)
ORDER = ['root', 'pelvis', 'spine_01', 'spine_02', 'neck', 'head', 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
         'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r']
log = []


def view_override():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return dict(window=win, area=area, region=region)


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def build_skeleton():
    arm = bpy.data.armatures.get("BW_Skeleton")
    if arm is not None and len(arm.bones) == len(ORDER):
        return arm
    if arm is None:
        arm = bpy.data.armatures.new("BW_Skeleton")
    ob = bpy.data.objects.new("BW_Rig_Build", arm)
    collection("Brinewake Rigs").objects.link(ob)
    with bpy.context.temp_override(**view_override()):
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for b in list(arm.edit_bones):
            arm.edit_bones.remove(b)
        for name in ORDER:
            head, tail, parent = J[name]
            eb = arm.edit_bones.new(name)
            eb.head, eb.tail, eb.roll = Vector(head), Vector(tail), 0.0
            if parent:
                eb.parent = arm.edit_bones[parent]
                eb.use_connect = False
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(ob)
    return arm


def rig_for(mesh_ob, arm):
    name = "BW_Rig_" + mesh_ob.name.replace("SM_BW_", "")
    rig = bpy.data.objects.get(name)
    if rig is None:
        rig = bpy.data.objects.new(name, arm)
        collection("Brinewake Rigs").objects.link(rig)
    rig.data = arm
    if mesh_ob.parent is not rig:
        rig.location = mesh_ob.matrix_world.translation.copy()
        mesh_ob.parent = rig
        mesh_ob.matrix_parent_inverse = Matrix.Identity(4)
        mesh_ob.location = (0, 0, 0)
    mod = mesh_ob.modifiers.get("Armature") or mesh_ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig


# ---------------------------------------------------------------- pose language
# Angles are radians in the character's own terms; they are turned into armature-axis rotations (x to its left,
# y behind it, z up) and then into each bone's local rest frame.
def clamp01(x):
    return max(0.0, min(1.0, x))


def sstep(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def pose(pelvis=(0, 0, 0), loc=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0),
         la=(0, 0, 0), ra=(0, 0, 0), le=0.3, re=0.3, lh=(0, 0, 0), rh=(0, 0, 0),
         ll=(0, 0.03), rl=(0, 0.03), lk=0.06, rk=0.06, lf=0.0, rf=0.0):
    """pelvis/spine/chest/neck/head = (lean forward, bend to its left, turn to its left); loc = pelvis shift (left, back, up).
    la/ra = (swing forward, lift sideways, twist), le/re = elbow bend; ll/rl = (swing forward, spread), lk/rk = knee bend, lf/rf = toes down."""
    return {'pelvis': (pelvis[0], -pelvis[1], pelvis[2]), 'pelvis_loc': loc,
            'spine_01': (spine[0], -spine[1], spine[2]), 'spine_02': (chest[0], -chest[1], chest[2]), 'neck': (neck[0], -neck[1], neck[2]), 'head': (head[0], -head[1], head[2]),
            'upperarm_l': (-la[0], 0.22 - la[1], la[2]), 'upperarm_r': (-ra[0], -0.22 + ra[1], -ra[2]),
            'lowerarm_l': (-le, 0, 0), 'lowerarm_r': (-re, 0, 0), 'hand_l': (-lh[0], lh[1], lh[2]), 'hand_r': (-rh[0], -rh[1], -rh[2]),
            'thigh_l': (-ll[0], -ll[1], 0), 'thigh_r': (-rl[0], rl[1], 0), 'calf_l': (lk, 0, 0), 'calf_r': (rk, 0, 0), 'foot_l': (lf, 0, 0), 'foot_r': (rf, 0, 0)}


def mix(a, b, t):
    out = {}
    for k in a:
        out[k] = tuple(a[k][i] + (b[k][i] - a[k][i]) * t for i in range(3))
    return out


def keyed(t, keys):
    """Blend through (time, pose) keys with eased steps."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t <= t1:
            return mix(p0, p1, sstep(t0, t1, t))
    return keys[-1][1]


def a_idle(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    return pose(pelvis=(0, 0.01 * s, 0.03 * s), loc=(0.012 * s, 0, -0.012 + 0.006 * c), spine=(0.02 + 0.015 * c, 0, 0), chest=(0.04 + 0.025 * c, 0, -0.02 * s), head=(-0.03 * c, 0, 0.05 * s),
                la=(0.04 * s, 0.02 * c, 0), ra=(-0.04 * s, 0.02 * c, 0), le=0.34 + 0.04 * c, re=0.34 + 0.04 * c, lk=0.08, rk=0.08)


def a_idle_hold(t):
    p = a_idle(t)
    s = math.sin(2 * math.pi * t)
    q = pose(ra=(0.38 + 0.03 * s, 0.10, 0), re=1.15 + 0.05 * s)
    p['upperarm_r'], p['lowerarm_r'] = q['upperarm_r'], q['lowerarm_r']
    return p


def walk_legs(s, c, amp, knee, lift=0.10):
    return dict(ll=(amp * s, 0.03), rl=(-amp * s, 0.03), lk=lift + knee * max(0.0, c) ** 1.5, rk=lift + knee * max(0.0, -c) ** 1.5, lf=-0.25 * s, rf=0.25 * s)


def a_walk(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    c2 = math.cos(4 * math.pi * t)
    return pose(pelvis=(0.02, 0.04 * c, -0.10 * s), loc=(-0.03 * c, 0, -0.02 + 0.025 * c2), spine=(0.04, -0.03 * c, 0.05 * s), chest=(0.05, 0.05 * c, 0.16 * s), head=(-0.04, 0, -0.08 * s),
                la=(-0.45 * s, 0.04, 0), ra=(0.45 * s, 0.04, 0), le=0.38 - 0.2 * s, re=0.38 + 0.2 * s, **walk_legs(s, c, 0.50, 0.95))


def a_run(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    c2 = math.cos(4 * math.pi * t)
    return pose(pelvis=(0.12, 0.05 * c, -0.14 * s), loc=(-0.02 * c, 0, -0.05 + 0.05 * c2), spine=(0.16, 0, 0.08 * s), chest=(0.14, 0, 0.24 * s), head=(-0.22, 0, -0.10 * s),
                la=(-0.95 * s, 0.10, 0), ra=(0.95 * s, 0.10, 0), le=1.35, re=1.35, **walk_legs(s, c, 0.90, 1.35, 0.30))


def a_jump(t):
    s = math.sin(2 * math.pi * t)
    return pose(pelvis=(0.05, 0, 0), spine=(0.06, 0, 0), chest=(0.05, 0, 0), la=(0.25 + 0.05 * s, 0.75 + 0.06 * s, 0), ra=(0.15 - 0.05 * s, 0.70 - 0.06 * s, 0), le=0.55, re=0.6,
                ll=(0.55 + 0.04 * s, 0.05), rl=(0.12 - 0.04 * s, 0.08), lk=0.95, rk=0.55, lf=0.35, rf=0.45)


def a_swim_tread(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    return pose(pelvis=(0.12, 0, 0.03 * s), loc=(0, 0, 0.035 * math.sin(4 * math.pi * t)), spine=(0.04, 0, 0), chest=(0.02, 0, 0.05 * s), head=(-0.14, 0, 0),
                la=(0.35 + 0.38 * s, 0.95 + 0.10 * c, 0), ra=(0.35 - 0.38 * s, 0.95 - 0.10 * c, 0), le=0.55 + 0.28 * c, re=0.55 - 0.28 * c,
                ll=(0.45 + 0.38 * s, 0.16), rl=(0.45 - 0.38 * s, 0.16), lk=0.90 + 0.38 * c, rk=0.90 - 0.38 * c, lf=0.5, rf=0.5)


def a_swim_forward(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    pull, back = max(0.0, s), max(0.0, -s)
    return pose(pelvis=(1.30 + 0.04 * c, 0, 0), loc=(0, 0, 0.03 * c), spine=(-0.14, 0, 0), chest=(-0.12, 0, 0), neck=(-0.40, 0, 0), head=(-0.50, 0, 0),
                la=(2.75 - 0.95 * (1 - c), 0.15 + 0.95 * pull, 0), ra=(2.75 - 0.95 * (1 - c), 0.15 + 0.95 * pull, 0), le=0.15 + 1.25 * back, re=0.15 + 1.25 * back,
                ll=(0.95 * back - 0.10, 0.18 + 0.50 * back), rl=(0.95 * back - 0.10, 0.18 + 0.50 * back), lk=0.12 + 1.5 * back, rk=0.12 + 1.5 * back, lf=0.7 - 0.9 * back, rf=0.7 - 0.9 * back)


def a_talk(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    s2 = math.sin(4 * math.pi * t)
    return pose(pelvis=(0, 0.02, 0.04 * s), loc=(0.015 * s, 0, -0.012), chest=(0.04, 0, 0.06 * s), head=(0.05 * s2, 0.03 * c, 0.10 * s),
                la=(-0.18, 0.50, 0), le=1.55, ra=(0.55 + 0.14 * s2, 0.18 + 0.10 * c, 0), re=1.30 + 0.28 * math.sin(4 * math.pi * t + 1.0), rh=(0.2 * s2, 0, 0), lk=0.08, rk=0.08)


def a_wave(t):
    s = math.sin(2 * math.pi * t)
    s2 = math.sin(4 * math.pi * t)
    p = a_idle(t)
    q = pose(ra=(0.25, 2.35 + 0.28 * s2, 0), re=0.55 - 0.25 * s2, rh=(0, 0.3 * s2, 0), chest=(0.03, -0.06, 0.04 * s), head=(-0.08, 0, -0.10))
    for k in ('upperarm_r', 'lowerarm_r', 'hand_r', 'spine_02', 'head'):
        p[k] = q[k]
    return p


def a_cheer(t):
    s2 = math.sin(4 * math.pi * t)
    up = abs(math.sin(2 * math.pi * t))
    return pose(loc=(0, 0, -0.05 + 0.07 * up), chest=(-0.08, 0, 0), head=(-0.20, 0, 0), la=(0.30, 2.45 + 0.18 * s2, 0), ra=(0.30, 2.45 - 0.18 * s2, 0), le=0.45 + 0.3 * s2, re=0.45 - 0.3 * s2,
                ll=(0.16 - 0.14 * up, 0.08), rl=(0.16 - 0.14 * up, 0.08), lk=0.34 - 0.28 * up, rk=0.34 - 0.28 * up, lf=0.10, rf=0.10)


def a_sit(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    return pose(pelvis=(-0.06, 0, 0), loc=(0, 0.05, -0.40), spine=(0.12 + 0.015 * c, 0, 0), chest=(0.10 + 0.02 * c, 0, 0.03 * s), head=(-0.08, 0, 0.06 * s),
                la=(0.50, 0.06, 0), ra=(0.50, 0.06, 0), le=0.85, re=0.85, ll=(1.48, 0.20), rl=(1.48, 0.20), lk=1.45, rk=1.45, lf=0.05, rf=0.05)


def a_drink(t):
    k = sstep(0.12, 0.32, t) - sstep(0.60, 0.82, t)
    p = a_idle(t)
    q = pose(ra=(0.38 + 0.95 * k, 0.10 + 0.28 * k, 0), re=1.15 + 1.10 * k, rh=(0.35 * k, 0, 0), head=(-0.32 * k, 0, 0), chest=(0.04 - 0.10 * k, 0, 0))
    for key in ('upperarm_r', 'lowerarm_r', 'hand_r', 'head', 'spine_02'):
        p[key] = q[key]
    return p


def a_slash(t):
    ready = pose(pelvis=(0, 0, -0.10), chest=(0.04, 0, -0.15), ra=(0.5, 0.25, 0), re=1.1, la=(0.1, 0.2, 0), le=0.8, ll=(0.25, 0.08), rl=(-0.2, 0.08), lk=0.3, rk=0.2)
    wind = pose(pelvis=(0, 0, -0.30), spine=(-0.05, 0, -0.15), chest=(-0.08, 0, -0.40), head=(0, 0, 0.35), ra=(2.3, 0.75, 0), re=1.15, la=(0.35, 0.35, 0), le=0.9,
                ll=(0.30, 0.08), rl=(-0.25, 0.08), lk=0.35, rk=0.2)
    hit = pose(pelvis=(0.06, 0, 0.30), spine=(0.14, 0, 0.20), chest=(0.20, 0, 0.50), head=(0.05, 0, -0.35), ra=(0.75, -0.45, 0), re=0.12, rh=(0.3, 0, 0), la=(-0.35, 0.45, 0), le=1.0,
               ll=(0.50, 0.08), rl=(-0.35, 0.08), lk=0.55, rk=0.15, loc=(0, -0.06, -0.06))
    return keyed(t, [(0.0, ready), (0.30, wind), (0.50, hit), (0.66, hit), (1.0, ready)])


def a_dig(t):
    c = math.cos(2 * math.pi * t)
    k = 0.5 - 0.5 * c
    return pose(pelvis=(0.10 + 0.20 * k, 0, 0), loc=(0, 0, -0.06 - 0.12 * k), spine=(0.22 + 0.30 * k, 0, 0.08), chest=(0.12 + 0.18 * k, 0, 0.10), head=(-0.25 - 0.1 * k, 0, 0),
                la=(0.95 - 0.35 * k, 0.05, 0), ra=(0.70 - 0.45 * k, 0.05, 0), le=1.05 - 0.75 * k, re=0.75 - 0.55 * k, ll=(0.42 + 0.20 * k, 0.10), rl=(0.05 + 0.25 * k, 0.10),
                lk=0.45 + 0.30 * k, rk=0.30 + 0.35 * k, lf=0.0, rf=0.12)


def a_steer(t):
    s = math.sin(2 * math.pi * t)
    return pose(pelvis=(0, 0, 0.03 * s), loc=(0.015 * s, 0, -0.03), spine=(0.05, 0.03 * s, 0), chest=(0.06, 0.04 * s, 0.05 * s), head=(-0.06, 0, -0.05 * s),
                la=(1.15 + 0.28 * s, 0.28, 0), ra=(1.15 - 0.28 * s, 0.28, 0), le=0.45 - 0.22 * s, re=0.45 + 0.22 * s, ll=(0.04, 0.14), rl=(-0.04, 0.14), lk=0.14, rk=0.14)


def a_climb(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    return pose(pelvis=(0.04, 0.05 * s, 0.05 * s), loc=(0.02 * s, 0, 0.03 * math.cos(4 * math.pi * t)), spine=(0.04, 0, 0), chest=(0.02, -0.05 * s, 0), head=(-0.35, 0, 0),
                la=(2.30 + 0.50 * s, 0.12, 0), ra=(2.30 - 0.50 * s, 0.12, 0), le=0.95 - 0.55 * s, re=0.95 + 0.55 * s,
                ll=(0.75 - 0.50 * s, 0.10), rl=(0.75 + 0.50 * s, 0.10), lk=1.05 - 0.60 * s, rk=1.05 + 0.60 * s, lf=0.2, rf=0.2)


def a_carry_idle(t):
    p = a_idle(t)
    q = pose(la=(0.55, 0.12, 0), ra=(0.55, 0.12, 0), le=1.35, re=1.35, spine=(-0.08, 0, 0), chest=(-0.06, 0, 0))
    for key in ('upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'spine_01', 'spine_02'):
        p[key] = q[key]
    return p


def a_carry_walk(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    c2 = math.cos(4 * math.pi * t)
    return pose(pelvis=(0.0, 0.05 * c, -0.08 * s), loc=(-0.035 * c, 0, -0.03 + 0.02 * c2), spine=(-0.08, -0.04 * c, 0.03 * s), chest=(-0.06, 0.04 * c, 0.06 * s), head=(0.02, 0, -0.04 * s),
                la=(0.55, 0.12, 0), ra=(0.55, 0.12, 0), le=1.35 + 0.04 * c2, re=1.35 + 0.04 * c2, **walk_legs(s, c, 0.38, 0.75))


def a_dance(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    hop = abs(math.sin(2 * math.pi * t))
    return pose(pelvis=(0, 0.06 * s, 0.12 * s), loc=(0.03 * s, 0, -0.03 + 0.07 * hop), spine=(0, -0.05 * s, 0), chest=(0.02, 0.08 * s, -0.16 * s), head=(0, 0.10 * c, 0.08 * s),
                la=(-0.12, 0.80, 0.3), ra=(-0.12, 0.80, 0.3), le=1.75, re=1.75, ll=(0.85 * max(0.0, s), 0.10), rl=(0.85 * max(0.0, -s), 0.10),
                lk=0.20 + 0.50 * max(0.0, -s) * hop, rk=0.20 + 0.50 * max(0.0, s) * hop, lf=0.45 * max(0.0, s), rf=0.45 * max(0.0, -s))


def a_death(t):
    stand = a_idle(0.0)
    stagger = pose(pelvis=(-0.18, 0.05, 0.1), loc=(0, 0.10, -0.08), spine=(-0.15, 0, 0), chest=(-0.20, 0, 0), head=(-0.30, 0, 0.2), la=(0.2, 0.9, 0), ra=(-0.1, 1.0, 0), le=0.6, re=0.5,
                   ll=(0.25, 0.10), rl=(-0.1, 0.12), lk=0.5, rk=0.35)
    down = pose(pelvis=(-1.50, 0.04, 0.05), loc=(0, 0.42, -0.80), spine=(0.03, 0, 0), chest=(0.05, 0, 0), head=(0.10, 0.2, 0.3), la=(0.05, 1.15, 0), ra=(-0.05, 0.85, 0), le=0.35, re=0.6,
                ll=(0.12, 0.16), rl=(0.30, 0.10), lk=0.12, rk=0.55, lf=0.5, rf=0.4)
    return keyed(t, [(0.0, stand), (0.22, stagger), (0.62, down), (1.0, down)])


def a_hammer(t):
    k = (0.5 - 0.5 * math.cos(2 * math.pi * t)) ** 2.2
    return pose(pelvis=(0.08, 0, -0.06), loc=(0, 0, -0.05), spine=(0.20 - 0.06 * k, 0, -0.05), chest=(0.14 - 0.10 * k, 0, -0.08 - 0.12 * k), head=(-0.12, 0, 0.06),
                la=(0.75, 0.10, 0), le=0.90, ra=(0.55 + 0.95 * k, 0.20 + 0.10 * k, 0), re=0.70 + 1.05 * k, rh=(-0.3 * k, 0, 0), ll=(0.22, 0.08), rl=(-0.10, 0.10), lk=0.30, rk=0.15)


def a_spyglass(t):
    s = math.sin(2 * math.pi * t)
    return pose(pelvis=(0, 0, 0.10 * s), loc=(0, 0, -0.012), chest=(-0.04, 0, 0.20 * s), head=(-0.05, 0, 0.14 * s), ra=(1.38, 0.42, 0), re=2.0, la=(-0.18, 0.50, 0), le=1.55, lk=0.08, rk=0.08)


def a_row(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    k = 0.5 - 0.5 * c
    return pose(pelvis=(-0.10 + 0.50 * k, 0, 0), loc=(0, 0.05, -0.40), spine=(0.05 + 0.25 * k, 0, 0), chest=(0.05 + 0.15 * k, 0, 0), head=(-0.20 * k, 0, 0),
                la=(1.25 - 0.55 * (1 - k) + 0.1 * s, 0.20, 0), ra=(1.25 - 0.55 * (1 - k) + 0.1 * s, 0.20, 0), le=0.25 + 1.30 * (1 - k), re=0.25 + 1.30 * (1 - k),
                ll=(1.30 + 0.20 * k, 0.16), rl=(1.30 + 0.20 * k, 0.16), lk=1.00 + 0.50 * k, rk=1.00 + 0.50 * k)


ANIMS = [("Idle", 80, a_idle, True), ("Idle_Hold", 80, a_idle_hold, True), ("Walk", 32, a_walk, True), ("Run", 20, a_run, True), ("Jump", 24, a_jump, True),
         ("Swim_Tread", 40, a_swim_tread, True), ("Swim_Forward", 44, a_swim_forward, True), ("Talk", 72, a_talk, True), ("Wave", 48, a_wave, True), ("Cheer", 36, a_cheer, True),
         ("Sit", 80, a_sit, True), ("Drink", 96, a_drink, True), ("Slash", 26, a_slash, False), ("Dig", 44, a_dig, True), ("Steer", 72, a_steer, True), ("Climb", 34, a_climb, True),
         ("Carry_Idle", 80, a_carry_idle, True), ("Carry_Walk", 34, a_carry_walk, True), ("Dance", 30, a_dance, True), ("Death", 40, a_death, False), ("Hammer", 26, a_hammer, True),
         ("Spyglass", 90, a_spyglass, True), ("Row", 50, a_row, True)]


def apply_pose(rig, P, rest):
    for pb in rig.pose.bones:
        e = P.get(pb.name)
        R = rest[pb.name]
        if e is None:
            pb.rotation_quaternion = (1, 0, 0, 0)
        else:
            q = Euler(e, 'XYZ').to_matrix()
            pb.rotation_quaternion = (R.inverted() @ q @ R).to_quaternion()
        pb.location = (R.inverted() @ Vector(P['pelvis_loc'])) if pb.name == 'pelvis' else (0, 0, 0)


def bake(rig, rest):
    made = []
    for name, frames, fn, loop in ANIMS:
        act = bpy.data.actions.get("A_BW_" + name)
        if act is not None:
            bpy.data.actions.remove(act)
        act = bpy.data.actions.new("A_BW_" + name)
        act.use_fake_user = True
        if rig.animation_data is None:
            rig.animation_data_create()
        rig.animation_data.action = act
        last = frames if loop else frames - 1
        for f in range(frames + (1 if loop else 0)):
            apply_pose(rig, fn(f / last if not loop else f / frames), rest)
            for pb in rig.pose.bones:
                pb.keyframe_insert("rotation_quaternion", frame=f)
                if pb.name == 'pelvis':
                    pb.keyframe_insert("location", frame=f)
        act["bw_frames"] = frames
        act["bw_loop"] = loop
        made.append(name)
    return made


arm = build_skeleton()
rest = {b.name: b.matrix_local.to_3x3() for b in arm.bones}
kit = bpy.data.collections["Brinewake Kit"]
figures = sorted((o for o in kit.objects if o.get("bw_rig")), key=lambda o: o.name)
rigs = [rig_for(o, arm) for o in figures]
bpy.context.scene.render.fps = FPS
master = rigs[0]
made = bake(master, rest)
idle = bpy.data.actions["A_BW_Idle"]
for rig in rigs:                                                     # leave everyone breathing in the idle
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = idle
    rig.animation_data.action_slot = idle.slots[0]               # a slot is not picked automatically for another object
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, 80
bpy.context.scene.frame_set(0)
result = {"bones": len(arm.bones), "figures": [o.name for o in figures], "actions": made, "slots": [len(a.slots) for a in bpy.data.actions if a.name.startswith("A_BW_")][:3]}
