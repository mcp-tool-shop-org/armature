"""The turnaround set: which azimuths, and whether each view really carries alpha.

No bpy. A turnaround is a reference kit — the thing a route is *handed* when it must
bind identity — so the two questions this module answers are the two that decide whether
the kit is usable at all:

    which azimuths does the set stand on, and does each view carry a real alpha channel?

**Why the alpha question needs its own andon, per view.** `startframe.gate_alpha` already
makes this argument for a single frame and it is the same argument here, with one addition
a per-frame gate cannot make: a turnaround fails *per view*. Nothing else in the render
path can tell a genuine RGBA render from a baked void with a fourth channel full of 255s —
the files open, the dimensions are right, the figure is in every one of them, and a contact
sheet of eight baked views looks exactly like a contact sheet of eight authored ones. That
is not hypothetical: the set this module exists to replace
(`E:\\AI\\training\\facet_E33\\turn_final\\`) is eight RGBA PNGs whose alpha extrema are
(255, 255) on all eight, with a flat grey void baked into the RGB. It was consumed as a
reference set and nothing anywhere reported a defect.

**The andon goes on the direction the invariant does not bound.** Both directions, because
each is silent in the other's presence:

* `alpha_min == 255` — no pixel is transparent. This is the baked-void defect exactly, and
  it is what the Director's ruling of 2026-08-12 forbids.
* `alpha_max < 255` — no pixel is opaque. A render nobody is in, or one whose subject
  material went transparent, is well-formed, correctly sized, non-empty as a file, and
  carries a beautifully varied alpha channel. A gate written only against the first clause
  passes it.

Both are structural facts about the extrema, not thresholds: neither can be tuned toward a
number by anyone who does not like the result. The opaque fraction *is* a magnitude and is
therefore **reported and never gated** — no calibrated threshold for how much of a portrait
frame a mannequin should fill exists on this rig, and inventing one here would be a pass
condition the experiment could move.
"""

import math

from .errors import ArmatureError, GateFailure
from .parts import require_finite


class TurnaroundGate(GateFailure):
    """A turnaround set is not the whole set of distinct views it claims to be."""

    gate = "TURN"


class TurnaroundPlanRefusal(ArmatureError):
    """A projection plan was asked for that cannot be composed. S05.

    **Not an andon, and deliberately not a `GateFailure`.** The four gates in this repo
    judge a *rendered artifact*; this refuses to compose the plan at all, before a camera
    exists, so giving it a gate letter would put a fifth andon into the vocabulary the
    manifests and reports use for measured views. It `raise`s for the same reason they do —
    an `assert` is deleted by `-O` — and it rides the same optimization probe.

    **Why it exists when the parser already refuses.** `render_turnaround`'s parser bounds
    callers who come through the command line. Nothing bounds a caller who imports
    `projection_plan` directly, and that caller is the one this repo keeps commissioning:
    the plan is the documented branch object, so a future tool asking it for a pinned
    *perspective* run would get a perspective plan with the pin silently dropped, render a
    perfectly well-formed turnaround, and record no shared scale at all. Silently ignoring
    the one number a run was pinned on is the exact disease the pin's manifest clause is
    written against, and the parser cannot reach that caller.
    """


class TurnaroundAlphaGate(TurnaroundGate):
    """A turnaround view does not carry the alpha the authored-RGBA law requires."""

    gate = "ALPHA"


class TurnaroundCropGate(TurnaroundGate):
    """A turnaround view's subject runs off the edge of its own cell. S04's andon.

    **The direction the scale solve does not bound.** The shared `ortho_scale` is solved
    from `silhouette_extent` over the sampled azimuths, and that extent is measured on a
    cloud `framing_cloud` has already decimated to its cap. So the solve is fitted to a
    *lower bound* on the silhouette: geometry between two surviving samples, at an azimuth
    where the widest part of the figure falls between strides, projects further than
    anything the solve ever saw. The scale then comes out slightly too tight and the cell
    is cropped.

    Every other check passes on that cell. Gate ALPHA passes — a cropped figure has
    transparent pixels and opaque ones. Gate TURN passes — the eight views are still
    distinct. Gate WHOLE passes *by construction*, because it reads the same decimated
    projection the solve was fitted to, so it is the one gate structurally incapable of
    seeing this. What is different about CROP is where it looks: at the **rendered alpha**,
    which is the only place the real silhouette exists.
    """

    gate = "CROP"


#: Alpha is measured in 8-bit counts, so the two saturated values are the two that matter.
OPAQUE = 255

#: Below this (on a 0..1 alpha plane) a pixel counts as transparent for the reported
#: fraction. The same threshold `render_start_frame` uses, so the two numbers compare.
TRANSPARENT_BELOW = 0.5


def orbit_azimuths(n_views, start_deg, sweep_deg):
    """The azimuth of each view, in order.

    `sweep_deg` is the angle of the **closed path**: view `n_views` would coincide with
    view 0, so a 360-degree sweep does not render the first view twice. This is the
    convention `blender_scene.orbit_azimuth` states, restated here because that module
    imports bpy and this one must not — `test_turnaround.py` pins the two formulas
    together so the duplication cannot drift silently.
    """
    n = int(n_views)
    if n < 1:
        raise TurnaroundGate(
            f"a turnaround of {n} view(s) is not a turnaround",
            {"clause": "no_views",
             "gate": "TURN", "andon": "TurnaroundGate", "n_views": n})
    out = [float(start_deg) + float(sweep_deg) * (i / float(n)) for i in range(n)]
    # WAVE 22, F-99e5de1a — the mechanism that produces a NON-ADJACENT revisit, bounded at
    # the function that produces it. `orbit_azimuths(8, 0, 720)` returned
    # `[0, 90, 180, 270, 360, 450, 540, 630]` — the same four azimuths twice, at stride 4 —
    # and `render_turnaround` bounds `--sweep` for FINITENESS only, so a doubled sweep wrote
    # eight well-formed RGBA files of four pictures with eight different digests. Gate TURN
    # ranged over ADJACENT pairs, and a revisit at stride 4 is never adjacent.
    #
    # Keyed on the azimuth MODULO a full turn, because 0 and 360 point the camera at the same
    # place. A NaN azimuth is not compared here (every comparison against it is False, so no
    # duplicate is claimed); `--sweep` and `--azimuth-start` are bounded for finiteness at
    # the parser, which is the complementary half.
    # CORRECTED IN PLACE, WAVE 25 (F-8361eff3), with the measurement that overturned the
    # old sentence. The refusal below used to end "... and Gate TURN's pixel clause ranges
    # over adjacent pairs — a revisit at stride {n} is never adjacent", which was the reason
    # this bound was needed and stopped being true in the SAME COMMIT that landed it:
    # F-99e5de1a shipped this refusal and `_pixel_pairs`' `identical_anywhere` walk and
    # `gate_set_distinct`'s `views_identical_in_pixels_anywhere` clause together. MEASURED
    # in this worktree on `580af47`: `orbit_azimuths(8, 0, 720)` raises this clause carrying
    # that sentence, while `gate_set_distinct` over eight 64x64x4 planes with view 4 a copy
    # of view 0 and eight distinct sha256 values RAISES `views_identical_in_pixels_anywhere`
    # with `pairs_identical_in_pixels_anywhere: [[0, 4]]` over
    # `n_unordered_pairs_compared: 28`. A triage reading the old halt line would conclude
    # the downstream gate cannot see a revisit and go looking for a second bound that
    # already exists.
    #
    # The STRIDE arithmetic was wrong too, measured in the same run: `n // len(seen)` printed
    # "stride 2" for `orbit_azimuths(8, 0, 720)`, whose coinciding views are 0 and 4. That
    # quotient is how many TIMES each direction is visited; the stride between two views
    # pointing the same way is `len(seen)`. Both halves are corrected here rather than
    # deleted, because the correction is the useful part.
    seen = {a % 360.0 for a in out}
    if len(seen) != n:
        raise TurnaroundGate(
            f"a sweep of {sweep_deg} over {n} view(s) revisits an azimuth: the plan names "
            f"{len(seen)} distinct direction(s) for {n} views, so the camera returns to a "
            f"place it has already photographed — views {len(seen)} apart point the same "
            f"way, and each direction is photographed {n // max(len(seen), 1)} times. The "
            f"run writes {n} well-formed RGBA files with {n} different digests over "
            f"{len(seen)} pictures and every per-view gate passes on every one of them. "
            f"Gate TURN's set clause refuses a pixel-identical pair at ANY distance "
            f"(`views_identical_in_pixels_anywhere`), so it would catch this too — after "
            f"{n} renders have been written and their time spent. This bound refuses the "
            f"PLAN, before the first file exists; the two are complementary, not one "
            f"compensating for a gap in the other",
            {"gate": "TURN", "andon": "TurnaroundGate",
             "clause": "sweep_revisits_an_azimuth", "n_views": n,
             "n_distinct_azimuths": len(seen), "start_deg": float(start_deg),
             "sweep_deg": float(sweep_deg),
             "revisit_stride": len(seen),
             "visits_per_direction": n // max(len(seen), 1),
             "azimuths": out[:16]})
    return out


#: The two projections a turnaround can stand on. `PERSPECTIVE` is the one the tool shipped
#: with; `ORTHOGRAPHIC` is S04's addition.
PERSPECTIVE = "PERSP"
ORTHOGRAPHIC = "ORTHO"

#: Where an ortho run's shared scale came from. S05. A manifest that records the NUMBER
#: without recording where it came from cannot be read: the same float means "this subject
#: was fitted to this frame" on one run and "a whole roster stands on this" on the next,
#: and only the second one may be retyped onto a different character.
SOLVED = "solved"
PINNED = "pinned"


def projection_plan(ortho, lens_mm, sensor_mm, ortho_scale_pin=None):
    """Which camera the run stands on, what is shared across its views, and where it
    came from.

    The whole branch between the two projections is this function, so that the claim "the
    perspective path is untouched when the flag is absent" is a property of one testable
    object rather than of a reader's careful eye over a render loop. **S05's pin lands in
    the same place for the same reason**: "the solved path is untouched when no pin is
    given" is then a property of this object too, not of a second careful reading.

    **The shared quantity is the point of the sprite path.** A perspective turnaround
    shares a *radius*, and each view's scale then varies a little with what happens to be
    near the lens. An ortho shot-set shares an *ortho_scale*, which is the frame's world
    span itself — so a millimetre of character is the same number of pixels in every cell,
    which is what makes the cells a sheet rather than eight photographs.

    **What the pin adds is sharing across RUNS.** The solve shares one scale across the
    views of one subject, which is what a single character's sheet needs and is exactly
    wrong for a cast: solved per character, the nine-foot brute and the halfling are each
    fitted to the same frame height and come out the same size on the sheet, every cell
    correctly framed and the roster's whole point destroyed. A pinned scale is one recorded
    number every character in the cast is drawn against, so the relation between them
    survives into the sheet. Nothing about it is a better fit for any one subject — it is
    deliberately not fitted at all, which is why it is `used verbatim` and why the direction
    it does not bound (a pin too tight for its subject) is where Gate CROP already stands.

    **`--height-frac` does not participate in a pinned run**, and the plan says so rather
    than leaving a caller to infer it. There is no solve for a target height to target, so
    a manifest recording one would describe a fit that never happened.

    **The ortho plan carries no focal length, and that is the assertion, not an omission.**
    Blender keeps a `lens` value on an ORTHO camera and ignores it; a plan that passed one
    along would let a reader believe the lens still composes the shot.

    **The perspective branch RECORDS two camera numbers and bounded neither** (F-329a9555,
    wave 18, sibling carried). The ortho branch's pin is refused by name unless it is a
    finite positive world span, and twenty lines below it `float(lens_mm)` and
    `float(sensor_mm)` took any float at all — a NaN, a zero, or a negative — and wrote it
    into the plan a whole run is composed from. This branch divides by nothing, which is
    exactly why it stayed open: the division happens later, in `framing.half_fovs` and
    `blender_scene.auto_radius`, both of which now refuse. The plan refuses too, in the
    same words as its ortho sibling, so a caller that never reaches a projection still
    cannot record a camera that cannot compose a shot.
    """
    pinned = ortho_scale_pin is not None
    if pinned:
        if not ortho:
            # WAVE 22, F-4ce10f2a — THE RECEIPT. Both ortho raises were ONE-ARGUMENT raises
            # while the PERSPECTIVE sibling twenty lines below passed a literal evidence
            # dict with a `clause`. MEASURED on `e8263a3` through `render_turnaround`'s own
            # handler: an ortho pin of `nan`, of `-1.0`, and this
            # perspective-with-a-pin refusal each produced exit 2 and
            # `{"outcome": "REFUSED — the tool declined to proceed", "gate": null,
            #   "error": "TurnaroundPlanRefusal", "evidence": null}` — a typed refusal at
            # the right exit code carrying no receipt and no clause — while `lens_mm=nan`
            # on the same function produced exit 2 with a full evidence dict naming its
            # clause. An operator whose pinned turnaround halts could not key a triage on a
            # clause the way every wave-20 receipt reader does.
            #
            # `TurnaroundPlanRefusal` derives from `ArmatureError` and NOT from
            # `GateFailure`, so `tests/test_core_solver_evidence.py`'s derived evidence
            # census — which walks raises whose class resolves to a `GateFailure` subclass —
            # cannot see either site, which is why neither was red.
            raise TurnaroundPlanRefusal(
                f"an ortho_scale pin ({ortho_scale_pin!r}) was given for a PERSPECTIVE "
                "plan. There is no shared world span on the perspective path — the "
                "quantity shared there is the radius — so this plan would be composed with "
                "the pin dropped, and the run would render a perfectly well-formed "
                "turnaround that silently ignored the one number it was pinned on. A "
                "roster rendered that way is eight characters each framed to his own "
                "height, which is the failure the pin exists to prevent",
                {"gate": None, "andon": "TurnaroundPlanRefusal",
                 "clause": "ortho_scale_pin_on_a_perspective_plan",
                 "projection": PERSPECTIVE,
                 "ortho_scale_pin": repr(ortho_scale_pin)})
        # THE COERCION IS INSIDE THE GUARD (F-4ce10f2a, second half). `pin =
        # float(ortho_scale_pin)` ran ABOVE `if not (math.isfinite(pin) and pin > 0.0)`, so
        # a pin that is not a real number left the family entirely: measured through the
        # same handler, a string pin `'wide'` exited **1** as a bare `ValueError` and a list
        # pin `[1.0]` exited **1** as a bare `TypeError`, both recorded as "FAILED — an
        # unhandled error". A pin that is a bad NUMBER and a pin that is not a number at all
        # left by two different doors at two different exit codes, and neither carried a
        # clause. This is the idiom the perspective branch below already spells.
        try:
            pin = float(ortho_scale_pin)
        except (TypeError, ValueError):
            pin = float("nan")
        if not (math.isfinite(pin) and pin > 0.0):
            raise TurnaroundPlanRefusal(
                f"an ortho_scale pin of {ortho_scale_pin!r} is not a finite positive world "
                "span. A non-positive span collapses every point onto the frame centre and "
                "a non-finite one sends them nowhere at all; either way the render still "
                "saves as a well-formed, correctly-sized RGBA PNG. `ortho_half_spans` "
                "refuses <= 0 downstream but takes nan and inf, so this is the check that "
                "binds those",
                {"gate": None, "andon": "TurnaroundPlanRefusal",
                 "clause": "ortho_scale_pin_not_finite_and_positive",
                 "projection": ORTHOGRAPHIC,
                 "ortho_scale_pin": repr(ortho_scale_pin),
                 "ortho_scale_pin_as_read": pin})
    else:
        for name, value in (("lens_mm", lens_mm), ("sensor_mm", sensor_mm)):
            try:
                v = float(value)
            except (TypeError, ValueError):
                v = float("nan")
            if not (math.isfinite(v) and v > 0.0):
                raise TurnaroundPlanRefusal(
                    f"a PERSPECTIVE plan was asked for with {name}={value!r}, which is "
                    f"not a finite positive camera number. The plan records both numbers "
                    f"verbatim and a run is composed from what it records: a zero sensor "
                    f"divides, a NaN places the orbit camera at a NaN radius, and a "
                    f"NEGATIVE lens gives a negative half-FOV that point-mirrors every "
                    f"projected point about the frame centre while Gate WHOLE, Gate CROP "
                    f"and Gate ALPHA all still read a plausible box",
                    {"gate": None, "andon": "TurnaroundPlanRefusal",
                     "clause": f"{name}_not_finite_and_positive",
                     "projection": PERSPECTIVE, name: value})

    if ortho:
        return {
            "projection": ORTHOGRAPHIC,
            "blender_camera_type": "ORTHO",
            "solved": None if pinned else "ortho_scale",
            "shared_across_views": "ortho_scale",
            "ortho_scale_source": PINNED if pinned else SOLVED,
            "ortho_scale_pin": float(ortho_scale_pin) if pinned else None,
            "shared_across_runs": pinned,
            "height_frac_participates": not pinned,
            "lens_mm": None,
            "sensor_mm": None,
            "radius_role": ("standoff only — parallel projection makes screen size "
                            "independent of distance, so the radius has to be clipping-"
                            "safe and nothing else"),
        }
    return {
        "projection": PERSPECTIVE,
        "blender_camera_type": "PERSP",
        "solved": "radius",
        "shared_across_views": "radius",
        "ortho_scale_source": None,
        "ortho_scale_pin": None,
        "shared_across_runs": False,
        "height_frac_participates": True,
        "lens_mm": float(lens_mm),
        "sensor_mm": float(sensor_mm),
        "radius_role": "composes the shot — it sets how large the subject draws",
    }


def gate_view_crop(view_index, subject_bbox, width, height, path=None, alpha_threshold=None):
    """Gate CROP · ANDON, per view — the subject does not run off the edge of its cell.

    `subject_bbox` is the INCLUSIVE `(x0, y0, x1, y1)` pixel box of the rendered subject,
    measured off the written PNG's alpha channel, or `None` when no pixel is subject at
    all. See `TurnaroundCropGate` for why this has to be measured on rendered alpha and
    cannot be measured on the projection the scale was solved against.

    **Contact is derived from the box alone**, so the verdict has exactly one source. A
    second measurement (per-border pixel counts) computed off the same array would agree by
    construction and read like corroboration it never provided.

    Two clauses, and the first is a vacuity guard. A cell nobody rendered into has no box,
    touches no border, and would sail through a gate written only against contact — passing
    *because* the failure was total. Gate ALPHA catches that case in the tool, which is
    precisely why this gate must not depend on Gate ALPHA having run: a gate whose andon is
    load-bearing only in another gate's presence is not an andon.
    """
    w, h = int(width), int(height)
    ev = {
        "gate": "CROP", "andon": "TurnaroundCropGate",
        "view": int(view_index), "path": path,
        "resolution": [w, h], "subject_bbox_px": (list(subject_bbox)
                                                  if subject_bbox is not None else None),
        "alpha_threshold": alpha_threshold,
        "measured_on": "the rendered alpha channel of the written PNG",
    }
    if subject_bbox is None:
        # F-f7449bc9, wave 28: the two raises here shared one `ev` with no `clause`, so a
        # vacuous cell and a cropped figure wrote the same receipt shape. `gate_alpha`
        # carries the same fix and the same reasoning.
        ev["clause"] = "view_has_no_subject_pixels"
        raise TurnaroundCropGate(
            f"view {view_index} has no subject pixels at all, so whether it is cropped "
            "cannot be answered. A gate written only against border contact PASSES this "
            "cell — an empty frame touches no border — and passes it because the failure "
            "was complete rather than partial", ev)

    x0, y0, x1, y1 = (int(v) for v in subject_bbox)
    clearances = {"left": x0, "right": (w - 1) - x1, "top": y0, "bottom": (h - 1) - y1}
    ev["clearance_px"] = clearances
    ev["border_contact"] = {side: (c <= 0) for side, c in clearances.items()}
    ev["cropped"] = any(ev["border_contact"].values())

    touching = sorted(side for side, hit in ev["border_contact"].items() if hit)
    if touching:
        ev["clause"] = "subject_reaches_the_frame_border"
        raise TurnaroundCropGate(
            f"view {view_index}: the subject reaches the frame border on "
            + ", ".join(touching)
            + f" (bbox {x0},{y0}..{x1},{y1} in {w}x{h}). The shared scale was solved from "
              "a decimated projection, so a silhouette wider than the samples the solve "
              "saw crops here and nowhere else: Gate ALPHA passes on a cropped figure, "
              "Gate TURN passes on eight distinct cropped views, and Gate WHOLE passes "
              "because it reads the same decimated projection the solve was fitted to",
            ev)

    ev["verdict"] = (f"view {view_index} whole in its cell; tightest clearance "
                     f"{min(clearances.values())} px")
    return ev


def gate_view_alpha(view_index, alpha_min, alpha_max, transparent_fraction, path=None):
    """Gate ALPHA · ANDON, per view — this view is authored RGBA, not a baked void.

    Raises on either saturated extreme; reports the measured numbers either way, because
    "it carries alpha" and "it carries alpha on four pixels" are different facts about a
    reference view, and the second one is a warning for the Director's eye rather than a
    verdict this gate should invent.

    **A non-finite fraction is refused before either extreme is asked** (F-bf3dfb4e, wave
    12). This gate decides on `alpha_min`/`alpha_max` only, and wrote
    `float(transparent_fraction)` into its evidence AND into its verdict string with no
    check. Measured 2026-09-04: `gate_view_alpha(3, 0, 255, float('nan'))` RETURNED with
    `verdict = "view 3 authored RGBA; extrema (0, 255), nan of the frame transparent"` and
    `transparent_fraction: nan`; with `inf` the verdict read "inf of the frame
    transparent". The sibling on the start-frame route refuses the same value
    (`startframe.gate_alpha(nan, ...)` -> AlphaGate), so the two ALPHA gates on the two
    routes disagreed about what a measurement is — the wave-10 sweep that closed
    F-90122505 stayed inside `startframe.py` and this is the turnaround route's other
    alpha gate. `tools/render_turnaround.py::main` prints the same number to the console as
    the per-view summary an executor reads. Through `parts.require_finite` with
    `positive=False`, because a transparent fraction may legitimately be 0.0 — one
    implementation of the NaN family, never a second `isfinite`.
    """
    lo, hi = int(alpha_min), int(alpha_max)
    ev = {
        "gate": "ALPHA", "andon": "TurnaroundAlphaGate",
        "view": int(view_index), "path": path,
        "alpha_extrema": [lo, hi],
    }
    require_finite("transparent_fraction", transparent_fraction, TurnaroundAlphaGate, ev,
                   positive=False)
    ev.update({
        "transparent_fraction": float(transparent_fraction),
        "opaque_fraction": 1.0 - float(transparent_fraction),
        "note": ("film_transparent makes the world background alpha=0 while the subject's "
                 "own geometry stays opaque, so a solid figure standing in a transparent "
                 "field is the expected shape"),
    })
    if lo >= OPAQUE:
        # F-f7449bc9, wave 28 — see `gate_view_crop` above and `startframe.gate_alpha`.
        ev["clause"] = "view_carries_no_transparent_pixel"
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is transparent, "
            "so this is not an RGBA render — it is a baked void with a fourth channel. "
            "`film_transparent` did not take effect, and every check after this one "
            "passes on the file anyway: it opens, it is the right size, the figure is in "
            "it, and a contact sheet cannot tell it from an authored view", ev)
    if hi < OPAQUE:
        ev["clause"] = "view_carries_no_opaque_pixel"
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is opaque, so "
            "nothing solid was rendered into this view. The file is well-formed, "
            "correctly sized, non-empty, and its alpha channel is richly varied — a gate "
            "written only against the flat-255 defect passes it", ev)
    ev["verdict"] = (f"view {view_index} authored RGBA; extrema ({lo}, {hi}), "
                     f"{float(transparent_fraction):.4f} of the frame transparent")
    return ev


#: Every `step`-th pixel in both axes before the comparison — `clipcompare.downsample`'s
#: stride, and the same reason: it preserves gross layout at a fraction of the cost, and
#: gross layout is exactly what a camera that did not move fails to change.
PIXEL_COMPARE_STRIDE = 8


def _read_plane(view_index, px):
    """`(strided_plane, None)` for one record's `pixels`, or `(None, reason)`.

    **It reports; it does not raise.** `np.asarray(px, dtype=np.float64)` raises whatever
    numpy raises — a `ValueError` on a ragged list, a `TypeError` on a string — and none
    of those is in the `ArmatureError` family, so the 21-tool halt contract records the
    render tool as "FAILED — an unhandled error" at exit 1 with no gate id, no clause and
    no evidence, after the eight views are already on disk. What happened is Gate TURN
    declining to read an input, which is a refusal at exit 2 (F-e207fd20, wave 16).

    The refusal is raised by `gate_set_distinct`, not here, because the evidence dict a
    gate raise carries has to be a literal the andon census can read in the same function
    (`tests/test_core_solver_evidence.evidence_dicts_missing`); a helper handed an `ev`
    parameter is a raise site that walk reports as `unreadable`.
    """
    try:
        import numpy as np
    except ImportError:                         # pragma: no cover - numpy is a hard dep
        return None, {"view": int(view_index), "clause": "numpy_unavailable",
                      "why": "numpy is not importable"}
    try:
        a = np.asarray(px, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        return None, {"view": int(view_index), "clause": "pixels_unreadable",
                      "why": f"{type(exc).__name__}: {exc}"}
    if a.ndim < 2:
        return None, {"view": int(view_index), "clause": "pixels_not_a_plane",
                      "why": f"shape {list(a.shape)} is not an (H, W[, C]) plane",
                      "shape": list(a.shape)}
    return a[::PIXEL_COMPARE_STRIDE, ::PIXEL_COMPARE_STRIDE, ...], None


def _pixel_pairs(view_records):
    """`(carrying, identical_pairs, distances, pairs_skipped_for_shape, unreadable)`.

    Adjacent pairs, because a turnaround is an ordered orbit and a camera that stopped
    moving stops between neighbours; the full N-squared comparison would cost eight times
    as much to answer the same question. `numpy` is imported lazily so this module keeps
    its "no bpy, no hard numeric dependency at import" shape for callers that only want
    `orbit_azimuths`.

    **Two populations, counted separately** (F-1935e0e1 / F-e207fd20, wave 16). This
    returned `compared` — the number of view RECORDS carrying a plane — and the caller
    spent that number in the sentence "distinct in PIXELS over {compared} of {n} view(s)",
    which is a claim about COMPARISONS PERFORMED. They are not the same population:
    `distances` accumulates only for adjacent pairs where both planes are present AND
    their strided shapes match. Measured with eight 64x64x4 planes and view 3 re-rendered
    at 72x64: `n_views_compared_in_pixels: 8`, verdict "...distinct in PIXELS over 8 of 8
    view(s)", while `adjacent_pixel_distances` carried 5 of the 7 adjacent pairs and view
    3 was compared to nothing at all. The one view a camera failed to advance to is
    exactly the view whose plane can come back a different size, and its two pairs were
    dropped from the comparison while the verdict reported them as compared.
    """
    planes, unreadable = [], []
    for i, rec in enumerate(view_records):
        px = rec.get("pixels")
        if px is None:
            planes.append(None)
            continue
        plane, why = _read_plane(i, px)
        if why is not None:
            unreadable.append(why)
        planes.append(plane)
    import math as _math

    import numpy as np

    identical, distances, skipped, non_finite = [], [], [], []
    for i in range(1, len(planes)):
        a, b = planes[i - 1], planes[i]
        if a is None or b is None:
            continue
        if getattr(a, "shape", None) != getattr(b, "shape", None):
            skipped.append({"pair": [i - 1, i],
                            "shapes": [list(a.shape), list(b.shape)]})
            continue
        d = float(np.abs(a - b).mean())
        # THE VALUE DOOR (F-8cfaefd9, wave 22). `d == 0.0` is False for a NaN and so is
        # every comparison `min` makes, so a pair whose planes carry a non-finite value was
        # APPENDED to `distances`, counted as compared, and ruled on by nothing: measured on
        # `e8263a3` on eight distinct 32x32x4 planes with one NaN element in view 3, the gate
        # RETURNED with `min_adjacent_pixel_distance = 0.29889835824724287` and a verdict
        # reading "distinct in PIXELS over 7 of 7 adjacent pair(s)", while the two pairs
        # touching view 3 carried `nan`. That is the population-vs-comparisons defect
        # F-1935e0e1 and F-e207fd20 closed through the SHAPE and UNREADABLE doors, arriving
        # through the VALUE door those two fixes left open. Partitioned, not dropped: the
        # pair count the verdict quotes is now the count of pairs actually ruled on.
        if not _math.isfinite(d):
            non_finite.append({"pair": [i - 1, i], "distance": repr(d)})
            continue
        distances.append(d)
        if d == 0.0:
            identical.append([i - 1, i])
    # F-99e5de1a — EVERY unordered pair, which is what this gate's docstring already claimed
    # ("compared in pixel space against every other view that carries one") while the walk
    # above ranged over neighbours. 64 views is 2016 mean-absolute-difference comparisons,
    # which is cheap; the ADJACENT population above is kept and counted separately because
    # wave 16 established that a verdict names only clauses that ran against a population
    # that could fail them, and the adjacent minimum is the magnitude the Director's eye
    # reads.
    anywhere, n_pairs_all = [], 0
    for i in range(len(planes)):
        for j in range(i + 1, len(planes)):
            a, b = planes[i], planes[j]
            if a is None or b is None:
                continue
            if getattr(a, "shape", None) != getattr(b, "shape", None):
                continue
            n_pairs_all += 1
            if float(np.abs(a - b).mean()) == 0.0:
                anywhere.append([i, j])
    return {
        "carrying": sum(1 for p in planes if p is not None),
        "identical": identical, "distances": distances, "skipped": skipped,
        "unreadable": unreadable, "non_finite": non_finite,
        "identical_anywhere": anywhere, "n_unordered_pairs_compared": n_pairs_all,
    }


def gate_set_distinct(view_records, expected):
    """Gate TURN · ANDON — the set is the whole turnaround, and every view is distinct.

    Runs after the views and **before the manifest**, because the manifest is what makes a
    run look finished (`stage_render`'s own doctrine, and the reason its G2 sits there).

    Three clauses, all silent elsewhere. A short set is the obvious one. The second is
    **duplicate content**: if the camera failed to move — an orbit helper handed the same
    azimuth every time, a scene frame that never advanced, a camera matrix assigned once
    outside the loop — the run writes `expected` well-formed RGBA files, every per-view
    alpha gate passes on every one of them, the count is right, and the set is eight copies
    of the front view. Nothing else here looks at whether the views differ from each other.

    **The third is that clause read in PIXELS** (F-c4cf355d, wave 14). The duplicate
    clause was a byte-hash equality test, and only the third of the three failures the
    paragraph above names produces byte-identical files. An orbit helper that advances by
    a rounding error rather than by zero — a `sweep_deg` computed as 0.0001 rather than
    360, an int/float division that collapses the step — or a camera that moves a
    hundredth of a degree per view, writes eight files with eight DIFFERENT digests, and
    the gate returned its strongest verdict, "8 distinct views, as many as were asked
    for", on a set that is visually one view eight times. CLAUDE.md rules on exactly this
    direction: "A file-hash mismatch is not evidence a render changed. Compare pixels;
    reserve byte-hashes for artifacts whose bytes are the contract." Here the bytes are
    not the contract — the pictures are.

    So a record that carries `pixels` (an `(H, W, C)` array, or anything `numpy` will read
    as one) is compared in pixel space against every other view that carries one, and a
    pair whose mean absolute difference is 0.0 while their digests differ is refused by
    its own clause. **That sentence was a claim this gate did not keep until wave 22**
    (F-99e5de1a): `_pixel_pairs` ranged over `range(1, len(planes))` — ADJACENT pairs only —
    so two views identical in pixels but different in bytes passed unseen whenever they were
    not neighbours, which is exactly the shape a revisited azimuth produces. Both
    populations are walked now and both are counted, separately: the ADJACENT pairs, whose
    minimum distance is the magnitude the verdict quotes, and EVERY unordered pair, which is
    what the identity clause ranges over. Zero is a STRUCTURAL reading, not a tuned floor: two renders whose
    every pixel agrees are the same picture whatever their PNG bytes say, and this repo
    does not invent a threshold for "different enough" where no calibrated one exists —
    the measured `min_adjacent_pixel_distance` rides the evidence and the verdict so the
    Director's eye reads a magnitude rather than the word "distinct".

    **And where the clause cannot run, the verdict says so.** A caller that hands digest-
    only records gets `n_views_carrying_pixels: 0` and a verdict that states the pixel
    comparison did not happen, rather than a sentence that reads as though it did. A
    verdict names only clauses that ran against a population that could fail them.

    **The population the pixel verdict is quoted over is ADJACENT PAIRS, not view
    records** (F-1935e0e1 / F-e207fd20, wave 16). The evidence carried
    `n_views_compared_in_pixels` — a count of records carrying a plane — and the verdict
    spent it in "distinct in PIXELS over {n} of {m} view(s)", which is a claim about
    comparisons performed. The evidence now carries `n_views_carrying_pixels`,
    `n_adjacent_pairs`, `n_adjacent_pairs_compared` and
    `n_adjacent_pairs_skipped_for_shape` as four separate numbers, the verdict is phrased
    over the pair count, and the two ways a pair used to vanish silently are refusals with
    their own clauses: `views_without_pixels` (a partly-attached set) and
    `adjacent_pair_shapes_differ` (a view whose plane came back a different size — the
    plausible shape for the one view a camera failed to advance to). A `pixels` value
    numpy cannot read is `pixels_unreadable`, a typed refusal at exit 2 rather than
    whatever `np.asarray` raises at exit 1.
    """
    ev = {"gate": "TURN", "andon": "TurnaroundGate",
          "expected": int(expected), "observed": len(view_records)}
    if not int(expected) or not view_records:
        ev["clause"] = "empty_set"
        raise TurnaroundGate(
            f"the set was gated over {len(view_records)} view(s) against an expected "
            f"{int(expected)}: the count clause compares 0 to 0, the digest loop never "
            f"runs and the duplicate clause compares two empty sets, so the gate would be "
            f"a check that cannot fail", ev)
    if len(view_records) != int(expected):
        ev["clause"] = "set_short"
        raise TurnaroundGate(
            f"the set carries {len(view_records)} view(s), not {expected}", ev)
    digests = [r.get("sha256") for r in view_records]
    if any(d is None for d in digests):
        ev["clause"] = "view_without_a_digest"
        raise TurnaroundGate(
            "a view record carries no sha256, so the set can be checked neither for "
            "duplicates nor for pinning", ev)
    ev["distinct_sha256"] = len(set(digests))
    if len(set(digests)) != len(digests):
        dupes = sorted({d for d in digests if digests.count(d) > 1})
        ev["clause"] = "views_byte_identical"
        raise TurnaroundGate(
            f"{len(digests) - len(set(digests))} of {len(digests)} views are "
            f"byte-identical to another view ({', '.join(d[:12] for d in dupes)}): the "
            "camera did not move between them. Every per-view check passes on this set — "
            "the files are RGBA, the count is right, the figure is in all of them", ev)

    _pp = _pixel_pairs(view_records)
    carrying, identical, distances = _pp["carrying"], _pp["identical"], _pp["distances"]
    skipped, unreadable = _pp["skipped"], _pp["unreadable"]
    n_pairs = max(len(view_records) - 1, 0)
    if unreadable:
        first = unreadable[0]
        ev["clause"] = first["clause"]
        ev["unreadable_view"] = first["view"]
        ev["unreadable_reason"] = first["why"]
        ev["unreadable_views"] = unreadable
        if "shape" in first:
            ev["pixels_shape"] = first["shape"]
        raise TurnaroundGate(
            f"view {first['view']} carries a `pixels` value this gate cannot read as a "
            f"plane ({first['why']}). The pixel clause is what stands between this gate "
            f"and a set of {len(view_records)} renders of one picture, and an input it "
            f"cannot read is refused rather than skipped — `np.asarray` raises a bare "
            f"builtin, which the halt contract records as a crash at exit 1", ev)
    ev["n_views_carrying_pixels"] = carrying
    ev["n_adjacent_pairs"] = n_pairs
    ev["n_adjacent_pairs_compared"] = len(distances)
    ev["n_adjacent_pairs_skipped_for_shape"] = len(skipped)
    ev["adjacent_pairs_skipped_for_shape"] = skipped[:12]
    ev["n_pairs_identical_in_pixels"] = len(identical)
    ev["pairs_identical_in_pixels"] = identical[:12]
    ev["adjacent_pixel_distances"] = [round(d, 9) for d in distances]
    ev["min_adjacent_pixel_distance"] = min(distances) if distances else None
    ev["n_adjacent_pairs_non_finite"] = len(_pp["non_finite"])
    ev["adjacent_pairs_non_finite"] = _pp["non_finite"][:12]
    n_unordered = len(view_records) * (len(view_records) - 1) // 2
    ev["n_unordered_pairs"] = n_unordered
    ev["n_unordered_pairs_compared"] = _pp["n_unordered_pairs_compared"]
    ev["n_pairs_identical_in_pixels_anywhere"] = len(_pp["identical_anywhere"])
    ev["pairs_identical_in_pixels_anywhere"] = _pp["identical_anywhere"][:12]

    # A set where SOME records carry a plane is refused rather than partly compared: the
    # views that carry none are the ones nothing rules on, and a verdict quoting a
    # magnitude over the rest reads as a verdict over the set. Measured (F-e207fd20) on a
    # set where only even-indexed views carried a plane: `compared == 4`, `distances ==
    # []`, and the verdict branch — keyed on `compared` rather than on `distances` —
    # called `min([])`, raising an untyped `ValueError` from inside the gate.
    if carrying and carrying != len(view_records):
        ev["clause"] = "views_without_pixels"
        ev["views_without_pixels"] = [i for i, r in enumerate(view_records)
                                      if r.get("pixels") is None]
        raise TurnaroundGate(
            f"{carrying} of {len(view_records)} view records carry `pixels`. The pixel "
            f"clause is the one that can see a camera which advanced by a rounding error, "
            f"and a partly-attached set gets it on some views and not others — so the "
            f"views that carry nothing are exactly the ones no clause rules on, while the "
            f"verdict quotes a magnitude and reads as a verdict over the set. Attach the "
            f"plane for every view or for none", ev)

    # A pair dropped for a shape mismatch is refused, not silently skipped: the view whose
    # plane came back a different size is the plausible one for a camera that failed to
    # advance, and dropping its two pairs removes it from the only clause that could see
    # that (F-1935e0e1).
    if skipped:
        ev["clause"] = "adjacent_pair_shapes_differ"
        raise TurnaroundGate(
            f"{len(skipped)} of {n_pairs} adjacent pair(s) carry planes of different "
            f"shapes ({[k['shapes'] for k in skipped[:4]]}), so they cannot be compared in "
            f"pixels. A turnaround's views are one camera orbiting one subject at one "
            f"resolution; a view whose plane is a different size is either a different "
            f"render or a different subject, and either way the pair is dropped from the "
            f"comparison rather than passing it", ev)

    # The VALUE door, refused before any verdict quotes a pair count (F-8cfaefd9).
    if _pp["non_finite"]:
        ev["clause"] = "non_finite_pair_distance"
        raise TurnaroundGate(
            f"{len(_pp['non_finite'])} of {n_pairs} adjacent pair(s) have a mean absolute "
            f"difference that is not a number "
            f"({[k['pair'] for k in _pp['non_finite'][:4]]}). `d == 0.0` is False for a NaN "
            f"and so is every comparison `min` makes, so such a pair used to be counted as "
            f"COMPARED and ruled on by nothing while the verdict quoted a magnitude taken "
            f"over the pairs that happened to be readable. This gate accepts anything numpy "
            f"will read as an (H, W, C) plane — `render_turnaround._alpha_stats` builds one "
            f"with `np.empty(w*h*4, float32)` and `foreach_get`, a FLOAT read — so a plane "
            f"from the render buffer, an EXR or a compositor output arrives here with values "
            f"this gate never asked about", ev)

    if identical:
        ev["clause"] = "views_identical_in_pixels"
        raise TurnaroundGate(
            f"{len(identical)} adjacent view pair(s) are identical in PIXELS while their "
            f"sha256 digests differ ({identical[:6]}): the camera did not move between "
            f"them, and the byte-hash clause cannot see it because the files are not "
            f"byte-identical — an orbit helper that advanced by a rounding error rather "
            f"than by zero writes {len(digests)} different digests over one picture. "
            f"Every per-view check passes on this set", ev)

    # And the same clause over EVERY unordered pair (F-99e5de1a, wave 22). The adjacent
    # clause above is the one a stopped camera trips; this one is the one a REVISITED
    # azimuth trips, and a revisit is never adjacent. Measured on `e8263a3` with eight
    # 64x64x4 random planes, view 4 replaced by a copy of view 0 and eight distinct sha256
    # values: the gate RETURNED its strongest verdict with `n_pairs_identical_in_pixels: 0`
    # while `np.abs(planes[0] - planes[4]).mean()` was exactly 0.0.
    if _pp["identical_anywhere"]:
        ev["clause"] = "views_identical_in_pixels_anywhere"
        raise TurnaroundGate(
            f"{len(_pp['identical_anywhere'])} view pair(s) are identical in PIXELS while "
            f"their sha256 digests differ ({_pp['identical_anywhere'][:6]}), at a distance "
            f"the adjacent clause above cannot see. A turnaround that revisits an azimuth "
            f"— `orbit_azimuths(8, 0, 720)` returns the same four directions twice, at "
            f"stride 4 — writes {len(digests)} well-formed RGBA files with "
            f"{len(digests)} different digests over fewer pictures, and every per-view gate "
            f"passes on every one of them", ev)

    # Keyed on `distances`, the population `min` is taken over, never on the count of
    # records carrying a plane (F-e207fd20): the two are different numbers, and the
    # branch that spends `min(distances)` has to be the branch that knows it is non-empty.
    if distances:
        ev["verdict"] = (
            f"{len(digests)} distinct views by sha256, as many as were asked for, and "
            f"distinct in PIXELS over {len(distances)} of {n_pairs} adjacent pair(s) "
            f"({carrying} of {len(digests)} view(s) carried a plane): closest adjacent "
            f"pair {min(distances):.6g} mean absolute difference")
    else:
        ev["verdict"] = (
            f"{len(digests)} distinct views by sha256, as many as were asked for; pixel "
            f"content was NOT compared (no view record carried pixels), so this verdict "
            f"rules on the bytes only")
    return ev
