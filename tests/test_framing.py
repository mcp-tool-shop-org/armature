"""Tests for the framing solver.

The load-bearing one is `test_half_fovs_matches_blenders`: the solver and the renderer
compute the same field of view from two copies of the same formula, and if they ever drift
the subject lands off the mark with nothing anywhere saying why. The rest ask the usual
question — what would this look like if the code were wrong in the way this catches?
"""

import inspect
import math

import pytest

from armature_core import framing


LENS, SENSOR, W, H = 50.0, 36.0, 832, 480


def test_half_fovs_matches_blenders():
    """`blender_scene` cannot be imported without bpy, so its source is read and the
    function is executed in isolation. Comparing the two implementations is the whole
    point; comparing this one to itself would prove nothing."""
    import os
    path = os.path.join(os.path.dirname(inspect.getfile(framing)), "blender_scene.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    start = src.index("def half_fovs(")
    end = src.index("\ndef ", start + 1)
    ns = {"math": math}
    exec(compile(src[start:end], "blender_scene.half_fovs", "exec"), ns)  # noqa: S102
    theirs = ns["half_fovs"]
    for w, h in ((832, 480), (480, 832), (512, 512), (1280, 720)):
        assert framing.half_fovs(LENS, SENSOR, w, h) == theirs(LENS, SENSOR, w, h)


def test_the_target_projects_to_the_centre_of_frame():
    """The camera looks AT the target. If it did not, every offset the solver computes
    would be measured from the wrong origin."""
    t = (0.3, -1.1, 0.2)
    x, y, ok = framing.project(t, t, 3.0, 205.0, 6.0, LENS, SENSOR, W, H)
    assert ok
    assert x == pytest.approx(0.5, abs=1e-9)
    assert y == pytest.approx(0.5, abs=1e-9)


def test_a_point_behind_the_camera_is_reported_not_wrapped():
    """A perspective divide by a negative depth silently mirrors the point into frame.
    Reporting `in_front=False` is what stops a subject behind the lens being 'framed'."""
    t = (0.0, 0.0, 0.0)
    behind = framing.camera_position(t, 3.0, 6.0, 205.0)
    beyond = tuple(c * 2.0 for c in behind)
    _, _, ok = framing.project(beyond, t, 3.0, 205.0, 6.0, LENS, SENSOR, W, H)
    assert ok is False


def test_screen_axes_point_the_way_a_composition_is_discussed():
    """x grows to the right, y grows DOWNWARD. A y that grew upward would put every
    'headroom' number upside down and the shot would be composed at his feet."""
    t = (0.0, 0.0, 0.0)
    az, el = 205.0, 0.0
    pos = framing.camera_position(t, 3.0, el, az)
    right, up, _ = framing.camera_basis(t, pos)
    x_r, y_r, _ = framing.project(right, t, 3.0, az, el, LENS, SENSOR, W, H)
    x_u, y_u, _ = framing.project(up, t, 3.0, az, el, LENS, SENSOR, W, H)
    assert x_r > 0.5 and y_r == pytest.approx(0.5, abs=1e-9)
    assert y_u < 0.5 and x_u == pytest.approx(0.5, abs=1e-9)


def test_a_character_facing_minus_y_walks_screen_right_at_azimuth_205():
    """The shot's premise, checked rather than assumed. If this were false the whole
    performance would run right-to-left and the bar would be on the wrong side."""
    t = (0.0, 0.0, 0.0)
    start, end = (0.0, 0.0, 0.0), (0.0, -1.0, 0.0)   # one unit forward for a -Y facer
    xs, _, _ = framing.project(start, t, 4.0, 205.0, 6.0, LENS, SENSOR, W, H)
    xe, _, _ = framing.project(end, t, 4.0, 205.0, 6.0, LENS, SENSOR, W, H)
    assert xe > xs


def test_solve_hits_the_requested_composition():
    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5), (0.15, 0.0, 0.0), (-0.15, 0.0, 0.0)]
    walk_path = [tuple(p[i] + (0.0, -1.27, 0.0)[i] * k for i in range(3))
                 for k in (0.0, 0.5, 1.0) for p in body]
    end = [tuple(p[i] + (0.0, -1.27, 0.0)[i] for i in range(3)) for p in body]
    sol = framing.solve_camera(walk_path, end, 205.0, 6.0, LENS, SENSOR, W, H,
                               height_frac=0.68, end_x_frac=0.67, target_y_frac=0.52)
    a = sol["achieved"]
    assert a["union_height_frac"] == pytest.approx(0.68, abs=1e-3)
    assert a["end_centre_x"] == pytest.approx(0.67, abs=1e-3)
    assert 0.5 * (a["union_y"][0] + a["union_y"][1]) == pytest.approx(0.52, abs=1e-3)
    assert sol["radius"] > 0.0


def test_a_bigger_height_fraction_needs_a_closer_camera():
    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5)]
    near = framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                                height_frac=0.85, end_x_frac=0.5)
    far = framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                               height_frac=0.40, end_x_frac=0.5)
    assert near["radius"] < far["radius"]


def test_an_unreachable_framing_raises_rather_than_returning_its_nearest_miss():
    """A solver that silently returns a bound looks like it succeeded. This is the
    difference between a shot that is framed and a shot that is merely rendered."""
    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5)]
    with pytest.raises(framing.FramingError,
                       match=r"the requested framing is not reachable between 20\.0 and"):
        framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                             height_frac=0.68, end_x_frac=0.5,
                             radius_bounds=(20.0, 40.0))


def test_a_straight_down_camera_raises():
    t = (0.0, 0.0, 0.0)
    with pytest.raises(framing.FramingError,
                       match=r"the camera is looking straight up or down; the up vector"):
        framing.project((0.1, 0.0, 0.0), t, 3.0, 0.0, 90.0, LENS, SENSOR, W, H)


# --- F-6a8edff0: the two final extents are guarded like every other ---------------------


def _deep_cloud_case():
    """A composition whose converged solution puts a union point behind the lens.

    Found by sweeping depth x end-cloud offset x height_frac x target_y_frac; the fixture
    the finding suggested (a large `height_frac` on a deep cloud) does NOT reach the
    branch, because the radius and vertical solves are both driven by `all_points` and
    self-correct. What reaches it is a deep union cloud whose target is pulled toward the
    top of frame after the last radius solve.
    """
    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5), (0.2, -20.0, 0.0), (-0.2, 20.0, 0.0)]
    end = [(0.0, 6.0, -0.5), (0.0, 6.0, 0.5)]
    return body, end


def test_an_unreachable_composition_raises_a_framing_error_not_a_nonetype_traceback():
    """Measured on this tree before the fix: this exact call raised
    `TypeError: 'NoneType' object is not subscriptable` from the middle of a dict literal.
    `_extent` returns None as soon as any point projects behind the camera; the three
    bisection closures each substitute the 99.0 sentinel and the two final calls indexed
    the result unguarded, where every other refusal in this module names what went wrong.
    """
    body, end = _deep_cloud_case()
    with pytest.raises(framing.FramingError, match=r"unreachable") as exc:
        framing.solve_camera(body, end, 205.0, 6.0, LENS, SENSOR, W, H,
                             height_frac=0.9, end_x_frac=0.5, target_y_frac=0.3,
                             radius_bounds=(0.05, 60.0))
    msg = str(exc.value)
    assert "BEHIND the camera" in msg
    assert "union" in msg
    assert "radius" in msg and "offset" in msg


def test_the_end_cloud_gets_the_same_refusal_and_is_named_separately(monkeypatch):
    """The `end` half of the guard, driven by making only the LAST evaluation of the end
    cloud fail — the shape the finding names: `x_of` solves the lateral offset at the
    PREVIOUS pass's vertical offset, so the final `end` extent is measured at a target no
    closure ever evaluated.
    """
    real = framing._extent
    state = {"n": 0}

    def counting(points, *args, **kw):
        state["n"] += 1
        return real(points, *args, **kw)

    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5)]
    monkeypatch.setattr(framing, "_extent", counting)
    framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                         height_frac=0.68, end_x_frac=0.5)
    total = state["n"]                       # the last call is the `end` extent

    state["n"] = 0

    def fail_last(points, *args, **kw):
        state["n"] += 1
        if state["n"] == total:
            return None
        return real(points, *args, **kw)

    monkeypatch.setattr(framing, "_extent", fail_last)
    with pytest.raises(framing.FramingError, match=r"unreachable") as exc:
        framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                             height_frac=0.68, end_x_frac=0.5)
    assert "end point cloud" in str(exc.value)


def test_the_guard_does_not_fire_on_a_composition_that_is_reachable():
    """Both directions: a solve that converges must still return its numbers."""
    body = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5), (0.15, 0.0, 0.0), (-0.15, 0.0, 0.0)]
    sol = framing.solve_camera(body, body, 205.0, 6.0, LENS, SENSOR, W, H,
                               height_frac=0.68, end_x_frac=0.5)
    assert sol["achieved"]["union_height_frac"] == pytest.approx(0.68, abs=1e-3)
