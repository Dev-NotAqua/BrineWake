"""Runs inside the open Blender, once: the resculpted rocks came out chalk white in a lit scene. Grade their paint to warm
sandstone (sunlit faces tan, shade sides a muted mauve-grey) so they sit with the rest of the kit."""
import bpy

done = 0
for obj in bpy.data.collections["Brinewake Kit"].objects:
    if obj.type != 'MESH' or not obj.get("bw_sculpted") or obj.get("bw_graded"):
        continue
    col = obj.data.color_attributes.get("Col")
    n = len(col.data)
    buf = [0.0] * (n * 4)
    col.data.foreach_get("color", buf)
    for i in range(0, n * 4, 4):
        r, g, b = (max(buf[i + k], 0.0) ** (1 / 2.2) for k in range(3))
        lum = (r + g + b) / 3
        k = min(1.0, max(0.0, (lum - 0.35) / 0.5))                  # how sunlit this texel is
        r2 = r * (0.80 + 0.06 * k)
        g2 = g * (0.74 + 0.02 * k)
        b2 = b * (0.72 - 0.14 * k)
        buf[i], buf[i + 1], buf[i + 2] = r2 ** 2.2, g2 ** 2.2, b2 ** 2.2
    col.data.foreach_set("color", buf)
    obj.data.update()
    obj["bw_graded"] = True
    done += 1
result = {"graded": done}
