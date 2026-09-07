"""G1 must survive `-O` and `PYTHONOPTIMIZE=1`.

87 of facet's ANDONs turned out to be removable by an environment variable. This is
the test that says do not add the 88th. It drives **the real write path**
(`stage_render.run_export`), not the gate function in isolation — a gate that raises
correctly but is never reached is not a gate.

It also checks that the output directory does not exist afterwards: G1 promises to
raise *before any frame is written*, and "before" is a claim about ordering that only
an on-disk check can falsify.
"""

import os
import subprocess
import sys
import textwrap

import pytest

from conftest import TOOLS

PROBE = textwrap.dedent(
    """
    import json, os, sys
    sys.path.insert(0, sys.argv[1])
    out_dir = sys.argv[2]
    case = sys.argv[3]

    import stage_render
    from armature_core.errors import G1GeneratorLegality

    asset = os.path.join(out_dir + "_asset.glb")
    with open(asset, "wb") as fh:
        fh.write(b"not-a-real-glb")

    bad = {
        "width":  dict(width=1020, height=768, count=33),
        "frames": dict(width=512,  height=768, count=80),
        "unknown_generator": dict(width=512, height=768, count=33),
    }[case]

    # `unknown_generator`: shotspec's unified table admits Gate L family names
    # (`wan`) that are NOT G1 profiles. A totally unknown string is SpecError
    # before G1 arms; `wan` reaches G1 and raises `unknown_generator_profile`.
    spec = {
        "spec_version": 1,
        "name": "optimize-probe",
        "generator": "wan" if case == "unknown_generator" else "wan-vace",
        "asset": {"path": asset},
        "resolution": {"width": bad["width"], "height": bad["height"]},
        "frames": {"count": bad["count"], "fps": 16},
        "channels": ["mask"],
    }
    from armature_core import shotspec
    spec = shotspec.normalise_spec(spec)

    result = {"optimize_flag": sys.flags.optimize,
              "asserts_active": __debug__}
    try:
        stage_render.run_export(spec, out_dir)
        result["outcome"] = "NO_RAISE"
    except G1GeneratorLegality as exc:
        result["outcome"] = "G1_RAISED"
        result["message"] = str(exc)
    except BaseException as exc:
        result["outcome"] = "WRONG_ERROR"
        result["message"] = f"{type(exc).__name__}: {exc}"
    result["out_dir_exists"] = os.path.exists(out_dir)
    print("RESULT " + json.dumps(result))
    """
)


def _run(tmp_path, case, *, flag=False, env_var=False):
    script = tmp_path / "probe.py"
    script.write_text(PROBE, encoding="utf-8")
    out_dir = str(tmp_path / f"run_{case}_{int(flag)}_{int(env_var)}")

    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"

    cmd = [sys.executable]
    if flag:
        cmd.append("-O")
    cmd += [str(script), TOOLS, out_dir, case]

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT ")]
    assert line, proc.stdout + proc.stderr
    import json

    return json.loads(line[-1][len("RESULT "):])


@pytest.mark.parametrize("case", ["width", "frames", "unknown_generator"])
@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_g1_raises_under_optimization(tmp_path, case, flag, env_var, label):
    res = _run(tmp_path, case, flag=flag, env_var=env_var)
    assert res["outcome"] == "G1_RAISED", f"{label}/{case}: {res}"
    assert res["out_dir_exists"] is False, (
        f"{label}/{case}: G1 promises to raise before any frame is written, but the "
        f"output directory exists"
    )


STARTFRAME_PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from armature_core import startframe as SF

    OK = dict(void_vs_plate_255=0.4, plate_vs_flat_255=61.0, transparent_fraction=0.296,
              why="a reason", tol_255=2.0, min_separation_255=4.0)
    cases = {
        "alpha_opaque":     lambda: SF.gate_alpha(0.0, (0.0, 0.0, 0.0), "why"),
        "alpha_all_clear":  lambda: SF.gate_alpha(1.0, (0.0, 0.0, 0.0), "why"),
        "whole_cut":        lambda: SF.gate_whole(
                                {"x0": -2.0, "x1": 520.0, "y0": 20.0, "y1": 450.0,
                                 "n_behind": 0, "n_points": 9}, 832, 480, 8),
        "backdrop_unwired": lambda: SF.gate_backdrop(**dict(OK, void_vs_plate_255=61.0)),
        "backdrop_vacuous": lambda: SF.gate_backdrop(**dict(OK, plate_vs_flat_255=0.0)),
        "backdrop_no_void": lambda: SF.gate_backdrop(**dict(OK, transparent_fraction=0.0)),
        "backdrop_no_why":  lambda: SF.gate_backdrop(**dict(OK, why=None)),
        "cover_degenerate": lambda: SF.cover_fit(0, 480, 1024, 576),
    }
    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__, "raised": {}}
    for name, fn in cases.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except SF.GateFailure:
            out["raised"][name] = "RAISED"
        except BaseException as exc:
            out["raised"][name] = f"WRONG_ERROR:{type(exc).__name__}"
    print("STARTFRAME " + json.dumps(out))
    """
)


def _run_startframe(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"sf_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(STARTFRAME_PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("STARTFRAME ")]
    assert line, proc.stdout + proc.stderr
    import json

    return json.loads(line[-1][len("STARTFRAME "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_the_start_frame_andons_all_survive_optimization(tmp_path, flag, env_var, label):
    """THE ALPHA LAW's andons and E12's Gate BACKDROP, every clause, under every form of
    optimization. 87 of facet's ANDONs turned out to be removable by an environment
    variable; each clause below is a way a start frame conditions a whole generation on the
    wrong picture while every other check passes, so none of them may be an `assert`."""
    res = _run_startframe(tmp_path, flag=flag, env_var=env_var)
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_startframe_optimization_actually_took_effect(tmp_path):
    """Same guard as below, for the same reason: a green sweep under an -O that never
    applied is a check that cannot fail."""
    assert _run_startframe(tmp_path, flag=False)["asserts_active"] is True
    assert _run_startframe(tmp_path, flag=True)["asserts_active"] is False
    assert _run_startframe(tmp_path, env_var=True)["asserts_active"] is False


def test_the_optimization_actually_took_effect(tmp_path):
    """Guard against a green result that proves nothing because -O never applied —
    a check that cannot fail is not a check."""
    plain = _run(tmp_path, "width", flag=False, env_var=False)
    flagged = _run(tmp_path, "width", flag=True, env_var=False)
    env = _run(tmp_path, "width", flag=False, env_var=True)

    assert plain["asserts_active"] is True and plain["optimize_flag"] == 0
    assert flagged["asserts_active"] is False and flagged["optimize_flag"] >= 1
    assert env["asserts_active"] is False and env["optimize_flag"] >= 1


ROUTE_PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from armature_core import route_gates as RG

    def graph(top=(), sub=()):
        return {"nodes": list(top),
                "definitions": {"subgraphs": [{"id": "sg-1", "name": "T2V",
                                               "nodes": list(sub)}]} if sub else {}}

    def sampler(i, seed, control):
        return {"id": i, "type": "KSamplerAdvanced",
                "widgets_values": ["enable", seed, control, 4, 1, "euler", "simple",
                                   0, 2, "enable"]}

    def latent(i, w, h, n):
        return {"id": i, "type": "EmptyHunyuanLatentVideo", "widgets_values": [w, h, n, 1]}

    def loader(i, f, cls="UNETLoader"):
        return {"id": i, "type": cls, "widgets_values": [f, "default"]}

    BASE = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
    EXCLUDED = "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors"
    CLEAN = [loader(1, BASE), sampler(2, 12345, "fixed"), latent(3, 832, 480, 65)]

    cases = {
        "route_excluded_lora_hidden_in_a_subgraph": lambda: RG.verify(graph(
            top=[latent(3, 832, 480, 65), sampler(2, 1, "fixed")],
            sub=[loader(83, EXCLUDED, cls="LoraLoaderModelOnly")])),
        "route_randomising_seed": lambda: RG.verify(graph(
            top=[loader(1, BASE), sampler(2, 5, "randomize"), latent(3, 832, 480, 65)])),
        "route_frame_legality_indeterminate": lambda: RG.verify(graph(
            top=[loader(1, BASE), sampler(2, 7, "fixed")])),
        "route_illegal_frame": lambda: RG.verify(graph(
            top=[loader(1, BASE), sampler(2, 7, "fixed"), latent(3, 833, 480, 64)])),
        "pair_unknown_conditioning_class": lambda: RG.verify(graph(
            top=CLEAN + [{"id": 9, "type": "WanSomethingNobodyFiledToVideo"}])),
        "pair_conditioning_against_a_model_with_no_channel": lambda: RG.verify(graph(
            top=CLEAN + [{"id": 9, "type": "WanVaceToVideo"}])),
        "pair_no_readable_diffusion_model_at_all": lambda: RG.verify(graph(
            top=[sampler(2, 1, "fixed"), latent(3, 832, 480, 65),
                 {"id": 9, "type": "WanVaceToVideo"}])),
        "pairing_called_directly": lambda: RG.pairing(graph(
            top=CLEAN + [{"id": 9, "type": "WanVaceToVideo"}])),
    }

    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__, "raised": {}}
    for name, fn in cases.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except (RG.RouteGate, RG.PairGate) as exc:
            out["raised"][name] = "RAISED:" + exc.gate
        except BaseException as exc:
            out["raised"][name] = "WRONG_ERROR:" + type(exc).__name__

    # The clean graph must still PASS, or a green sweep above would be a gate that
    # refuses everything rather than a gate that refuses the right things.
    try:
        ev = RG.verify(graph(top=CLEAN))
        out["clean"] = "PASS" if ev["frame_legality"][0]["legal"] else "WRONG_VERDICT"
    except BaseException as exc:
        out["clean"] = "RAISED:" + type(exc).__name__
    print("ROUTE " + json.dumps(out))
    """
)


def _run_route(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"route_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(ROUTE_PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("ROUTE ")]
    assert line, proc.stdout + proc.stderr
    import json

    return json.loads(line[-1][len("ROUTE "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_gates_ROUTE_and_PAIR_survive_optimization(tmp_path, flag, env_var, label):
    """The two gates every submitted graph passes before Gates S and L arm.

    `route_gates.py` carries 60 raises across Gates ROUTE and PAIR (57 until wave
    12's core-gates amend added `unreadable_node`,
    `uncredited_conditional_component` and `attribution_entry_for`'s refusal; the
    three have their own `-O` receipt in `tests/test_amend_w12_core_gates.py`) and
    had no `-O`
    receipt, while G1 and the start-frame andons each had one. The clauses below are the
    ways a graph reaches a paid submission while every name-level check reads clean: an
    excluded LoRA two levels down inside a subgraph blueprint; a randomising seed; a
    frame legality that is INDETERMINATE rather than legal; a conditioning class the
    table has never met; and a conditioning node wired at a model with no channel for it
    -- the pairing that produced 65 frames of nothing on 2026-08-12 with every other gate
    green. None of them may be an `assert`.
    """
    res = _run_route(tmp_path, flag=flag, env_var=env_var)
    for name, outcome in res["raised"].items():
        assert outcome.startswith("RAISED:"), f"{label}/{name}: {outcome}"
    assert res["raised"]["pair_unknown_conditioning_class"] == "RAISED:PAIR"
    assert res["raised"]["route_randomising_seed"] == "RAISED:ROUTE"
    assert res["clean"] == "PASS", f"{label}: the clean graph did not pass ({res['clean']})"


def test_the_route_optimization_actually_took_effect(tmp_path):
    """A green sweep under an -O that never applied is a check that cannot fail."""
    assert _run_route(tmp_path, flag=False)["asserts_active"] is True
    assert _run_route(tmp_path, flag=True)["asserts_active"] is False
    assert _run_route(tmp_path, env_var=True)["asserts_active"] is False


# ------------------------------------------- the other half: helpers may not use `assert`

#: Files under `tests/` that pytest DOES rewrite, so an `assert` in them survives `-O`.
#: `conftest.py` is a plugin and measured 2026-09-03 to be rewritten: the whole of
#: `test_gates.py` passes under `python -O -m pytest` with `PYTHONOPTIMIZE=1`, including
#: `test_an_evidence_free_gate_is_what_assert_gate_exists_to_refuse`, whose only signal is
#: an `assert` inside `conftest.assert_gate` raising AssertionError.
REWRITTEN_BY_PYTEST = ("conftest.py",)


def _asserts_in_test_helpers(root=None):
    """`(relpath, lineno)` for every `assert` statement in a non-rewritten tests/ module.

    WAVE 26, F-66b07477 — `root` exists so the red direction below drives THIS walk. What it
    used to do was write an assert-carrying helper into a scratch tree and then re-implement
    the scan inline (`ast.parse` + `[n.lineno for n in ast.walk(tree) if isinstance(n,
    ast.Assert)]`), which proves that `ast.walk` finds an `Assert` node — a property of the
    standard library — and left the production walk's FILE SELECTION unproven. That is the
    half that can go wrong: the prune list below drops `fixtures` from `dirs`, and the name
    filter skips anything starting with `test_` or listed in `REWRITTEN_BY_PYTEST`, so a
    helper placed under `tests/fixtures/` would never be scanned while the green direction
    still reported `scanned` non-empty. Latent rather than live on `81d6c07`:
    `find tests/fixtures -name '*.py'` returned 0 files.
    """
    import ast

    here = os.path.dirname(os.path.abspath(__file__)) if root is None else str(root)
    found, scanned = [], []
    for root, dirs, files in os.walk(here):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "fixtures")]
        for fn in sorted(files):
            if not fn.endswith(".py") or fn.startswith("test_") or fn in REWRITTEN_BY_PYTEST:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, here).replace(os.sep, "/")
            scanned.append(rel)
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            found += [(rel, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    return found, scanned


def test_no_helper_under_tests_checks_anything_with_assert():
    """Measured on this venv: an `assert` in a test body fails under both plain pytest and
    `python -O -m pytest`, because pytest rewrites test modules and plugins. An `assert`
    inside an imported NON-plugin helper fails plain and PASSES under `-O` -- pytest emits
    `PytestConfigWarning: assertions not in test modules or plugins will be ignored` and
    carries on.

    `ci.yml:107` runs `python -O -m pytest tests -q` as the mechanism proving gates still
    raise. That leg would report green over any check added to a helper. The helpers here
    are `fake_backend.py` and the six `tests/blender/check_*.py` scripts -- the second set
    runs inside Blender, where nothing rewrites anything at all.

    Helpers `raise`, for the same reason `tools/` does.
    """
    found, scanned = _asserts_in_test_helpers()
    assert scanned, "the walk found no helper modules; it is not scanning tests/"
    assert not found, (
        f"assert statements in non-rewritten tests/ helpers: {found}. `-O` deletes these "
        f"and `ci.yml`'s -O leg would report green over them. Raise instead.")


def test_the_helper_walk_would_catch_one(tmp_path):
    """The red direction, driven through the PRODUCTION walk (wave 26, F-66b07477).

    A scratch tests-tree carrying four modules, so the walk's FILE SELECTION is what is
    exercised and not `ast.walk`'s ability to see an `Assert`:

      * `fake_helper.py`        — a helper with an assert: MUST be found
      * `test_something.py`     — a test module with an assert: must be SKIPPED (pytest
                                  rewrites it, so `-O` does not delete it)
      * `conftest.py`           — a plugin with an assert: must be SKIPPED, by name
      * `fixtures/planted.py`   — a helper with an assert under the pruned directory

    The last one is the reason this test was rewritten. Nothing under `tests/fixtures/`
    carries Python today, so the prune could never have been caught by the real tree; here it
    is asserted directly, in whichever direction the prune is set to.
    """
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "fake_helper.py").write_text(
        "def check(x):\n    assert x, 'nope'\n", encoding="utf-8")
    (tmp_path / "test_something.py").write_text(
        "def test_x():\n    assert True\n", encoding="utf-8")
    (tmp_path / "conftest.py").write_text(
        "def assert_gate(x):\n    assert x\n", encoding="utf-8")
    (tmp_path / "fixtures" / "planted.py").write_text(
        "def check(x):\n    assert x\n", encoding="utf-8")
    (tmp_path / "__pycache__" / "cached.py").write_text(
        "def check(x):\n    assert x\n", encoding="utf-8")

    found, scanned = _asserts_in_test_helpers(tmp_path)

    assert ("fake_helper.py", 2) in found, found
    assert "fake_helper.py" in scanned, scanned
    assert "test_something.py" not in scanned, scanned
    assert "conftest.py" not in scanned, scanned
    assert not any(rel.startswith("__pycache__/") for rel, _ in found), found

    # The prune, stated in whichever direction it holds: `fixtures/` is dropped from `dirs`,
    # so a helper planted there is invisible to the production walk. This is a RECORD of the
    # selection rule, not an endorsement of it — the green direction above asserts that the
    # real `tests/fixtures/` carries no Python for the rule to hide.
    assert not any(rel.startswith("fixtures/") for rel, _ in found), (
        "the `fixtures` prune has been dropped; if that is deliberate, this clause and the "
        "one below it move together")


def test_the_pruned_fixtures_directory_carries_no_python_for_the_prune_to_hide():
    """The other half of F-66b07477: the prune is only harmless while it hides nothing.

    `_asserts_in_test_helpers` drops `fixtures` from `dirs`, so an assert-carrying helper
    placed there would never be scanned and the green direction would still report `scanned`
    non-empty. Measured on `81d6c07`: `tests/fixtures/**` holds 0 `.py` files. This says so
    on every run, so the day a fixture tree grows a helper is the day this fails and the
    prune has to be argued for rather than inherited.
    """
    import glob

    here = os.path.dirname(os.path.abspath(__file__))
    planted = sorted(glob.glob(os.path.join(here, "fixtures", "**", "*.py"), recursive=True))
    assert planted == [], (
        f"`tests/fixtures/` now carries Python that `_asserts_in_test_helpers` prunes: "
        f"{planted}; either drop the prune or move these under a scanned directory")
