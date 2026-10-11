import unreal

try:
    import bw_tools

    unreal.ToolsetRegistry.register_toolset_class(bw_tools.BWTools)
    unreal.log("[BWTools] toolset registered")
except Exception as exc:  # the editor must still start if the toolset registry is unavailable
    unreal.log_warning(f"[BWTools] toolset not registered: {exc}")
