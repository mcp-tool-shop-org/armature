#!/usr/bin/env python
"""gate_saved_graph — run admission on the SAVED file, and compare it to what we built.

    python tools/gate_saved_graph.py --saved=outputs/E09/route2/E09-B2-A3-t2v.saved.json \
                                     --api=outputs/E09/route2/E09-B2-A3-t2v.api.json \
                                     --seeds=specs/E09-A3-seeds.json \
                                     --out=outputs/E09/route2/E09-B2-A3-saved-admission.json

Why this exists as its own step. The cloud does not execute the API graph this repo builds;
it executes the SAVED graph, after a save->convert round trip that synthesises positions,
links and slot arrays. That round trip is a place a value can change, and CLAUDE.md's law is
that a `dry_run` PASS does not prove link sanity — so the file that will actually run is
gated in code, on its own bytes, before anything is submitted.

Two checks, and they answer different questions:

* **admission** — Gate ROUTE / S / L on the saved graph. Save format has a meaning API format
  does not: `control_after_generate`. A seed that reads `randomize` there is unpinned however
  concrete the number looks, and Gate S refuses it.
* **round-trip equality** — every value we wrote, found again in the saved file. A gate that
  passes on a graph which quietly lost the frame size or swapped an expert is a gate that
  passed on the wrong object.

Raises in-tool on any disagreement. Nothing here submits anything.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)

TOOL_VERSION = "E10.1"

#: Where each API-format input lands in a save-format node's `widgets_values`. Written out
#: rather than zipped positionally, because the whole point is to catch a positional slip.
WIDGET_INDEX = {
    # ---- E10, 2026-08-12: the Animate route's classes. `KSampler` has the same
    # control_after_generate insertion `KSamplerAdvanced` does, one slot earlier, which is
    # the shift a positional zip would sail past for the second time.
    "KSampler": {"seed": 0, "steps": 2, "cfg": 3, "sampler_name": 4, "scheduler": 5,
                 "denoise": 6},
    "WanAnimateToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3,
                          "continue_motion_max_frames": 4, "video_frame_offset": 5},
    # ---- E11, 2026-08-12: the I2V route's conditioning node. Four widgets, not six: its
    # schema carries no `continue_motion_max_frames` / `video_frame_offset` at all, so a
    # table entry copied from the Animate row would look right and compare `batch_size`
    # against nothing.
    "WanImageToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    "LoadImage": {"image": 0},
    # Every input this graph pins is a link; the empty entry is a recorded fact, not the
    # silence of a class nobody thought about (the table is looked up with `is None`).
    "TrimVideoLatent": {},
    "UNETLoader": {"unet_name": 0, "weight_dtype": 1},
    "ModelSamplingSD3": {"shift": 0},
    "CLIPLoader": {"clip_name": 0, "type": 1, "device": 2},
    "VAELoader": {"vae_name": 0},
    "CLIPTextEncode": {"text": 0},
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    # save format inserts `control_after_generate` at index 2, which API format has no slot
    # for at all — so every index after the seed is shifted by one. This is exactly the
    # kind of off-by-one that a positional zip would sail past.
    "KSamplerAdvanced": {"add_noise": 0, "noise_seed": 1, "steps": 3, "cfg": 4,
                         "sampler_name": 5, "scheduler": 6, "start_at_step": 7,
                         "end_at_step": 8, "return_with_leftover_noise": 9},
    # Every input is a link, so there is nothing to compare — but the entry is present
    # ON PURPOSE. The table is looked up with `is None`, so an absent class halts and an
    # empty one passes: "this node has no literal widgets" is a recorded fact here, not the
    # silence of a node nobody thought about. (Caught by this check firing on its own hole
    # before the first submission, 2026-08-12.)
    "VAEDecode": {},
    "CreateVideo": {"fps": 0, "bit_depth": 1},
    "SaveImage": {"filename_prefix": 0},
    "SaveVideo": {"filename_prefix": 0, "format": 1, "codec": 2},
    # E11 wave 2's camera tier. **These two rows were written because this check HALTED the
    # wave-2 submission on its own hole** — the second time it has done so, after the
    # `VAEDecode` case recorded above, and both times before a credit was spent rather than
    # after. The gate refused to skip a class it had no row for, which is the entire point
    # of looking the table up with `is None`.
    #
    # Unlike every row above, these indices are not a derivation: they were READ OFF the
    # save-format file the cloud converted, 2026-08-12 —
    # `WanCameraEmbedding.widgets_values == ["Static", 832, 480, 65, 1, 0.5, 0.5, 0.5, 0.5]`
    # and `WanCameraImageToVideo.widgets_values == [832, 480, 65, 1]`. That makes them the
    # empirical SECOND reading that `route_gates.LATENT_NODES` promised and could not supply
    # from a served template, and they agree with the `get_node` schema order that
    # `route_gates.CAMERA_NODES` was derived from. Neither class takes a
    # `control_after_generate` insertion — that shift is particular to the sampler above.
    "WanCameraEmbedding": {"camera_pose": 0, "width": 1, "height": 2, "length": 3,
                           "speed": 4, "fx": 5, "fy": 6, "cx": 7, "cy": 8},
    "WanCameraImageToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    # ---- S03, 2026-08-13: the assembly chain's batch node. Every input is a dotted
    # COMFY_AUTOGROW_V3 link (`images.image0` …), so there is no literal to compare and the
    # row is empty — a recorded fact, exactly as `VAEDecode` and `TrimVideoLatent` above,
    # because the table is looked up with `is None` and an ABSENT class halts the check.
    #
    # This row is added by the spec that actually EXECUTES the class. E13's executor was
    # ruled correct for declining to teach this table for a route that submitted nothing:
    # a green row for an untravelled path marks it walked. `CreateVideo`, `SaveVideo` and
    # `LoadImage` — the assembly chain's other three classes — already carried rows above,
    # so this is the only one S03 adds.
    "BatchImagesNode": {},
    # ---- E13's re-arm, 2026-08-13: the composed route's hosted generator. The spec owed
    # this row to "the first spec that arms this tier", and the halt-era executor was ruled
    # correct for declining to write it for a route that submitted nothing.
    #
    # **Read off the file the cloud converted**, not derived — the standard the camera rows
    # were held to. The converted node's widgets_values are:
    #   ["wan2.7-r2v", <prompt>, <negative>, "720P", "16:9", 5, 2026081351, "fixed", false]
    # and the `get_node` declaration order (model, prompt, negative_prompt, resolution,
    # ratio, duration, seed, watermark, with the IMAGE/VIDEO reference slots dropped as
    # links) agrees with it — two readings, required to agree, and they do.
    #
    # ⚠ `control_after_generate` is inserted at index 7, immediately after the seed, which
    # shifts `watermark` from the 7 a positional zip would give it to 8. That is exactly the
    # off-by-one this table exists to catch, and it is the third class in it to carry the
    # insertion after the two samplers.
    "Wan2ReferenceVideoApi": {"model": 0, "model.prompt": 1, "model.negative_prompt": 2,
                              "model.resolution": 3, "model.ratio": 4, "model.duration": 5,
                              "seed": 6, "watermark": 8},
}


def _same_value(got, value):
    """Exact equality for a pinned widget value. No widening, in either direction.

    ⚠ **The predicate used to be `got == value or (isinstance(got, (int, float)) and
    isinstance(value, (int, float)) and float(got) == float(value))`, and that `float()`
    clause makes two integers above 2**53 compare EQUAL when they are not.** Measured
    2026-09-04: built 18446744073709551615 against saved 18446744073709551614 gives
    `got == value` False and `float(got) == float(value)` True, so `same` was True; driven
    through `round_trip` on a `Wan2ReferenceVideoApi` node built from this module's own
    `WIDGET_INDEX` row it returned n_values_compared=3, all_equal=True, carrying
    `{'input': 'seed', 'built': ...615, 'saved': ...614, 'equal': True}` in its own
    evidence list. ComfyUI seeds are 64-bit and `specs/E09-seeds.json` records a served
    seed of 923510416338945, so the range is not hypothetical; a route pinning a 64-bit
    seed would get "every value round-tripped" from the last gate before a paid submission
    while the cloud executed a different number from the one the record names.

    Plain `==` needs no widening clause to do the job the widening clause was standing in
    for: Python compares `int` against `float` EXACTLY (`832 == 832.0` is True and
    `2**64 - 1 == float(2**64 - 1)` is False), so a converter that wrote `832.0` where we
    pinned `832` still round-trips.

    `bool` is guarded explicitly because `True == 1` and `False == 0` under `==`, so the
    two spellings are indistinguishable to a comparison that does not ask. No float widget
    in `WIDGET_INDEX` is served at a tolerance today, so none is granted one here; a widget
    that genuinely needs one gets it by NAME, never by a blanket coercion.
    """
    if isinstance(got, bool) != isinstance(value, bool):
        return False
    return got == value


def _as_saved_graph(doc, path=None):
    """A save-format graph, read through THE loader, or a refusal that names the format.

    Wave 8, F-4c5f67de. `round_trip` and `link_round_trip` each opened with
    `{str(n["id"]): n for n in saved_graph["nodes"]}` — a direct read that DISAGREED with
    `route_gates.normalise_graph` on the same input. Measured 2026-09-04:
    `round_trip({'workflow': <save doc>}, ...)` and `round_trip({'prompt': <save doc>}, ...)`
    each raised a bare `KeyError: 'nodes'`, and so did an API-format doc passed as the saved
    argument, while `normalise_graph` unwraps both wrappers to a readable save-format graph.
    Two exported functions and the module's own loader answered differently about one file.

    So both functions normalise their own argument here, and the boundary block `main` has
    carried since 2026-09-03 becomes this one implementation rather than a second.
    """
    doc = RG.normalise_graph(doc)
    if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
        keys = sorted(map(str, doc)) if isinstance(doc, dict) else []
        where = f"{path} is" if path else "the saved graph argument is"
        raise RG.RouteGate(
            f"{where} not a save-format graph: it carries no `nodes` list. Its "
            f"top-level keys are {keys}; the loader unwraps "
            f"{list(UNWRAPPED_BY_LOAD_GRAPH)} and hands anything else back as the wrapper "
            f"it found. Paste the workflow itself, not the tool result around it",
            {"gate": "SAVED_ADMISSION", "andon": "not_a_save_format_graph",
             "path": os.path.abspath(path) if path else None, "top_level_keys": keys,
             "unwrapped_by_load_graph": list(UNWRAPPED_BY_LOAD_GRAPH),
             "clause": "not_a_save_format_graph"})
    return doc


def _as_api_graph(doc, path=None):
    """An API-format graph, read through THE loader, or a refusal that names the format.

    The mirror of `_as_saved_graph`, and the clause `--api` never had. Measured 2026-09-04
    before it existed: an api file wrapped as `{'prompt': {...}}` — the standard submission
    envelope, and a shape the loader knows how to unwrap — raised `KeyError: 'class_type'`
    out of `round_trip`; an api file in SAVE format raised `TypeError: list indices must be
    integers or slices, not str`. Both surfaced as SAVED_ADMISSION_HALT with a stdlib key
    or type name standing in for a sentence, on the last gate before a paid submission.
    """
    doc = RG.normalise_graph(doc)
    if not RG.is_api_format(doc):
        keys = sorted(map(str, doc)) if isinstance(doc, dict) else []
        where = f"{path} is" if path else "the api graph argument is"
        raise RG.RouteGate(
            f"{where} not an API-format graph: its values carry no `class_type`. Its "
            f"top-level keys are {keys}; a `nodes` list means this is the SAVE format and "
            f"the two arguments are the wrong way round. The loader unwraps "
            f"{list(UNWRAPPED_BY_LOAD_GRAPH)}, so a submission envelope is read for you",
            {"gate": "SAVED_ADMISSION", "andon": "not_an_api_format_graph",
             "path": os.path.abspath(path) if path else None, "top_level_keys": keys,
             "unwrapped_by_load_graph": list(UNWRAPPED_BY_LOAD_GRAPH),
             "clause": "not_an_api_format_graph"})
    return doc


def round_trip(api_graph, saved_graph):
    """Every pinned value we wrote, found again in the saved file. Raises on any mismatch."""
    api_graph = _as_api_graph(api_graph)
    saved_graph = _as_saved_graph(saved_graph)
    saved_by_id = {str(n["id"]): n for n in saved_graph["nodes"]}
    checked, problems = [], []
    for node_id, node in api_graph.items():
        s = saved_by_id.get(str(node_id))
        if s is None:
            problems.append(f"node {node_id} ({node['class_type']}) is absent from the "
                            f"saved file")
            continue
        if s["type"] != node["class_type"]:
            problems.append(f"node {node_id}: built {node['class_type']}, saved {s['type']}")
            continue
        index = WIDGET_INDEX.get(node["class_type"])
        if index is None:
            problems.append(f"no widget index recorded for {node['class_type']}; add one "
                            f"rather than skipping the node")
            continue
        wv = s.get("widgets_values") or []
        for name, value in node["inputs"].items():
            if isinstance(value, list):
                continue                      # a link, not a literal
            if name not in index:
                problems.append(f"node {node_id}.{name} has no recorded widget slot")
                continue
            i = index[name]
            if i >= len(wv):
                problems.append(f"node {node_id}.{name} expected at widget {i}, but the "
                                f"saved node has {len(wv)} widgets")
                continue
            got = wv[i]
            same = _same_value(got, value)
            checked.append({"node": node_id, "input": name, "built": value, "saved": got,
                            "equal": bool(same)})
            if not same:
                problems.append(f"node {node_id}.{name}: built {value!r}, saved {got!r}")
    extra = sorted(set(saved_by_id) - {str(k) for k in api_graph})
    if extra:
        problems.append(f"the saved file carries nodes we did not build: {extra}")
    if problems:
        raise RG.RouteGate(
            "the saved file is not the graph this repo built: " + "; ".join(problems),
            {"checked": checked, "problems": problems})
    return {"n_values_compared": len(checked), "all_equal": True, "values": checked}


#: The wrapper keys `route_gates.load_graph` unwraps. Read off the loader where it
#: publishes them, so a widening there is reported here rather than re-typed: core-gates
#: owns the ONE loader (wave 6), and this tool refuses by name whatever it hands back
#: without a `nodes` list.
UNWRAPPED_BY_LOAD_GRAPH = tuple(getattr(RG, "WRAPPER_KEYS", ("workflow_json", "workflow")))


def link_table(saved_graph):
    """`{link_id: (origin_node_id, origin_slot)}` off the saved file's OWN link table.

    Save format records every edge twice: once as a `link` id on the target socket, and
    once in the top-level `links` array as
    `[id, origin_node, origin_slot, target_node, target_slot, type]`. Until 2026-09-04
    `link_round_trip` read only the first of those, so `slot.get("link") is not None` was
    satisfied by ANY link id and the array was never resolved anywhere in this module.
    Measured on a `WanCameraImageToVideo` fixture: an as-built save and one with its two
    same-type CONDITIONING links CROSSED produced byte-identical output from both gates.

    Returns `None` when the file declares no table at all — the caller decides, because a
    file with no links needs none and a file with links needs one.

    ⚠ **The table used to be built by a last-write-wins assignment with no duplicate
    clause**, so a file whose own `links` array declared the same link id twice with
    different origins resolved to whichever entry came last and discarded the other
    unexamined. Measured 2026-09-04 on a `WanImageToVideo` fixture in this repo's own API
    shape (30 = positive encoder, 31 = negative, 49 the conditioning node): a links array
    of `[[6,'31',0,49,0],[6,'30',0,49,0],[7,'31',0,49,1]]` — link 6 declared first from the
    NEGATIVE encoder, then from the positive — returned `{'n_links': 2, 'links':
    ['49.negative','49.positive'], 'optional_sockets_empty_in_both': []}` with no halt.
    This is the crossed-links family one level down: the table is resolved now, but its
    internal consistency was not, so a file that is AMBIGUOUS about where its conditioning
    comes from was admitted by the last gate before credits are spent. A repeat that agrees
    with itself is not a defect and is admitted.
    """
    raw = saved_graph.get("links")
    if raw is None:
        return None
    table = {}
    for entry in raw:
        if isinstance(entry, dict):
            lid = entry.get("id")
            origin, slot = entry.get("origin_id"), entry.get("origin_slot")
        elif isinstance(entry, (list, tuple)) and len(entry) >= 3:
            lid, origin, slot = entry[0], entry[1], entry[2]
        else:
            raise RG.RouteGate(
                f"the saved file's link table carries an entry this tool cannot read: "
                f"{entry!r}. A table that is skipped is a table that vouches for nothing, "
                f"and the origin of every link in this file would go unchecked",
                {"entry": entry, "n_entries": len(raw)})
        if lid is None or origin is None:
            raise RG.RouteGate(
                f"the saved file's link table entry {entry!r} names no link id or no "
                f"origin node", {"entry": entry, "n_entries": len(raw)})
        resolved = (str(origin), slot)
        prior = table.get(str(lid))
        if prior is not None and prior != resolved:
            raise RG.RouteGate(
                f"the saved file's link table declares link {lid!r} TWICE with different "
                f"origins — node {prior[0]} slot {prior[1]!r} and node {resolved[0]} slot "
                f"{resolved[1]!r}. Which one a socket carrying that id resolves to is an "
                f"accident of array order, and a file that is ambiguous about where its "
                f"conditioning comes from is not a file this gate can vouch for",
                {"gate": "SAVED_ADMISSION", "andon": "duplicate_link_id",
                 "link_id": str(lid), "origins": [list(prior), list(resolved)],
                 "n_entries": len(raw), "clause": "duplicate_link_id"})
        table[str(lid)] = resolved
    return table


def _origin_problems(node_id, name, link_id, ours, table, saved_by_id):
    """Where a link COMES FROM, compared to where we built it coming from.

    Four clauses, each its own sentence in the halt: no table to resolve against, a link
    id the table does not carry, an origin node the saved file never declares, and an
    origin node/slot that is not the one we wired.
    """
    if table is None:
        return [f"node {node_id}.{name} carries link {link_id!r} and the saved file "
                f"declares no link table, so where that link comes from cannot be "
                f"resolved and no origin in this file is checkable"]
    if str(link_id) not in table:
        return [f"node {node_id}.{name}: link {link_id!r} is not in the saved file's own "
                f"link table ({sorted(table)}), so it resolves to nothing"]
    origin, origin_slot = table[str(link_id)]
    problems = []
    if origin not in saved_by_id:
        problems.append(
            f"node {node_id}.{name}: link {link_id!r} names origin node {origin}, which "
            f"the saved file does not declare")
    want_node, want_slot = str(ours[0]), ours[1]
    if origin != want_node or origin_slot != want_slot:
        problems.append(
            f"node {node_id}.{name}: we wired it from node {want_node} slot {want_slot!r}, "
            f"and the saved file's link {link_id!r} comes from node {origin} slot "
            f"{origin_slot!r}")
    return problems


def link_round_trip(api_graph, saved_graph):
    """Every socket we wired is wired there, and every socket we left empty is empty there.

    The value round trip above compares literals; this compares TOPOLOGY, and it is the
    clause E08 checked by eye. The failure it guards is specific and silent: a save/convert
    round trip that attached something to `background_video` would produce a graph that
    runs, costs the same, and makes the scene-from-prompt clause unmeasurable — while every
    widget value still matched. It binds in both directions for the same reason Gate S
    does: a lost link and an invented link are different defects and both pass a
    value-only comparison.

    **The comparison walks the UNION of both socket lists, and that is a correction.**
    Until 2026-09-03 it iterated the SAVED node's sockets only, so the third defect —
    a socket we wired that the round trip removed ENTIRELY — was never visited, and the
    "we wired it and the saved file carries no link" branch could not run for it. Measured
    on a two-node fixture wiring `49.control_video`: with the socket present and its link
    null the gate raised; with the socket absent it returned `n_links: 0` and a clean
    verdict, and the value round trip returned `all_equal: True` beside it, because it
    skips list-valued inputs as links. Both checks passed a graph the cloud would execute
    with a conditioning link gone.

    **The link IDS are resolved against the saved file's own table, and that is the second
    correction.** Until 2026-09-04 the only thing read off a saved socket was
    `slot.get("link") is not None`, so `we_linked and they_linked` was satisfied by any
    link id at all and `saved_graph["links"]` was resolved nowhere in this module. Measured
    on a `WanCameraImageToVideo` fixture built from this repo's own CAMERA_API shape: the
    as-built save (`positive` <- 6 from node 30, `negative` <- 7 from node 31) and one with
    the two CROSSED, table and all, returned EQUAL values from both gates — 13 values
    compared, all_equal, and the identical `links` list. A conditioning swap, a reference
    video re-pointed at another node, and a link naming a node the file does not declare
    were all invisible on the last gate before credits are spent.

    Both arguments are read through THE loader (`_as_api_graph` / `_as_saved_graph`), so a
    wrapped or wrong-way-round doc is refused by a named format clause rather than by a
    stdlib `KeyError` — see `_as_saved_graph`.
    """
    api_graph = _as_api_graph(api_graph)
    saved_graph = _as_saved_graph(saved_graph)
    saved_by_id = {str(n["id"]): n for n in saved_graph["nodes"]}
    table = link_table(saved_graph)
    wired, empty, problems = [], [], []
    for node_id, node in api_graph.items():
        s = saved_by_id.get(str(node_id))
        if s is None:
            continue                                  # `round_trip` already raised on this
        saved_slots = {slot.get("name"): slot for slot in (s.get("inputs") or [])}
        names = list(saved_slots) + [n for n in node["inputs"] if n not in saved_slots]
        for name in names:
            ours = node["inputs"].get(name)
            we_linked = isinstance(ours, list)
            slot = saved_slots.get(name)
            if slot is None:
                # A name only WE carry. A literal belongs to `round_trip`; a LINK means the
                # save/convert round trip deleted the socket we wired.
                if we_linked:
                    problems.append(
                        f"node {node_id}.{name}: we wired it and the saved file declares "
                        f"no socket for it at all — the link is not null, it is gone, and "
                        f"a comparison that walks only the saved node's sockets never "
                        f"visits this name")
                continue
            they_linked = slot.get("link") is not None
            if we_linked and not they_linked:
                problems.append(f"node {node_id}.{name}: we wired it and the saved file "
                                f"carries no link")
            elif they_linked and not we_linked:
                problems.append(f"node {node_id}.{name}: the saved file wired it and we "
                                f"left it empty")
            elif we_linked:
                wired.append(f"{node_id}.{name}")
                problems.extend(_origin_problems(node_id, name, slot.get("link"), ours,
                                                 table, saved_by_id))
            else:
                empty.append(f"{node_id}.{name}")
    if problems:
        raise RG.RouteGate(
            "the saved file's topology is not the topology this repo built: "
            + "; ".join(problems),
            {"wired": wired, "empty_in_both": empty, "problems": problems})
    return {"n_links": len(wired), "links": sorted(wired),
            "optional_sockets_empty_in_both": sorted(empty)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", required=True)
    ap.add_argument("--api", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--experiment", default="E09")
    ap.add_argument("--stage", default="B2")
    ap.add_argument("--hosted-tier", default=None,
                    help="a tier from route_gates.HOSTED_TIER_RULES whose graph carries no "
                         "pixel dimension at all (wan2.7-r2v). Gate L's pixel clause is "
                         "INAPPLICABLE there, not skipped: the tier's own enum constraints "
                         "are checked instead and an illegal one still raises")
    ap.add_argument("--frame", default=None,
                    help="width,height,length — the shape the caller knows it is "
                         "generating. Gate L is INDETERMINATE and raises on a graph whose "
                         "latent it cannot read, so a route whose conditioning node sizes "
                         "its own latent states the shape here (argparse eats leading "
                         "minus signs: pass as --frame=832,480,81)")
    a = ap.parse_args(argv)

    saved = RG.load_graph(a.saved)
    # Refuse by NAME at the boundary. `load_graph` unwraps a known key list and hands back
    # anything else as the wrapper dict, and `round_trip`'s first statement then raised a
    # bare `KeyError: 'nodes'` — no gate id, no evidence, a stdlib key name standing in for
    # a sentence. What makes it load-bearing rather than merely ugly, measured 2026-09-04:
    # on the SAME wrapped doc `RG.verify` returns "0 weight file(s), 0 seed(s) all pinned,
    # 0 of 0 latent(s) checkable" and `RG.gate_s_registration` returns "0 noise-bearing
    # seed(s), all pinned", because `_iter_nodes` reads a wrapper-key doc as no nodes. The
    # KeyError was the only thing between a wrapped file and a SAVED_ADMISSION_OK over a
    # graph nothing examined. `round_trip`'s indexing stays strict below this line.
    #
    # Wave 8, F-4c5f67de: the block is `_as_saved_graph` now — ONE implementation, shared
    # with `round_trip` and `link_round_trip`, which used to read `saved_graph["nodes"]`
    # directly and disagree with the loader about the same file.
    saved = _as_saved_graph(saved, path=a.saved)
    # `--api` gets the MIRROR of that boundary, which it never had: it was a bare
    # `json.load` with no format check at all, two lines below a `--saved` refused by name.
    api = _as_api_graph(RG.load_graph(a.api), path=a.api)
    with open(a.seeds, encoding="utf-8") as fh:
        registered = json.load(fh)["seeds"]

    frame = None
    if a.frame:
        parts = [int(v) for v in a.frame.split(",")]
        if len(parts) != 3:
            raise RG.RouteGate(f"--frame={a.frame!r} is not width,height,length; two out "
                               f"of three proves nothing", {"supplied": a.frame})
        frame = tuple(parts)

    equality = round_trip(api, saved)                       # 0 — is it even our graph
    topology = link_round_trip(api, saved)                  # 0b — is it wired as we wired it
    gate_route = RG.verify(saved, frame=frame, hosted_tier=a.hosted_tier)   # 1
    gate_s = RG.gate_s_registration(saved, registered)      # 2
    checked = [f for f in gate_route["frame_legality"]]     # 3 — already raised if illegal
    if a.hosted_tier:
        # The honest Gate L line for a tier that has no pixels to report.
        t = gate_route["hosted_frame_legality"]
        shapes = [f"{t['resolution']} {t['ratio']} {t['duration_s']}s"]
    else:
        shapes = sorted({f"{f['width']}x{f['height']}x{f['length']}" for f in checked})

    record = {
        "tool": "gate_saved_graph", "tool_version": TOOL_VERSION,
        "experiment": a.experiment, "stage": a.stage,
        "saved_file": {"path": os.path.abspath(a.saved),
                       "sha256": hashlib.sha256(open(a.saved, "rb").read()).hexdigest()},
        "api_file": {"path": os.path.abspath(a.api),
                     "sha256": hashlib.sha256(open(a.api, "rb").read()).hexdigest()},
        "round_trip": equality,
        "topology_round_trip": topology,
        "gates": {"ROUTE": gate_route, "S": gate_s, "L": checked},
    }
    # BELOW every check, not above them. `build_payload.py` states the repo's invariant —
    # a refuse must leave no output directory — and until 2026-09-03 it held for Gate CANON
    # alone: this tool created the directory before the round trip, the topology comparison
    # and Gates ROUTE / S / L, so a halted admission left an empty directory beside real
    # ones, to be read later as a run that happened.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print("SAVED_ADMISSION_OK " + json.dumps({
        "round_trip_values_compared": equality["n_values_compared"],
        "links_compared": topology["n_links"],
        "optional_sockets_empty_in_both": topology["optional_sockets_empty_in_both"],
        "gate_ROUTE": gate_route["verdict"], "gate_S": gate_s["verdict"],
        "gate_L": f"{', '.join(shapes)} legal ({gate_route['frame_legality_verdict']})",
        "record": a.out}))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `SAVED_ADMISSION_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("SAVED_ADMISSION_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
