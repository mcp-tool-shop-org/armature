# S04 — the sprite shot-set instrument: orthographic turnaround (support dispatch)

**Dispatched 2026-08-13 on the Director's word, closing the gap consult #11 R3 named:
the headless turnaround instrument gains parallel projection, completing the GLB →
2.5D sprite shot-set capability on the repo's own shelf.** Branch/worktree: `S04-run`
at `E:\AI\armature-S04`. **Zero credits — this dispatch is fully local; no cloud
interaction of any kind. Any submission attempt is out of spec and halts the run.**

| Trajectory | A sprite shot-set is one more consumer of the staged scene — the same GLB, camera rig and alpha law that feed every video route, exercised at parallel projection. The shared-scale solve and the crop gate harden the turnaround instrument that builds reference kits for the composed and driven routes, and the finished shot-set serves the studio's painted 2.5D line downstream (facet's territory, untouched). Instrument work, advancing the full GLB→footage scope; no route is created or displaced. |
|---|---|

## The question

Can `render_turnaround` produce a true orthographic 8-direction sprite shot-set — one
shared scale across all cells, alpha cutouts, full provenance — with the perspective
path untouched when the flag is absent?

## Premises

| premise | status |
|---|---|
| `render_turnaround.py` solves **one radius across all azimuths** (`solve_radius_for_height(cloud, target, azimuths, …)`, called once) — the shared-framing property the ortho path must mirror | **MEASURED** — read 2026-08-13 (advisor seat, this session) |
| No orthographic support exists anywhere in the tool | **MEASURED** — case-insensitive grep, zero matches, 2026-08-13 |
| A silhouette-extent utility exists and is evaluated per azimuth (used by the radius solve and per-view records) | **MEASURED that it exists and where it is called**; its exact signature and semantics — **enumerate before extending** (the S03 law) |
| Blender 5.2 headless supports `camera.type='ORTHO'` + `ortho_scale` | **ASSUMED** — standard API; verified by the first unit render before any batch |
| Proof GLB: `E:\AI\training\facet_E33\out\performer_textured.glb` (sha256 `9e20ea7d…`, full hash in facet's known-defects entry) | **MEASURED by the cross-repo record**; executor re-verifies path + hash at start. `E:\AI\training` is read-only law. **Its texture holes are known** (facet's top-priority arc) and are not this instrument's subject: they will appear in beauty cells, pre-known, not findings |
| Gate ALPHA and the authored-alpha law (`film_transparent`, RGBA masters) already ride the tool | **MEASURED** — this session's read; the S03 kit the Director passed |

## Task A — the flag

Add `--ortho` to `render_turnaround.py`. Semantics:

1. Camera type `ORTHO`. **One shared `ortho_scale` across all views**, derived from the
   **maximum silhouette extent over the full azimuth set** at the locked elevation, so
   the largest view occupies `--height-frac` of the frame — constant scale across the
   sheet is the sprite property, and a per-view solve would defeat it. Radius keeps only
   its positional role (a clipping-safe distance).
2. **The perspective path is untouched when the flag is absent.** The branch point is
   the only shared edit; a unit test asserts default arguments select the perspective
   branch. (Renders are not pixel-compared for this — the invariant is structural.)
3. Provenance JSON records camera type and the shared `ortho_scale` beside everything it
   already records.
4. Enumerate the tool's and the extent utility's interfaces before extending either;
   tests ride the same commit.

## Task B — Gate CROP

The andon on the direction the solve does not bound: the shared scale is derived from
sampled extents, so under-sampling shows up as a **cropped view**. After each view's
render, if the subject's alpha touches the frame border, **raise** — a shot-set with a
cropped cell is the failure this instrument exists to refuse. The gate lives inside the
tool and raises (never asserts); a red test forcing border contact rides the commit.
Gate ALPHA continues per view unchanged.

## Task C — the shot-set proof

1. **Verify the VRAM watchdog first** (Blender is GPU work). All Blender through
   PowerShell, headless only.
2. Run the preset on the proof GLB: **8 views, 45° steps, elevation 30°, 1024×1024
   cells, RGBA** — the verbatim invocation pinned in the report.
3. Compose the shot-set sheet (enumerate the `sheet_compose` family's interface first),
   and a second sheet placing the ortho cells beside the existing perspective turnaround
   at the same elevation for comparison.
4. Both sheets to the Director's eye via the advisor. Outputs under `outputs/S04/` with
   a manifest: tool + Blender versions, GLB hash, per-view sha256, per-view alpha
   extrema, border-contact booleans, the shared ortho_scale.

## Hypotheses (advisor's, blind — no S04 artifact exists)

A "view" is one rendered azimuth cell of the proof GLB at the locked elevation; 8 per
set. Each clause predicted separately.

| id | clause | prediction |
|---|---|---|
| H-S04a | the ortho branch renders 8/8 views with Gate ALPHA green at the preset | YES — high confidence |
| H-S04b | the shared ortho_scale holds the subject fully inside frame on all 8 views (Gate CROP silent) at elevation 30° | YES — the max-extent solve samples every azimuth; the pose's extremes are lateral and sampled |
| H-S04c | at the Director's eye, the ortho cells read as sprite cells — constant scale, no perspective convergence — where the perspective set visibly foreshortens | his call alone; I predict he prefers ortho for sprite cells specifically. Graded only by his verdict (the E14 law: no seat's frame-read grades an identity- or preference-clause) |

## Metrics (diagnostics; they gate nothing beyond the named gates)

Per-view alpha extrema · border-contact boolean per view · the shared ortho_scale ·
wall-clock per view. The Director's eye judges the cells.

## Credit ceiling and disclosure

**0 credits — fully local; nothing leaves the rig.** No upload, no estimate call, no
submission surface touched. This is the per-route disclosure for a fully-local
instrument, stated as the law requires.

## Licence checks introduced

**None.** No new model, weight, LoRA, or dependency. Blender is the standing tool.

## Out of scope

The normal/depth-pass orbit variant (a named follow-on if dynamic-lit sprites are
wanted) · any repaint or restylize (the painted 2.5D line is facet's territory) ·
texture-hole anything (facet's arc; holes appear in beauty cells pre-known) · engine
packing formats · changing the perspective defaults · any generation.

## Gates and halts

Stale watchdog → HALT. Interface not enumerated → enumerate before extending. Flat
alpha on any view → that view FAILS, report. Gate CROP raises in-tool. Any cloud call →
HALT. No judging anywhere: sheets and measurements; the words *verified, shipped,
works, decisive, validated, proven* do not appear; the Director's eye rules the cells.
A negative result is a full success.

## Report

`docs/dispatches/S04-report.md` on `S04-run`; commit and push the branch, **do not
merge**. The executor's own predictions are committed **before the first Task-C
render**, blindness disclosed honestly (Tasks A–B are build-and-test; the judged
artifact is Task C's). Run the suite plus the `-O` pass before the close; report the
worktree count beside `main`'s, assert nothing about the skew.

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 2 | GLB hash, tool + Blender versions, per-view sha256, the shared ortho_scale, and the verbatim Task-C invocation all recorded; the proof rebuilds from the manifest |
| ANDON_AUTHORITY | 2 | four named halts (watchdog, alpha, CROP, cloud-call), each at the step it gates; CROP raises inside the tool with a red test proving it can fire |
| NAMED_COMPENSATORS | 2 | nothing irreversible: local renders land in fresh `outputs/S04/` directories (delete by directory), the branch push reverts by `git revert`; zero credits and zero uploads by construction |
| DECOMPOSE_BY_SECRETS | 2 | the ortho branch isolates at the camera-rig seam; sheet composition stays in the sheet tools; the extent utility is extended only after enumeration |
| UNCERTAINTY_GATED_HUMANS | 2 | the shot-set ships to the Director's eye before anything consumes it; H-S04c is explicitly his verdict, not a seat's |
| EXTERNAL_VERIFIER | 2 | alpha arithmetic and border-contact checks are mechanical; the standing human verifier judges the cells; the advisor (a different seat) rules on the report |
