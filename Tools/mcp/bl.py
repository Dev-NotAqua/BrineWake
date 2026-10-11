"""bl.py <file.py> [timeout]  |  bl.py -c "code"
Runs Python inside the user's open Blender through the Blender MCP bridge (127.0.0.1:9876).
Protocol: NUL-terminated JSON {"type": "execute", "code": ..., "strict_json": false}; the code must set `result` (a dict).
"""
import json
import socket
import sys

code = sys.argv[2] if sys.argv[1] == "-c" else open(sys.argv[1], encoding="utf-8").read()
timeout = float(sys.argv[2]) if sys.argv[1] != "-c" and len(sys.argv) > 2 else 300.0
if "result" not in code:
    code += "\nresult = {'ok': True}\n"
if len(code) > 3000:
    # The bridge reads 4 KB per timer tick and drops a client that needs more than ~40 ticks, so a long script
    # goes to disk and only a one-line loader crosses the socket.
    import os
    payload = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bl_payload_%d.py" % os.getpid())
    open(payload, "w", encoding="utf-8").write(code)
    code = "exec(compile(open(%r, encoding='utf-8').read(), %r, 'exec'))\nimport os\nos.remove(%r)\n" % (payload, payload, payload)
s = socket.socket()
s.settimeout(timeout)
s.connect(("127.0.0.1", 9876))
s.sendall((json.dumps({"type": "execute", "code": code, "strict_json": False}) + "\0").encode("utf-8"))
buf = b""
try:
    while b"\0" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
except socket.timeout:
    print("TIMEOUT")
s.close()
text = buf.split(b"\0")[0].decode("utf-8", "replace")
try:
    r = json.loads(text)
    print(r.get("status"), json.dumps(r.get("result"))[:1500] if r.get("result") is not None else "")
    for k in ("message", "stdout", "stderr"):
        if r.get(k):
            print(k.upper() + ":", str(r[k])[-2500:])
except ValueError:
    print(text[:2000])
