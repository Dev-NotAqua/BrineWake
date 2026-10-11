"""Build M_BW_Terrain and assign it to the island ground meshes (run inside the editor: py.py ue_terrain_mat.py).

The kit paint material shows the raw vertex colour and makes bright warm paint glow, which turns the
sand pure white in sunlight. The terrain material keeps the painted colour but caps its brightness,
breaks it up with world-space variation and darkens a wet band along the waterline.
"""
import unreal

MAT_DIR = "/Game/Brinewake/Materials"
MAT_NAME = "M_BW_Terrain"
TERRAIN_MESHES = ["/Game/Brinewake/Props/SM_BW_Isle_A", "/Game/Brinewake/Props/SM_BW_Isle_A_Detail"]

CODE = """
struct BWNoise {
    float hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
    float value(float2 p) {
        float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(hash(i), hash(i + float2(1, 0)), f.x), lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), f.x), f.y);
    }
};
BWNoise n;
float2 p = WP.xy;
float macro = n.value(p / 900.0) * 0.6 + n.value(p / 260.0) * 0.4;
float grain = n.value(p / 5.0);
float lum = dot(VC, float3(0.3, 0.59, 0.11));
float3 c = VC * (min(lum, MaxLum) / max(lum, 0.001));
float grass = saturate((VC.g - max(VC.r, VC.b)) * 6.0);
float3 grassC = c * lerp(float3(0.80, 0.90, 0.76), float3(1.12, 1.08, 0.80), macro);
float3 sandC = c * lerp(0.86, 1.05, macro) * lerp(0.94, 1.04, grain);
c = lerp(sandC, grassC, grass);
float wet = saturate((WetTop - WP.z) / WetBand) * (1.0 - grass);
c *= lerp(1.0, WetDarken, wet);
float rough = lerp(lerp(0.92, 0.84, grass), 0.28, wet);
return float4(c, rough);
"""

mel = unreal.MaterialEditingLibrary
path = f"{MAT_DIR}/{MAT_NAME}"
mat = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
if not mat:
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(mat)


def node(cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def scalar(name, value, y):
    p = node(unreal.MaterialExpressionScalarParameter, -900, y)
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", value)
    return p


vc = node(unreal.MaterialExpressionVertexColor, -900, -200)
wp = node(unreal.MaterialExpressionWorldPosition, -900, -60)
params = [scalar("Max Albedo", 0.56, 80), scalar("Wet Top Height", 42.0, 160),
          scalar("Wet Band Height", 34.0, 240), scalar("Wet Darken", 0.62, 320)]

custom = node(unreal.MaterialExpressionCustom, -500, 0)
custom.set_editor_property("code", CODE.strip())
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
custom.set_editor_property("description", "BW Terrain")
names = ["VC", "WP", "MaxLum", "WetTop", "WetBand", "WetDarken"]
inputs = []
for n in names:
    pin = unreal.CustomInput()
    pin.set_editor_property("input_name", n)
    inputs.append(pin)
custom.set_editor_property("inputs", inputs)
# The first connection made after replacing the inputs array does not stick, so wire twice and check.
for _ in range(2):
    wired = [mel.connect_material_expressions(src, "", custom, n) for src, n in zip([vc, wp] + params, names)]
if not all(mel.get_inputs_for_material_expression(mat, custom)):
    raise RuntimeError(f"terrain custom node inputs not wired: {wired}")

rgb = node(unreal.MaterialExpressionComponentMask, -200, -40)
for ch, on in (("r", True), ("g", True), ("b", True), ("a", False)):
    rgb.set_editor_property(ch, on)
alpha = node(unreal.MaterialExpressionComponentMask, -200, 100)
for ch, on in (("r", False), ("g", False), ("b", False), ("a", True)):
    alpha.set_editor_property(ch, on)
mel.connect_material_expressions(custom, "", rgb, "")
mel.connect_material_expressions(custom, "", alpha, "")
spec = node(unreal.MaterialExpressionConstant, -200, 220)
spec.set_editor_property("r", 0.25)

mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(alpha, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
mat.set_editor_property("two_sided", True)
mel.recompile_material(mat)
unreal.EditorAssetLibrary.save_asset(path)

for mesh_path in TERRAIN_MESHES:
    mesh = unreal.load_asset(mesh_path)
    for i in range(len(mesh.static_materials)):
        mesh.set_material(i, mat)
    unreal.EditorAssetLibrary.save_asset(mesh_path)
    print("assigned", mesh.get_name())
print("built", path)
