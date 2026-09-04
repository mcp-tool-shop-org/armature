"""The spend helper never creates the directory it refused to write into.

Nominated chip: a refused spend leaves no output directory.
"""

import glob
import importlib
import json
import os
import sys

import pytest

from armature_core import canon as C
from armature_core.errors import GateCanon

from conftest import upload_record
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


# ============================================================ every builder, enumerated
#
# The tests above exercise ONE builder. Nine files under `tools/` match
# `build_*payload*.py`, seven wire Gate CANON and two do not — and until this block
# existed, no test in `tests/` would have failed if a spend builder skipped the gate
# entirely. Measured 2026-09-03: `build_assembly_payload.main(['--uploads', <map>,
# '--out', <fresh dir>])` creates the directory and writes both its files, its record
# carries no canon key, and `--subject` does not appear in its source at all;
# `tests/test_assembly.py:167` and `tests/test_cascade.py:216` both call that same
# `main()` and assert only about frame ordering.
#
# Enumeration by glob is the point: a builder added later joins these checks whether or
# not anyone remembers to add it.

BUILDER_GLOB = "build_*payload*.py"

#: The two documented exceptions. They assemble already-rendered frames into a video —
#: LoadImage -> BatchImagesNode -> CreateVideo -> SaveVideo and nothing else — so they
#: carry ZERO text inputs and there is no prompt for a canon router to check in either
#: direction. That claim is asserted below against the graph each one actually builds,
#: not taken from this comment.
TEXTLESS_ASSEMBLERS = {"build_assembly_payload", "build_cascade_payload"}

SPEND_FLAGS = ("subject", "no_canon", "canon_prompt")


def _builder_names():
    names = sorted(os.path.basename(p)[:-3]
                   for p in glob.glob(os.path.join(TOOLS, BUILDER_GLOB)))
    assert len(names) >= 9, f"the glob found only {names}; it is not reaching tools/"
    return names


def _builder_source(name):
    with open(os.path.join(TOOLS, name + ".py"), encoding="utf-8") as fh:
        return fh.read()


def _capture_parser(mod):
    """The builder's own ArgumentParser, taken as it is handed to `add_spend_flags`.

    Every canon builder calls `add_spend_flags(ap)` immediately before `parse_args`, so
    spying on that one call reaches the real parser without a copy of it living here —
    and a builder that stops calling it is exactly what these checks exist to catch.
    """
    box = {}
    real = mod.add_spend_flags

    def spy(ap):
        box["ap"] = ap
        return real(ap)

    mod.add_spend_flags = spy
    try:
        try:
            mod.main([])
        except BaseException:
            # argparse's SystemExit on a missing required flag, or the gate itself on a
            # builder with no required flags. Either way the parser has been built.
            pass
    finally:
        mod.add_spend_flags = real
    assert "ap" in box, f"{mod.__name__} never called add_spend_flags"
    return box["ap"]


def _spend_builders():
    """`(name, module)` for every builder that wires the spend gate."""
    out = []
    for name in _builder_names():
        if name in TEXTLESS_ASSEMBLERS:
            continue
        out.append((name, importlib.import_module(name)))
    return out


BUILDERS = _builder_names()
SPEND_BUILDERS = sorted(set(BUILDERS) - TEXTLESS_ASSEMBLERS)


def test_the_only_builders_without_the_spend_gate_are_the_recorded_two():
    """A builder that quietly stops importing `gate_write` is a spend with no subject.

    The partition is measured off the source, not asserted from the list: if a third
    builder loses the gate, or one of the two acquires text inputs and needs it, this is
    the check that says so.
    """
    without = sorted(n for n in BUILDERS
                     if "gate_write" not in _builder_source(n)
                     and "require_canon" not in _builder_source(n))
    assert set(without) == TEXTLESS_ASSEMBLERS, (
        f"builders with no canon gate: {without}; the recorded exceptions are "
        f"{sorted(TEXTLESS_ASSEMBLERS)}")


@pytest.mark.parametrize("name", sorted(TEXTLESS_ASSEMBLERS))
def test_a_textless_assembler_carries_no_text_for_a_canon_router_to_check(name, tmp_path):
    """The exception, asserted rather than commented.

    These two are exempt from Gate CANON because there is no prompt in what they build —
    `canon.texts_from_api_graph` finds every string input named text/prompt/positive, and
    on their graphs it finds none. The day one of them grows a prompt, this fails and the
    exemption has to be re-earned.
    """
    mod = importlib.import_module(name)
    out = tmp_path / "assembled"
    mod.main(["--uploads", upload_record("outputs/E02/uploads_depth_pershot.json"),
              "--out", str(out)])

    graphs = sorted(p for p in os.listdir(out) if p.endswith(".api.json"))
    assert graphs, sorted(os.listdir(out))
    for g in graphs:
        with open(out / g, encoding="utf-8") as fh:
            wf = json.load(fh)
        assert C.texts_from_api_graph(wf) == [], (
            f"{name} emits text in {g}; a spend that carries a prompt has a subject to "
            f"name, and this builder wires no canon gate")
        classes = {n["class_type"] for n in wf.values()}
        assert classes <= {"LoadImage", "BatchImagesNode", "CreateVideo", "SaveVideo"}, (
            f"{name} builds {sorted(classes)}; it is exempt on the ground that it only "
            f"assembles already-rendered frames")

    assert "--subject" not in _builder_source(name), (
        f"{name} exposes --subject but wires no gate: a flag that is read by nothing is "
        f"a checkbox")


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_every_spend_builder_exposes_the_spend_flags(name):
    """`--subject` optional at argparse (so silence is a GateCanon, not an argparse
    error), `--no-canon` as the census-backed escape, `--canon-prompt` for the text the
    router checks. A builder missing one of them cannot be refused for the right reason.
    """
    ap = _capture_parser(importlib.import_module(name))
    dests = {a.dest for a in ap._actions}
    assert set(SPEND_FLAGS) <= dests, f"{name} is missing {sorted(set(SPEND_FLAGS) - dests)}"
    subject = next(a for a in ap._actions if a.dest == "subject")
    assert not subject.required and subject.default is None, (
        f"{name}'s --subject is required at argparse; silence must reach the gate as a "
        f"GateCanon, not bounce off argparse with a different error")


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_every_spend_builder_rules_on_canon_before_it_writes_anything(name):
    """Ordering, read off the source because most of these mains need Blender-adjacent
    inputs to reach their write. `gate_write` must be called in `main`, and it must come
    before the first `os.makedirs` or `open(..., "w")` in that function — the gate fires
    inside the tool that performs the irreversible step, not beside it."""
    import ast

    tree = ast.parse(_builder_source(name))
    fn = next((n for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    assert fn is not None, f"{name} has no module-level main()"

    gates_at, writes_at = [], []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (func.id if isinstance(func, ast.Name)
                  else func.attr if isinstance(func, ast.Attribute) else "")
        if called == "gate_write":
            gates_at.append(node.lineno)
        elif called == "makedirs":
            writes_at.append(node.lineno)
        elif (called == "open" and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and "w" in str(node.args[1].value)):
            writes_at.append(node.lineno)

    assert gates_at, f"{name}.main never calls gate_write"
    assert writes_at, f"{name}.main writes nothing; this check is reading the wrong function"
    assert min(gates_at) < min(writes_at), (
        f"{name}.main calls gate_write at line {min(gates_at)} but writes at line "
        f"{min(writes_at)}; a refused spend must leave no output behind")


#: Builders whose `main()` can be driven to the gate without an input this repo cannot
#: produce on a runner. The other five read an uploads map, a wave record or
#: `E:/AI/facet/docs/experiments/E33-twin-prompts-r3.json` — an absolute path into a
#: sibling repo — before they reach `gate_write`, so their ordering is checked by the AST
#: test above and their refusal cannot be exercised here. That is a gap, and it is named
#: rather than hidden: the ordering assertion is what stands in for it.
DRIVABLE_BUILDERS = {
    "build_payload": lambda out: ["--experiment", "E02", "--arm", "A1a", "--out", out],
    "build_t2v_payload": lambda out: ["--out", out],
}


@pytest.mark.parametrize("name", sorted(DRIVABLE_BUILDERS))
def test_a_spend_builder_with_no_subject_refuses_and_writes_nothing(name, tmp_path):
    """The three assertions `test_build_payload_main_refuses_silence_and_writes_nothing`
    makes for one builder, made for every builder that can be driven here: the refusal is
    a GateCanon naming `missing_subject`, and neither the out path nor its parent exists
    afterwards."""
    mod = importlib.import_module(name)
    out = str(tmp_path / "fresh" / "payload.json")
    with pytest.raises(GateCanon) as exc:
        mod.main(DRIVABLE_BUILDERS[name](out))
    assert exc.value.evidence["clause"] == "missing_subject"
    assert not os.path.exists(out)
    assert not os.path.exists(os.path.dirname(out))


def test_the_drivable_set_is_a_subset_of_the_enumerated_builders():
    """A recipe naming a builder that no longer exists would silently stop running."""
    assert set(DRIVABLE_BUILDERS) <= set(SPEND_BUILDERS), sorted(DRIVABLE_BUILDERS)
