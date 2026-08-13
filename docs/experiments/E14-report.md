# E14 — report: two style LoRAs on the held world, and they fail in different places

**Executor seat, 2026-08-13, branch `E14-run`.** Two arms, **two generations, the ceiling
reached exactly**. No re-runs. No gate fired. Predictions committed before the first
submission ([E14-predictions.md](E14-predictions.md), commit `05a27fb`).

**No judgement of quality is offered or implied.** Everything below is described. The
Director's eye rules the scene, the identity and the camera hold, separately.

**Look first:** `outputs/E14/sheets/E14-bakeoff-sheet.png` — baseline, arm T and arm S at
f0/f20/f40/f60/f80 with the reference plate, at full size.

| | |
|---|---|
| arm T — `technically_color` | `prompt_id 2fcc4091-41da-4f44-a6a7-eb25a0a95c66` |
| arm S — SmartphoneSnapshot v3 pair | `prompt_id 148304b0-4f20-45b8-a5b9-79fb6e850d1e` |
| baseline (not regenerated) | E12 w3 seed 1, `prompt_id bc390dc6-af02-45d1-9085-0df807430565` |

---

## 1. What ran, and the one thing that differed

Both arms are the **byte-pinned E12 wave-3 seed-1 graph** (sha256
`50a460b0…`) plus exactly two `LoraLoaderModelOnly` nodes. Gate LEDGER's verdict, identical
on both arms:

> 2 generation-reaching difference(s), all of them the LoRA insertions; 3 output-routing
> field(s) moved as named; every other field byte-identical to the baseline

The three output-routing fields are `filename_prefix` on nodes 41/71/81 — two arms cannot
write to one path. That classification was **declared in the tool before the diff ran**,
not chosen after seeing it, and it follows E12 wave 3's own precedent.

| | arm T | arm S |
|---|---|---|
| graph sha256 | `b6365d8a…` | `9aa69ebb…` |
| high-noise expert (sampler 60) ← loader 14 | `wan22-14b-t2v-technically_color.safetensors` | `WAN2.2-HighNoise_…v3_by-AI_Characters.safetensors.safetensors` |
| low-noise expert (sampler 61) ← loader 15 | the **same** file | `WAN2.2-LowNoise_…v3_by-AI_Characters.safetensors` |
| strength_model | 1.0 both | 1.0 both |
| Gate PAIR tier clause | **NOT VISIBLE** — one served file, no tier in the name | **tier-matched, verified from the served filenames** |

**Where the loader sits was measured, not assumed.** Both orders type-check. The served
`video_wan2_2_14B_t2v` template was read as a reference (never as a route) and its subgraph
MODEL links walked: `UNETLoader → LoraLoaderModelOnly → ModelSamplingSD3 → KSamplerAdvanced`,
with the lightx2v pair tier-matched high-to-high. Both facts are implemented.

**Arm T's tier is unresolvable and is recorded as such.** Its origin publishes a HN/LN pair;
the Cloud serves one file whose tier is not in the name, loaded on both experts. **One of
T's two attachments is necessarily tier-mismatched and nothing in the graph can say which.**
This is a live candidate explanation for anything odd in T and it is named here, not after
the fact.

## 2. Gate states

Both arms: **Gate LEDGER** (above) · **Gate ROUTE** built, `families_present ['fun_camera']`
· **Gate PAIR** camera pairing unchanged; tier clause per the table · **Gate S** seed
2026081233 pre-registered in `specs/E14-seeds.json`, committed ahead of the first submission
· **Gate L** unchanged from E12 (1024×576×81) · **Gate B** batch intact, decode
**pixel-identical**, 81 frames — on both arms.

**The credit gate: `estimate_credits` returned 0 before each submission** — "no paid API
nodes found". Zero partner credits, as specced. GPU-hour metered, no compensator; the
two-generation ceiling is the bound.

Gate B's pixel-identical verdict is the reused-upload claim **verified rather than
asserted**: the start frame that reached each arm's model is the same plate E12 used.

## 3. What came back, looked at

Frames inspected at full size, at f0/f40/f80 per arm plus the baseline's own.

**Both arms produced a legible transform. Neither returned a null.** The transfer premise —
the experiment's central measured question, marked ASSUMED — **bound visibly on both arms**.
A T2V-trained style LoRA reached the Fun-Camera derivative weights.

### Arm T — `technically_color`

- **Colour:** a strong, immediate warm push. Whites in the crowd's shirts read warm-tinted;
  the terracotta goes pinker and more saturated; the bar's blues and purples in the
  baseline's background are largely gone by f40.
- **The crowd converts.** At f0 the crowd reads human. By f40 several patrons have gone
  bald, jointed and clay-surfaced; by f80 the right side carries melted forms and a large
  bare-torso figure.
- **f80, structure hardest:** the figure's legs stay separate and both arms stay intact,
  but **the head carries a dark smear across it** and the face is much less legible than at
  f40. Hands taper out at both wrists.

### Arm S — SmartphoneSnapshot v3 pair

- **Colour:** far closer to the baseline than T. No comparable cast; the neutral-warm bar
  survives.
- **Rendering:** noticeably crisper than both baseline and T at f40 — the figure's edges,
  the face and the joints read sharply.
- **The crowd converts here too**, though the left foreground stays human; a mask-like face
  appears at the right edge from f40 on.
- **f80, structure hardest:** the **face stays legible** — eye, nose and mouth still read —
  but **the two legs have fused into a single column**. Arms extended, hands taper.

### The difference worth putting side by side

**Both arms degrade at f80, and they degrade in different places.** T keeps its legs and
loses its face; S keeps its face and loses its legs. The baseline at f80 does neither — E12's
record says the figure is coherent there, and looking at it confirms legs separate, face
legible, feet on the floor.

**The camera hold:** no push-in, drift or reframing was observed on either arm across the
frames inspected; framing at f80 matches f0 on both. The `Static` embedding is on a separate
conditioning channel from the weights the LoRA patches.

## 4. Diagnostics — these gate nothing

Single-run, no noise floor on this tier, **so no numeric claim rides them.** Recorded because
the spec says they ride the report.

| | frame_delta_median | abs_delta_luma_median | distinct frames |
|---|---|---|---|
| baseline | 8.745 | 0.425 | 81/81 |
| arm T | 11.158 | 0.566 | 81/81 |
| arm S | 7.352 | 0.414 | 81/81 |

`horizon_found_on 0/81` on all three. Full records in `outputs/E14/measure/`.

## 5. My predictions against what came back

Scored factually. **Ruling on what any of it means is the advisor's and the Director's, not
this seat's.**

| id | predicted | observed |
|---|---|---|
| P1 | arm T strongly legible; terracotta more saturated, blacks deeper | **matched on the warm/saturation clause.** "Deeper blacks" is not something I can claim from the frames inspected |
| P2 | arm S legible, and NOT the subtler of the two | **legible: yes.** "Not subtler" — on colour S is plainly the subtler; on rendering and on the f80 leg fusion it is not. The prediction was too coarse to score cleanly, and that is my fault in the writing |
| P3 | camera hold survives both | **matched** across frames inspected |
| P4 | transfer premise binds on both | **matched.** Neither arm is a null |
| P5 | arm T tier-mismatch artifact, unresolved | **still unresolved.** T's f80 face smear is *consistent* with it and equally consistent with three other causes. I am not attributing it |

**Where I was wrong, plainly.** I predicted S would apply the greater pressure to the
*subject* — that a photo-realism LoRA would pull the clay toward skin, and that if either arm
dissolved the character it would be S. **At f40 arm S's figure reads more cleanly as clay
than T's does**, and it is T whose face degrades by f80. My reasoning was that a grading
LoRA re-colours whatever surface it finds while a photoreality LoRA argues with the prompt
about what the surface is. That reasoning did not predict what came back.

## 6. Tool defects found and fixed, with tests

Two in `make_thesis_sheet.py`, both the same class — one experiment's meaning baked into a
literal:

1. **The reference plate was silently not drawn.** It was gated on the first row's label
   *starting with* `"CONTROL"`. E14's first row is a `BASELINE`, so the required
   four-column panel came out missing a column, with nothing reporting it. Now it rides the
   first row whatever that row is called.
2. **Captions fabricated a turnaround azimuth.** The default caption computed
   `az 360·i/n` — true for a turnaround, and a number that never happened on a video route,
   printed where a reader has no reason to doubt it. Azimuth is now opt-in.

Also removed: E03's measured prose about `WanVaceToVideo`'s `reference_image` socket,
hard-coded into the shared composer's `--reference=none` branch.

Four regression tests ride the commit. The first sheet built this session carried both
defects; the one in `outputs/E14/sheets/` was rebuilt after the fix.

## 7. Ceiling and what was not done

**Two generations spent, two authorised. No re-runs.** Both arms completed; no arm was lost
to a gate or a platform rejection.

Not done, deliberately: the strength sweep (the winner's follow-on, its own spec, two seeds)
· any second seed · any prompt change · any adoption ruling · any ruling on which look is
better.

## 8. Disclosure — an executor deviation, owned

Before this seat understood it had been handed the executor role, it **edited and pushed the
binding spec** (`182a98f`): the head candidates table, the dead-list, and two premise rows.
No experimental variable moved — arms, seed, strength, gates, graph and ceiling are all as
the pre-dispatch amendment set them at `e213103` — and the edits made the head table agree
with the amendment it had been contradicting. **It was still not an executor's call.** It is
recorded here rather than quietly left in the history, and it is the Director's to rule on.

## 9. Per-route disclosure

Unchanged from the spec, and now measured rather than projected: generation ran on Comfy
Cloud; the start image was already hosted and was **not** re-uploaded (Gate B confirms the
same plate reached both arms); the LoRA weights are cloud-served files that never touched the
rig; the only things that left the rig were the two graph payloads. Measurement, sheets and
frame inspection were fully local.

**Credit obligation, arm T:** the `technically_color` grant sets `allowNoCredit: false`.
**Any published footage from arm T carries a credits line for renderartist.** Arm S's grant
allows no-credit use.

## 10. Saved workflows

**None saved.** Both graphs were submitted directly from the in-repo builder in API format;
nothing was persisted to the workspace, so there is nothing to delete under the E12
convention. The executable record is `outputs/E14/route/{T,S}/E14-{T,S}-camera-i2v.api.json`
plus the payload records beside them.

## 11. Suite at close

`1006 passed, 48 skipped` — 1002 at the start of the session plus the 4 sheet regressions;
the 32 arm-builder tests were already in the first count. Both counts reported. **No claim
is made about the worktree skew** — this branch carries commits `main` does not.
