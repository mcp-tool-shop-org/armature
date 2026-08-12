# E11 — report: the GLB hands the model one frame, and the model keeps him and replaces the world

**Seat: executor**, branch `E11-nocontrol`, worktree `E:\AI\armature-E11`, from `main` at
`309664a`. **One generation** (`prompt_id` `ecedbe1c-8658-4119-8151-cfa693db1c50`, seed
`2026081231`). Reserve seeds `2026081232` and `2026081233` **unspent**. **No gate fired.**

> **This is the WAVE 1 report.** Wave 2 ran 2026-08-12 on reserve seed `2026081232` and has
> its own report: [E11-w2-report.md](E11-w2-report.md). Its one-line summary, so no reader
> of this document carries a stale picture — wave 2's camera embedding was delivered to the
> plain I2V experts rather than to the Fun-Camera weights that exist for it, every gate
> passed, and the frames contain no subject after f1. **Nothing in the wave-1 record below
> is changed or superseded by that run**; the reserve count above is (one spent, one left).

This report carries measurements, gate states and predictions against outcomes. It contains
no judgement of whether the footage is good; the Director's eye is the verifier of record
and the advisor rules on what the measurements mean.

**Look first:** the two-pipeline sheet this experiment exists for —
`outputs/E11/review/E11-vs-E08-truetempo.webp`, E08's driven probe beside E11's no-control
probe, same prompt, both 65 frames at their own native 16 fps so neither arm is resampled or
retimed. Then `outputs/E11/sheets/E11-gate0.png` at full size, then the 0.50× / 8 fps clip
from `lossless/`, then the face and hand strips.

**The two things this seat can state without judging them.** With no driving signal, no
reference image and no clip-vision embedding, the figure's identity features — the bald
head, the drawn brow, eye, nose and mouth, the mitten hands, the visible ball joints —
**are present in every frame inspected at full size, including the last.** And the world
around him is **gone by frame 8**: the authored grey studio is replaced by a bar with a lit
counter, bottles, a wooden floor and at least four other people, none of which the start
frame contained. Correlation between the final frame and the authored start frame is
**−0.198**.

**Read under E10's two-seed rule.** This is one seed. Nothing here about the scene is a
property of the route; it is one observation.

---

## 1. Premises, re-verified at use

| # | premise | spec status | what re-verification found |
|---|---|---|---|
| 1 | Wan 2.2 I2V-A14B weights, Apache | MEASURED (map row 2026-08-12) | Confirmed at use. The graph loads the **Comfy-Org repack** pair `wan2.2_i2v_{high,low}_noise_14B_fp8_scaled.safetensors`, covered by the map's 2026-08-11 repack ruling. The catalog also serves Kijai `Wan2_2-I2V-A14B-*_KJ` variants, which the map has no row for; they are not used. |
| 2 | The I2V conditioning node's socket schema | **ASSUMED — verify via `get_node` before building** | **VERIFIED before a single node was written.** `WanImageToVideo` takes `positive, negative, vae, width, height, length, batch_size` required and **two** optionals — `clip_vision_output` and `start_image`. It emits `CONDITIONING, CONDITIONING, LATENT`. Not six optionals, not seven: two. |
| 3 | The start frame, rendered from the GLB at 832×480 | **COMMISSION** | Delivered (§2). Looked at at full size and at 4× on the head, both hands and the feet **before** it uploaded. |
| 4 | 832×480×65 legal on this route | **ASSUMED — verify** | Confirmed three ways that agree: the shared `wan_2.1_vae` (the same transfer the `wan-fun-control` row records), the node's own declared defaults 832×480×81, and the reference workflow's 640×640×81 latent. **The schema itself enforces neither constraint** — it declares width/height/length as plain INT, min 16/16/1, max 16384. §5. |
| 5 | Billing 0 credits / GPU-hours metered | MEASURED (E08/E10 pattern) | Confirmed. `estimate_credits` re-run on the exact graph: **0 credits, no paid API nodes.** §11. |
| 6 | Comparability to E08's probe | **BOUNDED HONESTLY in the spec** | The bound is real and is now enumerated as nine differences in the payload record (`delta_from_E08`) rather than left as a sentence. §6. |

---

## 2. The commission — the GLB becomes the image

`tools/render_start_frame.py` + `armature_core/startframe.py`, tests riding the commit.

**What was rendered.** Frame 0 of the E09 A3 baseline dance — the same instant E08's clip
begins at — from `E:\AI\armature-E09\outputs\E09\b2-a3-lifted\performer_dance_ema.glb`,
sha256 `cd4e2f6ee85ef536130cebe27fe2282f1bb1eba02a6c410d999e4f2351ea0c17`, which **matches
the value E09 recorded and E08 re-verified**. The pose was chosen for comparability before
anything was rendered, and was not swapped after looking at it.

**Staging reused verbatim from `render_performer` (E09/E10):** the same 0.16/0.16/0.18
world, the same two suns at 3.2 and 1.1, EEVEE, Standard view transform, a ground plane, and
the banked camera convention — azimuth 225°, elevation 6°, 50 mm on a 36 mm sensor.

**What is different, and it is a decision:** the frame is authored at **832×480, the
generation's own size**, and the figure is composed to fill 0.90 of the frame height rather
than E08's 0.70 over a whole performance. E08 measured what a mismatched reference costs on
the other route — `WanAnimateToVideo` centre-cropped its 352×1024 twin to 204 of 1024 rows —
and E08's own report named the fix this implements. Nothing resamples this frame anywhere.

| quantity | value |
|---|---|
| resolution | 832 × 480, native |
| figure height fraction, achieved | **0.9024** (requested 0.90) |
| silhouette extent, px (unclipped) | x 257.5 → 575.2, y 23.9 → 457.0 |
| border margins, px | left 257.5 · right 255.8 · **top 23.9** · **bottom 22.0** (Gate WHOLE floor: 8 px) |
| subject + shadow, fraction of frame differing from the empty plate | 0.0802 |
| camera | target `[-0.0153, -0.0306, -0.0713]`, radius **2.4808**, position `[-1.7598, -1.7751, 0.1880]`, az 225° / el 6° / 50 mm / 36 mm |
| framing cloud | 114,992 evaluated vertices; 1,500 solved against; Gate WHOLE run on all 114,992 |
| Blender | 5.2.0 LTS |
| pose signature (evaluated geometry) | `94fbdefd9cc311d2…` |
| sha256 | `9c3c026fbd05dc08cd3d523a61e608b5…` |
| server name after upload | `adcab015d182b1eaf590ac5626174840fa5719afd97cda6bc0dcc31dedc3e9dd.png` |

**Read off the frame at full size, before upload.** A terracotta jointed clay mannequin,
whole body in frame, mid-stride with both arms out: the screen-left arm bent down with the
mitten hand closed into a loop, the screen-right arm raised out with a flat mitten hand.
Bald head turned to screen-right in three-quarter, with a drawn brow, a lidded eye, an ear,
a long nose and a mouth line. Ball joints visible at shoulders, elbows, wrists, hips, knees
and ankles. **Pale streak artifacts** on the crown, the neck and upper chest, both forearms
and the screen-right hand — texture-projection artifacts the asset carries, whose repair is
the brush pass named on E08's ledger and out of scope here. Background: a grey backdrop
above a horizon at row 155 (31 % down the frame), a near-white ground plane below it, the
figure's shadow falling to screen-left.

**The consequence of that staging, written into the tool's own provenance before the run:**
the start frame shows **a grey studio, not a bar**. On this route the start frame is the
model's only picture of the world, so the scene clause of the prompt is asking the model to
*replace* what it can see rather than to fill a silence. §9 records what that turned out to
be worth.

### Gate WHOLE — the andon this route needed and did not have

`framing.solve_camera` reports `in_frame`, and it is not enough here: it is solved over a
**landmark** cloud plus the rest bbox's half-extents, and `render_performer.body_cloud` says
in its own docstring that landmarks under-report the silhouette. Under-reporting costs a few
pixels of margin on a 1080p detector plate. It is not harmless when the frame **is** the
conditioning image: a start frame with a shaved skull or a cropped foot hands the model a
cropped character for sixty-five frames, and nothing downstream fires — the file is the
right size, the render is non-empty, the coverage fraction is healthy, and Gate L is about
frame legality, not about what is in the frame.

So the composition is solved on the silhouette (a deterministic reduction that carries every
per-axis extreme across it) and then checked on the silhouette **unclipped**. Unclipped is
the load-bearing word: `blender_scene.projected_bbox_px` drops every vertex outside the
frame before taking bounds, so a figure whose arm is 200 px off the left edge comes back
with `x0 = 0`, snug and innocent. A test builds exactly that case — a landmark framing that
reports `in_frame` over a silhouette that is over the top of the frame — and requires the
gate to fire.

---

## 3. The route, and the third instance of trap #3

The trajectory is **read off** a documented workflow, not solved and not carried over from
the Animate route. Both pinned revisions of `Comfy-Org/workflow_templates` (MIT)
`templates/video_wan2_2_14B_i2v.json` were fetched 2026-08-12 and banked with their sha256;
their wiring was traced through the file's own `links` array **in code**, not read off node
order.

| | `5d6089c4250f` | `dcc00d29d79d` | `main` |
|---|---|---|---|
| nodes | 17, **no LoRA of any kind** | 37; non-distilled branch present but `mode = 4` (bypassed) | 35, of which **only 5 are top level** |
| steps / split | 20 / at 10 | 20 / at 10 (bypassed branch) | 4 / at 2 |
| shift · cfg | 8.0 · 3.5 | 8.0 · 3.5 (bypassed branch) | 5.0 · 1.0 |
| LoRAs | none | `wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise` @ 1.0, live | the same pair @ 1.0, live |
| seed | — | high-noise sampler `randomize` | high-noise sampler `randomize` |

**`main` is not runnable under this gate**, and it is the third measured instance of the
pattern the licence map records as trap #3 — after the served Animate template's detector
tier and the served T2V template's 4-step trajectory. It presents five nodes and hides
thirty inside a subgraph blueprint; what is hidden is the map's EXCLUDED lightx2v tier at
strength 1.0 on a randomizing seed. **A served template is a reference, never a route.**

The values used are `5d6089c4250f`'s, cross-confirmed against the bypassed non-distilled
branch at `dcc00d29d79d`: **steps 20, split at step 10, shift 8.0, cfg 3.5, euler, simple,
fps 16.** A test reads the banked file and asserts every one of them, rather than trusting
the note that cites it — E09's citation check fired on exactly this class of claim.

Two further things measured on the cited revision and reproduced here: `clip_vision_output`
is **unconnected** there and is unconnected here, and its negative prompt is
**byte-identical** to Wan's own `shared_config.sample_neg_prompt`, which is the string E08
used and which this graph reads from the same banked file (sha256 `3ae102e029d4d0e3…`,
matching E08's record exactly).

### Gate PIN — "pinned verbatim" made a measurement

The positive and negative are rebuilt from their own sources through **E08's own code**
(`build_animate_payload.identity_clause` / `read_negative` — the twin JSON re-read, the
negative re-parsed) and then compared **byte for byte against E08's committed payload
record**, which the builder requires as an input. Both match:

```
positive  sha256 ff25d2c562081f629c0fcc9eae32cf94810d6e9204a8e7a7ed15c74f68534702  (553 chars)
negative  sha256 ce96e0324e4b54ce4b6e867f669ca520952e1a34cc116543516b1897f0d3c47e  (137 chars)
```

The A/B's load-bearing claim is "same prompt, different route". It is now checked in a tool
that halts on one character of drift, with a test that drifts it by one character.

### The defining property, checked rather than trusted

`verify_topology` refuses the graph if it carries **any** control-capable conditioning class
(`WanVaceToVideo`, `WanAnimateToVideo`, `Wan22FunControlToVideo`, `WanCameraImageToVideo`,
`WanFirstLastFrameToVideo`, the ControlNet apply classes …), **any** second uploaded image,
a wired `clip_vision_output`, a sampler fed straight from a text encode instead of from the
conditioning node, or an expert handover where one sampler's `end_at_step` is not the
other's `start_at_step`. E11's whole subject is a negative — nothing conditions the
generation but one image and one prompt — and a negative decays silently: a control node
added later still generates a video, still passes Gate L, S and ROUTE, and still costs the
same. Eleven fixtures build each violation and show it refused.

---

## 4. The instrument work this route forced

**`route_gates.LATENT_NODES` gains `WanImageToVideo`** (and `WanFirstLastFrameToVideo`,
which is the same object one socket wider) — **the day the first of them is used**, which
is what that table's own warning asks for. The node sizes its own latent, so an I2V graph
contains no `Empty*LatentVideo` at all; without the entry Gate L examines zero latents and
reports the graph legal, which is the E08 defect exactly. A test asks the gate the question
with **no frame supplied** and requires it to find the latent; a companion pops the entry
back out and requires `INDETERMINATE`.

**`gates.py` gains the `wan-i2v` profile**, and its provenance says DERIVED rather than
borrowing the sibling row's wording: unlike `WanAnimateToVideo`, this node's schema carries
no step fields and would enforce nothing. §5 has the three readings that agree.

**`gate_saved_graph.WIDGET_INDEX` gains `WanImageToVideo` with four widgets, not six.** A
row copied from the Animate node would have compared `batch_size` against nothing.

**`fetch_run.py`'s node map became a flag.** It was a module constant naming E02's tap ids,
so pointing the tool at any later dump sorted every frame into the fallback branch and
printed a plausible count — E10's closing lesson in a different tool. A malformed map now
halts rather than falling back to E02's.

**`gate_b_frames.py` gained `--source-label` / `--decoded-label`.** Its evidence strings
were `"N local stick frames"` / `"N server batchprobe frames"`; on this route the compared
artifact is one **start frame**, and evidence that called it a stick frame would be a label
asserting something untrue.

**A tool that was NOT reused, and why it is a finding.** `make_gate0_sheet.py` is the
generically-named sheet tool, and its provenance panel carries E02-era **literals**:
`Wan 2.1 VACE 14B fp16`, `uni_pc / simple / 30 steps / cfg 6`, `distinct imgs … of 33`, and
a bridge-fidelity note about a control channel. Pointed at this run it would have printed
E02's sampler beside E11's seed — a report containing a placeholder shaped like evidence.
`make_startframe_sheet.py` was written instead, with every provenance line read from the
run's own payload record, `NOT RECORDED` for anything the record does not carry, and a
parameterised test asserting that none of those eight literals can appear.

---

## 5. Gates

| gate | where | state |
|---|---|---|
| **fps ordering** | start-frame renderer | PASS — rate pinned on an empty scene before the import |
| **POSE** | start-frame renderer | PASS — frame 0 maps to scene frame 1, inside the action's keyed range |
| **WHOLE** | start-frame renderer | PASS — whole silhouette in frame, smallest margin **22.0 px**, 0 points behind the camera, measured unclipped over every evaluated vertex |
| **COVERAGE** | start-frame renderer | PASS — subject + shadow cover 0.0802 of the frame against an empty plate |
| **PIN** | payload builder | PASS — positive and negative byte-identical to E08's submitted strings |
| **L** | payload builder + ROUTE | PASS — 832×480×65 on the `wan-i2v` profile: /16, /16, 4n+1, ≤ 81 |
| **S** | payload builder + ROUTE | PASS — seed `2026081231`, drawn from `specs/E11-seeds.json`, committed at `accf74a` **before** the first submission |
| **ROUTE** | built API graph | PASS — 4 weight files, 2 seeds both pinned, 1 of 1 latent checkable, 2 frames checked, verdict **PROVEN** |
| **ROUTE / S / L** | saved projection | PASS — **42 pinned values** and **22 links** compared; `50.clip_vision_output` and `80.audio` empty in both; 1 noise-bearing seed, pinned, registered |
| **B (count)** | the run | PASS — 1 in, 1 back |
| **B (pixels)** | the run | PASS — **pixel-identical, per channel** |
| **ceiling** | generation count | **1 of 3 spent** |
| watchdog | before the local render | verified alive at session start (restarted from a stale heartbeat) and before the Blender work |

**Gate B, stated for what it proves here.** On the driven route Gate B guards a 65-frame
pack. Here the uploaded artifact is one image, and it is the *entire* image conditioning of
the generation — so the check is narrower and more load-bearing at once: the bytes the model
saw at frame 0 are this seat's rendered bytes, as evidence rather than as an assertion.

**One capture is weaker than it looks, disclosed.** The saved projection was captured by
**transcribing `get_saved_workflow`'s result into a file**, not by a byte-stream download —
no download route for a saved workflow is exposed through this session's tools. The
round-trip gate therefore compares the built graph against a transcription of what the cloud
holds. A transcription slip would almost certainly *fire* the gate rather than pass it, but
the honest statement is that this capture is one degree weaker than E08's and E10's uploads,
which were compared against returned bytes.

---

## 6. What differs from E08's arm, enumerated

The spec bounds the comparison as a **route comparison, not a single-variable one**. That
sentence in numbers, from the payload record:

| | E08 | E11 |
|---|---|---|
| conditioning node | `WanAnimateToVideo` | `WanImageToVideo` |
| diffusion weights | `wan2.2_animate_14B_bf16` (one expert) | `wan2.2_i2v_{high,low}_noise_14B_fp8_scaled` (two experts, MoE) |
| text encoder | `umt5_xxl_fp16` | `umt5_xxl_fp8_e4m3fn_scaled` (the I2V reference workflow's own) |
| driving signal | 65 AAPose-20 stick frames on `pose_video` | **none — this is the experiment** |
| identity conditioning | letterboxed twin on `reference_image` | the start frame itself; this node has no reference socket |
| sampler | 1 × `KSampler`, uni_pc/simple, 20 steps, cfg 6.0 | 2 × `KSamplerAdvanced`, euler/simple, 20 steps split at 10, cfg 3.5 |
| shift | 8.0 (inherited; undocumented for Animate) | 8.0 (read off the I2V reference workflow) |
| prompt / negative | — | **byte-identical, checked in-tool** |
| frame | 832×480×65 @ 16 fps | 832×480×65 @ 16 fps |

65 @ 16 fps was held deliberately. E10's standing direction — *the more fps the better* — is
a ruling about **driving density** on the skeletal route; there is no driving signal here, so
it has nothing to move, and a different length would have put a third variable into a
comparison that already spans two models.

---

## 7. What came back, measured

67 outputs: 1 video, 1 start-frame probe, 65 lossless frames. **65 of 65 output frames are
distinct.** All numbers below are computed by one instrument (`tools/measure_clip.py` +
`armature_core/clipstats.py`, 13 tests) over **both** arms' lossless frames, so the E08
column is a fresh measurement rather than a figure quoted from its report.

| statistic | E08 (driven) | E11 (no control) |
|---|---|---|
| frames · distinct | 65 · 65 | 65 · 65 |
| mean abs frame-to-frame delta — min | 2.551 | **1.753** |
| — median | 3.917 | **5.282** |
| — mean | 4.027 | 6.787 |
| — p90 | 4.842 | 12.907 |
| — max | 6.160 | **26.004** |
| mean luminance over the clip | 105.60 | **59.52** |
| luminance range across the clip | 52.56 | **144.94** |
| frame-to-frame \|Δ luma\| — median | 0.870 | **0.210** |
| — p90 | 1.541 | 9.232 |
| — max | 2.737 | 24.069 |
| \|Δ luma\| by quarter | 1.380 / 0.953 / 0.856 / 0.092 | **7.003 / 0.175 / 0.994 / 0.074** |
| mean abs difference from own frame 0, final frame | 66.82 | **153.24** |
| correlation with own frame 0, final frame | **+0.553** | **−0.198** |

**A convention note, because a third report will otherwise re-derive it.** E08's report
quotes its median frame delta as **3.95**; that is `sorted(deltas)[n//2]`, which on 64 values
takes the upper middle. `numpy.median`, which averages the two middle values, gives
**3.917**. Both conventions are computed here and they differ by 0.03; the tables above use
numpy's throughout, on both arms.

**The exposure reading is the one that inverts.** E11's first quarter swings 8× harder than
E08's — that is the scene being replaced — and its remaining three quarters are **quieter
than E08's**: 0.175 / 0.994 / 0.074 against 0.953 / 0.856 / 0.092. Set beside E10's median
of 9.05 on the driven route, E11's 0.210 over the whole clip is two orders of magnitude
smaller. This seat measured that; it does not claim a cause.

### The camera diagnostic, and what it can and cannot separate

`similarity_to_first` is **conflated by construction** — it moves with the subject, the
camera, the exposure and the scene alike and separates none of them. It is quoted beside
`horizon_row`, which is the one measurement here a moving subject cannot move: a static
camera over a dancing figure leaves the room's strongest horizontal edge on one row (the
figure occludes a few columns and the median across the rest does not care). A test builds
exactly that case and requires the row to hold constant while every whole-image statistic
changes.

| frame | correlation with frame 0 | horizon row | agreement |
|---|---|---|---|
| 0 | +1.0000 | **155** | 0.672 |
| 1 | — | **198** | 0.751 |
| 2 | — | **258** | 0.612 |
| 3 | — | **292** | 0.549 |
| 4 | +0.5347 | **NOT FOUND** | 0.101 |
| 8 | +0.1417 | NOT FOUND | 0.345 |
| 16 | −0.0056 | NOT FOUND | — |
| 32 | −0.0385 | NOT FOUND | — |
| 48 | −0.1706 | NOT FOUND | — |
| 64 | −0.1984 | NOT FOUND | 0.364 |

Correlation first falls below 0.5 at **frame 6** and below zero at **frame 16**; the minimum
is −0.1986 at frame 63. It is **not monotone** — there are small recoveries — but it never
returns near its early values. Mean absolute difference plateaus near 130 by frame 12 and
creeps to 153.5 by frame 62.

The horizon is found on **4 of 65 frames** and then never again. Looking at those four
frames at full size says what the number cannot: the row moving 155 → 292 in three frames is
**the grey backdrop's lower edge sliding down the frame as it dissolves**, not a camera tilt
— at f2 warm lamp shapes have appeared above the backdrop, and at f4 the backdrop reads as a
translucent band with a bar and human figures visible through it. After f4 the columns stop
agreeing on any single horizontal edge because the room no longer has one.

**On E08 the same instrument reports NOT FOUND on all 65 frames**, and that is correct
behaviour, not a failure: E08's background is painted from a uniform mid-grey plane and has
no authored horizon to find. Recorded so nobody reads the zero as a defect.

---

## 8. What came back, looked at

Nine frames read at **full size** — 0, 2, 4, 8, 24, 32, 48, 56, 64 — plus six 3×-NEAREST
crops of the head (f0, 8, 16, 32, 48, 64) and five of the screen-left hand (f0, 16, 32, 48,
64), with every crop box printed on the strip and written to a sidecar. **No judgement of
quality is offered or implied.**

**The arc.**

- **f0** — the start frame, VAE round-tripped: grey backdrop over a pale floor, horizon at
  row 155, terracotta jointed mannequin whole in frame, his shadow to screen-left.
- **f2** — the same studio; the backdrop's lower edge has descended to row 258; warm lamp
  shapes have appeared along the top edge.
- **f4** — the grey backdrop reads as a translucent band dissolving. Behind and above it:
  warm lamps, a back-bar, and human figures. The pale floor persists below.
- **f8** — a bar is fully present behind him: warm under-counter strip lighting, bottles on
  shelves, a woman leaning at the counter to the left, two standing figures to the right.
  The pale studio floor is still in the foreground.
- **f24** — the whole scene is the bar. A warm wooden floor, three figures at the right, one
  at the back left. The mannequin is whole in frame.
- **f32** — a dark bar with a polished floor carrying his reflection. His feet are at and
  below the bottom border.
- **f48 · f56 · f64** — the framing has pushed in further; he is cut below the knee and then
  at the shin; the head is roughly twice its f0 size on screen.

**The figure, whole in frame at f0, f8, f16 and f24; cut by the bottom border at f32, f48,
f56 and f64.** The onset lies between f24 and f32 and was not narrowed further.

**The head, at 3× across the clip.** Bald, with a drawn brow, a lidded eye, a long nose, a
mouth line and an ear — **present at every one of the six sampled frames, including the
last.** What changes: the surface reads matte sculpted clay at f0 and f8 and smoother, more
glazed, from f32 on; the brow reads heavier and more graphic by f48 and f64; and the overall
hue moves from terracotta toward a paler warm cream, in a room whose light is warm.

**The hands.** A mitten paddle or a closed loop at every sampled frame. **No frame inspected
resolves fingers.** The character has no fingers, so the absence is not a departure from him.

**The ball joints.** Visible at shoulders, elbows, hips and knees at f0, f8, f16, f24, f32
and f48. At f64 the knees and hips are outside the frame.

**The start frame's pale streak artifacts** — crown, neck and upper chest, both forearms —
persist as pale streaks on the torso and arms through f64.

---

## 9. Predictions versus outcomes

Registered blind at `fefab12`, committed before the submission and before any E11 output
existed. Blindness is disclosed in the predictions file itself: this seat had seen the start
frame at full size (the law requires looking before an upload) and both prior reports with
their outcomes, and had seen no E11 output of any kind.

| clause | predicted | outcome |
|---|---|---|
| **a1** terracotta / bald jointed-mannequin read survives to the final frame — 70 % | survives | **SPLIT, and predicted as one clause.** The bald jointed-mannequin read survives plainly; the *terracotta* hue reads paler and glazier from f32. Two properties in one clause — the same error E08's report made at the elbows and knees, one level finer than it was applied. |
| **a2** no visible drift in the first 16 frames — 80 % | none | **HIT.** Head, face, mitten hands and ball joints all present through f16. |
| **a3** visible drift somewhere in the clip — 65 % | drift | **MISS.** Under the definition registered before the fact, no named feature was absent or replaced while it remained in frame. The definition is also **partly untestable in the last quarter**, because the push-in removed two of the four named features from the frame — a collision the definition did not anticipate and this seat did not foresee. |
| **a4** the face still reads as a face at the final frame — 50 % | maybe | **HIT.** Brow, eye, nose and mouth at f64 at 3×. |
| **a5** knee and hip ball joints survive to the final frame — 60 % | survive | **NOT TESTABLE at the final frame** — cropped out. Present at f48, the last frame in which they are in frame. |
| **a6** no frame resolves fingers — 85 % | none | **HIT** across the crops inspected. |
| **b1** limbs visibly move — 80 % | yes | **HIT.** 65 distinct frames; arms and legs in visibly different positions across every sampled frame. |
| **b2** E11's median frame delta LOWER than E08's — 55 % | lower | **MISS.** 5.282 against 3.917 — E11 moves more per frame, not less. |
| **b3** \|Δ luma\| median nearer E08's than E10's — 60 % | nearer E08 | **HIT**, and past it: 0.210 against E08's 0.870 and E10's 9.05. |
| **b4** at least one frame shows a limb in a shape the rig could not make — 45 % | maybe | **NOT SUPPORTED, coverage stated.** Not observed in the nine frames read at full size or the eleven crops. All 65 frames were not inspected for this, so it is unobserved rather than absent. |
| **c1** a recognisable bar in the final frame — 35 % | probably not | **MISS, badly.** The bar is complete from f8 — back-bar shelving, bottles, lit counter, floor — and present in the final frame. |
| **c2** visibly warmer at the end than at f0 — 55 % | warmer | **HIT.** |
| **c3** the studio horizon still visible in the final frame — 60 % | visible | **MISS.** Lost after f3, NOT FOUND at f64, and gone at full size. |
| **c4** other people appear — 15 % | probably not | **MISS, and by the widest margin of the run.** At least four human figures from f8 onward. |
| **d1** the final framing is not the start frame's — 65 % | moved | **HIT.** A large push-in. |
| **d2** similarity declines and does not recover — 70 % | declines | **HIT** on the substance: +1.000 → −0.198, never returning near its early values. **Not monotone**, which the clause did not claim but a reader might assume. |
| **d3** some part of the figure cut by the border — 40 % | maybe | **HIT.** Whole through f24, cut from f32 on. |
| **o1** 65 lossless frames, all distinct — 85 % | yes | **HIT.** |
| **o2** Gate B pixel-identical — 85 % | yes | **HIT.** |
| **o3** no gate fires — 75 % | none | **HIT.** |

**The stated fail condition did not fire.** The clip is not a near-still hold: 65 distinct
frames, limbs travelling well past their own width.

**The pattern in my own misses, and it is one pattern.** Every scene clause missed, and all
four missed in the same direction. The reasoning registered in the predictions file was that
an I2V generation begins from its start frame *literally*, so a prompt asking for a bar over
an image of a grey studio is asking the model to replace what it can see, and that this
would cost the scene clause heavily. The premise is right and the conclusion was backwards:
**the start frame anchored the subject and was discarded as a constraint on the world inside
about eight frames.** The two things this seat weighted are the two that inverted — I
predicted the character would be the fragile part and the room the sticky part, and the run
did the opposite on both.

---

## 10. Deliverables

| artifact | what it is |
|---|---|
| `outputs/E11/review/E11-vs-E08-truetempo.webp` | **the two-pipeline sheet the experiment exists for** — E08's driven probe beside E11's no-control probe, same prompt, 65 composite frames, 4.062 s. Both arms are 65 frames at 16 fps, so **neither is resampled or retimed** and the union timeline is exact |
| `outputs/E11/review/half-speed/review_0.50x_8fps.webp` | the 0.50× / 8 fps review clip from `lossless/`, plus 28 stills |
| `outputs/E11/sheets/E11-gate0.png` | Gate 0: start frame \| output at f0/4/8/16/32/48/56/64 \| provenance, every provenance line from the run's own record |
| `outputs/E11/sheets/E11-face.png` | the head at 3× NEAREST at f0/8/16/32/48/64, crop boxes printed and in a sidecar |
| `outputs/E11/sheets/E11-hands.png` | the screen-left hand at 3× at f0/16/32/48/64, same |
| `outputs/E11/startframe/start_frame.png` + `zoom_{head,lhand,rhand,feet}.png` | the authored conditioning image and the 4× crops looked at before it uploaded |
| `outputs/E11/measure/E11-clip.json` | every number in §7, both arms, one instrument |

---

## 11. Both meters

**`estimate_credits` = 0 credits — no paid API nodes**, re-confirmed before submission on
the graph that was submitted. On an all-OSS route this is 0 by construction, so the ceiling
was enforced by **counting generations**: **1 of 3 spent**, reserves `2026081232` and
`2026081233` unspent.

**GPU hours.** Baseline recorded before submission: **$17.787831** for
2026-07-12T11:00Z → 2026-08-12T11:00Z. E11's run landed after 11:00Z and its bucket **has
not been invoiced**: re-queried after completion, the window and the total are unchanged.
E11's GPU cost is **NOT YET RESOLVED**; the number to read later is the delta against
$17.787831.

**E10's open ledger item can be closed on the same reading E10 used to close E08's.** E10's
report recorded $17.430281 for the window ending 09:00Z. The difference to the pre-E11
baseline is $0.357550, exactly the new 10:00–11:00Z bucket — so **E10's probe cost ≈ $0.36
in GPU hours**, with E10's own caveat carried forward: the two windows do not start at the
same hour and nothing else confirms the attribution.

---

## 12. Artifacts

| artifact | sha256 (first 32) |
|---|---|
| the start frame, as rendered and as uploaded | `9c3c026fbd05dc08cd3d523a61e608b5` |
| the empty plate (COVERAGE's baseline) | `d6ffd7ae453b11552aff86fbcaa663d6` |
| start-frame provenance (camera, gates, hashes) | `5338047facbbf1d2a2c86ade10f846bc` |
| the graph, as built | `af317433252507ed12dfaed15b7d031e` |
| the payload record | `ba91fcdbcd5b616111f73534b028e89a` |
| the saved projection, as transcribed from the cloud | `2a3122345cd6094f732b472de5ab17f4` |
| saved-graph admission (42 values + 22 links + gates) | `506bafdc0508acc2c67eb9794569295c` |
| i2v template @ `5d6089c4250f` (the cited revision) | `8fbab01d086df5f379f9ef9efea229f5` |
| i2v template @ `dcc00d29d79d` | `cccecf52ed81c9175c2d90b7981c6013` |
| i2v template @ `main` (the excluded one) | `455337c85e3fb0c7da9b2e3e6408f02f` |
| the negative's source, banked | `3ae102e029d4d0e3436ebbaa9f8fd32c` |
| Gate B evidence (1/1, per channel) | `6e233aba8c26e4c861f31442eeca7c97` |
| clip measurements, both arms | `3f780b8696f5690bf58f30528b9f603f` |
| **the Gate 0 sheet** | `9cc390108905af49c60369224d8190ef` |
| the head strip | `ced38a9b4a7ef28bfc0595605fe76ff7` |
| the hand strip | `23a2ab500022718de66f0fd298f85802` |
| **the two-pipeline A/B, lossless** | `40edae43cb717d657a648a72b3d29983` |
| the 0.50× review clip, lossless | `27f24e1bff41654dbbad35f86658ed5a` |
| 65 lossless frames | per-frame in `outputs/E11/probe/lossless/` |

New in the tree: `armature_core/startframe.py`, `armature_core/clipstats.py`,
`render_start_frame.py`, `build_i2v_payload.py`, `measure_clip.py`,
`make_startframe_sheet.py`, `make_crop_strip.py`, `specs/E11-seeds.json`, the
`route_gates.LATENT_NODES` and `gates.GENERATOR_PROFILES` additions,
`gate_saved_graph`'s `WanImageToVideo` row, `fetch_run`'s `--node-map`, and
`gate_b_frames`'s label flags.

**Suite: 741 passed, 46 skipped.** The comparable baseline is `main` at `d96bc95` measured
in a **fresh worktree with no `outputs/`**: **656 passed, 46 skipped**. Suite counts are only
comparable between trees carrying the same banked artifacts, since `outputs/` is git-ignored
and some tests require what is in it — E10's caveat, carried.

---

## 13. Compensators

| act | compensator | state |
|---|---|---|
| the probe generation `ecedbe1c…` | **none exists** — spent GPU time has no undo | 1 of 3; reserves `2026081232` / `2026081233` unspent |
| uploaded start frame `adcab015…dedc3e9dd.png` | delete server-side (Comfy Cloud inputs) | **present; owner executor** |
| saved cloud workflow `armature-E11-probe-i2v` (`cc9aca96-f3b3-4154-9c33-9b6c36c1af09`) | delete server-side | present; owner executor |
| downloaded outputs under `outputs/E11/` | delete the directories | written; owner executor |
| the temporary baseline worktree `E:\AI\armature-E11-mainbase` | `git worktree remove --force` | **already removed** |
| worktree + branch `E11-nocontrol` | `git worktree remove` + branch delete | owner advisor, after the ruling |

**Every uploaded artifact is listed above with its named undo.** One upload, one saved
workflow, one generation. No publishes, no releases, no external posts, no writes to the
memory store.

---

## 14. For the advisor

Measured here, with no authority to rule on any of it.

1. **The start frame anchors the subject and does not anchor the world.** Identity features
   survived to the last frame with nothing holding shape; the authored room was gone in
   about eight frames and replaced with a bar containing four people the prompt asked for
   and the image did not contain. Both directions are the opposite of what the registered
   predictions expected. Under E10's two-seed rule this is one observation, not a route
   property, and a second seed is what would make it one.
2. **The crowd clause resolved here where it did not on the other route.** E08 asked for
   people and got none; E10 got one unasked; E11 got at least four, with the **same
   byte-identical negative** that names 杂乱的背景 and 背景人很多. Three arms, three
   answers, one negative. Nothing here attributes the difference.
3. **A large uncommanded push-in is this route's measured price**, and it crops the figure
   from about frame 28. `main` moved to `d96bc95` while this branch was open, and consult
   #7's shelf already carries **camera embedding** (core nodes; Fun-Camera weights fetched
   Apache) — which is the lever this measurement asks for. This branch predates those two
   commits and does not carry them.
4. **`make_gate0_sheet.py` still carries E02-era literals** in its provenance panel and is
   the generically-named sheet tool. Not fixed here (out of scope); named so it is fixed
   deliberately rather than discovered by a fourth experiment.
5. **Gate WHOLE is doctrine-shaped, not E11-shaped.** It is the only check in the chain that
   sees whether the *body* is in the conditioning frame, and every route that authors an
   image — first-and-last-frame beat endpoints, set-hold anchors, per-chunk chaining — hands
   the model a frame that can be cut. The advisor may want it named the way the overlay check
   was named after E08.
6. **`a3`'s pre-registered definition collided with `d3`'s outcome.** A drift definition that
   names features of the lower body cannot be evaluated on a clip whose last quarter crops
   the lower body. The definition was registered before the fact and is not being retuned
   here; the collision is reported as it stands.
7. **The saved-projection capture is one degree weaker than E08's and E10's**, and §5 says
   why: transcription, not a byte-stream download.
8. **E08's frame-delta median is 3.95 under one convention and 3.917 under another.** Both
   are computed in §7 so a fourth report does not re-derive it.
9. **One error in this seat's own drafting, caught before the commit and recorded rather
   than quietly fixed.** The first draft of §2's table carried a camera target and radius
   this seat had never read — plausible numbers beside real ones, which is precisely the
   placeholder-shaped-like-evidence failure CLAUDE.md names. They were replaced with the
   values in `start_frame_provenance.json` (target `[-0.0153, -0.0306, -0.0713]`, radius
   2.4808). Nothing else in the report was derived from the wrong pair, and every other
   number in it was read from a file or a tool's own output. The general lesson is the one
   the repo already carries: a table is where invented values look most like measured ones.

The Director judges identity and motion, on the two-pipeline sheet at true tempo.
