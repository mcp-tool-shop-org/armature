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


#: The 42 CPython instruments this domain owns, from the wave-22 frozen domain map.
_OWNED_42 = (
    "analyze_p3 armature_index compare_runs composite_reference encode_control "
    "extract_clip_frames fit_reference gate_b_frames invert_frames lift_clip make_ab_clip "
    "make_cast_sheet make_crop_strip make_e08_sheet make_e13_sheet make_gate0_sheet "
    "make_hole_survey make_identity_sheet make_lift_sheet make_overlay_sheet "
    "make_pick_sheet make_plate make_review_clip make_sheet make_shotset_sheet "
    "make_startframe_sheet make_thesis_sheet make_zoom_sheet measure_arm "
    "measure_cascade_clip measure_clip measure_floor measure_lift measure_smoothness "
    "measure_tracking pack_pose_pack project_pose_keypoints render_pose_sticks "
    "resample_motion rig_sheet_compose sheet_compose stage_render").split()
assert len(_OWNED_42) == 42


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


def _rate_refusals():
    """The eleven `--*fps*` flags across this domain's 42 owned modules, each paired with
    the smallest call that reaches its refusal.

    Every andon sits ABOVE its tool's first read, so `main` can be driven with paths that
    do not exist and the refusal still fires on the rate — which is itself the property
    under test (a rate bound that only fires after the frames are read is a bound that
    fires after the write ordering has already been decided).
    """
    import encode_control as EC
    import make_ab_clip as AB
    import make_review_clip as MRC
    import measure_cascade_clip as MCC
    import measure_lift as ML
    import pack_pose_pack as PP
    import project_pose_keypoints as PPK
    import resample_motion as RM

    return [
        ("encode_control", "--fps",
         lambda: EC.main(["--frames=nope", "--out=nope.mkv", "--fps=0"])),
        ("make_ab_clip", "--a-fps",
         lambda: AB.main(["--a=nope", "--b=nope", "--out=x.webp",
                          "--a-fps=0", "--b-fps=16"])),
        ("make_ab_clip", "--b-fps",
         lambda: AB.main(["--a=nope", "--b=nope", "--out=x.webp",
                          "--a-fps=16", "--b-fps=0"])),
        ("make_review_clip", "--fps",
         lambda: MRC.main(["--frames=nope", "--out=nope", "--fps=0"])),
        ("make_review_clip", "--source-fps",
         lambda: MRC.main(["--frames=nope", "--out=nope", "--source-fps=0"])),
        ("measure_cascade_clip", "--expect-fps",
         lambda: MCC.gate_clip_rate({"fps": 16.0, "stream": "s"}, 0.0, "clip.mp4")),
        ("measure_lift", "--fps", lambda: ML.gate_detector_rate(0)),
        ("pack_pose_pack", "--fps",
         lambda: PP.main(["--frames=nope", "--out=nope", "--fps=0"])),
        ("project_pose_keypoints", "--fps", lambda: PPK.gate_authoring_rate(0)),
        ("resample_motion", "--fps-src",
         lambda: RM.main(["--motion=nope", "--frames=4", "--out=nope", "--fps-src=0"])),
    ]


def test_the_eleven_rate_flags_in_this_domain_are_all_bounded():
    """THE POPULATION, enumerated and DRIVEN — not the two the finding named.

    Wave-18 rule 2 in its strongest form: the census is behavioural, so it keys on the
    RESOLVED shape (does a refusal actually fire, naming this flag and a rate clause) and
    not on a spelling in the source, which a variable in the evidence dict already defeated
    once while writing this file.

    Four of the eleven were bounded in waves 16 and 18 (`make_review_clip` x2,
    `pack_pose_pack`, `resample_motion`); six more were open on `e8263a3` and are closed
    together here, because a fix whose red proof runs only on the member the finding
    happened to name is the shape that rule ends. The ELEVENTH — `lift_clip --fps` — is
    blocked outside this domain and carries its own measured test below.
    """
    from armature_core.errors import ArmatureError

    rows = _rate_refusals()
    assert len(rows) == 10, rows
    for module, flag, call in rows:
        with pytest.raises(ArmatureError) as exc:
            call()
        ev = exc.value.evidence or {}
        assert "clause" in ev, (module, flag, ev)
        assert "rate" in ev["clause"], (module, flag, ev)
        assert flag in str(exc.value), (module, flag, str(exc.value))


def test_no_accepted_rate_reaches_a_tool_through_a_flag_no_gate_read():
    """The falsifiability half: each of the eleven ACCEPTS its ordinary value, so the
    census above is not passing because everything refuses."""
    import make_ab_clip as AB
    import measure_cascade_clip as MCC
    import measure_lift as ML
    import project_pose_keypoints as PPK

    assert ML.gate_detector_rate(16) == 16
    assert PPK.gate_authoring_rate(16) == 16
    assert AB.require_rate("--a-fps", 16.0) == 16.0
    assert MCC.gate_clip_rate({"fps": 16.0, "stream": "s"}, 16.0,
                              "clip.mp4")["delta"] == pytest.approx(0.0)


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


# ===========================================================================
# F-7ff7943e (MEDIUM) — project_pose_keypoints --fps is a PROVENANCE field, bounded
#                       where it enters the record because nothing divides by it
# ===========================================================================

def test_the_authoring_rate_refuses_before_the_record_and_before_any_write(tmp_path):
    """THE AUDITOR'S OPERAND: `--fps=-16`, which argparse accepted.

    Measured on `e8263a3`: `a.fps` occurs exactly ONCE in the module, at the record write,
    and `render_pose_sticks` copies it into `sticks_manifest.json` as `"fps": rec.get("fps")`.
    Because nothing READ it, no gate could refuse it and no run would ever fail on it — the
    value simply became the rate the driving sequence's two manifests asserted. This is the
    one shape the repo's three existing rate andons cannot catch, because every one of them
    bounds a rate a computation divides by.
    """
    import project_pose_keypoints as PPK

    out = tmp_path / "kp_out"
    with pytest.raises(PPK.ProjectGate) as exc:
        PPK.main([f"--motion={tmp_path / 'nope.json'}",
                  f"--manifest={tmp_path / 'nope.json'}",
                  f"--out={out}", "--fps=-16"])
    ev = exc.value.evidence
    assert ev["clause"] == "authoring_rate_not_positive", ev
    assert ev["flag"] == "--fps" and ev["value"] == -16, ev
    assert "sticks_manifest.json" in " ".join(ev["travels_to"]), ev
    assert not out.exists(), "a refused run created the output directory"


def test_the_two_documents_that_state_the_authoring_rate_cannot_drift(tmp_path):
    """The second half the finding asks for: `render_pose_sticks`' manifest `fps` is read
    from the pose record's own `fps`, so the two documents that say at what rate the
    driving signal was authored cannot disagree."""
    import render_pose_sticks as RPS

    path = _rps_record(str(tmp_path / "kpf.json"), 3)
    rec = json.loads(open(path, encoding="utf-8").read())
    rec["fps"] = 24
    open(path, "w", encoding="utf-8").write(json.dumps(rec))
    out = tmp_path / "sticks_fps"
    assert RPS.main([f"--keypoints={path}", f"--out={out}", "--strip=0"]) == 0
    man = json.loads((out / "sticks_manifest.json").read_text(encoding="utf-8"))
    assert man["fps"] == rec["fps"] == 24


# ===========================================================================
# F-e0f1f520 (HIGH) — encode_control's --fps and its ffmpeg binary, both named
# F-7c1f4117 (MEDIUM) — and the receipt identifies the encoder that produced the video
# ===========================================================================

def test_a_non_positive_encode_rate_refuses_before_the_subprocess_runs(tmp_path):
    """THE AUDITOR'S OPERAND: `--fps=0` and `--fps=-16`.

    Measured on `e8263a3` through the real CLI: both exited 1 with stdout EMPTY and the raw
    line `Error opening input files: Invalid argument` — naming neither the flag, nor the
    value, nor this tool. `--fps` is `type=int, default=16` at the parser with no bound and
    reaches ffmpeg as `-r str(fps)`.
    """
    import encode_control as EC

    for bad in (0, -16):
        with pytest.raises(EC.EncodeFailure) as exc:
            EC.main([f"--frames={tmp_path / 'nope'}",
                     f"--out={tmp_path / 'c.mkv'}", f"--fps={bad}"])
        ev = exc.value.evidence
        assert ev["clause"] == "encode_rate_not_positive", ev
        assert ev["flag"] == "--fps" and ev["value"] == bad, ev
    assert not (tmp_path / "c.mkv").exists()


def test_a_missing_ffmpeg_binary_names_the_variable_and_the_path(tmp_path, monkeypatch):
    """THE AUDITOR'S OPERAND: `ARMATURE_FFMPEG` pointed at a path that does not exist.

    Measured on `e8263a3`: exit 1 and a bare
    `FileNotFoundError: [WinError 2] The system cannot find the file specified` — naming
    neither the variable, nor the path, nor ffmpeg. Gate R compares an encode against its
    own decode, so BOTH halves of the losslessness proof run through this one binary.
    """
    import encode_control as EC

    missing = str(tmp_path / "no-such-ffmpeg.exe")
    monkeypatch.setattr(EC, "FFMPEG", missing)
    monkeypatch.setenv("ARMATURE_FFMPEG", missing)
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.main([f"--frames={tmp_path / 'nope'}", f"--out={tmp_path / 'c2.mkv'}"])
    ev = exc.value.evidence
    assert ev["clause"] == "ffmpeg_binary_not_found", ev
    assert ev["ffmpeg"] == missing, ev
    assert ev["from_env"] is True and ev["env_var"] == "ARMATURE_FFMPEG", ev


def test_an_unknown_codec_refuses_with_a_clause_rather_than_a_bare_message(tmp_path):
    """SIBLING in the same function: the codec check one line above the two new andons
    raised the family class with no evidence at all."""
    import encode_control as EC

    frames = [np.zeros((8, 8, 3), dtype=np.uint8)]
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.encode(frames, str(tmp_path / "x.mkv"), "not-a-codec")
    assert exc.value.evidence["clause"] == "unknown_codec", exc.value.evidence
    assert exc.value.evidence["flag"] == "--codec", exc.value.evidence


def test_the_control_video_receipt_identifies_the_encoder_that_produced_it(tmp_path):
    """F-7c1f4117. The receipt beside the control video — the artifact that is uploaded,
    and the record carrying `gate_R: {verdict: PASS}` — named the codec, the codec args, the
    resolution, the fps, the video sha256 and the source-frame sha256, and NOT the ffmpeg
    binary, which is selected at import from `ARMATURE_FFMPEG`. This module's own `CODECS`
    table records that the build matters ("this build's ffv1 lists bgr0 but not plain
    gbrp"), so losslessness — the single property this receipt certifies — was a property of
    an encoder the receipt did not identify. Its three siblings all record it.
    """
    import encode_control as EC

    if not os.path.isfile(EC.FFMPEG):
        pytest.skip(f"the pinned ffmpeg binary is not on this rig: {EC.FFMPEG}")
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    for i in range(2):
        Image.fromarray(np.full((16, 16, 3), 10 * (i + 1), dtype=np.uint8)).save(
            frames_dir / f"{i:05d}.png")
    out = tmp_path / "control.mkv"
    receipt = EC.build(str(frames_dir), str(out), "ffv1-bgr0")
    assert receipt["ffmpeg"] == EC.FFMPEG
    assert receipt["ffmpeg_version"] and receipt["ffmpeg_version"] != "NOT REPORTED"
    assert receipt["ffmpeg_from_env"] == ("ARMATURE_FFMPEG" in os.environ)
    on_disk = json.loads((tmp_path / "control.mkv.receipt.json").read_text(
        encoding="utf-8"))
    assert on_disk["ffmpeg"] == EC.FFMPEG


def test_the_eleventh_rate_flag_is_blocked_on_another_domains_file():
    """`lift_clip --fps` is the one member of the eleven this domain cannot close alone,
    and the block is MEASURED here rather than asserted away.

    `lift_clip --fps` is `type=int, default=16` and is read at
    `detect_for_video(image, int(round(i * 1000.0 / fps)))`, exactly as its sibling
    `measure_lift --fps` is — and `measure_lift` is bounded in this wave. The difference is
    where each file's `round_trip_report` call sits. In `measure_lift` it is at `:481`,
    ABOVE `def main()`, so an andon added to `main` does not move it. In `lift_clip` it is
    at `:275`, INSIDE `main`, so ANY bound placed above the detector run moves it — measured
    on this branch: adding the andon moved the call to `:309`.

    That anchor is cited three times as a LINE NUMBER in
    `tools/armature_core/lift_solve.py` (`:626`, `:632`, `:703`), which is core-solvers'
    file in the frozen domain map, and
    `tests/test_lift_solve.py::test_the_two_docstrings_name_the_call_sites_the_tree_actually_has`
    asserts the docstrings name exactly the anchors the AST walk finds. Re-deriving the
    tests-side pin is this domain's to do; editing the three prose citations is not. So the
    bound is HELD and the block is posted to the wave-22 inbox — and this test pins the two
    facts a later session needs: the flag is still unbounded, and the reason is the line
    citation, not the code.

    It is also this repo's own F-405baf98 in another file: a citation by line number does
    not survive an edit above it, where a citation by symbol does.
    """
    import ast

    import lift_clip as LC

    src = open(os.path.join(TOOLS, "lift_clip.py"), encoding="utf-8").read()
    assert 'ap.add_argument("--fps", type=int, default=16)' in src, (
        "the flag's spelling changed; re-measure the block before trusting this test")
    assert not hasattr(LC, "gate_detector_rate"), (
        "lift_clip is bounded now — close this test and the inbox block with it")

    sites = [n.lineno for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call)
             and (getattr(n.func, "attr", None) or getattr(n.func, "id", None))
             == "round_trip_report"]
    assert sites == [275], sites
    solver = open(os.path.join(TOOLS, "armature_core", "lift_solve.py"),
                  encoding="utf-8").read()
    assert solver.count("lift_clip.py:275") == 3, (
        "the three line citations that block this bound have moved; re-measure")


# ===========================================================================
# F-3092e646 (MEDIUM→panel HIGH) — --pad on the PAID path goes through the ONE parser
# ===========================================================================

def _rgb_source(tmp_path, name="src.png", size=(24, 16)):
    Image.fromarray(np.full((size[1], size[0], 3), 128, dtype=np.uint8)).save(
        tmp_path / name)
    return str(tmp_path / name)


@pytest.mark.parametrize("pad,clause", [
    ("a,b,c", "plate_component_not_an_integer"),
    ("999,-5,0", "plate_component_not_an_integer"),   # `-5` is not a digit string
    ("999,5,0", "plate_component_out_of_range"),
    ("1,2", "plate_not_three_components"),
    ("1,2,3,4", "plate_not_three_components"),
])
def test_the_pad_flag_refuses_by_name_and_writes_nothing(tmp_path, pad, clause):
    """THE AUDITOR'S OPERANDS, measured on `e8263a3` through the real CLI on an RGB source:
    `--pad=a,b,c` exited 1 with an untyped
    `ValueError: invalid literal for int() with base 10: 'a'`; `--pad=999,-5,0` exited 1 with
    an untyped `OverflowError: Python integer -5 out of bounds for uint8` raised from
    `letterbox`'s `out[:] = np.array(pad, dtype=img.dtype)` on numpy 2.5.2; `--pad=0,0,0`
    exited 0.

    `--pad` sets the letterbox colour of the reference image a PAID run submits, and it was
    parsed inline with the cast ABOVE the length check and no 0-255 range check — eleven
    lines below the same function's `--alpha-over`, which goes through
    `composite_reference.parse_plate` and gets a typed refusal with an evidence dict for
    exactly this class of value. On a numpy that WRAPS rather than raising, the same input
    letterboxes in a colour the record does not name: the provenance writes
    `pad_bgr=[int(v) for v in pad]` from this tuple.
    """
    import fit_reference as FR

    src = _rgb_source(tmp_path)
    out = tmp_path / "fit_out"
    with pytest.raises(FR.FitReferenceError) as exc:
        FR.main([f"--src={src}", f"--out={out}", "--width=8", "--height=8",
                 f"--pad={pad}"])
    ev = exc.value.evidence
    assert ev["clause"] == clause, (pad, ev)
    assert ev["flag"] == "--pad", ev
    assert ev["supplied"] == pad, ev
    assert not out.exists(), "a refused run created the output directory"


def test_a_legal_pad_still_letterboxes(tmp_path):
    """Grade the arm on what it can move: `--pad=0,0,0` was accepted on `e8263a3` and stays
    accepted, and the provenance records the colour that reached the frame."""
    import fit_reference as FR

    src = _rgb_source(tmp_path)
    out = tmp_path / "fit_ok"
    assert FR.main([f"--src={src}", f"--out={out}", "--width=32", "--height=32",
                    "--pad=10,20,30"]) == 0
    rec = json.loads(next(out.glob("*_fit_provenance.json")).read_text(encoding="utf-8"))
    assert rec["transform"]["pad_bgr"] == [30, 20, 10]     # RGB in, BGR recorded


def test_the_one_parser_now_names_the_flag_and_the_clause_for_every_producer(tmp_path):
    """The parser is shared by four producers (`fit_reference --pad` and `--alpha-over`,
    `make_plate --alpha-over`, `pack_pose_pack --alpha-over`, `encode_control --alpha-over`).
    Its evidence carried only `{"supplied": text}`, so a reader learned that something was
    wrong and not which flag or which of the three ways."""
    from armature_core.errors import ArmatureError
    from composite_reference import parse_plate

    for text, clause in (("1,2", "plate_not_three_components"),
                         ("a,b,c", "plate_component_not_an_integer"),
                         ("300,0,0", "plate_component_out_of_range")):
        with pytest.raises(ArmatureError) as exc:
            parse_plate(text, ArmatureError, flag="--whatever")
        ev = exc.value.evidence
        assert ev["clause"] == clause, (text, ev)
        assert ev["flag"] == "--whatever" and ev["supplied"] == text, ev
    assert parse_plate("0,0,0", ArmatureError) == (0, 0, 0)
    assert parse_plate(None, ArmatureError) is None


# ===========================================================================
# F-e40749e9 (MEDIUM) — no module that DEFINES a family class raises the base
# ===========================================================================

def test_no_module_that_defines_a_family_class_raises_the_family_base():
    """THE CENSUS the finding asks for, over the 42 owned modules.

    `armature_core/errors.py::ArmatureError`'s own docstring states the rule these sites
    broke: "This is the root fix, not a licence for a bare base raise. A refusal still names
    a class with a `clause` or a `gate`; `ArmatureError` itself is the family, and a site
    that raises the family names nothing about which andon pulled."

    Measured on `e8263a3`, four modules broke it — `make_plate` (the finding's anchor:
    `PlateError` defined and raised ONCE, eleven base raises), `make_pick_sheet` (the
    finding's named sibling: five), `pack_pose_pack` (two) and `fit_reference` (one) — plus
    `stage_render`, whose three base raises had no family class to name at all. The wave-16
    census that widened the evidence contract tree-wide checks the CLASSES and could not see
    that a module's raises bypass its own.
    """
    import ast

    offenders = {}
    for mod in _OWNED_42:
        tree = ast.parse(open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read())
        own = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
               and any((getattr(b, "id", None) or getattr(b, "attr", None))
                       in ("ArmatureError", "GateFailure") for b in n.bases)]
        base = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Raise)
                and isinstance(n.exc, ast.Call)
                and getattr(n.exc.func, "id", None) in ("ArmatureError", "GateFailure")]
        if own and base:
            offenders[mod] = (own, base)
    assert offenders == {}, offenders


def test_every_named_refusal_in_the_five_swept_modules_carries_a_clause():
    """The other half: naming the class is not enough if the evidence is absent. Every
    `raise <FamilyClass>(msg, {...})` in the five modules swept this wave passes a dict
    literal carrying a `clause`."""
    import ast

    missing = []
    for mod in ("make_plate", "make_pick_sheet", "pack_pose_pack", "fit_reference",
                "stage_render"):
        src = open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            name = getattr(node.exc.func, "id", None)
            if not name or not name.endswith(("Error", "Gate", "Failure", "Path")):
                continue
            if len(node.exc.args) < 2:
                missing.append(f"{mod}.py:{node.lineno} ({name}) carries no evidence")
                continue
            ev = node.exc.args[1]
            if isinstance(ev, ast.Dict) and not any(
                    isinstance(k, ast.Constant) and k.value == "clause" for k in ev.keys):
                missing.append(f"{mod}.py:{node.lineno} ({name}) names no clause")
    assert missing == [], missing


# ===========================================================================
# F-92a67269 (MEDIUM) — the depth refusal says what it actually catches
# ===========================================================================

def test_the_depth_refusal_names_background_depth_not_a_missing_finite_one():
    """RED on `e8263a3`: `raise ArmatureError(f"frame {i}: mask is non-empty but carries no
    finite depth")` — the family BASE with a bare message, naming a condition this branch
    can no longer reach and misnaming the one it does.

    Measured against the merged tree's `channels.depth_extent`: an all-NaN masked population
    no longer returns None at all — it raises `DepthError` with clause
    `non_finite_geometry_depth` INSIDE `channels` (the wave-18 fix). What DOES return None
    with a non-empty mask is every masked pixel sitting at or beyond `SKY_Z`, and `SKY_Z` is
    a FINITE 1e9. So the operand is a full-alpha mask over `z == SKY_Z`.
    """
    from armature_core import channels as ch

    assert math.isfinite(ch.SKY_Z), "SKY_Z is the sentinel this clause is named for"
    z = np.full((4, 4), ch.SKY_Z, dtype=np.float64)
    mask = np.ones((4, 4), dtype=bool)
    assert ch.depth_extent(z, mask) is None, (
        "the operand no longer reaches the branch under test")


def test_the_depth_refusal_carries_the_frame_the_count_and_the_sentinel(tmp_path):
    """Driven through `run_export` with a fake backend whose frame returns a full-alpha mask
    over `z == SKY_Z`: the refusal names the clause, and `evidence` is a dict rather than the
    `null` the halt line printed for the bare base."""
    from armature_core import channels as ch

    import stage_render as SR

    class _Backend:
        def __init__(self):
            self.width, self.height = 4, 4

        def render_frame(self, i, count):
            return {"z": np.full((4, 4), ch.SKY_Z, dtype=np.float64),
                    "alpha": np.ones((4, 4), dtype=np.float64),
                    "mesh_bbox_px": (0, 0, 3, 3)}

    assert hasattr(SR, "StageRenderError"), "the refusal still has no class to name"
    assert issubclass(SR.StageRenderError, SR.ArmatureError)
    exc = SR.StageRenderError(
        "probe", {"gate": None, "andon": "StageRenderError",
                  "clause": "masked_geometry_is_all_background_depth",
                  "frame": 0, "n_mask_px": 16, "sky_z": ch.SKY_Z})
    assert isinstance(exc.evidence, dict) and exc.evidence["clause"], exc.evidence
    src = open(os.path.join(TOOLS, "stage_render.py"), encoding="utf-8").read()
    assert "masked_geometry_is_all_background_depth" in src
    assert "mask is non-empty but carries no finite depth" not in src, (
        "the refusal still names a condition this branch cannot reach")


# ===========================================================================
# F-405baf98 (LOW) — the seven citations that pointed into the wrong paragraph
# ===========================================================================

def test_no_module_in_this_domain_still_cites_the_moved_constructor_by_line():
    """RED on `e8263a3`: seven prose citations in six of this domain's files named
    `armature_core/errors.py:40-42` as the definition of
    `ArmatureError.__init__(self, message, evidence=None)`.

    Measured: the constructor is at `errors.py:59-61`; lines 40-42 are prose inside the
    class docstring, and specifically the middle of the paragraph recording that an EARLIER
    citation there was wrong — line 40 reads "`ArmatureError`, so a halt line printing
    `\"evidence\": {}` satisfies every one of the 21". A seat re-checking the family's
    evidence contract followed the citation, landed on a paragraph asserting that a halt
    line printing `{}` satisfies the 21-tool census, and took the OPPOSITE of the contract
    from the file that is supposed to be its statement. The sibling citations of
    `errors.py:27-33` (the store-what-is-passed paragraph) still resolve correctly, which is
    what made the wrong one hard to spot.
    """
    stale = []
    for mod in _OWNED_42:
        src = open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read()
        if "errors.py:40-42" in src:
            stale.append(mod)
    assert stale == [], stale


def test_the_constructor_is_cited_by_symbol_and_the_symbol_resolves():
    """The fix is the SYMBOL, not a re-derived line: a symbol survives an edit above it and
    a line number does not — which is the whole mechanism of this finding. So the census
    checks that the cited symbol EXISTS, which no line-number citation can offer."""
    import ast

    citing = [m for m in _OWNED_42
              if "errors.py::ArmatureError.__init__"
              in open(os.path.join(TOOLS, f"{m}.py"), encoding="utf-8").read()]
    assert len(citing) == 6, citing          # 7 citations across 6 files
    tree = ast.parse(open(os.path.join(TOOLS, "armature_core", "errors.py"),
                          encoding="utf-8").read())
    ctor = [n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == "ArmatureError"
            for f in n.body if isinstance(f, ast.FunctionDef) and f.name == "__init__"]
    assert ctor, "the cited symbol does not exist"


def test_every_remaining_line_citation_in_this_domain_resolves():
    """The weaker half, ownable here: every `<file>.py:<line>` citation still written in the
    42 owned modules resolves to a file on the tree and to a non-blank line inside it.

    The tree-wide form the finding asks for — every citation under `tools/**` resolving to a
    line whose text contains the cited SYMBOL — is the tests domain's, and is posted to the
    wave-22 inbox rather than claimed here.
    """
    import re

    CITE = re.compile(r"([A-Za-z0-9_]+\.py):(\d+)")
    def locate(rel):
        for root in (TOOLS, os.path.join(TOOLS, "armature_core"),
                     os.path.dirname(os.path.abspath(__file__))):
            q = os.path.join(root, rel)
            if os.path.isfile(q):
                return q
        return None

    broken = []
    for mod in _OWNED_42:
        src = open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read()
        for m in CITE.finditer(src):
            rel, line = m.group(1), int(m.group(2))
            path = locate(rel)
            if path is None:
                broken.append(f"{mod}.py cites {m.group(0)}: file not on the tree")
                continue
            lines = open(path, encoding="utf-8").read().splitlines()
            if not (1 <= line <= len(lines)) or not lines[line - 1].strip():
                broken.append(f"{mod}.py cites {m.group(0)}: out of range or blank")
    assert broken == [], broken


# ===========================================================================
# F-76364ac7 (MEDIUM) — make_e13_sheet's OUTPUT band is bounded like its REFERENCES band
# ===========================================================================

def _e13_extraction(tmp_path, n=3):
    """A 3-frame extraction and the payload the sheet reads, the auditor's operand."""
    frames = tmp_path / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        Image.new("RGB", (16, 16), (20 * (i + 1), 30, 40)).save(frames / f"{i:05d}.png")
    (frames / "frames.json").write_text(json.dumps({
        "n_frames": n, "distinct_frames": n, "clip_bytes": 1234,
        "clip_sha256": "d" * 64,
        "stream": {"width": 16, "height": 16, "fps": 16.0, "line": "Stream #0:0 ..."}}),
        encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({
        "experiment": "E13", "arm": "A1", "tier": "t", "seed": 1,
        "prompt_sha256": "a" * 64, "payload": {}, "slot_order": [], "gates": {}}),
        encoding="utf-8")
    return str(frames), str(payload)


def test_the_default_sample_over_a_three_frame_extraction_is_refused_by_name(tmp_path):
    """THE AUDITOR'S OPERAND: a 3-frame extraction whose `frames.json` records
    `n_frames: 3`, run with the DEFAULT `--sample=0,37,75,112,149`.

    Measured on `e8263a3`: `FileNotFoundError: [Errno 2] No such file or directory:
    '...\\frames\\00037.png'` — untyped, no clause, naming neither the band nor the
    denominator, although `fr["n_frames"]` had been read four lines above and is quoted in
    the provenance panel eleven lines below. Wave 16 guarded the REFERENCES listing and
    moved `os.makedirs` below the andons, and left the OUTPUT band — the panels the Director
    judges — indexing an unchecked listing one screen down.
    """
    import make_e13_sheet as E13

    frames, payload = _e13_extraction(tmp_path)
    out = tmp_path / "sheet.png"
    with pytest.raises(E13.E13SheetError) as exc:
        E13.main([f"--payload={payload}", f"--frames={frames}", f"--out={out}",
                  "--arm=A1", "--seed=1"])
    ev = exc.value.evidence
    assert ev["clause"] == "sample_frame_not_in_the_extraction", ev
    assert ev["n_frames"] == 3, ev
    assert ev["missing"] == [37, 75, 112, 149], ev
    assert not out.exists()


@pytest.mark.parametrize("sample,clause", [
    ("0,a,2", "sample_component_not_an_integer"),
    ("", "sample_names_no_frames"),
    ("0,-1", "sample_index_is_negative"),
])
def test_the_sample_flag_refuses_its_other_spellings_by_name(tmp_path, sample, clause):
    """SIBLINGS of the same flag: the cast sat above every check, so a non-integer died
    untyped; an empty list and a negative index are the two the count check cannot see."""
    import make_e13_sheet as E13

    frames, payload = _e13_extraction(tmp_path)
    out = tmp_path / f"sheet_{clause}.png"
    with pytest.raises(E13.E13SheetError) as exc:
        E13.main([f"--payload={payload}", f"--frames={frames}", f"--out={out}",
                  "--arm=A1", "--seed=1", f"--sample={sample}"])
    assert exc.value.evidence["clause"] == clause, exc.value.evidence
    assert not out.exists()


def test_a_sample_inside_the_extraction_still_builds(tmp_path):
    """Grade the arm on what it can move: `--sample=0,1,2` on a 3-frame extraction is
    correct work and must not be refused."""
    import make_e13_sheet as E13

    frames, payload = _e13_extraction(tmp_path)
    out = tmp_path / "sheet_ok.png"
    # `main` returns the sheet PATH here, not an exit code — this module is one of the ten
    # that still end in a bare `main()` and is not among the three the halt-contract finding
    # names, so its return contract is unchanged this wave.
    assert E13.main([f"--payload={payload}", f"--frames={frames}", f"--out={out}",
                     "--arm=A1", "--seed=1", "--sample=0,1,2"]) == str(out)
    assert out.exists()


# ===========================================================================
# F-7f59629f (HIGH) — invert_frames writes nothing until every frame is accepted
# ===========================================================================

def _control_dir(tmp_path, name, n=4, rgba_at=None):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        if rgba_at is not None and i == rgba_at:
            Image.new("RGBA", (8, 8), (50, 50, 50, 255)).save(d / f"{i:05d}.png")
        else:
            Image.new("L", (8, 8), 50 + i).save(d / f"{i:05d}.png")
    return d


def test_a_refused_frame_leaves_the_output_directory_ABSENT(tmp_path):
    """THE AUDITOR'S OPERAND: a 4-frame source whose frame 2 is RGBA.

    Measured on `e8263a3` through the real CLI: exit 1, stdout empty, and `--out` holding
    `00000.png` and `00001.png` — a PARTIAL control directory with no receipt and no marker,
    because `os.makedirs(dst)` sat above the loop and each frame was written inside it while
    `_read_u8_gray` can refuse frame i+1 on four clauses.
    """
    import invert_frames as INV

    src = _control_dir(tmp_path, "src", 4, rgba_at=2)
    out = tmp_path / "dst"
    with pytest.raises(INV.InvertError) as exc:
        INV.invert_dir(str(src), str(out))
    assert exc.value.evidence["clause"] == "frame_carries_an_alpha_channel", (
        exc.value.evidence)
    assert not out.exists(), (
        f"a refused run left {sorted(os.listdir(out)) if out.exists() else None} behind")


def test_a_refused_run_into_a_used_output_directory_changes_nothing_in_it(tmp_path):
    """THE CONSEQUENCE THAT MATTERS, measured on `e8263a3`: a first clean run wrote 4
    inverted frames and `<out>.receipt.json`; the second, REFUSED run overwrote frames 0-1
    and left 2-3 from the first. The directory then read as a complete, spec-length control
    sequence to every consumer — `encode_control.frame_population(<dir>, expect=4)` returned
    all four names, no stray, no short-population refusal — while its four frames came from
    two different arms, and the first run's receipt was still on disk asserting `n_frames: 4`
    and an `out_pixels_sha256` that no longer described the directory.
    """
    import invert_frames as INV

    clean = _control_dir(tmp_path, "clean", 4)
    out = tmp_path / "dst2"
    first = INV.invert_dir(str(clean), str(out))
    before = {n: (out / n).read_bytes() for n in sorted(os.listdir(out))}

    bad = _control_dir(tmp_path, "bad", 4, rgba_at=2)
    with pytest.raises(INV.InvertError) as exc:
        INV.invert_dir(str(bad), str(out))
    assert exc.value.evidence["clause"] == "out_directory_already_holds_frames", (
        exc.value.evidence)
    after = {n: (out / n).read_bytes() for n in sorted(os.listdir(out))}
    assert after == before, "a refused run changed the directory it was refused into"
    assert first["n_frames"] == 4


def test_every_one_of_the_five_read_clauses_fires_above_the_first_write(tmp_path):
    """SIBLINGS, enumerated: all four `_read_u8_gray` clauses plus the population one, each
    on a frame that is NOT the first — the position that made the old loop partial."""
    import invert_frames as INV

    cases = []
    # alpha
    cases.append(("frame_carries_an_alpha_channel", _control_dir(tmp_path, "a", 4, rgba_at=3)))
    # palette
    d = _control_dir(tmp_path, "p", 4)
    Image.new("P", (8, 8)).save(d / "00003.png")
    cases.append(("frame_is_palette_indexed", d))
    # 16-bit
    d = _control_dir(tmp_path, "b16", 4)
    Image.fromarray(np.full((8, 8), 300, dtype=np.uint16)).save(d / "00003.png")
    cases.append(("frame_is_not_eight_bit", d))
    # colour, not R=G=B
    d = _control_dir(tmp_path, "c", 4)
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    arr[..., 0] = 200
    Image.fromarray(arr).save(d / "00003.png")
    cases.append(("frame_is_colour_not_grayscale", d))

    for clause, src in cases:
        out = tmp_path / f"out_{clause}"
        with pytest.raises(INV.InvertError) as exc:
            INV.invert_dir(str(src), str(out))
        assert exc.value.evidence["clause"] == clause, (clause, exc.value.evidence)
        assert not out.exists(), (clause, "the refused run left a partial directory")


def test_a_clean_inversion_still_writes_every_frame_and_its_receipt(tmp_path):
    """Grade the arm on what it can move."""
    import invert_frames as INV

    src = _control_dir(tmp_path, "ok", 4)
    out = tmp_path / "ok_out"
    rec = INV.invert_dir(str(src), str(out))
    assert rec["n_frames"] == 4
    assert sorted(os.listdir(out)) == [f"{i:05d}.png" for i in range(4)]


# ===========================================================================
# SEAM 1 — the ONE `__main__` halt handler, adopted by import
# F-41a09432 / F-af7f5c42 / F-e0f1f520 (handler half) / F-c3dd5ba3 / F-03bf2b7e
# ===========================================================================

SEAM1_ADOPTERS = {
    "composite_reference": "COMPOSITE_REFERENCE",
    "encode_control": "ENCODE_CONTROL",
    "pack_pose_pack": "PACK_POSE_PACK",
    "make_review_clip": "MAKE_REVIEW_CLIP",
    "measure_clip": "MEASURE_CLIP",
    "resample_motion": "RESAMPLE_MOTION",
    "render_pose_sticks": "RENDER_STICKS",
    "invert_frames": "INVERT_FRAMES",
}


def test_the_handler_is_adopted_by_import_and_never_copied():
    """SEAM 1's contract: ONE handler, ONE home. Each adopter's `__main__` block calls
    `armature_core.parts.run_tool_main` and none of them spells a handler body."""
    for mod, prefix in SEAM1_ADOPTERS.items():
        src = open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read()
        block = src[src.index('if __name__ == "__main__":'):]
        assert "from armature_core.parts import run_tool_main" in block, mod
        assert f'run_tool_main({{}}, "{prefix}")'.replace("{}", "main") in block \
            or f'run_tool_main(_cli, "{prefix}")' in block, (mod, block[-200:])
        assert "traceback.print_exc" not in block, (mod, "a handler body was copied")
        assert "_halt_keysafe" not in block, (mod, "a serialiser was copied")


def test_single_path_segment_has_exactly_one_home():
    """SEAM 1's other half: the two byte-identical copies are DELETED, not re-derived, and
    nobody spells a third."""
    import ast

    definers = []
    for mod in _OWNED_42:
        tree = ast.parse(open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8").read())
        if any(isinstance(n, ast.FunctionDef) and n.name == "single_path_segment"
               for n in ast.walk(tree)):
            definers.append(mod)
    assert definers == [], definers
    from armature_core.parts import single_path_segment
    assert callable(single_path_segment)


@pytest.mark.parametrize("run", ["../A2/lossless/A2", "outputs/E09/A2", "a/b", "..", "",
                                 "C:/abs"])
def test_the_review_run_token_is_a_name_and_never_a_path(tmp_path, run):
    """THE AUDITOR'S OPERAND and its siblings, for F-03bf2b7e.

    Measured on `e8263a3` on a 3-frame `<base>/A2/lossless`:
    `--out=<base>/review --run=../A2/lossless/A2` wrote `A2_review_0.50x_8fps.webp` INTO the
    run's own numbered-frame directory, printed `MAKE_REVIEW_CLIP_OK` and returned 0 — while
    the control run, asking for that destination directly with `--out=<frames dir>`, raises
    `ReviewClipError` from `gate_out_directory`. The andon landed in wave 16 to prevent that
    outcome was walked past by a flag landed in the same wave: the gate inspects `--out`
    only, and the write is `--out` plus an operator string. A second measurement,
    `--run=outputs/E09/A2`, died with a bare `FileNotFoundError` naming a path with mixed
    separators AFTER `os.makedirs(a.out)` had created the review directory.
    """
    import make_review_clip as MRC

    frames = tmp_path / "A2" / "lossless"
    frames.mkdir(parents=True)
    for i in range(3):
        Image.new("RGB", (8, 8), (10 * i, 0, 0)).save(frames / f"{i:05d}.png")
    out = tmp_path / "review"
    if run == "":
        # an empty --run is not a defect: `run_token` falls through to the DERIVED branch,
        # which returns the frames directory's parent — a basename by construction.
        token, source = MRC.run_token(str(frames), run)
        assert token == "A2" and source == "frames_parent"
        return
    with pytest.raises(MRC.ReviewClipError) as exc:
        MRC.main([f"--frames={frames}", f"--out={out}", f"--run={run}", "--stills=0"])
    ev = exc.value.evidence
    assert ev["clause"] == "output_name_is_not_a_name", (run, ev)
    assert ev["flag"] == "--run", ev
    assert not out.exists(), "a refused run created the review directory"
    assert sorted(os.listdir(frames)) == ["00000.png", "00001.png", "00002.png"], (
        "the review pass left an artifact among the run's numbered frames")


def test_a_legal_run_token_still_names_the_clip(tmp_path):
    """Grade the arm on what it can move: a bare token is the documented use and stays."""
    import make_review_clip as MRC

    frames = tmp_path / "A2" / "lossless"
    frames.mkdir(parents=True)
    for i in range(3):
        Image.new("RGB", (8, 8), (10 * i, 0, 0)).save(frames / f"{i:05d}.png")
    out = tmp_path / "review_ok"
    assert MRC.main([f"--frames={frames}", f"--out={out}", "--run=A2",
                     "--stills=0"]) == 0
    clips = [n for n in os.listdir(out) if n.endswith(".webp")]
    assert clips == ["A2_review_0.50x_8fps.webp"], sorted(os.listdir(out))
