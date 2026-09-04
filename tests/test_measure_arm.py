"""The projection maths under measure_arm's ground truth — one copy, not a third one.

`measure_arm.half_fovs` was a third implementation of Blender's AUTO sensor fit, beside
`armature_core.blender_scene.half_fovs` and `armature_core.framing.half_fovs`. Its docstring
justified the duplication by naming a test that pins the copies together — and there was no
`tests/test_measure_arm.py` in the tree; a repo-wide grep for `test_measure_arm` found only
that docstring. `tests/test_framing.py::test_half_fovs_matches_blenders` pins framing's copy
against blender_scene's, so two of the three were held and the third was held by nothing.

Measured on 2026-09-03, all three agreed at 832x480, 480x832, 1024x1024 and 1280x720 — so
what this file records is an absent guard, not a live divergence. The absent guard matters
because the direction it leaves open is silent: a change to Blender's AUTO convention lands
in the two pinned copies, misses this one, and `measure_arm`'s projected ground truth — what
the Gate 0 sheet marks up — is quietly off with every test green.

The identity assertion is the load-bearing one. Numerical agreement is what the old comment
claimed and would have been satisfied by a copy that had not drifted *yet*; there being one
function is what makes drift impossible.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_arm as MA  # noqa: E402
from armature_core import framing  # noqa: E402

LENS, SENSOR = 50.0, 36.0
CASES = ((832, 480), (480, 832), (1024, 1024), (1280, 720))


def test_measure_arm_uses_framings_pinned_copy_rather_than_its_own():
    """There is no third implementation to drift: it is the same function object."""
    assert MA.half_fovs is framing.half_fovs


def test_the_projection_still_agrees_with_blenders_auto_fit_on_every_case():
    """The numeric pin the old docstring claimed, over the same landscape / portrait /
    square cases test_framing.py uses — through whichever copy measure_arm now calls."""
    for w, h in CASES:
        assert MA.half_fovs(LENS, SENSOR, w, h) == framing.half_fovs(LENS, SENSOR, w, h)


def test_the_sensor_sits_on_the_longer_axis_which_is_the_whole_auto_convention():
    """What would this look like if the code were wrong in the way this catches? A copy
    that put the sensor on the WIDTH always would give the same answer on a square frame
    and the wrong one in portrait — so the two orientations are asserted apart."""
    land_x, land_y = MA.half_fovs(LENS, SENSOR, 832, 480)
    port_x, port_y = MA.half_fovs(LENS, SENSOR, 480, 832)
    assert land_x > land_y
    assert port_y > port_x
    assert land_x == pytest.approx(port_y)


def test_project_puts_the_camera_target_at_the_centre_of_frame():
    """The consumer, exercised once: a wrong half-FOV would move this off centre, and this
    is the ground truth the Gate 0 sheet marks up."""
    import numpy as np

    target = (0.0, 0.0, 0.0)
    M = np.array([[1.0, 0.0, 0.0, 0.0],
                  [0.0, 0.0, -1.0, -4.0],
                  [0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]])  # looks down -Z_local toward +Y_world
    px, depth = MA.project([target], M, LENS, SENSOR, 832, 480)
    assert depth[0] == pytest.approx(4.0)
    assert px[0][0] == pytest.approx(416.0)
    assert px[0][1] == pytest.approx(240.0)


# ------------------------------------- the measured population IS the authored population
#
# `run` built `truth` from the manifest and the joints sidecar — one entry per AUTHORED
# frame — and then, when `--frames` was given, built `out["measured"]` from a bare
# `os.listdir` with no numbered filter and nothing comparing the two populations: no length
# check, no name check, and rows carrying `"frame": i`, the enumeration index, which is
# precisely the number `measure_lift.gate_pairing`'s own docstring says does NOT carry the
# information. That gate is one import away in the same domain and was not called.
#
# Measured 2026-09-04 on this branch: a 5-frame authored arc against a frames directory of
# 10 numbered frames plus one `strip_every8.png` produced `len(out["truth"]) == 5` and
# `len(out["measured"]) == 11`, the last measured row naming `file: strip_every8.png` as
# `frame: 10`, with no refusal and nothing in the record saying the two populations differ.
# `out["measured_crossing_frame"]` — the number the arm is graded on — was then an index
# into a population nobody had described.

import json  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import measure_lift as _ML  # noqa: E402


def _joint_world(angle_deg):
    """shoulder / elbow / wrist in world Z-up, the wrist swung by `angle_deg`."""
    import math as _math

    sh = [0.0, 0.0, 1.4]
    r = 0.6
    a = _math.radians(angle_deg)
    return {
        "shoulder_r": sh,
        "elbow_r": [sh[0] + 0.5 * r * _math.cos(a), 0.0, sh[2] + 0.5 * r * _math.sin(a)],
        "wrist_r": [sh[0] + r * _math.cos(a), 0.0, sh[2] + r * _math.sin(a)],
    }


def _arm_run(tmp, n_authored=5, w=64, h=64):
    """A run directory + joints sidecar for an `n_authored`-frame arm arc."""
    run = tmp / "run"
    run.mkdir(parents=True, exist_ok=True)
    cam = np.eye(4)
    cam[:3, 3] = (0.0, -4.0, 1.4)
    # Blender cameras look down local -Z; this basis puts -Z along +Y (the subject).
    cam[:3, :3] = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    (run / "manifest.json").write_text(json.dumps({
        "resolution": [w, h],
        "spec": {"camera": {"lens_mm": 50.0, "sensor_mm": 36.0}},
        "frames": [{"camera_matrix": cam.tolist()} for _ in range(n_authored)],
    }), encoding="utf-8")

    angles = [i * (90.0 / max(1, n_authored - 1)) for i in range(n_authored)]
    joints = tmp / "subject.joints.json"
    joints.write_text(json.dumps({
        "pose_arc": {"name": "arm_raise", "start_deg": 0.0, "end_deg": 90.0,
                     "frames": n_authored,
                     "readout": {"readout_deg": 45.0,
                                 "crossing_frame_exact": (n_authored - 1) / 2.0,
                                 "crossing_frame_nearest": (n_authored - 1) // 2}},
        "frames": [{"angle_deg": a, "joints_world_zup": _joint_world(a)} for a in angles],
    }), encoding="utf-8")
    return str(run), str(joints)


def _frames_dir(tmp, numbers, name="frames", extra=None, w=64, h=64):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for k, n in enumerate(numbers):
        arr = np.full((h, w, 3), 30, dtype=np.uint8)
        arr[20:24, 32 + k: 40 + k] = 220              # a limb-ish blob on the arm's side
        Image.fromarray(arr).save(d / f"{n:05d}.png")
    if extra:
        Image.fromarray(np.full((h, w, 3), 90, dtype=np.uint8)).save(d / extra)
    return str(d)


def test_more_measured_frames_than_authored_is_refused_by_the_pairing_gate(tmp_path):
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(6)))
    with pytest.raises(_ML.PairingGate) as e:
        MA.run(run, joints, frames_dir=frames)
    ev = e.value.evidence
    assert ev["gate"] == "PAIRING"
    assert ev["n_rendered"] == 6 and ev["n_authored"] == 5


def test_a_contact_strip_in_the_frames_directory_is_refused_by_name(tmp_path):
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(5)), extra="strip_every8.png")
    with pytest.raises(MA.MeasureError) as e:
        MA.run(run, joints, frames_dir=frames)
    assert e.value.evidence["unexpected"] == ["strip_every8.png"], e.value.evidence


def test_a_renumbered_render_is_paired_by_number_not_by_position(tmp_path):
    """Same count, same everything — numbered from 1. `zip` paired each measured frame
    with its predecessor's authored pose all the way down."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(1, 6)))
    with pytest.raises(_ML.PairingGate) as e:
        MA.run(run, joints, frames_dir=frames)
    assert e.value.evidence["first_disagreement"] == 0


def test_a_matching_directory_still_measures_and_records_the_verdict(tmp_path):
    """The guard the other way: a refusal that fires on a good population is not a check,
    and the passing verdict must be written down."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(5)))
    res = MA.run(run, joints, frames_dir=frames)
    assert len(res["measured"]) == len(res["truth"]) == 5
    assert res["gate_PAIRING"]["gate"] == "PAIRING"
    assert "verdict" in res["gate_PAIRING"]


def test_every_measured_row_names_the_frame_number_from_its_own_filename(tmp_path):
    """`"frame": i` was the enumeration index; the number that carries the information is
    in the file NAME. With the gate armed the two agree — and the row says so."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(5)))
    res = MA.run(run, joints, frames_dir=frames)
    for row in res["measured"]:
        assert row["frame"] == int(os.path.splitext(row["file"])[0])


def test_the_arm_pairing_gate_survives_python_optimize(tmp_path):
    import subprocess

    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(6)))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import measure_arm as MA, measure_lift as ML\n"
        "try:\n"
        "    MA.run(r'%s', r'%s', frames_dir=r'%s')\n"
        "except ML.PairingGate:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(root, "tools"), run, joints, frames)
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in res.stdout, res.stderr


# ------------------- the promised failure path, and the side the measurement was taken on
#
# **The docstring asserted a safety property no code implemented.** Lines 22-29 record the
# E02 confound ("a lit studio gradient got counted as subject and returned 78-89% coverage")
# and then state: "an angle whose segmentation is implausible is reported as failed, not as
# a number." `subject_mask` returned the fraction and said "the caller is expected to refuse
# an implausible one"; the caller stored `segmentation` on each row, computed a
# `segmentation_summary`, and refused nothing — there was no threshold, no clause and no
# per-row failure marker anywhere in the file.
#
# Measured 2026-09-04 in this worktree on a 5-frame authored arc whose frames carry a
# left-to-right luminance ramp: every row returned `subject_fraction 0.875` (inside the
# 78-89% band the docstring names) with `angle_deg_measured 0.0` and `n_px 292`, exit 0, and
# the row keys were ['angle_deg_measured','angle_p25','angle_p75','file','frame','n_px',
# 'segmentation'] — no `failed`, no `implausible`.
#
# **And the hemisphere was a global constant.** `arm_angle` kept `(dx > 0)`, commented
# "right hemisphere: the arm's side", while `run` derives the annulus RADII from the
# subject's own projected geometry two lines earlier and already holds the evidence that
# would falsify it. Measured on a 5-frame arc authored on the -X side (`truth[0].wrist_px`
# 13.3 px LEFT of `truth[0].shoulder_px`, authored image angles 180 -> 90): `measured_angles`
# came back [69.108, 71.565, 74.023, 76.717, 79.193] with `frames_without_an_angle: 0`,
# computed from whatever pixels happened to fall on the +dx side, and no key in the record
# named a hemisphere. `rig_character.py` records `which_arm_is_on_plus_x` precisely because
# the side is a measured property of the mesh, not a constant.


def _joint_world_left(angle_deg):
    """The same arc, authored on the -X side of the body."""
    import math as _math

    sh = [0.0, 0.0, 1.4]
    r = 0.6
    a = _math.radians(angle_deg)
    return {
        "shoulder_r": sh,
        "elbow_r": [sh[0] - 0.5 * r * _math.cos(a), 0.0, sh[2] + 0.5 * r * _math.sin(a)],
        "wrist_r": [sh[0] - r * _math.cos(a), 0.0, sh[2] + r * _math.sin(a)],
    }


def _arm_run_left(tmp, n_authored=5, w=64, h=64):
    run, joints = _arm_run(tmp, n_authored=n_authored, w=w, h=h)
    angles = [i * (90.0 / max(1, n_authored - 1)) for i in range(n_authored)]
    with open(joints, encoding="utf-8") as fh:
        rec = json.load(fh)
    rec["frames"] = [{"angle_deg": a, "joints_world_zup": _joint_world_left(a)}
                     for a in angles]
    with open(joints, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    return run, joints


def _gradient_frames(tmp, numbers, name="ramp", w=64, h=64):
    """Frames carrying a left-to-right luminance ramp and no subject at all.

    This is the E02 confound the module docstring names: the modal colour is one column's
    worth of pixels, so almost the whole frame reads as "subject" and the annulus is full
    of background. What would this look like if the code were right? No number.
    """
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    ramp = np.tile(np.linspace(0, 255, w, dtype=np.uint8)[None, :, None], (h, 1, 3))
    for n in numbers:
        Image.fromarray(ramp).save(d / f"{n:05d}.png")
    return str(d)


def test_a_gradient_background_yields_no_number(tmp_path):
    """THE fixture. The docstring's clause, made mechanical: the corners of a frame are
    background by construction on a shot framed around a figure, so a mask that classifies
    them as subject has not found a subject."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _gradient_frames(tmp_path, list(range(5)))
    with pytest.raises(MA.MeasureError) as e:
        MA.run(run, joints, frames_dir=frames)
    ev = e.value.evidence
    # The run-level refusal is on the NUMBER that would be quoted; it names the row that
    # failed and why, so the halt is legible without opening the record.
    assert ev["gate"] == "CROSSING"
    assert ev["failed"] == [0, 1, 2, 3, 4]
    assert "segmentation refused" in ev["failed_reason"]
    assert "corner" in ev["failed_reason"]


def test_the_failed_rows_are_marked_before_the_crossing_is_refused(tmp_path):
    """`rows_for_frames` is the half that reports; the refusal is on the NUMBER."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _gradient_frames(tmp_path, list(range(5)))
    rows = MA.rows_for_frames(frames, (32.0, 32.0), 2.0, 20.0, hemisphere=1)
    assert all(r["angle_deg_measured"] is None for r in rows)
    assert all(r["failed"] and r["failed_reason"] for r in rows)


def test_a_real_subject_still_measures_and_records_the_clause(tmp_path):
    """The guard the other way: a clause that fires on correct work is not a check."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _frames_dir(tmp_path, list(range(5)))
    res = MA.run(run, joints, frames_dir=frames)
    assert all(r["failed"] is False for r in res["measured"])
    assert res["segmentation_summary"]["frames_failed"] == 0


def test_the_crossing_refuses_rather_than_interpolating_across_a_failed_row():
    """The number the arm is graded on may not be interpolated between a measurement and
    a row that has no measurement."""
    with pytest.raises(MA.MeasureError, match=r"failed row"):
        MA.crossing_frame([0.0, None, 80.0], 45.0, failed=[False, True, False])
    assert MA.crossing_frame([0.0, 40.0, 80.0], 45.0,
                             failed=[False, False, False]) == pytest.approx(1.125)


def test_the_hemisphere_is_derived_from_the_authored_truth(tmp_path):
    """An arc authored on the -X side must be measured on the -X side, and the record must
    say which side it looked at."""
    run, joints = _arm_run_left(tmp_path, n_authored=5)
    res = MA.run(run, joints)
    assert res["hemisphere"] == -1
    assert "truth" in res["hemisphere_source"]

    right = tmp_path / "r"
    right.mkdir()
    run_r, joints_r = _arm_run(right, n_authored=5)
    assert MA.run(run_r, joints_r)["hemisphere"] == 1


def test_an_arc_authored_on_image_left_is_not_measured_on_the_right(tmp_path):
    """THE measured case: 69.1 -> 79.2 degrees returned confidently off the opposite side
    of the body, from pixels that happened to fall there."""
    run, joints = _arm_run_left(tmp_path, n_authored=5)
    d = tmp_path / "leftframes"
    d.mkdir(parents=True, exist_ok=True)
    for k, n in enumerate(range(5)):
        arr = np.full((64, 64, 3), 30, dtype=np.uint8)
        arr[20:24, 24 - k: 32 - k] = 220     # a limb-ish blob on image-LEFT of the shoulder
        Image.fromarray(arr).save(d / f"{n:05d}.png")
    res = MA.run(run, joints, frames_dir=str(d))
    assert res["hemisphere"] == -1
    for row in res["measured"]:
        assert row["angle_deg_measured"] is None or row["angle_deg_measured"] > 90.0


def test_a_side_with_no_annulus_pixels_while_the_other_has_them_is_refused():
    """`arm_angle` returned `None` with `note: annulus empty on the arm's side` and the
    caller counted it in `frames_without_an_angle` — a silent zero on the side that was
    asked for while the evidence sat on the other."""
    mask = np.zeros((64, 64), dtype=bool)
    mask[30:34, 20:28] = True                       # entirely on image-LEFT of (32, 32)
    with pytest.raises(MA.MeasureError, match=r"hemisphere") as e:
        MA.arm_angle(mask, (32.0, 32.0), 2.0, 20.0, hemisphere=1)
    assert e.value.evidence["n_px_other_side"] > 0


def test_a_non_finite_span_is_refused_rather_than_emptying_the_annulus(tmp_path):
    """`nan >= nan` is False in both directions, so a NaN span makes the annulus silently
    empty and every frame reports "no angle" instead of "the projection failed"."""
    run, joints = _arm_run(tmp_path, n_authored=5)
    with open(joints, encoding="utf-8") as fh:
        rec = json.load(fh)
    for fr in rec["frames"]:
        fr["joints_world_zup"]["wrist_r"] = [float("nan"), 0.0, 1.4]
    with open(joints, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    frames = _frames_dir(tmp_path, list(range(5)))
    with pytest.raises(MA.MeasureError, match=r"span") as e:
        MA.run(run, joints, frames_dir=frames)
    assert e.value.evidence["gate"] == "SPAN"


def test_the_segmentation_and_hemisphere_clauses_survive_python_optimize(tmp_path):
    import subprocess

    run, joints = _arm_run(tmp_path, n_authored=5)
    frames = _gradient_frames(tmp_path, list(range(5)))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import numpy as np\n"
        "import measure_arm as MA\n"
        "try:\n"
        "    MA.run(r'%s', r'%s', frames_dir=r'%s')\n"
        "except MA.MeasureError:\n"
        "    print('SEG_RAISED')\n"
        "m = np.zeros((64, 64), dtype=bool)\n"
        "m[30:34, 20:28] = True\n"
        "try:\n"
        "    MA.arm_angle(m, (32.0, 32.0), 2.0, 20.0, hemisphere=1)\n"
        "except MA.MeasureError:\n"
        "    print('HEMI_RAISED')\n"
    ) % (os.path.join(root, "tools"), run, joints, frames)
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "SEG_RAISED" in res.stdout, res.stderr
    assert "HEMI_RAISED" in res.stdout, res.stderr
