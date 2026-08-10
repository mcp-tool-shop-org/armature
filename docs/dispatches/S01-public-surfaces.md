# S01 — public surfaces (landing page + handbook)

**Seat:** executor · **Written:** 2026-08-10 by the advisor · **Type:** build session, not an
experiment — it measures nothing and predicts nothing. · **Credit ceiling: ZERO.**

**Why now, before the tool exists:** the surfaces are being stood up early *so they are cheap to
update as evidence arrives*, not because there is something to announce. Every later session
appends to a page that already exists instead of writing a page from scratch under deadline.

This is **not** the full treatment. No translations, no logo, no shipcheck, no publish, no npm.
Those are P02 on the [roadmap](../ROADMAP.md), after the thesis has been tested.

---

## The one rule that governs this whole session

**This repo is at day zero and the public surface must say so.**

armature has run zero experiments, spent zero credits, and its founding thesis is untested.
A landing page that reads like a product announcement would be a claim with no measurement
behind it — the same defect as facet's placeholder-shaped-like-evidence rule, published to
strangers instead of buried in a report.

So: **describe the thesis, the method and the evidence that exists; never imply a capability
that has not been measured.** Concretely —

- ✅ "armature's thesis is that a control sequence rendered from a posed mesh can hold one
  character through a video model. **That thesis is untested here.** Champ (arXiv:2403.14781)
  measured the closest published version of it and found dense 3D-parametric guidance beats
  2D skeleton-only."
- ❌ "armature keeps your character consistent across shots." — no measurement supports this yet.
- ❌ Any "Get started" / "Install" / "Quick start" section. **There is nothing to install.**
  A page that offers an install command for a package that does not exist is the worst version
  of this failure.
- ✅ A "Where this is" section carrying the honest counters from
  [README.md](../../README.md) — experiments run, credits spent, thesis status.

If a claim on the page cannot be traced to `docs/research-grounding.md`, `docs/license-map.md`,
or an explicit "not yet measured", it does not go on the page.

## Toolchain — enumerated, not invented

The studio's established path, verified on this rig 2026-08-10. **Do not introduce a different
site framework.**

- `@mcptoolshop/site-theme` **v2.1.0** on npm (bin: `site-theme`) — "Multi-template Astro toolkit
  for landing pages, docs, product sites, portfolios, and SaaS dashboards".
- Astro + `@astrojs/starlight` + `@tailwindcss/vite` + tailwindcss.
- **Reference implementation to mirror: `E:\AI\anchor\site\`.** Read it before you start. Its
  layout is the house pattern:

```
site/
  astro.config.mjs
  package.json
  src/site-config.ts
  src/content.config.ts
  src/content/docs/handbook/*.md
  src/styles/global.css
  src/styles/starlight-custom.css
```

`astro.config.mjs` follows anchor's shape exactly, with `base: '/armature'`,
`site: 'https://mcp-tool-shop-org.github.io'`, a GitHub social link to
`https://github.com/mcp-tool-shop-org/armature`, `disable404Route: true`, and a sidebar that
autogenerates from the `handbook` directory.

## Deliverable 1 — the landing page

**Hero (Director-selected 2026-08-10 — use this wording):**

> # armature
> ## You block the shot. The model shoots it.
>
> Stage your character in Blender. Render the control sequence. Let the video model paint the
> life over it.

Supporting copy may draw on the alternates that were considered, which remain good subheads:
*"Same character. Every frame."* · *"AI video that knows who's in it."* · *"The model
improvises. The scene doesn't."*

**Sections, in this order:**

1. **The hero**, above.
2. **The problem, in two sentences.** A video model produces motion, light and life no renderer
   can. It cannot be told who is on screen and where they are standing.
3. **How it works** — a three-step read: *stage the canonical mesh in Blender → render per-frame
   control channels (depth, normal, mask, edge, optional pose) → the video model generates
   within that structure.* Keep it visual and short; this is the section a stranger reads.
4. **Where this is** — the honest counters. Day zero, thesis untested, and a link to the roadmap.
   **This section is the point of the page.** Do not bury it.
5. **What is already established** — the two things that ARE evidenced, and they are genuinely
   interesting to a reader:
   - The closest published precedent (Champ, arXiv:2403.14781) measured 3D-parametric guidance
     beating 2D skeleton-only — FVD 192.34 → 170.20.
   - **The licensing finding**, which is a real service to anyone building in this space:
     OpenPose is CMU non-commercial, and Depth Anything V2 Small is Apache while Large is
     CC-BY-NC. Rendering control from geometry sidesteps that whole tier by construction.
6. **How this repo works** — the three roles and the spec→report→ruling loop, briefly, linking to
   the handbook.
7. **Links** — Handbook · GitHub · Roadmap · License map.

**No install section. No badges claiming a version that does not exist. No screenshots of
output that has not been generated.**

## Deliverable 2 — the handbook

Starlight pages under `site/src/content/docs/handbook/`. Write **these five and no others** —
pages for features that do not exist are the same failure as an install command:

| Page | Carries |
|---|---|
| `index.md` | What armature is, the thesis, and the day-zero state. The handbook's front door. |
| `the-thesis.md` | Why control sequences from geometry — the argument, with the research grounding cited by finding number. This is the most interesting page; give it room. |
| `method.md` | How this repo works: the three roles, spec → report → ruling, why the discipline exists (inherited from facet, six falsified claims in one session). |
| `license-gate.md` | The no-non-commercial stance, the verified map, and the traps found. Genuinely useful to strangers. |
| `roadmap.md` | Where this is going, the phases, and the drift tripwires. |

**Do not duplicate content — link to it.** `docs/research-grounding.md`, `docs/license-map.md`
and `docs/ROADMAP.md` in the repo are canonical; the handbook pages summarize and point. Two
copies of a finding will diverge, and the repo copy is the one specs cite.

## The unresolved question — report it, do not improvise past it

**GitHub Pages deployment is unresolved across the org and you must not guess.** Measured
2026-08-10: `anchor` and `ai-crucible` both build a `site/` with this exact toolchain, both have
**only `ci.yml`** in `.github/workflows/`, and neither has a Pages deploy workflow; the Pages API
returned no configured source for either.

This collides with two standing rules: **max two workflow files per repo**, and `release.yml` is
**already claimed** by the PyPI Trusted Publisher registration (see
[publishing.md](../publishing.md) — OIDC authenticates the workflow filename, so that name
cannot be repurposed).

**What to do:** build the site so that it compiles, and add a `site-build` **job inside
`ci.yml`** (paths-gated to `site/**`) that proves it builds. **Do not create a third workflow
file. Do not repurpose `release.yml`.** Then report the deployment question to the Director with
what you found — the org's actual Pages mechanism is a fact to be established, not invented here.

## Constraints

- **Workflow files: `ci.yml` only** in this session. Paths-gated, `ubuntu-latest`, with the
  required concurrency block.
- **Node dependencies live under `site/`**, not at repo root.
- `site/node_modules`, `site/dist`, `site/.astro` are gitignored — add them.
- **Verify the build locally** (`npm install && npm run build` inside `site/`) and report the
  result. A site that has not been built is written **NOT YET BUILT**, never assumed green.
- **This is a web deliverable**, so the preview tooling genuinely applies here — unusually for
  this workspace. Serve the built site and look at it before reporting.
- Do not touch `tools/`, `docs/experiments/`, or anything E01 owns. **E01 may be running in
  parallel**; if you find yourself editing a file E01 needs, stop and report the collision
  rather than resolving it yourself.

## Out of scope

Translations · logo/brand assets · shipcheck · the full treatment · npm or PyPI publishing ·
the marketing-site sync · any claim about armature's capability · screenshots of generated
output · a "getting started" or install path.

## Report

Write `docs/dispatches/S01-report.md`: what was built, the local build result (or **NOT YET
BUILT**), the Pages-deployment finding, any place where honesty forced you to cut copy you had
written, and anything on the page you were unsure was defensible. **No judgment words** — the
Director looks at the page and decides whether it is good.
