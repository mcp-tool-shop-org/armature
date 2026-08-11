# S02 — extract facet's record index into a shared tool, and give armature one

**Seat:** executor · **Dispatch written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director ratified the form 2026-08-10** ("Extract to shared tool") · **Credit ceiling:
ZERO — every stage is local.**

---

## What this is, and the ruling that already governs it

A standing ruling from **2026-08-08** placed facet's record index **in facet**, and stated the
extraction condition in as many words:

> *"Extraction is **GATED, not foreclosed**: the index extracts when **a second repo adopts the
> conventions** (none exists — measured, 146 local dirs + this store, 11 convention files all in
> facet)."*

**armature is now that second repo**, and the gate's condition is met by measurement rather than by
assertion:

| convention | armature |
|---|---|
| `docs/experiments/` with `E\d\d-` documents | **20 of 20 files match** |
| ruling docs matching `^E\d\d-.*ruling.*\.md` | **6** |
| `## Ruling N` headers | **20** |
| `CLAUDE.md` as the law book · `HANDOFF.md` | both present |

The same ruling names the served surface — **`record_query` / `record_verify` / `record_build`** —
and ratified a build order in which the index is **first**.

## Why extraction rather than a copy

Measured at dispatch time: `tools/facet_index.py` is **2,462 lines with 24 mentions of "facet"**, and
it already detects a record repo generically — `RECORD_MARKERS = ("CLAUDE.md", "docs/experiments")`
— with `resolve_repo()` already generalised for wheel installs. **The tool was built to be
extracted.** This is a parameterisation, not a rewrite.

And the alternative is a recorded mistake at scale: facet's own law book records **five hand-copies
of one background-model function living under four different names**, invisible to a name-based
grep for months. Forking 4,448 lines into a second repo is that error with three more zeros.

## Scope — what is in, what is out, and why

**IN:** `tools/facet_index.py` (the index and its four-leg verify) and `tools/record_mcp.py` (the
served surface and the certificate writer).

**OUT — `tools/instrument_census.py`.** It censuses `tools/diagnostics/`, a **facet-specific
population**, and its axes encode facet's own instrument conventions. It stays in facet. Naming it
here so nobody has to guess whether the omission was an oversight.

**OUT — armature's content.** This dispatch builds the tool and produces armature's **first** index.
It does not edit a single armature experiment document to make it parse better. **If armature's
record does not parse, that is a finding about the tool or about our conventions, and it is
reported — not repaired by rewriting the record.**

## ⚠ The central design question — measure it before extracting

Some of facet's parsers are generic and some encode facet's own history. Two examples found at
dispatch time: `PAID_RE = re.compile(r"\b(E0[1-9]|E1[0-5])\b")` — *which experiments paid for a
law* — is a facet fact, not a convention. `DB_REL = "docs/index/facet.db"` is a repo value.

**The first task is an enumeration, not a refactor: go through the module and classify every
constant and regex as GENERIC (the convention) or REPO-SPECIFIC (this repo's values).** Report that
classification **before** moving any code. The generic half becomes the tool; the repo-specific half
becomes a per-repo conventions config that facet and armature each supply.

**A classification is a measurement here.** Getting it wrong in the generic direction bakes facet's
history into a shared tool; getting it wrong in the repo-specific direction gives armature knobs it
should not have.

## Placement and naming

* **Repo:** a new repo under **`mcp-tool-shop-org`** — tool repos go to the org, per the standing
  canonical-ownership rule. **Repo-first is a hard rule:** the GitHub repo exists, `origin` is
  correct, default branch `main`, and a scaffold commit is pushed and visible **before any tool code
  is written.**
* **Distribution:** Python, so PyPI. facet already ships `facet-mcp`, so the packaging pattern is
  in-house and established.
* **Name:** proposed **`record-index`**. ⚠ **The name is a Director decision** — surface it and get
  a yes before the repo is created, because a repo name is expensive to change and an OIDC Trusted
  Publisher is configured against it.

## Sequencing — load-bearing, and it is not negotiable

1. **facet pushes its 4 unpushed commits first.** Nothing in this dispatch starts until facet's
   `origin/main` equals its local `HEAD`. Extracting from a tree whose record is not published is
   how a migration loses an unpublished fix.
2. **Enumerate and classify** (the section above). **Report and stop for a ruling.** Do not extract
   on your own classification.
3. **Build the tool** in its own repo, with tests.
4. **Migrate facet** to consume it, and pass every gate in the next section.
5. **Adopt in armature**, and build armature's first index.

**Steps 3–5 do not begin until step 2 has been ruled on.** This is the step where a wrong call is
cheapest to fix and most expensive to discover later.

## Gates — the migration's acceptance conditions

facet's index is a **certified, governed artifact under 7 test files** (`test_t01_index_verify`,
`t19`–`t22` record_mcp, `t24_index_parsers`, `t62`). That is the regression net, and it is a real
one.

* **G1 — facet's four-leg `verify` passes at 19/19** on the extracted tool, against a **scratch
  `--db`**. Any leg below that is a **halt**, reported with its evidence.
* **G2 — facet's 7 index/record test files pass unchanged.** A test that must change is **named,
  with the reason, in the report** — never edited quietly to go green. Narrowing a test to make a
  red gate green is forbidden.
* **G3 — facet's cited numbers still reproduce.** Its own law: *a cited number must still reproduce
  from the tool at HEAD.* Prove the extraction non-perturbing, or carry an anchor that reproduces
  each cited number, **in the commit that makes the change**.
* **G4 — facet's committed index and certificate regenerate to a verifying state.** ⚠ **Use
  `record_build`, not `facet_index.py build`** — E32 Ruling 15 measured that `facet_index.py verify`
  **does not write the certificate** (`write_certificate` lives at `record_mcp.py:499`, called only
  under `record_build`), so build-then-verify leaves a fresh db beside a stale cert. The pair moves
  together or not at all. Confirm `record_health` reads **`SERVING`** afterwards.
* **G5 — armature builds its first index and verifies**, and its db + certificate land as a pair in
  `docs/index/`.

**A gate that fires halts the session and is reported with its evidence.** Never change a parameter
and re-run to get past one.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | `facet_index.py` is 2,462 lines with 24 "facet" mentions and generic `RECORD_MARKERS` | **MEASURED** at dispatch time |
| 2 | armature's 20 experiment docs match the conventions the index parses | **MEASURED** at dispatch time (counts in the table above) |
| 3 | facet has 7 index/record test files | **MEASURED** |
| 4 | `write_certificate` is only called under `record_build` | **MEASURED** — E32 Ruling 15, `record_mcp.py:499` and `:931` |
| 5 | The generic/repo-specific split is cleanly separable | **ASSUMED — and step 2 exists to test it.** If it is not cleanly separable, that is the finding and the session halts for a ruling rather than forcing a split |
| 6 | armature's record parses without editing armature's documents | **ASSUMED** — if it does not, report it; do not rewrite the record to fit the tool |

## ⚠ Concurrency — three trees are live

* **`E:/AI/armature-E04`** — an E04 seat, spending credits.
* **`E:/AI/armature-E06`** — an E06 seat, spending credits.
* **`E:/AI/facet`** — an E32 seat may still hold it, and it has 4 unpushed commits.

**You work only in your own worktree**, and in the new tool repo. **Never write into another seat's
tree — not a file, not a commit.** Before touching facet at all, confirm with the Director that its
seat is closed; **a write into a live executor's tree is the failure this project has paid for four
times today.** If files appear in your tree that you did not write: **report them, do not commit
them, do not delete them.** Count surfaces and any pinned number two seats both move are the
advisor's to reconcile — name the collision and touch nothing.

## Report

The classification table from step 2 first, then the gate verdicts with evidence, then what
armature's first index actually contains and anything in armature's record that failed to parse. A
gate that did not run is written **NOT YET RUN**. **No judgement words** — do not call the
extraction clean, verified, or done; report what the gates returned.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | Every step is a recorded command; the extracted tool is version-pinned by both consumers. Not 3 — no lock file across the two repos yet, which is a real remaining gap named rather than hidden. |
| ANDON_AUTHORITY | **3** | G1–G5 each halt on failure; step 2 halts for a ruling by construction, before the expensive half begins. |
| NAMED_COMPENSATORS | **3** | Every write is a new repo or a new file, plus one migration of facet's `tools/` which is **reverted by `git revert` on a pushed commit** — hence the sequencing rule that facet publishes first. Zero credits, nothing external, no publish in this dispatch. |
| DECOMPOSE_BY_SECRETS | **3** | The whole dispatch **is** a decomposition by secrets: the generic convention parser separates from each repo's own values. That is Parnas exactly, and step 2 is the module-boundary decision. |
| UNCERTAINTY_GATED_HUMANS | **3** | Step 2 stops for a ruling at the point of maximum uncertainty and minimum cost; the repo name stops for the Director before anything is created. |
| EXTERNAL_VERIFIER | **2** | Better than usual here: facet's 7 existing test files and its 19/19 verify were written **before** this extraction and are not under the extractor's control, so they are a genuine independent check. Not 3 — still not a different model family. |

**16 / 18.**
