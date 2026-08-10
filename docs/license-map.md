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

## UNVERIFIED — treated as NO until retrieved

Recorded honestly rather than assumed. Each blocks the thing that depends on it.

| Item | Why unverified | Blocks |
|---|---|---|
| **Blender GPL / output statement** | blender.org and docs.blender.org both returned **403** to the fetcher | Nothing in practice — GPL covering software rather than output is near-universal — but the primary source is **not retrieved**, so it is written here as unverified rather than asserted. Re-fetch before the claim is published anywhere. |
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
