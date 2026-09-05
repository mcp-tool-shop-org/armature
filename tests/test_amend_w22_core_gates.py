"""Wave 22 (core-gates, Stage B amend #1): the tables nothing checked, the declarations
nothing counted, the containers nothing read, and the rows that could not name their node.

The wave-21 auditors measured, on `e8263a3`, that four gate surfaces state a contract in
prose and enforce none of it, and that three row families cannot say WHICH node they are
about:

  * **F-682ce228** `canon_census.CENSUS` is a hand-edited table whose docstring states the
    contract the spend helpers rest on, and no clause anywhere checks a row against it: a
    misspelled `surface:` key made `require_canon`'s `clause: checkbox` refusal
    inoperative and returned `UNGATED` for a subject that HAS a ratified surfaces file; an
    identity-only row with no `reason` returned `UNGATED` with `reason: None`; a row that
    is not a mapping raised a bare `AttributeError` from both `require_canon` and
    `resolve`, bypassing the halt contract's exit-2 branch.
  * **F-0d33958f** `normalise_graph` resolves a document declaring TWO graphs by
    wrapper-key order and records nowhere that a second declaration existed — the shape a
    ComfyUI queue/history record carries — so `verify` returned a green verdict on an API
    half while the save half loaded `causvid_x.safetensors` (BANNED, CC-BY-NC).
  * **F-ddfb61e6** an API-format entry that declares its OWN `widgets_values` has it
    DISCARDED: `_walk_nodes` synthesises widgets from `inputs.values()` alone and
    `NODE_CONTAINERS[True]` records only `('inputs', dict)`, so the BANNED file spelled
    there is neither read nor refused and `verify` RETURNED "0 of 1 component(s)
    classified, ... 1 frame(s) checked and generator-legal".
  * **F-715ecaab** `normalise_spec` validates the keys it knows and ACCEPTS every key it
    does not, at every level, and `dump_spec` writes them back into the provenance spec —
    so `camera.fov_degrees` rides beside the `fov_deg` the solvers read.
  * **F-2fa07723 / F-94cc5fe1** `hosted_enums`' 4-tuple and Gate PAIR's
    `conditioning_nodes` rows are the two row families that discard the level the walk
    yields, so a refusal on a tier that bills per node reads `node 6; node 6`.
  * **F-f2808386** five of the six functions that index a widget list positionally call a
    shift andon in their own body; `gate_s_registration` calls none, and its coverage is a
    comment plus a hand-kept dict two functions away.

Every test here is written against the operand the wave-21 auditor measured, and against
that operand's enumerated siblings. `family:` lines ride the output record.
"""

import json
import math
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from armature_core import canon as C                       # noqa: E402
from armature_core import canon_census as CC               # noqa: E402
from armature_core import cli                              # noqa: E402
from armature_core import donor_gate as DG                 # noqa: E402
from armature_core import route_gates as RG                # noqa: E402
from armature_core import shotspec as SS                   # noqa: E402
from armature_core.errors import GateCanon, SpecError      # noqa: E402

BANNED = "causvid_x.safetensors"
BASE = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"


# ---------------------------------------------------------------------------
# F-682ce228 — `canon_census.CENSUS` is checked against the contract its own
# docstring states, at import and again at run time.
# ---------------------------------------------------------------------------

#: The six malformed shapes, enumerated. The auditor measured the first three on
#: `e8263a3`; the other three are their siblings in the same table position — the row
#: whose `surfaces` is not a path at all, the empty path, and the subject key that is not
#: a name. Every one of them is what "adding a subject is a data change here" admits.
MALFORMED_ROWS = [
    ("not_a_mapping", {"NEWCHAR": "newchar.json"}, "row_is_not_a_mapping"),
    ("misspelled_key", {"NEWCHAR": {"surface": "newchar.json", "reason": "typo"}},
     "unknown_census_key"),
    ("identity_only_without_reason", {"NEWCHAR": {"surfaces": None}},
     "hole_without_a_reason"),
    ("identity_only_blank_reason", {"NEWCHAR": {"surfaces": None, "reason": "  "}},
     "hole_without_a_reason"),
    ("surfaces_not_a_path", {"NEWCHAR": {"surfaces": 7}}, "surfaces_is_not_a_path"),
    ("surfaces_empty_path", {"NEWCHAR": {"surfaces": ""}}, "surfaces_is_not_a_path"),
]


@pytest.mark.parametrize("label,table,clause",
                         MALFORMED_ROWS, ids=[m[0] for m in MALFORMED_ROWS])
def test_a_malformed_census_row_refuses_by_name(label, table, clause):
    """RED on base: `gate_census_table` did not exist. The misspelled-key row returned
    `{'verdict': 'UNGATED', 'clause': 'escape'}` from `require_canon(no_canon=True)` for a
    subject that HAS a surfaces file — the `clause: 'checkbox'` refusal inoperative
    because `rec.get('surfaces')` read None — and the non-mapping row raised a bare
    `AttributeError`, which is not an `ArmatureError`."""
    with pytest.raises(GateCanon) as exc:
        CC.gate_census_table(table)
    ev = exc.value.evidence
    assert ev["clause"] == clause
    assert ev["gate"] == "CANON" and ev["andon"] == "GateCanon"
    assert ev["subject"] == "NEWCHAR"


def test_the_table_itself_and_its_keys_are_bounded_too():
    """The two shapes above the row: a census that is not a mapping at all, and a subject
    key that is not a name. A table read with `.get` answers None to every question."""
    with pytest.raises(GateCanon) as exc:
        CC.gate_census_table([("NEWCHAR", {"surfaces": None, "reason": "x"})])
    assert exc.value.evidence["clause"] == "census_is_not_a_mapping"
    with pytest.raises(GateCanon) as exc2:
        CC.gate_census_table({7: {"surfaces": None, "reason": "x"}})
    assert exc2.value.evidence["clause"] == "subject_is_not_a_name"


def test_the_shipped_census_passes_its_own_gate_and_the_gate_runs_at_import():
    """The three rows in the tree today are well formed — this is the guard direction
    unbounded, not a live escape — and the andon runs at import time for the reason
    `route_gates.gate_alias_table()` does: a table mirroring a document loses rows when
    the document is re-fetched."""
    assert CC.gate_census_table() is CC.CENSUS
    src = open(os.path.join(TOOLS, "armature_core", "canon_census.py"),
               encoding="utf-8").read()
    assert "\ngate_census_table()\n" in src, (
        "the import-time call is the half a run-time-only check does not have")


@pytest.mark.parametrize("label,table,clause",
                         MALFORMED_ROWS, ids=[m[0] for m in MALFORMED_ROWS])
def test_the_spend_helpers_refuse_a_table_mutated_at_run_time(label, table, clause):
    """The auditor's own operand: the three readings were taken THROUGH `require_canon`'s
    `census=` parameter, so the import-time andon alone would not have caught them.
    `resolve` is the sibling — it raised the same bare `AttributeError` on the non-mapping
    row — and `gate_write` forwards into `require_canon`."""
    for call in (
        lambda: C.require_canon("NEWCHAR", "a prompt", no_canon=True, census=table),
        lambda: C.require_canon("NEWCHAR", "a prompt", census=table),
        lambda: C.gate_write("NEWCHAR", "a prompt", no_canon=True, census=table),
        lambda: C.resolve("NEWCHAR", census=table),
    ):
        with pytest.raises(GateCanon) as exc:
            call()
        assert exc.value.evidence["clause"] == clause


def test_the_misspelled_row_no_longer_reaches_ungated():
    """The measured consequence, stated as its own test: a subject that HAS a ratified
    surfaces file used to walk out of `--no-canon` with `verdict: UNGATED` because the
    key that carries the path was spelled `surface`."""
    table = {"NEWCHAR": {"surface": "newchar.json", "reason": "typo"}}
    with pytest.raises(GateCanon) as exc:
        C.require_canon("NEWCHAR", "a prompt", no_canon=True, census=table)
    assert exc.value.evidence["clause"] == "unknown_census_key"
    assert exc.value.evidence["key"] == "surface"
    assert "surfaces" in exc.value.evidence["known_keys"]


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _halt_line(argv, prefix, tool, expect_code=2):
    """Drive a tool's REAL `__main__` block in a subprocess and READ the halt record.

    Wave-18 rule 4: the fix is not landed until the printed line has been read — the
    class, the clause, the evidence keys. Returns the parsed sentinel payload.
    """
    import subprocess

    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "tools"))
    proc = subprocess.run([sys.executable, os.path.join(REPO, "tools", tool)] + argv,
                          capture_output=True, text=True, env=env, cwd=REPO)
    assert proc.returncode == expect_code, proc.stdout + proc.stderr
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith(prefix + " ")]
    assert len(halts) == 1, proc.stdout + proc.stderr
    return json.loads(halts[0][len(prefix) + 1:])


def test_the_canon_census_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ, not asserted about in-process (wave-18 rule 4). A malformed
    census handed to `canon_gate.py --census` must leave the process through the
    `CANON_GATE_HALT` sentinel with exit 2, carrying the clause — not as an
    `AttributeError` traceback at exit 1, which is what a non-mapping row produced."""
    census = tmp_path / "bad-census.json"
    census.write_text(json.dumps({"NEWCHAR": "newchar.json"}), encoding="utf-8")
    payload = _halt_line(["--census", str(census), "resolve", "--subject", "NEWCHAR"],
                         "CANON_GATE_HALT", "canon_gate.py")
    assert payload["error"] == "GateCanon"
    assert payload["evidence"]["clause"] == "row_is_not_a_mapping"
    assert payload["evidence"]["gate"] == "CANON"
    assert payload["evidence"]["subject"] == "NEWCHAR"


# ---------------------------------------------------------------------------
# F-c77f6cce — `out_dir` was a parameter of both spend helpers, forwarded between
# them, and read by neither. It is now a check.
# ---------------------------------------------------------------------------

def test_out_dir_is_read_by_the_gate_that_is_handed_it(tmp_path):
    """RED on base: `grep -n out_dir tools/armature_core/canon.py` returned exactly four
    lines — two signatures, one docstring negative and one forward — and no statement in
    either body read the value, while `tools/canon_gate.py:75` hands it a real directory.
    A parameter is a promise about what a function looks at.

    The check is the one the finding names: a re-run may not write into a HALF-FINISHED
    spend. The negative in the docstring stands — this still never creates the directory."""
    out = tmp_path / "half-finished"
    out.mkdir()
    (out / "payload.json").write_text("{}", encoding="utf-8")
    for call in (C.require_canon, C.gate_write):
        with pytest.raises(GateCanon) as exc:
            call("PERFORMER", "a prompt", no_canon=True, out_dir=str(out))
        ev = exc.value.evidence
        assert ev["clause"] == "out_dir_not_empty"
        assert ev["out_dir"] == str(out)
        assert ev["entries"] == ["payload.json"]


def test_out_dir_none_and_an_absent_or_empty_directory_are_unchanged(tmp_path):
    """The siblings of the operand, enumerated: `out_dir=None` (the shape every test in
    `test_canon.py` uses), a path that does not exist (the shape `canon_gate.py` uses
    before mkdir), and an existing but EMPTY directory — a re-run that got as far as the
    mkdir and no further is not a half-finished spend."""
    empty = tmp_path / "empty"
    empty.mkdir()
    for out in (None, str(tmp_path / "not-yet"), str(empty)):
        ev = C.require_canon("PERFORMER", "a prompt", no_canon=True, out_dir=out)
        assert ev["verdict"] == "UNGATED"
    assert not (tmp_path / "not-yet").exists(), "the gate still creates nothing"


def test_a_file_standing_where_out_dir_should_be_is_refused_by_name(tmp_path):
    """The third shape of the same operand: the path exists and is not a directory at all,
    so `os.listdir` would raise `NotADirectoryError` — not an `ArmatureError`."""
    f = tmp_path / "not-a-dir"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.gate_write("PERFORMER", "a prompt", no_canon=True, out_dir=str(f))
    assert exc.value.evidence["clause"] == "out_dir_is_not_a_directory"


def test_the_out_dir_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ. `canon_gate.py spend --no-canon --subject PERFORMER --out <a
    directory holding a file>` leaves through `CANON_GATE_HALT` at exit 2 with the clause,
    the path and the entries — where on base it printed `[canon] UNGATED: PERFORMER` and
    `CANON_GATE_OK` over a directory already holding another run's payload."""
    out = tmp_path / "half-finished"
    out.mkdir()
    (out / "payload.json").write_text("{}", encoding="utf-8")
    payload = _halt_line(["spend", "--no-canon", "--subject", "PERFORMER",
                          "--prompt", "a prompt", "--out", str(out)],
                         "CANON_GATE_HALT", "canon_gate.py")
    assert payload["error"] == "GateCanon"
    assert payload["evidence"]["clause"] == "out_dir_not_empty"
    assert payload["evidence"]["entries"] == ["payload.json"]


# ---------------------------------------------------------------------------
# F-0d33958f — a document that declares TWO graphs is refused by name rather than
# resolved by wrapper-key order with the second declaration recorded nowhere.
# ---------------------------------------------------------------------------

def _clean_api():
    return {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
            "2": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "control_after_generate": "fixed"}}}


def _banned_save():
    return {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
                      {"id": 4, "type": "LoraLoaderModelOnly",
                       "widgets_values": [BANNED, 1.0]}]}


def _two_declarations():
    """The shape a ComfyUI queue/history record carries: the API half under `prompt`, the
    save-format half under `workflow`."""
    return {"prompt": _clean_api(), "workflow": _banned_save()}


@pytest.mark.parametrize("reader", ["normalise_graph", "is_api_format", "components",
                                    "model_weights", "seeds", "latents", "cameras",
                                    "hosted_enums", "pairing", "ruled_node_classes",
                                    "unrecorded_seed_sources", "api_walk_census"])
def test_two_graph_declarations_refuse_in_every_reader(reader):
    """RED on base: `_shape_of(doc)` returned None, `components(doc)` returned only the
    API half's one weight, and `verify(doc, frame=(832,480,81))` RETURNED the verdict
    "0 of 1 component(s) classified, ... 1 frame(s) checked and generator-legal" with the
    BANNED CC-BY-NC file named nowhere in the receipt and no key naming a second
    declaration. Every reader on the page goes through `normalise_graph`, so the refusal
    is on the loader and the siblings are the enumeration."""
    with pytest.raises(RG.RouteGate) as exc:
        getattr(RG, reader)(_two_declarations())
    ev = exc.value.evidence
    assert ev["clause"] == "multiple_graph_declarations"
    assert ev["declaring_keys"] == ["prompt", "workflow"]
    assert ev["would_have_taken"] == "prompt"
    assert ev["gate"] == "ROUTE" and ev["andon"] == "RouteGate"


def test_the_refusal_does_not_depend_on_dict_order():
    """The tuple `GRAPH_WRAPPER_KEYS` is the selector, not dict order — measured on base by
    reversing the two keys in the document, which changed nothing. Both spellings refuse
    with the same `would_have_taken`."""
    doc = {"workflow": _banned_save(), "prompt": _clean_api()}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(doc, frame=(832, 480, 81))
    assert exc.value.evidence["would_have_taken"] == "prompt"


def test_all_three_wrapper_keys_and_the_lone_declaration_are_the_enumerated_siblings():
    """`GRAPH_WRAPPER_KEYS` is `('prompt', 'workflow_json', 'workflow')`; the pairs are the
    three, and a document declaring exactly ONE is the ordinary envelope wave 6 taught this
    loader to unwrap. A non-mapping under a wrapper key is not a declaration."""
    order = list(RG.GRAPH_WRAPPER_KEYS)
    for a, b in (("prompt", "workflow_json"), ("prompt", "workflow"),
                 ("workflow_json", "workflow")):
        with pytest.raises(RG.RouteGate) as exc:
            RG.normalise_graph({a: _clean_api(), b: _banned_save()})
        assert exc.value.evidence["declaring_keys"] == sorted([a, b], key=order.index)
    for k in RG.GRAPH_WRAPPER_KEYS:
        assert RG.normalise_graph({k: _clean_api()}) == _clean_api()
    # a wrapper key whose value is not a mapping declares nothing
    assert RG.normalise_graph({"prompt": _clean_api(), "workflow": None}) == _clean_api()
    assert RG.normalise_graph({"prompt": _clean_api(), "workflow": []}) == _clean_api()


def test_load_graph_of_a_two_declaration_file_refuses_with_the_path(tmp_path):
    """`load_graph` of the same document written to disk returned a graph equal to the API
    half on base. It now refuses through the loader, and the path rides the evidence."""
    f = tmp_path / "queue-record.json"
    f.write_text(json.dumps(_two_declarations()), encoding="utf-8")
    with pytest.raises(RG.RouteGate) as exc:
        RG.load_graph(str(f))
    assert exc.value.evidence["clause"] == "multiple_graph_declarations"
    assert exc.value.evidence["path"] == str(f)


# ---------------------------------------------------------------------------
# F-ddfb61e6 — an API entry's OWN `widgets_values` is READ, so a value inside it
# cannot sit in a graph no clause examined.
# ---------------------------------------------------------------------------

def _api_with_declared_widgets(widgets):
    return {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
            "2": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "control_after_generate": "fixed"}},
            "3": {"class_type": "LoraLoaderModelOnly", "inputs": {},
                  "widgets_values": widgets}}


def test_an_api_entrys_own_widgets_values_reaches_the_licence_clause():
    """RED on base, the auditor's operand exactly: `components()` named ONLY the
    UNETLoader, `verify(g, frame=(832,480,81))` RETURNED "0 of 1 component(s) classified,
    1 unclassified, ... 1 frame(s) checked and generator-legal", `json.dumps(ev)` contained
    'causvid' zero times, and `walk_census.n_nodes_walked` read 3. `_walk_nodes`
    synthesised the node's widgets from `inputs.values()` alone and `NODE_CONTAINERS[True]`
    recorded only `('inputs', dict)`, so `widgets_values` on an API entry was neither read
    nor refused."""
    g = _api_with_declared_widgets([BANNED, 1.0])
    files = [c["file"] for c in RG.components(g) if c.get("file")]
    assert BANNED in files
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert BANNED in str(exc.value)
    assert "BANNED" in str(exc.value)


def test_the_control_is_the_same_file_spelled_in_the_api_inputs_mapping():
    """The auditor's control, kept as a test so the two spellings are shown to reach the
    same clause rather than assumed to."""
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
         "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": BANNED}}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert BANNED in str(exc.value)


@pytest.mark.parametrize("spelling,wv", [
    ("mapping", {"lora_name": BANNED, "strength_model": 1.0}),
    ("bare string", BANNED),
    ("int", 3),
])
def test_an_api_widgets_values_that_is_not_a_list_refuses_by_name(spelling, wv):
    """The container guard the save-format branch has had since wave 20, on the format
    every builder submits. A mapping yields its KEYS and a string its CHARACTERS, so a
    weight inside either is tested against nothing."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(_api_with_declared_widgets(wv))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["container"] == "widgets_values"
    assert ev["where"] == "api" and ev["node_id"] == "3"
    assert ev["entry_type"] == type(wv).__name__


@pytest.mark.parametrize("reader", ["components", "model_weights", "seeds", "latents",
                                    "cameras", "ruled_node_classes", "pairing",
                                    "unrecorded_seed_sources", "hosted_enums"])
def test_every_node_reader_meets_the_api_container_refusal(reader):
    """Wave-18 rule 2, the same nine readers wave 20 enumerated for the save-format
    container — the guard is on the walk, not in `components`."""
    with pytest.raises(RG.RouteGate) as exc:
        getattr(RG, reader)(_api_with_declared_widgets({"lora_name": BANNED}))
    assert exc.value.evidence["clause"] == "unreadable_node"


def test_the_api_node_containers_table_records_both_containers():
    """The table is the census the walk keys on; a container absent from it is a container
    no clause examines. `inputs` is still a MAPPING in API format and `widgets_values` a
    LIST, which is why the two formats have separate rows."""
    api_row = dict((name, shape) for name, shape, _ in RG.NODE_CONTAINERS[True])
    assert api_row == {"inputs": dict, "widgets_values": list}
    save_row = dict((name, shape) for name, shape, _ in RG.NODE_CONTAINERS[False])
    assert save_row == {"widgets_values": list, "inputs": list}


def _gsg_case(tmp_path, saved_doc=None, api_doc=None):
    """The `gate_saved_graph.py` fixture trio, in the shape `tests/test_gate_saved_graph.py`
    already writes it — one WanAnimateToVideo whose save and API halves agree."""
    d = tmp_path / "in"
    d.mkdir(parents=True)
    saved = saved_doc if saved_doc is not None else {"nodes": [
        {"id": 49, "type": "WanAnimateToVideo", "inputs": [],
         "widgets_values": [832, 480, 81, 1, 5, 0]}]}
    api = api_doc if api_doc is not None else {
        "49": {"class_type": "WanAnimateToVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                          "continue_motion_max_frames": 5, "video_frame_offset": 0}}}
    (d / "g.saved.json").write_text(json.dumps(saved), encoding="utf-8")
    (d / "g.api.json").write_text(json.dumps(api), encoding="utf-8")
    (d / "seeds.json").write_text(json.dumps({"seeds": [1]}), encoding="utf-8")
    return d


def test_the_two_declaration_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ, through the last gate before a paid submission. On base this
    file was unwrapped to its `prompt` half and `SAVED_ADMISSION` continued reading a graph
    the submission may not carry."""
    d = _gsg_case(tmp_path, saved_doc=_two_declarations())
    out = tmp_path / "fresh" / "admission.json"
    payload = _halt_line([f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
                          f"--seeds={d / 'seeds.json'}", f"--out={out}"],
                         "SAVED_ADMISSION_HALT", "gate_saved_graph.py")
    assert payload["error"] == "RouteGate"
    ev = payload["evidence"]
    assert ev["clause"] == "multiple_graph_declarations"
    assert ev["declaring_keys"] == ["prompt", "workflow"]
    assert ev["shapes"] == {"prompt": "api", "workflow": "save"}
    assert not out.parent.exists(), "a refused admission created its output directory"


def _lora_arm_case(tmp_path, widgets):
    d = tmp_path / "in"
    d.mkdir(parents=True)
    (d / "base.api.json").write_text(json.dumps({
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {},
              "widgets_values": widgets}}), encoding="utf-8")
    (d / "reg.json").write_text(json.dumps({"seeds": [7]}), encoding="utf-8")
    return d


def test_an_api_declared_widget_reaches_the_printed_halt_record_both_ways(tmp_path):
    """The halt line READ for both halves of the fix, on the ONE builder whose graph
    arrives as a FILE on disk. On base `--base` carrying either spelling built the payload:
    the licence walk never entered the container.

    LIST -> the value is READ and the licence clause fires (`banned_component_in_base`).
    MAPPING -> the SHAPE is refused (`unreadable_node`, container `widgets_values`)."""
    d = _lora_arm_case(tmp_path, [BANNED, 1.0])
    out = tmp_path / "fresh" / "lora.json"
    read = _halt_line([f"--base={d / 'base.api.json'}", "--arm=T", f"--out={out}",
                       f"--seeds-registry={d / 'reg.json'}", "--seed=7"],
                      "BUILD_LORA_ARM_HALT", "build_lora_arm_payload.py")
    assert read["error"] == "RouteGate"
    assert read["evidence"]["clause"] == "banned_component_in_base"
    assert BANNED.split(".")[0] in read["message"] or "causvid" in read["message"]

    d2 = _lora_arm_case(tmp_path / "second", {"lora_name": BANNED})
    shape = _halt_line([f"--base={d2 / 'base.api.json'}", "--arm=T",
                       f"--out={tmp_path / 'second-out' / 'lora.json'}",
                       f"--seeds-registry={d2 / 'reg.json'}", "--seed=7"],
                      "BUILD_LORA_ARM_HALT", "build_lora_arm_payload.py")
    assert shape["evidence"]["clause"] == "unreadable_node"
    assert shape["evidence"]["container"] == "widgets_values"
    assert shape["evidence"]["where"] == "api"
