import json
OT="editor_toolset.toolsets.object.ObjectTools."
AS="editor_toolset.toolsets.asset.AssetTools."
SK="editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools."
SRC="C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/Export/Rigged"
F="/Game/Brinewake/Characters"
M="/Game/Brinewake/Props/M_BW_Painted.M_BW_Painted"
MASTER="SK_BW_NPC_Alekeeper"
NAMES="__NAMES__".split(",")
def call(n,a): return execute_tool(n,json.dumps(a))
def run():
    out={}
    for n in NAMES:
        try:
            if call(AS+"exists",{"path":F+"/"+n})["returnValue"]: call(AS+"delete",{"path":F+"/"+n})
            args={"folder_path":F,"asset_name":n,"source_file":SRC+"/"+n+".fbx","import_materials":False,"import_textures":False,"import_animations":n==MASTER,"create_physics_asset":False}
            if n!=MASTER: args["skeleton"]={"refPath":F+"/"+MASTER+"_Skeleton."+MASTER+"_Skeleton"}
            call(SK+"import_file",args)
            mesh={"refPath":F+"/"+n+"."+n}
            for s in call(SK+"get_material_slots",{"mesh":mesh})["returnValue"]:
                call(SK+"set_material",{"mesh":mesh,"slot_name":s,"material":{"refPath":M}})
            out[n]={"bones":len(call(SK+"get_bone_names",{"mesh":mesh})["returnValue"]),"b":call(SK+"get_bounds",{"mesh":mesh})["returnValue"],"skel":call(SK+"get_skeleton",{"mesh":mesh})["returnValue"]}
            call(AS+"save_assets",{"asset_paths":[F+"/"+n]})
        except Exception as e:
            out[n]="ERR "+str(e)[:400]
    try:
        out["assets"]=[(a.get("packageName","") if isinstance(a,dict) else str(a)).split("/")[-1] for a in call(AS+"find_assets",{"folder_path":F,"name":"","asset_type":"","recursive":True,"tags":{}})["returnValue"]]
    except Exception as e: out["assets"]=str(e)[:200]
    return out
