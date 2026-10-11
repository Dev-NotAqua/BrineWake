"""Run Python inside the open Unreal editor through the BWTools MCP toolset (full `unreal` module).

usage:
  py.py <script.py>        -> run a script file
  py.py -c "<code>"        -> run a snippet
Scripts share one globals dict in the editor; print() output comes back here.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLSET = "bw_tools.BWTools"


def main():
    a = sys.argv[1:]
    if a[0] == "-c":
        tool, args = "run_python", {"code": a[1]}
    else:
        tool, args = "run_file", {"path": os.path.abspath(a[0])}
    arg_file = os.path.join(HERE, "_py_args.json")
    with open(arg_file, "w", encoding="utf-8") as f:
        json.dump(args, f)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = subprocess.run([sys.executable, os.path.join(HERE, "ue.py"), "call", TOOLSET, tool, "@" + arg_file],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", env=env).stdout
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        print(json.loads(out)["returnValue"], end="")
    except (ValueError, KeyError, TypeError):
        print(out, end="")


main()
