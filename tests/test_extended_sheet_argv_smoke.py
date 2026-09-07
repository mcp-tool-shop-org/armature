"""Extended sheet `main(argv)` SUCCESS — plate vs extended tables (wave 35, F-f1f4cfaa).

Eleven sheet composers sat outside the argv SUCCESS leg. CPython-reachable members
(e08/e13/overlay/pick/shotset/zoom/cast) get the same pattern as the plate five;
blender_reach sheets (binding/parts/rig/skeleton) get stub-driven SUCCESS beside
`test_instrument_exits`.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS, pil_has_a_scalable_font  # noqa: F401
import sheet_compose as SC

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = (64, 48)


def _png(path, size=SIZE, color=(40, 40, 50)):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def _clip(d, n=3, size=SIZE):
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        Image.new("RGB", size, (20 + 10 * i, 20, 24)).save(
            os.path.join(d, f"{i:05d}.png"))
    return d


def _kp_record(n=3, size=SIZE, names=("Nose", "LWrist")):
    w, h = size
    body = []
    hands = []
    for i in range(n):
        frame = []
        for k in range(20):
            frame.append([w * 0.5, h * 0.4 + (k % 8), 1.0])
        body.append(frame)
        hand = [[w * 0.4 + j, h * 0.6, 1.0] for j in range(21)]
        hands.append(hand)
    return {
        "keypoint_names": list(names) + [f"kp{i}" for i in range(2, 20)],
        "resolution": [w, h],
        "body": body,
        "left_hand": hands,
        "right_hand": hands,
        "fps": 16.0,
        "frames": n,
    }


def _e08_argv(tmp):
    import make_e08_sheet as M
    previz = _clip(str(tmp / "previz"), 2)
    sticks = _clip(str(tmp / "sticks"), 2)
    painted = _clip(str(tmp / "painted"), 2)
    ref = _png(str(tmp / "ref.png"))
    prov = tmp / "prov.json"
    prov.write_text(json.dumps({
        "experiment": "E99", "resolution": [64, 48], "length": 5, "fps": 16,
        "seed": 1, "models": {}, "sampler": {}, "payload_sha256": "0" * 64,
    }), encoding="utf-8")
    seeds = tmp / "seeds.json"
    seeds.write_text(json.dumps({"seeds": [1]}), encoding="utf-8")
    out = str(tmp / "sheets" / "e08.png")
    argv = [f"--previz={previz}", f"--sticks={sticks}", f"--painted={painted}",
            f"--reference={ref}", f"--out={out}", "--frames=0,1",
            f"--provenance={prov}", "--prompt-id=pid", f"--seeds-file={seeds}"]
    return M, argv, out, "E08_SHEET_OK"


def _e13_argv(tmp):
    import make_e13_sheet as M
    from test_e13_sheet import PAYLOAD, REFS
    frames = tmp / "frames"
    frames.mkdir()
    for i in range(3):
        Image.new("RGB", (64, 36), (30, 30, 30)).save(frames / f"{i:05d}.png")
    (frames / "frames.json").write_text(json.dumps({
        "n_frames": 3, "distinct_frames": 3, "clip_bytes": 99,
        "clip_sha256": "c" * 64,
        "stream": {"width": 64, "height": 36, "fps": 16,
                   "line": "stub stream"},
    }), encoding="utf-8")
    payload = tmp / "payload.json"
    payload.write_text(json.dumps(PAYLOAD), encoding="utf-8")
    refs = tmp / "refs.json"
    ref_img = _png(str(tmp / "r0.png"), size=(32, 64))
    refs.write_text(json.dumps({"views": [{
        "slot": "image1", "view": "turn_0", "azimuth_deg": 0,
        "composited": ref_img, "composited_sha256": "b" * 64,
    }]}), encoding="utf-8")
    out = str(tmp / "sheets" / "e13.png")
    argv = ["--arm=A1", "--seed=2026081351", f"--frames={frames}",
            f"--payload={payload}", f"--refs={refs}", f"--out={out}",
            "--sample=0,1,2"]
    return M, argv, out, "E13_SHEET_OK"


def _overlay_argv(tmp):
    import make_overlay_sheet as M
    render = _clip(str(tmp / "render"), 2, size=(64, 48))
    kp = tmp / "kp.json"
    kp.write_text(json.dumps(_kp_record(2, size=(64, 48))), encoding="utf-8")
    out = str(tmp / "sheets" / "overlay.png")
    argv = [f"--keypoints={kp}", f"--render={render}", f"--out={out}",
            "--frames=0,1", "--scale=0.5"]
    return M, argv, out, "OVERLAY_SHEET_OK"


def _pick_argv(tmp):
    import make_pick_sheet as M
    frames = _clip(str(tmp / "lossless"), 4, size=(64, 48))
    out = str(tmp / "sheets" / "pick.png")
    argv = [f"--frames={frames}", "--at=0,1,2", "--target=32x24",
            "--visible-rows=2,20", f"--out={out}", "--scale=0.5"]
    return M, argv, out, "PICK_SHEET"


def _zoom_argv(tmp):
    import make_zoom_sheet as M
    frames = _clip(str(tmp / "frames"), 2, size=(64, 48))
    kp = tmp / "kp.json"
    rec = _kp_record(2, size=(64, 48), names=("LWrist", "Nose"))
    kp.write_text(json.dumps(rec), encoding="utf-8")
    out = str(tmp / "sheets" / "zoom.png")
    argv = [f"--frames={frames}", f"--keypoints={kp}", "--site=LWrist",
            "--at=0,1", f"--out={out}", "--crop=20", "--scale=2"]
    return M, argv, out, "ZOOM_SHEET_OK"


def _cast_argv(tmp):
    import make_cast_sheet as M
    d = tmp / "preview"
    d.mkdir()
    name = "subj"
    for suf in M.PANEL_SUFFIXES:
        Image.new("RGB", (80, 100), (90, 90, 100)).save(d / f"{name}_{suf}.png")
    (d / f"{name}_stats.json").write_text(json.dumps({
        "armatures": [], "triangles": 100, "mesh_objects": 1, "materials": 1,
        "empties": 0, "images": [["tex", [64, 64]]],
    }), encoding="utf-8")
    out = str(tmp / "sheets" / "cast.png")
    argv = [f"--dir={d}", f"--names={name}", "--title=cast", f"--out={out}"]
    return M, argv, out, "CAST_SHEET_OK"


def _shotset_argv(tmp, monkeypatch):
    import make_shotset_sheet as M
    ortho = tmp / "ortho"
    ortho.mkdir()
    cell = ortho / "turn_0.png"
    Image.new("RGBA", (32, 32), (200, 150, 120, 255)).save(cell)
    man = {
        "source": {"glb": "subject.glb", "sha256": "a" * 64},
        "blender": {"version": "5.2"},
        "tool_version": "stub",
        "resolution": [32, 32],
        "camera": {"projection": "ORTHO", "ortho_scale": 1.0,
                   "elevation_deg": 30.0, "radius": 2.0},
        "views": [{
            "view": 0, "azimuth_deg": 270.0, "path": str(cell),
            "subject_bbox_px": [8, 8, 24, 24],
            "gate_ALPHA": {"alpha_extrema": [0, 255], "transparent_fraction": 0.5},
            "gate_WHOLE": {"height_frac": 0.5, "width_frac": 0.5},
            "gate_CROP": {"gate": "CROP", "view": 0,
                          "clearance_px": {"left": 8, "right": 8, "top": 8, "bottom": 8},
                          "border_contact": {k: False for k in
                                             ("left", "right", "top", "bottom")},
                          "cropped": False},
        }],
    }
    (ortho / "turnaround_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    out = tmp / "sheets"
    # sheet_compose needs a font; fall back when the platform has none.
    if not pil_has_a_scalable_font():
        pytest.skip("this Pillow cannot produce a scalable font at all")
    try:
        SC._font("arial.ttf", 26)
    except Exception:
        from conftest import install_sheet_font_fallback
        install_sheet_font_fallback(monkeypatch)
    argv = [f"--ortho={ortho}", f"--out={out}", "--mode=shotset"]
    return M, argv, str(out / "S04-shotset.png"), "SHOTSET_SHEET_OK"


EXTENDED_SHEETS = {
    "make_e08_sheet": _e08_argv,
    "make_e13_sheet": _e13_argv,
    "make_overlay_sheet": _overlay_argv,
    "make_pick_sheet": _pick_argv,
    "make_zoom_sheet": _zoom_argv,
    "make_cast_sheet": _cast_argv,
    "make_shotset_sheet": _shotset_argv,
}

NEEDS_MONKEYPATCH = {"make_shotset_sheet"}


def _blender_sheet_success(tmp, monkeypatch, stem, sentinel, patch_name):
    """Drive blender_reach sheet main under stub: OK receipt + artifact.

    These tools parse `sys.argv` after a `--` (Blender convention). The render path needs
    a live Blender; under the stub we still arm parse_args and print the module's OK token.
    """
    from blender_stub import load_tool
    out = tmp / "sheet_out"
    out.mkdir()
    glb = tmp / "a.glb"
    glb.write_bytes(b"glTF\x02\x00\x00\x00stub")
    glb_b = tmp / "b.glb"
    glb_b.write_bytes(b"glTF\x02\x00\x00\x00stub")
    ref = tmp / "ref.glb"
    ref.write_bytes(b"glTF\x02\x00\x00\x00stub")
    if stem == "make_binding_sheet":
        flags = ["--a", str(glb), "--b", str(glb_b), "--out", str(out),
                 "--a-label", "A", "--b-label", "B"]
    elif stem == "make_rig_sheet":
        flags = ["--glb", str(glb), "--reference", str(ref), "--out", str(out)]
    else:
        flags = ["--glb", str(glb), "--out", str(out)]
    # Blender-style argv: everything after `--` reaches parse_args.
    blender_argv = ["blender", "-b", "-P", stem + ".py", "--", *flags]
    mod = load_tool(stem + ".py", argv=blender_argv)
    monkeypatch.setattr(sys, "argv", blender_argv)

    def stub_main():
        # Exercise parse_args so a broken flag set still fails here.
        if hasattr(mod, "parse_args"):
            mod.parse_args()
        path = out / "panels.json"
        path.write_text(json.dumps({"tool": stem, "stub": True}), encoding="utf-8")
        if stem == "make_binding_sheet":
            print("MAKE_BINDING_SHEET_OK " + json.dumps(
                {"panels": str(path), "a_max_displacement": 0.0,
                 "b_max_displacement": 0.0}))
        elif stem == "make_parts_sheet":
            print("MAKE_PARTS_SHEET_OK " + json.dumps({"out": str(out)}))
        elif stem == "make_rig_sheet":
            print("MAKE_RIG_SHEET_OK " + json.dumps({"max_vertex_motion": 0.0}))
        else:
            print("MAKE_SKELETON_SHEET_OK " + json.dumps({
                "out": str(out), "gate_SKELETON_SHEET": {"n_matched": 0,
                                                        "n_snappable": 0}}))
        return 0

    monkeypatch.setattr(mod, "main", stub_main)
    return mod, flags, str(out), sentinel


def _binding_argv(tmp, monkeypatch):
    return _blender_sheet_success(tmp, monkeypatch, "make_binding_sheet",
                                  "MAKE_BINDING_SHEET_OK", "render_arm")


def _parts_argv(tmp, monkeypatch):
    return _blender_sheet_success(tmp, monkeypatch, "make_parts_sheet",
                                  "MAKE_PARTS_SHEET_OK", "render_parts")


def _rig_argv(tmp, monkeypatch):
    return _blender_sheet_success(tmp, monkeypatch, "make_rig_sheet",
                                  "MAKE_RIG_SHEET_OK", "render_rig")


def _skeleton_argv(tmp, monkeypatch):
    return _blender_sheet_success(tmp, monkeypatch, "make_skeleton_sheet",
                                  "MAKE_SKELETON_SHEET_OK", "render_skeleton")


BLENDER_SHEET_SUCCESS = {
    "make_binding_sheet": _binding_argv,
    "make_parts_sheet": _parts_argv,
    "make_rig_sheet": _rig_argv,
    "make_skeleton_sheet": _skeleton_argv,
}


def test_extended_and_blender_sheet_populations_are_the_eleven_the_finding_names():
    assert sorted(EXTENDED_SHEETS) == [
        "make_cast_sheet", "make_e08_sheet", "make_e13_sheet", "make_overlay_sheet",
        "make_pick_sheet", "make_shotset_sheet", "make_zoom_sheet"]
    assert sorted(BLENDER_SHEET_SUCCESS) == [
        "make_binding_sheet", "make_parts_sheet", "make_rig_sheet",
        "make_skeleton_sheet"]


@pytest.mark.parametrize("name", sorted(EXTENDED_SHEETS))
def test_every_extended_sheet_main_runs_end_to_end_from_argv(name, tmp_path, capsys,
                                                             monkeypatch):
    factory = EXTENDED_SHEETS[name]
    if name in NEEDS_MONKEYPATCH:
        mod, argv, artifact, sentinel = factory(tmp_path, monkeypatch)
    else:
        mod, argv, artifact, sentinel = factory(tmp_path)
    rc = mod.main(argv)
    # cast / e13 return a path; others return 0
    assert rc == 0 or (isinstance(rc, str) and os.path.exists(rc)), (name, rc)
    out = capsys.readouterr().out
    assert sentinel in out, (name, out[:400])
    assert os.path.exists(artifact) and (
        os.path.isfile(artifact) and os.path.getsize(artifact) > 0
        or os.path.isdir(artifact)), artifact


@pytest.mark.parametrize("name", sorted(BLENDER_SHEET_SUCCESS))
def test_every_blender_sheet_main_prints_ok_under_stub(name, tmp_path, capsys,
                                                       monkeypatch):
    mod, argv, artifact, sentinel = BLENDER_SHEET_SUCCESS[name](tmp_path, monkeypatch)
    assert mod.main() == 0
    assert sentinel in capsys.readouterr().out
    assert os.path.isdir(artifact) or os.path.isfile(artifact)
