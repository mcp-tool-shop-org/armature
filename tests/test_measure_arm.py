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
