# E11 wave 3 — report: the camera held to one pixel, and the world it was given never left

**Executor seat, 2026-08-12, branch `E11-nocontrol`.** The corrected wave 2, per the E11 w2
ruling R5, on the last reserve. **One generation** (`prompt_id`
`61e03fe0-8433-4794-b2e8-2ce16ba977a9`, seed `2026081233`). **The ceiling is now exhausted:
3 of 3.** No gate fired.

**No judgement of quality is offered or implied.** The advisor rules; the Director judges the
dance, the camera and the hands. What follows is what was built, what the gates said, what
came back, and what this seat looked at.

**Look first:** `outputs/E11/w3/review/E11-w3-vs-w1-truetempo.webp` — wave 1 beside wave 3 at
true tempo; and `outputs/E11/w3/sheets/E11-w3-hands.png`, which carries the one finding a
number cannot.

---

## 1. Premise table — every claim marked, the weight files named

The w2 ruling's first law: *a licence row is not a wiring claim*, and every spec adding a
conditioning node names the exact weight files its graph loads as a marked premise. Wave 2
shipped without this table; that omission is what the generation bought.

| # | premise | status |
|---|---|---|
| 1 | The graph loads **`wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors`** and **`wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors`** | **MEASURED** — names read from `search_models` 2026-08-12 (exactly four `fun_camera` diffusion_model entries exist: bf16/fp8_scaled × high/low), asserted on the built graph by a test, and re-read off the saved file by `gate_saved_graph` |
| 2 | Those weights are the family `WanCameraImageToVideo` requires | **MEASURED** — Gate PAIR reports `families_present ['fun_camera']` on both the built and the saved graph, and goes RED on wave 2's banked graph |
| 3 | Their licence permits commercial use | **MEASURED** — `docs/license-map.md` line 43 on `main` (Apache-2.0, re-fetched at the w2 ruling). ⚠ This seat previously reported "no Fun-Camera row at all" from a stale branch checkout; the row was on `main`. Corrected by the ruling and read from `main` this session |
| 4 | Length 81 is the model's trained frame count | **MEASURED** — card README_en.md, fetched 2026-08-12, verbatim: *"multi-resolution (512, 768, 1024) video prediction, trained with 81 frames at 16 FPS"* |
| 5 | 1024×576 is the nearest in-distribution frame to our aspect | **DERIVED** — from premise 4's tiers; enumeration in `FRAME_DERIVATION` and §3 below |
| 6 | The camera node's socket schema | **MEASURED** — `get_node` 2026-08-12; widget order re-confirmed empirically on the converted save file at the new size |
| 7 | The sampling trajectory (steps 20, split 10, shift 8.0, cfg 3.5, euler, simple) transfers from the I2V reference workflow to the Fun-Camera derivative | **ASSUMED — marked, not measured.** The catalog's own `recommended` for these exact files says **cfg 6.0, uni_pc** — both differ from what ran. Held because the wave already moves five other things; recorded in the payload as the first named candidate if the run disappointed |
| 8 | The start frame is a legal, whole-figure conditioning image at 1024×576 | **MEASURED** — Gate WHOLE (height frac 0.9023, smallest margin 26.6 px), Gate COVERAGE (0.0771), Gate ALPHA (0.2960 transparent), and looked at at full size before upload |
| 9 | Billing 0 credits / GPU-hours metered | **MEASURED** — `estimate_credits` 0, as E08 §12 |
| 10 | Comparability to wave 1 | **BOUNDED — route-level only.** Six properties move together; see §2 |

## 2. Six things moved — nothing here isolates a lever

| | wave 1 | wave 3 |
|---|---|---|
| experts | `wan2.2_i2v_{high,low}_noise_14B_fp8_scaled` | `wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled` |
| camera | text only: "The camera is static." | `WanCameraEmbedding`, pose `Static`, 1024×576×81 |
| prompt | identity + 30-word bar scene containing the word "dancing" | identity **verbatim** + 52-word performance clause + 8-word set dressing |
| length | 65 | 81 |
| resolution | 832×480 | 1024×576 |
| start frame | 832×480 RGB, world background baked opaque | 1024×576, authored RGBA, composite over linear 0.035/0.022/0.014 |
| **held** | — | **the sampling trajectory, imported not retyped** |

Gate LEDGER required each of the four deliberate breaks to have *actually happened* — a
corrected run that silently still loaded the I2V experts or still ran 65 frames would ship a
report describing a correction that is not in the graph. Its verdict: *4 deliberate breaks
verified as actual; trajectory held; positive still differs from wave 1's.*

## 3. The frame, derived

The card's tiers are area buckets; at aspect *r*, tier *N* gives w = N·√r, h = N/√r, rounded
to the VAE's multiple of 16.

| tier | frame | area | disposition |
|---|---|---|---|
| 512 | 688×384 | 264,192 | rejected — below waves 1–2's 399,360, a downgrade |
| **768** | **1024×576** | **589,824** | **chosen** — 768·4/3 = 1024 and 768·3/4 = 576, both already multiples of 16: the tier is hit with **zero rounding**, and it is the nearest tier above waves 1–2 |
| 1024 | 1360×768 | 1,044,480 | rejected — ≈3.3× wave 1's pixel-frames on the last reserve for nothing the card promises |

Waves 1–2 ran 832×480 = 399,360 px, which **matches no tier**: it is the plain I2V model's
default, which is a different model's document. The aspect consequently moves 1.733 → 1.778;
the start frame was re-rendered at the new size, so the camera reframed rather than anything
being stretched.

## 4. Gate states

**Before submission:** Gate LEDGER (4 breaks verified, trajectory held, positive differs) ·
**Gate PAIR** (`families_present ['fun_camera']`) · Gate L `PASS` on profile
`wan-fun-camera` · Gate S (seed pre-registered) · Gate ROUTE built (4 weight files, 2 seeds
pinned, 1 of 1 latent checkable, 2 frames legal, 1 camera trajectory on the generated frame)
· Gate ROUTE saved (51 values, 23 links, `50.clip_vision_output` and `80.audio` empty in
both formats) · Gate L saved `1024x576x81 legal (PROVEN)` · Gate PAIR on the saved graph ·
camera widget order re-confirmed empirically · `estimate_credits` **0**.

**Render gates:** Gate WHOLE, Gate COVERAGE, **Gate ALPHA** (0.2960 of the frame transparent
— the void above the floor line, against an opaque floor and figure).

**After submission:** **Gate B** — batch intact, server decode **pixel-identical** to the
local composite, 81 painted frames.

## 5. What came back, looked at

Every frame named was opened at full size; the zooms are 3× native.

- **f0** — the start frame round-tripped: the mannequin whole, dim warm backdrop above a pale
  floor, horizon at row 183, shadow to screen-left. Face legible at 3×: brow, closed lidded
  eye, long nose, mouth line, ear, thumbprint hatching on the torso.
- **f8** — figure coherent and clearly the same character, mid-motion, arms out. **The world
  is unchanged.** At 3× the screen-left hand has grown **four or five separated, thin,
  spiky digits** where the authored mitten was.
- **f40** — figure coherent, arms extended. The world unchanged. The screen-right hand has
  **smeared into wisps** with no structure.
- **f60** — figure mid-stride, one hand smeared. World unchanged: backdrop, floor, horizon,
  shadow. No bar, no counter, no people.
- **f80** — figure coherent and whole in frame, arms extended wide, one leg lifted. World
  unchanged. At 3× the arm terminates in a rounded stump with no hand visible.

**Across all 81 frames the authored studio is never replaced.** There is no bar, no counter,
no bottles, no floor change and no other human figure at any point this seat examined.

**Identity.** The face persists to the final frame: same bald crown, single drawn brow,
closed lidded eye, long straight nose, thin mouth line, small ear. **The drift axis is
surface**: the matte sculpted clay and thumbprint hatching visible at f0 read progressively
smoother and waxier, and by f40–f80 the hatching is gone. A second axis the Director's eye
should land on: the limbs and neck read **longer** at f40–f80 than at f0.

## 6. Measurements

Source `outputs/E11/w3/measure/E11-w3-clip.json`, computed on the lossless PNG tap.

| quantity | wave 3 | wave 1 |
|---|---|---|
| frames / distinct | 81 / 81 | 65 / 65 |
| **horizon found on** | **70 / 81** | 4 / 65 |
| **horizon row range** | **182–183 (spread 1 px)** | 155 → 292 in three frames, then never found |
| **correlation with f0, last frame** | **+0.9247** | −0.1984 |
| mean abs difference from f0, last frame | 14.07 | 153.24 |
| frame-delta median (0–255) | 3.843 | 5.282 |
| \|Δ luma\| median | 0.148 | 0.210 |
| mean luma f0 → f80 | 158.6 → 163.4 (flat) | 180.8 → ~60 |

Correlation with f0 at f8 / f40 / f80: **0.9416 / 0.9151 / 0.9247** — high and without decline.
The eleven frames where the horizon is NOT found are scattered singletons (1, 14, 27, 41, 42,
50, 51, 52, 54, 68, 78), not a run — consistent with momentary column disagreement rather
than drift, since the row on either side of each is 182.

> ⚠ **The resolution changed, so frame-delta and |Δ luma| are not like-for-like across waves.**
> Both are means over pixels; at 1024×576 the same motion covers more pixels and finer
> detail survives the VAE. This was named in the predictions before the run. The horizon and
> correlation figures are not affected in the same way — a row index and a normalised
> correlation are comparable — which is why the camera claim rests on those.

## 7. Predictions versus outcomes

Registered blind at `docs/experiments/E11-w3-predictions.md`, committed at `b0ad995` before
`submit_workflow`. Blindness: complete with respect to wave 3; **not** blind with respect to
waves 1–2 or to wave 3's own start frame, disclosed there and here.

| # | claim | degree | outcome |
|---|---|---|---|
| p1 | no collapse to a structureless field | 85 % | **HIT** |
| p2 | recognisable mannequin at f80 | 80 % | **HIT** |
| p3 | subject survives past f8 | 85 % | **HIT** — survives all 81 |
| j1 | horizon found on more than 4/81 | 65 % | **HIT** — 70/81 |
| j2 | horizon found on ≥ 41/81 | 45 % | **HIT** — 70/81 |
| j3 | horizon found at f80 | 35 % | **HIT** — found, row 183 |
| j4 | figure not cut by any border at f80 | 60 % | **HIT** — whole in frame, read at full size |
| j5 | on-screen height at f80 within ±15 % of f0 | 55 % | **HIT, read by eye not measured** — the figure is slightly shorter at f80; this seat did not build a bbox instrument for it and says so rather than quoting a number it did not compute |
| j6 | similarity at f80 above wave 1's −0.1984 | 70 % | **HIT** — +0.9247 |
| k1 | frame-delta median above 5.282 | 55 % | **MISS** — 3.843, and not like-for-like (§6) |
| k2 | 81/81 distinct | 90 % | **HIT** |
| k3 | a frame with both arms above shoulder height | 55 % | **NOT OBSERVED, coverage stated** — not seen in the six frames read at full size; all 81 were not inspected for it |
| k4 | the Director calls it a dance | 45 % | **his verdict — not this seat's to score** |
| m1 | hands clearly better than wave 1's claw | 25 % | **his verdict.** Described in §5: the failure mode CHANGED rather than simply improving or worsening |
| m2 | hands clearly worse | 30 % | **his verdict** |
| m3 | a frame with separated fingers | 15 % | **HIT** — f8, clearly separated digits |
| n1 | authored floor gone by f8 | 55 % | **MISS** |
| n2 | bar counter legible at f80 | 60 % | **MISS** |
| n3 | at least one other human figure | 40 % | **MISS** |
| n4 | four or more figures | 15 % | **MISS** |
| n5 | dim warm backdrop persists | 40 % | **HIT** |
| q1 | credits 0 | 95 % | **HIT** |
| q2 | Gate B pixel-identical | 90 % | **HIT** |
| q3 | no gate fires after submission | 85 % | **HIT** |

**The n-block missed four of five in the same direction, registered blind.** This seat
expected partial world replacement and got **none at all**. That is the mirror image of wave
1, whose executor also missed its four scene predictions in one direction — there, the frame
anchored the subject and surrendered the world; here it anchored both.

## 8. The finding this run hands back, bounded honestly

Wave 1 (I2V base, camera free, bar-led prompt, grey-void start frame) **replaced the world
completely by f8** and produced at least four people. Wave 3 (Fun-Camera control tier, camera
held, performance-led prompt, bar-toned RGBA start frame) **preserved the world completely
for 81 frames** and produced none.

**Six things differ, so this is not attributable to any one of them**, and at least three are
live candidates: the Control-tier weights are trained to hold their input; the prompt no
longer names a crowd or a counter; and the start frame is no longer contradicting the prompt
with a grey studio. Under the two-seed rule this is one seed, so it is an observation, not a
route property.

What IS attributable, because it is what the lever mechanically does and the number is
categorical rather than marginal: **the camera held.** Horizon row 183 → 182 → 183 across 81
frames, spread of one pixel, against wave 1's uncommanded push-in that lost the horizon after
four frames and cut the feet from f32.

## 9. The meters

| | |
|---|---|
| `estimate_credits` | 0 (all-OSS; the ceiling is counted in generations) |
| generations spent | **3 of 3 — the ceiling is exhausted** |
| reserves remaining | **none.** Any further E11 generation needs a new ceiling from the Director; this seat has not assumed one |
| GPU / queue time | metered by the provider; to the ledger when the window resolves |
| `prompt_id` | `61e03fe0-8433-4794-b2e8-2ce16ba977a9` |
| suite | 827 passed, 46 skipped (from 795) |

## 10. Artifacts

```
outputs/E11/w3/startframe/start_frame_rgba.png        the authored RGBA master
outputs/E11/w3/startframe/start_frame.png             the submitted composite
outputs/E11/w3/startframe/start_frame_provenance.json Gate ALPHA + the composite's reason
outputs/E11/w3/route/E11-w3-camera-i2v.api.json       the graph, as built
outputs/E11/w3/route/E11-w3-camera-i2v.saved.json     as the cloud converted it
outputs/E11/w3/route/E11-w3-payload-record.json       provenance, premises, frame derivation
outputs/E11/w3/route/E11-w3-saved-admission.json      saved-file gate evidence
outputs/E11/w3/probe/lossless/00000-00080.png         81 frames, the measurement source
outputs/E11/w3/probe/gate_b_evidence.json             Gate B
outputs/E11/w3/measure/E11-w3-clip.json               measurements, w3 beside w1
outputs/E11/w3/sheets/E11-w3-arc-strip.png            f0 f20 f40 f60 f80, native scale
outputs/E11/w3/sheets/E11-w3-face.png                 face f0 f8 f40 f80, 3x
outputs/E11/w3/sheets/E11-w3-hands.png                hands f0 f8 f40 f80, 3x
outputs/E11/w3/review/E11-w3-vs-w1-truetempo.webp     A/B against wave 1, true tempo
outputs/E11/w3/review/half-speed/                     0.5x / 8 fps pair + stills
tests/fixtures/E11-w2-camera-i2v.api.json             Gate PAIR's red test, banked
```

## 11. Open, for the ruling

The trajectory premise (#7) is still ASSUMED and was never tested: this graph ran cfg 3.5 /
euler while the catalog recommends cfg 6.0 / uni_pc for these exact files. The run did not
disappoint in the way that would have implicated it, so it remains open rather than
resolved — and with the ceiling exhausted, testing it is a new-ceiling decision, not this
seat's.
