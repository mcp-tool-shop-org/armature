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

#: Node classes that size a video latent, and where width/height/length live.
LATENT_NODES = {
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2},
    "EmptyLatentVideo": {"width": 0, "height": 1, "length": 2},
}

#: Widget values that name a weight file. Anything ending in one of these is a component.
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".sft", ".gguf", ".task")


class RouteGate(GateFailure):
    """A graph was about to run that the repo's own record says it must not."""

    gate = "ROUTE"


def _iter_nodes(graph):
    """Every node in a save-format graph, INCLUDING the ones inside subgraph definitions.

    The clause that matters. A served template can present four nodes at the top level and
    hide thirty inside a subgraph blueprint, and a check that walked only the top level
    would report a clean graph while the excluded LoRA sat two levels down. Measured on
    `video_wan2_2_14B_t2v`, 2026-08-11: 4 nodes visible, 30 hidden.
    """
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


def seeds(graph):
    """Every seed in the graph and whether it is pinned or randomises."""
    out = []
    for where, n in _iter_nodes(graph):
        spec = SEED_NODES.get(n.get("type"))
        if not spec:
            continue
        wv = n.get("widgets_values") or []
        seed = wv[spec["seed"]] if len(wv) > spec["seed"] else None
        control = wv[spec["control"]] if len(wv) > spec["control"] else None
        out.append({"node_id": n.get("id"), "class": n.get("type"), "where": where,
                    "seed": seed, "control_after_generate": control,
                    "pinned": control == "fixed"})
    return out


def latents(graph):
    """Every video latent's width, height and frame count."""
    out = []
    for where, n in _iter_nodes(graph):
        spec = LATENT_NODES.get(n.get("type"))
        if not spec:
            continue
        wv = n.get("widgets_values") or []
        out.append({"node_id": n.get("id"), "class": n.get("type"), "where": where,
                    "width": wv[spec["width"]] if len(wv) > spec["width"] else None,
                    "height": wv[spec["height"]] if len(wv) > spec["height"] else None,
                    "length": wv[spec["length"]] if len(wv) > spec["length"] else None})
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
