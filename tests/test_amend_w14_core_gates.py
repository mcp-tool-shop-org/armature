"""Wave 14 (core-gates): the guards land on the OPERAND, not beside it.

Wave 12 gave this package a non-finite family, an `unreadable_node` andon and a
CONDITIONAL licence tier. Wave 13's auditors measured that every one of them landed one
operand, one level or one direction away from the defect it was written for:

  * `require_finite` sat on every THRESHOLD (`bbox_diagonal`, four times) and on none of
    the MEASURED quantities — so a NaN observation walked past all three rig andons and
    landed on the verdict line as agreement, with the receipt recording a delta of 0.0;
  * `unreadable_node` closed the top-level `nodes` array and not the recursion its own
    comment calls "the clause, not the loop";
  * the CONDITIONAL tier read `hits[0]`, so a merged filename that also matched a waivable
    EXCLUDED row lost its credit obligation entirely;
  * `verify` checked that every conditional component is credited and never the converse,
    while copying the unmatched credits into the record a builder publishes.

Every test here goes RED on the tree at base `4d21bec`; the red measurement is quoted on
each one, and each fixture exercises the guard rather than its neighbour — the threshold
is finite wherever a measurement is the NaN, and the bad node is one level DOWN.
"""

import math
import os
import sys

import numpy as np
import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from armature_core import gates, rig_gates, shotspec, subject  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, G4BboxSanity, GateDDeterminism, GatePRestPose, GateSSeedRegistration,
    SpecError, SubjectExtentError,
)

NAN = float("nan")
INF = float("inf")

# The threshold stays FINITE in every fixture below: the wave-12 guard already refuses a
# non-finite one, so a fixture that moved the NaN into the diagonal would prove the
# neighbouring clause and not this one.
FINITE_DIAGONAL = 1.0


# ====================================================================== F-13a144c2 · the
# NaN family, on the MEASURED quantity. Wave 12 guarded `bbox_diagonal` at :144, :242,
# :362 and :469 and left every comparison operand unchecked.


def _verts(nan_at=None):
    a = np.zeros((4, 3), dtype=np.float64)
    b = np.zeros((4, 3), dtype=np.float64)
    if nan_at is not None:
        b[nan_at] = [NAN, 0.0, 0.0]
    return a, b


def test_gate_p_rest_pose_refuses_a_non_finite_displacement():
    """RED on base: measured in this worktree, `gate_p_rest_pose(a, b, 1.0)` with ONE
    vertex NaN in the bound array returned `verdict: 'rest pose preserved'` with
    `max_displacement: nan` — `d[i] > threshold` is False for a NaN, so the andon that
    exists to catch a silent collapse certified the collapse."""
    a, b = _verts(nan_at=2)
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_rest_pose(a, b, FINITE_DIAGONAL)
    ev = exc.value.evidence
    assert ev["displacement_non_finite"] == {"first_index": 2, "n_non_finite": 1,
                                             "population": 4}
    assert math.isnan(ev["displacement[2]"])
    assert ev.get("verdict") != "rest pose preserved"
    # the guard fired on the MEASUREMENT, so the threshold was readable all along
    assert ev["bbox_diagonal"] == FINITE_DIAGONAL


def test_gate_p_liveness_refuses_a_non_finite_displacement():
    """RED on base: the same input returned `'the deform is live; Gate P's rest-pose
    reading is about a bound mesh'` — `d.max() <= threshold` is False for a NaN, so a
    probe that measured nothing reported that the deform was live."""
    a, b = _verts(nan_at=1)
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_evaluation_is_live(a, b, FINITE_DIAGONAL)
    assert exc.value.evidence["displacement_non_finite"]["first_index"] == 1
    assert "the deform is live" not in str(exc.value)


def _fingerprints(tail_b=(0.0, 1.0, 0.0), roll_b=0.0, w_b=(0.0, 1.0)):
    a = rig_gates.rig_fingerprint(
        {"b": {"head": (0.0, 0.0, 0.0), "tail": (0.0, 1.0, 0.0), "roll": 0.0,
               "parent": None}},
        {"g": [0.0, 1.0]}, 2)
    b = rig_gates.rig_fingerprint(
        {"b": {"head": (0.0, 0.0, 0.0), "tail": tail_b, "roll": roll_b, "parent": None}},
        {"g": list(w_b)}, 2)
    return a, b


AGREEMENT = "two builds agree on bones"


@pytest.mark.parametrize("kwargs,operand", [
    ({"tail_b": (NAN, NAN, NAN)}, "b.tail_delta"),
    ({"roll_b": NAN}, "b.roll_delta"),
    ({"w_b": (NAN, 1.0)}, "weight_delta[g][0]"),
])
def test_gate_d_refuses_a_non_finite_measurement(kwargs, operand):
    """RED on base, all three: measured in this worktree with a FINITE diagonal,
    `gate_d_determinism` returned an agreement verdict for a bone whose tail is
    `[nan,nan,nan]` in the second build, with `worst_bone_delta` reading
    `{'bone': None, 'quantity': None, 'delta': 0.0}`; the same for a NaN roll; and
    `worst_weight_delta` reading `{'group': None, 'max_abs': 0.0}` for weights
    `[0.0,1.0]` vs `[nan,1.0]`. `d > worst['delta']` and `d > tol` are BOTH False for a
    NaN, so the receipt recorded a zero difference between two rigs that differ."""
    a, b = _fingerprints(**kwargs)
    with pytest.raises(GateDDeterminism) as exc:
        rig_gates.gate_d_determinism(a, b, FINITE_DIAGONAL)
    ev = exc.value.evidence
    assert operand in ev and math.isnan(ev[operand])
    assert AGREEMENT not in str(exc.value)
    assert ev["bbox_diagonal"] == FINITE_DIAGONAL


def test_a_finite_difference_still_reaches_the_ordinary_refusal():
    """The guard must not become the only way this gate speaks: a real 4.0 tail move is
    still the determinism complaint it always was, worded from `problems`."""
    a, b = _fingerprints(tail_b=(0.0, 5.0, 0.0))
    with pytest.raises(GateDDeterminism, match=r"produced different rigs"):
        rig_gates.gate_d_determinism(a, b, FINITE_DIAGONAL)


def test_the_measurement_guard_uses_the_one_non_finite_helper():
    """Wave 12's rule 5, carried to the measurements: one NaN family, one helper. The
    page may not grow a second spelling of `isfinite` in the stdlib's namespace."""
    from armature_core import parts
    assert rig_gates.require_finite is parts.require_finite
    src = open(rig_gates.__file__, encoding="utf-8").read()
    assert "math.isfinite" not in src.replace("second `math.isfinite`", "")


# ====================================================================== F-8a5683e0 · the
# evidence dict was built BEFORE the refusal that exists to catch a bad diagonal.


@pytest.mark.parametrize("bad", [None, "x", True])
@pytest.mark.parametrize("clause", ["rest", "roundtrip", "live", "determinism"])
def test_a_non_numeric_diagonal_is_a_family_refusal_not_a_stdlib_crash(clause, bad):
    """RED on base: measured in this worktree, `gate_p_rest_pose(a, a, None)` raised
    `TypeError: float() argument must be a string or a real number, not 'NoneType'` and
    `gate_p_rest_pose(a, a, 'x')` raised `ValueError: could not convert string to float`,
    from the `float(bbox_diagonal)` in the evidence dict three lines above the
    `require_finite` call that exists to refuse exactly this. Neither is an
    `ArmatureError`, so `rig_character`'s halt handler classified it an unhandled crash
    with no receipt at all on its six-key `RIG_CHARACTER_HALT` line."""
    a = np.zeros((4, 3), dtype=np.float64)
    if clause == "determinism":
        fa, fb = _fingerprints()
        call, cls = (lambda: rig_gates.gate_d_determinism(fa, fb, bad)), GateDDeterminism
    elif clause == "rest":
        call, cls = (lambda: rig_gates.gate_p_rest_pose(a, a, bad)), GatePRestPose
    elif clause == "roundtrip":
        call, cls = (lambda: rig_gates.gate_p_round_trip_positions(a, a, bad)), GatePRestPose
    else:
        call, cls = (lambda: rig_gates.gate_p_evaluation_is_live(a, a + 0.5, bad)), GatePRestPose
    with pytest.raises(cls) as exc:
        call()
    assert isinstance(exc.value, ArmatureError)
    assert exc.value.evidence["bbox_diagonal"] == repr(bad)


def test_a_numpy_scalar_diagonal_is_still_a_number():
    """The direction the new clause must not break: `np.linalg.norm` hands back a numpy
    scalar, and a caller that forgets the `float()` is not passing a malformed value."""
    a = np.zeros((4, 3), dtype=np.float64)
    assert rig_gates.gate_p_rest_pose(a, a, np.float32(2.0))["verdict"] == "rest pose preserved"


# ====================================================================== F-38e783c0 · G4's
# four numbers were checked for TYPE and not for being numbers.


@pytest.mark.parametrize("mask,projected,edge", [
    ((NAN, NAN, NAN, NAN), (10, 10, 500, 500), "mask_bbox.x0"),
    ((10, 10, 20, 20), (NAN, 10, 500, 500), "projected_bbox.x0"),
    ((10, 10, 20, 20), (10, INF, 500, 500), "projected_bbox.y0"),
])
def test_g4_refuses_a_non_finite_bbox_edge_by_name(mask, projected, edge):
    """RED on base: measured in this worktree, `g4_bbox_sanity(0, (nan,nan,nan,nan),
    (10,10,500,500), 832, 480)` returned `[nan,nan,nan,nan]` — a PASS — and
    `g4_bbox_sanity(0, (10,10,20,20), (nan,10,500,500), 832, 480)` returned
    `[nan, 0, 480, 480]`, also a PASS, on a mask disagreeing with the projected mesh by
    480 px on two of four edges: one NaN first in the list swallows `max()`, and
    `nan > tolerance_px` is False."""
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(0, mask, projected, 832, 480)
    assert edge in str(exc.value)
    assert edge in exc.value.evidence


def test_g4_still_passes_and_still_fires_on_finite_boxes():
    """The two directions the new clause may not disturb."""
    assert gates.g4_bbox_sanity(0, (10, 10, 500, 500), (10, 10, 500, 500), 832, 480) == \
        [0, 0, 0, 0]
    with pytest.raises(G4BboxSanity, match=r"disagrees with the projected mesh"):
        gates.g4_bbox_sanity(0, (10, 10, 20, 20), (10, 10, 500, 500), 832, 480)


# ====================================================================== F-b4706738 · Gate
# S stated a verdict over an empty declared population.


def test_gate_s_refuses_a_declared_but_empty_registry():
    """RED on base: measured in this worktree, `gate_s_seed_registration(7, [], 'E14',
    False)` returned `{'registry_size': 0, 'verdict': 'N/A — E14 pre-registered no seeds
    and did not vary its own'}` — a PASS whose verdict asserts a property of a spec the
    call never read. `if not registry:` collapsed None and []."""
    with pytest.raises(GateSSeedRegistration) as exc:
        gates.gate_s_seed_registration(7, [], "E14", False)
    assert "EMPTY" in str(exc.value)
    assert exc.value.evidence["registry_declared"] is True


def test_gate_s_keeps_the_documented_none_path():
    """The half the docstring always drew and the code did not: None means 'this
    experiment pre-registered none', and its two directions still hold."""
    ev = gates.gate_s_seed_registration(7, None, "E14", False)
    assert ev["verdict"].startswith("N/A")
    assert ev["registry_declared"] is False
    with pytest.raises(GateSSeedRegistration, match=r"may not be varied"):
        gates.gate_s_seed_registration(7, None, "E14", True)
    assert gates.gate_s_seed_registration(7, [7, 8], "E14", True)["verdict"] == \
        "seed is pre-registered"


# ====================================================================== F-89eb81a9 · the
# shape discriminator reported a non-finite mesh as a well-proportioned figure.


@pytest.mark.parametrize("half", [(NAN, 1.0, 0.5), (INF, 1.0, 0.5), (1.0, NAN, 0.5)])
def test_extent_summary_refuses_a_non_finite_component(half):
    """RED on base: measured in this worktree, `extent_summary((nan, 1.0, 0.5))` returned
    `{'extents': [NaN, 2.0, 1.0], 'longest': NaN, 'shortest': NaN,
    'aspect_longest_over_shortest': Infinity, 'degenerate_axis': false}` — `any(v < 0)` is
    False for a NaN, `max`/`min` propagate it, `shortest > 0` is False so the guarded
    division falls to its `inf` branch, and the record states affirmatively that no axis
    is degenerate. `probe_subject` then writes the bare token `NaN` into
    `subject_extents.json` with the stdlib `allow_nan` default."""
    with pytest.raises(SubjectExtentError) as exc:
        subject.extent_summary(half)
    assert isinstance(exc.value, ArmatureError)
    assert "half_extent." in str(exc.value)


def test_the_three_shape_refusals_are_the_family_not_value_errors():
    """RED on base: all three raised a bare `ValueError`, which is not an
    `ArmatureError`, so `probe_subject`'s halt handler classified a deliberate refusal
    exit 1 (unhandled) instead of exit 2 — the 13-site re-classing wave 12 did elsewhere,
    with this module missed."""
    for bad, clause in ((None, r"has no geometry to measure"),
                        ((1.0, 2.0), r"must have 3 components"),
                        ((1.0, -2.0, 3.0), r"must be non-negative")):
        with pytest.raises(SubjectExtentError, match=clause):
            subject.extent_summary(bad)
    assert issubclass(SubjectExtentError, ArmatureError)


def test_a_planar_asset_is_still_reported_rather_than_refused():
    """The direction the finiteness clause must not swallow: zero is a degenerate axis,
    which this module REPORTS, because whether a mesh is the right shape is not its call."""
    s = subject.extent_summary((0.5, 0.5, 0.0))
    assert s["degenerate_axis"] is True and math.isinf(s["aspect_longest_over_shortest"])


# ====================================================================== F-b426ce5c · the
# one numeric camera field the wave-12 sweep did not reach, and depth.window's infinity.


def _spec(**over):
    spec = {"spec_version": 1, "name": "n", "generator": "wan2.1_vace_14B",
            "asset": {"path": "a.glb"},
            "resolution": {"width": 832, "height": 480},
            "frames": {"count": 33, "fps": 16}, "channels": ["depth"]}
    spec.update(over)
    return spec


@pytest.mark.parametrize("over,field", [
    ({"camera": {"type": "orbit", "target": [NAN, 0, 0]}}, "spec.camera.target"),
    ({"camera": {"type": "orbit", "target": [INF, 0, 0]}}, "spec.camera.target"),
    ({"camera": {"type": "orbit", "target": [0, 0, -INF]}}, "spec.camera.target"),
    ({"depth": {"window": [-INF, INF]}}, "spec.depth.window"),
])
def test_the_last_unswept_numeric_spec_fields_refuse_a_non_finite_value(over, field):
    """RED on base: measured in this worktree, `camera={'type':'orbit','target':
    [nan,0,0]}` and `target=[inf,0,0]` were both ACCEPTED and returned unchanged, and
    `depth.window=[-inf, inf]` was ACCEPTED — the window's NaN case was covered only by
    ACCIDENT, because `window[0] < window[1]` is False for a NaN. `load_spec` uses
    `json.load` with the stdlib default, which reads the bare tokens `NaN` and
    `Infinity`, so a spec file carrying one parses."""
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(_spec(**over))
    assert field in str(exc.value)


def test_the_window_ordering_clause_still_speaks_for_itself():
    """The clause the finiteness guard sits in FRONT of, not on top of."""
    with pytest.raises(SpecError, match=r"z_min must be below z_max"):
        shotspec.normalise_spec(_spec(depth={"window": [5.0, 1.0]}))


# ====================================================================== F-b543a535 ·
# `spec.edge` and `spec.render` were validated in no way at all.


@pytest.mark.parametrize("over,field", [
    ({"edge": {"depth_rel_threshold": "off", "normal_angle_deg": 30.0}},
     "spec.edge.depth_rel_threshold"),
    ({"edge": {"depth_rel_threshold": 0.02, "normal_angle_deg": None}},
     "spec.edge.normal_angle_deg"),
    ({"edge": {"depth_rel_threshold": NAN, "normal_angle_deg": 30.0}},
     "spec.edge.depth_rel_threshold"),
    ({"edge": {"depth_rel_threshold": 0.02, "normal_angle_deg": NAN}},
     "spec.edge.normal_angle_deg"),
    ({"edge": {"depth_rel_threshold": 0.02, "normal_angle_deg": 390.0}},
     "spec.edge.normal_angle_deg"),
    ({"render": {"engine": "BLENDER_EEVEE", "samples": -1, "filter_size": 0.01,
                 "film_transparent": True}}, "spec.render.samples"),
    ({"render": {"engine": "BLENDER_EEVEE", "samples": 1, "filter_size": NAN,
                 "film_transparent": True}}, "spec.render.filter_size"),
    ({"render": {"engine": "NOT_AN_ENGINE", "samples": 1, "filter_size": 0.01,
                 "film_transparent": True}}, "spec.render.engine"),
])
def test_the_two_unvalidated_spec_blocks_now_refuse_by_field_name(over, field):
    """RED on base: measured in this worktree, every one of these was ACCEPTED and
    returned unchanged — `normalise_spec` reached its `return` having never touched
    either block."""
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(_spec(**over))
    assert field in str(exc.value)


def test_a_nan_edge_threshold_writes_a_blank_control_channel():
    """**Why the NaN case is the silent one, measured on the consumer the spec feeds.**
    `stage_render.py:370` hands both edge numbers straight to `channels.derive_edge`,
    where `rel > float(nan)` and `min_dot < cos(nan)` are both all-False. A blank edge
    control channel is then a well-formed PNG at every frame: G2 counts files present and
    non-empty, G4 compares mask against projection and is blind to channel CONTENT, and
    the credits are spent on a generation whose edge control carried no information.

    This asserts the CONSEQUENCE, not the fix — it passes on base too, and it is here so
    the refusal above cannot be deleted as pedantry."""
    from armature_core import channels
    z = np.zeros((8, 8), dtype=np.float64)
    z[:, 4:] = 1.0
    n_cam = np.zeros((8, 8, 3), dtype=np.float64)
    n_cam[..., 2] = 1.0
    mask = np.ones((8, 8), dtype=bool)
    _, good = channels.derive_edge(z, n_cam, mask, 0.02, 30.0)
    _, blank = channels.derive_edge(z, n_cam, mask, NAN, NAN)
    assert good["depth_break_px"] > 0
    assert blank["depth_break_px"] == 0 and blank["normal_break_px"] == 0


def test_every_committed_spec_still_parses():
    """The population the two new blocks are allowed to refuse is malformed specs, not
    this repo's own. Derived from the directory, never a typed list."""
    import json
    root = os.path.dirname(TOOLS)
    specs = []
    for f in sorted(os.listdir(os.path.join(root, "specs"))):
        if not f.endswith(".json"):
            continue
        path = os.path.join(root, "specs", f)
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        # `specs/` also holds seed registries and prompt records, which are not shot specs
        # and `normalise_spec` has never read. The population is the files carrying the
        # key this module keys on, derived rather than typed.
        if isinstance(raw, dict) and "spec_version" in raw:
            specs.append(path)
    assert len(specs) >= 5, f"only {len(specs)} shot spec(s) found; this would pass over " \
                            f"an almost-empty population"
    for path in specs:
        shotspec.load_spec(path)


# ====================================================================== F-8a28fff6 · the
# CONDITIONAL tier read `hits[0]`, so a merged name lost its obligation.

BASE_WEIGHT = "wan2.1_vace_14B_fp16.safetensors"
#: A filename that matches BOTH a waivable EXCLUDED row and the CONDITIONAL one. The shape
#: `rulings_for`'s own docstring argues is the realistic one: "Stacked and merged LoRA
#: names are concatenations".
MERGED = "technically_color_lightx2v_merge.safetensors"


def _graph(*weights):
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE_WEIGHT}},
         "9": {"class_type": "KSampler",
               "inputs": {"seed": 7, "control_after_generate": "fixed"}}}
    for i, w in enumerate(weights, start=2):
        g[str(i)] = {"class_type": "LoraLoaderModelOnly",
                     "inputs": {"lora_name": w, "strength_model": 1.0}}
    return g


def test_the_merged_filename_matches_both_rows():
    """The premise, measured rather than assumed."""
    assert [(h["matched_on"], h["verdict"]) for h in RG.rulings_for(MERGED)] == \
        [("lightx2v", "EXCLUDED"), ("technically_color", "CONDITIONAL")]


def test_a_stricter_match_does_not_delete_the_credit_obligation():
    """RED on base: measured in this worktree, `conditional_component_keys(graph)`
    returned `[]` for this filename — a builder asking the graph which obligations it had
    picked up was told none — because the helper filtered on the TOP-LEVEL verdict, which
    `components()` copies from `hits[0]`, while `ruling['matches']` recorded both rows and
    went unread."""
    assert RG.conditional_component_keys(_graph(MERGED)) == ["technically_color"]


def test_the_obligation_survives_a_methodology_waiver_of_the_other_row():
    """RED on base: `verify(graph, frame=(832,480,33), allow=('lightx2v',))` returned
    GREEN with the receipt "1 of 1 component(s) classified, 0 unclassified, 0 conditional
    (credited) ... WAIVED components ['lightx2v']" — footage from a merged LoRA whose
    grant is conditional on crediting renderartist, submitted and publishable with no
    attribution anywhere and a receipt affirmatively stating zero conditional components.
    `allow=('lightx2v',)` is a live methodology waiver, not a hypothetical."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_graph(MERGED), frame=(832, 480, 33), allow=("lightx2v",))
    assert exc.value.evidence["clause"] == "uncredited_conditional_component"
    [row] = exc.value.evidence["uncredited_conditional"]
    assert row["matched_on"] == "technically_color"
    assert row["strictest_verdict"] == "EXCLUDED"

    entry = RG.attribution_entry_for("technically_color")
    ev = RG.verify(_graph(MERGED), frame=(832, 480, 33), allow=("lightx2v",),
                   attribution=[entry])
    assert ev["components_conditional"] == 1
    assert ev["components_conditional_credited"] == 1


# ====================================================================== F-74787978 · the
# converse nothing checked: a credit naming no component the graph loads.


def test_verify_refuses_a_credit_for_a_component_the_graph_never_loaded():
    """RED on base: measured in this worktree on a graph loading only the base model plus
    a pinned KSampler, `verify(g, frame=(832,480,33),
    attribution=[attribution_entry_for('technically_color')])` was ACCEPTED, with
    `ev['attribution']` carrying the full credit line "Technically Color LoRA by
    renderartist (CivitAI)" beside `ev['verdict']` reading "0 of 1 component(s)
    classified, 1 unclassified, 0 conditional (credited)" — one receipt, two populations,
    nothing reconciling them and no `attribution_unmatched` key."""
    entry = RG.attribution_entry_for("technically_color")
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_graph(), frame=(832, 480, 33), attribution=[entry])
    ev = exc.value.evidence
    assert ev["clause"] == "orphan_attribution"
    assert ev["attribution_unmatched"] == [entry]
    assert "renderartist" in str(exc.value)


def test_the_receipt_states_the_count_it_checked():
    """A record may not assert a property nobody checked — so the number is in the
    verdict line on the PASS path too, read back off the printed string."""
    entry = RG.attribution_entry_for("technically_color")
    ev = RG.verify(_graph(MERGED), frame=(832, 480, 33), allow=("lightx2v",),
                   attribution=[entry])
    assert ev["attribution_unmatched"] == []
    assert ev["attribution_unmatched_count"] == 0
    assert "0 attribution entries matching no loaded component" in ev["verdict"]


def test_a_graph_with_no_attribution_at_all_is_untouched_by_the_new_clause():
    """The direction the clause must not invent: no credits is not an orphan credit."""
    ev = RG.verify(_graph(), frame=(832, 480, 33))
    assert ev["attribution_unmatched"] == []


# ====================================================================== F-b44c880d ·
# `unreadable_node` closed the top-level array and not the recursion.

GOOD_NODE = {"id": 1, "type": "UNETLoader", "widgets_values": [BASE_WEIGHT]}


def _saved(stray):
    return {"nodes": [GOOD_NODE],
            "definitions": {"subgraphs": [
                {"id": "s1", "name": "blueprint", "nodes": [stray]}]}}


@pytest.mark.parametrize("stray", [None, "x", 7])
@pytest.mark.parametrize("fn", ["components", "seeds", "latents"])
def test_a_stray_entry_one_level_down_is_gate_route_not_an_attribute_error(fn, stray):
    """RED on base: measured in this worktree on a save-format graph holding one
    well-formed UNETLoader plus a subgraph definition whose `nodes` array carries a string
    or a JSON null, `components()`, `seeds()`, `latents()` and `verify()` ALL raised
    `AttributeError: 'NoneType' object has no attribute 'get'`, while the same stray entry
    at the TOP level raised `RouteGate` with `clause: unreadable_node`. `AttributeError`
    is not an `ArmatureError`, so the halt contract's exit-2 branch — the six-key
    `<TOOL>_HALT` receipt — was bypassed and the run was classified as an unhandled crash
    rather than as Gate ROUTE refusing a shape it cannot read."""
    with pytest.raises(RG.RouteGate) as exc:
        getattr(RG, fn)(_saved(stray))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["where"] == "blueprint"
    assert ev["index"] == 0
    assert ev["entry_type"] == type(stray).__name__


def test_verify_refuses_the_nested_stray_too():
    """The gate before a paid submission reads the same walk."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_saved(None), frame=(832, 480, 33), carries_no_sampler=True)
    assert exc.value.evidence["clause"] == "unreadable_node"


def test_the_top_level_refusal_is_the_same_object_and_still_fires():
    """One implementation, two levels, so they cannot drift apart again."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components({"nodes": [None]})
    assert exc.value.evidence["clause"] == "unreadable_node"
    assert exc.value.evidence["where"] == "top"


def test_a_well_formed_nested_graph_is_still_walked():
    """The direction the guard may not break: the nested weight is still SEEN."""
    nested = {"nodes": [GOOD_NODE],
              "definitions": {"subgraphs": [{"id": "s1", "nodes": [
                  {"id": 2, "type": "LoraLoaderModelOnly", "widgets_values": [MERGED]}]}]}}
    assert sorted(c["file"] for c in RG.components(nested)) == \
        sorted([BASE_WEIGHT, MERGED])


# ====================================================================== the root fix the
# coordinator routed here: `ArmatureError` dropped the evidence it was handed.


def test_the_base_class_stores_the_evidence_it_is_given():
    """RED on base: `ArmatureError` had no `__init__`, so a two-argument raise put the
    dict in `args[1]` and no `evidence` attribute existed — a halt handler reading
    `getattr(exc, 'evidence', None)` printed `"evidence": null` while the raising line was
    passing a receipt. `GateFailure` defined the constructor for its own subtree only."""
    receipt = {"k": 1}
    assert ArmatureError("m", receipt).evidence is receipt
    for cls in (SpecError, SubjectExtentError, GatePRestPose, RG.RouteGate):
        assert cls("m", receipt).evidence is receipt
    # WAVE 16, F-738053cc — the comment that used to sit here stated a FAMILY-WIDE rule and
    # the four assertions beneath it were a two-class sample (two plain refusals, two
    # gates). It read: "It stores what is PASSED and invents nothing … Only `GateFailure`
    # normalises, because its clauses index into `ev` while they measure." Measured on the
    # absent path across the whole family in this worktree on `041027c`: of the 125 family
    # class definitions under `tools/**`, 9 return None and 116 return `{}` — and 45 of
    # those 116 are NOT in the `GateFailure` subtree. Forty-four define their own
    # normalising `__init__` (10 in `armature_core`: `blender_scene` x2, `clipcompare`,
    # `clipstats`, `framing`, `glb`, `lift_solve`, `pngio`, `sitelist`, `walk`; 28 in
    # instruments-measure's tools; 4 `PayloadError`s; `rig_character.SiteListInvalid`), and
    # `measure_tracking.TrackingError` / `.AnchorMismatch` inherit one from
    # `_CarriesEvidence`. So the general claim was false of 45 measured classes, and
    # `tests/test_core_solver_evidence.py::test_the_two_dual_based_andons_are_both_kinds_of_
    # refusal_at_once` asserted of three of them that they are
    # `not issubclass(GateFailure)` and then checked only the PASSED path, two lines from
    # where the same file could have caught it.
    #
    # The rule is now asserted over the DERIVED family rather than narrated over a sample:
    # `tests/test_gates.py::test_no_family_class_outside_the_gate_failure_subtree_
    # normalises_a_bare_message` walks all 125 and names every member that breaks it, and
    # rule 5 deletes the 44 constructors this wave. What stays here is the base's own
    # contract, which is what this test is for — including clause 2 as IDENTITY, since
    # `dict(evidence)` satisfies equality and breaks the contract.
    assert ArmatureError("m").evidence is None
    assert SpecError("m").evidence is None
    assert GatePRestPose("m").evidence == {}
    assert RG.RouteGate("m").evidence == {}


def test_gate_failure_keeps_its_gate_id_formatting():
    """The half `GateFailure` still owns after the constructor moved up."""
    assert str(GatePRestPose("m")).startswith("[P] ")
    assert str(G4BboxSanity("m")).startswith("[G4] ")
