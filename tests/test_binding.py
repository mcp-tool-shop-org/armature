"""The rigid-per-segment assignment rule, driven against geometry with a known answer.

The rule decides which bone every one of 399,140 vertices belongs to, and a wrong answer is
invisible to every gate: Gate N passes on names, Gate P passes because the weights still sum
to one, Gate D reproduces the wrong assignment perfectly. The only thing that catches it is a
fixture built where the right answer is known in advance.
"""

import numpy as np
import pytest

from armature_core import binding
from armature_core.errors import ArmatureError


def _chain():
    """Two collinear bones meeting at z = 1.0 — the shared joint — plus a fat torso bone
    off to the side, standing in for the chest an arm hangs next to."""
    return [
        {"name": "upper", "head": (0.0, 0.0, 2.0), "tail": (0.0, 0.0, 1.0), "parent": None},
        {"name": "lower", "head": (0.0, 0.0, 1.0), "tail": (0.0, 0.0, 0.0),
         "parent": "upper"},
        {"name": "torso", "head": (0.6, 0.0, 2.0), "tail": (0.6, 0.0, 0.0), "parent": None},
    ]


RADII = {"upper": 0.10, "lower": 0.10, "torso": 0.40}


def _weights(points, bones=None, radii=None, band=binding.BLEND_BAND):
    return binding.rigid_segment_weights(np.asarray(points, dtype=float),
                                         bones or _chain(), radii or RADII, band)


# ---------------------------------------------------------------- the invariant Gate P reads


def test_weights_sum_to_exactly_one_on_every_vertex():
    """Skinning is the identity at bind only when the weights sum to 1. If this drifts,
    Gate P fires on a rig whose assignment is otherwise fine."""
    rng = np.random.default_rng(0)
    pts = rng.uniform(-1.0, 3.0, size=(4000, 3))
    w, diag = _weights(pts)
    total = sum(w.values())
    assert np.allclose(total, 1.0, atol=0.0)
    assert diag["weight_sum_min"] == 1.0 and diag["weight_sum_max"] == 1.0


def test_every_vertex_is_assigned_to_something():
    rng = np.random.default_rng(1)
    _, diag = _weights(rng.uniform(-2.0, 4.0, size=(2000, 3)))
    assert diag["vertices_with_any_weight"] == diag["vertices"]


# --------------------------------------------------- the boundary sits on the measured joint


def test_the_boundary_between_adjacent_bones_falls_at_their_shared_joint():
    """The property the whole arm rests on. The joint is at z = 1.0 because that is where
    the measured ball centre put it, so a vertex just above must be `upper` and one just
    below must be `lower` — not at some fraction anyone chose."""
    w, _ = _weights([(0.0, 0.0, 1.30), (0.0, 0.0, 0.70)])
    assert w["upper"][0] == 1.0 and w["lower"][0] == 0.0
    assert w["lower"][1] == 1.0 and w["upper"][1] == 0.0


def test_a_vertex_exactly_on_the_shared_joint_is_split_evenly():
    w, _ = _weights([(0.05, 0.0, 1.0)])
    assert abs(w["upper"][0] - 0.5) < 1e-9
    assert abs(w["lower"][0] - 0.5) < 1e-9


def test_moving_the_joint_moves_the_boundary_with_it():
    """If the boundary did not track the measured joint, correcting the pivots in round 2
    would have changed nothing about the skinning."""
    bones = _chain()
    for b in bones:
        if b["name"] == "upper":
            b["tail"] = (0.0, 0.0, 1.6)
        if b["name"] == "lower":
            b["head"] = (0.0, 0.0, 1.6)
    w, _ = _weights([(0.0, 0.0, 1.30)], bones=bones)
    assert w["lower"][0] == 1.0, "the boundary did not move with the joint"


# ------------------------------------------------------------------------- the blend band


def test_the_blend_band_only_applies_between_adjacent_bones():
    """`torso` is nobody's parent here. A vertex near the boundary between `lower` and
    `torso` must go rigidly to one of them, or a limb would smear into the trunk."""
    w, _ = _weights([(0.30, 0.0, 1.0)])
    shared = [n for n in ("upper", "lower", "torso") if 0.0 < w[n][0] < 1.0]
    assert not shared, f"blended across non-adjacent bones: {shared}"


def test_a_wider_band_blends_more_vertices_and_a_narrow_one_fewer():
    rng = np.random.default_rng(2)
    pts = rng.uniform(-0.2, 0.2, size=(3000, 3)) + np.array([0.0, 0.0, 1.0])
    _, narrow = _weights(pts, band=0.05)
    _, wide = _weights(pts, band=0.80)
    assert wide["vertices_blended"] > narrow["vertices_blended"]


def test_a_zero_or_negative_band_raises_rather_than_silently_making_hard_seams():
    with pytest.raises(ArmatureError):
        _weights([(0.0, 0.0, 1.0)], band=0.0)
    with pytest.raises(ArmatureError):
        _weights([(0.0, 0.0, 1.0)], band=-0.2)


# ------------------------------------------- normalising by radius, and why it is not optional


def test_a_vertex_deep_inside_the_thick_bone_is_not_stolen_by_a_nearer_thin_one():
    """The defect this prevents: the arms hang close to the torso, so on RAW distance a thin
    arm bone captures belly that merely happens to be nearer to it than to the thick chest
    bone, and a slab of torso ends up welded to the elbow."""
    # x = 0.22 puts the point 0.22 from the limb (radius 0.10 → u = 2.2) and 0.38 from the
    # torso (radius 0.40 → u = 0.95): nearer the limb, deeper inside the torso.
    p = (0.22, 0.0, 1.5)
    d_limb = binding.segment_distance([p], (0.0, 0.0, 2.0), (0.0, 0.0, 1.0))[0]
    d_torso = binding.segment_distance([p], (0.6, 0.0, 2.0), (0.6, 0.0, 0.0))[0]
    assert d_limb < d_torso, "fixture is wrong: the limb must be nearer in raw distance"
    assert d_torso / RADII["torso"] < d_limb / RADII["upper"], (
        "fixture is wrong: the torso must be the deeper one once normalised")

    w, _ = _weights([p])
    assert w["torso"][0] == 1.0, (
        "raw distance won: the vertex went to the thin limb bone it happened to be nearer "
        "to, instead of the thick bone it is deepest inside")


def test_a_missing_or_zero_radius_raises_instead_of_falling_back_to_a_constant():
    for bad in ({"upper": 0.1, "lower": 0.1}, dict(RADII, torso=0.0)):
        with pytest.raises(ArmatureError) as exc:
            _weights([(0.0, 0.0, 1.0)], radii=bad)
        assert "radius" in str(exc.value)


# -------------------------------------------------------------------------- shape and refusal


def test_a_single_deforming_bone_takes_everything():
    bones = [{"name": "only", "head": (0, 0, 0), "tail": (0, 0, 1), "parent": None}]
    w, diag = binding.rigid_segment_weights(np.zeros((10, 3)), bones, {"only": 0.2})
    assert np.all(w["only"] == 1.0) and diag["vertices_blended"] == 0


def test_empty_input_and_empty_bone_list_both_raise():
    with pytest.raises(ArmatureError):
        _weights(np.zeros((0, 3)))
    with pytest.raises(ArmatureError):
        binding.rigid_segment_weights(np.zeros((5, 3)), [], {})


def test_segment_distance_clamps_at_both_ends():
    """A point beyond the tail must measure to the tail, not to the infinite line — or a
    bone would capture vertices far past the end of the limb it describes."""
    d = binding.segment_distance([(0.0, 0.0, 5.0)], (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    assert abs(d[0] - 4.0) < 1e-12
    d = binding.segment_distance([(0.0, 0.0, -3.0)], (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    assert abs(d[0] - 3.0) < 1e-12


def test_a_degenerate_bone_measures_to_its_head_rather_than_dividing_by_zero():
    d = binding.segment_distance([(3.0, 0.0, 0.0)], (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert abs(d[0] - 3.0) < 1e-12


def test_the_assignment_is_deterministic():
    """Gate D compares two builds. If this were order-dependent the gate would fire on
    correct work, and the arm would look nondeterministic when the solver is not."""
    rng = np.random.default_rng(7)
    pts = rng.uniform(-1.0, 3.0, size=(2500, 3))
    a, _ = _weights(pts)
    b, _ = _weights(pts)
    for name in a:
        assert np.array_equal(a[name], b[name])
