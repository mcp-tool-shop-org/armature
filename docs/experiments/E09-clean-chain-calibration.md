# E09 — the clean chain, calibrated: generated motion onto his bones, measured before the shot

**Seat:** executor (run on Opus) · **Spec written:** 2026-08-11 by the advisor, before the work ·
**Advisor rules after the report** · **Director judges every sheet** · **Credit ceiling: 8
(2 generations × the measured 4/generation) — Stage B2 only; Stages A and B1 spend nothing.**
Worktree: `E:\AI\armature-E09`, branch `E09-run`.

## Trajectory

SLOT 1 of the confirmed two-slot route. The Director picked the **self-hosted clean chain** —
a Wan T2V performance clip, a MediaPipe lift, and our own solver landing the motion on the
performer's rig — over any hosted vendor contract: everything in the studio's hands, built at
marathon pace. This experiment builds the chain's one missing tool (the solver) and measures
the chain's floor **before** the first shot spends a credit on it. Every later performance —
dance, emote, walk, any footage — runs through what this experiment calibrates.

## The question

**Can the clean chain land generated human motion on the performer's rig at a quality worth a
shot?** Three clauses, predicted and read separately:

1. **The solver is correct** — on synthetic ground truth, rotations round-trip through
   landmark positions at numerical tolerance.
2. **The lift is measurable end-to-end** — a render of the performer performing a known
   motion goes through MediaPipe and back; solved rotations are compared against the known
   ones. Conditional on the detector firing on a stylized mannequin at all — either outcome
   is a full result.
3. **The chain works on its true population** — a generated human dance clip, lifted and
   solved onto his rig, reads as the dance at the Director's eye.

## Research grounding (cited by G-number → [research-grounding-e08.md](../research-grounding-e08.md))

The chain is the only fully-owned SLOT-1 route the field allows (G1–G5). The solver's shape
is the literature's, not improvised: two-bone analytic IK with pole/twist references, because
positions underdetermine twist (G16); world landmarks are hip-origin and the card rules out
metric depth, so root motion is out of scope here (G16, map row); dance is the stress case
for feet and no jitter benchmark exists for this landmarker, so both are measured, not
assumed (G4, G17). Foot artifacts are graded, never silently corrected (G17).

## Stages — each varies one thing

**Stage A — the solver, against math (local, free).**
Commission `tools/armature_core/lift_solve.py` (pure module, **no bpy** — testable) +
`tools/lift_solve.py` (the Blender-side applier): input = 33 MediaPipe-topology world
landmarks per frame; output = joint rotations on the 22-bone rig + a recorded
landmark→bone mapping table (fingers unused — mitten hands). Method: hip-centering,
per-limb two-bone analytic IK, pole/twist from the bind pose. **Round-trip test:** author
known rotations → FK to landmark positions → solve → compare. Pass condition: error at
numerical tolerance (the unit the experiment cannot move). Anything above is a solver
defect, never a tuning target. Tests ride the commit.

**Stage B1 — ground truth through the real detector (local, free).**
Fixture: the banked walk (`git checkout 8399d5a -- tools/walk.py tools/author_walk.py` into
this worktree — the banked tooling serves as a **measurement fixture with known ground
truth**; it is not any shot's motion source and the generative frame stands). Render the
performer performing it at 1080p (PowerShell, headless Blender, watchdog verified). **The
detection gate runs first and raises in-tool:** MediaPipe per-frame presence/visibility on
the mannequin render, reported before any error number is computed — a number from a
detector that did not fire is noise wearing a unit. If fired: per-joint solved-vs-authored
rotation error, bone-length stability, foot metrics, jitter before/after one EMA pass (the
single recorded lever). If not fired: a full negative result for this fixture class —
report and stop.

**Stage B2 — the true population (cloud; ceiling 8, probe first).**
**One** Wan 2.2 T2V generation: a single dancer, full body, mid-shot, plain background —
the card's own bounds (single person, head visible, near subject) written into the prompt,
which is recorded verbatim in the payload. 832×480×65 on the saved-route shape (E02 A2
no-control precedent — premise 6). Lift → solve → the performer performs it → control
render beside the source clip → the **Gate 0 sheet** (source | solved-on-rig |
provenance) at dailies standard before any number is quoted. Review at 0.5×, 8 fps, from
`lossless/`; stills where structure is hardest — hands, feet, turns. Reserve: 1 generation,
spent only on a defect with a named cause.

## Hypotheses — predictions stated before looking

- **H1 (A):** round-trip error ≈ 0 at tolerance. A miss is a bug.
- **H2 (B1):** detection on the stylized mannequin is genuinely uncertain — the executor
  writes a **blind prediction** (fires / does not, with expected presence range) before the
  first frame runs, and discloses that it was blind.
- **H3 (B2):** the lifted dance lands with visible jitter and foot noise (G4: no published
  jitter metric; G17: dance stresses contact) — degree measured; worth-a-shot is the
  Director's call at the sheet, not a threshold this spec invents (suspend rather than
  invent: numerator and denominator reported separately).

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The rigged performer: `E:\AI\armature-E07\outputs\E07\rig-repaired\performer_auto.glb`, sha256 `7f56c9ac…2a24` | **MEASURED** — re-verify the hash before use; copy in, never edit the E07 worktree |
| 2 | Banked walk tooling at `E08-run` @ `8399d5a` | **MEASURED** — branch verified this session; checkout paths named above |
| 3 | MediaPipe licence — repo, package (v1.0.0), and the models' own card all Apache-2.0 | **MEASURED 2026-08-11** — three fetched documents, rows in the licence map; pin installed versions in the report; a version bump re-fetches the card |
| 4 | The 33-landmark → 22-bone mapping is definable without finger bones | **ASSUMED** — the mapping table is part of the Stage A commission; recorded in code |
| 5 | 4 credits/generation planning number | **MEASURED** (E02 balance delta) — the Director's balance is the meter; GPU-hours metered separately and reported |
| 6 | The E02 A2 no-control payload shape serves the T2V clip | **ASSUMED** — verify the saved graph and link topology in code before submission; a `dry_run` PASS proves nothing |
| 7 | World landmarks are hip-origin; depth is non-metric | **MEASURED** (vendor docs + model card) — root motion out of scope for the dance; recorded |

## Environment

This experiment gives armature **its own venv**: `E:\AI\armature\.venv` (Python 3.11+),
`pip install mediapipe==1.0.0` (pinned; exact resolved versions in the report).
`trellis2-env` is not touched. VRAM watchdog verified before any render; Blender headless
via PowerShell only; scripts create their own output directories; `outputs/` stays out of
git — the record is the spec, the report, provenance JSON and sha256 manifests.

## Gates

Licence pin (premise 3; any new dependency halts for a map row) · **detection gate** (B1,
raises in-tool before any metric) · **Gate C** (ceiling 8; halt before any submission that
would exceed) · **Gate S** (seeds pre-registered, committed before the first submission) ·
**Gate L** (frame legality on the actual graph, derive-then-round) · the lossless tap ·
watchdog liveness before GPU work · the Blender success-sentinel (a crashed `blender -b -P`
exits 0 — verify a sentinel). A fired gate halts the session: report with evidence, never
re-parameterize past it.

## Out of scope

The first shot itself (E08's rewrite follows this report) · foot-lock correction (a lever
added only after B-stage measurement) · root motion / locomotion (the walk-to-the-bartender
wave) · identity (E08's clause, not this one) · the brush pass (rides E08's reference set) ·
skeleton v2 / fingers.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | Package + model versions pinned; seeds pre-registered; payloads + prompts recorded verbatim; fixture shas in premises |
| ANDON_AUTHORITY | **3** | Detection gate raises in-tool before metrics exist; Gate C halts before an exceeding submission; licence pin halts on any new dependency |
| NAMED_COMPENSATORS | **2** | Table below — no skip |
| DECOMPOSE_BY_SECRETS | **2** | The solver is a pure no-bpy module apart from the render/applier tooling; the mapping table is data, not code paths |
| UNCERTAINTY_GATED_HUMANS | **2** | Blind predictions disclosed; H3 suspends rather than invents a threshold; halts surface contrastively |
| EXTERNAL_VERIFIER | **2** | Stage A is graded by mathematics (round-trip), not by any model; B2 is graded by the Director's eye with diagnostics beside it; the executor judges nothing |

**Compensators:** cloud credits spent (Stage B2) — no undo; bounded at 8 and itemized,
owner = the advisor via Gate C. Venv creation — `Remove-Item -Recurse E:\AI\armature\.venv`,
owner = executor. Worktree/branch — `git worktree remove` + branch delete after the advisor
merges or discards, owner = advisor. Uploads to Comfy Cloud — deletable server-side,
owner = executor, listed in the report. No publishes, no releases, no external posts.

## Report

`docs/experiments/E09-report.md`: measurements only, no judgement words; every gate's state
(`NOT YET RUN` where true); both meters (credits, GPU-hours); the Gate 0 sheet path;
predictions vs outcomes with blindness disclosed. The advisor rules after; the Director's
eye decides what the numbers cannot.
