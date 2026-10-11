"""place2.py <clear|props|sea|npcs|lights> [face offset]  -> runs s_isle2.py in the editor with kit/Gullrest_v2.json, in batches."""
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(here, "kit", "Gullrest_v2.json")))
tpl = open(os.path.join(here, "s_isle2.py"), encoding="utf-8").read()
stage = sys.argv[1]
face = sys.argv[2] if len(sys.argv) > 2 else "-90.0"
key = {"props": "props", "sea": "sea"}.get(stage)
items = data[key] if key else [None]
step = 120 if key else 1
t0, total, errs = time.time(), 0, []
for lo in range(0, len(items), step):
    part = {"start": data["start"], "npcs": data["npcs"], "fx": data["fx"]}
    if key:
        part = {key: items[lo:lo + step]}
    src = tpl.replace("__STAGE__", stage).replace("__BASE__", str(lo)).replace("__FACE__", face).replace("__DATA__", json.dumps(part))
    json.dump({"script": src}, open(os.path.join(here, "_args.json"), "w", encoding="utf-8"))
    out = subprocess.run([sys.executable, os.path.join(here, "ue.py"), "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset", "execute_tool_script", "@" + os.path.join(here, "_args.json")],
                         capture_output=True, text=True, encoding="utf-8").stdout
    try:
        r = json.loads(out)["returnValue"]
        r = json.loads(r) if isinstance(r, str) else r
        total += r.get("n", 0)
        errs += r.get("err", [])
        print(stage, lo, "placed", total, "removed", r.get("removed"), "%.0fs" % (time.time() - t0), "err", r.get("err", [])[:2], flush=True)
    except Exception as e:
        print("FAIL", lo, str(e), out[:600], flush=True)
print("DONE", stage, total, "errors", len(errs))
