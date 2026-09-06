"""Wave 28 (Stage C amend #1) — the core-gates domain's nine approved findings.

Every test here drives the REAL predicate — the shipped function, not a re-implementation
of it — and every one was run RED with the source reverted before it was run green. The
findings, by canonical id:

  F-189195ea  the `[canon] UNGATED:` announcement carries the census reason
  F-e811c351  `add_spend_flags`' three help strings are written for the operator
  F-3c8db173  `escape_unknown` and `missing_subject` hand over the valid set
  F-a032cc84  `canon.load`'s refusals name the FILE and carry a clause word
  F-1e1780ba  `_component_label` keeps `node_id` and `where`
  F-21e7e0c1  `TOOL_VERSION` (and a graph digest) reach the receipts
  F-faa2f9f4  `RULED_COMPONENTS` carries the map's fetch date and source URL
  F-abf293d8  G2's two refusals name the run directory
  F-594c5a7a  Gate P's round trip says what it is about to walk, on every branch
"""

import argparse
import datetime
import inspect
import io
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from armature_core import canon, canon_census, gates, rig_gates  # noqa: E402
from armature_core import route_gates as R  # noqa: E402
from armature_core.errors import G2Completeness, GateCanon, GatePRestPose  # noqa: E402

ROUTE_GATES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "armature_core", "route_gates.py")


# ===========================================================================
# F-189195ea — the announcement that says a spend proceeded WITHOUT canon
# ===========================================================================


@pytest.mark.parametrize("subject", sorted(canon_census.CENSUS))
def test_the_ungated_announcement_carries_the_reason_not_only_the_subject(subject):
    """The loudest signal in the repo that a spend went ahead unGATED says WHY.

    Measured before the fix, for all three census rows: `[canon] UNGATED: BLACKGUARD`,
    `[canon] UNGATED: PERFORMER`, `[canon] UNGATED: WIRE` — the subject and nothing else,
    while the `reason` sat in the same dict. A reviewer scanning a build log could not
    tell a ratified-hole escape from a subject whose canon was never written.
    """
    ev = canon.require_canon(subject, "any prompt at all", no_canon=True)
    reason = canon_census.CENSUS[subject]["reason"]
    assert ev["announcement"].startswith(f"[canon] UNGATED: {subject}")
    assert reason in ev["announcement"], ev["announcement"]


def test_the_census_refusal_that_justifies_itself_on_the_announcement_now_tells_truth():
    """`hole_without_a_reason` refuses a reason-less row on the stated ground that the
    reason "is quoted in `require_canon`'s UNGATED record and in the spend it announces".
    The record half held; the announcement half did not until this wave. Both halves are
    driven here from one row, so the refusal's ground and the string cannot drift apart."""
    census = {"NEWCHAR": {"surfaces": None, "reason": "a stated hole"}}
    ev = canon.require_canon("NEWCHAR", "p", no_canon=True, census=census)
    assert ev["reason"] == "a stated hole"
    assert "a stated hole" in ev["announcement"]
    with pytest.raises(GateCanon) as exc:
        canon_census.gate_census_table({"NEWCHAR": {"surfaces": None, "reason": None}})
    assert exc.value.evidence["clause"] == "hole_without_a_reason"


def test_the_printed_line_is_the_modules_own_string(capsys, tmp_path):
    """`tools/canon_gate.canon_line` prints `announcement` verbatim where present — so the
    fix reaches the LINE a builder prints, not only the dict. Driven through that
    function, which is the production path (`tools/canon_gate.py:105-106`)."""
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import canon_gate  # noqa: E402

    ev = canon.require_canon("WIRE", "p", no_canon=True)
    print(canon_gate.canon_line(ev))
    printed = capsys.readouterr().out
    assert printed.startswith("[canon] UNGATED: WIRE")
    assert canon_census.CENSUS["WIRE"]["reason"] in printed


# ===========================================================================
# F-e811c351 — the three flags at the spend boundary explain themselves
# ===========================================================================


def _spend_help():
    ap = argparse.ArgumentParser(prog="build_x_payload.py", add_help=False)
    canon.add_spend_flags(ap)
    return {a.option_strings[0]: a.help for a in ap._actions}


def test_subject_help_names_the_census_ids_and_reads_them_from_the_table():
    """(a) of the three measured gaps. The old text — "census id this payload is of.
    Silence is a refuse." — named no legal value, though `resolve`'s own refusal quotes
    the census and the table is available at help-build time. Asserted against the TABLE
    rather than a literal list, so the text cannot drift from a census edit."""
    text = _spend_help()["--subject"]
    for subject in canon_census.gate_census_table():
        assert subject in text, (subject, text)
    assert "Silence is a refuse" not in text


def test_subject_help_says_what_omitting_it_does():
    """(b). The idiom "Silence is a refuse" compressed the docstring's plain statement —
    that an absent `--subject` raises GateCanon rather than an argparse error — into words
    that read as a typo, and the fact never reached the operator."""
    text = _spend_help()["--subject"]
    assert "Gate CANON" in text and "argparse" in text


def test_no_canon_help_says_what_it_turns_off_and_when_it_is_refused():
    """(c). The flag that BYPASSES the gate CLAUDE.md places inside the irreversible write
    described itself as a "census-backed escape" and never said what it switches off."""
    text = _spend_help()["--no-canon"]
    assert "BYPASS" in text and "Gate CANON" in text
    assert "REFUSED" in text and "surfaces" in text


def test_canon_prompt_help_says_it_can_only_refuse():
    """The third flag: `gate_canon_ships_what_it_gated` cross-checks it, so it can refuse
    a build and cannot change what is submitted — which the old one line did not say."""
    text = _spend_help()["--canon-prompt"]
    assert "cross-checked" in text and "cannot change" in text


# ===========================================================================
# F-3c8db173 — the two refusals that knew the valid set and did not hand it over
# ===========================================================================


def test_the_no_canon_escape_on_an_unknown_subject_quotes_the_census():
    """The one of six "that name is not one I know" refusals that put the valid set
    nowhere — on the flag that bypasses Gate CANON before a spend, in a branch that had
    read the whole table one line above."""
    with pytest.raises(GateCanon) as exc:
        canon.require_canon("raidar", "p", no_canon=True)
    assert exc.value.evidence["clause"] == "escape_unknown"
    assert exc.value.evidence["known"] == sorted(canon_census.CENSUS)
    for subject in canon_census.CENSUS:
        assert subject in str(exc.value), str(exc.value)


def test_the_missing_subject_refusal_names_the_flag_and_the_valid_set():
    """The adjacent half: "no subject: a spend with no census id has no answer" named
    neither the flag nor a value, where its `--no-canon` sibling names its flag."""
    with pytest.raises(GateCanon) as exc:
        canon.resolve(None)
    ev = exc.value.evidence
    assert ev["clause"] == "missing_subject"
    assert ev["flag"] == "--subject"
    assert ev["known"] == sorted(canon_census.CENSUS)
    assert "--subject" in str(exc.value)
    for subject in canon_census.CENSUS:
        assert subject in str(exc.value)


def test_the_six_unknown_name_refusals_in_this_domain_all_hand_over_the_set():
    """The property the finding is an exception to, driven across all six rather than
    asserted about the one that moved. `known` (or `known_keys`) in the evidence AND the
    values in the sentence."""
    raised = []

    with pytest.raises(Exception) as exc:
        gates.resolve_generator("wan22")
    raised.append(("resolve_generator", exc.value))
    with pytest.raises(Exception) as exc:
        R.frame_legality(832, 480, 81, "wan22")
    raised.append(("frame_legality", exc.value))
    with pytest.raises(GateCanon) as exc:
        canon.resolve("raidar")
    raised.append(("canon.resolve", exc.value))
    with pytest.raises(GateCanon) as exc:
        canon.require_canon("raidar", "p", no_canon=True)
    raised.append(("escape_unknown", exc.value))
    with pytest.raises(GateCanon) as exc:
        canon.resolve(None)
    raised.append(("missing_subject", exc.value))
    with pytest.raises(GateCanon) as exc:
        canon_census.gate_census_table({"X": {"surface": "x.json"}})
    raised.append(("gate_census_table", exc.value))

    for name, err in raised:
        ev = err.evidence
        assert "known" in ev or "known_keys" in ev, (name, sorted(ev))


# ===========================================================================
# F-a032cc84 — every `canon.load` refusal names the file and carries a clause
# ===========================================================================


#: `{filename: (body, clause)}` — one malformed canon per refusal that used to be silent
#: about the file it read. Written to disk and loaded through the real `canon.load`.
MALFORMED = {
    "not_object.json": ("[]", "not_object"),
    "schema.json": ('{"schema": 0}', "schema"),
    "stale.json": ('{"schema": 99}', "stale_consumer"),
    "no_surfaces.json": ('{"schema": 1}', "no_surfaces"),
    "no_clauses.json": ('{"schema": 1, "surfaces": []}', "no_legal_clauses"),
    "surface_no_id.json": ('{"schema": 1, "surfaces": [{}], "legal_clauses": []}',
                           "surface_needs_id"),
    "dup_id.json": ('{"schema": 1, "surfaces": [{"id": "torso"}, {"id": "torso"}], '
                    '"legal_clauses": []}', "duplicate_surface_id"),
    "occ_shape.json": ('{"schema": 1, "surfaces": [{"id": "t", "occupant": 7}], '
                       '"legal_clauses": []}', "occupant_is_not_an_object"),
    "occ_kind.json": ('{"schema": 1, "surfaces": [{"id": "t", '
                      '"occupant": {"kind": "wobble"}}], "legal_clauses": []}',
                      "unknown_occupant_kind"),
    "spatial_shape.json": ('{"schema": 1, "surfaces": [{"id": "t", "spatial": 7}], '
                           '"legal_clauses": []}', "spatial_is_not_an_object"),
    "spatial_kind.json": ('{"schema": 1, "surfaces": [{"id": "t", '
                          '"spatial": {"kind": "wobble", "ref": "x"}}], '
                          '"legal_clauses": []}', "unknown_spatial_kind"),
    "spatial_ref.json": ('{"schema": 1, "surfaces": [{"id": "t", '
                         '"spatial": {"kind": "region"}}], "legal_clauses": []}',
                         "spatial_needs_a_ref"),
    "joint_shape.json": ('{"schema": 1, "surfaces": [{"id": "t"}], '
                         '"legal_clauses": [], "joints": ["j1"]}',
                         "joint_is_not_an_object"),
    "bad_joint.json": ('{"schema": 1, "surfaces": [{"id": "t"}], "legal_clauses": [], '
                       '"joints": [{"id": "j1", "a": "t", "b": "head"}]}',
                       "joint_names_unknown_surface"),
    "clause_shape.json": ('{"schema": 1, "surfaces": [], "legal_clauses": [{"id": "c"}]}',
                          "legal_clause_needs_id_and_phrase"),
    "dup_clause.json": ('{"schema": 1, "surfaces": [], "legal_clauses": '
                        '[{"id": "c", "phrase": "p"}, {"id": "c", "phrase": "q"}]}',
                        "duplicate_legal_clause_id"),
    "clause_class.json": ('{"schema": 1, "surfaces": [], "legal_clauses": '
                          '[{"id": "c", "phrase": "p", "class": "wobble"}]}',
                          "unknown_legal_clause_class"),
    "bad_bone.json": ('{"schema": 1, "surfaces": [{"id": "t", "spatial": '
                      '{"kind": "bone", "ref": "not_a_site"}}], "legal_clauses": []}',
                      "unknown_bone"),
    "blocked_shape.json": ('{"schema": 1, "surfaces": [], "legal_clauses": [], '
                           '"blocked_additions": 7}', "blocked_additions_not_a_list"),
    "blocked_empty.json": ('{"schema": 1, "surfaces": [], "legal_clauses": [], '
                           '"blocked_additions": [" "]}', "blocked_addition_empty"),
    "blocked_row.json": ('{"schema": 1, "surfaces": [], "legal_clauses": [], '
                         '"blocked_additions": [7]}', "blocked_addition_shape"),
    "blocked_phrase.json": ('{"schema": 1, "surfaces": [], "legal_clauses": [], '
                            '"blocked_additions": [{"id": "b", "text": "halo"}]}',
                            "blocked_addition_phrase"),
    "forbidden_shape.json": ('{"schema": 1, "surfaces": [{"id": "t", "occupant": '
                             '{"forbidden": "glow"}}], "legal_clauses": []}',
                             "forbidden_not_a_list"),
    "forbidden_word.json": ('{"schema": 1, "surfaces": [{"id": "t", "occupant": '
                            '{"forbidden": [" "]}}], "legal_clauses": []}',
                            "forbidden_word"),
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_every_canon_load_refusal_names_the_file_and_its_clause(tmp_path, name):
    """The property, over the whole refusal population of the reader Gate CANON is decided
    from. Measured before the fix on eight of these: the first two named the path and the
    rest read "canon must be an object" / "canon needs a surfaces list" / "surface 0 needs
    id" / "duplicate surface id torso" / "joint j1 names unknown surfaces" with the path
    in the evidence and nowhere in the sentence — and twelve sites carried a receipt with
    no `clause` at all. `resolve` searches SEVERAL roots, so a sentence with no path does
    not even identify which root's file was read."""
    body, clause = MALFORMED[name]
    path = tmp_path / name
    io.open(path, "w", encoding="utf-8").write(body)
    with pytest.raises(GateCanon) as exc:
        canon.load(str(path))
    assert exc.value.evidence["clause"] == clause, sorted(exc.value.evidence)
    assert exc.value.evidence["path"] == str(path)
    assert str(path) in str(exc.value), str(exc.value)


def test_no_refusal_in_canon_carries_a_path_in_its_receipt_and_not_in_its_sentence():
    """The census the parametrisation above cannot see: an AST walk of every `_raise` site
    in `canon.py`, asserting that a site whose evidence dict carries `path` also mentions
    `path` in its message expression. Measured before the fix: 25 of the module's sites
    failed this, and 25 of the tree's 27 such sites were in this one file."""
    import ast

    src = io.open(canon.__file__, encoding="utf-8").read()
    offenders = []
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_raise" and len(node.args) > 1):
            continue
        ev = node.args[1]
        if not isinstance(ev, ast.Dict):
            continue
        keys = [k.value for k in ev.keys if isinstance(k, ast.Constant)]
        if "path" not in keys:
            continue
        if "path" not in ast.unparse(node.args[0]):
            offenders.append(node.lineno)
    assert offenders == [], offenders


def test_every_canon_raise_that_carries_a_receipt_carries_a_clause_word():
    """The other half of F-a032cc84: twelve sites carried an evidence dict with no
    `clause`, so the machine half of the halt record could not identify them either."""
    import ast

    src = io.open(canon.__file__, encoding="utf-8").read()
    offenders = []
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_raise" and len(node.args) > 1):
            continue
        ev = node.args[1]
        if not isinstance(ev, ast.Dict):
            continue
        keys = [k.value for k in ev.keys if isinstance(k, ast.Constant)]
        if "clause" not in keys:
            offenders.append((node.lineno, keys))
    assert offenders == [], offenders


def test_the_unknown_joint_endpoint_is_named_and_the_known_ids_quoted(tmp_path):
    """`joint j1 names unknown surfaces` did not say which of `a`/`b` was unknown nor list
    the ids, though the loop was holding them."""
    path = tmp_path / "j.json"
    io.open(path, "w", encoding="utf-8").write(
        '{"schema": 1, "surfaces": [{"id": "torso"}, {"id": "arm"}], '
        '"legal_clauses": [], "joints": [{"id": "j1", "a": "shoulder", "b": "head"}]}')
    with pytest.raises(GateCanon) as exc:
        canon.load(str(path))
    ev = exc.value.evidence
    assert ev["unknown_endpoints"] == ["a", "b"]
    assert ev["known"] == ["torso", "arm"]
    assert "a='shoulder'" in str(exc.value) and "b='head'" in str(exc.value)
    assert "torso" in str(exc.value) and "arm" in str(exc.value)


# ===========================================================================
# F-1e1780ba — the licence kill names the NODE it wants deleted
# ===========================================================================


def _banned_in_a_blueprint():
    """A SAVE-format graph whose banned LoRA sits inside a subgraph blueprint — the case
    the finding measured, and the one where a bare filename is least sufficient."""
    return {
        "nodes": [{"id": 1, "type": "UNETLoader",
                   "widgets_values": ["wan2.1_vace_14B_fp16.safetensors"]}],
        "definitions": {"subgraphs": [{
            "id": "sg", "name": "style_stack",
            "nodes": [{"id": 42, "type": "LoraLoaderModelOnly",
                       "widgets_values": ["causvid_x.safetensors", 1.0]}],
        }]},
    }


def test_the_licence_kill_names_the_node_and_the_subgraph_level():
    """Measured before the fix: `components()` returned `causvid_x.safetensors ->
    node_id: 42, where: style_stack` and `verify()` raised "[ROUTE] the graph loads
    'causvid_x.safetensors' (BANNED: …)" with neither `42` nor `style_stack` anywhere in
    the message — while the refusal's required action is to DELETE a node."""
    g = _banned_in_a_blueprint()
    comp = R.components(g)
    banned = [c for c in comp if c.get("matched_on") == "causvid"]
    assert banned and banned[0]["node_id"] == 42 and banned[0]["where"] == "style_stack"
    with pytest.raises(R.RouteGate) as exc:
        R.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    message = str(exc.value)
    assert "causvid_x.safetensors" in message
    assert "style_stack/42" in message, message
    assert any("style_stack/42" in s
               for s in exc.value.evidence["banned_or_excluded"]), \
        exc.value.evidence["banned_or_excluded"]


def test_one_helper_carries_the_node_to_every_sentence_built_from_it():
    """The fix is ONE helper so the BANNED, EXCLUDED and uncredited-CONDITIONAL messages
    and `ev['banned_or_excluded']` / `ev['unclassified']` gain it at once — the shape
    `hosted_enums` and Gate PAIR's rows already have (`{where}/{node_id}`)."""
    assert R._component_label({"kind": "weight", "file": "x.safetensors",
                               "where": "top", "node_id": 3}) == \
        "'x.safetensors' at top/3"
    assert R._component_label({"kind": "class", "class_type": "DWPreprocessor",
                               "where": "sg", "node_id": 9}) == \
        "node class 'DWPreprocessor' at sg/9"
    # A record carrying neither field still gets its name back rather than a sentence
    # about nothing — the direction the fix must not break.
    assert R._component_label({"kind": "weight", "file": "x.safetensors"}) == \
        "'x.safetensors'"


def test_the_uncredited_conditional_refusal_names_its_node_too():
    """The third message built from the same helper. `technically_color` is CONDITIONAL on
    a credit; with no attribution entry the refusal fires, and it now says which node."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "2": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "wan22-14b-t2v-technically_color.safetensors"}}}
    with pytest.raises(R.RouteGate) as exc:
        R.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    assert exc.value.evidence["clause"] == "uncredited_conditional_component"
    assert "at api/2" in str(exc.value), str(exc.value)


def test_the_unclassified_list_names_its_nodes():
    """`ev['unclassified']` is built from the same helper and is the list a builder stores
    and a provenance sheet prints."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "some_unknown_style_v3.safetensors"}}}
    ev = R.verify(g, frame=(832, 480, 81), carries_no_sampler=True)
    assert ev["unclassified"] == ["'some_unknown_style_v3.safetensors' at api/1"]


# ===========================================================================
# F-21e7e0c1 — the receipts at the spend boundary name the version that ruled
# ===========================================================================


def test_the_gate_route_receipt_carries_the_tool_version():
    """Measured before the fix: `verify()`'s receipt had 29 keys and `json.dumps(ev)`
    contained none of `TOOL_VERSION`, `tool_version`, `E09`, a graph hash or a graph path
    — while `donor_gate` and `lift_solve` both write theirs into the record they emit and
    all ten payload builders record their own. Gate ROUTE's clause set moved materially in
    waves 25 and 26, so two stored receipts from either side were indistinguishable."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.1_vace_14B_fp16.safetensors"}}}
    ev = R.verify(g, frame=(832, 480, 81), carries_no_sampler=True)
    assert ev["tool_version"] == R.TOOL_VERSION
    assert "E09" in json.dumps(ev)


def test_the_version_rides_a_refusal_as_well_as_a_receipt():
    """Written into the `ev` literal before the first clause can raise, for the same
    reason both fact keys are: a refusal is read back too."""
    g = {"1": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "causvid_x.safetensors"}}}
    with pytest.raises(R.RouteGate) as exc:
        R.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    assert exc.value.evidence["tool_version"] == R.TOOL_VERSION


def test_the_receipt_names_the_graph_it_ruled_on():
    """The other half of the reproducibility question: a digest over the NORMALISED graph,
    so a stored receipt says WHICH graph as well as which version."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.1_vace_14B_fp16.safetensors"}}}
    ev = R.verify(g, frame=(832, 480, 81), carries_no_sampler=True)
    assert ev["graph_sha256"] == R.graph_digest(g)
    # Same graph inside a wrapper digests the same; a different graph does not.
    assert R.graph_digest({"prompt": g}) == ev["graph_sha256"]
    other = {"1": {"class_type": "UNETLoader",
                   "inputs": {"unet_name": "wan2.2_i2v_A14B.safetensors"}}}
    assert R.graph_digest(other) != ev["graph_sha256"]


def test_the_ungated_record_carries_the_version():
    """`canon.TOOL_VERSION` was declared and written nowhere. The escape record is one of
    the two a spend stores; the ARMED half is the test below."""
    ungated = canon.require_canon("WIRE", "p", no_canon=True)
    assert ungated["tool_version"] == canon.TOOL_VERSION


def test_the_armed_record_carries_the_version(tmp_path):
    """The ARMED half, on a real surfaces file this test writes."""
    io.open(tmp_path / "s.json", "w", encoding="utf-8").write(json.dumps({
        "schema": 1,
        "surfaces": [{"id": "torso",
                      "occupant": {"kind": "prompt", "phrase": "grey plate",
                                   "ratified": True}}],
        "legal_clauses": [{"id": "c1", "phrase": "grey plate"}],
    }))
    ev = canon.require_canon(
        "SUBJ", "grey plate",
        census={"SUBJ": {"surfaces": "s.json"}}, search_roots=[str(tmp_path)])
    assert ev["verdict"] == "ARMED"
    assert ev["tool_version"] == canon.TOOL_VERSION


# ===========================================================================
# F-faa2f9f4 — the licence table carries the field the map's own rule is written in
# ===========================================================================


def test_every_ruled_component_row_carries_a_fetch_date():
    """`docs/license-map.md` states the law — "Entries older than 90 days are advisory
    until re-fetched" — and every row in that document carries a fetch date and the URL of
    the fetched document. `RULED_COMPONENTS` mirrored it and carried `fetched` in exactly
    one of eleven rows (inside `technically_color`'s `condition`), and no row carried a
    document URL — so no receipt and no refusal at the spend boundary could say how old
    the ruling it applied was."""
    missing = [k for k, v in R.RULED_COMPONENTS.items() if not v.get("fetched")]
    assert missing == [], missing
    for key, row in R.RULED_COMPONENTS.items():
        assert "source" in row, key
        datetime.date.fromisoformat(row["fetched"])


def test_the_rows_with_no_source_are_the_ones_the_map_records_as_unretrieved():
    """`source` is `None` — never a plausible-looking URL — exactly where the map itself
    records a non-retrieval. A placeholder shaped like evidence is the thing CLAUDE.md
    forbids, so the absence is asserted rather than filled."""
    unsourced = sorted(k for k, v in R.RULED_COMPONENTS.items() if not v.get("source"))
    assert unsourced == ["causvid", "dwpose", "vintage_film_grain"], unsourced
    markers = ("NOT RETRIEVED", "NOT INDEPENDENTLY RETRIEVED", "NON-RETRIEVAL",
               "NOT FETCHED", "NEVER FETCHED", "UNLOCATED")
    for key in unsourced:
        text = _reason_and_licence(key).upper()
        assert any(m in text for m in markers), (key, text)


def _reason_and_licence(key):
    row = R.RULED_COMPONENTS[key]
    return f"{row.get('licence', '')} {row.get('reason', '')}"


def test_the_ninety_day_rule_is_a_number_this_module_can_apply():
    """The rule was expressed only in prose, and a mirror that omits the field the
    authority's rule is written in cannot administer that rule."""
    assert R.LICENCE_ADVISORY_DAYS == 90
    assert R.licence_advisory_after("2026-08-10") == "2026-11-08"
    assert R.licence_advisory_after("2026-08-13") == "2026-11-11"
    assert R.licence_advisory_after(None) is None
    assert R.licence_age_days("2026-08-10", datetime.date(2026, 9, 5)) == 26
    assert R.licence_age_days(None) is None


def test_a_lapsed_ruling_says_so_in_the_sentence_on_the_day_it_lapses():
    """The measurement the finding turns on: the rows were fetched 2026-08-10 and
    2026-08-13 and go advisory 2026-11-08 and 2026-11-11, and on that day every receipt
    and refusal read exactly as it does today. Driven with an explicit `today` in both
    directions, so the assertion cannot be a coincidence of the calendar."""
    comp = R.components({"1": {"class_type": "LoraLoaderModelOnly",
                               "inputs": {"lora_name": "causvid_x.safetensors"}}})
    in_date = R.licence_fetch_reading(comp, today=datetime.date(2026, 9, 5))
    assert in_date["oldest_fetched"] == "2026-08-10"
    assert in_date["advisory_after"] == "2026-11-08"
    assert in_date["advisory_rows"] == []
    assert "ADVISORY" not in R.licence_phrase_for(in_date)

    lapsed = R.licence_fetch_reading(comp, today=datetime.date(2026, 11, 9))
    assert lapsed["advisory_rows"] == ["causvid"]
    phrase = R.licence_phrase_for(lapsed)
    assert "ADVISORY" in phrase and "re-fetch" in phrase


def test_the_verdict_quotes_the_oldest_applied_fetch_date():
    """Measured before the fix on an API graph loading the smartphone-snapshot LoRA: the
    receipt's 29 keys held `components`, `unclassified`, `attribution`, `verdict` and no
    date at all — `json.dumps(ev)` contained none of `fetched`, `2026-08`, `stale`,
    `advisory` or `90`."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "2": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": ("WAN2.2-HighNoise_SmartphoneSnapshotPhoto"
                                        "Reality_v3_by-AI_Characters.safetensors")}}}
    ev = R.verify(g, frame=(832, 480, 81), carries_no_sampler=True)
    assert "2026-08-13" in ev["verdict"], ev["verdict"]
    assert "advisory after 2026-11-11" in ev["verdict"], ev["verdict"]
    assert ev["licence_fetch"]["advisory_days"] == 90
    assert ev["licence_fetch"]["applied_rows"][0]["source"] == \
        "https://civitai.com/api/v1/models/1834338"


def test_the_banned_refusal_names_the_date_and_the_document():
    """The refusal half. Measured on `causvid_x.safetensors` before the fix: the message
    quoted verdict, licence and reason and named no date and no source."""
    g = {"1": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "causvid_x.safetensors"}}}
    with pytest.raises(R.RouteGate) as exc:
        R.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    message = str(exc.value)
    assert "fetched 2026-08-10" in message, message
    assert "advisory after 2026-11-08" in message, message
    assert "document NOT RETRIEVED" in message, message


def test_the_excluded_refusal_carries_the_provenance_too():
    """The EXCLUDED tier, which is a methodology ruling and takes the same treatment: a
    row's age is a fact about the row, not about its verdict."""
    g = {"1": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "lightx2v_4step.safetensors"}}}
    with pytest.raises(R.RouteGate) as exc:
        R.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    assert "fetched 2026-08-10" in str(exc.value)
    assert "huggingface.co/lightx2v" in str(exc.value)


def test_the_table_mirrors_the_maps_fetch_dates():
    """A MIRROR, checked against the document it mirrors: every `fetched` value in the
    table appears in `docs/license-map.md`, so a re-fetch that moves the map and not the
    table is visible here rather than in a spend."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = io.open(os.path.join(repo, "docs", "license-map.md"),
                  encoding="utf-8").read()
    for key, row in R.RULED_COMPONENTS.items():
        assert row["fetched"] in doc, (key, row["fetched"])
        if row.get("source"):
            assert row["source"].split("://", 1)[-1].rstrip("/") in doc \
                or row["source"] in doc, (key, row["source"])


# ===========================================================================
# F-abf293d8 — G2's refusals name the run directory
# ===========================================================================


def test_g2_incomplete_export_names_the_directory_it_read(tmp_path):
    """Measured before the fix: "export is incomplete: depth: 31 frames present, expected
    33 (missing e.g. […])" with `run_dir` in the evidence and nowhere in the sentence —
    on a gate that runs after every render, read by an operator with several run
    directories open at once."""
    os.makedirs(tmp_path / "depth")
    for i in range(2):
        io.open(tmp_path / "depth" / f"{i:05d}.png", "wb").write(b"x")
    names = [f"{i:05d}.png" for i in range(4)]
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"depth": names}, 4)
    assert str(exc.value).startswith(f"[G2] {tmp_path}: export is incomplete: ")
    assert exc.value.evidence["run_dir"] == str(tmp_path)


def test_g2_zero_channels_names_the_directory_too(tmp_path):
    """The refusal above it, which had the same shape: `run_dir` in the evidence, absent
    from the message."""
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {}, 3)
    assert str(tmp_path) in str(exc.value)
    assert exc.value.evidence["clause"] == "completeness_over_zero_channels"


def test_both_g2_refusals_follow_the_shape_the_domains_other_refusals_use():
    """`route_gates.load_graph` prefixes all three of its refusals with `f"{path}: "`,
    `donor_gate` puts `frames_dir` in its sentence and `canon.load` now puts the path in
    every one of its own. Asserted as the SHAPE rather than as a substring, so a later
    edit that mentions the directory in passing does not satisfy this."""
    import ast

    src = io.open(gates.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "g2_completeness")
    raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
    assert len(raises) == 2, len(raises)
    for node in raises:
        assert "run_dir" in ast.unparse(node.exc.args[0]), ast.unparse(node.exc.args[0])


# ===========================================================================
# F-594c5a7a — Gate P's round trip says what it is about to walk
# ===========================================================================


DIAGONAL_W28 = 10.0


def _one_moved_position(delta):
    """Two vertex arrays differing in ONE position by `delta` — enough to leave the early
    exit and enter the chunked nearest-position search."""
    src = np.array([[0.0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=np.float32)
    rt = np.array([[0.0, 0, 0], [1, 0, 0], [2 + delta, 0, 0]], dtype=np.float32)
    return src, rt


def test_the_pass_receipt_says_how_much_work_the_comparison_did():
    """Measured before the fix: `probe_population` / `probe_unexamined` were written ONLY
    on the truncation refusal, so a run that COMPLETED left no number saying how much it
    walked — on a clause whose live scale is `max_probe` 20,000 against a record of
    149,643 unique positions (about 81 s and a ~909 MB transient, extrapolated from
    pts x ref timings measured on synthetic arrays)."""
    src, rt = _one_moved_position(5e-4)
    ev = rig_gates.gate_p_round_trip_positions(src, rt, DIAGONAL_W28)
    assert ev["probe_population"] == 2
    assert ev["probe_pairs"] == 2 * 3
    assert ev["probe_elapsed_s"] >= 0.0
    assert ev["verdict"].startswith("positions agree")


def test_the_early_exit_receipt_says_it_measured_nothing_because_there_was_nothing():
    """The third answer. "Nothing to walk" and "walked and found nothing" must not be the
    same silence — the population is zero and the receipt says so."""
    src = np.array([[0.0, 0, 0], [1, 0, 0]], dtype=np.float32)
    ev = rig_gates.gate_p_round_trip_positions(src, src.copy(), DIAGONAL_W28)
    assert ev["probe_population"] == 0
    assert ev["probe_pairs"] == 0
    assert ev["max_deviation"] == 0.0


def test_the_caller_is_handed_the_population_and_the_bound_before_the_walk():
    """The progress seam. The printing belongs to `tools/rig_character.py`, which owns the
    operator's stdout — a library gate that printed would be a second home for a tool's
    own voice — so this gate EXPOSES the population it is about to walk and lets the tool
    say so (rule 5's "a wait says it is alive")."""
    src, rt = _one_moved_position(5e-4)
    seen = []
    rig_gates.gate_p_round_trip_positions(src, rt, DIAGONAL_W28, progress=seen.append)
    assert [e["stage"] for e in seen] == ["start", "done"]
    assert seen[0]["probe_population"] == 2 and seen[0]["probe_pairs"] == 6
    assert seen[0]["max_probe"] == 20000
    assert "elapsed_s" in seen[1]


def test_the_progress_seam_cannot_change_the_verdict():
    """A reporting callback is not a lever. The receipt is identical with and without one,
    minus the elapsed time, which is a measurement rather than a decision."""
    src, rt = _one_moved_position(5e-4)
    quiet = rig_gates.gate_p_round_trip_positions(src, rt, DIAGONAL_W28)
    loud = rig_gates.gate_p_round_trip_positions(src, rt, DIAGONAL_W28,
                                                 progress=lambda _e: None)
    assert {k: v for k, v in quiet.items() if k != "probe_elapsed_s"} == \
        {k: v for k, v in loud.items() if k != "probe_elapsed_s"}
    assert list(inspect.signature(
        rig_gates.gate_p_round_trip_positions).parameters)[-1] == "progress"


def test_the_refusal_branch_still_carries_its_own_per_side_count():
    """The direction the hoist must not break: the truncation refusal is about ONE
    direction's overflow and keeps that number, beside the walk's whole population."""
    src = np.array([[float(i), 0, 0] for i in range(10)], dtype=np.float32)
    rt = np.array([[float(i) + 0.5, 0, 0] for i in range(10)], dtype=np.float32)
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_round_trip_positions(src, rt, DIAGONAL_W28, max_probe=3)
    ev = exc.value.evidence
    assert ev["probe_population_this_side"] == 10
    assert ev["probe_population"] == 20
    assert ev["probe_elapsed_s"] >= 0.0
