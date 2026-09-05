"""Wave 25, builders — Stage B amend #3. Seven approved findings, none deferred.

Each block names the finding, the OPERAND the wave-24 auditor measured on `580af47`, the
siblings enumerated beside it, and the halt line READ back out of the tool's own
`__main__`. Every fix here was run once with the fix reverted; the `reverted-red` note in
each block records what the reverted tree did.

The rules this wave carries, on top of wave 18's five and wave 22's one: a halt-line or
clause fix cites the census that holds it, and a fix that would be a second spelling of
anything with ONE home is "adopt the home".
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import route_gates as RG

import gate_saved_graph as GSG

from test_amend_w14_builders import ASSEMBLY_API, ASSEMBLY_SAVED, _write, _builder_record

REPO = os.path.dirname(TOOLS)


def _assembly_cli(tmp_path, api=None, saved=None, record=True, extra=()):
    """The green assembly invocation — the one wave 14 drives to `SAVED_ADMISSION_OK`."""
    api_p = _write(tmp_path, "in/g.api.json", api if api is not None else ASSEMBLY_API)
    saved_p = _write(tmp_path, "in/g.saved.json",
                     saved if saved is not None else ASSEMBLY_SAVED)
    seeds_p = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    argv = [f"--saved={saved_p}", f"--api={api_p}", f"--seeds={seeds_p}",
            f"--out={tmp_path / 'out' / 'admission.json'}", "--frame=832,480,81"]
    if record:
        rec = _write(tmp_path, "in/payload-record.json", _builder_record(
            ASSEMBLY_API, family="wan", carries_no_sampler=True, frame=(832, 480, 81)))
        argv.append(f"--record={rec}")
    return argv + list(extra)


def _drive(tool, argv, sentinel):
    """Run a tool's own `__main__` as a REAL subprocess and read its printed lines."""
    proc = subprocess.run([sys.executable, os.path.join(TOOLS, tool), *argv],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=REPO)
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith(sentinel + "_HALT ")]
    oks = [ln for ln in proc.stdout.splitlines() if ln.startswith(sentinel + "_OK ")]
    halt = json.loads(halts[-1][len(sentinel) + 6:]) if halts else None
    return proc, halt, oks


def _gsg(tmp_path, **kw):
    return _drive("gate_saved_graph.py", _assembly_cli(tmp_path, **kw), "SAVED_ADMISSION")


# ===========================================================================
# F-e62bdc2b (panel CRITICAL) — the two headline refusals carry the identity
#              triple every reader in this tree branches on.
#
# `gate_saved_graph` exists to raise two sentences: "the saved file is not the graph this
# repo built" (`round_trip`) and "the saved file's topology is not the topology this repo
# built" (`link_round_trip`). Both raised `RG.RouteGate` with a bare two-key evidence
# literal, as did `link_table`'s two entry clauses — so the halt at the spend boundary
# named `[ROUTE]` in its message, `SAVED_ADMISSION` in its sentinel, and carried NO `gate`,
# NO `andon` and NO `clause`. That is the two-ids-for-one-event ambiguity wave 18's
# `SavedAdmission` class was written to end, re-created by omission.
#
# MEASURED on `580af47` as a real subprocess on the green assembly fixture with node 20's
# `fps` changed in the saved file only:
#   exit 2, SAVED_ADMISSION_HALT {"error": "RouteGate",
#     "message": "[ROUTE] the saved file is not the graph this repo built: node 20.fps:
#      built 8, saved 16", "evidence": {"checked": [...], "problems": [...]}}
#
# THE CENSUS THAT HOLDS IT (wave 24, F-d30bb5fb; instruments-measure's SEAM 1):
# `tests/test_gates.evidence_dicts_missing(key, root=TOOLS_DIR)` names
# `gate_saved_graph.py:round_trip`, `:link_table` and `:link_round_trip` under all three
# readings. Re-derived branch-local on `580af47`: `gate` 75 offenders tools-wide (9 in this
# domain), `andon` 118 (15), `clause` 119 (19).
#
# SIBLINGS ENUMERATED — every raise in the three functions:
#   round_trip        : the `_api_nodes` / `_as_*_graph` member clauses (wave 22,
#                       `unreadable_node`, all three keys) + THIS one -> fixed
#   link_table        : `duplicate_link_id` (all three keys) + the two entry clauses -> fixed
#   link_round_trip   : `duplicate_socket_name` (all three keys) + THIS one -> fixed
# So four of the seven raises across the three functions were the offenders; the other
# three already carried the triple, which is what made the contrast sit inside one body.

#: `(id, mutation, clause)`. One operand per refusal, each exercising a DIFFERENT one of
#: the four raises — rule 2's sibling proof, driven through the CLI.
W25_SAVED_ADMISSION_OPERANDS = []


def _saved_with_changed_widget():
    """Node 20's `fps` widget changed in the SAVED file only — `round_trip`'s operand."""
    doc = json.loads(json.dumps(ASSEMBLY_SAVED))
    for node in doc["nodes"]:
        if node["id"] == 20:
            node["widgets_values"] = [16, 8]
    return doc


def _saved_with_unreadable_link_entry():
    doc = json.loads(json.dumps(ASSEMBLY_SAVED))
    doc["links"].append("this is not a link table entry")
    return doc


def _saved_with_originless_link_entry():
    doc = json.loads(json.dumps(ASSEMBLY_SAVED))
    doc["links"].append([9, None, 0, 10, 0, "IMAGE"])
    return doc


def _saved_with_crossed_links():
    """Links 1 and 2 swap origins — the topology is not the topology we wired."""
    doc = json.loads(json.dumps(ASSEMBLY_SAVED))
    doc["links"] = [[1, 2, 0, 10, 0, "IMAGE"], [2, 1, 0, 10, 1, "IMAGE"],
                    [3, 10, 0, 20, 0, "IMAGE"], [4, 20, 0, 30, 0, "VIDEO"]]
    return doc


W25_SAVED_ADMISSION_OPERANDS = [
    ("a widget value changed in the saved file", _saved_with_changed_widget,
     "saved_values_are_not_the_built_values"),
    ("a link table entry this tool cannot read", _saved_with_unreadable_link_entry,
     "unreadable_link_table_entry"),
    ("a link table entry naming no origin", _saved_with_originless_link_entry,
     "link_table_entry_names_no_origin"),
    ("two conditioning links crossed", _saved_with_crossed_links,
     "saved_topology_is_not_the_built_topology"),
]


@pytest.mark.parametrize("name,mutate,clause", W25_SAVED_ADMISSION_OPERANDS,
                         ids=[r[0] for r in W25_SAVED_ADMISSION_OPERANDS])
def test_the_headline_refusals_name_their_gate_andon_and_clause(name, mutate, clause,
                                                                tmp_path):
    """F-e62bdc2b · rule 4: the halt line READ, one operand per raise.

    reverted-red: yes. On `580af47` each of these four prints
    `{"error": "RouteGate", "message": "[ROUTE] ...", "evidence": {<two or three keys>}}`
    — `evidence['gate']`, `['andon']` and `['clause']` all `KeyError`.
    """
    proc, halt, oks = _gsg(tmp_path, saved=mutate())
    assert halt is not None, proc.stdout + proc.stderr
    assert proc.returncode == 2, (proc.returncode, halt)
    assert oks == [], oks
    assert halt["error"] == "SavedAdmission", halt
    assert halt["message"].startswith("[SAVED_ADMISSION]"), halt["message"][:120]
    ev = halt["evidence"]
    assert ev["gate"] == "SAVED_ADMISSION", ev
    assert ev["andon"] == "SavedAdmission", ev
    assert ev["clause"] == clause, ev
    assert not (tmp_path / "out").exists(), "a refusal left an out directory"


@pytest.mark.parametrize("name,mutate,clause", W25_SAVED_ADMISSION_OPERANDS,
                         ids=[r[0] for r in W25_SAVED_ADMISSION_OPERANDS])
def test_the_four_refusals_keep_the_operand_they_always_carried(name, mutate, clause):
    """The evidence the two-key literal DID carry is still there beside the triple: a
    reader that opened `problems` / `checked` / `wired` / `entry` before still finds it."""
    api, saved = ASSEMBLY_API, mutate()
    with pytest.raises(RG.RouteGate) as caught:      # still a RouteGate for every catcher
        GSG.round_trip(api, saved)
        GSG.link_round_trip(api, saved)
    ev = caught.value.evidence
    assert isinstance(caught.value, GSG.SavedAdmission), type(caught.value).__name__
    assert ev["clause"] == clause, ev
    assert ({"checked", "problems"} <= set(ev) or {"wired", "empty_in_both"} <= set(ev)
            or {"entry", "n_entries"} <= set(ev)), sorted(ev)


def test_the_unmutated_fixture_still_reaches_admission_the_direction_not_bounded(tmp_path):
    """The direction the invariant does not bound: a check that refuses everything is not a
    check. The same fixture the wave-14 admission test drives still prints
    `SAVED_ADMISSION_OK` at exit 0, and the four clauses above never fire on it."""
    proc, halt, oks = _gsg(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert halt is None and len(oks) == 1, (halt, oks)
    printed = json.loads(oks[0][len("SAVED_ADMISSION_OK "):])
    assert printed["round_trip_values_compared"] >= 1, printed
    assert printed["links_compared"] == 4, printed


# ===========================================================================
# F-af838b99 (panel CRITICAL) — the ONE halt handler, adopted in all thirteen
#
# The nine builders, both fetchers, `canon_gate` and the LAST gate before a paid
# submission each printed their halt line through a LOCAL three-key handler
# (`json.dumps({error, message, evidence}, default=str)`), while wave 22 built exactly one
# home for the job — `armature_core.parts.run_tool_main` + `halt_keysafe` + `halt_outcome`.
# Thirteen byte-alike copies outside every property that home carries.
#
# MEASURED on `580af47` as a real subprocess on the green assembly fixture with a `NaN` in
# one saved widget value:
#   SAVED_ADMISSION_HALT {"error": "RouteGate", ..., "evidence": {"checked":
#     [{..., "saved": NaN, ...}]}}
# `json.loads` accepts that line; `json.loads(payload, parse_constant=<raise>)` refuses it
# with "bare NaN" — which is what JS `JSON.parse`, Go `encoding/json` and serde do. The
# `__main__` block of every one of the thirteen tells wrappers to key on its sentinel line,
# so the line is documented as a machine contract.
#
# THE CENSUS THAT HOLDS IT: `tests/test_instrument_exits.py` — `CPYTHON_WITH_HANDLER` (the
# population, unchanged at 25: these thirteen already HAD handlers, they were the wrong
# ones) and `test_the_one_handlers_adopters_are_derived_and_carry_the_six_key_record`,
# whose adopter list moves 8 -> 21 in this commit. The non-finite property was held for the
# Blender population alone (`test_stage_render_writes_a_non_finite_operand_as_strict_json`);
# widening that census over `CPYTHON_WITH_HANDLER` is the tests domain's, wave 26 — cited,
# not re-derived here.
#
# LATENT rather than measured, and stated as such: `halt_keysafe`'s stringified mapping
# keys and its `<circular>` marker close two more escapes (`json.dumps(default=str)`
# applies `default` to VALUES only, so a tuple or numpy evidence KEY raises inside the
# handler and `sys.exit` never runs — 21 of 21 Blender handlers escaped that way before
# wave 22). No reachable non-str evidence key was found in this domain on `580af47`.

#: The thirteen and the prefix each keeps. The prefix is NOT the module stem for eleven of
#: them, which is why `blender_stub.halt_handler` reads it off the block.
W25_ADOPTERS = [
    ("build_animate_payload.py", "BUILD_ANIMATE"),
    ("build_assembly_payload.py", "BUILD_ASSEMBLY"),
    ("build_camera_i2v_payload.py", "BUILD_CAMERA_I2V"),
    ("build_cascade_payload.py", "BUILD_CASCADE"),
    ("build_i2v_payload.py", "BUILD_I2V"),
    ("build_lora_arm_payload.py", "BUILD_LORA_ARM"),
    ("build_payload.py", "BUILD_PAYLOAD"),
    ("build_r2v_payload.py", "BUILD_R2V"),
    ("build_t2v_payload.py", "BUILD_T2V"),
    ("canon_gate.py", "CANON_GATE"),
    ("fetch_run.py", "FETCH_RUN"),
    ("fetch_t2v_run.py", "FETCH_T2V"),
    ("gate_saved_graph.py", "SAVED_ADMISSION"),
]


@pytest.mark.parametrize("filename,prefix", W25_ADOPTERS, ids=[r[0] for r in W25_ADOPTERS])
def test_every_tool_in_this_domain_prints_through_the_one_handler(filename, prefix):
    """F-af838b99 · the adoption is READ off the tree, never asserted in prose.

    reverted-red: yes — on `580af47` every one of the thirteen carries its own
    `print(PREFIX + "_HALT " + json.dumps(...))` and `run_tool_main` appears in none of
    them.
    """
    import ast

    src = open(os.path.join(TOOLS, filename), encoding="utf-8").read()
    tree = ast.parse(src)
    block = [n for n in tree.body
             if isinstance(n, ast.If) and "__main__" in ast.dump(n.test)]
    assert len(block) == 1, filename
    calls = [n for n in ast.walk(block[0])
             if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "run_tool_main"]
    assert len(calls) == 1, (filename, ast.dump(block[0])[:400])
    assert [a.value for a in calls[0].args[1:2]] == [prefix], filename
    assert calls[0].args[0].id == "main", filename
    # and no second spelling left behind: nothing in the block builds its own record.
    # Read off the AST rather than off the raw text, because `gate_saved_graph.py`'s block
    # QUOTES the deleted handler in the comment that records what it cost.
    assert not [n for n in ast.walk(block[0])
                if isinstance(n, ast.Call)
                and getattr(getattr(n.func, "value", None), "id", "") == "json"], filename
    assert not [n for n in ast.walk(block[0])
                if isinstance(n, ast.Call)
                and getattr(n.func, "id", "") == "print"], filename
    assert not [n for n in ast.walk(block[0]) if isinstance(n, ast.Try)], filename


#: `(kind, exit code, outcome)` — the three the home distinguishes and the local copy did
#: not: it printed three keys, so "a gate fired", "the tool declined" and "a crash" all
#: arrived looking alike.
W25_OUTCOMES = [
    ("gate", 2, "HALTED — a gate fired"),
    ("refusal", 2, "REFUSED — the tool declined to proceed"),
    ("crash", 1, "FAILED — an unhandled error"),
]


@pytest.mark.parametrize("kind,code,outcome", W25_OUTCOMES,
                         ids=[r[0] for r in W25_OUTCOMES])
@pytest.mark.parametrize("filename,prefix", W25_ADOPTERS, ids=[r[0] for r in W25_ADOPTERS])
def test_the_six_key_record_reaches_the_operator_from_every_adopter(filename, prefix,
                                                                    kind, code, outcome):
    """The record READ, driven through each tool's real `__main__` block with its entry
    replaced by a raiser — the same instrument the Blender census uses.

    reverted-red: yes. On `580af47` each of these prints three keys and no `outcome`, so
    every `rec["outcome"]` assertion here is a `KeyError`.
    """
    import contextlib
    import io as _io

    import blender_stub as B
    from armature_core.errors import ArmatureError, GateFailure

    handler = B.halt_handler(filename)
    assert handler == {"prefix": prefix, "entry": "main"}, (filename, handler)

    class _Gate(GateFailure):
        gate = "PROBE"

    def _raise():
        if kind == "gate":
            raise _Gate("a gate fired", {"measured": 1})
        if kind == "refusal":
            raise ArmatureError("a refusal, not a crash")
        raise ValueError("an ordinary mistake")

    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(_io.StringIO()):
        got, escaped = B.exit_code_of_main_block(
            filename, raiser=_raise, argv=["python", filename], main_name="main")
    assert escaped is None, (filename, escaped)
    assert got == code, (filename, kind, got)
    lines = [ln for ln in buf.getvalue().splitlines()
             if ln.split(" ", 1)[0] == prefix + "_HALT"]
    assert len(lines) == 1, (filename, buf.getvalue()[-400:])
    rec = json.loads(lines[0][len(prefix) + 6:])
    assert set(rec) == {"tool", "outcome", "gate", "error", "message", "evidence"}, rec
    assert rec["tool"] == prefix.lower(), rec
    assert rec["outcome"] == outcome, rec
    assert rec["gate"] == ("PROBE" if kind == "gate" else None), rec
    if kind == "gate":
        assert rec["evidence"] == {"measured": 1}, rec


def test_a_non_finite_operand_reaches_the_spend_boundary_as_strict_json(tmp_path):
    """F-af838b99 · the MEASURED half, end to end through a real subprocess.

    The saved file carries `NaN` in node 20's `fps` widget, so `round_trip` refuses and its
    evidence carries the float that caused the halt. The line an operator pipes into a
    non-Python reader must be JSON.

    reverted-red: yes. On `580af47` the same invocation printed `... "saved": NaN ...` —
    accepted by `json.loads` and refused by `json.loads(..., parse_constant=<raise>)`, by
    JS `JSON.parse`, by Go's `encoding/json` and by serde.
    """
    doc = json.loads(json.dumps(ASSEMBLY_SAVED))
    for node in doc["nodes"]:
        if node["id"] == 20:
            node["widgets_values"] = [float("nan"), 8]
    # `json.dump` writes the bare token into the FIXTURE on purpose; what is under test is
    # what the TOOL prints, not what this fixture file contains.
    proc, halt, oks = _drive("gate_saved_graph.py",
                             _assembly_cli(tmp_path, saved=doc), "SAVED_ADMISSION")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("SAVED_ADMISSION_HALT ")][-1]
    payload = line[len("SAVED_ADMISSION_HALT "):]

    def _refuse(token):
        raise AssertionError("the halt line carries the bare token " + repr(token))

    strict = json.loads(payload, parse_constant=_refuse)   # the assertion IS the parse
    assert strict["evidence"]["clause"] == "saved_values_are_not_the_built_values", strict
    saved_values = [c["saved"] for c in strict["evidence"]["checked"]]
    assert "nan" in saved_values, saved_values      # the operand, named, not deleted


@pytest.mark.parametrize("module", ["build_animate_payload", "build_camera_i2v_payload",
                                    "build_i2v_payload", "build_payload",
                                    "build_t2v_payload"])
def test_payload_error_names_its_own_gate_id(module):
    """F-af838b99 · the one class raised in this domain with no `gate` of its own.

    Fourteen raise sites already wrote `{"gate": "PAYLOAD"}` into their evidence while the
    class attribute `run_tool_main` reads said nothing, so a payload refusal's halt line
    read `gate: null` from both sources. `gate` here is a plain class attribute and NOT a
    `GateFailure`: `__str__`'s `[gate]` prefix lives on `GateFailure`, so no message text
    changes and `halt_outcome` still calls this a refusal rather than a fired gate.

    reverted-red: yes — `PayloadError.gate` is an `AttributeError` on `580af47`.
    """
    import importlib

    from armature_core.errors import GateFailure

    mod = importlib.import_module(module)
    assert mod.PayloadError.gate == "PAYLOAD", module
    assert not issubclass(mod.PayloadError, GateFailure), module
    assert str(mod.PayloadError("m")) == "m", module          # no `[PAYLOAD]` prefix
    assert mod.PayloadError("m").evidence is None, module     # wave 16's property, unmoved
