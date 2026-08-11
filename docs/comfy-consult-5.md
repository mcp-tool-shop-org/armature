# Comfy Agent consult #5 — the answer, the calibration, and the ruling

**Brief:** [comfy-consult-5-brief.md](comfy-consult-5-brief.md) · **Relayed back by the
Director:** 2026-08-11 · **Calibrated locally the same day** · **Status: RULED — the
rigid-parts route (Q1) is E07's third binding arm.**

## The answer, in substance

The agent marked its uncertainty honestly (no live catalog search was run; Comfy-side
claims flagged unverified; Blender-standard claims high-confidence) and refused to invent
version strings — the exact behavior the brief asked for.

| route | verdict |
|---|---|
| **Q1 rigid parts** | **Its ranked winner, "and it's not close."** Split the shell into per-segment objects at the sculpted balls (`bpy.ops.mesh.bisect` per joint from our measured pivots), parent each part to its bone, **no deformation anywhere** — a real stop-motion armature in software. Sidesteps every measured failure (no bone heat, no manifold requirement, no weights); **bisect preserves UVs so the atlas survives with zero re-bake**; the joint cut is the socket seam this character should have. ⚠ Its shell-class warning: `Separate → By Loose Parts` explodes on our 67 interior shells — **assign faces to segments by spatial region** (face-centroid vs bone-segment nearest test). For the cut line: **collar overlap** (offset the cut so parts interpenetrate at the ball) is what physical ball-jointed armatures do — no gap opens under articulation. Licence: Blender GPL + our script — clean. Cost ≈ zero, local |
| Q2 proxy-transfer | Real but weak on exactly our class: nearest-surface weight transfer puts inner-wall vertices on the wrong bone (the wall shears open), and any tractable voxel proxy loses fingers/toes below resolution. Blender-standard, clean, not chosen |
| Q3 repair-then-heat | The honest tension named: UV-preserving repair (fill holes, merge) cannot remove the 67 interior shells, so heat still fails; full remesh fixes heat but destroys UVs and needs an automated re-bake (`xatlas` MIT + Blender bake — scriptable). The fallback if true skin deformation is ever demanded |
| Q4 auto-rig ecosystem | **"The auto-rig ecosystem does not have your answer. That is itself the finding."** UniRig ruled out (measured), Rignet NC-banned, Mixamo humanoid-detector likely fails a ball-jointed mannequin, AccuRig licence-uncertain and off-cloud, Comfy-side rig nodes unverified without a catalog search |

Open offer from the agent: a read-only live catalog search to firm the Q3/Q4
"on-cloud-today" rows. **Disposition: optional, not on the critical path** — the chosen
route uses no Comfy nodes at all. Worth taking in a future consult round for the map's own
sake.

## The calibration — run before ruling, per protocol

**Claim tested:** `Mesh.bisect` preserves UVs across the cut.
**Method:** the actual performer GLB (sha `9e20ea7d…b1aa`), full-mesh bisect on one plane
through the torso band, per-face UV snapshot keyed by face center, compared pre/post.

```
faces far from cut: 298,366 → identical UVs 298,366 · changed 0 · missing 0
faces at the cut:     1,590 → 1,980 split products, interpolated UVs
VERDICT: PASS
```

The route's "atlas survives, no re-bake" promise is proven on this mesh before any
scripting. (Script: session scratchpad `calibrate_bisect_uv.py`; runnable anywhere.)

## The ruling

**E07 arm (c) — rigid parts — is commissioned**, with the consult's shell-class
prescriptions binding: spatial-region face assignment (never loose-parts), collar overlap
at each joint bounded by that joint's own measured ball radius, parts parented to their
bones with no armature deform, the atlas asserted untouched. Gates: parts accounting
(every face assigned exactly once, raises), part↔bone registration, rigid-arrival
liveness (the authored arc arrives whole), determinism. The result comes back on a
dailies-standard sheet — rest, arc frames, 1:1 joint insets under articulation — and
**the Director's eye rules on the joint seam read**, per his standing gate.

Arms (a) envelope and (b) rigid-per-segment stay in the record as the measured failures
that motivated this consult, per his ruling: *"This is a hard fail."*
