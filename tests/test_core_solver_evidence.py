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
BOTH `startframe.AlphaGate` and `turnaround.TurnaroundAlphaGate`. `stage_render.py:509-510`
prints `GATE_FAILURE <exc.gate>` beside `GATE_EVIDENCE <json>` and never the class name, so
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
        "assembly": 18, "blender_scene": 4, "canon": 1, "donor_gate": 6, "gates": 20,
        "glb": 4, "landmarks": 2, "lift_solve": 5, "parts": 7, "resample": 4,
        "rig_gates": 12, "route_gates": 34, "startframe": 19, "turnaround": 9,
    }, with_gates
    assert sum(with_gates.values()) == 145


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
    positives on the merged tree. `tests/test_gates.py::evidence_dicts_missing` resolves
    those shapes, so it is the walk this property is judged by; `_gate_raises` stays as the
    POPULATION pin above (per-module raise counts), which is a different question.
    """
    from test_gates import evidence_dicts_missing

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "armature_core")
    for key in ("gate", "andon"):
        offenders, examined = evidence_dicts_missing(key, root=root)
        assert examined > 0, "the walk examined no raise; a census over nothing is not a clean tree"
        offenders = [o for o in offenders
                     if not any(str(o[0]).replace("\\", "/").endswith(f"{x}.py") for x in EXEMPT)]
        assert offenders == [], f"gate raises whose evidence cannot name its {key!r}: {offenders}"


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

    for cls in (walk.WalkError, framing.FramingError, glb.MalformedGLB):
        assert issubclass(cls, ArmatureError)
        assert not issubclass(cls, GateFailure)
        assert cls("m", {"k": 1}).evidence == {"k": 1}
