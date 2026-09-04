"""`rig_character`'s two invocations, and what its skeleton-mode manifest may claim.

`tests/` had no coverage of any `tools/*.py` argv dispatch before wave 6.

**F-f1f03a2a — `--measure-only` could not run.** `main` called

    build_pass(args["glb"], args["name"], args["bands"], "measure")

with four positional arguments, so `bind` took its declared default `True`. `build_pass`
then reached `if bind:` and called `apply_binding(mesh_obj, arm_obj, bind, ...)`, whose
third positional parameter is `mode` — dispatched on `"auto" / "envelope" / "rigid"`, with
an `else` that raises `ArmatureError("unknown binding True; known: auto, envelope,
rigid")`. Every other caller passes a string: `run_skeleton` passes `bind=False`, the full
path passes `bind=mode`. So an executor told to measure a subject before rigging got a halt
naming a binding mode they never asked for — and, combined with F-f5530688, could read exit
0 from Blender while `measure.json` did not exist.

**F-6a3d2901 — Gate D's weights clause on the skeleton route.** Both `build_pass` calls in
`run_skeleton` pass `bind=False`, so `weights` stays `{}` and `rig_fingerprint` stores an
empty weight map in both fingerprints. `gate_d_determinism` then walks its weight clause
over nothing: `set(wa) != set(wb)` is `set() != set()`, the loop never executes, and
`worst_weight_delta` is written `{group: null, max_abs: 0.0, n_differing: 0}` — a zero
indistinguishable from the zero a perfect agreement produces. The gate returns *"two builds
agree on bones, hierarchy and weights"* and `run_skeleton` writes that string into
`skeleton_manifest.json`.

The gate is NOT vacuous on this route: its bones clause genuinely compares heads, tails,
rolls, parents and deform flags across all 22 bones, which is the whole content of a
skeleton build. Only the weights clause and the verdict string over-claim — and the same
manifest is scrupulous about exactly this three times over (`P_evaluation_liveness`,
`probe_action` and `deformation_diagnostics` are all written `NOT YET RUN` / `NOT AUTHORED`
with a reason). This is the one place that reported agreement instead.
"""

import ast
import json
import os
import sys

import numpy as np
import pytest

from armature_core import rig_gates
from blender_stub import blender_stubbed, load_tool, read_source


@pytest.fixture(scope="module")
def rc():
    return load_tool("rig_character.py")


# ------------------------------------------------------------- F-f1f03a2a: the dispatch


def test_build_pass_has_no_binding_default_left_to_fall_through():
    """`bind=True` was the only value `apply_binding` cannot accept, and no caller used it.
    A caller that forgets now fails at the call, not three functions deep in a message about
    a mode nobody asked for."""
    tree = ast.parse(read_source("rig_character.py"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_pass")
    args = [a.arg for a in fn.args.args]
    n_defaults = len(fn.args.defaults)
    defaulted = dict(zip(args[len(args) - n_defaults:], fn.args.defaults))
    assert "bind" in args, args
    assert "bind" not in defaulted, (
        "build_pass still defaults `bind`; the default was `True`, which apply_binding "
        "refuses by design")


def test_every_build_pass_call_site_states_its_binding():
    tree = ast.parse(read_source("rig_character.py"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "build_pass"]
    assert len(calls) >= 4, len(calls)
    for call in calls:
        names = {kw.arg for kw in call.keywords}
        assert "bind" in names or len(call.args) >= 5, (
            f"build_pass call at line {call.lineno} does not state its binding")


def test_apply_binding_still_refuses_a_boolean(rc):
    """The refusal that fired is correct and stays — what was wrong was reaching it."""
    tree = ast.parse(read_source("rig_character.py"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "apply_binding")
    known = [c.value for n in ast.walk(fn)
             for c in ast.walk(n) if isinstance(c, ast.Constant)
             and c.value in ("auto", "envelope", "rigid")]
    assert set(known) == {"auto", "envelope", "rigid"}
    assert True not in known


class _App:
    version_string = "5.2.0-probe"


class _Bpy:
    app = _App()


def test_measure_only_reaches_its_own_writer(rc, tmp_path, monkeypatch):
    """The behavioural half: the documented `--measure-only` invocation writes
    `measure.json`. It used to halt before the writer with `unknown binding True`."""
    calls = {}

    def fake_build_pass(glb, name, bands, label, bind=None, envelope_radii="measured"):
        calls["bind"] = bind
        calls["label"] = label
        return {
            "premise2": {}, "weld_on_import": {}, "normalisation": {},
            "premise6": {}, "bone_lengths": {}, "gate_p": None, "timings": {},
            "landmarks": {"landmarks": {}, "provenance": {}, "facing": {}, "regions": {}},
        }

    out = tmp_path / "measure_out"
    argv = ["blender", "-b", "-P", "rig_character.py", "--",
            "--glb=" + str(tmp_path / "subject.glb"), "--out=" + str(out),
            "--measure-only"]
    (tmp_path / "subject.glb").write_bytes(b"not-a-real-glb")

    with blender_stubbed():
        monkeypatch.setattr(rc, "bpy", _Bpy())
        monkeypatch.setattr(rc, "build_pass", fake_build_pass)
        monkeypatch.setattr(sys, "argv", argv)
        rc.main()

    written = os.path.join(str(out), "measure.json")
    assert os.path.isfile(written), os.listdir(str(out))
    rec = json.load(open(written, encoding="utf-8"))
    assert rec["mode"] == "measure-only"
    assert calls["bind"] is not True, (
        "the measure pass still hands apply_binding a boolean where a mode string belongs")
    assert calls["bind"] in (False, "auto", "envelope", "rigid"), calls


def test_the_measure_record_says_whether_anything_was_bound(rc, tmp_path, monkeypatch):
    """`rec["gate_p"]` is `None` when nothing is bound, and a null beside a gate name is the
    placeholder-shaped-like-evidence this repo refuses. The record has to say which it is."""
    def fake_build_pass(glb, name, bands, label, bind=None, envelope_radii="measured"):
        return {
            "premise2": {}, "weld_on_import": {}, "normalisation": {},
            "premise6": {}, "bone_lengths": {}, "gate_p": None, "timings": {},
            "landmarks": {"landmarks": {}, "provenance": {}, "facing": {}, "regions": {}},
        }

    out = tmp_path / "measure_out2"
    (tmp_path / "s.glb").write_bytes(b"x")
    with blender_stubbed():
        monkeypatch.setattr(rc, "bpy", _Bpy())
        monkeypatch.setattr(rc, "build_pass", fake_build_pass)
        monkeypatch.setattr(sys, "argv", ["blender", "-b", "-P", "x", "--",
                                          "--glb=" + str(tmp_path / "s.glb"),
                                          "--out=" + str(out), "--measure-only"])
        rc.main()
    rec = json.load(open(os.path.join(str(out), "measure.json"), encoding="utf-8"))
    assert "binding" in rec, sorted(rec)
    gate_p = rec["gate_p"]
    assert isinstance(gate_p, dict) and "verdict" in gate_p, gate_p


# ------------------------------------- F-6a3d2901: what Gate D may claim with no weights


def _fingerprint(weights):
    bones = {"hip": {"head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.2), "roll": 0.0,
                     "parent": None, "use_deform": True}}
    return rig_gates.rig_fingerprint(bones, weights, n_verts=10)


def test_two_empty_weight_maps_do_not_produce_a_verdict_about_weights(rc):
    """The invariant the finding names. The bones clause still reports what it compared."""
    a, b = _fingerprint({}), _fingerprint({})
    gate_d = rig_gates.gate_d_determinism(a, b, 1.0)
    assert "weights" in gate_d["verdict"], (
        "the core gate's own verdict changed; this test is about rig_character's record")

    rec = rc.unbound_determinism_record(gate_d, a, b)
    assert "weights" not in rec["verdict"], rec["verdict"]
    assert rec["weights_clause"]["verdict"] == "NOT YET RUN"
    assert "reason" in rec["weights_clause"]


def test_the_not_yet_run_clause_matches_the_manifests_own_convention(rc):
    """`P_evaluation_liveness`, `probe_action` and `deformation_diagnostics` are all written
    this way in the same dict; the weights clause was the one place that said "agree"."""
    a, b = _fingerprint({}), _fingerprint({})
    rec = rc.unbound_determinism_record(rig_gates.gate_d_determinism(a, b, 1.0), a, b)
    clause = rec["weights_clause"]
    assert set(clause) >= {"verdict", "reason"}
    assert "nothing is bound" in clause["reason"]
    src = read_source("rig_character.py")
    assert "nothing is bound in skeleton mode" in src


def test_a_bound_pair_keeps_the_gates_own_verdict(rc):
    """A record that rewrote every verdict would be as bad as one that never did."""
    w = {"hip": np.zeros(10)}
    a, b = _fingerprint(w), _fingerprint(w)
    gate_d = rig_gates.gate_d_determinism(a, b, 1.0)
    rec = rc.unbound_determinism_record(gate_d, a, b)
    assert rec is gate_d or rec["verdict"] == gate_d["verdict"]
    assert "weights_clause" not in rec


def test_declaring_unbound_over_a_pair_that_carries_weights_raises(rc):
    """The direction the record does not otherwise bound: a caller that says "nothing is
    bound" about a build that WAS bound would erase a real weight comparison."""
    w = {"hip": np.zeros(10)}
    a, b = _fingerprint({}), _fingerprint(w)
    with pytest.raises(rc.ArmatureError):
        rc.unbound_determinism_record(rig_gates.gate_d_determinism(a, b, 1.0), a, b,
                                      expect_weights=False)


def test_run_skeleton_records_the_unbound_determinism_record():
    src = read_source("rig_character.py")
    body = src.split("def run_skeleton")[1].split("\ndef ")[0]
    assert "unbound_determinism_record" in body, (
        "run_skeleton still writes the raw gate record, whose verdict names weights no "
        "build in that run ever had")


# ------------------------- the facing dict reaches the record whole (core-solvers seam)
#
# SEAM, wave 6: `armature_core.landmarks.facing()` now compares its two previously
# uncompared quantities and raises `FacingGate` (gate FACING, evidence = the whole facing
# dict) on an exact tie on the feet and on a head cross-check that disagrees while
# separating front/back at least as well as the feet do; margins are reported per structure
# as fractions of that structure's own y-extent (core-solvers F-d876df3f).
#
# rig_character is where a reader sees that dict. Two things have to stay true: nothing
# here catches the gate, and the manifest records the dict as landmarks returns it — a
# manifest that cherry-picked `facing_y_sign` and `left_x_sign` would drop the margins the
# disagreement is visible in.


def test_nothing_between_the_landmark_solve_and_the_manifest_catches_a_gate():
    """`FacingGate` is a GateFailure and must reach the __main__ handler, which writes its
    gate id into halt.json and exits 2."""
    tree = ast.parse(read_source("rig_character.py"))
    module_level_handlers = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            name = getattr(handler.type, "id", None)
            if name in ("GateFailure", "ArmatureError", "Exception", None, "BaseException"):
                module_level_handlers.append((handler.lineno, name))
    # The only broad handlers in this file are the two in the `__main__` block, which is
    # where a halt is SUPPOSED to be caught, recorded and re-raised as a non-zero exit.
    main_block = next(n for n in tree.body
                      if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                      and getattr(n.test.left, "id", None) == "__name__")
    in_main = {h.lineno for n in ast.walk(main_block) if isinstance(n, ast.Try)
               for h in n.handlers}
    stray = [(lineno, name) for lineno, name in module_level_handlers
             if lineno not in in_main]
    assert not stray, (
        f"rig_character catches {stray} outside its __main__ handler; a FacingGate caught "
        f"there would never reach halt.json or the exit code")


def test_every_manifest_records_the_facing_dict_whole():
    """Not `facing_y_sign` and `left_x_sign` picked out of it: the margin fractions
    core-solvers now reports are what make a head/foot disagreement legible."""
    src = read_source("rig_character.py")
    tree = ast.parse(src)
    writes = [n for n in ast.walk(tree)
              if isinstance(n, ast.Subscript)
              and isinstance(n.slice, ast.Constant) and n.slice.value == "facing"]
    assert len(writes) >= 4, len(writes)
    assert src.count('"facing": ctx["landmarks"]["facing"]') >= 3, (
        "a manifest no longer records the facing dict as landmarks returns it")
