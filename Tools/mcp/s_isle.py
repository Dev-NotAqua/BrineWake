import json
ST="editor_toolset.toolsets.scene.SceneTools."
OT="editor_toolset.toolsets.object.ObjectTools."
AT="editor_toolset.toolsets.actor.ActorTools."
AS="editor_toolset.toolsets.asset.AssetTools."
MT="editor_toolset.toolsets.material.MaterialTools."
SM="editor_toolset.toolsets.static_mesh.StaticMeshTools."
F="/Game/Brinewake/Props/"
OX,OY=23000.0,31000.0
SOLID=["SM_BW_Isle_A","SM_BW_Hut_A","SM_BW_Hut_B","SM_BW_Tower","SM_BW_Dock","SM_BW_Alehouse","SM_BW_WardenHut","SM_BW_SalvageTent","SM_BW_Keelwright","SM_BW_MarketStall","SM_BW_Sloop","SM_BW_Brigantine","SM_BW_DockEnd","SM_BW_DockCorner","SM_BW_Rowboat"]
DATA=json.loads(r'''__DATA__''')
def call(n,a): return execute_tool(n,json.dumps(a))
def xf(x,y,z,yaw=0.0,s=1.0): return {"location":{"x":x,"y":y,"z":z},"rotation":{"pitch":0,"yaw":yaw,"roll":0},"scale":{"x":s,"y":s,"z":s}}
def waterfall_material():
    P="/Game/Brinewake/Ocean/M_BW_Waterfall"
    if call(AS+"exists",{"path":P})["returnValue"]: return
    call(MT+"create_material",{"folder_path":"/Game/Brinewake/Ocean","asset_name":"M_BW_Waterfall"})
    mr={"refPath":P+".M_BW_Waterfall"}
    def add(cls,x,y,props=None):
        e=call(MT+"add_expression",{"material_or_function":mr,"expression_class":{"refPath":"/Script/Engine.MaterialExpression"+cls},"x":x,"y":y})["returnValue"]
        if props: call(OT+"set_properties",{"instance":e,"values":json.dumps(props)})
        return e
    def link(a,o,b,i): call(MT+"connect_expressions",{"from_expression":a,"from_output_name":o,"to_expression":b,"to_input_name":i})
    call(OT+"set_properties",{"instance":mr,"values":json.dumps({"blendMode":"BLEND_Translucent","twoSided":True})})
    try: call(OT+"set_properties",{"instance":mr,"values":json.dumps({"shadingModel":"MSM_Unlit"})})
    except Exception: pass
    foam={"refPath":"/Water/Textures/Foam/T_WaterFlow_03_Foam_Tiled.T_WaterFlow_03_Foam_Tiled"}
    samples=[]
    for i,(sx,sy,sp) in enumerate(((1.0,0.35,-1.1),(1.7,0.6,-1.7))):
        uv=add("TextureCoordinate",-1000,i*300,{"uTiling":sx,"vTiling":sy})
        pan=add("Panner",-800,i*300,{"speedX":0.0,"speedY":sp})
        link(uv,"",pan,"Coordinate")
        ts=add("TextureSample",-600,i*300,{"texture":foam})
        link(pan,"",ts,call(MT+"get_expression_input_names",{"expression":ts})["returnValue"][0])
        samples.append(ts)
    mx=add("Add",-350,100); link(samples[0],"R",mx,"A"); link(samples[1],"R",mx,"B")
    col=add("LinearInterpolate",-150,0,{"constA":{"r":0.55,"g":0.85,"b":0.95,"a":1},"constB":{"r":1.6,"g":1.7,"b":1.7,"a":1}})
    link(mx,"",col,"Alpha")
    op=add("Multiply",-150,250,{"constB":0.55}); link(mx,"",op,"A")
    opa=add("Add",0,250,{"constB":0.35}); link(op,"",opa,"A")
    sat=add("Saturate",120,250); link(opa,"",sat,"")
    call(MT+"connect_to_output",{"expression":col,"output_name":"","material_property":"MP_EmissiveColor"})
    call(MT+"connect_to_output",{"expression":sat,"output_name":"","material_property":"MP_Opacity"})
    call(MT+"recompile",{"material_or_function":mr})
    call(AS+"save_assets",{"asset_paths":[P]})
def run():
    out={"n":0,"err":[]}
    try: waterfall_material()
    except Exception as e: out["err"].append("wf "+str(e)[:300])
    try:
        for a in call(ST+"get_actors_in_folder",{"folder_path":"Island","recursive":True})["returnValue"]:
            call(ST+"remove_from_scene",{"actor":a})
    except Exception: pass
    for n in SOLID:
        try:
            call(OT+"set_properties",{"instance":{"refPath":F+n+"."+n+":BodySetup_0"},"values":json.dumps({"collisionTraceFlag":"CTF_UseComplexAsSimple"})})
            call(AS+"save_assets",{"asset_paths":[F+n]})
        except Exception as e: out["err"].append(n+" "+str(e)[:150])
    for n in ("SM_BW_Isle_A_Detail","SM_BW_Isle_A_Falls"):
        call(SM+"remove_collisions",{"mesh":{"refPath":F+n+"."+n}})
    fm={"refPath":F+"SM_BW_Isle_A_Falls.SM_BW_Isle_A_Falls"}
    try:
        for s in call(SM+"get_material_slots",{"mesh":fm})["returnValue"]:
            call(SM+"set_material",{"mesh":fm,"slot_name":s,"material":{"refPath":"/Game/Brinewake/Ocean/M_BW_Waterfall.M_BW_Waterfall"}})
    except Exception as e: out["err"].append("falls mat "+str(e)[:200])
    call(AS+"save_assets",{"asset_paths":[F+"SM_BW_Isle_A_Detail",F+"SM_BW_Isle_A_Falls"]})
    for n in ("SM_BW_Isle_A","SM_BW_Isle_A_Detail","SM_BW_Isle_A_Falls"):
        a=call(ST+"add_to_scene_from_asset",{"asset_path":F+n,"name":"BW_"+n[6:],"xform":xf(OX,OY,0)})["returnValue"]
        call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island"})
        call(OT+"set_properties",{"instance":a,"values":json.dumps({"bIsSpatiallyLoaded":False})})
        if n=="SM_BW_Isle_A":
            out["isle"]=a
            try: call(AT+"add_component",{"owner":a,"component_type":{"refPath":"/Script/Water.WaterTerrainComponent"},"name":"WaterTerrain"})
            except Exception as e: out["err"].append(str(e)[:200])
        if n.endswith(("Detail","Falls")):
            try: call(OT+"set_properties",{"instance":{"refPath":a["refPath"]+".StaticMeshComponent0"},"values":json.dumps({"castShadow":False})})
            except Exception as e: out["err"].append(str(e)[:200])
    for i,p in enumerate(DATA["props"]):
        try:
            a=call(ST+"add_to_scene_from_asset",{"asset_path":F+p["mesh"],"name":"BW_%s_%03d"%(p["mesh"][6:],i),"xform":{"location":{"x":OX+p["x"]*100,"y":OY-p["y"]*100,"z":p["z"]*100},"rotation":{"pitch":p.get("pitch",0),"yaw":-p["yaw"],"roll":p.get("roll",0)},"scale":{"x":p.get("sx",p["scale"]),"y":p.get("sy",p["scale"]),"z":p.get("sz",p["scale"])}}})["returnValue"]
            call(ST+"set_actor_folder",{"actor":a,"folder_path":"Island/Outpost" if p["mesh"] in SOLID else ("Island/Rocks" if "Slab" in p["mesh"] else "Island/Dressing")})
            out["n"]+=1
        except Exception as e:
            out["err"].append(str(e)[:200])
    s=DATA["start"]
    try:
        ps=call(ST+"add_to_scene_from_class",{"actor_type":{"refPath":"/Script/Engine.PlayerStart"},"name":"BW_PlayerStart","xform":xf(OX+s["x"]*100,OY-s["y"]*100,s["z"]*100+110,-s["yaw"])})["returnValue"]
        call(ST+"set_actor_folder",{"actor":ps,"folder_path":"Island"})
        out["start"]=ps
    except Exception as e:
        out["err"].append(str(e)[:300])
    for folder in ("Dressing","Physics"):
        try:
            for a in call(ST+"get_actors_in_folder",{"folder_path":folder,"recursive":False})["returnValue"]:
                t=call(AT+"get_actor_transform",{"actor":a})["returnValue"]
                if t["location"]["x"]<34500:
                    t["location"]["x"]+=7000
                    call(AT+"set_actor_transform",{"actor":a,"xform":t,"worldspace":True})
        except Exception as e: out["err"].append(folder+" "+str(e)[:150])
    return out
