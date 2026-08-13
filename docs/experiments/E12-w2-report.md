# E12 wave 2 — report: the world held on both seeds, and the figure did not

**Executor seat, 2026-08-12, branch `E12-run`, rebased onto `main` at `a3aa00f`.** Arm
**A2w** (full-bleed plate, authored shadow layer) at w3's pinned trajectory, **two seeds**.
**Two generations spent of the amended six-submission ceiling.** A1w was not submitted — the
Director ruled it broken at Gate LOOK, so its two submissions are unspent. **No gate fired.**

**No judgement of quality is offered or implied.** The Director judges the dance, the world
and the figure. What follows is what was submitted, what the gates said, what came back, and
what this seat looked at.

**Look first:** `outputs/E12/probe/seed1/seed1.mp4` and `seed2/seed2.mp4` at true tempo, and
`outputs/E12/sheets/E12-w2-seed1-face.png`, which carries the finding a number does not.

| | |
|---|---|
| seed 2026081233 | `prompt_id 2b15338b-9962-429a-b07c-4d9b8c410255` |
| seed 2026081241 | `prompt_id 34a113ae-af10-4b48-98e9-5d6f636d71c1` |

---

## 1. Premises, all resolved

| premise | status at dispatch | now |
|---|---|---|
| Cloud still serves the pinned camera files | ASSUMED | **MEASURED** — `search_models` returns exactly four `wan2.2_fun_camera` diffusion_model entries; both pinned `fp8_scaled` files present, the same four w3 measured |
| The startframe compositor may need an extension for a plate | ASSUMED | **MEASURED** — it did; three pieces, tests in the same commits |
| Candidate plate frames exist in w1's outputs at pickable quality | ASSUMED | **RESOLVED AGAINST** — every candidate carried wave 1's own mannequin; the Director supplied his own generation instead |
| w3's recipe reproducible from the E11 records | MEASURED | **re-checked** — 6 artifact hashes and 2 payload hashes recompute |
| Catalog 6.0 / uni_pc | ASSUMED | **still ASSUMED** — wave 3's rung, not this one's. The catalog re-stated it today |

## 2. One variable, proven by diff rather than asserted

Seed 1 carries **w3's own seed**, so its graph should differ from w3's in the start image
alone. Field-by-field it differs in **four**:

| node | field | w3 | E12 A2w |
|---|---|---|---|
| 40 `LoadImage` | `image` | `b2a9262d…png` | `265b1c17…png` |
| 41 `SaveImage` | `filename_prefix` | `E11/w3/startprobe` | `E12/w2/startprobe` |
| 71 `SaveImage` | `filename_prefix` | `E11/w3/lossless` | `E12/w2/lossless` |
| 81 `SaveVideo` | `filename_prefix` | `video/E11_w3` | `video/E12_w2` |

Only the first can reach the generation; the other three name server directories. They read
`E12/w2/` and not `E12/w3/` because `build_camera_i2v_payload`'s baked `WAVE = 3` literal was
parametrised first — the third time this repo has stripped a baked label, and the first time
one would have mislabelled server-side output directories that later runs read frames out of.

## 3. Gate states

**Before submission:** Gate LEDGER (4 deliberate breaks verified actual; trajectory held;
positive differs from wave 1's) · **Gate PAIR** (`families_present ['fun_camera']`) · Gate L
`PASS` · Gate S (seed pre-registered) · Gate ROUTE built · **saved-graph round trip** (51
values, 23 links, `50.clip_vision_output` and `80.audio` empty in both formats;
`control_after_generate` returned `fixed` on both samplers; Gate S "all pinned and all drawn
from the committed list of 2"; Gate L `1024x576x81 legal (PROVEN)`) · **pin check** ·
`estimate_credits` **0** on the real 18-node graph.

**Render gates on the A2w start frame:** Gate WHOLE (margin 26.6 px — *identical to w3's*),
Gate COVERAGE (0.0612), Gate ALPHA (0.9419 transparent), **Gate BACKDROP** (0.192/255 from
the plate against a 2.0 tolerance; 34.934/255 from the flat fallback it replaces).

**After submission:** **Gate B on both seeds** — batch intact, server decode **pixel-identical**
to the local composite, 81 painted frames each.

## 4. What came back, looked at

Every frame named was opened at full size; the strips are 3× native.

**The world held on both seeds, to the last frame.** At f8, f40 and f80 the bar is still the
bar: the back-bar shelving, the ring of patrons, the tiled floor, the magenta neon key. There
is no point on either clip where the room is replaced. That is the mirror image of E11 wave 1,
which replaced its world completely by f8.

**The figure degraded on both seeds, and differently.**

- **Seed 2026081233.** Coherent and sharp at f8. By f40 the face has doubled and smeared —
  two overlapping sets of features, no clean edge. By f80 the head is a blur with no face in
  it, and the arms have thinned. Limbs read longer at f80 than at f0.
- **Seed 2026081241.** Face still legible at f80 — brow, eye, nose, mouth line. But the
  screen-right arm has stretched into an impossibly long thin limb reaching out of frame, and
  the shoulder reads fibrous and melted.

**The crowd churns.** Individual background figures are not stable frame to frame; they ghost
and double under motion, most visibly at f40 and f80. *The room persists; the people in it are
repainted.* Those are different claims and only the first is a world-holding result.

**Contact.** At f8 and f40 both feet sit on the tiled floor with a soft painted contact shadow
under them, and read grounded to this seat's eye. This is the clause the amendment expected to
degrade.

**Hands — the Director's question, measured.** The conditioning image carries the mesh's
closed pincer. At **f8 on seed 1 the model has repainted it into an open hand with separated,
distinguishable fingers** — a better hand than the mesh's own, and unlike any E11 outcome
(wave 1's closed claw, wave 3's digits→wisps→stump). By f80 structure is gone again. ⚠ The
crop box is fixed and the hand leaves it at f40, so this strip does not cover the whole clip
and does not support a claim about the arc.

## 5. Measurements (diagnostics; they gate nothing)

| quantity | seed …233 | seed …241 | E11 w3 |
|---|---|---|---|
| frames / distinct | 81 / 81 | 81 / 81 | 81 / 81 |
| frame-delta median | 4.454 | 3.947 | 3.843 |
| \|Δ luma\| median | 0.322 | 0.268 | 0.148 |
| correlation with f0, last frame | 0.7348 | 0.8412 | 0.9247 |
| mean abs difference from f0, last | 22.481 | 15.971 | 14.067 |
| **horizon found on** | **0 / 81** | **0 / 81** | 70 / 81 |

> ⚠ **The horizon instrument returned nothing, and the camera claim is therefore NOT measured
> on this arm.** This was registered blind before submission, in those words: w3's horizon was
> a hard authored seam between a lit floor and a dark void — the easiest possible edge for a
> row detector — and A2w has no seam at all, only a soft tiled floor partly occluded by
> people. **0/81 is a detector limit, not a camera result**, and this seat will not convert it
> into one. H-E12d is unresolved and needs a different instrument.

> ⚠ Correlation-to-f0 is **not** like-for-like against w3. w3 held a nearly static authored
> studio; A2w holds a room full of moving people, where a lower correlation is what a
> *working* clip looks like. The number is reported, not read as a persistence ranking.

## 6. Predictions versus outcomes

Registered blind at `docs/experiments/E12-w2-predictions.md`, committed before
`submit_workflow`. Blind with respect to every E12 generation; **not** blind with respect to
E11, the A2w start frame, or the advisor's hypotheses — disclosed there and here.

| # | claim | degree | outcome |
|---|---|---|---|
| w1 | seed 1 world recognisably the same room at f80 | 75 % | **HIT** |
| w2 | seed 2 the same | 70 % | **HIT** |
| w3 | magenta/neon key legible to f80 on ≥1 seed | 80 % | **HIT** — both |
| w4 | neither seed replaces the crowd wholesale | 65 % | **HIT** |
| w5 | background faces NOT stable, they churn | 80 % | **HIT** |
| c1–c3 | horizon spread / count | 55–60 % | **NOT MEASURABLE** — 0/81, the caveat registered with them applies |
| n1 | contact reads wrong on ≥1 seed | 70 % | **MISS** — reads grounded at f8 and f40 on both |
| n2 | contact wrong on BOTH seeds | 50 % | **MISS** |
| n3 | figure slides/floats against the tile lines | 65 % | **NOT SCORED** — this seat did not build a tile-tracking instrument and will not score it by impression |
| i1 | face at f80 reads as the same character, both seeds | 70 % | **MISS** — holds on …241, gone on …233 |
| i2 | surface drifts smoother/waxier | 75 % | **HIT** |
| i3 | limbs read longer at f80 | 55 % | **HIT** on …233; …241 shows one arm grossly elongated |
| h1 | no clean five-fingered hand on either seed at any inspected frame | 92 % | **MISS** — f8 seed 1, separated fingers |
| h2 | ≥1 frame degraded further than the mesh's pincer | 80 % | **HIT** |
| h3 | failure mode differs between seeds | 55 % | **HIT** — head loss against arm elongation |
| q1 | credits 0 | 95 % | **HIT** |
| q2 | Gate B pixel-identical, both | 90 % | **HIT** |
| q3 | 81/81 distinct, both | 90 % | **HIT** |
| q4 | no gate fires after submission | 80 % | **HIT** |
| q5 | seeds differ visibly | 85 % | **HIT** |

**The h1 miss is the interesting one.** This seat put 92 % on the hands staying broken and was
wrong at f8 on the seed that shares w3's noise field. Given the same weights, trajectory and
seed as w3 — whose hands went digits→wisps→stump — the plate is the only thing that changed.
**One frame on one seed is an observation, not a route property**, and no claim about hands is
made from it.

## 7. What this run hands back, bounded

Wave 1 (plain I2V, grey-void start frame) replaced its world by f8. Wave 3 (camera tier,
authored void) held its world for 81 frames and delivered nothing, because the world was
nothing. **A2w (camera tier, photographic plate, full bleed) held a real room for 81 frames on
two seeds** — and the figure inside it came apart in two different ways.

Against w3 the single changed input is the start frame, so the world result is attributable to
it. **The figure's degradation is not attributable** — w3 degraded too, on the same seed and
settings, and this arm gives no way to separate "the plate is harder to hold a figure against"
from "this trajectory loses the figure by f40 regardless."

## 8. The meters

| | |
|---|---|
| `estimate_credits` | **0** (all-OSS; the ceiling is counted in generations) |
| generations spent | **2 of 6** — A1w's two unspent, ruled broken at Gate LOOK before submission |
| remaining | 4, of which wave 3 (6.0 / uni_pc, same two seeds) is the Director's next call |
| GPU / queue time | metered by the provider; to the ledger when the window resolves |
| suite | **950 passed, 48 skipped** (from w3's 827 / 46) |

**Uploads and cloud artifacts, with their deletes.**

| artifact | delete |
|---|---|
| upload `265b1c17…png` (the A2w start frame) | no delete endpoint on this API surface; content-addressed and inert unless a graph names it |
| saved workflow `e12-w2-camera-i2v-seed1.json` (round-trip admission only, never executed) | delete via the workflows UI / API; owner: the executor session |
| local `outputs/E12/**`, `outputs/_test_*` | delete the directories; owner: the executor session |

## 9. Open, for the ruling

1. **The camera lever is unmeasured on this arm.** The horizon detector returns 0/81 on a
   photographic plate. H-E12d needs an instrument that does not depend on an authored seam.
2. **A record defect, noted not fixed.** `build_camera_i2v_payload` writes
   `start_image.fit = "native — authored at 832x480, the same upload wave 1 ran"`. That string
   is false for w3 and for E12 — both ran 1024×576 — and it prints on the Gate 0 sheet. It is
   cosmetic, it was already wrong in w3's committed record, and this seat did not edit a
   builder after its graphs were submitted.
3. **A second stale figure**, from wave 1: the w3 report's comparison column gives wave 1's
   mean luma as `180.8 → ~60`; wave 1's own `measure/E11-clip.json` has f0 = 180.76 and
   f64 = **36.20**.
4. **Wave 3's rung is ready** — 6.0 / uni_pc on this world, same two seeds, 2 submissions,
   leaving 2. The catalog re-confirmed those settings today.
