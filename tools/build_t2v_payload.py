#!/usr/bin/env python
"""build_t2v_payload — E09 B2's graph, built in-repo from pieces the licence map covers.

    python tools/build_t2v_payload.py --seeds=specs/E09-seeds.json --out=outputs/E09/route

Commissioned by ruling R8 after Gate ROUTE refused the served `video_wan2_2_14B_t2v`
template. **A served template is a reference, never a route** (CLAUDE.md, measured twice on
2026-08-11), so every number below comes from the Wan 2.2 reference configuration or from
this repo's own record, and each one is written into the payload with the source it came
from. Nothing is taken from the served template — including the values that happen to
coincide, which are marked as coinciding rather than quietly reused.

--------------------------------------------------------------------------------
The sampling trajectory, and where each number is from

Fetched verbatim 2026-08-11 from the Wan-Video/Wan2.2 repository (Apache-2.0, already the
licence map's cited source for the driving convention):

    wan/configs/wan_t2v_A14B.py     sample_steps = 40
                                    sample_shift = 12.0
                                    boundary = 0.875
                                    sample_guide_scale = (3.0, 4.0)  # low noise, high noise
    wan/configs/shared_config.py    num_train_timesteps = 1000
                                    sample_fps = 16
                                    sample_neg_prompt = <the reference negative, verbatim>

**The two-expert split is DERIVED, not dialled.** Wan 2.2 T2V is a mixture of two experts
and the reference switches between them on the *timestep*, not on a step index: the
high-noise expert runs while t >= boundary * num_train_timesteps. ComfyUI's
`KSamplerAdvanced` splits on a step index instead, so the index has to be computed from the
shifted sigma schedule rather than guessed — and guessing it is how a two-expert model gets
run as one and a half. With the flow shift

    sigma' = shift * sigma / (1 + (shift - 1) * sigma)

and `simple` stepping sigma linearly 1 -> 0 across `steps`, the crossing index is solved in
`boundary_step()` below and recorded in the payload with its arithmetic. The served
template's own split (2 of 4) is NOT the reference's and is not used.

`euler` / `simple` are the one choice here that comes from neither source: the reference's
`unipc` solver has no ComfyUI equivalent for this graph, and euler+simple is ComfyUI's
standard flow-matching pair. Recorded as a port necessity, with its reason, rather than
presented as a Wan default.

--------------------------------------------------------------------------------
Admission, in the order ruling R8 fixed

Gate ROUTE on our own graph -> Gate S against the committed seed list -> Gate L on the
actual graph. All three raise in-tool. Nothing here submits anything or spends anything;
the graph and its record are written to disk for a separate, deliberate submission step.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import route_gates as RG  # noqa: E402

TOOL_VERSION = "E09.2"

WAN22_SOURCE = "https://github.com/Wan-Video/Wan2.2 (Apache-2.0), fetched 2026-08-11"

#: Every number, with the source it came from. This dict IS the payload's provenance — a
#: value that cannot name its source does not belong in the graph.
REFERENCE = {
    "sample_steps": {"value": 40, "source": f"{WAN22_SOURCE} wan/configs/wan_t2v_A14B.py"},
    "sample_shift": {"value": 12.0, "source": f"{WAN22_SOURCE} wan/configs/wan_t2v_A14B.py"},
    "boundary": {"value": 0.875, "source": f"{WAN22_SOURCE} wan/configs/wan_t2v_A14B.py"},
    "guide_scale_low_noise": {
        "value": 3.0,
        "source": f"{WAN22_SOURCE} sample_guide_scale = (3.0, 4.0)  # low noise, high noise"},
    "guide_scale_high_noise": {
        "value": 4.0,
        "source": f"{WAN22_SOURCE} sample_guide_scale = (3.0, 4.0)  # low noise, high noise"},
    "num_train_timesteps": {"value": 1000,
                            "source": f"{WAN22_SOURCE} wan/configs/shared_config.py"},
    "fps": {"value": 16, "source": f"{WAN22_SOURCE} shared_config.sample_fps"},
    "sampler_name": {
        "value": "euler",
        "source": ("NOT from the Wan reference and NOT from the served template: the "
                   "reference's unipc solver has no ComfyUI equivalent for this graph, and "
                   "euler is ComfyUI's standard flow-matching sampler. A port necessity, "
                   "recorded as one")},
    "scheduler": {
        "value": "simple",
        "source": ("same port necessity as the sampler; `simple` is the flow scheduler the "
                   "shift formula below assumes, so the derived split and the scheduler "
                   "have to agree")},
}

#: The Wan 2.2 reference negative prompt, verbatim from `shared_config.sample_neg_prompt`.
#: Copied from the fetched file, not from the served template — the two agree because both
#: descend from this source, which is a coincidence worth naming rather than leaning on.
REFERENCE_NEGATIVE = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，"
    "最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，"
    "画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，"
    "杂乱的背景，三条腿，背景人很多，倒着走"
)

#: The probe's prompt, recorded verbatim because the spec requires it and because a prompt
#: paraphrased in a report is a different experiment. Every clause is a bound the model
#: card names (single person, head visible, near subject) or a finding this experiment
#: already made: B1's H2c missed by predicting a blank face would detect weakly, and the
#: measurement said the weak landmarks were the OCCLUDED far-side arm — so the staging asks
#: for limbs held clear of the torso, and the arms are what B2's sheet inspects first.
PROBE_PROMPT = (
    "A single dancer alone in an empty studio, filmed head to feet in one continuous "
    "mid-shot. She dances slowly and evenly, facing the camera, with her arms held out "
    "away from her body and her legs apart, so that her arms and legs stay clear of her "
    "torso and never cross or overlap each other. Plain flat pale grey backdrop, even "
    "soft studio lighting, no props, no furniture. The camera does not move. One person "
    "only, whole body visible in frame at all times."
)

WIDTH, HEIGHT, LENGTH = 832, 480, 65

#: Weights, all covered by the licence map — the two Wan 2.2 T2V experts, the umt5 text
#: encoder and the Wan 2.1 VAE. The fp8-scaled files are Comfy-Org repacks of the mapped
#: Apache weights; the map's repack ruling (2026-08-11) says the upstream grant governs and
#: the repack asserts nothing itself, so no new rows. NO LoRA of any kind is loaded.
UNET_HIGH = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
UNET_LOW = "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
CLIP_NAME = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE_NAME = "wan_2.1_vae.safetensors"


def shifted_sigma(sigma, shift):
    """The flow-matching shift ComfyUI's `ModelSamplingSD3` applies."""
    return shift * sigma / (1.0 + (shift - 1.0) * sigma)


def boundary_step(steps, shift, boundary):
    """The step index at which the high-noise expert hands over to the low-noise one.

    Returns the first index whose shifted sigma falls BELOW the boundary — so every step
    the reference would run on the high-noise expert stays on it, and the handover is not
    half a step early. The whole table is returned as evidence, because a split nobody can
    recompute is a magic number.
    """
    table = []
    crossing = None
    for i in range(steps + 1):
        sigma = 1.0 - i / float(steps)
        s = shifted_sigma(sigma, shift)
        high = s >= boundary
        table.append({"step": i, "sigma": sigma, "sigma_shifted": s,
                      "timestep": s * REFERENCE["num_train_timesteps"]["value"],
                      "expert": "high" if high else "low"})
        if crossing is None and not high:
            crossing = i
    if crossing is None:
        raise RG.RouteGate(
            f"the shifted sigma never falls below the boundary {boundary} across {steps} "
            f"steps, so the low-noise expert would never run", {"table": table[:6]})
    if crossing == 0:
        raise RG.RouteGate(
            f"the shifted sigma is below the boundary {boundary} from step 0, so the "
            f"high-noise expert would never run", {"table": table[:6]})
    return crossing, table


def build_graph(seed, steps=None, shift=None, boundary=None,
                prompt=PROBE_PROMPT, negative=REFERENCE_NEGATIVE):
    """The API-format graph. Node ids are stable so the record and the graph line up."""
    steps = REFERENCE["sample_steps"]["value"] if steps is None else steps
    shift = REFERENCE["sample_shift"]["value"] if shift is None else shift
    boundary = REFERENCE["boundary"]["value"] if boundary is None else boundary
    split, table = boundary_step(steps, shift, boundary)

    g = {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": UNET_HIGH, "weight_dtype": "default"}},
        "11": {"class_type": "UNETLoader",
               "inputs": {"unet_name": UNET_LOW, "weight_dtype": "default"}},
        "12": {"class_type": "ModelSamplingSD3",
               "inputs": {"shift": shift, "model": ["10", 0]}},
        "13": {"class_type": "ModelSamplingSD3",
               "inputs": {"shift": shift, "model": ["11", 0]}},
        "20": {"class_type": "CLIPLoader",
               "inputs": {"clip_name": CLIP_NAME, "type": "wan", "device": "default"}},
        "21": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "30": {"class_type": "CLIPTextEncode",
               "inputs": {"text": prompt, "clip": ["20", 0]}},
        "31": {"class_type": "CLIPTextEncode",
               "inputs": {"text": negative, "clip": ["20", 0]}},
        "40": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": WIDTH, "height": HEIGHT, "length": LENGTH,
                          "batch_size": 1}},
        # The high-noise expert carries the run's registered seed and adds the noise.
        "50": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "enable", "noise_seed": seed, "steps": steps,
                          "cfg": REFERENCE["guide_scale_high_noise"]["value"],
                          "sampler_name": REFERENCE["sampler_name"]["value"],
                          "scheduler": REFERENCE["scheduler"]["value"],
                          "start_at_step": 0, "end_at_step": split,
                          "return_with_leftover_noise": "enable",
                          "model": ["12", 0], "positive": ["30", 0],
                          "negative": ["31", 0], "latent_image": ["40", 0]}},
        # The low-noise expert continues the same trajectory: it adds no noise, so its own
        # seed draws nothing and is inert — Gate S reports it and does not demand it.
        "51": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "disable", "noise_seed": 0, "steps": steps,
                          "cfg": REFERENCE["guide_scale_low_noise"]["value"],
                          "sampler_name": REFERENCE["sampler_name"]["value"],
                          "scheduler": REFERENCE["scheduler"]["value"],
                          "start_at_step": split, "end_at_step": 10000,
                          "return_with_leftover_noise": "disable",
                          "model": ["13", 0], "positive": ["30", 0],
                          "negative": ["31", 0], "latent_image": ["50", 0]}},
        "60": {"class_type": "VAEDecode",
               "inputs": {"samples": ["51", 0], "vae": ["21", 0]}},
        # THE LOSSLESS TAP. PNG frames straight off the decode, because the review is at
        # 0.5x from lossless and a compressed clip cannot be un-compressed later. The video
        # below is a convenience for watching, never the thing measured.
        "70": {"class_type": "SaveImage",
               "inputs": {"images": ["60", 0], "filename_prefix": "E09B2/lossless"}},
        "80": {"class_type": "CreateVideo",
               "inputs": {"images": ["60", 0], "fps": REFERENCE["fps"]["value"]}},
        "81": {"class_type": "SaveVideo",
               "inputs": {"video": ["80", 0], "filename_prefix": "E09B2/probe",
                          "format": "auto", "codec": "auto"}},
    }
    return g, {"split_step": split, "schedule": table}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="specs/E09-seeds.json")
    ap.add_argument("--out", default="outputs/E09/route")
    ap.add_argument("--seed", type=int, default=None,
                    help="which registered seed to use; defaults to the first")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)        # scripts create their own output directories
    with open(a.seeds, encoding="utf-8") as fh:
        reg = json.load(fh)
    registered = reg["seeds"]
    seed = a.seed if a.seed is not None else registered[0]

    graph, split = build_graph(seed)

    # ---- admission, in the order ruling R8 fixed. Each raises in-tool.
    gate_route = RG.verify(graph)                       # 1
    gate_s = RG.gate_s_registration(graph, registered)  # 2
    gate_l = RG.frame_legality(WIDTH, HEIGHT, LENGTH)   # 3
    if not gate_l["legal"]:
        raise RG.RouteGate(f"Gate L on the actual graph: {gate_l['problems']}", gate_l)

    graph_path = os.path.join(a.out, "E09-B2-t2v.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=False)
    graph_sha = hashlib.sha256(open(graph_path, "rb").read()).hexdigest()

    record = {
        "tool": "build_t2v_payload", "tool_version": TOOL_VERSION,
        "experiment": "E09", "stage": "B2",
        "graph": {"path": os.path.abspath(graph_path), "sha256": graph_sha,
                  "format": "api", "n_nodes": len(graph)},
        "built_not_served": (
            "This graph is built in-repo from the mapped pieces. The served "
            "`video_wan2_2_14B_t2v` template was refused by Gate ROUTE and is used here as "
            "a REFERENCE for node classes only — no value is taken from it. CLAUDE.md: a "
            "served template is a reference, never a route."),
        "weights": {"unet_high_noise": UNET_HIGH, "unet_low_noise": UNET_LOW,
                    "clip": CLIP_NAME, "vae": VAE_NAME, "loras": [],
                    "licence": ("all four covered by docs/license-map.md; the fp8-scaled "
                                "files are Comfy-Org repacks of the mapped Apache weights "
                                "and the map's repack ruling (2026-08-11) says the upstream "
                                "grant governs. No LoRA of any kind is loaded.")},
        "reference_values": REFERENCE,
        "two_expert_split": {
            "boundary": REFERENCE["boundary"]["value"],
            "shift": REFERENCE["sample_shift"]["value"],
            "steps": REFERENCE["sample_steps"]["value"],
            "formula": "sigma' = shift * sigma / (1 + (shift - 1) * sigma), sigma linear 1->0",
            "derived_split_step": split["split_step"],
            "high_noise_steps": f"0..{split['split_step']}",
            "low_noise_steps": f"{split['split_step']}..{REFERENCE['sample_steps']['value']}",
            "schedule": split["schedule"],
            "note": ("the reference switches experts on the TIMESTEP (t >= boundary * "
                     "num_train_timesteps); ComfyUI splits on a step index, so the index is "
                     "solved rather than dialled. The served template's own 2-of-4 split is "
                     "not the reference's and is not used."),
        },
        "frame": {"width": WIDTH, "height": HEIGHT, "length": LENGTH,
                  "fps": REFERENCE["fps"]["value"]},
        "prompt_verbatim": PROBE_PROMPT,
        "negative_prompt_verbatim": negative_source(),
        "seed": seed,
        "seed_registration": {"file": os.path.abspath(a.seeds), "registered": registered},
        "gates": {"ROUTE": gate_route, "S": gate_s, "L": gate_l},
    }
    rec_path = os.path.join(a.out, "E09-B2-payload-record.json")
    with open(rec_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print("BUILD_T2V_OK " + json.dumps({
        "graph": graph_path, "sha256": graph_sha, "nodes": len(graph), "seed": seed,
        "split_step": split["split_step"], "steps": REFERENCE["sample_steps"]["value"],
        "frame": [WIDTH, HEIGHT, LENGTH],
        "gate_ROUTE": gate_route["verdict"], "gate_S": gate_s["verdict"],
        "gate_L": "legal", "record": rec_path}))
    return 0


def negative_source():
    return {"text": REFERENCE_NEGATIVE,
            "source": f"{WAN22_SOURCE} wan/configs/shared_config.py sample_neg_prompt"}


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_T2V_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2)
