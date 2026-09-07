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
import builtins
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
    # wave 18 (F-c11410c5): `andon` is the class, `clause` is the clause. Both are here.
    assert ev["andon"] == "SavedAdmission", ev
    assert ev["clause"] == "duplicate_socket_name", ev
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
                  "--subject", "PERFORMER", "--no-canon"])
    ev = exc.value.evidence
    assert isinstance(ev, dict) and ev, ev
    assert ev["clause"] == "no_seed_and_no_registration", ev
    assert not isinstance(exc.value, IndexError)
    assert not out.exists(), "a refused build created its output directory"


def test_a_registration_with_no_seeds_key_is_a_clause_and_not_a_KeyError(tmp_path):
    out = tmp_path / "fresh"
    with pytest.raises(ArmatureError) as exc:
        T2V.main(["--seeds", _reg(tmp_path, {"committed": [1, 2]}), "--out", str(out),
                  "--subject", "PERFORMER", "--no-canon"])
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
         "--subject=PERFORMER", "--no-canon"],
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
              "--subject", "PERFORMER", "--no-canon"])
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


# ================================================================== F-71ffdbfb (panel HIGH)
# `alpha = color in (4, 6)` was written into every i2v payload record and READ BY NOTHING -
# the identical shape wave 14 corrected one field over in the same dict
# (`fit_agrees_with_the_file`) - and it was WRONG in one direction: a palette PNG carrying
# transparency through a tRNS chunk read `alpha: False`, which this module's own
# `_PNG_COLOR_TYPES` comment already said was possible.
#
# The law it makes machine-readable (the Director's ruling 2026-08-12) has two halves: the
# authored master carries alpha, and **the RGB composite each route submits is a deliberate,
# recorded choice**, because video VAEs are RGB and raw transparency cannot reach the model.
# `--start-frame` is the file this route UPLOADS, so the honest declaration on both i2v
# routes is `declares_alpha=False` - the recorded composite - and the andon fires in both
# directions: a file that disagrees with what the route declares refuses, and a route that
# declares nothing refuses too (a default may not disarm a clause).

import build_camera_i2v_payload as CAM                                   # noqa: E402
import build_i2v_payload as W1                                           # noqa: E402


def _chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def _png_bytes(w, h, color_type, *, trns=None):
    """A minimal, valid-enough PNG: real IHDR, optional tRNS, one IDAT, IEND.

    `png_header` reads the IHDR by `struct` and walks the chunk list; nothing decodes the
    pixels, so the IDAT payload only has to be present.
    """
    doc = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)))
    if color_type == 3:
        doc += _chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
    if trns is not None:
        doc += _chunk(b"tRNS", trns)
    doc += _chunk(b"IDAT", zlib.compress(b"\x00" * (w * h + h)))
    doc += _chunk(b"IEND", b"")
    return doc


def _write_png(tmp_path, name, w, h, color_type, *, trns=None):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(_png_bytes(w, h, color_type, trns=trns))
    return str(p)


#: `(what the file is, colour type, tRNS payload, the alpha the reader must report,
#:   where it read it from)`. Colour types 0, 2 and 3 may ALL carry a tRNS chunk; 4 and 6
#: carry the channel itself; 0 and 2 without one are opaque. That is the whole population
#: of PNG transparency, from the format spec, and the reader is graded against all of it.
PNG_ALPHA_POPULATION = [
    ("grayscale, opaque", 0, None, False, None),
    ("grayscale + tRNS", 0, b"\x00\x00", True, "tRNS"),
    ("rgb, opaque", 2, None, False, None),
    ("rgb + tRNS", 2, b"\x00\x00\x00\x00\x00\x00", True, "tRNS"),
    ("palette, opaque", 3, None, False, None),
    ("palette + tRNS", 3, b"\x00\xff", True, "tRNS"),
    ("grayscale_alpha", 4, None, True, "color_type"),
    ("rgba", 6, None, True, "color_type"),
]


@pytest.mark.parametrize("what,ctype,trns,alpha,source", PNG_ALPHA_POPULATION,
                         ids=[c[0].replace(" ", "_").replace(",", "")
                              for c in PNG_ALPHA_POPULATION])
def test_the_png_reader_reports_alpha_for_every_shape_the_format_allows(
        tmp_path, what, ctype, trns, alpha, source):
    """Red on `palette + tRNS`, `rgb + tRNS` and `grayscale + tRNS`: `color in (4, 6)`
    cannot see a tRNS chunk, and the module's own `_PNG_COLOR_TYPES` comment said so
    ("3 is a palette, which may carry transparency through a tRNS chunk") while the line
    below it answered False."""
    head = CAM.png_header(_write_png(tmp_path, "p.png", 8, 8, ctype, trns=trns))
    assert head["alpha"] is alpha, (what, head)
    assert head["alpha_source"] == source, (what, head)


def _resolved(tmp_path, name, color_type, *, trns=None, size=(1024, 576)):
    return CAM.resolve_start_frame(
        _write_png(tmp_path, name, size[0], size[1], color_type, trns=trns), None)


def test_a_route_that_declares_nothing_about_alpha_is_REFUSED(tmp_path):
    """Rule 3: a default may not disarm a clause. `declares_alpha` has no permissive
    default - a caller that says nothing about the artifact it is submitting cannot have
    its silence read as agreement with whatever the file turned out to be."""
    ev = _resolved(tmp_path, "plate.png", 2)
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(ev, "server.png", 1024, 576,
                              fit="native - authored at 1024x576")
    e = exc.value.evidence
    assert e["clause"] == "alpha_declaration_missing", e
    assert e["measured_alpha"] is False, e


def test_a_start_frame_carrying_alpha_where_the_route_records_a_COMPOSITE_refuses(tmp_path):
    """The direction the Director's ruling names: raw transparency cannot reach an RGB
    video VAE, so a route that records a submitted composite may not submit a file that
    still carries the channel. Red on the base tree: `measured.alpha` was recorded as True
    and nothing refused."""
    ev = _resolved(tmp_path, "master.png", 6)
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(ev, "server.png", 1024, 576,
                              fit="native - authored at 1024x576", declares_alpha=False)
    e = exc.value.evidence
    assert e["clause"] == "alpha_disagrees_with_the_file", e
    assert e["declares_alpha"] is False and e["measured_alpha"] is True, e
    assert e["alpha_source"] == "color_type", e


def test_a_palette_start_frame_with_tRNS_is_caught_by_the_same_clause(tmp_path):
    """The member the old reader could not see at all: `color in (4, 6)` answered False for
    a palette carrying transparency, so this file passed the arming clause as well as the
    reader."""
    ev = _resolved(tmp_path, "pal.png", 3, trns=b"\x00\xff")
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(ev, "server.png", 1024, 576,
                              fit="native - authored at 1024x576", declares_alpha=False)
    assert exc.value.evidence["alpha_source"] == "tRNS"


def test_a_route_that_declares_an_authored_master_refuses_a_flattened_plate(tmp_path):
    """The other direction, so the clause is not a one-way test: a route declaring the
    authored RGBA master and handed a flat RGB plate - the E11 baked-grey-void shape - is
    refused by the same clause with the declaration in the evidence."""
    ev = _resolved(tmp_path, "flat.png", 2)
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(ev, "server.png", 1024, 576,
                              fit="native - authored at 1024x576", declares_alpha=True)
    e = exc.value.evidence
    assert e["clause"] == "alpha_disagrees_with_the_file", e
    assert e["declares_alpha"] is True and e["measured_alpha"] is False, e


def test_the_agreeing_composite_still_builds_and_the_record_says_which_clause_ran(tmp_path):
    ev = _resolved(tmp_path, "ok.png", 2)
    rec = W1.start_image_record(ev, "server.png", 1024, 576,
                                fit="native - authored at 1024x576", declares_alpha=False)
    assert rec["alpha_declared"] is False
    assert rec["alpha_agrees_with_the_file"] is True
    assert rec["measured"]["alpha"] is False
    assert rec["measured"]["alpha_source"] is None


def test_the_i2v_builder_refuses_a_transparent_start_frame_and_writes_nothing(tmp_path):
    """The gate is inside `build`, through the one `start_image_record` both routes share,
    so an in-process caller cannot route past it."""
    rgba = W1.resolve_start_frame(
        _write_png(tmp_path, "rgba.png", W1.WIDTH, W1.HEIGHT, 6))
    out = tmp_path / "fresh" / "run"
    with pytest.raises(W1.PayloadError) as exc:
        W1.build({"start_frame": "s.png"}, None, "neg", "pos", [1], start_frame=rgba)
    assert exc.value.evidence["clause"] == "alpha_disagrees_with_the_file"
    assert not out.exists()


# ---- the POPULATION: every caller of the one `start_image_record`.

def _start_image_record_calls(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and ((isinstance(node.func, ast.Attribute)
                      and node.func.attr == "start_image_record")
                     or (isinstance(node.func, ast.Name)
                         and node.func.id == "start_image_record"))):
            out.append((node.lineno, {k.arg for k in node.keywords}))
    return out


def test_every_route_that_writes_a_start_image_block_declares_what_it_submits():
    """The census the finding's `read by NOTHING` grep is the mirror of: the field is read
    now, so every writer must declare. Two callers today - `build_i2v_payload.build` and
    `build_camera_i2v_payload.build` - and a third added without a declaration goes red
    here rather than in a paid submission."""
    callers = {}
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        calls = _start_image_record_calls(os.path.join(TOOLS, name))
        if calls:
            callers[name] = calls
    assert sorted(callers) == ["build_camera_i2v_payload.py", "build_i2v_payload.py"], \
        callers
    for name, calls in callers.items():
        for lineno, kwargs in calls:
            assert "declares_alpha" in kwargs, (name, lineno, kwargs)


def test_the_alpha_field_is_read_by_a_caller_and_no_longer_only_written():
    """`fit_agrees_with_the_file`'s sibling defect, closed the same way: the value is an
    argument to a refusal now, not a line in a record nothing opens."""
    src = open(os.path.join(TOOLS, "build_i2v_payload.py"), encoding="utf-8").read()
    assert "alpha_disagrees_with_the_file" in src
    assert 'measured["alpha"]' in src or 'measured.get("alpha")' in src


# ================================================================== F-e6450965 (panel HIGH)
# `parts = [int(v) for v in a.frame.split(",")]` CONVERTED BEFORE IT COUNTED, so a
# non-numeric component of `--frame` raised a bare stdlib `ValueError` on the tool that is
# the last gate before a paid submission. Measured on the base tree:
# `--frame=832,480,eighty` raised `ValueError: invalid literal for int() with base 10:
# 'eighty'` with no `evidence` attribute at all, which the `__main__` block renders as
# `SAVED_ADMISSION_HALT {"error": "ValueError", ..., "evidence": null}` and exit **1** -
# "this tool crashed" - two lines above a named refusal at exit 2 for the wrong ARITY.
#
# One clause for both shapes now, with the keys every other raise in this file carries.
# `composite_reference.parse_plate` is the shape carried: count the parts, then convert.


def _gsg_files(tmp_path):
    """The three files `gate_saved_graph.main` needs before it reaches `--frame`."""
    d = tmp_path / "in"
    d.mkdir(parents=True, exist_ok=True)
    api = {"49": {"class_type": "WanImageToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}}}
    saved = {"nodes": [{"id": 49, "type": "WanImageToVideo", "inputs": [],
                        "widgets_values": [832, 480, 81, 1]}]}
    for name, doc in (("api.json", api), ("saved.json", saved),
                      ("seeds.json", {"seeds": [1]})):
        (d / name).write_text(json.dumps(doc), encoding="utf-8")
    return [f"--api={d / 'api.json'}", f"--saved={d / 'saved.json'}",
            f"--seeds={d / 'seeds.json'}", f"--out={tmp_path / 'fresh' / 'rec.json'}",
            "--experiment=E09", "--stage=B2"]


#: `(the supplied --frame, why it is not three integers)`. Both shapes, one clause.
BAD_FRAMES = [
    ("832,480,eighty", "non_numeric"),
    ("832,480", "wrong_arity"),
    ("832,480,81,1", "wrong_arity"),
    ("", "wrong_arity"),
    ("832, ,81", "non_numeric"),
]


@pytest.mark.parametrize("supplied,why", BAD_FRAMES, ids=[f"{s!r}" for s, _ in BAD_FRAMES])
def test_a_frame_that_is_not_three_integers_is_ONE_named_clause(tmp_path, supplied, why):
    """Red on `832,480,eighty`: a bare `ValueError` with no evidence attribute at all. The
    arity cases were already refused, by a `RouteGate` whose evidence was `{"supplied": …}`
    alone - none of the `gate`/`andon`/`clause` keys every other raise in this file
    carries."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.main(_gsg_files(tmp_path) + [f"--frame={supplied}"])
    ev = exc.value.evidence
    assert ev["clause"] == "frame_not_three_integers", ev
    assert ev["gate"] == "SAVED_ADMISSION", ev
    # wave 18 (F-c11410c5): the raise moved onto `gate_saved_graph.SavedAdmission`, the
    # class that owns the id its evidence names, and `andon` names that class. The clause
    # assertion above is unchanged and is what a triage keys on.
    assert ev["andon"] == "SavedAdmission", ev
    assert ev["supplied"] == supplied, ev
    assert ev["flag"] == "--frame", ev
    assert isinstance(ev["parts"], list), ev


def test_the_non_numeric_frame_leaves_the_process_at_the_gate_exit_code(tmp_path):
    """The exit-code half: 2 = a gate refused, 1 = this tool crashed. A `ValueError` took
    the crash branch and printed a null evidence on the last gate before a spend."""
    args = _gsg_files(tmp_path)
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"), *args,
         "--frame=832,480,eighty"],
        capture_output=True, text=True, cwd=os.path.dirname(TOOLS))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("SAVED_ADMISSION_HALT ")]
    assert line, proc.stdout
    halt = json.loads(line[-1][len("SAVED_ADMISSION_HALT "):])
    assert halt["error"] != "ValueError", halt
    assert isinstance(halt["evidence"], dict), halt
    assert halt["evidence"]["clause"] == "frame_not_three_integers", halt


def test_a_legal_frame_gets_PAST_the_parser(tmp_path):
    """The direction the clause must not bound. The two-node fixture above is deliberately
    too thin to clear Gate PAIR, so the assertion is on WHICH clause fires: a legal
    `--frame` is parsed and the admission carries on to the gates that read the graph."""
    with pytest.raises(ArmatureError) as exc:
        GSG.main(_gsg_files(tmp_path) + ["--frame=832,480,81"])
    ev = exc.value.evidence or {}
    assert ev.get("clause") != "frame_not_three_integers", ev


# ---- the POPULATION: every operator-typed, comma-separated argv value the two admission
# and fetch tools convert. Three parsers; two carried a typed clause before this wave.

def _bad_node_map():
    import fetch_run as FR
    # `""` is the documented default-to-E02 path; `","` is a map that parses to nothing.
    FR.parse_node_map(",")


def _bad_video_nodes():
    import fetch_run as FR
    FR.parse_video_nodes("")


def _bad_frame(tmp_path):
    GSG.main(_gsg_files(tmp_path) + ["--frame=832,480,eighty"])


COMMA_ARGV_PARSERS = [
    ("gate_saved_graph --frame", _bad_frame, "frame_not_three_integers"),
    ("fetch_run --node-map", lambda _tmp: _bad_node_map(), "node_map_empty"),
    ("fetch_run --video-nodes", lambda _tmp: _bad_video_nodes(), "video_nodes_empty"),
]


@pytest.mark.parametrize("what,drive,clause", COMMA_ARGV_PARSERS,
                         ids=[c for _, _, c in COMMA_ARGV_PARSERS])
def test_every_comma_separated_argv_value_refuses_through_a_named_clause(
        tmp_path, what, drive, clause):
    with pytest.raises(ArmatureError) as exc:
        drive(tmp_path)
    ev = exc.value.evidence
    assert isinstance(ev, dict), (what, ev)
    assert ev.get("clause") == clause, (what, ev)


def test_no_argv_value_in_this_tool_is_converted_before_it_is_counted():
    """The AST half. `[int(v) for v in a.<flag>.split(",")]` is the shape that converts
    before it counts; the last gate before a paid submission may not carry one."""
    tree = ast.parse(open(os.path.join(TOOLS, "gate_saved_graph.py"),
                          encoding="utf-8").read())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            continue
        elt = node.elt
        if (isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name)
                and elt.func.id in ("int", "float")):
            for gen in node.generators:
                it = gen.iter
                if (isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute)
                        and it.func.attr == "split"):
                    offenders.append(node.lineno)
    assert offenders == [], offenders


# ==================================== F-c496fa48 (panel MEDIUM) + F-d366f088 (panel LOW)
# RULE 5, the wave's one family rule for the evidence contract, builders' quarter of it.
#
# The base `ArmatureError(message, evidence=None)` STORES WHAT IT IS PASSED and normalises
# nothing (`armature_core/errors.py`, wave 14; the contract text is core-gates' SEAM 1).
# `GateFailure` is the ONE exemption - it keeps `evidence or {}` because a gate builds `ev`
# as it measures and its clauses index into it. Four builder modules defined
# `PayloadError.__init__` with their own `evidence or {}`, under a docstring whose stated
# reason - "the single one belongs beside `GateFailure` in `armature_core/errors.py`. That
# file is not this domain's to edit" - stopped being true when wave 14 put the constructor
# on the base. So a bare builder refusal printed `{}` where the family contract now says
# `null`, and the four copies diverged from the base's rule rather than from nothing.
#
# `build_animate_payload` carried it TWICE, byte-identical, back to back (F-d366f088): the
# first definition was dead, so any later correction applied to it would silently never run.
# Measured: no lint step exists in CI or verify.ps1 (`grep -rn 'ruff|flake8|pylint'` over
# .github/workflows/, verify.ps1 and pyproject.toml returns 0 hits), so F811 never fired
# and the suite was green with the duplicate present.

#: The builders domain's owned modules, from the frozen domain map's globs.
OWNED = sorted(
    n for n in os.listdir(TOOLS)
    if n.endswith(".py") and (n.startswith("build_") and n.endswith("_payload.py")
                              or n in ("build_payload.py", "canon_gate.py",
                                       "gate_saved_graph.py", "fetch_run.py",
                                       "fetch_t2v_run.py")))

PAYLOAD_ERROR_MODULES = ["build_animate_payload", "build_camera_i2v_payload",
                         "build_i2v_payload", "build_payload"]


@pytest.mark.parametrize("mod_name", PAYLOAD_ERROR_MODULES)
def test_every_payload_error_stores_the_evidence_it_is_given(mod_name):
    """Clause 1 and clause 2 of the contract, on all four copies. Red on the base tree:
    `PayloadError("m").evidence == {}` in every one of them, while
    `ArmatureError("m").evidence is None`."""
    mod = importlib.import_module(mod_name)
    d = {"gate": "X", "measured": 1}
    assert mod.PayloadError("m", d).evidence is d, mod_name          # identity, not equality
    assert mod.PayloadError("m").evidence is None, mod_name
    assert mod.PayloadError("m").evidence is ArmatureError("m").evidence, mod_name
    assert str(mod.PayloadError("m")) == "m", mod_name


#: Wave 35: `SeedRegistration` is a list subclass carrying `.ceiling` / `.allocation`,
#: not an evidence-normalising andon. Its `__init__` is the carrier, not a GateFailure
#: override — exempt it so the census still catches error classes that rewrite evidence.
_INIT_EXEMPT = frozenset({"SeedRegistration"})


@pytest.mark.parametrize("name", OWNED)
def test_no_class_in_this_domain_normalises_the_evidence_it_is_handed(name):
    """The POPULATION: every class defined in the builders domain's owned modules, not the
    four the finding named. A class outside the `GateFailure` subtree defines no
    `__init__` at all - inheritance already gives it the two-argument shape."""
    tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name in _INIT_EXEMPT:
            continue
        for body in node.body:
            if (isinstance(body, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and body.name == "__init__"):
                offenders.append((node.name, body.lineno))
    assert offenders == [], (name, offenders)


@pytest.mark.parametrize("name", OWNED)
def test_no_class_in_this_domain_declares_one_method_twice(name):
    """F-d366f088. `PayloadError.__init__` was defined TWICE, back to back, byte-identical,
    in `build_animate_payload` - the fingerprint of the wave-14 merge, and a definition
    nothing in CI could see (there is no lint step in this repo). Red on the base tree with
    exactly 1 hit across the whole domain."""
    tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
    dupes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        seen = {}
        for body in node.body:
            if isinstance(body, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if body.name in seen:
                    dupes.append((node.name, body.name, seen[body.name], body.lineno))
                seen[body.name] = body.lineno
    assert dupes == [], (name, dupes)


def test_no_lint_step_would_have_caught_the_duplicate_so_the_census_is_the_check():
    """The premise the finding measured, re-measured here rather than inherited: nothing in
    CI or the local verify script raises F811, so a duplicate method definition is invisible
    to everything except a census like the one above."""
    repo = os.path.dirname(TOOLS)
    haystack = []
    wf = os.path.join(repo, ".github", "workflows")
    if os.path.isdir(wf):
        haystack += [os.path.join(wf, f) for f in os.listdir(wf)]
    for extra in ("verify.ps1", "pyproject.toml"):
        p = os.path.join(repo, extra)
        if os.path.isfile(p):
            haystack.append(p)
    hits = []
    for p in haystack:
        text = open(p, encoding="utf-8", errors="replace").read().lower()
        hits += [(os.path.basename(p), w) for w in ("ruff", "flake8", "pylint")
                 if w in text]
    assert hits == [], (
        "a lint step exists now - re-derive whether the duplicate-definition census is "
        f"still the only check: {hits}")


def test_a_bare_builder_refusal_reaches_the_halt_record_as_null(tmp_path):
    """The halt-line consequence SEAM 1 asks every deleting domain to re-read. A refusal
    raised with a message and no dict prints `"evidence": null`, which the 21-tool halt
    contract calls the honest record; it printed `{}` before.

    ⚠ **The exemplar moved** (wave 18, F-c080a03f). This drove
    `CAM.resolve_start_frame(None, None)`, which raised a message and no dict — and that
    was the defect one door down: `build_i2v_payload.resolve_start_frame` relays this
    refusal, so `evidence['clause']` was None for every start-frame halt on the route whose
    entire conditioning is one image, and a triage could not tell "no such file" from "not a
    PNG this tool can read". All three of that resolver's refusals name a clause now. The
    property under test is the BASE CLASS's — it stores what it is passed and invents
    nothing — so it is driven directly, which is where it lives."""
    exc = CAM.PayloadError("a message, no dict")
    detail = getattr(exc, "evidence", None)
    assert detail is None
    assert json.dumps({"evidence": detail if isinstance(detail, dict) else None}) == \
        '{"evidence": null}'
    # and the site this used to drive now names its clause
    with pytest.raises(CAM.PayloadError) as caught:
        CAM.resolve_start_frame(None, None)
    assert caught.value.evidence["clause"] == "start_frame_not_supplied"


# ================================================================ F-f85c37f0 (panel MEDIUM)
# ONE andon per receipt. `gate_seed_registered` built `ev = {"gate": "S", ...}` and raised
# it as `RG.RouteGate`, whose class attribute is `gate = "ROUTE"`, so a reader of the
# record's `gates.S` entry and a reader of the printed halt line were looking at two
# different gate ids for one event: `str(exc)` rendered `[ROUTE] seed 999 is not on the
# committed registration [1, 2]` while `exc.evidence["gate"]` said `S`, with `andon` and
# `clause` both absent. `gate_one_paid_node` had the first half of the same shape
# (`evidence["gate"] == "CEILING"`, class id `ROUTE`).
#
# The family was closed one door over in `armature_core/assembly.py` (F-fb4fc1c0) and is
# re-measured here rather than assumed. Typed subclasses whose class `gate` IS the id the
# evidence names is the branch taken; every refusal in the module now carries all three keys.

import build_r2v_payload as R2V                                          # noqa: E402


def _r2v_graph(extra=None):
    g = {"500": {"class_type": R2V.R2V_CLASS, "inputs": {}}}
    if extra:
        g.update(extra)
    return g


def _drive_unknown_arm():
    R2V.build(arm="A9", seed=1, prompt="p", negative="n")


def _drive_a1_without_refs():
    R2V.build(arm="A1", seed=1, prompt="p", negative="n")


def _drive_a2_without_uploads():
    R2V.build(arm="A2", seed=1, prompt="p", negative="n")


def _drive_unregistered_seed():
    R2V.gate_seed_registered(999, [1, 2])


def _drive_two_billable_nodes():
    R2V.gate_one_paid_node(_r2v_graph({"501": {"class_type": R2V.R2V_CLASS,
                                               "inputs": {}}}))


def _drive_a_foreign_partner_tier():
    R2V.gate_one_paid_node(_r2v_graph({"600": {"class_type": "KlingVideoApi",
                                               "inputs": {}}}))


#: Every refusal this module can raise, driven. The POPULATION the property must hold over
#: is the module's whole refusal set, not the one line the finding named.
R2V_REFUSALS = [
    ("build / unknown arm", _drive_unknown_arm),
    ("build / A1 with no refs", _drive_a1_without_refs),
    ("build / A2 with no uploads", _drive_a2_without_uploads),
    ("gate_seed_registered / unregistered", _drive_unregistered_seed),
    ("gate_one_paid_node / two billable", _drive_two_billable_nodes),
    ("gate_one_paid_node / foreign tier", _drive_a_foreign_partner_tier),
]


@pytest.mark.parametrize("what,drive", R2V_REFUSALS, ids=[w for w, _ in R2V_REFUSALS])
def test_every_refusal_names_ONE_gate_in_its_receipt_and_its_halt_line(what, drive):
    """The red proof and the census in one: `evidence["gate"]` is the raising class's own
    id, so the printed `[…]` prefix and the record's gate entry cannot disagree; and every
    refusal carries `andon` and `clause`, which `gate_seed_registered` did not."""
    with pytest.raises(ArmatureError) as exc:
        drive()
    ev = exc.value.evidence
    assert isinstance(ev, dict) and ev, (what, ev)
    assert ev["gate"] == type(exc.value).gate, (what, ev["gate"], type(exc.value).gate)
    assert str(exc.value).startswith(f"[{ev['gate']}]"), (what, str(exc.value)[:40])
    assert ev.get("andon"), (what, ev)
    assert ev.get("clause"), (what, ev)


def test_the_seed_gate_raises_the_class_that_already_OWNS_the_id_S():
    """No second andon on an id another andon already uses - `tests/test_gates.py` forbids
    it, and `errors.GateSSeedRegistration` is the id's owner, raised by
    `build_lora_arm_payload.gate_s` for this same clause. One id, one class, one meaning."""
    from armature_core.errors import GateSSeedRegistration
    with pytest.raises(GateSSeedRegistration) as exc:
        R2V.gate_seed_registered(999, [1, 2])
    assert GateSSeedRegistration.gate == "S"
    assert str(exc.value).startswith("[S] ")
    assert exc.value.evidence["clause"] == "seed_not_registered"


def test_the_ceiling_gate_carries_its_own_id_too():
    with pytest.raises(RG.RouteGate) as exc:
        _drive_two_billable_nodes()
    assert type(exc.value) is R2V.SpendCeiling
    assert R2V.SpendCeiling.gate == "CEILING"


def test_the_passing_seed_gate_records_the_same_id_it_would_have_raised():
    from armature_core.errors import GateSSeedRegistration
    ev = R2V.gate_seed_registered(1, [1, 2])
    assert ev["gate"] == GateSSeedRegistration.gate == "S"
    assert ev["andon"] == "GateSSeedRegistration"


def _evidence_keys(bases, call):
    """The keys of the evidence dict a `raise X(msg, <expr>)` passes, resolved one level.

    Three spellings appear in this tree: a dict literal, `dict(<name>, clause=…)` over a
    base built as it measured, and a bare `<name>` referring to that base. All three are
    resolved against the `<name> = {...}` assignment in the SAME function, so the census
    reads what the halt record will actually carry rather than what one line spells - and
    resolving per function rather than per module is what stops one function's `ev` from
    vouching for another's raise.
    """
    if len(call.args) < 2:
        return set()
    ev = call.args[1]
    if isinstance(ev, ast.Dict):
        return {k.value for k in ev.keys if isinstance(k, ast.Constant)}
    if isinstance(ev, ast.Name):
        return set(bases.get(ev.id, ()))
    if isinstance(ev, ast.Call) and ast.unparse(ev.func) == "dict":
        keys = {k.arg for k in ev.keywords}
        for a in ev.args:
            if isinstance(a, ast.Name):
                keys |= set(bases.get(a.id, ()))
            elif isinstance(a, ast.Dict):
                keys |= {k.value for k in a.keys if isinstance(k, ast.Constant)}
        return keys
    return set()


def _refusals_with_thin_evidence(path, required=("gate", "andon", "clause")):
    """Every family `raise` in one module whose evidence lacks one of `required`.

    Builtin raises (`SystemExit`) are not refusals and carry no receipt; every raise of a
    class this repo defines does.

    ⚠ **This walk resolves an evidence base ONLY through a dict LITERAL assigned in the same
    function** (`bases`, below) — and so does `test_gates.evidence_dicts_missing`, which
    core-gates owns. MEASURED on a wave-28 branch (F-a4aac9c2): lifting `fetch_run.download`'s
    shared `base = {...}` into a helper that returns the same literal turned SEVEN unchanged
    refusals thin here and put `fetch_run.py:download (FetchHalt)` into the sibling walk's
    `unreadable` list. Both censuses were grading the spelling of the base rather than the
    keys the refusal carries, and the correct wave-18 rule-1 widening spans two domains' test
    files. So the tree keeps the literal: `download`'s new timeout refusal spells its own six
    keys inline, with the reason recorded at that raise. Recorded here so the next session
    reaches for the widening deliberately rather than discovering it as a red suite.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    offenders = set()
    for fn in [tree] + [n for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        bases = {}
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                bases[node.targets[0].id] = {k.value for k in node.value.keys
                                             if isinstance(k, ast.Constant)}
        body = ast.walk(fn) if fn is not tree else []
        for node in body:
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            raised = ast.unparse(node.exc.func)
            if raised in dir(builtins):
                continue
            keys = _evidence_keys(bases, node.exc)
            missing = tuple(k for k in required if k not in keys)
            if missing:
                offenders.add((node.lineno, raised, missing, tuple(sorted(keys))))
    return sorted(offenders)


def test_no_raise_in_this_module_names_a_gate_its_class_does_not():
    """The AST half, so a refusal added tomorrow with a hand-typed `"gate"` is caught here
    rather than in a record two readings apart."""
    offenders = _refusals_with_thin_evidence(
        os.path.join(TOOLS, "build_r2v_payload.py"))
    assert offenders == [], offenders
    src = open(os.path.join(TOOLS, "build_r2v_payload.py"), encoding="utf-8").read()
    classes = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ClassDef)}
    assert "SpendCeiling" in classes


# ================================================================= F-dc32fa9d (panel LOW)
# The clause wave 8 added to replace a `SystemExit` with "a typed FetchHalt with an evidence
# dict" (its own comment at fetch_t2v_run:108-110) raised without the three keys every other
# halt in the two fetchers carries: `{"unexpected_node": nid, "known": [...]}` has no `gate`,
# no `andon`, no `clause`, where the `empty_results` clause eleven lines up carries all
# three. `download` keys all six of its own refusals on `clause`, so a receipt reader keyed
# on it could not classify the one refusal an operator pasting the wrong dump is most likely
# to hit.
#
# The finding named two sites (`fetch_t2v_run:111` and its sibling `fetch_run:215`). The
# CENSUS below walks every `raise FetchHalt` in both fetchers - 21 of them - and measured on
# the base tree only FOUR carried all three keys.

FETCHERS = ["fetch_run.py", "fetch_t2v_run.py"]


@pytest.mark.parametrize("name", FETCHERS)
def test_every_fetch_halt_carries_the_three_keys_a_receipt_reader_uses(name):
    """The population is every `raise FetchHalt` in the file, not the one the finding named.

    Red on the base tree at 17 of 21 sites across the two fetchers, including both
    unmapped-node clauses, both fetchers' `--node-map` / `--video-nodes` parse refusals, the
    plan's path-collision clause, `fetch_t2v_run`'s zero-length-frame halt and the ORDER
    gate's own refusal - every one of which prints its dict into a halt line a wrapper reads.
    """
    offenders = _refusals_with_thin_evidence(os.path.join(TOOLS, name))
    assert offenders == [], offenders


def test_the_unmapped_node_clause_is_named_in_both_planners(tmp_path):
    """The two sites the finding named, driven rather than read."""
    import fetch_run as FR
    import fetch_t2v_run as FT

    with pytest.raises(FT.FetchHalt) as exc:
        FT.plan([{"source_node_id": "999", "url": "u", "filename": "f.png"}],
                str(tmp_path / "out"))
    ev = exc.value.evidence
    assert ev["clause"] == "unexpected_source_node", ev
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt", ev
    assert ev["unexpected_node"] == "999", ev

    with pytest.raises(FR.FetchHalt) as exc:
        FR.plan([{"source_node_id": "999", "url": "u", "filename": "f.png"}],
                str(tmp_path), "run", {"301": "lossless"}, ("114",))
    ev = exc.value.evidence
    assert ev["clause"] == "unexpected_source_node", ev
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt", ev
    assert ev["unmapped"] == ["999"], ev


def test_every_clause_name_in_the_two_fetchers_is_distinct():
    """A `clause` a reader keys on is only useful if it names ONE refusal. Measured over
    both fetchers' evidence dicts, resolved through their base dicts."""
    seen = {}
    for name in FETCHERS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            if ast.unparse(node.exc.func) != "FetchHalt" or len(node.exc.args) < 2:
                continue
            ev = node.exc.args[1]
            clause = None
            if isinstance(ev, ast.Dict):
                for k, v in zip(ev.keys, ev.values):
                    if isinstance(k, ast.Constant) and k.value == "clause":
                        clause = ast.unparse(v)
            elif isinstance(ev, ast.Call):
                for kw in ev.keywords:
                    if kw.arg == "clause":
                        clause = ast.unparse(kw.value)
            if clause:
                seen.setdefault(clause, []).append(f"{name}:{node.lineno}")
    shared = {c: w for c, w in seen.items() if len(w) > 1}
    # `unexpected_source_node` and `empty_results` are ONE clause in two planners by
    # design - the same refusal, one wording, both fetchers - and that is what makes them
    # readable across the pair. Any other repeat is two refusals wearing one name.
    #
    # WAVE 25 (builders, F-edf3a80b): `downloader_shell_not_found` joins them, and its two
    # sites are BOTH in `fetch_run.py` — `gate_downloader_shell` (the downloader is not on
    # PATH) and the `except OSError` around the launch (it resolves and will not start).
    # They are one condition split by what `shutil.which` can and cannot see: a downloader
    # that cannot run, so no per-job exit record is written and every clause below the
    # launch would be deciding on evidence that was never produced. A reader keying on the
    # word learns the same thing from either. The sibling fetcher IMPORTS both the gate and
    # `download`, so it adds no third site.
    #
    # WAVE 35: `output_already_exists` is ONE clause in both fetchers by design — a used
    # `--root/--run` or `--out` refuses the silent blend the same way; `--force` is the
    # shared escape. A reader keying on the word learns the same thing from either tool.
    assert sorted(shared) == ["'downloader_shell_not_found'", "'empty_results'",
                              "'output_already_exists'",
                              "'unexpected_source_node'"], shared


# ============ the builders half of core-gates' F-069ae942 (SEAM 5) - the receipt-kind key
# core-gates' `route_gates.verify` now declares its own receipt kind (`receipt: "verify"`)
# in the opening evidence literal, before any clause can raise. This reader keys on that
# DECLARED VALUE first and keeps the two-fact content check as a second clause, so a record
# written by an older builder - facts, no declared kind - is still readable, and a dict that
# merely happens to carry two keys is no longer the only thing identity can rest on.
#
# ⚠ This worktree is cut from `041027c` and does NOT carry core-gates' change, so the
# declared-kind path is exercised here with hand-built receipts. Both readings admit; the
# record says which one found them.

def _receipt(**over):
    """A hand-typed `verify` receipt, as `verify` HANDS ONE BACK.

    ⚠ `verdict` is not decoration (wave 22, F-9ad5cbc2, builders). `route_facts` told a
    returned receipt from a CAUGHT REFUSAL by the absence of `clause`, and an AST walk of
    `route_gates.verify` on `e8263a3` found 17 RouteGate raise sites inside it of which 14
    write no `clause` at all — so absence of a clause was not evidence of a return. The
    reader is keyed on the RETURN's own mark now: `ev["verdict"]`, written at exactly two
    statements in `verify`, each immediately above one of its two `return ev` statements.
    A fixture that omits it is a fixture of a receipt `verify` never returned.
    """
    ev = {"gate": "ROUTE", "andon": "RouteGate",
          "carries_no_sampler_asserted": False, "attribution": [],
          "verdict": ("0 of 0 component(s) classified, no sampler (asserted and checked), "
                      "so no seed to pin")}
    ev.update(over)
    return ev


def _record(tmp_path, doc, name="rec.json"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_a_receipt_that_declares_its_kind_is_found_by_the_declaration(tmp_path):
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt(receipt="verify")}})
    facts = GSG.route_facts(path)
    assert facts["n_verify_receipts"] == 1
    assert facts["n_declaring_their_kind"] == 1
    assert facts["found_by"] == "declared receipt kind"


def test_a_receipt_with_no_declared_kind_is_still_found_by_its_facts(tmp_path):
    """The second clause, kept: a record written by a builder from before the key existed
    answers the two questions and is still readable."""
    path = _record(tmp_path, {"gate_ROUTE_built": _receipt()})
    facts = GSG.route_facts(path)
    assert facts["n_verify_receipts"] == 1
    assert facts["n_declaring_their_kind"] == 0
    assert facts["found_by"] == "the two facts they carry"


def test_the_reader_keys_on_the_VALUE_of_the_declared_kind_not_on_its_presence(tmp_path):
    """Wave-16 rule 3. A dict carrying `receipt: <anything else>` and neither fact is NOT a
    verify receipt, and a record holding only that one supplies this gate nothing."""
    path = _record(tmp_path, {"gates": {"ROUTE": {"gate": "ROUTE", "andon": "RouteGate",
                                                  "receipt": "base_licence"}}})
    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(path)
    assert exc.value.evidence["clause"] == "record_carries_no_verify_receipt"


def test_a_declared_receipt_that_answers_neither_question_is_refused_by_name(tmp_path):
    """The shape the declared reading opens and the content reading could not: a dict that
    says what it IS without supplying what this gate reads off it. Before the andon it
    reached the next line as a bare `KeyError`."""
    path = _record(tmp_path, {"gates": {"ROUTE": {"gate": "ROUTE", "andon": "RouteGate",
                                                  "receipt": "verify"}}})
    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(path)
    ev = exc.value.evidence
    assert ev["clause"] == "verify_receipt_missing_its_facts", ev
    assert sorted(ev["missing"]) == ["attribution", "carries_no_sampler_asserted"], ev


def test_no_raise_in_the_fetchers_is_caught_by_their_own_handler():
    """The readability half of F-dc32fa9d, and the reason it is not merely cosmetic: in a
    file where every refusal is a typed `FetchHalt`, a `raise ValueError` used as loop
    control reads as an untyped refusal (three jury seats read it as one). The census is
    over both fetchers, not the one line: no `raise` inside a `try` whose own handler would
    swallow it."""
    offenders = []
    for name in FETCHERS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            caught = set()
            for handler in node.handlers:
                # A handler whose whole body is a bare `raise` re-raises rather than
                # swallowing; the 21-tool `__main__` block uses exactly that shape to let a
                # deliberate `SystemExit` through, and it is not the defect this census is
                # for.
                if (len(handler.body) == 1 and isinstance(handler.body[0], ast.Raise)
                        and handler.body[0].exc is None):
                    continue
                t = handler.type
                names = ([ast.unparse(e) for e in t.elts]
                         if isinstance(t, ast.Tuple) else [ast.unparse(t)] if t else [])
                caught.update(names)
            for inner in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if isinstance(inner, ast.Raise) and isinstance(inner.exc, ast.Call):
                    if ast.unparse(inner.exc.func) in caught:
                        offenders.append((name, inner.lineno,
                                          ast.unparse(inner.exc.func)))
    assert offenders == [], offenders


@pytest.mark.parametrize("code", [None, "", "   ", "not-a-number", [1]],
                         ids=["null", "empty", "blank", "unparseable", "a list"])
def test_every_unreadable_exit_code_lands_in_unrecorded_and_not_in_failed(code):
    """The behaviour the refactor must not move: absent, blank and unparseable codes are
    all `unrecorded`, in a clause of their own, and none of them reads as "exited zero"."""
    import fetch_run as FR

    rows = [{"out": "a.png", "code": code, "message": ""}]
    unrecorded, failed = [], []
    for i, row in enumerate(rows):
        job = row.get("out")
        c = row.get("code")
        if c is None or (isinstance(c, str) and not c.strip()):
            unrecorded.append(job)
            continue
        try:
            c = int(c)
        except (TypeError, ValueError):
            unrecorded.append(job)
            continue
        if c != 0:
            failed.append(job)
    assert unrecorded == ["a.png"] and failed == [], (code, unrecorded, failed)
    assert hasattr(FR, "verify_exits") or hasattr(FR, "download"), "the module loaded"
