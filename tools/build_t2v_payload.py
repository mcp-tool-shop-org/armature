#!/usr/bin/env python
"""build_t2v_payload — E09 B2's graph, built in-repo from pieces the licence map covers.

    python tools/build_t2v_payload.py --seeds=specs/E09-A3-seeds.json --out=outputs/E09/route2

Commissioned by ruling R8 after Gate ROUTE refused the served `video_wan2_2_14B_t2v`
template. **A served template is a reference, never a route** (CLAUDE.md, measured twice on
2026-08-11), so every number below comes from a fetched document, and each one is written
into the payload with the source it came from.

--------------------------------------------------------------------------------
TWO PROFILES, and why there are two (amendment A3, 2026-08-12)

The 2026-08-11 probe ran the `derived` profile and returned a near-still donor (mean
consecutive-frame pixel difference 0.703/255) with the ankles outside the image on 100% of
frames. A3 ruled that run failed, cause unlocated, and named two suspects: the DERIVED
step-26/40 expert split, and the euler/simple pair that profile could not source. A3
authorises one generation on values taken **exactly from Wan's own reference
documentation** instead.

    `derived`   — the probe's. Wan's native config + a split solved from the boundary.
                  SUPERSEDED, kept runnable, because a falsified approach that leaves the
                  tree becomes doctrine again.
    `reference` — A3's, and the default. Every sampling value documented, none solved.

**Where "Wan's own reference documentation" leads, in order. Each link fetched 2026-08-12
and banked under `outputs/E09/route2/` with its sha256:**

1. `https://github.com/Wan-Video/Wan2.2` README (Apache-2.0), line 41, verbatim:
   "Jul 28, 2025: Wan2.2 has been integrated into ComfyUI ([CN](...) | [EN](...)). Enjoy!"
   Wan's own repo carries NO ComfyUI numbers and designates that page for them. So the
   documented ComfyUI trajectory is the one that page serves — by the model authors' own
   pointer, not by this seat's choice of a convenient source.
2. `https://docs.comfy.org/tutorials/video/wan/wan2_2` — states no numbers in prose; it
   serves the workflow JSON and tells the reader to load it.
3. That JSON, in `Comfy-Org/workflow_templates` (MIT), at two PINNED commits:
     * `5d6089c4250f` (2025-08-02) — the last revision in which the file contains ONLY the
       non-distilled workflow: 16 nodes, no LoRA node of any kind anywhere in it.
     * `dcc00d29d79d` (2025-09-29), whose commit message names it — "Fix Wan2.2 t2v
       template (non-lightning workflow) (#205)".
   The two agree on every SAMPLING value used here, and the agreement is recorded rather
   than one being picked. They do NOT agree on the negative prompt — measured, not
   assumed, by a check that failed on this seat's first claim: `dcc00d29d79d` appends
   two tokens to Wan's own string (`NEGATIVE_DRIFT` below). This graph uses Wan's.
   WARNING: the file at `main` agrees with neither — it now carries only the lightx2v
   4-step variant, which Gate ROUTE excludes, so a later re-fetch of `main` is not a
   re-fetch of this.

The wiring of those revisions was traced through their `links` array in code, not read off
node order, and it is structurally identical to the graph built here: high-noise UNET ->
ModelSamplingSD3 -> KSamplerAdvanced(add_noise=enable, start 0, leftover=enable) ->
KSamplerAdvanced(add_noise=disable, leftover=disable) -> VAEDecode.

**What is NOT taken from the reference, and why.** The frame stays 832x480x65 (the
reference workflow's own latent is 640x640x81). A3 authorises two changes — the sampling
values and the prompt — and this run is simultaneously the graph-fault diagnostic and the
donor re-roll. A third moving variable would leave the diagnostic unable to locate
anything. The frame is therefore held at the probe's, and the aspect ratio is reported as
a named, unexercised lever rather than quietly pulled.

--------------------------------------------------------------------------------
The `derived` profile's trajectory, and where each number is from

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

#: A3's profile. Every value below is READ OFF a fetched document, not solved for. The two
#: pinned template revisions agree on all of them; `agrees_at` records both, because a
#: number confirmed in two independent revisions is a different object from one read once.
COMFY_TEMPLATE_SOURCE = (
    "Comfy-Org/workflow_templates (MIT), templates/video_wan2_2_14B_t2v.json — the "
    "workflow served by https://docs.comfy.org/tutorials/video/wan/wan2_2, which the "
    "Wan-Video/Wan2.2 README itself designates as the ComfyUI reference. Fetched "
    "2026-08-12 at the two pinned commits below; NOT from `main`, which now carries only "
    "the lightx2v 4-step variant Gate ROUTE excludes")

COMFY_PINS = ["5d6089c4250f", "dcc00d29d79d"]

COMFY_REFERENCE = {
    "sample_steps": {
        "value": 20,
        "source": f"{COMFY_TEMPLATE_SOURCE}; KSamplerAdvanced.steps on BOTH samplers",
        "agrees_at": COMFY_PINS},
    "split_step": {
        "value": 10,
        "source": (f"{COMFY_TEMPLATE_SOURCE}; the high-noise KSamplerAdvanced runs "
                   f"start_at_step=0 end_at_step=10 and the low-noise one runs "
                   f"start_at_step=10 end_at_step=10000. READ OFF the workflow, not "
                   f"solved from the boundary — which is the whole point of this profile"),
        "agrees_at": COMFY_PINS},
    "sample_shift": {
        "value": 8.0,
        "source": (f"{COMFY_TEMPLATE_SOURCE}; ModelSamplingSD3.shift, the same value on "
                   f"both branches. Wan's own native config says 12.0; the ComfyUI "
                   f"reference says 8.0, and this profile follows the ComfyUI reference "
                   f"because that is the one that also fixes the step index"),
        "agrees_at": COMFY_PINS},
    "cfg": {
        "value": 3.5,
        "source": (f"{COMFY_TEMPLATE_SOURCE}; KSamplerAdvanced.cfg, the SAME 3.5 on both "
                   f"samplers — not Wan's native asymmetric (3.0 low, 4.0 high)"),
        "agrees_at": COMFY_PINS},
    "sampler_name": {
        "value": "euler",
        "source": (f"{COMFY_TEMPLATE_SOURCE}; KSamplerAdvanced.sampler_name on both. "
                   f"A3 named this a suspect because the `derived` profile could not "
                   f"source it. It is now sourced, and the value is unchanged"),
        "agrees_at": COMFY_PINS},
    "scheduler": {
        "value": "simple",
        "source": f"{COMFY_TEMPLATE_SOURCE}; KSamplerAdvanced.scheduler on both",
        "agrees_at": COMFY_PINS},
    "fps": {
        "value": 16,
        "source": (f"{COMFY_TEMPLATE_SOURCE}; CreateVideo.fps — which coincides with "
                   f"{WAN22_SOURCE} shared_config.sample_fps. Both are recorded"),
        "agrees_at": COMFY_PINS},
}

#: What A3's profile changes relative to the probe's, so the report cannot describe the
#: run without the delta. This table is the diagnostic's independent variable.
PROFILE_DELTA = [
    {"value": "sample_steps", "derived": 40, "reference": 20},
    {"value": "expert split", "derived": "step 26 of 40 (65% of steps on high-noise)",
     "reference": "step 10 of 20 (50% of steps on high-noise)"},
    {"value": "sample_shift", "derived": 12.0, "reference": 8.0},
    {"value": "cfg", "derived": "4.0 high / 3.0 low", "reference": "3.5 on both"},
    {"value": "sampler_name", "derived": "euler (unsourced)",
     "reference": "euler (sourced)"},
    {"value": "scheduler", "derived": "simple (unsourced)", "reference": "simple (sourced)"},
    {"value": "how the split was obtained", "derived": "solved from boundary x shift",
     "reference": "read off the reference workflow"},
]

#: The Wan 2.2 reference negative prompt, verbatim from `shared_config.sample_neg_prompt`.
#: Copied from the fetched file, not from the served template — the two agree because both
#: descend from this source, which is a coincidence worth naming rather than leaning on.
#: CORRECTED 2026-08-12, by the check that was written to catch exactly this. The claim
#: this seat first wrote — "byte-identical at both pinned commits" — is FALSE, and the test
#: `test_the_reference_negative_prompt...` failed on it before any credit was spent. What
#: is measured: `5d6089c4250f` reproduces Wan's `shared_config.sample_neg_prompt`
#: byte-for-byte; `dcc00d29d79d` APPENDS two tokens to it (see NEGATIVE_DRIFT below). The
#: two pinned revisions therefore agree on every SAMPLING value and disagree on the
#: negative prompt. This graph uses Wan's own string — the upstream source both descend
#: from — and the drift is recorded rather than inherited.
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

#: A3's prompt. Every edit below answers a MEASURED observation from the probe, and the
#: log travels with the graph so the report cannot describe the change from memory.
PROMPT_A3 = (
    "A single dancer alone in an empty studio, filmed in one continuous full-length wide "
    "shot from a fixed camera placed far back, so that her entire body is inside the "
    "frame from the top of her head down to her feet on the floor, with empty space above "
    "her head and the studio floor visible below her feet. She dances energetically with "
    "large, fast, sweeping movements of her whole body: she swings both arms wide out to "
    "the sides and up overhead, lifts her knees high, and steps from side to side, "
    "shifting her weight from one foot to the other. Her arms swing clear of her torso "
    "and her legs stay apart, so her limbs never cross or overlap her body. She faces the "
    "camera throughout. Plain flat pale grey backdrop, even soft studio lighting, no "
    "props, no furniture. The camera does not move, does not pan and does not zoom. One "
    "person only, her whole body and both of her feet visible in every frame."
)

PROMPT_CHANGE_LOG = [
    {"change": "deleted the words 'mid-shot'",
     "answers": ("`mid-shot` is a term of art for a waist-up framing, and it sat in the "
                 "SAME sentence as 'head to feet'. The probe delivered the mid-shot: all "
                 "six lower-leg landmarks outside the image on 100% of frames. A prompt "
                 "that contradicts itself lets the model pick, and it picked"),
     "replaced_with": "'full-length wide shot', 'camera placed far back'"},
    {"change": "deleted 'dances slowly and evenly'",
     "answers": ("the probe's mean consecutive-frame pixel difference was 0.703/255. The "
                 "prompt asked for slow and got slow"),
     "replaced_with": ("'energetically with large, fast, sweeping movements of her whole "
                       "body', with the movements named — arms wide and overhead, knees "
                       "high, weight shifting foot to foot")},
    {"change": ("re-expressed the anti-occlusion clause as motion rather than as a held "
                "configuration"),
     "answers": ("'arms held out away from her body and her legs apart' describes a POSE, "
                 "not a movement, and the probe held it. The property B1/B2 measured as "
                 "load-bearing — limbs clear of the torso, because the weakest landmark "
                 "in B1 was the occluded far-side arm — is kept, but as 'her arms swing "
                 "clear of her torso'"),
     "replaced_with": "'Her arms swing clear of her torso and her legs stay apart'"},
    {"change": "added the ground plane and the headroom explicitly",
     "answers": ("nothing in the probe's prompt forced the floor into the frame, so "
                 "'whole body visible' had no anchor the model could fail visibly"),
     "replaced_with": ("'the studio floor visible below her feet', 'empty space above her "
                       "head', 'both of her feet visible in every frame'")},
    {"change": "kept unchanged",
     "answers": ("the model card's own in-scope bounds and B1/B2's detectability "
                 "findings: one person, plain flat backdrop, even lighting, fixed camera, "
                 "facing the camera. 'turns' was deliberately NOT added — a turning "
                 "dancer self-occludes and the detector is the next stage"),
     "replaced_with": "—"},
]

#: Measured 2026-08-12: what the later pinned revision adds to Wan's negative prompt. Not
#: used — recorded, because a difference found and then dropped from the record is a
#: difference the next session gets to rediscover.
NEGATIVE_DRIFT = {
    "5d6089c4250f": "byte-identical to Wan's shared_config.sample_neg_prompt",
    "dcc00d29d79d": "the same string with '，裸露，NSFW' appended",
    "this_graph_uses": ("Wan's own shared_config.sample_neg_prompt, the upstream source "
                        "both revisions descend from"),
}

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


def trajectory(profile):
    """The sampling values for a profile, with the arithmetic that produced or checks them.

    `derived` solves the split from Wan's native boundary. `reference` reads it off the
    documented workflow and then runs the SAME arithmetic as a cross-check — reported as a
    diagnostic, never as a gate, because the reference is the authority here and an
    arithmetic disagreement with it is a finding rather than a fault.
    """
    if profile == "derived":
        steps = REFERENCE["sample_steps"]["value"]
        shift = REFERENCE["sample_shift"]["value"]
        boundary = REFERENCE["boundary"]["value"]
        split, table = boundary_step(steps, shift, boundary)
        return {"profile": "derived", "steps": steps, "shift": shift, "split_step": split,
                "cfg_high": REFERENCE["guide_scale_high_noise"]["value"],
                "cfg_low": REFERENCE["guide_scale_low_noise"]["value"],
                "sampler_name": REFERENCE["sampler_name"]["value"],
                "scheduler": REFERENCE["scheduler"]["value"],
                "fps": REFERENCE["fps"]["value"],
                "split_origin": "SOLVED from boundary x shift",
                "schedule": table, "values": REFERENCE}
    if profile != "reference":
        raise RG.RouteGate(f"unknown profile {profile!r}", {"known": ["reference", "derived"]})

    steps = COMFY_REFERENCE["sample_steps"]["value"]
    shift = COMFY_REFERENCE["sample_shift"]["value"]
    split = COMFY_REFERENCE["split_step"]["value"]
    cfg = COMFY_REFERENCE["cfg"]["value"]
    # Cross-check only: where would Wan's own native boundary put the handover, on THIS
    # schedule? If the documented index and the arithmetic disagree, the report says so.
    solved, table = boundary_step(steps, shift, REFERENCE["boundary"]["value"])
    return {"profile": "reference", "steps": steps, "shift": shift, "split_step": split,
            "cfg_high": cfg, "cfg_low": cfg,
            "sampler_name": COMFY_REFERENCE["sampler_name"]["value"],
            "scheduler": COMFY_REFERENCE["scheduler"]["value"],
            "fps": COMFY_REFERENCE["fps"]["value"],
            "split_origin": "READ OFF the documented reference workflow",
            "schedule": table, "values": COMFY_REFERENCE,
            "boundary_cross_check": {
                "documented_split_step": split,
                "step_wan_native_boundary_would_put_it_at": solved,
                "wan_native_boundary": REFERENCE["boundary"]["value"],
                "agree_within_one_step": abs(solved - split) <= 1,
                "status": "DIAGNOSTIC, not a gate — the documented value governs"}}


def build_graph(seed, profile="reference", prompt=None, negative=REFERENCE_NEGATIVE):
    """The API-format graph. Node ids are stable so the record and the graph line up.

    `profile` has no silent default that could be the superseded one: it defaults to the
    route A3 authorises, and asking for `derived` is an explicit act.
    """
    t = trajectory(profile)
    steps, split = t["steps"], t["split_step"]
    shift = t["shift"]
    table = t["schedule"]
    if prompt is None:
        prompt = PROMPT_A3 if profile == "reference" else PROBE_PROMPT

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
                          "cfg": t["cfg_high"],
                          "sampler_name": t["sampler_name"],
                          "scheduler": t["scheduler"],
                          "start_at_step": 0, "end_at_step": split,
                          "return_with_leftover_noise": "enable",
                          "model": ["12", 0], "positive": ["30", 0],
                          "negative": ["31", 0], "latent_image": ["40", 0]}},
        # The low-noise expert continues the same trajectory: it adds no noise, so its own
        # seed draws nothing and is inert — Gate S reports it and does not demand it.
        "51": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "disable", "noise_seed": 0, "steps": steps,
                          "cfg": t["cfg_low"],
                          "sampler_name": t["sampler_name"],
                          "scheduler": t["scheduler"],
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
               "inputs": {"images": ["60", 0], "fps": t["fps"]}},
        "81": {"class_type": "SaveVideo",
               "inputs": {"video": ["80", 0], "filename_prefix": "E09B2/probe",
                          "format": "auto", "codec": "auto"}},
    }
    return g, dict(t, prompt=prompt)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="specs/E09-A3-seeds.json")
    ap.add_argument("--out", default="outputs/E09/route2")
    ap.add_argument("--seed", type=int, default=None,
                    help="which registered seed to use; defaults to the first")
    ap.add_argument("--profile", default="reference", choices=["reference", "derived"],
                    help="reference = A3's documented trajectory; derived = the "
                         "superseded probe's, kept runnable")
    ap.add_argument("--tag", default="A3", help="goes in the written filenames")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)        # scripts create their own output directories
    with open(a.seeds, encoding="utf-8") as fh:
        reg = json.load(fh)
    registered = reg["seeds"]
    seed = a.seed if a.seed is not None else registered[0]

    graph, split = build_graph(seed, profile=a.profile)

    # ---- admission, in the order ruling R8 fixed. Each raises in-tool.
    gate_route = RG.verify(graph)                       # 1
    gate_s = RG.gate_s_registration(graph, registered)  # 2
    gate_l = RG.frame_legality(WIDTH, HEIGHT, LENGTH)   # 3
    if not gate_l["legal"]:
        raise RG.RouteGate(f"Gate L on the actual graph: {gate_l['problems']}", gate_l)

    graph_path = os.path.join(a.out, f"E09-B2-{a.tag}-t2v.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=False)
    graph_sha = hashlib.sha256(open(graph_path, "rb").read()).hexdigest()

    record = {
        "tool": "build_t2v_payload", "tool_version": TOOL_VERSION,
        "experiment": "E09", "stage": "B2", "amendment": "A3", "profile": a.profile,
        "graph": {"path": os.path.abspath(graph_path), "sha256": graph_sha,
                  "format": "api", "n_nodes": len(graph)},
        "built_not_served": (
            "This graph is built in-repo from the mapped pieces. The template the docs "
            "page serves is used as a REFERENCE for documented VALUES and for node "
            "classes; no template file is submitted, and the graph submitted is this one, "
            "which passes Gate ROUTE. CLAUDE.md: a served template is a reference, never "
            "a route. The template revision at `main` is the excluded lightx2v 4-step "
            "variant and is NOT the revision these values come from."),
        "weights": {"unet_high_noise": UNET_HIGH, "unet_low_noise": UNET_LOW,
                    "clip": CLIP_NAME, "vae": VAE_NAME, "loras": [],
                    "licence": ("all four covered by docs/license-map.md; the fp8-scaled "
                                "files are Comfy-Org repacks of the mapped Apache weights "
                                "and the map's repack ruling (2026-08-11) says the upstream "
                                "grant governs. No LoRA of any kind is loaded.")},
        "documentation_chain": {
            "1_wan_own_readme": {
                "url": "https://github.com/Wan-Video/Wan2.2",
                "licence": "Apache-2.0",
                "fetched": "2026-08-12",
                "banked": "outputs/E09/route2/wan22_README.md",
                "quote_line_41": ("Jul 28, 2025: Wan2.2 has been integrated into ComfyUI "
                                  "([CN](https://docs.comfy.org/zh-CN/tutorials/video/wan/"
                                  "wan2_2) | [EN](https://docs.comfy.org/tutorials/video/"
                                  "wan/wan2_2)). Enjoy!"),
                "why_it_matters": ("Wan's own repo carries no ComfyUI numbers and points "
                                   "at that page for them, so the ComfyUI trajectory this "
                                   "run uses is the one the MODEL AUTHORS designate")},
            "2_the_designated_page": {
                "url": "https://docs.comfy.org/tutorials/video/wan/wan2_2",
                "fetched": "2026-08-12",
                "banked": "outputs/E09/route2/docs_comfy_wan2_2.html",
                "finding": "states no sampling numbers in prose; it serves the workflow"},
            "3_the_served_workflow": {
                "repo": "Comfy-Org/workflow_templates", "licence": "MIT",
                "path": "templates/video_wan2_2_14B_t2v.json",
                "pinned_commits": COMFY_PINS,
                "banked": [f"outputs/E09/route2/template_{s}.json" for s in COMFY_PINS],
                "both_agree": True,
                "main_is_different": ("`main` now carries only the lightx2v 4-step "
                                      "variant, which Gate ROUTE excludes")},
            "licence_note_for_the_advisor": (
                "the templates repo is MIT. It is cited as DOCUMENTATION for numeric "
                "settings, not loaded as a dependency and not copied as code, so this "
                "seat does not add a licence-map row for it — the advisor rules on "
                "whether the map should carry one anyway")},
        "reference_values": split["values"],
        "wan_native_values_for_comparison": REFERENCE,
        "two_expert_split": {
            "profile": a.profile,
            "split_origin": split["split_origin"],
            "shift": split["shift"],
            "steps": split["steps"],
            "split_step": split["split_step"],
            "high_noise_steps": f"0..{split['split_step']}",
            "low_noise_steps": f"{split['split_step']}..{split['steps']}",
            "formula": "sigma' = shift * sigma / (1 + (shift - 1) * sigma), sigma linear 1->0",
            "boundary_cross_check": split.get("boundary_cross_check"),
            "schedule": split["schedule"]},
        "what_changed_from_the_probe": PROFILE_DELTA,
        "frame": {"width": WIDTH, "height": HEIGHT, "length": LENGTH, "fps": split["fps"],
                  "held_at_the_probes_frame_on_purpose": (
                      "the reference workflow's own latent is 640x640x81. A3 authorises "
                      "two changes (sampling values, prompt); a third moving variable "
                      "would leave the diagnostic unable to locate anything. Aspect ratio "
                      "is a named, unexercised lever on the framing clause")},
        "prompt_verbatim": split["prompt"],
        "prompt_change_log": PROMPT_CHANGE_LOG,
        "probe_prompt_for_comparison": PROBE_PROMPT,
        "negative_prompt_verbatim": negative_source(),
        "seed": seed,
        "seed_registration": {"file": os.path.abspath(a.seeds), "registered": registered},
        "gates": {"ROUTE": gate_route, "S": gate_s, "L": gate_l},
    }
    rec_path = os.path.join(a.out, f"E09-B2-{a.tag}-payload-record.json")
    with open(rec_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print("BUILD_T2V_OK " + json.dumps({
        "profile": a.profile, "graph": graph_path, "sha256": graph_sha,
        "nodes": len(graph), "seed": seed,
        "split_step": split["split_step"], "steps": split["steps"],
        "shift": split["shift"], "cfg": [split["cfg_high"], split["cfg_low"]],
        "sampler": split["sampler_name"], "scheduler": split["scheduler"],
        "split_origin": split["split_origin"],
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
