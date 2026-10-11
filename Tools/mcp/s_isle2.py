import json
import math
ST="editor_toolset.toolsets.scene.SceneTools."
OT="editor_toolset.toolsets.object.ObjectTools."
AT="editor_toolset.toolsets.actor.ActorTools."
AS="editor_toolset.toolsets.asset.AssetTools."
F="/Game/Brinewake/Props/"
C="/Game/Brinewake/Characters/"
OX,OY=23000.0,31000.0
STAGE="__STAGE__"
BASE=__BASE__
ALWAYS=("Ships","SetPieces","Outpost")
DATA=json.loads(r'''__DATA__''')
def call(n,a): return execute_tool(n,json.dumps(a))
def xf(x,y,z,yaw=0.0,s=1.0,pitch=0.0,roll=0.0,sx=None,sy=None,sz=None):
    return {"location":{"x":OX+x*100.0,"y":OY-y*100.0,"z":z*100.0},"rotation":{"pitch":pitch,"yaw":yaw,"roll":roll},"scale":{"x":sx or s,"y":sy or s,"z":sz or s}}
def setp(inst,vals): return call(OT+"set_properties",{"instance":inst,"values":json.dumps(vals)})
def comp(actor,name): return {"refPath":actor["refPath"]+"."+name}
def run():
    out={"n":0,"err":[]}
    def err(tag,e):
        if len(out["err"])<12: out["err"].append(tag+" "+str(e)[:220])
    if STAGE=="clear":
        n=0
        for folder in ("Island",):
            try:
                for a in call(ST+"get_actors_in_folder",{"folder_path":folder,"recursive":True})["returnValue"]:
                    call(ST+"remove_from_scene",{"actor":a}); n+=1
            except Exception as e: err("clear",e)
        out["removed"]=n
        for n_ in ("SM_BW_Isle_A","SM_BW_Isle_A_Detail","SM_BW_Isle_A_Falls"):
            try:
                a=call(ST+"add_to_scene_from_asset",{"asset_path":F+n_,"name":"BW_"+n_[6:],"xform":xf(0,0,0)})["returnValue"]
                call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island"})
                setp(a,{"bIsSpatiallyLoaded":False})
                if n_=="SM_BW_Isle_A":
                    call(AT+"add_component",{"owner":a,"component_type":{"refPath":"/Script/Water.WaterTerrainComponent"},"name":"WaterTerrain"})
                else:
                    setp(comp(a,"StaticMeshComponent0"),{"castShadow":False})
            except Exception as e: err(n_,e)
        s=DATA["start"]
        try:
            ps=call(ST+"add_to_scene_from_class",{"actor_type":{"refPath":"/Script/Engine.PlayerStart"},"name":"BW_PlayerStart","xform":xf(s["x"],s["y"],s["z"]+1.1,-s["yaw"])})["returnValue"]
            call(ST+"set_actor_folder",{"actor":ps,"folder_path":"Island"})
        except Exception as e: err("start",e)
    elif STAGE=="props":
        for i,p in enumerate(DATA["props"]):
            try:
                s=p.get("scale",1.0)
                a=call(ST+"add_to_scene_from_asset",{"asset_path":F+p["mesh"],"name":"BW_%s_%04d"%(p["mesh"][6:],BASE+i),
                    "xform":xf(p["x"],p["y"],p["z"],-p["yaw"],s,p.get("pitch",0),p.get("roll",0),p.get("sx"),p.get("sy"),p.get("sz"))})["returnValue"]
                folder=p.get("folder","Dressing")
                call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/"+folder})
                if folder in ALWAYS: setp(a,{"bIsSpatiallyLoaded":False})
                if folder in ("Plants","Reef"): setp(comp(a,"StaticMeshComponent0"),{"castShadow":p["mesh"].startswith(("SM_BW_Palm","SM_BW_Tree","SM_BW_Mangrove","SM_BW_Bamboo","SM_BW_Banana"))})
                out["n"]+=1
            except Exception as e: err(p["mesh"],e)
    elif STAGE=="sea":
        for i,p in enumerate(DATA["sea"]):
            try:
                a=call(ST+"add_to_scene_from_asset",{"asset_path":F+p["mesh"],"name":"BW_Sea_%s_%03d"%(p["mesh"][6:],BASE+i),"xform":xf(p["x"],p["y"],p["z"],-p["yaw"],p["scale"])})["returnValue"]
                call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/SeaRocks"})
                setp(a,{"bIsSpatiallyLoaded":False})
                call(AT+"add_component",{"owner":a,"component_type":{"refPath":"/Script/Water.WaterTerrainComponent"},"name":"WaterTerrain"})
                out["n"]+=1
            except Exception as e: err(p["mesh"],e)
    elif STAGE=="npcs":
        for i,p in enumerate(DATA["npcs"]):
            try:
                dx,dy=(p["face"][0]-p["x"]),-(p["face"][1]-p["y"])
                yaw=math.degrees(math.atan2(dy,dx))+__FACE__
                a=call(ST+"add_to_scene_from_asset",{"asset_path":C+p["mesh"],"name":"BW_"+p["mesh"][6:],"xform":xf(p["x"],p["y"],p["z"],yaw)})["returnValue"]
                call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/Crew"})
                setp(a,{"bIsSpatiallyLoaded":False})
                anim={"refPath":C+"Anims/A_BW_%s.A_BW_%s"%(p["anim"],p["anim"])}
                setp(comp(a,"SkeletalMeshComponent0"),{"animationMode":"AnimationSingleNode","animationData":{"animToPlay":anim,"bSavedLooping":True,"bSavedPlaying":True,"savedPosition":0.0,"savedPlayRate":1.0}})
                out["n"]+=1
            except Exception as e: err(p["mesh"],e)
    elif STAGE=="lights":
        for i,p in enumerate(DATA["fx"]):
            try:
                fire=p["kind"]=="fire"
                a=call(ST+"add_to_scene_from_class",{"actor_type":{"refPath":"/Script/Engine.PointLight"},"name":"BW_%s_%02d"%("FireLight" if fire else "LampLight",i),"xform":xf(p["x"],p["y"],p["z"]+(0.25 if fire else 0.0))})["returnValue"]
                call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/Lights"})
                setp(comp(a,"LightComponent0"),{"intensityUnits":"Candelas","intensity":(220.0*p.get("size",1.0) if fire else 70.0),"lightColor":{"r":255,"g":(150 if fire else 176),"b":(60 if fire else 96),"a":255},
                    "attenuationRadius":(1400.0 if fire else 1000.0),"castShadows":False,"sourceRadius":12.0})
                out["n"]+=1
            except Exception as e: err("light",e)
    return out
