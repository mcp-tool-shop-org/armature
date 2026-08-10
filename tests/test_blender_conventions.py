"""The conventions, measured on a real headless Blender render.

`test_channels.py` checks the arithmetic; this checks that the arithmetic is fed the
right buffers by the real renderer. An inverted Z pass, a bottom-up image, or a normal
transform that silently did nothing would all pass the numpy tests and fail here.

Skipped (not silently passed) when Blender is not on this machine.
"""

import json
import os
import subprocess

import numpy as np
import pytest
from PIL import Image

from conftest import BLENDER, REPO

pytestmark = pytest.mark.skipif(
    not os.path.isfile(BLENDER), reason=f"Blender not found at {BLENDER}"
)

SCRIPT = os.path.join(REPO, "tests", "blender", "make_synthetic_run.py")


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    out = tmp_path_factory.mktemp("blender_conventions")
    proc = subprocess.run(
        [BLENDER, "-b", "-P", SCRIPT, "--", str(out)],
        capture_output=True, text=True, timeout=900,
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("SYNTHETIC_RUN ")]
    assert lines, f"blender produced no result\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    info = json.loads(lines[-1][len("SYNTHETIC_RUN "):])
    info["stdout"] = proc.stdout
    return info


def _img(info, channel, frame=0):
    return np.array(Image.open(os.path.join(info["run_dir"], channel, f"{frame:05d}.png")))


def test_the_run_completed_and_every_frame_landed(synthetic):
    for d in ("depth_perframe", "depth_pershot", "mask", "normal", "edge", "p3_diff"):
        files = sorted(os.listdir(os.path.join(synthetic["run_dir"], d)))
        assert len(files) == 5, f"{d}: {files}"
    assert os.path.isfile(os.path.join(synthetic["run_dir"], "manifest.json"))


def test_depth_direction_the_nearer_plane_is_brighter(synthetic):
    """The test that would catch an inverted depth ramp."""
    depth = _img(synthetic, "depth_perframe").astype(np.float64)
    mask = np.array(Image.open(os.path.join(synthetic["run_dir"], "mask", "00000.png")))
    h = depth.shape[0]
    lower = depth[h // 2 + 4 :][mask[h // 2 + 4 :]]
    upper = depth[: h // 2 - 4][mask[: h // 2 - 4]]
    assert lower.size and upper.size, "both planes must be in frame"
    assert lower.mean() > upper.mean() + 100, (
        f"NEAR plane (lower, {lower.mean():.1f}) should be much brighter than "
        f"FAR plane (upper, {upper.mean():.1f})"
    )
    assert lower.max() == 255 and upper.min() == 0


def test_vertical_orientation_row_zero_is_the_top_of_the_scene(synthetic):
    """A flip is invisible on a symmetric subject. The FAR plane is the upper one in
    world space; it must be the upper one in the file."""
    mask = np.array(Image.open(os.path.join(synthetic["run_dir"], "mask", "00000.png")))
    depth = _img(synthetic, "depth_perframe")
    rows = np.flatnonzero(mask.any(axis=1))
    top_band = depth[rows[0] : rows[0] + 4][mask[rows[0] : rows[0] + 4]]
    bottom_band = depth[rows[-1] - 3 : rows[-1] + 1][mask[rows[-1] - 3 : rows[-1] + 1]]
    assert bottom_band.mean() > top_band.mean(), (
        "the near plane sits low in world space and must sit low in the image"
    )


def test_normals_are_camera_space_not_world_space(synthetic):
    """Both planes face world +X. Camera-space encoding is (128,128,255); shipping
    world normals unchanged would encode (255,128,128)."""
    normal = _img(synthetic, "normal")
    mask = np.array(Image.open(os.path.join(synthetic["run_dir"], "mask", "00000.png")))
    lit = normal[mask]
    assert lit.size, "mask is empty"
    mean = lit.reshape(-1, 3).mean(axis=0)
    assert abs(mean[0] - 128) <= 2 and abs(mean[1] - 128) <= 2 and mean[2] >= 253, (
        f"expected ~(128,128,255) camera-space, got {mean}"
    )


def test_background_is_black_in_depth_and_normal(synthetic):
    mask = np.array(Image.open(os.path.join(synthetic["run_dir"], "mask", "00000.png")))
    assert not mask[0, 0]
    assert _img(synthetic, "depth_perframe")[0, 0] == 0
    assert tuple(int(v) for v in _img(synthetic, "normal")[0, 0]) == (0, 0, 0)


def test_mask_is_exactly_binary_from_a_real_render(synthetic):
    """film_transparent + filter_size ~0 should give an exact silhouette, not a
    feathered one. The manifest records the soft fraction so this is measured, not
    assumed."""
    assert synthetic["alpha_soft_fraction"] == 0.0
    img = Image.open(os.path.join(synthetic["run_dir"], "mask", "00000.png"))
    assert img.mode == "1"


def test_g4_agreed_with_the_projected_mesh(synthetic):
    assert synthetic["g4_max_delta"] is not None
    assert synthetic["g4_max_delta"] <= 2


def test_depth_values_match_the_geometry_that_was_built(synthetic):
    """z_max - z_min must be the 1.0-unit separation between the two planes."""
    assert synthetic["z_max"] - synthetic["z_min"] == pytest.approx(1.0, abs=1e-3)


def test_edge_marks_the_boundary_between_the_planes(synthetic):
    edge = _img(synthetic, "edge")
    assert set(np.unique(edge).tolist()) <= {0, 255}
    assert edge.max() == 255


def test_a_parked_camera_produces_identical_frames(synthetic):
    """Sweep is 0, so every frame is the same view. Any difference here is renderer
    nondeterminism inside a single process, which G3 would then be measuring."""
    first = _img(synthetic, "depth_perframe", 0)
    for f in range(1, 5):
        assert np.array_equal(first, _img(synthetic, "depth_perframe", f)), f"frame {f}"
