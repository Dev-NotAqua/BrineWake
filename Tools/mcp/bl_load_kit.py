import bpy

KIT = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/Brinewake_Kit.blend"
coll = bpy.data.collections.get("Brinewake Kit")
if coll is None:
    coll = bpy.data.collections.new("Brinewake Kit")
    bpy.context.scene.collection.children.link(coll)
have = {o.name for o in coll.objects}
with bpy.data.libraries.load(KIT, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("SM_BW_") and n not in have]
added = 0
for o in dst.objects:
    if o is not None:
        coll.objects.link(o)
        added += 1
for name in ("Cube",):                       # the untouched default cube sits where the first asset is shelved
    ob = bpy.data.objects.get(name)
    if ob is not None and ob.type == 'MESH' and len(ob.data.vertices) == 8:
        ob.hide_set(True)
result = {"added": added, "in_kit": len(coll.objects), "names": sorted(o.name for o in coll.objects)[:60]}
