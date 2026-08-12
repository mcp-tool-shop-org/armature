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


class AlphaGate(GateFailure):
    """An authored image input does not carry the alpha the law requires."""

    gate = "ALPHA"


def composite_colour(text):
    """`"r,g,b"` linear floats -> a 3-tuple. THE ALPHA LAW's other half; no default.

    The Director's ruling, 2026-08-12: authored image inputs carry alpha, never a baked
    void, and the RGB each route submits is a **deliberate, recorded choice**. A default
    value here would defeat exactly that — the grey studio that bled through three waves of
    start frames was never chosen by anyone, which is why nobody could find the choice to
    argue with. So the caller names the colour or the render does not happen.

    Linear scene-referred floats, not sRGB bytes: `52,41,31` would be clamped nonsense and
    `0.2,0.16,0.12` is a different (much lighter) colour than the same numbers read as
    bytes. The check below catches the byte form rather than rendering it.
    """
    if not text or not str(text).strip():
        raise AlphaGate(
            "no composite colour was named: under the alpha law the render is authored "
            "RGBA and the RGB actually submitted is composited over a NAMED background. "
            "Pass linear floats, e.g. 0.035,0.022,0.014, with a reason",
            {"supplied": text})
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 3:
        raise AlphaGate(
            f"the composite colour must be three linear floats `r,g,b`, got {text!r}",
            {"supplied": text})
    try:
        rgb = tuple(float(p) for p in parts)
    except ValueError:
        raise AlphaGate(f"the composite colour carries a non-number: {text!r}",
                        {"supplied": text}) from None
    if any(c < 0.0 or c > 1.0 for c in rgb):
        raise AlphaGate(
            f"composite values are linear scene-referred floats in [0,1], got {rgb}. sRGB "
            f"bytes like 52,41,31 are NOT linear floats — that form would render as a "
            f"blown white void, which is the failure this law exists to end",
            {"supplied": list(rgb)})
    return rgb


def gate_alpha(transparent_fraction, composite_rgb, why, master_path=None):
    """Gate ALPHA · ANDON — the authored master really carries transparency.

    **The andon goes on the direction the invariant does not bound.** Nothing else in the
    render path can tell a genuine RGBA render from a baked void with a fourth channel full
    of 255s: the file opens, the dimensions are right, the figure is in it, Gate WHOLE and
    Gate COVERAGE both pass. If `film_transparent` silently stopped taking effect — an
    engine change, a world node that writes alpha, a compositor added later — the law would
    read as satisfied in the provenance and be violated in the file. So the master is
    required to contain transparent pixels, and the fraction is reported either way.

    `transparent_fraction` is a measured number, so this function stays free of bpy and can
    be tested against every value it can take, including the two that matter: 0 and 1.
    """
    ev = {"gate": "ALPHA", "master": master_path,
          "transparent_fraction": float(transparent_fraction),
          "opaque_fraction": 1.0 - float(transparent_fraction),
          "composite_linear_rgb": list(composite_rgb), "composite_why": why,
          "note": ("the world background is alpha=0 and the floor plane is geometry, so an "
                   "opaque floor beneath a transparent void is the expected shape")}
    if not why:
        raise AlphaGate(
            "the composite colour was named but not explained. A choice nobody wrote down "
            "is indistinguishable from a leftover a year later, which is the whole failure "
            "mode this law addresses", ev)
    if float(transparent_fraction) <= 0.0:
        raise AlphaGate(
            "the authored master carries NO transparent pixels, so it is not an RGBA "
            "render — it is a baked void with a fourth channel. `film_transparent` did not "
            "take effect, and every check after this one passes on the file anyway", ev)
    if float(transparent_fraction) >= 1.0:
        raise AlphaGate(
            "the authored master is ENTIRELY transparent — nothing was rendered into it. "
            "A fully transparent master would composite to a flat field of the chosen "
            "colour and condition the generation on an empty picture", ev)
    ev["verdict"] = (f"alpha authored; {float(transparent_fraction):.4f} of the frame is "
                     f"transparent")
    return ev


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
