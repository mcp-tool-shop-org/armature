# E07 — the skeleton: a named-bone rig on the canonical character

**Seat:** executor · **Spec written:** 2026-08-11, before the work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 0 generations. This experiment
spends no credits.**

## Trajectory

**armature is image-to-video with a GLB instead of an image** — movies, cutscenes, character
poses and movement, any footage. Every one of those requires posing the canonical character
*on purpose*, and no asset on this rig can be posed on purpose: E01 measured the blackguard's
rig importing as 30 `EMPTY` objects named `bone_0…bone_29`, **zero of 18 anatomical sites
identifiable by name**. That gap was ruled armature's blocking dependency (E03 closing,
Ruling 7), the attempt to route around it with a wire proxy failed on measurement (E06 closing,
Ruling 2), and nothing governs against closing it (E03 closing, Ruling 12). The Director named
this exact sequence: *"shouldn't there be a process of creating the skeleton before trying to
move the limbs?"*

E07 builds the skeleton. Its follow-on, E08, stages the first authored performance **of the
character** — the first frames of the actual product.

## The question

**Can the canonical character be given a rig with anatomically named bones that (a) covers the
registered site list completely, (b) preserves the rest pose, and (c) deforms without shredding
when posed** — so that authored performances are staged on *him*, not on a wire proxy?

(c) is judged by the Director on the sheet. (a) and (b) are gated in code.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The canonical asset is `E:\AI\training\_p0_packs_modernize\_mesh_line\blackguard\blackguard_unirig_rigged.glb`, sha256 `404e8445…` | **MEASURED** — `specs/E02-control-blackguard.json`, re-verify the hash before first use |
| 2 | Its rig imports as 30 EMPTYs, 0/18 named sites | **MEASURED** — E01 report; re-verify on import and record what Blender 5.2 actually produces |
| 3 | A sibling file in that directory may be a cleaner unrigged source | **ASSUMED** — enumerate the directory before choosing the source; a pre-rig A-pose GLB beats stripping a broken rig. Choice recorded with reasons |
| 4 | Blender 5.2 slotted-action API shape | **MEASURED** — `tools/make_test_armature.py` `_action_fcurves`, measured on this rig 2026-08-10 |
| 5 | `ARMATURE_AUTO` automatic weights produce a usable, non-shredding deform on this mesh | **ASSUMED — this is the thing the experiment measures.** UniRig's shredding of faced characters is a measured property of UniRig, not of skinning in general; whether Blender's bone-heat weighting fails the same way here is unknown |
| 6 | The GLB's mesh is skinnable as imported (object count, loose parts, manifoldness) | **ASSUMED** — measure on import, report per-object stats before rigging |

## Instruments — enumerated first, one commission justified

**Enumerated in `tools/`:** `make_test_armature.py` (procedural armature + slotted-action
handling — the rhyme for this work), `stage_render.py` (renders any staged scene; E01),
`compare_runs.py`, the sheet builders. **No rigging tool exists** — grepped `tools/` for
`rig|skin|weight|bone` beyond the test armature; nothing. **COMMISSION: `tools/rig_character.py`**
— given a source GLB and a site list, builds a named-bone armature, skins the mesh, authors the
probe action, exports the rigged GLB + manifest. **Tests ride the commit.** Each fixture answers:
what would this look like if the code were wrong in the way this check exists to catch?

## The site list — registered before the first bone

E01's report is re-read at build time. **If it enumerates the 18 sites, that list governs. If it
does not, the executor registers a list before any rigging begins** (Blender humanoid
convention: hips, spine, chest, neck, head; L/R shoulder, upper_arm, forearm, hand, thigh,
shin, foot — adjusted to whatever count E01's "18" actually denotes, with the discrepancy
reported rather than reconciled silently). Either way the list is committed **before** the
first bone is placed. A site list chosen after seeing what was easy to rig is name-shopping.

## Build order

1. **Verify the watchdog** (`pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1` — live
   heartbeat confirmed) before any Blender/GPU step. It was found dead 2026-08-11.
2. Enumerate the blackguard directory; choose and record the source (premise 3).
3. Import; measure premise 6; set scene fps **before** any animation work (E03 closing,
   Ruling 9 — the fps-ordering law).
4. Build the armature: named bones per the registered list, joint heads/tails placed to the
   mesh; parent with `ARMATURE_AUTO`.
5. Author the probe action: the **E03 arm arc** — one arm, 0→90°, 33 keys at 16 fps — the same
   authored ground truth E03 used, so E08 can compare wire-control against character-control on
   a known arc. Additional probe poses at the executor's discretion, each recorded.
6. Export rigged GLB + manifest (sha256 of source, of output, site→bone map, tool version).
7. Render the deformation sheet (below) via `stage_render.py` — **PowerShell, headless, local**.

## Gates — all raise inside `rig_character.py`; none can be skipped from a shell

- **Gate N — names.** Export raises unless every registered site maps to exactly one bone with
  exactly that name. The invariant unbounded elsewhere: nothing else prevents a half-named rig
  from shipping.
- **Gate P — rest-pose fidelity.** With the armature modifier live and no pose applied, max
  vertex displacement against the source mesh ≤ **1e-4 × the mesh's own bbox diagonal**
  (bounded by the structure's own size, per the global-constant law; linear-blend skinning at
  bind pose with normalized weights should be identity, so this is tight by design). Raises on
  breach.
- **Gate D — determinism.** A second run from the same inputs reproduces bone heads, tails,
  parents and weights within float tolerance — compared as **parsed objects, never bytes**
  (bytes-are-not-content law). Raises on mismatch.
- **A fired gate halts the session and is reported with its evidence.** Never re-parameterize
  past one.

**Deformation under pose is deliberately NOT a gate.** Per-bone vertex-displacement stats are
reported **per structure** as diagnostics; whether the deform is acceptable — whether he still
looks like *him* when his arm is up — is the Director's, on the sheet, at his zoom. No metric
here approximates it.

## Predictions

Registered by the executor **before step 4**, blind status disclosed, **each clause
separately**: (P1) does `ARMATURE_AUTO` produce a usable deform on this mesh — usable meaning
the Director does not reject the sheet outright; (P2) does any site fail to map cleanly to the
mesh's actual topology; (P3) does Gate P hold at the stated epsilon on the first export.
A miss with its mechanism is worth more than a hit.

## The sheet — first artifact under the dailies standard (audit §5.6)

`rest pose | posed frames of the arc | insets` — **uniform panel scale, the deforming regions
(shoulder, elbow, hand, hip) inset-zoomed at 1:1, labels readable at review distance, no
internal gate states printed on it.** Rendered from the character with material and light, not
a schematic: the sheet's job is to let his eye rule on deformation in one look. Sheets locate;
full size decides.

## Out of scope

Finger and face bones; weapon bones; a retargeting library; **any generation** (zero credits —
E08's job); any write into `E:\AI\facet` or `E:\AI\training` (sources are read-only; the rigged
GLB and everything else land in armature's tree, big binaries gitignored with sha256 manifests
committed); any promotion of rigging upstream into facet's pipeline (a later Director call,
foreclosed by nothing here).

## Licence rows introduced

None. Blender 5.2.0 LTS is already mapped (`docs/license-map.md`, Services and tools — fetched
from the installed build's own licence documents). No model, weight, or preprocessor enters.

## Report

Predictions with blind status first; premises re-verified with what moved; the source-choice
record; gates with verdicts (a gate that has not run is written **NOT YET RUN**); per-structure
deformation diagnostics; the sheet; manifest hashes. **No judgement words.** The Director
decides whether the skeleton is fit to perform.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | Source pinned by sha256; tool + spec versioned; output manifest carries the site→bone map and hashes. Not 3: no byte-replay of Blender internals is claimed, and the manifest says so |
| ANDON_AUTHORITY | **3** | Gates N/P/D raise inside the exporting tool, no skip flag; the watchdog precondition guards the GPU step |
| NAMED_COMPENSATORS | **3** | Nothing irreversible: zero credits, all outputs new files under `outputs/E07/` (`rm -r` undoes), sources opened read-only |
| DECOMPOSE_BY_SECRETS | **2** | Rigging, rendering, and measurement are separate tools; the site list is data, not code |
| UNCERTAINTY_GATED_HUMANS | **3** | The one question that matters — is the deform acceptable — goes to the Director on a sheet built for the judgment; diagnostics gate nothing |
| EXTERNAL_VERIFIER | **1** | Standing pipeline weakness, named not inflated: advisor ruling + Director's eye, a different kind of check rather than a different model family |

**14 / 18.** Sub-3 scores carry their reasons above rather than remediation theater; the two 2s
are honest ceilings for a local build experiment.
