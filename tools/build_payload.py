#!/usr/bin/env python
"""build_payload — assemble a submission, with the gates that must fire first.

    python tools/build_payload.py --experiment=E02 --arm=A1a --out=<payload.json>
    python tools/build_payload.py --experiment=E03 --arm=B1  --out=<payload.json>

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

--------------------------------------------------------------------------------
Two experiments, one builder (E03, 2026-08-10)

E03 varies the *subject's* motion instead of the camera's, so it needs a different prompt,
a different control source and — measured, not assumed — **no `reference_image` at all**
(`get_node WanVaceToVideo`: `reference_image` is `required: false`). Rather than fork a
second 240-line builder, the parts that differ are data in `EXPERIMENTS` and the emitted
graph shape is shared. **The E02 rows are pinned by payload sha256 in
`tests/test_build_payload.py`**, so a refactor that moved E02's bytes fails a test rather
than quietly re-topologising an experiment that has already been run and reported.

**The distinct-name check binds in both directions now.** Server names are
content-addressed, so E02 could demand 33 distinct names from 33 frames and catch a
collapsed batch. E03's B3 arm is *defined* as one held pose repeated 33 times — 33 frames
with exactly ONE distinct name — so a hard "must be 33 distinct" check would refuse the
arm. The expectation is therefore computed from the local frames' own content hashes and
compared: a moving control that collapsed raises, and a static arm that did not collapse
raises too.
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


# A1b is the polarity arm. Its control is a full-image `255-x` of A1a's, which is ALSO the
# semantically correct near-dark map: E01's exporter writes BACKGROUND_DEPTH = 0.0 (black =
# far) and subject near = bright, so inverting sends the background to 255, which still
# reads "far" under the near-dark convention. One transform on identical geometry, so the
# two arms differ by exactly one thing.
UPLOAD_MAP = {
    "A1a": "outputs/E02/uploads_depth_pershot.json",
    "A1b": "outputs/E02/uploads_depth_pershot_inverted.json",
}

# E03's prompt pair. Two departures from E02's, both executor choices the spec did not arm
# and both flagged in the report:
#
#  1. **The positive names no motion.** E02's said "turns slowly on the spot", which is fine
#     when the control IS a turn. Here the whole question is whether authored motion
#     transfers, so a prompt asking for the motion would hand B2 and B3 a reason to produce
#     it and the discriminator would be measuring the prompt, not the control.
#  2. **The negative drops "still image, static".** Keeping it would pay the model to move
#     under B3 — the exact arm whose job is to show what happens when the control does NOT
#     move. Whatever motion appears is then not something we asked for.
#
# It names no material and no costume, so P3 ("does it keep the wire look") is not answered
# by the prompt — though it does say there is a figure, which bounds that read.
E03_POSITIVE = (
    "A single figure stands in the centre of an empty studio. Plain grey seamless "
    "background, even neutral lighting, full body in frame."
)
E03_NEGATIVE = (
    "blurry, low quality, jpeg artifacts, extra limbs, deformed hands, deformed face, "
    "text, watermark"
)

#: Per-experiment configuration. An arm whose `uploads` is None carries no control video.
#: `source_dir` is the LOCAL directory the uploads came from; it is what the distinct-name
#: check derives its expectation from, so it is not decoration.
EXPERIMENTS = {
    "E02": {
        "positive": POSITIVE,
        "negative": NEGATIVE,
        "reference": ("outputs/E02/uploads_reference.json", "reference_apose_0"),
        "arms": {
            "A1a": {"uploads": UPLOAD_MAP["A1a"],
                    "source_dir": "outputs/E02/control_480x832/depth_pershot",
                    "normalization": "per-shot",
                    "polarity": "near-bright (as rendered, F19)"},
            "A1b": {"uploads": UPLOAD_MAP["A1b"],
                    "source_dir": "outputs/E02/control_480x832_inverted/depth_pershot",
                    "normalization": "per-shot",
                    "polarity": "near-dark (full-image 255-x of A1a)"},
            "A2": {"uploads": None},
        },
    },
    "E03": {
        "positive": E03_POSITIVE,
        "negative": E03_NEGATIVE,
        # NO reference image, held constant (absent) across all three arms. Measured legal:
        # `get_node WanVaceToVideo` reports reference_image as `required: false`. The E03
        # subject carries no identity, so a reference plate would inject one the experiment
        # is not asking about.
        "reference": None,
        "arms": {
            "B1": {"uploads": "outputs/E03/uploads_posearc.json",
                   "source_dir": "outputs/E03/control_posearc/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)"},
            "B2": {"uploads": None},
            "B3": {"uploads": "outputs/E03/uploads_static.json",
                   "source_dir": "outputs/E03/control_static/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)"},
        },
    },
}


def _distinct_source_frames(source_dir):
    """How many distinct images the LOCAL control directory holds, or None if absent."""
    if not source_dir or not os.path.isdir(source_dir):
        return None
    digests = set()
    for n in sorted(os.listdir(source_dir)):
        if n.lower().endswith(".png"):
            with open(os.path.join(source_dir, n), "rb") as fh:
                digests.add(hashlib.sha256(fh.read()).hexdigest())
    return len(digests) or None


def _load_uploads(arm="A1a", experiment="E02"):
    cfg = EXPERIMENTS[experiment]
    arm_cfg = cfg["arms"][arm]
    with open(arm_cfg["uploads"], encoding="utf-8") as fh:
        control = json.load(fh)

    ref = None
    if cfg["reference"]:
        path, key = cfg["reference"]
        with open(path, encoding="utf-8") as fh:
            ref = json.load(fh)[key]

    keys = sorted(control)
    if len(keys) != LENGTH:
        raise PayloadError(f"expected {LENGTH} uploaded control frames, have {len(keys)}")
    names = [control[k] for k in keys]

    # Server names are content-addressed (measured: re-uploading a frame returns the same
    # name), so the number of DISTINCT names is the number of distinct images the batch will
    # carry. E02 could demand 33 from 33 and catch a collapsed batch. E03's B3 arm is
    # *defined* as one held pose repeated 33 times — 33 frames, exactly ONE distinct name —
    # so a hard "must be 33 distinct" check would refuse the arm it was written to protect.
    #
    # The expectation is therefore taken from the LOCAL frames' own content hashes and
    # compared. It binds in both directions: a moving control that collapsed on upload
    # raises, and a static arm that did NOT collapse raises too, because it would not be the
    # arm it claims to be. Caught here rather than by Gate B after a spend.
    expected = _distinct_source_frames(arm_cfg.get("source_dir"))
    got = len(set(names))
    if expected is None:
        if got < 1:
            raise PayloadError("no uploaded control frames at all")
    elif got != expected:
        raise PayloadError(
            f"{LENGTH} uploaded frames map to {got} distinct server name(s), but "
            f"{arm_cfg['source_dir']} holds {expected} distinct image(s); the batch the "
            f"sampler receives would not be the control that was rendered"
        )
    return keys, names, ref


def build(arm, experiment="E02"):
    if experiment not in EXPERIMENTS:
        raise PayloadError(f"unknown experiment {experiment!r}; known: {sorted(EXPERIMENTS)}")
    cfg = EXPERIMENTS[experiment]
    if arm not in cfg["arms"]:
        raise PayloadError(f"unknown arm {arm!r} for {experiment}; known: {sorted(cfg['arms'])}")

    POSITIVE_TEXT, NEGATIVE_TEXT = cfg["positive"], cfg["negative"]
    use_control = cfg["arms"][arm]["uploads"] is not None
    if use_control:
        keys, control_names, ref_name = _load_uploads(arm, experiment)
    else:
        keys, control_names, ref_name = [], [], None
        if cfg["reference"]:
            path, key = cfg["reference"]
            with open(path, encoding="utf-8") as fh:
                ref_name = json.load(fh)[key]

    # ---- Gate L · ANDON. First statement that matters; nothing is emitted if it raises.
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, LENGTH, "wan-vace")

    wf = {
        "106": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "wan2.1_vace_14B_fp16.safetensors", "weight_dtype": "default"}},
        "105": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "110": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "umt5_xxl_fp16.safetensors", "type": "wan", "device": "default"}},
        "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8.0, "model": ["106", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "text": POSITIVE_TEXT, "clip": ["110", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "text": NEGATIVE_TEXT, "clip": ["110", 0]}},
    }

    vace_inputs = {
        "width": WIDTH, "height": HEIGHT, "length": LENGTH, "batch_size": 1, "strength": 1.0,
        "positive": ["6", 0], "negative": ["7", 0], "vae": ["105", 0],
    }
    if ref_name is not None:
        wf["134"] = {"class_type": "LoadImage", "inputs": {"image": ref_name}}
        vace_inputs["reference_image"] = ["134", 0]

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
            "filename_prefix": f"{experiment}/{arm}/batchprobe", "images": ["300", 0]}}
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
        "filename_prefix": f"video/{experiment}_{arm}", "format": "auto", "codec": "auto",
        "video": ["68", 0]}}
    # ---- THE LOSSLESS OUTPUT TAP. Costs no extra generation: these are the same frames
    # `CreateVideo` is about to hand to `SaveVideo`, taken off `VAEDecode` before any
    # codec touches them. The first noise floor was measured through H.264 on BOTH sides,
    # so its deltas carried codec noise of unknown size on top of model variance. A floor
    # measured through an uncharacterised codec is a moving denominator, which is the
    # thing this repo keeps paying for. Everything downstream reads these, not the video.
    wf["302"] = {"class_type": "SaveImage", "inputs": {
        "filename_prefix": f"{experiment}/{arm}/lossless", "images": ["8", 0]}}

    verify_topology(wf, arm, use_control, expects_reference=cfg["reference"] is not None)
    arm_cfg = cfg["arms"][arm]
    meta = {
        "experiment": experiment,
        "arm": arm,
        "resolution": [WIDTH, HEIGHT],
        "length": LENGTH,
        "fps": FPS,
        "seed": SEED,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "control": "none (the null — no control_video)" if not use_control else {
            "bridge": "33 x LoadImage -> BatchImagesNode",
            "source_dir": arm_cfg["source_dir"],
            "normalization": arm_cfg["normalization"],
            "polarity": arm_cfg["polarity"],
            "distinct_images": len(set(control_names)),
            "frame_keys": keys,
            "server_names": control_names,
        },
        "reference_image": ref_name,
        "positive": POSITIVE_TEXT,
        "negative": NEGATIVE_TEXT,
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


def verify_topology(wf, arm, use_control, expects_reference=None):
    """Check every link resolves, and that the arm is actually the arm it claims to be.

    `expects_reference` binds the reference image in BOTH directions, which matters now
    that E03 deliberately runs without one. Passing None keeps the historical behaviour of
    not checking it at all — but every call site inside this module passes a value, so a
    reference that silently appeared or vanished between arms of one experiment cannot get
    past here. An arm whose reference differs from its siblings' is not the arm it claims
    to be, and that is exactly the kind of difference a report would never notice.
    """
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
            problems.append(
                f"{arm} is the null arm and must have NO control_video; "
                f"the arm would not be the arm"
            )
        if any(n["class_type"] == "BatchImagesNode" for n in wf.values()):
            problems.append(f"{arm} is the null arm and still carries a batch node")

    if expects_reference is not None:
        has_ref = "reference_image" in wf["49"]["inputs"]
        if has_ref != expects_reference:
            problems.append(
                f"reference_image is {'present' if has_ref else 'absent'} but this "
                f"experiment expects it {'present' if expects_reference else 'absent'}; "
                f"a reference that differs between arms is a second variable"
            )
        if has_ref and wf["49"]["inputs"]["reference_image"] != ["134", 0]:
            problems.append("reference_image is not fed by the reference LoadImage node")
        if not has_ref and "134" in wf:
            problems.append("a reference LoadImage node is present but nothing consumes it")

    if wf.get("302", {}).get("inputs", {}).get("images") != ["8", 0]:
        problems.append(
            "the lossless tap is not wired to VAEDecode (node 8); the floor would be "
            "measured through the H.264 path again"
        )

    for dead in ("LoadVideo", "GetVideoComponents", "Canny"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} present; the video bridge was not removed")

    if problems:
        raise PayloadError(f"[{arm}] link topology is wrong: " + "; ".join(problems))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="E02", choices=sorted(EXPERIMENTS))
    ap.add_argument("--arm", required=True,
                    choices=sorted({a for e in EXPERIMENTS.values() for a in e["arms"]}))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    wf, meta = build(a.arm, a.experiment)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(a.out.replace(".json", ".meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print("BUILD_PAYLOAD " + json.dumps({
        "experiment": a.experiment, "arm": a.arm, "nodes": len(wf), "gate_L": "PASS",
        "reference": meta["reference_image"],
        "control_distinct_images": (
            meta["control"]["distinct_images"] if isinstance(meta["control"], dict) else None),
        "sha256": meta["payload_sha256"][:16], "out": a.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
