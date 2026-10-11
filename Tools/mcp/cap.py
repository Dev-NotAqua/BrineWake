"""cap.py x y z pitch yaw [name] -> captures the level viewport from a pose, saves a shrunk png"""
import json,subprocess,sys,os,base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
x,y,z,p,yw=[float(v) for v in sys.argv[1:6]]
name=sys.argv[6] if len(sys.argv)>6 else "cap"
args={"captureTransform":{"location":{"x":x,"y":y,"z":z},"rotation":{"pitch":p,"yaw":yw,"roll":0},"scale":{"x":1,"y":1,"z":1}},
"annotations":{"gridSpacing":0,"gridExtent":0,"gridHeight":0,"maxLabelDistance":0,"classFilter":{"refPath":"/Script/Engine.Actor"},"maxLabels":0},"bShowUI":False}
out=subprocess.run([sys.executable,"ue.py","raw","call_tool",json.dumps({"toolset_name":"EditorToolset.EditorAppToolset","tool_name":"CaptureViewport","arguments":args})],capture_output=True,text=True,encoding="utf-8").stdout
try:
    d=json.loads(out)["returnValue"]["image"]["data"]
    open(name+".png","wb").write(base64.b64decode(d))
    subprocess.run(["node","C:/Users/User/.claude/plugins/cache/ww-w-ai/super-token-saver/3.7.5/scripts/shrink-img.js",name+".png","--maxdim","1100"],capture_output=True)
    print("saved",name+"-sm.png")
except Exception as e:
    print("FAIL",e,out[:500])
