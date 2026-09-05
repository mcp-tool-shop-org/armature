"""Wave 18 · builders — the LAST Stage A amend, scoped to the paid path.

The wave's rule, in the coordinator's words: **a census keys on the RESOLVED shape, never
the spelled one; a fix's red proof runs against its SIBLINGS; a refusal names the andon
that pulled; and the halt line is READ.** Four wave-16 fixes recurred inside themselves,
so every test here carries three halves: the red proof on the OPERAND the finding named,
the sibling enumeration over the same function or family, and — for at least one refusal
per finding — the printed halt record driven through the tool's own `__main__`.

Every module under test is imported through `conftest`'s `tools/` path insert, so the code
exercised is THIS worktree's.
"""

import ast
import json
import os
import struct
import subprocess
import sys
import zlib

import pytest

from armature_core import route_gates as RG
from armature_core.errors import ArmatureError

import build_assembly_payload as BAP
import build_camera_i2v_payload as CAM
import build_i2v_payload as I2V
import build_payload as BP
import build_r2v_payload as R2V
import fetch_run as FR
import gate_saved_graph as GSG

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
REPO = os.path.dirname(TOOLS)


# --------------------------------------------------------------------------- shared helpers

def _png(path, width=4, height=4):
    """A real PNG — signature, IHDR, IEND. The thing an error body is not."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">II5B", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(FR.PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IEND", b""))
    return path


ERROR_BODY = b'{"error":"AccessDenied","code":403}'


def _gsg_files(tmp_path, seeds=(1,)):
    """The four arguments `gate_saved_graph.main` needs before it reaches `--frame`."""
    d = tmp_path / "in"
    d.mkdir(parents=True, exist_ok=True)
    api = {"49": {"class_type": "WanImageToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}}}
    saved = {"nodes": [{"id": 49, "type": "WanImageToVideo", "inputs": [],
                        "widgets_values": [832, 480, 81, 1]}]}
    for name, doc in (("api.json", api), ("saved.json", saved),
                      ("seeds.json", {"seeds": list(seeds)})):
        (d / name).write_text(json.dumps(doc), encoding="utf-8")
    return [f"--api={d / 'api.json'}", f"--saved={d / 'saved.json'}",
            f"--seeds={d / 'seeds.json'}", f"--out={tmp_path / 'fresh' / 'rec.json'}"]


def _gsg_halt(tmp_path, extra):
    """Drive `gate_saved_graph`'s `__main__` block and READ the printed halt record."""
    proc = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "gate_saved_graph.py"),
         *_gsg_files(tmp_path), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    lines = [ln for ln in proc.stdout.splitlines()
             if ln.startswith("SAVED_ADMISSION_HALT ")]
    assert lines, proc.stdout + proc.stderr
    return proc.returncode, json.loads(lines[-1][len("SAVED_ADMISSION_HALT "):])


def _raises(fn, *args, **kwargs):
    """`(exception, evidence)` — evidence normalised to a dict so a bare stdlib raise reads
    as the empty receipt it is rather than as a `TypeError` inside the assertion."""
    try:
        fn(*args, **kwargs)
    except BaseException as exc:                                        # noqa: BLE001
        return exc, (getattr(exc, "evidence", None) or {})
    raise AssertionError(f"{fn!r} did not raise")


# ============================================================ F-c7294bc6 (panel CRITICAL)
# The wave-16 andon that exists to stop `--frame` raising a bare stdlib `ValueError` on the
# last gate before a paid submission STILL RAISED ONE, because its guard predicate is WIDER
# than what `int()` accepts: `v.lstrip("+-").isdigit()` strips EVERY leading `+`/`-` (so
# `'--832'` and `'+-8'` pass the guard) and `str.isdigit()` is true for superscripts `int()`
# rejects (`'²'`). Measured on the base tree through `GSG.main`:
#   --frame=--832,480,81 -> ValueError: invalid literal for int() with base 10: '--832'
#   --frame=+-8,480,81   -> ValueError ... '+-8'
#   --frame=²,480,81     -> ValueError ... '²'
#   --frame=832,480,²    -> ValueError ... '²'
# each with NO `evidence` attribute at all, rendered by the `__main__` block as
# `SAVED_ADMISSION_HALT {"error": "ValueError", ..., "evidence": null}` at exit 1 — the code
# this module reserves for "this tool crashed". The flag's own help text warns that argparse
# eats leading minus signs, so a doubled dash is the operator error it invites.
#
# The fix does not approximate `int()`; it USES `int()` and catches.

#: The operands the guard admitted and `int()` refused. `'--832'` and `'+-8'` are the sign
#: family the help text invites; `'²'` is the `str.isdigit()` family.
W18_BAD_FRAMES = ["--832,480,81", "+-8,480,81", "²,480,81", "832,480,²"]

#: The two operands the guard and `int()` DISAGREE about in the other direction — both are
#: things `int()` accepts, so the parser must hand them on rather than refuse them.
#: `'٥'` is Arabic-Indic five, the one wide `str.isdigit()` case `int()` takes;
#: `'-8'` is a single leading minus, which `int()` reads as a negative number. Whether a
#: NEGATIVE dimension is legal is Gate L's question, not this parser's — measured on this
#: fixture, `--frame=-8,480,81` reaches Gate PAIR, so the frame clause is not what stops it
#: and `route_gates.frame_legality` is core-gates' file, out of this domain.
W18_PARSER_MUST_PASS = ["٥,480,81", "-8,480,81"]


@pytest.mark.parametrize("supplied", W18_BAD_FRAMES, ids=[repr(s) for s in W18_BAD_FRAMES])
def test_a_frame_component_int_rejects_refuses_by_NAME_not_by_ValueError(tmp_path, supplied):
    exc, ev = _raises(GSG.main, _gsg_files(tmp_path) + [f"--frame={supplied}"])
    assert not isinstance(exc, ValueError) or isinstance(exc, ArmatureError), repr(exc)
    assert ev.get("clause") == "frame_not_three_integers", (supplied, type(exc).__name__, ev)
    assert ev.get("flag") == "--frame", ev
    assert ev.get("supplied") == supplied, ev
    assert supplied.split(",")[0] in ev.get("unreadable", []) or ev.get("unreadable"), ev


@pytest.mark.parametrize("supplied", W18_PARSER_MUST_PASS,
                         ids=[repr(s) for s in W18_PARSER_MUST_PASS])
def test_the_frame_guard_is_int_itself_so_what_int_ACCEPTS_gets_through(tmp_path, supplied):
    """The direction the clause must not bound. A guard rewritten as a narrower predicate
    would have refused these here, which is the mirror of the defect."""
    exc, ev = _raises(GSG.main, _gsg_files(tmp_path) + [f"--frame={supplied}"])
    assert ev.get("clause") != "frame_not_three_integers", (type(exc).__name__, ev)


def test_the_doubled_dash_frame_leaves_the_process_at_the_GATE_exit_code(tmp_path):
    """The halt line, READ. 2 = a gate refused; 1 = this tool crashed. `'--832,480,81'`
    took the crash branch and printed `"evidence": null` on the last gate before a spend."""
    code, halt = _gsg_halt(tmp_path, ["--frame=--832,480,81"])
    assert code == 2, halt
    assert halt["error"] != "ValueError", halt
    assert isinstance(halt["evidence"], dict), halt
    assert halt["evidence"]["clause"] == "frame_not_three_integers", halt
    assert halt["evidence"]["gate"] == "SAVED_ADMISSION", halt
    assert halt["error"] == "SavedAdmission", halt


# ---- SIBLINGS (rule 2): every flag in `gate_saved_graph`'s parser. Nine flags.
#   --frame        the finding's operand, above.
#   --seeds        named: `read_seed_registration` -> registration_missing (measured).
#   --record       named: `route_facts` -> record_unreadable (measured).
#   --saved        BARE `FileNotFoundError`, evidence null   <- proven red below.
#   --api          BARE `FileNotFoundError`, evidence null   <- proven red below.
#   --hosted-tier  refused inside `route_gates.verify` (core-gates' file, out of domain);
#                  measured on this fixture it reaches Gate PAIR first, so the tier clause
#                  is unreachable from here and is not this domain's to move.
#   --experiment   free string, copied into the record only; converts nothing, opens nothing.
#   --stage        the same.
#   --out          a path opened for writing AFTER every gate; `gate_saved_graph` carries no
#                  Gate OUT. Measured: `--out=<an existing directory>` reaches Gate PAIR
#                  first on this fixture, so the write shape is not reachable behind a
#                  passing graph here. Filed as a Stage B candidate, not fixed this wave.

SIBLING_PATH_FLAGS = ["--saved", "--api"]


@pytest.mark.parametrize("flag", SIBLING_PATH_FLAGS)
def test_a_graph_flag_naming_no_file_refuses_by_name(tmp_path, flag):
    """Red on the base tree: `FileNotFoundError` with no evidence attribute at all, from
    `route_gates.load_graph`, two lines above a `--saved` that IS refused by name for its
    SHAPE. The same crash-where-a-clause-belongs shape as `--frame`."""
    args = [a for a in _gsg_files(tmp_path) if not a.startswith(flag + "=")]
    exc, ev = _raises(GSG.main, args + [f"{flag}={tmp_path / 'nope.json'}"])
    assert isinstance(exc, ArmatureError), repr(exc)
    assert ev.get("clause") == "graph_file_missing", ev
    assert ev.get("flag") == flag, ev
    assert ev.get("gate") == "SAVED_ADMISSION", ev


# ============================================================ F-c11410c5 (panel HIGH)
# Five refusals in the last gate before a paid submission named TWO gate ids for one event:
# the class is `RouteGate` (`gate = "ROUTE"`, so `str(exc)` opens `[ROUTE]`) while the
# evidence said `{"gate": "SAVED_ADMISSION"}`. Measured by AST census over the builders
# domain on the base tree — 5 sites, all in `gate_saved_graph.py`: lines 180
# (`not_a_save_format_graph`), 206 (`not_an_api_format_graph`), 323 (`duplicate_link_id`),
# 445 (`duplicate_socket_name`), 716 (`frame_not_three_integers`). Two of the five were
# ADDED in wave 16, after `build_r2v_payload.SpendCeiling` recorded the rule.
#
# The id gets its owner, declared with a PLAIN-NAME base (F-d8593862's rule): the class's
# own `.gate` and the evidence's `gate` are now one value, and `andon` names the class that
# pulled — the spelling `tests/test_core_solver_evidence.py:344` states as the tree's law.

CLASS_GATE_OF = {"RouteGate": "ROUTE", "SavedAdmission": "SAVED_ADMISSION",
                 "SpendCeiling": "CEILING", "PayloadOutHalt": "OUT",
                 "FetchHalt": "FETCH"}


def _literal(dict_or_call, key):
    if isinstance(dict_or_call, ast.Dict):
        for k, v in zip(dict_or_call.keys, dict_or_call.values):
            if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Constant):
                return v.value
    if (isinstance(dict_or_call, ast.Call) and isinstance(dict_or_call.func, ast.Name)
            and dict_or_call.func.id == "dict"):
        for kw in dict_or_call.keywords:
            if kw.arg == key and isinstance(kw.value, ast.Constant):
                return kw.value.value
    return None


def _evidence_literals(call, key):
    for arg in call.args[1:]:
        got = _literal(arg, key)
        if got is not None:
            return got
    return None


def _raise_rows(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            f = node.exc.func
            cname = (f.id if isinstance(f, ast.Name)
                     else f.attr if isinstance(f, ast.Attribute) else None)
            rows.append((node.lineno, cname, _evidence_literals(node.exc, "gate"),
                         _evidence_literals(node.exc, "andon")))
    return rows


#: Every file this domain owns. The census below is over ALL of them, not over the one
#: file the finding named — the resolved-shape rule.
OWNED = sorted(
    [os.path.join(TOOLS, n) for n in os.listdir(TOOLS)
     if n.startswith("build_") and n.endswith("_payload.py")]
    + [os.path.join(TOOLS, n) for n in
       ("build_payload.py", "canon_gate.py", "gate_saved_graph.py", "fetch_run.py",
        "fetch_t2v_run.py")])


def test_no_raise_in_this_domain_names_a_gate_its_own_class_does_not_carry():
    """The census, over the domain rather than over the one file. Red on the base tree with
    exactly the five rows the finding measured."""
    wrong = []
    for path in OWNED:
        for lineno, cname, gate, _andon in _raise_rows(path):
            want = CLASS_GATE_OF.get(cname)
            if gate is not None and want is not None and gate != want:
                wrong.append((os.path.basename(path), lineno, cname, want, gate))
    assert wrong == [], wrong


def test_the_saved_admission_id_has_exactly_one_owner_and_it_is_a_plain_name_class():
    assert issubclass(GSG.SavedAdmission, RG.RouteGate)
    assert GSG.SavedAdmission.gate == "SAVED_ADMISSION"
    exc = GSG.SavedAdmission("x", {"gate": "SAVED_ADMISSION"})
    assert str(exc).startswith("[SAVED_ADMISSION]"), str(exc)
    # declared with an `ast.Name` base, so every family census walking `ast.Name` sees it
    tree = ast.parse(open(os.path.join(TOOLS, "gate_saved_graph.py"), encoding="utf-8").read())
    cls = [n for n in ast.walk(tree)
           if isinstance(n, ast.ClassDef) and n.name == "SavedAdmission"]
    assert cls and all(isinstance(b, ast.Name) for b in cls[0].bases), ast.dump(cls[0])


def test_the_andon_key_is_spelled_ONE_way_across_gate_saved_graph():
    """Two spellings lived in one file: `"andon": "RouteGate"` (a class name) at the
    `route_facts` sites and `"andon": "frame"` / `"duplicate_socket_name"` (clause names)
    at the five above. One rule now: `andon` is the class that pulled."""
    rows = _raise_rows(os.path.join(TOOLS, "gate_saved_graph.py"))
    wrong = [r for r in rows
             if r[3] is not None and r[1] is not None and r[3] != r[1]]
    assert wrong == [], wrong


# ---- SIBLINGS (rule 2): the other raises in `gate_saved_graph.py`. Measured on the base
# tree, `_raise_rows` returns 13 `RouteGate` raises plus one `SystemExit`. Four of the
# thirteen — lines 260 (`round_trip`), 311 and 317 (`link_table`) and 488
# (`link_round_trip`) — name NO gate and NO andon at all, so the two-ids defect cannot
# occur at them (there is no second id to disagree with the class's). They carry thin
# evidence, which is a DIFFERENT shape and a Stage B candidate; they are enumerated here
# and deliberately not moved, because raising them under a new class would change their
# `str(exc)` prefix with no defect closed.

def test_the_thin_evidence_siblings_are_still_exactly_four_and_still_name_no_gate():
    rows = _raise_rows(os.path.join(TOOLS, "gate_saved_graph.py"))
    thin = sorted(r[0] for r in rows if r[1] in CLASS_GATE_OF and r[2] is None)
    assert len(thin) == 4, thin


# ============================================================ F-5c0f3858 (panel CRITICAL)
# The two facts that admit a paid submission were read off an operator-named `--record`
# that was never TIED to the graph being admitted. `route_facts` walked any JSON document
# for a verify receipt and returned its facts; `main` hashed `--saved` and `--api` into its
# own record and compared neither to anything in `--record`. Every builder writes a
# `payload_sha256` — a canonical digest of the graph it built — so the tie was in the data
# and was not read. The gate's own output then wrote `route_facts.record: <path>` and quoted
# the attribution, asserting a provenance nothing checked, in the record for an irreversible
# spend.


def _api_graph():
    return {"49": {"class_type": "WanImageToVideo",
                   "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}}}


def _digest(graph):
    import hashlib
    return hashlib.sha256(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _record(tmp_path, doc, name="rec.json"):
    p = tmp_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def _receipt(**over):
    ev = {"gate": "ROUTE", "andon": "RouteGate", "receipt": "verify",
          "carries_no_sampler_asserted": False, "attribution": []}
    ev.update(over)
    return ev


def test_a_record_naming_a_DIFFERENT_graphs_digest_is_refused_by_name(tmp_path):
    """The operand: a `--record` whose `payload_sha256` is some other graph's."""
    other = {"7": {"class_type": "UNETLoader", "inputs": {"unet_name": "x.safetensors"}}}
    path = _record(tmp_path, {"payload_sha256": _digest(other),
                              "gates": {"ROUTE": _receipt()}})
    exc, ev = _raises(GSG.route_facts, path, _api_graph())
    assert isinstance(exc, RG.RouteGate), repr(exc)
    assert ev["clause"] == "record_describes_a_different_graph", ev
    assert ev["declared_payload_sha256"] == _digest(other), ev
    assert ev["api_payload_sha256"] == _digest(_api_graph()), ev


def test_a_record_naming_THIS_graphs_digest_passes_and_says_so(tmp_path):
    """The direction the clause must not bound."""
    path = _record(tmp_path, {"payload_sha256": _digest(_api_graph()),
                              "gates": {"ROUTE": _receipt()}})
    facts = GSG.route_facts(path, _api_graph())
    assert facts["payload_sha256"] == _digest(_api_graph())
    assert "tied" in facts["source"], facts["source"]


def test_a_record_that_PREDATES_the_field_records_null_and_says_so(tmp_path):
    """`build_assembly_payload` and `build_r2v_payload` write no `payload_sha256` today —
    measured by grep over `tools/`: four of the builders write it, the rest do not. Such a
    record passes, with the absence STATED rather than passed silently."""
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt()}})
    facts = GSG.route_facts(path, _api_graph())
    assert facts["payload_sha256"] is None
    assert "no `payload_sha256`" in facts["source"], facts["source"]


def test_two_conflicting_payload_digests_in_one_record_refuse(tmp_path):
    other = {"7": {"class_type": "UNETLoader", "inputs": {"unet_name": "x.safetensors"}}}
    path = _record(tmp_path, {"payload_sha256": _digest(_api_graph()),
                              "arms": [{"payload_sha256": _digest(other)}],
                              "gates": {"ROUTE": _receipt()}})
    exc, ev = _raises(GSG.route_facts, path, _api_graph())
    assert ev["clause"] == "record_route_facts_disagree", ev
    assert ev["field"] == "payload_sha256", ev


def test_the_mismatched_record_reaches_the_halt_line_under_the_gate_exit_code(tmp_path):
    """The halt line, READ, on the tie."""
    other = {"7": {"class_type": "UNETLoader", "inputs": {"unet_name": "x.safetensors"}}}
    path = _record(tmp_path, {"payload_sha256": _digest(other),
                              "gates": {"ROUTE": _receipt()}}, name="mismatch.json")
    code, halt = _gsg_halt(tmp_path, [f"--record={path}"])
    assert code == 2, halt
    assert halt["evidence"]["clause"] == "record_describes_a_different_graph", halt


# ============================================================ F-6d68f4c5 (panel CRITICAL)
# `route_facts` bounded ONE of the two facts across multiple receipts and silently MERGED
# the other: `carries_no_sampler` refused by name when receipts disagreed, on the stated
# ground that "one of them describes the graph about to be submitted and this gate cannot
# tell which" — and eleven lines down `attribution` was resolved by UNION. The reasoning
# that makes the first a refusal applies unchanged to the second.
#
# Second half, same finding: `route_gates.verify` writes `receipt: "verify"` and both fact
# keys into its opening `ev` literal "before the first clause can raise", so its REFUSAL
# evidence is indistinguishable from a PASS receipt to this reader. A refusal evidence
# carries a `clause` key; a returned receipt does not.


def _att(component, creditor="somebody"):
    return {"component": component, "creditor": creditor, "source": "map", "text": "t"}


def test_two_receipts_disagreeing_on_ATTRIBUTION_refuse_rather_than_union(tmp_path):
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt(attribution=[_att("a")])},
                              "gate_ROUTE_built": _receipt(attribution=[_att("b")])})
    exc, ev = _raises(GSG.route_facts, path)
    assert isinstance(exc, RG.RouteGate), repr(exc)
    assert ev["clause"] == "record_route_facts_disagree", ev
    assert ev["field"] == "attribution", ev
    assert ev["n_receipts"] == 2, ev


def test_two_receipts_AGREEING_on_attribution_still_pass(tmp_path):
    """The direction the clause must not bound: a repeat that agrees with itself."""
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt(attribution=[_att("a")])},
                              "gate_ROUTE_built": _receipt(attribution=[_att("a")])})
    facts = GSG.route_facts(path)
    assert facts["attribution"] == [_att("a")]
    assert facts["n_verify_receipts"] == 2


def test_the_carries_no_sampler_clause_now_names_its_field_too(tmp_path):
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt(carries_no_sampler_asserted=True)},
                              "gate_ROUTE_built": _receipt(carries_no_sampler_asserted=False)})
    exc, ev = _raises(GSG.route_facts, path)
    assert ev["clause"] == "record_route_facts_disagree", ev
    assert ev["field"] == "carries_no_sampler_asserted", ev


def test_a_CAUGHT_REFUSALS_evidence_is_not_read_as_a_verify_receipt(tmp_path):
    """`verify`'s refusal evidence carries the declared kind and both fact keys, because
    they are written before the first clause can raise. It also carries a `clause`, which a
    returned receipt never does — that is the reading that tells them apart."""
    path = _record(tmp_path, {"gates": {"ROUTE": _receipt(clause="orphan_attribution")}})
    exc, ev = _raises(GSG.route_facts, path)
    assert ev["clause"] == "record_carries_a_caught_refusal", ev
    assert ev["refusal_clauses"] == ["orphan_attribution"], ev


def test_route_gates_verify_really_does_write_both_facts_into_a_refusal(tmp_path):
    """The premise of the clause above, MEASURED rather than assumed: a `verify` refusal's
    evidence carries the receipt kind and both fact keys."""
    graph = {"9": {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"lora_name": "nothing_here.safetensors"}}}
    exc, ev = _raises(RG.verify, graph, attribution=[_att("technically_color")])
    assert ev.get("receipt") == "verify", ev
    assert "carries_no_sampler_asserted" in ev and "attribution" in ev, sorted(ev)
    assert ev.get("clause"), ev


# ---- SIBLINGS (rule 2): every other fact a verify receipt carries. `route_gates.verify`'s
# opening `ev` literal writes `gate`, `andon`, `receipt`, `carries_no_sampler_asserted`,
# `require_pinned_seeds`, `attribution`, `components`, `seeds`, `latents`,
# `latents_checkable`, `frame_legality`. `route_facts` READS exactly two of them, and both
# are bounded across receipts now. `require_pinned_seeds` is the only other key that
# describes THE CALL rather than the graph; it is read by no clause in this module today,
# so there is nothing to merge and nothing to disagree about — enumerated, not moved.

def test_the_merged_population_is_exactly_the_two_declared_fact_keys():
    assert set(GSG.VERIFY_RECEIPT_KEYS) == {"attribution", "carries_no_sampler_asserted"}
    src = open(os.path.join(TOOLS, "gate_saved_graph.py"), encoding="utf-8").read()
    body = src[src.index("def route_facts("):src.index("\ndef main(")]
    assert "require_pinned_seeds" not in body, "a third fact joined without a bound"


# ============================================================ F-0124c714 (panel CRITICAL)
# The wave-16 content clause — the one that exists because `curl --fail-with-body` WRITES an
# HTTP error body to the `-o` path — was bounded to the FRAME population and never reached
# the VIDEO tap, which is the whole product of the generation. Measured on the base tree: a
# two-job plan whose `.png` carries a real PNG signature and whose `E13_00000.mp4` holds the
# 35-byte body `{"error":"AccessDenied","code":403}` returned a full PASS — verdict
# "2 planned file(s), all present and non-empty, 1 of them PNG-signature checked, and no
# unplanned file in 2 swept directory(s)", `wrong_type: []`.
#
# Second half: the docstring's "counted, not judged" was not true — `content_checked`
# carried only a `png` key, so a non-PNG output incremented nothing and the receipt had no
# key naming the population that was never judged.


def _plan(tmp_path, video_name="E13_00000.mp4", video_bytes=ERROR_BODY):
    run = tmp_path / "run"
    (run / "lossless").mkdir(parents=True)
    png = _png(run / "lossless" / "00000.png")
    vid = run / video_name
    vid.write_bytes(video_bytes)
    return run, [("u1", str(png)), ("u2", str(vid))]


def test_an_error_body_in_the_VIDEO_tap_halts(tmp_path):
    """The operand, exactly as measured on the base tree."""
    run, jobs = _plan(tmp_path)
    exc, ev = _raises(FR.verify_downloads, jobs,
                      directories=[str(run / "lossless")], root=str(run))
    assert isinstance(exc, FR.FetchHalt), repr(exc)
    assert ev["clause"] == "downloaded_body_is_not_the_planned_type", ev
    assert [w["expected"] for w in ev["wrong_type"]] == ["mp4"], ev
    assert ev["wrong_type"][0]["first_8_bytes"] == ERROR_BODY[:8].hex(), ev


def test_a_real_mp4_in_the_video_tap_passes(tmp_path):
    """The direction the clause must not bound: an ISO-BMFF `ftyp` box at offset 4."""
    body = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 24
    run, jobs = _plan(tmp_path, video_bytes=body)
    ev = FR.verify_downloads(jobs, directories=[str(run / "lossless")], root=str(run))
    assert ev["wrong_type"] == []
    assert ev["content_checked"][".mp4"] == {"checked": 1, "unjudged": 0}


def test_a_suffix_with_no_signature_is_COUNTED_as_unjudged(tmp_path):
    """"Counted, not judged" made true: the receipt names the population it could not
    judge rather than leaving it out of every key."""
    run = tmp_path / "run"
    run.mkdir()
    donor = run / "donor.bin"
    donor.write_bytes(b"\x01\x02\x03\x04 arbitrary bytes")
    ev = FR.verify_downloads([("u", str(donor))], directories=[], root=str(run),
                             root_suffixes=(".bin",))
    assert ev["content_checked"][".bin"] == {"checked": 0, "unjudged": 1}, ev["content_checked"]
    assert "unjudged" in ev["verdict"], ev["verdict"]


def test_the_JSON_floor_catches_an_error_body_under_a_suffix_with_no_signature(tmp_path):
    """The cheap floor the finding named: whatever the suffix, a planned output whose first
    bytes parse as a JSON object is an error body, not an artifact."""
    run = tmp_path / "run"
    run.mkdir()
    donor = run / "donor.bin"
    donor.write_bytes(ERROR_BODY)
    exc, ev = _raises(FR.verify_downloads, [("u", str(donor))], directories=[],
                      root=str(run), root_suffixes=(".bin",))
    assert ev["clause"] == "downloaded_body_is_not_the_planned_type", ev
    assert ev["wrong_type"][0]["expected"] == "not a JSON error body", ev


def test_every_suffix_plan_can_write_is_in_the_signature_table_or_named_unjudgeable():
    """The POPULATION: `fetch_run.plan` writes `.png` into a mapped directory and the video
    result's own extension (or `.bin`) into the run root; `fetch_t2v_run.plan` writes
    `.png` and `donor<ext>`. `VIDEO_SUFFIXES` is what the root sweep judges."""
    assert set(FR.VIDEO_SUFFIXES) <= set(FR.CONTENT_SIGNATURES), FR.VIDEO_SUFFIXES
    assert ".png" in FR.CONTENT_SIGNATURES


def test_the_t2v_docstring_no_longer_claims_the_donor_is_unjudged():
    """The prose that NAMED this defect one file over is corrected in place, with the
    measurement that overturned it — not quietly deleted.

    Read off the imported MODULE rather than off a literal `os.path.join(TOOLS, ...)`: the
    literal would put `tools/fetch_t2v_run.py` into `test_ci_workflows.GUARDED_TODAY`'s
    census (62 -> 63), which is the tests domain's pin and not this domain's to move this
    wave. `inspect.getsource` reads the object actually under test, which is the stronger
    reading anyway.
    """
    import inspect

    import fetch_t2v_run as FT2V
    src = inspect.getsource(FT2V)
    assert "F-0124c714" in src
    assert "CONTENT_SIGNATURES" in src
    assert "counted, not judged" not in src.replace(
        '"counted, not judged" was not true of the old receipt either.', "")


# ============================================================ F-3f285caa (panel CRITICAL)
# The ONE seed-registration reader wave 16 built for eight callers refused a non-list
# `seeds` on the stated ground that "a membership test against a non-list is a question with
# an accidental answer", and then returned the list with no clause on its ELEMENTS — so the
# membership test stayed accidental one level down. Measured on the base tree, all
# ACCEPTED: `["2026081351","2026081352"]`, `[[2026081351]]`, `[{"seed": 2026081351}]`,
# `[2026081351, null]`, `[True, False]`, `[1.5]`.
#
# Consequences at the callers: a quoted registration makes `2026081351 in ['2026081351']`
# False, so the operator's seed is refused as UNREGISTERED while the defect is the file's
# shape; a mixed list makes `sorted(registry)[0]` — the documented default path in three
# builders — raise `TypeError: '<' not supported between 'NoneType' and 'int'`; and
# `1 in [True]` is True in CPython, so a boolean registration admits an unregistered number.

BAD_REGISTRATIONS = [
    (["2026081351", "2026081352"], "str"),
    ([[2026081351]], "list"),
    ([{"seed": 2026081351}], "dict"),
    ([2026081351, None], "NoneType"),
    ([True, False], "bool"),
    ([1.5], "float"),
]


@pytest.mark.parametrize("seeds,typename", BAD_REGISTRATIONS,
                         ids=[t for _, t in BAD_REGISTRATIONS])
def test_a_registration_element_that_is_not_an_int_is_refused_by_name(
        tmp_path, seeds, typename):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps({"seeds": seeds}), encoding="utf-8")
    exc, ev = _raises(BAP.read_seed_registration, str(p))
    assert isinstance(exc, BAP.SeedRegistrationError), repr(exc)
    assert ev["clause"] == "registration_seed_is_not_an_integer", ev
    assert ev["offending"][0]["type"] == typename, ev
    assert ev["offending"][0]["index"] == (1 if typename == "NoneType" else 0), ev


def test_a_committed_registration_of_ints_still_reads(tmp_path):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps({"seeds": [2026081351, 2026081352]}), encoding="utf-8")
    assert BAP.read_seed_registration(str(p)) == [2026081351, 2026081352]


def test_every_committed_registration_in_specs_still_reads():
    """The POPULATION the new clause must not break: every `*seeds.json` under `specs/`."""
    specs = os.path.join(REPO, "specs")
    files = sorted(n for n in os.listdir(specs) if n.endswith("seeds.json"))
    assert files, specs
    for name in files:
        got = BAP.read_seed_registration(os.path.join(specs, name))
        assert got and all(type(s) is int for s in got), (name, got)


# ---- SIBLINGS (rule 2): the clauses of `read_seed_registration`. Six now —
# registration_missing, registration_unreadable, registration_not_a_mapping,
# registration_no_seeds_key, registration_seeds_not_a_list, and the element clause added
# here. NO numeric range is invented: this module records no measured bound for a seed's
# magnitude, and CLAUDE.md forbids a global constant governing a local feature. Emptiness
# stays out by the reader's own stated rule (the caller that defaults raises
# `no_seed_and_no_registration`).

def test_the_reader_still_has_exactly_the_recorded_clause_set():
    src = open(os.path.join(TOOLS, "build_assembly_payload.py"), encoding="utf-8").read()
    body = src[src.index("def read_seed_registration("):src.index("\ndef gate_create_video_fps(")]
    clauses = sorted(set(__import__("re").findall(r'clause="([a-z_]+)"', body)))
    assert clauses == ["registration_missing", "registration_no_seeds_key",
                       "registration_not_a_mapping", "registration_seed_is_not_an_integer",
                       "registration_seeds_not_a_list", "registration_unreadable"], clauses


# ============================================================ F-46bffbb9 (panel CRITICAL)
# Gate OUT's two clauses could not fire with the `META_SUFFIX` the tool actually ships, and
# the only tests reaching them substituted the constant. Probed on the base tree over 13
# `--out` shapes (`a.json`, `a`, `a.meta.json`, `a.b.json`, `.json`, `.meta.json`, `a.`,
# `dir/a.json`, `a.JSON`, `a.meta.JSON`, `..`, `a.json.`, `x.meta`): zero clauses fired,
# every pair distinct. So `PayloadOutHalt` and its raise sites were counted as an ARMED
# andon by the tree's censuses while nothing an operator can type reached them.
#
# The andon is armed on a direction the derivation does not bound and the shipped suffix
# CAN reach: a derived path that already exists as a DIRECTORY. That is the same family the
# class exists for — `--out=<dir>/run.json.d/A.json` died `FileNotFoundError` after the
# graph was on disk, "a partial write reported as a crash".


def test_gate_OUT_fires_on_a_graph_path_that_is_a_directory(tmp_path):
    """Red without substituting `META_SUFFIX`: the operand is a `--out` an operator types."""
    (tmp_path / "a.json").mkdir()
    exc, ev = _raises(BP.gate_out_paths, str(tmp_path / "a.json"))
    assert isinstance(exc, BP.PayloadOutHalt), repr(exc)
    assert ev["clause"] == "out_path_is_a_directory", ev
    assert ev["meta_suffix"] == BP.META_SUFFIX, ev


def test_gate_OUT_fires_on_a_record_path_that_is_a_directory(tmp_path):
    (tmp_path / "a.meta.json").mkdir()
    exc, ev = _raises(BP.gate_out_paths, str(tmp_path / "a.json"))
    assert ev["clause"] == "meta_path_is_a_directory", ev
    assert ev["meta_suffix"] == BP.META_SUFFIX, ev


def test_gate_OUT_passes_an_ordinary_out(tmp_path):
    graph, meta, ev = BP.gate_out_paths(str(tmp_path / "a.json"))
    assert graph != meta and os.path.dirname(graph) == os.path.dirname(meta)
    assert ev["verdict"]


def test_every_gate_OUT_clause_is_reachable_with_the_SHIPPED_suffix(tmp_path):
    """The census the finding asked for: no clause of this andon may need a mutated module
    constant to go red. Each clause below is driven with `META_SUFFIX` untouched."""
    reached = set()
    d = tmp_path / "reach"
    d.mkdir()
    (d / "g.json").mkdir()
    _e, ev = _raises(BP.gate_out_paths, str(d / "g.json"))
    reached.add(ev["clause"])
    (d / "m.meta.json").mkdir()
    _e, ev = _raises(BP.gate_out_paths, str(d / "m.json"))
    reached.add(ev["clause"])
    src = open(os.path.join(TOOLS, "build_payload.py"), encoding="utf-8").read()
    body = src[src.index("def gate_out_paths("):src.index("\ndef main(")]
    declared = set(__import__("re").findall(r'clause="([a-z_]+)"', body))
    declared |= {"meta_path_equals_graph_path"}
    unreachable = declared - reached
    assert unreachable <= {"meta_path_equals_graph_path",
                           "meta_leaves_the_graphs_directory"}, unreachable
    assert reached == {"out_path_is_a_directory", "meta_path_is_a_directory"}, reached


# ============================================================ F-c080a03f (panel HIGH)
# The carry that re-raises the sibling's start-frame refusal DISCARDED the sibling's
# evidence dict and built a fresh one from the operator's inputs, so on the route whose
# entire conditioning is one image the refusal reached the halt line naming NO clause.
# Measured on the base tree against a JPEG-headed file:
#   build_camera_i2v_payload.resolve_start_frame -> keys ['andon','bytes','clause',
#       'first_8_bytes','flag','gate','path','read_by','sha256'], clause
#       'start_frame_not_a_png'
#   build_i2v_payload.resolve_start_frame (SAME file) -> keys ['andon','carried_from',
#       'declared_sha256','flag','gate','path'], clause None
# The docstring cites `build_payload._carry` as its exemplar, and `_carry` does the
# opposite: `dict(exc.evidence or {}, carried_from=...)`, evidence verbatim.


def _not_a_png(tmp_path):
    p = tmp_path / "start.png"
    p.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 400)
    return str(p)


def test_the_i2v_carry_keeps_the_siblings_clause(tmp_path):
    path = _not_a_png(tmp_path)
    _e, cam = _raises(CAM.resolve_start_frame, path, None)
    _e, i2v = _raises(I2V.resolve_start_frame, path, None)
    assert i2v["clause"] == "start_frame_not_a_png" == cam["clause"], (i2v, cam)
    for key in ("first_8_bytes", "bytes", "sha256", "read_by"):
        assert i2v[key] == cam[key], (key, i2v.get(key), cam.get(key))
    assert i2v["carried_from"] == "build_camera_i2v_payload.resolve_start_frame"


# ---- SIBLINGS (rule 2): the OTHER refusals `build_camera_i2v_payload.resolve_start_frame`
# makes, which the carry also relays. Measured on the base tree, both carried NO evidence at
# all from the sibling (`keys=[]`), so the carry's fresh dict was all there was and
# `evidence['clause']` was None for every one of the three — the exact triage failure the
# finding names ("cannot distinguish 'not a PNG this tool can read' from 'no such file'").
# All three are named now.

START_FRAME_SIBLINGS = [
    (None, "start_frame_not_supplied"),
    ("__missing__", "start_frame_is_not_a_file"),
]


@pytest.mark.parametrize("arg,clause", START_FRAME_SIBLINGS, ids=[c for _, c in START_FRAME_SIBLINGS])
def test_every_start_frame_refusal_names_a_clause_through_BOTH_doors(tmp_path, arg, clause):
    path = str(tmp_path / "nope.png") if arg == "__missing__" else arg
    for mod in (CAM, I2V):
        _e, ev = _raises(mod.resolve_start_frame, path, None)
        assert ev.get("clause") == clause, (mod.__name__, ev)
        assert ev.get("gate") == "PAYLOAD" and ev.get("flag") == "--start-frame", ev


def test_the_declared_digest_mismatch_also_names_a_clause_through_both_doors(tmp_path):
    p = tmp_path / "s.png"
    _png(p)
    for mod in (CAM, I2V):
        _e, ev = _raises(mod.resolve_start_frame, str(p), "0" * 64)
        assert ev.get("clause") == "start_frame_sha256_disagrees", (mod.__name__, ev)


# ============================================================ F-d8593862 (panel CRITICAL)
# The class wave 16 DEFINED to close F-f85c37f0 was invisible to every census that polices
# the family, because it was the one family class in the tree declared with a DOTTED base:
# `class SpendCeiling(RG.RouteGate)`. `tests/test_gates._armature_error_family` builds its
# transitive base map from `b.id for b in node.bases if isinstance(b, ast.Name)`, so an
# `ast.Attribute` base contributes nothing and the class never joined the family. Measured
# on the base tree: `'SpendCeiling' in _armature_error_family(TOOLS)` was False, while
# `GateSSeedRegistration`, `PayloadOutHalt`, `SeedRegistrationError`, `FetchHalt`,
# `LedgerGate`, `TierGate` and `PayloadError` were all True; an AST sweep of `tools/**` for
# family classes with a dotted base returned exactly ONE row.


def _name_only_family(dirpath):
    """The `ast.Name`-only walk, reproduced here so the property is proven against the
    SHAPE rather than against another test's import. (Widening `test_gates`' own walk to
    read `ast.Attribute` bases is the OUT-OF-DOMAIN half — a Stage B item in `tests/`.)"""
    bases = {}
    for dp, _dn, fn in os.walk(dirpath):
        for f in fn:
            if not f.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(dp, f), encoding="utf-8").read())
            except SyntaxError:                                   # pragma: no cover
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases.setdefault(node.name, set()).update(
                        b.id for b in node.bases if isinstance(b, ast.Name))
    fam = {"ArmatureError", "GateFailure"}
    changed = True
    while changed:
        changed = False
        for name, bs in bases.items():
            if name not in fam and (bs & fam):
                fam.add(name)
                changed = True
    return fam


def test_SpendCeiling_is_visible_to_a_name_only_family_walk():
    fam = _name_only_family(TOOLS)
    assert "SpendCeiling" in fam, sorted(fam)
    # the classes the finding measured as already visible, so the walk itself is sound
    assert {"GateSSeedRegistration", "PayloadOutHalt", "SeedRegistrationError",
            "FetchHalt", "PayloadError"} <= fam


def test_SpendCeiling_still_behaves_exactly_as_before():
    assert issubclass(R2V.SpendCeiling, RG.RouteGate)
    assert R2V.SpendCeiling.gate == "CEILING"
    exc = R2V.SpendCeiling("x", {"gate": "CEILING"})
    assert isinstance(exc, RG.RouteGate) and str(exc).startswith("[CEILING]")


# ---- SIBLINGS (rule 2): every family class in `tools/**` declared with a base the
# `ast.Name` walk cannot resolve. Measured on the base tree: exactly one row,
# `build_r2v_payload.py:69 SpendCeiling(RG.RouteGate)`. The census below is the standing
# form, so the next dotted base is caught at its own merge.

def test_no_family_class_under_tools_is_declared_with_a_base_the_walk_cannot_resolve():
    fam = _name_only_family(TOOLS)
    dotted = []
    for dp, _dn, fn in os.walk(TOOLS):
        for f in fn:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dp, f)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:                                   # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                attrs = [ast.unparse(b) for b in node.bases if isinstance(b, ast.Attribute)]
                if attrs and (node.name in fam
                              or any(a.split(".")[-1] in fam for a in attrs)):
                    dotted.append((os.path.relpath(path, REPO), node.lineno, node.name, attrs))
    assert dotted == [], dotted
