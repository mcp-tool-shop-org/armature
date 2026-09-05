"""Every gate raise in `armature_core` carries its own id AND the andon that pulled.

Wave 8, F-32565688. Wave 6's stated contract was "every evidence dict in every gate module
carries `gate` + `andon`". The census that enforced it, `tests/test_gates.py`'s
`test_every_gate_in_gates_and_rig_gates_carries_its_own_id_in_its_evidence`, walked a TYPED
population of exactly two modules — `for module in (gates, rig_gates)` — so the eight
gate-bearing modules in `core-solvers` sat outside it and reported green by not being asked.

Measured before the fix, by the walk below over the 21 `core-solvers` modules: 72 raises of
a `GateFailure` subclass, 53 of them carrying evidence with no `andon` and 20 of those with
no `gate` either. Runtime confirmation on the same tree:
`startframe.gate_alpha(0.0, (0.1,0.1,0.1), "why")` raised with `exc.gate == "ALPHA"`,
`ev["gate"] == "ALPHA"` and `ev["andon"] is None`, while `turnaround.gate_view_alpha(...)`
raised with `ev["andon"] == "TurnaroundAlphaGate"` — and the gate id `ALPHA` is carried by
BOTH `startframe.AlphaGate` and `turnaround.TurnaroundAlphaGate`. `stage_render.py` records
`gate` beside `evidence` in one `STAGE_RENDER_HALT <json>` line and never the class name
(CORRECTED wave 14: the `GATE_FAILURE` / `GATE_EVIDENCE` lines this named were deleted with
the old handler), so
an `ALPHA` receipt read off that handler could not be traced back to the andon that pulled.
Gate id `D` is shared the same way, by `errors.GateDDeterminism` and
`parts.GatePartsDeterminism`.

**The population is derived, never typed.** It is every `.py` under `tools/armature_core/`,
and within each, every `raise` whose class resolves at runtime to a `GateFailure` subclass —
so a new gate module, or a new raise in an old one, joins the census the moment it is
written rather than when someone remembers to add it to a tuple.
"""

import ast
import importlib
import os

import pytest

from conftest import TOOLS  # noqa: F401  (puts tools/ on sys.path)
from blender_stub import blender_stubbed
from armature_core.errors import GateFailure

CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "tools", "armature_core")

#: Modules whose raises are NOT core-solvers' to fix in this wave, with the reason and the
#: date. Each is asserted below to be a real member of the derived population and to be
#: outside this domain's owned globs — an exemption that stops being true fails loudly
#: rather than quietly widening. Routed to core-gates (`gates.py`, `rig_gates.py`,
#: `route_gates.py`, `canon.py`, `donor_gate.py`) in wave 8 of run
#: `swarm-1788481819-3690`, 2026-09-04.
#: EMPTIED at the wave-8 merge (coordinator): core-gates carried `gate` + `andon` across all five
#: of these modules on its own branch (commit da80e59), so an exemption that named them would
#: be the stale kind this file's own docstring warns about. The set stays as a mechanism so a
#: module that regresses can be named here with a date and a reason, never silently.
EXEMPT = set()

#: The 21 modules this domain owns, from the wave-8 frozen domain map. Used ONLY to check
#: the exemptions above are outside it — never as the census population.
OWNED = {
    "aapose", "assembly", "binding", "blender_scene", "channels", "clipcompare",
    "clipstats", "framing", "glb", "joints", "landmarks", "lift_solve", "openpose",
    "parts", "pngio", "posearc", "resample", "sitelist", "startframe", "turnaround",
    "walk",
}


def _module_names():
    """Every module under `tools/armature_core/`, walked from disk."""
    return sorted(f[:-3] for f in os.listdir(CORE)
                  if f.endswith(".py") and f != "__init__.py")


def _resolve_keys(node, fn, tree, depth=0):
    """The literal keys of the evidence expression, following names and one call hop.

    A dict literal answers directly; `dict(ev, ...)` merges; a bare name is looked up in
    its enclosing function; a call to a function in the same module is followed to that
    function's own returned dict (which is how `lift_solve.gate_round_trip` gets its
    evidence from `round_trip_report`). Bounded depth, so a cycle cannot hang the census.
    """
    if node is None or depth > 4:
        return None
    if isinstance(node, ast.Dict):
        keys = set()
        for k, v in zip(node.keys, node.values):
            if k is None:
                sub = _resolve_keys(v, fn, tree, depth + 1)
                if sub:
                    keys |= sub
            elif isinstance(k, ast.Constant):
                keys.add(k.value)
        return keys
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "dict":
        base = _resolve_keys(node.args[0], fn, tree, depth + 1) if node.args else set()
        return (base or set()) | {kw.arg for kw in node.keywords if kw.arg}
    if isinstance(node, ast.Name) and fn is not None:
        for a in ast.walk(fn):
            if isinstance(a, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == node.id for t in a.targets):
                return _resolve_keys(a.value, fn, tree, depth + 1)
        return None
    if isinstance(node, ast.Call):
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        for f in ast.walk(tree):
            if isinstance(f, ast.FunctionDef) and f.name == name:
                for r in ast.walk(f):
                    if isinstance(r, ast.Return) and r.value is not None:
                        got = _resolve_keys(r.value, f, tree, depth + 1)
                        if got:
                            return got
        return None
    return None


def _literal_value(node, key, fn, tree):
    """The constant value bound to `key` in the evidence expression, if it is a literal."""
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Constant):
                return v.value
        return None
    if isinstance(node, ast.Name) and fn is not None:
        for a in ast.walk(fn):
            if isinstance(a, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == node.id for t in a.targets):
                return _literal_value(a.value, key, fn, tree)
    return None


def _gate_raises(module_name, source=None):
    """Every `raise <GateFailure subclass>(...)` in one module, with what its evidence says.

    Yields `(lineno, class_name, gate_id, keys, gate_literal, andon_literal)`.
    """
    if source is None:
        with open(os.path.join(CORE, module_name + ".py"), encoding="utf-8") as fh:
            source = fh.read()
        # `blender_scene` is the one module here that imports bpy. The stub is CARRIED from
        # `tests/blender_stub.blender_stubbed` rather than installed inline: its teardown
        # pops every module first imported under the stub, from the registry AND from its
        # package attribute, which is what keeps `tests/test_cli.py`'s `needs-blender` rows
        # and `test_blender_scene_pure`'s no-stub guard reading about a real import failure.
        # An inline stub left in `sys.modules` turned both green for the wrong reason —
        # measured here, and twice before in this run's serial verify.
        with blender_stubbed():
            m = importlib.import_module("armature_core." + module_name)
            classes = {name: getattr(m, name) for name in dir(m)}
        resolve_class = classes.get
    else:
        # The real base class, so `issubclass(..., GateFailure)` reads the same way it
        # does for a module on disk; only the source under the walk is synthetic.
        ns = {"GateFailure": GateFailure}
        exec(compile(source, "<census-mutant>", "exec"), ns)          # noqa: S102
        resolve_class = ns.get

    tree = ast.parse(source)
    fn_of = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                fn_of.setdefault(n, fn)

    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Raise) or not isinstance(n.exc, ast.Call):
            continue
        cname = getattr(n.exc.func, "id", None) or getattr(n.exc.func, "attr", None)
        cls = resolve_class(cname) if cname else None
        if not (isinstance(cls, type) and issubclass(cls, GateFailure)):
            continue
        ev = n.exc.args[1] if len(n.exc.args) > 1 else None
        fn = fn_of.get(n)
        out.append((n.lineno, cname, cls.gate, _resolve_keys(ev, fn, tree),
                    _literal_value(ev, "gate", fn, tree),
                    _literal_value(ev, "andon", fn, tree)))
    return out


# ------------------------------------------------------------------ the census's premises


def test_the_population_is_derived_from_the_tree_and_is_what_it_was_measured_to_be():
    """Size AND membership, so a new gate module fails loudly rather than joining silently.

    Measured 2026-09-04 by walking `tools/armature_core/`.
    """
    mods = _module_names()
    with_gates = {m: len(_gate_raises(m)) for m in mods if _gate_raises(m)}
    assert with_gates == {
        # rig_gates 11 → 12 and route_gates 32 → 34 at the wave-8 merge: core-gates' branch
        # added Gate P's truncation refusal and the class-level licence refusals.
        #
        # WAVE 10, re-derived on this branch 2026-09-04 (never hand-edited from a merge):
        #   framing 0 → 6   `PinnedCameraGate`, the pinned-camera andon split off
        #                   `FramingError` when that class rejoined the ArmatureError family
        #   walk    0 → 3   `GaitGate` (1) + `CadenceGate` (2), the same split on `walk.py`
        #   parts   7 → 8   Gate D's zero-vertex refusal (F-03955683)
        # `glb` is unchanged at 4: `MalformedGLB` rejoined the family but is a REFUSAL, not
        # a `GateFailure`, and this walk counts `GateFailure` subclasses only.
        # core-gates' branch moves `rig_gates` 12 → 15 in the same wave; the merged total is
        # re-derived on the merged tree rather than added up from two branches.
        # WAVE 12, core-solvers (F-5a810b95): `assembly` 18 → 20. `gate_no_paid_nodes`
        # gains a vacuity guard (an empty graph was returning the full success verdict) and
        # a licence-ruling clause read through `route_gates.rulings_for_class`, replacing a
        # two-word substring match that no real partner class name triggers.
        # WAVE 12 (core-gates, 2026-09-04), +7 and itemised rather than replaced:
        #   gates       20 → 22  `gate_b_batching`'s expectation-of-zero refusal and
        #                        `g5_openpose_conformance`'s empty-reference refusal.
        #   rig_gates   15 → 17  `gate_n_names` on an empty registry, and Gate D's
        #                        degenerate-diagonal clause (the one its three Gate P
        #                        siblings already carried). The non-finite half of that
        #                        family raises from `parts.require_finite`, which is a
        #                        `parts` site and is already in this count.
        #   route_gates 35 → 38  `unreadable_node`, `uncredited_conditional_component`,
        #                        and `attribution_entry_for`'s refusal.
        # WAVE 14 (core-gates, 2026-09-04), +2 and itemised rather than replaced:
        #   gates       22 → 23  Gate S's declared-but-empty registry (F-b4706738).
        #   route_gates 38 → 39  `verify`'s `orphan_attribution` (F-74787978).
        #   rig_gates   17 → 17  unchanged: wave 14's four measurement guards and the
        #                        non-numeric-diagonal clause raise from
        #                        `parts.require_finite` and from `_require_numeric`, a
        #                        module helper rather than a `gate_*` body, so they are
        #                        `parts` sites or outside this walk's population — the
        #                        same accounting the w12 note makes for `require_finite`.
        # WAVE-14 MERGE (coordinator, 2026-09-04): core-solvers (F-594e1792, F-3bc3659d, F-c4cf355d) `assembly` 20 → 21,
        #   `startframe` 19 → 21, `turnaround` 9 → 10 on the same tree as core-gates' +2 above; the
        #   dict below is MEASURED on the merged tree, never composed.
        # WAVE 16 — three rows move, COMPOSED from branch measurements posted in the seams
        # inbox and NOT measured on a merged tree; the coordinator re-measures, as at waves
        # 10, 12 and 14. This dict is RED on the tests branch, which still reads
        # assembly 21 / route_gates 39 / turnaround 10.
        #   assembly    21 → 22  core-solvers (SEAM 11 §2): `gate_no_paid_nodes`'s
        #                        `class_with_an_unreadable_measurement_date`.
        #   route_gates 39 → 41  core-gates (SEAM 5 §4): `_unreadable_level` (one raise
        #                        shared by three container levels) and Gate S's
        #                        all-`add_noise=disable` andon.
        #   turnaround  10 → 13  core-solvers (SEAM 11 §2): `gate_set_distinct`'s
        #                        unreadable-plane refusal, `views_without_pixels` and
        #                        `adjacent_pair_shapes_differ`.
        # `aapose` does NOT join this dict: its new raise is `ConventionError`, a plain
        # refusal with `gate: None`, and this walk counts `GateFailure` subclasses only.
        # `rig_gates`, `donor_gate` and `parts` are unchanged — core-gates' two new donor
        # clauses raise from `parts.require_finite`, already a `parts` site.
        # WAVE 18 (core-solvers): three rows move, RE-DERIVED with `==` on this worktree.
        # The base was measured GREEN here first, so every one of the +9 is this branch's.
        # This walk counts `GateFailure`-subclass raises inside `gate_*`-shaped bodies, so
        # a plain refusal (`gate: None`) does not join it — which is why `channels` and
        # `framing` do NOT appear below even though both gained refusals this wave, and
        # why `turnaround`'s new `TurnaroundPlanRefusal` raise does not move row 13.
        #   assembly       22 -> 23  F-47db9eff, `gate_no_paid_nodes`'
        #                            `measurement_dated_in_the_future` clause.
        #   blender_scene   4 ->  8  F-25a5ecbf, Gate FRAME's four clauses in
        #                            `render_frame` (`operator_status`,
        #                            `channel_never_reached_disk`, `channel_is_zero_bytes`,
        #                            `stale_channel`). `CameraGeometry` is a plain refusal
        #                            and does not join.
        #   resample        4 ->  8  F-62774c72, `endpoints_match`' two vacuity clauses and
        #                            its two bone-population clauses.
        "assembly": 23, "blender_scene": 8, "canon": 1, "donor_gate": 6, "framing": 6,
        "gates": 23, "glb": 4, "landmarks": 2, "lift_solve": 5, "parts": 8, "resample": 8,
        "rig_gates": 17, "route_gates": 41, "startframe": 21, "turnaround": 13, "walk": 3,
    }, with_gates
    # WAVE-10 MERGE (coordinator, 2026-09-04): core-gates' branch moved rig_gates 12 -> 15 and
    # route_gates 34 -> 35 in the same wave; merged = 155 + 3 + 1 = 159, MEASURED on the merged tree.
    # WAVE-12 MERGE (coordinator, 2026-09-04): core-solvers assembly 18 -> 20 (+2) and core-gates
    # gates 20 -> 22, rig_gates 15 -> 17, route_gates 35 -> 38 (+7) on different modules; merged
    # 159 + 2 + 7 = 168, MEASURED on the merged tree.
    # WAVE 14 (core-gates, 2026-09-04): gates +1, route_gates +1 -> 170, MEASURED on this
    # branch. The coordinator re-measures at the merge, as at waves 10 and 12.
    # WAVE-14 MERGE (coordinator, 2026-09-04): 170 (core-gates alone) → 174, MEASURED on the merged tree.
    # WAVE 16: 174 → 180 (+2 core-gates in `route_gates`, +1 core-solvers in `assembly`,
    # +3 core-solvers in `turnaround`). COMPOSED, not measured on a merged tree.
    # WAVE 18: 180 -> 189 (+1 assembly, +4 blender_scene, +4 resample), all core-solvers
    # and all MEASURED on this branch against a base measured green at 180 in the same
    # worktree — never summed from prose.
    assert sum(with_gates.values()) == 189


def test_the_exemptions_are_real_members_and_outside_this_domain():
    """An exemption set is asserted to be a SUBSET of the derived population, and each
    member is checked against the reason it is exempt — here, that it is not one of the
    21 modules core-solvers owns in the wave-8 frozen domain map."""
    mods = set(_module_names())
    assert EXEMPT <= mods, sorted(EXEMPT - mods)
    assert OWNED <= mods, sorted(OWNED - mods)
    assert not (EXEMPT & OWNED), sorted(EXEMPT & OWNED)


# --------------------------------------------------------------------------- the property


def test_every_gate_raise_carries_both_its_id_and_its_andon():
    """The property, through the suite's ONE evidence walk.

    Coordinator consolidation at the wave-8 merge: this file's own `_gate_raises` walk reads
    the dict LITERAL at an evidence name's last assignment and cannot see a key added by
    subscript afterwards (`ev["andon"] = "GateCanon"` at canon.py:91) or a dict built and
    mutated earlier in the function (gates.py:668, route_gates.py:857) — six false
    positives on the merged tree. `tests/test_gates.py::evidence_dicts_missing` was named
    the walk this property is judged by; `_gate_raises` stays as the POPULATION pin above
    (per-module raise counts), which is a different question.

    WAVE 10, F-b01840fc — the consolidation's premise, CORRECTED IN PLACE with the
    measurement that overturned it. The walk did not resolve those shapes; it DROPPED
    them. Replicating its per-site classification on 2026-09-04 it examined 135 sites and
    returned `UNRESOLVED` — never an offender, never counted in `examined` — for
    canon.py:91, gates.py:668, gates.py:675, route_gates.py:857/867/875, route_gates.py:1634,
    donor_gate.py:213, lift_solve.py:693 and lift_solve.py:702. Intersected with
    `_gate_raises`'s derived 145, exactly 10 `GateFailure` raise sites were invisible to
    this property test, six of them the very six the consolidation was written for. All ten
    carried gate+andon at runtime, so it was a blind spot rather than a live defect — and
    it is precisely the spelling a new raise would take to be invisible.

    `evidence_dicts_missing` now reads those shapes (a parameter mutated by
    `ev["k"] = ...`, `dict(x or {})`, `ev.update({...})`, `dict(base, gate=…)`, and one hop
    into a module-local builder) and returns an `unreadable` list for anything it still
    cannot decide, so a raise it cannot read fails loudly instead of leaving the census.
    `examined` is 145 on this tree, which is the number the population pin above derives.
    """
    from test_gates import evidence_dicts_missing

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "armature_core")
    for key in ("gate", "andon"):
        offenders, examined, unreadable, _no_evidence = evidence_dicts_missing(
            key, root=root)
        assert examined > 0, "the walk examined no raise; a census over nothing is not a clean tree"
        assert unreadable == [], (
            f"the judge cannot decide these raises' {key!r} key, so they are policed by "
            f"nothing: {unreadable}")
        offenders = [o for o in offenders
                     if not any(str(o).replace("\\", "/").startswith(f"{x}.py:") for x in EXEMPT)]
        assert offenders == [], f"gate raises whose evidence cannot name its {key!r}: {offenders}"


def test_the_population_pin_and_the_one_evidence_judge_count_the_same_sites():
    """The two walks in this repo that enumerate gate raises must agree, or "the ONE judge"
    is a claim rather than a fact.

    `_gate_raises` (this file) derives per-module counts of `GateFailure` raises;
    `test_gates.evidence_dicts_missing` derives, over the whole `ArmatureError` family,
    every raise it can say anything about. They coincided at 145 on 2026-09-04 and the
    difference — if one appears — is the interesting number, so it is printed per module.
    """
    from test_gates import evidence_dicts_missing, package_andons

    # WAVE-10 MERGE (coordinator, 2026-09-04): the judge walks the whole `ArmatureError` family and, since wave 10,
    # plain refusals in walk/framing/glb carry evidence (`gate: None`, `andon`, `clause`) — nine of
    # them on the merged tree — while `_gate_raises` counts `GateFailure` raises only. The two
    # walks agree on the population they SHARE, so the judge is narrowed to the andon classes
    # here; the family-wide count stays the judge's own business.
    andons = {c.split(".", 1)[1] for c in package_andons()}
    _, examined, unreadable, _no_ev = evidence_dicts_missing(
        "gate", root=CORE, classes=andons)
    with_gates = {m: len(_gate_raises(m)) for m in _module_names() if _gate_raises(m)}
    assert unreadable == [], unreadable
    assert examined == sum(with_gates.values()), {
        "the judge examined": examined,
        "the population pin derives": sum(with_gates.values()),
        "per module": with_gates,
    }


def test_the_evidence_agrees_with_the_raising_class_wherever_both_are_literal():
    """`ev["gate"]` must be the class's own `.gate`, and `ev["andon"]` its class name.

    The shared-id ambiguity is the reason: `ALPHA` is carried by both `startframe.AlphaGate`
    and `turnaround.TurnaroundAlphaGate`, and `D` by both `errors.GateDDeterminism` and
    `parts.GatePartsDeterminism`, so the id alone cannot identify the andon.
    """
    wrong = []
    for mod in _module_names():
        if mod in EXEMPT:
            continue
        for lineno, cname, gate_id, _keys, gate_lit, andon_lit in _gate_raises(mod):
            if gate_lit is not None and gate_lit != gate_id:
                wrong.append((f"{mod}.py:{lineno}", "gate", gate_lit, gate_id))
            if andon_lit is not None and andon_lit != cname:
                wrong.append((f"{mod}.py:{lineno}", "andon", andon_lit, cname))
    assert wrong == [], repr(wrong)


def test_a_shared_gate_id_is_still_unambiguous_through_the_andon_key():
    """The runtime half, on the two andons that share `ALPHA`. `stage_render` prints the id
    and the evidence, never the class, so the evidence has to carry the class."""
    from armature_core import startframe, turnaround

    with pytest.raises(startframe.AlphaGate) as a:
        startframe.gate_alpha(0.0, (0.1, 0.1, 0.1), "why")
    with pytest.raises(turnaround.TurnaroundAlphaGate) as b:
        turnaround.gate_view_alpha(0, 255, 255, 0.0)
    assert a.value.evidence["gate"] == b.value.evidence["gate"] == "ALPHA"
    assert a.value.evidence["andon"] == "AlphaGate"
    assert b.value.evidence["andon"] == "TurnaroundAlphaGate"
    assert a.value.evidence["andon"] != b.value.evidence["andon"]


# ------------------------------------------------------------------------ the red direction


MUTANT = '''
class GoodGate(GateFailure):
    gate = "GOOD"

class SloppyGate(GateFailure):
    gate = "SLOPPY"

def good():
    raise GoodGate("named", {"gate": "GOOD", "andon": "GoodGate", "n": 1})

def sloppy():
    raise SloppyGate("unnamed", {"gate": "SLOPPY", "n": 1})

def lying():
    raise GoodGate("mislabelled", {"gate": "WRONG", "andon": "SloppyGate"})
'''


def test_the_census_goes_red_on_a_raise_that_cannot_name_its_andon():
    """A census that cannot fail is the defect class this wave exists to close. The
    mutation adds members WITHOUT the property to a synthetic module, so nothing in the
    tree is weakened to demonstrate it."""
    rows = _gate_raises("<mutant>", source=MUTANT)
    by_line = {cname: (keys, g, a) for _l, cname, _gid, keys, g, a in rows}
    assert len(rows) == 3
    missing = [cname for _l, cname, _gid, keys, _g, _a in rows
               if not ({"gate", "andon"} <= (keys or set()))]
    assert missing == ["SloppyGate"], missing
    # and the agreement clause catches the mislabelled one
    wrong = [(cname, g, a) for _l, cname, gid, _k, g, a in rows
             if (g is not None and g != gid) or (a is not None and a != cname)]
    assert wrong == [("GoodGate", "WRONG", "SloppyGate")], wrong
    assert by_line["GoodGate"][0] >= {"gate", "andon"}


# ------------------------------- wave 10: every refusal reaches the repo's own root error


TOOLS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "tools")


def _class_graph(tools_root):
    """`{class name: [base names]}` for every `class` statement under `tools/`.

    THE NODE THIS CENSUS KEYS ON is the **class hierarchy**, not a name pattern and not a
    file list: the property being asserted ("this refusal is one of ours") is a property of
    what a class DERIVES FROM, so the population is derived from `ClassDef.bases` and the
    edges are followed to their root. `tools/superseded/` is excluded — it is the failure
    museum, not the pipeline.
    """
    graph = {}
    for root, _dirs, files in os.walk(tools_root):
        if "superseded" in root.replace("\\", "/").split("/"):
            continue
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(root, fname), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    graph.setdefault(node.name, []).extend(
                        b.id if isinstance(b, ast.Name)
                        else getattr(b, "attr", "?") for b in node.bases)
    return graph


def _raised_names(tools_root):
    """Every class NAME raised from at least one site under `tools/`."""
    names = set()
    for root, _dirs, files in os.walk(tools_root):
        if "superseded" in root.replace("\\", "/").split("/"):
            continue
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(root, fname), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                    n = (getattr(node.exc.func, "id", None)
                         or getattr(node.exc.func, "attr", None))
                    if n:
                        names.add(n)
    return names


def _reaches(name, graph, root="ArmatureError", depth=0):
    """Does `name` reach `root` by following `class` bases inside the tree?"""
    if name == root:
        return True
    if depth > 12 or name not in graph:
        return False
    return any(_reaches(b, graph, root, depth + 1) for b in graph[name])


def outside_the_family(tools_root=None, graph=None):
    """Every class defined AND raised under `tools/` that does not reach `ArmatureError`."""
    tools_root = TOOLS_ROOT if tools_root is None else tools_root
    graph = _class_graph(tools_root) if graph is None else graph
    raised = _raised_names(tools_root)
    return sorted(n for n in raised if n in graph and not _reaches(n, graph))


def test_every_refusal_class_this_tree_raises_reaches_the_repo_s_own_root_error():
    """F-0d621185 and F-ba21426c. The ONE halt contract on every tool discriminates three
    outcomes by `isinstance`: `GateFailure` -> "HALTED — a gate fired", exit 2;
    `ArmatureError` -> "REFUSED", exit 2; anything else -> "FAILED — an unhandled error",
    exit 1. A refusal class defined outside that tree is therefore RECORDED AS A CRASH, and
    `evidence_dicts_missing` — the walk `test_every_gate_raise_carries_both_its_id_and_its
    _andon` is judged by — filters on family membership and never examines it.

    Measured on the wave-10 base (cd2d941) by the walk above: three classes were outside,
    with 30 raise sites between them —
    `walk.WalkError(ValueError)` (12), `framing.FramingError(ValueError)` (12) and
    `glb.MalformedGLB(ValueError)` (6). Replaying `author_walk.py:712-725`'s handler over
    `gate_stance_frac_is_modelled(0.4)` printed outcome "FAILED — an unhandled error",
    gate null, exit 1, while the evidence dict it carried said gate "GAIT".
    """
    assert outside_the_family() == []


def test_the_family_census_goes_red_on_a_refusal_raised_outside_the_tree(tmp_path):
    """Prove it can fail: a synthetic module adding a MEMBER WITHOUT the property.

    Nothing in the real tree is weakened to demonstrate it — the walk is pointed at a
    directory holding one file.
    """
    (tmp_path / "rogue.py").write_text(
        "class ArmatureError(RuntimeError):\n    pass\n\n"
        "class Ours(ArmatureError):\n    pass\n\n"
        "class Rogue(ValueError):\n    pass\n\n"
        "def a():\n    raise Ours('fine')\n\n"
        "def b():\n    raise Rogue('outside the family')\n",
        encoding="utf-8")
    assert outside_the_family(str(tmp_path)) == ["Rogue"]


def test_the_two_dual_based_andons_are_both_kinds_of_refusal_at_once():
    """The shape the rebase uses, asserted at runtime rather than read off the source.

    `walk.GaitGate` / `walk.CadenceGate` / `framing.PinnedCameraGate` derive from BOTH the
    module's own refusal class and `GateFailure`, so every existing `except WalkError` /
    `except FramingError` call site and every `pytest.raises(walk.WalkError)` in this suite
    keeps catching them, while the halt contract now reads them as gates rather than as
    crashes.
    """
    from armature_core import framing, glb, walk
    from armature_core.errors import ArmatureError

    for cls, own, gate in ((walk.GaitGate, walk.WalkError, "GAIT"),
                           (walk.CadenceGate, walk.WalkError, "CADENCE"),
                           (framing.PinnedCameraGate, framing.FramingError, "PIN")):
        assert issubclass(cls, own)
        assert issubclass(cls, GateFailure)
        assert cls.gate == gate
        assert str(cls("why", {"gate": gate})).startswith(f"[{gate}] ")

    receipt = {"k": 1}
    for cls in (walk.WalkError, framing.FramingError, glb.MalformedGLB):
        assert issubclass(cls, ArmatureError)
        assert not issubclass(cls, GateFailure)
        # WAVE 16, F-738053cc + rule 5. This loop established that all three are OUTSIDE the
        # `GateFailure` subtree and then checked only the PASSED path — two lines from where
        # it could have caught that all three normalised a bare message to `{}` anyway,
        # which is the one thing the exemption is supposed to distinguish. Both directions
        # now, and the passed one by IDENTITY: `dict(evidence)` satisfies `==` and publishes
        # a receipt the raising line never wrote. RED ON THIS BRANCH until core-solvers'
        # SEAM 4 deletion merges (their `-10` constructors include all three).
        assert cls("m", receipt).evidence is receipt
        assert cls("m").evidence is None, (
            f"{cls.__name__} is outside the `GateFailure` subtree and invents an empty "
            f"receipt for a bare message; the halt record then reads as a gate that "
            f"measured nothing instead of a refusal that carried nothing")
