# S05 — the roster scale pin (support dispatch)

**Dispatched 2026-08-13 on the Director's word, following S04's close: the ortho
turnaround gains an explicit scale pin so a roster of characters renders on one common
world scale — relative heights preserved across the sheet — with the auto-solve
untouched when the pin is absent.** Branch/worktree: `S05-run` at `E:\AI\armature-S05`.
**Zero credits — fully local; no cloud interaction of any kind. Any submission attempt
is out of spec and halts the run.**

| Trajectory | Rosters are how productions consume shot-sets: a cast on one world scale, where the nine-foot brute and the halfling keep their relation inside every cell. The pin is the recipe-true form of that — one recorded number shared across a roster's runs — and Gate CROP already stands on its failure mode. Instrument work on the same shelf as S04, serving the painted 2.5D line downstream; no route created or displaced. |
|---|---|

## The question

Can `render_turnaround --ortho` accept a pinned `ortho_scale` — used verbatim, recorded
as pinned, shared across any number of runs — while the solved path stays untouched
when no pin is given, and Gate CROP refuses any pin too tight for its subject?

## Premises

| premise | status |
|---|---|
| S04's ortho path is on `main`: one shared solved `ortho_scale`, Gate CROP per view on the ortho path, provenance recording the scale and solve record | **MEASURED** — S04 merged at its close (`S04-run` → main, 2026-08-13); the S04 report and manifest carry the values |
| The solved scale for the proof GLB at the S04 preset is `1.1235359256161628`, largest view 855 px of 1024 (view 1, az 315) | **MEASURED** — S04 manifest and report per-view table |
| Gate CROP reads rendered alpha per view and raises in-tool on border contact | **MEASURED** — S04 Task B, red tests on all four borders at the inclusive last index |
| Blender ORTHO conventions (scale honoured, longer axis, bottom-up rows, distance-independent) | **MEASURED** — S04's calibration fixture, committed and re-runnable |
| Proof GLB: `E:\AI\training\facet_E33\out\performer_textured.glb`, sha256 `9e20ea7d…b1aa` | **MEASURED** — re-hashed at S04's start; **re-verify path + hash at this run's start**; `E:\AI\training` read-only law; texture holes pre-known (facet's arc), not findings |
| A multi-character roster proof needs a second canonical character | **No such pinned asset exists in armature** — the pin's mechanics are provable single-subject (see out-of-scope) |

## Task A — the pin

Add `--ortho-scale=<float>` to `render_turnaround.py`:

1. **Requires `--ortho`** — a pin without the flag is a usage error refused at the
   parser, with a test.
2. When given, **the solve is skipped** and the pinned value is used verbatim for every
   view. Provenance and the manifest record `ortho_scale_source: "pinned" | "solved"`
   and the value; a pinned run's record makes the pin re-typable byte-for-byte (the
   recipe law).
3. The pin must be > 0; refuse otherwise at the parser.
4. **The solved path is untouched when no pin is given** — the branch is a property of
   the projection plan, same doctrine as S04's flag; a test asserts the default path
   still solves and records `"solved"`.
5. `--height-frac` does not participate in a pinned run (there is no solve for it to
   target); the manifest says so rather than carrying a silently ignored value.
6. Tests ride the commit: parser wiring both refusals, pinned-verbatim property,
   source-key recording, default-path structural test. Gate CROP itself is unchanged —
   its existing red tests and `-O` probe already cover the gate; add only what the pin
   path newly reaches.

## Task B — the proof, three arms on the pinned GLB

Verify the watchdog first (Blender is GPU work; PowerShell, headless only). Re-hash the
GLB. Then, at the S04 preset (8 views, 45° steps, elevation 30°, 1024×1024, RGBA):

1. **Arm SOLVED** — no pin. Expected to reproduce S04's scale; records `"solved"`.
2. **Arm PINNED-ROOMY** — pin = 1.25 × the solved scale (type the full float from arm
   1's manifest). The figure renders smaller in identical geometry; CROP silent.
3. **Arm PINNED-TIGHT** — pin = 0.80 × the solved scale. **Gate CROP is expected to
   raise, and the raise is this arm's result, not a failure to route around.** Stop at
   the gate as always: record the gate's message, the view it raised on, and the
   partial output listing. Do not retry, do not adjust the pin, do not continue the
   sweep. A raised CROP here is the gate demonstrating it can fail on a real render —
   the anti-vacuity proof at full scale.

Sheet: arm 1 beside arm 2 (`make_shotset_sheet`, compare mode) for the Director's eye —
same GLB, same preset, scale source the only difference. Arm 3's evidence is the gate
record and the partial output, quoted in the report; a halted run does not sheet.

Outputs under `outputs/S05/` with the S04-shape manifest per arm: tool + Blender
versions, GLB hash, per-view sha256 and alpha extrema, border-contact booleans, the
scale, its source, and the verbatim invocations.

## Hypotheses (advisor's, blind — no S05 artifact exists)

A "view" is one rendered azimuth cell of the proof GLB at the locked elevation. Each
clause predicted separately.

| id | clause | prediction |
|---|---|---|
| H-S05a | arm SOLVED reproduces S04's shared scale to the recorded precision, 8/8 ALPHA green, CROP silent | YES — same GLB, same preset, same solve; the manifest float matches `1.1235359256161628` |
| H-S05b | arm PINNED-ROOMY: 8/8 ALPHA green, CROP silent, and the largest view's rendered pixel height lands at 855/1.25 ≈ **684 px ± 12** | YES on all three clauses — parallel projection scales linearly with 1/ortho_scale |
| H-S05c | arm PINNED-TIGHT: Gate CROP raises **on the first view rendered (view 0, az 270)** and the run halts there | YES — every S04 view's rendered height × 1.25 exceeds 1024 (829–855 px → 1036–1069), so the first rendered view already crops; the gate is per-view and in-tool, so the halt lands at view 0 |
| H-S05d | at the Director's eye, the roomy arm's cells read as the same figure smaller in the same frame — the roster relation made visible on one subject | his call alone, graded on his verdict per the E14 law |

## Metrics (diagnostics; they gate nothing beyond the named gates)

Per-view alpha extrema · border-contact booleans · rendered bbox heights · the scale and
its source per arm · wall-clock per arm. The Director's eye judges the cells.

## Credit ceiling and disclosure

**0 credits — fully local; nothing leaves the rig.** No upload, no estimate call, no
submission surface touched. The per-route disclosure for a fully-local instrument,
stated as the law requires.

## Licence checks introduced

**None.** No new model, weight, LoRA, or dependency. Blender is the standing tool.

## Out of scope

The multi-character roster proof (no second canonical character exists as a pinned
armature asset; the pin's mechanics — verbatim use, recorded source, CROP refusal —
are fully provable single-subject, and the first real roster names its own spec) · the
shot-set re-proof on the repaired performer (gated on facet's arc, its own step, the
Director's standing word) · the normal/depth-pass orbit variant · engine packing ·
changing solved-path defaults · any generation.

## Gates and halts

Stale watchdog → HALT. Interface not enumerated → enumerate before extending. Flat
alpha on any completed view → that view FAILS, report. **Gate CROP raising on arm
PINNED-TIGHT is the arm's expected result: record and stop that arm; it halts nothing
else.** CROP raising on any *other* arm → HALT the run. Any cloud call → HALT. No
judging anywhere: sheets and measurements; the words *verified, shipped, works,
decisive, validated, proven* do not appear; the Director's eye rules the cells. A
negative result is a full success.

## Report

`docs/dispatches/S05-report.md` on `S05-run`; commit and push the branch, **do not
merge**. The executor's own predictions are committed **before the first Task-B
render**, blindness disclosed honestly (Task A is build-and-test; the judged artifacts
are Task B's). Run the suite plus the `-O` pass before the close; report the worktree
count beside `main`'s post-S04-merge count, asserting nothing beyond the measured
skip grouping already ruled in S04-ruling R4.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | the pin IS the pinned parameter — recorded verbatim with source key per arm; GLB re-hashed at start; verbatim invocations in the report; S04's calibration fixture stands behind the conventions |
| ANDON_AUTHORITY | 2 | Gate CROP unchanged and armed; the tight arm exists to demonstrate it firing on a real render, with the expected-raise clause written so the halt is a result, never improvised past; watchdog checked before renders |
| NAMED_COMPENSATORS | 2 | nothing irreversible: outputs delete by directory, the branch reverts by `git revert`; zero credits and zero uploads by construction |
| DECOMPOSE_BY_SECRETS | 2 | the pin lands in the projection plan beside S04's branch; parser, plan, and gate change independently; sheet layout stays in `sheet_compose` |
| UNCERTAINTY_GATED_HUMANS | 2 | the compare sheet ships to the Director's eye; H-S05d is his clause explicitly; the roster-proof scope boundary is surfaced, not settled silently |
| EXTERNAL_VERIFIER | 2 | alpha arithmetic and border contact are mechanical; the advisor (a different seat) rules on the report; the standing human verifier judges the cells |
