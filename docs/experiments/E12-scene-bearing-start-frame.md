# E12 — the scene-bearing start frame (spec)

**Status:** SPEC — written 2026-08-12, dispatched to its own executor session on the
Director's word ("E12 runs in another session"). Report after; advisor ruling last; the
Director's eye is the verdict of record.
**Route:** free route, camera tier (Wan 2.2 Fun-Camera weights on Comfy Cloud).
**Branch/worktree convention:** `E12-run` at `E:\AI\armature-E12`.

| Trajectory | This spend moves the free route from "holds what it is handed" (E11 w3's faithfully-held void) to **holding a world worth publishing** — the missing piece for unanchored footage of the character in real scenes. Every future staged-frame shot — film shot, cutscene, any footage — inherits the start-frame law this experiment prices. The mechanism under test is the scope sentence made literal: the frame carries the world; the model paints life. |
|---|---|

## The question

E11 wave 3 measured the camera tier obeying explicit camera control to one pixel and
preserving the world it was handed — and it was handed a toned void, so it delivered
nothing, faithfully (the Director's hard fail). Two questions, one ladder:

1. Handed a **real bar** the same way, does it hold that world to the last frame?
2. Does the catalog's own sampler/cfg for these weights (**6.0 / uni_pc** — the one
   still-ASSUMED premise) reduce the **arm deformation** w3 measured, at the Director's
   zoom?

## Premises

| premise | status |
|---|---|
| Camera weights mapped Apache; exact Cloud files `wan2.2_fun_camera_high_noise_14B_fp8_scaled` / `…_low_noise_…`; camera nodes REQUIRE this family | **MEASURED** (licence map row, re-fetched 2026-08-12; E11 w2 — Gate PAIR is the mechanical form) |
| w3's recipe (payload record, frame spec 1024×576 · 81 @ 16 fps, gates, prompt) is reproducible from the E11 worktree's records | **MEASURED** at w3; the executor **re-verifies file hashes** against the w3 report's artifact table before use |
| Gates WHOLE / COVERAGE / ALPHA and the startframe tooling exist and ran at w3's thresholds | **MEASURED** (w3 report, gate table) |
| Catalog settings 6.0 / uni_pc for the camera weights | **ASSUMED** — arm A2 exists to measure it |
| The startframe compositor composites over a flat linear tone; compositing over a plate image may need a small extension | **ASSUMED** — the executor enumerates `armature_core/startframe.py` FIRST; any change ships with its tests in the same commit |
| Candidate plate frames exist in E11 w1's outputs at pickable quality | **ASSUMED** — Gate PLATE decides; fallback is a Director-supplied photograph |
| Cloud still serves the pinned camera files | **ASSUMED** until the pin check at submission |

## The plate, and its licence

**No new model enters this experiment.** The plate comes from exactly one of:

1. **Default:** a still the Director picks from E11 wave 1's own generated bar clips —
   generated on licence-mapped Apache weights, output clause on the map, zero new rows,
   zero new spend, already on disk in the E11 worktree, hash-pinned.
2. **Alternative:** a photograph the Director owns.

The plate's provenance (source clip prompt_id + frame index, or "Director-supplied
photograph, <date>") is recorded in `start_frame_provenance.json`. A plate from anywhere
else does not exist for this experiment.

**Amendment — 2026-08-12, at Gate PLATE (the pick).** The gate fired as designed and
was answered with a third source class, admitted under the clause's intent
(ownership): **the Director generated the plate himself** on the studio's
commercial-safe image stack — Qwen-Edit 2511, `Qwen_Edit_2511_00001.png`, supplied
2026-08-12. The wave-1 candidates were passed over on the pick sheet's second-figure
fact (every candidate carries wave 1's own mannequin, head uncovered in the band); a
found photograph of a real venue was surfaced the same day and **blocked at this
gate** — rights unverifiable, identifiable real persons in the band — the gate's
first live firing, answered with a clean generation. The executor copies the file
into the worktree, sha256s it, and records provenance (generator family ·
Director-supplied · date · hash); the cover-fit anchor is a deliberate recorded
composite choice per the alpha law. Wave 2 proceeds per the spec, otherwise
unchanged.

## Gate PLATE (human; uncertainty-gated; blocks all spend)

The executor extracts 4–6 sharp candidate stills from E11 w1's clip(s) (frames where the
bar reads clean — avoid mid-wander motion blur), builds a pick sheet (labels derived
from inputs, `make_startframe_sheet` conventions), and **HALTS for the Director's
pick**. No composite, no upload, no submission before his word names the plate. If he
supplies a photograph instead, that is the pick.

## Amendment — 2026-08-12, after the Director's eye on the first composite

The band-only composite was looked at full size by the Director and **ruled
insufficient before any spend**: below the seam the frame read as a white void —
wave 3's opaque studio floor, which the original one-variable rung deliberately kept.
His word, same exchange: run **both** world-completion treatments, for the experiment.
The arms restructure as follows; everything not named here is unchanged.

**Wave 2 — the world comparison.** Settings pinned at w3's (3.5 / euler). One variable
between arms: the world-completion treatment.

- **A1w — the authored floor.** The previz floor gains a real material — **procedural
  dark wood, no texture file, zero licence surface** — and the same character, pose and
  camera re-render. The plate fills the band; the floor below the seam is ours, in
  correct perspective, with the figure's true contact shadow. Two seeds.
- **A2w — the full-bleed plate.** The rendered floor is dropped; the figure rides over
  the **whole** plate with a recorded shadow treatment (shadow-catcher alpha or an
  authored shadow layer — the choice recorded per the alpha law). The plate's own floor
  carries a deliberate perspective mismatch with the figure's contact points — that
  mismatch is the arm, not a defect to fix. Two seeds, the same pair as A1w.

**Gate LOOK (new, human — the checkpoint the Director's eye just proved).** Both
composites ride one sheet to the Director at full size BEFORE any upload or
submission. His word releases Wave 2. No exceptions.

**Wave 3 — the settings rung, moved.** The catalog correction (6.0 / uni_pc) runs on
whichever world the Director rules better after Wave 2, same two seeds. The original
H-E12b attaches here.

**Ceiling amended 4 → 6 submissions** (2 + 2 + 2, itemized), on the Director's word in
the same exchange. No re-runs; a fired gate still ends the run where it stands.

**Blind additions (the advisor's, written before either frame exists):**

| id | clause | prediction |
|---|---|---|
| H-E12e | A1w: the tier holds band + authored floor as one room; seam reads as depth | HOLDS on both seeds; feet contact intact |
| H-E12f | A2w: the world holds, but feet/shadow contact degrades under the plate's mismatched floor perspective | contact visibly wrong on **at least one** of two seeds |

H-E12a / H-E12c / H-E12d carry unchanged onto the new frames.

## Arms — one variable per rung; the ladder is w3 → A1 → A2 (superseded above)

- **A1 — the world variable.** Byte-identical to w3's payload except the start image:
  the character's authored RGBA composited **under the alpha law** over the picked plate
  (composite is a deliberate recorded choice; the submitted RGB and its reason go in the
  provenance record). Settings remain w3's (3.5 / euler). **Two seeds** — w3's seed plus
  one new — because world-holding is a scene claim and a scene claim needs two seeds.
- **A2 — the settings variable.** A1's start frame and the same two seeds; sampler/cfg
  moved to the catalog's **6.0 / uni_pc**. Everything else pinned. Seed is never a
  second variable inside a rung.
- Frame spec: w3's exact numbers, copied from the pinned record, never re-derived.

## Hypotheses (the advisor's, written blind — before any E12 artifact exists)

| id | clause | prediction |
|---|---|---|
| H-E12a | output holds the bar to frame 81 — seed 1 · seed 2 (separate clauses) | HOLDS · HOLDS |
| H-E12b | at 6.0/uni_pc, arm deformation vs A1 at the Director's zoom · hands at speed | REDUCED · hands still fail (hand geometry stays the promoted lever regardless of outcome) |
| H-E12c | identity reads as the twin's through the paint, all four generations | HOLDS ×4 |
| H-E12d | w3's one-pixel camera obedience replicates over a real plate | HOLDS |

## Prompt

w3's performance-led prompt **verbatim** — no scene naming; the frame carries the world
(consistent with the official guide's I2V rule, `docs/wan-video-prompt-guide-notes.md`,
which is advisory and not the reason: the reason is the ladder — a prompt edit would be
a second variable). Prompt changes are out of scope.

## Credit ceiling

**Four submissions** (2 arms × 2 seeds). No re-runs: a gate that fires halts the
experiment where it stands, and no parameter changes past a gate, ever. Ledger context,
not a bound we control: the arc's GPU-hour valuations ran ≈$0.3–0.9 per generation;
reconciliation state is in the handoff's admin shelf. Spent GPU time has no compensator;
the ceiling is the honest treatment.

## Gates (in-tool, raising — never `assert`, never shell-chained)

Gate ROUTE (graph built in-repo, admission before anything arms — a served template is a
reference, never a route) · Gate PAIR (camera conditioning class ↔ fun-camera weight
family) · Gate ALPHA (authored RGBA in; composite recorded with reason) · Gates WHOLE +
COVERAGE at w3's thresholds · the saved-graph round-trip (fail-closed on unknown
classes) · the pin check at submission (exact weight files) · Gate PLATE (above).
Uploads and saved cloud workflows: their deletes are listed in the report, per the E11
convention.

## Metrics (diagnostics; they gate nothing; the Director's eye rules)

w3's persistence checks (similarity-to-f0, frame deltas) · the one-pixel camera check ·
`measure_clip` standards. **Sheets before numbers:** `make_startframe_sheet` per start
frame; a control | output | reference | provenance sheet per arm before any metric is
quoted; the A/B builder for w3-vs-A1 and A1-vs-A2 (neither arm resampled); stills
extracted where structure is hardest — hands, face, turns; clips judged in motion AND
as frames, at the Director's zoom.

## Out of scope

The plain tier's second seed · smoothing/chop · hand geometry (promoted twice; its own
work) · the narration shelf · anything Wan 2.6/2.7 (`docs/comfy-consult-8-brief.md`
owns that investigation) · **any generative composite of the character** (the alpha law
stands; that fork is the Director's alone and stays closed here) · prompt changes ·
resolution/length changes.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | every generation records model ids, the full payload, seed, and input hashes; submissions are saved files submitted verbatim |
| ANDON_AUTHORITY | 3 | every gate raises inside the tool that acts; Gate PLATE halts before any spend; the gate suite is exercised under `-O` |
| NAMED_COMPENSATORS | 2 | uploads/saved-workflow deletes named in the report; spent GPU time has no undo — the bounded four-submission ceiling is the honest treatment (no skip claimed) |
| DECOMPOSE_BY_SECRETS | 2 | arms isolate one variable per rung; any tooling change rides its own tested commit, separate from run records |
| UNCERTAINTY_GATED_HUMANS | 3 | Gate PLATE gates on the one judgment only the Director's eye owns, before spend, with a pick sheet framed contrastively (candidates side by side) |
| EXTERNAL_VERIFIER | 2 | no model grades its own output; metrics are diagnostics; the verdict of record is the Director's eye — the studio's standing verifier for artifact truth |
