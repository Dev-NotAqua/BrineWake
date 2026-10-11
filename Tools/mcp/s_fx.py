import json
ST="editor_toolset.toolsets.scene.SceneTools."
OT="editor_toolset.toolsets.object.ObjectTools."
V="/Game/Brinewake/VFX/"
OX,OY=23000.0,31000.0
DATA=json.loads(r'''__DATA__''')
def call(n,a): return execute_tool(n,json.dumps(a))
def run():
    out={"n":0,"err":[]}
    if "Island/VFX" in call(ST+"get_folders",{})["returnValue"]:
        for a in call(ST+"get_actors_in_folder",{"folder_path":"Island/VFX","recursive":True})["returnValue"]:
            call(ST+"remove_from_scene",{"actor":a})
    for i,p in enumerate(DATA):
        try:
            a=call(ST+"add_to_scene_from_asset",{"asset_path":V+p["fx"],"name":"BW_%s_%02d"%(p["fx"][6:],i),
                "xform":{"location":{"x":OX+p["x"]*100.0,"y":OY-p["y"]*100.0,"z":p["z"]*100.0},"rotation":{"pitch":0,"yaw":0,"roll":0},"scale":{"x":p["s"],"y":p["s"],"z":p["s"]}}})["returnValue"]
            call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/VFX"})
            call(OT+"set_properties",{"instance":a,"values":json.dumps({"bIsSpatiallyLoaded":False})})
            out["n"]+=1
        except Exception as e:
            if len(out["err"])<6: out["err"].append(str(e)[:200])
    return out
