"""place_isle.py  -> runs s_isle.py in the editor with kit/SM_BW_Isle_A.json embedded (too long for a command line)."""
import json
import subprocess
import sys

src = open("s_isle.py", encoding="utf-8").read().replace("__DATA__", json.dumps(json.load(open("kit/SM_BW_Isle_A.json"))))
json.dump({"script": src}, open("_args.json", "w", encoding="utf-8"))
out = subprocess.run([sys.executable, "ue.py", "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset",
                      "execute_tool_script", "@_args.json"], capture_output=True, text=True, encoding="utf-8").stdout
open("o_isle.txt", "w", encoding="utf-8").write(out)
try:
    o = json.loads(json.loads(out)["returnValue"])
    print("placed", o["n"], "errors", o["err"][:5])
except Exception:
    print(out[:500])
