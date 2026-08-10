"""Tests that drive the real `run_export` write path with a synthetic backend."""

import json
import os

import numpy as np
import pytest
from PIL import Image

import stage_render
from armature_core import pngio
from armature_core.errors import (
    ArmatureError,
    G1GeneratorLegality,
    G2Completeness,
    G4BboxSanity,
    NotInsideBlender,
)
from fake_backend import FakeBackend, make_spec


def test_export_writes_every_channel(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    manifest = stage_render.run_export(
        spec, str(out), backend=FakeBackend(64, 96, breathe=0.8)
    )

    for d in ("mask", "normal", "edge", "depth_perframe", "depth_pershot", "p3_diff"):
        files = sorted(os.listdir(out / d))
        assert len(files) == 9, d
        assert files[0] == "00000.png" and files[-1] == "00008.png"
    assert (out / "manifest.json").is_file()
    assert (out / "spec.json").is_file()
    assert manifest["gates"]["G1"]["verdict"] == "PASS"
    assert manifest["gates"]["G5"]["verdict"].startswith("NOT RUN")
    assert len(manifest["sha256"]["mask"]) == 9


def test_g1_fires_before_the_backend_is_touched(tmp_path):
    """The backend must never be prepared for an illegal frame."""
    spec = make_spec(tmp_path, width=1020)
    backend = FakeBackend(1020, 96)
    with pytest.raises(G1GeneratorLegality):
        stage_render.run_export(spec, str(tmp_path / "run"), backend=backend)
    assert backend.prepared is False
    assert not (tmp_path / "run").exists()


def test_g1_fires_before_blender_is_needed(tmp_path):
    """Outside Blender a legal spec raises NotInsideBlender, an illegal one raises G1.
    The two outcomes are distinguishable, which is what proves the ordering."""
    illegal = make_spec(tmp_path, count=80)
    with pytest.raises(G1GeneratorLegality):
        stage_render.run_export(illegal, str(tmp_path / "a"))

    legal = make_spec(tmp_path)
    with pytest.raises(NotInsideBlender):
        stage_render.run_export(legal, str(tmp_path / "b"))
    assert not (tmp_path / "b").exists()


def test_g4_fires_on_a_mask_that_disagrees_with_the_mesh(tmp_path):
    spec = make_spec(tmp_path)
    with pytest.raises(G4BboxSanity) as exc:
        stage_render.run_export(
            spec, str(tmp_path / "run"), backend=FakeBackend(64, 96, lie_about_bbox=True)
        )
    assert exc.value.evidence["frame"] == 0


def test_g2_fires_before_the_manifest_is_written(tmp_path, monkeypatch):
    """Drop one frame on the floor mid-run. A partial export must never look like a
    finished one, so `manifest.json` must not exist afterwards."""
    spec = make_spec(tmp_path)
    out = tmp_path / "run"

    real = pngio.write_png
    state = {"n": 0}

    def flaky(path, arr, bit_depth=8):
        if os.path.basename(path) == "00004.png" and os.path.basename(os.path.dirname(path)) == "edge":
            state["n"] += 1
            return 0
        return real(path, arr, bit_depth)

    monkeypatch.setattr(stage_render.pngio, "write_png", flaky)

    with pytest.raises(G2Completeness) as exc:
        stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    assert state["n"] == 1
    assert "edge" in str(exc.value)
    assert not (out / "manifest.json").exists(), "the manifest was written despite G2"
    assert (out / "mask" / "00004.png").exists(), "other channels did write; only edge was dropped"


def test_pose_is_refused_because_its_convention_is_not_retrieved(tmp_path):
    spec = make_spec(tmp_path, channels=("mask", "pose"))
    with pytest.raises(ArmatureError) as exc:
        stage_render.run_export(spec, str(tmp_path / "run"), backend=FakeBackend(64, 96))
    assert "not fully retrieved" in str(exc.value)
    assert not (tmp_path / "run").exists()


def test_depth_direction_near_is_bright(tmp_path):
    """The test that would catch an inverted depth ramp — invisible by eye on a
    complex mesh and fatal downstream. The fake subject ramps near (left) to far
    (right) by construction."""
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))

    img = np.array(Image.open(out / "depth_perframe" / "00000.png"))
    row = img[55]  # inside the box (rows 20..90); the ramp spans columns 10..60
    near_px, far_px = int(row[10]), int(row[60])
    assert near_px > far_px, f"near {near_px} should be brighter than far {far_px}"
    assert near_px == 255 and far_px == 0
    assert list(row[10:61]) == sorted(row[10:61], reverse=True), "the ramp is monotonic"


def test_mask_is_exactly_one_bit(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    img = Image.open(out / "mask" / "00000.png")
    assert img.mode == "1"
    arr = np.array(img)
    assert set(np.unique(arr).tolist()) <= {False, True}
    ys, xs = np.nonzero(arr)
    assert (xs.min(), ys.min(), xs.max(), ys.max()) == (10, 20, 60, 90)


def test_normal_encodes_a_camera_facing_surface_as_128_128_255(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    arr = np.array(Image.open(out / "normal" / "00000.png"))
    assert tuple(int(v) for v in arr[55, 30]) == (128, 128, 255)
    assert tuple(int(v) for v in arr[2, 2]) == (0, 0, 0)  # background


def test_p3_reports_both_normalizations_and_chooses_neither(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    manifest = stage_render.run_export(
        spec, str(out), backend=FakeBackend(64, 96, breathe=1.0)
    )
    p3 = json.loads((out / "p3_normalization.json").read_text())
    assert p3["pixel_weighted_mean_abs"] > 0
    assert manifest["p3"]["z_range_swing"] > 1.0
    assert (out / "depth_perframe").is_dir() and (out / "depth_pershot").is_dir()
    assert not (out / "depth").exists(), "a canonical `depth/` would be choosing"


def test_compensator_refuses_a_directory_it_did_not_create(tmp_path):
    foreign = tmp_path / "not_ours"
    foreign.mkdir()
    (foreign / "precious.txt").write_text("hi")
    with pytest.raises(ArmatureError):
        stage_render.delete_output_dir(str(foreign))
    assert (foreign / "precious.txt").exists()


def test_compensator_removes_a_run_it_did_create(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    assert stage_render.delete_output_dir(str(out)) is True
    assert not out.exists()
