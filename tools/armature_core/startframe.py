"""The start frame's geometry: what must be inside the frame, and how it is checked.

No bpy. E11 authors the first frame of an image-to-video generation from a GLB, so the
whole product of this module is one question asked twice, two different ways:

    is the WHOLE performer inside the frame we are about to hand the model?

**Why that question needs its own module and its own andon.** `framing.solve_camera`
already reports `in_frame`, and it is not enough here. It is solved over a *landmark*
cloud plus the rest bbox's half-extents hung on the hips — `render_performer.body_cloud`
says so in its own docstring: "landmarks under-report the SILHOUETTE". Under-reporting is
harmless when it costs a few pixels of margin on a 1080p detector plate; it is not harmless
when the frame IS the conditioning image. A start frame with a shaved skull or a cropped
foot hands the model a cropped character, the model paints a cropped character for
sixty-five frames, and nothing downstream fires: the file is the right size, the render is
non-empty, the coverage fraction is healthy, and Gate L is about frame legality, not about
what is in the frame.

So the composition is solved on the silhouette rather than on landmarks, and then checked
on the silhouette *unclipped*.

**Unclipped is the load-bearing word.** `blender_scene.projected_bbox_px` drops every
vertex outside the frame before taking its bounds, which is right for comparing against a
rendered mask and wrong for asking whether anything left the frame: a figure whose arm is
200 px off the left edge comes back with `x0 = 0`, snug and innocent. The extent computed
here keeps negative and over-width coordinates, because the number this gate needs is
exactly the one clipping destroys.

The second instrument — the rendered-pixel difference against an empty plate — lives in the
tool, bounds the other direction (is anybody in the frame at all), and is not a substitute
for this one: it sees the figure's shadow on the floor as subject, so its bounds cannot say
where the *body* ends.
"""

from . import framing
from .errors import GateFailure


class StartFrameGate(GateFailure):
    """The start frame is not a frame of the whole performer."""

    gate = "WHOLE"


def framing_cloud(points, cap=1500):
    """Reduce a vertex cloud to at most `cap` points, keeping every axis extreme.

    `framing.solve_camera` projects its whole cloud inside three nested bisections, so a
    40,000-vertex mesh is tens of millions of pure-Python projections. Striding is the
    obvious reduction and the obvious reduction is the dangerous one: a stride can drop the
    single topmost vertex, the solve then fits a figure shorter than the real one, and the
    composition comes out slightly too large with no symptom anywhere.

    So the extremes are carried across the reduction by construction — the six per-axis
    argmin/argmax vertices are always kept. The guarantee is a testable one and it is
    tested: for every axis, `min`/`max` of the result equal `min`/`max` of the input.

    The reduction is deterministic (a fixed stride, then a sorted merge), because a
    composition that changes between two runs of the same tool is not a recipe.
    """
    pts = [tuple(float(c) for c in p) for p in points]
    if not pts:
        raise StartFrameGate(
            "no vertices to frame; a camera solved against nothing frames the origin and "
            "the render would be of an empty room", {"n_points": 0})
    if cap < 8:
        raise StartFrameGate(
            f"cap={cap} is below the 8 bbox corners this reduction must keep",
            {"cap": cap})
    if len(pts) <= cap:
        return list(pts)

    keep = set()
    for axis in (0, 1, 2):
        keep.add(min(range(len(pts)), key=lambda i: pts[i][axis]))
        keep.add(max(range(len(pts)), key=lambda i: pts[i][axis]))

    room = cap - len(keep)
    stride = max(1, len(pts) // max(1, room))
    for i in range(0, len(pts), stride):
        if len(keep) >= cap:
            break
        keep.add(i)
    return [pts[i] for i in sorted(keep)]


def silhouette_extent(points, target, radius, azimuth_deg, elevation_deg,
                      lens_mm, sensor_mm, width, height):
    """Unclipped pixel bounds of a projected cloud, plus what fell behind the camera.

    Returns `{x0, x1, y0, y1, n_behind, n_points}` in PIXELS, with values free to be
    negative or larger than the frame — see the module docstring for why that matters.

    A point behind the camera is counted rather than projected: the perspective divide
    mirrors it into frame, so including it would move the bounds to a place the figure
    never occupied. Any point behind the lens is itself a framing failure, so the count is
    reported and the caller's gate raises on it.
    """
    xs, ys, behind = [], [], 0
    for p in points:
        fx, fy, ok = framing.project(p, target, radius, azimuth_deg, elevation_deg,
                                     lens_mm, sensor_mm, width, height)
        if not ok:
            behind += 1
            continue
        xs.append(fx * width)
        ys.append(fy * height)
    if not xs:
        raise StartFrameGate(
            f"every one of {len(points)} points is behind the camera; there is no "
            f"silhouette to measure", {"n_points": len(points), "n_behind": behind})
    return {"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys),
            "n_behind": behind, "n_points": len(points)}


def gate_whole(extent, width, height, margin_px):
    """Gate WHOLE · ANDON — the entire silhouette is inside the frame, with margin.

    Raises unless every side clears the border by `margin_px`. Reports the achieved margin
    per side either way, because "it passed" and "it passed by one pixel" are different
    facts about a composition and the second one is a warning.

    **It binds on both directions of the same edge.** Too large is the failure this exists
    for (a cropped character conditioning the whole clip); too *small* is not caught here
    and is not silent — the figure's height fraction is reported and the Director sees the
    frame. The andon is placed where nothing else looks.
    """
    ev = {
        "gate": "WHOLE", "margin_px": margin_px, "resolution": [width, height],
        "extent_px": {k: extent[k] for k in ("x0", "x1", "y0", "y1")},
        "n_points": extent.get("n_points"), "n_behind": extent.get("n_behind"),
        "margins_px": {
            "left": extent["x0"], "right": (width - 1) - extent["x1"],
            "top": extent["y0"], "bottom": (height - 1) - extent["y1"]},
        "height_frac": (extent["y1"] - extent["y0"]) / float(height),
        "width_frac": (extent["x1"] - extent["x0"]) / float(width),
    }
    if extent.get("n_behind"):
        raise StartFrameGate(
            f"{extent['n_behind']} of {extent['n_points']} silhouette points are behind "
            f"the camera; the perspective divide mirrors those into frame, so any bounds "
            f"computed with them would describe a place the figure never was", ev)

    short = {side: m for side, m in ev["margins_px"].items() if m < margin_px}
    if short:
        raise StartFrameGate(
            "the performer's silhouette does not clear the frame border by "
            f"{margin_px} px on: "
            + ", ".join(f"{side} ({m:.1f} px)" for side, m in sorted(short.items()))
            + ". This frame IS the conditioning image, so a body cut by the border is a "
              "cut body for the whole generation — and every downstream check passes on "
              "it: the file is the right size, the render is not empty, the coverage "
              "fraction is healthy and Gate L only asks whether the frame is legal",
            ev)
    ev["verdict"] = ("whole silhouette in frame; smallest margin "
                     f"{min(ev['margins_px'].values()):.1f} px")
    return ev


def mask_bbox(mask_rows):
    """Inclusive `(x0, y0, x1, y1)` of a boolean row-major mask, or None if empty.

    Kept here rather than inlined in the tool so the tool's own measurement of what it
    rendered is testable without Blender, which is the only way the empty case — the
    render nobody is in — gets exercised at all.
    """
    xs0 = ys0 = None
    xs1 = ys1 = -1
    for y, row in enumerate(mask_rows):
        hit = [x for x, v in enumerate(row) if v]
        if not hit:
            continue
        lo, hi = hit[0], hit[-1]
        xs0 = lo if xs0 is None else min(xs0, lo)
        xs1 = max(xs1, hi)
        ys0 = y if ys0 is None else ys0
        ys1 = y
    if xs0 is None:
        return None
    return (xs0, ys0, xs1, ys1)
