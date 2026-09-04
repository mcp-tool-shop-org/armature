"""The spend helper never creates the directory it refused to write into.

Nominated chip: a refused spend leaves no output directory.
"""

import json
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


# ---------------------------------------------------------------------------------------
# Wave 3, F-5b968bec / F-dfcc0bea. Two defects that rode together in every spend builder.
#
# (1) Every builder called `gate_write(...)` and DISCARDED its return. `require_canon`
#     builds an evidence dict carrying the verdict (ARMED / UNGATED), the clause and an
#     `announcement` string that canon.py says exists so the census escape announces
#     itself. Measured: `build_r2v_payload.py --subject=BLACKGUARD --no-canon` printed
#     BUILD_R2V_OK with four gate lines and no canon line, and the written record's gates
#     were exactly CEILING_one_paid_node, L_hosted, ROUTE, S_build_time — a payload record
#     submitted as the provenance for a paid generation with no way to tell whether canon
#     was armed or escaped. The same helper through canon_gate.py DID print it.
#
# (2) `--canon-prompt` was gated in place of the text the builder ships. Measured against a
#     census row carrying a surfaces file: without the flag the build was refused; with the
#     flag set to a covering string the identical invocation succeeded and the record's
#     prompt was the very text the gate had just refused.

import ast
import glob
import io
import contextlib

SPEND_BUILDERS = sorted(
    os.path.basename(p) for p in glob.glob(os.path.join(TOOLS, "build_*payload*.py"))
    if "add_spend_flags" in open(p, encoding="utf-8").read())


def _module_ast(name):
    with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
        return ast.parse(fh.read()), fh


def test_the_spend_builder_set_is_the_seven_the_finding_names():
    """Enumerated from the tree, not typed: a builder added later must join this family or
    fail here rather than quietly shipping a record with no canon verdict."""
    assert SPEND_BUILDERS == [
        "build_animate_payload.py", "build_camera_i2v_payload.py", "build_i2v_payload.py",
        "build_lora_arm_payload.py", "build_payload.py", "build_r2v_payload.py",
        "build_t2v_payload.py"]


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_no_spend_builder_discards_the_canon_evidence(name):
    """The defect's exact shape: the canon call as a bare expression statement, its return
    thrown away. Walked mechanically because seven files is where a family fix rots."""
    with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    discarded = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        fn = node.value.func
        called = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
        if called in ("gate_write", "canon_spend", "require_canon"):
            discarded.append(f"{name}:{node.lineno}")
    assert discarded == [], f"canon evidence discarded at {discarded}"


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_every_spend_builder_writes_a_canon_gate_and_prints_its_line(name):
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    assert "CANON" in src, f"{name} puts no canon verdict in its record"
    assert "canon_line(" in src, f"{name} never prints the canon verdict"


# ------------------------------------------------------------------ behavioural, per tool


def _capture(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **kw)
    return out, buf.getvalue()


ESCAPE = ["--subject", "PERFORMER", "--no-canon"]


def test_build_payload_records_the_canon_verdict_and_announces_the_escape(tmp_path):
    import build_payload as bp

    # E03 arm B2 is the null arm: no uploads manifest, no reference, so main() runs end to
    # end from the repo alone.
    out = tmp_path / "run" / "B2.json"
    _, printed = _capture(bp.main, ["--experiment", "E03", "--arm", "B2",
                                    "--out", str(out), *ESCAPE])
    meta = json.loads((out.parent / "B2.meta.json").read_text(encoding="utf-8"))
    assert meta["gate_CANON"]["verdict"] == "UNGATED"
    assert meta["gate_CANON"]["subject"] == "PERFORMER"
    assert "[canon] UNGATED: PERFORMER" in printed


def test_build_payload_refuses_a_canon_prompt_that_is_not_the_shipped_text(tmp_path):
    """`build()` re-derives the payload's positive from EXPERIMENTS, so --canon-prompt could
    never be the shipped text — it could only replace what the router examined."""
    import build_payload as bp

    out = tmp_path / "fresh" / "B2.json"
    with pytest.raises(GateCanon) as exc:
        bp.main(["--experiment", "E03", "--arm", "B2", "--out", str(out),
                 "--subject", "PERFORMER", "--no-canon",
                 "--canon-prompt", "a completely different sentence"])
    assert exc.value.evidence["clause"] == "gated_text_is_not_shipped_text"
    assert not out.parent.exists()


def test_build_t2v_records_the_canon_verdict(tmp_path):
    import build_t2v_payload as bt

    out = tmp_path / "t2v"
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"seeds": [2026081201]}), encoding="utf-8")
    _, printed = _capture(bt.main, [f"--seeds={seeds}", f"--out={out}", *ESCAPE])
    rec = json.loads(next(out.glob("*payload-record.json")).read_text(encoding="utf-8"))
    assert rec["gates"]["CANON"]["verdict"] == "UNGATED"
    assert "[canon] UNGATED: PERFORMER" in printed


def test_build_lora_arm_records_the_canon_verdict(tmp_path):
    import build_lora_arm_payload as bl

    base = os.path.join(os.path.dirname(TOOLS), "tests", "fixtures",
                        "E12-w3-camera-i2v.api.json")
    out = tmp_path / "e14"
    _, printed = _capture(bl.main, [
        f"--base={base}", "--arm=T", f"--out={out}",
        f"--seeds-registry={os.path.join(os.path.dirname(TOOLS), 'specs', 'E14-seeds.json')}",
        "--seed=2026081233", *ESCAPE])
    rec = json.loads(next(out.glob("*payload-record.json")).read_text(encoding="utf-8"))
    assert rec["gates"]["CANON"]["verdict"] == "UNGATED"
    assert "[canon] UNGATED: PERFORMER" in printed


def test_build_animate_records_the_canon_verdict(tmp_path, monkeypatch):
    """The identity clause is read from a file outside this repo, so the two prompt sources
    are stubbed; everything else is the real main()."""
    import build_animate_payload as BAP

    neg = tmp_path / "shared_config.py"
    neg.write_text("sample_neg_prompt = 'blurry, low quality'", encoding="utf-8")
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"reference": "r.png", "pose_pack": "p.png",
                              "pose_frames": 65}), encoding="utf-8")
    monkeypatch.setattr(BAP, "identity_clause",
                        lambda *a, **k: ("a jointed clay mannequin", "orig", []))
    out = tmp_path / "e08"
    registry = os.path.join(os.path.dirname(TOOLS), "specs", "E08-seeds.json")
    _, printed = _capture(BAP.main, [f"--uploads={up}", f"--out={out}",
                                     f"--negative-source={neg}", "--seed=2026081211",
                                     f"--seeds-registry={registry}", *ESCAPE])
    rec = json.loads((out / "E08-probe-payload-record.json").read_text(encoding="utf-8"))
    assert rec["gate_CANON"]["verdict"] == "UNGATED"
    assert "[canon] UNGATED: PERFORMER" in printed
