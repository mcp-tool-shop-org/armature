> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — CORRECTION: the turntable is our input, not armature's ceiling

**Director, 2026-08-10: _"How is armature being shrunk to just making turnarounds?"_**
He is right and this corrects the advisor's framing in
[E02-floor-and-thesis-notes.md](E02-floor-and-thesis-notes.md) §3–4 and in the fork the
advisor put to him verbally.

## What I did wrong

I read A1a as "a turnaround" and A2 as "a dramatic render", then offered a fork whose first
branch was *"if a rigid turnaround is the goal — sprite sheets, 8-direction assets — then
control at full strength is correct."*

**That is the shrinking pattern**, and it is named in this studio's own advisor doctrine: treating
a first result as a ceiling and proposing a smaller product that fits it. It would also have
handed armature's job to facet, which already produces turnarounds and does not need a video
model to do it.

## What the result actually says

The turntable is **not a property of armature**. It is the input we supplied, returned faithfully:

| what E02 fed the model | consequence |
|---|---|
| a **static mesh** — no animation, no pose change | nothing told the model to perform, so it didn't |
| a **camera orbit** around that static mesh | the only motion in the control *was* a turntable |
| **strength 1.0** — the node default, never chosen | maximum adherence, never varied |

A1a is a turntable because **we staged a turntable.** That is the control working, on the most
trivial scene that can be built.

A2's "step forward and swinging cape" is the mirror image: with no control, the model invented
motion because nothing constrained it. That is not drama outperforming control — it is an
unconstrained model improvising in the absence of instruction.

**Neither arm has tested the thesis.** armature exists for a character who *performs* — walks,
turns his head, swings a blade — while staying the same man. E02 tested *does control govern
placement at all*, which was the right first question and is answered yes. It never tested
performance, because no performance was ever authored.

## What follows

1. **Animate the subject and re-run.** Pose and animate the mesh in Blender, give the camera
   something a camera does, keep everything else fixed. This is the first test of the actual
   thesis and it costs one generation.
2. **Strength is a real question but it was premature and mis-framed.** Not *turntable versus
   performance* — that is a false choice created by an unanimated input. The real question is
   **how much the model may add on top of authored motion**, and it is only askable once there
   is authored motion to add to.
3. **The framing note stands** (control imposes its framing), but as a staging consideration,
   not a limit.

## The standing correction

**A first experiment's output is not the product's ceiling.** When a trivial input produces a
trivial output, the finding is about the input. Before proposing that a project narrow its
scope to match a result, check whether the result is merely the test design reflected back.