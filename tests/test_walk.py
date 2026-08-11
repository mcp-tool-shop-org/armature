"""Tests for the gait model — E08's commission.

Every fixture below was written by asking the question CLAUDE.md demands: *what would
this look like if the code were wrong in the specific way this check exists to catch?*
Two of them (`test_forward_travel_is_not_a_dialled_in_constant`, `test_knee_never_bends_forward`)
answer that with a **deliberately broken gait built in the test**, because a threshold
picked by the same session that wrote the code it grades is not a check — it is a
preference. Comparing against a known-wrong implementation is.
"""

import math

import pytest

from armature_core import sitelist, walk


# The measured character — E07's `performer_auto.glb`, read out of its rig manifest.
# Held here as a fixture so the gait's arithmetic is pinned against a real body rather
# than a symmetric toy that would hide a handedness bug.
LANDMARKS = {
    "crotch": [0.0, -0.0006940506396546584, 0.09013529837131495],
    "spine_base": [0.0, -0.0006940506396546584, 0.16276808008551596],
    "chest_base": [0.0, -0.0006940506396546584, 0.23540086179971695],
    "neck_base": [0.0, -0.0006940506396546584, 0.30803364351391793],
    "head_base": [0.0, -0.0006940506396546584, 0.31805195823311805],
    "head_top": [0.0, -0.0006940506396546584, 0.5008862018585205],
    "shoulder_L": [0.09275070150431834, 0.0094478502936047, 0.2842401460558176],
    "elbow_L": [0.1528999652263399, 0.004753624026222313, 0.00019168854907726345],
    "wrist_L": [0.1438070055946485, -0.012335006685791176, -0.13466060843118074],
    "hand_end_L": [0.1271223249760541, -0.02454659379807047, -0.2454782447218895],
    "shoulder_R": [-0.08907494030004956, 0.010097877648215707, 0.2842401460558176],
    "elbow_R": [-0.14900356787396413, 0.01660645046252496, 0.013186038282886576],
    "wrist_R": [-0.1441543335578029, 0.0004102049044769581, -0.13830703889385865],
    "hand_end_R": [-0.12732619295517603, -0.006212402833625674, -0.2454782447218895],
    "hip_L": [0.04559906323750814, 0.016744044664341748, 0.09013529837131495],
    "knee_L": [0.05120297933653532, -0.006778942472445088, -0.1512646613903969],
    "ankle_L": [0.07592608329529564, 0.014102310313319322, -0.4633765898644924],
    "toe_L": [0.07592608329529564, -0.08368825912475586, -0.5009452700614929],
    "hip_R": [-0.02467412936675828, 0.01590917509747669, 0.09013529837131495],
    "knee_R": [-0.06755729096054348, -0.0005150250592855024, -0.16092250072412295],
    "ankle_R": [-0.05206753941321814, 0.05623684009468114, -0.4633765898644924],
    "toe_R": [-0.05206753941321814, -0.027832822874188423, -0.5009452700614929],
}
FACING_Y_SIGN = -1.0   # measured: rig_manifest_auto.json -> facing.facing_y_sign
LEFT_X_SIGN = 1.0      # measured: rig_manifest_auto.json -> facing.left_x_sign


@pytest.fixture
def performer():
    return walk.Performer(LANDMARKS, FACING_Y_SIGN, LEFT_X_SIGN)


@pytest.fixture
def gait(performer):
    return walk.build_gait(performer, walk.GaitParams())


# --------------------------------------------------------------- the registration


def test_parent_table_agrees_with_the_committed_site_list():
    """The gait carries its own parent map so FK can run without bpy. Two copies of one
    fact drift; this is what makes the drift fail instead."""
    registered = {b.name: b for b in sitelist.BONES}
    for bone, parent in walk.PARENT.items():
        assert bone in registered, f"{bone} is not a registered site"
        assert registered[bone].parent == parent, (
            f"{bone}: gait says parent {parent!r}, the site list says "
            f"{registered[bone].parent!r}"
        )
        assert registered[bone].head == walk.HEAD_LANDMARK[bone]


def test_gait_bones_are_exactly_the_deforming_ones():
    """The five facial markers are registered `use_deform=False`. Keying them would
    write channels that cannot move a rendered pixel; omitting a deforming bone would
    leave part of the body behind when he walks."""
    deforming = {b.name for b in sitelist.BONES if b.deform}
    assert set(walk.GAIT_BONES) == deforming


# ------------------------------------------------------------------ basic contract


def test_frame_count_and_phase_names(gait):
    p = walk.GaitParams()
    assert p.n_frames == 65
    assert len(gait["frames"]) == 65
    names = [f["phase_name"] for f in gait["frames"]]
    assert names[:40] == ["walk"] * 40
    assert names[40:48] == ["decelerate"] * 8
    assert names[48:60] == ["gesture"] * 12
    assert names[60:] == ["hold"] * 5


def test_determinism(performer):
    """Same inputs, identical floats. Compared as parsed objects — never as bytes: a
    file-hash mismatch is not evidence anything changed, and a hash match on a dict
    would not prove the numbers inside it are equal either."""
    a = walk.build_gait(performer, walk.GaitParams())
    b = walk.build_gait(walk.Performer(LANDMARKS, FACING_Y_SIGN, LEFT_X_SIGN),
                        walk.GaitParams())
    assert a["frames"] == b["frames"]
    assert a["phase_rad"] == b["phase_rad"]
    assert a["derived"] == b["derived"]


def test_the_walk_stops_with_the_feet_together(gait):
    """omega is SOLVED so the stop lands on a half-step boundary — the legs passing —
    and the amplitude envelope has reached zero by then, so both legs are straight and
    together. If the rate were merely typed in, the figure would freeze mid-stride."""
    p = walk.GaitParams()
    final_phase = gait["phase_rad"][-1]
    assert final_phase == pytest.approx((p.steps + 0.5) * math.pi, abs=1e-9)
    last = gait["frames"][-1]["pose"]
    assert last["hip.L"]["rx"] == pytest.approx(0.0, abs=1e-9)
    assert last["hip.R"]["rx"] == pytest.approx(0.0, abs=1e-9)
    assert last["knee.L"]["rx"] == pytest.approx(0.0, abs=1e-9)
    assert last["knee.R"]["rx"] == pytest.approx(0.0, abs=1e-9)


def test_gait_speed_envelope(gait):
    speeds = gait["gait_speed"]
    assert speeds[:40] == [1.0] * 40
    assert speeds[47] == pytest.approx(0.0, abs=1e-12)
    assert all(s == 0.0 for s in speeds[48:])
    assert all(speeds[i] >= speeds[i + 1] for i in range(40, 47))


def test_legs_and_arms_are_antiphase(gait):
    """The two legs are half a cycle apart — NOT exact negatives of one another, because
    stance is a linear ramp and swing is a smootherstep, so the profiles differ by shape.
    What must hold is that one leg is forward while the other is back, and that each arm
    opposes its own side's leg. Same-sign arm and leg is the zombie walk: a reader spots
    it on the sheet in a second and no aggregate number would ever say so."""
    for rec in gait["frames"][:44]:
        pose = rec["pose"]
        hl, hr = pose["hip.L"]["rx"], pose["hip.R"]["rx"]
        if min(abs(hl), abs(hr)) > 1e-3:
            assert hl * hr < 0.0, f"frame {rec['frame']}: both legs on the same side"
        for side in ("L", "R"):
            leg = pose[f"hip.{side}"]["rx"]
            arm = pose[f"shoulder.{side}"]["rx"]
            if abs(leg) > 1e-3:
                assert leg * arm < 0.0, (
                    f"frame {rec['frame']}: {side} arm and leg swing together"
                )


def test_knee_never_bends_forward(gait):
    """A knee is a hinge. The contrastive question: a sign error here produces a figure
    whose shins fold FORWARD, which reads as a broken leg in every frame — so the check
    is on the sign of every sample, not on a mean."""
    # backward, for a character facing -Y, is +X-rotation; the gait multiplies by -fy.
    expected_sign = -FACING_Y_SIGN
    for rec in gait["frames"]:
        for side in ("L", "R"):
            v = rec["pose"][f"knee.{side}"]["rx"]
            assert v * expected_sign >= -1e-9, (
                f"frame {rec['frame']} knee.{side} bends the wrong way: {v}"
            )


def test_he_walks_forwards_and_stops(gait):
    ys = [f["pose"]["hips"]["translation"][1] for f in gait["frames"]]
    # forward is -Y for this character; travel must be monotone in that direction
    for i in range(1, 48):
        assert ys[i] <= ys[i - 1] + 1e-12, f"frame {i} moved backwards"
    assert ys[47] < -0.5 * gait["derived"]["step_distance_derived"]
    # and the hips must be still once he has stopped, or he keeps gliding at the bar
    for i in range(49, len(ys)):
        assert ys[i] == pytest.approx(ys[48], abs=1e-12)


def test_total_travel_matches_the_derived_stride(gait):
    """The phase target is (steps + 0.5) half-cycles, and one half-cycle is one stance,
    so the travel must be that many stride lengths. A disagreement here means the
    integration and the leg geometry are describing different legs — which is exactly
    the defect the first version of this module had, and it read 24% short."""
    d = gait["derived"]
    expected = (walk.GaitParams().steps + 0.5) * d["step_distance_derived"]
    assert d["total_forward_travel"] == pytest.approx(expected, rel=0.02)


def test_the_hips_advance_at_a_steady_rate_through_the_walk(gait):
    """A sinusoidal leg angle stalls the body at both ends of every stride, and the
    planted foot skates to make up the difference. Constant-rate stance is what fixes it,
    so this is the check that the fix is still in place: the per-frame advance must not
    vary by more than a few percent while he is at full gait."""
    ys = [f["pose"]["hips"]["translation"][1] for f in gait["frames"]]
    steps = [abs(ys[i] - ys[i - 1]) for i in range(1, 40)]
    assert min(steps) > 0.0
    assert max(steps) / min(steps) < 1.05, (
        f"the hips advance between {min(steps):.5f} and {max(steps):.5f} per frame; the "
        f"body is stalling inside the stride"
    )


# ------------------------------------------------------------------------- the FK


def test_fk_on_a_null_pose_returns_the_rest_landmarks(performer):
    """The identity case. An FK that rotates or translates when nothing was authored
    would put a constant offset into every ground-truth number downstream — and it
    would be invisible, because every frame would carry the same wrong answer."""
    p = walk.GaitParams(hip_swing_deg=0.0, knee_flex_deg=0.0, arm_swing_deg=0.0,
                        elbow_base_deg=0.0, elbow_swing_deg=0.0, ankle_level_frac=0.0,
                        sway_frac=0.0, chest_twist_deg=0.0, nod_peak_deg=0.0,
                        nod_settle_deg=0.0, gesture_lift_deg=0.0, gesture_abduct_deg=0.0,
                        gesture_elbow_deg=0.0, gesture_wrist_deg=0.0)
    g = walk.build_gait(performer, p)
    fk = walk.forward_kinematics(performer, g)
    for name in ("ankle_L", "ankle_R", "toe_L", "toe_R", "wrist_L", "wrist_R",
                 "hand_end_L", "hand_end_R", "head_top"):
        for k in range(3):
            assert fk[0][name][k] == pytest.approx(LANDMARKS[name][k], abs=1e-12)
            assert fk[-1][name][k] == pytest.approx(LANDMARKS[name][k], abs=1e-12)


def test_forward_travel_is_not_a_dialled_in_constant(performer, gait):
    """THE anti-moonwalk fixture, and it is contrastive rather than thresholded.

    A threshold picked by the session that wrote the code is a preference. So the gait is
    graded against two deliberately wrong implementations built right here — hips advanced
    at a constant rate, with the SAME leg angles:

    * `scale=1.0` — the plausible one, a constant rate that covers the correct distance.
      It is what you get by dialling in a speed that "looks about right", and it slides
      because the true rate is only nearly constant.
    * `scale=0.6` — the real defect: a body speed that disagrees with the stride. This is
      moonwalking, and the statistic must separate it by a wide margin or it is not
      measuring what its name says.
    """
    fk = walk.forward_kinematics(performer, gait)
    good = walk.foot_slip(fk)["slide"]["slide_fraction_total"]

    def constant_rate(scale):
        total = gait["derived"]["total_forward_travel"] * scale
        broken = {**gait, "frames": []}
        for rec in gait["frames"]:
            r = {k: v for k, v in rec.items() if k != "pose"}
            pose = {b: dict(ch) for b, ch in rec["pose"].items()}
            t = pose["hips"]["translation"]
            pose["hips"]["translation"] = [t[0], -total * min(rec["frame"], 48) / 48.0, t[2]]
            r["pose"] = pose
            broken["frames"].append(r)
        return walk.foot_slip(walk.forward_kinematics(performer, broken))["slide"][
            "slide_fraction_total"]

    plausible = constant_rate(1.0)
    moonwalk = constant_rate(0.6)
    assert good < plausible, (
        f"the derived travel ({good:.3f}) does no better than a constant rate tuned to "
        f"the same distance ({plausible:.3f}); the derivation is buying nothing"
    )
    assert good < moonwalk / 3.0, (
        f"the derived travel slides {good:.3f} of the hips' path against a moonwalk's "
        f"{moonwalk:.3f}; the statistic cannot separate a planted foot from a sliding one"
    )
    # and a loose absolute bound: for most of the shot, a foot is on the floor
    assert good < 0.30, good


def test_foot_slip_finds_the_contacts(performer, gait):
    fk = walk.forward_kinematics(performer, gait)
    slip = walk.foot_slip(fk)
    # 5.5 stances over the shot, shared between two feet
    for side in ("L", "R"):
        assert 2 <= slip[side]["n_contacts"] <= 4, slip[side]["n_contacts"]
    assert slip["slide"]["hips_path"] > 0.0
    assert slip["slide"]["worst_frame_hips_speed"] is not None


# ---------------------------------------------------------------------- the emote


def test_the_gesture_raises_the_right_hand_and_not_the_left(performer, gait):
    fk = walk.forward_kinematics(performer, gait)
    before, after = fk[47], fk[-1]
    rise_r = after["hand_end_R"][2] - before["hand_end_R"][2]
    rise_l = after["hand_end_L"][2] - before["hand_end_L"][2]
    assert rise_r > 0.25 * performer.height, f"the hail barely lifts the hand: {rise_r}"
    assert abs(rise_l) < 0.02 * performer.height, f"the other hand moved too: {rise_l}"
    # it must go out on the character's RIGHT, which is -left_x_sign
    out = (after["hand_end_R"][0] - before["hand_end_R"][0]) * -LEFT_X_SIGN
    assert out > 0.0, "the raised arm crossed to the wrong side of the body"
    # and forward, toward the bar he is facing
    fwd = (after["hand_end_R"][1] - before["hand_end_R"][1]) * FACING_Y_SIGN
    assert fwd > 0.0, "the raised arm went backwards"


def test_the_nod_goes_down_and_settles(performer, gait):
    fk = walk.forward_kinematics(performer, gait)
    facing = [f["head_top"][1] * FACING_Y_SIGN for f in fk]
    stand = facing[47]
    peak = max(facing[48:60])
    assert peak > stand + 0.01, "the head never tipped toward the direction he faces"
    assert facing[-1] > stand, "the head did not settle looking slightly down"
    assert facing[-1] < peak, "the head never came back up out of the nod"


# ------------------------------------------------------------------- the numerics


def test_rotation_order_is_x_then_y_then_z():
    """Rz first, then Ry, then Rx. The gesture is the only place it matters, and it
    matters completely: lift-then-abduct rolls the arm about its own length."""
    got = walk.rotation_matrix(90.0, 90.0, 0.0)
    want = walk._mat_mul(walk._rot("X", 90.0), walk._rot("Y", 90.0))
    for i in range(3):
        for j in range(3):
            assert got[i][j] == pytest.approx(want[i][j], abs=1e-12)
    other = walk._mat_mul(walk._rot("Y", 90.0), walk._rot("X", 90.0))
    assert any(abs(got[i][j] - other[i][j]) > 1e-6 for i in range(3) for j in range(3))


def test_positive_x_rotation_carries_a_hanging_limb_toward_plus_y():
    """The sentence every sign in the gait is derived from. If this is ever false, the
    walk swings backwards and the nod looks up."""
    down = [0.0, 0.0, -1.0]
    out = walk._mat_vec(walk._rot("X", 20.0), down)
    assert out[1] > 0.0


def test_smootherstep_clamps_and_is_symmetric():
    assert walk.smootherstep(-3.0) == 0.0
    assert walk.smootherstep(0.0) == 0.0
    assert walk.smootherstep(0.5) == pytest.approx(0.5)
    assert walk.smootherstep(1.0) == 1.0
    assert walk.smootherstep(4.0) == 1.0
    for x in (0.1, 0.25, 0.4):
        assert walk.smootherstep(x) + walk.smootherstep(1.0 - x) == pytest.approx(1.0)


# --------------------------------------------------------------------- the refusals


def test_unknown_axis_raises():
    with pytest.raises(walk.WalkError):
        walk._rot("W", 10.0)


def test_a_performer_without_the_measurements_raises():
    thin = {k: v for k, v in LANDMARKS.items() if k != "ankle_L"}
    with pytest.raises(walk.WalkError):
        walk.Performer(thin, FACING_Y_SIGN, LEFT_X_SIGN)


def test_an_unmeasured_facing_sign_raises():
    """`facing_y_sign` is a MEASURED +/-1 out of the rig manifest. A 0.0 or a 0.98 means
    somebody passed a raw dot product, and the whole gait's handedness would be a guess."""
    with pytest.raises(walk.WalkError):
        walk.Performer(LANDMARKS, 0.0, LEFT_X_SIGN)
    with pytest.raises(walk.WalkError):
        walk.Performer(LANDMARKS, -1.0, 0.87)


def test_a_zero_length_phase_raises():
    with pytest.raises(walk.WalkError):
        walk.GaitParams(n_decel=0)
    with pytest.raises(walk.WalkError):
        walk.GaitParams(steps=0)
