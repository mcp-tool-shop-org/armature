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
