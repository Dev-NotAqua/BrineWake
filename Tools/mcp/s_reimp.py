import json
OT="editor_toolset.toolsets.object.ObjectTools."
AS="editor_toolset.toolsets.asset.AssetTools."
SM="editor_toolset.toolsets.static_mesh.StaticMeshTools."
SRC="C:/Users/User/AppData/Local/Temp/claude/C--Users-User/809492bd-1b32-40ed-a614-4d20e1db1ed9/scratchpad/kit"
NAMES="__NAMES__".split(",")
HULLS=__HULLS__
F="/Game/Brinewake/Props"
M=F+"/M_BW_Painted.M_BW_Painted"
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
            if HULLS:
                call(SM+"remove_collisions",{"mesh":mesh})
                call(SM+"generate_convex_collisions",{"mesh":mesh,"hull_count":HULLS,"max_hull_verts":16,"hull_precision":100000})
            out[n]={"tris":call(SM+"get_triangle_count",{"mesh":mesh,"lod_index":0})["returnValue"],"b":call(SM+"get_bounds",{"mesh":mesh})["returnValue"]}
            call(AS+"save_assets",{"asset_paths":[F+"/"+n]})
        except Exception as e:
            out[n]=str(e)[:400]
    for bp,n in (("BP_BW_FloatBarrel","SM_BW_Barrel"),("BP_BW_FloatCrate","SM_BW_Crate")):
        if n in NAMES:
            c={"refPath":"/Game/Brinewake/Physics/%s.Default__%s_C:StaticMeshComponent0"%(bp,bp)}
            try:
                call(OT+"set_properties",{"instance":c,"values":json.dumps({"staticMesh":{"refPath":F+"/"+n+"."+n}})})
                out[bp]=call(OT+"get_properties",{"instance":c,"properties":["staticMesh"]})["returnValue"]
                call(AS+"save_assets",{"asset_paths":["/Game/Brinewake/Physics/"+bp]})
            except Exception as e: out[bp]=str(e)[:300]
    return out
