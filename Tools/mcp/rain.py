"""Configures NS_BW_Rain: fast streaks falling through a sphere that the storm keeps on the player."""
import json
import subprocess
import sys

NS = "NiagaraToolsets.NiagaraToolset_System"
SYS = {"refPath": "/Game/Brinewake/Weather/NS_BW_Rain.NS_BW_Rain"}


def call(tool, args):
    json.dump(args, open("_n.json", "w"))
    out = subprocess.run([sys.executable, "ue.py", "call", NS, tool, "@_n.json"], capture_output=True, text=True, encoding="utf-8").stdout
    return out


def ref(script="", module="", inp=None, renderer=-1):
    return {"system": SYS, "emitterName": "Rain", "scriptName": script, "moduleName": module,
            "rendererIndex": renderer, "inputNameStack": inp or []}


def setin(script, module, name, struct, value):
    out = call("SetStackInputData", {"stackInputRef": ref(script, module, [name]),
                                     "inputData": {"struct": {"refPath": struct}, "value": value}})
    if "ERROR" in out or "rror" in out[:80]:
        print("FAIL", module, name, out[:300])


F, B, V3, COL = "/Script/Niagara.NiagaraFloat", "/Script/Niagara.NiagaraBool", "/Script/CoreUObject.Vector3f", "/Script/CoreUObject.LinearColor"
V2 = "/Script/CoreUObject.Vector2f"
ENUM = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum"


def enum(path, name):
    return {"enum": {"refPath": path}, "enumName": path.split(".")[-1] + "::" + name}


EU, PS, PU = "EmitterUpdateScript", "ParticleSpawnScript", "ParticleUpdateScript"
setin(EU, "SpawnRate", "SpawnRate", F, {"value": 2600})
setin(PS, "InitializeParticle", "Lifetime Min", F, {"value": 1.3})
setin(PS, "InitializeParticle", "Lifetime Max", F, {"value": 1.6})
setin(PS, "InitializeParticle", "Color", COL, {"r": 0.72, "g": 0.84, "b": 0.95, "a": 0.45})
setin(PS, "InitializeParticle", "Sprite Size Mode", ENUM, enum("/Niagara/Enums/ENiagara_SizeScaleMode.ENiagara_SizeScaleMode", "NewEnumerator4"))
setin(PS, "InitializeParticle", "Sprite Size", V2, {"x": 2.2, "y": 95.0})
setin(PS, "InitializeParticle", "Sprite Rotation Mode", ENUM, enum("/Niagara/Enums/ENiagara_SpriteRotationMode.ENiagara_SpriteRotationMode", "NewEnumerator0"))
setin(PS, "ShapeLocation", "Sphere Radius", F, {"value": 2600})
setin(PS, "AddVelocity", "Velocity Mode", ENUM, enum("/Niagara/Enums/Utility/ENiagara_VelocityMode.ENiagara_VelocityMode", "NewEnumerator0"))
setin(PS, "AddVelocity", "Velocity", V3, {"x": -520, "y": 180, "z": -2900})
setin(PU, "Drag", "Drag", F, {"value": 0.0})
setin(PU, "GravityForce", "Gravity", V3, {"x": 0, "y": 0, "z": -300})
print(call("SetModuleEnabled", {"moduleRef": ref(PU, "ScaleColor"), "bEnabled": False})[:120])
print(call("SetRendererData", {"renderer": ref(renderer=0), "rendererData": {"propertyValues": json.dumps(
    {"Alignment": "VelocityAligned", "FacingMode": "FaceCamera"})}})[:200])
print(call("GetSystemCompileState", {"system": SYS})[:400])
print(call("GetStackIssues", {"system": SYS})[:500])
