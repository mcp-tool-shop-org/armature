"""Landmark derivation, against a synthetic figure whose anatomy is known by construction.

The subject this ran on is a 400k-vertex clay mannequin with no ground truth anywhere: if
the derivation puts the elbow in the wrong place, the rig still builds, Gate N still passes,
Gate P still reads zero and Gate D still reproduces the wrong elbow perfectly. Nothing in
the pipeline can see it. So the derivation is tested against a figure assembled from known
numbers, where "the shoulder is at x = 0.20" is a fact rather than a hope.
"""

import numpy as np
import pytest

from armature_core import landmarks
from armature_core.errors import LandmarkError

# The synthetic figure, in the same convention as the real subject: Z up, facing -Y.
GROUND, TOP = 0.0, 1.0
ANKLE_Z, HAND_BOTTOM_Z, CROTCH_Z, ARMPIT_Z = 0.06, 0.24, 0.50, 0.76
NECK_TOP_Z, HEAD_BASE_Z = 0.84, 0.88
LEG_X, LEG_R = 0.09, 0.045
ARM_X, ARM_R = 0.20, 0.035
FOOT_RX, FOOT_RY, FOOT_Y = 0.075, 0.065, -0.035


def _ecyl(x0, y0, rx, ry, z0, z1, na=256):
    """An elliptical shell, sampled densely enough that its own X distribution has no
    gap wider than the clustering threshold.

    `na` is not cosmetic. At 32 angles the widest structure's X samples are spaced ~0.023
    apart near the ellipse's flanks — wider than the 2%-of-width gap threshold — so the
    clusterer split every single part in two and the figure read as having four legs. The
    defect was in the fixture, not in the derivation, which is exactly why a fixture built
    from known numbers is worth having.
    """
    nz = max(40, int(round(200 * (z1 - z0))))
    z = np.linspace(z0, z1, nz)
    a = np.linspace(0.0, 2.0 * np.pi, na, endpoint=False)
    Z, A = np.meshgrid(z, a, indexing="ij")
    return np.stack([x0 + rx * np.cos(A), y0 + ry * np.sin(A), Z], axis=-1).reshape(-1, 3)


def synthetic_figure(mirror_y=False):
    parts = [
        _ecyl(0.0, 0.0, 0.115, 0.075, CROTCH_Z, ARMPIT_Z),          # torso
        _ecyl(0.0, 0.0, 0.240, 0.090, ARMPIT_Z, NECK_TOP_Z),        # shoulder block
        _ecyl(0.0, 0.0, 0.035, 0.035, NECK_TOP_Z, HEAD_BASE_Z),     # neck
        _ecyl(0.0, 0.0, 0.085, 0.085, HEAD_BASE_Z, TOP),            # head
    ]
    for s in (+1, -1):
        parts += [
            _ecyl(s * LEG_X, 0.0, LEG_R, LEG_R, ANKLE_Z, CROTCH_Z),            # leg
            _ecyl(s * LEG_X, FOOT_Y, FOOT_RX, FOOT_RY, GROUND, ANKLE_Z),       # foot
            _ecyl(s * ARM_X, 0.0, ARM_R, ARM_R, HAND_BOTTOM_Z, ARMPIT_Z + 0.04),
        ]
    verts = np.concatenate(parts, axis=0)
    if mirror_y:
        verts = verts * np.array([1.0, -1.0, 1.0])
    return verts


def _derive(verts=None, **kw):
    return landmarks.derive(synthetic_figure() if verts is None else verts,
                            n_bands=kw.pop("n_bands", 100))


def test_the_region_transitions_are_found_where_they_were_built():
    r = _derive()["regions"]
    tol = 0.02  # one band at n_bands=100
    assert abs(r["z_ground"] - GROUND) < 1e-6
    assert abs(r["z_top"] - TOP) < 1e-6
    assert abs(r["z_hand_bottom"] - HAND_BOTTOM_Z) < tol
    assert abs(r["z_crotch"] - CROTCH_Z) < tol
    assert abs(r["z_armpit"] - ARMPIT_Z) < tol
    assert abs(r["z_ankle"] - ANKLE_Z) < tol


def test_the_neck_is_found_between_the_shoulders_and_the_head():
    r = _derive()["regions"]
    assert NECK_TOP_Z < r["z_neck_min"] < HEAD_BASE_Z
    assert abs(r["neck_min_width"] - 0.07) < 0.02
    assert abs(r["z_neck_base"] - NECK_TOP_Z) < 0.03
    assert abs(r["z_head_base"] - HEAD_BASE_Z) < 0.03


def test_facing_is_read_off_the_toes_and_the_head_agrees():
    f = _derive()["facing"]
    assert f["facing_y_sign"] == -1.0          # toes were built pointing -Y
    assert f["left_x_sign"] == +1.0            # so the character's left is +X
    assert f["cross_check_agrees"] is True


def test_facing_flips_when_the_figure_is_mirrored():
    """A facing test that only ever sees one orientation cannot fail."""
    f = landmarks.derive(synthetic_figure(mirror_y=True), n_bands=100)["facing"]
    assert f["facing_y_sign"] == +1.0
    assert f["left_x_sign"] == -1.0


def test_limb_joints_land_on_their_own_limb():
    m = _derive()["landmarks"]
    for side, sign in (("L", +1), ("R", -1)):
        for joint in ("shoulder", "elbow", "wrist", "hand_end"):
            x = m[f"{joint}_{side}"][0]
            assert abs(x - sign * ARM_X) < 2.0 * ARM_R, f"{joint}_{side} is off its arm"
        for joint in ("hip", "knee", "ankle"):
            x = m[f"{joint}_{side}"][0]
            assert abs(x - sign * LEG_X) < 2.5 * LEG_R, f"{joint}_{side} is off its leg"


def test_joints_are_ordered_down_each_limb():
    m = _derive()["landmarks"]
    for side in ("L", "R"):
        zs = [m[f"{j}_{side}"][2] for j in ("shoulder", "elbow", "wrist", "hand_end")]
        assert zs == sorted(zs, reverse=True), f"arm {side} joints are out of order: {zs}"
        zs = [m[f"{j}_{side}"][2] for j in ("hip", "knee", "ankle", "toe")]
        assert zs == sorted(zs, reverse=True), f"leg {side} joints are out of order: {zs}"


def test_the_left_and_right_sides_mirror_on_a_symmetric_figure():
    m = _derive()["landmarks"]
    for base in ("shoulder", "elbow", "wrist", "hand_end", "hip", "knee", "ankle"):
        a, b = m[f"{base}_L"], m[f"{base}_R"]
        assert abs(a[0] + b[0]) < 0.01, f"{base} is not mirrored in x"
        assert abs(a[2] - b[2]) < 0.01, f"{base} is not mirrored in z"


def test_every_landmark_declares_whether_it_was_measured_or_derived():
    d = _derive()
    for name in d["landmarks"]:
        p = d["provenance"][name]
        assert p.startswith("MEASURED") or p.startswith("DERIVED"), f"{name}: {p!r}"


def test_the_eyes_and_ears_say_out_loud_that_no_feature_was_measured():
    """They are placed at fractions of the head because a clay mannequin has no eyes and
    no ears. A report that presented them as measurements would be making one up."""
    d = _derive()
    for name in ("eye_L", "eye_R", "ear_L", "ear_R"):
        assert "NO EYE FEATURE" in d["provenance"][name] or \
               "NO EAR FEATURE" in d["provenance"][name]


# --- the defect this instrument was measured to have, 2026-08-11 ---------------------


def _bridged_figure(z0=0.60, z1=0.615):
    """A figure whose right arm touches its torso across two bands.

    This is the real defect, reproduced: on the subject, bands 109 and 110 merged the
    right arm into the trunk because the gap fell under the clustering threshold. The
    picker returned a trunk-plus-arm blob whose centroid sat near the body's centreline,
    that one point added ~0.30 of spurious arc length to a 0.55-long limb, and the elbow
    placed at 0.44 along landed almost on the spine. Every count and every gate stayed
    green — the rig built, all 22 names checked out, the rest pose was preserved and the
    build reproduced exactly, with the elbow in the wrong place.
    """
    base = synthetic_figure()
    z = np.linspace(z0, z1, 12)
    x = np.linspace(-(ARM_X - ARM_R), -0.115, 40)
    Z, X = np.meshgrid(z, x, indexing="ij")
    bridge = np.stack([X, np.zeros_like(X), Z], axis=-1).reshape(-1, 3)
    return np.concatenate([base, bridge], axis=0)


def test_a_band_where_a_limb_touches_the_body_does_not_drag_the_joint_off_it():
    m = landmarks.derive(_bridged_figure(), n_bands=100)["landmarks"]
    assert abs(m["elbow_R"][0] + ARM_X) < 2.0 * ARM_R, (
        f"elbow_R landed at x={m['elbow_R'][0]:.4f}; the right arm's centreline is at "
        f"x={-ARM_X}. A merged band dragged the arc-length parameterisation off the limb."
    )
    assert abs(m["wrist_R"][0] + ARM_X) < 2.0 * ARM_R


def test_the_unbridged_and_bridged_figures_agree_on_the_right_elbow():
    """The stronger form: contact with the body must not move the joint at all."""
    clean = landmarks.derive(synthetic_figure(), n_bands=100)["landmarks"]
    bridged = landmarks.derive(_bridged_figure(), n_bands=100)["landmarks"]
    assert abs(clean["elbow_R"][0] - bridged["elbow_R"][0]) < 0.5 * ARM_R


# --- refusals ------------------------------------------------------------------------


def test_a_subject_that_is_not_a_standing_figure_raises_instead_of_guessing():
    """A sphere has no limbs. Placing bones on it anyway would produce a rig whose every
    gate is green and whose every joint is invented."""
    a = np.linspace(0, np.pi, 200)
    b = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    A, B = np.meshgrid(a, b, indexing="ij")
    ball = np.stack([np.sin(A) * np.cos(B), np.sin(A) * np.sin(B), np.cos(A)],
                    axis=-1).reshape(-1, 3)
    with pytest.raises(LandmarkError) as exc:
        landmarks.derive(ball, n_bands=100)
    assert "standing figure" in str(exc.value)


def test_a_vertex_array_too_sparse_to_band_raises():
    with pytest.raises(LandmarkError):
        landmarks.derive(np.random.default_rng(0).uniform(0, 1, size=(50, 3)), n_bands=100)


def test_a_malformed_vertex_array_raises():
    with pytest.raises(LandmarkError):
        landmarks.band_profile(np.zeros((100, 2)), n_bands=10)


def test_an_arm_that_never_separates_from_the_body_raises():
    """A figure with its arms fully fused to the torso presents no arm column; the
    derivation must refuse rather than read a centreline off the trunk."""
    parts = [
        _ecyl(0.0, 0.0, 0.115, 0.075, CROTCH_Z, ARMPIT_Z),
        _ecyl(0.0, 0.0, 0.240, 0.090, ARMPIT_Z, NECK_TOP_Z),
        _ecyl(0.0, 0.0, 0.035, 0.035, NECK_TOP_Z, HEAD_BASE_Z),
        _ecyl(0.0, 0.0, 0.085, 0.085, HEAD_BASE_Z, TOP),
    ]
    for s in (+1, -1):
        parts += [
            _ecyl(s * LEG_X, 0.0, LEG_R, LEG_R, ANKLE_Z, CROTCH_Z),
            _ecyl(s * LEG_X, FOOT_Y, FOOT_RX, FOOT_RY, GROUND, ANKLE_Z),
        ]
    with pytest.raises(LandmarkError):
        landmarks.derive(np.concatenate(parts, axis=0), n_bands=100)
