#!/usr/bin/env python
r"""build_i2v_payload — E11's `WanImageToVideo` graph, built in this repo.

    python tools\build_i2v_payload.py --uploads=<uploads.json> --out=<dir>
           --negative-source=<wan22_shared_config.py> --seeds-registry=specs\E11-seeds.json
           --e08-record=<E08-probe-payload-record.json> [--seed=2026081231]

The no-control route. A render of the performer is the first frame, a prompt describes the
shot, and **nothing else conditions the generation** — no pose sticks, no reference image,
no control video, no clip-vision embedding. Everything after frame 0 is the model's.

**Built here, never served.** Measured on this route 2026-08-12, and it is the third
instance of the pattern `docs/license-map.md` records as trap #3: the served
`video_wan2_2_14B_i2v` template at `main` presents **5 top-level nodes and hides 30 inside
a subgraph blueprint**, and what is hidden is the licence map's EXCLUDED lightx2v 4-step
tier — `wan2.2_i2v_lightx2v_4steps_lora_{high,low}_noise.safetensors` at strength 1.0,
4 steps, cfg 1.0, shift 5.0, with the high-noise sampler's `control_after_generate` set to
`randomize`. That graph could not pass Gate ROUTE or Gate S. A served template is a
reference, never a route.

--------------------------------------------------------------------------------
Where every number comes from

The trajectory is READ OFF the LoRA-free revision of the same template family, not solved
and not carried over from the Animate route. Two pinned commits of
`Comfy-Org/workflow_templates` (MIT — `docs/license-map.md`, *Services and tools*),
`templates/video_wan2_2_14B_i2v.json`, both fetched 2026-08-12 and banked with their
sha256 under `outputs/E11/route/`:

  * `5d6089c4250f` — 17 nodes, **no LoRA node of any kind anywhere in the file**. This is
    the revision the values come from.
  * `dcc00d29d79d` — carries the distilled path live and the non-distilled path bypassed
    (`mode = 4`). Its bypassed branch pins the SAME values, so the two revisions agree and
    the agreement is recorded rather than one being picked.

    steps 20 · split at step 10 · shift 8.0 · cfg 3.5 · euler · simple · fps 16

Its wiring was traced through the file's own `links` array in code rather than read off
node order, and it is the wiring built below: LoadImage -> WanImageToVideo.start_image;
both text encodes -> the conditioning node; the node's positive/negative to BOTH samplers
and its latent to the first; high-noise KSamplerAdvanced (add_noise enable, 0..split,
leftover enable) -> low-noise (add_noise disable, split..10000, leftover disable) ->
VAEDecode. `clip_vision_output` is unconnected there and is unconnected here.

--------------------------------------------------------------------------------
What is deliberately absent, and the andon that keeps it absent

`verify_topology` refuses the graph if it contains ANY conditioning class that can carry a
driving signal (`WanVaceToVideo`, `WanAnimateToVideo`, `Wan22FunControlToVideo`, ...), if
`clip_vision_output` is wired, or if any node other than the Gate B probe reads a second
uploaded image. E11's whole question is what the model does with no driving signal; a
graph that quietly acquired one would answer a different question and every other gate
would pass on it.

--------------------------------------------------------------------------------
"Pinned verbatim" is measured here, not asserted

The positive and negative are rebuilt from E08's own sources through E08's own code
(`build_animate_payload.identity_clause` / `read_negative`) and then compared **byte for
byte against E08's committed payload record**, which this tool requires as an input. If
either string has drifted by a character the build halts. The two-pipeline sheet's claim —
same prompt, different route — is the experiment's load-bearing comparability claim, and
E09's citation check already fired once on a negative somebody described from memory.

--------------------------------------------------------------------------------
The gates

* **Gate L** — `gates.g1_generator_legality` on the `wan-i2v` profile, raised in-tool
  before a single node is emitted.
* **Gate S** — `gates.gate_s_seed_registration` against `specs/E11-seeds.json`, committed
  before the first submission.
* **topology** — checked in code, because a `dry_run` PASS does not prove link sanity.
* **Gate ROUTE** — `route_gates.verify` on the graph this tool just built, with the frame
  supplied: `WanImageToVideo` sizes its own latent, and E08 measured what Gate L does on a
  graph whose latent it cannot find (it reported it legal having examined zero frames).
  It runs again, separately, on the saved file (`gate_saved_graph.py`).

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory. It submits nothing and spends nothing.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.canon import add_spend_flags, gate_write  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

import build_animate_payload as E08  # noqa: E402  - the prompt's source of record

TOOL_VERSION = "E11.1"
EXPERIMENT = "E11"

#: E11's frame. 65 @ 16 fps is E08's, held deliberately: the deliverable this experiment
#: exists for is E08's painted probe beside E11's at true tempo, and a different length or
#: rate would put a second variable inside a comparison that already spans two models.
#: E10's ruling — "the more fps the better" — is a ruling about DRIVING density on the
#: skeletal route; there is no driving signal here, so it has nothing to move.
WIDTH, HEIGHT, LENGTH, FPS = 832, 480, 65, 16

#: Weights. Comfy-Org repacks of the Apache-2.0 Wan 2.2 I2V-A14B experts (map row fetched
#: 2026-08-12) — the 2026-08-11 repack ruling governs: the upstream grant applies and the
#: repack asserts nothing itself. umt5-xxl Apache-2.0; wan_2.1_vae is the Wan 2.1 tier.
#: The Kijai `Wan2_2-I2V-A14B-*_KJ` variants the catalog also serves are NOT used: they
#: are a third-party repack the map has no row for.
#: **NO LoRA of any kind is loaded** — see the trap above.
UNET_HIGH = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
UNET_LOW = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
CLIP_NAME = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE_NAME = "wan_2.1_vae.safetensors"

TEMPLATE_SOURCE = (
    "Comfy-Org/workflow_templates (MIT), templates/video_wan2_2_14B_i2v.json — the "
    "workflow served by https://docs.comfy.org/tutorials/video/wan/wan2_2, which the "
    "Wan-Video/Wan2.2 README itself designates as the ComfyUI reference. Fetched "
    "2026-08-12 at the two pinned commits below; NOT from `main`, which carries only the "
    "excluded lightx2v 4-step variant inside a subgraph blueprint")
TEMPLATE_PINS = ["5d6089c4250f", "dcc00d29d79d"]

#: Every sampling value with the source it came from. A value that cannot name its source
#: does not belong in the graph.
TRAJECTORY = {
    "steps": {"value": 20, "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.steps on both",
              "agrees_at": TEMPLATE_PINS},
    "split_step": {"value": 10,
                   "source": (f"{TEMPLATE_SOURCE}; the high-noise sampler runs "
                              f"start_at_step=0 end_at_step=10 and the low-noise one runs "
                              f"start_at_step=10 end_at_step=10000. READ OFF the workflow, "
                              f"not solved from a boundary"),
                   "agrees_at": TEMPLATE_PINS},
    "shift": {"value": 8.0,
              "source": (f"{TEMPLATE_SOURCE}; ModelSamplingSD3.shift on both branches "
                         f"(the file stores 8.000000000000002 on one and 8 on the other; "
                         f"they are the same value to float precision and 8.0 is used)"),
              "agrees_at": TEMPLATE_PINS},
    "cfg": {"value": 3.5, "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.cfg on both",
            "agrees_at": TEMPLATE_PINS},
    "sampler_name": {"value": "euler",
                     "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.sampler_name on both",
                     "agrees_at": TEMPLATE_PINS},
    "scheduler": {"value": "simple",
                  "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.scheduler on both",
                  "agrees_at": TEMPLATE_PINS},
    "fps": {"value": FPS,
            "source": (f"{TEMPLATE_SOURCE}; CreateVideo.fps — which coincides with "
                       f"Wan-Video/Wan2.2 shared_config.sample_fps. Both are recorded, and "
                       f"it is also E08's rate, which is what the A/B needs"),
            "agrees_at": TEMPLATE_PINS},
}

#: What differs from E08's arm, enumerated so no reader has to reconstruct it. The spec
#: bounds this honestly as a ROUTE comparison, not a single-variable one; this table is
#: what that sentence means in numbers.
DELTA_FROM_E08 = [
    {"value": "conditioning node", "E08": "WanAnimateToVideo", "E11": "WanImageToVideo"},
    {"value": "diffusion weights", "E08": "wan2.2_animate_14B_bf16 (one expert)",
     "E11": "wan2.2_i2v_{high,low}_noise_14B_fp8_scaled (two experts, MoE)"},
    {"value": "text encoder", "E08": "umt5_xxl_fp16",
     "E11": "umt5_xxl_fp8_e4m3fn_scaled (the I2V reference workflow's own)"},
    {"value": "driving signal", "E08": "65 AAPose-20 stick frames on pose_video",
     "E11": "NONE — this is the experiment"},
    {"value": "identity conditioning", "E08": "letterboxed twin on reference_image",
     "E11": "the start frame itself; no reference socket exists on this node"},
    {"value": "sampler", "E08": "1 x KSampler, uni_pc/simple, 20 steps, cfg 6.0",
     "E11": "2 x KSamplerAdvanced, euler/simple, 20 steps split at 10, cfg 3.5"},
    {"value": "shift", "E08": "8.0 (inherited, undocumented for Animate)",
     "E11": "8.0 (read off the I2V reference workflow)"},
    {"value": "prompt / negative", "E08": "—", "E11": "byte-identical, checked in-tool"},
    {"value": "frame", "E08": "832x480x65 @ 16 fps", "E11": "832x480x65 @ 16 fps"},
]


class PayloadError(ArmatureError):
    """The payload could not be built as specified."""


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True,
                    help="JSON: {start_frame: <server name>}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--negative-source", default=None,
                    help="path to Wan's shared_config.py; the negative is READ from it "
                         "rather than retyped")
    ap.add_argument("--e08-record", required=True,
                    help="E08's committed payload record. The prompt and negative built "
                         "here are compared byte for byte against it and the build halts "
                         "on any drift — 'pinned verbatim' is a measurement, not a claim")
    ap.add_argument("--seeds-registry", default=None)
    ap.add_argument("--experiment", default=EXPERIMENT)
    ap.add_argument("--length", type=int, default=LENGTH,
                    help="frame count (argparse eats leading minus signs, so pass flags "
                         "as --flag=value)")
    ap.add_argument("--fps", type=float, default=FPS)
    add_spend_flags(ap)
    return ap.parse_args(argv)


def pin_against_e08(positive, negative, e08_record_path):
    """Gate PIN · ANDON — the strings are E08's, byte for byte. Raises on any drift.

    Both are rebuilt here from their own sources through E08's own code, so this is not a
    tautology: the identity clause is re-read from facet's twin JSON and the negative is
    re-parsed from the banked Wan config, and either file could have moved under the
    experiment. What this compares is *today's* rebuild against the string E08 actually
    submitted, which is the only object the A/B's "same prompt" claim can mean.
    """
    with open(e08_record_path, encoding="utf-8") as fh:
        rec = json.load(fh)
    ev = {"gate": "PIN", "e08_record": os.path.abspath(e08_record_path),
          "e08_experiment": rec.get("experiment"), "e08_seed": rec.get("seed")}
    problems = []
    for field, ours in (("positive", positive), ("negative", negative)):
        theirs = rec.get(field)
        ev[field] = {
            "sha256_built": hashlib.sha256(ours.encode("utf-8")).hexdigest(),
            "sha256_e08": (hashlib.sha256(theirs.encode("utf-8")).hexdigest()
                           if isinstance(theirs, str) else None),
            "len_built": len(ours),
            "len_e08": len(theirs) if isinstance(theirs, str) else None,
        }
        if not isinstance(theirs, str):
            problems.append(f"E08's record carries no {field} string to pin against")
        elif theirs != ours:
            problems.append(
                f"the {field} rebuilt here is not E08's: {len(ours)} chars against "
                f"{len(theirs)}, sha256 {ev[field]['sha256_built'][:16]} against "
                f"{ev[field]['sha256_e08'][:16]}")
    if problems:
        raise PayloadError(
            "the prompt this graph would submit is not the one E08 submitted, so the "
            "two-pipeline sheet would be comparing two prompts as well as two routes: "
            + "; ".join(problems))
    ev["verdict"] = "positive and negative byte-identical to E08's submitted strings"
    return ev


def build(uploads, seed, negative, positive, registry, experiment=EXPERIMENT,
          length=LENGTH, fps=FPS):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists."""
    gate_s = gates.gate_s_seed_registration(seed, registry, experiment,
                                            seed_was_explicit=seed is not None)
    seed_used = seed if seed is not None else (sorted(registry)[0] if registry else 0)
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-i2v")

    steps = TRAJECTORY["steps"]["value"]
    split = TRAJECTORY["split_step"]["value"]
    shift = TRAJECTORY["shift"]["value"]
    cfg = TRAJECTORY["cfg"]["value"]
    sampler = TRAJECTORY["sampler_name"]["value"]
    scheduler = TRAJECTORY["scheduler"]["value"]

    start_name = uploads["start_frame"]

    wf = {
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
               "inputs": {"text": positive, "clip": ["20", 0]}},
        "31": {"class_type": "CLIPTextEncode",
               "inputs": {"text": negative, "clip": ["20", 0]}},
        # The GLB, as an image. One frame, uploaded once.
        "40": {"class_type": "LoadImage", "inputs": {"image": start_name}},
        # Gate B probe: the start frame as the conditioning node receives it, saved so it
        # can be compared pixel for pixel against the local render. The local round trip
        # cannot prove the half that matters — that the SERVER decodes the upload the same
        # way — and on this route the start frame is the entire image conditioning.
        "41": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": f"{experiment}/probe/startprobe",
                          "images": ["40", 0]}},
        "50": {"class_type": "WanImageToVideo", "inputs": {
            "width": WIDTH, "height": HEIGHT, "length": length, "batch_size": 1,
            "positive": ["30", 0], "negative": ["31", 0], "vae": ["21", 0],
            "start_image": ["40", 0],
            # clip_vision_output is deliberately absent — unconnected in the documented
            # reference workflow too, and wiring it would add a second image-conditioning
            # channel to an experiment whose subject is having only one.
        }},
        # The high-noise expert carries the run's registered seed and adds the noise.
        "60": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": seed_used, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": 0, "end_at_step": split,
            "return_with_leftover_noise": "enable",
            "model": ["12", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["50", 2]}},
        # The low-noise expert continues the same trajectory: it adds no noise, so its own
        # seed draws nothing and is inert — Gate S reports it and does not demand it.
        "61": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "disable", "noise_seed": 0, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": split, "end_at_step": 10000,
            "return_with_leftover_noise": "disable",
            "model": ["13", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["60", 0]}},
        "70": {"class_type": "VAEDecode",
               "inputs": {"samples": ["61", 0], "vae": ["21", 0]}},
        # THE LOSSLESS OUTPUT TAP — the frames CreateVideo is about to hand SaveVideo,
        # taken off VAEDecode before any codec touches them. Every measurement reads these.
        "71": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"{experiment}/probe/lossless", "images": ["70", 0]}},
        "80": {"class_type": "CreateVideo",
               "inputs": {"fps": fps, "bit_depth": 8, "images": ["70", 0]}},
        "81": {"class_type": "SaveVideo", "inputs": {
            "filename_prefix": f"video/{experiment}_probe", "format": "auto",
            "codec": "auto", "video": ["80", 0]}},
    }

    verify_topology(wf, start_name)

    gate_route = route_gates.verify(wf, frame=(WIDTH, HEIGHT, length))

    meta = {
        "experiment": experiment, "tool_version": TOOL_VERSION,
        "route": "no-control I2V — the GLB supplies the image, the model supplies the rest",
        "resolution": [WIDTH, HEIGHT], "length": length, "fps": fps,
        "seed": seed_used,
        "gate_S": gate_s,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "gate_ROUTE_built": gate_route,
        "models": {"unet_high_noise": UNET_HIGH, "unet_low_noise": UNET_LOW,
                   "clip": CLIP_NAME, "vae": VAE_NAME, "loras": []},
        "trajectory": TRAJECTORY,
        "two_expert_split": {
            "steps": steps, "split_step": split,
            "high_noise_steps": f"0..{split}", "low_noise_steps": f"{split}..{steps}",
            "origin": "READ OFF the documented reference workflow, not solved"},
        "positive": positive,
        "negative": negative,
        "start_image": {"server_name": start_name, "fit": "native — authored at 832x480",
                        "why": ("no letterbox and no centre-crop: the frame is rendered at "
                                "the generation's own size, so nothing resamples it. E08 "
                                "measured what a mismatched aspect costs on the other "
                                "route — WanAnimateToVideo kept 204 of its reference's "
                                "1024 rows")},
        "unconnected_inputs": {
            "clip_vision_output": ("unconnected in the documented reference workflow and "
                                   "unconnected here; a second image-conditioning channel "
                                   "would change what this experiment is measuring")},
        "no_driving_signal": (
            "checked in code by verify_topology: the graph contains no control-capable "
            "conditioning class, no second uploaded image outside the Gate B probe, and "
            "no clip-vision path. This is E11's defining property"),
        "delta_from_E08": DELTA_FROM_E08,
        "payload_sha256": hashlib.sha256(
            json.dumps(wf, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    return wf, meta


#: Conditioning classes that can carry a driving signal. Presence of any of them is the
#: end of E11 as an experiment, so the check is on the class list rather than on whether a
#: particular socket happens to be wired: a control node present but unfed is one edit
#: from being fed, and the map's own ruling on the licence tier is that presence is
#: presence.
CONTROL_CLASSES = ("WanVaceToVideo", "WanAnimateToVideo", "Wan22FunControlToVideo",
                   "WanFunControlToVideo", "WanCameraImageToVideo",
                   "WanFirstLastFrameToVideo", "WanPhantomSubjectToVideo",
                   "ControlNetApply", "ControlNetApplyAdvanced",
                   "ControlNetApplySD3", "ACN_AdvancedControlNetApply")


def verify_topology(wf, start_name):
    """Link topology, checked in code. A `dry_run` PASS does not prove link sanity."""
    problems = []

    node = wf.get("50")
    if not node or node["class_type"] != "WanImageToVideo":
        problems.append("node 50 is not the WanImageToVideo conditioning node")
    else:
        inp = node["inputs"]
        if inp.get("start_image") != ["40", 0]:
            problems.append("start_image is not fed by the start-frame LoadImage")
        if "clip_vision_output" in inp:
            problems.append(
                "clip_vision_output is connected; this wave's record says it is not, and "
                "a second image-conditioning channel would make the identity clause "
                "unattributable between the start frame and the embedding")

    # ---- the defining property, checked rather than trusted.
    for nid, n in wf.items():
        if n["class_type"] in CONTROL_CLASSES:
            problems.append(
                f"node {nid} is {n['class_type']}, a conditioning class that can carry a "
                f"driving signal. E11 is the no-control route; a graph with one answers a "
                f"different question and every other gate passes on it")
    loaders = [nid for nid, n in wf.items() if n["class_type"] == "LoadImage"]
    if loaders != ["40"]:
        problems.append(
            f"expected exactly one LoadImage (the start frame), found {loaders}. A second "
            f"uploaded image is a second conditioning channel however it is labelled")

    hi = wf.get("60", {}).get("inputs", {})
    lo = wf.get("61", {}).get("inputs", {})
    if hi.get("latent_image") != ["50", 2]:
        problems.append("the high-noise sampler does not take the conditioning node's latent")
    if lo.get("latent_image") != ["60", 0]:
        problems.append("the low-noise sampler does not continue the high-noise latent")
    for tag, ks, model in (("high", hi, ["12", 0]), ("low", lo, ["13", 0])):
        if ks.get("model") != model:
            problems.append(f"the {tag}-noise sampler does not take its own shifted expert")
        if ks.get("positive") != ["50", 0] or ks.get("negative") != ["50", 1]:
            problems.append(
                f"the {tag}-noise sampler does not take the conditioning node's "
                f"conditioning; text encodes wired straight to a sampler would drop the "
                f"start image's latent conditioning entirely and still generate a video")
    if hi.get("add_noise") != "enable" or lo.get("add_noise") != "disable":
        problems.append("the two-expert split's add_noise pair is not enable then disable")
    if hi.get("end_at_step") != lo.get("start_at_step"):
        problems.append(
            f"the experts do not hand over at the same step: high ends at "
            f"{hi.get('end_at_step')} and low starts at {lo.get('start_at_step')}, which "
            f"would silently skip or repeat part of the trajectory")

    if wf.get("41", {}).get("inputs", {}).get("images") != ["40", 0]:
        problems.append("the Gate B probe does not read the start-frame LoadImage directly")
    if wf.get("71", {}).get("inputs", {}).get("images") != ["70", 0]:
        problems.append("the lossless tap does not read VAEDecode directly")
    if wf.get("40", {}).get("inputs", {}).get("image") != start_name:
        problems.append("the LoadImage does not name the uploaded start frame")

    for nid, n in wf.items():
        for key, v in n["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in wf:
                problems.append(f"node {nid}.{key} links to missing node {v[0]}")

    for dead in ("DWPreprocessor", "OpenposePreprocessor", "SAM2", "LoadVideo",
                 "GetVideoComponents", "LoraLoaderModelOnly", "LoraLoader"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} is present; the licence map bans or excludes this tier")

    if problems:
        raise PayloadError("the built graph is not the graph the spec describes: "
                           + "; ".join(problems))
    return True


def main(argv=None):
    a = parse_args(argv)
    out = os.path.abspath(a.out)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    if "start_frame" not in uploads:
        raise PayloadError(f"{a.uploads} carries no `start_frame` upload name")

    registry = None
    if a.seeds_registry:
        with open(a.seeds_registry, encoding="utf-8") as fh:
            registry = json.load(fh)["seeds"]

    if not a.negative_source:
        raise PayloadError(
            "--negative-source is required: Wan's sample_neg_prompt is READ from the "
            "banked config, never retyped. E09's citation check fired on this string")
    negative = E08.read_negative(a.negative_source)
    ident, ident_original, drops = E08.identity_clause()
    positive = ident + ". " + E08.SCENE_CLAUSE
    gate_write(a.subject, a.canon_prompt or positive, no_canon=a.no_canon, out_dir=out)

    gate_pin = pin_against_e08(positive, negative, a.e08_record)

    wf, meta = build(uploads, a.seed, negative, positive, registry,
                     experiment=a.experiment, length=a.length, fps=a.fps)
    meta["gate_PIN"] = gate_pin
    meta["prompt_record"] = {
        "identity_clause_source": E08.TWIN_PROMPT_JSON,
        "identity_clause_original": ident_original,
        "identity_clause_used": ident,
        "identity_drops": drops,
        "scene_clause": E08.SCENE_CLAUSE,
        "rebuilt_through": ("build_animate_payload.identity_clause / read_negative — E08's "
                            "own code, not a copy of its output"),
        "negative_source": os.path.abspath(a.negative_source),
        "negative_source_sha256": hashlib.sha256(
            open(a.negative_source, "rb").read()).hexdigest(),
    }

    os.makedirs(out, exist_ok=True)
    gpath = os.path.join(out, f"{a.experiment}-probe-i2v.api.json")
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    mpath = os.path.join(out, f"{a.experiment}-probe-payload-record.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print("BUILD_I2V_OK " + json.dumps({
        "graph": gpath, "record": mpath, "nodes": len(wf), "seed": meta["seed"],
        "length": meta["length"], "fps": meta["fps"],
        "split_step": meta["two_expert_split"]["split_step"],
        "payload_sha256": meta["payload_sha256"][:32],
        "gate_PIN": gate_pin["verdict"],
        "gate_L": meta["gate_L"]["verdict"], "gate_S": meta["gate_S"].get("verdict"),
        "gate_ROUTE_built": meta["gate_ROUTE_built"]["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_I2V_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
