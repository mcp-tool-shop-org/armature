"""Gates N, P and D — driven with the wrong inputs they exist to catch.

Every fixture below answers the question the repo asks of a fixture: *what would this look
like if the code were wrong in the specific way this check exists to catch?* For Gate N
that question has a documented answer sitting in E01's report, so it is used verbatim as
the wrong input.
"""

import numpy as np
import pytest

from armature_core import sitelist
from armature_core.errors import GateDDeterminism, GateNNames, GatePRestPose
from armature_core import rig_gates

REGISTERED = list(sitelist.ALL_NAMES)
DIAGONAL = 1.069037


# --------------------------------------------------------------------------- Gate N


def test_gate_n_passes_on_exactly_the_registered_list():
    ev = rig_gates.gate_n_names(REGISTERED, REGISTERED, "test")
    assert ev["mapped"] == 22
    assert ev["missing"] == [] and ev["unregistered"] == []


def test_gate_n_fires_on_e01s_actual_result():
    """The wrong input is not hypothetical. E01 measured four rigged GLBs on this machine
    naming their bones `bone_0 … bone_N` with zero of 18 sites findable. That rig imports,
    skins and poses; only the names are wrong. If Gate N does not fire on it, Gate N does
    not do the one job it exists for."""
    e01_style = [f"bone_{i}" for i in range(22)]
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(e01_style, REGISTERED, "an E01-style rig")
    assert exc.value.evidence["mapped"] == 0
    assert len(exc.value.evidence["missing"]) == 22
    assert exc.value.gate == "N"


def test_gate_n_fires_when_the_export_drops_the_non_deforming_markers():
    """`export_def_bones=True` is a single flag that silently deletes every marker bone.
    The rig would still carry 17 of 22 names and nothing else would notice."""
    deform_only = [b.name for b in sitelist.BONES if b.deform]
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(deform_only, REGISTERED, "an export with def-bones only")
    assert sorted(exc.value.evidence["missing"]) == ["ear.L", "ear.R", "eye.L", "eye.R",
                                                     "nose"]
    assert exc.value.evidence["mapped"] == 17


def test_gate_n_fires_on_a_bone_no_list_registered():
    """The second direction, and the one a coverage-only gate would wave through: a
    glTF round trip that suffixes a clashing name leaves all 22 sites present AND an
    extra bone nobody registered."""
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(REGISTERED + ["neck.001"], REGISTERED, "a suffixed import")
    assert exc.value.evidence["unregistered"] == ["neck.001"]
    assert exc.value.evidence["missing"] == []


def test_gate_n_fires_on_a_duplicated_site():
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(REGISTERED + ["wrist.L"], REGISTERED, "a doubled bone")
    assert exc.value.evidence["duplicated"] == ["wrist.L"]


def test_gate_n_is_case_and_spelling_exact():
    """`Shoulder.L` is not `shoulder.L`. A matcher looking for substrings would pass this
    and a downstream consumer asking for the registered name would get nothing."""
    sloppy = [n if n != "shoulder.L" else "Shoulder.L" for n in REGISTERED]
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(sloppy, REGISTERED, "a case-mangled rig")
    assert "shoulder.L" in exc.value.evidence["missing"]


# --------------------------------------------------------------------------- Gate P


def _cloud(n=500, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(-0.5, 0.5, size=(n, 3))


def test_gate_p_passes_when_binding_moves_nothing():
    a = _cloud()
    ev = rig_gates.gate_p_rest_pose(a, a.copy(), DIAGONAL)
    assert ev["max_displacement"] == 0.0
    assert ev["verdict"] == "rest pose preserved"


def test_gate_p_passes_just_under_the_threshold_and_fires_just_over():
    """The threshold is a boundary, so it is tested as one — otherwise a gate could be
    off by an order of magnitude and every test would still be green."""
    a = _cloud()
    eps = rig_gates.REST_POSE_EPSILON_FRAC * DIAGONAL

    under = a.copy()
    under[7, 0] += eps * 0.99
    assert rig_gates.gate_p_rest_pose(a, under, DIAGONAL)["n_over_threshold"] == 0

    over = a.copy()
    over[7, 0] += eps * 1.01
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_rest_pose(a, over, DIAGONAL)
    assert exc.value.evidence["max_displacement_vertex"] == 7
    assert exc.value.gate == "P"


def test_gate_p_fires_on_a_vertex_collapsed_to_the_origin():
    """The failure it is really for: a vertex weighted to nothing that Blender drops to
    the object origin. One vertex in 400k, invisible in any mean, catastrophic on screen."""
    a = _cloud()
    bad = a.copy()
    bad[123] = (0.0, 0.0, 0.0)
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_rest_pose(a, bad, DIAGONAL)
    assert exc.value.evidence["max_displacement_vertex"] == 123


def test_gate_p_fires_when_the_vertex_arrays_do_not_correspond():
    a = _cloud(n=500)
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_rest_pose(a, _cloud(n=499), DIAGONAL)
    assert "different vertex array" in str(exc.value)


def test_gate_p_fires_on_a_degenerate_diagonal():
    """The threshold is a fraction of the subject's own size; with no size there is no
    threshold, and defaulting to one would be a global constant sneaking back in."""
    a = _cloud()
    with pytest.raises(GatePRestPose):
        rig_gates.gate_p_rest_pose(a, a.copy(), 0.0)


def test_gate_p_liveness_fires_when_the_deform_is_not_live():
    """Gate P reads 0.0 both when skinning is a perfect identity and when the mesh was
    never bound. This is the clause that separates them."""
    a = _cloud()
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_evaluation_is_live(a, a.copy(), DIAGONAL)
    assert "not live" in str(exc.value)


def test_gate_p_liveness_passes_when_a_posed_bone_moves_the_mesh():
    a = _cloud()
    moved = a.copy()
    moved[:, 0] += 0.05
    ev = rig_gates.gate_p_evaluation_is_live(a, moved, DIAGONAL)
    assert ev["n_vertices_moved"] == len(a)


# --------------------------------------------------------------------------- Gate D


def _fp(seed=0, n=64):
    rng = np.random.default_rng(seed)
    bones = {b.name: {"head": rng.uniform(-1, 1, 3).tolist(),
                      "tail": rng.uniform(-1, 1, 3).tolist(),
                      "roll": 0.0, "parent": b.parent, "use_deform": b.deform}
             for b in sitelist.BONES}
    weights = {b.name: rng.uniform(0, 1, n) for b in sitelist.BONES if b.deform}
    return rig_gates.rig_fingerprint(bones, weights, n)


def test_gate_d_passes_on_two_identical_builds():
    ev = rig_gates.gate_d_determinism(_fp(), _fp(), DIAGONAL)
    assert ev["verdict"].startswith("two builds agree")


def test_gate_d_is_content_comparison_not_byte_comparison():
    """The property the docstring claims: a rig whose *content* is identical but whose
    serialisation order differs must pass. A hash comparison would fail this, and would
    then be quoted as evidence of nondeterminism that does not exist."""
    a = _fp()
    b = rig_gates.rig_fingerprint(
        {k: a["bones"][k] for k in reversed(list(a["bones"]))},
        {k: a["weights"][k] for k in reversed(list(a["weights"]))},
        a["n_verts"],
    )
    assert list(a["bones"]) != list(b["bones"])          # the serialisation differs
    assert rig_gates.gate_d_determinism(a, b, DIAGONAL)["verdict"].startswith("two builds")


def test_gate_d_fires_when_a_bone_head_moves():
    a, b = _fp(), _fp()
    b["bones"]["elbow.L"]["head"][0] += 1e-3
    with pytest.raises(GateDDeterminism) as exc:
        rig_gates.gate_d_determinism(a, b, DIAGONAL)
    assert "elbow.L.head" in str(exc.value)
    assert exc.value.gate == "D"


def test_gate_d_fires_on_a_weight_difference_of_one_vertex():
    """The realistic nondeterminism: a solver that reorders and lands a hair differently
    on one vertex. Bone positions would be identical and the GLB would look the same."""
    a, b = _fp(), _fp()
    b["weights"]["shoulder.L"][17] += 1e-3
    with pytest.raises(GateDDeterminism) as exc:
        rig_gates.gate_d_determinism(a, b, DIAGONAL)
    assert "shoulder.L" in str(exc.value)


def test_gate_d_fires_on_a_changed_parent_and_on_a_changed_deform_flag():
    a, b = _fp(), _fp()
    b["bones"]["wrist.R"]["parent"] = "chest"
    with pytest.raises(GateDDeterminism):
        rig_gates.gate_d_determinism(a, b, DIAGONAL)

    a, c = _fp(), _fp()
    c["bones"]["nose"]["use_deform"] = True
    with pytest.raises(GateDDeterminism):
        rig_gates.gate_d_determinism(a, c, DIAGONAL)


def test_gate_d_fires_when_a_bone_is_missing_from_the_second_build():
    a, b = _fp(), _fp()
    del b["bones"]["ear.L"]
    with pytest.raises(GateDDeterminism) as exc:
        rig_gates.gate_d_determinism(a, b, DIAGONAL)
    assert "ear.L" in str(exc.value)


def test_gate_d_tolerance_scales_with_the_subject_not_with_metres():
    """A global constant must not govern a local feature. The same absolute wobble must
    fire on a small subject and pass on a large one."""
    wobble = 1e-5
    a, b = _fp(), _fp()
    b["bones"]["hips"]["head"][2] += wobble
    with pytest.raises(GateDDeterminism):
        rig_gates.gate_d_determinism(a, b, bbox_diagonal=1.0)
    rig_gates.gate_d_determinism(a, b, bbox_diagonal=1000.0)


# ------------------------------------------------- Gate P, the round-trip clause


def test_round_trip_passes_when_only_vertex_MULTIPLICITY_changed():
    """The measured case. glTF re-splits vertices at attribute discontinuities: this
    subject went out as 399,140 vertices and came back as 399,903, over the same 149,643
    positions. An index-wise comparison reads two different arrays against each other —
    which is what the first version of this code did, until it raised and said so."""
    rng = np.random.default_rng(3)
    base = rng.uniform(-0.5, 0.5, size=(400, 3)).astype(np.float32)
    doubled = np.concatenate([base, base[:37]], axis=0)   # 37 seam-splits
    ev = rig_gates.gate_p_round_trip_positions(base, doubled, DIAGONAL)
    assert ev["unique_positions_source"] == ev["unique_positions_roundtrip"] == 400
    assert ev["n_roundtrip_vertices"] == 437
    assert ev["max_deviation"] == 0.0


def test_round_trip_fires_when_a_position_actually_moved():
    rng = np.random.default_rng(3)
    base = rng.uniform(-0.5, 0.5, size=(400, 3)).astype(np.float32)
    moved = base.copy()
    moved[11, 2] += 0.01
    with pytest.raises(GatePRestPose) as exc:
        rig_gates.gate_p_round_trip_positions(base, moved, DIAGONAL)
    assert exc.value.evidence["positions_only_in_source"] == 1
    assert exc.value.evidence["positions_only_in_roundtrip"] == 1
    assert exc.value.evidence["max_deviation"] > 0.009


def test_round_trip_tolerates_a_last_bit_difference_the_format_is_entitled_to():
    """float32 is glTF's storage precision. Firing on one ULP would fire on correct exports."""
    rng = np.random.default_rng(3)
    base = rng.uniform(-0.5, 0.5, size=(400, 3)).astype(np.float32)
    nudged = base.copy()
    nudged[5] = np.nextafter(nudged[5], np.float32(1.0))
    ev = rig_gates.gate_p_round_trip_positions(base, nudged, DIAGONAL)
    assert ev["positions_only_in_source"] == 1
    assert ev["max_deviation"] < ev["threshold"]


def test_round_trip_fires_on_a_degenerate_diagonal():
    a = np.zeros((10, 3), dtype=np.float32)
    with pytest.raises(GatePRestPose):
        rig_gates.gate_p_round_trip_positions(a, a, 0.0)
