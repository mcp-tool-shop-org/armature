# Grok build #3 — prompt-craft: your exit contract is right about three things and wrong about one, and a study-swarm is why I can say which

**2026-08-17, armature advisor seat.** Two for two. #2's chip was verified by re-running the
original defect myself rather than trusting the test: `pcraft gate` on a nonexistent path now
gives `error[IO_GATE_INPUT]`, **exit 2**, and no `gate overall:` line. Suite **57 passed**,
wheel and sdist both build, armature untouched.

**Both change-sets are folded.** armature `c8f186b` (Gate CANON, 1341 passing). prompt-craft
`be5f0d9` (the exit contract, 57 passing). You are building on committed ground now.

Your `_is_identity_atom` finding was the round's best work and it did not come from the brief —
I asked whether an atom was doing identity work and you found the router, not the contract. A
study-swarm running the same afternoon returned the same disease from the literature, and
neither of you knew about the other. That convergence is in
`docs/research-grounding-verification-gates.md` §A1.

This round I am bringing you evidence that **corrects the contract you just shipped.**

*Everything below the line is the paste block.*

---

# Two for two. The four-way verdict you built is a three-way verdict, and a 1990s monitoring standard already has the missing code.

## ⚑ The correction — `GATE_UNAVAILABLE` must not share an exit code with `GATE_FAIL`

Your contract:

| situation | code | exit |
|---|---|---|
| path missing / unreadable | `IO_GATE_INPUT` | 2 |
| nothing scored, required tier could not run | `GATE_UNAVAILABLE` | **2** |
| a required atom scored FAIL | `GATE_FAIL` | **2** |
| ≥1 real score, roll-up uncertain | `PARTIAL_UNCONFIRMED` | 3 |
| every required atom passed | — | 0 |

**"Could not check" and "checked, and it is bad" are on the same exit code.** That is the exact
conflation that produced the original defect, moved up one level: the old gate merged three
states into 0; the new one merges two into 2.

This is not my taste. It is the single best-documented failure in this area:

- **OCSP hard-fail vs soft-fail.** Browsers deliberately ship *soft*-fail because hard-fail
  turns any CA or CDN outage into a global outage — and the root cause named in that history is
  that hard-fail conflated *could not check* with *checked and it is bad*. Fail-closed itself
  caused repeated real availability harm through exactly this merge.
- **The Nagios plugin API**, the de-facto monitoring standard since the 1990s, mandates a
  four-way verdict: `0 OK / 1 WARNING / 2 CRITICAL / 3 UNKNOWN`, where **UNKNOWN means the check
  could not determine status** and CRITICAL is never overloaded for "could not run."
- **`sysexits.h`** (4.0BSD, still shipped) splits `EX_UNAVAILABLE` (69) and `EX_TEMPFAIL` (75)
  from generic error.
- **Terraform's `plan -detailed-exitcode`** uses 0/1/2 to gate an irreversible `apply` — proof
  that gates in front of irreversible operations routinely need more than two codes, and that CI
  is already built to branch on them.

⚠ **Provenance, stated honestly: all four of the above are documented engineering practice, not
peer-reviewed research, and they passed through no citation gate.** The research agent labelled
them as practice and I am not upgrading that label. The *shape* is well-attested; the specific
numbers are conventions, not findings.

Your error **codes** already carry the distinction. Only the exit code — the thing a CI branch
actually reads — collapses it. **What the right mapping is, is yours.** Nagios would put "could
not run" at its own code above the failure codes; you may prefer to keep `PARTIAL_UNCONFIRMED`
where it is and add a fifth. I am naming the defect, not the fix.

## The research grounding — and what is actually verified

A four-agent study-swarm ran today. Every citation went through an external gate:
`prism verify --type citations`, caller family `anthropic`, verifier `mistral-small:24b` via
local Ollama — a different family, reasoning stripped. **21 citations, all 21 existence-resolved,
14 `supported`, 7 `not_addressed`, 0 `contradicted`, 0 fabricated.**

`not_addressed` means the oracle reads title and abstract only, so a figure living in a results
table reads as unaddressed. **It is not evidence the finding is wrong and not evidence it is
right.** Every citation below is marked. Full record and the three instrument defects the gate
run itself exposed: `docs/research-grounding-verification-gates.md`.

**F1 · `supported`.** A component's own confidence is a poor abstention signal — a separately
trained calibrator reached 56% coverage at 80% accuracy versus 48% for raw confidence
(arXiv:2006.09462).

> **Implication.** A tier's internal confidence must not double as the gate's roll-up UNCERTAIN
> signal. Your roll-up needs its own logic, not a max or a min over tier confidences.

**F2 · `supported`.** Abstention is a distinct and harder skill than the underlying check — a
model at 86% F1 when forced to answer fell to 66% once required to abstain correctly
(arXiv:1806.03822).

> **Implication.** "When may this gate decline to decide" deserves its own tests, not coverage
> inherited from the pass and fail paths.

**F3 · `supported`.** A confident-looking output presented up front produces rubber-stamping;
forcing independent engagement measurably reduces overreliance on wrong suggestions
(arXiv:2102.09692).

> **Implication.** Whatever prints for `PARTIAL_UNCONFIRMED` must not read as a wall of green
> passes with one asterisk.

**F4 · `supported`.** Holistic judges drift from human judgment as models improve — up to 17.7%
absolute error — and per-atom decomposition with soft aggregation is the proposed fix
(arXiv:2512.16853).

> **Implication.** This validates the contract's central bet. The atomic decomposition is not a
> stylistic choice; it is the thing the evidence says survives.

**F5 · `supported`.** No single metric performs consistently across compositional tasks, and
VQA-based metrics are not uniformly superior to embedding-based ones (arXiv:2509.21227).

> **Implication.** A point *for* your tiering, against collapsing to one verifier.

**F6 · `supported`.** CLIP's object-attribute binding failure is a training-data property, not
fixed by scaling batch size or adding hard negatives (arXiv:2507.07985).

> **Implication.** The CLIPScore ban stands. Honest limit: measured on CLIP, not SigLIP2 — same
> contrastive family, transfer plausible, **unconfirmed**.

**F7 · `not_addressed`.** A single RL-trained *generative* verifier outperforms GPT-4o on its own
benchmark (OmniVerifier, arXiv:2510.13804).

> **Implication — a live tension worth your argument.** The field's leading edge is trending
> toward one generative verifier while this architecture bans generative verifiers. But the ban's
> actual wording is that a generative VLM is never *its own* gate. A **separate** generative
> verifier of a different family may not violate it at all. Nobody has written that distinction
> down carefully, and it should be written before someone resolves it by accident.

**F8 · The gap that bites directly.** TNG-CLIP (`supported`, arXiv:2505.18434) confirms CLIP
remains limited at negation. **No source was found benchmarking a sigmoid zero-shot score as a
negation or absence verifier.**

> **Implication.** This repo carries four **required** negations — `no_human_face`,
> `no_rival_colours`, `no_modern_gear`, `no_shield` — resting on a capability nobody has
> measured. They can currently block an asset.

## The watchdog signal, and why I am asking for it

Documented practice, ungated: the Prometheus always-firing Watchdog alert, whose **absence** is
what reveals the pipeline died; and the SRE-book rule to monitor the monitoring path, because a
check that quietly stops running is indistinguishable from "fine."

The argument is not theoretical. **Today's own citation gate produced a top-level verdict of
`revise` while every one of its fifteen groundedness lenses had failed with "Ollama API not
reachable."** The headline read like a judgment about the citations. It was a dead verifier. I
only caught it by opening `lens_results`. Before that, the same tool **exited 0 while refusing to
run at all** on a missing signing key.

So: the gate should emit a positive **"N of M required tiers actually executed"** count,
independent of the verdict, on the transcript and in the record. Not a log line — a field a
caller can assert on.

## What to build this round — and argue the scope

**My call:**

1. **Split the exit contract** so "could not run" is not the same code as "ran and failed."
2. **The `N of M tiers executed` count** as a first-class field, per above.
3. **The roll-up's own logic** (F1) — the gate's UNCERTAIN must not be a tier's confidence
   wearing a different hat. Tests for the abstention path specifically (F2).
4. **Write down the generative-verifier distinction** (F7) — `core/gate/verifier_iface.py`
   already documents CLIPScore as known-broken; this belongs beside it. Prose plus whatever the
   `family_guard` should actually enforce, which may be narrower than what it enforces today.

**Deliberately not this round:** the negation measurement (F8). It needs the `[image]` extra
installed and a labelled set, and it is an experiment, not a fix — but **say so in your report if
you think four required negations resting on an unmeasured capability should stop being
`required` until measured.** That is a product call I would rather surface than sit on.

**If this is the wrong half, cut it.** Two rounds, two cuts that improved the work.

## Argue

1. **The exit mapping** — Nagios-style dedicated code for "could not run," or something better.
2. **F7's distinction** — is "never its own gate" the right rule, or is the real rule "never the
   same weights, and never the same family"? These differ, and the difference decides whether a
   generative verifier of a different family is ever admissible.
3. **F8** — should the four required negations be downgraded pending measurement?
4. **Anything unnamed.** Two rounds running you have returned something the brief did not ask
   for and it was the best part both times.

## Constraints

No GPU, no cloud generation, **no credits.** No publishing, no version bump (stays `0.1.0`), no
repo-visibility change. Public surfaces stay fenced: `README*.md`, landing page, handbook,
`CHANGELOG.md` content, GitHub metadata, `[project] description`. `SECURITY.md` and
`SCORECARD.md` are scaffolds awaiting authorship — leave them.

`core/` is open, same condition as #2: report every core change with its reasoning at the top.

Gates `raise`, never a bare `assert`. Tests ride the commit. Premises marked **measured** or
**assumed** — and note that the engineering-practice items in the correction section above are
marked as practice deliberately, not upgraded.

Counts: prompt-craft **57 passing** at `be5f0d9`; armature **1341 passing / 13 skipped** at
`c8f186b`.

## Calibration

Nominate **one checkable claim** we verify by running it before anything trusts the rest.

Two for two. A round where the chip loses is still reported.
