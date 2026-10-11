"""shot.py <out name> <azimuth> <elevation> <distance factor> <focus 0..1> <object> [object ...]
Renders the objects in the user's Blender and writes <out name>.png plus a shrunk -sm copy for viewing."""
import json
import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, sys.argv[1] + ".png").replace("\\", "/")
code = open(os.path.join(here, "bl_shot.py"), encoding="utf-8").read()
code = code.replace("__NAMES__", json.dumps(sys.argv[6:])).replace("__OUT__", out)
code = code.replace("__VIEW__", "(%s, %s, %s, %s)" % tuple(sys.argv[2:6]))
open(os.path.join(here, "_shot.py"), "w", encoding="utf-8").write(code)
print(subprocess.run([sys.executable, os.path.join(here, "bl.py"), os.path.join(here, "_shot.py"), "300"], capture_output=True, text=True).stdout[-160:])
subprocess.run(["node", "C:/Users/User/.claude/plugins/cache/ww-w-ai/super-token-saver/3.7.5/scripts/shrink-img.js", out, "--maxdim", "1150"], capture_output=True)
