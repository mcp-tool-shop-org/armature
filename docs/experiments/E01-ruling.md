# E01 — advisor ruling

**Ruled 2026-08-10.** Report: [E01-report.md](E01-report.md). Spec:
[E01-control-sequence-exporter.md](E01-control-sequence-exporter.md).

**Verdict: accepted.** The exporter is built, 103 tests pass (re-run at ruling time), G3 shows
byte and pixel identity across two process pairs, and a gate fired on a real defect. Two
decisions were referred up; both are ruled below. One premise of the spec was mine and was
wrong for the third time in two dispatches, which is the most useful thing in this document.

---

## 1. RULING — the post-fix character arm is ADMISSIBLE

Referred by the executor, who was right to refer it rather than decide it.

G4 fired at frame 0 of the character arm. The executor halted, diagnosed read-only, changed no
parameter, found that Blender's glTF importer creates a hidden `glTF_not_exported` collection
holding a radius-1.0 Icosphere, and that selecting geometry by `type == "MESH"` swept it into
the subject — inflating both G4's expected bbox and, silently, the auto camera radius.

This clears facet's E23 boundary on every clause:

| Requirement | Met? |
|---|---|
| The gate measured the *instrument*, not an inconvenient result | **Yes** — the defect was in the exporter's subject selection |
| No parameter was tuned to get past it | **Yes** — G4's tolerance is untouched |
| The repair **adds capability** rather than removing coverage | **Yes** — correct subject selection; nothing was narrowed |
| Coverage-removing alternatives named and rejected | **Yes** — the report rejects loosening G4 |
| The firing is reported as a fired gate, not smoothed green | **Yes** — reported as a halt |
| The edit is proven **non-perturbing** | **Yes, and this is the clincher** — the primary re-run pre-fix vs post-fix differs by **0 pixels and 0 bytes** |

That last row is what makes this a repair rather than a re-roll. The executor did not assume
the fix left the passing arm alone; it measured, and the measurement is identity. **G4 did
exactly what a gate is for** — it caught a defect that the silent half (camera radius) would
otherwise have carried into every later experiment unnoticed.

## 2. RULING — both normalizations ship. Do NOT create a `depth/` alias.

The executor emitted per-frame and per-shot depth side by side and **refused to name either
`depth/`**, on the grounds that naming one is choosing. That is correct and it is the ruling.

The spec deferred the choice to E02 and it stays deferred. No alias, no default, no symlink —
the directory called `depth/` comes into existence in the commit where a measurement chooses
it, and not before. E02 arms the two against a real generation.

**P3's measurement, for the record:** registered 0.12, measured 0.060 (sword) and 0.085
(character). Over-predicted on magnitude, half right on direction — near surfaces do darken
under per-shot, but so do most far surfaces, and the crossover sits at level 56/112 of 255
rather than near the middle. The prediction was wrong in a way that teaches something, which
is the point of registering it.

## 3. My third falsified premise, and the pattern is now undeniable

The spec named `longsword_hero.glb` **"a facet-finished asset, the natural primary (armature is
downstream of facet)"** — for a character-staging tool. Measured at ruling time:

```
extents X/Y/Z: 0.226 × 1.002 × 0.063     aspect (longest/shortest): 15.8
```

**It is a hero longsword.** A weapon prop. A standing figure runs nearer 6:1 with real depth in
two axes; this is a blade. P2's "no armature" result and the whole shape of the primary run
follow from it, and the executor inherited my reading until the contact sheet showed a sword.

**The mechanism, and it is the one this lineage keeps recording.** The spec's premise table
marked premise 2 **MEASURED** — "enumerated 2026-08-10; 15+ found under `E:\AI\training`". What
I actually measured was that *files exist*. I never opened one. That is precisely
*a real population whose members you never checked for the property*: the population was real,
every member was real, and the property I needed — **is this a character** — was never checked
for a single one.

Three dispatch premises falsified in two dispatches, all the same shape:

| # | Premise | What I did | Truth |
|---|---|---|---|
| 1 | "Pages deployment is unresolved org-wide" | measured 2 repos | 71 of 71 deploying repos use a workflow build |
| 2 | "Mirror anchor's site config exactly" | read a sibling repo | Starlight 0.39 removed that shorthand; it will not build |
| 3 | "`longsword_hero.glb`, the natural primary" | listed filenames | it is a sword, 15.8:1 |

Each time I asserted an *environmental fact* from a cheap proxy — a two-repo sample, a sibling's
frozen config, a directory listing — and each time the proxy was one command away from the truth.

**Standing correction, effective now:** a premise may be marked `MEASURED` only if the
measurement tested **the property the spec depends on**, not merely the existence of the thing.
Where the spec depends on *what an asset is*, the premise line carries the measurement that
opened it. The executor's own P2 miss has the same shape — taking `_rigged` in a filename as
evidence of a rig — so this is not a seat-specific failure; it is what filenames do to both
seats.

## 4. The finding that changes the roadmap: the pose channel is blocked on assets, not code

P2 measured 2 of 4 files carrying a usable armature, against a predicted 3. **P2b missed
harder and matters more: 0 of 4.** Both real rigs name their bones `bone_0…bone_29`, so **no
anatomical joint is identifiable by name in any asset on this rig.**

F20's OpenPose-18 convention is an *anatomical* mapping — nose, shoulders, elbows, wrists, hips,
knees, ankles. A skeleton of `bone_0…bone_29` cannot be mapped to it without a human declaring
the correspondence. So the pose channel is not blocked by the exporter; it is blocked by asset
provenance. G5 is correctly `NOT RUN`.

Folded into the roadmap: **the pose channel needs an explicit joint-naming or retarget step that
did not exist in the plan.** F1 softens the cost — Champ measured skeleton-only as the weakest
signal and dense depth+normal as the strong one — so the four channels that *do* emit are the
ones the evidence favours anyway. The gap is real and it is not on the critical path.

## 5. Accepted without change, and worth keeping

- **Five Blender 5.2 API shapes falsified before being built on** — `scene.node_tree` is now
  `compositing_node_group`; `CompositorNodeComposite` is gone; `base_path`→`directory`;
  `file_slots`→`file_output_items`; per-item format gated behind `media_type`. This is a
  standing environment fact for every later experiment, not an E01 detail.
- **The `glTF_not_exported` Icosphere is a general trap.** Any Blender tool importing glTF and
  selecting by `type == "MESH"` inherits it. It is now in the environment section below.
- **The Blender licence row moved out of UNVERIFIED** by reading the installed build's own
  bundled documents rather than the website that still 403s — a better primary source than the
  one the spec asked for, because it is the licence of the exact binary that ran.
- **The judging-word sweep.** The executor grepped its own report for the forbidden vocabulary
  and tightened everything that read ambiguously. Four survivors were quotations of the spec.

## 6. The blindness corroboration — produced by my own error

The executor's predictions are timestamped in git at **15:14:22**; its first measurement ran at
**15:32:49**. Neither timestamp is a seat's to author, so blindness does not rest on anyone's
word.

That evidence exists **because I swept the executor's in-progress report into an S01 commit with
`git add -A`** and recorded the error. A mistake that corrupted provenance in one direction
happened to create independent provenance in another. Worth noting precisely so nobody
mistakes it for a designed control — it was luck, and the honest record is what made the luck
legible.

## 7. And I did it again — second cross-seat contamination, different mechanism

At ruling time the branch `E01-control-sequence-exporter` pointed at **my logo/favicon commit**,
not the executor's. The executor left HEAD checked out on its branch; I ran `git commit` in that
repo without checking what branch I was on, so unrelated brand assets landed on top of E01's
work.

Repaired locally before this ruling (nothing had been pushed): the logo commit was cherry-picked
onto `main` as `e8a94c6`, and `E01-control-sequence-exporter` was reset to its own tip
`de4f73d`. The branch now differs from main by E01's files alone.

Two contaminations in one day from one root cause — **acting in a shared repo without checking
what the other seat has left there.** The first correction covered staging (`git add -A`); it
did not cover the branch pointer. The rule is now the general one: **check `git rev-parse
--abbrev-ref HEAD` and stage by explicit path, every time, while another seat is live.**

## 8. Awaiting the Director

Nothing here is pushed. What needs his eye rather than a measurement: the six-channel contact
sheets for both subjects, and whether the character arm — measured on a tool that only ever
produced it post-fix — reads correctly to him. My ruling admits it on the evidence; the artifact
is still his to judge.
