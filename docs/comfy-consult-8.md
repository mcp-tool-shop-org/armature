# Comfy Agent consult #8 — answer, calibration, ruling

**Brief:** `docs/comfy-consult-8-brief.md` (the Wan reference-to-video tier — the
`@`-tag mode's API surface). **Relayed by the Director, answered and ruled the same
day, 2026-08-12.** Round discipline held on both sides: knowledge only, zero credits,
licences as documents never verdicts.

**Relay fidelity note:** the reply arrived with code-span literals mangled by the relay
surface (several model ids and one tool name rendered as "the model" or emptied). The
ruling below relies on schemas re-measured at ruling time, not on the mangled spans; the
answer is stored as received.

---

## The agent's answer (as relayed)

> **Q0 — calibration — ⚠ DRIFT SEEN.** The 2.6 node (`WanReferenceVideoApi`) fully
> renders and matches the brief's table: model `wan2.6-r2v`, prompt/negative,
> `reference_videos` (auto-grow, required), the 10 exact size pairs, duration, seed,
> `shot_type single|multi`, watermark. The 2.7 node (`Wan2ReferenceVideoApi`) renders
> only three static inputs (model id, seed, watermark) to the agent's schema view — the
> reference-image/video slots, resolution/ratio and duration 2–10 recorded in the brief
> do NOT surface there. Flagged honestly as likely tool-visibility on auto-grow /
> dynamic-combo inputs, not a confirmed catalog regression; re-measure with the brief's
> own `get_node` path before relying on the 2.7 field detail.
>
> **Q1 — the spatial contract.** On the r2v partner nodes: **no spatial conditioning
> input is served** — no start/first frame, no camera control, no pose/driving input.
> Composition is model-decided; the only spatial signal is whatever the reference
> videos' own frames carry. The r2v nodes are API nodes with a single VIDEO output and
> no MODEL/latent/controlnet socket, so they **cannot compose with Uni3C or any local
> control** — r2v + camera-control is NOT AVAILABLE at current catalog state. Where
> spatial control does live for Wan (adjacent, not on r2v): camera —
> `video_wan2_2_14B_fun_camera`, `video_wan2.1_fun_camera_v1.1_14B`,
> `video_wan2.1_fun_camera_v1.1_1.3B`; pose/depth/edge — `video_wan2_2_14B_fun_control`,
> `video_wan2_2_5B_fun_control`, `wan2.1_fun_control`, VACE `video_wan_vace_14B_v2v`;
> first/last frame — `video_wan2_2_14B_flf2v`, `wan2.1_flf2v_720_f16`,
> `video_wan_vace_flf2v`; trajectory/point motion — `video_wan_ati`,
> `video_wanmove_480p`.
>
> **Q2 — the identifier contract.** The only node-documented convention is the prompt
> tooltip: "Use identifiers such as character1 and character2." Binding order,
> one-identity-per-reference, image+video mixing for one character, a hard character
> cap, and stylized-reference behavior are all NOT VISIBLE as machine-readable contract;
> `shot_type single|multi` governs shot composition, not a character cap. The app
> guide's "two" is app-guide material, not node-enforced.
>
> **Q3 — terms surface: NOT VISIBLE.** The agent's catalog/schema tools do not expose
> rendered ToS pages, partner-model licence links, or Alibaba/DashScope terms documents,
> and it declined to reconstruct URLs from memory. Licence-map status unchanged:
> UNVERIFIED = NO for every Wan 2.6/2.7 variant.
>
> **Q4 — price: NOT VISIBLE.** No per-generation credit figure exposed on its surface;
> estimating would be invention; naming stopped at what it would take (a pricing panel
> read, or an estimate against a built-not-run graph).
>
> **Q5 — the changelog's two Wan items.** Both served as local (non-partner) tiers.
> **Wan-Animate2:** `WanAnimate2ToVideo` (conditioning node; takes pose + reference
> spatially — unlike r2v), `WanAnimate2Cache` (pose-branch cache, MODEL→MODEL, cpu/gpu,
> int8/int4), pose-branch preprocessors, template `video_wan_animate2`; the diffusion
> checkpoint is chosen at an upstream loader — exact filename NOT VISIBLE without
> inspecting the template's loader. **Uni3C:** core `WanUni3CControlnetApply`
> (model/patch/wan; MODEL + MODEL_PATCH + VAE + render_video → MODEL) and wrapper
> `WanVideoUni3C_ControlnetLoader` / `WanVideoUni3C_embeds`; the loader's choice list
> pins the exact weight file **`Wan21_Uni3C_controlnet_fp16.safetensors`**; licence for
> that weight NOT VISIBLE. Two r2v templates exist (`api_wan2_7_r2v`, the 2.6 r2v line)
> plus the calibration i2v `api_wan2_6_i2v`.

## Calibration at ruling time (the advisor's own measurements, 2026-08-12)

| check | result |
|---|---|
| `Wan2ReferenceVideoApi` re-measured via MCP `get_node` | **the brief's table stands byte-consistent** — `model.reference_images.image1…image5`, `model.reference_videos.video1…video3`, 720P/1080P, ratio ×5, duration 2–10, `characterN` tooltip, seed, watermark default false. The agent's drift flag resolves as **tool visibility**: its schema surface caps dynamic-combo dotted fields; the MCP path expands them. Both instruments honest; they see different depths. |
| `WanVideoUni3C_ControlnetLoader` options | **`Wan21_Uni3C_controlnet_fp16.safetensors` confirmed verbatim** in the served choice list (ComfyUI-WanVideoWrapper pack). |
| `WanUni3CControlnetApply` (core) | Confirmed: MODEL + MODEL_PATCH + VAE + `render_video` (IMAGE) → MODEL. The tooltip: *"The guidance video rendered from the camera trajectory, most commonly warped point cloud renders of the input image."* |
| `WanAnimate2ToVideo` full contract | Confirmed and richer than the reply: optional `reference_image` ("the character to animate"), `pose_video`, `continue_motion` (temporal chaining), `positive_pose` (a **separate motion prompt**), CLIP-vision hooks; defaults 832×480×81; operational tooltips (pose_strength 1.0 = trained behavior; `pose_end_percent` ≈0.7 keeps choreography while loosening fine detail; `reference_image_strength` >1.0 tightens identity against drift). |
| r2v cannot bind local control | Structurally confirmed from the held schemas: API nodes, single VIDEO output, no MODEL/latent socket. |

**Channel convention earned this round:** on dynamic-combo/auto-grow nodes, field-level
truth comes from our `get_node`; the agent's surface under-renders them. Its strengths
remain inventory, adjacency, and template knowledge. (Also: relay code-spans mangle —
next brief asks for literals in plain text.)

## Ruling

1. **The spatial contract is now measured, twice-instrumented:** the r2v tier authors
   nothing spatial and cannot bind local control. For armature it is an identity-lock
   surface whose only spatial channel is the content of the references themselves. It
   cannot replace the authored-spatial routes. Its candidate role — parked as a shelf
   idea, not a plan: a **composed route** where the references are themselves authored
   (GLB turnaround renders into `reference_images` on 2.7; an authored performance clip
   as `reference_video`), so identity locks natively while spatial authorship rides in
   through what we hand it. E13-shaped if ever specced; enters only through terms,
   price, and the Director's word.
2. **Terms and price remain OURS to fetch, at adoption time, not before:** Comfy ToS
   ownership clauses + Alibaba/DashScope hosted terms + a credit estimate against a
   built-not-run graph. No licence rows created today; UNVERIFIED = NO stands for all
   of 2.6/2.7.
3. **Uni3C joins the free route's shelf as a measured pairing candidate,** behind its
   documents: core apply class ↔ wrapper loader ↔ weight
   `Wan21_Uni3C_controlnet_fp16.safetensors` (pinned verbatim). The mechanism note that
   makes it armature-shaped: its `render_video` guidance input is *rendered from a
   camera trajectory* — this repo renders true guidance from authored scenes natively,
   where others warp point clouds. Licence of the weight AND of the wrapper pack:
   unfetched, NO until documents.
4. **Animate2's full contract is banked for the driven route's unpark** — pose +
   reference spatially, separate motion prompt, continue_motion chaining, native
   832×480×81. The checkpoint filename is one template-loader inspection away, owed at
   unpark, not now.
5. **The adjacent-inventory names** (FLF2V ×3, ATI, WanMove, fun-control/fun-camera
   template ids) enter the record as agent-reported catalog facts, attribution kept,
   each to be `get_node`-verified by whichever spec first leans on it.
6. **E12 is untouched by everything in this round.** The answer to "why 2.2" is now a
   measurement, not an argument.
