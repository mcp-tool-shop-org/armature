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
import subprocess
import sys
import textwrap

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
    with pytest.raises(FramingError,
                       match=r"load_pinned_camera was called with no expectation to"):
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


# ------------------------------------------- and none of the new refusals is an `assert`

PROBE = textwrap.dedent(
    """
    import json, sys, types
    sys.path.insert(0, sys.argv[1])

    import numpy as np
    from armature_core import parts, walk, landmarks, glb, assembly as AS
    from armature_core import turnaround as TA

    asserts_active = False
    try:
        assert False
    except AssertionError:
        asserts_active = True

    for _n in ("bpy", "mathutils"):
        if _n not in sys.modules:
            _s = types.ModuleType(_n)
            _s.context = types.SimpleNamespace()
            _s.data = types.SimpleNamespace()
            _s.ops = types.SimpleNamespace()
            sys.modules[_n] = _s
    from armature_core import blender_scene as BS

    NAMES = ["chest", "neck", "head"]

    def _fp():
        return {n: {"n_verts": 4, "n_faces": 2,
                    "positions": np.zeros((4, 3))} for n in NAMES}

    def parts_determinism_empty():
        parts.gate_parts_determinism({}, {}, 1.0)

    def parts_determinism_disjoint():
        parts.gate_parts_determinism(_fp(), {"other": _fp()["chest"]}, 1.0)

    def parts_accounting_empty():
        parts.gate_parts_accounting(np.array([], dtype=int), 0, [])

    def turn_empty_set():
        TA.gate_set_distinct([], 0)

    def walk_cadence():
        p = walk.GaitParams(n_walk=2, n_decel=2, steps=30)
        _speed, phase, _omega = walk._phase_schedule(p)
        walk.gate_cadence_is_representable(phase, p.stance_frac, where="probe")

    def walk_missing_landmark():
        lm = {n: [0.0, 0.0, float(i)] for i, n in enumerate(walk.REQUIRED_LANDMARKS)}
        del lm["head_top"]
        walk.Performer(lm, -1.0, 1.0)

    def facing_tie():
        pts = [(0.0, -0.05, 0.01), (0.0, 0.05, 0.01), (0.0, 0.0, 0.08),
               (0.0, -0.08, 0.95), (0.0, 0.08, 0.95)]
        landmarks.facing(np.array(pts, dtype=np.float64), 0.06, 1.0, 0.0)

    def facing_head_outvotes():
        pts = [(0.0, -0.011, 0.01), (0.0, 0.010, 0.01), (0.0, 0.0, 0.08),
               (0.0, -0.02, 0.95), (0.0, -0.02, 0.95), (0.0, 0.20, 0.95)]
        landmarks.facing(np.array(pts, dtype=np.float64), 0.06, 1.0, 0.0)

    def compositor_no_link():
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers", [])

    def compositor_wrong_socket():
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                  [("Render Layers", "Alpha")])

    def union_single_use_iterator():
        BS.union_sphere(iter([np.zeros((1, 3))]))

    CASES = {
        "parts_determinism_empty": parts_determinism_empty,
        "parts_determinism_disjoint": parts_determinism_disjoint,
        "parts_accounting_empty": parts_accounting_empty,
        "turn_empty_set": turn_empty_set,
        "walk_cadence": walk_cadence,
        "walk_missing_landmark": walk_missing_landmark,
        "facing_tie": facing_tie,
        "facing_head_outvotes": facing_head_outvotes,
        "compositor_no_link": compositor_no_link,
        "compositor_wrong_socket": compositor_wrong_socket,
        "union_single_use_iterator": union_single_use_iterator,
    }

    out = {"asserts_active": asserts_active, "raised": {}}
    for name, fn in CASES.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except BaseException as exc:
            out["raised"][name] = type(exc).__name__
    print("AMEND6 " + json.dumps(out))
    """
)


def _run_probe(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"w6_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    assert proc.returncode == 0, proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("AMEND6 ")]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[-1][len("AMEND6 "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_refusal_added_in_this_amend_survives_optimization(tmp_path, flag, env_var,
                                                                 label):
    """CLAUDE.md: gates raise, never `assert` — an `assert` is deleted by `-O` or
    `PYTHONOPTIMIZE=1`, and 87 of facet's andons turned out to be removable by an
    environment variable. Every refusal added in this amend MUTATES the protected thing
    and must still fire with assertions gone."""
    #: The exact exception each mutation must produce. Naming the class rather than
    #: accepting "something raised" is the difference between proving the andon fired and
    #: proving a typo did.
    expected = {
        "parts_determinism_empty": "GatePartsDeterminism",
        "parts_determinism_disjoint": "GatePartsDeterminism",
        "parts_accounting_empty": "GatePartsAccounting",
        "turn_empty_set": "TurnaroundGate",
        "walk_cadence": "WalkError",
        "walk_missing_landmark": "WalkError",
        "facing_tie": "FacingGate",
        "facing_head_outvotes": "FacingGate",
        "compositor_no_link": "CompositorWiring",
        "compositor_wrong_socket": "CompositorWiring",
        "union_single_use_iterator": "TypeError",
    }
    res = _run_probe(tmp_path, flag=flag, env_var=env_var)
    assert set(res["raised"]) == set(expected), res["raised"]
    for name, want in expected.items():
        assert res["raised"][name] == want, (
            f"{label}/{name}: expected {want}, got {res['raised'][name]}")


def test_the_optimization_actually_took_effect(tmp_path):
    """Otherwise the parametrisation above is three copies of the same run."""
    assert _run_probe(tmp_path, flag=False)["asserts_active"] is True
    assert _run_probe(tmp_path, flag=True)["asserts_active"] is False
    assert _run_probe(tmp_path, env_var=True)["asserts_active"] is False


def test_none_of_the_modules_this_amend_touched_uses_a_bare_assert():
    """Source-level, because `-O` deletes asserts and this repo has been bitten."""
    for name in ("assembly.py", "blender_scene.py", "framing.py", "glb.py", "joints.py",
                 "landmarks.py", "parts.py", "turnaround.py", "walk.py"):
        path = os.path.join(TOOLS, "armature_core", name)
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                assert not line.strip().startswith("assert "), f"{name}:{i} {line!r}"
