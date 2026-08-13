# Comfy Agent consult #10 — answer, calibration, ruling

**Brief:** `docs/comfy-consult-10-brief.md` (the LoRA lever on the free route — scene
definition). **Relayed by the Director, answered and ruled the same day, 2026-08-13.**
Round discipline held: knowledge only, zero credits, documents never verdicts. The
relay's elision struck the inventory despite the plain-text request — the agent's read
was complete; the relay dropped literals; our own uncapped `get_node` restored every
one (calibration below).

---

## The agent's answer (as relayed; elided literals marked)

> **Q0.** No drift on LoraLoaderModelOnly: model + lora_name + strength_model → MODEL.
>
> **Q1.** The lora_name combo is one shared list (~450 entries [see calibration: 646]).
> Wan-family style/scene entries, excluding accel/distill (lightx2v, CausVid, AccVid,
> FastWan, Lightning, Turbo, rCM, self-forcing, DMD), motion/control utilities
> (VACE-ditto, SCAIL, Skyreels, CineScale, Stand-In, UniAnimate, EchoShot, Pusa,
> AniSora, relight, InP-reward) and RGBA/alpha: ≈19 entries — several arrived with the
> prefix elided to "the model-", two fully blanked [all restored below]. Every style
> entry is T2V-trained by name; **no entry names Fun-Camera / Fun-Control / I2V as its
> training base.** Base tagging is filename-token inference; the catalog carries no
> base/type metadata field.
>
> **Q2.** No served template demonstrates a *style* LoRA on a Wan 2.2 dual-expert
> graph — NOT VISIBLE. The only served signal for the dual-expert convention is that
> accel and instareal LoRAs ship as explicit HIGH + LOW file pairs — inference from
> file-pair naming, not a documented wiring note. What a verdict would take: read the
> t2v template's interior for loader instances.
>
> **Q3.** Base-LoRA-on-derivative-weights posture: NOT VISIBLE anywhere served. No
> compatibility field exists on lora_name entries. No speculation offered.
>
> **Q4.** Custom-LoRA path on the video tier: NOT VISIBLE — every loader's lora_name
> is a fixed combo of pre-provisioned filenames; no free-text path, no HF-URL, no
> upload handle; no served node references a user-supplied LoRA. A provisioning
> mechanism outside the node catalog cannot be confirmed or denied from this surface.
>
> **Q5.** Strength conventions: sparse. The FLOAT carried no default/min/max on the
> agent's surface; the one template-carried datapoint is strength 1 (video_wan_animate2,
> consult #9).

## Calibration at ruling time (the advisor's own measurements, 2026-08-13)

| check | result |
|---|---|
| `LoraLoaderModelOnly` full schema via our `get_node` (uncapped) | **646 total lora_name options** (not ~450 — the agent's surface under-counted), 85 matching `wan`. `strength_model`: **default 1, min −100, max 100** — Q5's NOT VISIBLE resolved by our instrument. `WanVideoLoraSelect.strength`: default 1, ±1000. |
| The elided inventory, restored byte-exact | The mangled prefix is **`wan22-14b-t2v-`**; the two blanked entries are **`wan22-14b-t2v-if.safetensors`** and **`wan22-14b-t2v-instagirl.safetensors`**. The full style/scene set as served: `wan22-14b-t2v-{80s_fantasy_movie, dark_ghibli_fairytales, faceless_gods, hyperdetailed_colored_pencil, technically_color, vhs_television_style_80s_90s_phonk_style_2000s, vintage_film_grain, if, instagirl, instareal_2_2, polyhedron_all_perfect_skin_perfect_hands_perfect_eyes_m_f, 2d_to_3d_stereoscopic_conversion_and_3d_stereoscopic_generation}` · `wan22-candid_photography` · the tier-matched pairs `wan2.2_instareal_highnoise` / `_lownoise` and `WAN2.2-HighNoise_SmartphoneSnapshotPhotoReality_v3_by-AI_Characters.safetensors.safetensors` (double suffix verbatim) / `WAN2.2-LowNoise_…_v3_…` · `Wan21_T2V_14B_MoviiGen_lora_rank32_fp16` (2.1) · `wan22-14b-flippinrad_motion_morph` (borderline). The agent's filtering judgment is CONFIRMED against the full list. |
| Q2's "what a verdict would take" | **Already measured in-repo:** E09's Gate ROUTE evidence records the served `video_wan2_2_14B_t2v` wiring the lightx2v HIGH/LOW pair at strength 1.0 — **one loader per expert, tier-matched** is the demonstrated dual-expert convention. For single-file style LoRAs, one-vs-both remains a measured question for the spec. |

**Channel law, fourth and fifth confirmations in one round:** the combo list's
byte-truth and the strength spec both came from our `get_node` where the agent's
surface elided or omitted. Its filtering judgment and adjacency knowledge held.

## Ruling

1. **The inventory is real and the exact strings are banked above** — licence-fetch
   targets, not adoptions. Expectation set honestly: these are community-origin LoRAs
   (CivitAI-style naming); licence documents may be thin or unlocatable, and
   UNVERIFIED = NO will kill candidates at the fetch. That is the gate working.
2. **One candidate is excluded before any fetch:** `wan22-14b-t2v-dark_ghibli_fairytales`
   — Ghibli-styled output is anime-adjacent, and the studio's no-anime law is absolute.
   Not fetched, not considered.
3. **The dual-expert wiring convention stands demonstrated** (E09's own evidence): one
   loader per expert, tier-matched where pairs exist. The tier-matched pairs
   (`instareal`, `SmartphoneSnapshotPhotoReality`) are therefore the wiring-cleanest
   candidates; a single-file candidate carries — and would itself measure — the
   one-vs-both question.
4. **The transfer premise is the spec's central measured question:** every style entry
   is T2V-trained by name, the route's baseline runs Fun-Camera derivative weights,
   and no served documentation addresses the combination. The spec marks it ASSUMED,
   orders arms so a failure-to-bind is cheap, and treats a null as a finding — a
   licence row is not a wiring claim, and a LoRA row is not a binding claim either.
5. **Q4 is catalog-closed but not question-closed:** no served node loads a
   user-supplied LoRA — and the studio's own record holds a dated lead the catalog
   cannot see: the 2026-06-26 image-pipeline bridge delivered LoRAs by HF URL through
   the same cloud (a submission-surface mechanism, not a catalog node). Whether that
   extends to the video tier is unmeasured. Recorded as the open path for the
   studio's future canon-trained video LoRA; re-measured when that future is specced.
6. **Shelf notes from the full list:** `wan_alpha_2.1_rgba_lora` (an RGBA/alpha LoRA —
   rhymes with the authored-alpha law; shelf) · `wan2.2_animate_14B_relight_lora` +
   `WanAnimate_relight_lora` (relight for the driven route's unpark shelf) · the
   Fun-Reward InP LoRAs prove Fun-family LoRA training exists, though none is a style.
7. **Next, in order:** the Director picks a candidate (shortlist in the session
   record) → its licence fetch and row → the E14-shaped spec: one LoRA, strength as
   the single variable (strength-0 = the byte-pinned E12 baseline as the control arm),
   the same two seeds, zero partner credits, identity / world / camera graded
   separately, Gate LOOK before anything, and the per-route disclosure note stating
   that the free route remains a route whose generation runs on Comfy Cloud.
