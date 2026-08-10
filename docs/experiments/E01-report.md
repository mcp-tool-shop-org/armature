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
