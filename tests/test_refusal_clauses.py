"""Every `pytest.raises` on a root or base error class names the clause it is pinning.

Wave 6, F-0d6fa12a. 34 sites in this suite wrapped a refusal in a bare
`pytest.raises(ArmatureError)` / `GateFailure` / `PayloadError` with no `match=`, no
`str(exc.value)` assertion and no evidence check, so ANY refusal raised anywhere inside the
call satisfied them. `tests/test_make_plate.py` was the representative case: three inputs
(no `--why`, `--why=`, `--why=   `) each under a bare raise, where a size gate, an anchor
gate or a source gate firing first would have passed all three under the name "no reason".

The class was measured decisively on the compensator pair (F-c0f49504): replacing the whole
`.armature_run` ownership clause in `stage_render.delete_output_dir` with an unrelated
`ArmatureError` left both of its tests green. Measured again here, on two more members of
the family: substituting `make_plate`'s `--why` refusal and `aapose.hand_stickwidth`'s
unknown-profile refusal with unrelated `ArmatureError`s turns
`test_a_plate_with_no_reason_never_gets_written` and
`test_unknown_stickwidth_type_raises_rather_than_falling_through` red, where the bare form
accepted both substitutions.

This file is the census. Fixing 34 sites does not stop the 35th being written, and a
population that may not grow is the mechanical form this repo already uses for shared gate
ids. The bar is deliberately zero: a leaf class exists for most of these refusals, and
where it does not, the message is what the refusal is named for.
"""

import ast
import os

import pytest  # noqa: F401  (imported so the fixture source below reads as this suite's)

TESTS = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(os.path.dirname(TESTS), "tools", "armature_core")
TOOLS = os.path.join(os.path.dirname(TESTS), "tools")

#: The classes a bare `pytest.raises` says almost nothing about. `ArmatureError` is the
#: repo root; `GateFailure` is the base every typed gate inherits; `PayloadError` is the
#: per-tool base four builders raise for every refusal they make. Asserted against the
#: tree below rather than trusted as a list.
ROOT_CLASSES = {"ArmatureError", "GateFailure", "PayloadError"}


def _class_bases(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {node.name: [b.id for b in node.bases if isinstance(b, ast.Name)]
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def test_the_root_classes_are_the_ones_the_tree_actually_bases_things_on():
    """The census's own premise, measured. `ArmatureError` and `GateFailure` are bases in
    `armature_core.errors`; `PayloadError` is defined in four builders and each is an
    `ArmatureError` subclass that its module raises for every refusal, leaf or not."""
    bases = _class_bases(os.path.join(CORE, "errors.py"))
    inherited = {b for bs in bases.values() for b in bs}
    assert {"ArmatureError", "GateFailure"} <= inherited, (
        f"errors.py bases classes on {sorted(inherited)}; the census names "
        f"{sorted(ROOT_CLASSES)}")

    payload_modules = sorted(
        name for name in os.listdir(TOOLS)
        if name.endswith(".py")
        and _class_bases(os.path.join(TOOLS, name)).get("PayloadError") == ["ArmatureError"])
    assert payload_modules == ["build_animate_payload.py", "build_camera_i2v_payload.py",
                               "build_i2v_payload.py", "build_payload.py"], payload_modules


def _enclosing_functions(tree):
    """`{node: function}` for every node inside a function body."""
    owner = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            owner.setdefault(node, fn)
    return owner


def _reads_the_exception(fn, bound):
    """Does the enclosing function assert on the caught exception at all?

    `exc.value` — a message assertion or an evidence-dict assertion — is the only shape in
    this suite; `exc` bound and never read is the defect.
    """
    if bound is None or fn is None:
        return False
    for node in ast.walk(fn):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == bound and node.attr == "value"):
            return True
    return False


def _raises_sites(tree):
    """`(with-node, raises-call, bound-name, class-name)` for every `pytest.raises` here."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            call = item.context_expr
            if not (isinstance(call, ast.Call)
                    and getattr(call.func, "attr", "") == "raises" and call.args):
                continue
            cls = call.args[0]
            cname = cls.attr if isinstance(cls, ast.Attribute) else getattr(cls, "id", "")
            bound = (item.optional_vars.id
                     if isinstance(item.optional_vars, ast.Name) else None)
            yield node, call, bound, cname


def _suite_files():
    return [n for n in sorted(os.listdir(TESTS))
            if n.startswith("test_") and n.endswith(".py")]


def clauseless_root_raises():
    """Every `with pytest.raises(<root class>)` in this suite that pins no clause."""
    out = []
    for name in _suite_files():
        with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        owner = _enclosing_functions(tree)
        for node, call, bound, cname in _raises_sites(tree):
            if cname not in ROOT_CLASSES:
                continue
            if any(k.arg == "match" for k in call.keywords):
                continue
            if _reads_the_exception(owner.get(node), bound):
                continue
            out.append(f"{name}:{node.lineno} ({cname})")
    return out


def test_no_refusal_is_pinned_by_its_class_alone():
    """The census. Zero, because a refusal that cannot be told apart from its neighbours is
    a test that passes on the wrong reason — which is how a deleted ownership clause, a
    substituted anchor gate and a substituted stickwidth gate all read green."""
    clauseless = clauseless_root_raises()
    assert clauseless == [], (
        "these sites accept any refusal raised anywhere inside the call; give each a "
        "`match=` on the distinguishing phrase, or an `as exc:` and an assertion on "
        "`exc.value`:\n  " + "\n  ".join(clauseless))


#: Five shapes, written here so the detector is exercised against a tree whose answers are
#: known. Without this, a walk that silently reached nothing would report a clean suite.
DETECTOR_FIXTURE = '''
def test_a():
    with pytest.raises(ArmatureError):
        boom()

def test_b():
    with pytest.raises(ArmatureError, match=r"the clause"):
        boom()

def test_c():
    with pytest.raises(ArmatureError) as exc:
        boom()
    assert exc.value.evidence["clause"] == "x"

def test_d():
    with pytest.raises(ArmatureError) as exc:
        boom()
    assert "something" in str(exc.value)

def test_e():
    with pytest.raises(ArmatureError) as exc:
        boom()
    assert True

def test_f():
    with pytest.raises(GateCanon) as exc:
        boom()
    assert True
'''


def test_the_census_can_see_a_clauseless_site():
    """What this file looks like if it were wrong: a detector reading the wrong nodes
    reports a clean tree forever. `test_a` and `test_e` are the defect, `test_f` is a leaf
    class the census deliberately does not police, and the other three are the two
    accepted shapes."""
    tree = ast.parse(DETECTOR_FIXTURE)
    owner = _enclosing_functions(tree)
    verdict = {}
    for node, call, bound, cname in _raises_sites(tree):
        fn = owner[node]
        if cname not in ROOT_CLASSES:
            verdict[fn.name] = "not policed"
            continue
        pinned = (any(k.arg == "match" for k in call.keywords)
                  or _reads_the_exception(fn, bound))
        verdict[fn.name] = "pinned" if pinned else "clauseless"
    assert verdict == {"test_a": "clauseless", "test_b": "pinned", "test_c": "pinned",
                       "test_d": "pinned", "test_e": "clauseless",
                       "test_f": "not policed"}, verdict


def test_the_policed_population_is_large_enough_for_the_census_to_mean_something():
    """A census over an empty population passes for the wrong reason, so what is counted is
    stated: the number of `pytest.raises` sites naming a root class at all."""
    total = 0
    for name in _suite_files():
        with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        total += sum(1 for _, _, _, cname in _raises_sites(tree) if cname in ROOT_CLASSES)
    assert total >= 80, (
        f"only {total} root-class raises found; the walk is not reaching this suite, and "
        f"an empty population would make the census above vacuous")
