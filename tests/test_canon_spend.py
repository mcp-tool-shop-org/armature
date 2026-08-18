"""The spend helper never creates the directory it refused to write into.

Nominated chip: a refused spend leaves no output directory.
"""

import os
import sys

import pytest

from armature_core import canon as C
from armature_core.errors import GateCanon

from test_canon import COVERED, FIXTURES, TEST_CENSUS

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def test_a_refused_spend_creates_no_output_directory(tmp_path):
    """Nominated chip. The gate fires before mkdir; the caller never reaches it.

    What this looks like if wrong: require_canon (or gate_write) creates
    out_dir so it can write a refusal receipt, and a later session treats
    the directory as evidence a payload was built.
    """
    out = tmp_path / "payloads" / "E99"
    assert not out.exists()
    with pytest.raises(GateCanon) as exc:
        C.gate_write(
            "PROBE",
            "a wire figure in an empty studio, even lighting",
            out_dir=str(out),
            census=TEST_CENSUS,
            search_roots=[FIXTURES],
        )
    assert "featureless head" in str(exc.value)
    assert not out.exists()
    assert not out.parent.exists()


def test_a_silent_subject_creates_no_output_directory(tmp_path):
    out = tmp_path / "fresh-spend"
    with pytest.raises(GateCanon) as exc:
        C.gate_write(None, COVERED, out_dir=str(out),
                     census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "missing_subject"
    assert not out.exists()


def test_gate_write_does_not_itself_mkdir_on_a_pass(tmp_path):
    """Passing the gate is not a licence to create the directory. The builder does that."""
    out = tmp_path / "should-not-appear"
    ev = C.gate_write("PROBE", COVERED, out_dir=str(out),
                      census=TEST_CENSUS, search_roots=[FIXTURES])
    assert ev["verdict"] == "ARMED"
    assert not out.exists()


def test_an_existing_directory_is_not_deleted_on_refuse(tmp_path):
    """The gate does not compensate by destroying operator work."""
    out = tmp_path / "already"
    out.mkdir()
    marker = out / "kept.txt"
    marker.write_text("stay", encoding="utf-8")
    with pytest.raises(GateCanon):
        C.gate_write(None, COVERED, out_dir=str(out),
                     census=TEST_CENSUS, search_roots=[FIXTURES])
    assert marker.read_text(encoding="utf-8") == "stay"


def test_build_payload_main_refuses_silence_and_writes_nothing(tmp_path):
    """The builder is the irreversible step. Silence is a refuse. No parent dir."""
    import build_payload as bp

    out = tmp_path / "fresh" / "A1a.json"
    with pytest.raises(GateCanon) as exc:
        bp.main(["--experiment", "E02", "--arm", "A1a", "--out", str(out)])
    assert exc.value.evidence["clause"] == "missing_subject"
    assert not out.exists()
    assert not out.parent.exists()


def test_build_payload_checkbox_on_probe_writes_nothing(tmp_path, monkeypatch):
    """--no-canon on a subject that HAS surfaces is the checkbox trap, at the builder."""
    import build_payload as bp

    monkeypatch.setattr(C, "DEFAULT_ROOT", FIXTURES)
    # Probe is not in the production census; point the builder at the test census.
    monkeypatch.setattr(
        "armature_core.canon_census.CENSUS",
        TEST_CENSUS,
    )
    out = tmp_path / "fresh" / "A1a.json"
    with pytest.raises(GateCanon) as exc:
        bp.main([
            "--experiment", "E02", "--arm", "A1a", "--out", str(out),
            "--subject", "PROBE", "--no-canon",
            "--canon-prompt", COVERED,
        ])
    assert exc.value.evidence["clause"] == "checkbox"
    assert not out.exists()


def test_canon_gate_cli_spend_refuse_creates_nothing(tmp_path):
    import canon_gate as cli

    census_path = tmp_path / "census.json"
    census_path.write_text(
        '{"PROBE": {"surfaces": "probe.surfaces.json"}}', encoding="utf-8"
    )
    out = tmp_path / "cli-spend"
    rc = cli.main([
        "--roots", FIXTURES, "--census", str(census_path),
        "spend", "--subject", "PROBE",
        "--prompt", "a wire figure in an empty studio, even lighting",
        "--out", str(out),
    ])
    assert rc == 2
    assert not out.exists()
