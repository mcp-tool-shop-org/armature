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
identity at the bind pose and is the property Gate P reads.
"""

import numpy as np

from .errors import ArmatureError

#: Width of the joint blend, in units of normalised distance. Fixed, and dimensionless.
BLEND_BAND = 0.35


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
        raise ArmatureError(f"expected a non-empty (N, 3) vertex array, got {p.shape}")
    if not bones:
        raise ArmatureError("no deforming bones to assign vertices to")
    if not (blend_band > 0):
        raise ArmatureError(
            f"blend band must be positive, got {blend_band}; a zero band is a hard seam at "
            f"every joint and would be a different arm than the one specified"
        )

    names = [b["name"] for b in bones]
    missing = [n for n in names if n not in radii or not (radii[n] > 0)]
    if missing:
        raise ArmatureError(
            f"no positive measured radius for {missing}; the assignment normalises by each "
            f"bone's own radius and cannot fall back to a length in metres"
        )

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
                 "vertices_dominated": {only: int(n)}, "bones_with_no_vertices": []})

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
    }
    return weights, diagnostics
