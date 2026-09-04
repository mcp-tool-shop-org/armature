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


# ================================================================== F-0682bd00 (panel HIGH)
# `seed = a.seed if a.seed is not None else registered[0]` indexed the committed
# registration with no clause on it being non-empty, and `registered = reg["seeds"]` one
# line up indexed the document with no clause on the key existing. Measured as a subprocess
# on the base tree against `{"seeds": []}`: `BUILD_T2V_HALT {"error": "IndexError",
# "message": "list index out of range", "evidence": null}` and exit **1** - the code this
# module's own `__main__` block reserves for "this tool crashed" - for an operator supplying
# an emptied registration file.
#
# The POPULATION is not this one line. Every tool in the tree that reads a committed seed
# registration read it as a bare index or as a disarming `.get("seeds") or []`: six bare
# `["seeds"]` subscripts across five builders and `gate_saved_graph`, plus
# `build_lora_arm_payload`'s default. One reader now, `build_assembly_payload
# .read_seed_registration`, and the AST census below walks EVERY file under `tools/`.

import build_t2v_payload as T2V                                          # noqa: E402
import build_assembly_payload as ASSY                                    # noqa: E402


def _reg(tmp_path, doc, name="seeds.json"):
    p = tmp_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_an_empty_registration_is_a_clause_and_not_an_IndexError(tmp_path):
    out = tmp_path / "fresh"
    with pytest.raises(ArmatureError) as exc:
        T2V.main(["--seeds", _reg(tmp_path, {"seeds": []}), "--out", str(out),
                  "--subject", "BLACKGUARD", "--no-canon"])
    ev = exc.value.evidence
    assert isinstance(ev, dict) and ev, ev
    assert ev["clause"] == "no_seed_and_no_registration", ev
    assert not isinstance(exc.value, IndexError)
    assert not out.exists(), "a refused build created its output directory"


def test_a_registration_with_no_seeds_key_is_a_clause_and_not_a_KeyError(tmp_path):
    out = tmp_path / "fresh"
    with pytest.raises(ArmatureError) as exc:
        T2V.main(["--seeds", _reg(tmp_path, {"committed": [1, 2]}), "--out", str(out),
                  "--subject", "BLACKGUARD", "--no-canon"])
    ev = exc.value.evidence
    assert ev["clause"] == "registration_no_seeds_key", ev
    assert ev["flag"] == "--seeds", ev
    assert "committed" in ev["keys"], ev
    assert not out.exists()


def test_the_empty_registration_halt_leaves_the_process_at_the_gate_exit_code(tmp_path):
    """The exit-code half, measured the way an operator meets it. The `__main__` block's
    convention is 2 = a gate refused, 1 = this tool crashed; an `IndexError` took the
    crash branch and printed a null evidence."""
    out = tmp_path / "fresh"
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "build_t2v_payload.py"),
         "--seeds=" + _reg(tmp_path, {"seeds": []}), "--out=" + str(out),
         "--subject=BLACKGUARD", "--no-canon"],
        capture_output=True, text=True, cwd=os.path.dirname(TOOLS))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("BUILD_T2V_HALT ")]
    assert line, proc.stdout
    halt = json.loads(line[-1][len("BUILD_T2V_HALT "):])
    assert halt["error"] != "IndexError", halt
    assert isinstance(halt["evidence"], dict), halt
    assert halt["evidence"]["clause"] == "no_seed_and_no_registration", halt
    assert not out.exists()


def test_an_explicit_seed_still_builds_against_a_one_entry_registration(tmp_path):
    """The direction the clause must NOT bound: the operator who names the seed is not
    defaulting to anything, so there is nothing to index."""
    out = tmp_path / "fresh"
    T2V.main(["--seeds", _reg(tmp_path, {"seeds": [7]}), "--out", str(out), "--seed", "7",
              "--subject", "BLACKGUARD", "--no-canon"])
    assert out.exists()


#: `(what the registration is, its text, the clause it must raise)` - the reader's whole
#: refusal set.
REGISTRATION_CLAUSES = [
    ("no such file", None, "registration_missing"),
    ("not JSON", "{not json", "registration_unreadable"),
    ("a list, not a mapping", "[1, 2, 3]", "registration_not_a_mapping"),
    ("no seeds key", '{"committed": [1]}', "registration_no_seeds_key"),
    ("seeds is not a list", '{"seeds": 7}', "registration_seeds_not_a_list"),
]


@pytest.mark.parametrize("what,text,clause", REGISTRATION_CLAUSES,
                         ids=[c for _, _, c in REGISTRATION_CLAUSES])
def test_the_one_registration_reader_refuses_every_unreadable_shape(
        tmp_path, what, text, clause):
    path = str(tmp_path / "reg.json")
    if text is not None:
        open(path, "w", encoding="utf-8").write(text)
    with pytest.raises(ASSY.SeedRegistrationError) as exc:
        ASSY.read_seed_registration(path, flag="--seeds")
    ev = exc.value.evidence
    assert ev["clause"] == clause, (what, ev)
    assert ev["gate"] == "PAYLOAD" and ev["andon"] == "seed_registration", ev
    assert ev["path"] == os.path.abspath(path), ev


def test_the_reader_returns_an_empty_list_rather_than_refusing_it(tmp_path):
    """Emptiness is the CALLER's clause, not the reader's: a caller with an explicit
    `--seed` is not defaulting to anything and has nothing to index."""
    p = str(tmp_path / "r.json")
    open(p, "w", encoding="utf-8").write('{"seeds": []}')
    assert ASSY.read_seed_registration(p, flag="--seeds") == []


# ---- the CENSUS: every file under `tools/`, not the one line the finding named.

def _is_json_load(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "load" and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "json")


def _seeds_reads(path):
    """Every `seeds` read off a JSON DOCUMENT in one file, by AST.

    Precise rather than textual: it walks each module- or function-level scope, collects
    the names bound from a `json.load(...)` call, and reports `<that name>["seeds"]`,
    `<that name>.get("seeds")` and the direct `json.load(fh)["seeds"]` form. Keying on the
    loaded document rather than on the string is what keeps `gate_route["seeds"]` (a gate
    result, `build_cascade_payload:247`) out of the population while keeping every
    registration read in it — the census would otherwise flag a site it has no business
    ruling on, and a census that cries wolf is one a later session deletes.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    hits = []
    for scope in [tree] + [n for n in ast.walk(tree)
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        loaded = set()
        for node in ast.walk(scope):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if value is not None and _is_json_load(value):
                    loaded.update(t.id for t in targets if isinstance(t, ast.Name))
        for node in ast.walk(scope):
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                    and node.slice.value == "seeds"
                    and ((isinstance(node.value, ast.Name) and node.value.id in loaded)
                         or _is_json_load(node.value))):
                hits.append(("subscript", node.lineno))
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "seeds"
                    and ((isinstance(node.func.value, ast.Name)
                          and node.func.value.id in loaded)
                         or _is_json_load(node.func.value))):
                hits.append(("get", node.lineno))
    return sorted(set(hits))


def test_no_tool_in_the_tree_reads_a_seed_registration_by_bare_index():
    """The wave-16 population clause. The finding named `build_t2v_payload:497`; the same
    bare read was at SIX sites across five builders and `gate_saved_graph`, and
    `build_lora_arm_payload` carried the disarming form (`registry.get("seeds") or []`,
    which turns a registration with no key into an empty list and reports the seed as
    unregistered rather than the file as unreadable).

    Measured on the base tree, this census listed build_animate_payload.py,
    build_camera_i2v_payload.py, build_i2v_payload.py, build_lora_arm_payload.py,
    build_r2v_payload.py, build_t2v_payload.py and gate_saved_graph.py."""
    offenders = {}
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py") or name == "build_assembly_payload.py":
            continue
        hits = _seeds_reads(os.path.join(TOOLS, name))
        if hits:
            offenders[name] = hits
    assert offenders == {}, (
        "every seed registration is read through "
        "build_assembly_payload.read_seed_registration; still bare: %r" % (offenders,))


def test_the_one_reader_is_the_one_place_that_names_the_key():
    hits = _seeds_reads(os.path.join(TOOLS, "build_assembly_payload.py"))
    assert hits, "the reader must be the site that names the key"
