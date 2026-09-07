"""Wave 34 builders — sanctioned submitter, ledger, uploads, disclosure, fetch recipe."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import build_assembly_payload as BAP
import fetch_run as FR
import submit_comfy_cloud as SUB
import upload_assets as UP


REPO = Path(__file__).resolve().parents[1]
SEEDS = REPO / "specs" / "E09-A3-seeds.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (dict, list)):
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    else:
        path.write_bytes(obj if isinstance(obj, (bytes, bytearray)) else str(obj).encode())
    return path


# ---- F-43868378: budget reader


def test_read_seed_registration_budget_returns_ceiling_and_allocation():
    budget = BAP.read_seed_registration_budget(str(SEEDS), flag="--seeds")
    assert budget["seeds"] == [2026081201, 2026081202]
    assert budget["submissions"] == 2
    assert budget["ceiling"]["submissions"] == 2
    assert "2026081201" in budget["allocation"]


def test_ceiling_budget_refuses_when_ledger_is_exhausted(tmp_path):
    budget = BAP.read_seed_registration_budget(str(SEEDS), flag="--seeds")
    ledger_path = tmp_path / "E09-A3-seeds-spend-ledger.json"
    _write(ledger_path, {"submissions": [
        {"prompt_id": "a", "utc": "2026-09-06T00:00:00Z"},
        {"prompt_id": "b", "utc": "2026-09-06T00:01:00Z"},
    ]})
    ledger = SUB.load_ledger(str(ledger_path))
    with pytest.raises(SUB.CeilingBudget) as exc:
        SUB.gate_ceiling_budget(budget, ledger)
    assert exc.value.evidence["clause"] == "ceiling_exhausted"


def test_dry_run_ledger_rows_do_not_count_against_ceiling(tmp_path):
    budget = BAP.read_seed_registration_budget(str(SEEDS), flag="--seeds")
    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, {"submissions": [
        {"prompt_id": None, "dry_run": True},
        {"prompt_id": None, "dry_run": True},
    ]})
    ev = SUB.gate_ceiling_budget(budget, SUB.load_ledger(str(ledger_path)))
    assert ev["submissions_spent"] == 0
    assert ev["remaining_before"] == 2


# ---- F-5fb34131: admission match / refuse-without-admission / dry-run


def test_admission_digest_mismatch_is_refused(tmp_path):
    api = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "x", "images": ["0", 0]}}}
    api_path = _write(tmp_path / "g.api.json", api)
    saved_path = _write(tmp_path / "g.saved.json", {"nodes": [], "links": []})
    admission = {
        "api_file": {"sha256": "0" * 64},
        "saved_file": {"sha256": "1" * 64},
        "route_facts": {},
    }
    adm_path = _write(tmp_path / "adm.json", admission)
    with pytest.raises(SUB.SubmitGate) as exc:
        SUB.gate_admission_matches(str(adm_path), str(api_path), str(saved_path), api)
    assert exc.value.evidence["clause"] == "admission_digest_mismatch"


def test_missing_admission_file_is_refused_by_main(tmp_path):
    api = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "x", "images": ["0", 0]}}}
    api_path = _write(tmp_path / "g.api.json", api)
    saved_path = _write(tmp_path / "g.saved.json", {"nodes": [], "links": []})
    seeds = _write(tmp_path / "seeds.json", {
        "seeds": [1], "allocation": {"1": "x"},
        "ceiling": {"submissions": 1, "note": "n"},
    })
    with pytest.raises(SUB.SubmitGate) as exc:
        SUB.main([
            f"--api={api_path}", f"--saved={saved_path}",
            f"--admission={tmp_path / 'nope.json'}", f"--seeds={seeds}",
            "--dry-run",
        ])
    assert exc.value.evidence["clause"] in ("input_missing", "admission_missing")


def test_dry_run_never_posts_when_admission_matches(tmp_path, monkeypatch):
    api = {"1": {"class_type": "SaveImage", "inputs": {"filename_prefix": "x", "images": ["0", 0]}}}
    api_path = _write(tmp_path / "g.api.json", api)
    saved_path = _write(tmp_path / "g.saved.json", {"nodes": [], "links": []})
    api_sha = _sha(api_path)
    saved_sha = _sha(saved_path)
    payload = BAP.canonical_payload_digest(api)
    adm_path = _write(tmp_path / "adm.json", {
        "api_file": {"sha256": api_sha},
        "saved_file": {"sha256": saved_sha},
        "route_facts": {"payload_sha256": payload, "carries_no_sampler": True,
                        "attribution": []},
        "experiment": "T", "stage": "dry",
    })
    seeds = _write(tmp_path / "seeds.json", {
        "seeds": [1], "allocation": {"1": "x"},
        "ceiling": {"submissions": 3, "note": "n"},
    })
    posted = []

    def _boom(*_a, **_k):
        posted.append(True)
        raise AssertionError("live POST must not run under --dry-run")

    monkeypatch.setattr(SUB, "post_prompt", _boom)
    monkeypatch.setattr(SUB, "rearm_gates", lambda *a, **k: {
        "ROUTE": {"verdict": "stub"}, "S": {"verdict": "stub"}, "route_facts": {}})
    # load_graph / as_* still run — stub those to avoid format clauses on empty saved.
    monkeypatch.setattr(SUB.RG, "load_graph", lambda p: (
        api if str(p).endswith("api.json") else {"nodes": [], "links": []}))
    monkeypatch.setattr(SUB, "_as_api_graph", lambda doc, path=None: api)
    monkeypatch.setattr(SUB, "_as_saved_graph", lambda doc, path=None: doc)

    rc = SUB.main([
        f"--api={api_path}", f"--saved={saved_path}",
        f"--admission={adm_path}", f"--seeds={seeds}",
        f"--ledger={tmp_path / 'ledger.json'}", "--dry-run",
    ])
    assert rc == 0
    assert posted == []
    # dry-run must not append a live ledger row
    assert not (tmp_path / "ledger.json").exists()


# ---- F-cc2dff5c: upload map


def test_upload_assets_dry_run_i2v_map(tmp_path):
    png = tmp_path / "start.png"
    # minimal 8-byte header-ish payload; name is content-addressed from bytes
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 24)
    out = tmp_path / "uploads.json"
    rc = UP.main([
        "--route=i2v", f"--start-frame={png}", f"--out={out}", "--dry-run",
    ])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert set(doc) == {"start_frame"}
    assert doc["start_frame"].endswith(".png")
    assert len(doc["start_frame"]) == 64 + 4


def test_upload_assets_dry_run_assembly_frame_keys(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    for i in range(3):
        (frames / f"{i:05d}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 16)
    out = tmp_path / "uploads.json"
    rc = UP.main([
        "--route=assembly", f"--frames-dir={frames}", f"--out={out}", "--dry-run",
    ])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert BAP.frame_order(doc) == ["00000.png", "00001.png", "00002.png"]


# ---- F-d092c186: disclosure


def test_comfy_cloud_oss_disclosure_has_required_kinds():
    block = BAP.comfy_cloud_oss_disclosure(route_verdict="ok")
    kinds = {o["kind"] for o in block["obligations"]}
    assert {"data_use", "training_use", "ai_content_disclosure", "watermark"} <= kinds
    lines = BAP.disclosure_lines(block)
    assert lines[0].startswith("  ROUTE:")
    assert any("DATA USE" in ln or "TRAINING USE" in ln for ln in lines)


def test_assembly_leave_disclosure_is_shorter():
    block = BAP.assembly_leave_disclosure()
    assert len(block["obligations"]) == 1
    assert block["obligations"][0]["kind"] == "data_use"


# ---- F-dc84b444: fetch recipe


def test_fetch_recipe_keys_and_none_map():
    recipe = BAP.fetch_recipe(
        node_map={}, video_nodes=("402",), root_hint="outputs/S03/runs")
    assert recipe["fetch"]["node_map_flag"] == "none"
    assert recipe["fetch"]["video_nodes_flag"] == "402"
    assert recipe["video_nodes"] == ["402"]
    assert recipe["node_map"] == {}


def test_parse_node_map_none_is_empty_not_e02():
    assert FR.parse_node_map(None) == dict(FR.NODE_DIR)
    assert FR.parse_node_map("none") == {}


def test_fetch_run_reads_recipe_from_record(tmp_path):
    rec = _write(tmp_path / "rec.json", {
        "fetch": {
            "node_map": {"71": "lossless"},
            "video_nodes": ["81"],
            "root_hint": str(tmp_path / "runs"),
            "node_map_flag": "71=lossless",
            "video_nodes_flag": "81",
        }
    })
    # Exercise the --record branch without downloading: dump with no results refuses
    # after the recipe is applied — but first confirm parse via a tiny helper path.
    dump = _write(tmp_path / "dump.json", {"results": []})
    with pytest.raises(FR.FetchHalt) as exc:
        FR.main([
            f"--dump={dump}", "--run=r1", f"--record={rec}",
        ])
    # empty results is a later clause; if record failed we'd see record_* first
    assert exc.value.evidence["clause"] in (
        "empty_results", "dump_results_not_a_list", "record_missing_fetch_recipe",
        "node_map_without_a_root")
    # root should have been filled from record so node_map_without_a_root is not required
    # when root_hint is present — empty_results is the expected halt.
    assert exc.value.evidence["clause"] == "empty_results"
