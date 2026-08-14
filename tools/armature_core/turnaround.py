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
            f"a turnaround of {n} view(s) is not a turnaround", {"n_views": n})
    return [float(start_deg) + float(sweep_deg) * (i / float(n)) for i in range(n)]


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
    """
    pinned = ortho_scale_pin is not None
    if pinned:
        if not ortho:
            raise TurnaroundPlanRefusal(
                f"an ortho_scale pin ({ortho_scale_pin!r}) was given for a PERSPECTIVE "
                "plan. There is no shared world span on the perspective path — the "
                "quantity shared there is the radius — so this plan would be composed with "
                "the pin dropped, and the run would render a perfectly well-formed "
                "turnaround that silently ignored the one number it was pinned on. A "
                "roster rendered that way is eight characters each framed to his own "
                "height, which is the failure the pin exists to prevent")
        pin = float(ortho_scale_pin)
        if not (math.isfinite(pin) and pin > 0.0):
            raise TurnaroundPlanRefusal(
                f"an ortho_scale pin of {ortho_scale_pin!r} is not a finite positive world "
                "span. A non-positive span collapses every point onto the frame centre and "
                "a non-finite one sends them nowhere at all; either way the render still "
                "saves as a well-formed, correctly-sized RGBA PNG. `ortho_half_spans` "
                "refuses <= 0 downstream but takes nan and inf, so this is the check that "
                "binds those")

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
        "gate": "CROP", "view": int(view_index), "path": path,
        "resolution": [w, h], "subject_bbox_px": (list(subject_bbox)
                                                  if subject_bbox is not None else None),
        "alpha_threshold": alpha_threshold,
        "measured_on": "the rendered alpha channel of the written PNG",
    }
    if subject_bbox is None:
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
    """
    lo, hi = int(alpha_min), int(alpha_max)
    ev = {
        "gate": "ALPHA", "view": int(view_index), "path": path,
        "alpha_extrema": [lo, hi],
        "transparent_fraction": float(transparent_fraction),
        "opaque_fraction": 1.0 - float(transparent_fraction),
        "note": ("film_transparent makes the world background alpha=0 while the subject's "
                 "own geometry stays opaque, so a solid figure standing in a transparent "
                 "field is the expected shape"),
    }
    if lo >= OPAQUE:
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is transparent, "
            "so this is not an RGBA render — it is a baked void with a fourth channel. "
            "`film_transparent` did not take effect, and every check after this one "
            "passes on the file anyway: it opens, it is the right size, the figure is in "
            "it, and a contact sheet cannot tell it from an authored view", ev)
    if hi < OPAQUE:
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is opaque, so "
            "nothing solid was rendered into this view. The file is well-formed, "
            "correctly sized, non-empty, and its alpha channel is richly varied — a gate "
            "written only against the flat-255 defect passes it", ev)
    ev["verdict"] = (f"view {view_index} authored RGBA; extrema ({lo}, {hi}), "
                     f"{float(transparent_fraction):.4f} of the frame transparent")
    return ev


def gate_set_distinct(view_records, expected):
    """Gate TURN · ANDON — the set is the whole turnaround, and every view is distinct.

    Runs after the views and **before the manifest**, because the manifest is what makes a
    run look finished (`stage_render`'s own doctrine, and the reason its G2 sits there).

    Two clauses, both silent elsewhere. A short set is the obvious one. The second is
    **duplicate content**: if the camera failed to move — an orbit helper handed the same
    azimuth every time, a scene frame that never advanced, a camera matrix assigned once
    outside the loop — the run writes `expected` well-formed RGBA files, every per-view
    alpha gate passes on every one of them, the count is right, and the set is eight copies
    of the front view. Nothing else here looks at whether the views differ from each other.
    """
    ev = {"gate": "TURN", "expected": int(expected), "observed": len(view_records)}
    if len(view_records) != int(expected):
        raise TurnaroundGate(
            f"the set carries {len(view_records)} view(s), not {expected}", ev)
    digests = [r.get("sha256") for r in view_records]
    if any(d is None for d in digests):
        raise TurnaroundGate(
            "a view record carries no sha256, so the set can be checked neither for "
            "duplicates nor for pinning", ev)
    ev["distinct_sha256"] = len(set(digests))
    if len(set(digests)) != len(digests):
        dupes = sorted({d for d in digests if digests.count(d) > 1})
        raise TurnaroundGate(
            f"{len(digests) - len(set(digests))} of {len(digests)} views are "
            f"byte-identical to another view ({', '.join(d[:12] for d in dupes)}): the "
            "camera did not move between them. Every per-view check passes on this set — "
            "the files are RGBA, the count is right, the figure is in all of them", ev)
    ev["verdict"] = f"{len(digests)} distinct views, as many as were asked for"
    return ev
