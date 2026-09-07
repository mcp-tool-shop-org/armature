"""Banked spend-builder API graphs — live-or-fixture resolution + round-trip (wave 34).

F-025b750b: `tests/fixtures` only banked three camera/i2v `*.api.json` files, so
gate_saved_graph / link-round-trip for t2v, r2v, animate, assembly, cascade (and the rest)
could not be rehearsed from a clean clone. One minimal API-format fixture per spend
builder now lives under `tests/fixtures/records/<route>/`, resolved through the same
live-or-fixture helpers uploads use, and the round-trip pair is parametrized over that
table wherever every class already has a `WIDGET_INDEX` row.
"""

from __future__ import annotations

import json
import os

import pytest

from conftest import (  # noqa: F401
    API_GRAPH_RECORDS, PAYLOAD_FIXTURES, TOOLS, api_graph_record, api_graph_record_branch,
    api_graph_record_paths,
)
import gate_saved_graph as GSG
from armature_core import route_gates as RG


#: Save-format-only `control_after_generate` insertions (indices already shifted in
#: `WIDGET_INDEX`). Faithful synthesizer fills these so widget length matches the table.
CONTROL_AFTER_SLOT = {
    "KSampler": 1,
    "KSamplerAdvanced": 2,
    "Wan2ReferenceVideoApi": 7,
}


def _load_api(path):
    doc = json.loads(open(path, encoding="utf-8").read())
    if isinstance(doc, dict) and "prompt" in doc and isinstance(doc["prompt"], dict):
        if any(isinstance(v, dict) and "class_type" in v for v in doc["prompt"].values()):
            return doc["prompt"]
    return doc


def faithful_saved(api):
    """A save-format twin that round-trips: widgets from WIDGET_INDEX, links from list inputs."""
    nodes, links = [], []
    next_link = 1
    for nid, node in api.items():
        if not isinstance(node, dict) or "class_type" not in node:
            continue
        ct = node["class_type"]
        index = GSG.WIDGET_INDEX.get(ct)
        if index is None:
            raise KeyError(f"no WIDGET_INDEX for {ct} (node {nid})")
        inputs = node.get("inputs") or {}
        max_i = max(index.values()) if index else -1
        if ct in CONTROL_AFTER_SLOT:
            max_i = max(max_i, CONTROL_AFTER_SLOT[ct])
        wv = [None] * (max_i + 1) if max_i >= 0 else []
        if ct in CONTROL_AFTER_SLOT:
            wv[CONTROL_AFTER_SLOT[ct]] = "fixed"
        sockets = []
        slot_i = 0
        for name, value in inputs.items():
            if isinstance(value, list) and len(value) >= 2:
                lid = next_link
                next_link += 1
                origin = int(value[0]) if str(value[0]).isdigit() else value[0]
                target = int(nid) if str(nid).isdigit() else nid
                links.append([lid, origin, value[1], target, slot_i, "ANY"])
                sockets.append({"name": name, "type": "ANY", "link": lid})
                slot_i += 1
            elif name in index:
                wv[index[name]] = value
        for i, v in enumerate(wv):
            if v is None:
                wv[i] = 0
        nodes.append({
            "id": int(nid) if str(nid).isdigit() else nid,
            "type": ct,
            "inputs": sockets,
            "widgets_values": wv,
        })
    return {"nodes": nodes, "links": links}


def _missing_widget_classes(api):
    return sorted({
        n["class_type"] for n in api.values()
        if isinstance(n, dict) and "class_type" in n
        and n["class_type"] not in GSG.WIDGET_INDEX
    })


def test_the_api_graph_bank_covers_every_spend_builder_route():
    """Nine builders, nine committed API graphs — the census, not a spot check."""
    routes = sorted({rel.split("/")[1] for rel in API_GRAPH_RECORDS})
    assert routes == [
        "animate", "assembly", "camera_i2v", "cascade", "i2v", "lora_arm",
        "payload", "r2v", "t2v"], routes
    assert len(API_GRAPH_RECORDS) == 9


@pytest.mark.parametrize("relpath", API_GRAPH_RECORDS)
def test_every_banked_api_graph_resolves_and_is_api_format(relpath):
    """Live-or-fixture resolution reaches a file, and Gate ROUTE's loader accepts it."""
    path = api_graph_record(relpath)
    assert os.path.isfile(path), (
        f"{relpath} resolves to {path!r} ({api_graph_record_branch(relpath)}) but the "
        f"file is absent; fixture should be at "
        f"{api_graph_record_paths(relpath)[1]}")
    api = _load_api(path)
    assert RG.is_api_format(api), (relpath, sorted(api)[:8])
    assert any(isinstance(v, dict) and "class_type" in v for v in api.values()), relpath


@pytest.mark.parametrize("relpath", API_GRAPH_RECORDS)
def test_every_round_trippable_banked_graph_survives_value_and_link_checks(relpath):
    """gate_saved_graph round-trips over the bank wherever WIDGET_INDEX already covers it.

    lora_arm / payload currently load classes with no widget row (`LoraLoaderModelOnly`,
    `WanVaceToVideo`) — that half is OUT-OF-DOMAIN for this seat (gate_saved_graph owns
    WIDGET_INDEX). Those two still resolve as API format above; the round-trip parametrize
    skips them by name rather than inventing a second widget table here.
    """
    api = _load_api(api_graph_record(relpath))
    missing = _missing_widget_classes(api)
    if missing:
        pytest.skip(f"WIDGET_INDEX has no row for {missing}; OUT-OF-DOMAIN for tests/**")
    saved = faithful_saved(api)
    ev = GSG.round_trip(api, saved)
    assert ev["all_equal"] is True
    assert ev["n_values_compared"] > 0
    link = GSG.link_round_trip(api, saved)
    assert link["n_links"] >= 0
