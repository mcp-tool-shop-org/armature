# License map — verified commercial-use status

**The gate:** no non-commercially-licensed model, weight, LoRA, preprocessor or code dependency
enters this pipeline — including in experiments. CC-BY-NC, research-only and academic-only are
banned outright. A license that cannot be retrieved is **UNVERIFIED, which is treated as NO**.

Every row carries the URL of the **actual license document** (not a blog summary), the operative
clause, and the date it was fetched. **Entries older than 90 days are advisory until re-fetched**
— licenses in this space change.

`CONDITIONAL` is a **Director decision**, surfaced with its condition. It is never a quiet yes.

**All rows below fetched 2026-08-10** by the founding study-swarm's license lane.

---

## Generation models (open weights)

| Model | License | Commercial | Source | Operative clause |
|---|---|---|---|---|
| **Wan 2.1 T2V-14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) | "We claim no rights over the your generate contents" *(sic)* |
| **Wan 2.2 T2V-A14B** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) | same output clause |
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
| **umt5-xxl** (text encoder, both graphs) | Apache-2.0 | **YES** | [HF card](https://huggingface.co/google/umt5-xxl) — `cardData.license: apache-2.0`, retrieved at ruling time | ⚠ the Comfy-Org **repackaged** repo Cloud serves declares **no license at all** (blank field). Apache permits redistribution so the upstream grant governs — but the redistribution asserts nothing itself, which is worth knowing before anyone cites the repack as the authority. |
| **CausVid `Wan21_CausVid…_1_3B`** speed-LoRA | CC-BY-NC (flagged) | **NO — BANNED** | flagged by Comfy consult #1; **not independently retrieved** | Was bypassed inside the VACE graph. **Ruled: delete, not bypass** — see below. |
| **lightx2v 4-step** speed-LoRAs | Apache-2.0 | YES (but excluded) | [HF](https://huggingface.co/lightx2v/Wan2.2-Lightning) + [HF](https://huggingface.co/lightx2v/Wan2.1-T2V-14B-StepDistill-CfgDistill-Lightx2v) — **retrieved 2026-08-10**, upgraded from consult-sourced | Commercially clean; excluded on *methodology* grounds, not licensing — a 4-step/cfg-1 trajectory confounds a control-strength curve. |

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
| **DWPose** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/IDEA-Research/DWPose/onnx/LICENSE) | "perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable copyright license" |
| **RTMPose / MMPose** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/open-mmlab/mmpose/main/LICENSE) | same grant |
| **Depth Anything V2 Small** | Apache 2.0 | **YES** | [HF card](https://huggingface.co/depth-anything/Depth-Anything-V2-Small) | `apache-2.0` |
| **Depth Anything V2 Large** | CC-BY-NC-4.0 | **NO — BANNED** | [HF card](https://huggingface.co/depth-anything/Depth-Anything-V2-Large) | `cc-by-nc-4.0` |
| **Depth Anything V3 (weights)** | CC-BY-NC-4.0 | **NO — BANNED** | [HF card](https://huggingface.co/depth-anything/DA3-Large) | `cc-by-nc-4.0` — note the *code* at ByteDance-Seed/Depth-Anything-3 is Apache 2.0; the **weights** are what would ship |
| **SAM** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/facebookresearch/segment-anything/main/LICENSE) | — |
| **SAM 2** | Apache 2.0 | **YES** | [LICENSE](https://raw.githubusercontent.com/facebookresearch/sam2/main/LICENSE) | "no non-commercial or field-of-use restrictions" |
| **BiRefNet** | MIT | **YES** | [LICENSE](https://raw.githubusercontent.com/ZhengPeng7/BiRefNet/main/LICENSE) | "deal in the Software without restriction… and/or sell copies" |
| **rembg** | MIT (code) | **CONDITIONAL** | [LICENSE.txt](https://raw.githubusercontent.com/danielgatis/rembg/main/LICENSE.txt) | MIT covers code only — **bundled weights (u2net/isnet) carry separate licenses, not yet fetched** |

**Two traps confirmed, both of the kind this gate exists for:**

1. **OpenPose is non-commercial** — the single most widely used pose extractor in the ControlNet
   ecosystem, and it is banned here. DWPose or RTMPose replace it.
2. **The Small/Large split is real.** Depth Anything V2 **Small is Apache; Large is CC-BY-NC**,
   same family, same page structure, different license — exactly the "check the exact variant"
   law. V3's weights are NC across the board while its code is Apache; the weights are what a
   pipeline actually runs.

**Architectural consequence, and it is a large one.** armature renders depth from Blender's own
Z-buffer and can draw a skeleton from known bone transforms. Where it does that, **no depth or
pose *estimator* is in the pipeline at all** — the entire banned tier above is sidestepped by
construction, not by substitution. This is a genuine advantage of CG-sourced control over
video-extracted control, and E01 is designed to keep it.

⚠ **Open question this raises, for a later ruling:** matching a pose ControlNet's expected
*drawing convention* is a format question, but the **conditioning model's own weights** carry
their own license and are not yet in this table. Any pose/depth ControlNet or adapter checkpoint
gets a row here before it runs.

## Services and tools

| Item | Commercial | Source | Operative clause |
|---|---|---|---|
| **Comfy Cloud** | **YES** | [Terms of Service](https://www.comfy.org/terms-of-service) | "Customer retains all right, title, and interest in and to… Output"; also "will not use Input or Output to train generative AI" |
| **Blender 5.2.0 LTS** (build `fbe6228777e7`, 2026-07-14) | **YES** | the build's own bundled `license/license.md` and `license/spdx/GPL-3.0-or-later.txt`, read on this rig 2026-08-10 | licence: "While Blender itself is released under [GPU-GPL 3.0 or later] `© 2011-2026 Blender Foundation`" *(the "GPU-GPL" typo is verbatim from Blender's auto-generated file)*. Output, GPL-3.0 §2 Basic Permissions: **"The output from running a covered work is covered by this License only if the output, given its content, constitutes a covered work."** Also: "This License explicitly affirms your unlimited permission to run the unmodified Program." |

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

## UNVERIFIED — treated as NO until retrieved

Recorded honestly rather than assumed. Each blocks the thing that depends on it.

| Item | Why unverified | Blocks |
|---|---|---|
| ~~**Blender GPL / output statement**~~ | ~~blender.org and docs.blender.org both returned **403** to the fetcher~~ | **RESOLVED 2026-08-10 by E01's executor** — retrieved from the installed build's own bundled licence documents; row filed under *Services and tools* above. The web sources still 403; the local route is the better one. |
| **Kling terms** | HTTP 446 (Cloudflare block) on two URLs | Kling may not be used until fetched |
| **MiniMax terms** | JS-rendered page, no text returned | MiniMax may not be used until fetched |
| **ByteDance / Seedance output ownership** | BytePlus master ToS retrieved but contains **no AI-output clause**; the operative service-specific agreement was not located | Seedance may not be used until fetched |
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

The check is recorded **in the spec that introduces the dependency**, and the row lands here.
