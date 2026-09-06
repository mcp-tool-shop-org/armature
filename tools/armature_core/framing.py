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

import json
import math

from .errors import ArmatureError, GateFailure

WORLD_UP = (0.0, 0.0, 1.0)


class FramingError(ArmatureError):
    """The shot could not be framed as asked.

    Carries an `evidence` dict the way `armature_core.errors.GateFailure` does, because a
    refusal that reaches a receipt as a sentence and nothing else is the shape
    `tests/conftest.assert_gate` exists to refuse — "a gate raised with no measurement is a
    well-formed, silent object". Measured on the wave-10 base: none of this module's 12
    raises passed a second argument, so `getattr(exc, "evidence", None)` was None in every
    halt line this module could produce, and an operator reading the receipt could not see
    which field disagreed or by how much without re-running.

    **It used to subclass `ValueError`** (F-ba21426c, corrected 2026-09-04), which put all
    12 sites outside the family the ONE halt contract discriminates on: every one was
    recorded as "FAILED — an unhandled error" with gate null at exit 1, and
    `evidence_dicts_missing` examined none of them. The same defect `walk.WalkError` and
    `glb.MalformedGLB` carried; all three were rebased together, the family being derived
    by an AST walk of the class hierarchy under `tools/` rather than by naming the ones
    somebody noticed.

    **A refusal's evidence names `gate` explicitly as `None`.** Now that this class is in
    the family, `tests/test_gates.evidence_dicts_missing` examines every raise here that
    carries a dict, and it asks for `gate` and `andon`. A refusal is not an andon and has
    no gate id, so the honest answer is written down rather than left absent: the receipt
    line reads "REFUSED" with `gate` null and the class name under `andon`, which is a
    different fact from the crash line it used to read (outcome "FAILED", `gate` null
    because nothing knew what had happened).

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
    """


class PinnedCameraGate(FramingError, GateFailure):
    """Gate PIN · ANDON — a pinned camera record disagrees with what the caller projects at.

    `load_pinned_camera`'s docstring already called this the andon rather than optional
    discipline; it now raises as one, so the halt contract records exit 2 and "a gate
    fired" rather than a crash. It keeps `FramingError` in its bases, so every existing
    `except FramingError` and every `pytest.raises(FramingError)` in the suite still
    catches it.
    """

    gate = "PIN"


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
        raise FramingError(
            f"cannot normalise a zero-length direction: the vector "
            f"{[float(v) for v in a]} has length {n}",
            {"gate": None, "andon": "FramingError", "clause": "zero_length_direction",
             "vector": [float(v) for v in a], "length": n})
    return _scale(a, 1.0 / n)


def _finite(value):
    """Is `value` a number that is finite? A PREDICATE, never a raiser — `_finite_positive`'s
    sibling for the quantities that may legitimately be zero or negative (a screen fraction
    measured from the frame's left edge, a vertical offset)."""
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _finite_positive(value):
    """Is `value` a number that is finite and strictly greater than zero?

    A PREDICATE, never a raiser, and that is deliberate: `tests/test_gates.
    evidence_dicts_missing` is the suite's one evidence walk, and it returns `unreadable`
    — policed by nothing — for a raise whose evidence dict it cannot resolve. A shared
    raising helper mutating a caller's `ev` is exactly that shape, so every refusal below
    is spelled at its own site with a literal dict carrying `gate`, `andon` and `clause`.
    A diagnostic and a gate are different objects (CLAUDE.md); this is the diagnostic.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f) and f > 0.0


#: Why both span functions bound the FRAME SIZE and not only the camera numbers:
#: `sensor_mm * height / width` divides by one of the frame's own dimensions, and
#: `width >= height` chooses WHICH — so a zero width is a bare `ZeroDivisionError` on one
#: branch and a silently collapsed span on the other, and the render saves as a
#: well-formed image either way.
_FRAME_SIZE_REFUSAL = (
    "is not a finite positive number of pixels. Both span functions divide one sensor "
    "dimension by the frame's aspect, and which dimension divides is chosen by "
    "`width >= height`, so a degenerate size is a bare ZeroDivisionError on one branch "
    "and a silently collapsed span on the other — and the render saves as a well-formed "
    "image either way")


def half_fovs(lens_mm, sensor_mm, width, height):
    """Half field of view per axis, matching Blender's AUTO sensor fit.

    Copied in form from `blender_scene.half_fovs` deliberately: if the two ever disagree,
    the framing solved here and the framing rendered there would differ, and the only
    symptom would be a subject slightly off the mark with nothing pointing at why.
    `tests/test_framing.py` pins them against each other.

    **It had no clause at all, twenty lines from a sibling that does** (F-329a9555, wave
    18). `ortho_half_spans` below opens with a non-positive guard; this function opened
    with the arithmetic. Measured on the wave-18 base: `half_fovs(50.0, 0.0, 832, 480)`
    returned `(0.0, 0.0)` and `project` then raised a bare `ZeroDivisionError` from
    `math.tan(0.0)` — untyped, so the 21-tool halt contract records exit 1 "an unhandled
    error" where a refusal at exit 2 belongs. `half_fovs(nan, 36.0, ...)` returned
    `(nan, nan)`. And `half_fovs(-50.0, 36.0, 832, 480)` returned
    `(-0.34555558058171215, -0.2047809499429749)` — a NEGATIVE field of view, from which
    `project` point-mirrors the whole frame about its centre while `silhouette_extent`
    reports a perfectly plausible finite box.

    That last one is the escape that was open END TO END: `render_turnaround.py` declares
    `--lens` and `--sensor` as bare `type=float` with no bound, and a mirrored silhouette
    that stays inside the frame clears Gate WHOLE, Gate CROP and Gate ALPHA — an eight-view
    turnaround rendered and shipped upside down with every andon green.

    **The andon is inside the function performing the step**, per CLAUDE.md, rather than at
    each caller: `blender_scene.auto_radius` divides by `math.sin(min(hx, hy))` and
    `project` divides by `math.tan(hx)`, so both are closed by this one clause in each
    copy rather than by a guard per division.
    """
    for name, v in (("width", width), ("height", height)):
        if not _finite_positive(v):
            raise FramingError(
                f"{name}={v!r} {_FRAME_SIZE_REFUSAL}",
                {"gate": None, "andon": "FramingError",
                 "clause": "frame_size_not_positive", name: v,
                 "lens_mm": lens_mm, "sensor_mm": sensor_mm,
                 "width": width, "height": height})
    for name, v in (("sensor_mm", sensor_mm), ("lens_mm", lens_mm)):
        if not _finite_positive(v):
            raise FramingError(
                f"{name}={v!r} is not a finite positive camera number. A NaN fails every "
                f"comparison in both directions and reaches the verdict line; a zero "
                f"divides; and a NEGATIVE one returns a negative half-FOV, which "
                f"point-mirrors the projected frame about its centre while every extent, "
                f"crop and alpha gate still reads a plausible finite box",
                {"gate": None, "andon": "FramingError",
                 "clause": f"{name}_not_finite_and_positive",
                 "lens_mm": lens_mm, "sensor_mm": sensor_mm,
                 "width": width, "height": height})
    if width >= height:
        sx = sensor_mm
        sy = sensor_mm * height / width
    else:
        sy = sensor_mm
        sx = sensor_mm * width / height
    return math.atan(sx * 0.5 / lens_mm), math.atan(sy * 0.5 / lens_mm)


def ortho_half_spans(ortho_scale, width, height):
    """Half the world-space width and height an ORTHO frame covers, AUTO sensor fit.

    The parallel-projection counterpart of `half_fovs`, and deliberately the same shape:
    Blender's AUTO fit puts the sensor dimension on the LONGER image axis and derives the
    other from the aspect, so `ortho_scale` spans the longer axis and the shorter one
    follows. On a square frame the two are equal and the convention is invisible — which is
    why S04's calibration render is taken at 352x1024 and not at the square preset it ships.

    Returns HALF spans, because that is what the projection divides by.

    **The guard used to bound one direction and not the other** (F-329a9555, wave 18). It
    read `if ortho_scale <= 0.0`, and `nan <= 0.0` is False: measured on the wave-18 base,
    `ortho_half_spans(nan, 832, 480)` RETURNED `(nan, nan)` past this function's own and
    only clause, and `+inf` returned `(inf, inf)`. `turnaround.projection_plan`'s docstring
    already recorded the fact — "`ortho_half_spans` refuses <= 0 downstream but takes nan
    and inf" — and guarded it at the two callers instead of here. The clause is now
    `not (isfinite and > 0)`, which is the direction the invariant did not bound; the
    callers' pins stand and are no longer the only thing standing.
    """
    for name, v in (("width", width), ("height", height)):
        if not _finite_positive(v):
            raise FramingError(
                f"{name}={v!r} {_FRAME_SIZE_REFUSAL}",
                {"gate": None, "andon": "FramingError",
                 "clause": "frame_size_not_positive", name: v,
                 "ortho_scale": ortho_scale, "width": width, "height": height})
    if not _finite_positive(ortho_scale):
        raise FramingError(
            f"ortho_scale is {ortho_scale}, which spans no world at all; a parallel camera "
            f"with a non-positive scale collapses every point onto the frame centre, a "
            f"non-finite one sends every point nowhere at all, and the render still saves "
            f"as a well-formed image either way",
            {"gate": None, "andon": "FramingError",
             "clause": "ortho_scale_not_positive", "ortho_scale": ortho_scale,
             "width": width, "height": height})
    if width >= height:
        sx = ortho_scale
        sy = ortho_scale * height / width
    else:
        sy = ortho_scale
        sx = ortho_scale * width / height
    return 0.5 * sx, 0.5 * sy


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
            f"the camera is looking straight up or down from "
            f"{[float(v) for v in position]} to {[float(v) for v in target]}; the up "
            f"vector is undefined and the roll of the shot would be arbitrary",
            {"gate": None, "andon": "FramingError",
             "clause": "view_direction_parallel_to_up",
             "position": [float(v) for v in position],
             "target": [float(v) for v in target]})
    up = _norm(proj)
    right = _cross(up, back)
    return right, up, back


def project(point, target, radius, azimuth_deg, elevation_deg,
            lens_mm, sensor_mm, width, height, ortho_scale=None):
    """Screen fractions (x right, y down) of a world point, plus whether it is in front.

    (0, 0) is the top-left corner and (1, 1) the bottom-right, so the numbers read the way
    a composition is discussed: "he arrives at 0.67" is two thirds across.

    **`ortho_scale=None` is the perspective path and it is the one that was here before**
    (S04): the camera placement, the basis, the behind-test and the perspective arithmetic
    below are untouched, so a caller that does not pass the keyword cannot tell this
    function changed. Passing a scale switches the divide: parallel projection drops the
    `/-z` and measures the lateral offset against a fixed world span instead of a cone.

    **The behind-test is kept in ORTHO too, and that is deliberate.** Parallel projection
    has no perspective divide, so a point behind the camera does *not* mirror into frame —
    the arithmetic would place it correctly. Blender's near plane would still clip it, and
    `silhouette_extent`'s `n_behind` count is what Gate WHOLE raises on, so keeping the
    test conservative means the ortho standoff has to be genuinely clipping-safe rather
    than merely arithmetically survivable.
    """
    pos = camera_position(target, radius, elevation_deg, azimuth_deg)
    right, up, back = camera_basis(target, pos)
    v = _sub(point, pos)
    z = _dot(v, back)          # positive means behind the camera
    if z >= -1e-9:
        return None, None, False
    if ortho_scale is not None:
        hx, hy = ortho_half_spans(ortho_scale, width, height)
        return 0.5 + 0.5 * (_dot(v, right) / hx), 0.5 - 0.5 * (_dot(v, up) / hy), True
    hx, hy = half_fovs(lens_mm, sensor_mm, width, height)
    ndc_x = (_dot(v, right) / -z) / math.tan(hx)
    ndc_y = (_dot(v, up) / -z) / math.tan(hy)
    return 0.5 + 0.5 * ndc_x, 0.5 - 0.5 * ndc_y, True


def load_pinned_camera(path, expect):
    """(target, radius) from a prior camera record, or raise naming what disagreed.

    Any JSON carrying `camera.target` and `camera.radius` will do — a
    `render_provenance.json`, a `keypoints.json`, a `shot_spec`. Two uses: overlaying one
    tool's output on another tool's render, and locking one composition across a series of
    shots (E08's reference-set discipline, G14, applied to framing).

    **`expect` is not optional discipline, it is the andon.** Pinning a camera skips the
    framing solve, and skipping the solve skips its gate. A record pinned at a different
    azimuth or lens would project a perfectly plausible skeleton of the same body seen from
    somewhere else, and every downstream check — counts, legality, ink, in-canvas — passes
    on it. So the caller states the angles it projects at and any disagreement raises here,
    where the mistake is still cheap.

    **It is required, and an empty expectation is refused** (F-abcb06a8). The signature was
    `load_pinned_camera(path, expect=None)` with the comparison written
    `(expect or {}).items()`, so omitting the argument - or passing `None` - skipped the
    loop and the andon this docstring already called non-optional was disarmed by a
    caller who typed less. `tests/test_pinned_camera.py` named `expect=None` "the escape
    hatch" and pinned it; that test is replaced by the refusal below. It is left
    positional-or-keyword rather than keyword-only because both production call sites
    already pass it positionally and the invariant is about presence, not spelling.
    """
    if not expect:
        raise PinnedCameraGate(
            f"{path}: load_pinned_camera was called with no expectation to check against "
            f"({expect!r}). Pinning a camera skips the framing solve and therefore skips "
            f"its gate; a record pinned at a different azimuth, elevation or lens projects "
            f"a plausible view of the same body from somewhere else and every downstream "
            f"check passes on it. This argument is the andon, not optional discipline, so "
            f"there is no shape of it that means 'do not check'",
            {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
             "expect": expect, "clause": "empty_expectation"})

    with open(path, "r", encoding="utf-8") as fh:
        rec = json.load(fh)
    cam = rec.get("camera")
    if not isinstance(cam, dict) or "target" not in cam or "radius" not in cam:
        raise PinnedCameraGate(
            f"{path} carries no camera.target/camera.radius to pin to; its top-level keys "
            f"are {sorted(rec)[:12]}",
            {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
             "top_level_keys": sorted(rec)[:12],
             "camera_keys": sorted(cam) if isinstance(cam, dict) else None,
             "clause": "no_camera_block"})
    target = cam["target"]
    if not (isinstance(target, (list, tuple)) and len(target) == 3):
        raise PinnedCameraGate(
            f"{path}: camera.target is not a 3-vector: {target!r}",
            {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
             "field": "target", "got": target, "clause": "target_not_a_3_vector"})
    radius = float(cam["radius"])
    if not (radius > 0.0):
        raise PinnedCameraGate(
            f"{path}: camera.radius is {radius}, which is not a distance",
            {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
             "field": "radius", "got": radius, "clause": "radius_not_a_distance"})

    for field, ours in sorted(expect.items()):
        theirs = cam.get(field)
        if theirs is None:
            raise PinnedCameraGate(
                f"{path}: the pinned camera does not record {field}, so it cannot be shown "
                f"to match the {ours} this caller projects at. A camera that agrees by "
                f"silence is not a camera that agrees",
                {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
                 "field": field, "expected": ours, "got": None,
                 "recorded_fields": sorted(cam), "clause": "field_absent"})
        if abs(float(theirs) - float(ours)) > 1e-9:
            raise PinnedCameraGate(
                f"{path}: the pinned camera's {field} is {theirs} and this caller projects "
                f"at {ours}. The result would be a plausible view of the same body from "
                f"somewhere else, and every downstream check passes on that",
                {"gate": "PIN", "andon": "PinnedCameraGate", "record": path,
                 "field": field, "expected": float(ours), "got": float(theirs),
                 "difference": abs(float(theirs) - float(ours)), "tolerance": 1e-9,
                 "clause": "field_disagrees"})
    return tuple(float(v) for v in target), radius


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
    residuals here are smooth but not analytically invertible.

    **The bracket test is the only clause here, and a non-finite target deletes it**
    (F-c6124fe0, wave 22). `(flo - want) * (fhi - want) > 0` is False for a NaN and the
    loop's `(f(lo) - want) * (f(mid) - want) <= 0` is False for the same reason, so the
    search walked to its own bound and RETURNED it: measured on `e8263a3`,
    `_bisect(lambda t: t, 0.0, 1.0, nan)` returns 1.0. A solver that returns a bound looks
    exactly like a solver that succeeded, which is the difference this module's own
    reachability refusal exists to draw.

    The clause is here as well as in `solve_camera` deliberately — the wave-18 SEAM 5 shape:
    the andon inside the function performing the step, the bound at the caller that composes
    the request. Complementary, not redundant; an importer that reaches this helper without
    going through `solve_camera` gets the refusal too.

    **The bracket has TWO ends and wave 22 guarded one** (F-526e9069, wave 25). The clause
    below rules on `want`; `flo` and `fhi` are the values the CLOSURE returns, and the same
    sentence is true of them — `(flo - want) * (fhi - want) > 0` is False when `flo` is a
    NaN just as surely as when `want` is. MEASURED in this worktree on `580af47`:
    `_bisect(lambda t: float('nan'), 0.0, 1.0, 0.5)` returns **1.0**, its own upper bound,
    with a finite legal target. The closure here is `h_of` / `x_of` / `y_of` in
    `solve_camera`, each of which measures a screen extent over a point cloud, so a
    non-finite vertex reaches the bracket test through the closure rather than through the
    request. Both ends are ruled on now, under their own clause word.
    """
    if not _finite(want):
        raise FramingError(
            f"the framing target {want!r} is not a finite number, so the bracket test "
            f"below cannot rule on it: `(flo - want) * (fhi - want) > 0` is False for a "
            f"NaN in both directions and so is every comparison the loop makes, which "
            f"means the search terminates at its own bound and returns it. A returned "
            f"bound is indistinguishable from a solved composition",
            {"gate": None, "andon": "FramingError",
             "clause": "bisect_target_not_finite",
             "search_bounds": [lo, hi], "wanted": want})
    flo, fhi = f(lo), f(hi)
    for _end, _v in (("flo", flo), ("fhi", fhi)):
        if not _finite(_v):
            raise FramingError(
                f"the bracket end {_end}={_v!r} is not a finite number: the closure this "
                f"search is solving returned it at {lo if _end == 'flo' else hi!r}, so the "
                f"bracket test `(flo - want) * (fhi - want) > 0` is False in both "
                f"directions and so is every comparison the loop makes. The search then "
                f"terminates at its own bound and returns it, and a returned bound is "
                f"indistinguishable from a solved composition — the same defect the target "
                f"clause above refuses, arriving through the closure instead of through "
                f"the request",
                {"gate": None, "andon": "FramingError",
                 "clause": "bisect_bracket_not_finite",
                 "search_bounds": [lo, hi], "wanted": want,
                 "end": _end, "value": repr(_v),
                 "value_range": [repr(flo), repr(fhi)]})
    if (flo - want) * (fhi - want) > 0:
        raise FramingError(
            f"the requested framing is not reachable between {lo} and {hi}: the value "
            f"runs {flo:.4f}..{fhi:.4f} and {want:.4f} is outside it",
            {"gate": None, "andon": "FramingError",
             "clause": "composition_unreachable",
             "search_bounds": [lo, hi], "value_range": [flo, fhi], "wanted": want})
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
    # WAVE 22, F-c6124fe0 — THE SOLVER HALF of the composition-fraction bound. Measured on
    # `e8263a3` on an eight-point cloud at 832x480, lens 50 / sensor 36: the legal call
    # returns radius 5.566204 with `achieved.union_height_frac` 0.8, while
    # `height_frac=nan` RETURNS radius 40.0 — the `radius_bounds` CEILING — with
    # `union_height_frac` 0.106, `in_frame: True` and `requested.height_frac: nan`;
    # `end_x_frac=nan` RETURNS with `achieved.end_centre_x = -1.0042`, the subject a full
    # frame-width off the left edge; `target_y_frac=nan` RETURNS with `achieved.union_y
    # [2.223, 3.023]`, the union entirely below the frame. In every case the record is
    # complete and well-formed, and publishes the unreadable REQUEST beside the achieved
    # numbers as though the two were related.
    #
    # F-f0c261c1 measured this same defect ON THIS FUNCTION and its fix went to one tool's
    # PARSER (`render_start_frame.require_shot_fraction`). `end_x_frac` and `target_y_frac`
    # are bounded at NO parser in the tree — measured by grep, `--height-frac` is the only
    # such flag — so an importer, or a new tool exposing a composition fraction, got the
    # whole escape. The clause WORDS are that parser's, so one grep against
    # `STARTFRAME_FRACTION`'s vocabulary finds the flag and the solver both.
    #
    # `height_frac` is a fraction of the frame HEIGHT and must be positive; `end_x_frac` and
    # `target_y_frac` are positions measured across the frame and may legitimately sit
    # outside [0, 1] while a shot is being composed, so only finiteness is bounded there —
    # the direction that walks past every comparison rather than the direction a composition
    # may deliberately want.
    _who = "framing.solve_camera"
    if not _finite_positive(height_frac):
        raise FramingError(
            f"height_frac={height_frac!r} is not a finite positive fraction of the frame. "
            f"A NaN fails every comparison in both directions, so the bisection's bracket "
            f"test cannot fire and the search returns its own ceiling — measured, radius "
            f"40.0 over a subject filling 0.106 of the frame, with `in_frame: True` and a "
            f"complete record naming the unreadable request beside the achieved numbers",
            {"gate": None, "andon": "FramingError", "who": _who, "flag": "height_frac",
             "clause": "not_a_finite_positive_fraction", "height_frac": height_frac})
    for _name, _value in (("end_x_frac", end_x_frac), ("target_y_frac", target_y_frac)):
        if not _finite(_value):
            raise FramingError(
                f"{_name}={_value!r} is not a finite fraction of the frame. Measured: a "
                f"non-finite `end_x_frac` returns a camera whose subject arrives a full "
                f"frame-width off the left edge, and a non-finite `target_y_frac` one whose "
                f"union sits entirely below the frame — both with no refusal anywhere, "
                f"because the only clause that could rule on the request is a bracket test "
                f"a NaN makes False",
                {"gate": None, "andon": "FramingError", "who": _who, "flag": _name,
                 "clause": "not_a_finite_fraction", _name: _value})
    _bounds = list(radius_bounds)
    if len(_bounds) != 2 or not all(_finite_positive(b) for b in _bounds):
        raise FramingError(
            f"radius_bounds={radius_bounds!r} is not two finite positive radii. This is "
            f"the interval the search returns a member of when it cannot refuse, so a "
            f"bracket that is not itself two real distances makes every verdict below "
            f"unreadable",
            {"gate": None, "andon": "FramingError", "who": _who, "flag": "radius_bounds",
             "clause": "radius_bounds_not_finite_and_positive",
             "radius_bounds": list(radius_bounds)})
    if not float(_bounds[0]) < float(_bounds[1]):
        raise FramingError(
            f"radius_bounds={radius_bounds!r} is not an interval: the lower bound is not "
            f"below the upper one, so bisection has nothing to halve",
            {"gate": None, "andon": "FramingError", "who": _who, "flag": "radius_bounds",
             "clause": "radius_bounds_not_an_interval",
             "radius_bounds": [float(_bounds[0]), float(_bounds[1])]})
    if not all_points or not end_points:
        raise FramingError(
            f"no points to frame: {len(all_points)} point(s) in the cloud and "
            f"{len(end_points)} end point(s)",
            {"gate": None, "andon": "FramingError", "clause": "empty_point_cloud",
             "n_all_points": len(all_points), "n_end_points": len(end_points)})
    # THE POINT CLOUD'S CLAUSE (F-526e9069, wave 25). Wave 22 bounded every SCALAR request
    # above — `height_frac`, `end_x_frac`, `target_y_frac`, `radius_bounds` — on the stated
    # ground that `(flo - want) * (fhi - want) > 0` is False for a NaN, so "the search
    # terminates at its own bound and returns it. A returned bound is indistinguishable
    # from a solved composition". The cloud took no clause: the line above is an EMPTINESS
    # test and nothing else, and `_extent`'s `min(xs)` / `max(xs)` walk past a NaN exactly
    # as `min(distances)` did in `turnaround`'s value door (F-8cfaefd9).
    #
    # MEASURED in this worktree on `580af47`, an eight-point cloud at 832x480 / lens 50 /
    # sensor 36: the legal call returns radius 3.70665 with `achieved.union_height_frac`
    # 0.8 and `in_frame: True`; replacing ONE coordinate with `nan` RETURNS radius **40.0**
    # — the `radius_bounds` CEILING, the signature the wave-22 comment names — with
    # `target: [nan, nan, nan]`, `achieved.union_height_frac: nan` and a `requested` block
    # in which every fraction is finite and legal. An `inf` in one coordinate gives the
    # identical record. The returned dict is not JSON either:
    # `json.dumps(record, allow_nan=False)` raises `ValueError: Out of range float values
    # are not JSON compliant: nan`, and at the default it emits the bare `NaN` token that
    # `parts.halt_keysafe`'s own docstring records as rejected by JS `JSON.parse`, Go
    # `encoding/json` and serde.
    #
    # Honest about what does NOT happen: `in_frame` is a conjunction of `>=`/`<=` tests,
    # all False for a NaN, so the live consumers (`render_start_frame.py::main` — the paid
    # I2V start frame — `render_performer.py::main` and `project_pose_keypoints.py::main`) DO
    # refuse. They refuse with "the union does not stay inside the frame", which is a
    # statement about a composition nobody requested, and no clause anywhere said a vertex
    # was not a number. This is the census `channels._non_finite_census` already uses,
    # spelled over a list of triples, and it runs on BOTH clouds because `end_points` is
    # the cloud `x_of` solves against and it is not always a subset of `all_points`.
    for _name, _cloud in (("all_points", all_points), ("end_points", end_points)):
        _bad = [i for i, p in enumerate(_cloud)
                if not all(_finite(c) for c in tuple(p)[:3])]
        if _bad:
            _first = _bad[0]
            raise FramingError(
                f"{len(_bad)} of {len(_cloud)} point(s) in {_name} carry a coordinate that "
                f"is not a finite number (first at index {_first}: "
                f"{tuple(_cloud[_first])!r}). Every bracket test this solver makes is False "
                f"against a NaN in both directions, so the bisection does not refuse — it "
                f"walks to its own ceiling and returns it, and the record it returns names "
                f"a legal `requested` composition beside a `target` and an "
                f"`achieved.union_height_frac` that are not numbers. Measured: radius 40.0, "
                f"the `radius_bounds` ceiling, on one non-finite vertex",
                {"gate": None, "andon": "FramingError", "who": _who,
                 "clause": "point_cloud_not_finite", "cloud": _name,
                 "n": len(_cloud), "n_finite": len(_cloud) - len(_bad),
                 "n_non_finite": len(_bad),
                 "first_non_finite_index": _first,
                 "first_non_finite_point": [repr(c) for c in tuple(_cloud[_first])[:3]],
                 "non_finite_indices": _bad[:12]})
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
    # `_extent` returns None as soon as ANY point projects behind the camera, and the three
    # bisection closures above each handle that by substituting the 99.0 sentinel. These
    # two final calls did not (F-6a8edff0): they were indexed unguarded inside the dict
    # literal below. The union here is measured at the target built from the LAST pass's
    # offsets but at a `radius` solved earlier in that same pass, so the two are not
    # guaranteed consistent, and a composition whose converged vertical offset pushes a
    # point behind the lens returned a bare `TypeError: 'NoneType' object is not
    # subscriptable` from the middle of a dict literal - where every other refusal in this
    # module names what went wrong and why it matters.
    behind = [name for name, value in (("union", union), ("end", end)) if value is None]
    if behind:
        raise FramingError(
            f"the requested composition is unreachable: after {passes} pass(es) the "
            f"{' and '.join(behind)} point cloud(s) put at least one point BEHIND the "
            f"camera at radius {radius:.6f}, target {[round(float(v), 6) for v in target]} "
            f"(lateral offset {offset_r:.6f}, vertical offset {offset_u:.6f}, azimuth "
            f"{az}, elevation {el}). Requested height_frac {height_frac}, end_x_frac "
            f"{end_x_frac}, target_y_frac {target_y_frac}: no camera on this orbit frames "
            f"that, so the numbers below would have been read off a projection that does "
            f"not exist",
            {"gate": None, "andon": "FramingError",
             "clause": "composition_puts_points_behind_the_camera",
             "behind": behind, "passes": passes, "radius": float(radius),
             "azimuth": az, "elevation": el, "height_frac": height_frac,
             "end_x_frac": end_x_frac, "target_y_frac": target_y_frac})
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
