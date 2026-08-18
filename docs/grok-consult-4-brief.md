# Grok build #4 — prompt-craft: the suite is 81% covered and caught none of the four defects we found this week

**2026-08-17, armature advisor seat.** Three for three. #3's chip was verified by re-running the
original defect rather than trusting the test: `pcraft gate` on a nonexistent path gives
`error[IO_GATE_INPUT]` and **exit 4**. Folded at `8d8ebc1`.

Your F8 recommendation went to the Director and he ruled: the four negations move to `optional`.
I implemented it, and the implementation is the reason for this round — see below. Folded at
`4541a1d`, suite **77**.

Your call on *why not Nagios 3* was better than my brief's suggestion, and I had it wrong. That
is three rounds running where the returned work corrected the dispatch.

*Everything below the line is the paste block.*

---

# Three for three. This round is about the tests, and the argument for it is that four real defects were all inside covered code.

## The evidence

Coverage, measured today: **81%**, 1332 statements, 252 missed. That number is not the problem
and raising it is not this round.

Four defects surfaced in this repo this week. **Every one was in code the suite executed.**

| # | defect | why coverage could not see it |
|---|---|---|
| 1 | `pcraft gate` on a nonexistent path exited 0, reporting on an image it never opened | the lines ran; the verdict was wrong |
| 2 | `_is_identity_atom` substring-matched `face`/`palette`/`sigil`, routing garment and species claims to identity repair | the function ran; the predicate was wrong |
| 3 | `_counts` read `severity is required **or** polarity is negate` — the `or` overrode severity, so an `optional` negation still blocked | the line ran on every gate evaluation |
| 4 | `_merge_must_not` had no fail-closed severity guard, so a character contract could silently relax a faction's `required` negation to `optional` | the function ran; the missing branch cannot be covered |

**Three of the four share one shape: a compound predicate whose second clause silently overrides
the first.** #2 and #3 are literally the same bug in two files. #4 is its absence-shaped twin — a
guard that was correct by construction until a schema field made it wrong, with nothing asserting
the invariant it had been getting for free.

Defect #3 nearly shipped as a cosmetic change: the schema gained `MustNot.severity`, the contracts
declared `optional`, the suite went green, and the atom still blocked. It was caught by writing a
fixture and then **deliberately reverting the fix to watch the fixture fail.** That is a
hand-rolled mutation test, and it is the technique this round is about.

Defect #4 was not caught by tests at all. It was caught by reading `loader.py` while scouting for
this brief.

## What to build this round — and argue the scope

**My call: an adversarial pass over the predicates, not a coverage climb.**

**1 · Mutation-test the decision sites.** For each predicate below, flip it — drop a clause,
invert a comparison, swap `and`/`or`, replace a severity check with `True` — and record whether
any test fails. A surviving mutant is a decorative test. Use a tool (`mutmut`, `cosmic-ray`) or
hand-roll it; the deliverable is **the list of survivors**, not a green run.

The eleven compound predicates in `core/`, measured today:

```
contract/compile_questions.py:58   if q.depends_on and q.depends_on in index
contract/loader.py:64             if contract.level == "faction" or contract.extends is None
contract/loader.py:108            if base_atom is not None and _SEVERITY_RANK[...] < _SEVERITY_RANK[...]
gate/harness.py:62                v.zone is Zone.FAIL and _counts(v)
gate/harness.py:65                v.zone in (UNCERTAIN, SKIPPED, NA) and _counts(v)
gate/harness.py:69                _counts(v) and v.score is not None
gate/harness.py:110               if q.depends_on and q.depends_on in verdicts
gate/harness.py:134               if tier == 1 and zone in (UNCERTAIN, FAIL) and 2 in verifiers
loop/retry_policy.py:53           inpaints <= 0 and reprompts <= 0 and rerolls <= 0
loop/retry_policy.py:90           if len(failed) > 1 and budget.reprompts > 0
synth/visual_inventory.py:75      if any(norm in tok or tok in norm for tok in allowed)
```

⚠ **`visual_inventory.py:75` is a bidirectional substring match** — the same shape as defect #2,
in a different file, still live. It decides whether a synthesized token traces to a depictable
atom, which is the guard the whole synthesizer rests on. `norm in tok or tok in norm` means a
one-character atom matches almost everything. Measure what it actually admits before deciding
whether it is a defect.

**2 · Close the latent `family_guard` hole.** `assert_distinct_families(gen, verifiers)` takes
`list[str]`. Given a bare string it iterates characters, none normalize to the generator's family,
and **the guard passes — including `sdxl` against `sdxl`, the one case it exists to refuse.** The
only production caller passes a proper list, so this is latent, not live. I found it by making the
mistake myself while verifying your round. A guard that cannot fail when misused belongs in the
round about guards that cannot fail.

**3 · ⚑ The identity sub-gate, and this is the one I would not cut.**
`domains/image/subdomains/sprite/identity_subgate.py` is at **38% coverage** — 45 statements, 28
missed — and it is not inert. It computes CLIP-I cosine between a reference plate and each rendered
view, requires a floor **and** low cross-view variance, and its failures **route to
reference-anchored inpaint**. Its `similarity` callable is injectable and explicitly mock-friendly,
so it is testable today with no GPU and no network. Nothing tests it.

Three things about it need answering, and the third is the important one:

- `floor = 0.55` and `max_variance = 0.05` are hardcoded defaults with no recorded calibration.
  What do they take when the arm does nothing, and when it works perfectly? If those are close,
  the threshold is not measuring the arm.
- It is a **`siglip2`-family verifier scoring output whose generator may also be SigLIP2-adjacent.**
  Does it pass its own `family_guard`? Nothing checks.
- Its docstring says it catches **"silhouette/palette drift."** This week's study-swarm returned
  StyleID (arXiv:2604.21689, citation-gated `supported`): identity encoders **"mistake changes in
  texture or color palette for identity drift."** So this sub-gate proposes to detect palette drift
  *with an identity metric* — the exact conflation the literature documents, and the exact
  conflation you found in `_is_identity_atom` and fixed.

**The governing ruling, which is not mine and not yours:** the Director has ruled that a gate on
**nameable attribute presence** may block, and that **identity gates nothing, ever**. An identity
metric routing repairs is at minimum in tension with that. **Measure and report what this thing
does; do not resolve the tension by deleting it or by promoting it.**

**Deliberately not this round:** coverage on `flux_generator.py` (0%), `sdxl_generator.py` (47%),
`dsg_verifier.py` (54%) — GPU-bound, and mock coverage there buys little. `compile.py` at 57% is a
maybe; say so if you disagree.

**If this is the wrong half, cut it.** Three rounds, three cuts that improved the work.

## The transfer, from a sibling repo, today

An Opus seat fixed armature's record-index failure and reported the structural cause: **armature
had zero tests touching its index, and neither its verify script nor any CI workflow ran it.**
That is why a broken gate reached `main` and sat there. It also found that the index's `build` verb
never wrote a certificate despite the module's own docstring claiming no such path existed, and
that a `health()` function computing exactly the early-warning signal had **no verb reaching it**.

The transferable question for you: **what in prompt-craft is exercised by nothing, and what exists
that nothing calls?** The identity sub-gate is one answer. There may be others — an unreachable
branch, a helper with no caller, a check no test ever fails.

## Argue

1. **`visual_inventory.py:75`** — defect or acceptable looseness? Measure before ruling.
2. **The identity sub-gate's thresholds** — is `0.55` / `0.05` calibrated against anything, or
   inherited from a docstring? What would it take to find out without a GPU?
3. **Mutation-testing tooling** — worth a dependency and a CI stage, or a one-off script whose
   survivor list is the artifact?
4. **Anything unnamed.** Three rounds running the unnamed item has been the best part.

## Constraints

No GPU, no cloud generation, **no credits.** No publishing, no version bump (stays `0.1.0`), no
repo-visibility change, no commits. Public surfaces fenced: `README*.md`, landing page, handbook,
`CHANGELOG.md` content, GitHub metadata, `[project] description`. `SECURITY.md` and `SCORECARD.md`
are scaffolds awaiting authorship — leave them.

`core/` is open, same condition as #2 and #3: report every core change with its reasoning at the
top.

Gates `raise`, never a bare `assert`. Tests ride the commit. **A test that cannot fail is not a
test** — if you add a fixture, show what breaks it. Premises marked **measured** or **assumed**.

Counts: prompt-craft **77 passing** at `4541a1d`, coverage **81%**. armature **1341 passing** at
`c8f186b`, with an index change-set uncommitted from another seat.

## Calibration

Nominate **one checkable claim** we verify by running it before anything trusts the rest.

Three for three. A round where the chip loses is still reported.
