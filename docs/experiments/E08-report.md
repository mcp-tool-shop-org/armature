# E08 — report: the first painted shot, on the calibrated chain

**Seat: executor**, branch `E08-shot`, worktree `E:\AI\armature-E08b`, from `main` at
`aa09986`. **One generation of the shot** (`prompt_id`
`eb1fb0df-d754-4b2f-a4f4-b2f3b9d8c29f`, seed `2026081211`), plus one model-free bridge
verification (`ef07f754-cf79-4998-8fdf-0f3d63051029`). Reserve seeds `2026081212` and
`2026081213` **unspent**. No gate fired.

This report carries measurements, gate states, and predictions against outcomes. It contains
no judgement of whether the footage is good; the Director's eye is the verifier of record and
the advisor rules on what the measurements mean.

**Look first:** `outputs/E08/sheets/E08-gate0.png` — previz | control | painted | reference |
provenance, five frames. Then the review clip at 0.5× / 8 fps from `lossless/`, then the zoom
sheets in the order the spec asks: arms, hands, skull, the bar.

---

## 1. Premises, re-verified at use

| # | premise | spec status | what re-verification found |
|---|---|---|---|
| 1 | The E09 A3 baseline motion + GLB | MEASURED | **CONFIRMED with a label correction.** The digest matches exactly. The spec calls `cd4e2f6ee85e…` an **md5**; the E09 report's table heads that column **sha256 (first 32)**, and sha256 is what matches. The file's actual md5 is `6614691df9db7cacfe8580a30a2593d9`. Value right, algorithm mislabelled in the spec. |
| 2 | The drawing convention, "fetched + banked with hash (E09 route2)" | MEASURED | **FALSIFIED as stated.** No copy of `human_visualization.py` existed in `outputs/E09/route2/`, anywhere else in the repo, or in any worktree — that directory holds the Wan **T2V** configs and README. The only record was G6, a summary. Re-fetched under the map's existing Apache-2.0 row, banked at `outputs/E08/convention/`, sha256 `962813c71b2f…`, 44,228 bytes, pinned to commit `29d4a35d32273d5309a3a95250bd4e118d8789b2`. §2 records what the summary got wrong. |
| 3 | The twin reference, Director-approved | MEASURED | Confirmed; sha256 `4d40c9a19c46bb09…`, 352×1024. §5 records what the node does to it. |
| 4 | `WanAnimateToVideo` socket schema, "six optionals" | MEASURED | **SEVEN optionals**, measured 2026-08-12: `clip_vision_output`, `reference_image`, `face_video`, `pose_video`, `background_video`, `character_mask`, `continue_motion`. |
| 5 | Licence rows | MEASURED | Confirmed. Every weight this graph loads has a row (§8). |
| 6 | The model accepts CG-rendered sticks at product quality | **ASSUMED — the experiment** | §9–§11. |
| 7 | The billing meter | ASSUMED until measured | §12. Measured, and it does not do what Gate C needed it to do. |

---

## 2. The convention, transcribed from the source rather than the summary

`tools/armature_core/aapose.py`. Three things the source says that G6's summary does not:

1. **It is a 20-keypoint, 19-pair convention, not an 18-point one.** G6 calls it "the classic
   18-point `limbSeq`". `draw_aapose_new` — the function `draw_aapose_by_meta_new` calls —
   carries the OpenPose-18 body **plus `LToe` and `RToe`**, joined by `[14, 19]` and
   `[11, 20]`. An 18-point render against this convention omits both feet and nothing errors.
2. **Limbs are filled at 0.6 of their palette colour; joint circles are drawn at full.**
3. **The v2 hand stick width is half the body's**, floored at 1.

**The trap this keeps visible.** `armature_core.openpose` holds ControlNet's OpenPose-18. It
agrees with Wan's on **seventeen of nineteen** pairs and differs exactly at the feet
(ControlNet closes shoulder-to-ear `[3,17],[6,18]`; Wan closes the feet). Both modules stay;
tests assert they are different objects and that `check_convention` refuses ControlNet's
table outright.

**The named residual: channel order.** The palette is fed straight to `cv2`, which is
order-agnostic, so the canvas's order is the caller's. The file settles it in its own
`__main__` — `cv2.imwrite("traj.png", res[0][..., ::-1])`, i.e. the array is RGB and is
reversed for writing. Frames are written under that reading and the manifest records it. A
red/blue swap would fail silently (G10); this is the module's highest-risk residual and it
rests on one line of somebody else's demo code.

At **832×480 the convention's own formula gives `stickwidth = 1`** — `max(int(480/200)−1, 1)`.
At 720p the same formula gives 3. The driving signal for this shot is a one-pixel skeleton.

---

## 3. The toes were wrong, and the instrument that caught it was the body

The first projector read keypoints off the exported GLB's bone heads and tails. Eighteen of
twenty landed correctly. `LToe` and `RToe` did not: glTF stores joints as nodes and has **no
bone tail**, so Blender's importer synthesises one for every leaf bone, and the ankles are
leaves.

| quantity | GLB bone tails | rig manifest, measured |
|---|---|---|
| ankle→toe over hip→ankle, projected | 0.33 – 0.55 | **0.087 – 0.139** (median 0.114) |
| `ankle.L`→`toe_L` | — | 0.10476 (against `knee.L`→`ankle.L` 0.31379) |

**Every gate passed on the wrong output.** MAP resolved, FRONT resolved, FRAMING solved,
MOTION counted 65 distinct poses; CANVAS, INK and COUNT passed downstream. Every check in the
chain is a check of internal consistency, and a skeleton with its feet in the wrong place is
perfectly self-consistent.

What saw it: the sticks composited onto the E09 previz of the same performance, through a
camera **pinned to that render's own provenance** (`framing.load_pinned_camera`, which refuses
a record that disagrees about any angle *and* one that is merely silent about one). Both toe
markers hung in empty air on the floor, clear of the rendered feet, at frames 0, 32 and 64 —
`outputs/E08/sheets/E08-overlay-feet.png`.

The replacement places landmarks with `lift_solve.fk_sites` from the rig manifest's measured
rest landmarks and the motion record, through the same kinematics the solver inverts. `toe_L`
and `toe_R` are measured landmarks there. The tool needs no Blender at all. The falsified
route is runnable at `tools/superseded/project_pose_keypoints_from_glb.py` with its numbers.

**That overlay now runs before any credit is spent.** It is the only instrument in the chain
that can see an error of *correspondence* rather than of consistency.

---

## 4. The control sequence, measured

65 frames, 832×480, 16 fps, from the E09 A3 baseline dance.

| quantity | value |
|---|---|
| figure span, px per frame | min 246.7 · median 254.8 · max 307.2 |
| hand span, px per frame (synthesised mitten fan) | min 19.5 · median 23.4 · max 29.0 |
| stick width / hand stick width | **1 px / 1 px** (the convention's formula at this resolution) |
| ink fraction | min 0.00483 (frame 6) |
| distinct projected poses | 65 / 65 |
| camera | az 225° / el 6° / 50 mm / 36 mm, height-frac 0.70 — `render_performer`'s banked E09 values, verbatim |

The hands are a **construction, not a measurement**: the mannequin has mitten hands with no
fingers, so 21 keypoints are laid out as a rigid five-finger fan in the wrist bone's own
frame, every offset a fraction of that hand's own measured length. It turns with the arm and
never articulates.

---

## 5. The reference, and what the node does to it

`WanAnimateToVideo` does not letterbox `reference_image`. It calls
`comfy.utils.common_upscale(..., "area", "center")` — a **cover** crop. Read from the source
and computed on this asset: the twin is 352×1024 (aspect 0.344), the frame is 832×480 (1.733),
so `y = round((1024 − 1024 × (0.344/1.733)) / 2) = 410` and the node keeps **rows 410–613 —
204 of 1024, 19.9%**. That band is the hips and thighs: no head, no face, no hands. Nothing
errors; the node resizes cleanly and the run completes.

Measured, rendered as a comparison (`outputs/E08/sheets/E08-reference-fit.png`) and put to the
Director. **He ruled letterbox.** `tools/fit_reference.py` performs the contain-fit — scale to
480 tall (165×480), centred on 832×480, pad sampled as the median of the source's own outer
4% border — and its provenance carries the source hash, the derived hash, the transform, and
what the node would have done instead. The figure occupies **19.83%** of the reference frame;
the remaining 80% is flat pad.

---

## 6. `character_mask`: not wired, for a measured reason

The spec's condition was "wired **only if** its animation-mode semantics verify from the node
schema/docs". The schema carries no description at all. They verify from the **core node
source**, and they say do not wire it here.

`character_mask` is upscaled to latent resolution and written into `mask_refmotion`, which
becomes the conditioning's `concat_mask` over the background plane. Mask 1 means generate;
0 means keep what is in `concat_latent_image`. With `background_video` unconnected the node
builds that plane as `torch.ones(...) * 0.5` — uniform mid-grey — and leaves the mask all
ones. A character mask would therefore instruct the model to **preserve flat grey everywhere
outside the figure**: a grey void exactly where clause 3 is asking for a bar.

It becomes a live lever the moment `background_video` is used, and not before. G12 prices
masking in the literature; the literature's mask sits over a real background, and this graph
has none.

---

## 7. The bridge: one file instead of sixty-five, and how far it was proven

`ComfyUI/nodes.py::LoadImage` concatenates every frame of a multi-frame image into one IMAGE
batch — its PIL fallback exists for that, under a comment naming animated WebP outright.

| step | result |
|---|---|
| lossless animated WebP, Gate R locally | **identical** |
| upload to Comfy Cloud | **REFUSED — `422 INVALID_IMAGE`, "Uploaded input is not a valid image"** |
| lossless APNG, Gate R locally | **identical**, 65 frames, 170,942 bytes |
| upload | accepted |
| model-free run `LoadImage → SaveImage` (`ef07f754…`) | **65 results, in order** (`batch_00001_` … `batch_00065_`) |
| those frames vs the local sticks, sampled 0/16/32/48/64 | **pixel-identical** |
| Gate B on the real run, **all 65 frames** | **identical** |

The driving signal reached the model exactly as drawn — not sampled, not inferred: all 65
frames compared pixel for pixel.

---

## 8. Gates

| gate | where | state |
|---|---|---|
| **MAP** | projector | PASS — every AAPose landmark resolves on the registered rig |
| **FRONT** | projector | PASS — 65 × 62 points, all in front of the camera |
| **FRAMING** | projector | PASS solved (shot); SKIPPED-and-recorded when pinned (overlay) |
| **MOTION** | projector | PASS — 65 distinct projected poses |
| **CONV** | sticks renderer | PASS — 20 keypoints / 19 pairs / 20 palette entries vs the pinned source |
| **CANVAS** | sticks renderer | PASS — every body keypoint inside 832×480 |
| **INK** | sticks renderer | PASS — min 0.00483 at frame 6 |
| **R** | pose pack | PASS — identical, both encodings |
| **L** | payload builder + ROUTE | PASS — 832×480×65: /16, /16, 4n+1, ≤ 81 |
| **S** | payload builder + ROUTE | PASS — seed `2026081211`, drawn from the list committed at `ce9f004`, pre-submission |
| **ROUTE** | built API graph **and** saved file | PASS — 3 weight files, 1 seed pinned, 1 latent legal |
| **B** | the run | PASS — 65/65 frames pixel-identical |
| topology | payload builder | PASS — checked in code; a `dry_run` PASS does not prove link sanity |

**Gate L would have checked nothing on this route, and that is the session's second
self-inflicted catch.** `route_gates.LATENT_NODES` knew only `Empty*LatentVideo`.
`WanAnimateToVideo` emits its own latent from its own `width`/`height`/`length`, so an Animate
graph contains no latent node the table recognised: `latents()` returned an empty list and
`verify()` reported the graph legal having examined **zero** frames. A check that cannot fail
is not a check. The table now carries `WanAnimateToVideo` and `WanVaceToVideo`, with six
regression tests.

**Admission, built vs saved:** the conditioning node's widgets agree
(`[832, 480, 65, 1, 5, 0]`); the saved `KSampler`'s `control_after_generate` reads `"fixed"`;
the five deliberately-empty sockets are `null` in the saved file —
`background_video`, `character_mask`, `clip_vision_output`, `continue_motion`, `face_video`.
Evidence: `outputs/E08/route/E08-gate-evidence.json`.

---

## 9. The prompt, with its change log

The identity clause is facet E33's `_entry_verbatim`. Two phrases were **dropped**, each
recorded with its reason rather than silently edited:

| dropped | reason |
|---|---|
| `plain pale grey background` | names a backdrop; contradicts the scene clause this shot measures |
| `soft studio light` | names a lighting setup; contradicts "warmly lit" |

Carried verbatim, the clause would have instructed the model to paint a plain pale grey
background in the same breath as a crowded bar, and clause 3 would have measured a
contradiction rather than the prompt's strength.

The negative is Wan's own `sample_neg_prompt`, **read from the banked config**, never retyped
— E09's citation check fired on that exact string.

**A contradiction inside the graph, found while building and left in place.** Wan's default
negative contains 杂乱的背景 ("cluttered background") and 背景人很多 ("many people in the
background"). The positive asks for a crowded bar with other people around him. The negative
fights that clause of the positive. It was left unchanged — it is Wan's documented default,
changing it would have moved two variables — and named in the predictions **before** the run
as the first candidate cause if the crowd failed to appear.

---

## 10. What came back

131 outputs: 1 video, 65 Gate-B batch frames, 65 lossless frames. 65 of 65 output frames are
distinct. Mean absolute frame-to-frame delta: min 2.55, median 3.95, max 6.16 (0–255).

Read off the sheet and the zoom crops, in the order the spec asks:

- **Arms** (`E08-zoom-arms.png`, 2×). At all five sampled frames the painted figure's shoulder
  and elbow angles correspond to the control sticks: f0 one arm down-forward and one out
  horizontally; f16 both angled down with the screen-right arm extended; f32 screen-right arm
  raised ~45° and screen-left bent across the chest; f48 screen-left arm high and screen-right
  extended up-right; f64 both out to the sides. The painted arms read as smooth — the
  sculpted ball joints visible at the elbows in the reference are absent at the elbows in most
  frames, while remaining visible at the knees and hips.
- **Hands** (`E08-zoom-Lhand.png` / `-Rhand.png`, 6×). No frame resolves fingers. f0 is a
  motion smear; f16 tapers to a thin dark spike; f32 is a flattened paddle with a hooked tip;
  f48 a paddle with a dark notch; f64 a blurred lump. The reference itself has fingerless
  mitten hands ("empty open hands"), so absence of fingers is not a departure from the
  character; the spikes and hooks at f16 and f32 have no counterpart in the reference.
- **Skull** (`E08-zoom-skull.png`, 5×). At f0, f32, f48 and f64 the head reads as a smooth
  bald head with ears, brows, lidded eyes and a small closed smile. **At f16 the face is
  smeared** — features dissolve into a horizontal blur. Face stability is not uniform across
  the clip.
- **The bar** (`E08-zoom-bar.png`). Back-bar shelving with bottles, warm strip lighting under
  each shelf, glassware racks left and right, a counter carrying a coffee machine, straws,
  glasses and a board; a wooden bar top across the foreground. Present and consistent at every
  sampled frame. **No other people appear in any frame.** The figure stands on the bar top.

**A washed vertical banding** runs through the clip, strongest early and reducing by f48–f64,
with a faint chromatic strip at x ≈ 160–200 in the later frames.

---

## 11. A diagnostic that failed, reported as failed

The banding invited an obvious hypothesis: the letterbox's flat pad leaking in. Two
instruments were built to test it and **neither discriminates**:

1. **Vertical-seam step** (max jump between adjacent column-mean luminances). It fires on
   65 of 65 frames (min 20.9, median 40.6, max 78.7). It would fire just as hard on any
   ordinary bright vertical edge — a pillar against dark shelving — so it does not separate a
   compositing seam from scene content.
2. **Column overlap with the reference's margins.** The washed quarter of columns falls inside
   the reference's pad regions **100%** of the time — against a **chance level of 80.2%**,
   because the pad occupies 80% of the reference frame. The margin over chance is too small to
   carry the claim.

So: the banding is a description from looking, and the pad-leak reading is a **named candidate
cause, not a finding**. Ask of a metric what value it takes when the hypothesis is false;
these two take nearly the same value either way, which is the "grade an arm only on what it
can move" law failing in this seat's own instruments. A discriminating test would need a
second generation with the as-is (cover-cropped) reference, and that is the advisor's call
against the remaining ceiling, not this seat's.

---

## 12. Both meters

**The declared billing meter cannot arm Gate C on this route.** `estimate_credits` returns
**0 credits — no paid API nodes**: the graph is entirely OSS/local nodes, and the tool prices
only per-node declarations. GPU and queue time are excluded by the tool's own statement.

**The GPU meter has not yet resolved.** `get_usage_report`'s window closes at
2026-08-12T08:00:00Z; the probe ran after that (its signed URLs are stamped ~08:33Z), so the
invoice does not yet include it. Baseline for a later delta: GPU Hours Product **$17.166467**
for 2026-07-12 → 2026-08-12, of which the 2026-08-12 00:00–08:00 bucket is **$0.552448**.

**The ceiling was therefore enforced by counting generations**, not by a credit figure: 1 of
3 spent on the shot, plus one model-free bridge verification. Reserve `2026081212` and
`2026081213` unspent. This is a finding for the advisor: on an all-OSS route the spec's "Gate C
arms on the measured billing number" has no number to arm on, and the honest substitute is the
generation count.

---

## 13. Predictions versus outcomes

Registered blind at `ce9f004`, before the submission and before any E08 output existed.
Each clause read separately.

| clause | predicted | outcome |
|---|---|---|
| **H-E08a** gross body pose tracks the sticks — 80% | tracks | **HIT.** Correspondence visible at all five sampled frames, arms and legs. |
| **H-E08a** limb timing matches frame for frame — 65% | matches | **HELD, not isolated.** The sheet samples five frames; frame-exact timing across all 65 was not measured, and this seat did not build an instrument for it. |
| **H-E08a** the 1-px stick width costs something visible — 55% | costs | **NOT SUPPORTED as the dominant risk.** Adherence is visible despite a one-pixel skeleton. Whether it costs *degree* is unmeasured. |
| **H-E08b** terracotta / bald jointed-mannequin read survives — 70% | survives | **HIT.** |
| **H-E08b** the face survives as the twin's face — **30%** | mostly not | **MISS, and by a wide margin.** The face reads at 4 of 5 sampled frames — brows, lidded eyes, small closed smile, ears. I under-predicted this badly. The one exception is f16, where it smears. |
| **H-E08b** the pad leaks in as a grey field — 40% | maybe | **UNRESOLVED.** Banding is present; §11 shows this seat's two tests cannot attribute it. |
| **H-E08c** some scene arrives — 75% | arrives | **HIT.** |
| **H-E08c** a recognisable bar — counter, bottles, warm light — 45% | maybe | **HIT**, and more completely than predicted: shelving, bottles, under-shelf lighting, glassware, counter, machine. |
| **H-E08c** other people, as the prompt asks — 25% | probably not | **HIT on the prediction, and the pre-named cause stands unrefuted.** No people in any frame. Wan's default negative names both "cluttered background" and "many people in the background". Named before the run; still only a candidate, since nothing tested it. |
| **H-E08d** some humanisation at the limbs — 60% | some | **HELD, weakly.** The painted proportions read closer to human than the reference's; not measured. |
| **H-E08d** elbow/knee ball joints survive — 35% | mostly not | **SPLIT.** Knees and hips keep visible ball joints; the elbows largely do not. Predicted as one clause; it resolved differently at different joints. |
| **H-E08d** hands come back malformed — 80% | malformed | **HIT on the letter, ambiguous on the meaning.** No fingers anywhere — but the character has no fingers. The spikes and hooks at f16/f32 are the part with no counterpart in the reference. |
| **H-E08d** skull reads as smooth and bald — 65% | reads | **HIT.** |

**The pattern in my own misses:** I under-predicted every clause about identity and scene, and
over-weighted the risks I had spent the session building instruments for. The stated fail
condition — "if the painted figure's limbs do not follow the sticks" — did not occur.

---

## 14. Artifacts

| artifact | sha256 (first 32) |
|---|---|
| the convention source, banked | `962813c71b2f2e09f7cd745b35b31a0d` |
| projected keypoints (shot, 832×480) | `62b27eebfe52f0efdaf0d2e393e463bd` |
| stick manifest (65 frames + per-frame hashes) | `de63919bf9f4b59c0ac94acb1dff762c` |
| the pose pack, as uploaded (APNG, 65 frames) | `2c83271a1a8bd2e96c17806c297de9f8` |
| the letterboxed reference, as uploaded | `34fd9177f590fc31a832a0319af04ca4` |
| the graph, as built | `3d00fffeabef1c64d438abfa3f1f807d` |
| payload record (every value + its source, the prompt change log) | `c5a68fa65e9ea0798227f7b5ad141656` |
| gate evidence, built + saved | `06a469db37ac9fcca8fcbaa5b48fd2e9` |
| Gate B evidence (65/65) | `64c509c4fdcea7209bdc439cff18ba35` |
| **the Gate 0 sheet** | `bffa4930b8a2b9f91895fafe5bde5c6b` |
| the correspondence overlay | `a391f5e2a1ab76c5b51d9b5d058dd3e3` |
| the reference-fit comparison | `8efa195bb5ca7a0455038d2e66acd102` |
| **the review clip, lossless 0.5×** | `1ad9565e41289e4b8cb1e10fdea84e1f` |
| the probe video (convenience only) | `e9d8110150f1e9a5e66af4e6909dc74d` |
| 65 lossless frames | per-frame in `outputs/E08/probe/` |

New in the tree: `armature_core/aapose.py`, `project_pose_keypoints.py`,
`render_pose_sticks.py`, `pack_pose_pack.py`, `fit_reference.py`, `build_animate_payload.py`,
`make_overlay_sheet.py`, `make_e08_sheet.py`, `framing.load_pinned_camera`, the `wan-animate`
generator profile, the `LATENT_NODES` additions, `specs/E08-seeds.json`, and
`tools/superseded/project_pose_keypoints_from_glb.py`.

**Suite: 556 passed, 43 skipped** (main's baseline was 472/43).
⚠ The commit message on `ce9f004` says "532 → 566 passed". **566 is wrong; it is 556.** The
error is in the commit message only; no measurement depends on it.

---

## 15. Compensators

| act | compensator | state |
|---|---|---|
| the probe generation `eb1fb0df…` | **none exists** — spent GPU time has no undo | 1 of 3; reserve `2026081212`/`2026081213` unspent |
| the bridge-check run `ef07f754…` | none | model-free; a few GPU-seconds |
| uploaded reference `54a38251…6125758a84f.png` | delete server-side (Comfy Cloud inputs) | **present; owner executor** |
| uploaded pose pack `a863dff3…d41b10863.png` | delete server-side | **present; owner executor** |
| saved cloud workflow `armature-E08-probe-animate` (`f18636b6-9461-4e97-84dd-59312c2b5b5b`) | delete server-side | present; owner executor |
| downloaded outputs under `outputs/E08/` | delete the directories | written; owner executor |
| worktree + branch `E08-shot` | `git worktree remove` + branch delete | owner advisor, after the ruling |

**Every uploaded artifact is listed above with its named undo.** Two files were uploaded, not
sixty-six — the pack bridge is why. No publishes, no releases, no external posts, no writes to
the memory store.

---

## 16. For the advisor

Measured here, with no authority to rule on any of it:

1. **Spec premise 2 was false and premise 4 was off by one.** The convention source was never
   banked, and the node has seven optionals, not six. Both are now measured; the spec should
   be corrected in place.
2. **Gate C has no number on an all-OSS route.** `estimate_credits` returns 0 by construction.
   Either the spec's Gate C is re-specified against generation count, or a GPU-time meter that
   resolves before the invoice window is found.
3. **The banding is unattributed and this seat's two tests cannot attribute it.** A
   discriminating experiment exists — one generation on the as-is cover-cropped reference,
   same seed — and it would spend a reserve.
4. **The negative prompt fights the positive's crowd clause.** Wan's own default excludes
   "many people in the background". Changing it is a variable; whether E08's next wave should
   move it is a ruling.
5. **The overlay check should be doctrine, not an E08 tool.** It is the only instrument in the
   chain that sees correspondence errors rather than consistency errors, and it caught one
   that every gate passed.
6. **The elbows lose their ball joints while knees and hips keep them.** Predicted as one
   clause and it resolved differently per joint — the "predict each clause separately" law
   applies one level finer than I applied it.

The Director judges the shot.
