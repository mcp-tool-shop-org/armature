# armature — the build roadmap

**Status:** authored 2026-08-10 by the advisor seat, before any code. Phases A–C are firm;
D onward are **provisional by construction** — each is shaped by what the phase before it
measures. A provisional phase may be re-cut; it may not be *skipped* silently, and a phase
that gets re-cut records why in this file.

This file exists to prevent drift. It is the answer to "what are we building, in what order,
and how do we know when to stop." Read it at the start of every session here.

---

## The thesis (one paragraph, unchanged for the life of the project)

A video model can produce motion, light and life that no renderer can. It cannot be told
*who is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model must obey. The scene is the skeleton; the model is the
skin. Structure comes from geometry we own; life comes from the model; **identity is a named,
versioned thing that rides in the prompt and the reference stack, never an accident of a
lucky frame**.

## What armature is NOT (the scope fence)

Named now, because each of these is a plausible-sounding drift that would eat the project:

- **Not a video editor or NLE.** It produces shots. Assembly, grading and sound live elsewhere.
- **Not an animation suite.** Blender is the animation tool. armature stages and renders.
- **Not a character creator.** facet makes the asset. armature consumes it.
- **Not a model.** No training a video model from scratch. Per-character identity LoRAs are a
  measured question (Phase E), not a founding assumption.
- **Not a general 3D-to-video converter.** The unit of work is *a shot of a known character*.
- **Not a real-time system.** Batch, headless, recorded.

## Definition of done

Two bars, in order. The studio's `built | filled` rule governs, and the second is the real one:

1. **built** — the tool ships: repo public under `mcp-tool-shop-org`, shipcheck hard gates A–D
   pass, full treatment applied, published, CI green.
2. **filled** — **the Director has accepted a shot armature produced and used it in a real
   game project.** A test count is not this bar. A demo reel is not this bar. Until a shot is
   accepted and used, armature is `built`, and this file says so.

---

## The arc

Each row is one session. **Seat** is who runs it. A session ends when its deliverable exists
and its gates have been reported — not when it feels finished.

| # | Seat | Session | Produces | Ends when |
|---|---|---|---|---|
| **A0** | advisor | Foundation | repo footing, `CLAUDE.md`, this roadmap, `docs/license-map.md` v1, E01 spec + paste block | E01 is startable without another round trip |
| **E01** | executor | The exporter | `tools/stage_render.py` + shot-spec format + tests + anchor | the anchor reproduces and every gate has a verdict |
| **R01** | advisor | Ruling on E01 | ruling doc; roadmap corrections | the record is folded and E02's spec is on screen |
| **E02** | executor | First contact | provider noise floor + first control probe + the Gate-0 sheet | the sheet is on the Director's screen |
| **R02** | advisor | Ruling on E02 | ruling; **the go/no-go on the whole thesis** | the Director has judged the sheet |
| **E03** | executor | Control modality | depth vs pose vs edge vs combined, one variable per arm | all arms measured, sheet built |
| **E04** | executor | Control strength | the strength/stiffness curve on the surviving modality | the curve exists with both failure ends observed |
| **E05** | executor | Identity — reference stack | 1 view vs N views vs full turnaround | sheets at the Director's zoom |
| **E06** | executor | Identity — LoRA vs zero-shot | *conditional on E05* | — |
| **E07** | executor | Continuity across cuts | one character, several shots, assembled | the Director judges the cut, not the clips |
| **E08** | executor | Shot length and extension drift | where coherence ends, measured not assumed | — |
| **P01** | executor | The tool surface | CLI (+ MCP if earned), tests, docs, `docs/license-map.md` current | shipcheck audit passes |
| **P02** | advisor+executor | Ship | shipcheck → full treatment → publish | CI green on the org repo |
| **F01** | Director | Fill | a shot in a real game project | the Director says so |

Phases D–F (E03–E08) will be re-cut as evidence lands. **E02 is the hinge**: if a CG-rendered
control sequence does not hold a character in a real video model, the honest outcome is to say
so and stop — a negative result there is a full success and saves the rest of the arc.

---

## Phase detail

### Phase A — Foundation (advisor, no GPU, no credits) — IN PROGRESS

Repo footing under the repo-first rule (repo exists, origin correct, `main`, scaffold pushed),
the discipline file, this roadmap, the study-swarm's research grounding, the first license map,
and the E01 spec. **No code beyond scaffold.**

### Phase B — The exporter (local, zero credits)

**E01 — the control-sequence exporter.** Given a GLB and a shot spec, render per-frame control
channels from a staged scene in headless Blender, plus a manifest that makes the run
reproducible. This is the whole foundation; everything downstream consumes its output.

Non-negotiable in E01's spec: the exact format conventions (depth direction, normalization,
bit depth; skeleton drawing convention; edge parameters) are **grounded in the study-swarm's
retrieved evidence, not guessed** — getting them wrong silently invalidates every later
experiment. Frame dimensions and counts must be generator-legal. Tests ride the commit.

**Zero generation in Phase B.** No credits are spent until the exporter's output is trusted.

### Phase C — First contact (cloud, bounded credits) — THE HINGE

**E02** does two things in one session, in this order:

1. **Measure the provider's noise floor first.** Submit one payload several times and measure
   what "the same request" produces. Every later comparison is read against this floor. facet's
   law — a single-run comparison has no noise floor — applies with double force here, because
   a cloud video provider may not be reproducible at all.
2. **The first control probe.** One character, one short shot, control sequence from E01.
   Gate 0 is the **control | output | reference | provenance** sheet, built *before* any metric
   is quoted.

R02 is where the Director rules on the thesis itself.

### Phase D — Control (E03, E04)

Which control signal, at what strength. Arms vary one thing. Both failure directions must be
observed and named: too weak (structure and identity drift) and too strong (motion goes stiff,
the render's own artifacts print through). A strength curve with only one end observed is half
a result.

### Phase E — Identity (E05, E06)

How many reference views, arranged how — the studio's turnaround output is the natural input
and this is where its value is measured. E06 (per-character LoRA) runs only if E05 leaves a gap
worth the training cost.

**Standing rule:** identity is judged by the Director. Diagnostics may inform; they may not
gate.

### Phase F — Continuity (E07, E08)

Whether the same character survives across separate generations, and where a single shot's
coherence ends. E07's artifact is a **cut**, judged as a cut.

### Phase G — Ship (P01, P02, F01)

The tool surface, then shipcheck, then the full treatment, then a real shot in a real game.

---

## Drift tripwires

Named in advance so they can be caught by name. Any session may call one; the Director rules.

1. **Building the tool before proving the thesis.** Product polish before E02 rules is drift.
2. **Chasing the newest model.** A new model is an *arm in a future experiment*, never a reason
   to restart. The arc outlives any model version.
3. **A metric quietly becoming the judge.** The first time a number is cited to accept an
   artifact the Director has not seen, the tripwire has fired.
4. **Scope leaking toward an editor.** See the scope fence. Assembly is not our job.
5. **"Just for a test" non-commercial models.** The license gate has no test exemption. A
   conclusion drawn on a banned model is a conclusion that must be discarded.
6. **Unbounded credits.** A submission without a stated ceiling is a defect, not a shortcut.
7. **Feature creep in E01** because a channel is easy to add. The exporter ships what the
   experiments need, not what Blender can do.
8. **Session sprawl** — an executor that keeps going past its deliverable. Sessions end at the
   deliverable and its gates.

## What is open (closed by the study-swarm, then folded into E01's spec)

These are deliberately unanswered here. They are architecture decisions that empirical evidence
should settle, not the advisor's taste:

- Which control channels E01 emits first, and their exact format conventions.
- Which generation route E02 probes (open-weights on cloud GPU vs partner API) — gated by the
  license map, not by convenience.
- Whether the shot or the cut is the tool's output unit.
- Whether reference views or a trained adapter is the identity mechanism.

**Nothing above is a prediction.** Where this file states a number or a mechanism later, it
carries the measurement that produced it or it is marked provisional.
