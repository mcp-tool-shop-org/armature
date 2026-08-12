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

import math

from . import framing
from .errors import GateFailure


class StartFrameGate(GateFailure):
    """The start frame is not a frame of the whole performer."""

    gate = "WHOLE"


class AlphaGate(GateFailure):
    """An authored image input does not carry the alpha the law requires."""

    gate = "ALPHA"


class BackdropGate(GateFailure):
    """What stands behind the performer is not the plate the record names."""

    gate = "BACKDROP"


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


def cover_fit(src_w, src_h, width, height):
    """Geometry for putting a plate behind the performer: COVER, never contain.

    Returns the scale, the resized size and the crop box that take a source of `src_w x
    src_h` to exactly `width x height` with **no padding anywhere**. Every returned box is
    fully inside the resized image by construction, so a caller that crops to it can never
    read a pixel that does not exist.

    **Why cover and not contain, which is what this repo's other fitter does.**
    `fit_reference.letterbox` deliberately pads: its subject is an identity reference, the
    Director ruled that the whole figure must reach the model, and flat margin was the
    accepted price. A backdrop is the opposite case. Padding a backdrop puts bands of
    invented colour into the conditioning image, and this repo already has that disease on
    file twice — the grey letterbox pads on E08's reference are the standing suspect for its
    washed bands, and the baked grey void is what THE ALPHA LAW exists to end. A plate that
    does not reach the frame edge is not a world; it is a picture of a world with a border
    drawn round it, and the model paints the border too.

    So the overhang is cropped and the loss is REPORTED rather than hidden. The centred crop
    is the choice; what it discards is in the record, in both source and resized pixels, so
    a later reader can see what left the frame without re-deriving it.

    Pure arithmetic — no image library, no bpy — because the invariants worth testing here
    (the box is exactly the target size; the box is inside the resized image; nothing is
    ever padded) are testable over a sweep of aspects only if no file has to exist.
    """
    src_w, src_h = int(src_w), int(src_h)
    width, height = int(width), int(height)
    if src_w <= 0 or src_h <= 0:
        raise BackdropGate(
            f"degenerate plate of {src_w}x{src_h}; there is no image to stand behind the "
            f"performer", {"source_size": [src_w, src_h]})
    if width <= 0 or height <= 0:
        raise BackdropGate(
            f"degenerate target frame of {width}x{height}",
            {"target_size": [width, height]})

    scale = max(width / src_w, height / src_h)
    # ceil, not round: rounding down by a single pixel would leave one row or column of the
    # crop box outside the resized image, and the caller would pad it without meaning to —
    # which is the one thing this function promises never to happen.
    nw = max(width, int(math.ceil(src_w * scale - 1e-9)))
    nh = max(height, int(math.ceil(src_h * scale - 1e-9)))
    ox, oy = (nw - width) // 2, (nh - height) // 2

    return {
        "fit": "cover",
        "source_size": [src_w, src_h], "target_size": [width, height],
        "source_aspect": src_w / src_h, "target_aspect": width / height,
        "scale": scale, "upscaled": scale > 1.0,
        "resized_size": [nw, nh],
        "crop_offset": [ox, oy],
        "crop_box": [ox, oy, ox + width, oy + height],
        "dropped_px_resized": {"x": nw - width, "y": nh - height},
        "dropped_px_source": {"x": (nw - width) / scale, "y": (nh - height) / scale},
        "kept_fraction_of_source_area": (width * height) / float(nw * nh),
        "pads": False,
        "note": ("cover fit: scale = max(width/src_w, height/src_h), then a centred crop. "
                 "Nothing is padded; the overhang is cropped and reported"),
    }


def gate_backdrop(void_vs_plate_255, plate_vs_flat_255, transparent_fraction, why,
                  tol_255, min_separation_255, plate=None, plate_sha256=None):
    """Gate BACKDROP · ANDON — the plate really reached the submitted composite.

    **The andon goes on the direction the invariant does not bound.** Every other check in
    this module looks at the performer: Gate WHOLE says the body is inside the frame, Gate
    COVERAGE says somebody is in it, Gate ALPHA says the master carries real transparency.
    None of them looks at what fills the transparent part, and that is the whole variable of
    a scene-bearing start frame. If a compositor node fails to wire, if the plate loads at
    the wrong colour space, if a later edit renders the flat-colour path by mistake, the
    file still opens, is still the right size, still contains the whole performer, still has
    healthy coverage — and the run is conditioned on the void the plate was meant to end,
    while the provenance records a plate. That is the exact failure shape THE ALPHA LAW was
    written for, one layer further in.

    Two measured numbers, because one of them alone can be fooled:

    * `void_vs_plate_255` — mean absolute difference, over the master's transparent region,
      between the submitted composite and the plate itself. Near zero when the plate
      arrived.
    * `plate_vs_flat_255` — mean absolute difference, over the same region, between the
      plate and the flat-colour composite this route would otherwise have submitted. This
      is the **vacuity guard**: if a plate is indistinguishable from the flat fallback there,
      then the first number is near zero whether the compositing worked or not, and a green
      verdict would be proving nothing. *A check that cannot fail is not a check*, so this
      raises and says so rather than passing.

    Both are measured quantities, so this function stays free of bpy and of any image
    library and can be tested against every value it can take.
    """
    ev = {"gate": "BACKDROP", "plate": plate, "plate_sha256": plate_sha256,
          "void_vs_plate_255": float(void_vs_plate_255),
          "plate_vs_flat_255": float(plate_vs_flat_255),
          "tol_255": float(tol_255), "min_separation_255": float(min_separation_255),
          "transparent_fraction": float(transparent_fraction), "why": why,
          "measured_over": ("the master's transparent region only — the part of the frame "
                            "the performer and the floor do not occupy")}
    if not why:
        raise BackdropGate(
            "the plate was named but not explained. A backdrop nobody wrote down a reason "
            "for is indistinguishable from a leftover a year later, which is the failure "
            "mode THE ALPHA LAW addresses", ev)
    if float(transparent_fraction) <= 0.0:
        raise BackdropGate(
            "the authored master has NO transparent region, so there is nowhere for a plate "
            "to be and nothing for this gate to measure. A green verdict here would be a "
            "check that cannot fail", ev)
    if float(plate_vs_flat_255) < float(min_separation_255):
        raise BackdropGate(
            f"the plate and the flat-colour fallback differ by only "
            f"{float(plate_vs_flat_255):.3f}/255 over the transparent region, below the "
            f"{float(min_separation_255)} needed for the check below to mean anything. "
            f"Either this plate is the void it was meant to replace, or the plate never "
            f"loaded — and in both cases a PASS would prove nothing", ev)
    if float(void_vs_plate_255) > float(tol_255):
        raise BackdropGate(
            f"behind the performer the submitted composite differs from the plate by "
            f"{float(void_vs_plate_255):.3f}/255 (tolerance {float(tol_255)}). The image "
            f"about to condition the generation is not the plate this record names", ev)
    ev["verdict"] = (f"the plate is behind the performer: {float(void_vs_plate_255):.3f}/255 "
                     f"from the plate, {float(plate_vs_flat_255):.3f}/255 from the flat "
                     f"fallback it replaces")
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
