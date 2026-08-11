# Working in this repo

**armature** — you block the shot; the model shoots it. Canonical character meshes
(GLB) are staged and animated in headless Blender; those renders become the per-frame
**control sequences** and reference stacks that drive video-diffusion generation, so
AI-generated video keeps **one persistent main character** whose position and pose are known
every frame. The previz scene is ground truth; the video model paints life over it.

## The scope, in the Director's words — read before any other rule

> The Director's scope ruling, 2026-08-11: armature is not limited to games — it makes
> cutscenes, movies, anything image-to-video can make, with a GLB in place of the image.

**armature is image-to-video with a GLB instead of an image.** Movies, game cutscenes,
character poses and movement, any footage at all — everything spatial is authored, and the
model paints life over it. The game is one consumer, not the boundary. There is no end to the
possibilities, and the repo's job is to open them, not to pick one.

This scope has been shrunk twice — to "a turnaround tool," then to "a tool for making game
footage" — and corrected twice by the Director. **Describing armature by a use-case is the
drift signature.** If a spec, ruling, summary, or README line names a narrower product than
*footage from a scene you own*, stop and re-read this block before writing another word.

**Every credit-spending spec carries a `Trajectory` row** — what this spend advances toward
the full scope — with the same force as its licence rows. A spec that cannot fill the row does
not run; the advisor checks it at dispatch; an executor who finds it missing halts before the
first submission. Earned the expensive way: 22 generations and zero shots, because hygiene had
gates and purpose had prose (`docs/audit-first-arc.md` §2).

armature sits **downstream of facet** (`E:\AI\facet`): facet cuts and paints the figure;
armature stages and performs it. armature consumes facet's canonical assets and turnarounds
and **never writes into facet's tree**.

This file is about **how to work here**. What is *true* here lives in README.md and
`docs/experiments/`. Read those for facts; read this for method.

---

## Why this discipline exists

This repo inherits its method from facet, where it was paid for. In facet's founding session
**six inherited or asserted claims were falsified** — each in minutes, because each sat next
to runnable code. Later arcs falsified a pass condition that scaled with how bad the problem
turned out to be, a taboo nobody could cite, and 87 gates that an environment variable could
delete.

The rules below are not process decorum; every one was earned. facet's
[CLAUDE.md](../facet/CLAUDE.md) is the full law book with each law's earning story.
**Those laws bind here.** When a situation here rhymes with one recorded there, the facet law
governs until a measurement *here* overturns it.

## The three roles

| role | does | must not |
|---|---|---|
| **Director** (Mike) | sets direction; judges every artifact by eye | — |
| **Advisor** | writes specs, rules on reports, folds findings into the repo | execute, or grade its own rulings |
| **Executor** | runs the spec, measures, reports evidence | decide what results *mean*, or judge quality |

The separation is the point: the session that designs an experiment does not grade its
results, and the session that runs it does not decide their meaning.

## Rules for an executor session

1. **Never judge whether output is good.** Produce measurements and comparison sheets. The
   Director judges. The words *verified, shipped, works, decisive, validated, proven* do not
   belong in a report, a commit message, or a doc.
2. **State a prediction before you look**, and disclose whether it was blind. A hypothesis
   with no prediction cannot be wrong, and one that cannot be wrong teaches nothing.
3. **Stop at every gate. Never improvise past one.** If a gate fires, report it with its
   evidence and halt. Never change a parameter and re-run to get past a gate.
4. **Do not write to the memory store.** The advisor folds findings into the repo after the
   Director has seen them. The repo is the record.
5. **A negative result is a full success.** Say so plainly and stop, rather than tuning
   toward a number.

## Rules for an advisor session

0. **Before any product-defining dispatch, confirm the frame with the Director
   contrastively — one or two lines: "I'm about to build X, not Y — stop me if you meant
   Y."** A product-defining dispatch is one that stakes out WHAT armature does, not how.
   Earned 2026-08-11, the most expensive way: the advisor specced E08 as authored-motion-
   plus-control while the Director meant model-generated performance from a GLB-informed
   reference — his scope sentence was in this very file, quoted in three documents, and the
   repo's control-first momentum still won. Every execution gate passed on a spec built
   inside the wrong frame; the check that was missing costs one sentence and ten seconds.
   Trajectory rows police spend direction; this rule polices whether the advisor understood
   the Director at all. They are not the same check, and today proved a seat cannot
   administer the second one to itself.

1. **Rule when the evidence is in; do not predict when it is not.** Deciding is the job.
2. **Correct in place, with the measurement that overturned the claim.** Never quietly delete
   a wrong statement; the correction is more useful than the original.
3. **Pick a pass-condition unit the experiment cannot move.** Never define a pass condition as
   a fraction of a quantity not yet measured. When no calibrated threshold exists, **suspend
   rather than invent one** — report numerator and denominator separately and let the
   Director's eye rule. Retuning a condition after seeing the result is always wrong;
   **withdraw** a broken condition rather than re-derive it while looking at the results it
   would judge.
4. **Own errors in the commit message.** They are how the next session learns which parts of
   the record to distrust.
5. **A dispatch is not delivered until its executor paste block is on the screen** — in the
   same message, unasked. Keeping the project moving is the job, and moving means the next
   session can begin without another round trip.
6. **Do not end a session the Director has not ended.**

## Rules for everyone (the portable core — full stories in facet's CLAUDE.md)

- **The Director's conversational words are private to the session.** Public surfaces —
  this repo, its docs, its site, its commit messages — carry decisions and facts in neutral
  prose, never quotations from chat. When a ruling must be recorded, record the ruling, not
  the sentence it arrived in. Verbatim capture for seat calibration, where needed at all,
  lives only in private local session records, never on GitHub. Earned 2026-08-11: a seat
  published his words across a day of public documents and he named it what it was — a
  breach of trust and privacy.
- **An inherited claim is a hypothesis wearing a fact's clothes.** Checking one costs minutes;
  building on one costs a session. This binds hardest on the premises of *your own dispatch* —
  an executor has least reason to doubt those, so every spec marks each premise **measured**
  or **assumed**.
- **Enumerate the resource before commissioning one.** A flag, an instrument, a node, a model,
  or an upload path may already exist. One grep separates a commission from a thing already
  built; the commission is always the expensive branch.
- **Check the unit, the population, and the object being counted before predicting.** Nine
  consecutive facet arcs missed on this family. Write what one of the counted thing *is*
  before writing the number, and predict each clause of a conjunction separately.
- **Tests ride the commit that touches the code.** A dispatch that plans a tool change without
  naming its tests is missing a step; the executor adds them unasked. Ask of every fixture:
  what would this look like if the code were wrong in the specific way this check exists to
  catch?
- **Gates raise; they never `assert`.** A check that decides whether an irreversible step
  proceeds lives *inside* the tool performing that step and `raise`s — no shell-chain
  separation (a chain can walk past a failing exit code), no `assert` (deleted by `-O` or
  `PYTHONOPTIMIZE=1`), no skip flag. **Put the andon on the direction the invariant does not
  bound.** A check that cannot fail is not a check; a diagnostic and a gate are different
  objects.
- **A file-hash mismatch is not evidence a render changed.** Compare pixels; reserve
  byte-hashes for artifacts whose bytes are the contract.
- **A single-run comparison has no noise floor. Measure the floor before reading a
  difference** — doubly so here, where cloud generation may not be reproducible at all.
  Measure each provider's repeat-variance before reading any one-run gap.
- **A recipe that does not reproduce its output is not a recipe.** Every generation records
  model id + version, the full payload, the seed, and control-input hashes. Where a provider
  is nondeterministic, the record says so, and its measured noise floor is the context for
  every number quoted against it.
- **A global constant must not govern a local feature.** Derive per-structure or bound as a
  fraction of that structure's own size, and report per-structure what an operation changed.
- **Grade an arm only on what it can move.** Before adopting a metric, ask what value it takes
  when the arm does nothing and when it works perfectly. If those are the same number, it is
  not measuring the arm.
- **A report may not contain a placeholder shaped like evidence.** A gate that has not run is
  written `NOT YET RUN`, never a plausible identifier with a verdict beside it. The advisor
  resolves every external citation at ruling time.
- **Failures stay in the repo** — `tools/superseded/`, runnable, with the reason. A falsified
  approach that leaves the tree becomes doctrine again.
- **Metrics are diagnostics; the Director's eye is the judge.**

## Non-negotiables specific to armature

### The license gate (no non-commercial — the same stance as facet)

**No non-commercially-licensed model, weight, LoRA, preprocessor, or code dependency anywhere
in the pipeline — including experiments.** CC-BY-NC, research-only and academic-only are
banned outright. An experiment concluded on a banned model is a conclusion that has to be
thrown away, so it never starts.

- Every model or dependency enters through a **license check recorded in the spec that
  introduces it**: name, version, license, the URL of the actual license document, the
  operative clause, the fetch date, and the verdict
  `COMMERCIAL: YES / NO / CONDITIONAL(<condition>)`.
- **CONDITIONAL is a Director decision**, surfaced contrastively, never silently accepted.
- Partner APIs: output-ownership and commercial-use terms verified per provider **before the
  first credit is spent** on that provider.
- A license that cannot be retrieved is **UNVERIFIED — treat as NO**.
- The verified map lives in `docs/license-map.md`. Licenses change: entries older than 90 days
  are advisory until re-fetched.
- **The same family can split across variants** — check the exact variant and version you are
  about to run, not the family name.

### Identity is the product

Whether the figure on screen **is the same character** is canon — a ground truth the Director
holds, and **no metric approximates it** (facet learned this twice, once with high-pass
statistics for material identity and once with silhouette IoU for character identity).
Identity and quality diagnostics ride reports as diagnostics and **may gate nothing**.

Stylized game characters may break face-embedding tools outright; a diagnostic that returns
numbers on a face it cannot find is noise wearing a unit. Any such number is quoted with
evidence that its detector actually fired.

### Credits are bounded

Cloud generation costs real money and **spent credits have no compensator** — the bound is the
honest treatment. Every spec states its **credit ceiling before the first submission**,
itemized per arm. Compute an arm's ceiling before spending it and skip arms whose cost exceeds
their information value.

### Judging artifacts

- **Beside the reference, with provenance, always:** every generating experiment produces a
  **control | output | reference | provenance** sheet *before* any metric is quoted. facet ran
  four arms and two gates before building this sheet, and when it finally existed the Director
  read the whole thesis off one panel.
- **At the Director's zoom, not from a contact sheet.** Sheets locate; full size decides.
- **Video is judged in motion AND as frames.** A clip that reads well at speed can carry a
  melted hand in every frame. Extract stills where structure is hardest — fast motion,
  occlusion, hands, face turns — and inspect those.

## Experiments

Every non-trivial change runs as a numbered experiment in `docs/experiments/`:

```
spec written BEFORE the work  →  report written AFTER  →  advisor ruling LAST
```

A spec carries: **the Trajectory row** (what this advances toward the full GLB→video scope —
see the scope block at the top of this file); the question; hypotheses with predictions; arms varying one thing each; the
metrics; the gates; **the credit ceiling**; **the license checks it introduces**; an explicit
out-of-scope section; **every premise marked measured or assumed**; and a standards-compliance
block scoring the six workflow standards. Amendments are appended in place with dates and
reasons — a spec that hides its own corrections is the thing we are getting away from.

## Environment

This is the Robot rig (Omen 45L, RTX 5090, 32 GB VRAM). Drives **C**, **E** (workspace and
models), and **D** (external `AI-BACKUP`, archive only — `Test-Path D:\` before use and never
put a live pipeline path on it). **No F:** — any `F:/AI/...` path in an inherited document
means `E:/AI/...`.

```
blender   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
python    E:\AI-Models\trellis2-env\Scripts\python.exe   (until this repo has its own venv)
assets    consumed from E:\AI\training\... and E:\AI\facet\... — READ ONLY, never edited
```

- **Verify the VRAM watchdog before any GPU work** (Blender renders included), every session:
  `pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1`. A stale heartbeat means the GPU
  is unprotected.
- **Run all Blender work through PowerShell** — Git Bash mangles the paths and every call
  fails with `Error: Please select a file`.
- **Blender runs headless only** (`blender -b -P script.py -- <args>`). A live GUI session
  produces artifacts with no recorded parameters, and a recipe that does not reproduce its
  output is not a recipe. Blender's MCP server is a **reference for when you are stumped,
  never a pipeline stage**.
- **Generation runs on Comfy Cloud; rendering and measurement run locally.** The local ComfyUI
  VRAM-ceiling saga is recorded in facet's CLAUDE.md — `--reserve-vram` and
  `--disable-smart-memory` are falsified levers, and the ceiling is never raised.
- **Generation frames must be generator-legal.** Every video model constrains resolution and
  frame count (divisibility rules, fixed buckets, frame-count forms). Derive the frame from
  the scene, then round to the nearest legal size — and record the constraint per model in the
  spec that first uses it.
- **A `dry_run` PASS does not prove link sanity.** Submit saved workflow files verbatim and
  check link topology in code before submission.
- **A served template is a reference, never a route.** Measured twice on 2026-08-11: the
  served Animate template wires the banned detector tier, and the served T2V template wires
  the licence map's excluded 4-step trajectory at strength 1.0 under a randomizing seed with
  no length or seed slot exposed. Every graph this pipeline submits is built in-repo and
  passes **Gate ROUTE** (`tools/armature_core/route_gates.py`, E09 — it walks subgraph
  blueprints) before Gates S and L arm.
- **argparse eats leading minus signs** — use `--views=-30,0,30`.
- **Scripts create their own output directories.** Two facet runs died on this.
- Big binaries (renders, videos, GLBs) stay out of git — `outputs/` is ignored. The record is
  specs, reports, provenance JSON, and sha256 manifests.
