"""Runs inside the open Blender: lays the kit out in labelled rows, then writes the library to Art/Brinewake_Kit.blend
and a copy of the whole session to Art/Brinewake_Workshop.blend. A rigged figure is moved by its armature."""
import bpy

ART = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Art/"
coll = bpy.data.collections["Brinewake Kit"]
ROWS = [("Ships", ("Sloop", "Brigantine", "Galleon", "Rowboat", "Mast", "Sail", "ShipWheel")),
        ("Crew", ("Pirate_", "NPC_")),
        ("Buildings", ("Alehouse", "WardenHut", "SalvageTent", "Keelwright", "MarketStall", "Tower", "Hut_")),
        ("Docks", ("Dock", "Walkway", "Pier", "Stairs", "Platform", "Crane", "Bridge", "Ladder", "Mooring")),
        ("Bones", ("Skeleton", "Skull", "Bone", "Leviathan", "Gibbet", "Cage", "Grave")),
        ("Wrecks and ruins", ("Wreck", "Ruin", "Idol", "Totem")),
        ("Cliffs", ("Slab_", "Cliff", "SeaStack", "Spire", "Arch", "Cave")),
        ("Rocks", ("Rock_", "Boulder", "Pebbles", "Step_Stones")),
        ("Trees", ("Palm", "Tree_", "Mangrove", "Banana", "Bamboo")),
        ("Plants", ("Bush", "Hedge", "Fern", "BigLeaf", "Grass", "Flowers", "Reeds", "Vines", "Creeper", "Agave", "Mushrooms", "Stump", "Log_", "Driftwood", "Seaweed", "Kelp", "Coral", "Shells")),
        ("Lights and flags", ("Lantern", "Brazier", "Torch", "Campfire", "Bunting", "Banner", "Flag", "Signpost")),
        ("Props", ("",))]
left = sorted((o for o in coll.objects if o.type == 'MESH'), key=lambda o: o.name)
y = 0.0
placed = {}
for label, keys in ROWS:
    row = [o for o in left if any(k in o.name for k in keys)]
    left = [o for o in left if o not in row]
    if not row:
        continue
    first = True
    while row:
        line, x = [], 0.0
        while row and (not line or x < 170.0):
            o = row.pop(0)
            line.append((o, x))
            w = max(o.dimensions.x, 1.0)
            x += w + max(1.0, w * 0.2)
        depth = max(max(o.dimensions.y, 2.0) for o, _ in line)
        y -= depth / 2
        for o, x0 in line:
            mover = o.parent if o.parent is not None and o.parent.type == 'ARMATURE' else o
            mover.location = (x0 + max(o.dimensions.x, 1.0) / 2, y, 0.0)
        if first:
            txt = bpy.data.objects.get("BW_Label_" + label)
            if txt is None:
                cu = bpy.data.curves.new("BW_Label_" + label, 'FONT')
                txt = bpy.data.objects.new("BW_Label_" + label, cu)
                bpy.context.scene.collection.objects.link(txt)
            txt.data.body = label
            txt.data.size = 2.0
            txt.location = (-22.0, y, 0.0)
            first = False
        y -= depth / 2 + 4.0
    placed[label] = sum(1 for o in coll.objects if o.type == 'MESH' and any(k in o.name for k in keys))
bpy.context.view_layer.update()
keep = set(coll.objects)
rigs = bpy.data.collections.get("Brinewake Rigs")
if rigs is not None:
    keep |= set(rigs.objects)
keep |= {a for a in bpy.data.actions if a.name.startswith("A_BW_")}
bpy.data.libraries.write(ART + "Brinewake_Kit.blend", keep, fake_user=True)
err = ""
try:
    bpy.ops.wm.save_as_mainfile(filepath=ART + "Brinewake_Workshop.blend", copy=True)
except Exception as e:
    err = str(e)
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'SOLID'
        sp.shading.color_type = 'VERTEX'
        sp.shading.light = 'STUDIO'
        sp.shading.show_cavity = True
        sp.clip_end = 3000
result = {"rows": placed, "assets": len([o for o in coll.objects if o.type == 'MESH']), "saved_copy_error": err}
