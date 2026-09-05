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
