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
    with pytest.raises(LandmarkError,
                       match=r"50 vertices cannot be resolved into 100 bands; the"):
        landmarks.derive(np.random.default_rng(0).uniform(0, 1, size=(50, 3)), n_bands=100)


def test_a_malformed_vertex_array_raises():
    with pytest.raises(LandmarkError,
                       match=r"expected an \(N, 3\) vertex array, got shape \(100, 2\)"):
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
    with pytest.raises(LandmarkError,
                       match=r"the silhouette does not resolve into the expected"):
        landmarks.derive(np.concatenate(parts, axis=0), n_bands=100)


# ------------------------------- the facing cross-check is compared to something now


def _facing_verts(foot_ys, head_ys, shin_ys=(0.0,)):
    """Vertices shaped for `facing(verts, z_ankle=0.06, height=1.0, z_ground=0.0)`.

    Slabs, not a figure: the foot slab is z < 0.03, the shin slab 0.06 <= z < 0.11, the
    head slab z > 0.88. Building them directly is what lets each clause be driven on its
    own — a whole synthetic figure moves several of these at once.
    """
    pts = [(0.0, y, 0.01) for y in foot_ys]
    pts += [(0.0, y, 0.08) for y in shin_ys]
    pts += [(0.0, y, 0.95) for y in head_ys]
    return np.array(pts, dtype=np.float64)


def _facing(foot_ys, head_ys, **kw):
    return landmarks.facing(_facing_verts(foot_ys, head_ys, **kw), 0.06, 1.0, 0.0)


def test_a_foot_that_does_not_separate_forward_from_back_is_refused():
    """F-d876df3f. `sign = 1.0 if fwd > back else -1.0` had NO separation requirement, so
    on an exact tie the sign was taken from the `else` branch — an arbitrary -1 — and
    `left_x_sign = -sign` mirrored the whole downstream chain from it: the gait's forward
    direction and handedness (walk.py reads fy and lx on every bone) and the AAPose-20 L/R
    map, whose own docstring warns that a mirrored reading would produce a solve that
    round-trips perfectly and is wrong. `foot_margin` measured exactly this separation and
    was read by nothing."""
    with pytest.raises(landmarks.FacingGate) as exc:
        _facing(foot_ys=(-0.05, 0.05), head_ys=(-0.08, 0.08))
    assert exc.value.evidence["foot_margin"] == pytest.approx(0.0)
    assert "arbitrary" in str(exc.value) or "tie" in str(exc.value)


def test_the_head_cross_check_is_refused_when_it_separates_better_than_the_feet():
    """`cross_check_agrees` was computed and compared to nothing — a repo-wide grep found
    it in exactly two places, this line and one assertion in this file. The head stays
    ADVISORY (a clay mannequin may have no nose, and a face-derived answer would be noise),
    so the comparison is between the two instruments in their own units: each margin as a
    fraction of its own structure's y-extent. A head that disagrees while separating its
    own front from its own back at least as well as the feet do is not noise."""
    with pytest.raises(landmarks.FacingGate) as exc:
        _facing(foot_ys=(-0.011, 0.010), head_ys=(-0.02, -0.02, 0.20))
    ev = exc.value.evidence
    assert ev["cross_check_agrees"] is False
    assert ev["head_margin_fraction"] >= ev["foot_margin_fraction"]


def test_a_noisy_head_that_disagrees_with_decisive_feet_is_reported_not_refused():
    """The other side, and the reason this is not a raise on `cross_check_agrees` alone:
    the module's own docstring says the head is a cross-check and not a tiebreaker."""
    # A head whose mean sits below its own midpoint by a hair: it reads +1 against the
    # feet's -1, and separates its own front from its own back on 0.3292 of its y-extent
    # against the feet's 0.5385 - measured, both.
    f = _facing(foot_ys=(-0.10, 0.03), head_ys=(-0.08, -0.079, 0.08))
    assert f["facing_y_sign"] == -1.0
    assert f["cross_check_agrees"] is False
    assert f["head_margin_fraction"] < f["foot_margin_fraction"]
    assert "advisory" in f["instrument"]


def test_the_two_margins_ride_the_record_as_fractions_of_their_own_structures():
    """Per-structure, never a length in metres — a global constant must not govern a local
    feature, and a margin in metres would mean different things on a 0.3 m foot and a
    1.8 m one."""
    f = _facing(foot_ys=(-0.10, 0.03), head_ys=(-0.02, -0.02, 0.20))
    assert 0.0 <= f["foot_margin_fraction"] <= 1.0
    assert f["foot_margin_fraction"] == pytest.approx(
        abs(f["foot_forward_extent"] - f["foot_backward_extent"])
        / (f["foot_forward_extent"] + f["foot_backward_extent"]))


# --- F-884c0c8e: the figure's own X centreline, not the world's -----------------------


def _put_x_literals(source=None):
    """Every `put(...)` in `landmarks.derive` whose x coordinate is a bare numeric literal.

    Derived by walking the module's own AST — the population is whatever the source
    contains today, not a list typed into this test — so a landmark newly placed at a
    constant world x joins it the moment it is written.

    WAVE 26, F-a89efade — `source` is the seam that lets the red direction below drive
    THIS walk over a decoy instead of re-implementing it inline. A proof that parses
    its own scratch source and re-writes the predicate demonstrates that `ast` finds
    the node; it cannot fail when the production walk is loosened, which is the one
    thing a red proof exists to make impossible.
    """
    import ast
    import inspect

    src = inspect.getsource(landmarks) if source is None else source
    out = []
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "put" and len(node.args) >= 2):
            continue
        point = node.args[1]
        if not isinstance(point, ast.Tuple) or not point.elts:
            continue
        x = point.elts[0]
        if isinstance(x, ast.Constant) and isinstance(x.value, (int, float)):
            name = node.args[0]
            label = name.value if isinstance(name, ast.Constant) else ast.unparse(name)
            out.append((label, x.value, node.lineno))
    return out


def test_no_landmark_is_placed_at_a_literal_world_x():
    """Census, derived by AST over landmarks.py.

    Nine landmarks — crotch, neck_base, head_base, head_top, shoulder_line, spine_base,
    chest_base, nose, nose_tip — were written at the literal world x = 0.0 while every
    limb landmark was measured off the mesh, so the whole torso and head chain silently
    assumed the subject arrives centred on the world axis (F-884c0c8e). The module's own
    docstring says a global constant must not govern a local feature; a world coordinate
    typed into a placement is exactly that.
    """
    assert _put_x_literals() == [], (
        "landmarks placed at a literal world x: " + repr(_put_x_literals()))


def test_the_literal_world_x_census_goes_red_on_a_reintroduced_constant():
    """Prove the census can fail — driving `_put_x_literals` itself (wave 26, F-a89efade).

    What stood here re-implemented the predicate inline over its own scratch source, so it
    asserted that `ast.walk` finds a `Call` with a `Tuple` first argument. Loosening
    `_put_x_literals` — dropping the `isinstance(x.value, (int, float))` clause, keying on a
    different callee, missing a nested `put` — left this proof green. It calls the production
    walk now, and the decoy carries both directions: one landmark at a literal world x, one
    placed from measured coordinates, so the walk must report exactly the first.
    """
    mutated = (
        "def derive(v):\n"
        "    def put(name, point, prov):\n"
        "        pass\n"
        "    put('crotch', (0.0, 1.0, 2.0), 'MEASURED')\n"
        "    put('hip_L', (cx, cy, cz), 'MEASURED')\n"
    )
    found = _put_x_literals(source=mutated)
    assert [label for label, _x, _line in found] == ["crotch"], (
        "the census would not have caught the reintroduced literal: " + repr(found))
    assert found == [("crotch", 0.0, 4)], found


def _shifted(dx):
    return synthetic_figure() + np.array([dx, 0.0, 0.0])


@pytest.mark.parametrize("dx", [0.0, 0.02, 0.05, 0.08])
def test_the_torso_chain_tracks_the_figure_not_the_world_origin(dx):
    """Measured before the fix on this fixture: at dx = 0.02 / 0.05 / 0.08 on a 1.000-tall
    figure, crotch / spine_base / chest_base / neck_base / head_base / head_top /
    shoulder_line / nose all stayed at x = +0.0000 while hip_L and hip_R moved with the
    mesh, so the `hips` bone head was dislocated from the midpoint of its own two children
    by exactly the offset — invisible to Gate N (names), Gate P (rest pose against itself)
    and Gate D (which reproduces the same wrong skeleton).
    """
    m = landmarks.derive(_shifted(dx), n_bands=100)["landmarks"]
    hip_mid = 0.5 * (m["hip_L"][0] + m["hip_R"][0])
    hip_half = 0.5 * abs(m["hip_L"][0] - m["hip_R"][0])
    for name in ("crotch", "spine_base", "chest_base", "neck_base", "head_base",
                 "head_top", "shoulder_line", "nose"):
        assert abs(m[name][0] - hip_mid) < 0.25 * hip_half, (
            f"{name} sits at x={m[name][0]:.4f}; this figure's own centreline is at "
            f"x={hip_mid:.4f} (dx={dx})")


@pytest.mark.parametrize("dx", [0.02, 0.05, 0.08])
def test_the_head_is_measured_about_its_own_axis_not_the_world_axis(dx):
    """`head_half` was `max(abs(head[:,0].max()), abs(head[:,0].min()))` — a half-width
    about the WORLD origin. Measured before the fix: ear_L / ear_R came back at ±0.0808 at
    dx=0, ±0.1283 at dx=0.05 and ±0.1568 at dx=0.08, a head up to 1.94× too wide with both
    ears symmetric about the world axis rather than about the skull — and aapose reads
    ear_R / ear_L as keypoints 16 / 17, so the pose stick that conditions a generation is
    drawn that wide too.
    """
    base = landmarks.derive(synthetic_figure(), n_bands=100)["landmarks"]
    moved = landmarks.derive(_shifted(dx), n_bands=100)["landmarks"]
    w0 = base["ear_L"][0] - base["ear_R"][0]
    w1 = moved["ear_L"][0] - moved["ear_R"][0]
    assert abs(w1 - w0) < 0.05 * abs(w0), (
        f"ear separation {w1:.4f} at dx={dx} against {w0:.4f} at dx=0")
    for name in ("ear_L", "ear_R", "eye_L", "eye_R"):
        assert abs((moved[name][0] - base[name][0]) - dx) < 0.02, (
            f"{name} did not travel with the mesh: {base[name][0]:.4f} -> "
            f"{moved[name][0]:.4f} for dx={dx}")


@pytest.mark.parametrize("dx", [0.02, 0.05, 0.08])
def test_the_limbs_still_land_on_their_own_limb_when_the_figure_is_off_centre(dx):
    """`side_picker` split left from right on `c["cx"] > 0`, the same world-origin test,
    and the foot slab was split the same way. Both now split about the measured
    centreline, so the sides do not swap and the picker does not starve."""
    m = landmarks.derive(_shifted(dx), n_bands=100)["landmarks"]
    for side, sign in (("L", +1), ("R", -1)):
        for joint in ("shoulder", "elbow", "wrist", "hand_end"):
            assert abs(m[f"{joint}_{side}"][0] - (dx + sign * ARM_X)) < 2.0 * ARM_R
        for joint in ("hip", "knee", "ankle", "toe"):
            assert abs(m[f"{joint}_{side}"][0] - (dx + sign * LEG_X)) < 2.5 * LEG_R


def test_the_measured_centreline_rides_the_record():
    """The premise that used to be silent is now a measurement a report can read."""
    r = landmarks.derive(_shifted(0.05), n_bands=100)["regions"]
    assert abs(r["x_centreline"] - 0.05) < 0.02
    assert abs(r["x_head_centreline"] - 0.05) < 0.02
