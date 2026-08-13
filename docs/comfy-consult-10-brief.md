# Comfy Agent consult #10 — brief: the LoRA lever on the free route (scene definition)

**From:** the armature advisor seat, 2026-08-13 · **Relay:** the Director carries this
brief to the Comfy Agent and returns its answer · **Trigger:** the Director's direction —
a future experiment measuring what a LoRA does to the free route's process ("a major
lever that can define a scene"); a LoRA on the camera graph is a new graph-component
class, the standing brief trigger. The catalog inventory and wiring conventions come
before any spec. · **Numbering:** file series (…8, 9 → 10).

**Round shape: knowledge only.** No tabs, no graph building, no generations, no credits.
Catalog facts and licence **documents** only — never verdicts; UNVERIFIED = NO stands.
**All model ids, node names and filenames in plain text, not code spans** (the #8
relay-mangling lesson). Mark NOT VISIBLE what the catalog does not say.

---

## Context — the experiment this feeds

The free route's pinned baseline (E12): an authored start image into the Wan
2.2-Fun-Camera dual-expert graph (high/low noise, two KSamplerAdvanced, cfg 6.0 /
uni_pc) with a Static camera embedding → 81 frames at 1024×576, GPU-hour metered. The
experiment: insert **one style/scene LoRA**, sweep strength against strength-0 on the
same two seeds and the same start frame, and measure what it does to the world, the
subject's identity, and the camera hold. Nothing runs until the licence rows for
whichever LoRA is picked are fetched and ruled.

## Already measured — calibrate against, do not re-derive

| item | state |
|---|---|
| The E12 baseline graph shape and settings | in-repo record (E12 route files); byte-pinned |
| LoraLoaderModelOnly exists and takes MODEL + lora_name + strength_model → MODEL | consult #9 (the Animate2 template carries one at strength 1) |
| The lightx2v distill LoRA row | the licence map — Apache-clean, **methodology-excluded as an accel**; it is NOT a style LoRA and is not this experiment's object |
| A LoRA inherits its base model's licence posture; every LoRA gets its own map row before it runs | the licence gate |

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Confirm LoraLoaderModelOnly's served
contract: inputs model (MODEL), lora_name (combo), strength_model (float) → MODEL. One
line if no drift; name exactly what moved if you see any.

**Q1 — the served Wan-LoRA inventory (the load-bearing question).** List the lora_name
option strings served for Wan-family models that are **style / scene / aesthetic**
LoRAs — not accel/distill, not motion-patch utilities. Exact filenames as saved, plain
text. If the catalog knows a LoRA's base (Wan 2.1 vs 2.2, T2V vs I2V), say so per
entry. If the list is long, the 10–20 most scene/style-shaped entries verbatim, plus
the total count.

**Q2 — wiring on the dual-expert graph.** For a two-expert Wan 2.2 graph (separate
high-noise and low-noise models): where does a LoRA attach — one loader per expert,
one on both, or a documented convention? Name any served template that demonstrates a
style LoRA on a Wan 2.2 dual-expert graph — template ids verbatim — and how many
loader instances it carries.

**Q3 — base-vs-derivative posture.** Is anything documented — node tooltips, template
notes, catalog metadata — about LoRAs trained on base Wan 2.2 T2V/I2V being applied to
**derivative weights** (Fun-Camera, Fun-Control, Animate)? Supported, cautioned
against, or NOT VISIBLE. Do not speculate about what "should" work.

**Q4 — the custom-LoRA path.** Does Comfy Cloud serve any mechanism to load a
**user-supplied** LoRA on the video tier — upload, HF-URL reference, private model
storage, anything? Exact node or mechanism names as served; NOT VISIBLE if none.
(Context, so the answer lands right: the studio trains its own image-model LoRAs and
will eventually want its own video-style LoRA; this question bounds that future — it
does not propose it.)

**Q5 — strength conventions.** Any documented strength ranges or conventions for Wan
style LoRAs — defaults, template-carried values, tooltip guidance — verbatim from what
is served, only.

## Halt conditions

Answer what the catalog and visible documents support; mark everything else NOT
VISIBLE. No speculation, no substitutions of "equivalent" models, no licence verdicts,
no builds. If a question would require building or running anything, stop at naming
what it would take.
