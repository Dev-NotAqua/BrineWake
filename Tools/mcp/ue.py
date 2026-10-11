"""Tiny client for the Unreal editor MCP server (streamable HTTP, 127.0.0.1:8000/mcp).

usage:
  ue.py list                          -> list_toolsets
  ue.py desc <toolset>                -> describe_toolset
  ue.py call <toolset|-> <tool> <json-args | @file.json>
  ue.py raw <mcp-tool> <json-args | @file.json>
"""
import json
import os
import sys
import urllib.request

URL = "http://127.0.0.1:8000/mcp"
HERE = os.path.dirname(os.path.abspath(__file__))
SID_FILE = os.path.join(HERE, "ue.sid")


def post(body, sid=None, timeout=600):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }
    if sid:
        headers["Mcp-Session-Id"] = sid
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
        return r.headers.get("Mcp-Session-Id"), raw


def parse(raw):
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("{"):
        return json.loads(raw)
    last = None
    for line in raw.splitlines():
        if line.startswith("data:"):
            last = json.loads(line[5:].strip())
    return last


def session():
    if os.path.exists(SID_FILE):
        return open(SID_FILE).read().strip()
    sid, _ = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "claude-code-http", "version": "1.0"}}})
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    open(SID_FILE, "w").write(sid)
    return sid


def tool(name, args):
    body = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": name, "arguments": args}}
    try:
        _, raw = post(body, session())
    except Exception:
        if os.path.exists(SID_FILE):
            os.remove(SID_FILE)
        _, raw = post(body, session())
    return parse(raw)


def load(arg):
    if arg.startswith("@"):
        return json.load(open(arg[1:], encoding="utf-8"))
    return json.loads(arg)


def show(res):
    if res is None:
        print("<empty>")
        return
    if "error" in res:
        print("ERROR", json.dumps(res["error"])[:4000])
        return
    r = res.get("result", {})
    if r.get("isError"):
        print("TOOL ERROR")
    for c in r.get("content", []):
        if c.get("type") == "text":
            print(c["text"])
        elif c.get("type") == "image":
            import base64
            n = 0
            while os.path.exists(os.path.join(HERE, "shot%d.png" % n)):
                n += 1
            p = os.path.join(HERE, "shot%d.png" % n)
            open(p, "wb").write(base64.b64decode(c["data"]))
            print("<image saved %s>" % p)
        else:
            print(json.dumps(c)[:2000])
    if "structuredContent" in r and not r.get("content"):
        print(json.dumps(r["structuredContent"], indent=1))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if a[0] == "list":
        show(tool("list_toolsets", {}))
    elif a[0] == "desc":
        show(tool("describe_toolset", {"toolset_name": a[1]}))
    elif a[0] == "call":
        args = {"tool_name": a[2], "arguments": load(a[3]) if len(a) > 3 else {}}
        if a[1] != "-":
            args["toolset_name"] = a[1]
        show(tool("call_tool", args))
    elif a[0] == "raw":
        show(tool(a[1], load(a[2]) if len(a) > 2 else {}))


main()
