#!/usr/bin/env python
"""build_animate_payload — E08's `WanAnimateToVideo` graph, built in this repo.

    python tools\\build_animate_payload.py --uploads=<uploads.json> --out=<dir> \
        --subject=PERFORMER --no-canon
           [--seed=2026081201 | --seeds-registry=specs\\E08-seeds.json]

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
from armature_core import canon as C  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from canon_gate import canon_line, canon_spend  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
from build_assembly_payload import (  # noqa: E402
    canonical_payload_digest, gate_create_video_fps, read_seed_registration,
    single_path_segment)

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
    """The payload could not be built as specified.

    Carries an optional evidence dict, the way `GateFailure` does. Wave 8 (F-bc806f79):
    `ledger_against_wave1` built a full evidence dict, wrote it into the payload record on
    the PASSING path, and then raised with a message and nothing else — so the failing
    measurement, the one worth having, reached no record at all. Four modules define this
    class; all four take the dict now, through the base's own constructor.

    **CORRECTION, wave 16 (F-c496fa48, rule 5).** This class used to define its own
    `__init__` normalising `evidence or {}`, under a note saying the single implementation
    "belongs beside `GateFailure` in `armature_core/errors.py`. That file is not this
    domain's to edit". Wave 14 put the constructor on the base and made a deliberate choice
    the four copies then overrode: `ArmatureError` STORES WHAT IT IS PASSED and normalises
    nothing, because `"evidence": null` beside `"gate": null` is the honest halt record for
    a refusal that carries no receipt. `GateFailure` is the one exemption - its clauses
    index into `ev` while they measure. `PayloadError` is not a gate, so the constructor is
    DELETED and the base's inherited: `PayloadError("m").evidence is None` and
    `PayloadError("m", d).evidence is d`, by identity.
    """


#: What each key of `--uploads` IS, so an absence is reported as an absence. Until wave 6
#: `uploads["pose_pack"]` and `uploads["reference"]` were indexed with no guard at all
#: (bare `KeyError: 'pose_pack'`, naming neither the file nor the flag, on the route where
#: the pose pack IS the conditioning), and `uploads.get("pose_frames")` was worse in a
#: quieter way: a missing key surfaced as "the pose pack declares None frames and the shot
#: is 81" — a message about a COUNT standing in for a missing key. `build_i2v_payload:476`
#: and `build_camera_i2v_payload:971` already guard exactly this shape; the fix was never
#: carried to the tool the other two were derived from.
UPLOAD_KEYS = {
    "reference": "the server-side name of the reference image this shot is performed from",
    "pose_pack": "the server-side name of the lossless animated WebP pose pack, which is "
                 "this route's whole conditioning",
    "pose_frames": "how many frames that pose pack declares, checked against the shot "
                   "length before anything is submitted",
}


def upload_value(uploads, key, source=None):
    """One entry of the upload map, or a PayloadError naming the file and the key."""
    if key not in uploads:
        where = f"{source} " if source else "the upload map "
        raise PayloadError(
            f"{where}carries no `{key}` entry: it is {UPLOAD_KEYS[key]}. Pass an "
            f"--uploads map that names it",
            {"clause": "missing_upload_key", "key": key,
             "source": os.path.abspath(source) if source else None,
             "present": sorted(uploads)})
    return uploads[key]


def require_uploads(uploads, source=None):
    """Every key this route needs, checked where `--uploads` is read. Returns the map."""
    for key in UPLOAD_KEYS:
        upload_value(uploads, key, source)
    return uploads


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
                         "center-crop; 'letterbox' names a pre-fitted reference, which "
                         "ASSERTS the file is already the generation frame. Pass "
                         "--reference-file to have that assertion MEASURED against the "
                         "artifact; without it the record says DECLARED-not-measured "
                         "rather than stating the fit as a fact")
    ap.add_argument("--reference-file", default=None,
                    help="the LOCAL path of the reference image that was uploaded. "
                         "`--uploads` carries only the server-side name, so without this "
                         "nothing here can open the file the record describes. Given, the "
                         "PNG header is read and a `letterbox` declaration that "
                         "contradicts the file raises `fit_disagrees_with_the_file` "
                         "(the clause `build_i2v_payload`'s start-frame path already "
                         "carries)")
    ap.add_argument("--seeds-registry", default=None)
    ap.add_argument("--experiment", default=EXPERIMENT,
                    help="names the output files and the server-side filename prefixes")
    ap.add_argument("--length", type=int, default=LENGTH,
                    help="frame count; Gate L and Gate ROUTE both check it (argparse eats "
                         "leading minus signs, so pass flags as --flag=value)")
    ap.add_argument("--fps", type=float, default=FPS,
                    help="the CreateVideo rate. Presentation only — it is downstream of "
                         "VAEDecode and cannot change a generated pixel")
    add_spend_flags(ap)
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
        # ⚠ This was `phrase not in text` followed by
        # `text.replace(", " + phrase, "").replace(phrase + ", ", "")` — a bare substring
        # edit with no word boundary, the same class core-gates closed in
        # `canon._find_phrase` (routed here 2026-09-04, F-138c009c's family): 'cape' matched
        # inside 'landscape'. A drop of a short single-word phrase — cape, helm, arm, hood,
        # mask, the form a surfaces file names an occupant with — would cut a hole in the
        # middle of an unrelated word and the change log would record a drop that did not
        # happen the way it says.
        #
        # Located through `canon._find_phrase`, which is the ONE matcher (core-gates owns
        # it; no second implementation here), so presence and removal cannot disagree and
        # the boundary rule arrives with the module rather than being re-derived.
        low = text.lower()
        idx = C._find_phrase(low, phrase.lower())
        if idx < 0:
            raise PayloadError(
                f"the identity clause no longer contains {phrase!r} as a whole phrase, so "
                f"this shot's recorded drop cannot be applied. The clause has changed under "
                f"the experiment and the change log would be describing a different string",
                {"phrase": phrase, "clause_sha256":
                    hashlib.sha256(original.encode("utf-8")).hexdigest()})
        before, after = text[:idx], text[idx + len(phrase):]
        if before.rstrip().endswith(","):
            before = before.rstrip()[:-1]
        elif after.lstrip().startswith(","):
            after = after.lstrip()[1:]
        text = re.sub(r"\s+", " ", (before + " " + after)).replace(" ,", ",")
        log.append({"dropped": phrase, "reason": reason})
    return text.strip().strip(",").strip(), original, log


#: What each `--reference-fit` choice ASSERTS about the file, and therefore what a
#: measurement can contradict. `letterbox` names a pre-fitted plate — a claim about the
#: artifact's dimensions. `as-is` claims nothing about size: the node center-crops it
#: (`common_upscale(..., "area", "center")`), so any size is consistent with the sentence.
#: Written out rather than implied by the clause, because "which declarations are checkable"
#: is the thing a reader of the record needs and the thing a new choice has to answer.
REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME = {"as-is": False, "letterbox": True}


def gate_reference_fit(fit, path, width=None, height=None):
    """Gate PAYLOAD · ANDON — the record's `fit` sentence, MEASURED where it is checkable.

    Wave 22, F-40220b64. `--reference-fit` is a two-choice label that performs no fitting:
    it was stored verbatim as `meta['reference_image']['fit']` and reached the record
    unexamined. RE-READ on `e8263a3`: the flag is declared with
    `choices=('as-is','letterbox')` and its help said "The choice and its measured
    consequence are recorded either way"; grepped over the whole file, nothing opened or
    measured the uploaded reference — no PNG header read, no IHDR, no size comparison — so
    the record could state 'as-is' over a letterboxed plate, or 'letterbox' over a plate
    that had never been fitted.

    The sibling precedent is in this domain and is ARMED: `build_i2v_payload` raises
    `fit_disagrees_with_the_file` when the declared fit contradicts the file it measured
    (wave 14, F-e17613c2), with `measured`, `generation_frame`, `path` and `sha256` in the
    evidence. This is the same clause, keyed on the caller's OWN sentence rather than on a
    constant here — a future fit that claims something else states its own assertion in
    `REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME` and is checked against that.

    CLAUDE.md names the grey letterbox pads on E08's reference as the standing suspect for
    its washed bands, which makes this the one field in the record most worth measuring
    rather than asserting.

    **Where no local path is available the record says so.** `--uploads` carries only the
    server-side name, so with no `--reference-file` there is nothing to open; the block
    returned then is explicitly DECLARED-not-measured, which is a recorded fact rather than
    a fit stated as one.
    """
    width = WIDTH if width is None else width
    height = HEIGHT if height is None else height
    asserts_frame = REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME.get(fit)
    if asserts_frame is None:
        raise PayloadError(
            f"--reference-fit {fit!r} has no recorded assertion about the file, so nothing "
            f"here can say whether a measurement would contradict it. Add the choice to "
            f"`REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME` in the same commit that adds it "
            f"to the parser",
            {"gate": "PAYLOAD", "andon": "reference_image",
             "clause": "reference_fit_has_no_recorded_assertion", "flag": "--reference-fit",
             "fit": fit,
             "known": sorted(REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME)})
    if path is None:
        return {
            "fit": fit,
            "measured": None,
            "declared_not_measured": True,
            "asserts_the_generation_frame": asserts_frame,
            "generation_frame": [width, height],
            "why_not_measured": (
                "--reference-file was not supplied. `--uploads` carries only the "
                "server-side name of the reference, so this build opened no file and the "
                "`fit` above is a DECLARATION, not a measurement. Pass --reference-file "
                "with the local artifact to have it checked"),
        }
    resolved = os.path.abspath(path)
    if not os.path.isfile(resolved):
        raise PayloadError(
            f"--reference-file {path!r} is not a file. The flag exists so the record's "
            f"`fit` sentence can be a measurement; a path that names nothing measures "
            f"nothing, and a build that silently fell back to the unmeasured branch would "
            f"record DECLARED-not-measured while the operator believed otherwise",
            {"gate": "PAYLOAD", "andon": "reference_image",
             "clause": "reference_file_missing", "flag": "--reference-file",
             "path": resolved, "exists": os.path.exists(resolved),
             "is_dir": os.path.isdir(resolved)})
    # `png_header` has ONE home — `build_camera_i2v_payload` — and this reads the reference
    # through it rather than writing a second IHDR reader (wave 22, F-40220b64). The import
    # is LOCAL because a module-level one closes a cycle: `build_camera_i2v_payload` imports
    # `build_i2v_payload`, which imports THIS module for the prompt's source of record.
    # Measured: a top-level import raised `AttributeError: partially initialized module
    # 'build_i2v_payload' ... (most likely due to a circular import)` at collection.
    import build_camera_i2v_payload as CAM

    header = CAM.png_header(resolved)
    digest = hashlib.sha256(open(resolved, "rb").read()).hexdigest()
    if header is None:
        with open(resolved, "rb") as fh:
            head = fh.read(8)
        raise PayloadError(
            f"--reference-file {path!r} is not a PNG this tool can read: its first 8 bytes "
            f"are {head.hex()!r} and no IHDR chunk follows them, so its width and height "
            f"cannot be measured and the record's `fit` sentence stays a claim",
            {"gate": "PAYLOAD", "andon": "reference_image",
             "clause": "reference_file_not_a_png", "flag": "--reference-file",
             "path": resolved, "first_8_bytes": head.hex(), "sha256": digest,
             "read_by": "IHDR, stdlib struct - no image library"})
    measured = [header["width"], header["height"]]
    if asserts_frame and measured != [width, height]:
        raise PayloadError(
            f"--reference-fit {fit!r} asserts a reference already fitted to this "
            f"generation's frame, and --reference-file is "
            f"{header['width']}x{header['height']} while the frame is {width}x{height}. "
            f"The record's own `fit` sentence would be untrue about the image this route "
            f"performs from. Re-fit the plate to {width}x{height}, or state the route's "
            f"real fit ('as-is' hands the reference to the node and lets it center-crop, "
            f"and passes this clause with its own words)",
            {"gate": "PAYLOAD", "andon": "reference_image",
             "clause": "fit_disagrees_with_the_file", "flag": "--reference-fit",
             "fit": fit, "asserts_the_generation_frame": True,
             "measured": measured, "generation_frame": [width, height],
             "path": resolved, "sha256": digest})
    return {
        "fit": fit,
        "measured": dict(header, path=resolved, sha256=digest),
        "declared_not_measured": False,
        "asserts_the_generation_frame": asserts_frame,
        "generation_frame": [width, height],
    }


def build(uploads, seed, negative, positive, registry, reference_fit,
          experiment=EXPERIMENT, length=LENGTH, fps=FPS, reference_file=None):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists."""
    # ---- Gate ROUTE - ANDON on `CreateVideo.fps` (wave 10, F-29693a0e, family carry).
    # `--fps` reached the node with no clause in all five builders that take the flag,
    # while every one of their records states the node's measured contract as
    # "fps FLOAT (1-120)". One implementation, in `build_assembly_payload`, imported here.
    gate_create_video_fps(fps)
    # ---- Gate PAYLOAD · ANDON on the record's `fit` sentence (wave 22, F-40220b64). Above
    # everything that writes, so a build whose declared fit contradicts the artifact leaves
    # no output directory.
    reference_block = gate_reference_fit(reference_fit, reference_file,
                                         width=WIDTH, height=HEIGHT)
    # The default is resolved BEFORE Gate S, not after it. The old order put
    # `seed_used = seed if seed is not None else (sorted(registry)[0] if registry else 0)`
    # BELOW a gate that refuses a non-int first, so the fallback was dead code and the
    # usage block's optional `--seed` always halted on a message about NoneType — an
    # operator following the documented invocation got a halt naming the wrong problem.
    # The `else 0` branch was worse than dead: it read as a working default and would have
    # shipped an unregistered seed the moment the ordering changed.
    if seed is None and not registry:
        # ---- wave 22, F-87600738. This raise carried NO second argument at all, so under
        # the wave-16 rule-5 base (`armature_core/errors.py`: a bare message stores `None`)
        # the halt line printed `"evidence": null` and the refusal carried no `gate`, no
        # `andon` and no `clause`. RE-MEASURED on `e8263a3` by grep across `tools/`: the
        # string `no_seed_and_no_registration` occurred at exactly ONE site,
        # `build_t2v_payload.py`, while THREE builders — this one, `build_i2v_payload` and
        # `build_camera_i2v_payload` — raised the same refusal as a sentence. Confirmed by
        # calling `build(...)` with `seed=None` and an empty registry: `PayloadError`
        # raised, `evidence` None, `gate` None. So of the four callers that default a seed
        # off the registration, one was machine-readable and three were prose: the clause
        # census that wave 16 built to prove every refusal is reachable and NAMED saw 1 of
        # the 4 sites, and an operator hitting it on three of the four routes got a halt a
        # wrapper cannot classify.
        raise PayloadError(
            "no --seed and no --seeds-registry: this experiment pre-registered no seeds, "
            "so there is no committed number to default to, and Gate S refuses a seed "
            "varied without a registration. Pass --seeds-registry with the experiment's "
            "committed list, or pass --seed with a number that is on it",
            {"gate": "PAYLOAD", "andon": "seed_registration",
             "clause": "no_seed_and_no_registration", "flag": "--seeds-registry",
             "registered": list(registry or [])})
    seed_used = seed if seed is not None else sorted(registry)[0]
    gate_s = gates.gate_s_seed_registration(seed_used, registry, experiment,
                                            seed_was_explicit=seed is not None)
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-animate")

    # Read through the guarded accessor, so a direct `build()` call refuses by name too:
    # `main` checks the map where --uploads is read, and this is the same check one
    # implementation deep rather than a second one.
    pose_name = upload_value(uploads, "pose_pack")
    packed = upload_value(uploads, "pose_frames")
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
        "134": {"class_type": "LoadImage",
                "inputs": {"image": upload_value(uploads, "reference")}},
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
        # `fit` is no longer a bare label: the block carries whether the declaration
        # ASSERTS anything about the file, what was measured, and — when nothing was — that
        # it is DECLARED-not-measured and why (wave 22, F-40220b64).
        "reference_image": dict(reference_block,
                                server_name=upload_value(uploads, "reference")),
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
        # Wave 20, F-dba1bcd8: through the ONE shared derivation, not a copy
        # of the expression. Four builders each carried their own spelling of it
        # and `route_facts` carried a fifth, five places for the digest the gate
        # compares against to drift from the digest a record declares.
        "payload_sha256": canonical_payload_digest(wf),
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
    # ---- ANDON, wave 22 (F-7e45e62b, sibling carry). `--experiment` is pasted into this tool's
    # written filenames with no clause, exactly as `fetch_run --run` was. Census over this
    # domain, 2026-09-05: FIVE free-string flags reach a written filename -- `--experiment`
    # in `build_animate_payload`, `build_i2v_payload` and `build_camera_i2v_payload`,
    # `--tag` in `build_t2v_payload` (whose own help says "goes in the written filenames"),
    # and `fetch_run --run`. `build_camera_i2v_payload --wave` also reaches a filename and
    # is ALREADY BOUNDED by `type=int` -- measured, argparse refuses `--wave=a/b` before
    # `main` is entered -- so it takes no clause of its own. The bounded convention already
    # exists in this domain: `build_payload --experiment` and `build_r2v` /
    # `build_lora_arm --arm` are `choices=`-bounded.
    #
    # The clause is `single_path_segment`'s, imported from its ONE home (SEAM 1): same
    # clause word `output_name_is_not_a_name`, same evidence keys.
    single_path_segment(a.experiment, "--experiment", PayloadError,
                        extra={"pasted_into": ["<out>/{experiment}-probe-animate.api.json",
                                        "<out>/{experiment}-probe-payload-record.json",
                                        "the server-side filename prefixes"]})
    out = os.path.abspath(a.out)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    require_uploads(uploads, a.uploads)

    registry = None
    if a.seeds_registry:
        # ONE reader, eight callers (wave 16, F-0682bd00). The bare `json.load(fh)["seeds"]`
        # this replaces raised a stdlib KeyError naming a key and nothing else on a
        # registration with no `seeds` key.
        registry = read_seed_registration(a.seeds_registry, flag="--seeds-registry")

    neg_path = a.negative_source
    if not neg_path:
        raise PayloadError(
            "--negative-source is required: Wan's sample_neg_prompt is READ from the banked "
            "config, never retyped. E09's citation check fired on exactly this string")
    negative = read_negative(neg_path)
    ident, ident_original, drops = identity_clause()
    positive = ident + ". " + SCENE_CLAUSE
    # The SHIPPED positive is what the router checks. `--canon-prompt` used to stand in
    # for it while `build()` was handed `positive` regardless.
    canon_ev = canon_spend(a.subject, positive, no_canon=a.no_canon, out_dir=out,
                           canon_prompt=a.canon_prompt)

    wf, meta = build(uploads, a.seed, negative, positive, registry, a.reference_fit,
                     experiment=a.experiment, length=a.length, fps=a.fps,
                     reference_file=a.reference_file)
    meta["gate_CANON"] = canon_ev
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

    os.makedirs(out, exist_ok=True)
    gpath = os.path.join(out, f"{a.experiment}-probe-animate.api.json")
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    mpath = os.path.join(out, f"{a.experiment}-probe-payload-record.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(canon_line(canon_ev))
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
