"""Swap the low-poly kit grass, bushes, flowers, jungle trees and pebbles on Gullrest for the
StyleHex forest pack, as painted foliage instances (run inside the editor: py.py ue_foliage.py).

Rerunnable: the kit actors it removes are recorded in kit/foliage_sources.json the first time and
every run rebuilds the instances from that file.
"""
import json
import math
import os
import random

import unreal

PACK = "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes"
FT_DIR = "/Game/Brinewake/Foliage"
GRASS_MI = "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Materials/Mat_Foliage/MI_Fol_Grass_Atlas"
SOURCES = os.path.join(unreal.Paths.project_dir(), "Tools", "mcp", "kit", "foliage_sources.json")
TERRAIN_LABELS = {"BW_Isle_A", "BW_Isle_A_Detail"}
SEA_LEVEL_MARGIN = 25.0

# mesh -> (subfolder, cull start, cull end, cast shadow, collision profile)
TYPES = {
    "SM_Fol_Grass_Clump_1": ("Foliage", 5000, 8000, False, "NoCollision"),
    "SM_Fol_Grass_Clump_2": ("Foliage", 5000, 8000, False, "NoCollision"),
    "SM_Fol_Grass_Clump_3": ("Foliage", 5000, 8000, False, "NoCollision"),
    "SM_Fol_Grass_Clump_4": ("Foliage", 5000, 8000, False, "NoCollision"),
    "SM_Fol_Grass_Clump_5": ("Foliage", 5000, 8000, False, "NoCollision"),
    "SM_Fol_Flower_Clump_1": ("Foliage", 4500, 7000, False, "NoCollision"),
    "SM_Fol_Flower_Clump_2": ("Foliage", 4500, 7000, False, "NoCollision"),
    "SM_Fol_Flower_Clump_3": ("Foliage", 4500, 7000, False, "NoCollision"),
    "SM_Fol_Bush_1": ("Foliage", 14000, 20000, True, "NoCollision"),
    "SM_Fol_Bush_2": ("Foliage", 14000, 20000, True, "NoCollision"),
    "SM_Stone_1": ("Stones", 9000, 13000, True, "NoCollision"),
    "SM_Stone_2": ("Stones", 9000, 13000, True, "NoCollision"),
    "SM_Stone_3": ("Stones", 0, 0, True, "BlockAll"),
    "SM_Stone_Boulder_1": ("Stones", 0, 0, True, "BlockAll"),
    "SM_Tree_Birch_1": ("Trees", 0, 0, True, "BlockAll"),
    "SM_Tree_Birch_2": ("Trees", 0, 0, True, "BlockAll"),
    "SM_Tree_Broadleaf_1": ("Trees", 0, 0, True, "BlockAll"),
    "SM_Tree_Broadleaf_2": ("Trees", 0, 0, True, "BlockAll"),
}

# kit mesh -> list of (pack meshes, count, scatter radius cm, scale min, scale max)
RECIPES = {
    "SM_BW_Grass_A": [(["SM_Fol_Grass_Clump_1", "SM_Fol_Grass_Clump_2"], 5, 75, 1.0, 1.5)],
    "SM_BW_Grass_B": [(["SM_Fol_Grass_Clump_1", "SM_Fol_Grass_Clump_2", "SM_Fol_Grass_Clump_4"], 8, 120, 1.1, 1.7)],
    "SM_BW_Grass_Short": [(["SM_Fol_Grass_Clump_3", "SM_Fol_Grass_Clump_2"], 5, 80, 0.9, 1.3)],
    "SM_BW_Grass_Tall": [(["SM_Fol_Grass_Clump_4", "SM_Fol_Grass_Clump_5", "SM_Fol_Grass_Clump_1"], 9, 140, 1.6, 2.4)],
    "SM_BW_Flowers_Mixed": [(["SM_Fol_Flower_Clump_1", "SM_Fol_Flower_Clump_2", "SM_Fol_Flower_Clump_3"], 6, 70, 1.4, 2.2)],
    "SM_BW_Flowers_Red": [(["SM_Fol_Flower_Clump_1", "SM_Fol_Flower_Clump_3"], 6, 70, 1.4, 2.2)],
    "SM_BW_Flowers_Blue": [(["SM_Fol_Flower_Clump_2", "SM_Fol_Flower_Clump_3"], 6, 70, 1.4, 2.2)],
    "SM_BW_Bush_A": [(["SM_Fol_Bush_1"], 1, 0, 1.0, 1.35)],
    "SM_BW_Bush_B": [(["SM_Fol_Bush_2"], 1, 0, 0.9, 1.25)],
    "SM_BW_Bush_C": [(["SM_Fol_Bush_1"], 1, 0, 0.6, 0.85)],
    "SM_BW_Hedge_Long": [(["SM_Fol_Bush_2"], 1, 0, 0.8, 1.0), (["SM_Fol_Bush_1"], 2, 150, 0.8, 1.1)],
    "SM_BW_Tree_Jungle_A": [(["SM_Tree_Broadleaf_1", "SM_Tree_Broadleaf_2"], 1, 0, 0.75, 0.95)],
    "SM_BW_Tree_Jungle_C": [(["SM_Tree_Broadleaf_2", "SM_Tree_Birch_1"], 1, 0, 0.6, 0.8)],
    "SM_BW_Pebbles_A": [(["SM_Stone_1", "SM_Stone_2"], 4, 110, 0.25, 0.55)],
    "SM_BW_Pebbles_B": [(["SM_Stone_1", "SM_Stone_2"], 3, 110, 0.25, 0.55), (["SM_Stone_3"], 1, 60, 0.35, 0.6)],
}
EXTRA_TREES = 22
EXTRA_TREE_MESHES = ["SM_Tree_Broadleaf_1", "SM_Tree_Broadleaf_2", "SM_Tree_Broadleaf_2", "SM_Tree_Birch_2"]
EXTRA_TREE_HOSTS = {"SM_BW_Bush_B", "SM_BW_Bush_A", "SM_BW_Fern_B", "SM_BW_BigLeaf_A"}
UPRIGHT = {"Trees"}
COVERING_FOLDERS = {"Outpost", "Rocks", "SetPieces", "Dressing", "Ships", "SeaRocks"}
BLOCKING_FOLDERS = {"Outpost", "Ships", "SetPieces", "Dressing", "Crew", "Lights"}

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()
rng = random.Random(1107)
TERRAIN = [a.static_mesh_component for a in eas.get_all_level_actors() if a.get_actor_label() in TERRAIN_LABELS]


def mesh_name(actor):
    comp = actor.static_mesh_component
    return comp.static_mesh.get_name() if comp and comp.static_mesh else ""


def foliage_type(name):
    path = f"{FT_DIR}/FT_{name}"
    ft = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if not ft:
        ft = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "FT_" + name, FT_DIR, unreal.FoliageType_InstancedStaticMesh, unreal.FoliageType_InstancedStaticMeshFactory())
    _, cull_min, cull_max, shadow, profile = TYPES[name]
    ft.set_editor_property("mesh", unreal.load_asset(f"{PACK}/{'Foliage' if 'Fol_' in name else 'Stones' if 'Stone' in name else 'Trees'}/{name}"))
    ft.set_editor_property("cull_distance", unreal.Int32Interval(cull_min, cull_max))
    ft.set_editor_property("cast_shadow", shadow)
    ft.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    body = ft.get_editor_property("body_instance")
    body.set_editor_property("collision_profile_name", profile)
    ft.set_editor_property("body_instance", body)
    return ft


def grass_material():
    """Copy of the pack grass material that takes its colour from parameters: the pack version reads
    a runtime virtual texture of the terrain, which this level does not have, and renders near-black."""
    path = f"{FT_DIR}/MI_BW_Grass"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.duplicate_asset(GRASS_MI, path)
    mi = unreal.load_asset(path)
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_static_switch_parameter_value(mi, "Use RVT as Base Color?", False)
    mel.set_material_instance_vector_parameter_value(mi, "Base Color", unreal.LinearColor(0.07, 0.26, 0.04, 1.0))
    mel.set_material_instance_vector_parameter_value(mi, "Top Color", unreal.LinearColor(0.30, 0.60, 0.07, 1.0))
    mel.update_material_instance(mi)
    return mi


def ground(x, y):
    """Terrain height and normal under a point, or None off the island or under a building or rock."""
    start, end = unreal.Vector(x, y, 9000.0), unreal.Vector(x, y, -300.0)
    best = None
    for comp in TERRAIN:
        found = comp.line_trace_component(start, end, True, False, False)
        if found and (not best or found[0].z > best[0].z):
            best = found
    if not best or best[0].z < SEA_LEVEL_MARGIN:
        return None
    hit = unreal.SystemLibrary.line_trace_single(
        world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if hit:
        parts = hit.to_tuple()
        above = parts[9]
        if above and parts[5].z > best[0].z + 30.0 and str(above.get_folder_path()).split("/")[-1] in COVERING_FOLDERS:
            return None
    return best[0], best[1]


def instance(x, y, scale, upright, max_slope_z):
    g = ground(x, y)
    if not g or g[1].z < max_slope_z:
        return None
    point, normal = g
    yaw = rng.uniform(0.0, 360.0)
    if upright:
        rot = unreal.Rotator(0.0, 0.0, yaw)
    else:
        # lean halfway toward the slope so clumps sit on it without looking combed flat
        lean = unreal.Vector(normal.x * 0.5, normal.y * 0.5, 1.0).normal()
        rot = unreal.MathLibrary.make_rot_from_zx(lean, unreal.Vector(math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.0))
    return unreal.Transform(unreal.Vector(point.x, point.y, point.z - 2.0), rot, unreal.Vector(scale, scale, scale))


def kit_actors():
    return [a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.StaticMeshActor) and str(a.get_folder_path()).startswith("Island/")
            and (mesh_name(a) in RECIPES or mesh_name(a) in EXTRA_TREE_HOSTS)]


def load_sources():
    """Kit plants to replace. The first run records them; later runs read the record back."""
    if os.path.exists(SOURCES):
        with open(SOURCES, encoding="utf-8") as f:
            return json.load(f)
    rows = []
    for a in kit_actors():
        loc, rot, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        rows.append({"mesh": mesh_name(a), "label": a.get_actor_label(), "folder": str(a.get_folder_path()),
                     "x": loc.x, "y": loc.y, "z": loc.z, "yaw": rot.yaw, "scale": sc.x})
    os.makedirs(os.path.dirname(SOURCES), exist_ok=True)
    with open(SOURCES, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    return rows


def blockers():
    """Circles (x, y, radius) the extra trees must stay out of: buildings, ships, palms, set pieces."""
    out = []
    for a in eas.get_all_level_actors():
        leaf = str(a.get_folder_path()).split("/")[-1]
        is_palm = isinstance(a, unreal.StaticMeshActor) and "Palm" in mesh_name(a)
        if leaf in BLOCKING_FOLDERS or is_palm:
            origin, ext = a.get_actor_bounds(False)
            out.append((origin.x, origin.y, max(ext.x, ext.y) + 350.0))
    return out


def main():
    sources = load_sources()
    actors = [a for a in kit_actors() if mesh_name(a) in RECIPES]
    types = {name: foliage_type(name) for name in TYPES}
    grass = grass_material()
    for name, ft in types.items():
        if "Grass" in name:
            ft.set_editor_property("override_materials", [grass])
    batches = {name: [] for name in TYPES}

    for row in sources:
        for meshes, count, radius, smin, smax in RECIPES.get(row["mesh"], []):
            for _ in range(count):
                ang, dist = rng.uniform(0, math.tau), radius * math.sqrt(rng.random())
                name = rng.choice(meshes)
                upright = TYPES[name][0] in UPRIGHT
                t = instance(row["x"] + math.cos(ang) * dist, row["y"] + math.sin(ang) * dist,
                             rng.uniform(smin, smax) * max(0.8, min(1.3, row["scale"])), upright, 0.55 if not upright else 0.7)
                if t:
                    batches[name].append(t)

    blocked = blockers()
    trees = [(t.translation.x, t.translation.y) for n in batches if TYPES[n][0] == "Trees" for t in batches[n]]
    hosts = [r for r in sources if r["mesh"] in EXTRA_TREE_HOSTS]
    rng.shuffle(hosts)
    added = 0
    for row in hosts:
        if added >= EXTRA_TREES:
            break
        x, y = row["x"], row["y"]
        if any(math.hypot(x - bx, y - by) < br for bx, by, br in blocked) or any(math.hypot(x - tx, y - ty) < 650.0 for tx, ty in trees):
            continue
        t = instance(x, y, rng.uniform(0.6, 0.95), True, 0.8)
        if t:
            batches[rng.choice(EXTRA_TREE_MESHES)].append(t)
            trees.append((x, y))
            added += 1

    for name, transforms in batches.items():
        unreal.InstancedFoliageActor.remove_all_instances(world, types[name])
        if transforms:
            unreal.InstancedFoliageActor.add_instances(world, types[name], transforms)
        print(f"{name}: {len(transforms)}")
    for a in actors:
        eas.destroy_actor(a)
    # instances added from script are not drawn until the foliage trees are rebuilt
    unreal.SystemLibrary.execute_console_command(world, "foliage.RebuildFoliageTrees")
    unreal.EditorAssetLibrary.save_directory(FT_DIR, only_if_is_dirty=True)
    print(f"sources {len(sources)}, kit actors removed {len(actors)}, extra trees {added}")


main()
