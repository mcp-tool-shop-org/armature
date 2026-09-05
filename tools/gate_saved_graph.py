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
from armature_core.route_gates import RouteGate  # noqa: E402
from build_assembly_payload import read_seed_registration  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)

TOOL_VERSION = "E10.1"


class SavedAdmission(RouteGate):
    """Gate SAVED_ADMISSION, raised under its own id.

    Wave 18, F-c11410c5. Five refusals in the last gate before a paid submission named TWO
    different gate ids for one event: the class raised was `RG.RouteGate`, whose class
    attribute is `gate = "ROUTE"` — so `str(exc)` opened `[ROUTE]` and `exc.gate` read
    `"ROUTE"` — while the evidence dict beside it said `{"gate": "SAVED_ADMISSION"}`, and
    the `__main__` block prints both into one `SAVED_ADMISSION_HALT` line. Measured by AST
    census over the builders domain, comparing each raise's evidence `gate` literal against
    the raised class's `gate` attribute: 5 sites, all in this file — :180
    `not_a_save_format_graph`, :206 `not_an_api_format_graph`, :323 `duplicate_link_id`,
    :445 `duplicate_socket_name`, :716 `frame_not_three_integers`. Two of the five were
    ADDED in wave 16, AFTER `build_r2v_payload.SpendCeiling` recorded the rule in its own
    docstring. A wrapper or a later session triaging a halt at the spend boundary keys on
    whichever id it read first and looks for a gate that did not fire.

    This is the fix wave 16 applied one file over, carried here: the id gets an owner.
    Declared with a PLAIN-NAME base rather than `RG.RouteGate`, because F-d8593862 measured
    that a dotted base is invisible to `tests/test_gates._armature_error_family` and so to
    every census that polices this family.

    It is a `RouteGate`, so every caller that catches `RG.RouteGate` still catches it.

    **The `andon` spelling is one rule now, too.** The key was spelled two ways in this one
    file — `"andon": "RouteGate"` (a class name) at the `route_facts` sites and
    `"andon": "frame"` / `"duplicate_socket_name"` (clause names) at the five above.
    `tests/test_core_solver_evidence.py:344` states the tree's law: `ev["gate"]` is the
    class's own `.gate` and `ev["andon"]` is its class name. The clause name it displaced
    was never lost — every one of these raises already carried it under `clause`.
    """

    gate = "SAVED_ADMISSION"

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
        raise SavedAdmission(
            f"{where} not a save-format graph: it carries no `nodes` list. Its "
            f"top-level keys are {keys}; the loader unwraps "
            f"{list(UNWRAPPED_BY_LOAD_GRAPH)} and hands anything else back as the wrapper "
            f"it found. Paste the workflow itself, not the tool result around it",
            {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
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
        raise SavedAdmission(
            f"{where} not an API-format graph: its values carry no `class_type`. Its "
            f"top-level keys are {keys}; a `nodes` list means this is the SAVE format and "
            f"the two arguments are the wrong way round. The loader unwraps "
            f"{list(UNWRAPPED_BY_LOAD_GRAPH)}, so a submission envelope is read for you",
            {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
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
            raise SavedAdmission(
                f"the saved file's link table declares link {lid!r} TWICE with different "
                f"origins — node {prior[0]} slot {prior[1]!r} and node {resolved[0]} slot "
                f"{resolved[1]!r}. Which one a socket carrying that id resolves to is an "
                f"accident of array order, and a file that is ambiguous about where its "
                f"conditioning comes from is not a file this gate can vouch for",
                {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
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

    **The saved node's own socket table is refused when it is ambiguous, and that is the
    third correction** (wave 16, F-04fdd395). `saved_slots` was a last-write-wins dict
    comprehension with no duplicate clause, so a node declaring one input socket name twice
    kept the LAST entry and the earlier declaration was never visited. Measured 2026-09-04
    on a `WanImageToVideo` fixture in this repo's own API shape: node 49 declaring
    `positive` from the NEGATIVE encoder and again from the positive returned
    `{'n_links': 2, 'links': ['49.negative','49.positive']}` with no halt, beside an
    all_equal `round_trip` — a clean topology verdict over a file that declares three
    sockets and was examined for two. `link_table` above refuses a duplicate link id and
    `fetch_run.parse_node_map` a duplicate node id for the same reason; this table is the
    third member of that family.

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
        # ---- ANDON, wave 16 (F-04fdd395). The THIRD name-keyed table in this domain, and
        # the one that was not given the clause. This was a last-write-wins dict
        # comprehension with no duplicate clause, so a saved node declaring the same input
        # socket name twice kept only the LAST entry and the earlier one was never visited
        # by `_origin_problems`. Measured 2026-09-04 on a `WanImageToVideo` fixture in this
        # repo's own API shape (30 = positive encoder, 31 = negative, 49 = the conditioning
        # node): node 49 declaring `[positive<-7, positive<-6, negative<-7]` against a table
        # of `[[6,'30',0,49,0],[7,'31',0,49,1]]` returned `{'n_links': 2, 'links':
        # ['49.negative','49.positive'], 'optional_sockets_empty_in_both': []}` with no halt
        # and `round_trip` all_equal beside it — a clean topology verdict over a file that
        # declares three sockets and was examined for two, on the last gate before a paid
        # submission. `link_table` (:322) already refuses a duplicate LINK ID and
        # `fetch_run.parse_node_map` (:162) a duplicate NODE ID, both citing the same
        # reason and each other; this is that family's third member.
        #
        # An agreeing repeat is refused too, unlike `link_table`'s clause. A link id
        # declared twice from one origin resolves to that origin either way; a node input
        # slot declared twice is a shape no converter emits, and the receipt's own
        # `n_links` counts fewer sockets than the file declares whatever the links say.
        saved_slots = {}
        for slot in (s.get("inputs") or []):
            slot_name = slot.get("name")
            if slot_name in saved_slots:
                raise SavedAdmission(
                    f"the saved file's node {node_id} declares the input socket "
                    f"{slot_name!r} TWICE, carrying link {saved_slots[slot_name].get('link')!r} "
                    f"and link {slot.get('link')!r}. Which one this comparison resolves is "
                    f"an accident of array order, the other is never visited, and a file "
                    f"that is ambiguous about where its conditioning comes from is not a "
                    f"file this gate can vouch for",
                    {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
                     "clause": "duplicate_socket_name", "node": str(node_id),
                     "name": slot_name,
                     "links": [saved_slots[slot_name].get("link"), slot.get("link")],
                     "n_sockets_declared": len(s.get("inputs") or []),
                     "declared_names": [x.get("name") for x in (s.get("inputs") or [])]})
            saved_slots[slot_name] = slot
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


#: The two keys `route_gates.verify` writes into its own receipt for the two facts a
#: builder passes it. A dict carrying BOTH is a `verify` receipt; `gate_base_licence`'s
#: evidence carries the same `gate`/`andon` pair and neither of these, which is why this
#: reader kept keying on the FACTS and not on the gate id (wave 12's rule: key on
#: behaviour, not spelling).
VERIFY_RECEIPT_KEYS = ("attribution", "carries_no_sampler_asserted")

#: The KIND `route_gates.verify` declares about its own receipt, and the value this reader
#: matches on (wave 16, core-gates' `F-069ae942`; the key landed in `verify`'s opening
#: evidence literal, before any clause can raise). Keyed on the VALUE, never on the key's
#: presence — a dict carrying `receipt: "something-else"` is not a verify receipt.
VERIFY_RECEIPT_KIND = "verify"


def verify_receipts(doc):
    """Every `route_gates.verify` receipt inside a payload record.

    Walks the record rather than indexing a key path, because the builders spell that path
    two different ways — `gates.ROUTE` (the assemblers, `build_lora_arm_payload`,
    `build_r2v_payload`) and `gate_ROUTE_built` (`build_i2v_payload` and its camera
    sibling) — and a reader keyed on one of them would silently find nothing in the others
    and hand the DEFAULT facts to the last gate before a spend.

    **Two readings, wave 16.** A receipt now DECLARES its own kind (`receipt: "verify"`),
    so the identity of the dict is read off a declared value rather than inferred from the
    co-presence of two fact keys — the reading that had to be used while nothing declared
    anything, and one that a third key set could collide with tomorrow. The content check
    is kept as the second clause rather than replaced: a record written by an older builder
    carries the facts and no declared kind, and a receipt that answers the two questions is
    still a receipt this gate can read the facts off. Either reading alone admits; both are
    recorded in `route_facts` so a reader of the record can see which one found it.
    """
    out = []
    stack = [doc]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if (node.get("gate") == "ROUTE" and node.get("andon") == "RouteGate"
                    and (node.get("receipt") == VERIFY_RECEIPT_KIND
                         or all(k in node for k in VERIFY_RECEIPT_KEYS))):
                out.append(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return out


def payload_digests(doc):
    """Every `payload_sha256` a record declares, de-duplicated, full-length only.

    Wave 18, F-5c0f3858. Every builder that writes one writes a canonical digest of the
    graph it built — `hashlib.sha256(json.dumps(wf, sort_keys=True,
    separators=(",", ":")).encode()).hexdigest()`, e.g. `build_i2v_payload.py:660` — so the
    tie between a record and the graph it describes was already in the data and was not
    read. Values shorter than 64 hex characters are ignored on purpose: the builders' OK
    lines print a TRUNCATED copy (`meta["payload_sha256"][:32]`), and a prefix is not a
    digest this gate can compare.
    """
    out, stack = [], [doc]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            v = node.get("payload_sha256")
            if isinstance(v, str) and len(v.strip()) == 64:
                out.append(v.strip().lower())
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return sorted(set(out))


def _attribution_key(entry):
    """One canonical string per attribution entry, so two lists compare as SETS."""
    return json.dumps(entry, sort_keys=True, default=str)


def route_facts(record_path, api_graph=None):
    """The two facts every builder passes `verify`, READ OFF the record beside the graph.

    Wave 14, F-2da88c51. This tool is the LAST gate before a paid submission and it called
    `RG.verify(saved, frame=..., hosted_tier=...)` — neither `attribution` nor
    `carries_no_sampler`. Two route families this repo's own builders emit could therefore
    not be admitted at all:

    * the free assembly / cascade chains, which carry no sampler and say so
      (`build_assembly_payload.py:507`, `build_cascade_payload.py:192`). Measured
      2026-09-04 on `build_assembly_payload.build([8 names])`: `RG.verify` with this tool's
      exact kwargs raises `RouteGate` — "the seed clause is INDETERMINATE on this graph and
      therefore UNPROVEN ... Pass carries_no_sampler=True if the graph really carries none".
    * arm T of `build_lora_arm_payload`, whose graph loads the CONDITIONAL
      `wan22-14b-t2v-technically_color.safetensors`. Measured on a one-node graph loading
      it: `RG.verify(g)` raises clause `uncredited_conditional_component`, and
      `RG.verify(g, attribution=[RG.attribution_entry_for('technically_color')])` clears it.

    Both refusal texts instruct the operator to pass a Python keyword, and the CLI exposed
    no way to supply either — so the admission step that exists because "a dry_run PASS does
    not prove link sanity" fired on a CORRECT configuration, and the only way past it was to
    skip the last check before an irreversible spend.

    The facts are DERIVED, never re-typed at this call site: the credit the builder built
    from the licence row (`route_gates.attribution_entry_for`) is the credit checked here,
    and the no-sampler assertion is the one the builder already had CHECKED against its own
    graph. Deriving `carries_no_sampler` from the saved graph instead would make the
    assertion self-fulfilling — `verify` checks the caller's claim against the graph, and a
    claim read off that same graph is not a claim.
    """
    path = os.path.abspath(record_path)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise RG.RouteGate(
            f"--record={record_path!r} could not be read as JSON ({type(exc).__name__}: "
            f"{exc}). The two facts this admission hands to Gate ROUTE come from the "
            f"builder's own payload record, and a record that cannot be read supplies "
            f"neither",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "record_unreadable",
             "record": path, "error": type(exc).__name__}) from exc
    receipts = verify_receipts(doc)
    # ---- ANDON, wave 18 (F-6d68f4c5, second half). `route_gates.verify` writes
    # `receipt: "verify"` AND both fact keys into its opening `ev` literal, explicitly
    # "before the first clause can raise" — so the evidence of a CAUGHT REFUSAL is
    # indistinguishable from a PASS receipt to the reader above. Measured in this worktree:
    # `RG.verify(<graph loading an unmapped LoRA>, attribution=[...])` raises with
    # `receipt: "verify"`, both fact keys, AND a `clause`. A returned receipt never carries
    # `clause`; that is the reading that tells them apart. No builder records a caught
    # refusal today, which is the only thing that kept this closed — and a latent shape at
    # the spend boundary is refused by name rather than left to a future builder.
    refusals = [r for r in receipts if r.get("clause")]
    if refusals:
        raise RG.RouteGate(
            f"--record={record_path!r} carries the evidence of a CAUGHT Gate ROUTE "
            f"REFUSAL, not a passing receipt: "
            f"{sorted({str(r.get('clause')) for r in refusals})}. `verify` writes its "
            f"declared kind and both fact keys before the first clause can raise, so a "
            f"refusal looks like a receipt to this reader; a record of a gate that FIRED "
            f"may not supply the facts that admit the next submission",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_carries_a_caught_refusal", "record": path,
             "refusal_clauses": sorted({str(r.get("clause")) for r in refusals}),
             "n_receipts": len(receipts)})
    if not receipts:
        raise RG.RouteGate(
            f"--record={record_path!r} carries no `route_gates.verify` receipt: no dict in "
            f"it holds gate=ROUTE, andon=RouteGate and either "
            f"`receipt: {VERIFY_RECEIPT_KIND!r}` or both of "
            f"{list(VERIFY_RECEIPT_KEYS)}. A record that does not say what the builder "
            f"asserted is a record that cannot supply this gate's facts, and defaulting "
            f"them would put an unasserted claim on the last check before a spend",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_carries_no_verify_receipt", "record": path,
             "required_keys": list(VERIFY_RECEIPT_KEYS)})
    # ---- ANDON, wave 16. A receipt admitted on its DECLARED kind must still answer the
    # two questions this gate reads off it; the fact keys were the identity test before,
    # so a receipt could not be admitted without them, and adding the declared reading
    # opens a shape where it can. A missing fact is refused by name rather than reaching
    # the next line as a `KeyError`.
    thin = [r for r in receipts
            if any(k not in r for k in VERIFY_RECEIPT_KEYS)]
    if thin:
        raise RG.RouteGate(
            f"--record={record_path!r} carries a receipt declaring "
            f"`receipt: {VERIFY_RECEIPT_KIND!r}` that does not answer both of "
            f"{list(VERIFY_RECEIPT_KEYS)}. A declared kind says what a dict IS; it does "
            f"not supply what this gate reads off it",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "verify_receipt_missing_its_facts", "record": path,
             "required_keys": list(VERIFY_RECEIPT_KEYS),
             "missing": sorted({k for r in thin for k in VERIFY_RECEIPT_KEYS
                                if k not in r})})
    asserted = sorted({bool(r["carries_no_sampler_asserted"]) for r in receipts})
    if len(asserted) != 1:
        raise RG.RouteGate(
            f"--record={record_path!r} carries {len(receipts)} verify receipts that "
            f"DISAGREE about `carries_no_sampler_asserted` ({asserted}). One of them "
            f"describes the graph about to be submitted and this gate cannot tell which",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_route_facts_disagree", "record": path,
             "field": "carries_no_sampler_asserted",
             "carries_no_sampler_values": asserted, "n_receipts": len(receipts)})
    # ---- ANDON, wave 18 (F-6d68f4c5). This function bounded ONE of the two facts across
    # receipts and silently MERGED the other: the clause above refuses a disagreement about
    # the sampler on the stated ground that "one of them describes the graph about to be
    # submitted and this gate cannot tell which", and eleven lines down `attribution` was
    # resolved by UNION — every entry from every receipt de-duplicated into one list and
    # handed to `RG.verify`. The reasoning that makes the first a refusal applies unchanged
    # to the second: a union INVENTS a credit list no builder wrote, on the last gate before
    # a spend, and `attribution` is the fact that PAYS a CONDITIONAL licence row.
    #
    # Measured on the tree: each builder writes exactly ONE verify receipt (`gates.ROUTE` in
    # the assemblers / lora / r2v, `gate_ROUTE_built` in the two i2v builders), so no
    # committed record has two today and the exposure was latent — but `--record` accepts
    # any path, and a concatenated or hand-merged record is the reachable shape. A repeat
    # that AGREES with itself is admitted, as `link_table`'s duplicate clause admits an
    # agreeing repeat.
    att_lists = {tuple(sorted(_attribution_key(e) for e in (r.get("attribution") or [])))
                 for r in receipts}
    if len(att_lists) != 1:
        raise RG.RouteGate(
            f"--record={record_path!r} carries {len(receipts)} verify receipts that "
            f"DISAGREE about `attribution`: {sorted(sorted(x) for x in att_lists)}. One of "
            f"them describes the graph about to be submitted and this gate cannot tell "
            f"which; unioning them would hand Gate ROUTE a credit list no builder wrote",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_route_facts_disagree", "record": path,
             "field": "attribution",
             "attribution_values": sorted(sorted(x) for x in att_lists),
             "n_receipts": len(receipts)})
    attribution, seen = [], set()
    for rec in receipts:
        for entry in rec.get("attribution") or []:
            key = _attribution_key(entry)
            if key not in seen:
                seen.add(key)
                attribution.append(entry)
    # ---- ANDON, wave 18 (F-5c0f3858). The two facts that admit a paid submission were read
    # off an operator-named `--record` that was never TIED to the graph being admitted. This
    # function walked ANY JSON document for a dict carrying the receipt shape and returned
    # its facts; `main` separately hashed `--saved` and `--api` into its own record and
    # compared neither to anything in `--record`.
    #
    # HONEST BOUND, so the fix is not oversold: both facts fail CLOSED today — a mismatched
    # record produces a FALSE REFUSAL, not a false admission (`verify` checks the
    # no-sampler claim against the graph and raises `orphan_attribution` on a credit for a
    # component the graph does not load). The defect closed here is the RECORD: this tool
    # writes `route_facts.record: <path>` and its `SAVED_ADMISSION_OK` line quotes the
    # attribution, ASSERTING that these facts came from the builder that built this graph —
    # an assertion nothing checked, in the provenance document for an irreversible spend.
    # The exposure widens the moment a third fact is added that `verify` cannot cross-check.
    declared_digests = payload_digests(doc)
    if len(declared_digests) > 1:
        raise RG.RouteGate(
            f"--record={record_path!r} declares {len(declared_digests)} different "
            f"`payload_sha256` values ({declared_digests}). One of them describes the graph "
            f"about to be submitted and this gate cannot tell which",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_route_facts_disagree", "record": path,
             "field": "payload_sha256", "payload_sha256_values": declared_digests})
    declared = declared_digests[0] if declared_digests else None
    api_digest = None
    if api_graph is not None:
        api_digest = hashlib.sha256(
            json.dumps(api_graph, sort_keys=True,
                       separators=(",", ":")).encode()).hexdigest()
    if declared is not None and api_digest is not None and declared != api_digest:
        raise RG.RouteGate(
            f"--record={record_path!r} states `payload_sha256` {declared!r}, and the graph "
            f"this admission is about to vouch for hashes to {api_digest!r}. The record "
            f"describes a DIFFERENT graph, so the two facts it supplies — the credit that "
            f"pays a CONDITIONAL licence row and the no-sampler assertion — were asserted "
            f"about something else",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "record_describes_a_different_graph", "record": path,
             "declared_payload_sha256": declared, "api_payload_sha256": api_digest,
             "digest_of": ("json.dumps(api_graph, sort_keys=True, "
                           "separators=(',',':')) — the builders' own derivation")})
    n_declaring = sum(1 for r in receipts if r.get("receipt") == VERIFY_RECEIPT_KIND)
    if declared is None:
        tie = ("the record declares no `payload_sha256`, so the facts below are NOT tied "
               "to the graph being admitted")
    elif api_digest is None:
        tie = (f"the record declares `payload_sha256` {declared}, and no api graph was "
               f"supplied to compare it against")
    else:
        tie = (f"tied: the record's `payload_sha256` {declared} is the digest of the api "
               f"graph this admission vouches for")
    return {"record": path, "n_verify_receipts": len(receipts),
            "payload_sha256": declared, "api_payload_sha256": api_digest,
            # which reading found them, so a record's reader can see whether the receipts
            # declared their own kind or were recognised by the facts they carry.
            "n_declaring_their_kind": n_declaring,
            "found_by": ("declared receipt kind" if n_declaring == len(receipts) else
                         "the two facts they carry" if n_declaring == 0 else
                         "a mix: some declare their kind, some are read by their facts"),
            "carries_no_sampler": asserted[0], "attribution": attribution,
            "source": ("route_gates.verify's own receipt inside the builder's payload "
                       "record; neither fact is typed at this call site — " + tie)}


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
    ap.add_argument("--record", default=None,
                    help="the payload record the builder wrote beside this graph. Gate "
                         "ROUTE's two caller-supplied facts - the `attribution` entries "
                         "the record carries and whether the builder asserted the graph "
                         "carries no sampler - are READ OFF it, so the credit derived "
                         "from the licence row is the credit this admission checks. "
                         "Without it both facts are `verify`'s defaults and a free "
                         "assembly chain or a CONDITIONAL-component arm cannot be "
                         "admitted at all (wave 14, F-2da88c51)")
    ap.add_argument("--frame", default=None,
                    help="width,height,length — the shape the caller knows it is "
                         "generating. Gate L is INDETERMINATE and raises on a graph whose "
                         "latent it cannot read, so a route whose conditioning node sizes "
                         "its own latent states the shape here (argparse eats leading "
                         "minus signs: pass as --frame=832,480,81)")
    a = ap.parse_args(argv)

    # ---- ANDON, wave 18 (F-c7294bc6's sibling half). Rule 2 asks for every flag in this
    # parser. Measured on the base tree: `--saved=<no such file>` and `--api=<no such file>`
    # each raised a bare `FileNotFoundError` out of `route_gates.load_graph`, with no
    # `evidence` attribute at all — exit 1, `"evidence": null`, "this tool crashed" — two
    # lines above a `--saved` that IS refused by name for its SHAPE. `--seeds` and
    # `--record` already carry named clauses for the same operator mistake
    # (`registration_missing`, `record_unreadable`); these two did not. The loader is
    # core-gates' file, so the clause lives here, at the boundary, exactly as the shape
    # clauses below do.
    for flag, given in (("--saved", a.saved), ("--api", a.api)):
        if not os.path.isfile(given):
            raise SavedAdmission(
                f"{flag} {given!r} is not a file. The last gate before a paid submission "
                f"reads its two graphs off disk, and a path that names nothing supplies "
                f"neither; the bare `FileNotFoundError` this replaces printed "
                f"`\"evidence\": null` at the exit code this tool reserves for a crash",
                {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
                 "clause": "graph_file_missing", "flag": flag,
                 "path": os.path.abspath(given),
                 "is_dir": os.path.isdir(given), "exists": os.path.exists(given)})

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
    # ONE reader, eight callers (wave 16, F-0682bd00): the bare index this replaces
    # raised a stdlib KeyError on a registration with no `seeds` key, on the last gate
    # before a paid submission.
    registered = read_seed_registration(a.seeds, flag="--seeds")

    frame = None
    if a.frame is not None:
        # ---- ANDON, wave 16 (F-e6450965). This CONVERTED BEFORE IT COUNTED:
        # `[int(v) for v in a.frame.split(",")]` ran above the arity clause, so a
        # non-numeric component raised a bare stdlib `ValueError` with no `evidence`
        # attribute at all - rendered by the `__main__` block below as
        # `SAVED_ADMISSION_HALT {"error": "ValueError", ..., "evidence": null}` and exit 1,
        # "this tool crashed", on the last gate before a paid submission. The arity case
        # two lines down WAS a named refusal at exit 2, and its evidence was
        # `{"supplied": a.frame}` alone - none of the gate/andon/clause keys every other
        # raise in this file carries. Measured 2026-09-04: `--frame=832,480,eighty` ->
        # `ValueError: invalid literal for int() with base 10: 'eighty'`.
        #
        # One clause for both shapes: split, COUNT, then convert. The shape is
        # `composite_reference.parse_plate`'s, which counts its three components before
        # reading any of them.
        # ⚠ **The fix recurred inside itself** (wave 18, F-c7294bc6). The clause above
        # counted before it converted, as it must — but the count was taken through a GUARD
        # that only APPROXIMATES `int()`, and the guard is WIDER than `int()` on two
        # families. `v.lstrip("+-")` strips EVERY leading character in that set, so `'--832'`
        # and `'+-8'` reach `int()` and raise; and `str.isdigit()` is true for superscripts
        # `int()` rejects, so `'²'` does too. Measured on the base tree by calling
        # `main()` on the same three fixture files the suite builds:
        #     --frame=--832,480,81 -> ValueError: invalid literal for int() ... '--832'
        #     --frame=+-8,480,81   -> ValueError ... '+-8'
        #     --frame=²,480,81     -> ValueError ... '²'
        #     --frame=832,480,²   -> ValueError ... '²'
        # each with NO `evidence` attribute at all, rendered by the `__main__` block as
        # `SAVED_ADMISSION_HALT {"error": "ValueError", ..., "evidence": null}` at exit 1 —
        # the code this module reserves for "this tool crashed" — on the last check before
        # an irreversible spend. Only `--frame=832,480,eighty` reached the named refusal.
        # The flag's OWN help text warns that argparse eats leading minus signs, so a
        # doubled dash is the operator error it invites.
        #
        # So the predicate is `int()` itself, caught. Nothing approximates it: `'٥'`
        # (Arabic-Indic five) is the one wide `str.isdigit()` case `int()` DOES accept, and
        # it is admitted here exactly as `int()` admits it.
        raw = [v.strip() for v in a.frame.split(",")]
        parts, unreadable = [], []
        for v in raw:
            try:
                parts.append(int(v))
            except (TypeError, ValueError):
                unreadable.append(v)
        if len(raw) != 3 or len(parts) != 3:
            raise SavedAdmission(
                f"--frame={a.frame!r} is not width,height,length: it reads as "
                f"{raw!r}, of which {len(parts)} of {len(raw)} are integers"
                + (f" and {unreadable!r} " + ("is" if len(unreadable) == 1 else "are")
                   + " not" if unreadable else "")
                + ". Two out of "
                f"three proves nothing, and a component this tool cannot read is not a "
                f"dimension it can hand Gate L (argparse eats leading minus signs: pass "
                f"as --frame=832,480,81)",
                {"gate": "SAVED_ADMISSION", "andon": "SavedAdmission",
                 "clause": "frame_not_three_integers", "flag": "--frame",
                 "supplied": a.frame, "parts": raw, "n_integers": len(parts),
                 "unreadable": unreadable,
                 "read_by": "int(), not a predicate that approximates it"})
        frame = tuple(parts)

    equality = round_trip(api, saved)                       # 0 — is it even our graph
    topology = link_round_trip(api, saved)                  # 0b — is it wired as we wired it
    # The facts the BUILDER passed `verify`, read off its record rather than re-typed here
    # (wave 14, F-2da88c51). With no `--record` they are `verify`'s own defaults, and the
    # recorded `route_facts` block says which of the two this admission ran under.
    facts = (route_facts(a.record, api) if a.record else
             {"record": None, "n_verify_receipts": 0, "carries_no_sampler": False,
              "attribution": [], "payload_sha256": None, "api_payload_sha256": None,
              "source": "no --record supplied; route_gates.verify's defaults"})
    gate_route = RG.verify(saved, frame=frame, hosted_tier=a.hosted_tier,
                           carries_no_sampler=facts["carries_no_sampler"],
                           attribution=facts["attribution"])                # 1
    # The SAME fact reaches Gate S. `gate_s_registration` runs the identical seed-population
    # andon, so a no-sampler graph that cleared Gate ROUTE above used to be refused one line
    # later by the sibling clause that was never told.
    gate_s = RG.gate_s_registration(saved, registered,
                                    carries_no_sampler=facts["carries_no_sampler"])  # 2
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
        "route_facts": facts,
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
        "route_facts": {"record": facts["record"],
                        "payload_sha256": facts.get("payload_sha256"),
                        "carries_no_sampler": facts["carries_no_sampler"],
                        "attribution": [e.get("component") if isinstance(e, dict) else e
                                        for e in facts["attribution"]]},
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
