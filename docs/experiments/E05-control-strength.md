# E05 — control strength: where does the model stop copying and start painting?

> # WITHDRAWN 2026-08-10 — its premise is falsified
>
> **This experiment is withdrawn, not deferred.** Its premise was *"the model may be reproducing
> the control rather than painting over it, and if it ever paints, that lives below strength
> 1.0."*
>
> **E02's A1a falsifies it, and A1a was already on disk when this spec was written.** A1a is a
> solid-figure depth control with a reference at `strength` 1.0, and it produced a fully painted
> armoured knight — cape, plate, plinth, studio light, cast shadow — with silhouette and placement
> obeyed from the control. **At full strength, with a body to paint, the model paints.** There is
> no copying problem to sweep for.
>
> Withdrawn rather than re-derived, per the standing law: withdrawing is not choosing a new number,
> and that is the whole difference. **This seat's error is that the deciding artifact existed and
> was not read before the spec was written** — *enumerate the resource before commissioning one*,
> which is this repo's most-repeated law and was missed by the seat that keeps citing it.
>
> **What survives, demoted to a candidate:** A1a's figure is small and plinth-bound where A2's (no
> control) is large and dynamic, so control at 1.0 does appear to constrain **composition and
> scale**. That is a refinement question, not the thesis question, and it waits.
>
> **Superseded by [E06](E06-reference-onto-schematic.md)**, which changes the one variable A1a and
> B1 leave confounded. Nothing below was run and no credits were spent.

---


**Seat:** executor · **Spec written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 4 generations (16 credits); 3 planned,
1 reserved for a fired gate.**

---

## The question

**At what control strength does the model stop reproducing the control and start painting a
subject over it?**

One question. That is the whole scope.

## Why this, and why now

E03's B1 returned a **black stick figure on grey** — the control, re-drawn. The model painted
nothing. armature's one line is *you block the shot; the model shoots it*, and in B1 it did not
shoot; it traced.

E03's closing ruling establishes that its **subject** is the sufficient explanation — a depth pass
of a wire armature *is* a stick figure, and there was no body to dress. **But a second explanation
has never been tested and costs almost nothing to test:**

⚠ **`strength` = 1.0 in every payload armature has ever submitted** — A1a, A1b, B1, B2, B3, read
directly from all five. It has never been varied in any experiment. Consult #3 established there is
no *schedule* on `WanVaceToVideo`, but **the scalar is free**, and full strength is the setting most
likely to produce passthrough.

If the model is ever going to paint life over a previz, that behaviour lives **below 1.0**, and we
have never looked.

## The subject — E02's blackguard control, and why not E03's wire figure

E03's subject cannot answer this question: it has no volume, no face and no costume, so at *any*
strength there is nothing to paint. **E05 uses E02's A1a control sequence** — a near-bright depth
pass of a real character mesh, 33 frames, 480×832, **with E02's reference image** — because it is
the only asset on disk that has a body to dress and a *who* to dress it as.

⚠ **E05 is NOT a turnaround experiment.** A1a's control happens to be a camera orbit, and that is
incidental: this experiment varies **one scalar** and asks what the model does with the freedom it
buys. Motion is E03's question and is not re-asked here. **Do not let the testbed's shape leak into
the conclusion** — that error is on this repo's record already.

## Arms — 3 new generations, 4th reserved

| arm | `strength` | note |
|---|---|---|
| **C-1.00** | 1.00 | **REUSE E02's A1a — already generated, no spend** |
| **C-0.75** | 0.75 | new |
| **C-0.50** | 0.50 | new |
| **C-0.25** | 0.25 | new |

**Everything else byte-identical to A1a's submitted payload** — same seed, both prompts, reference,
all three models, `ModelSamplingSD3` shift, sampler, steps, cfg, and the same 33 uploaded control
frames. **`strength` is the only field that changes**, and the executor verifies that in code by
diffing the payloads before submitting, not by asserting it.

## What is being read, and it is categorical

Two things move in **opposite directions** as strength falls, and the question is whether a band
exists where both are acceptable:

* **fidelity to the control** — is the figure still where the control put it, at the right scale?
* **painted life** — is there a character there, or a re-drawn depth map?

**The read is the Director's eye on a strength-ladder sheet**, and it is categorical: *at which
strength does a character appear, and at which strength does the control stop being obeyed?*

## ⛔ No pass condition, and no metric may rank the arms

There is no threshold here to hit. Report what each arm looks like and let the eye rule.

**Explicitly forbidden by E03's ruling and E02's:** ranking arms on a fine numeric gap. E04 (the
between-generation floor) is **not measured**, so no arm-vs-arm magnitude comparison is readable.
Any diagnostic quoted rides as a diagnostic and **gates nothing**. If a result appears to turn on a
small numeric difference, that is a **halt** — report it and stop.

**And the instrument caution from E03 carries:** the arm-angle/subject classifier was measured
confounded by a lit background gradient on B2. Any instrument reused here states its subject
fraction beside its number, or it is not quoted.

## Predictions — register before looking, blind, each clause separately

- **P1** — at which strengths does a recognisable character appear rather than a re-drawn control?
  Name the strengths *before* looking.
- **P2** — at which strength does control fidelity visibly fail (figure in the wrong place or at
  the wrong scale)?
- **P3** — is there a band where **both** hold? Predict yes/no. **A "no" is a full result** and is
  the more consequential answer, because it would say this control modality and this model cannot
  both obey and invent at once.
- **P4** — does lowering strength change **who** the figure is? E02 measured that prompt and
  reference supply identity; this arm tests whether control strength modulates that. *A row
  predicted to be uninformative is still a prediction and can still miss.*

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | A1a's submitted payload is on disk and re-submittable | **MEASURED** — `outputs/E02/payloads/A1a.json`, read at spec time |
| 2 | `strength` is a scalar FLOAT on `WanVaceToVideo`, no schedule | **MEASURED** — read from the payload; independently confirmed by Comfy consult #3's socket list, which passed calibration against our own graph |
| 3 | A1a carries a `reference_image` | **MEASURED** — present in the payload's `WanVaceToVideo` inputs |
| 4 | `strength` = 1.0 in every armature payload to date | **MEASURED** — all five read |
| 5 | Generation costs 4 credits | **MEASURED** — E02, Director's balance delta |
| 6 | A1a's 33 control frames are still resident server-side under their recorded upload names | **ASSUMED** — verify before submitting; re-upload if not, and say so |
| 7 | Lowering `strength` is a monotone relaxation of control authority | **ASSUMED** — this is the hypothesis, not a fact. If the arms are non-monotone, that is a finding |

## Gates

Inherited and already built: **Gate L** (frame legality, raises in-tool), **Gate B** (batch count
off `BatchImagesNode`), **the lossless tap**, **Gate 0** (control | output | reference | provenance
sheet **before any number is quoted**), **Gate C** (state projected spend before submitting; halt
above the ceiling).

**Gate V — one-variable, verified in code.** Before each submission the builder diffs the arm's
payload against A1a's and **raises** unless the only differing values are `strength` and the output
filename prefixes. Inside the submitting tool, raising, no skip flag. E03's executor did this by
hand and it caught a real confound; here it is a gate.

## Out of scope

Authored motion (E03's question) · identity as a *claim* — P4 observes, it does not adjudicate ·
rigging · any new model, node, LoRA or preprocessor, so **this spec introduces no licence rows** ·
`control_masks` (its own experiment) · frame counts other than 33 · any change to the control
sequence itself.

## Report

Predictions with blind/not-blind first, then the strength-ladder Gate 0 sheet, then observations per
arm, then every gate with a verdict. A gate that did not run is written **NOT YET RUN**. **No
judgement words** — the Director decides whether a character is there.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **3** | Every arm is A1a's byte-identical payload with one scalar varied; models, seed, prompts and control-frame hashes recorded per run. |
| ANDON_AUTHORITY | **3** | Gate V raises in the submitting tool with no skip flag; L/B/C inherited and already firing in E02/E03. |
| NAMED_COMPENSATORS | **2** | Local artifacts are new files under `outputs/E05/` (`rm -r` undoes it). **Spent credits have no compensator**, which is why the ceiling is stated first and Gate C halts. |
| DECOMPOSE_BY_SECRETS | **3** | Payload build, submit, fetch and sheet-building are separate tools; this experiment adds no new seam. |
| UNCERTAINTY_GATED_HUMANS | **3** | No pass condition by design; the strength ladder goes to the Director's eye and the ruling waits on it. |
| EXTERNAL_VERIFIER | **1** | Named rather than inflated: the verifier is the Director's eye plus this seat's ruling — a different *kind* of check, not a different model family. Carries the pipeline's standing remediation. |

**15 / 18.**
