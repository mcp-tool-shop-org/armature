"""The lift solver, against mathematics.

Every fixture here was written by asking the question CLAUDE.md asks of a fixture: *what
would this look like if the code were wrong in the specific way this check exists to
catch?* The two that matter most are the last kind — a gate that cannot fail is not a gate,
so `test_the_round_trip_gate_can_actually_fail` breaks a good solve on purpose, and
`test_the_gate_survives_optimization` runs the same break under `-O` and
`PYTHONOPTIMIZE=1`, because 87 of facet's andons turned out to be deletable by an
environment variable.

`test_fk_agrees_with_the_banked_walk_kinematics` is the one external check in the file: my
forward kinematics and E08's banked `walk.forward_kinematics` are two independent
implementations of the same composition, and a composition error that agreed with itself
would make every number in this experiment wrong in the same direction and perfectly
self-consistent.
"""

import math
import os
import subprocess
import sys
import textwrap

import pytest

from conftest import TOOLS  # noqa: F401  (puts tools/ on sys.path)
from armature_core import lift_solve as LS
from armature_core import sitelist, walk


# --------------------------------------------------------------------- the fixture

def synthetic_rest():
    """A humanoid rest table in the rig's own conventions: Z up, faces -Y, left on +X.

    Synthetic on purpose. The real performer's landmarks live in E07's manifest, which is
    a generated artifact outside git; a unit test that needs it could not run on a clean
    clone, and the arithmetic under test does not care whose body it is.
    """
    m = {
        "crotch": (0.0, 0.010, 0.000),
        "spine_base": (0.0, 0.010, 0.090),
        "chest_base": (0.0, 0.010, 0.180),
        "neck_base": (0.0, 0.010, 0.270),
        "head_base": (0.0, 0.010, 0.330),
        "head_top": (0.0, 0.010, 0.500),
        "shoulder_line": (0.0, 0.010, 0.250),
        "nose": (0.0, -0.060, 0.410), "nose_tip": (0.0, -0.100, 0.410),
        "eye_L": (0.030, -0.050, 0.430), "eye_L_tip": (0.030, -0.090, 0.430),
        "eye_R": (-0.030, -0.050, 0.430), "eye_R_tip": (-0.030, -0.090, 0.430),
        "ear_L": (0.070, 0.010, 0.410), "ear_L_tip": (0.100, 0.010, 0.410),
        "ear_R": (-0.070, 0.010, 0.410), "ear_R_tip": (-0.100, 0.010, 0.410),
    }
    # The arms and legs are COLLINEAR in the rest pose, which is what a mannequin standing
    # with straight limbs actually is — and it is the condition under which the lateral
    # hinge datum is exactly perpendicular to each limb bone. A rest limb with a slight
    # kink makes the hinge assumption an approximation, and the first version of this
    # fixture had one: it put a few degrees of unexplained error on every limb and read
    # like a solver defect.
    for side, sx in (("L", 1.0), ("R", -1.0)):
        m[f"shoulder_{side}"] = (sx * 0.150, 0.010, 0.250)
        m[f"elbow_{side}"] = (sx * 0.150, 0.010, 0.060)
        m[f"wrist_{side}"] = (sx * 0.150, 0.010, -0.100)
        m[f"hand_end_{side}"] = (sx * 0.150, 0.010, -0.180)
        m[f"hip_{side}"] = (sx * 0.050, 0.010, 0.000)
        m[f"knee_{side}"] = (sx * 0.050, 0.010, -0.250)
        m[f"ankle_{side}"] = (sx * 0.050, 0.010, -0.480)
        m[f"toe_{side}"] = (sx * 0.050, -0.080, -0.500)
    return m


DIAGONAL = 1.0  # the synthetic figure spans 1.0 in Z; the unit only has to be its own


def euler(rx, ry, rz):
    """The rig's own rotation convention — Rx @ Ry @ Rz, degrees — via the banked gait
    module, so the tests cannot drift from what the applier will key."""
    m = walk.rotation_matrix(rx, ry, rz)
    return tuple(tuple(float(v) for v in row) for row in m)


def motion(local_overrides, root=(0.0, 0.0, 0.0)):
    """A solved-shaped dict: every bone identity except the ones named."""
    local = {b.name: LS.IDENTITY for b in sitelist.BONES}
    local.update(local_overrides)
    return {"local": local, "root": {"hips_delta_translation": tuple(root)}}


def observed_from(rest, authored):
    """Forward-kinematic the authored motion, then keep only what a detector would see."""
    placed = LS.fk_sites(rest, authored)
    return {s: placed[s] for s in LS.SITE_FROM_LANDMARK}


#: A limb-only performance: the torso stays rigid and every limb bends. Bends are large
#: enough that no twist is underdetermined by collinearity.
LIMB_MOTION = {
    "shoulder.L": euler(-38.0, 0.0, 0.0), "elbow.L": euler(31.0, 0.0, 0.0),
    "wrist.L": euler(-12.0, 0.0, 0.0),
    "shoulder.R": euler(25.0, 0.0, 0.0), "elbow.R": euler(-44.0, 0.0, 0.0),
    "wrist.R": euler(9.0, 0.0, 0.0),
    "hip.L": euler(22.0, 0.0, 0.0), "knee.L": euler(-35.0, 0.0, 0.0),
    "ankle.L": euler(14.0, 0.0, 0.0),
    "hip.R": euler(-18.0, 0.0, 0.0), "knee.R": euler(40.0, 0.0, 0.0),
    "ankle.R": euler(-11.0, 0.0, 0.0),
}


# ------------------------------------------------------- the registration cannot drift

def test_model_covers_every_registered_bone():
    """A bone added to the site list and forgotten here would be silently held at
    identity — the rig would gain a joint the lift could never move, and nothing else in
    the pipeline would notice."""
    assert set(LS.MODEL) == set(sitelist.ALL_NAMES)


def test_every_landmark_index_is_accounted_for():
    """Used and unused must partition the 33. An index that is in neither is an omission
    nobody wrote down."""
    used = set(LS.SITE_FROM_LANDMARK.values())
    unused = set(LS.UNUSED_LANDMARKS)
    assert used & unused == set(), sorted(used & unused)
    assert used | unused == set(range(33))
    assert len(LS.POSE_LANDMARKS) == 33


def test_indices_agree_with_the_named_topology():
    """Every site must point at the landmark whose NAME says so, and the character's own
    left must read MediaPipe's left. A transposed pair here produces a solve that
    round-trips perfectly and puts the performance on the wrong side of his body."""
    want = {
        "nose": "nose", "ear_L": "left_ear", "ear_R": "right_ear",
        "shoulder_L": "left_shoulder", "shoulder_R": "right_shoulder",
        "elbow_L": "left_elbow", "elbow_R": "right_elbow",
        "wrist_L": "left_wrist", "wrist_R": "right_wrist",
        "hand_end_L": "left_index", "hand_end_R": "right_index",
        "hip_L": "left_hip", "hip_R": "right_hip",
        "knee_L": "left_knee", "knee_R": "right_knee",
        "ankle_L": "left_ankle", "ankle_R": "right_ankle",
        "toe_L": "left_foot_index", "toe_R": "right_foot_index",
    }
    assert set(want) == set(LS.SITE_FROM_LANDMARK)
    for site, landmark_name in want.items():
        assert LS.POSE_LANDMARKS[LS.SITE_FROM_LANDMARK[site]] == landmark_name


# ------------------------------------------------------------------ the round trip

def test_position_round_trip_is_exact_for_limb_motion():
    """H1a. Every pivot on a limb chain is itself an observed landmark, so the inversion
    is algebra rather than a fit and the gate is armed at 1e-9 of the figure's own size."""
    rest = synthetic_rest()
    authored = motion(LIMB_MOTION, root=(0.02, -0.03, 0.01))
    obs = observed_from(rest, authored)
    solved = LS.solve_frame(rest, obs)
    ev = LS.round_trip_report(rest, obs, solved, DIAGONAL)   # raises on failure
    assert ev["worst"]["d"] < LS.ROUND_TRIP_TOL_FRAC * DIAGONAL


def test_position_round_trip_is_exact_under_a_whole_body_rotation():
    """The same claim with the torso carried somewhere else: a rigid body rotation on
    `hips` must be recovered exactly, or every later frame of a moving shot is wrong."""
    rest = synthetic_rest()
    authored = motion(dict(LIMB_MOTION, **{"hips": euler(7.0, -13.0, 21.0)}),
                      root=(-0.04, 0.06, 0.02))
    obs = observed_from(rest, authored)
    solved = LS.solve_frame(rest, obs)
    LS.round_trip_report(rest, obs, solved, DIAGONAL)


def test_rotations_are_recovered_exactly_for_limb_motion():
    """H1b. Not just the positions — the authored rotations themselves come back.

    The authored motion here is a set of rotations about world X, which is the character's
    own lateral axis and therefore exactly the hinge every limb bone declares. With
    collinear rest limbs that motion lies inside the solver's parameterisation, so exact
    recovery is the claim and anything else is a defect.

    The wrists and ankles are excluded **by name**, not by a filter that could quietly
    grow: nothing is observed past their tails, so their twist is not recoverable and the
    solver is required to say so.
    """
    rest = synthetic_rest()
    authored = motion(LIMB_MOTION, root=(0.02, -0.03, 0.01))
    obs = observed_from(rest, authored)
    solved = LS.solve_frame(rest, obs)
    errs = LS.compare_rotations(solved["local"], authored["local"])
    tol_deg = math.degrees(LS.ROTATION_TOL_RAD)
    unrecoverable = {"wrist.L", "wrist.R", "ankle.L", "ankle.R"}
    for bone, err in errs.items():
        if bone in unrecoverable:
            continue
        assert err < tol_deg, f"{bone}: {err} deg"
    for bone in unrecoverable:
        assert bone in solved["underdetermined"]


def test_the_solve_is_idempotent():
    """The claim that needs no authored motion at all, and so cannot be circular.

    Whatever `solve_frame` returns is by definition inside its own parameterisation. Push
    it back through forward kinematics and solve those positions again: the second answer
    must be the first, exactly. Any disagreement between how the solve composes rotations
    and how the kinematics does would show up here even when every authored-motion test
    was written to suit the model.
    """
    rest = synthetic_rest()
    obs = observed_from(rest, motion(dict(LIMB_MOTION,
                                          **{"hips": euler(7.0, -13.0, 21.0)}),
                                     root=(-0.04, 0.06, 0.02)))
    first = LS.solve_frame(rest, obs)
    again = {s: LS.fk_sites(rest, first)[s] for s in LS.SITE_FROM_LANDMARK}
    second = LS.solve_frame(rest, again)

    tol_deg = math.degrees(LS.ROTATION_TOL_RAD)
    for bone, err in LS.compare_rotations(second["local"], first["local"]).items():
        assert err < tol_deg, f"{bone}: {err} deg between the first solve and the second"
    drift = LS._norm(LS._sub(second["root"]["hips_delta_translation"],
                             first["root"]["hips_delta_translation"]))
    assert drift < LS.ROUND_TRIP_TOL_FRAC * DIAGONAL, drift


def test_the_torso_solve_is_a_projection_and_the_pelvis_is_still_exact():
    """The model's one honest gap, pinned so it cannot widen unnoticed.

    `chest_base` is not an observed landmark — the 33 carry no mid-torso point — so a
    torso twist cannot be inverted exactly the way a limb can. What MUST still hold is
    that the contamination does not reach the pelvis's own landmarks: `hip_L` and `hip_R`
    are placed by `hips` alone, whose rotation is fixed by the hip axis, and they stay
    exact. The residual on the shoulders is measured here and reported, never asserted
    to be zero and never tuned toward one.
    """
    rest = synthetic_rest()
    authored = motion(dict(LIMB_MOTION, **{"chest": euler(0.0, 0.0, 9.0)}))
    obs = observed_from(rest, authored)
    solved = LS.solve_frame(rest, obs)
    ev = LS.round_trip_report(rest, obs, solved, DIAGONAL, raise_on_fail=False)

    for site in ("hip_L", "hip_R"):
        assert ev["per_site"][site] < LS.ROUND_TRIP_TOL_FRAC * DIAGONAL, (
            f"{site} is placed by `hips` alone and must survive a torso twist exactly; "
            f"got {ev['per_site'][site]}")
    # The gap exists and is bounded by the torso segment it comes from — not by a number
    # typed in here. Above the chest's own rest length would mean the solve is not
    # projecting the torso but scrambling it.
    chest_len = LS._norm(LS._sub(rest["neck_base"], rest["chest_base"]))
    assert ev["worst"]["d"] < chest_len, ev["worst"]


def test_a_mirrored_reading_is_visible_in_the_round_trip_but_only_partly():
    """What a transposed left/right actually does — measured, not assumed.

    **This test was written the other way round and the measurement corrected it.** The
    expectation was that a mirrored reading would round-trip perfectly, since a mirrored
    body is still a body; the residual came back at 0.16 of the figure's height. The
    reason is that the character is not mirror-symmetric where it counts: both feet point
    the same way in Y, so swapping the legs asks the solve to put a left foot where a
    right foot's toe was, and the torso frames' handedness inverts.

    So the round trip is **partly** sensitive to a transposed reading, which makes it a
    poor instrument for one — it would fire without saying why, and a near-symmetric pose
    would slip through. The handedness stays measured against known ground truth in the
    measuring tool. What is pinned here is only that the swap is not free.
    """
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    swapped = dict(obs)
    for a, b in (("shoulder_L", "shoulder_R"), ("elbow_L", "elbow_R"),
                 ("wrist_L", "wrist_R"), ("hand_end_L", "hand_end_R"),
                 ("hip_L", "hip_R"), ("knee_L", "knee_R"),
                 ("ankle_L", "ankle_R"), ("toe_L", "toe_R"), ("ear_L", "ear_R")):
        swapped[a], swapped[b] = obs[b], obs[a]
    solved = LS.solve_frame(rest, swapped)
    ev = LS.round_trip_report(rest, swapped, solved, DIAGONAL, raise_on_fail=False)
    assert ev["worst"]["d"] > 100.0 * LS.ROUND_TRIP_TOL_FRAC * DIAGONAL, ev["worst"]


# ---------------------------------------------------------------- the underdetermined

def test_twist_is_reported_underdetermined_when_the_limb_is_straight():
    """G16 made mechanical: no bend, no bend plane, no twist. The solver must say so
    rather than return a confident zero that reads like a measurement."""
    rest = synthetic_rest()
    obs = observed_from(rest, motion({}))     # the bind pose: every limb straight
    solved = LS.solve_frame(rest, obs)
    for bone in ("shoulder.L", "elbow.L", "hip.R"):
        assert bone in solved["underdetermined"], solved["underdetermined"]
        assert "bend plane" in solved["underdetermined"][bone]
        assert solved["twist_conditioning"][bone] < LS.COLLINEAR_SIN_EPS


def test_the_conditioning_number_is_a_sine_and_stays_in_range():
    """It is reported as the sine of the observed bend angle, so it must live in [0, 1].

    The first version divided by the bone's own length as well and returned 4.3 — a
    conditioning number outside its own range, which would have been read as a strong
    bend on a joint that barely moved.
    """
    rest = synthetic_rest()
    for authored in (motion({}), motion(LIMB_MOTION)):
        solved = LS.solve_frame(rest, observed_from(rest, authored))
        for bone, sine in solved["twist_conditioning"].items():
            assert 0.0 <= sine <= 1.0 + 1e-12, (bone, sine)


def test_a_backward_bend_does_not_flip_the_parents_twist():
    """A hinge is a line, not a ray — and this is the fixture for the defect that proved
    it. The two elbows here bend in OPPOSITE directions about the same lateral hinge; if
    the datum were matched as a ray, one of the two shoulders would come back with a
    180-degree twist error while its positions round-tripped perfectly.
    """
    rest = synthetic_rest()
    authored = motion({"elbow.L": euler(31.0, 0.0, 0.0),
                       "elbow.R": euler(-44.0, 0.0, 0.0)})
    solved = LS.solve_frame(rest, observed_from(rest, authored))
    for bone in ("shoulder.L", "shoulder.R"):
        err = LS.geodesic_deg(LS.IDENTITY, solved["local"][bone])
        assert err < 1e-9, f"{bone} picked up {err} deg of twist from its child's bend"


def test_a_bent_limb_reports_its_twist_as_determined():
    """The other direction, because a flag that is always on measures nothing."""
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    solved = LS.solve_frame(rest, obs)
    for bone in ("shoulder.L", "elbow.L", "hip.R", "knee.R"):
        assert bone not in solved["underdetermined"]


def test_held_bones_are_named_with_a_reason():
    """A bone held at identity must carry why. The three that are held are held because
    the 33 landmarks cannot determine them, and that reason belongs in the output the
    report is written from, not only in a docstring."""
    rest = synthetic_rest()
    solved = LS.solve_frame(rest, observed_from(rest, motion(LIMB_MOTION)))
    assert set(solved["held"]) == {"spine", "neck", "nose", "eye.L", "eye.R",
                                   "ear.L", "ear.R"}
    for bone, reason in solved["held"].items():
        assert reason and len(reason) > 20, (bone, reason)


# ------------------------------------------------------------- the gate can fail

def test_the_round_trip_gate_can_actually_fail():
    """A check that cannot fail is not a check. Break a good solve by a thousandth of a
    radian on one bone and the andon must pull."""
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    solved = LS.solve_frame(rest, obs)
    LS.round_trip_report(rest, obs, solved, DIAGONAL)          # clean first

    solved["local"]["elbow.L"] = LS.mat_mul(
        LS.axis_angle((0.0, 1.0, 0.0), 1e-3), solved["local"]["elbow.L"])
    with pytest.raises(LS.SolveGate) as exc:
        LS.round_trip_report(rest, obs, solved, DIAGONAL)
    assert exc.value.gate == "SOLVE"
    assert exc.value.evidence["worst"]["site"] in ("wrist_L", "hand_end_L")


def test_the_gate_is_not_an_assert():
    """Source-level, because `-O` deletes asserts and this repo has been bitten."""
    src = open(os.path.join(TOOLS, "armature_core", "lift_solve.py"),
               encoding="utf-8").read()
    for line in src.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("assert "), line


PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    sys.path.insert(0, sys.argv[2])
    from armature_core import lift_solve as LS
    from test_lift_solve import synthetic_rest, observed_from, motion, LIMB_MOTION, DIAGONAL

    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    solved = LS.solve_frame(rest, obs)
    solved["local"]["elbow.L"] = LS.mat_mul(
        LS.axis_angle((0.0, 1.0, 0.0), 1e-3), solved["local"]["elbow.L"])
    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__}
    try:
        LS.round_trip_report(rest, obs, solved, DIAGONAL)
        out["outcome"] = "NO_RAISE"
    except LS.SolveGate:
        out["outcome"] = "GATE_RAISED"
    except BaseException as exc:
        out["outcome"] = "WRONG_ERROR: %s" % type(exc).__name__
    print("RESULT " + json.dumps(out))
    """
)


def _probe(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / "probe.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else [])
    cmd += [str(script), TOOLS, os.path.dirname(os.path.abspath(__file__))]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert line, proc.stdout + proc.stderr
    import json
    return json.loads(line[-1][len("RESULT "):])


@pytest.mark.parametrize("flag,env_var,label",
                         [(False, False, "plain"), (True, False, "-O"),
                          (False, True, "PYTHONOPTIMIZE=1")])
def test_the_gate_survives_optimization(tmp_path, flag, env_var, label):
    res = _probe(tmp_path, flag=flag, env_var=env_var)
    assert res["outcome"] == "GATE_RAISED", f"{label}: {res}"


def test_the_optimization_actually_took_effect(tmp_path):
    """Otherwise the three green results above prove nothing."""
    assert _probe(tmp_path)["asserts_active"] is True
    assert _probe(tmp_path, flag=True)["asserts_active"] is False
    assert _probe(tmp_path, env_var=True)["asserts_active"] is False


# ------------------------------------------------------------------ the diagnostics

def test_bone_length_residual_reads_zero_on_the_rig_and_moves_on_another_body():
    """Grade an arm only on what it can move. A residual that reads the same whether the
    observed body matches the rig or not would not be measuring the body."""
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    same = LS.bone_length_residuals(rest, obs)
    assert max(abs(v["residual_fraction"]) for v in same.values()) < 1e-12

    bigger = {k: LS._scale(v, 1.20) for k, v in obs.items()}
    scaled = LS.bone_length_residuals(rest, bigger)
    for bone, rec in scaled.items():
        assert abs(rec["residual_fraction"] - 0.20) < 1e-9, (bone, rec)


def test_hip_centering_puts_the_hip_midpoint_on_the_origin():
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION, root=(0.3, -0.2, 0.1)))
    centred = LS.hip_center(obs)
    mid = LS._mid(centred["hip_L"], centred["hip_R"])
    assert max(abs(v) for v in mid) < 1e-12


def test_convert_axes_is_a_rotation_and_preserves_shape():
    rest = synthetic_rest()
    obs = observed_from(rest, motion(LIMB_MOTION))
    basis = LS.axis_angle(LS._unit((1.0, 2.0, -0.5)), 0.9)
    turned = LS.convert_axes(obs, basis)
    a = LS._norm(LS._sub(obs["shoulder_L"], obs["wrist_L"]))
    b = LS._norm(LS._sub(turned["shoulder_L"], turned["wrist_L"]))
    assert abs(a - b) < 1e-12


def test_a_hinge_hint_parallel_to_its_bone_raises_rather_than_guessing():
    """The datum the twist is measured against must exist. A rig whose arms lie along the
    lateral axis would have none, and a silently-chosen substitute would put a confident
    number on noise."""
    with pytest.raises(LS.SolveError) as exc:
        LS._bind_reference((1.0, 0.0, 0.0), LS.LATERAL_AXIS, "probe")
    assert "hinge" in str(exc.value)


def test_a_short_landmark_list_raises():
    with pytest.raises(LS.SolveError):
        LS.sites_from_landmarks([(0.0, 0.0, 0.0)] * 30)


# ------------------------------------------------- the record the applier will consume

def _record(n=4):
    return [{"frame": i, "local": {b.name: LS.IDENTITY for b in sitelist.BONES},
             "root": (0.0, 0.0, 0.0)} for i in range(n)]


def test_a_valid_motion_record_passes():
    ev = LS.validate_motion_record(_record())
    assert ev["n_frames"] == 4


def test_a_gap_in_the_frame_numbering_raises():
    """The failure this exists for is silent: Blender holds the previous keyframe, so a
    dropped frame plays as a stutter and reads as detector noise rather than as a frame
    that never arrived."""
    frames = _record()
    frames[2]["frame"] = 3
    with pytest.raises(LS.SolveGate) as exc:
        LS.validate_motion_record(frames)
    assert exc.value.evidence["index"] == 2


def test_a_missing_bone_on_one_frame_raises():
    """Equally silent: the bone simply keeps its last rotation, and every count-based
    check still passes."""
    frames = _record()
    del frames[1]["local"]["elbow.R"]
    with pytest.raises(LS.SolveGate) as exc:
        LS.validate_motion_record(frames)
    assert exc.value.evidence["missing"] == ["elbow.R"]


def test_an_empty_motion_record_raises():
    with pytest.raises(LS.SolveGate):
        LS.validate_motion_record([])


# --------------------------------------------------------- the independent cross-check

def test_fk_agrees_with_the_banked_walk_kinematics():
    """Two independent implementations of the same composition must agree.

    `walk.forward_kinematics` was written for E08 and is the ground truth `author_walk`'s
    Gate F holds Blender to. If my composition here differed from it, every solved pose
    would be measured against a ground truth built a different way, and the disagreement
    would look like solver error rather than like the bug it is.
    """
    rest = synthetic_rest()
    performer = walk.Performer(rest, facing_y_sign=-1.0, left_x_sign=1.0)
    pose = {b: {"rx": 0.0, "ry": 0.0, "rz": 0.0} for b in walk.GAIT_BONES}
    angles = {"hips": (5.0, 0.0, 3.0), "chest": (0.0, 0.0, 7.0),
              "shoulder.L": (-38.0, 0.0, 0.0), "elbow.L": (31.0, 0.0, 0.0),
              "wrist.L": (-12.0, 0.0, 0.0), "hip.R": (-18.0, 0.0, 0.0),
              "knee.R": (40.0, 0.0, 0.0), "ankle.R": (-11.0, 0.0, 0.0)}
    for bone, (rx, ry, rz) in angles.items():
        pose[bone].update(rx=rx, ry=ry, rz=rz)
    pose["hips"]["translation"] = [0.02, -0.03, 0.01]

    gait = {"frames": [{"frame": 0, "scene_frame": 1, "pose": pose}]}
    theirs = walk.forward_kinematics(performer, gait)[0]

    mine = LS.fk_sites(rest, motion(
        {b: euler(*angles[b]) for b in angles}, root=(0.02, -0.03, 0.01)))

    for their_key, my_key in (("hips", "crotch"), ("head_top", "head_top"),
                              ("ankle_R", "ankle_R"), ("toe_R", "toe_R"),
                              ("wrist_L", "wrist_L"), ("hand_end_L", "hand_end_L")):
        d = LS._norm(LS._sub(tuple(theirs[their_key]), mine[my_key]))
        assert d < 1e-12, f"{their_key}: my FK and walk.forward_kinematics differ by {d}"
