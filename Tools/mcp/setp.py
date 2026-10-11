import json,subprocess,sys
ref=sys.argv[1]; vals=sys.argv[2]
json.dump({"instance":{"refPath":ref},"values":vals},open("_set.json","w"))
print(subprocess.run([sys.executable,"ue.py","call","editor_toolset.toolsets.object.ObjectTools","set_properties","@_set.json"],capture_output=True,text=True,encoding="utf-8").stdout[:400].strip())
