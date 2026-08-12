"""Measurements over a decoded clip: how much it moves, how it is lit, where the room is.

No bpy, no network. Every function takes a list of `(H, W, 3)` uint8 arrays — the lossless
frames off `VAEDecode`, never a re-encoded video — and returns plain numbers.

**Why this exists as a module and not as a script.** E10 measured a ten-fold frame-to-frame
luminance swing and reported it from an ad-hoc computation with no tool behind it, so the
number is in that report and the instrument is not in the tree. These are the same
quantities with the arithmetic written down, tested, and named for what they measure rather
than for the experiment that first needed them.

--------------------------------------------------------------------------------
What each measurement can and cannot separate — read before quoting one

`frame_deltas` and `similarity_to_first` are **conflated by construction**. They move when
the subject moves, when the camera moves, when the exposure shifts and when the scene is
repainted, and they cannot tell those apart. That is not a defect to be fixed by scaling
them differently; it is what a whole-image difference is. They are reported as what they
are and they gate nothing.

`horizon_row` is the one here that separates camera from subject, and it is built for
exactly that. A static camera over a moving figure leaves the room's horizon on the same
row — the figure occludes a few columns and the median across the rest does not care. A
camera that tilts, dollies or pans moves it. So a declining `similarity_to_first` beside a
constant `horizon_row` says "the subject moved"; both moving says "the camera moved too".

Its own failure mode is honest and is reported rather than smoothed: if the room stops
existing — repainted into somewhere else — the columns stop agreeing and the function
returns `None` with its agreement fraction, instead of a plausible row number nobody could
check. A diagnostic that returns a number on a frame it cannot read is noise wearing a unit,
and this repo has already shipped two of those.
"""

import hashlib

import numpy as np

#: Rec.709. Written out rather than imported so the weights are visible next to every
#: number computed from them.
LUMA_WEIGHTS = (0.2126, 0.7152, 0.0722)


def _as_float(frame):
    return np.asarray(frame, dtype=np.float64)


def luma(frame):
    """Rec.709 luminance of an `(H, W, 3)` frame, in the frame's own units."""
    a = _as_float(frame)
    if a.ndim != 3 or a.shape[2] < 3:
        raise ValueError(f"expected an (H, W, 3) frame, got shape {a.shape}")
    return a[..., 0] * LUMA_WEIGHTS[0] + a[..., 1] * LUMA_WEIGHTS[1] \
        + a[..., 2] * LUMA_WEIGHTS[2]


def _stats(values):
    if not len(values):
        return {"n": 0}
    v = np.asarray(values, dtype=np.float64)
    return {"n": int(v.size), "min": float(v.min()), "median": float(np.median(v)),
            "mean": float(v.mean()), "p90": float(np.percentile(v, 90)),
            "max": float(v.max())}


def frame_deltas(frames):
    """Mean absolute difference between consecutive frames, over all three channels.

    The quantity E08 and E10 both report (E08: min 2.55 / median 3.95 / max 6.16; E10:
    4.91 / 15.95 / 69.85), reproduced here so a third clip is comparable to them. Whole
    image, all channels, so it moves with background and exposure as much as with the
    figure — see the module docstring.
    """
    per = [float(np.abs(_as_float(b) - _as_float(a)).mean())
           for a, b in zip(frames, frames[1:])]
    return {"per_frame": per, "stats": _stats(per)}


def luma_series(frames):
    """Mean luminance per frame, and the frame-to-frame absolute change in it.

    E10's headline unaimed-at measurement. Segment medians are returned too, because E10's
    swing was strongly non-uniform across its clip and a single median hid that.
    """
    means = [float(luma(f).mean()) for f in frames]
    deltas = [abs(b - a) for a, b in zip(means, means[1:])]
    segments = {}
    if len(deltas) >= 4:
        step = len(deltas) // 4
        for i in range(4):
            lo = i * step
            hi = len(deltas) if i == 3 else (i + 1) * step
            segments[f"q{i + 1}"] = float(np.median(deltas[lo:hi]))
    return {"mean_luma_per_frame": means,
            "mean_luma_over_clip": float(np.mean(means)) if means else None,
            "luma_range_over_clip": float(max(means) - min(means)) if means else None,
            "abs_delta_luma": deltas, "stats": _stats(deltas),
            "segment_medians": segments}


def similarity_to_first(frames):
    """Per frame: mean absolute difference from frame 0, and Pearson correlation with it.

    **Conflated, deliberately, and labelled.** H-E11d asks whether the framing drifts from
    the authored start frame; this is the direct reading of that question and it also moves
    when the figure dances in a locked-off frame. It is quoted beside `horizon_row`, which
    is what separates the two, and never on its own.

    Pearson is included because it is invariant to a global brightness or contrast shift,
    so the pair `(mean_abs, correlation)` distinguishes "the picture got darker" from "the
    picture became a different picture". A clip that only dims reads a rising mean_abs at a
    near-flat correlation.
    """
    if not frames:
        return {"per_frame": [], "stats": {"n": 0}}
    first = _as_float(frames[0])
    fz = first.ravel() - first.mean()
    fz_norm = float(np.sqrt((fz * fz).sum()))
    per, corr = [], []
    for f in frames:
        a = _as_float(f)
        per.append(float(np.abs(a - first).mean()))
        az = a.ravel() - a.mean()
        an = float(np.sqrt((az * az).sum()))
        corr.append(float((fz * az).sum() / (fz_norm * an))
                    if fz_norm > 0 and an > 0 else float("nan"))
    return {"per_frame_mean_abs": per, "per_frame_correlation": corr,
            "stats_mean_abs": _stats(per), "stats_correlation": _stats(corr),
            "measures": ("distance from the authored start frame. It moves with the "
                         "subject, the camera, the exposure and the scene alike and "
                         "separates none of them; read it beside horizon_row")}


def horizon_row(frame, band=None, tolerance=3, min_agreement=0.5):
    """The row of the room's strongest horizontal edge, or `None` if the columns disagree.

    For each column the row of greatest vertical luminance gradient is taken; the answer is
    the median of those, and `agreement` is the fraction of columns landing within
    `tolerance` rows of it. A figure standing in the frame occludes some columns and drags
    their argmax elsewhere, which is why the statistic is a median with an agreement figure
    rather than a mean.

    Returns `None` for the row when agreement falls below `min_agreement` — the case where
    the room has been repainted into something without one horizontal edge. Reporting a
    number there would be a measurement of nothing, and the whole reason this function
    exists is to be the one quantity in the clip that a moving subject cannot move.
    """
    lum = luma(frame)
    h, w = lum.shape
    lo, hi = band if band else (1, h - 1)
    lo, hi = max(1, int(lo)), min(h - 1, int(hi))
    if hi - lo < 2:
        raise ValueError(f"band ({lo}, {hi}) leaves fewer than two rows to search")
    grad = np.abs(lum[lo + 1:hi + 1, :] - lum[lo - 1:hi - 1, :])
    rows = np.argmax(grad, axis=0) + lo
    med = float(np.median(rows))
    agreement = float(np.mean(np.abs(rows - med) <= tolerance))
    strength = float(np.median(grad.max(axis=0)))
    found = agreement >= min_agreement
    return {"row": med if found else None, "agreement": agreement,
            "edge_strength": strength, "tolerance": tolerance,
            "min_agreement": min_agreement, "n_columns": int(w),
            "verdict": ("found" if found else
                        "NOT FOUND — the columns do not agree on one horizontal edge")}


def distinct_frames(frames):
    """How many of the frames are byte-distinct. A clip that froze reads 1."""
    seen = {hashlib.sha256(np.ascontiguousarray(f).tobytes()).hexdigest() for f in frames}
    return {"n_frames": len(frames), "n_distinct": len(seen)}
