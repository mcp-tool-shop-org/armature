# THE HANDOFF — armature advisor seat, 2026-08-11, written at the Director's instruction

**Why this handoff exists:** the Director relieved this seat after it dispatched E08 — the
first product shot — **three different ways against one unchanged instruction.** His
corrections, in order: the executor was hand-authoring motion when the model should generate
the performance; the single-render fallback reduced the product to plain image-to-video; and
his final ruling — his intent never changed across the exchange, the misreadings were all the
seat's — ended with the instruction to write this handoff for a successor.

**The single most important instruction in this file: do not inherit ANY of this seat's
three E08 interpretations — including its last one, which he never confirmed. Your first
act on E08 is to ask the Director what he wants, as he directed, and confirm it back
contrastively (CLAUDE.md advisor rule 0) before any seat is dispatched.** His standing
definition of E08, restated as decision content: put the rigged GLB through the pipeline to
produce an informed, 4-second GLB-to-video of the performer dancing or emoting across
different scenarios — for example walking up to a bartender in a crowded bar — to test
whether the capability is possible.

Everything below was **measured at write time**. Two prior handoffs today are in git
history; this one supersedes both.

---

## 1. What armature is — the binding scope, in CLAUDE.md's scope block

**"Image-to-video with a GLB instead of an image."** Movies, cutscenes, character poses and
movement, any footage. A game is one consumer, never the boundary. Scope was shrunk twice
before this seat and corrected twice; describing armature by a use-case is the drift
signature. **Advisor rule 0** (added today, earned by E08): before any product-defining
dispatch, confirm the frame with the Director contrastively — trajectory rows police spend
direction; rule 0 polices whether the advisor understood him at all, and a seat cannot
administer that check to itself.

## 2. THE FOUR-REPO SYSTEM — all connected, all current, measured tonight

```
style-dataset-lab (canon + datasets)
   │  styled concepts & canon feed facet's route
   ▼
facet (styled 2D concept → accepted textured 3D asset)
   │  accepted assets ingest BACK into sdlab's asset-lane as dataset entries
   │  (dragon = asset #3, longsword = asset #4, tonight's commits)
   ▼
armature (stages & performs facet's characters → footage)

record-index — the shared evidence engine UNDER facet and armature:
both records are queryable SQLite+FTS5 databases on the same published package.
The studio constitution sits above all of it (memory-gate enforced).
```

| repo | state at write time |
|---|---|
| **armature** `E:\AI\armature` | main pushed & green. E01–E07 closed. **E08 OPEN, halted, ZERO credits spent** (§4). Index SERVING (`docs/index/armature.db` + cert, `tools/armature_index.py`). Branch `E08-run` @ `8399d5a` holds banked tooling, unmerged — advisor merges when E08 truly closes |
| **facet** `E:\AI\facet` | **pushed & green for the first time since the extraction** — `1e4a527`, hermetic 887/0, complete 927/0, CI + Pages success. E33 delivered the performer. Record queryable (`npx @mcptoolshop/facet`). Advisor leftovers: `verify.experiment_coverage` still declares E01–E15 (gates nothing); `docs/advisor-kickoff.md` says T63 while T65 exists |
| **record-index** `E:\AI\record-index` | **0.1.0 LIVE on PyPI** (OIDC, attestations) with the full treatment: 455-check suite, landing+handbook (Pages 200), the Director's own mark as banner, README ×8 languages, SECURITY (measured zero-egress), CHANGELOG. **Five** defects pinned strict-xfail (the fifth found post-release by facet's clean-venv gate). 0.1.1 queue: the five + certificate duplication resolving toward the package |
| **style-dataset-lab** `E:\AI\style-dataset-lab` | v3.4.0, clean, level with origin. `facet-assets/` project ingesting facet's accepted assets via the asset-lane; `salt-road/` among its game projects. Not on record-index (its own structure) |

**The one-system laws:** never advise about another repo from memory or summaries — read
its record or query it (both indexes exist for exactly this). armature never writes into
facet's or training's trees. The Agent tool inherits your model unless you set `model` —
executors default to `opus`.

## 3. Today's completed capital (all pushed, all verifiable)

- **The audit** (docs/audit-first-arc.md) — the Director ruled CONTINUE; E-series aimed at
  the full pipeline; trajectory rows binding in every credit-spending spec.
- **Surfaces decontaminated** — README/handbook/roadmap/metadata all carry the full scope;
  the roadmap records its re-cut.
- **The publish chain, end to end** — record-index tested→treated→published; facet pushed
  green; armature S02 merged + closed (five questions ruled in
  docs/dispatches/S02-closing-ruling.md).
- **F01/E33** — the Director's clay-armature concept through facet's full route: the
  performer, terracotta r3, delivered and hash-verified.
- **E07 closed** (docs/experiments/E07-closing-ruling.md) — skeleton APPROVED with his
  reservation; binding accepted PROVISIONALLY — his assessment: improved, still below the quality bar; five laws earned (liveness clause · a crashed `blender -b -P` exits 0, verify a
  sentinel · bone heat is all-or-nothing against manifoldness · a global deviation statistic
  cannot see a face · the licence gate protects the PIPELINE, not the rig). Deliverable:
  `E:\AI\armature-E07\outputs\E07\rig-repaired\performer_auto.glb`, sha256 `7f56c9ac…2a24`.
- **Consult #5** (docs/comfy-consult-5.md) — the rigid-parts detour, calibrated then
  superseded by repair-not-resample; the Q4 finding stands: the auto-rig ecosystem does not
  have a clean supplied-mesh answer.

## 4. E08 — the honest record, and what the next advisor inherits

**Spend: ZERO.** Verified three ways at every halt (empty queue, no generation bucket on
today's invoice, no prompt_id anywhere). Total cloud contact: 66 free uploads.

**The three wrong dispatches, so you can avoid all three:** (1) authored walk cycle +
control render — he stopped it: the model should generate the motion; (2) one GLB beauty
render + prompt into no-control VACE — plain I2V; he stopped it: reducing the product to
plain image-to-video defeated the point of the whole pipeline; (3) this seat's two-stage generative frame
(prompt → motion model → his skeleton → video model) — **never confirmed by him; treat as
noise.** The spec (docs/experiments/E08-the-first-shot.md) carries the halt banner; its
"proposed corrected route" paragraph is WITHDRAWN by this handoff.

**Banked and real regardless of route** (branch `E08-run`, 371 tests):
`walk.py`/`author_walk.py` (a measured gait — the moonwalk fix is real work) · `framing.py` ·
`render_reference.py` · Gate L pre-checked PASS at 832×480×65 (Wan-legal) · the E02 A2
payload precedent for no-control shapes.

**A measured blocker for any GLB-rendered input:** the reference render exposed E07's
atlas damage as **broad white patches** — neck, left torso, both arms, both hands, feet,
shins — far worse than the "tiny triangles" visible earlier
(`E:\AI\armature-E08\outputs\E08\reference\performer_reference.png`, sha `87d155d5…`).
**The E33 brush pass (never run) is now likely a prerequisite** for any route that renders
him from the GLB. It sits on the finish ledger with the wood grain.

**Consult prep already staged** (verified rows from the local model-knowledge KB, for
whatever route he specifies): **Wan2.2-Animate-14B — Apache-2.0, "animate a character still
with a driving performance video," motion retargeting**; Wan2.2-Fun-A14B-Control (Apache,
pose/depth/reference-locked motion); Wan 2.2 I2V/TI2V family (Apache). armature's licence
map already records that the Animate route's banned pose-detector tier is **sidestepped by
rendering the skeleton input from our own rigged geometry**. The Comfy Agent consult
channel exists for the what-fills-the-slots question — docs/comfy-consult-5-brief.md is the
format precedent, and calibration (verify one cheap claim first) is mandatory.

## 5. The standing ledgers

**Finish (the performer):** the brush pass over the atlas (now likely blocking, §4) · the
wood-grain texture note · ear-rim notches + nose speck from the 593 repaired faces ·
armpit/thigh bone-heat creases · the elbow ball softening under bend (character question) ·
weak neck bone · **skeleton v2: articulated fingers** (needs an F-series hand-mesh
iteration first).
**record-index 0.1.1:** five pinned defects + certificate duplication.
**facet:** the two small advisor items (§2 table).
**armature misc:** `tools/invert_frames.py` adoption (E02 closing Ruling 5) still open;
roadmap maintenance per its re-cut section.

**Director's standing preferences:** review at 0.5×, 8 fps, from `lossless/` · dark means
tone with colour in the shadows · full size decides, sheets locate · dailies standard on
every Director-facing sheet (uniform panels, 1:1 insets on the deciding regions, no debug
states) · metrics are diagnostics, his eye is the verifier of record · the record's
vocabulary, never invented jargon · marathon, not a race · do not end a session he has not
ended.

## 6. This seat's error record — the calibration table for reading everything above

| error | correction |
|---|---|
| **E08 dispatched three ways against one unchanged instruction** — the session-ending failure. Frame errors, not execution errors: every gate passed on every wrong dispatch | Rule 0 written into CLAUDE.md; the E08 definition returned to the Director's own words; this handoff |
| Specced a facet build without reading facet's route | Caught by the Director; corrected mid-flight |
| Banned the measured twin venue, permitted the falsified one | Venue ruling reversed in F01 |
| Dispatched an executor on Fable by omitting `model` | Tiering rule; wrapped at a boundary |
| "Zero credits" repeated without its meaning | GPU-hours are metered; both meters reported since |
| Invented jargon at the Director | The vocabulary rule + memory entry |
| Matched the banner's dimensions without looking at its composition | Rebuilt after his catch |
| Shipped the halt sheet without examining its own insets | His catch; pre-examination promised and kept thereafter |
| QuadRemesher "owned-commercial YES" | His licence ruling; the map's second axis |
| Recommended binding (b) as passable | Overruled — he ruled both bindings failures; the seat had graded relative improvement, not shippability |

**The pattern, named plainly for your calibration: this seat's failures were all frame
and verification failures — hearing instructions through existing momentum, asserting
instead of reading or looking. The executors were right every time they disagreed. The
Director's eye caught what every gate missed. Weight those three facts accordingly.**

## 7. What to do first

1. Read CLAUDE.md (rule 0 first), then this file, then verify §2's states yourself.
2. **E08: ask the Director what he wants, as he directed. Confirm it back contrastively.
   Then spec it.** The consult channel and the staged KB rows are ready when the route
   needs the what-exists answer. Ceiling discipline stands; his balance is the meter;
   probe-first.
3. The white-patches blocker (§4) is likely upstream of any GLB-rendered input — surface
   it with the route question, not after another dispatch.
4. The ledgers in §5, none urgent tonight.
5. He said this session ends when E08 closes — this handoff exists because the seat, not
   the session, ended. Do not end anything he has not ended.
