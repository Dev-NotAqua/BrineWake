"""Runs inside the open Blender (python bl.py bl_export.py 3000): writes the kit for Unreal.
Art/Export/Static/<name>.fbx   one file per prop, pivot at its origin, vertex paint kept linear
Art/Export/Rigged/<name>.fbx   one file per figure with the shared skeleton; the first one also carries every action
Art/Export/manifest.json       names, sizes and triangle counts
Set ONLY to a tuple of name fragments to export part of the kit."""
import json
import os

import bpy

OUT = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/Export/T"
ONLY = ("NPC_Alekeeper",)
MASTER = "SM_BW_NPC_Alekeeper"
os.makedirs(OUT + "/Static", exist_ok=True)
os.makedirs(OUT + "/Rigged", exist_ok=True)
kit = bpy.data.collections["Brinewake Kit"]
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
manifest = {"static": {}, "rigged": {}, "anims": []}
errors = {}


def export(path, objs, active, **kw):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active
    with bpy.context.temp_override(window=win, area=area, region=region, selected_objects=objs, active_object=active, object=active):
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, colors_type='LINEAR', add_leaf_bones=False, axis_forward='-Y', axis_up='Z', **kw)


meshes = sorted((o for o in kit.objects if o.type == 'MESH'), key=lambda o: o.name)
for o in meshes:
    if ONLY and not any(k in o.name for k in ONLY):
        continue
    try:
        if o.get("bw_rig") and o.parent is not None and o.parent.type == 'ARMATURE':
            rig = o.parent
            home, old = rig.location.copy(), rig.name
            other = bpy.data.objects.get("BW_Rig")
            if other is not None and other is not rig:
                other.name = "BW_Rig_old"
            rig.location = (0, 0, 0)
            rig.name = "BW_Rig"                                    # Unreal drops a node of this name, so 'root' stays the root bone
            bpy.context.view_layer.update()
            master = o.name == MASTER
            export(OUT + "/Rigged/" + o.name.replace("SM_", "SK_") + ".fbx", [rig, o], rig, object_types={'ARMATURE', 'MESH'}, mesh_smooth_type='FACE', bake_anim=master,
                   bake_anim_use_all_actions=master, bake_anim_use_nla_strips=False, bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                   bake_anim_simplify_factor=0.0, use_armature_deform_only=True)
            rig.name = old
            rig.location = home
            idle = bpy.data.actions.get("A_BW_Idle")
            if idle is not None:
                rig.animation_data.action = idle
                rig.animation_data.action_slot = idle.slots[0]
            manifest["rigged"][o.name.replace("SM_", "SK_")] = {"tris": len(o.data.polygons), "master": master}
        else:
            home = o.location.copy()
            o.location = (0, 0, 0)
            bpy.context.view_layer.update()
            export(OUT + "/Static/" + o.name + ".fbx", [o], o, object_types={'MESH'}, mesh_smooth_type='FACE', bake_space_transform=True, bake_anim=False)
            o.location = home
            bb = [o.bound_box[0][:], o.bound_box[6][:]]
            manifest["static"][o.name] = {"tris": len(o.data.polygons), "min": [round(v, 2) for v in bb[0]], "max": [round(v, 2) for v in bb[1]]}
    except Exception as e:
        errors[o.name] = str(e)[:300]
manifest["anims"] = sorted([a.name, int(a.get("bw_frames", 0)), bool(a.get("bw_loop", True))] for a in bpy.data.actions if a.name.startswith("A_BW_"))
bpy.context.view_layer.update()
if not ONLY:
    json.dump(manifest, open(OUT + "/manifest.json", "w"), indent=0)
result = {"static": len(manifest["static"]), "rigged": len(manifest["rigged"]), "anims": len(manifest["anims"]), "errors": errors}
