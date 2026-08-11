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
            f"unknown pose arc {name!r}; known: {sorted(POSE_ARCS)}"
        )
    return arc


def angle_at_frame(index, count, start_deg, end_deg):
    """The authored angle at control frame `index`, in degrees."""
    if count < 2:
        raise SpecError(f"a pose arc needs at least 2 frames, got {count}")
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


def joints_at_frame(joints, arc, index, count, start_deg, end_deg):
    """Every joint's true world position at control frame `index`.

    This is the ground truth the whole subject exists to provide: a measurement can ask
    *where was the wrist supposed to be on frame 20* and get a number, rather than an
    inference from a silhouette.
    """
    theta = angle_at_frame(index, count, start_deg, end_deg)
    applied = arc["sign"] * theta
    pivot = joints[arc["pivot"]]
    out = {}
    for name, p in joints.items():
        if name in arc["moving_joints"]:
            out[name] = rotate_about_y(p, pivot, applied)
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

    The readout used instead is the frame at which the arm passes the **midpoint angle**
    (45° for a 0→90° arc): monotonic, crossed exactly once, unambiguous by eye at the
    Director's zoom, and authored rather than measured. `leaves_start_frame` and
    `reaches_end_frame` are reported beside it so the whole profile is legible and the
    spec's original intent is still answerable from the record.

    Flagged for the advisor to overrule: it is a change to how a registered prediction is
    read, made before the prediction was registered and before anything was rendered.
    """
    if start_deg == end_deg:
        raise SpecError(
            f"pose arc start and end are both {start_deg}°; that is a held pose, not a "
            f"performance. Render a held pose with subject.animation='static' instead — "
            f"an arc that does not move would trip G6 after 33 frames of work"
        )
    readout_deg = arc["readout_deg"]
    span = end_deg - start_deg
    if not (min(start_deg, end_deg) <= readout_deg <= max(start_deg, end_deg)):
        raise SpecError(
            f"readout angle {readout_deg}° lies outside the arc {start_deg}°..{end_deg}°; "
            f"it would never be crossed"
        )
    exact = (readout_deg - start_deg) / span * (count - 1)
    return {
        "readout_deg": readout_deg,
        "crossing_frame_exact": exact,
        "crossing_frame_nearest": int(round(exact)),
        "lands_on_an_integer_frame": abs(exact - round(exact)) < 1e-9,
        "leaves_start_frame": 0,
        "reaches_end_frame": count - 1,
        "start_deg": start_deg,
        "end_deg": end_deg,
        "frames": count,
        "monotonic": True,
        "note": (
            "The readout is the MIDPOINT crossing, not 'passes horizontal'. A T-pose arm "
            "begins horizontal, so the spec's stated readout is 0 for every possible "
            "outcome and cannot be moved by the arm. See arc_readout.__doc__."
        ),
    }
