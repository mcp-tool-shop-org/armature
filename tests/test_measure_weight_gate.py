"""Synthetic CPU tests for `MeasureWeightGate` (`L1`–`L3`, `M1`, and mirror invariants).

Tests run with stdlib + synthetic byte files only; no model or weight is downloaded or loaded
(`docs/dispatches/shot-diagnostics-design.md` §4.3, §5).
"""

import builtins
import datetime
import hashlib
import importlib
import os

import pytest

from armature_core import errors
from armature_core import measure_weights as MW
from armature_core import shotdiag as SD
from armature_core.measure_weights import MeasureWeightGate

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _forbid_heavy_ml_imports(monkeypatch):
    """Fail immediately if `torch`, `safetensors`, or `transformers` is imported."""
    blocked_roots = {"torch", "safetensors", "transformers"}
    real_import = builtins.__import__
    real_import_module = importlib.import_module

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".")[0] in blocked_roots:
            raise AssertionError(f"heavy ML dependency {name!r} imported before MeasureWeightGate")
        return real_import(name, globals, locals, fromlist, level)

    def _guarded_import_module(name, package=None):
        if name.split(".")[0] in blocked_roots:
            raise AssertionError(f"heavy ML dependency {name!r} imported before MeasureWeightGate")
        return real_import_module(name, package)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)
    monkeypatch.setattr(importlib, "import_module", _guarded_import_module)


def test_l1_model_safetensors_filename_collision_keys_on_bytes_not_filename(tmp_path):
    """L1: Fails if a BANNED or unknown `model.safetensors` slips past because `dinov2-base` shares that filename."""
    allowed_bytes = b"allowed-dinov2-vitb14-checkpoint-bytes"
    banned_bytes = b"banned-map-anything-cc-by-nc-checkpoint-bytes"
    unknown_bytes = b"unpinned-mystery-checkpoint-bytes"

    allowed_sha = hashlib.sha256(allowed_bytes).hexdigest()
    banned_sha = hashlib.sha256(banned_bytes).hexdigest()

    table = (
        {
            "repo_id": "facebook/dinov2-base",
            "revision": "f9e44c81",
            "filename": "model.safetensors",
            "sha256": allowed_sha,
            "verdict": "ALLOWED",
            "licence": "Apache-2.0",
            "fetched": "2026-11-11",
            "source": "https://huggingface.co/api/models/facebook/dinov2-base",
        },
        {
            "repo_id": "facebook/map-anything",
            "revision": "a1d87e90",
            "filename": "model.safetensors",
            "sha256": banned_sha,
            "verdict": "BANNED",
            "licence": "CC-BY-NC-4.0",
            "fetched": "2026-11-11",
            "source": "https://huggingface.co/api/models/facebook/map-anything",
        },
    )

    # 1. Same filename `model.safetensors`, even claiming `repo_id="facebook/dinov2-base"`,
    #    whose bytes hash to the BANNED `facebook/map-anything` digest -> `weight_banned`.
    banned_file = tmp_path / "banned" / "model.safetensors"
    banned_file.parent.mkdir()
    banned_file.write_bytes(banned_bytes)
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(banned_file),
            repo_id="facebook/dinov2-base",
            revision="f9e44c81",
            table=table,
        )
    assert exc.value.evidence["gate"] == "MEASURE_WEIGHT"
    assert exc.value.evidence["clause"] == "weight_banned"
    assert exc.value.evidence["repo_id"] == "facebook/map-anything"

    # 2. Same filename `model.safetensors` with unknown bytes -> `weight_hash_unverified`.
    unknown_file = tmp_path / "unknown" / "model.safetensors"
    unknown_file.parent.mkdir()
    unknown_file.write_bytes(unknown_bytes)
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(unknown_file),
            repo_id="facebook/dinov2-base",
            revision="f9e44c81",
            table=table,
        )
    assert exc.value.evidence["clause"] == "weight_hash_unverified"

    # 3. Exact pinned `ALLOWED` bytes -> admitted with full provenance receipt and age reading.
    allowed_file = tmp_path / "allowed" / "model.safetensors"
    allowed_file.parent.mkdir()
    allowed_file.write_bytes(allowed_bytes)
    receipt = MW.gate_measurement_weight(
        str(allowed_file),
        repo_id="facebook/dinov2-base",
        revision="f9e44c81",
        table=table,
        today="2026-11-15",
    )
    assert receipt["verdict"] == "ALLOWED"
    assert receipt["sha256"] == allowed_sha
    assert receipt["licence_age"]["advisory_after"] == "2027-02-09"
    assert receipt["licence_age"]["past_advisory_days"] is False


def test_l2_distinctive_banned_stems_halt_while_commercial_vggt_filename_is_not_stem_banned(tmp_path):
    """L2: Fails if `MonST3R`/`DUSt3R`/`VGGT-Omega` stems are missing or if a bare `vggt` stem bans `vggt_1B_commercial.pt`."""
    for bad_name in (
        "MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth",
        "DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth",
        "MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth",
        "cut3r_512_dpt.pth",
        "vggt_omega_checkpoint.safetensors",
        "insightface_glintr100.onnx",
    ):
        p = tmp_path / bad_name
        p.write_bytes(b"non-empty-checkpoint-bytes")
        with pytest.raises(MeasureWeightGate) as exc:
            MW.gate_measurement_weight(str(p))
        assert exc.value.evidence["clause"] == "weight_banned", bad_name

    # `vggt_1B_commercial.pt` MUST NOT match any distinctive banned stem; under its declared
    # repo it refuses as `weight_unverified` (HTTP 401 gated LICENSE), never as `weight_banned`.
    assert MW.classify_weight_stem("vggt_1B_commercial.pt") is None
    comm_path = tmp_path / "vggt_1B_commercial.pt"
    comm_path.write_bytes(b"commercial-checkpoint-placeholder")
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(comm_path),
            repo_id="facebook/VGGT-1B-Commercial",
            revision="ebb29a53",
        )
    assert exc.value.evidence["clause"] == "weight_unverified"


def test_l3_gate_refuses_before_importing_any_ml_dependency_and_publishes_to_errors_catalog(
    tmp_path, monkeypatch
):
    """L3: Fails if `MeasureWeightGate` imports `torch`/`safetensors`/`transformers` before refusing or is missing from `GATE_BY_ID`."""
    assert errors.GATE_BY_ID["MEASURE_WEIGHT"] is MeasureWeightGate
    assert errors.MeasureWeightGate is MeasureWeightGate

    _forbid_heavy_ml_imports(monkeypatch)

    # Missing file and empty file clauses on `gate_measurement_weight`.
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(str(tmp_path / "absent.safetensors"))
    assert exc.value.evidence["clause"] == "weight_path_not_a_file"

    empty_file = tmp_path / "empty.safetensors"
    empty_file.write_bytes(b"")
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(str(empty_file))
    assert exc.value.evidence["clause"] == "weight_file_empty"

    # Conditional weight without structured ruling -> `weight_conditional_unaccepted`;
    # with structured ruling + pinned sha256 -> admitted, still without importing `torch`.
    cond_bytes = b"synthetic-conditional-checkpoint-bytes"
    cond_sha = hashlib.sha256(cond_bytes).hexdigest()
    cond_file = tmp_path / "model.safetensors"
    cond_file.write_bytes(cond_bytes)
    cond_table = (
        {
            "repo_id": "example-org/synthetic-conditional-weight",
            "revision": "00000001",
            "filename": "model.safetensors",
            "sha256": cond_sha,
            "verdict": "CONDITIONAL",
            "licence": "Synthetic-Conditional-1.0 (test-only fixture)",
            "fetched": "2026-11-11",
            "source": "https://example.invalid/licenses/synthetic-conditional",
        },
    )
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(cond_file),
            repo_id="example-org/synthetic-conditional-weight",
            revision="00000001",
            table=cond_table,
        )
    assert exc.value.evidence["clause"] == "weight_conditional_unaccepted"

    valid_ruling = {
        "by": "legal-review-board",
        "date": "2026-11-25",
        "scope": "example-org/synthetic-conditional-weight",
        "licence_clause": "Synthetic-Conditional-1.0 §2",
    }
    admitted = MW.gate_measurement_weight(
        str(cond_file),
        repo_id="example-org/synthetic-conditional-weight",
        revision="00000001",
        ruling=valid_ruling,
        table=cond_table,
    )
    assert admitted["verdict"] == "CONDITIONAL"
    assert admitted["ruling"] == valid_ruling

    # Also verify `SD.load_dinov2_vitb14_embedder` hits `MeasureWeightGate` BEFORE touching `torch`.
    banned_monst3r = tmp_path / "MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth"
    banned_monst3r.write_bytes(b"monst3r-bytes")
    with pytest.raises(MeasureWeightGate) as exc:
        SD.load_dinov2_vitb14_embedder(str(banned_monst3r))
    assert exc.value.evidence["clause"] == "weight_banned"


def test_l4_loading_pi3_and_pi3x_refuses_as_banned(tmp_path, monkeypatch):
    """L4: Fails if `yyfz233/Pi3` or `yyfz233/Pi3X` (CC BY-NC 4.0 weights) is not refused as `weight_banned`."""
    _forbid_heavy_ml_imports(monkeypatch)

    pi3_file = tmp_path / "model.safetensors"
    pi3_bytes = b"synthetic-pi3-safetensors-bytes"
    pi3_sha = hashlib.sha256(pi3_bytes).hexdigest()
    pi3_file.write_bytes(pi3_bytes)

    for repo_id, rev in (("yyfz233/Pi3", "ae722e70"), ("yyfz233/Pi3X", "bb1deea4")):
        with pytest.raises(MeasureWeightGate) as exc:
            SD.load_dinov2_vitb14_embedder(str(pi3_file), repo_id=repo_id, revision=rev)
        assert exc.value.evidence["gate"] == "MEASURE_WEIGHT"
        assert exc.value.evidence["clause"] == "weight_banned"
        assert exc.value.evidence["repo_id"] == repo_id
        assert exc.value.evidence["licence"] == "CC-BY-NC-4.0"

        matches = [
            r
            for r in MW.MEASUREMENT_WEIGHTS
            if r.get("repo_id") == repo_id and r.get("revision") == rev
        ]
        assert len(matches) == 1, repo_id
        row = matches[0]
        assert row["verdict"] == "BANNED"
        assert row["licence"] == "CC-BY-NC-4.0"
        assert "9fa3ddb3f8d53041f8b2738df404f62223bbaa7b/README.md" in row["source"]

        # Even with a pinned sha256 and a structured `ruling`, BANNED Pi3/Pi3X weights cannot be admitted.
        pinned = (dict(row, sha256=pi3_sha),)
        with pytest.raises(MeasureWeightGate) as pinned_exc:
            MW.gate_measurement_weight(
                str(pi3_file),
                repo_id=repo_id,
                revision=rev,
                ruling={
                    "by": "test-reviewer",
                    "date": "2026-11-25",
                    "scope": repo_id,
                    "licence_clause": "test",
                },
                table=pinned,
            )
        assert pinned_exc.value.evidence["clause"] == "weight_banned"


def test_structured_ruling_required_for_conditional_weights_and_legacy_keyword_refused(tmp_path):
    """Item 1: a CONDITIONAL row unlocks only on a complete, in-scope structured `ruling`
    mapping (`by`, `date`, `scope`, `licence_clause`), records the full ruling on the receipt,
    and refuses the removed legacy keyword."""
    row_a_bytes = b"conditional-row-a-bytes"
    row_b_bytes = b"conditional-row-b-bytes"
    sha_a = hashlib.sha256(row_a_bytes).hexdigest()
    sha_b = hashlib.sha256(row_b_bytes).hexdigest()
    file_a = tmp_path / "row_a.safetensors"
    file_b = tmp_path / "row_b.safetensors"
    file_a.write_bytes(row_a_bytes)
    file_b.write_bytes(row_b_bytes)

    table = (
        {
            "repo_id": "example-org/cond-a",
            "revision": "rev-a",
            "filename": "row_a.safetensors",
            "sha256": sha_a,
            "verdict": "CONDITIONAL",
            "licence": "Custom-A",
            "fetched": "2026-11-11",
            "source": "https://example.invalid/cond-a",
        },
        {
            "repo_id": "example-org/cond-b",
            "revision": "rev-b",
            "filename": "row_b.safetensors",
            "sha256": sha_b,
            "verdict": "CONDITIONAL",
            "licence": "Custom-B",
            "fetched": "2026-11-11",
            "source": "https://example.invalid/cond-b",
        },
    )

    base_ruling = {
        "by": "release-signoff",
        "date": "2026-11-25",
        "scope": "example-org/cond-a",
        "licence_clause": "Custom-A §2.1",
    }

    # 1. Removed legacy keyword refuses cleanly with structured error.
    legacy_kw = "dir" + "ector_ruling"
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(file_a),
            repo_id="example-org/cond-a",
            revision="rev-a",
            table=table,
            **{legacy_kw: "accepted"},
        )
    assert exc.value.evidence["clause"] == "legacy_ruling_keyword_removed"
    assert exc.value.evidence["code"] == "legacy_ruling_keyword_removed"
    assert exc.value.evidence["message"] and exc.value.evidence["hint"]

    # 2. Truthy non-mapping string refuses.
    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(file_a),
            repo_id="example-org/cond-a",
            revision="rev-a",
            ruling="accepted-in-prose",
            table=table,
        )
    assert exc.value.evidence["clause"] == "invalid_conditional_ruling"
    assert exc.value.evidence["code"] == "invalid_conditional_ruling"
    assert exc.value.evidence["hint"]

    # 3. Missing or empty required field refuses and names the missing field.
    for missing_field in ("by", "date", "scope", "licence_clause"):
        partial = dict(base_ruling)
        partial.pop(missing_field)
        with pytest.raises(MeasureWeightGate) as exc:
            MW.gate_measurement_weight(
                str(file_a),
                repo_id="example-org/cond-a",
                revision="rev-a",
                ruling=partial,
                table=table,
            )
        assert exc.value.evidence["clause"] == "invalid_conditional_ruling"
        assert missing_field in exc.value.evidence["missing_fields"]
        assert missing_field in str(exc.value)
        assert exc.value.evidence["code"] and exc.value.evidence["message"] and exc.value.evidence["hint"]

        empty_val = dict(base_ruling)
        empty_val[missing_field] = "   " if missing_field != "scope" else []
        with pytest.raises(MeasureWeightGate) as exc:
            MW.gate_measurement_weight(
                str(file_a),
                repo_id="example-org/cond-a",
                revision="rev-a",
                ruling=empty_val,
                table=table,
            )
        assert exc.value.evidence["clause"] == "invalid_conditional_ruling"
        assert missing_field in exc.value.evidence["missing_fields"]

    # 4. Wrong date formats / invalid calendar dates refuse naming `date`.
    for bad_date in ("2026/11/25", "20261125", "2026-02-30", "not-a-date"):
        bad = dict(base_ruling, date=bad_date)
        with pytest.raises(MeasureWeightGate) as exc:
            MW.gate_measurement_weight(
                str(file_a),
                repo_id="example-org/cond-a",
                revision="rev-a",
                ruling=bad,
                table=table,
            )
        assert exc.value.evidence["clause"] == "invalid_conditional_ruling"
        assert exc.value.evidence["field"] == "date"
        assert "date" in str(exc.value)

    # 5. Valid ruling for row A unlocks row A and records the whole ruling, while
    #    refusing out-of-scope row B (including wildcard attempts).
    receipt = MW.gate_measurement_weight(
        str(file_a),
        repo_id="example-org/cond-a",
        revision="rev-a",
        ruling=base_ruling,
        table=table,
        today="2026-11-25",
    )
    assert receipt["verdict"] == "CONDITIONAL"
    assert receipt["ruling"] == base_ruling

    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(file_b),
            repo_id="example-org/cond-b",
            revision="rev-b",
            ruling=base_ruling,
            table=table,
        )
    assert exc.value.evidence["clause"] == "ruling_out_of_scope"
    assert exc.value.evidence["field"] == "scope"

    with pytest.raises(MeasureWeightGate) as exc:
        MW.gate_measurement_weight(
            str(file_b),
            repo_id="example-org/cond-b",
            revision="rev-b",
            ruling=dict(base_ruling, scope="*"),
            table=table,
        )
    assert exc.value.evidence["clause"] == "ruling_out_of_scope"

    # 6. Collection `scope` (e.g. list), wrong types for fields/scope, and unknown kwargs fail cleanly.
    list_ruling = dict(base_ruling, scope=["other/model", "example-org/cond-a"])
    receipt_list = MW.gate_measurement_weight(
        str(file_a),
        repo_id="example-org/cond-a",
        revision="rev-a",
        ruling=list_ruling,
        table=table,
        today="2026-11-25",
    )
    assert receipt_list["ruling"]["scope"] == ["other/model", "example-org/cond-a"]

    for bad_ruling in (
        dict(base_ruling, scope=123),
        dict(base_ruling, scope=[123]),
        dict(base_ruling, by=123),
    ):
        with pytest.raises(MeasureWeightGate) as bad_exc:
            MW.gate_measurement_weight(
                str(file_a),
                repo_id="example-org/cond-a",
                revision="rev-a",
                ruling=bad_ruling,
                table=table,
            )
        assert bad_exc.value.evidence["clause"] == "invalid_conditional_ruling"

    with pytest.raises(TypeError):
        MW.gate_measurement_weight(str(file_a), unknown_flag=True)

    assert MW._ruling_covers_row({"scope": []}, {"repo_id": "example-org/cond-a"}) is False
    assert MW._ruling_covers_row(base_ruling, {"repo_id": None}) is False


def test_m1_every_measurement_weight_row_carries_dated_fetch_and_mirrors_license_map():
    """M1: Fails if any `MEASUREMENT_WEIGHTS` row lacks an ISO `fetched` date, `source` / non-retrieval reason, or map entry."""
    assert len(MW.MEASUREMENT_WEIGHTS) >= 12
    map_path = os.path.join(REPO, "docs", "license-map.md")
    with open(map_path, encoding="utf-8") as fh:
        license_map_text = fh.read()

    for row in MW.MEASUREMENT_WEIGHTS:
        fetched = row.get("fetched")
        assert isinstance(fetched, str) and fetched, f"missing fetched date on {row}"
        datetime.date.fromisoformat(fetched)
        assert MW.licence_advisory_after(fetched) is not None
        assert fetched in license_map_text, (row.get("repo_id"), fetched)

        src = row.get("source")
        if src is None:
            reason = row.get("non_retrieval_reason")
            assert isinstance(reason, str) and len(reason) >= 15, (
                f"source=None row {row.get('repo_id')} must state non_retrieval_reason"
            )
        else:
            assert src.startswith("https://"), f"non-https source on {row}"
            assert src in license_map_text or src.split("://", 1)[-1] in license_map_text, (
                row.get("repo_id"),
                src,
            )

    for stem, row in MW.DISTINCTIVE_BANNED_STEMS.items():
        datetime.date.fromisoformat(row["fetched"])
        assert row["source"].startswith("https://"), stem
