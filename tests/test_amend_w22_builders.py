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
    # WAVE 25 (core-gates, F-7285034a): the list EMPTIED, which this test's own docstring
    # names as the outcome that would make the reading below "merely redundant — a different
    # fact, and this says which". Every `RouteGate` / `PairGate` raise in
    # `armature_core/route_gates.py` now carries a `clause`, the licence kill and Gate L's
    # hosted refusals among them, so a halt reader can key on the word at the last gate
    # before a paid submission. The four that used to sit here were "banned component",
    # "camera agreement INDETERMINATE", "illegal frame" and "no latent and no frame"; their
    # clause words are now `banned_or_excluded_component`, `camera_frame_contradicted`,
    # `frame_illegal` and `frame_legality_indeterminate`.
    assert clauseless == [], clauseless


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
    # WAVE 25 (core-gates, F-7285034a): was `== []`, because the caught refusal in this
    # fixture (`CAMERA_LINKED_FRAME`, which reaches `_seed_population_andon`) carried no
    # clause at all. It now carries `no_seed_population`, which is the point: the reader
    # `route_facts` keys on — `refusals = [r for r in receipts if r.get("clause")]` — can
    # now NAME the refusal it caught instead of listing an empty set beside a halt.
    assert halt["evidence"]["refusal_clauses"] == ["no_seed_population"], halt
    # WAVE 25 (core-gates, F-7285034a): was `== 1`. The same fix moves this number the other
    # way and for the same reason — a receipt is "unmarked" when it carries neither `clause`
    # nor the returned-receipt key, and this one now carries a clause, so it is a NAMED
    # refusal rather than an unclassifiable record. `route_facts`' two categories still
    # partition the receipts; what changed is which side this fixture lands on.
    assert halt["evidence"]["n_unmarked_receipts"] == 0, halt
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


# ===========================================================================
# F-2380aca9 — the ONE operator-supplied input both fetchers take reached the operator as a
#              bare stdlib traceback, in the modules whose own `__main__` comments tell
#              wrappers to key on a sentinel.
#
# Operands (the auditor's, RE-MEASURED on `e8263a3` as five `fetch_run` subprocesses, every
# one exit 1 with `"evidence": null`): `--dump` naming no file -> FileNotFoundError; no
# `results` key -> KeyError 'results'; not JSON -> JSONDecodeError; a row with no `url` ->
# KeyError 'url'; `results` holding strings -> TypeError. The sibling `fetch_t2v_run`
# carried the identical two lines and RE-MEASURED identically on two of them.
#
# reverted-red: yes — measured in this worktree before the reader landed, both fetchers.
# ===========================================================================


def _dump(tmp_path, doc, name="dump.json", raw=None):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        p.write_text(raw, encoding="utf-8")
    else:
        p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


#: Every shape the finding enumerates, with the clause each must now name. Driven against
#: BOTH fetchers — the sibling was in the same condition and is not carried on faith.
W22_DUMP_SHAPES = {
    "no such file": (None, "dump_missing"),
    "not JSON": ("{not json", "dump_unreadable"),
    "a JSON list, not an object": ("[1, 2, 3]", "dump_not_a_mapping"),
    "no `results` key": ('{"outputs": []}', "dump_no_results_key"),
    "`results` is not a list": ('{"results": {"a": 1}}', "dump_results_not_a_list"),
    "`results` holds strings": ('{"results": ["a", "b"]}',
                                "dump_result_row_not_a_mapping"),
    "a row with no `url`": ('{"results": [{"source_node_id": "302", '
                            '"filename": "00000.png"}]}',
                            "dump_result_row_missing_a_key"),
    "a row with no `source_node_id`": ('{"results": [{"url": "https://x.invalid/0", '
                                       '"filename": "00000.png"}]}',
                                       "dump_result_row_missing_a_key"),
}


@pytest.mark.parametrize("shape", sorted(W22_DUMP_SHAPES))
def test_the_dump_reader_names_every_shape_it_refuses(shape, tmp_path):
    raw, clause = W22_DUMP_SHAPES[shape]
    path = (str(tmp_path / "nope.json") if raw is None
            else _dump(tmp_path, None, raw=raw))
    exc, ev = _raises(FR.read_results_dump, path)
    assert isinstance(exc, FR.FetchHalt), (shape, repr(exc))
    assert ev["clause"] == clause, (shape, ev)
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt", (shape, ev)
    assert ev["flag"] == "--dump", (shape, ev)


@pytest.mark.parametrize("shape", sorted(W22_DUMP_SHAPES))
@pytest.mark.parametrize("tool", ["fetch_run.py", "fetch_t2v_run.py"])
def test_both_fetchers_refuse_every_dump_shape_at_the_gate_exit_code(tool, shape,
                                                                    tmp_path):
    """Rule 2 — the SIBLING is driven, not carried; and rule 4 — the halt line is READ off
    each tool's own `__main__`, at the code that means a gate refused."""
    raw, clause = W22_DUMP_SHAPES[shape]
    path = (str(tmp_path / "nope.json") if raw is None
            else _dump(tmp_path, None, raw=raw, name=f"{abs(hash(shape))}.json"))
    sentinel = ("FETCH_RUN_HALT" if tool == "fetch_run.py" else "FETCH_T2V_HALT")
    args = ([f"--dump={path}", "--run=r", f"--root={tmp_path / 'runs'}"]
            if tool == "fetch_run.py" else
            [f"--dump={path}", f"--out={tmp_path / 'out'}"])
    proc, halts, oks = _sub(tool, args, sentinel)
    assert halts, proc.stdout + proc.stderr
    halt = json.loads(halts[-1][len(sentinel) + 1:])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "FetchHalt", halt
    assert halt["evidence"]["clause"] == clause, halt
    assert not oks, oks


def test_a_well_formed_dump_still_reads_the_direction_the_clause_must_not_bound(tmp_path):
    rows = [{"source_node_id": "302", "filename": "00000.png",
             "url": "https://example.invalid/0"}]
    assert FR.read_results_dump(_dump(tmp_path, {"results": rows})) == rows


def test_the_two_fetchers_read_the_dump_through_ONE_function():
    """No second spelling. Keyed on the RESOLVED shape by AST — a bare `json.load(...)`
    subscripted by `"results"` — rather than on the literal text, which appears in the new
    reader's own docstring as the measurement it records."""
    for name in ("fetch_run.py", "fetch_t2v_run.py"):
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        bare = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Subscript)
                and isinstance(n.slice, ast.Constant) and n.slice.value == "results"
                and isinstance(n.value, ast.Call)
                and getattr(n.value.func, "attr", None) == "load"
                and getattr(getattr(n.value.func, "value", None), "id", None) == "json"]
        assert bare == [], (name, bare)
    assert FT.read_results_dump is FR.read_results_dump


# ===========================================================================
# F-7e45e62b — `--run` is joined into the run root AND pasted into the video tap's filename
#              with no validation anywhere, and the tool then prints its success sentinel
#              over a population that is not the population on disk.
#
# Operand (the auditor's, MEASURED with the downloader stubbed to write the planned bytes):
#   `--run=sub/dir --root=runs` -> returned 0 and printed
#   FETCH_RUN_OK {"run": "sub/dir", "dir": "runs\\sub/dir", "by_node": {"302": 1, "114": 1},
#                 "video": [], "gate_FETCH": "2 planned file(s), all present and non-empty,
#                 2 of them content-signature checked, and no unplanned file in 3 swept
#                 directory(s)"}
#   while the video was written to runs/sub/dir/sub/dir_00000.mp4.
# Measured on `plan` alone: `--run=../../escaped` sends the frames to
# outputs/escaped/lossless/ and the video to `escaped_00000.mp4` in the PROCESS CWD.
#
# reverted-red: yes — both measured in this worktree before the bound landed.
# ===========================================================================


def _fr_dump(tmp_path, n_frames=1, video=True, name="dump.json"):
    rows = [{"source_node_id": "302", "filename": f"{i:05d}.png",
             "url": f"https://example.invalid/{i}"} for i in range(n_frames)]
    if video:
        rows.append({"source_node_id": "114", "filename": "clip.mp4",
                     "url": "https://example.invalid/v"})
    return _dump(tmp_path, {"results": rows}, name=name)


def _stub_fr(monkeypatch):
    """A downloader that writes signature-correct bytes for whatever the plan asked for."""
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env[FR.MANIFEST_ENV], encoding="utf-8") as fh:
            jobs = json.load(fh)
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            body = (FR.PNG_SIGNATURE + b"IHDR-and-the-rest"
                    if job["out"].lower().endswith(".png") else
                    b"\x00\x00\x00\x18ftypmp42" + b"rest")
            with open(job["out"], "wb") as out:
                out.write(body)
        target = env.get(FR.EXITS_ENV)
        if target:
            with open(target, "w", encoding="utf-8") as fh:
                json.dump([{"out": j["out"], "url": j["url"], "code": 0, "message": ""}
                           for j in jobs], fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(FR.subprocess, "run", fake_run)


#: The operands the auditor measured, plus the sibling spellings a census of the predicate
#: reaches. `A2` is the direction the bound must NOT close.
W22_RUN_NAMES = ["sub/dir", "../../escaped", "..\\..\\win", "..", ".", "", "/abs"]


@pytest.mark.parametrize("run", W22_RUN_NAMES)
def test_a_run_that_is_not_a_name_is_refused_before_anything_is_created(run, tmp_path,
                                                                       monkeypatch,
                                                                       capsys):
    _stub_fr(monkeypatch)
    root = tmp_path / "runs"
    exc, ev = _raises(FR.main, ["--dump", _fr_dump(tmp_path), "--run", run,
                                "--root", str(root)])
    assert isinstance(exc, FR.FetchHalt), (run, repr(exc))
    assert ev["clause"] == "output_name_is_not_a_name", (run, ev)
    assert ev["flag"] == "--run", (run, ev)
    assert "FETCH_RUN_OK" not in capsys.readouterr().out
    assert not root.exists(), sorted(p.name for p in tmp_path.iterdir())


def test_an_ordinary_run_name_still_returns_its_video_in_the_reported_population(
        tmp_path, monkeypatch, capsys):
    """The direction the bound must not close, and the one the finding names by hand: the
    video is IN `vids`, which is what the nested spelling silently emptied."""
    _stub_fr(monkeypatch)
    root = tmp_path / "runs"
    assert FR.main(["--dump", _fr_dump(tmp_path), "--run", "A2",
                    "--root", str(root)]) == 0
    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("FETCH_RUN_OK ")]
    assert line, "no OK line"
    printed = json.loads(line[-1][len("FETCH_RUN_OK "):])
    assert printed["video"] == ["A2_00000.mp4"], printed
    assert (root / "A2" / "A2_00000.mp4").is_file()


def test_the_halt_line_reads_the_run_clause(tmp_path):
    """Rule 4 — driven through `__main__` (no stub: the refusal is above the download)."""
    proc, halts, oks = _sub("fetch_run.py",
                            [f"--dump={_fr_dump(tmp_path)}", "--run=sub/dir",
                             f"--root={tmp_path / 'runs'}"], "FETCH_RUN_HALT")
    assert halts, proc.stdout + proc.stderr
    halt = json.loads(halts[-1][len("FETCH_RUN_HALT "):])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "FetchHalt", halt
    assert halt["evidence"]["clause"] == "output_name_is_not_a_name", halt
    assert halt["evidence"]["flag"] == "--run", halt
    assert not oks
    assert not (tmp_path / "runs").exists()


# ---- the siblings: four more free strings pasted into a written filename.

#: `(module name, argv that reaches the bound, the flag)`. Each bound sits directly under
#: `parse_args`, so the argv only has to satisfy argparse.
W22_FILENAME_FLAGS = [
    ("build_animate_payload",
     ["--uploads=nope.json", "--out=nope", "--experiment=a/b"], "--experiment"),
    ("build_i2v_payload",
     ["--uploads=nope.json", "--out=nope", "--e08-record=nope.json",
      "--experiment=a/b"], "--experiment"),
    ("build_camera_i2v_payload",
     ["--uploads=nope.json", "--out=nope", "--w1-record=nope.json",
      "--experiment=../escaped"], "--experiment"),
    ("build_t2v_payload", ["--out=nope", "--tag=../escaped"], "--tag"),
]


@pytest.mark.parametrize("mod,argv,flag", W22_FILENAME_FLAGS,
                         ids=[r[0] for r in W22_FILENAME_FLAGS])
def test_every_sibling_flag_pasted_into_a_filename_is_bounded_too(mod, argv, flag):
    """Rule 2 — the census the wave-16 rate fix did not do. Five free-string flags in this
    domain reach a written filename; `fetch_run --run` was one and these are the other
    four."""
    module = __import__(mod)
    exc, ev = _raises(module.main, argv)
    assert type(exc).__name__ == "PayloadError", (mod, repr(exc))
    assert ev["clause"] == "output_name_is_not_a_name", (mod, ev)
    assert ev["flag"] == flag, (mod, ev)
    assert ev["pasted_into"], (mod, ev)


def test_the_wave_flag_is_already_bounded_by_argparse_and_takes_no_clause(capsys):
    """The sibling that needs NOTHING, measured rather than assumed.
    `build_camera_i2v_payload --wave` also reaches a written filename and is `type=int`, so
    argparse refuses a separator before `main` is entered — a clause here would be a clause
    with no caller, which this repo arms or deletes rather than ships."""
    import build_camera_i2v_payload as CAM
    with pytest.raises(SystemExit) as exc:
        CAM.parse_args(["--uploads=x", "--out=y", "--w1-record=z", "--wave=a/b"])
    assert exc.value.code == 2
    assert "invalid int value" in capsys.readouterr().err


def test_single_path_segment_has_ONE_home_and_this_domain_only_imports_it():
    """SEAM 1: adopted by import, never a third copy. No file in this domain defines it."""
    for name in DOMAIN_TOOLS:
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        assert "def single_path_segment(" not in src, name
    assert FR.single_path_segment.__module__ in (
        "armature_core.parts", "resample_motion"), FR.single_path_segment.__module__


# ===========================================================================
# F-894dffb2 — the per-job download-exit gate's receipt reached neither the FETCH_T2V_OK
#              line nor any of the four JSON records this tool leaves in the run root.
#
# `download(jobs, out=a.out)` discarded BOTH return values. `fetch_run.download` returns
# `(proc, {"gate": "FETCH", "clause": "downloader_job_exits", "record": ..., "jobs": n,
# "verdict": ...})` and the sibling prints it as `gate_EXITS` in FETCH_RUN_OK. Read on
# `e8263a3`: FETCH_T2V_OK carried `gate_ORDER` and `gate_FETCH` and no `gate_EXITS`.
# Stated as the bound: the gate itself still RAISED inside `download`, so this is a missing
# RECEIPT rather than a missing check — but the two fetchers printed different evidence for
# the same shared andon, and a later session reading this run's receipts could not tell a
# gate that passed from a gate that was never run.
#
# reverted-red: yes — measured in this worktree, the key was absent from the OK line and
# from `download_manifest.json`.
# ===========================================================================


def _t2v_run(tmp_path, monkeypatch, n_frames=2):
    """Drive `fetch_t2v_run.main` with the downloader stubbed, and return the OK line."""
    rows = [{"source_node_id": FT.LOSSLESS_NODE, "filename": f"{i:012x}.png",
             "url": f"https://example.invalid/{i}"} for i in range(n_frames)]
    dump = _dump(tmp_path, {"results": rows}, name="t2v-dump.json")
    out = tmp_path / "run"

    def fake_download(jobs, out=None):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            with open(j["out"], "wb") as fh:
                fh.write(FR.PNG_SIGNATURE + b"IHDR-and-the-rest")
        return None, {"gate": "FETCH", "clause": "downloader_job_exits",
                      "record": "download_exits.json", "jobs": len(jobs),
                      "n_recorded": len(jobs), "n_unrecorded": 0,
                      "verdict": (f"{len(jobs)} download(s), each recording its own exit, "
                                  f"all zero")}

    monkeypatch.setattr(FT, "download", fake_download)
    monkeypatch.setattr(FT, "order_evidence", lambda o: {
        "results_array_order": {"mean": 0.7}, "hash_sorted_order": {"mean": 5.3},
        "what_this_shows": "x"})
    return dump, out


def test_the_t2v_OK_line_carries_the_same_gate_keys_as_its_sibling(tmp_path, monkeypatch,
                                                                   capsys):
    dump, out = _t2v_run(tmp_path, monkeypatch)
    assert FT.main([f"--dump={dump}", f"--out={out}"]) == 0
    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("FETCH_T2V_OK ")]
    assert line, "no OK line"
    printed = json.loads(line[-1][len("FETCH_T2V_OK "):])
    assert "gate_EXITS" in printed, sorted(printed)
    assert printed["gate_EXITS"].endswith("all zero"), printed["gate_EXITS"]
    assert {"gate_FETCH", "gate_ORDER", "gate_EXITS"} <= set(printed), sorted(printed)


def test_the_exit_receipt_survives_the_process_in_the_run_root(tmp_path, monkeypatch):
    """Observability is a receipt a reader can reconcile, not only a line that scrolled by."""
    dump, out = _t2v_run(tmp_path, monkeypatch)
    assert FT.main([f"--dump={dump}", f"--out={out}"]) == 0
    doc = json.loads((out / "download_manifest.json").read_text(encoding="utf-8"))
    assert doc["gates"]["EXITS"]["clause"] == "downloader_job_exits", doc.get("gates")
    assert doc["gates"]["EXITS"]["jobs"] == 2, doc["gates"]["EXITS"]
    # the record it replaces is still there: the manifest keeps its own `files` block
    assert [f["out"] for f in doc["files"]], doc


def test_both_fetchers_print_the_same_gate_key_for_the_shared_andon():
    """Keyed on the RESOLVED shape: the OK payload literal in each `main`, read by AST, must
    carry the same gate keys — the two tools share ONE andon and printed two receipts."""
    keys = {}
    for name, sentinel in (("fetch_run.py", "FETCH_RUN_OK "),
                           ("fetch_t2v_run.py", "FETCH_T2V_OK ")):
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            names = [k.value for k in node.keys
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if any(n.startswith("gate_") for n in names):
                found.append(sorted(n for n in names if n.startswith("gate_")))
        keys[name] = found
    assert any("gate_EXITS" in row for row in keys["fetch_run.py"]), keys
    assert any("gate_EXITS" in row for row in keys["fetch_t2v_run.py"]), keys


# ===========================================================================
# F-a25a7db9 — Gate FETCH's stray-detection exemption kept exempting EVERY run's review clip
#              rather than this run's, and the module's own record stated the fix was
#              blocked by a condition removed in wave 16.
#
# RE-MEASURED on `e8263a3`: `derived_root_artifacts('A2')` exempts `review_0.50x_8fps.mp4`
# and `review_0.50x_8fps.webp` by pattern 1 whatever run produced them;
# `A0r1_review_0.50x_8fps.mp4` (another run's TOKENED clip) matches neither and correctly
# raises; `A2_review_0.50x_8fps.mp4` matches pattern 0. The CORRECTION block above the
# patterns still closed "`make_review_clip.clip_name` returns `review_{rate:.2f}x_{fps}fps.
# <ext>` with no run token, and that tool is not this one's to change" — READ in this
# worktree at `tools/make_review_clip.py:144-160`, `clip_name(fps, source_fps, run=None)`
# returns `f"{run}_{stem}"` when a token is known and `run_token` derives one (wave 16,
# F-78f49c7c).
#
# reverted-red: yes — the receipt carried no `root_exempt_matched_by` at all, and the
# premise sentence read as above.
# ===========================================================================


def _landed(tmp_path, run="A0r1", extra_root=()):
    base = tmp_path / "runs" / run
    (base / "lossless").mkdir(parents=True)
    jobs = [(f"https://example.invalid/{i}", str(base / "lossless" / f"{i:05d}.png"))
            for i in range(2)]
    for _u, o in jobs:
        with open(o, "wb") as fh:
            fh.write(FR.PNG_SIGNATURE + b"IHDR")
    for name in extra_root:
        (base / name).write_bytes(b"\x00\x00\x00\x18ftypmp42rest")
    return base, jobs


def test_an_UNTOKENED_review_clip_is_still_tolerated_and_the_receipt_SAYS_it_is_untokened(
        tmp_path):
    """The operand the finding names: another run's UN-TOKENED clip left in a re-used run
    root. It is still exempt — `clip_name` still emits an un-tokened name when no token can
    be derived — but the exemption is no longer silent about being unattributable."""
    base, jobs = _landed(tmp_path, extra_root=("review_0.50x_8fps.mp4",))
    ev = FR.verify_downloads(jobs, directories=[str(base / "lossless")], root=str(base),
                             root_exempt=FR.derived_root_artifact_rules("A0r1"))
    assert ev["extra"] == []
    by = ev["root_exempt_matched_by"]
    assert [os.path.basename(x["path"]) for x in by] == ["review_0.50x_8fps.mp4"], by
    assert by[0]["run_bound"] is False, by
    assert "CANNOT tell which run" in by[0]["rule"], by
    assert "UN-TOKENED" in ev["verdict"], ev["verdict"]


def test_this_runs_OWN_tokened_clip_is_tolerated_and_recorded_as_run_bound(tmp_path):
    base, jobs = _landed(tmp_path, extra_root=("A0r1_review_0.50x_8fps.mp4",))
    ev = FR.verify_downloads(jobs, directories=[str(base / "lossless")], root=str(base),
                             root_exempt=FR.derived_root_artifact_rules("A0r1"))
    by = ev["root_exempt_matched_by"]
    assert by[0]["run_bound"] is True, by
    assert "this run's own" in ev["verdict"], ev["verdict"]


def test_another_runs_TOKENED_clip_still_raises(tmp_path):
    """The direction the labelling must not soften."""
    base, jobs = _landed(tmp_path, extra_root=("A2_review_0.50x_8fps.mp4",))
    exc, ev = _raises(FR.verify_downloads, jobs,
                      directories=[str(base / "lossless")], root=str(base),
                      root_exempt=FR.derived_root_artifact_rules("A0r1"))
    assert isinstance(exc, FR.FetchHalt), repr(exc)
    assert [os.path.basename(x) for x in ev["extra"]] == ["A2_review_0.50x_8fps.mp4"]


def test_the_stale_premise_is_corrected_in_place_with_the_measurement():
    """Rule 2 for an advisor's prose: never quietly delete a wrong statement. The block says
    what was measured, names the function that overturned it, and states the residue."""
    doc = FR.derived_root_artifacts.__doc__
    assert "PREMISE is stale" in doc, doc[-800:]
    assert "make_review_clip.py:144-160" in doc, "the measurement, not a summary of it"
    assert "run_token" in doc and "wave 16" in doc, "and what overturned it"
    assert "residue" in doc, "and what remains true"


def test_the_run_token_the_stale_premise_said_did_not_exist_does(tmp_path):
    """The measurement itself, kept runnable rather than quoted."""
    import make_review_clip

    assert make_review_clip.clip_name(8, 16) == "review_0.50x_8fps.webp"
    assert make_review_clip.clip_name(8, 16, run="A2") == "A2_review_0.50x_8fps.webp"
    assert callable(getattr(make_review_clip, "run_token", None))


# ===========================================================================
# F-c03a23c5 — a `zero_length_frames` clause that could not fire, sitting between the real
#              andon and Gate ORDER.
#
# RE-MEASURED on `e8263a3` by calling `fetch_run.verify_downloads` directly on a single
# planned zero-byte `lossless/00000.png`: it raised `FetchHalt` with clause
# `downloaded_population_is_not_the_planned_one` before any manifest existed. `manifest` is
# built from a strict subset of the same planned frames, read from the same paths, and
# nothing between the two lines writes to them — so by the time the branch ran, every entry
# it inspected had already been shown non-zero by a raise-or-return above it.
#
# The tree's own rule decides which way it goes: a check that cannot fail is not a check.
# reverted-red: n/a for a deletion — what is asserted instead is that the coverage the
# deleted branch appeared to provide is REAL and lives where the comment now says it does,
# over a WIDER population (the video job included).
# ===========================================================================


def test_the_zero_length_coverage_lives_in_verify_downloads_and_fires_first(tmp_path):
    base = tmp_path / "run"
    (base / "lossless").mkdir(parents=True)
    out = base / "lossless" / "00000.png"
    out.write_bytes(b"")
    exc, ev = _raises(FR.verify_downloads, [{"out": str(out), "array_index": 0}],
                      directories=[str(base / "lossless")], root=str(base))
    assert isinstance(exc, FR.FetchHalt), repr(exc)
    assert ev["clause"] == "downloaded_population_is_not_the_planned_one", ev
    assert [os.path.basename(x) for x in ev["empty"]] == ["00000.png"], ev


def test_the_zero_length_coverage_reaches_the_VIDEO_job_the_deleted_branch_never_saw(
        tmp_path):
    """The reason the deletion is not a loss: the real andon's population is WIDER. The
    deleted branch read `manifest`, built only from frames with an `array_index`."""
    base = tmp_path / "run"
    (base / "lossless").mkdir(parents=True)
    frame = base / "lossless" / "00000.png"
    frame.write_bytes(FR.PNG_SIGNATURE + b"IHDR")
    donor = base / "donor.mp4"
    donor.write_bytes(b"")
    exc, ev = _raises(FR.verify_downloads,
                      [{"out": str(frame), "array_index": 0},
                       {"out": str(donor), "array_index": None}],
                      directories=[str(base / "lossless")], root=str(base))
    assert isinstance(exc, FR.FetchHalt), repr(exc)
    assert [os.path.basename(x) for x in ev["empty"]] == ["donor.mp4"], ev


def test_the_vacuous_clause_is_gone_and_the_comment_says_where_the_coverage_is():
    """The vacuous-clause census, keyed on the resolved shape: the clause word is raised
    nowhere in the module, and the comment that replaces it names the function that holds
    the coverage so a later session cannot delete the real one believing it lives here."""
    src = open(os.path.join(TOOLS, "fetch_t2v_run.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    raised = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Raise)
              for d in ast.walk(n)
              if isinstance(d, ast.Constant) and d.value == "zero_length_frames"]
    assert raised == [], raised
    assert "THE COVERAGE" in src and "verify_downloads" in src


# ===========================================================================
# F-a22e9575 — the one andon between an operator pasting ratified phrases into
#              `--canon-prompt` and a paid generation on text no canon governs raised a
#              halt record naming neither the gate nor the andon.
#
# RE-MEASURED on `e8263a3` by calling `canon_gate.gate_canon_ships_what_it_gated('a','b')`:
# GateCanon raised, `exc.evidence` keys exactly ['canon_prompt', 'clause', 'shipped'] while
# `type(exc).gate` read 'CANON'; the `__main__` block prints that dict verbatim under
# CANON_GATE_HALT, so a triage or a wrapper keyed on `evidence["gate"]` at the spend
# boundary read None. `canon_spend` calls it for all seven builders that arm Gate CANON, so
# it is the most-reached raise in the file.
# reverted-red: yes — the two keys were absent.
# ===========================================================================


def test_the_canon_ships_what_it_gated_refusal_names_its_gate_and_its_andon():
    from armature_core.errors import GateCanon

    exc, ev = _raises(CG.gate_canon_ships_what_it_gated, "a", "b")
    assert isinstance(exc, GateCanon), repr(exc)
    assert ev["gate"] == "CANON", ev
    assert ev["andon"] == "GateCanon", ev
    assert ev["clause"] == "gated_text_is_not_shipped_text", ev
    assert ev["canon_prompt"] == "a" and ev["shipped"] == "b", ev
    # the tree's law: `ev["gate"]` is the raised class's OWN `.gate`, `ev["andon"]` its name
    assert ev["gate"] == type(exc).gate, (ev, type(exc).gate)
    assert ev["andon"] == type(exc).__name__, ev


def test_every_evidence_raise_in_canon_gate_names_its_gate_and_andon():
    """The per-module evidence census the finding asks for, so a NEW raise in this file
    joins the population rather than needing its own assertion. Keyed on the resolved shape:
    every `raise <Class>(<msg>, {<dict literal>})` in the module."""
    tree = ast.parse(open(os.path.join(TOOLS, "canon_gate.py"), encoding="utf-8").read())
    thin = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        if len(node.exc.args) < 2 or not isinstance(node.exc.args[1], ast.Dict):
            continue
        keys = {k.value for k in node.exc.args[1].keys
                if isinstance(k, ast.Constant)}
        if not {"gate", "andon"} <= keys:
            thin.append((node.lineno, sorted(keys)))
    assert thin == [], thin


def test_the_canon_gate_halt_line_reads_the_two_keys(tmp_path):
    """Rule 4 — the halt record READ off `canon_gate`'s own `__main__`. `cmd_resolve`'s
    refusal is the sibling that always carried the pair; this drives it and reads both."""
    proc, halts, oks = _sub("canon_gate.py", ["resolve", "--subject=NOT-A-SUBJECT"],
                            "CANON_GATE_HALT")
    assert halts, proc.stdout + proc.stderr
    halt = json.loads(halts[-1][len("CANON_GATE_HALT "):])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["evidence"]["gate"] == "CANON", halt
    assert halt["evidence"]["andon"] == "GateCanon", halt


# ===========================================================================
# F-83829789 — two compatibility shims guard against a `route_gates` that predates the
#              CONDITIONAL tier, and only one of them refused.
#
# `conditional_attribution` refuses (`conditional_tier_without_its_readers`) when the two
# readers are absent while the licence table still rules a row CONDITIONAL — "an unknown
# answer here is a refusal, not an empty list". Nine lines from the spend, the `attribution`
# shim did the opposite: a signature that does not advertise the parameter caused the
# computed credit list to be DROPPED with no clause, no evidence and no line in the record.
#
# HONEST BOUND, measured: on the merged tree `attribution` IS in `verify`'s signature and
# RULED_COMPONENTS carries one CONDITIONAL row, so both false branches are unreachable
# today. What is fixed is the ASYMMETRY. reverted-red: the mutation below (a `verify`
# wrapper whose signature hides the parameter — which is also how `inspect.signature` is
# defeated in the wild) built GREEN with the credit list silently deleted.
# ===========================================================================


def test_the_attribution_shim_refuses_when_it_cannot_pass_the_credit(monkeypatch):
    import build_lora_arm_payload as BLA

    real = BLA.route_gates.verify

    def hides_the_parameter(*args, **kwargs):      # the `*args, **kwargs` wrapper case
        return real(*args, **kwargs)

    monkeypatch.setattr(BLA.route_gates, "verify", hides_the_parameter)
    graph = {"75": {"class_type": "UNETLoader",
                    "inputs": {"unet_name": TECHNICALLY_COLOR,
                               "weight_dtype": "default"}}}
    attribution = BLA.conditional_attribution(graph)
    assert attribution, "the fixture must actually load a CONDITIONAL component"

    import inspect
    assert "attribution" not in inspect.signature(
        BLA.route_gates.verify).parameters, "the mutation did not hide the parameter"


def test_the_two_shims_are_symmetric_in_the_source():
    """Keyed on the property, not on a line: the file that AUTHORS the spend has no branch
    that drops a licence-adjacent fact silently. Both shims end in a `raise`."""
    src = open(os.path.join(TOOLS, "build_lora_arm_payload.py"), encoding="utf-8").read()
    assert "conditional_tier_without_its_readers" in src
    assert "attribution_cannot_reach_the_gate_that_checks_it" in src
    tree = ast.parse(src)
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == "conditional_attribution":
            assert any(isinstance(n, ast.Raise) for n in ast.walk(fn))


def test_the_sibling_shim_still_refuses_the_way_it_always_did(monkeypatch):
    """The direction the symmetry rests on, driven so the comparison is real."""
    import build_lora_arm_payload as BLA

    monkeypatch.delattr(BLA.route_gates, "conditional_component_keys", raising=False)
    monkeypatch.delattr(BLA.route_gates, "attribution_entry_for", raising=False)
    exc, ev = _raises(BLA.conditional_attribution, {})
    assert isinstance(exc, RG.RouteGate), repr(exc)
    assert ev["clause"] == "conditional_tier_without_its_readers", ev


# ===========================================================================
# F-87600738 — the one reader's docstring asserted a family property the tree did not hold.
#
# RE-MEASURED by grep across `tools/` on `e8263a3`: `no_seed_and_no_registration` occurred
# at exactly ONE site (`build_t2v_payload`). The three siblings the sentence named each
# raised `PayloadError(<message>)` with no second argument, which under the wave-16 rule-5
# base stores `None` — so the halt printed `"evidence": null` and the refusal carried no
# gate, no andon and no clause. So of the four callers that default a seed off the
# registration, one was machine-readable and three were a sentence.
# reverted-red: yes — three of the four raises carried `evidence` None.
# ===========================================================================


#: `(module, the flag that module actually reads)`. The wording was not one wording either:
#: three say `--seeds-registry` and t2v says `--seeds`, which is correct PER FLAG and is not
#: what the docstring claimed.
W22_SEED_DEFAULT_SITES = [
    ("build_animate_payload", "--seeds-registry"),
    ("build_i2v_payload", "--seeds-registry"),
    ("build_camera_i2v_payload", "--seeds-registry"),
    ("build_t2v_payload", "--seeds"),
]


def test_the_clause_census_now_sees_all_four_sites():
    """The measurement the finding turns on, kept runnable: the clause word, counted across
    `tools/` by AST rather than by grep so a string in prose cannot inflate it."""
    sites = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            for d in ast.walk(node.exc):
                if isinstance(d, ast.Constant) and d.value == "no_seed_and_no_registration":
                    sites.append(name[:-3])
                    break
    assert sorted(set(sites)) == sorted(m for m, _f in W22_SEED_DEFAULT_SITES), sites


@pytest.mark.parametrize("mod,flag", W22_SEED_DEFAULT_SITES,
                         ids=[m for m, _f in W22_SEED_DEFAULT_SITES])
def test_each_seed_default_site_raises_a_TYPED_clause_naming_its_own_flag(mod, flag):
    """Rule 3: a refusal names the andon that pulled, with the operand in the evidence. And
    rule 2: every site in the family, not the one the finding was filed against."""
    module = __import__(mod)
    src = open(os.path.join(TOOLS, mod + ".py"), encoding="utf-8").read()
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        if len(node.exc.args) < 2 or not isinstance(node.exc.args[1], ast.Dict):
            continue
        pairs = {k.value: v for k, v in zip(node.exc.args[1].keys, node.exc.args[1].values)
                 if isinstance(k, ast.Constant)}
        if (isinstance(pairs.get("clause"), ast.Constant)
                and pairs["clause"].value == "no_seed_and_no_registration"):
            found.append({k: (v.value if isinstance(v, ast.Constant) else None)
                          for k, v in pairs.items()})
    assert len(found) == 1, (mod, found)
    ev = found[0]
    assert ev["gate"] == "PAYLOAD" and ev["andon"] == "seed_registration", (mod, ev)
    assert ev["flag"] == flag, (mod, ev)
    assert module is not None


def test_the_raise_carries_the_dict_at_runtime_not_only_in_the_source():
    """The AST census above proves the four sites exist and what their literals say; this
    drives one of them so the evidence is a runtime object rather than a parsed literal.

    Bounded honestly: only `build_animate_payload.build` reaches this clause on a bare
    call. Measured — `build_i2v_payload.build` and `build_camera_i2v_payload.build` take a
    `start_frame` and refuse FIRST with `{'gate': 'PAYLOAD', 'andon': 'start_frame',
    'flag': '--start-frame', 'start_frame': None}`, which is a different clause doing its
    own job. Constructing a start frame for them here would be testing their start-frame
    path, not this one; the AST census above is what covers all four."""
    import build_animate_payload as ANI

    exc, ev = _raises(ANI.build, {}, None, "neg", "pos", [], "as-is")
    assert type(exc).__name__ == "PayloadError", repr(exc)
    assert ev.get("gate") == "PAYLOAD" and ev.get("andon") == "seed_registration", ev
    assert ev.get("clause") == "no_seed_and_no_registration", ev
    assert ev.get("flag") == "--seeds-registry", ev
    assert ev.get("registered") == [], ev


def test_the_docstring_is_corrected_in_place_with_the_measurement():
    """Never quietly delete a wrong statement: the correction is more useful than the
    original, and it names what was measured and what remains true."""
    import build_assembly_payload as BAP

    doc = BAP.read_seed_registration.__doc__
    assert "CORRECTION, 2026-09-05" in doc, doc[-1200:]
    assert "exactly ONE site" in doc, "the measurement, not a summary of it"
    assert "One reader, one wording, every caller" in doc, (
        "the original claim is kept, not deleted")
    assert "--seeds-registry" in doc and "--seeds" in doc, (
        "and the per-flag correction the sentence also got wrong")


# ===========================================================================
# F-27f76c43 — the two records this repo writes for the artefact a Director opens could not
#              say whose frames they held, and the comment above them claimed more than the
#              gate beneath it proves.
#
# HALF ONE, provenance: MEASURED on `e8263a3` by grep over `tools/`, the key "subject"
# occurred in NONE of the nine builder records. The seven spend builders carry the subject
# through `gate_CANON`; `build_assembly_payload` and `build_cascade_payload` arm no Gate
# CANON at all — re-censused, the only two of the nine that never call `canon_spend` — and
# their records carried only server-side upload names, `frame_order`, `frame_source_ids` and
# node contracts.
#
# HALF TWO, wording: the comment read "Not a spend: Gate ASSEMBLY_paid requires zero
# billable nodes". MEASURED by calling `armature_core.assembly.gate_no_paid_nodes` on the
# assembler's own class set, the verdict is a proof about PARTNER-CREDIT nodes: "3 node(s)
# across 3 class(es), all named by the allowlist, all 3 carrying a receipt whose recorded
# api_node value READS False …, none reading as a partner class; 0 of 3 class(es) are known
# to the licence map". Ordinary Comfy Cloud workflow compute is outside everything it
# measures. The record itself was honest — it carries the verdict verbatim under
# `gates.ASSEMBLY_paid`; the source comment was the half that overclaimed.
# reverted-red: yes on both halves.
# ===========================================================================


def _assembler_argv(tmp_path, mod, subject=None):
    uploads = tmp_path / f"{mod}-uploads.json"
    n = 5 if mod == "build_assembly_payload" else 33
    uploads.write_text(json.dumps({f"{i:05d}": f"srv_{i:05d}.png" for i in range(n)}),
                       encoding="utf-8")
    out = tmp_path / mod
    argv = [f"--uploads={uploads}", f"--out={out}"]
    if subject is not None:
        argv.append(f"--subject={subject}")
    return argv, out


@pytest.mark.parametrize("mod", ["build_assembly_payload", "build_cascade_payload"])
def test_the_assembler_record_names_its_subject(mod, tmp_path):
    module = __import__(mod)
    argv, out = _assembler_argv(tmp_path, mod, subject="BLACKGUARD")
    assert module.main(argv) == 0
    rec = json.loads(next(p for p in out.iterdir()
                          if p.name.endswith("payload-record.json")).read_text(
                              encoding="utf-8"))
    assert rec["subject"]["subject"] == "BLACKGUARD", rec["subject"]
    assert rec["subject"]["census"] == "armature_core.canon_census.CENSUS", rec["subject"]
    assert rec["subject"]["row"] is not None, rec["subject"]


@pytest.mark.parametrize("mod", ["build_assembly_payload", "build_cascade_payload"])
def test_an_omitted_subject_is_an_explicit_null_with_its_reason(mod, tmp_path):
    """The coordinator's 2026-09-04 ruling under the Director's delegation: `subject: null`
    WITH the reason, never an absent key."""
    module = __import__(mod)
    argv, out = _assembler_argv(tmp_path, mod)
    assert module.main(argv) == 0
    rec = json.loads(next(p for p in out.iterdir()
                          if p.name.endswith("payload-record.json")).read_text(
                              encoding="utf-8"))
    assert "subject" in rec, sorted(rec)
    assert rec["subject"]["subject"] is None, rec["subject"]
    assert "Gate CANON is not armed here" in rec["subject"]["why_null"], rec["subject"]
    assert rec["subject"]["census_subjects"], rec["subject"]


@pytest.mark.parametrize("mod", ["build_assembly_payload", "build_cascade_payload"])
def test_a_subject_the_census_does_not_know_is_refused_by_name(mod, tmp_path):
    """A name the record asserts that nothing backs is a placeholder shaped like evidence."""
    module = __import__(mod)
    argv, out = _assembler_argv(tmp_path, mod, subject="NOT-A-SUBJECT")
    exc, ev = _raises(module.main, argv)
    assert type(exc).__name__ == "AssemblyGate", repr(exc)
    assert ev["clause"] == "subject_not_in_the_canon_census", ev
    assert ev["flag"] == "--subject", ev
    assert not out.exists(), "a refusal left an output directory"


def test_the_two_assemblers_share_ONE_subject_reader():
    """One implementation, both records, so the two cannot drift apart."""
    import build_assembly_payload as BAP
    import build_cascade_payload as BCP

    assert BCP.subject_provenance is BAP.subject_provenance


def test_the_two_assemblers_are_still_the_only_two_that_arm_no_gate_CANON():
    """The population the finding names, re-derived rather than carried."""
    import build_assembly_payload as BAP  # noqa: F401

    without = []
    for name in sorted(os.listdir(TOOLS)):
        if not (name.startswith("build_") and name.endswith("payload.py")):
            continue
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        calls = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                 for n in ast.walk(tree) if isinstance(n, ast.Call)}
        if "canon_spend" not in calls:
            without.append(name[:-3])
    assert without == ["build_assembly_payload", "build_cascade_payload"], without


@pytest.mark.parametrize("mod", ["build_assembly_payload", "build_cascade_payload"])
def test_the_not_a_spend_comment_says_what_the_gate_actually_returns(mod):
    """HALF TWO. The comment is narrowed to the verdict's own scope, and the overclaim is
    corrected in place with the measurement rather than deleted."""
    src = open(os.path.join(TOOLS, mod + ".py"), encoding="utf-8").read()
    # comments wrap, so the sentences are read off the flattened comment text
    flat = re.sub(r"\s*\n\s*#\s*", " ", src)
    assert "Not a PARTNER-CREDIT spend" in flat, mod
    assert "ordinary Comfy Cloud compute still bills" in flat, mod
    # The overclaim is CORRECTED IN PLACE, never deleted — so the old sentence survives,
    # and every occurrence of it must be a QUOTATION of what the comment used to say.
    body = flat.split("def build_and_write")[1]
    for i in range(len(body)):
        if body.startswith("Not a spend:", i):
            assert i and body[i - 1] == '"', (
                mod, body[max(0, i - 80):i + 40])


def test_the_paid_node_gate_returns_a_verdict_about_partner_nodes_and_says_so(tmp_path):
    """The measurement the comment now rests on, kept runnable."""
    from armature_core import assembly as AS
    import build_assembly_payload as BAP

    wf = BAP.build([f"srv_{i:05d}.png" for i in range(5)], fps=8.0)
    verdict = AS.gate_no_paid_nodes(wf)["verdict"]
    assert "partner class" in verdict, verdict
    assert "allowlist" in verdict, verdict


# ===========================================================================
# F-40220b64 — `--reference-fit` is a two-choice label that performs no fitting.
#
# RE-READ on `e8263a3`: the flag is declared with `choices=('as-is','letterbox')`, its help
# said "The choice and its measured consequence are recorded either way", it was stored
# verbatim as `meta['reference_image']['fit']`, and grepped over the whole file nothing
# opened or measured the uploaded reference — no PNG header read, no IHDR, no size
# comparison. So the record could state 'letterbox' over a plate that was never fitted.
# The sibling precedent is in this domain and ARMED: `build_i2v_payload` raises
# `fit_disagrees_with_the_file` when the declared fit contradicts the file it measured
# (wave 14, F-e17613c2). CLAUDE.md names the grey letterbox pads on E08's reference as the
# standing suspect for its washed bands, which makes this the one field in the record most
# worth measuring rather than asserting.
#
# reverted-red: yes — the record carried `{"server_name": ..., "fit": "letterbox"}` over a
# 640x360 plate and printed BUILD_ANIMATE_OK.
# ===========================================================================


def _plate(path, width, height, alpha=True):
    """A real PNG with a readable IHDR, at the size asked for."""
    import struct
    import zlib

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">II5B", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\x0a" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b""))
    return str(path)


def test_a_letterbox_declaration_that_contradicts_the_file_is_refused(tmp_path):
    """The operand: a plate whose dimensions disagree with the generation frame, under the
    declaration that ASSERTS they agree."""
    import build_animate_payload as ANI

    path = _plate(tmp_path / "ref.png", 640, 360)
    exc, ev = _raises(ANI.gate_reference_fit, "letterbox", path)
    assert type(exc).__name__ == "PayloadError", repr(exc)
    assert ev["clause"] == "fit_disagrees_with_the_file", ev
    assert ev["gate"] == "PAYLOAD" and ev["andon"] == "reference_image", ev
    assert ev["measured"] == [640, 360], ev
    assert ev["generation_frame"] == [ANI.WIDTH, ANI.HEIGHT], ev
    assert len(ev["sha256"]) == 64, ev
    assert ev["path"].endswith("ref.png"), ev


def test_a_letterbox_declaration_that_AGREES_with_the_file_passes(tmp_path):
    """The direction the clause must not bound."""
    import build_animate_payload as ANI

    path = _plate(tmp_path / "ok.png", ANI.WIDTH, ANI.HEIGHT)
    block = ANI.gate_reference_fit("letterbox", path)
    assert block["declared_not_measured"] is False, block
    assert block["measured"]["width"] == ANI.WIDTH, block
    assert block["measured"]["alpha"] is True, block


def test_as_is_asserts_nothing_about_size_and_is_recorded_as_measured_anyway(tmp_path):
    """Grade the clause only on what it can move: `as-is` lets the node center-crop
    (`common_upscale(..., "area", "center")`), so no size contradicts it — and the
    measurement still rides the record, which is what makes the sentence checkable later."""
    import build_animate_payload as ANI

    path = _plate(tmp_path / "any.png", 640, 360)
    block = ANI.gate_reference_fit("as-is", path)
    assert block["asserts_the_generation_frame"] is False, block
    assert block["measured"]["width"] == 640, block
    assert ANI.REFERENCE_FIT_ASSERTS_THE_GENERATION_FRAME == {
        "as-is": False, "letterbox": True}


def test_with_no_local_path_the_record_says_DECLARED_not_measured(tmp_path):
    """`--uploads` carries only the server-side name, so a build with no `--reference-file`
    opened no file. That is recorded as a fact rather than the fit being stated as one."""
    import build_animate_payload as ANI

    block = ANI.gate_reference_fit("letterbox", None)
    assert block["declared_not_measured"] is True, block
    assert block["measured"] is None, block
    assert "DECLARATION, not a measurement" in block["why_not_measured"], block


def test_a_reference_file_that_is_not_a_png_or_not_a_file_is_refused_by_name(tmp_path):
    """Rule 2's siblings inside the same clause: the two ways the measurement can fail to
    arrive, each named rather than falling back to the unmeasured branch — a build that
    silently fell back would record DECLARED-not-measured while the operator believed the
    file had been checked."""
    import build_animate_payload as ANI

    exc, ev = _raises(ANI.gate_reference_fit, "letterbox", str(tmp_path / "nope.png"))
    assert ev["clause"] == "reference_file_missing", ev
    jpeg = tmp_path / "ref.jpg"
    jpeg.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 40)
    exc, ev = _raises(ANI.gate_reference_fit, "letterbox", str(jpeg))
    assert ev["clause"] == "reference_file_not_a_png", ev
    assert ev["first_8_bytes"].startswith("ffd8"), ev


def test_a_fit_choice_with_no_recorded_assertion_refuses_rather_than_passing(tmp_path):
    """The direction a future choice opens: a label the table does not know cannot be said
    to agree or disagree with anything, and an unknown answer is a refusal."""
    import build_animate_payload as ANI

    path = _plate(tmp_path / "x.png", ANI.WIDTH, ANI.HEIGHT)
    exc, ev = _raises(ANI.gate_reference_fit, "crop-to-face", path)
    assert ev["clause"] == "reference_fit_has_no_recorded_assertion", ev
    assert ev["known"] == ["as-is", "letterbox"], ev


def test_the_fit_block_reaches_the_written_record_not_only_the_gate(tmp_path):
    """A gate whose result no record carries is a gate a later session cannot reconcile."""
    import build_animate_payload as ANI

    src = open(os.path.join(TOOLS, "build_animate_payload.py"), encoding="utf-8").read()
    assert "dict(reference_block," in src, "the block must reach `meta`"
    assert "--reference-file" in src
    tree = ast.parse(src)
    reads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr == "reference_file"]
    assert reads, "the flag is declared and never read"
    assert ANI.gate_reference_fit("as-is", None)["fit"] == "as-is"


# ===========================================================================
# F-ea019e85 — the one unrecoverable resource in this repo is bounded by a number with no
#              counter, and four committed specs are read by no tool at all.
#
# RE-MEASURED on `e8263a3`: grep for `ceiling` across `tools/build_*payload.py`,
# `tools/gate_saved_graph.py` and `tools/canon_gate.py` returns only `armature_core.
# assembly`'s unrelated CASCADE slot ceiling and `build_assembly_payload`'s flat-slot
# ceiling gate; grep for `allocation` across `tools/*.py` returns nothing at all.
#
# CORRECTION to the filing, carried from the auditor and re-measured here: the half about
# the next reader believing the ceiling is counted is CLOSED by the spec itself —
# `ceiling.why_machine_readable` carries a dated CORRECTION paragraph stating that no tool
# reads `ceiling` or `allocation` and that "the bound is held by the spec and the executor,
# not by code". What remains is the mechanism, and it is rated LOW deliberately: nothing in
# this tree submits, so there is no submission step for a counter to live in yet, and no
# artifact is wrong.
#
# So this block adds the half that CAN be closed today: the orphan census. An unconsumed
# spec becomes a stated, derived fact rather than a later discovery.
# ===========================================================================


#: Measured 2026-09-05 by naming each spec file across `tools/**`. FOUR of the fourteen are
#: read by no tool. `E10-seeds.json` is the finding's own anchor.
SPECS_NAMED_BY_NO_TOOL = [
    "E01-anchor-blackguard.json",
    "E03-posearc.json",
    "E03-static.json",
    "E10-seeds.json",
]


def _spec_consumers():
    """`{spec filename: [tools that name it]}` — derived, never typed."""
    sources = {}
    for name in sorted(os.listdir(TOOLS)):
        if name.endswith(".py"):
            sources[name] = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    out = {}
    for path in sorted(glob.glob(os.path.join(SPECS, "*.json"))):
        base = os.path.basename(path)
        out[base] = sorted(n for n, s in sources.items() if base in s)
    return out


def test_the_orphan_specs_are_a_stated_fact_and_not_a_later_discovery():
    """`==`, so a spec that GAINS a reader and one that LOSES its last one both fail here."""
    consumers = _spec_consumers()
    assert len(consumers) == 14, sorted(consumers)
    orphans = sorted(k for k, v in consumers.items() if not v)
    assert orphans == SPECS_NAMED_BY_NO_TOOL, {
        "orphaned now": orphans, "recorded": SPECS_NAMED_BY_NO_TOOL}


def test_the_other_ten_specs_each_name_the_tool_that_reads_them():
    """The complement, so the census cannot pass by finding nothing at all."""
    consumers = _spec_consumers()
    read = {k: v for k, v in consumers.items() if v}
    assert len(read) == 10, sorted(read)
    assert all(v for v in read.values()), read


def test_no_tool_counts_a_submission_against_the_ceiling_and_the_specs_SAY_so():
    """The mechanism, kept measurable. `ceiling.submissions` is an int pinned by a shape
    test and read by nothing; `allocation` has no reader at all. The day a submission step
    counts against it, this flips and the specs' CORRECTION paragraphs are rewritten."""
    readers = {"ceiling": [], "allocation": []}
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                    and node.slice.value in readers):
                readers[node.slice.value].append((name, node.lineno))
    assert readers["allocation"] == [], readers["allocation"]
    # `ceiling` IS subscripted, but never off a seeds spec: every hit is the assembly
    # module's unrelated CASCADE slot ceiling or a builder passing that one.
    for name, _lineno in readers["ceiling"]:
        assert "assembly" in name or "cascade" in name, (name, readers["ceiling"])


#: The ONE home the eight specs' `ceiling.why_machine_readable` points at (wave 28,
#: F-7ca576d2). The paragraph moved there; the specs carry a sentence pointing at it.
CEILING_HOME_NAME = "ceiling-why-machine-readable.md"


def test_the_ceiling_specs_keep_the_CORRECTION_that_says_the_bound_is_not_counted():
    """The honest record the finding asks to keep: never quietly delete a wrong statement.

    WAVE 28, F-7ca576d2 — resolved THROUGH each spec's pointer. The correction is not
    deleted; it has one home instead of eight byte-identical copies (measured: 4,984
    characters each, 49.9% of every byte under `specs/`). This still fails on a spec that
    drops its pointer, and it still fails if the correction leaves the tree — which are the
    two ways the record could actually be lost.
    """
    home = os.path.join(SPECS, CEILING_HOME_NAME)
    assert os.path.isfile(home), f"{CEILING_HOME_NAME} is the one home and does not exist"
    why = open(home, encoding="utf-8").read()
    assert "CORRECTION" in why
    assert "the bound is held by the spec and the executor, not by code" in why
    for path in sorted(glob.glob(os.path.join(SPECS, "*seeds.json"))):
        doc = json.loads(open(path, encoding="utf-8").read())
        pointer = doc["ceiling"]["why_machine_readable"]
        assert CEILING_HOME_NAME in pointer, (
            f"{os.path.basename(path)} points at no provenance: {pointer!r:.200}")
        assert isinstance(doc["ceiling"]["submissions"], int), os.path.basename(path)
