# E11 wave 3 — blind predictions, registered before the first submission

**Executor seat, 2026-08-12, branch `E11-nocontrol`.** Committed BEFORE `submit_workflow` is
called on the wave-3 graph. Nothing of wave 3 has been generated: the start frame is
rendered, the graph is built, gated and saved, and no job exists.

## Blindness, disclosed

**Blind with respect to wave 3 — completely.** No wave-3 generation exists at the time of
writing.

**NOT blind with respect to waves 1 and 2.** Before writing these degrees this seat had read
both reports and the w2 ruling, and had looked at full size at: wave 1's start frame and its
f0/f64; wave 2's f0–f4, f8, f32, f64 and its 3× head/hand zooms; and wave 3's own re-authored
start frame and RGBA master. So these are informed priors, not naive ones.

## The wave is MULTI-BREAK — nothing below isolates a lever

Six things move together against wave 1: the **experts** (I2V → Fun-Camera), the **camera
embedding** (absent → `Static`), the **prompt** (bar-led → performance-led), the **length**
(65 → 81), the **resolution** (832×480 → 1024×576) and the **start frame** (grey baked void
→ RGBA authored, dim warm composite). The comparison is route-level. No clause below may be
read as evidence about any single change, and the report will not read them that way.

## ⚠ Instrument limits, named before the numbers

Carried forward from wave 2's predictions, all still true, plus two new ones:

- **`horizon_row` needs the room to survive** to say anything about camera hold. A held
  camera over a replaced room still reads NOT FOUND. **New for wave 3:** the start frame's
  backdrop is now a dim warm tone over a pale floor, which is *higher* contrast than wave
  1's grey-over-pale, so the horizon should be more findable while the authored room lasts —
  making a low count more attributable to replacement than to the camera.
- **`similarity_to_first` is conflated by construction** and this wave asks the subject to
  move more.
- **NEW — the resolution changed, so pixel statistics are not strictly comparable.**
  Frame-delta and |Δ luma| are means over pixels; at 1024×576 the same physical motion covers
  more pixels and finer detail survives the VAE. Cross-wave numeric comparisons on these two
  are indicative, not like-for-like, and the report must say so rather than quoting them flat.
- **NEW — 81 frames against 65 means the tail is longer.** Any "by frame N" clause is
  measured on a clip 25 % longer, so drift has more room to accumulate.

## H-E11p — did the correction work at all? (the headline)

Wave 2 spent a generation on a graph that could only produce noise. This is the first
question, and it is genuinely open — Gate PAIR proves the pairing is *right*, not that the
result is *good*.

| # | claim | unit | degree |
|---|---|---|---|
| p1 | the clip does NOT collapse to a structureless field | binary, full size | **85 %** |
| p2 | a recognisable jointed mannequin is present in the final frame (f80) | one frame, binary, full size | **80 %** |
| p3 | the subject survives past f8 (wave 2 died at f2) | binary | **85 %** |

## H-E11j — the camera (the lever's first actual test)

| # | claim | unit | degree |
|---|---|---|---|
| j1 | `horizon_row` FOUND on more than 4 of 81 frames | count | **65 %** |
| j2 | FOUND on at least 41 of 81 (half) | count | **45 %** |
| j3 | FOUND on the final frame f80 | binary | **35 %** |
| j4 | the figure is NOT cut by any frame border at f80 (wave 1: cut from f32) | binary, full size | **60 %** |
| j5 | the figure's on-screen height at f80 is within ±15 % of f0's | ratio of two pixel heights | **55 %** |
| j6 | `similarity_to_first` at f80 exceeds wave 1's −0.1984 | one number | **70 %** |

j4 and j5 remain the clauses that actually test the lever; j1–j3 are hostage to whether the
room survives.

## H-E11k — motion character (the Director's diagnosis, first actual test)

The prompt surgery rides unchanged from wave 2 and has **never been tested** — wave 2's
frames had no subject to judge it on. This is its first measurement.

| # | claim | unit | degree |
|---|---|---|---|
| k1 | frame-delta median exceeds wave 1's 5.282 | median over 80 adjacent pairs (⚠ different resolution) | **55 %** |
| k2 | 81 of 81 frames distinct | count | **90 %** |
| k3 | at least one frame shows both arms above shoulder height | binary, full size | **55 %** |
| k4 | the Director calls the motion a dance rather than a wobble | **his eye — this seat does not judge it** | **45 %** |

## H-E11m — the hands

Unchanged prior: the base negative already carried five hand/deformity terms and wave 1's
claw came through all of them; the GLB's hands are mittens; the performance clause asks for
faster, wider arm motion. **New consideration pushing m1 up slightly:** 1024×576 gives the
hands ~48 % more pixels than 832×480, and fine structure is where resolution helps most.

| # | claim | unit | degree |
|---|---|---|---|
| m1 | hands read as clearly better than wave 1's claw at full size | two crops, described not judged | **25 %** |
| m2 | hands read as clearly worse than wave 1's | same | **30 %** |
| m3 | at least one frame shows a hand with separated fingers | binary, full size | **15 %** |

## H-E11n — does world replacement survive the weight swap? (the dispatch's new question)

Wave 1 replaced the authored studio completely by f8 and produced ≥4 people from a prompt
that named a crowd. Wave 3 differs three ways that all bear on this: the prompt no longer
mentions people at all (8 words of set dressing), the start frame's backdrop is already
bar-toned rather than studio grey, and **the weights are a Control-tier derivative** —
`Wan2.2-Fun-A14B-Control-Camera` — and control models are generally trained to hold their
input more tightly than a plain I2V base.

| # | claim | unit | degree |
|---|---|---|---|
| n1 | the authored pale floor is gone by f8 | binary, full size | **55 %** |
| n2 | a bar counter is legible at f80 | binary, full size | **60 %** |
| n3 | at least one other human figure appears anywhere | binary | **40 %** |
| n4 | four or more human figures, as in wave 1 | binary | **15 %** |
| n5 | the dim warm backdrop persists rather than being replaced | binary | **40 %** |

n3/n4 are the cleanest read available of the bar's own semantic gravity: nothing in this
prompt names a person.

## H-E11q — the run

| # | claim | unit | degree |
|---|---|---|---|
| q1 | `estimate_credits` 0, billed as GPU time only | credits | **95 %** |
| q2 | Gate B reports the server decode pixel-identical to the local composite | binary | **90 %** |
| q3 | no gate fires after submission | binary | **85 %** |

## What would make this wave uninformative

Stated in advance so it cannot be rationalised after: if the clip collapses again (p1 false),
then every clause from j through n is unreadable and the wave measures only that the weight
swap was not sufficient — in which case the **named next candidate is already on the record**
in the payload as `trajectory_premise`: this graph runs cfg 3.5 / euler off the I2V reference
workflow while the catalog recommends cfg 6.0 / uni_pc for these exact files. That is a
prediction about what the failure would mean, registered before seeing whether it happens.
