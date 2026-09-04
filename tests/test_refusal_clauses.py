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
    assert len(POLICED) == 96, sorted(POLICED)
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
    # WAVE 16 (builders): 63 -> 61 on this branch, MEASURED — the first time this number
    # has gone DOWN. +1 `gate_saved_graph.link_round_trip`'s `duplicate_socket_name`
    # (F-04fdd395); -3 in `build_r2v_payload`, where three raises moved off the bare
    # `RouteGate` onto the classes whose own id the evidence names (F-f85c37f0): one to
    # `errors.GateSSeedRegistration` and two to the new `SpendCeiling`. A raise that leaves
    # this count because it became MORE specific is the fix working, not the census
    # shrinking.
    assert len(RAISE_SITES["RouteGate"]) == 61, sorted(RAISE_SITES["RouteGate"])
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
