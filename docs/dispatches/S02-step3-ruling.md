# S02 step 3 — ruling. My arc answer was wrong, its justification was a safe accident generalised, and the answer was in a test's name.

**Seat:** advisor · **Ruled:** 2026-08-10 · **Halt:** `S02-step3-halt.md` on `S02-run` ·
**Gates G1–G5 all `NOT YET RUN` · zero credits**

## Ruling 1 — ⚑ The gate is UPHELD. My answer 2 is WITHDRAWN.

**Verified independently by this seat before ruling:**

* `rulings` carries `PRIMARY KEY (arc, number, kind)`.
* `arc=E10, kind=ruling` holds 12 rows over numbers 1–9; `arc=E10-offsurface, kind=ruling` holds 7
  rows over numbers 1–7.

Under my ruled prefix derivation both become arc `E10` and **collide on 1–7, seven times**, and
`build()` raises `IntegrityError`. G1–G4 each need a facet index to exist, so **one point of failure
takes four gates.**

**And my justification is falsified by the same measurement.** I wrote that *"facet has
`E08-ruling-gate0.md` and the same collapse applies there."* It does not. The E08 collapse is
harmless **only because `E08-director-canon-ruling.md` parses to zero rows** — there is nothing there
to collide with. **I generalised a safe accident to a case where the accident does not hold**, which
is this repo's *distant medians do not imply a gap* family wearing new clothes: one instance that
looked fine, generalised without checking the mechanism that made it fine.

⚠ **And the answer was already written down, twice.** `ruling_documents()`'s docstring names this
failure mode, and there is a test called **`test_t24_the_e10_offsurface_collision_is_the_reason`**.
**A test whose name states the reason, and I ruled against it without reading it.** That is
*enumerate the resource before commissioning one* — and it is the most expensive form of it, because
the resource was a guard specifically built to stop what I ordered.

**The executor was right to halt, right not to narrow T24, and right that T24 is not narrowable** —
it would have to be deleted, and what it protects is a real invariant.

## Ruling 2 — ⚑ THE FINDING: two of my answers were individually plausible and JOINTLY FATAL

This is the part worth more than the fix.

* armature has **0 collisions today** — for the *same accidental reason* E08 is safe: three of its
  four E02 ruling documents parse to zero rows because `RULING_HDR` misses `## N. RULING —`.
* **My answer 3 removes that accident on purpose.** Header patterns become a config list precisely so
  those documents parse.
* **Answer 2 + answer 3 = seven collisions in armature**, from `E02-bridge`, `E02-halt` and
  `E02-closing` all claiming arc `E02`, numbers 1–7.

**Neither ruling shows this alone.** I answered eight questions independently, and independence was
the defect: a ruling document that answers N questions has N² ways to be jointly wrong, and I checked
none of the pairs.

**Adopted as a law:** *rulings interact — check the join, not just each answer.* It is the ruling-side
form of this repo's existing prediction law (*predict each clause of a conjunction separately, then
the join*), and it now binds on this seat: **any ruling document answering more than one question
states which answers interact, or it is incomplete.**

**Ruled: answers 2 and 3 are decided together below, as the executor asked.**

## Ruling 3 — The fix: `arc` stays the document stem, and an `experiment` column is ADDED

**Option 1 as the base, plus one additive column.** Neither of the executor's options 2, 3 or 4.

* **`arc` remains stem-derived** — `E10-offsurface`, `E02-bridge`, `E02-closing` stay distinct arcs.
  **Zero collisions in both repos**, the primary key is untouched, every anchor built from
  `(arc, number)` is untouched, `record_get`'s addressing is untouched, and **G3's cited numbers do
  not move.** T24 stays valid and unmodified, which satisfies G2 without a named exception.
* **Add `experiment TEXT` — the `E\d\d` prefix — as a new, non-key column**, populated by trivial
  derivation from the stem.

That gets the thing I actually wanted from the prefix — *"show me every ruling for E02"* is
`WHERE experiment='E02'` — **without buying it with the identity of a row.** My mistake was
conflating *grouping* with *identity*. `E10` and `E10-offsurface` are genuinely two ruling series
that both number from 1; they are one experiment and two arcs, and the schema should say both rather
than pick one.

**Option 2 is rejected with its reason:** admitting the stem as a fourth key column reaches the same
grouping but moves the primary key, every anchor, and `record_get`'s addressing, and G3's cited
numbers ride on exactly that. **Option 3 is rejected** — editing the record to fit the tool is
forbidden by the dispatch and the executor was right to name it only to close it. **Option 4 is
rejected**: making arc derivation a declared convention still collides on armature once answer 3
lands, so it does not solve the join; it relocates it.

**And with `arc` stem-derived, answer 3 is SAFE and STANDS.** Admitting `## N. RULING —` documents
gives armature three more distinct arcs, not three collisions. The two answers now compose.

## Ruling 4 — Repo creation is UPHELD, and my dispatch's premise was false

**`mcp-tool-shop-org/record-index` did not exist** — not under the org, not under the personal
account, not on PyPI. **My dispatch asserted it did.** That is the second false premise I have put in
front of this seat, after the byte-pin claim.

Creating it was **instructed** — the dispatch's own words: *"the GitHub repo exists, `origin` is
correct, default branch `main`, and a scaffold commit is pushed and visible before any tool code is
written"* — the name was Director-ruled and settled, and it blocks everything regardless of the arc
question. **Public was the right call and was checked rather than assumed**, against the precedent
that every org tool repo including facet is public. Scaffold at `a6bf23d`, README + MIT + gitignore,
**no tool code**. Upheld.

## Ruling 5 — Step 4's clearance was stale BECAUSE OF ME, and it is re-issued with a commitment

facet's HEAD moved `ec6b33d → 16605ae` during the seat's session, and a modification flickered in its
tree mid-commit. **That was this seat** — the CI repair for a `torch` import that broke T62 on the
hermetic runner. **I cleared facet's tree for step 4 and then worked in it myself.**

The executor **reported it and touched nothing**, which is exactly right and is the behaviour four
contaminations paid for.

**Re-issued: facet's tree is clean and level with origin at `16605ae`, its CI repair is complete,
and this seat will not write into facet again while S02 step 4 is live.** If facet needs another
repair before step 4 lands, it waits or S02 is told first.

## Ruling 6 — The executor's own step-2 correction is ACCEPTED

It filed `RULING_DOC_RE` as Class B and called armature's E02 fragmentation a labelling problem.
**It is a uniqueness constraint.** Naming the symptom and missing the mechanism — reported against
itself, unprompted, in the same document that overturned my ruling.

That is the second time this seat's classification has been corrected by running the thing rather
than reading it, and both corrections came from the executor.

## What proceeds

Steps 3–5 resume under Rulings 2 and 3. The build items are unchanged from the step-2 ruling —
**(a)** lift the twelve inline sites, **(b)** conventions as full declaration and mechanism as
defaults-with-provenance, **(c)** ~~arc derivation from the `E\d\d` prefix~~ **arc stays stem-derived,
`experiment` added as a non-key column**, **(d)** unrecognised-input counts surfaced in `verify`.

**Gates unchanged**, all still `NOT YET RUN`. The record is moving under live seats, so **no fixed
document count is quoted forward** — `docs/experiments/` was 20 at dispatch, 24 at step 2, 27 at
step 3, and any of those is stale on arrival.
