import json
ST="editor_toolset.toolsets.scene.SceneTools."
OT="editor_toolset.toolsets.object.ObjectTools."
AT="editor_toolset.toolsets.actor.ActorTools."
V="/Game/Brinewake/VFX/"
C="/Game/Brinewake/Characters/"
OX,OY=23000.0,31000.0
DATA=json.loads(r'''__DATA__''')
def call(n,a): return execute_tool(n,json.dumps(a))
def xf(x,y,z,yaw=0.0,s=1.0): return {"location":{"x":OX+x*100.0,"y":OY-y*100.0,"z":z*100.0},"rotation":{"pitch":0,"yaw":yaw,"roll":0},"scale":{"x":s,"y":s,"z":s}}
def setp(inst,vals): return call(OT+"set_properties",{"instance":inst,"values":json.dumps(vals)})
def run():
    out={"removed":0,"spray":0,"err":[]}
    for a in call(ST+"get_actors_in_folder",{"folder_path":"Ocean","recursive":False})["returnValue"]:
        cls=a["refPath"].split(".")[-1].split("_UAID")[0]
        if cls in ("StaticMeshActor","NiagaraActor","SkeletalMeshActor"):
            try:
                call(ST+"remove_from_scene",{"actor":a}); out["removed"]+=1
            except Exception as e: out["err"].append(str(e)[:150])
    for i,p in enumerate(DATA["spray"]):
        try:
            a=call(ST+"add_to_scene_from_asset",{"asset_path":V+p["fx"],"name":"BW_%s_%02d"%(p["fx"][6:],i),"xform":xf(p["x"],p["y"],p["z"],0.0,p["s"])})["returnValue"]
            call(ST+"set_actor_folder",{"actor":a,"folder_path":"Ocean/Spray"})
            setp(a,{"bIsSpatiallyLoaded":False})
            out["spray"]+=1
        except Exception as e:
            if len(out["err"])<8: out["err"].append(str(e)[:200])
    return out
