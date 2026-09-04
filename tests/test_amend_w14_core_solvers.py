"""Wave-14 core-solvers amend — the red proofs for eight routed findings.

Every test here was written before the fix it names and run against the wave-14 base
(`4d21bec`) to see it fail, then run once more with the fix reverted (`git stash`) to
prove the guard and not its neighbour is what turns it green.

**The rule this wave adds, and what it changes about these fixtures.** Wave 12's guards
landed one operand, one level or one caller away from the defect they were written for:
`require_finite` sat on every THRESHOLD and on none of the MEASURED quantities the gates
compare, so a NaN observation passed every one. So each test below names the operand it
drives — a NaN in the *measurement* with the bounds finite; a *negative* per-interval
advance; the exact fifteen partner class names the auditor measured zero recall on; an
all-equal gradient column — and asserts on the clause that must fire, never on "something
raised".
"""

import hashlib
import json
import math
import os
import sys

import numpy as np
import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import blender_stub  # noqa: E402,F401

from armature_core import (aapose, assembly, clipstats, lift_solve, parts,  # noqa: E402
                           route_gates, startframe, turnaround, walk)
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

NAN = float("nan")
TAU = 2.0 * math.pi


# ====================================================================== F-5733588e
# Gate RIGID applied `require_finite` to every BOUND and to none of the three
# MEASUREMENTS its clauses compare. Measured on the base with clean bounds
# (`bbox_diagonal=1.0`, both fractions defaulted) and one part whose three
# measurements are NaN beside one healthy part: the gate RETURNED
# "2 parts each landed on their own bone transform; figure max displacement nan".
# Both clauses are `>` comparisons, which NaN fails in both directions, and the
# vacuity guard `moved <= tol` is switched off by the same value.

RIGID_MEASURED = ("max_transform_error", "max_pair_distance_change", "max_displacement")


def _rigid_obs(**overrides):
    """One healthy part beside one whose named measurement is the bad value."""
    bad = {"name": "bad", "max_transform_error": 0.0,
           "max_pair_distance_change": 0.0, "max_displacement": 0.5}
    bad.update(overrides)
    return [{"name": "good", "max_transform_error": 0.0,
             "max_pair_distance_change": 0.0, "max_displacement": 0.5}, bad]


@pytest.mark.parametrize("field", RIGID_MEASURED)
@pytest.mark.parametrize("bad", [NAN, float("inf"), float("-inf")])
def test_gate_rigid_refuses_a_non_finite_measurement_with_every_bound_finite(field, bad):
    """The operand is the MEASUREMENT, and every bound this gate reads is finite.

    `bbox_diagonal=1.0` and both fractions defaulted, so the wave-8 and wave-12 guards
    (which cover `epsilon_frac`, `rigidity_frac` and `bbox_diagonal`) all pass and are
    not what makes this red.
    """
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival(_rigid_obs(**{field: bad}), 1.0)
    ev = exc.value.evidence
    assert "is not a finite" in str(exc.value)
    assert field in str(exc.value) or any(field in k for k in ev)
    # the bounds were fine; this refusal is not the neighbour's
    assert math.isfinite(ev["bbox_diagonal"]) and ev["bbox_diagonal"] == 1.0


def test_gate_rigid_still_passes_a_clean_observation_set():
    """The guard bounds finiteness, not magnitude: a healthy set still returns."""
    obs = [{"name": "a", "max_transform_error": 0.0,
            "max_pair_distance_change": 0.0, "max_displacement": 0.5}]
    ev = parts.gate_rigid_arrival(obs, 1.0)
    assert ev["verdict"].startswith("1 parts")


def test_gate_rigid_names_the_part_the_bad_measurement_came_from():
    """Per-structure reporting: the refusal says WHICH part, never only that one was bad."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival(_rigid_obs(max_displacement=NAN), 1.0)
    assert "bad" in str(exc.value) or "bad" in json.dumps(exc.value.evidence, default=str)


# `lift_solve.gate_round_trip` is the same shape one module over: `require_finite` on
# `diagonal`, `tightened` on `tol_frac`, and nothing on the per-site distances the
# comparison reads. A NaN residual is worse there than in Gate RIGID: `d > worst["d"]`
# is False for a NaN, so the bad site is silently DROPPED from `worst` and the verdict
# quotes a healthy maximum over a population one of whose members is not a number.

def test_gate_round_trip_refuses_a_non_finite_per_site_residual():
    import test_lift_solve as T  # the suite's synthetic rig, one copy
    rest = T.synthetic_rest()
    authored = T.motion(T.LIMB_MOTION, root=(0.02, -0.03, 0.01))
    obs = T.observed_from(rest, authored)
    solved = lift_solve.solve_frame(rest, obs)
    lift_solve.gate_round_trip(rest, obs, solved, T.DIAGONAL)          # clean first

    site = sorted(lift_solve.SITE_FROM_LANDMARK)[0]
    dirty = dict(obs)
    dirty[site] = (NAN, obs[site][1], obs[site][2])
    with pytest.raises(lift_solve.SolveGate) as exc:
        lift_solve.gate_round_trip(rest, dirty, solved, T.DIAGONAL)
    assert "is not a finite" in str(exc.value)
    ev = exc.value.evidence
    assert math.isfinite(ev["bbox_diagonal"])          # the bound was fine


# ====================================================================== F-bed000c4
# Gate CADENCE's comparison was sign-blind and NaN-permeable and its evidence
# reported `max(du)` over the SIGNED intervals, which is the number that hides both.

def _reverse_phase():
    """The auditor's exact reproduction: `steps` mutated negative after construction."""
    p = walk.GaitParams(n_walk=4, n_decel=2, n_gesture=1, n_hold=1, steps=5)
    p.steps = -12
    return p, walk._phase_schedule(p)[1]


def test_gate_cadence_refuses_a_reverse_cadence_of_the_same_magnitude():
    """The invariant is about the sampling rate, which is symmetric in sign.

    Measured on the base: five intervals each advancing -1.278 cycles/frame — 2.56x the
    0.5 limit — RETURNED with `max_cycles_per_frame: 0.0`, because `max()` over the
    signed list picked the 0.0 hold interval. The same magnitude forwards refuses, so
    which way the gait ran decided whether the andon existed.
    """
    _, phase = _reverse_phase()
    signed = [(phase[i] - phase[i - 1]) / TAU for i in range(1, len(phase))]
    assert min(signed) < -walk.MAX_CYCLES_PER_FRAME       # the operand really is negative
    assert max(signed) <= walk.MAX_CYCLES_PER_FRAME       # and forwards it looks clean
    with pytest.raises(walk.CadenceGate) as exc:
        walk.gate_cadence_is_representable(phase, 0.5)
    ev = exc.value.evidence
    assert ev["n_intervals_over_half_a_cycle"] >= 5
    assert ev["max_cycles_per_frame"] == pytest.approx(max(abs(d) for d in signed))
    assert ev["signed_extreme_cycles_per_frame"] == pytest.approx(min(signed))


def test_gate_cadence_evidence_reports_the_magnitude_not_the_signed_max():
    """A representable REVERSE walk still returns, and its receipt quotes |du|."""
    phase = [0.0, -0.1 * TAU, -0.2 * TAU, -0.3 * TAU]
    ev = walk.gate_cadence_is_representable(phase, 0.5)
    assert ev["max_cycles_per_frame"] == pytest.approx(0.1)
    assert ev["signed_extreme_cycles_per_frame"] == pytest.approx(-0.1)
    assert "0.100" in ev["verdict"]


def test_gate_cadence_refuses_a_non_finite_phase_interval():
    """`nan > 0.5` is False in both directions and `max()` skips it: the base
    RETURNED `max_cycles_per_frame: 0.3` over a population two of whose four members
    were not numbers."""
    with pytest.raises(walk.CadenceGate) as exc:
        walk.gate_cadence_is_representable([0.0, 0.3 * TAU, NAN, 0.9 * TAU, 1.2 * TAU])
    assert "is not a finite" in str(exc.value)


def test_build_gait_re_checks_steps_after_construction():
    """`GaitParams.__init__` refuses `steps < 1`; `build_gait` re-validated only
    `stance_frac`, whose own docstring says it is re-called there 'so mutating the
    attribute after construction does not get past it'. The identical mutation on
    `steps` walked straight through."""
    import test_walk as W
    performer = walk.Performer(W.LANDMARKS, W.FACING_Y_SIGN, W.LEFT_X_SIGN)
    p, _ = _reverse_phase()
    with pytest.raises(walk.WalkError) as exc:
        walk.build_gait(performer, p)
    ev = getattr(exc.value, "evidence", {}) or {}
    assert ev.get("clause") == "no_steps"
    assert ev.get("where") == "build_gait"


# ====================================================================== F-594e1792
# The clause wave 12 installed to replace a falsified one has the same recall on the
# same population: zero. `RULED_COMPONENTS` carries only LoRA and preprocessor rows,
# so the "licence second opinion" can never fire on a paid node — the class of thing
# this gate exists for — and the verdict printed two licence properties nothing
# measured, on the last free-chain gate before an assembly payload is submitted.

#: The exact population the auditor measured zero recall on.
PARTNER_CLASS_NAMES = (
    "KlingVideoNode", "LumaVideoNode", "MinimaxVideoNode", "VeoVideoNode", "IdeogramV3",
    "RecraftTextToImageNode", "PixverseTextToVideoNode", "RunwayImageToVideoNode",
    "MoonvalleyTxt2VideoNode", "GeminiNode", "OpenAIDalle3",
    "StabilityStableImageUltraNode", "FluxProImageNode", "PikaImageToVideoNode",
    "ViduImageToVideoNode",
)


def test_the_licence_map_still_rules_on_none_of_the_partner_class_names():
    """The measurement that falsified the replacement clause, pinned so the day the map
    grows a partner-node row family this test says so instead of going quietly stale."""
    hits = {c: len(route_gates.rulings_for_class(c)) for c in PARTNER_CLASS_NAMES}
    assert set(hits.values()) == {0}, hits


@pytest.mark.parametrize("cls", PARTNER_CLASS_NAMES)
def test_gate_no_paid_nodes_refuses_a_partner_class_admitted_by_a_widened_constant(
        cls, monkeypatch):
    """The direction the narrowing guard leaves open, driven on the auditor's own call.

    `parts.narrowed` refuses a CALLER widening the allowlist, so the only widening left
    is a diff to `ALLOWED_CLASSES` itself — which the wave-12 docstring names as the
    clause's reason for existing. Measured on the base with the constant widened by
    ('KlingVideoNode',): the gate RETURNED with `licence_rulings: {}` and the verdict
    "...none reading as a partner class, and 0 carrying a licence-map ruling (none
    BANNED/EXCLUDED)".
    """
    monkeypatch.setattr(assembly, "ALLOWED_CLASSES",
                        assembly.ALLOWED_CLASSES + (cls,))
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes({"1": {"class_type": cls}})
    ev = exc.value.evidence
    assert ev["clause"] == "class_without_a_recorded_free_measurement"
    assert ev["classes_without_a_free_measurement"] == [cls]


def test_gate_no_paid_nodes_verdict_names_only_what_it_measured():
    """A verdict must name only clauses that ran against a population that can fail
    them. 'none BANNED/EXCLUDED' over an empty `ruled` reads as a clearance where it
    means 'the map has never heard of this class'."""
    ev = assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"},
                                      "2": {"class_type": "SaveVideo"}})
    assert "BANNED/EXCLUDED" not in ev["verdict"]
    assert ev["classes_unknown_to_the_licence_map"] == ["LoadImage", "SaveVideo"]
    assert "0 of 2" in ev["verdict"]
    assert ev["n_classes_ruled_by_the_licence_map"] == 0


def test_every_module_allowlist_class_carries_its_free_measurement():
    """The record is the population the new clause rules on; it must cover the four."""
    assert set(assembly.ALLOWED_CLASSES) <= set(assembly.MEASURED_FREE_CLASSES)
    for cls, rec in assembly.MEASURED_FREE_CLASSES.items():
        assert rec["api_node"] is False
        assert rec["measured_on"] and rec["measured_with"]


def test_gate_no_paid_nodes_still_refuses_a_banned_licence_class():
    """The licence second opinion keeps the recall it does have: a BANNED preprocessor
    or LoRA class is still refused, and the clause that fires is named."""
    banned = None
    for key, rec in route_gates.RULED_COMPONENTS.items():
        if rec.get("verdict") in ("BANNED", "EXCLUDED"):
            pats = route_gates.class_patterns_for(key)
            if pats:
                banned = pats[0]
                break
    assert banned, "no BANNED/EXCLUDED row with a class pattern in the licence map"
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes({"1": {"class_type": banned}})
    assert exc.value.evidence["licence_refused"] == [banned]


# ====================================================================== F-eb8689f1
# `horizon_row` reports unanimous agreement on a frame with no edge at all, because
# `np.argmax` over an all-equal column returns index 0 — the argmin tie-breaking
# defect F-2ceefec7 closed in `clipcompare.order_check`, recurring in the sibling
# instrument of the same pair.

def test_horizon_row_returns_none_on_a_uniform_plate():
    """Measured on the base: a uniform 64x64x3 plate of value 30 returned
    `{'row': 1.0, 'agreement': 1.0, 'edge_strength': 0.0, 'verdict': 'found'}` — the
    agreement statistic reading its maximum precisely where there is no information."""
    out = clipstats.horizon_row(np.full((64, 64, 3), 30, dtype=np.uint8))
    assert out["row"] is None
    assert out["n_columns_with_an_edge"] == 0
    assert out["verdict"].startswith("NOT FOUND")


def test_horizon_row_returns_none_on_a_smooth_vertical_ramp():
    """Also edgeless: every row of every column carries the same gradient, so every
    argmax is a tie the tie-break resolves to the top of the band."""
    col = np.linspace(0.0, 200.0, 64).reshape(64, 1, 1)
    ramp = np.tile(col, (1, 64, 3))
    out = clipstats.horizon_row(ramp)
    assert out["row"] is None
    assert out["n_columns_with_an_edge"] == 0


def test_horizon_row_still_finds_a_real_step_edge():
    """The guard must not disarm the instrument: a real discontinuity still reads."""
    step = np.zeros((64, 64, 3), dtype=np.uint8)
    step[32:] = 170
    out = clipstats.horizon_row(step)
    assert out["row"] == pytest.approx(31.0, abs=1.5)
    assert out["verdict"] == "found"
    assert out["n_columns_with_an_edge"] == 64


def test_horizon_row_counts_only_columns_that_carry_an_edge():
    """A column with nothing to say does not vote: half the frame edgeless, half a
    clean step, and the agreement is read over the half that has an edge."""
    frame = np.zeros((64, 64, 3), dtype=np.float64)
    frame[32:, :32] = 170.0                       # left half: a step at row 32
    frame[:, 32:] = 40.0                          # right half: flat
    out = clipstats.horizon_row(frame)
    assert out["n_columns_with_an_edge"] == 32
    assert out["row"] == pytest.approx(31.0, abs=1.5)
    assert out["agreement"] == pytest.approx(1.0)


def test_horizon_row_still_refuses_a_noise_frame():
    """Unchanged behaviour: many columns carry an edge and they disagree."""
    rng = np.random.default_rng(0)
    out = clipstats.horizon_row(rng.integers(0, 255, (64, 64, 3)).astype(np.uint8))
    assert out["row"] is None
    assert out["n_columns_with_an_edge"] > 0


# ====================================================================== F-d0de0c2d
# Gate CONV's two refusals passed no evidence argument at all, so a Gate CONV halt
# wrote a null receipt at the one door where a mis-drawn skeleton reaches the model.

def test_gate_conv_digest_drift_refusal_carries_a_receipt(monkeypatch):
    monkeypatch.setattr(aapose, "RECORDED_CONVENTION_SHA256", "0" * 64)
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    ev = exc.value.evidence
    assert ev["gate"] is None and ev["andon"] == "ConventionError"
    assert ev["clause"] == "recorded_convention_digest_drift"
    assert ev["pinned_sha256"] == "0" * 64
    assert ev["computed_sha256"] == aapose.recorded_convention_digest()


def test_gate_conv_nonconformance_refusal_carries_a_receipt(monkeypatch):
    monkeypatch.setattr(aapose, "LIMB_BRIGHTNESS", 1.0)
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    ev = exc.value.evidence
    assert ev["gate"] is None and ev["andon"] == "ConventionError"
    assert ev["clause"] == "convention_nonconformance"
    assert ev["problems"] and ev["banked_source"] in ("verified", "MISMATCH", "absent")
    assert ev["computed_sha256"] == aapose.recorded_convention_digest()


def test_convention_error_is_in_the_armature_error_family():
    """The 21-tool halt contract classifies on the family; a Gate CONV refusal is a
    REFUSED at exit 2, not an unhandled crash."""
    assert issubclass(aapose.ConventionError, ArmatureError)
    assert not issubclass(aapose.ConventionError, GateFailure)


# ====================================================================== F-d59fab92
# `RECORDED_CONVENTION` carries nine fields; `check_convention` compared five. The
# record's `hand_keypoint_count` and `limb_brightness` were pinned by the digest and
# compared against nothing, and `HAND_JOINT_COLOR` / `DEFAULT_THRESHOLD` were in
# neither the record nor the comparison. All four decide what pixels are drawn.

@pytest.mark.parametrize("const,bad", [
    ("LIMB_BRIGHTNESS", 1.0),
    ("HAND_KEYPOINT_COUNT", 18),
    ("HAND_JOINT_COLOR", (255, 0, 0)),
    ("DEFAULT_THRESHOLD", 0.0),
])
def test_gate_conv_fires_on_every_drawing_constant_the_record_pins(const, bad,
                                                                  monkeypatch):
    """Measured on the base with all four edited at once: `check_convention` returned
    verdict PASS with the unchanged detail line '20 keypoints / 19 pairs / 20 palette
    entries, module tables and caller both equal to RECORDED_CONVENTION'."""
    monkeypatch.setattr(aapose, const, bad)
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    problems = exc.value.evidence["problems"]
    assert any(const.lower().replace("_", " ") in p.lower() or const.lower() in p.lower()
               for p in problems), problems


def test_the_record_pins_every_drawing_constant_the_gate_compares():
    """Coverage stated as data, so a constant added to the module without a recorded
    value is visible rather than silently outside the gate."""
    for key in ("hand_keypoint_count", "limb_brightness", "hand_joint_color",
                "default_threshold"):
        assert key in aapose.RECORDED_CONVENTION
    assert aapose.RECORDED_CONVENTION["hand_joint_color"] == list(aapose.HAND_JOINT_COLOR)
    assert aapose.RECORDED_CONVENTION["default_threshold"] == aapose.DEFAULT_THRESHOLD


def test_the_recorded_digest_is_the_digest_of_the_record_as_written():
    blob = json.dumps(aapose.RECORDED_CONVENTION, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(blob).hexdigest() == aapose.RECORDED_CONVENTION_SHA256


def test_the_banked_source_is_checked_against_the_hash_the_digest_pins(tmp_path,
                                                                      monkeypatch):
    """The banked-source clause compared against `SOURCE['sha256']`, which is OUTSIDE
    the digest, rather than against `record['source_sha256']`, which is inside it. The
    two are equal today and were never compared to each other, so the one hash the pin
    protects was not the one the file was checked against."""
    assert aapose.RECORDED_CONVENTION["source_sha256"] == aapose.SOURCE["sha256"]
    body = b"not the fetched source"
    banked = tmp_path / "human_visualization.py"
    banked.write_bytes(body)
    monkeypatch.setattr(aapose, "BANKED_SOURCE", str(banked))
    # SOURCE drifts to agree with the file; the RECORD is what the digest protects, so
    # the state must still read MISMATCH.
    monkeypatch.setitem(aapose.SOURCE, "sha256", hashlib.sha256(body).hexdigest())
    state, got = aapose.banked_source_state()
    assert state == "MISMATCH", "the state must be read against the RECORD's hash"
    assert got == hashlib.sha256(body).hexdigest()


# ====================================================================== F-c4cf355d
# Gate TURN's duplicate clause is a byte-hash equality test, and the property it is
# written to catch is a camera that did not move. CLAUDE.md: "A file-hash mismatch is
# not evidence a render changed. Compare pixels; reserve byte-hashes for artifacts
# whose bytes are the contract."

def _view(i, plane):
    return {"view": i, "sha256": f"{i:064x}", "pixels": plane}


def test_gate_turn_refuses_eight_byte_distinct_copies_of_one_view():
    """The operand: eight files with eight different digests whose PIXELS are one
    view eight times — an orbit helper that advanced by a rounding error rather than
    by zero, or a camera that moved a hundredth of a degree per view. On the base this
    returned the gate's strongest verdict, '8 distinct views, as many as were asked
    for'."""
    plane = np.zeros((32, 32, 3), dtype=np.float64)
    plane[8:24, 8:24] = 200.0
    records = [_view(i, plane.copy()) for i in range(8)]
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.gate_set_distinct(records, 8)
    ev = exc.value.evidence
    assert ev["clause"] == "views_identical_in_pixels"
    assert ev["n_pairs_identical_in_pixels"] == 7


def test_gate_turn_passes_a_set_whose_views_really_differ():
    rng = np.random.default_rng(3)
    records = [_view(i, rng.normal(128.0, 40.0, (32, 32, 3))) for i in range(8)]
    ev = turnaround.gate_set_distinct(records, 8)
    assert ev["n_pairs_identical_in_pixels"] == 0
    assert ev["n_views_compared_in_pixels"] == 8
    assert "distinct in PIXELS over 8 of 8" in ev["verdict"]
    assert ev["min_adjacent_pixel_distance"] > 0.0


def test_gate_turn_verdict_says_so_when_no_view_carried_pixels():
    """A verdict must name only clauses that ran. With digest-only records the pixel
    clause cannot run, and the verdict says that rather than calling the set
    'distinct'."""
    ev = turnaround.gate_set_distinct(
        [{"view": i, "sha256": f"{i:064x}"} for i in range(8)], 8)
    assert ev["n_views_compared_in_pixels"] == 0
    assert "NOT compared" in ev["verdict"]


def test_gate_turn_still_refuses_byte_identical_views():
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.gate_set_distinct(
            [{"view": i, "sha256": "ab" * 32} for i in range(8)], 8)
    assert exc.value.evidence["clause"] == "views_byte_identical"


# ====================================================================== F-3bc3659d
# The refusal message asserted a fact that is false in the case that most often
# produces it: `xs` is empty when `points` is empty, and the message then read
# "every one of 0 points is behind the camera" beside `n_behind: 0`.

CAM = dict(target=(0.0, 0.0, 0.0), radius=5.0, azimuth_deg=0.0, elevation_deg=0.0,
           lens_mm=50.0, sensor_mm=36.0, width=512, height=512)


def test_empty_point_cloud_is_refused_by_its_own_clause():
    with pytest.raises(startframe.StartFrameGate) as exc:
        startframe.silhouette_extent([], **CAM)
    ev = exc.value.evidence
    assert ev["clause"] == "no_points_given"
    assert ev["n_points"] == 0 and ev["n_behind"] == 0
    assert "behind the camera" not in str(exc.value)


def test_a_cloud_entirely_behind_the_camera_keeps_its_own_clause():
    behind = [(100.0, 0.0, 0.0), (101.0, 1.0, 1.0)]   # measured: `project` returns ok=False
    with pytest.raises(startframe.StartFrameGate) as exc:
        startframe.silhouette_extent(behind, **CAM)
    ev = exc.value.evidence
    assert ev["clause"] == "every_point_behind_the_camera"
    assert ev["n_points"] == 2 and ev["n_behind"] == 2
    assert "every one of 2 points is behind the camera" in str(exc.value)


def test_gate_whole_refuses_an_extent_over_zero_points():
    """`gate_whole` read `extent.get('n_points')` into its evidence and gated on
    `n_behind` but never on `n_points`, so an extent dict built by any other path with
    zero points would reach a PASS. No such path exists in the tree today; the andon
    goes on the direction the invariant does not bound."""
    ext = {"x0": 100.0, "x1": 400.0, "y0": 100.0, "y1": 400.0,
           "n_behind": 0, "n_points": 0}
    with pytest.raises(startframe.StartFrameGate) as exc:
        startframe.gate_whole(ext, 512, 512, 16.0)
    assert exc.value.evidence["clause"] == "extent_over_zero_points"
