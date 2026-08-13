# S03 — the performer reference kit (report)

**Executor session, 2026-08-13.** Worktree `E:\AI\armature-S03`, branch `S03-run`, cut from
`main` at `8e0cdc3`. Dispatch: [S03-performer-reference-kit.md](S03-performer-reference-kit.md),
confirmed byte-identical to `main`'s copy before any work began
(`git diff origin/main -- docs/dispatches/S03-performer-reference-kit.md` → empty).
Predictions: [S03-predictions.md](S03-predictions.md), committed at `f8e678c` **before the
first render existed**, with blindness disclosed per prediction.

**Nothing in this report is a judgement of quality.** The kit goes to the Director's eye.

| task | outcome |
|---|---|
| **A** — the RGBA-true turnaround | 8 views rendered, alpha extrema (0, 255) on all eight; Gates ALPHA, TURN and WHOLE passed |
| **B** — the hole survey | 8 full-size old-beside-new sheets + contact sheet + per-view numbers; the patches persist, as predicted |
| **C** — the frames→VIDEO chain | **The 81-frame chain FAILED at the batch link.** Zero partner credits. The chain executes at 8 frames; `CreateVideo(fps=16)` → `SaveVideo` produced a decodable 16 fps video |

Zero partner credits spent, on the estimate and on both submissions. No named halt fired.

---

## 0. Dispatch checks, in the order the dispatch ordered them

| check | result |
|---|---|
| VRAM watchdog before any GPU work | **alive**, heartbeat 0 s old; re-armed at kill VRAM 31200 MiB / RAM 90% / 87 °C |
| Dispatch byte-identical to `main`'s copy | **yes** — empty diff |
| Binding documents read from `main` | CLAUDE.md, the halt ruling, the E13 report (from `E13-run`), E12 w2/w3 §7 |
| Blender headless, through PowerShell | yes — `blender -b -P`, `RENDER_TURNAROUND_OK` printed |
| `E:\AI\training`, `E:\AI\facet`, the E12 worktree | **read only.** Nothing written to any of them |

---

## 1. Predictions, scored

Committed at `f8e678c`, before any output existed. Scored honestly, including the one that
was half wrong.

| # | prediction | outcome |
|---|---|---|
| P-A1 | the canonical asset is `performer_textured.glb` (declared NOT BLIND) | **held** — and see §2, the dispatch's own premise list does not name it |
| P-A2 | all 8 views return `alpha_min = 0`, `alpha_max = 255` | **held** — exactly (0, 255) on all eight |
| P-A3 | the holes persist, on views 1, 2, 3, 5, 6, 7; 0 and 4 clean | **held** — see §4 |
| P-A4 | profiles (2, 6) most transparent; front (0) and back (4) least | **HALF WRONG.** 2 and 6 are the most transparent (0.8472, 0.8461) as predicted. View 4 is the least (0.7541), but **view 0 is the most transparent of the six non-profile views** (0.7614), not among the least. The "front and back are the least" clause is false for the front |
| P-A5 | every view's transparent fraction in 0.70–0.90 | **held** — measured 0.7541 … 0.8472 |
| P-A6 | Gate WHOLE passes on all 8 | **held** |
| P-A7 | all 8 views byte-distinct | **held** — 8 distinct sha256 |
| P-A8 | same character as the A2 clip, same rest pose | **held** — read at full size beside an extracted clip frame, §3 |
| P-C1 | 81 frames re-hash to the E12 `gate_b` record | **held**, and see §5 for the instrument slip that nearly made it look otherwise |
| P-C2 | `estimate_credits` returns 0 partner credits | **held** — "0 credits - no paid API nodes found in this workflow" |
| P-C3 | the E02 batch mechanism carries all 81 frames | **FALSIFIED.** The submission failed with `BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'` |
| P-C4a | the produced VIDEO decodes to N frames at fps 16 | **held at 8** (not reachable at 81, because P-C3 failed): 8 decoded frames, 16 fps |
| P-C4b | the decoded frames are NOT bit-exact, and the error is structured at colour edges | **held** — 0 of 8 frames identical; mean abs 2.23–2.54; mean difference 12.19 on the top-10% gradient pixels against 5.28 on the bottom-50% |
| P-C5 | (not a prediction — the r2v residual) | stays **ASSUMED**, §6 |

**One wording slip in the predictions file, disclosed rather than edited.** P-A8 there reads
"Verified by eye at full size" — and *verified* is one of the six words an executor's
documents may not use. It is left standing: that file is a pre-registration, and editing it
after seeing the results is a worse fault than the word is, whatever the edit. The word is
used there in the sense of "checked by looking", and the same sentence contrasts it with
asserting from the hash chain, but it should have read "read at full size" and it does not.

---

## 2. Task A — the lineage, and a correction to the dispatch's own premise table

**The dispatch's premise row is incomplete, and choosing from it would have failed the
coherence row.** The row reads: *"Performer GLBs on the rig: `performer_300k.glb` (12.75 MB),
`performer_raw.glb` (36.19 MB); `performer_dance_ema.glb` (13.00 MB, E11's start)"*, marked
MEASURED against E13 §5. Every file in it exists at the stated size. But the canonical
**unposed, textured** asset on the A2 lineage is none of the three: `performer_300k` and
`performer_raw` are pre-texture, and `performer_dance_ema` is posed.

Resolved by hashing every link rather than by picking from the list:

| step | file | sha256 | bytes |
|---|---|---|---|
| canonical, unposed, textured | `facet_E33\out\performer_textured.glb` | `9e20ea7d800c0ffd…` | 21,588,628 |
| — same file, copied into armature | `armature-E07\outputs\E07\subject\performer_textured.glb` | `9e20ea7d800c0ffd…` | 21,588,628 |
| → `rig_repair` (UV layout and atlas survive; material `hero`) | `performer_repaired.glb` | `501a6db79cea0afa…` | 10,648,452 |
| → `rig_character` | `performer_auto.glb` | `7f56c9ac101218db…` | 12,961,704 |
| → `lift_solve` + `lifted_ema` motion | `performer_dance_ema.glb` | `cd4e2f6ee85ef536…` | 12,999,740 |
| → `render_start_frame` E11.1 | E12's start frames → the A2 clip | | |

**No ambiguity, so no halt.** All three E12 start-frame provenance records
(`startframe/`, `startframe-A1w/`, `startframe-A2w/`) name the same source GLB and the same
pose signature, and the chain above resolves to exactly one unposed textured asset.
`E33_manifest.json` independently names `out/performer_textured.glb` as its `_deliverable`,
and the `turn_final` views were written in the same minute as it.

The two dispatch premises that were re-measured rather than inherited:

- **`turn_final` is defective** — re-measured this session: all 8 views RGBA 352×1024,
  **alpha extrema (255, 255)** on every one, corner pixel (154, 154, 157). The premise holds.
- **The performer faces −Y** — `rig_manifest_auto.json` records `facing_y_sign: -1.0`, feet
  primary, head cross-check agreeing. Front is therefore azimuth 270°.

### What was rendered

`tools/render_turnaround.py` (`S03.1`), Blender 5.2.0 LTS `fbe6228777e7` (build 2026-07-14),
numpy 2.3.4. Full record: `outputs/S03/turn_rgba/turnaround_manifest.json`.

Composition, every value a recorded choice: 352×1024 (matching `turn_final`, so the Task-B
comparison is a comparison and not a resize) · 8 views, azimuth start 270°, sweep +360°,
elevation 0° · 50 mm on a 36 mm sensor, AUTO fit · orbit radius **1.728241**, solved through
`framing.project` to put the tallest projected view at 0.831 of frame height — the fraction
measured off the old set (rows 86–937 of 1024) · no floor plane, because a ground plane is
opaque geometry and would bake exactly the kind of non-transparent backdrop this task exists
to remove · staging inherited verbatim from E09/E10 via `render_start_frame` (two suns at
3.2/1.1, world 0.16/0.16/0.18 linear, EEVEE, Standard view transform).

**The lens is a recorded choice, not a match.** `turn_final`'s lens is not recorded anywhere
on this rig; 50 mm is the repo's standing value in `render_performer` and `render_start_frame`.

| view | azimuth | sha256 (first 16) | alpha extrema | transparent | height frac | width frac |
|---|---|---|---|---|---|---|
| 0 | 270° | `83ab99d19162b3dd` | (0, 255) | 0.7614 | 0.8173 | 0.7782 |
| 1 | 315° | `f61e2071444fd8d1` | (0, 255) | 0.7578 | 0.8290 | 0.5802 |
| 2 | 360° | `42fd871b280bcb9a` | (0, 255) | 0.8472 | 0.8293 | 0.3902 |
| 3 | 405° | `b3ddd99fd1e12c61` | (0, 255) | 0.7564 | 0.8203 | 0.6083 |
| 4 | 450° | `8772ad21b6c711b3` | (0, 255) | 0.7541 | 0.8235 | 0.7877 |
| 5 | 495° | `1294270f5b2eb576` | (0, 255) | 0.7561 | 0.8303 | 0.5715 |
| 6 | 540° | `3434e3a8d5b2cd93` | (0, 255) | 0.8461 | 0.8310 | 0.3803 |
| 7 | 585° | `a7d260769da5c539` | (0, 255) | 0.7603 | 0.8201 | 0.6283 |

**No view failed the alpha check**, so no view is withheld. Framing against the old set,
measured with matched pixel instruments (new: alpha > 0; old: colour difference from its
baked void):

| view | new (px) | old (px) | | view | new (px) | old (px) |
|---|---|---|---|---|---|---|
| 0 | 276 × 842 | 285 × 852 | | 4 | 279 × 849 | 285 × 852 |
| 1 | 212 × 856 | 215 × 852 | | 5 | 211 × 855 | 216 × 852 |
| 2 | 140 × 855 | 140 × 852 | | 6 | 136 × 857 | 140 × 852 |
| 3 | 226 × 850 | 232 × 852 | | 7 | 231 × 849 | 233 × 852 |

### The instrument, and the gates that ride it

`render_turnaround.py` is a **new tool**, and the enumeration is the reason. Both renderers
the dispatch names were read first: `stage_render.py` orbits a static subject with
`film_transparent` already on, but emits control channels (depth/normal/mask/edge/pose) with
no shaded pass; `render_performer.py` and `render_start_frame.py` both shade and light
correctly and both stand at **one** azimuth on a performance frame. The orbit machinery
(`blender_scene.orbit_azimuth`, `orbit_matrix`, `auto_radius`) and the alpha law
(`startframe.gate_alpha`, `gate_whole`, `silhouette_extent`, `framing_cloud`) already existed
and are reused; nothing was re-invented.

Gates, all raising in-tool, all running after the frames and **before the manifest**:

- **Gate ALPHA**, per view — binds both directions. `alpha_min == 255` is the `turn_final`
  defect exactly; `alpha_max < 255` is the view nobody rendered into, which has a richly
  varied alpha channel and which the criterion as stated in prose ("extrema ≠ (255,255)")
  admits. Both are extrema, not thresholds.
- **Gate TURN** — the count, and that no two views are byte-identical. A camera assigned once
  outside the loop writes 8 well-formed RGBA files that every per-view gate passes.
- **Gate WHOLE**, per view — the silhouette inside the frame, measured unclipped. The radius
  is fitted on height; this is the check on the axis that varies.

The **opaque fraction is reported and gated by nothing**: no calibrated threshold for how
much of a portrait frame a mannequin fills exists on this rig, and inventing one would be a
pass condition this session could move.

**45 tests ride these commits** — 18 for the turnaround gates, 10 for the survey arithmetic,
17 for the assembly chain — including every andon under `-O` and `PYTHONOPTIMIZE=1`, with the
guard that the optimization actually took effect.

---

## 3. The coherence row

Read at full size, not inferred from the hash chain: frame 0 of the pinned A2 clip
(`w3-seed1.mp4`, sha256 `b3b43e23f9bc…`, recomputed this session and matching E13's pin)
beside `turn_0.png` and `turn_1.png`.

Both carry the same wooden/clay jointed lay figure: ovoid bald cranium with a slight crown
point and small protruding ears; carved brow, long straight nose, thin closed-lip mouth; ball
joints at shoulder, elbow, hip and knee; flat paddle hands with an articulated thumb; rounded
oval flipper feet; matte terracotta wood tone. The turnaround stands in the mesh's rest pose,
arms at sides — the same pose `turn_final` shows. Clip frames extracted with the repo's
pinned ffmpeg to `outputs/S03/coherence/`.

---

## 4. Task B — the hole survey

`tools/make_hole_survey.py` (`S03.1`) → `outputs/S03/survey/`: eight full-size per-view
sheets `view_0.png` … `view_7.png` (OLD beside NEW), one `contact.png`, and `survey.json`.

**The composite is a choice and is recorded.** The sheets show the new RGBA masters
composited over **the old set's own measured background**, sRGB (154, 154, 157), so the two
panels differ in the figure and not in the ground. The composite exists only in the survey;
the delivered masters in `turn_rgba/` stay RGBA and were not overwritten. Alpha was measured
**straight**, not premultiplied, before the compositing formula was written: edge pixels at
alpha < 60 carry mean RGB (110, 86, 76) against a full-alpha mean of (136, 98, 79), where
premultiplied edges would read near (16, 12, 9).

**The locator number is measured on an eroded interior in both sets, and that is not a
detail.** The old views have no alpha, so their figure must be masked by colour difference
from the baked grey void — which necessarily includes the antialiased rim, and rim pixels
blending into grey are low-saturation. The new views are masked by their real alpha. Counted
un-eroded, the two masks disagree at the edge and the number reports the *masking method* as
if it were a texture defect. Both masks are eroded 3 px before anything is counted. It is a
locator for the eye and gates nothing; the whole percentile curve is in `survey.json`.

| view | new sat<0.20 | old sat<0.20 | new mean value | old mean value |
|---|---|---|---|---|
| 0 | 0.00058 | 0.00057 | 107.5 | 147.4 |
| 1 | 0.02594 | 0.01654 | 77.0 | 135.2 |
| 2 | 0.03979 | 0.02434 | 77.0 | 151.7 |
| 3 | 0.01966 | 0.01383 | 88.5 | 166.6 |
| 4 | 0.00104 | 0.00041 | 83.5 | 160.4 |
| 5 | 0.04905 | 0.04096 | 69.7 | 146.8 |
| 6 | 0.05988 | 0.04581 | 91.8 | 150.6 |
| 7 | 0.04144 | 0.03614 | 115.4 | 158.6 |

### Per-view notes, from the full-size look

- **view 0 (270°, front)** — no unpainted patches visible. Small dark speckles on limbs and
  torso, present in the old view too.
- **view 1 (315°)** — patches at the right jaw and neck, right shoulder and upper chest, a
  small one at the left hip, both hands, the left foot.
- **view 2 (360°, profile)** — patches on the skull crown, along the jaw and under the chin,
  down the near arm and forearm, at the hip, across both hands, on the ankle and both feet.
- **view 3 (405°)** — patches on the crown and temple, the back of the head, the jaw, a large
  one on the mid-back over the spine, a small one at the hip, one on the near heel.
- **view 4 (450°, back)** — no unpainted patches visible. Dark speckles only.
- **view 5 (495°)** — patches on the crown, side of the head and ear, the shoulder-blade
  area, a run down the near arm and forearm, the hand, the near foot.
- **view 6 (540°, profile)** — patches on the crown, side of the head and ear, the jaw, a
  dense cluster across both hands, patches on both feet and toes.
- **view 7 (585°)** — patches on the near shoulder and upper chest, a run down the near side,
  hip and thigh, both hands, small ones at the feet.

**Two factual differences between the sets, beyond alpha, reported without interpretation:**

1. **The patches read grey in the new set and white in the old.** Same texels, different
   exposure: the new staging is E09/E10's and `turn_final`'s lighting is not recorded on this
   rig.
2. **The new set is darker throughout** — interior mean value 69.7–115.4 against the old
   set's 135.2–166.6. Same cause; it is a difference of staging, not of texture.

**Texture repair was not attempted and is out of scope** — the patches live in the atlas and
no re-render moves them; they are facet's projection-coverage arc. `E:\AI\training` and
`E:\AI\facet` were opened read-only. Which views are usable is the Director's ruling.

---

## 5. Task C — the frames→VIDEO chain

### The frame pin

n = 81, all 81 pixel-distinct, all 1024×576×3. The E12 `gate_b` record's three frame-delta
statistics reproduce **exactly**:

| | recomputed | E12 record |
|---|---|---|
| min | 6.550375479239005 | 6.550375479239005 |
| median | 8.756735342520255 | 8.756735342520255 |
| max | 10.866203590675637 | 10.866203590675637 |

**One instrument slip, recorded rather than smoothed.** The first recomputation reported a
median of 8.7448 against the record's 8.7567, with min and max matching to twelve decimals.
The data were not the odd one out — `gate_b_frames` computes `sorted(deltas)[len//2]`, the
upper-middle element of an 80-long list, where `numpy.median` averages the two middle
elements. Recomputed under the tool's own formula, all three match exactly. Had the check
been run only on the median, this would have read as a corrupted pin.

### Uploads

All 81 frames uploaded, **81 distinct content-addressed server names for 81 distinct local
frames**. The server's name is not the file's sha256 (checked: frame 0 hashes locally to
`9ccf615b0e39…`, the server returned `05ed637d2c36…`), so every name was captured rather than
predicted. Map: `outputs/S03/uploads.json`; local hashes: `outputs/S03/frames_pin.json`.

### The graph, built in-repo

`tools/build_assembly_payload.py` (`S03.1`) → `outputs/S03/route/S03-assembly.api.json`,
84 nodes: 81 × `LoadImage` → `BatchImagesNode` (dotted `images.image0…image80`) →
`CreateVideo(fps=16, bit_depth=8)` → `SaveVideo`. Node contracts re-measured with `get_node`
on 2026-08-13 and byte-consistent with the halt ruling's R2 measurement; all four classes
`api_node: false`, and `SaveVideo` is the only `output_node: true`.

**Frames are ordered by their LOCAL name.** Upload names are content-addressed, so sorting by
them would assemble the clip in an arbitrary sequence while every count in every gate still
read correctly. A test pins this.

### Gates, before submission

| gate | status |
|---|---|
| **ASSEMBLY (paid nodes)** | **PASSED** — 84 nodes across 4 classes, all named by the allowlist, none reading as a partner class. The allowlist is the binding clause; the name pattern is a second opinion on the allowlist itself, and its recall is unknown and stated as such |
| **ASSEMBLY (batch topology)** | **PASSED** — 81 distinct `LoadImage` nodes, dotted slot keys, every link resolved, `CreateVideo` fed by the batch, `SaveVideo` fed by `CreateVideo` |
| **ROUTE** | **PASSED** — 0 components, 0 seeds, 0 latents; frame legality decided on the supplied (1024, 576, 81) |
| **ROUTE / licence clause** | ran on an empty set: the graph loads **no weights**, so none can be banned. Reported for what it examined, not as a green tick |
| **ROUTE / Gate PAIR** | ran on an empty set: **no conditioning node**, so none can be unpaired |
| **Gate S (seed registration)** | **n/a — not claimed as passed.** This graph has no noise-bearing node, so `require_pinned_seeds=False` was passed deliberately. A green "0 seeds, all pinned" here would be the vacuous shape the E13 executor was ruled right to refuse |
| **Gate L (frame legality)** | ran on a **supplied** frame, not a graph-read one — this graph pins no latent. It decides that 1024×576×81 is legal for the `wan` rules; it does not check the graph |
| **Credit-ceiling halt (> 0 partner credits)** | **RAN — did not fire.** "0 credits - no paid API nodes found in this workflow" |
| Saved-graph round trip | **NOT RUN** — no workflow was saved to the cloud this session |

The round-trip table gained **one** row, `BatchImagesNode: {}` — empty because every input is
a dotted auto-grow link with no literal to compare, recorded as a fact exactly as `VAEDecode`
and `TrimVideoLatent` are, because the table is looked up with `is None` and an absent class
halts. `CreateVideo`, `SaveVideo` and `LoadImage` already carried rows. That is the whole of
what this graph needs and nothing more.

### The submission, and what it measured

**Submission 1 — the dispatch's chain, 81 frames.** `prompt_id`
`973199a5-85b3-44f1-8cd2-111e447d0a0b`. Pre-flight accepted it with **zero warnings**. The job
then **failed at execution**:

```
error_type: execution.node        node 400, BatchImagesNode
TypeError: BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'
```

**The 81-frame chain FAILED.** No named halt fired — the gates all passed, and this is an
execution result, not a gate. It is reported as failed and was not re-run at 81.

**Diagnostic — 8 frames, the same pinned uploads, labelled a diagnostic and not a retry.**
`prompt_id` `e0047fc1-f9b3-47c7-a335-f5c2948fe621`, job **completed**. This separates the two
readings of the failure: the dotted `images.image<N>` form is not wrong (it executes), so the
81-frame failure is a **limit on the number of slots**, not a malformed key.

**The limit's value is INFERRED, not measured.** The error named `images.image50` as the
unexpected keyword, and 8 slots execute, which points at `execute()` accepting
`images.image0 … images.image49` — 50 slots. It is **not** declared anywhere in the catalog:
`get_node` and `search_nodes(detail="full")` both report the input only as
`images: COMFY_AUTOGROW_V3` with no maximum, so the cap is a runtime property of the
signature. **No submission was made at 49, 50 or 51 slots**, so the boundary is not located.

### The produced VIDEO, decode-compared

From the 8-frame diagnostic. `outputs/S03/route/probe8.mp4`, 141,238 bytes, sha256
`44d24ef3bf04911afae2bdea67e6e12eb4701a11172d7d559f2ee329d6679097`.

Stream: **h264 (High), yuv420p, 1024×576, 16 fps**, duration 0.50 s. Decoded with the repo's
pinned ffmpeg to **8 frames** for 8 submitted.

| frame | identical | mean abs | max abs | pixels differing |
|---|---|---|---|---|
| 0 | no | 2.3390 | 36 | 99.42% |
| 1 | no | 2.2373 | 51 | 99.32% |
| 2 | no | 2.2555 | 43 | 99.25% |
| 3 | no | 2.2357 | 42 | 99.23% |
| 4 | no | 2.2258 | 46 | 99.34% |
| 5 | no | 2.4525 | 57 | 99.47% |
| 6 | no | 2.5359 | 60 | 99.50% |
| 7 | no | 2.4986 | 51 | 99.55% |

**Not bit-exact, and the error is structured**: on frame 0 the mean difference over the
top-10% gradient pixels is **12.19** against **5.28** over the bottom-50%. The save path is
`yuv420p` — the chroma-subsampling disease `GateRRoundTrip` exists for. Full record:
`outputs/S03/route/probe8_decode_compare.json`.

### The chain, link by link

| link | verdict |
|---|---|
| 81 pinned frames identified and hashed | **MEASURED** — n = 81, all distinct, gate_b statistics reproduced exactly |
| 81 frames uploaded | **MEASURED** — 81 distinct server names for 81 distinct frames |
| graph built in-repo, no partner node | **MEASURED** — 4 classes, all `api_node: false`, allowlist and topology gates passed |
| cost | **MEASURED** — 0 partner credits estimated; GPU/queue time metered separately and excluded from that figure |
| batch → `CreateVideo` **at 81 frames** | **FAILED** — `TypeError: unexpected keyword argument 'images.image50'`, evidence above |
| batch → `CreateVideo` **at 8 frames** | **MEASURED** — job completed |
| `CreateVideo(fps=16)` → `SaveVideo` → downloadable VIDEO | **MEASURED** at 8 frames — h264, 1024×576, 16 fps |
| decoded frame count equals submitted | **MEASURED** at 8; **not reachable at 81** |
| decoded pixels vs source | **MEASURED** — not bit-exact, structured at edges |
| the r2v node's runtime acceptance of a constructed VIDEO | **ASSUMED** — see §6 |

---

## 6. The named residual, in the dispatch's own words

**The r2v-acceptance link stays ASSUMED.** Whether `Wan2ReferenceVideoApi`'s
`reference_videos.video1` accepts a VIDEO constructed this way is **not provable at zero
credits**, was not probed, and is not claimed here. It is typed-compatible and never
executed. Task C cannot and does not claim it.

---

## 7. Uploads, cloud artifacts, and their deletes

| artifact | delete |
|---|---|
| 81 uploaded PNG frames (`outputs/S03/uploads.json`) | **no delete endpoint on this API surface** — content-addressed, inert unless a graph names them, persisting service-side (the E12 w2/w3 §7 convention) |
| 2 submitted jobs and their outputs (`973199a5…` failed, `e0047fc1…` completed) | no delete offered by this surface; the completed one's output is one 141 KB mp4 |
| saved cloud workflows | **none** — no workflow was saved to the cloud this session |
| local `outputs/S03/**` | delete the directory; owner: the executor session |

**Disclosure, per the per-route disclosure law.** Tasks A and B are **fully local — nothing
left the rig**. Task C uploaded 81 PNG frames of a clip Comfy Cloud itself generated (E12 w3
seed 1) back to Comfy Cloud, and submitted two jobs that executed there. The exposure delta
over the already-hosted source generation is the frames themselves. No partner/third-party
tier was touched: every node executed is core, `api_node: false`.

---

## 8. The meters

| | |
|---|---|
| `estimate_credits` | **0** — "no paid API nodes found in this workflow" |
| partner credits spent | **0** |
| jobs submitted | 2 (1 failed at execution, 1 completed) — GPU/queue time metered by the provider |
| uploads accepted | **81** |
| suite, this worktree (`S03-run`) | **1015 passed, 48 skipped** (1063 collected) |
| suite, `main` | **1005 passed, 13 skipped** (1018 collected) |

**Both counts are reported and nothing is asserted about the gap.** S03 adds 45 tests
(1018 + 45 = 1063 collected). The 35-test skip skew between worktree and `main` is the
instrument item E13 flagged and this session did not chase it; it is the same size here.

---

## 9. What was looked at, at full size

Recorded because nothing here is described unlooked-at.

- `turn_final/armfinal_0` and `armfinal_2` (the old set), before any render existed.
- All eight new views, `turn_0` … `turn_7`, individually at full size.
- The survey sheet `view_2.png`, old beside new.
- Frame 0 of the pinned A2 clip, for the coherence row.

---

## 10. The negative result, stated plainly

**The dispatch's chain does not carry 81 frames, and that is a full result.** It cost zero
partner credits to establish, and it is structural rather than a parameter that could be
tuned: `BatchImagesNode.execute()` refuses the 51st dotted slot, the catalog declares no
maximum, and the halt ruling's proposed rescue —
`uploaded PNG frames → the E02 batch mechanism → CreateVideo(fps=16) → reference_videos.video1`
— therefore has an unmeasured ceiling between 8 and 81 sitting in the middle of it.

What did hold is the rest of the chain: the frames upload, the graph is legal and free, the
batch executes below the limit, and `CreateVideo` → `SaveVideo` produces a downloadable
16 fps VIDEO whose pixels differ from the source only by the encoder. The links either side of
the failure are measured; the failure is one link, and it is the one E13's re-arming would
have hit on its first real submission.

Whether an 81-frame VIDEO can be constructed some other way — chained batches, a different
batch class, or a length the tier accepts — is a ruling, not a measurement, and is not made
here.
