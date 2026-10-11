"""runs.py <script.py> [KEY=VALUE ...] -> runs a tool script in the Unreal editor (placeholders replaced), prints the parsed result."""
import json, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
src = open(sys.argv[1], encoding="utf-8").read()
for kv in sys.argv[2:]:
    k, v = kv.split("=", 1)
    src = src.replace(k, open(v[1:], encoding="utf-8").read() if v.startswith("@") else v)
json.dump({"script": src}, open(os.path.join(here, "_args.json"), "w", encoding="utf-8"))
out = subprocess.run([sys.executable, os.path.join(here, "ue.py"), "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset", "execute_tool_script", "@" + os.path.join(here, "_args.json")],
                     capture_output=True, text=True, encoding="utf-8").stdout
try:
    r = json.loads(out)["returnValue"]
    r = json.loads(r) if isinstance(r, str) else r
    print(json.dumps(r, indent=1)[:int(os.environ.get("RUNS_MAX", "6000"))])
except Exception:
    print(out[:4000])
