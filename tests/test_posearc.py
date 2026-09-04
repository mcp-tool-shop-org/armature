"""Tests for the authored-performance kinematics.

This module is the ground truth every E03 measurement is read against, so the fixtures ask
the question the repo demands: *what would this look like if the code were wrong in the
specific way this check exists to catch?* The two ways it can be wrong and still look
plausible are (a) the rotation sign — an arm that goes DOWN to a well-formed −90° is a
perfectly good render of the wrong experiment — and (b) the frame convention, where
dividing by `count` instead of `count - 1` produces an arc that never quite arrives.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from armature_core import posearc  # noqa: E402
from armature_core.errors import SpecError  # noqa: E402

JOINTS = {
    "shoulder_r": (0.090, 0.0, 0.820),
    "elbow_r": (0.250, 0.0, 0.820),
    "wrist_r": (0.400, 0.0, 0.820),
    "head_top": (0.000, 0.0, 1.000),
    "ankle_l": (-0.085, 0.0, 0.045),
}
ARC = posearc.POSE_ARCS["arm_r_raise"]


# ----------------------------------------------------------------- the sign, measured

def test_the_arm_ends_OVERHEAD_and_not_underfoot():
    """The sign check. A +90° rotation about +Y sends +X to −Z — the arm would swing DOWN,
    render cleanly, and answer a different question than the one E03 is asking."""
    _, joints = posearc.joints_at_frame(JOINTS, ARC, 32, 33, 0.0, 90.0)
    wrist = joints["wrist_r"]

    # The wrist must end ABOVE the shoulder, not below it.
    assert wrist[2] > JOINTS["shoulder_r"][2], "the arm went down, not up"
    # And it must end essentially straight overhead: same X as the shoulder.
    assert wrist[0] == pytest.approx(JOINTS["shoulder_r"][0], abs=1e-9)
    assert wrist[2] == pytest.approx(0.820 + (0.400 - 0.090), abs=1e-9)
    # It ends above the top of the head, which is the visible consequence on the sheet.
    assert wrist[2] > JOINTS["head_top"][2]


def test_the_arm_starts_in_the_bind_pose_exactly():
    theta, joints = posearc.joints_at_frame(JOINTS, ARC, 0, 33, 0.0, 90.0)
    assert theta == 0.0
    for name, p in JOINTS.items():
        assert joints[name] == pytest.approx(p, abs=1e-12)


def test_only_the_named_joints_move():
    """A rotation applied to the wrong group is the failure that looks most like success."""
    _, joints = posearc.joints_at_frame(JOINTS, ARC, 20, 33, 0.0, 90.0)
    for still in ("shoulder_r", "head_top", "ankle_l"):
        assert joints[still] == pytest.approx(JOINTS[still], abs=1e-12), f"{still} moved"
    for moved in ARC["moving_joints"]:
        assert joints[moved] != pytest.approx(JOINTS[moved], abs=1e-6)


def test_the_arm_stays_rigid_and_planar():
    """The elbow does not bend, and the arc stays in the plane the camera looks at."""
    for i in (0, 8, 16, 24, 32):
        _, j = posearc.joints_at_frame(JOINTS, ARC, i, 33, 0.0, 90.0)
        def dist(a, b):
            return math.dist(j[a], j[b])
        assert dist("shoulder_r", "elbow_r") == pytest.approx(0.160, abs=1e-9)
        assert dist("elbow_r", "wrist_r") == pytest.approx(0.150, abs=1e-9)
        assert dist("shoulder_r", "wrist_r") == pytest.approx(0.310, abs=1e-9)
        # y is preserved by a rotation about Y — this is what keeps the performance
        # face-on to a camera on the Y axis, with no foreshortening anywhere in it.
        for p in j.values():
            assert p[1] == pytest.approx(0.0, abs=1e-12)


# ------------------------------------------------------- the frame convention, measured

def test_the_arc_reaches_its_END_angle_on_the_LAST_frame():
    """Dividing by `count` instead of `count - 1` leaves the arc 3° short of overhead and
    nothing anywhere would report it. `orbit_azimuth` divides by `count` on purpose because
    a 360° orbit is a closed loop; a performance is not, and must hit both ends."""
    assert posearc.angle_at_frame(0, 33, 0.0, 90.0) == 0.0
    assert posearc.angle_at_frame(32, 33, 0.0, 90.0) == pytest.approx(90.0, abs=1e-12)
    assert posearc.angle_at_frame(16, 33, 0.0, 90.0) == pytest.approx(45.0, abs=1e-12)


def test_the_angle_is_monotonic_across_the_shot():
    angles = [posearc.angle_at_frame(i, 33, 0.0, 90.0) for i in range(33)]
    assert all(b > a for a, b in zip(angles, angles[1:]))


def test_a_one_frame_arc_raises_rather_than_dividing_by_zero():
    with pytest.raises(SpecError, match="at least 2 frames"):
        posearc.angle_at_frame(0, 1, 0.0, 90.0)


# --------------------------------------------------------------------------- the readout

def test_the_readout_crosses_the_midpoint_on_an_integer_frame():
    r = posearc.arc_readout(ARC, 33, 0.0, 90.0)
    assert r["readout_deg"] == 45.0
    assert r["crossing_frame_exact"] == pytest.approx(16.0, abs=1e-12)
    assert r["crossing_frame_nearest"] == 16
    assert r["lands_on_an_integer_frame"] is True
    assert r["reaches_end_frame"] == 32


def test_the_readout_angle_is_actually_reached_by_the_arm_at_that_frame():
    """Ties the readout to the kinematics rather than to arithmetic about the kinematics."""
    r = posearc.arc_readout(ARC, 33, 0.0, 90.0)
    theta, _ = posearc.joints_at_frame(JOINTS, ARC, r["crossing_frame_nearest"], 33, 0.0, 90.0)
    assert theta == pytest.approx(r["readout_deg"], abs=1e-12)


def test_a_zero_span_arc_raises_because_it_is_a_held_pose_not_a_performance():
    """This is the arc that would render 33 identical frames and trip G6 after the work."""
    with pytest.raises(SpecError, match="held pose, not a performance"):
        posearc.arc_readout(ARC, 33, 0.0, 0.0)


def test_an_arc_that_never_reaches_the_readout_angle_raises():
    with pytest.raises(SpecError, match="never be crossed"):
        posearc.arc_readout(ARC, 33, 0.0, 20.0)


def test_unknown_arc_raises_and_names_what_is_known():
    with pytest.raises(SpecError, match="unknown pose arc"):
        posearc.resolve_arc("arm_l_wave")


def test_the_arc_declares_moving_parts_that_match_its_moving_joints():
    """A part list that misses a limb leaves geometry behind mid-air while the joints say
    it moved — the ground truth and the render would disagree and only the eye would know."""
    parts = set(ARC["moving_parts"])
    assert "bone_shoulder_r__elbow_r" in parts, "the upper arm must travel"
    assert "bone_elbow_r__wrist_r" in parts, "the forearm must travel"
    assert "joint_elbow_r" in parts, "the elbow ball must travel with the limb it joins"
    # The pivot's own ball must NOT move: it is the centre of rotation.
    assert f"joint_{ARC['pivot']}" not in parts


# --- F-314c4a79: the record may not name a property no code checked -------------------


def test_over_a_full_span_the_record_does_not_call_the_readout_the_midpoint():
    """Measured at count=33: 0..180 puts the registered readout 45.0deg at
    `crossing_frame_exact` 8.00 while the true midpoint (90deg) is frame 16.00 — off by 8
    of 32 frames, under a note that read "The readout is the MIDPOINT crossing". The only
    guard was the "lies outside the arc" clause, which a 0..180 arc satisfies. This is the
    class this repo pays for most often: a verdict naming a property no code checked, and
    it sat in the timing quantity the experiment is read by.
    """
    r = posearc.arc_readout(ARC, 33, 0.0, 180.0)
    assert r["readout_deg"] == 45.0
    assert r["crossing_frame_exact"] == pytest.approx(8.0, abs=1e-12)
    assert r["midpoint_deg"] == pytest.approx(90.0)
    assert r["midpoint_frame_exact"] == pytest.approx(16.0, abs=1e-12)
    assert r["is_the_midpoint"] is False
    # Either the crossing frame IS the midpoint frame, or the record does not claim it is.
    assert (r["crossing_frame_exact"] == pytest.approx(r["midpoint_frame_exact"])
            or "is NOT the midpoint" in r["note"])
    assert "MIDPOINT crossing" not in r["note"]


def test_on_the_shipped_probe_span_the_two_coincide_and_the_record_says_so():
    """0..90 is what `rig_character.py:661` uses, and there the registered readout and the
    midpoint are the same frame — by coincidence of the numbers, which is exactly why the
    record has to state it rather than assume it."""
    r = posearc.arc_readout(ARC, 33, 0.0, 90.0)
    assert r["is_the_midpoint"] is True
    assert r["crossing_frame_exact"] == pytest.approx(r["midpoint_frame_exact"])
    assert "IS the midpoint" in r["note"]


def test_the_midpoint_is_derived_from_the_span_it_is_given():
    """A property computed from the arc, not a constant: it moves with both ends."""
    for start, end in ((0.0, 90.0), (0.0, 180.0), (30.0, 60.0), (-90.0, 90.0)):
        r = posearc.arc_readout(dict(ARC, readout_deg=0.5 * (start + end)),
                                33, start, end)
        assert r["midpoint_deg"] == pytest.approx(0.5 * (start + end))
        assert r["is_the_midpoint"] is True
        assert r["midpoint_frame_exact"] == pytest.approx(16.0, abs=1e-9)


# --------------------------- wave 10: a record field that cannot be False is not evidence


def test_the_monotonic_flag_is_labelled_as_an_invariant_rather_than_read_as_a_measurement():
    """F-93f0e38f. `arc_readout` returned `"monotonic": True` as a literal beside eleven
    fields computed from the arc. Nothing measures it — `angle_at_frame` is linear in the
    frame index by construction, so it takes the same value when the arc is what it claims
    and when it is anything else, which is the "grade an arm only on what it can move" law
    and a placeholder shaped like evidence in a record the E03 report quotes.

    The repo already had the right shape one module over, so it is carried rather than
    re-invented: `binding.rigid_segment_weights` returns `invariant_by_construction` naming
    the three fields that cannot take another value, "so no report can quote a constant as
    corroboration".
    """
    for count, start, end in ((33, 0.0, 90.0), (17, 90.0, 0.0), (9, 0.0, 90.0)):
        rec = posearc.arc_readout(ARC, count, start, end)
        assert rec["monotonic"] is True
        assert "monotonic" in rec["invariant_by_construction"]
        assert "linear in the frame index" in rec["invariant_by_construction_note"]


def test_every_labelled_invariant_is_a_key_the_record_actually_carries():
    """The label is only worth having if it names real fields — the same subset check
    `binding`'s siblings get, so a renamed field cannot leave the note pointing at nothing.
    """
    rec = posearc.arc_readout(ARC, 33, 0.0, 90.0)
    assert set(rec["invariant_by_construction"]) <= set(rec)


def test_the_fields_beside_it_can_still_take_more_than_one_value():
    """The direction that makes the label mean something: the rest of this record IS
    measured, so labelling `monotonic` is a statement about one field and not a shrug at
    the record."""
    a = posearc.arc_readout(ARC, 33, 0.0, 90.0)
    b = posearc.arc_readout(ARC, 33, 0.0, 120.0)
    assert a["crossing_frame_exact"] != b["crossing_frame_exact"]
    assert a["is_the_midpoint"] and not b["is_the_midpoint"]
