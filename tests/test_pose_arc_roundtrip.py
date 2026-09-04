"""The wrapper for `tests/blender/check_pose_arc_roundtrip.py`.

WHY THIS FILE EXISTS. That 132-line check lived under `tests/` and **no `test_*.py`
invoked it**. A reference sweep over `*.py` / `*.md` / `*.ps1` / `*.yml` found it named
only by `docs/experiments/E03-report.md` and `tools/make_test_armature.py`. Every sibling
under `tests/blender/` — `check_visibility`, `check_ortho_convention`,
`check_plate_composite`, `check_floor_material`, `make_synthetic_run` — has a wrapper that
subprocesses it under a Blender-presence skipif. Its own docstring calls it "the check E03
cannot proceed without".

WHAT IT CATCHES THAT NOTHING ELSE DOES. Failure mode 2: glTF stores key times in
**seconds**, so an export at one fps read back at another lands the keys on different
frames and the arc arrives compressed or stretched. G6, the andon it defers to, cannot see
that: G6's quantity is `distinct_signatures` (`tools/stage_render.py:420`, asserted at
`tests/test_gate_g6.py:81`), and a time-warped arc still yields one distinct signature per
frame, so G6 reads PASS. That claim is pinned below in CPython, without Blender.

The consequence is an authored performance arriving time-warped in a paid generation with
every gate green, and the only instrument that could have said so being a file nothing
runs.

The check's contract is now the printed `POSE_ARC <json>` record rather than an exit code
— CLAUDE.md forbids a shell-chain gate by name, because a chain can walk past a failing
exit code. Every test here asserts on that record.
"""

import json
import os
import subprocess

import pytest

from armature_core import gates
from conftest import BLENDER, REPO

pytestmark = pytest.mark.skipif(
    not os.path.isfile(BLENDER), reason=f"Blender not found at {BLENDER}"
)

CHECK = os.path.join(REPO, "tests", "blender", "check_pose_arc_roundtrip.py")
MAKER = os.path.join(REPO, "tools", "make_test_armature.py")
MARKER = "POSE_ARC "

#: The one arc `armature_core.posearc` registers, and the shot it is authored over.
ARC, FRAMES, FPS = "arm_r_raise", 9, 16


def _blender(script, args, timeout=300):
    proc = subprocess.run(
        [BLENDER, "-b", "-P", script, "--", *args],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc


def _record(proc):
    """The one machine-readable line, or the whole transcript in the failure message."""
    lines = [l for l in proc.stdout.splitlines() if l.startswith(MARKER)]
    assert lines, (
        f"the check printed no {MARKER.strip()} record.\nrc={proc.returncode}\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return json.loads(lines[-1][len(MARKER):])


def _make_subject(directory, name, *, arc=ARC):
    """A wire armature with (or without) an authored performance, plus its sidecar."""
    glb = os.path.join(str(directory), name + ".glb")
    args = ["--frames", str(FRAMES), "--fps", str(FPS), "--out", glb]
    if arc:
        # `--pose-arc=<name>`: argparse eats leading minus signs, and the maker's own
        # help says to pass these as `--flag=value`.
        args = [f"--pose-arc={arc}"] + args
    proc = _blender(MAKER, args)
    assert proc.returncode == 0, f"the maker failed:\n{proc.stdout}\n{proc.stderr}"
    assert os.path.isfile(glb), proc.stdout
    assert os.path.isfile(os.path.splitext(glb)[0] + ".joints.json"), proc.stdout
    return glb


@pytest.fixture(scope="module")
def performer(tmp_path_factory):
    return _make_subject(tmp_path_factory.mktemp("posearc"), "subject")


@pytest.fixture(scope="module")
def bind_pose_only(tmp_path_factory):
    """The same subject built with no arc at all — its sidecar carries no `pose_arc`."""
    return _make_subject(tmp_path_factory.mktemp("posearc_static"), "static", arc=None)


@pytest.fixture(scope="module")
def at_authored_fps(performer):
    return _record(_blender(CHECK, [performer]))


@pytest.fixture(scope="module")
def at_half_the_authored_fps(performer):
    """Failure mode 2, driven on purpose. A check that cannot be made to fire is not a
    check, and this is the mode G6 is blind to."""
    return _record(_blender(CHECK, [performer, f"--fps={FPS // 2}"]))


# ------------------------------------------------------ the round trip, at the right rate

def test_the_arc_survives_the_round_trip_at_the_authored_frame_rate(at_authored_fps):
    rec = at_authored_fps
    assert rec["verdict"] == "OK", rec
    assert rec["fps_used"] == rec["fps_authored"] == FPS
    assert rec["frames"] == FRAMES


def test_failure_mode_1_an_action_survived_the_export_and_import(at_authored_fps):
    """The exporter may not write object-level TRS animation at all. It produces a
    well-formed GLB either way."""
    assert at_authored_fps["actions"] >= 1, at_authored_fps
    assert at_authored_fps["mesh_objects"] >= 1, at_authored_fps


def test_failure_mode_3_the_action_is_actually_driving_the_geometry(at_authored_fps):
    """The importer may create the action and leave it unassigned, in which case
    `frame_set` moves the timeline and the geometry does not follow. Measured on the
    evaluated vertices, which is what the renderer will read."""
    rec = at_authored_fps
    assert rec["displacement_m"] > rec["tol_m"], rec
    # The arm sweeps 0 -> 90 degrees, so the displacement is on the order of a limb.
    assert rec["displacement_m"] > 10 * rec["limb_radius_m"], rec


def test_the_evaluated_geometry_sits_on_the_authored_wrist_at_every_sampled_frame(
        at_authored_fps):
    """Against the ground truth in the sidecar, not against itself. The wrist is a bone
    END, so the comparison is to the nearest vertex — within one limb radius means the
    arm is where it was authored to be."""
    rec = at_authored_fps
    bound = rec["limb_radius_m"] + rec["tol_m"]
    assert len(rec["rows"]) == 3, rec["rows"]
    assert [r["angle_deg"] for r in rec["rows"]] == [0.0, 45.0, 90.0], rec["rows"]
    for row in rec["rows"]:
        assert row["nearest_vertex_m"] <= bound, (row, bound)


# ------------------------------- failure mode 2: the one G6 cannot see, driven on purpose

def test_failure_mode_2_an_arc_read_back_at_the_wrong_frame_rate_is_caught(
        at_half_the_authored_fps):
    """glTF stores key times in SECONDS. Read back at half the authored rate, the arc is
    stretched over twice the timeline and every sampled frame lands on the wrong angle —
    and nothing errors anywhere. Measured: at 8 fps against an arc authored at 16, the
    mid-frame wrist is 0.181 m from its authored position against a 0.030 m limb radius,
    six times the bound, while the arc still moves and still imports cleanly."""
    rec = at_half_the_authored_fps
    assert rec["fps_used"] == FPS // 2 and rec["fps_matches_authored"] is False
    assert rec["verdict"] == "OFF_TRUTH", rec
    assert rec["actions"] >= 1, "the action still imported; that is what makes this silent"
    assert rec["displacement_m"] > rec["tol_m"], "the arc still moves; G6 would read PASS"

    mid = rec["rows"][1]
    assert mid["nearest_vertex_m"] > 3 * rec["limb_radius_m"], (
        f"the time warp moved the mid-frame wrist only {mid['nearest_vertex_m']:.5f} m "
        f"against a {rec['limb_radius_m']} m limb radius; this fixture is not driving the "
        f"failure it exists to drive")
    assert "seconds" in rec["reason"], rec["reason"]


def test_G6_reads_PASS_on_the_shot_this_check_would_refuse():
    """Why mode 2 needs its own instrument, pinned without Blender.

    G6's quantity is `distinct_signatures` — whether the evaluated geometry CHANGED
    between frames, not whether it changed by the authored amount. A compressed or
    stretched arc still yields one distinct signature per frame, so G6 reports the
    subject moved and the run proceeds to a paid submission.
    """
    warped = [f"frame{i}" for i in range(FRAMES)]
    detail = gates.g6_subject_motion(warped, "per_frame")
    assert detail["distinct_signatures"] == FRAMES
    assert detail["verdict"] == "subject moved"


# ----------------------------------------- nothing-to-check and everything-checked-out

def test_an_asset_with_no_authored_arc_is_refused_rather_than_reported_clean(
        bind_pose_only):
    """"Nothing to check" and "everything checked out" are different verdicts. A subject
    built with no `--pose-arc` carries no `pose_arc` in its sidecar, and the check must
    say so rather than returning an OK on a performance nobody authored."""
    rec = _record(_blender(CHECK, [bind_pose_only]))
    assert rec["verdict"] == "NO_ARC", rec
    assert "no pose_arc" in rec["reason"]


def test_the_check_prints_a_record_even_when_its_arguments_are_wrong():
    """The contract is the printed record, not the exit code — so the record has to exist
    on every path, including the ones that used to `print(...)` and return 2."""
    rec = _record(_blender(CHECK, []))
    assert rec["verdict"] == "BAD_ARGS", rec
    assert "need a path" in rec["reason"]

    rec = _record(_blender(CHECK, ["nope.glb", "--fps=zero"]))
    assert rec["verdict"] == "BAD_ARGS", rec
    assert "--fps" in rec["reason"]
