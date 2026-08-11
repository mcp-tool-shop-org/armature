# E04 — predictions, registered before the first submission

**Seat:** executor · **Registered:** 2026-08-10 · **Blind status: see below, and it is not a
clean yes.** · Committed to git before any new generation was submitted; the commit
timestamp is what makes this a prediction rather than a description.

---

## What I had already seen when I wrote these — the honest disclosure

A hypothesis with no prediction cannot be wrong, and a prediction registered by someone who
has already seen the answer is not a prediction. So, exactly:

**Blind to:** every quantity predicted below. **No new generation had been submitted**, no
between-seed comparison of any kind existed, and no run at any seed other than
`654654950714624` had ever been made on this route.

**NOT blind to** — I had, in building the instrument:

* E02's published values, recomputed: A1a **+0.5207**, A1b **+0.5813**, A2 **−0.0645**,
  corr(A1a, A1b) **+0.3428**, corr(A1a, A2) **−0.1130**.
* The **fixed-seed** floor on this statistic: A0r1/r2/r3 return **+0.5206918475**, all
  three, to ten decimal places. Exactly zero.
* That the codec moves this statistic by **~0.025** (A1a's H.264 frames read +0.5452 where
  its lossless frames read +0.5207), and that a *second H.264 encode of frames known to be
  bit-identical* reads +0.5509 — so re-encoding alone moves it ~0.006.
* That the control's energy profile is **bit-identical** under `255 − x` (max difference
  0.0 across all 32 deltas), so both conditions correlate against the same reference.

That last group is what my reasoning below is built from, and P1 leans on it hard. It is
knowledge of the *apparatus*, not of the answer — but a reader should judge for themselves
whether it amounts to a partial peek, so it is listed rather than summarised.

## Definitions, fixed here so the experiment cannot move them

Chosen before any number exists, because a definition chosen afterwards is a result.

| term | definition |
|---|---|
| **the statistic** | `measure_tracking.py`'s timing correlation: Pearson of `d(t) = mean\|f(t) − f(t−1)\|` against the control's own profile, grayscale, 33 frames → 32 deltas |
| **within-condition spread** | sample standard deviation (`ddof=1`) of the 6 values in one condition. **Range (max − min) is reported beside it**, always, and predicted separately |
| **between-condition gap** | \|mean(C-dark) − mean(C-bright)\|, over 6 values each |
| **the pixel statistic** | `measure_floor.py`'s existing unit — per-frame mean absolute difference on RGB between two runs' `lossless/` frames, averaged over the 33 frames — for each of the 15 within-condition pairs |

**There is no pass condition, and inventing one here would be this repo's most expensive
recorded error.** Every prediction below is a registered guess that can miss. None of them
is a threshold anything is graded against.

---

## P1 — the within-condition spread of the timing correlation

**Reasoning, stated before the number so the number can be judged against it.** E02
measured corr(A1a, A1b) = **+0.343** between two generations that each track the control at
~0.55. If two outputs shared *only* their control-driven component, that cross-correlation
would be ≈ 0.521 × 0.581 = **0.303**. Measured 0.343 — close. So each generation's temporal
energy profile is roughly *the control's signal plus a large, generation-specific,
independent part*, and the independent part is the majority of the variance.

A Pearson r over n = 32 points estimating ρ ≈ 0.55 has a sampling standard error of about
(1 − ρ²)/√(n−1) = 0.70/5.57 ≈ **0.125**. A new seed draws a new independent noise profile,
which is structurally the same situation. That is the high estimate.

Against it: the only empirical hint is that A1a and A1b — two different generations —
landed 0.0606 apart. For two independent draws E\|Δ\| ≈ 1.128σ, implying σ ≈ 0.054. **That
is an n = 1 estimate and worth very little**, but it points the other way, so I sit between
the two and lean toward the theory.

| clause | registered |
|---|---|
| **P1a** — within-condition SD of the statistic | **≈ 0.08**, band **0.04 – 0.15** |
| **P1b** — SD versus the 0.060 gap E02 could not read | **SD > 0.060** — the spread exceeds the gap |
| **P1c** — range (max − min) across 6 seeds | **≈ 0.20**, band **0.10 – 0.38** |

P1b is the clause that matters and it is the one I am least sure of: if the true SD is near
the low end of my band, 0.060 sits right on top of it and P1b is a coin flip.

## P2 — is the spread the same in both conditions?

**Predicted: YES**, and I predict the experiment **cannot show otherwise even if it is not**.

Mechanism: the two conditions' control profiles are bit-identical under `d(t)` (measured,
0.0), E02 established the model reads the control's geometry rather than its tone, and the
measured tone carry was 11.7 output levels from a 233-level provocation — about 5%. The
process that generates seed-to-seed variance is the sampler's noise draw, which is the same
object in both arms.

| clause | registered |
|---|---|
| **P2a** — the two SDs land within a factor of **2** of each other | **YES** |
| **P2b** — the measurement has the power to separate them | **NO.** With 6 values per condition, an F-ratio on 5 and 5 df puts the 95% interval for a true SD ratio of 1 at roughly **[0.35, 2.9]** — so a 2× observed difference is what *identical* spreads look like |

**P2b is a prediction about the instrument, and it can miss in an informative direction:**
if the two SDs come back differing by *far* more than 2×, that is evidence the floor is
condition-dependent and a single floor number is not portable — which the spec names as a
finding in its own right.

## P3 — the pixel statistic, whose fixed-seed floor is exactly zero

*A row predicted to be uninformative is still a prediction and can still miss.*

| clause | registered |
|---|---|
| **P3a** — mean \|Δ\| between two different-seed runs in one condition | **≈ 25 / 255**, band **12 – 45** |
| **P3b** — bit-identical pairs among the 15 within-condition pairs | **0 of 15**, both conditions (against A0's 3 of 3 at a fixed seed) |
| **P3c** — the spread of that pairwise value across the 15 pairs | **SD ≈ 5 levels**, band 2 – 12 |

**P3's row is where the spec's warning bites hardest.** The pixel statistic's fixed-seed
floor is 0 and its between-seed value will not be, so the ratio "between-seed over
fixed-seed" is a division by zero. It is not a large ratio; it is an undefined one. The row
is informative *categorically* — the two floors are different kinds of quantity — and
carries no number that any arm comparison should be read against. **If a later document
quotes a pixel ratio from this experiment, it has misread it.**

## P4 — the gap against the floor. Registered BEFORE computing it

| clause | registered |
|---|---|
| **P4a** — is the between-condition gap larger or smaller than the within-condition spread? | **SMALLER** |
| **P4b** — the gap of the two means | **< 0.060**, and I expect roughly 0.02 – 0.05 |
| **P4c** — do the two conditions' six-value ranges overlap? | **YES, they overlap.** Complete separation of the twelve values into two blocks is a clean miss |

**Why smaller.** If P1a is right at ≈ 0.08, the standard error of each condition's mean is
0.08/√6 ≈ 0.033 and of their difference ≈ 0.046. A true gap would have to be substantial to
clear that. E02's 0.0606 was a difference between two single draws, so it carries two
noise terms; averaging six per side should pull both toward their condition means and
shrink it.

**No confident direction is registered for the sign of the gap.** E02 found near-dark above
near-bright by 0.060 at one seed. I am registering that I expect that ordering **not to
reproduce reliably** — which is what P4c makes falsifiable. Registering a direction I have
no mechanism for would be noise wearing a prediction's clothes.

## What each outcome would mean — written now, so it cannot be written later

* **The floor swallows the gap** (P1b, P4a, P4c all hold): E02's polarity comparison was
  unreadable, and we will have *proven* that rather than assumed it. **A full success**, and
  every future arm comparison gets designed against a measured number instead of a hope.
* **The floor is much smaller than the gap** (P1b misses): the 0.060 gap was readable after
  all, E02's refusal to rank was conservative rather than wrong, and A1b really did track
  differently. Also a full success, and a more expensive one, because it means the standing
  constraint from E02's Ruling 2 can be relaxed with a number attached.
* **The two conditions disagree about their own spread** (P2a misses badly): a single floor
  number is not portable and every statement of the form "the floor is X" needs its
  condition named.

---

## Projected spend — stated before the first submission

| | |
|---|---|
| planned | **10 generations** — 5 new seeds × 2 conditions |
| reused, costing nothing | **2** — A0r1 (C-bright seed 1) and A1b (C-dark seed 1), both already on disk and hash-verified |
| **projected cost** | **40 credits** (premise 3: 4 credits per generation, MEASURED in E02 from the Director's balance delta 14,284 → 14,280) |
| **ceiling** | **12 generations / 48 credits** — 2 held in reserve for a fired gate |
| Gate C | halts if any submission would take the count past 12 |

**A note on the unit, because the number should not be quoted more precisely than it is
known.** The Comfy usage report is dollar-denominated and exposes no credit balance, so the
credit figures above come from E02's measured per-generation cost and not from a balance
read today. For context, the two GPU-hours day buckets covering E02's and E03's runs
(2026-08-10 and 2026-08-11) total **$1.26** across 10 generations plus other workspace
activity — which bounds a single generation well under $0.20 but does not attribute it.

**Spent credits have no compensator.** That is why the ceiling is stated here, before the
first submission, rather than reconciled afterwards.
