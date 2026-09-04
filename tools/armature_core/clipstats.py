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

from .errors import ArmatureError


class ClipStatsError(ArmatureError):
    """An instrument in this module was handed something it cannot measure.

    A deliberate refusal, and it used to be a bare `ValueError` (F-9fab7829, wave 12). The
    21-tool halt contract classifies on the `ArmatureError` family — `GateFailure` is
    "HALTED", `ArmatureError` is "REFUSED" at exit 2, and anything else is "FAILED — an
    unhandled error" at exit 1 — so every refusal in this module was recorded as a crash
    in the measuring code when what happened is the instrument declining to read an input
    it cannot read. Same defect `walk.WalkError`, `framing.FramingError` and
    `glb.MalformedGLB` carried before wave 10 rebased them.

    Carries an `evidence` dict like `GateFailure` does, and a plain refusal writes
    `gate: None` + `andon` + `clause` — a refusal is not an andon and has no gate id, so
    the honest answer is written down rather than left absent.

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
    """


#: Rec.709. Written out rather than imported so the weights are visible next to every
#: number computed from them.
LUMA_WEIGHTS = (0.2126, 0.7152, 0.0722)

#: The relative tolerance `horizon_row` uses to ask whether a column's PEAK gradient and
#: its MEDIAN gradient are the same float. Not a threshold on picture content: an
#: edgeless column is one whose gradient never rises above its own middle, and in float64
#: "never rises above" is a comparison with a rounding budget. 1e-9 is fifteen thousand
#: times the double-precision epsilon and fifteen orders below any real edge measured on
#: this rig (a step edge reads a peak/median ratio of ~1e17; a linspace ramp reads
#: 1 + 5e-15).
EDGE_RTOL = 1e-9


def _as_float(frame):
    return np.asarray(frame, dtype=np.float64)


def luma(frame):
    """Rec.709 luminance of an `(H, W, 3)` frame, in the frame's own units."""
    a = _as_float(frame)
    if a.ndim != 3 or a.shape[2] < 3:
        raise ClipStatsError(
            f"expected an (H, W, 3) frame, got shape {a.shape}",
            {"gate": None, "andon": "ClipStatsError", "clause": "frame_not_hw3",
             "shape": list(a.shape)})
    return a[..., 0] * LUMA_WEIGHTS[0] + a[..., 1] * LUMA_WEIGHTS[1] \
        + a[..., 2] * LUMA_WEIGHTS[2]


#: The keys `_stats` returns for EVERY population, empty or not. Written down so a
#: consumer can read the contract without running the function.
STAT_KEYS = ("n", "n_finite", "n_non_finite", "min", "median", "mean", "p90", "max")


def _stats(values):
    """Summary over `values`, partitioned into finite and non-finite. One key set, always.

    **Two findings, one function, and they pull in the same direction.**

    F-11b349bf — *one degenerate frame turned every aggregate into NaN while the receipt
    still said nine values were summarised.* `similarity_to_first` writes `float("nan")`
    into `per_frame_correlation` whenever a frame has zero variance (an all-black frame, a
    flat fade, a decode that produced a constant plate), and `v.min()` / `np.median` /
    `v.mean()` / `np.percentile` / `v.max()` all propagate NaN. Measured 2026-09-04 on
    nine frames of which exactly ONE (index 5) is flat: `n nan in corr: 1 of 9`, and
    `stats_correlation = {'n': 9, 'min': nan, 'median': nan, 'mean': nan, 'p90': nan,
    'max': nan}` — eight good correlations discarded by a summary still reporting `n: 9`,
    and a reader who takes `nan` for "no correlation" reads a healthy clip as a scene
    change. This module's own docstring says "a diagnostic that returns a number on a
    frame it cannot read is noise wearing a unit", and `horizon_row` is built to return
    None with an agreement figure rather than a plausible number; this was the same module
    taking the opposite decision silently.

    F-86e9b5b9 — *the empty case returned a DIFFERENT KEY SET.* `{"n": 0}` with no
    `min`/`median`/`mean`/`p90`/`max`, and `tools/measure_clip.py:131` does
    `round(arm["frame_deltas"]["stats"]["median"], 3)` unguarded, so a one-frame clip —
    the natural input for exactly the failure these instruments exist to detect — killed
    the instrument with a bare `KeyError: 'median'` instead of describing the clip.

    So: `n` is the population, `n_finite` and `n_non_finite` partition it, the five
    statistics are computed over the FINITE values only, and they are `None` (never NaN,
    never a missing key) when there are none. A single non-finite entry never erases a
    population again, and a consumer's `stats["median"]` always resolves.
    """
    v = np.asarray(list(values), dtype=np.float64)
    finite = v[np.isfinite(v)] if v.size else v
    out = {"n": int(v.size), "n_finite": int(finite.size),
           "n_non_finite": int(v.size - finite.size)}
    if finite.size:
        out.update({"min": float(finite.min()), "median": float(np.median(finite)),
                    "mean": float(finite.mean()),
                    "p90": float(np.percentile(finite, 90)), "max": float(finite.max())})
    else:
        out.update({k: None for k in ("min", "median", "mean", "p90", "max")})
    return out


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
        return {"per_frame_mean_abs": [], "per_frame_correlation": [],
                "stats_mean_abs": _stats([]), "stats_correlation": _stats([]),
                "measures": "no frames were given, so there is nothing to compare"}
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

    **A column with nothing to say does not vote** (F-eb8689f1, wave 14). `rows =
    np.argmax(grad, axis=0)` over an all-EQUAL column returns index 0, and nothing
    bounded the strength from below, so the agreement statistic read its MAXIMUM
    precisely where there is no information. Measured 2026-09-04: a uniform 64x64x3 plate
    of value 30 returned `{'row': 1.0, 'agreement': 1.0, 'edge_strength': 0.0, 'verdict':
    'found'}` — every column's gradient identically zero, every argmax resolved to the
    top of the band — and a smooth vertical ramp, also edgeless, returned `agreement:
    1.0` on the same mechanism. This is the argmin tie-breaking defect F-2ceefec7 closed
    in `clipcompare.order_check` recurring in the sibling instrument of the same pair,
    which was not checked at the time.

    So a column carries an edge only when its own peak gradient EXCEEDS its own median
    gradient — a comparison inside one column, with no absolute number in it and nothing
    to tune. A flat column (peak == median == 0) and a constant-gradient ramp column
    (peak == median > 0) both decline to vote; a step edge (peak 170 against a median
    near 0) votes. `agreement` is then read over the voting columns only, and
    `n_columns_with_an_edge` rides the dict beside it so the vacuous case is legible even
    to a reader who quotes only `row` and `verdict` — which is what a report quotes.

    `EDGE_RTOL` is a FLOAT-EQUALITY tolerance, not an image threshold, and the difference
    matters because this repo does not invent pass conditions. A `np.linspace` ramp's
    per-column gradients are equal in exact arithmetic and differ by 3.4e-14 on a
    magnitude of 6.35 — 5e-15 relative — in float64, so a bare `peak > median` reads that
    rounding as an edge and hands back a row. The comparison asked is "are these two
    numbers the same number", answered the way float comparisons are answered
    everywhere; it is scale-free, and no value of it can be tuned toward a picture.

    Worst case this closes: a generation that collapses to a flat or near-flat plate in
    its late frames — the failure video judging exists to catch — reported `horizon_row`
    locked at row 1.0 with agreement 1.0 across exactly those frames, so the instrument
    read the scene as perfectly stable at the moment the scene had been destroyed.
    """
    lum = luma(frame)
    h, w = lum.shape
    lo, hi = band if band else (1, h - 1)
    lo, hi = max(1, int(lo)), min(h - 1, int(hi))
    if hi - lo < 2:
        raise ClipStatsError(
            f"band ({lo}, {hi}) leaves fewer than two rows to search",
            {"gate": None, "andon": "ClipStatsError", "clause": "band_too_narrow",
             "band": [lo, hi], "frame_height": int(h)})
    grad = np.abs(lum[lo + 1:hi + 1, :] - lum[lo - 1:hi - 1, :])
    peak = grad.max(axis=0)
    # Per COLUMN, against that column's own middle: no global constant governs a local
    # feature, and a column whose gradient never rises above its own median has no
    # discontinuity for `argmax` to locate — only a tie for `argmax` to break. The
    # `EDGE_RTOL` term is float equality, not a picture threshold; see the docstring.
    mid = np.median(grad, axis=0)
    has_edge = (peak - mid) > EDGE_RTOL * np.maximum(np.abs(peak), np.abs(mid))
    n_edge = int(has_edge.sum())
    out = {"tolerance": tolerance, "min_agreement": min_agreement,
           "n_columns": int(w), "n_columns_with_an_edge": n_edge}
    if not n_edge:
        out.update({"row": None, "agreement": 0.0, "edge_strength": 0.0,
                    "verdict": ("NOT FOUND — no column carries a horizontal edge; every "
                                "column's gradient is flat, so every argmax is a tie "
                                "resolved at the top of the band")})
        return out
    rows = (np.argmax(grad, axis=0) + lo)[has_edge]
    med = float(np.median(rows))
    agreement = float(np.mean(np.abs(rows - med) <= tolerance))
    strength = float(np.median(peak[has_edge]))
    found = agreement >= min_agreement
    out.update({"row": med if found else None, "agreement": agreement,
                "edge_strength": strength,
                "verdict": ("found" if found else
                            "NOT FOUND — the columns do not agree on one horizontal "
                            "edge")})
    return out


def distinct_frames(frames):
    """How many of the frames are byte-distinct. A clip that froze reads 1."""
    seen = {hashlib.sha256(np.ascontiguousarray(f).tobytes()).hexdigest() for f in frames}
    return {"n_frames": len(frames), "n_distinct": len(seen)}
