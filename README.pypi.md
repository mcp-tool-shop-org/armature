# armature

**You block the shot. The model shoots it.**

A video model can produce motion, light and life that no renderer can. It cannot be told
*who is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model must obey — so AI-generated video can carry one
persistent main character whose position and pose are known every frame.

**armature is image-to-video with a GLB instead of an image.** Everything spatial is
authored, and the model paints life over it. The deliverable is footage — film, cutscenes,
character poses and movement, any shot at all. A game is one consumer of that footage, never
the boundary of the tool.

## Install

```bash
pip install armature-studio
```

```bash
armature check
```

## What this package is

The installable package is `armature_core` — the measured pieces of the pipeline, every one
of which imports under a plain CPython:

- **Gates that raise.** `gates`, `route_gates`, `rig_gates`, `donor_gate` — predicates that
  refuse a bad step *inside* the tool performing it, rather than warning beside it.
- **Framing and turnaround.** `framing`, `turnaround`, `startframe` — perspective and
  orthographic camera solves, shared-scale shot-sets, silhouette extent, and the
  frame-clearance checks that refuse a cropped subject.
- **Control channels.** `channels`, `openpose`, `aapose`, `landmarks`, `lift_solve` —
  channel maths and pose conventions for driving a video model.
- **Rig and mesh.** `joints`, `binding`, `parts`, `posearc`, `walk`, `glb`.
- **Contracts and records.** `shotspec`, `subject`, `sitelist`, `assembly`, `clipstats`,
  `clipcompare`, `pngio`, `errors`.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

## What this package is not

**The rendering scripts are not console entry points, deliberately.**
`render_turnaround.py`, `stage_render.py` and their siblings run inside **Blender's own
interpreter**:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

A console script installed on your Python could not import `bpy` and would fail on its first
line, so shipping one would be a promise the package cannot keep. Those scripts live in the
repository, where the invocation that works is the one written down.

`armature_core.blender_scene` is the single module that imports `bpy`. It is packaged, and it
resolves only under Blender — `armature check` reports it as `needs-blender` rather than as a
defect.

## The discipline this comes from

armature is an experiment repository whose product is its record: a spec before the work, a
report after, a ruling last, and the Director's eye as the verdict of record. Metrics are
diagnostics and gate nothing on their own. Every generation records its model, payload, seed
and control hashes, because a recipe that does not reproduce its output is not a recipe. No
non-commercially-licensed model, weight or dependency enters the pipeline — anywhere,
including experiments.

- **Docs and handbook:** https://mcp-tool-shop-org.github.io/armature/
- **Repository and the full record:** https://github.com/mcp-tool-shop-org/armature

## Requirements

Python 3.10+ and numpy. Blender 5.x is required only for the rendering scripts in the
repository, not for this package.

## License

MIT.
