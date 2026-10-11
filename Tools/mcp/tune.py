"""tune.py '{"Param":[r,g,b,a] | number, ...}' -> sets overrides on MI_BW_Ocean"""
import json,subprocess,sys
MI="editor_toolset.toolsets.material_instance.MaterialInstanceTools"
inst={"refPath":"/Game/Brinewake/Ocean/MI_BW_Ocean.MI_BW_Ocean"}
for k,v in json.loads(sys.argv[1]).items():
    if isinstance(v,list): t,a="set_vector_parameter",{"instance":inst,"name":k,"value":{"r":v[0],"g":v[1],"b":v[2],"a":v[3]}}
    else: t,a="set_scalar_parameter",{"instance":inst,"name":k,"value":v}
    json.dump(a,open("_t.json","w"))
    o=subprocess.run([sys.executable,"ue.py","call",MI,t,"@_t.json"],capture_output=True,text=True,encoding="utf-8").stdout.strip()
    if "true" not in o and "null" not in o: print(k,o[:200])
