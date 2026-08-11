# S02 step 3 — HALTED on a gate before the first line of tool code

**Seat:** executor · **Written:** 2026-08-10, after the measurement, before any extraction ·
**Ruling being executed:** [S02-step2-ruling.md](S02-step2-ruling.md) ·
**Credits spent: 0** · **Gates G1–G5: all still `NOT YET RUN`**

The ruling unblocked steps 3–5 under four build items. **Item (c) — "fix the arc derivation
generically to the `E\d\d` prefix" — was measured against facet before it was built, and it does
not hold.** This document reports it with its evidence and stops, per the executor rule that a
fired gate is never improvised past.

Two other findings ride along: a falsified premise about the repo (fixed, because its fix is
unambiguous and ruled), and an interaction between two ruled items that neither one shows alone.

---

## 1. ⚑ THE GATE — the ruled arc rule collides on facet's primary key, 7 times

`rulings` is declared `PRIMARY KEY (arc, number, kind) WITHOUT ROWID`
(`facet_index.py:1395–1402`). Under the ruled derivation, two of facet's ruling documents merge
into one arc and their rulings are the same keys:

| arc | documents merged | rows | colliding keys |
|---|---|---|---|
| `E08` | `E08-director-canon-ruling.md` + `E08-ruling-gate0.md` | **0** + 35 | **0** |
| `E10` | `E10-offsurface-ruling.md` + `E10-ruling.md` | **13** + **12** | **7** — rulings 1, 2, 3, 4, 5, 6, 7 |

**Consequence: facet's `build()` raises `IntegrityError` and no index is produced.** That is not
one gate failing — G1, G2, G3 and G4 all fail at the same point, because each of them needs a
facet index to exist first.

### The ruling's own justification is falsified by the same measurement

> *"⚠ And this is a generic fix, not a repo-specific one — facet has `E08-ruling-gate0.md` and the
> same collapse applies there."*

Measured: **the E08 collapse is harmless precisely because `E08-director-canon-ruling.md` parses to
zero rows.** There is nothing there to collide. The E08 case is safe *by an accident of that
document carrying no numbered rulings*, and it was generalised to E10, where the accident does not
hold. One merge is free; the other is a primary-key failure.

### The record warned about this in advance, in writing, twice

`ruling_documents()`'s docstring, written before this extraction:

> *"`E10-offsurface-ruling.md` must stay its own arc. Keyed on the E-number alone it would merge
> into `E10`, and twelve rulings and seven rulings would collide on numbers 1–7 — a primary-key
> failure, not a quiet miscount."*

And `tests/test_t24_the_e10_offsurface_collision_is_the_reason` asserts exactly this, with a failure
message naming the same mechanism. **That test is not narrowable.** Under G2 a test that must change
is named with its reason and never edited to go green; this one would have to be *deleted*, and what
it protects is a real invariant, not a convention.

I did not classify this correctly in step 2 either. I filed `RULING_DOC_RE` as **G/R** and wrote
that the arc rule "fragments armature's E02 into four arcs" — true, and I framed it as a labelling
problem. **It is a uniqueness constraint, and I should have said so.** The step-2 report named the
symptom and missed the mechanism that makes it load-bearing.

## 2. ⚑ The two ruled items are individually plausible and jointly fatal

This is the finding neither item shows on its own, and it is why the arc question cannot be re-ruled
in isolation from the header question.

**On armature today the collapse is safe — 0 collisions.** Measured:

| arc | documents | rows each | colliding keys |
|---|---|---|---|
| `E02` | bridge, canon, closing, halt | **0**, **0**, 9, **0** | **0** |
| `E01`/`E03`/`E04`/`E06` | one document each | 0 / 12 / 12 / 10 | 0 |

It is safe **for the same accidental reason E08 is safe**: three of the four E02 documents parse to
zero rows, because they use `## N. RULING — …` and `RULING_HDR` does not match it.

**And the ruling's answer 3 removes that accident.** Ruling-header patterns become a config list
specifically so armature's second form parses. The moment both ruled items are implemented together:

| arc | number | claimed by |
|---|---|---|
| `E02` | 1 … 7 | `E02-bridge-ruling.md`, `E02-closing-ruling.md`, `E02-halt-ruling.md` |

**7 collisions on armature, from three documents at once.** Answer 2 makes the arc coarser; answer 3
makes more documents produce rows; each is defensible alone and together they guarantee a
primary-key failure in *both* repos.

## 3. Premise falsified — the repo did not exist. Fixed, and reported.

> *"Repo-first still binds: `mcp-tool-shop-org/record-index` exists, `origin` correct, `main`
> default, scaffold pushed before any tool code."*

Measured at resume: `gh repo view mcp-tool-shop-org/record-index` → **`Could not resolve to a
Repository`**. Also absent under `mcp-tool-shop`; `gh search repos` returns `[]`; **`record-index` is
not on PyPI** (HTTP 404). The Trusted-Publisher claim is not necessarily wrong — the studio's
documented bootstrap configures TP against a package that does not exist yet — but no repo existed
under either account.

Repo-first says *if any fail, STOP and fix immediately*, and this fix is unambiguous: the name is
Director-ruled and settled, the org is ruled, and creating it blocks nothing else. **Fixed:**

* `https://github.com/mcp-tool-shop-org/record-index` — **PUBLIC**, matching every org tool repo
  including facet and the sibling `comfy-preflight`
* default branch `main`, `origin` correct, local clone `E:/AI/record-index`
* scaffold pushed at `a6bf23d` — README, LICENSE (MIT, copied from facet), `.gitignore`
* **no tool code**, which is the point of the rule and also correct while a design gate is open

## 4. Also measured: armature's record moved again

`docs/experiments/` is now **27 files** (24 at step 2, 20 at dispatch), and `E04-closing-ruling.md`
now exists carrying **12 rulings** — it did not at step 2. The ruling's own restatement (41 `## Ruling
N` across four closing rulings) is already behind. Stated so nothing downstream quotes a fixed number
for a record that is moving under two live seats.

## 4b. ⚑ facet's seat is live again — step 4's precondition no longer holds

The dispatch's sequencing step 1 recorded facet as free: *"The E32 seat is closed (the Director's
word). facet's tree is free."* That was true at step 2 and **is not true now.**

Observed during this session, without touching anything: `tools/diagnostics/e32_route_preprocess.py`
appeared modified in facet's working tree at 22:39:13, then cleared. Re-checked: facet's **HEAD moved
`ec6b33d` → `16605ae`** at 22:43:12 — *"CI repair: a tool that could not answer `--help` without a
GPU stack"*, 1 file, +5/−1. facet is clean and level with `origin/main` at the new HEAD.

I did not write, commit or delete it — the transient ` M` was that same file's mtime moving under
git's stat cache while a facet seat was mid-commit; its content re-hashed identical and the flag
cleared on the next status.

**This is load-bearing for step 4, which writes into facet's tree.** The dispatch's own rule:
*"Before touching facet at all, confirm with the Director that its seat is closed; a write into a
live executor's tree is the failure this project has paid for four times today."* That confirmation
was given for the state at step 2 and does not carry to a tree that has since taken a commit from
another seat. **Step 4 needs it again.**

Also: the seat that just committed touches `tools/diagnostics/`, which this dispatch put explicitly
**out of scope** (`instrument_census.py` and its population stay in facet). The two do not collide on
a file — but they are both in one tree, and that is the condition the rule names.

## 5. What was NOT done, and why

Items (a) lift the twelve inline sites, (b) split conventions from mechanism, (d) unrecognised-input
counts — **not started.** All three are written *into the conventions config schema*, and arc
derivation is a field of that schema whose type is exactly what is in question: tool constant, or
declared value. Building the schema around an unruled central field is building on a falsified
premise, which is the thing this repo's discipline exists to prevent. **No parameter was changed and
re-run to get past the gate.**

## 6. What the ruling has to decide

Stated as options with their measured consequences. This seat does not choose.

1. **Keep the stem derivation** (`E10-offsurface`, `E02-bridge` stay distinct arcs). Zero collisions
   in both repos. Costs: armature's E02 remains four arcs, which the ruling called "simply wrong",
   and the `## N. RULING —` documents can then be admitted safely by answer 3.
2. **`E\d\d` prefix + make the arc/number pair unique some other way** — e.g. admit the document
   stem into the primary key as a fourth column, or namespace `number` by document. Gets the ruled
   arc semantics; changes the `rulings` schema, every anchor built from `(arc, number)`, and
   `record_get`'s addressing. Not a small change and G3 cited numbers ride on it.
3. **`E\d\d` prefix + renumber the record** — forbidden by the dispatch's own rule against editing
   the record to fit the tool. Named only to close it.
4. **Arc derivation becomes a declared convention** (facet declares stem, armature declares prefix)
   — but note this reverses the ruling's "Class B resolves toward generic", and on armature the
   prefix declaration still collides once answer 3 lands.

**A dependent question either way:** if arc derivation and ruling-header patterns are ruled
separately again, the interaction in §2 recurs. They want ruling together.

---

## Gates

| gate | state |
|---|---|
| G1 facet four-leg verify 19/19 on a scratch db | **NOT YET RUN** |
| G2 facet's 7 index/record test files pass unchanged | **NOT YET RUN** |
| G3 facet's cited numbers reproduce | **NOT YET RUN** |
| G4 `record_build` writes db + certificate as a pair, `record_health` reads SERVING | **NOT YET RUN** |
| G5 armature's first index builds and verifies | **NOT YET RUN** |

**Untouched:** facet's tree is clean and level with origin at `16605ae` — **moved by its own seat
during this session, not by me** (§4b). No armature document was edited — E02-canon parsing to zero
is reported in §2, not repaired. No other seat's tree was written to; the E04 and E06 seats are at
`540da16` and `81a4518`.
