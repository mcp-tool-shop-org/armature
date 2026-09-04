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


# --------------------------------------- the receipt's id lives in the evidence too

#: Modules whose gate-function evidence dicts omit the `gate` key. EMPTY, as of the
#: wave-6 amend: ten sites were measured 2026-09-04 (F-f2f42e4a), four in core-solvers
#: (`parts.py` x3, `glb.py`) fixed with this test, and the rest in `gates.py` and
#: `rig_gates.py` fixed on the core-gates branch (commit b4b49f1, seven sites - the six
#: this census found plus `g6_subject_motion`, which their own AST sweep added).
#:
#: `stage_render.py:509` prints `GATE_FAILURE <exc.gate>` and `GATE_EVIDENCE <json of
#: exc.evidence>` as two lines, so a reader holding only the JSON has no id at all - and
#: ids are shared across andon families ("D" by GateDDeterminism and GatePartsDeterminism,
#: "ALPHA" by AlphaGate and TurnaroundAlphaGate), so the prose is not enough either.
#:
#: SUBSET assertion: the set can only shrink. Until the core-gates branch is merged this
#: test is RED on the core-solvers branch alone, by two modules that branch owns - the
#: coordinated-pair artifact the wave brief names, not a defect in either half.
EVIDENCE_WITHOUT_GATE_ID_ROUTED = set()


def _evidence_dicts_missing_the_gate_key():
    """Every `ev = {...}` / `evidence = {...}` literal inside a gate-raising function in
    `armature_core` that does not name its own gate id."""
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "tools" / "armature_core"
    out = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in [n for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            raised = {getattr(r.exc.func, "id", getattr(r.exc.func, "attr", ""))
                      for r in ast.walk(fn)
                      if isinstance(r, ast.Raise) and isinstance(r.exc, ast.Call)}
            if not any("Gate" in name for name in raised):
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)):
                    continue
                target = node.targets[0]
                if not (isinstance(target, ast.Name) and target.id in ("ev", "evidence")):
                    continue
                keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
                if "gate" not in keys:
                    out.append(f"{path.name}:{node.lineno} {fn.name}")
    return out


def test_no_core_solvers_gate_raises_evidence_that_cannot_name_its_own_andon():
    """The census, not the instance. Measured 2026-09-04 before the fix: ten sites across
    four modules, of which `glb.gate_atlas_untouched` and all three of `parts.py`'s gates
    were in this domain."""
    offenders = _evidence_dicts_missing_the_gate_key()
    modules = {o.split(":", 1)[0] for o in offenders}
    assert modules <= EVIDENCE_WITHOUT_GATE_ID_ROUTED, (
        f"a gate evidence dict outside the routed modules omits its own id: {offenders}; "
        f"routed and expected to shrink, never to grow: "
        f"{sorted(EVIDENCE_WITHOUT_GATE_ID_ROUTED)}")
    for module in ("parts.py", "glb.py", "assembly.py", "turnaround.py", "startframe.py",
                   "resample.py", "lift_solve.py"):
        assert module not in modules, f"{module} regressed: {offenders}"


def test_the_census_would_catch_an_evidence_dict_that_forgot_its_id():
    """The red direction: the scan must actually see a dict literal that omits the key,
    or the assertion above is a check that cannot fail."""
    import ast

    src = (
        "def gate_x(a):\n"
        "    ev = {'n': len(a)}\n"
        "    raise SomeGate('bad', ev)\n"
    )
    tree = ast.parse(src)
    fn = tree.body[0]
    raised = {r.exc.func.id for r in ast.walk(fn)
              if isinstance(r, ast.Raise) and isinstance(r.exc, ast.Call)}
    assert any("Gate" in name for name in raised)
    dicts = [n for n in ast.walk(fn)
             if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)]
    assert dicts and "gate" not in [k.value for k in dicts[0].value.keys]


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


def test_every_gate_in_gates_and_rig_gates_carries_its_own_id_in_its_evidence():
    """The census core-solvers' `EVIDENCE_WITHOUT_GATE_ID_ROUTED` was waiting on.
    `stage_render.py` prints `GATE_FAILURE <exc.gate>` beside the evidence dict, so a
    receipt whose `ev["gate"]` is absent (or disagrees with the raising class's `.gate`)
    cannot be read back to the andon that produced it. Shared ids stay shared — the three
    Gate P clauses all report "P" — the requirement is agreement, not uniqueness."""
    import ast
    import inspect

    from armature_core import rig_gates

    for module in (gates, rig_gates):
        tree = ast.parse(inspect.getsource(module))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(fn):
                if (isinstance(node, ast.Assign)
                        and getattr(node.targets[0], "id", None) == "ev"
                        and isinstance(node.value, ast.Dict)):
                    keys = [k.value for k in node.value.keys
                            if isinstance(k, ast.Constant)]
                    assert "gate" in keys, (
                        f"{module.__name__}.{fn.name} builds an evidence dict with no "
                        f"'gate' key; the receipt cannot name its own andon")
                    assert "andon" in keys, (
                        f"{module.__name__}.{fn.name}'s evidence names no raising class")


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
