# E06 — can a reference image put a character onto a schematic control?

**Seat:** executor · **Spec written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 3 generations (12 credits); 2 planned,
1 reserved for a fired gate.**

---

## The question

**E03's B1 had an animated control and no reference, and came back a bare diagram. If we give the
same control a reference image, does a painted character appear on it — performing?**

One question. That is the whole scope.

## Why this is the next experiment, and why it may be worth more than its cost

Two measurements make it askable, and both are already in hand:

* **A1a (E02)** — solid depth control **+ reference** → a fully painted armoured knight. **The model
  paints when there is a body to paint.**
* **B1 (E03)** — schematic wire control **+ no reference** → a black stick figure. **The model traces
  when there is not.**

Those differ in **two** things at once: the subject's volume *and* the presence of a reference.
**E06 changes exactly one of them.** It takes B1's control, unchanged, and adds a reference.

**What hangs on it.** armature's blocking dependency is the rigging gap — E01 measured that every
rig here names its bones `bone_0 … bone_29`, so the blackguard cannot be posed on purpose, and E03
routed around that with a wire figure it could pose. **If a reference can supply the body while a
posable wire armature supplies the performance, then authored motion on a real character is
available now, without rigging anything.** That is the whole product, unblocked by one generation.

If instead the control's thin silhouette dominates and D1 returns a stick-shaped knight, **the
rigging gap is confirmed as the real blocker** and we stop looking for a way round it. Both answers
are decisive; neither is a consolation.

## Arms — a one-variable ladder, 2 new generations

| arm | control | reference | prompt | status |
|---|---|---|---|---|
| **B1** | E03 posearc (animated wire) | **none** | generic | **already generated — the baseline, no spend** |
| **D1** | **same, byte-identical** | **E02's blackguard A-pose plate** | generic, **unchanged from B1** | new |
| **D2** | same | same | **names the character** | new |

**Each step differs from the one above it by exactly one thing** — D1 adds the reference, D2 changes
the prompt. Everything else stays byte-identical to B1's submitted payload: seed, negative,
`WanVaceToVideo` width/height/length/strength, all three models, `ModelSamplingSD3` shift, sampler,
steps, cfg, and the same 33 uploaded control frames.

**D2 exists because of a standing law, not as a spare arm.** facet: *if a canon element is not named
in the prompt, it is arriving by accident and will leave the same way.* E03's prompt names no
identity at all — B2 proved it, resolving "a figure" into a woman nobody chose. D1 tests whether a
reference alone carries identity; **D2 tests the configuration we would actually ship**, where the
canon element is named. Running D1 without D2 would answer a question we do not intend to ship.

**Assets — both already uploaded, verify before re-uploading:**
`outputs/E02/uploads_reference.json` → `71836f47…png` · `outputs/E03/uploads_posearc.json` → 33
frames.

## What is being read, and it is categorical

Three things, in this order, judged on a **control | output | reference | provenance** sheet before
any number is quoted:

1. **Is there a painted character at all**, or a re-drawn diagram?
2. **Does it perform?** The control's arm rises 0°→90° across the 33 frames. Does the output's?
3. **Is it the same man as the reference?** ⚠ **Canon, and the Director's alone.** No metric here
   approximates it; facet learned that twice. Any identity diagnostic rides as a diagnostic and
   **gates nothing**.

## ⛔ No pass condition, and nothing may be ranked on a magnitude

E04 (the between-generation floor) is **not measured**, so no arm-vs-arm numeric ranking is
readable. Every diagnostic is a diagnostic. **If a result appears to turn on a small numeric gap,
that is a halt** — report it and stop.

**Instrument caution, carried from E03:** the arm-angle/subject classifier was measured confounded
by a lit background gradient on B2 (subject fraction 0.456 against 0.050–0.054 elsewhere). Any
instrument reused here quotes its subject fraction beside its number or is not quoted at all. **The
arm-rise read for question 2 is by eye on the sheet**, not by that classifier.

## Predictions — register before looking, blind, each clause separately

- **P1** — does D1 produce a painted character, a diagram, or something between? Name it before
  looking.
- **P2** — does D1's arm rise? Predict yes/no. *This is the clause that decides whether the rigging
  gap can be routed around, so predict it on its own and not as part of P1.*
- **P3** — does D1's figure carry the reference's **silhouette** (bulk, cape, helm) or the
  **control's** (thin tubes)? This is the mechanism question: which input owns the outline.
- **P4** — does naming the character in D2's prompt change identity, surface, or neither, relative to
  D1? *A row predicted to be uninformative is still a prediction and can still miss.*

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | B1's submitted payload is on disk and re-submittable | **ASSUMED** — verify at `outputs/E03/payloads/B1.json` before building; if absent, rebuild from the spec and say so |
| 2 | `reference_image` is an optional IMAGE input on `WanVaceToVideo` and B1 omitted it | **MEASURED** — B1's payload read at spec time; confirmed against the consult's socket list, which passed calibration |
| 3 | E02's reference plate is uploaded and still resident under its recorded name | **ASSUMED** — verify server-side before submitting; re-upload if not, and say so |
| 4 | E03's 33 posearc frames are uploaded and still resident | **ASSUMED** — same |
| 5 | Adding a reference does not loosen control authority over position | **ASSUMED** — this is P3's question, not a fact |
| 6 | Generation costs 4 credits | **MEASURED** — E02, Director's balance delta |

## Gates

Inherited and already built: **Gate L** (frame legality, raises in-tool), **Gate B** (batch count off
`BatchImagesNode`), **the lossless tap**, **Gate 0** (the sheet **before** any number), **Gate C**
(projected spend stated before submitting; halt above ceiling).

**Gate V — one-variable, verified in code.** Before each submission the builder diffs the arm's
payload against its predecessor and **raises** unless the only differing values are the intended one
(D1: the reference link; D2: the positive prompt) plus output filename prefixes. Inside the
submitting tool, raising, no shell chain, no `assert`, no skip flag.

**A gate that fires is reported with its evidence and the session halts.** Never change a parameter
and re-run to get past one.

## Out of scope

Control strength — **E05 is withdrawn**, its premise falsified by A1a · control modality (seg/ID,
canny, normals — recorded in `docs/comfy-consult-3.md`, not tested here) · rigging itself · frame
counts other than 33 · `control_masks` · any new model, node, LoRA or preprocessor, so **this spec
introduces no licence rows**.

## Report

Predictions with blind/not-blind first, then the Gate 0 sheet, then observations per arm against
predictions, then every gate with a verdict. A gate that did not run is written **NOT YET RUN**.
**No judgement words.** Whether it is the same man is the Director's call and no sentence in the
report may pre-empt it.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **3** | Each arm is its predecessor's byte-identical payload with one field changed; models, seed, prompts, reference and control-frame hashes recorded per run. |
| ANDON_AUTHORITY | **3** | Gate V raises in the submitting tool with no skip flag; L/B/C inherited and already firing across E02 and E03. |
| NAMED_COMPENSATORS | **2** | Local artifacts are new files under `outputs/E06/` (`rm -r` undoes it). **Spent credits have no compensator** — hence the ceiling before the first submission and a halting Gate C. |
| DECOMPOSE_BY_SECRETS | **3** | Build, submit, fetch and sheet-building stay separate tools; no new seam. |
| UNCERTAINTY_GATED_HUMANS | **3** | No pass condition by design; the identity question is routed to the Director explicitly and no metric may pre-empt it. |
| EXTERNAL_VERIFIER | **1** | Named rather than inflated — the verifier is the Director's eye plus this seat's ruling, a different *kind* of check rather than a different model family. Carries the pipeline's standing remediation. |

**15 / 18.**
