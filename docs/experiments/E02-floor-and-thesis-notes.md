> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — the floor was the codec, and A2 changes what the thesis is about

**Advisor notes, 2026-08-10. PROVISIONAL** — E02 is still open (see
[E02-STATUS.md](E02-STATUS.md)); these are working conclusions, not doctrine.

---

## 1. My floor measurement was wrong, and it was wrong in the way I flagged

I reported: *"the Cloud path is NOT deterministic under a fixed seed"* — 32 of 33 frames
differing, per-frame max 0→71, growing through the clip. **Measured on lossless frames, the
model's repeat variance is exactly zero: 3 of 3 pairs bit-identical across all 33 frames.**

The executor did not merely get a different number — **it reproduced mine and named its
mechanism.** The same two runs, measured both ways: max |Δ| 0 on the lossless frames, and on
H.264 an early/late profile of `[1,3,3,2,1]` → `[54,54,52,55]`. That is my reported shape,
produced from frames that are provably identical. The entire floor, *including its
frame-index structure*, is **H.264 encoder nondeterminism accumulating away from the
keyframe.**

**The precise nature of my error matters more than the fact of it.** I attached the right
caveat — "measured through a lossy codec on both sides, the true variance could be larger or
smaller" — and I mandated the lossless tap before A0 could run. That part worked; it is why the
error cost one paragraph rather than an arc. **What I did wrong was state a conclusion the
caveat could not support.** "The Cloud path is not deterministic" was not a finding with a
caveat; it was an *open question* I wrote in the indicative. The honest form was: *unresolved
until the tap exists.*

That is a distinct failure from my four falsified premises, and worth naming separately: not
*asserting an unmeasured fact*, but *reporting a measured number as evidence for a claim the
measurement could not reach.*

**Consequence, and it is large and good:** with a floor of zero there is nothing to subtract.
Arm differences read directly, at full sensitivity, and every later comparison in this arc is
cheaper and stronger than the spec assumed. The early/late split remains mandatory for anything
read off a **video**, and is moot on `lossless/`.

Their P1 missed too — registered 0 bit-identical pairs, measured 3 — and they say so plainly.
Two seats predicted nondeterminism and the machine was deterministic.

## 2. A2 — the null is not empty, and that is the most useful result so far

**Same prompt, same reference, no `control_video`. A2 also produces a horned armoured figure
that turns.** Had we never run it, the A1a sheet would have been read as "control works," and it
could not have been separated from "the prompt and the reference do this on their own."

**This is the row that makes E02 an experiment**, and it justifies the spec's insistence on it.

### What the panel shows, read off the artifact rather than a metric

- **A1a tracks the control's azimuth.** At each sampled frame the output's facing matches the
  control's facing, and the figure stays put — same scale, same position on its plinth,
  through the whole turn.
- **A2 drifts.** It turns, but it wanders in position and scale, and by f024–f032 it degenerates
  toward cape-with-legs — the body loses coherence while the costume persists.
- **A1a's figure is small in frame; A2's fills it.** A1a inherits the control's framing, where
  the subject was 226 px of 480. A2, unconstrained, composes for itself.

## 3. What the thesis is actually about — narrowed by evidence

armature's README says a video model *"cannot be told who is on screen and where they are
standing."* **A2 falsifies the first half and supports the second.** The model produced a
plausible *who* — horned helm, dark plate, ragged cape — from prompt and reference alone. What
it could not do without control was keep that figure **in one place, at one scale, turning on
cue**.

So the demonstrated division of labour is:

| supplied by | what |
|---|---|
| prompt + reference stack | **who** — costume, materials, character read |
| control sequence | **where, at what scale, and when** |

**The research grounding predicted exactly this split and we should say so.** F6 recorded that
VACE *"beats task-specific baselines on depth and pose control but loses reference-to-video"* —
structure is the solved leg, identity the weak one. E02's first evidence lands on the same
seam.

⚠ This does not mean identity is free. A2 kept *a* costume; whether it kept **this character**
across a longer shot, or across cuts, is E05 and E07 and is untouched.

## 4. The framing pre-registration resolves — differently than I expected

I pre-registered *"subject too small in frame"* as a candidate cause **if control did nothing**.
Control did something, so the escape hatch is not needed. But the observation has a consequence
I did not anticipate: **control imposes its framing.** A subject occupying 226 px of a 480 px
control frame produces a subject that small in the output, while the unconstrained arm composes
larger.

That is the mechanism working, not failing — but it makes **framing a creative decision taken at
render time**, not a detail. Whoever stages a shot is choosing the output's composition, and
they are choosing it in Blender.

## 5. On the temporal diagnostic — admitted as a diagnostic, gating nothing

Per-frame temporal energy correlated against the control's profile: **A1a +0.521, A2 −0.064**.
Estimator-free, so no licence question. The executor states plainly that it does not answer P3,
which is correct and is the right instinct.

**Admitted as a reported diagnostic; it gates nothing and decides nothing.** It has the one
property this repo demands of a metric — it takes clearly different values when the thing is
present and absent — but it has not been validated against an artifact the Director rejected,
which is the bar for promotion. Report it; never accept an arm on it.

## 6. My own instrument, caught and dropped

I tried to quantify §2's framing claim with a subject-coverage measure keyed on modal
background. **It is confounded and I am not reporting its numbers:** A1a's background is a lit
studio gradient, so the measure counted the gradient as subject and returned ~78–89% coverage
against A2's 32%. That is the denominator law again — *check what your denominator is made of* —
and the honest move is to state the framing difference from the panel, which is visible, rather
than dress it in a broken number.

## 7. State

- **6 of 12 generations spent.** Floor: zero. Gates L, B, C, 0: passed. Gate R: N/A, retained.
- **Unrun: A1b (polarity, P2) and A3 (Fun-Control cross-check, P4).**
- **P3 — whether the character is in the same place at the same time — is the Director's**, on
  the panel at full size. My reading is that A1a holds placement and timing and A2 does not, but
  the panel is his to judge and the eye is the verifier of record here.
