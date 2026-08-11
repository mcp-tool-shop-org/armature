# E06 — does a reference image put a character onto a schematic control?

**Seat:** executor · **Spec written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 3 generations (12 credits); 2 planned,
1 reserved for a fired gate.**

*Revised 2026-08-10 before dispatch: an earlier draft of this file was written and never issued to a
seat. It required a new gate in `tools/build_payload.py`; enumeration of that file showed the gate
it needed **already exists**. Nothing was run under the earlier draft and no credits were spent.*

---

## The question

**Two runs exist. They differ in two things. This changes one of them.**

| run | control | reference | result |
|---|---|---|---|
| **A1a** (E02) | depth pass of a solid character mesh | **present** | a fully painted armoured knight — cape, plate, plinth, studio light, cast shadow |
| **B1** (E03) | depth pass of a wire armature, animated | **absent** | a black stick figure on grey |

**E06 takes B1's control, byte-identical, and adds a reference.**

That is the whole scope.

## What hangs on it

armature's blocking dependency is the rigging gap. E01 measured it: every rigged asset on this rig
names its bones `bone_0 … bone_29`, and **zero of 18 anatomical sites are identifiable by name in
any of them**, so the character mesh cannot be posed on purpose. E03 routed around that by building
a wire figure it *could* pose — and got a figure with no body.

**If a reference supplies the body while a posable wire armature supplies the performance, authored
motion on a character is available without rigging anything.** If instead the control's thin
silhouette dominates, the rigging gap is confirmed as the real blocker and we stop looking for a way
around it.

Both outcomes are decisive. Neither is a consolation prize.

## Arms — 2 new generations, one variable per step

| arm | control | reference | prompt | status |
|---|---|---|---|---|
| **B1** | E03 posearc | **absent** | generic | **already generated — the baseline, no spend** |
| **D1** | same, byte-identical | **E02's A-pose plate** | generic, unchanged | new |
| **D2** | same | same | **names the character** | new |

Everything not named in the table stays byte-identical to B1's submitted payload: seed, negative
prompt, `WanVaceToVideo` width/height/length/strength, all three models, `ModelSamplingSD3` shift,
sampler, steps, cfg, and the same 33 uploaded control frames.

**D2 is not a spare arm.** facet's law: *if a canon element is not named in the prompt, it is
arriving by accident and will leave the same way.* E03's prompt named no identity, and B2 showed
what that means — "a figure" resolved into a person nobody chose. **D1 isolates what a reference
does on its own; D2 is the configuration we would actually ship.** Running only D1 would answer a
question we do not intend to ship.

**Assets, both already uploaded — verify server-side residency before re-uploading:**
`outputs/E02/uploads_reference.json` → `reference_apose_0` ·
`outputs/E03/uploads_posearc.json` → 33 frames.

## Tooling — enumerated first, and it needs less than it looks

**Verified in `tools/build_payload.py` at spec time:**

* An `EXPERIMENTS` table already keys arms by experiment and carries a **`reference`** field per
  experiment — E02's is populated, E03's is explicitly `None` with its reason in a comment.
* **`verify_topology(..., expects_reference=...)` already binds the reference in BOTH directions**
  and raises when an arm's reference presence does not match what its experiment declares. Its own
  docstring states the reason: *a reference that differs between arms is a second variable.*

**So E06 needs an `EXPERIMENTS` entry, not a new gate.** The load-bearing dimension of this
experiment — reference present versus absent — is already gated by a check that was built for
exactly this hazard and is already under test.

**What rides the commit:** the new entry, its arms, and tests for them. `tests/test_build_payload.py`
already pins E02's submitted payload **bytes**; that pin must still pass unchanged, and it is the
regression net for everything below.

## Gates

All inherited and already built — **this experiment commissions none**:

* **Gate L** — frame legality, raises inside the tool.
* **Gate B** — batch count off `BatchImagesNode`.
* **The lossless tap** — enforced by `verify_topology`.
* **`expects_reference`** — the one-variable guard for this experiment's variable, above.
* **Gate 0** — the **control | output | reference | provenance** sheet **before any number is
  quoted**.
* **Gate C** — state projected spend before submitting; halt above the ceiling.

**A gate that fires is reported with its evidence and the session halts.** Never change a parameter
and re-run to get past one.

## What is read, and it is categorical

On the Gate 0 sheet, in this order:

1. **Is there a painted character at all**, or a re-drawn diagram?
2. **Does it perform?** The control's arm rises 0° → 90° across the 33 frames. Does the output's?
3. **Is it the same man as the reference?** ⚠ **Canon, and the Director's alone.** No metric here
   approximates it — this repo has learned that twice. Identity diagnostics ride as diagnostics and
   **gate nothing**.

## ⛔ No pass condition, and nothing is ranked on a magnitude

E04's between-generation floor is **not yet measured**, so no arm-vs-arm numeric ranking is
readable. Every diagnostic is a diagnostic. **If a result appears to turn on a small numeric gap,
that is a halt** — report it and stop.

**Instrument caution, carried from E03:** its arm-angle/subject classifier was measured confounded
by a lit background gradient (subject fraction 0.456 against 0.050–0.054 elsewhere). Any instrument
reused here quotes its subject fraction beside its number or is not quoted. **Question 2 is read by
eye on the sheet**, not by that classifier.

## Predictions — register before looking, blind, each clause separately

- **P1** — what does D1 produce: a painted character, a diagram, or something between? Name it
  before looking.
- **P2** — **does D1's arm rise?** Predict yes/no on its own. *This clause alone decides whether the
  rigging gap can be routed around, so it does not ride inside P1.*
- **P3** — does D1's figure take its **silhouette** from the reference (bulk, cape, helm) or from the
  control (thin tubes)? This is the mechanism question: which input owns the outline.
- **P4** — does naming the character in D2 change identity, surface, or neither, against D1? *A row
  predicted to be uninformative is still a prediction and can still miss.*

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | `EXPERIMENTS` in `build_payload.py` carries a per-experiment `reference` field | **MEASURED** — read at spec time |
| 2 | `verify_topology` binds reference presence in both directions and raises on mismatch | **MEASURED** — read at spec time |
| 3 | `tests/test_build_payload.py` pins E02's submitted payload bytes | **MEASURED** — read at spec time |
| 4 | B1's submitted payload is on disk and re-submittable | **ASSUMED** — verify before building; if absent, rebuild from E03's spec and say so |
| 5 | E02's reference plate is still resident server-side under its recorded name | **ASSUMED** — verify; re-upload and say so if not |
| 6 | E03's 33 posearc frames are still resident server-side | **ASSUMED** — same |
| 7 | Adding a reference does not loosen control authority over position | **ASSUMED** — this is P3's question, not a fact |
| 8 | Generation costs 4 credits | **MEASURED** — E02, Director's balance delta |

## ⚠ Concurrency — another seat is live in the same file

**An E04 seat is running in `E:/AI/armature-E04`** and is adding a gate to `tools/build_payload.py`,
in the submission path. E06 touches the `EXPERIMENTS` table in the same file.

* **Rebase on `origin/main` before editing that file**, and again before committing.
* **Never refactor, rename or remove anything you did not write there.** If E04's gate is present,
  leave it exactly as it is.
* **The regression net is real, not hope:** `tests/test_build_payload.py` pins E02's payload bytes,
  so a merge that corrupts the builder fails the suite before it can spend a credit. Run it after
  any rebase.
* **You work only in `E:/AI/armature-E06`.** Never write into another seat's tree — not a file, not
  a commit. **If files appear in your tree that you did not write: report them, do not commit them,
  do not delete them.**
* **Count surfaces and any pinned number two seats both move are the advisor's to reconcile.** Name
  the collision; touch nothing.

## Out of scope

Control strength · control modality (segmentation, canny, normals — recorded in
`docs/comfy-consult-3.md`, not tested here) · rigging itself · frame counts other than 33 ·
`control_masks` · any new model, node, LoRA or preprocessor, so **this spec introduces no licence
rows**.

## Report

Predictions with blind/not-blind first, then the Gate 0 sheet, then observations per arm against
predictions, then every gate with a verdict. A gate that did not run is written **NOT YET RUN**.
**No judgement words.** Whether it is the same man is the Director's call and no sentence in the
report may pre-empt it. **A negative result is a full success.**

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **3** | Each arm is its predecessor's byte-identical payload with one field changed; models, seed, prompts, reference and control-frame hashes recorded per run; E02's payload bytes pinned by an existing test. |
| ANDON_AUTHORITY | **3** | `expects_reference` raises on this experiment's own variable and is already under test; L/B/C inherited and already firing across E02 and E03. **No new gate commissioned** — the one needed already existed. |
| NAMED_COMPENSATORS | **2** | Local artifacts are new files under `outputs/E06/` (`rm -r` undoes it). **Spent credits have no compensator** — hence a ceiling stated before the first submission and a halting Gate C. |
| DECOMPOSE_BY_SECRETS | **3** | Build, submit, fetch and sheet-building stay separate tools; this experiment adds a config entry and no new seam. |
| UNCERTAINTY_GATED_HUMANS | **3** | No pass condition by design; the identity question is routed to the Director explicitly and no metric may pre-empt it. |
| EXTERNAL_VERIFIER | **1** | Named rather than inflated — the verifier is the Director's eye plus this seat's ruling, a different *kind* of check rather than a different model family. Carries the pipeline's standing remediation. |

**15 / 18.**
