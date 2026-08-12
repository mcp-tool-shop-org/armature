"""The gait model — a walk, a stop, and an emote, as numbers.

No bpy, no numpy, no file IO. That is deliberate and it is the same split
`blender_scene` / `channels` already uses (DECOMPOSE_BY_SECRETS): the thing that
changes when the performance changes is the gait, and the thing that changes when
Blender changes is the driver. Keeping the gait out here means its tests run in
milliseconds without Blender, and — more to the point — means the **authored ground
truth** is computed from the authored angles rather than read back from the mesh the
measurement is supposed to grade. E03 earned that: only the authored ground truth
caught a performance that arrived at two thirds of its magnitude while every gate
passed.

--------------------------------------------------------------------------------
Conventions, all measured on this character rather than assumed

* Blender/armature space is **Z up**. The character's facing and handedness are
  MEASURED properties of the mesh, carried in E07's rig manifest
  (`facing.facing_y_sign`, `facing.left_x_sign`) and passed in here — never
  hard-coded, because "the arm named _r" was a label on a planar T-pose once
  already (sitelist.PROBE_ARC_SIDE_X_SIGN records that lesson).
* A bone's authored pose is a rotation about **world axes**, applied about the
  bone's own rest head, composed as ``Rx @ Ry @ Rz``. Order matters exactly once —
  the gesture abducts (Y) and then lifts (X), and lifting first would leave the
  abduction rotating the arm about its own length instead of swinging it out.
* Positive rotation about +X carries a downward-pointing limb toward **+Y**. So a
  limb swings *forward* with the sign of `facing_y_sign`. Every sign below is
  derived from that sentence; none is a magic constant.

--------------------------------------------------------------------------------
Why the forward travel is integrated rather than dialled in

A walk whose hips advance at a rate somebody typed in slides: the stance foot skates
because the body speed and the leg swing disagree. Here the hips' forward increment
is derived from the stance leg's own geometry every frame —

    d(hip_y) = -L_leg * d(sin theta_stance)

which is exactly the condition "the planted ankle does not move". `L_leg` is the
character's **own measured hip-to-ankle distance**, not a constant: a global constant
must not govern a local feature. The residual slip (from blending the two legs across
double support) is then a *measurement*, reported by `foot_slip`, not a hope.
"""

import math

#: Bones the gait writes. The five facial markers (`nose`, `eye.*`, `ear.*`) are
#: registered non-deforming and are deliberately NOT keyed — they deform nothing, so a
#: key on them would be a channel that cannot change a rendered pixel.
GAIT_BONES = (
    "hips", "spine", "chest", "neck", "head",
    "shoulder.L", "elbow.L", "wrist.L",
    "shoulder.R", "elbow.R", "wrist.R",
    "hip.L", "knee.L", "ankle.L",
    "hip.R", "knee.R", "ankle.R",
)

#: Parent of each gait bone, mirroring `sitelist.BONES`. Held here as well so the FK
#: ground truth can be computed without importing the site list's Bone objects — and
#: `tests/test_walk.py` checks the two agree, so they cannot drift apart.
PARENT = {
    "hips": None, "spine": "hips", "chest": "spine", "neck": "chest", "head": "neck",
    "shoulder.L": "chest", "elbow.L": "shoulder.L", "wrist.L": "elbow.L",
    "shoulder.R": "chest", "elbow.R": "shoulder.R", "wrist.R": "elbow.R",
    "hip.L": "hips", "knee.L": "hip.L", "ankle.L": "knee.L",
    "hip.R": "hips", "knee.R": "hip.R", "ankle.R": "knee.R",
}

#: Rest head landmark per gait bone (sitelist's `head` column).
HEAD_LANDMARK = {
    "hips": "crotch", "spine": "spine_base", "chest": "chest_base",
    "neck": "neck_base", "head": "head_base",
    "shoulder.L": "shoulder_L", "elbow.L": "elbow_L", "wrist.L": "wrist_L",
    "shoulder.R": "shoulder_R", "elbow.R": "elbow_R", "wrist.R": "wrist_R",
    "hip.L": "hip_L", "knee.L": "knee_L", "ankle.L": "ankle_L",
    "hip.R": "hip_R", "knee.R": "knee_R", "ankle.R": "ankle_R",
}


class WalkError(ValueError):
    """The gait could not be built as specified."""


# ------------------------------------------------------------------ small numerics


def smootherstep(x):
    """Ken Perlin's C2 smoothstep. Clamped, so callers cannot run off either end."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mat_vec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def _rot(axis, deg):
    """Rotation matrix about a world axis, right-handed, degrees in."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    if axis == "X":
        return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    if axis == "Y":
        return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    if axis == "Z":
        return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]
    raise WalkError(f"unknown axis {axis!r}; expected 'X', 'Y' or 'Z'")


def rotation_matrix(rx, ry, rz):
    """The authored per-bone rotation, ``Rx @ Ry @ Rz``, degrees in.

    The order is load-bearing for the gesture and irrelevant for everything else (the
    walk uses one axis per bone). Rz is applied first, then Ry, then Rx: the arm
    abducts away from the body and *then* lifts, which is the shape of a raised hand.
    Lifting first would put the arm along +/-Y and the abduction would spin it about
    its own length instead of swinging it out — measured on paper, then on the sheet.
    """
    return _mat_mul(_rot("X", rx), _mat_mul(_rot("Y", ry), _rot("Z", rz)))


# ----------------------------------------------------------------------- parameters


class GaitParams:
    """Every number the performance is made of. All of them are in this one place so
    a report can quote the recipe and a reader can re-derive any frame by hand."""

    def __init__(
        self,
        n_walk=40, n_decel=8, n_gesture=12, n_hold=5,
        steps=5, stance_frac=0.5,
        hip_swing_deg=12.0, knee_flex_deg=42.0,
        arm_swing_deg=14.0, elbow_base_deg=9.0, elbow_swing_deg=7.0,
        ankle_level_frac=0.60, sway_frac=0.30, chest_twist_deg=4.0,
        nod_peak_deg=15.0, nod_settle_deg=6.0,
        gesture_lift_deg=105.0, gesture_abduct_deg=30.0, gesture_elbow_deg=55.0,
        gesture_wrist_deg=12.0,
    ):
        self.n_walk = int(n_walk)
        self.n_decel = int(n_decel)
        self.n_gesture = int(n_gesture)
        self.n_hold = int(n_hold)
        self.steps = int(steps)
        self.stance_frac = float(stance_frac)
        self.hip_swing_deg = float(hip_swing_deg)
        self.knee_flex_deg = float(knee_flex_deg)
        self.arm_swing_deg = float(arm_swing_deg)
        self.elbow_base_deg = float(elbow_base_deg)
        self.elbow_swing_deg = float(elbow_swing_deg)
        self.ankle_level_frac = float(ankle_level_frac)
        self.sway_frac = float(sway_frac)
        self.chest_twist_deg = float(chest_twist_deg)
        self.nod_peak_deg = float(nod_peak_deg)
        self.nod_settle_deg = float(nod_settle_deg)
        self.gesture_lift_deg = float(gesture_lift_deg)
        self.gesture_abduct_deg = float(gesture_abduct_deg)
        self.gesture_elbow_deg = float(gesture_elbow_deg)
        self.gesture_wrist_deg = float(gesture_wrist_deg)

        if min(self.n_walk, self.n_decel, self.n_gesture, self.n_hold) < 1:
            raise WalkError("every phase must be at least one frame long")
        if self.steps < 1:
            raise WalkError("a walk needs at least one step")
        if not 0.0 < self.stance_frac < 1.0:
            raise WalkError(
                f"stance_frac={self.stance_frac}; a leg must spend part of the cycle on "
                f"the ground and part of it in the air"
            )

    @property
    def n_frames(self):
        return self.n_walk + self.n_decel + self.n_gesture + self.n_hold

    def as_dict(self):
        return {k: v for k, v in sorted(vars(self).items())}


class Performer:
    """The character's MEASURED metrics — everything the gait scales itself against.

    Built from E07's rig manifest, never typed in. `leg_length` is the mean hip-to-ankle
    distance of this mesh; `hip_half_separation` is half the distance between its own hip
    landmarks. Both exist so that no length in the gait is a global constant.
    """

    def __init__(self, landmarks, facing_y_sign, left_x_sign):
        missing = [n for n in set(HEAD_LANDMARK.values()) if n not in landmarks]
        extra = [n for n in ("toe_L", "toe_R", "hand_end_L", "hand_end_R") if n not in landmarks]
        if missing or extra:
            raise WalkError(
                f"the landmark table is missing {sorted(missing + extra)}; the gait scales "
                f"itself against this character's own measurements and cannot proceed on "
                f"defaults"
            )
        self.landmarks = {k: [float(v) for v in p] for k, p in landmarks.items()}
        self.facing_y_sign = float(facing_y_sign)
        self.left_x_sign = float(left_x_sign)
        if self.facing_y_sign not in (1.0, -1.0) or self.left_x_sign not in (1.0, -1.0):
            raise WalkError(
                f"facing_y_sign={facing_y_sign} left_x_sign={left_x_sign}; both are "
                f"measured signs and must be exactly +1 or -1"
            )

        def dist(a, b):
            pa, pb = self.landmarks[a], self.landmarks[b]
            return math.sqrt(sum((pa[i] - pb[i]) ** 2 for i in range(3)))

        self.leg_length = 0.5 * (dist("hip_L", "ankle_L") + dist("hip_R", "ankle_R"))
        self.arm_length = 0.5 * (dist("shoulder_L", "wrist_L") + dist("shoulder_R", "wrist_R"))
        self.hip_half_separation = 0.5 * abs(
            self.landmarks["hip_L"][0] - self.landmarks["hip_R"][0]
        )
        zs = [p[2] for p in self.landmarks.values()]
        self.height = max(zs) - min(zs)
        if self.leg_length <= 0.0 or self.height <= 0.0:
            raise WalkError("the measured leg length or height is not positive")

    def as_dict(self):
        return {
            "leg_length": self.leg_length,
            "arm_length": self.arm_length,
            "hip_half_separation": self.hip_half_separation,
            "landmark_height_span": self.height,
            "facing_y_sign": self.facing_y_sign,
            "left_x_sign": self.left_x_sign,
        }


# ------------------------------------------------------------------------ the gait


def _phase_schedule(p):
    """Per-frame gait speed in [0, 1], and the phase angle it integrates to.

    The phase rate is **solved**, not chosen: omega is set so the last moving frame
    lands the cycle on a half-step boundary, where the legs pass each other, rather than
    freezing the figure mid-stride. Typing a rate in and hoping the stop lands somewhere
    presentable is how a walk ends with one leg stuck out.
    """
    speed = [1.0] * p.n_walk
    for j in range(p.n_decel):
        speed.append(1.0 - smootherstep((j + 1) / float(p.n_decel)))
    moving_frames = p.n_walk + p.n_decel
    effective = sum(speed[:moving_frames])
    if effective <= 0.0:
        raise WalkError("the deceleration envelope leaves no moving frames")
    omega = (p.steps + 0.5) * math.pi / effective

    phase = [0.0]
    for i in range(1, moving_frames + 1):
        phase.append(phase[-1] + omega * speed[i - 1])
    # Past the stop the phase is frozen. The amplitude envelope has already reached 0 by
    # then, so both legs are straight and together whatever the phase happens to be.
    while len(phase) < p.n_frames:
        phase.append(phase[-1])
    speed.extend([0.0] * (p.n_frames - len(speed)))
    return speed[:p.n_frames], phase[:p.n_frames], omega


def _leg_state(u, stance_frac):
    """(psi_unit, knee_unit, is_stance) for one leg at cycle position `u` in [0, 1).

    `psi_unit` is the leg's swing in units of the amplitude, measured **positive
    forward**; `knee_unit` is flexion in units of its amplitude and is never negative,
    because a knee is a hinge.

    THE shape that matters, and the first version got it wrong: through stance the leg
    rotates at a CONSTANT rate. A sinusoidal leg angle is stationary at both extremes,
    so the body it carries stalls twice per cycle and the planted foot skates to make up
    the difference — measured at 0.226 of slip against a 0.231 stride, i.e. the foot
    moved almost a whole step while it was supposed to be on the floor. A linear stance
    ramp makes the hip's forward rate constant and the same at the instant the legs
    exchange, which is what plants the foot.

    Knee flexion is zero through the whole of stance. That is not cosmetic: the forward
    travel below is derived assuming the stance leg is straight, so a knee that bent
    under load would be describing a different leg than the one on the ground.
    """
    if u < stance_frac:
        v = u / stance_frac
        return 1.0 - 2.0 * v, 0.0, True
    v = (u - stance_frac) / (1.0 - stance_frac)
    # skewed bump: zero at toe-off and at heel strike, peaking about 30% into swing
    knee = math.sin(math.pi * (v ** 0.75)) ** 1.4
    return -1.0 + 2.0 * smootherstep(v), knee, False


def _integrate_forward(performer, p, phase, speed, legs):
    """The hips' forward travel, integrated from whichever leg is on the floor.

    The whole point of the tool: `d(hip_y) = -L * d(sin theta_stance)` is the condition
    "the planted ankle does not move", so this is derived from the character's own leg
    rather than being a speed somebody typed in.

    **The stance exchange is handled exactly**, and that detail is worth its lines. The
    incoming leg arrives at the end of its swing, where the smootherstep is flat, so on
    the frame it takes over its own sin has barely changed — differencing it across the
    switch reports a body that stalled. Measured: one frame in eight showed the hips
    advancing 0.0003 where the neighbouring frames advanced 0.029, and the slide statistic
    read 9.1 at exactly that frame. Splitting the increment at the boundary — outgoing leg
    up to psi = -1, incoming leg from psi = +1 — removes it, because those two states are
    the same instant of the same gait.
    """
    L = performer.leg_length
    fy = performer.facing_y_sign

    def s_of(psi, amp):
        return math.sin(math.radians(p.hip_swing_deg * amp * fy * psi))

    ys = [0.0]
    for i in range(1, len(phase)):
        a, b = legs[i - 1], legs[i]
        amp_a, amp_b = speed[i - 1], speed[i]
        y = ys[-1]
        if a["stance_L"] == b["stance_L"]:
            key = "psi_L" if b["stance_L"] else "psi_R"
            y += -L * (s_of(b[key], amp_b) - s_of(a[key], amp_a))
        else:
            # More than one exchange inside a frame interval means the cadence has
            # outrun the frame rate; nothing downstream could reconstruct the walk.
            du = (phase[i] - phase[i - 1]) / (2.0 * math.pi)
            if du > 0.5:
                raise WalkError(
                    f"frame {i}: the gait advances {du:.3f} of a cycle in one frame, so "
                    f"more than one stance exchange falls between two samples; the walk "
                    f"cannot be represented at this frame rate"
                )
            amp_mid = 0.5 * (amp_a + amp_b)
            out_key = "psi_L" if a["stance_L"] else "psi_R"
            in_key = "psi_L" if b["stance_L"] else "psi_R"
            y += -L * (s_of(-1.0, amp_mid) - s_of(a[out_key], amp_a))
            y += -L * (s_of(b[in_key], amp_b) - s_of(1.0, amp_mid))
        ys.append(y)
    return ys


def build_gait(performer, params):
    """The whole performance: per-frame world-axis rotations and the hips' translation.

    Returns a dict with `frames` (one record per frame, each mapping bone -> channels),
    plus the resolved schedule and derived stride numbers. Pure: the same inputs return
    the same floats, which is what `tests/test_walk.py::test_determinism` pins.
    """
    p = params
    fy = performer.facing_y_sign
    lx = performer.left_x_sign
    L = performer.leg_length
    speed, phase, omega = _phase_schedule(p)

    n = p.n_frames
    frames = []

    # ---- pass 1: every leg's state, so the forward travel can be integrated with the
    # stance exchange handled exactly rather than landing between two samples.
    legs = []
    for i in range(n):
        u_L = (phase[i] / (2.0 * math.pi)) % 1.0
        psi_L, kn_L, stance_L = _leg_state(u_L, p.stance_frac)
        psi_R, kn_R, _ = _leg_state((u_L + 0.5) % 1.0, p.stance_frac)
        legs.append({"u_L": u_L, "psi_L": psi_L, "psi_R": psi_R,
                     "kn_L": kn_L, "kn_R": kn_R, "stance_L": stance_L})

    hips_y = _integrate_forward(performer, p, phase, speed, legs)

    # phase boundaries, 0-based frame indices, half-open at the top
    f_decel = p.n_walk
    f_gesture = p.n_walk + p.n_decel
    f_hold = f_gesture + p.n_gesture

    for i in range(n):
        phi = phase[i]
        amp = speed[i]
        st = legs[i]
        u_L, psi_L, psi_R = st["u_L"], st["psi_L"], st["psi_R"]
        kn_L, kn_R, stance_L = st["kn_L"], st["kn_R"], st["stance_L"]

        # ---- legs. `fy` puts the swing in the direction the character actually faces:
        # positive about +X carries a hanging limb toward +Y, so forward is fy's sign.
        th_hip_L = p.hip_swing_deg * amp * fy * psi_L
        th_hip_R = p.hip_swing_deg * amp * fy * psi_R
        # A knee bends backward: positive about +X carries the shin toward +Y, which is
        # backward when the character faces -Y, so the sign follows -fy.
        knee_L = p.knee_flex_deg * amp * kn_L * -fy
        knee_R = p.knee_flex_deg * amp * kn_R * -fy
        th_ankle_L = -p.ankle_level_frac * (th_hip_L + knee_L)
        th_ankle_R = -p.ankle_level_frac * (th_hip_R + knee_R)
        hip_y = hips_y[i]

        # ---- vertical bob and lateral sway, both from the character's own geometry.
        # The hip rides the stance leg: it is highest when that leg is vertical.
        th_stance = th_hip_L if stance_L else th_hip_R
        hip_z = L * (math.cos(math.radians(th_stance)) - 1.0)
        hip_x = (p.sway_frac * performer.hip_half_separation * lx * amp
                 * math.sin(2.0 * math.pi * u_L))

        # ---- arms counter-swing the same-side leg, on that leg's own profile.
        th_sh_L = -p.arm_swing_deg * amp * fy * psi_L
        th_sh_R = -p.arm_swing_deg * amp * fy * psi_R
        # The elbow bends the forearm forward, so its sign is fy; the extra bend rides
        # the forward half of that arm's swing.
        el_L = fy * (p.elbow_base_deg + p.elbow_swing_deg * amp * max(0.0, -psi_L))
        el_R = fy * (p.elbow_base_deg + p.elbow_swing_deg * amp * max(0.0, -psi_R))

        # ---- torso counter-twist about Z. Sign derived, not guessed: the forward-going
        # shoulder must travel toward `fy`, and +Z carries the +X shoulder toward +Y.
        twist = p.chest_twist_deg * amp * -psi_L * lx * (-fy)

        pose = {b: {"rx": 0.0, "ry": 0.0, "rz": 0.0} for b in GAIT_BONES}
        pose["hips"].update(rz=-0.5 * twist)
        pose["hips"]["translation"] = [hip_x, hip_y, hip_z]
        pose["spine"]["rz"] = 0.35 * twist
        pose["chest"]["rz"] = 0.65 * twist
        pose["head"]["rz"] = -0.45 * twist
        pose["hip.L"]["rx"] = th_hip_L
        pose["hip.R"]["rx"] = th_hip_R
        pose["knee.L"]["rx"] = knee_L
        pose["knee.R"]["rx"] = knee_R
        pose["ankle.L"]["rx"] = th_ankle_L
        pose["ankle.R"]["rx"] = th_ankle_R
        pose["shoulder.L"]["rx"] = th_sh_L
        pose["shoulder.R"]["rx"] = th_sh_R
        pose["elbow.L"]["rx"] = el_L
        pose["elbow.R"]["rx"] = el_R

        # ---- the emote, layered on the (by now motionless) stance.
        if i >= f_gesture:
            t = (i - f_gesture + 1) / float(p.n_gesture)
            lift = smootherstep(min(1.0, t / 0.85))
            # Nod: down and back up to a settled slight tilt, inside the first 60% of
            # the gesture window so the hand and the head are not one simultaneous move.
            tn = (i - f_gesture + 1) / float(max(1, int(round(p.n_gesture * 0.60))))
            if tn <= 1.0:
                nod = p.nod_peak_deg * math.sin(math.pi * smootherstep(tn))
                nod += p.nod_settle_deg * smootherstep(tn)
            else:
                nod = p.nod_settle_deg
            # Positive about +X carries the head top toward +Y; chin-down is therefore
            # the direction the character faces.
            pose["head"]["rx"] += -fy * nod
            pose["neck"]["rx"] += -fy * nod * 0.25

            # The hail. Abduct (Y) then lift (X) — see `rotation_matrix`.
            # `-lx` is the character's RIGHT side, and outward for that arm is the
            # positive Y-rotation that carries a hanging limb toward -X.
            pose["shoulder.R"]["ry"] += lx * p.gesture_abduct_deg * lift
            pose["shoulder.R"]["rx"] += fy * p.gesture_lift_deg * lift
            pose["elbow.R"]["rx"] += fy * p.gesture_elbow_deg * lift
            pose["wrist.R"]["rx"] += fy * p.gesture_wrist_deg * lift

        frames.append({
            "frame": i,
            "scene_frame": 1 + i,
            "phase_rad": phi,
            "gait_speed": amp,
            "phase_name": ("walk" if i < f_decel else
                           "decelerate" if i < f_gesture else
                           "gesture" if i < f_hold else "hold"),
            "pose": pose,
        })

    step_distance = 2.0 * L * math.sin(math.radians(p.hip_swing_deg))
    return {
        "frames": frames,
        "omega_rad_per_frame": omega,
        "gait_speed": speed,
        "phase_rad": phase,
        "phase_boundaries": {"walk": [0, f_decel], "decelerate": [f_decel, f_gesture],
                             "gesture": [f_gesture, f_hold], "hold": [f_hold, n]},
        "derived": {
            "leg_length_measured": L,
            "step_distance_derived": step_distance,
            "total_forward_travel": abs(frames[-1]["pose"]["hips"]["translation"][1]),
            "forward_axis": "Y",
            "forward_sign": fy,
        },
        "params": p.as_dict(),
        "performer": performer.as_dict(),
    }


# ---------------------------------------------------------------- forward kinematics


def forward_kinematics(performer, gait):
    """World positions of every landmark at every frame, from the authored angles.

    This is the GROUND TRUTH — computed from what was authored, never read back from
    the render it exists to grade. `author_walk.py` cross-checks it against Blender's
    own evaluated pose matrices (Gate F) so the two cannot quietly disagree.

    The composition matches Blender's pose-bone semantics: a bone's delta is its
    parent's delta composed with a rotation about the bone's **rest** head, so a child's
    axes are carried by its parent's rotation exactly as `matrix_basis` does.
    """
    lm = performer.landmarks
    out = []
    for rec in gait["frames"]:
        pose = rec["pose"]
        deltas = {}
        for bone in GAIT_BONES:
            ch = pose[bone]
            R = rotation_matrix(ch["rx"], ch["ry"], ch["rz"])
            p0 = lm[HEAD_LANDMARK[bone]]
            # local delta: rotate about this bone's rest head
            t_local = [p0[k] - sum(R[k][j] * p0[j] for j in range(3)) for k in range(3)]
            trans = ch.get("translation")
            if trans:
                t_local = [t_local[k] + trans[k] for k in range(3)]
            parent = PARENT[bone]
            if parent is None:
                deltas[bone] = (R, t_local)
            else:
                Rp, tp = deltas[parent]
                deltas[bone] = (_mat_mul(Rp, R),
                                [sum(Rp[k][j] * t_local[j] for j in range(3)) + tp[k]
                                 for k in range(3)])

        def place(bone, landmark):
            R, t = deltas[bone]
            v = lm[landmark]
            return [_mat_vec(R, v)[k] + t[k] for k in range(3)]

        out.append({
            "frame": rec["frame"],
            "hips": place("hips", "crotch"),
            "head_top": place("head", "head_top"),
            "ankle_L": place("ankle.L", "ankle_L"),
            "ankle_R": place("ankle.R", "ankle_R"),
            "toe_L": place("ankle.L", "toe_L"),
            "toe_R": place("ankle.R", "toe_R"),
            "wrist_L": place("wrist.L", "wrist_L"),
            "wrist_R": place("wrist.R", "wrist_R"),
            "hand_end_L": place("wrist.L", "hand_end_L"),
            "hand_end_R": place("wrist.R", "hand_end_R"),
        })
    return out


def foot_slip(fk, ground_margin_frac=0.25):
    """How far each foot travels horizontally while it is the planted one.

    THE diagnostic for this tool, and it is defined so it can actually fail. Two
    readings, because the first needs a threshold and the second does not:

    **`slide_fraction_total`** — threshold-free, and the one to quote. At every frame at
    least one foot should be still, so sum the horizontal path of the *slower* foot over
    the shot and divide by the hips' own path. A planted walk reads ~0; a figure gliding
    with its feet painted on reads ~1. No ground plane, no contact test, no tuned constant
    anywhere in it, and dimensionless, so it does not care how big the character is.

    It is a **total**, not a per-frame maximum, and deliberately: the per-frame ratio is
    reported too, but its denominator goes to zero as the figure decelerates, so it reads
    1.0 on the settling frames where both the hips and the feet have all but stopped. A
    ratio whose denominator vanishes is not a measurement of sliding; quoting its maximum
    would be quoting an artefact of the stop.

    **The per-contact slip** — a foot counts as planted on frames where its toe sits in the
    lowest `ground_margin_frac` of that foot's OWN vertical range over the shot (its own
    range, never a typed-in floor: a global constant must not govern a local feature), and
    the reading is the toe's horizontal displacement between landing and lifting. It is the
    reading a person can check by eye against the preview, which is why it survives despite
    needing a threshold.

    Both gate nothing. The Director's eye on the preview is the judge; these say where to
    look.
    """
    report = {}
    speeds = []
    for a, b in zip(fk, fk[1:]):
        def h(name):
            return math.hypot(b[name][0] - a[name][0], b[name][1] - a[name][1])
        v_hips = h("hips")
        slower = min(h("toe_L"), h("toe_R"))
        speeds.append({
            "frame": a["frame"],
            "hips_speed": v_hips,
            "slower_foot_speed": slower,
            "slide_fraction": (slower / v_hips) if v_hips > 1e-9 else None,
        })
    moving = [s for s in speeds if s["slide_fraction"] is not None
              and s["hips_speed"] > 1e-6]
    foot_path = sum(s["slower_foot_speed"] for s in speeds)
    hips_path = sum(s["hips_speed"] for s in speeds)
    worst = max(moving, key=lambda s: s["slide_fraction"]) if moving else None
    report["slide"] = {
        "slide_fraction_total": (foot_path / hips_path) if hips_path > 1e-9 else 0.0,
        "slower_foot_path": foot_path,
        "hips_path": hips_path,
        "n_moving_frames": len(moving),
        "worst_frame": worst["frame"] if worst else None,
        "worst_frame_ratio": worst["slide_fraction"] if worst else None,
        "worst_frame_hips_speed": worst["hips_speed"] if worst else None,
        "worst_frame_slower_foot_speed": worst["slower_foot_speed"] if worst else None,
        "note": ("headline is slide_fraction_total = (path of the slower foot) / (path "
                 "of the hips) over the whole shot; 0 = a foot is always planted, 1 = "
                 "both feet glide with the body. The per-frame worst is reported WITH "
                 "its denominator because that denominator vanishes at the stop."),
    }
    for side in ("L", "R"):
        key = f"toe_{side}"
        zs = [f[key][2] for f in fk]
        lo, hi = min(zs), max(zs)
        span = hi - lo
        threshold = lo + ground_margin_frac * span if span > 0 else lo
        contacts, run = [], []
        for f in fk:
            if f[key][2] <= threshold:
                run.append(f)
            elif run:
                contacts.append(run)
                run = []
        if run:
            contacts.append(run)

        intervals = []
        for run in contacts:
            a, b = run[0][key], run[-1][key]
            dx, dy = b[0] - a[0], b[1] - a[1]
            intervals.append({
                "frames": [run[0]["frame"], run[-1]["frame"]],
                "n_frames": len(run),
                "horizontal_slip": math.sqrt(dx * dx + dy * dy),
                "slip_xy": [dx, dy],
            })
        report[side] = {
            "toe_z_range": [lo, hi],
            "contact_threshold_z": threshold,
            "n_contacts": len(intervals),
            "intervals": intervals,
            "max_slip": max((iv["horizontal_slip"] for iv in intervals), default=0.0),
        }
    report["max_slip_either_foot"] = max(report["L"]["max_slip"], report["R"]["max_slip"])
    return report
