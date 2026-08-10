> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — Gate C closed, and the noise floor is not zero

**Ruled 2026-08-10.** Closes the Gate C hold from
[E02-bridge-ruling.md](E02-bridge-ruling.md) §3, and records a measurement that changes how
every later arm in this arc must be read.

---

## 1. GATE C — CLOSED. 4 credits per generation.

No programmatic surface exposes it — `estimate_credits` returns 0 because Wan's entire cost is
the GPU time that estimator excludes, the invoice lags with no bucket for the day, and the job
record carries no cost field. The Director found the instrument that does work: **the workspace
credit balance**, read either side of a single generation.

| | |
|---|---|
| balance before | **14,284** |
| balance after one generation | **14,280** |
| **observed cost** | **4 credits** — 33 frames, 480×832, Wan 2.1 VACE 14B fp16, 30 steps |

**The arithmetic Gate C exists to force:**

| | credits | share of balance |
|---|---|---|
| 12-generation ceiling at the observed rate | **48** | **0.336%** |
| same ceiling if a cold run costs 5× | 240 | 1.68% |
| same ceiling if a cold run costs 10× | 480 | 3.36% |

**Gate C clears decisively and the ceiling stands at 12.** Even on the pessimistic assumption
that every remaining run costs ten times the observed figure, the whole experiment consumes
under 4% of the balance.

⚠ **Treat 4 as a lower bound, not the price.** The measured run completed in seconds where the
first took ~5 minutes — almost certainly a **warm worker**, since run 1 paid the cold load of a
28 GB fp16 model and run 2 did not. If billing tracks GPU seconds, a cold run costs more. The
bracket above is why this does not matter: the conclusion is insensitive to a 10× error.

**Method note worth keeping.** A balance delta is a *better* instrument than the invoice
report, not a worse one — it is observed rather than reported, it needs no per-job attribution,
and it arrives immediately. Where a system exposes no per-unit cost, **bracket the unit by
differencing a total across exactly one unit.**

## 2. THE NOISE FLOOR — the Cloud path is NOT deterministic under a fixed seed

The rerun was submitted **byte-identical**: same payload, same seed `654654950714624`, same 33
uploaded control frames, same reference. It is therefore A0's first repeat pair, and it says the
provider does not reproduce.

| | |
|---|---|
| frames differing | **32 of 33** |
| per-frame max abs delta | min **0** · median **37** · max **71** |
| mean abs delta across all frames | **0.176** |
| pixels differing by more than 8 | **0.304%** |

**And the divergence grows through the clip** — this is the most useful part of the shape:

| frames | max abs delta |
|---|---|
| 0–4 | 0–2 |
| 29–32 | 54–71 |

Early frames are essentially identical; late frames diverge substantially. That is the signature
of a sampler whose tiny early differences **compound along the temporal axis**, and it means the
floor is not a single number — *it is a function of frame index*.

### What this obliges every later arm to do

1. **No arm-to-arm difference below this floor means anything.** A 0.3% pixel-difference result
   would be indistinguishable from running the same payload twice.
2. **A comparison must report early and late frames separately**, or a late-clip difference will
   be read as an effect when it is the floor.
3. **A0's three submissions are now clearly necessary, not ceremonial.** One pair gives a floor;
   three give a spread, and the spread is what a later arm is actually measured against.
4. The first frames being near-identical is itself informative: **the control's grip is
   strongest where the floor is smallest**, so the early frames are where a control effect will
   be cleanest to see.

### The caveat that limits this number, and the cheap fix

**This floor was measured through a lossy H.264 codec on both sides.** The graph's only output
is an mp4; it saves lossless PNGs of the *control batch* but nothing lossless of the *output*.
So the measured deltas contain codec noise of unknown size, and the true model variance could be
larger or smaller.

**Spec amendment, before A0 runs properly:** add a `SaveImage` on the `VAEDecode` output
(node 8) alongside the existing `CreateVideo`/`SaveVideo` path. It costs no extra generation —
the frames already exist in the graph — and it turns the floor from *measured through a codec*
into *measured*. **A0 does not run until that tap exists**, because a noise floor measured
through an uncharacterised codec is exactly the moving denominator this repo keeps paying for.

## 3. Process — my own role drift, stated

**I executed a generation and measured its output.** That is executor work. The Director asked
for the run directly and the measurement followed immediately from it, but the seat that rules
on results should not be grading output it produced.

So, precisely: **§2 is a measurement, not a ruling.** It is recorded so the number is not lost
and so the spec amendment can be written, and **the E02 executor should reproduce the floor
independently** — with the lossless tap in place — before any arm leans on it. If their number
disagrees with mine, theirs is the one that counts.

§1 is a ruling and is properly mine: the Director supplied the observation, the arithmetic is
arithmetic, and the conclusion is insensitive to the one uncertainty in it.

## 4. State after this ruling

- **Generations spent: 2 of 12.** Both arm A1a, identical payloads, the second bought a price
  and a floor.
- **Gate C: CLOSED.** Gate B: PASS. Gate L: PASS. Gate R: N/A (retained). Gate 0: pending the
  Director's eye on the sheet.
- **Next:** add the lossless output tap, then A0's three submissions, then the arms. A2 — the
  no-control row — remains the one that makes this an experiment rather than a demonstration.
