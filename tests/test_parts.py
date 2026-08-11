"""Arm (c)'s partition rules and its four gates, driven with the inputs they exist to catch."""

import numpy as np
import pytest

from armature_core import parts
from armature_core.errors import ArmatureError

# A short thin bone between two fat ones — the neck, reduced to its essentials.
BONES = [
    {"name": "chest", "head": (0.0, 0.0, 0.00), "tail": (0.0, 0.0, 0.30), "parent": None},
    {"name": "neck", "head": (0.0, 0.0, 0.30), "tail": (0.0, 0.0, 0.35), "parent": "chest"},
    {"name": "head", "head": (0.0, 0.0, 0.35), "tail": (0.0, 0.0, 0.50), "parent": "neck"},
]
RADII = {"chest": 0.056, "neck": 0.020, "head": 0.050}
NAMES = [b["name"] for b in BONES]


# ------------------------------------------------------------------- face assignment


def test_plain_nearest_gives_the_neck_its_own_faces():
    """The consult's prescription, and the one that works here."""
    centroids = np.array([(0.02, 0.0, 0.32), (0.02, 0.0, 0.15), (0.02, 0.0, 0.45)])
    labels = parts.assign_faces(centroids, BONES, RADII, normalise=False)
    assert NAMES[labels[0]] == "neck"
    assert NAMES[labels[1]] == "chest"
    assert NAMES[labels[2]] == "head"


def test_normalising_squeezes_the_short_thin_bone_out_entirely():
    """The measured defect, reproduced. Dividing by each bone's own radius protects a thin
    bone from a fat NEIGHBOUR, and destroys a short thin bone BETWEEN two fat ones: on the
    performer the neck won zero of 306,110 faces this way and Gate PARTS fired."""
    # A hollow tube, not a filled cloud: this subject is a SHELL and carries no faces on
    # the limb axis. A volume-filled fixture hands the neck the on-axis points for free and
    # the squeeze never reproduces — which is what the first version of this fixture did.
    n = 4000
    z = np.linspace(0.30, 0.35, n)
    theta = np.linspace(0.0, 40.0 * np.pi, n)
    surface = 0.019                                    # the neck's own surface radius
    ring = np.stack([surface * np.cos(theta), surface * np.sin(theta), z], axis=1)
    plain = parts.assign_faces(ring, BONES, RADII, normalise=False)
    norm = parts.assign_faces(ring, BONES, RADII, normalise=True)
    assert (plain == NAMES.index("neck")).sum() > 0, "plain nearest must give the neck faces"
    assert (norm == NAMES.index("neck")).sum() == 0, (
        "fixture stale: normalisation no longer squeezes the neck out, so the regression it "
        "reproduces is gone")


def test_normalised_assignment_still_needs_a_radius_and_refuses_a_default():
    with pytest.raises(ArmatureError):
        parts.assign_faces(np.zeros((4, 3)), BONES, {"chest": 0.05}, normalise=True)


def test_plain_assignment_does_not_require_radii_at_all():
    labels = parts.assign_faces(np.array([(0.0, 0.0, 0.32)]), BONES, {}, normalise=False)
    assert NAMES[labels[0]] == "neck"


def test_a_malformed_centroid_array_raises():
    with pytest.raises(ArmatureError):
        parts.assign_faces(np.zeros((0, 3)), BONES, RADII)
    with pytest.raises(ArmatureError):
        parts.assign_faces(np.zeros((5, 2)), BONES, RADII)


# ------------------------------------------------------------------- Gate PARTS


def test_accounting_passes_on_a_clean_partition():
    labels = np.array([0, 0, 1, 2, 2])
    ev = parts.gate_parts_accounting(labels, 5, NAMES)
    assert ev["faces_per_part"] == {"chest": 2, "neck": 1, "head": 2}


def test_accounting_fires_on_a_face_assigned_to_nothing():
    """A dropped face is a hole in the character that every other gate reports green on."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([0, -1, 1, 2, 2]), 5, NAMES)
    assert "assigned to nothing" in str(exc.value)


def test_accounting_fires_when_a_registered_part_would_be_empty():
    """The measured case: the neck with zero faces would separate into an empty object."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([0, 0, 2, 2]), 4, NAMES)
    assert "neck" in str(exc.value)


def test_accounting_fires_when_the_label_count_does_not_match_the_face_count():
    with pytest.raises(parts.GatePartsAccounting):
        parts.gate_parts_accounting(np.array([0, 1, 2]), 99, NAMES)


def test_accounting_fires_on_a_label_outside_the_registered_list():
    with pytest.raises(parts.GatePartsAccounting):
        parts.gate_parts_accounting(np.array([0, 1, 2, 7]), 4, NAMES)


# ------------------------------------------------------------------- joint planes


def test_a_plane_sits_on_the_measured_ball_with_the_limb_axis_as_its_normal():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.02, "head": 0.05}, RADII)
    by = {p["child"]: p for p in planes}
    assert np.allclose(by["neck"]["point"], (0.0, 0.0, 0.30))
    assert np.allclose(by["neck"]["normal"], (0.0, 0.0, 1.0))
    assert by["neck"]["radius_source"].startswith("measured")
    assert abs(by["neck"]["collar"] - 0.02 * parts.COLLAR_BALL_FRACTION) < 1e-12


def test_a_joint_with_no_ball_falls_back_and_says_so_in_the_record():
    """A fallback that looks like a measurement is the thing this repo keeps catching."""
    planes = parts.joint_planes(BONES, {}, {}, RADII)
    by = {p["child"]: p for p in planes}
    assert by["neck"]["radius_source"].startswith("FALLBACK")
    assert abs(by["neck"]["radius"] - RADII["neck"]) < 1e-12


def test_a_joint_with_neither_a_ball_nor_a_cross_section_raises():
    with pytest.raises(ArmatureError):
        parts.joint_planes(BONES, {}, {}, {"chest": 0.05})


def test_a_zero_length_child_bone_raises_because_its_plane_has_no_normal():
    bad = [dict(BONES[0]), {"name": "neck", "head": (0, 0, 0.3), "tail": (0, 0, 0.3),
                            "parent": "chest"}]
    with pytest.raises(ArmatureError):
        parts.joint_planes(bad, {}, {}, {"chest": 0.05, "neck": 0.02})


# ------------------------------------------------------------------- collar overlap


def test_each_part_borrows_from_its_neighbour_across_the_joint():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.05, "head": 0.05}, RADII)
    centroids = np.array([(0.0, 0.0, 0.32), (0.0, 0.0, 0.27), (0.0, 0.0, 0.05)])
    labels = np.array([NAMES.index("neck"), NAMES.index("chest"), NAMES.index("chest")])
    borrowed, detail = parts.collar_faces(centroids, labels, NAMES, planes)
    assert 0 in borrowed["chest"], "the chest did not reach past the joint into the neck"
    assert 1 in borrowed["neck"], "the neck did not reach back past the joint into the chest"
    assert 2 not in borrowed["neck"], "a face far from the joint was borrowed"
    assert any(d["joint"] == "chest->neck" for d in detail)


def test_a_zero_collar_borrows_nothing():
    """Without overlap, adjacent parts meet exactly at the plane and a gap opens the moment
    the joint rotates. Asserted so the collar cannot silently become decorative."""
    planes = parts.joint_planes(BONES, {}, {"neck": 0.05, "head": 0.05}, RADII,
                                collar_fraction=0.0)
    centroids = np.array([(0.0, 0.0, 0.32), (0.0, 0.0, 0.27)])
    labels = np.array([NAMES.index("neck"), NAMES.index("chest")])
    borrowed, _ = parts.collar_faces(centroids, labels, NAMES, planes)
    assert all(len(v) == 0 for v in borrowed.values())


def test_the_collar_is_bounded_by_its_own_joints_radius_not_a_shared_length():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.02, "head": 0.08}, RADII)
    by = {p["child"]: p for p in planes}
    assert by["head"]["collar"] > by["neck"]["collar"] * 3.0


# ------------------------------------------------------------------- Gate RIGID


def _obs(name="a", disp=0.5, xform=0.0, pair=0.0):
    return {"name": name, "max_displacement": disp, "max_transform_error": xform,
            "max_pair_distance_change": pair, "vertices": 100}


def test_rigid_passes_when_each_part_lands_on_its_bone_transform():
    ev = parts.gate_rigid_arrival([_obs("a"), _obs("b", disp=0.0)], 1.069)
    assert ev["verdict"].startswith("2 parts")


def test_rigid_fires_when_a_part_is_not_where_its_bone_puts_it():
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("elbow.L", xform=0.01)], 1.069)
    assert "elbow.L" in str(exc.value)


def test_rigid_fires_when_a_part_deforms():
    """The whole promise of this route is that nothing deforms. A part that is accidentally
    bound as well as parented still looks broadly right in a thumbnail."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("chest", pair=0.001)], 1.069)
    assert "deforming" in str(exc.value)


def test_rigid_fires_when_nothing_arrived_at_all():
    """E03 Ruling 9's family: every other gate passes on a performance that did not happen."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("a", disp=0.0), _obs("b", disp=0.0)], 1.069)
    assert "nothing arrived" in str(exc.value)


def test_rigid_fires_on_no_observations_rather_than_passing_vacuously():
    with pytest.raises(parts.GateRigidArrival):
        parts.gate_rigid_arrival([], 1.069)


# ------------------------------------------------------------------- Gate D


def _fp(seed=0, n=50):
    rng = np.random.default_rng(seed)
    return {name: {"n_verts": n, "n_faces": n // 2,
                   "positions": np.sort(rng.uniform(-1, 1, size=(n, 3)), axis=0)}
            for name in NAMES}


def test_determinism_passes_on_two_identical_builds():
    assert parts.gate_parts_determinism(_fp(), _fp(), 1.069)["verdict"].startswith("3 parts")


def test_determinism_fires_on_a_moved_vertex_and_on_a_changed_count():
    a, b = _fp(), _fp()
    b["neck"]["positions"][3, 1] += 1e-3
    with pytest.raises(parts.GatePartsDeterminism):
        parts.gate_parts_determinism(a, b, 1.069)

    a, c = _fp(), _fp()
    c["head"]["n_faces"] += 1
    with pytest.raises(parts.GatePartsDeterminism):
        parts.gate_parts_determinism(a, c, 1.069)


def test_determinism_fires_when_a_part_is_missing_from_the_second_build():
    a, b = _fp(), _fp()
    del b["neck"]
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert "neck" in str(exc.value)
