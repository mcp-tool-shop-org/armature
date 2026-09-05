"""Coordinator tests at the wave-18 merge (the LAST Stage A amend).

core-gates' SEAM 14 posted a block to builders that builders' report did not act on: `gate_saved_graph.round_trip`
indexed `node["class_type"]` on every API entry BEFORE Gate ROUTE's walk ran, so the exact operand core-gates taught
the walk to refuse by name (F-7eb1ba2a: one node whose `class_type` was lost, among readable nodes) still crashed the
last gate before a paid submission. Measured on the merged tree `64a9fd3` as a real subprocess:

    exit 1 · `round_trip` :265 `if s["type"] != node["class_type"]` → `KeyError: 'class_type'`
    `SAVED_ADMISSION_HALT {"error": "KeyError", "message": "'class_type'", "evidence": null}`

`_as_api_graph` did not catch it because `RG.is_api_format` answers for the graph as a whole and the OTHER nodes
carry the key. The fix classifies every top-level entry by SHAPE through Gate ROUTE's own `_api_entry_kind` before
any class is read, so the refusal is the walk's own `unreadable_node` with the node's key in its evidence, and
envelope metadata is skipped exactly as the walk skips it. This file reads the halt line back through the tool's
real `__main__`, as a subprocess, on the operand that crashed.
"""
import json
import os
import subprocess
import sys

import pytest

from conftest import TOOLS  # noqa: F401
import gate_saved_graph as GSG
from armature_core import route_gates as RG


def _pair(tmp_path, *, drop_class_type_on=None, metadata=None, with_lora=True):
    """A saved/api/seeds trio, with one optional defect: the API entry `drop_class_type_on` loses its
    `class_type`; `metadata` adds envelope keys beside the nodes. The LoRA node (`with_lora`) is the
    F-7eb1ba2a operand's shape and has no `WIDGET_INDEX` row, so a pair meant to be ACCEPTED omits it."""
    d = tmp_path / "in"
    d.mkdir(parents=True)
    saved = {"nodes": [
        {"id": 49, "type": "WanAnimateToVideo", "inputs": [], "widgets_values": [832, 480, 81, 1, 5, 0]},
    ]}
    api = {
        "49": {"class_type": "WanAnimateToVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                          "continue_motion_max_frames": 5, "video_frame_offset": 0}},
    }
    if with_lora:
        saved["nodes"].append({"id": 50, "type": "LoraLoaderModelOnly", "inputs": [],
                               "widgets_values": ["some_lora.safetensors", 1.0]})
        api["50"] = {"class_type": "LoraLoaderModelOnly",
                     "inputs": {"lora_name": "some_lora.safetensors", "strength_model": 1.0}}
    if drop_class_type_on is not None:
        del api[drop_class_type_on]["class_type"]
    if metadata:
        api.update(metadata)
    (d / "g.saved.json").write_text(json.dumps(saved), encoding="utf-8")
    (d / "g.api.json").write_text(json.dumps(api), encoding="utf-8")
    (d / "seeds.json").write_text(json.dumps({"seeds": [1]}), encoding="utf-8")
    return d, saved, api


def test_a_node_whose_class_was_lost_is_refused_by_the_walks_own_clause_not_a_key_error(tmp_path):
    """Red on the pre-fix shape by construction: it raised `KeyError`, which is not a `RouteGate`."""
    _, saved, api = _pair(tmp_path, drop_class_type_on="50")
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(api, saved)
    ev = exc.value.evidence
    assert isinstance(ev, dict), ev
    assert ev["clause"] == "unreadable_node", ev
    assert ev["gate"] == "ROUTE", ev
    assert "50" in json.dumps(ev), "the evidence must name the node whose class was lost"


def test_the_halt_line_an_operator_reads_on_the_lost_class_operand_names_the_andon(tmp_path):
    """The measurement that found the defect, re-run as the proof: the tool's real `__main__`, as a
    subprocess, on the operand — exit 2 (a gate refused), ONE sentinel line, evidence carrying the clause.
    Before the fix: exit 1, `"error": "KeyError"`, `"evidence": null`."""
    d, _, _ = _pair(tmp_path, drop_class_type_on="50")
    out = tmp_path / "fresh" / "admission.json"
    # The tool's halt prose carries non-ASCII punctuation; under a cp1252 console the child writes it as
    # cp1252 bytes, which a strict utf-8 reader thread drops on the floor (measured: `r.stderr` came back
    # `None`). Pin the child's encoding and decode leniently — the sentinel line is JSON and survives either way.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"),
         f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
         f"--seeds={d / 'seeds.json'}", f"--out={out}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
        cwd=os.path.dirname(TOOLS))
    assert r.returncode == 2, (r.returncode, r.stdout[-800:], r.stderr[-800:])
    lines = [l for l in r.stdout.splitlines() if l.split(" ", 1)[0] == "SAVED_ADMISSION_HALT"]
    assert len(lines) == 1, r.stdout[-1200:]
    rec = json.loads(lines[0][len("SAVED_ADMISSION_HALT"):].strip())
    assert rec["error"] == "RouteGate", rec
    ev = rec["evidence"]
    assert isinstance(ev, dict), rec
    assert ev["clause"] == "unreadable_node" and ev["gate"] == "ROUTE", ev
    # The pre-fix record, byte for byte — the handler prints its traceback to stderr for EVERY gate, so
    # stderr is not the discriminator; the record's `error` and `evidence` are.
    assert '"error": "KeyError"' not in r.stdout and '"evidence": null' not in r.stdout, r.stdout[-400:]
    assert not out.parent.exists(), "a refused admission created its output directory"


def test_envelope_metadata_beside_the_nodes_is_skipped_as_the_walk_skips_it_not_reported_absent(tmp_path):
    """The other direction of the same classification: `version` / `extra_data` are metadata by
    `API_ENVELOPE_KEYS`, and must neither crash the class read nor be counted as nodes the saved
    file lacks. `nodes` is what the round-trip compares; the envelope is not a node."""
    _, saved, api = _pair(tmp_path, metadata={"version": "0.4", "extra_data": {"ds": {}}}, with_lora=False)
    for key in ("version", "extra_data"):
        assert key in RG.API_ENVELOPE_KEYS
    result = GSG.round_trip(api, saved)
    assert result["all_equal"] is True
    assert result["n_values_compared"] == 6, result
