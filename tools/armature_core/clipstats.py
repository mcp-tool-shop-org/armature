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
import math

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


def scale_of(frames):
    """The population's own scale, as FACTS: dtype, observed range, frame count.

    F-af6b12ed, wave 28. Every number this module reports is "in the frame's own units"
    (`luma`'s docstring) because `_as_float` is a bare `np.asarray(..., dtype=float64)` and
    inherits whatever the caller decoded. MEASURED on the repo venv over the same six
    16x16x3 frames, once as uint8 0..255 and once as float64 0..1: `frame_deltas` returned
    a median of 83.9167 against 0.3291 and `luma_series` a `mean_luma_over_clip` of 127.81
    against 0.5012 — a factor of 255 — and NEITHER record carried a key naming the scale,
    the input dtype or the value range. `frame_deltas`' own docstring quotes E08's
    2.55 / 3.95 / 6.16 and E10's 4.91 / 15.95 / 69.85 "so a third clip is comparable to
    them", which is exactly the comparison a missing scale breaks: the number reaches the
    Director as the tile "d(frame) med" (`make_startframe_sheet.main`) with no unit on it
    and none in the record, so a float-decoded run and a byte-decoded run differ by 255x
    while both look like healthy small numbers next to a banked 3.95.

    **Facts, never a verdict, and never a coercion.** This does not label a range "byte" or
    "unit" and does not rescale anything — rescaling would silently move numbers the reports
    have already banked. It reports what the array WAS: `input_dtype`, `observed_min`,
    `observed_max`, `n_frames`. Two runs whose scales differ then differ visibly in the
    record itself.

    The shape is `similarity_to_first`'s `measures` sentence, which is the only public
    reader in this module that already declared what it was measuring.
    """
    seq = list(frames) if frames is not None else []
    if not len(seq):
        return {"input_dtype": None, "observed_min": None, "observed_max": None,
                "n_frames": 0}
    dtypes = sorted({str(np.asarray(f).dtype) for f in seq})
    # Over the FINITE values only, and `None` when there are none: a NaN reaching here
    # would otherwise be written into the report as the bare token `NaN`, which is not
    # JSON — the defect `parts.halt_keysafe` exists to stop on the halt line, and this
    # record is read from `measure_clip.py`'s file rather than from a halt.
    lo, hi = None, None
    for f in seq:
        v = _as_float(f).ravel()
        v = v[np.isfinite(v)]
        if not v.size:
            continue
        lo = float(v.min()) if lo is None else min(lo, float(v.min()))
        hi = float(v.max()) if hi is None else max(hi, float(v.max()))
    return {"input_dtype": dtypes[0] if len(dtypes) == 1 else dtypes,
            "observed_min": lo, "observed_max": hi, "n_frames": len(seq)}


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
    `min`/`median`/`mean`/`p90`/`max`, and `tools/measure_clip.py::main` does
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
    return {"per_frame": per, "stats": _stats(per),
            "scale": scale_of(frames),
            "measures": ("mean absolute difference between consecutive frames, over the "
                         "whole image and all three channels, in the frames' own units — "
                         "see `scale`. It moves with the background and the exposure as "
                         "much as with the figure and separates none of them; a byte "
                         "decode and a float decode of one clip differ by 255x here")}


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
            "segment_medians": segments,
            "scale": scale_of(frames),
            "measures": ("Rec.709 mean luminance per frame and its frame-to-frame absolute "
                         "change, in the frames' own units — see `scale`. It is a whole-"
                         "image statistic: a light coming up, an exposure drift and the "
                         "figure moving across a bright wall all move it alike")}


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
           "n_columns": int(w), "n_columns_with_an_edge": n_edge,
           "scale": scale_of([frame]),
           "measures": ("the row of the room's strongest horizontal luminance edge, in "
                        "PIXEL ROWS — the one quantity here a moving subject cannot move. "
                        "`edge_strength` is a luminance gradient in the frame's own units "
                        "(see `scale`); `row`, `tolerance` and `agreement` are not")}
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


#: How many samples per frame the PIXEL comparison reads. A stride over the flattened
#: frame, not a crop: a freeze is a property of the whole plate, and a crop would answer
#: about a corner of it. 4096 over a 256x256x3 plate is every 48th value; over a
#: 832x480x3 one, every 292nd. The number is a COST bound and nothing about it is tuned
#: toward a picture — the quantity reported is the mean absolute difference over whatever
#: it reads, and the count of samples rides the dict so a reader knows what it was taken
#: over.
PIXEL_SAMPLES_PER_FRAME = 4096


def distinct_frames(frames):
    """How many of the frames differ — in BYTES and, separately, in PIXELS.

    **The byte count's failing direction is unreachable on this function's real input**
    (F-4ba279bf, wave 25). `n_distinct` is a count of sha256 digests and its docstring used
    to say "A clip that froze reads 1", which is true only of a clip that froze
    byte-for-byte. CLAUDE.md rules on this direction: "A file-hash mismatch is not evidence
    a render changed. Compare pixels; reserve byte-hashes for artifacts whose bytes are the
    contract." Here the bytes are not the contract — the pictures are.

    MEASURED in this worktree on `580af47`, 65 frames of a 256x256x3 plate in which each
    frame differs from the base by ONE byte in one channel: `n_frames: 65,
    n_distinct: 65` — the strongest reading the instrument has — while the neighbouring
    `frame_deltas` in this same module reported a median frame-to-frame mean absolute
    difference of **5.09e-06**. A decoded generation is never byte-identical frame to
    frame, so on its real input this diagnostic could only ever return `n_frames`. It is
    the finding wave 14 already paid for one module over
    (F-c4cf355d on `turnaround.gate_set_distinct`: an orbit helper advancing by a rounding
    error writes eight files with eight DIFFERENT digests over one picture).

    The panel the Director reads quotes it verbatim — `make_e13_sheet.py::main` prints
    "<n> frames, <d> distinct" and `make_startframe_sheet.py::main` the same, both filled by
    `measure_clip.py` — so the sheet now carries a number the arm can move.

    **The shape is `gate_set_distinct`'s, which is where this repo already settled it**:
    every UNORDERED pair, mean absolute difference, both populations counted separately,
    and the measured minimum quoted as a MAGNITUDE rather than as the word "distinct". A
    frame is pixel-distinct when it is not identical to any earlier frame, so a clip that
    froze reads `n_pixel_distinct: 1` whether or not its bytes agree.

    **It gates nothing**, per this module's own doctrine — these are diagnostics, and the
    Director's eye is the judge. `gate_set_distinct` is the gate-shaped sibling and it
    lives in `turnaround` because that is where the andon belongs.

    Returned keys: `n_frames`, `n_distinct` (bytes), `n_pixel_distinct`,
    `n_pairs_compared`, `n_pairs_identical_in_pixels`, `pairs_identical_in_pixels` (first
    12), `min_pair_mean_abs_difference`, `n_samples_per_frame` and `pixel_stride`. A
    single frame has no pair to compare, and `min_pair_mean_abs_difference` is then None
    rather than a number taken over nothing.
    """
    seen = {hashlib.sha256(np.ascontiguousarray(f).tobytes()).hexdigest() for f in frames}
    flats = [_as_float(f).ravel() for f in frames]
    size = min((v.size for v in flats), default=0)
    stride = max(1, int(np.ceil(size / PIXEL_SAMPLES_PER_FRAME))) if size else 1
    # Frames of differing shape are compared over the leading `size` samples of each, which
    # is what a stride over a ravel gives; a clip whose frames are not one size is a
    # different defect and `frame_deltas` beside this would already be reporting on it.
    sampled = [v[:size:stride] for v in flats]
    identical, distances, non_finite = [], [], []
    pixel_distinct = 0
    for i in range(len(sampled)):
        is_new = True
        for j in range(i):
            d = float(np.abs(sampled[i] - sampled[j]).mean()) if size else 0.0
            # THE VALUE DOOR, partitioned rather than dropped — the shape
            # `turnaround._pixel_pairs` settled in wave 22 (F-8cfaefd9). `d == 0.0` is
            # False for a NaN and so is every comparison `min` makes, so a pair carrying
            # one would be counted as compared and read as distinct while the minimum
            # quoted beside it was taken over the readable pairs only. Frames off
            # `VAEDecode` are uint8 and cannot produce one; `_as_float` accepts a float
            # array and this function is public, so the pairs are counted rather than
            # assumed away.
            if not math.isfinite(d):
                non_finite.append([j, i])
                continue
            distances.append(d)
            if d == 0.0:
                identical.append([j, i])
                is_new = False
        if is_new:
            pixel_distinct += 1
    return {"n_frames": len(frames), "n_distinct": len(seen),
            "n_pixel_distinct": pixel_distinct,
            "n_pairs_compared": len(distances),
            "n_pairs_identical_in_pixels": len(identical),
            "pairs_identical_in_pixels": identical[:12],
            "n_pairs_non_finite": len(non_finite),
            "pairs_non_finite": non_finite[:12],
            "min_pair_mean_abs_difference": (min(distances) if distances else None),
            "n_samples_per_frame": int(len(sampled[0])) if sampled else 0,
            "pixel_stride": stride,
            "scale": scale_of(frames),
            "measures": ("two counts of the same clip: `n_distinct` counts sha256 digests "
                         "and `n_pixel_distinct` counts frames not pixel-identical to an "
                         "earlier one. `min_pair_mean_abs_difference` is a mean absolute "
                         "difference in the frames' own units — see `scale` — so a byte "
                         "decode and a float decode of one clip differ by 255x in it while "
                         "both counts are unchanged")}


def motion_aware_diagnostics(frames, motion_record, rest=None, obs=None,
                             authored_locals=None):
    """Lift/pose-unit diagnostics beside pixel clipstats (F-48da73de).

    Consumes decoded `frames` (for length / scale context only) plus a motion record
    (`{frames: [...]}` or a bare frame list). Reuses `lift_solve.bone_length_residuals`
    when `rest`+`obs` site tables are supplied, and `lift_solve.compare_rotations` when
    `authored_locals` (per-frame bone->3x3, or a single dict broadcast) is supplied.
    Consecutive-frame geodesic steps come from `resample.step_angles`. No new pixel
    heuristics — a bad lift is graded in lift/pose units rather than conflated luma deltas.
    """
    if not frames:
        raise ClipStatsError(
            "motion_aware_diagnostics was given no decoded frames",
            {"gate": None, "andon": "ClipStatsError",
             "clause": "motion_diag_no_frames"})
    if isinstance(motion_record, dict) and "frames" in motion_record:
        motion_frames = motion_record["frames"]
        schema = motion_record.get("motion_schema")
    elif isinstance(motion_record, (list, tuple)):
        motion_frames = list(motion_record)
        schema = None
    else:
        raise ClipStatsError(
            "motion_record must be a dict with 'frames' or a frame list",
            {"gate": None, "andon": "ClipStatsError",
             "clause": "motion_diag_record_unreadable",
             "type": type(motion_record).__name__})
    if not motion_frames:
        raise ClipStatsError(
            "motion_aware_diagnostics motion record carries no frames",
            {"gate": None, "andon": "ClipStatsError",
             "clause": "motion_diag_empty_motion"})
    from . import lift_solve
    from . import resample as _resample
    step = _resample.step_angles(motion_frames)
    bone_residuals = None
    if rest is not None or obs is not None:
        if rest is None or obs is None:
            raise ClipStatsError(
                "bone_length_residuals needs both rest and obs site tables",
                {"gate": None, "andon": "ClipStatsError",
                 "clause": "motion_diag_rest_obs_incomplete",
                 "has_rest": rest is not None, "has_obs": obs is not None})
        bone_residuals = lift_solve.bone_length_residuals(rest, obs)
    rotation_compare = None
    if authored_locals is not None:
        if isinstance(authored_locals, dict) and "local" not in authored_locals \
                and all(isinstance(v, (list, tuple)) for v in authored_locals.values()):
            # Single pose dict broadcast against every motion frame.
            rotation_compare = [
                lift_solve.compare_rotations(fr.get("local") or {}, authored_locals)
                for fr in motion_frames
            ]
        elif isinstance(authored_locals, (list, tuple)):
            if len(authored_locals) != len(motion_frames):
                raise ClipStatsError(
                    f"authored_locals length {len(authored_locals)} != motion "
                    f"{len(motion_frames)}",
                    {"gate": None, "andon": "ClipStatsError",
                     "clause": "motion_diag_authored_length_mismatch",
                     "n_authored": len(authored_locals),
                     "n_motion": len(motion_frames)})
            rotation_compare = [
                lift_solve.compare_rotations(
                    fr.get("local") or {},
                    (al.get("local") if isinstance(al, dict) and "local" in al else al) or {},
                )
                for fr, al in zip(motion_frames, authored_locals)
            ]
        else:
            raise ClipStatsError(
                "authored_locals must be a bone->matrix dict or a per-frame sequence",
                {"gate": None, "andon": "ClipStatsError",
                 "clause": "motion_diag_authored_unreadable",
                 "type": type(authored_locals).__name__})
    return {
        "n_decoded_frames": len(frames),
        "n_motion_frames": len(motion_frames),
        "length_match": len(frames) == len(motion_frames),
        "motion_schema": schema,
        "scale": scale_of(frames),
        "step_angles": step,
        "bone_length_residuals": bone_residuals,
        "rotation_compare": rotation_compare,
        "measures": ("lift/pose units via bone_length_residuals / compare_rotations / "
                     "step_angles; pixel luma deltas stay in frame_deltas"),
    }
