"""An andon that a caller can disarm by omission (wave-6 core-solvers amend, F-abcb06a8).

CLAUDE.md: a gate lives inside the tool performing the irreversible step and has *no skip
flag*. An optional keyword IS a skip flag — it just costs one fewer character to use.
Wave 3 removed exactly this shape from `assembly.gate_batch_topology` by making
`expected_sources` a required keyword-only argument; this file pins the same removal for
the two that were left.

Both checks here are SOURCE-level as well as behavioural, because the population that
matters is *every call site*: `blender_scene` imports `bpy` at module scope and cannot be
imported by the suite, so its half is read out of the file with `ast` rather than
skipped — a skip here would be the silence the finding is about.
"""

import ast
import json
import os

import pytest

from armature_core import framing
from armature_core.framing import FramingError
from conftest import REPO, TOOLS


def _func(module_relpath, name):
    path = os.path.join(REPO, module_relpath)
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {module_relpath}")


def _call_sites(func_name):
    """(path, lineno, keywords, n_positional) for every call to `func_name` under tools/."""
    out = []
    for root, _dirs, files in os.walk(TOOLS):
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:  # pragma: no cover - a syntax error is another test's job
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                attr = getattr(node.func, "attr", getattr(node.func, "id", None))
                if attr != func_name:
                    continue
                out.append((os.path.relpath(path, REPO).replace("\\", "/"), node.lineno,
                            {k.arg for k in node.keywords}, len(node.args)))
    return out


# ------------------------------------------------ import_glb: the fps andon is required


def test_import_glb_cannot_be_called_without_the_fps_expectation():
    """Measured: `import_glb(path, expected_fps=None)` skipped the check entirely when the
    caller omitted it, and the import proceeded at whatever rate the scene carried. The
    docstring calls this the andon and records what it cost — a 33-key action authored at
    16 fps landing on frames 1..49 at Blender's default 24, a 0-90 degree arm raise
    arriving as 0-60."""
    fn = _func("tools/armature_core/blender_scene.py", "import_glb")
    names = [a.arg for a in fn.args.args]
    kwonly = {a.arg: d for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults)}
    assert "expected_fps" not in names, (
        "expected_fps is still a positional-or-keyword parameter, so it can be omitted")
    assert "expected_fps" in kwonly, "expected_fps is not declared keyword-only"
    assert kwonly["expected_fps"] is None, (
        "expected_fps carries a default, which is what makes the andon optional")


#: The one call site that still omits the fps expectation, measured 2026-09-04. It is
#: outside the core-solvers domain (instruments owns `tools/probe_subject.py`) and is
#: routed there; the correct call is `expected_fps=int(blender_scene.scene_fps())` right
#: after its `reset_scene()`, so the omission becomes a recorded choice. Subset assertion,
#: so the list can only shrink — a NEW bare call site fails this test.
IMPORT_GLB_SITES_WITHOUT_AN_EXPECTATION_ROUTED = {"tools/probe_subject.py"}


def test_every_import_glb_call_site_states_the_rate_it_expects():
    """The family, not the instance. `probe_subject.py:42` called `import_glb(path)` with
    no expectation immediately after `reset_scene()` — harmless there because it reads
    geometry, and proof that nothing anywhere required a caller to arm the andon."""
    sites = _call_sites("import_glb")
    assert len(sites) >= 10, sites
    bare = {p for p, ln, kw, npos in sites if "expected_fps" not in kw and npos < 2}
    assert bare <= IMPORT_GLB_SITES_WITHOUT_AN_EXPECTATION_ROUTED, (
        f"a call site disarms the fps andon by omission: {sorted(bare)}; routed and "
        f"expected to shrink, never to grow: "
        f"{sorted(IMPORT_GLB_SITES_WITHOUT_AN_EXPECTATION_ROUTED)}")


# --------------------------------------- load_pinned_camera: expect is not optional


def test_load_pinned_camera_refuses_to_run_with_no_expectation(tmp_path):
    """`expect=None` was the escape hatch, and `tests/test_pinned_camera.py` named it one.
    Pinning a camera skips the framing solve and therefore its gate; a record pinned at a
    different azimuth or lens projects a plausible skeleton of the same body seen from
    somewhere else and every downstream check passes on it."""
    path = os.path.join(str(tmp_path), "prov.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"camera": {"target": [0.0, 0.0, 0.0], "radius": 4.0,
                              "azimuth_deg": 225.0}}, fh)
    with pytest.raises(TypeError):
        framing.load_pinned_camera(path)
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(path, None)
    assert "andon" in str(exc.value) or "no expectation" in str(exc.value)
    with pytest.raises(FramingError):
        framing.load_pinned_camera(path, {})


def test_load_pinned_camera_still_loads_when_the_expectation_is_stated(tmp_path):
    path = os.path.join(str(tmp_path), "prov.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"camera": {"target": [0.0, 0.0, 0.0], "radius": 4.0,
                              "azimuth_deg": 225.0}}, fh)
    target, radius = framing.load_pinned_camera(path, {"azimuth_deg": 225.0})
    assert target == (0.0, 0.0, 0.0) and radius == pytest.approx(4.0)


def test_every_load_pinned_camera_call_site_states_its_expectation():
    sites = _call_sites("load_pinned_camera")
    assert len(sites) >= 2, sites
    bare = [(p, ln) for p, ln, kw, npos in sites if "expect" not in kw and npos < 2]
    assert bare == [], f"call sites that disarm the pinned-camera andon: {bare}"
