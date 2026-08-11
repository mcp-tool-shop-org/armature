# Random routes — kept alive on purpose

**Director's call, 2026-08-10:** *"We can keep FLF2V as a 'Random' Route… Not the main pipeline,
but we shouldn't abandon it entirely if that's its only fault. In time we can possibly tame it
with a structured prompt."*

## What a random route is, and why the repo has this file

This repo already keeps **falsified** approaches runnable in `tools/superseded/`, because *a
falsified approach that leaves the tree becomes doctrine again* — "we tried that, it didn't work"
hardens into folklore nobody can cite. This file is **the same law applied to the opposite case**:
a route that was never falsified at all, and whose only fault was not serving the arm we happened
to be building that week.

A **random route** is:

- **Not on the main pipeline's critical path**, and never a dependency of it.
- **Not abandoned.** It stays named, with its mechanism, its open questions, and what would have
  to be true for it to graduate.
- **Not held to the main route's cost discipline.** It rides a spare generation when one exists,
  rather than justifying a ceiling of its own.
- **Not doctrine in either direction** — neither "this is how we do it" nor "we ruled that out."

The bar to open one is deliberately low. The bar to let one quietly die is the thing this file
raises.

---

## RR-1 — FLF2V: authored keys, model-invented in-betweens

**Node:** core `WanFirstLastFrameToVideo` (separate node from `WanVaceToVideo` — not a VACE mode;
consult #4 corrected that filing). Takes `start_image` **and** `end_image`, both optional IMAGE.
**Has no `control_video` and no `control_masks` socket.**

### The advisor's error this route corrects

Consult #4's reasoning — which I adopted — was that FLF2V *"pins two frames and lets the model
invent the interior, but you already author every interior frame as dense control, so it risks
solving a problem your control already solves."* I ruled it near-closed on that basis.

**That reasoning is sound about the dense-control arm and wrong about the tool.** It grades FLF2V
on how well it duplicates the thing we already built, which is the *shrinking* family: judging a
capability by our current test design rather than by what it is. The Director stopped it.

### What it actually is, stated properly

**FLF2V is the arm where the model has freedom, and armature can give it the best possible
endpoints.** Most users of first/last-frame conditioning have to *guess* their endpoints — they
have chunk N's decoded last frame and must invent chunk N+1's. **We author both, exactly, from
geometry we own, on-model, for free.**

Pin two authored key poses; let the model generate the motion between them.

**That is in-betweening** — keys and in-betweens, the oldest workflow in animation — and it is a
**different instrument from dense control**, not a redundant one:

| | dense control (VACE) | FLF2V |
|---|---|---|
| what we author | every frame | two frames |
| what the model supplies | surface, light, life | **the motion itself** |
| the lever on what it invents | geometry | **prompt + reference** |
| cost to author a shot | a full Blender animation | **two poses** |

The last row is the one that could matter most to a studio. A route where a performance costs two
authored poses instead of an authored animation is not a lesser version of the main pipeline; it
is a different economics.

### ⚠ The honest risk, and it is the thing this route must be measured on

E02 measured that **control supplies where/scale/when, and prompt + reference supply who.** On
FLF2V the geometric anchor is *absent through the interior* — so prompt and reference carry both
identity **and** motion character, alone, exactly where we have the least evidence they hold.

**This is the route where identity is least protected.** That is not a reason to close it. It is
the thing any FLF2V experiment must measure first, and it is why this route does not go near the
main pipeline until it has been.

The Director's "tame it with a structured prompt" is the right instinct and names the right lever:
if the model owns the interior, the interior is governed by language and reference rather than by
geometry. **Structured prompting is the control surface of this route.**

### Open questions, in the order they would be asked

1. **Does the two-node stack even cohere?** VACE dense control + FLF2V endpoints are two
   conditioning nodes; whether they reinforce or fight is **unverified**. Cheapest possible
   discriminator, and it gates everything else about combining them.
2. **Standalone, with authored endpoints:** does the model produce plausible motion between two
   authored poses at all?
3. **Does the man survive the interior?** The identity question above — judged by the Director's
   eye, never by a metric.
4. **What does structured prompting actually move** — motion character, timing, both, neither?

### Status

**OPEN — no generations spent, no ceiling assigned.** It rides a spare generation. It is not
scheduled against E03, E04, or the `control_masks` work, and it blocks nothing.

**Licence:** core `WanFirstLastFrameToVideo` is **ASSUMED-FROM-CATEGORY, not verified** — a row
gets retrieved before it runs. `FL_WanFirstLastFrameToVideo` (Fill Nodes) is **UNVERIFIED → NO**;
do not substitute it.

---

## Graduation and closure

A random route **graduates** when a measurement shows it does something the main pipeline cannot,
at which point it gets a numbered experiment and a ceiling like anything else.

A random route **closes** only on a *measurement that falsifies it* — never on "it didn't fit the
arm we were building." When one does close, it moves to `tools/superseded/` with the measurement
that killed it, per the standing law.
