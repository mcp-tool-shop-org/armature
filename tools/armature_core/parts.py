"""Split a shell mesh into rigid per-segment parts. No bpy, so the rules are testable.

**A real stop-motion armature in software.** Separate rigid parts articulating at the
sculpted balls, parented to bones, with **no deformation anywhere** — no skin weights, no
armature modifier, nothing to shred and nothing to step. Commissioned as E07 arm (c) after
both deforming arms failed at the Director's eye (ruled a hard fail), on the ranked
recommendation of Comfy Agent consult #5.

Two prescriptions from that consult are binding here, and both are encoded in this module:

**1 · Assignment is by SPATIAL REGION, never by connectivity.** `Separate → By Loose Parts`
explodes on this mesh class: the performer carries **67 interior shells**, so a connectivity
split produces 67 fragments that have nothing to do with anatomy. Every face — interior
shells included — is assigned by a nearest-bone-segment test on its centroid, normalised by
each bone's own measured radius for the same reason the deforming arm normalised: a thin arm
bone must not capture torso flesh that merely happens to be nearer to it.

**2 · Collar overlap at every joint.** Each part is extended *past* the joint plane into its
neighbour's territory, so adjacent parts interpenetrate exactly as a physical ball-jointed
armature does and **no gap opens under articulation**. The collar is a fixed fraction of
**that joint's own measured ball radius** — per structure, never a length in metres — and the
per-joint values are recorded in the manifest.

The primary assignment is a **partition**: every face belongs to exactly one part, and that
is what the accounting gate checks. The collar is duplication layered on top, counted
separately, so the two can never be confused in the record.
"""

import numpy as np

from .binding import segment_distance
from .errors import ArmatureError, GateFailure

#: Collar depth as a fraction of that joint's own measured ball radius.
COLLAR_BALL_FRACTION = 0.9
#: Collar RADIUS about the joint axis, as a multiple of that joint's own radius. Without
#: it the collar is an infinite slab: measured on the performer, `shoulder.L` borrowed
#: 16,023 faces spanning x from -0.047 to +0.167 -- a slice straight across the body,
#: reaching 0.219 from the shoulder ball, nine times its 0.0242 radius. That slab is the
#: flat blade that appeared at the armpit the moment the arm rotated.
COLLAR_RADIAL_MULTIPLE = 2.0


class GatePartsAccounting(GateFailure):
    """Arm (c)'s andon: the mesh was not partitioned cleanly into the registered parts.

    **The direction nothing else bounds.** Every other check in this route looks at parts
    that exist: the registration gate reads their names, the rigidity gate reads their
    motion, the atlas gate reads the texture. None of them can see a face that was assigned
    to nothing and silently dropped on separation, or a face handed to two parts and
    duplicated into the render. The figure would simply be missing a patch, or carrying a
    doubled one, and every other gate would report green on the parts that remain.
    """

    gate = "PARTS"


def assign_faces(centroids, bones, radii, normalise=False):
    """Assign every face to one part by nearest bone segment to its centroid.

    `normalise=False` is the consult's prescription and the default: **plain nearest bone
    segment**, exactly "face-centroid vs bone-segment nearest test".

    `normalise=True` divides each distance by that bone's own measured radius — the rule arm
    (b) used, where it was right, because blended weights let a thin arm bone steal torso
    flesh that merely happens to be nearer to it. **Measured on this performer, it is wrong
    here:** the neck bone is 0.05 long and thin, sits between the chest and the head which are
    both far fatter, and under normalisation it wins **zero of 306,110 faces** — Gate PARTS
    fires on an empty part. A short bone between two fat ones is squeezed out by the very
    normalisation that protects a thin bone from a fat neighbour. Kept runnable and reported,
    because the difference between the two is a measurement and not an opinion.
    """
    c = np.asarray(centroids, dtype=np.float64)
    if c.ndim != 2 or c.shape[1] != 3 or not len(c):
        raise ArmatureError(f"expected a non-empty (N, 3) centroid array, got {c.shape}")
    if not bones:
        raise ArmatureError("no parts to assign faces to")
    if normalise:
        missing = [b["name"] for b in bones if not (radii.get(b["name"], 0) > 0)]
        if missing:
            raise ArmatureError(
                f"no positive measured radius for {missing}; normalised assignment divides "
                f"by each part's own radius and will not fall back to a length in metres")

    u = np.empty((len(c), len(bones)), dtype=np.float64)
    for j, b in enumerate(bones):
        d = segment_distance(c, b["head"], b["tail"])
        u[:, j] = d / float(radii[b["name"]]) if normalise else d
    return np.argmin(u, axis=1)


def gate_parts_accounting(labels, n_faces, bone_names):
    """Gate PARTS · ANDON — the partition is total, exclusive, and over the registered list."""
    labels = np.asarray(labels)
    ev = {"n_faces": int(n_faces), "n_labels": int(len(labels)),
          "n_parts_registered": len(bone_names)}
    problems = []

    if len(labels) != n_faces:
        problems.append(f"{len(labels)} assignments for {n_faces} faces")
    if len(labels):
        if labels.min() < 0:
            problems.append(f"{int((labels < 0).sum())} face(s) assigned to nothing")
        if labels.max() >= len(bone_names):
            problems.append(f"a face is assigned to part index {int(labels.max())}, "
                            f"outside the registered list of {len(bone_names)}")

    counts = {name: int((labels == i).sum()) for i, name in enumerate(bone_names)}
    empty = sorted(n for n, v in counts.items() if v == 0)
    ev.update({"faces_per_part": counts, "parts_with_no_faces": empty,
               "total_assigned": int(sum(counts.values()))})
    if ev["total_assigned"] != n_faces:
        problems.append(f"{ev['total_assigned']} faces assigned but the mesh has {n_faces}")
    if empty:
        problems.append(f"{len(empty)} registered part(s) would be an empty object: {empty}")

    if problems:
        raise GatePartsAccounting(
            "the mesh was not partitioned cleanly into the registered parts: "
            + "; ".join(problems), ev)
    ev["verdict"] = (f"{n_faces} faces partitioned across {len(bone_names)} parts, "
                     f"each face exactly once")
    return ev


def joint_planes(bones, marks, ball_radius, limb_radius,
                 collar_fraction=COLLAR_BALL_FRACTION):
    """One cut plane per parent-child pair: the measured joint, and its collar depth.

    The plane passes through the **measured ball centre** — the child bone's head, which
    round 2 moved onto the sculpted ball — with its normal along the child's own limb axis.
    Joints that carry no sculpted ball (the torso chain, the neck, the head) fall back to
    that bone's measured cross-section radius, and say so in `radius_source`, because a
    fallback that looks like a measurement is the thing this repo keeps catching.
    """
    index = {b["name"]: b for b in bones}
    out = []
    for b in bones:
        parent = b.get("parent")
        if parent not in index:
            continue
        head = np.asarray(b["head"], dtype=np.float64)
        axis = np.asarray(b["tail"], dtype=np.float64) - head
        length = float(np.linalg.norm(axis))
        if length <= 0:
            raise ArmatureError(f"joint {parent}->{b['name']}: the child bone has no length, "
                                f"so the cut plane has no normal")
        r = ball_radius.get(b["name"])
        source = "measured sculpted ball radius"
        if r is None or not (r > 0):
            r = limb_radius.get(b["name"])
            source = "FALLBACK — this joint carries no sculpted ball; that bone's own " \
                     "measured cross-section radius is used instead"
        if r is None or not (r > 0):
            # Found by its own test: without the None guard this line raised TypeError
            # instead of the ArmatureError it exists to raise, so the failure path was
            # broken in exactly the case it was written for.
            raise ArmatureError(f"joint {parent}->{b['name']}: no positive radius from a "
                                f"ball or a cross-section; the collar cannot be sized")
        out.append({
            "parent": parent, "child": b["name"],
            "point": [float(v) for v in head],
            "normal": [float(v) for v in (axis / length)],
            "radius": float(r), "radius_source": source,
            "collar_fraction": float(collar_fraction),
            "collar": float(r * collar_fraction),
        })
    return out


def clamp_to_joint_planes(centroids, labels, bone_names, planes):
    """No part may own geometry on the far side of its OWN joint plane.

    **The chest tear, and the rule that closes it.** Nearest-segment assignment let
    `shoulder.L` own a broad patch of torso *surface* behind its own shoulder ball — the
    shoulder bone is simply nearer to the armpit than the chest bone is. That patch rotated
    away with the arm and left a raw opening in the chest, visible as a torn seam at 1:1.

    The fix is not a cap and not a wider collar: it is a boundary. A limb part's territory
    **begins at its own measured joint plane**; anything it was given behind that plane goes
    back to its parent. The parts still interpenetrate, because the collar then reaches
    `collar` either side of the same plane — so the seam is covered without any part carrying
    a piece of its neighbour's body that swings away when it moves.

    Per joint and bounded by that joint's own measured plane. No length in metres appears.
    """
    c = np.asarray(centroids, dtype=np.float64)
    labels = np.asarray(labels).copy()
    index = {name: i for i, name in enumerate(bone_names)}
    detail = []
    for plane in planes:
        p = np.asarray(plane["point"], dtype=np.float64)
        n = np.asarray(plane["normal"], dtype=np.float64)
        child, parent = index[plane["child"]], index[plane["parent"]]
        behind = np.flatnonzero((labels == child) & (((c - p) @ n) < 0.0))
        labels[behind] = parent
        detail.append({"joint": f"{plane['parent']}->{plane['child']}",
                       "faces_returned_to_parent": int(len(behind))})
    return labels, detail


def collar_faces(centroids, labels, bone_names, planes,
                 radial_multiple=COLLAR_RADIAL_MULTIPLE):
    """Faces each part borrows from its neighbour so the two interpenetrate at the joint.

    A collar is a **disc around the joint**, not a slab across the figure. Two bounds, both
    per structure:

    * along the joint normal — within `collar` either side of the plane, and
    * about the joint axis — within `radial_multiple` × that joint's own radius of the point.

    **The second bound is the fix for the armpit blade.** Without it the plane test alone
    admits everything in an infinite slab, and on this performer the shoulder collar reached
    across the torso to x = -0.047 and out to 0.219 from the ball — nine times its radius.
    Those faces rotated with the arm and swept out of the body as a flat serrated shard,
    visible at full-body scale. Nothing else could see it: the partition stayed valid, the
    parts stayed rigid, the arc still arrived whole.
    """
    c = np.asarray(centroids, dtype=np.float64)
    labels = np.asarray(labels)
    index = {name: i for i, name in enumerate(bone_names)}
    borrowed = {name: [] for name in bone_names}
    detail = []
    for plane in planes:
        p = np.asarray(plane["point"], dtype=np.float64)
        n = np.asarray(plane["normal"], dtype=np.float64)
        collar = float(plane["collar"])
        s = (c - p) @ n
        radial = np.linalg.norm((c - p) - s[:, None] * n[None, :], axis=1)
        near = radial <= radial_multiple * float(plane["radius"])
        pi, ci = index[plane["parent"]], index[plane["child"]]

        into_parent = np.flatnonzero((labels == ci) & (s >= 0.0) & (s <= collar) & near)
        into_child = np.flatnonzero((labels == pi) & (s < 0.0) & (s >= -collar) & near)
        borrowed[plane["parent"]].append(into_parent)
        borrowed[plane["child"]].append(into_child)
        detail.append({"joint": f"{plane['parent']}->{plane['child']}",
                       "collar": collar, "radius": plane["radius"],
                       "collar_radius": float(radial_multiple * plane["radius"]),
                       "radius_source": plane["radius_source"],
                       "faces_lent_to_parent": int(len(into_parent)),
                       "faces_lent_to_child": int(len(into_child))})

    out = {}
    for name, chunks in borrowed.items():
        joined = np.concatenate(chunks) if chunks else np.array([], dtype=np.int64)
        out[name] = np.unique(joined).astype(np.int64)
    return out, detail


class GateRigidArrival(GateFailure):
    """Arm (c)'s andon: the authored arc arrived whole, and each part stayed rigid.

    Two failures live here and neither is visible anywhere else.

    **Arrival.** E03's Ruling 9 is the standing warning: a distinctness gate cannot detect a
    wrong-MAGNITUDE performance, and arm (a) proved the point on this very character — every
    gate passed while an authored 90 degrees arrived as a third of itself. A rigidly parented
    part has an exactly predictable destination: its bone's own rest-to-pose transform applied
    to its rest vertices. So the check is equality with that, not "did something move".

    **Rigidity.** The whole promise of this route is that nothing deforms. If a part were
    accidentally bound as well as parented, or parented to the wrong space, its internal
    distances would change while the figure still looked broadly right in a thumbnail.
    """

    gate = "RIGID"


def gate_rigid_arrival(observations, bbox_diagonal, epsilon_frac=1e-4, rigidity_frac=1e-5):
    """Gate RIGID · ANDON — per part: posed == bone transform applied to rest, and rigid.

    `observations` is one record per part with `name`, `max_transform_error` (max distance
    between the posed vertices and the bone transform applied to the rest vertices),
    `max_pair_distance_change` (largest change in any sampled intra-part vertex distance),
    and `max_displacement`. `authored_max` is the largest bone-level displacement the action
    calls for, computed from the armature rather than from the mesh.
    """
    tol = epsilon_frac * float(bbox_diagonal)
    rig_tol = rigidity_frac * float(bbox_diagonal)
    ev = {"transform_tolerance": tol, "rigidity_tolerance": rig_tol,
          "bbox_diagonal": float(bbox_diagonal), "parts": observations}
    problems = []

    if not observations:
        raise GateRigidArrival("no parts were observed under the pose; the gate would be a "
                               "check that cannot fail", ev)
    for rec in observations:
        if rec["max_transform_error"] > tol:
            problems.append(
                f"{rec['name']}: posed geometry is {rec['max_transform_error']:.3e} from "
                f"where its bone's own transform puts it (> {tol:.3e})")
        if rec["max_pair_distance_change"] > rig_tol:
            problems.append(
                f"{rec['name']}: internal distances changed by up to "
                f"{rec['max_pair_distance_change']:.3e} (> {rig_tol:.3e}) — this part is "
                f"deforming, and this route promises no deformation anywhere")

    moved = max(r["max_displacement"] for r in observations)
    ev["figure_max_displacement"] = float(moved)
    if moved <= tol:
        problems.append(
            f"the whole figure moved at most {moved:.3e} under the authored arc; nothing "
            f"arrived at all")

    if problems:
        ev["problems"] = problems[:12]
        raise GateRigidArrival("the authored arc did not arrive whole: "
                               + "; ".join(problems[:6]), ev)
    ev["verdict"] = (f"{len(observations)} parts each landed on their own bone transform; "
                     f"figure max displacement {moved:.5f}")
    return ev


class GatePartsDeterminism(GateFailure):
    """Two builds of the same parts disagreed. Compared as parsed geometry, never bytes."""

    gate = "D"


def gate_parts_determinism(a, b, bbox_diagonal, length_frac=1e-6):
    """Gate D · ANDON — a second build produced the same parts.

    `a` and `b` map part name to {"n_verts", "n_faces", "positions"} where positions is a
    lexicographically sorted (N, 3) array. Sorted because a rebuild may emit the same
    geometry in a different order and that is not a difference in the rig; compared as arrays
    because a file hash would fire on exporter noise and, worse, a hash MATCH would be quoted
    as proof of a property it never tested.
    """
    tol = length_frac * float(bbox_diagonal)
    ev = {"tolerance": tol, "n_parts_a": len(a), "n_parts_b": len(b)}
    problems = []
    if set(a) != set(b):
        problems.append(f"part sets differ: only in first {sorted(set(a) - set(b))[:8]}, "
                        f"only in second {sorted(set(b) - set(a))[:8]}")
    worst = {"part": None, "delta": 0.0}
    for name in sorted(set(a) & set(b)):
        pa, pb = a[name], b[name]
        if pa["n_verts"] != pb["n_verts"] or pa["n_faces"] != pb["n_faces"]:
            problems.append(f"{name}: {pa['n_verts']}v/{pa['n_faces']}f vs "
                            f"{pb['n_verts']}v/{pb['n_faces']}f")
            continue
        d = float(np.abs(np.asarray(pa["positions"]) - np.asarray(pb["positions"])).max())
        if d > worst["delta"]:
            worst = {"part": name, "delta": d}
        if d > tol:
            problems.append(f"{name}: vertices differ by up to {d:.3e} (> {tol:.3e})")
    ev["worst"] = worst
    if problems:
        ev["problems"] = problems[:12]
        raise GatePartsDeterminism("two builds produced different parts: "
                                   + "; ".join(problems[:6]), ev)
    ev["verdict"] = f"{len(a)} parts identical across two builds"
    return ev
