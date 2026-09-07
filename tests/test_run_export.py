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
    with pytest.raises(G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-vace'"):
        stage_render.run_export(spec, str(tmp_path / "run"), backend=backend)
    assert backend.prepared is False
    assert not (tmp_path / "run").exists()


def test_g1_fires_before_blender_is_needed(tmp_path):
    """Outside Blender a legal spec raises NotInsideBlender, an illegal one raises G1.
    The two outcomes are distinguishable, which is what proves the ordering."""
    illegal = make_spec(tmp_path, count=80)
    with pytest.raises(G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-vace': frame"):
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
    """WAVE 34 pin-fix: OpenPose-18 PALETTE/names ARE retrieved, so the convention
    door no longer refuses `pose`. This tool still does not emit pose frames, so G2
    fires on an empty pose channel after the run directory exists.
    """
    from armature_core import openpose

    assert openpose.require_drawing_convention() is True
    spec = make_spec(tmp_path, channels=("mask", "pose"))
    out = tmp_path / "run"
    with pytest.raises(G2Completeness) as exc:
        stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    assert "not fully retrieved" not in str(exc.value)
    assert "pose" in str(exc.value)
    assert out.exists()


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
    # far_px was 0 until F-aa0ca08b: the farthest GEOMETRY pixel encoded to the same byte
    # as the background, so the rearmost band of the silhouette dissolved into the void.
    # Byte 0 is now reserved for "not geometry" and geometry starts one byte above it.
    assert near_px == 255 and far_px == 1
    bg = int(np.array(Image.open(out / "depth_perframe" / "00000.png"))[0, 0])
    assert bg == 0 and bg != far_px, "background and farthest geometry must differ"
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


# ------------------------------------------------------------------ the compensator pair
#
# Wave 6, F-c0f49504. This is the repo's only NAMED_COMPENSATORS pair, and both halves were
# pinned by outcome alone: a bare `pytest.raises(ArmatureError)` on one side and
# `delete_output_dir(...) is True` on the other. Measured: replacing the whole
# `.armature_run` marker clause in `stage_render.delete_output_dir` with an unrelated raise
# (`if len(os.path.basename(run_dir)) > 3: raise ArmatureError(...)`) left BOTH tests green
# — the foreign directory's name is long so the substitute fired, and the run directory is
# named `run`, three characters, so it did not and rmtree proceeded. The marker mechanism
# could be deleted outright with 2 passed, and the compensator that keeps this tool from
# removing a directory it did not make would have lost its only check.
#
# What decides is the MARKER, so that is what the fixtures below vary: the refusal has to
# name it, and a directory carrying the marker is deleted whoever wrote it.

MARKER = ".armature_run"


def test_compensator_refuses_a_directory_it_did_not_create(tmp_path):
    foreign = tmp_path / "not_ours"
    foreign.mkdir()
    (foreign / "precious.txt").write_text("hi")
    with pytest.raises(ArmatureError) as exc:
        stage_render.delete_output_dir(str(foreign))
    assert MARKER in str(exc.value), (
        "the refusal does not name the marker it refused on; any ArmatureError raised "
        "anywhere inside the call would satisfy this test")
    assert (foreign / "precious.txt").exists()


def test_compensator_removes_a_run_it_did_create(tmp_path):
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    assert (out / MARKER).is_file(), "run_export left no marker for the compensator to read"
    assert stage_render.delete_output_dir(str(out)) is True
    assert not out.exists()


def test_the_marker_is_what_decides_not_the_name_or_the_contents(tmp_path):
    """The positive half of the same clause: a directory this tool did not build, carrying
    the marker, IS deleted. Paired with the refusal above, the two fixtures differ in the
    marker and in nothing else, so a substitute clause reading the name, the depth or the
    contents cannot satisfy both."""
    adopted = tmp_path / "not_ours"
    adopted.mkdir()
    (adopted / "precious.txt").write_text("hi")
    (adopted / MARKER).write_text("{}", encoding="utf-8")
    assert stage_render.delete_output_dir(str(adopted)) is True
    assert not adopted.exists()


def test_removing_the_marker_from_a_real_run_makes_the_compensator_refuse_it(tmp_path):
    """And the negative of the same pair, on a directory the tool really did create: with
    the marker deleted the compensator refuses its own run, so what it reads is the marker
    and not authorship it has no other record of."""
    spec = make_spec(tmp_path)
    out = tmp_path / "run"
    stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))
    (out / MARKER).unlink()
    with pytest.raises(ArmatureError) as exc:
        stage_render.delete_output_dir(str(out))
    assert MARKER in str(exc.value)
    assert out.exists()


def test_a_missing_directory_is_reported_not_raised(tmp_path):
    """The third branch, never pinned: nothing to compensate is `False`, not a refusal.
    A compensator that raised here would turn a clean rollback into a halt."""
    assert stage_render.delete_output_dir(str(tmp_path / "never_existed")) is False


def test_the_marker_name_is_the_one_the_tool_writes():
    """The two constants are the same object of the same name, asserted rather than
    assumed: the fixtures above are only about the marker if this holds."""
    import ast

    src = open(stage_render.__file__, encoding="utf-8").read()
    literals = {n.value for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value.startswith(".armature")}
    assert literals == {MARKER}, (
        f"stage_render names {sorted(literals)} where these fixtures pin {MARKER!r}")


# ---------------------------------- the fake's contract against the real backend's

def _returned_keys(path, class_name):
    """The literal key set of the dict `render_frame` returns, read out of the source.

    AST rather than a live call: the real backend's `render_frame` needs Blender, an EXR
    on disk and a live depsgraph, so the only place the two contracts can be compared on
    a runner is the source.
    """
    import ast

    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == class_name):
            continue
        for fn in node.body:
            if not (isinstance(fn, ast.FunctionDef) and fn.name == "render_frame"):
                continue
            for ret in ast.walk(fn):
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Dict):
                    return {k.value for k in ret.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    raise AssertionError(f"no dict-returning render_frame on {class_name} in {path}")


def _real_backend_class():
    """The class in `stage_render` whose `render_frame` the writer actually consumes."""
    import ast

    with open(stage_render.__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    names = [n.name for n in ast.walk(tree)
             if isinstance(n, ast.ClassDef)
             and any(isinstance(f, ast.FunctionDef) and f.name == "render_frame"
                     for f in n.body)]
    assert len(names) == 1, f"expected one render_frame class in stage_render, got {names}"
    return names[0]


def test_the_fake_backend_returns_exactly_what_the_real_one_does():
    """The invariant: EVERY KEY THE WRITER READS IS SUPPLIED BY BOTH BACKENDS.

    `FakeBackend` exists so the gate tests can drive the real `run_export` without
    Blender. Nothing bound its return contract to the real backend's, and one key had
    already drifted: `master_paths` was returned by `stage_render`'s backend and not by
    the fake, and `run_export` reads it with `.get()` — so every fake-driven run wrote
    `master_paths: null` into each per-frame record and the whole suite stayed green.
    A rename or a relpath-base change on the real side would null it for every frame the
    same way, and `master_paths` is the manifest's pointer back to the source EXRs.
    """
    real = _returned_keys(stage_render.__file__, _real_backend_class())
    fake = _returned_keys(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_backend.py"),
        "FakeBackend")

    assert real, "read no keys off the real backend; the AST walk is broken, not clean"
    assert fake == real, (
        f"the two render_frame contracts have drifted — only the real backend returns "
        f"{sorted(real - fake)}, only the fake returns {sorted(fake - real)}. Every key "
        f"the writer reads with .get() must be supplied by both, or a fake-driven run "
        f"writes null where a real one writes the value and no test can tell.")


def test_every_frame_record_carries_its_master_paths(tmp_path):
    """The other half, driven through the real write path: the key has to arrive in the
    manifest non-null, per frame, not merely be present in a dict somewhere."""
    spec = make_spec(tmp_path, count=5)
    out = tmp_path / "run"
    manifest = stage_render.run_export(spec, str(out), backend=FakeBackend(64, 96))

    frames = manifest["frames"]
    assert len(frames) == 5
    for rec in frames:
        paths = rec["master_paths"]
        assert isinstance(paths, dict) and paths, (
            f"frame {rec['frame']} carries master_paths={paths!r}; the manifest's pointer "
            f"back to the source masters is the reproducibility link, and null is what a "
            f"backend that stopped supplying the key writes")
        assert set(paths) >= {"depth", "alpha"}, sorted(paths)

    on_disk = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert [r["master_paths"] for r in on_disk["frames"]] == [r["master_paths"] for r in frames]
