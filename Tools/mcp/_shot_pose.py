
import math
import bpy
from mathutils import Vector
ITEMS = [["Pirate_Captain", "Idle", "0"], ["Pirate_Quartermaster", "Wave", "12"], ["Pirate_Brute", "Carry_Idle", "0"], ["Pirate_Gunner", "Idle", "20"], ["Pirate_Lookout", "Spyglass", "20"], ["Pirate_Cook", "Idle_Hold", "0"], ["Pirate_OldSalt", "Talk", "20"], ["Pirate_Deckhand", "Dance", "8"]]
OUT = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Tools/mcp/_pv_crew.png"
VIEW = (285, 8, 0.6, 0.5)
scene = bpy.context.scene
rigs, home = [], {}
x = 0.0
for fig, act, frame in ITEMS:
    mesh = bpy.data.objects["SM_BW_" + fig]
    rig = mesh.parent
    home[rig.name] = rig.location.copy()
    rig.animation_data.action = bpy.data.actions["A_BW_" + act]
    rig.animation_data.action_slot = bpy.data.actions["A_BW_" + act].slots[0]
    scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    rig.animation_data.action = None
    rig.location = (x, 6000.0, 0.0)
    x += 1.9
    rigs.append((rig, mesh))
bpy.context.view_layer.update()
lo, hi = Vector((-1.0, 5999.0, -0.1)), Vector((x - 0.9, 6001.0, 2.4))
mid = (lo + hi) / 2
mid.z = lo.z + (hi.z - lo.z) * VIEW[3]
size = max((hi - lo).length * 0.6, (hi.x - lo.x))
cam, sun = bpy.data.objects["BW_ShotCam"], bpy.data.objects["BW_ShotSun"]
az, el = math.radians(VIEW[0]), math.radians(VIEW[1])
cam.location = mid + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * size * VIEW[2]
cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
sa, se = az + math.radians(55), math.radians(48)
sun.rotation_euler = (-Vector((math.cos(sa) * math.cos(se), math.sin(sa) * math.cos(se), math.sin(se)))).to_track_quat('-Z', 'Y').to_euler()
keep = {o.name: o.hide_render for o in bpy.data.objects}
shown = {m for r, m in rigs}
for o in bpy.data.objects:
    o.hide_render = not (o in shown or o is sun)
prev = (scene.camera, scene.render.engine, scene.render.filepath, scene.render.resolution_x, scene.render.resolution_y, scene.world, scene.view_settings.view_transform)
scene.camera, scene.world = cam, bpy.data.worlds["BW_ShotWorld"]
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
(scene.camera, scene.render.engine, scene.render.filepath, scene.render.resolution_x, scene.render.resolution_y, scene.world, scene.view_settings.view_transform) = prev
for o in bpy.data.objects:
    o.hide_render = keep.get(o.name, False)
idle = bpy.data.actions["A_BW_Idle"]
for rig, mesh in rigs:
    rig.location = home[rig.name]
    rig.animation_data.action = idle
    rig.animation_data.action_slot = idle.slots[0]
scene.frame_set(0)
result = {"shot": OUT, "error": err}
