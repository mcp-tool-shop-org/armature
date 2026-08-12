"""Where to put the camera so the shot is composed rather than merely fitted.

No bpy. The projection here reproduces `blender_scene.orbit_matrix` + Blender's AUTO
sensor fit exactly, so a framing solved here can be checked against the render's own
`projected_bbox` in the manifest afterwards — and it is, every run.

**Why this exists at all.** `stage_render`'s `auto` radius fits the union of every frame
with a margin. That is right for a turnaround and wrong for a travelling shot: a figure
that walks 1.27 of his own heights makes the union nearly three bodies wide, so auto-fit
pulls back until he is a doll. E03 already had to pin target and radius numerically for a
different reason; this makes the pinning derivable instead of typed.

**And a composition is a choice, so it is stated as one.** The two things the Director's
shot needs — he reads as a mid-shot, and he arrives at the right third — cannot both be
dialled independently: the walk distance is fixed, so once the radius sets his size it has
also set how far across the frame he travels. Size wins and the traverse follows. That
trade is in `solve_camera`'s signature, not buried in it.
"""

import math

WORLD_UP = (0.0, 0.0, 1.0)


class FramingError(ValueError):
    """The shot could not be framed as asked."""


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    if n < 1e-12:
        raise FramingError("cannot normalise a zero-length direction")
    return _scale(a, 1.0 / n)


def half_fovs(lens_mm, sensor_mm, width, height):
    """Half field of view per axis, matching Blender's AUTO sensor fit.

    Copied in form from `blender_scene.half_fovs` deliberately: if the two ever disagree,
    the framing solved here and the framing rendered there would differ, and the only
    symptom would be a subject slightly off the mark with nothing pointing at why.
    `tests/test_framing.py` pins them against each other.
    """
    if width >= height:
        sx = sensor_mm
        sy = sensor_mm * height / width
    else:
        sy = sensor_mm
        sx = sensor_mm * width / height
    return math.atan(sx * 0.5 / lens_mm), math.atan(sy * 0.5 / lens_mm)


def camera_position(target, radius, elevation_deg, azimuth_deg):
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    return _add(target, (radius * math.cos(el) * math.cos(az),
                         radius * math.cos(el) * math.sin(az),
                         radius * math.sin(el)))


def camera_basis(target, position):
    """(right, up, back) unit axes, matching `to_track_quat('-Z', 'Y')`.

    The camera looks along its own -Z with +Y as near world up as it can manage, which is
    a Gram-Schmidt of world +Z against the view direction.
    """
    back = _norm(_sub(position, target))            # camera local +Z
    up_hint = WORLD_UP
    proj = _sub(up_hint, _scale(back, _dot(up_hint, back)))
    if math.sqrt(_dot(proj, proj)) < 1e-9:
        raise FramingError(
            "the camera is looking straight up or down; the up vector is undefined and "
            "the roll of the shot would be arbitrary")
    up = _norm(proj)
    right = _cross(up, back)
    return right, up, back


def project(point, target, radius, azimuth_deg, elevation_deg,
            lens_mm, sensor_mm, width, height):
    """Screen fractions (x right, y down) of a world point, plus whether it is in front.

    (0, 0) is the top-left corner and (1, 1) the bottom-right, so the numbers read the way
    a composition is discussed: "he arrives at 0.67" is two thirds across.
    """
    pos = camera_position(target, radius, elevation_deg, azimuth_deg)
    right, up, back = camera_basis(target, pos)
    v = _sub(point, pos)
    z = _dot(v, back)          # positive means behind the camera
    if z >= -1e-9:
        return None, None, False
    hx, hy = half_fovs(lens_mm, sensor_mm, width, height)
    ndc_x = (_dot(v, right) / -z) / math.tan(hx)
    ndc_y = (_dot(v, up) / -z) / math.tan(hy)
    return 0.5 + 0.5 * ndc_x, 0.5 - 0.5 * ndc_y, True


def _extent(points, target, radius, az, el, lens, sensor, width, height):
    """(x0, x1, y0, y1) screen bounds of a point cloud, or None if any point is behind."""
    xs, ys = [], []
    for p in points:
        x, y, ok = project(p, target, radius, az, el, lens, sensor, width, height)
        if not ok:
            return None
        xs.append(x)
        ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)


def _bisect(f, lo, hi, want, iters=80):
    """Solve f(t) = want on a monotone f. Bisection, because it cannot diverge and the
    residuals here are smooth but not analytically invertible."""
    flo, fhi = f(lo), f(hi)
    if (flo - want) * (fhi - want) > 0:
        raise FramingError(
            f"the requested framing is not reachable between {lo} and {hi}: the value "
            f"runs {flo:.4f}..{fhi:.4f} and {want:.4f} is outside it")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if (f(lo) - want) * (f(mid) - want) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def solve_camera(all_points, end_points, azimuth_deg, elevation_deg,
                 lens_mm, sensor_mm, width, height,
                 height_frac, end_x_frac, target_y_frac=0.52,
                 radius_bounds=(0.5, 40.0), passes=6):
    """Pin a camera so the subject fills `height_frac` and arrives at `end_x_frac`.

    `all_points` is every point that must stay in frame across the whole shot (the union
    silhouette samples); `end_points` is the subject at the frame he arrives on, which is
    what the composition is built around.

    Three knobs are solved and each is solved against one thing:

    * **radius** — from the union's screen height. Size is the constraint that wins; see
      the module docstring for why the traverse cannot also be dialled.
    * **lateral offset** of the target along screen-right — so his centre lands on
      `end_x_frac` at the mark.
    * **vertical offset** of the target — so his centre sits at `target_y_frac` down the
      frame, which is what leaves headroom above him for the model to put a room in.

    They interact weakly (moving the target sideways barely changes the height it
    subtends), so the three 1-D solves are simply repeated `passes` times rather than
    solved jointly. The residuals are reported; a caller that does not check them is
    trusting the iteration, which is why `make_shot_spec` prints them and the report
    quotes them against the render's own measured bbox.
    """
    if not all_points or not end_points:
        raise FramingError("no points to frame")
    cx = sum(p[0] for p in all_points) / len(all_points)
    cy = sum(p[1] for p in all_points) / len(all_points)
    cz = sum(p[2] for p in all_points) / len(all_points)
    base = (cx, cy, cz)

    az, el = azimuth_deg, elevation_deg
    # horizontal screen-right direction, for offsetting the target along the frame
    pos0 = camera_position(base, 1.0, el, az)
    right, up, _ = camera_basis(base, pos0)

    radius = 0.5 * (radius_bounds[0] + radius_bounds[1])
    offset_r = 0.0
    offset_u = 0.0

    def target_of(r_off, u_off):
        return _add(base, _add(_scale(right, r_off), _scale(up, u_off)))

    for _ in range(passes):
        def h_of(rad):
            e = _extent(all_points, target_of(offset_r, offset_u), rad, az, el,
                        lens_mm, sensor_mm, width, height)
            if e is None:
                return 99.0
            return e[3] - e[2]
        radius = _bisect(h_of, radius_bounds[0], radius_bounds[1], height_frac)

        def x_of(r_off):
            e = _extent(end_points, target_of(r_off, offset_u), radius, az, el,
                        lens_mm, sensor_mm, width, height)
            if e is None:
                return 99.0
            return 0.5 * (e[0] + e[1])
        # a positive lateral offset of the TARGET moves the subject left on screen, so
        # the bracket runs the other way; bisection does not care which.
        offset_r = _bisect(x_of, -6.0, 6.0, end_x_frac)

        def y_of(u_off):
            e = _extent(all_points, target_of(offset_r, u_off), radius, az, el,
                        lens_mm, sensor_mm, width, height)
            if e is None:
                return 99.0
            return 0.5 * (e[2] + e[3])
        offset_u = _bisect(y_of, -6.0, 6.0, target_y_frac)

    target = target_of(offset_r, offset_u)
    union = _extent(all_points, target, radius, az, el, lens_mm, sensor_mm, width, height)
    end = _extent(end_points, target, radius, az, el, lens_mm, sensor_mm, width, height)
    return {
        "target": list(target),
        "radius": radius,
        "azimuth_deg": az,
        "elevation_deg": el,
        "lens_mm": lens_mm,
        "sensor_mm": sensor_mm,
        "resolution": [width, height],
        "achieved": {
            "union_height_frac": union[3] - union[2],
            "union_x": [union[0], union[1]],
            "union_y": [union[2], union[3]],
            "end_centre_x": 0.5 * (end[0] + end[1]),
            "end_x": [end[0], end[1]],
            "end_y": [end[2], end[3]],
        },
        "requested": {"height_frac": height_frac, "end_x_frac": end_x_frac,
                      "target_y_frac": target_y_frac},
        "in_frame": (union[0] >= 0.0 and union[1] <= 1.0
                     and union[2] >= 0.0 and union[3] <= 1.0),
    }
