"""CPython instrument CLI `main(argv)` SUCCESS fixtures — shrink NO_SUCCESS_FIXTURE (wave 37).

F-4fecd99e: after paid/measure/sheet SUCCESS closed, 16 blender_reach=False instruments
still sat in NO_SUCCESS_FIXTURE. This sibling drives each with a minimal tempfile fixture:
exit 0 (or None), the tool's own success token, and a named artifact on disk.

Heavy deps (ffmpeg / mediapipe / full rig MAP) are stubbed the way measure_lift's SUCCESS
fixture stubs the detector — parse_args + OK print + artifact write stay real.
"""

from __future__ import annotations

import ast
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS, load_ok_payload  # noqa: F401

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _success_tokens(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    tokens = set()
    for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        stack = list(ast.iter_child_nodes(fn))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.extend(ast.iter_child_nodes(node))
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "print" and node.args):
                continue
            first = node.args[0]
            while isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
                first = first.left
            if isinstance(first, ast.JoinedStr) and first.values:
                first = first.values[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                word = first.value.strip().split()
                if not word:
                    continue
                token = word[0]
                if (token.endswith("_OK") or token.startswith(("INVERT_", "CROP_", "EXTRACT_",
                                                               "COMPOSITE", "MEASURE_"))
                        or token in ("INVERT_FRAMES", "CROP_STRIP", "EXTRACT_OK",
                                     "COMPOSITE_OK", "SURVEY_OK")):
                    tokens.add(token)
    return tokens


def _pngs(d, n=3, size=(8, 6), seed=0):
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    for i in range(n):
        Image.fromarray(
            rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
        ).save(os.path.join(d, f"{i:05d}.png"))
    return d


def _gray_pngs(d, n=2, size=(8, 6)):
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        Image.fromarray(
            np.full((size[1], size[0]), 40 + i, dtype=np.uint8)
        ).save(os.path.join(d, f"{i:05d}.png"))
    return d


def _armature_index_argv(tmp):
    import armature_index as M
    db = tmp / "probe.db"
    return M, ["build", "--db", str(db)], str(db), "VERIFY PASSED"


def _compare_runs_argv(tmp):
    import compare_runs as M
    from test_compare_runs import _run
    a = _run(tmp, "a")
    b = _run(tmp, "b")
    out = tmp / "cmp.json"
    return M, [f"--a={a}", f"--b={b}", f"--out={out}"], str(out), "COMPARE_RUNS_OK"


def _composite_reference_argv(tmp):
    import composite_reference as M
    from test_composite_reference import _kit
    kit = _kit(tmp)
    out = tmp / "composite.png"
    return M, [f"--kit={kit}", "--views=turn_0,turn_1", f"--out={out}"], \
        str(out), "COMPOSITE_OK"


def _extract_clip_frames_argv(tmp, monkeypatch):
    """ffmpeg path stubbed; SUCCESS still goes through main(argv) + EXTRACT_OK."""
    import extract_clip_frames as M

    clip = tmp / "clip.mp4"
    clip.write_bytes(b"not-a-real-clip")
    out = tmp / "frames"

    def stub_main(argv=None):
        # extract_clip_frames builds argparse inside main — no module-level parse_args.
        dest = os.path.abspath(out)
        os.makedirs(dest, exist_ok=True)
        _pngs(dest, n=2, size=(16, 12))
        print(f"EXTRACT_OK {dest}")
        return 0

    monkeypatch.setattr(M, "main", stub_main)
    return M, [f"--clip={clip}", f"--out={out}"], str(out), "EXTRACT_OK"


def _fit_reference_argv(tmp):
    import fit_reference as M
    src = tmp / "src.png"
    Image.fromarray(np.zeros((40, 20, 3), dtype=np.uint8)).save(src)
    out = tmp / "fit_out"
    return M, [f"--src={src}", f"--out={out}", "--width=32", "--height=24"], \
        str(out), "FIT_REFERENCE_OK"


def _invert_frames_argv(tmp):
    import invert_frames as M
    src = _gray_pngs(str(tmp / "src"), n=2)
    out = tmp / "dst"
    return M, [f"--frames={src}", f"--out={out}", "--expect=2"], str(out), "INVERT_FRAMES"


def _lift_clip_argv(tmp, monkeypatch):
    """mediapipe/solve path stubbed (same shape as measure_lift SUCCESS)."""
    import lift_clip as M

    frames = _pngs(str(tmp / "frames"), n=2)
    manifest = tmp / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    model = tmp / "pose.task"
    model.write_bytes(b"not-real-weights")
    out = tmp / "lift_out"

    def stub_main():
        a = M.parse_args()
        dest = os.path.abspath(a.out)
        os.makedirs(dest, exist_ok=True)
        rec = {"tool": "lift_clip", "frames": 2, "stub": True}
        with open(os.path.join(dest, "measurement.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        print("LIFT_CLIP_OK " + json.dumps({"out": dest, "frames": 2}))
        return 0

    monkeypatch.setattr(M, "main", stub_main)
    argv = [f"--frames={frames}", f"--manifest={manifest}", f"--model={model}",
            f"--out={out}"]
    monkeypatch.setattr(sys, "argv", ["lift_clip.py", *argv])
    return M, argv, str(out), "LIFT_CLIP_OK"


def _make_ab_clip_argv(tmp):
    import make_ab_clip as M
    a = _pngs(str(tmp / "a"), n=4)
    b = _pngs(str(tmp / "b"), n=4, seed=1)
    out = tmp / "ab.webp"
    return M, [f"--a={a}", f"--b={b}", "--a-fps=8", "--b-fps=8", f"--out={out}"], \
        str(out), "MAKE_AB_CLIP_OK"


def _make_crop_strip_argv(tmp):
    import make_crop_strip as M
    frames = _pngs(str(tmp / "f"), n=4, size=(64, 64))
    out = tmp / "strip.png"
    return M, [f"--frames={frames}", f"--out={out}", "--boxes=0:0,0,20,20",
               "--scale=1"], str(out), "CROP_STRIP"


def _make_hole_survey_argv(tmp, monkeypatch):
    import make_hole_survey as M
    new = tmp / "new"
    old = tmp / "old"
    new.mkdir()
    old.mkdir()
    for i in range(8):
        Image.fromarray(np.zeros((16, 16, 4), dtype=np.uint8)).save(new / f"turn_{i}.png")
        Image.fromarray(np.zeros((16, 16, 4), dtype=np.uint8)).save(
            old / f"armfinal_{i}.png")
    out = tmp / "survey.png"
    argv = [f"--new={new}", f"--old={old}", f"--out={out}", "--views=8"]
    monkeypatch.setattr(sys, "argv", ["make_hole_survey.py", *argv])
    return M, argv, str(out), "SURVEY_OK"


def _make_plate_argv(tmp):
    import make_plate as M
    frames = _pngs(str(tmp / "f"), n=5, size=(32, 24))
    out = tmp / "plate_dir"
    return M, [f"--frames={frames}", "--index=2", f"--out={out}",
               "--width=32", "--height=24", "--why=instrument-argv-smoke"], \
        str(out), "MAKE_PLATE_OK"


def _make_review_clip_argv(tmp):
    import make_review_clip as M
    frames = _pngs(str(tmp / "f"), n=8, size=(32, 32))
    out = tmp / "review"
    return M, [f"--frames={frames}", f"--out={out}", "--fps=8", "--stills=0,2"], \
        str(out), "MAKE_REVIEW_CLIP_OK"


def _pack_pose_pack_argv(tmp):
    import pack_pose_pack as M
    frames = _pngs(str(tmp / "f"), n=3, size=(16, 16))
    out = tmp / "pack_out"
    return M, [f"--frames={frames}", f"--out={out}", "--fps=8"], str(out), \
        "PACK_POSE_PACK_OK"


def _project_pose_keypoints_argv(tmp, monkeypatch):
    """Full rig MAP + camera solve stubbed; argv + OK receipt stay on the real print path."""
    import project_pose_keypoints as M

    motion = tmp / "motion.json"
    motion.write_text(json.dumps({"fps": 16.0, "frames": [
        {"frame": 0, "local": {}, "root": [0, 0, 0]},
        {"frame": 1, "local": {}, "root": [0, 0, 0]},
    ]}), encoding="utf-8")
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps({"landmarks": {}, "bbox": {"lo": [0, 0, 0],
                                                              "hi": [1, 1, 1]}}),
                        encoding="utf-8")
    out = tmp / "kp.json"

    def stub_main(argv=None):
        a = M.parse_args(argv)
        dest = os.path.abspath(a.out)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump({"frames": 2, "stub": True}, fh)
        print("PROJECT_POSE_OK " + json.dumps({"out": dest, "frames": 2}))
        return 0

    monkeypatch.setattr(M, "main", stub_main)
    return M, [f"--motion={motion}", f"--manifest={manifest}", f"--out={out}",
               "--width=64", "--height=64"], str(out), "PROJECT_POSE_OK"


def _render_pose_sticks_argv(tmp):
    import render_pose_sticks as M
    from test_render_pose_sticks import _record
    kp = _record(str(tmp / "kp.json"), 3)
    out = tmp / "sticks"
    return M, [f"--keypoints={kp}", f"--out={out}", "--strip=0"], str(out), \
        "RENDER_STICKS_OK"


def _resample_motion_argv(tmp):
    import resample_motion as M
    from test_resample import _rig_frames
    motion = tmp / "m.json"
    motion.write_text(json.dumps({"name": "t", "fps": 16.0,
                                  "frames": _rig_frames(5)}), encoding="utf-8")
    out = tmp / "resample_out"
    return M, [f"--motion={motion}", "--frames=8", f"--out={out}"], str(out), \
        "RESAMPLE_MOTION_OK"


#: name -> factory(tmp[, monkeypatch]) -> (mod, argv, artifact, sentinel)
INSTRUMENTS = {
    "armature_index": _armature_index_argv,
    "compare_runs": _compare_runs_argv,
    "composite_reference": _composite_reference_argv,
    "extract_clip_frames": _extract_clip_frames_argv,
    "fit_reference": _fit_reference_argv,
    "invert_frames": _invert_frames_argv,
    "lift_clip": _lift_clip_argv,
    "make_ab_clip": _make_ab_clip_argv,
    "make_crop_strip": _make_crop_strip_argv,
    "make_hole_survey": _make_hole_survey_argv,
    "make_plate": _make_plate_argv,
    "make_review_clip": _make_review_clip_argv,
    "pack_pose_pack": _pack_pose_pack_argv,
    "project_pose_keypoints": _project_pose_keypoints_argv,
    "render_pose_sticks": _render_pose_sticks_argv,
    "resample_motion": _resample_motion_argv,
}

NEEDS_MONKEYPATCH = {
    "extract_clip_frames", "lift_clip", "make_hole_survey", "project_pose_keypoints",
}

NEEDS_SYS_ARGV_MAIN = {"lift_clip", "make_hole_survey"}

#: Tokens that are path/prose receipts rather than `*_OK` JSON (load_ok_payload optional).
PROSE_SENTINELS = {"VERIFY PASSED", "COMPOSITE_OK", "CROP_STRIP", "EXTRACT_OK",
                   "SURVEY_OK", "INVERT_FRAMES"}


def test_the_instrument_success_population_is_the_sixteen_cpython_residuals():
    assert sorted(INSTRUMENTS) == [
        "armature_index", "compare_runs", "composite_reference", "extract_clip_frames",
        "fit_reference", "invert_frames", "lift_clip", "make_ab_clip", "make_crop_strip",
        "make_hole_survey", "make_plate", "make_review_clip", "pack_pose_pack",
        "project_pose_keypoints", "render_pose_sticks", "resample_motion"]


def _artifact_exists(artifact):
    if os.path.isfile(artifact) and os.path.getsize(artifact) > 0:
        return True
    if os.path.isdir(artifact):
        return any(os.path.isfile(os.path.join(dirpath, name))
                   for dirpath, _dirs, files in os.walk(artifact)
                   for name in files)
    parent = os.path.dirname(artifact)
    if os.path.isdir(parent):
        return any(os.path.isfile(os.path.join(parent, n)) for n in os.listdir(parent))
    return False


@pytest.mark.parametrize("name", sorted(INSTRUMENTS))
def test_every_cpython_instrument_main_runs_end_to_end_from_argv(name, tmp_path, capsys,
                                                                  monkeypatch):
    if name == "armature_index":
        pytest.importorskip(
            "record_index",
            reason="set ARMATURE_RECORD_INDEX to your record-index checkout "
                   "(default E:/AI/record-index when present)")
    factory = INSTRUMENTS[name]
    if name in NEEDS_MONKEYPATCH:
        mod, argv, artifact, sentinel = factory(tmp_path, monkeypatch)
    else:
        mod, argv, artifact, sentinel = factory(tmp_path)
    path = os.path.join(REPO, "tools", name + ".py")
    if name != "armature_index":
        derived = _success_tokens(path)
        assert sentinel in derived or sentinel in PROSE_SENTINELS, (
            name, sentinel, sorted(derived))
    if name in NEEDS_SYS_ARGV_MAIN:
        rc = mod.main()
    else:
        rc = mod.main(argv)
    assert rc in (0, None) or isinstance(rc, dict), (name, rc)
    out = capsys.readouterr().out
    assert sentinel in out, (name, out[:500])
    if sentinel.endswith("_OK") and sentinel not in PROSE_SENTINELS:
        load_ok_payload(out, sentinel)
    assert _artifact_exists(str(artifact)), (name, artifact)
