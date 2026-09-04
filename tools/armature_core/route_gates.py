"""Read a workflow graph and answer, in code, whether it can carry an experiment.

No bpy, no network, no numpy — it parses JSON and reports. Written because
`docs/license-map.md` and CLAUDE.md both say the same thing in different words:

> A `dry_run` PASS does not prove link sanity. Submit saved workflow files verbatim and
> check link topology in code before submission.

and the check was being done by eye. Three questions get asked of every graph before a
credit is spent, and each is a question a served template can silently answer wrong:

* **which weights does it actually load** — the licence gate's population. A template's
  title says nothing about the LoRA wired inside its subgraph, and the map's own ruling is
  that a *bypassed* non-commercial node still counts as present. So the answer comes from
  the node list, not from the name.
* **is every seed pinned** — Gate S. A `KSamplerAdvanced` whose `control_after_generate`
  reads `randomize` produces a run whose seed no committed list pre-registered, and E04's
  andon exists because a seed chosen after seeing a result turns a measurement of the
  between-generation floor into a selection of it.
* **is the frame generator-legal** — Gate L, derive-then-round. Every video model
  constrains resolution and frame count; the constraint is recorded per model here rather
  than remembered per session.

Nothing here spends anything, and nothing here is a matter of taste. It reports what the
graph contains; the rulings about what may run are the Director's and the advisor's.
"""

import json

from .canon import GRAPH_WRAPPER_KEYS
from .errors import GateFailure

TOOL_VERSION = "E09.1"

#: The wrapper keys `normalise_graph` (and therefore every gate here, and `load_graph`)
#: unwraps, published under this module's own name so a caller outside the package reads
#: the SAME list the loader uses instead of re-typing a subset of it. It is
#: `canon.GRAPH_WRAPPER_KEYS` — one tuple, two names, no second implementation.
WRAPPER_KEYS = GRAPH_WRAPPER_KEYS

#: Generator constraints, per model family, from the spec that first used each. Wan's are
#: the ones E02 and E08 measured: both dimensions divisible by 16, frame count of the form
#: 4n+1, and a trained horizon of 81 frames beyond which the model was never trained.
GENERATOR_RULES = {
    "wan": {"dim_multiple": 16, "frame_form": "4n+1", "max_frames": 81},
}

#: Components the repo has already ruled on, keyed by a substring of the file name. This is
#: a MIRROR of `docs/license-map.md`, not a second authority: the map is the record and
#: this is what lets a script fail on it. A component absent from this table is UNKNOWN,
#: which is reported, never silently treated as clean.
RULED_COMPONENTS = {
    "lightx2v": {
        "verdict": "EXCLUDED",
        "licence": "Apache-2.0 — commercially clean",
        "reason": ("excluded on METHODOLOGY grounds by the licence map, not on licence "
                   "grounds: a 4-step / cfg-1 distilled trajectory is a different sampler "
                   "trajectory from the one every other arm is measured on"),
    },
    "causvid": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC",
        "reason": "non-commercial; the map's ruling is delete, not bypass",
    },
    "openpose": {"verdict": "BANNED", "licence": "CMU Academic / Non-Commercial",
                 "reason": "non-commercial preprocessor tier"},
    "dwpose": {"verdict": "BANNED", "licence": "weights not fetched",
               "reason": "UNVERIFIED weights tier — treated as NO"},

    # ---- the E14 style-LoRA field, mirrored from the licence map's 2026-08-13 fetch pass.
    # Four of these are kills. They are entered BECAUSE they are dead: an absent row reads
    # "NOT IN THIS TABLE", which is a shrug, and the point of a mirror is that naming a
    # gate-dead file in a graph halts instead of shrugging.
    "technically_color": {
        "verdict": "ALLOWED",
        "licence": "CivitAI grant matrix ['RentCivit', 'Rent', 'Image'], allowNoCredit false",
        "reason": ("E14 arm T. Third-party-service use and image-commercial both granted. "
                   "⚠ CREDIT REQUIRED: published footage from this LoRA credits renderartist. "
                   "The page's 'Apache 2.0' badge is the BASE MODEL's, not this file's — "
                   "reading it as the grant is a mistake this map made and corrected"),
    },
    "smartphonesnapshot": {
        "verdict": "ALLOWED",
        "licence": ("CivitAI grant matrix ['Image', 'RentCivit', 'Rent', 'Sell'], "
                    "allowNoCredit true, allowDerivatives true"),
        "reason": ("E14 arm S — the most permissive grant in the field. Served as a "
                   "tier-labelled HIGH/LOW pair; the HIGH file's doubled .safetensors "
                   "suffix is a Cloud provisioning artifact and is part of its served name"),
    },
    "candid_photography": {
        "verdict": "BANNED",
        "licence": "CivitAI grant matrix ['RentCivit'] ONLY",
        "reason": ("withdrawn from E14 before it ran. No image-commercial right and no "
                   "third-party-service right — both rights this route needs are withheld. "
                   "Its first YES was read off the base model's Apache badge"),
    },
    "80s_fantasy": {
        "verdict": "BANNED",
        "licence": "CivitAI grant matrix ['RentCivit', 'Image'], allowDerivatives false",
        "reason": ("image-commercial granted but 'Rent' — third-party generation-service "
                   "use — is WITHHELD, and generation through Comfy Cloud is exactly that "
                   "use. Revival would take the creator's grant, not a re-fetch"),
    },
    "instareal": {
        "verdict": "BANNED",
        "licence": "Instara Fair Use License",
        "reason": ("prohibits use on any image/video generation service, platform or API; "
                   "this route IS that use. `instagirl` is the same house and inherits it"),
    },
    "instagirl": {
        "verdict": "BANNED",
        "licence": "Instara Fair Use License (same house as instareal)",
        "reason": "inherits the instareal row's verdict per the licence map",
    },
    "vintage_film_grain": {
        "verdict": "BANNED",
        "licence": "source unlocated — NOT RETRIEVED",
        "reason": ("a licence that cannot be retrieved is treated as NO. Revivable only if "
                   "a source page is found and fetched"),
    },
}

#: Node classes that carry a seed, and where it lives in `widgets_values`.
#:
#: `add_noise` is the third entry and it is per-class rather than assumed: `KSamplerAdvanced`
#: carries the switch as its first widget, and **`KSampler` has no such input at all** — it
#: always adds noise. Reading widget 0 for both (which this table let a caller do until
#: 2026-08-12) asks a `KSampler` whether its SEED equals "disable"; the answer is right for
#: the wrong reason on every graph, and would be wrong outright on a class whose first
#: widget happened to be a disabling literal.
#: ⚠ **A class absent from this table disarms Gate S silently.** E13's halt-era executor
#: measured exactly that and refused to record it as a pass: on a `wan2.7-r2v` graph
#: `seeds()` returned empty and `gate_s_registration` reported "0 noise-bearing seed(s),
#: all pinned" — a green verdict having checked nothing. The halt ruling (R6) ruled the
#: refusal correct and owed the row to **the first spec that arms this tier**, which is
#: E13's re-arm.
#:
#: `Wan2ReferenceVideoApi` is a hosted partner node, not a sampler: it carries no
#: `add_noise` input at all, so that entry is `None` for the same reason `KSampler`'s is.
#: Its save-format widget indices are **READ OFF the file the cloud converted**, 2026-08-13,
#: not derived — the standard the camera rows were held to. Both readings (the `get_node`
#: declaration order, and the converted file's own `widgets_values`) are recorded in the
#: E13 run report and required to agree.
SEED_NODES = {
    "KSampler": {"seed": 0, "control": 1, "add_noise": None},
    "KSamplerAdvanced": {"seed": 1, "control": 2, "add_noise": 0},
    "Wan2ReferenceVideoApi": {"seed": 6, "control": 7, "add_noise": None},
}

#: What a *hosted* tier constrains, where a local generator constrains pixels.
#:
#: ⚠ Gate L's `wan` rules describe a dim multiple of 16 and a 4n+1 frame count. **They do
#: not describe this tier at all** — `wan2.7-r2v` takes a resolution enum, a ratio enum and
#: an integer duration in seconds, and never receives a pixel dimension from us. Running the
#: pixel rules against it was the second vacuous gate the E13 halt report recorded, and the
#: halt ruling owed this table to the first spec that arms the tier. A check that cannot
#: fail is not a check.
HOSTED_TIER_RULES = {
    "wan2.7-r2v": {
        "resolutions": ("720P", "1080P"),
        "ratios": ("16:9", "9:16", "1:1", "4:3", "3:4"),
        "duration_s": (2, 10),
        "measured": ("get_node('Wan2ReferenceVideoApi'), 2026-08-12, re-measured "
                     "byte-consistent 2026-08-13"),
    },
}

#: Node classes that size a video latent, and where width/height/length live in save
#: format's positional `widgets_values`.
#:
#: ⚠ **A conditioning node can size a latent too, and forgetting that disarms Gate L
#: silently.** Added 2026-08-12 (E08): `WanAnimateToVideo` emits its own zeroed latent from
#: its own width/height/length inputs, so an Animate graph contains no `Empty*LatentVideo`
#: node at all — and this table drove `latents()`, which drove `frame_legality()`. On the
#: first E08 graph Gate L therefore examined ZERO latents and reported the graph legal
#: without checking anything, which is the failure mode CLAUDE.md names outright: a check
#: that cannot fail is not a check. Any future conditioning node that sizes a latent belongs
#: here the day it is first used.
#:
#: ⚠ **Adding a class to this table fixes one graph; it does not fix the shape of that
#: failure.** The next unrecorded latent-sizing node would disarm Gate L exactly the same
#: way, and this table can only ever be complete about nodes somebody already met. So the
#: gate no longer trusts the table to be complete: `verify` distinguishes "nothing was
#: checkable" from "everything checked out" and raises on the first (E08 closing ruling's
#: commission, shipped E10 2026-08-12).
#:
#: Widget order for `WanAnimateToVideo` is read from its `define_schema` declaration order,
#: keeping only the non-link inputs: width, height, length, batch_size,
#: continue_motion_max_frames, video_frame_offset.
#:
#: `WanImageToVideo` and `WanFirstLastFrameToVideo` were added 2026-08-12 (E11) under the
#: warning above — the day the first of them was used, not the day one of them broke
#: something. Both size their own latent from their own width/height/length exactly as
#: `WanAnimateToVideo` does, so an I2V graph likewise contains no `Empty*LatentVideo` node
#: at all. Widget order measured two ways and required to agree: `get_node`'s
#: `input_details` order (positive, negative, vae, width, height, length, batch_size) with
#: the link inputs dropped, and the served template's own `widgets_values` for that node,
#: `[640, 640, 81, 1]`. `WanFirstLastFrameToVideo` shares the declaration order and is
#: entered here now because it is the same object one socket wider — not used by E11.
#: `WanCameraImageToVideo` was added 2026-08-12 (E11 wave 2) under the same warning — the
#: day it was first used. It sizes its own latent from its own width/height/length exactly
#: as the three above do, so a camera-route graph likewise contains no `Empty*LatentVideo`
#: node at all, and leaving it out would have put Gate L back in the vacuous state E08
#: measured.
#:
#: ⚠ **Only ONE reading of its widget order was available, and that is recorded rather than
#: dressed up as two.** The convention above is to measure widget order two ways and require
#: agreement; here the second source does not exist. `get_node`'s `input_details` order
#: (positive, negative, vae, width, height, length, batch_size, then the optional
#: clip_vision_output / start_image / camera_conditions links) with the link inputs dropped
#: gives width, height, length, batch_size — the first reading. `search_templates` was
#: searched for a served workflow wiring this class on 2026-08-12 and **none of the 201
#: templates wires the Fun-Camera tier at all**, so no `widgets_values` reading exists to
#: check it against. The exposure is bounded: widget order is irrelevant in API format,
#: where inputs are keyed by name, and matters only when re-reading the SAVED file. So the
#: second reading is taken empirically there instead — `camera_widget_order_evidence`
#: reports the values standing at these indices on the converted file, and the builder's
#: saved-graph step requires them to be the ones it set.
LATENT_NODES = {
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2},
    "EmptyLatentVideo": {"width": 0, "height": 1, "length": 2},
    "WanVaceToVideo": {"width": 0, "height": 1, "length": 2},
    "WanAnimateToVideo": {"width": 0, "height": 1, "length": 2},
    "WanImageToVideo": {"width": 0, "height": 1, "length": 2},
    "WanFirstLastFrameToVideo": {"width": 0, "height": 1, "length": 2},
    "WanCameraImageToVideo": {"width": 0, "height": 1, "length": 2},
}

#: Nodes that solve a CAMERA TRAJECTORY from their own width/height/length. These do **not**
#: size the video latent — they emit a `WAN_CAMERA_EMBEDDING` — so they do not belong in
#: `LATENT_NODES`, and Gate L must not count them among the frames it checked. They get
#: their own table because of a failure mode nothing above can see.
#:
#: ⚠ **A camera embedding solved for a different frame than the one being generated passes
#: every other gate in this file.** Gate L would find the conditioning node's 832x480x65
#: legal and report a PROVEN frame; the seed clause would find every seed pinned; the
#: licence clause would find no banned weights. Meanwhile the trajectory steering the camera
#: would have been solved for, say, 81 frames, and the run would generate 65 frames of a
#: camera path computed for a clip a quarter longer — silently, with a clean receipt.
#: `WanCameraEmbedding` **defaults to length 81 while this route runs 65**, so the defect is
#: one omitted argument away rather than hypothetical. `verify` therefore checks agreement
#: rather than trusting that whoever wired the graph passed the same numbers twice.
#:
#: Widget order from `get_node` `input_details`, fetched 2026-08-12: camera_pose, width,
#: height, length, then the optional speed / fx / fy / cx / cy floats. Every input is a
#: literal — there are no link inputs to drop — so save-format indices are 1, 2, 3.
CAMERA_NODES = {
    "WanCameraEmbedding": {"width": 1, "height": 2, "length": 3},
}

#: Widget values that name a weight file. Anything ending in one of these is a component.
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".sft", ".gguf", ".task")

#: Extra node-CLASS-NAME substrings that identify a `RULED_COMPONENTS` row, beyond the
#: row key itself. Lower-cased substring test, exactly as `rulings_for` matches a file.
#:
#: ⚠ **A banned tier can enter a graph as a NODE CLASS carrying no weight filename at
#: all.** Every clause of the licence gate read `widgets_values` for something ending in
#: a weight suffix, so a `DWPreprocessor` — the served Animate template's detector, whose
#: `dwpose` row in `RULED_COMPONENTS` reads BANNED / "weights not fetched" — contributed
#: nothing to `components()` and `verify()` reported the graph clean. The detector fetches
#: its own weights at run time; there is no filename in the graph for the file clause to
#: see. A licence row is not a wiring claim, and a wiring claim is not always a filename.
#:
#: This table only ADDS aliases: the row key is always a pattern, so a row absent here is
#: not silently exempt — it is matched on its own name. The two entries below are the
#: preprocessor tier, whose ComfyUI class names do not contain their row key
#: (`DWPreprocessor` does not contain "dwpose"). Measured against the served Animate
#: template, which wires `DWPreprocessor` and `OpenposePreprocessor`.
RULED_COMPONENT_CLASSES = {
    "dwpose": ("dwpreprocessor", "dwposeestimator"),
    "openpose": ("openposepreprocessor", "openpose_preprocessor"),
}

# =======================================================================================
# GATE PAIR — does the model this graph loads have a channel for the conditioning wired
# at it? Commissioned by the E11 wave-2 ruling (R3), 2026-08-12, and paid for by one
# generation of pure noise.
#
# **What happened, because the gate exists to stop it happening again.** Wave 2 wired
# `WanCameraImageToVideo` + `WanCameraEmbedding` — both core, both correctly schema-checked
# via `get_node` before building — over the plain Wan 2.2 I2V experts. The camera tier is a
# SEPARATE set of weights (`wan2.2_fun_camera_*`, a derivative of Wan2.2-I2V-A14B trained
# for camera synthesis). The base has no channel for a camera embedding. Every check in this
# file went green: the licence clause found no banned weights, Gate S found every seed
# pinned, Gate L proved 832x480x65, the camera/frame andon found the trajectory solved for
# the generated frame, the saved-file round trip compared 51 values and 23 links. The job
# succeeded. The frames contained no subject after f1.
#
# The suite checked everything about the graph except **whether the model could receive what
# was wired at it**, and no amount of care inside the other clauses would ever have caught
# it: they are all questions about the graph's internal consistency, and this graph was
# internally consistent. The missing question is about the relationship between two things
# each of which was individually correct.
#
# ⚠ **A licence row is not a wiring claim** (now also a CLAUDE.md law). The wave-2 dispatch
# said "weights mapped Apache" and that was TRUE — of weights the graph never loaded.

#: Weight-file substrings that identify a model family, lower-cased. A file may match more
#: than one and every match is recorded; the gate asks whether the REQUIRED family is among
#: those present, never whether it is the only one.
WEIGHT_FAMILIES = {
    "fun_camera": ("fun_camera", "fun-camera", "control_camera", "control-camera"),
    "fun_control": ("fun_control", "fun-control"),
    "vace": ("vace",),
    "animate": ("animate",),
    "phantom": ("phantom",),
    "i2v": ("i2v",),
    "t2v": ("t2v",),
}

#: Conditioning class -> the weight family the loaded model MUST belong to.
#:
#: `WanFirstLastFrameToVideo` pairs with `i2v` on the same grounds as `WanImageToVideo`: it
#: is the I2V conditioning shape one socket wider. It is entered here unused, deliberately —
#: the cost of a row is nothing and the cost of its absence is measured above.
CONDITIONING_WEIGHT_FAMILY = {
    "WanCameraImageToVideo": "fun_camera",
    "WanAnimateToVideo": "animate",
    "WanVaceToVideo": "vace",
    "Wan22FunControlToVideo": "fun_control",
    "WanFunControlToVideo": "fun_control",
    "WanPhantomSubjectToVideo": "phantom",
    "WanImageToVideo": "i2v",
    "WanFirstLastFrameToVideo": "i2v",
}

#: Conditioning classes that pair with NO diffusion-model family, recorded explicitly rather
#: than by omission. ControlNet appliers carry their own weights, which the licence clause
#: already populates; they attach to a base rather than requiring a variant of it.
#:
#: The two tables are exhaustive TOGETHER: `pairing` raises on a conditioning class it finds
#: in neither, so the next new class announces itself instead of slipping through. That is
#: the `gate_saved_graph` fail-closed pattern, which stopped this same wave twice.
CONDITIONING_FAMILY_EXEMPT = {
    "ControlNetApply", "ControlNetApplyAdvanced", "ControlNetApplySD3",
    "ACN_AdvancedControlNetApply",
}

#: Node classes that load the DIFFUSION MODEL — the thing that either has the channel or
#: does not. Deliberately not every loader: a VAE or a text encoder says nothing about
#: whether the denoiser was trained on camera conditions, and counting `wan_2.1_vae` or
#: `umt5_xxl` as evidence of a family would make this gate answer the wrong question.
MODEL_LOADER_CLASSES = ("UNETLoader", "CheckpointLoaderSimple", "CheckpointLoader",
                        "UnetLoaderGGUF", "DiffusersLoader")


class PairGate(GateFailure):
    """A conditioning node was wired at a model with no channel for it."""

    gate = "PAIR"


#: Class-name suffixes that mark a node as *conditioning a video model* — the role Gate
#: PAIR needs a row for. Matched by ROLE, not by vendor prefix.
#:
#: ⚠ The fail-closed clause used to read `startswith("Wan") and endswith("ToVideo")`,
#: which a class name disarmed outright: measured 2026-09-03, a graph loading
#: `wan2.2_t2v_high_noise.safetensors` and wiring `HunyuanImageToVideo` returned
#: "0 conditioning node(s) paired against 1 model file(s)" — green, with
#: `conditioning_nodes == []` — while renaming that same node `WanSomethingNewToVideo`
#: raised. The gate exists because a licence row is not a wiring claim; a gate that only
#: recognises one vendor's naming is a licence row of its own. The E11 wave-2 failure
#: (65 frames, no subject after f1, every other gate green) would repeat unseen on any
#: non-Wan tier, which the note at the head of `LATENT_NODES` already predicts.
CONDITIONING_CLASS_SUFFIXES = ("ToVideo", "ToVideoLatent")


def _looks_like_conditioning(cls):
    """Does this class name declare the conditioning role, whoever built it?"""
    return isinstance(cls, str) and cls.endswith(CONDITIONING_CLASS_SUFFIXES)


def families_of(filename):
    """Every family a weight filename matches, lower-cased substring test."""
    low = str(filename).lower()
    return sorted(fam for fam, pats in WEIGHT_FAMILIES.items()
                  if any(p in low for p in pats))


def model_weights(graph):
    """Every DIFFUSION-model weight file the graph loads, with the families it matches."""
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        if n.get("type") not in MODEL_LOADER_CLASSES:
            continue
        for v in (n.get("widgets_values") or []):
            if isinstance(v, str) and v.lower().endswith(WEIGHT_SUFFIXES):
                out.append({"file": v, "node_id": n.get("id"), "class": n.get("type"),
                            "where": where, "families": families_of(v)})
    return out


def pairing(graph):
    """Gate PAIR · ANDON — every conditioning class is paired with a model that can take it.

    Raises when a graph wires a conditioning class whose required weight family is absent
    from the models it loads. Also raises, rather than passing quietly, when it cannot tell:
    a conditioning class it has never met, or a graph that wires one and loads no diffusion
    model this gate can read. "Nothing to check" and "everything checked out" are different
    verdicts here for the same reason they are in `verify`.
    """
    graph = normalise_graph(graph)
    loaded = model_weights(graph)
    present = sorted({fam for w in loaded for fam in w["families"]})
    cond = [(str(n.get("id")), n.get("type")) for _, n in _iter_nodes(graph)
            if n.get("type") in CONDITIONING_WEIGHT_FAMILY
            or n.get("type") in CONDITIONING_FAMILY_EXEMPT]

    ev = {"gate": "PAIR", "andon": "PairGate",
          "model_weights": loaded, "families_present": present,
          "conditioning_nodes": [{"node_id": i, "class": c,
                                  "requires": CONDITIONING_WEIGHT_FAMILY.get(c)}
                                 for i, c in cond]}

    unknown = sorted({n.get("type") for _, n in _iter_nodes(graph)
                      if _looks_like_conditioning(n.get("type"))
                      and n["type"] not in CONDITIONING_WEIGHT_FAMILY
                      and n["type"] not in CONDITIONING_FAMILY_EXEMPT})
    if unknown:
        ev["verdict"] = "INDETERMINATE"
        raise PairGate(
            f"conditioning class(es) {', '.join(unknown)} are in neither "
            f"CONDITIONING_WEIGHT_FAMILY nor CONDITIONING_FAMILY_EXEMPT, so this gate "
            f"cannot say whether the loaded model can receive them. Add a row rather than "
            f"letting a new class through — the class this gate was built for passed every "
            f"other check in this file", ev)

    required = [(i, c, CONDITIONING_WEIGHT_FAMILY[c]) for i, c in cond
                if c in CONDITIONING_WEIGHT_FAMILY]
    if required and not loaded:
        ev["verdict"] = "INDETERMINATE"
        raise PairGate(
            f"the graph wires {len(required)} conditioning node(s) but loads no diffusion "
            f"model this gate can read ({', '.join(MODEL_LOADER_CLASSES)}), so the pairing "
            f"is UNPROVEN. A check that cannot fail is not a check", ev)

    missing = [(i, c, fam) for i, c, fam in required if fam not in present]
    if missing:
        ev["verdict"] = "CONTRADICTED"
        raise PairGate(
            "; ".join(
                f"node {i} is {c}, which requires a {fam!r} model, but the graph loads "
                f"{', '.join(w['file'] for w in loaded) or 'nothing'} "
                f"(families present: {present or 'none'})" for i, c, fam in missing) +
            ". Measured 2026-08-12: this exact pairing produced 65 frames with no subject "
            "after the first, and every other gate in this file passed on it", ev)

    ev["verdict"] = (f"{len(required)} conditioning node(s) paired against "
                     f"{len(loaded)} model file(s); families present {present}")
    return ev


class RouteGate(GateFailure):
    """A graph was about to run that the repo's own record says it must not."""

    gate = "ROUTE"


def _shape_of(doc):
    """`'api'`, `'save'`, or `None` when this mapping is neither. Decides nothing."""
    if not isinstance(doc, dict):
        return None
    if isinstance(doc.get("nodes"), list):
        return "save"
    if any(isinstance(v, dict) and "class_type" in v for v in doc.values()):
        return "api"
    return None


def normalise_graph(graph):
    """THE loader. Every gate in this module reads its graph through this one function.

    Returns the graph in the shape the walk understands — API format (node-id keyed,
    `class_type` per value) or save format (a `nodes` list) — unwrapping a submission
    envelope named in `canon.GRAPH_WRAPPER_KEYS` when it finds one, and RAISING
    `RouteGate` on a mapping it cannot recognise at all.

    ⚠ **"This graph has no nodes" and "I cannot read this shape" were the same answer,
    and the second one arrived under a green receipt.** Measured 2026-09-03 on the
    standard ComfyUI submission envelope `{"prompt": <api graph>}` wrapping a graph that
    loads `causvid_x.safetensors` (BANNED, CC-BY-NC) and a `KSamplerAdvanced` at
    noise_seed 999999: bare, `verify(g, frame=(832, 480, 81))` raised naming the banned
    file; wrapped, `components()`, `seeds()` and `latents()` all returned `[]` and
    `verify` returned "0 weight file(s), 0 seed(s) all pinned, 0 of 0 latent(s)
    checkable, 1 frame(s) checked and generator-legal", with pairing reporting "0
    conditioning node(s) paired against 0 model file(s)". `gate_s_registration(wrapped,
    [7])` likewise reported every seed pinned and registered. Gate ROUTE reported a graph
    clean on licence, seeds and pairing having read zero nodes.

    This is verbatim the fix wave 3 applied to `canon.texts_from_api_graph` — "'No text
    here' and 'I did not recognise this shape' are different answers" — carried into the
    module where the spend gates live, as ONE loader rather than a second implementation:
    the wrapper-key tuple is `canon.GRAPH_WRAPPER_KEYS`, so the comment beside it and the
    behaviour here cannot drift apart again.
    """
    doc = graph
    for _ in range(len(GRAPH_WRAPPER_KEYS) + 1):
        if _shape_of(doc) is not None:
            return doc
        inner = None
        if isinstance(doc, dict):
            inner = next((doc[k] for k in GRAPH_WRAPPER_KEYS
                          if isinstance(doc.get(k), dict)), None)
        if inner is None:
            break
        doc = inner
    raise RouteGate(
        f"this is not a graph this module can read: a {type(doc).__name__} that is "
        f"neither API format (node-id keyed values carrying `class_type`) nor save "
        f"format (a `nodes` list), and that carries no wrapper key from "
        f"{list(GRAPH_WRAPPER_KEYS)}. A shape that cannot be read is not an empty "
        f"graph, and every clause of this module would otherwise report its "
        f"zero-population verdict as a pass",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_shape",
         "type": type(doc).__name__,
         "top_level_keys": sorted(map(str, doc)) if isinstance(doc, dict) else None,
         "wrapper_keys": list(GRAPH_WRAPPER_KEYS)})


def is_api_format(graph):
    """API format is node-id keyed with `class_type`; save format has a `nodes` array.

    Reads through `normalise_graph`, so an unrecognised shape raises here too rather
    than answering `False` and sending the caller down the save-format branch to walk a
    `nodes` list that does not exist.
    """
    return _shape_of(normalise_graph(graph)) == "api"


def _iter_nodes(graph):
    """Every node in the graph, read through `normalise_graph`. See `_walk_nodes`."""
    return _walk_nodes(normalise_graph(graph))


def _walk_nodes(graph):
    """Every node in the graph, INCLUDING the ones inside subgraph definitions.

    The clause that matters. A served template can present four nodes at the top level and
    hide thirty inside a subgraph blueprint, and a check that walked only the top level
    would report a clean graph while the excluded LoRA sat two levels down. Measured on
    `video_wan2_2_14B_t2v`, 2026-08-11: 4 nodes visible, 30 hidden.

    Yields `(where, node)` with the node normalised to `{id, type, widgets, inputs}`, so
    the same three questions can be asked of a hand-built API graph and of a served
    save-format one. **Both formats matter here**: we build in API format and the cloud is
    handed a saved file, so the gate has to be able to read what we wrote AND what came
    back.

    ⚠ **The recursion is the clause, not the loop.** Until 2026-09-03 this walked
    `definitions.subgraphs[*].nodes` and stopped, so a definition carrying its own
    `definitions` hid everything inside it. Measured: a graph whose outer subgraph
    contains a nested subgraph holding a `LoraLoaderModelOnly` for `causvid_x.safetensors`
    returned `['base.safetensors', 'clean.safetensors']` from `components()` — the BANNED
    file two levels down was missed and `verify` would have reported the graph clean.
    That is this function's own docstring one level further down. NOT measured: whether
    Comfy's served save format ever nests definitions rather than hoisting them, so this
    closed a hole in the walk rather than a demonstrated escape. A `visited` set of
    definition ids stands against a blueprint that references itself: the gate before a
    spend must halt or answer, never hang.
    """
    if _shape_of(graph) == "api":
        for node_id, node in graph.items():
            if not isinstance(node, dict) or "class_type" not in node:
                continue
            inputs = node.get("inputs") or {}
            # A link is [node_id, slot]; anything else is a literal this graph pins.
            widgets = [v for v in inputs.values() if not isinstance(v, list)]
            yield ("api", {"id": node_id, "type": node["class_type"],
                           "widgets_values": widgets, "inputs": inputs})
        return
    for n in graph.get("nodes") or []:
        yield ("top", n)
    yield from _iter_definitions(graph, set())


def _iter_definitions(container, visited):
    """Every node inside `container`'s subgraph definitions, to any depth."""
    for d in (container.get("definitions") or {}).get("subgraphs") or []:
        if not isinstance(d, dict):
            continue
        key = id(d) if d.get("id") is None else ("id", d["id"])
        if key in visited:
            continue
        visited.add(key)
        where = d.get("name") or d.get("id") or "subgraph"
        for n in d.get("nodes") or []:
            yield (where, n)
        yield from _iter_definitions(d, visited)


#: Verdict precedence, strictest first. A filename that matches more than one row in
#: `RULED_COMPONENTS` is governed by the STRICTEST match, never by whichever row happens
#: to have been typed into the dict first.
VERDICT_RANK = {"BANNED": 3, "EXCLUDED": 2, "ALLOWED": 1, "NOT IN THIS TABLE": 0}


def rulings_for(filename):
    """EVERY `RULED_COMPONENTS` row this weight filename matches, strictest first.

    ⚠ **`components()` used to take the FIRST match in dict-insertion order and record
    no other.** `families_of()` on the same page deliberately does the opposite and its
    table's comment says why: "A file may match more than one and every match is
    recorded." The licence clause — the one CLAUDE.md calls a non-negotiable — got the
    weaker rule. Measured 2026-09-03: `technically_color_instagirl_v2.safetensors`
    matches `technically_color` (ALLOWED, typed in at index 4) and `instagirl` (BANNED,
    Instara Fair Use — "prohibits use on any image/video generation service", index 9),
    and `components()` returned verdict ALLOWED, matched_on technically_color, with the
    BANNED row named nowhere in the evidence; `verify()` on a graph loading it returned
    green. The precedence was an accident of typing order. Stacked and merged LoRA names
    are concatenations, and the served style field this table mirrors is exactly where
    those names come from.
    """
    low = str(filename).lower()
    hits = [dict(rec, matched_on=key) for key, rec in RULED_COMPONENTS.items()
            if key in low]
    hits.sort(key=lambda r: -VERDICT_RANK.get(r["verdict"], 0))
    return hits


def class_patterns_for(key):
    """Every class-name substring that identifies the `RULED_COMPONENTS` row `key`.

    The key itself is always one of them, so a row that names no alias is still matched
    on its own name rather than silently exempted.
    """
    return tuple(sorted({str(key).lower()}
                        | {str(a).lower() for a in RULED_COMPONENT_CLASSES.get(key, ())}))


def rulings_for_class(class_type):
    """EVERY `RULED_COMPONENTS` row this NODE CLASS name matches, strictest first.

    The class-name twin of `rulings_for`, and it is a separate reading because the thing
    being read is different: a weight file is a value inside `widgets_values`, a class is
    the node's own type. A banned preprocessor tier appears only as the second.
    """
    low = str(class_type).lower()
    hits = []
    for key, rec in RULED_COMPONENTS.items():
        pat = next((c for c in class_patterns_for(key) if c in low), None)
        if pat is not None:
            hits.append(dict(rec, matched_on=key, matched_class_pattern=pat))
    hits.sort(key=lambda r: -VERDICT_RANK.get(r["verdict"], 0))
    return hits


def ruled_node_classes(graph):
    """Every node whose CLASS NAME the licence map has already ruled on.

    Reads in either format and through the subgraph walk, like every other clause here.
    Each row carries `class_type`, `verdict`, `licence` and `reason` at the top level for
    a caller that wants the ruling without unpacking, and the full `ruling` (strictest
    row, with `matches` naming every row hit) beside them.

    These rows are also returned by `components()`, so a caller already filtering that
    list on BANNED picks them up without a second call. `verify` refuses them exactly as
    it refuses a banned weight file.
    """
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        if not isinstance(cls, str):
            continue
        hits = rulings_for_class(cls)
        if not hits:
            continue
        ruling = dict(hits[0])
        ruling["matches"] = [{"matched_on": h["matched_on"], "verdict": h["verdict"],
                              "licence": h.get("licence"),
                              "matched_class_pattern": h["matched_class_pattern"]}
                             for h in hits]
        out.append({"kind": "class", "file": None, "class_type": cls,
                    "class": cls, "node_id": n.get("id"), "where": where,
                    "verdict": ruling["verdict"], "licence": ruling.get("licence"),
                    "reason": ruling.get("reason"),
                    "matched_on": ruling.get("matched_on"), "ruling": ruling})
    return out


def components(graph):
    """Every ruled thing the graph carries: weight files loaded, and ruled node CLASSES.

    The ruling is the STRICTEST row the name matches, and `ruling["matches"]` names
    every row it matched — see `rulings_for` and `rulings_for_class`.

    Rows carry `kind`: `"weight"` for a file named in `widgets_values`, `"class"` for a
    node class the licence map rules on (see `ruled_node_classes` — a `DWPreprocessor`
    brings no filename with it and was invisible to every clause here until 2026-09-04).
    Both carry `verdict` at the top level as well as inside `ruling`, so one filter
    reads both kinds.
    """
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        for v in (n.get("widgets_values") or []):
            if not isinstance(v, str):
                continue
            if not v.lower().endswith(WEIGHT_SUFFIXES):
                continue
            hits = rulings_for(v)
            ruling = dict(hits[0]) if hits else {"verdict": "NOT IN THIS TABLE",
                                                 "reason": "check docs/license-map.md"}
            ruling["matches"] = [{"matched_on": h["matched_on"], "verdict": h["verdict"],
                                  "licence": h.get("licence")} for h in hits]
            out.append({"kind": "weight", "file": v, "node_id": n.get("id"),
                        "class": n.get("type"), "where": where,
                        "verdict": ruling["verdict"], "licence": ruling.get("licence"),
                        "reason": ruling.get("reason"),
                        "matched_on": ruling.get("matched_on"), "ruling": ruling})
    out.extend(ruled_node_classes(graph))
    return out


def _component_label(rec):
    """What to call a component in a refusal: its filename, or its node class."""
    return (f"node class {rec['class_type']!r}" if rec.get("kind") == "class"
            else repr(rec.get("file")))


#: The input names a seed lives under in API format, per node class.
SEED_INPUTS = {"KSampler": "seed", "KSamplerAdvanced": "noise_seed",
               "Wan2ReferenceVideoApi": "seed"}

#: Input names that ARE a seed, whatever class carries them, and class-name suffixes that
#: declare a sampling or noise role. Used only by `unrecorded_seed_sources` — the andon
#: that answers "this table does not know that class" instead of answering "no seeds".
SEED_INPUT_NAMES = ("seed", "noise_seed", "rand_seed")
SEED_CLASS_SUFFIXES = ("Sampler", "Noise")

#: Class-name suffixes that mark a HOSTED / partner node, whose save-format
#: `widgets_values` this repo cannot interpret without a recorded widget-index row.
#:
#: ⚠ Used by `unrecorded_seed_sources` in SAVE FORMAT ONLY. In API format inputs are
#: keyed by name and the input-name clause already answers; in save format the values are
#: positional and nothing names them, so a vendor node's widget list is exactly the
#: direction no other clause bounds — and save format is the format the cloud hands back
#: and the one `load_graph` / `gate_saved_graph` read before submission. Measured
#: 2026-09-04 on `{"nodes": [KSampler(seed 7, "fixed"), KlingVideoApi(widgets
#: [..., 999999999]), ...]}`: `unrecorded_seed_sources` returned [], `gate_s_registration`
#: reported "1 noise-bearing seed(s), all pinned and all drawn from the committed list of
#: 1", and node 4's 999999999 was never examined. `Wan2ReferenceVideoApi` carries a
#: `SEED_NODES` row and so is read rather than flagged — which is what the andon asks
#: for: a row, in the spec that arms the tier.
HOSTED_API_CLASS_SUFFIXES = ("Api", "API")


def _save_format_input_names(node):
    """Every input NAME a save-format node declares, converted widgets included.

    Save format spells `inputs` as a LIST of slot dicts (`{"name", "type", "link"}`); a
    widget converted to an input also carries `{"widget": {"name": ...}}`. API format
    spells it as a mapping, which the caller reads directly.
    """
    out = []
    for slot in node.get("inputs") or []:
        if not isinstance(slot, dict):
            continue
        if isinstance(slot.get("name"), str):
            out.append(slot["name"])
        widget = slot.get("widget")
        if isinstance(widget, dict) and isinstance(widget.get("name"), str):
            out.append(widget["name"])
    return out


def unrecorded_seed_sources(graph):
    """Nodes that look like they carry a seed and have NO `SEED_NODES` row.

    ⚠ **A class absent from `SEED_NODES` used to disarm Gate S in the affirmative.**
    `seeds()` returns [] for it, and both readers then reported green. Measured
    2026-09-03 on an API graph wiring `SamplerCustomAdvanced` fed by `RandomNoise` at
    `noise_seed=123456789`: `seeds()` returned [], `verify(g, family="wan")` reported
    "0 seed(s) all pinned" with `seed_clause_verdict = "CHECKED — 0 seed(s) all pinned"`,
    and `gate_s_registration(g, [7])` reported "0 noise-bearing seed(s), all pinned and
    all drawn from the committed list of 1" — while the seed that would actually run was
    123456789 and the committed list was [7].

    That is the shape the E13 halt-era executor refused to record as a pass, and the
    remedy taken then was to add one row to `SEED_NODES` — which is exactly what the
    `LATENT_NODES` note says is not a fix: "Adding a class to this table fixes one graph;
    it does not fix the shape of that failure." So the shape is fixed here instead, the
    way Gate L and Gate PAIR already answer: "nothing was checkable" is a third answer,
    and it raises.

    Detection is by the thing being read, not by a vendor prefix: an input named
    `seed`/`noise_seed`/`rand_seed` on a class with no row; or a class name ending in
    `Sampler` or `Noise` with no row. `endswith` rather than a substring on purpose —
    `KSamplerSelect` picks a scheduler and carries no seed, and an andon that fires on a
    correct graph is not one anybody keeps.

    ⚠ **The input-name half used to run in API FORMAT ONLY, and the two formats then
    gave opposite answers about the same graph.** Line `if api:` gated it, and in save
    format only the class-name suffix survived — so a hosted or vendor node carrying a
    seed widget was invisible. Measured 2026-09-04 on the save-format graph `{"nodes":
    [KSampler(seed 7, control "fixed"), KlingVideoApi(widgets [..., 999999999]),
    UNETLoader, WanImageToVideo]}`: this function returned [], `seeds()` returned only
    the KSampler, `gate_s_registration(g, [7])` returned "1 noise-bearing seed(s), all
    pinned and all drawn from the committed list of 1", and `verify(g,
    frame=(832,480,81))` returned "CHECKED — 1 seed(s) all pinned" — while node 4's seed
    999999999 was never examined and no committed list pre-registers it. The same node in
    API format WAS caught. Save format is the format the cloud hands back and the one
    `load_graph` / `gate_saved_graph` read before submission.

    Save format names inputs too — as a list of slot dicts, converted widgets included —
    so the input-name clause now runs in both, reading each format's own spelling
    (`_save_format_input_names`). The second save-format clause is
    `HOSTED_API_CLASS_SUFFIXES`: a partner node whose positional widget list this repo
    has no recorded row for, which is the KlingVideoApi shape above.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        if not isinstance(cls, str) or cls in SEED_NODES:
            continue
        names = (list(n.get("inputs") or {}) if api
                 else _save_format_input_names(n))
        why = None
        hit = sorted({k for k in names if k in SEED_INPUT_NAMES})
        if hit:
            why = f"carries seed-shaped input(s) {', '.join(hit)}"
        if why is None and cls.endswith(SEED_CLASS_SUFFIXES):
            why = "the class name declares a sampling or noise role"
        if why is None and not api and cls.endswith(HOSTED_API_CLASS_SUFFIXES):
            why = (f"it is a hosted/partner node whose save-format widgets are "
                   f"positional and this module has no recorded widget row for "
                   f"{cls!r}, so a seed among its {len(n.get('widgets_values') or [])} "
                   f"widget value(s) cannot be read at all")
        if why:
            out.append({"node_id": n.get("id"), "class": cls, "where": where, "why": why})
    return out


def _seed_population_andon(graph, found, ev, carries_no_sampler):
    """The third answer, shared by `verify`'s seed clause and `gate_s_registration`.

    Raises unless the seed population is one this module can honestly describe. The
    caller may assert `carries_no_sampler=True` — and that assertion is CHECKED, not
    obeyed: it raises if a seed or an unrecorded seed source turns up under it, which is
    what keeps it from being a skip flag.
    """
    # The caller's evidence dict is the one that will be raised, and the andon that
    # raises from here is `RouteGate` whatever clause called in. Written as plain
    # assignments so the receipt names its own id even when this helper is reached from
    # a caller that built its dict differently.
    ev["gate"] = "ROUTE"
    ev["andon"] = "RouteGate"
    unrecorded = unrecorded_seed_sources(graph)
    ev["unrecorded_seed_sources"] = unrecorded
    ev["carries_no_sampler_asserted"] = bool(carries_no_sampler)
    if unrecorded:
        ev["seed_clause_verdict"] = "INDETERMINATE"
        raise RouteGate(
            "the seed clause is INDETERMINATE: " + "; ".join(
                f"node {u['node_id']} is {u['class']}, which has no SEED_NODES row and "
                f"{u['why']}" for u in unrecorded) +
            ". `seeds()` reports nothing for such a class and every reader then reports "
            "green — the affirmative form of the failure Gate S exists to prevent. Add "
            "the class's row in the spec that first arms the tier", ev)
    if carries_no_sampler:
        if found:
            ev["seed_clause_verdict"] = "CONTRADICTED"
            raise RouteGate(
                f"the caller asserted this graph carries no sampler and it carries "
                f"{len(found)} seed-bearing node(s): " + ", ".join(
                    f"node {s['node_id']} ({s['class']})" for s in found) +
                ". The assertion is checked, not obeyed", ev)
        return
    if not found:
        ev["seed_clause_verdict"] = "INDETERMINATE"
        raise RouteGate(
            "the seed clause is INDETERMINATE on this graph and therefore UNPROVEN: it "
            "found no seed at all, and 'no seed was found' and 'every seed is pinned' "
            "are not the same verdict — the second is what this module used to print. "
            "Pass carries_no_sampler=True if the graph really carries none (the "
            "assertion is checked), or add the sampler class's SEED_NODES row", ev)


def seeds(graph):
    """Every seed in the graph and whether it is pinned.

    **Pinned means something different in each format, and both meanings are the honest
    one.** In save format the UI widget `control_after_generate` decides the next run's
    seed, so `randomize` is not pinned however concrete the current number looks. In API
    format that widget does not exist at all: a seed is pinned when it is a literal, and
    unpinned when it arrives over a link from a node that could compute anything.

    **A third state exists and it used to read as the first.** `literal = not
    isinstance(value, list)` is True for a key that is not there at all, so an API
    `KSampler` carrying no `seed` input was recorded `seed=None, seed_is_literal=True,
    pinned=True` — measured 2026-09-03, `verify` reported "1 seed(s) all pinned" on it.
    An absent seed is not a pinned one: nothing in the graph says what will run, which is
    the same thing a link says and worse. It is now `seed_is_literal=False,
    pinned=False`, carrying `seed_input_present=False` so a reader can tell the missing
    key from the link. (`gate_s_registration` did fail closed on the same graph, so this
    was confined to `verify`'s pinned clause and its verdict string.)
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        spec = SEED_NODES.get(cls)
        if not spec:
            continue
        if api:
            key = SEED_INPUTS[cls]
            inputs = n.get("inputs") or {}
            present = key in inputs
            value = inputs.get(key)
            literal = present and not isinstance(value, list)
            out.append({"node_id": n.get("id"), "class": cls, "where": where,
                        "seed": value if literal else None,
                        "control_after_generate": None,
                        "seed_input_present": present,
                        "seed_is_literal": literal, "pinned": literal})
            continue
        wv = n.get("widgets_values") or []
        seed = wv[spec["seed"]] if len(wv) > spec["seed"] else None
        control = wv[spec["control"]] if len(wv) > spec["control"] else None
        out.append({"node_id": n.get("id"), "class": cls, "where": where,
                    "seed": seed, "control_after_generate": control,
                    "seed_is_literal": True, "pinned": control == "fixed"})
    return out


def latents(graph):
    """Every video latent's width, height and frame count.

    Each record carries `checkable`: whether all three numbers are literals this graph
    pins. A dimension arriving over a link, or missing from a short `widgets_values`, is
    `None` — and a `None` is not a small frame, it is **no answer**. `verify` counts the
    checkable ones, because a list whose entries answer nothing is the shape the E08 defect
    wore.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        spec = LATENT_NODES.get(n.get("type"))
        if not spec:
            continue
        rec = {"node_id": n.get("id"), "class": n.get("type"), "where": where}
        if api:
            inp = n.get("inputs") or {}
            for key in ("width", "height", "length"):
                v = inp.get(key)
                rec[key] = v if not isinstance(v, list) else None
        else:
            wv = n.get("widgets_values") or []
            for key in ("width", "height", "length"):
                i = spec[key]
                rec[key] = wv[i] if len(wv) > i else None
        rec["checkable"] = None not in (rec["width"], rec["height"], rec["length"])
        out.append(rec)
    return out


def cameras(graph):
    """Every camera-trajectory node's width, height and frame count.

    Shaped exactly like `latents()` — including the `checkable` flag, for the same reason: a
    dimension arriving over a link is `None`, and a `None` is no answer rather than a small
    number. These records are reported separately from the latents so that Gate L's count of
    "frames checked" cannot be inflated by a node that sizes no frame at all.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        spec = CAMERA_NODES.get(n.get("type"))
        if not spec:
            continue
        rec = {"node_id": n.get("id"), "class": n.get("type"), "where": where}
        if api:
            inp = n.get("inputs") or {}
            for key in ("width", "height", "length"):
                v = inp.get(key)
                rec[key] = v if not isinstance(v, list) else None
        else:
            wv = n.get("widgets_values") or []
            for key in ("width", "height", "length"):
                i = spec[key]
                rec[key] = wv[i] if len(wv) > i else None
        rec["checkable"] = None not in (rec["width"], rec["height"], rec["length"])
        out.append(rec)
    return out


def camera_widget_order_evidence(graph, expect):
    """The empirical SECOND reading of `CAMERA_NODES` widget order, on a save-format graph.

    `CAMERA_NODES` and the camera entry of `LATENT_NODES` were each derived from a single
    source — the `get_node` schema — because no served template wires this tier to check
    them against. Positional indices derived once and never confirmed are exactly what the
    `LATENT_NODES` warning is about, so the confirmation is taken here instead: read the
    values standing at those indices on the file the cloud will actually execute, and hand
    back what was found. `expect` is `{"width": .., "height": .., "length": ..}` — the
    numbers the builder set.

    Returns evidence with `agrees` per node. It reports; the caller decides whether a
    disagreement halts, because on an API-format graph there is nothing positional to
    confirm and the honest answer there is `not_applicable`, not `PASS`.
    """
    graph = normalise_graph(graph)
    ev = {"check": "camera widget order (empirical second reading)", "expect": dict(expect),
          "nodes": []}
    if is_api_format(graph):
        ev["verdict"] = "not_applicable — API format keys inputs by name, nothing positional"
        return ev
    for where, n in _iter_nodes(graph):
        spec = CAMERA_NODES.get(n.get("type")) or LATENT_NODES.get(n.get("type"))
        if not spec or n.get("type") not in set(CAMERA_NODES) | {"WanCameraImageToVideo"}:
            continue
        wv = n.get("widgets_values") or []
        found = {k: (wv[spec[k]] if len(wv) > spec[k] else None)
                 for k in ("width", "height", "length")}
        ev["nodes"].append({
            "node_id": n.get("id"), "class": n.get("type"), "where": where,
            "indices": {k: spec[k] for k in ("width", "height", "length")},
            "found": found, "widgets_values": wv,
            "agrees": all(found[k] == expect[k] for k in ("width", "height", "length")),
        })
    disagree = [n for n in ev["nodes"] if not n["agrees"]]
    ev["verdict"] = (
        "CONTRADICTED — the declared indices do not carry the builder's numbers"
        if disagree else
        f"the declared indices carry the builder's numbers on {len(ev['nodes'])} node(s)")
    ev["agrees"] = not disagree
    return ev


def _frame_triple(frame):
    """`(width, height, length)` from a tuple or a mapping, or raise saying what arrived."""
    if isinstance(frame, dict):
        try:
            return int(frame["width"]), int(frame["height"]), int(frame["length"])
        except KeyError as exc:
            raise RouteGate(
                f"the supplied frame is missing {exc.args[0]!r}; Gate L needs all three of "
                f"width, height and length, and two out of three proves nothing",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_triple",
                 "supplied": frame}) from None
    if isinstance(frame, (list, tuple)) and len(frame) == 3:
        return int(frame[0]), int(frame[1]), int(frame[2])
    raise RouteGate(
        f"the supplied frame {frame!r} is not (width, height, length) or a mapping "
        f"carrying those three keys",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_triple",
         "supplied": frame})


def _frame_form(rules, family):
    """`(modulus, residue)` parsed out of a family's declared `frame_form`.

    The rule is DATA — `GENERATOR_RULES['wan']['frame_form'] == '4n+1'` — and the code
    used to test `(length - 1) % 4` against a literal 4, so the declared field was never
    read. A second family declaring `8n+1` would have been graded on wan's temporal rule
    while its own row said otherwise, and nothing would have printed differently.
    `gates.GeneratorProfile` already stores modulus and residue separately; this parses
    the same two numbers out of the string form this table uses.
    """
    form = rules.get("frame_form")
    try:
        mod, res = str(form).split("n+")
        return int(mod), int(res)
    except (AttributeError, TypeError, ValueError):
        raise RouteGate(
            f"generator family {family!r} declares frame_form {form!r}, which is not of "
            f"the form '<modulus>n+<residue>'. The rule is data and it is read; a family "
            f"whose row cannot be parsed is graded on nobody's rule rather than silently "
            f"on wan's",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_form",
             "family": family, "rules": rules}) from None


def frame_legality(width, height, length, family="wan"):
    """Gate L, standalone: is this frame legal for that generator? Derive, then round.

    Returns the verdict and, when illegal, the nearest legal value in each direction — so a
    caller rounds to a stated number instead of guessing one.

    **Zero and negative are illegal, and they used not to be.** Measured 2026-09-03,
    `frame_legality(0, 0, 1)` and `frame_legality(-16, -16, 1)` both returned
    `legal=True` with no problems, because 0 and -16 are multiples of 16 and (1-1) is a
    multiple of 4: a builder whose frame derivation returned 0 got a green Gate L. A
    non-integer dimension raised a bare `TypeError` from the modulo, which is not an
    exception any caller of a gate is catching — that now raises `RouteGate` naming the
    value. The split is deliberate: a wrong TYPE is a malformed question and raises; a
    wrong VALUE is an illegality and is reported through `problems` like every other,
    so `verify` halts on it with the whole evidence dict rather than a bare error.
    """
    rules = GENERATOR_RULES.get(family)
    if rules is None:
        raise RouteGate(f"no recorded frame rules for generator family {family!r}; the "
                        f"constraint is recorded per model in the spec that first uses it",
                        {"gate": "ROUTE", "andon": "RouteGate",
                         "clause": "unknown_generator_family",
                         "known": sorted(GENERATOR_RULES)})
    for axis, value in (("width", width), ("height", height), ("length", length)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise RouteGate(
                f"{axis} {value!r} is not an int ({type(value).__name__}); Gate L "
                f"compares it against a divisibility rule and would otherwise raise a "
                f"bare TypeError out of the modulo",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_type",
                 "family": family, "width": width, "height": height, "length": length})
    m = rules["dim_multiple"]
    modulus, residue = _frame_form(rules, family)
    problems = []
    for axis, value in (("width", width), ("height", height)):
        if value <= 0:
            problems.append(f"{axis} {value} is not positive")
        elif value % m:
            problems.append(f"{axis} {value} is not a multiple of {m} "
                            f"(nearest: {m * round(value / m)})")
    if length <= 0:
        problems.append(f"length {length} is not positive")
    elif (length - residue) % modulus:
        problems.append(
            f"length {length} is not of the form {modulus}n+{residue} "
            f"(nearest: {modulus * round((length - residue) / modulus) + residue})")
    if length > rules["max_frames"]:
        problems.append(f"length {length} exceeds the {rules['max_frames']}-frame "
                        f"trained horizon")
    return {"gate": "L", "family": family, "width": width, "height": height,
            "length": length, "rules": rules, "frame_form": f"{modulus}n+{residue}",
            "problems": problems, "legal": not problems}


#: Where a hosted tier's enum values sit in SAVE format's positional `widgets_values`.
#: Read off the file the cloud converted, 2026-08-13, and required to agree with the
#: `get_node` declaration order — the same two-reading standard the camera rows carry.
#: `gate_saved_graph.WIDGET_INDEX` holds the full row for the same class; this is the
#: subset Gate L needs, kept here so `route_gates` does not import the gate that imports it.
HOSTED_ENUM_WIDGETS = {
    "Wan2ReferenceVideoApi": {"resolution": 3, "ratio": 4, "duration": 5},
}


def hosted_enums(graph):
    """EVERY hosted node's `(node_id, resolution, ratio, duration)`, in EITHER format.

    Found by the field rather than by the class name in API format, because the thing being
    read is the field. In save format there are no field names at all — the values are
    positional — so the class-keyed table above is the only way in, and a class missing
    from it contributes nothing rather than guessing an index.

    ⚠ **It returns a LIST because it used to return the first match.** Measured
    2026-09-03 on a save-format graph with two `Wan2ReferenceVideoApi` nodes — the first
    at ('720P', '16:9', 5) and the second at ('4K', '99:1', 900) — this function returned
    the first and `verify`'s hosted branch checked only that tuple, reporting "hosted tier
    wan2.7-r2v at 720P 16:9 5s — enum-legal". The illegal second node was named nowhere
    in the evidence, so a two-shot hosted graph could carry an out-of-contract resolution,
    ratio or duration under a green Gate L receipt.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for _where, n in _iter_nodes(graph):
        if api:
            inp = n.get("inputs") or {}
            if "model.resolution" in inp:
                out.append((n.get("id"), inp.get("model.resolution"),
                            inp.get("model.ratio"), inp.get("model.duration")))
        else:
            idx = HOSTED_ENUM_WIDGETS.get(n.get("type"))
            if idx:
                wv = n.get("widgets_values") or []
                if len(wv) > max(idx.values()):
                    out.append((n.get("id"), wv[idx["resolution"]], wv[idx["ratio"]],
                                wv[idx["duration"]]))
    return out


def hosted_frame_legality(resolution, ratio, duration, tier):
    """Gate L, for a tier that constrains by enum rather than by pixels.

    The clause `frame_legality` above cannot express: `wan2.7-r2v` never receives a width,
    a height or a frame count from us, so asking whether 1024 is a multiple of 16 answers
    a question this route does not pose. What it does constrain is a resolution enum, a
    ratio enum and an integer number of seconds — and every one of those has an illegal
    value the submission would be refused for, which is what makes this a gate and the
    pixel clause a category error here.

    Returns the same shape `frame_legality` does, so a caller reports both the same way.
    """
    rules = HOSTED_TIER_RULES.get(tier)
    if rules is None:
        raise RouteGate(
            f"no recorded tier rules for {tier!r}; a hosted tier's constraints are recorded "
            f"in the spec that first uses it, from that tier's own node contract",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unknown_hosted_tier",
             "known": sorted(HOSTED_TIER_RULES)})
    problems = []
    if resolution not in rules["resolutions"]:
        problems.append(f"resolution {resolution!r} is not one of {rules['resolutions']}")
    if ratio not in rules["ratios"]:
        problems.append(f"ratio {ratio!r} is not one of {rules['ratios']}")
    lo, hi = rules["duration_s"]
    if not isinstance(duration, int) or isinstance(duration, bool):
        problems.append(f"duration {duration!r} is not an integer number of seconds")
    elif not lo <= duration <= hi:
        problems.append(f"duration {duration} is outside {lo}..{hi} seconds")
    return {"gate": "L", "tier": tier, "resolution": resolution, "ratio": ratio,
            "duration_s": duration, "rules": {k: list(v) if isinstance(v, tuple) else v
                                              for k, v in rules.items()},
            "problems": problems, "legal": not problems}


def gate_s_registration(graph, registered, *, carries_no_sampler=False):
    """Gate S · ANDON — every seed about to run was pre-registered in a committed list.

    E04's andon, and it guards a failure with no technical symptom at all: every other gate
    passes on a seed-shopped run, and what is wrong is epistemic. A rule forbids; a list
    removes the possibility, and git timestamps the list ahead of the artifacts it governs.

    It binds in **both** directions. An unregistered seed is the obvious clause. A
    registered list that the graph does not draw from is the second: a graph running some
    other number while a tidy list sits in the repo is the same defect wearing a receipt.
    """
    graph = normalise_graph(graph)
    found = seeds(graph)
    reg = list(registered or [])
    # The evidence's `gate` is the id of the andon that will raise, which is
    # `RouteGate.gate` == "ROUTE". It used to read "S": `stage_render.py:509-510` prints
    # `GATE_FAILURE <exc.gate>` and `GATE_EVIDENCE <json of exc.evidence>` as two lines,
    # so a receipt for this clause said ROUTE on one and S on the other — and "S" is
    # already the id of a DIFFERENT andon (`errors.GateSSeedRegistration`), carrying
    # different evidence keys, so a reader resolving the id landed on the wrong class.
    # The clause's own name rides beside it instead. `pairing` on this page already does
    # it this way (`ev["gate"] == "PAIR"` and it raises `PairGate`).
    ev = {"gate": "ROUTE", "andon": "RouteGate", "clause": "gate_s_registration",
          "registered": reg, "seeds": found}
    # · ANDON — the third answer. See `_seed_population_andon`: a sampler class with no
    # SEED_NODES row makes `seeds()` return [] and this function then reported "0
    # noise-bearing seed(s), all pinned and all drawn from the committed list".
    _seed_population_andon(graph, found, ev, carries_no_sampler)
    if not reg:
        raise RouteGate(
            "Gate S: no seed list was pre-registered, so no seed may be varied at all. "
            "Commit the list before the first submission — that is what makes it a "
            "registration rather than a note", ev)
    loose = [s for s in found if not s["pinned"]]
    if loose:
        raise RouteGate(
            "Gate S: " + ", ".join(
                f"node {s['node_id']} ({s['class']}) is not pinned "
                f"(control_after_generate={s['control_after_generate']!r}, "
                f"literal={s['seed_is_literal']})" for s in loose), ev)
    # add_noise="disable" samplers take no noise from their seed; theirs is inert and is
    # reported rather than demanded, so a two-expert split does not need a second entry.
    #
    # **The two formats spell `inputs` differently and that is not cosmetic.** In API format
    # it is a mapping of name -> literal-or-link; in save format it is a LIST of slot dicts.
    # Calling `.get` on the list raised outright on the first save-format graph whose
    # sampler had any connected input (measured 2026-08-12, E10): E09's saved samplers had
    # empty input arrays, `or {}` swallowed them, and the defect waited for a graph with
    # links. It is a crash rather than a wrong answer, which is the good kind of latent bug.
    api = is_api_format(graph)
    live = []
    for s in found:
        n = next((x for _, x in _iter_nodes(graph) if str(x.get("id")) == str(s["node_id"])),
                 None)
        slot = SEED_NODES[s["class"]].get("add_noise")
        adds = True
        if n is not None and slot is not None:
            if api:
                adds = (n.get("inputs") or {}).get("add_noise", "enable") \
                    not in ("disable", False)
            else:
                wv = n.get("widgets_values") or []
                adds = (wv[slot] if len(wv) > slot else "enable") not in ("disable", False)
        s["adds_noise"] = adds
        if adds:
            live.append(s)
    unregistered = [s for s in live if s["seed"] not in reg]
    if unregistered:
        raise RouteGate(
            "Gate S: " + ", ".join(
                f"node {s['node_id']} would run seed {s['seed']}" for s in unregistered) +
            f", which the committed list {reg} does not pre-register. A seed chosen after "
            f"seeing a result turns a measurement into a selection of one", ev)
    ev["verdict"] = (
        f"no sampler in this graph (asserted by the caller and checked), so no seed was "
        f"drawn against the committed list of {len(reg)}" if not found else
        f"{len(live)} noise-bearing seed(s), all pinned and all drawn from "
        f"the committed list of {len(reg)}")
    return ev


def verify(graph, *, family="wan", require_pinned_seeds=True, allow=(), frame=None,
           hosted_tier=None, carries_no_sampler=False):
    """The three questions at once. Raises on anything the record already ruled against.

    `allow` names component keys the caller has an explicit ruling for — it is not a skip
    flag, because a component named here still appears in the returned evidence with its
    verdict, so the report cannot omit that it ran.

    `hosted_tier` names a tier from `HOSTED_TIER_RULES` whose graph carries **no pixel
    dimension at all** — `wan2.7-r2v` takes a resolution enum, a ratio enum and an integer
    duration, and never receives a width or a frame count from us. On such a graph the
    pixel clause is not merely unproven, it is INAPPLICABLE, and the enum clause is the one
    that binds. It is not a skip flag: the tier must be a recorded one (an unknown name
    raises), the enum values are checked exactly as the pixel rules would be, an illegal
    one raises here, and the evidence carries both the enum verdict and the reason the
    pixel clause did not apply — so a report cannot omit that the substitution happened.
    Passing `frame` and `hosted_tier` together is refused: they are two answers to one
    question. Owed to this tier by the E13 halt ruling (R6), which measured Gate L's `wan`
    rules unable to describe it.

    `frame` is `(width, height, length)`, or a mapping carrying those keys, for the caller
    that KNOWS the shape it is about to generate — the builder of the graph. It is not a
    skip flag either: a supplied frame is checked against the generator's rules exactly as
    a graph-read one is, it is labelled `supplied` in the evidence, and where the graph
    also pins a checkable latent the two must agree or the gate raises.

    **Why a caller may need to supply it — the E08 catch, 2026-08-12.** Gate L examined
    ZERO latents on the first Animate graph and reported it legal: `WanAnimateToVideo`
    emits its own latent, so no `Empty*LatentVideo` node existed and `latents()` came back
    empty. Adding that class to the table fixed THAT graph. It did not fix the shape of the
    failure, which is that "no latent was found" and "every latent found is legal" were the
    same verdict. They are now different: with nothing checkable and nothing supplied the
    frame-legality clause is **INDETERMINATE — unproven — and raises**, because a check
    that cannot fail is not a check.
    """
    graph = normalise_graph(graph)
    if hosted_tier is not None and frame is not None:
        raise RouteGate(
            "verify() was given both a hosted tier and a pixel frame; they are two answers "
            "to the same question and one of them would be the number nobody checked",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "two_answers",
             "hosted_tier": hosted_tier, "frame": frame})
    comp = components(graph)
    sd = seeds(graph)
    lat = latents(graph)
    legality = [dict(frame_legality(l["width"], l["height"], l["length"], family),
                     source="graph", node_id=l["node_id"], node_class=l["class"])
                for l in lat if l["checkable"]]
    supplied = None
    if frame is not None:
        w, h, n = _frame_triple(frame)
        supplied = dict(frame_legality(w, h, n, family), source="supplied")
        legality.append(supplied)
    ev = {"gate": "ROUTE", "andon": "RouteGate",
          "components": comp, "seeds": sd, "latents": lat,
          "latents_checkable": sum(1 for l in lat if l["checkable"]),
          "frame_legality": legality}

    # `allow` may wave a METHODOLOGY ruling. It may not wave a LICENCE one. The filter
    # used to treat the two verdicts as one class, so `allow=('causvid',)` moved a
    # CC-BY-NC weight through and returned a green verdict that said nothing about the
    # waiver — measured 2026-09-03. CLAUDE.md's licence gate is a non-negotiable: no
    # non-commercially-licensed weight anywhere in the pipeline, experiments included.
    # An attempt to allow one is refused here rather than obeyed, and it is refused even
    # on a graph that does not load it, because the call itself is the defect.
    banned_allowed = sorted(k for k in allow
                            if RULED_COMPONENTS.get(k, {}).get("verdict") == "BANNED")
    if banned_allowed:
        raise RouteGate(
            "allow= names " + ", ".join(
                f"{k!r} ({RULED_COMPONENTS[k]['licence']}: "
                f"{RULED_COMPONENTS[k]['reason']})" for k in banned_allowed) +
            ". A BANNED row is a LICENCE ruling and no keyword argument waves one; "
            "`allow` exists for the EXCLUDED rows, which are methodology rulings",
            dict(ev, allow=list(allow)))

    bad = [c for c in comp
           if c["ruling"]["verdict"] in ("BANNED", "EXCLUDED")
           and c["ruling"].get("matched_on") not in allow]
    if bad:
        raise RouteGate(
            "the graph loads " + ", ".join(
                f"{_component_label(c)} ({c['ruling']['verdict']}: "
                f"{c['ruling']['reason']})"
                + (f" [this {'class name' if c.get('kind') == 'class' else 'filename'}"
                   f" also matches "
                   + ", ".join(f"{m['matched_on']}={m['verdict']}"
                               for m in c["ruling"]["matches"][1:]) + "]"
                   if len(c["ruling"].get("matches") or []) > 1 else "")
                for c in bad) +
            ". The licence map's ruling is that presence is presence — a bypassed node "
            "still counts, and these are not even bypassed", ev)

    # A waived component appears in `components` with its verdict, but the string a
    # builder stores and a provenance sheet prints is `verdict` — so the waiver is named
    # there too. A receipt that omits it is a receipt that reads clean.
    waived = sorted({c["ruling"]["matched_on"] for c in comp
                     if c["ruling"]["verdict"] == "EXCLUDED"
                     and c["ruling"].get("matched_on") in allow})
    ev["waived"] = waived

    # · ANDON — Gate PAIR. Placed after the licence clause (a banned weight stays the
    # headline) and before everything else, because every clause below is a question about
    # the graph's internal consistency and this one is the only question about whether the
    # model can receive what the graph wires at it. Wave 2 was internally consistent.
    ev["pairing"] = pairing(graph)

    # The verdict must describe what RAN. `require_pinned_seeds=False` skipped the clause
    # and still returned "N seed(s) all pinned" — the string `build_t2v_payload` and
    # `gate_saved_graph` store in the spend meta and `make_startframe_sheet` renders onto
    # the provenance sheet. Measured 2026-09-03 on a graph whose only sampler carries
    # control_after_generate='randomize'. A record may not assert a property nobody
    # checked, so the skip is named in the verdict rather than hidden by it.
    if require_pinned_seeds:
        # · ANDON — the third answer the other three clauses in this file already have
        # (Gate L latent, Gate L hosted, Gate PAIR). A sampler class absent from
        # SEED_NODES makes `seeds()` return [] and this clause used to print "0 seed(s)
        # all pinned" over it. See `_seed_population_andon`.
        _seed_population_andon(graph, sd, ev, carries_no_sampler)
    elif carries_no_sampler:
        raise RouteGate(
            "verify() was given carries_no_sampler=True with require_pinned_seeds=False; "
            "one asserts a property of the graph and the other says nobody looked, and "
            "the assertion would go unchecked", dict(ev, seeds=sd))

    if not require_pinned_seeds:
        ev["seed_clause_verdict"] = "NOT CHECKED (require_pinned_seeds=False)"
        seed_phrase = (f"{len(sd)} seed(s) NOT CHECKED for pinning "
                       f"(require_pinned_seeds=False)")
    elif not sd:
        ev["seed_clause_verdict"] = (
            "CHECKED — no sampler in this graph (asserted by the caller and checked)")
        seed_phrase = "no sampler (asserted and checked), so no seed to pin"
    else:
        ev["seed_clause_verdict"] = f"CHECKED — {len(sd)} seed(s) all pinned"
        seed_phrase = f"{len(sd)} seed(s) all pinned"

    if require_pinned_seeds:
        loose = [s for s in sd if not s["pinned"]]
        if loose:
            raise RouteGate(
                "Gate S cannot be armed on this graph: " + ", ".join(
                    f"node {s['node_id']} ({s['class']}) has control_after_generate="
                    f"{s['control_after_generate']!r}" for s in loose) +
                ". A seed that randomises is a seed no committed list pre-registered, and "
                "the experiment's number would be quoted against a run nobody can repeat",
                ev)

    illegal = [f for f in ev["frame_legality"] if not f["legal"]]
    if illegal:
        raise RouteGate(
            "Gate L: " + "; ".join("; ".join(f["problems"]) for f in illegal), ev)

    # A supplied frame that disagrees with a frame the graph itself pins is not a small
    # discrepancy to average over: one of the two is what will run, and the report would
    # quote the other. Both are legal at this point, so nothing else in the chain looks.
    if supplied is not None:
        want = (supplied["width"], supplied["height"], supplied["length"])
        clash = [f for f in ev["frame_legality"] if f["source"] == "graph"
                 and (f["width"], f["height"], f["length"]) != want]
        if clash:
            ev["frame_legality_verdict"] = "CONTRADICTED"
            raise RouteGate(
                "Gate L: the caller supplied {}x{}x{} and the graph's {} node {} pins "
                "{}x{}x{}. Both are legal, so nothing downstream would notice that the "
                "number in the report is not the number that runs".format(
                    *want, clash[0]["node_class"], clash[0]["node_id"],
                    clash[0]["width"], clash[0]["height"], clash[0]["length"]), ev)

    # · ANDON — a camera trajectory solved for a frame other than the one being generated.
    # See CAMERA_NODES: this defect passes every other clause in this function, and the
    # node's own default length (81) is not this route's (65), so it is one omitted argument
    # away. The andon is put on the direction the other clauses do not bound.
    cams = cameras(graph)
    ev["cameras"] = cams
    if cams:
        graph_frames = {(f["width"], f["height"], f["length"])
                        for f in ev["frame_legality"] if f["source"] == "graph"}
        target = None
        if supplied is not None:
            target = (supplied["width"], supplied["height"], supplied["length"])
        elif len(graph_frames) == 1:
            target = next(iter(graph_frames))

        unchecked = [c for c in cams if not c["checkable"]]
        if unchecked:
            ev["camera_agreement_verdict"] = "INDETERMINATE"
            raise RouteGate(
                "the camera trajectory's frame is UNPROVEN: " + ", ".join(
                    f"node {c['node_id']} ({c['class']}) does not pin width, height and "
                    f"length as literals" for c in unchecked) +
                ". A trajectory whose frame cannot be read cannot be shown to match the "
                "one being generated, and every other clause here passes either way", ev)
        if target is None:
            ev["camera_agreement_verdict"] = "INDETERMINATE"
            raise RouteGate(
                f"the graph carries {len(cams)} camera-trajectory node(s) but no single "
                f"frame to check them against: the graph pins {sorted(graph_frames)} and "
                f"the caller supplied none. Pass frame=(width, height, length) — the "
                f"agreement is the whole point of the check", ev)
        off = [c for c in cams
               if (c["width"], c["height"], c["length"]) != target]
        if off:
            ev["camera_agreement_verdict"] = "CONTRADICTED"
            raise RouteGate(
                "the camera trajectory is solved for a different frame than the one being "
                "generated: " + "; ".join(
                    f"node {c['node_id']} ({c['class']}) is {c['width']}x{c['height']}x"
                    f"{c['length']} against the generated {target[0]}x{target[1]}x"
                    f"{target[2]}" for c in off) +
                ". The run would still produce video, and every other gate would pass on "
                "it", ev)
        ev["camera_agreement_verdict"] = "AGREES"

    # · ANDON — the clause E08 found passing vacuously. "Nothing to check" and "everything
    # checked out" must not be the same verdict. On a hosted tier the honest third answer
    # is INAPPLICABLE: there is no pixel dimension in the graph to check, and the enum
    # clause below is what decides legality instead. It still raises on an illegal enum.
    if hosted_tier is not None:
        if lat:
            raise RouteGate(
                f"verify() was told this is hosted tier {hosted_tier!r}, but the graph "
                f"carries {len(lat)} latent-sizing node(s). One of those two is wrong, and "
                f"the pixel clause would go unchecked either way",
                dict(ev, hosted_tier=hosted_tier))
        found = hosted_enums(graph)
        if not found:
            raise RouteGate(
                f"verify() was told this is hosted tier {hosted_tier!r}, but no node in the "
                f"graph carries that tier's enum inputs. Gate L would then have nothing to "
                f"decide in EITHER clause, which is the vacuous state this argument exists "
                f"to remove", dict(ev, hosted_tier=hosted_tier))
        # EVERY hosted node is graded, and every one is recorded, before anything raises.
        # `hosted_enums` used to return the first match and this branch checked only that
        # tuple: a second node at an illegal resolution, ratio or duration was named
        # nowhere in the evidence.
        rows = [dict(hosted_frame_legality(res, ratio, dur, hosted_tier),
                     source="graph", node_id=nid) for nid, res, ratio, dur in found]
        ev["hosted_frame_legality_nodes"] = rows
        ev["frame_legality_verdict"] = "INAPPLICABLE — hosted tier, enum clause instead"
        ev["frame_legality_inapplicable_reason"] = (
            f"{hosted_tier} receives no width, height or frame count from this graph; the "
            f"pixel rules of family {family!r} decide nothing here, so the tier's own enum "
            f"constraints are checked instead and are reported in `hosted_frame_legality`")
        illegal_rows = [r for r in rows if not r["legal"]]
        if illegal_rows:
            raise RouteGate(
                "Gate L (hosted tier): " + "; ".join(
                    f"node {r['node_id']}: " + "; ".join(r["problems"])
                    for r in illegal_rows), ev)
        if len(rows) > 1:
            # Both legal is not the same as one checked. This tier bills per node, so a
            # graph carrying two of them is one submission and two charges, and a single
            # tier verdict would be the number nobody checked — the argument this
            # function already makes for `frame` and `hosted_tier` together.
            raise RouteGate(
                f"the graph carries {len(rows)} {hosted_tier} node(s) "
                f"({', '.join(str(r['node_id']) for r in rows)}); every one is legal and "
                f"reported in `hosted_frame_legality_nodes`, but one submission carrying "
                f"two billable nodes is two charges against a ceiling counted per "
                f"submission, and one tier verdict cannot describe both", ev)
        tier_ev = rows[0]
        ev["hosted_frame_legality"] = tier_ev
        ev["verdict"] = (
            f"{len(comp)} weight file(s), {seed_phrase}, hosted tier "
            f"{hosted_tier} at {tier_ev['resolution']} {tier_ev['ratio']} "
            f"{tier_ev['duration_s']}s — enum-legal; the pixel clause is inapplicable"
            + (f"; WAIVED components {waived}" if waived else ""))
        return ev

    if not ev["frame_legality"]:
        ev["frame_legality_verdict"] = "INDETERMINATE"
        raise RouteGate(
            f"Gate L is INDETERMINATE on this graph and therefore UNPROVEN: none of its "
            f"{len(lat)} latent-sizing node(s) pins width, height and length as literals, "
            f"and the caller supplied no frame. Measured on E08, 2026-08-12: a graph in "
            f"this state was reported LEGAL having examined zero frames. Pass "
            f"frame=(width, height, length) if you know the shape being generated — the "
            f"gate then checks it against the generator's rules like any other", ev)

    ev["frame_legality_verdict"] = "PROVEN"
    ev["verdict"] = (f"{len(comp)} weight file(s), {seed_phrase}, "
                     f"{ev['latents_checkable']} of {len(lat)} latent(s) checkable, "
                     f"{len(ev['frame_legality'])} frame(s) checked and generator-legal"
                     + (f", {len(cams)} camera trajectory(s) on the generated frame"
                        if cams else "")
                     + (f"; WAIVED components {waived}" if waived else ""))
    return ev


def load_graph(path):
    """A graph from disk, read through the one loader.

    ⚠ **This function used to unwrap `workflow_json` and `workflow` and NOT `prompt` —
    the standard submission envelope.** A file left inside that envelope was returned
    whole, and every clause of `verify` then reported its zero-population verdict as a
    pass (the measurement is on `normalise_graph`). `gate_saved_graph.round_trip` died
    on the same file with `KeyError: 'nodes'`, which is a crash rather than a wrong
    answer and so the good kind of latent bug.

    The unwrap list is now `WRAPPER_KEYS` (== `canon.GRAPH_WRAPPER_KEYS`) and it is read
    through `normalise_graph`, so a file whose shape this module cannot read raises
    `RouteGate` naming the top-level keys instead of being handed on as an empty graph.
    """
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    # The parse used to sit OUTSIDE the try below, so this function's own docstring
    # promise — "raises RouteGate naming the top-level keys" — did not hold for a file
    # that is not JSON at all. Measured 2026-09-04: a file containing `{ not json at all }`
    # raised `json.JSONDecodeError('Expecting property name enclosed in double quotes')`
    # with the path nowhere in the message, and an EMPTY file raised
    # `JSONDecodeError('Expecting value')` because `find` and `rfind` both return -1 and
    # the slice is ''. Neither is an `ArmatureError`, so a caller catching `GateFailure`
    # around a submission step did not catch it and the operator saw a decoder error with
    # no filename.
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise RouteGate(
            f"{path}: contains no JSON object at all "
            f"({len(raw)} character(s) read, no '{{' ... '}}' pair). An empty or "
            f"brace-free file is refused by name rather than parsed as ''",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unparseable_file",
             "path": str(path), "n_chars": len(raw)})
    try:
        doc = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as err:
        raise RouteGate(
            f"{path}: could not parse as JSON: {err}",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unparseable_file",
             "path": str(path), "error": str(err),
             "line": err.lineno, "column": err.colno}) from None
    try:
        return normalise_graph(doc)
    except RouteGate as exc:
        raise RouteGate(
            f"{path}: {exc}",
            dict(exc.evidence or {}, gate="ROUTE", andon="RouteGate",
                 path=str(path))) from None
