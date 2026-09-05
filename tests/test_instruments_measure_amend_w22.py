"""Wave 22, instruments-measure — Stage B amend #1, the domain's 18 approved findings.

Every test here names the OPERAND the wave-21 auditor measured on `e8263a3` and, per the
wave-18 rule 2 this brief carries unchanged, the SIBLINGS of that operand: the other rate
flags in the same family, the other empty-evidence raises in the same file, the other
`__main__` blocks in the same population. A fix whose red proof runs only on the one
member the finding happened to name is the shape that rule ends.

Nothing here judges whether an artifact is good. Every assertion is on a refusal, a
clause, an exit code, a printed halt record, or a file that is or is not on disk.
"""

import json
import math
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import REPO, TOOLS  # noqa: F401


# ===========================================================================
# helpers
# ===========================================================================

def _frames(tmp, name, numbers, size=(8, 8), colour=(30, 30, 30), mode="RGB"):
    """A frames directory whose files carry exactly `numbers`."""
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i in numbers:
        Image.new(mode, size, colour if mode == "RGB" else colour + (255,)).save(
            d / f"{i:05d}.png")
    return str(d)


def _run_main_block(module, argv, cwd=None):
    """Drive a tool's REAL `__main__` block as a subprocess and hand back the result.

    The halt record is a property of the process boundary — the printed line and the exit
    code — so it cannot be read by calling `main()` in process.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = TOOLS + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, os.path.join(TOOLS, f"{module}.py")] + list(argv),
        capture_output=True, text=True, cwd=cwd or REPO, env=env)


def _halt_record(proc, prefix):
    """The `<PREFIX>_HALT {json}` line the operator keys on, parsed."""
    for line in proc.stdout.splitlines():
        if line.startswith(prefix + " "):
            return json.loads(line[len(prefix) + 1:])
    return None


# ===========================================================================
# F-afa9c41e (HIGH) — make_ab_clip's two rate flags, and the eleven-flag family
# ===========================================================================

def test_a_negative_a_fps_refuses_instead_of_wrapping_the_pairing(tmp_path):
    """THE AUDITOR'S OPERAND: `--a-fps=-16 --b-fps=16` on two 4-frame arms.

    Measured on `e8263a3`: the run completed, printed `MAKE_AB_CLIP_OK` with
    `"clip_s": -0.25`, exited 0, and wrote both the WebP and the manifest. The axis
    `event_timeline(4, -16.0, 4, 16.0)` carried NEGATIVE indices, which `ia_frames[x]`
    resolves by Python's wrap-around to frames counted from the END — so the two arms were
    paired frame-3-against-frame-1 for the whole clip, under a banner printing the wrapped
    frame's own file number and a manifest asserting that NEITHER arm is retimed.
    """
    import make_ab_clip as AB

    a = _frames(tmp_path, "a", [0, 1, 2, 3])
    b = _frames(tmp_path, "b", [0, 1, 2, 3])
    out = tmp_path / "ab.webp"
    with pytest.raises(AB.ABClipError) as exc:
        AB.main([f"--a={a}", "--a-fps=-16", f"--b={b}", "--b-fps=16", f"--out={out}"])
    ev = exc.value.evidence
    assert ev["gate"] == "ARGS", ev
    assert ev["andon"] == "ABClipError", ev
    assert ev["clause"] == "playback_rate_not_positive", ev
    assert ev["flag"] == "--a-fps" and ev["value"] == -16.0, ev
    assert not out.exists(), "a refused run wrote a composite anyway"


@pytest.mark.parametrize("flag,value,clause", [
    ("--a-fps", "-16", "playback_rate_not_positive"),
    ("--a-fps", "0", "playback_rate_not_positive"),
    ("--a-fps", "nan", "playback_rate_not_finite"),
    ("--a-fps", "inf", "playback_rate_not_finite"),
    ("--b-fps", "-16", "playback_rate_not_positive"),
    ("--b-fps", "0", "playback_rate_not_positive"),
    ("--b-fps", "nan", "playback_rate_not_finite"),
    ("--b-fps", "inf", "playback_rate_not_finite"),
])
def test_both_rate_flags_are_bounded_on_both_directions(tmp_path, flag, value, clause):
    """SIBLINGS, enumerated: both flags x {negative, zero, nan, inf}.

    `--a-fps=0` raised a bare `ZeroDivisionError` and `--a-fps=nan` a bare
    `ValueError: cannot convert float NaN to integer` on `e8263a3`, neither naming the
    flag nor the value. Finite is checked FIRST, for the reason `resample_motion` records:
    `nan > 0` is False and `inf > 0` is True, so a positivity bound alone admits both.
    """
    import make_ab_clip as AB

    a = _frames(tmp_path, "a", [0, 1, 2, 3])
    b = _frames(tmp_path, "b", [0, 1, 2, 3])
    out = tmp_path / f"ab_{flag.strip('-')}_{value}.webp"
    argv = [f"--a={a}", f"--b={b}", f"--out={out}", "--a-fps=16", "--b-fps=16"]
    argv = [x for x in argv if not x.startswith(flag + "=")] + [f"{flag}={value}"]
    with pytest.raises(AB.ABClipError) as exc:
        AB.main(argv)
    assert exc.value.evidence["clause"] == clause, exc.value.evidence
    assert exc.value.evidence["flag"] == flag, exc.value.evidence
    assert not out.exists()


def test_event_timeline_refuses_a_non_positive_rate_itself(tmp_path):
    """The invariant does not depend on one caller checking it first."""
    import make_ab_clip as AB

    for bad in (-16.0, 0.0, float("nan")):
        with pytest.raises(AB.ABClipError) as exc:
            AB.event_timeline(4, bad, 4, 16.0)
        assert exc.value.evidence["flag"] == "--a-fps", exc.value.evidence
        with pytest.raises(AB.ABClipError) as exc_b:
            AB.event_timeline(4, 16.0, 4, bad)
        assert exc_b.value.evidence['flag'] == '--b-fps', exc_b.value.evidence


def test_no_accepted_input_produces_a_negative_index(tmp_path):
    """Grade the arm on what it can move: over accepted rates the axis never wraps."""
    import make_ab_clip as AB

    for na, fa, nb, fb in ((65, 16.0, 81, 20.0), (4, 16.0, 4, 16.0), (1, 1.0, 9, 240.0)):
        for _t, x, y in AB.event_timeline(na, fa, nb, fb):
            assert 0 <= x < na and 0 <= y < nb


def test_the_eleven_rate_flags_in_this_domain_are_all_bounded():
    """THE POPULATION, enumerated and measured — not the two the finding named.

    Every `--*fps*` argparse flag across the domain's 42 owned modules. Three tools (four
    flags) were bounded in waves 16/18; this wave closes the remaining seven. The check
    is behavioural where it can be: each module's source must carry a refusal naming its
    rate flag, so a later edit that deletes the bound goes red here.
    """
    expected = {
        "encode_control": ["--fps"],
        "lift_clip": ["--fps"],
        "make_ab_clip": ["--a-fps", "--b-fps"],
        "make_review_clip": ["--fps", "--source-fps"],
        "measure_cascade_clip": ["--expect-fps"],
        "measure_lift": ["--fps"],
        "pack_pose_pack": ["--fps"],
        "project_pose_keypoints": ["--fps"],
        "resample_motion": ["--fps-src"],
    }
    assert sum(len(v) for v in expected.values()) == 11
    for module, flags in expected.items():
        src = open(os.path.join(TOOLS, f"{module}.py"), encoding="utf-8").read()
        for flag in flags:
            assert f'"flag": "{flag}"' in src or f"'flag': '{flag}'" in src, (
                f"{module}{flag} reaches no refusal that names it")


# ===========================================================================
# F-070bfff3 (MEDIUM) — Gate TIMELINE quotes a frame time, not 1000/n_frames
# ===========================================================================

def test_the_timeline_refusal_quotes_a_shift_that_depends_on_the_RATE():
    """RED on `e8263a3`: the quoted milliseconds were `1000/len(numbers)` — INVARIANT to
    the rate. A 4-frame arm reported "250 ms-scale early" at 16 fps (true 62.5 ms) and the
    same 250 at 8 fps (true 125 ms). The same gapped arm at two rates must differ."""
    import make_ab_clip as AB

    gapped = [0, 1, 3, 4]
    msgs = {}
    for fps in (16.0, 8.0):
        with pytest.raises(AB.ABClipError) as exc:
            AB.gate_contiguous_numbering(gapped, "--a", fps)
        msgs[fps] = str(exc.value)
        ev = exc.value.evidence
        assert ev["fps"] == fps, ev
        assert ev["frame_time_ms"] == pytest.approx(1000.0 / fps), ev
        assert ev["frames_after_the_gap"] == 2, ev
        assert f"{1000.0 / fps:.1f} ms" in msgs[fps], msgs[fps]
    assert msgs[16.0] != msgs[8.0], "the quoted shift is invariant to the rate"


def test_the_timeline_gate_refuses_a_rate_it_cannot_quote():
    """A gate that divides by a rate bounds it: `1000/0` is not a shift."""
    import make_ab_clip as AB

    with pytest.raises(AB.ABClipError) as exc:
        AB.gate_contiguous_numbering([0, 1, 2], "--a", 0.0)
    assert exc.value.evidence["clause"] == "playback_rate_not_positive", exc.value.evidence


# ===========================================================================
# F-a5b1e0af (HIGH) — render_pose_sticks --strip is bounded ABOVE the first write
# F-eab60ac3 (MEDIUM) — the three `{}` evidence raises in the same file
# ===========================================================================

RPS_W, RPS_H = 128, 128


def _rps_pose():
    """A deterministic standing figure in pixels — `test_render_pose_sticks`' own fixture,
    at that file's frame size. Not measured from anything."""
    cx, cy = RPS_W * 0.5, RPS_H * 0.5
    s = min(RPS_W, RPS_H) / 6.0
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


def _rps_record(path, frames=3):
    """A keypoint record `render_pose_sticks` accepts, pinned to `aapose.SOURCE`."""
    from armature_core import aapose

    body = _rps_pose()
    L = 0.06 * min(RPS_W, RPS_H)
    lh = [[q[0], q[1], 1.0] for q in
          aapose.mitten_hand((body[7][0], body[7][1], 0.0), (0, 1, 0), (1, 0, 0), L)]
    rh = [[q[0], q[1], 1.0] for q in
          aapose.mitten_hand((body[4][0], body[4][1], 0.0), (0, 1, 0), (-1, 0, 0), L)]
    rec = {"convention": dict(aapose.SOURCE), "resolution": [RPS_W, RPS_H],
           "frames": frames, "fps": 16, "body": [body] * frames,
           "left_hand": [lh] * frames, "right_hand": [rh] * frames, "diagnostics": {}}
    open(path, "w", encoding="utf-8").write(json.dumps(rec))
    return path


def test_a_negative_strip_stride_refuses_before_any_frame_is_written(tmp_path):
    """THE AUDITOR'S OPERAND: `--strip=-8` on a 5-frame record.

    Measured on `e8263a3`: `list(range(0, 5, -8))` is `[]`, so `np.concatenate([], axis=1)`
    raised an untyped `ValueError: need at least one array to concatenate` — AFTER every
    `NNNNN.png` was written and Gate COUNT had passed, but BEFORE `sticks_manifest.json`.
    The output directory then held a complete-looking driving sequence with no manifest, no
    convention pin, no per-frame sha256 and no Gate INK/CANVAS verdicts, which every
    consumer deriving its population from a bare listing reads as a finished sequence.
    """
    import render_pose_sticks as RPS

    kp = _rps_record(str(tmp_path / "kp.json"), 5)
    out = tmp_path / "sticks_neg"
    with pytest.raises(RPS.SticksGate) as exc:
        RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=-8"])
    ev = exc.value.evidence
    assert ev["gate"] == "ARGS", ev
    assert ev["andon"] == "SticksGate", ev
    assert ev["clause"] == "strip_stride_not_positive", ev
    assert ev["flag"] == "--strip" and ev["value"] == -8, ev
    assert not out.exists(), "a refused run created the output directory anyway"


def test_the_strip_stride_zero_spelling_still_disables_the_strip(tmp_path):
    """Grade the arm on what it can move: `--strip=0` is the parser's own documented off
    switch, and a bound that refused it would fail on correct work."""
    import render_pose_sticks as RPS

    kp = _rps_record(str(tmp_path / "kp0.json"), 3)
    out = tmp_path / "sticks0"
    assert RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0"]) == 0
    assert (out / "sticks_manifest.json").exists()
    assert not [f for f in os.listdir(out) if f.startswith("strip_every")]


def test_the_strip_bound_is_read_where_the_stride_is_used(tmp_path):
    """SIBLING of the same flag: a stride LARGER than the population is legal (it yields
    one tile) and must not be refused — the invariant this gate bounds is the DIRECTION
    `range` collapses on, not the magnitude."""
    import render_pose_sticks as RPS

    kp = _rps_record(str(tmp_path / "kpbig.json"), 3)
    out = tmp_path / "sticks_big"
    assert RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=99"]) == 0
    assert (out / "strip_every99.png").exists()


def test_the_cv2_write_refusal_names_the_frame_and_the_path(tmp_path, monkeypatch):
    """RED on `e8263a3`: `raise SticksGate(f"cv2 refused to write {p}", {})` printed
    `"evidence": {}` in the `RENDER_STICKS_HALT` line — no gate, no clause, no frame index,
    no output path in any machine-readable field — with a partial control sequence already
    on disk eight lines below `os.makedirs`. Its own sibling twenty-four lines below (the
    strip write) carries `{"gate": "WRITE", ...}`."""
    import cv2

    import render_pose_sticks as RPS

    kp = _rps_record(str(tmp_path / "kpw.json"), 4)
    out = tmp_path / "sticks_w"
    real = cv2.imwrite
    state = {"n": 0}

    def fake(path, img, *rest):
        state["n"] += 1
        if state["n"] == 2:
            return False
        return real(path, img, *rest)

    monkeypatch.setattr(cv2, "imwrite", fake)
    with pytest.raises(RPS.SticksGate) as exc:
        RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0"])
    ev = exc.value.evidence
    assert ev, "the per-frame write refusal still carries an empty dict"
    assert ev["gate"] == "WRITE", ev
    assert ev["clause"] == "cv2_refused_the_frame_write", ev
    assert ev["frame"] == 1, ev
    assert os.path.basename(ev["path"]) == "00001.png", ev
    assert ev["n"] == 4 and ev["out"], ev


def test_the_record_self_disagreement_refusal_carries_its_counts(tmp_path):
    """SIBLING, the first of the three `{}` raises: the record declares more frames than
    it carries. Red today — the halt line printed `"evidence": {}`."""
    import render_pose_sticks as RPS

    path = _rps_record(str(tmp_path / "kpd.json"), 3)
    rec = json.loads(open(path, encoding="utf-8").read())
    rec["frames"] = 4
    open(path, "w", encoding="utf-8").write(json.dumps(rec))
    out = tmp_path / "sticks_d"
    with pytest.raises(RPS.SticksGate) as exc:
        RPS.main([f"--keypoints={path}", f"--out={out}", "--strip=0"])
    ev = exc.value.evidence
    assert ev, "the record-disagreement refusal still carries an empty dict"
    assert ev["clause"] == "record_frame_counts_disagree", ev
    assert ev["n_declared"] == 4, ev
    assert ev["n_body"] == 3 and ev["n_left_hand"] == 3 and ev["n_right_hand"] == 3, ev


def test_the_convention_pin_refusal_carries_both_digests(tmp_path):
    """SIBLING, the second of the three: the record was projected against a different
    convention pin. It already carried `record` / `module` but neither `gate` nor
    `clause`, so the halt line named no andon."""
    import render_pose_sticks as RPS

    path = _rps_record(str(tmp_path / "kpc.json"), 3)
    rec = json.loads(open(path, encoding="utf-8").read())
    rec["convention"]["sha256"] = "0" * 64
    open(path, "w", encoding="utf-8").write(json.dumps(rec))
    out = tmp_path / "sticks_c"
    with pytest.raises(RPS.SticksGate) as exc:
        RPS.main([f"--keypoints={path}", f"--out={out}", "--strip=0"])
    ev = exc.value.evidence
    assert ev["gate"] == "CONV", ev
    assert ev["clause"] == "convention_pin_disagrees", ev
    assert ev["record"] == "0" * 64 and len(ev["module"]) == 64, ev


def test_no_raise_site_in_this_module_passes_a_literal_empty_dict():
    """The census keyed on the RESOLVED shape (wave-18 rule 1): an empty dict LITERAL at
    the raise site is the same defect wave 16 deleted family-wide (`evidence or {}`),
    spelled where that sweep does not reach — and it is what the three sites above did."""
    import ast

    src = open(os.path.join(TOOLS, "render_pose_sticks.py"), encoding="utf-8").read()
    empty = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in node.exc.args[1:]:
                if isinstance(arg, ast.Dict) and not arg.keys:
                    empty.append(node.lineno)
    assert empty == [], f"raise sites still passing a literal empty evidence dict: {empty}"


# ===========================================================================
# F-5250a2ef (HIGH) — Gate CLIP_RATE cannot fire on a non-finite expectation
# ===========================================================================

def test_a_non_finite_expected_rate_is_a_refusal_not_a_PASS():
    """THE AUDITOR'S OPERAND: `gate_clip_rate({'fps': 16.0, 'stream': 's'}, nan, 'clip.mp4')`.

    Measured on `e8263a3`: it returned `delta=nan` and the verdict string
    "16.0 fps, within 0.05 of the declared nan" — a PASS asserting a property no code
    checked, because `nan > 0.05` is False. `inf` and `24.0` both raised.
    """
    import measure_cascade_clip as MCC

    with pytest.raises(MCC.ClipRateError) as exc:
        MCC.gate_clip_rate({"fps": 16.0, "stream": "s"}, float("nan"), "clip.mp4")
    assert "expect_fps" in str(exc.value)
    assert exc.value.evidence["gate"] == "CLIP_RATE", exc.value.evidence


@pytest.mark.parametrize("read,expect", [
    (float("nan"), 16.0),
    (float("inf"), 16.0),
    (16.0, float("nan")),
    (16.0, float("-inf")),
    (16.0, 0.0),
])
def test_both_operands_of_the_rate_comparison_are_bounded(read, expect):
    """SIBLINGS: the DECODED rate is the other half of the same comparison, and a
    zero expectation is a rate nothing can be within a tolerance of."""
    import measure_cascade_clip as MCC

    with pytest.raises(MCC.ClipRateError) as exc:
        MCC.gate_clip_rate({"fps": read, "stream": "s"}, expect, "clip.mp4")
    assert exc.value.evidence['clause'] in (
        'decoded_rate_not_finite', 'expected_rate_not_finite',
        'expected_rate_not_positive'), exc.value.evidence


def test_a_finite_agreeing_rate_still_passes():
    """What the gate takes when it does nothing and when it works: not the same number."""
    import measure_cascade_clip as MCC

    ev = MCC.gate_clip_rate({"fps": 16.0, "stream": "s"}, 16.0, "clip.mp4")
    assert ev["delta"] == pytest.approx(0.0)
    assert "16.0" in ev["verdict"]
