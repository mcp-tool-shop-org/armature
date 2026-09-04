"""Wave-12 core-solvers amend — the red proofs for thirteen routed findings.

Every test here was written before the fix it names and run against the wave-12 base
(`89269f1`) to see it fail. Each one probes the FULL invariant its finding names, and the
gate tests mutate the protected thing rather than asking a gate to pass on happy input.

The population walks in this file key on BEHAVIOUR, not on a spelling (wave-12 rule 1):
the refusal census resolves every `raise` of an `ArmatureError` subclass by walking the
class hierarchy, inline or through a helper, and it is proven red on a raise written with
no evidence argument at all — the shape that hid from `test_gates.evidence_dicts_missing`,
which `continue`d past `EV_NONE` before counting.
"""

import ast
import contextlib
import json
import math
import os
import sys

import numpy as np
import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
CORE = os.path.join(REPO, "tools", "armature_core")
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import blender_stub  # noqa: E402

from armature_core import (aapose, assembly, clipcompare, clipstats, framing, glb,  # noqa: E402
                           parts, pngio, sitelist, startframe, turnaround, walk)
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402


# ======================================================================= F-2a564189
# `tightened` refuses 0.0 — the tightest legal request — with `require_finite`'s NaN
# paragraph, which is untrue of a number that compares correctly in both directions.

def test_tightened_accepts_zero_the_tightest_possible_request():
    """0.0 is exact-match: the one value that is unambiguously not a loosening. Measured
    on the base against `owned=1e-4`: 1e-30 accepted, 1e-4 accepted, 1e-3 refused
    (correct), 0.0 refused with the NaN reasoning."""
    ev = {}
    assert parts.tightened("epsilon_frac", 0.0, 1e-4, parts.GateRigidArrival, ev) == 0.0


def test_tightened_still_refuses_a_loosening_and_a_nan_and_a_negative():
    """The three directions the guard exists for must all stay closed."""
    for bad in (1e-3, float("nan"), float("inf"), -1e-9):
        with pytest.raises(parts.GateRigidArrival,
                           match=r"may only TIGHTEN|not a finite number|admits nothing"):
            parts.tightened("epsilon_frac", bad, 1e-4, parts.GateRigidArrival, {})


def test_a_negative_tolerance_is_refused_by_its_own_clause_not_the_nan_paragraph():
    """A negative number compares correctly in both directions, so quoting the NaN
    reasoning at it is a message that describes a different defect."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.tightened("epsilon_frac", -1.0, 1e-4, parts.GateRigidArrival, {})
    assert "admits nothing" in str(exc.value)
    assert "NaN fails EVERY comparison" not in str(exc.value)


def test_determinism_gate_accepts_an_exact_equality_request():
    """The natural caller: `epsilon_frac=0.0` means "two builds must be byte-identical",
    the strictest reading of Gate D. On the base this refused as an uncomparable number."""
    pos = np.zeros((3, 3), dtype=float)
    a = {"p": {"n_verts": 3, "n_faces": 1, "positions": pos}}
    b = {"p": {"n_verts": 3, "n_faces": 1, "positions": pos.copy()}}
    ev = parts.gate_parts_determinism(a, b, 1.0, length_frac=0.0)
    assert ev["length_frac"] == 0.0


def test_require_rotation_accepts_an_exact_tolerance_through_the_same_helper():
    """The refusal reached every public gate importing the helper — measured on the base:
    `require_rotation(I, 'w', tol=0.0)` raised ResampleGate with the NaN text."""
    from armature_core import resample
    resample.require_rotation(np.eye(3), "w", tol=0.0)


# ======================================================================= F-cd1cbd18
# Gate WHOLE checked five of its seven numbers and skipped the two in its denominators.

def _ok_extent():
    return {"x0": 100.0, "x1": 924.0, "y0": 100.0, "y1": 924.0,
            "n_points": 10, "n_behind": 0}


def test_gate_whole_passes_on_a_finite_frame():
    ev = startframe.gate_whole(_ok_extent(), 1024, 1024, 16.0)
    assert ev["margins_px"]["right"] == pytest.approx(100.0)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0, -1024])
@pytest.mark.parametrize("which", ["width", "height"])
def test_gate_whole_refuses_a_non_finite_or_non_positive_resolution(which, bad):
    """Measured on the base: `gate_whole(ext, nan, 1024, 16.0)` RETURNED the verdict
    "whole silhouette in frame; smallest margin 100.0 px" with `margins_px['right'] = nan`
    and `width_frac = nan`; `gate_whole(ext, 1024, 0, 16.0)` raised a bare
    ZeroDivisionError from inside the gate, which a halt handler records as an unhandled
    error rather than a refusal."""
    kw = {"width": 1024, "height": 1024}
    kw[which] = bad
    with pytest.raises(startframe.StartFrameGate) as exc:
        startframe.gate_whole(_ok_extent(), kw["width"], kw["height"], 16.0)
    assert exc.value.evidence[which] == pytest.approx(float(bad), nan_ok=True)


def test_gate_whole_never_certifies_a_margin_that_is_not_a_number():
    """The property, not the instance: no PASS may carry a non-finite margin or fraction."""
    ev = startframe.gate_whole(_ok_extent(), 1024, 1024, 16.0)
    for v in list(ev["margins_px"].values()) + [ev["height_frac"], ev["width_frac"]]:
        assert math.isfinite(v)


# ======================================================================= F-bf3dfb4e
# THE ALPHA LAW's turnaround-route gate printed a non-number in its PASS verdict.

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_gate_view_alpha_refuses_a_non_finite_transparent_fraction(bad):
    """Measured on the base: `gate_view_alpha(3, 0, 255, nan)` RETURNED with the verdict
    "view 3 authored RGBA; extrema (0, 255), nan of the frame transparent". The sibling on
    the start-frame route refuses the same value."""
    with pytest.raises(turnaround.TurnaroundAlphaGate) as exc:
        turnaround.gate_view_alpha(3, 0, 255, bad)
    assert exc.value.evidence["transparent_fraction"] == pytest.approx(
        float(bad), nan_ok=True)


def test_gate_view_alpha_still_passes_a_real_measurement():
    ev = turnaround.gate_view_alpha(3, 0, 255, 0.42)
    assert "0.42" in ev["verdict"] or "0.420" in ev["verdict"]
    assert math.isfinite(ev["transparent_fraction"])


def test_both_alpha_gates_on_both_routes_refuse_the_same_value():
    """The reason this finding exists: the sweep that closed the start-frame route stopped
    inside `startframe.py` and this is the turnaround route's other alpha gate."""
    with pytest.raises(startframe.AlphaGate, match=r"not a finite number"):
        startframe.gate_alpha(float("nan"), (0.1, 0.1, 0.1), "why")
    with pytest.raises(turnaround.TurnaroundAlphaGate, match=r"not a finite number"):
        turnaround.gate_view_alpha(0, 0, 255, float("nan"))


# ======================================================================= F-499b7cfa
# Gate CONV compared the module's tables against the module's own tables.

def test_recorded_convention_is_pinned_by_its_own_digest():
    assert aapose.recorded_convention_digest() == aapose.RECORDED_CONVENTION_SHA256


def test_gate_conv_refuses_when_the_modules_tables_drift_from_the_recorded_reference(
        monkeypatch):
    """THE red proof. On the base, swapping the module's own tables to a ControlNet-18
    shape — the exact conflation this module's docstring says it exists to keep visible —
    left `check_convention(len(KEYPOINT_NAMES), LIMB_SEQ, PALETTE)` returning True, because
    all three arguments are read from the tables being compared against."""
    from armature_core import openpose
    monkeypatch.setattr(aapose, "KEYPOINT_NAMES", aapose.KEYPOINT_NAMES[:18])
    monkeypatch.setattr(aapose, "KEYPOINT_COUNT", 18)
    monkeypatch.setattr(aapose, "PALETTE", aapose.PALETTE[:18])
    monkeypatch.setattr(aapose, "LIMB_SEQ", tuple(tuple(p) for p in openpose.LIMB_SEQ))
    with pytest.raises(ArmatureError) as exc:
        aapose.check_convention(len(aapose.KEYPOINT_NAMES), aapose.LIMB_SEQ,
                                aapose.PALETTE)
    assert "recorded reference" in str(exc.value)


def test_gate_conv_refuses_a_mutated_recorded_reference(monkeypatch):
    """The other direction: the reference cannot be edited into agreement with a wrong
    table without the digest pin firing."""
    bad = json.loads(json.dumps(aapose.RECORDED_CONVENTION))
    bad["limb_seq"][-1] = [3, 17]
    monkeypatch.setattr(aapose, "RECORDED_CONVENTION", bad)
    with pytest.raises(ArmatureError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    assert "digest" in str(exc.value)


def test_gate_conv_verdict_names_what_it_actually_compared():
    """A verdict naming a comparison no code performs is this repo's named most-expensive
    defect class. The provenance detail is now read off the return value."""
    v = aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    assert isinstance(v, dict)
    assert v["compared_against"] == "armature_core.aapose.RECORDED_CONVENTION"
    assert v["recorded_sha256"] == aapose.RECORDED_CONVENTION_SHA256
    assert v["banked_source"] in ("verified", "absent", "MISMATCH")
    assert v["source_commit"] == aapose.SOURCE["commit"]
    # The detail line a provenance record may quote verbatim, and it does not claim a
    # comparison against the fetched file unless one happened.
    if v["banked_source"] == "absent":
        assert "human_visualization.py" not in v["detail"]


def test_gate_conv_still_refuses_the_controlnet_table_from_a_caller():
    from armature_core import openpose
    with pytest.raises(ArmatureError, match=r"caller: limb pair 17"):
        aapose.check_convention(18, openpose.LIMB_SEQ, aapose.PALETTE)


# ======================================================================= F-5a810b95
# The allowlist keyword had no tightening guard, no vacuity guard, and a two-word
# substring for a "second opinion".

def test_gate_no_paid_nodes_refuses_a_widened_allowlist():
    """Measured on the base: the same graph that raises on the default allowlist RETURNED
    the full success verdict under `allowed=ALLOWED_CLASSES + ('KlingVideoNode',)` — the
    second opinion is silent because no real partner class name contains 'api' or
    'partner'."""
    graph = {"1": {"class_type": "KlingVideoNode"}}
    with pytest.raises(assembly.AssemblyGate, match=r"the allowlist does not name"):
        assembly.gate_no_paid_nodes(graph)
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes(
            graph, allowed=assembly.ALLOWED_CLASSES + ("KlingVideoNode",))
    assert "widen" in str(exc.value).lower()


def test_gate_no_paid_nodes_allows_a_narrowing():
    """The guard bounds one direction only — a caller may still tighten."""
    ev = assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"}},
                                     allowed=("LoadImage",))
    assert ev["allowed"] == ["LoadImage"]


def test_gate_no_paid_nodes_refuses_an_empty_graph():
    """Measured on the base: `gate_no_paid_nodes({})` returned "PASS — 0 node(s) across 0
    class(es), all named by the allowlist". Its two siblings in this module got their
    vacuity guards at wave 10."""
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes({})
    assert exc.value.evidence["n_nodes"] == 0


def test_the_second_opinion_is_a_licence_ruling_not_a_two_word_substring():
    """The replacement clause reads the same `route_gates` tables the licence gate reads,
    so a class the licence map has ruled BANNED is refused even from inside the allowlist —
    which is exactly what the substring could not see."""
    from armature_core import route_gates
    banned = None
    for key, rec in route_gates.RULED_COMPONENTS.items():
        if rec.get("verdict") in ("BANNED", "EXCLUDED"):
            pats = route_gates.class_patterns_for(key)
            if pats:
                banned = sorted(pats)[0]
                break
    assert banned is not None, "no ruled class pattern to drive the clause with"
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes({"1": {"class_type": banned}},
                                    allowed=("LoadImage",) )
    assert "licence" in str(exc.value).lower() or "license" in str(exc.value).lower()


def test_gate_no_paid_nodes_still_passes_the_free_four_class_chain():
    graph = {str(i): {"class_type": c}
             for i, c in enumerate(assembly.ALLOWED_CLASSES)}
    ev = assembly.gate_no_paid_nodes(graph)
    assert ev["verdict"].startswith("4 node(s)")


# ======================================================================= F-11b349bf
# One degenerate frame turned every aggregate into NaN while `n` still said nine.

def _flat_and_moving_frames(n=9, flat_at=5):
    rng = np.random.default_rng(7)
    out = []
    for i in range(n):
        if i == flat_at:
            out.append(np.zeros((8, 8, 3), dtype=np.float64))
        else:
            out.append(rng.random((8, 8, 3)) * 255.0)
    return out


def test_one_flat_frame_does_not_erase_eight_good_correlations():
    """Measured on the base with nine frames of which exactly one is flat:
    `stats_correlation = {'n': 9, 'min': nan, 'median': nan, 'mean': nan, 'p90': nan,
    'max': nan}`. Every one of the eight good correlations was discarded by a summary that
    still reported n: 9."""
    st = clipstats.similarity_to_first(_flat_and_moving_frames())["stats_correlation"]
    assert st["n"] == 9
    assert st["n_finite"] == 8
    assert st["n_non_finite"] == 1
    for k in ("min", "median", "mean", "p90", "max"):
        assert st[k] is not None and math.isfinite(st[k]), (k, st)


def test_a_population_that_is_entirely_non_finite_reports_none_not_a_number():
    st = clipstats._stats([float("nan"), float("nan")])
    assert (st["n"], st["n_finite"], st["n_non_finite"]) == (2, 0, 2)
    assert st["median"] is None


# ======================================================================= F-86e9b5b9
# `_stats` returned a DIFFERENT KEY SET for the empty case and a consumer read a key that
# was not there.

STAT_KEYS = ("n", "n_finite", "n_non_finite", "min", "median", "mean", "p90", "max")


def test_stats_returns_one_key_set_for_every_population():
    for values in ([], [1.0], [1.0, 2.0, 3.0], [float("nan")]):
        st = clipstats._stats(values)
        assert set(st) == set(STAT_KEYS), values


def test_a_one_frame_clip_reports_none_rather_than_raising_keyerror():
    """`tools/measure_clip.py:131` does `round(arm["frame_deltas"]["stats"]["median"], 3)`
    with no guard, so on the base the instrument died with a bare `KeyError: 'median'` on
    the one-frame clip it most needs to describe."""
    one = _flat_and_moving_frames(n=1, flat_at=-1)
    fd = clipstats.frame_deltas(one)
    assert fd["stats"]["n"] == 0
    assert fd["stats"]["median"] is None
    assert clipstats.luma_series(one)["stats"]["median"] is None
    assert clipstats.similarity_to_first([])["stats_mean_abs"]["median"] is None


# ======================================================================= F-2ceefec7
# `order_check` reported a scramble on a byte-identical round trip of a clip with a hold.

def _walk_shaped_clip(n_moving=8, n_hold=4):
    rng = np.random.default_rng(3)
    frames = [rng.random((16, 16, 3)) * 255.0 for _ in range(n_moving)]
    frames += [frames[-1].copy() for _ in range(n_hold)]
    return frames


def test_a_hold_is_named_a_hold_not_a_displacement():
    """Measured on the base against an exact copy of itself: `order_preserved: False`,
    `n_on_diagonal: 8/12`, `displaced: [(8,7),(9,7),(10,7),(11,7)]` — four frames reported
    as landing in the wrong place in a clip where source and decode are the same bytes.
    `walk.GaitParams` ends every authored walk with exactly this hold."""
    clip = _walk_shaped_clip()
    out = clipcompare.order_check(clip, [f.copy() for f in clip], step=1)
    assert out["order_preserved"] is True
    assert out["n_displaced"] == 0
    # Five frames are byte-identical — the last moving frame plus the four holds that
    # copy it — so the tie group is 7..11 and the four the base called displaced are 8..11.
    assert out["n_tied"] == 5
    assert sorted(out["tie_groups"][0]) == [7, 8, 9, 10, 11]


def test_a_real_displacement_still_reads_as_one():
    """The direction the check exists for must stay open: grade an arm only on what it can
    move."""
    clip = _walk_shaped_clip(n_moving=8, n_hold=0)
    scrambled = clip[4:] + clip[:4]
    out = clipcompare.order_check(clip, scrambled, step=1)
    assert out["order_preserved"] is False
    assert out["n_displaced"] == 8


def test_the_hold_this_repos_own_walk_generator_authors_is_the_fixture():
    """The premise, measured rather than asserted: `GaitParams` carries a hold phase."""
    p = walk.GaitParams()
    assert p.n_hold >= 1


# ======================================================================= F-ae74741c
# `write_png` produced a structurally invalid PNG on a zero-sized array and returned a
# byte count as if it had succeeded.

@pytest.mark.parametrize("shape", [(0, 64, 3), (64, 0, 3), (0, 64), (64, 0), (0, 0)])
def test_write_png_refuses_a_zero_dimension(tmp_path, shape):
    """Measured on the base: `write_png(p, zeros((0,64,3)))` -> 'WROTE 65 bytes' and PIL
    raises `UnidentifiedImageError` on the file. The PNG spec requires both IHDR
    dimensions greater than zero."""
    p = tmp_path / "z.png"
    with pytest.raises(pngio.PngWriteError) as exc:
        pngio.write_png(str(p), np.zeros(shape, dtype=np.uint8), bit_depth=8)
    assert exc.value.evidence["clause"] == "zero_dimension"
    assert not p.exists(), "the refusal must fire before any bytes are written"


def test_write_png_still_writes_a_real_frame(tmp_path):
    p = tmp_path / "ok.png"
    n = pngio.write_png(str(p), np.zeros((4, 5, 3), dtype=np.uint8), bit_depth=8)
    assert n == os.path.getsize(str(p)) > 0


# ======================================================================= F-9fab7829
# A deliberate refusal raised as a bare builtin is recorded by the halt contract as a
# crash. Thirteen sites across six owned modules.

def _halt_classifier(exc):
    """The 21-tool halt contract's own three-way classifier, replayed verbatim."""
    if isinstance(exc, GateFailure):
        outcome, code = "HALTED - a gate fired", 2
    elif isinstance(exc, ArmatureError):
        outcome, code = "REFUSED - the tool declined to proceed", 2
    else:
        outcome, code = "FAILED - an unhandled error", 1
    return outcome, code, getattr(exc, "gate", None), getattr(exc, "evidence", None)


def test_sitelist_validate_refuses_as_a_refusal_not_a_crash(monkeypatch):
    """Measured on the base by driving that exact classifier with the exception
    `validate()` raises on a duplicated registration: ('FAILED - an unhandled error',
    exit 1, gate None, evidence None). Three production Blender tools call it."""
    monkeypatch.setattr(sitelist, "BONES", list(sitelist.BONES) + [sitelist.BONES[0]])
    with pytest.raises(sitelist.SiteListError) as exc:
        sitelist.validate()
    outcome, code, gate, ev = _halt_classifier(exc.value)
    assert code == 2 and outcome.startswith("REFUSED")
    assert gate is None
    assert ev["andon"] == "SiteListError"
    assert ev["clause"] == "registration_inconsistent"
    assert ev["problems"]


def test_sitelist_validate_still_passes_the_registered_list():
    assert sitelist.validate() is True


BUILTIN_REFUSAL_MODULES = ("pngio", "clipcompare", "clipstats", "blender_scene",
                           "lift_solve", "sitelist")


def _raised_class_names(path):
    """Every class name raised directly in a module — by BEHAVIOUR (the AST `raise`), not
    by a name pattern, so an inline raise cannot hide from this walk."""
    out = []
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            fn = node.exc.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name:
                out.append((node.lineno, name))
    return out


def test_no_owned_module_refuses_through_a_bare_builtin():
    """The census, over the population that CANNOT hide: every `raise` of a name that
    resolves to a builtin exception in the six modules the finding measured. Thirteen on
    the base — pngio 65/69/71/74/76, clipcompare 49/51/100, clipstats 51/152,
    blender_scene 389, lift_solve 634, sitelist 133."""
    builtins_raised = []
    for mod in BUILTIN_REFUSAL_MODULES:
        for lineno, name in _raised_class_names(os.path.join(CORE, mod + ".py")):
            if isinstance(getattr(__builtins__, name, None)
                          if not isinstance(__builtins__, dict)
                          else __builtins__.get(name), type):
                builtins_raised.append(f"{mod}.py:{lineno} {name}")
    assert builtins_raised == [], (
        "a deliberate refusal raised as a builtin is recorded by the halt contract as "
        "'FAILED - an unhandled error' at exit 1: " + "; ".join(builtins_raised))


def test_the_builtin_census_is_red_on_a_module_that_reintroduces_one(tmp_path):
    """Proven red by ADDING a member without the property — a fresh module carrying an
    inline `raise ValueError`, a spelling no name filter would catch."""
    p = tmp_path / "fake_core.py"
    p.write_text("def f():\n    raise ValueError('nope')\n", encoding="utf-8")
    found = [n for _, n in _raised_class_names(str(p))]
    assert "ValueError" in found


@pytest.mark.parametrize("call", [
    lambda: clipstats.luma(np.zeros((4, 4))),
    lambda: clipstats.horizon_row(np.zeros((3, 4, 3)), band=(1, 2)),
    lambda: clipcompare.frame_fidelity(np.zeros((4, 4)), np.zeros((4, 4))),
    lambda: clipcompare.frame_fidelity(np.zeros((4, 4, 3)), np.zeros((5, 4, 3))),
    lambda: clipcompare.order_check([np.zeros((4, 4, 3))], []),
])
def test_every_swept_refusal_lands_in_the_armature_family(call):
    with pytest.raises(ArmatureError) as exc:
        call()
    _outcome, code, _gate, ev = _halt_classifier(exc.value)
    assert code == 2
    assert ev and ev.get("andon") and ev.get("gate", "MISSING") is None


def test_union_sphere_refuses_a_spent_iterator_in_the_family():
    with blender_stub.blender_stubbed():
        from armature_core import blender_scene as BS
        with pytest.raises(ArmatureError) as exc:
            BS.union_sphere(iter([]))
    assert _halt_classifier(exc.value)[1] == 2


def test_round_trip_report_refuses_being_armed_in_the_family():
    from armature_core import lift_solve
    with pytest.raises(ArmatureError) as exc:
        lift_solve.round_trip_report({}, {}, {}, 1.0, raise_on_fail=True)
    assert _halt_classifier(exc.value)[1] == 2


# ======================================================================= F-197cf096
# The receipt rule reached nine sites out of ninety, and the census that polices it could
# not see the other eighty-one.

RECEIPT_MODULES = ("walk", "framing", "glb")


def _armature_error_subclass_names():
    """The family, by CLASS HIERARCHY — every subclass of `ArmatureError` reachable from
    the owned modules, resolved on the imported classes rather than on a name pattern.

    Always read off the real package, never off whatever directory a fixture points the
    SOURCE walk at: the family is a property of the class tree, and a census whose family
    goes empty when its source directory moves is a census that cannot fail."""
    names = set()
    with blender_stub.blender_stubbed():
        import importlib
        for fn in sorted(os.listdir(os.path.join(REPO, "tools", "armature_core"))):
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            mod = importlib.import_module("armature_core." + fn[:-3])
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if isinstance(obj, type) and issubclass(obj, ArmatureError):
                    names.add(attr)
    return names


def plain_refusals_without_a_receipt(modules, root=None):
    """Every `raise <ArmatureError subclass>(...)` with NO evidence argument.

    Keyed on behaviour: the class is resolved against the `ArmatureError` hierarchy, and a
    site is an offender when the call carries fewer than two arguments — which is exactly
    the shape `test_gates.evidence_dicts_missing` skipped with `if verdict == EV_NONE:
    continue` BEFORE `examined += 1`, so the 81 were not offenders, not unreadable, and not
    even in the denominator.
    """
    family = _armature_error_subclass_names()
    out = []
    for mod in modules:
        path = os.path.join(CORE if root is None else root, mod + ".py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            fn = node.exc.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name in family and (len(node.exc.args) + len(node.exc.keywords)) < 2:
                out.append(f"{mod}.py:{node.lineno} {name}")
    return out


def test_every_plain_refusal_in_walk_framing_and_glb_carries_a_receipt():
    """Eighteen sites on the base — walk 8, framing 5, glb 5 — including two `GaitParams`
    siblings that sit four lines from a compliant third."""
    assert plain_refusals_without_a_receipt(RECEIPT_MODULES) == []


def test_the_receipt_census_is_red_on_a_raise_written_with_no_evidence(tmp_path):
    """Proven red on the two spellings that hide.

    The first is a raise with NO second argument at all — the shape
    `test_gates.evidence_dicts_missing` `continue`s past on `EV_NONE` before `examined`,
    so 81 of this domain's 90 refusals were neither offenders nor in the denominator.
    The second is an INLINE raise of a family member reached through an import ALIAS, which
    a walk keyed on callee names would not recognise as a refusal at all. Both are caught,
    because the walk keys on the class hierarchy and on the argument count."""
    fake = tmp_path / "fake_mod.py"
    fake.write_text("from .errors import ArmatureError\n"
                    "from .walk import WalkError\n"
                    "def f():\n    raise ArmatureError('no receipt')\n"
                    "def g():\n    raise WalkError('also no receipt')\n", encoding="utf-8")
    found = plain_refusals_without_a_receipt(["fake_mod"], root=str(tmp_path))
    assert found == ["fake_mod.py:4 ArmatureError", "fake_mod.py:6 WalkError"], found


@pytest.mark.parametrize("make", [
    lambda: walk.GaitParams(n_walk=0),
    lambda: walk.GaitParams(steps=0),
    lambda: walk._rot("Q", 10.0),
    lambda: framing._norm((0.0, 0.0, 0.0)),
    lambda: framing.ortho_half_spans(0.0, 4, 4),
])
def test_the_receipt_reaches_the_halt_line_for_named_siblings(make):
    """The two `GaitParams` siblings the finding names, plus one per swept module. The
    receipt a halt record writes is `gate: None` + `andon` + `clause`."""
    with pytest.raises(ArmatureError) as exc:
        make()
    ev = exc.value.evidence
    assert ev["gate"] is None
    assert ev["andon"] == type(exc.value).__name__
    assert isinstance(ev["clause"], str) and ev["clause"]


def test_the_glb_reader_refusals_carry_their_clause(tmp_path):
    p = tmp_path / "short.glb"
    p.write_bytes(b"glTF")
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.read_chunks(str(p))
    assert exc.value.evidence["gate"] is None
    assert exc.value.evidence["clause"] == "short_header"


# ======================================================================= F-efe65849 /
# F-e2be2262 — the naive `scene=None` door on `world_bounds`, and the docstring that
# asserted three live call sites the tree does not have.

def test_world_bounds_requires_a_scene():
    """Re-derived by grep across `tools/` and `tests/` on this worktree: every live call
    passes a scene (`preview_walk:159`, `probe_subject:67`, `stage_render:160`,
    `tests/blender/check_visibility.py:72`), and the single omission left,
    `tools/superseded/render_reference.py:183`, is inside `UNFILTERED_BAN_EXEMPT_DIRS` by
    name and date. Zero live call sites, not three."""
    with blender_stub.blender_stubbed():
        from armature_core import blender_scene as BS
        with pytest.raises(TypeError):
            BS.world_bounds(["a", "b"])


def test_world_bounds_refuses_an_explicit_none_scene_by_name():
    """The second spelling of the same door: passing `scene=None` explicitly must be
    refused toward `unfiltered_world_bounds`, not silently measured naively."""
    with blender_stub.blender_stubbed():
        from armature_core import blender_scene as BS
        with pytest.raises(ArmatureError) as exc:
            BS.world_bounds(["a", "b"], scene=None)
    assert "unfiltered_world_bounds" in str(exc.value)
    assert exc.value.evidence["gate"] is None


def test_the_world_bounds_docstring_no_longer_claims_three_naive_call_sites():
    src = open(os.path.join(CORE, "blender_scene.py"), encoding="utf-8").read()
    fn = src.split("def world_bounds(")[1].split("def unfiltered_world_bounds(")[0]
    assert "three call sites in other domains still omit it" not in fn
    assert "superseded" in fn, "the correction names the one omission that remains"


def test_the_two_unbanned_doors_are_named_so_the_next_session_reads_the_truth():
    """The finding's shape: `evaluated_geometry_signature` and `projected_bbox_px` are the
    doors production actually uses with the scene omitted. The signature-tightening half
    is this domain's; the ban's population half is tests'. The module says which is which
    rather than leaving a reader to infer it."""
    src = open(os.path.join(CORE, "blender_scene.py"), encoding="utf-8").read()
    for door in ("evaluated_geometry_signature", "projected_bbox_px"):
        assert door in src.split("def _points_to_measure(")[1][:4000]


# ============================================================== the -O leg, per refusal
#
# CLAUDE.md: gates raise, never `assert` — an `assert` is deleted by `-O` or
# `PYTHONOPTIMIZE=1`, and 87 of facet's andons turned out to be removable by an environment
# variable. Every refusal this amend ADDED or RE-CLASSED mutates the protected thing here
# and must still fire, under the same class name, with assertions gone. The probe runs in a
# subprocess so the flag is real rather than simulated.

import json as _json          # noqa: E402
import subprocess as _sub     # noqa: E402
import textwrap as _tw        # noqa: E402

TOOLS_DIR = os.path.join(REPO, "tools")

PROBE = _tw.dedent(
    """
    import json, sys, types
    sys.path.insert(0, sys.argv[1])

    import numpy as np
    from armature_core import (aapose, assembly as AS, clipcompare as CC,
                               clipstats as CS, framing, lift_solve as LS, parts,
                               pngio, resample as RS, sitelist, startframe as SF,
                               turnaround as TA, walk)

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

    EXTENT = {"x0": 100.0, "x1": 924.0, "y0": 100.0, "y1": 924.0,
              "n_points": 10, "n_behind": 0}

    def gate_whole_width_nan():
        SF.gate_whole(EXTENT, float("nan"), 1024, 16.0)

    def gate_whole_height_zero():
        SF.gate_whole(EXTENT, 1024, 0, 16.0)

    def view_alpha_nan():
        TA.gate_view_alpha(3, 0, 255, float("nan"))

    def tightened_negative():
        parts.tightened("epsilon_frac", -1.0, 1e-4, parts.GateRigidArrival, {})

    def allowlist_widened():
        AS.gate_no_paid_nodes({"1": {"class_type": "KlingVideoNode"}},
                              allowed=AS.ALLOWED_CLASSES + ("KlingVideoNode",))

    def empty_graph():
        AS.gate_no_paid_nodes({})

    def conv_module_tables_drifted():
        from armature_core import openpose
        aapose.LIMB_SEQ = tuple(tuple(p) for p in openpose.LIMB_SEQ)
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)

    def png_zero_dimension():
        pngio.write_png(sys.argv[2], np.zeros((0, 64, 3), dtype=np.uint8), bit_depth=8)

    def sitelist_inconsistent():
        original = sitelist.BONES
        try:
            sitelist.BONES = list(original) + [original[0]]
            sitelist.validate()
        finally:
            sitelist.BONES = original

    def clipstats_bad_frame():
        CS.luma(np.zeros((4, 4), dtype=np.uint8))

    def clipcompare_length_mismatch():
        CC.order_check([np.zeros((4, 4, 3))], [])

    def world_bounds_without_scene():
        BS.world_bounds(["a", "b"], scene=None)

    def walk_phase_too_short():
        walk.GaitParams(n_walk=0)

    def framing_zero_direction():
        framing._norm((0.0, 0.0, 0.0))

    def resample_zero_tol_still_binds():
        RS.require_rotation([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]],
                            "probe", tol=0.0)

    def lift_solve_arming():
        LS.round_trip_report({}, {}, {}, 1.0, raise_on_fail=True)

    CASES = {
        "gate_whole_width_nan": (gate_whole_width_nan, "StartFrameGate"),
        "gate_whole_height_zero": (gate_whole_height_zero, "StartFrameGate"),
        "view_alpha_nan": (view_alpha_nan, "TurnaroundAlphaGate"),
        "tightened_negative": (tightened_negative, "GateRigidArrival"),
        "allowlist_widened": (allowlist_widened, "AssemblyGate"),
        "empty_graph": (empty_graph, "AssemblyGate"),
        "conv_module_tables_drifted": (conv_module_tables_drifted, "ArmatureError"),
        "png_zero_dimension": (png_zero_dimension, "PngWriteError"),
        "sitelist_inconsistent": (sitelist_inconsistent, "SiteListError"),
        "clipstats_bad_frame": (clipstats_bad_frame, "ClipStatsError"),
        "clipcompare_length_mismatch": (clipcompare_length_mismatch, "ClipCompareError"),
        "world_bounds_without_scene": (world_bounds_without_scene,
                                       "MeasurementWithoutScene"),
        "walk_phase_too_short": (walk_phase_too_short, "WalkError"),
        "framing_zero_direction": (framing_zero_direction, "FramingError"),
        "resample_zero_tol_still_binds": (resample_zero_tol_still_binds, "ResampleGate"),
        "lift_solve_arming": (lift_solve_arming, "SolveError"),
    }

    out = {"asserts_active": asserts_active, "raised": {}}
    for name, (fn, want) in CASES.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except BaseException as exc:
            got = type(exc).__name__
            out["raised"][name] = "RAISED" if got == want else "WRONG_ERROR:" + got
    print("AMEND12 " + json.dumps(out))
    """
)


def _run_probe(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"w12_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = ([sys.executable] + (["-O"] if flag else [])
           + [str(script), TOOLS_DIR, str(tmp_path / "probe.png")])
    proc = _sub.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr)
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("AMEND12 ")]
    if not line:
        raise AssertionError(proc.stdout + proc.stderr)
    return _json.loads(line[-1][len("AMEND12 "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_refusal_this_amend_added_survives_optimization(tmp_path, flag, env_var,
                                                              label):
    res = _run_probe(tmp_path, flag=flag, env_var=env_var)
    assert len(res["raised"]) == 16, res["raised"]
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_optimization_actually_took_effect(tmp_path):
    """Otherwise the parametrisation above is three copies of the same run."""
    assert _run_probe(tmp_path, flag=False)["asserts_active"] is True
    assert _run_probe(tmp_path, flag=True)["asserts_active"] is False
    assert _run_probe(tmp_path, env_var=True)["asserts_active"] is False
