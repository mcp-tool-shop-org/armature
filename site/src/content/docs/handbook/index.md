---
title: The armature handbook
description: What armature is, the thesis it exists to test, and the honest state of the repo.
sidebar:
  order: 1
---

**You block the shot. The model shoots it.**

A video model can produce motion, light and life that no renderer can. It cannot be told
*who is on screen and where they are standing*. armature is meant to supply exactly that: a
canonical character mesh is staged and animated in headless Blender, and the render becomes a
per-frame **control sequence** the video model works inside — so AI-generated video can carry
one persistent main character whose position and pose are known every frame.

The previz scene is ground truth. The video model paints life over it.

## Read this part first

**armature was founded on 2026-08-10 and nothing has been measured here.**

| | As of 2026-08-10 |
|---|---|
| Experiments run | 0 |
| Generation probes | 0 |
| Credits spent | 0 |
| The founding thesis | **UNTESTED** |

Everything on this site is one of three things: an idea, stated as an idea; a finding measured
by someone else and retrieved with a resolvable citation; or an explicit statement that
something has not been measured. There is no install page, no quick start and no version badge,
because there is nothing yet to install.

That is not modesty. A page that implies a capability nobody has measured is the same defect as
a report with a placeholder shaped like evidence — published to strangers instead of buried in a
document. The repo's method is built to catch that defect, so its own public surface has to
survive it.

## Where armature sits

armature is downstream of [facet](https://github.com/mcp-tool-shop-org/facet), a sibling repo
that turns a styled 2D concept into a textured 3D asset. **facet cuts and paints the figure;
armature stages and performs it.** armature consumes facet's canonical assets and turnarounds
and never writes into its tree.

It inherits facet's discipline too, which is described on the [method](/armature/handbook/method/)
page and was paid for the hard way.

## What armature is not

Named in the roadmap, because each is a plausible-sounding drift that would eat the project:

- **Not a video editor or NLE.** It produces shots. Assembly, grading and sound live elsewhere.
- **Not an animation suite.** Blender is the animation tool. armature stages and renders.
- **Not a character creator.** facet makes the asset; armature consumes it.
- **Not a model.** No training a video model from scratch. Per-character identity adapters are a
  measured question, not a founding assumption.
- **Not a general 3D-to-video converter.** The unit of work is *a shot of a known character*.
- **Not a real-time system.** Batch, headless, recorded.

## The rest of this handbook

- [The thesis](/armature/handbook/the-thesis/) — why control sequences rendered from geometry,
  and what the published evidence actually says. The longest page, and the one worth your time.
- [Method](/armature/handbook/method/) — three seats, spec → report → ruling, and why the
  discipline exists.
- [The license gate](/armature/handbook/license-gate/) — no non-commercial models anywhere,
  the verified map, and the two traps it caught.
- [Roadmap](/armature/handbook/roadmap/) — the arc, the hinge, and the drift tripwires.

The canonical copies of everything summarized here live in the repo:
[README](https://github.com/mcp-tool-shop-org/armature/blob/main/README.md) ·
[CLAUDE.md](https://github.com/mcp-tool-shop-org/armature/blob/main/CLAUDE.md) ·
[research grounding](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/research-grounding.md) ·
[license map](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/license-map.md) ·
[roadmap](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/ROADMAP.md).
Where this handbook and the repo disagree, the repo is right — it is what the specs cite.
