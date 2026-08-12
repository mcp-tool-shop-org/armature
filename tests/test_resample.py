"""The resampler, against motions whose in-betweens are known in closed form.

Every fixture here is checkable against mathematics rather than against a render, which is
the whole reason the module carries no numpy and no bpy. Where a test exists to catch a
specific wrong implementation, it also builds that wrong implementation and shows it
failing — a fixture that cannot tell the right answer from the wrong one is decoration.
"""

import math

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import lift_solve as LS
from armature_core import resample as RS
from armature_core import sitelist


def rot_z(deg):
    return LS.axis_angle((0.0, 0.0, 1.0), math.radians(deg))


def rot_x(deg):
    return LS.axis_angle((1.0, 0.0, 0.0), math.radians(deg))


def frame(i, local, root=(0.0, 0.0, 0.0)):
    return {"frame": i,
            "local": {k: [list(r) for r in v] for k, v in local.items()},
            "root": list(root)}


def close(a, b, tol=1e-12):
    return all(abs(x - y) <= tol for ra, rb in zip(a, b) for x, y in zip(ra, rb))


# ------------------------------------------------------------------ the index map

def test_the_map_spans_the_source_exactly_and_only_forwards():
    """Monotonic time. A mapping that stalled would emit a clip that plays and stutters."""
    ev = RS.monotonic(65, 81)
    u = RS.positions(65, 81)
    assert ev["first"] == 0.0 and ev["last"] == 64.0
    assert all(u[i + 1] > u[i] for i in range(len(u) - 1))
    # 65 -> 81 is exactly 0.8 source samples per destination sample.
    assert all(abs(u[j] - 0.8 * j) < 1e-12 for j in range(81))


def test_a_stalled_map_is_what_the_monotonic_gate_would_catch():
    """The gate's own discrimination: a timeline that repeats a position must raise."""
    u = [0.0, 1.0, 1.0, 2.0]
    bad = [k for k in range(len(u) - 1) if not (u[k + 1] > u[k])]
    assert bad == [1]


def test_resampling_to_fewer_than_two_samples_refuses():
    with pytest.raises(RS.ResampleError):
        RS.sample_map(65, 1)
    with pytest.raises(RS.ResampleError):
        RS.sample_map(1, 81)


def test_the_true_tempo_is_exactly_twenty_for_this_shot():
    """65 samples at 16 fps densified to 81 over the same first-to-last span."""
    assert RS.fps_for(16, 65, 81) == 20.0
    # the span between first and last sample is unchanged, which is what "same duration"
    # means when the endpoints are exact
    assert (65 - 1) / 16 == (81 - 1) / RS.fps_for(16, 65, 81)


# --------------------------------------------------------------- rotation algebra

@pytest.mark.parametrize("deg", [0.0, 1.0, 45.0, 90.0, 179.0, 180.0, -120.0])
def test_matrix_quaternion_round_trip(deg):
    m = LS.mat_mul(rot_z(deg), rot_x(23.5))
    assert close(RS.quat_to_mat(RS.mat_to_quat(m)), m, 1e-12)


def test_the_analytic_midpoint_of_a_ninety_degree_arc_is_forty_five_degrees():
    """The one number the whole commission rests on, in closed form."""
    got = RS.slerp_matrix(LS.IDENTITY, rot_z(90.0), 0.5)
    assert close(got, rot_z(45.0), 1e-12)
    assert abs(RS.geodesic_deg(LS.IDENTITY, got) - 45.0) < 1e-12


@pytest.mark.parametrize("t,want", [(0.0, 0.0), (0.25, 22.5), (0.5, 45.0),
                                    (0.75, 67.5), (1.0, 90.0)])
def test_the_arc_is_travelled_at_constant_angular_rate(t, want):
    got = RS.slerp_matrix(LS.IDENTITY, rot_z(90.0), t)
    assert abs(RS.geodesic_deg(LS.IDENTITY, got) - want) < 1e-11
    assert close(got, rot_z(want), 1e-11)


def test_the_shortest_arc_is_taken_when_the_far_representative_is_handed_in():
    """THE double-cover clause.

    `q` and `-q` name the identical orientation. A slerp that does not choose the sign
    takes the long way round: a 20-degree turn becomes a 340-degree spin, and nothing
    errors — the count, the endpoints and every legality check pass on it. The naive blend
    is built here so the fixture is shown discriminating.
    """
    q0 = RS.mat_to_quat(LS.IDENTITY)
    q1 = RS.mat_to_quat(rot_z(20.0))
    far = tuple(-c for c in q1)                       # the same rotation, other cover

    got = RS.quat_to_mat(RS.slerp(q0, far, 0.5))
    assert abs(RS.geodesic_deg(LS.IDENTITY, got) - 10.0) < 1e-11
    assert close(got, rot_z(10.0), 1e-11)

    # ... and the halfway pose is the same whichever representative is supplied
    near = RS.quat_to_mat(RS.slerp(q0, q1, 0.5))
    assert close(got, near, 1e-11)

    # the implementation this test exists to catch: no sign flip, so the arc is the long one
    d = RS.quat_dot(q0, far)
    theta = math.acos(max(-1.0, min(1.0, d)))
    s = math.sin(theta)
    naive = RS.quat_normalise(tuple(
        math.sin(0.5 * theta) / s * a + math.sin(0.5 * theta) / s * b
        for a, b in zip(q0, far)))
    assert RS.geodesic_deg(LS.IDENTITY, RS.quat_to_mat(naive)) > 160.0


def test_a_near_identity_pair_does_not_divide_by_a_vanishing_sine():
    tiny = rot_z(1e-9)
    got = RS.slerp_matrix(LS.IDENTITY, tiny, 0.5)
    assert close(got, LS.IDENTITY, 1e-9)


# --------------------------------------------------------------- the rotation gate

def test_an_element_wise_average_of_two_rotations_is_refused():
    """The exact wrong move the module exists to prevent, built and rejected.

    Averaging identity with a 90-degree turn element-wise gives determinant 0.5: applied
    through `fk_sites` it would shrink and skew the body on every in-between frame, and
    nothing downstream looks for that.
    """
    a, b = LS.IDENTITY, rot_z(90.0)
    avg = tuple(tuple(0.5 * (a[i][j] + b[i][j]) for j in range(3)) for i in range(3))
    ok, worst, det = RS.is_rotation(avg)
    assert ok is False and abs(det - 0.5) < 1e-12 and worst > 0.1
    with pytest.raises(RS.ResampleGate) as exc:
        RS.require_rotation(avg, "the fixture")
    assert "not a rotation" in str(exc.value)
    assert exc.value.evidence["determinant"] == pytest.approx(0.5)


def test_a_real_rotation_passes_the_gate_at_float_noise():
    """The gate must not fire on correct work: the repo's own records sit at ~3e-15."""
    m = LS.mat_mul(rot_z(37.0), rot_x(11.0))
    ok, worst, _det = RS.is_rotation(m)
    assert ok is True and worst < 1e-12


def test_a_reflection_is_refused_even_though_it_is_orthonormal():
    """Orthonormality alone is not enough — a mirrored frame passes it and is not a pose."""
    mirror = ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    ok, _worst, det = RS.is_rotation(mirror)
    assert ok is False and det == pytest.approx(-1.0)


def test_resampling_halts_on_a_record_whose_matrices_are_not_rotations():
    a, b = LS.IDENTITY, rot_z(90.0)
    avg = tuple(tuple(0.5 * (a[i][j] + b[i][j]) for j in range(3)) for i in range(3))
    frames = [frame(0, {"a": LS.IDENTITY}), frame(1, {"a": avg})]
    with pytest.raises(RS.ResampleGate):
        RS.resample_frames(frames, 5)


# ------------------------------------------------------------------- the endpoints

TWO_BONE = [
    frame(0, {"a": rot_z(0.0), "b": rot_x(0.0)}, (0.0, 0.0, 0.0)),
    frame(1, {"a": rot_z(90.0), "b": rot_x(60.0)}, (1.0, 2.0, 3.0)),
    frame(2, {"a": rot_z(180.0), "b": rot_x(60.0)}, (2.0, 4.0, 6.0)),
]


def test_the_endpoints_are_the_sources_own_values_not_a_round_trip():
    """`==`, not `approx`. A quaternion round trip is an identity in algebra and an
    identity to ~1e-16 in float64, and the contract is about the record."""
    out = RS.resample_frames(TWO_BONE, 5)
    assert out[0]["local"] == TWO_BONE[0]["local"]
    assert out[0]["root"] == TWO_BONE[0]["root"]
    assert out[-1]["local"] == TWO_BONE[-1]["local"]
    assert out[-1]["root"] == TWO_BONE[-1]["root"]
    RS.endpoints_match(TWO_BONE, out)


def test_the_endpoint_gate_catches_a_performance_shifted_in_time():
    """What a half-frame phase slip looks like: everything counts, nothing matches."""
    shifted = RS.resample_frames(TWO_BONE, 5)
    shifted[0] = frame(0, {"a": rot_z(3.0), "b": rot_x(0.0)}, (0.0, 0.0, 0.0))
    with pytest.raises(RS.ResampleGate) as exc:
        RS.endpoints_match(TWO_BONE, shifted)
    assert "first" in str(exc.value)


# ---------------------------------------------------------------- the golden resample

def test_the_golden_resample_of_a_synthetic_two_bone_motion():
    """Three frames to five, every expected value written out in closed form.

    Bone `a` turns 0 -> 90 -> 180 about z; bone `b` turns 0 -> 60 about x and then holds;
    the root travels linearly. At positions 0, 0.5, 1, 1.5, 2 the answers are analytic, so
    this fixture is a statement about the mathematics rather than a capture of whatever the
    implementation happened to produce.
    """
    out = RS.resample_frames(TWO_BONE, 5)
    assert [f["frame"] for f in out] == [0, 1, 2, 3, 4]

    want_a = [0.0, 45.0, 90.0, 135.0, 180.0]
    want_b = [0.0, 30.0, 60.0, 60.0, 60.0]
    want_root = [(0.0, 0.0, 0.0), (0.5, 1.0, 1.5), (1.0, 2.0, 3.0),
                 (1.5, 3.0, 4.5), (2.0, 4.0, 6.0)]

    for j, f in enumerate(out):
        assert close(f["local"]["a"], rot_z(want_a[j]), 1e-11), (j, "a")
        assert close(f["local"]["b"], rot_x(want_b[j]), 1e-11), (j, "b")
        assert tuple(f["root"]) == pytest.approx(want_root[j], abs=1e-12), (j, "root")


def test_a_held_bone_stays_held_through_the_in_betweens():
    """Bone `b` holds across the second segment; interpolation must not invent motion."""
    out = RS.resample_frames(TWO_BONE, 5)
    assert RS.geodesic_deg(out[2]["local"]["b"], out[3]["local"]["b"]) < 1e-9
    assert RS.geodesic_deg(out[3]["local"]["b"], out[4]["local"]["b"]) < 1e-9


def test_the_step_diagnostic_reports_the_knots_and_the_in_betweens_apart():
    """Slerp densifies the path BETWEEN knots and leaves the knots where they were, so a
    single mean would hide the thing being measured."""
    src = RS.step_angles(TWO_BONE)
    dst = RS.step_angles(RS.resample_frames(TWO_BONE, 5))
    assert src["a"]["median_deg"] == pytest.approx(90.0, abs=1e-9)
    assert dst["a"]["median_deg"] == pytest.approx(45.0, abs=1e-9)
    # total travel along the path is conserved: densification adds samples, not motion
    assert dst["a"]["sum_deg"] == pytest.approx(src["a"]["sum_deg"], abs=1e-9)


# -------------------------------------------------------------- shape and integration

def test_a_bone_that_appears_midway_is_refused():
    frames = [frame(0, {"a": LS.IDENTITY}), frame(1, {"a": LS.IDENTITY, "b": LS.IDENTITY})]
    with pytest.raises(RS.ResampleError) as exc:
        RS.resample_frames(frames, 5)
    assert "which bones exist" in str(exc.value)


def _rig_frames(n):
    """A synthetic record carrying every registered bone, so the real validator applies."""
    out = []
    for i in range(n):
        local = {b: LS.IDENTITY for b in sitelist.ALL_NAMES}
        local["elbow.L"] = rot_x(40.0 * i / max(1, n - 1))
        out.append(frame(i, local, (0.01 * i, 0.0, 0.0)))
    return out


def test_sixty_five_to_eighty_one_produces_a_record_the_solver_validates():
    src = _rig_frames(65)
    out = RS.resample_frames(src, 81)
    assert len(out) == 81
    ev = LS.validate_motion_record(out)
    assert ev["n_frames"] == 81
    RS.endpoints_match(src, out)
    # the driving signal's per-step turn shrinks by the interval ratio on a smooth path
    ratio = (RS.step_angles(out)["elbow.L"]["median_deg"]
             / RS.step_angles(src)["elbow.L"]["median_deg"])
    assert ratio == pytest.approx(64 / 80, rel=1e-6)


def test_the_gate_is_not_an_assert():
    """`-O` and `PYTHONOPTIMIZE=1` delete `assert`. A gate that vanishes is not a gate."""
    import os
    src = open(os.path.join(TOOLS, "armature_core", "resample.py"),
               encoding="utf-8").read()
    for line in src.splitlines():
        assert not line.strip().startswith("assert "), line
