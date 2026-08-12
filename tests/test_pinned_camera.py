"""`framing.load_pinned_camera` — reusing a composition instead of re-solving one.

**The failure this exists to catch.** Pinning a camera skips the framing solve, and skipping
the solve skips its gate. A record pinned at a different azimuth, elevation, lens or sensor
projects a perfectly plausible skeleton of the same body seen from somewhere else — and
every downstream check passes on it: the counts are right, the frames are legal, nothing
lands off canvas, no frame is blank. Nothing but this comparison can fail on that input, so
the comparison raises rather than warns, and a record that is merely SILENT about an angle
is refused too.
"""

import json
import os

import pytest

from armature_core import framing
from armature_core.framing import FramingError

CAM = {
    "azimuth_deg": 225.0, "elevation_deg": 6.0, "lens_mm": 50.0, "sensor_mm": 36.0,
    "target": [-0.182057, 0.152792, 0.059935], "radius": 4.21793030051821,
}
EXPECT = {"azimuth_deg": 225.0, "elevation_deg": 6.0, "lens_mm": 50.0, "sensor_mm": 36.0}


def write(tmp_path, camera, name="prov.json"):
    p = os.path.join(str(tmp_path), name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"tool": "fixture", "camera": camera}, fh)
    return p


def test_a_matching_record_loads_its_target_and_radius(tmp_path):
    target, radius = framing.load_pinned_camera(write(tmp_path, CAM), EXPECT)
    assert target == (-0.182057, 0.152792, 0.059935)
    assert radius == pytest.approx(4.21793030051821)


def test_a_pinned_camera_reproduces_the_projection_it_came_from(tmp_path):
    """The point of the whole exercise: the same world point lands on the same pixel."""
    target, radius = framing.load_pinned_camera(write(tmp_path, CAM), EXPECT)
    a = framing.project((0.0, 0.0, 0.0), target, radius, 225.0, 6.0, 50.0, 36.0, 1920, 1080)
    b = framing.project((0.0, 0.0, 0.0), tuple(CAM["target"]), CAM["radius"],
                        225.0, 6.0, 50.0, 36.0, 1920, 1080)
    assert a == b


@pytest.mark.parametrize("field,wrong", [
    ("azimuth_deg", 45.0),        # the same body from the other side
    ("elevation_deg", 30.0),
    ("lens_mm", 85.0),
    ("sensor_mm", 24.0),
])
def test_a_disagreeing_angle_raises_and_names_itself(tmp_path, field, wrong):
    cam = dict(CAM, **{field: wrong})
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(write(tmp_path, cam), EXPECT)
    assert field in str(exc.value)


def test_a_record_silent_about_an_angle_is_refused(tmp_path):
    """A camera that agrees by omission is not a camera that agrees — and omission is the
    likelier shape, since a record written by another tool need not carry these fields."""
    cam = {k: v for k, v in CAM.items() if k != "lens_mm"}
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(write(tmp_path, cam), EXPECT)
    assert "lens_mm" in str(exc.value)
    assert "silence" in str(exc.value)


def test_no_expectation_means_no_comparison(tmp_path):
    """`expect=None` is the escape hatch, so it is tested rather than assumed absent."""
    cam = dict(CAM, azimuth_deg=45.0)
    target, radius = framing.load_pinned_camera(write(tmp_path, cam))
    assert radius == pytest.approx(CAM["radius"])


def test_a_record_with_no_camera_block_raises(tmp_path):
    p = os.path.join(str(tmp_path), "x.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"tool": "fixture", "resolution": [832, 480]}, fh)
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(p, EXPECT)
    assert "camera.target" in str(exc.value)


@pytest.mark.parametrize("bad", [
    {"target": [0.0, 0.0], "radius": 4.0},          # a 2-vector
    {"target": "origin", "radius": 4.0},
])
def test_a_malformed_target_raises(tmp_path, bad):
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(write(tmp_path, dict(CAM, **bad)), None)
    assert "3-vector" in str(exc.value)


@pytest.mark.parametrize("radius", [0.0, -4.0])
def test_a_nonpositive_radius_raises(tmp_path, radius):
    """Zero would put the camera inside the subject and every projection behind it."""
    with pytest.raises(FramingError) as exc:
        framing.load_pinned_camera(write(tmp_path, dict(CAM, radius=radius)), None)
    assert "not a distance" in str(exc.value)


def test_the_real_e09_previz_record_loads_if_it_is_on_this_rig():
    """The actual artifact this feature was built for. Skips off-rig rather than pretending."""
    p = (r"E:\AI\armature-E09\outputs\E09\b2-a3-render-lifted\render_provenance.json")
    if not os.path.isfile(p):
        pytest.skip("the E09 previz worktree is not on this machine")
    target, radius = framing.load_pinned_camera(p, EXPECT)
    assert len(target) == 3
    assert radius > 0
