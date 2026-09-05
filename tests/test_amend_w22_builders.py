"""Wave 22, builders — Stage B amend #1. Sixteen approved findings, none deferred.

Each block names the finding, the OPERAND the wave-21 auditor measured on `e8263a3`, the
siblings enumerated beside it, and the halt line read back out of the tool's own
`__main__`. Every fix here was run once with the fix reverted; the `reverted-red` note in
each block records what the reverted tree did.

The rule this wave adds, on top of wave 18's five: a census keys on the RESOLVED shape; a
guard is a gate that RAISES a named andon with evidence; observability is a halt line an
operator can key on and a receipt a reader can reconcile.
"""

import ast
import copy
import glob
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import route_gates as RG

import gate_saved_graph as GSG
import fetch_run as FR
import fetch_t2v_run as FT
import canon_gate as CG

from test_amend_w14_builders import ASSEMBLY_API, ASSEMBLY_SAVED, _write, _builder_record
from test_amend_w18_builders import _gsg_halt, _gsg_files, _raises

REPO = os.path.dirname(TOOLS)
SPECS = os.path.join(REPO, "specs")


def _sub(tool, args, sentinel):
    """Drive a tool's own `__main__` in a subprocess and READ its printed halt record."""
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, tool), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith(sentinel + " ")]
    oks = [ln for ln in proc.stdout.splitlines()
           if ln.startswith(sentinel.replace("_HALT", "_OK") + " ")]
    return proc, halts, oks


# ===========================================================================
# F-defa6973 — the save-format member shape, on the last gate before a spend
#
# The wave-18 merge fix-up (475f4eb) classified every top-level API entry before any
# `class_type` was read and left the SECOND bare index in the same loop untouched
# (`node["inputs"]`), and the SAVE side had no member clause at all. Measured on `e8263a3`
# on the assembly fixture that otherwise prints SAVED_ADMISSION_OK at exit 0:
#
#   api node with `inputs` deleted   -> KeyError 'inputs',   evidence null, exit 1
#   saved node with no `id`          -> KeyError 'id',       evidence null, exit 1
#   saved node with no `type`        -> KeyError 'type',     evidence null, exit 1
#   `nodes` holding a string member  -> TypeError,           evidence null, exit 1
#   saved `inputs` spelled as a dict -> AttributeError,      evidence null, exit 1
#
# reverted-red: yes — the table above IS the reverted tree, re-measured in this worktree
# before the fix landed.
# ===========================================================================


def _api_missing_inputs():
    g = copy.deepcopy(ASSEMBLY_API)
    del g["20"]["inputs"]
    return g


def _api_inputs_is_a_list():
    g = copy.deepcopy(ASSEMBLY_API)
    g["20"]["inputs"] = ["images", "fps"]
    return g


def _saved_missing(key):
    s = copy.deepcopy(ASSEMBLY_SAVED)
    del s["nodes"][0 if key == "id" else 3][key]
    return s


def _saved_non_dict_member():
    s = copy.deepcopy(ASSEMBLY_SAVED)
    s["nodes"].append("a string where a node belongs")
    return s


def _saved_inputs_is_a_mapping():
    s = copy.deepcopy(ASSEMBLY_SAVED)
    s["nodes"][2]["inputs"] = {"images.image0": 1, "images.image1": 2}
    return s


#: The five shapes the finding enumerates plus the API container sibling, as
#: `(name, api graph, saved graph)`. Both exported comparisons are driven over ALL of them:
#: `link_round_trip` used to return CLEANLY on a saved node with no `type`, so a red proof
#: run on `round_trip` alone would have reported a closed hole one function over.
W22_UNREADABLE_MEMBERS = [
    ("api node declares no `inputs`", _api_missing_inputs(), ASSEMBLY_SAVED, "inputs"),
    ("api `inputs` is a list", _api_inputs_is_a_list(), ASSEMBLY_SAVED, "inputs"),
    ("saved node declares no `id`", ASSEMBLY_API, _saved_missing("id"), "id"),
    ("saved node declares no `type`", ASSEMBLY_API, _saved_missing("type"), "type"),
    ("saved `nodes` holds a string", ASSEMBLY_API, _saved_non_dict_member(), None),
    ("saved `inputs` is a mapping", ASSEMBLY_API, _saved_inputs_is_a_mapping(), "inputs"),
]


@pytest.mark.parametrize("name,api,saved,container",
                         W22_UNREADABLE_MEMBERS, ids=[r[0] for r in W22_UNREADABLE_MEMBERS])
@pytest.mark.parametrize("fn", [GSG.round_trip, GSG.link_round_trip],
                         ids=["round_trip", "link_round_trip"])
def test_every_unreadable_member_shape_is_refused_by_name(fn, name, api, saved, container):
    """Rule 2: the red proof runs against the SIBLINGS, both functions, one clause word."""
    exc, ev = _raises(fn, api, saved)
    assert isinstance(exc, RG.RouteGate), (name, type(exc).__name__, str(exc)[:200])
    assert ev.get("clause") == "unreadable_node", (name, ev)
    assert ev.get("gate") in ("ROUTE", "SAVED_ADMISSION"), (name, ev)
    if container is not None:
        assert ev.get("container") == container, (name, ev)


def test_the_green_fixture_is_still_green_the_direction_the_clause_must_not_bound():
    """A check that refuses everything is not a check. The unmutated assembly fixture — the
    same one the wave-14 admission test drives to exit 0 — still compares clean."""
    assert GSG.round_trip(ASSEMBLY_API, ASSEMBLY_SAVED)["all_equal"] is True
    assert GSG.link_round_trip(ASSEMBLY_API, ASSEMBLY_SAVED)["n_links"] == 4


def _assembly_cli(tmp_path, api=None, saved=None, out=None, record=True):
    d = tmp_path / "in"
    d.mkdir(parents=True, exist_ok=True)
    api_p = _write(tmp_path, "in/g.api.json", api if api is not None else ASSEMBLY_API)
    saved_p = _write(tmp_path, "in/g.saved.json",
                     saved if saved is not None else ASSEMBLY_SAVED)
    seeds_p = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    argv = [f"--saved={saved_p}", f"--api={api_p}", f"--seeds={seeds_p}",
            f"--out={out if out is not None else tmp_path / 'out' / 'admission.json'}",
            "--frame=832,480,81"]
    if record:
        rec = _write(tmp_path, "in/payload-record.json", _builder_record(
            ASSEMBLY_API, family="wan", carries_no_sampler=True, frame=(832, 480, 81)))
        argv.append(f"--record={rec}")
    return argv


def test_the_halt_line_reads_the_unreadable_node_clause(tmp_path):
    """Rule 4 — the halt line READ, on the operand the auditor measured as `KeyError:
    'inputs'` / exit 1 / `"evidence": null`."""
    argv = _assembly_cli(tmp_path, api=_api_missing_inputs())
    proc = subprocess.run([sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"),
                           *argv], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=REPO)
    line = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("SAVED_ADMISSION_HALT ")]
    assert line, proc.stdout + proc.stderr
    halt = json.loads(line[-1][len("SAVED_ADMISSION_HALT "):])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "SavedAdmission", halt
    assert halt["evidence"]["clause"] == "unreadable_node", halt
    assert halt["evidence"]["container"] == "inputs", halt
    assert not (tmp_path / "out").exists(), "a refusal left an out directory"


# ===========================================================================
# F-9ad5cbc2 — the two facts that admit a paid submission may not be read off
#              the evidence of a Gate ROUTE refusal that FIRED.
#
# The wave-18 clause `record_carries_a_caught_refusal` was keyed on ONE key —
# `refusals = [r for r in receipts if r.get("clause")]` — on the comment "a returned receipt
# never carries `clause`; that is the reading that tells them apart". That proposition is
# true. The converse, which is what the reader actually needs, is false: RE-MEASURED on
# `e8263a3`, 17 `RouteGate` raise sites live inside `route_gates.verify` and 14 of them pass
# evidence carrying no `clause` at all.
#
# Operand (the auditor's): `RG.verify` on a two-node graph — `WanCameraEmbedding` with
# width/height/length wired as LINKS plus a `PrimitiveInt` — raises with `receipt: "verify"`,
# `gate: "ROUTE"`, `andon: "RouteGate"`, both VERIFY_RECEIPT_KEYS and NO `clause`. Written
# into a record as `{"gates": {"ROUTE": <that evidence>}}` it was ADMITTED: n_verify_receipts
# 1, found_by "declared receipt kind", carries_no_sampler False, attribution [].
# reverted-red: yes — that admission IS the reverted tree, re-measured in this worktree.
# ===========================================================================


CAMERA_LINKED_FRAME = {
    "45": {"class_type": "WanCameraEmbedding",
           "inputs": {"camera_pose": "Static", "width": ["99", 0], "height": ["99", 0],
                      "length": ["99", 0], "speed": 1.0, "fx": 0.5, "fy": 0.5,
                      "cx": 0.5, "cy": 0.5}},
    "99": {"class_type": "PrimitiveInt", "inputs": {"value": 832}},
}

TECHNICALLY_COLOR = "wan22-14b-t2v-technically_color.safetensors"


def _caught_refusal(graph, **kwargs):
    """The EVIDENCE of a real `verify` refusal — never a hand-typed dict."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(graph, **kwargs)
    ev = exc.value.evidence
    assert isinstance(ev, dict) and ev.get("receipt") == GSG.VERIFY_RECEIPT_KIND, ev
    assert all(k in ev for k in GSG.VERIFY_RECEIPT_KEYS), sorted(ev)
    return ev


#: Rule 2's sibling enumeration, DRIVEN rather than typed: six distinct refusals of
#: `verify`, FOUR of them carrying no `clause`. Each is a record a wrapper could write.
W22_CAUGHT_REFUSALS = {
    "camera agreement INDETERMINATE": (CAMERA_LINKED_FRAME, {}),
    "banned component": (
        {"1": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "causvid_x.safetensors"}}}, {}),
    "no latent and no frame": (
        {"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "hi"}}}, {}),
    "uncredited conditional": (
        {"75": {"class_type": "UNETLoader",
                "inputs": {"unet_name": TECHNICALLY_COLOR, "weight_dtype": "default"}}},
        {"frame": (832, 480, 81)}),
    "illegal frame": (
        {"5": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": 833, "height": 480, "length": 81, "batch_size": 1}}},
        {"carries_no_sampler": True}),
    "orphan attribution": (
        {"5": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}}},
        {"carries_no_sampler": True,
         "attribution": [RG.attribution_entry_for("technically_color")]}),
}


@pytest.mark.parametrize("name", sorted(W22_CAUGHT_REFUSALS))
def test_a_caught_verify_refusal_is_never_read_as_a_source_of_the_two_facts(name, tmp_path):
    graph, kwargs = W22_CAUGHT_REFUSALS[name]
    ev = _caught_refusal(graph, **kwargs)
    record = _write(tmp_path, "rec/%s.json" % re.sub(r"\W+", "_", name),
                    {"gates": {"ROUTE": ev}})
    exc, refusal = _raises(GSG.route_facts, str(record))
    assert isinstance(exc, RG.RouteGate), (name, repr(exc))
    assert refusal.get("clause") == "record_carries_a_caught_refusal", (name, refusal)


def test_four_of_the_six_caught_refusals_carry_no_clause_at_all():
    """The measurement that makes the wave-18 reading wrong, kept runnable rather than
    remembered. If a future `verify` stamps a clause on every raise this list empties and
    the reading below becomes merely redundant — a different fact, and this says which."""
    clauseless = sorted(
        name for name, (g, kw) in W22_CAUGHT_REFUSALS.items()
        if not _caught_refusal(g, **kw).get("clause"))
    assert clauseless == ["banned component", "camera agreement INDETERMINATE",
                          "illegal frame", "no latent and no frame"], clauseless


def _verify_fn_node():
    src = open(os.path.join(TOOLS, "armature_core", "route_gates.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "verify"]
    assert len(fns) == 1, [f.lineno for f in fns]
    return fns[0]


def _route_gate_raises_in_verify():
    out = []
    for n in ast.walk(_verify_fn_node()):
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
            name = getattr(n.exc.func, "id", None) or getattr(n.exc.func, "attr", None)
            if name == "RouteGate":
                ev = n.exc.args[1] if len(n.exc.args) > 1 else None
                has_clause = False
                if isinstance(ev, ast.Dict):
                    has_clause = any(isinstance(k, ast.Constant) and k.value == "clause"
                                     for k in ev.keys)
                elif isinstance(ev, ast.Call):
                    has_clause = any(kw.arg == "clause" for kw in ev.keywords)
                out.append((n.lineno, has_clause))
    return out


def test_the_population_is_derived_not_pinned_and_the_clause_less_majority_is_real():
    """The AST census the finding asks for, keyed on the RESOLVED shape (a raise of the
    class, wherever it sits inside `verify`) rather than on a list of line numbers. A new
    raise joins the population without a new pin; what is asserted is the PROPERTY."""
    sites = _route_gate_raises_in_verify()
    assert len(sites) >= 17, sites
    clause_less = [ln for ln, has in sites if not has]
    assert len(clause_less) >= 14, (len(clause_less), sites)


def test_the_returned_mark_is_written_only_on_the_way_out():
    """`verdict` is the property the RETURN establishes. This is what makes the new reading
    load-bearing rather than lucky: every assignment to `ev["verdict"]` inside `verify` sits
    immediately above one of its `return ev` statements, so no raise site can hand this
    reader a receipt already carrying it."""
    fn = _verify_fn_node()
    returns = sorted(n.lineno for n in ast.walk(fn) if isinstance(n, ast.Return))
    assigns = sorted(
        n.lineno for n in ast.walk(fn) if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
        and t.value.id == "ev" and isinstance(t.slice, ast.Constant)
        and t.slice.value == GSG.VERIFY_RECEIPT_RETURNED_KEY)
    assert assigns, "no `ev['verdict']` assignment found; re-derive this reader"
    assert len(assigns) == len(returns), (assigns, returns)
    for a, r in zip(assigns, returns):
        assert a < r, (a, r)


def test_a_receipt_carrying_the_returned_mark_is_still_admitted():
    """The direction the clause must not bound: `verify`'s own RETURN value, unaltered."""
    ev = RG.verify(ASSEMBLY_API, family="wan", carries_no_sampler=True,
                   frame=(832, 480, 81))
    assert str(ev[GSG.VERIFY_RECEIPT_RETURNED_KEY]).strip()


def test_the_admission_still_passes_end_to_end_on_a_real_builder_receipt(tmp_path, capsys):
    """And through the CLI, so the reader's new key is proven not to close the green path."""
    assert GSG.main(_assembly_cli(tmp_path)) == 0
    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("SAVED_ADMISSION_OK ")]
    assert line, "the green admission stopped printing its OK line"


def test_the_halt_line_reads_the_caught_refusal_clause(tmp_path):
    """Rule 4 — the halt record READ off `__main__`, on the auditor's own operand."""
    ev = _caught_refusal(CAMERA_LINKED_FRAME)
    record = _write(tmp_path, "in/caught.json", {"gates": {"ROUTE": ev}})
    code, halt = _gsg_halt(tmp_path, [f"--record={record}", "--frame=832,480,81"])
    assert code == 2, halt
    assert halt["error"] == "RouteGate", halt
    assert halt["evidence"]["clause"] == "record_carries_a_caught_refusal", halt
    assert halt["evidence"]["refusal_clauses"] == [], halt
    assert halt["evidence"]["n_unmarked_receipts"] == 1, halt
    assert halt["evidence"]["returned_receipt_key"] == "verdict", halt


# ===========================================================================
# F-1b6be488 — the LAST gate before a paid submission opened its `--out` with no Gate OUT.
#
# Operand (the auditor's, RE-MEASURED on `e8263a3`): the assembly fixture that runs GREEN —
# the same files as the control run, which printed SAVED_ADMISSION_OK at exit 0 — with
# `--out` pointing at an existing DIRECTORY. Every gate PASSED and the tool then exited 1
# with `SAVED_ADMISSION_HALT {"error": "PermissionError", "message": "[Errno 13] Permission
# denied: '...\\out\\isadir'", "evidence": null}` (`IsADirectoryError` on POSIX) — "this tool
# crashed", with a stdlib exception name where a clause belongs, and no admission record for
# the spend that had just been cleared.
#
# The wave-18 entry closed this sibling BY MEASUREMENT on the wrong fixture: it recorded
# "`--out=<an existing directory>` reaches Gate PAIR first on this fixture, so the write
# shape is not reachable behind a passing graph here". The measurement is right about that
# fixture and the conclusion does not follow — that fixture cannot reach the write AT ALL.
# The red proof below therefore runs behind a graph that PASSES every gate.
#
# reverted-red: yes — measured in this worktree before the fix, exit 1 / PermissionError /
# evidence null on exactly the invocation below.
# ===========================================================================


import build_payload as BP  # noqa: E402


def test_gate_OUT_refuses_an_out_that_is_a_directory_behind_a_PASSING_graph(tmp_path):
    """The operand, in-process: the green assembly admission with `--out` on a directory."""
    isadir = tmp_path / "out" / "isadir"
    isadir.mkdir(parents=True)
    argv = _assembly_cli(tmp_path, out=isadir)
    exc, ev = _raises(GSG.main, argv)
    assert isinstance(exc, BP.PayloadOutHalt), repr(exc)
    assert ev["clause"] == "out_path_is_a_directory", ev
    assert ev["gate"] == "OUT" and ev["andon"] == "PayloadOutHalt", ev
    assert ev["flag"] == "--out" and ev["is_dir"] is True, ev


def test_the_same_invocation_without_the_directory_still_reaches_the_OK_line(tmp_path,
                                                                            capsys):
    """The direction the gate must not bound, and the proof the operand really is green
    otherwise: one character of difference between this and the refusal above."""
    assert GSG.main(_assembly_cli(tmp_path)) == 0
    printed = [ln for ln in capsys.readouterr().out.splitlines()
               if ln.startswith("SAVED_ADMISSION_OK ")]
    assert printed, "the control invocation stopped printing its OK line"
    line = json.loads(printed[0][len("SAVED_ADMISSION_OK "):])
    assert line["gate_OUT"], line
    written = json.loads((tmp_path / "out" / "admission.json").read_text(encoding="utf-8"))
    assert written["gates"]["OUT"]["clause"] == "out_path_is_a_directory", written["gates"]
    assert written["gates"]["OUT"]["verdict"], written["gates"]["OUT"]


def test_the_halt_line_reads_the_gate_OUT_clause(tmp_path):
    """Rule 4 — driven through `__main__`, the halt record READ, at the gate exit code."""
    isadir = tmp_path / "out" / "isadir"
    isadir.mkdir(parents=True)
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"),
         *_assembly_cli(tmp_path, out=isadir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    line = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("SAVED_ADMISSION_HALT ")]
    assert line, proc.stdout + proc.stderr
    halt = json.loads(line[-1][len("SAVED_ADMISSION_HALT "):])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "PayloadOutHalt", halt
    assert halt["evidence"]["clause"] == "out_path_is_a_directory", halt
    assert halt["evidence"]["gate"] == "OUT", halt


# ---- the census: keyed on the RESOLVED shape, not on a file list.

#: The domain's own tools. Enumerated from the tree so a tool added later joins the census.
DOMAIN_TOOLS = sorted({
    os.path.basename(p) for p in
    glob.glob(os.path.join(TOOLS, "build_*payload*.py"))
    + [os.path.join(TOOLS, n) for n in
       ("build_payload.py", "canon_gate.py", "gate_saved_graph.py",
        "fetch_run.py", "fetch_t2v_run.py")]})

#: The names that ARE a Gate OUT, wherever the call sits.
GATE_OUT_CALLS = {"gate_out_writable", "gate_out_paths"}


def _out_writes_and_their_gate(path):
    """`[(function, opens `--out` directly, calls a Gate OUT)]` for one tool.

    A write is `open(<x>, "w"...)` whose target is the parsed `--out` value itself
    (`a.out` / `args.out`) — a path the tool opens rather than a directory it creates. The
    shape is resolved from the AST, never from a spelling: a tool that renames its namespace
    variable is still read, and a tool that joins `--out` with a filename is correctly NOT
    in this population, because `os.makedirs` on a directory is not the defect this bounds.
    """
    tree = ast.parse(open(os.path.join(TOOLS, path), encoding="utf-8").read())
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        opens_out = False
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            if getattr(call.func, "id", None) != "open" or not call.args:
                continue
            target = call.args[0]
            mode = call.args[1].value if (len(call.args) > 1
                                          and isinstance(call.args[1], ast.Constant)) else \
                next((kw.value.value for kw in call.keywords
                      if kw.arg == "mode" and isinstance(kw.value, ast.Constant)), "r")
            if (isinstance(target, ast.Attribute) and target.attr == "out"
                    and isinstance(target.value, ast.Name)
                    and "w" in str(mode)):
                opens_out = True
        gated = any((getattr(c.func, "id", None) or getattr(c.func, "attr", None))
                    in GATE_OUT_CALLS
                    for c in ast.walk(fn) if isinstance(c, ast.Call))
        if opens_out:
            out.append((fn.name, opens_out, gated))
    return out


def test_every_tool_that_OPENS_its_out_is_bounded_by_a_gate_OUT():
    """The population, re-derived every run. `gate_out_paths` was the ONLY Gate OUT in this
    domain on `e8263a3` and NO other builder or fetcher called it — re-censused there. A
    tool whose `--out` is a directory it creates is correctly outside this population; a
    tool that OPENS the value is inside it and must be gated."""
    ungated = {name: sites for name in DOMAIN_TOOLS
               for sites in [[fn for fn, _o, g in _out_writes_and_their_gate(name)
                              if not g]]
               if sites}
    assert ungated == {}, ungated


def test_the_census_would_have_seen_the_defect_it_was_written_for():
    """A census that cannot fail is not a census. `gate_saved_graph.main` is in the
    population — it OPENS `--out` — so the pre-fix tree, where nothing in that function
    called a Gate OUT, would have failed the check above."""
    sites = _out_writes_and_their_gate("gate_saved_graph.py")
    assert [fn for fn, _o, _g in sites] == ["main"], sites
    assert all(gated for _fn, _o, gated in sites), sites
    assert "gate_out_writable" in open(
        os.path.join(TOOLS, "gate_saved_graph.py"), encoding="utf-8").read()


def test_gate_out_writable_is_the_ONE_home_of_the_directory_clause():
    """No second spelling: `os.path.isdir` guarding a write raises through this function in
    every tool of the domain, so the two clause words have one implementation."""
    spellings = []
    for name in DOMAIN_TOOLS:
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        for lineno, line in enumerate(src.splitlines(), 1):
            if "is a DIRECTORY, so" in line and "raise" not in line:
                spellings.append((name, lineno))
    assert [n for n, _ln in spellings] == ["build_payload.py"], spellings


# ===========================================================================
# F-f97b0bb3 (panel CRITICAL) — Gate L's verdict said PROVEN whether or not an independent
#              frame was ever supplied, and neither the printed line nor the written record
#              carried a key saying which.
#
# Operand (the auditor's, MEASURED on `e8263a3` as subprocesses on a graph whose
# EmptyHunyuanLatentVideo pins 832x480x81):
#   WITHOUT --frame           -> exit 0, `gate_L: 832x480x81 legal (PROVEN)`, sources ['graph']
#   WITH --frame=832,480,81   -> exit 0, gate_L line BYTE-IDENTICAL, sources ['graph','supplied']
#   WITH --frame=832,480,65   -> exit 2, RouteGate, frame_legality_verdict CONTRADICTED
# The only tell between "checked against an independently supplied frame" and "checked
# against nothing" was a count buried inside gate_ROUTE's string.
#
# reverted-red: yes — the byte-identity of the two printed lines IS the reverted tree, and
# the first assertion below is exactly that comparison.
# ===========================================================================


LATENT_API = {
    "5": {"class_type": "EmptyHunyuanLatentVideo",
          "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}},
}

LATENT_SAVED = {"nodes": [
    {"id": 5, "type": "EmptyHunyuanLatentVideo", "inputs": [],
     "widgets_values": [832, 480, 81, 1]},
], "links": []}


def _latent_cli(tmp_path, frame=None, out_name="admission.json"):
    api = _write(tmp_path, "in/l.api.json", LATENT_API)
    saved = _write(tmp_path, "in/l.saved.json", LATENT_SAVED)
    seeds = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    record = _write(tmp_path, "in/rec.json", _builder_record(
        LATENT_API, family="wan", carries_no_sampler=True, frame=(832, 480, 81)))
    argv = [f"--saved={saved}", f"--api={api}", f"--seeds={seeds}",
            f"--out={tmp_path / 'out' / out_name}", f"--record={record}"]
    if frame is not None:
        argv.append(f"--frame={frame}")
    return argv


def _ok_line(tmp_path, capsys, frame=None, out_name="admission.json"):
    assert GSG.main(_latent_cli(tmp_path, frame=frame, out_name=out_name)) == 0
    printed = [ln for ln in capsys.readouterr().out.splitlines()
               if ln.startswith("SAVED_ADMISSION_OK ")]
    assert printed, "no OK line"
    return json.loads(printed[-1][len("SAVED_ADMISSION_OK "):])


def test_the_printed_gate_L_line_DIFFERS_between_a_supplied_frame_and_none(tmp_path,
                                                                          capsys):
    """The operand, exactly: one graph, two invocations, the printed line compared.

    On `e8263a3` the two `gate_L` strings were byte-identical, so an operator reading the
    last check before a paid submission could not tell a verdict checked against an
    independent frame from one proven off the graph agreeing with itself."""
    alone = _ok_line(tmp_path, capsys, frame=None, out_name="alone.json")
    supplied = _ok_line(tmp_path, capsys, frame="832,480,81", out_name="supplied.json")
    assert alone["gate_L"] != supplied["gate_L"], alone["gate_L"]
    assert "graph alone" in alone["gate_L"], alone["gate_L"]
    assert "supplied and agreed" in supplied["gate_L"], supplied["gate_L"]


def test_the_OK_line_carries_the_frame_source_as_its_own_key(tmp_path, capsys):
    """A reader keys on a KEY, never on a substring of a sentence."""
    alone = _ok_line(tmp_path, capsys, frame=None, out_name="alone.json")
    supplied = _ok_line(tmp_path, capsys, frame="832,480,81", out_name="supplied.json")
    assert alone["gate_L_frame_source"] == "graph alone, no independent frame supplied"
    assert supplied["gate_L_frame_source"] == "supplied and agreed"


def test_the_written_record_says_it_too_and_names_the_flag(tmp_path, capsys):
    """The receipt a later session reconciles, not only the line the operator saw."""
    _ok_line(tmp_path, capsys, frame=None, out_name="alone.json")
    written = json.loads((tmp_path / "out" / "alone.json").read_text(encoding="utf-8"))
    block = written["gates"]["L_source"]
    assert block["clause"] == "gate_l_frame_source", block
    assert block["flag"] == "--frame" and block["supplied"] is None, block
    assert block["independently_checked"] is False, block
    assert block["sources"] == ["graph"], block
    assert "proven off the graph alone" in block["verdict"].lower(), block


def test_a_supplied_frame_that_CONTRADICTS_the_graph_still_refuses(tmp_path):
    """The direction the new key must not soften: recording the source is not a substitute
    for the clash clause, and the clash clause still fires."""
    exc, ev = _raises(GSG.main, _latent_cli(tmp_path, frame="832,480,65"))
    assert isinstance(exc, RG.RouteGate), repr(exc)
    assert "CONTRADICTED" in json.dumps(ev, default=str), sorted(ev)


def test_the_frame_source_block_is_derived_from_gate_L_not_from_the_flag(tmp_path):
    """Rule 1 — keyed on the RESOLVED shape. The block reads the `source` field Gate L
    itself stamps on each checked frame, so a route that acquires a second independent
    source joins the reading without a new branch; the raw flag is recorded beside it as
    context, never as the answer."""
    checked = RG.verify(LATENT_API, family="wan", carries_no_sampler=True,
                        frame=(832, 480, 81))["frame_legality"]
    block = GSG.gate_l_frame_source(checked, "832,480,81")
    assert block["sources"] == ["graph", "supplied"], block
    assert block["independently_checked"] is True, block
    # and the same call with the flag's text present but Gate L having seen only the graph
    # reads FALSE — the flag is not what the block is keyed on.
    graph_only = RG.verify(LATENT_API, family="wan",
                           carries_no_sampler=True)["frame_legality"]
    lying = GSG.gate_l_frame_source(graph_only, "832,480,81")
    assert lying["independently_checked"] is False, lying


def test_the_hosted_tier_route_is_named_rather_than_called_graph_alone():
    """Why `--frame` is recorded-not-required, measured rather than preferred: the hosted
    tiers carry no pixel dimension at all, so a required `--frame` would demand a number
    that route does not have. The block says so in its own words."""
    block = GSG.gate_l_frame_source([], None, hosted_tier="wan2.7-r2v")
    assert "INAPPLICABLE" in block["verdict"], block
    assert block["independently_checked"] is False, block
    assert "wan2.7-r2v" in RG.HOSTED_TIER_RULES, sorted(RG.HOSTED_TIER_RULES)


def test_the_frame_source_reaches_the_subprocess_line_too(tmp_path):
    """Rule 4 — read off the tool's own `__main__`, not off an in-process return."""
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"),
         *_latent_cli(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    line = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("SAVED_ADMISSION_OK ")]
    assert line, proc.stdout + proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    printed = json.loads(line[-1][len("SAVED_ADMISSION_OK "):])
    assert printed["gate_L_frame_source"] == "graph alone, no independent frame supplied"
