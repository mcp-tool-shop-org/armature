"""Gate unit tests.

Every one of these asks the question CLAUDE.md asks of a fixture: *what would this
look like if the code were wrong in the specific way this check exists to catch?*
"""

import os

import pytest

from conftest import assert_gate, gate_failure_subclasses
from armature_core import gates
from armature_core.errors import (
    G1GeneratorLegality,
    G2Completeness,
    G4BboxSanity,
    G5ConventionConformance,
    GateFailure,
)


# ------------------------------------------------------------------ G1 goes red

def test_g1_passes_a_legal_frame():
    profile = gates.g1_generator_legality(512, 768, 33, "wan-vace")
    assert profile.dim_divisor == 16
    assert profile.frame_modulus == 4 and profile.frame_residue == 1


def test_g1_red_on_width_not_divisible_by_16():
    # 1020 is the spec's named case: 1020 = 63.75 * 16.
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(1020, 768, 33, "wan-vace")
    assert "width=1020" in str(exc.value)
    # Through `assert_gate` rather than on the message alone: a gate whose evidence dict
    # went empty on a refactor would keep this message and stop carrying the numbers.
    assert_gate(exc, "G1", width=1020, height=768, frame_count=33, problems=...)


def test_g1_red_on_height_not_divisible_by_16():
    with pytest.raises(G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-vace'"):
        gates.g1_generator_legality(512, 770, 33, "wan-vace")


def test_g1_red_on_frame_count_not_4n_plus_1():
    # 80 is the spec's named case: 80 % 4 == 0, not 1.
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(512, 768, 80, "wan-vace")
    assert "4n+1" in str(exc.value)
    assert_gate(exc, "G1", frame_count=80, problems=...)


# The sweep's own population. `81 + 1` sat here and evaluated to 82, whose residue is 2 —
# so the four values covered residues {0, 2, 3} and the accept branch below never ran once.
# 81 is the legal 4n+1 value that arm needs.
G1_RESIDUE_SWEEP = [80, 81, 34, 35, 36]


def test_the_residue_sweep_actually_covers_every_residue():
    """The guard on the sweep. A parametrisation that lost its 4n+1 value turns the
    accept branch below into a branch that cannot run, and a branch that cannot run
    cannot fail — the test would keep its name and stop making its claim."""
    assert {c % 4 for c in G1_RESIDUE_SWEEP} == {0, 1, 2, 3}


@pytest.mark.parametrize("count", G1_RESIDUE_SWEEP)
def test_g1_only_accepts_the_right_residue(count):
    if count % 4 == 1:
        profile = gates.g1_generator_legality(512, 768, count, "wan-vace")
        # Not merely "it did not raise": the accepted count must be accepted for the
        # stated reason, on the modulus and residue the profile itself declares.
        assert profile.frame_modulus == 4 and profile.frame_residue == 1
        assert count % profile.frame_modulus == profile.frame_residue
    else:
        with pytest.raises(G1GeneratorLegality, match=r"\[G1\] frame is not legal for generator 'wan-vace': frame"):
            gates.g1_generator_legality(512, 768, count, "wan-vace")


def test_g1_red_on_unknown_generator():
    """The andon is on the direction the invariant does not bound: an unknown
    generator is the case where *nothing* would be checked."""
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(512, 768, 33, "some-model-nobody-filed")
    assert "unknown generator profile" in str(exc.value)
    assert_gate(exc, "G1", generator="some-model-nobody-filed", known=...)


def test_g1_red_on_bool_masquerading_as_int():
    with pytest.raises(G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-vace': width"):
        gates.g1_generator_legality(True, 768, 33, "wan-vace")


def test_g1_is_not_an_assertionerror():
    """`assert` is deleted by -O; a gate that raised AssertionError would vanish."""
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(1020, 768, 33, "wan-vace")
    assert not isinstance(exc.value, AssertionError)


# ------------------------------------------------------------------ G2 goes red

def _make_channel(tmp_path, name, filenames, blank=(), missing=()):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    for f in filenames:
        if f in missing:
            continue
        (d / f).write_bytes(b"" if f in blank else b"x" * 32)
    return d


def test_g2_passes_a_complete_export(tmp_path):
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names)
    detail = gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert detail["mask"]["present"] == 5


def test_g2_red_on_a_truncated_directory(tmp_path):
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names, missing={names[3]})
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert "4 frames present, expected 5" in str(exc.value)
    assert_gate(exc, "G2", frame_count=5, run_dir=..., channels=...)


def test_g2_red_on_a_zero_length_frame(tmp_path):
    """A frame file that exists but is empty is the failure that looks finished."""
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names, blank={names[2]})
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert "zero-length" in str(exc.value)
    assert_gate(exc, "G2", frame_count=5, channels=...)


def test_g2_red_on_a_missing_directory(tmp_path):
    names = [f"{i:05d}.png" for i in range(3)]
    with pytest.raises(G2Completeness,
                       match=r"\[G2\] export is incomplete: edge: directory missing"):
        gates.g2_completeness(str(tmp_path), {"edge": names}, 3)


# ------------------------------------------------------------------ G4 goes red

def test_g4_passes_when_the_boxes_agree():
    deltas = gates.g4_bbox_sanity(0, (10, 20, 60, 90), (10, 20, 61, 90), 128, 128)
    assert max(deltas) == 1


def test_g4_red_on_facets_actual_failure():
    """facet's version caught a mask 751 px wide in a 752 px frame when the mesh was
    388. That is this case."""
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), 752, 752)
    assert exc.value.gate == "G4"
    assert "disagrees" in str(exc.value)
    assert_gate(exc, "G4", frame=7, tolerance_px=2, mask_bbox=..., projected_bbox=...,
                deltas_px=...)


def test_g4_red_on_an_empty_mask():
    """The direction the superset check does not bound: a collapsed mask."""
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(3, None, (10, 10, 100, 100), 128, 128)
    assert "mask is empty" in str(exc.value)
    assert_gate(exc, "G4", frame=3, mask_bbox=None, projected_bbox=...)


def test_g4_red_when_nothing_projects():
    with pytest.raises(G4BboxSanity,
                       match=r"\[G4\] frame 0: no mesh vertex projects into the frame, so"):
        gates.g4_bbox_sanity(0, (10, 10, 20, 20), None, 128, 128)


# ------------------------------------------------------------------ G5 goes red

def test_g5_passes_against_f20():
    from armature_core import openpose

    assert gates.g5_openpose_conformance(
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ,
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ,
    )


def test_g5_red_on_coco17():
    from armature_core import openpose

    with pytest.raises(G5ConventionConformance) as exc:
        gates.g5_openpose_conformance(17, openpose.LIMB_SEQ, 18, openpose.LIMB_SEQ)
    assert "keypoint count 17 != 18" in str(exc.value)
    assert_gate(exc, "G5", keypoint_count=17, reference_count=18, problems=...)


def test_g5_red_on_zero_indexing():
    """F20's limbSeq is 1-indexed. A from-scratch renderer that helpfully 'fixed' the
    off-by-one would produce exactly this, and it must not pass."""
    from armature_core import openpose

    zero_indexed = [[a - 1, b - 1] for a, b in openpose.LIMB_SEQ]
    with pytest.raises(G5ConventionConformance) as exc:
        gates.g5_openpose_conformance(18, zero_indexed, 18, openpose.LIMB_SEQ)
    assert "1-indexed" in str(exc.value) or "limb pair" in str(exc.value)


def test_g5_red_on_a_dropped_pair():
    """`match=` added 2026-09-04 (wave 12): G5 gained a second refusal — an empty reference
    convention — so its class name stopped being its clause and
    `tests/test_refusal_clauses.py` caught this site. Without the match, an empty-reference
    refusal raised for the wrong reason would satisfy a test named for a dropped pair."""
    from armature_core import openpose

    with pytest.raises(G5ConventionConformance, match=r"limb pair count 18 != 19"):
        gates.g5_openpose_conformance(18, openpose.LIMB_SEQ[:-1], 18, openpose.LIMB_SEQ)


# --- A3's profile row, added for E02. ---------------------------------------------


def test_wan_fun_control_profile_exists_and_binds_the_same_constraints():
    """A3 could not run until this row existed: G1 raises on an unknown generator.

    The row's provenance is a derivation from the VAE both routes share, not a
    separate retrieval, and the profile's `source` says so in those words. This test
    pins that the row is honest about it — if someone later rewrites the source string
    to imply a Fun-Control document was fetched, this fails.
    """
    from armature_core.gates import GENERATOR_PROFILES, g1_generator_legality

    p = GENERATOR_PROFILES["wan-fun-control"]
    assert (p.dim_divisor, p.frame_modulus, p.frame_residue) == (16, 4, 1)
    assert "DERIVED" in p.source
    assert "No Fun-Control-specific document was retrieved." in p.source
    assert g1_generator_legality(480, 832, 33, "wan-fun-control") is p


def test_wan_fun_control_rejects_the_same_near_misses_as_vace():
    """Both routes must halt on the same illegal frames, or A3 is not comparable."""
    from armature_core.errors import G1GeneratorLegality
    from armature_core.gates import g1_generator_legality

    for w, h, n in ((480, 832, 32), (470, 832, 33), (480, 830, 33)):
        for gen in ("wan-vace", "wan-fun-control"):
            with pytest.raises(G1GeneratorLegality,
                               match=r"\[G1\] frame is not legal for generator 'wan-"):
                g1_generator_legality(w, h, n, gen)


# --- W3 amend: the G2 population is the directory, not the expectation ------------
#
# What would this look like if the code were wrong in the way the check exists to
# catch? The loop that iterates `filenames` can only ever discover *absence*. A stale
# frame left by a longer previous run is present, correctly named, and out of range —
# and `len(present) != frame_count` cannot see it, because `present` is built from the
# expectation. The consumers build their populations with `os.listdir` (encode_control,
# gate_b_frames), so the extra frame reaches the encoder that G2 declared complete.


def test_g2_red_on_a_stale_out_of_range_frame(tmp_path):
    """The direction `len(present) != frame_count` does not bound.

    Gate B's own docstring already argues this shape: "a batch larger than submitted is
    as wrong as a smaller one". G2 must say the same about a directory.
    """
    names = [f"{i:05d}.png" for i in range(2)]
    _make_channel(tmp_path, "depth", names + ["99999.png"])
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"depth": names}, 2)
    assert "unexpected" in str(exc.value)
    assert "99999.png" in str(exc.value)
    assert exc.value.evidence["channels"]["depth"]["unexpected"] == ["99999.png"]


def test_g2_reports_unexpected_beside_missing_and_empty(tmp_path):
    """The refusal shape the encoder side of the pair reads (P1)."""
    names = [f"{i:05d}.png" for i in range(3)]
    _make_channel(tmp_path, "mask", names)
    detail = gates.g2_completeness(str(tmp_path), {"mask": names}, 3)
    assert detail["mask"]["unexpected"] == []
    assert detail["mask"]["missing"] == [] and detail["mask"]["empty"] == []


def test_g2_ignores_a_sidecar_of_another_extension(tmp_path):
    """The channel's population is its frames. A note beside them is not a frame."""
    names = [f"{i:05d}.png" for i in range(2)]
    _make_channel(tmp_path, "mask", names + ["notes.json"])
    detail = gates.g2_completeness(str(tmp_path), {"mask": names}, 2)
    assert detail["mask"]["unexpected"] == []


# --- W3 amend: G4's tolerance is the gate's, not the spec's -----------------------


def test_g4_tolerance_is_a_module_constant_no_caller_supplies():
    """`gates.py`'s own docstring rules that a spec-supplied number is a skip flag
    wearing a schema's clothes. The same argument binds for G4: if the tolerance is a
    parameter, one extra zero passes a mask that is not the subject."""
    import inspect

    assert gates.G4_TOLERANCE_PX == 2
    params = list(inspect.signature(gates.g4_bbox_sanity).parameters)
    assert params == ["frame_index", "mask_bbox", "projected_bbox", "width", "height"]


def test_g4_still_goes_red_on_facets_failure_without_a_tolerance_argument():
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), 752, 752)
    assert exc.value.evidence["tolerance_px"] == gates.G4_TOLERANCE_PX
    assert "gates.G4_TOLERANCE_PX" in exc.value.evidence["tolerance_source"]

# ------------------------------------------------- the class-wide invariant on the andons

def test_every_gate_failure_subclass_declares_its_own_id():
    """`GateFailure.gate` defaults to `"G?"`. A subclass that forgets to override it
    raises an andon that no report can name, and every message-string assertion in the
    suite stays green through it. Enumerated, so a gate added later cannot opt out."""
    subs = gate_failure_subclasses()
    assert subs, "no GateFailure subclasses found; the enumeration is broken, not clean"
    anonymous = [c.__name__ for c in subs if c.gate == GateFailure.gate]
    assert not anonymous, f"these carry the default gate id {GateFailure.gate!r}: {anonymous}"
    blank = [c.__name__ for c in subs if not isinstance(c.gate, str) or not c.gate.strip()]
    assert not blank, blank


#: Gate ids carried by more than one andon today, with the pair that carries each. Both
#: are one law applied in two tools — the alpha law on a start frame and on a turnaround
#: master, determinism on a rig and on a parts build — so a report that names `[ALPHA]`
#: or `[D]` needs its message to say which. Recorded rather than changed here: those are
#: other domains' files, and a rename would move strings that provenance records already
#: carry. The assertion is that this population may not GROW.
SHARED_GATE_IDS = {
    "ALPHA": {"AlphaGate", "TurnaroundAlphaGate"},
    "D": {"GateDDeterminism", "GatePartsDeterminism"},
}


def test_no_new_andon_takes_an_id_another_andon_already_uses():
    """Two andons sharing an id makes a report ambiguous about which one pulled.

    Measured 2026-09-03 with every `armature_core` module imported: 29 subclasses, of
    which two ids are shared by exactly two classes each. A third class on either id, or a
    new collision, is a report nobody can read back.
    """
    subs = gate_failure_subclasses()
    by_id = {}
    for cls in subs:
        by_id.setdefault(cls.gate, set()).add(cls.__name__)

    shared = {gate: names for gate, names in by_id.items() if len(names) > 1}
    assert shared == SHARED_GATE_IDS, (
        f"the gate ids carried by more than one andon are now {shared}; recorded is "
        f"{SHARED_GATE_IDS}. An id shared by a third class, or a new collision, makes a "
        f"provenance record ambiguous about which andon pulled.")


def test_the_subclass_walk_sees_every_andon_not_just_the_imported_ones():
    """`__subclasses__()` only knows about classes whose module has been imported, so a
    walk that did not force the imports would check a population that changes with
    collection order — measured: 12 andons from test_gates.py alone, 29 from the full
    suite. The helper imports every core module first; this is what says it still does."""
    names = {c.__name__ for c in gate_failure_subclasses()}
    assert len(names) >= 29, sorted(names)
    for expected in ("AlphaGate", "GatePartsDeterminism", "RouteGate", "PairGate",
                     "GateCanon", "G1GeneratorLegality"):
        assert expected in names, f"{expected} missing from {sorted(names)}"


#: Re-derived 2026-09-04 (wave 10, F-27a92797) with `blender_scene` imported under
#: `blender_stub.blender_stubbed()`. Size AND membership, so a new andon fails HERE by name
#: rather than sliding under a `>= 29`.
#:
#: MERGE NOTE: core-solvers' branch adds `CadenceGate` (gate CADENCE), `GaitGate` (GAIT) and
#: `PinnedCameraGate` (PIN) as `GateFailure` subclasses (SEAM 1, 2026-09-04). Re-DERIVE this
#: list after the merge — never hand-edit it to make the merge green.
RECORDED_ANDON_CLASSES = [
    "assembly.AssemblyGate", "assembly.CascadeGate", "blender_scene.CompositorWiring",
    # WAVE 18 (core-solvers, F-25a5ecbf): `blender_scene.RenderedFrame`, gate `FRAME` —
    # `render_frame` was the one `bpy.ops.render.render` site in the live tree whose
    # operator status set was neither captured nor read, and the andon it now raises is a
    # `GateFailure` subclass, so it joins this population by construction. RE-DERIVED, not
    # typed: 35 -> 36, measured red at exactly this one member.
    "blender_scene.RenderedFrame",
    "donor_gate.DonorGate", "errors.G1GeneratorLegality", "errors.G2Completeness",
    "errors.G4BboxSanity", "errors.G5ConventionConformance", "errors.G6SubjectMotion",
    "errors.GateBBatching", "errors.GateCanon", "errors.GateDDeterminism",
    "errors.GateNNames", "errors.GatePRestPose", "errors.GateRRoundTrip",
    "errors.GateSSeedRegistration",
    # WAVE-10 MERGE (coordinator, 2026-09-04): `walk.WalkError` / `framing.FramingError` rejoined the `ArmatureError`
    # family and their named andons split off as `GateFailure` subclasses (core-solvers, seam 1):
    # 32 -> 35, re-derived on the merged tree.
    "framing.PinnedCameraGate", "glb.GateAtlasUntouched", "glb.ReliftMismatch",
    "landmarks.FacingGate", "lift_solve.SolveGate", "parts.GatePartsAccounting",
    "parts.GatePartsDeterminism", "parts.GateRigidArrival", "resample.ResampleGate",
    "route_gates.PairGate", "route_gates.RouteGate", "startframe.AlphaGate",
    "startframe.BackdropGate", "startframe.StartFrameGate", "turnaround.TurnaroundAlphaGate",
    "turnaround.TurnaroundCropGate", "turnaround.TurnaroundGate", "walk.CadenceGate",
    "walk.GaitGate",
]


def package_andons():
    """The andons DEFINED BY `armature_core`, as `<module>.<class>`, deduplicated.

    Two filters, each measured rather than assumed:

    * `__module__.startswith("armature_core")` — `gate_failure_subclasses()` deliberately
      returns test-local decoys too (`test_the_enumeration_would_catch_a_new_andon_that_
      forgot_its_id` depends on that), and a decoy is not a member of the package.
    * DEDUPLICATED — measured 2026-09-04 running `tests/test_core_solver_evidence.py`
      first: `gate_failure_subclasses()` returns 38 classes with six names twice
      (`AlphaGate`, `BackdropGate`, `StartFrameGate`, `TurnaroundAlphaGate`,
      `TurnaroundCropGate`, `TurnaroundGate`). That file re-imports `startframe` and
      `turnaround` under `blender_stub.blender_stubbed()`, whose teardown pops them out of
      `sys.modules`, so the next import builds a SECOND class object of the same name. That
      is a property of the suite's fixtures, not of the package, and the module-qualified
      key keeps two genuinely different classes with one name apart while collapsing two
      objects of the same one.
    """
    return sorted({f"{c.__module__.split('.')[-1]}.{c.__name__}"
                   for c in gate_failure_subclasses()
                   if c.__module__.startswith("armature_core")})


def test_the_andon_population_is_the_one_the_class_wide_invariants_are_asked_of():
    """Size and membership before the property.

    THE NODE: the class hierarchy rooted at `GateFailure`, with every `armature_core`
    module imported first. Until wave 10 the enumerator SKIPPED `armature_core.
    blender_scene` on the premise that it "imports bpy and cannot resolve under a plain
    CPython" — a premise this suite's own `blender_stub.blender_stubbed()` falsifies, and
    which `tests/test_core_solver_evidence._gate_raises` already walks that module through.
    Measured 2026-09-04: 31 classes before, 32 after, the newcomer `CompositorWiring`.
    """
    names = package_andons()
    assert names == RECORDED_ANDON_CLASSES, {
        "appeared": sorted(set(names) - set(RECORDED_ANDON_CLASSES)),
        "vanished": sorted(set(RECORDED_ANDON_CLASSES) - set(names)),
    }


def test_the_andon_the_enumerator_used_to_skip_is_asked_the_class_wide_invariants():
    """The measurement that overturned the exclusion, kept runnable.

    `CompositorWiring` passes both invariants today, so this was an unasked question rather
    than a live break — and a census whose guarantee is "no new andon can opt out" cannot
    have a module it never asks.
    """
    from armature_core.errors import GateFailure as GF

    assert "blender_scene.CompositorWiring" in package_andons(), package_andons()
    cls = next(c for c in gate_failure_subclasses() if c.__name__ == "CompositorWiring")
    assert cls.__module__ == "armature_core.blender_scene"
    assert cls.gate == "COMPOSITOR" and cls.gate != GF.gate
    assert str(cls("something happened")).startswith("[COMPOSITOR] ")

    # The falsified premise, MEASURED rather than asserted — in a subprocess, because
    # observing it in this one would mean writing into `sys.modules`, which is the thing
    # `test_packaging.sys_modules_writers` exists to forbid outside the three installers.
    import subprocess
    import sys as _sys

    from conftest import TOOLS

    proc = subprocess.run(
        [_sys.executable, "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "import armature_core.blender_scene", TOOLS],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode != 0, (
        "blender_scene now imports under a plain CPython; re-derive this exclusion")
    assert "bpy" in proc.stderr, proc.stderr[-800:]

    # …and calling the enumerator twice returns the same population: the module is imported
    # exactly once and held by a strong reference, so the stub teardown neither unregisters
    # the class nor lets a second import register a duplicate.
    assert package_andons() == RECORDED_ANDON_CLASSES


def test_the_enumeration_would_catch_a_new_andon_that_forgot_its_id():
    """The red direction. A check that only ever runs on a clean population is unproven,
    so an andon that forgets is defined here and the same enumeration must find it."""

    class _AndonThatForgot(GateFailure):
        pass

    try:
        subs = gate_failure_subclasses()
        assert _AndonThatForgot in subs, "the walk does not reach a locally defined subclass"
        anonymous = [c.__name__ for c in subs if c.gate == GateFailure.gate]
        assert anonymous == ["_AndonThatForgot"], anonymous
    finally:
        # Subclass registration is process-global and weakly held; drop the only
        # references so a later run of the two tests above does not see this decoy.
        import gc

        del _AndonThatForgot, subs, anonymous
        gc.collect()
        assert not [c for c in gate_failure_subclasses() if c.gate == GateFailure.gate]


def test_the_gate_id_prefixes_the_message_a_report_prints():
    """`__str__` is what reaches a log. The id has to be in it or the andon is anonymous
    at exactly the moment somebody is reading."""
    for cls in gate_failure_subclasses():
        assert str(cls("something happened")).startswith(f"[{cls.gate}] ")


def test_an_evidence_free_gate_is_what_assert_gate_exists_to_refuse():
    """The defect this helper closes: `self.evidence = evidence or {}` makes a gate raised
    with no measurement well-formed and silent."""
    bare = G1GeneratorLegality("something is wrong")
    assert bare.evidence == {}
    with pytest.raises(AssertionError, match="EMPTY evidence dict"):
        assert_gate(bare, "G1")

    carried = G1GeneratorLegality("something is wrong", {"width": 1020})
    assert assert_gate(carried, "G1", width=1020) == {"width": 1020}
    with pytest.raises(AssertionError, match="no 'height'"):
        assert_gate(carried, "G1", height=768)
    # the class name is the phrase; the quoted id is anchored by the newline that follows
    # it, so `'G1'` cannot be satisfied by a message reading `'G1x'` (F-02683edb)
    with pytest.raises(AssertionError, match=r"raised G1GeneratorLegality with gate 'G1'\n"):
        assert_gate(carried, "G4")


#: Gate raises in `tools/` that pass a message and no evidence. All three raise the BASE
#: `GateFailure`, whose `gate` is the default `"G?"`, so the andon they pull is anonymous
#: as well as evidence-free. Recorded rather than fixed here: `tools/` is another domain's
#: territory, and the point of the assertion below is that this population may not GROW.
EVIDENCE_FREE_GATE_RAISES = {
    ("tools/build_lora_arm_payload.py", "GateFailure"),
    ("tools/rig_bake.py", "GateFailure"),
}


def _gate_raises_without_evidence():
    """Every `raise <a GateFailure type>(msg)` under `tools/` with no evidence argument."""
    import ast
    import warnings

    names = {c.__name__ for c in gate_failure_subclasses()} | {"GateFailure"}
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    found, total = set(), 0
    for root, dirs, files in os.walk(tools):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            with warnings.catch_warnings():
                # `tools/make_e08_sheet.py:4` carries an invalid escape (`"\m"` in a
                # Windows path inside its docstring) and every parse of it warns. That is
                # a defect in another domain's file, routed rather than silenced at the
                # source; this walk is not the place it should surface.
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source)
            rel = "tools/" + os.path.relpath(path, tools).replace(os.sep, "/")
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                    continue
                func = node.exc.func
                cls = (func.id if isinstance(func, ast.Name)
                       else func.attr if isinstance(func, ast.Attribute) else None)
                if cls not in names:
                    continue
                total += 1
                if len(node.exc.args) < 2 and not any(
                        kw.arg == "evidence" for kw in node.exc.keywords):
                    found.add((rel, cls))
    return found, total


def test_no_new_gate_raise_ships_without_its_evidence():
    """A ratchet, not a clean bill. Measured 2026-09-03: 33 gate raises under `tools/`,
    of which 3 (in 2 files) pass a message alone. The invariant to hold going forward is
    that no FOURTH joins them — every andon a spend or a render halts on must carry the
    measurement that fired it, or the report names a gate with nothing behind it."""
    found, total = _gate_raises_without_evidence()
    assert total >= 30, f"only {total} gate raises found; the walk is not reaching tools/"
    new = sorted(found - EVIDENCE_FREE_GATE_RAISES)
    assert not new, (
        f"these gate raises carry no evidence dict: {new}. Pass the measurement that "
        f"fired the gate as the second argument.")


# --------------------------------------- the receipt's id lives in the evidence too

#: WAVE 8, F-99e15391 — the census below was blind in three directions at once and
#: returned `[]` on a tree carrying 31 evidence dicts with no `gate` key.
#:
#: (a) Its per-function filter was `if not any("Gate" in name for name in raised)`, so
#:     every andon whose CLASS NAME has no "Gate" substring was skipped outright —
#:     `G1GeneratorLegality`, `G2Completeness`, `G5ConventionConformance`,
#:     `G6SubjectMotion`. A naming convention is not a class hierarchy.
#: (b) It examined only `ast.Assign` nodes whose target was a `Name` called `ev` or
#:     `evidence` and whose value was a `Dict` literal. Most of the package raises
#:     `SomeGate(msg, {...})` INLINE, and that shape was never examined at all.
#: (c) The red-direction test re-implemented the walk inline instead of calling the
#:     shipped function, so it showed that `ast.walk` can find a `Dict` — not that this
#:     census can see one.
#:
#: The walk below resolves the dict actually handed to each raise: the second positional
#: argument, an `evidence=` keyword, a `Name` resolved back to its assignment in the same
#: function, or the base of a `dict(ev, ...)` update. The population is every raise of a
#: class in the `ArmatureError` hierarchy, derived from the tree.
#:
#: WHY THE KEY MATTERS: `stage_render.py` records a halt as one six-key
#: `STAGE_RENDER_HALT <json>` line whose `gate` and `evidence` are separate keys, so a
#: reader holding only the evidence dict has no id at all — and ids are shared across
#: andon families ("D" by
#: (CORRECTED wave 14: this sentence named `GATE_FAILURE` / `GATE_EVIDENCE`, two lines
#: the handler no longer prints. The property it argues for is unchanged.)
#: `GateDDeterminism` and `GatePartsDeterminism`, "ALPHA" by `AlphaGate` and
#: `TurnaroundAlphaGate`), so the prose beside it is not enough either.

import ast as _ast
import pathlib as _pathlib

CORE_DIR = _pathlib.Path(__file__).resolve().parents[1] / "tools" / "armature_core"
TOOLS_DIR = _pathlib.Path(__file__).resolve().parents[1] / "tools"


def _armature_error_family(tools_root):
    """Every class under `tools/` whose bases reach `ArmatureError`, transitively."""
    bases = {}
    for path in sorted(_pathlib.Path(tools_root).rglob("*.py")):
        if "superseded" in path.parts or "__pycache__" in path.parts:
            continue
        for node in _ast.walk(_ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, _ast.ClassDef):
                bases.setdefault(node.name, set()).update(
                    b.id for b in node.bases if isinstance(b, _ast.Name))
    family = {"ArmatureError"}
    growing = True
    while growing:
        growing = False
        for name, parents in bases.items():
            if name not in family and (parents & family):
                family.add(name)
                growing = True
    return family


def _enclosing_function(tree):
    owner = {}
    for fn in _ast.walk(tree):
        if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            for node in _ast.walk(fn):
                owner.setdefault(node, fn)
    return owner


def _resolve_dict_expr(node, fn, before_line):
    """Follow an expression back to a `Dict` node, or `"UNRESOLVED"`.

    Shapes: a dict literal; `dict(base, ...)`; `dict(x or {})` (the BoolOp base — canon.py:
    91); and a `Name` resolved to its latest assignment above `before_line` inside `fn`.
    """
    for _ in range(5):
        if isinstance(node, _ast.Dict):
            return node
        if isinstance(node, _ast.Call) and getattr(node.func, "id", "") == "dict":
            if not node.args:
                return "UNRESOLVED"
            arg = node.args[0]
            if isinstance(arg, _ast.BoolOp) and isinstance(arg.op, _ast.Or) and arg.values:
                arg = arg.values[0]
            node = arg
            continue
        if isinstance(node, _ast.Name) and fn is not None:
            latest = None
            for assign in _ast.walk(fn):
                if (isinstance(assign, _ast.Assign) and assign.lineno < before_line
                        and any(isinstance(t, _ast.Name) and t.id == node.id
                                for t in assign.targets)):
                    latest = assign.value
            if latest is None:
                return "UNRESOLVED"
            node = latest
            continue
        return "UNRESOLVED"
    return "UNRESOLVED"


def _evidence_expr(raise_node):
    """The expression handed to this raise as evidence, or `None`."""
    exc = raise_node.exc
    if not isinstance(exc, _ast.Call):
        return None
    node = exc.args[1] if len(exc.args) >= 2 else None
    for kw in exc.keywords:
        if kw.arg == "evidence":
            node = kw.value
    return node


def _evidence_node(raise_node, fn):
    """The dict handed to this raise: `None` (none given) or a node, or `"UNRESOLVED"`."""
    node = _evidence_expr(raise_node)
    if node is None:
        return None
    return _resolve_dict_expr(node, fn, raise_node.lineno)


def _evidence_name(raise_node):
    """The NAME the evidence was handed under, if it was handed under one."""
    exc = raise_node.exc
    if not isinstance(exc, _ast.Call):
        return None
    node = exc.args[1] if len(exc.args) >= 2 else None
    for kw in exc.keywords:
        if kw.arg == "evidence":
            node = kw.value
    return node.id if isinstance(node, _ast.Name) else None


def _dict_call_keyword_keys(raise_node):
    """Keys supplied as KEYWORDS to a `dict(base, gate=..., andon=...)` evidence argument.

    `donor_gate.ankle_framing` builds its evidence as
    `dict({k: v for ...}, gate="DONOR", andon="DonorGate")`: the base is a comprehension
    the walk cannot read, but the two keys the census asks about are right there.
    """
    exc = raise_node.exc
    if not isinstance(exc, _ast.Call):
        return set()
    node = exc.args[1] if len(exc.args) >= 2 else None
    for kw in exc.keywords:
        if kw.arg == "evidence":
            node = kw.value
    if isinstance(node, _ast.Call) and getattr(node.func, "id", "") == "dict":
        return {kw.arg for kw in node.keywords if kw.arg}
    return set()


def _update_keys(fn, name, before_line):
    """Keys added by `name.update({...})` inside `fn`, above `before_line`."""
    if fn is None or name is None:
        return set()
    keys = set()
    for node in _ast.walk(fn):
        if not isinstance(node, _ast.Call) or getattr(node, "lineno", 0) >= before_line:
            continue
        func = node.func
        if not (isinstance(func, _ast.Attribute) and func.attr == "update"
                and isinstance(func.value, _ast.Name) and func.value.id == name):
            continue
        for arg in node.args:
            if isinstance(arg, _ast.Dict):
                keys.update(k.value for k in arg.keys
                            if isinstance(k, _ast.Constant) and isinstance(k.value, str))
        keys.update(kw.arg for kw in node.keywords if kw.arg)
    return keys


def _subscript_keys(fn, name, before_line):
    """Keys added by `name["k"] = ...` inside `fn`, above `before_line`.

    The second live shape the walk could not read (F-b01840fc): a dict built or received
    earlier and MUTATED by subscript — `ev["andon"] = "GateCanon"` at canon.py:91,
    `ev` as a function PARAMETER at gates.py:668/675 and route_gates.py:857/867/875. The
    old walk returned `UNRESOLVED` for all of them, and `UNRESOLVED` was silently skipped,
    so ten `GateFailure` raise sites were invisible to a property test whose whole claim
    was that it read every one.
    """
    if fn is None or name is None:
        return set()
    keys = set()
    for node in _ast.walk(fn):
        if not isinstance(node, _ast.Assign) or node.lineno >= before_line:
            continue
        for target in node.targets:
            if (isinstance(target, _ast.Subscript)
                    and isinstance(target.value, _ast.Name) and target.value.id == name
                    and isinstance(target.slice, _ast.Constant)
                    and isinstance(target.slice.value, str)):
                keys.add(target.slice.value)
    return keys


#: `_evidence_keys` verdicts.
#:   NONE      — no evidence argument at all (a different defect; `EVIDENCE_FREE_GATE_RAISES`)
#:   LITERAL   — every key is readable, so ABSENCE of a key is provable
#:   AUGMENTED — a `**spread`, a parameter, or `dict(x or {})` base: PRESENCE is provable
#:               from the subscript writes, absence is not
#:   UNREADABLE— nothing about the keys is knowable
EV_NONE, EV_LITERAL, EV_AUGMENTED, EV_UNREADABLE = "NONE", "LITERAL", "AUGMENTED", "UNREADABLE"


def _builder_keys(tree, call_node):
    """Keys of the dict a module-local builder RETURNS, when every return is a literal.

    `lift_solve.gate_round_trip` does `ev = round_trip_report(...)` and raises with `ev`;
    the keys are one function away, and following one hop is the difference between
    "unreadable" and reading the `{"gate": "SOLVE", "andon": "SolveGate", …}` that is
    actually there. Returns `(keys, complete)` — `complete` is False when any return is not
    a dict literal, in which case absence is still not provable.
    """
    if not isinstance(call_node, _ast.Call):
        return set(), False
    name = getattr(call_node.func, "id", None)
    if name is None:
        return set(), False
    target = next((n for n in tree.body
                   if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                   and n.name == name), None)
    if target is None:
        return set(), False
    keys, complete, saw = set(), True, False
    for node in _ast.walk(target):
        if not isinstance(node, _ast.Return) or node.value is None:
            continue
        saw = True
        value = _resolve_dict_expr(node.value, target, node.lineno)
        if isinstance(value, _ast.Dict) and not any(k is None for k in value.keys):
            local = {k.value for k in value.keys
                     if isinstance(k, _ast.Constant) and isinstance(k.value, str)}
            if isinstance(node.value, _ast.Name):
                local |= _subscript_keys(target, node.value.id, node.lineno)
                local |= _update_keys(target, node.value.id, node.lineno)
            keys.update(local)
        else:
            complete = False
    return keys, (complete and saw)


def _evidence_keys(raise_node, fn, tree=None):
    """`(keys, verdict)` for one raise — see the four verdicts above."""
    found = _evidence_node(raise_node, fn)
    name = _evidence_name(raise_node)
    written = (_subscript_keys(fn, name, raise_node.lineno)
               | _update_keys(fn, name, raise_node.lineno)
               | _dict_call_keyword_keys(raise_node))
    if found is None:
        return set(), EV_NONE
    if found == "UNRESOLVED":
        # one hop into a module-local builder: `ev = round_trip_report(...)`
        if tree is not None and name is not None:
            expr = _evidence_expr(raise_node)
            latest = None
            if fn is not None and isinstance(expr, _ast.Name):
                for assign in _ast.walk(fn):
                    if (isinstance(assign, _ast.Assign)
                            and assign.lineno < raise_node.lineno
                            and any(isinstance(t, _ast.Name) and t.id == expr.id
                                    for t in assign.targets)):
                        latest = assign.value
            built, complete = _builder_keys(tree, latest)
            if built:
                return written | built, EV_LITERAL if complete else EV_AUGMENTED
        return written, EV_AUGMENTED if written else EV_UNREADABLE
    literal = {k.value for k in found.keys if isinstance(k, _ast.Constant)}
    if any(k is None for k in found.keys):          # `{**base, ...}`
        return literal | written, EV_AUGMENTED
    return literal | written, EV_LITERAL


def _site_key(path, fn, cls):
    """`<file>:<function> (<class>)` — the stable identity of a raise site.

    NOT the line number (wave 10, F-a30afea5): a line number moves under any edit above it,
    and 23 of the 31 entries in the ratchet below named a `(file, line)` that no longer
    held a raise at all. `(file, function, class)` survives the edit that a line number does
    not, which is what an exemption has to do to stay meaningful.
    """
    return f"{path.name}:{fn.name if fn is not None else '<module>'} ({cls})"


def evidence_dicts_missing(key, root=None, classes=None):
    """Every raise in the `ArmatureError` family whose evidence dict omits `key`.

    Returns `(offenders, examined, unreadable, no_evidence)`:

    * `offenders` — sites whose keys are fully readable and where `key` is absent. A
      genuine defect: the receipt cannot name its own andon.
    * `examined` — every raise of the family this walk LOOKED AT, judged or not, so a
      census over nothing cannot read as a clean tree and the denominator cannot shrink in
      silence.
    * `unreadable` — sites this walk CANNOT decide: a `**spread`, a parameter, or a
      `dict(x or {})` base whose incoming keys are not knowable here, and where the
      subscript writes do not supply `key`. Returned rather than silently skipped, which is
      the wave-10 correction (F-b01840fc): 10 `GateFailure` raise sites were dropped as
      `UNRESOLVED` and never counted, while the consolidation that named this the
      authoritative walk said it "resolves those shapes". It did not; it dropped them.
    * `no_evidence` — sites that pass NO evidence argument at all. WAVE 12, F-1da3769f:
      `if verdict == EV_NONE: continue` sat ABOVE `examined += 1`, so such a raise was not
      an offender, not unreadable, and NOT COUNTED — it left both the numerator and the
      denominator through the same door F-b01840fc had closed three lines lower. Measured
      2026-09-04 over `armature_core/*.py`: 270 raises of the family, 102 of them EV_NONE
      across 50 distinct sites, leaving `examined` at 168 with `offenders == []` and
      `unreadable == []`. All 159 `GateFailure` raises carry a readable dict, so every one
      of the 102 is a PLAIN refusal — and `errors.py:24` is
      `self.evidence = evidence or {}`, so each raises a well-formed refusal whose evidence
      dict is empty and therefore omits `gate`, the exact property this census exists to
      police. The `assert examined >= 120` guard cleared 168 with 102 sites missing.

    Site identity is `(file, function, class)`, not a line number — see `_site_key`.
    """
    root = CORE_DIR if root is None else _pathlib.Path(root)
    family = _armature_error_family(TOOLS_DIR if root == CORE_DIR else root)
    # WAVE-10 MERGE (coordinator, 2026-09-04): `classes` narrows the walk to a subset of the family (bare class names)
    # so a caller comparing against a `GateFailure`-only population compares like with like —
    # since wave 10 a plain refusal in walk/framing/glb carries evidence too (`gate: None`).
    if classes is not None:
        family = {n for n in family if n in set(classes)}
    offenders, unreadable, no_evidence, examined = set(), set(), set(), 0
    for path in sorted(root.glob("*.py")):
        tree = _ast.parse(path.read_text(encoding="utf-8"))
        owner = _enclosing_function(tree)
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Raise) or node.exc is None:
                continue
            func = node.exc.func if isinstance(node.exc, _ast.Call) else node.exc
            name = (func.attr if isinstance(func, _ast.Attribute)
                    else getattr(func, "id", ""))
            if name not in family:
                continue
            fn = owner.get(node)
            keys, verdict = _evidence_keys(node, fn, tree)
            # COUNTED FIRST (wave 12, rule 3): the denominator is every raise the walk
            # looked at, never only the ones it could judge.
            examined += 1
            if verdict == EV_NONE:
                no_evidence.add(_site_key(path, fn, name))
                continue
            if key in keys:
                continue
            if verdict == EV_LITERAL:
                offenders.add(_site_key(path, fn, name))
            else:
                unreadable.add(_site_key(path, fn, name))
    return sorted(offenders), examined, sorted(unreadable), sorted(no_evidence)


def family_raise_count(root=None, classes=None):
    """Every raise of the `ArmatureError` family under `root` — the DENOMINATOR.

    Derived beside the census so `examined` can be asserted EQUAL to it rather than held
    above a floor. A floor is what let 102 sites leave the census in silence: 168 clears
    `>= 120` just as comfortably as 270 does.
    """
    root = CORE_DIR if root is None else _pathlib.Path(root)
    family = _armature_error_family(TOOLS_DIR if root == CORE_DIR else root)
    if classes is not None:
        family = {n for n in family if n in set(classes)}
    total = 0
    for path in sorted(root.glob("*.py")):
        for node in _ast.walk(_ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, _ast.Raise) or node.exc is None:
                continue
            func = node.exc.func if isinstance(node.exc, _ast.Call) else node.exc
            name = (func.attr if isinstance(func, _ast.Attribute)
                    else getattr(func, "id", ""))
            if name in family:
                total += 1
    return total


#: RE-DERIVED 2026-09-04 (wave 10, F-a30afea5) and EMPTY.
#:
#: What it held: 31 sites, keyed on `(file, LINE, function, class)`. Two things had gone
#: wrong with it at once. First, `evidence_dicts_missing("gate")` returns no offenders on
#: this tree, so `new = offenders - ROUTED` was empty and `set(offenders) <= ROUTED` was
#: trivially true over an empty set — both assertions were SUBSET assertions, so a
#: regression at any of the 31 named sites would have been re-admitted in silence, which
#: is the one direction the set existed to close. Second, the variable that would have
#: named the staleness, `closed`, was computed and used only as the failure MESSAGE of the
#: other assertion, so it could never fire; cross-checked against the AST, 23 of the 31
#: named a `(file, line)` that no longer held any raise at all.
#:
#: So: the assertion below is EQUALITY in both directions, and site identity is
#: `(file, function, class)` — a line number moves under any edit above it, which is how
#: 23 of 31 entries came to name nothing. A site that is closed must be deleted from this
#: set in the commit that closes it, and a site that regresses fails here.
EVIDENCE_WITHOUT_GATE_ID_ROUTED = set()

#: Raise sites whose evidence keys this walk cannot decide — named, dated, and asserted to
#: be a SUBSET of what the walk reports, so an exemption cannot outlive the shape it names.
#: EMPTY on 2026-09-04: the four shapes that were `UNRESOLVED` are now read (a parameter
#: mutated by `ev["k"] = ...`, `dict(x or {})`, `ev.update({...})`, `dict(base, gate=…)`,
#: and one hop into a module-local builder — `lift_solve.gate_round_trip`'s
#: `ev = round_trip_report(...)`). See F-b01840fc.
EVIDENCE_UNREADABLE_EXEMPT = set()

#: WAVE 12, F-1da3769f. Raise sites that pass NO evidence argument at all — a plain refusal
#: whose `evidence or {}` is empty and therefore omits `gate`. Named, dated 2026-09-04, and
#: re-derived from the walk itself, the way `EVIDENCE_UNREADABLE_EXEMPT` is.
#:
#: 50 sites when this set was written; 40 today (see the wave-14 block below — the ten
#: closed by wave 12's receipts are deleted). Every one of them is a plain refusal: all `GateFailure`
#: raises in the package carry a readable dict (the ONE-judge agreement test at
#: `tests/test_core_solver_evidence.py:266` confirms 159 == 159 under the class filter), so
#: nothing here is a gate that lost its evidence — it is the wave-10 contract, "a plain
#: refusal writes `gate: None` + `andon` + `clause`", realised on 9 of the 111 plain refusal
#: sites.
#:
#: **WAVE 14, F-95ac9f17 — RE-DERIVED to 40, and the direction is now EQUALITY.** The ceiling
#: DID shrink and the constant did not follow it. Measured on the wave-13 tree,
#: `evidence_dicts_missing('gate')` returned 40 no-evidence sites against this 50-entry set,
#: and the ten that named nothing were precisely the receipts core-solvers landed in wave 12:
#: `framing.py:_norm`, `framing.py:camera_basis`, `framing.py:ortho_half_spans`,
#: `framing.py:solve_camera`, `glb.py:_image_blob`, `walk.py:__init__`,
#: `walk.py:_integrate_forward`, `walk.py:_phase_schedule`, `walk.py:_rot`,
#: `blender_scene.py:union_sphere`. The comment below stated the discipline — "entries closed
#: by a receipt are deleted by the commit that adds it" — and the deletion did not happen at
#: the merge, so those ten were a standing permission slip: simulated by re-adding all ten to
#: `no_evidence`, `new` stayed `[]` and the test stayed green. A refactor in `framing` or
#: `walk` — the two modules with the most churn in this run — could have reverted the wave-12
#: plain-refusal contract for nine of its sites with no test to notice, and `errors.py`'s
#: `self.evidence = evidence or {}` then writes `evidence: null` into the halt line.
#:
#: The converse direction is asserted beside the growth one, which is the shape
#: `EVIDENCE_UNREADABLE_EXEMPT` already has by being empty: a routed entry that stops naming a
#: live site fails here rather than sitting as a silent exemption. Entries closed by a receipt
#: are deleted by the commit that adds it.
#:
#: Re-derive with:
#:     python -c "import sys;sys.path[:0]=['tests','tools'];import test_gates as G;\
#:     print(len(G.evidence_dicts_missing('gate')[3]))"
EVIDENCE_NO_EVIDENCE_ROUTED = {
    # WAVE-14 MERGE (coordinator, 2026-09-04): 8 routed entries left this set because they carry a receipt on the merged tree
    # (core-solvers gave every `aapose.py` refusal `gate: None` + andon + clause, F-d0de0c2d/F-d59fab92);
    # measured as `ROUTED - no_evidence`, deleted rather than commented.
    "binding.py:rigid_segment_weights (ArmatureError)",
    "joints.py:_limb_radius (LandmarkError)",
    "joints.py:snap_sites_to_balls (LandmarkError)",
    "joints.py:sphere_fit (LandmarkError)",
    "landmarks.py:_point_along (LandmarkError)",
    "landmarks.py:_prune_discontinuities (LandmarkError)",
    "landmarks.py:_region_runs (LandmarkError)",
    "landmarks.py:band_profile (LandmarkError)",
    "landmarks.py:bone_radii (LandmarkError)",
    "landmarks.py:cross_section_radius (LandmarkError)",
    "landmarks.py:derive (LandmarkError)",
    "landmarks.py:facing (LandmarkError)",
    "lift_solve.py:_bind_reference (SolveError)",
    "lift_solve.py:_unit (SolveError)",
    "lift_solve.py:bone_length_residuals (SolveError)",
    "lift_solve.py:frame_from (SolveError)",
    "lift_solve.py:sites_from_landmarks (SolveError)",
    "lift_solve.py:solve_frame (SolveError)",
    "openpose.py:require_drawing_convention (ArmatureError)",
    "parts.py:assign_faces (ArmatureError)",
    "parts.py:joint_planes (ArmatureError)",
    "posearc.py:angle_at_frame (SpecError)",
    "posearc.py:arc_readout (SpecError)",
    "posearc.py:resolve_arc (SpecError)",
    "resample.py:quat_normalise (ResampleError)",
    "resample.py:resample_frames (ResampleError)",
    "resample.py:sample_map (ResampleError)",
    "shotspec.py:_require (SpecError)",
    "shotspec.py:_require_positive (SpecError)",
    "shotspec.py:normalise_spec (SpecError)",
    "shotspec.py:resolve_asset (SpecError)",
    # WAVE 22 (core-solvers, F-4ce10f2a): `turnaround.py:projection_plan
    # (TurnaroundPlanRefusal)` LEFT this set — both ortho raises now carry a literal
    # evidence dict with a clause, matching the perspective sibling twenty lines below.
    # Deleted rather than commented in the commit that adds the receipt, which is what the
    # converse assertion below requires: a routed entry that names no live site re-admits
    # that site in silence.
}


def test_the_widened_census_examines_the_whole_core_and_not_a_naming_convention():
    """The population, before the property.

    WAVE 12, F-1da3769f: the guard was `assert examined >= 120`, a FLOOR — and a floor
    cannot tell you the denominator shrank. 168 cleared it just as comfortably as 270 does,
    with 102 raises leaving the census silently through the `EV_NONE` continue. It is now an
    EQUALITY against the family raise count derived beside it, so a site that stops being
    examined fails here rather than reducing the census's own scope.
    """
    family = _armature_error_family(TOOLS_DIR)
    assert len(family) >= 70, sorted(family)
    for outside_the_naming_convention in ("G1GeneratorLegality", "G2Completeness",
                                          "G5ConventionConformance", "G6SubjectMotion"):
        assert outside_the_naming_convention in family
    _, examined, _unreadable, _none = evidence_dicts_missing("gate")
    total = family_raise_count()
    assert examined == total, (
        f"the walk looked at {examined} of {total} `ArmatureError`-family raises in "
        f"armature_core; a raise it does not count is a raise it cannot police, and the "
        f"whole census reads as a clean tree over the gap")
    # WAVE-12 MERGE (coordinator, 2026-09-04): 270 → 296 on the merged tree — core-solvers re-classed 13 bare builtin
    # refusals into the family and added new refusals (`narrowed`, the vacuity guard, `MeasurementWithoutScene`,
    # `PngWriteError`'s zero-dimension clause), core-gates added 39 refusals of which the in-package ones
    # (`unreadable_node`, `uncredited_conditional_component`, `attribution_entry_for`, `gate_b_batching`,
    # `gate_n_names`, `g5` empty-reference, `canon.load`, `shotspec`) land here. Re-measured, not summed.
    # WAVE 14 (core-gates, 2026-09-04): 296 → 303 on this branch, MEASURED not summed.
    # The seven: `rig_gates._require_numeric` (a non-numeric bbox_diagonal, F-8a5683e0);
    # `subject.py`'s three refusals re-classed from bare `ValueError` into the family plus
    # its non-finite clause (F-89eb81a9); `gates.gate_s_seed_registration`'s empty declared
    # registry (F-b4706738); `route_gates.verify`'s `orphan_attribution` (F-74787978); and
    # `shotspec`'s two new named refusals — the render-engine enum and the
    # `normal_angle_deg` domain (F-b543a535). The four measurement guards of F-13a144c2
    # raise from `parts.require_finite`, which this count already carries.
    # WAVE-14 MERGE (coordinator, 2026-09-04): 303 (core-gates alone) → 307 on the merged tree — core-solvers' +4 (`assembly`,
    # `startframe` ×2, `turnaround`) land here too. Re-measured, never summed (SEAM 8 §1 is the worked example).
    # WAVE 16: 307 → 315. This number cannot be measured on one branch, so its composition
    # is written out and the coordinator re-measures at merge (this assertion is RED on the
    # tests branch, which reads 307 — no domain added a raise in `armature_core` here):
    #   +3 core-gates (SEAM 5 §4): `route_gates._unreadable_level` (one raise, called from
    #      three container levels), Gate S's all-`add_noise=disable` andon, and `subject`'s
    #      `float()` coercion re-classed from a bare TypeError/ValueError.
    #   +5 core-solvers (SEAM 11 §1): `aapose.check_convention`'s
    #      `drawing_constant_outside_the_record`, `assembly.gate_no_paid_nodes`'s
    #      `class_with_an_unreadable_measurement_date`, and three in
    #      `turnaround.gate_set_distinct` (the unreadable-plane refusal,
    #      `views_without_pixels`, `adjacent_pair_shapes_differ`).
    # instruments, instruments-measure and builders add ZERO here — every raise they added
    # is in `tools/*.py`, which this walk does not reach (both confirmed it in the inbox).
    # WAVE 18 (core-solvers): 315 -> 333. RE-DERIVED with `==` on this worktree against
    # `git show 6b984dd:<path>` for the same walk, per module, not summed from prose. The
    # base was measured GREEN at 315 here first, so all eighteen are this branch's:
    #   assembly.py      22 -> 23  (+1)  F-47db9eff: `measurement_dated_in_the_future`,
    #                                    the ageing clock's floor.
    #   blender_scene.py  7 -> 13  (+6)  F-25a5ecbf: Gate FRAME's four clauses
    #                                    (`operator_status`, `channel_never_reached_disk`,
    #                                    `channel_is_zero_bytes`, `stale_channel`) plus
    #                                    F-329a9555's two in the `half_fovs` byte-twin.
    #   channels.py       0 -> 3   (+3)  F-476a4ee8: the module had NO refusal of any kind;
    #                                    `depth_extent`'s non-finite clause and
    #                                    `normalize_depth`'s window and pixel clauses.
    #   framing.py       12 -> 15  (+3)  F-329a9555: `half_fovs`' frame-size and
    #                                    camera-number clauses and `ortho_half_spans`' own
    #                                    frame-size clause.
    #   resample.py      10 -> 14  (+4)  F-62774c72: `endpoints_match`' vacuity pair and
    #                                    the two bone-population clauses.
    #   turnaround.py    15 -> 16  (+1)  F-329a9555 sibling: `projection_plan`'s
    #                                    PERSPECTIVE branch refusing the camera numbers it
    #                                    records.
    # Nothing in `tools/*.py` reaches this walk, so sibling domains add zero here.
    # WAVE 18 (core-gates): 315 → 325, measured in the core-gates worktree. +5
    # `route_gates.RouteGate` (the API branch's `unreadable_node`, the walk's
    # `duplicate_subgraph_id`, Gate S's `seed_node_unresolvable`, and the two hosted
    # enum-shift clauses), +4 `donor_gate.DonorGate` (`_readable_landmark_row`), +1
    # `gates.GateSSeedRegistration` (`registry_member_not_an_int`). core-solvers also
    # edits `armature_core` this wave, so the merged tree will read HIGHER — the
    # coordinator re-measures at merge and never sums the branches.
    # WAVE-18 MERGE (coordinator, 2026-09-05): 343 on the MERGED tree, measured by calling `family_raise_count()` on it — never a
    # sum of branches (core-gates froze 325 and core-solvers 333, each branch-local by its own note).
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
    # WAVE 22 (core-solvers, 2026-09-05): 346 -> 348, RE-DERIVED with `==` in this
    # worktree against `e8263a3`, which this census read GREEN at 346 first. BRANCH-LOCAL —
    # five domains move this denominator at once and the coordinator re-measures at the
    # merge. The two are `channels.require_readable_normals`' clauses
    # (`non_finite_geometry_normal`, `zero_length_geometry_normal`), the normal half of the
    # non-finite census wave 18 landed on the depth half only (F-4efe0fad).
    # And 348 -> 353 in the same wave, RE-DERIVED with `==` after each step: +5 in
    # `framing` (F-c6124fe0) — `_bisect`'s `bisect_target_not_finite`, `solve_camera`'s
    # `height_frac` clause, its `end_x_frac`/`target_y_frac` clause, and the two
    # `radius_bounds` clauses. The SOLVER half of F-f0c261c1, whose fix went to one tool's
    # parser while `end_x_frac` and `target_y_frac` were bounded at no parser in the tree.
    # And 353 -> 356: +3 in `turnaround` — `orbit_azimuths`' `sweep_revisits_an_azimuth`
    # (F-99e5de1a) and `gate_set_distinct`'s `non_finite_pair_distance` (F-8cfaefd9) and
    # `views_identical_in_pixels_anywhere` (F-99e5de1a). RE-DERIVED with `==`, branch-local.
    # And 356 -> 357: +1 in `lift_solve` — the twist-datum tripwire (F-d255af87), a guard
    # the algebra bounds that used to fall through to the COLLINEARITY message the test four
    # lines above it had already ruled out. Kept as an andon with its own clause rather than
    # deleted, so a change to the arithmetic above it is loud.
    # And 357 -> 360: +3 in `clipcompare.gradient_split` (F-e15d9de2) — the (H, W, 3)
    # clause and the shape-mismatch clause its sibling `frame_fidelity` twenty lines above
    # already carried, and `empty_gradient_band` for a band that selects no pixel and
    # returned a mean over nothing as the band error.
    assert total == 360, (
        f"{total} family raises in armature_core; this pin asserts 360, RE-DERIVED on the "
        f"wave-22 core-solvers branch. This is the denominator every ratio below is quoted against — "
        f"re-measure it deliberately")


def test_a_refusal_that_carries_no_evidence_at_all_is_counted_in_its_own_category():
    """F-1da3769f. `if verdict == EV_NONE: continue` sat above `examined += 1`, so a raise
    with no evidence argument was not an offender, not unreadable, and not counted.

    This is the shape of F-b01840fc one door over: that finding closed sites the walk
    returned UNRESOLVED on and "never counted", and its correction added an `unreadable`
    list so nothing would leave the census silently. EV_NONE left by the same door, three
    lines earlier.
    """
    _offenders, _examined, _unreadable, no_evidence = evidence_dicts_missing("gate")
    assert no_evidence, (
        "the no-evidence bucket is empty; either every plain refusal now carries a receipt "
        "— in which case delete EVIDENCE_NO_EVIDENCE_ROUTED — or the walk has stopped "
        "classifying")
    new = sorted(set(no_evidence) - EVIDENCE_NO_EVIDENCE_ROUTED)
    assert new == [], {
        "raises no evidence at all and is not routed": new,
        "why it matters": "errors.py:24 is `self.evidence = evidence or {}`, so the halt "
                          "line records a null evidence value and the receipt for a "
                          "refused stage cannot name what refused it",
    }
    # WAVE 14, F-95ac9f17: the CONVERSE direction. Without it a routed entry outlives the
    # site it names and becomes a standing permission slip for that site to regress.
    closed = sorted(EVIDENCE_NO_EVIDENCE_ROUTED - set(no_evidence))
    assert closed == [], {
        "carries a receipt now and is still routed (delete these in the commit that adds "
        "the receipt)": closed,
        "why it matters": "a routed entry that names no live site re-admits that site in "
                          "silence: the ten wave-12 receipts in framing/walk/glb/"
                          "blender_scene could all have been reverted with this test green",
    }
    # The census on the page, pinned `==` (wave 14, rule 4). Re-derive with the command
    # beside EVIDENCE_NO_EVIDENCE_ROUTED.
    # WAVE-14 MERGE (coordinator, 2026-09-04): 40 → 32, measured on the merged tree.
    # WAVE 22 (core-solvers, F-4ce10f2a): 32 -> 31, RE-DERIVED with `==` in this worktree.
    # `turnaround.py:projection_plan` is the entry that left; its two one-argument
    # `TurnaroundPlanRefusal` raises now carry `gate`, `andon`, `clause` and the operand.
    assert len(no_evidence) == 31, sorted(no_evidence)


#: Modules of `armature_core` whose classes this census cannot INSTANTIATE on a rig with no
#: Blender, because importing them imports `bpy`. Named and dated 2026-09-04, and DERIVED —
#: the census below puts every module through `importlib` and files the failures here, so a
#: module that starts needing Blender joins loudly and one that stops leaves. Counting what it
#: cannot judge rather than skipping past it (wave 12, rule 3).
CORE_MODULES_NEEDING_BLENDER = {"blender_scene"}


def _family_classes_defined_in_core():
    """`{module stem: {class names}}` for every `ArmatureError` family class defined under
    `armature_core/`, read off the AST — the population, before the property."""
    family = _armature_error_family(TOOLS_DIR)
    out = {}
    for path in sorted(CORE_DIR.glob("*.py")):
        for node in _ast.walk(_ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, _ast.ClassDef) and node.name in family:
                out.setdefault(path.stem, set()).add(node.name)
    return out


def test_every_family_class_stores_the_evidence_it_is_passed():
    """The other half of the evidence census: the raise site PASSES a dict — does the class
    KEEP it?

    WAVE 14, the seam from instruments-measure (`F-8393e66c`). `stage_render.py:582` raised
    the BASE `ArmatureError(msg, {...})`; the base had no `__init__`, so the second argument
    (WAVE 16: that line is `stage_render.py:597` on the merged tree — instruments-measure
    measured the move with `difflib.SequenceMatcher` against `git show 041027c:` and posted
    it in SEAM 15; it is still :582 in this worktree. The citation names a HISTORICAL site
    either way, which is why it is prose and not an assertion.)
    went to `RuntimeError.args` and `.evidence` did not exist — the halt line printed
    `"evidence": null` for a refusal whose raise site looked, to the AST census above,
    perfectly compliant. A census that reads only the CALL cannot see that, which is why the
    two halves are both needed: `evidence_dicts_missing` judges what is written at the raise,
    and this judges what the class does with it.

    The population is derived from the AST family and reconciled against the classes that are
    actually importable, so a class the walk finds but never instantiates cannot hide here.
    """
    import importlib

    defined = _family_classes_defined_in_core()
    unimportable, live = {}, {}
    for stem, names in sorted(defined.items()):
        try:
            mod = importlib.import_module(f"armature_core.{stem}")
        except Exception as exc:                                        # noqa: BLE001
            unimportable[stem] = f"{type(exc).__name__}: {exc}"
            continue
        for name in sorted(names):
            live[f"{stem}.{name}"] = getattr(mod, name)

    assert set(unimportable) == CORE_MODULES_NEEDING_BLENDER, {
        "cannot be imported without Blender and is not named": unimportable,
        "named and importable now (delete it)":
            sorted(CORE_MODULES_NEEDING_BLENDER - set(unimportable))}
    expected = {f"{stem}.{n}" for stem, names in defined.items()
                for n in names if stem not in unimportable}
    assert set(live) == expected, {
        "defined by the walk and not reached live": sorted(expected - set(live)),
        "reached live and not defined by the walk": sorted(set(live) - expected)}
    assert live, "the census instantiated nothing; it is not measuring the family"

    sentinel = {"measured": 1, "threshold": 2}
    dropped = {}
    for qualified, cls in sorted(live.items()):
        try:
            exc = cls("a refusal", sentinel)
        except Exception as err:                                        # noqa: BLE001
            dropped[qualified] = f"cannot take (message, evidence): {type(err).__name__}"
            continue
        got = getattr(exc, "evidence", None)
        if got != sentinel:
            dropped[qualified] = repr(got)
    assert dropped == {}, {
        "raised with an evidence dict and does not store it": dropped,
        "why it matters": "the halt handler records `getattr(exc, 'evidence', None)`, so a "
                          "class that drops the argument prints `\"evidence\": null` for a "
                          "refusal whose raise site the AST census scores compliant",
    }


# ------------------------------------- the census, TREE-WIDE (wave 16, rule 5, F-9aa7974e)
#
# `_family_classes_defined_in_core()` iterates `CORE_DIR.glob("*.py")` only. Measured in this
# worktree: `_armature_error_family(TOOLS_DIR)` yields 120 NAMES and `tools/**` holds 125
# class DEFINITIONS of them across 71 modules (three names are defined twice —
# `DetectionGate`, `PayloadError`, `RenderGate`). The core-only walk reached 51 of them and
# 0 of the 74 definitions outside `armature_core/`, which are precisely the classes whose
# halt lines the 21-tool contract prints. `tests/test_amend_w14_merge.py`'s own docstring
# says "the evidence census walks `armature_core` only, so the suite was green" about
# exactly this hole, and closed that one instance by hand-writing three tests for one class
# in one tool.
#
# THE CONTRACT (core-gates, SEAM 1, wave 16 rule 5), three clauses, one exemption:
#   1. `E("m").evidence is None` — a bare message carries NO receipt. `"evidence": null`.
#   2. `E("m", d).evidence is d` — IDENTITY, not equality. No `or {}`, no `dict(evidence)`.
#   3. `GateFailure` and its whole subtree keep `evidence or {}`, because a gate builds `ev`
#      as it measures and its clauses index into it. It is the ONLY `__init__` in the family
#      allowed to normalise, and its subclasses define none of their own.

#: Family classes under `tools/**` the tree-wide walk cannot INSTANTIATE. Named and dated
#: 2026-09-04 (wave 16), and DERIVED — the walk files every failure here rather than letting
#: it fall out silently, which is the half of `F-9aa7974e` that is about the population and
#: not about the property. EMPTY today: all 125 definitions import under
#: `blender_stub.blender_stubbed()`, the Blender-side ones included.
TREE_WIDE_UNIMPORTABLE = {}


def _family_classes_defined_under(root):
    """`{module path relative to `root`: {class names}}` for every family class under it."""
    family = _armature_error_family(TOOLS_DIR)
    out = {}
    for path in sorted(_pathlib.Path(root).rglob("*.py")):
        if "superseded" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            tree = _ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:                                             # pragma: no cover
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ClassDef) and node.name in family:
                rel = path.relative_to(root).as_posix()
                out.setdefault(rel, set()).add(node.name)
    return out


def _live_family_classes(root=None):
    """`({"<rel>::<Class>": class}, {failure: why})` — every importable member of the family.

    Imported inside ONE `blender_stubbed()` block, whose teardown pops every module first
    imported under the stub out of `sys.modules` AND off the `armature_core` package's
    attributes. The class OBJECTS survive by strong reference (the same arrangement
    `conftest._STUB_IMPORTED` uses), so the census reads real classes without leaving a
    stub-bound module behind for `tests/test_cli.py::_probe` to read as `ok`.
    """
    import importlib
    import importlib.util

    from blender_stub import blender_stubbed

    root = TOOLS_DIR if root is None else _pathlib.Path(root)
    defined = _family_classes_defined_under(root)
    live, failed = {}, {}
    with blender_stubbed():
        for rel, names in sorted(defined.items()):
            path = root / rel
            dotted = rel[:-3].replace("/", ".")
            try:
                if root == TOOLS_DIR:
                    mod = importlib.import_module(dotted)
                else:
                    spec = importlib.util.spec_from_file_location(
                        "_family_census_" + dotted.replace(".", "_"), path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
            except Exception as exc:                                    # noqa: BLE001
                failed[rel] = f"{type(exc).__name__}: {exc}"
                continue
            for name in sorted(names):
                obj = getattr(mod, name, None)
                if obj is None:
                    failed[f"{rel}::{name}"] = "not an attribute of the imported module"
                else:
                    live[f"{rel}::{name}"] = obj
    return live, failed


def test_the_evidence_census_walks_the_whole_tree_and_not_one_directory():
    """The POPULATION half of F-9aa7974e (wave-16 rule 1).

    The walk must reach every family class DEFINED under `tools/**`, and the ones it cannot
    instantiate must be named in a dated table rather than dropping out. Pinned `==` on the
    derivation itself, not on a count a sibling domain can move: a class added anywhere
    under `tools/` joins on the day it lands.
    """
    defined = _family_classes_defined_under(TOOLS_DIR)
    live, failed = _live_family_classes()

    assert failed == TREE_WIDE_UNIMPORTABLE, {
        "cannot be instantiated and is not named": {
            k: v for k, v in failed.items() if k not in TREE_WIDE_UNIMPORTABLE},
        "named as unimportable and imports now (delete the entry)":
            sorted(set(TREE_WIDE_UNIMPORTABLE) - set(failed))}
    expected = {f"{rel}::{n}" for rel, names in defined.items() for n in names
                if rel not in failed and f"{rel}::{n}" not in failed}
    assert set(live) == expected, {
        "defined by the walk and never instantiated": sorted(expected - set(live)),
        "instantiated and not defined by the walk": sorted(set(live) - expected)}

    # The old walk is a strict SUBSET, and the gap is the thing the finding is about.
    core_only = {f"armature_core/{stem}.py::{n}"
                 for stem, names in _family_classes_defined_in_core().items()
                 for n in names}
    assert core_only < set(live), sorted(core_only - set(live))
    assert len(live) > 2 * len(core_only), (
        f"the tree-wide walk reached {len(live)} of the family and the core-only walk "
        f"reached {len(core_only)}; if these are close the widening did not happen")


def test_every_family_class_tree_wide_keeps_the_dict_it_was_handed():
    """Clause 2 of the contract, over all 125 — and by IDENTITY, not by equality.

    `E("m", d).evidence is d`: the dict the raising line built is the dict the halt handler
    reads. `dict(evidence)` and `evidence or {}` both satisfy equality and both break the
    contract, which is why this asserts `is`.
    """
    live, _failed = _live_family_classes()
    assert live, "the census instantiated nothing; it is not measuring the family"
    sentinel = {"measured": 1, "threshold": 2}
    dropped = {}
    for qualified, cls in sorted(live.items()):
        try:
            got = cls("a refusal", sentinel).evidence
        except Exception as err:                                        # noqa: BLE001
            dropped[qualified] = f"cannot take (message, evidence): {type(err).__name__}"
            continue
        if got is not sentinel:
            dropped[qualified] = (
                "a COPY" if got == sentinel else repr(got))
    assert dropped == {}, {
        "handed an evidence dict and does not store THAT dict": dropped,
        "why it matters": "the halt handler records `getattr(exc, 'evidence', None)`; a "
                          "class that copies or replaces it publishes a receipt the raising "
                          "line never wrote",
    }


def test_no_family_class_outside_the_gate_failure_subtree_normalises_a_bare_message():
    """Clauses 1 and 3, and rule 5's structural half — over the whole tree.

    A plain refusal carrying no receipt must record `"evidence": null`, and a gate that
    measured nothing must record `{}`. Those are the two things wave 14's base constructor
    was landed to separate, and reading one as the other is unrecoverable from the halt
    record. `GateFailure` and its subtree are the ONE exemption, and the structural form of
    that is: outside the subtree, no class defines an `__init__` at all — inheritance
    already gives it the two-argument shape.

    RED ON THIS BRANCH by construction and expected green on the merged tree. Measured here
    on `041027c`: 45 non-`GateFailure` members return `{}` for a bare message, 44 of them
    defining their own normalising `__init__` and two more
    (`measure_tracking.TrackingError`, `.AnchorMismatch`) inheriting one from
    `_CarriesEvidence`. Rule 5 deletes all of them this wave — core-solvers 10
    (`armature_core`, SEAM 4), instruments-measure 27 plus the `_CarriesEvidence` class
    (SEAM 5), builders 4 `PayloadError`s (SEAM 10), instruments 1
    (`rig_character.SiteListInvalid`, SEAM 6). `ArmatureError`'s own `__init__` stays: it is
    the contract, and it does not normalise.
    """
    from armature_core.errors import ArmatureError, GateFailure

    live, _failed = _live_family_classes()
    normalising, own_init = {}, []
    for qualified, cls in sorted(live.items()):
        gate = issubclass(cls, GateFailure)
        bare = cls("a refusal").evidence
        if gate:
            assert bare == {}, (qualified, bare)
        elif bare is not None:
            normalising[qualified] = repr(bare)
        if "__init__" in vars(cls) and not gate and cls is not ArmatureError:
            own_init.append(qualified)

    assert normalising == {}, {
        "a plain refusal that invents an empty receipt": normalising,
        "why it matters": 'a reader takes `"evidence": {}` in a halt record as "a gate '
                          'measured nothing and printed an empty receipt" when it is in '
                          'fact "a plain refusal that carried no receipt at all"',
    }
    assert own_init == [], (
        "these define their own `__init__` outside the `GateFailure` subtree; inheritance "
        f"already gives them the two-argument shape and any override can only drift: "
        f"{own_init}")


def test_the_tree_wide_census_goes_red_on_a_tools_side_class_the_core_walk_cannot_see():
    """RED on a member OUTSIDE the old walk (wave-16 rule 2), which is the whole finding.

    A synthetic `tools/`-shaped root holds one class with a normalising `__init__` — the
    `stage_render:582` shape, one directory out from `armature_core/`. The tree-wide walk
    must find it and report it; the core-only walk, reconstructed here, must not see it at
    all. If both saw it the comparison would be with itself.
    """
    from armature_core.errors import ArmatureError

    root = _pathlib.Path(__import__("tempfile").mkdtemp())
    (root / "armature_core").mkdir()
    (root / "armature_core" / "errors.py").write_text(
        "class ArmatureError(RuntimeError):\n"
        "    def __init__(self, message, evidence=None):\n"
        "        super().__init__(message)\n"
        "        self.evidence = evidence\n", encoding="utf-8")
    (root / "make_synthetic_sheet.py").write_text(
        "from armature_core.errors import ArmatureError\n"
        "class SheetPopulationError(ArmatureError):\n"
        "    def __init__(self, message, evidence=None):\n"
        "        super().__init__(message)\n"
        "        self.evidence = evidence or {}\n", encoding="utf-8")

    defined = _family_classes_defined_under(root)
    assert "make_synthetic_sheet.py" in defined, sorted(defined)
    live, failed = _live_family_classes(root)
    assert failed == {}, failed
    cls = live["make_synthetic_sheet.py::SheetPopulationError"]
    assert cls("m").evidence == {}, "the probe class does not carry the defect"
    assert "__init__" in vars(cls)

    # the CORE-ONLY walk, reconstructed: it globs one directory and cannot reach a tool.
    core_only = sorted(p.name for p in (root / "armature_core").glob("*.py"))
    assert core_only == ["errors.py"], core_only
    assert not any(p.name == "make_synthetic_sheet.py"
                   for p in (root / "armature_core").glob("*.py"))
    # and the real base is the honest one, or the probe proves nothing about normalising
    assert ArmatureError("m").evidence is None


def test_the_evidence_a_family_class_stores_is_the_object_the_halt_line_reads():
    """Rule 3 on the census above, on the shape it exists to catch.

    A class that takes `(message, evidence)` and throws the second argument away is exactly
    `ArmatureError` before wave 14, and it must be reported — otherwise the test is asserting
    a property of `GateFailure` and calling it a property of the family.
    """
    from armature_core.errors import ArmatureError

    class _Drops(ArmatureError):
        def __init__(self, message, evidence=None):
            RuntimeError.__init__(self, message)

    sentinel = {"measured": 1}
    exc = _Drops("a refusal", sentinel)
    assert getattr(exc, "evidence", None) != sentinel, (
        "the probe class stored the evidence anyway; it does not carry the defect and the "
        "comparison below says nothing")
    with pytest.raises(AssertionError):
        assert getattr(exc, "evidence", None) == sentinel

    # …and the real base, which is the operand the seam named.
    assert ArmatureError("a refusal", sentinel).evidence == sentinel, (
        "the base class drops the evidence dict its callers pass; a bare "
        "`ArmatureError(msg, {...})` raise prints `\"evidence\": null` in the halt line")


def test_the_no_evidence_sites_are_plain_refusals_and_not_gates_that_lost_their_receipt():
    """The claim that makes the ceiling above defensible, measured rather than asserted.

    If any of the 50 were a `GateFailure`, this would be a live defect in the gate receipt
    rather than an unfinished half of the wave-10 plain-refusal contract.
    """
    andons = {c.split(".", 1)[1] for c in package_andons()}
    _o, _e, _u, gate_class_none = evidence_dicts_missing("gate", classes=andons)
    assert gate_class_none == [], (
        "a GateFailure subclass raises with no evidence argument at all; its halt line "
        "records `evidence: null` and the andon cannot name what fired it")


def test_no_new_gate_raises_evidence_that_cannot_name_its_own_andon():
    """The census, per SITE. A ratchet: the 31 sites the widened walk found on 2026-09-04
    are written down above with the domain that owns each, and a 32nd fails here."""
    offenders, _, unreadable, _none = evidence_dicts_missing("gate")
    assert set(offenders) == EVIDENCE_WITHOUT_GATE_ID_ROUTED, {
        "regressed (omit their own gate id)":
            sorted(set(offenders) - EVIDENCE_WITHOUT_GATE_ID_ROUTED),
        "closed but still listed (delete these in the commit that closed them)":
            sorted(EVIDENCE_WITHOUT_GATE_ID_ROUTED - set(offenders)),
    }
    assert set(unreadable) == EVIDENCE_UNREADABLE_EXEMPT, {
        "the walk cannot decide these":
            sorted(set(unreadable) - EVIDENCE_UNREADABLE_EXEMPT),
        "no longer unreadable":
            sorted(EVIDENCE_UNREADABLE_EXEMPT - set(unreadable)),
    }
    assert EVIDENCE_UNREADABLE_EXEMPT <= set(unreadable) | EVIDENCE_UNREADABLE_EXEMPT


def test_the_census_calls_its_own_shipped_walk_on_a_tree_whose_answers_are_known(tmp_path):
    """The red direction, done properly: `evidence_dicts_missing` is CALLED on a synthetic
    package rather than re-implemented beside itself.

    Four raises, one per shape the real package uses, and one control. The inline form is
    the one the old walk could not see at all, and `G1Legality` is a class whose name
    carries no "Gate" substring — the filter that hid four andons for a whole wave.
    """
    pkg = tmp_path / "armature_core"
    pkg.mkdir()
    (pkg / "errors.py").write_text(
        "class ArmatureError(Exception):\n    pass\n\n"
        "class SomeGate(ArmatureError):\n    pass\n\n"
        "class G1Legality(ArmatureError):\n    pass\n", encoding="utf-8")
    (pkg / "shapes.py").write_text(
        "def assigned_then_raised(a):\n"
        "    ev = {'n': len(a)}\n"
        "    raise SomeGate('bad', ev)\n\n"
        "def inline(a):\n"
        "    raise SomeGate('bad', {'n': len(a)})\n\n"
        "def by_keyword(a):\n"
        "    raise G1Legality('bad', evidence={'n': len(a)})\n\n"
        "def carries_its_id(a):\n"
        "    raise SomeGate('bad', {'gate': 'X', 'n': len(a)})\n\n"
        # WAVE 12, F-1da3769f — the FIFTH shape: no evidence argument at all. 102 of the
        # package's 270 family raises look like this, and the walk `continue`d past every
        # one of them before counting it.
        "def no_evidence_at_all(a):\n"
        "    raise SomeGate('bad')\n", encoding="utf-8")

    offenders, examined, unreadable, no_evidence = evidence_dicts_missing("gate", root=pkg)
    assert examined == 5, (examined, offenders, no_evidence)
    assert offenders == [
        "shapes.py:assigned_then_raised (SomeGate)",
        "shapes.py:by_keyword (G1Legality)",
        "shapes.py:inline (SomeGate)",
    ], offenders
    assert unreadable == [], unreadable
    assert no_evidence == ["shapes.py:no_evidence_at_all (SomeGate)"], no_evidence
    # the denominator is derived beside the census and must agree with it
    assert family_raise_count(root=pkg) == examined

    #: and the same tree with every id present reports nothing — a census that named a
    #: site unconditionally would be no better than one that named none.
    (pkg / "shapes.py").write_text(
        "def inline(a):\n"
        "    raise SomeGate('bad', {'gate': 'X', 'n': len(a)})\n", encoding="utf-8")
    assert evidence_dicts_missing("gate", root=pkg) == ([], 1, [], [])


def test_every_shared_gate_id_is_disambiguated_by_the_evidence_in_this_domain():
    """`SHARED_GATE_IDS` records that two ids are carried by two andons each. The receipt
    line cannot tell them apart, so the evidence must: each core-solvers gate on a shared
    id names its own class under "andon"."""
    from armature_core import parts, turnaround as TA

    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism({}, {}, 1.0)
    assert exc.value.gate == "D" and exc.value.evidence["andon"] == "GatePartsDeterminism"

    with pytest.raises(TA.TurnaroundAlphaGate) as exc:
        TA.gate_view_alpha(0, 255, 255, 0.0)
    assert exc.value.gate == "ALPHA"
    assert exc.value.evidence["andon"] == "TurnaroundAlphaGate"


# --- W6 amend: completeness over zero channels (F-2bf70017) ---------------------------


@pytest.mark.parametrize("expected", [{}, dict()])
def test_g2_refuses_an_empty_channel_expectation(tmp_path, expected):
    """The loop iterates `expected`, so an empty mapping walked no channels and the gate
    returned {} — a PASS having examined nothing, with no statement anywhere that nothing
    was examined. Measured 2026-09-03: g2_completeness(<empty tmpdir>, {}, 33) returned
    {}. This gate runs immediately before the manifest that makes a run look finished."""
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), expected, 33)
    assert_gate(exc, "G2", expected_channels=[], frame_count=33)
    assert "ZERO channels" in str(exc.value)


def test_g2_still_passes_on_a_populated_expectation(tmp_path):
    """The direction the andon must not break."""
    names = [f"{i:05d}.png" for i in range(3)]
    d = tmp_path / "mask"
    d.mkdir()
    for n in names:
        (d / n).write_bytes(b"x")
    assert gates.g2_completeness(str(tmp_path), {"mask": names}, 3)["mask"]["present"] == 3


# --- W6 amend: a receipt names its own andon unambiguously (core-solvers seam) --------


def _named_evidence_assignments(root=None):
    """`(module, lineno, function, missing keys)` for every `ev`/`evidence = {...}`.

    The same predicate the wave-6 test used, over EVERY module in `armature_core` rather
    than the typed two-module tuple `(gates, rig_gates)` it was written against. Widening
    it was F-99e15391's third direction: measured 2026-09-04, the same predicate turns 17
    dicts red the moment it is allowed to look outside those two files.
    """
    root = CORE_DIR if root is None else _pathlib.Path(root)
    out = []
    for path in sorted(root.glob("*.py")):
        tree = _ast.parse(path.read_text(encoding="utf-8"))
        for fn in [n for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef)]:
            for node in _ast.walk(fn):
                if (isinstance(node, _ast.Assign)
                        and getattr(node.targets[0], "id", None) in ("ev", "evidence")
                        and isinstance(node.value, _ast.Dict)):
                    keys = {k.value for k in node.value.keys
                            if isinstance(k, _ast.Constant)}
                    missing = [k for k in ("gate", "andon") if k not in keys]
                    if missing:
                        out.append((path.name, node.lineno, fn.name, missing))
    return out


def test_every_named_evidence_dict_in_the_core_names_its_gate_and_its_andon():
    """`stage_render.py` records the gate id beside the evidence dict in one
    `STAGE_RENDER_HALT <json>` line (CORRECTED wave 14: `GATE_FAILURE` / `GATE_EVIDENCE`
    were deleted with the old handler), so a
    receipt whose `ev["gate"]` is absent — or whose `ev["andon"]` is, on an id two andon
    families share — cannot be read back to the andon that produced it. Shared ids stay
    shared: the three Gate P clauses all report "P". The requirement is agreement, not
    uniqueness.

    NO exemption set. The 17 sites this turns red on 2026-09-04 belong to the core-gates
    and core-solvers domains, which are closing them in this same wave (`route_gates`
    evidence carries gate+andon everywhere; `andon` on all 20 dicts in the solvers'
    modules). Until both land, this test is red on this branch by their sites, not by a
    defect in the census.
    """
    offenders = _named_evidence_assignments()
    assert offenders == [], (
        "these evidence dicts cannot name the andon that produced them:\n  "
        + "\n  ".join(f"{m}:{ln} {fn} missing {'+'.join(miss)}"
                      for m, ln, fn, miss in offenders))


def test_that_census_can_see_a_dict_that_forgot_its_andon(tmp_path):
    """The red direction for the widened predicate, called rather than re-implemented."""
    pkg = tmp_path / "armature_core"
    pkg.mkdir()
    (pkg / "one.py").write_text(
        "def gate_a(n):\n"
        "    ev = {'gate': 'A', 'n': n}\n"
        "    raise SomeGate('bad', ev)\n\n"
        "def gate_b(n):\n"
        "    ev = {'gate': 'B', 'andon': 'SomeGate', 'n': n}\n"
        "    raise SomeGate('bad', ev)\n", encoding="utf-8")
    assert _named_evidence_assignments(pkg) == [("one.py", 2, "gate_a", ["andon"])]


@pytest.mark.parametrize("gate_id,call", [
    ("G4", lambda: gates.g4_bbox_sanity(0, (10, 10), (10, 10, 500, 500), 832, 480)),
    ("R", lambda: gates.gate_r_round_trip([1], [1, 2])),
    ("B", lambda: gates.gate_b_batching(1, True)),
])
def test_a_raised_gates_evidence_agrees_with_the_class_it_was_raised_from(gate_id, call):
    with pytest.raises(GateFailure) as exc:
        call()
    assert exc.value.gate == gate_id
    if "gate" in exc.value.evidence:
        assert exc.value.evidence["gate"] == gate_id
