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


# ===========================================================================
# F-d30bb5fb (panel HIGH) — this domain's share of the evidence-triple census
#
# `tests/test_gates.evidence_dicts_missing(key, root=None)` defaults `root` to
# `tools/armature_core` and is called with that default at every production site, so the
# layer that PRINTS the receipt — `tools/*.py` — was examined by nothing and the ratchet
# `EVIDENCE_WITHOUT_GATE_ID_ROUTED` read as an empty set. Filed as instruments-measure's
# SEAM 1 asks, and widened to the two keys that post did not quote.
#
# CALLED with `root=TOOLS_DIR` on `580af47`, re-derived branch-local before the first edit:
#   gate    75 offenders tools-wide / 492 examined / 8 unreadable / 50 with no evidence
#   andon  118
#   clause 119   <- the key a halt reader branches on
# Builders' share, by site identity `(file, function, class)`: 9 missing `gate`, 15 missing
# `andon`, 19 missing `clause`, and 19 sites passing NO evidence argument at all.
#
# THE ANCHOR the finding names is the seed's own site: `build_animate_payload.upload_value`
# raised `{"clause": "missing_upload_key", ...}` — a clause and no `gate`, no `andon` —
# while `gate_reference_fit` sixty lines above it carried all three.
#
# WHAT IS NOT DONE HERE, and why: the census WIDENING itself (pointing
# `evidence_dicts_missing` at `TOOLS_DIR` in a tree-wide test with a dated ratchet routed
# per domain) is the tests domain's, wave 26. This block closes builders' rows against the
# call, and asserts them by CALLING the census with `root=TOOLS_DIR` here rather than by
# listing sites — so the property is held by a derivation and cannot be satisfied by a
# table going stale.
#
# MEASURED AND OUT OF DOMAIN, filed rather than fixed (the finding asks for it):
# `tests/test_amend_w16_builders._refusals_with_thin_evidence` raises
# `TypeError: '<' not supported between instances of 'str' and 'NoneType'` on
# `tools/build_i2v_payload.py`, because `_evidence_keys` takes `{k.arg for k in
# ev.keywords}` and a `**spread` keyword's `arg` is None. That helper is not called by any
# test today; it is a tests-domain object and is posted, not touched.

#: The thirteen modules this domain owns, in the frozen domain map's order.
W25_DOMAIN_MODULES = [
    "build_animate_payload.py", "build_assembly_payload.py",
    "build_camera_i2v_payload.py", "build_cascade_payload.py", "build_i2v_payload.py",
    "build_lora_arm_payload.py", "build_payload.py", "build_r2v_payload.py",
    "build_t2v_payload.py", "canon_gate.py", "fetch_run.py", "fetch_t2v_run.py",
    "gate_saved_graph.py",
]

#: Every clause word this wave ADDS to the vocabulary, spelled here so none of them joins
#: `test_refusal_clauses.CLAUSES_NAMED_BY_NO_FIXTURE` — a receipt word no fixture names is
#: a word no test would notice changing. Grouped by the module that raises it.
W25_NEW_CLAUSE_WORDS = {
    "build_animate_payload.py": [
        "negative_source_has_no_sample_neg_prompt", "identity_clause_absent",
        "identity_clause_phrase_absent", "pose_pack_frames_are_not_the_shot_length",
        "built_graph_is_not_the_spec_graph", "negative_source_not_supplied",
    ],
    "build_assembly_payload.py": [
        "flat_slot_ceiling_exceeded", "frame_key_is_not_a_frame_name",
        "frame_key_shapes_are_mixed", "frame_indices_have_a_hole",
        "slot_plan_does_not_cover_the_clip", "slot_does_not_hold_its_frame",
        "two_frames_share_one_server_name",
    ],
    "build_camera_i2v_payload.py": [
        "performance_clause_does_not_dominate", "payload_is_not_the_ruling_it_describes",
        "start_frame_was_not_resolved", "uploads_carry_no_start_frame",
        "override_names_no_trajectory_field", "override_field_is_structural",
        "override_does_not_move_the_field",
    ],
    "build_i2v_payload.py": [
        "prompt_is_not_the_e08_prompt", "start_frame_refused_by_the_sibling",
    ],
    "build_lora_arm_payload.py": [
        "positive_encoder_is_not_reachable", "baseline_is_not_the_two_expert_split",
        "experts_read_different_positives", "positive_prompt_is_empty",
        "tier_matched_pair_is_crossed", "tier_is_not_in_the_lora_name",
        "unnamed_difference_from_the_baseline", "baseline_node_was_removed",
        "insertions_are_not_the_named_ones", "named_break_did_not_happen",
        "seed_is_not_in_the_committed_registry",
        "noise_adding_sampler_carries_another_seed", "model_chain_loops",
        "conditioning_chain_loops", "inserted_node_id_already_exists",
        "expected_model_sampling_node", "expected_unet_loader_node",
    ],
    "build_payload.py": [
        "upload_count_is_not_the_shot_length",
        "control_source_directory_holds_no_frames", "no_uploaded_control_frames",
        "distinct_uploads_disagree_with_the_rendered_control",
        "control_names_not_supplied", "built_graph_link_topology_is_wrong",
        "carried_from_an_assembly_gate",
    ],
    "build_t2v_payload.py": [
        "boundary_is_never_crossed", "boundary_is_crossed_at_step_zero",
        "unknown_trajectory_profile",
    ],
    "gate_saved_graph.py": [
        "saved_values_are_not_the_built_values", "unreadable_link_table_entry",
        "link_table_entry_names_no_origin", "saved_topology_is_not_the_built_topology",
    ],
}

#: The ONE site in this domain the walk cannot judge, named rather than left in a count.
#: `build_payload.gate_out_writable` builds its evidence as a literal carrying all three
#: keys and then, only when the caller supplied `extra`, rebinds it to `dict(extra, **ev)`.
#: `_resolve_dict_expr` follows the Name to that latest assignment and cannot know what a
#: parameter holds, so the site is UNREADABLE rather than an offender. Its literal is
#: asserted directly below, which is what the walk would have proved if it could.
W25_UNREADABLE_BY_THE_WALK = ["build_payload.py:gate_out_writable (PayloadOutHalt)"]


@pytest.mark.parametrize("key", ["gate", "andon", "clause"])
def test_no_raise_in_this_domain_omits_the_identity_triple(key):
    """F-d30bb5fb · the property, held by CALLING the census rather than by a list.

    reverted-red: yes. On `580af47` this call returns 9 / 15 / 19 offender sites in these
    thirteen modules for `gate` / `andon` / `clause`, plus 19 sites passing no evidence
    argument at all.
    """
    import test_gates as TG

    offenders, examined, unreadable, no_evidence = TG.evidence_dicts_missing(
        key, root=os.path.join(REPO, "tools"))
    assert examined > 400, examined          # a census over nothing is not a clean tree
    mine = sorted(s for s in offenders if s.split(":")[0] in W25_DOMAIN_MODULES)
    assert mine == [], mine
    mine_none = sorted(s for s in no_evidence if s.split(":")[0] in W25_DOMAIN_MODULES)
    assert mine_none == [], mine_none
    mine_unreadable = sorted(s for s in unreadable
                             if s.split(":")[0] in W25_DOMAIN_MODULES)
    assert mine_unreadable == W25_UNREADABLE_BY_THE_WALK, mine_unreadable


def test_the_one_unreadable_site_carries_the_triple_the_walk_cannot_see():
    """The half a census that cannot judge a site must not be allowed to skip.

    `gate_out_writable`'s evidence is unreadable to the AST walk only because a caller may
    merge `extra` under it. Both branches are driven and both carry the three keys.
    """
    import build_payload as BP

    plain = BP.gate_out_writable(os.path.join(REPO, "does", "not", "exist.json"),
                                 flag="--out", what="a record")
    assert {"gate", "andon", "clause"} <= set(plain), sorted(plain)
    with pytest.raises(BP.PayloadOutHalt) as caught:
        BP.gate_out_writable(REPO, flag="--out", what="a record",
                             extra={"tool": "a caller's own key"})
    ev = caught.value.evidence
    assert ev["gate"] == "OUT" and ev["andon"] == "PayloadOutHalt", ev
    assert ev["clause"] and ev["tool"] == "a caller's own key", ev


def test_the_census_still_goes_red_on_a_raise_that_drops_the_triple(tmp_path):
    """A census that cannot fail is not a census. A module shaped like this domain's, with
    one refusal carrying a clause and no gate — the anchor's exact shape — is walked and
    must be reported."""
    import test_gates as TG

    root = tmp_path / "tools"
    root.mkdir()
    (root / "errors.py").write_text(
        "class ArmatureError(RuntimeError):\n    pass\n", encoding="utf-8")
    (root / "build_probe_payload.py").write_text(
        "from errors import ArmatureError\n\n\n"
        "class ProbeError(ArmatureError):\n    pass\n\n\n"
        "def upload_value(key):\n"
        "    raise ProbeError('no such key', {'clause': 'missing_upload_key'})\n",
        encoding="utf-8")
    offenders, examined, _unreadable, _none = TG.evidence_dicts_missing("gate", root=root)
    assert examined == 1, examined
    assert sorted(offenders) == ["build_probe_payload.py:upload_value (ProbeError)"],         offenders


@pytest.mark.parametrize("filename", sorted(W25_NEW_CLAUSE_WORDS),
                         ids=sorted(W25_NEW_CLAUSE_WORDS))
def test_every_new_clause_word_is_raised_by_the_module_that_records_it(filename):
    """The table above is a claim about the tree; this reads the tree back.

    Each word must appear as a `clause` value in the module it is listed under, so a
    renamed clause fails here rather than leaving a fixture naming a word nothing raises.
    """
    import _census_nodes as CN

    src = open(os.path.join(TOOLS, filename), encoding="utf-8").read()
    for word in W25_NEW_CLAUSE_WORDS[filename]:
        assert '"' + word + '"' in src, (filename, word)
    vocabulary = CN.clause_literals()
    missing = [w for w in W25_NEW_CLAUSE_WORDS[filename] if w not in vocabulary]
    assert missing == [], missing


def test_the_new_clause_words_are_distinct_and_none_was_already_taken():
    """Rule: one condition, one word. A word reused across two modules would put two
    conditions behind one key a halt reader branches on — except where the SAME condition
    is raised by two tools from one implementation, which is enumerated rather than assumed.
    """
    from collections import Counter

    seen = Counter(w for words in W25_NEW_CLAUSE_WORDS.values() for w in words)
    repeated = sorted(w for w, n in seen.items() if n > 1)
    # `two_frames_share_one_server_name` is ONE condition in TWO tools: the assembly and
    # cascade builders each refuse a upload map whose frames collapse onto one server
    # object, with the same sentence. `built_graph_is_not_the_spec_graph` is the same shape
    # across the three graph builders that carry `verify_topology`.
    assert repeated == [], repeated


# ===========================================================================
# F-edf3a80b (panel HIGH) — the downloader launch is a named refusal, not a crash
#
# `fetch_run.download` launched `subprocess.run(["pwsh", "-NoProfile", "-Command", ps], …)`
# and the launch was the ONE step in that function with no clause, two lines above four
# clauses that exist for every other way the downloader can fail
# (`downloader_process_exit_nonzero`, `downloader_exits_unobserved`,
# `downloader_exits_unreadable`, `downloader_exits_incomplete`).
#
# MEASURED on `580af47` as a real subprocess of the tool with `PATH` set to a directory
# that does not exist:
#   FETCH_RUN_HALT {"error": "FileNotFoundError",
#                   "message": "[WinError 2] The system cannot find the file specified",
#                   "evidence": null}                                          exit 1
# — the code this module reserves for "this tool crashed" — with a raw traceback on stderr
# and a message naming neither `pwsh` nor the flag nor anything an operator can act on.
#
# `fetch_t2v_run` imports this exact function (`from fetch_run import download as
# fetch_download`), so both fetchers shared the one unguarded site — and BOTH run AFTER
# credits have been spent, where the only thing left to protect is the operator's ability
# to tell an environment fault from a broken fetch.

FETCHERS = [("fetch_run.py", "FETCH_RUN"), ("fetch_t2v_run.py", "FETCH_T2V")]


def _fetch_dump(tmp_path, name, node="302"):
    """A dump each fetcher's own `plan` accepts, so the halt under test is the launch."""
    rows = [{"source_node_id": node, "filename": "00000.png",
             "url": "https://example.invalid/0"}]
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"results": rows}), encoding="utf-8")
    return p


def _no_pwsh_env(tmp_path):
    """The process environment of a rig with no downloader on PATH."""
    env = dict(os.environ)
    env["PATH"] = str(tmp_path / "an-empty-directory-that-does-not-exist")
    env["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
    env["PYTHONPATH"] = os.pathsep.join(
        [TOOLS, *(p for p in (os.environ.get("PYTHONPATH") or "").split(os.pathsep) if p)])
    return env


@pytest.mark.parametrize("tool,prefix", FETCHERS, ids=[t for t, _ in FETCHERS])
def test_a_missing_downloader_is_a_named_refusal_in_both_fetchers(tool, prefix, tmp_path):
    """F-edf3a80b · rule 2: the sibling is DRIVEN, not carried. Rule 4: the halt line read.

    reverted-red: yes. On `580af47` both print
    `{"error": "FileNotFoundError", ..., "evidence": null}` at exit 1.
    """
    import fetch_t2v_run as FT

    node = "302" if tool == "fetch_run.py" else FT.LOSSLESS_NODE
    dump = _fetch_dump(tmp_path, f"{prefix.lower()}-dump.json", node=node)
    out = tmp_path / prefix.lower() / "run"
    argv = ([f"--dump={dump}", "--run=r", f"--root={out}"] if tool == "fetch_run.py"
            else [f"--dump={dump}", f"--out={out}"])
    proc = subprocess.run([sys.executable, os.path.join(TOOLS, tool), *argv],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=REPO, env=_no_pwsh_env(tmp_path))
    lines = [ln for ln in proc.stdout.splitlines()
             if ln.startswith(prefix + "_HALT ")]
    assert lines, proc.stdout + proc.stderr
    halt = json.loads(lines[-1][len(prefix) + 6:])
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "FetchHalt", halt
    ev = halt["evidence"]
    assert isinstance(ev, dict), halt                      # it was `null`
    assert ev["gate"] == "FETCH" and ev["andon"] == "FetchHalt", ev
    assert ev["clause"] == "downloader_shell_not_found", ev
    assert ev["executable"] == "pwsh", ev
    assert "searched" in ev, sorted(ev)
    # the invariant a refusal must keep: nothing on disk to be read as a run that happened
    assert not out.exists(), sorted(p.name for p in out.iterdir())


def test_the_gate_is_one_implementation_shared_by_both_fetchers():
    """Adopt the home, do not spell a second. `fetch_t2v_run` imports the function object
    itself, exactly as it already imports `download`."""
    import fetch_run as FR
    import fetch_t2v_run as FT

    assert FT.gate_downloader_shell is FR.gate_downloader_shell
    assert FT.fetch_download is FR.download
    src = open(os.path.join(TOOLS, "fetch_t2v_run.py"), encoding="utf-8").read()
    assert "shutil.which" not in src, "the sibling spelled its own copy"


def test_the_gate_returns_a_receipt_when_the_downloader_is_present():
    """The direction the invariant does not bound: a check that refuses everything is not a
    check. On this rig `pwsh` resolves, and the gate says so with the path it found."""
    import fetch_run as FR

    if shutil.which("pwsh") is None:                      # pragma: no cover - rig-dependent
        pytest.skip("no pwsh on PATH; the refusal direction is covered above")
    ev = FR.gate_downloader_shell()
    assert ev["gate"] == "FETCH" and ev["executable"] == "pwsh", ev
    assert os.path.basename(ev["resolved"]).lower().startswith("pwsh"), ev
    assert "clause" not in ev, ev                          # a receipt is not a refusal


def test_a_downloader_that_exists_and_cannot_start_is_named_by_the_same_clause(
        tmp_path, monkeypatch):
    """`shutil.which` cannot see a `pwsh` that resolves and will not exec — a broken shim, a
    permission bit, an exec-format error — so the launch is caught too, under one word."""
    import fetch_run as FR

    manifest = tmp_path / "urls.json"
    manifest.write_text(json.dumps([{"url": "https://example.invalid/0",
                                     "out": str(tmp_path / "00000.png")}]),
                        encoding="utf-8")

    def refuse_to_start(cmd, **kw):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(FR.subprocess, "run", refuse_to_start)
    with pytest.raises(FR.FetchHalt) as caught:
        FR.download(str(manifest))
    ev = caught.value.evidence
    assert ev["clause"] == "downloader_shell_not_found", ev
    assert ev["error"] == "PermissionError", ev
    assert ev["resolved"], ev


def test_the_four_downloader_clauses_below_the_launch_still_fire_on_their_own_operands(
        tmp_path, monkeypatch):
    """The direction the new clause must not bound (rule 2): with a downloader present, the
    clauses that decide on the per-job exit record are unchanged and still fire."""
    import fetch_run as FR

    manifest = tmp_path / "urls.json"
    manifest.write_text(json.dumps([{"url": "https://example.invalid/0",
                                     "out": str(tmp_path / "00000.png")}]),
                        encoding="utf-8")

    def nonzero(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 7, "", "boom")

    monkeypatch.setattr(FR.subprocess, "run", nonzero)
    with pytest.raises(FR.FetchHalt) as caught:
        FR.download(str(manifest))
    assert caught.value.evidence["clause"] == "downloader_process_exit_nonzero", \
        caught.value.evidence

    def silent(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(FR.subprocess, "run", silent)
    with pytest.raises(FR.FetchHalt) as caught:
        FR.download(str(manifest))
    assert caught.value.evidence["clause"] == "downloader_exits_unobserved", \
        caught.value.evidence


# ===========================================================================
# F-2c15e4e8 (panel HIGH) — the tie between the record and the graph is REQUIRED
#
# `route_facts` refuses `record_describes_a_different_graph` when the record's
# `payload_sha256` disagrees with `canonical_payload_digest(api_graph)` — but when the
# record declared NO digest it set
#   tie = "the record declares no `payload_sha256`, so the facts below are NOT tied to the
#          graph being admitted"
# and ADMITTED, returning that sentence inside `source`. The tie was COMPUTED, RECORDED and
# never REQUIRED.
#
# MEASURED on `580af47`: a record carrying a real `RG.verify` receipt and no digest is
# admitted on the green assembly fixture — `SAVED_ADMISSION_OK`, exit 0,
# `route_facts.payload_sha256: null`, and `source` ending in that sentence. So the
# provenance document for an irreversible spend stated in prose that its two
# spend-admitting facts are not tied to the graph, while the verdict line said OK.
#
# THE POPULATION THAT NEEDED THE ESCAPE IS EMPTY. The wave-18 entry that added the
# comparison (F-5c0f3858) accepted the bound explicitly, on the ground that wave 20 had
# re-measured only FOUR of the nine builders writing the digest. Wave 23 closed that half.
# Re-derived here from the tree, not quoted: the census below reads every builder.
#
# BOUNDED at what there is to tie the record TO: with no `api_graph` there is no graph
# being admitted, and that reading records the absence as before. `--api` is
# `required=True` on this tool's parser and `main` is its only caller, so every CLI path is
# inside the refusal.

W25_NINE_BUILDERS = [
    "build_animate_payload.py", "build_assembly_payload.py",
    "build_camera_i2v_payload.py", "build_cascade_payload.py", "build_i2v_payload.py",
    "build_lora_arm_payload.py", "build_payload.py", "build_r2v_payload.py",
    "build_t2v_payload.py",
]


def test_an_untied_record_is_refused_at_the_admission_boundary(tmp_path):
    """F-2c15e4e8 · the operand: a record with a REAL `verify` receipt and no digest.

    reverted-red: yes — on `580af47` this exact invocation prints `SAVED_ADMISSION_OK` at
    exit 0 with `route_facts.payload_sha256: null`.
    """
    record = _builder_record(ASSEMBLY_API, family="wan", carries_no_sampler=True,
                             frame=(832, 480, 81))
    record.pop("payload_sha256")
    rec_path = _write(tmp_path, "in/untied-record.json", record)
    argv = [a for a in _assembly_cli(tmp_path, record=False)] + [f"--record={rec_path}"]
    proc, halt, oks = _drive("gate_saved_graph.py", argv, "SAVED_ADMISSION")
    assert halt is not None, proc.stdout + proc.stderr
    assert proc.returncode == 2, (proc.returncode, halt)
    assert oks == [], oks
    assert halt["error"] == "SavedAdmission", halt
    ev = halt["evidence"]
    assert ev["clause"] == "record_is_not_tied_to_the_graph", ev
    assert ev["gate"] == "SAVED_ADMISSION" and ev["andon"] == "SavedAdmission", ev
    assert ev["declared_payload_sha256"] is None, ev
    assert ev["api_payload_sha256"], ev
    assert ev["n_verify_receipts"] >= 1, ev      # the receipt was real; the TIE was missing
    assert not (tmp_path / "out").exists(), "a refusal left an out directory"


def test_the_same_record_with_its_digest_is_admitted(tmp_path):
    """The direction the clause must not bound — and the green half of the red proof: the
    ONLY difference between this run and the one above is the digest the builders write."""
    proc, halt, oks = _gsg(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert halt is None and len(oks) == 1, (halt, oks)
    printed = json.loads(oks[0][len("SAVED_ADMISSION_OK "):])
    assert printed["route_facts"]["payload_sha256"], printed
    written = json.loads((tmp_path / "out" / "admission.json").read_text(encoding="utf-8"))
    assert written["route_facts"]["source"].endswith(
        "graph this admission vouches for"), written["route_facts"]["source"]


def test_the_refusals_premise_cannot_go_stale_without_failing_here():
    """The census the refusal rests on: the untied branch's population is EMPTY because
    every builder writes the digest. Derived from the tree, so the day one stops, this
    fails rather than the refusal quietly becoming wrong about its own reason."""
    import ast

    silent = []
    for name in W25_NINE_BUILDERS:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        writes = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and n.value == "payload_sha256"]
        if not writes:
            silent.append(name)
    assert silent == [], silent
    assert len(W25_NINE_BUILDERS) == 9


def test_the_facts_only_reading_still_records_an_absence_it_cannot_judge(tmp_path):
    """The bound, stated as a test: with no graph to tie to, the absence is a RECORDED FACT
    and not a refusal — because there is no graph being admitted for it to be untied from.
    Unreachable from the CLI (`--api` is required), and kept for an in-process caller."""
    import gate_saved_graph as GSG

    record = _builder_record(ASSEMBLY_API, family="wan", carries_no_sampler=True,
                             frame=(832, 480, 81))
    record.pop("payload_sha256")
    rec_path = _write(tmp_path, "in/untied-record.json", record)
    facts = GSG.route_facts(str(rec_path))
    assert facts["payload_sha256"] is None, facts
    assert "nothing was tied and nothing was checked" in facts["source"], facts["source"]

    # WAVE 28 — the bound is that `--api` is REQUIRED, resolved off the parser's own AST
    # rather than matched as a source string. This asserted the literal
    # `ap.add_argument("--api", required=True)`, so giving that flag a `help=`
    # (F-c63c6ba4) failed a test whose subject is CLI reachability and not formatting.
    # Wave 18's rule 1: a census keys on the resolved shape, never the spelled one.
    import ast

    src = open(os.path.join(TOOLS, "gate_saved_graph.py"), encoding="utf-8").read()
    required_flags = {
        node.args[0].value: {kw.arg: getattr(kw.value, "value", None)
                             for kw in node.keywords}
        for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", "") == "add_argument"
        and node.args and isinstance(node.args[0], ast.Constant)}
    assert required_flags.get("--api", {}).get("required") is True, (
        "the bound rests on --api being required from the CLI", sorted(required_flags))


def test_the_disagreeing_digest_clause_beside_it_is_unchanged(tmp_path):
    """Rule 2 — the sibling clause on the same field still fires on its own operand, and
    still under its own word."""
    import gate_saved_graph as GSG

    record = _builder_record(ASSEMBLY_API, family="wan", carries_no_sampler=True,
                             frame=(832, 480, 81))
    record["payload_sha256"] = "0" * 64
    rec_path = _write(tmp_path, "in/wrong-record.json", record)
    with pytest.raises(RG.RouteGate) as caught:
        GSG.route_facts(str(rec_path), ASSEMBLY_API)
    ev = caught.value.evidence
    assert ev["clause"] == "record_describes_a_different_graph", ev
    assert ev["declared_payload_sha256"] == "0" * 64, ev


# ===========================================================================
# F-db6ec1f4 (panel MEDIUM) — an unknown `--hosted-tier` refuses on the FLAG
#
# `--hosted-tier` took any string and was never checked against the table its own help text
# names ("a tier from route_gates.HOSTED_TIER_RULES"), which has exactly one key.
#
# MEASURED on `580af47` as three subprocesses on the green assembly fixture:
# `--hosted-tier=bogus-tier`, `--hosted-tier=wan2.7-r2v` and `--hosted-tier=WAN2.7-R2V` all
# exit 2 with the IDENTICAL `SAVED_ADMISSION_HALT` message — "verify() was told this is
# hosted tier '<x>', but no node in the graph carries that tier's enum inputs. Gate L would
# then have nothing to decide in EITHER clause, which is the vacuous state …" — a sentence
# about the GRAPH, on an argument that names no tier at all. The refusal is fail-closed;
# what it costs is the operator's next hour, at the boundary of the one route in this repo
# that bills per submission.
#
# core-gates' `hosted_nodes_without_a_tier` (their SEAM 3 / SEAM 11) is the CONVERSE and
# the two do not overlap: theirs fires when NO tier is declared and the graph carries
# hosted nodes; this fires when a tier IS declared and is not in the table.

#: The operand family, driven through the CLI. The case-shifted spelling is the one an
#: operator actually types, and it is not a key.
W25_UNKNOWN_TIERS = ["bogus-tier", "WAN2.7-R2V", "wan2.7", "", "wan2.7-r2v "]


@pytest.mark.parametrize("tier", W25_UNKNOWN_TIERS)
def test_an_unknown_hosted_tier_refuses_on_the_flag_not_on_the_graph(tier, tmp_path):
    """F-db6ec1f4 · rule 4: the halt line READ, on a flag value that names no tier.

    reverted-red: yes. On `580af47` every one of these exits 2 with the graph-shaped
    message quoted above and `evidence['clause'] == 'hosted_tier_enums_absent'`.
    """
    proc, halt, oks = _drive(
        "gate_saved_graph.py",
        _assembly_cli(tmp_path, extra=[f"--hosted-tier={tier}"]), "SAVED_ADMISSION")
    assert halt is not None, proc.stdout + proc.stderr
    assert proc.returncode == 2, (proc.returncode, halt)
    assert halt["error"] == "SavedAdmission", halt
    ev = halt["evidence"]
    assert ev["clause"] == "unknown_hosted_tier", ev
    assert ev["flag"] == "--hosted-tier", ev
    assert ev["supplied"] == tier, ev
    assert ev["known"] == ["wan2.7-r2v"], ev
    # the message is about the FLAG, not about the graph
    assert "--hosted-tier" in halt["message"], halt["message"]
    assert "no node in the graph" not in halt["message"], halt["message"]
    assert not (tmp_path / "out").exists(), "a refusal left an out directory"


def test_the_known_set_is_read_off_the_table_and_not_frozen_in_this_file(monkeypatch):
    """A tier ADDED to `route_gates.HOSTED_TIER_RULES` joins without an edit here — which
    an argparse `choices=` would not do, and which is why this is a raise and not a
    parser constraint."""
    import ast

    import gate_saved_graph as GSG

    monkeypatch.setitem(RG.HOSTED_TIER_RULES, "probe-tier",
                        dict(RG.HOSTED_TIER_RULES["wan2.7-r2v"]))
    assert "probe-tier" in sorted(RG.HOSTED_TIER_RULES)
    assert GSG.RG is RG                             # the same module object is read

    # Read off the PARSER (the resolved shape), not off the file's text: this module's own
    # prose says why `choices=` is the wrong instrument here, and a text search would find
    # the sentence saying so.
    src = open(os.path.join(TOOLS, "gate_saved_graph.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    frozen = [n.lineno for n in ast.walk(tree)
              if isinstance(n, ast.Call)
              and getattr(n.func, "attr", "") == "add_argument"
              and any(kw.arg == "choices" for kw in n.keywords)]
    assert frozen == [], frozen
    # and the refusal reads the table by NAME at call time, so a new key is admitted
    reads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr == "HOSTED_TIER_RULES"]
    assert len(reads) >= 2, len(reads)              # the membership test and the evidence


def test_the_real_tier_on_a_graph_that_carries_its_enums_still_reaches_gate_L(tmp_path):
    """The direction the invariant must NOT bound (rule 2): the recorded tier is admitted
    and Gate L decides on the tier's own enum clauses.

    This is the invocation `tests/test_packaging.py`'s success fixture drives, so the
    property is measured twice from two directions.
    """
    import test_gate_saved_graph as G

    api = _write(tmp_path, "in/g.api.json", G.REF_API)
    saved = _write(tmp_path, "in/g.saved.json", G.ref_saved())
    seeds = _write(tmp_path, "in/seeds.json", {"seeds": [2026081351]})
    proc, halt, oks = _drive("gate_saved_graph.py", [
        f"--saved={saved}", f"--api={api}", f"--seeds={seeds}",
        f"--out={tmp_path / 'out' / 'admission.json'}",
        "--hosted-tier=wan2.7-r2v"], "SAVED_ADMISSION")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert halt is None and len(oks) == 1, (halt, oks)
    printed = json.loads(oks[0][len("SAVED_ADMISSION_OK "):])
    assert "pixel clause inapplicable" in printed["gate_L_frame_source"], printed


def test_the_flag_is_refused_above_the_loader(tmp_path):
    """The PLACEMENT, not only the clause: the refusal runs before either graph is opened,
    so a typo is answered without reading two files off disk — the shape wave 23's
    `encode_control` commit established and `--saved` / `--api` already follow."""
    argv = _assembly_cli(tmp_path, extra=["--hosted-tier=bogus-tier"])
    argv = [a if not a.startswith("--saved=") else "--saved=no-such-file.json"
            for a in argv]
    proc, halt, oks = _drive("gate_saved_graph.py", argv, "SAVED_ADMISSION")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    # the TIER clause wins, because it is above the file clause
    assert halt["evidence"]["clause"] == "unknown_hosted_tier", halt["evidence"]


# ===========================================================================
# F-9dd141d9 (panel MEDIUM) — one condition, ONE clause word
#
# `build_r2v_payload` raised `arm_input_missing` from `build()` for arms A1 and A2 and
# `missing_arm_input` from `build_and_write` for the same two arms off its own local copy
# of the same table. Both words were live in the vocabulary census and neither was in
# `CLAUSES_NAMED_BY_NO_FIXTURE`, so the census carried two live clauses where one condition
# exists. Via the CLI only `missing_arm_input` was ever printed, because the CLI check ran
# first; a library caller of `build()` saw only `arm_input_missing`.
#
# Rated LOW by its author and MEDIUM by the panel, deliberately in both cases: no artifact
# is wrong and the refusal was correct in both spellings. What was wrong is that a wrapper
# keyed on the clause word had to know which layer refused.
#
# The surviving word is `missing_arm_input` — the one the CLI printed, whose message names
# the flag and says what the file is for — and `build()` CALLS the same check rather than
# carrying a second one, so there is one raise and not two words agreeing.


@pytest.mark.parametrize("arm,flag", [("A1", "--refs"), ("A2", "--uploads")])
def test_the_library_call_and_the_cli_refuse_under_one_word(arm, flag, tmp_path):
    """F-9dd141d9 · both layers, one clause.

    reverted-red: yes — on `580af47` `build()` answers `arm_input_missing` here.
    """
    import build_r2v_payload as R2V

    with pytest.raises(RG.RouteGate) as caught:
        R2V.build(arm=arm, seed=123456789, prompt="p", negative="n")
    ev = caught.value.evidence
    assert ev["clause"] == "missing_arm_input", ev
    assert ev["arm"] == arm and ev["flag"] == flag, ev
    assert ev["gate"] == "ROUTE" and ev["andon"] == "RouteGate", ev


def test_the_retired_spelling_is_gone_from_the_vocabulary():
    """The census that holds the pair (wave 23's `ONE_CONDITION_TWO_SPELLINGS`) asserted
    BOTH words still existed, so retiring one forces its row to be deleted in the same
    commit. Read off the walk, not off the row."""
    import _census_nodes as CN

    vocabulary = CN.clause_literals()
    assert "arm_input_missing" not in vocabulary, vocabulary.get("arm_input_missing")
    sites = vocabulary["missing_arm_input"]
    assert [s for s in sites if s.startswith("build_r2v_payload.py")] == sites, sites
    assert len(sites) == 1, sites               # one condition, one word, one raise


def test_the_two_layers_share_one_table_and_one_raise():
    """Adopt the home: `build_and_write`'s local `ARM_INPUT` is gone and both layers read
    the module-level table through the same gate function."""
    import ast

    import build_r2v_payload as R2V

    assert sorted(R2V.ARM_INPUT) == ["A1", "A2"]
    src = open(os.path.join(TOOLS, "build_r2v_payload.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    assigns = [n for n in ast.walk(tree)
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "ARM_INPUT" for t in n.targets)]
    assert len(assigns) == 1, [n.lineno for n in assigns]
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef)
          and n.name == "gate_arm_input"]
    assert len(fn) == 1
    raises = [n for n in ast.walk(fn[0]) if isinstance(n, ast.Raise)]
    assert len(raises) == 1, [n.lineno for n in raises]


def test_the_gate_admits_an_arm_that_has_its_input():
    """The direction the check must not bound: a call WITH the input is not refused, and an
    arm the table does not name is not refused by this check either."""
    import build_r2v_payload as R2V

    assert R2V.gate_arm_input("A1", ["a-plate.png"]) is None
    assert R2V.gate_arm_input("A2", ["00000.png"]) is None
    assert R2V.gate_arm_input("A9", None) is None     # not this check's business
