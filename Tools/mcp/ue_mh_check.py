"""MetaHuman readiness check (run inside the editor: py.py ue_mh_check.py [login]).

Reports what the MetaHuman character pipeline still needs, and once the Creator Core Data is
installed writes the catalogue of presets, grooms and clothing to kit/mh_catalog.json.
Pass "login" to start the Epic sign-in that cloud rigging needs (it opens the browser).
"""
import json
import os
import sys

import unreal

OPTIONAL = "/MetaHumanCharacter/Optional"
CATALOG = os.path.join(unreal.Paths.project_dir(), "Tools", "mcp", "kit", "mh_catalog.json")
PROBE_DIR = "/Game/Brinewake/MetaHumans/_Probe"

subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
installed = unreal.MetaHumanGeneratorSubsystemWrapper.is_optional_content_installed()
print("MetaHuman Creator plugin:", "on" if subsystem else "OFF")
print("Creator Core Data:", "installed" if installed else "MISSING (Epic Games Launcher > Unreal Engine > Library > 5.8 > Options)")

if installed:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    catalog = {}
    for data in registry.get_assets_by_path(OPTIONAL, recursive=True):
        kind = str(data.asset_class_path.asset_name)
        if kind in ("MetaHumanCharacter", "MetaHumanWardrobeItem"):
            folder = str(data.package_path)[len(OPTIONAL) + 1:]
            catalog.setdefault(kind, {}).setdefault(folder, []).append(str(data.asset_name))
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=1)
    for kind, folders in catalog.items():
        for folder, names in sorted(folders.items()):
            print(f"  {kind} {folder}: {len(names)}")
    print("catalogue written to", CATALOG)

if "login" in sys.argv[1:] or globals().get("MH_LOGIN"):
    # A rig request on a throwaway character is the only scripted way to raise the sign-in.
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    probe = tools.create_asset("MH_Probe", PROBE_DIR, unreal.MetaHumanCharacter, unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
    if subsystem.try_add_object_to_edit(probe):
        request = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        request.blocking = False
        request.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
        subsystem.request_auto_rigging(probe, request)
        print("sign-in requested: approve it in the browser within 10 minutes")
