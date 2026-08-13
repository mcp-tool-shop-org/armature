# E12 wave 3 — report: the catalog settings held the figure and cost the crowd

**Executor seat, 2026-08-12, branch `E12-run`.** The settings rung: arm A2w, same start frame,
same two seeds, **cfg 3.5 → 6.0 and `sampler_name` euler → `uni_pc`, nothing else moved.**
**Two generations spent; 4 of 6. A1w's two remain unspent.** No gate fired.

**No judgement of quality is offered or implied.** The trade below is described, not ruled on.

**Look first:** `outputs/E12/look/E12-w2-vs-w3.png` — the same seeds and frames at both
settings, side by side at full size.

| | |
|---|---|
| seed 2026081233 | `prompt_id bc390dc6-af02-45d1-9085-0df807430565` |
| seed 2026081241 | `prompt_id 8bb9bf8d-41f6-475b-bbc5-c107ab1c38f1` |

---

## 1. Exactly two fields moved, proven by diff

Per the Director's instruction, field-by-field against the wave-2 graphs. **Both seeds, seven
differing fields each:**

| node | field | wave 2 | wave 3 |
|---|---|---|---|
| 60 `KSamplerAdvanced` | `cfg` | 3.5 | **6.0** |
| 60 `KSamplerAdvanced` | `sampler_name` | `euler` | **`uni_pc`** |
| 61 `KSamplerAdvanced` | `cfg` | 3.5 | **6.0** |
| 61 `KSamplerAdvanced` | `sampler_name` | `euler` | **`uni_pc`** |
| 41 / 71 / 81 | `filename_prefix` | `E12/w2/…` | `E12/w3/…` |

**Generation-reaching differences: 4, all of them `cfg` or `sampler_name`.** Steps, split,
shift, scheduler, length, resolution, prompt, negative and the `LoadImage` name are byte-identical
to wave 2. The start frame is the **same server image**, reused — no re-upload, and Gate B
re-verified it decodes pixel-identically on both runs.

## 2. The gate that had to be re-pointed rather than deleted

Gate LEDGER required flat equality with wave 1's trajectory — the one property E11 w3 held. This
rung moves two of its fields, so the unchanged clause would have halted an authorised wave and
deleting it would have been the thing the wave-2 postmortem named. The andon keeps its shape and
changes target: **fields not named in an override must still equal wave 1's; fields that are named
must actually differ.** Its verdict here:

> `4 deliberate breaks verified as actual; trajectory moved on cfg, sampler_name and held on
> 5 other field(s); positive still differs from wave 1's`

`steps`, `split_step`, `shift`, `scheduler` and `fps` are refused as overrides in code — moving one
would make the wave incomparable rather than informative. An override that sets a field to what it
already was is refused too, because a break that did not happen is wave 2's failure shape.

## 3. Gate states

Gate LEDGER · Gate PAIR (`families_present ['fun_camera']`) · Gate L `PASS` · Gate S
(pre-registered, drawn from the committed list of 2) · Gate ROUTE built · **saved-graph round
trip** — the cloud's own conversion read back with `["enable", 2026081233, "fixed", 20, 6,
"uni_pc", "simple", 0, 10, "enable"]`, so `uni_pc` survived the COMBO conversion and
`control_after_generate` came back `fixed`; 51 values, 23 links, both optional sockets empty in
both formats · pin check (four `fun_camera` entries, both pinned files present) ·
`estimate_credits` **0** · **Gate B on both seeds: batch intact, decode pixel-identical, 81 frames.**

## 4. What came back, looked at

**The figure held, on both seeds, and that is the visible change.** At wave 2 seed …233's face
doubled and smeared by f40 and the head was a featureless blur by f80. At wave 3 the same seed is
coherent at f40 and **still coherent at f80** — face legible (brow, closed eye, nose, mouth line),
ball joints clean, both arms intact, feet on the floor. Seed …241's wave-2 arm elongation does not
recur; at f80 the figure is whole, mid-stride, with a raised arm that keeps its proportions.

**The crowd converted toward the subject.** On seed …241, background figures become **clay
mannequins** — bald heads, ball-and-socket joints, terracotta surface — visible at f40 and
pronounced at f80, where several patrons are copies of the character rather than people. Seed
…233's crowd stays human across the frames inspected.

That is mechanistically legible rather than mysterious: cfg 6.0 is stronger prompt adherence, and
the positive's identity clause — *"a slender jointed clay mannequin, a smooth bald head… sculpted
thumbprint hatching…"* — **is not scoped to the subject**. Stronger adherence applied it more
widely. The prompt was byte-pinned by design, so this wave could not have avoided it; naming it is
the finding.

**The room itself held on both seeds** — back-bar, counter, tiled floor, magenta key all still
present at f80.

## 5. Measurements (diagnostics; they gate nothing)

| quantity | …233 w2 | **…233 w3** | …241 w2 | **…241 w3** |
|---|---|---|---|---|
| frames / distinct | 81 / 81 | 81 / 81 | 81 / 81 | 81 / 81 |
| frame-delta median | 4.454 | **8.745** | 3.947 | **10.188** |
| \|Δ luma\| median | 0.322 | **0.425** | 0.268 | **0.513** |
| correlation with f0, last | 0.7348 | **0.6032** | 0.8412 | **0.5915** |
| mean abs diff from f0, last | 22.481 | **32.886** | 15.971 | **30.628** |
| horizon found on | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 |

Every persistence number moved the same way: **roughly double the per-frame change, and a
markedly lower correlation to frame 0.** Read plainly, the wave-3 clips move more and end further
from where they started. This seat does **not** read that as "worse" — the figure is visibly
better preserved in the same clips — and offers it as the measured shape of the trade, for the
Director's eye to rule on. The horizon detector returned 0/81 again on both, as predicted; it
remains a detector limit on a plate with no authored seam.

## 6. Predictions versus outcomes

Registered blind at `docs/experiments/E12-w3-predictions.md`, committed before submission, with the
weakest blindness in the experiment disclosed there: a re-run of clips this seat had already seen.

| # | claim | degree | outcome |
|---|---|---|---|
| b1 | deformation visibly reduced vs wave 2, seed …233 | 55 % | **HIT** |
| b2 | same on …241; no arm elongated as before | 50 % | **HIT** |
| b3 | hands still fail at f80 on both | 85 % | **HIT** |
| b4 | …233's f80 head-loss does not recur | 45 % | **HIT** |
| w1 | bar still holds to f80 on both | 85 % | **HIT** |
| w2 | world result not degraded by the settings change | 80 % | **MISS** — the room held, but on …241 the crowd's *people* became mannequins, which is a world change this clause did not anticipate |
| w3 | crowd still churns | 85 % | **HIT** |
| q1 | credits 0 | 95 % | **HIT** |
| q2 | Gate B pixel-identical, both | 90 % | **HIT** |
| q3 | 81/81 distinct, both | 90 % | **HIT** |
| q4 | no gate fires after submission | 80 % | **HIT** |
| q5 | horizon still 0/81 | 85 % | **HIT** |
| q6 | frame-delta median moves < 1.0 | 50 % | **MISS** — it roughly doubled on both seeds |

**b1/b2/b4 were coin-flips and all three landed on the catalog's side.** This seat wrote that it
had "no mechanism that predicts reduction, only a catalog recommendation," and the recommendation
was right where the held trajectory was not. **The ASSUMED premise carried since E11 wave 3 —
that wave 1's cfg/sampler transfer to the Fun-Camera weights — resolves against the assumption.**

The w2 miss is the more useful one: this seat predicted the world was insulated from a sampler
change and it was not. *The room* was insulated; *the people in it* were not, because the lever
that preserved the subject also pushed the subject's description onto everything else.

## 7. The meters

| | |
|---|---|
| `estimate_credits` | **0** |
| generations spent | **4 of 6** (wave 2 ×2, wave 3 ×2). A1w's two unspent |
| remaining | **2**, unallocated — the Director's |
| suite | **962 passed, 48 skipped** |

**Uploads and cloud artifacts, with their deletes.**

| artifact | delete |
|---|---|
| upload `265b1c17…png` (reused for all four generations) | no delete endpoint on this API surface; content-addressed, inert unless a graph names it |
| saved workflows `e12-w2-camera-i2v-seed1.json`, `e12-w3-camera-i2v-seed1.json` (round-trip admission only; never executed) | delete via the workflows UI/API; owner: the executor session |
| local `outputs/E12/**`, `outputs/_test_*` | delete the directories; owner: the executor session |

## 8. Owed, and not yet done

**The deterministic re-lift check on the two E09 GLB pins remains OWED.** It was named as due
after this wave and has not been run; it is not reported here as done, and it is the first item
outstanding.

## 9. Open, for the ruling

1. **The settings premise is resolved against the held trajectory**, on two seeds, at one
   comparison. Whether 6.0/uni_pc becomes the arc's default is the Director's call, not this
   seat's — and if it does, every earlier number in the arc was measured on the other setting.
2. **The identity clause is unscoped.** The crowd-to-mannequin conversion is a prompt-scope
   problem the higher cfg exposed rather than created. A prompt that bounds the identity clause to
   the subject is the obvious next lever, and it is **out of E12's scope** — prompt changes are
   excluded by the spec.
3. **The camera lever is still unmeasured** on this arm; the horizon detector wants a seam the
   plate does not have.
4. Two stale strings from wave 2 still stand, unedited: the builder's `start_image.fit`
   ("authored at 832x480" on a 1024×576 run) and the w3 report's wave-1 luma endpoint.
