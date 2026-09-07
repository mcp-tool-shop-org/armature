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

import json
import math
import os
import sys

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
        raise ArmatureError(f"expected a non-empty (N, 3) centroid array, got {c.shape}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "centroids_not_n_by_3"})
    if not bones:
        raise ArmatureError("no parts to assign faces to",
            {"gate": None, "andon": "ArmatureError",
             "clause": "no_parts_to_assign_to"})
    if normalise:
        missing = [b["name"] for b in bones if not (radii.get(b["name"], 0) > 0)]
        if missing:
            raise ArmatureError(
                f"no positive measured radius for {missing}; normalised assignment divides "
                f"by each part's own radius and will not fall back to a length in metres",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "part_radius_not_positive"})

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

    The evidence carries `gate` and `andon` (F-f2f42e4a): the halt contract's
    `STAGE_RENDER_HALT` line (`stage_render.py::__main__`, and the same six-key shape in all
    21 sibling tools) carries the gate id beside the evidence JSON, and gate ids are
    shared across andon families, so the JSON has to name which andon pulled. The
    citation used to name `GATE_FAILURE` / `GATE_EVIDENCE`, two print lines wave 12
    deleted; corrected in passing rather than dropped, because the correction is the
    useful part.
    """
    labels = np.asarray(labels)
    ev = {"gate": "PARTS", "andon": "GatePartsAccounting",
          "n_faces": int(n_faces), "n_labels": int(len(labels)),
          "n_parts_registered": len(bone_names)}
    problems = []

    if not len(bone_names) or not int(n_faces):
        ev["clause"] = "nothing_to_partition"
        raise GatePartsAccounting(
            f"the partition was gated over {int(n_faces)} face(s) across "
            f"{len(bone_names)} registered part(s): every clause below compares 0 to 0 "
            f"and the gate would be a check that cannot fail. A comparison over nothing "
            f"must not report agreement", ev)

    if len(labels) != n_faces:
        problems.append({"clause": "assignment_count_is_not_the_face_count",
                         "detail": f"{len(labels)} assignments for {n_faces} faces"})
    if len(labels):
        if labels.min() < 0:
            problems.append({"clause": "face_assigned_to_nothing",
                             "detail": f"{int((labels < 0).sum())} face(s) assigned to "
                                       f"nothing"})
        if labels.max() >= len(bone_names):
            problems.append({"clause": "face_assigned_outside_the_registered_list",
                             "detail": f"a face is assigned to part index "
                                       f"{int(labels.max())}, outside the registered list "
                                       f"of {len(bone_names)}"})

    counts = {name: int((labels == i).sum()) for i, name in enumerate(bone_names)}
    empty = sorted(n for n, v in counts.items() if v == 0)
    ev.update({"faces_per_part": counts, "parts_with_no_faces": empty,
               "total_assigned": int(sum(counts.values()))})
    if ev["total_assigned"] != n_faces:
        problems.append({"clause": "assigned_total_is_not_the_face_count",
                         "detail": f"{ev['total_assigned']} faces assigned but the mesh "
                                   f"has {n_faces}"})
    if empty:
        problems.append({"clause": "registered_part_with_no_faces",
                         "detail": f"{len(empty)} registered part(s) would be an empty "
                                   f"object: {empty}"})

    if problems:
        # `assembly.gate_batch_topology`'s shape (`assembly._problem`, wave 18): the
        # message stays the same sentence over the same details in the same order, and the
        # RECEIPT gains `problems` as `{clause, detail}` records, `clauses` as the list and
        # `clause` as the first. Spelled as dict LITERALS at each append so the words are
        # visible to `_census_nodes.clause_literals`, which `assembly`'s own `_problem`
        # helper is not — measured on `3380ae2`, none of its words is in the vocabulary.
        ev["problems"] = problems
        ev["clauses"] = [p["clause"] for p in problems]
        ev["clause"] = problems[0]["clause"]
        raise GatePartsAccounting(
            "the mesh was not partitioned cleanly into the registered parts: "
            + "; ".join(p["detail"] for p in problems), ev)
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
                                f"so the cut plane has no normal",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "child_bone_has_no_length"})
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
                                f"ball or a cross-section; the collar cannot be sized",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "no_positive_joint_radius"})
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
#: cannot see the defect. Neither production call site passes one — `rig_parts.py::main`
#: calls `parts.gate_parts_determinism` and `parts.gate_rigid_arrival` and both take the
#: defaults — so the freedom bought nothing and the loosening direction was unbounded.
#: (Re-anchored on the symbol 2026-09-04, F-0f035830: the two line numbers had drifted onto
#: a `view_layer.update()` and onto a blank line.)
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

    **The coercion is INSIDE the guard, not above it (wave 22, F-fda74b87).** `v =
    float(value)` used to run first, so the ONE implementation of rule 4 was broken in one
    class of the case it exists for: a value that is not a real number left here as an
    untyped `TypeError`, which the 21-tool halt contract records as exit 1 "FAILED — an
    unhandled error" where a typed refusal at exit 2 belongs. MEASURED on `e8263a3`:
    `require_finite('x', None, AlphaGate, {})` raised `TypeError: float() argument must be
    a string or a real number, not 'NoneType'` — not in the `ArmatureError` family — and so
    did a list and a dict, while `'nan'` (a string) `float()` accepts and this clause
    refuses correctly. Two spellings of an unreadable measurement, two different exits.
    Through the importers, `turnaround.gate_view_alpha(0, 0, 255, None)`,
    `startframe.gate_backdrop(None, ...)` and `startframe.gate_whole(extent, 64, None, 4)`
    each raised the bare `TypeError`; their input is a MEASUREMENT read back from a record,
    and `null` is the ordinary JSON shape of a measurement nobody took.

    An unreadable operand is read as NaN — which the clause below already refuses by name —
    and the RAW value rides the evidence beside the coerced one under `<name>_raw`, because
    "not a number at all" and "a number that is not finite" are different facts about a
    record and the halt line has to be able to say which one arrived. This is the shape
    `channels.normalize_depth` already uses for `z_near`/`z_far` and `framing._finite_positive`
    uses as a predicate; the file records the same defect being caught by its own test at
    `joint_planes` below.
    """
    try:
        v = float(value)
        unreadable = False
    except (TypeError, ValueError):
        v = float("nan")
        unreadable = True
    if not math.isfinite(v) or (positive and v <= 0.0):
        ev[name] = v
        if unreadable:
            ev[f"{name}_raw"] = repr(value)
        shown = (f"{name}={value!r} is not a number at all (read as {v!r}) and so is not a "
                 f"finite {'positive ' if positive else ''}number"
                 if unreadable else
                 f"{name}={v!r} is not a finite "
                 f"{'positive ' if positive else ''}number")
        # WHERE THE CALLER HAS NONE, NEVER OVER ONE THE CALLER WROTE — `tightened`'s rule,
        # eleven lines of its docstring, adopted rather than re-derived (F-f7449bc9, wave
        # 28). Every caller in this package that reaches this raise through a GATE's shared
        # `ev` had no clause at all: `gate_alpha`, `gate_backdrop`, `gate_view_alpha`,
        # `gate_round_trip`, `gate_rigid_arrival` and `gate_parts_determinism` each wrote
        # a receipt a census could only tell apart by regexing 200 characters of English.
        # A caller that DOES name one is naming the same condition with its own operand in
        # it, which is the finer id. Spelled as an assignment of a literal, not
        # `setdefault`, because that is the only shape `_census_nodes.clause_literals`
        # reads — the lesson `tightened` paid for in wave 25.
        if "clause" not in ev:
            ev["clause"] = "value_not_finite"
        raise gate_cls(
            f"{shown}, so it cannot be compared against. "
            f"A NaN fails EVERY comparison in both directions — `nan > x` and `nan < x` "
            f"are both False — so it does not fire a bound, it walks past every bound and "
            f"lands on the verdict line. A gate that returns a PASS beside a measurement "
            f"that is not a number certifies nothing", ev)
    return v


def tightened(name, requested, owned, gate_cls, ev):
    """`requested` if it only tightens `owned`, else raise. None means "use the module's".

    Wave 10, F-e982d505: the comparison below is `value > float(owned)`, and `float('nan')
    > 1e-4` is False — so a NaN, an infinity of the wrong sign, a zero and a negative all
    read as tightenings and were accepted. `require_finite` runs first, and it refuses
    them by name.

    **Public in wave 10 because two more gates needed exactly this** (F-1c6683f0 on
    `resample.require_rotation`, F-8cd65665 on `lift_solve.gate_round_trip`) — one
    implementation, imported, rather than a third and a fourth copy of the same paragraph.
    `_tightened` remains as this module's own spelling.

    **Zero is the tightest legal request, and it was refused** (F-2a564189, wave 12). This
    function called `require_finite` with the `positive=True` default, so `requested=0.0`
    — exact match, the one value that is unambiguously NOT a loosening — raised, and it
    raised quoting `require_finite`'s NaN paragraph, none of which is true of a number that
    compares correctly in both directions. Measured 2026-09-04 against `owned = 1e-4`:
    1e-30 accepted, 1e-4 accepted, 1e-3 refused as a loosening (correct), 0.0 refused as
    "not a finite positive number". The refusal reached every public gate importing the
    helper (`resample.require_rotation(I, 'w', tol=0.0)` -> ResampleGate with the same
    text), and the natural caller is a determinism tightening:
    `gate_parts_determinism(..., epsilon_frac=0.0)` meaning "two builds must be
    byte-identical", the strictest reading of Gate D. A session asking a gate for exact
    equality was told its number was not comparable, and the way past that message is to
    loosen — the guard producing the loosening it exists to prevent.

    So the two obligations are split: finiteness is asked with `positive=False`, and a
    NEGATIVE bound gets its own clause and its own sentence. The NaN paragraph is now
    quoted only at values it describes.

    **The three refusals name their condition** (wave 25, the `binding` / `startframe`
    bounds' half). MEASURED on `580af47` by reading every caller in `armature_core` and
    `tools/`: not one of the eight ev dicts handed to this function or to `narrowed`
    carries a `clause` key (`parts.gate_rigid_arrival` / `gate_parts_determinism`,
    `assembly.gate_no_paid_nodes`, `resample.require_rotation`,
    `armature_core.lift_solve.gate_round_trip`, `tools/lift_solve` twice,
    `tools/author_walk` three times), so every "may only TIGHTEN" refusal reached a halt
    line with `"clause"` absent and a halt reader keying on that string had nothing to key
    on. Three words, one per condition, assigned as literals so
    `tests/_census_nodes.clause_literals` can see them.

    **Written where the caller has none, never over one the caller wrote.** A caller that
    DOES name a clause is naming the same condition with its own flag in it, which is a
    FINER id than the generic one — `render_performer.gate_coverage` passes
    `clause: min_frac_may_only_tighten` (posted by the instruments domain, wave 25 SEAM 4).
    Overwriting that with `bound_may_only_tighten` would replace a word that says which
    flag with a word that says only which helper, which is the opposite of the improvement
    this change is. So the home supplies a word where the caller has none and defers where
    the caller has one.

    **Spelled `if "clause" not in ev: ev["clause"] = "..."` rather than `ev.setdefault`,
    and the spelling is load-bearing.** `tests/_census_nodes.clause_literals` — the ONE walk
    over the clause vocabulary — reads a `Constant` inside an evidence dict and a `Constant`
    ASSIGNED into one. A `setdefault` call is neither, so the four words below would have
    been invisible to the census that exists to notice a clause word being added, misspelled
    or doubled: measured in this worktree, the vocabulary pin went red reporting all four as
    "vanished". This is the same defect the f-string clause in `blender_scene.half_fovs` had,
    caught in the same wave; a clause word must be written in a shape the census can read.

    And the finiteness word goes into a COPY of the caller's dict, never the caller's own:
    `require_finite` RETURNS on the happy path and this function does not, so writing into
    `ev` up front would leave a stale `bound_not_finite` under the clause key of an evidence
    dict that `resample.require_rotation` and `author_walk`'s three gates go on to raise
    their OWN refusal with. (Written that way round rather than quoting the key-and-value
    pair. The wave-22 census that holds one clause word to one refusal per module regexes
    this module's SOURCE for that literal shape, so prose quoting it reads as a second raise
    site — measured here, twice, before this sentence was reworded.)
    """
    if requested is None:
        return float(owned)
    # A COPY for the finiteness call, never `ev` itself: `require_finite` returns on the
    # happy path and this function does not, so writing the clause into the caller's dict
    # up front would leave a stale `bound_not_finite` under the clause key of an evidence
    # dict that `resample.require_rotation` and `author_walk`'s three gates go on to raise
    # their OWN refusal with — a halt line naming a condition that did not pull. The copy
    # carries everything the caller had plus the word, and only a refusal ever sees it.
    _guard = dict(ev)
    if "clause" not in _guard:
        _guard["clause"] = "bound_not_finite"
    value = require_finite(name, requested, gate_cls, _guard, positive=False)
    if value < 0.0:
        ev[name] = value
        if "clause" not in ev:
            ev["clause"] = "bound_is_negative"
        raise gate_cls(
            f"a caller asked this gate to run with {name}={value:.3e}: a negative "
            f"tolerance admits nothing, so the gate would fire on correct work and the "
            f"refusal would describe a defect that is not there. Zero is the tightest "
            f"legal request (exact equality); below zero is not a tightening, it is a "
            f"bound no measurement can satisfy", ev)
    if value > float(owned):
        ev[name] = value
        if "clause" not in ev:
            ev["clause"] = "bound_may_only_tighten"
        raise gate_cls(
            f"a caller asked this gate to run with {name}={value:.3e}, above the module's "
            f"own {float(owned):.3e}. It may only TIGHTEN: a tolerance the caller supplies "
            f"is a tolerance the caller can loosen, and a gate whose tolerance grows with "
            f"the deviation it is measuring cannot see the deviation", ev)
    return value


#: This module's own spelling of the shared helper above.
_tightened = tightened


def narrowed(name, requested, owned, gate_cls, ev):
    """`requested` if it is a SUBSET of `owned`, else raise. None means "use the module's".

    `tightened`'s set-valued sibling, and the same law: a bound the caller supplies is a
    bound the caller can widen. Written here, beside the numeric one, rather than inside
    the module that needed it first — the two are the same rule over two orderings
    (`<=` on the reals, `⊆` on a finite set), and the repo has already paid for the second
    copy of a rule drifting from the first.

    Commissioned by F-5a810b95 (wave 12): `assembly.gate_no_paid_nodes(graph,
    allowed=ALLOWED_CLASSES)` was the fourth site of the family closed three times in wave
    10 (`gate_rigid_arrival`/`gate_parts_determinism`, `assembly.gate_slot_ceiling`,
    `resample.require_rotation`, `lift_solve.gate_round_trip`) and the only one of the
    family that guards SPEND. Measured 2026-09-04: the graph
    `{'1': {'class_type': 'KlingVideoNode'}}` raises on the default allowlist and RETURNS a
    full success verdict under `allowed=ALLOWED_CLASSES + ('KlingVideoNode',)`.

    The evidence records both sides and the difference, so the refusal names the classes
    that were added rather than only that a widening happened.
    """
    own = tuple(owned)
    if requested is None:
        return own
    req = tuple(requested)
    added = sorted(set(req) - set(own))
    if added:
        ev[name] = list(req)
        ev[name + "_added"] = added
        ev[name + "_module_owns"] = list(own)
        if "clause" not in ev:
            ev["clause"] = "allowlist_may_only_narrow"
        raise gate_cls(
            f"a caller asked this gate to run with {name} widened by {added}, which the "
            f"module's own {name} does not name. It may only NARROW: an allowlist the "
            f"caller supplies is an allowlist the caller can widen, and widening it at a "
            f"call site puts the addition outside every clause written to watch the "
            f"module constant. Widen the constant in a deliberate diff, or narrow here",
            ev)
    return req


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
    merely LARGE diagonal is not, and cannot be: `rig_parts.py::build_pass` measures it off
    the mesh bbox (`rig_character.subject_scale`) and this module does not know the caller's
    units, so "big" is not a
    property this gate can rule on — what it can rule on is that the multiplicand is a
    number at all.

    **And the MEASUREMENTS are checked, because they are what the clauses compare**
    (F-5733588e, wave 14). Every finiteness guard this gate carried sat on a BOUND —
    `bbox_diagonal` and the two fractions — and none on the three per-part numbers the
    clauses read, which is the direction the invariant does not bound. Measured
    2026-09-04 with clean bounds (`bbox_diagonal=1.0`, both fractions defaulted) and one
    part whose three measurements are NaN beside one healthy part: this function RETURNED
    with `transform_tolerance: 0.0001` and the verdict "2 parts each landed on their own
    bone transform; figure max displacement nan". Both refusal clauses are `>`
    comparisons, which a NaN fails in both directions, and the vacuity guard
    `moved <= tol` is switched off by the same value because `max([nan, 0.5])` is nan and
    `nan <= 1e-4` is False — so the guard that exists to catch "nothing moved" is
    disabled by the same defect. `require_finite`'s own refusal message, three hundred
    lines above, reads "A gate that returns a PASS beside a measurement that is not a
    number certifies nothing"; this gate was the counterexample. The general rule the
    wave-8 and wave-12 sweeps kept re-deriving one argument at a time is that the NaN
    sweep belongs on the measurement side too — the bound is the direction the invariant
    already covers. `lift_solve.gate_round_trip` carried the identical shape and is
    swept in the same commit.

    `positive=False` on all three: a displacement or an error of exactly 0.0 is the
    healthiest reading any of them can take.
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
        ev["clause"] = "no_parts_observed"
        raise GateRigidArrival("no parts were observed under the pose; the gate would be a "
                               "check that cannot fail", ev)
    # The measurement side of the sweep, BEFORE any bound is asked of any of them, and
    # named per part so the refusal says which structure the bad number came from.
    for rec in observations:
        for _field in ("max_transform_error", "max_pair_distance_change",
                       "max_displacement"):
            require_finite(f"{rec.get('name')}.{_field}", rec[_field],
                           GateRigidArrival, ev, positive=False)

    for rec in observations:
        if rec["max_transform_error"] > tol:
            problems.append({
                "clause": "part_did_not_land_on_its_bone_transform",
                "detail": f"{rec['name']}: posed geometry is "
                          f"{rec['max_transform_error']:.3e} from where its bone's own "
                          f"transform puts it (> {tol:.3e})"})
        if rec["max_pair_distance_change"] > rig_tol:
            problems.append({
                "clause": "part_deformed_under_the_pose",
                "detail": f"{rec['name']}: internal distances changed by up to "
                          f"{rec['max_pair_distance_change']:.3e} (> {rig_tol:.3e}) — this "
                          f"part is deforming, and this route promises no deformation "
                          f"anywhere"})

    moved = max(r["max_displacement"] for r in observations)
    ev["figure_max_displacement"] = float(moved)
    if moved <= tol:
        problems.append({
            "clause": "the_figure_did_not_move_at_all",
            "detail": f"the whole figure moved at most {moved:.3e} under the authored arc; "
                      f"nothing arrived at all"})

    if problems:
        # `gate_batch_topology`'s shape; see `gate_parts_accounting` above for why the
        # words are spelled as dict literals rather than passed to a helper.
        ev["problems"] = problems[:12]
        ev["clauses"] = [p["clause"] for p in problems]
        ev["clause"] = problems[0]["clause"]
        raise GateRigidArrival("the authored arc did not arrive whole: "
                               + "; ".join(p["detail"] for p in problems[:6]), ev)
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
        ev["clause"] = "one_build_carries_no_parts"
        raise GatePartsDeterminism(
            f"two builds were compared with {len(a)} and {len(b)} part(s): the set clause "
            f"reads False over an empty pair, the intersection loop never runs, and the "
            f"gate would be a check that cannot fail. A determinism andon that returns "
            f"'0 parts identical across two builds' certifies nothing", ev)
    if not shared:
        ev["clause"] = "the_two_builds_share_no_part_name"
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
        ev["clause"] = "part_with_no_geometry_to_compare"
        raise GatePartsDeterminism(
            f"{len(empty)} part(s) carry no vertices on one or both sides "
            f"({empty[:8]}), so there is no geometry to compare and the comparison this "
            f"gate exists for would run over an empty array. `.max()` over one is numpy's "
            f"untyped error, and a delta of 0.0 over one would read as agreement — a "
            f"determinism andon certifying a part that does not exist. Gate PARTS accounts "
            f"every face earlier in `rig_parts.build_pass`, so a part with no geometry "
            f"reaching here is itself the finding", ev)

    if set(a) != set(b):
        problems.append({
            "clause": "part_sets_differ",
            "detail": f"part sets differ: only in first {sorted(set(a) - set(b))[:8]}, "
                      f"only in second {sorted(set(b) - set(a))[:8]}"})
    worst = {"part": None, "delta": 0.0}
    for name in shared:
        pa, pb = a[name], b[name]
        if pa["n_verts"] != pb["n_verts"] or pa["n_faces"] != pb["n_faces"]:
            problems.append({
                "clause": "part_topology_differs_between_builds",
                "detail": f"{name}: {pa['n_verts']}v/{pa['n_faces']}f vs "
                          f"{pb['n_verts']}v/{pb['n_faces']}f"})
            continue
        d = float(np.abs(np.asarray(pa["positions"]) - np.asarray(pb["positions"])).max())
        # WAVE 22, F-cfb560aa — the sweep before either strict `>` is asked. `worst` is
        # seeded `{"part": None, "delta": 0.0}` and BOTH readings of `d` are strict `>`,
        # which a NaN fails in BOTH directions, so no problem was appended and `worst` was
        # never updated: MEASURED on `e8263a3` on two single-part builds differing only in
        # that the second carried `nan` in one coordinate, Gate D RETURNED
        # `verdict: '1 parts identical across two builds'` with `worst: {'part': None,
        # 'delta': 0.0}` — its strongest verdict over a part set that is not the one the
        # previous build produced. `+inf` refused, but by ACCIDENT (`inf > tol`), so only
        # the sign-free direction was unbounded and only by luck was the other one not.
        # `lift_solve.gate_round_trip` sweeps its residuals this way and the helper is
        # defined 310 lines above, in this file. Reachability is F-13a144c2's, verbatim: a
        # GLB carrying a non-finite vertex position, representable in glTF float32 and
        # passed through by the importer.
        require_finite(f"delta.{name}", d, GatePartsDeterminism, ev, positive=False)
        if d > worst["delta"]:
            worst = {"part": name, "delta": d}
        if d > tol:
            problems.append({
                "clause": "part_vertices_differ_between_builds",
                "detail": f"{name}: vertices differ by up to {d:.3e} (> {tol:.3e})"})
    ev["worst"] = worst
    if problems:
        # `gate_batch_topology`'s shape; see `gate_parts_accounting` above.
        ev["problems"] = problems[:12]
        ev["clauses"] = [p["clause"] for p in problems]
        ev["clause"] = problems[0]["clause"]
        raise GatePartsDeterminism("two builds produced different parts: "
                                   + "; ".join(p["detail"] for p in problems[:6]), ev)
    ev["verdict"] = f"{len(a)} parts identical across two builds"
    return ev


# ===================================================================================
# WAVE 22 · SEAM 1 — THE TOOL-ENTRY HELPERS, ONE HOME
# ===================================================================================
#
# The two things every CPython instrument in this repo had to spell for itself, spelled
# ONCE here and imported. Both are LIFTS of code that already existed in 22 and 2 copies
# respectively; neither is a new rule.
#
# **Why `parts.py` and not `errors.py`.** Every one of the 22 `_halt_keysafe` docstrings
# nominates `armature_core.errors` as the home, and both `single_path_segment` copies
# nominate `armature_core`. `errors.py` is core-gates' file in the frozen domain map, and a
# NEW module under `armature_core/` matches no domain's globs at all — the swarm's
# `checkOwnership` resolves such a file to `unassigned`, which is an ownership violation,
# which fails the whole wave's collect. So the one home is an existing core-solvers file,
# and this is the one the repo already points at: `require_finite` — the refusal's RAISE
# end — lives here and is imported by 12 `armature_core` modules and by `measure_arm.py`,
# and `rig_gates.py` and both `single_path_segment` copies name it as the pattern to
# follow. `run_tool_main` is the same refusal's EXIT end. The two ends belong together.


def halt_keysafe(value, _seen=None):
    """`value` with every mapping key stringified and every non-finite float named.

    The 22-copy `_halt_keysafe`, plus the clause instruments measured in wave 22 (SEAM 3,
    F-897a3329). Two failure modes, both of which end with `blender -b -P` reporting exit
    **0** on a fired andon:

    1. `json.dumps(..., default=str)` applies `default` to VALUES ONLY, so a tuple key or a
       `numpy.int64` key raises `TypeError` from inside the halt handler, the new exception
       leaves the whole `try`, and `sys.exit` never runs. MEASURED 2026-09-04 against all 21
       handlers: 21 of 21 escaped that way.
    2. A SELF-REFERENCING evidence dict recursed until `RecursionError` escaped the handler
       — 21 of 21 again. Containers already on the path are written as the literal
       `"<circular>"` rather than re-entered.

    And the strictness clause: a non-finite float is written as its `repr` (`"nan"`,
    `"inf"`, `"-inf"`), because `json.dumps` at its `allow_nan` default emits the bare token
    `NaN`, which Python's own `json.loads` accepts and JS `JSON.parse`, Go `encoding/json`
    and serde all reject. `require_finite` writes exactly such a float into the caller's
    evidence (`ev[name] = v`), so the halt line an operator pipes into any non-Python reader
    was not JSON. Named here rather than dropped: `"nan"` is the operand, and the operand is
    why the tool halted.
    """
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list, tuple)):
        if id(value) in _seen:
            return "<circular>"
        _seen = _seen | {id(value)}
    if isinstance(value, dict):
        return {str(k): halt_keysafe(v, _seen) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [halt_keysafe(v, _seen) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value


#: cp1252-hostile glyphs -> ASCII stand-ins. Em dash (U+2014) and degree (U+00B0) ARE in
#: cp1252; substituting them would rewrite every outcome sentence. These four are not, and
#: leaving them for `printable_halt_line`'s backslashreplace produces the mixed LOOK
#: (glyphs beside `\u2264`) F-0d3138c9 names. Apply in `halt_ascii_standins` BEFORE the
#: dump so the common path never mixes; keep `printable_halt_line` as last-resort guard.
_HALT_ASCII_STANDINS = str.maketrans({
    "\u2264": "<=",   # ≤
    "\u2265": ">=",   # ≥
    "\u2260": "!=",   # ≠
    "\u2026": "...",  # …
})


def halt_ascii_standins(text):
    """`text` with cp1252-hostile glyphs replaced by ASCII stand-ins (`<=`, `>=`, …)."""
    if not isinstance(text, str):
        text = str(text)
    return text.translate(_HALT_ASCII_STANDINS)


def _evidence_clause_first(evidence):
    """Evidence mapping with `clause` first when present — halt-line wrap LOOK."""
    if not isinstance(evidence, dict) or "clause" not in evidence:
        return evidence
    return {"clause": evidence["clause"],
            **{k: v for k, v in evidence.items() if k != "clause"}}


def printable_halt_line(line, stream=None):
    """`line` rendered so that printing it to `stream` cannot raise on its encoding.

    F-0a27b25c, wave 28. `run_tool_main` prints the halt line from a `finally`, so an
    exception raised by that `print` propagates out of the whole `try` statement and the
    `sys.exit` below it never runs — `blender -b -P` then reports exit 0 on a fired andon.
    That is why `run_tool_main` cannot simply pass `ensure_ascii=False` and print the
    result: the halt record's `message` is the refusal's own prose, and 45 of this package's
    raise sites carry a character (an em dash, a degree sign, `≤`) that a cp1252 stdout
    opened with `errors="strict"` — **this rig's default; measured, `sys.stdout.encoding ==
    'cp1252'`** — cannot encode.

    So the escaping decision is made HERE, against the stream that will actually carry the
    line, rather than globally by `json.dumps`:

    * a stream whose encoding carries the line (a UTF-8 stdout, a pipe under
      `PYTHONIOENCODING=utf-8`, CI on Linux) gets the line UNCHANGED — the em dash is an em
      dash;
    * a stream whose encoding does not gets `backslashreplace` for exactly the characters it
      cannot carry, so the line still prints, still parses as JSON, and still says which
      character it could not render;
    * a stream with no `encoding` attribute at all (`io.StringIO`, pytest's capture) carries
      any `str` and gets the line unchanged.

    The stream is NOT reconfigured. `sys.stdout.reconfigure(encoding="utf-8")` would change
    the encoding of every other line the process prints — including the success sentinels
    the tools earn by an effect — and on a real cp1252 console it substitutes mojibake for
    the escape rather than removing it. A rendering decision belongs to the line being
    rendered.

    Total on failure: this returns a `str` for every input it is given and raises nothing;
    `run_tool_main` still wraps the `print`, because a stream can fail for reasons that have
    nothing to do with encoding.
    """
    text = line if isinstance(line, str) else str(line)
    stream = sys.stdout if stream is None else stream
    enc = getattr(stream, "encoding", None)
    if not isinstance(enc, str) or not enc:
        return text
    errors = getattr(stream, "errors", None)
    try:
        text.encode(enc, errors if isinstance(errors, str) and errors else "strict")
        return text
    except (UnicodeError, LookupError, TypeError, ValueError):
        pass
    try:
        return text.encode(enc, "backslashreplace").decode(enc, "replace")
    except (UnicodeError, LookupError, TypeError, ValueError):
        return text.encode("ascii", "backslashreplace").decode("ascii")


def halt_outcome(exc):
    """`(exit_code, outcome)` for `exc` under the halt contract. THREE outcomes, not two.

    A typed `GateFailure` is an andon that fired and names itself; a bare `ArmatureError`
    is a deliberate refusal with no gate behind it (an unknown flag, an unknown `--mode=`);
    anything else is a crash. Recording a crash as "a gate fired" is a false record —
    F-c3f86abc measured `rig_character` writing one. A deliberate refusal exits 2; a crash
    exits 1.
    """
    if isinstance(exc, GateFailure):
        return 2, "HALTED — a gate fired"
    if isinstance(exc, ArmatureError):
        return 2, "REFUSED — the tool declined to proceed"
    return 1, "FAILED — an unhandled error"


def run_tool_main(main, prefix, tool=None):
    """Run `main()` under the halt contract and exit. NEVER RETURNS.

        if __name__ == "__main__":
            from armature_core.parts import run_tool_main
            run_tool_main(main, "RENDER_TURNAROUND")

    `blender -b -P` exits **0** when the script's exception propagates (E07, measured three
    times: `rig_character.py`, `rig_parts.py`, `author_walk.py`), so a halt that does not
    exit deliberately is reported as a success. This prints `f"{prefix}_HALT " + <record>`
    and exits 2 for a refusal, 1 for a crash. It does NOT print the tool's success
    sentinel — that stays with the tool, earned by an effect (wave 12).

    `tool` defaults to `prefix.lower()`, which reproduces all 22 spellings on `e8263a3`.

    ── THE CONTRACT, STATED HERE (F-48f0c3d4, wave 28) ──────────────────────────────

    README.md §"Reading a halt" is the operator's half and it ends "the one implementation
    of the CPython contract is `armature_core.parts.run_tool_main`; its docstring is the
    specification". This paragraph is that specification, so the reader's half and the
    code's half cannot drift apart. What the tree looked like before it existed: `grep -rn
    "_HALT" --include=*.md .` returned ZERO hits, README included — the `<TOOL>_HALT` line,
    the six keys, the three outcome sentences and the exit-code table lived only in these
    docstrings and in the suite that drives them.

    **The line.** Exactly one line on stdout, `f"{prefix}_HALT "` followed by a JSON object.
    Nothing else is printed by this handler on the refusal path.

    **The six keys, in this order and never a seventh** (F-8e83b813 — `evidence` before
    `message` so an 80-column wrap still surfaces `evidence.clause` in the first lines):

      ``tool``      the tool's own name (`tool`, else `prefix.lower()`)
      ``outcome``   one of the three sentences `halt_outcome` returns, below
      ``gate``      `exc.gate` — the gate id a typed `GateFailure` names, else null
      ``evidence``  the raise's evidence dict through `halt_keysafe` (with `clause` first
                    when present), else null
      ``error``     `type(exc).__name__`
      ``message``   `str(exc)` — the refusal's own prose, written for a person
                    (`halt_ascii_standins` applied so cp1252-hostile glyphs become `<=` /
                    `>=` / `!=` / `...` before the dump; F-0d3138c9)

    **The three outcomes and the exit codes** (`halt_outcome`, and it is three and not two
    because a bad `--mode=` is a refusal with no gate behind it):

      exit 2   "HALTED — a gate fired"                   a typed `GateFailure`
      exit 2   "REFUSED — the tool declined to proceed"   a bare `ArmatureError`
      exit 1   "FAILED — an unhandled error"              anything else
      exit 0   never printed here; success is the tool's own sentinel, earned by an effect

    **`evidence.clause`** is the machine-readable word a caller, a census or a later session
    branches on — the message is for a person, the clause is for a machine, and both must
    hold. The vocabulary is held by `tests/test_refusal_clauses.py`.

    **THE HALT CONTRACT'S OWN GUARD (F-586822bf, wave 12).** Wave 10 moved `json.dumps`
    inside a try/except/finally so a sentinel that cannot serialise could no longer delete
    `sys.exit` — but the sentinel's CONSTRUCTION stayed ABOVE that guard, and so did
    `traceback.print_exc()`. Everything below that can fail is inside the guard; what is
    above it cannot: `isinstance` on an exception, `type(exc).__name__`, and a
    `json.dumps` of six values that are already strings or None.

    **THE TRACEBACK IS THE CRASH'S DIAGNOSTIC, NOT THE REFUSAL'S** (F-2df6fd1b, wave 28).
    `traceback.print_exc()` used to run for all three outcomes, so a deliberate refusal and
    a crash were the same thing on screen inside the one handler whose whole design is to
    tell them apart: measured in a child process, a `GateFailure`, a bare `ArmatureError`
    ("--mode=wobble is not a mode") and a `KeyError` each produced the same five-line stack
    rooted at this function, while the record on the other stream distinguished them at
    exit 2 / 2 / 1. An operator who mistyped a flag read repo internals as "the tool is
    broken". It now prints only when `_code == 1`, where the stack IS the diagnostic; a
    refusal already carries `error`, `message`, `gate` and `evidence`. It stays inside the
    guarded region, which is the property `tests/test_instruments_amend_w12.py` pins.

    **THE LINE IS UN-CRASHABLE ON ANY STDOUT ENCODING** (F-0a27b25c, wave 28). The record's
    `message` is the refusal's own prose and 117 of 946 raise-with-a-message sites tree-wide
    carry a non-ASCII character, so `ensure_ascii`'s default True printed them as
    backslash-u escapes in the middle of the one sentence a person reads. `ensure_ascii=False`
    ALONE is not the fix and would be a worse defect than the one it closes: the `print`
    below sits in the `finally`, so a `UnicodeEncodeError` from it would propagate out of
    the whole statement and DELETE `sys.exit`, handing `blender -b -P` exit 0 on a fired
    andon — the exact failure this handler exists to prevent, twice recorded in
    `halt_keysafe`'s docstring. So the record is dumped with `ensure_ascii=False` and the
    line is then rendered FOR THE STREAM by `printable_halt_line` before it is printed, and
    the print itself is wrapped so that nothing it can raise reaches `sys.exit`. Measured
    both ways, because either one alone would not be a measurement: a UTF-8 stdout carries
    the character, and a cp1252 stdout opened with `errors="strict"` (this rig's default
    console encoding) carries a `\\uXXXX` escape for that one character and still exits 2.
    """
    import traceback

    name = prefix.lower() if tool is None else tool
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:                # noqa: BLE001 — the halt must be loud
        _code, _outcome = halt_outcome(exc)
        _sentinel = {
            "tool": name, "outcome": halt_ascii_standins(_outcome), "gate": None,
            "evidence": None, "error": type(exc).__name__,
            "message": "the halt line could not be built"}
        _line = json.dumps(_sentinel)
        try:
            if _code == 1:
                # Only the crash. See "THE TRACEBACK IS THE CRASH'S DIAGNOSTIC" above.
                traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _evidence = (halt_keysafe(_detail)
                         if isinstance(_detail, dict) else None)
            _sentinel = {
                "tool": name,
                "outcome": halt_ascii_standins(_outcome),
                "gate": getattr(exc, "gate", None),
                "evidence": _evidence_clause_first(_evidence),
                "error": type(exc).__name__,
                "message": halt_ascii_standins(str(exc))}
            _line = json.dumps(_sentinel, default=str, allow_nan=False,
                               ensure_ascii=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            try:
                print(printable_halt_line(prefix + "_HALT " + _line))
            except BaseException:                                     # noqa: BLE001
                # NOTHING from the print reaches `sys.exit`. A closed, detached or
                # exotic stdout costs the halt LINE; it must never cost the exit code,
                # because an exit 0 on a fired andon is read as a success by every
                # caller and by `blender -b -P` itself.
                pass
            sys.exit(_code)


def single_path_segment(value, flag, exc, extra=None):
    """`value` if it names ONE path component, else raise `exc` naming the flag. · ANDON

    A `--name` is a NAME, not a path. `os.path.join(out_dir, f"{name}.{ext}")` with
    `name="../escaped"` writes OUTSIDE `--out` while every gate above it stays green and
    the manifest that certifies the artifact stays behind in `--out` — measured on the base
    tree (F-62dec63b): `PACK_POSE_PACK_OK` with `"gate_R": "identical"`, exit 0, the pack
    at `<base>/esc/escaped.apng.png` and the manifest at `<base>/esc/inner/`, so the
    directory the caller was told to read held a manifest and no pack. Gate R read the
    escaped file back and reported it identical, because Gate R compares pixels and is
    blind to where they live. The neighbouring spelling refused by accident rather than by
    name: `--name=a/b` died with an untyped `FileNotFoundError` whose halt record read
    `"evidence": null`, so a run that was refused looked like a run that crashed.

    `os.path.basename` alone is not the check: it is platform-dependent (on POSIX
    `basename` of a backslash-bearing string is the whole string) and it accepts `.` and
    `..` unchanged. Both separators, the drive-relative spellings, the two dot names and an
    absent name are refused explicitly, so the same call answers the same way on either
    platform.

    **WAVE 22, SEAM 1: this is the ONE home.** It was two byte-identical copies
    (`pack_pose_pack.py`, `resample_motion.py`), each carrying a docstring saying the single
    home is `armature_core`. Signature, argument ORDER, clause word
    (`output_name_is_not_a_name`) and evidence keys are unchanged, so the copies are deleted
    and imported rather than re-derived.
    """
    text = "" if value is None else str(value)
    sep = {"/", "\\"} | {c for c in (os.sep, os.altsep) if c}
    if (not text.strip() or text in (".", "..") or os.path.isabs(text)
            or any(c in text for c in sep) or os.path.basename(text) != text):
        ev = {"gate": "ARGS", "andon": exc.__name__,
              "clause": "output_name_is_not_a_name", "flag": flag, "name": text}
        ev.update(extra or {})
        raise exc(
            f"{flag}={text!r} is not a name; it is pasted into the output path as one "
            f"component of a filename, so a separator, an absolute path or a dot name "
            f"writes the artifact somewhere other than the directory this tool was told to "
            f"write into, while the manifest that certifies it stays behind and every "
            f"gate above reports on the file that escaped",
            ev)
    return text
