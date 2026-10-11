"""Runs inside the open Blender, once. Kit paint was stored as palette ** 1.6 (tuned for Unreal reading the bytes as linear),
which shows far too dark in Blender. From now on the stored colour IS the palette colour: Blender shows it as painted and
Unreal's material applies the sRGB to linear curve. This converts every kit mesh that is still in the old encoding."""
import bpy

done = 0
for obj in bpy.data.collections["Brinewake Kit"].objects:
    if obj.type != 'MESH' or obj.get("bw_srgb"):
        continue
    col = obj.data.color_attributes.get("Col")
    if col is None:
        continue
    n = len(col.data)
    e = 1.375 if obj.get("bw_sculpted") else 0.625     # resculpted rocks were written through the attribute API (linear), the rest raw
    buf = [0.0] * (n * 4)
    col.data.foreach_get("color", buf)
    for i in range(0, n * 4, 4):
        buf[i] = max(buf[i], 0.0) ** e
        buf[i + 1] = max(buf[i + 1], 0.0) ** e
        buf[i + 2] = max(buf[i + 2], 0.0) ** e
    col.data.foreach_set("color", buf)
    obj.data.update()
    obj["bw_srgb"] = True
    done += 1
result = {"converted": done}
