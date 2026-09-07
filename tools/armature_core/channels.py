"""Channel maths — pure numpy, no bpy, no I/O.

Conventions fixed here, each with the finding that fixes it:

  depth   inverse relative, **near = bright** (F19). Normalised min-max over the
          pixels where geometry exists; background is not depth and is written 0
          (black = far), which is a stated convention of this exporter, not a
          retrieved one.
  normal  camera-space, +X right / +Y up / +Z toward the viewer — Blender's own
          camera axes — encoded n*0.5+0.5. A surface square to the camera encodes
          (128, 128, 255). Blender's Normal pass is world-space, so the caller
          hands us the camera rotation and the transform happens here.
  edge    geometric discontinuity derived from depth and normal (F22 — a rendered
          edge pass sidesteps Canny's contrast-sensitive dual-threshold tuning).
          The depth term is **relative to local depth** and the normal term is an
          angle, so no global constant governs a local feature; the silhouette term
          is exact.
  softedge  authored soft falloff of a geometric edge (F-e37bc671) — NOT HED /
          PiDiNet (those detector weights are not licence-mapped here). White ink
          on black; background 0; non-finite refused.
  canny   thin geometric edge alias (F-e37bc671) — NOT OpenCV Canny. Same geometric
          stance as `derive_edge`; named so routes that ask for a canny socket get
          a byte layout with the non-finite contract instead of a hand-rolled plate.
  flow    camera-plane UV displacement → RGB (F-e37bc671): R=u', G=v' via
          n*0.5+0.5 over a stated max magnitude; B unused (0). Authored layout,
          not a partner optical-flow weight.

`depth` deliberately produces BOTH normalisations. F19 says the ControlNet
convention is per-frame, but per-frame normalisation on a moving camera re-maps the
range every frame. Which one ships is not this module's decision and not this
session's — E01 reports both.
"""

import numpy as np

from .errors import ArmatureError
from .parts import require_finite

BACKGROUND_DEPTH = 0.0  # black = far, for pixels with no geometry

#: The lowest value a GEOMETRY pixel may take, so that "farthest geometry" and "no
#: geometry" are not the same byte. 1/255 encodes to byte 1; BACKGROUND_DEPTH encodes to
#: byte 0. Reserving one byte costs 0.4% of the depth range and is what keeps the
#: subject's far edge from dissolving into the void it is supposed to stand against.
GEOMETRY_DEPTH_FLOOR = 1.0 / 255.0
SKY_Z = 1e9  # Blender writes 1e10 into the Z pass where nothing was hit


def mask_from_alpha(alpha, threshold=0.5):
    """Exact silhouette. With filter_size ~0 the alpha pass is already binary; the
    threshold exists for materials that render partial coverage, and the caller
    records how many pixels were not already 0 or 1."""
    return (alpha > threshold).astype(np.uint8)


def alpha_binarity(alpha):
    """Diagnostic: fraction of pixels whose alpha is neither 0 nor 1."""
    a = np.asarray(alpha, dtype=np.float32)
    soft = np.logical_and(a > 1e-6, a < 1.0 - 1e-6)
    return float(soft.mean())


class DepthError(ArmatureError):
    """A depth this module was asked to encode is not a number an encoder can read.

    F-476a4ee8, wave 18. This module authors every depth control-sequence pixel and had no
    non-finite clause anywhere: `require_finite` appears in `parts`, `gates`, `donor_gate`,
    `lift_solve`, `resample`, `rig_gates` and `turnaround`, and zero times here. Both
    non-finite doors reopened the exact byte collision `GEOMETRY_DEPTH_FLOOR` was
    introduced to close, per pixel.

    Measured on the wave-18 base, on a 2x2 all-geometry mask:

    * `z = [[1, 2], [nan, 3]]` — `nan < SKY_Z` is False, so the NaN was dropped from the
      extent and left in the array. `depth_extent` returned `(1.0, 3.0)`,
      `normalize_depth` returned `nan` at that pixel, and `encode_u8` cast it to byte
      **0** — byte-identical to `BACKGROUND_DEPTH`, the farthest-geometry-vs-void
      collision the reserved floor exists to prevent.
    * `z = [[1, 2], [3, -inf]]` — `-inf < SKY_Z` is True, so `-inf` became `z_min`. `span`
      was `+inf`, the `span <= 0` guard was False, and every finite geometry pixel encoded
      to byte **1**: the whole depth frame a flat plate with no gradient at all, and the
      offending pixel byte 0.

    The realistic consequence rides `stage_render.py::run_export`, where the per-shot window is
    `float(min(mins))` over every frame's `z_min`: ONE `-inf` pixel on ONE frame makes
    `shot_min` `-inf` and EVERY frame's `depth_pershot` control image a flat byte-1 plate.
    The PNGs open, are the right size, are hashed into the manifest, and a paid video
    generation is steered by a depth sequence carrying no depth.

    `stage_render.py::run_export` raises "frame {i}: mask is non-empty but carries no finite
    depth" when `depth_extent` returns None — a message asserting a finiteness property
    the function never measured. It measures it now, and the message is true.

    **Not a `GateFailure`.** No andon stands here: these are refusals from a maths module,
    and the honest halt record is "REFUSED" with `gate` null and the class name under
    `andon`. It defines no `__init__`, so the base stores the receipt the raising line
    passes and manufactures none when a raise carries none.
    """


class NormalError(ArmatureError):
    """A camera-space normal this module was asked to encode is not a direction.

    F-4efe0fad, wave 22 — the half wave 18's `DepthError` did not cover. This module
    authors every control-sequence pixel, and the non-finite clause landed on the DEPTH
    side only: `encode_normal` read `n_cam` with `np.asarray(..., float64)` and no census
    at all, and its normalisation is
    `np.divide(n, norm, out=np.zeros_like(n), where=norm > 1e-8)`. `nan > 1e-8` is False,
    so an unreadable normal took the ZERO fallback and encoded as if it were the zero
    vector.

    Measured on `e8263a3`, on a 4x4 field of camera-facing normals whose baseline encodes
    uniformly to (128, 128, 255):

    * one NaN component -> pixel **(128, 128, 128)**, no refusal;
    * one **+inf** component -> **(0, 128, 128)**;
    * one **-inf** component -> **(0, 128, 128)** — the SAME byte as +inf, so the sign is
      lost too;
    * a legitimately **zero-length** normal -> **(128, 128, 128)**, indistinguishable from
      the unreadable one, which is why it is refused here under its own clause rather than
      folded into the census;
    * an **all-NaN** field -> a UNIFORM (128, 128, 128) plate, returned with no refusal, no
      census and no key naming the population that took the fallback.

    The realistic consequence is `DepthError`'s own, word for word, on the path
    `stage_render.py::run_export` actually runs: `world_normals_to_camera` then
    `encode_normal` writes the PNG straight to `out_dir/normal/` with **no gate between
    them** — the depth line four above it, `depth_extent`, DOES refuse — so a normal
    control sequence that is a flat grey plate, or that carries silently unmarked pixels,
    is written, hashed into the manifest and used to steer a paid generation.

    The second consumer of the same unbounded array is `_neighbour_min_dot` /
    `derive_edge`: `normal_break = m & (min_dot < cos_thresh)` is False for a NaN, so the
    normal break is silently NOT drawn and `diag['normal_break_px']` counts fewer, with no
    clause. Both consumers now run the same census, and the evidence names which one under
    `where`.

    **Not a `GateFailure`,** for `DepthError`'s reason: these are refusals from a maths
    module, and the honest halt record is "REFUSED" with `gate` null and the class name
    under `andon`.
    """


class ChannelEncodeError(ArmatureError):
    """The shared byte writer was handed a value it cannot encode. Channel-neutral.

    F-e8074763, wave 25. `DepthError` and `NormalError` above closed the two PRODUCER
    doors — `depth_extent` / `normalize_depth` in wave 18, `require_readable_normals` in
    wave 22 — and left the shared WRITER open. `encode_u8` is
    `np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)`, the one function in this module
    with no clause, and it is the function that writes every control-sequence byte.

    MEASURED in this worktree on `580af47`:
    `encode_u8([[0.5, nan], [inf, -inf]])` returns `[[128, 0], [255, 0]]`. So:

    * a **NaN** becomes byte **0**, and so does a **-inf**;
    * `encode_u8(BACKGROUND_DEPTH)` is byte **0** too, and `encode_u8(GEOMETRY_DEPTH_FLOOR)`
      is byte 1 — measured beside it in the same run. That is exactly the
      farthest-geometry-vs-void collision `GEOMETRY_DEPTH_FLOOR` exists to prevent,
      arriving through the writer instead of through the producer;
    * a **+inf** becomes byte **255**, the NEAREST-geometry byte, so an unreadable pixel is
      encoded as the closest thing in the shot.

    The only signal the cast gave was a numpy `RuntimeWarning: invalid value encountered in
    cast` — a warning under the default filter, not a refusal, in a repo whose law is that
    a check deciding whether an irreversible step proceeds raises inside the tool
    performing that step.

    **Why channel-neutral rather than `DepthError`.** This writer authors the depth byte,
    the normal RGB triple (`encode_normal` at the bottom of this module) and
    `stage_render`'s P3 difference plate, so naming any one channel in the refusal would be
    a refusal that does not name the andon that pulled. `where` says which caller asked.

    **What was and was not reachable, honestly.** Every producer INSIDE this module is
    guarded, and the wave-18 test asserting the property
    (`tests/test_amend_w18_core_solvers.py`,
    `test_the_encoder_can_never_be_handed_a_non_finite_input_from_this_module`) is scoped to
    exactly that, over one hand-picked finite fixture. The open door is the PUBLIC
    signature: `stage_render.py::run_export` already calls `ch.encode_u8(diff)` on an array this
    module did not normalise, and the next channel or tool that computes its own array gets
    the whole escape. The cost of closing it is one pass over an array the function already
    walks twice.

    **Not a `GateFailure`,** for the reason its two siblings give: a refusal from a maths
    module, halt record "REFUSED" with `gate` null and the class name under `andon`.
    """


def _non_finite_census(vals):
    """`{n, n_finite, n_non_finite, n_nan, n_pos_inf, n_neg_inf}` over a float array.

    The shape `clipstats._stats` already uses: partition, then REPORT the count. A caller
    that refuses and a caller that only wants to know both read the same dict.
    """
    v = np.asarray(vals, dtype=np.float64).ravel()
    finite = np.isfinite(v)
    nan = np.isnan(v)
    return {
        "n": int(v.size),
        "n_finite": int(finite.sum()),
        "n_non_finite": int((~finite).sum()),
        "n_nan": int(nan.sum()),
        "n_pos_inf": int((v == np.inf).sum()),
        "n_neg_inf": int((v == -np.inf).sum()),
    }


def _context_prefix(extra):
    """`"[frame=12, channel=depth_perframe, path=...] "` for `extra`, or `""`.

    F-98b9b966, wave 28 — the message half of the `extra` mapping. See `depth_extent` for
    why it exists; the ORDER is fixed (`frame`, `view`, `channel`, `path`, then whatever
    else the caller sent, sorted) so two halt lines from the same shot sort and read the
    same way, and a `None` value is dropped rather than printed as the word None.
    """
    if not extra:
        return ""
    lead = ("frame", "view", "channel", "path")
    shown = [f"{k}={extra[k]}" for k in lead
             if k in extra and extra[k] is not None]
    shown += [f"{k}={extra[k]}" for k in sorted(extra)
              if k not in lead and extra[k] is not None]
    return f"[{', '.join(shown)}] " if shown else ""


def depth_extent(z, mask, extra=None):
    """(min, max) camera-Z over the pixels where geometry exists, or None — else raise.

    **`extra` names WHERE this call is** (F-98b9b966, wave 28), and every raising function
    in this module takes it as its last parameter, defaulting to None. The mapping is
    merged into the evidence and rendered into the front of the message by
    `_context_prefix`; a call without it is byte-identical to the call before this
    parameter existed.

    The shape is `parts.single_path_segment(value, flag, exc, extra=None)`'s, already in
    the tree (`parts.py`, `ev.update(extra or {})`), so this is an existing convention
    rather than a new one. Why it was needed: all seven raises in the module that authors
    every control-sequence pixel carried pixel counts and NOTHING locating them — no frame
    index, no path, no channel tag, no view — while `stage_render.run_export` calls them
    from inside its per-frame loop, whose own gate evidence already spells `"frame": i`. So
    the tool knows the convention and applied it to its own andon and not to these. An
    operator staging an 81-frame shot for a paid
    generation was told a control-sequence frame carried an unreadable depth pixel and not
    which of the 81, nor which EXR, nor which of depth / normal / edge; the halt record had
    no field that could answer any of those. The caller's key names are `frame`, `path` and
    `channel`, agreed with the tool that passes them; a caller may send others and they ride
    the evidence the same way.

    A key in `extra` OVERWRITES an evidence key of the same name: the caller's frame and
    path are the more specific fact about where a refusal happened.

    The population is the SELECTED one: the pixels the mask admits and the sky test does
    not exclude. A non-finite value OUTSIDE the mask is background, not a depth this
    module authored, and is not this function's business; `SKY_Z` is a finite 1e10 and
    stays excluded by value rather than refused. See `DepthError` for what the two
    non-finite doors did to the encoded byte.
    """
    z = np.asarray(z, dtype=np.float64)
    geometry = np.asarray(mask) > 0
    sel = np.logical_and(geometry, np.logical_or(~np.isfinite(z), z < SKY_Z))
    if not sel.any():
        return None
    vals = z[sel]
    census = _non_finite_census(vals)
    if census["n_non_finite"]:
        # The evidence is spelled as a LITERAL carrying `gate` and `andon`, not built by
        # `dict(census, ...)`: `tests/test_gates.evidence_dicts_missing` is the suite's one
        # evidence walk and it returns `unreadable` — policed by nothing — for a dict whose
        # base is a call result it cannot resolve. A raise the judge cannot read is the
        # spelling a new raise would take to be invisible to the census.
        ev = {"gate": None, "andon": "DepthError",
              "clause": "non_finite_geometry_depth",
              "n": census["n"], "n_finite": census["n_finite"],
              "n_non_finite": census["n_non_finite"], "n_nan": census["n_nan"],
              "n_pos_inf": census["n_pos_inf"], "n_neg_inf": census["n_neg_inf"],
              "n_geometry_px": int(geometry.sum()), "sky_z": SKY_Z}
        ev.update(extra or {})
        raise DepthError(
            _context_prefix(extra)
            + f"{census['n_non_finite']} of {census['n']} selected geometry pixel(s) carry "
            f"a non-finite camera-Z ({census['n_nan']} NaN, {census['n_pos_inf']} +inf, "
            f"{census['n_neg_inf']} -inf). Neither reaches this function's extent as a "
            f"number: `nan < SKY_Z` is False so a NaN is dropped from the extent and left "
            f"in the array, where `encode_u8` casts it to byte 0 — the void byte "
            f"GEOMETRY_DEPTH_FLOOR reserves so that farthest geometry and no geometry are "
            f"not the same byte; and `-inf < SKY_Z` is True so a -inf becomes z_min, the "
            f"span becomes +inf, and every finite geometry pixel encodes to byte 1. "
            f"'No geometry' and 'a pixel we could not read' must not be the same byte",
            ev)
    return float(vals.min()), float(vals.max())


def normalize_depth(z, mask, z_near, z_far, extra=None):
    """Inverse relative depth - near = bright (F19), background reserved.

    `extra` is the caller's location mapping; see `depth_extent` for the shape and why.

    z_near/z_far are the window this frame is normalised against. Passing the
    frame's own extent gives per-frame normalisation; passing the shot's extent
    gives per-shot.

    **Geometry lands on [GEOMETRY_DEPTH_FLOOR, 1], never on the background value.** The
    geometry pixel at `z == z_far` used to map to `(z_far - z_far)/span = 0.0`, which is
    BACKGROUND_DEPTH, and `encode_u8` took both to byte 0: measured, `z = [[1, 2], [3,
    1e10]]` with mask `[[1,1],[1,0]]` over (1, 3) gave bytes `[[255, 128], [0, 0]]` - the
    farthest geometry pixel byte-identical to the void. In a depth control image that
    dissolves the rearmost band of the silhouette into the background, and under per-shot
    normalisation it is a band of pixels on every frame where the subject sits furthest,
    not one pixel. So 0 is reserved for "not geometry" and the geometry range starts one
    byte above it.

    **Two non-finite clauses** (F-476a4ee8, wave 18), because there are two doors into the
    same encoder and only one of them goes through `depth_extent`:

    * the WINDOW. `span <= 0` is False for a NaN `z_near`/`z_far`, and `(z_far - z) / nan`
      sends the whole frame to `nan`, which `encode_u8` casts to byte 0 — the void byte,
      for every geometry pixel in the frame. That door is closed upstream today by
      `shotspec`'s `_require_finite_number` on `depth.window`, but only for callers who
      arrive through a normalised spec, and this module is imported directly.
    * the PIXELS inside the mask, for a caller that supplies its own window rather than
      `depth_extent`'s.

    The decision on a non-finite pixel is REFUSE and say how many, not "write BACKGROUND
    and record it": writing the void byte is the collision itself, and a depth frame with
    unreadable pixels in it is not a control image this pipeline can honestly submit.
    """
    z = np.asarray(z, dtype=np.float64)
    for name, v in (("z_near", z_near), ("z_far", z_far)):
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = float("nan")
        if not np.isfinite(f):
            # The evidence stays a LITERAL and `extra` is merged into it afterwards, never
            # `dict(<literal>, **extra)`: `_census_nodes.clause_literals` reads a Constant
            # inside a Dict node, and a `dict(...)` CALL is not one — the trap wave 26
            # recorded at 64 sites tree-wide. Same reason the comment in `depth_extent`
            # gives for spelling the census keys out rather than `dict(census, ...)`.
            ev = {"gate": None, "andon": "DepthError",
                  "clause": "non_finite_depth_window",
                  "z_near": z_near, "z_far": z_far, name: v}
            ev.update(extra or {})
            raise DepthError(
                _context_prefix(extra)
                + f"{name}={v!r} is not a finite depth, so the normalisation window is not a "
                f"window. `span <= 0` is False for a NaN, so the guard below does not "
                f"fire, `(z_far - z) / span` is NaN at every pixel, and `encode_u8` casts "
                f"every one of them to byte 0 — the value BACKGROUND_DEPTH reserves for "
                f"'no geometry'. The frame opens, is the right size, and carries no depth",
                ev)
    inside = np.asarray(mask) > 0
    if inside.any():
        census = _non_finite_census(z[inside])
        if census["n_non_finite"]:
            ev = {"gate": None, "andon": "DepthError",
                  "clause": "non_finite_geometry_depth",
                  "n": census["n"], "n_finite": census["n_finite"],
                  "n_non_finite": census["n_non_finite"], "n_nan": census["n_nan"],
                  "n_pos_inf": census["n_pos_inf"], "n_neg_inf": census["n_neg_inf"],
                  "n_geometry_px": int(inside.sum())}
            ev.update(extra or {})
            raise DepthError(
                _context_prefix(extra)
                + f"{census['n_non_finite']} of {census['n']} pixel(s) inside the mask carry "
                f"a non-finite depth ({census['n_nan']} NaN, {census['n_pos_inf']} +inf, "
                f"{census['n_neg_inf']} -inf). `encode_u8` casts a NaN to byte 0, which is "
                f"BACKGROUND_DEPTH — so the pixel we could not read and the void we did "
                f"read become the same byte, which is the collision GEOMETRY_DEPTH_FLOOR "
                f"exists to prevent", ev)
    span = float(z_far) - float(z_near)
    if span <= 0:
        # A shot with zero depth extent has no gradient to encode. Everything that
        # is geometry is equally near; say so rather than dividing by zero.
        d = np.where(mask > 0, 1.0, BACKGROUND_DEPTH)
        return d.astype(np.float64)
    d = (float(z_far) - z) / span
    d = np.clip(d, 0.0, 1.0)
    d = GEOMETRY_DEPTH_FLOOR + d * (1.0 - GEOMETRY_DEPTH_FLOOR)
    return np.where(mask > 0, d, BACKGROUND_DEPTH)


def encode_u8(x01, where="encode_u8", extra=None):
    """[0,1] float -> uint8, half-to-even rounding. Refuses a value it cannot encode. · ANDON

    `extra` is the caller's location mapping; see `depth_extent` for the shape and why.
    It is the frame-and-file half of the same question `where` answers for the CALL SITE:
    `where` says which computation, `extra` says which frame of which shot.

    The census is INSIDE the writer (F-e8074763, wave 25). See `ChannelEncodeError` for the
    measured bytes: NaN and -inf both cast to 0 — `BACKGROUND_DEPTH`'s byte — and +inf to
    255, with a numpy `RuntimeWarning` as the only signal. The population is the WHOLE
    array, not a selected subset: unlike `depth_extent` and `require_readable_normals`,
    which are handed a camera measurement and a mask that says which pixels this module
    authored, everything reaching here is already a value this module is about to write as
    a byte, so there is no "outside the mask" for it to be excused by.

    `where` names the caller in the evidence, so a halt line distinguishes the depth plate
    from the normal triple from `stage_render`'s P3 difference. It is a label, never a
    switch: no value of it changes what is refused.
    """
    x = np.asarray(x01, dtype=np.float64)
    census = _non_finite_census(x)
    if census["n_non_finite"]:
        flat = x.ravel()
        first = int(np.flatnonzero(~np.isfinite(flat))[0])
        ev = {"gate": None, "andon": "ChannelEncodeError",
              "clause": "non_finite_encoder_input", "where": where,
              "n": census["n"], "n_finite": census["n_finite"],
              "n_non_finite": census["n_non_finite"], "n_nan": census["n_nan"],
              "n_pos_inf": census["n_pos_inf"], "n_neg_inf": census["n_neg_inf"],
              "first_non_finite_flat_index": first,
              "first_non_finite_value": repr(float(flat[first])),
              "shape": [int(d) for d in x.shape]}
        ev.update(extra or {})
        raise ChannelEncodeError(
            _context_prefix(extra)
            + f"{census['n_non_finite']} of {census['n']} value(s) handed to the byte writer "
            f"are not finite ({census['n_nan']} NaN, {census['n_pos_inf']} +inf, "
            f"{census['n_neg_inf']} -inf; first at flat index {first}). The cast is "
            f"`np.rint(x * 255.0).astype(np.uint8)`, which takes a NaN and a -inf to byte "
            f"0 — the byte BACKGROUND_DEPTH already occupies, so 'no geometry' and 'a pixel "
            f"we could not read' become the same byte, which is the collision "
            f"GEOMETRY_DEPTH_FLOOR reserves byte 1 to prevent — and a +inf to byte 255, the "
            f"NEAREST-geometry byte. numpy signals this with a RuntimeWarning, which is "
            f"silent under the default filter; the byte it writes steers a paid generation",
            ev)
    return np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)


def world_normals_to_camera(n_world, cam_rot_3x3):
    """Rotate world-space normals into camera space.

    cam_rot_3x3 is the camera's world rotation R (columns = camera axes in world
    space). Camera-space n = R^T n_world, which puts +Z toward the viewer because
    Blender's camera looks down its own -Z.
    """
    R = np.asarray(cam_rot_3x3, dtype=np.float64).reshape(3, 3)
    flat = np.asarray(n_world, dtype=np.float64).reshape(-1, 3)
    out = flat @ R  # (R^T n) per row == n @ R
    return out.reshape(np.asarray(n_world).shape)


def require_readable_normals(n_cam, mask, where, extra=None):
    """Refuse a camera-space normal field this module cannot encode. · ANDON

    `extra` is the caller's location mapping; see `depth_extent` for the shape and why.

    The population is the SELECTED one — the pixels the mask admits — which is the rule
    `depth_extent` already states: a value OUTSIDE the mask is background, not a normal
    this module authored, and is not this function's business.

    Two clauses, because the two inputs encode to the SAME byte and are different facts
    about a render: `non_finite_geometry_normal` (a component that is not a number, which
    `np.divide`'s `where=norm > 1e-8` reads as "do not divide" and leaves as the zero
    vector) and `zero_length_geometry_normal` (a direction of length zero, which the same
    guard also leaves at the origin). The census keys are `_non_finite_census`'s, so a
    reader that can reconcile a `DepthError` receipt can reconcile this one.
    """
    n = np.asarray(n_cam, dtype=np.float64)
    m = np.asarray(mask) > 0
    if not m.any():
        return n
    sel = n[m]
    census = _non_finite_census(sel)
    n_geometry_px = int(m.sum())
    if census["n_non_finite"]:
        # A LITERAL evidence dict carrying `gate` and `andon`, not `dict(census, ...)`:
        # `tests/test_gates.evidence_dicts_missing` is the suite's one evidence walk and it
        # returns `unreadable` — policed by nothing — for a dict whose base is a call
        # result it cannot resolve. `depth_extent` spells its own for the same reason.
        ev = {"gate": None, "andon": "NormalError",
              "clause": "non_finite_geometry_normal", "where": where,
              "n": census["n"], "n_finite": census["n_finite"],
              "n_non_finite": census["n_non_finite"], "n_nan": census["n_nan"],
              "n_pos_inf": census["n_pos_inf"], "n_neg_inf": census["n_neg_inf"],
              "n_geometry_px": n_geometry_px}
        ev.update(extra or {})
        raise NormalError(
            _context_prefix(extra)
            + f"{census['n_non_finite']} of {census['n']} normal component(s) inside the "
            f"mask are a non-finite camera-space normal ({census['n_nan']} NaN, "
            f"{census['n_pos_inf']} +inf, {census['n_neg_inf']} -inf) over "
            f"{n_geometry_px} geometry pixel(s). `np.divide(..., where=norm > 1e-8)` is "
            f"False for a NaN, so the pixel takes the ZERO fallback and encodes to "
            f"(128, 128, 128) — the same byte a legitimately zero-length normal produces, "
            f"and +inf and -inf both encode to (0, 128, 128), so the sign is lost as well. "
            f"An all-non-finite field returns a uniform grey plate with no refusal at all, "
            f"and nothing between here and `out_dir/normal/` looks at channel content", ev)
    zero = int((np.linalg.norm(sel, axis=-1) <= 1e-8).sum())
    if zero:
        ev = {"gate": None, "andon": "NormalError",
              "clause": "zero_length_geometry_normal", "where": where,
              "n": census["n"], "n_zero_length_px": zero,
              "n_geometry_px": n_geometry_px}
        ev.update(extra or {})
        raise NormalError(
            _context_prefix(extra)
            + f"{zero} of {n_geometry_px} geometry pixel(s) carry a normal of length zero, "
            f"which is not a direction. It takes the same `where=norm > 1e-8` fallback an "
            f"unreadable normal takes and encodes to the same (128, 128, 128) byte, so the "
            f"two are named apart here rather than left to a reader of the PNG", ev)
    return n


def encode_normal(n_cam, mask, extra=None):
    """Camera-space normals -> uint8 RGB, background black. Refuses what it cannot read.

    `extra` is the caller's location mapping and is passed straight through to both
    refusing functions below; see `depth_extent` for the shape and why.
    """
    n = require_readable_normals(n_cam, mask, "encode_normal", extra=extra)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = np.divide(n, norm, out=np.zeros_like(n), where=norm > 1e-8)
    rgb = encode_u8(n * 0.5 + 0.5, extra=extra)
    m = np.asarray(mask) > 0
    return np.where(m[..., None], rgb, np.uint8(0))


def _erode3(binary, border=False):
    """3x3 binary erosion, numpy only (scipy is not in Blender's python).

    `border` is what lies OUTSIDE the frame, and it is the whole of the border policy this
    module now states once (F-3d03d8bf). `False` reads the outside as background, so any
    mask pixel on the outermost row or column survives as a boundary pixel; `True` reads it
    as more of the same subject, so a pixel there is a boundary pixel only if an IN-FRAME
    neighbour is background. `silhouette` passes `True`; see its docstring for why.
    """
    m = np.asarray(binary, dtype=bool)
    padded = np.pad(m, 1, mode="constant", constant_values=bool(border))
    out = np.ones_like(m, dtype=bool)
    h, w = m.shape
    for dy in range(3):
        for dx in range(3):
            out &= padded[dy : dy + h, dx : dx + w]
    return out


def silhouette(mask):
    """The mask's boundary — WITHOUT the frame border (F-3d03d8bf).

    **The three terms `derive_edge` ORs together used to disagree about the frame border.**
    `_neighbour_max` and `_neighbour_min_dot` each build an `edge` mask and exclude it, with
    the comment "do not compare across the frame border"; this function was
    `m & ~_erode3(m)` with `_erode3` padding False, so every mask pixel on the outermost row
    or column was marked as a geometric edge. Measured on the wave-10 base, on a 6x6 mask
    whose subject fills the bottom three rows: `silhouette(m)[-1].sum()` was 6 — a full row
    of edge pixels drawn along the image boundary, where no geometric discontinuity exists.

    **The policy, decided once and stated here: the frame border is NOT a silhouette.** The
    edge channel is a control input, so this difference is drawn into the picture that
    conditions a generation, and a straight line across the bottom of the frame is a
    statement to the model that the body ENDS there. It does not — the crop ends there. That
    is the same failure `startframe.gate_whole` exists to keep out of a conditioning image,
    one channel over, and a subject reaching the frame edge (feet at the bottom of a
    full-body plate) is the ordinary case rather than the exotic one.

    What is outside the frame is unknown, not empty, so the erosion pads with the subject
    (`border=True`) and a pixel on the border is a boundary pixel only when an in-frame
    neighbour is background. A figure that ENDS inside the frame is unaffected: its boundary
    is a real discontinuity and every pixel of it is still marked.
    """
    m = np.asarray(mask) > 0
    return np.logical_and(m, np.logical_not(_erode3(m, border=True)))


def _neighbour_max(values, mask):
    """Max over the 4-neighbourhood of |value - neighbour|, masked."""
    v = np.asarray(values, dtype=np.float64)
    m = np.asarray(mask) > 0
    out = np.zeros_like(v)
    for axis, shift in ((1, 1), (1, -1), (0, 1), (0, -1)):
        rolled_v = np.roll(v, shift, axis=axis)
        rolled_m = np.roll(m, shift, axis=axis)
        # do not compare across the frame border
        if axis == 1:
            edge = np.zeros_like(m)
            edge[:, 0 if shift == 1 else -1] = True
        else:
            edge = np.zeros_like(m)
            edge[0 if shift == 1 else -1, :] = True
        valid = m & rolled_m & ~edge
        out = np.maximum(out, np.where(valid, np.abs(v - rolled_v), 0.0))
    return out


def _neighbour_min_dot(n_cam, mask):
    """Min over the 4-neighbourhood of the dot product between unit normals."""
    n = np.asarray(n_cam, dtype=np.float64)
    m = np.asarray(mask) > 0
    out = np.ones(n.shape[:2], dtype=np.float64)
    for axis, shift in ((1, 1), (1, -1), (0, 1), (0, -1)):
        rolled_n = np.roll(n, shift, axis=axis)
        rolled_m = np.roll(m, shift, axis=axis)
        if axis == 1:
            edge = np.zeros_like(m)
            edge[:, 0 if shift == 1 else -1] = True
        else:
            edge = np.zeros_like(m)
            edge[0 if shift == 1 else -1, :] = True
        valid = m & rolled_m & ~edge
        dot = np.sum(n * rolled_n, axis=-1)
        out = np.minimum(out, np.where(valid, dot, 1.0))
    return out


def derive_edge(z, n_cam, mask, depth_rel_threshold, normal_angle_deg, extra=None):
    """Geometric edge pass: relative depth break OR normal break OR silhouette.

    `extra` is the caller's location mapping; see `depth_extent` for the shape and why.

    Returns (uint8 image, diagnostics). The image is near-binary by construction
    (F22): every pixel is 0 or 255.

    **All three terms agree about the frame border and none of them draws one**
    (F-3d03d8bf). `_neighbour_max` and `_neighbour_min_dot` exclude it because `np.roll`
    wraps, so an un-excluded comparison would compare the top row against the bottom one;
    `silhouette` excludes it because the crop is not a discontinuity in the subject. The
    two reasons are different and the policy is the same, which is why it is written down
    in one place instead of inferred from three implementations. `silhouette_px` in the
    diagnostics therefore counts real silhouette and not the length of the crop.

    **The two thresholds take a clause of their own** (F-075b3af4, wave 25). They were the
    only numbers in this module reaching a comparison with no finiteness clause, in the one
    module whose stated job is that a pixel it could not read never becomes an ordinary
    byte. MEASURED in this worktree on `580af47`, on a flat camera-facing field:

    * `depth_rel_threshold=nan` and `=inf` both RETURNED, with `depth_break_px: 0` and the
      threshold itself written back into the diagnostics as `nan` / `inf` — `rel > nan` is
      False at every pixel, so the depth term contributes nothing and the diagnostic
      reports the truth about a term that was never asked;
    * `normal_angle_deg=nan` / `=inf` the same, through
      `float(np.cos(np.radians(nan)))` and a second numpy RuntimeWarning;
    * `normal_angle_deg=400.0` RETURNED as well, and silently: `cos(radians(400))` is
      `cos(40°)`, so a request outside the angle's own domain becomes a DIFFERENT, plausible
      threshold rather than a refusal;
    * `None` and `'x'` left as a bare `TypeError` / `ValueError` — not in the
      `ArmatureError` family, so the halt contract records exit 1 "FAILED — an unhandled
      error" where a typed refusal at exit 2 belongs. That is the exact shape wave 22 fixed
      INSIDE `parts.require_finite` (F-fda74b87), and adopting the home carries the fix.

    The diagnostics then published `float(nan)` back into the per-frame record, the bare
    non-JSON token `parts.halt_keysafe` exists to stop reaching a halt line.

    **Honest about reachability: the live path is guarded upstream.**
    `shotspec.normalise_spec` refuses both, including the `[0, 180]` domain, and
    `stage_render.py::run_export` is the only production caller. The gap this closes is that the
    bound lived at the SPEC and not inside the function performing the step, which is where
    this repo puts an andon — the wave-18 SEAM-5 shape, complementary to the spec bound and
    not a second spelling of it. This module already carries two named andons for its other
    two inputs; these are the third and fourth.
    """
    _ev_depth = {"gate": None, "andon": "DepthError",
                 "clause": "depth_rel_threshold_not_finite_and_positive",
                 "where": "derive_edge",
                 "depth_rel_threshold_raw": repr(depth_rel_threshold)}
    _ev_depth.update(extra or {})
    depth_rel_threshold = require_finite(
        "depth_rel_threshold", depth_rel_threshold, DepthError, _ev_depth, positive=True)
    _ev_normal = {"gate": None, "andon": "NormalError",
                  "clause": "normal_angle_deg_not_finite",
                  "where": "derive_edge",
                  "normal_angle_deg_raw": repr(normal_angle_deg)}
    _ev_normal.update(extra or {})
    normal_angle_deg = require_finite(
        "normal_angle_deg", normal_angle_deg, NormalError, _ev_normal, positive=False)
    if not (0.0 <= normal_angle_deg <= 180.0):
        # The DOMAIN, separately from finiteness, because the two are different facts and
        # `cos` accepts both. A cosine is periodic: 400 degrees is 40 degrees and 190 is
        # 170, so an out-of-domain request does not fail here, it succeeds as a threshold
        # nobody asked for. `[0, 180]` is the range over which `cos` is injective and is the
        # same interval `shotspec.normalise_spec` bounds this flag to at the spec.
        _ev_domain = {"gate": None, "andon": "NormalError",
                      "clause": "normal_angle_deg_outside_domain", "where": "derive_edge",
                      "normal_angle_deg": float(normal_angle_deg),
                      "domain_deg": [0.0, 180.0]}
        _ev_domain.update(extra or {})
        raise NormalError(
            _context_prefix(extra)
            + f"normal_angle_deg={normal_angle_deg!r} is outside [0, 180], the interval over "
            f"which the cosine this threshold is taken through is one-to-one. "
            f"`cos(radians(400))` is `cos(radians(40))`, so the request does not fire a "
            f"bound — it becomes a different, plausible break angle, and `normal_break_px` "
            f"reports honestly on a term nobody asked for",
            _ev_domain)
    m = np.asarray(mask) > 0
    # The SECOND consumer of the same unbounded array (F-4efe0fad). `normal_break = m &
    # (min_dot < cos_thresh)` is False for a NaN, so an unreadable normal silently removed
    # its own break from the edge pass and `diag["normal_break_px"]` counted fewer, with no
    # clause anywhere. Same census, same class; `where` says which consumer refused.
    require_readable_normals(n_cam, m, "derive_edge", extra=extra)
    z = np.asarray(z, dtype=np.float64)
    z_safe = np.where(m, z, np.nan)

    grad = _neighbour_max(np.nan_to_num(z_safe, nan=0.0), m)
    local = np.maximum(np.where(m, z, 1.0), 1e-6)
    rel = np.where(m, grad / local, 0.0)
    depth_break = rel > float(depth_rel_threshold)

    min_dot = _neighbour_min_dot(n_cam, m)
    cos_thresh = float(np.cos(np.radians(float(normal_angle_deg))))
    normal_break = np.logical_and(m, min_dot < cos_thresh)

    sil = silhouette(m)
    edge = np.logical_or(np.logical_or(depth_break, normal_break), sil)

    diag = {
        "depth_break_px": int(depth_break.sum()),
        "normal_break_px": int(normal_break.sum()),
        "silhouette_px": int(sil.sum()),
        "edge_px": int(edge.sum()),
        "depth_rel_threshold": float(depth_rel_threshold),
        "normal_angle_deg": float(normal_angle_deg),
    }
    return (edge.astype(np.uint8) * 255), diag


def bbox_of(binary):
    """(x0, y0, x1, y1) inclusive pixel bounds of the True region, or None."""
    m = np.asarray(binary) > 0
    if not m.any():
        return None
    rows = np.flatnonzero(m.any(axis=1))
    cols = np.flatnonzero(m.any(axis=0))
    return (int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1]))


#: Byte-layout digests for the softedge / canny / flow conventions (F-e37bc671).
#: Authored layouts — partner detector weights (HED / PiDiNet / OpenCV Canny models)
#: are not licence-mapped in `docs/license-map.md`, so these encoders never load them.
CHANNEL_CONVENTIONS = {
    "softedge": {
        "layout": "uint8 HxW; white ink on black; soft falloff of geometric edge",
        "licence": "authored geometric; NOT HED/PiDiNet (unmapped)",
        "background": 0,
        "digest_seed": "armature.channels.softedge.v1",
    },
    "canny": {
        "layout": "uint8 HxW; thin geometric edge 0 or 255; NOT OpenCV Canny",
        "licence": "authored geometric; same stance as derive_edge",
        "background": 0,
        "digest_seed": "armature.channels.canny.v1",
    },
    "flow": {
        "layout": "uint8 HxWx3; R=encode_u8(u/max*0.5+0.5), G=same for v, B=0",
        "licence": "authored UV displacement layout; no partner flow weight",
        "background": (0, 0, 0),
        "digest_seed": "armature.channels.flow.v1",
    },
}


def convention_digest(name):
    """Stable digest string for Gate CONV-style pinning of a channel byte layout."""
    import hashlib
    rec = CHANNEL_CONVENTIONS.get(name)
    if rec is None:
        raise ArmatureError(
            f"no channel convention named {name!r}; known: "
            f"{sorted(CHANNEL_CONVENTIONS)}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "unknown_channel_convention", "name": name})
    payload = "|".join([
        rec["digest_seed"], rec["layout"], rec["licence"], repr(rec["background"]),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _box_blur_u8(plane, radius):
    """Separable box blur on a float plane; radius 0 returns the input unchanged."""
    r = int(radius)
    if r <= 0:
        return plane
    pad = np.pad(plane, r, mode="edge")
    kern = 2 * r + 1
    # Horizontal then vertical cumulative sums for O(1) box filter.
    c = np.cumsum(pad, axis=1)
    left = np.concatenate(
        [np.zeros((c.shape[0], 1), dtype=c.dtype), c[:, :-kern]], axis=1)
    h = (c[:, kern - 1:] - left) / float(kern)
    c2 = np.cumsum(h, axis=0)
    top = np.concatenate(
        [np.zeros((1, c2.shape[1]), dtype=c2.dtype), c2[:-kern, :]], axis=0)
    return (c2[kern - 1:, :] - top) / float(kern)


def encode_softedge(edge, radius=2, extra=None):
    """Soft geometric edge → uint8 (F-e37bc671). White ink, background 0.

    `edge` is a geometric edge plane (from `derive_edge` or a binary mask). Softness is
    a box blur of radius `radius` — an authored falloff, not a detector. Non-finite
    refused via `encode_u8`.
    """
    e = np.asarray(edge, dtype=np.float64)
    if e.ndim != 2:
        raise ArmatureError(
            f"encode_softedge expects an HxW plane, got shape {e.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "softedge_bad_shape", "shape": list(e.shape)})
    # Normalise any uint8 0/255 edge into [0,1] before blur.
    if e.max() > 1.0:
        e = e / 255.0
    soft = _box_blur_u8(e, radius)
    soft = np.clip(soft, 0.0, 1.0)
    out = encode_u8(soft, where="encode_softedge", extra=extra)
    return out, {
        "convention": "softedge",
        "digest": convention_digest("softedge"),
        "radius": int(radius),
        "ink_px": int((out > 0).sum()),
        "licence": CHANNEL_CONVENTIONS["softedge"]["licence"],
    }


def encode_canny(edge, extra=None):
    """Thin geometric edge → uint8 0/255 (F-e37bc671). NOT OpenCV Canny.

    Routes that expose a canny ControlNet socket get this authored layout instead of a
    hand-rolled plate. Thresholds mid-grey so a soft plane still collapses to binary.
    """
    e = np.asarray(edge, dtype=np.float64)
    if e.ndim != 2:
        raise ArmatureError(
            f"encode_canny expects an HxW plane, got shape {e.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "canny_bad_shape", "shape": list(e.shape)})
    if e.max() > 1.0:
        e = e / 255.0
    binary = (e > 0.5).astype(np.float64)
    out = encode_u8(binary, where="encode_canny", extra=extra)
    return out, {
        "convention": "canny",
        "digest": convention_digest("canny"),
        "edge_px": int((out > 0).sum()),
        "licence": CHANNEL_CONVENTIONS["canny"]["licence"],
        "note": "authored thin geometric edge; not OpenCV Canny",
    }


def encode_flow(flow_uv, mask, max_mag, extra=None):
    """Camera-plane UV displacement → uint8 RGB (F-e37bc671).

    `flow_uv` is HxWx2 (u, v) in pixels (or any consistent unit). Each component is
    mapped through `encode_u8((c / max_mag) * 0.5 + 0.5)` so zero flow encodes to
    (128, 128, 0); background under the mask is black. `max_mag` must be finite and
    positive — a global constant governing a local feature is refused by requiring the
    caller to state the magnitude bound for THIS clip.
    """
    from .parts import require_finite
    max_mag = require_finite(
        "max_mag", max_mag, ArmatureError,
        {"gate": None, "andon": "ArmatureError",
         "clause": "flow_max_mag_not_finite_and_positive",
         "where": "encode_flow"},
        positive=True)
    f = np.asarray(flow_uv, dtype=np.float64)
    if f.ndim != 3 or f.shape[-1] != 2:
        raise ArmatureError(
            f"encode_flow expects HxWx2, got shape {f.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "flow_bad_shape", "shape": list(f.shape)})
    m = np.asarray(mask) > 0
    u01 = np.clip(f[..., 0] / max_mag * 0.5 + 0.5, 0.0, 1.0)
    v01 = np.clip(f[..., 1] / max_mag * 0.5 + 0.5, 0.0, 1.0)
    r = encode_u8(u01, where="encode_flow.u", extra=extra)
    g = encode_u8(v01, where="encode_flow.v", extra=extra)
    b = np.zeros(f.shape[:2], dtype=np.uint8)
    rgb = np.stack([r, g, b], axis=-1)
    rgb = np.where(m[..., None], rgb, np.uint8(0))
    return rgb, {
        "convention": "flow",
        "digest": convention_digest("flow"),
        "max_mag": float(max_mag),
        "geometry_px": int(m.sum()),
        "licence": CHANNEL_CONVENTIONS["flow"]["licence"],
        "zero_flow_byte": 128,
    }


def normalization_difference(d_per_frame, d_per_shot, mask):
    """P3's measurement: |per-frame - per-shot| over geometry pixels only.

    Returns (abs-difference image as float, stats dict). Pixels outside the mask are
    zero in both inputs by construction and are excluded from the statistics rather
    than diluting them toward zero — a mean over the whole frame would mostly be
    measuring how much background there is.
    """
    m = np.asarray(mask) > 0
    diff = np.abs(np.asarray(d_per_frame, dtype=np.float64) - np.asarray(d_per_shot, dtype=np.float64))
    diff = np.where(m, diff, 0.0)
    if not m.any():
        return diff, {"n_px": 0, "mean_abs": None, "max_abs": None,
                      "signed_mean": None, "n_darker": 0, "n_lighter": 0}
    vals = diff[m]
    signed = (np.asarray(d_per_shot, dtype=np.float64) - np.asarray(d_per_frame, dtype=np.float64))[m]
    return diff, {
        "n_px": int(m.sum()),
        "mean_abs": float(vals.mean()),
        "max_abs": float(vals.max()),
        "signed_mean": float(signed.mean()),
        "n_darker": int((signed < -1e-9).sum()),   # per-shot darker than per-frame
        "n_lighter": int((signed > 1e-9).sum()),
    }
