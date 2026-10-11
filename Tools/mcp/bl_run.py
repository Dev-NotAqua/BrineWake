"""bl_run.py <asset script.py> [timeout]
Sends an asset script to the user's open Blender with the Brinewake modelling helpers loaded in front of it.
The helpers are bw_kit.py up to its BUILD table; Prop.export is replaced so that a finished prop becomes (or replaces)
an object in the 'Brinewake Kit' collection instead of being written to FBX. Nothing in the user's scene is reset.
"""
import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
kit = open(os.path.join(here, "bw_kit.py"), encoding="utf-8").read()
kit = kit[:kit.index("BUILD = {")]
kit = kit.replace('os.makedirs(OUT, exist_ok=True)', '')
kit = kit.replace("** 1.6", "** 1.0")        # stored paint is the palette colour itself: Blender then shows it as painted
# Prop.tube wound its faces inward (invisible from outside once back faces are culled in the engine): turn them out.
kit = kit.replace("faces.append(self.bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k])))",
                  "faces.append(self.bm.faces.new((a[(k + 1) % sides], a[k], b[k], b[(k + 1) % sides])))")
kit = kit.replace("faces.append(self.bm.faces.new(loops[-1]))", "faces.append(self.bm.faces.new(list(reversed(loops[-1]))))")
kit = kit.replace("faces.append(self.bm.faces.new(list(reversed(loops[0]))))", "faces.append(self.bm.faces.new(loops[0]))")
assert "(a[(k + 1) % sides], a[k], b[k], b[(k + 1) % sides])" in kit and "faces.new(list(reversed(loops[-1])))" in kit, "tube patch did not apply"
tail = '''

def _bw_finish(self):
    """Replace or create the kit object for this prop, keep its place on the shelf, show its paint."""
    coll = bpy.data.collections.get("Brinewake Kit")
    if coll is None:
        coll = bpy.data.collections.new("Brinewake Kit")
        bpy.context.scene.collection.children.link(coll)
    mesh = bpy.data.meshes.new(self.name)
    bmesh.ops.triangulate(self.bm, faces=self.bm.faces[:])
    self.bm.to_mesh(mesh)
    self.bm.free()
    mat = bpy.data.materials.get("BW_Painted")
    if mat is not None:
        mesh.materials.append(mat)
    col = mesh.color_attributes.get("Col")
    if col is not None:
        mesh.color_attributes.active_color = col
        mesh.color_attributes.render_color_index = list(mesh.color_attributes).index(col)
    obj = bpy.data.objects.get(self.name)
    if obj is None:
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        n = len(coll.objects) - 1
        obj.location = ((n % 10) * 26.0, -(n // 10) * 30.0, 0.0)
    else:
        old = obj.data
        obj.data = mesh
        if old.users == 0:
            bpy.data.meshes.remove(old)
    for key in ("bw_ao", "bw_sculpted"):
        if key in obj:
            del obj[key]
    obj["bw_srgb"] = True
    _bw_occlude(obj)
    BW_BUILT.append((self.name, len(mesh.polygons)))


def _bw_occlude(obj, rays=14):
    """Ambient occlusion by ray casting against the asset itself, multiplied into the paint (cavities darker and cooler)."""
    from mathutils.bvhtree import BVHTree
    mesh = obj.data
    col = mesh.color_attributes.get("Col")
    if col is None or len(mesh.polygons) == 0:
        return
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [tuple(q.vertices) for q in mesh.polygons])
    reach = max(0.5, min(2.0, max(obj.dimensions) * 0.12))
    rnd = random.Random(7)
    dirs = []
    while len(dirs) < rays:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.1 < d.length < 1.0:
            dirs.append(d.normalized())
    ao = []
    for v in mesh.vertices:
        n = v.normal
        origin = v.co + n * 0.02
        hit = 0.0
        for d in dirs:
            loc, _, _, dist = tree.ray_cast(origin, d if d.dot(n) > 0 else -d, reach)
            if loc is not None:
                hit += 1.0 - dist / reach
        ao.append(1.0 - hit / rays)
    n = len(col.data)
    buf = [0.0] * (n * 4)
    col.data.foreach_get("color", buf)
    for loop in mesh.loops:
        a = ao[loop.vertex_index]
        k = 0.30 + 0.70 * a ** 1.2
        i = loop.index * 4
        buf[i] *= k * (1.0 - 0.10 * (1.0 - a))
        buf[i + 1] *= k * (1.0 - 0.04 * (1.0 - a))
        buf[i + 2] *= k * (1.0 + 0.08 * (1.0 - a))
    col.data.foreach_set("color", buf)
    mesh.update()
    obj["bw_ao"] = True


BW_BUILT = []
Prop.export = _bw_finish
'''
code = kit + tail + "\n" + open(sys.argv[1], encoding="utf-8").read() + "\nresult = {'built': BW_BUILT}\n"
open(os.path.join(here, "_run.py"), "w", encoding="utf-8").write(code)
print("asset script starts at line", (kit + tail).count(chr(10)) + 2)
print(subprocess.run([sys.executable, os.path.join(here, "bl.py"), os.path.join(here, "_run.py"), sys.argv[2] if len(sys.argv) > 2 else "600"],
                     capture_output=True, text=True).stdout[:3500])
