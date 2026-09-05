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


# ---------------------------------------------------------------------------
# F-2fa07723 / F-94cc5fe1 — the two row families that discarded the level the walk
# yields. Node identity in this walk is the PAIR `(where, id)` (wave 18).
# ---------------------------------------------------------------------------

R2V_WIDGETS = ["wan2.7-r2v", "a prompt", "a negative", "720P", "16:9", 5, 7, "fixed"]


def _r2v_node(node_id, widgets=None):
    return {"id": node_id, "type": "Wan2ReferenceVideoApi",
            "widgets_values": list(widgets if widgets is not None else R2V_WIDGETS)}


def _two_level_r2v(top_widgets=None, inner_widgets=None):
    """The auditor's operand: a top-level `Wan2ReferenceVideoApi` id 6 and a blueprint
    `Wan2ReferenceVideoApi` id 6, both at ('720P','16:9',5)."""
    return {"nodes": [_r2v_node(6, top_widgets)],
            "definitions": {"subgraphs": [
                {"id": "bp", "name": "inner",
                 "nodes": [_r2v_node(6, inner_widgets)]}]}}


def test_hosted_enums_rows_carry_the_level_the_walk_yields():
    """RED on base: `hosted_enums` returned `[(6,'720P','16:9',5), (6,'720P','16:9',5)]`
    — the loop was `for _where, n in _iter_nodes(graph)` and the level was discarded, so
    two DIFFERENT nodes produced two identical rows on the one tier that bills per node."""
    rows = RG.hosted_enums(_two_level_r2v())
    assert rows == [("top", 6, "720P", "16:9", 5), ("inner", 6, "720P", "16:9", 5)]
    assert len({r[:2] for r in rows}) == 2, "the pair (where, id) is the identity"


def test_the_per_node_billing_refusal_names_which_node_it_stopped():
    """On base the refusal read 'the graph carries 2 wan2.7-r2v node(s) (6, 6)' and the two
    rows in `hosted_frame_legality_nodes` were keyed `node_id: 6` and `node_id: 6` with no
    `where`. An operator reading a halt that stopped a per-node-billed submission could not
    locate the node that stopped it."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_two_level_r2v(), hosted_tier="wan2.7-r2v")
    ev = exc.value.evidence
    assert "top/6" in str(exc.value) and "inner/6" in str(exc.value)
    rows = ev["hosted_frame_legality_nodes"]
    assert [(r["where"], r["node_id"]) for r in rows] == [("top", 6), ("inner", 6)]


def test_the_hosted_enum_refusal_names_which_node_is_illegal():
    """Making the BLUEPRINT node illegal instead: on base the message read 'Gate L (hosted
    tier): node 6: resolution 4K is not one of ...', which does not say which node 6."""
    illegal = list(R2V_WIDGETS)
    illegal[3] = "4K"
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_two_level_r2v(inner_widgets=illegal), hosted_tier="wan2.7-r2v")
    assert "node inner/6" in str(exc.value)
    assert "node top/6" not in str(exc.value), "only the illegal node is named illegal"


def test_a_single_hosted_node_still_reads_its_row_and_verdict():
    """The ordinary population — one hosted node — is unchanged except for the new first
    member, and `verify` still reaches its enum-legal verdict."""
    assert RG.hosted_enums({"nodes": [_r2v_node(6)]}) == [
        ("top", 6, "720P", "16:9", 5)]
    ev = RG.verify({"nodes": [_r2v_node(6)]}, hosted_tier="wan2.7-r2v",
                   carries_no_sampler=False)
    assert ev["hosted_frame_legality"]["where"] == "top"
    assert "enum-legal" in ev["verdict"]


def test_hosted_enums_carries_the_level_in_api_format_too():
    """API format has its own level label (`api`), and it is recorded for the same reason:
    the row family's identity is the pair, whichever branch produced it."""
    api = {"6": {"class_type": "Wan2ReferenceVideoApi",
                 "inputs": {"model.resolution": "720P", "model.ratio": "16:9",
                            "model.duration": 5}}}
    assert RG.hosted_enums(api) == [("api", "6", "720P", "16:9", 5)]


def _two_level_i2v():
    """A save-format graph carrying a top-level `WanImageToVideo` id 3 and a blueprint
    `WanImageToVideo` id 3 — the auditor's Gate PAIR operand."""
    node = {"id": 3, "type": "WanImageToVideo", "widgets_values": [832, 480, 81, 1]}
    return {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
                      dict(node)],
            "definitions": {"subgraphs": [
                {"id": "bp", "name": "inner", "nodes": [dict(node)]}]}}


def test_gate_pair_rows_carry_the_level_the_walk_yields():
    """RED on base: `conditioning_nodes` carried two rows keyed 3 and 3 and no `where`,
    while `components`, `ruled_node_classes`, `model_weights`, `seeds`, `latents`,
    `cameras` and `camera_widget_order_evidence` every one record it."""
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(_two_level_i2v())
    ev = exc.value.evidence
    assert ev["verdict"] == "CONTRADICTED"
    rows = ev["conditioning_nodes"]
    assert [(r["where"], r["node_id"]) for r in rows] == [("top", "3"), ("inner", "3")]
    assert all(set(r) == {"where", "node_id", "class", "requires"} for r in rows)
    assert "node top/3" in str(exc.value) and "node inner/3" in str(exc.value)


def test_the_pair_indeterminate_refusal_names_level_and_id_too():
    """The sibling clause in the same function: a graph that wires conditioning nodes and
    loads no diffusion model this gate can read. It counted them and named none."""
    g = {"nodes": [{"id": 3, "type": "WanImageToVideo",
                    "widgets_values": [832, 480, 81, 1]}],
         "definitions": {"subgraphs": [{"id": "bp", "name": "inner", "nodes": [
             {"id": 3, "type": "WanImageToVideo",
              "widgets_values": [832, 480, 81, 1]}]}]}}
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    ev = exc.value.evidence
    assert ev["verdict"] == "INDETERMINATE"
    assert [(r["where"], r["node_id"]) for r in ev["conditioning_nodes"]] == [
        ("top", "3"), ("inner", "3")]
    assert "top/3" in str(exc.value) and "inner/3" in str(exc.value)


def test_every_row_family_on_this_page_now_records_where():
    """The census the two findings are two members of: each row family that names a node
    records the level the walk yielded it at. `hosted_enums` is a tuple family and is
    checked by position; the rest are dict rows."""
    i2v_base = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [i2v_base]},
                   {"id": 2, "type": "KSampler",
                    "widgets_values": [7, "fixed", 20, 1.0, "euler", "normal", 1.0]},
                   {"id": 3, "type": "WanImageToVideo",
                    "widgets_values": [832, 480, 81, 1]}]}
    for reader in ("components", "model_weights", "seeds", "latents", "cameras",
                   "ruled_node_classes"):
        rows = getattr(RG, reader)(g)
        assert all("where" in r for r in rows), reader
    assert all(r["where"] == "top" for r in RG.pairing(g)["conditioning_nodes"])
    assert all(len(r) == 5 for r in RG.hosted_enums({"nodes": [_r2v_node(6)]}))


def test_the_gate_pair_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ. `gate_saved_graph.py` runs Gate PAIR on the saved graph, and its
    `SAVED_ADMISSION_HALT` carries the evidence dict — where on base the
    `conditioning_nodes` rows in that printed record carried no `where` at all."""
    d = _gsg_case(tmp_path)
    out = tmp_path / "fresh" / "admission.json"
    payload = _halt_line([f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
                          f"--seeds={d / 'seeds.json'}", f"--out={out}"],
                         "SAVED_ADMISSION_HALT", "gate_saved_graph.py")
    assert payload["error"] == "PairGate"
    rows = payload["evidence"]["conditioning_nodes"]
    assert rows == [{"where": "top", "node_id": "49", "class": "WanAnimateToVideo",
                     "requires": "animate"}]
    assert "top/49" in payload["message"]


def test_the_hosted_billing_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ for the tier that bills per node. On base the printed message
    read "the graph carries 2 wan2.7-r2v node(s) (6, 6)" and the two rows in
    `hosted_frame_legality_nodes` were both keyed `node_id: 6`."""
    d = _gsg_case(tmp_path, saved_doc=_two_level_r2v(),
                  api_doc={"6": {"class_type": "Wan2ReferenceVideoApi",
                                 "inputs": {"model.resolution": "720P",
                                            "model.ratio": "16:9",
                                            "model.duration": 5}}})
    out = tmp_path / "fresh" / "admission.json"
    payload = _halt_line([f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
                          f"--seeds={d / 'seeds.json'}", f"--out={out}",
                          "--hosted-tier=wan2.7-r2v"],
                         "SAVED_ADMISSION_HALT", "gate_saved_graph.py")
    assert "top/6" in payload["message"] and "inner/6" in payload["message"]
    rows = payload["evidence"].get("hosted_frame_legality_nodes")
    if rows is not None:
        assert [(r["where"], r["node_id"]) for r in rows] == [("top", 6), ("inner", 6)]


# ---------------------------------------------------------------------------
# F-715ecaab — `normalise_spec` validated the keys it knew and ACCEPTED every key it
# did not, at every level, and `dump_spec` wrote them back into the provenance spec.
# ---------------------------------------------------------------------------

def _minimal_spec(**over):
    spec = {"spec_version": 1, "name": "w22", "generator": "wan",
            "asset": {"path": "x.glb", "sha256": "0" * 64},
            "resolution": {"width": 832, "height": 480},
            "frames": {"count": 81, "fps": 20},
            "channels": ["depth"]}
    spec.update(over)
    return spec


#: One typo per checked block — the auditor's five, plus the four blocks the auditor did
#: not name whose siblings are checked the same way. Rule 2: the SIBLINGS, enumerated.
TYPO_CASES = [
    ("spec", "cammera", _minimal_spec(cammera={"type": "orbit"})),
    ("spec.camera", "fov_degrees", _minimal_spec(camera={"fov_degrees": 90.0})),
    ("spec.resolution", "depth", _minimal_spec(
        resolution={"width": 832, "height": 480, "depth": 3})),
    ("spec.frames", "framerate", _minimal_spec(
        frames={"count": 81, "fps": 20, "framerate": 24})),
    ("spec.render", "engien", _minimal_spec(render={"engien": "CYCLES"})),
    ("spec.asset", "sha256sum", _minimal_spec(
        asset={"path": "x.glb", "sha256": "0" * 64, "sha256sum": "0" * 64})),
    ("spec.subject", "animated", _minimal_spec(subject={"animated": True})),
    ("spec.depth", "windows", _minimal_spec(depth={"windows": "per_shot"})),
    ("spec.edge", "normal_angle", _minimal_spec(edge={"normal_angle": 30.0})),
]


@pytest.mark.parametrize("where,key,raw", TYPO_CASES,
                         ids=[f"{w}.{k}" for w, k, _ in TYPO_CASES])
def test_an_unknown_spec_key_is_refused_by_name(where, key, raw):
    """RED on base: every one of these was ACCEPTED and survived into the returned spec.
    The auditor measured the first five on `e8263a3`; the other four are the same question
    asked of the blocks beside them."""
    with pytest.raises(SpecError) as exc:
        SS.normalise_spec(raw)
    assert key in str(exc.value) and where in str(exc.value)
    ev = getattr(exc.value, "evidence", None)
    assert ev and ev["clause"] == "unknown_spec_key"
    assert ev["where"] == where and ev["unknown"] == [key]
    assert ev["andon"] == "SpecError" and ev["gate"] is None
    assert key not in ev["known_keys"]


def test_the_round_trip_the_auditor_measured_no_longer_happens():
    """The measured consequence: with `camera.fov_degrees = 90.0` alongside
    `camera.fov_deg = 35.0`... (`fov_deg` is not a field of this schema either, which is
    the point — the auditor's operand was a spec carrying BOTH an ignored field and a used
    one, and `dump_spec` wrote a camera block carrying both, with nothing saying which was
    read). Neither reaches `dump_spec` now."""
    raw = _minimal_spec(camera={"fov_degrees": 90.0, "fov_deg": 35.0})
    with pytest.raises(SpecError) as exc:
        SS.normalise_spec(raw)
    assert exc.value.evidence["unknown"] == ["fov_deg", "fov_degrees"]


def test_the_underscore_prefix_is_the_named_passthrough_and_it_is_recorded():
    """Forward compatibility has ONE explicitly-named shape rather than "anything not
    recognised": a key beginning with `_`. It is what the five committed specs already use
    (`_notes`), it is what `dump_spec` already strips on write (`if not
    k.startswith("_")`), and it is RECORDED on the returned spec so a reader can tell
    which fields the schema did not read."""
    raw = _minimal_spec(_notes={"why": "because"},
                        camera={"_measured_framing": "off the E01 render"})
    spec = SS.normalise_spec(raw)
    assert spec["_passthrough_keys"] == {"spec": ["_notes"],
                                         "spec.camera": ["_measured_framing"]}
    assert spec["_notes"] == {"why": "because"}


def test_a_spec_with_no_passthrough_records_none_and_dump_writes_neither(tmp_path):
    """The negative half: a clean spec grows no key, and the passthrough record itself is
    `_`-prefixed so `dump_spec` strips it — the provenance spec on disk is the schema."""
    spec = SS.normalise_spec(_minimal_spec())
    assert "_passthrough_keys" not in spec
    with_notes = SS.normalise_spec(_minimal_spec(_notes={"a": 1}))
    out = SS.dump_spec(with_notes, str(tmp_path / "s.json"))
    written = json.loads(open(out, encoding="utf-8").read())
    assert "_passthrough_keys" not in written and "_notes" not in written


def test_every_committed_spec_still_parses():
    """The population this clause could break: `specs/**` carries `_notes` at the top level
    and `asset.note`, both of which are the schema's rather than an author's typo. A gate
    that fires on correct work is the gate nobody keeps."""
    import glob

    seen = 0
    for path in glob.glob(os.path.join(REPO, "specs", "**", "*.json"), recursive=True):
        raw = json.loads(open(path, encoding="utf-8").read())
        if not isinstance(raw, dict) or "resolution" not in raw:
            continue
        SS.normalise_spec(raw, spec_path=path)
        seen += 1
    assert seen >= 5, seen


def test_the_key_census_covers_every_block_normalise_spec_reads():
    """A census that names fewer blocks than the function validates is a census that lets
    a level through. Every mapping block `normalise_spec` reaches has a row."""
    assert set(SS.SPEC_KEYS) == {
        "spec", "spec.asset", "spec.resolution", "spec.frames", "spec.camera",
        "spec.subject", "spec.depth", "spec.edge", "spec.render"}
    # every block named in the top-level row that holds a mapping in DEFAULTS has its own
    # row, so no nested block is checked at its parent and nowhere else
    for key, value in SS.DEFAULTS.items():
        if isinstance(value, dict):
            assert f"spec.{key}" in SS.SPEC_KEYS, key


def test_the_retired_gates_key_keeps_its_own_refusal():
    """`spec.gates` is refused by the clause written for it — the KEY is the retired schema
    surface and the message names where the number went — not by the generic unknown-key
    clause. Its clause runs first, and this pins that it still does."""
    with pytest.raises(SpecError, match=r"retired schema surface"):
        SS.normalise_spec(_minimal_spec(gates={}))
    with pytest.raises(SpecError, match=r"skip flag wearing a schema's clothes"):
        SS.normalise_spec(_minimal_spec(gates={"g4_tolerance_px": 4}))


def test_the_unknown_spec_key_refusal_reaches_a_printed_halt_record(capsys):
    """The halt line READ, through the REAL `__main__` block of the tool that runs the
    spec. `stage_render.py` runs inside Blender, so it is driven with Blender stubbed and
    `main` replaced by a call that raises the actual refusal — the handler, the sentinel
    and the exit code are the shipped ones."""
    import blender_stub

    def raiser():
        SS.normalise_spec(_minimal_spec(camera={"fov_degrees": 90.0}))

    code, escaped = blender_stub.exit_code_of_main_block("stage_render.py",
                                                         raiser=raiser)
    assert escaped is None
    assert code == 2, code
    out = capsys.readouterr().out
    halts = [ln for ln in out.splitlines() if ln.startswith("STAGE_RENDER_HALT ")]
    assert len(halts) == 1, out
    payload = json.loads(halts[0][len("STAGE_RENDER_HALT "):])
    assert payload["error"] == "SpecError"
    assert payload["evidence"]["clause"] == "unknown_spec_key"
    assert payload["evidence"]["where"] == "spec.camera"
    assert payload["evidence"]["unknown"] == ["fov_degrees"]


# ---------------------------------------------------------------------------
# F-0d00378d — the named landmark-table guard that only a test called is armed.
# ---------------------------------------------------------------------------

def _rows_with_ankles(n=4):
    image = [[0.5, 0.5] for _ in range(33)]
    return [{"frame": i, "fired": True, "image": [list(p) for p in image]}
            for i in range(n)]


def test_a_renamed_landmark_table_refuses_by_name(monkeypatch):
    """RED on base: `ankle_framing` built `idx` with `LS.POSE_LANDMARKS.index(a)` and a
    renamed table raised a bare `ValueError` — not an `ArmatureError`, so the halt
    contract's exit-2 branch was bypassed — and it was raised AFTER the function had been
    entered rather than before. The named guard that would have caught it had exactly one
    caller in the whole worktree: `tests/test_donor_gate.py:64`."""
    from armature_core import lift_solve as LS

    renamed = [n for n in LS.POSE_LANDMARKS if n != "left_ankle"] + ["left_foot"]
    monkeypatch.setattr(LS, "POSE_LANDMARKS", renamed)
    with pytest.raises(DG.DonorGate) as exc:
        DG.ankle_framing(_rows_with_ankles())
    ev = exc.value.evidence
    assert ev["clause"] == "landmark_table_renamed"
    assert ev["missing"] == ["left_ankle"]
    assert ev["gate"] == "DONOR" and ev["andon"] == "DonorGate"
    assert ev["table"] == "lift_solve.POSE_LANDMARKS"


def test_both_ankle_names_are_the_enumerated_siblings(monkeypatch):
    """`ANKLES` is the population the clause is written against; each member is proved
    red separately, and both-missing names both."""
    from armature_core import lift_solve as LS

    original = list(LS.POSE_LANDMARKS)
    for missing in ("left_ankle", "right_ankle"):
        monkeypatch.setattr(LS, "POSE_LANDMARKS",
                            [n for n in original if n != missing])
        with pytest.raises(DG.DonorGate) as exc:
            DG.ankle_framing(_rows_with_ankles())
        assert exc.value.evidence["missing"] == [missing]
    monkeypatch.setattr(LS, "POSE_LANDMARKS",
                        [n for n in original if n not in DG.ANKLES])
    with pytest.raises(DG.DonorGate) as exc:
        DG.ankle_framing(_rows_with_ankles())
    assert exc.value.evidence["missing"] == ["left_ankle", "right_ankle"]


def test_the_guard_fires_BEFORE_the_clause_reads_a_row(monkeypatch):
    """Position is half the finding: the `ValueError` it replaces was raised after
    `ankle_framing` had been entered. A row population that would itself refuse
    (`no frame carries image landmarks`) still meets the TABLE clause first."""
    from armature_core import lift_solve as LS

    monkeypatch.setattr(LS, "POSE_LANDMARKS",
                        [n for n in LS.POSE_LANDMARKS if n != "left_ankle"])
    with pytest.raises(DG.DonorGate) as exc:
        DG.ankle_framing([])
    assert exc.value.evidence["clause"] == "landmark_table_renamed"


def test_the_intact_table_is_unchanged_and_the_gate_still_computes():
    """The gate that fires on correct work is the gate nobody keeps."""
    ev = DG.ankle_framing(_rows_with_ankles())
    assert ev["both_ankles_in_image"] == 1.0
    assert ev["n_frames_considered"] == 4


def test_the_landmark_table_refusal_reaches_a_printed_halt_record(tmp_path, capsys):
    """The halt line READ. `lift_clip.py` is Gate DONOR's one production caller; its
    `__main__` handler is driven with Blender stubbed and `main` replaced by the real
    refusal, so the handler, the sentinel and the exit code are the shipped ones."""
    import blender_stub
    from armature_core import lift_solve as LS

    renamed = [n for n in LS.POSE_LANDMARKS if n != "left_ankle"]

    def raiser():
        saved = LS.POSE_LANDMARKS
        try:
            LS.POSE_LANDMARKS = renamed
            DG.ankle_framing(_rows_with_ankles())
        finally:
            LS.POSE_LANDMARKS = saved

    code, escaped = blender_stub.exit_code_of_main_block("lift_clip.py", raiser=raiser)
    assert escaped is None and code == 2, (code, escaped)
    out = capsys.readouterr().out
    halts = [ln for ln in out.splitlines() if "_HALT " in ln]
    assert len(halts) == 1, out
    payload = json.loads(halts[0].split("_HALT ", 1)[1])
    assert payload["error"] == "DonorGate"
    assert payload["evidence"]["clause"] == "landmark_table_renamed"
    assert payload["evidence"]["missing"] == ["left_ankle"]


# ---------------------------------------------------------------------------
# F-092dd71f — `armature check`'s failure row carries its cause.
# ---------------------------------------------------------------------------

def test_a_probe_forced_to_raise_produces_a_row_naming_the_exception(monkeypatch):
    """RED on base: `_probe` caught `Exception` and returned the bare string `'MISSING'`;
    the type and the message were discarded and appeared in no output path. The auditor's
    operand: `importlib.import_module('armature_core.shotspec')` raising
    `ValueError('boom: a table in this module is malformed')`."""
    import importlib as _il

    real = _il.import_module

    def boom(name, *a, **k):
        if name == "armature_core.shotspec":
            raise ValueError("boom: a table in this module is malformed")
        return real(name, *a, **k)

    monkeypatch.setattr(cli.importlib, "import_module", boom)
    row = cli._probe("shotspec")
    assert row["status"] == "MISSING"
    assert row["error"] == "ValueError"
    assert row["message"] == "boom: a table in this module is malformed"
    assert row["module"] == "shotspec" and row["missing_root"] is None


def test_the_cause_reaches_both_output_paths(monkeypatch, capsys):
    """The receipt half. `--json` carries the whole row and keeps `modules` and `missing`
    exactly as they were, so every existing pin on them holds; the text output prints the
    type and the message beside the module."""
    import importlib as _il

    real = _il.import_module

    def boom(name, *a, **k):
        if name == "armature_core.shotspec":
            raise ValueError("boom: a table in this module is malformed")
        return real(name, *a, **k)

    monkeypatch.setattr(cli.importlib, "import_module", boom)
    assert cli.main(["check", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"]["shotspec"] == "MISSING"
    assert payload["missing"] == ["shotspec"]
    row = next(r for r in payload["module_rows"] if r["module"] == "shotspec")
    assert (row["error"], row["message"]) == (
        "ValueError", "boom: a table in this module is malformed")

    assert cli.main(["check"]) == 1
    text = capsys.readouterr().out
    assert "shotspec         MISSING" in text
    assert "ValueError: boom: a table in this module is malformed" in text
    assert "UNRESOLVED: shotspec" in text


@pytest.mark.parametrize("exc,root,status", [
    (ModuleNotFoundError("No module named 'bpy'", name="bpy"), "bpy", "needs-blender"),
    (ModuleNotFoundError("No module named 'nope'", name="nope"), "nope", "MISSING"),
    (SyntaxError("invalid syntax"), None, "MISSING"),
])
def test_every_failing_outcome_carries_its_cause(monkeypatch, exc, root, status):
    """The siblings, enumerated: the four outcomes this command distinguishes. The two that
    can carry a missing root do; `needs-blender` — the ONE expected condition outside
    Blender — keeps its status and now says which module was absent, which is what told the
    genuine bpy-absent reading from a typo'd import in the first place."""
    import importlib as _il

    real = _il.import_module

    def boom(name, *a, **k):
        if name == "armature_core.shotspec":
            raise exc
        return real(name, *a, **k)

    monkeypatch.setattr(cli.importlib, "import_module", boom)
    row = cli._probe("shotspec")
    assert row["status"] == status
    assert row["error"] == type(exc).__name__
    assert row["missing_root"] == root


def test_a_healthy_module_row_says_so_and_carries_no_cause():
    """The negative half: an `ok` row and a `needs-<dep>` row both carry `error: None`, so
    a reader keyed on `error` cannot mistake a resolvable module for a broken one."""
    row = cli._probe("errors")
    assert row["status"] == "ok" and row["error"] is None and row["message"] is None


def test_the_check_cause_reaches_the_real_main_block(tmp_path):
    """The printed record READ from the tool's OWN `__main__`, in a subprocess. `armature
    check` carries no `<PREFIX>_HALT` sentinel — its record IS the printed table and the
    exit code, and that is what this reads: exit 1, the UNRESOLVED line, and the cause
    beside the module."""
    import subprocess

    driver = tmp_path / "drive_check.py"
    driver.write_text(
        "import importlib, runpy\n"
        "_real = importlib.import_module\n"
        "def _boom(name, *a, **k):\n"
        "    if name == 'armature_core.shotspec':\n"
        "        raise ValueError('boom: a table in this module is malformed')\n"
        "    return _real(name, *a, **k)\n"
        "importlib.import_module = _boom\n"
        "runpy.run_module('armature_core.cli', run_name='__main__')\n",
        encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "tools"))
    proc = subprocess.run([sys.executable, str(driver), "check"],
                          capture_output=True, text=True, env=env, cwd=REPO)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "UNRESOLVED: shotspec" in proc.stdout
    assert "ValueError: boom: a table in this module is malformed" in proc.stdout
