# E11 wave 2 — blind predictions, registered before the first submission

**Executor seat, 2026-08-12, on branch `E11-nocontrol`.** Committed BEFORE
`submit_workflow` is called on the wave-2 graph. Nothing of wave 2 has been generated: the
graph is built, gated and saved, and no job exists.

## Blindness, disclosed

**Blind with respect to wave 2 — completely.** No wave-2 output exists at the time of
writing; there is nothing to have peeked at.

**NOT blind with respect to wave 1**, and that matters for reading these numbers. Before
writing them this seat had read `E11-report.md` and `E11-probe-ruling.md` in full, and had
looked at wave 1's start frame and its frame 64 at full size. Every degree below is
therefore an informed prior conditioned on wave 1, not a naive one — which makes a MISS more
informative than usual, since the prior had the sibling run to lean on.

## The two levers, and why nothing below may be attributed to either alone

Wave 2 is a **composed** wave by the Director's direction: the camera embedding and the
prompt surgery move together. These predictions are about OUTCOMES, not about which lever
produced them. No clause below should be read as evidence for the camera embedding or for
the prompt in isolation, and the report will not read them that way.

## ⚠ The instruments' limits, named before the numbers

Two of the three diagnostics this wave leans on are conflated, and saying so afterwards
would be worth much less than saying so now.

- **`horizon_row` is not a clean camera-hold instrument on this route.** It finds the
  strongest horizontal edge a frame's columns agree on. That requires the ROOM to keep one.
  Wave 1's authored studio dissolved by f4 and the horizon was never found again — and the
  report's own full-size reading of those four frames says the row moving 155 → 292 was
  **the backdrop's lower edge sliding as it dissolved, not a camera tilt.** So on this route
  a lost horizon is ambiguous between "the camera moved" and "the room was replaced," and a
  held camera over a replaced room could still read NOT FOUND on all 65 frames. On E08 the
  same instrument reports NOT FOUND on 65/65 correctly, because that background has no
  authored horizon at all.
- **`similarity_to_first` is conflated by construction** — it moves with the subject, the
  camera, the exposure and the scene alike, and separates none of them. Wave 2 deliberately
  asks the subject to move MORE, which pushes this number down for reasons that have nothing
  to do with the camera.
- **The most direct framing read available is the border test** — whether the figure is cut
  by the frame edge, and where. Wave 1 was whole through f24 and cut from f32 on, under a
  large push-in. It is not perfectly clean either (a dancing figure can leave the frame by
  dancing), but it does not require the room to survive.

## H-E11e — the camera (the lever's own target)

| # | claim | unit | degree |
|---|---|---|---|
| e1 | `horizon_row` is FOUND on more than 4 of 65 frames | count of frames where the columns agree on a horizontal edge | **60 %** |
| e2 | `horizon_row` is FOUND on at least 32 of 65 frames | same | **35 %** |
| e3 | `horizon_row` is FOUND on the final frame (f64) | one frame, binary | **30 %** |
| e4 | the figure is NOT cut by any frame border at f64 (wave 1: cut from f32) | one frame, binary, read at full size | **55 %** |
| e5 | `similarity_to_first` at f64 is higher than wave 1's −0.1986 | one number | **65 %** |
| e6 | no large uncommanded push-in — the figure's on-screen height at f64 is within ±15 % of f0's | ratio of two pixel heights | **50 %** |

e1–e3 are deliberately low for a wave whose whole point is holding the camera: the
instrument needs a surviving room, and h1 below says the room probably does not survive. e4
and e6 are the clauses that actually test the lever.

## H-E11f — motion character (the Director's diagnosis under test)

His wave-1 reading was **drunken wobble, not a dance**, and his diagnosis was that the bar
language pulled the performance toward it. The prompt surgery is that diagnosis operationalised.

| # | claim | unit | degree |
|---|---|---|---|
| f1 | median per-frame delta exceeds wave 1's 5.282 | median over 64 adjacent-frame pairs, 0–255 mean abs | **60 %** |
| f2 | 65 of 65 frames distinct | count | **90 %** |
| f3 | at least one frame shows both arms above shoulder height | one frame, binary, read at full size | **45 %** |
| f4 | the Director calls the motion a dance rather than a wobble | **his eye — this seat does not judge it** | **45 %** |

f4 is recorded as a degree only so the seat is on the record with a number it can be wrong
about. **The verdict is his and no measurement here substitutes for it.**

## H-E11g — the hands (genuinely uncertain, and the prior says so)

The base negative already carried five hand and deformity terms — 残缺的, 多余的手指,
画得不好的手部, 畸形的, 手指融合 — and wave 1's claw appeared through all of them. The
extension adds two more. The source GLB's hands are **mittens**: closed loops with no
separated fingers, visible in the start frame at full size. A prompt cannot add fingers to
geometry that has none.

| # | claim | unit | degree |
|---|---|---|---|
| g1 | hands read as clearly better than wave 1's claw at full size | two crops, this seat's description only — the Director judges | **20 %** |
| g2 | hands read as clearly worse than wave 1's | same | **35 %** |
| g3 | at least one frame shows a hand with separated fingers | one frame, binary, full size | **15 %** |

g2 exceeds g1 on purpose: the performance clause asks for **faster, wider arm motion**, and
fast motion is where structure degrades. Buying dance with hands is the trade this wave may
have made.

## H-E11h — the scene (read under the two-seed rule; one seed proves no route property)

Wave 1's prompt said "crowded ... other people around him" and produced at least four
figures past a crowd-suppressing negative. **Wave 2's prompt removes every mention of
people and of crowding** — the bar is eight words of set dressing. What the bar does now is
a cleaner read of the word's own semantic gravity than wave 1 could give.

| # | claim | unit | degree |
|---|---|---|---|
| h1 | the authored grey studio is gone by f8 | one frame, binary, full size | **80 %** |
| h2 | at least one other human figure appears anywhere in the clip | binary over frames read | **45 %** |
| h3 | four or more human figures appear, as in wave 1 | binary | **20 %** |
| h4 | a bar counter is legible in the final frame | one frame, binary, full size | **70 %** |

h2/h3 are the interesting pair. Wave 1 got its crowd with the crowd named in the prompt;
if a crowd arrives here with nothing naming it, the bar is supplying the people by itself.

## H-E11i — the run

| # | claim | unit | degree |
|---|---|---|---|
| i1 | `estimate_credits` reports 0 and the graph bills as GPU time only | credits | **95 %** |
| i2 | Gate B reports the server's decode pixel-identical to the local start frame, as in wave 1 | binary | **90 %** |
| i3 | the run completes without a gate firing after submission | binary | **85 %** |

## What would make this wave uninformative

Stated in advance so it cannot be rationalised afterwards: if the world is replaced as
completely as wave 1's was, `horizon_row` will be NOT FOUND on nearly every frame and e1–e3
will be unreadable as camera evidence. In that case the camera claim rests on e4 and e6 —
the border and the on-screen scale — and the report must say so rather than quoting a
horizon count as though it settled anything.
