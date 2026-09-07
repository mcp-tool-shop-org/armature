#!/usr/bin/env python
r"""build_camera_i2v_payload — E11's camera-held graph, built in this repo.

    python tools\build_camera_i2v_payload.py --uploads=<uploads.json> --out=<dir> --subject=PERFORMER --no-canon
           --negative-source=<wan22_shared_config.py> --seeds-registry=specs\E11-seeds.json
           --w1-record=<E11-probe-payload-record.json> --start-frame=<start.png>
           [--seed=2026081233 | --seeds-registry=specs\\E12-seeds.json]

The camera-held route. Two levers move together and the record says so throughout: the
camera moves from the prompt to a **camera embedding**, and the prompt's centre of gravity
moves from the bar to the **performance**. Attribution between the two is NOT claimed by
this build or by the report it feeds; the wave-1 probe is the baseline and the target is the
shot.

--------------------------------------------------------------------------------
⚠ THIS TOOL BUILT WAVE 2, WHICH PRODUCED NOTHING — READ THAT BEFORE TRUSTING IT

At `TOOL_VERSION = "E11.2"` this file loaded `W1.UNET_HIGH` / `W1.UNET_LOW` — the plain
Wan 2.2 I2V experts — under `WanCameraImageToVideo`. The camera tier is a **separate
checkpoint**; the I2V base has no channel for a camera embedding. The run passed Gate PIN,
Gate L, Gate S, Gate ROUTE on both the built and the saved graph, and Gate B, then returned
65 frames whose subject survived exactly one frame.

Two things changed as a result and both are load-bearing here:

* the experts below are the **Fun-Camera** pair, named from `search_models` rather than
  inherited from a neighbouring route;
* `route_gates.pairing` (**Gate PAIR**) now refuses this class of mistake in-tool, and its
  red test is wave 2's exact graph, banked at `tests/fixtures/E11-w2-camera-i2v.api.json`.

The corrected wave also moves length, resolution and the start frame — see
`DELIBERATE_BREAKS`, which the ledger gate requires to have ACTUALLY happened, because a
report describing a correction that did not happen is wave 2's failure one wave later.

--------------------------------------------------------------------------------
⚠ THE ROUTE'S NAME CHANGES HERE, AND THAT IS NOT A DETAIL

Wave 1 was "no control of any kind" and its builder enforced that literally:
`build_i2v_payload.CONTROL_CLASSES` lists `WanCameraImageToVideo` among the conditioning
classes whose mere presence ends the experiment. **Wave 2 wires exactly that node.**

That earlier gate is NOT edited, deleted, or loosened — it governed a run that has already
happened, and rewriting it would rewrite the receipt of a completed generation. Wave 2 gets
its own ban list instead, drawn on a different line:

    wave 1: no signal drives ANYTHING.
    wave 2: no signal drives the PERFORMER. The camera is held.

What that buys and what it costs, stated rather than smoothed over. The performer's motion,
pose, blocking and identity remain entirely the model's invention from a single start frame
— no pose sticks, no reference image, no control video, no clip-vision embedding, and
`verify_topology` below refuses the graph if any of them appear. What is no longer free is
the CAMERA: a `Static` trajectory is imposed on it. Wave 1 measured the price of leaving the
camera free (an uncommanded push-in; the horizon found on 4 of 65 frames and never again),
and the prompt clause that was supposed to prevent it — "The camera is static." — was
present in wave 1's positive and did nothing. So the honest description of wave 2's route is
**"the model performs; the camera is held"**, and any report that calls it the no-control
route without that qualifier is describing wave 1.

--------------------------------------------------------------------------------
Where every number comes from

Nothing about the sampling trajectory is re-derived here. `build_i2v_payload`'s `TRAJECTORY`
is IMPORTED and re-emitted, so "held constant against wave 1" is a property of the code
rather than a claim in a document — steps 20, split at 10, shift 8.0, cfg 3.5, euler,
simple, fps 16, all still sourced to the two pinned commits of the LoRA-free I2V reference
workflow. Same weights, same text encoder, same VAE, same 832x480x65 frame, same uploaded
start frame. `pin_against_wave1` re-checks each of those against wave 1's committed payload
record and halts on any drift.

The two new nodes come from `get_node` (fetched 2026-08-12), never from a served template —
`search_templates` carries no workflow wiring this tier at all, so there is no template to
be tempted by:

  * `WanCameraEmbedding` — core, `model/conditioning/wan/camera`. `camera_pose` is a COMBO
    whose options include `Static`; width/height/length must match the generated frame (the
    node defaults to 81 and this route runs 65 — see `route_gates.CAMERA_NODES`, where that
    exact mismatch is an andon). `speed`, `fx`, `fy`, `cx`, `cy` are left at their declared
    defaults: this build changes the camera from free to held, and moving an intrinsic in
    the same wave would be a third lever nobody asked for.
  * `WanCameraImageToVideo` — core, same category. Same sockets as `WanImageToVideo` plus
    `camera_conditions`. It sizes its own latent, so it is entered in
    `route_gates.LATENT_NODES` the day it is first used.

--------------------------------------------------------------------------------
The prompt, and the pin that had to be released to change it

Wave 1's builder pinned its positive and negative **byte-identical to E08's** and halted on
any drift; that pin is what made "same prompt, different route" a measurement. Wave 2 is
directed to rewrite the prompt, so that pin is **released deliberately and the release is
recorded** — with the E08 comparison it supported explicitly retired. What replaces it is
the inverse check: the prompt must NOT still be wave 1's. A wave-2 build that quietly
submitted wave 1's strings would produce a null result wearing a full set of receipts, so
`pin_against_wave1` raises if the positive it built matches the one wave 1 ran.

The surgery itself, per the dispatch: the performance clause leads and dominates, the bar
demotes to set-dressing. "Dominates" is measured, not asserted — `PROMPT_DOMINANCE` counts
the words in each clause and the build halts if the set-dressing is not clearly outweighed.
The identity clause is carried VERBATIM from the same source wave 1 read it from
(`build_animate_payload.identity_clause`), because identity is what the experiment is
watching and rewriting its description would confound the one read the Director rules on.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory. It submits nothing and spends nothing.
"""

import argparse
import hashlib
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from canon_gate import canon_line, canon_spend  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.
from build_assembly_payload import (  # noqa: E402
    canonical_payload_digest, comfy_cloud_oss_disclosure, disclosure_lines,
    fetch_recipe, gate_create_video_fps, gate_output_not_overwritten,
    read_seed_registration, single_path_segment)

import build_animate_payload as E08  # noqa: E402  - the identity clause's source of record
import build_i2v_payload as W1  # noqa: E402  - wave 1's trajectory, weights and frame

TOOL_VERSION = "E11.3"
EXPERIMENT = "E11"
WAVE = 3

#: ---------------------------------------------------------------------------------------
#: THE EXPERTS. Wave 2 loaded `W1.UNET_HIGH` / `W1.UNET_LOW` — the plain I2V pair — under a
#: camera conditioning node, and produced 65 frames with no subject after the first. The
#: camera tier is its own checkpoint. Names MEASURED via `search_models` 2026-08-12: the
#: catalog serves exactly four `wan2.2_fun_camera` diffusion_model entries (bf16 and
#: fp8_scaled, high and low), from Comfy-Org/Wan_2.2_ComfyUI_Repackaged
#: `split_files/diffusion_models/`. The fp8_scaled pair is taken because that is the tier
#: waves 1 and 2 ran, so the swap moves the model family and not the quantisation as well.
UNET_HIGH = "wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors"
UNET_LOW = "wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors"

#: Text encoder and VAE stay wave 1's — same family, and the Fun-Camera card names no other.
CLIP_NAME, VAE_NAME = W1.CLIP_NAME, W1.VAE_NAME

#: ---------------------------------------------------------------------------------------
#: THE FRAME, DERIVED — not assumed, and not inherited from a model this route does not run.
#:
#: The card's verbatim envelope (README_en.md, fetched 2026-08-12): *"multi-resolution (512,
#: 768, 1024) video prediction, trained with 81 frames at 16 FPS"*.
#:
#: **Length** is 81: the card's own trained frame count, and 4·20+1 so Gate L's 4n+1 form
#: holds. Waves 1 and 2 ran 65 — legal, but below this model's trained horizon for no reason
#: that survives the model swap. (The Director's standing more-fps ruling agrees, though it
#: is not the reason: the reason is the card.)
#:
#: **Resolution** is derived against the tiers rather than carried over. The tiers are area
#: buckets, so for tier N the in-distribution frame at aspect r is w=N·√r, h=N/√r, rounded
#: to the VAE's multiple of 16. Waves 1–2 ran 832×480 — area 399,360 — which sits BETWEEN
#: the 512 tier (262,144) and the 768 tier (589,824) and matches neither. Enumerated:
#:
#:   tier 512  -> 688×384  = 264,192 px   — below waves 1–2, a resolution downgrade
#:   tier 768  -> 1024×576 = 589,824 px   — EXACT: 768·4/3 = 1024, 768·3/4 = 576, no rounding
#:   tier 1024 -> 1360×768 = 1,044,480 px — 2.6× waves 1–2, ~3.3× the pixel-frames
#:
#: The 768 tier is taken. It is the only tier that lands on a legal frame with **zero
#: rounding** (both dims already multiples of 16), it is the nearest tier ABOVE waves 1–2 so
#: the comparison is not read against a downgrade, and the 1024 tier would spend roughly
#: 3.3× the pixel-frames of wave 1 on the last reserve for nothing the card promises.
#:
#: The aspect moves 1.733 → 1.778 (16:9) as a consequence, and that is a real change to the
#: authored frame, recorded rather than smuggled: the start frame is re-rendered at this
#: size, so the camera reframes the figure to it rather than anything being stretched.
FRAME_DERIVATION = {
    "source": ("huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera README_en.md, "
               "fetched 2026-08-12, verbatim: 'multi-resolution (512, 768, 1024) video "
               "prediction, trained with 81 frames at 16 FPS'"),
    "tiers_are": ("area buckets — for tier N at aspect r, w=N·√r and h=N/√r, rounded to the "
                  "VAE's multiple of 16"),
    "candidates": [
        {"tier": 512, "frame": [688, 384], "area": 264192,
         "rejected": "below waves 1–2's 399,360 px — a resolution downgrade"},
        {"tier": 768, "frame": [1024, 576], "area": 589824, "chosen": True,
         "why": ("exact: 768·4/3 = 1024 and 768·3/4 = 576, both already multiples of 16, so "
                 "the tier is hit with zero rounding; and it is the nearest tier above "
                 "waves 1–2")},
        {"tier": 1024, "frame": [1360, 768], "area": 1044480,
         "rejected": ("~3.3× wave 1's pixel-frames on the last reserve, for nothing the "
                      "card promises over the 768 tier")},
    ],
    "waves_1_and_2_ran": {"frame": [832, 480], "area": 399360,
                          "note": ("matches NO tier — it is the plain I2V model's default, "
                                   "which is a different model's document")},
    "aspect_change": {"from": 1.7333, "to": 1.7778,
                      "consequence": ("the start frame is re-rendered at 1024×576, so the "
                                      "camera reframes to the new aspect; nothing is "
                                      "stretched or cropped from wave 1's pixels")},
}

WIDTH, HEIGHT, LENGTH, FPS = 1024, 576, 81, W1.FPS

#: The camera lever. `Static` is the option consult #7 identified and `get_node` confirms is
#: served; the rest are the node's declared defaults, unmoved.
CAMERA_POSE = "Static"
CAMERA_SPEED = 1.0
CAMERA_INTRINSICS = {"fx": 0.5, "fy": 0.5, "cx": 0.5, "cy": 0.5}

#: ---------------------------------------------------------------------------------------
#: THE PROMPT SURGERY
#:
#: Wave 1's non-identity text was one word of performance ("dancing") inside twenty-eight
#: words of bar. The Director's diagnosis of the resulting motion was that the bar language
#: pulled the performance toward it. So the two clauses swap weight.
#:
#: Written to the guidance banked in `PROMPT_GUIDANCE` below: natural language, no weight
#: syntax (Wan does not honour `(word:1.2)`, so emphasis has to come from ORDER and
#: PROPORTION), explicit verbs, and the motion sub-elements the published formula names —
#: amplitude, speed, and the effect of the movement.
PERFORMANCE_CLAUSE = (
    "He is dancing, a full and energetic dance: knees bending and springing, hips swinging "
    "from side to side, shoulders rolling, both arms lifting and swinging wide above his "
    "head, torso twisting, his weight rocking from one foot to the other, bouncing on the "
    "beat, fast and loose and continuous, never standing still")

#: Everything the bar is allowed to be now. Wave 1's version of this sentence carried the
#: crowd, the counter, the bottles and the glasses; it arrived in full and took the
#: performance with it.
SET_DRESSING_CLAUSE = "Behind him, a dim warmly lit bar interior."

#: Wave 1's positive ended "The camera is static." — and the camera pushed in anyway, which
#: is the measured fact that put the embedding in this wave. The sentence is DROPPED rather
#: than kept alongside the embedding, for two recorded reasons: the embedding now holds the
#: camera mechanically, and Wan's own negative (read from the banked config, unedited)
#: contains 静态 and 静止不动的画面 — "static" and "motionless picture" — so a positive
#: sentence asking for a static camera is arguing with the negative on the same word. Kept,
#: it would be a third lever whose contribution nobody could separate; dropped, the camera
#: claim belongs entirely to the embedding.
CAMERA_SENTENCE_DROPPED = "The camera is static."

#: The negative extension. Recorded with its gloss because a term nobody can read is a term
#: nobody can check.
#:
#: ⚠ **The base negative ALREADY carries five hand and deformity terms** — 残缺的
#: (mutilated), 多余的手指 (extra fingers), 画得不好的手部 (badly drawn hands), 畸形的
#: (deformed), 手指融合 (fused fingers) — and wave 1's claw appeared through all of them.
#: This extension is therefore made as directed but the record states its prior: adding a
#: sixth and seventh term to a string that already failed on five is not where the evidence
#: points, and **no hand improvement may be attributed to this extension alone.** The
#: mannequin's hands are modelled as mittens in the source GLB; a prompt cannot add fingers
#: to geometry that has none, and the geometry fix stays on the F-series ledger.
NEGATIVE_EXTENSION = [
    ("爪状的手", "claw-shaped hands — names the defect the Director's eye landed on"),
    ("钩状的手指", "hook-shaped fingers — the curl that reads as a claw"),
]

#: The guidance this prompt was written to, with what was and was not retrievable. Fetched
#: 2026-08-12. A citation that cannot be resolved is recorded as unresolved, never as a
#: plausible reference with a verdict beside it.
PROMPT_GUIDANCE = {
    "retrieved": [
        {"source": "ComfyUI Comfy-Cloud bundled model guide, family `wan` "
                   "(`get_prompting_guide(model='wan')`, fetched 2026-08-12) — the guide "
                   "shipped by the tool that submits this graph",
         "operative_lines": [
             "Prompting style: natural_language",
             "Prompt weights (e.g. `(word:1.2)`): not honored",
             "Wan 2.x (text-to-video / image-to-video) takes natural-language descriptions "
             "of the scene AND its motion.",
             "Don't omit motion description — Wan needs verbs and camera direction to "
             "animate.",
         ],
         "how_it_shaped_the_prompt": (
             "'not honored' is the load-bearing line: emphasis cannot be bought with weight "
             "syntax, so the performance clause dominates by position and word count "
             "instead. 'Needs verbs' is why the clause is built out of bending, swinging, "
             "rolling, lifting, twisting, rocking and bouncing rather than adjectives")},
        {"source": "Wan-Video/Wan2.2 README (github.com/Wan-Video/Wan2.2, fetched "
                   "2026-08-12) — the model's own repository",
         "operative_lines": [
             "Extending the prompts can effectively enrich the details in the generated "
             "videos, further enhancing the video quality. Therefore, we recommend enabling "
             "prompt extension.",
         ],
         "how_it_shaped_the_prompt": (
             "supports a longer and more specific performance clause rather than a terse "
             "one; the repo's own prompt-extension step is not used here because it would "
             "put an unpinned model between the spec and the submission")},
    ],
    "NOT_RETRIEVED": [
        {"source": "the official Wan 2.2 Prompt Guide",
         "url": "https://alidocs.dingtalk.com/i/nodes/EpGBa2Lm8aZxe5myC99MelA2WgN7R35y",
         "status": "ATTEMPTED 2026-08-12, NOT RETRIEVED — the page renders its content via "
                   "JavaScript and returns no text to a fetch. Both official sources above "
                   "defer to this document for prompt structure, so the most authoritative "
                   "statement of the formula is UNREAD, and nothing in this record is "
                   "sourced to it"},
    ],
    "third_party_corroboration_only": {
        "claim": "a widely-republished formula ordering prompts as Subject + Scene + Motion "
                 "+ Aesthetic Control + Stylization, with motion described by amplitude, "
                 "speed and effect",
        "status": "NOT OFFICIAL. Several independent third-party guides state this and "
                  "agree with each other, which is weak corroboration and is recorded as "
                  "such. It is consistent with the two retrieved sources and with the "
                  "dispatch's own instruction, so it changed nothing that those did not "
                  "already decide",
    },
    "known_divergence_left_alone": (
        "the bundled `wan` guide recommends cfg ~6 and uni_pc; this graph runs cfg 3.5 and "
        "euler because `build_i2v_payload.TRAJECTORY` reads them off the official I2V "
        "reference workflow at two pinned commits, and that trajectory is held constant "
        "against wave 1. The divergence is recorded rather than resolved — changing the "
        "sampler under a prompt experiment would confound both"),
}

#: The dominance requirement, made checkable. The dispatch says the performance clause
#: leads and dominates; a build that quietly produced the opposite would still look tidy.
PROMPT_DOMINANCE = {"min_ratio": 3.0}


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

    **WAVE 25, F-af838b99 — the class-level `gate`.** All thirteen tools in this domain
    print their halt line through `armature_core.parts.run_tool_main` now, which writes
    `getattr(exc, "gate", None)` into the record's `gate` key. `PayloadError` was the only
    class raised in this domain carrying none, so a payload refusal read `gate: null` from
    BOTH sources — the class attribute and, at the sites that pass no dict, the evidence —
    while fourteen raise sites were already writing `{"gate": "PAYLOAD"}` into their
    evidence literal. The id gets its owner, the way wave 18 gave `SAVED_ADMISSION` one.
    `gate` is a plain class attribute here and NOT a `GateFailure`: `__str__`'s `[gate]`
    prefix is defined on `GateFailure`, so no message text changes, and `halt_outcome`
    still reads this as "REFUSED — the tool declined to proceed" rather than as a gate
    that fired.
    """

    gate = "PAYLOAD"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Build and gate the Fun-Camera i2v route's API graph: one start frame plus a "
            "camera trajectory, pinned against wave 1's committed record. Writes the graph "
            "and its payload record; submits nothing."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
                "ROUTE: E12's camera arm, and the baseline E14's LoRA arms are measured against. The trajectory is pinned to --w1-record and every DELIBERATE_BREAK is REQUIRED to have actually happened - a report describing a correction that did not occur is the failure shape this ledger exists to refuse.\n"
                "\n"
                "WHAT A REFUSAL COSTS: nothing but your time; it is spent here rather than on a submission."))
    build_opts = ap.add_argument_group("build")
    output_opts = ap.add_argument_group("output")

    build_opts.add_argument("--uploads", required=True, help="JSON: {start_frame: <server name>}")
    output_opts.add_argument("--out", required=True,
                    help="the directory the graph and its payload record are written into, "
                         "created below the last gate so a refusal leaves nothing behind; "
                         "an existing build there is refused unless --overwrite is passed")
    output_opts.add_argument("--overwrite", action="store_true",
                    help="replace an existing graph/record pair in --out. Without it a "
                         "rebuild over an earlier build refuses by name "
                         "(`output_already_exists`) and names both digests")
    build_opts.add_argument("--seed", type=int, default=None,
                    help="the seed to submit; omitted, the first seed in --seeds-registry "
                         "is used. Gate S refuses an unregistered number either way")
    build_opts.add_argument("--negative-source", default=None,
                    help="path to Wan's shared_config.py; the base negative is READ from it "
                         "rather than retyped, then extended")
    build_opts.add_argument("--w1-record", required=True,
                    help="wave 1's committed payload record. The trajectory is pinned "
                         "against it, the four DELIBERATE_BREAKS are required to have "
                         "actually happened, and the positive is required to DIFFER")
    build_opts.add_argument("--start-frame", default=None,
                    help="path to the LOCAL re-authored start frame. Required: this is the "
                         "single load-bearing control input of an i2v route, and CLAUDE.md "
                         "requires every generation to record its control-input hashes. "
                         "The tool hashes the file itself; it does not accept a typed "
                         "digest as the record")
    build_opts.add_argument("--start-frame-sha256", default=None,
                    help="OPTIONAL cross-check only. When given it must equal the sha256 "
                         "the tool computes from --start-frame, or the build halts. It is "
                         "never the recorded value: a digest nothing checks is worse than "
                         "an absent one")
    build_opts.add_argument("--seeds-registry", default=None,
                    help="the committed seed registration Gate S checks --seed against, and "
                         "the list the default seed is taken from")
    build_opts.add_argument("--experiment", default=EXPERIMENT,
                    help="names the output files and the server-side filename prefixes "
                         "(default: %(default)s)")
    build_opts.add_argument("--length", type=int, default=LENGTH,
                    help="frame count, checked by Gate L and Gate ROUTE (argparse eats "
                         "leading minus signs, so pass flags as --flag=value) "
                         "(default: %(default)s)")
    build_opts.add_argument("--fps", type=float, default=FPS,
                    help="the CreateVideo rate (default: %(default)s). Presentation only - "
                         "it is downstream of VAEDecode and changes no generated pixel")
    build_opts.add_argument("--cfg", type=float, default=None,
                    help="move the sampler cfg off wave 1's value. The ledger then REQUIRES "
                         "it to actually differ, and requires every trajectory field not "
                         "named here to still match wave 1's")
    build_opts.add_argument("--sampler", default=None,
                    help="move the sampler_name off wave 1's value, same contract as --cfg")
    build_opts.add_argument("--trajectory-source", default=None,
                    help="where the overridden values come from, into the record - a number "
                         "with no history is indistinguishable from a typo a month later")
    build_opts.add_argument("--wave", type=int, default=WAVE,
                    help="which wave of the experiment this is. Labels the graph and "
                         "record filenames, the record's own `wave` field and the cloud "
                         "output prefixes; a baked constant here writes plausible labels "
                         "pointing at the wrong run the first time the tool is reused")
    add_spend_flags(ap)
    return ap.parse_args(argv)


def word_count(text):
    """Words, for the dominance measurement. Punctuation is not a word."""
    return len([w for w in re.split(r"[\s,.:;—-]+", text.strip()) if w])


def build_prompt():
    """The wave-2 positive, plus the change log against wave 1's.

    The identity clause is re-read from its own source through E08's own code — the same
    call wave 1 made — so it is carried verbatim rather than copied out of a record.
    """
    ident, ident_original, drops = E08.identity_clause()
    positive = f"{ident}. {PERFORMANCE_CLAUSE}. {SET_DRESSING_CLAUSE}"

    perf_words = word_count(PERFORMANCE_CLAUSE)
    dress_words = word_count(SET_DRESSING_CLAUSE)
    ratio = perf_words / dress_words if dress_words else float("inf")
    if ratio < PROMPT_DOMINANCE["min_ratio"]:
        raise PayloadError(
            f"the performance clause does not dominate: {perf_words} words against the set "
            f"dressing's {dress_words} (ratio {ratio:.2f}, floor "
            f"{PROMPT_DOMINANCE['min_ratio']}). The wave exists to invert wave 1's "
            f"proportion, and a prompt that did not would be measuring the camera lever "
            f"alone while the report described two",
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "performance_clause_does_not_dominate",
             "performance_words": perf_words, "dressing_words": dress_words,
             "ratio": ratio, "min_ratio": PROMPT_DOMINANCE["min_ratio"]})

    log = {
        "carried_verbatim": {"identity_clause": ident,
                             "source": E08.TWIN_PROMPT_JSON,
                             "why": ("identity is what the Director rules on; rewriting the "
                                     "subject's description would confound that read")},
        "added": {"performance_clause": PERFORMANCE_CLAUSE,
                  "why": ("the Director's diagnosis of wave 1: the bar language pulled the "
                          "performance toward it. This clause leads the non-identity text "
                          "and outweighs the set dressing")},
        "demoted": {"from": E08.SCENE_CLAUSE, "to": SET_DRESSING_CLAUSE,
                    "why": "the bar becomes background rather than the subject of the shot"},
        "dropped": {"sentence": CAMERA_SENTENCE_DROPPED,
                    "why": ("the embedding holds the camera mechanically; wave 1 measured "
                            "this sentence failing, and it argues with 静态 in the "
                            "unedited negative")},
        "dominance": {"performance_words": perf_words, "set_dressing_words": dress_words,
                      "ratio": round(ratio, 2), "floor": PROMPT_DOMINANCE["min_ratio"],
                      "wave_1_for_comparison": {
                          "performance_words": 1, "scene_words": word_count(E08.SCENE_CLAUSE),
                          "note": ("wave 1's performance was the single word 'dancing' "
                                   "inside the scene clause counted here")}},
        "identity_clause_original": ident_original,
        "identity_drops": drops,
    }
    return positive, log


def build_negative(negative_source):
    """Wan's own `sample_neg_prompt`, read from the banked config, then extended as directed."""
    base = E08.read_negative(negative_source)
    added = [term for term, _ in NEGATIVE_EXTENSION]
    negative = base + "，" + "，".join(added)
    already = [t for t in ("残缺的", "多余的手指", "画得不好的手部", "畸形的", "手指融合")
               if t in base]
    return negative, {
        "base_source": os.path.abspath(negative_source),
        "base_sha256": hashlib.sha256(base.encode("utf-8")).hexdigest(),
        "base_unedited": True,
        "appended": [{"term": t, "gloss": g} for t, g in NEGATIVE_EXTENSION],
        "hand_terms_already_present_in_base": already,
        "prior_recorded_before_the_run": (
            f"the base already carried {len(already)} hand/deformity term(s) and wave 1's "
            f"claw appeared through all of them. No hand improvement may be attributed to "
            f"this extension alone"),
        "combined_sha256": hashlib.sha256(negative.encode("utf-8")).hexdigest(),
    }


#: What wave 3 deliberately breaks against wave 1, each with the reason and the authority.
#: The E11 w2 ruling: *"The weights-held pin against wave 1 breaks by necessity; the
#: comparison is route-level and says so."* A break that is listed is a stated limit on the
#: comparison; a break that is not listed is a confound nobody noticed, and the difference
#: between the two is entirely whether somebody wrote it down before the run.
DELIBERATE_BREAKS = {
    "weights": {
        "wave_1": "wan2.2_i2v_{high,low}_noise_14B_fp8_scaled",
        "wave_3": "wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled",
        "why": ("THE correction. Wave 2 fed a camera embedding to the plain I2V base, which "
                "has no channel for it, and produced 65 frames with no subject after the "
                "first. Gate PAIR now refuses that pairing in-tool"),
        "authority": "E11 w2 ruling R5(1)"},
    "length": {
        "wave_1": 65, "wave_3": 81,
        "why": ("the Fun-Camera card's own trained frame count; 65 was the I2V default, a "
                "different model's number"),
        "authority": "E11 w2 ruling R5(2) + the card, fetched 2026-08-12"},
    "resolution": {
        "wave_1": [832, 480], "wave_3": [WIDTH, HEIGHT],
        "why": ("derived against the card's 512/768/1024 training tiers — 832x480 matches "
                "none of them. See FRAME_DERIVATION for the enumeration"),
        "authority": "E11 w2 ruling R5(3)"},
    "start_frame_pixels": {
        "wave_1": "832x480 RGB, world background baked opaque",
        "wave_3": ("1024x576, authored RGBA, submitted composite over a named colour "
                   "recorded in the render provenance"),
        "why": ("the alpha law (CLAUDE.md, the Director's ruling 2026-08-12) plus the "
                "resolution change — the frame has to be re-rendered either way"),
        "authority": "E11 w2 ruling R5(4)"},
}


#: PNG colour types, from the format spec. 6 and 4 are the two that carry an alpha
#: CHANNEL; 0, 2 and 3 may carry transparency through a tRNS chunk instead, which
#: `_has_trns` below reads (wave 16, F-71ffdbfb - until then the comment named a
#: spelling the line under it could not see).
_PNG_COLOR_TYPES = {0: "grayscale", 2: "rgb", 3: "palette", 4: "grayscale_alpha",
                    6: "rgba"}


def _has_trns(fh):
    """Does this PNG carry a `tRNS` chunk? Walks the chunk list; decodes nothing.

    Wave 16, F-71ffdbfb. `alpha = color_type in (4, 6)` could not see a tRNS chunk, and
    `_PNG_COLOR_TYPES` above already said it existed ("3 is a palette, which may carry
    transparency through a tRNS chunk"). The comment was right and the line below it
    answered False, so a palette PNG carrying real transparency was recorded as opaque on
    the one input this route's docstring calls the whole of its conditioning. Colour types
    0 and 2 may carry one too, so the walk is not palette-only.

    The walk stops at the first `IDAT`: the spec requires `tRNS` before it, so nothing
    after the image data can change the answer, and no pixel data is ever read.
    """
    fh.seek(8)                                   # past the signature
    while True:
        head = fh.read(8)
        if len(head) < 8:
            return False
        length, tag = struct.unpack(">I", head[:4])[0], head[4:8]
        if tag == b"tRNS":
            return True
        if tag in (b"IDAT", b"IEND"):
            return False
        fh.seek(length + 4, 1)                   # payload + CRC


def png_header(path):
    """`{width, height, bit_depth, color_type, alpha, alpha_source}` from the file, or None.

    Stdlib only - 20 bytes of `struct` and a walk of the chunk headers, no Pillow - because
    this runs in the CPU builders and the render side already refuses to take a dependency
    for the same reason (`armature_core.pngio` is a writer with no reader for exactly that
    trade).

    **Why a builder measures this at all** (the Director's alpha ruling, 2026-08-12):
    every reference or start-frame render of the character is authored RGBA with a real
    alpha channel, and the RGB composite each route submits is a deliberate, recorded
    choice. Until wave 10 this route's record asserted `fit: "native - authored at
    832x480"` about an image the tool never opened, so nothing could contradict it: a
    re-authored, resampled or flattened start frame left the sentence unchanged. The
    numbers here come from the artifact, so `fit` becomes a measurement instead of a claim
    and the record says whether the submitted input carries alpha at all.

    **CORRECTION, wave 16 (F-71ffdbfb).** `alpha` was `color in (4, 6)` and was wrong in
    one direction: a palette PNG carrying transparency through a tRNS chunk - and equally a
    grayscale or truecolour PNG carrying one - reported `alpha: False`. Transparency in
    this format has two spellings and only one was read. `alpha_source` now names which
    spelling answered (`"color_type"`, `"tRNS"`, or `None` when the file is opaque), so the
    clause that reads the boolean can say what it read it off.
    """
    with open(path, "rb") as fh:
        head = fh.read(33)
        if (len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\x0a"
                or head[12:16] != b"IHDR"):
            return None
        width, height, depth, color = struct.unpack(">IIBB", head[16:26])
        if color in (4, 6):
            alpha, source = True, "color_type"
        elif _has_trns(fh):
            alpha, source = True, "tRNS"
        else:
            alpha, source = False, None
    return {"width": width, "height": height, "bit_depth": depth,
            "color_type": _PNG_COLOR_TYPES.get(color, color),
            "alpha": alpha, "alpha_source": source,
            "read_by": "IHDR + the chunk list, stdlib struct - no image library"}


def resolve_start_frame(path, declared_sha256):
    """The start frame's sha256, COMPUTED from the artifact. Raises rather than accepting.

    Wave 3, F-d342f393. `--start-frame-sha256` defaulted to None and was threaded through
    `ledger_against_wave1` only to be stored as
    `ev["start_frame"]["wave_3_local_sha256"]`. It appeared in no comparison and in no
    `problems.append` condition, so the hash of the re-authored start frame — the single
    load-bearing control input of an i2v route, and the artifact the Director's alpha
    ruling governs — was an optional operator-typed string that rode the record unverified
    and read as `null` when omitted. CLAUDE.md requires every generation to record its
    control-input hashes, and a value nothing checks is worse than an absent one.

    So the tool reads the file. A declared digest is kept only as a cross-check, and a
    declared digest that disagrees with the bytes halts the build.
    """
    # ---- wave 18 (F-c080a03f). These two raises carried NO evidence at all — measured on
    # the base tree, `exc.evidence` was `None` for both, so `evidence['clause']` was None
    # and a triage keyed on it could not distinguish "no such file" from "not a PNG this
    # tool can read". That is the consequence the finding names, one door up from the carry
    # it names; the third refusal below (a declared digest that disagrees with the bytes)
    # had the same hole. All three are named now, with the keys `start_frame_not_a_png`
    # already carried.
    base = {"gate": "PAYLOAD", "andon": "start_frame", "flag": "--start-frame",
            "path": os.path.abspath(path) if path else None}
    if not path:
        raise PayloadError(
            "--start-frame is required: this route's whole conditioning is one image, and "
            "a record that cannot name that image's bytes is not a recipe. Pass the local "
            "path to the re-authored start frame; the tool hashes it",
            dict(base, clause="start_frame_not_supplied", supplied=path))
    if not os.path.isfile(path):
        raise PayloadError(
            f"--start-frame {path!r} is not a file, so there is nothing to hash and no "
            f"control-input hash to record",
            dict(base, clause="start_frame_is_not_a_file",
                 is_dir=os.path.isdir(path), exists=os.path.exists(path)))
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    ev = {"path": os.path.abspath(path), "sha256": digest,
          "bytes": os.path.getsize(path), "source": "hashed_in_tool",
          # The alpha ruling's half: what the authored artifact actually IS, measured,
          # beside whatever the record asserts about how it was fitted. `None` when the
          # file is not a PNG, which is itself a fact worth recording on a route whose
          # entire conditioning is this one image.
          "image": png_header(path)}
    # ---- ANDON, wave 12 (F-08853dfb). `png_header` DECLINES TO GUESS at a file without an
    # IHDR and returns None; storing that None was the end of the matter, so a 403-byte file
    # with a JPEG header rode this route as the whole of its conditioning with
    # BUILD_I2V_OK printed, and `fit_agrees_with_the_file` degraded to a null on exactly the
    # input the comparison exists for — leaving the record's asserted `fit` sentence
    # unchallenged. Measured 2026-09-04 against this function: a 1024x576 RGBA PNG, a
    # 1024x576 RGB PNG and a 403-byte JPEG-headed file were all ACCEPTED; the third returned
    # image: None. A route whose whole conditioning is one image may not record a
    # conditioning input it could not open.
    #
    # The two jobs stay separate: the READER reports an absent measurement rather than an
    # invented one, and the REFUSAL lives here, in the function both routes resolve
    # through — `build_i2v_payload.resolve_start_frame` carries this one rather than
    # writing a second.
    if ev["image"] is None:
        with open(path, "rb") as fh:
            head = fh.read(8)
        raise PayloadError(
            f"--start-frame {path!r} is not a PNG this tool can read: its first 8 bytes are "
            f"{head.hex()!r} and no IHDR chunk follows them, so its width, height and "
            f"colour type cannot be measured. On this route the start frame is the entire "
            f"image conditioning, and a record that asserts how the frame FITS the "
            f"generation while carrying no measurement of the file is the claim wave 10 set "
            f"out to replace",
            {"gate": "PAYLOAD", "andon": "start_frame", "clause": "start_frame_not_a_png",
             "flag": "--start-frame", "path": os.path.abspath(path),
             "first_8_bytes": head.hex(), "bytes": ev["bytes"], "sha256": digest,
             "read_by": "IHDR, stdlib struct - no image library"})
    if declared_sha256:
        if declared_sha256.strip().lower() != digest:
            raise PayloadError(
                f"--start-frame-sha256 {declared_sha256!r} does not hash to the file "
                f"{path!r}, which is {digest!r}. One of the two names a different "
                f"artifact, and the record may not carry a digest the bytes do not support",
                dict(base, clause="start_frame_sha256_disagrees",
                     declared_sha256=declared_sha256.strip().lower(), sha256=digest,
                     bytes=ev["bytes"]))
        ev["declared_sha256"] = declared_sha256.strip().lower()
        ev["source"] = "hashed_in_tool_and_confirmed_against_the_declared_value"
    return ev


def ledger_against_wave1(positive, uploads, length, w1_record_path,
                         start_frame_sha256=None, trajectory_overrides=None):
    """Gate LEDGER · ANDON — what still holds is checked; what breaks is named in advance.

    Wave 2's `pin_against_wave1` asserted that the start frame, frame, length and trajectory
    were all identical to wave 1's, and halted on drift. **Wave 3 breaks four of those on
    purpose**, so an unchanged pin would either halt the corrected run or be quietly deleted
    — and quietly deleting a pin is how a confound becomes invisible.

    What replaces it keeps the same andon shape pointed at a different target:

    * everything in `DELIBERATE_BREAKS` must ACTUALLY differ from wave 1. A "corrected" run
      that silently still loaded the I2V experts, or still ran 65 frames, would produce a
      report describing a correction that did not happen — the precise shape of wave 2's own
      failure, one wave later.
    * the sampling trajectory must still MATCH, because it is the one thing this wave holds.
    * the positive must still differ from wave 1's (wave 2's inverted clause, unchanged).

    So the gate raises both when something that should have moved did not, and when the one
    thing that should have held did not.
    """
    with open(w1_record_path, encoding="utf-8") as fh:
        w1 = json.load(fh)
    ev = {"gate": "LEDGER_W3", "andon": "PayloadError",
          "wave_1_record": os.path.abspath(w1_record_path),
          "wave_1_seed": w1.get("seed"),
          "comparison_is": ("ROUTE-LEVEL, not single-variable. Four properties break "
                            "deliberately and are listed below; no number from this run may "
                            "be read as isolating any one lever"),
          "deliberate_breaks": DELIBERATE_BREAKS}
    problems = []

    # ---- the breaks must actually have happened.
    w1_res = w1.get("resolution") or [None, None]
    moved = {
        "length": (length, w1.get("length")),
        "width": (WIDTH, w1_res[0]),
        "height": (HEIGHT, w1_res[1]),
        "unet_high": (UNET_HIGH, (w1.get("models") or {}).get("unet_high_noise")),
        "unet_low": (UNET_LOW, (w1.get("models") or {}).get("unet_low_noise")),
    }
    ev["breaks_verified"] = {k: {"wave_3": a, "wave_1": b, "differs": a != b}
                             for k, (a, b) in moved.items()}
    for key, (ours, theirs) in moved.items():
        if theirs is not None and ours == theirs:
            problems.append(
                f"{key} is still wave 1's ({ours!r}), but this wave's whole purpose is that "
                f"it changed. A report describing a correction that did not happen is wave "
                f"2's failure one wave later")

    if UNET_HIGH == W1.UNET_HIGH or UNET_LOW == W1.UNET_LOW:
        problems.append(
            "the experts are still the plain I2V pair — the pairing Gate PAIR exists to "
            "refuse and the one that produced a clip with no subject")

    # ---- the start frame must be a NEW authored artifact, not wave 1's upload reused.
    ev["start_frame"] = {"wave_3_server_name": uploads.get("start_frame"),
                         "wave_1_server_name": (w1.get("start_image") or {}).get(
                             "server_name"),
                         "wave_3_local_sha256": start_frame_sha256}
    if uploads.get("start_frame") == (w1.get("start_image") or {}).get("server_name"):
        problems.append(
            "the start frame is wave 1's upload, but this wave re-authors it at a new "
            "resolution under the alpha law — the old 832x480 baked-void frame cannot be "
            "the input to a 1024x576 graph")

    # ---- the trajectory: what is HELD must match, what is MOVED must actually have moved.
    #
    # This clause asserted flat equality with wave 1's trajectory, because that was the one
    # property E11 wave 3 held. E12's settings rung is directed to move cfg and sampler_name
    # and hold everything else, so an unchanged clause would halt an authorised wave — and
    # deleting it would be the thing the wave-2 postmortem named: quietly dropping a pin is
    # how a confound becomes invisible. So the andon keeps its shape and changes target,
    # exactly as it did when wave 3 broke four of wave 2's pins: every field NOT named in an
    # override must still equal wave 1's, and every field that IS named must actually differ
    # from it. A break that did not happen fails here.
    overrides = dict(trajectory_overrides or {})
    w1_traj = w1.get("trajectory") or {}
    traj = {k: v["value"] for k, v in effective_trajectory(overrides).items()}
    w1_vals = {k: (v or {}).get("value") for k, v in w1_traj.items()}
    held = {k: v for k, v in traj.items() if k not in overrides}
    w1_held = {k: v for k, v in w1_vals.items() if k not in overrides}
    # ⚠ `held_agrees: held == w1_held` used to sit here, and it could not read False in any
    # record that reaches disk: the very next clause appends a problem on the negation, and
    # this function raises on any problem, so `ev` — and therefore the record — existed only
    # when the comparison was True. A later session reading `meta['gate_LEDGER_W3']` would
    # take it as evidence a comparison was made. The two SIDES are recorded instead; they
    # vary, and a reader can do the comparison the field was standing in for.
    ev["trajectory"] = {
        "this_wave": traj, "wave_1": w1_vals,
        "moved_on_purpose": sorted(overrides),
        "held": sorted(held),
        "held_this_wave": held,
        "held_wave_1": w1_held,
        "role": ("the fields not named in an override are what this wave holds against "
                 "wave 1; the named ones are its lever")}
    if held != w1_held:
        problems.append(
            f"a trajectory field this wave was NOT authorised to move differs from wave "
            f"1's: {held} against {w1_held}. Only {sorted(overrides) or 'nothing'} may "
            f"move, and nothing would be comparable if anything else did")
    for field in overrides:
        if w1_vals.get(field) is None:
            problems.append(f"wave 1's record carries no {field!r} to break against")
        elif traj[field] == w1_vals[field]:
            problems.append(
                f"{field} was declared a deliberate break but still equals wave 1's "
                f"{w1_vals[field]!r} — a report describing a lever that never moved is "
                f"wave 2's failure one wave later")

    # ---- wave 2's inverted clause, unchanged.
    w1_pos = w1.get("positive")
    ev["positive"] = {
        "sha256_wave_3": hashlib.sha256(positive.encode("utf-8")).hexdigest(),
        "sha256_wave_1": (hashlib.sha256(w1_pos.encode("utf-8")).hexdigest()
                          if isinstance(w1_pos, str) else None),
        # `differs` used to sit here and was constant for the same reason `held_agrees`
        # was: the clauses below raise unless wave 1's positive is a str AND differs. The
        # two hashes are already the varying record of that comparison.
        "words_wave_3": word_count(positive),
        "words_wave_1": word_count(w1_pos) if isinstance(w1_pos, str) else None,
        "note": ("the prompt surgery rides UNCHANGED from wave 2 — it has never been "
                 "tested, because wave 2's frames had no subject to judge it on"),
    }
    if not isinstance(w1_pos, str):
        problems.append("wave 1's record carries no positive string to check against")
    elif w1_pos == positive:
        problems.append(
            "the positive built here is byte-identical to wave 1's, so the prompt surgery "
            "did not happen and the run would measure the weight swap alone while the "
            "report described two levers")

    if problems:
        # The evidence rides the HALT, not only the pass. It was built, filled, and then
        # dropped on the floor here, so the failing measurement — the interesting one —
        # reached no record at all.
        ev["clause"] = "payload_is_not_the_ruling_it_describes"
        ev["problems"] = problems
        raise PayloadError("wave 3's payload is not the one the ruling describes: "
                           + "; ".join(problems),
                           ev)
    moved = sorted(overrides)
    ev["verdict"] = (
        f"{len(DELIBERATE_BREAKS)} deliberate breaks verified as actual; "
        + (f"trajectory moved on {', '.join(moved)} and held on {len(held)} other field(s)"
           if moved else "trajectory held")
        + "; positive still differs from wave 1's")
    return ev


#: Which trajectory fields a wave is allowed to move. Everything else in `W1.TRAJECTORY` is
#: structural to the two-expert split (steps, split_step, shift, scheduler, fps) and moving
#: one would make the wave incomparable rather than informative.
OVERRIDABLE = ("cfg", "sampler_name")


def effective_trajectory(overrides=None):
    """`W1.TRAJECTORY` with named fields replaced, each replacement carrying its own source.

    The trajectory is IMPORTED rather than retyped precisely so that "held constant" is a
    property of the code. A wave that moves part of it must therefore move it through one
    named door, with the old value and the reason preserved beside the new one — otherwise
    the record shows a number with no history and the next reader cannot tell a measured
    correction from a typo.
    """
    out = {k: dict(v) for k, v in W1.TRAJECTORY.items()}
    for field, spec in (overrides or {}).items():
        if field not in out:
            raise PayloadError(
                f"{field!r} is not a trajectory field; the trajectory is "
                f"{sorted(out)}",
                {"gate": "PAYLOAD", "andon": "PayloadError",
                 "clause": "override_names_no_trajectory_field",
                 "field": field, "trajectory_fields": sorted(out)})
        if field not in OVERRIDABLE:
            raise PayloadError(
                f"{field!r} is structural to the two-expert split and is not overridable "
                f"here. Moving it would make the wave incomparable rather than informative; "
                f"overridable fields are {list(OVERRIDABLE)}",
                {"gate": "PAYLOAD", "andon": "PayloadError",
                 "clause": "override_field_is_structural",
                 "field": field, "overridable": list(OVERRIDABLE)})
        was = out[field]["value"]
        if spec["value"] == was:
            raise PayloadError(
                f"the override for {field!r} sets it to {was!r}, which is what it already "
                f"was. A break that did not happen is wave 2's failure shape: the report "
                f"would describe a lever that never moved",
                {"gate": "PAYLOAD", "andon": "PayloadError",
                 "clause": "override_does_not_move_the_field",
                 "field": field, "value": was})
        out[field] = {"value": spec["value"], "source": spec["source"],
                      "was": was, "moved_by": "an explicit override on this wave"}
    return out


def build(uploads, seed, negative, positive, registry, experiment=EXPERIMENT,
          length=LENGTH, fps=FPS, wave=WAVE, trajectory_overrides=None,
          start_frame=None):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists.

    `wave` is a parameter and not the module constant for the reason this repo has now paid
    for twice: a tool that names an experiment in a literal is a tool that will lie the first
    time it is reused. Reused at E12, `WAVE = 3` would have written `E12-w3-…` filenames, a
    `"wave": 3` field, and cloud output prefixes under `E12/w3/` — every one of them a
    plausible label pointing at the wrong run.
    """
    # ---- ANDON, wave 12 (F-d979ec52), the sibling's clause carried verbatim in shape.
    # `start_image` used to be `{"server_name": …, "fit": "native — authored at 832x480,
    # the same upload wave 1 ran"}` — prose about wave 1's resolution inside a record whose
    # own DELIBERATE_BREAKS says this wave generates at 1024x576. The measurement that
    # settles it was already computed by `resolve_start_frame` in `main` and reached only
    # `gate_LEDGER_W3`. It is a parameter of the graph builder now, and required here rather
    # than in `main` so an in-process caller cannot route around it.
    if not start_frame or not start_frame.get("sha256"):
        raise PayloadError(
            "build() needs the resolved start frame: on this route the start image is the "
            "whole of the conditioning, and `meta['start_image']` used to identify it only "
            "by a server-side content-addressed name beside a `fit` sentence nothing "
            "checked. Call `resolve_start_frame(path, declared)` and pass its evidence",
            {"gate": "PAYLOAD", "andon": "start_frame",
             "clause": "start_frame_was_not_resolved", "flag": "--start-frame",
             "start_frame": start_frame})
    if not start_frame.get("image"):
        raise PayloadError(
            "the resolved start frame carries no measurement of its own pixels: "
            "`fit_agrees_with_the_file` would be null on exactly the input the comparison "
            "exists for. Resolve it through `resolve_start_frame`, which reads the file's "
            "IHDR and refuses a file it cannot read",
            {"gate": "PAYLOAD", "andon": "start_frame", "clause": "start_frame_unmeasured",
             "flag": "--start-frame", "start_frame": start_frame})
    # ---- Gate ROUTE - ANDON on `CreateVideo.fps` (wave 10, F-29693a0e, family carry).
    # `--fps` reached the node with no clause in all five builders that take the flag,
    # while every one of their records states the node's measured contract as
    # "fps FLOAT (1-120)". One implementation, in `build_assembly_payload`, imported here.
    gate_create_video_fps(fps)
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
    # `wan-fun-camera`, not `wan-i2v`: the route runs the camera weights, so it reads its
    # legality constraints from the camera model's own row. Wave 2 is the argument.
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-fun-camera")

    traj = effective_trajectory(trajectory_overrides)
    steps = traj["steps"]["value"]
    split = traj["split_step"]["value"]
    shift = traj["shift"]["value"]
    cfg = traj["cfg"]["value"]
    sampler = traj["sampler_name"]["value"]
    scheduler = traj["scheduler"]["value"]

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
        "40": {"class_type": "LoadImage", "inputs": {"image": start_name}},
        # Gate B probe: the start frame as the conditioning node receives it, saved so it can
        # be compared pixel for pixel against the local render.
        "41": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": f"{experiment}/w{wave}/startprobe",
                          "images": ["40", 0]}},
        # THE CAMERA LEVER. Its width/height/length must equal the generated frame's —
        # route_gates.CAMERA_NODES puts an andon on exactly that, because this node's own
        # default length is 81 and this route runs 65.
        "45": {"class_type": "WanCameraEmbedding", "inputs": {
            "camera_pose": CAMERA_POSE, "width": WIDTH, "height": HEIGHT, "length": length,
            "speed": CAMERA_SPEED, **CAMERA_INTRINSICS}},
        "50": {"class_type": "WanCameraImageToVideo", "inputs": {
            "width": WIDTH, "height": HEIGHT, "length": length, "batch_size": 1,
            "positive": ["30", 0], "negative": ["31", 0], "vae": ["21", 0],
            "start_image": ["40", 0],
            "camera_conditions": ["45", 0],
            # clip_vision_output stays absent, as in wave 1: a second image-conditioning
            # channel would make the identity read unattributable between the start frame
            # and the embedding.
        }},
        "60": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": seed_used, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": 0, "end_at_step": split,
            "return_with_leftover_noise": "enable",
            "model": ["12", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["50", 2]}},
        "61": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "disable", "noise_seed": 0, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": split, "end_at_step": 10000,
            "return_with_leftover_noise": "disable",
            "model": ["13", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["60", 0]}},
        "70": {"class_type": "VAEDecode",
               "inputs": {"samples": ["61", 0], "vae": ["21", 0]}},
        # The lossless tap — every measurement reads these, before any codec.
        "71": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"{experiment}/w{wave}/lossless", "images": ["70", 0]}},
        "80": {"class_type": "CreateVideo",
               "inputs": {"fps": fps, "bit_depth": 8, "images": ["70", 0]}},
        "81": {"class_type": "SaveVideo", "inputs": {
            "filename_prefix": f"video/{experiment}_w{wave}", "format": "auto",
            "codec": "auto", "video": ["80", 0]}},
    }

    verify_topology(wf, start_name)

    gate_route = route_gates.verify(wf, frame=(WIDTH, HEIGHT, length))

    meta = {
        "experiment": experiment, "wave": wave, "tool_version": TOOL_VERSION,
        "route": ("the model performs; the camera is held — a start frame from the GLB, a "
                  "prompt, and a Static camera embedding. No signal drives the performer"),
        "route_name_change": {
            "wave_1": "no control of any kind",
            "wave_2": "no control over the PERFORMER; the camera is held",
            "why_it_matters": (
                "wave 1's builder bans WanCameraImageToVideo outright and that ban is left "
                "standing on the run it governed. Wave 2 draws the line differently and "
                "says so; a report calling this the no-control route without the qualifier "
                "would be describing wave 1"),
        },
        "resolution": [WIDTH, HEIGHT], "length": length, "fps": fps,
        "seed": seed_used,
        "gate_S": gate_s,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "gate_ROUTE_built": gate_route,
        "models": {"unet_high_noise": UNET_HIGH, "unet_low_noise": UNET_LOW,
                   "clip": CLIP_NAME, "vae": VAE_NAME, "loras": []},
        "frame_derivation": FRAME_DERIVATION,
        "trajectory": traj,
        "trajectory_overrides": dict(trajectory_overrides or {}),
        "trajectory_source": ("IMPORTED from build_i2v_payload, not retyped — the sampling "
                              "trajectory is the one thing this wave holds against waves "
                              "1-2, so it is held by the code rather than by a claim"),
        "trajectory_premise": {
            "status": "ASSUMED — marked, not measured",
            "claim": ("the trajectory read off the official I2V reference workflow (steps "
                      "20, split 10, shift 8.0, cfg 3.5, euler, simple) transfers to the "
                      "Fun-Camera derivative"),
            "why_it_is_plausible": ("Fun-Camera is a derivative of Wan2.2-I2V-A14B and the "
                                    "same A14B two-expert MoE architecture, so the high/low "
                                    "split and shift are architectural properties it shares"),
            "the_divergence_recorded": ("the Comfy catalog's `recommended` block for these "
                                        "exact fun_camera files says steps 20, cfg 6.0, "
                                        "sampler uni_pc, scheduler simple — cfg and sampler "
                                        "BOTH differ from what this graph runs"),
            "why_it_was_not_changed": ("this wave already moves weights, length, resolution "
                                       "and the start frame. Changing cfg and the sampler "
                                       "too would leave nothing held at all. It is marked "
                                       "here as the first named candidate if the run "
                                       "disappoints — not silently adopted, not silently "
                                       "ignored"),
        },
        "camera": {
            "node": "WanCameraEmbedding -> WanCameraImageToVideo.camera_conditions",
            "camera_pose": CAMERA_POSE, "speed": CAMERA_SPEED,
            "intrinsics": dict(CAMERA_INTRINSICS),
            "frame": [WIDTH, HEIGHT, length],
            "schema_source": "get_node, fetched 2026-08-12; no served template wires this "
                             "tier, so nothing was read off one",
            "defaults_left_alone": ("speed and the four intrinsics are the node's declared "
                                    "defaults; this wave changes the camera from free to "
                                    "held and moving an intrinsic would be a third lever"),
            "what_it_replaces": ("wave 1's positive ended 'The camera is static.' and the "
                                 "camera pushed in regardless — horizon on 4 of 65 frames"),
        },
        "positive": positive,
        "negative": negative,
        # ONE implementation of this block, in the sibling (see `W1.start_image_record`).
        # `fit` names THIS wave's own resolution, and the boolean beside it is the file's
        # own IHDR compared against the frame the graph generates.
        "start_image": W1.start_image_record(
            start_frame, start_name, WIDTH, HEIGHT,
            # DELIBERATE_BREAKS["start_frame_pixels"] states this wave's artifact in words:
            # "authored RGBA, submitted composite over a named colour recorded in the render
            # provenance". `--start-frame` names the file that is UPLOADED, so the
            # declaration is the composite (wave 16, F-71ffdbfb).
            declares_alpha=False,
            fit=(f"native — authored at {WIDTH}x{HEIGHT}, this wave's own frame; wave 1 "
                 f"ran 832x480 and DELIBERATE_BREAKS['resolution'] is the ruling that "
                 f"moved it"),
            why=("the start frame is re-authored for this wave: the resolution changed and "
                 "the alpha law (the Director's ruling 2026-08-12) governs the artifact, so "
                 "nothing here is wave 1's upload")),
        "unconnected_inputs": {
            "clip_vision_output": "unconnected, as in wave 1",
        },
        "no_performer_control": (
            "checked in code by verify_topology: no pose sticks, no reference image, no "
            "control video, no clip-vision path, and no second uploaded image outside the "
            "Gate B probe. The camera embedding is present BY DESIGN and steers the camera "
            "only"),
        # Wave 20, F-dba1bcd8: through the ONE shared derivation, not a copy
        # of the expression. Four builders each carried their own spelling of it
        # and `route_facts` carried a fifth, five places for the digest the gate
        # compares against to drift from the digest a record declares.
        "payload_sha256": canonical_payload_digest(wf),
    }
    disc = comfy_cloud_oss_disclosure(
        route_verdict=(meta.get("gate_ROUTE_built") or {}).get("verdict"))
    meta["disclosure"] = disc
    meta.update(fetch_recipe(
        node_map={"41": "startprobe", "71": "lossless"}, video_nodes=("81",),
        root_hint="outputs/E11/runs",
        taps=[{"node": "41", "class_type": "SaveImage", "subdir": "startprobe"},
              {"node": "71", "class_type": "SaveImage", "subdir": "lossless"},
              {"node": "81", "class_type": "SaveVideo", "subdir": None}]))
    return wf, meta


#: Conditioning classes that can drive the PERFORMER. `WanCameraImageToVideo` is deliberately
#: NOT here — see the module docstring. Everything that could supply a pose, a reference
#: identity, or a driving video is, and presence is presence: an unfed control node is one
#: edit from being fed.
PERFORMER_CONTROL_CLASSES = ("WanVaceToVideo", "WanAnimateToVideo", "Wan22FunControlToVideo",
                             "WanFunControlToVideo", "WanFirstLastFrameToVideo",
                             "WanPhantomSubjectToVideo", "ControlNetApply",
                             "ControlNetApplyAdvanced", "ControlNetApplySD3",
                             "ACN_AdvancedControlNetApply")


def verify_topology(wf, start_name):
    """Link topology, checked in code. A `dry_run` PASS does not prove link sanity."""
    problems = []

    node = wf.get("50")
    if not node or node["class_type"] != "WanCameraImageToVideo":
        problems.append("node 50 is not the WanCameraImageToVideo conditioning node")
    else:
        inp = node["inputs"]
        if inp.get("start_image") != ["40", 0]:
            problems.append("start_image is not fed by the start-frame LoadImage")
        if inp.get("camera_conditions") != ["45", 0]:
            problems.append(
                "camera_conditions is not fed by the WanCameraEmbedding. The socket is "
                "OPTIONAL on this node, so an unwired camera generates video exactly like "
                "wave 1 and every gate passes — this wave's whole lever would be absent "
                "from the run and present in the report")
        if "clip_vision_output" in inp:
            problems.append("clip_vision_output is connected; wave 2's record says it is not")

    cam = wf.get("45")
    if not cam or cam["class_type"] != "WanCameraEmbedding":
        problems.append("node 45 is not the WanCameraEmbedding")
    else:
        if cam["inputs"].get("camera_pose") != CAMERA_POSE:
            problems.append(
                f"the camera pose is {cam['inputs'].get('camera_pose')!r}, not "
                f"{CAMERA_POSE!r}; this wave holds the camera rather than moving it")

    for nid, n in wf.items():
        if n["class_type"] in PERFORMER_CONTROL_CLASSES:
            problems.append(
                f"node {nid} is {n['class_type']}, a conditioning class that can drive the "
                f"performer. Wave 2 frees the performance and holds only the camera; a "
                f"graph with one of these answers a different question")
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
                f"conditioning; text encodes wired straight to a sampler would drop both "
                f"the start image AND the camera embedding and still generate a video")
    if hi.get("add_noise") != "enable" or lo.get("add_noise") != "disable":
        problems.append("the two-expert split's add_noise pair is not enable then disable")
    if hi.get("end_at_step") != lo.get("start_at_step"):
        problems.append(
            f"the experts do not hand over at the same step: high ends at "
            f"{hi.get('end_at_step')} and low starts at {lo.get('start_at_step')}")

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
        raise PayloadError(
            "the built graph is not the graph the spec describes: " + "; ".join(problems),
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "built_graph_is_not_the_spec_graph", "problems": problems})
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
                        extra={"pasted_into": ["<out>/{experiment}-w{wave}-camera-i2v.api.json",
                                        "<out>/{experiment}-w{wave}-payload-record.json",
                                        "the server-side filename prefixes"]})
    out = os.path.abspath(a.out)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    if "start_frame" not in uploads:
        raise PayloadError(
            f"{a.uploads} carries no `start_frame` upload name",
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "uploads_carry_no_start_frame", "flag": "--uploads",
             "path": os.path.abspath(a.uploads)})

    registry = None
    if a.seeds_registry:
        # ONE reader, eight callers (wave 16, F-0682bd00). The bare `json.load(fh)["seeds"]`
        # this replaces raised a stdlib KeyError naming a key and nothing else on a
        # registration with no `seeds` key.
        registry = read_seed_registration(a.seeds_registry, flag="--seeds-registry")

    if not a.negative_source:
        raise PayloadError(
            "--negative-source is required: Wan's sample_neg_prompt is READ from the banked "
            "config, never retyped. E09's citation check fired on this string",
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "negative_source_not_supplied", "flag": "--negative-source"})

    positive, prompt_log = build_prompt()
    # The SHIPPED positive is what the router checks; `--canon-prompt` is compared
    # against it rather than substituted for it.
    canon_ev = canon_spend(a.subject, positive, no_canon=a.no_canon, out_dir=out,
                           canon_prompt=a.canon_prompt)
    negative, negative_log = build_negative(a.negative_source)
    overrides = {}
    if a.cfg is not None:
        overrides["cfg"] = {"value": a.cfg, "source": a.trajectory_source or
                            "an explicit --cfg override on this wave"}
    if a.sampler is not None:
        overrides["sampler_name"] = {"value": a.sampler, "source": a.trajectory_source or
                                     "an explicit --sampler override on this wave"}

    # The control input is hashed from the artifact before anything else is built.
    start_frame = resolve_start_frame(a.start_frame, a.start_frame_sha256)
    gate_ledger = ledger_against_wave1(positive, uploads, a.length, a.w1_record,
                                       start_frame_sha256=start_frame["sha256"],
                                       trajectory_overrides=overrides)
    gate_ledger["start_frame"]["wave_3_local"] = start_frame

    wf, meta = build(uploads, a.seed, negative, positive, registry,
                     experiment=a.experiment, length=a.length, fps=a.fps, wave=a.wave,
                     trajectory_overrides=overrides, start_frame=start_frame)
    meta["gate_LEDGER_W3"] = gate_ledger
    meta["gate_CANON"] = canon_ev
    meta["prompt_record"] = {
        "surgery": prompt_log,
        "negative": negative_log,
        "guidance": PROMPT_GUIDANCE,
        "rebuilt_through": ("build_animate_payload.identity_clause / read_negative — the "
                            "same code wave 1 and E08 read them through"),
    }

    gpath = os.path.join(out, f"{a.experiment}-w{a.wave}-camera-i2v.api.json")
    mpath = os.path.join(out, f"{a.experiment}-w{a.wave}-payload-record.json")
    # Wave 35, F-0bd5c9c9: same overwrite shape as assembly/cascade.
    gate_overwrite = gate_output_not_overwritten(
        [gpath, mpath], out, a.overwrite, PayloadError, gate="PAYLOAD")
    meta["gates"] = dict(meta.get("gates") or {})
    meta["gates"]["PAYLOAD_overwrite"] = gate_overwrite
    meta["out_dir_pre_existed"] = gate_overwrite["out_dir_pre_existed"]
    meta["overwrote"] = gate_overwrite["overwrote"]
    os.makedirs(out, exist_ok=True)
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(canon_line(canon_ev))
    for line in disclosure_lines(meta["disclosure"]):
        print(line)
    print("BUILD_CAMERA_I2V_OK " + json.dumps({"path": gpath, 
        "graph": gpath, "record": mpath, "nodes": len(wf), "seed": meta["seed"],
        "resolution": meta["resolution"], "length": meta["length"], "fps": meta["fps"],
        "camera_pose": CAMERA_POSE, "experts": [UNET_HIGH, UNET_LOW],
        "payload_sha256": meta["payload_sha256"][:32],
        "prompt_dominance": prompt_log["dominance"]["ratio"],
        "gate_LEDGER_W3": gate_ledger["verdict"],
        "gate_PAIR": meta["gate_ROUTE_built"]["pairing"]["verdict"],
        "gate_L": meta["gate_L"]["verdict"], "gate_S": meta["gate_S"].get("verdict"),
        "gate_ROUTE_built": meta["gate_ROUTE_built"]["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `BUILD_CAMERA_I2V_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "BUILD_CAMERA_I2V")

