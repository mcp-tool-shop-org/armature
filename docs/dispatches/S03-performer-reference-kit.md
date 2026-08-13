# S03 — the performer reference kit (support dispatch)

**Dispatched 2026-08-13 on the Director's word: E13 holds per shape 1 of the halt ruling
([E13-halt-ruling.md](../experiments/E13-halt-ruling.md) R7). This dispatch produces the
assets and zero-credit measurements E13 waits behind.** Branch/worktree: `S03-run` at
`E:\AI\armature-S03`. **Zero partner credits — no API/partner node appears in any
submitted graph; a partner-credit estimate above 0 halts the run.**

| Trajectory | Reference kits with authored alpha serve every route that takes a reference — the composed route today, the driven route at its unpark, any tier that binds identity from what it is handed. And the frames→VIDEO chain, if it holds, opens every VIDEO-typed socket on the platform to authored clips: performance references, driving videos, edit sources. Both advance the full GLB→video scope independent of any single route's fate. |
|---|---|

## Premises

| premise | status |
|---|---|
| `turn_final` (E:\AI\training\facet_E33\turn_final\, `armfinal_0…7`, RGBA 352×1024) is defective: alpha extrema (255,255) on all 8; white texture-projection holes on views 1,2,3,5,6,7; 0 and 4 clean | **MEASURED** — E13 report asset survey, full-size look, 2026-08-13 |
| Performer GLBs on the rig: `E:\AI\training\facet_E33\performer_300k.glb` (12.75 MB), `performer_raw.glb` (36.19 MB); `E:\AI\armature-E09\outputs\E09\b2-a3-lifted\performer_dance_ema.glb` (13.00 MB, E11's start) | **MEASURED** — E13 report §5; re-verify sizes and hash at start |
| E12's start frame descends from a performer GLB recorded in E12's plate/start-frame provenance | **ASSUMED** — verify from the E12 worktree's provenance JSON before rendering; ambiguity → HALT, never guess |
| **Coherence row (the halt ruling's new law):** the rendered turnaround's subject and texture lineage = the A2 clip's performer | verified at the look — same character, same appearance, stated with evidence in the report |
| `tools/render_performer.py` (shaded pass) and `tools/stage_render.py` (control-sequence exporter) exist in-repo; Blender headless renders true alpha natively | **MEASURED** — E13 report §5; enumerate both interfaces before extending either |
| `CreateVideo` served: core, `images` IMAGE + `fps` FLOAT (1–120) → VIDEO, optional audio/bit_depth, `api_node: false` | **MEASURED** — halt ruling R2, `get_node` 2026-08-13 |
| The E02 batch mechanism feeds an IMAGE socket at scale | **MEASURED** historically (the E02 record); at 81 frames into `CreateVideo` — **ASSUMED** until Task C runs |
| The A2 clip's 81 lossless frames exist, decode-verified | **MEASURED** — E12 worktree `outputs/E12/probe/w3-seed1/lossless/` n=81, gate_b evidence |
| The r2v node accepts a constructed VIDEO at runtime | **ASSUMED — not provable at zero credits.** Typed-compatible; stays assumed until E13's first real submission. The named residual; Task C cannot and does not claim it |

## Task A — the RGBA-true turnaround (fully local; nothing leaves the rig)

1. **Verify the VRAM watchdog first** (Blender is GPU work). All Blender calls through
   PowerShell, headless only.
2. Identify the canonical performer GLB by lineage: read E12's plate/start-frame
   provenance, trace which GLB the A2 clip's start frame descends from, and pick the
   canonical (unposed) performer asset on that lineage. Pin path + sha256 in the
   manifest. Ambiguity → HALT with what you found.
3. Render 8 views matching `turn_final`'s azimuth convention and framing (352×1024
   unless the tool's native framing argues otherwise — record the choice and reason),
   **RGBA PNGs with real alpha**: verify per-view alpha extrema ≠ (255,255). A flat-alpha
   view FAILS and is reported, not shipped.
4. Enumerate the two renderers' interfaces before extending either; tests ride any tool
   change, same commit.
5. Output `outputs/S03/turn_rgba/` + manifest: tool + version, Blender build, GLB hash,
   per-view sha256, per-view alpha extrema.

## Task B — the hole survey (evidence for facet's arc; no fixing here)

Full-size per-view renders of the new set beside `turn_final`'s old views, plus one
contact sheet; per-view factual notes on white unpainted patches (present/absent,
where). Alpha will differ by construction; **texture holes are expected to persist** —
they live in the texture, and texture repair is facet's projection-coverage arc, out of
scope here (facet's tree and E:\AI\training are read-only law). The survey documents;
the Director's eye rules which views are usable.

## Task C — the frames→VIDEO chain, at zero partner credits

1. Source: the 81 lossless frames, verified against the E12 gate_b record before use.
2. Upload the frames; build the assembly graph **in-repo**: batch → `CreateVideo`
   (fps=16) → save class. **No partner/API node anywhere in it.**
3. Teach the round-trip table every class this graph needs — this path *executes*, so
   its green rows are earned, unlike the untravelled r2v row the E13 executor rightly
   refused. Gate ROUTE walks the graph; tests ride the commit.
4. `estimate_credits` before submission: expected 0 / GPU-hour-metered. **Any
   partner-credit estimate above 0 → HALT.**
5. Download the produced VIDEO; verify: frame count 81, fps 16, and per-frame pixel
   comparison against the source frames (the Gate B decode-compare shape). Record all
   hashes.
6. Verdict shape: each chain link **MEASURED or FAILED with evidence**; the
   r2v-acceptance link stays **ASSUMED** and the report says so in those words.

## Disclosure (per-route disclosure law — measurement addendum)

Task C uploads 81 PNG frames of a clip Comfy Cloud itself generated (E12 w3 seed 1)
back to Comfy Cloud: content-addressed, **no delete endpoint on this API surface**,
inert unless a graph names them. The exposure delta over the already-hosted source
generation is the frames themselves. Tasks A and B are fully local — nothing leaves
the rig.

## Gates and halts

Stale watchdog → HALT. GLB lineage ambiguous → HALT. Flat alpha on any Task-A view →
that view FAILS, report. Gate ROUTE failure → HALT. Partner-credit estimate > 0 →
HALT. No judging anywhere: sheets and measurements; the words *verified, shipped,
works, decisive, validated, proven* do not appear; the Director's eye rules the kit.

## Report

`docs/dispatches/S03-report.md` on `S03-run`; commit and push the branch, **do not
merge**. Run the suite before the close and report it beside `main`'s numbers — the
worktree skip-skew (35 rig-local tests) is a flagged instrument item; report both
counts, assert nothing about the gap.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | GLB hash, tool + Blender versions, per-view sha256, full graph and payload records; frames verified against the E12 pin before use |
| ANDON_AUTHORITY | 2 | five named halts (watchdog, lineage, alpha, route, credits), each at the step it gates; Gate ROUTE raises in-tool |
| NAMED_COMPENSATORS | 2 | uploads carry the no-delete-endpoint disclosure (E12 convention, listed in the report); local outputs delete by directory; zero credits by construction — nothing else irreversible |
| DECOMPOSE_BY_SECRETS | 2 | A (render) / B (evidence) / C (chain) isolated; C teaches the round-trip table only classes it actually executes |
| UNCERTAINTY_GATED_HUMANS | 2 | the kit ships to the Director's eye before E13 re-arms; the coherence row is verified by look, not asserted |
| EXTERNAL_VERIFIER | 2 | pixel decode-compare against pinned sources on Task C; Task A verified by alpha arithmetic + the standing human verifier |
