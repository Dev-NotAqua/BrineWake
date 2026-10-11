"""Runs inside the open Blender: renders the named kit objects to a PNG with Eevee (sun + sky light, vertex paint).
shot.py fills in NAMES / OUT / VIEW."""
import math

import bpy
from mathutils import Vector

NAMES = ["SM_BW_Sloop", "SM_BW_Brigantine", "SM_BW_Galleon"]
OUT = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Tools/mcp/_pv_ships.png"
VIEW = (222, 14, 1.15, 0.42)            # (azimuth deg, elevation deg, distance factor, focus height 0..1)

scene = bpy.context.scene
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == 'VIEW_3D':                      # let the owner see the paint in their own viewport too
        sp = area.spaces.active
        sp.shading.type = 'SOLID'
        sp.shading.color_type = 'VERTEX'
        sp.shading.light = 'STUDIO'
        sp.shading.show_cavity = True
objs = [bpy.data.objects[n] for n in NAMES if n in bpy.data.objects]
home = {o.name: o.location.copy() for o in objs}
if len(objs) > 1:                                   # line the chosen assets up side by side for the picture, then put them back
    x = 0.0
    for o in objs:
        w = max(o.dimensions.x, o.dimensions.y)
        o.location = (x + w / 2, 5000.0, 0.0)
        x += w + max(0.4, w * 0.15)
    bpy.context.view_layer.update()
lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
        hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
mid = (lo + hi) / 2
mid.z = lo.z + (hi.z - lo.z) * VIEW[3]
size = max((hi - lo).length * 0.6, (hi.x - lo.x), (hi.y - lo.y))


def get(name, data_new):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, data_new())
        scene.collection.objects.link(ob)
    return ob


cam = get("BW_ShotCam", lambda: bpy.data.cameras.new("BW_ShotCam"))
sun = get("BW_ShotSun", lambda: bpy.data.lights.new("BW_ShotSun", 'SUN'))
az, el = math.radians(VIEW[0]), math.radians(VIEW[1])
cam.location = mid + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * size * VIEW[2]
cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens, cam.data.clip_end = 40, 3000
sa, se = az + math.radians(55), math.radians(48)
sun.rotation_euler = (-Vector((math.cos(sa) * math.cos(se), math.sin(sa) * math.cos(se), math.sin(se)))).to_track_quat('-Z', 'Y').to_euler()
sun.data.energy, sun.data.angle = 3.2, 0.06
world = bpy.data.worlds.get("BW_ShotWorld")
if world is None:
    world = bpy.data.worlds.new("BW_ShotWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.62, 0.78, 0.95, 1.0)
    bg.inputs[1].default_value = 0.85
keep = {o.name: o.hide_render for o in bpy.data.objects}
for o in bpy.data.objects:
    o.hide_render = not (o in objs or o is sun)
prev = (scene.camera, scene.render.engine, scene.render.filepath, scene.render.resolution_x, scene.render.resolution_y, scene.world,
        scene.view_settings.view_transform)
scene.camera, scene.world = cam, world
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 1400, 860
scene.render.filepath = OUT
scene.view_settings.view_transform = 'Standard'
err = ""
try:
    bpy.ops.render.render(write_still=True)
except Exception as e:
    err = str(e)
(scene.camera, scene.render.engine, scene.render.filepath, scene.render.resolution_x, scene.render.resolution_y, scene.world,
 scene.view_settings.view_transform) = prev
for o in bpy.data.objects:
    o.hide_render = keep.get(o.name, False)
for o in objs:
    o.location = home[o.name]
result = {"shot": OUT, "objects": len(objs), "error": err}
