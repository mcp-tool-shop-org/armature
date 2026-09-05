"""Compare a decoded clip against the frames it was assembled from.

The question this module answers is not "is the video good" — nothing here judges anything.
It answers three separable questions about a round trip through an encoder:

* **count** — did every submitted frame come back?
* **order** — is decoded frame *i* the same picture as source frame *i*, or did the
  assembly shuffle them? A cascade of batches is exactly where an ordering fault hides:
  the count is right, the fps is right, every gate is green, and the clip's motion is
  scrambled. So order is measured, not inferred from the count.
* **fidelity** — how far each decoded frame sits from its source, and *where* the error
  lives. S03 measured the `yuv420p` save path putting its error at colour edges (12.19 on
  the top-decile gradient against 5.28 on the flat half of frame 0). That is a property of
  the encoder, and it is reported as one rather than read as damage.

Every number here is a diagnostic. **They gate nothing.**

Why the order matrix runs on downsampled frames: the honest comparison is n x n, and at
1024x576x3 that is 6561 full-resolution differences for an 81-frame clip. The fault being
looked for — a group of 27 frames landing in the wrong third of the clip — is a gross
displacement of the whole picture, legible at a fraction of the resolution. The fidelity
numbers, which are about single-digit pixel differences, are computed at full resolution
where they mean something.
"""

import numpy as np

from .errors import ArmatureError


class ClipCompareError(ArmatureError):
    """A comparison in this module was handed inputs it cannot compare.

    A deliberate refusal, and it used to be a bare `ValueError` (F-9fab7829, wave 12). The
    21-tool halt contract discriminates three outcomes on the `ArmatureError` family, so a
    bare builtin was recorded as "FAILED — an unhandled error" at exit 1 in the comparing
    code, when what happened is this module declining to compare. Carries an `evidence`
    dict; a plain refusal writes `gate: None` + `andon` + `clause`.

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


def _f(a):
    return np.asarray(a, dtype=np.float64)


def frame_fidelity(src, dec):
    """Per-frame distance between a source frame and its decoded counterpart.

    **`(H, W, 3)` only, and the shape is checked.** `frac_differing` reduces over the
    CHANNEL axis, so it is a fraction of PIXELS - but on a 2-D `(H, W)` frame the same
    expression collapsed the WIDTH axis and returned the fraction of differing ROWS under
    the same key name: measured on a 4x100 pair with exactly one differing pixel, the 2-D
    form reported 0.25 where the (4, 100, 3) form reported 0.0025, a 100x error with no
    shape check and nothing in the returned dict recording which reading was taken. A
    fidelity table over single-channel frames (a mask, an alpha or depth sequence, a luma
    extraction) would have quoted that number beside numbers in the right unit.
    `clipstats.luma` already refuses the same way, and `downsample` fails loudly; this
    accepted anything. The reduction axis is now named in the returned dict as well.
    """
    s, d = _f(src), _f(dec)
    if s.ndim != 3 or s.shape[2] < 3:
        raise ClipCompareError(
            f"expected an (H, W, 3) frame, got shape {s.shape}",
            {"gate": None, "andon": "ClipCompareError", "clause": "frame_not_hw3",
             "source_shape": list(s.shape)})
    if s.shape != d.shape:
        raise ClipCompareError(
            f"shape mismatch: source {s.shape} vs decoded {d.shape}",
            {"gate": None, "andon": "ClipCompareError", "clause": "shape_mismatch",
             "source_shape": list(s.shape), "decoded_shape": list(d.shape)})
    diff = np.abs(s - d)
    return {
        "identical": bool(np.array_equal(np.asarray(src), np.asarray(dec))),
        "mean_abs": float(diff.mean()),
        "max_abs": float(diff.max()),
        "frac_differing": float((diff.sum(axis=-1) > 0).mean()),
        "frac_differing_reduced_over": "channel axis -1; the unit is PIXELS",
    }


def gradient_split(src, dec, top_frac=0.10, flat_frac=0.50):
    """Mean error over the source's steepest-gradient pixels vs its flattest.

    The clause it exists for: chroma subsampling puts its error at colour edges, so the
    *shape* of the error is evidence about the encoder rather than about the picture. A
    number that is the same in both bands says something different from one that is not,
    and both readings are legible only if the two bands are reported separately.

    **The two clauses `frame_fidelity` already had, and this did not** (F-e15d9de2, wave
    22). Both measured on `e8263a3`:

    * **`(H, W, 3)`.** On a 16x16x1 pair `frame_fidelity` REFUSED with
      `clause: frame_not_hw3` and this function RETURNED
      `{'mean_err_top_gradient': 0.01, 'mean_err_flat': 0.01}` — so two functions in one
      module disagreed about what a frame is, and a fidelity table built from both would
      carry one refused population beside one accepted. Same class, same clause word, so a
      reader keys one triage on both.
    * **A band that selects no pixel.** The selections are unguarded slices, so a zero
      fraction selects NOTHING and `err[...].mean()` over an empty array is returned as the
      band's error: `gradient_split(a, b, top_frac=0.0)` returned
      `mean_err_top_gradient: nan` and `flat_frac=0.0` returned `mean_err_flat: nan` — a
      mean over nothing reported as a measurement, with no refusal and nothing in the dict
      saying the band was empty. The population a band is quoted over is a clause of the
      reading, not a number beside it (`turnaround.gate_set_distinct`'s wave-16 rule, one
      module over).
    """
    s, d = _f(src), _f(dec)
    if s.ndim != 3 or s.shape[2] < 3:
        raise ClipCompareError(
            f"expected an (H, W, 3) frame, got shape {s.shape}",
            {"gate": None, "andon": "ClipCompareError", "clause": "frame_not_hw3",
             "source_shape": list(s.shape)})
    if s.shape != d.shape:
        raise ClipCompareError(
            f"shape mismatch: source {s.shape} vs decoded {d.shape}",
            {"gate": None, "andon": "ClipCompareError", "clause": "shape_mismatch",
             "source_shape": list(s.shape), "decoded_shape": list(d.shape)})
    lum = s.mean(axis=-1)
    gy, gx = np.gradient(lum)
    g = np.hypot(gy, gx).ravel()
    err = np.abs(s - d).mean(axis=-1).ravel()
    order = np.argsort(g)
    n = g.size
    top = order[int(round(n * (1.0 - top_frac))):]
    flat = order[:int(round(n * flat_frac))]
    for _band, _sel in (("top_gradient", top), ("flat", flat)):
        if _sel.size == 0:
            raise ClipCompareError(
                f"the {_band} band selects 0 of {n} pixel(s) at top_frac="
                f"{float(top_frac)!r} / flat_frac={float(flat_frac)!r}, so the mean this "
                f"function would return for it is a mean over nothing. numpy reports that "
                f"as `nan` with a RuntimeWarning, and a NaN in a fidelity table is a "
                f"measurement-shaped hole: it fails every comparison in both directions and "
                f"reads as a band that was examined",
                {"gate": None, "andon": "ClipCompareError",
                 "clause": "empty_gradient_band", "band": _band, "n": int(n),
                 "top_gradient_frac": float(top_frac), "flat_frac": float(flat_frac),
                 "n_selected": int(_sel.size)})
    return {
        "top_gradient_frac": float(top_frac), "flat_frac": float(flat_frac),
        "mean_err_top_gradient": float(err[top].mean()),
        "mean_err_flat": float(err[flat].mean()),
    }


def downsample(frame, step=8):
    """Every `step`-th pixel in both axes. Cheap, and it preserves gross layout."""
    return _f(frame)[::step, ::step, :]


def order_check(sources, decoded, step=8):
    """Is decoded frame *i* nearest to source frame *i*?

    Returns the nearest source index for every decoded frame, how many sit on the
    diagonal, and the worst offender. A permutation shows up as a diagonal count below n;
    a cascade wired out of group order shows up as whole contiguous runs displaced by a
    group's length, which is why the run of mismatches is reported and not only the count.

    **A TIE is reported as a tie, not as a displacement** (F-2ceefec7, wave 12). Each
    decoded frame was assigned `np.argmin` of its distance to every source, and `argmin`
    breaks ties at the LOWEST index — so N identical frames all resolved to the first of
    them and the N-1 that follow read as displaced. This repo's own walk generator ends
    every authored walk with a hold (`walk.GaitParams.n_hold`), so the false alarm was on
    the ordinary shape of its own clips. Measured 2026-09-04 on a walk-shaped 12-frame clip
    (8 distinct moving frames then a 4-frame hold) compared against an EXACT COPY of
    itself: `order_preserved: False`, `n_on_diagonal: 8/12`, `n_displaced: 4`,
    `displaced: [(8,7),(9,7),(10,7),(11,7)]` — four frames reported as landing in the wrong
    place in a clip where source and decode are the same bytes. `min_margin` did read 0.0
    and the note below explains that as weak separation, but `order_preserved` and
    `displaced` are what a report quotes and both invented a fault.
    `tools/measure_cascade_clip.py::main` is the live consumer — the call is
    `record["order"] = CC.order_check(sources, decoded, step=a.step)`, re-anchored on the
    SYMBOL 2026-09-04 (F-0f035830) after two line citations went stale in two waves (`:185`
    at wave 12, then `:258`, which by this wave read `"mean_abs_min": min(...)`) — on the
    cascade path where a
    real group displacement is what the check exists for — so the false alarm arrived
    beside the true positive it would be confused with, and either reading is expensive:
    credits re-spent on a clip that round-tripped perfectly, or a real displacement
    dismissed as "that's just the hold frames again".

    So frame `i` counts as on-diagonal when `i` is among the source indices AT the minimum
    distance (within `tie_atol`), the tie sets are returned as `tie_groups`, and `n_tied`
    counts the frames whose answer was ambiguous. A genuinely ambiguous clip now says so
    instead of reading as displaced, and a real displacement still reads as one because a
    displaced frame is not tied with its own index.
    """
    if len(sources) != len(decoded):
        raise ClipCompareError(
            f"{len(sources)} source frame(s) against {len(decoded)} decoded",
            {"gate": None, "andon": "ClipCompareError", "clause": "length_mismatch",
             "n_sources": len(sources), "n_decoded": len(decoded)})
    n = len(sources)
    S = np.stack([downsample(f, step).ravel() for f in sources])
    D = np.stack([downsample(f, step).ravel() for f in decoded])
    tie_atol = 0.0
    nearest, margins, ties = [], [], []
    for i in range(n):
        dist = np.abs(S - D[i]).mean(axis=1)
        lo = float(dist.min())
        at_min = [int(k) for k in np.flatnonzero(dist <= lo + tie_atol)]
        # The reported nearest prefers the diagonal when the diagonal is AMONG the minima:
        # `argmin`'s lowest-index rule is an arbitrary choice between equals, and choosing
        # it over `i` is what manufactured the displacement.
        j = i if i in at_min else int(np.argmin(dist))
        nearest.append(j)
        ties.append(at_min)
        own = float(dist[i])
        other = float(np.min(np.delete(dist, i))) if n > 1 else float("inf")
        margins.append(other - own)
    on_diagonal = [i for i, j in enumerate(nearest) if j == i]
    off = [(i, nearest[i]) for i in range(n) if nearest[i] != i]
    tied = [i for i in range(n) if len(ties[i]) > 1]
    groups = sorted({tuple(sorted(ties[i])) for i in tied})
    return {
        "n": n, "step": int(step),
        "nearest": nearest,
        "n_on_diagonal": len(on_diagonal),
        "order_preserved": len(on_diagonal) == n,
        "displaced": off[:20],
        "n_displaced": len(off),
        # Frames whose nearest source is not unique — identical pictures, which is what a
        # hold phase IS. Reported rather than resolved silently by index order.
        "n_tied": len(tied),
        "tie_groups": [list(g) for g in groups],
        "tie_atol": tie_atol,
        # How much closer each decoded frame is to its own source than to any other. A
        # thin margin means the order finding is weakly separated and says so, rather
        # than reading as a clean result on a clip whose frames barely differ.
        "min_margin": float(np.min(margins)),
        "median_margin": float(np.median(margins)),
    }
