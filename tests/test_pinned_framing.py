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


# ------------------------------------------------------- preview_walk resolves the shot
#
# F-b97fba5b. `preview_walk.py:93-94` re-derived the two camera fields instead of reading
# them the way `stage_render` does:
#
#     target = Vector(c["target"]) if c["target"] != "bbox_center" else Vector((0, 0, 0))
#     radius = float(c["radius"])
#
# `bbox_center` is the DEFAULT (`shotspec.DEFAULTS["camera"]["target"]`) and it resolved to
# the WORLD ORIGIN, not the subject; `radius` is `"auto"` by default and `float("auto")`
# raises. So the one artifact whose stated purpose is "so the performance can be inspected
# before a credit is spent" either crashed on the default spec or previewed a shot aimed at
# the origin — while the module docstring claims "one implementation, so the preview cannot
# drift from the render."
#
# `stage_render.BlenderBackend.prepare` needs bpy, so the tie here is the one the file's own
# coverage-boundary note already uses: preview_walk must call the SAME helpers with the SAME
# arguments (`bs.auto_radius(sphere_r, lens, sensor, width, height, fit_margin)`, stage_render
# lines 168-170) and report the SAME source strings.

import ast

from blender_stub import load_tool, read_source

SPECS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs")
COMMITTED_SPECS = sorted(f for f in os.listdir(SPECS_DIR) if f.endswith(".json"))

#: A subject that is nowhere near the origin, so "resolved to (0,0,0)" is distinguishable
#: from "resolved to the measured centre".
BOUNDS = (np.array([1.5, -2.25, 0.875]), np.array([0.3, 0.3, 0.9]), 1.125)


def _shot_specs():
    """The committed specs that describe a render (a camera and a resolution)."""
    out = []
    for fn in COMMITTED_SPECS:
        try:
            spec = shotspec.load_spec(os.path.join(SPECS_DIR, fn))
        except SpecError:
            continue
        if "camera" in spec and "resolution" in spec:
            out.append((fn, spec))
    return out


def test_the_committed_shot_specs_still_exercise_both_defaults():
    """If every committed spec pinned both fields this check would prove nothing — E03 is
    the only one that does, and it is not the population."""
    specs = _shot_specs()
    assert specs, COMMITTED_SPECS
    assert any(s["camera"]["target"] == "bbox_center" for _, s in specs)
    assert any(s["camera"]["radius"] == "auto" for _, s in specs)


@pytest.mark.parametrize("filename", [fn for fn, _ in _shot_specs()])
def test_preview_walk_resolves_every_committed_spec_the_way_stage_render_does(filename):
    pw = load_tool("preview_walk.py")
    bs = pw.blender_scene          # imported under the bpy stub; auto_radius is pure math
    spec = shotspec.load_spec(os.path.join(SPECS_DIR, filename))
    c = spec["camera"]
    w, h = int(spec["resolution"]["width"]), int(spec["resolution"]["height"])

    got = pw.resolve_camera(spec, BOUNDS, w, h)

    if c["target"] == "bbox_center":
        assert tuple(got["target"]) == tuple(float(v) for v in BOUNDS[0])
        assert tuple(got["target"]) != (0.0, 0.0, 0.0)
        assert got["target_source"] == "measured bbox centre"
    else:
        assert tuple(got["target"]) == tuple(float(v) for v in c["target"])
        assert got["target_source"] == "spec.camera.target (pinned)"

    if c["radius"] == "auto":
        want = bs.auto_radius(BOUNDS[2], c["lens_mm"], c["sensor_mm"], w, h,
                              c["fit_margin"])
        assert got["radius"] == pytest.approx(want, rel=0, abs=0)
        assert got["radius_source"].startswith("auto")
    else:
        assert got["radius"] == float(c["radius"])
        assert got["radius_source"] == "spec.camera.radius (pinned)"


def test_preview_walk_reports_the_same_source_vocabulary_stage_render_writes():
    """The two strings are the record a reader compares a preview against; if they drift
    the two artifacts stop being comparable at all."""
    sr = read_source("stage_render.py")
    pw = read_source("preview_walk.py")
    for phrase in ('"measured bbox centre"', '"spec.camera.target (pinned)"'):
        assert phrase in sr, phrase
        assert phrase in pw, phrase


def test_the_old_two_lines_disagree_with_the_resolver_on_the_default_spec():
    """The red direction, pinned so this cannot become a check that passes on anything.

    The superseded expressions are reproduced here VERBATIM and must fail or disagree on a
    spec carrying the shotspec defaults."""
    pw = load_tool("preview_walk.py")
    spec = shotspec.load_spec(os.path.join(SPECS_DIR, "E01-anchor.json"))
    c = spec["camera"]
    assert c["target"] == "bbox_center" and c["radius"] == "auto"

    old_target = tuple(c["target"]) if c["target"] != "bbox_center" else (0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        float(c["radius"])                      # `float("auto")` — the crash

    got = pw.resolve_camera(spec, BOUNDS, int(spec["resolution"]["width"]),
                            int(spec["resolution"]["height"]))
    assert tuple(got["target"]) != old_target


def test_the_preview_counts_its_frames_by_name_not_by_extension():
    """`preview_walk.py:114` counted `*.png` in the output directory with a bare listdir.
    Its population must be the plan — `shotspec.frame_names` — so a stray file cannot make
    a short render look complete and a misnamed frame cannot hide."""
    src = read_source("preview_walk.py")
    assert 'os.listdir(a.out) if f.endswith(".png")' not in src, (
        "the completeness check still counts whatever *.png happens to be in the output "
        "directory: a stray makes a short render look complete, and the check cannot name "
        "which frame is missing")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "frame_names"]
    assert calls, "preview_walk does not build its population from shotspec.frame_names"
