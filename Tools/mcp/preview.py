"""blender -b --python preview.py -- out.png a.fbx b.fbx ...  : workbench render of the vertex-painted props side by side"""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
x = 0.0
for path in args[1:]:
    bpy.ops.import_scene.fbx(filepath=path)
    for o in bpy.context.selected_objects:
        o.location.x += x
        if o.type == 'MESH' and o.data.color_attributes:
            o.data.color_attributes.active_color = o.data.color_attributes[0]
            print('PV attr', o.name, [(a.name, a.domain, a.data_type) for a in o.data.color_attributes])
        w = max(o.dimensions.x, o.dimensions.y)
    x += w + 0.5
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = "FLAT"
sh.color_type = 'VERTEX'
sh.show_cavity = True
sh.show_shadows = False
scene.world = bpy.data.worlds.new('w')
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x, scene.render.resolution_y = 1100, 650
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
mid = Vector(((x - 0.5) / 2 - 0.4, 0, 0.5))
dist = float(args[0].split("@")[1]) if "@" in args[0] else 3.6
cam.location = mid + Vector((dist * 0.55, -dist, dist * 0.55))
cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = args[0].split("@")[0]
bpy.ops.render.render(write_still=True)
