# E08 — the first shot: he walks up to the bartender, and the model paints the bar

**Seat:** executor · **Spec written:** 2026-08-11 by the advisor, before the work · **Advisor
rules after the report** · **Director judges the footage** · **Credit ceiling: 6 generations
(≈24 credits at the measured 4/generation); 3 planned in wave 1, 3 reserved.** Spend
authority stands (Director, 2026-08-10) — the ceiling is the discipline, not the constraint.

> ## ⛔ HALTED AND REFRAMED 2026-08-11 — the advisor dispatched the wrong product
>
> Watching the executor hand-author a walk cycle, the Director ruled that the model, not the
> seat, should generate the motion. **He is right and the spec
> below this banner describes the wrong route.** The advisor read the walk-to-the-bartender instruction through the arc's control-first lineage — author the motion, model paints over
> it — when the scope sentence says the other thing: the GLB replaces the **image** in
> image-to-video. It supplies *who he is*; **the model generates the performance.** This
> misdispatch earned CLAUDE.md advisor rule 0 (contrastive frame confirmation before any
> product-defining dispatch).
>
> **The halt was clean: 0 generations, 0 credits** — verified three ways by the stopped seat
> (empty queue at halt, no generation bucket on today's invoice, no prompt_id on disk). Its
> gait tooling (`walk.py` + `author_walk.py` + framing, 371 tests, branch `E08-run` @
> `0c49e67`) is banked as the **authored end of armature's control dial** — a recorded tool,
> not this experiment's route. Its two findings (the distinct-name check's silent
> degradation inherits into its test; glTF export re-splits posed vertices) ride the record.
>
> **THE CORRECTED ROUTE — PROPOSED, awaiting the Director's frame confirmation under rule 0:**
> rendered views of the performer from the GLB serve as the **reference**; the scenario lives
> in the **prompt**; the model generates **all motion** — no authored animation, no control
> channels, the skeleton unused this wave. Route = the already-mapped Apache Wan VACE
> configuration with the control input absent (E02's no-control shape): zero new nodes, zero
> new licence rows. Wave 1: the bar walk, then a dance and an emote variant. 65 frames @
> 16 fps, 832×480, ceiling and gates unchanged, probe first. The staging sections below are
> superseded by this banner where they conflict; they are kept as the authored-end recipe.

> **AMENDED 2026-08-11, incoming advisor seat — the "corrected route" paragraph above is
> WITHDRAWN.** THE HANDOFF (commit `18ed461`, cut at the Director's instruction) withdraws
> it: the Director never confirmed it — it was the relieved seat's third reading of one
> unchanged instruction, and the handoff's binding line is that no seat inherits any of the
> three. **No route in this spec is live.** The route question returns to the Director's
> words, asked fresh under advisor rule 0 and confirmed back contrastively before any spec
> or dispatch. His instruction, paraphrased — the only standing definition of E08: put the rigged GLB through the pipeline for an informed 4-second GLB-to-video of the performer dancing or emoting across scenarios — for example, walking up to a bartender in a crowded bar — to test whether the capability is possible

> **FRAME CONFIRMED 2026-08-11, later the same day.** The Director confirmed the route
> shape: **both stages generative** — a motion model generates the performance from the
> prompt, the performance lands on the character's rigged skeleton, and a video model paints
> him performing it; no motion is hand-authored, and the character's own rig is where the
> generated performance arrives. The shot he named: the character **dancing in a crowded
> bar**, to show the character in action, the same character available across multiple shots,
> and the scene arriving from prompt + GLB. Comfy consult #6
> (`docs/comfy-consult-6-brief.md`) is dispatched for what fills the two generative slots;
> **the spec below is rewritten after its answers return** — until then the staging sections
> remain the authored-end recipe only.

> **CONSULT #6 ANSWERED AND RULED, same day** ([comfy-consult-6.md](../comfy-consult-6.md)):
> SLOT 2 is provisionally adopted on the core `WanAnimateToVideo` node in a graph we build
> ourselves — the served template wires the banned detector tier and is unusable under the
> gate — with `pose_video` from rig-rendered frames, identity on GLB reference renders, and
> `background_video` unconnected so the prompt paints the scene. SLOT 1 (prompt → skeletal
> motion) is confirmed unfilled on Cloud; the licence-fetch pass on the consult's named
> out-of-Cloud candidates is the next action, and **the spec rewrite follows its
> resolution.** The consult's interim suggestion to hand-author the first shot's motion is
> rejected as out of frame (ruling R6).

> **STUDY-SWARM RUN AND GATED, same day**
> ([research-grounding-e08.md](../research-grounding-e08.md)): five Sonnet research lanes,
> existence oracle-resolved, load-bearing claims verified by two non-Claude families. What
> it fixes for this spec: the pose-render convention is code-defined in an Apache repo and
> exactly matchable (G6–G8); one locked reference-render set is reused across all shots
> (G14); the face channel and character mask are armed (G7, G12); the probe measures
> scene-from-prompt strength (G15) and identity under the skeleton route (G9, G13) as
> explicit clauses. SLOT 1 narrows to two arms — a hosted vendor contract (G5) or the
> self-hosted MediaPipe lift chain (G4, G16, G17) — **the pick is the Director's; the
> rewrite waits on it.**

> **THE REWRITE IS IN: see "THE REWRITE — 2026-08-12" below the amendment chain.** E09
> closed as the baseline ([E09-closing-ruling.md](E09-closing-ruling.md)); this spec's live
> body is the rewrite section. The staging sections beneath it remain the authored-end
> historical record.

> **SLOT 1 RULED, same day: the self-hosted clean chain.** The Director picked the
> fully-owned route — Wan T2V performance clip → MediaPipe lift → the studio's own solver
> onto the rig — over any hosted vendor contract; marathon pace, studio-building over
> shortcuts. The MediaPipe licence is fetched at all three layers (repo, package, the
> models' own Apache card — map rows landed 2026-08-11). **E09
> ([E09-clean-chain-calibration.md](E09-clean-chain-calibration.md)) is dispatched to build
> and calibrate the chain's solver; this spec's rewrite follows E09's report.**

---

# THE REWRITE — 2026-08-12: the first painted shot, on the calibrated chain

**Seat: executor (run on Opus) · new branch `E08-shot` from `main` (≥ `3728a59`), fresh
worktree `E:\AI\armature-E08b`** (the old `E08-run` bank is subsumed by the E09 merge and
awaits retirement — do not build on it). **Ceiling: ≤ 3 generations wave 1** (1 probe + 2
reserve on named causes); `estimate_credits` runs and is recorded BEFORE the first
submission — this route's billing meter is a premise, not an assumption. Both meters
reported.

## Trajectory (the rewrite's)

This is the product's first shot: footage of the performer, **both stages generative**,
every dependency licence-mapped, publishable by construction. E09 supplies the motion (the
baseline dance on his rig); this experiment supplies the paint. Everything after it — other
dances, other scenes, the movement library, the bar walk — reuses what this shot proves.

## The question

**Does the painted output show HIM performing the baseline dance in a prompt-described
scene?** Three clauses, read separately at the sheet: (1) **motion adherence** — the
painted figure performs the rig's dance (panels against the previz); (2) **identity** — the
same character; canon; the Director's eye only, with the stylized-reference floor expected
lower than photoreal benchmarks (G13); (3) **scene-from-prompt** — how much of the bar
arrives from text (G15 says motion is designed to dominate text; this clause is measured,
never promised).

## Route (consult #6 R1 + the grounding, all pieces measured)

Own-built **`WanAnimateToVideo`** graph — the served template wires the banned detector
tier (map trap #3); the template law stands. Inputs:

- `positive` / `negative`: the scene prompt (a crowded, warmly lit bar) + the identity
  clause; recorded verbatim in the payload record.
- `pose_video`: **rig-rendered pose sticks** of the baseline dance — the commission below.
- `reference_image`: the Director-approved twin, `E:\AI\training\facet_E33\twins\
  twin_r3_v0.png`, hash-pinned at use — the canon seed of the locked reference set (G14);
  the multi-view GLB reference set arrives only after the brush pass (ledger).
- `background_video`: **unconnected** — clause 3 exists to measure what the prompt paints.
- `face_video`: **unconnected in wave 1** (one-variable discipline; the expression lever is
  named for later — G7).
- `character_mask`: wired **only if** its animation-mode semantics verify from the node
  schema/docs; the decision and its source are recorded either way.

**The commission — `tools/render_pose_sticks.py` (+ pure module, tests ride):** render the
E09 baseline motion (`outputs/E09/b2-a3-lifted/performer_dance_ema.glb`, md5
`cd4e2f6ee85e…`, and its motion record) as pose-stick frames in the **pinned Wan
convention** — `human_visualization.py` at the sha banked in the E09 route2 evidence:
zeroed-black canvas, the 20-entry OpenPose rainbow palette, the 18-point `limbSeq`
including the five head keypoints (nose/eyes/ears markers derived from the head bone and
skull geometry), `stickwidth = max(int(min(H,W)/200) − 1, 1)`, hands drawn separately
(static mitten-hand sticks from the wrist bones — the rig has no fingers; recorded as a
known degradation, G6). Tests: palette/topology/width assertions + golden frames. Frames at
**832×480×65, 16 fps** (Gate L on the actual graph).

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The baseline motion (E09 A3), its GLB + motion record | **MEASURED** — hashes in the E09 report; re-verify at use |
| 2 | The drawing convention | **MEASURED** — Apache source fetched + banked with hash (E09 route2); pin the sha in the payload record |
| 3 | The twin reference, Director-approved | **MEASURED** — hash it at use |
| 4 | `WanAnimateToVideo` socket schema (six optionals) | **MEASURED** — catalog `get_node`, 2026-08-11 (consult #6 calibration) |
| 5 | Licence rows: Animate-14B weights (Apache), core node code (GPL-3.0, output clause), the convention source (Apache) | **MEASURED** — the map |
| 6 | The model accepts CG-rendered sticks at product quality | **ASSUMED — this is the experiment** (G11: the render-don't-detect pattern is published; this exact model is not) |
| 7 | Billing meter for this route | **ASSUMED until `estimate_credits` runs** — Gate C arms on the measured number before submission |

## Hypotheses — executor states blind degrees before submission

- **H-E08a (motion):** adherence visible at sheet level; degree predicted blind.
- **H-E08b (identity):** unknown; the Director judges; the stylized floor (G13) is the
  prior. Identity metrics ride as diagnostics and gate nothing.
- **H-E08c (scene):** partial scene from prompt (G15); the measured fraction is the
  finding, whatever it is.
- **H-E08d (proportions):** the non-human skeleton is out-of-distribution risk (G9, G10) —
  watch for the model "humanizing" his limbs; panels at the elbows and skull.

## Gates

Gate ROUTE on the built graph **and** on the saved file (`gate_saved_graph.py`) · Gate S
(`specs/E08-seeds.json` committed before submission) · Gate L on the actual graph · Gate C
(the measured billing number × ≤ 3 generations; halt before any submission that would
exceed) · watchdog before local renders · uploads compensator: every uploaded artifact
(stick frames, reference PNG) listed in the report with its server-side delete as the named
undo. A fired gate halts the session.

## The sheet and the report

Gate 0 sheet: **control (sticks) | painted output | reference | provenance**, with the E09
previz beside it as the motion's ground truth; review clip 0.5× / 8 fps from lossless;
arms first, then hands, skull, and the bar itself. Report appended as
`docs/experiments/E08-report.md`: measurements, both meters, gate states, predictions vs
outcomes with blindness disclosed. The advisor rules; the Director judges the shot.

## Out of scope (wave 1)

Multi-shot persistence (the locked-set discipline starts here but is proven later) · the
bar-walk locomotion shot · `face_video` · the aspect/figure-size variable (E10) · the
movement-library sourcing arc · the brush pass.

## Standards compliance (the rewrite's)

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | 2 | convention sha, motion hashes, seeds, verbatim payloads |
| ANDON_AUTHORITY | 3 | ROUTE/S/L/C raise in-tool before spend; saved-file re-admission |
| NAMED_COMPENSATORS | 2 | uploads deletable server-side + bounded spend, both tabled — no skip |
| DECOMPOSE_BY_SECRETS | 2 | sticks renderer = pure module + thin bpy shell |
| UNCERTAINTY_GATED_HUMANS | 2 | blind hypotheses; halts surface contrastively; identity is the Director's |
| EXTERNAL_VERIFIER | 2 | gates + the Director's eye; no self-grading anywhere |

## Amendments (the rewrite's)

**R-A1 — 2026-08-12 (the Director's call, mid-run):** the executor read the core node's
source and found `WanAnimateToVideo` **center-crops `reference_image` to the generation
size** (`common_upscale(..., "area", "center")`) — so the 352×1024 portrait twin would have
reached the model as a 204-row band (19.9 %: hips and thighs; no head, no face, no hands).
Surfaced with options; **the Director ruled: letterbox the whole figure.** The letterbox
derivation is a committed, tested tool rather than an inline script, and the padded
reference is hashed into the payload record. What this changes about the probe's reading:
clause 2 (identity) is now measured through a whole-figure reference whose face is small —
the figure scales to ≈165×480 inside the 832×480 frame — stacked on the stylized-reference
floor (G13). **Wave 1's identity result is therefore a floor, not the route's ceiling**;
the named lever is a native-832×480 reference set with the figure filling the frame, which
arrives with the brush-passed GLB renders (ledger). Premise 3 carries this note.

---

## Trajectory

This IS the product. armature is image-to-video with a GLB instead of an image, and to date
not one frame of an authored performance exists. E08 stages the Director's named shot —
the walk to the bartender in a crowded bar — as previz: the performer walks, stops
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
