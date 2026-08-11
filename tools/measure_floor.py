#!/usr/bin/env python
"""measure_floor — the provider's repeat variance, per frame index.

    python tools/measure_floor.py --runs=A0r1,A0r2,A0r3 [--early=0-4] [--late=29-32]

A0. Three identical submissions, same seed, same payload — so every difference between
them is the provider, not us.

**CORRECTED 2026-08-10 (E04). The rationale below was measuring the codec, not the
provider.** It read, and this is kept rather than deleted because the correction is more
useful than the original:

    "**The floor is not a scalar.** The first pass through this data showed the early
    frames of a clip agreeing almost exactly while the late frames diverged badly, which
    means a single number would understate the floor at the end of a clip and overstate
    it at the start."

**That early/late shape was H.264.** E02's A0 re-measured the same three submissions on
the lossless VAEDecode tap and found **33 of 33 frames identical in all 3 pairs — the
fixed-seed floor is exactly zero, at every frame index, early and late alike.** There is
no shape to report because there is no divergence to have a shape. The observed early/late
gradient was the encoder's, and it disappeared when the encoder left the path.

**Why the per-index reporting stays anyway.** It is now the instrument that *proves* the
floor is flat rather than an instrument that assumes it is not: a scalar mean of zero and
a per-index row of zeros look identical on a good run and differ completely on a bad one,
and this tool must be able to catch the day a provider stops being deterministic. The
EARLY/LATE rows stay for the same reason — they are how a returning gradient would
announce itself. **What must not be inherited is the claim that the gradient is there.**

⚠ **This is the fixed-seed floor and nothing else.** Zero here means *re-running one
submission* costs nothing. It says nothing about the spread across *different seeds*,
which is a separate quantity measured by E04, and nothing about any statistic other than
the pixel one — the timing correlation has its own floor and its own instrument
(`measure_tracking.py`).

Read on the **lossless** frames only (`lossless/`, the VAEDecode tap). The earlier floor
came through H.264 on both sides; on this rig the codec alone moves a single generation's
frames by a per-frame max of 43-64, which is the same order as the whole floor being
measured. A floor measured through that is a moving denominator.

Everything here is a diagnostic. Nothing raises, nothing gates, and no arm is graded by
it — it is the denominator every later number is read against.
"""

import argparse
import itertools
import json
import os
import statistics as st

import numpy as np
from PIL import Image


def _stack(run_dir, sub="lossless"):
    d = os.path.join(run_dir, sub)
    names = sorted(n for n in os.listdir(d) if n.endswith(".png"))
    return [np.array(Image.open(os.path.join(d, n)).convert("RGB")).astype(np.int16) for n in names]


def _span(text):
    a, _, b = text.partition("-")
    return list(range(int(a), int(b) + 1))


def pair_stats(A, B, big=8):
    """Per-frame stats for one pair of runs."""
    out = []
    for i, (a, b) in enumerate(zip(A, B)):
        d = np.abs(a - b)
        out.append({
            "frame": i,
            "max": int(d.max()),
            "mean": float(d.mean()),
            "pct_gt": float(100.0 * (d > big).mean()),
            "identical": bool(d.max() == 0),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--root", default="outputs/E02/runs")
    ap.add_argument("--early", default="0-4")
    ap.add_argument("--late", default="29-32")
    ap.add_argument("--big", type=int, default=8)
    ap.add_argument("--out", default="outputs/E02/floor.json")
    a = ap.parse_args()

    runs = [r for r in a.runs.split(",") if r]
    stacks = {r: _stack(os.path.join(a.root, r)) for r in runs}
    n = len(next(iter(stacks.values())))
    early, late = _span(a.early), _span(a.late)

    pairs = {}
    for x, y in itertools.combinations(runs, 2):
        pairs[f"{x}|{y}"] = pair_stats(stacks[x], stacks[y], a.big)

    print(f"A0 — repeat variance on LOSSLESS frames · {len(runs)} runs · {n} frames · "
          f"{len(pairs)} pairs")
    print()
    print("P1 clause A — bit-identical pairs")
    for k, ps in pairs.items():
        ident = sum(1 for p in ps if p["identical"])
        print(f"  {k:<14} frames identical: {ident:>2}/{n}   "
              f"pair bit-identical overall: {'YES' if ident == n else 'NO'}")
    nbit = sum(1 for ps in pairs.values() if all(p['identical'] for p in ps))
    print(f"  => {nbit} of {len(pairs)} pairs are bit-identical")
    print()

    print("THE SHAPE — per-frame max |delta|, every frame, first pair listed per column")
    print("  frame :  " + " ".join(f"{i:>3}" for i in range(n)))
    for k, ps in pairs.items():
        print(f"  {k[:12]:<12}: " + " ".join(f"{p['max']:>3}" for p in ps))
    print()

    def window(ps, idx):
        m = [ps[i]["max"] for i in idx if i < len(ps)]
        g = [ps[i]["pct_gt"] for i in idx if i < len(ps)]
        return m, g

    print(f"EARLY (frames {a.early}) vs LATE (frames {a.late}) — reported separately, always")
    rows = []
    for k, ps in pairs.items():
        em, eg = window(ps, early)
        lm, lg = window(ps, late)
        rows.append((k, em, eg, lm, lg))
        print(f"  {k}")
        print(f"    early  max|d|: min {min(em):>3} median {int(st.median(em)):>3} max {max(em):>3}"
              f"   |  px >{a.big}: {st.mean(eg):.3f}%")
        print(f"    late   max|d|: min {min(lm):>3} median {int(st.median(lm)):>3} max {max(lm):>3}"
              f"   |  px >{a.big}: {st.mean(lg):.3f}%")

    allmax = [p["max"] for ps in pairs.values() for p in ps]
    allpct = [p["pct_gt"] for ps in pairs.values() for p in ps]
    ndiff = sum(1 for ps in pairs.values() for p in ps if not p["identical"])
    print()
    print("WHOLE-CLIP SCALAR — recorded only so it can be compared with the codec-contaminated")
    print("                    first pass. It is NOT the floor; the per-index shape above is.")
    print(f"  frames differing : {ndiff} of {n * len(pairs)}")
    print(f"  per-frame max|d| : min {min(allmax)} · median {int(st.median(allmax))} · max {max(allmax)}")
    print(f"  px differing >{a.big}  : {st.mean(allpct):.3f}%")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({
            "runs": runs, "n_frames": n, "big_threshold": a.big,
            "early_window": early, "late_window": late,
            "pairs": pairs,
            "whole_clip": {
                "frames_differing": ndiff, "of": n * len(pairs),
                "max_min": min(allmax), "max_median": st.median(allmax), "max_max": max(allmax),
                "pct_gt_big_mean": st.mean(allpct),
            },
        }, fh, indent=1)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
