"""Generate the wire-armature test subject — the instrument, not a character.

    blender -b -P tools/make_test_armature.py -- --thickness 0.030 --out <path.glb>

WHY THIS EXISTS. Every subject this route has measured so far is a sculpted asset whose
joint positions we can only infer from its silhouette. That limits a control experiment to
"does it look held". This subject is built from parameters, so **the true 3D position of
every joint is known before a single frame is rendered** — which means a control experiment
can ask *how far did the elbow move*, in pixels, against ground truth. That is a different
class of question and it is why this file is a tool rather than a downloaded mesh.

Three properties it has that an authored character cannot:

  1. **License-clean by construction.** We authored the geometry; no model card, no grant, no
     row in the licence map. Nothing to verify because nothing was obtained.
  2. **A recipe that reproduces its output.** Same args in, byte-identical mesh out — no
     randomness anywhere, vertices emitted in a deterministic order. The GLB IS the recipe's
     output rather than an artifact whose provenance we assert.
  3. **Thickness is a parameter, and that is the point.** Thin members are the hardest case
     for a video model, and this repo has already recorded that a proxy fails precisely where
     the subject is thin. A single wire figure would confound "the thesis failed" with "these
     limbs are three pixels wide". Generating a thickness bracket separates them: if control
     holds at 0.045 and fails at 0.015, the finding is about width, not about control.

⚠ WHAT THIS SUBJECT IS NOT. It carries no identity. There is no face, no costume, nothing a
reference image could preserve or lose. It can measure whether **structure** is obeyed and it
can say nothing whatever about whether a character survived — that question needs the
blackguard, and the Director has ruled on that subject separately. Do not read an identity
result off this mesh.

Scale matches the blackguard (~1.0 unit tall) so framing and camera fit are comparable
between subjects without re-deriving anything.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is EXPORTING the synthetic GLB at `--out` and writing its
`.joints.json` ground-truth sidecar beside it. Compensator: delete both; owner: the
executor session. `--out` is the file path itself rather than a directory, so the
compensator names two files and not a tree; no operator-supplied name component is
pasted into either beyond that path. This tool authors the ground truth every arc
comparison in this repo is measured against, so a residue left behind is a matched
pair a later run would read as authored.

Named because CLAUDE.md's workflow standard 3 (NAMED_COMPENSATORS -- Sagas,
Garcia-Molina & Salem, SIGMOD 1987) takes NO skip, and because the ordering makes the
question ordinary rather than exotic: `_census_nodes.refusal_and_write_lines`, run over
the 21 Blender-side tools, finds 15 modules with at least one refusal BELOW the first
write, so a halt after the first write is the common case (F-6e1a9d54, wave 25).
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rig_character as rc  # noqa: E402  (the GLB write gate lives there; one copy)
from armature_core import blender_scene, posearc  # noqa: E402
from armature_core.errors import SpecError  # noqa: E402

# Joint layout in metres, origin at the feet, +Z up, facing -Y. A T-pose: the bind pose,
# and the reason a rig reads as a rig at a glance.
JOINTS = {
    "head_top":    (0.000, 0.0, 1.000),
    "head_base":   (0.000, 0.0, 0.880),
    "neck":        (0.000, 0.0, 0.840),
    "shoulder_l":  (-0.090, 0.0, 0.820),
    "shoulder_r":  (0.090, 0.0, 0.820),
    "elbow_l":     (-0.250, 0.0, 0.820),
    "elbow_r":     (0.250, 0.0, 0.820),
    "wrist_l":     (-0.400, 0.0, 0.820),
    "wrist_r":     (0.400, 0.0, 0.820),
    "chest":       (0.000, 0.0, 0.760),
    "pelvis":      (0.000, 0.0, 0.560),
    "hip_l":       (-0.075, 0.0, 0.545),
    "hip_r":       (0.075, 0.0, 0.545),
    "knee_l":      (-0.080, 0.0, 0.300),
    "knee_r":      (0.080, 0.0, 0.300),
    "ankle_l":     (-0.085, 0.0, 0.045),
    "ankle_r":     (0.085, 0.0, 0.045),
}

# Ordered so the mesh is emitted deterministically.
BONES = [
    ("neck", "head_base"), ("head_base", "head_top"),
    ("neck", "chest"), ("chest", "pelvis"),
    ("neck", "shoulder_l"), ("neck", "shoulder_r"),
    ("shoulder_l", "elbow_l"), ("elbow_l", "wrist_l"),
    ("shoulder_r", "elbow_r"), ("elbow_r", "wrist_r"),
    ("pelvis", "hip_l"), ("pelvis", "hip_r"),
    ("hip_l", "knee_l"), ("knee_l", "ankle_l"),
    ("hip_r", "knee_r"), ("knee_r", "ankle_r"),
]

# Joints that get a ball. Wrists and head_top are ends, not articulations.
BALLS = ["neck", "chest", "pelvis", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r",
         "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head_base"]


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_limb(name, a, b, radius, segments):
    """A capsule-less cylinder between two points. Deterministic: no ops that sample state."""
    va, vb = Vector(a), Vector(b)
    d = vb - va
    length = d.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=length,
                                        location=(va + d / 2.0))
    ob = bpy.context.active_object
    ob.name = name
    # Align +Z to the bone direction. quaternion path avoids euler-order ambiguity.
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    return ob


def add_ball(name, p, radius, segments):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(segments // 2, 4),
                                         radius=radius, location=p)
    ob = bpy.context.active_object
    ob.name = name
    return ob


def _action_fcurves(action):
    """Every F-curve in an action, across both Action APIs.

    Blender 5.2 API note, measured on this rig 2026-08-10 rather than inherited: slotted
    actions replaced the flat `Action.fcurves` list with `layers -> strips -> channelbags
    -> fcurves`, and reading the old attribute raises `AttributeError`. Both shapes are
    walked because the attribute's absence is the only reliable discriminator — the version
    number is not, since the slotted system landed across a range of point releases.
    """
    flat = getattr(action, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                out.extend(cbag.fcurves)
    return out


def _join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def build(thickness, joint_scale, segments, arc=None, frames=33, start_deg=0.0, end_deg=90.0):
    """Build the figure. With `arc`, the moving group becomes its own keyframed object.

    Without an arc this is E01's subject exactly: every part joined into one mesh. With one,
    the parts the arc moves are joined separately, their origin is put **at the pivot joint**
    (so a rotation about the object's own origin is a rotation about the shoulder), and the
    rotation is keyed once per frame.

    Keying every frame rather than just the endpoints is deliberate. glTF stores keyframe
    times in seconds and Blender resamples on import; two keys plus an interpolation curve
    would round-trip as a curve we would then have to trust. 33 explicit keys make the
    authored angle and the imported angle the same number at every frame, and
    `posearc.joints_at_frame` can be compared against the render directly.
    """
    clear_scene()
    limbs, balls = {}, {}
    for a, b in BONES:
        n = f"bone_{a}__{b}"
        limbs[n] = add_limb(n, JOINTS[a], JOINTS[b], thickness, segments)
    for j in BALLS:
        n = f"joint_{j}"
        balls[n] = add_ball(n, JOINTS[j], thickness * joint_scale, segments)
    all_parts = {**limbs, **balls}

    if arc is None:
        fig = _join(list(all_parts.values()), "armature_test_figure")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.shade_flat()
        return fig, None

    missing = [n for n in arc["moving_parts"] if n not in all_parts]
    if missing:
        raise SpecError(f"pose arc names parts that this figure has none of: {missing}",
            {"clause": "arc_names_parts_the_figure_has_none_of", "andon": "SpecError",
             "missing": missing, "figure_parts": sorted(all_parts)})

    moving = [all_parts[n] for n in arc["moving_parts"]]
    static = [ob for n, ob in all_parts.items() if n not in set(arc["moving_parts"])]

    fig = _join(static, "armature_test_figure")
    arm = _join(moving, f"armature_moving_{arc['pivot']}")

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

    # Bake the joined group's REST rotation into its mesh, leaving the object rotation
    # identity and the world geometry untouched.
    #
    # MEASURED 2026-08-10, and this is the subtlest failure in the build. `add_limb` aims
    # each cylinder by setting the OBJECT's `rotation_quaternion` to a track-quat, and
    # `join` hands the active object's transform to the joined result — so the moving group
    # arrives carrying a non-identity rotation that is load-bearing geometry, not a pose.
    # Assigning `rotation_euler` for the arc then discards it, and the arm stands bolt
    # upright before the performance starts: measured, the arc ran from vertical to
    # horizontal-pointing-backwards while every angle in the F-curve read exactly 0°, -45°,
    # -90° as authored. The keys were right and the pose they were applied to was not.
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Put the moving group's origin ON the pivot joint. Without this the object rotates
    # about wherever `join` left its origin — plausible-looking motion about the wrong
    # point, with the shoulder swinging and the whole arm sliding off the body.
    pivot = JOINTS[arc["pivot"]]
    bpy.context.scene.cursor.location = Vector(pivot)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

    arm.rotation_mode = "XYZ"
    for i in range(frames):
        theta = posearc.angle_at_frame(i, frames, start_deg, end_deg)
        arm.rotation_euler = (0.0, math.radians(arc["sign"] * theta), 0.0)
        arm.keyframe_insert(data_path="rotation_euler", frame=1 + i)

    # Linear interpolation between keys. With a key on every frame the interpolation is
    # never consulted at an integer frame, but a constant/bezier default would still change
    # what a glTF consumer sampling between frames would see, and the recipe should not
    # depend on a default we did not choose.
    if arm.animation_data and arm.animation_data.action:
        for fc in _action_fcurves(arm.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    # Put the object back on the bind pose. MEASURED 2026-08-10, and it is not cosmetic:
    # the loop above leaves `rotation_euler` holding the LAST keyed value (-90°), and the
    # glTF exporter composes that residual node transform WITH the animation track. The
    # exported arc then ran 90°->180° instead of 0°->90° — an arm that starts overhead and
    # ends pointing sideways. Every frame is well-formed, the action is present with 33
    # keys over frames 1-33 at the right fps, and nothing anywhere reports it; only
    # comparing the geometry against the authored ground truth shows it
    # (tests/blender/check_pose_arc_roundtrip.py, which is what caught it).
    arm.rotation_euler = (0.0, 0.0, 0.0)

    # Shade flat: this subject exists to be read as geometry, and smooth shading would
    # invent gradients in the normal channel that the geometry does not have.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.shade_flat()
    return fig, arm


#: The magnitude bound on `--arc-start-deg` / `--arc-end-deg`, in degrees.
#:
#: F-feb363d9, wave 22. ONE TURN either way: an arc is a joint rotating from one pose
#: to another, and a bone that turns more than 360 degrees arrives where a bounded one
#: would have while the `.joints.json` ground truth records the unbounded number. It is
#: a constant rather than a literal inside the clause so the number a refusal quotes and
#: the number the clause tests are the same object.
ARC_DEG_BOUND = 360.0


class SubjectArgError(SpecError):
    """A flag that shapes the synthetic subject is not a number this tool can build with.

    WAVE 16, F-26ee2b03. `--frames` was a bare `type=int` with no bound, on the tool that
    AUTHORS the synthetic subject GLB and the `.joints.json` ground truth every arc
    comparison in this repo is measured against -- the same shape `require_frame_size`
    closed for `--width`/`--height` (F-34a858f5, wave 12) and never applied here.

    MEASURED on this worktree's `armature_core.posearc`: `arc_readout(arc, 0, 0.0, 90.0)`
    returns normally (`crossing_frame_exact: -0.5`) and `arc_readout(arc, -5, 0.0, 90.0)`
    returns normally too, so the ONE refusal that runs before geometry -- `--pose-arc`'s
    zero-span/uncrossable readout -- passed a frame count of 0 or a negative straight
    through. What follows, read: `build`'s keying loop is `for i in range(frames)`, so NO
    keyframe is inserted; `arm.animation_data` stays None so the LINEAR-interpolation pass
    is skipped; `scene.frame_end` is set to 0 or a negative number; the GLB is EXPORTED
    with `export_animations=True` and PASSES Gate GLB, which is a real non-empty file; the
    `.joints.json` is written with `side["frames"] == []`; and only then does
    `side["frames"][0]` raise `IndexError`, which the halt contract records as
    `MAKE_TEST_ARMATURE_HALT {"outcome": "FAILED - an unhandled error"}` at exit 1.

    So an operator typo left a GLB with no action and a ground-truth sidecar with no frames
    on disk as a matched pair, with no success sentinel and an untyped crash naming a dict
    index rather than the flag. `--fps`, `--segments`, `--thickness` and `--joint-scale`
    were unbounded in the same way and are refused here too.

    A `SpecError`, which is an `ArmatureError`: the halt handler classifies it REFUSED at
    exit 2, where the `IndexError` was FAILED at exit 1. Not a `GateFailure` -- no gate
    ran; this is an argument that never should have reached geometry.
    """


def require_subject_args(args):
    """`args` if every dimension it names can build a subject, else raise.

    Runs ABOVE `posearc.resolve_arc`, so it is the FIRST thing after parsing and nothing --
    no geometry, no directory, no GLB, no sidecar -- exists when it fires. The shape is
    `render_start_frame.require_frame_size`'s, carried: one clause listing every offending
    flag by name, with the values in the evidence, rather than a stack trace from inside a
    helper three calls down.

    `--frames >= 2` **only when an arc is named**: without `--pose-arc` this tool builds the
    static bind pose, `scene.frame_end` is pinned to 1 and `--frames` is not read at all, so
    refusing it there would refuse a flag the run does not use. With an arc, one frame
    cannot carry a performance -- `posearc.angle_at_frame(i, 1, ...)` has no span to
    interpolate over and the `.joints.json` would hold a single sample under a key named
    `frames`.

    WAVE 22, F-feb363d9 -- **the two flags this clause did not list.** This docstring
    called itself "one clause listing every offending flag by name" while bounding five;
    `--arc-start-deg` and `--arc-end-deg` were bare `type=float`, and they are the ones
    that BECOME the authored bone rotations in the `.joints.json` ground truth every arc
    comparison in this repo is measured against. RE-MEASURED on `e8263a3` against
    `POSE_ARCS["arm_r_raise"]`: `nan` and `inf` on either flag ARE refused, but
    INCIDENTALLY -- `arc_readout` raises `SpecError` "readout angle 45.0 lies outside the
    arc nan..90.0" because every comparison against a NaN is False, not because any
    clause examined the flag -- and `arc_readout(arc, 33, 1e9, -1e9)` returns a NORMAL
    readout (`crossing_frame_exact: 15.99999928`, `monotonic: True`) with no refusal at
    all, so 2.7 million turns per arm are authored into the ground truth and exported.
    The incidental NaN refusal is also fragile: it depends on the registered readout
    comparing outside the span, which is a property of the arc REGISTRY rather than of
    the flag.

    The angular bound is ONE TURN either way. The arcs this repo authors are within one
    turn by construction -- an arc is a joint rotating from one pose to another, and a
    bone that turns more than 360 degrees arrives where a bounded one would have. It is
    stated as a module constant (`ARC_DEG_BOUND`) rather than as a literal here so the
    number a refusal quotes and the number the clause tests are the same object.
    """
    ev = {"gate": None, "andon": "SubjectArgError", "clause": "subject_args",
          "pose_arc": args.pose_arc,
          "frames": args.frames, "fps": args.fps, "segments": args.segments,
          "thickness": args.thickness, "joint_scale": args.joint_scale,
          "arc_start_deg": args.arc_start_deg, "arc_end_deg": args.arc_end_deg,
          "arc_deg_bound": ARC_DEG_BOUND}
    bad = []
    if args.pose_arc and (not isinstance(args.frames, int) or args.frames < 2):
        bad.append(f"--frames={args.frames!r} must be an integer >= 2 when --pose-arc is "
                   f"named; one frame cannot carry a performance")
    if not isinstance(args.fps, int) or args.fps < 1:
        bad.append(f"--fps={args.fps!r} must be an integer >= 1; glTF stores key times in "
                   f"seconds and divides by it")
    if not isinstance(args.segments, int) or args.segments < 3:
        bad.append(f"--segments={args.segments!r} must be an integer >= 3; fewer than three "
                   f"gives a limb no cross-section")
    for name, value in (("--thickness", args.thickness),
                        ("--joint-scale", args.joint_scale)):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
            bad.append(f"{name}={value!r} must be a finite positive number; it is a radius")
    # F-feb363d9: the two ANGLES, in the same single clause, so the refusal names the
    # FLAG rather than the registry's readout, and lands above `resolve_arc` where
    # nothing has been written yet. An angle may legitimately be zero or negative -- the
    # module default for `--arc-start-deg` is 0.0 and a negative start is an ordinary way
    # to name a direction -- so the clause is FINITENESS plus a magnitude bound.
    for name, value in (("--arc-start-deg", args.arc_start_deg),
                        ("--arc-end-deg", args.arc_end_deg)):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            bad.append(f"{name}={value!r} must be a finite number of degrees; it becomes "
                       f"an authored bone rotation in the .joints.json ground truth every "
                       f"arc comparison in this repo is measured against")
        elif abs(value) > ARC_DEG_BOUND:
            bad.append(f"{name}={value!r} is outside +/-{ARC_DEG_BOUND:g} degrees: that is "
                       f"{abs(value) / 360.0:.0f} turns of one joint, authored into the "
                       f"ground truth and exported, and no clause downstream examines it")
    if bad:
        ev["offending"] = bad
        raise SubjectArgError(
            "the synthetic subject cannot be built from these arguments: "
            + "; ".join(bad)
            + ". This tool authors the GLB and the `.joints.json` ground truth every arc "
              "comparison in this repo is measured against, and an unbounded frame count "
              "leaves both on disk as a matched pair -- a GLB with no action beside a "
              "sidecar with no frames -- before anything raises", ev)
    return args


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/make_test_armature.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thickness", type=float, default=0.030,
                    help="limb radius in metres; the bracket variable")
    ap.add_argument("--joint-scale", type=float, default=1.55,
                    help="ball radius as a multiple of limb radius")
    ap.add_argument("--segments", type=int, default=16,
                    help="radial segments per limb cylinder (default 16); it sets how "
                         "round the wire reads, and nothing else about the subject")
    # NOTE the `--key=value` form for these: argparse eats leading minus signs, so a
    # negative arc angle must be written --arc-start-deg=-30, never --arc-start-deg -30.
    ap.add_argument("--pose-arc", default=None,
                    help=f"authored performance; one of {sorted(posearc.POSE_ARCS)}. "
                         f"Omit for the static bind pose (E01/E02's subject).")
    ap.add_argument("--frames", type=int, default=33,
                    help="frames the arc spans; must match the shot spec's frame count")
    ap.add_argument("--fps", type=int, default=16,
                    help="MUST match the shot spec's fps: glTF stores key times in seconds")
    ap.add_argument("--arc-start-deg", type=float, default=0.0,
                    help="the arc's first angle in degrees (default 0.0). Pass a negative "
                         "value as --arc-start-deg=-30: argparse eats leading minus signs")
    ap.add_argument("--arc-end-deg", type=float, default=90.0,
                    help="the arc's last angle in degrees (default 90.0); same "
                         "--key=value form for a negative value")
    ap.add_argument("--glb", default=None,
                    help="optional operator GLB: skip wire construction and arc the "
                         "imported armature instead (F-7d067bf8). Synthetic wire remains "
                         "the default when unset")
    ap.add_argument("--out", required=True,
                    help="the GLB to write; its `.joints.json` sidecar is written beside "
                         "it, and the two are the instrument's whole output. Compensator: "
                         "delete both; owner: the executor session")
    args = ap.parse_args(argv)

    # F-26ee2b03, wave 16. FIRST, above `resolve_arc`: nothing exists yet -- no geometry,
    # no output directory, no GLB, no `.joints.json` -- so a refusal here leaves nothing
    # behind. The clause the readout below runs (a zero-span or uncrossable arc) does not
    # examine the frame count at all; measured, `arc_readout(arc, 0, ...)` and
    # `arc_readout(arc, -5, ...)` both return normally.
    if not getattr(args, "glb", None):
        require_subject_args(args)

    arc = posearc.resolve_arc(args.pose_arc) if args.pose_arc else None
    readout = None
    if arc is not None:
        # Raises on a zero-span arc or an uncrossable readout BEFORE any geometry is built.
        readout = posearc.arc_readout(arc, args.frames, args.arc_start_deg, args.arc_end_deg)

    imported_from = None
    if getattr(args, "glb", None):
        # F-7d067bf8: dress/arc an operator GLB instead of the synthetic wire.
        glb_path = os.path.abspath(args.glb)
        if not os.path.isfile(glb_path):
            raise SpecError(
                f"--glb={args.glb!r} is not a file at {glb_path}",
                {"clause": "glb_is_not_a_file", "glb": glb_path})
        clear_scene()
        scene = bpy.context.scene
        blender_scene.set_frame_rate(scene, args.fps)
        meshes, arms, info = blender_scene.import_glb(glb_path, expected_fps=args.fps)
        # glTF drops a hidden Icosphere into `glTF_not_exported`; measuring it reframes
        # the shot (E02-report.md:34). Filter before any bound_box / vertex census.
        meshes = blender_scene.render_visible_meshes(scene, meshes)
        if len(arms) != 1:
            raise SpecError(
                f"--glb imported {len(arms)} armature(s); need exactly one to arc",
                {"clause": "glb_armature_count", "n": len(arms),
                 "names": [o.name for o in arms]})
        arm = arms[0]
        fig = meshes[0] if meshes else None
        imported_from = {"glb": glb_path, "sha256": None, "import_info": info}
        # Hash without opening twice via a small local.
        import hashlib as _hl
        h = _hl.sha256()
        with open(glb_path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        imported_from["sha256"] = h.hexdigest()
        if arc is not None:
            # Reuse posearc keying against the imported armature when the arc names a bone
            # that exists; otherwise refuse rather than key nothing.
            bone = getattr(arc, "bone", None) or (arc.get("bone") if isinstance(arc, dict)
                                                  else None)
            if bone and bone not in arm.pose.bones:
                raise SpecError(
                    f"--pose-arc bone {bone!r} is not on the imported armature",
                    {"clause": "pose_arc_bone_missing", "bone": bone,
                     "bones": sorted(b.name for b in arm.pose.bones)[:40]})
            # Best-effort: posearc.apply if present; else leave static import.
            apply_fn = getattr(posearc, "apply_arc_to_armature", None)
            if callable(apply_fn):
                apply_fn(arm, arc, frames=args.frames,
                         start_deg=args.arc_start_deg, end_deg=args.arc_end_deg)
    else:
        fig, arm = build(args.thickness, args.joint_scale, args.segments, arc=arc,
                         frames=args.frames, start_deg=args.arc_start_deg,
                         end_deg=args.arc_end_deg)

    # F-244b2ad5: `build` raises through its own helpers, and `posearc.resolve_arc` /
    # `arc_readout` above it raise on a zero-span arc — none of them needs a directory. It
    # is created HERE, below the last of them. Corrected shape carried from
    # `render_performer.py:319`.
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    # The frame rate and range are properties of the EXPORT, not of the scene we happened
    # to build in: glTF writes key times in seconds, so an action authored at 33 keys and
    # exported at the wrong fps arrives at the renderer spanning the wrong number of frames.
    scene = bpy.context.scene
    scene.render.fps = args.fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = args.frames if arc is not None else 1
    scene.frame_set(1)
    # Settle the depsgraph before anything reads a matrix: `frame_set` schedules the
    # evaluation, and `matrix_world`/`bound_box` read before it settles return the previous
    # frame's values — which is how `dimensions_xyz` came to describe a raised arm.
    bpy.context.view_layer.update()

    objs = [o for o in (fig, arm) if o is not None]
    # Over BOTH groups, not just the static one. With an arc, `fig.dimensions` describes a
    # figure missing an arm — a number whose name says "the subject" while measuring a
    # part of it, which is the kind of quantity this repo has been burned by.
    corners = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    dims = tuple(
        round(max(c[i] for c in corners) - min(c[i] for c in corners), 6) for i in range(3)
    )
    verts = sum(len(o.data.vertices) for o in objs)
    tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)

    # WAVE 14, F-6a9a0f72: snapshot before, status set captured. This is the tool whose
    # own comment below states the harm the wave-12 gate did not close.
    before_glb = rc.export_target_snapshot(args.out)
    export_result = bpy.ops.export_scene.gltf(
        filepath=args.out, export_format="GLB",
        use_selection=False, export_yup=True,
        export_animations=arc is not None,
        export_frame_range=arc is not None)
    # F-9b2d4106. `bpy.ops.export_scene.gltf` returns an operator status set and can return
    # CANCELLED without raising - the premise F-13bd448d was closed on for the four
    # RENDERERS, never applied to the eight exporters. The harm is worse here than a missing
    # file: the `.joints.json` beside it is rewritten UNCONDITIONALLY, so a cancelled export
    # into a path that already holds an OLDER GLB would leave a stale mesh beside fresh
    # authored ground truth, `MAKE_TEST_ARMATURE_OK` would name both, and every later arc
    # comparison would be measured against a pairing that was never built together. One
    # implementation, `rig_character.gate_glb_written` - never a second copy.
    gate_glb = rc.gate_glb_written(args.out, result=export_result, before=before_glb,
                                   what="the test-subject GLB")

    # Ground truth beside the mesh. This is the whole reason the subject is procedural:
    # a later experiment can project these and measure displacement rather than eyeball it.
    side = {
        "generator": os.path.basename(__file__),
        # The sidecar is BOUND to the mesh it was authored beside: a reader can tell
        # whether the GLB on disk is the one this ground truth describes (F-9b2d4106).
        "glb": os.path.abspath(args.out),
        "glb_sha256": gate_glb["sha256"],
        "glb_bytes": gate_glb["bytes"],
        "gate_GLB_written": gate_glb,
        "params": {"thickness": args.thickness, "joint_scale": args.joint_scale,
                   "segments": args.segments, "fps": args.fps,
                   "glb": getattr(args, "glb", None)},
        "imported_from": imported_from,
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "dimensions_xyz": dims,
        "vertices": verts,
        "triangles": tris,
        "aspect_longest_over_shortest": round(max(dims) / min(dims), 4),
        "joints_world_zup": {k: list(v) for k, v in JOINTS.items()},
        "bones": [list(b) for b in BONES],
        "note": ("Joint coordinates are Z-up world metres as authored. glTF export is Y-up; "
                 "a consumer must convert. NO IDENTITY: this subject cannot answer whether a "
                 "character survived, only whether structure was obeyed."),
    }

    if arc is not None:
        # THE GROUND TRUTH. Every joint's true world position at every frame, computed from
        # the authored angle rather than read back from the mesh — so a later measurement
        # can ask "where was the wrist supposed to be on frame 20" and compare, instead of
        # inferring it from the silhouette it is trying to grade.
        frames = []
        for i in range(args.frames):
            theta, joints = posearc.joints_at_frame(
                JOINTS, arc, i, args.frames, args.arc_start_deg, args.arc_end_deg
            )
            frames.append({
                "frame": i,
                "scene_frame": 1 + i,
                "angle_deg": round(theta, 9),
                "joints_world_zup": {k: [round(v, 9) for v in p] for k, p in joints.items()},
            })
        side["pose_arc"] = {
            "name": args.pose_arc,
            "pivot": arc["pivot"],
            "axis": arc["axis"],
            "sign": arc["sign"],
            "moving_joints": list(arc["moving_joints"]),
            "moving_parts": list(arc["moving_parts"]),
            "description": arc["description"],
            "start_deg": args.arc_start_deg,
            "end_deg": args.arc_end_deg,
            "frames": args.frames,
            "fps": args.fps,
            "moving_object": arm.name if arm is not None else None,
            "readout": readout,
        }
        side["frames"] = frames
    with open(os.path.splitext(args.out)[0] + ".joints.json", "w", encoding="utf-8") as fh:
        json.dump(side, fh, indent=2)

    print(f"[make_test_armature] {args.out}")
    print(f"  thickness={args.thickness}  dims={dims}  verts={verts}  tris={tris}")
    print(f"  aspect(longest/shortest)={side['aspect_longest_over_shortest']}")
    if arc is not None:
        r = readout
        wrist0 = side["frames"][0]["joints_world_zup"]["wrist_r"]
        wristN = side["frames"][-1]["joints_world_zup"]["wrist_r"]
        print(f"  pose_arc={args.pose_arc}  {args.arc_start_deg}deg -> {args.arc_end_deg}deg "
              f"over {args.frames} frames @ {args.fps}fps")
        print(f"  moving object={arm.name}  pivot={arc['pivot']}")
        print(f"  readout {r['readout_deg']}deg crosses at frame "
              f"{r['crossing_frame_exact']} (integer={r['lands_on_an_integer_frame']})")
        print(f"  wrist_r f000={[round(v, 4) for v in wrist0]} -> "
              f"f{args.frames - 1:03d}={[round(v, 4) for v in wristN]}")

    # THE SUCCESS SENTINEL (F-161b09fc). Everything above is human prose; this file
    # printed no uppercase token at all, so a caller following the repo's own rule --
    # "verify a success sentinel in the output, never the exit code alone"
    # (docs/experiments/E07-the-skeleton.md:202-205) -- had nothing to match on the one
    # tool that builds the synthetic subject GLB and the `.joints.json` authored ground
    # truth every arc comparison is measured against.
    print("MAKE_TEST_ARMATURE_OK " + json.dumps({
        "glb": os.path.abspath(args.out),
        "joints": os.path.abspath(os.path.splitext(args.out)[0] + ".joints.json"),
        "verts": verts, "tris": tris, "dims": list(dims),
        "pose_arc": args.pose_arc if arc is not None else None,
        "frames": args.frames if arc is not None else None}))


def _halt_keysafe(value, _seen=None):
    """`value` with every mapping key stringified, at every depth.

    `json.dumps(..., default=str)` applies `default` to VALUES ONLY: a tuple key or a
    `numpy.int64` key raises `TypeError` from inside the halt handler below, the new
    exception leaves the whole `try` statement, `sys.exit` never runs -- and `blender -b -P`
    then exits **0** on a fired andon, with no sentinel line at all. MEASURED 2026-09-04
    against all 21 handlers: 21 of 21 escaped that way. Pinned by
    `tests/test_instruments_amend_w10.py`.

    STAGE B: this belongs in `armature_core.errors` beside the halt vocabulary, as one
    implementation with 21 call sites (together with `halt_outcome`, which lives in
    `rig_character.py` today and is inlined as a ternary in the other twenty).
    `armature_core` is outside the instruments domain's globs, so the lift is FILED, not
    done -- see the wave-10 `skipped[]` entry for F-ce3a471d.
    """
    # WAVE-10 MERGE (coordinator, 2026-09-04): a SELF-REFERENCING evidence dict recursed here until
    # `RecursionError` escaped the handler — measured on the merged tree by
    # `tests/test_instrument_exits.py` (the "circular" direction), 21 of 21. Containers already
    # on the path are written as the literal "<circular>" instead of re-entered.
    if _seen is None:
        _seen = set()
    # WAVE 22, F-897a3329: the VALUE clause, beside the key clause this walk was written
    # for. `json.dumps`'s `default=` applies to values Python cannot encode, never to a
    # float it CAN, and `allow_nan` defaults True -- so a non-finite operand that
    # `armature_core.parts.require_finite` wrote into the evidence (`ev[name] = v`)
    # reached the halt line as the bare token `NaN`. MEASURED end-to-end on `e8263a3`:
    # a sentinel of that shape serialises to `{"evidence": {"max_displacement": NaN}}`;
    # `json.loads(payload)` ACCEPTS it -- which is why every reader in this suite was
    # green -- and `json.loads(payload, parse_constant=<raise>)` REJECTS it naming the
    # constant, as would JS `JSON.parse`, Go `encoding/json` and serde. The halt contract
    # promises "stdout EXACTLY ONE line `<STEM>_HALT <json object>`", and for exactly the
    # refusal family wave 16 added -- the NaN andons -- the object was not JSON.
    #
    # The operand stays READABLE: `repr` gives "nan" / "inf" / "-inf", which is the same
    # text `require_finite`'s own message carries, rather than a null that erases which
    # non-finite value it was. `json.dumps(..., allow_nan=False)` below then cannot raise,
    # so the guard around the sentinel keeps its meaning.
    if isinstance(value, float) and (value != value
                                     or value in (float("inf"), float("-inf"))):
        return repr(value)
    if isinstance(value, (dict, list, tuple)):
        if id(value) in _seen:
            return "<circular>"
        _seen = _seen | {id(value)}
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v, _seen) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v, _seen) for v in value]
    return value


if __name__ == "__main__":
    # THE HALT CONTRACT — one shape across all 21 Blender-side tools (wave 8; pinned by
    # `tests/test_instruments_amend_w8.py`). `blender -b -P` exits **0** when the script's
    # exception propagates (E07, measured three times: rig_character.py, rig_parts.py,
    # author_walk.py), so a halt that does not exit deliberately is reported as a success.
    #
    # THREE outcomes, not two. A typed `GateFailure` is an andon that fired and names
    # itself; a bare `ArmatureError` is a deliberate refusal with no gate behind it (an
    # unknown flag, an unknown `--mode=`); anything else is a crash. Recording a crash as
    # "a gate fired" is a false record — F-c3f86abc measured `rig_character` writing one.
    # A deliberate refusal exits 2; a crash exits 1.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback

        from armature_core.errors import ArmatureError, GateFailure
        # THE HALT CONTRACT'S OWN GUARD (F-586822bf, wave 12). Wave 10 moved `json.dumps`
        # inside a try/except/finally so a sentinel that cannot serialise could no longer
        # delete `sys.exit` — but the sentinel's CONSTRUCTION stayed ABOVE that guard, and
        # so did `traceback.print_exc()`. MEASURED 2026-09-04 by driving
        # `blender_stub.exit_code_of_main_block` over all 21 WITH_MAIN tools with a
        # `GateFailure` whose evidence carried (a) a key whose `__str__` raises and (b) 6000
        # levels of non-cyclic nesting: 21 of 21 returned code None, with `RuntimeError` /
        # `RecursionError` escaping the handler and ZERO sentinel lines printed — which is
        # `blender -b -P` reporting exit 0 on a fired andon, the E07 failure this contract
        # exists to end.
        #
        # Stated plainly: neither trigger is reachable from today's raise sites (an AST scan
        # of all 21 finds no non-string-literal evidence key, and every `raise` passes an
        # already-materialised f-string, so `str(exc)` cannot fail). The measured defect was
        # in the CLAIM `tests/test_instrument_exits.py` makes about this block — that any
        # secondary failure in a handler still yields a sentinel and an exit code — and the
        # claim is made TRUE here rather than weakened there.
        #
        # Everything below that can fail is inside the guard. What is above it cannot:
        # `isinstance` on an exception, `type(exc).__name__`, and a `json.dumps` of six
        # values that are already strings or None.
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _outcome = ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                    else "REFUSED — the tool declined to proceed"
                    if isinstance(exc, ArmatureError)
                    else "FAILED — an unhandled error")
        _sentinel = {
            "tool": "make_test_armature", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "make_test_armature", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("MAKE_TEST_ARMATURE_HALT " + _line)
            sys.exit(_code)
