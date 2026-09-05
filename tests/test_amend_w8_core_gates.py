"""Wave 8 (core-gates): the receipt names the andon that pulled — every raise, derived.

**Why this file is an AST walk and not a list.** The wave-6 census
(`tests/test_gates.py::_evidence_dicts_missing_the_gate_key`) returned `[]` on a tree
carrying dozens of evidence dicts with no `gate` key, because its population was TYPED
rather than DERIVED: line 504 skipped any function that did not raise a class whose NAME
contains the substring "Gate" — which excludes `G1GeneratorLegality`, `G2Completeness`,
`G4BboxSanity`, `G5ConventionConformance` and `G6SubjectMotion` outright — and line 510
inspected only `ev = {...}` / `evidence = {...}` dict LITERALS, so an inline dict passed
at the raise and an `ev = dict(...)` were both invisible. A census that cannot see its
own population is the defect class wave 8 exists to close.

So the population here is derived by walking **every `ast.Raise`** in the eleven
`armature_core` files this domain owns, keeping the ones whose exception class is a
`GateFailure` subclass, and resolving each raise's evidence argument to a key set
through the four shapes this tree actually uses:

    raise X(msg, {"k": v})                 an inline dict literal
    raise X(msg, ev)                       a name, resolved from its assignments,
                                           its `ev["k"] = ...` subscripts and its
                                           `ev.update({...})` calls in the same function
    raise X(msg, dict(ev, k=v))            a `dict()` call, args and kwargs both
    raise X(msg, dict({...}, k=v))         the same over a comprehension or literal

Three properties are asserted: the derived population's SIZE and MEMBERSHIP (so a raise
added later fails loudly rather than joining silently), that every member's evidence
carries `gate` and `andon`, and that the `gate` value AGREES with the raised class's own
`gate` attribute — the F-1844be26 defect, where `gate_s_registration` built
`{"gate": "S"}` and raised `RouteGate`, whose id is `ROUTE`, while `"S"` is already the
id of a *different* andon (`errors.GateSSeedRegistration`) carrying different keys.

`stage_render.py:509-510` prints `GATE_FAILURE <exc.gate>` and `GATE_EVIDENCE <json of
exc.evidence>` as two separate lines, and `rig_character._write_halt` and its siblings
read the same two sources — so a reader holding only the JSON half must be able to say
which andon pulled, and the prose half is not enough because ids are shared across andon
families ("D" by `GateDDeterminism` and `GatePartsDeterminism`, "ALPHA" by `AlphaGate`
and `TurnaroundAlphaGate`).
"""

import ast
import os

import pytest

from conftest import TOOLS, gate_failure_subclasses

CORE = os.path.join(TOOLS, "armature_core")

#: The eleven files this domain owns. The wider sweep over every `armature_core` module
#: is the tests domain's (wave 8, routed) — this file polices the population core-gates
#: is responsible for, and says so rather than implying it covers the package.
OWNED = (
    "__init__.py", "gates.py", "route_gates.py", "rig_gates.py", "donor_gate.py",
    "canon.py", "canon_census.py", "errors.py", "subject.py", "shotspec.py", "cli.py",
)

#: Every `(file, line, class)` in `OWNED` that raises a `GateFailure` subclass, measured
#: 2026-09-04 after the wave-8 amend. Asserted by SIZE and MEMBERSHIP, so a raise added
#: later joins this list deliberately instead of arriving unpoliced.
#: Wave 12 (core-gates) moved five of these counts, +7 raises in total: the licence
#: clause's CONDITIONAL tier (two RouteGate refusals plus `attribution_entry_for`'s), the
#: save-format node walk's `unreadable_node`, and four empty-population/non-finite andons
#: (`gate_b_batching`, `g5_openpose_conformance`, `gate_n_names`, `gate_d_determinism`).
#: Recorded in the same commit as the raises, which is what this ratchet asks for.
RECORDED_GATE_RAISES = {
    ("canon.py", "GateCanon"): 1,
    # WAVE 22 (core-gates, F-682ce228): the file's first raise. `canon_census.CENSUS` is a
    # hand-edited table whose docstring states the contract the spend helpers rest on, and
    # NO clause checked a row against it: a misspelled `surface:` key returned
    # `verdict: UNGATED` from `--no-canon` for a subject that HAS a ratified surfaces file
    # (the `clause: checkbox` refusal inoperative because `.get` reads None), an
    # identity-only row with no `reason` announced an escape it could not explain, and a
    # non-mapping row raised a bare `AttributeError` from BOTH `require_canon` and
    # `resolve`. ONE raise site — `_refuse`, the module's own andon, reached by six clauses
    # (`census_is_not_a_mapping`, `subject_is_not_a_name`, `row_is_not_a_mapping`,
    # `unknown_census_key`, `surfaces_is_not_a_path`, `hole_without_a_reason`), the shape
    # `canon._raise` already uses. RE-DERIVED with `==` in this worktree; BRANCH-LOCAL.
    ("canon_census.py", "GateCanon"): 1,
    # WAVE 18: 6 → 10 (core-gates, F-04197047). `_readable_landmark_row` — Gate DONOR
    # guarded its EMPTY population and never the SHAPE of a row it reads, so a
    # 17-landmark (COCO-topology) record raised IndexError, a None landmark TypeError
    # and a dict-shaped landmark KeyError — none of them an ArmatureError, so
    # `lift_clip`'s halt handler wrote a halt line naming no gate. Four clauses: the
    # `image` that is not a sequence, the sequence too short to hold index 28, the
    # landmark that is not an (x, y) pair, the coordinate that is not a number.
    ("donor_gate.py", "DonorGate"): 10,
    ("gates.py", "G1GeneratorLegality"): 2,
    ("gates.py", "G2Completeness"): 2,
    ("gates.py", "G4BboxSanity"): 4,
    ("gates.py", "G5ConventionConformance"): 2,  # +1 w12: empty-reference refusal
    ("gates.py", "G6SubjectMotion"): 2,
    ("gates.py", "GateBBatching"): 3,  # +1 w12: expectation-of-zero refusal
    ("gates.py", "GateRRoundTrip"): 4,
    # WAVE 18: 4 → 5 (core-gates, F-d83e5879). `registry_member_not_an_int` — the gate
    # guarded the SEED's type and never the COMMITTED LIST's, and `in` is `==`
    # membership, so `[True]`, `[False]` and `[1.0]` each returned "seed is
    # pre-registered". Same clause closes the bare TypeError from
    # `sorted(registry).index(seed)` on a mixed-type registry.
    ("gates.py", "GateSSeedRegistration"): 5,  # +1 w14: a DECLARED but empty registry
                                               # (F-b4706738) — `if not registry:`
                                               # collapsed None and [], so 'N/A — pre-
                                               # registered no seeds' was stated over a
                                               # list the caller declared and dropped
    ("rig_gates.py", "GateDDeterminism"): 3,  # +1 w12: degenerate bbox_diagonal
    ("rig_gates.py", "GateNNames"): 2,  # +1 w12: empty registry
    ("rig_gates.py", "GatePRestPose"): 12,
    ("route_gates.py", "PairGate"): 3,
    # WAVE 16: 36 → 38 (core-gates, SEAM 5 §4). `_unreadable_level` — ONE raise reached from
    # three container levels (`definitions`, `definitions.subgraphs`, a non-dict definition
    # entry), all clause `unreadable_node` — and Gate S's andon for a graph where `seeds()`
    # found samplers and every one carries `add_noise=disable`, which used to return a PASS
    # over an empty population. Carried from their branch measurement, not measured here:
    # this entry is RED on the tests branch (which reads 36) and expected green at merge.
    # WAVE 18: 38 → 43 (core-gates). `_api_entry_kind`'s `unreadable_node` — the API
    # branch answered a node-shaped mapping that lost its `class_type` with a silent
    # `continue` while the save-format branch beside it raised (F-7eb1ba2a);
    # `_iter_definitions`' `duplicate_subgraph_id` — the cycle guard keyed on the
    # blueprint's `id` VALUE and dropped the second of two blueprints declaring one id
    # (F-039202b9); Gate S's `seed_node_unresolvable` — the seed-record lookup is now
    # keyed on the pair `(where, id)` and is TOTAL (F-10af549a); and
    # `_hosted_enum_shift_andon`'s two, `converted_widget_shifts_enum_indices` and
    # `hosted_enum_widgets_truncated` (F-7854d570).
    # WAVE 20 (core-gates, 2026-09-05): +3 in `route_gates.RouteGate`, RE-DERIVED with
    # `==` in this worktree against the merged base `475f4eb`, which every census here read
    # GREEN first. BRANCH-LOCAL — the coordinator re-measures at the merge.
    #   `_iter_definitions`' `duplicate_subgraph_label` — the LABEL the walk EMITS, which
    #   the id clause did not bound, so two blueprints under one `name` (or two under
    #   neither field, or one named `top`) collapsed the `(where, id)` pair Gate S keys on
    #   (F-400c1df4).
    #   `_readable_containers`' `unreadable_node` — the node's OWN `widgets_values` /
    #   `inputs` container, where a BANNED weight spelled inside a mapping or a bare string
    #   was read as empty and `verify` returned GREEN (F-f9ab0645).
    #   `_converted_widget_shift_andon`'s `converted_widget_shifts_recorded_indices` — the
    #   converted-widget shift clause over `LATENT_NODES`, `CAMERA_NODES` and `SEED_NODES`,
    #   which wave 18 gave `HOSTED_ENUM_WIDGETS` alone (F-29e1cbb7).
    ("route_gates.py", "RouteGate"): 46,  # +3 w12: unreadable_node,
                                          # uncredited_conditional_component,
                                          # attribution_for_unconditional_row
                                          # +1 w14: orphan_attribution (F-74787978) — the
                                          # converse of the conditional clause: a credit
                                          # naming no component the graph loads. w14 also
                                          # MOVED `unreadable_node` into `_readable_node`
                                          # so the nested walk shares it (F-b44c880d);
                                          # one site before, one site after.
}


def _dict_keys(node):
    """key name -> the VALUE node standing at it, for a dict literal."""
    if isinstance(node, ast.Dict):
        return {k.value: v for k, v in zip(node.keys, node.values)
                if isinstance(k, ast.Constant)}
    return None


def _resolve(fn, expr):
    """The key -> key-node mapping an evidence expression carries, or None."""
    literal = _dict_keys(expr)
    if literal is not None:
        return dict(literal)
    if isinstance(expr, ast.Call) and getattr(expr.func, "id", "") == "dict":
        keys = {}
        for arg in expr.args:
            keys.update(_resolve(fn, arg) or {})
        for kw in expr.keywords:
            if kw.arg:
                keys[kw.arg] = kw.value
        return keys
    if isinstance(expr, ast.Name):
        keys, seen = {}, False
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == expr.id:
                        got = _resolve(fn, node.value)
                        if got is not None:
                            keys.update(got)
                            seen = True
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == expr.id
                            and isinstance(target.slice, ast.Constant)):
                        keys[target.slice.value] = node.value
                        seen = True
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "update"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == expr.id):
                for arg in node.args:
                    keys.update(_resolve(fn, arg) or {})
                for kw in node.keywords:
                    if kw.arg:
                        keys[kw.arg] = kw.value
                seen = True
        return keys if seen else None
    return None


def _enclosing_functions(tree):
    out = {}
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for node in ast.walk(fn):
            out.setdefault(id(node), fn)
    return out


def gate_raise_sites():
    """Every raise of a GateFailure subclass in the owned files, with its evidence keys.

    The exception-class population is derived from the class hierarchy
    (`conftest.gate_failure_subclasses`), never from a name substring — the wave-6
    census's `"Gate" in name` filter is exactly what let five andons out.
    """
    known = {c.__name__: c for c in gate_failure_subclasses()}
    sites = []
    for name in OWNED:
        path = os.path.join(CORE, name)
        tree = ast.parse(open(path, encoding="utf-8").read())
        owner = _enclosing_functions(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            cls_name = getattr(node.exc.func, "id",
                               getattr(node.exc.func, "attr", ""))
            cls = known.get(cls_name)
            if cls is None:
                continue
            fn = owner.get(id(node))
            evidence = node.exc.args[1] if len(node.exc.args) > 1 else None
            keys = _resolve(fn, evidence) if (fn and evidence is not None) else None
            sites.append({
                "file": name, "line": node.lineno, "class": cls_name, "cls": cls,
                "function": fn.name if fn else "<module>",
                "has_evidence": evidence is not None,
                "keys": keys,
            })
    return sites


def test_the_derived_population_is_the_one_this_file_records():
    """SIZE and MEMBERSHIP first: a census that does not pin its population can report
    green over a smaller one than it claims."""
    sites = gate_raise_sites()
    counted = {}
    for s in sites:
        counted[(s["file"], s["class"])] = counted.get((s["file"], s["class"]), 0) + 1
    assert counted == RECORDED_GATE_RAISES, (
        "the gate-raise population moved. Add the new site to RECORDED_GATE_RAISES in "
        f"the same commit that adds the raise.\nderived: {sorted(counted.items())}")
    # WAVE 14 (core-gates): 84 -> 86. `gates.GateSSeedRegistration` +1 (a declared but
    # empty registry, F-b4706738) and `route_gates.RouteGate` +1 (`orphan_attribution`,
    # F-74787978). MEASURED on this branch, itemised on the two rows above.
    # WAVE 16: 86 → 88, both from `route_gates.RouteGate` (see the row's own note).
    # core-solvers' +4 `GateFailure` raises this wave are in `assembly.py` and
    # `turnaround.py`, which this census does not walk, and their fifth is
    # `aapose.ConventionError`, a plain refusal. instruments, instruments-measure and
    # builders add none in `armature_core` at all. RED on the tests branch (88 vs 86);
    # composed from branch measurements, so re-measure at merge.
    # WAVE 18 (core-gates): 88 → 98. +5 route_gates.RouteGate, +4 donor_gate.DonorGate,
    # +1 gates.GateSSeedRegistration — itemised at each entry above. Measured in the
    # core-gates worktree; core-solvers also edits `armature_core`, so the coordinator
    # re-measures at merge rather than summing the branches (SEAM 8 §1's worked example).
    # WAVE 20 (core-gates, 2026-09-05): +3 in `route_gates.RouteGate`, RE-DERIVED with
    # `==` in this worktree against the merged base `475f4eb`, which every census here read
    # GREEN first. BRANCH-LOCAL — the coordinator re-measures at the merge.
    #   `_iter_definitions`' `duplicate_subgraph_label` — the LABEL the walk EMITS, which
    #   the id clause did not bound, so two blueprints under one `name` (or two under
    #   neither field, or one named `top`) collapsed the `(where, id)` pair Gate S keys on
    #   (F-400c1df4).
    #   `_readable_containers`' `unreadable_node` — the node's OWN `widgets_values` /
    #   `inputs` container, where a BANNED weight spelled inside a mapping or a bare string
    #   was read as empty and `verify` returned GREEN (F-f9ab0645).
    #   `_converted_widget_shift_andon`'s `converted_widget_shifts_recorded_indices` — the
    #   converted-widget shift clause over `LATENT_NODES`, `CAMERA_NODES` and `SEED_NODES`,
    #   which wave 18 gave `HOSTED_ENUM_WIDGETS` alone (F-29e1cbb7).
    # WAVE 22 (core-gates, 2026-09-05): 101 → 102. +1 `canon_census.GateCanon` — itemised
    # at its entry above. RE-DERIVED with `==` in this worktree against `e8263a3`, which
    # every census here read GREEN first. BRANCH-LOCAL — five domains move pins this wave
    # and the coordinator re-measures on the merged tree rather than summing.
    assert sum(counted.values()) == sum(RECORDED_GATE_RAISES.values()) == 102


def test_every_gate_raise_carries_evidence_naming_its_own_andon():
    """The property. `gate` and `andon` on every evidence dict that reaches a report."""
    offenders = []
    for s in gate_raise_sites():
        if not s["has_evidence"]:
            offenders.append(f"{s['file']}:{s['line']} {s['function']} — NO EVIDENCE")
            continue
        if s["keys"] is None:
            offenders.append(
                f"{s['file']}:{s['line']} {s['function']} — evidence expression could "
                f"not be resolved to a key set")
            continue
        missing = [k for k in ("gate", "andon") if k not in s["keys"]]
        if missing:
            offenders.append(f"{s['file']}:{s['line']} {s['function']} — missing "
                             f"{missing} (has {sorted(s['keys'])})")
    assert not offenders, "\n".join(offenders)


def test_the_evidences_gate_id_agrees_with_the_andon_that_raises():
    """F-1844be26. `gate_s_registration` built `ev = {"gate": "S", ...}` and every
    failure path raised `RouteGate`, whose class attribute is `gate = "ROUTE"` — so a
    receipt said ROUTE on the prose line and S on the JSON line, and "S" is already
    `errors.GateSSeedRegistration`'s id, a different andon with different evidence keys.
    Checked wherever the value is a literal; a computed one is reported, not waved."""
    disagreements = []
    for s in gate_raise_sites():
        node = (s["keys"] or {}).get("gate")
        value = getattr(node, "value", None) if isinstance(node, ast.Constant) else None
        if value is None:
            continue
        if value != s["cls"].gate:
            disagreements.append(
                f"{s['file']}:{s['line']} {s['function']} raises {s['class']} "
                f"(gate {s['cls'].gate!r}) with evidence gate {value!r}")
    assert not disagreements, "\n".join(disagreements)


def test_the_evidences_andon_names_a_real_andon_class():
    """An `andon` value that names no class is a receipt pointing nowhere."""
    known = {c.__name__ for c in gate_failure_subclasses()}
    wrong = []
    for s in gate_raise_sites():
        node = (s["keys"] or {}).get("andon")
        value = getattr(node, "value", None) if isinstance(node, ast.Constant) else None
        if value is None:
            continue
        if value not in known:
            wrong.append(f"{s['file']}:{s['line']} names andon {value!r}")
    assert not wrong, "\n".join(wrong)


def test_the_census_goes_red_on_a_raise_that_forgot_its_id(tmp_path, monkeypatch):
    """The mutation. A census that cannot fail is the thing this file exists to replace,
    so a module carrying a bad raise is written into a temp tree and the walk pointed at
    it — all four assertions above must then have something to say."""
    import test_amend_w8_core_gates as mod

    bad = tmp_path / "fake_module.py"
    bad.write_text(
        "from .errors import GateCanon\n"
        "def gate_x(a):\n"
        "    ev = {'n': len(a)}\n"
        "    raise GateCanon('bad', ev)\n"
        "def gate_y(a):\n"
        "    raise GateCanon('worse', {'gate': 'NOPE', 'andon': 'NoSuchAndon'})\n"
        "def gate_z(a):\n"
        "    raise GateCanon('silent')\n",
        encoding="utf-8")
    monkeypatch.setattr(mod, "CORE", str(tmp_path))
    monkeypatch.setattr(mod, "OWNED", ("fake_module.py",))

    sites = mod.gate_raise_sites()
    assert len(sites) == 3

    with pytest.raises(AssertionError, match="population moved"):
        mod.test_the_derived_population_is_the_one_this_file_records()
    with pytest.raises(AssertionError) as exc:
        mod.test_every_gate_raise_carries_evidence_naming_its_own_andon()
    assert "NO EVIDENCE" in str(exc.value) and "missing" in str(exc.value)
    with pytest.raises(AssertionError, match="evidence gate 'NOPE'"):
        mod.test_the_evidences_gate_id_agrees_with_the_andon_that_raises()
    with pytest.raises(AssertionError, match="NoSuchAndon"):
        mod.test_the_evidences_andon_names_a_real_andon_class()


def test_the_resolver_sees_the_three_shapes_the_wave_six_census_was_blind_to():
    """The wave-6 census inspected `ev = {...}` literals only. These are the shapes this
    tree actually raises with, and each one must resolve to its keys or the census above
    is green over an unread population."""
    src = (
        "def gate_a():\n"
        "    raise GateCanon('m', {'gate': 'CANON', 'andon': 'GateCanon'})\n"
        "def gate_b():\n"
        "    ev = {'gate': 'CANON'}\n"
        "    ev['andon'] = 'GateCanon'\n"
        "    raise GateCanon('m', ev)\n"
        "def gate_c():\n"
        "    ev = dict(base or {})\n"
        "    ev.update({'gate': 'CANON', 'andon': 'GateCanon'})\n"
        "    raise GateCanon('m', ev)\n"
        "def gate_d():\n"
        "    ev = {'gate': 'CANON'}\n"
        "    raise GateCanon('m', dict(ev, andon='GateCanon'))\n"
    )
    tree = ast.parse(src)
    owner = _enclosing_functions(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            fn = owner[id(node)]
            keys = _resolve(fn, node.exc.args[1])
            assert keys is not None and {"gate", "andon"} <= set(keys), fn.name
