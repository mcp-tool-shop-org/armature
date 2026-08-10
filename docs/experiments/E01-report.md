# E01 — report

**Seat:** executor · **Spec:** [E01-control-sequence-exporter.md](E01-control-sequence-exporter.md)
· **Credits spent: 0** (nothing was submitted to any provider) · **Advisor rules after the
Director has seen this.**

This report states measurements. It does not decide what they mean.

---

## 1. Registered predictions

**Registered 2026-08-10, before any code was written, before any subject GLB was opened, and
before any render ran.** The only facts in hand at registration time were the environment
presence checks in §2 — tool versions and the byte sizes of the four subject files. Nothing had
been imported, rendered or measured.

Per CLAUDE.md, each prediction first states **what one of the counted thing is**, then the
number. Conjunctions are predicted clause by clause before the join.

> **The blindness claim has third-party corroboration, which is better than my word for it.**
> A parallel S01 advisor session swept this file into commit `fc2f2c2` with `git add -A` while
> I was still writing — an error it recorded against itself in `6fb9925`. The useful side
> effect is a timestamp neither seat controls: **the predictions below entered git at
> 15:14:22**, byte-identical to what is here now, and **my first measurement of anything —
> `outputs/E01/p2/p2_armatures.json` — was written at 15:32:49**, eighteen minutes later. The
> first render (`runA`) landed at 15:34:49. No prediction below was edited after any
> measurement; `git show fc2f2c2:docs/experiments/E01-report.md` is the check.

### P1 — channels producible with no ML estimator

> *Spec:* Of the 5 channels, how many can be produced with **no ML estimator** in the pipeline?
> (Unit: a channel emitted by the shipped tool for the E01 subject, not a channel Blender could
> theoretically produce.)

**One of the counted thing is:** one named channel that `tools/stage_render.py` actually writes
as a per-frame image sequence into the E01 run directory for the **primary** subject
(`longsword_hero.glb`), in a process that loads no ML model weights of any kind.

**Blind: YES** — no GLB had been opened, no channel had been rendered.

| clause | prediction |
|---|---|
| channels emitted for the primary subject | **4** — `depth`, `normal`, `mask`, `edge` |
| channels *not* emitted, and why | **1** — `pose`, because the primary carries no armature |
| channels that would **require** an ML estimator | **0** |

Reasoning recorded at registration: Z-buffer, normal pass and alpha are direct renderer outputs;
`edge` I intend to derive arithmetically from depth+normal rather than from Canny or a learned
edge model, so it needs no estimator either. `pose` needs an armature, not an estimator — so I
predict the count lands at 4 for a reason that has nothing to do with the license gate. **If any
channel turns out to need an estimator, the spec says that is a finding, not a dependency.**

### P2 — GLBs carrying a usable armature

> *Spec:* Of the GLBs at the paths in §Subject, how many carry an armature that **loads in
> Blender with bones posable and named**? (Unit: a file, not a character.) Note the conjunction:
> *loads* ∧ *has bones* ∧ *bones are usable*.

**One of the counted thing is:** one `.glb` **file** at one of the four §Subject paths (not one
character — `blackguard_rigged.glb` and `blackguard_unirig_rigged.glb` are two files and, if both
are blackguard, one character), which after `bpy.ops.import_scene.gltf()` yields at least one
object of type `ARMATURE` that has ≥1 bone, whose pose bones carry non-empty names and accept a
rotation assignment.

**Blind: YES** — no GLB had been opened.

Denominator: **4 files.** Clauses predicted separately, then joined:

| clause | what it means | prediction |
|---|---|---|
| **A · loads** | `import_scene.gltf` returns without raising | **4 / 4** |
| **B · has bones** | ≥1 `ARMATURE` object with ≥1 bone exists after import | **3 / 4** — three filenames say `_rigged`; `longsword_hero.glb` does not |
| **C · bones usable** | pose bones exist, names non-empty, a rotation can be assigned | **3 / 3** of those with bones |
| **JOIN (P2)** | A ∧ B ∧ C | **3 / 4** |

**The unit trap I am deliberately stepping around:** the studio's standing verdict is that
*rigging was abandoned in June 2026 because UniRig shreds faced characters.* That verdict is
about **rig quality**, which is a different counted thing from **mechanical loadability**. C as
the spec words it ("posable and named") is mechanical, so the June verdict does not lower my
prediction for C. I therefore also register the stricter, downstream-relevant measurement as a
separate number, so the two are never conflated:

| extra measurement | one of the counted thing is | prediction |
|---|---|---|
| **P2b — COCO-18-mappable rigs** | one file whose bone **names** map onto the 18 OpenPose keypoints under a standard humanoid naming convention (Mixamo / Rigify / glTF-standard), with no hand-authored per-file map | **1 / 4** |

P2b is the number the `pose` channel actually depends on; P2 is not.

### P3 — per-frame vs per-shot depth normalization on static geometry

> *Spec:* over an orbit, what is the mean absolute per-pixel depth difference on **static
> geometry** between per-frame and per-shot normalization? Report both; do not choose.

**One of the counted thing is:** one **pixel of one frame** of the depth channel, drawn from the
set of pixels where the mask is 1 (geometry present — background is excluded because it carries
no depth), measured in normalized depth units on [0, 1] where 1 = nearest. The reported statistic
is the mean of |d_per-frame − d_per-shot| over all such pixels across all frames of the shot.

The subject is world-static; only the camera moves. Every mask pixel is therefore static
geometry.

**Blind: YES** — no render had been made and no depth range had been measured.

| clause | prediction |
|---|---|
| **P3a · mean \|Δ\|** | **0.12** normalized units ≈ **31 / 255** 8-bit levels |
| **P3b · worst frame's mean \|Δ\|** | **0.30** normalized units ≈ **77 / 255** levels |
| **P3c · range swing** | the per-frame depth range (z_max − z_min) at its widest is **≥ 1.5×** its narrowest across the orbit |
| **P3d · the sign, per pixel** | per-shot normalization **compresses** the subject: near surfaces come out **darker** and far surfaces **lighter** than under per-frame, with a crossover in between |

Reasoning recorded at registration. Writing d_pf = (z_maxᶠ − z)/wᶠ and d_ps = (Z_MAX − z)/W with
wᶠ ≤ W, substitution gives **d_ps = cᶠ + (wᶠ/W)·d_pf** with cᶠ = (Z_MAX − z_maxᶠ)/W ≥ 0. So the
per-shot image is an affine compression of the per-frame image — which forces P3d — and for d_pf
spread over [0,1] the mean absolute difference is ≈ ½·(1 − wᶠ/W) when cᶠ is small. P3a's 0.12 is
that expression at wᶠ/W ≈ 0.75, discounted because a character's depth histogram is concentrated
in the torso rather than spread uniformly across its range.

---

*(Everything below this line was produced after the predictions above were registered.)*

## 2. Environment, as measured

| | |
|---|---|
| Blender | 5.2.0 LTS, build `fbe6228777e7`, 2026-07-14, bundled Python 3.13.13 / numpy 2.3.4 |
| test python | `E:\AI-Models\trellis2-env` — 3.13.13, numpy 2.4.6, Pillow 12.2.0, pytest 9.1.1 |
| VRAM watchdog | alive at session start, restarted to a fresh heartbeat; kill@ 31200 MiB / RAM 90% / 87 °C |
| GPU work | Blender EEVEE renders only. No model weights of any kind were loaded in any process. |
| **credits spent** | **0.** Nothing was submitted to any provider; no cloud tool was called. |
| writes to `E:\AI\training` | **none.** The only files modified there in the session window are the watchdog's own `_watchdog_HEARTBEAT` and `_watchdog_log.csv`, which the watchdog writes. Every subject was opened read-only. |

## 3. Predictions beside measurements

### P1 — 4 of 5. Registered 4. **Hit.**

`stage_render.py` emitted **`depth`, `normal`, `mask`, `edge`** for the primary subject, and
**zero channels required an ML estimator**. Both clauses landed where they were registered.

The registered *reason* — "`pose` is absent because the primary carries no armature" — also holds,
but it turned out to be the weaker of two independent blocks, and the second one is not about this
subject at all:

1. the primary carries no armature (§4 measures this);
2. **`pose` is refused for every subject**, including the one that does have an armature.
   `openpose.require_drawing_convention()` raises because F20 records limbSeq and the keypoint
   count but **not** the 18-colour palette or the keypoint order, and this tool does not write a
   convention from memory. That is a decision made during this session, so P1's 4 is partly a
   measurement of a choice — but only for the *other* subjects. For the primary as registered, 4
   is forced by the asset regardless of that choice.

**No estimator entered the pipeline.** Depth is Blender's Z pass, normal is its Normal pass
rotated into camera space, mask is the alpha pass, and edge is arithmetic over the first two. The
banned tier in `docs/license-map.md` (OpenPose CMU non-commercial; Depth Anything V2-Large /
V3 weights CC-BY-NC) is absent by construction rather than by substitution.

### P2 — 2 of 4. Registered 3 of 4. **Miss**, and the miss is in one named clause.

Measured by `tools/probe_glb.py` → `outputs/E01/p2/p2_armatures.json`.

| clause | registered | measured | |
|---|---|---|---|
| **A · loads** | 4 / 4 | **4 / 4** | hit |
| **B · has bones** | 3 / 4 | **2 / 4** | **miss** |
| **C · posable and named** | 3 / 3 with bones | **2 / 2 with bones** | hit as a ratio; the denominator moved under it |
| **JOIN (P2)** | 3 / 4 | **2 / 4** | **miss, entirely via B** |
| **P2b · all 18 sites named** | 1 / 4 | **0 / 4** | **miss** |

| file | loads | ARMATURE | bones | posable+named | anatomical sites named |
|---|---|---|---|---|---|
| `longsword_hero.glb` | yes | 0 | 0 | — | 0 / 18 |
| `blackguard_rigged.glb` | yes | **0** | 0 | — | 0 / 18 |
| `blackguard_unirig_rigged.glb` | yes | 1 | 28 | yes | **0 / 18** |
| `swordsman_apose1_trellis_rigged.glb` | yes | 1 | 52 | yes | **0 / 18** |

**Why B missed, exactly.** My reasoning was "three filenames say `_rigged`". One of them does not
carry a glTF skin: `blackguard_rigged.glb` imports as **30 `EMPTY` objects named `bone_0`…`bone_29`**
plus 2 meshes and **no `ARMATURE`**. Its skeleton is a node hierarchy of transforms, not a skin, so
Blender has nothing to build an armature from. The filename was the evidence and the filename was
a hypothesis wearing a fact's clothes.

**Why P2b missed, and it is not a near miss.** Both files that do carry an armature name their
bones `bone_0 … bone_N`. **Zero** of the 18 anatomical sites are identifiable by name in **any** of
the four files — not 1/4 as registered, and not "some sites in some files": the matcher found
nothing anywhere. A COCO-18 map would have to be authored by hand per file, and even then the
keypoint *order* is not in the retrieved record (§ P1 clause 2).

**Premise 3 of the spec — "some of those GLBs carry a usable armature", marked ASSUMED — now reads
2 of 4 files, on the mechanical sense of "usable".** The studio's June 2026 verdict about rig
quality was deliberately kept out of this count and is untouched by it.

### P3 — reported for two subjects, and **not chosen between**.

**Both normalizations are emitted side by side** as `depth_perframe/` and `depth_pershot/`. There
is no `depth/` directory: naming one would be choosing, and the choice is the Director's.

| | registered | **sword** (`longsword_hero`) | **character** (`blackguard_unirig`) |
|---|---|---|---|
| **P3a · mean \|Δ\| on geometry** | 0.12 (31/255) | **0.0604 (15.39/255)** | **0.0849 (21.66/255)** |
| **P3b · worst frame's mean** | 0.30 (77/255) | **0.0920 (23.47/255)** — frame 6 | **0.1876 (47.84/255)** — frame 8 |
| max \|Δ\| at any single pixel | — | 0.229 (58/255) | 0.262 (67/255) |
| quietest frame's mean | — | 0.0047 (1.19/255) — frame 18 | 0.0074 (1.88/255) — frame 19 |
| **P3c · z-range swing** | ≥ 1.5× | **1.396×** | **1.786×** |
| shot depth window | — | 2.324 → 2.548 (0.224) | 2.402 → 2.990 (0.588) |
| per-frame window range | — | 0.157 → 0.220 | 0.322 → 0.575 |

**P3a: miss, over-predicted on both** — by 2.0× on the sword and 1.4× on the character.
**P3b: miss, over-predicted on both** — by 3.3× and 1.6×.
**P3c: split** — missed on the sword (1.396 against a registered ≥1.5), hit on the character (1.786).
The registered threshold was a single number applied to a subject population I had not looked at,
and the two subjects fall either side of it.

**P3d — the direction. Half right, and the wrong half is the informative one.**

| | sword | character |
|---|---|---|
| pixels **darker** under per-shot | 76.0 % | 66.6 % |
| pixels **lighter** under per-shot | 20.9 % | 30.7 % |
| pixels identical | 3.1 % | 2.8 % |
| frames where the **near half** is darker | **27 / 33** | **26 / 33** |
| frames where the **far half** is lighter | **8 / 33** | **14 / 33** |
| crossover, in per-frame depth level | **56 / 255** | **112 / 255** |

*Near surfaces darker under per-shot normalization* is what the frames show — 27/33 and 26/33.
*Far surfaces lighter* is *not* generally what they show: on most frames the far half is darker
too. The crossover exists, but it sits at level 56 (sword) and 112 (character) rather than near
the middle, so on a typical frame **most of the subject darkens and only the darkest fifth to
third lightens**. On the worst frame of each run the far half is still negative
(−8.69 and −37.41 levels). The affine algebra in §1 permits this — cᶠ can be small enough that the
crossover sits below the median — but I registered the symmetric picture and the measurement is
asymmetric.

**A caveat on P3's magnitude that the numbers cannot carry by themselves.** The spec's named
primary is a **weapon prop, not a figure** (§5). A blade's depth histogram is not a body's, and
the two subjects here differ by 1.4× on P3a in the direction you would expect from that. The
character number is the one that generalizes to armature's actual unit of work; the sword number
is reported because it is the subject the spec named.

**The difference image** is emitted per frame at `p3_diff/`, in the same 8-bit space that ships,
with no amplification — so a dark tile means a small difference rather than a hidden one. Per-frame
mean and max are printed on each tile of the sheets, and the full per-pixel record is in
`p3_normalization.json` and `p3_sign_*.json`.

## 4. Gates

| gate | verdict | evidence |
|---|---|---|
| **G1 · generator legality** | **PASS** on both anchors | 512×768 (both /16), 33 frames (4·8+1), profile `wan-vace` from F24. Raised red on demand in 9 subprocess cases — see §6. |
| **G2 · completeness** | **PASS** on both anchors | 6 channel directories × 33 frames, no zero-length file. Fired red in test when one frame was dropped mid-run, with `manifest.json` absent afterwards. |
| **G3 · reproducibility (pixels)** | **max per-pixel difference 0, mean 0, across all 6 channels × 33 frames**, on two independent process pairs | `outputs/E01/g3_compare.json`, `g3_compare_postfix.json`. Byte hashes also matched on every file — reported separately from the pixel result on purpose, because those are different claims. |
| **G4 · bbox sanity** | **FIRED** on the character arm, then **PASS** at max delta **1 px** (tolerance 2) on both anchors after the defect it found was fixed | §5. |
| **G5 · OpenPose conformance** | **NOT RUN** — `pose` was not emitted | The limbSeq fixture is pinned against F20 in `tests/test_openpose_convention.py` and cross-checked against `docs/research-grounding.md` itself, but G5 proper never executed because no skeleton was drawn. |

## 5. G4 fired. What it caught, and what I did next

**This is the part of the report the advisor should read first.**

Running the anchor on the character subject halted at frame 0:

```
GATE_FAILURE G4 [G4] frame 0: mask bbox (222, 275, 289, 497) disagrees with the
projected mesh bbox (39, 163, 472, 592) by [183, 112, 183, 95] px (tolerance 2 px)
```

I did not change a parameter and re-run. I diagnosed it read-only, and the diagnosis is that
**the exporter was wrong, not the asset**:

Blender's own glTF importer creates a collection named **`glTF_not_exported`** with
`hide_render=True`, and drops a 42-vertex **`Icosphere` of world radius 1.0** into it. My
geometry selection was `type == "MESH"`, which swept the decoy up. Two consequences, both real:

1. **G4's expected bbox** covered the decoy, which the render correctly omits — hence the firing.
2. **The auto camera radius** fitted a bounding sphere inflated by the decoy, so the subject would
   have been framed too small. That one is silent; nothing else would have caught it.

The fix (`blender_scene.render_visible_meshes`) selects on render visibility: object `hide_render`,
plus `hide_render` or `exclude` anywhere up the layer-collection ancestry. It deliberately does
**not** use `visible_get()`, which reports *viewport* visibility — a collection can be hidden in
render and visible in the viewport, and a predicate built on `visible_get()` would let that case
through. `tests/test_render_visibility.py` pins all three cases plus the negative control that the
naive filter would have returned 4 meshes instead of 1.

**Two things about the re-run, stated so the advisor can rule on them rather than discover them.**

- What changed is a **defect in the instrument**, not a parameter, and not the gate's tolerance.
  G4 is exactly as strict as it was. But the character arm's numbers in §3 come from a run made
  **after** that fix, and the advisor may rule that arm inadmissible for E01.
- The fix could have moved the primary too, so I measured rather than assumed: **run A (pre-fix)
  vs run D (post-fix) differ by 0 pixels and 0 bytes** across all six channels
  (`prefix_vs_postfix_primary.json`). The primary subject has one mesh and no decoy, so the filter
  was a no-op there. Every P3 number quoted for the sword is unaffected by the fix.

The halted run is left in place at `outputs/E01/runC_blackguard/` — it has a `.armature_run`
marker, partial channel directories and **no manifest**, which is what a halted export is supposed
to look like.

## 6. What else the session falsified or found

Recorded because each one cost minutes here and would have cost a session later.

**The spec's named primary is not a character.** `longsword_hero.glb` is a *hero longsword* — a
weapon prop from facet's `E14_strokes` run, 795,958 vertices, bbox half-extent
`[0.113, 0.032, 0.501]`. The spec calls it "a facet-finished asset, the natural primary (armature
is downstream of facet)", which reads as a character for a character-staging tool. It is not one.
This explains its zero-armature result without any appeal to rigging policy, and it is why §3
reports P3 on a second, character subject as well.

**Four Blender 5.2 API claims that would have been inherited wrong.** Each was probed before being
built on:

| inherited shape | Blender 5.2 |
|---|---|
| `scene.node_tree`, `scene.use_nodes` | `node_tree` **does not exist**; the compositor is a node group on `scene.compositing_node_group`, and `use_nodes` is deprecated for removal in 6.0 |
| `CompositorNodeOutputFile.base_path` / `.file_slots` | `directory` / `file_name` / `file_output_items` |
| `format.file_format = 'OPEN_EXR'` | rejected until `format.media_type` is set to `'IMAGE'`; the node defaults to `MULTI_LAYER_IMAGE`, whose format enum has exactly one member |
| `file_output_items.new('COLOR', …)` | socket types are `FLOAT` / `VECTOR` / `RGBA` / …; `COLOR` is not one |
| the engine enum | `RenderSettings.bl_rna` lists only `BLENDER_EEVEE` — but `CYCLES` **assigns fine**; the static enum is not the live one |

**The File Output node does not append a frame number.** Every frame would have overwritten the
last under a naive setup. The tool sets `file_name` per frame itself.

**`is` on a bpy datablock is always False.** My own compositor link-topology check fired spuriously
because bpy returns a fresh Python proxy per attribute access. Caught by the Blender-side test on
first run; the check now compares names, and also checks the *source socket* per output.

**Measured, not assumed, about the render:** Blender's Z pass is **perpendicular camera-space
depth** (a plane parallel to the image plane reads one constant value across the whole frame — 2.0
and 5.0 exactly on the two-plane fixture), unhit pixels read **1e10**, and at `filter_size = 0.01`
the alpha pass is **exactly binary** — `alpha_soft_fraction` is 0.0 on the synthetic run and is
recorded per frame in every manifest.

**A defect in `run_export` that the tests caught before any render did:** it assumed a normalised
spec and raised `KeyError` from the middle of the render loop on a raw one. It now fills defaults
first — the only step that precedes G1, and it touches no filesystem.

**Two seats were live in this working tree at once.** The S01 advisor session's `git add -A`
swept this report into `fc2f2c2` mid-write, and recorded the error against itself in `6fb9925`.
Nothing was lost — main's copy is byte-identical to §1 as it stands — and the accident produced
the timestamp evidence quoted at the top of §1. Noted here from the executor side because the
collision is a property of the *tree*, not of either seat: this branch is based on `8666d9b`,
which already contains that snapshot, so the report's history reads continuously rather than as
two competing files.

## 7. Conventions this exporter fixes, and what backs each

| convention | value | backing |
|---|---|---|
| depth direction | inverse relative, **near = bright** | F19 |
| depth normalization | **both** per-frame and per-shot, emitted separately | F19 says per-frame; P3 is the open question, so neither is privileged |
| depth background | 0 (black = far); normalization statistics computed over mask pixels only | **this exporter's own convention** — not retrieved. Background has no depth, and letting 1e10 clip to "nearest" would render a wall against the lens |
| lossless master | the 32-bit float EXR Z/normal/alpha passes, retained under `master/` | spec: deriving down is free, deriving up is impossible |
| normal space | camera-space, +X right / +Y up / +Z toward viewer, encoded `n*0.5+0.5`; background black | F1's channel. A camera-facing surface encodes exactly (128,128,255), checked on a real render with a non-axis-aligned camera |
| mask | 1-bit PNG, exact silhouette | spec |
| edge | relative depth break (2 % of **local** depth) ∪ normal break (30°) ∪ silhouette; near-binary | F22. The depth term is a fraction of local depth and the normal term is an angle, so no global constant governs a local feature |
| frame legality | /16 dims, 4n+1 frames, from a **named profile pinned in code** | F24. A spec-supplied divisor would be a skip flag wearing a schema's clothes |
| pose | **not emitted** | F20's palette and keypoint order are not in the retrieved record |

## 8. Deliverables

```
tools/stage_render.py          the exporter; G1/G2/G4 raise inside it, G5 called when pose is emitted
tools/armature_core/           gates · shotspec · channels · pngio · openpose · blender_scene · errors
tools/probe_glb.py             P2's instrument
tools/compare_runs.py          G3's instrument — decodes pixels, reports bytes separately
tools/analyze_p3.py            P3's sign and crossover, in the 8-bit space that ships
tools/make_sheet.py            the control|provenance sheet
specs/E01-anchor.json          the primary shot spec, asset sha256 pinned
specs/E01-anchor-blackguard.json   the character arm; only the subject differs
tests/                         103 tests, all passing
```

**103 tests pass** (`pytest tests -q`), across three groups:

- **pure python** — gates, spec contract, channel maths, PNG writer (read back with Pillow, a
  different implementation), the F20 fixture;
- **the real write path with a synthetic backend** — G1 red before the backend is touched and
  before the output directory exists; G2 red with the manifest absent; G4 red on a lying mask;
  the compensator refusing a directory it did not create;
- **headless Blender** — depth direction, vertical orientation, camera-space normals, exact binary
  mask, G4 agreement, intra-run frame determinism, and the render-visibility regression.

**G1 under optimization**, the test the spec asks for by name: 9 subprocess cases (3 failure modes
× plain / `-O` / `PYTHONOPTIMIZE=1`) each raise `G1GeneratorLegality`, each leave no output
directory behind, and a tenth case checks that `-O` actually took effect (`__debug__` False,
`sys.flags.optimize` ≥ 1) — because a green result from an optimization that never applied would
be a check that cannot fail.

**Compensator, per the spec's NAMED_COMPENSATORS row:** `stage_render.delete_output_dir(run_dir)`,
owner = the executor session that made the run. It refuses any directory without the
`.armature_run` marker this tool writes.

## 9. Artifacts for the Director

Sheets — **control channels beside their provenance**, every tile at native 512×768 with no
resampling:

- `outputs/E01/sheets/E01-anchor-sheet.png` — the sword, frames 0/6/12/20/28 × 6 channels
- `outputs/E01/sheets/E01-blackguard-sheet.png` — the character, frames 0/8/16/24 × 6 channels

Each sheet's header carries the asset sha256, resolution, frame count, generator profile, engine,
Blender version, every gate verdict, and P3's headline numbers. Per-tile labels on `p3_diff` carry
that frame's mean and max.

**Sheets locate; full size decides.** The runs are at `outputs/E01/runD` (sword) and
`outputs/E01/runF_blackguard` (character); `master/` in each holds the lossless EXRs.

## 10. Open, and not closed by this session

- **The normalization choice.** P3 reports both. Reported, not chosen.
- **F20's palette and keypoint order** are unretrieved, so no skeleton can be drawn to the
  convention. G5 cannot run until they are filed.
- **No file on this rig has COCO-mappable bone names** — 0/18 sites in all four. Any pose channel
  needs a hand-authored per-file map *and* the missing convention.
- **Whether a Z-buffer render substitutes acceptably for an estimator's depth** is premise 7,
  still ASSUMED. E01 renders it; E02 tests it.
- **G4's tolerance is 2 px and both anchors ran at max delta 1 px.** That is one pixel of headroom.
  A subject with alpha-blended materials or an off-frustum limb may sit differently against it, and
  nothing here measures that.
- **Both anchors are 33 frames at 512×768 with one camera move.** Nothing here says how the
  exporter behaves at other resolutions, other frame counts, or with an animated subject.
