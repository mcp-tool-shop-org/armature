# S01 — report

**Seat:** executor · **Run:** 2026-08-10 · **Spec:**
[S01-public-surfaces.md](S01-public-surfaces.md) · **Credits spent: 0** (ceiling was ZERO; no
generation of any kind occurred).

This session measured nothing about armature's thesis and predicts nothing about it. It built a
public surface and reports what was found while building it. The Director judges the page.

---

## 1. What was built

### `site/` — 14 tracked files, 6 pages

```
site/astro.config.mjs          site/src/site-config.ts
site/package.json              site/src/pages/index.astro
site/package-lock.json         site/src/content.config.ts
site/tsconfig.json             site/src/styles/global.css
                               site/src/styles/starlight-custom.css
site/src/content/docs/handbook/{index,the-thesis,method,license-gate,roadmap}.md
```

**Landing page** (`/armature/`), sections in the spec's order: hero · the problem · how it works ·
**where this is** · what is already established · how this repo works · links.

**Handbook** (`/armature/handbook/`), the five pages named in the spec and no others, sidebar
ordered by frontmatter rather than alphabetically: index → the thesis → method → the license gate
→ roadmap.

**Hero wording is the Director's, verbatim.** `headline: 'armature —'` +
`headlineAccent: 'You block the shot. The model shoots it.'` renders as the supplied line; the
description is the supplied third line unaltered.

**No install section, no quick start, no version badge, no npm link, no screenshots.** The
`npmUrl` field is omitted, which suppresses the theme's npm header button and footer link. The
hero's `previews` array — three code cards in the house pattern, used by anchor for `git clone` /
`npm install` / `npm run` — is **empty**, because every card it could hold would be a command for
something that does not exist. That leaves a visible structural gap under the hero relative to
anchor and facet. It was left empty rather than filled.

### `.github/workflows/ci.yml` — new, one job

The repo had **no `.github/` directory at all** before this session. `ci.yml` is created here
with a single `site-build` job: `ubuntu-latest`, paths-gated to `site/**` and
`.github/workflows/**`, `workflow_dispatch` fallback, the required concurrency block, `npm ci`
then `npm run build`. It carries a comment stating that the exporter arc's Python tests belong in
a **second job in this same file**, not a third workflow file.

**No third workflow file was created and `release.yml` was not touched** (it does not exist yet;
the name is reserved by the PyPI Trusted Publisher registration per `docs/publishing.md`).

### `.gitignore`

Three lines added — `site/node_modules/`, `site/dist/`, `site/.astro/`. The **lockfile is
committed** so CI's `npm ci` resolves the same tree that was built on the rig.

---

## 2. Build result

**BUILT.** `npm install` then `npm run build` inside `site/`, on this rig, 2026-08-10.

| Step | Result |
|---|---|
| `npm install` | exit 0 — 374 packages added, 375 audited, **0 vulnerabilities** |
| `npm run build` | exit 0 — **6 pages** in 2.98 s (re-run after a copy fix: 1.14 s) |
| Pages emitted | `/index.html` + `/handbook/{,license-gate,method,roadmap,the-thesis}/index.html` |
| Pagefind search index | 6 HTML files indexed |
| Sitemap | `sitemap-index.xml` emitted |

**The first build attempt failed.** Recorded because it falsifies a premise of the spec — see §4.

**Served and looked at.** `astro preview` on `localhost:4321`, inspected in the browser at 821 px
and 1441 px viewport widths: hero, all six sections, both data tables, the three feature grids,
the links grid, the footer, the handbook sidebar, and the thesis page's comparison table. Full
page text was extracted and compared against the source copy — no truncation, all sections
present. The three-column grids collapse to one column below the `md` breakpoint.

**Internal link check, run against the built output:** every `href` in `dist/*.html` pointing at
`/armature/*` or `handbook/*` was requested against the preview server.

| Result | Count | Paths |
|---|---|---|
| 200 | 12 | `/armature/`, all five handbook routes, the four CSS assets, sitemap, `handbook/` |
| **404** | **1** | `/armature/favicon.svg` — see §5 |

---

## 3. The Pages-deployment finding — **the spec's premise did not survive measurement**

The spec states: *"GitHub Pages deployment is unresolved across the org and you must not guess,"*
measured 2026-08-10 on `anchor` and `ai-crucible`.

**I surveyed all ~90 repos in `mcp-tool-shop-org` through the Pages API. It is not unresolved.**

| Measurement | Result |
|---|---|
| Org repos with a Pages source configured | **~70**, every one of them `build_type: "workflow"` |
| Org repos returning 404 (no Pages source) | ~20, including `armature`, `anchor` and `ai-crucible` |
| `facet` — armature's direct upstream sibling | **configured**, `build_type: workflow`, `https://mcp-tool-shop-org.github.io/facet/` returns **HTTP 200** |
| `shipcheck` | same, **HTTP 200** |
| `anchor` | 404 at both the API and `https://mcp-tool-shop-org.github.io/anchor/` |

`anchor` and `ai-crucible` — the two repos the spec measured — are the **exception**, not the
rule. Reading them as the org's state inverted the finding.

**The mechanism is a third workflow file.** `facet`, `shipcheck` and `roll` each carry exactly
three: `ci.yml`, `pages.yml`, `release.yml`. facet's `pages.yml` was retrieved verbatim: push on
`main` gated to `site/**`, the concurrency block, `permissions: {contents: read, pages: write,
id-token: write}`, a build job running `npm ci` + `npm run build` in `site/` then
`actions/upload-pages-artifact` on `site/dist`, and a `deploy` job on the `github-pages`
environment using `actions/deploy-pages`.

**I did not create it.** The spec's instruction was a gate — *do not create a third workflow
file, do not repurpose `release.yml`, report it* — and a gate is not walked past because the
evidence behind it turned out to be wrong. Two things now need a Director ruling, and both are
outside an executor's authority:

1. **The two-workflow cap.** `docs/publishing.md` and the studio Actions rule cap this repo at
   two files, and both are spoken for: `ci.yml`, and `release.yml` whose *filename* the PyPI
   Trusted Publisher registration authenticates over OIDC. Adding `pages.yml` makes three — which
   is what every deploying sibling actually does. The alternative is folding the upload/deploy
   jobs into `ci.yml`, which requires giving `ci.yml` `pages: write` and `id-token: write`.
2. **Pages is not enabled on `armature`.** The API returns 404 — there is no configured source.
   That is a repository-settings change, which I did not make.

Until both are resolved, `ci.yml` proves the site compiles and nothing publishes it.

---

## 4. The reference implementation does not build on the current toolchain

**The first `npm run build` failed**, hard, with a config error:

> `Found an `autogenerate` object with a `label`. Support for autogenerated sidebar groups was
> removed in Starlight v0.39.0.`

`anchor` (Starlight `^0.38.2`) and `facet` (`^0.37.6`) both use the
`{ label, autogenerate }` sidebar shorthand. On Starlight 0.41.7 it is a **build-stopping error,
not a deprecation warning**. The autogenerate config now has to sit inside an `items` array.
armature's `astro.config.mjs` uses the current form and carries a comment saying why it differs
from the two repos it was told to mirror.

Mirroring the reference implementation verbatim would not have produced a building site. Flagged
because it applies to any future repo told to copy `anchor/site/`.

**Versions installed:** `astro ^7.2.0`, `@astrojs/starlight ^0.41.7`, `@mcptoolshop/site-theme
^2.1.0`, `tailwindcss` / `@tailwindcss/vite ^4.3.3`. site-theme 2.1.0 is the version the spec
named; the rest are current releases as of 2026-08-10. Starlight 0.41.7 declares
`astro: ^7.0.2` as a peer, so Astro 6 (anchor's pin) and Astro 7 + Starlight 0.41 are not
interchangeable — they move together.

**The `tool` template was considered and not used.** site-theme 2.0.0 added a sixth template for
CLI/MCP/npm landing pages, but `ToolSiteConfig` makes `quickstart` (install / run / verify) a
**required** field. It cannot represent a tool with nothing to install. The `default` template
was used instead, as anchor does.

---

## 5. Defects and things left alone

**`/armature/favicon.svg` returns 404 on every page load.** site-theme's `BaseLayout` emits
`<link rel="icon" href="${base}favicon.svg">` unconditionally, and there is no `site/public/`.
This is **pre-existing and org-wide, not introduced here**: `anchor` and `facet` have no
`site/public/` either, and the live `facet` and `shipcheck` sites return 404 on the same path.
Fixing it means authoring a brand asset, which the spec puts out of scope. Left as found and
reported.

**`README.md` may now be inaccurate, and I did not edit it.** It states *"no code exists beyond
scaffold."* The working tree currently contains untracked `tools/`, `tests/` and `specs/`
directories from the E01 session running in parallel. The landing page deliberately carries **no
code-state counter** for this reason — any such number would be stale within hours, and I could
not check E01's tree without touching it. The counters the page does carry (experiments, probes,
credits) are the README's, and the table header dates them `As of 2026-08-10` with a line
pointing at README.md as the live source. **`README.md` is left for the advisor to reconcile once
E01 lands.**

**E01 collision avoidance.** Nothing under `tools/`, `tests/`, `specs/` or `docs/experiments/`
was read for editing, modified, or staged. `git add -A` was never run; every path was staged
explicitly and `git add --dry-run site/` was inspected before staging (14 files, no
`node_modules`, no `dist`). The only shared file touched is `.gitignore`, whose diff is three
site-only ignore lines plus a comment. **No collision was found.**

---

## 6. Copy that was cut, and the claims I am least sure of

The spec's rule was that a claim must trace to `docs/research-grounding.md`,
`docs/license-map.md`, or an explicit "not yet measured." What that removed:

**Cut — F2, Ctrl-Adapter (arXiv:2404.09967).** The most quotable control-signal result available
("multi-condition control compounds but saturates," with the depth-vs-canny split). It is
**downgraded to diagnostic** in the grounding doc — both groundedness checkers returned
NOT_IN_ABSTRACT because the numbers live in a table that has not been retrieved. It appears
nowhere on the site.

**Cut — F23's flicker analysis.** The grounding doc flags with a ⚠ that the second identifier's
actual title is "Generative World Renderer" and that its characterization as a flicker analysis
is the research lane's summary and **is not confirmed**. Rather than repeat a characterization
the source record itself distrusts, F23 was left off entirely.

**Cut — a dataset for Champ.** The grounding doc does not record what data Champ used, so the
page says its result was measured *"on someone else's subject matter"* rather than naming a
benchmark.

**Cut — a code-state counter.** See §5.

**Softened after first draft.** The license-map counter originally read *"5 recorded UNVERIFIED
and therefore treated as banned."* `docs/license-map.md` says UNVERIFIED is *treated as NO until
retrieved* — a block pending retrieval, not the outright ban that CC-BY-NC carries. The cell now
reads *"treated as NO until retrieved."* The site was rebuilt after the change.

### The three I am least sure are defensible

1. **The channel list in "How it works," step 2** — *"depth, normal, mask, edge, and optionally a
   skeleton."* That list is the spec's own wording. The grounding's F1 measures **depth + normal
   + semantic**, skeleton optional; **mask and edge are not part of what F1 measured**, and F22
   (rendered edges vs Canny) is explicitly marked *unverified-groundedness* and framed in the
   grounding doc as a testable claim rather than an assumption. It is written on the page as what
   the exporter is *intended* to emit, never as an evidenced set — but a reader could take it as
   settled, and the exporter's spec is what actually decides it. **Flagged for the advisor.**

2. **"20+ rows" for the license map.** Taken from README.md. Counting the tables directly gives
   20 licensed rows plus 5 UNVERIFIED. Defensible, but it is a README figure re-quoted rather
   than a count I derived.

3. **"armature is the handle"** — the third card in "The problem." It is the only card on the
   page that states what armature *does* rather than what it intends, and it ends *"That is the
   idea. Whether it holds is the thing this repo exists to find out."* The hedge is in the same
   card as the claim. Whether that is enough separation is a judgment, and it is the Director's.

---

## 7. Not done, per the spec's out-of-scope

Translations · logo and brand assets · shipcheck · the full treatment · npm or PyPI publishing ·
the marketing-site sync · screenshots of generated output · any "getting started" or install
path · any claim about armature's capability.

**Also not done, and stated because it was not asked for either way:** the work is committed
locally and **not pushed**. The repo is public, so pushing puts the page in front of strangers,
which is the exact thing this session's governing rule is about. That is the Director's call.

## 8. Reproducing this

```bash
cd site && npm ci && npm run build && npm run preview
```

Then `http://localhost:4321/armature/`.
