"""Import a `tools/*.py` module that does `import bpy`, with Blender stubbed out.

`tests/conftest.py`'s `rt` fixture does exactly this for `render_turnaround` and records
why: the repo's older idiom regexes one function out of the source text and execs it,
which works and silently stops covering anything the regex does not reach. This is that
fixture's machinery generalised, so the wave-6 checks can reach every Blender-side tool
rather than the one that already had a fixture — one implementation, not twenty-one.

`main_block` is the second half. A `if __name__ == "__main__":` handler is ordinary code
that never runs under import, so nothing has ever covered one. It is extracted by AST
(never by regex, and never by re-running the module through `runpy`, which would run
`main()` for real against mocks) and executed in the module's own namespace with `main`
replaced by a raiser: what is under test is the handler, not the tool.

Helpers under `tests/` **raise**; they never `assert` — `-O` deletes an `assert` in a
non-plugin helper and `ci.yml`'s `-O` leg would report green over it
(`test_gate_survives_optimize.py::test_no_helper_under_tests_checks_anything_with_assert`).
"""

import ast
import contextlib
import math
import importlib.util
import os
import sys
import types
from unittest import mock

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

#: Every module under `tools/` that imports `bpy`. Built by reading the files, not typed
#: out, so a new Blender tool joins the population the day it lands.
def blender_tools():
    names = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        src = read_source(fn)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "bpy" for a in node.names):
                names.append(fn)
                break
    return names


def read_source(filename):
    with open(os.path.join(TOOLS, filename), encoding="utf-8") as fh:
        return fh.read()


class _BruteForceKDTree:
    """A stand-in for `mathutils.kdtree.KDTree` — exact, and O(n*m).

    `author_walk.gate_a_arrival`'s skin clause does `from mathutils import kdtree` inside
    the function, so the clause cannot be reached at all with `mathutils` merely stubbed.
    The real KDTree is an exact nearest-neighbour structure; over the handful of points a
    unit test hands it, brute force returns the same answer, which is the property the
    clause depends on.
    """

    def __init__(self, size):
        self._pts = []

    def insert(self, co, index):
        self._pts.append((tuple(float(v) for v in co), index))

    def balance(self):
        pass

    def find(self, co):
        probe = tuple(float(v) for v in co)
        if not self._pts:
            return None, None, float("inf")
        best = min(self._pts, key=lambda t: math.dist(t[0], probe))
        return best[0], best[1], math.dist(best[0], probe)


@contextlib.contextmanager
def blender_stubbed():
    """`bpy`, `mathutils` and `bmesh` replaced for the duration."""
    keys = ("bpy", "mathutils", "mathutils.kdtree", "bmesh")
    saved = {k: sys.modules.get(k) for k in keys}
    try:
        sys.modules["bpy"] = mock.MagicMock(name="bpy")
        sys.modules["bmesh"] = mock.MagicMock(name="bmesh")
        mathutils = types.ModuleType("mathutils")
        mathutils.Vector = lambda v: v
        mathutils.Matrix = mock.MagicMock(name="Matrix")
        mathutils.Quaternion = mock.MagicMock(name="Quaternion")
        mathutils.Euler = mock.MagicMock(name="Euler")
        kdtree = types.ModuleType("mathutils.kdtree")
        kdtree.KDTree = _BruteForceKDTree
        mathutils.kdtree = kdtree
        sys.modules["mathutils"] = mathutils
        sys.modules["mathutils.kdtree"] = kdtree
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def load_tool(filename, *, argv=None):
    """The real module object for `tools/<filename>`, imported with Blender stubbed.

    `argv` is installed for the duration of the import because several tools read
    `sys.argv` at module scope.
    """
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    saved_argv = list(sys.argv)
    with blender_stubbed():
        try:
            if argv is not None:
                sys.argv = list(argv)
            path = os.path.join(TOOLS, filename)
            spec = importlib.util.spec_from_file_location(
                "_under_test_" + filename[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        finally:
            sys.argv = saved_argv


def main_block(filename):
    """The compiled `if __name__ == "__main__":` body, or None if the file has none."""
    src = read_source(filename)
    tree = ast.parse(src)
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name) and test.left.id == "__name__"):
            block = ast.Module(body=node.body, type_ignores=[])
            ast.fix_missing_locations(block)
            return compile(block, os.path.join(TOOLS, filename), "exec")
    return None


class _Boom(Exception):
    """Stand-in for whatever blew up inside `main`."""


def exit_code_of_main_block(filename, *, raiser=None, argv=("blender", "-b", "-P", "x"),
                            main_name="main"):
    """Run the tool's `__main__` handler with `main` replaced, and report the exit code.

    Returns `(code, error)` where `code` is the `SystemExit` code the handler produced
    (`None` if the handler exited by falling off the end) and `error` is the exception
    that escaped the handler entirely, if one did — which is the defect
    `rig_character.py:1132` had: a second failure inside the `except` block propagates
    out of the whole `try` statement and `sys.exit` is never reached. Under
    `blender -b -P` that is exit **0**.
    """
    code_obj = main_block(filename)
    if code_obj is None:
        raise ValueError(f"{filename} has no `if __name__ == \"__main__\":` block")
    mod = load_tool(filename, argv=argv)
    if raiser is None:
        def raiser():
            raise _Boom("the tool blew up")
    setattr(mod, main_name, raiser)
    ns = mod.__dict__
    saved_name, saved_argv = ns.get("__name__"), list(sys.argv)
    ns["__name__"] = "__main__"
    with blender_stubbed():
        try:
            sys.argv = list(argv)
            exec(code_obj, ns)
        except SystemExit as exc:
            return exc.code, None
        except BaseException as exc:                                  # noqa: BLE001
            return None, exc
        finally:
            ns["__name__"] = saved_name
            sys.argv = saved_argv
    return None, None
