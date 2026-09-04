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
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] no subject: a spend with no census id has no"):
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


def _probe_census(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(
        '{"PROBE": {"surfaces": "probe.surfaces.json"}}', encoding="utf-8"
    )
    return census_path


def test_canon_gate_cli_spend_refuse_creates_nothing(tmp_path):
    """Wave 10 (F-55e6d1cb): the refusal is now the typed `GateCanon` in process, not a
    bare `return 2`. `main` used to swallow it, print `CANON_REFUSE …` to stderr and return
    2 — which `raise SystemExit(2)` then carried straight past the `__main__` handler, so
    the `CANON_GATE_HALT` line that block exists to print never ran on this tool's PRIMARY
    refusal. The subprocess leg below is the half that could not be asserted before."""
    import canon_gate as cli

    out = tmp_path / "cli-spend"
    with pytest.raises(GateCanon) as exc:
        cli.main([
            "--roots", FIXTURES, "--census", str(_probe_census(tmp_path)),
            "spend", "--subject", "PROBE",
            "--prompt", "a wire figure in an empty studio, even lighting",
            "--out", str(out),
        ])
    assert exc.value.evidence, "a refusal without its measurement is not a receipt"
    assert not out.exists()


def test_a_canon_refusal_exits_2_with_exactly_one_CANON_GATE_HALT_line(tmp_path):
    """The tool's own `__main__` comment instructs a wrapper to key on the sentinel and
    never on the code alone, because argparse's usage errors also exit 2. Measured before
    the fix: a canon refusal printed `CANON_REFUSE …` on STDERR and exited 2 with no
    sentinel anywhere, while `--census <missing file>` — a plain FileNotFoundError, not a
    gate at all — DID print `CANON_GATE_HALT` and exit 1. Crashes got the machine-readable
    line; gate refusals did not."""
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "tools"))
    proc = subprocess.run(
        [sys.executable, os.path.join(repo, "tools", "canon_gate.py"),
         "--roots", FIXTURES, "--census", str(_probe_census(tmp_path)),
         "spend", "--subject", "PROBE",
         "--prompt", "a wire figure in an empty studio, even lighting",
         "--out", str(tmp_path / "cli-spend-sub")],
        capture_output=True, text=True, env=env, cwd=repo)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith("CANON_GATE_HALT ")]
    assert len(halts) == 1, proc.stdout
    payload = json.loads(halts[0][len("CANON_GATE_HALT "):])
    assert payload["error"] == "GateCanon"
    assert payload["evidence"], "the evidence dict rides the sentinel, on stdout"
    assert "CANON_GATE_OK" not in proc.stdout
    assert not (tmp_path / "cli-spend-sub").exists()


def test_an_unknown_subject_refuses_through_the_same_door(tmp_path):
    """`cmd_resolve` returned 2 for an unknown subject the same silent way. A refusal and a
    mistyped flag were the same observation to a wrapper."""
    import canon_gate as cli

    with pytest.raises(GateCanon) as exc:
        cli.main(["--roots", FIXTURES, "--census", str(_probe_census(tmp_path)),
                  "resolve", "--subject", "NOBODY"])
    assert exc.value.evidence["clause"] == "unknown_subject"


def test_a_canon_gate_success_prints_the_OK_sentinel(tmp_path, capsys):
    """The success half of the convention. This tool printed no success line at all."""
    import canon_gate as cli

    rc = cli.main(["--roots", FIXTURES, "--census", str(_probe_census(tmp_path)),
                   "spend", "--subject", "PROBE", "--prompt", COVERED,
                   "--out", str(tmp_path / "ok")])
    assert rc == 0
    out = capsys.readouterr().out
    assert len([ln for ln in out.splitlines()
                if ln.startswith("CANON_GATE_OK ")]) == 1, out


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

import _census_nodes as CN

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


# ------------------------------------------------------- the record check, made mechanical
#
# Wave 6, F-f770490d. This pair of clauses used to read
#
#     assert "CANON" in src
#     assert "canon_line(" in src
#
# over the builder's SOURCE TEXT. Measured: deleting `meta["gate_CANON"] = canon_ev` from
# build_i2v_payload.py and leaving one comment carrying the word CANON kept the whole suite
# green — the gate still fired, still printed, and its verdict no longer reached the record
# a later reader uses to tell whether canon was armed or escaped. A check a comment can
# satisfy is not a check.
#
# What replaces it walks main() and requires the canon call's RETURN VALUE to be routed
# into a record dict under a CANON key — `meta["gate_CANON"] = canon_ev` or
# `{"CANON": canon_ev}` — the two shapes the seven builders actually use. The predicate is
# exercised against a deliberately broken source below
# (`test_the_record_check_goes_red_when_the_record_line_is_deleted`) so that this file
# holds evidence the check can fail.

#: The three names the canon gate is called by across the builders.
CANON_CALLS = ("gate_write", "canon_spend", "require_canon")

#: Attribute calls that are in-tool refusals but carry no `gate_` prefix. A hint since wave
#: 12, not the definition: the predicate is behavioural and resolves a module-local helper
#: that raises. These two are `route_gates.verify` and `route_gates.frame_legality`, which
#: are attribute calls into another module and so are not reachable by the one-hop walk.
OTHER_GATE_CALLS = ("verify", "frame_legality", "parse_plate", "parse_boxes",
                    "frame_paths", "frame_population", "frames_by_number", "check_runs",
                    "common_frame_count", "bound_windows")

#: Every `ArmatureError` subclass name, from the live hierarchy AND from the tree. Computed
#: once; the walk above runs many times.
ERROR_NAMES = CN.armature_error_names()


# ONE implementation of each of these nodes, in `tests/_census_nodes.py` (F-e63ce880).
# `_called_name`, `_is_gate_call` and `_cli_body` used to be duplicated byte-for-byte
# between this file and `tests/test_instrument_write_ordering.py` — identical 1901-character
# AST dumps — and only that copy applied the mutually-exclusive-branch correction, so the
# two walks reported different write lines on `encode_control`, `measure_cascade_clip` and
# `rig_character` while each file's docstring claimed to compute the other's answer. None of
# the three is in `BUILDERS`, so no verdict differed on that tree; the divergence would have
# surfaced the day a module crossed between the two populations, with each file citing the
# other as its authority.
_called_name = CN.called_name
_cli_body = CN.cli_body


def _is_gate_call(called):
    return CN.is_refusal_call(called, CANON_CALLS, OTHER_GATE_CALLS)


def _main_of(src, what):
    fn = _cli_body(ast.parse(src))
    assert fn is not None, f"{what} has no module-level command-line function"
    return fn


def _canon_binding(fn):
    """The local name `main()` binds the canon evidence to, or None if it binds none."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and _called_name(node.value) in CANON_CALLS
                and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            return node.targets[0].id
    return None


def _canon_record_sites(fn, bound):
    """Every place `main()` puts the canon evidence into a record under a CANON key.

    Two shapes, both live in the tree: a subscript assignment
    (`meta["gate_CANON"] = canon_ev`, five builders) and a dict literal
    (`{"CANON": canon_ev}`, build_r2v_payload and build_t2v_payload).
    """
    sites = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) \
                and node.value.id == bound:
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and isinstance(target.slice.value, str)
                        and "CANON" in target.slice.value):
                    sites.append((target.slice.value, node.lineno))
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and "CANON" in key.value
                        and isinstance(value, ast.Name) and value.id == bound):
                    sites.append((key.value, node.lineno))
    return sites


def _prints_the_canon_line(fn, bound):
    """`print(canon_line(canon_ev))` — the announcement, on the evidence main() just built."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and _called_name(node) == "canon_line":
            if any(isinstance(a, ast.Name) and a.id == bound for a in node.args):
                return node.lineno
    return None


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_every_spend_builder_writes_a_canon_gate_and_prints_its_line(name):
    """The verdict reaches the record and the operator, asserted off the syntax tree.

    What this looks like if wrong: the gate fires, the build succeeds, and the payload
    record — the provenance a later reader uses to tell whether canon was armed or escaped
    — carries no CANON key at all, while the word CANON survives in a comment.
    """
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    fn = _main_of(src, name)
    bound = _canon_binding(fn)
    assert bound is not None, (
        f"{name}.main never binds the return of {'/'.join(CANON_CALLS)}; its canon verdict "
        f"cannot reach a record")
    sites = _canon_record_sites(fn, bound)
    assert sites, (
        f"{name}.main binds the canon evidence to {bound!r} and never writes it into a "
        f"record under a CANON key; the record would carry no canon verdict")
    assert _prints_the_canon_line(fn, bound) is not None, (
        f"{name}.main never calls canon_line({bound}); the census escape does not announce "
        f"itself")


#: The mutation the substring check could not see: the record line deleted, the word CANON
#: left behind in a comment. Applied to real builder source, in memory, so the predicate is
#: shown failing on a tree that differs from the shipped one in exactly this way.
def _delete_the_record_line(src):
    """Unhook the canon evidence from the record, both shapes, leaving the word behind."""
    import re

    subscripted, n1 = re.subn(
        r'(\w+)\[\s*"(?:gate_)?CANON"\s*\]\s*=\s*canon_ev\b',
        r'\1["CANON_is_no_longer_recorded"] = "a comment about CANON"', src)
    both, n2 = re.subn(
        r'"CANON"\s*:\s*canon_ev\b',
        '"CANON_is_no_longer_recorded": "a comment about CANON"', subscripted)
    return both, n1 + n2


@pytest.mark.parametrize("name", SPEND_BUILDERS)
def test_the_record_check_goes_red_when_the_record_line_is_deleted(name):
    """The falsifiability fixture for the check above.

    The old clause (`"CANON" in src`) passes on this mutated source — the word survives in
    the comment left in its place — and the AST clause fails. Both halves are asserted, so
    if the predicate ever stops being able to fail, this test says so rather than the
    builders quietly losing their verdicts.
    """
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    mutated, cut = _delete_the_record_line(src)
    assert cut, f"the mutation found no record line in {name}; it is not testing anything"
    assert "CANON" in mutated, "the substring check the AST clause replaced still passes"
    fn = _main_of(mutated, name)
    bound = _canon_binding(fn)
    assert bound is not None
    assert _canon_record_sites(fn, bound) == [], (
        f"the mutated {name} still records a canon verdict; the mutation missed")


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
    assert rec["gate_CANON"]["subject"] == "PERFORMER"
    assert "[canon] UNGATED: PERFORMER" in printed


# ------------------------------- the three builders that carried no behavioural record pin
#
# Wave 6, F-f770490d. Four of the seven builders had a block above driving `main()` and
# reading the written record; `build_i2v_payload`, `build_camera_i2v_payload` and
# `build_r2v_payload` had none, and the family check that stood in for them was a substring
# over source text. Each of the three is driven here on inputs this repo can produce, with
# the census below asserting that the set of builders with a behavioural pin is all seven.


def _banked_negative(tmp_path):
    """Wan's `shared_config.py`, the file the builders READ their negative from."""
    neg = tmp_path / "shared_config.py"
    neg.write_text("sample_neg_prompt = 'blurry, low quality'", encoding="utf-8")
    return neg


#: The identity clause is re-read from facet's twin JSON — an absolute path into a sibling
#: repo — so it is stubbed exactly as the animate fixture above stubs it. Everything else in
#: each `main()` is the real code path.
STUB_IDENTITY = "a jointed clay mannequin"


def _authored_png(path, size):
    """A real PNG at a route's own frame, written by the repo's dependency-free writer.

    Wave 12, F-08853dfb. Two fixtures below wrote 26 bytes of ASCII and an 8-byte PNG
    signature followed by prose, standing in for the entire image conditioning of an i2v
    route — the shape `resolve_start_frame` now refuses, because a record that asserts how
    the frame FITS the generation while carrying no measurement of the file is a claim, not
    a measurement.
    """
    import numpy as np

    from armature_core import pngio

    pngio.write_png(str(path), np.zeros((size[1], size[0], 3), dtype="uint8"))
    return path


def test_build_i2v_records_the_canon_verdict(tmp_path, monkeypatch):
    import build_animate_payload as E08
    import build_i2v_payload as bi

    monkeypatch.setattr(E08, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _banked_negative(tmp_path)
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"start_frame": "start.png"}), encoding="utf-8")
    # Gate PIN compares the strings this build rebuilds against E08's committed record, so
    # the fixture record carries exactly those two strings.
    e08 = tmp_path / "E08-record.json"
    e08.write_text(json.dumps({
        "experiment": "E08", "seed": 2026081211,
        "positive": STUB_IDENTITY + ". " + E08.SCENE_CLAUSE,
        "negative": E08.read_negative(str(neg))}), encoding="utf-8")
    out = tmp_path / "e11"
    registry = os.path.join(os.path.dirname(TOOLS), "specs", "E11-seeds.json")
    # Wave 10 (F-531c5f1f): the start frame is this route's whole image conditioning, and
    # the tool hashes it, so the fixture supplies a real file rather than a typed digest.
    start = tmp_path / "start.png"
    # Wave 12 (F-08853dfb): `resolve_start_frame` refuses a file whose IHDR it cannot
    # read, so the fixture is a real PNG at the route's own frame.
    _authored_png(start, (bi.WIDTH, bi.HEIGHT))
    _, printed = _capture(bi.main, [f"--uploads={up}", f"--out={out}",
                                    f"--negative-source={neg}", f"--e08-record={e08}",
                                    f"--start-frame={start}",
                                    f"--seeds-registry={registry}", *ESCAPE])
    rec = json.loads((out / f"{bi.EXPERIMENT}-probe-payload-record.json")
                     .read_text(encoding="utf-8"))
    assert rec["gate_CANON"]["verdict"] == "UNGATED"
    assert rec["gate_CANON"]["subject"] == "PERFORMER"
    assert "[canon] UNGATED: PERFORMER" in printed


def test_build_camera_i2v_records_the_canon_verdict(tmp_path, monkeypatch):
    import build_animate_payload as E08
    import build_camera_i2v_payload as bc
    from test_build_camera_i2v_payload import w1_record

    monkeypatch.setattr(E08, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _banked_negative(tmp_path)
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"start_frame": "w3_start.png"}), encoding="utf-8")
    w1 = tmp_path / "E11-probe-payload-record.json"
    w1.write_text(json.dumps(w1_record()), encoding="utf-8")
    # The one load-bearing control input, hashed from the artifact by the tool.
    start = tmp_path / "w3_start.png"
    _authored_png(start, (bc.WIDTH, bc.HEIGHT))
    out = tmp_path / "e12"
    registry = os.path.join(os.path.dirname(TOOLS), "specs", "E12-seeds.json")
    _, printed = _capture(bc.main, [f"--uploads={up}", f"--out={out}",
                                    f"--negative-source={neg}", f"--w1-record={w1}",
                                    f"--start-frame={start}",
                                    f"--seeds-registry={registry}", *ESCAPE])
    rec = json.loads(next(out.glob("*payload-record.json")).read_text(encoding="utf-8"))
    assert rec["gate_CANON"]["verdict"] == "UNGATED"
    assert rec["gate_CANON"]["subject"] == "PERFORMER"
    assert "[canon] UNGATED: PERFORMER" in printed


def test_build_r2v_records_the_canon_verdict(tmp_path):
    """The builder the finding measured: its own file asserts `gates.L_hosted`,
    `CASCADE_topology`, `CASCADE_ceiling` and `CASCADE_slot_frame_index`, and never
    `gates.CANON` — the key that says whether the spend was armed or escaped."""
    import build_r2v_payload as br
    from test_r2v_payload import NEG, PROMPT, REFS, SEEDS

    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"seeds": SEEDS}), encoding="utf-8")
    prompt = tmp_path / "prompt.json"
    prompt.write_text(json.dumps({"prompt": PROMPT, "negative_prompt": NEG}),
                      encoding="utf-8")
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps({"views": [
        {"slot": f"image{i + 1}", "view": f"turn_{i}", "upload_name": REFS[i]}
        for i in range(4)]}), encoding="utf-8")
    out = tmp_path / "e13"
    _, printed = _capture(br.main, ["--arm=A1", f"--seed={SEEDS[0]}", f"--seeds={seeds}",
                                    f"--prompt-file={prompt}", f"--refs={refs}",
                                    f"--out={out}", *ESCAPE])
    rec = json.loads((out / f"E13-A1-seed{SEEDS[0]}-payload-record.json")
                     .read_text(encoding="utf-8"))
    assert rec["gates"]["CANON"]["verdict"] == "UNGATED"
    assert rec["gates"]["CANON"]["subject"] == "PERFORMER"
    assert "[canon] UNGATED: PERFORMER" in printed


#: builder module -> the test in THIS file that drives its `main()` and reads the canon
#: verdict back out of the record it wrote. The census below is the family assertion: a
#: builder with no behavioural pin is the state F-f770490d measured, and it may not recur
#: silently.
BEHAVIOURAL_CANON_PINS = {
    "build_animate_payload": "test_build_animate_records_the_canon_verdict",
    "build_camera_i2v_payload": "test_build_camera_i2v_records_the_canon_verdict",
    "build_i2v_payload": "test_build_i2v_records_the_canon_verdict",
    "build_lora_arm_payload": "test_build_lora_arm_records_the_canon_verdict",
    "build_payload": "test_build_payload_records_the_canon_verdict_and_announces_the_escape",
    "build_r2v_payload": "test_build_r2v_records_the_canon_verdict",
    "build_t2v_payload": "test_build_t2v_records_the_canon_verdict",
}


def test_every_spend_builder_has_a_behavioural_canon_record_pin():
    """The census, not a spot check. Three of the seven had no test that ran the builder
    and read its record; the substring clause over source text was what stood in for
    them."""
    assert set(BEHAVIOURAL_CANON_PINS) == set(SPEND_BUILDER_MODULES), (
        "the behavioural-pin census and the enumerated spend builders disagree: "
        f"{sorted(set(BEHAVIOURAL_CANON_PINS) ^ set(SPEND_BUILDER_MODULES))}")
    missing = sorted(t for t in BEHAVIOURAL_CANON_PINS.values() if t not in globals())
    assert missing == [], f"named in the census, absent from this file: {missing}"

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
    # The flat assembler is bounded at MEASURED_FLAT_SLOT_MAX = 8 since wave 10 (the
    # largest flat batch S03 saw execute; the boundary between 8 and 81 is unlocated), and
    # Gate L wants a 4n+1 count — so it gets a 5-frame map. The cascade batches the batches
    # and keeps E02's real 33-frame record. The property under test is that the emitted
    # graph carries no text at all, which is independent of clip length.
    if name == "build_assembly_payload":
        small = tmp_path / "uploads_small.json"
        small.write_text(json.dumps({f"{i:05d}": f"srv_{i:05d}.png" for i in range(5)}),
                         encoding="utf-8")
        uploads = str(small)
    else:
        uploads = upload_record("outputs/E02/uploads_depth_pershot.json")
    mod.main(["--uploads", uploads, "--out", str(out)])

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


def _gate_and_write_lines(src, what):
    """`({line: refusal}, {line: write kind})` for the builder's CLI body.

    Wave 6, F-f770490d. This walk used to count ONLY `gate_write` / `canon_spend` /
    `require_canon` and then compare `min(gates_at) < min(writes_at)` — the FIRST gate
    against the FIRST write. Two ways that reads green over a real defect: every refusal
    that is not the canon gate is invisible to it, and a gate BELOW the mkdir does not
    move the minimum. Measured on `build_t2v_payload.main`: `os.makedirs` at 486 sits
    directly under `canon_spend` at 485 and ABOVE `route_gates.verify` (495),
    `gate_s_registration` (496) and the Gate L check (497-499), and `485 < 486` passed.
    Driving it with an unregistered seed raises Gate S and leaves an empty run directory
    on disk — an empty directory beside real ones, read later as a run that happened.

    So: every in-tool refusal the CLI body runs is collected, and the first write is
    compared against the LAST of them.

    WAVE 12, F-183635ad + F-e63ce880 — ONE implementation, and it is behavioural. The walk
    is `tests/_census_nodes.refusal_and_write_lines`, shared with
    `tests/test_instrument_write_ordering.py`; a refusal is any `raise` of an
    `ArmatureError` subclass, inline or one hop through a module-local helper, unioned with
    the named gate calls. The mutually-exclusive-branch correction rides with it, so the two
    files can no longer answer differently about the same module.
    """
    return CN.refusal_and_write_lines(
        src, error_names=ERROR_NAMES, canon_calls=CANON_CALLS,
        other_gate_calls=OTHER_GATE_CALLS)


def test_the_builders_and_the_instruments_are_read_by_the_same_function():
    """F-e63ce880's fix, asserted rather than described.

    The shape `tests/test_packaging.py` already uses for the two import scanners: not "these
    two walks agree today" but "there is one walk". This file's docstring for
    `gate_and_write_lines` in the instruments census claimed the two computed the same
    shape; they did not, and nothing could have told a reader which was authoritative.
    """
    import test_instrument_write_ordering as WO

    assert _cli_body is WO._cli_body is CN.cli_body
    assert _called_name is WO._called_name is CN.called_name
    for name in sorted(set(BUILDERS)):
        src = _builder_source(name)
        assert _gate_and_write_lines(src, name) == WO.gate_and_write_lines(src, name), name


@pytest.mark.parametrize("name", BUILDERS)
def test_every_spend_builder_rules_on_canon_before_it_writes_anything(name):
    """WAVE 8, F-f8c00be2 — parametrized over BUILDERS, not `SPEND_BUILDER_MODULES`.

    The law here is "a refused spend leaves nothing behind". The population was
    `sorted(set(BUILDERS) - TEXTLESS_ASSEMBLERS)` — seven builders — while NINE write.
    The two assemblers' exemption is from Gate CANON, on the ground that they ship no
    prompt for a canon router to check; that is a different law from this one, and it was
    silently borrowed. Measured 2026-09-04 with this file's own `_gate_and_write_lines`:
    both assemblers DO run in-tool refusals and DO write — `build_assembly_payload` gates
    at 266, 268, 270 and 278 and first writes at 308; `build_cascade_payload` gates at
    153-171 and first writes at 210 — so both order correctly today and no live defect
    follows. What follows is that either could grow an `os.makedirs` above its last
    refusal and leave an empty run directory beside real ones, read later as a run that
    happened, with no test in the population to notice.

    Ordering, read off the source because most of these mains need Blender-adjacent
    inputs to reach their write. Every in-tool refusal main() runs — the canon gate and
    every `gate_*` / `route_gates.verify` / `frame_legality` call beside it — must come
    before the first `os.makedirs` or `open(..., "w")` in that function: the gate fires
    inside the tool that performs the irreversible step, not beside it, and a refused
    spend leaves nothing behind."""
    gates_at, writes_at = _gate_and_write_lines(_builder_source(name), name)

    assert gates_at, f"{name}.main runs no in-tool refusal at all"
    assert writes_at, f"{name}.main writes nothing; this check is reading the wrong function"
    last_gate, first_write = max(gates_at), min(writes_at)
    assert last_gate < first_write, (
        f"{name}.main writes at line {first_write} ({writes_at[first_write]}) but is still "
        f"gating at line {last_gate} ({gates_at[last_gate]}); every refusal below the "
        f"first write leaves an output directory behind when it fires. Gates in main: "
        f"{sorted((ln, n) for ln, n in gates_at.items())}")


def _write_before_the_first_gate(src, what):
    """Move a write ABOVE main()'s first refusal — the defect the check exists to catch."""
    gates_at, _ = _gate_and_write_lines(src, what)
    at = min(gates_at)
    lines = src.splitlines(keepends=True)
    target = lines[at - 1]
    indent = target[:len(target) - len(target.lstrip())]
    lines.insert(at - 1, f"{indent}os.makedirs(_probe_out, exist_ok=True)\n")
    return "".join(lines)


@pytest.mark.parametrize("name", BUILDERS)
def test_the_ordering_check_goes_red_when_a_write_moves_above_the_gate(name):
    """The falsifiability fixture for the check above, on each builder's real source.

    What this looks like if the check were wrong in the specific way wave 5 measured: a
    builder creates its output directory before a refusal runs, the refusal fires, and the
    empty directory is left on disk while the suite stays green.
    """
    src = _builder_source(name)
    mutated = _write_before_the_first_gate(src, name)
    gates_at, writes_at = _gate_and_write_lines(mutated, name)
    assert gates_at and writes_at
    assert not max(gates_at) < min(writes_at), (
        f"a write inserted above {name}.main's first gate did not move the comparison; "
        f"the ordering check cannot fail")


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
