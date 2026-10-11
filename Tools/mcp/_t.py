import bpy, bmesh, math
from mathutils import Vector
bm = bmesh.new()
sides = 8
loops = []
for z in (0.0, 1.0):
    axis = Vector((0, 0, 1))
    side = axis.cross(Vector((0, 1, 0))); side.normalize(); up = side.cross(axis)
    loops.append([bm.verts.new(Vector((0, 0, z)) + (side * math.cos(a) + up * math.sin(a)) * 0.5) for a in (2 * math.pi * k / sides for k in range(sides))])
a, b = loops
f = bm.faces.new((a[0], a[1], b[1], b[0]))
bm.normal_update()
c = f.calc_center_median()
out = f.normal.dot(Vector((c.x, c.y, 0)))
cap = bm.faces.new(loops[-1]); bm.normal_update()
mat = bpy.data.materials.get("BW_Painted")
result = {"tube_side_outward": out > 0, "top_cap_up": cap.normal.z > 0, "backface_culling": mat.use_backface_culling if mat else None}
bm.free()
