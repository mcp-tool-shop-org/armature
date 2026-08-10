# E02 — first contact: does a CG control sequence hold a character?

**Seat:** executor · **Spec written:** 2026-08-10, before any submission · **Advisor:** rules
after the report · **Director:** judges the sheets.

**This is the hinge.** If a control sequence rendered from geometry does not hold a character
through a real video model, the honest outcome is to say so and stop, and the rest of the arc
is saved. A negative result here is a full success and the roadmap says so in advance.

Grounding: [research-grounding.md](../research-grounding.md) by finding number ·
[license-map.md](../license-map.md) · [E01 ruling](E01-ruling.md) ·
[Comfy consult #1](../comfy-consult-brief-01.md).

---

## Credit ceiling — read before anything else

**Ceiling: 12 generations of 33 frames at 480×832, and not one more without a new ruling.**

Spent credits have no compensator, so the bound is the honest treatment. And per this repo's
rule to bound an expensive arm before spending it:

> **Gate C (ANDON, fires before arm A1):** submit **exactly one** generation, record its actual
> credit cost, and **halt**. Multiply by the remaining arm count. If the projected total exceeds
> the ceiling, report the arithmetic and stop — do not proceed at a reduced arm count, because
> dropping arms silently is how a comparison loses the row that would have falsified it.

## Premises — marked, and this table is under scrutiny

Three advisor premises have been falsified across two dispatches, every one an environmental
fact asserted from a cheap proxy. **A premise is `MEASURED` here only if the measurement tested
the property this spec depends on** — not that the thing exists.

| # | Premise | Status |
|---|---|---|
| 1a | Both graphs exist on Cloud and are licence-clean | **MEASURED** — `get_saved_workflow` at spec time: VACE is 24 nodes (down from 27) with **no LoRA loader of any class**, models `wan2.1_vace_14B_fp16` / `umt5_xxl_fp16` / `wan_2.1_vae` |
| 1b | Both are portrait 480×832 at 33 frames | **ASSUMED — corrected 2026-08-10.** This line originally said MEASURED. It was not: the summary surface exposes node ids, types and model names but **not** widget values, so the dimensions were never read. **The executor verifies `WanVaceToVideo`/`Wan22FunControlToVideo` width, height and length in the graph before the first submission and reports the values.** Fourth instance in this repo of marking a premise MEASURED on a partial check |
| 2 | Wan 2.1 VACE / 2.2 Fun-Control weights are Apache-2.0 and disclaim output rights | **RETRIEVED** — licence documents fetched 2026-08-10, not re-verified since |
| 3 | E01's exporter emits byte-identical frames across runs | **MEASURED** — G3, two process pairs, 0 pixel and 0 byte difference |
| 4 | A lossless encode preserves our frames exactly through the upload path | **ASSUMED — and Gate R exists precisely because it is assumed** |
| 5 | ControlNet-family depth is near-bright | **RETRIEVED for ControlNet, NOT for Wan.** Treated as unknown here — see A1 |
| 6 | The subject is a character | **MEASURED** — the executor opens the GLB and reports its extents in the report's first table, before anything else. E01 was specified on a sword because nobody did this |

## What E02 does NOT do

Out of scope, named so the session ends where it should: the control-strength curve (E04), the
modality comparison (E03), reference-count and identity (E05), multi-shot continuity (E07),
prompt engineering, and any judgement of whether the output is *good*.

---

## Stage 0 — the round-trip gate

**Gate R (ANDON, before any generation).** Encode the control PNG sequence losslessly —
**FFV1 with `-pix_fmt gbrp`** (preferred) or **H.264 `-qp 0 -pix_fmt yuv444p`**. Then decode it
and compare frame-by-frame against the source PNGs. **Assert zero pixel difference. Raise on
any non-zero.**

This gate exists because of a specific, silent failure mode identified in consult #1: `-qp 0`
alone is *luma*-lossless while x264 still defaults to `yuv420p`, which subsamples chroma 4:1.
Our depth, mask and edge channels are grayscale (R=G=B, zero chroma, survives) — but the
**normal** channel is true RGB, so subsampling would corrupt precisely the channel F1 measured
as load-bearing, and **the video would look correct**.

There is no folder loader on Comfy Cloud — verified independently at spec time, not taken from
the consult — so encoding is the only supported bridge and this gate is the price of it.

## Stage 1 — the noise floor, measured before anything is compared

**A0 — repeat variance.** Submit the *same payload with the same seed* **three times**.

Report, per pair: mean and max per-pixel difference, and whether any pair is bit-identical.
**Every later number in this experiment is read against this floor.** A single-run comparison
has no noise floor, and consult #1's Q6 went unanswered, so we do not know whether this
provider is deterministic. Assume it is not until A0 says otherwise.

## Stage 2 — the arms

Each varies **one** thing. Trace what each parameter feeds before running: "one variable" is a
property of the dependency graph, not of the field you edited.

| arm | varies | why |
|---|---|---|
| **A1a / A1b** | depth polarity: near-bright vs near-dark | Premise 5 is unknown for Wan. **Measured, not inherited** — getting it backwards produces a completed run with wrong numbers, and no error anywhere |
| **A2** | control removed entirely (same prompt, same reference, no control video) | **The thesis test.** Without this row there is nothing to compare the controlled runs *to*, and "the character stayed put" means nothing |
| **A3** | VACE → Fun-Control, control held constant | Cross-implementation. If A1/A2 fail on one route we cannot otherwise distinguish "CG control does not work" from "this implementation does not" |

**⚠ Named confound, carried deliberately.** VACE runs fp16 diffusion + fp16 text encoder;
Fun-Control runs fp8 for both. So A3 varies implementation **and** precision. For E02 that is
acceptable because the two routes are read independently — each answers *does control hold on
this route*. **A3 may not be used to difference the two routes.** Any later experiment that
does must match precision first.

## Stage 3 — integration traps, closed before the first submission

Found by reading the built graphs at spec time. Each is a halt if not closed:

1. **The `Canny` node (VACE id 147) must be bypassed.** The template derives edges by running
   Canny on the loaded video. We render a geometric edge channel precisely to avoid Canny's
   per-image threshold tuning, which does not generalise across shots. Leaving it in re-derives
   edges *from our own depth render* — a proxy inheriting every failure mode of the thing it
   stands in for.
2. **Template prompts are still the defaults** — a dancing-girl-in-flowers positive and a
   Chinese boilerplate negative. They will silently drive the run if not replaced.
3. **Node 149's markdown still describes the deleted CausVid LoRA.** Corrected text is in the
   consult thread; it is an editor-only edit.

## Gates

Gates raise inside the tool performing the irreversible step. No shell chaining, no bare
`assert`, no skip flag.

- **Gate R** — the round-trip, above. Fires before any credit is spent.
- **Gate C** — the credit bound, above. One generation, then halt and do the arithmetic.
- **Gate L** — frame legality: dims divisible by 16, count ≡ 1 (mod 4). Note the node schema
  enforces **neither** (`length` min 1, max 16384), so nothing upstream will catch an illegal
  frame count. This gate is the only thing standing there.
- **Gate 0 — the sheet before the metrics.** No number is quoted anywhere in the report until a
  **control | output | reference | provenance** sheet exists for every arm. facet ran four arms
  and two gates before building this sheet; when it finally existed the Director read the whole
  thesis off one panel.

## Predictions — register before looking, state whether blind

Write what one of the counted thing **is** before the number. Predict each clause of a
conjunction separately, then the join.

- **P1** — Of 3 identical submissions, how many pairs are bit-identical? And if none, what is
  the mean per-pixel difference between the closest pair?
- **P2** — Which polarity holds structure better, and by how much on your chosen unit? State
  the unit before you look, and pick one the arms cannot move.
- **P3** — **The thesis.** Between A2 (no control) and the better of A1a/A1b, will the character
  be in the same place at the same time? State what you would accept as "held" *before* running,
  in terms an eye can check on the sheet, not a metric.
- **P4** — Does A3 (Fun-Control) agree with VACE on P3's verdict? A row you predict to be
  uninformative is still a prediction and can still miss.

## Report

In this order: subject extents first (premise 6); registered predictions with blind/not-blind;
Gate R and Gate C verdicts before anything else; A0's floor; the Gate 0 sheets; then measured
values beside their predictions; then every gate with a verdict — a gate that did not run is
written **NOT YET RUN**, never a plausible identifier with a result beside it.

**No judgement words.** Whether the figure on screen is the right character is canon, and no
metric approximates it — the Director judges the sheets.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | Workflow filenames pin the graphs **by content, not by bytes** — see the note below. Every submission records payload, seed, model ids and control-input hashes. Not 3 until a replay is demonstrated. |
| ANDON_AUTHORITY | **2** | Gates R, C, L and 0 each halt. Not 3 until one fires on a real defect. |
| NAMED_COMPENSATORS | **2** | **Spent credits have NO compensator** — stated, not skipped. The bound (Gate C) is the honest treatment of an unrecoverable action. Uploaded assets: `delete_uploaded_control_video`, owner executor. |
| DECOMPOSE_BY_SECRETS | **2** | Encode/upload, submission, and measurement are separate stages; the graphs are external artifacts pinned by name. |
| UNCERTAINTY_GATED_HUMANS | **3** | Gate 0 is a human checkpoint by construction — the Director sees the sheet before any metric is read, and P3's pass condition is defined in terms an eye checks rather than a number. |
| EXTERNAL_VERIFIER | **2** | The executor does not grade its own output. A3 is a second implementation checking the first. Not 3 until a different-family check runs on an E02 artifact. |

**13 / 18.** No row below 2; no remediation item required.

### ⚠ How the graphs are pinned — measured, because the obvious answer is wrong

**A saved workflow's file size changes without the graph changing.** Measured 2026-08-10:
between two listings minutes apart, with **identical modified timestamps**, the byte sizes moved
— VACE 26431 → 26436, Fun-Control 56129 → 56102. Re-fetched, the VACE graph is **semantically
identical**: same 24 node ids and types, same models, same prompts, same seed.

So the bytes drift under server-side re-serialization while the graph stands still. This is
facet's law in a new place — *a byte mismatch is not evidence the content changed* — and it
matters because a naive byte-hash pin would produce a **false halt** on an unchanged graph,
which this lineage has already paid for twice with PNG hashes.

**The pin is therefore the parsed graph, not the file.** Any replay check normalizes the JSON
before hashing (canonical key order, whitespace stripped) and compares node ids, types, links
and widget values — never raw bytes. `modified` is also not a change signal here: it did not
move when the size did.

**Also measured: bookmarking does not promote a workflow.** After the Director bookmarked both,
`workflow_id` is still `null` and the paths are still bare filenames rather than `workflows/…`.
Bookmarking is a UI convenience; the record tier remains unreached and is a manual editor step.
