"""Runs inside Blender (python bl.py bl_scatter.py) only because the island's height field uses mathutils.noise:
nothing in the scene is touched. Reads kit/SM_BW_Isle_A.json (cliffs, buildings, the first scatter) and writes
kit/Gullrest_v2.json: the same island dressed with the full kit - varied vegetation, rocks, set pieces, skeletons,
wrecks and ruins, dock gear, sea rocks, the crew with their animations, and the points that need light, fire and sound.
Coordinates are island metres (x east, y north, z up, yaw in degrees), as in the first file."""
import json
import math
import os
import random

from mathutils import Vector, noise

HERE = r"C:/Users/User/Documents/Unreal Projects/Brinewake2/Tools/mcp"
src = open(os.path.join(HERE, "bw_outpost.py"), encoding="utf-8").read()
ns = {"math": math, "Vector": Vector, "noise": noise}
exec(src[src.index('NAME = "SM_BW_Isle_A"'):src.index("def colour(")], ns)          # only the terrain functions
land, height, grass_amount = ns["land"], ns["height"], ns["grass_amount"]
OUTPOST, PEAK, PEAK2, BOX = ns["OUTPOST"], ns["PEAK"], ns["PEAK2"], ns["BOX"]
old = json.load(open(os.path.join(HERE, "kit", "SM_BW_Isle_A.json")))
rnd = random.Random(2026)
props, sea, npcs, fx = [], [], [], []
keep = []                                                            # (x, y, radius) nothing may be scattered into


def ground(x, y):
    return max(height(x, y), 0.0)


def add(mesh, x, y, yaw=None, scale=1.0, sink=0.0, z=None, folder="Dressing"):
    p = {"mesh": mesh, "x": round(x, 2), "y": round(y, 2), "z": round((ground(x, y) if z is None else z) - sink, 2), "yaw": round(rnd.uniform(0, 360) if yaw is None else yaw, 1),
         "scale": round(scale, 2), "folder": folder}
    props.append(p)
    return p


def shore(angle, e_target=0.1, frm=(0.0, 0.0)):
    """Walk out from the middle of the island along a bearing until the land value drops to e_target."""
    a = math.radians(angle)
    d = 0.0
    while land(frm[0] + math.cos(a) * d, frm[1] + math.sin(a) * d) > e_target and d < 160:
        d += 0.5
    return frm[0] + math.cos(a) * d, frm[1] + math.sin(a) * d


# ---- what stays from the first layout: cliffs, buildings, dock; plants get the new variety
PALMS = ["SM_BW_Palm_A", "SM_BW_Palm_B", "SM_BW_Palm_C", "SM_BW_Palm_A", "SM_BW_Palm_C", "SM_BW_Palm_D", "SM_BW_Palm_E", "SM_BW_Palm_F"]
BUSHES = ["SM_BW_Bush_A", "SM_BW_Bush_A", "SM_BW_Bush_B", "SM_BW_Bush_C", "SM_BW_Bush_Flower_A", "SM_BW_Bush_Flower_B", "SM_BW_BigLeaf_A", "SM_BW_Banana_Young"]
FERNS = ["SM_BW_Fern_A", "SM_BW_Fern_B", "SM_BW_Fern_C", "SM_BW_Fern_A", "SM_BW_BigLeaf_B", "SM_BW_Agave_A", "SM_BW_Grass_Tall"]
dock = next(p for p in old["props"] if p["mesh"] == "SM_BW_Dock")
da = math.radians(dock["yaw"])
ca, sa = math.cos(da), math.sin(da)


def along(dist, side):
    return dock["x"] + ca * dist - sa * side, dock["y"] + sa * dist + ca * side


for p in old["props"]:
    m = p["mesh"]
    q = dict(p)
    q.setdefault("scale", 1.0)
    if m.startswith("SM_BW_Slab"):
        q["folder"] = "Rocks"
    elif m in ("SM_BW_Sloop", "SM_BW_Brigantine") or m.startswith("SM_BW_Pirate"):
        continue
    elif m.startswith("SM_BW_Palm"):
        q["mesh"] = rnd.choice(PALMS)
        q["scale"] = round(q["scale"] * (0.8 if q["mesh"][-1] in "DF" else 1.0), 2)
        q["folder"] = "Plants"
    elif m == "SM_BW_Bush_A":
        q["mesh"] = rnd.choice(BUSHES)
        q["scale"] = round(min(q["scale"], 1.9) * 0.85, 2)
        q["folder"] = "Plants"
    elif m == "SM_BW_Fern_A":
        q["mesh"] = rnd.choice(FERNS)
        q["folder"] = "Plants"
    elif m in ("SM_BW_Alehouse", "SM_BW_WardenHut", "SM_BW_SalvageTent", "SM_BW_Keelwright", "SM_BW_MarketStall", "SM_BW_Tower", "SM_BW_Hut_A", "SM_BW_Hut_B", "SM_BW_Dock", "SM_BW_DockEnd",
               "SM_BW_DockCorner"):
        q["folder"] = "Outpost"
        keep.append((p["x"], p["y"], 9.0))
    elif m == "SM_BW_LanternPost":
        q["mesh"] = rnd.choice(["SM_BW_LanternPost", "SM_BW_LanternPost_B", "SM_BW_LanternPost_C"])
        q["folder"] = "Dressing"
    else:
        q["folder"] = "Dressing"
    props.append(q)
for k in range(0, 50, 6):
    keep.append((along(k, 0)[0], along(k, 0)[1], 5.5))
keep.append((OUTPOST.x, OUTPOST.y - 4, 13.0))

# ---- ships: one each side of the dock, the galleon riding at anchor off the end
x, y = along(34.0, 7.2)
add("SM_BW_Sloop", x, y, dock["yaw"] + 180.0, z=0.0, folder="Ships")
x, y = along(22.0, -8.4)
add("SM_BW_Brigantine", x, y, dock["yaw"], z=0.0, folder="Ships")
x, y = along(104.0, -34.0)
add("SM_BW_Galleon", x, y, dock["yaw"] + 62.0, z=0.0, folder="Ships")
gal = (x, y)
x, y = along(52.0, 9.0)
add("SM_BW_Rowboat", x, y, dock["yaw"] + 20.0, z=0.0, folder="Ships")

# ---- the outpost square
ox, oy = OUTPOST.x, OUTPOST.y
square = [("SM_BW_Campfire_Spit", 3.5, -3.5, 20), ("SM_BW_Table_Set", -3.5, 4.5, 95), ("SM_BW_Table", -0.5, 7.0, 10), ("SM_BW_Stool", 0.9, 5.4, 0), ("SM_BW_Chair", -1.8, 7.9, 200),
          ("SM_BW_Barrel_Stack", -11.5, 3.5, 40), ("SM_BW_Barrel_Rack", -13.0, 7.0, 95), ("SM_BW_Crate_Stack_Tarp", 10.5, -4.5, 30), ("SM_BW_Crate_Stack", 13.0, -7.5, 110),
          ("SM_BW_Sack_Pile", 8.5, -6.5, 0), ("SM_BW_Cart", 6.5, -13.5, 150), ("SM_BW_Well", -10.0, -8.5, 0), ("SM_BW_Signpost", 3.0, -15.0, 0), ("SM_BW_Signpost_Hanging", -4.5, 2.0, 185),
          ("SM_BW_Bell_Post", -2.5, -11.5, 20), ("SM_BW_Bunting", 0.5, -6.0, 8), ("SM_BW_Weapon_Rack", -23.0, -1.0, 150), ("SM_BW_Brazier", -21.0, -6.5, 0), ("SM_BW_Brazier", -27.5, 0.5, 0),
          ("SM_BW_Basket_Fruit", 9.6, -7.9, 0), ("SM_BW_Basket_Fish", 20.5, -11.5, 0), ("SM_BW_FishRack", 23.5, -13.5, 120), ("SM_BW_Chest", 15.0, -15.5, 200), ("SM_BW_Gold_Small", 15.6, -14.6, 0),
          ("SM_BW_Bottles", -1.0, 4.4, 0), ("SM_BW_Powder_Keg", 27.0, -3.0, 0), ("SM_BW_Cannonballs", 29.0, -5.0, 0), ("SM_BW_Tent", 24.0, -19.5, 35), ("SM_BW_Lookout_Platform", -15.5, -14.0, 20),
          ("SM_BW_Gibbet", 21.0, 3.5, 250), ("SM_BW_Skull_Pike", -17.5, -3.0, 0), ("SM_BW_Banner_Pole_X", 0, 0, 0), ("SM_BW_FlagPole", 5.5, -9.5, 0), ("SM_BW_Hammock", 28.5, 6.5, 60),
          ("SM_BW_TikiTorch", 1.0, -17.5, 0), ("SM_BW_TikiTorch", 5.5, -19.0, 0), ("SM_BW_TikiTorch", -6.0, -14.5, 0), ("SM_BW_TikiTorch", 12.0, -11.5, 0), ("SM_BW_Spyglass_Stand", -14.6, -13.4, 0),
          ("SM_BW_Stool", 5.2, -2.2, 0), ("SM_BW_Stool", 2.2, -5.4, 0), ("SM_BW_Fence_Rope", -9.0, -17.5, 15), ("SM_BW_Fence_Plank", 17.5, 1.5, 100), ("SM_BW_Rope_Coil_X", 0, 0, 0)]
for mesh, dx, dy, yaw in square:
    if mesh.endswith("_X"):
        continue
    x, y = ox + dx, oy + dy
    z = None
    if mesh == "SM_BW_Spyglass_Stand":
        z = ground(x, y) + 4.25                                      # stands on the lookout stage
    add(mesh.replace("Powder_Keg", "PowderKeg"), x, y, yaw, z=z)
    keep.append((x, y, 2.6))
# ---- on and beside the dock (deck 1.3 m above the water)
for mesh, dist, side, yaw, z in (("SM_BW_Dock_Crane", 41.0, 3.3, 180, 0.0), ("SM_BW_Barrel_Stack", 13.0, 0.95, 0, 1.3), ("SM_BW_Crate_Stack", 25.0, -0.9, 90, 1.3), ("SM_BW_RopeCoil", 18.5, 1.1, 0, 1.3),
                                 ("SM_BW_Lantern_Ground", 31.5, -1.3, 0, 1.3), ("SM_BW_CrabPot", 36.0, 1.1, 40, 1.3), ("SM_BW_Buoy", 43.0, -1.0, 0, 1.3), ("SM_BW_Sack_Pile", 8.0, -0.9, 0, 1.3),
                                 ("SM_BW_Spyglass_Stand", 49.0, -0.9, 0, 1.3), ("SM_BW_MooringPost_B", 52.5, 0.0, 0, -3.0), ("SM_BW_MooringPost_B", 20.0, 2.9, 0, -3.0),
                                 ("SM_BW_Lantern_Ground", 6.0, 1.2, 0, 1.3), ("SM_BW_Cannon", 46.5, 1.0, -90, 1.3), ("SM_BW_Cannonballs", 45.3, 1.1, 0, 1.3), ("SM_BW_Powder_Keg", 44.6, 0.4, 0, 1.3),
                                 ("SM_BW_Buoy", 30.0, 6.0, 0, -0.2), ("SM_BW_Buoy", 58.0, -6.0, 0, -0.2)):
    x, y = along(dist, side)
    add(mesh.replace("Powder_Keg", "PowderKeg"), x, y, dock["yaw"] + yaw, z=z)

# ---- set pieces round the island
levi = shore(250, 0.14)
wreck = shore(98, 0.03)
sets = [("SM_BW_Skeleton_Captain", shore(162, 0.16), None, 0.0), ("SM_BW_Leviathan_Bones", levi, 70.0, 0.1), ("SM_BW_Wreck_Hull", wreck, 25.0, 0.3), ("SM_BW_Wreck_Mast", shore(22, 0.06), 200.0, 0.0),
        ("SM_BW_Wreck_Rowboat", shore(215, 0.12), 40.0, 0.0), ("SM_BW_DigSpot", shore(300, 0.22), None, 0.0), ("SM_BW_Skeleton_Buried", shore(304, 0.20), None, 0.0),
        ("SM_BW_Skull_Pikes", shore(132, 0.26), 132.0, 0.0), ("SM_BW_Anchor_Buried", shore(332, 0.08), None, 0.0), ("SM_BW_Skeleton_Lie", shore(74, 0.16), None, 0.0),
        ("SM_BW_Wreck_Hull_Small", shore(188, 0.02), 110.0, 0.2), ("SM_BW_Anchor", shore(40, 0.12), None, 0.0), ("SM_BW_Skeleton_Sit", shore(352, 0.2), None, 0.0),
        ("SM_BW_Sword_Stuck", shore(165, 0.2), None, 0.0), ("SM_BW_Chest_Open", shore(301, 0.26), 120.0, 0.0), ("SM_BW_Gold_Pile", shore(299, 0.3), None, 0.0),
        ("SM_BW_Campfire", shore(120, 0.2), None, 0.0), ("SM_BW_Tent", shore(124, 0.26), 300.0, 0.0), ("SM_BW_Bone_Pile", shore(252, 0.24), None, 0.0), ("SM_BW_Skull_Pile", shore(246, 0.2), None, 0.0)]
for mesh, (x, y), yaw, sink in sets:
    add(mesh, x, y, yaw, sink=sink, folder="SetPieces")
    keep.append((x, y, 7.0 if "Wreck_Hull" in mesh or "Leviathan" in mesh else 3.0))


def clear_spot(cx, cy, reach, need=0.35, rad=6.0):
    """A spot near (cx, cy) that is on firm ground and away from everything kept."""
    best = None
    for _ in range(400):
        a, d = rnd.uniform(0, 6.283), rnd.uniform(0, reach)
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if land(x, y) < need or (Vector((x, y)) - PEAK).length < 27 or (Vector((x, y)) - PEAK2).length < 15:
            continue
        if any(math.hypot(x - kx, y - ky) < kr + rad for kx, ky, kr in keep):
            continue
        best = (x, y)
        break
    return best


ruins = clear_spot(34, 26, 18, 0.4, 9.0) or (34.0, 26.0)
keep.append((ruins[0], ruins[1], 11.0))
for mesh, dx, dy, yaw in (("SM_BW_Ruin_Arch", 0, 0, 20), ("SM_BW_Ruin_Pillar", -5.5, 2.5, 0), ("SM_BW_Ruin_Pillar_Broken", 5.5, -2.5, 0), ("SM_BW_Ruin_Pillar_Stub", -3.0, -6.0, 0),
                          ("SM_BW_Ruin_Wall", 2.0, 7.5, 15), ("SM_BW_Ruin_Wall_Low", -8.0, -3.0, 100), ("SM_BW_Idol_Head", 1.0, 3.6, 200), ("SM_BW_Skeleton_Chest", 3.5, 5.5, 160),
                          ("SM_BW_Brazier", -2.2, -1.6, 0), ("SM_BW_Brazier", 2.2, -1.6, 0), ("SM_BW_Vines_Hang_A", 0.0, 0.0, 20), ("SM_BW_Mushrooms_Glow", 4.5, 1.5, 0)):
    add(mesh, ruins[0] + dx, ruins[1] + dy, yaw, z=(ground(ruins[0] + dx, ruins[1] + dy) + 4.3) if "Vines" in mesh else None, folder="SetPieces")
graves = clear_spot(-36, 2, 16, 0.35, 7.0) or (-36.0, 2.0)
keep.append((graves[0], graves[1], 8.0))
for k in range(7):
    gx, gy = graves[0] + (k % 4) * 2.4 - 3.6, graves[1] + (k // 4) * 3.4 - 1.7
    add(rnd.choice(["SM_BW_Grave_Stone", "SM_BW_Grave_Stone_B", "SM_BW_Grave_Cross"]), gx, gy, 180 + rnd.uniform(-12, 12), folder="SetPieces")
add("SM_BW_Tree_Dead_A", graves[0] - 6.5, graves[1] + 1.0, folder="SetPieces")
add("SM_BW_Lantern_Ground", graves[0] + 0.3, graves[1] - 3.6, folder="SetPieces")
add("SM_BW_Fence_Plank", graves[0], graves[1] + 5.2, 0, folder="SetPieces")
totem = clear_spot(-62, 34, 12, 0.3, 5.0) or (-62.0, 34.0)
keep.append((totem[0], totem[1], 6.0))
add("SM_BW_Totem", totem[0], totem[1], 300, folder="SetPieces")
add("SM_BW_Skull_Pile", totem[0] + 1.6, totem[1] - 1.0, folder="SetPieces")
add("SM_BW_Campfire", totem[0] - 2.5, totem[1] - 2.2, folder="SetPieces")


# ---- vegetation and rocks by rule
def place(meshes, count, emin, emax, scale=(0.9, 1.3), sink=0.05, gap=2.0, grass=None, near=None, reach=0.0, folder="Plants", wet=False):
    made, tries, mine = 0, 0, []
    while made < count and tries < 14000:
        tries += 1
        if near is not None:
            a, d = rnd.uniform(0, 6.283), rnd.uniform(0, reach)
            x, y = near[0] + math.cos(a) * d, near[1] + math.sin(a) * d
        else:
            x, y = rnd.uniform(BOX[0], BOX[1]), rnd.uniform(BOX[2], BOX[3])
        e = land(x, y)
        if not emin <= e <= emax:
            continue
        if not wet and ((Vector((x, y)) - PEAK).length < 25 or (Vector((x, y)) - PEAK2).length < 13):
            continue
        if grass is not None and not grass[0] <= grass_amount(x, y) <= grass[1]:
            continue
        if any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep) or any(math.hypot(x - mx, y - my) < gap for mx, my in mine):
            continue
        s = rnd.uniform(*scale)
        z = height(x, y) if wet else ground(x, y)
        props.append({"mesh": rnd.choice(meshes), "x": round(x, 2), "y": round(y, 2), "z": round(z - sink * s, 2), "yaw": round(rnd.uniform(0, 360), 1), "scale": round(s, 2), "folder": folder})
        mine.append((x, y))
        made += 1
    return mine


trees = place(["SM_BW_Tree_Jungle_A", "SM_BW_Tree_Jungle_B", "SM_BW_Tree_Jungle_C", "SM_BW_Tree_Jungle_A"], 16, 0.32, 2.0, (0.85, 1.25), 0.25, 10.0, grass=(0.55, 1.0))
for tx, ty in trees:
    place(["SM_BW_Mushrooms_Red", "SM_BW_Mushrooms_Brown", "SM_BW_Fern_B", "SM_BW_Creeper_A", "SM_BW_BigLeaf_Dark"], 3, 0.2, 2.0, (0.8, 1.3), 0.0, 1.5, near=(tx, ty), reach=4.5)
place(["SM_BW_Bamboo_A", "SM_BW_Bamboo_B"], 9, 0.25, 2.0, (0.8, 1.2), 0.1, 6.0, grass=(0.3, 1.0))
place(["SM_BW_Banana_A", "SM_BW_Banana_B", "SM_BW_Banana_Young"], 14, 0.22, 2.0, (0.9, 1.3), 0.1, 4.0, grass=(0.25, 1.0))
place(["SM_BW_BigLeaf_A", "SM_BW_BigLeaf_B", "SM_BW_BigLeaf_Dark", "SM_BW_Agave_B"], 26, 0.2, 2.0, (0.8, 1.5), 0.02, 2.4, grass=(0.3, 1.0))
place(["SM_BW_Bush_A", "SM_BW_Bush_B", "SM_BW_Bush_C", "SM_BW_Bush_Flower_A", "SM_BW_Bush_Flower_B", "SM_BW_Hedge_Long"], 44, 0.2, 2.0, (0.8, 1.5), 0.1, 2.6, grass=(0.35, 1.0))
place(["SM_BW_Fern_A", "SM_BW_Fern_B", "SM_BW_Fern_C"], 46, 0.2, 2.0, (0.9, 1.7), 0.02, 1.9, grass=(0.3, 1.0))
place(["SM_BW_Grass_A", "SM_BW_Grass_B", "SM_BW_Grass_B", "SM_BW_Grass_Short", "SM_BW_Grass_Tall"], 300, 0.2, 2.0, (1.0, 1.9), 0.0, 1.15, grass=(0.4, 1.0))
place(["SM_BW_Grass_Dry", "SM_BW_Grass_Short", "SM_BW_Bush_Dry"], 60, 0.12, 2.0, (0.9, 1.5), 0.0, 1.6, grass=(0.03, 0.4))
place(["SM_BW_Flowers_Red", "SM_BW_Flowers_Mixed", "SM_BW_Flowers_Blue", "SM_BW_Flowers_Mixed"], 64, 0.2, 2.0, (1.0, 1.8), 0.0, 1.6, grass=(0.5, 1.0))
place(["SM_BW_Reeds_A", "SM_BW_Reeds_B"], 26, -0.03, 0.05, (0.9, 1.4), 0.1, 2.2)
place(["SM_BW_Agave_A", "SM_BW_Agave_B"], 16, 0.14, 0.6, (0.8, 1.4), 0.02, 3.0, grass=(0.0, 0.25))
place(["SM_BW_Log_Fallen", "SM_BW_Log_Short", "SM_BW_Stump_A", "SM_BW_Stump_B"], 12, 0.25, 2.0, (0.9, 1.2), 0.04, 6.0, grass=(0.4, 1.0))
place(["SM_BW_Mangrove_A", "SM_BW_Mangrove_B"], 7, -0.06, 0.03, (0.9, 1.3), 0.5, 7.0)
place(["SM_BW_Rock_Moss_A", "SM_BW_Rock_Moss_B", "SM_BW_Rock_Moss_C", "SM_BW_Rock_Pile_Moss"], 16, 0.3, 2.0, (0.6, 1.3), 0.35, 5.0, grass=(0.45, 1.0), folder="Rocks")
place(["SM_BW_Rock_A", "SM_BW_Rock_C", "SM_BW_Rock_D", "SM_BW_Rock_E", "SM_BW_Rock_F", "SM_BW_Boulder_A", "SM_BW_Boulder_C", "SM_BW_Rock_Flat_A", "SM_BW_Rock_Pile_A"], 30, 0.02, 0.5, (0.5, 1.2), 0.3, 5.0,
      grass=(0.0, 0.35), folder="Rocks")
place(["SM_BW_Pebbles_A", "SM_BW_Pebbles_B"], 30, 0.0, 0.3, (0.8, 1.4), 0.03, 3.0, grass=(0.0, 0.3), folder="Rocks")
place(["SM_BW_Driftwood_A", "SM_BW_Driftwood_B", "SM_BW_Shells_A", "SM_BW_Shells_A", "SM_BW_Palm_Frond_Fallen", "SM_BW_Seaweed_A"], 40, 0.0, 0.14, (0.8, 1.3), 0.0, 3.0, grass=(0.0, 0.2))
# under water on the shelf: reef growth and stones
place(["SM_BW_Coral_Branch", "SM_BW_Coral_Fan", "SM_BW_Coral_Brain", "SM_BW_Coral_Tubes", "SM_BW_Coral_Branch_Blue", "SM_BW_Seaweed_A", "SM_BW_Kelp_A", "SM_BW_Kelp_A"], 70, -0.36, -0.06, (1.0, 2.2), 0.05, 2.6,
      folder="Reef", wet=True)
place(["SM_BW_Rock_Grey_A", "SM_BW_Rock_Grey_B", "SM_BW_Rock_Grey_C", "SM_BW_Rock_B", "SM_BW_Boulder_B", "SM_BW_Rock_Flat_B", "SM_BW_Step_Stones"], 22, -0.30, -0.04, (0.7, 1.5), 0.5, 7.0, folder="Reef", wet=True)

# ---- rocks standing in the sea: each one makes its own ring of foam
def sea_rock(mesh, angle, dist, scale, sink, yaw=None):
    a = math.radians(angle)
    x, y = math.cos(a) * dist, math.sin(a) * dist
    for _ in range(40):
        if land(x, y) < -0.22 and math.hypot(x - gal[0], y - gal[1]) > 45 and all(math.hypot(x - along(k, 0)[0], y - along(k, 0)[1]) > 40 for k in (20, 50, 80)):
            break
        dist += 6.0
        x, y = math.cos(a) * dist, math.sin(a) * dist
    sea.append({"mesh": mesh, "x": round(x, 2), "y": round(y, 2), "z": round(-sink, 2), "yaw": round(rnd.uniform(0, 360) if yaw is None else yaw, 1), "scale": round(scale, 2)})
    return x, y


for k, (mesh, ang, dist, sc, sink) in enumerate((("SM_BW_SeaStack", 30, 150, 1.3, 3.0), ("SM_BW_SeaStack_B", 52, 185, 1.6, 2.0), ("SM_BW_Rock_Arch", 78, 210, 2.4, 2.5), ("SM_BW_Spire_A", 105, 165, 1.5, 2.0),
                                                 ("SM_BW_SeaStack", 140, 200, 1.6, 3.5), ("SM_BW_Spire_B", 165, 150, 1.8, 1.5), ("SM_BW_SeaStack_B", 195, 175, 1.5, 2.0), ("SM_BW_Spire_A", 225, 205, 1.9, 2.5),
                                                 ("SM_BW_SeaStack", 258, 170, 1.2, 3.0), ("SM_BW_Rock_Arch", 285, 240, 2.8, 3.0), ("SM_BW_Spire_B", 345, 190, 2.0, 1.5), ("SM_BW_SeaStack_B", 8, 230, 2.0, 2.5),
                                                 ("SM_BW_Cliff_B", 120, 260, 1.6, 2.0), ("SM_BW_Cliff_A", 240, 290, 1.5, 3.0), ("SM_BW_SeaStack_Ember", 315, 330, 1.5, 3.0), ("SM_BW_Spire_Ash", 60, 300, 1.8, 2.0))):
    cx, cy = sea_rock(mesh, ang, dist, sc, sink)
    for j in range(rnd.randint(3, 5)):                               # a skirt of lower rocks round each one
        a2, d2 = rnd.uniform(0, 6.283), rnd.uniform(9, 22) * sc
        sea.append({"mesh": rnd.choice(["SM_BW_Rock_B", "SM_BW_Rock_D", "SM_BW_Boulder_B", "SM_BW_Rock_Grey_B", "SM_BW_Rock_Pile_A", "SM_BW_Rock_Flat_B"]), "x": round(cx + math.cos(a2) * d2, 2),
                    "y": round(cy + math.sin(a2) * d2, 2), "z": round(-rnd.uniform(0.6, 1.6), 2), "yaw": round(rnd.uniform(0, 360), 1), "scale": round(rnd.uniform(1.2, 2.4), 2)})
for ang in range(15, 360, 24):                                       # loose rocks just off the beaches
    x, y = shore(ang + rnd.uniform(-8, 8), -0.14)
    sea.append({"mesh": rnd.choice(["SM_BW_Rock_A", "SM_BW_Rock_D", "SM_BW_Boulder_A", "SM_BW_Rock_Grey_A", "SM_BW_Rock_F"]), "x": round(x, 2), "y": round(y, 2), "z": round(-rnd.uniform(0.5, 1.1), 2),
                "yaw": round(rnd.uniform(0, 360), 1), "scale": round(rnd.uniform(1.0, 2.0), 2)})
sea = [s for s in sea if math.hypot(s["x"] - gal[0], s["y"] - gal[1]) > 30 and all(math.hypot(s["x"] - along(k, 0)[0], s["y"] - along(k, 0)[1]) > 22 for k in (10, 30, 50, 70))]

# ---- the crew: who stands where, doing what, facing which point
def npc(mesh, x, y, anim, face, z=None):
    npcs.append({"mesh": mesh, "x": round(x, 2), "y": round(y, 2), "z": round(ground(x, y) if z is None else z, 2), "anim": anim, "face": [round(face[0], 2), round(face[1], 2)]})


fire = (ox + 3.5, oy - 3.5)
npc("SK_BW_NPC_Alekeeper", ox - 5.0, oy + 2.6, "Idle_Hold", (ox, oy))
npc("SK_BW_Pirate_Cook", fire[0] - 1.5, fire[1] + 0.6, "Idle_Hold", fire)
npc("SK_BW_Pirate_Deckhand", fire[0] + 2.2, fire[1] + 1.6, "Dance", fire)
npc("SK_BW_Pirate_OldSalt", fire[0] + 1.7, fire[1] + 1.3 - 3.2, "Talk", fire)
npc("SK_BW_Pirate_Brute", ox + 11.4, oy - 6.0, "Carry_Idle", (ox, oy - 8))
npc("SK_BW_NPC_Warden", ox - 22.0, oy - 4.0, "Idle", (ox, oy))
npc("SK_BW_NPC_Deepfinder", ox + 14.5, oy - 13.0, "Talk", (ox + 10, oy - 10))
npc("SK_BW_Pirate_Gunner", ox + 27.2, oy - 5.2, "Idle", (ox + 40, oy - 20))
npc("SK_BW_Pirate_Captain", ox + 4.0, oy - 12.0, "Idle", (ox + 4, oy - 30))
npc("SK_BW_Pirate_Quartermaster", *along(4.0, -0.6), "Wave", along(-10, 0), z=None)
x, y = along(33.0, 1.0)
npc("SK_BW_NPC_Saltmarket", x, y, "Talk", along(33.0, -3.0), z=1.3)
x, y = along(47.6, -0.2)
npc("SK_BW_Pirate_Lookout", x, y, "Spyglass", along(120.0, -20.0), z=1.3)
kw = next(p for p in old["props"] if p["mesh"] == "SM_BW_Keelwright")
npc("SK_BW_NPC_Keelwright", kw["x"] - ca * 3.0, kw["y"] - sa * 3.0, "Hammer", (kw["x"], kw["y"]), z=ground(kw["x"] - ca * 3.0, kw["y"] - sa * 3.0))

# ---- points that need a light, a fire, a sound
LAMP = {"SM_BW_LanternPost": [(0.86, 0.0, 2.55)], "SM_BW_LanternPost_B": [(0.86, 0.0, 3.05), (-0.86, 0.0, 2.93)], "SM_BW_LanternPost_C": [(0.86, 0.0, 3.85)], "SM_BW_Lantern_Ground": [(0, 0, 0.3)],
        "SM_BW_Signpost_Hanging": [(-0.75, 0.0, 1.75)], "SM_BW_Bunting": [(0.0, 0.0, 2.3)], "SM_BW_Lookout_Platform": [(1.48, 1.48, 5.5)]}
FIRE = {"SM_BW_Campfire": (0, 0, 0.5, 1.0), "SM_BW_Campfire_Spit": (0, 0, 0.5, 1.0), "SM_BW_Brazier": (0, 0, 1.6, 0.9), "SM_BW_TikiTorch": (0.1, 0.0, 2.4, 0.5)}
for p in props:
    yaw, s = math.radians(p["yaw"]), p.get("scale", 1.0)
    for lx, ly, lz in LAMP.get(p["mesh"], ()):
        fx.append({"kind": "lamp", "x": round(p["x"] + (lx * math.cos(yaw) - ly * math.sin(yaw)) * s, 2), "y": round(p["y"] + (lx * math.sin(yaw) + ly * math.cos(yaw)) * s, 2), "z": round(p["z"] + lz * s, 2)})
    if p["mesh"] in FIRE:
        lx, ly, lz, size = FIRE[p["mesh"]]
        fx.append({"kind": "fire", "x": round(p["x"] + lx, 2), "y": round(p["y"] + ly, 2), "z": round(p["z"] + lz * s, 2), "size": size})
start = dict(old["start"])
out = {"props": props, "sea": sea, "npcs": npcs, "fx": fx, "start": start, "falls": old.get("falls"), "peak": old.get("peak"), "dock": {"x": dock["x"], "y": dock["y"], "yaw": dock["yaw"]},
       "galleon": [round(gal[0], 2), round(gal[1], 2)], "ruins": [round(v, 2) for v in ruins], "graves": [round(v, 2) for v in graves]}
json.dump(out, open(os.path.join(HERE, "kit", "Gullrest_v2.json"), "w"), indent=0)
counts = {}
for p in props:
    counts[p["folder"]] = counts.get(p["folder"], 0) + 1
result = {"props": len(props), "by_folder": counts, "sea": len(sea), "npcs": len(npcs), "fx": len(fx), "ruins": out["ruins"], "graves": out["graves"], "dock": out["dock"]}
