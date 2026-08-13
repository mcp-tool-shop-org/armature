"""S04 — the sprite shot-set: parallel projection, one shared scale, and Gate CROP.

Three properties are worth a test here and each one is silent everywhere else.

**The perspective path did not move.** `framing.project` grew a keyword. If the
perspective arithmetic shifted by a float in the process, every composition this repo has
ever solved shifts with it and no gate anywhere reports a thing — the renders would simply
be slightly different from the ones the reports describe. So the old formula is written out
again in this file, by hand, and the two are compared. Comparing the function to itself
would prove nothing.

**The ortho fit is on the same axis as the perspective fit.** Blender's AUTO sensor fit
puts the sensor dimension on the longer image axis; `half_fovs` is already pinned against
Blender's own copy of that rule in `test_framing.py`. `ortho_half_spans` is therefore
pinned against `half_fovs` rather than against a fresh reading of the manual, which chains
it onto an anchor that is already measured. **A square frame cannot see this at all** — the
two spans are equal there — and the Task-C preset is square, which is why the calibration
render is taken at 352x1024.

**One scale is shared by every cell.** That is the whole sprite property. A per-view solve
produces eight beautifully framed cells that cannot be laid beside one another, and the
symptom is invisible in any single cell: a character genuinely narrower in profile is
silently enlarged until he matches his own front view.
"""

import importlib.util
import math
import os
import sys
import types
from unittest import mock

import pytest

from armature_core import framing
from armature_core import turnaround as TA
from conftest import TOOLS


LENS, SENSOR = 50.0, 36.0


# --------------------------------------------------------------- the tool, without Blender


@pytest.fixture(scope="module")
def rt():
    """`render_turnaround`, imported with Blender stubbed out.

    The module does `import bpy` at the top, so the suite cannot import it the ordinary
    way. The repo's existing idiom for this (`test_turnaround.py`, `test_framing.py`) is
    to regex one function out of the source text and exec it — which works, and which
    silently stops covering anything the regex does not reach. Stubbing the two modules
    Blender owns and importing the real file covers `parse_args`, the solve, and the
    module constants at once, and it fails loudly if the import surface changes.
    """
    saved = {k: sys.modules.get(k) for k in ("bpy", "mathutils")}
    sys.modules["bpy"] = mock.MagicMock(name="bpy")
    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = lambda v: v
    mathutils.Matrix = mock.MagicMock(name="Matrix")
    sys.modules["mathutils"] = mathutils
    try:
        path = os.path.join(TOOLS, "render_turnaround.py")
        spec = importlib.util.spec_from_file_location("_rt_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# ------------------------------------------------- the perspective path did not move


def _perspective_reference(point, target, radius, az, el, lens, sensor, w, h):
    """The pre-S04 projection, written out by hand so the comparison is a comparison."""
    ex, ax = math.radians(el), math.radians(az)
    pos = (target[0] + radius * math.cos(ex) * math.cos(ax),
           target[1] + radius * math.cos(ex) * math.sin(ax),
           target[2] + radius * math.sin(ex))
    back = [pos[i] - target[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in back))
    back = [c / n for c in back]
    d = back[2]
    proj = [(0.0, 0.0, 1.0)[i] - back[i] * d for i in range(3)]
    n = math.sqrt(sum(c * c for c in proj))
    up = [c / n for c in proj]
    right = [up[1] * back[2] - up[2] * back[1],
             up[2] * back[0] - up[0] * back[2],
             up[0] * back[1] - up[1] * back[0]]
    v = [point[i] - pos[i] for i in range(3)]
    z = sum(v[i] * back[i] for i in range(3))
    if z >= -1e-9:
        return None, None, False
    if w >= h:
        sx, sy = sensor, sensor * h / w
    else:
        sy, sx = sensor, sensor * w / h
    hx, hy = math.atan(sx * 0.5 / lens), math.atan(sy * 0.5 / lens)
    ndc_x = (sum(v[i] * right[i] for i in range(3)) / -z) / math.tan(hx)
    ndc_y = (sum(v[i] * up[i] for i in range(3)) / -z) / math.tan(hy)
    return 0.5 + 0.5 * ndc_x, 0.5 - 0.5 * ndc_y, True


@pytest.mark.parametrize("w,h", [(352, 1024), (1024, 1024), (832, 480)])
@pytest.mark.parametrize("az,el", [(270.0, 0.0), (315.0, 30.0), (45.0, -20.0)])
def test_the_perspective_projection_is_exactly_what_it_was_before_the_keyword(w, h, az, el):
    """THE regression fixture for Task A's structural invariant.

    A keyword with a default cannot change a caller's behaviour *in principle*; in practice
    the edit that adds one is the edit that reorders the arithmetic around it. Nothing in
    this repo would report that: renders still succeed, gates still pass, and the framing
    is merely a little different from every number already written down.
    """
    target = (0.31, -0.12, 0.94)
    for point in ((0.0, 0.0, 0.0), (0.4, 0.25, 1.8), (-0.6, 0.33, 0.2), (0.1, -0.9, 1.1)):
        got = framing.project(point, target, 2.4, az, el, LENS, SENSOR, w, h)
        want = _perspective_reference(point, target, 2.4, az, el, LENS, SENSOR, w, h)
        assert got[2] == want[2]
        if got[2]:
            assert got[0] == pytest.approx(want[0], abs=1e-12)
            assert got[1] == pytest.approx(want[1], abs=1e-12)


def test_omitting_the_keyword_and_passing_none_are_the_same_call(rt):
    """`ortho_scale=None` is the perspective path, stated as a property rather than as a
    comment. A refactor that made `None` mean "square frame, scale 1" would pass every
    other test in this file."""
    args = ((0.4, 0.25, 1.8), (0.0, 0.0, 0.9), 2.4, 315.0, 30.0, LENS, SENSOR, 352, 1024)
    assert framing.project(*args) == framing.project(*args, ortho_scale=None)


# --------------------------------------------------------------- the ortho fit convention


@pytest.mark.parametrize("w,h", [(352, 1024), (1024, 352), (1024, 1024), (832, 480)])
def test_the_ortho_fit_lands_on_the_same_axis_the_perspective_fit_does(w, h):
    """`half_fovs` is already pinned against Blender's own copy in `test_framing.py`, so
    pinning the ortho spans to it chains the new convention onto a measured anchor instead
    of onto a second reading of the manual.

    If `ortho_scale` were applied to the SHORT axis instead, this ratio inverts — and on
    the square Task-C preset the error is exactly zero, which is the whole reason the
    calibration render is 352x1024.
    """
    hx, hy = framing.half_fovs(LENS, SENSOR, w, h)
    sx, sy = framing.ortho_half_spans(3.0, w, h)
    assert sx / sy == pytest.approx(math.tan(hx) / math.tan(hy))


def test_the_scale_spans_the_longer_axis_in_world_units():
    sx, sy = framing.ortho_half_spans(4.0, 1024, 352)
    assert 2 * sx == pytest.approx(4.0)
    assert 2 * sy == pytest.approx(4.0 * 352 / 1024)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_a_non_positive_scale_raises_rather_than_collapsing_the_frame(bad):
    """A zero span projects every point to the frame centre. The render saves, opens, is
    the right size, and carries a perfectly valid alpha channel."""
    with pytest.raises(framing.FramingError):
        framing.ortho_half_spans(bad, 512, 512)


# ------------------------------------------------------------- parallel means parallel


def test_distance_does_not_change_size_under_parallel_projection():
    """The defining property, and the one that fails if the `/-z` divide is left in.

    A perspective projection at two standoffs draws two different sizes; a parallel one
    draws the same size. Both renders look entirely plausible on their own.
    """
    target, point = (0.0, 0.0, 0.0), (0.0, 0.0, 0.8)
    near = framing.project(point, target, 3.0, 270.0, 0.0, LENS, SENSOR, 512, 512,
                           ortho_scale=2.0)
    far = framing.project(point, target, 30.0, 270.0, 0.0, LENS, SENSOR, 512, 512,
                          ortho_scale=2.0)
    assert near[0] == pytest.approx(far[0], abs=1e-12)
    assert near[1] == pytest.approx(far[1], abs=1e-12)

    p_near = framing.project(point, target, 3.0, 270.0, 0.0, LENS, SENSOR, 512, 512)
    p_far = framing.project(point, target, 30.0, 270.0, 0.0, LENS, SENSOR, 512, 512)
    assert p_near[1] != pytest.approx(p_far[1], abs=1e-6)


def test_on_a_square_frame_the_screen_fraction_is_the_world_extent_over_the_scale():
    """The identity that makes the shared scale mean what the sheet needs it to mean: two
    characters measured in the same `ortho_scale` are drawn at the same millimetres-per-
    pixel, which is what lets the cells sit beside each other."""
    target = (0.0, 0.0, 0.0)
    for extent, scale in ((0.8, 2.0), (1.6, 2.0), (0.8, 4.0)):
        lo = framing.project((0.0, 0.0, -extent / 2), target, 5.0, 270.0, 0.0,
                            LENS, SENSOR, 512, 512, ortho_scale=scale)
        hi = framing.project((0.0, 0.0, extent / 2), target, 5.0, 270.0, 0.0,
                             LENS, SENSOR, 512, 512, ortho_scale=scale)
        assert abs(hi[1] - lo[1]) == pytest.approx(extent / scale)


# --------------------------------------------------------------------- the shared scale


def _asymmetric_cloud():
    """A figure much deeper than he is wide: his profile silhouette is not his front one.

    A subject symmetric about the vertical axis would make a per-view solve and a
    max-over-views solve return the same number, and the test would pass on either.
    """
    pts = []
    for z in (0.0, 0.4, 0.9, 1.4, 1.75):
        pts += [(0.0, 0.0, z), (0.12, 0.0, z), (-0.12, 0.0, z)]
    # arms thrown forward along -Y, which only a side-on view sees the full length of
    pts += [(0.0, -0.55, 1.35), (0.0, -0.55, 1.2), (0.1, -0.5, 1.3)]
    # and a hat brim that raises the silhouette from the front only
    pts += [(0.22, 0.0, 1.82), (-0.22, 0.0, 1.82)]
    return pts


def test_one_scale_is_shared_and_the_largest_view_is_the_one_that_fits(rt):
    """Task A's first clause, as a property of the returned number.

    Two things have to hold together and they are predicted separately: the TALLEST view
    lands exactly on `height_frac`, and NO view exceeds it. A solve that took the first
    azimuth, or the mean, satisfies neither reliably — and every individual cell it
    produced would still look correctly framed on its own.
    """
    cloud = _asymmetric_cloud()
    target, azimuths, frac = (0.0, -0.1, 0.9), [270.0, 315.0, 0.0, 45.0, 90.0], 0.831
    w, h = 512, 1024

    scale = rt.solve_ortho_scale_for_height(cloud, target, 6.0, azimuths, 30.0,
                                            w, h, frac)

    from armature_core import startframe as SF
    heights = []
    for az in azimuths:
        ext = SF.silhouette_extent(cloud, target, 6.0, az, 30.0, None, None, w, h,
                                   ortho_scale=scale)
        heights.append((ext["y1"] - ext["y0"]) / float(h))
    assert max(heights) == pytest.approx(frac, abs=1e-6)
    assert all(v <= frac + 1e-9 for v in heights)


def test_the_shared_scale_does_not_depend_on_the_standoff(rt):
    """The radius keeps only a positional role on the ortho path. If it leaked into the
    solve, the sheet's scale would silently depend on a clipping choice."""
    cloud, target = _asymmetric_cloud(), (0.0, -0.1, 0.9)
    az = [270.0, 315.0, 0.0]
    a = rt.solve_ortho_scale_for_height(cloud, target, 5.0, az, 30.0, 512, 1024, 0.8)
    b = rt.solve_ortho_scale_for_height(cloud, target, 40.0, az, 30.0, 512, 1024, 0.8)
    assert a == pytest.approx(b, rel=1e-9)


# ------------------------------------------------------------------- the branch itself


def test_the_default_arguments_select_the_perspective_branch(rt):
    """Task A's structural invariant, taken through the REAL parser rather than a
    hand-written flag value.

    A test that passed `ortho=False` directly would keep passing after somebody flipped
    the flag's default to `True`, and the perspective path would be gone with every gate
    still green.
    """
    argv = sys.argv
    sys.argv = ["blender", "--", "--glb=x.glb", "--out=y"]
    try:
        a = rt.parse_args()
    finally:
        sys.argv = argv

    assert a.ortho is False
    plan = TA.projection_plan(a.ortho, a.lens, a.sensor)
    assert plan["projection"] == TA.PERSPECTIVE
    assert plan["blender_camera_type"] == "PERSP"
    assert plan["solved"] == "radius"
    assert plan["lens_mm"] == 50.0 and plan["sensor_mm"] == 36.0


def test_the_flag_selects_the_ortho_branch(rt):
    argv = sys.argv
    sys.argv = ["blender", "--", "--glb=x.glb", "--out=y", "--ortho"]
    try:
        a = rt.parse_args()
    finally:
        sys.argv = argv
    assert a.ortho is True
    plan = TA.projection_plan(a.ortho, a.lens, a.sensor)
    assert plan["projection"] == TA.ORTHOGRAPHIC
    assert plan["blender_camera_type"] == "ORTHO"
    assert plan["solved"] == "ortho_scale"


def test_the_ortho_plan_carries_no_focal_length():
    """Blender keeps a `lens` value on an ORTHO camera and ignores it. A plan that passed
    one through would let a reader believe the lens still composes the shot — and the
    manifest is where that belief would land."""
    plan = TA.projection_plan(True, 50.0, 36.0)
    assert plan["lens_mm"] is None
    assert plan["sensor_mm"] is None


def test_the_two_plans_disagree_about_what_is_shared():
    assert TA.projection_plan(False, 50.0, 36.0)["shared_across_views"] == "radius"
    assert TA.projection_plan(True, 50.0, 36.0)["shared_across_views"] == "ortho_scale"


# ------------------------------------------------------------------------- Gate CROP


W, H = 1024, 1024


def test_a_whole_cell_passes_and_reports_its_tightest_clearance():
    ev = TA.gate_view_crop(2, (40, 90, 980, 940), W, H, path="turn_2.png")
    assert ev["cropped"] is False
    assert ev["clearance_px"] == {"left": 40, "right": 43, "top": 90, "bottom": 83}
    assert "tightest clearance 40 px" in ev["verdict"]


@pytest.mark.parametrize("bbox,side", [
    ((0, 90, 980, 940), "left"),
    ((40, 0, 980, 940), "top"),
    ((40, 90, W - 1, 940), "right"),
    ((40, 90, 980, H - 1), "bottom"),
])
def test_the_gate_fires_on_each_border_including_the_last_index(bbox, side):
    """THE red test, and the off-by-one is the point of the last two cases.

    The subject's box is INCLUSIVE, so a figure amputated at the right edge has
    `x1 == width - 1`, not `width`. A gate written `x1 >= width` — the natural thing to
    write — passes a cell whose whole right side is sheared off, and passes it silently:
    the file is the right size, the alpha is authored, the eight views are distinct.
    """
    with pytest.raises(TA.TurnaroundCropGate) as exc:
        TA.gate_view_crop(0, bbox, W, H)
    assert side in str(exc.value)
    assert exc.value.gate == "CROP"
    assert exc.value.evidence["border_contact"][side] is True
    assert exc.value.evidence["cropped"] is True


def test_one_pixel_of_contact_is_enough():
    """A gate written against a fraction of the border, or against "several" pixels, would
    admit the first millimetre of an amputation — which is the whole of it on a cell the
    sheet then repeats eight times."""
    with pytest.raises(TA.TurnaroundCropGate):
        TA.gate_view_crop(0, (0, 500, 500, 600), W, H)


def test_a_clearance_of_exactly_one_pixel_passes():
    """The boundary is a structural fact about the box, not a margin somebody could move
    by a pixel when they did not like the result."""
    ev = TA.gate_view_crop(0, (1, 1, W - 2, H - 2), W, H)
    assert min(ev["clearance_px"].values()) == 1


def test_a_cell_nobody_rendered_into_raises_rather_than_passing_vacuously():
    """The vacuity guard. An empty frame touches no border, so a gate written only against
    contact PASSES it — and passes it precisely because the failure was total rather than
    partial. Gate ALPHA catches this case in the tool, which is exactly why this gate must
    not lean on Gate ALPHA having run first."""
    with pytest.raises(TA.TurnaroundCropGate) as exc:
        TA.gate_view_crop(4, None, W, H)
    assert "no subject pixels at all" in str(exc.value)
    assert exc.value.evidence["subject_bbox_px"] is None


def test_the_evidence_carries_the_box_even_when_it_raises():
    with pytest.raises(TA.TurnaroundCropGate) as exc:
        TA.gate_view_crop(1, (0, 0, W - 1, H - 1), W, H, path="turn_1.png")
    ev = exc.value.evidence
    assert ev["subject_bbox_px"] == [0, 0, W - 1, H - 1]
    assert ev["path"] == "turn_1.png"
    assert sorted(ev["border_contact"]) == ["bottom", "left", "right", "top"]


def test_the_gate_reads_a_non_square_frame_on_the_right_axes():
    """Width and height are not interchangeable, and a transposed read passes on every
    square fixture in this file — which is what the Task-C preset is."""
    ev = TA.gate_view_crop(0, (10, 10, 340, 1000), 352, 1024)
    assert ev["clearance_px"] == {"left": 10, "right": 11, "top": 10, "bottom": 23}
    with pytest.raises(TA.TurnaroundCropGate):
        TA.gate_view_crop(0, (10, 10, 351, 1000), 352, 1024)


# ---------------------------------------------------- the tool's own border measurement


def test_the_tools_border_measurement_agrees_with_the_gate(rt):
    """`_border_contact` reports on the perspective path, where the gate is not armed. A
    measurement that disagreed with the gate would put two different answers in one
    manifest."""
    assert rt._border_contact((0, 5, 100, 200), 1024, 1024)["touching"] == ["left"]
    assert rt._border_contact((5, 5, 100, 200), 1024, 1024)["touching"] == []
    assert rt._border_contact(None, 1024, 1024)["subject_bbox_px"] is None


def test_no_quantity_derived_from_the_bbox_can_see_a_flipped_row_order():
    """The measurement that decided where the flip check has to live.

    The solve centres the figure, so flipping the rows maps the box to itself: at
    `height_frac` 0.831 in 1024 rows the two boxes differ by ONE pixel. That kills the
    obvious candidates — the predicted-vs-measured delta, and any probe that asks where
    the subject's crown falls WITHIN the measured box, since the box it is measured
    against flipped too. Anyone reading either as an orientation check is reading a number
    that looks perfect with the picture upside down.
    """
    h, y0, y1 = 1024, 87, 937
    flipped_y0, flipped_y1 = h - 1 - y1, h - 1 - y0
    assert abs(flipped_y0 - y0) <= 1 and abs(flipped_y1 - y1) <= 1

    crown_from_top_true = 0.0
    crown_from_top_flipped = ((h - 1 - y0) - flipped_y0) / float(flipped_y1 - flipped_y0)
    assert crown_from_top_flipped == pytest.approx(1.0, abs=0.01)
    assert crown_from_top_true != pytest.approx(crown_from_top_flipped, abs=0.5)


def test_the_alpha_measurement_flips_blenders_bottom_up_rows_to_top_down(rt):
    """THE flip fixture, and the only place in the suite that binds it.

    `Image.pixels` hands row 0 back at the BOTTOM of the picture. A subject occupying the
    TOP of the image therefore sits in the LAST rows of the array Blender returns. Drop the
    flip and this bbox comes back as rows 7..9 instead of 0..2 — Gate CROP would then name
    `bottom` for a figure amputated at the `top`, on evidence that is otherwise entirely
    correct.
    """
    import numpy as np

    plane = np.zeros((10, 6), dtype=np.float32)
    plane[7:10, 1:4] = 1.0          # bottom-up rows 7..9 == the top three rows of the image
    m = rt._measure_alpha_plane(plane)

    assert m["subject_bbox"] == (1, 0, 3, 2)
    assert m["subject_pixels"] == 9
    assert m["alpha_min"] == 0 and m["alpha_max"] == 255
    assert m["transparent_fraction"] == pytest.approx(51 / 60)


def test_the_alpha_measurement_reports_an_empty_plane_as_no_box(rt):
    """The render nobody is in. `mask_bbox` returns None and Gate CROP's vacuity clause is
    what turns that into a halt — this only pins that the measurement does not invent a
    zero-sized box at the origin."""
    import numpy as np

    m = rt._measure_alpha_plane(np.zeros((8, 8), dtype=np.float32))
    assert m["subject_bbox"] is None
    assert m["subject_pixels"] == 0
    assert m["transparent_fraction"] == 1.0


def test_predicted_versus_measured_is_a_signed_delta_and_survives_an_empty_render(rt):
    ext = {"x0": 10.4, "x1": 200.6, "y0": 5.2, "y1": 300.9}
    d = rt._predicted_vs_measured(ext, (9, 4, 202, 302))["delta_px"]
    assert d["x0"] == pytest.approx(-1.4) and d["x1"] == pytest.approx(1.4)
    assert rt._predicted_vs_measured(ext, None)["measured_px"] is None
