# E14 — the LoRA scene lever: the bake-off (spec)

**Status:** SPEC + DISPATCH-READY — written 2026-08-13 on the Director's word (the
LoRA lever named by him; shape 1, the bake-off, picked by him from the contrastive
fork). **Route:** the free route at its E12 baseline. **Branch/worktree:** `E14-run`
at `E:\AI\armature-E14`. **Zero partner credits** — the free route is GPU-hour
metered; any partner-credit estimate above 0 halts.

| Trajectory | A style LoRA is a scene-defining lever the studio does not have to hand-build: if a served adapter can re-author the look of a held world without dissolving the character, the scope gains art-directed footage at zero marginal authoring cost — and the measurement bounds the studio's future canon-trained video LoRA (the long-game version of the same lever, custom path recorded open in consult #10 R5). A null is a full result: it prices the lever honestly. |
|---|---|

## The question

On the free route's proven baseline — a handed world that holds, at 6.0 / uni_pc —
what does one style LoRA at its trained strength do to **the world** (the scene it
defines), **the subject** (identity at the Director's eye), and **the camera hold**
beneath both?

## Candidates and the licence gate (already run — 2026-08-13 fetch pass)

Six shortlisted; the gate cut four; **two run** (rows in
[the licence map](../license-map.md), *Added 2026-08-13, E14 pass*):

| arm | LoRA (served filename) | look (per the Director's memo, corrected) | licence |
|---|---|---|---|
| T | `wan22-14b-t2v-technically_color.safetensors` | three-strip Technicolor: saturated primaries, deep blacks, high-contrast studio key | Apache-2.0, fetched |
| C | `wan22-candid_photography.safetensors` | street-photography framing, unposed behavior, natural ambient light | Apache-2.0, fetched |

Dead at the gate, recorded not waved: the instareal pair (the Instara licence bans use
on any generation service — the route itself is the banned act) · 80s_fantasy_movie
(no licence displayed; Wan versions are T2I) · SmartphoneSnapshot v3 (origin terms
unretrieved) · vintage_film_grain (source unlocated) · dark_ghibli (excluded before
any fetch — the no-anime law). Any revival enters through a fresh document only.

## Design — the bake-off, not the sweep

Each arm = **the byte-pinned E12 wave-3 graph + the arm's LoRA, nothing else moved.**
The comparison reference is the **existing E12 wave-3 seed-1 record** (the Director's
ruled-strongest result) — no baseline re-generation. Two generations total.

- Seed **2026081233** (E12's seed 1), explicit, Gate-S registered. **One seed, and the
  two-seed scene law is not violated because the bake-off claims no property:** its
  outputs are candidates for the Director's eye, and whichever look he picks earns the
  property-grade follow-on (the strength sweep, two seeds, its own spec).
- Strength **1.0** both arms (the trained behavior; consult #10: served default 1).
- **Wiring convention, pinned:** the single served file loads via `LoraLoaderModelOnly`
  on **both experts** (high-noise and low-noise models), one loader instance per
  expert, same file, strength 1.0 — recorded per arm. This is the pinned convention,
  not a measured claim; see premises.
- Start image: the **same server upload** E12 used (`265b1c17…`, content-addressed,
  already hosted) — no re-upload. Prompt, negative, resolution, length, fps, sampler,
  cfg, scheduler, shift, steps, split: **byte-identical to the E12 wave-3 graph.**

## Premises

| premise | status |
|---|---|
| The E12 wave-3 graph reproduces as pinned (fields, upload, seed registry) | **MEASURED** (E12 record; Gate LEDGER re-verifies at run) |
| The two LoRA filenames resolve in the served combo list | **MEASURED** — consult #10 calibration, uncapped `get_node`, 2026-08-13 |
| Licence rows for both arms | **MEASURED** — fetched 2026-08-13 (the map) |
| **The transfer premise:** a T2V/T2I-trained style LoRA binds visibly on the Fun-Camera derivative weights | **ASSUMED — the experiment's central measured question.** Nothing served documents it (consult #10 Q3). A null (no visible look change) or a break (degraded output) is a FINDING per arm, not a failure |
| The served single file's expert-tier identity (both origins publish tier-labeled versions; the Cloud serves one file each) | **NOT VISIBLE** — the both-experts convention is pinned regardless and recorded; a tier-mismatch artifact is a candidate explanation for any oddity, named in advance |
| `LoraLoaderModelOnly` contract (model + lora_name + strength → MODEL; default 1, ±100) | **MEASURED** — consult #10 calibration |

## Gates

- **Gate LEDGER, break-aware, against the E12 wave-3 pinned graph:** the named break
  is exactly the LoRA loader insertions (two `LoraLoaderModelOnly` per arm, on the
  expert MODEL lines); every unnamed field must hold byte-identical; structural
  fields refuse override. The one generation-reaching difference per arm is the LoRA.
- **Gate ROUTE** walks the built graph (in-repo, never the served template); the
  round-trip table is taught any class it lacks, tests riding the commit.
- **Gate PAIR:** the camera weights ↔ camera nodes pairing unchanged from E12. The
  LoRA↔expert attachment is recorded per arm (which loader on which expert line) —
  a mis-attachment is an E11-w2-class wiring error and the record must make it
  visible.
- **Gate S** (seed explicit, registered) · **Gate L** (legality unchanged from E12) ·
  **Gate B** (batch intact, decode pixel-verified) per arm.
- **The credit gate:** `estimate_credits` per arm before submission — expected
  0 / GPU-hour; **any partner-credit estimate above 0 → HALT.**

## Ceiling

**Two generations.** No re-runs; a fired gate ends the arm where it stands; the other
arm proceeds (arms are independent — a platform rejection or gate on one arm is a
finding for that arm only).

## Judging

Per arm, before any number: a **baseline (E12 w3 s1 frame) | arm output | reference |
provenance** sheet, frames where structure is hardest (the figure, the crowd, the
bar's fixtures), clips in motion AND as frames. **The Director's eye rules three
things separately: the scene the LoRA defines, whether the subject is still his
character, and whether the camera hold survived.** Single-run comparison: no numeric
claims ride it (no noise floor on this tier); `measure_clip` diagnostics ride the
report and gate nothing. E12 R3 stands behind the identity read: a LoRA is unscoped
by nature — what it does to the subject is as much the question as what it does to
the world.

## Hypotheses (the advisor's, written blind — before any E14 artifact exists)

| id | clause | prediction |
|---|---|---|
| H-E14a | each arm produces a Director-legible look transform at 1.0 | T: YES, strongly legible; C: YES but subtle — candid-photo is closer to the baseline's look than Technicolor is |
| H-E14b | the subject reads as the same character at his eye | holds on **both** arms — but with visible re-styling pressure on at least one (the unscoped-lever lesson, E12 R3); the crowd re-styles before the subject does |
| H-E14c | the Static camera hold survives | YES, both arms |
| H-E14d | the transfer premise binds at all (visible LoRA effect on derivative weights) | YES on both — a null on either would be the tier/derivative-mismatch finding, and it is the prediction this seat is least certain of |

## Per-route disclosure (measurement addendum)

The free route's standing exposure, unchanged: generation runs on Comfy Cloud; the
start image is already hosted (content-addressed, no delete endpoint); the LoRA
weights are cloud-served files that never touch the rig; the only new things leaving
the rig are the two graph payloads. Fully-local stages (measurement, sheets) stay
local.

## Out of scope

The strength sweep (the winner's follow-on, its own spec, two seeds) · any second
seed · prompt changes (byte-pinned to E12) · the subject-scoped identity clause
(promoted, but it is a prompt change — it waits for the sweep) · any adoption ruling ·
reviving gate-dead candidates (fresh documents only).

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | every field inherited byte-pinned from E12's record; the only deltas are named, hashed, and ledger-verified; full payload records per arm |
| ANDON_AUTHORITY | 3 | LEDGER/ROUTE/PAIR/S/L/B plus the credit halt, all raising in-tool; arms independent so one andon cannot silently kill the other |
| NAMED_COMPENSATORS | 2 | no uploads (the start image is already hosted); saved workflows listed with deletes per convention; GPU-hour spend has no compensator — the two-generation ceiling is the honest treatment |
| DECOMPOSE_BY_SECRETS | 3 | one variable per arm (LoRA identity), strength and seed frozen; the sweep is deliberately a separate future spec |
| UNCERTAINTY_GATED_HUMANS | 3 | the licence gate ran before the spec; the Director picked the shape contrastively; his eye is the sole verdict on all three judged axes |
| EXTERNAL_VERIFIER | 2 | no model grades its own output; the standing human verifier rules; pixel-level Gate B decode-checks ride each arm |
