"""Tests for the two things E03 pins so its arms differ in exactly one variable.

Both exist for the same reason and it is worth stating once: B1 and B3 render the SAME
asset and are supposed to differ only in whether the timeline advances. Two derived
quantities quietly broke that — the camera fit (union of all frames vs the bind pose) and
the depth normalisation window (each shot's own z extent). Neither is a bug; both are
correct behaviour that becomes a confound the moment two arms are compared.

⚠ **Coverage boundary, stated rather than implied.** The camera-target *resolution* lives
in `BlenderBackend.prepare`, which needs bpy, so these tests cover its spec validation
only. That the pinned target actually reaches the camera was verified by measurement
instead: both E03 control manifests report `camera_target_source: "spec.camera.target
(pinned)"` and the same `camera_radius_resolved` to ten decimals.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import stage_render  # noqa: E402
from armature_core import shotspec  # noqa: E402
from armature_core.errors import SpecError  # noqa: E402
from fake_backend import FakeBackend, make_spec  # noqa: E402


# ------------------------------------------------------------------ the depth window

def _spec(tmp_path, **over):
    spec = make_spec(tmp_path, count=5, channels=("depth", "mask"))
    spec.update(over)
    return spec


def test_default_is_per_shot_so_E01_and_E02_are_unchanged(tmp_path):
    manifest = stage_render.run_export(
        _spec(tmp_path), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    p3 = manifest["p3"]
    assert p3["window_source"] == "measured per-shot"
    assert p3["shot_z_min"] == p3["measured_z_min"] == pytest.approx(2.0)
    assert p3["shot_z_max"] == p3["measured_z_max"] == pytest.approx(5.0)


def test_a_pinned_window_overrides_the_measured_extent(tmp_path):
    manifest = stage_render.run_export(
        _spec(tmp_path, depth={"window": [1.0, 9.0]}), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    p3 = manifest["p3"]
    assert p3["window_source"] == "spec.depth.window (pinned)"
    assert (p3["shot_z_min"], p3["shot_z_max"]) == (1.0, 9.0)
    # The measured extent is still recorded — a pinned window must never hide what the
    # shot actually held.
    assert p3["measured_z_min"] == pytest.approx(2.0)
    assert p3["measured_z_max"] == pytest.approx(5.0)
    assert p3["measured_within_window"] is True


def test_two_shots_with_different_extents_get_the_SAME_pixels_under_one_window(tmp_path):
    """The property the pin exists for, measured end to end.

    Two runs of identical geometry whose shots have different z extents — exactly B1 vs B3.
    Under per-shot normalisation their depth PNGs differ; under one pinned window they are
    byte-identical.
    """
    # `breathe` widens the depth window as the shot proceeds and leaves frame 0 untouched,
    # so two runs differing only in breathe hold IDENTICAL geometry on frame 0 and different
    # shot extents — which is the B1/B3 shape. (Varying z_far instead would change the
    # scene's depth content, not just its extent, and the pin could not fix that.)
    def render(name, breathe, depth):
        stage_render.run_export(
            _spec(tmp_path, depth=depth), str(tmp_path / name),
            backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0, breathe=breathe),
        )
        return (tmp_path / name / "depth_pershot" / "00000.png").read_bytes()

    still_ps = render("still_ps", 0.0, {"window": "per_shot"})
    moving_ps = render("moving_ps", 1.0, {"window": "per_shot"})
    assert still_ps != moving_ps, (
        "fixture is wrong: with per-shot normalisation the same frame-0 geometry must "
        "render differently under different shot extents, or there is nothing to pin"
    )

    win = {"window": [2.0, 8.0]}
    assert render("still_pin", 0.0, win) == render("moving_pin", 1.0, win)


def test_a_window_that_does_not_contain_the_shot_is_REPORTED_not_hidden(tmp_path):
    """Clipping is not raised on — a deliberately tight window is a legitimate creative
    choice — but it must be visible in the manifest rather than inferred from the pixels."""
    manifest = stage_render.run_export(
        _spec(tmp_path, depth={"window": [2.5, 3.0]}), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    assert manifest["p3"]["measured_within_window"] is False


@pytest.mark.parametrize("bad", [
    [3.0], [1, 2, 3], "auto", [3.0, 1.0], ["1", "2"], [True, False], None,
])
def test_a_malformed_window_raises(bad):
    with pytest.raises(SpecError, match="depth.window"):
        shotspec.normalise_spec({
            "spec_version": 1, "name": "x", "generator": "wan-vace",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 480, "height": 832},
            "frames": {"count": 33, "fps": 16},
            "channels": ["depth"], "depth": {"window": bad},
        })


def test_an_inverted_window_raises_before_it_collapses_the_normalisation():
    with pytest.raises(SpecError, match="z_min must be below"):
        shotspec.normalise_spec({
            "spec_version": 1, "name": "x", "generator": "wan-vace",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 480, "height": 832},
            "frames": {"count": 33, "fps": 16},
            "channels": ["depth"], "depth": {"window": [5.0, 5.0]},
        })


# ------------------------------------------------------------------ the camera target

def _cam_spec(target):
    return shotspec.normalise_spec({
        "spec_version": 1, "name": "x", "generator": "wan-vace",
        "asset": {"path": "x.glb"},
        "resolution": {"width": 480, "height": 832},
        "frames": {"count": 33, "fps": 16},
        "channels": ["depth"], "camera": {"target": target},
    })


def test_bbox_center_remains_the_default():
    assert shotspec.DEFAULTS["camera"]["target"] == "bbox_center"
    assert _cam_spec("bbox_center")["camera"]["target"] == "bbox_center"


def test_a_numeric_target_is_accepted():
    assert _cam_spec([0.0, 0.0, 0.56])["camera"]["target"] == [0.0, 0.0, 0.56]


@pytest.mark.parametrize("bad", [
    [0.0, 0.0], [0.0, 0.0, 0.0, 0.0], "centre", [0.0, 0.0, "z"], [True, False, True], 0.56,
])
def test_a_malformed_target_raises(bad):
    with pytest.raises(SpecError, match="camera.target"):
        _cam_spec(bad)
