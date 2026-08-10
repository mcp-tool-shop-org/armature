#!/usr/bin/env python
"""build_payload — assemble an E02 submission, with the gates that must fire first.

    python tools/build_payload.py --arm=A1a --out=<payload.json>

Emits ComfyUI **API format**. The bridge is the one ruled in `E02-halt-ruling.md`:
33 x `LoadImage` -> `BatchImagesNode` -> `control_video`. There is no encoder anywhere in
it, which is the whole point — losslessness is structural rather than measured, and Gate R
is **N/A for this route, not deleted** (it and its 18 tests stay in the tree for the day a
video bridge opens).

Two things this refuses to emit a payload without:

* **Gate L** (`g1_generator_legality`) is called here, in the function that builds the
  thing that gets submitted — not chained behind a shell `&&`, which can walk past a
  failing exit code. Illegal frames never reach the wire.
* **Link topology is verified in code.** CLAUDE.md is explicit that a `dry_run` PASS does
  not prove link sanity, and E02 measured why: `dry_run` accepted a `LoadImage` naming a
  file that does not exist, without a warning.

**The Gate B probe.** A `SaveImage` hangs off `BatchImagesNode`'s output. It is not
decoration — it is the only way to observe the batch the sampler actually received.
Counting *output video* frames cannot work: `WanVaceToVideo` pads a short `control_video`
up to `length`, so a 1-image batch and a 33-image batch both yield 33 frames. See
`GateBBatching`.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

WIDTH, HEIGHT, LENGTH, FPS = 480, 832, 33, 16
SEED = 654654950714624  # pinned from the saved graph, so A0's three repeats are identical

POSITIVE = (
    "A lone armored warrior stands in place and turns slowly on the spot. Dark plate "
    "armor, horned helm, heavy cloak. Neutral studio background, even lighting."
)
NEGATIVE = (
    "blurry, low quality, jpeg artifacts, extra limbs, deformed hands, deformed face, "
    "text, watermark, still image, static"
)


class PayloadError(ArmatureError):
    """The payload could not be built as specified."""


def _load_uploads():
    with open("outputs/E02/uploads_depth_pershot.json", encoding="utf-8") as fh:
        control = json.load(fh)
    with open("outputs/E02/uploads_reference.json", encoding="utf-8") as fh:
        ref = json.load(fh)["reference_apose_0"]
    keys = sorted(control)
    if len(keys) != LENGTH:
        raise PayloadError(f"expected {LENGTH} uploaded control frames, have {len(keys)}")
    names = [control[k] for k in keys]
    if len(set(names)) != LENGTH:
        # Server names are content-addressed (measured: re-uploading a frame returns the
        # same name), so two identical frames would collapse to one entry and the batch
        # would silently be short. Caught here rather than by Gate B after a spend.
        raise PayloadError(
            f"{LENGTH} frames map to only {len(set(names))} distinct server names; "
            f"duplicate content would shrink the batch"
        )
    return keys, names, ref


def build(arm):
    keys, control_names, ref_name = _load_uploads()
    use_control = arm != "A2"

    # ---- Gate L · ANDON. First statement that matters; nothing is emitted if it raises.
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, LENGTH, "wan-vace")

    wf = {
        "106": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "wan2.1_vace_14B_fp16.safetensors", "weight_dtype": "default"}},
        "105": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "110": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "umt5_xxl_fp16.safetensors", "type": "wan", "device": "default"}},
        "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8.0, "model": ["106", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POSITIVE, "clip": ["110", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["110", 0]}},
        "134": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
    }

    vace_inputs = {
        "width": WIDTH, "height": HEIGHT, "length": LENGTH, "batch_size": 1, "strength": 1.0,
        "positive": ["6", 0], "negative": ["7", 0], "vae": ["105", 0],
        "reference_image": ["134", 0],
    }

    if use_control:
        # COMFY_AUTOGROW_V3 slots are DOTTED keys — `images.image0`, `images.image1`, ...
        # A list of links under a bare `images` key is rejected by the server with
        # `required_input_missing: images.image0`. That form was tried first and
        # `dry_run` VALIDATED it with zero warnings; only a real submission refused it.
        # Third measured instance in E02 of dry_run passing something broken.
        batch_inputs = {}
        for i, name in enumerate(control_names):
            nid = str(200 + i)
            wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
            batch_inputs[f"images.image{i}"] = [nid, 0]
        wf["300"] = {"class_type": "BatchImagesNode", "inputs": batch_inputs}
        # Gate B probe: the batch as the sampler receives it, saved so it can be counted
        # and compared pixel-for-pixel against the local source frames.
        wf["301"] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"E02/{arm}/batchprobe", "images": ["300", 0]}}
        vace_inputs["control_video"] = ["300", 0]

    wf["49"] = {"class_type": "WanVaceToVideo", "inputs": vace_inputs}
    wf["3"] = {"class_type": "KSampler", "inputs": {
        "seed": SEED, "steps": 30, "cfg": 6, "sampler_name": "uni_pc", "scheduler": "simple",
        "denoise": 1, "model": ["48", 0], "positive": ["49", 0], "negative": ["49", 1],
        "latent_image": ["49", 2]}}
    wf["58"] = {"class_type": "TrimVideoLatent", "inputs": {
        "samples": ["3", 0], "trim_amount": ["49", 3]}}
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["58", 0], "vae": ["105", 0]}}
    wf["68"] = {"class_type": "CreateVideo", "inputs": {
        "fps": FPS, "bit_depth": 8, "images": ["8", 0]}}
    wf["114"] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": f"video/E02_{arm}", "format": "auto", "codec": "auto",
        "video": ["68", 0]}}

    verify_topology(wf, arm, use_control)
    meta = {
        "arm": arm,
        "resolution": [WIDTH, HEIGHT],
        "length": LENGTH,
        "fps": FPS,
        "seed": SEED,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "control": "none (A2 — the thesis test)" if not use_control else {
            "bridge": "33 x LoadImage -> BatchImagesNode",
            "source_dir": "outputs/E02/control_480x832/depth_pershot",
            "normalization": "per-shot",
            "polarity": "near-bright (as rendered, F19)",
            "frame_keys": keys,
            "server_names": control_names,
        },
        "reference_image": ref_name,
        "positive": POSITIVE,
        "negative": NEGATIVE,
        "models": {
            "unet": "wan2.1_vace_14B_fp16.safetensors",
            "clip": "umt5_xxl_fp16.safetensors",
            "vae": "wan_2.1_vae.safetensors",
        },
        "payload_sha256": hashlib.sha256(
            json.dumps(wf, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    return wf, meta


def verify_topology(wf, arm, use_control):
    """Check every link resolves, and that the arm is actually the arm it claims to be."""
    problems = []
    for nid, node in wf.items():
        for k, v in node["inputs"].items():
            cands = v if (isinstance(v, list) and v and isinstance(v[0], list)) else [v]
            for c in cands:
                if isinstance(c, list) and len(c) == 2 and isinstance(c[0], str):
                    if c[0] not in wf:
                        problems.append(f"{nid}.{k} -> missing node {c[0]}")

    if use_control:
        bi = wf["300"]["inputs"]
        if "images" in bi:
            problems.append(
                "batch uses a bare `images` list; COMFY_AUTOGROW_V3 needs dotted "
                "`images.image<N>` keys (dry_run does NOT catch this)"
            )
        expected_keys = [f"images.image{i}" for i in range(LENGTH)]
        if sorted(bi) != sorted(expected_keys):
            problems.append(
                f"batch slot keys are wrong: {len(bi)} keys, expected {LENGTH} named "
                f"images.image0..images.image{LENGTH - 1}"
            )
        srcs = [v[0] for v in bi.values()]
        if len(set(srcs)) != LENGTH:
            problems.append("a batch link is bound twice")
        if wf["49"]["inputs"].get("control_video") != ["300", 0]:
            problems.append("control_video is not fed by the batch node")
        if wf["301"]["inputs"]["images"] != ["300", 0]:
            problems.append("the Gate B probe is not wired to the batch node")
    else:
        if "control_video" in wf["49"]["inputs"]:
            problems.append("A2 must have NO control_video; the arm would not be the arm")
        if any(n["class_type"] == "BatchImagesNode" for n in wf.values()):
            problems.append("A2 still carries a batch node")

    for dead in ("LoadVideo", "GetVideoComponents", "Canny"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} present; the video bridge was not removed")

    if problems:
        raise PayloadError(f"[{arm}] link topology is wrong: " + "; ".join(problems))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["A1a", "A1b", "A2"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    wf, meta = build(a.arm)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(a.out.replace(".json", ".meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print("BUILD_PAYLOAD " + json.dumps({
        "arm": a.arm, "nodes": len(wf), "gate_L": "PASS",
        "sha256": meta["payload_sha256"][:16], "out": a.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
