# E13 — the composed-route probe (spec)

**Status:** SPEC — written 2026-08-12 on the Director's word ("make this E13, to run
when E12 lands"). **QUEUED.** Dispatch requires ALL of: **(1)** E12 has landed
(reported and ruled); **(2)** the terms gate below is cleared; **(3)** a fresh credit
re-estimate at dispatch with the exact overrides. The executor paste block is delivered
at dispatch, not before.
**Route:** the composed route — authored references into the Wan 2.7 reference-to-video
partner tier (`Wan2ReferenceVideoApi`, model `wan2.7-r2v`, hosted).
**Branch/worktree convention:** `E13-run` at `E:\AI\armature-E13`.

| Trajectory | This spend probes whether a native identity-lock tier can serve the product when **everything handed to it is authored** — turnaround stills and performance clips we own. If identity holds, the scope gains a footage class where model-decided cinematography is acceptable (performance studies, motion reels, idea footage) and the studio learns what the lock is worth on a stylized character no platform documents. If it fails, the negative closes the tier honestly and the authored-spatial routes stand alone, measured twice. |
|---|---|

## The question

Consult #8 measured the r2v tier spatially opaque: nothing is authorable except the
references themselves. So the probe asks exactly that: **from authored references —
stills versus a clip — does `wan2.7-r2v` hold OUR character's identity, and what does
its model-decided spatial behavior do with what it is handed?**

## The terms gate (blocks dispatch; two unblock paths, both the Director's)

The Comfy-side ToS row is retrieved and stands ("Customer retains all right, title, and
interest in and to… Output"; no training on Input/Output). The **provider-side**
document is NOT RETRIEVED (map row, 2026-08-12: `create.wan.video/terms` is a
JS-rendered shell; Alibaba's master ToS carries no AI-output clauses). The map's
standing treatment for partner tiers blocks use until the provider document exists.
E13 dispatches only when either:

1. the provider document is fetched (the Director's browser-export path is the known
   instrument) and its row is ruled through the gate; **or**
2. the Director rules the Comfy ToS row sufficient for this tier — a CONDITIONAL,
   recorded in the map at ruling time.

`watermark=false` is pinned in every payload; if any fetched term conditions commercial
use on watermarking, that is a new CONDITIONAL for the Director before submission.

## Premises

| premise | status |
|---|---|
| `Wan2ReferenceVideoApi` contract: `model.reference_images.image1…5`, `model.reference_videos.video1…3`, 720P/1080P, ratio ×5, duration 2–10, `characterN` prompt convention, seed, watermark default false | **MEASURED** — `get_node` twice on 2026-08-12 (morning; re-measured byte-consistent at the consult #8 ruling) |
| Template `api_wan2_7_r2v` exists server-side | **MEASURED** — `estimate_credits` resolved it, 2026-08-12 (reference only; the submitted graph is built in-repo) |
| Price ≈ **106–211 credits per generation** | **ESTIMATED** — bundled pricing catalog, 2026-08-12; can lag live prices; **re-estimate at dispatch** with the exact resolution/duration |
| Comfy-side output-ownership terms | **MEASURED** (map row) — provider-side NOT RETRIEVED → the terms gate above |
| Stylized-reference behavior (a wooden, non-photoreal character) | **UNKNOWN BY DESIGN** — the probe's central question; the platform documents nothing |
| `characterN` ↔ upload-slot binding order | **NOT VISIBLE** — record exactly what is sent per slot; observe what binds |
| A1 references: facet's canonical turnaround renders (consumed READ-ONLY from facet's tree; rig-local — CI skips visibly) | **MEASURED** (facet canon exists); authored-RGBA law applies — submitted RGB composites recorded with reasons |
| A2 reference clip: E08's painted shot (banked, Director-judged a strong first result) or E12's best output | **PENDING the Director's pick at dispatch** — E12's candidacy exists only if E12 lands well |
| Reference-clip format/length constraints on the video slots | **NOT VISIBLE** — a platform rejection is a finding, not a failure |

## Arms — one variable: the reference modality

Common to both arms: model `wan2.7-r2v` · 720P · 16:9 · duration 5 · `watermark=false`
· the same performance-led prompt using `character1` (no scene naming, no quoted
dialogue — quoted dialogue invokes lip-sync/voice, out of scope) · the same two seeds
across arms · negative prompt minimal and recorded verbatim.

- **A1 — stills.** `model.reference_images.image1…imageN` (3–5 canonical turnaround
  renders: front, three-quarter, profile at minimum), slot order recorded.
- **A2 — the clip.** `model.reference_videos.video1` = the authored performance clip
  the Director picks at dispatch.

Two seeds per arm (scene claims need two seeds; the tier's worlds are model-decided,
so world claims WILL arise). **Four submissions total.**

## Hypotheses (the advisor's, written blind at spec time — before any E13 artifact)

| id | clause | prediction |
|---|---|---|
| H-E13a | A1 (stills): identity reads as the twin's at the Director's zoom | holds on **at most 1 of 2 seeds** — the stylized character defeats consistent binding from stills |
| H-E13b | A2 (clip): identity reads as the twin's | holds on **2 of 2** — the richer signal binds |
| H-E13c | model-decided worlds differ across the two seeds within each arm | DIFFER (the seed-volatility law, both prior sightings) |
| H-E13d | `watermark=false` is honored — no visible watermark | YES |

## Credit ceiling

**Four submissions.** Estimate bracket 424–844 credits total (4 × 106–211, bundled
catalog 2026-08-12). At dispatch the executor re-estimates with the exact overrides;
**if the re-estimated total exceeds 900 credits, HALT and surface to the Director
before any submission.** No re-runs; a fired gate ends the run where it stands. Spent
credits have no compensator — the ceiling is the honest treatment.

## Gates and admission

- **The terms gate** (above) — spec-level, blocks dispatch.
- **The graph is built in-repo** (the template is a reference, never a route) and
  passes the saved-graph round-trip, which fails closed on unknown classes — the
  executor teaches the round-trip table `Wan2ReferenceVideoApi` (and the save/output
  class the graph uses) with tests riding the same commit; Gate ROUTE walks what it
  knows.
- **Gate PAIR:** n/a — no local weights load on this tier (hosted); recorded as n/a,
  not skipped silently.
- **Authored-reference hygiene:** A1 stills are whole-figure canonical renders under
  the RGBA law (composited RGB recorded with reason); the A2 clip's provenance
  (experiment, prompt_id, hash) rides the payload record.
- **Uploads and saved cloud workflows:** delete commands listed in the report (E11
  convention).

## Metrics and sheets (diagnostics; the Director's eye is the verdict)

A references | output | provenance sheet per arm before any number is quoted (the
existing sheet tooling extends to a references strip if needed — enumerate first;
tests ride any change; every provenance line derives from the run's record, `NOT
RECORDED` fallbacks). Stills where structure is hardest — hands, face, turns. Clips
judged in motion AND as frames. Identity is canon and his; no metric approximates it;
`measure_clip` diagnostics ride the report and gate nothing.

## Out of scope

Dialogue / lip-sync / voice (no quoted dialogue anywhere) · the 2.6 voice tier ·
1080P · multi-character (`character2`) · any local-control composition (measured
impossible at consult #8) · any adoption ruling — this is a probe; adoption would be
its own Director decision on the probe's evidence · prompt experimentation beyond the
one pinned prompt.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | every submission records the full payload (all dotted fields incl. slot order), seed, reference hashes, and the estimate at dispatch; graphs submitted as saved files verbatim |
| ANDON_AUTHORITY | 3 | the terms gate blocks dispatch; the round-trip gate fails closed on unknown classes; the 900-credit re-estimate halt fires before any submission; all raise in-tool |
| NAMED_COMPENSATORS | 2 | upload/saved-workflow deletes named in the report; spent credits have no undo — the bounded four-submission ceiling is the honest treatment (no skip claimed) |
| DECOMPOSE_BY_SECRETS | 2 | one variable (reference modality) between arms; seeds pinned across arms; tooling changes ride their own tested commits |
| UNCERTAINTY_GATED_HUMANS | 3 | two Director checkpoints gate on genuinely his calls: the terms CONDITIONAL and the A2 clip pick — both before spend, both contrastively framed |
| EXTERNAL_VERIFIER | 2 | no model grades its own output; identity is judged by the Director's eye, the studio's standing verifier; diagnostics gate nothing |
