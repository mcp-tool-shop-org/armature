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
SPEND_BUILDER_MODULES = sorted(set(BUILDERS) - TEXTLESS_ASSEMBLERS)


def test_the_only_builders_without_the_spend_gate_are_the_recorded_two():
    """A builder that quietly stops importing `gate_write` is a spend with no subject.

    The partition is measured off the source, not asserted from the list: if a third
    builder loses the gate, or one of the two acquires text inputs and needs it, this is
    the check that says so.
    """
    without = sorted(n for n in BUILDERS
                     if not any(g in _builder_source(n) for g in ("gate_write", "canon_spend", "require_canon"))
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


@pytest.mark.parametrize("name", SPEND_BUILDER_MODULES)
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


@pytest.mark.parametrize("name", SPEND_BUILDER_MODULES)
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
        if called in ("gate_write", "canon_spend", "require_canon"):
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
    assert set(DRIVABLE_BUILDERS) <= set(SPEND_BUILDER_MODULES), sorted(DRIVABLE_BUILDERS)


# ---------------------------------- every gate, not just the canon one (wave 6, F-c6580beb)

#: Calls that are an in-tool gate for the purposes of the ordering census below. Named by
#: shape rather than enumerated, because the enumeration is what went stale: the check
#: above walks `gate_write` / `canon_spend` / `require_canon` only, so Gates ROUTE, S and L
#: were invisible to it and `build_t2v_payload` passed with `os.makedirs` sitting directly
#: under `canon_spend` and ABOVE all three of them (485 < 486 satisfied first-to-first).
def _is_gate_call(called):
    return (called.startswith("gate_") or called.endswith("_gate")
            or called in ("canon_spend", "require_canon", "verify", "frame_legality"))


@pytest.mark.parametrize("name", SPEND_BUILDER_MODULES)
def test_every_in_tool_gate_precedes_the_first_write_not_only_the_canon_one(name):
    """A refused spend leaves no output directory — for EVERY gate the tool performs, not
    just the first one. The first-to-first comparison above cannot see a gate below a
    mkdir; this compares the LAST gate call in `main` against the first write."""
    import ast

    tree = ast.parse(_builder_source(name))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "main")

    gates_at, writes_at = [], []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (func.id if isinstance(func, ast.Name)
                  else func.attr if isinstance(func, ast.Attribute) else "")
        if _is_gate_call(called):
            gates_at.append((node.lineno, called))
        elif called == "makedirs":
            writes_at.append((node.lineno, called))
        elif (called == "open" and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and "w" in str(node.args[1].value)):
            writes_at.append((node.lineno, called))

    assert gates_at, f"{name}.main calls no gate this census can see"
    assert writes_at, f"{name}.main writes nothing; the census is reading the wrong function"
    last_gate, first_write = max(gates_at), min(writes_at)
    assert last_gate[0] < first_write[0], (
        f"{name}.main calls {last_gate[1]} at line {last_gate[0]}, below its first write "
        f"({first_write[1]}) at line {first_write[0]}; a refused spend must leave no "
        f"output behind, and that binds on every gate the tool performs")
