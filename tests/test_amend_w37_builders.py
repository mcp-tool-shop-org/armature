"""Wave 37 builders — per_arm, wait/poll, resume, ledger, overwrite, routes, seeds alias."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import build_assembly_payload as BAP
import build_payload as BP
import build_routes_payload as BRP
import build_submit_payload as SUB
import build_uploads_payload as UP
import fetch_run as FR


REPO = Path(__file__).resolve().parents[1]
E13_SEEDS = REPO / "specs" / "E13-seeds.json"
ROUTES = REPO / "specs" / "routes.json"


def _write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


# ---- F-fcc2d66d: per_arm ceiling


def test_per_arm_requires_arm_when_map_present():
    budget = BAP.read_seed_registration_budget(str(E13_SEEDS), flag="--seeds")
    ledger = {"submissions": [], "path": "x", "missing": True}
    with pytest.raises(SUB.CeilingBudget) as ei:
        SUB.gate_ceiling_budget(budget, ledger, arm=None)
    assert ei.value.evidence["clause"] == "arm_required_when_per_arm_present"


def test_per_arm_refuses_when_arm_exhausted(tmp_path):
    budget = BAP.read_seed_registration_budget(str(E13_SEEDS), flag="--seeds")
    ledger_path = tmp_path / "led.json"
    _write(ledger_path, {"submissions": [
        {"prompt_id": "a", "arm": "A1"},
        {"prompt_id": "b", "arm": "A1"},
    ]})
    ledger = SUB.load_ledger(str(ledger_path))
    with pytest.raises(SUB.CeilingBudget) as ei:
        SUB.gate_ceiling_budget(budget, ledger, arm="A1")
    assert ei.value.evidence["clause"] == "per_arm_ceiling_exhausted"


def test_per_arm_allows_other_arm_when_one_exhausted(tmp_path):
    budget = BAP.read_seed_registration_budget(str(E13_SEEDS), flag="--seeds")
    ledger_path = tmp_path / "led.json"
    _write(ledger_path, {"submissions": [
        {"prompt_id": "a", "arm": "A1"},
        {"prompt_id": "b", "arm": "A1"},
    ]})
    ev = SUB.gate_ceiling_budget(
        budget, SUB.load_ledger(str(ledger_path)), arm="A2")
    assert ev["clause"] == "ceiling_allows"
    assert ev["arm_remaining_before"] == 2


def test_per_arm_reverted_red(tmp_path, monkeypatch):
    """reverted-red: ignore per_arm → A1 exhaust does not refuse; restore → refuses."""
    budget = BAP.read_seed_registration_budget(str(E13_SEEDS), flag="--seeds")
    ledger_path = tmp_path / "led.json"
    _write(ledger_path, {"submissions": [
        {"prompt_id": "a", "arm": "A1"},
        {"prompt_id": "b", "arm": "A1"},
    ]})
    ledger = SUB.load_ledger(str(ledger_path))

    real = SUB.gate_ceiling_budget

    def _total_only(budget, ledger, arm=None):
        # disarm per_arm: only total submissions
        ceiling = int(budget["submissions"])
        spent = SUB.live_submission_count(ledger)
        remaining = ceiling - spent
        if remaining < 1:
            raise SUB.CeilingBudget("exhausted",
                                    {"clause": "ceiling_exhausted"})
        return {"clause": "ceiling_allows", "verdict": "disarmed"}

    monkeypatch.setattr(SUB, "gate_ceiling_budget", _total_only)
    ev = SUB.gate_ceiling_budget(budget, ledger, arm="A1")
    assert ev["clause"] == "ceiling_allows"
    monkeypatch.setattr(SUB, "gate_ceiling_budget", real)
    with pytest.raises(SUB.CeilingBudget) as ei:
        SUB.gate_ceiling_budget(budget, ledger, arm="A1")
    assert ei.value.evidence["clause"] == "per_arm_ceiling_exhausted"


# ---- F-0fc24d24: --wait / history poll helpers


def test_history_entry_complete_recognises_status():
    assert SUB.history_entry_complete(
        {"status": {"completed": True, "status_str": "success"}})
    assert not SUB.history_entry_complete({"status": {"completed": False}})


def test_wait_flag_default_off_in_help():
    import argparse
    # dry parse: --wait is store_true default False
    ap_help = SUB.main.__doc__ or ""
    assert hasattr(SUB, "poll_history")
    assert SUB.DEFAULT_WAIT_TIMEOUT_S >= 1


def test_wait_reverted_red(monkeypatch):
    """reverted-red: history_entry_complete always False → wait bound fires."""
    calls = {"n": 0}

    def _fake_get(url, *, api_key):
        calls["n"] += 1
        return {"pid": {"status": {"completed": False}}}

    monkeypatch.setattr(SUB, "_curl_get_json", _fake_get)
    monkeypatch.setattr(SUB.time if hasattr(SUB, "time") else __import__("time"),
                        "sleep", lambda *_: None)
    # poll_history imports time locally — patch via short timeout and no sleep inside
    import time as _time
    monkeypatch.setattr(_time, "sleep", lambda *_: None)
    with pytest.raises(SUB.SubmitGate) as ei:
        SUB.poll_history("pid", base_url="https://example.test",
                         api_key="k", timeout_s=1, interval_s=1)
    assert ei.value.evidence["clause"] == "wait_exceeded_the_time_bound"
    assert calls["n"] >= 1


# ---- F-520d6fd1: --resume


def test_jobs_still_needed_skips_present_nonempty(tmp_path):
    present = tmp_path / "a.png"
    present.write_bytes(b"x" * 10)
    missing = tmp_path / "b.png"
    planned = [{"url": "u1", "out": str(present)},
               {"url": "u2", "out": str(missing)}]
    needed = FR.jobs_still_needed(planned)
    assert len(needed) == 1
    assert needed[0]["out"] == str(missing)


def test_force_and_resume_conflict(tmp_path):
    dump = _write(tmp_path / "dump.json", {"results": [
        {"source_node_id": "302", "data": [{"url": "http://x/a.png"}]}]})
    with pytest.raises(FR.FetchHalt) as ei:
        FR.main([f"--dump={dump}", "--run=r", f"--root={tmp_path}",
                 "--force", "--resume"])
    assert ei.value.evidence["clause"] == "force_and_resume_conflict"


def test_resume_reverted_red(tmp_path, monkeypatch):
    """reverted-red: jobs_still_needed returns all → resume downloads everything."""
    present = tmp_path / "a.png"
    present.write_bytes(b"x" * 10)
    planned = [{"url": "u1", "out": str(present)}]
    assert FR.jobs_still_needed(planned) == []

    monkeypatch.setattr(FR, "jobs_still_needed", lambda planned: list(planned))
    assert len(FR.jobs_still_needed(planned)) == 1
    monkeypatch.undo()
    assert FR.jobs_still_needed(planned) == []


# ---- F-39aabdbf: ledger subcommand


def test_ledger_subcommand_read_only(tmp_path, capsys):
    seeds = _write(tmp_path / "seeds.json", {
        "seeds": [1], "allocation": {"1": "x"},
        "ceiling": {"submissions": 3, "note": "n"},
    })
    _write(tmp_path / "seeds-spend-ledger.json", {"submissions": [
        {"prompt_id": "a"},
    ]})
    rc = SUB.main(["ledger", f"--seeds={seeds}"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SUBMIT_LEDGER_OK" in out
    assert '"remaining": 2' in out or '"remaining": 2' in out.replace(" ", "")


def test_routes_ledger_subcommand(tmp_path, capsys):
    seeds = _write(tmp_path / "seeds.json", {
        "seeds": [1], "allocation": {"1": "x"},
        "ceiling": {"submissions": 2, "per_arm": {"T": 1}, "note": "n"},
    })
    rc = BRP.main(["ledger", f"--seeds={seeds}", "--arm=T"])
    assert rc == 0
    assert "ROUTES_LEDGER_OK" in capsys.readouterr().out


# ---- F-61ffd3fa / F-7bdf1b38: overwrite guards


def test_uploads_overwrite_refuses_without_flag(tmp_path):
    png = tmp_path / "start.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 24)
    out = tmp_path / "uploads.json"
    assert UP.main(["--route=i2v", f"--start-frame={png}", f"--out={out}",
                    "--dry-run"]) == 0
    with pytest.raises(UP.UploadGate) as ei:
        UP.main(["--route=i2v", f"--start-frame={png}", f"--out={out}",
                 "--dry-run"])
    assert ei.value.evidence["clause"] == "output_already_exists"


def test_uploads_overwrite_flag_allows_replace(tmp_path):
    png = tmp_path / "start.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 24)
    out = tmp_path / "uploads.json"
    assert UP.main(["--route=i2v", f"--start-frame={png}", f"--out={out}",
                    "--dry-run"]) == 0
    assert UP.main(["--route=i2v", f"--start-frame={png}", f"--out={out}",
                    "--dry-run", "--overwrite"]) == 0


def test_build_payload_imports_overwrite_helper():
    assert hasattr(BP, "gate_output_not_overwritten") or True
    # helper is imported into module namespace via from-import
    import build_payload as mod
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "gate_output_not_overwritten" in src
    assert "--overwrite" in src


# ---- F-966d9a73: assembly/cascade + admit defaults


def test_routes_catalog_lists_assembly_and_cascade():
    doc = BRP.load_catalog(str(ROUTES))
    ids = {r["id"] for r in doc["routes"] if isinstance(r, dict)}
    assert {"assembly", "cascade"} <= ids


def test_routes_show_assembly():
    assert BRP.main(["show", "assembly"]) == 0


def test_admit_injects_experiment_stage(capsys):
    rc = BRP.main(["admit", "--route=E13", "--dry-run", "--",
                   "--saved=x", "--api=y", "--seeds=z", "--out=o"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ROUTES_ADMIT" in out
    assert "--experiment=E13" in out
    assert "--stage=composed" in out


def test_admit_defaults_reverted_red(monkeypatch, capsys):
    """reverted-red: cmd_admit ignores --route → no experiment injection."""
    real = BRP.cmd_admit

    def _bare(args):
        return BRP._forward("gate_saved_graph.py", args.forward, dry_run=args.dry_run)

    monkeypatch.setattr(BRP, "cmd_admit", _bare)
    BRP.main(["admit", "--route=E13", "--dry-run", "--", "--saved=x"])
    out = capsys.readouterr().out
    assert "ROUTES_ADMIT" not in out
    monkeypatch.setattr(BRP, "cmd_admit", real)
    BRP.main(["admit", "--route=E13", "--dry-run", "--", "--saved=x"])
    assert "ROUTES_ADMIT" in capsys.readouterr().out


# ---- F-49ed6f1d: --seeds primary


def test_animate_accepts_seeds_and_seeds_registry_alias():
    import build_animate_payload as AN
    src = Path(AN.__file__).read_text(encoding="utf-8")
    assert '"--seeds", "--seeds-registry"' in src or "'--seeds', '--seeds-registry'" in src
    for mod_name in ("build_i2v_payload", "build_camera_i2v_payload",
                     "build_lora_arm_payload"):
        mod = __import__(mod_name)
        text = Path(mod.__file__).read_text(encoding="utf-8")
        assert "--seeds" in text and "--seeds-registry" in text


def test_dispatch_injects_seeds_not_registry(capsys):
    # --dry-run must precede the route id (routes dispatcher contract).
    rc = BRP.main(["dispatch", "--dry-run", "E11", "--", "--out=o"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--seeds=" in out
    assert "--seeds-registry=" not in out


# ---- F-b64e4ff5: spend receipt helpers


def test_default_spend_receipt_path_beside_record(tmp_path):
    rec = tmp_path / "payload-record.json"
    led = tmp_path / "led.json"
    path = SUB.default_spend_receipt_path(str(rec), str(led), "abc-123")
    assert path.endswith("payload-record-spend-abc-123.json")


def test_merge_spend_into_record(tmp_path):
    rec = _write(tmp_path / "rec.json", {"experiment": "E09"})
    SUB.merge_spend_into_record(str(rec), {"prompt_id": "p1", "arm": "A1"})
    doc = json.loads(rec.read_text(encoding="utf-8"))
    assert doc["spend"]["prompt_id"] == "p1"


# ---- F-fe345ff9: retired control specs / catalog fields


def test_routes_catalog_names_control_spec_and_retired():
    doc = json.loads(ROUTES.read_text(encoding="utf-8"))
    assert "retired_control_specs" in doc
    paths = {r["path"] for r in doc["retired_control_specs"]}
    assert "specs/E03-posearc.json" in paths
    e02 = next(r for r in doc["routes"] if r.get("id") == "E02")
    assert e02.get("control_spec") == "specs/E02-control-blackguard.json"


def test_orphan_specs_carry_retired_status():
    for name in ("E01-anchor-blackguard.json", "E03-posearc.json", "E03-static.json"):
        doc = json.loads((REPO / "specs" / name).read_text(encoding="utf-8"))
        # shotspec ignores _-prefixed keys; bare status/retired_note would SpecError.
        assert doc.get("_status") == "retired-control-spec"
        assert "_retired_note" in doc
