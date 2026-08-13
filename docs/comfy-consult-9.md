# Comfy Agent consult #9 — answer, calibration, ruling

**Brief:** `docs/comfy-consult-9-brief.md` (the driven route's unpark surface — Animate2
under authored motion). **Relayed by the Director, answered and ruled the same day,
2026-08-13.** Round discipline held on both sides: knowledge only, zero credits, licences
as documents never verdicts, literals in plain text (the #8 relay-mangling lesson —
every string arrived intact this round).

---

## The agent's answer (as relayed)

> **Q0 — calibration.** Contract holds with one drift to flag. WanAnimate2ToVideo still
> serves reference_image, pose_video, continue_motion, positive_pose, the CLIP-vision
> hooks, and defaults 832×480×81. Drift from the consult #8 table: the node now also
> carries a second CLIP-vision hook named clip_vision_output_pose (a separate
> pose-branch CLIP-vision input, distinct from clip_vision_output). Its outputs are
> positive, negative, latent, trim_latent, trim_image, video_frame_offset. Field-level
> meaning of clip_vision_output_pose is NOT VISIBLE beyond its name/type.
>
> **Q1 — loader inventory (template video_wan_animate2).** The template is 17 nodes; all
> loaders live inside a subgraph. There are two structurally identical subgraph
> instances — the live one (instance 261) and a bypassed duplicate (instance 477, the
> "duplicate the subgraph" copy). Both reference the same filename strings. Exact
> strings as saved:
>
> - Diffusion checkpoint — unet_name = wan_animate_2_int8_convrot.safetensors
>   (weight_dtype = default)
> - Accel LoRA — LoraLoaderModelOnly, lora_name =
>   lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors (strength_model = 1)
> - Text encoder — clip_name = umt5_xxl_fp8_e4m3fn_scaled.safetensors (type = wan)
> - CLIP-vision — clip_name = clip_vision_h.safetensors
> - VAE — vae_name = Wan2_1_VAE_bf16.safetensors
> - WanAnimate2Cache config (in-template): device = gpu, dtype = int8
>
> There is no separate pose-branch weights loader — the pose branch consumes rendered
> frames, not a model. The int8 quantized build named wan_animate_2_int8_convrot
> .safetensors is what the Animate-2 licence rows should be fetched against (still
> treated NO until its documents are in hand — no verdict from me). Input widgets the
> template ships with: 189.image = pink_hair_mech_arms_ref.png; 240.file =
> street_dance_drive.mp4.
>
> **Q2 — pose_video contract.** (a) Drawing convention: NOT VISIBLE / NOT DOCUMENTED —
> the input is plainly typed IMAGE with no format tooltip; whether Animate2 expects the
> Wan2.2-repo stick convention or an updated one is not stated anywhere readable.
> Measurable, not derivable. (b) width/height/length are plain INT defaults 832/480/81;
> the template normalizes incoming frames (area scaling), implying pose_video is resized
> to target rather than required at exact resolution; no documented hard constraint; fps
> NOT VISIBLE at the node (the template's CreateVideo carries fps = 30 output-side).
> (c) Exact chain: LoadVideo (240) → GetVideoComponents (288) → [subgraph 261] → area
> scale (261/243) → WanAnimate2ToVideo (261/247) pose_video. **No detector node appears
> anywhere on this path** — no DWPreprocessor, no ViTPose, no SAM2 in the animate2
> template (that stack was the v1 template only). The pose branch is separable from any
> detector stage: rendered frames go straight in.
>
> **Q3 — chaining (continue_motion).** Mechanics NOT DOCUMENTED beyond the field
> surface: continue_motion is optional IMAGE; the node emits and consumes
> video_frame_offset plus trim outputs — the machinery of temporal handoff — but
> per-segment limits, seam behavior, cross-segment persistence of positive_pose /
> reference_image, and any total-length cap are NOT VISIBLE. The template's
> ContextWindowsManual (context_length 21, overlap 8, standard_static) is the
> context-window mechanism, not continue_motion semantics — do not conflate.
>
> **Q4 — root translation.** NOT VISIBLE. No platform-documented statement on root/hip
> traversal versus in-place. Measure it your side.
>
> **Q5 — dated field check.** No new skeleton-driven nodes/templates beyond the three
> animate nodes (WanAnimate2ToVideo, WanAnimate2Cache, WanAnimateToVideo) and the one
> template. Uni3C: WanUni3CControlnetApply (core) + the two WanVideoWrapper nodes;
> both Uni3C-apply and WanAnimate2Cache operate MODEL→MODEL and are by socket type
> chainable in series — a type-compatibility observation only; no served graph
> demonstrates the combination and no speculation is offered.
>
> **Halt note.** Q2(a), Q3, Q4 require measuring the running node; stopped at naming
> what they'd take. No documents fetched. The template was read in a separate scratch
> tab; the original canvas is untouched.

## Calibration at ruling time (the advisor's own measurements, 2026-08-13)

| check | result |
|---|---|
| `WanAnimate2ToVideo` re-measured via our `get_node` | Contract confirmed — and **our tooltips resolve two of the agent's NOT-VISIBLEs.** `clip_vision_output_pose`: *"CLIP vision of the pose video's first frame. Defaults to clip_vision_output."* Chaining mechanism, field-documented: `video_frame_offset` (required INT, default 0) — *"Frames to seek into the pose video. Connect to the video_frame_offset output of the previous node when extending"* — with `continue_motion` as *"Previous motion sequence to continue from for temporal consistency."* Mechanism documented; per-segment limits and seam behavior remain unmeasured. Also new versus the #8 banked table: `pose_start_percent` (window start; outside the window the pose branch is skipped entirely), and `pose_strength` 0.0 *"mutes it but does not fully remove it."* Schema min/max on width/height/length are 16–16384/1–16384 — the trained envelope is not schema-enforced, same shape as the camera tier. |
| Template `video_wan_animate2` top level via our `get_template` | **17 nodes confirmed, titles exact** (Load Image (Reference Image) 189 · Load Video (Pose Video) 240 · GetVideoComponents 288 · CreateVideo 245 · two SaveVideo · the notes incl. "Model Links" 575). The full workflow JSON (207k chars) exceeds our surface's cap and was omitted — **the loader filename strings are therefore agent-reported, attribution kept**; they harden or falsify at licence-fetch time, when each string either resolves to a document or does not. |
| Subgraph count | **The answer accounts for two subgraph instances (261 live, 477 bypassed); our top-level read shows a THIRD subgraph-typed node, 291, with a different blueprint UUID** (79280513…, vs 11706f8a… for 261 and b798a87e… for 477), wired near the second SaveVideo — consistent with an extension-segment block but unread. Carried as an open detail for the unpark; not assumed benign. |

**Channel law, third confirmation:** field-level truth comes from our `get_node`; the
agent's strengths are inventory, adjacency, and reading interiors our surface caps out
of (the subgraph loaders). The two instruments see different depths in both directions
this round.

## Ruling

1. **The licence fetch list for the driven route's unpark is now concrete** — this is
   what the round was for. To fetch, per the map's procedure, before the unpark runs
   anything: `wan_animate_2_int8_convrot.safetensors` (the served Animate-2 diffusion
   build — upstream identity unknown until its documents are in hand) ·
   `clip_vision_h.safetensors` (no row exists) · `Wan2_1_VAE_bf16.safetensors` and
   `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (the repack precedent likely extends —
   confirmed at fetch, not assumed) · the lightx2v distill LoRA already has its row
   (Apache-clean, methodology-excluded). UNVERIFIED = NO stands for all of them today.
   The template's own "Model Links" note (node 575) is a pointer source once the JSON
   interior is read.
2. **The served template wires the excluded lightx2v step-distill at strength 1.0 —
   the third sighting of the law.** E09's T2V template, the v1 Animate template's
   detector tier, now this. A served template is a reference, never a route; the
   unpark's in-repo graph rules on the accel question deliberately, and for a motion
   experiment the methodology exclusion presumably extends (ruled at spec time).
3. **The pose branch is detector-free at the platform's own current template level** —
   rendered frames enter `pose_video` directly, no DWPreprocessor anywhere on the path.
   The unpark's central structural licence fear is discharged by construction: armature
   renders pose natively and it goes straight in. The drawing convention itself stays a
   **measured** question — the unpark renders our Wan2.2-repo-convention sticks and
   observes adherence, against the silent-failure warning already on the map (a wrong
   convention fails silently; the model just obeys weakly).
4. **The unpark experiment's measured-question set is fixed:** (a) pose-convention
   adherence; (b) chaining beyond the documented mechanism — the mechanism itself
   (seek + continue) is now field-documented, the limits and seam behavior are not;
   (c) root/hip traversal. Each measurable, none derivable. Uni3C×Animate2 enters the
   record as a type-compatibility observation only.
5. **The #8 banked contract is amended by this round's re-measurement:**
   `clip_vision_output_pose` (pose video's first-frame CLIP-vision, defaults to the
   reference's) and `pose_start_percent` join the banked table; output names
   (trim_latent / trim_image / video_frame_offset) carried as agent-reported over our
   type-verified shape (2×CONDITIONING + LATENT + 3×INT).
6. **Conduct note:** the agent held the standing rules — scratch tab, canvas untouched,
   deviations at top. Removing its scratch tab is the Director's word to give; nothing
   here depends on that tab.

**Standing next-brief triggers unchanged**, plus one earned: the subgraph-291 interior
and the "Model Links" note, wanted at unpark-spec time if the licence fetch needs URLs
the filenames alone cannot locate.

**Addendum — 2026-08-13, same day: the fetch pass ran.** Ruling item 1's list is
resolved — every filename located in one repack repo (`Comfy-Org/Wan-Animate-2`),
upstream `Wan-AI/Wan2.2-Animate-2-14B` fetched Apache-2.0, the CLIP-vision upstream
fetched MIT, rows landed in the licence map (*Added 2026-08-13*) with the Director's
export corroborating. The subgraph-291 / Model-Links trigger was not needed — the
filename search resolved directly. The unpark is licence-clear; its remaining gates
are the three measured questions.
