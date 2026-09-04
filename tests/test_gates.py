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
    with pytest.raises(G1GeneratorLegality):
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
        with pytest.raises(G1GeneratorLegality):
            gates.g1_generator_legality(512, 768, count, "wan-vace")


def test_g1_red_on_unknown_generator():
    """The andon is on the direction the invariant does not bound: an unknown
    generator is the case where *nothing* would be checked."""
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(512, 768, 33, "some-model-nobody-filed")
    assert "unknown generator profile" in str(exc.value)
    assert_gate(exc, "G1", generator="some-model-nobody-filed", known=...)


def test_g1_red_on_bool_masquerading_as_int():
    with pytest.raises(G1GeneratorLegality):
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
    with pytest.raises(G2Completeness):
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
    with pytest.raises(G4BboxSanity):
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
    from armature_core import openpose

    with pytest.raises(G5ConventionConformance):
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
            with pytest.raises(G1GeneratorLegality):
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
    with pytest.raises(AssertionError, match="with gate 'G1'"):
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
