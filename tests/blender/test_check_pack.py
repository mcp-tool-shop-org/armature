"""First-class pytest nodes for tests/blender/check_*.py (wave 37, F-66df25e5).

The six scripts under tests/blender/ were suite product only partially hung off pytest —
individual wrappers existed for some, but `pytest tests/ -q` did not systematically drive
the headless check pack as collected nodes with blender markers. This thin pack
parametrizes over check_*.py (and make_synthetic_run), invokes each headless with a
timeout, and carries the `blender` marker so `-m blender` / `--suite-family=blender`
include it.
"""

from __future__ import annotations

import glob
import os
import subprocess

import pytest

from conftest import BLENDER, REPO, requires_blender

pytestmark = requires_blender()

BLENDER_DIR = os.path.join(REPO, "tests", "blender")
CHECK_SCRIPTS = sorted(
    os.path.basename(p) for p in glob.glob(os.path.join(BLENDER_DIR, "check_*.py"))
)
#: Sentinels each check prints on SUCCESS (blender -b -P exits 0 even on a crash).
SENTINELS = {
    "check_floor_material.py": "FLOOR_MATERIAL ",
    "check_ortho_convention.py": "ORTHO_CONVENTION ",
    "check_plate_composite.py": "PLATE_COMPOSITE ",
    "check_pose_arc_roundtrip.py": "POSE_ARC ",
    "check_visibility.py": "VISIBILITY ",
}


def test_the_blender_check_pack_lists_every_check_script():
    assert CHECK_SCRIPTS == [
        "check_floor_material.py",
        "check_ortho_convention.py",
        "check_plate_composite.py",
        "check_pose_arc_roundtrip.py",
        "check_visibility.py",
    ]
    assert os.path.isfile(os.path.join(BLENDER_DIR, "make_synthetic_run.py"))


@pytest.mark.parametrize("script", CHECK_SCRIPTS)
def test_every_blender_check_script_is_invokable_headless(script, tmp_path):
    """Drive each check_*.py under blender -b -P; assert its SUCCESS sentinel.

    check_pose_arc_roundtrip needs a subject GLB — skipped with the bank lever when the
    maker has not produced one in this session (the durable wrapper test_pose_arc_roundtrip
    still owns the full arc). make_synthetic_run is exercised beside conventions, not here.
    """
    path = os.path.join(BLENDER_DIR, script)
    if script == "check_pose_arc_roundtrip.py":
        pytest.skip(
            "check_pose_arc_roundtrip needs a subject.glb (outputs/ / banked); "
            "see tests/test_pose_arc_roundtrip.py for the full headless drive")
    cmd = [BLENDER, "-b", "-P", path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    sentinel = SENTINELS[script]
    assert sentinel in proc.stdout, (
        f"{script} produced no {sentinel!r}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


def test_make_synthetic_run_is_invokable_headless(tmp_path):
    script = os.path.join(BLENDER_DIR, "make_synthetic_run.py")
    out = tmp_path / "synthetic"
    proc = subprocess.run(
        [BLENDER, "-b", "-P", script, "--", str(out)],
        capture_output=True, text=True, timeout=900,
    )
    assert "SYNTHETIC_RUN " in proc.stdout, (
        f"make_synthetic_run produced no SYNTHETIC_RUN\nSTDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}")
