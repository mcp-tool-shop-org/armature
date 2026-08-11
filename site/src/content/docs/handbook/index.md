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

**The founding thesis is no longer untested.** Five experiments have closed since 2026-08-10,
and the arc has been through a repo-wide audit — called by the Director, recorded in
[docs/audit-first-arc.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/audit-first-arc.md) —
whose finding is stated plainly rather than buried: the first arc bought clean measurements of
the *mechanism* and zero frames of the *product*, and the work now runs under a binding
trajectory rule because of it.

| | Measured, as of 2026-08-11 |
|---|---|
| Experiments closed | **5** — exporter · first contact · authored motion · the noise floor · reference-onto-schematic (one more withdrawn un-run on a falsified premise) |
| Generation probes | **22** |
| What a control sequence governs | **where** the figure is, at what scale, **when** it moves, and **authored subject motion** — 85.0° against 0.062° |
| The division of labour | **control owns the outline; the reference owns surface, material and costume** |
| The open question that matters | whether the figure is the *same character* — canon, judged by eye, still open |
| In production now | the first performer, built fresh through facet's route; then the rig; then the first authored performance |

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
