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
SEED_NODES = {
    "KSampler": {"seed": 0, "control": 1},
    "KSamplerAdvanced": {"seed": 1, "control": 2},
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
#: Widget order for `WanAnimateToVideo` is read from its `define_schema` declaration order,
#: keeping only the non-link inputs: width, height, length, batch_size,
#: continue_motion_max_frames, video_frame_offset.
LATENT_NODES = {
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2},
    "EmptyLatentVideo": {"width": 0, "height": 1, "length": 2},
    "WanVaceToVideo": {"width": 0, "height": 1, "length": 2},
    "WanAnimateToVideo": {"width": 0, "height": 1, "length": 2},
}

#: Widget values that name a weight file. Anything ending in one of these is a component.
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".sft", ".gguf", ".task")


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
    """Every video latent's width, height and frame count."""
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
        out.append(rec)
    return out


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
    live = []
    for s in found:
        n = next((x for _, x in _iter_nodes(graph) if str(x.get("id")) == str(s["node_id"])),
                 None)
        adds = True
        if n is not None:
            inp = n.get("inputs") or {}
            wv = n.get("widgets_values") or []
            adds = (inp.get("add_noise", wv[0] if wv else "enable")) not in ("disable", False)
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


def verify(graph, *, family="wan", require_pinned_seeds=True, allow=()):
    """The three questions at once. Raises on anything the record already ruled against.

    `allow` names component keys the caller has an explicit ruling for — it is not a skip
    flag, because a component named here still appears in the returned evidence with its
    verdict, so the report cannot omit that it ran.
    """
    comp = components(graph)
    sd = seeds(graph)
    lat = latents(graph)
    ev = {"gate": "ROUTE", "components": comp, "seeds": sd, "latents": lat,
          "frame_legality": [frame_legality(l["width"], l["height"], l["length"], family)
                             for l in lat
                             if None not in (l["width"], l["height"], l["length"])]}

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

    ev["verdict"] = (f"{len(comp)} weight file(s), {len(sd)} seed(s) all pinned, "
                     f"{len(lat)} latent(s) all generator-legal")
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
