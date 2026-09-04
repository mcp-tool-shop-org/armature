"""The pairing between what the detector saw and what was authored.

`truth` comes from `motion['ground_truth']`, each entry carrying its own `frame` number.
`rows` comes from the PNGs in `--render`, each row carrying the file it was read from.
`main` paired them with `zip(rows, truth)`, and `rotation_errors` zipped again. Nothing
compared the two lengths, and nothing compared a row's file number to the authored frame
number it was about to be graded against.

Gate DETECT only proves the detector fired on every frame it was given, so it is silent
here by construction. A render directory holding a different frame count truncates to the
shorter, and a directory numbered from 1 pairs frame 1's detection with frame 0's authored
pose all the way down — and then every rotation error, jitter figure and foot-slip number in
E09's report is computed against the wrong authored pose, while the record's
`"frames": len(rows)` names the detected count as if it were the compared population.

`resample_motion`'s own docstring names this failure ("the clip plays, the count is right,
and the dance starts late") and gates it there. This file gates it here.

The detector is not run: mediapipe is not a test dependency and the pairing is what is
under test, so `rows` are shaped exactly as `detect()` returns them.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_lift as ML  # noqa: E402


def _rows(n, start=0):
    """Shaped as `detect()` returns: `frame` is the ENUMERATION index, `file` is the name.

    That distinction is the whole defect — `r['frame']` is `range(len(rows))` no matter
    how the directory is numbered, so a gate comparing it to the authored frames would
    pass on the off-by-one it exists to catch.
    """
    return [{"frame": i, "file": f"{start + i:05d}.png", "fired": True} for i in range(n)]


def _truth(n, start=0):
    return [{"frame": start + i, "local": {}, "sites": {}, "root": (0.0, 0.0, 0.0)}
            for i in range(n)]


def test_a_short_render_against_a_longer_ground_truth_raises(tmp_path):
    """64 rendered frames, 65 authored. zip silently graded 64 and dropped the last."""
    with pytest.raises(ML.PairingGate) as e:
        ML.gate_pairing(_rows(64), _truth(65))
    ev = e.value.evidence
    assert ev["n_rendered"] == 64
    assert ev["n_authored"] == 65
    assert ev["authored_frames"][-1] == 64


def test_a_long_render_against_a_shorter_ground_truth_raises(tmp_path):
    """Both directions: zip truncates whichever side is longer."""
    with pytest.raises(ML.PairingGate) as e:
        ML.gate_pairing(_rows(66), _truth(65))
    assert e.value.evidence["n_rendered"] == 66


def test_a_render_numbered_from_one_raises_rather_than_pairing_off_by_one(tmp_path):
    """THE fixture the enumeration index cannot catch. 65 files numbered 00001..00065
    against truth numbered 0..64: the counts match, `r['frame']` is 0..64 either way, and
    every pose is graded against its predecessor's authored angles."""
    with pytest.raises(ML.PairingGate) as e:
        ML.gate_pairing(_rows(65, start=1), _truth(65, start=0))
    ev = e.value.evidence
    assert ev["rendered_frames"][:3] == [1, 2, 3]
    assert ev["authored_frames"][:3] == [0, 1, 2]
    assert ev["first_disagreement"] == 0


def test_a_gap_in_the_render_numbering_raises(tmp_path):
    rows = _rows(5)
    rows[3]["file"] = "00009.png"
    with pytest.raises(ML.PairingGate) as e:
        ML.gate_pairing(rows, _truth(5))
    assert e.value.evidence["first_disagreement"] == 3


def test_a_render_file_that_is_not_numbered_raises_naming_it(tmp_path):
    rows = _rows(3)
    rows[2]["file"] = "strip_every8.png"
    with pytest.raises(ML.PairingGate) as e:
        ML.gate_pairing(rows, _truth(3))
    assert "strip_every8.png" in str(e.value)


def test_a_matching_pair_returns_its_evidence_rather_than_raising(tmp_path):
    """The guard the other way: 65 for 65, numbered alike, must pass — and must say what
    it checked, since a gate that only ever raises is never read."""
    ev = ML.gate_pairing(_rows(65), _truth(65))
    assert ev["n_rendered"] == ev["n_authored"] == 65
    assert ev["verdict"].startswith("65 rendered frames")


def test_the_gate_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`. `-O` deletes an assert and this must survive."""
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import measure_lift as ML\n"
        "rows = [{'frame': i, 'file': '%%05d.png' %% i, 'fired': True} for i in range(4)]\n"
        "truth = [{'frame': i} for i in range(5)]\n"
        "try:\n"
        "    ML.gate_pairing(rows, truth)\n"
        "except ML.PairingGate:\n"
        "    print('RAISED')\n"
    ) % os.path.join(repo, "tools")
    out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in out.stdout, out.stderr
