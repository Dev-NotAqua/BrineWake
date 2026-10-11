import json,subprocess,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
ref=sys.argv[1]; flt=[s.lower() for s in sys.argv[2:]]
out=subprocess.run([sys.executable,"ue.py","call","editor_toolset.toolsets.object.ObjectTools","list_properties",json.dumps({"instance":{"refPath":ref}})],capture_output=True,text=True,encoding="utf-8").stdout
d=json.loads(json.loads(out)["returnValue"])
for k,v in d.items():
    if flt and not any(f in k.lower() for f in flt): continue
    print(k,":",v.get("title") or v.get("type"), "|", (v.get("description") or "").replace("\n"," ")[:70])
