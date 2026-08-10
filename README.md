# armature

**The scene is the skeleton; the model is the skin.**

A video model can produce motion, light and life that no renderer can. It cannot be told *who
is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model must obey — so AI-generated video can carry one persistent
main character whose position and pose are known every frame.

Structure comes from geometry we own. Life comes from the model. Identity is a named, versioned
thing that rides in the prompt and the reference stack — never an accident of a lucky frame.

---

## State: day zero — nothing has been measured

This repo was founded on 2026-08-10. **No experiment has run, no code exists beyond scaffold,
and no claim in this file is backed by a measurement taken here.** That is the honest state and
this section will change only as evidence arrives.

| | |
|---|---|
| Experiments run | 0 |
| Generation probes | 0 |
| Credits spent | 0 |
| Verified license map | pending — `docs/license-map.md` |

The thesis this repo exists to test — *does a CG-rendered control sequence hold a character
through a video model* — is **untested**. The roadmap treats a negative answer as a full
success, and says so in advance.

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
