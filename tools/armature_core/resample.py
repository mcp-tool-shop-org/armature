"""Resample a motion record to a different sample count over the identical duration.

No bpy, no numpy, no cv2 — arithmetic only, so its tests run in milliseconds and every
claim in them is checkable against mathematics rather than against a render. Same split as
`lift_solve`, whose representation this module reads and writes unchanged.

--------------------------------------------------------------------------------
Why interpolation is not a matter of taste here

The motion record stores each bone's LOCAL rotation as a 3x3 matrix (measured at use,
2026-08-12: `lifted_ema.motion.json`, 65 frames x 22 bones, every matrix orthonormal to
2.6e-15, because `lift_clip.ema_rotations` SVD-orthonormalises after each smoothing step).
Rotations do not live in a vector space, and the two obvious wrong moves both produce
something that plays:

* **Element-wise averaging of two rotation matrices is not a rotation.** The result has
  determinant below one and non-orthogonal columns; applied through `fk_sites` it scales
  and shears the body a little on every in-between frame. Nothing raises — the limbs simply
  shrink and skew at the frames nobody authored.
* **Averaging Euler triples interpolates the parameterisation, not the orientation.** Two
  triples that name the same orientation differ, and the path between them swings through
  poses neither endpoint asked for.

So each bone's rotation is carried to a **unit quaternion**, interpolated along the
**shortest great-circle arc** (slerp), and carried back. Root translation is a position in
a vector space, and linear interpolation is the same statement there.

**The double cover is the trap that makes this more than a formula.** A rotation has two
quaternion representations, `q` and `-q`, naming the identical orientation. Interpolating
between `q0` and a `q1` that happens to be the far representative takes the long way round
the sphere — nearly 360 degrees of spin where the correct answer was a few degrees. Nothing
errors, the count is right, the endpoints are right, and the character throws a limb around
between two nearly identical poses. `slerp` therefore negates `q1` whenever the dot product
is negative, and `test_resample.py` builds that case explicitly.

--------------------------------------------------------------------------------
What "the identical duration" means, exactly

The mapping is index-space: destination sample `j` reads source position
`u = j * (n_src - 1) / (n_dst - 1)`. Both endpoints therefore land ON source samples, and
the sample interval scales by `(n_src - 1) / (n_dst - 1)`. A record sampled at `fps_src`
resamples to `fps_dst = fps_src * (n_dst - 1) / (n_src - 1)` if the wall-clock span between
the first and last sample is to be unchanged — 65 -> 81 at 16 fps gives exactly 20.0 fps.

Endpoint samples are returned **verbatim**, not round-tripped through a quaternion. The
algebra says the round trip is an identity; float64 says it is an identity to about 1e-16,
and "the endpoints are the source's own endpoints" is a contract about the record rather
than about the algebra. `resample_frames` short-circuits at `t == 0.0` for that reason and
`endpoints_match` gates it.
"""

import math

from .errors import ArmatureError, GateFailure

TOOL_VERSION = "E10.1"

#: How far from orthonormal a stored matrix may be before it is not a rotation. Measured
#: float64 noise on this repo's own records is ~3e-15; a real defect (an element-wise
#: average of two rotations, a scaled matrix, a transposed convention) is orders of
#: magnitude larger. Sitting the bound between them means the gate cannot fire on correct
#: work and cannot stay silent on the failure it exists for.
ORTHONORMAL_TOL = 1e-6

#: Below this angular separation the slerp denominator `sin(theta)` is small enough that
#: the quotient loses precision, and a normalised linear blend is both stable and — at that
#: separation — indistinguishable from the arc.
SLERP_LINEAR_EPS = 1e-9


class ResampleError(ArmatureError):
    """The record cannot be resampled as asked."""


class ResampleGate(GateFailure):
    """A resampling invariant did not hold. Never a tuning target."""

    gate = "RESAMPLE"


# ------------------------------------------------------------------ rotation algebra

def is_rotation(m, tol=ORTHONORMAL_TOL):
    """Is this 3x3 a rotation — orthonormal, right-handed? Returns (bool, worst, det)."""
    worst = 0.0
    for i in range(3):
        for j in range(3):
            dot = sum(m[k][i] * m[k][j] for k in range(3))
            worst = max(worst, abs(dot - (1.0 if i == j else 0.0)))
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    return (worst <= tol and abs(det - 1.0) <= tol), worst, det


def require_rotation(m, where, tol=ORTHONORMAL_TOL):
    """· ANDON — the input really is a rotation, checked before it is believed.

    Put on the direction the invariant does not bound: nothing upstream of this module
    guarantees that what a motion record calls a rotation is one. A matrix that is merely
    NEAR a rotation converts to a quaternion that is silently wrong, interpolates to
    something plausible, and lands a body slightly sheared on every frame — while every
    count, every frame index and every downstream legality check passes.

    It raises rather than repairing. Orthonormalising here would erase the evidence that
    the record arrived broken, and the repair would be indistinguishable in the output from
    a record that was fine.
    """
    ok, worst, det = is_rotation(m, tol)
    if not ok:
        raise ResampleGate(
            f"{where}: this 3x3 is not a rotation — worst |M^T M - I| entry {worst:.3e}, "
            f"det {det:.12f}, against a tolerance of {tol:.1e}. Interpolating it would "
            f"produce a plausible pose that shears the body, and nothing downstream checks "
            f"for that",
            {"gate": "RESAMPLE", "where": where, "orthonormality_error": worst,
             "determinant": det, "tolerance": tol})
    return {"orthonormality_error": worst, "determinant": det}


def mat_to_quat(m):
    """A rotation matrix to a unit quaternion `(w, x, y, z)`, Shepperd's branch.

    The branch is not decoration. The naive trace formula divides by `sqrt(trace + 1)`,
    which goes to zero at a 180-degree rotation and has already lost most of its precision
    well before that; choosing the branch on the largest diagonal term keeps the divisor
    away from zero for every rotation. Convention: `mat_vec` applies `M` to a column
    vector, which is what `lift_solve.axis_angle` produces, so this reads the same matrices
    the solver wrote.
    """
    m00, m01, m02 = m[0]
    m10, m11, m12 = m[1]
    m20, m21, m22 = m[2]
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = (0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        q = ((m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s)
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        q = ((m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s)
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        q = ((m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s)
    return quat_normalise(q)


def quat_normalise(q):
    n = math.sqrt(sum(c * c for c in q))
    if n < 1e-12:
        raise ResampleError("a zero quaternion names no orientation and cannot be "
                            "normalised")
    return tuple(c / n for c in q)


def quat_to_mat(q):
    """A unit quaternion back to a 3x3 rotation, the same convention as `mat_to_quat`."""
    w, x, y, z = quat_normalise(q)
    return ((1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z), 2.0 * (x * z + w * y)),
            (2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)),
            (2.0 * (x * z - w * y), 2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y)))


def quat_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def slerp(q0, q1, t):
    """Shortest-arc spherical linear interpolation between two unit quaternions.

    Two clauses, each with a silent failure behind it:

    * **the double cover** — `q` and `-q` are the same orientation, so the sign of `q1` is
      chosen to make the arc the short one. Without it the in-betweens take the long way
      round and the limb spins.
    * **the near-parallel case** — `sin(theta)` in the denominator goes to zero as the two
      orientations coincide, so below `SLERP_LINEAR_EPS` a normalised linear blend is used.
      At that separation the two agree far beyond float64's ability to tell them apart.
    """
    q0 = quat_normalise(q0)
    q1 = quat_normalise(q1)
    d = quat_dot(q0, q1)
    if d < 0.0:
        q1 = tuple(-c for c in q1)
        d = -d
    d = max(-1.0, min(1.0, d))
    if 1.0 - d < SLERP_LINEAR_EPS:
        return quat_normalise(tuple(a + t * (b - a) for a, b in zip(q0, q1)))
    theta = math.acos(d)
    s = math.sin(theta)
    a = math.sin((1.0 - t) * theta) / s
    b = math.sin(t * theta) / s
    return quat_normalise(tuple(a * x + b * y for x, y in zip(q0, q1)))


def slerp_matrix(m0, m1, t):
    """The rotation `t` of the way from `m0` to `m1`, along the shortest arc."""
    return quat_to_mat(slerp(mat_to_quat(m0), mat_to_quat(m1), t))


def geodesic_deg(a, b):
    """Angle of the rotation carrying `a` onto `b`, in degrees. The comparison unit.

    Compared as matrices, never as Euler triples: two triples that differ can name the same
    orientation, and a report that subtracted them would print an error that is not one.
    """
    r = tuple(tuple(sum(a[k][i] * b[k][j] for k in range(3)) for j in range(3))
              for i in range(3))
    tr = r[0][0] + r[1][1] + r[2][2]
    return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1.0) / 2.0))))


# ------------------------------------------------------------------- the index map

def sample_map(n_src, n_dst):
    """`[(i, t)]` per destination sample: read source `i` and `i + 1`, blend by `t`.

    Both endpoints are made exact by construction rather than by hoping the division lands
    on an integer, and every position is strictly increasing, which `monotonic` gates.
    """
    if n_src < 2:
        raise ResampleError(f"a {n_src}-sample record carries no interval to resample over")
    if n_dst < 2:
        raise ResampleError(f"resampling to {n_dst} samples would discard the performance")
    out = []
    span = n_src - 1
    for j in range(n_dst):
        if j == 0:
            out.append((0, 0.0))
            continue
        if j == n_dst - 1:
            out.append((span, 0.0))
            continue
        u = j * span / (n_dst - 1)
        i = int(math.floor(u))
        t = u - i
        if i >= span:                     # u landed on (or past) the last source sample
            i, t = span, 0.0
        out.append((i, t))
    return out


def positions(n_src, n_dst):
    """The source position each destination sample reads. A diagnostic and a fixture."""
    return [i + t for i, t in sample_map(n_src, n_dst)]


def monotonic(n_src, n_dst):
    """· ANDON — the resampled timeline runs forwards and spans the source exactly.

    A mapping that stalled or reversed would emit a sequence that plays, counts correctly,
    and holds or stutters at the stall. The gate is on time itself because nothing else in
    the chain looks at it.
    """
    u = positions(n_src, n_dst)
    bad = [(k, u[k], u[k + 1]) for k in range(len(u) - 1) if not (u[k + 1] > u[k])]
    ev = {"gate": "RESAMPLE", "n_src": n_src, "n_dst": n_dst,
          "first": u[0], "last": u[-1], "non_increasing": bad}
    if bad:
        raise ResampleGate(
            f"the resampled timeline is not strictly increasing at {len(bad)} position(s), "
            f"first at destination sample {bad[0][0]}: {bad[0][1]} -> {bad[0][2]}", ev)
    if u[0] != 0.0 or u[-1] != float(n_src - 1):
        raise ResampleGate(
            f"the resampled timeline spans {u[0]}..{u[-1]} where the source spans "
            f"0..{n_src - 1}; the performance would be cropped or extrapolated", ev)
    ev["verdict"] = f"{n_dst} strictly increasing positions spanning 0..{n_src - 1}"
    return ev


def fps_for(fps_src, n_src, n_dst):
    """The playback rate that leaves the first-to-last wall-clock span unchanged."""
    return fps_src * (n_dst - 1) / (n_src - 1)


# ------------------------------------------------------------------- the resampling

def lerp_vec(a, b, t):
    return tuple(x + t * (y - x) for x, y in zip(a, b))


def _as_mat(m):
    return tuple(tuple(float(v) for v in row) for row in m)


def resample_frames(frames, n_dst):
    """Resample `{frame, local: {bone: 3x3}, root: [x, y, z]}` records to `n_dst` frames.

    Every input rotation is gated as a rotation FIRST — before any of them is believed — so
    a broken record halts before a single in-between exists rather than after the whole
    sequence is built.
    """
    n_src = len(frames)
    monotonic(n_src, n_dst)

    bones = list(frames[0].get("local") or {})
    if not bones:
        raise ResampleError("frame 0 carries no bone rotations to resample")
    for k, fr in enumerate(frames):
        names = list(fr.get("local") or {})
        if set(names) != set(bones):
            raise ResampleError(
                f"frame {k} disagrees with frame 0 about which bones exist "
                f"({sorted(set(names) ^ set(bones))}); interpolating across a changing bone "
                f"set would hold the missing bone's last pose with nothing reporting it")
        for name in names:
            require_rotation(_as_mat(fr["local"][name]), f"frame {k}, bone {name!r}")
        root = fr.get("root")
        if not (isinstance(root, (list, tuple)) and len(root) == 3):
            raise ResampleError(f"frame {k}: root is {root!r}, not a 3-vector")

    out = []
    for j, (i, t) in enumerate(sample_map(n_src, n_dst)):
        src = frames[i]
        if t == 0.0:
            # Verbatim, not round-tripped: "the endpoints are the source's own endpoints"
            # is a contract about the record, not about the algebra.
            local = {b: _as_mat(src["local"][b]) for b in bones}
            root = tuple(float(v) for v in src["root"])
        else:
            nxt = frames[i + 1]
            local = {b: slerp_matrix(_as_mat(src["local"][b]),
                                     _as_mat(nxt["local"][b]), t) for b in bones}
            root = lerp_vec([float(v) for v in src["root"]],
                            [float(v) for v in nxt["root"]], t)
        out.append({"frame": j,
                    "local": {b: [list(r) for r in local[b]] for b in bones},
                    "root": list(root)})
    return out


def endpoints_match(src_frames, dst_frames):
    """· ANDON — the resampled record starts and ends on the source's own end poses.

    The failure this guards has no symptom anywhere else: an off-by-one in the index map,
    or a `t` that never quite reaches zero, shifts the whole performance by a fraction of a
    frame. The count is right, the timeline is monotonic, every rotation is a rotation, and
    the clip plays — starting a little into the dance and ending a little before it
    finishes. Compared as stored VALUES, because that is what the contract says.
    """
    pairs = ((0, 0, "first"), (len(src_frames) - 1, len(dst_frames) - 1, "last"))
    ev = {"gate": "RESAMPLE", "checked": []}
    for si, di, label in pairs:
        s, d = src_frames[si], dst_frames[di]
        rot_bad = [b for b in s["local"]
                   if _as_mat(s["local"][b]) != _as_mat(d["local"][b])]
        root_bad = tuple(float(v) for v in s["root"]) != tuple(float(v) for v in d["root"])
        if rot_bad or root_bad:
            raise ResampleGate(
                f"the {label} resampled frame is not the source's {label} frame: "
                f"{len(rot_bad)} bone rotation(s) differ"
                + (" and the root translation differs" if root_bad else "")
                + ". The performance would be shifted in time with every count still right",
                dict(ev, label=label, bones=sorted(rot_bad)[:8], root_differs=root_bad))
        ev["checked"].append(label)
    ev["verdict"] = "first and last frames are the source's own, value for value"
    return ev


def step_angles(frames, bones=None):
    """Per bone, the geodesic angle between consecutive frames. A DIAGNOSTIC; gates nothing.

    What it is for: a resampled record's steps should be smaller than the source's by the
    interval ratio wherever the path is smooth, and the same size wherever the source
    turned a corner. Reporting the distribution rather than a single number is the point —
    slerp densifies the path between knots and leaves the knots exactly where they were.
    """
    names = list(bones or frames[0]["local"])
    out = {}
    for b in names:
        seq = [_as_mat(fr["local"][b]) for fr in frames]
        d = [geodesic_deg(seq[i], seq[i + 1]) for i in range(len(seq) - 1)]
        if not d:
            continue
        s = sorted(d)
        out[b] = {"n": len(d), "median_deg": s[len(s) // 2],
                  "p90_deg": s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))],
                  "max_deg": s[-1], "sum_deg": sum(d)}
    return out
