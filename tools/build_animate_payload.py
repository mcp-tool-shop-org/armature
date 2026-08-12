#!/usr/bin/env python
"""build_animate_payload — E08's `WanAnimateToVideo` graph, built in this repo.

    python tools\\build_animate_payload.py --uploads=<uploads.json> --out=<dir>
           [--seed=2026081201]

**Built here, never served.** `docs/license-map.md` trap #3 and CLAUDE.md both record the
same measurement, taken twice on 2026-08-11: the served `video_wan2_2_14B_animate` template
wires two `DWPreprocessor` nodes — the DWPose weights tier, UNVERIFIED and therefore NO — and
a SAM2 mask path, at its top level. A served template is a reference, never a route. Every
graph this pipeline submits is built in-repo and passes Gate ROUTE before Gates S and L arm.

--------------------------------------------------------------------------------
The input table, and why three sockets are deliberately empty

`pose_video`      the 65 AAPose-20 stick frames as ONE lossless APNG through a single
                  `LoadImage`, which concatenates every frame of a multi-frame image into
                  one IMAGE batch (`ComfyUI/nodes.py`, the PIL fallback; read 2026-08-12).
                  `pack_pose_pack` gates the pack's losslessness locally with Gate R before
                  upload, and a model-free run measured the server side: 65 frames, in
                  order, pixel-identical at 0/16/32/48/64. The
                  conditioning node then VAE-encodes the batch and sets `pose_video_latent`
                  on BOTH positive and negative conditioning (source read 2026-08-12).
`reference_image` the Director-approved twin. **The node center-crops it to width x height**
                  via `common_upscale(..., "area", "center")` — see `--reference-fit`.
`background_video` UNCONNECTED. With it absent the node builds the background plane as
                  `torch.ones(...) * 0.5`, a uniform mid-grey, and the concat mask stays all
                  ones — "generate everything". That is precisely clause 3: how much bar
                  arrives from text alone.
`face_video`      UNCONNECTED in wave 1. One-variable discipline; the expression lever is
                  named for later (G7).
`character_mask`  UNCONNECTED, and now for a measured reason rather than a missing tooltip.
                  The schema carries no description, so the spec's condition was "wire it
                  only if its animation-mode semantics verify". They verify from the core
                  node source, and they say do not wire it here: `character_mask` is written
                  into `mask_refmotion`, which becomes the conditioning's `concat_mask`
                  over the background plane. Mask 1 means generate, 0 means keep the plane.
                  With `background_video` unconnected that plane is flat mid-grey, so a
                  character mask would instruct the model to PRESERVE flat grey everywhere
                  outside the figure — a grey void where clause 3 is asking for a bar. It
                  becomes a live lever the moment `background_video` is used, and not before.
`clip_vision_output` / `continue_motion` UNCONNECTED — neither is in wave 1's scope.

--------------------------------------------------------------------------------
The gates

* **Gate L** — `gates.g1_generator_legality`, raised in-tool before a single node is
  emitted. The `wan-animate` profile's constraints come from the node's own schema.
* **Gate S** — `gates.gate_s_seed_registration` against `specs/E08-seeds.json`, committed
  before the first submission.
* **topology** — checked in code, because a `dry_run` PASS does not prove link sanity. E02
  measured that three times over.
* **Gate ROUTE** runs separately on the built graph AND on the saved file.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory. It submits nothing and spends nothing.
"""

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E10.1"
EXPERIMENT = "E08"

#: E08's shot, and the defaults. `--length` and `--fps` are E10's variables and nothing
#: else moves: E10 drives the SAME dance resampled to 81 samples over the identical
#: duration, so the frame count rises and the playback rate rises with it.
#:
#: **`fps` reaches `CreateVideo` and nothing upstream of it** — measured from the node
#: schema 2026-08-12: `CreateVideo` takes `fps` as a FLOAT (min 1, max 120), and it sits
#: downstream of `VAEDecode`, after every sampling step. `WanAnimateToVideo` and `KSampler`
#: carry no fps input at all. So the rate is a presentation parameter here: it decides how
#: fast the convenience video plays and cannot change a generated pixel. The lossless
#: `SaveImage` tap that every measurement reads bypasses it entirely.
WIDTH, HEIGHT, LENGTH, FPS = 832, 480, 65, 16

#: Weights. Every one is ruled in `docs/license-map.md`:
#: Wan2.2-Animate-14B Apache-2.0; the Comfy-Org repack tier is covered by the 2026-08-11
#: ruling (the upstream grant governs, the repack asserts nothing itself); umt5-xxl
#: Apache-2.0; wan_2.1_vae is the Wan 2.1 tier, Apache-2.0.
#: The Kijai fp8 variants of this model are NOT used: they are a third-party repack the map
#: has no row for, and "check the exact variant you are about to run" is the standing law.
UNET_NAME = "wan2.2_animate_14B_bf16.safetensors"
CLIP_NAME = "umt5_xxl_fp16.safetensors"
VAE_NAME = "wan_2.1_vae.safetensors"

#: Sampler settings. `steps`, `cfg`, `sampler_name`, `scheduler` are the catalog's own
#: documented recommendation for this model, retrieved 2026-08-12 via
#: `get_prompting_guide(model="wan2.2_animate_14B_bf16.safetensors")`: 20 / 6 / uni_pc /
#: simple at 832x480. `shift` has no Animate-specific document; 8.0 is carried from the
#: Wan 2.2 reference workflow E09 A3 ran on, and that inheritance is recorded rather than
#: dressed up as a retrieval.
STEPS, CFG, SAMPLER, SCHEDULER, SHIFT = 20, 6.0, "uni_pc", "simple", 8.0
SETTINGS_SOURCE = {
    "steps_cfg_sampler_scheduler": ("get_prompting_guide(model=wan2.2_animate_14B_bf16"
                                    ".safetensors), retrieved 2026-08-12"),
    "shift": ("INHERITED from the Wan 2.2 reference workflow used by E09 A3 "
              "(two_expert_split.shift = 8.0); no Animate-specific document was retrieved"),
}

#: The identity clause, from facet E33's Director-approved twin entry.
TWIN_PROMPT_JSON = r"E:\AI\facet\docs\experiments\E33-twin-prompts-r3.json"

#: Phrases removed from the identity clause for THIS shot, each with its reason. The clause
#: was written for a studio plate and carries its backdrop and lighting inside it; carried
#: verbatim into a bar it would instruct the model to paint a plain pale grey background in
#: the same breath as a crowded bar, and clause 3 — how much scene arrives from text — would
#: be measuring a contradiction rather than the prompt's strength. Recorded as a change log
#: rather than a silent edit, the same way E09 A3 recorded its two deleted clauses.
IDENTITY_DROPS = [
    ("plain pale grey background",
     "names a backdrop; directly contradicts the scene clause this shot is measuring"),
    ("soft studio light",
     "names a lighting setup; contradicts 'warmly lit' and would confound clause 3"),
]

SCENE_CLAUSE = ("He is dancing in a crowded, warmly lit bar, other people around him, "
                "a long bar counter behind him with bottles and glasses catching the light. "
                "The camera is static.")


class PayloadError(ArmatureError):
    """The payload could not be built as specified."""


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True,
                    help="JSON: {reference, pose_pack, pose_frames}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--negative-source", default=None,
                    help="path to Wan's shared_config.py; the negative is read from it "
                         "rather than retyped")
    ap.add_argument("--reference-fit", default="as-is", choices=("as-is", "letterbox"),
                    help="'as-is' hands the reference to the node unchanged and lets it "
                         "center-crop; 'letterbox' names a pre-fitted reference. The choice "
                         "and its measured consequence are recorded either way")
    ap.add_argument("--seeds-registry", default=None)
    ap.add_argument("--experiment", default=EXPERIMENT,
                    help="names the output files and the server-side filename prefixes")
    ap.add_argument("--length", type=int, default=LENGTH,
                    help="frame count; Gate L and Gate ROUTE both check it (argparse eats "
                         "leading minus signs, so pass flags as --flag=value)")
    ap.add_argument("--fps", type=float, default=FPS,
                    help="the CreateVideo rate. Presentation only — it is downstream of "
                         "VAEDecode and cannot change a generated pixel")
    return ap.parse_args(argv)


def read_negative(path):
    """Wan's own `sample_neg_prompt`, read from the banked source. Never retyped.

    E09's citation check fired on this very string when a seat described it from memory, so
    it is parsed out of the file and the file's hash rides the record.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"sample_neg_prompt\s*=\s*(['\"])(.*?)\1", text, re.S)
    if not m:
        raise PayloadError(
            f"{path} carries no `sample_neg_prompt` assignment to read; the negative is not "
            f"retyped from memory, so the build halts rather than inventing one")
    return m.group(2)


def identity_clause(path=TWIN_PROMPT_JSON):
    """The twin's verbatim entry with this shot's drops applied, plus the change log."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    text = doc.get("_entry_verbatim")
    if not isinstance(text, str) or not text.strip():
        raise PayloadError(f"{path} carries no `_entry_verbatim` identity clause")
    original = text
    log = []
    for phrase, reason in IDENTITY_DROPS:
        if phrase not in text:
            raise PayloadError(
                f"the identity clause no longer contains {phrase!r}, so this shot's "
                f"recorded drop cannot be applied. The clause has changed under the "
                f"experiment and the change log would be describing a different string")
        text = text.replace(", " + phrase, "").replace(phrase + ", ", "")
        log.append({"dropped": phrase, "reason": reason})
    return text.strip().strip(","), original, log


def build(uploads, seed, negative, positive, registry, reference_fit,
          experiment=EXPERIMENT, length=LENGTH, fps=FPS):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists."""
    gate_s = gates.gate_s_seed_registration(seed, registry, experiment,
                                            seed_was_explicit=seed is not None)
    seed_used = seed if seed is not None else (sorted(registry)[0] if registry else 0)
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-animate")

    pose_name = uploads["pose_pack"]
    packed = uploads.get("pose_frames")
    if packed != length:
        raise PayloadError(
            f"the pose pack declares {packed} frames and the shot is {length}. The "
            f"conditioning node pads a short pose video by REPEATING its last frame and "
            f"truncates a long one, both silently — so a miscount arrives as a performance "
            f"that freezes or ends early, with every gate green")

    wf = {
        "106": {"class_type": "UNETLoader",
                "inputs": {"unet_name": UNET_NAME, "weight_dtype": "default"}},
        "105": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "110": {"class_type": "CLIPLoader",
                "inputs": {"clip_name": CLIP_NAME, "type": "wan", "device": "default"}},
        "48": {"class_type": "ModelSamplingSD3",
               "inputs": {"shift": SHIFT, "model": ["106", 0]}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": positive, "clip": ["110", 0]}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": ["110", 0]}},
        "134": {"class_type": "LoadImage", "inputs": {"image": uploads["reference"]}},
    }

    # ONE `LoadImage` on a lossless animated WebP, not N of them into a `BatchImagesNode`.
    # `ComfyUI/nodes.py::LoadImage` concatenates every frame of a multi-frame image into a
    # single IMAGE batch — its PIL fallback exists for exactly this, under a comment naming
    # animated WebP outright. Read from the source 2026-08-12; the pack's own losslessness
    # is gated locally by `pack_pose_webp` (Gate R, verdict recorded in its manifest).
    wf["200"] = {"class_type": "LoadImage", "inputs": {"image": pose_name}}
    # Gate B probe: the batch as the conditioning node receives it, saved so it can be
    # counted and compared pixel-for-pixel against the local stick frames. This is the half
    # the local round trip cannot prove — that the SERVER decodes the pack the same way.
    wf["301"] = {"class_type": "SaveImage",
                 "inputs": {"filename_prefix": f"{experiment}/probe/batchprobe",
                            "images": ["200", 0]}}

    wf["49"] = {"class_type": "WanAnimateToVideo", "inputs": {
        "width": WIDTH, "height": HEIGHT, "length": length, "batch_size": 1,
        "continue_motion_max_frames": 5, "video_frame_offset": 0,
        "positive": ["6", 0], "negative": ["7", 0], "vae": ["105", 0],
        "reference_image": ["134", 0], "pose_video": ["200", 0],
        # background_video / face_video / character_mask / clip_vision_output /
        # continue_motion are deliberately absent — see the module docstring.
    }}
    wf["3"] = {"class_type": "KSampler", "inputs": {
        "seed": seed_used, "steps": STEPS, "cfg": CFG, "sampler_name": SAMPLER,
        "scheduler": SCHEDULER, "denoise": 1.0, "model": ["48", 0],
        "positive": ["49", 0], "negative": ["49", 1], "latent_image": ["49", 2]}}
    wf["58"] = {"class_type": "TrimVideoLatent",
                "inputs": {"samples": ["3", 0], "trim_amount": ["49", 3]}}
    wf["8"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["58", 0], "vae": ["105", 0]}}
    wf["68"] = {"class_type": "CreateVideo",
                "inputs": {"fps": fps, "bit_depth": 8, "images": ["8", 0]}}
    wf["114"] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": f"video/{experiment}_probe", "format": "auto", "codec": "auto",
        "video": ["68", 0]}}
    # THE LOSSLESS OUTPUT TAP — the same frames CreateVideo is about to hand SaveVideo,
    # taken off VAEDecode before any codec touches them. Everything downstream reads these.
    wf["302"] = {"class_type": "SaveImage", "inputs": {
        "filename_prefix": f"{experiment}/probe/lossless", "images": ["8", 0]}}

    verify_topology(wf)

    # Gate ROUTE on the graph THIS tool just built, in-tool, with the frame values stated.
    # Supplying them is not a convenience: `WanAnimateToVideo` sizes its own latent, and
    # E08 measured what happens when the gate cannot find one — it reported the graph legal
    # having examined zero frames. The route gate now refuses to call an empty examination
    # a pass, and a caller that knows its own shape says so.
    gate_route = route_gates.verify(wf, frame=(WIDTH, HEIGHT, length))

    meta = {
        "experiment": experiment, "tool_version": TOOL_VERSION,
        "resolution": [WIDTH, HEIGHT], "length": length, "fps": fps,
        "seed": seed_used,
        "gate_S": gate_s,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "gate_ROUTE_built": gate_route,
        "models": {"unet": UNET_NAME, "clip": CLIP_NAME, "vae": VAE_NAME},
        "sampler": {"steps": STEPS, "cfg": CFG, "sampler_name": SAMPLER,
                    "scheduler": SCHEDULER, "shift": SHIFT, "denoise": 1.0,
                    "source": SETTINGS_SOURCE},
        "positive": positive,
        "negative": negative,
        "reference_image": {"server_name": uploads["reference"], "fit": reference_fit},
        "pose_video": {"bridge": ("1 x LoadImage on a lossless animated WebP; "
                                  "LoadImage concatenates every frame into one IMAGE "
                                  "batch (ComfyUI/nodes.py, PIL fallback)"),
                       "server_name": pose_name, "declared_frames": packed},
        "unconnected_inputs": {
            "background_video": ("the background plane stays torch.ones*0.5 mid-grey and "
                                 "the concat mask stays all ones; clause 3 measures how "
                                 "much bar arrives from text alone"),
            "face_video": "one-variable discipline; the expression lever is named for later",
            "character_mask": ("its semantics verify from the core node source and say do "
                               "not wire it here: it writes the concat mask over the "
                               "background plane, so with that plane flat grey it would "
                               "instruct the model to preserve a grey void outside the "
                               "figure"),
            "clip_vision_output": "not in wave 1's scope",
            "continue_motion": "single-chunk shot; no previous chunk to continue",
        },
        "payload_sha256": hashlib.sha256(
            json.dumps(wf, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    return wf, meta


def verify_topology(wf):
    """Link topology, checked in code. A `dry_run` PASS does not prove link sanity."""
    problems = []
    node = wf.get("49")
    if not node or node["class_type"] != "WanAnimateToVideo":
        problems.append("node 49 is not the WanAnimateToVideo conditioning node")
    else:
        inp = node["inputs"]
        if inp.get("pose_video") != ["200", 0]:
            problems.append("pose_video is not fed by the pose-pack LoadImage")
        if inp.get("reference_image") != ["134", 0]:
            problems.append("reference_image is not fed by the reference LoadImage")
        for absent in ("background_video", "face_video", "character_mask",
                       "clip_vision_output", "continue_motion"):
            if absent in inp:
                problems.append(
                    f"{absent} is connected; this wave's record says it is not, and a "
                    f"connected background_video would make clause 3 unmeasurable")

    if wf.get("301", {}).get("inputs", {}).get("images") != ["200", 0]:
        problems.append("the Gate B probe does not read the pose LoadImage directly")
    if wf.get("200", {}).get("inputs", {}).get("image") ==             wf.get("134", {}).get("inputs", {}).get("image"):
        problems.append("the pose pack and the reference name the same uploaded file")

    ks = wf.get("3", {}).get("inputs", {})
    if ks.get("latent_image") != ["49", 2]:
        problems.append("the sampler does not take the conditioning node's latent")
    if ks.get("model") != ["48", 0]:
        problems.append("the sampler does not take the shifted model")
    if wf.get("58", {}).get("inputs", {}).get("trim_amount") != ["49", 3]:
        problems.append("TrimVideoLatent does not take the node's own trim_latent output")
    if wf.get("302", {}).get("inputs", {}).get("images") != ["8", 0]:
        problems.append("the lossless tap does not read VAEDecode directly")

    # Every link must name a node that exists.
    for nid, n in wf.items():
        for key, v in n["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in wf:
                problems.append(f"node {nid}.{key} links to missing node {v[0]}")

    for dead in ("DWPreprocessor", "OpenposePreprocessor", "SAM2", "LoadVideo",
                 "GetVideoComponents"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} is present; the licence map bans or excludes this tier")

    if problems:
        raise PayloadError("the built graph is not the graph the spec describes: "
                           + "; ".join(problems))
    return True


def main(argv=None):
    a = parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)

    registry = None
    if a.seeds_registry:
        with open(a.seeds_registry, encoding="utf-8") as fh:
            registry = json.load(fh)["seeds"]

    neg_path = a.negative_source
    if not neg_path:
        raise PayloadError(
            "--negative-source is required: Wan's sample_neg_prompt is READ from the banked "
            "config, never retyped. E09's citation check fired on exactly this string")
    negative = read_negative(neg_path)
    ident, ident_original, drops = identity_clause()
    positive = ident + ". " + SCENE_CLAUSE

    wf, meta = build(uploads, a.seed, negative, positive, registry, a.reference_fit,
                     experiment=a.experiment, length=a.length, fps=a.fps)
    meta["prompt_record"] = {
        "identity_clause_source": TWIN_PROMPT_JSON,
        "identity_clause_original": ident_original,
        "identity_clause_used": ident,
        "identity_drops": drops,
        "scene_clause": SCENE_CLAUSE,
        "negative_source": os.path.abspath(neg_path),
        "negative_source_sha256": hashlib.sha256(
            open(neg_path, "rb").read()).hexdigest(),
    }

    gpath = os.path.join(out, f"{a.experiment}-probe-animate.api.json")
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    mpath = os.path.join(out, f"{a.experiment}-probe-payload-record.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print("BUILD_ANIMATE_OK " + json.dumps({
        "graph": gpath, "record": mpath, "nodes": len(wf), "seed": meta["seed"],
        "length": meta["length"], "fps": meta["fps"],
        "payload_sha256": meta["payload_sha256"][:32],
        "gate_L": meta["gate_L"]["verdict"], "gate_S": meta["gate_S"].get("verdict"),
        "gate_ROUTE_built": meta["gate_ROUTE_built"]["verdict"]},
        ensure_ascii=False))
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
        print("BUILD_ANIMATE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
