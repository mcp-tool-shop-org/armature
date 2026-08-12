<p align="center">
  <img src="docs/assets/logo-wide.png" alt="armature — you block the shot, the model shoots it" width="820">
</p>

#

**You block the shot. The model shoots it.**

**[Landing page & handbook →](https://mcp-tool-shop-org.github.io/armature/)** *(the repo
is private as of 2026-08-11 and Pages is dark with it — the record is this tree)*

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

---

## State: the thesis is under test, and three things are measured

Founded **2026-08-10**. Eleven experiments closed and the thesis has moved from *under test*
to **measured at product level**: the character has danced on screen twice — once driven from
his own rig, once free — judged by the Director's eye both times. The founding-arc audit is at
[docs/audit-first-arc.md](docs/audit-first-arc.md); the posture since 2026-08-12 is a learning
monorepo — experiments prove paths, no route is canon by momentum (CLAUDE.md).

| | |
|---|---|
| Experiments | **E01–E11 closed** (E05 withdrawn on a falsified premise) — the control arc (E01–E06) · rig repair + skeleton approval (E07) · **the first painted shot** (E08) · the clean-chain baseline (E09) · densified driving adopted (E10) · the no-control route, three waves to an instructive hard fail (E11) |
| Routes | **two** — the **driven route** (rig-rendered AAPose sticks → Animate; proven at shot level, parked for AI-animation buildout) · the **free route** (GLB-authored start frame → I2V / camera tiers; identity holds unanchored, worlds must be authored or tamed) |
| Spend | 22 probes in the founding arc at 4 credits each; the E08–E11 arc ran at **0 credits** (GPU-hour billing) under per-experiment ceilings, reserves lapsing unspent |
| Licence map | every adopted dependency carries a **retrieved licence document**; UNVERIFIED is treated as NO; the gate's stated purpose is publishing the studio's art |
| Tests | **860 passing on the rig** (13 skips), under `-O` too; CI exercises what a runner honestly can — rig-local assets **skip visibly** |
| Status | **private by the Director's choice since 2026-08-11** — Pages dark; the record is the docs tree, and it is complete |

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

### What is not

- **Arms and hands at speed.** Prompt-side treatment measured insufficient twice; the hand
  geometry is the promoted lever, and the cfg/sampler premise (catalog says 6.0 / uni_pc for
  the camera weights; we ran 3.5 / euler) is named and open.
- **A world worth holding on the camera tier.** It preserves what it is handed — hand it a
  previz void and it faithfully delivers nothing (E11 wave 3's hard fail). The alpha law's
  scene-plate composite is the named, undispatched lever.
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

## Standing rules that shape everything here

**No non-commercial models, ever — including in experiments.** CC-BY-NC, research-only and
academic-only licenses are banned outright. A conclusion drawn on a banned model is a
conclusion that has to be thrown away, so it never starts.

**Metrics are diagnostics; the Director judges.** Whether the figure on screen is the same
character is canon, and no metric approximates it. Every generating experiment builds a
**control | output | reference | provenance** sheet before a single number is quoted.

**Cloud credits are bounded before they are spent.** Spent credits have no undo, so every spec
states its ceiling per arm in advance.

## License

MIT — see [LICENSE](LICENSE). The license of any *model* used through this tool is a separate
question, tracked in `docs/license-map.md`.
