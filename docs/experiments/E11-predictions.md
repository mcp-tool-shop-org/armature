# E11 — predictions, registered before the submission

**Registered by the executor seat on `E11-nocontrol`, 2026-08-12, before any E11 generation
existed.** Committed ahead of the first submission so the git timestamp carries the claim
rather than the prose.

## Blindness, disclosed

What this seat **had** seen when these were written:

- **The start frame, at full size, and four 4× crops of it** (head, both hands, feet). Not
  optional — CLAUDE.md requires looking at an artifact before it uploads, and the whole
  point of Gate WHOLE is that somebody looked. Every prediction below is therefore informed
  by knowing exactly what the model is being handed.
- **E08's and E10's reports in full**, including their measured outcomes: E08's bar arrived
  complete and empty of people; E08's face read at 4 of 5 sampled frames; E10's people
  appeared unasked and its frame-to-frame luminance swing was ~10× E08's.
- The built graph, its gate evidence, and `estimate_credits` (0).

What this seat had **not** seen: any E11 output, in any form. No E11 generation had been
submitted, and no partial result existed. The queue was not consulted for one.

**The degrees are this seat's own** and are not derived from any published benchmark for
this model.

## The reading rule these are scored under

E10's closing ruling R3 binds E11 from birth: **one seed is an observation, never a route
property.** Every scene and identity clause below is scored as an observation of one
generation. Nothing here, however it resolves, may be written up as a property of the
no-control route.

## H-E11a — identity: does he stay HIM with nothing holding his shape

The route's headline risk. Unconstrained generation is free to morph a stylized figure
toward the human prior, and there is no skeleton, no reference socket and no mask.

| # | clause | degree |
|---|---|---|
| a1 | the terracotta / bald jointed-mannequin read survives to the **final** frame | **70 %** |
| a2 | **no** visible identity drift in the first 16 frames (the first second) | **80 %** |
| a3 | visible identity drift **somewhere** in the clip | **65 %** |
| a4 | the face still reads as a face — brows, eye, mouth discernible at full size — in the final frame | **50 %** |
| a5 | the visible ball joints at knees and hips survive to the final frame | **60 %** |
| a6 | no frame resolves fingers | **85 %** |

**"Visible drift" is defined before the fact**, so it cannot be defined around the result: a
feature present at frame 0 — the bald head, the drawn face, the mitten hands, the ball
joints at knees and hips — is absent or replaced at some later frame, read at full size.

The prior behind a1 and a4: an I2V start frame is a pixel-exact anchor at frame 0 and a
weakening one after it, and the head here is roughly 40 px tall. E08's identity clause beat
this seat's predecessor's prediction badly, which is a reason to predict identity *higher*
than instinct says; the counterweight is that E08 had a reference image and a driving
skeleton and this has neither.

## H-E11b — motion character: the Director's hypothesis

**Recorded as his:** freed from choppy driving, the model's own motion may read smoother and
livelier than the driven route's. **His eye rules that**, at true tempo, on the two-pipeline
sheet. This seat predicts only measurables, and one of them is a coin-flip it expects to
learn from.

| # | clause | degree |
|---|---|---|
| b1 | the figure's limbs visibly move — some limb travels more than its own width across the clip | **80 %** |
| b2 | E11's **median** frame-to-frame mean-absolute pixel delta is LOWER than E08's 3.95 | **55 %** |
| b3 | E11's frame-to-frame median \|Δ luma\| is nearer E08's 0.84 than E10's 9.05 | **60 %** |
| b4 | at least one frame shows a limb in a shape the rig could not make (a bend against a joint, a limb count wrong, a hand fused to the body) | **45 %** |

b2 is deliberately close to even. Free generation could read either as more motion (nothing
constrains it, and the negative prompt names 静态 and 静止不动的画面 outright) or as less
(E09's own T2V probe returned a near-still donor at 0.703/255 mean consecutive delta from a
prompt that asked for dancing). This seat does not know which, and says so with the number.

## H-E11c — scene: does the bar arrive

**The clause the start frame changes most, and this is stated before the result.** E08's
background plane was a uniform mid-grey the model was free to fill. E11's start frame is a
*specific grey studio with a white floor and a horizon line at 31 % down the frame*, and an
I2V generation begins from that image literally. The prompt is therefore asking the model to
**replace** what it can see rather than to fill a silence, and this seat expects that to cost
the scene clause heavily.

| # | clause | degree |
|---|---|---|
| c1 | a recognisable bar — counter, bottles, or back-bar shelving — present in the **final** frame | **35 %** |
| c2 | the clip is visibly warmer at the end than at frame 0 | **55 %** |
| c3 | the studio horizon line is still visible in the final frame | **60 %** |
| c4 | other people appear anywhere in the clip | **15 %** |

c4 is low for three reasons stacked: Wan's default negative names 杂乱的背景 and 背景人很多
(both carried verbatim from E08), the start frame contains nobody, and the model has one
image to extrapolate from. E10 saw a person appear unasked on the other route; this seat
does not treat that as transferring.

## H-E11d — the route's price: camera and framing

Named in the spec as a **characteristic, not a defect**. Measured, not judged.

| # | clause | degree |
|---|---|---|
| d1 | the framing at the final frame is not the start frame's framing — the camera moved | **65 %** |
| d2 | similarity to frame 0 declines across the clip and does not recover to its early value | **70 %** |
| d3 | some part of the figure is cut by the frame border in at least one frame | **40 %** |

The prompt says "The camera is static", carried verbatim from E08 where it was one clause
among many. Nothing enforces it.

## Operational

| # | clause | degree |
|---|---|---|
| o1 | 65 lossless frames come back, all distinct | **85 %** |
| o2 | Gate B — the start frame as the server decoded it is pixel-identical to the local render | **85 %** |
| o3 | no gate fires on the run | **75 %** |

## The stated fail condition

If the returned clip is a near-still hold of the start frame — the figure's limbs not moving
more than their own width across all 65 frames — then this arm has not tested the Director's
motion question at all and the report says so plainly rather than reading motion character
off a hold.
