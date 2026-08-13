---
title: The armature handbook
description: What armature is, the thesis under test, and the honest measured state of the repo.
sidebar:
  order: 1
---

**You block the shot. The model shoots it.**

A video model can produce motion, light and life that no renderer can. It cannot be told
*who is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model works inside — so AI-generated video carries one
persistent main character whose position and pose are known every frame.

**armature is image-to-video with a GLB instead of an image.** Everything spatial is authored —
character, pose, camera, staging, blocking — and the model paints life over it. The deliverable
is footage: film, cutscenes, character performance, any shot at all. A game is one consumer of
that footage, not the boundary of the tool.

The previz scene is ground truth. The video model paints life over it.

## Read this part first

**The founding thesis is no longer untested.** Twelve experiments have closed since 2026-08-10,
and the arc has been through a repo-wide audit — called by the Director, recorded in
[docs/audit-first-arc.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/audit-first-arc.md) —
whose finding is stated plainly rather than buried: the first arc bought clean measurements of
the *mechanism* and zero frames of the *product*, and the work now runs under a binding
trajectory rule because of it.

| | Measured, as of 2026-08-13 |
|---|---|
| Experiments closed | **12** (one more withdrawn un-run on a falsified premise) — the control arc · rig repair and skeleton approval · **the first painted shot** · the clean-chain baseline · densified driving · the no-control route's instructive hard fail · **the free route's first held world** |
| Routes | the **driven route** (rig-rendered pose → Animate; proven at shot level, parked for AI-animation buildout) · the **free route** (authored start frame → camera tier at the 6.0 / uni_pc baseline) · the **composed route** under probe (E13, dispatched 2026-08-13) |
| What a control sequence governs | **where** the figure is, at what scale, **when** it moves, and **authored subject motion** — 85.0° against 0.062° |
| The division of labour | **control owns the outline; the reference owns surface, material and costume** |
| Identity | **holds at the Director's eye** — driven (E08) and unanchored (E11 wave 1); whether it survives a hosted reference-to-video tier fed only authored references is E13's question |
| Worlds | **hold when handed** — a real room survives to the last frame on two seeds (E12); handed a previz void, the tier faithfully keeps the void (E11 wave 3) |

Everything on this site is measured, cited to a numbered experiment, or explicitly marked
open. A page that implies a capability nobody has measured is the same defect as a report
with a placeholder shaped like evidence — the repo's method exists to catch that defect, so
its own public surface has to survive it.

## Where armature sits

armature is downstream of [facet](https://github.com/mcp-tool-shop-org/facet), a sibling repo
that turns a styled 2D concept into a textured 3D asset. **facet cuts and paints the figure;
armature stages and performs it.** armature consumes facet's canonical assets and never writes
into its tree — and the two repos share one record engine
([record-index](https://github.com/mcp-tool-shop-org/record-index)), so each side's evidence
trail is queryable by the other.

It inherits facet's discipline too, described on the [method](/armature/handbook/method/) page
and paid for the hard way.

## What armature is not

Named because each is a plausible-sounding drift that would eat the project:

- **Not limited to games.** Cutscenes, movies, character poses and movement — anything
  image-to-video can make, made with a scene you own instead of a still. The scope has been
  shrunk twice and corrected twice; describing armature by a single use-case is the drift
  signature.
- **Not a video editor or NLE.** It produces shots. Assembly, grading and sound live elsewhere.
- **Not an animation suite.** Blender is the animation tool. armature stages and renders.
- **Not a character creator.** facet makes the asset; armature consumes it.
- **Not a model.** No training a video model from scratch. Per-character identity adapters are
  a measured question, not a founding assumption.
- **Not a real-time system.** Batch, headless, recorded.

## The rest of this handbook

- [The thesis](/armature/handbook/the-thesis/) — why control sequences rendered from geometry,
  and what the measured evidence actually says.
- [Method](/armature/handbook/method/) — three seats, spec → report → ruling, and why the
  discipline exists.
- [The license gate](/armature/handbook/license-gate/) — no non-commercial models anywhere,
  the verified map, and the traps it caught.
- [Roadmap](/armature/handbook/roadmap/) — the arc as planned, the arc as run, and what
  governs now.

The canonical copies of everything summarized here live in the repo:
[README](https://github.com/mcp-tool-shop-org/armature/blob/main/README.md) ·
[CLAUDE.md](https://github.com/mcp-tool-shop-org/armature/blob/main/CLAUDE.md) ·
[the audit](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/audit-first-arc.md) ·
[license map](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/license-map.md) ·
[roadmap](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/ROADMAP.md).
Where this handbook and the repo disagree, the repo is right — it is what the specs cite.
