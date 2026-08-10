# E02 closing ruling — first contact, and what it does and does not establish

**Seat:** advisor · **Ruled:** 2026-08-10 · **Arc:** E02, first contact between a rendered
control sequence and a video model · **Status entering this ruling:** EXPERIMENTING

This ruling consolidates the arc. Eight interim documents were written one per message, which
was the outgoing seat's error and is corrected here by closing once.

## 0. The record after this ruling

**These stand as the durable record — read these:**

| document | what it holds |
|---|---|
| [E02-first-contact.md](E02-first-contact.md) | the spec, with its amendments in place |
| [E02-predictions.md](E02-predictions.md) | every prediction, with its registration timestamp and blind status |
| [E02-report.md](E02-report.md) | all four parts, every measurement, with its own corrections in place |
| [E02-CORRECTION-not-a-turnaround-tool.md](E02-CORRECTION-not-a-turnaround-tool.md) | the scope correction the Director made. **Load-bearing; do not fold away** |
| this document | the ruling |

**These are SUPERSEDED by this ruling** and stay in the tree as the trail that produced it —
`E02-halt-ruling.md`, `E02-canon-ruling.md`, `E02-bridge-ruling.md`,
`E02-gateC-and-noise-floor.md`, `E02-floor-and-thesis-notes.md`, `E02-STATUS.md`. Nothing in
them is deleted; where one conflicts with this document, this document governs.

---

## Ruling 1 — What E02 establishes

Three generations bear on the thesis: **A1a** (near-bright depth control), **A1b** (the same
control inverted to near-dark), **A2** (no control at all). Timing correlation against the
control sequence:

| arm | timing correlation |
|---|---|
| A1a — control present, near-bright | **+0.521** |
| A1b — control present, near-dark | **+0.581** |
| A2 — no control | **−0.065** (derived: \|A1b−A2\| 0.646) |
| A1a with A1b | +0.343 |

**Established:** a rendered control sequence governs **where** the figure is, **at what scale**,
and **when** it moves. Both control arms sit far from the no-control arm; the gap between either
control arm and A2 is an order of magnitude larger than the gap between the two control arms.

**Also established, and it is the useful thing A1b bought:** control **polarity does not break
tracking**. Inverting the depth map end-to-end — a full-image `255 − x`, the largest change that
can be made to a control without changing its geometry — left the arm tracking. Whatever the
model is reading, it is reading the **geometry**, not the tone.

**The tone carry, measured:** a **233-level** swing in control luma produced an **11.7-level**
swing in output luma, in the same direction. Tone does leak, and it leaks at roughly 5% of the
provocation. That is a diagnostic worth carrying forward, not a result to act on yet.

**NOT established, and I am ruling against the reading:** that A1b tracks *better* than A1a.

## Ruling 2 — P2's numeric clause MISSED, and the executor's refusal to bank the miss is UPHELD

Registered: timing correlation **+0.30**, predicting A1b would track *less* well than A1a's
+0.521. Measured: **+0.581** — a miss, in the direction the executor did not expect.

The executor then refused to claim A1b tracks better, and wrote the reason down. **That refusal
is upheld, and the reasoning is worth preserving as the ruling:**

> The difference (0.581 vs 0.521) is **exact, not noisy** — repeat runs are bit-identical, so
> this statistic has zero measurement variance. **Zero measurement variance is not evidence of a
> real ordering.** It is two numbers from two single generations.

This is the sharpest thing in the arc. A quantity with no measurement noise still has **sampling**
variance across generations, and the two are different things. The floor E02 measured — **zero** —
is the floor for *re-running the same submission*, not the floor for *drawing a second sample from
the model*. **The between-generation floor has never been measured on this route**, and until it
is, no single-run gap between two arms may be read as an ordering.

**That is the standing constraint this arc produces**, and it applies to every future armature
experiment that compares two arms at one generation each.

## Ruling 3 — The withdrawal of clause B is UPHELD, and it is the law working

The original P2 clause B read *"A1a-vs-A1b exceeds A0's floor by more than 3×."* The floor
measured **zero**, so any nonzero difference satisfied it trivially — a clause that could no
longer fail.

The executor **withdrew it, did not re-derive it, and re-registered before A1b existed**, at
`d5fa350` / 19:24:59, timestamped in git. That is exactly what the law asks: *withdraw a broken
condition rather than re-derive it while looking at the results it would judge.* A check that
cannot fail is not a check, and the honest move on discovering one is to say so and stop using it.

**Upheld without qualification.** The re-registration's own timestamp preceding the artifact is
what makes it a prediction rather than a description.

## Ruling 4 — The direction clause and P3 are the DIRECTOR'S, and stay open

The executor pre-defined "as well" as **at least 28 of 33 frames** carrying the figure in the same
region with the same facing, **judged by eye**, precisely so that no metric of its own could settle
it — and then declined to settle it. Correct on both counts.

**Open, and gated on the Director's eye:**

1. **P2's direction clause** — 28 of 33, on `outputs/E02/sheets/E02-A1a-vs-A1b-polarity.png` and
   the 8 fps review clip, at 0.5× from `lossless/`.
2. **P3** — awaiting the same look.
3. **P4** — unmeasured; A3 is deferred by ruling and is not run.

**E02 does not close until those are ruled.** Merging this branch is bookkeeping, not closure —
the arc stays **EXPERIMENTING** and nothing in it is promoted to CLAUDE.md.

## Ruling 5 — Contamination #4: the files stay untracked, and the disposition is mine

`tools/invert_frames.py` (19:26:50) and `tests/test_invert_frames.py` (19:27:31) were written into
a **live executor's working tree** by another seat, after that executor's 19:24:59 commit. Not by
this seat — this advisor has written nothing into `E:\AI\armature`'s working tree at any point.

**The executor's handling was right on every axis** and is upheld: left untracked (committing them
would attribute another seat's work to the executor), not deleted (worse — it would destroy both
the evidence and the work), reported, and — the part that matters most — it **re-measured a number
it had already committed**. The report said "130 tests pass" while the suite reported 140, because
the foreign file was being collected. Measured both ways: **130 without it, 140 with it. 130 is the
executor's count**, and the committed figure was corrected in place.

**This is the fourth cross-seat contamination in this project, and the first that a `git worktree`
practice could not have prevented** — the standing rule covers *commits*, and no commit appeared. A
plain `Write` into a live executor's tree is the same class of event and is now named as such.

**Amendment to the standing practice, effective now:** while any executor session is live, the
advisor writes **nothing** into that seat's working tree — not a commit, not a file. Authoring
happens in a detached worktree. The rule's scope is the *tree*, not the *branch*.

**Disposition of the two files:** the transform is wanted as a recorded, re-runnable tool — a
recipe that does not reproduce its output is not a recipe, and 10 passing tests ride it. They are
**adoptable, but not into E02's commit**, because the executor's count must stay honest at 130 and
because attribution is the whole point of the report that surfaced them. They remain untracked in
the working tree and are adopted, if adopted, by a **separate advisor-authored commit** after the
Director has ruled on the open clauses. Nothing is deleted.

## Ruling 6 — The `E03-authored-motion` branch is a STALE POINTER. Delete it after this merge

The handoff flagged this as an ambiguity to resolve before anyone built on it. **Resolved, by
measurement and by the executor's own account:**

* Its tip `e7b8806` is E02's first seven commits **rebased**, different hashes.
* Its tree is a **strict subset** of `E02-first-contact` — the two differ by exactly the 72 lines
  of `E02-predictions.md` that the P2 re-registration (`d5fa350`) added. It carries **nothing**
  unique.
* It is **local-only** — never pushed; `origin` carries only `main`.
* **Cause, from the executor:** its working tree was checked out on `E03-authored-motion` — a
  branch it did not create — so its first rebase moved *that* pointer instead of
  `E02-first-contact`. It then switched to the branch the dispatch named and left this one alone.

**Ruled: it contains no E03 work and nothing unique. It is safe to delete once this merge lands**,
and it must be deleted before E03 starts, so that E03 branches clean from `main` and nobody
inherits a pointer named for an experiment it does not contain.

## Ruling 7 — Credits

**7 of 12 generations spent. 5 unspent.** A1b cost one generation (4 credits) as specified. **A3
was not run**, deferred by ruling, and this ruling does not revive it — its information value has
not been argued against its cost since the deferral.

E03's ceiling is 4 generations, which fits inside what remains. **No new spend is authorised by
this ruling.**

## Ruling 8 — What the arc says about armature, stated carefully

E02 was **first contact**: does a rendered control sequence govern a video model at all? It does.
Position, scale and timing follow the control; identity does not come from it. That is the hinge
the repo was built on, and it held on first contact.

**What E02 is not.** It is not a finding about identity-through-motion, which needs the
anatomically-named-bone gap closed first. It is not a finding about authored motion — that is E03,
whose whole question is whether a control that *moves on purpose* is followed on purpose. And it is
**not** evidence that armature is a turnaround tool. The subject of A1a/A1b was a turntable because
that is the input we had, and the outgoing seat mistook the test design for the product. **armature
is a video tool: a character who performs and stays the same man.** That correction stands and is
the reason `E02-CORRECTION-not-a-turnaround-tool.md` is not folded away.

## Ruling 9 — This seat's error record for the arc

Carried because the next seat should know which parts of the record to distrust:

* **The outgoing advisor's**, recorded in the handoff and not re-litigated here: four falsified
  premises, a gate that could not fire, a floor that measured the codec, a conflation of
  byte-exactness with lossless transport, three cross-seat contaminations, the shrinking pattern,
  and a confounded coverage instrument.
* **This seat's**, in this session: none in this document. One in the E32 ruling, recorded there —
  a name-based grep reported as an enumeration.
* **The sprawl itself** — eight interim ruling documents where one closing ruling was needed. That
  is what this document exists to end, and the next arc closes once.

---

## What the Director is asked to look at, and nothing else blocks on it

1. `outputs/E02/sheets/E02-A1a-vs-A1b-polarity.png` — control | output for both polarities.
2. The **8 fps review clip at 0.5×**, built from `lossless/`, not from re-encoded video.

The question is P2's direction clause as pre-registered: **for at least 28 of 33 frames, does
A1b's figure occupy the same region and face the same way as A1a's?** That count is yours; no
metric in this arc is permitted to make it.
