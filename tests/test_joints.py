"""Ball-joint detection and the instrument-versus-subject ruling.

The ruling in `joints.verdict` is the one that decided whether to move 22 bones or to fix a
renderer, so it is tested in **both** directions: a uniform offset must read as the
instrument, and a spread of offsets must read as the subject. A discriminator that only ever
sees one answer is not a discriminator.
"""

import numpy as np
import pytest

from armature_core import joints
from armature_core.errors import LandmarkError


def _sphere(centre, radius, n=600, jitter=0.0, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    r = radius * (1.0 + jitter * rng.normal(size=(n, 1)))
    return np.asarray(centre) + v * r


def _capsule(a, b, radius, n=600, seed=1):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    t = rng.uniform(0, 1, size=(n, 1))
    axis = b - a
    axis = axis / np.linalg.norm(axis)
    u = np.cross(axis, [1.0, 0.0, 0.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(axis, [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    w = np.cross(axis, u)
    ang = rng.uniform(0, 2 * np.pi, size=(n, 1))
    return a + t * (b - a) + radius * (np.cos(ang) * u + np.sin(ang) * w)


# --------------------------------------------------------------------- sphere fitting


def test_sphere_fit_recovers_a_known_sphere():
    centre, radius, resid = joints.sphere_fit(_sphere((0.1, -0.2, 0.3), 0.024))
    assert np.allclose(centre, (0.1, -0.2, 0.3), atol=1e-6)
    assert abs(radius - 0.024) < 1e-6
    assert resid < 1e-6


def test_sphere_fit_reports_a_large_residual_for_something_that_is_not_a_sphere():
    _, _, resid = joints.sphere_fit(_capsule((0, 0, 0), (0, 0, 0.3), 0.02))
    assert resid > 0.2, "an elongated limb must not look like a ball"


def test_sphere_fit_refuses_too_few_points():
    with pytest.raises(LandmarkError):
        joints.sphere_fit(np.zeros((3, 3)))


# ------------------------------------------------------------------ shells and balls


def _labelled(parts):
    verts = np.concatenate(parts, axis=0)
    labels = np.concatenate([np.full(len(p), i) for i, p in enumerate(parts)])
    return verts, labels


def test_a_ball_is_picked_out_of_a_scene_of_limbs():
    verts, labels = _labelled([
        _capsule((0, 0, 0.0), (0, 0, 0.30), 0.02, n=900),
        _sphere((0.0, 0.0, 0.32), 0.024, n=900),
        _capsule((0, 0, 0.34), (0, 0, 0.64), 0.02, n=900, seed=3),
    ])
    balls = joints.candidate_balls(joints.describe_shells(verts, labels))
    assert len(balls) == 1
    assert np.allclose(balls[0]["centre"], (0.0, 0.0, 0.32), atol=2e-3)


def test_a_sliver_never_becomes_a_pivot():
    """A 6-vertex fragment can fit a sphere beautifully and mean nothing."""
    verts, labels = _labelled([_sphere((0, 0, 0), 0.02, n=6),
                               _capsule((0, 0, 0), (0, 0, 0.3), 0.02, n=900)])
    assert joints.candidate_balls(joints.describe_shells(verts, labels)) == []


# ------------------------------------------------------------------------- snapping


def _derived(marks, limb_r=0.015):
    trace = [{"z": z, "r_mean": limb_r} for z in np.linspace(-0.6, 0.6, 60)]
    return {"landmarks": dict(marks),
            "traces": {k: list(trace) for k in ("arm_L", "arm_R", "leg_L", "leg_R")}}


BASE = {
    "shoulder_L": (0.09, 0.0, 0.29), "elbow_L": (0.147, 0.0, 0.025),
    "wrist_L": (0.144, 0.0, -0.133), "shoulder_R": (-0.09, 0.0, 0.29),
    "elbow_R": (-0.147, 0.0, 0.025), "wrist_R": (-0.144, 0.0, -0.133),
    "hip_L": (0.039, 0.0, 0.025), "knee_L": (0.066, 0.0, -0.219),
    "ankle_L": (0.078, 0.0, -0.463), "hip_R": (-0.036, 0.0, 0.025),
    "knee_R": (-0.068, 0.0, -0.213), "ankle_R": (-0.053, 0.0, -0.463),
}


def _ball(centre, radius=0.016, n=200, aspect=0.9, resid=0.05):
    return {"centre": list(centre), "radius": radius, "n": n,
            "aspect": aspect, "relative_residual": resid}


def test_a_pivot_moves_onto_its_ball():
    """The measured case: the elbow ball sits well above the heuristic elbow."""
    balls = [_ball((0.149, 0.006, 0.098))]
    marks, table = joints.snap_sites_to_balls(_derived(BASE), balls)
    assert table["elbow_L"]["matched"] is True
    assert np.allclose(marks["elbow_L"], (0.149, 0.006, 0.098))
    assert table["elbow_L"]["offset"] > 0.07
    assert 0.25 < table["elbow_L"]["offset_as_fraction_of_segment"] < 0.32


def test_a_site_with_no_ball_keeps_its_heuristic_and_says_so():
    marks, table = joints.snap_sites_to_balls(_derived(BASE), [])
    assert all(v["matched"] is False for v in table.values())
    assert marks["elbow_L"] == BASE["elbow_L"]
    assert "NOT a measured marker" in table["elbow_L"]["reason"]


def test_a_ball_of_the_wrong_size_for_the_limb_is_not_claimed():
    """The face carries small spherical pieces. One sitting near a wrist must not become
    the wrist pivot just because it is round and close."""
    tiny = _ball((0.144, 0.0, -0.130), radius=0.0035)
    huge = _ball((0.144, 0.0, -0.130), radius=0.20)
    for ball in (tiny, huge):
        _, table = joints.snap_sites_to_balls(_derived(BASE), [ball])
        assert table["wrist_L"]["matched"] is False


def test_a_ball_beyond_the_search_radius_is_not_claimed():
    far = _ball((0.147, 0.0, 0.025 + 0.40))
    _, table = joints.snap_sites_to_balls(_derived(BASE), [far])
    assert table["elbow_L"]["matched"] is False


def test_the_search_radius_stops_one_ball_serving_both_ends_of_a_segment():
    """A point inside both ends' tolerances cannot exist: the bound is 0.35 of the segment,
    so anything equidistant from the two ends is 0.5 of the segment from each. Asserted
    rather than assumed, because it is what makes double-claiming rare in the first place."""
    mid = tuple((np.array(BASE["shoulder_L"]) + np.array(BASE["elbow_L"])) / 2.0)
    _, table = joints.snap_sites_to_balls(_derived(BASE), [_ball(mid)])
    assert table["shoulder_L"]["matched"] is False
    assert table["elbow_L"]["matched"] is False


def test_one_ball_cannot_be_claimed_by_two_sites():
    """The two hips sit 0.075 apart with tolerances of ~0.086 each, so a ball between them
    is genuinely inside both. Without uniqueness the table would report two confident
    matches to one piece of mesh, and two bones would be moved onto the same point."""
    mid = tuple((np.array(BASE["hip_L"]) + np.array(BASE["hip_R"])) / 2.0)
    _, table = joints.snap_sites_to_balls(_derived(BASE), [_ball(mid)])
    claimed = [k for k, v in table.items() if v["matched"]]
    assert len(claimed) == 1, f"expected exactly one claimant, got {claimed}"
    assert claimed[0] in ("hip_L", "hip_R")


# ------------------------------------------------------- the instrument/subject ruling


def _table_from_offsets(offsets):
    out = {}
    for i, (site, off) in enumerate(offsets.items()):
        out[site] = {"matched": True, "offset": float(np.linalg.norm(off)),
                     "offset_vector": list(off), "offset_as_fraction_of_segment":
                     float(np.linalg.norm(off)) / 0.25}
    return out


def test_uniform_offsets_read_as_the_instrument():
    """Every marker shifted by the same vector is what one wrong transform does."""
    shift = (0.0, 0.0, 0.02)
    r = joints.verdict(_table_from_offsets({f"j{i}": shift for i in range(12)}))
    assert r["ruling"].startswith("THE INSTRUMENT")
    assert r["residual_after_removing_common_translation_max"] < 1e-9


def test_a_spread_of_offsets_reads_as_the_subject():
    """The measured case: ankles 0.004 off, elbows 0.076 off. No single transform does that."""
    offs = {"ankle_L": (0.0, 0.0, 0.004), "ankle_R": (0.0, 0.0, 0.004),
            "hip_L": (0.0, 0.0, 0.010), "knee_L": (0.0, 0.0, 0.024),
            "shoulder_L": (-0.016, 0.0, 0.0), "elbow_L": (0.0, 0.0, 0.074),
            "elbow_R": (0.0, 0.0, 0.076)}
    r = joints.verdict(_table_from_offsets(offs))
    assert r["ruling"].startswith("THE SUBJECT")
    assert r["offset_spread_ratio"] > 3.0


def test_the_ruling_says_so_when_nothing_matched():
    r = joints.verdict({"elbow_L": {"matched": False, "offset": 0.0}})
    assert "NO BALLS MATCHED" in r["ruling"]
