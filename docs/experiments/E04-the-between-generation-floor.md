# E04 — the between-generation floor: how much does the tracking statistic move when only the seed changes?

**Seat:** executor · **Spec written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director judges the sheets** · **Credit ceiling: 12 generations (48 credits).**

**Spend authority:** the Director raised the budget on 2026-08-10 — *"You have the authority to
increase the spend as needed."* That removes the scarcity constraint. It does **not** remove the
discipline: a ceiling is stated before the first submission and an arm's cost is weighed against
its information value, because that reasoning was never about money.

---

> ## STATUS: ACTIVE — un-deferred by the Director, 2026-08-10
>
> **The Director has called E04 on**, and that is his call: credits are his and the deferral was a
> priority judgement by this seat, never a correctness one. Nothing in this spec changed; the
> reasoning that deferred it is kept below, unedited, because it is still the honest account of why
> it was not first.
>
> ⚠ **Two things this seat must flag before it runs.** (1) **E06 is live in parallel** and both
> experiments add a gate to `tools/build_payload.py` — E04 adds **Gate S**, E06 adds **Gate V**.
> That file is a **shared surface this round**; see the paste block. (2) E05 is **WITHDRAWN** — do
> not run it, and do not take its strength ladder as context for anything here.
>
> ### The superseded deferral reasoning, kept
>
> ## (was) DEFERRED 2026-08-10 — not withdrawn, and still correct
>
> Deferred by the Director after E03. Nothing in this spec is wrong; it is simply not the next
> question. **E03's result was categorical** (85.0 deg against 0.062 deg, a factor of ~1370) and
> needed no floor to be read, and **[E05](E05-control-strength.md) is categorical too** — *is a
> character there, is the control still obeyed* — judged by eye.
>
> **E04 becomes REQUIRED the moment any arm comparison turns on a magnitude rather than a
> category.** Until it is measured, no armature document may rank two arms on a fine numeric gap,
> and both E03's and E05's specs carry that prohibition explicitly. Measuring the apparatus before
> we know the pipeline can produce a character at all would be optimising the ruler while the
> subject is unresolved.
>
> ⚠ **One scope point survives the deferral and should be read now:** the floor is a property of
> the **statistic**, not of the model, and this spec measures it **at 33 frames**. If armature
> moves to 81 frames (consult #3: well inside Wan's trained horizon), this floor does not
> automatically travel with it.

## The question

**When nothing about a generation changes except the seed, how much does the tracking statistic
move?**

That is the whole question. It is a measurement, not a test.

## Why this is worth 10 generations

E02 measured A1a at timing correlation **+0.521** and A1b at **+0.581** — a gap of **0.060** — and
the closing ruling **refused to read it as an ordering**, because the only floor we had was for
*re-running one submission* (bit-identical, 3/3) and not for *drawing a second sample*.

**Every future numeric arm comparison in armature is unrankable until this number exists.** That
is the cost of not buying it. E03 escapes only because its reads are categorical (does the arm go
up), and the next question after E03 — *how much* may the model improvise on top of control — is
inherently a magnitude question and cannot be asked at all without this.

⚠ **The floor is a property of the STATISTIC, not of the model.** E02's own history proves it: the
pixel floor on lossless frames is exactly **zero**, while the tracking statistic's floor is
unknown and certainly is not zero. Every statistic quoted in this repo needs its own floor before
a gap in it is read. This experiment measures the floor for the statistics E02 actually quoted,
and for no others.

## Design — 2 conditions × 6 seeds, of which 10 generations are new

| condition | control | n |
|---|---|---|
| **C-bright** | E02 A1a's control sequence, near-bright depth, byte-identical | 6 |
| **C-dark** | E02 A1b's control sequence, near-dark depth (`255 − x`), byte-identical | 6 |

**Only the KSampler seed varies.** Everything else — both prompts, `WanVaceToVideo`, the
reference, all three models, `ModelSamplingSD3` shift, sampler, steps, cfg — is byte-identical to
E02's submitted payloads, which are on disk at `outputs/E02/payloads/A1a.json` and `A1b.json`.

**The two existing E02 runs join as the first seed of each condition.** They were generated under
exactly these conditions at seed `654654950714624`; reusing them is honest and saves two
generations. **So 10 new generations buy n=6 per condition.**

### Pre-registered seeds — committed before the first submission

```
654654950714624   (existing: A1a = C-bright, A1b = C-dark)
654654950714625
654654950715624
654654950724624
654654950814624
654654951714624
```

The list is fixed here, in the commit that opens the experiment, **and Gate S below makes it
unskippable.** A seed chosen after seeing a result is seed-shopping; a committed list removes the
possibility rather than forbidding it.

## What this yields — three things, not one

1. **The floor**: the within-condition spread of each statistic across 6 seeds, **measured twice
   independently** (once per condition).
2. **Whether the floor is condition-dependent** — if C-bright and C-dark disagree about their own
   spread, a single floor number is not portable and that is itself the finding.
3. **A real two-sample comparison of the polarity question E02 had to leave unruled** — 6 against
   6 instead of 1 against 1. This is a by-product of measuring the floor properly, not a separate
   purchase.

## ⛔ There is NO pass condition, deliberately

This experiment measures a quantity; it does not test a hypothesis about one. **Report the
within-condition spread and the between-condition gap side by side and let the Director's eye
rule.** Inventing a threshold — "the gap counts if it exceeds 2× the spread" — would be exactly
the recorded error this repo has paid for four times: a pass condition defined as a fraction of a
quantity not yet measured. **When no calibrated threshold exists, suspend rather than invent one.**

The one thing the report **may** say is arithmetic: the gap expressed in units of the measured
spread. It may not attach a verdict to that ratio.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | E02's A1a/A1b payloads are on disk and re-submittable | **MEASURED** — `outputs/E02/payloads/{A1a,A1b}.json`, read at spec time |
| 2 | The KSampler seed is the only field that need change, and nothing else is seed-derived | **ASSUMED** — the executor diffs the two payloads and confirms before submitting. If any other field derives from the seed, that is a finding and a halt |
| 3 | Generation costs 4 credits | **MEASURED** — E02, Director's balance delta 14,284 → 14,280 |
| 4 | Repeat runs at a fixed seed are bit-identical on lossless frames | **MEASURED** — E02 A0, 3/3 |
| 5 | The tracking statistic has a re-runnable instrument | **MEASURED FALSE — see Commission** |
| 6 | The existing A1a/A1b runs' lossless frames are still on disk and intact | **ASSUMED** — verify by hash before reusing them as seed 1; if either is gone, generate it and say so |

## Instruments — enumerated first, and one commission is justified

**Enumerated in `tools/` before specifying anything:** `measure_floor.py` (pixel repeat-variance,
per frame index), `compare_runs.py` (pixel-by-pixel run comparison), `analyze_p3.py`,
`make_gate0_sheet.py`, `make_sheet.py`, `make_thesis_sheet.py`, `build_payload.py`,
`fetch_run.py`, `encode_control.py`.

**COMMISSION — `tools/measure_tracking.py`.** The timing-correlation statistic that produced
+0.521 and +0.581 **has no tool**. It was computed inline during E02 and is not reproducible from
the repo. That is *a recipe that does not reproduce its output is not a recipe*, sitting under the
single number this whole experiment is about. It must exist before E04 quotes it.

It takes a run directory and the control sequence, and emits the statistic per run as JSON. **Its
definition must reproduce E02's published numbers on E02's runs** — an anchor leg that reproduces
**+0.521 on A1a and +0.581 on A1b** rides the commit, or the instrument is measuring something
E02 did not. **Tests ride the commit**, and each fixture answers: *what would this look like if
the code were wrong in the specific way this check exists to catch?*

**REUSE unchanged:** everything else above.

**CORRECTION, small and separate:** `tools/measure_floor.py`'s docstring still argues *"the floor
is not a scalar… early frames agreeing while late frames diverged"*. That shape was **the H.264
codec**, falsified by E02's A0 on lossless frames (floor exactly zero). The tool is fine; its
stated rationale teaches a falsified finding to the next reader. **Correct it in place, with the
measurement that overturned it — do not delete the original claim.**

## Gates

Inherited and already built: **Gate L** (frame legality, raises inside the tool), **Gate B**
(batch count off `BatchImagesNode`), **the lossless tap** (enforced by `verify_topology`),
**Gate 0** (control | output | reference | provenance sheet **before any number is quoted**).

**Gate S — NEW, the seed pre-registration andon.** The submitting tool **raises** if the seed it
is about to submit is not in the committed list above. It lives **inside** the tool that performs
the submission — not in a shell chain, not an `assert`, no skip flag — because a check that a
scripting accident can separate from the irreversible step it guards is not a gate. Put the andon
on the direction the invariant does not bound: nothing else here prevents a seed from being
chosen after a result is seen.

**Gate C — credits.** State projected spend before submitting. **Ceiling 12 generations**; 10
planned, 2 reserved for a fired gate. Halt if a run would exceed it.

**A gate that fires is reported with its evidence and the session halts.** Never change a
parameter and re-run to get past one.

## Predictions — register before looking, state whether blind

The executor registers these **before the first new submission**, and predicts **each clause
separately** rather than predicting a join:

- **P1** — the within-condition spread of the timing correlation across 6 seeds. State it as a
  number with a band, and state it **relative to the 0.060 gap** E02 could not read.
- **P2** — is the spread the **same** in C-bright and C-dark? Predict yes/no and why.
- **P3** — the within-condition spread of the **pixel** statistic (mean |Δ|), whose fixed-seed
  floor is zero. *A row predicted to be uninformative is still a prediction and can still miss.*
- **P4** — after the floor is known: is the C-bright/C-dark gap larger or smaller than the spread?
  **Register this before computing it**, and note that either answer is a full result.

**A negative result is a full success.** If the floor swallows the gap, then E02's polarity
comparison was unreadable, we will have proven it rather than assumed it, and every future arm
comparison gets designed around a known number instead of a hope.

## Out of scope

Anything about identity, anything about authored motion (that is E03), the no-control (A2)
condition's own floor — deferred, and named here so it is not silently assumed to be the same —
any change to the control sequences, any new model, and any parameter other than the seed. **No
new dependency enters, so this spec introduces no licence rows**; the stack is E02's, unchanged.

## ⚠ Scope note — the floor is measured at 33 frames, and length changes the population

E04 runs byte-identical to E02's payloads, so `length` stays **33**. That is required — a floor
measured at a different length is not comparable to the numbers it exists to contextualise.

**But a floor measured at 33 frames is not automatically the floor at 81.** Comfy consult #3
(`docs/comfy-consult-3.md`, calibrated) puts Wan 2.1 VACE 14B's trained horizon around the
**81-frame class**, so 33 sits well inside it and 81 is the cheapest available length win.
Temporal coherence is exactly the kind of quantity that can drift with clip length.

**Ruled: this experiment does not chase that.** It measures the floor for the statistics E02
quoted, at the length E02 quoted them. Re-measuring the floor at 81 frames is a later,
separately-bounded experiment, and **any number from E04 carries "at 33 frames" with it** —
the same discipline that made "the floor is a property of the statistic" explicit above.

## Report

Predictions with blind/not-blind first, then Gate 0 sheets, then the per-seed statistics as a
table, then the spread beside the gap, then every gate with a verdict. A gate that did not run is
written **NOT YET RUN**. **No judgement words.** The Director decides what the numbers mean.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **3** | Every submission is a byte-identical payload from disk with one field varied; the seed list is committed before the first submission; model ids, payload and control hashes recorded per run. |
| ANDON_AUTHORITY | **3** | Gate S raises inside the submitting tool with no skip flag; Gates L/B/C inherited and already firing in E02. |
| NAMED_COMPENSATORS | **2** | Every local artifact is a new file under `outputs/E04/` (`rm -r` undoes it). **Spent credits have no compensator** — that is why the ceiling is stated before the first submission and Gate C halts. Not 3 because the irreversible action is genuinely irreversible; the bound is the honest treatment. |
| DECOMPOSE_BY_SECRETS | **3** | Payload construction, submission, fetch, and measurement are separate tools; the commission adds one that hides the statistic's definition behind a file interface. |
| UNCERTAINTY_GATED_HUMANS | **3** | There is deliberately **no pass condition** — the spread and the gap go to the Director side by side. The escalation is the design, not an afterthought. |
| EXTERNAL_VERIFIER | **1** | Honestly weak and named rather than inflated: the verifier is the advisor's ruling plus the Director's eye, which is a different *kind* of check rather than a different model family. Unchanged by this experiment; carries the pipeline's standing remediation. |

**15 / 18.** The two sub-3 scores are named with their reasons rather than argued away.

---

## AMENDMENT 1 — 2026-08-10, executor, before the first submission

Four premises were checked before any credit was spent. Two held, two moved. Appended in
place rather than edited into the table above, so the spec shows its own corrections.

### A. Premise 2 (**ASSUMED** → **MEASURED TRUE**)

*"The KSampler seed is the only field that need change, and nothing else is seed-derived."*

Both on-disk payloads were diffed field by field (48 and 49 nodes). **Exactly one
seed-bearing field exists in each: node 3, `KSampler.seed`.** No other field named `seed`
or `noise`, and nothing else derives from it. Varying the seed varies nothing else. This is
now enforced rather than trusted: `tests/test_gate_s.py` diffs every E04 payload at every
registered seed against the E02 payload actually submitted and permits only node 3's seed
and three output-name strings.

### B. Premise 1 (**MEASURED** → **MEASURED, with the wrong file named**)

The spec named `A1a.json` as C-bright's base. **It cannot be**: A1a ran *before* the
lossless output tap existed, so its payload carries no node 302 and re-running it would
return no frames the statistic is defined on.

**C-bright's base is `A0.json`** — which is `A1a.json` plus the tap and nothing else
(diffed: node 302 is the sole difference; same seed, same control, same prompts, same
models). This is not a change of condition. It is the same condition, captured losslessly.
`build_payload.py --experiment=E02 --arm=A1a` already emits exactly `A0.json`, and the
sha256 pinned in `tests/test_build_payload.py` has been pinning those bytes all along.

### C. Premise 5 — the commission is built, and its anchor moved a published attribution

`tools/measure_tracking.py` exists and reproduces **all five** figures E02 published
(+0.521, +0.581, −0.064, +0.343, −0.113) within 0.0005.

**But E02's published +0.521 for A1a was computed on A0r1's lossless frames, not on A1a's
own.** A1a's own frames are H.264 and return **+0.545**. The E02 report is not wrong about
the *condition* — it is silent about *which frames*, and the difference is 0.024, which is
40% of the very gap this experiment exists to put a floor under. Every E04 number is
computed from `lossless/` and nothing else.

Also measured while anchoring, and both are now context for every number here:

* the **fixed-seed** floor on this statistic is exactly zero (A0r1/r2/r3 all
  +0.5206918475), so any spread E04 measures is between-generation and nothing else;
* the control's energy profile is **bit-identical** under `255 − x`, so both conditions
  correlate against the same reference profile and the conditions differ only in output.

### D. Premise 6 (**ASSUMED** → **MEASURED TRUE**)

Both reused seed-1 runs are on disk, 33 lossless frames each, manifest-hashed before use:
`A0r1/lossless` `fe33cb6b…`, `A1b/lossless` `3ff2212f…`. Neither needed regenerating.

### E. Reported, not fixed — E02's A1b distinct-name check could not fire

`EXPERIMENTS["E02"]["arms"]["A1b"]["source_dir"]` names
`outputs/E02/control_480x832_inverted/depth_pershot`, **which is not on disk**. With the
directory absent, `_distinct_source_frames` returns `None` and the distinct-name check
degrades to "at least one distinct image" — so for that arm it could not have caught a
collapsed batch. A1b's batch was in fact intact (33 distinct server names, and Gate B
passed), so nothing about E02's result is in question; the *check* was not doing its job.

**Not fixed here.** It is E02's row on an experiment already run and reported, and
`tools/build_payload.py` is a surface E06 is editing in parallel this round. E04's own
C-dark row names `control_480x832_neardark/depth_pershot`, which is on disk, so the check
binds at 33 for these submissions. **Disposition is the advisor's.**
