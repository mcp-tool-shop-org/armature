<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/armature/readme.png" alt="armature — you block the shot, the model shoots it" width="820">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/armature/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

#

**You block the shot. The model shoots it.**

**[Landing page & handbook →](https://mcp-tool-shop-org.github.io/armature/)**

A video model can produce motion, light and life that no renderer can. It cannot be told *who
is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model must obey — so AI-generated video can carry one persistent
main character whose position and pose are known every frame.

**armature is image-to-video with a GLB instead of an image.** Everything spatial is authored,
and the model paints life over it. The deliverable is footage — film, cutscenes, character
poses and movement, any shot at all. A game is one consumer of that footage, never the
boundary of the tool.

Stage your character in Blender. Render the control sequence. Let the video model paint the life
over it. Structure comes from geometry you own; life comes from the model; identity is a named,
versioned thing that rides in the prompt and the reference stack — never an accident of a lucky
frame.

## Install

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

The installable package is **`armature_core`** — the gates, the framing and turnaround solvers,
the shot-spec contract, the channel maths and the payload builders. Every one of them imports
under a plain CPython, which is what lets them be tested, and packaged, without Blender present.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**The rendering scripts are not console entry points, and that is deliberate.**
`render_turnaround.py`, `stage_render.py` and their siblings run inside **Blender's own
interpreter** — a console script on your Python could not import `bpy` and would fail on its
first line, so shipping one would be a promise the package cannot keep:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

They stay here in the repository, where the invocation that works is the one written down.
`armature_core.blender_scene` is the single module that imports `bpy`; `armature check` reports
it as `needs-blender` rather than as a defect.

The npm package is a **launcher, not a port**: re-implementing a threshold in a second language
is how a threshold drifts, so it forwards to the Python that holds the truth, and refuses —
loudly, non-zero, with the one command that fixes it — rather than installing anything on your
behalf.

---

## State: the thesis is measured at product level

Founded **2026-08-10**. Thirteen experiments closed and the thesis has moved from *under test*
to **measured at product level**: the character has danced on screen driven from his own rig
and free, a handed world holds to the last frame on two seeds (E12), and **identity now
survives a hosted, human-trained tier fed nothing but authored references** (E13) — all
judged by the Director's eye. The founding-arc audit is at
[docs/audit-first-arc.md](docs/audit-first-arc.md); the posture since 2026-08-12 is a learning
monorepo — experiments prove paths, no route is canon by momentum (CLAUDE.md).

| | |
|---|---|
| Experiments | **E01–E14 closed** (E05 withdrawn on a falsified premise) — the control arc (E01–E06) · rig repair + skeleton approval (E07) · **the first painted shot** (E08) · the clean-chain baseline (E09) · densified driving adopted (E10) · the no-control route, three waves to an instructive hard fail (E11) · **the free route gains a world** and the 6.0 / uni_pc baseline (E12) · **the composed route answers its question** (E13 — dispatched, halted at zero spend, repaired by a support arc, re-armed, run, and closed inside one date: identity holds at the Director's eye; reference grounds steer model-decided worlds) · **the LoRA scene-lever priced live** (E14 — the bake-off: both style LoRAs bind on the derivative weights; the character holds on `technically_color` and fails on the photo-real pair; the winner carries an unresolvable served-file tier and a credit obligation, both recorded) |
| Routes | **three, measured** — the **driven route** (rig-rendered AAPose sticks → Animate; proven at shot level, parked, and licence-clear for its unpark) · the **free route** (GLB-authored start frame → camera tier at the 6.0 / uni_pc baseline; identity holds unanchored, a handed world holds on two seeds, and the LoRA scene-lever is measured live — E14) · the **composed route** (authored references into a hosted identity-lock tier — graduated by E13: identity-locked, model-decided cinematography with worlds steered by what the references carry; disclosure note in its spec) |
| Spend | 22 probes in the founding arc at 4 credits each; the E08–E12 arc metered **0 credits** (GPU-hour billing) under per-experiment ceilings; **E13's four generations are the repo's first partner-credit spend, inside their pre-stated 424–844 bracket**; E14's two generations metered **0 partner credits** at a two-generation ceiling, reached exactly |
| Licence map | every adopted dependency carries a **retrieved licence document**; UNVERIFIED is treated as NO; routes through third-party tiers additionally carry **per-route disclosure** (Director-ruled 2026-08-12); the gate's stated purpose is publishing the studio's art |
| Tests | **1311 passing on the rig** (13 skips, measured 2026-08-15 at the v0.2.0 cut), under `-O` too; CI exercises what a runner honestly can — rig-local assets **skip visibly** |
| Status | **v0.2.1 released 2026-08-15** — the record becomes an installable toolkit: `armature_core` on PyPI as `armature-studio` and on npm as `@mcptoolshop/armature-studio`, published from a tag by OIDC with no long-lived token anywhere. The record is still the docs tree, and it is still complete |

### What is measured (the current arc)

- **Identity holds** — driven (E08: the face reads as the twin's through the shot) *and*
  unanchored (E11 wave 1: every feature to the last frame with no reference, no clip-vision,
  no driving signal). The Director's eye is the verdict of record on both.
- **The camera obeys explicit control to one pixel** on the camera-tier weights (E11 wave 3) —
  and pushes in uncommanded without it (E11 wave 1).
- **Density moves the signal, not the performance** (E10) — resampling smooths steps 41 %,
  the performance 8.6 %; adopted anyway by eye: more fps reads better.
- **A licence row is not a wiring claim** (E11 wave 2) — a mapped-Apache model and a graph that
  never loaded it produced 65 frames of noise with every gate green. Gate PAIR now exists.
- **Scene composition is seed-volatile** (E10 / E11) — identical text re-composed the world
  wholesale across seeds. **A scene claim needs two seeds before it is a property.**
- **A handed world holds** (E12) — a real room in the start frame survives to the last frame
  on two seeds on the camera tier, one-variable-attributed to the start image by field diff.
  The same tier handed a previz void held a void (E11 wave 3): worlds are authored, then kept.
- **The catalog's 6.0 / uni_pc is the camera tier's baseline** (E12) — the inherited
  3.5 / euler premise fell to its own rung: at the catalog settings the same seeds that lost a
  head and grew a limb hold the figure to f80. The cost is named — stronger adherence pushed
  the **unscoped identity clause** onto the crowd on one seed of two; the subject-scoped
  prompt is the promoted lever.
- **Identity survives a hosted tier fed only authored references** (E13) — on wan2.7's
  reference-to-video, both arms, both seeds, the stylized wooden performer came through a
  human-trained model as the same character at the Director's eye. Three blind predictions
  across two seats expected the tier to overwrite non-human structure; none was right —
  one-directional pessimism about these models is now written down as calibration doctrine.
- **Reference grounds steer model-decided worlds, and dominate seed chaos on that tier**
  (E13) — grey plates begat a grey studio, a warm bar clip begat a warm interior, and both
  seeds per arm agreed. Mechanism attribution (plate-bleed vs studio-default) honestly open
  at four generations; a property-grade claim runs under the two-seed law in a designed
  follow-up.
- **A constructed VIDEO reaches VIDEO sockets** (E13) — no upload path exists for clips, but
  81 authored frames assembled in-graph (`CreateVideo`) were accepted at a reference-video
  socket. Every VIDEO-typed input on the platform is in principle reachable from authored
  frames.

### What is not

- **Arms and hands at speed.** Still failing at f80 on both seeds at both settings (E12).
  The lever is re-scoped **presentation-first** — wrist and camera staging, from the
  Director's own diagnosis on the GLB (the claw is a projection artifact, not mesh damage) —
  with mesh surgery as the fallback, never the first move.
- **The camera claim on photographic worlds.** 0/81 horizon detections across all four E12
  clips is a detector wanting a seam this world does not have — registered blind before
  submission, never converted into a camera result. A **seam-free camera instrument** is owed
  before any camera number is read on a real room.
- **The narration shelf** (consult #7): beat endpoints, per-chunk prompts, video-time area
  conditioning, camera embeddings — adopted, licensed where needed, untested.

A negative answer remains a full success here — E11's hard fail bought three gates, two laws,
and the exact shape of the next work, and the roadmap said it would before any evidence arrived.

## How this repo works

- [CLAUDE.md](CLAUDE.md) — how to work here: the three roles, the rules each seat runs under,
  and the non-negotiables (the license gate, bounded credits, identity is judged by eye).
- [docs/ROADMAP.md](docs/ROADMAP.md) — the whole build, session by session, with the drift
  tripwires named in advance.
- `docs/experiments/` — every non-trivial change runs as a numbered experiment:
  **spec before the work → report after → advisor ruling last.**
- `docs/license-map.md` — the verified commercial-use map. Nothing enters the pipeline without
  a retrieved license document.

The method is inherited from [facet](../facet), where it was paid for: in facet's founding
session six inherited claims were falsified, each in minutes, because each sat next to runnable
code. armature is downstream of facet — facet cuts and paints the figure; armature stages and
performs it.

## Running it

There is nothing to install. This is a repository you clone and run — no package on any
registry, no service, no daemon. Every instrument is invoked directly:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Platform | Windows 11 on the rig (Omen 45L, RTX 5090). The hermetic tests also run on `ubuntu-latest` in CI; Blender-dependent tests **skip visibly** where Blender is absent rather than passing silently |
| Python | 3.13+ — CI runs 3.13, the rig venv runs 3.14. Test dependencies are numpy, pillow, pytest, opencv (pinned to the rig's version, because the pose-raster tests assert byte-stable rasterization) and matplotlib |
| Blender | 5.2, headless only. A live GUI session produces artifacts with no recorded parameters, and a recipe that does not reproduce its output is not a recipe |
| Node | 22, for the site under `site/` only |
| Generation | runs on Comfy Cloud and is submitted by the operator; rendering and measurement run locally |

Absolute rig paths are baked into many tools and docs — they are not secrets, but they do
mean most instruments will not run unmodified on another machine.

## Standing rules that shape everything here

**No non-commercial models, ever — including in experiments.** CC-BY-NC, research-only and
academic-only licenses are banned outright. A conclusion drawn on a banned model is a
conclusion that has to be thrown away, so it never starts.

**Metrics are diagnostics; the Director judges.** Whether the figure on screen is the same
character is canon, and no metric approximates it. Every generating experiment builds a
**control | output | reference | provenance** sheet before a single number is quoted.

**Cloud credits are bounded before they are spent.** Spent credits have no undo, so every spec
states its ceiling per arm in advance.

**Routes disclose what rides with them** (the Director's ruling, 2026-08-12). Any route
through a third-party tier documents its providers' data-use and training posture, its
AI-content disclosure duties and its watermark policy, grounded in the licence map's fetched
documents. Fully-local routes state that nothing leaves the rig. A route without its
disclosure note is not complete — the first application rides E13's spec.

## Trust and threat model

The full policy is [SECURITY.md](SECURITY.md), measured against the tree rather than asserted.
The short form:

- **Data touched** — meshes, renders, videos, images and JSON on local disk, at paths you pass
  on the command line, plus `docs/index/armature.db`, a SQLite index *derived* from this repo's
  own markdown. Canonical assets are consumed read-only from sibling trees and never written to.
- **Data NOT touched** — no credentials of any kind: none are read, stored or transmitted, and
  a sweep of every tracked file for provider-prefixed keys, tokens, private-key blocks and
  inline secret assignments returns zero matches. **No telemetry, analytics or usage counting**
  is collected or sent; there is no opt-out because there is nothing to opt out of.
- **Network egress** — no Python networking library is imported anywhere in `tools/` or
  `tests/`. Two tools shell out to `curl.exe` to download the files listed in a dump *you*
  paste in, from a generation *you* submitted. Nothing else here makes a network call.
- **Permissions** — ordinary user permissions. No elevation, no service installation, no
  registry or system-settings writes.
- **The sharp edges, disclosed rather than claimed away** — file operations are not sandboxed;
  a tool writes wherever its arguments say. Unexpected failures print a raw traceback.
  Deliberate refusals do not: every gate raises a typed error carrying the measurement that
  fired it, and **none of them is an `assert`** — the suite runs a second time under `-O` in CI
  to prove they still raise.
- **Support status** — `main` is the only supported state. No release channel, no backport
  policy, no SLA.

**Ship gate.** [SHIP_GATE.md](SHIP_GATE.md) carries the hard gates A–D as they actually stand,
with every line either checked with its evidence or skipped with the reason on its merits. The
soft-gate identity items are listed honestly, including the one still open.

## License

MIT — see [LICENSE](LICENSE). The license of any *model* used through this tool is a separate
question, tracked in `docs/license-map.md`.
