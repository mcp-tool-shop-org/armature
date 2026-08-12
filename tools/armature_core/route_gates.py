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

from .errors import GateFailure

TOOL_VERSION = "E09.1"

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
}

#: Node classes that carry a seed, and where it lives in `widgets_values`.
#:
#: `add_noise` is the third entry and it is per-class rather than assumed: `KSamplerAdvanced`
#: carries the switch as its first widget, and **`KSampler` has no such input at all** — it
#: always adds noise. Reading widget 0 for both (which this table let a caller do until
#: 2026-08-12) asks a `KSampler` whether its SEED equals "disable"; the answer is right for
#: the wrong reason on every graph, and would be wrong outright on a class whose first
#: widget happened to be a disabling literal.
SEED_NODES = {
    "KSampler": {"seed": 0, "control": 1, "add_noise": None},
    "KSamplerAdvanced": {"seed": 1, "control": 2, "add_noise": 0},
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


def families_of(filename):
    """Every family a weight filename matches, lower-cased substring test."""
    low = str(filename).lower()
    return sorted(fam for fam, pats in WEIGHT_FAMILIES.items()
                  if any(p in low for p in pats))


def model_weights(graph):
    """Every DIFFUSION-model weight file the graph loads, with the families it matches."""
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
    loaded = model_weights(graph)
    present = sorted({fam for w in loaded for fam in w["families"]})
    cond = [(str(n.get("id")), n.get("type")) for _, n in _iter_nodes(graph)
            if n.get("type") in CONDITIONING_WEIGHT_FAMILY
            or n.get("type") in CONDITIONING_FAMILY_EXEMPT]

    ev = {"gate": "PAIR", "model_weights": loaded, "families_present": present,
          "conditioning_nodes": [{"node_id": i, "class": c,
                                  "requires": CONDITIONING_WEIGHT_FAMILY.get(c)}
                                 for i, c in cond]}

    unknown = sorted({n.get("type") for _, n in _iter_nodes(graph)
                      if isinstance(n.get("type"), str)
                      and n["type"].startswith("Wan") and n["type"].endswith("ToVideo")
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


def is_api_format(graph):
    """API format is node-id keyed with `class_type`; save format has a `nodes` array."""
    if isinstance(graph.get("nodes"), list):
        return False
    return any(isinstance(v, dict) and "class_type" in v for v in graph.values())


def _iter_nodes(graph):
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
    """
    if is_api_format(graph):
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
    for d in (graph.get("definitions") or {}).get("subgraphs") or []:
        for n in d.get("nodes") or []:
            yield (d.get("name") or d.get("id") or "subgraph", n)


def components(graph):
    """Every weight file the graph loads, with the repo's ruling on each."""
    out = []
    for where, n in _iter_nodes(graph):
        for v in (n.get("widgets_values") or []):
            if not isinstance(v, str):
                continue
            if not v.lower().endswith(WEIGHT_SUFFIXES):
                continue
            ruling = None
            for key, rec in RULED_COMPONENTS.items():
                if key in v.lower():
                    ruling = dict(rec, matched_on=key)
                    break
            out.append({"file": v, "node_id": n.get("id"), "class": n.get("type"),
                        "where": where,
                        "ruling": ruling or {"verdict": "NOT IN THIS TABLE",
                                             "reason": "check docs/license-map.md"}})
    return out


#: The input names a seed lives under in API format, per node class.
SEED_INPUTS = {"KSampler": "seed", "KSamplerAdvanced": "noise_seed"}


def seeds(graph):
    """Every seed in the graph and whether it is pinned.

    **Pinned means something different in each format, and both meanings are the honest
    one.** In save format the UI widget `control_after_generate` decides the next run's
    seed, so `randomize` is not pinned however concrete the current number looks. In API
    format that widget does not exist at all: a seed is pinned when it is a literal, and
    unpinned when it arrives over a link from a node that could compute anything.
    """
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        spec = SEED_NODES.get(cls)
        if not spec:
            continue
        if api:
            key = SEED_INPUTS[cls]
            value = (n.get("inputs") or {}).get(key)
            literal = not isinstance(value, list)
            out.append({"node_id": n.get("id"), "class": cls, "where": where,
                        "seed": value if literal else None,
                        "control_after_generate": None,
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
                {"supplied": frame}) from None
    if isinstance(frame, (list, tuple)) and len(frame) == 3:
        return int(frame[0]), int(frame[1]), int(frame[2])
    raise RouteGate(
        f"the supplied frame {frame!r} is not (width, height, length) or a mapping "
        f"carrying those three keys", {"supplied": frame})


def frame_legality(width, height, length, family="wan"):
    """Gate L, standalone: is this frame legal for that generator? Derive, then round.

    Returns the verdict and, when illegal, the nearest legal value in each direction — so a
    caller rounds to a stated number instead of guessing one.
    """
    rules = GENERATOR_RULES.get(family)
    if rules is None:
        raise RouteGate(f"no recorded frame rules for generator family {family!r}; the "
                        f"constraint is recorded per model in the spec that first uses it",
                        {"known": sorted(GENERATOR_RULES)})
    m = rules["dim_multiple"]
    problems = []
    if width % m:
        problems.append(f"width {width} is not a multiple of {m} "
                        f"(nearest: {m * round(width / m)})")
    if height % m:
        problems.append(f"height {height} is not a multiple of {m} "
                        f"(nearest: {m * round(height / m)})")
    if (length - 1) % 4:
        problems.append(f"length {length} is not of the form 4n+1 "
                        f"(nearest: {4 * round((length - 1) / 4) + 1})")
    if length > rules["max_frames"]:
        problems.append(f"length {length} exceeds the {rules['max_frames']}-frame "
                        f"trained horizon")
    return {"gate": "L", "family": family, "width": width, "height": height,
            "length": length, "rules": rules, "problems": problems,
            "legal": not problems}


def gate_s_registration(graph, registered):
    """Gate S · ANDON — every seed about to run was pre-registered in a committed list.

    E04's andon, and it guards a failure with no technical symptom at all: every other gate
    passes on a seed-shopped run, and what is wrong is epistemic. A rule forbids; a list
    removes the possibility, and git timestamps the list ahead of the artifacts it governs.

    It binds in **both** directions. An unregistered seed is the obvious clause. A
    registered list that the graph does not draw from is the second: a graph running some
    other number while a tidy list sits in the repo is the same defect wearing a receipt.
    """
    found = seeds(graph)
    reg = list(registered or [])
    ev = {"gate": "S", "registered": reg, "seeds": found}
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
    ev["verdict"] = (f"{len(live)} noise-bearing seed(s), all pinned and all drawn from "
                     f"the committed list of {len(reg)}")
    return ev


def verify(graph, *, family="wan", require_pinned_seeds=True, allow=(), frame=None):
    """The three questions at once. Raises on anything the record already ruled against.

    `allow` names component keys the caller has an explicit ruling for — it is not a skip
    flag, because a component named here still appears in the returned evidence with its
    verdict, so the report cannot omit that it ran.

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
    ev = {"gate": "ROUTE", "components": comp, "seeds": sd, "latents": lat,
          "latents_checkable": sum(1 for l in lat if l["checkable"]),
          "frame_legality": legality}

    bad = [c for c in comp
           if c["ruling"]["verdict"] in ("BANNED", "EXCLUDED")
           and c["ruling"].get("matched_on") not in allow]
    if bad:
        raise RouteGate(
            "the graph loads " + ", ".join(
                f"{c['file']!r} ({c['ruling']['verdict']}: {c['ruling']['reason']})"
                for c in bad) +
            ". The licence map's ruling is that presence is presence — a bypassed node "
            "still counts, and these are not even bypassed", ev)

    # · ANDON — Gate PAIR. Placed after the licence clause (a banned weight stays the
    # headline) and before everything else, because every clause below is a question about
    # the graph's internal consistency and this one is the only question about whether the
    # model can receive what the graph wires at it. Wave 2 was internally consistent.
    ev["pairing"] = pairing(graph)

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
    # checked out" must not be the same verdict.
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
    ev["verdict"] = (f"{len(comp)} weight file(s), {len(sd)} seed(s) all pinned, "
                     f"{ev['latents_checkable']} of {len(lat)} latent(s) checkable, "
                     f"{len(ev['frame_legality'])} frame(s) checked and generator-legal"
                     + (f", {len(cams)} camera trajectory(s) on the generated frame"
                        if cams else ""))
    return ev


def load_graph(path):
    """A save-format graph from disk, tolerating a tool-result wrapper around the JSON."""
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    doc = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    for key in ("workflow_json", "workflow"):
        if isinstance(doc.get(key), dict):
            return doc[key]
    return doc
