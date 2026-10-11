"""ue_import.py [name fragment ...] -> imports Art/Export/Static/*.fbx into /Game/Brinewake/Props in batches."""
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "..", "Art", "Export", "Static")
names = sorted(f[:-4] for f in os.listdir(src) if f.endswith(".fbx"))
if len(sys.argv) > 2 and sys.argv[1] == "--from":
    names = names[int(sys.argv[2]):]
elif len(sys.argv) > 1:
    names = [n for n in names if any(k in n for k in sys.argv[1:])]
tpl = open(os.path.join(here, "s_import.py"), encoding="utf-8").read()
allout, t0 = {}, time.time()
for i in range(0, len(names), 12):
    batch = names[i:i + 12]
    json.dump({"script": tpl.replace("__NAMES__", ",".join(batch))}, open(os.path.join(here, "_args.json"), "w", encoding="utf-8"))
    out = subprocess.run([sys.executable, os.path.join(here, "ue.py"), "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset", "execute_tool_script", "@" + os.path.join(here, "_args.json")],
                         capture_output=True, text=True, encoding="utf-8").stdout
    try:
        r = json.loads(out)["returnValue"]
        r = json.loads(r) if isinstance(r, str) else r
        allout.update(r)
        bad = [k for k, v in r.items() if isinstance(v, str)]
        print("%3d/%d %5.0fs ok %d bad %s" % (i + len(batch), len(names), time.time() - t0, len(r) - len(bad), bad), flush=True)
    except Exception as e:
        print("BATCH FAIL", batch[0], str(e), out[:400], flush=True)
json.dump(allout, open(os.path.join(here, "o_import_%d.json" % int(time.time())), "w"), indent=0)
