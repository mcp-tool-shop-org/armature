# S01 — advisor ruling

**Ruled 2026-08-10.** Report: [S01-report.md](S01-report.md). Dispatch:
[S01-public-surfaces.md](S01-public-surfaces.md).

**Verdict: accepted.** The surfaces are built, the build is green, the honesty rule held, and
the session found two defects in its own dispatch. Two rulings below are mine; one is the
Director's.

---

## 1. Two of my premises were falsified. Both were mine, and here is the measurement.

### 1a. "GitHub Pages deployment is unresolved across the org" — FALSE

I wrote that into the dispatch as a measured finding. It is not one. Measured at ruling time
across the whole org:

| | |
|---|---|
| repos in `mcp-tool-shop-org` | **89** |
| with Pages configured | **71** |
| of those, `build_type: workflow` | **71 — all of them** |

**facet — armature's direct upstream sibling — carries `ci.yml`, `pages.yml` and `release.yml`,
and serves HTTP 200 at `https://mcp-tool-shop-org.github.io/facet/`.** There is no ambiguity
org-wide and never was.

The mechanism of my error is the one this repo has recorded nine times: **I measured a
population of two and generalized to eighty-nine.** Worse than a small sample — `anchor` and
`ai-crucible` both happen to sit in the 18-repo minority that has no Pages at all, so I drew a
conclusion about deployment from two repos that do not deploy. The dispatch even stated the
evidence in a way that looked rigorous ("both have only `ci.yml`; the Pages API returned no
configured source"), which is what made it survive into a gate.

This is *check the population before you predict its density*, and it is the advisor's
recurring shape: **a check whose form assumed its answer.**

### 1b. "Mirror `E:\AI\anchor\site\` — follow anchor's shape exactly" — FALSE, and it would not
have built

Starlight ≥ 0.39.0 removed the `{ label, autogenerate }` sidebar shorthand that `anchor` and
`facet` both use. On the current 0.41 it is a build-stopping error, and the executor's first
build died on it. **My instruction to copy the reference implementation verbatim would have
produced a site that does not compile.**

The lesson generalizes past this repo: *a reference implementation is a claim about the
present, and it ages.* A frozen config in a sibling repo is exactly an inherited claim wearing
a fact's clothes. Ported forward: **the next repo that scaffolds a site should be given
anchor's *layout* as the pattern and the *current* Starlight docs as the API.**

⚠ **Consequence beyond armature:** `anchor` and `facet` carry configs that will not build on a
current Starlight. That is a real, dated finding about two other repos, filed here so it is not
lost. It is not armature's to fix.

### The executor's handling of both was correct and is the point of the discipline

Faced with a gate whose stated evidence it had just disproved, the session **did not build the
third workflow file.** It reported the collision and stopped. That is exactly right: *a gate is
not walked past because the reasoning behind it turned out to be wrong* — the gate is voided by
the person who owns it, in writing, which is what this document is. An executor that had
"helpfully" created `pages.yml` would have been wrong even though the outcome would have
matched this ruling.

## 2. RULING — `pages.yml` is approved. The two-file cap does not bind Pages deploys.

Mine to decide; it is an input-side implementation call.

The studio's GitHub Actions rule reads *"Max 2 workflow files per repo (e.g., ci.yml +
publish.yml)"*. Its stated purpose in that same rule set is **CI-minute cost control**, and its
worked example contemplates CI plus publish — it does not contemplate a Pages deploy. Against
that: **71 of 71 deploying repos in this org use a workflow build**, and the closest sibling
runs precisely `ci.yml` + `pages.yml` + `release.yml`.

A rule that every deploying repo in the org violates is not being enforced; it is mis-scoped.
The cap's intent is respected here because a Pages deploy gated to `site/**` is among the
cheapest jobs in the org.

**Adopt facet's `pages.yml` shape.** `release.yml` stays reserved for the PyPI Trusted
Publisher — its filename is authenticated by OIDC and cannot be repurposed (see
[publishing.md](../publishing.md)).

## 3. DIRECTOR'S GATE — enabling Pages and pushing

**Not mine.** Pages is not enabled on `armature` (the API returns 404), so enabling it is a
repo-settings change *and* the act that puts the page in front of strangers. The executor was
right to stop at it and right not to push. Publishing is the Director's call, and it stays
unmade until he makes it.

## 4. Accepted without change

- **The empty code-preview cards.** The house pattern's install/run strip is left blank, which
  leaves a visible gap under the hero versus `anchor` and `facet`. **That gap is the correct
  artifact.** A filled strip would be an install command for software that does not exist. The
  page looks less finished than its siblings because the product is less finished than theirs.
- **Copy cut for lack of grounding.** F2 dropped entirely (both groundedness checkers returned
  NOT_IN_ABSTRACT), F23 dropped (its own characterization is flagged unconfirmed in the
  grounding doc), no dataset named for Champ, no code-state counter. Every cut is correct, and
  cutting the most quotable control-signal result rather than softening it is the behaviour the
  rule was written to produce.
- **The license-map wording fix.** "Treated as banned" → "treated as NO until retrieved" is
  more accurate to the source and the executor checked the source before changing it.
- **The favicon 404.** `/armature/favicon.svg` 404s; so do facet's and shipcheck's on the live
  org site. Pre-existing, org-wide, and fixing it means authoring a brand asset. Out of scope
  for S01 — and now overtaken by events, since logo candidates exist as of this session.

## 5. Noted, minor — the channel list on the landing page

The executor flagged this as the claim it was least sure of: "How it works" step 2 lists
`depth, normal, mask, edge`, while F1 measured depth + normal + **semantic**.

**Ruling: defensible as written, provided it is never footnoted to F1.** The channel set is
armature's own design decision, recorded in the [E01 spec](../experiments/E01-control-sequence-exporter.md),
not a research finding — and the spec derives channel *ordering* from F1 while choosing the set
itself. The handbook's thesis page attributes F1 correctly. No change required; the flag was the
right instinct and the distinction is worth keeping in view.

## 6. Carried to the advisor — README staleness

`README.md` says "no code exists beyond scaffold." At HEAD that is still true — E01's `tools/`,
`tests/` and `specs/` are untracked — but it goes false the moment E01 commits. Corrected in
this ruling's commit to state that E01 is in flight, which is the honest present state.

The executor correctly left it alone. Two seats are live; **the shared surfaces are the
advisor's to reconcile**, which is the same rule I broke earlier today by staging E01's report
into an S01 commit with `git add -A`.
