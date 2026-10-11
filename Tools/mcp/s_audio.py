import json
ST="editor_toolset.toolsets.scene.SceneTools."
OT="editor_toolset.toolsets.object.ObjectTools."
AT="editor_toolset.toolsets.actor.ActorTools."
AS="editor_toolset.toolsets.asset.AssetTools."
A="/Game/Brinewake/Audio/"
OX,OY=23000.0,31000.0
DATA=json.loads(r'''__DATA__''')
LOOPS=["A_BW_Ocean_Loop","A_BW_Shore_Loop","A_BW_Wind_Loop","A_BW_Fire_Loop","A_BW_Jungle_Loop","A_BW_Ship_Creak_Loop","A_BW_Underwater_Loop","A_BW_Rain_Loop","M_BW_Theme","M_BW_Tavern","M_BW_Calm","M_BW_Battle"]
def call(n,a): return execute_tool(n,json.dumps(a))
def setp(inst,vals): return call(OT+"set_properties",{"instance":inst,"values":json.dumps(vals)})
def snd(n): return {"refPath":A+n+"."+n}
def run():
    out={"loops":0,"placed":0,"err":[]}
    def err(t,e):
        if len(out["err"])<10: out["err"].append(t+" "+str(e)[:200])
    have=[(a.get("packageName","") if isinstance(a,dict) else str(a)).split("/")[-1] for a in call(AS+"find_assets",{"folder_path":"/Game/Brinewake/Audio","name":"","asset_type":"","recursive":False,"tags":{}})["returnValue"]]
    out["have"]=len(have)
    out["missing"]=[n for n in DATA["need"] if n not in have]
    if "__MODE__"=="check": return out
    for n in LOOPS:
        if n in have:
            try:
                setp(snd(n),{"bLooping":True}); call(AS+"save_assets",{"asset_paths":[A+n]}); out["loops"]+=1
            except Exception as e: err(n,e)
    if "Audio" in call(ST+"get_folders",{})["returnValue"]:
        for a in call(ST+"get_actors_in_folder",{"folder_path":"Audio","recursive":True})["returnValue"]:
            call(ST+"remove_from_scene",{"actor":a})
    try:
        for a in call(ST+"get_actors_in_folder",{"folder_path":"Ocean","recursive":False})["returnValue"]:
            if "AmbientSound" in a["refPath"]: call(ST+"remove_from_scene",{"actor":a})
    except Exception as e: err("old",e)
    for i,s in enumerate(DATA["sounds"]):
        try:
            a=call(ST+"add_to_scene_from_class",{"actor_type":{"refPath":"/Script/Engine.AmbientSound"},"name":"BW_Snd_%s_%02d"%(s["tag"],i),
                "xform":{"location":{"x":OX+s["x"]*100.0,"y":OY-s["y"]*100.0,"z":s["z"]*100.0},"rotation":{"pitch":0,"yaw":0,"roll":0},"scale":{"x":1,"y":1,"z":1}}})["returnValue"]
            call(ST+"set_actor_folder",{"actor":a,"folder_path":"Audio"})
            setp(a,{"bIsSpatiallyLoaded":False})
            c={"refPath":a["refPath"]+".AudioComponent0"}
            vals={"sound":snd(s["sound"]),"volumeMultiplier":s["vol"],"bAutoActivate":True}
            if s["radius"]<=0:
                vals["bAllowSpatialization"]=False
                vals["bIsUISound"]=False
            else:
                vals["bAllowSpatialization"]=True
                vals["bOverrideAttenuation"]=True
                vals["attenuationOverrides"]={"bAttenuate":True,"bSpatialize":True,"attenuationShape":"Sphere","attenuationShapeExtents":{"x":s["radius"]*0.25,"y":0,"z":0},"falloffDistance":s["radius"]}
            setp(c,vals)
            out["placed"]+=1
        except Exception as e: err(s["tag"],e)
    return out
