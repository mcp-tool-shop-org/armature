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


def _f(a):
    return np.asarray(a, dtype=np.float64)


def frame_fidelity(src, dec):
    """Per-frame distance between a source frame and its decoded counterpart."""
    s, d = _f(src), _f(dec)
    if s.shape != d.shape:
        raise ValueError(f"shape mismatch: source {s.shape} vs decoded {d.shape}")
    diff = np.abs(s - d)
    return {
        "identical": bool(np.array_equal(np.asarray(src), np.asarray(dec))),
        "mean_abs": float(diff.mean()),
        "max_abs": float(diff.max()),
        "frac_differing": float((diff.sum(axis=-1) > 0).mean()),
    }


def gradient_split(src, dec, top_frac=0.10, flat_frac=0.50):
    """Mean error over the source's steepest-gradient pixels vs its flattest.

    The clause it exists for: chroma subsampling puts its error at colour edges, so the
    *shape* of the error is evidence about the encoder rather than about the picture. A
    number that is the same in both bands says something different from one that is not,
    and both readings are legible only if the two bands are reported separately.
    """
    s, d = _f(src), _f(dec)
    lum = s.mean(axis=-1)
    gy, gx = np.gradient(lum)
    g = np.hypot(gy, gx).ravel()
    err = np.abs(s - d).mean(axis=-1).ravel()
    order = np.argsort(g)
    n = g.size
    top = order[int(round(n * (1.0 - top_frac))):]
    flat = order[:int(round(n * flat_frac))]
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
    """
    if len(sources) != len(decoded):
        raise ValueError(f"{len(sources)} source frame(s) against {len(decoded)} decoded")
    n = len(sources)
    S = np.stack([downsample(f, step).ravel() for f in sources])
    D = np.stack([downsample(f, step).ravel() for f in decoded])
    nearest, margins = [], []
    for i in range(n):
        dist = np.abs(S - D[i]).mean(axis=1)
        j = int(np.argmin(dist))
        nearest.append(j)
        own = float(dist[i])
        other = float(np.min(np.delete(dist, i))) if n > 1 else float("inf")
        margins.append(other - own)
    on_diagonal = [i for i, j in enumerate(nearest) if j == i]
    off = [(i, nearest[i]) for i in range(n) if nearest[i] != i]
    return {
        "n": n, "step": int(step),
        "nearest": nearest,
        "n_on_diagonal": len(on_diagonal),
        "order_preserved": len(on_diagonal) == n,
        "displaced": off[:20],
        "n_displaced": len(off),
        # How much closer each decoded frame is to its own source than to any other. A
        # thin margin means the order finding is weakly separated and says so, rather
        # than reading as a clean result on a clip whose frames barely differ.
        "min_margin": float(np.min(margins)),
        "median_margin": float(np.median(margins)),
    }
