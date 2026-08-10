# E01 — the control-sequence exporter

**Seat:** executor · **Spec written:** 2026-08-10, before any code · **Advisor:** rules after the
report · **Credit ceiling: ZERO** — E01 spends no cloud credits and submits nothing.

Grounding: [research-grounding.md](../research-grounding.md), cited by finding number.
Method: [CLAUDE.md](../../CLAUDE.md). Arc: [ROADMAP.md](../ROADMAP.md).

---

## The question

Given a GLB and a shot specification, can headless Blender emit per-frame **control channels**
that are reproducible, generator-legal, and correct against the published conventions — with
**no ML estimator anywhere in the pipeline**?

E01 builds the foundation everything downstream consumes. It generates nothing. If the exporter
is wrong, every later experiment is measuring the exporter.

## Why these channels

F1 (Champ, arXiv:2403.14781 — **the one claim confirmed by two independent non-Claude
verifiers**) measured dense 3D-parametric guidance against 2D skeleton-only: FVD 192.34 → 170.20,
SSIM 0.672 → 0.773. Dropping the skeleton *entirely* still beat skeleton-only on FVD. F21 notes
the same work renders those maps from a 3D body with no 2D detector — the closest published
precedent to this exporter's exact move.

So the channel set is **depth + normal + semantic/mask first, skeleton last and optional**. This
is not a preference; it is the ordering the measurement implies.

## Premises — marked, per CLAUDE.md

| # | Premise | Status |
|---|---|---|
| 1 | Blender 5.2 is present at the recorded path and runs headless | **MEASURED** (facet ran 12 headless invocations) |
| 2 | GLB character assets exist on this rig | **MEASURED** — enumerated 2026-08-10; 15+ found under `E:\AI\training` |
| 3 | Some of those GLBs carry a usable armature | **ASSUMED** — filenames say `_rigged`, contents unverified. **P2 measures it.** |
| 4 | ControlNet-family depth is near-bright, per-frame normalized, 8-bit | **RETRIEVED** (F19) — from a model card, not tested here |
| 5 | OpenPose-18 uses a 19-pair 1-indexed `limbSeq` | **VERIFIED AT SOURCE** (F20) — `util.py` fetched and read at ruling time |
| 6 | Wan/VACE needs dims /16 and frame count 4n+1 | **RETRIEVED** (F24) — from ComfyUI docs, not tested here |
| 7 | Rendering depth from the Z-buffer avoids every banned preprocessor | **ASSUMED** — the license map (F: lane 5) shows the estimators are banned; that a Z-buffer render substitutes acceptably is what E02 tests, not E01 |

Premise 3 is the one most likely to be wrong, and the studio's standing verdict makes it
suspicious: **rigging was abandoned in June 2026 because UniRig shreds faced characters.** If no
usable armature exists, E01 still delivers four channels and armature v1 is camera-motion over a
posed-but-static mesh — which F1 says is the stronger signal anyway.

## Deliverable

`tools/stage_render.py` — consumes a **shot spec** (JSON) plus a GLB, writes a directory of
per-frame channel sequences and a manifest. Plus `tests/` covering it, in the same commit.

The shot spec is E01's other deliverable and it is a **contract**: it must capture everything
needed to reproduce a shot — asset path + sha256, camera path, frame count and rate, resolution,
channels requested, and Blender version. A run that cannot be reproduced from its spec is a
failed run.

### Channels

| Channel | Source | Format |
|---|---|---|
| `depth` | Z-buffer | inverse relative, near = bright (F19); 8-bit PNG for consumers **and** a 16-bit or EXR master retained |
| `normal` | camera-space normals | 8-bit RGB (F1's channel) |
| `mask` | alpha / object index | 1-bit exact silhouette |
| `edge` | geometric discontinuity (Freestyle or normal/depth break) | 8-bit, near-binary (F22) |
| `pose` | armature bone projection → OpenPose-18 | **only if premise 3 holds** (F20 convention, exactly) |

**Retain the lossless master even though F19 says consumers cap at 8-bit.** The 8-bit export is
what ships to a model; the master is what lets a later experiment re-derive a different
normalization without re-rendering. Deriving down is free; deriving up is impossible.

## Predictions — register these BEFORE running anything, and state whether each was blind

The executor writes predictions into the report *first*. Per CLAUDE.md, a hypothesis with no
prediction cannot be wrong, and one that cannot be wrong teaches nothing. **facet missed nine
consecutive arcs on the unit/population family — so for each prediction, write what one of the
counted thing *is* before writing the number.**

- **P1** — Of the 5 channels, how many can be produced with **no ML estimator** in the pipeline?
  (Unit: a channel emitted by the shipped tool for the E01 subject, not a channel Blender could
  theoretically produce.)
- **P2** — Of the GLBs at the paths in §Subject, how many carry an armature that **loads in
  Blender with bones posable and named**? (Unit: a file, not a character — several files may be
  the same character.) Note the conjunction: *loads* ∧ *has bones* ∧ *bones are usable*. Predict
  each clause, then the join.
- **P3** — **The open design question, and E01's most interesting measurement.** F19 says
  ControlNet depth is *per-frame min-max normalized*. But per-frame normalization on a **moving
  camera** re-maps the depth range every frame — the same surface changes brightness as the scene
  depth range changes. Predict: over an orbit, what is the mean absolute per-pixel depth
  difference on **static geometry** between per-frame and per-shot normalization? Report both;
  **do not choose between them.** The choice is E02's, with the Director's eye on the result.

## Gates

Gates **raise inside the tool that performs the write** — no shell chaining, no bare `assert`
(deletable by `-O`), no skip flag. Per CLAUDE.md, put the andon on the direction the invariant
does not bound.

- **G1 · ANDON — generator legality.** Width and height divisible by 16; frame count ≡ 1 (mod 4)
  (F24). Raises before any frame is written. This failure is *quiet* — facet lost a whole
  experiment's pairing to a width that decoded 2 px short — so it is checked at write time, not
  at review time.
- **G2 · ANDON — completeness.** Every requested channel has exactly the declared frame count,
  and no frame file is zero-length. A partial export must never look like a finished one.
- **G3 · Reproducibility — compare PIXELS, not bytes.** Run the same spec twice from fresh
  processes; report per-channel **max and mean per-pixel difference**. A PNG byte-hash mismatch
  is *not* evidence a render changed (facet false-halted on this twice). Report the number; do
  not halt on nonzero without inspecting where it lives.
- **G4 · Bbox sanity — test the failure mode.** The mask's bounding box must agree with the
  mesh's projected bounding box within a stated tolerance. This is the check that catches a
  channel silently rendering the wrong thing; facet's version caught a mask 751 px wide in a
  752 px frame when the mesh was 388.
- **G5 · Convention conformance (only if `pose` is emitted).** Keypoint count is exactly 18 and
  the limb-pair list matches F20's fetched `limbSeq` **element for element, including its
  1-indexing**. Assert against the retrieved reference, not against memory.

**If a gate fires: report it with its evidence and halt.** Do not change a parameter and re-run.

## Tests (ride this commit — not a later one)

Naming them here because a dispatch that plans a tool change without naming its tests is missing
a step:

1. **G1 goes red** — a spec with width 1020 (not /16) and one with 80 frames (not 4n+1) each
   raise. *Prove the gate fires*; a gate that cannot fail is not a gate.
2. **G1 survives `-O`** — the same case under `python -O` and `PYTHONOPTIMIZE=1` still raises.
   87 of facet's ANDONs were removable by an environment variable; do not add the 88th.
3. **G2 goes red** on a truncated output directory.
4. **Depth direction** — a synthetic two-plane scene where the near plane is *known* nearer:
   assert the near plane is brighter. This is the test that would catch an inverted depth ramp,
   which is invisible by eye on a complex mesh and fatal downstream.
5. **limbSeq fixture** — pinned against the F20 values, so a future edit to the skeleton renderer
   fails loudly rather than drifting.
6. **Shot-spec round trip** — spec → render → re-render from the spec alone reproduces (per G3's
   pixel comparison).

Use synthetic scenes for 1–4 where possible: an instrument that lives inside its own population
must not be tested with fixtures that move the thing being measured.

## Subject

Enumerated on this rig 2026-08-10. Use **one primary** and keep the others for P2's count:

- `E:\AI\training\facet_next\E14_strokes\run\final\longsword_hero.glb` — a facet-finished asset,
  the natural primary (armature is downstream of facet).
- `E:\AI\training\_p0_packs_modernize\_mesh_line\blackguard\blackguard_rigged.glb` and
  `blackguard_unirig_rigged.glb` — the rigging candidates for P2.
- `E:\AI\training\_p0_packs_modernize\_mesh_line\swordsman\swordsman_apose1_trellis_rigged.glb`.

**These are read-only.** Never write into `E:\AI\training`; it is not in git and has no revert.

## Out of scope

Named explicitly so the session ends where it should:

- **All generation.** No cloud submission, no credits, no ComfyUI. E02 does that.
- **Animation authoring.** E01 renders an existing pose or an existing animation; it does not
  create performance.
- **Identity, references, prompts** — Phase E.
- **Multi-shot and assembly** — Phase F.
- **The MCP/CLI surface** — P01. A working script beats a polished interface here.
- **Choosing the normalization.** P3 reports both; the Director rules.

## License checks this experiment introduces

- **Blender** — the license map records the Foundation's GPL/output statement as **UNVERIFIED**
  (blender.org returned 403 to the fetcher). E01's executor retrieves it and files the row. Low
  risk, but the map does not carry assumptions.
- **No estimator enters.** If any channel turns out to need one, that is a **finding to report,
  not a dependency to add** — the banned tier (OpenPose, Depth Anything V2 Large / V3 weights) is
  exactly what this architecture exists to avoid.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | The shot spec + manifest pin asset sha256, camera path, resolution, frame count and Blender version; G3 re-runs from the spec alone. Not 3 until a test proves the replay is byte-stable in the fields that matter. |
| ANDON_AUTHORITY | **2** | G1/G2 raise inside the writing tool, with a test proving each goes red and survives `-O`. Not 3 until they have fired on a real defect. |
| NAMED_COMPENSATORS | **2** | E01's only world-touching act is writing a new output directory. **Compensator: `delete_output_dir`** — remove the run directory; owner: executor. Source assets are opened read-only and never modified, so there is nothing else to undo. No skip claimed. |
| DECOMPOSE_BY_SECRETS | **2** | Scene construction, per-channel rendering, and the spec/manifest schema are separate modules: channel formats change often, scene assembly rarely. |
| UNCERTAINTY_GATED_HUMANS | **2** | P3 is an explicit uncertainty-gated checkpoint — the executor reports both normalizations contrastively ("you may expect per-frame because the convention says so; here is what it costs on static geometry") and does not choose. |
| EXTERNAL_VERIFIER | **2** | The executor does not grade its own output; the advisor rules and the Director judges. G5 verifies against a **retrieved source file**, not model memory. Not 3 until a different-family check runs on an E01 artifact. |

**Total 12/18.** Every row is a 2 with a named path to 3; none is below 2, so no remediation item
is required. The 3s here would be earned by gates firing on real defects, which cannot be
manufactured in the spec.

## Report requirements

The report carries, in this order: the registered predictions with blind/not-blind stated; the
measured values beside them; every gate with a verdict (a gate that did not run is written
**NOT YET RUN**, never a plausible-looking result); P3's two normalizations reported separately
with a difference image; and the manifest of what was produced. **No judgment words** — the
Director decides whether the output is good.
