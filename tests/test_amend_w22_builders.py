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
