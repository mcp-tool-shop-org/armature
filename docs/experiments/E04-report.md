# E04 — report: the between-generation floor, measured

**Seat:** executor · **Run:** 2026-08-10 · **Advisor rules after this** · **Director judges the
sheets** · Predictions registered blind at [`E04-predictions.md`](E04-predictions.md), committed
`6808489`, **before the first submission**.

**There is no pass condition in this experiment and none is invented here.** The spread and the
gap are reported side by side. What they mean is not this seat's to say.

---

## 1. Predictions, scored first — 7 hit, 3 missed, 1 split

Registered blind; the blindness disclosure is in the predictions document and is not a clean
yes — I knew the apparatus (E02's five values, the fixed-seed floor of zero, the codec shift)
and was blind to every predicted quantity.

| clause | registered | measured | verdict |
|---|---|---|---|
| **P1a** within-condition SD | ≈0.08, band 0.04–0.15 | **0.169** / **0.157** | **MISS** — above the band |
| **P1b** SD vs E02's 0.060 gap | SD > 0.060 | 0.163 mean SD = **2.7×** the gap | **HIT** |
| **P1c** range across 6 seeds | ≈0.20, band 0.10–0.38 | **0.464** / **0.417** | **MISS** — above the band |
| **P2a** the two SDs within 2× | yes | ratio **0.93** | **HIT** |
| **P2b** can the measurement separate them | no | 0.93, inside [0.35, 2.9] | **HIT** |
| **P3a** pairwise mean \|Δ\| | ≈25, band 12–45 | **34.3** / **40.1** | **HIT** on the band |
| **P3b** bit-identical pairs | 0 of 15, both | **0 / 15** and **0 / 15** | **HIT** |
| **P3c** SD of that pairwise value | ≈5, band 2–12 | **5.98** / **14.00** | **SPLIT** — C-dark outside |
| **P4a** gap vs spread | SMALLER | gap = **0.79 SD** | **HIT** |
| **P4b** the gap of means | < 0.060, expect 0.02–0.05 | **0.129** | **MISS** — and in the direction I did not expect |
| **P4c** do the ranges overlap | yes | **YES** | **HIT** |

### The three misses are one mistake and one wrong mechanism, and both are worth recording

**P1a and P1c are the same miss: I underestimated the spread by about 2×.** My reasoning
offered two estimates — a sampling-theory figure of ~0.125 and an n=1 empirical hint of ~0.054
— and I wrote that the n=1 estimate was "worth very little" and then **let it pull my number
down anyway**, to 0.08. Theory alone would have landed inside its own band. Writing down that
a piece of evidence is weak is not the same as declining to use it.

**P4b missed on a mechanism I had backwards, and the correction is the most useful thing in
this report.** I predicted the gap of means would come out *below* E02's single-pair 0.0606,
reasoning that a single pair "carries two noise terms" that averaging six per side would
shrink. It came out **0.1288 — roughly double**. The reason is that **the two conditions are
not independent at a shared seed** (section 5): E02's A1a and A1b ran on the *same* seed, so
their difference was never a two-noise-term quantity. It was a paired difference — the
*low-noise* comparison — and 0.0606 happens to be the **smallest of the six** paired
differences this experiment measured.

---

## 2. Gate 0 — the sheets exist, and they came first

**12 of 12 built before any number in this document was computed.**
`outputs/E04/sheets/E04-{C-bright,C-dark}-s{1..6}.png`, each a control | output | reference |
provenance panel at native 480×832.

Seed 1 of each condition is sheeted from E02's own run — C-bright from `A0r1/lossless`, C-dark
from `A1b/lossless` — pointed at where those live rather than copied, so each sheet's
provenance names the real directory.

⚠ **The provenance panels read `prompt_id NOT RECORDED` and `Gate B NOT YET RUN`.** That is
correct rather than a defect: the panel is rendered from the payload's build-time meta, written
*before* submission, when neither was known. The prompt ids are in
`outputs/E04/provenance.json` and Gate B's verdicts are in section 4.

**The low outlier was inspected, not just tabulated.** C-bright-s4 returns 0.2296, far below its
siblings. Its sheet shows an ordinary, well-formed generation — the figure is present, in the
control's position, turning with it. It is a real draw, not a broken run, and it is not excluded.

---

## 3. The measurement

### Per-seed timing correlation — grayscale, 33 frames → 32 deltas

| seed | | C-bright | C-dark | dark − bright |
|---|---|---|---|---|
| 654654950714624 | s1 *(E02)* | 0.5207 | 0.5813 | +0.0606 |
| 654654950714625 | s2 | 0.6933 | 0.8149 | +0.1216 |
| 654654950715624 | s3 | 0.5756 | 0.7585 | +0.1830 |
| 654654950724624 | s4 | **0.2296** | 0.3977 | +0.1681 |
| 654654950814624 | s5 | 0.5356 | 0.7814 | +0.2458 |
| 654654951714624 | s6 | 0.6853 | 0.6790 | **−0.0063** |

| | C-bright | C-dark |
|---|---|---|
| mean | 0.5400 | 0.6688 |
| **SD (the spread)** | **0.1689** | **0.1571** |
| range (max − min) | 0.4637 | 0.4172 |
| min · max | 0.2296 · 0.6933 | 0.3977 · 0.8149 |

### The spread beside the gap — arithmetic, with no verdict attached

| quantity | value |
|---|---|
| within-condition SD, mean of the two | **0.1630** |
| between-condition gap (difference of means) | **0.1288** |
| E02's single-pair gap, which it declined to read | 0.0606 |
| **the gap in units of the spread** | **0.79 SD** |
| **E02's 0.0606 in units of the spread** | **0.37 SD** |
| SD ratio, C-dark / C-bright | 0.93 |
| ranges | C-bright [0.2296, 0.6933] · C-dark [0.3977, 0.8149] — **they overlap** |

**The fixed-seed floor on this same statistic is exactly zero** (E02's A0r1/r2/r3 all return
+0.5206918475). The between-seed spread is 0.163. Those are the two floors, and they are not
the same object.

### The pixel statistic — `measure_floor`'s unit, 15 within-condition pairs each

| | pairs | mean \|Δ\| | SD | min | max | bit-identical |
|---|---|---|---|---|---|---|
| C-bright | 15 | 34.31 | 5.98 | 25.32 | 43.11 | **0 / 15** |
| C-dark | 15 | 40.06 | 14.00 | 21.20 | 63.07 | **0 / 15** |
| *A0, fixed seed* | *3* | ***0.00*** | — | — | — | ***3 / 3*** |

**This row carries no ratio, deliberately.** Its fixed-seed floor is 0 and its between-seed
value is not, so "between-seed over fixed-seed" is a division by zero — undefined, not large.
The row is informative categorically: **the two floors are different kinds of quantity.** If a
later document quotes a pixel ratio from this experiment, it has misread it.

---

## 4. Every gate, with a verdict

| gate | verdict | evidence |
|---|---|---|
| **Gate S** — seed pre-registration | **PASS, 10 of 10** | every submitted seed on the committed list; raises inside `build()` before any disk read; survives `-O` and `PYTHONOPTIMIZE=1`; a CLI submission of an unregistered seed was driven to failure and wrote no file |
| **Gate L** — frame legality | **PASS, 10 of 10** | 480×832×33, `wan-vace` profile |
| **Gate B** — control batch intact | **PASS, 10 of 10** | 33 of 33 images at the batch node, every run |
| **Gate 0** — the sheet | **PASS, 12 of 12** | built before any number was computed |
| **Gate C** — credits | **PASS** | 10 spent against a ceiling of 12; 2 unspent |
| **Gate R** — round trip | **N/A** | no encoder in this route |
| **the lossless tap** | **PASS, 10 of 10** | node 302 wired to `VAEDecode`, enforced by `verify_topology`; 33 lossless frames returned per run |
| **the anchor leg** | **PASS, 5 of 5** | E02's published figures reproduce within 0.0005 |

**No gate fired. Nothing was re-run to get past one.**

The bridge reproduced E02's measured `max(src−1, 0)` offset exactly — per-frame max \|Δ\|
between batch probe and local control is 1 on every frame of all 10 runs, min and max alike.

### Credits

| | |
|---|---|
| new generations | **10** (5 seeds × 2 conditions) |
| reused at no cost | 2 — E02's A0r1 and A1b, hash-verified before use |
| **spent** | **40 credits** (4 per generation, E02's measured rate) |
| ceiling | 12 generations / 48 credits — **2 unspent** |
| submission | 1 probe (`f2ff1e57`) verified end-to-end before the remaining 9 went as one batch |

The probe was not in the plan and cost nothing extra: it converted a possible 40-credit loss
into a possible 4-credit one before committing the rest.

---

## 5. ⚠ POST-HOC and NOT PRE-REGISTERED — the seed is shared, so these are pairs

**This section was not planned and is flagged as loudly as I can make it.** The pre-registered
analysis is section 3; this is arithmetic I ran *after* seeing that result, and an analysis
chosen because the data suggested it is a different epistemic object from one chosen in advance.
**It rules nothing.**

The design gives both conditions the *same six seeds*. So the twelve values are **six pairs**,
not two independent samples of six:

| quantity | value |
|---|---|
| per-seed differences (dark − bright) | +0.0606, +0.1216, +0.1830, +0.1681, +0.2458, **−0.0063** |
| mean difference | 0.1288 |
| **SD of the differences** | **0.0907** |
| SD expected if the conditions were independent | 0.2306 |
| **cross-condition correlation across seeds** | **r = 0.848** |
| seeds where dark > bright | **5 of 6** |

**The two conditions move together across seeds.** A seed that tracks poorly under C-bright
tracks poorly under C-dark (s4 is lowest in both); a seed that tracks well tracks well in both.
The difference between them varies **2.5× less** than two independent draws would.

**Why this matters beyond E04, and why it is not a conclusion:** it means the unpaired reading
in section 3 (gap = 0.79 SD, ranges overlap) and the paired arithmetic here (a difference that
is consistent in 5 of 6 seeds, with a third the noise) are **two honest readings of the same
twelve numbers**. Which one governs a future arm comparison depends on whether that comparison
shares its seeds — and that is a design decision, and the Director's and the advisor's, not a
measurement.

**What it does NOT establish:** that C-dark tracks better than C-bright. One seed reverses, the
analysis is post-hoc, n is 6, and E02's Ruling 2 constraint is not discharged by an analysis
invented after the fact.

---

## 6. What this experiment produced

1. **The floor exists and has a number: 0.163** — the within-condition SD of the timing
   correlation across 6 seeds, at 33 frames, on this route. Measured twice independently
   (0.169 and 0.157) and the two agree.
2. **A single floor number is portable across these two conditions.** P2's finding: the SD
   ratio is 0.93. The spec named condition-dependence as a finding in its own right; it is not
   present here.
3. **E02's 0.060 gap sits at 0.37 of that spread.** The closing ruling declined to read it as
   an ordering. That refusal now has a number under it instead of a caution.
4. **The fixed-seed floor and the between-seed floor differ by everything.** Zero against 0.163
   on the timing correlation; zero against a mean \|Δ\| in the thirties on pixels. Quoting one
   where the other belongs is the specific error this experiment was bought to prevent.
5. **The statistic is now a tool** with an anchor leg that reproduces all five of E02's
   published figures, and E02's `+0.521` is attributed to the frames it was actually computed
   from.

## 7. Scope — what these numbers do not cover

- **At 33 frames.** Every number here carries that. Wan 2.1 VACE's trained horizon is around
  the 81-frame class; temporal coherence can drift with clip length, and the floor at 81 is
  unmeasured.
- **This statistic only.** Every statistic quoted in this repo needs its own floor. This
  measures the two E02 quoted and no others.
- **These two conditions only.** The no-control (A2) arm's own floor is still unmeasured and is
  not assumed to be the same.
- **n = 6 per condition.** An SD from 6 values is itself uncertain; P2b registered in advance
  that this design cannot separate two spreads that differ by less than about 3×.
- **Nothing here is about identity.** No metric in this document bears on whether the figure is
  the same character. That is canon and the Director's eye.

## 8. This seat's error record

- **P1a / P1c:** underestimated the spread ~2× by letting an n=1 estimate I had explicitly
  called worthless pull my number away from the theory that was right.
- **P4b:** predicted the gap would shrink under averaging; it doubled, because I had the
  independence structure backwards. Corrected in section 5 with the measurement that overturned
  it.
- **Premise 1 in the spec named the wrong file** (`A1a.json` for C-bright's base). Caught before
  any spend; corrected in Amendment 1. C-bright ran on `A0.json`, which is the same condition
  plus the lossless tap.
- **An early check of mine was the wrong check:** I tested whether the uploaded server names
  were sha256 of the local PNG bytes. They are not — 0 of 33 matched even for the arm whose
  source directory is certain. The server's content-addressing is not that function, and no
  conclusion was drawn from the failed check.
- **One fixture pair in the commission was wrong, not the tool** — a profile against its own
  reverse is not anti-correlation (+0.61), and integer halving is not exact scaling. Both are
  corrected in place with the reason.

## 9. What the Director is asked to look at

1. **`outputs/E04/sheets/E04-C-bright-s{1..6}.png` and `E04-C-dark-s{1..6}.png`** — twelve
   panels, control | output | reference | provenance, at full size rather than as a contact
   sheet.
2. **`E04-C-bright-s4.png` specifically** — the lowest value in the experiment (0.2296) on a
   sheet that looks like every other one. Whether that generation is worse *to the eye* is the
   question no number here answers, and it bears directly on what the statistic is measuring.
3. **The two readings in sections 3 and 5**, and which one should govern the design of the next
   arm comparison.
