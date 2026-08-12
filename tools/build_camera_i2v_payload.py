#!/usr/bin/env python
r"""build_camera_i2v_payload — E11's camera-held graph, built in this repo.

    python tools\build_camera_i2v_payload.py --uploads=<uploads.json> --out=<dir>
           --negative-source=<wan22_shared_config.py> --seeds-registry=specs\E11-seeds.json
           --w1-record=<E11-probe-payload-record.json> [--seed=2026081233]

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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

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
    """The payload could not be built as specified."""


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True, help="JSON: {start_frame: <server name>}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--negative-source", default=None,
                    help="path to Wan's shared_config.py; the base negative is READ from it "
                         "rather than retyped, then extended")
    ap.add_argument("--w1-record", required=True,
                    help="wave 1's committed payload record. The trajectory is pinned "
                         "against it, the four DELIBERATE_BREAKS are required to have "
                         "actually happened, and the positive is required to DIFFER")
    ap.add_argument("--start-frame-sha256", default=None,
                    help="the local sha256 of the re-authored start frame, into the record")
    ap.add_argument("--seeds-registry", default=None)
    ap.add_argument("--experiment", default=EXPERIMENT)
    ap.add_argument("--length", type=int, default=LENGTH,
                    help="frame count (argparse eats leading minus signs, so pass flags "
                         "as --flag=value)")
    ap.add_argument("--fps", type=float, default=FPS)
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
            f"alone while the report described two")

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


def ledger_against_wave1(positive, uploads, length, w1_record_path,
                         start_frame_sha256=None):
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
    ev = {"gate": "LEDGER_W3", "wave_1_record": os.path.abspath(w1_record_path),
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

    # ---- the one thing that must still hold.
    w1_traj = w1.get("trajectory") or {}
    traj = {k: v["value"] for k, v in W1.TRAJECTORY.items()}
    w1_vals = {k: (v or {}).get("value") for k, v in w1_traj.items()}
    ev["trajectory"] = {"wave_3": traj, "wave_1": w1_vals, "agrees": traj == w1_vals,
                        "role": "the only property this wave holds against wave 1"}
    if traj != w1_vals:
        problems.append(f"the sampling trajectory differs from wave 1's: {traj} against "
                        f"{w1_vals} — it is the one thing this wave holds, and nothing "
                        f"would be comparable if it moved too")

    # ---- wave 2's inverted clause, unchanged.
    w1_pos = w1.get("positive")
    ev["positive"] = {
        "sha256_wave_3": hashlib.sha256(positive.encode("utf-8")).hexdigest(),
        "sha256_wave_1": (hashlib.sha256(w1_pos.encode("utf-8")).hexdigest()
                          if isinstance(w1_pos, str) else None),
        "differs": isinstance(w1_pos, str) and w1_pos != positive,
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
        raise PayloadError("wave 3's payload is not the one the ruling describes: "
                           + "; ".join(problems))
    ev["verdict"] = (f"{len(DELIBERATE_BREAKS)} deliberate breaks verified as actual; "
                     f"trajectory held; positive still differs from wave 1's")
    return ev


def build(uploads, seed, negative, positive, registry, experiment=EXPERIMENT,
          length=LENGTH, fps=FPS):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists."""
    gate_s = gates.gate_s_seed_registration(seed, registry, experiment,
                                            seed_was_explicit=seed is not None)
    seed_used = seed if seed is not None else (sorted(registry)[0] if registry else 0)
    # `wan-fun-camera`, not `wan-i2v`: the route runs the camera weights, so it reads its
    # legality constraints from the camera model's own row. Wave 2 is the argument.
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-fun-camera")

    steps = W1.TRAJECTORY["steps"]["value"]
    split = W1.TRAJECTORY["split_step"]["value"]
    shift = W1.TRAJECTORY["shift"]["value"]
    cfg = W1.TRAJECTORY["cfg"]["value"]
    sampler = W1.TRAJECTORY["sampler_name"]["value"]
    scheduler = W1.TRAJECTORY["scheduler"]["value"]

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
               "inputs": {"filename_prefix": f"{experiment}/w{WAVE}/startprobe",
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
            "filename_prefix": f"{experiment}/w{WAVE}/lossless", "images": ["70", 0]}},
        "80": {"class_type": "CreateVideo",
               "inputs": {"fps": fps, "bit_depth": 8, "images": ["70", 0]}},
        "81": {"class_type": "SaveVideo", "inputs": {
            "filename_prefix": f"video/{experiment}_w{WAVE}", "format": "auto",
            "codec": "auto", "video": ["80", 0]}},
    }

    verify_topology(wf, start_name)

    gate_route = route_gates.verify(wf, frame=(WIDTH, HEIGHT, length))

    meta = {
        "experiment": experiment, "wave": WAVE, "tool_version": TOOL_VERSION,
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
        "trajectory": W1.TRAJECTORY,
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
        "start_image": {"server_name": start_name,
                        "fit": "native — authored at 832x480, the same upload wave 1 ran"},
        "unconnected_inputs": {
            "clip_vision_output": "unconnected, as in wave 1",
        },
        "no_performer_control": (
            "checked in code by verify_topology: no pose sticks, no reference image, no "
            "control video, no clip-vision path, and no second uploaded image outside the "
            "Gate B probe. The camera embedding is present BY DESIGN and steers the camera "
            "only"),
        "payload_sha256": hashlib.sha256(
            json.dumps(wf, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
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
        raise PayloadError("the built graph is not the graph the spec describes: "
                           + "; ".join(problems))
    return True


def main(argv=None):
    a = parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

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
            "--negative-source is required: Wan's sample_neg_prompt is READ from the banked "
            "config, never retyped. E09's citation check fired on this string")

    positive, prompt_log = build_prompt()
    negative, negative_log = build_negative(a.negative_source)
    gate_ledger = ledger_against_wave1(positive, uploads, a.length, a.w1_record,
                                       start_frame_sha256=a.start_frame_sha256)

    wf, meta = build(uploads, a.seed, negative, positive, registry,
                     experiment=a.experiment, length=a.length, fps=a.fps)
    meta["gate_LEDGER_W3"] = gate_ledger
    meta["prompt_record"] = {
        "surgery": prompt_log,
        "negative": negative_log,
        "guidance": PROMPT_GUIDANCE,
        "rebuilt_through": ("build_animate_payload.identity_clause / read_negative — the "
                            "same code wave 1 and E08 read them through"),
    }

    gpath = os.path.join(out, f"{a.experiment}-w{WAVE}-camera-i2v.api.json")
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    mpath = os.path.join(out, f"{a.experiment}-w{WAVE}-payload-record.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print("BUILD_CAMERA_I2V_OK " + json.dumps({
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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_CAMERA_I2V_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
