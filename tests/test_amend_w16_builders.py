"""Wave 16 · builders — the seventh Stage A amend.

The wave's rule, in the coordinator's words: **name the POPULATION, and prove the census
reaches all of it**. Wave 14's fixes were right one level down and blind one level up — a
clause was added to the operand the finding named while the family around it kept the hole.
Every test in this file therefore carries two halves: the red proof on the member the
finding named, and a census over the whole population the property must hold across.

Every module under test is imported through `conftest`'s `tools/` path insert, so the code
exercised is THIS worktree's.
"""

import ast
import importlib
import json
import os
import struct
import subprocess
import sys
import zlib

import pytest

from armature_core import route_gates as RG
from armature_core.errors import ArmatureError

import gate_saved_graph as GSG

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


# ============================================================== F-04fdd395 (panel CRITICAL)
# `saved_slots = {slot.get("name"): slot for slot in (s.get("inputs") or [])}` is a
# last-write-wins comprehension with no duplicate clause. A saved node declaring `positive`
# TWICE keeps only the last entry; the earlier one is never visited by `_origin_problems`,
# and the receipt's own `n_links` disagrees with the number of sockets the file declares.
#
# This is the THIRD member of a family this module already refuses twice — `link_table`
# raises `duplicate_link_id` and `fetch_run.parse_node_map` raises `node_map_duplicate_id`,
# both citing the same reason: which entry a name resolves to is an accident of array order,
# and a file that is ambiguous about where its conditioning comes from is not a file the
# last gate before a paid submission can vouch for.

DUP_API = {
    "30": {"class_type": "CLIPTextEncode", "inputs": {"text": "the positive"}},
    "31": {"class_type": "CLIPTextEncode", "inputs": {"text": "the negative"}},
    "49": {"class_type": "WanImageToVideo",
           "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                      "positive": ["30", 0], "negative": ["31", 0]}},
}


def dup_saved(sockets, table):
    return {"nodes": [
        {"id": 30, "type": "CLIPTextEncode", "inputs": [],
         "widgets_values": ["the positive"]},
        {"id": 31, "type": "CLIPTextEncode", "inputs": [],
         "widgets_values": ["the negative"]},
        {"id": 49, "type": "WanImageToVideo", "inputs": sockets,
         "widgets_values": [832, 480, 81, 1]},
    ], "links": table}


#: The exact fixture the finding measured: `positive` declared FIRST from the negative
#: encoder (link 7) and again from the positive (link 6), with `negative` sharing link 7.
#: The old comprehension kept the LAST `positive` — the one that agrees with what we wired —
#: and the disagreeing declaration was discarded unexamined.
AMBIGUOUS_SOCKETS = [{"name": "positive", "type": "CONDITIONING", "link": 7},
                     {"name": "positive", "type": "CONDITIONING", "link": 6},
                     {"name": "negative", "type": "CONDITIONING", "link": 7}]
AMBIGUOUS_TABLE = [[6, 30, 0, 49, 0, "CONDITIONING"],
                   [7, 31, 0, 49, 1, "CONDITIONING"]]


def test_a_saved_node_declaring_one_socket_twice_is_refused_by_name():
    """The red proof. Measured on the base tree: this fixture returned
    `{'n_links': 2, 'links': ['49.negative', '49.positive'],
      'optional_sockets_empty_in_both': []}` with no halt, beside a `round_trip` that
    reported all_equal — a clean topology verdict over a file that declares three sockets
    and was examined for two."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(DUP_API, dup_saved(AMBIGUOUS_SOCKETS, AMBIGUOUS_TABLE))
    ev = exc.value.evidence
    assert ev["clause"] == "duplicate_socket_name", ev
    assert ev["gate"] == "SAVED_ADMISSION", ev
    assert ev["andon"] == "duplicate_socket_name", ev
    assert ev["node"] == "49", ev
    assert ev["name"] == "positive", ev
    assert sorted(ev["links"]) == [6, 7], ev
    assert "positive" in str(exc.value)


def test_a_socket_declared_twice_with_the_SAME_link_is_also_refused():
    """A repeat that agrees with itself is still a file declaring one socket twice, and the
    receipt's `n_links` still counts fewer sockets than the file declares. `link_table`'s
    sibling clause admits an agreeing repeat because a link id resolves to ONE origin
    either way; a socket name is the node's own input slot and two of them is a shape no
    converter emits."""
    sockets = [{"name": "positive", "type": "CONDITIONING", "link": 6},
               {"name": "positive", "type": "CONDITIONING", "link": 6},
               {"name": "negative", "type": "CONDITIONING", "link": 7}]
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(DUP_API, dup_saved(sockets, AMBIGUOUS_TABLE))
    assert exc.value.evidence["clause"] == "duplicate_socket_name"


def test_the_unambiguous_save_still_passes_and_n_links_counts_what_the_file_declares():
    sockets = [{"name": "positive", "type": "CONDITIONING", "link": 6},
               {"name": "negative", "type": "CONDITIONING", "link": 7}]
    ev = GSG.link_round_trip(DUP_API, dup_saved(sockets, AMBIGUOUS_TABLE))
    assert ev["n_links"] == 2
    assert ev["links"] == ["49.negative", "49.positive"]


# ---- the POPULATION: every name->object table this domain builds from a supplied array.
#
# Three tables, three files, one property: a name declared twice is a refusal carrying a
# `clause`, never a last-write-wins pick. Two of the three carried the clause before this
# wave; the census is driven so that a fourth table added without one goes red here rather
# than in a paid submission.

def _dup_link_table():
    GSG.link_table({"links": [[6, "30", 0, 49, 0, "CONDITIONING"],
                              [6, "31", 0, 49, 0, "CONDITIONING"]]})


def _dup_socket_name():
    GSG.link_round_trip(DUP_API, dup_saved(AMBIGUOUS_SOCKETS, AMBIGUOUS_TABLE))


def _dup_node_map():
    import fetch_run as FR
    FR.parse_node_map("301=batchprobe,301=lossless")


#: `(what the table is keyed on, the driver, the clause it must raise)`.
DUPLICATE_KEY_TABLES = [
    ("gate_saved_graph.link_table / link id", _dup_link_table, "duplicate_link_id"),
    ("gate_saved_graph.link_round_trip / socket name", _dup_socket_name,
     "duplicate_socket_name"),
    ("fetch_run.parse_node_map / node id", _dup_node_map, "node_map_duplicate_id"),
]


@pytest.mark.parametrize("what,drive,clause", DUPLICATE_KEY_TABLES,
                         ids=[c for _, _, c in DUPLICATE_KEY_TABLES])
def test_every_name_keyed_table_in_this_domain_refuses_a_duplicate_declaration(
        what, drive, clause):
    with pytest.raises(ArmatureError) as exc:
        drive()
    ev = exc.value.evidence
    assert isinstance(ev, dict), (what, ev)
    assert ev.get("clause") == clause, (what, ev)
    assert ev.get("gate"), (what, ev)
    assert ev.get("andon"), (what, ev)
