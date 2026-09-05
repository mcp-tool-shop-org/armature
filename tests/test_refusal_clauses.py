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
`FramingError` and `WalkError` were the proof that the old premise was the wrong one: on
the wave-10 base both derived from `ValueError`, not `ArmatureError`, so a class-hierarchy
walk rooted at the repo root class would still have missed 11 clauseless sites. (Wave 10
rebased them, and `glb.MalformedGLB`, onto `ArmatureError` — see
`test_two_policed_classes_do_not_descend_from_the_repo_root_error`. The derivation did not
have to change, which is the point: it never depended on the hierarchy.)

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


def _raising_parameters(trees):
    """`{function name: {parameter name: positional index or None}}` — the `exc=` helpers.

    WAVE 16, F-d426d4bd. This census keyed `sites` on the identifier in a literal
    `raise X(...)`, and the repo routes three of its refusal classes through a helper
    instead: `make_sheet.parse_argv(..., exc=<class>)` raises whatever it was handed, and so
    does `sheet_compose.compose_over_named_plate` and `parse_plate`. Measured over `tools/`:
    `MakeSheetError`, `PosePackError` and `AnalyzeP3Error` appeared in NO `raise` at all, so
    each was recorded with zero raise sites, reached neither `POLICED` nor the
    deliberately-unpoliced single-site set, and was policed by nothing — while
    `pack_pose_pack` is what conditions a paid submission and `tests/test_alpha_law.py:101`
    already carries a bare `pytest.raises(PPP.PosePackError)` the census exempts by
    construction.

    A parameter that a function `raise`s IS a refusal class slot, so the call that fills it
    is a raise site. Derived from the tree, never listed: a second helper of this shape
    joins the day it lands.
    """
    out = {}
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = [a.arg for a in node.args.args + node.args.kwonlyargs]
            positional = {a.arg: i for i, a in enumerate(node.args.args)}
            raised = {_raised_name(n) for n in ast.walk(node) if isinstance(n, ast.Raise)}
            slots = {p: positional.get(p) for p in params if p in raised}
            if slots:
                out.setdefault(node.name, {}).update(slots)
    return out


def _delegated_raise_sites(tree, defined, raising):
    """`[(name, lineno)]` — a refusal class handed to a helper that raises its parameter.

    Three spellings, all live: the `exc=<Class>` keyword (`analyze_p3.py:173`,
    `pack_pose_pack.py:116`), the class as a bare POSITIONAL in the raised parameter's slot
    (`pack_pose_pack.py:164`, `parse_plate(a.alpha_over, PosePackError)`), and the
    module-level fallback `exc = exc or MakeSheetError` (`make_sheet.py:52`), which fills the
    slot for every caller that names none.
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            slots = raising.get(called_name_of(node))
            if slots:
                for kw in node.keywords:
                    if (kw.arg in slots and isinstance(kw.value, ast.Name)
                            and kw.value.id in defined):
                        out.append((kw.value.id, node.lineno))
                for index, arg in enumerate(node.args):
                    if (isinstance(arg, ast.Name) and arg.id in defined
                            and index in set(slots.values())):
                        out.append((arg.id, node.lineno))
        # `exc = exc or MakeSheetError` — the default that fills the slot for every caller
        # that names none. Keyed on the ASSIGNMENT to a name the enclosing function raises,
        # which is why `raising` is consulted rather than the spelling `exc`.
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.BoolOp)
                and isinstance(node.value.op, ast.Or)):
            targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if any(t in slot for slot in raising.values() for t in targets):
                for value in node.value.values:
                    if isinstance(value, ast.Name) and value.id in defined:
                        out.append((value.id, node.lineno))
    return out


def called_name_of(node):
    """The bare callee name of a `Call` — `f(...)` and `mod.f(...)` both give `f`."""
    func = node.func
    return (func.id if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute) else "")


def derive_population(tools_root):
    """`(policed, raise_sites)` — see THE DERIVATION in this module's docstring."""
    defined = set()
    sites = {}
    parsed = []
    for path in _tool_modules(tools_root):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        rel = os.path.relpath(path, tools_root).replace(os.sep, "/")
        parsed.append((rel, tree))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Raise):
                name = _raised_name(node)
                if name:
                    sites.setdefault(name, set()).add((rel, node.lineno))
    # THE SECOND EDGE (wave 16, F-d426d4bd): a class handed to a helper that raises it.
    raising = _raising_parameters([tree for _rel, tree in parsed])
    for rel, tree in parsed:
        for name, lineno in _delegated_raise_sites(tree, defined, raising):
            sites.setdefault(name, set()).add((rel, lineno))
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
#: `MalformedGLB` arrives with core-solvers' (13 sites in `glb.py` after wave 10 —
#: `read_chunks` and `_image_blob`). It subclassed `ValueError` on the wave-10 base, which
#: is why the predicate is "defined under tools/ and raised from more than one site" and
#: not "an `ArmatureError` subclass": the hierarchy rule would not have seen it, exactly as
#: it did not see `FramingError` and `WalkError`. Wave 10 rebased all three; the predicate
#: is unchanged, because it never keyed on the hierarchy.
#: Wave 10 also adds `CadenceGate` (2 sites in `walk.py`) and `PinnedCameraGate` (6 in
#: `framing.py`); `walk.GaitGate` has ONE raise site, so it is deliberately absent and
#: joins the day a second one is written. Core-solvers' `NonReiterableFrames` is deliberately
#: absent — one raise site, so the class IS its clause. `CropStripError` arrives with
#: instruments-measure's (7 sites in `make_crop_strip.py`, whose refusals were `SystemExit`
#: on this branch). `RenderTurnaroundGate` is unaffected by being
#: re-based on `GateFailure` in the same amend: the derivation keys on the class NAME and
#: its raise count, never on its bases, which is the whole reason `FramingError` and
#: `WalkError` are policed at all.
RECORDED_POPULATION = frozenset({
    # WAVE 18 (core-solvers) — MEASURED in this worktree, not carried. Three new family
    # classes, each with more than one raise site, so each crosses this predicate's
    # threshold: `blender_scene.RenderedFrame` (Gate FRAME, F-25a5ecbf, four sites),
    # `blender_scene.CameraGeometry` (F-329a9555, two sites) and `channels.DepthError`
    # (F-476a4ee8, three sites). The base was measured GREEN at 101 in this worktree
    # first, so 104 is a delta of exactly these three and nothing else.
    "CameraGeometry", "DepthError", "RenderedFrame",
    # WAVE 16 (tests, F-d426d4bd) — MEASURED in this worktree. The derivation gained a
    # second edge: a refusal class handed to a helper that raises its own parameter. Two
    # classes cross the two-site threshold on it. `PosePackError` was raised on every real
    # run through `compose_over_named_plate(..., exc=PosePackError)` (pack_pose_pack.py:115)
    # and `parse_plate(a.alpha_over, PosePackError)` (:164) and was recorded with ZERO raise
    # sites; `PlateError` had one literal raise (make_plate.py:204) and gains :207 and :210
    # the same way. `MakeSheetError` and `AnalyzeP3Error` reach exactly ONE site each
    # (`exc = exc or MakeSheetError` at make_sheet.py:52; `exc=AnalyzeP3Error` at
    # analyze_p3.py:172) and are therefore deliberately absent — a class raised once IS its
    # clause — and join the day a second site is written.
    "PlateError", "PosePackError",
    # WAVE 16 — CARRIED FROM THE SEAMS INBOX, not measured in this worktree, and therefore
    # RED HERE and expected green on the merged tree. Each is a class a sibling domain
    # posted as crossing the two-site threshold this wave:
    #   `ABClipError`, `ResampleArgError` — instruments-measure, SEAM 5 ("POLICED 94 -> 96":
    #     Gate TIMELINE gives `make_ab_clip.ABClipError` a second site, the `--fps-src`
    #     clause gives `resample_motion.ResampleArgError` one). Their two NEW classes
    #     (`PickSheetError`, `E13SheetError`) are deliberately single-site and absent.
    #   `SeedRegistrationError` — builders, SEAM 4 (`build_assembly_payload.py`, ONE seed
    #     registration reader with five clauses, "+6 raises" there and "+1 raise" in
    #     `build_t2v_payload.py`). Builders posted the raise deltas, not a POLICED delta;
    #     six sites is unambiguously more than one, so it is recorded here and the seam asks
    #     them to confirm. If it does not land, this assertion names it by name.
    "ABClipError", "ResampleArgError", "SeedRegistrationError", "SpendCeiling",
    "ArcDidNotSurvive",
    # WAVE-14 MERGE (coordinator, 2026-09-04): `aapose.ConventionError` (core-solvers, F-d0de0c2d) — the class landed, the
    # name did not; measured `POLICED - RECORDED_POPULATION == ["ConventionError"]` on the merged tree.
    "ConventionError",
    # WAVE 16 (builders): the two classes this wave adds with two or more raise sites.
    # `SeedRegistrationError` (F-0682bd00) is the ONE reader for a committed seed
    # registration - five clauses, replacing a bare `["seeds"]` index at seven sites.
    # `SpendCeiling` (F-f85c37f0) is Gate CEILING raised under its own id; its sibling half
    # raises `errors.GateSSeedRegistration`, the id `S`'s existing owner, so no second
    # andon takes an id another andon already uses.
    "SeedRegistrationError", "SpendCeiling",
    # WAVE-14 MERGE (coordinator, 2026-09-04, after #159/#160 and receipt #287): `make_rig_sheet.ReferenceFileError` — two raise sites, a plain refusal.
    "ReferenceFileError",
    # WAVE 18 (builders, F-c11410c5): `gate_saved_graph.SavedAdmission` — Gate
    # SAVED_ADMISSION raised under its own id, six raise sites. Declared with a PLAIN-NAME
    # base (`from armature_core.route_gates import RouteGate`) for F-d8593862's reason: the
    # one family class in the tree with a dotted base was invisible to every census that
    # walks `ast.Name` bases. MEASURED in the builders worktree, not carried.
    "SavedAdmission",
    "CadenceGate", "PinnedCameraGate",
    "CropStripError", "GateMode", "GateSubject", "MalformedGLB", "PreviewGlbGate",
    "PreviewWalkGate",
    # JOINED 2026-09-04 (wave 12, instruments F-940b0800): `rig_character.
    # GateSubjectDegenerate` refuses a subject whose coordinates are not numbers, from two
    # sites in `subject_scale` — the empty-population clause and the non-finite-coordinate
    # clause — so its NAME stops being its clause and its `pytest.raises` sites need one.
    "GateSubjectDegenerate",
    # JOINED 2026-09-04 (wave 12, instruments F-9b2d4106): `rig_character.gate_glb_written`
    # refuses a GLB export that never reached disk and one that is zero bytes - two sites,
    # so its NAME stops being its clause. It is the one implementation for all nine
    # `bpy.ops.export_scene.gltf` call sites in the tree.
    "GateGlbWritten",
    # JOINED 2026-09-04, exactly as this comment anticipated: the instruments wave-10
    # amend (F-51c5e0ef) gives `make_binding_sheet.shoot` and `make_parts_sheet.shoot`
    # the render-completeness refusal their siblings carry, so `BindingSheetGate` and
    # `PartsSheetGate` each reach a second raise site and stop being their own clause.
    "BindingSheetGate", "PartsSheetGate",
    # And `ReliftWindow` (3 sites in `check_relift.py`), the wave-10 andon that derives the
    # compared window from each GLB's own keyed action range instead of from `--frames`.
    "ReliftWindow",
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
    "StartFrameGate", "SticksGate",
    # WAVE 14 (core-gates, F-89eb81a9): `subject.extent_summary`'s three refusals were
    # bare `ValueError`s and are now this family class, so the discriminator this module
    # exists to BE reports a malformed subject as a refusal the halt contract can read.
    "SubjectExtentError",
    "TierGate", "TrackingError", "TurnaroundAlphaGate",
    "TurnaroundCropGate", "TurnaroundGate", "TurnaroundPlanRefusal", "WalkError",
    "WalkGate",
    # Joined 2026-09-04 (wave 10, instruments-measure). The census caught the growth
    # loudly, which is what it is for: `ReviewClipError`, `ShotsetSheetError` and
    # `ZoomSheetError` are new typed classes replacing thirteen bare
    # `raise SystemExit(<str>)` refusals, and `SheetPopulationError` crossed from one
    # raise site to two when `make_lift_sheet.subject_box` stopped raising a string.
    # (`ABClipError` is raised from exactly one site, so its name IS its clause and the
    # derivation deliberately leaves it out.)
    "ReviewClipError", "SheetPopulationError", "ShotsetSheetError", "ZoomSheetError",
    # Joined 2026-09-04 (wave 12, core-solvers, F-9fab7829). Thirteen bare `ValueError` /
    # `TypeError` refusals in six owned modules became typed members of the `ArmatureError`
    # family, because the 21-tool halt contract classifies on that family and recorded every
    # one of them as "FAILED - an unhandled error" at exit 1 where the honest record is
    # "REFUSED" at exit 2. Three of the new classes reach more than one raise site and
    # therefore enter the policed population: `PngWriteError` (6 sites in `pngio.py`),
    # `ClipCompareError` (3 in `clipcompare.py`), `ClipStatsError` (2 in `clipstats.py`).
    # `SiteListError` (1 site) and `MeasurementWithoutScene` (1) are deliberately absent —
    # one raise site means the class IS its clause — and join the day a second one is
    # written, exactly as `walk.GaitGate` and `ABClipError` do.
    "ClipCompareError", "ClipStatsError", "PngWriteError",
    # And `NonReiterableFrames` crosses from one raise site to two: `union_sphere`'s
    # non-callable guard was a bare `TypeError` and is now the same class as its
    # re-iterability clause. The comment above that recorded it as "deliberately absent —
    # one raise site, so the class IS its clause" is corrected here rather than deleted.
    "NonReiterableFrames",
    # Joined 2026-09-04 (wave 12, builders, F-4f72af05). `build_payload.PayloadOutHalt` is
    # the andon on the direction the sidecar-path derivation does not bound: the graph and
    # its record colliding on one path. Two raise sites in `gate_out_paths`, so its name is
    # not its clause and each site needs a distinguishing phrase.
    "PayloadOutHalt",
    # Joined 2026-09-04 (wave 12, core-gates), and both crossed the one-site line the same
    # way: each gained a SECOND refusal, so its class name stopped being its clause.
    # `G5ConventionConformance` now also refuses an empty reference convention (a
    # conformance verdict over zero keypoints and zero limb pairs is not a verdict), and
    # `GateNNames` now also refuses an empty registry (a "0 / 0 registered sites map to one
    # bone each" verdict is a coverage claim about an empty population). Every
    # `pytest.raises` on either class in this suite therefore has to name which refusal it
    # is pinning, and this census is what found them.
    "G5ConventionConformance", "GateNNames",
    "ReviewClipError", "SheetPopulationError", "ShotsetSheetError",
    "ZoomSheetError",
    # Joined 2026-09-04 (wave 12, instruments-measure). `SheetInputError`
    # (`make_e08_sheet`) crossed from one raise site to two when the sheet's
    # `cv2.imwrite` return was checked — `cv2.imwrite` returns a BOOL on failure and
    # raises nothing, so `E08_SHEET_OK` was printed over a write that had not landed
    # (F-e4fc9531). `ClipRateError` (`measure_cascade_clip`) is the new andon for
    # `--expect-fps`, which was parsed, recorded and printed beside the value read off the
    # stream with nothing comparing them; two raise sites — an fps ffprobe could not
    # parse, and one outside tolerance (F-c397574b).
    "ClipRateError", "SheetInputError",
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
    # 71 -> 73 in wave 10: `CadenceGate` (2 sites in `walk.py`) and `PinnedCameraGate`
    # (6 in `framing.py`) are the two andons split off `WalkError` / `FramingError` when
    # the family was rebased on `ArmatureError`. `walk.GaitGate` is raised ONCE and is
    # deliberately not here; both parents keep more than one raise site and stay policed.
    # WAVE-10 MERGE (coordinator, 2026-09-04): instruments' branch added `BindingSheetGate`,
    # `PartsSheetGate` (each reached a second raise site) and `ReliftWindow` (3 sites):
    # 71 + 2 + 3 = 76; instruments-measure's branch added `ReviewClipError`, `ShotsetSheetError`,
    # `ZoomSheetError` (new classes) and `SheetPopulationError` (crossed to two sites):
    # 76 + 4 = 80, MEASURED on the merged tree.
    # WAVE 12 (core-solvers, F-9fab7829): 80 + 3 new classes with two or more raise sites
    # (`PngWriteError`, `ClipCompareError`, `ClipStatsError`) + `NonReiterableFrames`
    # crossing from one site to two = 84, MEASURED on this branch. `SiteListError` and
    # `MeasurementWithoutScene` are new classes with ONE raise site each and are correctly
    # not derived.
    # WAVE 12 (builders, F-4f72af05): `build_payload.PayloadOutHalt` — the andon on the
    # direction the sidecar-path derivation does not bound, raised from 2 sites in
    # `gate_out_paths`. 80 + 1 = 81. ⚠ This number moves once per domain that adds a typed
    # refusal in a wave; the coordinator re-measures it at the merge, as it did at wave 10.
    # WAVE-12 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE-12 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE-12 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE 12 (instruments-measure, F-e4fc9531): 80 -> 81. `make_e08_sheet.SheetInputError`
    # crossed to a second raise site when the sheet's `cv2.imwrite` return was checked --
    # `cv2.imwrite` returns a BOOL on failure and raises nothing, so `E08_SHEET_OK` was
    # printed over a write that had not landed. Three sibling sites took the same refusal
    # (`make_overlay_sheet` gained `OverlaySheetError`, `make_zoom_sheet` reused
    # `ZoomSheetError`, `render_pose_sticks` reused `SticksGate`); only this one crossed
    # the two-site threshold the derivation uses.
    # ...and 81 -> 82 (F-c397574b): `measure_cascade_clip.ClipRateError` is the andon for
    # `--expect-fps`, which was parsed, recorded and printed beside the value read off the
    # stream with nothing comparing them. Two raise sites: an fps ffprobe could not parse,
    # and one outside tolerance.
    # WAVE-12 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE 14 (core-gates, F-89eb81a9): 91 -> 92. `subject.SubjectExtentError` is the new
    # member — `extent_summary`'s three refusals (None, wrong arity, a negative component)
    # were bare `ValueError`s, which are not `ArmatureError`s, so `probe_subject`'s halt
    # handler classified a deliberate refusal exit 1 (unhandled crash) instead of exit 2.
    # Three raise sites plus the non-finite clause, so it crosses the two-site threshold
    # the derivation uses. MEASURED on this branch; the coordinator re-measures at merge.
    # WAVE-14 MERGE (coordinator, 2026-09-04): 91 → 92 on core-gates (`SubjectExtentError`) AND 91 → 92 on core-solvers
    # (`ConventionError`) — two classes, one number twice; the merged tree measures 93 (SEAM 8 §2).
    # WAVE-14 MERGE (coordinator, 2026-09-04, after #159/#160 and receipt #287): 93 → 94 (`ReferenceFileError`), measured.
    # WAVE 16 (builders, F-0682bd00 + F-f85c37f0): 94 -> 96 on this branch, MEASURED.
    #   +1 `build_assembly_payload.SeedRegistrationError` — the ONE reader for a committed
    #      seed registration, five raise sites, replacing the bare `json.load(fh)["seeds"]`
    #      index at seven sites across five builders and `gate_saved_graph`.
    #   +1 `build_r2v_payload.SpendCeiling` — Gate CEILING raised under its own id, two
    #      raise sites. Its sibling half raises the id `S`'s EXISTING owner
    #      (`errors.GateSSeedRegistration`) rather than defining a second class on that id,
    #      so it adds nothing here. ⚠ Sibling branches move this too; the coordinator
    #      re-measures the merged number, as at waves 10, 12 and 14.
    # WAVE 16: 94 → 99. Composition, because this number cannot be measured on one branch:
    #   +2 MEASURED HERE (tests, F-d426d4bd): `PosePackError`, `PlateError` cross the
    #      threshold on the new `exc=` edge — derivation command:
    #      python -c "import sys;sys.path[:0]=['tests','tools'];import test_refusal_clauses as M;print(len(M.POLICED))"
    #      reads 96 in this worktree.
    #   +2 CARRIED from instruments-measure's SEAM 5 (`ABClipError`, `ResampleArgError`).
    #   +2 CARRIED from builders' SEAM 10 (`SeedRegistrationError`, 5 raise sites;
    #      `SpendCeiling`, 2 sites under its own gate id — builders measured POLICED 96 on
    #      their branch, i.e. base + these two).
    #   +1 CARRIED from instruments' SEAM 13 (`make_parts_sheet.ArcDidNotSurvive`, three
    #      literal raise sites across `make_parts_sheet:413`, `make_binding_sheet:241` and
    #      `make_rig_sheet:192`, each carrying `clause == "arc_did_not_survive"`).
    # So this assertion is RED on this branch (96) and expected green on the merged tree.
    # The coordinator re-measures at merge; the SET assertion beneath names any member that
    # did not arrive, which is why the pin is a set and not only a count.
    # WAVE-16 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE 18 (core-solvers): 101 -> 104, RE-DERIVED with `==` on this worktree (the base
    # was measured GREEN at 101 here first). The three newcomers each cross the
    # two-raise-site threshold this predicate uses, and all three are named in
    # RECORDED_POPULATION below so the SET assertion names any that did not arrive:
    #   `blender_scene.RenderedFrame` (F-25a5ecbf, Gate FRAME, four raise sites)
    #   `blender_scene.CameraGeometry` (F-329a9555, two raise sites)
    #   `channels.DepthError`          (F-476a4ee8, three raise sites)
    # WAVE 18 (builders, F-c11410c5): 101 → 102, MEASURED in the builders worktree with the
    # derivation command written out above —
    #   +1 `gate_saved_graph.SavedAdmission`, the owner the id `SAVED_ADMISSION` never had.
    #      Five refusals in the last gate before a paid submission raised the bare
    #      `RouteGate` (class attribute `gate = "ROUTE"`) while their evidence said
    #      `{"gate": "SAVED_ADMISSION"}`, so one halt line carried two gate ids for one
    #      event — the shape wave 16 fixed one file over with `SpendCeiling`. Six raise
    #      sites (the five, plus `graph_file_missing` on `--saved` / `--api`), so it crosses
    #      the two-site threshold. `POLICED - RECORDED_POPULATION == ['SavedAdmission']` and
    #      nothing vanished, both measured before this line was moved.
    #      ⚠ **BRANCH-LOCAL.** This is measured in `w18-builders` and is a COMPOSITION on the
    #      merged tree (core-solvers posts +3 and core-gates +5 on the sibling pins); it must be
    #      RE-DERIVED there by measurement, never summed. tests' SEAM 11 carries the
    #      derivation command; the base was measured green in this worktree first, so every
    #      delta here is demonstrably this domain's.
    #
    # WAVE-18 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    assert len(POLICED) == 105, sorted(POLICED)
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
    #
    # 53 on the wave-10 builders branch, and it moved in BOTH directions, which is why the
    # arithmetic is written out rather than the number replaced:
    #   +3  `build_assembly_payload.gate_create_video_fps` (F-29693a0e) — a non-numeric fps,
    #       a non-finite fps, and an fps outside `CreateVideo`'s measured 1-120 contract.
    #       One function with five importers (every builder that takes a `--fps` flag and
    #       writes it into a `CreateVideo` node), so +3 and not +15.
    #   -1  `build_t2v_payload`'s standalone Gate L raise (F-45bc4fbb) — DELETED because it
    #       could not fire: it re-read the three module constants that build the graph's
    #       only latent, two lines under a `verify(graph)` that already reads that latent
    #       and raises first. A refusal site disappearing is as much a finding as one
    #       appearing, and this census is where it shows.
    # 51 + 3 - 1 = 53. Re-pinned with the reason rather than relaxed (wave 3 section 0).
    # WAVE-10 MERGE (coordinator, 2026-09-04): core-gates' branch added one RouteGate raise site
    # (51 -> 52 on its own branch); merged = 53 + 1 = 54, MEASURED on the merged tree.
    # WAVE 12 (builders, F-4f72af05's sibling deliverable — the coordinator's CONDITIONAL
    # licence ruling): `build_lora_arm_payload.conditional_attribution` raises `RouteGate`
    # when the licence table rules a row CONDITIONAL and the readers that build its credit
    # entries are absent — an unknown attribution is not something a spend tool completes.
    # 54 + 1 = 55 on this branch. ⚠ core-gates' branch takes the same count to 57; the
    # merged number is 58 and the coordinator re-measures it, as at wave 10.
    # WAVE-12 MERGE (coordinator, 2026-09-04): builders +1 (`conditional_attribution`) and core-gates +3
    # (`unreadable_node`, `uncredited_conditional_component`, `attribution_entry_for`): 54 + 1 + 3 = 58,
    # MEASURED on the merged tree.
    # WAVE 14 (builders, F-2da88c51): `gate_saved_graph.route_facts` raises `RouteGate`
    # three times reading the payload record beside the graph — the source of the two facts
    # the LAST gate before a paid submission hands to `verify`:
    #   +1  `record_unreadable`: a record that will not parse supplies neither fact.
    #   +1  `record_carries_no_verify_receipt`: a record with no `verify` receipt in it —
    #       and `gate_base_licence`'s evidence carries the same gate/andon pair and neither
    #       fact, so the reader keys on content and refuses that shape by name.
    #   +1  `record_route_facts_disagree`: two receipts, two answers about the sampler.
    # WAVE 14 (builders, F-eec3f145): `build_r2v_payload.gate_one_paid_node` splits into
    # two clauses where it had one —
    #   +1  `hosted_population_is_not_the_expected_node`: the billable population counted by
    #       `route_gates.HOSTED_API_CLASS_SUFFIXES` (behaviour) must be the same set as the
    #       node this route expects to be charged for (identity). The old single clause
    #       counted one hard-coded class SPELLING and returned a green verdict over a graph
    #       carrying a second partner tier.
    #   (the count clause `not_exactly_one_billable_node` is the original raise, kept.)
    # 58 + 3 + 1 = 62 on this branch. Re-pinned with the arithmetic rather than replaced
    # (wave 3 section 0); ⚠ sibling branches move it too and the coordinator re-measures
    # the merged number, as at waves 10 and 12.
    # WAVE 14 (core-gates, F-74787978): 58 -> 59. `verify` gains `orphan_attribution` —
    # the CONVERSE of the conditional clause, which nothing checked: every credit the
    # record carries must name a component the graph actually loads, or the provenance
    # JSON and the public disclosure surface publish a credit to a creator whose weights
    # were never loaded. F-b44c880d MOVED `unreadable_node` out of the top-level loop and
    # into `_readable_node`, shared with `_iter_definitions`' recursion — one raise site
    # before, one after, so it moves this count by nothing.
    # WAVE-14 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE 16 (builders): 63 -> 62 on this branch, MEASURED — the first time this number
    # has gone DOWN. +2 in `gate_saved_graph`: `link_round_trip`'s `duplicate_socket_name`
    # (F-04fdd395) and `route_facts`' `verify_receipt_missing_its_facts`, the andon on the
    # shape core-gates' declared receipt kind opens (SEAM 5); -3 in `build_r2v_payload`,
    # where three raises moved off the bare `RouteGate` onto the classes whose own id the
    # evidence names (F-f85c37f0): one to `errors.GateSSeedRegistration` and two to the new
    # `SpendCeiling`. A raise that leaves this count because it became MORE specific is the
    # fix working, not the census shrinking.
    # WAVE 16: 63 → 63, and the zero hides three moves in both directions, so it is
    # itemised rather than left as "unchanged" (SEAM 5 §4 + SEAM 10 §2):
    #   +2 core-gates in `armature_core/route_gates.py` (`_unreadable_level`, Gate S's
    #      all-`add_noise=disable` andon);
    #   +1 builders in `gate_saved_graph.py` (`duplicate_socket_name`);
    #   −3 builders in `build_r2v_payload.py`, where three raises moved off the bare
    #      `RouteGate` onto `SpendCeiling`, the class whose own gate id the evidence names.
    # This is the first wave this count has gone DOWN. ⚠ The `files` assertion below still
    # names `build_r2v_payload.py`; builders' SEAM 10 does not say whether any `RouteGate`
    # raise remains there. If none does, that set loses a member at merge — flagged in the
    # inbox rather than guessed at here.
    # WAVE-16 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    # WAVE 18 (builders): 64 → 63, MEASURED, and the −1 hides moves in both directions, so
    # it is itemised rather than left as a number:
    #   −5 in `gate_saved_graph.py`, where the five raises whose evidence already said
    #      `{"gate": "SAVED_ADMISSION"}` moved off the bare `RouteGate` onto the class whose
    #      own gate id that is (`SavedAdmission`, F-c11410c5) — the same "a raise that
    #      leaves this count because it became MORE specific is the fix working" the wave-16
    #      note above records for `SpendCeiling`.
    #   +4 in `gate_saved_graph.route_facts`, which is Gate ROUTE's own id and so stays
    #      `RouteGate`: `record_carries_a_caught_refusal` (a caught `verify` refusal's
    #      evidence is shaped like a PASS receipt, because `verify` writes its declared kind
    #      and both fact keys before the first clause can raise — F-6d68f4c5),
    #      `record_route_facts_disagree` on `attribution` (the fact that was silently
    #      UNIONED across receipts while its sibling refused a disagreement — F-6d68f4c5),
    #      the same clause on `payload_sha256`, and `record_describes_a_different_graph`
    #      (the `--record` is TIED to the graph it vouches for — F-5c0f3858).
    # 64 − 5 + 4 = 63, measured with
    # `len(M.RAISE_SITES["RouteGate"])`, never summed.
    #      ⚠ **BRANCH-LOCAL.** This is measured in `w18-builders` and is a COMPOSITION on the
    #      merged tree (core-solvers posts +3 and core-gates +5 on the sibling pins); it must be
    #      RE-DERIVED there by measurement, never summed. tests' SEAM 11 carries the
    #      derivation command; the base was measured green in this worktree first, so every
    #      delta here is demonstrably this domain's.
    #
    # WAVE 18 (core-gates): 64 → 69, all five in `armature_core/route_gates.py` and all
    # five on the walk itself — `_api_entry_kind`'s `unreadable_node` (the API branch
    # answered a node-shaped mapping with no `class_type` by a silent `continue`),
    # `_iter_definitions`' `duplicate_subgraph_id` (the cycle guard keyed on the
    # blueprint's `id` VALUE and dropped the second of two blueprints declaring one
    # id), Gate S's `seed_node_unresolvable` (the seed-record lookup is keyed on the
    # pair `(where, id)` and is now TOTAL), and `_hosted_enum_shift_andon`'s two.
    # Measured in the core-gates worktree; builders and core-solvers may move this
    # count too, so the coordinator re-measures at merge rather than summing.
    # WAVE-18 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    assert len(RAISE_SITES["RouteGate"]) == 68, sorted(RAISE_SITES["RouteGate"])
    # WAVE 12 (core-gates, 2026-09-04): +3 = 57, itemised rather than replaced —
    #   +1  `_iter_nodes`' save-format branch: `unreadable_node`, the guard the API branch
    #       and `_iter_definitions` already carried and this one did not (a `None` inside
    #       `nodes` used to leave through `AttributeError`, bypassing the halt contract).
    #   +1  `verify`'s `uncredited_conditional_component`: a CONDITIONAL licence row is
    #       passed only when the submitting record credits it.
    #   +1  `attribution_entry_for`: a credit line asked for on a row that owes none.
    # (core-gates' 57 was its branch alone; the merged assertion above carries the measured 58.)
    files = {path for path, _ in RAISE_SITES["RouteGate"]}
    # `build_lora_arm_payload.py` joined at the wave-8 merge: its new `gate_base_licence`
    # raises RouteGate on a banned node class in the operator's baseline graph.
    # `build_assembly_payload.py` joined in wave 10: `gate_create_video_fps` lives there and
    # the other four `--fps` builders import it rather than carrying a copy.
    assert files == {"armature_core/route_gates.py", "gate_saved_graph.py",
                     "build_t2v_payload.py", "build_r2v_payload.py",
                     "build_lora_arm_payload.py", "build_assembly_payload.py"}, sorted(files)


def test_the_exemption_set_is_empty_and_sits_inside_the_population():
    """Rule 4 of wave 8: an exemption is named, dated, and re-derived. Empty today; the
    subset assertion is what stops a name being excused that the census never policed."""
    assert EXEMPT <= POLICED
    assert EXEMPT == frozenset()


def test_a_class_raised_from_exactly_one_site_is_deliberately_not_policed():
    """The predicate's other half, stated so it cannot drift into "police everything".

    A class raised once IS its own clause — `pytest.raises(QuadriflowDeclined)` can only be
    satisfied by the single refusal that exists. Measured 2026-09-04 (wave 16): 25 such
    classes, of which 22 are `ArmatureError`-family classes defined under `tools/**`.
    """
    single = {n for n, s in RAISE_SITES.items() if len(s) == 1} & {
        n for n in RAISE_SITES if n not in POLICED}
    assert "QuadriflowDeclined" in single
    assert not (single & POLICED)


def _family_classes_defined_under_tools():
    """Every `ArmatureError`-family class DEFINED under `tools/**` — the whole 120."""
    import _census_nodes as CN

    family = CN.armature_error_names()
    out = set()
    for path in _tool_modules(TOOLS):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in family:
                out.add(node.name)
    return out


#: The classes NOTHING raises — named and dated, because "zero raise sites" was the hole.
#: `POLICED` keeps a class only when `len(sites) > 1`, and
#: `test_a_class_raised_from_exactly_one_site_is_deliberately_not_policed` states the other
#: half for ONE-site classes; nothing stated anything about ZERO-site ones, so three classes
#: that fire on every real run through an `exc=` parameter sat outside both categories and
#: were policed by nothing (F-d426d4bd). With the second edge they are back in the
#: derivation and this set is what remains.
NOTHING_RAISES_THESE = {
    "GateFailure": "the family's gate BASE (armature_core/errors.py). A base is raised "
                   "through its subclasses; a literal `raise GateFailure(...)` would be the "
                   "defect `test_two_policed_classes_do_not_descend...` exists to name.",
    "_CarriesEvidence": "measure_tracking.py:91 — a mixin with no behaviour and no raise "
                        "site anywhere in the tree. instruments-measure DELETES it this "
                        "wave (SEAM 5, rule 5), so this entry is conditional on the class "
                        "still being defined: when it goes, it leaves both sets at once.",
}


def test_every_family_class_under_tools_is_policed_one_site_or_named_as_raised_by_nothing():
    """The three-way partition, so a class cannot fall out of the census in silence.

    F-d426d4bd. `derive_population` keyed `sites` on the identifier in a literal
    `raise X(...)`, and three refusal classes that fire on ordinary runs are handed to a
    helper instead — `MakeSheetError`, `PosePackError`, `AnalyzeP3Error`. Each was recorded
    with ZERO raise sites: not policed (the predicate needs two), not in the deliberately-
    unpoliced single-site set (the predicate needs one), and named by nothing. So
    `pack_pose_pack` — which is what conditions a paid submission — could grow a second
    refusal through the same helper with no test in the suite required to tell the two
    apart.

    Every member of the 120 now lands in exactly one of three named categories, and the
    third one is a table with a reason per entry rather than a silence.
    """
    defined = _family_classes_defined_under_tools()
    # WAVE-16 MERGE (coordinator, 2026-09-04): 120 (tests' branch) → 125 on the merged tree — builders +2 (`SeedRegistrationError`,
    # `SpendCeiling`), instruments +1 (`ArcDidNotSurvive`), instruments-measure +2 −1 (`PickSheetError`,
    # `E13SheetError`; `_CarriesEvidence` gone). Measured, never summed.
    # WAVE 18 (core-solvers): 125 -> 128, RE-DERIVED with `==` — the same three classes
    # the POLICED pin above names (`RenderedFrame`, `CameraGeometry`, `DepthError`). All
    # three are declared with a PLAIN-NAME base, so this walk and every other AST census
    # in the suite can see them; the dotted-base blind spot wave 17 found on
    # `SpendCeiling` is deliberately not reproduced here.
    # WAVE 18 (builders): 125 → 126 — +1 `gate_saved_graph.SavedAdmission` (F-c11410c5).
    # ⚠ `build_r2v_payload.SpendCeiling` does NOT move this number: it was already visible
    # here, because THIS file's `_family_classes_defined_under_tools` resolves a dotted base
    # while `tests/test_gates._armature_error_family` does not — which is precisely the
    # F-d8593862 defect (two censuses of one family disagreeing about its membership).
    # Widening the other walk is Stage B.
    #      ⚠ **BRANCH-LOCAL.** This is measured in `w18-builders` and is a COMPOSITION on the
    #      merged tree (core-solvers posts +3 and core-gates +5 on the sibling pins); it must be
    #      RE-DERIVED there by measurement, never summed. tests' SEAM 11 carries the
    #      derivation command; the base was measured green in this worktree first, so every
    #      delta here is demonstrably this domain's.
    #
    # WAVE-18 MERGE (coordinator, 2026-09-04): the number is MEASURED on the merged tree, never summed — see the merge log.
    assert len(defined) == 129, len(defined)

    zero = {n for n in defined if not RAISE_SITES.get(n)}
    one = {n for n in defined if len(RAISE_SITES.get(n, ())) == 1}
    policed = {n for n in defined if n in POLICED}

    assert zero | one | policed == defined, sorted(
        defined - (zero | one | policed))
    assert not (zero & one) and not (one & policed) and not (zero & policed)
    assert zero == {n for n in NOTHING_RAISES_THESE if n in defined}, {
        "raised by nothing and not named": sorted(
            zero - set(NOTHING_RAISES_THESE)),
        "named as raised by nothing and now raised": sorted(
            {n for n in NOTHING_RAISES_THESE if n in defined} - zero)}
    for name, why in NOTHING_RAISES_THESE.items():
        assert why and "REVIEW" not in why, (name, why)


def test_the_delegated_edge_sees_the_three_classes_the_literal_walk_could_not():
    """RED on members OUTSIDE the old walk (wave-16 rule 2), in both directions.

    The pre-wave-16 derivation is reconstructed here — literal `raise X(...)` only — and
    shown returning ZERO sites for all three, while the widened one returns the sites the
    tools actually reach. If the old walk could see them, this comparison would be with
    itself.
    """
    def literal_sites_only(tools_root):
        sites = {}
        for path in _tool_modules(tools_root):
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            rel = os.path.relpath(path, tools_root).replace(os.sep, "/")
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and _raised_name(node):
                    sites.setdefault(_raised_name(node), set()).add((rel, node.lineno))
        return sites

    # WAVE-16 MERGE (coordinator, 2026-09-04): the site LINES below are re-measured through `RAISE_SITES` itself —
    # instruments-measure deleted 27 four-line constructors and every line below each moved
    # (`pack_pose_pack.py` 115 → 111, 164 → 160).
    # WAVE-18 MERGE (coordinator, 2026-09-05): `PosePackError` gained a LITERAL raise site — the `--fps` andon
    # instruments-measure landed (F-6bb38028, `pack_pose_pack.py:231`) — so it leaves the zero-literal pair and
    # is stated as its own row: the literal walk sees ONE of its four sites, the delegated edge all four. Every
    # line below is re-measured on the merged tree through `RAISE_SITES` and the literal walk (SEAM 9's numbers
    # were one docstring re-wrap stale by SEAM 15 — a line pinned from a branch is stale by construction).
    old = literal_sites_only(TOOLS)
    for name in ("MakeSheetError", "AnalyzeP3Error"):
        assert old.get(name, set()) == set(), (name, sorted(old.get(name, ())))
        assert RAISE_SITES[name], name
    assert sorted(old.get("PosePackError", ())) == [("pack_pose_pack.py", 231)]   # literal-blind until wave 18

    assert sorted(RAISE_SITES["PosePackError"]) == [("pack_pose_pack.py", 163), ("pack_pose_pack.py", 231),
                                                    ("pack_pose_pack.py", 241), ("pack_pose_pack.py", 245)]
    assert sorted(RAISE_SITES["MakeSheetError"]) == [("make_sheet.py", 48)]
    assert sorted(RAISE_SITES["AnalyzeP3Error"]) == [("analyze_p3.py", 168)]
    # `PlateError` had ONE literal site and gains two delegated ones, so the edge moves a
    # class across the threshold as well as into the census.
    assert len(old.get("PlateError", ())) == 1 and len(RAISE_SITES["PlateError"]) == 3
    assert "PlateError" in POLICED and "PosePackError" in POLICED


def _class_bases(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {node.name: [b.id for b in node.bases if isinstance(b, ast.Name)]
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def test_two_policed_classes_do_not_descend_from_the_repo_root_error():
    """Why the population is not a class-hierarchy walk rooted at `ArmatureError`.

    **Corrected in place 2026-09-04, wave 10 (F-0d621185, F-ba21426c).** This test asserted
    `_class_bases(...)["FramingError"] == ["ValueError"]` and the same for `WalkError`. That
    was true and it was the defect, not the justification: a refusal class outside the
    `ArmatureError` tree is recorded by every tool's halt contract as an unhandled crash at
    exit 1, and `evidence_dicts_missing` — which filters on family membership — examined 0
    of their 24 raises. Core-solvers rebased all three members of that family
    (`walk.WalkError`, `framing.FramingError`, `glb.MalformedGLB`) onto `ArmatureError` in
    wave 10, so the old assertion now pins a defect rather than a premise.

    **The reason the population here is still NOT a hierarchy walk survives the fix, and it
    is now stated as the general claim rather than as three names.** A class-hierarchy
    census answers "is this one of our errors"; THIS census answers "can a
    `pytest.raises(X)` in the suite tell one refusal from another", and the second is a
    property of how often a class is raised, not of what it inherits from. The historical
    proof is kept below: on the wave-10 base those three classes really did sit outside the
    hierarchy and a rooted walk would have missed 24 sites — which is why the derivation
    was written this way, and why it did not have to change when they moved.
    """
    bases = dict(_class_bases(os.path.join(CORE, "framing.py")))
    bases.update(_class_bases(os.path.join(CORE, "walk.py")))
    bases.update(_class_bases(os.path.join(CORE, "glb.py")))
    assert bases["FramingError"] == ["ArmatureError"]
    assert bases["WalkError"] == ["ArmatureError"]
    assert bases["MalformedGLB"] == ["ArmatureError"]
    assert {"FramingError", "WalkError", "MalformedGLB"} <= POLICED

    # The derivation's independence from the hierarchy, proven on a source that HAS a class
    # outside it — the shape the tree carried until wave 10 — rather than on the tree.
    outside = _class_bases_from_source(
        "class Rogue(ValueError):\n    pass\n")
    assert outside["Rogue"] == ["ValueError"]


def _class_bases_from_source(source):
    tree = ast.parse(source)
    return {node.name: [b.id for b in node.bases if isinstance(b, ast.Name)]
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


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


# ------------------------------- a deliberate refusal is a typed error, not a `SystemExit`
#
# Wave 10, routed from builders. A `raise SystemExit(<str>)` carries no measurement, cannot
# be caught by class, and at the process boundary is indistinguishable from argparse's own
# usage exit — which is the whole reason this repo's refusals are typed and carry an
# evidence dict. Thirteen such sites sat in the instruments-measure domain
# (`encode_control`, `make_ab_clip`, `make_lift_sheet`, `make_shotset_sheet` x6,
# `make_zoom_sheet` x3, `measure_smoothness` x2), each one a deliberate refusal written as
# a string.
#
# THE NODE THIS CENSUS KEYS ON is the `raise` statement itself, walked by AST over every
# `tools/*.py` — not a name pattern, not a grep for "SystemExit", and not the module's
# import list. `raise SystemExit(main())` in a `__main__` block is a different object: its
# argument is a Call, it is the exit convention rather than a refusal, and it is excluded by
# looking at what is being raised rather than at the class name.

import ast as _ast  # noqa: E402
import glob as _glob  # noqa: E402

#: Named, dated, and re-derived below: `fetch_run.py` is the BUILDERS domain's file in the
#: wave-10 frozen map. Its four sites are that domain's to convert (its amend brief carries
#: them); this row is asserted to be a subset of the derived population so it cannot rot
#: into an exemption for a file that no longer has the defect.
# WAVE-10 MERGE (coordinator, 2026-09-04): builders typed `fetch_run.py`'s four bare `raise SystemExit(<str>)` sites in
# the same wave (F-af78df0f), so the exemption row EMPTIED at the merge — exactly the direction the
# subset assertion below exists for. A file that regresses joins `found` and fails there.
STRING_SYSTEMEXIT_EXEMPT = set()


def _string_systemexit_sites(path):
    """Every `raise SystemExit(<string-valued expression>)` in one file, by AST.

    A constant, an f-string, or a concatenation — the three spellings a message takes. An
    argument that is a Call (`SystemExit(main())`) is the exit convention, not a refusal.
    """
    with open(path, encoding="utf-8") as fh:
        tree = _ast.parse(fh.read())
    out = []
    for node in _ast.walk(tree):
        if not (isinstance(node, _ast.Raise) and isinstance(node.exc, _ast.Call)):
            continue
        func = node.exc.func
        if not (isinstance(func, _ast.Name) and func.id == "SystemExit"):
            continue
        if not node.exc.args:
            continue
        arg = node.exc.args[0]
        if isinstance(arg, (_ast.Constant, _ast.JoinedStr, _ast.BinOp)):
            out.append(node.lineno)
    return out


def _string_systemexit_census():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = {}
    for path in sorted(_glob.glob(os.path.join(root, "tools", "*.py"))):
        sites = _string_systemexit_sites(path)
        if sites:
            found[os.path.basename(path)] = sites
    return found


def test_no_tool_refuses_with_a_bare_string_system_exit():
    """The population is walked, so a fourteenth site added tomorrow fails here."""
    found = _string_systemexit_census()
    offenders = {k: v for k, v in found.items() if k not in STRING_SYSTEMEXIT_EXEMPT}
    assert offenders == {}, offenders


def test_the_exemption_is_a_subset_of_the_population_and_still_earns_it():
    """An exemption asserted to be a SUBSET of the derived population, and checked against
    the REASON it is exempt — the file belongs to another domain in this wave's frozen map
    — rather than against a proxy. When builders land their half, this set empties and the
    assertion below is what fails, loudly, rather than the row quietly outliving the defect.
    """
    found = _string_systemexit_census()
    assert STRING_SYSTEMEXIT_EXEMPT <= set(found), (sorted(STRING_SYSTEMEXIT_EXEMPT),
                                                    sorted(found))


def test_the_census_goes_red_on_a_module_that_refuses_with_a_string(tmp_path):
    """The falsifiability fixture: a temp module carrying each of the three spellings, and
    the `raise SystemExit(main())` exit convention, which must NOT be counted."""
    p = tmp_path / "make_fourteenth_thing.py"
    p.write_text(
        "def a():\n"
        "    raise SystemExit('plain')\n"
        "def b(x):\n"
        "    raise SystemExit(f'interpolated {x}')\n"
        "def c(x):\n"
        "    raise SystemExit('concatenated ' + str(x))\n"
        "def main():\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n", encoding="utf-8")
    assert _string_systemexit_sites(str(p)) == [2, 4, 6]


def test_every_converted_refusal_carries_an_evidence_dict():
    """The other half: a typed class is not the point on its own — the measurement that
    fired the refusal is. Each of the six modules is exercised on the input that used to
    reach a `SystemExit`, and the evidence dict must name its gate."""
    import make_ab_clip
    import make_shotset_sheet
    import make_zoom_sheet

    with pytest.raises(make_ab_clip.ABClipError) as e:
        make_ab_clip.frame_paths(os.path.dirname(os.path.abspath(__file__)))
    assert e.value.evidence["gate"] == "FRAMES"

    with pytest.raises(make_shotset_sheet.ShotsetSheetError) as e:
        make_shotset_sheet.load_set(os.path.dirname(os.path.abspath(__file__)))
    assert e.value.evidence["gate"] == "MANIFEST"

    # every converted class is one of this repo's own errors, catchable as a family
    from armature_core.errors import ArmatureError

    for cls in (make_ab_clip.ABClipError, make_shotset_sheet.ShotsetSheetError,
                make_zoom_sheet.ZoomSheetError):
        assert issubclass(cls, ArmatureError), cls
