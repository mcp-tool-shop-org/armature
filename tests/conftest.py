import importlib.util
import os
import sys
import types
from unittest import mock

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get(
    "ARMATURE_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)


@pytest.fixture(scope="module")
def rt():
    """`render_turnaround`, imported with Blender stubbed out.

    Written for S04's ortho tests and moved here when S05's pin tests needed the same
    stub — one copy, not two that can drift apart. The module does `import bpy` at the
    top, so the suite cannot import it the ordinary way. The repo's older idiom
    (`test_turnaround.py`, `test_framing.py`) regexes one function out of the source text
    and execs it, which works and silently stops covering anything the regex does not
    reach. Stubbing the two modules Blender owns and importing the real file covers
    `parse_args`, both solves, the manifest's scale record and the module constants at
    once, and it fails loudly if the import surface changes.
    """
    saved = {k: sys.modules.get(k) for k in ("bpy", "mathutils")}
    sys.modules["bpy"] = mock.MagicMock(name="bpy")
    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = lambda v: v
    mathutils.Matrix = mock.MagicMock(name="Matrix")
    sys.modules["mathutils"] = mathutils
    try:
        path = os.path.join(TOOLS, "render_turnaround.py")
        spec = importlib.util.spec_from_file_location("_rt_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
