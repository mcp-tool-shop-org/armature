# License map — verified commercial-use status

**The gate:** no non-commercially-licensed model, weight, LoRA, preprocessor or code dependency
enters this pipeline — including in experiments. CC-BY-NC, research-only and academic-only are
banned outright. A license that cannot be retrieved is **UNVERIFIED, which is treated as NO**.

Every row carries the URL of the **actual license document** (not a blog summary), the operative
clause, and the date it was fetched. **Entries older than 90 days are advisory until re-fetched**
— licenses in this space change.

`CONDITIONAL` is a **Director decision**, surfaced with its condition. It is never a quiet yes.

**The purpose, ruled by the Director 2026-08-12:** every pipeline licence-friendly end to
end, so the studio's art can be published without encumbrance. The gate is not caution for
its own sake — it is the publishing plan.

**All rows below fetched 2026-08-10** by the founding study-swarm's license lane.

---

## Generation models (open weights)

| Model | License | Commercial | Source | Operative clause |
|---|---|---|---|---|
| **Wan 2.1 T2V-14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) | "We claim no rights over the your generate contents" *(sic)* |
| **Wan 2.2 T2V-A14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) | same output clause |
| **Wan 2.2 I2V-A14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B), fetched 2026-08-12 (the E11 spec) | "claim no rights over the your generated contents" *(sic — the family's output clause)* |
| **Wan 2.1 VACE-14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.1-VACE-14B) | "licensed under the Apache 2.0 License" |
| **Wan 2.1 Fun-14B-Control** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/alibaba-pai/Wan2.1-Fun-14B-Control) | `apache-2.0` |
| **Mochi 1 preview** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/genmo/mochi-1-preview) | "releasing the model under a permissive Apache 2.0 license" |
| **LTX-Video 0.9.x** | Open Weights (OpenRAIL-M style) | **YES** — no revenue cap found | [license txt](https://huggingface.co/Lightricks/LTX-Video/raw/main/ltx-video-2b-v0.9.5.license.txt) | "Licensor claims no rights in the Output You generate using the Model" |
| **LTX-2** | LTX-2 Community | **CONDITIONAL** — revenue < $10M/yr; attribution retained | [LICENSE](https://huggingface.co/Lightricks/LTX-2/raw/main/LICENSE) | "Entities with annual revenues of at least $10,000,000… required to obtain a paid commercial use license" |
| **HunyuanVideo** | Tencent Hunyuan Community | **CONDITIONAL** — territory + MAU | [LICENSE.txt](https://raw.githubusercontent.com/Tencent-Hunyuan/HunyuanVideo/main/LICENSE.txt) | "worldwide territory, excluding the territory of the European Union, United Kingdom and South Korea"; >100M MAU must request a license |
| **CogVideoX-5b** | Zhipu custom | **CONDITIONAL** — registration + traffic cap | [LICENSE](https://huggingface.co/zai-org/CogVideoX-5b/raw/main/LICENSE) | "must register and obtain a basic commercial license"; "must not exceed 1 million visits per month" |

### Added 2026-08-10 (second pass — local KB + Comfy consult #1)

| Model / component | License | Commercial | Source | Note |
|---|---|---|---|---|
| **Wan2.2-Fun-A14B-Control** | Apache-2.0 | **YES** | `readouts/model-knowledge` KB (retrieval-verified) | "VACE-style control conditioning" |
| **Wan2.2-VACE-Fun-A14B** | Apache-2.0 | **YES** | same | finetuned from Wan2.2-I2V-A14B |
| **Wan2.2-Animate-14B** | Apache-2.0 | **YES** | same | animate a still from a driving video |
| **Wan2.2-Fun-A14B-Control-Camera** | Apache-2.0 | **YES** | [HF card](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera), fetched 2026-08-12 (consult #7 ruling; re-fetched at the E11 w2 ruling) | camera-controlled video; a **derivative of Wan2.2-I2V-A14B** trained for camera synthesis on **81-frame sequences @ 16 fps**, training resolutions **512/768/1024**. Serves `WanCameraEmbedding` → `WanCameraImageToVideo` (both core nodes, GPL row). The Cloud-served files are `wan2.2_fun_camera_high_noise_14B_fp8_scaled` / `…_low_noise_…` (Comfy-Org repacks — the repack ruling extends). ⚠ **A licence row is not a wiring claim** (E11 w2, measured): the camera nodes REQUIRE these weights — fed to the plain I2V experts they produce noise. ⚠ this card is **silent on output rights** — Comfy Cloud's ToS ownership row governs our generations service-side. |
| **umt5-xxl** (text encoder, both graphs) | Apache-2.0 | **YES** | [HF card](https://huggingface.co/google/umt5-xxl) — `cardData.license: apache-2.0`, retrieved at ruling time | ⚠ the Comfy-Org **repackaged** repo Cloud serves declares **no license at all** (blank field). Apache permits redistribution so the upstream grant governs — but the redistribution asserts nothing itself, which is worth knowing before anyone cites the repack as the authority. |
| **CausVid `Wan21_CausVid…_1_3B`** speed-LoRA | CC-BY-NC (flagged) | **NO — BANNED** | flagged by Comfy consult #1; **not independently retrieved** | Was bypassed inside the VACE graph. **Ruled: delete, not bypass** — see below. |
| **lightx2v 4-step** speed-LoRAs | Apache-2.0 | YES (but excluded) | [HF](https://huggingface.co/lightx2v/Wan2.2-Lightning) + [HF](https://huggingface.co/lightx2v/Wan2.1-T2V-14B-StepDistill-CfgDistill-Lightx2v) — **retrieved 2026-08-10**, upgraded from consult-sourced | Commercially clean; excluded on *methodology* grounds, not licensing — a 4-step/cfg-1 trajectory confounds a control-strength curve. |

**Ruling 2026-08-11 (E09 calibration ruling) — the Comfy-Org repack tier.** The served
`wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`, `…_low_noise…`, and
`wan_2.1_vae.safetensors` are Comfy-Org repacks of weights this map already rules Apache
(Wan 2.2 T2V-A14B; Wan 2.1). Per the umt5 precedent above, the upstream grant governs and
the repack asserts nothing itself — covered, no new rows. The lightx2v exclusion is
methodological and unchanged.

**Ruling — a bypassed non-commercial node still counts as present.** The gate's words are
"anywhere in the pipeline — including experiments." A bypassed node is one accidental
un-bypass from executing, and the workflow JSON is an artifact we version, share and cite; it
would carry a reference to a non-commercial model. **Bypassing is not removal. Delete it.**

**Ruling — Wan 2.x is the default generation route.** It is the only family that is
unconditionally Apache 2.0 across base, VACE and Fun-Control, and it explicitly disclaims rights
in outputs. HunyuanVideo's territory exclusion (EU/UK/South Korea) makes it unusable for a game
sold internationally; CogVideoX's registration requirement and LTX-2's revenue threshold are
Director decisions, not defaults.

## Preprocessors — the tier where the violation actually lives

| Tool | License | Commercial | Source | Operative clause |
|---|---|---|---|---|
| **OpenPose (CMU)** | CMU Academic / Non-Commercial | **NO — BANNED** | [LICENSE](https://raw.githubusercontent.com/CMU-Perceptual-Computing-Lab/openpose/master/LICENSE) | "may be used for your own noncommercial internal research purposes" |
| **DWPose (code)** | Apache 2.0 | **YES — CODE ONLY** | [LICENSE](https://raw.githubusercontent.com/IDEA-Research/DWPose/onnx/LICENSE) | "perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable copyright license" |
| **DWPose / ViTPose WEIGHTS** | not fetched | **UNVERIFIED — treated as NO** | — | ⚑ **Narrowed 2026-08-10 (Comfy consult #3).** The row above cited the *code* licence and was read as clearing the detector. The **weights are a separate grant and were never fetched** — the identical trap this map already records for `rembg`. Costs armature nothing: we render pose from geometry, so no detector is in the pipeline. Blocks any pose-preprocessor route, incl. `WanAnimatePreprocess`. |
| **RTMPose / MMPose** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/open-mmlab/mmpose/main/LICENSE) | same grant |
| **Depth Anything V2 Small** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/depth-anything/Depth-Anything-V2-Small) | `apache-2.0` |
| **Depth Anything V2 Large** | CC-BY-NC-4.0 | **NO — BANNED** | [HF card](https://huggingface.co/depth-anything/Depth-Anything-V2-Large) | `cc-by-nc-4.0` |
| **Depth Anything V3 (weights)** | CC-BY-NC-4.0 | **NO — BANNED** | [HF card](https://huggingface.co/depth-anything/DA3-Large) | `cc-by-nc-4.0` — note the *code* at ByteDance-Seed/Depth-Anything-3 is Apache 2.0; the **weights** are what would ship |
| **SAM** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/facebookresearch/segment-anything/main/LICENSE) | — |
| **SAM 2** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/facebookresearch/sam2/main/LICENSE) | "no non-commercial or field-of-use restrictions" |
| **BiRefNet** | MIT | **YES** | [LICENSE](https://raw.githubusercontent.com/ZhengPeng7/BiRefNet/main/LICENSE) | "deal in the Software without restriction… and/or sell copies" |
| **rembg** | MIT (code) | **CONDITIONAL** | [LICENSE.txt](https://raw.githubusercontent.com/danielgatis/rembg/main/LICENSE.txt) | MIT covers code only — **bundled weights (u2net/isnet) carry separate licenses, not yet fetched** |

**Two traps confirmed at founding, a third measured 2026-08-11 — all of the kind this gate
exists for:**

1. **OpenPose is non-commercial** — the single most widely used pose extractor in the ControlNet
   ecosystem, and it is banned here. ⚑ **Corrected 2026-08-10:** this line used to read "DWPose
   or RTMPose replace it," which cleared a *replacement* on the strength of a **code** licence.
   Their weights are a separate, unfetched grant. **The honest replacement is not another
   detector — it is rendering pose from geometry we own**, which is what armature does and why
   the whole tier stays out of the pipeline.
2. **The Small/Large split is real.** Depth Anything V2 **Small is Apache; Large is CC-BY-NC**,
   same family, same page structure, different license — exactly the "check the exact variant"
   law. V3's weights are NC across the board while its code is Apache; the weights are what a
   pipeline actually runs.
3. **The served Animate template wires the banned tier (measured 2026-08-11, consult #6
   calibration).** `video_wan2_2_14B_animate` carries two `DWPreprocessor` nodes (the DWPose
   weights tier, UNVERIFIED = NO) plus a SAM2 mask path at its top level. The template is not
   runnable under this gate as served; the clean route is the core `WanAnimateToVideo` node in
   a graph we build, with `pose_video` fed by frames rendered from our own rig — sidestepped
   by construction, not substitution, again. **Second instance, same day (E09 Gate ROUTE):**
   the served `video_wan2_2_14B_t2v` wires this map's excluded lightx2v 4-step LoRAs at
   strength 1.0 (not bypassed), runs both samplers on the excluded 4-step/cfg-1 trajectory,
   randomizes one sampler's seed, and exposes no length or seed slot — evidence
   `outputs/E09/route/route_gate_evidence.json` on `E09-run`. The pattern is now law in
   CLAUDE.md: a served template is a reference, never a route.

**Architectural consequence, and it is a large one.** armature renders depth from Blender's own
Z-buffer and can draw a skeleton from known bone transforms. Where it does that, **no depth or
pose *estimator* is in the pipeline at all** — the entire banned tier above is sidestepped by
construction, not by substitution. This is a genuine advantage of CG-sourced control over
video-extracted control, and E01 is designed to keep it.

⚠ **Open question this raises, for a later ruling:** matching a pose ControlNet's expected
*drawing convention* is a format question, but the **conditioning model's own weights** carry
their own license and are not yet in this table. Any pose/depth ControlNet or adapter checkpoint
gets a row here before it runs.

## Motion data and motion-capture tier — surveyed 2026-08-11 (the E08 study-swarm)

| Item | License | Commercial | Source | Operative clause |
|---|---|---|---|---|
| **AMASS** (the mocap dataset behind the open text-to-motion line) | MPI-IS custom, non-commercial | **NO — BANNED, and it reaches through weights** | [license](https://amass.is.tue.mpg.de/license.html), fetched 2026-08-11 | "This license also prohibits the use of the Dataset to train methods/algorithms/neural networks/etc. for commercial use of any kind." Closes the released weights of MDM / MotionGPT / MoMask / T2M-GPT / OmniControl / OMG for this pipeline regardless of their MIT code — the data licence purports to bind trained models. Commercial contact: ps-license@tue.mpg.de. |
| **MediaPipe Pose Landmarker** (Lite / Full / Heavy `.task` models + `mediapipe` package + repo) | Apache-2.0 at all three layers | **YES** | repo [LICENSE](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/LICENSE) · [PyPI metadata](https://pypi.org/project/mediapipe/) (v1.0.0, 2026-07-27) · model card "BlazePose GHUM 3D" PDF (storage.googleapis.com/mediapipe-assets), all fetched 2026-08-11 | Model card: "LICENSED UNDER Apache License, Version 2.0" — the licence of the shipped model files themselves, not only the code (the docs page declares none; the card does). Repo LICENSE carries a permissive BSD-style Lucent sub-licence for UTF utilities. GHUM appears in the models' *construction*; the shipped `.task` files carry their own Apache card, and nothing GHUM-licensed ships or runs here. Card's own out-of-scope list is binding design context: multi-person, far subjects (>4 m), hidden head, and **"applications requiring metric accurate depth."** Pin the installed package + model file versions in any spec that uses them; a version bump re-fetches the card. |

The rest of the surveyed tier (SMPL/SMPL-X body models, MediaPipe Pose, hosted
text-to-motion vendors) sits in the UNVERIFIED table below until each licence document is
fetched by this map's own procedure. Full survey with measured quality numbers:
[research-grounding-e08.md](research-grounding-e08.md).

## Services and tools

| Item | Commercial | Source | Operative clause |
|---|---|---|---|
| **Comfy Cloud** | **YES** | [Terms of Service](https://www.comfy.org/terms-of-service) | "Customer retains all right, title, and interest in and to… Output"; also "will not use Input or Output to train generative AI" |
| **Blender 5.2.0 LTS** (build `fbe6228777e7`, 2026-07-14) | **YES** | the build's own bundled `license/license.md` and `license/spdx/GPL-3.0-or-later.txt`, read on this rig 2026-08-10 | licence: "While Blender itself is released under [GPU-GPL 3.0 or later] `© 2011-2026 Blender Foundation`" *(the "GPU-GPL" typo is verbatim from Blender's auto-generated file)*. Output, GPL-3.0 §2 Basic Permissions: **"The output from running a covered work is covered by this License only if the output, given its content, constitutes a covered work."** Also: "This License explicitly affirms your unlimited permission to run the unmodified Program." |
| **ComfyUI core node code** (`WanAnimateToVideo` · `Wan22FunControlToVideo` · `WanVaceToVideo` · `WanFirstLastFrameToVideo` et al.) | **YES — same output logic as the Blender row** | [LICENSE](https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/LICENSE), fetched 2026-08-11 (consult #6 ruling) | GPL-3.0. Output, §2: "The output from running a covered work is covered by this License only if the output, given its content, constitutes a covered work." The nodes execute hosted on Comfy Cloud; we redistribute no GPL code, and a generated video is not derived from the node source. Output ownership is separately granted by the Comfy Cloud ToS row above. Caveat, recorded honestly: fetched from the upstream repo at `master`; that Cloud serves this exact tree is asserted by category — the same shape every served-core-node claim carries. |
| **Wan-Video/Wan2.2 code repo** (the convention source: `wan/modules/animate/preprocess/human_visualization.py`) | **YES** | [LICENSE.txt](https://raw.githubusercontent.com/Wan-Video/Wan2.2/main/LICENSE.txt), fetched 2026-08-11 | Apache-2.0 — "perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable copyright license." Resolves procedure note 7 for the pose-render route: the drawing convention (palette, limbSeq, stickwidth formula, separate hand pass) is defined in commercially-licensed source, so reading and matching it puts no banned tier in the pipeline. |
| **Comfy-Org/workflow_templates** (documentation tier — the day-0 T2V reference workflow's numeric settings, E09 A3) | **YES** | [LICENSE](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/LICENSE), fetched 2026-08-12 | MIT — "Permission is hereby granted, free of charge… to deal in the Software without restriction." Cited for documented values; nothing loaded as a dependency, nothing copied as code. |

**Blender — resolved by E01's executor, 2026-08-10.** The founding swarm recorded this row as
UNVERIFIED because blender.org and docs.blender.org both returned **403** to the fetcher; both
still did on re-attempt today, and `blender/blender@main:COPYING` turns out to be a pointer file
rather than the licence text. The route that worked is better than either: **the installed build
carries its own licence documents**, so the retrieved text is the licence of the exact binary that
rendered E01 rather than of whatever is at HEAD — which is what "check the exact variant and
version you are about to run" asks for.

The output clause is the one that matters here and it is narrow: GPL-3.0 covers a render only if
the render *itself* constitutes a covered work. A depth or normal pass of geometry we own is not
derived from Blender's source, so E01's control sequences are not covered works. This row states
what the licence says; it is not legal advice, and the "given its content" qualifier is the part a
future arm should re-read before shipping anything that embeds Blender-authored content (its
bundled fonts, matcaps or asset library, each carrying its own licence in the same file).


### Rigging vendors — the class is CLOSED (2026-08-10)

| Vendor | Commercial | Note |
|---|---|---|
| **Tripo** (partner/3d — import · rig · retarget) | **NO — LICENCE CONFLICT** | ⛔ **Director's ruling, 2026-08-10.** The only Cloud vendor whose import node (`FILE_3D_GLB` → `MODEL_TASK_ID`) can rig **a mesh we supply**, and it is out. Comfy consult #1 (2026-08-01) had already left Tripo P1's licence open, and recorded that swapping to v3.1 *moved* the question rather than resolving it — same vendor, same ToS. |
| **Meshy** (partner/3d — rig) | not retrieved | Moot: its rig node takes a `MESHY_TASK_ID` obtainable only from a Meshy *generation* node, so it **cannot rig our canonical character**. |
| **Rodin · Tencent/Hunyuan3D** | — | **No rig node exists** in either family — verified by absence, consult #7. |

**Consequence — ruled:** with Tripo out, Meshy unable to take our mesh, no rig node elsewhere, and **no open-weights auto-rig on Cloud** (verified by absence), **there is no Cloud rigging route that survives this gate. Rigging happens locally** — which carries no licence question at all and keeps the control path estimator-free by construction.

### Retopo tools — a second axis the gate protects, ruled 2026-08-11

| Tool | Pipeline-fit | Note |
|---|---|---|
| **QuadRemesher (Exoside)** | **NO — RULED OUT** | ⛔ **Director's ruling, 2026-08-11:** he ruled it not commercially safe for the pipeline A proprietary paid addon cannot be a canonical route stage regardless of who owns a seat licence — the gate protects the **pipeline's** cleanliness and reproducibility, not one rig's right to run a tool. The advisor's same-day "owned-commercial YES" is corrected in place: it graded the wrong axis. |
| **Blender built-in remeshers** (Voxel, QuadriFlow) | **YES** | Ship inside Blender — covered by the Blender 5.2.0 LTS row above; headless-scriptable; zero new dependency. The E07 arm-(d) route uses these. |
| **Instant Meshes or any other external retopo** | **UNVERIFIED — treated as NO** | Enters only through a retrieved licence document ruled through this gate before first use. |

## UNVERIFIED — treated as NO until retrieved

Recorded honestly rather than assumed. Each blocks the thing that depends on it.

| Item | Why unverified | Blocks |
|---|---|---|
| ~~**Blender GPL / output statement**~~ | ~~blender.org and docs.blender.org both returned **403** to the fetcher~~ | **RESOLVED 2026-08-10 by E01's executor** — retrieved from the installed build's own bundled licence documents; row filed under *Services and tools* above. The web sources still 403; the local route is the better one. |
| **Kling terms** | HTTP 446 (Cloudflare block) on two URLs | Kling may not be used until fetched |
| **MiniMax terms** | JS-rendered page, no text returned | MiniMax may not be used until fetched |
| **ByteDance / Seedance output ownership** | BytePlus master ToS retrieved but contains **no AI-output clause**; the operative service-specific agreement was not located | Seedance may not be used until fetched |
| **Wan 2.6/2.7 partner tier** (`wan2.6-i2v` · `wan2.6-r2v` · `wan2.7-r2v` · `wan2.7-t2v` · `wan2.7-videoedit`) | ~~provider-side terms NOT RETRIEVED~~ **RETRIEVED 2026-08-12 by the Director's export** (fetchers still get a JS shell): *Wan Terms of Service*, `wan.video/policy/termsofService`, updated **2026-08-06**, Intelligent Cloud Computing (Singapore) Pte Ltd; full text pinned sha256 `26d81f01…cb4cd6` (Director's local export). **Outputs:** "we assign to you all of our right, title, and interest—if any—in Outputs" (§III.4). **Conditions found:** publication carries an AI-disclosure duty — "clearly and conspicuously disclose… generated by artificial intelligence" (§III.8(g)); no removing "any label or watermark applied" (§II.1(a)); and the heavy one — **User Content (Prompts AND Outputs) is licensed to Wan** "unconditional, irrevocable… fully transferable, sub-licensable, perpetual, worldwide" (§III.6), deemed "non-confidential and non-proprietary" (§III.3(c)), expressly usable "to develop and improve our machine-learning and artificial-intelligence technologies" (§III.3(e)) — i.e., **uploaded reference assets carry a training-and-publication licence to the provider on this surface**. Scope caveat: the document governs "Services accessible via wan.video"; its own §II.1(c) bans automated extraction of Outputs, which cannot describe the API tier — so **which paper governs Comfy-mediated partner calls is NOT established**; Comfy's own row above says no training on Input/Output. **API tier RETRIEVED same day:** the Model Studio service-specific terms (`help.aliyun.com/en/model-studio/bailian-service-notes`) restrict **trial** content only ("may only be used to evaluate the model's performance… not… any commercial purpose"; "must not remove or tamper with labels such as 'AI-generated' added by the trial service") and are **silent on paid-tier ownership** — Comfy's assignment fills our side of that chain; and the Model Studio FAQ, Product Q7, publishes: **"Alibaba Cloud strictly protects data privacy and never uses your data for model training"** (a vendor FAQ — weaker paper than a contract clause, recorded as such). Residual: the Comfy↔Alibaba reseller agreement itself is unseeable — the same residual every partner-API row on this map will ever carry | **CONDITIONAL — the Director's ruling required** on two named conditions before E13 or any 2.6+ generation: (1) the AI-disclosure duty on published outputs; (2) the input-licence scope — E13 uploads the twin's canonical renders and an authored clip as Prompts; on the consumer surface those would carry a perpetual provider licence incl. training. Options surfaced 2026-08-12: proceed via Comfy on Comfy's no-training clause accepting the governance ambiguity · hold for the API-tier paper · proceed with reduced-exposure references |
| **`FL_WanVaceToVideoMultiRef`** / Fill custom-node pack | licence not retrieved | multi-reference VACE route — stay on core `WanVaceToVideo` |
| **`WanVaceAdvanced` tier** (`VaceStrengthTester`, `VaceAdvancedModelPatch`) | licence not retrieved | any scheduled/advanced VACE control strength |
| **`FL_WanFirstLastFrameToVideo`** (Fill Nodes) | licence not retrieved | first/last-frame conditioning — use core `WanFirstLastFrameToVideo` instead if ever needed |
| ~~**Core Wan nodes** `WanAnimateToVideo`, `WanFirstLastFrameToVideo`~~ | ~~ASSUMED-FROM-CATEGORY, not retrieved~~ | **RESOLVED 2026-08-11 by the consult #6 ruling** — the core node code licence is fetched and filed under *Services and tools* (ComfyUI core, GPL-3.0, narrow output clause). Closes the node-code question for the core Wan conditioning tier. |
| **"Wan Animate 2"** (`video_wan_animate2` template) | model name, weight files and licence unidentified from catalog metadata; ~~the consult's claimed node class `WanAnimate2ToVideo` does not resolve in the node catalog (checked twice, 2026-08-11)~~ **corrected 2026-08-12: the class RESOLVES** — full contract retrieved by `get_node` at the consult #8 ruling (core pack, `model/conditioning/wan/animate`; pose + reference spatial inputs; see `docs/comfy-consult-8.md`), consistent with the runtime changelog's v0.31.0 landing | the Animate-2 route — still treated NO until weights and LICENSE are identified (the checkpoint is chosen at an upstream loader; one template-loader inspection away, owed at the driven route's unpark) |
| **SCAIL-2** (`video_wan21_scail2_character_replacement`, + `_int8`) | weight files, upstream repo and licence unlocated in catalog metadata; template-level only, no raw node schema; background likely inherited from the driving video (consult #6, marked SPECULATION there) | any SCAIL-2 route — treated NO |
| **SMPL / SMPL-X body-model licences** | reported research-only with commercial via Meshcapade (E08 study-swarm G2, agent-retrieved URLs) — not yet fetched by this map | any SMPL-dependent lift route (WHAM / TRAM / 4D-Humans at inference; GVHMR and SMPLer-X are additionally NC at the code layer) — treated NO |
| ~~**MediaPipe Pose Landmarker** (shipped models + repo)~~ | ~~reported Apache-2.0 — not yet fetched~~ | **RESOLVED 2026-08-11** — all three layers fetched (repo LICENSE, PyPI metadata, the models' own card); row filed under *Motion data and motion-capture tier* above. Verdict YES. |
| **DeepMotion SayMotion · Uthana · Cartwheel terms** | vendor pages claim commercial rights to generated output by contract; the terms documents are not fetched and no vendor discloses its training-data chain | the hosted text-to-motion arm (Arm A) — per-vendor terms fetch + Director decision before any use |
| **`WanAnimatePreprocess` detector tier** (ViTPose/DWPose weights) | licence not retrieved | Wan 2.2 Animate via *detected* pose. Authoring pose from Blender geometry sidesteps this entirely |
| **rembg bundled weights (u2net / isnet)** | individual model licenses not fetched | rembg may not be used until fetched — the MIT applies to the code only |

**Note the shape of these gaps:** every unverified row is a **partner API** or a bundled weight,
and every verified-clean row is open weights. Partner-API terms are the harder half of this map
to establish, which is itself an argument for the open-weights route being the default.

## Procedure when a new dependency appears

1. Fetch the actual license document — model card, `LICENSE` file, or official terms page.
2. Record: name, version, license name, URL, operative clause (short quote), fetch date.
3. Rule `COMMERCIAL: YES / NO / CONDITIONAL(<condition>)`.
4. `NO` → the dependency does not enter, and the spec names what replaces it.
5. `CONDITIONAL` → surfaced to the Director with the condition stated, before use.
6. `UNVERIFIED` → treated as `NO` until retrieved.
7. ⚑ **A non-commercial dependency can enter as a SPECIFICATION, not only as a runtime import.**
   Added 2026-08-10 (Comfy consult #4). If the only documentation of a format, convention or
   colour table we must match lives in non-commercially-licensed source, then *reading it to
   learn the spec* puts that tier back in the pipeline — the same logic as our own ruling that
   **a bypassed non-commercial node is still present**, one layer up. "We re-implemented it
   ourselves" does not obviously launder a table lifted from it.
   **Bounded honestly: this is a risk to surface, not a settled legal conclusion.** Licences
   govern copying and distribution; learning a fact is not automatically a derivative work, and a
   verbatim table is a different object from a fact. **Prefer determining such a convention
   empirically.** Where that is impractical, retrieve the licence and route the question to the
   Director. ⚠ Note the failure mode that makes this urgent rather than academic: a wrong
   convention of this kind **fails silently** — the model simply obeys weakly and no gate fires.

The check is recorded **in the spec that introduces the dependency**, and the row lands here.
