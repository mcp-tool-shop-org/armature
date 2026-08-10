# E02 — report (PARTIAL — halted before any credit was spent)

**Seat:** executor · **Written:** 2026-08-10 · Spec:
[E02-first-contact.md](E02-first-contact.md) · Predictions:
[E02-predictions.md](E02-predictions.md) (committed `95e2dd2`, before any submission).

**Status: HALTED at the upload bridge. Zero credits spent. Zero generations submitted.**
The stop is not a gate firing on our output — it is the spec's chosen bridge measuring as
unavailable. Everything that did not depend on that bridge was completed and is reported
below; everything that did is `NOT YET RUN`.

---

## 1. Subject extents (premise 6) — measured, first, before anything else

`blackguard_unirig_rigged.glb`, sha256 `404e8445…b47a8`, opened in Blender 5.2.0 LTS:

| | X | Y | Z | longest/shortest | longest/middle | longest axis |
|---|---|---|---|---|---|---|
| **blackguard (E02 subject)** | 0.6033 | 0.3100 | 1.0013 | **3.23** | 1.66 | Z |
| *E01's `longsword_hero.glb`, for contrast* | 0.226 | 1.002 | 0.063 | 15.9 | 4.43 | Y |

It is a standing figure. The measurement is an independent import, and it matches E01's
`runF_blackguard` manifest half-extent to every printed digit.

**The E01 defect is still live and still worth showing.** `probe_subject.py` also reports
what the naive `type == "MESH"` selection would have concluded on this same asset:

```
naive selection:   1.9021 x 2.0000 x 2.0000   aspect 1.05   bounding sphere 1.0000
correct selection: 0.6033 x 0.3100 x 1.0013   aspect 3.23   bounding sphere 0.5483
```

The hidden `glTF_not_exported` Icosphere turns a 3.23:1 figure into a 1.05:1 near-cube and
nearly doubles the bounding sphere — which is what silently mis-framed the camera in E01.

## 2. Premise 1b — resolved, and both graphs agree

Read from the graphs' widget values, which is the check the spec's amendment demanded:

| graph | node | width | height | length | other |
|---|---|---|---|---|---|
| `armature-E02-vace-control` | 49 `WanVaceToVideo` | **480** | **832** | **33** | `strength` 1.0, `batch_size` 1 |
| `armature-E02-funcontrol` | 160 `Wan22FunControlToVideo` | **480** | **832** | **33** | **no `strength` widget exists** |

Premise 1b is confirmed. E01's blackguard run was 512×768, so the control sequence was
re-rendered at 480×832 for E02 (`outputs/E02/control_480x832/`, G1/G2/G4 all PASS, G4 max
delta 1 px against a 2 px tolerance).

## 3. Two spec claims corrected by measurement

**Stage 3 trap 1 was already closed.** The spec requires the VACE `Canny` node (id 147) be
bypassed. It already is — `mode: 4`, and the server's own api_format conversion omits node
147 entirely and wires `GetVideoComponents → control_video` directly. Nothing to do.
Traps 2 (template prompts) and 3 (node 149's stale CausVid markdown) remain open as
described.

**Premise 1a's evidence covered only half its claim.** The premise reads "*Both* graphs
exist on Cloud and are licence-clean — MEASURED", and the evidence quoted is entirely about
VACE ("24 nodes… no LoRA loader of any class"). The Fun-Control graph was never checked and
**contains two `LoraLoaderModelOnly` nodes** (181, 182).

Measured, they are `wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise.safetensors` — the
lightx2v speed-LoRAs, which `docs/license-map.md` records as **Apache-2.0, commercially
clean**, excluded on methodology rather than licensing grounds. Both are `mode: 4`
(bypassed) and sit inside a **second, wholly bypassed pipeline** (nodes 163–182, a 4-step /
cfg-1 variant). The active pipeline is the 20-step / cfg-3.5 route and touches neither.

**So the verdict survives and the evidence did not.** This is the fifth instance in this
repo of a premise marked `MEASURED` on a check that did not cover the property claimed —
this time the unmeasured half happened to be clean. Two things for the advisor, neither of
them mine to rule:

1. `docs/license-map.md` sources the lightx2v row to *Comfy consult #1*, not to a retrieved
   licence document. Under the gate's own words — "a licence that cannot be retrieved is
   UNVERIFIED, treated as NO" — that row is an assertion, not a retrieval.
2. The map's ruling "bypassing is not removal — delete it" was written for *non-commercial*
   nodes, so it does not fire here on its own terms. Whether it should be widened to any
   methodology-excluded node is a ruling, not a measurement.

## 4. Registered predictions

In [E02-predictions.md](E02-predictions.md), committed `95e2dd2` at
`2026-08-10T17:20:14-04:00` — before any submission. **Blind to every generation output**
(none exists); **not blind** to the graphs' configuration, because premise 1b required
reading it first. P2's magnitude clause is registered as SUSPENDED with reasons rather than
given an invented threshold.

## 5. Gate R — PASS, and it falsified one of the spec's own options

The spec offers two encodings. Both were measured, against **two** probes — a grayscale one
and a true-RGB one — because a grayscale probe cannot detect the failure this gate exists
for.

| encoding | container | grayscale probe | true-RGB probe |
|---|---|---|---|
| **`ffv1 -pix_fmt gbrp`** (spec's preference) | mkv | **lossless** | **lossless** |
| `ffv1 -pix_fmt bgr0` | mkv | lossless | lossless |
| `libx264rgb -qp 0` | mkv | lossless | lossless |
| `libx264 -qp 0 -pix_fmt yuv444p` (**spec's stated fallback**) | mp4 | max\|Δ\| **1** | max\|Δ\| **2** |
| `libx264 -qp 0 -pix_fmt yuv420p` (the named trap) | mp4 | max\|Δ\| **1** | max\|Δ\| **233** |

Three findings:

- **The spec's fallback is not lossless.** `-qp 0 -pix_fmt yuv444p` loses 1–2 levels: 4:4:4
  removes *subsampling*, but the RGB→YUV→RGB matrix still rounds. The spec offers it as an
  equal alternative; it is not one.
- **The trap is real, and is now measured rather than inferred.** `yuv420p` differs by 1 on
  grayscale and **233** on true RGB — a bridge that would look almost perfect certified on
  depth and destroy the normal channel, exactly as the spec predicted.
- **`ffv1 -pix_fmt gbrp` works**, although this ffmpeg build's `-h encoder=ffv1` does *not*
  list 8-bit `gbrp` among its pixel formats. I read that help text first and concluded the
  format was unavailable. That conclusion was wrong: the encode is the authority, not the
  help text.

**Gate R verdict on the artifacts actually built: PASS.** 33 frames each, zero pixel
difference through encode→decode, receipts beside the files:

```
A1a_depth_pershot_nearbright.mkv   sha256 7481c4378a8268cf…   33 frames   Gate R PASS
A1b_depth_pershot_neardark.mkv     sha256 38a295b725973dfa…   33 frames   Gate R PASS
```

**A parameter the spec did not arm, chosen by me and flagged for overrule.** E01 shipped
per-frame and per-shot depth normalisation and deliberately refused to name either
`depth/`; the E01 ruling deferred the choice to E02, but E02's arms are polarity, no-control
and implementation — normalisation is not among them. I used **per-shot**, because per-frame
re-maps the range every frame, so on a 360° orbit the figure's brightness pulses while the
geometry stands still, injecting a temporal signal into a *video* control input. That is a
mechanism argument, not a measurement, and it is the advisor's to overturn.

**A1b is one operation on A1a.** Full-image `255 − x`. Because `BACKGROUND_DEPTH = 0.0`
(black = far), inverting sends the background to 255, which in the near-dark convention
still reads "far" — so the plain inversion is also the semantically correct near-dark map,
and the two arms differ by exactly one transform on identical geometry.

## 6. Gate L — PASS

`g1_generator_legality(480, 832, 33, "wan-vace")` passes: 480 and 832 both divisible by 16,
33 ≡ 1 (mod 4). It is a real gate, not a formality — it raises on frame count 32, on width
470, and on height 830, and it **raises on the generator name `wan-fun-control`**, which has
no profile row. A3 therefore needs a profile entry with a retrieved source before it can
run; the andon is correctly on the direction where nothing would otherwise be checked.

Gate L already existed as E01's G1. It was not rebuilt.

## 7. THE HALT — the spec's control bridge does not exist

The spec's Stage 0 states: *"There is no folder loader on Comfy Cloud … so encoding is the
only supported bridge and this gate is the price of it."* Gate R proved the encoding is
sound. **The delivery is not.**

Measured, three probes chosen to discriminate between "the upload path is broken" and "video
is refused":

| file | result |
|---|---|
| `A1a_…nearbright.mkv` (FFV1) | `{"status":"tool_error","error_type":"validation.input"}` |
| `probe_x264rgb.mp4` (H.264) | `{"status":"tool_error","error_type":"validation.input"}` |
| `depth_pershot/00000.png` | **accepted** — returned a signed single-use PUT URL |

The upload path is alive; **video files are refused by extension**. `upload_file` documents
`.jpg/.jpeg/.png/.webp/.gif` only, and both a Matroska and an MP4 container are rejected
identically.

**Bridges enumerated before concluding** (the repo's rule is to enumerate before
commissioning):

| bridge | status |
|---|---|
| `upload_file` → `LoadVideo` | **BLOCKED** — video extensions refused |
| folder loader | absent (spec verified independently at spec time) |
| URL/remote loader in core | none found |
| `VHS_LoadVideo` (videohelpersuite) | reads the same server input folder we cannot write a video into |
| **33 × `LoadImage` → `BatchImagesNode` → `control_video`** | **available**, and lossless by construction |
| Director uploads a video by hand in the Cloud web UI | possible, needs the Director |

`control_video` is typed `IMAGE` on both `WanVaceToVideo` and `Wan22FunControlToVideo`, so a
batch of images is a first-class input, not a workaround. `BatchImagesNode` is a core node
whose `images` input is an auto-grow list.

### Why this is referred up rather than decided

The PNG-batch payload is built and its topology verified in code
(`outputs/E02/payloads/A1a_vace_pngbridge.json`, 47 nodes, 34 `LoadImage`, no dangling
links, control_video fed by the batch, video-bridge and Canny nodes absent). It also passes
`dry_run`. **That is not sufficient evidence to spend on**, for two reasons:

1. `dry_run` accepted a `LoadImage` naming a file that does not exist, without a warning —
   so its silence is weak evidence, exactly as CLAUDE.md warns. Whether `BatchImagesNode`
   truly batches all 33 or silently takes the first can only be settled by execution.
2. Adopting it replaces `LoadVideo` + `GetVideoComponents` with 34 nodes in **both** graphs.
   The spec pins those graphs by parsed content and rests its PIN_PER_STEP score on them.
   Re-topologising a pinned artifact is a ruling, not an execution detail.

Spent credits have no compensator, which is precisely why the seat that redesigned the
bridge should not also be the seat that decides the redesign is sound.

### Gate C could not be pre-computed, and that confirms the spec's design

`estimate_credits` on the E02 graph returns **0 — no paid API nodes found**, and its own
caveats exclude GPU and queue time. Wan runs as open weights, so its entire cost is the GPU
time the estimator excludes. **There is no way to price an arm before running one**, which
is exactly why the spec made Gate C a one-submission-then-halt andon rather than an estimate.

## 8. Gate and arm status — nothing written that has not run

| item | verdict |
|---|---|
| Premise 6 — subject extents | **MEASURED** — figure, 3.23:1 |
| Premise 1b — graph dimensions | **MEASURED** — both 480×832×33 |
| Premise 1a — Fun-Control licence | **MEASURED** — clean, but the premise's evidence had not covered it |
| Gate R — round trip | **PASS** (ffv1-gbrp, both arms, 0 px) |
| Gate L — frame legality | **PASS** (480×832×33) |
| Gate C — credit bound | **NOT YET RUN** — blocked by the bridge |
| A0 — repeat variance / noise floor | **NOT YET RUN** |
| A1a / A1b — depth polarity | **NOT YET RUN** |
| A2 — no control (the thesis test) | **NOT YET RUN** |
| A3 — Fun-Control | **NOT YET RUN** (also needs a `wan-fun-control` G1 profile row) |
| Gate 0 — the sheet | **NOT YET RUN** — no output exists to sheet |
| P1 · P2 · P3 · P4 | **NOT YET MEASURED** — registered only |

**Credits spent: 0. Generations submitted: 0. Uploads that succeeded: 0** (the PNG upload
returned a URL; the PUT was not executed, so nothing was transferred).

## 8b. A second input the spec did not name — found, and not a blocker

Every arm needs a `reference_image` (A2 is defined as *"same prompt, same reference, no
control video"*, so the reference is held constant across arms and cannot be omitted). The
spec never says where it comes from. Enumerated rather than commissioned — four plates
already sit beside the subject GLB:

```
blackguard_apose_{0,1,2,3}.png    RGB, 1024x1024, no alpha
```

So no reference needs generating. **Whether these depict the same character as
`blackguard_unirig_rigged.glb` is not something I can settle** — a shared filename stem is
exactly the kind of evidence this repo has been burned by twice, and identity is canon and
the Director's. They are named here as the candidates, with their measured properties, for
his eye. E05 owns reference count and identity; E02 needs only that one exists, and one does.

## 9. Tests

121 pass (E01's 103, plus 10 for `subject.py` and 8 for Gate R), and **121 pass under `-O`**
— the gates are not `assert`s and do not evaporate under `PYTHONOPTIMIZE`.

One test caught a claim of mine that was wrong. `subject.py` first argued that using
longest/middle as the discriminator "collapses the distinction" and would let a blade pass
for a figure. Measured: 4.43 vs 1.66, a 2.7× separation against longest/shortest's 4.9×. It
separates less well; it does not collapse. I asserted a ratio instead of computing it, which
is the same family of error this repo keeps recording. Both the module and the test now
carry the measured margins.

## 10. What the advisor is being asked to rule

Stated contrastively, since that is what the standard asks for.

**You probably expected** Gate R to be the risk in Stage 0 — a lossy encoder silently
corrupting the normal channel. It was not: the encoder is fine, and the spec's own preferred
setting is the one that works.

**What actually blocks E02** is one layer further out: the encoded file cannot be delivered
to Cloud at all through the available tooling, so the bridge the spec called "the only
supported" one does not exist. The question is therefore not *which encoding* but *which
bridge*:

- **(a)** adopt the PNG-batch bridge as a documented deviation — lossless by construction,
  no encoder in the path at all, Gate R becomes N/A rather than PASS for the arms that use
  it; costs a re-topologised graph and one cheap execution to confirm batching semantics;
- **(b)** have the Director upload the control videos by hand through the Cloud web UI,
  keeping both pinned graphs byte-for-byte as built;
- **(c)** something else.

I have not chosen. The measurements for each are above.

---

# E02 — report, part 2 (resumed after the halt was lifted)

**Bridge (a) adopted per [E02-halt-ruling.md](E02-halt-ruling.md). Canon settled per
[E02-canon-ruling.md](E02-canon-ruling.md).** Rebased on both. One generation submitted,
then halted, exactly as Gate C specifies.

## 11. Gate B — PASS, but built on a different quantity than the one specified

**The check the ruling named cannot fire.** It asks Gate B to assert "the output frame
count equals the submitted control frame count". Traced before implementing:
`WanVaceToVideo` truncates or pads `control_video` to `length` and emits `length` frames
regardless — so a 1-image batch and a 33-image batch **both** yield 33 output frames. The
quantity does not move when the defect is present, and this repo's own law is that a check
that cannot fail is not a check.

Implemented instead against the quantity that does move: a `SaveImage` wired directly to
`BatchImagesNode`'s output, so the batch is observed *as the sampler received it*. This
still honours the ruling's principle — verify from an output, never from the absence of an
error — and it rides the same single submission the ruling asked for.

| | |
|---|---|
| submitted control frames | 33 |
| images returned by the batch probe (node 301) | **33** |
| **Gate B** | **PASS — batch intact** |

The gate binds in both directions (`!=`, not `<`), so a duplicated auto-grow link fires it
too. `test_the_rejected_check_could_not_fire` pins the reasoning in executable form so the
weaker check is not re-derived later.

## 12. The autogrow encoding — and dry_run's third failure

The first submission was **rejected by the server before executing**:

```
node 300 BatchImagesNode: required_input_missing, details "image0",
input_name "images.image0"
```

`COMFY_AUTOGROW_V3` slots are **dotted keys** — `images.image0`, `images.image1`, … — not
a list of links under a bare `images` key. **The list form passed `dry_run` clean**:
`{"status":"validated","warnings":[]}`.

That is the **third measured instance in E02** of `dry_run` validating something the real
path refuses. The first two were a `LoadImage` naming a file that does not exist, accepted
without a warning. This one is stronger: a structurally invalid graph, validated silently.
CLAUDE.md already says a `dry_run` PASS does not prove link sanity; E02 now has receipts.

**Cost of learning it: zero.** The rejection happened at prompt validation, before the
worker ran, and no GPU-hours bucket appeared. `verify_topology` now rejects the bare-list
form by name so it cannot come back quietly.

## 13. "Lossless by construction" is FALSIFIED as stated — measured, with the mechanism

The ruling chose bridge (a) partly because it is *"lossless by CONSTRUCTION rather than by
measurement — there's no codec left to prove anything about."* The first half is true: there
is no codec. **The conclusion does not follow, and the measurement says so.**

Comparing the 33 probe images (the batch as the sampler received it) against the 33 local
source PNGs:

| | |
|---|---|
| frames compared | 33 |
| frames differing | **33 of 33** |
| max abs delta | **1** |
| distinct signed deltas | **{−1, 0} — never +1** |
| background (src 0) | 36,656,196 px, **100.000% unchanged** |
| subject (src > 0) | 2,880,444 px, **100.000% exactly 1 lower** |

The relationship is a pure deterministic function of the source value:

```
out = max(src - 1, 0)        exact for every value present;  0 -> 0,  254 -> 253
```

**Two candidate mechanisms; I tested one and killed it.** My first hypothesis was ComfyUI's
`SaveImage` truncating a float32 round trip (`astype` floors rather than rounds).
Reproduced locally: float32 `x/255 x 255` recovers **all 256 values exactly**, predicting
zero loss. Falsified. What survives is a **255-vs-256 divisor mismatch** somewhere in the
path — `floor(255 * v/256)` reproduces `max(v-1, 0)` exactly — but *where* it sits I cannot
determine from this run.

**What I cannot separate, stated plainly:** whether the −1 is applied on **ingest** (the
sampler genuinely received `src−1`) or only on **save** (the sampler received `src`, and my
probe is the thing that shifted). The probe is the only window onto the batch, so it cannot
observe itself. Separating them needs a second run driven by a known synthetic ramp, and
that costs credits, so it is not mine to authorise.

**What is true either way:** the offset is uniform, one-sided, deterministic, and applied to
every non-background pixel identically. A constant offset preserves every gradient in the
depth map, so the control's *structure* is intact and only its absolute level moves by
1/255 (0.4%). Whether that matters to the model is not a question a measurement answers —
but "lossless" is the wrong word for the observable bridge, and the record should not carry
it.

## 14. Gate C — HALTED, and the cost is NOT YET OBSERVABLE

One generation submitted (`prompt_id 382dbb1f-57e6-47b2-a80b-2e675b35db11`), completed, and
halted. The arithmetic Gate C asks for cannot be done yet:

- `estimate_credits` returns **0 — no paid API nodes**. Wan runs as open weights, so its
  entire cost is the GPU time that estimator explicitly excludes.
- The **invoice-backed usage report has not moved.** `GPU Hours Product` reads
  **$12.253086 both before and after** the run, and the 2026-08-10 bucket carries no
  GPU-hours entry at all — while the job demonstrably occupied a GPU for roughly five
  minutes of wall clock.
- **No cost, credit, duration or billing field exists anywhere on the job record.** Its
  fields are `source_node_id`, `filename_prefix`, `class_type`, `filename`, `url`,
  `suggested_save_path`, `download_command`.

The provider's billing lags, so **the number Gate C needs does not exist yet**. I am not
inventing one, and not estimating one from adjacent days — a per-day GPU total containing an
unknown number of runs is not this run's cost. **Gate C stands OPEN**: one submission made,
arithmetic pending an observable figure, and the projection against the 12-generation
ceiling waits on it.

## 15. Gate 0 — the sheet exists

`outputs/E02/sheets/E02-A1a-gate0.png` — control | output | reference | provenance, native
480x832 in both rows with no resampling, plus the 33-frame clip and all 33 stills.
Delivered to the Director. **No arm metric is quoted anywhere above**: sections 11-14 are
gate verdicts and bridge measurements, which is the ordering Gate 0 governs.

## 16. Status after part 2

| item | verdict |
|---|---|
| Gate L (incl. the new `wan-fun-control` row) | **PASS** |
| Gate B — batching | **PASS (33 of 33)** |
| Gate R | **N/A for this route** — retained in the tree with its 18 tests |
| Gate C — credit bound | **HALTED — cost not yet observable** |
| Gate 0 — the sheet | **BUILT** for A1a |
| A1a | **RUN** — one generation |
| A0 (noise floor, 3 repeats) | **NOT YET RUN** |
| A1b · A2 · A3 | **NOT YET RUN** |
| P1 · P2 · P3 · P4 | **NOT YET MEASURED** |

**Generations submitted: 1** (plus one server-side rejection that never executed).
**Credits spent: one generation's worth, unpriced.**

Tests: 130 pass, including under `-O`.

---

# E02 — report, part 3: the lossless tap, A0, and A2

Four generations (ledger: **6 of 12 spent, 6 left**). Prompt ids `1beb4773` (A0r1),
`d2d68367` (A0r2), `82e2fbea` (A0r3), `626e6531` (A2).

## 17. The lossless output tap

`SaveImage` on node 8 (`VAEDecode`), alongside the existing `CreateVideo`/`SaveVideo` path.
No extra generation — the same frames, taken before any codec. `verify_topology` now fails
a payload whose tap is not wired to node 8, so a floor cannot be measured through H.264
again by accident.

## 18. Codec contamination — measured directly, and it is large

One generation emits both the lossless frames and its own H.264 copy, so the codec error
can be measured with **zero model variance in it**:

| A0r1 lossless vs A0r1's own H.264 | |
|---|---|
| per-frame max abs delta | min **43** · median **52** · max **64** |
| per-frame mean abs delta | median **1.73** |

That is the same order as the entire provisional floor. Two caveats kept in view: H.264
error is a deterministic function of content, so it partly cancels when two *similar*
videos are differenced, and max-delta is not additive. So this alone does not overturn the
earlier number — it establishes that the codec is not a negligible term at this magnitude.

## 19. A0 — the noise floor is EXACTLY ZERO

Precondition checked first, because a floor measured on runs with different inputs is not
a floor: **the control input was byte-identical across all three runs** (max abs delta 0
over 33 frames, all three pairs), and the `max(src-1,0)` bridge offset reproduced
identically in each. So what follows is model variance and nothing else.

| A0, three identical submissions, **lossless** frames | |
|---|---|
| pairs compared | 3 (r1\|r2, r1\|r3, r2\|r3) |
| frames identical | **33 of 33, every pair** |
| **pairs bit-identical** | **3 of 3** |
| per-frame max abs delta | **0 at every frame index** |
| px differing by >8 | **0.000%** |

**The floor is zero, and it is zero at every frame index** — there is no shape, because
there is no variance. Reported per-index anyway, as instructed, so the absence is legible.

### Verified hard, because the claim is large

1. **Three genuinely distinct jobs** — 201 distinct download URLs, no reuse; video outputs
   `E02_A1a_00001/2/3` with three different sha256 and three different byte sizes.
2. **The videos differ while the frames do not.** Same source frames, three different mp4s.
3. **Cross-checked against the first A1a generation** (`382dbb1f`, a separate job with no
   tap): its H.264 differenced against A0r1's lossless gives median max 52, range 43-68 —
   the *same* distribution as A0r1's own H.264 against its own lossless. So that earlier
   generation produced the same frames too. Determinism holds across jobs, not just within
   this batch.

### The provisional floor was measuring the codec — reproduced exactly

Differencing **the same two runs** two ways:

| | max abs delta |
|---|---|
| on **lossless** frames | **0** at every frame |
| on **H.264** frames | min 1 · median 15 · max 56 · px>8 0.123% |

and the H.264 shape by frame index:

```
f000..f032:  1  3  3  2  1 11 11  6  2  9 15 13 16 20 18 17 13 13 11 12 12 47 47 49 31 50 52 56 55 54 54 52 55
early f0-4  : [1, 3, 3, 2, 1]
late  f29-32: [54, 54, 52, 55]
```

That reproduces the provisional floor's reported shape — early near-identical, late in the
50s-70s — from frames that are **provably identical**. The mechanism is H.264 encoder
nondeterminism accumulating away from the keyframe: early frames sit next to an I-frame and
encode almost the same way twice; later P/B frames diverge as rate-control state drifts.

**So the provisional floor was correctly measured and was measuring the encoder.** Its
numbers stand as a characterisation of the review path. They are not the provider's
variance, and the "floor is a function of frame index" finding is a property of H.264, not
of Wan.

**Consequence:** on lossless frames there is **no floor to subtract**. Arm-to-arm
differences can be read directly. The early/late split remains mandatory for anything read
off a video, and is moot for anything read off `lossless/`.

### P1 — registered blind, and I was wrong

| clause | registered | measured |
|---|---|---|
| A — bit-identical pairs of 3 | **0** | **3** |
| B — mean abs delta of closest pair | 12/255 | **0** — no difference exists |
| structural claim — "bimodal, lands on the far mode, >5/255 not <2/255" | predicted far mode | **neither mode; there is no divergence at all** |

The reasoning behind the structural claim — diffusion is chaotic, so any early perturbation
amplifies rather than averages out — was sound *conditional on there being a perturbation*.
There is none. I registered the possibility of exactly this outcome ("if the provider pins
GPU model, container and kernel selection, 3/3 bit-identical is entirely plausible and I
would not be surprised") and still put 0 as the number, so the miss is on the number and
not on the reasoning.

## 20. A2 — the no-control row, and the null is NOT empty

Same prompt, same reference image, same seed, `control_video` absent (14 nodes; no
`BatchImagesNode`, verified in code before submission).

**A2 also produces a horned armored figure that turns.** That is the finding that makes A2
load-bearing: the A1a sheet on its own could never have distinguished "control worked" from
"the prompt and reference alone produce a turning armored figure", because the latter is
what A2 shows they do.

The panel is `outputs/E02/sheets/E02-thesis-A1a-vs-A2.png` — one control row, two output
rows, same five frame indices. Delivered to the Director with both clips at 8fps.

### Diagnostic — motion *timing*, gating nothing

Estimator-free, so no licence question: per-frame temporal energy
`d(t) = mean|frame(t) - frame(t-1)|`, then correlated against the control's own profile.
Floor and ceiling stated before reading: identical repeat runs give 1.000 by construction;
an arm ignoring the control gives ~0.

| | corr with control |
|---|---|
| **A1a** (control present) | **+0.521** |
| **A2** (no control) | **−0.064** |

**This does not answer P3.** P3 is *same place at the same time*, and that is an eye check
on the panel. This says only whether the clips move at the same moments. It is a diagnostic
and it gates nothing.

## 21. Status

| item | verdict |
|---|---|
| lossless tap | **BUILT**, enforced by `verify_topology` |
| A0 — noise floor | **ZERO on lossless frames**, 3/3 pairs bit-identical |
| provisional floor | **overturned** — reproduced as H.264 encoder nondeterminism |
| A2 — no-control | **RUN**; the null is not empty |
| Gate 0 sheets | A1a **BUILT**, thesis panel **BUILT** |
| P1 | **MEASURED — registered 0, measured 3. Wrong.** |
| P2 · P3 · P4 | **NOT YET MEASURED** (A1b and A3 unrun) |
| ceiling | **6 of 12 spent, 6 left** |

Review artifacts are 8fps (0.5x) from here on. Generation untouched.
