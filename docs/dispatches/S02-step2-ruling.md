# S02 step 2 — ruling. The halt worked, my two-class framing was wrong, and the facet-ness is not in the constants.

**Seat:** advisor · **Ruled:** 2026-08-10 · **Dispatch:**
[S02-record-index-extraction.md](S02-record-index-extraction.md) ·
**Classification:** `S02-step2-classification.md` on `S02-run` · **Credits: zero**

## 0. The halt did its job, and the executor did the thing the dispatch asked for

Step 2 was written to stop at the point of maximum uncertainty and minimum cost. It stopped, with
no tool code written, no repo created, and all five gates `NOT YET RUN`. **That is the design
working.**

And the classification was **measured, not read**: facet's parsers were run against armature's
record with `facet_index.REPO` monkeypatched — the same override facet's own suite uses — read-only,
scratch DB. A classification arrived at by running the thing is a different object from one arrived
at by reading it, and the two silent failures below are the proof.

---

## Ruling 1 — ⚑ My two-class framing is FALSIFIED. There are three, and the third is the dangerous one.

The dispatch said: *classify every constant and regex as **GENERIC** or **REPO-SPECIFIC**.* Premise 5
marked clean separability **ASSUMED** and said the session halts if it does not hold. **It does not
hold, and the halt is correct.**

Measured, it separates into three:

* **Class A — generic mechanism, facet-calibrated value.** `bm25(8.0, 1.0)`, `CANDIDATES=400`,
  `PHRASE_SLOTS=3`, seven unnamed length floors. The *mechanism* is the convention; the *number* was
  fit to one corpus. Neither label in my binary fits.
* **Class B — generic shape, repo-specific derivation.** `RULING_DOC_RE` finds all seven of
  armature's ruling documents and then **labels them wrongly** — one experiment becomes four arcs
  (`E02-bridge`, `E02-canon`, `E02-closing`, `E02-halt`). The regex is generic; what it *derives*
  is not. And `handoff_documents()` uses a deliberately different rule, so **"the arc rule" is not
  one rule even inside facet.**
* **Class C — the twelve sites with no upper-case name.** Ruling 2.

**A binary that has no slot for "generic mechanism, wrong value" would have forced every Class A
constant into one of two wrong homes.** That is my error and it is the error the halt exists to
catch.

## Ruling 2 — ⚑ THE FINDING: the facet-ness is in function bodies, and my instruction could not see it

**Twelve facet-specific sites carry no constant name at all**, and my dispatch told the executor to
classify *constants and regexes* — an instruction that is blind to every one of them:

* inside `verify()` — **nine hardcoded arc bounds** (`("E12","ruling",1,28)` … `("E17",…,4)`),
  `arc='E12'` with `range(1,17)`, and `range(1,16)` as the experiment span;
* inside `parse_experiments()` — a spec-file detector that is **a list of facet's own filename
  fragments**: `-cover-|-paint-|-cull-|-atlas-|-facial-`;
* inside `claims()` — `startswith("E15-")`;
* a **second verdict vocabulary** in `_verdict()` that differs from `VERDICTS`.

The executor's sentence is the ruling:

> **A parameterisation that moves the constant block and leaves function bodies alone ships all of
> that into the shared tool invisibly.**

**Ruled: the twelve inline sites are IN SCOPE, and they are the most important part of the work.**
The dispatch's instruction is **corrected in place** — the unit of classification is not "constants
and regexes", it is **every site whose value is a fact about one repo**, wherever it lives. A shared
tool that hard-codes `E12`'s ruling count is not shared; it is facet with a different import path.

## Ruling 3 — ⚑ A law: a vocabulary mismatch is silent where a path mismatch is loud

Three failures were **loud** — `parse_experiments`, `parse_decisions`, `parse_prose` each raise
`FileNotFoundError` on a facet file armature does not have, and `build()` dies on the first.

**Two were silent, and neither was anticipated:**

* `PAID_RE` leaves **all 38 parsed armature laws with `paid_for_by = NULL`**;
* `ARTIFACT_KIND` has no video extension, so armature's **`.mp4` ×3 and `.mkv` ×3 are dropped** —
  **in the repo whose entire product is video.**

> **A missing file raises; a non-matching vocabulary returns nothing and says nothing.**

**Adopted as a law, and it governs the whole build:** a shared tool must **report what it did not
recognise**, not merely what it failed to find. An empty table and a table that silently discarded
six artifacts are indistinguishable at the call site, and only one of them is correct. Every
vocabulary in this tool gets an unrecognised-input count surfaced in `verify`.

This is the same family as *a check that silently skips is worse than one that cannot fail* — third
instance in two days, and the first found in a tool rather than a test.

---

## The eight questions, answered

**1 — Class A tuning values: shared, per-repo, or a third place?**
**Shared defaults, overridable, with the calibrating corpus named at the site.** They are mechanism,
so per-repo is wrong — nobody adopting this tool has evidence to tune BM25 with, and inviting them to
turn knobs they cannot evaluate is worse than a default. But shipping them *bare* hides that they
were fit to one corpus. Each carries a comment naming the corpus and date it was calibrated on. Not a
third config file — provenance at the constant.

**2 — Arc derivation, and does armature's E02 stay fragmented?**
**No. The arc is the `E\d\d` prefix, not the filename stem.** `E02-bridge`, `E02-canon`,
`E02-closing` and `E02-halt` are **one arc with four ruling documents**, and treating them as four
arcs is simply wrong. ⚠ **And this is a generic fix, not a repo-specific one** — facet has
`E08-ruling-gate0.md` and the same collapse applies there. Class B resolves **toward generic**: fix
the derivation in the tool, do not push it into config.

**3 — Ruling-header patterns: config list, or leave four armature documents unparsed?**
**The config carries a list of header patterns.** Two reasons: a shared tool that hard-codes one
header form breaks on the third repo as surely as on the second; and the convention is genuinely
plural in practice. **Verified by this seat:** armature's early ruling docs use `## N. RULING —`
(E01 ×2, E02-bridge ×1, E02-halt ×1), E02-canon uses **neither**, and the four closing rulings use
`## Ruling N`. That drift is **ours**.

**And separately — armature normalises going forward, and does NOT rewrite the closed documents.**
New rulings use `## Ruling N`. The four existing ones stay as written: rewriting the record to fit
the tool is exactly what the dispatch forbids, and they are closed rulings. E02-canon's zero is a
finding to report, not to repair.

**4 — Config: overrides-with-defaults, or full declaration?**
**Split, and the split is principled.** **Conventions are a FULL DECLARATION** — a repo must state
what its documents mean, because an overrides model ships facet's values as the silent default and a
second repo inherits facet's history by omission. That is precisely the failure Ruling 2 caught, and
this repo family has paid for silent inheritance repeatedly. **Mechanism (Class A) is
defaults-with-overrides**, per answer 1. You must declare what your repo means; you may inherit how
the search is tuned.

**5 — A missing optional corpus: raise, or skip-and-report?**
**Skip-and-report — and the report is surfaced in `verify`, not swallowed.** Per Ruling 3, a silent
skip is the failure mode. Both directions are reported: a **declared corpus that is absent**, and an
**undeclared corpus that exists**. Neither raises.
⚠ **And `REQUIRED_CONVENTIONS` making `PROFILE_FILES` mandatory is wrong for a shared tool** — it
turns "this repo has no profiles" into a `CONVENTIONS_INVALID` refusal. **Required-versus-optional
becomes a per-repo declaration; the tool has no opinion about which corpora exist.**

**6 — Domain vocabularies: per-repo or union?**
**Per-repo declaration, and a union is wrong.** A union would have facet's index claiming to know
about video and armature's about meshes. **And the load-bearing half of this answer is Ruling 3: an
artifact matching no declared kind is REPORTED, never dropped.** Per-repo declaration alone would not
have caught armature's six video files; per-repo declaration *plus* an unrecognised count would have
caught it on the first run.

**7 — `CERT_SCHEMA = "facet-record-index-certificate/1"`.**
**Rename it, bump the version, and accept both on read.** A schema id carrying one repo's name in a
shared tool is the same defect as the rest of this ruling. The migration is bounded and already
gated: the reader accepts `/1` and the new id; the writer emits only the new one; **facet's committed
certificate is regenerated in the migration commit — which G4 already requires**, via `record_build`,
db and cert as a pair. `record_health` reading the old artifact is handled by the dual-accept read.

**8 — Are the twelve inline sites in scope?**
**Yes. Ruling 2. They are the work, not an addendum to it.**

---

## Premise corrections — all accepted, and one is mine to own

* **Premise 2's counts are stale** (20→24 docs, 6→7 ruling docs, 20→31 `## Ruling N`) because the
  E05/E06 seats were landing work while the dispatch was being written. Direction unchanged.
  **Accepted, and the executor restating them so nothing downstream quotes the stale pair is exactly
  right.** They have moved again since — four closing rulings now carry 41 `## Ruling N` headers
  between them.
* **Premise 1's "24 facet mentions" measures 25 case-sensitive / 27 case-insensitive.** Mine, and it
  is the fourth counting error this seat has made in two days. The 2,462 lines holds exactly.
* **Premise 6 does not hold as written** — and *where* it fails is the finding: **every failure is a
  facet file list aimed at a file armature does not have, not a failure to parse armature's prose.**
  What parsed at probe time: 31 rulings, 38 laws, 45 artifacts, 0 handoffs, 0 phenomena, **and no
  armature document was edited.** That is the premise failing in the harmless direction, and the
  distinction is worth more than the premise was.
* **No prediction was registered before measuring, and the executor declines to back-fill one.**
  **Upheld.** A classification is not a hypothesis experiment; a back-filled prediction is a
  fabricated one, and refusing to write it is the honest call.

## What proceeds

**Steps 3–5 are UNBLOCKED**, under the three rulings above and the eight answers.

**The build order changes in one respect:** the extraction is no longer "move the constant block."
It is **(a)** lift the twelve inline sites into named, declared configuration, **(b)** split
conventions (full declaration) from mechanism (defaults with provenance), **(c)** fix the arc
derivation generically, and **(d)** give every vocabulary an unrecognised-input count that `verify`
surfaces. **(a)** and **(d)** are new since the dispatch and both come from this halt.

**The gates are unchanged** — G1 19/19 on a scratch db, G2 facet's 7 test files passing with any
change named, G3 cited numbers reproducing, G4 `record_build` writing db and cert as a pair, G5
armature's first index. All still `NOT YET RUN`.
