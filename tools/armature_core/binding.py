"""Procedural rigid-per-segment skinning. No bpy, so the assignment rule is testable.

**Why this arm exists, on the record.** The subject is a clay artist's mannequin: a stack of
rigid segments that articulate at sculpted ball-joints. Rigid segments with a small blend at
the joints are not a fallback for this character — **they are what the character is**. Bone
heat tries to solve a smooth diffusion over a surface that has no smooth deformation in it,
and on this mesh it produced nothing at all (E07 round 1).

## The assignment rule, stated exactly because the manifest quotes it

For each vertex `v` and each deforming bone `i` with segment `head_i -> tail_i` and measured
cross-section radius `r_i`:

1. `d_i` = distance from `v` to the segment (clamped to the segment's ends).
2. `u_i = d_i / r_i` — **normalised** by that bone's own measured radius.
3. `i1` = the bone with the smallest `u`, `i2` = the second smallest.
4. If `i1` and `i2` are **adjacent in the hierarchy** (one is the other's parent) and
   `u_i2 - u_i1 < BLEND_BAND`, the vertex is shared:
   `w_i1 = 0.5 + 0.5 * (u_i2 - u_i1) / BLEND_BAND`, `w_i2 = 1 - w_i1`.
5. Otherwise `w_i1 = 1`.

**Why normalised and not raw distance.** The arms hang close to the torso. On raw distance a
thin arm bone captures torso flesh that is nearer to it than to the thick chest bone, and the
figure gets a slab of belly welded to his elbow. Dividing by each bone's own radius asks
"which bone is this vertex deepest inside", which is the question that has an anatomical answer.

**Why the boundary lands on the sculpted ball.** Two adjacent limb bones share a joint, and
their heads and tails are now the measured ball centres. For near-collinear bones the surface
where `u` ties is the plane through that shared ball — so the rigid boundary is the joint the
sculptor drew, not a fraction anyone chose.

**Why the blend band is dimensionless.** `u` is already a distance divided by that structure's
own measured radius, so a band expressed in `u` scales with the subject instead of encoding
this one. A length in metres here would be a global constant governing a local feature.

Weights sum to exactly 1 on every vertex by construction, which is what keeps skinning the
identity at the bind pose. That sum is **not** what Gate P reads: `rig_gates.gate_p_*`
compare rest-pose world-space vertex positions, the round-tripped positions, and whether
the evaluation is live - none of them looks at a weight sum. The diagnostics below say so
in the dict itself, so no manifest line can quote a constant as corroboration.
"""

import numpy as np

from .errors import ArmatureError

#: Width of the joint blend, in units of normalised distance. Fixed, and dimensionless.
BLEND_BAND = 0.35

#: Character-class → binding arm (F-a4aeb565). Rigid segments remain the default for the
#: clay mannequin; soft/heat-skinned imports use the named alternate behind the flag.
CHARACTER_BINDING = {
    "mannequin_balls": "rigid_segment_weights",
    "imported_sites": "imported_weights",
    "proportion_fallback": "rigid_segment_weights",
    "soft_skinned": "bounded_heat_weights",
}

#: Soft falloff exponent for `bounded_heat_weights`. Dimensionless; larger = closer to
#: rigid winner-take-all. Bounded so a caller cannot turn heat into an unbounded solver.
HEAT_POWER = 2.0
HEAT_POWER_MAX = 8.0


def segment_distance(points, head, tail):
    """Distance from each point to a segment, clamped at both ends."""
    p = np.asarray(points, dtype=np.float64)
    a = np.asarray(head, dtype=np.float64)
    b = np.asarray(tail, dtype=np.float64)
    ab = b - a
    denom = float(ab @ ab)
    if denom <= 0.0:
        return np.linalg.norm(p - a, axis=1)
    t = np.clip(((p - a) @ ab) / denom, 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def rigid_segment_weights(verts, bones, radii, blend_band=BLEND_BAND):
    """Weights for one vertex array. `bones` is an ordered list of dicts with
    name / head / tail / parent. Returns (weights by bone name, diagnostics)."""
    p = np.asarray(verts, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not len(p):
        raise ArmatureError(f"expected a non-empty (N, 3) vertex array, got {p.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "vertices_not_n_by_3"})
    if not bones:
        raise ArmatureError("no deforming bones to assign vertices to",
            {"gate": None, "andon": "ArmatureError",
             "clause": "no_deforming_bones"})
    # THE BAND IS A BOUND ON A MODULE CONSTANT, so it goes through the home that bounds
    # those (F-95c9a97e, wave 25). `if not (blend_band > 0)` refused zero, negatives and
    # NaN — and ADMITTED `inf`, because `inf > 0` is True. MEASURED in this worktree on
    # `580af47` over a three-vertex, two-bone chain with `blend_band=inf`: `gap <
    # blend_band` is True at every vertex, `t = np.clip(gap / inf, 0, 1)` is 0, so `w1 =
    # w2 = 0.5` on EVERY vertex whose two nearest bones are adjacent — weights
    # `{'a': [0.5, 0.5, 0.5], 'b': [0.5, 0.5, 0.5]}`, `blended_fraction: 1.0`. That is a
    # uniformly smooth skin over a subject whose module docstring says, in the second
    # paragraph above, that rigid segments with a small blend at the joints are not a
    # fallback for this character — they are what the character is, and the E07-round-1
    # failure this arm exists to replace. `blend_band_normalised: inf` then rode the
    # manifest, and `json.dumps` writes it as the bare `Infinity` token
    # `parts.halt_keysafe` was written to stop putting on a halt line (measured in the
    # same run).
    #
    # Reachability is the SHAPE and not a live escape: grep across `tools/` finds one call
    # site, `rig_character.py::apply_binding`, and it takes the default.
    #
    # `parts.tightened` gives finiteness, the negative clause and the may-only-tighten
    # clause in one call, against this module's own `BLEND_BAND` — a caller may narrow the
    # band, never widen it. Zero is the tightest legal request THERE and is refused HERE,
    # by the clause below, for the reason it already gave: a hard seam at every joint is a
    # different arm. The two are complementary; `tightened` rules on the direction, this
    # clause rules on the value the arm cannot be.
    # Imported INSIDE the function, not at module scope: `parts` imports
    # `binding.segment_distance` at its own top, so a module-level `from .parts import
    # tightened` here is a genuine cycle — measured in this worktree, `ImportError: cannot
    # import name 'tightened' from partially initialized module 'armature_core.parts'`. The
    # lazy import is the shape `turnaround._pixel_pairs` already uses for numpy, and it
    # keeps the home ONE home rather than spelling the bound a second time here.
    from .parts import tightened

    blend_band = tightened(
        "blend_band", blend_band, BLEND_BAND, ArmatureError,
        {"gate": None, "andon": "ArmatureError", "where": "rigid_segment_weights",
         "module_blend_band": BLEND_BAND, "blend_band_requested": blend_band})
    if not (blend_band > 0):
        raise ArmatureError(
            f"blend band must be positive, got {blend_band}; a zero band is a hard seam at "
            f"every joint and would be a different arm than the one specified",
            {"gate": None, "andon": "ArmatureError",
             "clause": "blend_band_not_positive",
             "blend_band": float(blend_band),
             "module_blend_band": BLEND_BAND})

    names = [b["name"] for b in bones]
    missing = [n for n in names if n not in radii or not (radii[n] > 0)]
    if missing:
        raise ArmatureError(
            f"no positive measured radius for {missing}; the assignment normalises by each "
            f"bone's own radius and cannot fall back to a length in metres",
            {"gate": None, "andon": "ArmatureError",
             "clause": "bone_radius_not_positive"})

    n, m = len(p), len(bones)
    u = np.empty((n, m), dtype=np.float64)
    for j, b in enumerate(bones):
        u[:, j] = segment_distance(p, b["head"], b["tail"]) / float(radii[b["name"]])

    if m == 1:
        only = bones[0]["name"]
        return ({only: np.ones(n, dtype=np.float64)},
                {"rule": "single deforming bone; every vertex belongs to it",
                 "blend_band_normalised": float(blend_band), "vertices": int(n),
                 "vertices_rigid": int(n), "vertices_blended": 0, "blended_fraction": 0.0,
                 "vertices_with_any_weight": int(n), "weight_sum_min": 1.0,
                 "weight_sum_max": 1.0, "vertices_with_weight": {only: int(n)},
                 "vertices_dominated": {only: int(n)}, "bones_with_no_vertices": [],
                 "invariant_by_construction": ["weight_sum_min", "weight_sum_max",
                                               "vertices_with_any_weight"],
                 "invariant_by_construction_note": (
                     "these three are fixed by the assignment rule, not measured; the "
                     "single-bone branch hard-codes 1.0 outright.")})

    order = np.argpartition(u, 1, axis=1)[:, :2]
    first = u[np.arange(n), order[:, 0]]
    second = u[np.arange(n), order[:, 1]]
    swap = second < first
    order[swap] = order[swap][:, ::-1]
    i1, i2 = order[:, 0], order[:, 1]
    u1 = u[np.arange(n), i1]
    u2 = u[np.arange(n), i2]

    index = {b["name"]: j for j, b in enumerate(bones)}
    adjacent = np.zeros((m, m), dtype=bool)
    for b in bones:
        parent = b.get("parent")
        if parent in index:
            adjacent[index[b["name"]], index[parent]] = True
            adjacent[index[parent], index[b["name"]]] = True

    gap = u2 - u1
    blended = adjacent[i1, i2] & (gap < blend_band)
    t = np.clip(gap / blend_band, 0.0, 1.0)
    w1 = np.where(blended, 0.5 + 0.5 * t, 1.0)
    w2 = np.where(blended, 1.0 - w1, 0.0)

    weights = {name: np.zeros(n, dtype=np.float64) for name in names}
    stack = np.zeros((m, n), dtype=np.float64)
    np.add.at(stack, (i1, np.arange(n)), w1)
    np.add.at(stack, (i2, np.arange(n)), w2)
    for j, name in enumerate(names):
        weights[name] = stack[j]

    totals = stack.sum(axis=0)
    counts = {name: int((stack[j] > 0).sum()) for j, name in enumerate(names)}
    dominated = {name: int((i1 == j).sum()) for j, name in enumerate(names)}
    diagnostics = {
        "rule": ("nearest bone segment by distance normalised by that bone's own measured "
                 "cross-section radius; a fixed blend band of "
                 f"{blend_band} in normalised units where the two nearest bones are "
                 "adjacent in the hierarchy"),
        "blend_band_normalised": float(blend_band),
        "vertices": int(n),
        "vertices_rigid": int((~blended).sum()),
        "vertices_blended": int(blended.sum()),
        "blended_fraction": float(blended.sum()) / n,
        "vertices_with_any_weight": int((totals > 0).sum()),
        "weight_sum_min": float(totals.min()),
        "weight_sum_max": float(totals.max()),
        "vertices_with_weight": counts,
        "vertices_dominated": dominated,
        "bones_with_no_vertices": sorted(k for k, v in counts.items() if v == 0),
        # weight_sum_min / weight_sum_max / vertices_with_any_weight cannot take any other
        # value: w2 = 1.0 - w1 with w1 in [0.5, 1.0) sums to exactly 1.0 in IEEE754
        # (Sterbenz), the rigid branch is 1.0 + 0.0, and i1 != i2 always. Measured over
        # 200 random 500-vertex clouds against a 4-bone chain, the set of distinct
        # (min, max) pairs is exactly {(1.0, 1.0)}. Labelled here so no report can quote
        # them as corroboration that the partition of unity holds - a check that cannot
        # fail is not a check.
        "invariant_by_construction": ["weight_sum_min", "weight_sum_max",
                                      "vertices_with_any_weight"],
        "invariant_by_construction_note": (
            "these three are fixed by the assignment rule (w1 + w2 == 1.0 exactly in "
            "IEEE754 by Sterbenz, i1 != i2 always), not measured. A real measurement of "
            "the partition of unity is the weight sum AS WRITTEN INTO THE GLB after "
            "export, where the value can differ."),
    }
    return weights, diagnostics


def resolve_binding(character_class):
    """Which weight arm a character class uses (F-a4aeb565). Unknown class refuses."""
    arm = CHARACTER_BINDING.get(character_class)
    if arm is None:
        raise ArmatureError(
            f"character_class={character_class!r} has no binding arm; known: "
            f"{sorted(CHARACTER_BINDING)}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "unknown_binding_character_class",
             "character_class": character_class,
             "known": sorted(CHARACTER_BINDING)})
    return arm


def validate_imported_weights(verts, bones, weights_by_bone, sum_tol=1e-5):
    """Validate pre-authored / exported soft weights for Gate P diagnostics (F-a4aeb565).

    Does not invent weights — refuses shape, non-finite, and partition-of-unity failures
    so a soft-skinned GLB either arrives with readable weights or stops here rather than
    growing a one-off inside an instrument. Returns `(weights, diagnostics)`.
    """
    p = np.asarray(verts, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not len(p):
        raise ArmatureError(
            f"expected a non-empty (N, 3) vertex array, got {p.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "vertices_not_n_by_3"})
    if not bones:
        raise ArmatureError(
            "no deforming bones to validate imported weights against",
            {"gate": None, "andon": "ArmatureError",
             "clause": "no_deforming_bones"})
    names = [b["name"] for b in bones]
    n = len(p)
    missing = [name for name in names if name not in weights_by_bone]
    if missing:
        raise ArmatureError(
            f"imported weights missing bone(s) {missing}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "imported_weights_missing_bone", "missing": missing})
    weights = {}
    for name in names:
        w = np.asarray(weights_by_bone[name], dtype=np.float64).reshape(-1)
        if w.shape[0] != n:
            raise ArmatureError(
                f"imported weights for {name!r} length {w.shape[0]} != n_verts {n}",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "imported_weights_length_mismatch",
                 "bone": name, "got": int(w.shape[0]), "n_verts": n})
        if not np.isfinite(w).all():
            raise ArmatureError(
                f"imported weights for {name!r} carry non-finite values",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "imported_weights_not_finite", "bone": name})
        if (w < 0).any():
            raise ArmatureError(
                f"imported weights for {name!r} carry negative values",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "imported_weights_negative", "bone": name})
        weights[name] = w
    totals = sum(weights[name] for name in names)
    lo, hi = float(totals.min()), float(totals.max())
    if lo < 1.0 - sum_tol or hi > 1.0 + sum_tol:
        raise ArmatureError(
            f"imported weights sum to [{lo}, {hi}] outside 1±{sum_tol}; Gate P needs a "
            f"partition of unity at bind",
            {"gate": None, "andon": "ArmatureError",
             "clause": "imported_weights_sum_not_one",
             "weight_sum_min": lo, "weight_sum_max": hi, "sum_tol": sum_tol})
    counts = {name: int((weights[name] > 0).sum()) for name in names}
    dominated = {
        name: int((np.argmax(np.stack([weights[n] for n in names], axis=0), axis=0)
                   == j).sum())
        for j, name in enumerate(names)
    }
    diagnostics = {
        "rule": "imported_weights_validator — authored/exported weights, not solved here",
        "binding_arm": "imported_weights",
        "vertices": int(n),
        "vertices_with_any_weight": int((totals > 0).sum()),
        "weight_sum_min": lo,
        "weight_sum_max": hi,
        "vertices_with_weight": counts,
        "vertices_dominated": dominated,
        "bones_with_no_vertices": sorted(k for k, v in counts.items() if v == 0),
        "gate_p_readable": True,
    }
    return weights, diagnostics


def bounded_heat_weights(verts, bones, radii, power=HEAT_POWER):
    """Bounded inverse-distance soft weights for heat-skinned characters (F-a4aeb565).

    Clearly named alternate behind `character_class='soft_skinned'`. Not the mannequin
    default — rigid segments remain what the clay figure is. Each vertex gets
    `w_i ∝ 1 / (u_i ** power)` over normalised segment distances, renormalised to sum 1.
    Power is tightened to `HEAT_POWER` (may only tighten) and capped at `HEAT_POWER_MAX`.
    """
    from .parts import tightened

    p = np.asarray(verts, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not len(p):
        raise ArmatureError(
            f"expected a non-empty (N, 3) vertex array, got {p.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "vertices_not_n_by_3"})
    if not bones:
        raise ArmatureError(
            "no deforming bones to assign vertices to",
            {"gate": None, "andon": "ArmatureError",
             "clause": "no_deforming_bones"})
    power = tightened(
        "power", power, HEAT_POWER, ArmatureError,
        {"gate": None, "andon": "ArmatureError", "where": "bounded_heat_weights",
         "module_heat_power": HEAT_POWER, "power_requested": power})
    if not (power > 0) or not (power <= HEAT_POWER_MAX):
        raise ArmatureError(
            f"heat power must be in (0, {HEAT_POWER_MAX}], got {power}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "heat_power_out_of_bounds",
             "power": float(power), "heat_power_max": HEAT_POWER_MAX})
    names = [b["name"] for b in bones]
    missing = [n for n in names if n not in radii or not (radii[n] > 0)]
    if missing:
        raise ArmatureError(
            f"no positive measured radius for {missing}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "bone_radius_not_positive"})
    n, m = len(p), len(bones)
    u = np.empty((n, m), dtype=np.float64)
    for j, b in enumerate(bones):
        u[:, j] = segment_distance(p, b["head"], b["tail"]) / float(radii[b["name"]])
    # Floor so a vertex exactly on a segment does not produce inf weight.
    u = np.maximum(u, 1e-8)
    inv = u ** (-float(power))
    totals = inv.sum(axis=1, keepdims=True)
    normed = inv / totals
    weights = {name: normed[:, j].copy() for j, name in enumerate(names)}
    row_sums = normed.sum(axis=1)
    counts = {name: int((normed[:, j] > 0).sum()) for j, name in enumerate(names)}
    dominated = {
        name: int((np.argmax(normed, axis=1) == j).sum()) for j, name in enumerate(names)
    }
    diagnostics = {
        "rule": (f"bounded_heat_weights — inverse normalised distance to power "
                 f"{float(power)}; alternate soft-skin arm, not the mannequin default"),
        "binding_arm": "bounded_heat_weights",
        "heat_power": float(power),
        "vertices": int(n),
        "vertices_with_any_weight": int((row_sums > 0).sum()),
        "weight_sum_min": float(row_sums.min()),
        "weight_sum_max": float(row_sums.max()),
        "vertices_with_weight": counts,
        "vertices_dominated": dominated,
        "bones_with_no_vertices": sorted(k for k, v in counts.items() if v == 0),
        "gate_p_readable": True,
        "blended_fraction": 1.0,
    }
    return weights, diagnostics


def bind_weights(verts, bones, radii, character_class="mannequin_balls",
                 imported=None, **kwargs):
    """Dispatch binding by character class; rigid segments remain the default."""
    arm = resolve_binding(character_class)
    if arm == "rigid_segment_weights":
        return rigid_segment_weights(verts, bones, radii, **kwargs)
    if arm == "imported_weights":
        if imported is None:
            raise ArmatureError(
                "character_class requires imported weights; pass imported={{bone: w}}",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "imported_weights_required",
                 "character_class": character_class})
        return validate_imported_weights(verts, bones, imported)
    if arm == "bounded_heat_weights":
        return bounded_heat_weights(verts, bones, radii, **kwargs)
    raise ArmatureError(
        f"binding arm {arm!r} is registered but has no dispatcher branch",
        {"gate": None, "andon": "ArmatureError",
         "clause": "binding_arm_unimplemented", "arm": arm})
