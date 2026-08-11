# S02 step 2 — the generic / repo-specific classification. HALTED FOR A RULING.

**Seat:** executor · **Written:** 2026-08-10, after the enumeration, before any extraction ·
**Spec:** [S02-record-index-extraction.md](S02-record-index-extraction.md) · **Credits spent: 0**
(every measurement below is local)

**Steps 3–5 have not begun.** No tool code is written, no repo is created, `facet/` is untouched.
This document is the step-2 deliverable and the session stops on it.

---

## 0. Prediction, and its honesty disclosure

The dispatch does not require a numeric prediction for a classification task, and **I registered no
prediction before measuring — so nothing here is blind, and I am not back-filling one.** What I can
disclose precisely:

* I read the constant list and armature's file listing **before** running the probe, so the three
  `FileNotFoundError` sites and the mixed ruling-header shape were **expected, not discovered**.
* Two results were **not** anticipated at the time the probe was written: that 27 of armature's 31
  parsed rulings come back with `verdict=None`, and that `parse_artifacts` silently drops
  armature's video artifacts rather than erroring.

## 1. Premises of my own dispatch, re-measured

The law binds hardest on the premises of one's own spec, so each was re-measured rather than
carried.

| # | dispatch premise | re-measured | result |
|---|---|---|---|
| 1 | `facet_index.py` is 2,462 lines | 2,462 newlines (116,812 bytes) | **holds** |
| 1 | …with 24 mentions of "facet" | 25 case-sensitive, 27 case-insensitive | **off by one to three** — restated, not disputed |
| 1 | `RECORD_MARKERS` detects a record repo generically | `is_record_root("E:/AI/armature-S02")` → `True` | **holds** |
| 2 | armature: 20 of 20 `E\d\d-` docs, 6 ruling docs, 20 `## Ruling N` | now **24 of 24**, **7** ruling docs, **31** `## Ruling N` | **the record moved since dispatch** (E05/E06 seats). Direction unchanged |
| 3 | facet has 7 index/record test files | 7 files, 1,984 lines total | **holds** |
| 4 | `write_certificate` only called under `record_build` | not re-measured this step — carried from E32 Ruling 15 | **NOT YET RUN** |
| 5 | the split is cleanly separable — **ASSUMED** | see §5 | **holds with three named exception classes** |
| 6 | armature's record parses without edits — **ASSUMED** | see §6 | **does not hold as written** — and the failure is in facet's *file lists*, not in armature's prose |

**Also measured, and load-bearing for step 3:** `mcp-tool-shop-org/record-index` **does not exist
yet** (`gh repo view` → `Could not resolve to a Repository`). Repo-first is unsatisfied, as expected
at this point in the sequence.

---

## 2. The classification — 62 module-level constants and regexes in `facet_index.py`

Verdicts: **G** = generic (the convention or the mechanism) · **R** = repo-specific (this repo's
values) · **G/R** = generic shape carrying a repo-specific rule or list, the class §5 argues is real.

### G — generic: these are the tool

| # | name | line | why generic |
|---|---|---|---|
| 1 | `HERE` | 69 | module directory; runtime fact |
| 2 | `REPO` | 154 | resolver output |
| 3 | `RECORD_MARKERS` | 111 | `("CLAUDE.md", "docs/experiments")` — measured true on armature unchanged |
| 4–8 | `EXIT_OK/USER/RUNTIME/PARTIAL/REFUSED` | 207–229 | the studio's operator contract, not a record fact |
| 9 | `DEBUG_HELP` | 281 | CLI help text |
| 10 | `DASH` | 572 | em/en/hyphen class — typography |
| 11 | `BOLD_LEAD` | 573 | `^\*\*` — markdown |
| 12 | `DATE_RE` | 605 | ISO-8601 |
| 13 | `SECTION_HDR` | 672 | `^(#{2,3}) +` — markdown |
| 14 | `NUM_RULE` | 890 | `^(\d+)\. +\*\*` — markdown list |
| 15 | `LIST_ITEM` | 891 | markdown list |
| 16 | `LIST_LAW` | 895 | markdown list opening in bold |
| 17 | `CLASS_LABEL` | 1157 | leading-capital label; the pattern is generic — **but its only caller reads `PROFILE_FILES`, which is R** |
| 18 | `SKIPPED_CROSSREFS` | 758 | empty accumulator (see §7 observation 3) |
| 19 | `SCHEMA` | 1394 | the table ontology; empty tables are legal SQL |
| 20 | `STOPWORDS` | 1753 | the source comment states it is not derived from the seeded set; English function words |
| 21 | `RELEASED_RE` | 1824 | `^## \[\d+\.\d+\.\d+\]` — Keep-a-Changelog |
| 22 | `AMBIGUOUS_SUFFIX` | 1903 | English hedges |

### R — repo-specific: these are facet's values

| # | name | line | the facet content, and what armature measured |
|---|---|---|---|
| 23 | `DB_REL` | 70 | `docs/index/facet.db` — named in the dispatch |
| 24 | `DB_ENV` | 78 | `FACET_INDEX_DB` — brand; T32 pins it against `record_mcp`'s copy |
| 25 | `TOPICAL_RULING_FILES` | 412 | 5 named facet documents (E01/E02/E06/E07/E08) |
| 26 | `PROFILE_FILES` | 483 | `profiles/{beast,character,ship}.json` — **armature has no `profiles/`; `parse_decisions` raised `FileNotFoundError`** |
| 27 | `PROSE_FILES` | 486 | 8 facet paths — **5 absent in armature; `parse_prose` raised `FileNotFoundError` on `docs/context-architecture.md`** |
| 28 | `SWEEP_EXTRA` | 529 | `CHANGELOG/SHIP_GATE/SCORECARD/SECURITY.md` — **none present in armature**; guarded by `os.path.exists`, so no crash |
| 29 | `KICKOFF_DOC_RE` | 429 | `^E\d\d-.*kickoff.*\.md$` — **0 matches in armature**; armature's dispatches are `docs/dispatches/S\d\d-*.md` |
| 30 | `RULING_HDR` | 658 | `^## Ruling (\d+)` — **matches 3 of armature's 7 ruling documents.** The other 4 write `## N. RULING — …` and parse to **zero rows** (§6) |
| 31 | `ADDENDA_HDR` | 659 | `## Post-ingest addenda` — facet E11 only; **0 in armature** |
| 32 | `AMEND_HDR` | 660 | `> ### Amendment N (` — facet E08 only; **0 in armature** |
| 33 | `SUB_RULING` | 669 | `^\*\*Nx <space> dash` — **0 in armature under any dash spacing tested** |
| 34 | `SUB_CLOSURE` | 670 | `^\*\*Nx-CLOSED` — **0 in armature** |
| 35 | `HANDOFF_HDR` | 671 | `## Session handoff` — **0 in armature**; armature's dispatch record is `HANDOFF.md`, a different shape |
| 36 | `SUPERSEDE_RE` | 676 | verbs directed at `Ruling\|Amendment N` — facet's object nouns |
| 37 | `SUPERSEDE_TITLE_RE` | 681 | same |
| 38 | `VERDICTS` | 832 | 18 capitalised words — **8 appear in armature**; armature also uses `ADMISSIBLE`, which is absent from the list |
| 39 | `PAID_RE` | 892 | `\b(E0[1-9]\|E1[0-5])\b` — named in the dispatch. **Measured failure mode: silent.** All 38 armature laws parsed with `paid_for_by = NULL`; no error anywhere |
| 40 | `EXP_ROW` | 981 | the experiments-README table row — **armature has no `docs/experiments/README.md`; `parse_experiments` raised `FileNotFoundError`** |
| 41 | `ARTIFACT_RE` | 1196 | extension alternation `glb\|png\|npy\|jsonl\|json\|obj\|ply\|ps1\|sh` |
| 42 | `ARTIFACT_KIND` | 1208 | the same 9 extensions → kind. **armature's record carries `.mp4` ×3 and `.mkv` ×3 with no entry, so they are dropped silently — in the repo whose product is video** |
| 43 | `STATUS_WORDS` | 1200 | 5 house status words |
| 44 | `PHENOM_PATTERNS` | 1271 | 7 naming verbs — **0 of 7 fire anywhere in armature's record; `parse_phenomena` returned 0 rows** |
| 45 | `SEEDED` | 1574 | 18 facet questions with facet anchors |
| 46 | `COUNT_CHECKS` | 1666 | 21 legs, every one naming a facet file and arc |
| 47 | `CURRENT_STATE` | 1796 | 5 facet paths; 2 exist in armature |
| 48 | `CURRENT_STATE_DIRS` | 1803 | `docs/handbook/` absent in armature; `site/src/content/docs/` present |
| 49 | `HISTORICAL_DIRS` | 1805 | `docs/research/` absent in armature |
| 50 | `BANNERED` | 1806 | `docs/advisor-kickoff.md` — absent in armature |
| 51 | `CURRENT_STATE_EXTRA` | 1825 | 2 facet files with facet reasons |
| 52 | `HISTORICAL_EXTRA` | 1829 | 1 facet file with a facet reason |
| 53 | `CLAIM_FAMILIES` | 1883 | 7 phrasings over facet's object nouns — **0 of 7 have a site in armature** |
| 54 | `CLAIM_SHAPED` | 1912 | same nouns |
| 55 | `BANNER_RE` | 1807 | `SUPERSEDED` — one house word |
| 56 | `SPLIT_AT_RELEASE` | 1823 | `CHANGELOG.md` — absent in armature |

### G/R — the shape is generic, the rule or list inside it is not

| # | name | line | the split |
|---|---|---|---|
| 57 | `RULING_DOC_RE` | 382 | the **glob** is generic and found all 7 armature ruling docs. The **arc-derivation rule beside it** (`re.split(r"-?ruling", fn)`, line 405) is facet's: it exists so `E10-offsurface` stays its own arc, and on armature it splits one experiment into **four arcs** — `E02-bridge`, `E02-canon`, `E02-closing`, `E02-halt` |
| 58 | `LAW_FILES` | 481 | `["CLAUDE.md"]` — a per-repo list whose facet and armature values coincide today |
| 59 | `SWEEP_EXTRA_DIRS` | 538 | `["site/src/content/docs"]` — a per-repo list; armature has this path, by the same Starlight convention |
| 60 | `ARC_RE` | 1917 | `\bE(\d\d)\b` — both repos use `E\d\d`, **but armature already runs a second series**: `docs/dispatches/S01-*`, `S02-*`, which this pattern cannot see |
| 61 | `CANDIDATES` | 1759 | 400 — generic mechanism, value calibrated on facet's corpus |
| 62 | `PHRASE_SLOTS` | 1768 | 3 — same; the source comment records the facet measurement that produced it |

---

## 3. What a constants-only sweep misses — facet values living inside functions

**This is the half where a copy-paste extraction would carry facet's history into the shared tool
without anyone seeing it**, because none of these has an upper-case name.

| site | line | the facet content |
|---|---|---|
| `verify()` — the `seq` list | 2226–2237 | 9 hardcoded facet arc bounds: `("E12","ruling",1,28)`, `("E04",…,28)`, `("E08","amendment",1,35)`, `("E11",…,7)`, `("E10",…,12)`, `("E15",…,8)`, `("E14",…,16)`, `("E16",…,7)`, `("E17",…,4)` |
| `verify()` — handoff coverage | 2256–2262 | `arc='E12'`, `range(1, 17)`, and the assertion `missing != [1]` |
| `verify()` — experiment coverage | 2264–2270 | `want = ["E%02d" % i for i in range(1, 16)]` — E01–E15, facet's span |
| `parse_experiments()` | 1033 | spec-file detector `(kickoff\|spec\|-E\d\|-the-\|-cover-\|-paint-\|-cull-\|-atlas-\|-facial-\|-texture-\|-environment-\|-dense-\|-context-)` — a list of **facet's own experiment filename fragments** |
| `parse_experiments()` | 1011–1012 | the corpus root `docs/experiments` and `^E\d\d[-.]`, inline |
| `_verdict()` | 1061 | `("ACCEPTED","RULED","IN FLIGHT","RUN AND RULED","STAGED","CLOSED")` — a **second, different** verdict vocabulary from `VERDICTS` at line 832 |
| `claims()` | 1949 | `if os.path.basename(rel).startswith("E15-"): continue` — facet's self-reference exclusion, hardcoded |
| `handoff_documents()` | 450 | arc derivation `fn.split("-", 1)[0]` — deliberately a **different rule** from `ruling_documents()`'s, for a facet-specific reason recorded in its own docstring |
| `classify()` | 856 | `\bDirector\b` — the authority word; coincides across both repos, still house vocabulary |
| `record_markdown()` | 502–504 | `["CLAUDE.md", "README.md"]` and the walk root `["docs"]` |
| `query()` | 2078 | `bm25(fts, 8.0, 1.0)` — column weights calibrated on facet's corpus |
| length floors and caps | 968, 1255, 1306, 1348, 1380, 873, 576 | `< 12`, `< 1200`, `[:4000]`, `< 40` ×2, `[:4000]`, `limit=240` — tuning values with no names |

## 4. `record_mcp.py` — the second file in scope

23 module-level constants; 69 case-insensitive "facet" mentions (against 25 in `facet_index.py`).
Classified at the same grain:

| verdict | names |
|---|---|
| **G** | `HERE`, `FROZEN`, `REPO`, `CODES`, `LEG_HEADERS`, `LEG_KEYS`, `DISCOVERY_HEADER`, `VERDICT_PASS`, `VERDICT_FAIL`, `DET_PREFIX`, `BLOCK_BOUNDARIES`, `GET_DEFAULT_LINES`, `GET_MAX_LINES`, `TRANSCRIPT_TAIL`, `STALE_NAMES`, `TOOL_ORDER`, `TABLES` |
| **R** | `CERT_SCHEMA` = `"facet-record-index-certificate/1"` — brand inside a **persisted artifact's schema id** · `DB_ENV` · `DB_DEFAULT` · `SERVER_VERSION` (pinned to four other declarations) · `FIX_COMMAND` (names `tools/facet_index.py`) · the server identity `name="facet-record"`, `title="facet record index"` |
| **G/R** | `FAIL_ROUTES` — 9 generic routes, **one of which is the literal `"E12 handoff coverage"`**: a facet arc string inside the MCP server's failure router · `BOUNDARY_NOTE` — a served string citing **"E15 Ruling 7"** · `REQUIRED_CONVENTIONS` — includes `"PROFILE_FILES"`, so **a record repo with no profiles fails the conventions gate outright** rather than serving an empty table |

Also: the module imports the conventions **by name** (`import facet_index`) and reaches through that
name at ~10 call sites.

---

## 5. Premise 5 — is the split cleanly separable?

**It separates, with three exception classes that the binary GENERIC / REPO-SPECIFIC question does
not have a slot for.** Naming them is the finding; deciding what to do with them is the ruling.

**Class A — generic mechanism, facet-calibrated value.** `bm25(8.0, 1.0)`, `CANDIDATES=400`,
`PHRASE_SLOTS=3`, and the seven unnamed length floors. These are not the convention and they are not
armature's values either: they are **the tool's own tuning, measured once on one corpus.** Calling
them generic ships facet's corpus statistics as a shared default; calling them repo-specific hands
armature knobs it has no measurement to set.

**Class B — generic shape, repo-specific derivation rule.** `RULING_DOC_RE` finds armature's
documents correctly and then labels them wrongly for armature: **one experiment becomes four arcs.**
The pattern and the rule beside it have to be configured together or the tool discovers the right
files under the wrong keys — and `handoff_documents()` uses a *deliberately different* derivation for
the same class of problem, so "the arc rule" is not even one rule inside facet.

**Class C — facet values with no upper-case name** (§3, twelve sites). A parameterisation that
extracts the constant block and leaves the function bodies alone would move ~56 named constants and
**silently retain nine facet arc bounds, two facet arc spans, a facet filename-fragment list and a
facet self-reference exclusion** inside the shared tool's verifier.

**And one structural finding that is not a classification at all:** `REQUIRED_CONVENTIONS` makes
`PROFILE_FILES` mandatory. Under the current code, a record repo that has no profiles registry is
not a repo with an empty `decisions` table — it is a `CONVENTIONS_INVALID` refusal. Whether the
per-repo conventions config carries **required** keys or **optional** ones is a decision the ruling
has to make before any code moves, because it determines whether the config is a set of overrides or
a full declaration.

---

## 6. Premise 6 — what facet's parsers actually did to armature's record

Method: `facet_index` imported from `E:/AI/facet/tools`, `facet_index.REPO` monkeypatched to
`E:/AI/armature-S02` — the same override facet's own suite uses. Read-only against both records;
the only write was a scratch db in the session scratchpad. **facet's tree was not modified.**

| parser | result |
|---|---|
| `resolve_repo` / `is_record_root` | **OK** — armature resolves as a record root unchanged |
| `ruling_documents` | **OK** — 7 documents, arc labels `E01`, `E02-bridge`, `E02-canon`, `E02-closing`, `E02-halt`, `E03-closing`, `E06-closing` |
| `handoff_documents` | **OK** — 0 documents |
| `record_markdown` / `sweep_markdown` | **OK** — 37 / 42 files |
| `parse_rulings` | **OK — 31 rows**, all from the 3 `*-closing-ruling.md` files. `E01-ruling.md` (8 sections), `E02-bridge-ruling.md` (7), `E02-halt-ruling.md` (7) and `E02-canon-ruling.md` (0) contributed **nothing**: they write `## N. RULING — …`, not `## Ruling N` |
| `parse_laws` | **OK — 38 rows** across 5 sections of armature's `CLAUDE.md`; `paid_for_by` NULL on all 38 |
| `parse_handoffs` | **OK — 0 rows**; the inverse ANDON did not fire (nothing to find) |
| `parse_artifacts` | **OK — 45 rows** (21 data, 20 render, 4 mesh); no video rows |
| `parse_phenomena` | **OK — 0 rows** |
| `parse_experiments` | **RAISED** `FileNotFoundError: docs/experiments/README.md` |
| `parse_decisions` | **RAISED** `FileNotFoundError: profiles/beast.json` |
| `parse_prose` | **RAISED** `FileNotFoundError: docs/context-architecture.md` |
| `build()` end-to-end | **RAISED** `FileNotFoundError: docs/experiments/README.md` |

`classify()` over the 31 parsed rulings: `ACCEPTED` ×2, `CONFIRMED` ×1, **`None` ×28** — 27 advisor,
1 Director.

**Premise 6 does not hold as written.** The important half of that sentence is *where* it fails:
**every failure is a facet file list pointed at a file armature does not have — not a failure to
parse armature's prose.** Under the dispatch's own rule this is reported and nothing in armature's
record is edited to accommodate it.

---

## 7. Observations recorded, not ruled on

1. **The dispatch's premise-2 counts have moved** (20→24 docs, 6→7 ruling docs, 20→31 `## Ruling N`)
   because two armature seats have been landing work since the dispatch was written. Direction
   unchanged; the numbers are restated here so nothing downstream quotes the stale pair.
2. **Two silent-empty failure modes** were measured, distinct from the three loud ones: `PAID_RE`
   (38 laws, all NULL) and `ARTIFACT_KIND` (6 video-file mentions dropped). A missing file raises; a
   non-matching vocabulary returns nothing and says nothing.
3. **`SKIPPED_CROSSREFS` (line 758) is a module-level list that is appended to and never cleared.**
   `verify()` calls `build()` three times in one process and `record_mcp` is long-lived. Stated as a
   measurement of the code's shape; no verdict attached, and it is out of this step's scope.
4. **`_verdict()` (1061) and `VERDICTS` (832) are two different verdict vocabularies** in one module,
   one named and one not.

## 8. Gates

| gate | state |
|---|---|
| G1 facet four-leg verify 19/19 on the extracted tool | **NOT YET RUN** — step 4 |
| G2 facet's 7 index/record test files pass unchanged | **NOT YET RUN** — step 4 |
| G3 facet's cited numbers reproduce | **NOT YET RUN** — step 4 |
| G4 committed index + certificate regenerate via `record_build`, `record_health` reads SERVING | **NOT YET RUN** — step 4 |
| G5 armature builds its first index and verifies | **NOT YET RUN** — step 5 |

---

## 9. What the ruling has to decide before step 3 begins

Stated as questions, not as recommendations — this seat does not rule.

1. **Class A (tuning values).** Do `bm25` weights, `CANDIDATES`, `PHRASE_SLOTS` and the seven unnamed
   length floors go into the tool as shared defaults, into the per-repo config, or into a third
   place that records which corpus calibrated them?
2. **Class B (arc derivation).** `RULING_DOC_RE` splits armature's E02 into four arcs. Is the arc
   rule a per-repo config value, and if so does armature keep the fragmentation or collapse to `E02`?
3. **`RULING_HDR`.** 4 of armature's 7 ruling documents use `## N. RULING — …`. Does the per-repo
   config carry a **list** of ruling-header patterns, or does the tool carry one and armature's four
   documents stay unparsed and reported?
4. **`REQUIRED_CONVENTIONS`.** Is the per-repo config a set of overrides with tool-side defaults, or
   a full declaration each repo must supply? This decides whether "armature has no `profiles/`" is an
   empty table or a refusal.
5. **Optional-corpus semantics.** Should a missing `PROSE_FILES` / `PROFILE_FILES` / experiments-table
   entry raise (as today) or be skipped and **reported**? Three parsers currently raise.
6. **Domain vocabularies** — `ARTIFACT_KIND`, `VERDICTS`, `STATUS_WORDS`, `PHENOM_PATTERNS`,
   `CLAIM_FAMILIES`. Per-repo, or a shared union? armature measured 0/7 on `PHENOM_PATTERNS` and
   0/7 on `CLAIM_FAMILIES`; whether those tables are *empty for armature* or *not armature's tables*
   is an ontology decision, not a parsing one.
7. **Brand in persisted artifacts.** `CERT_SCHEMA = "facet-record-index-certificate/1"` is written
   into every certificate. Renaming it under the shared tool is a schema change to an artifact
   `record_health` already reads.
8. **Scope confirmation.** §3's twelve inline sites are in `facet_index.py` but not in its constant
   block. Confirming they are in scope for the parameterisation is cheap now and expensive later.

**Nothing proceeds until these are ruled.**
