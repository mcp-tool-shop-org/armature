---
title: Roadmap
description: The arc session by session, the hinge where the thesis lives or dies, and the drift tripwires named in advance.
sidebar:
  order: 5
---

The canonical roadmap is
[docs/ROADMAP.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/ROADMAP.md) in the
repo — this page summarizes it. Where they differ, the repo is right.

It was authored on 2026-08-10, before any code. **Phases A–C are firm; everything after is
provisional by construction** — each phase is shaped by what the phase before it measures. A
provisional phase may be re-cut. It may not be *skipped silently*, and a phase that gets re-cut
records why.

## Definition of done

Two bars, in order. The second is the real one:

1. **built** — the tool ships: repo public, quality gates pass, published, CI green.
2. **filled** — **the Director has accepted a shot armature produced and used it in a real
   project.** *(Corrected 2026-08-11: this line used to say "a real game project." The game is
   one consumer — a cutscene, a film shot, or any footage counts the same.)*

A test count is not the second bar. A demo reel is not the second bar. Until a shot is accepted
and used in a real project, armature is `built`, and the roadmap says so out loud. The studio has
a name for the failure this prevents: tools that get built and never filled.

As of 2026-08-13, armature is **built** by the first bar's own terms — public, hard gates green
(`shipcheck audit` exit 0), v0.1.0 released. **`filled` remains open**, and this page keeps
saying so out loud.

## The arc as run — recorded 2026-08-11, after the audit

The plan below was authored on day one and the first arc re-cut it silently, which the
repo-wide [audit](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/audit-first-arc.md)
names as a first-class failure: E03–E06 as run bear little resemblance to E03–E06 as planned,
and identity — the planned experiment closest to the product — never ran while two unplanned
proxies did. What actually ran: exporter (E01) · first contact (E02) · authored motion (E03) ·
the between-generation noise floor (E04) · reference-onto-schematic (E06) · one withdrawal
un-run (E05). The measurements are real and kept; the framing failure is the audit's subject.

**What governs now:** every credit-spending spec carries a Trajectory row — what the spend
advances toward the full GLB→video scope — with the same force as its licence rows. The
current line: the first performer built fresh through facet's route (F01/E33) → the named-bone
rig (E07) → **the first authored performance of a real character (E08)**.

## The arc as it stands — recorded 2026-08-13

Twelve experiments closed (E05 withdrawn un-run), and **v0.1.0 — the first marked state of
the record — released 2026-08-13**. The phase letters below map loosely onto what actually
ran: foundation, the exporter and first contact (A–C) held; control (D) became the control
arc and the **driven route**, proven at shot level and parked for AI-animation buildout;
identity (E) is measured at the Director's eye three ways — driven (E08), unanchored (E11
wave 1), and through a held world (E12) — with reference-view mechanics now **E13's probe**
on a hosted identity-lock tier: dispatched, halted at zero spend on two structural premise
failures, repaired by a support arc that rebuilt the reference kit with true alpha, and
re-armed, all on 2026-08-13. Continuity (F) waits on the narration shelf. The posture since
2026-08-12 is a **learning monorepo**: experiments prove paths, no route is canon by
momentum, and three routes now stand where the plan imagined one.

## The arc

| Phase | What it is |
|---|---|
| **A — Foundation** | Repo footing, the discipline, this roadmap, the research grounding, the first licence map, the exporter's spec. No code beyond scaffold. |
| **B — The exporter** | Given a mesh and a shot spec, render per-frame control channels from a staged scene in headless Blender, plus a manifest that makes the run reproducible. Everything downstream consumes its output. **Zero generation, zero credits** — no credit is spent until the exporter's output is trusted. |
| **C — First contact** | **The hinge.** Measure the provider's noise floor *first*, then run one control probe: one character, one short shot. The gate is a **control \| output \| reference \| provenance** sheet built before any metric is quoted. |
| **D — Control** | Which control signal, at what strength. Arms vary one thing each. |
| **E — Identity** | How many reference views, arranged how. A per-character adapter runs only if the reference stack leaves a gap worth the training cost. |
| **F — Continuity** | Whether the same character survives across separate generations, and where a single shot's coherence ends. |
| **G — Ship** | The tool surface, then the quality gates, then the full treatment, then a real shot in a real project. |

**Phase C is where the thesis lives or dies.** If a CG-rendered control sequence does not hold a
character in a real video model, the honest outcome is to say so and stop — and that is written
down *now*, in advance, so that it cannot later be renegotiated. A negative result there is a
full success and saves the rest of the arc.

Two structural notes carried from the spec:

- **Phase D must observe both failure directions**: too weak, where structure and identity drift;
  and too strong, where motion goes stiff and the render's own artifacts print through. A strength
  curve with only one end observed is half a result.
- **Phase F's artifact is a cut**, judged as a cut — not as a set of clips that each look fine.

## Drift tripwires

Named in advance so they can be caught **by name**. Any session may call one; the Director rules.

1. **Building the tool before proving the thesis.** Product polish before the hinge rules is
   drift.
2. **Chasing the newest model.** A new model is an arm in a future experiment, never a reason to
   restart. The arc outlives any model version.
3. **A metric quietly becoming the judge.** The first time a number is cited to accept an artifact
   the Director has not seen, this one has fired.
4. **Scope leaking toward an editor.** Assembly is not the job.
5. **"Just for a test" non-commercial models.** The [licence gate](/armature/handbook/license-gate/)
   has no test exemption.
6. **Unbounded credits.** A submission without a stated ceiling is a defect, not a shortcut.
7. **Feature creep in the exporter** because a channel is easy to add. It ships what the
   experiments need, not what Blender can do.
8. **Session sprawl** — a session that keeps going past its deliverable. Sessions end at the
   deliverable and its gates.

## What is deliberately still open

These are architecture decisions that evidence should settle rather than taste:

- Which control channels the exporter emits first, and their exact format conventions.
- Which generation route the first probe uses — open weights on cloud GPU, or a partner API —
  gated by the licence map rather than by convenience.
- Whether the shot or the cut is the tool's output unit.
- Whether reference views or a trained adapter is the identity mechanism.

**Nothing above is a prediction.** Where the roadmap states a number or a mechanism later, it
carries the measurement that produced it, or it is marked provisional.

## Where publishing sits

Publishing reached its first milestone on 2026-08-13: **v0.1.0**, a GitHub release marking a
state of the record — twelve experiments, three routes, the laws, with translations landed
before the tag because a tag is immutable. **Nothing ships to a package registry** — the
reserved names remain unused, and a version here marks the record, not an installable
artifact. *(This section read "nothing has been published from this repo yet" until the
release; the day-zero half expired and the registry half stands.)* The details, including a
load-bearing constraint about which workflow filename the release path authenticates, are in
[docs/publishing.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/publishing.md).
