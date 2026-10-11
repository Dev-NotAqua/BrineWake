import json
OT="editor_toolset.toolsets.object.ObjectTools."
AS="editor_toolset.toolsets.asset.AssetTools."
MT="editor_toolset.toolsets.material.MaterialTools."
P="/Game/Brinewake/Props/M_BW_Painted"
def call(n,a): return execute_tool(n,json.dumps(a))
def run():
    out={}
    mr={"refPath":P+".M_BW_Painted"}
    ex=call(MT+"get_expressions",{"material_or_function":mr})["returnValue"]
    out["expressions"]=[e["refPath"].split(":")[-1] if isinstance(e,dict) else str(e) for e in ex]
    if "__MODE__"=="inspect":
        out["props"]=call(OT+"get_properties",{"instance":mr,"properties":["twoSided","blendMode","shadingModel"]})["returnValue"]
        for prop in ("MP_BaseColor","MP_EmissiveColor","MP_Roughness"):
            try: out[prop]=call(MT+"get_property_input",{"material":mr,"material_property":prop})["returnValue"]
            except Exception as e: out[prop]=str(e)[:120]
        return out
    call(OT+"set_properties",{"instance":mr,"values":json.dumps({"twoSided":True})})
    vc=None
    for e in ex:
        if isinstance(e,dict) and "VertexColor" in e["refPath"]: vc=e
    def add(cls,x,y,props=None):
        e=call(MT+"add_expression",{"material_or_function":mr,"expression_class":{"refPath":"/Script/Engine.MaterialExpression"+cls},"x":x,"y":y})["returnValue"]
        if props: call(OT+"set_properties",{"instance":e,"values":json.dumps(props)})
        return e
    def first_in(e): return call(MT+"get_expression_input_names",{"expression":e})["returnValue"][0]
    def link(a,o,b,i): call(MT+"connect_expressions",{"from_expression":a,"from_output_name":o,"to_expression":b,"to_input_name":i})
    if vc is None: vc=add("VertexColor",-1400,500)
    out["vc_outputs"]=call(MT+"get_expression_output_names",{"expression":vc})["returnValue"]
    rgb=out["vc_outputs"][0]
    mR=add("ComponentMask",-1150,450,{"r":True,"g":False,"b":False,"a":False}); link(vc,rgb,mR,first_in(mR))
    mB=add("ComponentMask",-1150,600,{"r":False,"g":False,"b":True,"a":False}); link(vc,rgb,mB,first_in(mB))
    hot=add("Subtract",-950,450,{"constB":0.88}); link(mR,"",hot,"A")
    hot2=add("Multiply",-800,450,{"constB":10.0}); link(hot,"",hot2,"A")
    hot3=add("Saturate",-650,450); link(hot2,"",hot3,first_in(hot3))
    warm=add("Subtract",-950,600); link(mR,"",warm,"A"); link(mB,"",warm,"B")
    warm1=add("Subtract",-800,600,{"constB":0.36}); link(warm,"",warm1,"A")
    warm2=add("Multiply",-650,600,{"constB":4.0}); link(warm1,"",warm2,"A")
    warm3=add("Saturate",-500,600); link(warm2,"",warm3,first_in(warm3))
    both=add("Multiply",-350,520); link(hot3,"",both,"A"); link(warm3,"",both,"B")
    glow=add("Multiply",-200,520); link(vc,rgb,glow,"A"); link(both,"",glow,"B")
    gain=add("Multiply",-50,520,{"constB":9.0}); link(glow,"",gain,"A")
    call(MT+"connect_to_output",{"expression":gain,"output_name":"","material_property":"MP_EmissiveColor"})
    out["recompile"]=str(call(MT+"recompile",{"material_or_function":mr}))[:200]
    call(AS+"save_assets",{"asset_paths":[P]})
    out["props"]=call(OT+"get_properties",{"instance":mr,"properties":["twoSided"]})["returnValue"]
    return out
