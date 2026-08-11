# E03 — registered predictions

**Registered 2026-08-10, before any submission to any generator.** Committed on its own so
its timestamp is git's and not a seat's.

---

## Blindness disclosure — precise, because "blind" is a claim

**Blind to:** all three generations. Nothing has been submitted to Comfy Cloud. No video
model has rendered anything for E03. B1, B2 and B3 do not exist.

**NOT blind to, and each of these could bias a prediction:**

1. **The control sequences.** I rendered them, and I have looked at their manifests — mask
   bounding boxes, gate verdicts, depth windows. I know the control moves and exactly how.
2. **The instrument's calibration.** `measure_arm.py` was run on the *control* frames and
   checked against the control's own authored ground truth **before** this file was written.
   That is deliberate — an instrument whose error is unknown cannot support a tolerance —
   and it is disclosed because the calibration number is what P1's tolerance is built from.
   It involved no generated output.
3. **E02's results**, including the closing ruling: control governs placement, scale and
   timing; polarity does not break tracking; the no-control null is not empty; and no
   single-run gap between two arms may be read as an ordering.

---

## ⚠ A readout the spec specified cannot be measured, and what replaced it

The spec asks for **"the frame index at which it passes horizontal"** while specifying the
motion as **"from T-pose to overhead"**. Those are inconsistent: a T-pose arm *starts*
horizontal, so it never passes horizontal — it leaves it on frame 0, and a readout that
answers 0 for every possible outcome is one the arm cannot move. That is the one property
this repo forbids a readout to have.

**Replaced, before anything was rendered and before this registration, with the midpoint
crossing:** the frame at which the arm passes **45°**, halfway through the authored arc.
Monotonic, crossed exactly once, unambiguous by eye, and authored rather than measured.
`leaves_start_frame` and `reaches_end_frame` are reported beside it so the spec's original
intent is still answerable from the record.

**This is flagged for the advisor to overrule.** It changes how a registered prediction is
read. It was made before the prediction existed, which is the only reason it is a correction
rather than a retune.

**The authored crossing is frame 16.0** — exact, landing on an integer frame, from
`arc_readout`: `(45 − 0) / 90 × 32 = 16`.

---

## The instrument, and its measured error

`measure_arm.py` classifies subject vs background, takes the pixels in an annulus about the
projected shoulder, and reports the angular lobe they fall in. Run against the **control**,
whose true per-frame joint positions are authored:

| | |
|---|---|
| authored crossing frame (45° arc angle) | **16.000** |
| authored crossing in **image** space (the camera sits 8° above the horizon) | 44.921° |
| **measured** crossing frame on the control | **16.323** |
| **instrument error on a signal with known truth** | **0.32 frames** |
| bias across frames 0–28 | −0.9° ± 0.05, near-constant |
| bias at frame 32 (arm vertical) | −5.7° — the annulus keeps only the right hemisphere, so a vertical arm is clipped |
| subject fraction, all frames | 0.0496–0.0498 — stable, so the segmentation is not drifting |

**It is a diagnostic and it gates nothing.** The spec chose an arm raise so the answer is
readable by eye off a sheet with no pose estimator involved. This repo has twice recorded a
metric returning confident numbers about something it could not see, and E02 dropped a
modal-background coverage measure for the confound this one could hit. If the segmentation
on a generated frame is implausible, **the angle is reported as failed, not as a number.**

---

## P1 — does the output move with the subject, and at the right time?

**What one of the counted thing is:** a frame index, 0–32, at which the figure's raised arm
passes 45° above horizontal — measured on the arm that is on the **right-hand side of the
image**, which is where the control's `_r` arm appears (measured: the control's mask right
edge travels 382 → 287 px while its top edge climbs 262 → 214 px).

**Clause A — categorical, and this is the clause that matters.** Does B1's figure raise an
arm from horizontal to overhead across the 33 frames? **Prediction: YES.**

**Clause B — the tolerance, stated before measuring, as the dispatch requires.**

> **I would accept ±3 frames as "the same time."**

Chosen for two reasons, both fixed before any output exists:
- it is **~10× the instrument's measured error** on the control (0.32 frames), so a result
  inside it cannot be an artifact of the instrument;
- it is **under 10% of the shot** (3 of 33 frames ≈ 190 ms at 16 fps), so an arm arriving
  inside it is following the control's schedule rather than keeping its own.

**Prediction on clause B: B1's measured crossing frame lands within ±3 frames of 16.0,
i.e. in [13, 19]. Point estimate: frame 18** — I expect the output to *lag*, because a
diffusion video model eases into motion and E02's A1a tracked the control's timing at
+0.521 rather than at 1.0.

**Clause C — SUSPENDED, deliberately.** "How closely does B1 track compared to B3 or to the
control" is a magnitude comparison across single generations, which Amendment 1 puts out of
bounds. Numerator and denominator are reported separately and nothing is ranked.

**Where I expect to be wrong if I am wrong:** that the arm rises but *not monotonically* —
it drifts up, falls back, and rises again — in which case a single crossing frame is the
wrong summary and the honest report is the whole angle series with the crossing marked
undefined.

## P2 — does the static control produce a moving figure anyway?

**Clause A — the discriminator, categorical.** Does B3's figure raise an arm?
**Prediction: NO.**

Reasoning: B3 is not the unconstrained case. E02's A2 invented motion because *nothing*
constrained it; B3 carries a full control sequence at strength 1.0 that says "hold this
pose", and E02 established that the control governs *when* the figure moves. A model that
raised an arm here would be overriding an explicit instruction, not filling a vacuum.

**Clause B — separately, because a conjunction must be predicted clause by clause.** Does
B3's figure show *any* motion — drift, sway, background movement, breathing?
**Prediction: YES.** Some residual motion is near-certain; a video model asked for a figure
in a studio will not produce 33 identical frames, and the negative prompt no longer says
"static". This clause is why clause A is about **the arm** and not about motion in general.

**Confidence:** moderate on A, high on B. **A is the prediction I most expect to miss**, and
if I do — if B3's arm rises too — that is the most valuable outcome E03 can produce, because
it would mean B1's rising arm is the model's habit rather than our authored motion.

## P3 — what does the model do with a shape that is not a person?

Does B1's figure keep the wire-armature look, or does the model dress it as something else?

**Prediction: it does NOT keep the wire look. The model renders a solid, person-like
figure** — limbs with volume, a head with a face, some implied clothing or skin — using the
control only for pose and placement.

Reasoning: the prompt names "a single figure" and says nothing about material or costume, so
the strongest prior available to the model is a human body; E02's A2 showed it will invent a
complete costumed character from prompt alone, and E02's ruling recorded that the control
supplies *where and when* while prompt and reference supply *who*. A control that says "a
thin stick figure" is being read for structure, not for material.

**Bounded, and stated because it limits what P3 can conclude:** the prompt does say there is
a figure. So this predicts what the model does with a *non-human shape*, not what it does
with no guidance at all.

**Not identity.** This subject carries none — no face, no costume, nothing a reference could
preserve or lose. Nothing in P3 may be read as an identity result.

---

## What is NOT predicted

- Any ranking of B1 against B3 or against the control on a magnitude. Out of bounds under
  Amendment 1 at one generation per arm.
- Anything about control strength, cuts, length, reference stacks, or whether any output is
  *good*. The Director judges the sheet.
