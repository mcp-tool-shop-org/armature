"""Every `pytest.raises` on a class that carries more than one refusal names its clause.

Wave 6, F-0d6fa12a. 34 sites in this suite wrapped a refusal in a bare
`pytest.raises(ArmatureError)` / `GateFailure` / `PayloadError` with no `match=`, no
`str(exc.value)` assertion and no evidence check, so ANY refusal raised anywhere inside the
call satisfied them. `tests/test_make_plate.py` was the representative case: three inputs
(no `--why`, `--why=`, `--why=   `) each under a bare raise, where a size gate, an anchor
gate or a source gate firing first would have passed all three under the name "no reason".

The class was measured decisively on the compensator pair (F-c0f49504): replacing the whole
`.armature_run` ownership clause in `stage_render.delete_output_dir` with an unrelated
`ArmatureError` left both of its tests green. Measured again there, on two more members of
the family: substituting `make_plate`'s `--why` refusal and `aapose.hand_stickwidth`'s
unknown-profile refusal with unrelated `ArmatureError`s turns
`test_a_plate_with_no_reason_never_gets_written` and
`test_unknown_stickwidth_type_raises_rather_than_falling_through` red, where the bare form
accepted both substitutions.

Wave 8, F-6e1c1dd6 — why the population is now DERIVED. Until this wave the census policed
three TYPED names (`ArmatureError`, `GateFailure`, `PayloadError`) and its premise test
asked the wrong question: whether a name is a BASE class in `errors.py`. Being a base is not
the property that makes a bare `pytest.raises` weak. The property is how many DISTINCT
refusals one class carries: if a class is raised from exactly one site, its name IS its
clause; from 45 sites it names nothing. Measured on the tree: `RouteGate` is raised from 45
distinct sites across `route_gates.py`, `gate_saved_graph.py`, `build_t2v_payload.py` and
`build_r2v_payload.py`, and this suite carried 21 clauseless `pytest.raises(RouteGate)`
sites that the typed census could not see. Measured decisively: with a plugin leaving
`route_gates.is_api_format` and `route_gates.gate_s_registration` raising `RouteGate` but
substituting an unrelated CLAUSE, `test_route_gates.py::test_is_api_format_refuses_an_...`
and `::test_a_graph_with_no_seed_at_all_is_indeterminate_...` both passed.

THE DERIVATION (wave 8's rule — a census may not type its own population):

  population = every class DEFINED by a `class` statement anywhere under `tools/`
               (`tools/superseded/` excluded — it is the failure museum, not the pipeline)
               that is RAISED from MORE THAN ONE distinct `(file, line)` under `tools/`.

Both halves come from one `ast.walk` of every module in the tree: `ClassDef` names for the
first, `Raise` nodes for the second. Nothing is typed but the recorded answer the derivation
is asserted against, which is what makes a new member fail loudly here on the day it lands.
`FramingError` and `WalkError` are the proof that the old premise was the wrong one: both
derive from `ValueError`, not `ArmatureError`, so a class-hierarchy walk rooted at the repo
root class would still have missed 11 clauseless sites.

The bar is deliberately zero: a leaf class exists for most of these refusals, and where it
does not, the message is what the refusal is named for.
"""

import ast
import os

import pytest  # noqa: F401  (imported so the fixture source below reads as this suite's)

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
CORE = os.path.join(REPO, "tools", "armature_core")
TOOLS = os.path.join(REPO, "tools")


def _tool_modules(tools_root):
    """Every `.py` under `tools/` except the superseded museum."""
    out = []
    for dirpath, dirnames, filenames in os.walk(tools_root):
        dirnames[:] = [d for d in dirnames if d != "superseded" and d != "__pycache__"]
        for name in sorted(filenames):
            if name.endswith(".py"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def _raised_name(node):
    """The name in `raise X(...)` / `raise X` / `raise mod.X(...)`; '' for a bare re-raise."""
    exc = node.exc
    if exc is None:
        return ""
    func = exc.func if isinstance(exc, ast.Call) else exc
    if isinstance(func, ast.Attribute):
        return func.attr
    return getattr(func, "id", "")


def derive_population(tools_root):
    """`(policed, raise_sites)` — see THE DERIVATION in this module's docstring."""
    defined = set()
    sites = {}
    for path in _tool_modules(tools_root):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        rel = os.path.relpath(path, tools_root).replace(os.sep, "/")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Raise):
                name = _raised_name(node)
                if name:
                    sites.setdefault(name, set()).add((rel, node.lineno))
    policed = {n for n in defined if len(sites.get(n, ())) > 1}
    return policed, sites


POLICED, RAISE_SITES = derive_population(TOOLS)

#: The population as it stood on 2026-09-04, derived by the walk above and recorded here so
#: that a class which grows a second raise site fails HERE, on the day it lands, instead of
#: quietly joining a set nobody re-derives. A new member is not a defect: add it to this set
#: in the same commit, and give its bare `pytest.raises` sites a clause.
#:
#: Six names are recorded here BEFORE they exist in this branch's tree, so this census
#: is red on this branch alone and green on the merged one. `PreviewGlbGate` (2 sites),
#: `PreviewWalkGate` (3), `GateMode` (3) and `GateSubject` (2) arrive with the instruments
#: wave-8 amend, counted by AST at its tip on 2026-09-04; its `GateObjects` (1 site),
#: `BindingSheetGate` (1) and `PartsSheetGate` (1) are deliberately absent, and join the
#: day a second raise site does;
#: `MalformedGLB` arrives with core-solvers' (6 sites in `glb.py`, `read_chunks` and
#: `_image_blob`). `MalformedGLB` subclasses `ValueError`, which is why the predicate is
#: "defined under tools/ and raised from more than one site" and not "an `ArmatureError`
#: subclass": the hierarchy rule would not see it, exactly as it does not see
#: `FramingError` and `WalkError`. Core-solvers' `NonReiterableFrames` is deliberately
#: absent — one raise site, so the class IS its clause. `CropStripError` arrives with
#: instruments-measure's (7 sites in `make_crop_strip.py`, whose refusals were `SystemExit`
#: on this branch). `RenderTurnaroundGate` is unaffected by being
#: re-based on `GateFailure` in the same amend: the derivation keys on the class NAME and
#: its raise count, never on its bases, which is the whole reason `FramingError` and
#: `WalkError` are policed at all.
RECORDED_POPULATION = frozenset({
    "CropStripError", "GateMode", "GateSubject", "MalformedGLB", "PreviewGlbGate",
    "PreviewWalkGate",
    # JOINED 2026-09-04, exactly as this comment anticipated: the instruments wave-10
    # amend (F-51c5e0ef) gives `make_binding_sheet.shoot` and `make_parts_sheet.shoot`
    # the render-completeness refusal their siblings carry, so `BindingSheetGate` and
    # `PartsSheetGate` each reach a second raise site and stop being their own clause.
    "BindingSheetGate", "PartsSheetGate",
    "AlphaGate", "ArmatureError", "AssemblyGate", "BackdropGate", "BakeEmpty",
    "CascadeGate", "ClipReadError", "ClipShapeError", "CompareError",
    "ComparisonNotIsolated", "CompositorWiring", "DetectionGate", "DonorGate",
    "EncodeFailure", "FacingGate", "FetchHalt", "FitReferenceError", "FloorError",
    "FramingError", "G1GeneratorLegality", "G2Completeness", "G4BboxSanity",
    "G6SubjectMotion", "GateBBatching", "GateCanon", "GateDDeterminism", "GatePRestPose",
    "GatePartsAccounting", "GatePartsDeterminism", "GateRRoundTrip", "GateRigidArrival",
    "GateSSeedRegistration", "IdentitySheetError", "InvertError", "LandmarkError",
    "LedgerGate", "LiftGate", "MeasureError", "NoRetopoProduced", "PairGate",
    "PairingGate", "PayloadError", "ProjectGate", "ReferenceGate", "ReliftMismatch",
    "RenderGate", "RenderTurnaroundGate", "ResampleError", "ResampleGate", "RouteGate",
    "SkeletonSheetGate", "SmoothnessInputError", "SolveError", "SolveGate", "SpecError",
    "StartFrameGate", "SticksGate", "TierGate", "TrackingError", "TurnaroundAlphaGate",
    "TurnaroundCropGate", "TurnaroundGate", "TurnaroundPlanRefusal", "WalkError",
    "WalkGate",
})

#: Re-derived 2026-09-04 and EMPTY. There is no class this census excuses: a class raised
#: twice carries two refusals, and no reason to prefer one of them over the other has been
#: measured. The set is kept (rather than deleted) so that any future exemption must be
#: written down, dated, and checked against the population it claims to sit inside — the
#: `preview_glb` exemption in `test_instrument_exits.py` was a premise its own file
#: falsified, which is what an unchecked exemption comment is worth.
EXEMPT = frozenset()

#: The three names the wave-6 census typed. Kept only as a direction check: whatever else
#: the derivation returns, it may never return LESS than what the typed version policed.
WAVE_6_TYPED = frozenset({"ArmatureError", "GateFailure", "PayloadError"})


def test_the_policed_population_is_derived_from_the_tree_and_has_not_grown_silently():
    """Rule 2 of wave 8: SIZE, then MEMBERSHIP, then the property (the census below).

    `GateFailure` leaves the population here for a measured reason and not an editorial
    one: it is raised from zero sites in the tree (every gate raises a leaf subclass), so
    the derivation cannot see it. The typed set is therefore checked by direction — the
    two names that ARE raised must still be policed — rather than by containment.
    """
    assert len(POLICED) == 73, sorted(POLICED)
    assert POLICED == set(RECORDED_POPULATION), {
        "appeared": sorted(POLICED - RECORDED_POPULATION),
        "vanished": sorted(RECORDED_POPULATION - POLICED),
    }
    assert WAVE_6_TYPED - POLICED == {"GateFailure"}, sorted(WAVE_6_TYPED - POLICED)
    assert "GateFailure" not in RAISE_SITES, (
        "GateFailure is raised directly now; if it is raised from two sites it belongs in "
        "RECORDED_POPULATION, and its bare `pytest.raises` sites need a clause")


def test_route_gate_is_the_member_the_typed_census_could_not_see():
    """The finding's own subject, pinned as a number rather than as prose. `RouteGate` is
    the widest refusal in the repo and was invisible to a census that policed three base
    classes; if it ever stops being derived, this file has stopped doing its job."""
    assert "RouteGate" in POLICED
    # 45 on the tests branch; 51 on the merged wave-8 tree, where core-gates added the
    # class-level licence refusals, Gate P's truncation refusal and the save-format seed
    # clauses (all RouteGate). Recorded as measured at the merge.
    assert len(RAISE_SITES["RouteGate"]) == 51, sorted(RAISE_SITES["RouteGate"])
    files = {path for path, _ in RAISE_SITES["RouteGate"]}
    # `build_lora_arm_payload.py` joined at the wave-8 merge: its new `gate_base_licence`
    # raises RouteGate on a banned node class in the operator's baseline graph.
    assert files == {"armature_core/route_gates.py", "gate_saved_graph.py",
                     "build_t2v_payload.py", "build_r2v_payload.py",
                     "build_lora_arm_payload.py"}, sorted(files)


def test_the_exemption_set_is_empty_and_sits_inside_the_population():
    """Rule 4 of wave 8: an exemption is named, dated, and re-derived. Empty today; the
    subset assertion is what stops a name being excused that the census never policed."""
    assert EXEMPT <= POLICED
    assert EXEMPT == frozenset()


def test_a_class_raised_from_exactly_one_site_is_deliberately_not_policed():
    """The predicate's other half, stated so it cannot drift into "police everything".

    A class raised once IS its own clause — `pytest.raises(QuadriflowDeclined)` can only be
    satisfied by the single refusal that exists. Measured: 15 such classes today.
    """
    single = {n for n, s in RAISE_SITES.items() if len(s) == 1} & {
        n for n in RAISE_SITES if n not in POLICED}
    assert "QuadriflowDeclined" in single
    assert not (single & POLICED)


def _class_bases(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {node.name: [b.id for b in node.bases if isinstance(b, ast.Name)]
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def test_two_policed_classes_do_not_descend_from_the_repo_root_error():
    """Why the population is not a class-hierarchy walk rooted at `ArmatureError`.

    `FramingError` and `WalkError` subclass `ValueError`. A census deriving its population
    from the repo's own error tree would police neither, and 11 clauseless sites would stay
    invisible for the second wave running.
    """
    assert _class_bases(os.path.join(CORE, "framing.py"))["FramingError"] == ["ValueError"]
    assert _class_bases(os.path.join(CORE, "walk.py"))["WalkError"] == ["ValueError"]
    assert {"FramingError", "WalkError"} <= POLICED


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


def _suite_files(tests_dir):
    return [n for n in sorted(os.listdir(tests_dir))
            if n.startswith("test_") and n.endswith(".py")]


def clauseless_root_raises(tests_dir=TESTS, policed=None):
    """Every `with pytest.raises(<policed class>)` in a suite that pins no clause."""
    policed = POLICED if policed is None else policed
    out = []
    for name in _suite_files(tests_dir):
        with open(os.path.join(tests_dir, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        owner = _enclosing_functions(tree)
        for node, call, bound, cname in _raises_sites(tree):
            if cname not in policed or cname in EXEMPT:
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


#: Six shapes, written here so the detector is exercised against a tree whose answers are
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
    with pytest.raises(QuadriflowDeclined) as exc:
        boom()
    assert True
'''


def test_the_census_can_see_a_clauseless_site():
    """What this file looks like if it were wrong: a detector reading the wrong nodes
    reports a clean tree forever. `test_a` and `test_e` are the defect, `test_f` names a
    class with one raise site (so the class IS the clause), and the other three are the two
    accepted shapes."""
    tree = ast.parse(DETECTOR_FIXTURE)
    owner = _enclosing_functions(tree)
    verdict = {}
    for node, call, bound, cname in _raises_sites(tree):
        fn = owner[node]
        if cname not in POLICED:
            verdict[fn.name] = "not policed"
            continue
        pinned = (any(k.arg == "match" for k in call.keywords)
                  or _reads_the_exception(fn, bound))
        verdict[fn.name] = "pinned" if pinned else "clauseless"
    assert verdict == {"test_a": "clauseless", "test_b": "pinned", "test_c": "pinned",
                       "test_d": "pinned", "test_e": "clauseless",
                       "test_f": "not policed"}, verdict


MUTANT_TOOL = '''
class NewlyWideGate(Exception):
    pass

def one():
    raise NewlyWideGate("the first refusal")

def two():
    if False:
        raise NewlyWideGate("a second, entirely different refusal")
'''

MUTANT_TEST = '''
import pytest

def test_something():
    with pytest.raises(NewlyWideGate):
        one()
'''


def test_the_census_goes_red_when_a_member_arrives_without_the_property(tmp_path):
    """Rule 3 of wave 8, and the reason this file was rewritten: prove the census FAILS on
    a mutation that adds a member without the property.

    The mutation is the real one — a tool grows a second raise site for a class, and a test
    pins it by class alone. Both halves of this file are driven against the synthetic tree:
    the derivation must NAME the new class, and the census must NAME the bare site. A
    census that could not do this is the wave-6 defect verbatim.
    """
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "newly_wide.py").write_text(MUTANT_TOOL, encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_newly_wide.py").write_text(MUTANT_TEST, encoding="utf-8")

    policed, sites = derive_population(str(tools))
    assert policed == {"NewlyWideGate"}, sorted(policed)
    assert len(sites["NewlyWideGate"]) == 2

    named = clauseless_root_raises(str(tests), policed)
    assert named == ["test_newly_wide.py:5 (NewlyWideGate)"], named

    #: and the same tree with the clause present is clean — a census that reported the
    #: defect unconditionally would be no better than one that never reported it.
    (tests / "test_newly_wide.py").write_text(
        MUTANT_TEST.replace("raises(NewlyWideGate)",
                            'raises(NewlyWideGate, match=r"the first refusal")'),
        encoding="utf-8")
    assert clauseless_root_raises(str(tests), policed) == []


def test_a_single_raise_site_class_is_not_dragged_into_the_population(tmp_path):
    """The exemption-by-derivation, proven in the same direction: one raise site, one
    clause, no census entry. Without this the predicate could quietly become "every class",
    and 400 further sites would need a `match=` for no measured reason."""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "narrow.py").write_text(
        'class NarrowGate(Exception):\n    pass\n\n'
        'def one():\n    raise NarrowGate("the only refusal")\n', encoding="utf-8")
    policed, sites = derive_population(str(tools))
    assert policed == set()
    assert len(sites["NarrowGate"]) == 1


def test_the_policed_population_is_large_enough_for_the_census_to_mean_something():
    """A census over an empty population passes for the wrong reason, so what is counted is
    stated: the number of `pytest.raises` sites naming a policed class at all. 618 on
    2026-09-04, against 80-odd under the typed three-class version."""
    total = 0
    for name in _suite_files(TESTS):
        with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        total += sum(1 for _, _, _, cname in _raises_sites(tree) if cname in POLICED)
    assert total >= 600, (
        f"only {total} policed raises found; the walk is not reaching this suite, and "
        f"an empty population would make the census above vacuous")
