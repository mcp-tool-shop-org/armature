# E10 — predictions, registered before the measurement and before the submission

**Seat: executor**, branch `E10-density`, worktree `E:\AI\armature-E10`. Written before the
smoothness diagnostic was computed and before any E10 graph was submitted. The commit that
carries this file is the timestamp.

## What this seat had already seen when writing these numbers — disclosed, because it
## bounds how blind "blind" is

Blind to: **every second-difference number**, in either unit, for either sequence. No
smoothness measurement of any kind had been run on either the E08 sticks or the E10 sticks.
Blind to every painted E10 output — nothing has been submitted.

**Not** blind to, and therefore disclosed:

- the resampler's own per-bone **first**-difference diagnostic in rotation space (geodesic
  degrees between consecutive frames): median `hips` 3.719 → 2.919, `chest` 2.038 → 1.631,
  `head` 3.089 → 2.377, `shoulder.L` 28.478 → 21.197. These are step angles, not second
  differences, and they are in degrees of rotation, not pixels.
- that 17 of the 81 destination samples land exactly on a source sample, and that at every
  one of those the projected pixels reproduce E08's **exactly** (max |Δpx| = 0).
- the projected body span: E10 min 246.67 / median 254.80 / max 302.89 px against E08's
  246.67 / 254.80 / 307.20. The max is lower because the source frame carrying the widest
  pose is not one of the 17 the new sampling lands on.
- the E08 report's own outcomes, including that this seat's E08 predecessor under-predicted
  every identity and scene clause.

## The arithmetic these predictions are reasoned from — stated so a wrong prediction can be
## traced to a wrong model rather than to a wrong guess

Densification resamples the **same path**: slerp between adjacent source keys traces the
identical piecewise-geodesic curve the E08 record describes, and only the sample positions
move. Two consequences that pull in opposite directions and are predicted separately:

- Per-frame velocity scales by the interval ratio **0.8** (= 64/80), so a turn at a source
  key contributes a second difference 0.8× the size it did.
- The number of second-difference terms rises from 63 to 79, while the source's 63 interior
  keys still each carry their full turn — 63 of the 80 destination steps still cross one.

So the **mean** per-frame second difference should fall by roughly 0.8 × 63/79 ≈ **0.64**,
which is also what a smooth path would give ((Δt)² = 0.64). The **max** is one knot's turn
and should fall by roughly **0.8**. In per-second units the two effects cancel: the path's
acceleration in wall-clock time is a property of the performance, not of the sampling.

## H-E10a — the driving signal (per-keypoint second difference, 20 body keypoints, 81 vs 65)

| clause | prediction | degree |
|---|---|---|
| the per-frame (px/frame²) **median** over all keypoints drops | ratio to E08 in **[0.60, 0.85]** | **60 %** |
| the per-frame **mean** drops | ratio in **[0.55, 0.75]**, centred on 0.64 | **65 %** |
| the per-frame **max** drops | ratio in **[0.70, 0.95]** | **55 %** |
| every one of the 20 body keypoints drops on the per-frame median (none rises) | all 20 | **70 %** |
| the per-**second** (px/s²) median is approximately unchanged | ratio in **[0.85, 1.15]** | **60 %** |

The last row is the one this seat expects to be most informative: if it holds, the honest
statement is that densification did not smooth the performance, it **re-sampled the same
performance in smaller steps** — which is a claim about what the model is shown, not about
the motion.

## H-E10b — the painted result

| clause | prediction | degree |
|---|---|---|
| the Director reads the E10 clip as visibly smoother than E08's at true tempo | yes | **45 %** |
| some visible difference in motion texture, direction unspecified | yes | **70 %** |

45 %, not higher, because the driving delta falls by about a third while the chop may be
generation-side as much as driving-side, and nothing in E08 separated those. No threshold is
invented; his eye rules and this row exists only to be scored against.

## H-E10c — tempo

| clause | prediction | degree |
|---|---|---|
| 81 frames at 20.0 fps and 65 at 16 fps agree in duration to within one frame | yes (0.0125 s ≈ 0.25 E10-frames) | **90 %** |
| the run returns exactly 81 lossless frames | yes | **90 %** |

The first is arithmetic rather than empiricism; the 10 % is the chance the deliverable is
built at the other convention (81/19.94) or that the encode stage rounds the rate.

## H-E10d — the named risk, which is a full result if it lands

| clause | prediction | degree |
|---|---|---|
| the stick-level per-frame drop is small enough to call the lever weak (median ratio > 0.90) | no | **20 %** |
| the painted chop is unchanged even though the sticks measurably smoothed | possible | **35 %** |

## The rest of the shot, predicted clause by clause

E08's seat recorded that it under-predicted every identity and scene clause; these are
corrected upward for that, and the correction is stated so the adjustment is visible.

| clause | prediction | degree |
|---|---|---|
| Gate B: all 81 driving frames arrive server-side pixel-identical | yes | **85 %** |
| the bar arrives again — shelving, bottles, warm light | yes | **85 %** |
| no other people, the unchanged negative still excluding them | none | **80 %** |
| the face reads as the twin's at ≥ 3 of 5 sampled frames | yes | **65 %** |
| no frame resolves fingers | none | **90 %** |
| the vertical banding is still present | yes | **70 %** |
| the painted body tracks the sticks at every sampled frame | yes | **85 %** |

## Fail conditions, named now

- Any gate fires → halt and report, no re-parameterisation.
- The returned frame count is not 81 → the pack bridge or the conditioning node's padding
  is implicated; report, do not re-run.
- The painted figure does not follow the sticks → the densified driving signal is not being
  read; that is a result, and it ends the lever rather than tuning it.
