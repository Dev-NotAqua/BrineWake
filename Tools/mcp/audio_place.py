"""audio_place.py [check] -> places looping ambience and music around Gullrest from kit/Gullrest_v2.json."""
import json, math, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(here, "kit", "Gullrest_v2.json")))
need = sorted(f[:-4] for f in os.listdir(os.path.join(here, "..", "..", "Art", "Audio")) if f.endswith(".wav"))
S = []
def add(tag, sound, x, y, z, vol, radius): S.append({"tag": tag, "sound": sound, "x": x, "y": y, "z": z, "vol": vol, "radius": radius})
add("Ocean", "A_BW_Ocean_Loop", 0, 0, 30, 0.55, 0)
add("Wind", "A_BW_Wind_Loop", 0, 0, 40, 0.22, 0)
add("Music", "M_BW_Theme", 0, 0, 50, 0.38, 0)
shore = [s for s in d["sea"] if s["scale"] <= 2.0 and math.hypot(s["x"], s["y"]) < 135][::2]
for s in shore[:9]:
    add("Shore", "A_BW_Shore_Loop", s["x"], s["y"], 1.0, 0.9, 5500)
trees = [p for p in d["props"] if p["mesh"].startswith("SM_BW_Tree_Jungle")][::4]
for p in trees[:4]:
    add("Jungle", "A_BW_Jungle_Loop", p["x"], p["y"], p["z"] + 3, 0.7, 4500)
for f in d["fx"]:
    if f["kind"] == "fire":
        add("Fire", "A_BW_Fire_Loop", f["x"], f["y"], f["z"], 0.9 * f.get("size", 1.0), 1500)
for p in d["props"]:
    if p.get("folder") == "Ships" and p["mesh"] != "SM_BW_Rowboat":
        add("Creak", "A_BW_Ship_Creak_Loop", p["x"], p["y"], 4.0, 0.8, 4000)
    if p["mesh"] == "SM_BW_Alehouse":
        add("Tavern", "M_BW_Tavern", p["x"], p["y"], p["z"] + 2.0, 0.75, 3000)
    if p["mesh"] in ("SM_BW_Wreck_Hull", "SM_BW_Leviathan_Bones"):
        add("Creak", "A_BW_Ship_Creak_Loop", p["x"], p["y"], 2.0, 0.35, 2200)
mode = sys.argv[1] if len(sys.argv) > 1 else "place"
src = open(os.path.join(here, "s_audio.py"), encoding="utf-8").read().replace("__MODE__", mode).replace("__DATA__", json.dumps({"need": need, "sounds": S}))
json.dump({"script": src}, open(os.path.join(here, "_args.json"), "w", encoding="utf-8"))
out = subprocess.run([sys.executable, os.path.join(here, "ue.py"), "call", "editor_toolset.toolsets.programmatic.ProgrammaticToolset", "execute_tool_script", "@" + os.path.join(here, "_args.json")],
                     capture_output=True, text=True, encoding="utf-8").stdout
print(len(S), "sounds;", out[:1500])
