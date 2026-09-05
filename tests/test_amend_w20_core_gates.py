"""Wave 20 (core-gates): the walk's own identity, its node containers, and the positional
tables it reads by index.

Wave 18 keyed Gate S's seed resolution on the pair `(where, id)`, gave `definitions` and
`definitions.subgraphs` the refusal their entries already had, and taught the hosted enum
block that a converted widget shifts a positional read. Wave 19's auditors measured that
all three fixes stop one level short of the thing they are about:

  * **F-400c1df4** `where` is not an identity. `_iter_definitions` refuses a duplicate
    blueprint `id` and nothing refuses the LABEL the walk actually emits, so two
    blueprints sharing a `name`, two declaring neither field, or one whose `name` is the
    walk's own level label `top`, collapse the `(where, id)` pair Gate S keys on — and
    Gate S RETURNED a PASS naming `expert/3, expert/3` while a blueprint node ran seed
    999999999;

Every test here goes RED on the tree at base `475f4eb`, and each red is proved on the
OPERAND the finding named — the auditor's two-blueprint Gate S graphs — and on that operand's enumerated
SIBLINGS.
"""

import json
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from armature_core import route_gates as RG  # noqa: E402

BASE = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
T2V_BASE = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
BANNED = "causvid_x.safetensors"


# =======================================================================================
# F-400c1df4 · CRITICAL (unanimous) — `where` is the label the walk EMITS, and nothing
# made it unique. The id clause bounds one field over from the invariant Gate S rests on.
# =======================================================================================


def _label_graph(first, second, ids=("bp1", "bp2")):
    """The auditor's graph: a live top-level `KSamplerAdvanced` (add_noise=enable, seed 7)
    plus two blueprints each holding their OWN node 3 — the first exempt, the second
    adding noise at seed 999999999. `first` / `second` are the blueprints' `name` fields
    (`None` deletes the key); `ids` are their `id` fields (`None` deletes both)."""
    d1 = {"nodes": [{"id": 3, "type": "KSamplerAdvanced",
                     "widgets_values": ["disable", 7, "fixed"]}]}
    d2 = {"nodes": [{"id": 3, "type": "KSamplerAdvanced",
                     "widgets_values": ["enable", 999999999, "fixed"]}]}
    if first is not None:
        d1["name"] = first
    if second is not None:
        d2["name"] = second
    if ids is not None:
        d1["id"], d2["id"] = ids
    return {"nodes": [
        {"id": 1, "type": "UNETLoader", "widgets_values": [T2V_BASE]},
        {"id": 2, "type": "KSamplerAdvanced", "widgets_values": ["enable", 7, "fixed"]},
    ], "definitions": {"subgraphs": [d1, d2]}}


def test_two_blueprints_sharing_a_name_refuse_instead_of_grading_the_wrong_node():
    """RED on base: with DISTINCT ids `bp1`/`bp2` and the same `name: "expert"`,
    `seeds()` correctly returned `[('top',2,7), ('expert',3,7), ('expert',3,999999999)]`
    and `gate_s_registration(g, [7])` RETURNED `seeds_noise_bearing: 1 of 3` with the
    verdict "... 2 exempted by add_noise=disable (node(s) expert/3, expert/3)". Seed
    999999999 was never graded: the second colliding record read its `add_noise` off the
    FIRST node the walk yielded, because `next(... if (w, str(id)) == ...)` is TOTAL but
    not UNIQUE."""
    g = _label_graph("expert", "expert")
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    ev = exc.value.evidence
    assert ev["clause"] == "duplicate_subgraph_label"
    assert ev["label"] == "expert"
    assert ev["collides_with"] == {"kind": "subgraph", "index": 0, "id": "bp1"}
    assert ev["gate"] == "ROUTE" and ev["andon"] == "RouteGate"


def test_two_blueprints_declaring_neither_a_name_nor_an_id_refuse():
    """The auditor's second reproduction. With no `name` and no `id` on either blueprint
    `where` falls to the literal `"subgraph"` for BOTH, the `bid is not None` guard skips
    the duplicate-id clause entirely, and the same green PASS came back naming
    `subgraph/3, subgraph/3`."""
    g = _label_graph(None, None, ids=None)
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    assert exc.value.evidence["clause"] == "duplicate_subgraph_label"
    assert exc.value.evidence["label"] == "subgraph"


def test_a_blueprint_labelled_top_collides_with_the_walks_own_level():
    """The sibling neither reproduction reaches, and it needs only ONE blueprint: `top` is
    the label `_walk_nodes` gives the save-format graph's own `nodes` array. Measured on
    base in this worktree — a live top-level `KSamplerAdvanced` id 2, an exempt top-level
    id 3, and a blueprint NAMED "top" holding its own id 3 at seed 999999999:
    `seeds()` returned `[('top',2,7), ('top',3,7), ('top',3,999999999)]` and Gate S
    RETURNED "1 noise-bearing seed(s) of 3 ... 2 exempted by add_noise=disable (node(s)
    top/3, top/3)" with `seeds_exempt_nodes` printing one identity twice."""
    g = {"nodes": [
        {"id": 1, "type": "UNETLoader", "widgets_values": [T2V_BASE]},
        {"id": 2, "type": "KSamplerAdvanced", "widgets_values": ["enable", 7, "fixed"]},
        {"id": 3, "type": "KSamplerAdvanced", "widgets_values": ["disable", 7, "fixed"]},
    ], "definitions": {"subgraphs": [
        {"id": "bp1", "name": "top", "nodes": [
            {"id": 3, "type": "KSamplerAdvanced",
             "widgets_values": ["enable", 999999999, "fixed"]}]}]}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    ev = exc.value.evidence
    assert ev["clause"] == "duplicate_subgraph_label"
    assert ev["label"] == "top"
    assert ev["collides_with"]["kind"] == "reserved_level_label"


def test_a_blueprint_labelled_api_is_refused_on_the_same_clause():
    """`api` is the other label `_walk_nodes` emits. It cannot collide inside one graph
    today — the API branch returns before `_iter_definitions` runs — and it is reserved
    explicitly rather than by omission, the way `CONDITIONING_FAMILY_EXEMPT` records the
    classes that pair with nothing."""
    g = _label_graph("api", "other")
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(g)
    assert exc.value.evidence["clause"] == "duplicate_subgraph_label"
    assert exc.value.evidence["label"] == "api"


def test_the_auditors_control_with_distinct_names_still_grades_the_seed():
    """The control the auditor measured green-to-red against: the identical graph with
    the names distinct REFUSED "node 3 would run seed 999999999, which the committed list
    [7] does not pre-register". The fix may not turn that seed refusal into a label
    refusal."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(_label_graph("first", "second"), [7])
    assert exc.value.evidence["clause"] == "gate_s_registration"
    assert "999999999" in str(exc.value)


def test_the_duplicate_id_clause_still_fires_first_when_both_collide():
    """The auditor's other control: with the ids EQUAL the walk refused
    `duplicate_subgraph_id`. Two ambiguities are two facts and the id clause is the one
    wave 18 earned, so it keeps the graph on which both apply."""
    g = _label_graph("first", "second", ids=("bp", "bp"))
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(g)
    assert exc.value.evidence["clause"] == "duplicate_subgraph_id"


@pytest.mark.parametrize("d,expected", [
    ({"id": "bp7", "name": "expert"}, "expert"),
    ({"id": "bp7"}, "bp7"),
    ({}, "subgraph"),
])
def test_the_emitted_label_itself_is_unchanged(d, expected):
    """SEAM 1's promise to builders: nothing about `where` moves on a graph the walk
    admits. A labelled blueprint reads its `name`, one with only an `id` reads the `id`,
    one with neither reads the literal `"subgraph"` — so every Gate S receipt string, the
    `level/id` verdict wording and `seeds_exempt_nodes`' pairs stay byte-identical."""
    blueprint = dict(d, nodes=[{"id": 9, "type": "LoraLoaderModelOnly",
                                "widgets_values": ["clean_style.safetensors"]}])
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [T2V_BASE]}],
         "definitions": {"subgraphs": [blueprint]}}
    assert [c["where"] for c in RG.components(g)] == ["top", expected]


def test_a_self_referencing_blueprint_still_terminates():
    """The label clause sits AFTER the cycle guard's `continue`, so a blueprint that
    contains itself declares its label ONCE. Cycle protection is the guard's other job and
    the gate before a spend must halt or answer, never hang."""
    inner = {"id": "loop", "name": "loop", "nodes": [
        {"id": 20, "type": "LoraLoaderModelOnly",
         "widgets_values": ["clean_style.safetensors"]}]}
    inner["definitions"] = {"subgraphs": [inner]}
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [T2V_BASE]}],
         "definitions": {"subgraphs": [inner]}}
    assert [c["file"] for c in RG.components(g)] == [T2V_BASE, "clean_style.safetensors"]


def test_a_deeper_self_reference_terminates_too():
    """A -> B -> A, the wave-18 control. The recursion path pops on the way back up and
    the label ledger does not, which is the difference between a cycle guard and the
    ambiguity refusal."""
    a = {"id": "A", "name": "A", "nodes": [
        {"id": 30, "type": "LoraLoaderModelOnly", "widgets_values": ["a.safetensors"]}]}
    b = {"id": "B", "name": "B", "nodes": [
        {"id": 31, "type": "LoraLoaderModelOnly", "widgets_values": ["b.safetensors"]}],
        "definitions": {"subgraphs": [a]}}
    a["definitions"] = {"subgraphs": [b]}
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [T2V_BASE]}],
         "definitions": {"subgraphs": [a]}}
    assert [c["file"] for c in RG.components(g)] == [
        T2V_BASE, "a.safetensors", "b.safetensors"]


def test_the_id_ledger_and_the_label_ledger_do_not_cross():
    """The two ledgers are separate namespaces, and one dict keyed by both would have made
    an ordinary graph refuse. Blueprint one declares the ID "bp1" and the LABEL "keep";
    blueprint two declares the ID "bp2" and the LABEL "bp1". Nothing is ambiguous — the
    labels are distinct and so are the ids — so the walk proceeds and both `where` values
    are the ones `seeds()` and Gate S will key on."""
    g = _label_graph("keep", "bp1")            # second blueprint's NAME is the first's ID
    assert [s["where"] for s in RG.seeds(g)] == ["top", "keep", "bp1"]


# =======================================================================================
# The halt line an operator actually reads (wave-18 rule 4), and the family census.
# =======================================================================================


HALT_ROUTES = [
    ("duplicate_subgraph_label", "gate_saved_graph.py", "SAVED_ADMISSION_HALT"),
]


def _refusal_for(clause):
    """The REAL call that raises `clause`, so the halt record read below is the one an
    operator gets rather than a hand-built exception wearing the clause's name."""
    if clause == "duplicate_subgraph_label":
        return lambda: RG.components(_label_graph("expert", "expert"))
    raise AssertionError(clause)


@pytest.mark.parametrize("clause,tool,sentinel", HALT_ROUTES)
def test_the_halt_line_an_operator_reads_names_the_andon_that_pulled(
        clause, tool, sentinel, capsys):
    """Wave-18 rule 4, read rather than assumed. Two of this wave's three findings ended
    in a RETURNED green receipt and the third's API mirror in a bare `AttributeError`; a
    refusal that does not reach the tool's exit-2 `<TOOL>_HALT` branch is not a refusal an
    operator sees."""
    from blender_stub import exit_code_of_main_block

    code, escaped = exit_code_of_main_block(
        tool, raiser=_refusal_for(clause),
        argv=["python", tool, "--out", "nope"])
    out = capsys.readouterr().out
    assert escaped is None, f"{tool}: {escaped!r} escaped the handler"
    assert code == 2, f"{tool} ({clause}): exit {code!r}, the contract says 2 for a gate"
    lines = [ln for ln in out.splitlines() if ln.split(" ", 1)[0] == sentinel]
    assert len(lines) == 1, f"{tool} ({clause}): {len(lines)} sentinel line(s)"
    rec = json.loads(lines[0][len(sentinel):].strip())
    ev = rec["evidence"]
    assert isinstance(ev, dict), f"{tool} ({clause}): evidence {ev!r}"
    assert ev["clause"] == clause
    assert ev["andon"] == rec["error"] == "RouteGate"
    assert ev["gate"] == "ROUTE"


def test_every_clause_added_this_wave_raises_a_named_subclass_with_evidence():
    """Gates raise, never `assert`; the refusal names the andon that pulled and carries
    the operand. Driven again under `-O` by the suite's own `-O` leg."""
    from armature_core.errors import ArmatureError

    for clause, _tool, _sentinel in HALT_ROUTES:
        with pytest.raises(RG.RouteGate) as exc:
            _refusal_for(clause)()
        assert isinstance(exc.value, ArmatureError), clause
        assert exc.value.evidence["clause"] == clause
        assert exc.value.evidence.get("andon") == "RouteGate"
        assert exc.value.evidence.get("gate") == "ROUTE"
