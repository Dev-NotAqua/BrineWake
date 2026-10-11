"""Dress the Gullrest outpost with props from the installed Fab packs (run inside the editor: py.py ue_dress.py).

Each cluster hangs off a shopkeeper: "f" is the distance out from their building, "r" the distance to
the right of that line. A prop that would overlap something is nudged to the nearest free ground.
Rerunnable: everything it spawns lives in the Island/PackProps folder and is rebuilt each run.
"""
import math

import unreal

FOLDER = "Island/PackProps"
PACKS = {"SFA": "/Game/STYLIZEDFantasyArmory", "DSH": "/Game/STYLIZEDDeepSeaHuntersStation",
         "LIB": "/Game/Stylized_Library", "MUG": "/Game/StylizedBeerMugs"}
GROUND_PREFIXES = ("BW_Isle_A", "BW_Dock", "BW_Keelwright")
SEARCH_RADII = (0, 90, 180, 270, 360)
DETAIL_LABEL = "BW_Isle_A_Detail"


def ring(key, f, r, radius, count, scale, start=0.0):
    """Items evenly round a centre, facing it (chairs round a table)."""
    out = []
    for i in range(count):
        ang = math.radians(start + 360.0 * i / count)
        out.append((key, f + math.cos(ang) * radius, r + math.sin(ang) * radius, math.degrees(ang) + 180.0, scale, []))
    return out


# (mesh, f, r, yaw relative to the outward direction, scale, [(mesh, dx, dy, yaw, scale) on top])
CLUSTERS = [
    {"name": "Alehouse", "anchor": "BW_NPC_Alekeeper", "building": "BW_Alehouse_0000", "items": [
        ("LIB:SM_Table", 330, -340, 0, 0.9, [("MUG:SM_BeerMug_01", 22, 14, 30, 1), ("MUG:SM_BeerMug_03", -26, -8, 140, 1),
                                             ("MUG:SM_BeerMug_04", 4, -30, 250, 1), ("SFA:SM_SFA_Bottle_004", -8, 26, 0, 1.6)]),
        *ring("SFA:SM_SFA_Chair_001", 330, -340, 100, 3, 1.15, 40),
        ("LIB:SM_Table", 240, 400, 25, 0.9, [("MUG:SM_BeerMug_02", 20, -12, 80, 1), ("MUG:SM_BeerMug_05", -22, 16, 200, 1),
                                             ("SFA:SM_SFA_Lamp_001", 0, 0, 0, 1.2)]),
        *ring("SFA:SM_SFA_Chair_001", 240, 400, 100, 3, 1.15, 100),
        ("SFA:SM_SFA_Barrel_001", -40, -430, 0, 1.1, [("SFA:SM_SFA_Bottle_001", 8, 6, 0, 1.6), ("SFA:SM_SFA_Bottle_006", -10, -4, 0, 1.6)]),
        ("SFA:SM_SFA_Barrel_001", 50, -500, 40, 1.0, []),
        ("SFA:SM_SFA_Box_001", 20, 330, 12, 1.0, [("LIB:SM_Gramophone", 0, 0, 200, 0.6)]),
    ]},
    {"name": "Warden", "anchor": "BW_NPC_Warden", "building": "BW_WardenHut_0001", "items": [
        ("SFA:SM_SFA_CombWeaponRack_001", -60, -330, 0, 1.0, []),
        ("SFA:SM_SFA_CombWeaponRack_003", -60, 330, 0, 1.0, []),
        ("SFA:SM_SFA_CombTable_001", 120, 330, 90, 0.9, []),
        ("SFA:SM_SFA_CombatDummy_001", 560, -330, 180, 1.1, []),
        ("SFA:SM_SFA_CombatDummy_002", 620, -140, 180, 1.1, []),
        ("SFA:SM_SFA_CombatDummy_003", 560, 60, 180, 1.1, []),
        ("SFA:SM_SFA_Target_001", 760, 300, 180, 1.2, []),
        ("SFA:SM_SFA_Box_001", 140, -300, 20, 0.9, [("SFA:SM_SFA_Anvil_001", 0, 0, 90, 1.3)]),
    ]},
    {"name": "Salvage", "anchor": "BW_NPC_Deepfinder", "building": "BW_SalvageTent_0002", "items": [
        ("DSH:SM_Kraken_001", -120, -460, 30, 0.8, []),
        ("DSH:SM_Krakren_Table_003", -60, 470, -20, 0.6, []),
        ("DSH:SM_Table_001", 260, -300, 90, 0.75, [("DSH:SM_Harpoon_001", 20, 20, 15, 1), ("DSH:SM_Harpoon_003", -30, -25, 190, 1),
                                                   ("DSH:SM_Fish_Head_001", -70, 30, 60, 0.8)]),
        ("DSH:SM_Fish_Head_Stand_001", 90, 230, 0, 1.6, []),
        ("DSH:SM_Fish_Head_Stand_002", 90, -150, 0, 1.6, []),
        ("DSH:SM_Naval_Mine_001", 330, 330, 0, 1.3, []),
        ("DSH:SM_Naval_Mine_001", 420, 240, 70, 1.1, []),
        ("DSH:SM_Chest_001", 190, 440, 200, 1.0, []),
        ("DSH:SM_Crab_Claw_001", -220, -330, 110, 0.7, []),
        ("DSH:SM_Crab_Claw_005", -40, -620, 250, 0.6, []),
    ]},
    {"name": "Timber", "at": (25800.0, 34760.0, 90.0), "items": [
        ("SFA:SM_SFA_CombWagon_001", 0, 0, 70, 1.0, []),
        ("SFA:SM_SFA_WoodenLog_002", -40, 520, 20, 0.9, []),
        ("SFA:SM_SFA_WoodenLog_001", 150, 430, -35, 0.9, []),
        ("LIB:SM_Woodlog_01", 190, 250, 60, 1.6, []),
        ("LIB:SM_Woodlog_03", 230, 320, 130, 1.6, []),
        ("SFA:SM_SFA_Box_002", -20, -420, 15, 1.0, [("SFA:SM_SFA_Bucket_001", 30, 10, 0, 1.4), ("DSH:SM_Lamp_001", -40, -20, 0, 1.0)]),
        ("SFA:SM_SFA_Barrel_001", 130, -330, 0, 1.0, []),
    ]},
    {"name": "Market", "anchor": "BW_NPC_Saltmarket", "building": "BW_Dock_0005", "low_trace": True, "items": [
        ("SFA:SM_SFA_Vase_005", 60, -130, 0, 1.5, []), ("SFA:SM_SFA_Vase_011", 20, -170, 40, 1.4, []),
        ("SFA:SM_SFA_Vase_017", 110, -150, 90, 1.6, []), ("SFA:SM_SFA_Vase_002", 60, 140, 0, 1.5, []),
        ("SFA:SM_SFA_Vase_021", 100, 190, 10, 1.4, []), ("LIB:SM_Pot_01", 20, 190, 0, 0.9, []),
        ("LIB:SM_Suitcase_01", 150, -60, 80, 0.8, [("SFA:SM_SFA_MoneyBag_001", 0, 0, 0, 1.6)]),
        ("LIB:SM_Stack", 150, 70, 20, 0.8, []),
    ]},
    {"name": "Lookout", "anchor": "BW_Pirate_Lookout", "building": "BW_Dock_0005", "low_trace": True, "items": [
        ("LIB:SM_Telescope", 120, 60, 0, 1.0, []),
        ("LIB:SM_FishBoard", -60, -150, 90, 1.0, []),
        ("LIB:SM_Bucket", 40, -160, 0, 0.9, []),
        ("LIB:SM_Backpack", -40, 150, 30, 1.0, []),
    ]},
]

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()
actors = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
BASE_TERRAIN = actors["BW_Isle_A"].static_mesh_component
crew = [a.get_actor_location() for a in actors.values() if str(a.get_folder_path()).endswith("Crew")]
meshes = {}


def mesh(key):
    if key not in meshes:
        tag, name = key.split(":")
        found = unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(PACKS[tag], recursive=True)
        path = next(str(d.package_name) for d in found if str(d.asset_name) == name and str(d.asset_class_path.asset_name) == "StaticMesh")
        meshes[key] = unreal.load_asset(path)
    return meshes[key]


def ground(x, y, top):
    """Height of the walkable surface under a point, or None over water or under a roof or prop."""
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, top), unreal.Vector(x, y, -100.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    parts = hit.to_tuple()
    owner = parts[9]
    if not owner or not owner.get_actor_label().startswith(GROUND_PREFIXES) or parts[5].z < 20.0:
        return None
    z = parts[5].z
    if owner.get_actor_label() == DETAIL_LABEL:
        # the detail mesh carries baked tufts and pebbles: stand props on the sand underneath them
        under = BASE_TERRAIN.line_trace_component(unreal.Vector(x, y, top), unreal.Vector(x, y, -100.0), True, False, False)
        if under and z - under[0].z < 80.0:
            z = under[0].z
    return z


def is_free(x, y, z, radius):
    if any(math.hypot(x - c.x, y - c.y) < radius + 70.0 for c in crew):
        return False
    hits = unreal.SystemLibrary.sphere_overlap_actors(
        world, unreal.Vector(x, y, z + radius + 20.0), radius,
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, [])
    return not any(not h.get_actor_label().startswith(GROUND_PREFIXES) for h in hits or [])


def spawn(key, loc, yaw, scale, label):
    m = mesh(key)
    b = m.get_bounds()
    base = (b.origin.z - b.box_extent.z) * scale
    a = eas.spawn_actor_from_object(m, unreal.Vector(loc.x, loc.y, loc.z - min(base, 0.0)), unreal.Rotator(0.0, 0.0, yaw))
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    a.set_folder_path(FOLDER + "/" + label.split("_")[1])
    a.set_actor_label(label)
    return a, loc.z + (b.origin.z + b.box_extent.z) * scale - min(base, 0.0)


def main():
    for a in list(actors.values()):
        if str(a.get_folder_path()).startswith(FOLDER):
            eas.destroy_actor(a)
    placed = skipped = 0
    for cluster in CLUSTERS:
        if "at" in cluster:
            # free-standing cluster: a fixed spot and facing instead of a shopkeeper
            x, y, facing = cluster["at"]
            anchor = unreal.Vector(x, y, ground(x, y, 600.0) or 150.0)
            out = unreal.Vector(math.cos(math.radians(facing)), math.sin(math.radians(facing)), 0.0)
        else:
            anchor = actors[cluster["anchor"]].get_actor_location()
            origin, _ = actors[cluster["building"]].get_actor_bounds(False)
            out = unreal.Vector(anchor.x - origin.x, anchor.y - origin.y, 0.0).normal()
        if cluster.get("low_trace"):
            # on the dock the shopkeeper faces along it: use the dock direction instead
            out = unreal.Vector(math.cos(math.radians(52.0)), math.sin(math.radians(52.0)), 0.0)
        right = unreal.Vector(-out.y, out.x, 0.0)
        out_yaw = math.degrees(math.atan2(out.y, out.x))
        top = anchor.z + (150.0 if cluster.get("low_trace") else 320.0)
        for n, (key, f, r, yaw, scale, kids) in enumerate(cluster["items"]):
            b = mesh(key).get_bounds()
            radius = max(b.box_extent.x, b.box_extent.y) * scale * 0.85
            spot = None
            for dist in SEARCH_RADII:
                for step in range(1 if dist == 0 else 8):
                    ang = math.radians(step * 45.0)
                    x = anchor.x + out.x * f + right.x * r + math.cos(ang) * dist
                    y = anchor.y + out.y * f + right.y * r + math.sin(ang) * dist
                    z = ground(x, y, top)
                    if z is not None and is_free(x, y, z, radius):
                        spot = unreal.Vector(x, y, z)
                        break
                if spot:
                    break
            if not spot:
                print(f"no room: {cluster['name']} {key}")
                skipped += 1
                continue
            name = key.split(":")[1].replace("SM_SFA_", "").replace("SM_", "")
            parent, top_z = spawn(key, spot, out_yaw + yaw, scale, f"PP_{cluster['name']}_{n:02d}_{name}")
            placed += 1
            c, s = math.cos(math.radians(out_yaw + yaw)), math.sin(math.radians(out_yaw + yaw))
            for k, (kid, dx, dy, kyaw, kscale) in enumerate(kids):
                kname = kid.split(":")[1].replace("SM_SFA_", "").replace("SM_", "")
                spawn(kid, unreal.Vector(spot.x + c * dx - s * dy, spot.y + s * dx + c * dy, top_z), out_yaw + yaw + kyaw, kscale,
                      f"PP_{cluster['name']}_{n:02d}{chr(97 + k)}_{kname}")
                placed += 1
    print(f"placed {placed}, skipped {skipped}")


main()
