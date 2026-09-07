"""Wave 32 (Stage D amend) — core-solvers visual findings.

  F-db018aea  draw_hand HAND_EPS no longer wipes top/left in-frame hands
  F-eab59919  draw_frame refuses a blank plate (clause drawn_ink_empty)
  F-8e83b813  halt JSON puts evidence (clause first) before message
  F-0d3138c9  cp1252-hostile glyphs get ASCII stand-ins before the dump
  F-0f57accd  pose_sticks_ink_look records stickwidth next to resolution
"""

import io
import json
import os
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

from armature_core import aapose, parts, walk  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ===================================================================== F-db018aea


def _edge_hand(axis, value, n=21):
    """21-point hand along the top (y=value) or left (x=value) border."""
    kp = np.zeros((n, 3), dtype=np.float64)
    for i in range(n):
        if axis == "y":
            kp[i] = (5.0 + i, float(value), 1.0)
        else:
            kp[i] = (float(value), 5.0 + i, 1.0)
    return kp


def test_draw_hand_paints_top_and_left_border_joints():
    """RED on base: int() then `> HAND_EPS` wiped every joint with inted x/y of 0.

    Measured: 64x64 hand along y=0 -> ink 0; along y=1 -> ink 65. After the fix the
    detector-zero filter runs on the float pair, so a confident hand on the border draws.
    """
    for axis, value in (("y", 0.0), ("x", 0.0), ("y", 0.5), ("x", 0.5)):
        canvas = aapose.blank_canvas(64, 64)
        receipt = {}
        aapose.draw_hand(canvas, _edge_hand(axis, value), receipt=receipt)
        ink = int(np.count_nonzero(np.any(canvas != 0, axis=2)))
        assert ink > 0, (axis, value, ink, receipt)
        assert receipt["hand_drawn_joints"], (axis, value, receipt)


def test_draw_hand_still_skips_detector_zero_origin_sentinel():
    """Both floats <= HAND_EPS remain the unset sentinel and must not paint."""
    kp = np.zeros((21, 3), dtype=np.float64)
    kp[:, 2] = 1.0  # confident but at (0,0)
    canvas = aapose.blank_canvas(64, 64)
    receipt = {}
    aapose.draw_hand(canvas, kp, receipt=receipt)
    assert int(np.count_nonzero(canvas)) == 0
    assert receipt["hand_detector_zero_dropped"] == list(range(21))


# ===================================================================== F-eab59919


def test_draw_frame_refuses_a_blank_plate():
    """RED on base: all-outside body returned a black uint8 plate with no refusal."""
    body = np.full((aapose.KEYPOINT_COUNT, 3), 1.0, dtype=np.float64)
    body[:, 0] = 9000.0
    body[:, 1] = 9000.0
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(64, 64, body, draw_hands=False)
    assert exc.value.evidence["clause"] == "drawn_ink_empty"
    assert exc.value.evidence["n_ink"] == 0
    assert exc.value.evidence["n_confident"] == aapose.KEYPOINT_COUNT


def test_draw_frame_receipt_names_ink_and_stickwidth():
    body = np.zeros((aapose.KEYPOINT_COUNT, 3), dtype=np.float64)
    body[0] = (20, 20, 1)
    body[1] = (40, 20, 1)
    receipt = {}
    canvas = aapose.draw_frame(64, 64, body, draw_hands=False, receipt=receipt)
    assert int(np.count_nonzero(np.any(canvas != 0, axis=2))) == receipt["n_ink"] > 0
    assert receipt["stickwidth_px"] == aapose.stickwidth(64, 64, "v2")
    assert receipt["resolution"] == [64, 64]


# ===================================================================== F-0f57accd


@pytest.mark.parametrize("h,w", [(480, 832), (832, 480), (576, 1024), (512, 512)])
def test_pose_sticks_ink_look_states_the_one_px_floor(h, w):
    """Generator-legal sizes sit on the v2 floor; provenance must say so next to resolution."""
    look = aapose.pose_sticks_ink_look(h, w, "v2")
    assert look["resolution"] == [w, h]
    assert look["stickwidth_px"] == 1
    assert look["hand_stickwidth_px"] == 1
    assert look["at_formula_floor"] is True


# ===================================================================== F-8e83b813 / F-0d3138c9


_PROBE = '''\
import sys
sys.path.insert(0, {tools!r})
from armature_core.errors import GateFailure
from armature_core.parts import run_tool_main

MESSAGE = "arc 45.0\\u00b0; span 12 \\u2264 16 — see evidence"


class _Gate(GateFailure):
    gate = "GAIT"


def main():
    raise _Gate(MESSAGE, {{"stance_frac": 0.4, "clause": "stance_frac_not_modelled",
                          "gate": "GAIT"}})


if __name__ == "__main__":
    run_tool_main(main, "PROBE_TOOL")
'''


def _run_halt(tmp_path, io_encoding="utf-8"):
    script = tmp_path / "probe_halt.py"
    script.write_text(
        _PROBE.format(tools=os.path.join(REPO, "tools")), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = io_encoding
    env.pop("PYTHONWARNINGS", None)
    proc = subprocess.run([sys.executable, str(script)],
                          capture_output=True, env=env, timeout=120)
    codec = io_encoding.split(":")[0]
    out = proc.stdout.decode(codec, "replace")
    line = [ln for ln in out.splitlines() if ln.startswith("PROBE_TOOL_HALT ")]
    assert len(line) == 1, out
    rec = json.loads(line[0][len("PROBE_TOOL_HALT "):])
    return proc.returncode, rec, line[0]


def test_halt_line_puts_evidence_before_message_with_clause_first(tmp_path):
    """RED on base: key order buried clause behind a 700+ char message."""
    rc, rec, raw = _run_halt(tmp_path, "utf-8")
    assert rc == 2
    assert list(rec.keys()) == [
        "tool", "outcome", "gate", "evidence", "error", "message"]
    assert list(rec["evidence"].keys())[0] == "clause"
    assert rec["evidence"]["clause"] == "stance_frac_not_modelled"
    # First 160 columns of the JSON object must already name the branch word.
    payload = raw.split(" ", 1)[1]
    assert "stance_frac_not_modelled" in payload[:160]


def test_halt_ascii_standins_replace_le_before_the_stream_guard(tmp_path):
    """RED on base: cp1252 kept em dash / degree and escaped ≤ as \\u2264 mid-sentence."""
    assert parts.halt_ascii_standins("12 \u2264 16") == "12 <= 16"
    rc, rec, raw = _run_halt(tmp_path, "cp1252:strict")
    assert rc == 2
    assert "<=" in rec["message"]
    assert "\\u2264" not in raw
    assert "\u2264" not in rec["message"]


def test_printable_halt_line_remains_last_resort_for_hostile_glyphs():
    """Guard still backslash-replaces a leftover ≤ that skipped the stand-in path."""
    line = 'X_HALT {"m": "12 \u2264 16"}'

    class _Stream:
        encoding = "cp1252"
        errors = "strict"

    narrowed = parts.printable_halt_line(line, _Stream())
    assert "\\u2264" in narrowed
    narrowed.encode("cp1252")


def test_shortened_stance_gate_message_still_names_the_model():
    # WAVE 34: (0,1) is modelled; the live andon is stance_frac outside that interval.
    with pytest.raises(walk.GaitGate) as exc:
        walk.gate_stance_frac_is_modelled(1.5)
    assert "stance_frac in (0, 1)" in str(exc.value)
    assert len(str(exc.value)) < 200
    assert exc.value.evidence["clause"] == "stance_frac_outside_0_1"
