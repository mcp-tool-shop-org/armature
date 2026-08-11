# Comfy Agent consult #5 — rigging and skinning image-to-3D shell meshes for authored animation

**From:** the armature advisor seat, 2026-08-11 · **Relay:** the Director carries this brief to
the Comfy Agent and returns its answer · **Trigger:** both binding approaches failed at the
Director's eye — he ruled both binding approaches a hard failure

---

## Context — two paragraphs, then the measurements

armature is a previz-to-video pipeline: a character GLB is staged and animated in **headless
Blender 5.2**, the render becomes per-frame control sequences (depth / normal / edge / mask),
and those drive **Wan 2.1 VACE** video generation on Comfy Cloud. The character in hand is a
ball-jointed clay mannequin whose joints are sculpted ON the body; a 22-bone skeleton is
already built with every limb pivot measured onto its sculpted ball center (that part is
approved). What fails is the **binding** — attaching the mesh to the skeleton well enough that
an authored arm arc produces clean deformation in the control renders.

The mesh class matters more than this one mesh: it is a **TRELLIS-2 image-to-3D output**, and
every character on this studio's route will share the class — **hollow double-walled shell**
(~two voxels thick), **67 interior shells**, **non-manifold edges** (98 on the outer shell),
**glTF seam-splitting** (399k rendered vertices that weld to 149k), **one 4096 embedded
texture atlas** that must survive whatever the route does, ~300k tris.

## Measured already — do not re-derive

| approach | result |
|---|---|
| Blender bone heat (`ARMATURE_AUTO`) | **0 of 399,140 vertices weighted**, silently — Blender reports INFO and returns success. Mechanism sweep ruled out bone count, seam-splits, shell count, scale; envelope binds the same mesh, so the mesh is weightable and bone heat specifically fails on this geometry class |
| Envelope (Blender defaults) | Binds 100%, but mean weight-sum 7.7 at ~10 influences/vertex: the figure **tears into shards** under a single-arm arc — torso shears, face splits, leg dislocates |
| Envelope (radii from each structure's own cross-section) | 1,162 finger/toe vertices escape every envelope; glTF invents a `neutral_bone`; export refused by gate |
| Rigid per segment (each vertex to its limb-segment bone, 0.35 blend band at joints) | Coherent motion, weight-sum exactly 1.0 — but **visible stepping/seams at every joint** at 1:1. Ruled a hard fail for footage |

## Hard constraints

- **No non-commercial licence anywhere** — weights AND code; CC-BY-NC / research-only /
  academic-only banned outright; check the exact variant, not the family. Known bans already
  ruled studio-side: **Tripo** (licence conflict), **OpenPose-class detectors** (CMU NC).
  Known dead ends: **Meshy** (cannot take a supplied mesh), **Rodin / Hunyuan3D** (no rig
  node existed as of our consult #7), **UniRig** (studio-measured: shreds faced characters).
- Output must remain **a GLB that headless Blender 5.2 can animate** (bones + skin weights,
  or parented rigid parts — see Q1). The **texture atlas must survive**, or the route must
  include an automated re-bake/re-projection step, not a manual one.
- Venue: local Blender / local tools first; Comfy Cloud where it must be. Cloud **GPU-hours
  are metered** on this workspace — rough cost per route, please.

## The questions, ranked

**Q1 — the rigid-parts route (we suspect this is the honest answer for THIS character).**
A real stop-motion armature is separate rigid parts articulating at ball joints — no skin
deformation at all. Is there a standard, automatable route to **split a shell mesh into
per-segment objects** (cut at the sculpted ball joints), cap or leave the cuts, keep each
part's UV region, and parent each part to its bone? Any Comfy-side segmentation node or
Blender-standard tool that does joint-boundary mesh splitting on supplied geometry? What
handles the visible cut lines at the balls (which on this character could legitimately read
as the socket seam)?

**Q2 — the proxy-transfer route.** Watertight proxy (voxel remesh / shrinkwrap) → bone-heat
the proxy → **transfer weights** proxy→shell (Blender Data Transfer or equivalent). Is this
the established practice for binding non-manifold shell meshes? Known failure modes on
double-walled hollow geometry (inner wall inheriting outer-wall weights, etc.)? Anything in
the Comfy ecosystem that packages it?

**Q3 — repair-then-bone-heat.** What exists for **manifold repair that preserves UVs** — or
remesh + automated atlas re-bake — such that vanilla bone heat becomes viable? Name the
tools, what they pair with, and the licence per item.

**Q4 — the auto-rig ecosystem, today.** Has anything landed on Comfy Cloud or as
commercially-clean OSS that **rigs AND skins a SUPPLIED character mesh** (not one generated
inside the same service)? Exact node/model names and versions as saved in the catalog, with
licence documents. We know the landscape as of our consult #7 (2026-08-10); we are asking
what is true **now**.

**Q5 — per recommended route:** exact node/tool names · input/output formats · licence with
URL and operative clause · known failure modes on hollow double-walled shells · rough cost
(GPU-hours or local runtime).

## Answer format requested

A per-route table for Q1–Q4, then **one ranked recommendation** for this character class,
then — per our calibration protocol — **one cheap, checkable claim** we can verify locally
before acting on anything expensive.

## Standing rules (abbreviated — this is a question brief, not a build order)

No builds, no tab creation or mutation, no workflow edits. Exact names as saved in the
catalog — named models are not substitutable. If any answer is uncertain, say so at the top
rather than smoothing it. Deviations from the questions, listed first.
