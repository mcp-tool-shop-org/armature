# E10 — report: the same dance, 81 samples over the same four seconds

**Seat: executor**, branch `E10-density`, worktree `E:\AI\armature-E10`, from `main` at
`e80f813`. **One generation** (`prompt_id` `263bc224-cf3c-47ff-867e-6814dfda59e7`, seed
`2026081221`). Reserve seed `2026081222` **unspent**. No gate fired on the experiment; four
defects fired inside this session's own tools and are recorded below with their fixes.

This report carries measurements, gate states and predictions against outcomes. It contains
no judgement of whether the footage is good; the Director's eye is the verifier of record and
the advisor rules on what the measurements mean.

**Look first:** the true-tempo A/B — `outputs/E10/review/E10-vs-E08-truetempo.webp` (E08's
65-frame probe at 16 fps beside E10's 81-frame probe at 20 fps, neither arm resampled or
retimed). Then `outputs/E10/sheets/E10-gate0.png` at full size, then the 0.50×/10 fps clip
from `lossless/`, then the zoom sheets.

**The headline this seat can state without judging it:** the driving signal did what the
lever intended — per-frame second differences fell to 0.585 of E08's at the median, with
every one of the 20 keypoints falling and none rising — and the painted output changed in a
way the experiment did not aim at: its **frame-to-frame luminance swing is about ten times
E08's** (median |Δ mean-luma| 9.05 against 0.84), and **other people appear in the bar**,
which they did not in E08. Nothing in this run separates the two registered changes (a new
frame count and a new seed) as the cause of either.

---

## 1. Premises, re-verified at use

| # | premise | spec status | what re-verification found |
|---|---|---|---|
| 1 | The E08 probe's exact inputs, by hash from its payload record | MEASURED | **CONFIRMED, every one.** payload record `c5a68fa65e9ea079…`, graph as built `3d00fffeabef1c64…`, gate evidence `06a469db37ac9fcc…`, negative source `3ae102e029d4d0e3…`, pose pack `2c83271a1a8bd2e9…`, projected keypoints `62b27eebfe52f0ef…`, convention `962813c71b2f2e09…`, reference as uploaded `34fd9177f590fc31…`, motion record `907faebc5ccf8b91…`, rig manifest `f9de52d6871c566e…`, rigged GLB `7f56c9ac101218db…`. All match the values E08 and E09 recorded. |
| 2 | 81 @ 832×480 is generator-legal on this route | MEASURED | Confirmed and re-checked in code: 4n+1 ✓, ≤ 81 ✓, both dimensions /16 ✓. Gate L ran with supplied frame values **and** against the node's own literal, and the two were required to agree (§5). |
| 3 | fps is carried at encode/presentation, not inside the generation | **ASSUMED — verify** | **CONFIRMED, from the node schema rather than from memory.** `CreateVideo` takes `fps` as a **FLOAT** (min 1, max 120) and sits downstream of `VAEDecode`, after every sampling step. `WanAnimateToVideo` and `KSampler` carry no fps input at all. The rate therefore cannot change a generated pixel, and the lossless `SaveImage` tap every measurement reads bypasses it entirely. |
| 4 | The motion record's rotation representation supports slerp directly | **ASSUMED — verify** | **FALSE AS STATED.** Rotations are stored as **3×3 matrices**, not quaternions, so slerp is not directly applicable and the conversion is the commission's first job. Measured on all 1430 matrices of the E09 A3 record: orthonormal to **2.55e-15**, determinant within **2.0e-15** of 1 — because `lift_clip.ema_rotations` SVD-orthonormalises after every smoothing step. That measurement is what makes matrix→quaternion well-conditioned here, so it is recorded rather than assumed. |
| 5 | Billing: 0 credits, GPU-hours metered | MEASURED | Confirmed. `estimate_credits` re-run before submission: **0 credits, no paid API nodes**. §11. |

---

## 2. The tempo, derived exactly — and a number in the spec that came from the other convention

The spec's commission says **endpoints exact** over **the identical duration**. Those two
clauses together fix the mapping: destination sample `j` reads source position
`j × 64/80 = 0.8j`, so both endpoints land on source samples and the sample interval scales
by 0.8. The playback rate that leaves the first-to-last span unchanged is therefore

  16 × 80/64 = **20.0 fps exactly**, and the span is 64/16 = 80/20 = **4.000 s**.

The spec's parenthetical says "~19.95 fps sampling". That number comes from the other
convention — clip length as *frames ÷ fps*: 81 ÷ (65/16) = **19.9385 fps**. Under that
reading the endpoints would not be exact in time (the first-to-last span becomes 4.0125 s,
a 0.31 % stretch), so it is incompatible with the commission's own "endpoints exact" clause.
**The deliverables use 20.0.** Both conventions are written into the resampler's provenance
so no reader has to guess which one a tempo claim used.

| quantity | E08 | E10 |
|---|---|---|
| samples | 65 | 81 |
| rate | 16 fps | 20.0 fps |
| first-to-last span | 4.0000 s | 4.0000 s |
| clip length (frames ÷ fps) | 4.0625 s | 4.0500 s |

The two clip lengths differ by **12.5 ms = 0.25 of an E10 frame**.

---

## 3. The commission — `tools/resample_motion.py` and its module

`armature_core/resample.py`: shortest-arc slerp per bone between adjacent keys, linear on
the root translation, endpoints returned **verbatim** rather than round-tripped. Three
failure modes have fixtures that build the wrong implementation and show it failing:

- **element-wise matrix averaging** — determinant 0.5, shears the body on every in-between
  frame while every count stays right;
- **the q/−q double cover** — a 20° turn becomes a 340° spin with nothing erroring;
- **a half-frame phase slip** — the clip plays, starting late, with every count right.

`require_rotation` **raises rather than repairing**: orthonormalising would erase the
evidence that a record arrived broken, and the repair would be indistinguishable in the
output from a record that was fine.

**31 tests, all analytic** — the 45° midpoint of a 90° arc, constant angular rate across the
arc, conserved total travel, and a 65→81 record the solver's own validator accepts.

Measured on the real record (per-bone geodesic step, degrees, median):

| bone | 65-frame | 81-frame | ratio |
|---|---|---|---|
| `hips` | 3.719 | 2.919 | 0.785 |
| `chest` | 2.038 | 1.631 | 0.800 |
| `head` | 3.089 | 2.377 | 0.769 |
| `shoulder.L` | 28.478 | 21.197 | 0.744 |

**17 of the 81 destination samples land on a source sample** (`u = 0, 4, 8 … 64`), and at
every one of those the projected pixels reproduce E08's **exactly — max |Δpx| = 0.000e+00**,
body and both hands. The other 48 source samples are on the path but are not sample points
of the new sequence; that is what resampling at a non-integer ratio does, and it is why the
projected body span's **max** fell from 307.20 px to 302.89 px while the min and median are
unchanged (246.67 / 254.80 in both).

---

## 4. The instrument work E08's closing ruling commissioned

**Gate L no longer calls an empty examination a pass.** E08 added `WanAnimateToVideo` to
`LATENT_NODES`, which fixed that graph and not the shape of the failure — the next
unrecorded latent-sizing node disarms the gate identically, and a table can only ever be
complete about nodes somebody already met. So `verify()` now distinguishes **"nothing was
checkable"** from **"everything checked out"**: with no checkable latent and no supplied
frame the frame-legality clause is **INDETERMINATE — unproven — and raises**. A caller that
knows its own shape passes `frame=(w, h, length)`; that is not a skip flag, because the
supplied numbers are checked against the generator's rules like any others, are labelled
`supplied` in the evidence, and must **agree** with any frame the graph itself pins or the
gate raises on the contradiction. A latent whose dimensions arrive over links now reads as
unchecked rather than as checked.

**The red test is `test_a_graph_with_no_checkable_latent_and_no_supplied_frame_goes_RED`**,
and a companion reconstructs the historical case by removing `WanAnimateToVideo` from the
table again — the fix has to hold without it. Ten route-gate tests in total.

---

## 5. Gates

| gate | where | state |
|---|---|---|
| **MAP / FRONT / MOTION** | projector (shot, 832×480) | PASS — 81 distinct projected poses |
| **FRAMING** | projector | SKIPPED-and-recorded — camera **pinned** to E08's `keypoints.json`, not solved. Its loader refuses a record that disagrees about any angle *and* one that is silent about one; radius and target came back byte-identical to E08's (4.116721, [-0.176417, 0.146821, 0.060699]) |
| **CONV / CANVAS / INK / COUNT** | sticks renderer | PASS — 20 keypoints / 19 pairs, every body keypoint in canvas, min ink 0.00493 at f72, 81 files |
| **overlay (pre-spend, standing)** | sticks over the **densified** previz, pinned camera | PASS — §6 |
| **R** | pose pack | PASS — identical, 81 frames, 212,129 bytes |
| **L** | payload builder + ROUTE | PASS — 832×480×81, verdict **PROVEN**, checked twice (the node's literal and the caller's supplied values, required to agree) |
| **S** | payload builder + ROUTE | PASS — seed `2026081221`, drawn from `specs/E10-seeds.json`, committed at `7cb55ad` before the first submission |
| **ROUTE** | built API graph **and** saved projection | PASS — 3 weight files, 1 seed pinned, 1 of 1 latent checkable, 2 frames checked |
| **saved round trip** | `gate_saved_graph` | PASS — **30 pinned values** and **20 links** compared; 6 optional sockets empty in both |
| **B (count)** | the run | PASS — 81 in, 81 back |
| **B (pixels)** | the run | PASS — **all 81 frames pixel-identical**, per channel |
| **ceiling** | generation count | 1 of 2 spent |
| watchdog | before every local render | verified alive at session start and before the Blender work |

**The one-variable statement, checked mechanically rather than by reading the diff.** The
E08 API graph as submitted and the E10 API graph differ in exactly **seven values**:

```
3.KSampler.seed            2026081211 -> 2026081221
49.WanAnimateToVideo.length        65 -> 81
68.CreateVideo.fps                 16 -> 20.0
200.LoadImage.image        a863dff3….png -> c8f4d8df….png   (the 81-frame pack)
114 / 301 / 302 filename_prefix     E08 -> E10               (server-side foldering)
```

Prompt, negative, sampler, models, resolution, the reference upload and the five empty
sockets are byte-identical. The reference was re-uploaded from E08's own file and the
endpoint returned **the same server name** (`54a38251…`), which is content-derived — so the
bytes reaching the model are E08's bytes as evidence rather than as an assertion.

---

## 6. The overlay pre-spend gate, and what it says about the toes

The 81 sticks were composited onto a **densified previz** — the resampled motion keyed onto
the rig (`lift_solve`, Gate ARRIVED max 7.281e-06 over 81 frames) and rendered at 1920×1080
through a camera the projection was then pinned to. At frames 0, 20, 40, 60, 80 and at the
interpolated frames 1, 2, 3, 41, 42 the sticks sit on the body: head markers on the skull,
shoulders/elbows/wrists along the arms with the mitten fans on the hands, hips/knees/ankles
down the legs.

**The toe markers (18, 19) sit just outside the rendered feet.** They sit there in **E08's
own shipped overlay too**, at the same offset and in the same direction — compare
`outputs/E10/sheets/E10-overlay-feet.png` with `E:\AI\armature-E08b\outputs\E08\sheets\
E08-overlay-feet.png`. The measured quantity agrees: ankle→toe distance over the whole clip
is min 12.86 / median 23.27 / max 28.38 px in E08 and 12.91 / 23.30 / 28.35 px in E10, and
the foot/leg ratio is 0.087–0.139 (median 0.113) against the rig manifest's measured
0.087–0.139. This is the inherited placement of the shipped projector, not something E10
introduced; recorded here because the next seat will see it and should not re-derive it.

---

## 7. H-E10a — the driving signal, measured

`tools/measure_smoothness.py`, pooled over all 20 body keypoints, both records projected
through the identical camera at 832×480.

| statistic | E08 (65) | E10 (81) | **ratio** |
|---|---|---|---|
| second difference, px/frame² — median | 2.098 | 1.227 | **0.585** |
| — mean | 5.714 | 3.489 | **0.611** |
| — p90 | 15.901 | 9.923 | **0.624** |
| — max | 81.964 | 56.815 | **0.693** |
| second difference, px/s² — median (**control**) | 537.0 | 490.8 | **0.914** |
| — mean | 1462.8 | 1395.8 | 0.954 |
| — p90 | 4070.6 | 3969.1 | 0.975 |
| — max | 20982.8 | 22726.1 | **1.083** |
| first difference (velocity), px/frame — median | — | — | **0.793** |

**Every one of the 20 keypoints fell on the per-frame median; none rose.** The spread runs
from `REye` 0.421 to `LAnkle` 0.651.

Two readings, kept apart deliberately:

- The **per-frame** column is what the model experiences between consecutive driving frames,
  and it fell by 41 % at the median. The velocity ratio, 0.793, is the interval ratio 0.8 to
  within measurement — which is the mechanism, not a coincidence.
- The **per-second** column is what the performance does in wall clock, and it is a
  **control**: a do-nothing arm and a perfect arm read the same there. It moved by 8.6 % at
  the median. So the dominant effect is that the same path is being shown in smaller steps,
  not that the performance was smoothed.

The 8.6 % is not fully explained by this seat's own model and is **not** claimed as
smoothing. A candidate mechanism, offered as a candidate: a destination step that straddles
one of the source path's turns carries a blended velocity, so a single knot's turn is spread
across two second-difference terms and each is smaller than the whole. The `max` column
moving the other way (1.083) sits awkwardly with that story. Nothing here tests it.

---

## 8. What came back

163 outputs: 1 video, 81 Gate-B batch frames, 81 lossless frames. **81 of 81 output frames
are distinct.** Mean absolute frame-to-frame delta: **min 4.91 · median 15.95 · max 69.85**
(0–255), against E08's 2.55 / 3.95 / 6.16 — E10's *quietest* frame transition is larger than
E08's *largest*. (Read the units before reading the ratio: this is a whole-image mean over
all three channels, so it moves with exposure and background as much as with the figure, and
§8's luminance table is the same phenomenon measured directly.)

Read off the sheets, at full size, in the order the spec asks. **No judgement of quality is
offered or implied.**

- **Motion adherence.** With the driving sticks composited onto the painted output at the
  four fastest-motion frames (15, 31, 49, 64 — located by wrist speed, not by eye), the head
  markers land on the head, shoulder/elbow/wrist markers along the painted arms, and
  hip/knee/ankle markers down the painted legs, at every one of the four.
  `outputs/E10/sheets/E10-painted-over-control.png`.
- **The figure.** A bald terracotta jointed mannequin with visible ball joints at the knees
  and hips, a dark band at the pelvis, and elbows that mostly do not show the joint. At the
  six fastest frames the head reads as bald with ears, brows, closed lidded eyes and a small
  closed mouth in **all six** (`E10-zoom-Nose.png`, 3× nearest).
- **Hands.** No frame resolves fingers. At the sampled frames the hands are rounded paddles
  or motion-blurred lumps (`E10-zoom-LWrist.png` / `-RWrist.png`).
- **The scene.** A long wooden bar counter with bottles and glasses along the top, warm
  strip lighting beneath it, a pale panelled wall at the left with a floor lamp on a round
  white base, and a pale wooden floor. Present in every frame inspected.
- **Other people — present.** A seated human figure (long dark hair, sleeveless top,
  patterned trousers, sandals) is visible at the left edge of the frame, and in some frames
  a hand and forearm near the counter. **Inspected at full size at frames 0, 24, 40, 56, 60,
  80 and across two 12-frame consecutive strips (20–31, 60–71) plus a 21-frame contact
  sheet.** The figure is present in every frame checked at full size; a first read off the
  small contact sheet recorded it as absent at f24/f40/f56 and that read was **wrong** —
  sheets locate, full size decides, and this is that law firing on this seat.
- **Exposure and tone swing frame to frame.** Measured as mean image luminance per frame:

| | E08 | E10 |
|---|---|---|
| mean luminance over the clip | 107.1 | 132.7 |
| luminance range across the clip | 51.9 | 113.8 |
| **frame-to-frame \|Δ luma\| — median** | **0.84** | **9.05** |
| — p90 | 1.55 | 31.67 |
| — max | 2.69 (f4→5) | 67.31 (f28→29) |

  By segment, E10's median |Δ luma| is 5.93 (f0–20), **17.48** (f20–40), 10.99 (f40–60),
  4.90 (f60–80). E08's quietest segment is 0.09 and its noisiest 1.35 — so **E10's quietest
  segment is 3.6× E08's noisiest.** Visible in the consecutive strips as the figure and the
  room alternating between pale-and-bright and dark-and-warm from one frame to the next.

**This seat did not measure a cause for either the luminance swing or the appearance of
people, and cannot separate one from the other.** The registered changes are the frame count
(65→81, the trained horizon's ceiling) and the seed; the prompt and negative are byte-
identical, and `CreateVideo`'s fps is downstream of the decode and cannot reach a lossless
frame. A discriminating design exists — the reserve seed at the **same** 81 frames, which
separates seed from frame count — and it would spend the reserve. That is the advisor's call
against the remaining ceiling, not this seat's.

---

## 9. Defects found inside this session's own tools

Four, all found by running the tools rather than by reading them, all fixed with tests in
the commit that touched the code:

1. **`route_gates.gate_s_registration` crashed on a wired save-format sampler.** Save format
   spells `inputs` as a **list** of slot dicts, API format as a mapping, and the noise check
   called `.get` on it. E09's saved samplers had *empty* input arrays, so `or {}` swallowed
   the difference and the crash waited for a graph whose sampler was actually wired — which
   every real one is. The same line also asked a plain `KSampler` whether its first widget
   read "disable"; `KSampler` has no `add_noise` input at all, so the answer was right for
   the wrong reason. Both fixed per-class.
2. **`make_e08_sheet` hardcoded E08's provenance.** `prompt_id`, frame count, fps and the
   gate line were string literals, so the first E10 sheet quoted E10's seed beside **E08's
   prompt_id and "832x480x65 @ 16 fps"** — a report carrying a placeholder shaped like
   evidence. Every value now comes from the run's own payload record and `--prompt-id` has
   no default.
3. **`make_review_clip` named its output `review_0.5x_8fps.webp` whatever the flags said.**
   True only while every source ran at 16 fps; against E10's 20 fps source the same file is
   0.40×. The name is now built from the actual rates.
4. **`gate_b_frames` counted a contact strip as a frame.** `render_pose_sticks` writes
   `strip_every8.png` beside its `NNNNN.png` frames, so the first run reported 82 driving
   frames and the count andon fired with a message about batching.

A fifth was caught by a test before it ever ran: `make_ab_clip` used `round` where `floor`
was meant, which snapped a side to the nearest frame boundary rather than the frame already
on screen — one arm would have run a fraction of a frame ahead of its own tempo for the
whole clip.

---

## 10. Deliverables

| artifact | what it is |
|---|---|
| `outputs/E10/review/E10-vs-E08-truetempo.webp` | **the A/B the Director judges** — E08 at 16 fps beside E10 at 20 fps, lossless, 129 composite frames, 4.062 s. Built on the union of both arms' frame times with each side holding its own frame between its own events: **neither arm is resampled or retimed** |
| `…-truetempo-q95.webp` | the same at quality 95, 9.8 MB against 63 MB — a convenience copy, not a measurement source |
| `outputs/E10/review/half-speed/review_0.50x_10fps.webp` | the 0.5× review clip from `lossless/`, lossless |
| `outputs/E10/review/eight-fps/review_0.40x_8fps.webp` | 8 fps from the same source. **The spec's "0.5× / 8 fps" is one clip at 16 fps and two different clips at 20 fps**, so both are delivered and each is named for what it is |
| `outputs/E10/sheets/E10-gate0.png` | previz \| control \| painted \| reference \| provenance, at f0/20/40/60/80 |
| `outputs/E10/sheets/E10-painted-over-control.png` | the driving sticks on the painted output at the four fastest frames |
| `outputs/E10/sheets/E10-zoom-{Nose,LWrist,RWrist}.png` | 1:1 crops at 3× nearest, centred on the driving keypoints, at the six fastest frames; crop boxes in the sidecars |
| `outputs/E10/sheets/E10-overlay*.png` | the pre-spend overlay gate, including the feet detail |
| `outputs/E10/sheets/E10-consec-{20-31,60-71}.png` | consecutive painted frames, where the luminance swing is visible |

Stills were located at the frames of **fastest wrist motion** (15, 16, 31, 32, 49, 64;
104.1 → 81.1 px/frame summed over both wrists, against a median of 49.7) rather than at
evenly spaced indices — structure is hardest where motion is fastest.

---

## 11. Both meters

**`estimate_credits` = 0 credits — no paid API nodes**, re-confirmed before submission on
the exact graph submitted. On an all-OSS route this is 0 by construction, so the ceiling was
enforced by **counting generations**: 1 of 2 spent, reserve `2026081222` unspent.

**GPU hours.** Baseline recorded before submission: **$17.430281** for
2026-07-12T09:00Z → 2026-08-12T09:00Z, of which the 08:00–09:00Z bucket is **$0.263814**.
E08's report recorded **$17.166467** for its window before its own probe landed; the
difference between the two totals is $0.263814, exactly the new bucket. **On that reading
E08's probe cost ≈ $0.26 in GPU hours** — which closes E08's open ledger item, with the
caveat that the two windows do not start at the same hour and nothing else confirms the
attribution. E10's own bucket had not been invoiced when this report was written; it is
`NOT YET RESOLVED`, and the delta against $17.430281 is the number to read.

---

## 12. Predictions versus outcomes

Registered blind at `7cb55ad`, before the smoothness diagnostic was computed and before the
submission. Each clause read separately. Blindness disclosed in the predictions file itself.

| clause | predicted | outcome |
|---|---|---|
| **H-E10a** per-frame **median** ratio in [0.60, 0.85] — 60 % | in range | **MISS, narrowly and in the direction of more improvement.** 0.585, just below the interval. |
| **H-E10a** per-frame **mean** ratio in [0.55, 0.75], centred 0.64 — 65 % | in range | **HIT.** 0.611. |
| **H-E10a** per-frame **max** ratio in [0.70, 0.95] — 55 % | in range | **MISS, narrowly, same direction.** 0.693. |
| **H-E10a** all 20 keypoints fall, none rises — 70 % | all 20 | **HIT.** None rose. |
| **H-E10a** per-**second** median ratio in [0.85, 1.15] — 60 % | in range | **HIT.** 0.914. |
| **H-E10b** the Director reads it as visibly smoother at true tempo — 45 % | maybe | **NOT THIS SEAT'S TO SCORE.** The A/B is built; his eye rules. |
| **H-E10b** some visible difference in motion texture — 70 % | yes | **HELD, but not for the reason predicted.** The measured difference in the painted output is a ~10× larger frame-to-frame luminance swing, which is not what the lever aimed at. |
| **H-E10c** durations agree within one frame — 90 % | yes | **HIT.** 4.0625 s vs 4.0500 s = 0.25 of an E10 frame. |
| **H-E10c** exactly 81 lossless frames — 90 % | yes | **HIT.** 81, all distinct. |
| **H-E10d** the lever reads weak at stick level (median ratio > 0.90) — 20 % | no | **HIT on the prediction.** 0.585 is not a weak move at the stick level. |
| **H-E10d** painted chop unchanged though the sticks smoothed — 35 % | possible | **UNRESOLVED at this seat.** The Director's eye decides; this seat measured that something else changed a great deal. |
| Gate B identical on all 81 — 85 % | yes | **HIT.** |
| the bar arrives — 85 % | yes | **HIT.** Counter, bottles, glasses, warm strip lighting, panelling. |
| **no other people — 80 %** | none | **MISS, and by the widest margin of the run.** A seated human figure is present at the frame edge in every frame inspected at full size, plus a hand near the counter in some. The negative that E08 named as the cause of their absence is byte-identical here. |
| the face reads as the twin's at ≥ 3 of 5 sampled frames — 65 % | yes | **HIT** — 6 of 6 at the fastest frames, which is the hardest sample this seat could pick. |
| no frame resolves fingers — 90 % | none | **HIT.** |
| the vertical banding is still present — 70 % | yes | **NOT SUPPORTED as stated, and not tested.** E08's washed vertical bands are not what this output shows; what it shows is a whole-frame luminance swing. This seat built no instrument that separates the two, and E08's own two banding instruments were reported as failed instruments. |
| the painted body tracks the sticks at every sampled frame — 85 % | yes | **HIT**, checked by compositing the driving sticks onto the output at the four fastest frames rather than at even spacing. |

**The pattern in my own misses:** both H-E10a tail misses fell on the same side — the
per-frame drop was *larger* than predicted, from a model that reasoned about the mean and
then assumed the median and max would sit near it. And the largest miss, the crowd clause,
was a prediction inherited from E08's outcome rather than derived: the negative prompt is
identical, so nothing about the *text* changed, and I read "the negative excludes people" as
if it were a mechanism rather than a candidate cause E08 had explicitly labelled as one.

---

## 13. Artifacts

| artifact | sha256 (first 32) |
|---|---|
| the resampled motion record, 81 frames | `26098e2f40b6bde63bd1af338555ecbc` |
| the densified GLB (81 keys @ 20 fps) | `1b16089a23637ea2f30f030fad940a7f` |
| projected keypoints, shot (832×480, camera pinned to E08) | `f8fbb568804a31ce52c8dab11a41e453` |
| stick manifest (81 frames + per-frame hashes) | `fa5087ecd64749c7e8b03043d9dd5457` |
| the pose pack, as uploaded (APNG, 81 frames) | `47909b26b955218d9e8575c30bd64094` |
| projected keypoints, overlay (1920×1080) | `3a37738ab251f6c8ca1f0259940c3062` |
| densified previz render provenance | `e29c729915816eba449f0e7d6e309168` |
| the graph, as built | `21fd329a4261cb060e901f241bf5e3f1` |
| the payload record | `ee093d6fb2cc056c33a80f0d2144cd7c` |
| the saved projection, as the cloud holds it | `1f49a08f6866cb5938ebbb0c86a0e846` |
| saved-graph admission (values + links + gates) | `e3cc0be10bad507206cdc72b81f12e51` |
| Gate B evidence (81/81) | `c1c2b2ec34209dcf48421b5db2d18f52` |
| smoothness measurement (H-E10a) | `2b643b70797a610b129f1f1d12603ad3` |
| luminance measurement | `c2ece3b2b4eb04bda40a33ac9d9ea5dd` |
| **the Gate 0 sheet** | `f92ca93c3cb50e871a7aad45a258346b` |
| the pre-spend overlay | `367523e54f8f09030043b2d7772a3cf3` |
| the feet detail | `8cd7cdfece3a40af364fcc60ed37c9b4` |
| painted output with its own driving sticks | `b99974efe3edf8f597939a0ce03280b6` |
| **the true-tempo A/B, lossless** | `30efeb93bb151a1590ba7199785d3802` |
| the 0.50× review clip, lossless | `423801780606acd56a2fac513a7c188b` |
| 81 lossless frames | per-frame in `outputs/E10/probe/lossless/` |

New in the tree: `armature_core/resample.py`, `resample_motion.py`, `measure_smoothness.py`,
`gate_b_frames.py`, `make_ab_clip.py`, `make_zoom_sheet.py`, `specs/E10-seeds.json`, the
`route_gates` INDETERMINATE clause and seed-gate fix, `build_animate_payload`'s
length/fps/experiment parameters and its in-tool Gate ROUTE, `gate_saved_graph`'s Animate
classes and topology round trip, and corrections to `make_e08_sheet` and `make_review_clip`.

**Suite: 656 passed, 46 skipped.** The comparable baseline is `main` at `e80f813` measured
in a **fresh worktree with no `outputs/`**: **553 passed, 46 skipped**. (Measuring `main` in
its own long-lived worktree reads 588/11 — 35 tests there require banked artifacts under
`outputs/`, which is git-ignored, so a suite count is only comparable between trees with the
same artifacts present. Recorded because E08's report quotes 556/43 and the difference is
the tree, not the code.)

---

## 14. Compensators

| act | compensator | state |
|---|---|---|
| the probe generation `263bc224…` | **none exists** — spent GPU time has no undo | 1 of 2; reserve `2026081222` unspent |
| uploaded pose pack `c8f4d8df…8591faf3.png` | delete server-side (Comfy Cloud inputs) | **present; owner executor** |
| uploaded reference `54a38251…6125758a84f.png` | delete server-side | **present; owner executor** — the same object E08 uploaded, kept by that experiment's ruling |
| saved cloud workflow `armature-E10-probe-animate` (`9240e68a-710d-4cce-a2e0-903d05f3acf5`) | delete server-side | present; owner executor |
| downloaded outputs under `outputs/E10/` | delete the directories | written; owner executor |
| worktree + branch `E10-density` | `git worktree remove` + branch delete | owner advisor, after the ruling |

**Every uploaded artifact is listed above with its named undo.** Two uploads, one saved
workflow, one generation. No publishes, no releases, no external posts, no writes to the
memory store.

---

## 15. For the advisor

Measured here, with no authority to rule on any of it:

1. **The spec's "~19.95 fps" and its "endpoints exact" clause disagree.** 20.0 is what
   endpoint-exact resampling gives; 19.9385 is the frames÷fps convention. The deliverables
   use 20.0 and the provenance records both. The spec should be corrected in place.
2. **Premise 4 was false as stated** — matrices, not quaternions — and the conversion is
   tested. Premise 3 was assumed and is confirmed from the node schema.
3. **The painted output changed in a way this experiment did not aim at.** A ~10× larger
   frame-to-frame luminance swing, and people in the bar where E08 had none. Two registered
   changes could cause either (81 frames at the trained horizon; a new seed), and nothing
   here separates them. The discriminating run is the reserve seed at the same 81 frames.
4. **A new frame count forces a new seed on this route** — the latent's shape changes, so
   the same integer cannot reproduce E08's noise field even in principle. E10 could not have
   been a same-seed comparison, and any future "one variable" claim across frame counts
   carries this rider.
5. **Four tool defects fired at use in one session** (§9), three of them labels asserting
   things that were no longer true when a tool was pointed at a second experiment. The
   pattern is worth a rule: **a tool that names an experiment in a literal is a tool that
   will lie the first time it is reused.**
6. **E08's GPU-hours ledger item can probably be closed at ≈ $0.26**, on the reading in §11,
   which is a reading and not a confirmation.
7. **The stick-level lever worked and the per-second control says why**: densification did
   not smooth the performance, it re-sampled the same performance in smaller steps. Whether
   that is what the Director's eye wanted is his call, and the A/B is built for it.

The Director judges the motion at true tempo.
