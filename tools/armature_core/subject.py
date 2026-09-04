"""What a subject asset *is*, as a number rather than as a filename.

This module exists because of E01. Its spec named `longsword_hero.glb` "a
facet-finished asset, the natural primary" for a **character**-staging tool, and the
name was believed through an entire dispatch. Measured afterwards, the asset is
0.226 x 1.002 x 0.063 — a blade, aspect 15.8. Nobody had opened it.

So the E02 premise table carries "the subject is a character" as a line the executor
must *measure*, and this is the measurement. It is deliberately arithmetic on the
bounding box and nothing more: no thresholds, no verdict, no `is_character` boolean.
Whether a figure is the right character is canon and the Director's to judge; what a
mesh's proportions are is a number, and only the number belongs here.

`aspect_longest_over_shortest` is the discriminator, and it is specifically **longest
over shortest** rather than longest over middle. A sword is long in one axis and thin
in *both* others; a standing figure has real extent in two, so the shortest axis is
where the difference lives.

Both ratios are reported because the margin between them was measured rather than
asserted, and the first version of this docstring got it wrong. On E01's two real
subjects:

    longest/shortest   sword 15.9  ·  figure 3.23   -> 4.9x apart
    longest/middle     sword  4.43 ·  figure 1.66   -> 2.7x apart

So longest/middle does **not** collapse the distinction — an earlier draft here
claimed it put a blade among figures, and that claim was false. It simply separates
less well. longest/shortest is preferred on the measured margin, which is a weaker and
truer reason than the one first written down.
"""


from .errors import SubjectExtentError
from .parts import require_finite


def extent_summary(half_extent):
    """Bounding-box proportions from a half-extent triple.

    `half_extent` is the (x, y, z) half-extent as `blender_scene.world_bounds`
    returns it — half the box, not the box. Returning `extents` at full size is the
    point: an off-by-2 here would silently halve every dimension a report quotes.
    """
    # ⚠ **These three refusals were bare `ValueError`s.** A `ValueError` is not an
    # `ArmatureError`, so `probe_subject`'s halt handler classified a deliberate refusal
    # from this module exit 1 (an unhandled crash) instead of exit 2 (an andon), and wrote
    # no receipt — the same 13-site re-classing wave 12 did elsewhere, with this module
    # missed. They raise the family now, with the offending value in the evidence.
    ev = {"gate": None, "andon": "SubjectExtentError", "half_extent": repr(half_extent)}
    if half_extent is None:
        raise SubjectExtentError(
            "half_extent is None: the subject has no geometry to measure", ev)
    half = [float(v) for v in half_extent]
    if len(half) != 3:
        raise SubjectExtentError(
            f"half_extent must have 3 components, got {len(half)}", ev)

    # · ANDON — the three guards covered None, arity and negativity, and `any(v < 0)` is
    # **False for NaN**. Measured 2026-09-04: `extent_summary((nan, 1.0, 0.5))` returned
    # `{'extents': [NaN, 2.0, 1.0], 'longest': NaN, 'middle': NaN, 'shortest': NaN,
    # 'aspect_longest_over_shortest': Infinity, 'degenerate_axis': false}` — `max`/`min`
    # propagate the NaN, `shortest > 0` is False so the guarded division falls to its
    # `inf` branch, and the record therefore states affirmatively that **no axis is
    # degenerate** on a mesh whose extent is not a number. `(inf, 1.0, 0.5)` returns
    # finite extents with an infinite aspect.
    #
    # Two consequences, both on the one caller (`probe_subject.py:133/:150`):
    #   (a) the record it writes is `json.dump(payload, fh, indent=2)` with the stdlib
    #       `allow_nan` default, so `subject_extents.json` gets the bare token `NaN` and
    #       is not RFC-8259 JSON — the identical defect `shotspec.dump_spec` was given
    #       `allow_nan=False` for on 2026-09-04;
    #   (b) the shape discriminator this module exists to BE reports a non-finite mesh as
    #       a well-proportioned figure. E01's whole lesson is that the answer to "what is
    #       this asset" was believed without being measured; a non-number is not an answer.
    #
    # Through `parts.require_finite` — the repo's one non-finite helper — rather than a
    # second spelling of it here. `positive=False`: a half-extent of 0 is a planar asset,
    # which the `degenerate_axis` branch below reports rather than refuses.
    for axis, v in zip("xyz", half):
        require_finite(f"half_extent.{axis}", v, SubjectExtentError, ev, positive=False)

    if any(v < 0 for v in half):
        raise SubjectExtentError(
            f"half_extent components must be non-negative, got {half}", ev)

    extents = [v * 2.0 for v in half]
    longest, shortest = max(extents), min(extents)
    mid = sorted(extents)[1]

    return {
        "extents": extents,
        "longest_axis": "XYZ"[extents.index(longest)],
        "longest": longest,
        "middle": mid,
        "shortest": shortest,
        # The discriminator. Guarded rather than left to raise ZeroDivisionError, so a
        # degenerate (planar) asset reports as degenerate instead of crashing the probe
        # that was asked what the asset is.
        "aspect_longest_over_shortest": (longest / shortest) if shortest > 0 else float("inf"),
        "aspect_longest_over_middle": (longest / mid) if mid > 0 else float("inf"),
        "degenerate_axis": shortest <= 0,
    }
