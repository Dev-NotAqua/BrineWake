"""Export Brinewake Kit (static) + rigged pirates (skeletal) to FBX for UE import."""
import bpy
import os

OUT = "C:/Users/User/AppData/Local/Temp/opencode/bwkit"
os.makedirs(OUT, exist_ok=True)

ctx = bpy.context
kit = bpy.data.collections.get("Brinewake Kit")

skinned = set()
for o in bpy.data.objects:
    if o.type == "MESH" and o.modifiers:
        for m in o.modifiers:
            if m.type == "ARMATURE" and m.object is not None:
                skinned.add(o.name)

static_objs = [o for o in kit.objects if o.type == "MESH" and o.name not in skinned]

done, failed = [], []
for o in static_objs:
    try:
        ctx.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        loc = o.location.copy()
        o.location = (0, 0, 0)
        path = os.path.join(OUT, o.name + ".fbx")
        bpy.ops.export_scene.fbx(
            filepath=path, check_existing=False, use_selection=True,
            object_types={"MESH"}, apply_unit_scale=True,
            axis_forward="-Z", axis_up="Y", bake_anim=False,
            add_leaf_bones=False)
        o.location = loc
        done.append(o.name)
    except Exception as e:
        failed.append(o.name + ": " + str(e)[:150])

result = {"static_done": len(done), "static_failed": failed[:10], "out": OUT}
