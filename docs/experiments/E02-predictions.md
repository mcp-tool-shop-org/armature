# E02 — registered predictions

**Registered 2026-08-10, before any submission to any generator.** This file is
committed on its own so its timestamp is git's and not a seat's. E01's blindness
evidence existed only by luck (an advisor error timestamped the executor's file); here
it is deliberate.

## Blindness disclosure — precise, because "blind" is a claim

**Blind to:** every generation output. No payload has been submitted to Comfy Cloud or
any other generator at the time of writing. Nothing has been rendered by any video
model. A0 has not run.

**NOT blind to:** the two saved graphs' configuration. Reading them was required by the
spec (premise 1b demanded the executor verify width/height/length before submitting),
so at registration time I know both graphs' dimensions, seeds, samplers, prompts, model
files and node modes. I also know the subject's extents (premise 6). None of these are
results of the thing being predicted, but the distinction is stated rather than left for
someone else to work out.

---

## P1 — repeat variance

**What one of the counted thing is:** an unordered *pair* of submissions drawn from the
three identical A0 runs — so three pairs (AB, AC, BC). "Bit-identical" means the decoded
frame sequences are equal at every pixel of every one of the 33 frames.

**Clause A — how many of the 3 pairs are bit-identical: `0`.**

**Clause B — conditional on clause A, the mean per-pixel absolute difference of the
closest pair: `12 / 255`** (8-bit, over all channels and all 33 frames).

**The structural claim, which is the part worth being wrong about:** I predict the
result is *bimodal and lands on the far mode*. Diffusion sampling is chaotic — a
perturbation at an early denoising step is amplified rather than averaged out. So if
there is any nondeterminism at all, I expect a **visibly different take of the same
shot** (mean |Δ| well above 5/255), not a rounding-level difference (below 2/255). A
result in the 2–5/255 band would falsify the reasoning even if it happened to bracket
the number.

**Confidence:** low on clause A, moderate on the structural claim. If the provider pins
GPU model, container and kernel selection, 3/3 bit-identical is entirely plausible and I
would not be surprised.

## P2 — depth polarity

**Registered before looking, and the magnitude clause is deliberately not a threshold I
invented.**

**Clause A — direction: `A1a` (near-bright) holds structure better than `A1b`
(near-dark).** Reasoning: the ControlNet-family convention is near-bright inverse-relative
depth (F24 / consult #1), and Wan's control-video path is trained against preprocessor
output following that convention. Premise 5 records this as retrieved for ControlNet and
**not** for Wan, which is exactly why it is an arm and not an assumption.

**Clause B — the unit, stated before looking, chosen because the arms cannot move it:**
mean per-pixel absolute difference **between A1a's and A1b's outputs**, read against
**A0's measured noise floor**. This unit has the floor/ceiling property the repo demands:
if polarity is irrelevant to the model, A1a-vs-A1b collapses to the A0 floor; if it
matters, it exceeds it. The arms cannot move the floor, because the floor is measured
from three runs that do not vary polarity at all.

**Prediction on clause B: A1a-vs-A1b exceeds A0's floor by more than 3x.**

**Clause C — "by how much" in the sense of *which is better*: SUSPENDED, deliberately.**
There is no calibrated unit for "holds structure better" available in E02 without adding
a segmentation or depth estimator, and every candidate is either (a) circular — ranking
generated luma against the control depth that produced it just reports the arm's own
input back, or (b) a new dependency with no row in `docs/license-map.md`, which the
license gate forbids from entering inside an experiment. Per the advisor rule *suspend
rather than invent a threshold*, this clause is reported as the Director's eye-judgement
on the Gate 0 sheet, numerator and denominator separately, and no number is manufactured
for it.

## P3 — the thesis

**What "held" means, defined before running, in terms an eye checks on the sheet and not
a metric:**

Overlaying the control frame and the generated frame at the same frame index, the figure
is **held** when both are true, judged by eye at full size:

1. **Place** — the generated figure's torso sits over the control silhouette, displaced by
   no more than roughly its own torso width; and
2. **Facing** — the direction the body is turned tracks the control's orbit angle, so that
   over the 33 frames the generated figure turns the same way, through the same
   quarter-turns, at the same frame indices.

Counted the way a count should be: **the number of frames, out of 33, satisfying both
clauses.**

**Prediction — each clause separately, then the join:**

| | controlled arm (better of A1a/A1b) | A2 (no control) |
|---|---|---|
| Place | held in **30** of 33 frames | held in **4** of 33 frames |
| Facing | held in **28** of 33 frames | held in **2** of 33 frames |
| **Join (both)** | **27** of 33 | **1** of 33 |

**The thesis passes** if the controlled arm holds and A2 does not. I predict it passes.

**Where I expect to be wrong if I am wrong:** the failure mode I consider most likely is
not "no control at all" but **control without identity** — the figure tracks the orbit
correctly while not looking like the blackguard. That would satisfy P3 fully and still
leave the arc's real question open, because whether the figure is the right character is
canon and E05's subject, not a thing P3 can pass or fail.

**Secondary risk, named because it would confound the read:** A2 has no control video and
therefore no camera orbit driving it. If A2 simply produces a near-static shot, "A2 did
not track the orbit" is nearly tautological. I register in advance that a near-static A2
is a **weak** falsification of the null, and that the informative comparison is whether
the controlled arm's motion matches the control's *specific* orbit rather than merely
being non-static.

## P4 — cross-implementation agreement

**Clause A — does Fun-Control (A3) reach the same verdict as VACE on P3: `yes, agrees` —
both hold.**

**Clause B — measured before predicting, and it changes what A3 can mean:** the spec names
one confound (VACE fp16 vs Fun-Control fp8). Reading the graphs, there are **three**
differences, not one:

1. precision — fp16 diffusion + fp16 text encoder vs fp8 for both;
2. sampler — VACE runs a single 30-step `uni_pc` at cfg 6; Fun-Control runs the Wan 2.2
   two-expert split, `KSamplerAdvanced` 0→10 on the high-noise model then 10→10000 on the
   low-noise model, 20 steps at cfg 3.5;
3. **conditioning shape** — `Wan22FunControlToVideo` takes a **start image** and exposes
   **no `strength` widget at all**, where `WanVaceToVideo` takes a `reference_image` and a
   `strength` (currently 1.0).

The third was not in the spec and is the one that matters most: A3 is not "the same
experiment at lower precision", it is a differently-conditioned route. The spec's own
ruling — **A3 may not be used to difference the two routes** — is therefore correct for a
stronger reason than the one it gives, and I am recording that before running rather than
after.

**Confidence:** low. This is the prediction I most expect to miss.

---

# P2 — re-registered before A1b runs (2026-08-10)

**Registered before any A1b submission exists.** Blind to A1b entirely: no inverted frames
have been uploaded and no generation has been requested at the time of writing. Not blind
to A1a, A2 and the floor, all of which are measured and reported.

## Withdrawal — the original clause B is degenerate, and the floor is why

The clause registered at the top of this file read:

> **Clause B — the unit:** mean per-pixel absolute difference **between A1a's and A1b's
> outputs**, read against **A0's measured noise floor** … **Prediction: A1a-vs-A1b exceeds
> A0's floor by more than 3x.**

**A0's floor measured exactly zero.** Any difference whatsoever is more than 3x zero, so the
condition can no longer fail. That is this repo's own disqualifier — *a check that cannot
fail is not a check* — and the fault is mine: I picked a unit defined as a multiple of a
quantity that had not been measured yet, which is the same shape as defining a pass
condition as a fraction of an unmeasured number.

**Withdrawn, not re-derived.** The repo's rule is to withdraw a broken condition rather than
retune it while looking at the results it would judge. What follows is a fresh
pre-registration, and it is legitimate as one because **A1b does not exist yet** — the floor
is not A1b's result.

## What I predict

**Direction: WORSE than A1a, but not "not at all".**

The mechanism, stated so it can be wrong for a reason. Inverting is not only a depth-polarity
flip. In A1a the background is 0 (black) and the subject is bright; after `255-x` the
background is 255 (white) and the subject is darker than its surround. So **figure/ground
contrast inverts as well as depth ordering**, and a white field reading as "nearest" is
strongly out of distribution for a depth control. But the silhouette *boundary* survives
inversion untouched — an edge is an edge at either polarity — so I expect the model to still
find and place the figure while reading its interior structure wrongly.

## What I would accept as "as well" — stated before measuring

Judged by eye on the A1a-vs-A1b sheet, at full size, at the same frame indices:

- **AS WELL** — for at least **28 of 33** frames, A1b's figure occupies the same region of
  frame and shows the same facing as A1a's. That is: the two controlled arms are
  interchangeable on placement and facing to the Director's eye.
- **WORSE** — the figure is present and roughly placed, but structure or facing visibly
  degrades on a meaningful number of frames relative to A1a.
- **NOT AT ALL** — the figure does not track the control's orbit; A1b reads closer to A2
  (unconstrained) than to A1a.

**I predict WORSE.**

## Numeric diagnostics, gating nothing, floor now known to be 0

Registered as numbers so they can miss:

| quantity | registered prediction |
|---|---|
| temporal-timing correlation vs control (same unit as A1a +0.521, A2 −0.064) | **+0.30** — positive and tracking, weaker than A1a |
| is A1b nearer A1a or A2 on that unit? | **nearer A1a** |
| mean abs delta A1a vs A1b, whole clip, 0-255 | **> 0** and read directly, because the floor is 0 |

The timing correlation has the floor/ceiling property the repo asks for: an arm ignoring the
control sits near 0 (A2 measured −0.064), an arm following it sits well above (A1a measured
+0.521). A1b cannot move that scale; it only takes a position on it.

**Where I expect to be wrong if I am wrong:** that the model is more polarity-agnostic than I
think, because the silhouette carries most of the placement information and the interior
gradient carries little of it at strength 1.0. If that is so, A1b comes out AS WELL and my
direction call is simply wrong.
