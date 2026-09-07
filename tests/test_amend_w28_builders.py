"""Wave 28, builders — Stage C amend #1. Eight approved findings, none deferred.

Each block names the finding, the OPERAND the wave-27 auditor measured on `3380ae2`, the
siblings enumerated beside it, and — where a refusal is involved — the halt line READ back
out of the tool's own `__main__`. Every fix here was run once with the fix reverted; the
`reverted-red` note in each block records what the reverted tree did.

The rules this wave carries, on top of wave 18's five, wave 22's one and wave 24's two
(`wave-28/coordinator-brief.md` §"What Stage C adds to the rule"):

* a refusal's `message` is for a person and its `evidence` is for a census — both must hold;
* help text is MEASURED, not written by feel: a `description=` saying what the tool does and
  to whom, `help=` on every flag an operator reaches, `choices=`/enums read from the table
  that owns them, and the default named where a default matters;
* the silent-overwrite family is ONE mechanism at two anchors, spelled identically across
  builders and instruments (`--overwrite`, clause `output_already_exists`, one sentence,
  `out_dir_pre_existed` / `overwrote`) — agreed in the relay BEFORE the first edit
  (`wave-28/seams-inbox.md`: instruments @ 13:20, coordinator @ 13:2x);
* a wait says it is alive: elapsed and a bound printed, every subprocess with `timeout=`,
  and a bound that is reached is a NAMED refusal carrying the partial state, never a retry
  (coordinator's ruling @ 23:1x, adopted at builders @ 23:30).
"""

import ast
import json
import re
import os
import subprocess
import sys

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import assembly as AS
from armature_core import route_gates as RG

import build_assembly_payload as BAP
import build_cascade_payload as BCP
import build_r2v_payload as BR2V
import build_lora_arm_payload as BLA
import fetch_run as F
import gate_saved_graph as GSG

REPO = os.path.dirname(TOOLS)
SPECS = os.path.join(REPO, "specs")

import _census_nodes as CN

#: The thirteen graph / admit / fetch tools this domain owns for parser censuses, plus the
#: wave-34 boundary pair (submitter + uploads map) recorded as their own class. Derived
#: from the owned globs, not from a hand-kept list of "the ones I remembered".
_GRAPH_AND_ADMIT = CN.spend_and_fetch_tools()
_BOUNDARY = CN.boundary_payload_tools()
DOMAIN_TOOLS = sorted(set(_GRAPH_AND_ADMIT) | set(_BOUNDARY))


def _run(tool, *args, cwd=None):
    env = dict(os.environ, PYTHONPATH=TOOLS)
    return subprocess.run([sys.executable, os.path.join(TOOLS, tool), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, cwd=cwd or REPO)


def _squash(text):
    """argparse re-wraps every help string to the terminal width, so a sentence a test
    looks for is split across lines at a width nobody controls. Grade the words, not the
    wrapping."""
    return " ".join(text.split())


def _padded_map(path, n=5):
    path.write_text(json.dumps({f"{i:05d}.png": f"srv_{i:05d}_aaaa.png"
                                for i in range(n)}), encoding="utf-8")
    return str(path)


# ===========================================================================
# F-5fd16451 (panel HIGH) — a rebuild does not silently replace a prior build,
#                           and two runs are distinguishable in a scrollback.
# ===========================================================================
#
# OPERAND, measured on `3380ae2`: `build_assembly_payload.main` called twice into ONE
# `--out` with DIFFERENT upload maps replaced both artefacts (`S03-assembly.api.json`
# 2c986d17… -> b3e8f53f…, `S03-assembly-payload-record.json` f61a47b7… -> 80ad650f…) and the
# second run's stdout was BYTE-IDENTICAL to the first — nine lines, none naming an existing
# file, none carrying a digest or any other value that differs between two builds.
#
# SIBLINGS enumerated (rule 2), the nine builders plus the two admission writers:
# `os.path.exists` / `os.path.isfile` appears ZERO times in seven of the nine builders and
# the three hits in the other two are INPUT checks. `build_assembly_payload` and
# `build_cascade_payload` write FIXED filenames and are open; `gate_saved_graph` overwrites
# its admission record at `--out` the same way and is open; **`build_r2v_payload` is CLOSED
# ALREADY and that is measured below, not assumed**; the six builders that take a
# `--seeds-registry` write experiment- and seed-named files into a `--out` that Gate CANON
# already refuses when non-empty.
#
# reverted-red: yes — with `gate_output_not_overwritten` reverted, the second run below
# exits 0 and prints the same nine lines as the first.


def test_a_rebuild_over_an_earlier_build_refuses_by_name_with_both_digests(tmp_path):
    """The refusal a person reads AND the evidence a census reads (Stage C rule 1)."""
    up = _padded_map(tmp_path / "uploads.json")
    out = tmp_path / "out"
    first = _run("build_assembly_payload.py", f"--uploads={up}", f"--out={out}")
    assert first.returncode == 0, first.stdout + first.stderr

    second = _run("build_assembly_payload.py", f"--uploads={up}", f"--out={out}")
    assert second.returncode == 2, second.stdout + second.stderr
    line = next(ln for ln in second.stdout.splitlines()
                if ln.startswith("BUILD_ASSEMBLY_HALT "))
    halt = json.loads(line[len("BUILD_ASSEMBLY_HALT "):])
    ev = halt["evidence"]
    assert ev["clause"] == "output_already_exists"
    assert ev["gate"] == "PAYLOAD"
    assert ev["andon"] == "AssemblyGate"
    assert ev["out_dir_pre_existed"] is True
    assert ev["overwrote"] == []
    assert ev["flag"] == "--overwrite"
    assert sorted(ev["already_present"]) == [
        "S03-assembly-payload-record.json", "S03-assembly.api.json"]
    # the digests the finding asks for — of BOTH artefacts, in the evidence and the message
    assert sorted(ev["digests"]) == sorted(ev["already_present"])
    for name, digest in ev["digests"].items():
        assert len(digest) == 64, (name, digest)
        assert digest[:12] in halt["message"], (
            "the message quotes the digest its evidence carries", name)
    # the sentence, in the one spelling both domains agreed on
    assert "already on disk from an earlier run; this run would replace what is there" in \
        halt["message"]
    assert "Pass --overwrite to replace it" in halt["message"]


def test_the_overwrite_flag_replaces_and_the_run_SAYS_so(tmp_path):
    """The other half of rule 4: with the flag, there is no refusal and the run says what
    it replaced — on stdout and in the record on disk."""
    up = _padded_map(tmp_path / "uploads.json")
    out = tmp_path / "out"
    assert _run("build_assembly_payload.py", f"--uploads={up}",
                f"--out={out}").returncode == 0
    again = _run("build_assembly_payload.py", f"--uploads={up}", f"--out={out}",
                 "--overwrite")
    assert again.returncode == 0, again.stdout + again.stderr
    assert "--overwrite: 2 artefact(s) from an earlier build were replaced" in again.stdout

    record = json.loads((out / "S03-assembly-payload-record.json").read_text(
        encoding="utf-8"))
    assert record["out_dir_pre_existed"] is True
    assert sorted(record["overwrote"]) == [
        "S03-assembly-payload-record.json", "S03-assembly.api.json"]
    receipt = record["gates"]["PAYLOAD_overwrite"]
    assert "clause" not in receipt, "a receipt that PASSED must carry no clause"
    assert "was sha256" in receipt["verdict"]
    # the digests of what was replaced are in the record, so the earlier build is nameable
    assert sorted(receipt["digests"]) == sorted(record["overwrote"])


def test_a_first_build_records_a_measured_absence_not_a_silence(tmp_path):
    """A fresh `--out` gets a receipt too: "nothing was there" is a measured fact."""
    up = _padded_map(tmp_path / "uploads.json")
    out = tmp_path / "out"
    proc = _run("build_assembly_payload.py", f"--uploads={up}", f"--out={out}")
    assert proc.returncode == 0
    record = json.loads((out / "S03-assembly-payload-record.json").read_text(
        encoding="utf-8"))
    assert record["out_dir_pre_existed"] is False
    assert record["overwrote"] == []
    assert "none of them already present" in \
        record["gates"]["PAYLOAD_overwrite"]["verdict"]


def test_two_runs_are_distinguishable_in_a_scrollback(tmp_path):
    """The finding's own complaint: the second run's stdout was BYTE-IDENTICAL to the
    first, so a log of two builds could not tell them apart. The graph's own
    `payload_sha256` — the value `gate_saved_graph.route_facts` compares — is on the
    success line now, and it differs when the inputs differ."""
    a = _padded_map(tmp_path / "a.json", 5)
    # the same frame COUNT (the flat chain is bounded at 8 slots and Gate L wants 4n+1) with
    # a different upload map — the very case the finding measured: a re-run with a corrected
    # map, printing byte-identical output.
    b = tmp_path / "b.json"
    b.write_text(json.dumps({f"{i:05d}.png": f"srv_{i:05d}_bbbb.png"
                             for i in range(5)}), encoding="utf-8")
    b = str(b)
    one = _run("build_assembly_payload.py", f"--uploads={a}", f"--out={tmp_path / 'o1'}")
    two = _run("build_assembly_payload.py", f"--uploads={b}", f"--out={tmp_path / 'o2'}")
    assert one.returncode == 0 and two.returncode == 0
    digests = []
    for proc in (one, two):
        line = next(ln for ln in proc.stdout.splitlines()
                    if ln.startswith("payload sha256"))
        digests.append(line.split()[-1])
    assert len(digests[0]) == 64 and digests[0] != digests[1], digests
    # and each printed digest IS the record's tie, not a second derivation
    for proc, out, digest in ((one, "o1", digests[0]), (two, "o2", digests[1])):
        record = json.loads(
            (tmp_path / out / "S03-assembly-payload-record.json").read_text(
                encoding="utf-8"))
        assert record["payload_sha256"] == digest


def test_the_cascade_builder_carries_the_same_shape(tmp_path):
    """Rule 2: the sibling on the same fixed filenames, refusing in the same words."""
    up = _padded_map(tmp_path / "uploads.json", 81)
    out = tmp_path / "out"
    assert _run("build_cascade_payload.py", f"--uploads={up}",
                f"--out={out}").returncode == 0
    second = _run("build_cascade_payload.py", f"--uploads={up}", f"--out={out}")
    assert second.returncode == 2
    halt = json.loads(next(ln for ln in second.stdout.splitlines()
                           if ln.startswith("BUILD_CASCADE_HALT "))
                      [len("BUILD_CASCADE_HALT "):])
    assert halt["evidence"]["clause"] == "output_already_exists"
    assert sorted(halt["evidence"]["already_present"]) == [
        "E13-cascade-payload-record.json", "E13-cascade.api.json"]


def test_the_admission_writer_carries_the_same_shape(tmp_path):
    """`gate_saved_graph` writes ONE file at `--out` and overwrote it the same way. An
    admission record is the receipt that a specific saved file was proven to be the graph
    this repo built BEFORE credits were spent; replacing one silently leaves the earlier
    spend with no receipt at all."""
    from test_amend_w25_builders import _assembly_cli

    argv = _assembly_cli(tmp_path)
    out = tmp_path / "out" / "admission.json"
    assert GSG.main(argv) == 0
    with pytest.raises(GSG.SavedAdmission) as exc:
        GSG.main(argv)
    ev = exc.value.evidence
    assert ev["clause"] == "output_already_exists"
    assert ev["gate"] == "OUT"
    assert ev["already_present"] == [os.path.basename(str(out))]
    assert GSG.main(argv + ["--overwrite"]) == 0
    record = json.loads(open(out, encoding="utf-8").read())
    assert record["out_dir_pre_existed"] is True
    assert record["overwrote"] == [os.path.basename(str(out))]


def test_the_spend_builder_is_measured_as_ALREADY_CLOSED_not_assumed(tmp_path):
    """The one member of the family that needed no flag, and why — measured, not assumed.

    `build_r2v_payload` reaches `armature_core.canon._gate_out_dir` through
    `canon_spend(..., out_dir=out)`, whose `out_dir_not_empty` clause refuses a non-empty
    `--out` outright, one gate ABOVE where an `--overwrite` check would sit. Adding the flag
    there would have been a flag that cannot fire, and wiring a bypass around another
    domain's gate is not this fix. So the tool carries the printed-digest half of
    F-5fd16451 and no flag, and this is the measurement that says so.
    """
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps(
        {"views": [{"upload_name": f"srv_view{i}.png"} for i in range(4)]}),
        encoding="utf-8")
    seeds = os.path.join(SPECS, "E13-seeds.json")
    seed = json.loads(open(seeds, encoding="utf-8").read())["seeds"][0]
    out = tmp_path / "out"
    argv = ["--arm=A1", f"--seed={seed}", f"--seeds={seeds}",
            f"--prompt-file={os.path.join(SPECS, 'E13-prompt.json')}",
            f"--out={out}", f"--refs={refs}", "--subject", "PERFORMER", "--no-canon"]
    assert BR2V.main(argv) == 0
    with pytest.raises(Exception) as exc:
        BR2V.main(argv)
    assert exc.value.evidence["clause"] == "out_dir_not_empty", exc.value.evidence
    assert exc.value.evidence["gate"] == "CANON"
    # and the flag really is absent, so nobody reads this tool as unprotected
    flags = {node.args[0].value
             for node in ast.walk(ast.parse(
                 open(os.path.join(TOOLS, "build_r2v_payload.py"),
                      encoding="utf-8").read()))
             if isinstance(node, ast.Call)
             and getattr(node.func, "attr", "") == "add_argument"
             and node.args and isinstance(node.args[0], ast.Constant)}
    assert "--overwrite" not in flags, (
        "an --overwrite here cannot fire: Gate CANON refuses a non-empty --out above it")


def test_the_overwrite_check_has_ONE_home_and_three_callers():
    """"Adopt the home", wave 24's rule. The helper is defined once in this domain's shared
    module and imported; a second spelling anywhere is what this asserts against."""
    assert BCP.gate_output_not_overwritten is BAP.gate_output_not_overwritten
    assert GSG.gate_output_not_overwritten is BAP.gate_output_not_overwritten
    defined = []
    for name in DOMAIN_TOOLS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "gate_output_not_overwritten"):
                defined.append(name)
    assert defined == ["build_assembly_payload.py"], defined


def test_the_overwrite_refusal_leaves_no_output_directory(tmp_path):
    """The neighbouring invariant this fix must not break: a refuse leaves no output
    directory. The gate sits ABOVE `os.makedirs`, like every other refusal in these tools."""
    up = _padded_map(tmp_path / "uploads.json")
    out = tmp_path / "out"
    assert _run("build_assembly_payload.py", f"--uploads={up}",
                f"--out={out}").returncode == 0
    stamp = (out / "S03-assembly.api.json").stat().st_mtime_ns
    assert _run("build_assembly_payload.py", f"--uploads={up}",
                f"--out={out}").returncode == 2
    assert (out / "S03-assembly.api.json").stat().st_mtime_ns == stamp, (
        "the refused run rewrote the artefact it refused to replace")


# ===========================================================================
# F-2dcaf53a (panel HIGH) — the one route in this repo that bills per submission
#                           says what riding it costs its user.
# ===========================================================================
#
# OPERAND, measured end to end on `3380ae2` (`build_r2v_payload.main` on the committed
# `specs/E13-seeds.json` + `specs/E13-prompt.json`, arm A1, seed 2026081351): the whole of
# stdout was nine lines — the canon line, `arm`, `nodes`, `seed gate`, `ceiling gate`,
# `route`, `gate L (hosted)`, `slots`, `BUILD_R2V_OK` — and not one named a data-use
# posture, an AI-content disclosure duty or a watermark policy; the payload record carried
# `tier`, `payload`, `slot_order`, `gate_pair_note`, `gate_l_note`, `payload_sha256` and no
# disclosure key. The E14 sibling had been given exactly that surface a wave earlier
# (F-92f67091) for a SMALLER obligation — one credits line on one LoRA.
#
# reverted-red: yes — with `disclosure` / the print loop reverted, stdout is nine lines
# again and `record["disclosure"]` raises KeyError.


def _r2v(tmp_path, *extra):
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps(
        {"views": [{"upload_name": f"srv_view{i}.png"} for i in range(4)]}),
        encoding="utf-8")
    seeds = os.path.join(SPECS, "E13-seeds.json")
    seed = json.loads(open(seeds, encoding="utf-8").read())["seeds"][0]
    out = tmp_path / "out"
    return ["--arm=A1", f"--seed={seed}", f"--seeds={seeds}",
            f"--prompt-file={os.path.join(SPECS, 'E13-prompt.json')}",
            f"--out={out}", f"--refs={refs}", "--subject", "PERFORMER", "--no-canon",
            *extra], out


def test_the_paid_route_prints_its_disclosure_above_its_success_line(tmp_path, capsys):
    """Read BACK off stdout, not off the record: the obligation is said at the moment the
    spend is authored, which is what CLAUDE.md's per-route disclosure ruling asks."""
    argv, _out = _r2v(tmp_path)
    assert BR2V.main(argv) == 0
    printed = capsys.readouterr().out
    lines = printed.splitlines()
    ok = next(i for i, ln in enumerate(lines) if ln.startswith("BUILD_R2V_OK"))
    above = "\n".join(lines[:ok])
    above_flat = re.sub(r"\s+", " ", above)

    assert "TRAINING USE:" in above
    assert "AI CONTENT DISCLOSURE:" in above
    assert "WATERMARK:" in above
    # the three obligations in the licence map's OWN words, not this builder's.
    # Wave 32 wraps disclosure at 78 cols with a hanging indent (F-fd2be19e);
    # collapse whitespace so a wrap inside a phrase still counts as above the OK line.
    assert "machine-learning and artificial-intelligence technologies" in above_flat
    assert "clearly and conspicuously disclose" in above_flat
    assert "watermark=False` was sent" in above_flat
    # and each names the document it is grounded in
    assert above.count("Wan ToS") >= 3


def test_the_record_carries_the_disclosure_block(tmp_path):
    """It rides the provenance too, so a reader who never saw stdout still meets it."""
    argv, out = _r2v(tmp_path)
    assert BR2V.main(argv) == 0
    record = json.loads(
        (out / "E13-A1-seed2026081351-payload-record.json").read_text(encoding="utf-8"))
    d = record["disclosure"]
    assert d["tier"] == BR2V.TIER
    assert [o["kind"] for o in d["obligations"]] == [
        "training_use", "ai_content_disclosure", "watermark"]
    assert d["provider_terms"]["url"].startswith("https://wan.video/")
    assert d["provider_terms"]["fetched"].startswith("2026-08-12")
    assert d["route_verdict"] == record["gates"]["ROUTE"]["verdict"]
    assert d["watermark_requested"] is False
    # the residual is stated rather than papered over
    assert "NOT established" in d["residual"]
    # and the block says plainly that nothing in code checks these
    assert "nothing in code" in d["checked_by"]


def test_the_watermark_line_is_read_off_the_payload_not_off_a_literal(tmp_path):
    """A licence row is not a wiring claim (CLAUDE.md). The disclosure's watermark half
    must describe the value the GRAPH carries, so it cannot drift from the request."""
    argv, out = _r2v(tmp_path)
    assert BR2V.main(argv) == 0
    record = json.loads(
        (out / "E13-A1-seed2026081351-payload-record.json").read_text(encoding="utf-8"))
    assert record["payload"]["watermark"] is False
    assert record["disclosure"]["watermark_requested"] == record["payload"]["watermark"]
    block = BR2V.disclosure("A1", {"verdict": "v"}, True)
    assert block["watermark_requested"] is True
    assert "`watermark=True` was sent" in \
        [o["text"] for o in block["obligations"] if o["kind"] == "watermark"][0]


def test_the_disclosure_renderer_has_ONE_home_and_two_callers():
    """"Adopt the home", not a second spelling. It was written in wave 14 for E14's arm;
    E13 imports the same function object rather than being given a copy."""
    assert BR2V.disclosure_lines is BAP.disclosure_lines
    assert BLA.disclosure_lines is BAP.disclosure_lines
    defined = []
    for name in DOMAIN_TOOLS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "disclosure_lines":
                defined.append(name)
    assert defined == ["build_assembly_payload.py"], defined


def test_the_E14_arms_own_lines_are_unchanged_by_the_lift():
    """The sibling's output must not move because its renderer moved house."""
    block = {"route_verdict": "V",
             "credit_obligation": {"text": "none ruled"},
             "obligations": [{"kind": "credit", "creditor": "renderartist",
                              "text": "credit the creator", "component": "technically_color",
                              "applies_to": "published footage from this arm",
                              "source": "docs/license-map.md"}]}
    lines = BAP.disclosure_lines(block)
    assert lines[0] == "  ROUTE: V"
    joined = " ".join(ln.strip() for ln in lines[1:])
    assert "CREDIT OBLIGATION: this arm credits renderartist - credit the creator" in joined
    assert "published footage from this arm" in joined
    assert "docs/license-map.md" in joined
    assert "technically_color]" in joined
    assert all(len(ln) <= 78 for ln in lines), lines
    empty = BAP.disclosure_lines({"route_verdict": "V",
                                  "credit_obligation": {"text": "none ruled"},
                                  "obligations": []})
    empty_joined = " ".join(ln.strip() for ln in empty[1:])
    assert "CREDIT OBLIGATION: none - the licence map rules no CONDITIONAL" in empty_joined
    assert "component in this arm's graph (none ruled)" in empty_joined
    assert all(len(ln) <= 78 for ln in empty), empty


# ===========================================================================
# F-8601de91 (panel MEDIUM) — the two report lines say what was JUDGED.
# ===========================================================================
#
# OPERAND, measured as printed output from a real run on `3380ae2`:
#   route components 0  seeds 0  latents 0
#   frame legality   [True]
# — three zeros with no sentence saying whether zero means an empty set was examined (it
# does) or nothing was found to examine (the vacuous state `verify` exists to refuse), and a
# bare list of booleans with no width, height or frame count beside it. The same information
# is rendered well one file over on the paid route: `gate L (hosted)  720P 16:9 5s -> legal
# True`. SIBLINGS: both call sites, `build_assembly_payload` and `build_cascade_payload`.
#
# reverted-red: yes — reverted, the assertions below fail on the bare `[True]` repr.


@pytest.mark.parametrize("tool,frames,prefix", [
    ("build_assembly_payload.py", 5, "BUILD_ASSEMBLY"),
    ("build_cascade_payload.py", 81, "BUILD_CASCADE"),
])
def test_the_route_report_names_the_values_it_judged(tmp_path, tool, frames, prefix):
    up = _padded_map(tmp_path / "uploads.json", frames)
    proc = _run(tool, f"--uploads={up}", f"--out={tmp_path / 'out'}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    legality = next(ln for ln in proc.stdout.splitlines()
                    if ln.startswith("frame legality"))
    assert "[True]" not in legality, "the repr is back"
    assert f"x{frames} " in legality, legality
    assert "-> legal" in legality
    assert "wan 4n+1" in legality, "the rule that judged it is named"

    components = next(ln for ln in proc.stdout.splitlines()
                      if ln.startswith("route ") and "components" in ln)
    assert components.startswith("route            components"), components
    assert "EMPTY SET examined, not a check skipped" in components, components
    assert "loads no weights" in components


def test_the_report_lines_have_ONE_home_and_report_an_illegal_frame_as_such():
    """Grade the arm only on what it can move: with an ILLEGAL row the line must say so and
    carry the problems, or the "legal" half is a constant."""
    assert BCP.route_report_lines is BAP.route_report_lines
    lines = BAP.route_report_lines({
        "components": [], "seeds": [], "latents": [],
        "frame_legality": [dict(RG.frame_legality(832, 480, 80), source="supplied")]})
    assert lines[1].endswith("ILLEGAL: length 80 is not of the form 4n+1 (nearest: 81)"), \
        lines
    assert "832x480x80" in lines[1]


def test_the_report_says_when_no_frame_was_checkable():
    """The third state, which the boolean list could not express at all."""
    lines = BAP.route_report_lines({"components": [1], "seeds": [], "latents": [],
                                    "frame_legality": []})
    assert lines[1] == "frame legality   no frame was checkable on this graph"
    assert "EMPTY SET examined" not in lines[0], (
        "a non-empty component list must not be described as an empty set")


# ===========================================================================
# F-a4aac9c2 (panel HIGH) — the operation that runs AFTER the credits are spent
#                           is bounded and says it is alive.
# ===========================================================================
#
# OPERAND, measured on `3380ae2`: `fetch_run.py` had exactly ONE `print` call (:1048, the
# terminal receipt) and `fetch_t2v_run.py` exactly one (:393); the download was
# `subprocess.run([...], capture_output=True, text=True, env=env)` with NO `timeout=`,
# running `curl.exe -sS` (which suppresses curl's own meter) inside `ForEach-Object
# -Parallel -ThrottleLimit 12`; and `grep -n "max-time\|connect-timeout\|timeout"` over both
# fetchers returned ZERO hits. SIBLINGS: `fetch_t2v_run.download` calls this same
# implementation, so both fetchers move together and there is no second shape.
#
# The shape is the wave's ONE spelling (instruments-measure @ 13:41; the coordinator's SEAM 8 named it
# final after its own SEAM 6 crossed builders' adoption — aligned here in the merge fix-up): stderr,
# `fetch_run download <done>/<total>  elapsed <e>s  bound <b>s` before and after the wait, clause
# `downloader_exceeded_the_time_bound`, evidence `{clause, bound_s, elapsed_s, planned, partial,
# binary, input}`, and NEVER a retry.
#
# reverted-red: yes — reverted, `subprocess.run` takes no `timeout` keyword (asserted
# below by driving a fake that records its kwargs), nothing is printed to stderr, and a hung
# downloader has no bound at all.


def test_the_downloader_command_carries_curls_own_bounds():
    for command in (F.DOWNLOAD_PS, F.DOWNLOAD_PS_NO_URLS):
        assert f"--connect-timeout {F.CURL_CONNECT_TIMEOUT_S}" in command
        assert f"--max-time {F.CURL_MAX_TIME_S}" in command
        assert f"-ThrottleLimit {F.DOWNLOAD_THROTTLE}" in command
        # the wave-12 quoting fix survives: nothing operator-derived is in the command
        assert "$env:ARMATURE_FETCH_MANIFEST" in command
        assert "-- $_.url" in command


def test_the_process_bound_is_derived_from_the_work_not_a_global_constant():
    """CLAUDE.md: a global constant must not govern a local feature. One wave of the
    throttle costs one per-request bound; the start-up is not any request's."""
    one_wave = F.DOWNLOAD_STARTUP_S + F.CURL_MAX_TIME_S
    assert F.timeout_for_jobs(1) == one_wave
    assert F.timeout_for_jobs(F.DOWNLOAD_THROTTLE) == one_wave
    assert F.timeout_for_jobs(F.DOWNLOAD_THROTTLE + 1) == one_wave + F.CURL_MAX_TIME_S
    assert F.timeout_for_jobs(0) == one_wave, "an empty plan still bounds the process"


def test_the_bound_that_is_printed_is_the_bound_that_is_ENFORCED(tmp_path, monkeypatch,
                                                                 capfd):
    """The two cannot drift: the number in the sentence IS the argument."""
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(kw)
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
            rows.append({"out": job["out"], "url": job["url"], "code": 0, "message": ""})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    from test_fetch_run import _dump, _result

    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    assert F.main(["--dump", dump, "--run", "r",
                   "--root", str(tmp_path / "runs")]) == 0
    err = capfd.readouterr().err
    assert seen.get("timeout") == F.timeout_for_jobs(3), seen.get("timeout")
    assert f"bound {F.timeout_for_jobs(3)}s" in err, err
    assert "fetch_run download 0/3" in err
    assert "fetch_run download 3/3" in err
    assert "elapsed " in err


def test_the_progress_lines_are_on_stderr_and_are_not_sentinels(tmp_path, monkeypatch,
                                                                capfd):
    """stdout keeps its ONE success line — the sentinel censuses walk stdout's prints, and a
    progress line that looks like a sentinel takes them red on the commit that adds it."""
    from test_fetch_run import _dump, _result

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
            rows.append({"out": job["out"], "url": job["url"], "code": 0, "message": ""})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    assert F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")]) == 0
    cap = capfd.readouterr()
    assert len([ln for ln in cap.out.splitlines() if ln.strip()]) == 1, cap.out
    assert cap.out.startswith("FETCH_RUN_OK ")
    for line in cap.err.splitlines():
        first = line.split()[0] if line.split() else ""
        assert not first.isupper() or not first.isidentifier(), (
            f"{first!r} reads as a sentinel token", line)


def test_a_downloader_that_exceeds_the_bound_is_a_NAMED_refusal_with_the_partial_state(
        tmp_path, monkeypatch):
    """A bound that is reached is a refusal, never a retry: this step runs after the
    generation has been billed."""
    from test_fetch_run import _dump, _result

    calls = []

    def fake_run(cmd, **kw):
        calls.append(kw.get("timeout"))
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        # one job landed before the hang; the rest did not
        os.makedirs(os.path.dirname(jobs[0]["out"]), exist_ok=True)
        with open(jobs[0]["out"], "wb") as out:
            out.write(F.PNG_SIGNATURE)
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    ev = exc.value.evidence
    assert ev["clause"] == "downloader_exceeded_the_time_bound"
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt"
    assert ev["bound_s"] == F.timeout_for_jobs(3) == calls[0]
    assert isinstance(ev["elapsed_s"], float)
    assert ev["planned"] == 3
    assert ev["binary"] == F.DOWNLOADER
    assert ev["input"].endswith("urls.json")
    assert [row["present"] for row in ev["partial"]] == [True, False, False]
    assert ev["partial"][0]["bytes"] > 0
    # never a retry
    assert len(calls) == 1, "the fetcher retried after a timeout"
    assert "No download was retried" in str(exc.value)
    # and it is a REFUSAL, not a crash: the stdlib exception never reaches the operator
    assert isinstance(exc.value, F.FetchHalt)


def test_the_timeout_refusal_carries_the_same_base_keys_as_its_siblings():
    """Its five siblings' receipt fields, so a reader of any download halt sees one shape.
    `process_returncode` is None and that is the honest value: the child was killed, so it
    never exited."""
    tree = ast.parse(open(os.path.join(TOOLS, "fetch_run.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        keys = {}
        if isinstance(node.exc.args[1] if len(node.exc.args) > 1 else None, ast.Dict):
            d = node.exc.args[1]
            keys = {k.value: v for k, v in zip(d.keys, d.values)
                    if isinstance(k, ast.Constant)}
        if keys.get("clause") is not None and getattr(
                keys.get("clause"), "value", None) == "downloader_exceeded_the_time_bound":
            assert {"gate", "andon", "clause", "process_returncode", "returncode",
                    "exits_record", "planned", "bound_s", "elapsed_s", "binary",
                    "input", "partial"} <= set(keys), sorted(keys)
            break
    else:
        raise AssertionError("no `downloader_exceeded_the_time_bound` raise found in fetch_run")


def test_the_sibling_fetcher_moves_with_it():
    """One implementation, two fetchers: `fetch_t2v_run.download` calls THIS function, so
    the bound and the progress lines are not a second shape there."""
    import fetch_t2v_run as T

    assert T.fetch_download is F.download


# ===========================================================================
# F-073cdeed (panel MEDIUM) — the download refusals say what the operator holds
#                             and what the supported next step is.
# ===========================================================================
#
# OPERAND: `downloader_job_exit_nonzero` (:649-658) and `downloader_job_exit_unrecorded`
# (:660-671) each named the failed jobs, their curl codes and the `-Parallel`
# exit-propagation reason at length — and neither said what the operator NOW HOLDS. MEASURED
# across both fetchers' parsers on `3380ae2`: `fetch_run` accepts
# `--dump --run --root --node-map --video-nodes` and `fetch_t2v_run` accepts
# `--dump --out --prompt-id`; there is no `--resume`, no `--clean` and no `--force` in
# either. And the state a plain re-run lands in is the one this module records as
# un-backstopped in its own comment eleven lines above the refusal.
#
# reverted-red: yes — reverted, neither message mentions the run directory, `urls.json` or
# a next step, and neither evidence dict carries `partial`.


@pytest.mark.parametrize("clause,fixture", [
    ("downloader_job_exit_nonzero", "nonzero"),
    ("downloader_job_exit_unrecorded", "unrecorded"),
])
def test_both_download_refusals_name_the_state_and_the_next_step(tmp_path, monkeypatch,
                                                                 clause, fixture):
    from test_fetch_run import _dump, _result

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for i, job in enumerate(jobs):
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            if i == 0:                      # one landed; the rest did not
                with open(job["out"], "wb") as out:
                    out.write(F.PNG_SIGNATURE)
            rows.append({"out": job["out"], "url": job["url"],
                         "code": 22 if fixture == "nonzero" else None,
                         "message": "boom"})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    message = str(exc.value)
    ev = exc.value.evidence
    assert ev["clause"] == clause
    # name the directory, say it holds partial work, say it is NOT a result, say what next
    assert "holds a PARTIAL fetch" in message
    assert "1 of 3 planned file(s) are present" in message
    assert "it is not a result" in message
    assert "`urls.json` beside them still names every planned job" in message
    assert "CLEAR the run directory and re-fetch" in message
    assert "mixture of two fetches" in message
    # and the evidence carries what the sentence claims (Stage C rule 1)
    assert [row["present"] for row in ev["partial"]] == [True, False, False]


def test_the_partial_sentence_has_ONE_wording_across_the_three_halts():
    """The coordinator's SEAM 6 §5: one wording across every halt on the retrieval path."""
    src = open(os.path.join(TOOLS, "fetch_run.py"), encoding="utf-8").read()
    assert src.count("_partial_sentence(dest, planned)") == 3, (
        "the two download refusals and the timeout all carry the same sentence")
    assert src.count("def _partial_sentence(") == 1


# ===========================================================================
# F-5f51c793 (panel MEDIUM) — `--root`'s E02 default is documented, and a
#                             non-E02 tap map may not silently file under E02.
# ===========================================================================
#
# OPERAND: `ap.add_argument("--root", default="outputs/E02/runs")` carried no `help=`, while
# the neighbouring E02 default IS documented — `--node-map`'s help spells out "Defaults to
# E02's taps (301=batchprobe,302=lossless)" and `parse_node_map` refuses rather than falling
# back. MEASURED on `3380ae2` by calling `fetch_run.plan` with the default root and a
# non-E02 node map: an E13 run fetched with `--node-map` supplied and `--root` forgotten
# plans its frames to `outputs/E02/runs\\E13-A1-seed2026081351\\lossless\\00000.png`.
#
# reverted-red: yes — reverted, `--root` renders as a bare `--root ROOT` in `--help` and the
# pair below builds an E02-rooted plan at exit 0.


def test_the_root_flags_help_names_its_default_and_says_it_is_E02s():
    rendered = _run("fetch_run.py", "--help")
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    assert "--root ROOT\n" not in rendered.stdout, "the flag renders with no text"
    assert F.DEFAULT_ROOT in rendered.stdout
    assert "E02" in rendered.stdout


def test_a_non_E02_tap_map_without_a_root_refuses_by_name(tmp_path, monkeypatch):
    """An operator naming another experiment's taps is by construction not fetching E02, so
    the pair is the condition — refused at the boundary, the way `--run` is.

    `monkeypatch.chdir` is load-bearing and was earned: the default root is RELATIVE, so with
    this check disarmed the run below writes `outputs/E02/runs/E13-A1-seed2026081351/` into
    the process CWD — which, when the reverted-red proof drove it from the repo root, left a
    bogus E02 run tree in the worktree and un-skipped three `test_measure_tracking.py` tests
    that key on that path. The defect this test is about, reproduced by the test itself. A red
    proof may not litter the tree it is grading.
    """
    from test_fetch_run import _dump, _result

    monkeypatch.chdir(tmp_path)
    dump = _dump(tmp_path, [_result("71", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main(["--dump", dump, "--run", "E13-A1-seed2026081351",
                "--node-map=71=lossless"])
    ev = exc.value.evidence
    assert ev["clause"] == "node_map_without_a_root"
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt"
    assert ev["default_root"] == F.DEFAULT_ROOT
    assert ev["run"] == "E13-A1-seed2026081351"
    # the message quotes what the evidence carries, and says what to pass
    assert F.DEFAULT_ROOT in str(exc.value)
    assert "pass --root explicitly" in str(exc.value)
    assert ev["would_have_written"].endswith(
        os.path.join("outputs", "E02", "runs", "E13-A1-seed2026081351"))


def test_the_default_root_still_applies_when_no_tap_map_is_named(tmp_path, monkeypatch):
    """The direction the refusal must NOT bound: E02's own callers pass neither flag and
    their behaviour is unchanged."""
    from test_fetch_run import _dump, _result

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
            rows.append({"out": job["out"], "url": job["url"], "code": 0, "message": ""})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    monkeypatch.chdir(tmp_path)
    dump = _dump(tmp_path, [_result("302", 0)])
    assert F.main(["--dump", dump, "--run", "r", "--video-nodes=none"]) == 0
    assert (tmp_path / F.DEFAULT_ROOT / "r" / "lossless" / "00000.png").is_file()


# ===========================================================================
# F-c63c6ba4 (panel MEDIUM) — `--help` can say what every tool in this domain IS.
# ===========================================================================
#
# OPERAND, walked by AST over all 13 files on `3380ae2`: **0 of 13 parsers passed
# `description=`, 0 of 13 passed `epilog=`, and 59 of 99 `add_argument` calls carried no
# `help=`.** RENDERED, not inferred: `gate_saved_graph.py --help` — the last gate before a
# paid submission — printed a usage block whose four REQUIRED flags rendered as bare
# `--saved SAVED`, `--api API`, `--seeds SEEDS`, `--out OUT`, with no sentence anywhere
# saying the tool exists to prove the saved file is the graph this repo built before credits
# are spent; `canon_gate.py --help` printed `{resolve,coverage,check,spend}` as a bare
# positional. The tree's own precedent is one line long: `tools/compare_runs.py`'s parser.
#
# EXCLUDED from the 59, as core-gates': the three flags `canon.add_spend_flags` writes.
# OUT OF DOMAIN: the prose half — `build_r2v_payload` is named in ZERO of the repo's 159
# `.md` files — is the coordinator's; `docs/tools.md` on the base is generated from every
# docstring and is the anchor.
#
# reverted-red: yes — reverted, the census below reads 0 / 13 / 13 / 59 again.


def _parser_census():
    """`{file: {"description": bool, "epilog": bool, "bare": [flags]}}`, by AST."""
    out = {}
    for name in DOMAIN_TOOLS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        row = {"description": False, "epilog": False, "bare": [], "n_args": 0}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fname = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if fname == "ArgumentParser":
                kw = {k.arg for k in node.keywords}
                row["description"] |= "description" in kw
                row["epilog"] |= "epilog" in kw
            elif fname == "add_argument":
                row["n_args"] += 1
                if "help" not in {k.arg for k in node.keywords}:
                    flag = (node.args[0].value
                            if node.args and isinstance(node.args[0], ast.Constant)
                            else "<positional>")
                    row["bare"].append(flag)
        out[name] = row
    return out


def test_the_domain_population_is_the_thirteen_tools():
    """Size and membership before the property, so a new tool joins the census on the day
    it lands rather than being guarded by a list somebody forgot.

    Thirteen graph/admit/fetch tools plus the wave-34 boundary class (submitter + uploads
    map) that match `build_*payload*.py` without authoring a graph.
    """
    assert _GRAPH_AND_ADMIT == [
        "build_animate_payload.py", "build_assembly_payload.py",
        "build_camera_i2v_payload.py", "build_cascade_payload.py",
        "build_i2v_payload.py", "build_lora_arm_payload.py", "build_payload.py",
        "build_r2v_payload.py", "build_t2v_payload.py", "canon_gate.py",
        "fetch_run.py", "fetch_t2v_run.py", "gate_saved_graph.py"], _GRAPH_AND_ADMIT
    assert len(_GRAPH_AND_ADMIT) == 13
    assert _BOUNDARY == ["build_submit_payload.py", "build_uploads_payload.py"]
    assert len(DOMAIN_TOOLS) == 15, DOMAIN_TOOLS


def test_every_parser_in_this_domain_says_what_its_tool_IS():
    census = _parser_census()
    missing = sorted(n for n, r in census.items() if not r["description"])
    assert missing == [], missing


def test_every_parser_in_this_domain_names_its_route_and_what_a_refusal_costs():
    census = _parser_census()
    missing = sorted(n for n, r in census.items() if not r["epilog"])
    assert missing == [], missing
    # and the epilogs are not decoration: each names the route and the cost. RENDERED, not
    # read off the source — an epilog is an f-string in three of the thirteen (the enums and
    # the measured bounds are read from the tables that own them), so `literal_eval` is not
    # the reader for it; `--help` is.
    for name in DOMAIN_TOOLS:
        rendered = _squash(_run(name, "--help").stdout)
        assert "ROUTE:" in rendered, name
        assert "COSTS" in rendered, name


def test_no_flag_an_operator_reaches_renders_without_text():
    census = _parser_census()
    bare = {n: r["bare"] for n, r in census.items() if r["bare"]}
    assert bare == {}, bare
    assert sum(r["n_args"] for r in census.values()) >= 99, "the census stopped walking"


def test_the_subcommands_of_the_canon_gate_say_what_they_are():
    """`canon_gate.py --help` printed `{resolve,coverage,check,spend}` as a bare positional,
    so an operator could not learn from the CLI that `spend` is the gate every payload
    builder calls."""
    rendered = _run("canon_gate.py", "--help")
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    out = _squash(rendered.stdout)
    assert "THE GATE every payload builder calls" in out
    for sub in ("resolve", "coverage", "check", "spend"):
        assert sub in out
    spend = _run("canon_gate.py", "spend", "--help")
    assert spend.returncode == 0
    assert "this is what is gated" in _squash(spend.stdout)


def test_the_last_gate_before_a_spend_says_so_in_its_own_help():
    rendered = _run("gate_saved_graph.py", "--help")
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    out = _squash(rendered.stdout)
    assert "the graph this repo built" in out
    assert "last gate before a paid submission" in out
    assert "billed per attempt" in out
    # each of the four REQUIRED flags — bare `--saved SAVED` etc. before this — now says
    # what it is. The usage line still spells the metavars, so grade the OPTIONS section.
    options = _squash(rendered.stdout.split("options:", 1)[-1])
    for flag, phrase in (("--saved", "the file that will actually be run"),
                         ("--api", "this repo built and submitted for conversion"),
                         ("--seeds", "the committed seed registration"),
                         ("--out", "the JSON admission record this gate writes")):
        assert phrase in options, f"{flag} renders with no text"


def test_a_flags_legal_values_are_READ_from_the_table_that_owns_them():
    """"Where a flag's legal values are a constant, read the set into the help string
    rather than typing it" — so a tier added to the table cannot leave the help behind."""
    rendered = _run("build_r2v_payload.py", "--help")
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    out = _squash(rendered.stdout)
    rules = RG.HOSTED_TIER_RULES[BR2V.TIER]
    for value in rules["resolutions"] + rules["ratios"]:
        assert value in out, value
    assert str(rules["duration_s"][1]) in out
    # and it is READ, not typed: the source interpolates the table
    src = open(os.path.join(TOOLS, "build_r2v_payload.py"), encoding="utf-8").read()
    assert "tier_rules['resolutions']" in src
    assert "tier_rules['ratios']" in src


@pytest.mark.parametrize("name", DOMAIN_TOOLS)
def test_every_tool_in_this_domain_can_answer_for_its_own_usage(name):
    """The whole point of a `--help`: it runs, exits 0 and prints a usage block. The
    precedent this follows, `compare_runs.py`, was added because its predecessor died with
    `KeyError: 'a'` when asked."""
    rendered = _run(name, "--help")
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    assert rendered.stdout.lower().startswith("usage:")
    assert len(rendered.stdout) > 400, "a usage block with no prose in it"


# ===========================================================================
# F-7ca576d2 (panel MEDIUM) — the seeds paragraph has one home.
# ===========================================================================
#
# The measurement and the citation census live in `tests/test_seeds_specs.py`, which owns
# this property and rides the change. This is the builders-side pin: the eight specs no
# longer carry the paragraph, and the operator's path to the bound is short.
#
# reverted-red: yes — reverted, each `ceiling` block is 4,984 characters of another
# experiment's citation history before `submissions`.


def test_the_ceiling_block_an_operator_reads_is_short_again():
    """"How many submissions may this arm make" is a two-line answer, and it was behind
    4,984 characters of census provenance in the same object."""
    import glob

    for path in sorted(glob.glob(os.path.join(SPECS, "*seeds.json"))):
        ceiling = json.loads(open(path, encoding="utf-8").read())["ceiling"]
        assert isinstance(ceiling["submissions"], int)
        assert len(ceiling["why_machine_readable"]) < 1000, os.path.basename(path)
        # the values that BIND are still beside it
        assert ceiling["note"].strip()
        assert ceiling["counted_in"].strip()
    home = os.path.join(SPECS, "ceiling-why-machine-readable.md")
    assert os.path.isfile(home), "the correction history left the tree"
    assert len(open(home, encoding="utf-8").read()) > 4984
