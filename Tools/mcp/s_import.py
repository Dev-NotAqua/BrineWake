import json
OT="editor_toolset.toolsets.object.ObjectTools."
AS="editor_toolset.toolsets.asset.AssetTools."
SM="editor_toolset.toolsets.static_mesh.StaticMeshTools."
SRC="C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/Export/Static"
NAMES="__NAMES__".split(",")
F="/Game/Brinewake/Props"
M=F+"/M_BW_Painted.M_BW_Painted"
NONE=("Grass","Flowers","Fern","Bush","Hedge","Vines","Creeper","Reeds","Seaweed","Kelp","Coral","Mushrooms","Shells","Pebbles","BigLeaf","Agave","Banana","Bamboo","Frond","Bunting","Lantern_Hanging","RopeCoil","Skull","Bone_Pile","Bottles","Gold","SM_BW_Sail","Skeleton","Sword_Stuck","Basket","Driftwood")
SIMPLE=("SM_BW_Barrel","SM_BW_Crate")
def call(n,a): return execute_tool(n,json.dumps(a))
def run():
    out={}
    for n in NAMES:
        try:
            if call(AS+"exists",{"path":F+"/"+n})["returnValue"]: call(AS+"delete",{"path":F+"/"+n})
            call(SM+"import_file",{"folder_path":F,"asset_name":n,"source_file":SRC+"/"+n+".fbx","import_materials":False,"import_textures":False,"combine_meshes":True})
            mesh={"refPath":F+"/"+n+"."+n}
            for s in call(SM+"get_material_slots",{"mesh":mesh})["returnValue"]:
                call(SM+"set_material",{"mesh":mesh,"slot_name":s,"material":{"refPath":M}})
            mode="complex"
            if n in SIMPLE: mode="simple"
            elif any(k in n for k in NONE): mode="none"
            if mode=="none": call(SM+"remove_collisions",{"mesh":mesh})
            elif mode=="complex":
                call(SM+"remove_collisions",{"mesh":mesh})
                call(OT+"set_properties",{"instance":{"refPath":F+"/"+n+"."+n+":BodySetup_0"},"values":json.dumps({"collisionTraceFlag":"CTF_UseComplexAsSimple"})})
            b=call(SM+"get_bounds",{"mesh":mesh})["returnValue"]
            out[n]={"t":call(SM+"get_triangle_count",{"mesh":mesh,"lod_index":0})["returnValue"],"b":b,"c":mode}
            call(AS+"save_assets",{"asset_paths":[F+"/"+n]})
        except Exception as e:
            out[n]="ERR "+str(e)[:300]
    return out
