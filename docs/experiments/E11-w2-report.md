# E11 wave 2 — report: the camera embedding ran on weights that were never trained to take one

**Executor seat, 2026-08-12, branch `E11-nocontrol`.** Wave 2 of the no-control route: the
composed wave the Director picked — camera embedding plus prompt surgery, one generation,
seed 2026081232 drawn from the registered reserves.

**No judgement of quality is offered or implied anywhere in this document.** The advisor
rules; the Director judges. What follows is what was built, what gates said, what came back,
and what this seat looked at.

---

## 0. The short version

The graph built clean, passed every gate before submission and every gate after it, and
generated 65 frames. **The generated frames contain no subject and no scene after f1.**
From f2 to f64 the output is a static orange lattice — a regular grid of red speckle over a
dark-to-orange vertical gradient — with no figure, no bar, no horizon and no camera.

A named cause was identified after the run and checked against the model catalog:
**`WanCameraImageToVideo` was fed a camera embedding while the graph loaded the plain
Wan 2.2 I2V experts.** The camera tier has its own weights —
`wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled.safetensors`, served in the same catalog
— and this graph loaded `wan2.2_i2v_{high,low}_noise_14B_fp8_scaled.safetensors` instead.

**This seat spent one generation and stopped.** The remaining reserve is unspent. Whether it
is spent on a corrected run is the Director's call and the advisor's ruling, not this seat's.

---

## 1. The premise that was never marked

The spec's premise table marked six premises measured or assumed for wave 1. **Wave 2 added
two nodes and no premise row**, and the missing row is precisely where this run went.

The wave-2 dispatch reads: "the graph moves to `WanCameraImageToVideo` + `WanCameraEmbedding`
(`camera_pose = "Static"`) — **both core, weights mapped Apache (consult #7 ruling)**." Two
distinct claims sit inside that clause and only the first was checked:

| claim | status going in | status now |
|---|---|---|
| the two node classes exist, are core, and carry the sockets described | **MEASURED** — `get_node`, 2026-08-12, before building | holds; the schema was as described |
| the weights for the camera tier are licence-mapped Apache | **ASSUMED**, inherited from consult #7 | the licence is Apache (§7) — but `docs/license-map.md` **carries no Fun-Camera row at all** |
| **the camera tier runs on the weights this graph already loads** | **never stated, never marked, never checked** | **falsified by this run** |

The third line is the one that mattered. The licence claim and the compatibility claim were
carried as a single phrase — "weights mapped Apache" — and a licence row for weights the
graph never loads says nothing about whether the graph's actual weights accept a camera
embedding. This is the repo's own recorded law, met head-on: *the same family can split
across variants; check the exact variant you are about to run, not the family name.* The
variant that was checked was the node's; the variant that ran was the model's.

## 2. The named cause, and how it was checked

After the frames came back, `search_models` was queried for the camera tier (zero spend).
The catalog serves, as `diffusion_model` entries:

- `wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors`
- `wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors`
- (plus bf16 variants and the Wan 2.1 1.3B/14B Fun-Camera pair)

This graph loaded `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` and
`wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` — imported from `build_i2v_payload` and
held constant against wave 1 deliberately, and recorded as held in `Gate PIN_W2`.

The upstream card for the camera tier
([alibaba-pai/Wan2.2-Fun-A14B-Control-Camera](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera),
fetched 2026-08-12) states it is **derived from `Wan-AI/Wan2.2-I2V-A14B`** and that it
"specializes in camera movement synthesis." A derivative trained to consume a camera
conditioning signal is a different set of weights from the base it was derived from; the
base has no channel for that signal.

**What is established and what is not.** Established: the camera tier has dedicated weights;
this graph did not load them; the output collapsed. **Not established:** that the weights
mismatch is the sole and sufficient cause. This was one generation with two levers moving
(camera embedding + prompt surgery) and a third difference nobody intended (the conditioning
node class itself changed from `WanImageToVideo` to `WanCameraImageToVideo`). A run that
swapped only the weights would separate them. No such run has been made.

## 3. What was held constant, and what moved

`Gate PIN_W2` checked the held variables against wave 1's committed record and halted on
drift. Its verdict: *start frame, frame, length and trajectory identical to wave 1; positive
deliberately different.*

| | wave 1 | wave 2 |
|---|---|---|
| start frame | `adcab015…png`, sha256 `9c3c026f…` | **the same upload, byte-unchanged** |
| frame | 832×480×65 @ 16 fps | same |
| trajectory | steps 20, split 10, shift 8.0, cfg 3.5, euler, simple | same — **imported**, not retyped |
| weights | `wan2.2_i2v_{high,low}_noise_14B_fp8_scaled` | same (**this is §2**) |
| conditioning node | `WanImageToVideo` | `WanCameraImageToVideo` |
| camera | text only: "The camera is static." | `WanCameraEmbedding`, pose `Static`, 832×480×65, speed 1.0, intrinsics at defaults |
| positive | identity clause + 30-word bar scene containing the single word "dancing" | identity clause **verbatim** + 52-word performance clause + 8-word set dressing; camera sentence dropped |
| negative | Wan `sample_neg_prompt`, unedited | same base + `爪状的手`, `钩状的手指` |
| seed | 2026081231 | 2026081232 |

Prompt dominance, measured in-tool rather than asserted: **52 performance words against 8 of
set dressing, ratio 6.50** against a 3.0 floor. Wave 1's equivalent was 1 against 30.

## 4. Gate states

**Before submission**

| gate | verdict |
|---|---|
| Gate PIN_W2 | held constants identical to wave 1; positive differs (the inverted clause) |
| Gate L (built) | `PASS`, profile `wan-i2v` |
| Gate S (built) | seed pre-registered |
| Gate ROUTE (built) | 4 weight files, 2 seeds all pinned, 1 of 1 latent checkable, 2 frames checked and generator-legal, 1 camera trajectory on the generated frame |
| Gate ROUTE (saved file) | 51 values compared, 23 links, optional sockets `50.clip_vision_output` and `80.audio` empty in both formats |
| Gate L (saved) | `832x480x65 legal (PROVEN)` |
| Gate S (saved) | 1 noise-bearing seed, pinned, drawn from the committed list of 3 |
| `estimate_credits` | **0** — no paid API nodes; the ceiling is counted in generations |

**After submission**

| gate | verdict |
|---|---|
| Gate B | batch intact; **server decode pixel-identical to the local start frame**; 65 painted frames |

**Every gate passed. The output is what §5 describes.** That combination is the finding
worth carrying forward more than any number here: the gate suite as it stands cannot see a
conditioning signal delivered to a model that has no channel for it. Every check it makes —
licence, seed, frame legality, link topology, camera/frame agreement, saved-file round trip
— was satisfied by this graph.

### Two gates fired on their own holes, before any spend

Both halted the work and both were resolved before submission; both are recorded because
they are the reason the run reached the cloud in a checkable state at all.

1. **`route_gates`** had no row for `WanCameraImageToVideo` in `LATENT_NODES`. Without it
   Gate L would have found zero checkable latents — the E08 vacuous-pass shape, one route
   later. A new `CAMERA_NODES` table and an andon were added for a defect nothing else
   bounds: a camera trajectory solved for a frame other than the one generated passes Gate
   L, Gate S and the licence clause with a clean receipt, and the node's own default length
   is 81 while this route runs 65.
2. **`gate_saved_graph` HALTED the submission** because its widget table had no row for
   either new class. This is the **second sighting** of that species after the `VAEDecode`
   case recorded in the same file — both times the fail-closed `is None` lookup stopped the
   work before a credit was spent, rather than silently skipping the node.

Resolving (2) closed a hole the code had flagged in itself: both index tables were derived
from **one** source, the `get_node` schema, because `search_templates` carries no served
workflow wiring this tier (checked 2026-08-12, 201 templates). The saved file the cloud
converted supplied the empirical second reading, and it agrees —
`WanCameraEmbedding.widgets_values == ["Static", 832, 480, 65, 1, 0.5, 0.5, 0.5, 0.5]`,
`WanCameraImageToVideo.widgets_values == [832, 480, 65, 1]`. Banked at
`outputs/E11/w2/route/E11-w2-camera-widget-order.json`.

## 5. What came back, looked at

Every frame named below was opened at full size. The strip is
`outputs/E11/w2/sheets/E11-w2-collapse-strip.png` (f0, f1, f2, f4, f64, native scale); the
zooms are `E11-w2-zoom-f0-f1.png` at 3×.

- **f0** — the start frame, VAE round-tripped. Grey backdrop over a pale floor, horizon at
  row 155, the terracotta jointed mannequin whole in frame, shadow to screen-left. Legible
  at 3×: brow, lidded eyes, long nose, mouth line, small ears, the clay surface.
- **f1** — the figure's **silhouette and limb arrangement are still readable at full-frame
  scale**: head, both arms, both legs, the shadow. But the frame is overlaid with vertical
  banding, the grey backdrop has gone brown-orange, and red speckle has appeared. **At 3×
  the face is already a smear** — no brow, no eyes, no mouth — and the screen-left hand has
  lost its edge into the floor.
- **f2** — no figure. A full-frame orange lattice: regular vertical and horizontal grid
  ruling, clusters of dark-red speckle, brighter toward the lower-left, dark at the top.
- **f3, f4, f8, f32, f64** — the same lattice throughout, drifting slightly in speckle
  distribution. No figure, no bar, no counter, no people, no horizon, no floor.

The subject survives **one** generated frame in silhouette and **zero** generated frames in
face.

## 6. Measurements — and why most of them cannot be read here

Source: `outputs/E11/w2/measure/E11-w2-clip.json`, computed on the lossless PNG tap.

| quantity | wave 2 | wave 1 |
|---|---|---|
| frames / distinct | 65 / 65 | 65 / 65 |
| frame-delta median (0–255) | 4.549 | 5.282 |
| \|Δ luma\| median | 0.974 | 0.210 |
| correlation with f0, last frame | **+0.2906** | −0.1984 |
| mean abs difference from f0, last frame | 122.32 | 153.24 |
| horizon found on | **1 / 65** | 4 / 65 |

**The transition series is where the run is legible:**

- frame-to-frame delta: **72.27** (f0→f1), **48.39** (f1→f2), 9.19 (f2→f3), then 2–7 for the
  rest of the clip.
- mean luma: **168.0** (f0) → 96.7 → 47.9 → 39.6 → 39.1, then flat at 40–42 to f64.
- similarity to f0: 0.0 → 72.27 → 119.16 → 126.42, then flat at 123–126.

Wave 1's equivalents change *gradually* across ten-plus frames (luma 180.8 → 171.1 → 156.9 →
147.6 → 123.5 → 113.8 → 94.6 → 85.4 → 68.7 …). Wave 2 saturates in three frames and then
holds.

> ⚠ **The motion and camera metrics return numbers on a clip with no subject, and those
> numbers must not be read as motion or camera measurements.** "65 of 65 frames distinct"
> and "frame-delta median 4.549" describe a noise field jittering. `similarity_to_first` and
> `horizon_row` were both flagged as conflated in the predictions document *before* the run;
> what this run adds is worse than conflation — the instruments have no arm to grade. Grading
> an arm only on what it can move is a rule this repo already holds, and here nothing moved
> that these instruments were built to see.

## 7. The licence position

`docs/license-map.md` carries rows for Wan2.2-Fun-A14B-Control, Wan2.2-VACE-Fun-A14B and
Wan2.2-Animate-14B. **It carries no Fun-Camera row.** The wave-2 dispatch's phrase "weights
mapped Apache (consult #7 ruling)" refers to a row the map does not contain.

Retrieved by this seat, 2026-08-12, zero spend:

| component | licence | commercial | source | notes |
|---|---|---|---|---|
| Wan2.2-Fun-A14B-Control-Camera | Apache 2.0 | **YES** | [HF card](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera), fetched 2026-08-12 — "本项目采用 Apache License (Version 2.0)" | derived from `Wan-AI/Wan2.2-I2V-A14B`; the card states **no** output-ownership clause of its own, so the umt5 precedent applies — the upstream grant governs and the derivative asserts nothing itself |

**Two facts on that card bear on any corrected run and are recorded, not resolved:** it is
trained on **81-frame sequences at 16 fps**, and it names resolutions **512 / 768 / 1024**.
This route runs 65 frames at 832×480. Whether that matters is not something this run can
answer.

Writing the map row is the advisor's; nothing has been added to `docs/license-map.md` by
this seat.

## 8. Predictions versus outcomes

Registered blind at `docs/experiments/E11-w2-predictions.md`, committed at `3803cec` before
`submit_workflow` was called. Blindness: complete with respect to wave 2 (nothing existed);
**not** blind with respect to wave 1, disclosed there and again here.

The predictions document named, in advance, the condition that would make the wave
uninformative — "if the world is replaced as completely as wave 1's was, `horizon_row` will
be NOT FOUND on nearly every frame and e1–e3 will be unreadable as camera evidence." **The
actual outcome is a stronger version of that condition than was anticipated**: not a replaced
world but no world at all.

| # | claim | degree | outcome |
|---|---|---|---|
| e1 | horizon found on more than 4/65 | 60 % | **MISS.** 1/65 — the start frame only. |
| e2 | horizon found on ≥ 32/65 | 35 % | **MISS.** |
| e3 | horizon found at f64 | 30 % | **MISS.** |
| e4 | figure not cut by any border at f64 | 55 % | **UNREADABLE.** There is no figure at f64. |
| e5 | similarity at f64 above wave 1's −0.1986 | 65 % | **numerically HIT (+0.2906) and meaningless.** A frozen noise field correlates with f0 better than a moving figure in a changed room does. Recorded as a hit only to show the metric scoring on an empty clip. |
| e6 | on-screen figure height at f64 within ±15 % of f0 | 50 % | **UNREADABLE.** No figure. |
| f1 | frame-delta median above 5.282 | 60 % | **MISS numerically** (4.549) **and unreadable** — it measures noise jitter. |
| f2 | 65/65 distinct | 90 % | **HIT** (65/65) **and unreadable** — noise is distinct frame to frame. |
| f3 | a frame with both arms above shoulder height | 45 % | **MISS.** No arms after f1. |
| f4 | the Director calls the motion a dance | 45 % | **not applicable** — there is no motion to call. His verdict is not sought on this clip. |
| g1 | hands clearly better than wave 1's claw | 20 % | **UNREADABLE.** No hands after f1. |
| g2 | hands clearly worse | 35 % | **UNREADABLE.** |
| g3 | a frame with separated fingers | 15 % | **MISS.** |
| h1 | authored studio gone by f8 | 80 % | **HIT in letter, wrong in substance.** The studio is gone by f2 — but so is everything else, which is not what the clause meant. |
| h2 | at least one other human figure | 45 % | **MISS.** None. |
| h3 | four or more human figures | 20 % | **MISS.** |
| h4 | a bar counter legible at f64 | 70 % | **MISS.** |
| i1 | `estimate_credits` 0, GPU time only | 95 % | **HIT.** 0. |
| i2 | Gate B pixel-identical decode | 90 % | **HIT.** |
| i3 | run completes without a gate firing after submission | 85 % | **HIT.** No gate fired after submission — which is §4's point. |

**The scoreboard's own lesson.** Of twenty clauses, seven are unreadable, and two "hits"
(e5, f2) are hits on instruments measuring nothing. The prediction set was built to
discriminate between *camera held* and *camera free*; the run landed outside the space both
branches assumed, which no degree in the table could have expressed. Nothing here should be
read as evidence for or against the camera embedding as a lever — **it has not yet been
tested on weights that can receive it.**

## 9. The meters

| | |
|---|---|
| `estimate_credits` | 0 (all-OSS graph; the E08 §12 pattern holds) |
| generations spent | **2 of 3** — wave 1's probe, wave 2's probe |
| reserves remaining | **1** (seed 2026081233, unspent) |
| GPU / queue time | metered by the provider; to the ledger when the window resolves |
| `prompt_id` | `514a4a57-5b8d-4de7-9f18-a0d12367795e` |
| job status | `completed` / `succeeded`, no warnings |

## 10. What this seat did not do

- **Did not spend the remaining reserve.** A weights mismatch is a named cause and the spec
  authorises the second reserve on one — but a corrected run changes the model, which is a
  new licence row (§7), a break in the "weights held constant against wave 1" pin (§3), and
  a change to what the arm is. That is a design decision.
- **Did not edit `docs/license-map.md`.**
- **Did not edit wave 1's builder.** Its `CONTROL_CLASSES` ban on `WanCameraImageToVideo`
  still stands on the run it governed.
- **Did not judge the output.** The description in §5 is what was seen at full size.

## 11. Artifacts

```
outputs/E11/w2/route/E11-w2-camera-i2v.api.json        the graph, as built
outputs/E11/w2/route/E11-w2-camera-i2v.saved.json      the graph, as the cloud converted it
outputs/E11/w2/route/E11-w2-payload-record.json        provenance, prompt surgery, guidance
outputs/E11/w2/route/E11-w2-saved-admission.json       saved-file gate evidence
outputs/E11/w2/route/E11-w2-camera-widget-order.json   the empirical second reading
outputs/E11/w2/probe/lossless/00000-00064.png          65 frames, the measurement source
outputs/E11/w2/probe/gate_b_evidence.json              Gate B
outputs/E11/w2/measure/E11-w2-clip.json                measurements, w2 beside w1
outputs/E11/w2/sheets/E11-w2-collapse-strip.png        f0 f1 f2 f4 f64, native scale
outputs/E11/w2/sheets/E11-w2-zoom-f0-f1.png            head and hand, f0 vs f1, 3x
outputs/E11/w2/review/E11-w2-vs-w1-truetempo.webp      A/B against wave 1, true tempo
outputs/E11/w2/review/half-speed/                      0.5x / 8 fps pair + stills
```

Tests riding this arc: 46 new (11 route-gate, 30 builder, 5 saved-graph). Suite **790
passed, 46 skipped** against a 749/46 baseline.

## 12. The open question this run hands back

The camera lever has **not** been tested. What was tested, unintentionally, is what happens
when a conditioning signal is delivered to weights with no channel for it — and the answer
is that the gate suite does not notice, the job succeeds, and the frames come back empty of
subject after one frame.

Whether the next step is the corrected camera run on the Fun-Camera experts, a return to the
wave-1 route with the prompt surgery alone (which would isolate the prompt lever the camera
run confounded), or something else, is not this seat's to choose.
