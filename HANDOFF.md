# THE HANDOFF — armature advisor seat, written 2026-08-11 evening

Supersedes the 2026-08-11 morning handoff (git history holds it — it was written mid-crisis
and organized around the audit; this one is written after the Director ruled and the repo got
back on track). Everything below was **measured at write time**, not recalled. Two seats were
live at write time and are marked IN FLIGHT — verify their outcomes before acting on them.

**Read CLAUDE.md first — its scope block outranks every other rule — then this file, then
verify every fact here yourself.**

---

## 1. What armature is — in the Director's words, now binding

> *"It shouldn't be at all limited to a game. You should be able to make cutscenes, movies,
> anything that you could do with image to video but with glb."*

**armature is image-to-video with a GLB instead of an image.** The deliverable is footage —
film, cutscenes, character poses and movement, any shot at all. A game is one consumer, never
the boundary. The scope was shrunk twice (a turnaround tool; a game-footage tool) and
corrected twice; **describing armature by a use-case is the drift signature**. This is no
longer prose: the scope block sits at the top of CLAUDE.md where every seat reads it first,
and **every credit-spending spec carries a `Trajectory` row** with the force of a licence row.
A spec that cannot fill it does not run. The public surfaces (README, handbook, roadmap, repo
description) were decontaminated of the shrinkage on 2026-08-11 — if you find a surface that
still shrinks the scope, that is a defect; fix it in place with a dated correction.

## 1b. armature and facet are ONE SYSTEM — they share a database

The repos share the **record-index** engine, now a published package
(`pip install record-index`, 0.1.0, OIDC attestations). facet's evidence trail is a queryable
SQLite+FTS5 database (`npx @mcptoolshop/facet` serves it; `facet-index q` from a checkout),
and **armature now has its own**: `docs/index/armature.db` + paired certificate +
`docs/index/conventions.json`, adapter at `tools/armature_index.py` — S02's deliverable,
merged 2026-08-11. The markdown stays canonical; an index is derived and wrong by definition
the day it is hand-edited.

**THE RULE, paid for twice in one day:** never advise, spec, or dispatch about the other repo
from memory, this handoff, or any summary. **Read its record or query it.** The F01 scope
error ("the surface job is faithful clay" — written without reading facet's route, whose
first box is *form-exaggerated clay concept*) and the venue error (an order banning the
measured twin venue and permitting the VRAM-falsified one) were both this failure. Both were
caught by the Director or the executor, corrected in place (F01, `f7a8b4e`, `88f1100`).

**Dispatched-seat model tiering:** the Agent tool inherits the dispatching session's model
when `model` is omitted — an expensive trap (F01's first seat ran Fable on route-following
until the Director caught the spend). Executor seats default to `opus`, `sonnet` for
mechanical sweeps; Fable only deliberately. Set the parameter on every dispatch.

## 2. The audit, and the Director's ruling on it

The repo-wide audit ([docs/audit-first-arc.md](docs/audit-first-arc.md), Amendment 1) is the
ledger of the first arc: 22 generations, ~88 credits, clean measurements of the mechanism,
zero frames of the product — because every instrument bounded validity and nothing bounded
value. **The Director ruled: continue, in place** (*"let's get this repo back on track so
that I don't have to start over from scratch"*). The method stays **experiments**, E-series,
aimed at the full pipeline, Comfy Agent consulted as needed. The audit's §5 conditions stand;
the roadmap now records its re-cut per its own header (docs/ROADMAP.md, "THE RE-CUT").

**What survives the audit as measured capital:** control governs where/scale/when (E02) and
authored subject motion categorically (E03); control owns the outline, reference owns
surface/material/costume, and can extend a silhouette only where control is silent (E06); the
between-generation floor is SD ≈ 0.16 at 33 frames vs exactly 0 fixed-seed (E04); at strength
1.0 with a body to paint, the model paints (E02 A1a). Identity — *is it the same character* —
remains the open canon question, judged only by the Director's eye.

## 3. The line — where the product work stands

| step | state at write time |
|---|---|
| **F01 / facet E33** — the first performer | **DELIVERED.** The Director's own clay-armature concept through facet's full route: `E:\AI\training\facet_E33\out\performer_textured.glb`, sha256 `9e20ea7d…b1aa`, 299,956 tris, one mesh, one 4096 atlas, terracotta (his r3 ruling), unrigged, 67 interior shells. His wood-grain note + the not-run brush stage (hand-interior texels are dilation fill) are standing notes for a finish iteration, NOT change orders |
| **E07** — the skeleton | **SKELETON APPROVED with reservation, bindings IN FLIGHT** (opus seat, worktree `E:\AI\armature-E07`, branch E07-run). The arc so far: bone heat bound zero weights (halt upheld, liveness clause adopted as law); pivots caught off the sculpted balls at the Director's zoom, re-derived from measured ball centers (elbows were 27–28% of segment off; his knee-read was vindicated by the offset table); skeleton approved 2026-08-11 **with his reservation on the record** — *"It's approved, but I'm not really happy with it"* — and the named future item **skeleton v2: articulated fingers** (needs finger bones AND a hand mesh that separates them; the mannequin sculpts a mitten-with-thumb). The two-binding comparison (envelope vs rigid-per-segment) is running; **his eye picks the binding from the sheet** |
| **E08** — the first authored performance | NEXT. Him, moving on purpose, reference stack carrying who he is. Spec opens with a Comfy Agent consult round (reference stacking, strength below 1.0 with a real body, the 81-frame class). This is the first frames of the actual product |

## 4. The publish chain — executed 2026-08-11 on the Director's green light

- **record-index 0.1.0 is LIVE on PyPI** (release v0.1.0 → OIDC → attestations), with the
  full treatment: 455-check suite (four real defects pinned as strict-xfails, named on the
  front page), landing page + 5-page handbook (Pages, HTTP 200), the Director's own mark as
  the banner (armature composition), README in eight languages staged with the release
  commit, SECURITY.md with a *measured* zero-egress claim, CHANGELOG, repo metadata.
- **armature S02 MERGED + CLOSED** ([S02-closing-ruling.md](docs/dispatches/S02-closing-ruling.md)
  rules the five open questions). armature CI green on the merge.
- **facet push: IN FLIGHT.** A sweep seat is clearing the 20 pre-existing hermetic failures
  (wheel-fixture deps resolution; source-scan guards re-pointing at code that moved into the
  package; one CRLF check; PAID_RE unfrozen from E01–E15), then pushes facet's ~5 local
  commits and watches CI to green. Verify it landed green before treating facet as current.
- **The 0.1.1 queue:** the four pinned record-index defects (verify-doubling, E-form arc
  regex, sub-ruling locator, declared-empty fields) + the certificate duplication resolving
  toward the package + whatever the facet sweep surfaces.

## 5. Working rules that earned their keep today

- **Query the record, don't recall it** (§1b). Both repos now have queryable indexes.
- **Speak the record's vocabulary to the Director** — twin, projection, brush, fill — never
  invented compressions. He knows the process; the jargon was the problem.
- **Look at the artifact before making claims about it** — the banner was rebuilt after being
  "matched" by dimensions alone; the reference was on disk the whole time.
- **Watchdog before any GPU work** (`pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1`
  — found dead once today).
- **Comfy Cloud GPU-hours are metered on this workspace.** "Zero credits" in facet's record
  means partner-API credits only; the six E33 twins moved GPU-hours ~$0.61. Report both meters.
- **The Director's standing preferences:** review video at 0.5× from lossless frames; dark
  means tone with colour in the shadows; judge at full size, never from a contact sheet;
  sheets are dailies (uniform panels, insets on the deciding regions, no debug states);
  metrics are diagnostics and his eye is the verifier of record; this is a marathon; do not
  end a session he has not ended.

## 6. This seat's error record — for your calibration

| error | correction |
|---|---|
| Specced a facet build without reading facet's route (clay ≠ final surface) | Caught by the Director in one line; orders corrected mid-flight; F01 A4 corrected in place |
| Ordered "local ComfyUI only" — banning the measured twin venue, permitting the falsified one | Reversed by venue ruling in F01 after the first seat surfaced the conflict |
| Dispatched an executor on Fable by omitting the model param | Wrapped at a stage boundary; successor on opus; tiering rule in §1b |
| Repeated facet's "zero credits" claim without its meaning | Corrected: partner credits vs metered GPU-hours, §5 |
| Invented jargon at the Director ("who the mascot is painted") | His correction; the vocabulary rule in §5 and in the memory store |
| Matched the armature banner's dimensions without looking at its composition | Rebuilt to the true layout after his catch |
| Sent the E07 halt sheet without examining its own insets | The Director caught misaligned joint pivots at his zoom — the bones sat off the sculpted ball-joints the character literally carries. Placement re-derived from measured ball centers; the look-at-images law violated twice in one day by the seat that polices it |
| Reused the blackguard as E07's subject after my own audit named the palette as starving the judgment | His catch; the survey → F01 commission replaced it |

**What worked:** independent verification before acting (the GLB hash, the CI watches, the
PyPI check), executors' state blocks enabling clean seat handovers, corrections landing in
place with dates, and the chain running end-to-end in one evening once the gate (tests) was
satisfied.

## 7. What to do first

1. Verify §3 and §4's IN FLIGHT items yourself — E07's delivery block and the facet sweep's
   CI conclusion. Do not inherit them.
2. When E07's skeleton approval sheet lands: it goes to the Director's eye, **pre-examined
   by you at his zoom first** — pivots on the sculpted balls, every inset. ⛔ **Nothing
   proceeds until he approves the skeleton** — not the binding arms, not E08, nothing
   downstream. After his approval: the two-binding comparison (envelope vs rigid-per-segment,
   his eye picks), then E08 — the first authored performance — opening with the Comfy Agent
   consult round, under the Trajectory row.
3. When the facet sweep lands green, the one-system state is fully current; fold anything it
   surfaced into the 0.1.1 queue.
4. Small leftovers, none urgent: `tools/invert_frames.py` adoption (E02 closing, Ruling 5);
   the roadmap stays maintained per its re-cut section; the E04/E06 artifacts still awaiting
   the Director's fresh eyes (`outputs/E06/sheets/`, `E04-C-bright-s4`) if he ever wants them.
