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


def extent_summary(half_extent):
    """Bounding-box proportions from a half-extent triple.

    `half_extent` is the (x, y, z) half-extent as `blender_scene.world_bounds`
    returns it — half the box, not the box. Returning `extents` at full size is the
    point: an off-by-2 here would silently halve every dimension a report quotes.
    """
    if half_extent is None:
        raise ValueError("half_extent is None: the subject has no geometry to measure")
    half = [float(v) for v in half_extent]
    if len(half) != 3:
        raise ValueError(f"half_extent must have 3 components, got {len(half)}")
    if any(v < 0 for v in half):
        raise ValueError(f"half_extent components must be non-negative, got {half}")

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
