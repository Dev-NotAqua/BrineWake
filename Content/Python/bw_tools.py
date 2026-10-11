"""Brinewake editor toolset: lets the editor MCP run pipeline scripts with the full `unreal` module.

Registered from init_unreal.py. Scripts share one globals dict, so helpers defined by one
call stay available to the next.
"""

import contextlib
import io
import traceback

import toolset_registry
import unreal

_MAX_OUTPUT = 60000
_GLOBALS = {"unreal": unreal, "__name__": "__bw__"}


def _run(code: str, name: str) -> str:
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, name, "exec"), _GLOBALS)
    except Exception:  # report the failure to the caller instead of losing the output so far
        buf.write("\n" + traceback.format_exc())
    out = buf.getvalue()
    return out[-_MAX_OUTPUT:] if len(out) > _MAX_OUTPUT else out


@unreal.uclass()
class BWTools(unreal.ToolsetDefinition):
    """Brinewake project tools: run editor Python for the asset and level pipeline."""

    @toolset_registry.tool_call
    @staticmethod
    def run_file(path: str) -> str:
        """Run a Python script file inside the editor with the full unreal module.

        Args:
            path: Absolute path of the script on disk.

        Returns:
            Everything the script printed, followed by the traceback if it raised.
        """
        with open(path, encoding="utf-8") as f:
            return _run(f.read(), path)

    @toolset_registry.tool_call
    @staticmethod
    def run_python(code: str) -> str:
        """Run a short Python snippet inside the editor with the full unreal module.

        Args:
            code: Python source to execute.

        Returns:
            Everything the snippet printed, followed by the traceback if it raised.
        """
        return _run(code, "<bw>")
