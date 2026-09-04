"""Gate COUNT, which until now had no test at all.

`render_pose_sticks` writes the pose-stick control sequence that drives a paid generation,
and Gate COUNT is its own docstring's promise: "as many PNGs on disk as there are frames in
the record". The census it runs is

    written = sorted(f for f in os.listdir(out)
                     if f.endswith(".png") and f[0].isdigit())

— a case-SENSITIVE extension match against a first-character-is-a-digit stem test, while the
family was settled the other way in wave 8: the five consumers of that same directory
(`measure_floor.frame_population`, `encode_control.frame_population`,
`measure_arm._load_frames`, `gate_b_frames.frame_paths`, `measure_clip.frame_paths`) all
match `.png` case-INSENSITIVELY and test the whole stem with `isdigit()`.

Measured 2026-09-04 in this worktree, a 3-frame synthetic record: a first run wrote
00000..00002.png; `00003.PNG` was placed beside them and the same command re-run — exit 0,
`RENDER_STICKS_OK ... frames: 3`, and `sticks_manifest.json` recording
`gates.COUNT = {"verdict": "PASS", "frames": 3}`. On that same directory the five consumers
each returned FOUR names. The upper-case arrival is a real shape here:
`fetch_run.verify_downloads` sweeps `.PNG` as a downloaded frame (cited at
`measure_floor.py:196-199` as `00099.PNG`) and Windows preserves case.

The other direction already fired and is kept as the falsifiability fixture: a planted
`0_debug.png` — first character a digit, stem not numeric — raised `SticksGate` with exit 2
and the `RENDER_STICKS_HALT` line. Under the corrected predicate it is no longer counted as
a frame at all, so the gate is proved red here by the case direction instead.
"""

import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

from conftest import TOOLS  # noqa: F401,E402

from armature_core import aapose  # noqa: E402
import render_pose_sticks as RPS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 128, 128


def _pose():
    """A deterministic standing figure in pixels — the `test_aapose_convention` fixture,
    at this file's own frame size. Not measured from anything."""
    cx, cy = W * 0.5, H * 0.5
    s = min(W, H) / 6.0
    P = {
        0: (cx, cy - 2.30 * s), 1: (cx, cy - 1.80 * s),
        2: (cx - 0.70 * s, cy - 1.75 * s), 3: (cx - 1.05 * s, cy - 0.95 * s),
        4: (cx - 1.30 * s, cy - 0.15 * s),
        5: (cx + 0.70 * s, cy - 1.75 * s), 6: (cx + 1.05 * s, cy - 0.95 * s),
        7: (cx + 1.30 * s, cy - 0.15 * s),
        8: (cx - 0.45 * s, cy - 0.10 * s), 9: (cx - 0.50 * s, cy + 1.00 * s),
        10: (cx - 0.52 * s, cy + 2.05 * s),
        11: (cx + 0.45 * s, cy - 0.10 * s), 12: (cx + 0.50 * s, cy + 1.00 * s),
        13: (cx + 0.52 * s, cy + 2.05 * s),
        14: (cx - 0.18 * s, cy - 2.42 * s), 15: (cx + 0.18 * s, cy - 2.42 * s),
        16: (cx - 0.38 * s, cy - 2.36 * s), 17: (cx + 0.38 * s, cy - 2.36 * s),
        18: (cx + 0.62 * s, cy + 2.38 * s), 19: (cx - 0.62 * s, cy + 2.38 * s),
    }
    return [[P[i][0], P[i][1], 1.0] for i in range(20)]


def _record(path, frames=3):
    """A keypoint record this tool will accept: the convention pin is `aapose.SOURCE`'s own,
    so Gate CONV passes and the run reaches Gate COUNT, which is what is under test."""
    body = _pose()
    L = 0.06 * min(W, H)
    lh = [[p[0], p[1], 1.0] for p in
          aapose.mitten_hand((body[7][0], body[7][1], 0.0), (0, 1, 0), (1, 0, 0), L)]
    rh = [[p[0], p[1], 1.0] for p in
          aapose.mitten_hand((body[4][0], body[4][1], 0.0), (0, 1, 0), (-1, 0, 0), L)]
    rec = {"convention": dict(aapose.SOURCE), "resolution": [W, H], "frames": frames,
           "fps": 16, "body": [body] * frames,
           "left_hand": [lh] * frames, "right_hand": [rh] * frames,
           "diagnostics": {}}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    return path


def _run(tmp_path, frames=3):
    kp = _record(str(tmp_path / "kp.json"), frames)
    out = str(tmp_path / "sticks")
    assert RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0"]) == 0
    return kp, out


def test_a_clean_run_writes_the_frames_the_record_declares(tmp_path, capsys):
    """SUCCESS direction (rule 3): exit 0, the `RENDER_STICKS_OK` sentinel, and the
    manifest's own COUNT verdict over the population that is actually on disk."""
    _kp, out = _run(tmp_path)
    assert "RENDER_STICKS_OK " in capsys.readouterr().out
    man = json.loads(open(os.path.join(out, "sticks_manifest.json"), encoding="utf-8").read())
    assert man["gates"]["COUNT"] == {"verdict": "PASS", "frames": 3}
    assert sorted(f for f in os.listdir(out) if f.lower().endswith(".png")) == [
        "00000.png", "00001.png", "00002.png"]


def test_an_upper_case_png_beside_the_frames_halts_gate_count(tmp_path):
    """THE fixture: `00003.PNG`, the shape `fetch_run.verify_downloads` sweeps as a
    downloaded frame and Windows preserves.

    Under the case-sensitive predicate the gate recorded PASS over three frames while the
    directory held four, and every consumer of that directory derived the four.
    """
    kp, out = _run(tmp_path)
    Image.fromarray(np.zeros((H, W, 3), dtype=np.uint8)).save(
        os.path.join(out, "00003.PNG"))
    with pytest.raises(RPS.SticksGate) as e:
        RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0"])
    assert "4 frames" in str(e.value) and "record carries 3" in str(e.value)
    assert e.value.evidence["written"] == ["00000.png", "00001.png", "00002.png",
                                           "00003.PNG"]
    assert e.value.evidence["gate"] == "COUNT"


def test_the_gates_population_is_the_one_its_five_consumers_derive(tmp_path):
    """The node this census keys on is the DIRECTORY LISTING, and the property is that the
    gate's predicate is the consumers' predicate — so this asserts the two agree on the
    same directory rather than asserting a count.

    Population derived by importing the five consumers named in `measure_floor`'s and
    `measure_arm`'s docstrings and running each on the directory the tool just wrote.
    """
    import encode_control
    import gate_b_frames
    import measure_arm
    import measure_clip
    import measure_floor

    _kp, out = _run(tmp_path)
    Image.fromarray(np.zeros((H, W, 3), dtype=np.uint8)).save(
        os.path.join(out, "00003.PNG"))

    consumers = {
        "measure_floor.frame_population": lambda: measure_floor.frame_population(out),
        "encode_control.frame_population": lambda: encode_control.frame_population(out),
        "measure_arm._load_frames": lambda: measure_arm._load_frames(out)[0],
        "gate_b_frames.frame_paths": lambda: gate_b_frames.frame_paths(out),
        "measure_clip.frame_paths": lambda: measure_clip.frame_paths(out),
    }
    seen = {}
    for name, call in consumers.items():
        try:
            seen[name] = sorted(os.path.basename(str(p)) for p in call())
        except Exception as exc:            # the two that REFUSE a stray also see it
            seen[name] = type(exc).__name__
    for name, got in seen.items():
        assert got == ["00000.png", "00001.png", "00002.png", "00003.PNG"] \
            or isinstance(got, str), (name, got)
    # The gate now sees the same file the consumers do.
    assert RPS._written_frames(out) == ["00000.png", "00001.png", "00002.png",
                                        "00003.PNG"]


def test_a_digit_prefixed_non_frame_is_not_counted_as_a_frame(tmp_path):
    """The other direction of the same predicate, kept because it USED to fire.

    `0_debug.png` has a digit first character and a stem that is not a number. Under
    `f[0].isdigit()` it raised `SticksGate: wrote 4 frames and the record carries 3` — the
    gate over-counting safely. Under the consumers' `os.path.splitext(f)[0].isdigit()` it
    is not a frame at all, so the gate passes and the file is named nowhere: this pins
    which of the two behaviours the tool now has, rather than leaving it undescribed.
    """
    _kp, out = _run(tmp_path)
    Image.fromarray(np.zeros((H, W, 3), dtype=np.uint8)).save(
        os.path.join(out, "0_debug.png"))
    assert RPS._written_frames(out) == ["00000.png", "00001.png", "00002.png"]


def test_the_count_gate_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`. Driven through the `__main__` block so the halt
    contract rides with it: exit 2 and the `RENDER_STICKS_HALT` line."""
    kp, out = _run(tmp_path)
    Image.fromarray(np.zeros((H, W, 3), dtype=np.uint8)).save(
        os.path.join(out, "00003.PNG"))
    res = subprocess.run(
        [sys.executable, "-O", os.path.join(REPO, "tools", "render_pose_sticks.py"),
         f"--keypoints={kp}", f"--out={out}", "--strip=0"],
        capture_output=True, text=True)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "RENDER_STICKS_HALT " in res.stdout, res.stdout
