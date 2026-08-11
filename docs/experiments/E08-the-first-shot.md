# E08 — the first shot: he walks up to the bartender, and the model paints the bar

**Seat:** executor · **Spec written:** 2026-08-11 by the advisor, before the work · **Advisor
rules after the report** · **Director judges the footage** · **Credit ceiling: 6 generations
(≈24 credits at the measured 4/generation); 3 planned in wave 1, 3 reserved.** Spend
authority stands (Director, 2026-08-10) — the ceiling is the discipline, not the constraint.

## Trajectory

This IS the product. armature is image-to-video with a GLB instead of an image, and to date
not one frame of an authored performance exists. E08 stages the Director's named shot —
*"Have him walk up to a bartender in a crowded bar"* — as previz: the performer walks, stops
at the bar, gestures; the control sequence carries his authored motion; the prompt and
reference carry his identity and the scene; **Wan paints everything armature stayed silent
about** (E06: the reference and prompt can extend where control is silent — this shot is that
finding at scene scale). Four seconds of footage of one persistent character doing what was
blocked.

## The question

**Does an authored performance rendered as control, plus an identity reference and a scene
prompt, return footage in which HE performs the blocking inside a painted world?** Three
clauses, read separately: (1) the motion — does the walk/stop/gesture arrive at the authored
timing; (2) the identity — is it the same figure throughout (Director's eye, canon, no metric
approximates it); (3) the scene — does the bar arrive from the prompt in the regions the
control leaves silent.

## The shot (previz spec — authored, deterministic, recorded)

- **Performance:** a procedural walk cycle (stride, cadence, arm counter-swing — a new
  authored action on the rigged skeleton), ~2.5 s of walking toward a mark, stop, then an
  emote at the mark (head nod + one arm gesture, e.g. raising a hand to order). Terminal
  pose held to the last frame. All keys authored at 16 fps; fps set BEFORE animation (E03
  Ruling 9).
- **Camera:** static or a slight push-in, landscape, framing him mid-ground walking toward
  the right-third where the bar line will be. The control must leave generous silent regions
  (background, bar, bartender's position) for the model to fill.
- **Frames:** **65 @ 16 fps ≈ 4.06 s** — Wan's 4n+1 form, inside the 81-frame trained
  horizon (consult #3). **Resolution 832×480** (the 480p bucket, landscape).
- **Control channels:** per the E01/E02 conventions (depth is the proven governor; the
  near-bright polarity of the closed arc).

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The rigged performer: `E:\AI\armature-E07\outputs\E07\rig-repaired\performer_auto.glb`, sha256 `7f56c9ac101218db78c10aa5764b9a72a7d8b6f4b539f035b7739351ed6e2a24` | **MEASURED** — hashed by the advisor at spec time; re-verify before use; copy into your worktree, never edit the E07 worktree |
| 2 | 65 frames is generator-legal at 832×480 on the saved Wan 2.1 VACE route | **ASSUMED** — verify against the saved Cloud graphs (E02's `width/height/length` fields) before any render; derive-then-round per the generation-frames law; if 65 or 832×480 is not accepted, the nearest legal form is recorded and the spec amended in place |
| 3 | The walk can be authored procedurally on the 22-bone skeleton (hips translation + leg/arm swings) with the slotted-action API | **ASSUMED** — the walk builder is this spec's commission; its tests ride the commit |
| 4 | The reference: `E:\AI\training\facet_E33\twins\twin_r3_v0.png` (the Director-approved terracotta register) | **MEASURED** — exists, approved 2026-08-11; hash it into the payload record |
| 5 | Identity rides the prompt: E33's twin `_entry_verbatim` clause (the jointed clay mannequin description) | **MEASURED** — `E:\AI\facet\docs\experiments\E33-twin-prompts-r3.json`; the scene clause is appended to it, never replaces it |
| 6 | Generation cost 4 credits | **MEASURED** — E02 balance delta; the Director's balance remains the meter; GPU-hours are metered separately and reported |

## The generation payloads

Core `WanVaceToVideo` single-reference route only (the multi-ref custom nodes are UNVERIFIED
= NO in the licence map). Strength 1.0 (the closed arc's setting — with a body to paint, the
model paints; strength below 1.0 is a recorded lever, NOT varied here). Prompt = identity
clause (premise 5) + the scene: *he walks up to the bartender in a crowded, warmly lit bar* —
written out in the payload record; the negative per the closed arc's conventions. Seeds
pre-registered (Gate S list committed before the first submission). Wave 1: **one probe
generation end-to-end, then two more** (seed variants) after the probe's Gate 0 sheet exists.
Reserve: 3.

## Gates

Inherited and armed: **Gate L** (frame legality, raises in the tool) · **Gate S** (seed
pre-registration) · **Gate B** (batch count) · **the lossless tap** (`verify_topology`) ·
**Gate C** (ceiling 6; halt before any submission that would exceed) · **Gate 0** (the
control | output | reference | provenance sheet before any number) · the export **OBJ gate**
and Blender **success-sentinel** rule from E07. A fired gate halts the session — report with
evidence, never re-parameterize past it.

## Review — the Director's standing rules

The clip at **0.5×, 8 fps, built from `lossless/`**, never from re-encoded video. Stills
extracted where structure is hardest: **hands, the face through the turn, every
crowd-occlusion moment**. The sheet at dailies standard. Identity is his call alone; the
report carries measurements and no judgement words.

## Out of scope

The dancing/emoting scenario variants (the Director's other named tests — they are the NEXT
waves and reuse this spec's machinery); any strength sweep; multi-shot continuity; brush-pass
atlas repair (the triangle texels ride the reference-free control path and the twin
reference, so they do not gate this shot); skeleton v2.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **3** | Rigged GLB + reference + prompts hashed into payloads; seeds pre-registered; saved-graph route |
| ANDON_AUTHORITY | **3** | L/S/B/C/0 + lossless tap + OBJ gate + success-sentinel, all raising in-tool |
| NAMED_COMPENSATORS | **2** | Local artifacts under `outputs/E08/` (`rm -r` undoes); **spent credits have no compensator** — the ceiling and the probe-first wave are the honest treatment |
| DECOMPOSE_BY_SECRETS | **2** | Walk builder / stage render / payload builder / fetch / sheets are separate tools |
| UNCERTAINTY_GATED_HUMANS | **3** | The three clauses are read separately and the artifact goes to the Director's eye; no pass condition is invented for identity |
| EXTERNAL_VERIFIER | **1** | Standing weakness, named: advisor + Director's eye |
