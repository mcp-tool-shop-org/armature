---
title: Method
description: Three seats, spec to report to ruling, and why this repo runs under a discipline that looks excessive for its size.
sidebar:
  order: 3
---

armature is a few days old and runs under a discipline that looks disproportionate to its size.
This page explains where it came from and what it costs, because the discipline is the reason
anything on this site can be read at face value.

## Why it exists

The method is inherited from [facet](https://github.com/mcp-tool-shop-org/facet), the sibling
repo upstream, where it was paid for rather than designed.

In facet's founding session **six inherited or asserted claims were falsified** — each in
minutes, because each one sat next to runnable code. Later arcs falsified a pass condition that
scaled with how bad the problem turned out to be; a taboo that nobody could produce a source
for; and 87 gates that a single environment variable could delete.

None of those were caught by being careful. They were caught by a structure that makes checking
cheaper than assuming. The rules below are that structure, and every one of them has a specific
failure behind it.

## Three seats

| Seat | Does | Must not |
|---|---|---|
| **Director** | Sets direction; judges every artifact by eye | — |
| **Advisor** | Writes specs, rules on reports, folds findings into the repo | Execute, or grade its own rulings |
| **Executor** | Runs the spec, measures, reports evidence | Decide what results *mean*, or judge quality |

**The separation is the point.** The session that designs an experiment does not grade its
results, and the session that runs it does not decide their meaning. An executor that is allowed
to conclude will conclude in favour of the thing it just built.

That is enforced in the writing, not just in the intent: the words *verified, shipped, works,
decisive, validated, proven* are not permitted in an executor's report, commit message or doc.
Reports carry measurements and comparison sheets; the ruling is a separate document written by a
separate seat, after the Director has seen the artifact.

## Spec, then work, then report, then ruling

Every non-trivial change runs as a numbered experiment:

```
spec written BEFORE the work  →  report written AFTER  →  advisor ruling LAST
```

A spec carries the question; hypotheses **with predictions**; arms that vary one thing each; the
metrics; the gates; the credit ceiling; the licence checks it introduces; an explicit
out-of-scope section; and **every premise marked measured or assumed**. Amendments are appended
in place with dates and reasons — a spec that hides its own corrections is the thing this
discipline exists to get away from.

A hypothesis with no prediction cannot be wrong, and one that cannot be wrong teaches nothing.
So predictions are stated before the results are looked at, and the report discloses whether the
prediction was blind.

## The rules that keep getting earned

These are the portable ones. The full law book, with each law's earning story, lives in
[CLAUDE.md](https://github.com/mcp-tool-shop-org/armature/blob/main/CLAUDE.md).

**An inherited claim is a hypothesis wearing a fact's clothes.** Checking one costs minutes;
building on one costs a session. This binds hardest on the premises of your *own* dispatch — the
place you have least reason to doubt.

**Enumerate the resource before commissioning one.** A flag, an instrument, a node, a model or an
upload path may already exist. One search separates a commission from a thing already built, and
the commission is always the expensive branch.

**Gates raise; they never assert.** A check that decides whether an irreversible step proceeds
lives *inside* the tool performing that step and raises. Not a shell chain — a chain can walk
past a failing exit code. Not an `assert` — Python deletes those under `-O`. No skip flag. That
last one is not hypothetical: 87 gates upstream were deletable by one environment variable.

**A check that cannot fail is not a check**, and a diagnostic and a gate are different objects.

**A single-run comparison has no noise floor.** Measure the floor before reading a difference —
doubly so here, where cloud video generation may not be reproducible at all. Each provider's
repeat-variance gets measured before any one-run gap is read as a result.

**A recipe that does not reproduce its output is not a recipe.** Every generation records model
id and version, the full payload, the seed and control-input hashes. Where a provider is
nondeterministic the record says so, and its measured noise floor is the context for every number
quoted against it.

**A file-hash mismatch is not evidence that a render changed.** Compare pixels; byte-hashes are
for artifacts whose bytes are the contract.

**Grade an arm only on what it can move.** Before adopting a metric, ask what value it takes when
the arm does nothing and when it works perfectly. If those are the same number, it is not
measuring the arm.

**A report may not contain a placeholder shaped like evidence.** A gate that has not run is
written `NOT YET RUN`, never a plausible identifier with a verdict beside it. That rule is why
this website has no screenshots.

**A negative result is a full success.** Say so plainly and stop, rather than tuning toward a
number. Never change a parameter and re-run to get past a gate.

**Failures stay in the repo** — under `tools/superseded/`, still runnable, with the reason. A
falsified approach that leaves the tree quietly becomes doctrine again.

## An instrument that was nearly believed

The clearest illustration is in the founding research pass, and it is recorded because it was one
careless step from doing real damage.

Every citation gathered by the research swarm was checked for existence against a deterministic
retrieval oracle rather than model memory. **The oracle's first run returned 0 of 34 resolved.**

Taken at face value that is a catastrophe — an entire research foundation fabricated. But
known-real papers failed alongside everything else, and *a check that rejects everything is
measuring itself*. The defect was XML parsing in the harness. Corrected, the same identifiers
resolved 31 of 34, and the remaining three were arXiv rate-limiting at the HTTP level, never
fabrication.

The final count is **34 of 34 resolved, zero fabricated**. It is written down because the first
result was nearly a false halt on the whole swarm, and the next session needs to know that this
particular instrument can lie in that particular direction.

## What is bounded on purpose

**Credits.** Cloud generation costs real money and spent credits have no undo — there is no
compensator, so the bound is the honest treatment. Every spec states its credit ceiling before
the first submission, itemized per arm, and an arm whose cost exceeds its information value gets
skipped rather than discounted.

**Licences.** Nothing enters the pipeline without a retrieved licence document, including in
experiments. That has its own page: [the license gate](/armature/handbook/license-gate/).

**Judgement.** Metrics are diagnostics; the Director's eye is the judge. Every generating
experiment produces a **control | output | reference | provenance** sheet *before* any metric is
quoted, and artifacts are judged at full size rather than off a contact sheet. Video is judged
in motion **and** as frames — a clip that reads well at speed can carry a melted hand in every
one of them.
