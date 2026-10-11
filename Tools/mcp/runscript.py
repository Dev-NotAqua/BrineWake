import json,subprocess,sys
src=open(sys.argv[1],encoding="utf-8").read()
for kv in sys.argv[3:]:
    k,v=kv.split("=",1); src=src.replace(k,v)
json.dump({"script":src},open("_args.json","w",encoding="utf-8"))
out=subprocess.run([sys.executable,"ue.py","call","editor_toolset.toolsets.programmatic.ProgrammaticToolset","execute_tool_script","@_args.json"],capture_output=True,text=True,encoding="utf-8").stdout
open(sys.argv[2],"w",encoding="utf-8").write(out)
print(len(out), out[:300])
