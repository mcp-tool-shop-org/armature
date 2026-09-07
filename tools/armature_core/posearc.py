"""Authored performances for the procedural wire subject — the kinematics, without bpy.

`make_test_armature.py` imports bpy at module scope, so nothing in it can be exercised
outside Blender. The pose arithmetic is the part worth testing hardest — it is the ground
truth every later measurement is read against — so it lives here instead, in a module that
imports cleanly anywhere. Same reason `stage_render` keeps its gates importable without a
render backend: a test that cannot drive the real function tests a copy of it.

**What an arc is.** A rigid rotation of one named group of parts about one named joint, by
an angle that moves linearly with the frame index. That is deliberately the smallest thing
that can answer E03's question. A richer rig (an elbow that bends, a spine that leans) adds
joints whose true positions we would then have to solve for, and E03 is not asking about
those — it is asking whether *any* authored motion transfers.

**Frame 0 is the bind pose**, and the arc reaches its end angle exactly on the last frame:
`angle(i) = start + (end - start) * i / (count - 1)`. Note this is NOT the convention
`orbit_azimuth` uses — an orbit divides by `count` because frame `count` would coincide with
frame 0 on a closed loop. A performance is not a loop; it has two ends and must hit both.
"""

import math

from .errors import SpecError

#: The arcs this subject can perform. Adding one is a data change, not a code change.
#: Extra arcs (F-72d73808): elbow bend, spine lean, contralateral raise — E03-style
#: transfer checks and sheet fixtures cover more than one performance without editing code.
POSE_ARCS = {
    "arm_r_raise": {
        "pivot": "shoulder_r",
        "axis": "Y",
        # A rotation of +theta about +Y maps +X to -Z, and the arm must go UP, so the
        # applied angle is negated. Verified in `test_posearc.py` against the endpoint
        # rather than asserted from the right-hand rule, because that is exactly the kind
        # of sign this repo has been wrong about before.
        "sign": -1.0,
        "moving_joints": ("elbow_r", "wrist_r"),
        "moving_parts": (
            "bone_shoulder_r__elbow_r",
            "bone_elbow_r__wrist_r",
            "joint_elbow_r",
        ),
        "readout_deg": 45.0,
        "description": (
            "the arm named _r in the generator (the +X side) rises straight from the "
            "T-pose to overhead, rotating rigidly about the shoulder; the elbow does not "
            "bend and no other joint moves"
        ),
    },
    "arm_l_raise": {
        "pivot": "shoulder_l",
        "axis": "Y",
        # Contralateral of arm_r_raise: the -X arm rises about +Y with opposite sign so
        # +theta maps it UP (right-hand rule on -X).
        "sign": 1.0,
        "moving_joints": ("elbow_l", "wrist_l"),
        "moving_parts": (
            "bone_shoulder_l__elbow_l",
            "bone_elbow_l__wrist_l",
            "joint_elbow_l",
        ),
        "readout_deg": 45.0,
        "description": (
            "the arm named _l (the -X side) rises straight from the T-pose to overhead, "
            "rotating rigidly about the shoulder; contralateral of arm_r_raise"
        ),
    },
    "elbow_r_bend": {
        "pivot": "elbow_r",
        "axis": "X",
        "sign": 1.0,
        "moving_joints": ("wrist_r",),
        "moving_parts": (
            "bone_elbow_r__wrist_r",
            "joint_wrist_r",
        ),
        "readout_deg": 45.0,
        "description": (
            "the right elbow bends about the lateral hinge (+X); only the wrist moves, "
            "so transfer checks can see an articulated elbow rather than a rigid raise"
        ),
    },
    "spine_lean": {
        "pivot": "spine_base",
        "axis": "Y",
        "sign": -1.0,
        "moving_joints": ("chest_base", "neck_base", "head_top", "shoulder_l", "shoulder_r"),
        "moving_parts": (
            "bone_spine",
            "bone_chest",
            "joint_chest_base",
        ),
        "readout_deg": 15.0,
        "description": (
            "the torso leans about the spine base on +Y; upper sites move as a rigid "
            "group so sheet fixtures can cover spine-led motion"
        ),
    },
    # Lower-body arcs (F-71579a7f). Wave-35 covered upper arcs only; knee bend and a
    # seated hip hinge are the calibration fixtures procedural wire subjects still needed.
    "knee_r_bend": {
        "pivot": "knee_r",
        "axis": "X",
        "sign": 1.0,
        "moving_joints": ("ankle_r", "toe_r"),
        "moving_parts": (
            "bone_knee_r__ankle_r",
            "joint_ankle_r",
        ),
        "readout_deg": 45.0,
        "description": (
            "the right knee bends about the lateral hinge (+X); ankle and toe travel with "
            "the shin so transfer checks can see a lower-limb articulation"
        ),
    },
    "hip_sit": {
        "pivot": "hip_r",
        "axis": "X",
        "sign": 1.0,
        "moving_joints": ("knee_r", "ankle_r", "toe_r"),
        "moving_parts": (
            "bone_hip_r__knee_r",
            "bone_knee_r__ankle_r",
            "joint_knee_r",
        ),
        "readout_deg": 60.0,
        "description": (
            "the right hip hinges toward a seated posture about +X; the whole lower limb "
            "moves as a rigid group from the hip so sit/stand fixtures need no hand edit"
        ),
    },
}


def resolve_arc(name):
    """Look up an arc by name, or raise naming what is known.

    An unknown arc raises rather than falling back to a default: silently rendering the
    bind pose for a spec that asked for a performance is the failure G6 exists to catch,
    and it is cheaper to refuse it here than to detect it after 33 frames.
    """
    arc = POSE_ARCS.get(name)
    if arc is None:
        raise SpecError(
            f"unknown pose arc {name!r}; known: {sorted(POSE_ARCS)}",
            {"gate": None, "andon": "SpecError",
             "clause": "unknown_pose_arc"})
    return arc


def angle_at_frame(index, count, start_deg, end_deg):
    """The authored angle at control frame `index`, in degrees."""
    if count < 2:
        raise SpecError(f"a pose arc needs at least 2 frames, got {count}",
            {"gate": None, "andon": "SpecError",
             "clause": "too_few_frames_for_an_arc"})
    return start_deg + (end_deg - start_deg) * (index / float(count - 1))


def rotate_about_y(point, pivot, deg):
    """Rotate `point` about the vertical-plane axis +Y through `pivot`.

    Standard right-handed R_y: (x, y, z) -> (x cos + z sin, y, -x sin + z cos). The wire
    figure is planar at y = 0 and this rotation preserves y, so an arc built on it keeps
    every joint in the same plane — which is why a camera looking down ±Y sees the whole
    performance face-on with no foreshortening.
    """
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy, dz = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
    return (
        pivot[0] + dx * c + dz * s,
        pivot[1] + dy,
        pivot[2] - dx * s + dz * c,
    )


def rotate_about_x(point, pivot, deg):
    """Right-handed R_x through `pivot`: (x, y, z) -> (x, y cos - z sin, y sin + z cos)."""
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy, dz = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
    return (
        pivot[0] + dx,
        pivot[1] + dy * c - dz * s,
        pivot[2] + dy * s + dz * c,
    )


def rotate_about_z(point, pivot, deg):
    """Right-handed R_z through `pivot`: (x, y, z) -> (x cos - y sin, x sin + y cos, z)."""
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy, dz = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
    return (
        pivot[0] + dx * c - dy * s,
        pivot[1] + dx * s + dy * c,
        pivot[2] + dz,
    )


def rotate_about_axis(point, pivot, deg, axis):
    """Dispatch to the axis named on the arc data entry (F-72d73808)."""
    key = str(axis).upper()
    if key == "Y":
        return rotate_about_y(point, pivot, deg)
    if key == "X":
        return rotate_about_x(point, pivot, deg)
    if key == "Z":
        return rotate_about_z(point, pivot, deg)
    raise SpecError(
        f"pose arc axis {axis!r} is not one of X/Y/Z",
        {"gate": None, "andon": "SpecError",
         "clause": "unknown_pose_arc_axis", "axis": axis})


def joints_at_frame(joints, arc, index, count, start_deg, end_deg):
    """Every joint's true world position at control frame `index`.

    This is the ground truth the whole subject exists to provide: a measurement can ask
    *where was the wrist supposed to be on frame 20* and get a number, rather than an
    inference from a silhouette.
    """
    theta = angle_at_frame(index, count, start_deg, end_deg)
    applied = arc["sign"] * theta
    pivot = joints[arc["pivot"]]
    axis = arc.get("axis", "Y")
    out = {}
    for name, p in joints.items():
        if name in arc["moving_joints"]:
            out[name] = rotate_about_axis(p, pivot, applied, axis)
        else:
            out[name] = tuple(float(v) for v in p)
    return theta, out


def arc_readout(arc, count, start_deg, end_deg):
    """The timing quantity the arc is meant to be read by, computed before any render.

    ⚠ **This departs from the E03 spec's stated readout, deliberately and visibly.** The
    spec asks for "the frame index at which it passes horizontal" while also specifying the
    motion as "from T-pose to overhead". Those are inconsistent: a T-pose arm *starts*
    horizontal, so it never passes horizontal — it leaves it on frame 0, and a readout that
    always answers 0 measures nothing. The arm cannot move that number, which is the one
    property a readout must not have.

    The readout used instead is the frame at which the arm passes the arc's **registered
    readout angle** (`POSE_ARCS[...]["readout_deg"]`, 45° for `arm_r_raise`): monotonic,
    crossed exactly once, unambiguous by eye at the Director's zoom, and authored rather
    than measured. `leaves_start_frame` and `reaches_end_frame` are reported beside it so
    the whole profile is legible and the spec's original intent is still answerable from
    the record.

    ⚠ **The record used to call that angle the MIDPOINT, and no code computed one**
    (F-314c4a79). `readout_deg` is a per-arc literal; the arc's span is a caller's choice
    (`make_test_armature.py` exposes `--arc-start-deg` / `--arc-end-deg`). Measured here
    at count=33: 0..90 gives readout 45.0 at `crossing_frame_exact` 16.00, and the true
    midpoint frame is also 16.00 — they agree by construction. 0..180 gives the same
    readout 45.0 at frame 8.00, while the midpoint (90°) is frame 16.00: the record named
    MIDPOINT and reported the QUARTER crossing, off by 8 of 32 frames. The only guard was
    the "lies outside the arc" clause, which a 0..180 arc satisfies.
    `rig_character.py::author_probe` uses the fixed 0..90 `PROBE_ARC` so the shipped probe
    agreed by coincidence; the CLI path did not. (Re-anchored on the symbol 2026-09-04,
    F-0f035830: `rig_character.py:661` had drifted onto `gate_objects_registered`.)

    The registration is kept rather than re-derived — re-deriving would silently change a
    registered prediction, and the "outside the arc" refusal exists only because the
    registered angle is independent of the span. What is fixed is the claim: the record now
    reports `midpoint_deg`, `midpoint_frame_exact` and `is_the_midpoint`, and its note says
    "registered readout angle" and states whether the two coincide for THIS arc.

    Flagged for the advisor to overrule: it is a change to how a registered prediction is
    read, made before the prediction was registered and before anything was rendered.
    """
    if start_deg == end_deg:
        raise SpecError(
            f"pose arc start and end are both {start_deg}°; that is a held pose, not a "
            f"performance. Render a held pose with subject.animation='static' instead — "
            f"an arc that does not move would trip G6 after 33 frames of work",
            {"gate": None, "andon": "SpecError",
             "clause": "arc_does_not_move"})
    readout_deg = arc["readout_deg"]
    span = end_deg - start_deg
    if not (min(start_deg, end_deg) <= readout_deg <= max(start_deg, end_deg)):
        raise SpecError(
            f"readout angle {readout_deg}° lies outside the arc {start_deg}°..{end_deg}°; "
            f"it would never be crossed",
            {"gate": None, "andon": "SpecError",
             "clause": "readout_angle_outside_the_arc"})
    exact = (readout_deg - start_deg) / span * (count - 1)
    # The midpoint of THIS arc, computed rather than assumed (F-314c4a79). It is reported
    # beside the registered readout so a reader can see when the two coincide instead of
    # reading a note that claims they always do.
    midpoint_deg = 0.5 * (start_deg + end_deg)
    midpoint_exact = (midpoint_deg - start_deg) / span * (count - 1)
    is_midpoint = abs(readout_deg - midpoint_deg) < 1e-9
    return {
        "readout_deg": readout_deg,
        "crossing_frame_exact": exact,
        "crossing_frame_nearest": int(round(exact)),
        "lands_on_an_integer_frame": abs(exact - round(exact)) < 1e-9,
        "midpoint_deg": midpoint_deg,
        "midpoint_frame_exact": midpoint_exact,
        "is_the_midpoint": is_midpoint,
        "leaves_start_frame": 0,
        "reaches_end_frame": count - 1,
        "start_deg": start_deg,
        "end_deg": end_deg,
        "frames": count,
        "monotonic": True,
        # F-93f0e38f. `monotonic` sat here as a literal beside eleven fields computed from
        # the arc, and nothing measures it: `angle_at_frame` is linear in the frame index
        # by construction, so the value is True for every possible input and takes the same
        # value when the arc is what it claims and when it is anything else. "Grade an arm
        # only on what it can move" — a field that cannot be False is not a measurement,
        # and the E03 report quotes this record. It is LABELLED rather than deleted,
        # because the property is real and a reader wants to know it holds; the label says
        # who guarantees it. The shape is `binding.rigid_segment_weights`', carried rather
        # than re-invented.
        "invariant_by_construction": ["monotonic"],
        "invariant_by_construction_note": (
            "`monotonic` is a property of the formula, not of this arc: `angle_at_frame` "
            "is linear in the frame index, so it is True for every arc this module can "
            "build and no code checks it. A real measurement of monotonicity would be "
            "taken on the angles read back OUT of the rendered performance, where the "
            "value can differ."),
        "note": (
            "The readout is the arc's REGISTERED readout angle, not 'passes horizontal'. "
            "A T-pose arm begins horizontal, so the spec's stated readout is 0 for every "
            "possible outcome and cannot be moved by the arm. "
            + ("For this arc the registered readout IS the midpoint of the span."
               if is_midpoint else
               f"For this arc the registered readout {readout_deg}deg is NOT the midpoint "
               f"of {start_deg}..{end_deg}deg (midpoint {midpoint_deg}deg, frame "
               f"{midpoint_exact}); the crossing reported above is the registered angle's.")
            + " See arc_readout.__doc__."
        ),
    }
