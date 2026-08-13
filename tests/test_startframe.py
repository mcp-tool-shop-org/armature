"""Tests for the start frame's geometry and its andon.

Every fixture here builds the WRONG implementation's answer and shows it failing, because
the failures this module exists to catch are all silent: a cropped conditioning image
renders, saves, uploads and generates without a single error anywhere.
"""

import math

import numpy as np
import pytest

from armature_core import framing, startframe as SF


LENS, SENSOR, W, H = 50.0, 36.0, 832, 480
AZ, EL = 225.0, 6.0


# --------------------------------------------------------------- framing_cloud


def test_the_reduction_keeps_every_axis_extreme_a_stride_would_drop():
    """The dangerous reduction is the obvious one.

    The cloud below puts its topmost vertex at index 1, which every stride > 1 skips. A
    reduction that merely strided would hand `solve_camera` a figure shorter than the real
    one; the solve would then fit that shorter figure to the requested height fraction and
    the real one would come out too large — with nothing erroring, because a slightly
    oversized figure is a perfectly well-formed render.
    """
    pts = [(0.0, 0.0, 0.0)] * 40
    pts[1] = (0.0, 0.0, 9.0)          # the top of the head, at an index a stride skips
    pts[7] = (-5.0, 0.0, 0.0)         # the far hand
    pts[38] = (5.0, 0.0, 0.0)
    out = SF.framing_cloud(pts, cap=8)

    assert len(out) <= 8
    for axis in (0, 1, 2):
        assert max(p[axis] for p in out) == max(p[axis] for p in pts)
        assert min(p[axis] for p in out) == min(p[axis] for p in pts)

    strided = pts[::len(pts) // 8]
    assert max(p[2] for p in strided) != max(p[2] for p in pts), (
        "the fixture no longer demonstrates the failure it was built to demonstrate")


def test_the_reduction_is_deterministic():
    """A composition that changes between two runs of the same tool is not a recipe."""
    pts = [(math.sin(i), math.cos(i), i * 0.01) for i in range(5000)]
    assert SF.framing_cloud(pts, cap=200) == SF.framing_cloud(pts, cap=200)


def test_a_cloud_under_the_cap_is_returned_whole():
    pts = [(float(i), 0.0, 0.0) for i in range(11)]
    assert SF.framing_cloud(pts, cap=1500) == pts


def test_an_empty_cloud_raises_rather_than_framing_the_origin():
    with pytest.raises(SF.StartFrameGate):
        SF.framing_cloud([])


# ---------------------------------------------------------- silhouette_extent


def _extent_of(points, target=(0.0, 0.0, 0.0), radius=4.0):
    return SF.silhouette_extent(points, target, radius, AZ, EL, LENS, SENSOR, W, H)


def test_the_extent_is_unclipped_and_that_is_the_whole_point():
    """A vertex outside the frame must come back OUTSIDE it.

    `blender_scene.projected_bbox_px` clips to the frame before taking bounds, which is
    correct for comparing against a rendered mask and catastrophic here: an arm 200 px off
    the left edge returns `x0 = 0`, and a gate reading that number sees a figure sitting
    neatly against the border. This test fails the moment somebody clamps.
    """
    target = (0.0, 0.0, 0.0)
    inside = _extent_of([target], target)
    assert inside["x0"] == pytest.approx(W * 0.5, abs=1e-6)

    # A point pushed hard along screen-right of the same camera.
    pos = framing.camera_position(target, 4.0, EL, AZ)
    right, up, _ = framing.camera_basis(target, pos)
    far = tuple(target[i] - right[i] * 6.0 for i in range(3))
    out = _extent_of([target, far], target)
    assert out["x0"] < 0.0, "an off-frame point was clamped into the frame"


def test_a_point_behind_the_camera_is_counted_not_projected():
    """The perspective divide mirrors a point behind the lens into frame. Including it
    would move the bounds to somewhere the figure never was, and the bounds would look
    entirely reasonable."""
    target = (0.0, 0.0, 0.0)
    behind = framing.camera_position(target, 8.0, EL, AZ)
    ext = _extent_of([target, behind], target)
    assert ext["n_behind"] == 1
    assert ext["n_points"] == 2


def test_all_points_behind_the_camera_raises():
    target = (0.0, 0.0, 0.0)
    behind = framing.camera_position(target, 8.0, EL, AZ)
    with pytest.raises(SF.StartFrameGate):
        _extent_of([behind], target)


# ------------------------------------------------------------------ gate_whole


def test_the_gate_passes_a_figure_with_margin_and_reports_the_smallest_one():
    ext = {"x0": 300.0, "x1": 520.0, "y0": 24.0, "y1": 456.0, "n_behind": 0,
           "n_points": 100}
    ev = SF.gate_whole(ext, W, H, margin_px=8)
    assert ev["margins_px"]["top"] == pytest.approx(24.0)
    assert ev["margins_px"]["bottom"] == pytest.approx(23.0)
    assert ev["height_frac"] == pytest.approx(0.9, abs=1e-9)


@pytest.mark.parametrize("side,ext", [
    ("top", {"x0": 300.0, "x1": 520.0, "y0": -14.0, "y1": 450.0}),
    ("bottom", {"x0": 300.0, "x1": 520.0, "y0": 20.0, "y1": 479.0}),
    ("left", {"x0": -2.0, "x1": 520.0, "y0": 20.0, "y1": 450.0}),
    ("right", {"x0": 300.0, "x1": 831.0, "y0": 20.0, "y1": 450.0}),
])
def test_the_gate_fires_on_a_body_cut_by_any_border(side, ext):
    """Four separate fixtures rather than one, because "the figure is in frame" is a
    conjunction of four clauses and a gate that only ever saw one of them fail would be
    a gate nobody had checked the other three of."""
    ext = dict(ext, n_behind=0, n_points=100)
    with pytest.raises(SF.StartFrameGate) as exc:
        SF.gate_whole(ext, W, H, margin_px=8)
    assert side in str(exc.value)


def test_the_gate_fires_when_anything_is_behind_the_camera():
    ext = {"x0": 300.0, "x1": 520.0, "y0": 24.0, "y1": 456.0, "n_behind": 3,
           "n_points": 100}
    with pytest.raises(SF.StartFrameGate):
        SF.gate_whole(ext, W, H, margin_px=8)


def test_the_landmark_cloud_can_pass_while_the_silhouette_does_not():
    """The measurement this module exists for, made executable.

    A landmark cloud is a handful of joint centres; the silhouette is the body around them.
    Here `solve_camera` composes on the landmarks, reports `in_frame`, and the real
    silhouette is over the top of the frame — which is the E11 failure mode exactly: the
    composition looks solved and the conditioning image is of a decapitated character.
    """
    landmarks = [(0.0, 0.0, z) for z in (0.0, 0.4, 0.8, 1.2, 1.5)]
    sol = framing.solve_camera(landmarks, landmarks, AZ, EL, LENS, SENSOR, W, H,
                               height_frac=0.98, end_x_frac=0.5, target_y_frac=0.5)
    assert sol["in_frame"], "the fixture must start from a framing that reports itself fine"

    silhouette = landmarks + [(0.0, 0.0, 1.75), (0.0, 0.0, -0.2)]   # skull cap, heels
    ext = SF.silhouette_extent(silhouette, sol["target"], sol["radius"], AZ, EL,
                               LENS, SENSOR, W, H)
    with pytest.raises(SF.StartFrameGate):
        SF.gate_whole(ext, W, H, margin_px=8)


# -------------------------------------------------------------------- mask_bbox


def test_an_empty_mask_is_none_rather_than_a_zero_bbox():
    """A render nobody is in must not report a bbox at the origin: `(0,0,0,0)` is a
    1-pixel figure in the top-left corner as far as any consumer can tell."""
    assert SF.mask_bbox([[False] * 4 for _ in range(3)]) is None


def test_the_mask_bbox_is_inclusive_and_row_major():
    rows = [
        [False, False, False, False],
        [False, True, True, False],
        [False, False, True, False],
    ]
    assert SF.mask_bbox(rows) == (1, 1, 2, 2)


# ============================================================================ THE ALPHA LAW
# The Director's ruling, 2026-08-12: authored image inputs carry alpha, never a baked void,
# and the RGB each route submits is a deliberate, recorded choice. Every fixture below is a
# way the law reads as satisfied in a provenance file while being violated in the render.

class TestCompositeColour:

    def test_a_named_linear_colour_parses(self):
        assert SF.composite_colour("0.035,0.022,0.014") == (0.035, 0.022, 0.014)
        assert SF.composite_colour(" 0.0 , 0.0 , 0.0 ") == (0.0, 0.0, 0.0)

    def test_there_is_no_default_because_a_default_is_how_the_void_got_in(self):
        """The grey studio was never chosen by anyone, which is why nobody could find the
        choice to argue with. An unnamed colour halts the render."""
        for empty in (None, "", "   "):
            with pytest.raises(SF.AlphaGate) as exc:
                SF.composite_colour(empty)
            assert "NAMED background" in str(exc.value)

    def test_srgb_bytes_are_refused_rather_than_rendered(self):
        """`52,41,31` is the shape a human reaches for first and it is not linear. Rendered,
        it clamps to a blown white void — the exact failure the law ends."""
        with pytest.raises(SF.AlphaGate) as exc:
            SF.composite_colour("52,41,31")
        assert "blown white void" in str(exc.value)
        assert exc.value.evidence["supplied"] == [52.0, 41.0, 31.0]

    @pytest.mark.parametrize("bad", ["0.1,0.2", "0.1,0.2,0.3,0.4", "0.1,dim,0.3", ","])
    def test_a_malformed_colour_halts(self, bad):
        with pytest.raises(SF.AlphaGate):
            SF.composite_colour(bad)


class TestGateAlpha:

    OK = dict(composite_rgb=(0.035, 0.022, 0.014), why="dim warm bar interior")

    def test_a_normal_render_passes_and_reports_its_fraction(self):
        ev = SF.gate_alpha(0.42, **self.OK)
        assert ev["transparent_fraction"] == 0.42
        assert ev["opaque_fraction"] == pytest.approx(0.58)
        assert "alpha authored" in ev["verdict"]

    def test_a_fully_opaque_master_is_a_baked_void_with_a_fourth_channel(self):
        """THE clause. If film_transparent silently stops taking effect, the file still
        opens, still has the right dimensions, still contains the figure, and Gate WHOLE and
        Gate COVERAGE both pass on it. Only this notices."""
        with pytest.raises(SF.AlphaGate) as exc:
            SF.gate_alpha(0.0, **self.OK)
        assert "baked void with a fourth channel" in str(exc.value)
        assert exc.value.evidence["transparent_fraction"] == 0.0

    def test_a_fully_transparent_master_is_caught_from_the_other_side(self):
        """The opposite failure, which the same andon must bound: nothing rendered at all
        composites to a flat field of the chosen colour and conditions on an empty picture."""
        with pytest.raises(SF.AlphaGate) as exc:
            SF.gate_alpha(1.0, **self.OK)
        assert "ENTIRELY transparent" in str(exc.value)

    def test_a_colour_chosen_without_a_reason_halts(self):
        """'Deliberate and RECORDED' is two requirements. A choice nobody wrote down is
        indistinguishable from a leftover a year later."""
        with pytest.raises(SF.AlphaGate) as exc:
            SF.gate_alpha(0.4, composite_rgb=(0.0, 0.0, 0.0), why=None)
        assert "not explained" in str(exc.value)

    def test_the_evidence_carries_the_choice_even_when_it_raises(self):
        """A gate that hides what it saw makes the next reader re-measure it."""
        with pytest.raises(SF.AlphaGate) as exc:
            SF.gate_alpha(0.0, **self.OK)
        ev = exc.value.evidence
        assert ev["composite_linear_rgb"] == [0.035, 0.022, 0.014]
        assert ev["composite_why"] == "dim warm bar interior"


# ========================================================================= THE PLATE
# E12: the void becomes a picture of a world. Everything below is a way that picture fails
# to arrive while every other check in the module still passes.

class TestCoverFit:

    def test_the_measured_case_this_was_built_for(self):
        """E11 wave 1 painted 832x480; wave 3's frame — E12's — is 1024x576. The aspects
        differ (1.733 vs 1.778), so a still lifted from one cannot simply be scaled into
        the other, and this is the arithmetic that says what it costs."""
        g = SF.cover_fit(832, 480, 1024, 576)
        assert g["resized_size"] == [1024, 591]
        assert g["crop_box"] == [0, 7, 1024, 583]
        assert g["scale"] == pytest.approx(1024 / 832)
        assert g["dropped_px_resized"] == {"x": 0, "y": 15}
        assert g["pads"] is False

    @pytest.mark.parametrize("sw,sh", [
        (832, 480), (1920, 1080), (640, 640), (1024, 576), (3000, 1000), (100, 4000),
        (17, 13), (1, 1), (1023, 575), (1025, 577),
    ])
    def test_it_never_pads_whatever_the_aspect(self, sw, sh):
        """THE promise, over a sweep rather than one example. A resized image even one pixel
        short of the target leaves part of the crop box outside it, and the caller fills
        that strip with something nobody chose — which is the letterbox disease this fit
        exists to avoid."""
        w, h = 1024, 576
        g = SF.cover_fit(sw, sh, w, h)
        nw, nh = g["resized_size"]
        x0, y0, x1, y1 = g["crop_box"]
        assert nw >= w and nh >= h, "the resize left a gap the caller would have to pad"
        assert 0 <= x0 and x1 <= nw, "the crop box reads columns outside the resized image"
        assert 0 <= y0 and y1 <= nh, "the crop box reads rows outside the resized image"
        assert (x1 - x0, y1 - y0) == (w, h)

    def test_a_source_already_at_the_frames_aspect_is_not_cropped(self):
        """When nothing needs to be discarded, nothing is: a fit that always cropped a
        little would quietly reframe every plate that was already correct."""
        g = SF.cover_fit(512, 288, 1024, 576)
        assert g["crop_offset"] == [0, 0]
        assert g["dropped_px_resized"] == {"x": 0, "y": 0}
        assert g["kept_fraction_of_source_area"] == pytest.approx(1.0)

    def test_a_downscale_is_reported_as_one(self):
        """The caller picks its resampling filter off this flag; INTER_CUBIC on a 4x
        downscale is how a plate acquires aliasing nobody asked for."""
        assert SF.cover_fit(4096, 2304, 1024, 576)["upscaled"] is False
        assert SF.cover_fit(832, 480, 1024, 576)["upscaled"] is True

    def test_what_was_dropped_is_reported_in_source_pixels_too(self):
        """Resized pixels are the tool's units; source pixels are the ones a human looking
        at the original can find."""
        g = SF.cover_fit(1920, 1080, 1024, 576)
        assert g["dropped_px_source"]["x"] == pytest.approx(0.0, abs=1e-9)
        assert g["dropped_px_source"]["y"] == pytest.approx(0.0, abs=1e-9)
        g = SF.cover_fit(1000, 1000, 1024, 576)
        assert g["dropped_px_source"]["y"] == pytest.approx(1000 - 576 / 1.024, abs=1e-6)

    def test_the_default_anchor_cuts_exactly_what_it_cut_before_anchors_existed(self):
        """The anchor arrived after a plate had already been fitted with a centred crop.
        A default that shifted the box by a pixel would silently change every recipe that
        predates it, and nothing would report the difference."""
        assert (SF.cover_fit(832, 480, 1024, 576)["crop_box"]
                == SF.cover_fit(832, 480, 1024, 576, 0.5, 0.5)["crop_box"] == [0, 7, 1024, 583])

    @pytest.mark.parametrize("anchor_y,oy", [(0.0, 0), (0.5, 53), (1.0, 107)])
    def test_the_anchor_places_the_crop_on_the_measured_plate(self, anchor_y, oy):
        """The measured case: the Director's 1248x832 plate into E12's 1024x576 leaves 107
        rows of overhang, and where those rows come off decides which part of the picture is
        inside the band and which is discarded entirely."""
        g = SF.cover_fit(1248, 832, 1024, 576, anchor_y=anchor_y)
        assert g["resized_size"] == [1024, 683]
        assert g["crop_offset"][1] == oy
        assert g["crop_box"] == [0, oy, 1024, oy + 576]
        assert g["anchor"] == [0.5, anchor_y]

    @pytest.mark.parametrize("anchor_y", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_no_anchor_puts_the_box_outside_the_resized_image(self, anchor_y):
        """The promise the anchor must not break. At 1.0 a rounding-up would read one row
        past the bottom of the image, and the caller would pad it — the one thing this
        function exists to make impossible."""
        for sw, sh in [(1248, 832), (832, 480), (1000, 1000), (3000, 1001)]:
            g = SF.cover_fit(sw, sh, 1024, 576, anchor_y=anchor_y)
            nw, nh = g["resized_size"]
            x0, y0, x1, y1 = g["crop_box"]
            assert 0 <= y0 and y1 <= nh and 0 <= x0 and x1 <= nw

    @pytest.mark.parametrize("ax,ay", [(-0.1, 0.5), (0.5, 1.1), (2.0, 0.0)])
    def test_an_anchor_outside_the_range_halts(self, ax, ay):
        with pytest.raises(SF.BackdropGate):
            SF.cover_fit(1248, 832, 1024, 576, anchor_x=ax, anchor_y=ay)

    def test_the_band_map_follows_the_anchor(self):
        """`band_source_rows` is what "the band carries" is measured on, so it has to move
        with the anchor. If it did not, a bottom-anchored plate would be described by the
        content of its centre — a claim about the wrong pixels."""
        top = SF.cover_fit(1248, 832, 1024, 576, anchor_y=0.0)
        bot = SF.cover_fit(1248, 832, 1024, 576, anchor_y=1.0)
        assert SF.band_source_rows((0, 182), top)[0] == pytest.approx(0.0)
        assert SF.band_source_rows((0, 182), top)[1] == pytest.approx(221.8, abs=0.1)
        assert SF.band_source_rows((0, 182), bot)[0] == pytest.approx(130.4, abs=0.1)
        assert SF.band_source_rows((0, 182), bot)[1] == pytest.approx(352.2, abs=0.1)

    @pytest.mark.parametrize("sw,sh", [(0, 480), (832, 0), (-1, 480), (832, -1)])
    def test_a_degenerate_source_halts(self, sw, sh):
        with pytest.raises(SF.BackdropGate):
            SF.cover_fit(sw, sh, 1024, 576)

    @pytest.mark.parametrize("w,h", [(0, 576), (1024, 0)])
    def test_a_degenerate_target_halts(self, w, h):
        with pytest.raises(SF.BackdropGate):
            SF.cover_fit(832, 480, w, h)


class TestShadowLayer:
    """The authored shadow layer — A2w's treatment, and the branch a measurement forced.

    `is_shadow_catcher` exists on the object in Blender 5.2 and EEVEE ignores it: a catcher
    render came back byte-identical to an ordinary opaque floor. So the shadow is derived,
    and derived arithmetic is arithmetic that can be wrong in silence — a shadow of the
    wrong density still looks like a shadow.
    """

    def test_the_transfer_functions_round_trip(self):
        a = np.linspace(0.0, 1.0, 257)
        assert SF.linear_to_srgb(SF.srgb_to_linear(a)) == pytest.approx(a, abs=1e-9)

    def test_the_encoding_is_the_piecewise_standard_not_a_gamma_power(self):
        """Measured on this build: `Image.pixels` hands back byte 128 as 0.50196, so arrays
        arrive sRGB-encoded and the conversion has to be the real one. A 2.2 power is wrong
        by several levels in the shadows, which is exactly where a shadow layer lives."""
        assert float(SF.srgb_to_linear(128 / 255.0)) == pytest.approx(0.21586, abs=1e-4)
        assert float(SF.srgb_to_linear(0.04)) == pytest.approx(0.04 / 12.92, abs=1e-12)

    def test_an_unshadowed_floor_produces_no_shadow_at_all(self):
        """The identity case. If the figure casts nothing, the ratio is 1 everywhere and the
        plate comes back untouched — a layer that darkened a little regardless would tint
        every A2w frame with no one able to say why."""
        lit = np.full((8, 8, 3), 0.5)
        assert SF.shadow_ratio(lit.copy(), lit) == pytest.approx(np.ones((8, 8, 3)))
        plate = np.random.default_rng(3).random((8, 8, 3))
        assert SF.apply_shadow(plate, np.ones((8, 8, 3))) == pytest.approx(plate, abs=1e-9)

    def test_the_ratio_is_taken_in_linear_and_that_changes_the_density(self):
        """THE clause the colour space matters for. A floor at linear 0.4 shadowed to linear
        0.1 is a quarter of the light; the same two values compared in the ENCODED domain
        give 0.66/0.35 = 0.53, a shadow half as deep. Both look like shadows."""
        lit = SF.linear_to_srgb(np.full((4, 4, 3), 0.40))
        cast = SF.linear_to_srgb(np.full((4, 4, 3), 0.10))
        assert SF.shadow_ratio(cast, lit) == pytest.approx(np.full((4, 4, 3), 0.25), abs=1e-6)
        naive = np.asarray(cast) / np.asarray(lit)
        assert abs(float(naive.mean()) - 0.25) > 0.2, (
            "the fixture no longer demonstrates that the domain matters")

    def test_a_ratio_above_one_is_clamped_because_a_shadow_cannot_add_light(self):
        lit = np.full((4, 4, 3), 0.3)
        cast = np.full((4, 4, 3), 0.9)
        assert SF.shadow_ratio(cast, lit).max() == pytest.approx(1.0)

    def test_near_black_reference_pixels_are_held_unshadowed_not_divided(self):
        """Dividing two near-black pixels turns render noise into bright speckle. A shadow
        layer that invents light in the dark corners is worse than no shadow layer, so those
        pixels are held at 1 and the fact is recorded."""
        lit = np.zeros((4, 4, 3))
        cast = np.zeros((4, 4, 3))
        cast[0, 0] = 0.02
        r = SF.shadow_ratio(cast, lit)
        assert r == pytest.approx(np.ones((4, 4, 3)))

    def test_the_shadow_darkens_the_plate_and_never_brightens_it(self):
        rng = np.random.default_rng(11)
        plate = rng.random((16, 16, 3))
        ratio = rng.random((16, 16, 3))
        out = SF.apply_shadow(plate, ratio)
        assert (out <= plate + 1e-9).all()
        assert out.min() >= 0.0 and out.max() <= 1.0

    def test_a_fully_occluded_pixel_goes_to_black(self):
        assert SF.apply_shadow(np.full((2, 2, 3), 0.8),
                               np.zeros((2, 2, 3))) == pytest.approx(np.zeros((2, 2, 3)))


class TestGateBackdrop:

    OK = dict(void_vs_plate_255=0.4, plate_vs_flat_255=61.0, transparent_fraction=0.296,
              why="the picked bar still", tol_255=2.0, min_separation_255=4.0)

    def test_a_plate_that_arrived_passes_and_reports_both_numbers(self):
        ev = SF.gate_backdrop(**self.OK)
        assert ev["void_vs_plate_255"] == 0.4
        assert ev["plate_vs_flat_255"] == 61.0
        assert "the plate is behind the performer" in ev["verdict"]

    def test_a_compositor_that_never_wired_is_caught(self):
        """THE clause. The submitted file still opens, is still the right size, still holds
        the whole performer, still passes WHOLE, ALPHA and COVERAGE — and behind him is the
        void the plate was chosen to end, with a plate recorded in the provenance."""
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, void_vs_plate_255=61.0))
        assert "is not the plate this record names" in str(exc.value)
        assert exc.value.evidence["void_vs_plate_255"] == 61.0

    def test_a_plate_indistinguishable_from_the_void_is_refused_as_vacuous(self):
        """The vacuity guard. If the plate matches the flat fallback over the region being
        measured, the first number is near zero whether the compositing worked or not — so
        a PASS would prove nothing, and a check that cannot fail is not a check."""
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, plate_vs_flat_255=0.2))
        assert "a PASS would prove nothing" in str(exc.value)

    def test_the_vacuity_guard_runs_before_the_match_check(self):
        """Order matters: a run where BOTH are near zero is the un-wired compositor with a
        flat plate, and reporting it as a match failure would send the next reader looking
        at the compositor's arithmetic instead of at the plate."""
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, void_vs_plate_255=99.0, plate_vs_flat_255=0.0))
        assert "a PASS would prove nothing" in str(exc.value)

    def test_a_master_with_no_transparent_region_halts_rather_than_passing_vacuously(self):
        """Gate ALPHA bounds this too, from its own side. Here it matters for a different
        reason: with no void there is no region to measure, so the mean would be taken over
        an empty set and every threshold below would be satisfied by nothing at all."""
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, transparent_fraction=0.0))
        assert "a check that cannot fail" in str(exc.value)

    def test_a_plate_chosen_without_a_reason_halts(self):
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, why=None))
        assert "not explained" in str(exc.value)

    def test_the_thresholds_are_the_callers_and_ride_the_evidence(self):
        """A gate whose numbers live only in the tool makes the next reader open the tool
        to find out what it compared against."""
        ev = SF.gate_backdrop(**dict(self.OK, tol_255=0.5, min_separation_255=60.0))
        assert ev["tol_255"] == 0.5 and ev["min_separation_255"] == 60.0
        with pytest.raises(SF.BackdropGate):
            SF.gate_backdrop(**dict(self.OK, tol_255=0.3))

    def test_the_evidence_carries_the_plate_even_when_it_raises(self):
        with pytest.raises(SF.BackdropGate) as exc:
            SF.gate_backdrop(**dict(self.OK, void_vs_plate_255=61.0,
                                    plate="p.png", plate_sha256="abc123"))
        assert exc.value.evidence["plate"] == "p.png"
        assert exc.value.evidence["plate_sha256"] == "abc123"
