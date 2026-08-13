"""Blender's ORTHO camera, measured rather than assumed. S04's calibration.

The S04 spec marks one premise ASSUMED — "Blender 5.2 headless supports
`camera.type='ORTHO'` + `ortho_scale`" — and three conventions ride on it that the
shot-set's own 1024x1024 preset **cannot see**:

* which image axis `ortho_scale` spans (identical predictions on a square frame);
* whether parallel projection is really independent of distance;
* which end of `Image.pixels` is the top of the picture.

The third is the one with no fallback. It is the sole premise carrying the row flip in
`render_turnaround._measure_alpha_plane`, and nothing derived from a rendered figure's bbox
can check it: the scale solve centres the subject, so a vertical flip maps the box to
itself within a pixel. Get it backwards and Gate CROP fires correctly and names the wrong
border in every report it ever writes. So the fixture's subject is deliberately NOT
centred — one cube high above the camera target — and the raw array's row order answers it.

Compensator: the Blender script writes three PNGs under
`outputs/_test_ortho_convention/`. Compensator: delete that directory; owner: the executor
session.
"""

import json
import os
import subprocess

import pytest

from conftest import BLENDER, REPO

pytestmark = pytest.mark.skipif(
    not os.path.isfile(BLENDER), reason=f"Blender not found at {BLENDER}"
)

SCRIPT = os.path.join(REPO, "tests", "blender", "check_ortho_convention.py")


@pytest.fixture(scope="module")
def measured():
    proc = subprocess.run(
        [BLENDER, "-b", "-P", SCRIPT], capture_output=True, text=True, timeout=900
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("ORTHO_CONVENTION ")]
    assert lines, f"no result\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    return json.loads(lines[-1][len("ORTHO_CONVENTION "):])


def test_the_frame_is_not_square_or_this_whole_file_is_vacuous(measured):
    """Guard on the fixture, first because everything else leans on it.

    On a square frame the two candidate ortho fits predict identical pixels and
    `test_the_scale_spans_the_longer_axis` becomes a check that cannot fail. If someone
    ever "simplifies" this fixture to the Task-C preset, this is what says so.
    """
    assert measured["frame_is_square"] is False
    assert measured["resolution"] == [352, 1024]


def test_blender_accepts_an_ortho_camera_and_keeps_the_scale(measured):
    """The spec's ASSUMED premise, read back off the datablock rather than off the docs.
    Assigning an attribute is not the same as Blender honouring it."""
    assert measured["camera_type_after_assignment"] == "ORTHO"
    assert measured["ortho_scale_after_assignment"] == pytest.approx(2.0)


def test_the_scale_spans_the_longer_axis(measured):
    """THE discriminating fixture, and it cannot come out ambiguous.

    A 0.4-unit cube at `ortho_scale` 2.0 in a 352x1024 frame is 204.8 px wide under the
    convention `framing.ortho_half_spans` implements, and 70.4 px wide under the transposed
    one — a factor of 2.9. Measured: 203 px.
    """
    a = measured["scale_a"]
    x0, x1 = a["raw_bbox"][0], a["raw_bbox"][2]
    span = x1 - x0
    ours = a["width_hypotheses"]["ours_px"]
    theirs = a["width_hypotheses"]["transposed_px"]
    assert span == pytest.approx(ours, abs=3)
    assert abs(span - theirs) > 0.5 * ours


def test_a_square_world_span_renders_square_on_square_pixels(measured):
    """The cube is 0.4 units in both axes. If the two spans were derived from different
    scales, this is where it shows — and it is invisible in the width check alone."""
    a = measured["scale_a"]["raw_bbox"]
    assert (a[2] - a[0]) == pytest.approx(a[3] - a[1], abs=2)


def test_image_pixels_come_back_bottom_up(measured):
    """The premise carrying `_measure_alpha_plane`'s flip, stated as the flip itself.

    The cube sits high in the world, so `framing.project` puts it near the TOP of the
    picture — predicted rows 25.6..230.4 top-down. The raw array returns it at rows
    794..997, which is that box reflected through the frame: `1023 - 230.4 = 792.6` and
    `1023 - 25.6 = 997.4`. Asserting the reflection rather than merely "the rows are in the
    bottom half" is what makes this fail if the projector and the reader ever disagree by
    an offset instead of by an orientation.
    """
    h = measured["resolution"][1]
    raw = measured["scale_a"]["raw_bbox"]
    pred = measured["scale_a"]["predicted_top_down"]
    assert raw[1] == pytest.approx((h - 1) - pred["y1"], abs=2)
    assert raw[3] == pytest.approx((h - 1) - pred["y0"], abs=2)
    assert raw[1] > h / 2 and raw[3] > h / 2


def test_distance_does_not_change_size_in_the_render_either(measured):
    """The property the shared `ortho_scale` rests on, checked in Blender rather than only
    in the projector. One scale across eight views means nothing if standoff still moves
    size — and the ortho path sets the radius from the subject's bounding sphere, so it is
    free to differ between subjects."""
    assert measured["scale_a"]["raw_bbox"] == measured["scale_a_far"]["raw_bbox"]
    assert measured["scale_a_far"]["radius"] == 10 * measured["scale_a"]["radius"]


def test_doubling_the_scale_halves_the_subject(measured):
    """`ortho_scale` is a world span, so size goes as its inverse. A camera that ignored
    the value entirely would render both frames identically and pass every check above
    except this one."""
    a, b = measured["scale_a"]["raw_bbox"], measured["scale_b"]["raw_bbox"]
    assert measured["scale_b"]["ortho_scale"] == 2 * measured["scale_a"]["ortho_scale"]
    assert (b[2] - b[0]) == pytest.approx((a[2] - a[0]) / 2.0, abs=3)
    assert (b[3] - b[1]) == pytest.approx((a[3] - a[1]) / 2.0, abs=3)


def test_the_projector_agrees_with_the_render_on_both_axes(measured):
    """The two independent measurements the manifest carries per view, exercised here on a
    subject whose geometry is exactly known — so a disagreement is the projector's fault
    and not a decimated cloud's."""
    h = measured["resolution"][1]
    for tag in ("scale_a", "scale_b"):
        raw, pred = measured[tag]["raw_bbox"], measured[tag]["predicted_top_down"]
        assert raw[0] == pytest.approx(pred["x0"], abs=2)
        assert raw[2] == pytest.approx(pred["x1"], abs=2)
        assert raw[1] == pytest.approx((h - 1) - pred["y1"], abs=2)
        assert raw[3] == pytest.approx((h - 1) - pred["y0"], abs=2)
