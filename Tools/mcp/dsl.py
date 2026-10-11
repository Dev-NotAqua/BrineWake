"""dsl.py <blueprint package path> <dsl file> [graph]  -> writes the graph from DSL, compiles, saves, prints the result"""
import json
import subprocess
import sys

pkg, path = sys.argv[1], sys.argv[2]
graph = sys.argv[3] if len(sys.argv) > 3 else "EventGraph"
name = pkg.rsplit("/", 1)[1]
script = '''import json
BT="editor_toolset.toolsets.blueprint.BlueprintTools."
AS="editor_toolset.toolsets.asset.AssetTools."
def call(n,a): return execute_tool(n,json.dumps(a))
def run():
    out={}
    bp={"refPath":%(obj)s}
    g={"refPath":%(g)s}
    out["write"]=call(BT+"write_graph_dsl",{"graph":g,"code":%(code)s})
    out["compile"]=call(BT+"compile_blueprint",{"blueprint":bp,"warnings_as_errors":False})
    call(AS+"save_assets",{"asset_paths":[%(pkg)s]})
    return out
''' % {"obj": json.dumps(pkg + "." + name), "g": json.dumps(pkg + "." + name + ":" + graph),
       "code": json.dumps(open(path, encoding="utf-8").read()), "pkg": json.dumps(pkg)}
json.dump({"script": script}, open("_args.json", "w", encoding="utf-8"))
out = subprocess.run([sys.executable, "ue.py", "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset",
                      "execute_tool_script", "@_args.json"], capture_output=True, text=True, encoding="utf-8").stdout
print(out[:3000])
