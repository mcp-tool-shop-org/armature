# S06 — the repaired performer: re-survey and re-proof (support dispatch)

**Dispatched 2026-08-14 on the Director's word, carried on facet's E34 close relay:
facet's projection-coverage arc is accepted (facet main @ `2c8ffa3`, suite 927/0), the
repaired performer exists as a new artifact, and the standing support armature promised
is requested — the re-survey, plus the re-proof the Director's own word deferred to
exactly this moment.** Branch/worktree: `S06-run` at `E:\AI\armature-S06`. **Zero
credits — fully local; no cloud interaction of any kind. Any submission attempt is out
of spec and halts the run.**

| Trajectory | The performer is the studio's one canonical character, and every route that binds identity — composed references, driven sticks, sprite cells — consumes what its texture carries. The re-survey documents the repair on armature's own instrument for the Director's eye, and the re-proof grades the deferred sprite-cell verdict (H-S04c) on paint worth judging. Both advance the full GLB→footage scope by clearing the reference constraint at its source; no route is created or displaced. |
|---|---|

## The questions

1. Do the texture-projection holes read closed at the five named landmarks on
   armature's own staging — same instrument, same convention, before beside after?
2. Do the S04 preset's ortho cells, re-rendered on the repaired GLB, give the Director
   sprite cells worth the deferred verdict?

## Premises

| premise | status |
|---|---|
| The repaired GLB: `E:\AI\training\facet_E34\out\performer_textured_8view.glb`, sha256 `ce7930643e573b475737eca676d9118b036d5e131c8b7af66a65b3b7ae0113c5`, 22,284,208 bytes, unrigged, same 299,956-tri mesh, new 4096 atlas — **texture-space repair; geometry unmodified by construction** | **MEASURED by facet's accepted record** (E34-ruling, facet main @ `2c8ffa3`); path confirmed on this rig at dispatch; **re-hash at run start** |
| The pre-repair asset (`facet_E33\out\performer_textured.glb`, `9e20ea7d…b1aa`) is **byte-unchanged in place** | **ASSUMED from the relay → re-hash at start**; it is the "before" of every panel |
| facet's repair, measured at facet's seat: holes 927,492 → 157,228 texels; largest patch 22,457 → 7,390; views 0/4 reproduce E33 to the digit; landmarks read closed on facet's controlled sheet | **MEASURED by facet's record** — armature's panels are evidence on our own staging, **not a re-adjudication of facet's acceptance** |
| facet's E34-ruling **Ruling 2 records three surface observations the Director accepted WITH**: smoother surface with less sculpted hatching; better-defined brow/eye on views 1/7; a **faint tonal seam down the back of head/neck on views 3/5** | **MEASURED by facet's record — read the ruling before Task C notes are written**; nothing pre-known is reported as new |
| `tools/make_hole_survey.py` and the RGBA-true turnaround stand on main; S03's E33 kit (`E:\AI\armature-S03\outputs\S03\turn_rgba\` + manifest) is the before-set, Director-passed | **MEASURED** — S03 record; paths confirmed at dispatch |
| The S04 preset and sheets (`--ortho`, 8×45°, elevation 30, 1024², `make_shotset_sheet`) stand on main | **MEASURED** — S04/S05 close-merges; suite 1296/13 |
| E33's `turn_final` lighting was never recorded (S03 R3) | **MEASURED** — which is why every comparison below is armature-instrument against armature-instrument |
| `facet_E33` and `facet_E34` are **read-only, manifest-gated trees** (E33_manifest.json 117 files — ⚠ its own entry carries a stale byte size, a known self-reference, not a tree change; E34_manifest.json 84 files, self-excluded) | **MEASURED by the relay** — consume, never edit, unchanged in both directions |
| **The VRAM watchdog was found DEAD at this session's start** (heartbeat 13.2 h stale) despite a restart note on the relay | **MEASURED at dispatch — Task A's first gate exists because of it** |

## Task A — ground truth before any render

1. **The watchdog, verified ADVANCING — not the starter's exit code.** Run
   `pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1`, then read the heartbeat
   **twice, seconds apart, and require the timestamp to move**. A heartbeat that exists
   but does not advance is a dead watchdog wearing a file. Stale or static → HALT.
2. Re-hash **both** GLBs: E34 must match `ce793064…3c5` byte-for-byte; E33 must still
   match `9e20ea7d…b1aa` (the relay's byte-unchanged claim, verified rather than
   inherited). Either mismatch → HALT with what was found.
3. Read facet's `docs/experiments/E34-ruling.md` (read-only) — Ruling 2's three
   accepted observations go into the executor's notes as **pre-known**, so Task C
   cannot rediscover them as findings.

## Task B — the RGBA-true turnaround of the repaired performer

S03's convention exactly: enumerate S03's `turn_rgba` manifest and reproduce its
framing arguments verbatim (352×1024, 8 views, the same azimuth convention and
elevation), swapping only the GLB. Gate ALPHA per view — a flat-alpha view FAILS and is
reported, not shipped. Output `outputs/S06/turn_rgba_e34/` with the S03-shape manifest:
tool + Blender versions, GLB hash, per-view sha256 and alpha extrema.

## Task C — the survey panels, before beside after

`make_hole_survey` per view: **S03's E33 render beside S06's E34 render** — same
instrument, same staging, both armature's own — plus one contact sheet. Factual notes
per view: white unpainted patches present/absent at the five named landmarks (jaw,
temple, shoulder, ribcage, flank); anything else seen is checked against Ruling 2's
three pre-known observations **before** the word "new" is written. **No pass condition
on hole counts** — facet's acceptance is the standing verdict; these panels are
evidence for the Director's eye, and the Director's eye is the only judge here.

## Task D — the re-proof at the S04 preset

The S04 Task-C invocations verbatim with only the GLB swapped to E34: the ortho
shot-set and its perspective sibling (8 views, 45° steps, elevation 30, 1024×1024,
RGBA), then both sheets (`make_shotset_sheet`, shotset + compare modes). All S04/S05
gates armed as they stand (ALPHA, TURN, WHOLE, CROP on the ortho path). Output under
`outputs/S06/{ortho,persp,sheets}/` with full manifests and pinned invocations.

These sheets carry the two deferred verdicts to the Director: **H-S04c** (do the ortho
cells read as sprite cells, now on clean paint) and the **51-row placement question** —
both his alone, graded at his eye, per the E14 law.

## Hypotheses (advisor's, blind — no S06 artifact exists)

A "view" is one rendered azimuth cell at the stated preset. Each clause predicted
separately.

| id | clause | prediction |
|---|---|---|
| H-S06a | on the Task-C panels, the five named landmarks read closed on all six previously-affected views (1,2,3,5,6,7) | YES — facet's controlled sheet showed it; our staging differs in lighting, not paint |
| H-S06b | views 0/4 read unchanged between the E33 and E34 sets on our instrument | YES — the clean pair reproduced to the digit at facet's seat |
| H-S06c | facet's faint tonal seam (back of head/neck) is visible on our views 3/5 panels | YES, faintly — moderate confidence; our lighting may mute or move it; pre-known either way, not a finding |
| H-S06d | the S04-profile landmarks that carried the seam the Director's zoom found on E33 ortho cells carry **no white patches** on the E34 ortho cells | YES — this is the repair's direct payoff line at the sprite surface |
| H-S06e | all Task-D gates green: ALPHA 16/16 across both sets, TURN distinct, CROP silent on ortho | YES — same instrument, same preset, geometry unchanged |
| H-S04c (carried) | the ortho cells read as sprite cells at the Director's eye, now on clean paint | **his verdict alone**, deferred to exactly this artifact by his own word at the S04 close |

## Metrics (diagnostics; they gate nothing)

Per-view alpha extrema · per-view sha256 · per-landmark presence/absence notes ·
clearances on the Task-D sets · wall-clock. The Director's eye judges panels and cells.

## Credit ceiling and disclosure

**0 credits — fully local; nothing leaves the rig.** No upload, no estimate call, no
submission surface touched. A hosted-tier revalidation (an E13-shaped probe at the same
landmarks) is explicitly **out of this dispatch** — it is the Director's pricing
decision, and the standing 106–211-credits-per-generation estimate is unchanged.

## Licence checks introduced

**None.** No new model, weight, or dependency. Blender is the standing tool; the E34
GLB is a facet-accepted studio asset consumed read-only.

## Out of scope

Any edit to `facet_E33` or `facet_E34` (read-only, manifest-gated, both directions) ·
any texture work · the hosted-tier revalidation (above) · any judgment of whether the
repair is good — facet's acceptance stands and the Director's eye rules the panels ·
any generation.

## Gates and halts

Watchdog heartbeat stale **or not advancing** → HALT. Either GLB hash mismatch → HALT.
Flat alpha on any view → that view FAILS, report. Gate CROP raising on any Task-D arm →
HALT (no arm here expects a raise). Any cloud call → HALT. No judging anywhere: panels,
sheets and measurements; the words *verified, shipped, works, decisive, validated,
proven* do not appear; the Director's eye rules. A negative result is a full success.

## Report

`docs/dispatches/S06-report.md` on `S06-run`; commit and push the branch, **do not
merge**. The executor's own predictions are committed **before the first render**,
blindness disclosed honestly (the facet relay's numbers are known; our panels are not).
Run the suite plus the `-O` pass before close; report the worktree count beside main's
1296/13, asserting nothing beyond S04-ruling R4's measured skip grouping.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | both GLB hashes re-measured at start against relayed values; S03's manifest enumerated and its arguments reproduced verbatim; every invocation pinned; per-view sha256 in every manifest |
| ANDON_AUTHORITY | 2 | the watchdog gate hardened to heartbeat-advancing after a measured 13-hour silent death; hash gates halt before any render; ALPHA/TURN/WHOLE/CROP armed as they stand |
| NAMED_COMPENSATORS | 2 | nothing irreversible: outputs delete by directory, the branch reverts by `git revert`; facet trees opened read-only; zero credits and zero uploads by construction |
| DECOMPOSE_BY_SECRETS | 2 | survey, turnaround and shot-set each ride their standing tool; nothing new is commissioned — S06 is four tasks of existing instruments pointed at a new asset |
| UNCERTAINTY_GATED_HUMANS | 2 | panels and sheets go to the Director's eye; H-S04c and the placement question are his explicitly; pre-known observations are quarantined from "new" before notes are written |
| EXTERNAL_VERIFIER | 2 | facet's numbers and armature's panels are two instruments on one artifact; alpha and hash arithmetic are mechanical; the advisor rules on the report; the standing human verifier judges |
