"""Export 13 rigged pirates/NPCs. Captain carries all 23 actions; others mesh+rig only."""
import bpy
import os

OUT = "C:/Users/User/AppData/Local/Temp/opencode/bwkit"
os.makedirs(OUT, exist_ok=True)

ctx = bpy.context
rigs = sorted([o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("BW_Rig_")],
              key=lambda o: o.name)
by_rig = {r.name: [] for r in rigs}
for o in bpy.data.objects:
    if o.type == "MESH" and o.modifiers:
        for m in o.modifiers:
            if m.type == "ARMATURE" and m.object is not None and m.object.name in by_rig:
                by_rig[m.object.name].append(o)

# rest pose everywhere so bind pose is clean
for r in rigs:
    ctx.view_layer.objects.active = r
    bpy.ops.object.select_all(action="DESELECT")
    r.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        r.animation_data.action = None
    except Exception:
        pass

done, failed = [], []
for r in rigs:
    try:
        bpy.ops.object.select_all(action="DESELECT")
        r.select_set(True)
        for m in by_rig[r.name]:
            m.select_set(True)
        ctx.view_layer.objects.active = r
        full = (r.name == "BW_Rig_Pirate_Captain")
        path = os.path.join(OUT, "SK_" + r.name[7:] + ".fbx")
        bpy.ops.export_scene.fbx(
            filepath=path, check_existing=False, use_selection=True,
            object_types={"ARMATURE", "MESH"}, apply_unit_scale=True,
            axis_forward="-Z", axis_up="Y", add_leaf_bones=False,
            primary_bone_axis="Y", secondary_bone_axis="X",
            bake_anim=full, bake_anim_use_all_bones=full,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=full,
            bake_anim_force_startend_keying=full,
            bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
        done.append(r.name)
    except Exception as e:
        failed.append(r.name + ": " + str(e)[:200])

result = {"rig_done": done, "rig_failed": failed}
