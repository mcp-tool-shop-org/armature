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

import math

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
    """Gate PARTS · ANDON — the partition is total, exclusive, and over the registered list.

    **The empty population is refused** (F-1dd37d93's family, measured 2026-09-04):
    `gate_parts_accounting([], 0, [])` returned green with the verdict "0 faces
    partitioned across 0 parts, each face exactly once". Every clause here compares a
    count to another count, and over an empty mesh with an empty registered list they all
    compare 0 to 0.

    The evidence carries `gate` and `andon` (F-f2f42e4a): `stage_render` prints
    `GATE_FAILURE <exc.gate>` beside `GATE_EVIDENCE <json>`, and gate ids are shared
    across andon families, so the JSON has to name which andon pulled.
    """
    labels = np.asarray(labels)
    ev = {"gate": "PARTS", "andon": "GatePartsAccounting",
          "n_faces": int(n_faces), "n_labels": int(len(labels)),
          "n_parts_registered": len(bone_names)}
    problems = []

    if not len(bone_names) or not int(n_faces):
        raise GatePartsAccounting(
            f"the partition was gated over {int(n_faces)} face(s) across "
            f"{len(bone_names)} registered part(s): every clause below compares 0 to 0 "
            f"and the gate would be a check that cannot fail. A comparison over nothing "
            f"must not report agreement", ev)

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


#: The tolerances Gate RIGID and Gate D own, as fractions of the subject's own bbox
#: diagonal — never as lengths in metres. **This module owns them; a caller may only
#: TIGHTEN.** Carried from core-gates' wave-8 threshold-ARGUMENT sweep (which removed the
#: same keywords from four rig gates) and from `assembly.gate_slot_ceiling`'s `cap` clause,
#: which is the shape this repo already settled on: a bound the caller supplies is a bound
#: the caller can raise, and a gate whose tolerance grows with the defect it is measuring
#: cannot see the defect. Neither production call site passes one — `rig_parts.py:490` and
#: `rig_parts.py:503` both take the defaults — so the freedom bought nothing and the
#: loosening direction was unbounded.
RIGID_TRANSFORM_FRAC = 1e-4
RIGID_RIGIDITY_FRAC = 1e-5
DETERMINISM_LENGTH_FRAC = 1e-6


def require_finite(name, value, gate_cls, ev, positive=True):
    """`float(value)` if it is a number a gate can compare against, else raise `gate_cls`.

    **The one implementation of wave 10's rule 4** — a verdict on a non-finite number is a
    refusal, never a PASS — shared by the four gate-bearing modules that compare a
    measurement: this one, `startframe.gate_alpha`/`gate_backdrop`, `resample.
    require_rotation` and `lift_solve.gate_round_trip`. It raises the CALLER's own andon
    class and writes into the caller's own evidence dict, so each module keeps its gate id
    and its evidence; nothing here is a second copy of `math.isfinite` with a different
    message.

    **Why the direction matters.** `nan > x` and `nan < x` are BOTH False, so a NaN walks
    through every comparison a gate makes, in both directions at once, and lands on the
    verdict line — measured 2026-09-04 on `_tightened` below (`float('nan') > 1e-4` is
    False, so a NaN was accepted as a *tightening*), on `startframe.gate_alpha` (a full
    PASS verdict reading "nan of the frame is transparent") and on `gate_backdrop`. An
    infinity is the same shape one step over: it satisfies a `<=` bound or fails it
    silently depending on sign, and neither answer is a measurement.

    `positive=False` bounds finiteness only, for quantities that may legitimately be zero
    or negative (a transparent fraction, a mean absolute difference). The default also
    refuses zero and negatives, which is what a tolerance, a fraction of a diagonal, or a
    length scale has to be.

    The natural long-term home for this is `armature_core/errors.py`, beside `GateFailure`;
    that file is another domain's in the wave-10 frozen map, so the helper lives here (with
    `_tightened`, the repo's settled "the module owns the bound" shape) and is imported by
    the other three rather than copied.
    """
    v = float(value)
    if not math.isfinite(v) or (positive and v <= 0.0):
        ev[name] = v
        raise gate_cls(
            f"{name}={v!r} is not a finite "
            f"{'positive ' if positive else ''}number, so it cannot be compared against. "
            f"A NaN fails EVERY comparison in both directions — `nan > x` and `nan < x` "
            f"are both False — so it does not fire a bound, it walks past every bound and "
            f"lands on the verdict line. A gate that returns a PASS beside a measurement "
            f"that is not a number certifies nothing", ev)
    return v


def _tightened(name, requested, owned, gate_cls, ev):
    """`requested` if it only tightens `owned`, else raise. None means "use the module's".

    Wave 10, F-e982d505: the comparison below is `value > float(owned)`, and `float('nan')
    > 1e-4` is False — so a NaN, an infinity of the wrong sign, a zero and a negative all
    read as tightenings and were accepted. `require_finite` runs first, and it refuses
    them by name.
    """
    if requested is None:
        return float(owned)
    value = require_finite(name, requested, gate_cls, ev)
    if value > float(owned):
        raise gate_cls(
            f"a caller asked this gate to run with {name}={value:.3e}, above the module's "
            f"own {float(owned):.3e}. It may only TIGHTEN: a tolerance the caller supplies "
            f"is a tolerance the caller can loosen, and a gate whose tolerance grows with "
            f"the deviation it is measuring cannot see the deviation", ev)
    return value


def gate_rigid_arrival(observations, bbox_diagonal, epsilon_frac=None, rigidity_frac=None):
    """Gate RIGID · ANDON — per part: posed == bone transform applied to rest, and rigid.

    `observations` is one record per part with `name`, `max_transform_error` (max distance
    between the posed vertices and the bone transform applied to the rest vertices),
    `max_pair_distance_change` (largest change in any sampled intra-part vertex distance),
    and `max_displacement`. `authored_max` is the largest bone-level displacement the action
    calls for, computed from the armature rather than from the mesh.

    The evidence carries `gate` and `andon` (F-f2f42e4a) — see `gate_parts_accounting`.

    **The tolerance fractions are this module's, not the caller's.** `epsilon_frac` and
    `rigidity_frac` were keywords any caller could raise; they now default to None, meaning
    `RIGID_TRANSFORM_FRAC` and `RIGID_RIGIDITY_FRAC`, and a value ABOVE either raises. See
    `_tightened`.

    **And `bbox_diagonal` is checked, because it multiplies both of them** (F-e982d505).
    Wave 8 closed the loosening direction on the two fractions and left it fully open one
    argument over: measured 2026-09-04 on an observation set that raises at
    `bbox_diagonal=1.0`, the same call PASSED at `bbox_diagonal=1e6` with
    `transform_tolerance` 100.0 and PASSED at `bbox_diagonal=float('nan')` with
    `transform_tolerance` nan. Non-finite and non-positive are refused here by name. A
    merely LARGE diagonal is not, and cannot be: `rig_parts.py:338` measures it off the
    mesh bbox and this module does not know the caller's units, so "big" is not a
    property this gate can rule on — what it can rule on is that the multiplicand is a
    number at all.
    """
    ev = {"gate": "RIGID", "andon": "GateRigidArrival",
          "bbox_diagonal": float(bbox_diagonal),
          "module_transform_frac": RIGID_TRANSFORM_FRAC,
          "module_rigidity_frac": RIGID_RIGIDITY_FRAC,
          "transform_frac_requested": epsilon_frac,
          "rigidity_frac_requested": rigidity_frac,
          "parts": observations}
    require_finite("bbox_diagonal", bbox_diagonal, GateRigidArrival, ev)
    eps = _tightened("epsilon_frac", epsilon_frac, RIGID_TRANSFORM_FRAC,
                     GateRigidArrival, ev)
    rig = _tightened("rigidity_frac", rigidity_frac, RIGID_RIGIDITY_FRAC,
                     GateRigidArrival, ev)
    tol = eps * float(bbox_diagonal)
    rig_tol = rig * float(bbox_diagonal)
    ev["transform_frac"], ev["rigidity_frac"] = eps, rig
    ev["transform_tolerance"], ev["rigidity_tolerance"] = tol, rig_tol
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


def gate_parts_determinism(a, b, bbox_diagonal, length_frac=None):
    """Gate D · ANDON — a second build produced the same parts.

    `a` and `b` map part name to {"n_verts", "n_faces", "positions"} where positions is a
    lexicographically sorted (N, 3) array. Sorted because a rebuild may emit the same
    geometry in a different order and that is not a difference in the rig; compared as arrays
    because a file hash would fire on exporter noise and, worse, a hash MATCH would be quoted
    as proof of a property it never tested.

    **This gate had no vacuity guard** (F-1dd37d93). Measured 2026-09-04:
    `gate_parts_determinism({}, {}, 1.0)` returned with the verdict "0 parts identical
    across two builds" and `worst {"part": None, "delta": 0.0}` — `set(a) != set(b)` is
    False over two empty dicts, the intersection loop never runs, and `problems` stays
    empty. Two functions above, `gate_rigid_arrival` refuses the identical shape and says
    why; this one was saved only by Gate PARTS firing earlier in `rig_parts.build_pass`,
    a different function on a different pass, and `turnaround.gate_view_crop`'s docstring
    already rules that out: a gate whose andon is load-bearing only in another gate's
    presence is not an andon. An empty side, and a non-empty pair sharing no part name,
    both raise; `n_parts_compared` states what the geometry clause actually covered.

    The evidence carries `gate` and `andon` (F-f2f42e4a). Gate id "D" is carried by two
    andons — `errors.GateDDeterminism` (E07's rig determinism) and this one — so a
    receipt line reading "[D] two builds produced different parts" is ambiguous by id and
    the evidence is what disambiguates it.

    **The tolerance fraction is this module's, not the caller's.** `length_frac` was a
    keyword defaulting to 1e-6 that any caller could raise; it now defaults to None,
    meaning `DETERMINISM_LENGTH_FRAC`, and a value ABOVE that raises. See `_tightened`.
    Wave 10 (F-e982d505): a NaN read as a tightening and `bbox_diagonal` was unchecked —
    measured, `gate_parts_determinism(a, b, 1.0, length_frac=float('nan'))` returned the
    verdict "1 parts identical across two builds" while its own evidence recorded
    `worst {"part": "p", "delta": 99.0}`. Both are refused by `require_finite` now.

    **A part carrying no vertices is refused rather than compared** (F-03955683).
    `np.abs(...).max()` over an empty array raises numpy's untyped `ValueError: zero-size
    array to reduction operation maximum which has no identity`, which carries no gate id,
    no evidence and no andon name, so the halt contract records Gate D firing as "FAILED —
    an unhandled error". Returning 0.0 for such a part would be the other wrong answer: a
    delta of zero over geometry that does not exist reads as agreement.
    """
    shared = sorted(set(a) & set(b))
    ev = {"gate": "D", "andon": "GatePartsDeterminism",
          "module_length_frac": DETERMINISM_LENGTH_FRAC,
          "length_frac_requested": length_frac,
          "bbox_diagonal": float(bbox_diagonal),
          "n_parts_a": len(a), "n_parts_b": len(b), "n_parts_compared": len(shared)}
    require_finite("bbox_diagonal", bbox_diagonal, GatePartsDeterminism, ev)
    frac = _tightened("length_frac", length_frac, DETERMINISM_LENGTH_FRAC,
                      GatePartsDeterminism, ev)
    tol = frac * float(bbox_diagonal)
    ev["length_frac"], ev["tolerance"] = frac, tol
    problems = []

    if not a or not b:
        raise GatePartsDeterminism(
            f"two builds were compared with {len(a)} and {len(b)} part(s): the set clause "
            f"reads False over an empty pair, the intersection loop never runs, and the "
            f"gate would be a check that cannot fail. A determinism andon that returns "
            f"'0 parts identical across two builds' certifies nothing", ev)
    if not shared:
        raise GatePartsDeterminism(
            f"the two builds share no part name at all ({len(a)} and {len(b)} part(s)), "
            f"so the geometry comparison this gate exists for ran over nothing: only in "
            f"first {sorted(set(a) - set(b))[:8]}, only in second "
            f"{sorted(set(b) - set(a))[:8]}", ev)

    empty = sorted(n for n in shared
                   if len(np.asarray(a[n]["positions"])) == 0
                   or len(np.asarray(b[n]["positions"])) == 0)
    if empty:
        ev["empty_parts"] = empty
        raise GatePartsDeterminism(
            f"{len(empty)} part(s) carry no vertices on one or both sides "
            f"({empty[:8]}), so there is no geometry to compare and the comparison this "
            f"gate exists for would run over an empty array. `.max()` over one is numpy's "
            f"untyped error, and a delta of 0.0 over one would read as agreement — a "
            f"determinism andon certifying a part that does not exist. Gate PARTS accounts "
            f"every face earlier in `rig_parts.build_pass`, so a part with no geometry "
            f"reaching here is itself the finding", ev)

    if set(a) != set(b):
        problems.append(f"part sets differ: only in first {sorted(set(a) - set(b))[:8]}, "
                        f"only in second {sorted(set(b) - set(a))[:8]}")
    worst = {"part": None, "delta": 0.0}
    for name in shared:
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
