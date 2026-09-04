"""Does an authored performance survive the glTF round trip? Run inside Blender.

    blender -b -P tests/blender/check_pose_arc_roundtrip.py -- <subject.glb> [--fps N]

**This is the check E03 cannot proceed without**, and it is separated from the render
because it is fast, free, and answers the one question that would otherwise be answered by
33 rendered frames and a fired G6. The round trip has three places to lose an action:

  1. the exporter may not write object-level TRS animation at all;
  2. glTF stores key times in **seconds**, so an export at one fps read back at another
     lands the keys on different frames — the arc arrives compressed or stretched, and
     nothing errors;
  3. the importer may create the action but leave it unassigned, in which case
     `frame_set` moves the timeline and the geometry does not follow.

All three produce a well-formed GLB. Only the evaluated world position of the moving
geometry distinguishes them, which is what this measures — against the authored ground
truth in the `.joints.json` sidecar, not against itself.

**Mode 2 is not covered by G6.** G6's quantity is `distinct_signatures`
(`tools/stage_render.py:421`), and a compressed or stretched arc still yields one distinct
signature per frame, so G6 reads PASS on a performance that arrives time-warped. This file
is the only instrument that can say so.

--------------------------------------------------------------------------------
THE CONTRACT IS THE PRINTED RECORD, NOT THE EXIT CODE.

This used to be designed as a shell-chain exit code, which CLAUDE.md forbids by name — a
chain can walk past a failing exit code, and for three months nothing ran this file at
all: every sibling under `tests/blender/` had a `test_*.py` wrapper and this one did not.
It now prints one line, `POSE_ARC <json>`, carrying every measurement it made, and
`tests/test_pose_arc_roundtrip.py` asserts on that record. The exit code is kept for a
human running it by hand; it is not what anything checks.

`--fps N` reads the file back at N instead of the rate the sidecar authored, which is how
the wrapper drives failure mode 2 on purpose. A check that cannot be made to fire is not
a check.

No `assert` anywhere below: this file is a helper, pytest does not rewrite it, and it runs
inside Blender's own interpreter where nothing rewrites anything at all.
"""

import json
import os
import sys

import bpy
import numpy as np

TOL = 1e-4  # metres. Round-trip error is float32 in the buffer; 0.1 mm is generous.
MARKER = "POSE_ARC "


def evaluated_vertices(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    chunks = []
    for ob in objects:
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        if me is None or not len(me.vertices):
            ev.to_mesh_clear()
            continue
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        M = np.array(ev.matrix_world, dtype=np.float64)
        chunks.append(co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
        ev.to_mesh_clear()
    return np.concatenate(chunks, axis=0) if chunks else np.zeros((0, 3))


def emit(record):
    """One line, machine-readable, whatever happened. The wrapper reads this."""
    print(MARKER + json.dumps(record))
    return 0 if record.get("verdict") == "OK" else 1


def parse_argv(argv):
    """`(glb, fps_override)` — `--fps=N` and `--fps N` both, or a named refusal."""
    if not argv:
        return None, None, "need a path to a .glb"
    glb, fps = argv[0], None
    rest = argv[1:]
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok.startswith("--fps="):
            fps = tok.split("=", 1)[1]
        elif tok == "--fps" and i + 1 < len(rest):
            i += 1
            fps = rest[i]
        else:
            return None, None, f"unknown argument {tok!r}"
        i += 1
    if fps is not None:
        try:
            fps = int(fps)
        except ValueError:
            return None, None, f"--fps must be an integer, got {fps!r}"
        if fps < 1:
            return None, None, f"--fps must be positive, got {fps}"
    return glb, fps, None


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    glb, fps_override, bad = parse_argv(argv)
    if bad:
        return emit({"verdict": "BAD_ARGS", "reason": bad})

    sidecar = os.path.splitext(glb)[0] + ".joints.json"
    if not os.path.isfile(sidecar):
        return emit({"verdict": "NO_SIDECAR", "reason": f"no sidecar at {sidecar}",
                     "glb": glb})
    with open(sidecar, encoding="utf-8") as fh:
        side = json.load(fh)

    arc = side.get("pose_arc")
    if not arc:
        return emit({"verdict": "NO_ARC", "glb": glb,
                     "reason": "the sidecar carries no pose_arc; this asset has no "
                               "performance"})
    count, fps_authored = arc["frames"], arc["fps"]
    fps_used = fps_authored if fps_override is None else fps_override

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Set fps BEFORE importing: the importer maps key times in seconds onto frames using
    # the scene's rate, and this is failure mode 2 above.
    scene.render.fps = fps_used
    scene.render.fps_base = 1.0
    bpy.ops.import_scene.gltf(filepath=glb)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    record = {
        "glb": glb,
        "frames": count,
        "fps_authored": fps_authored,
        "fps_used": fps_used,
        "fps_matches_authored": fps_used == fps_authored,
        "mesh_objects": len(meshes),
        "actions": len(bpy.data.actions),
        "tol_m": TOL,
        "limb_radius_m": side["params"]["thickness"],
    }

    if record["actions"] == 0:
        record["verdict"] = "NO_ACTION"
        record["reason"] = ("no action survived the export/import; the arc is gone "
                            "(failure mode 1)")
        return emit(record)

    # glTF export is Y-up; the sidecar's ground truth is authored Z-up. Convert the truth
    # into the imported frame rather than the other way round, so what is compared is what
    # the renderer will actually evaluate.
    def zup_to_import(p):
        return np.array([p[0], p[1], p[2]], dtype=np.float64)

    worst = 0.0
    rows = []
    for i in (0, count // 2, count - 1):
        scene.frame_set(1 + i)
        bpy.context.view_layer.update()
        pts = evaluated_vertices(meshes)
        truth = zup_to_import(side["frames"][i]["joints_world_zup"]["wrist_r"])
        # The wrist is a bone END, not a ball, so no vertex sits exactly on it. Compare
        # against the nearest vertex: if the arm is where it should be, some geometry is
        # within a limb radius of the authored wrist. If the arc did not survive, the
        # nearest vertex stays at the T-pose position and the distance blows up.
        d = float(np.linalg.norm(pts - truth, axis=1).min())
        rows.append({"frame": i, "angle_deg": side["frames"][i]["angle_deg"],
                     "authored_wrist": [round(v, 6) for v in truth.tolist()],
                     "nearest_vertex_m": d})
        worst = max(worst, d)
    record["rows"] = rows
    record["worst_gap_m"] = worst

    # The arc must MOVE: frame 0 and the last frame must not evaluate identically.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    first = evaluated_vertices(meshes)
    scene.frame_set(count)
    bpy.context.view_layer.update()
    last = evaluated_vertices(meshes)
    record["displacement_m"] = float(np.abs(first - last).max())

    if record["displacement_m"] < TOL:
        record["verdict"] = "STATIC"
        record["reason"] = ("the geometry is identical at the first and last frame; the "
                            "action imported but is not driving anything (failure mode 3)")
        return emit(record)
    if worst > record["limb_radius_m"] + TOL:
        record["verdict"] = "OFF_TRUTH"
        record["reason"] = (
            f"geometry is {worst:.5f} m from the authored wrist, further than one limb "
            f"radius ({record['limb_radius_m']}); the pose does not match the ground "
            f"truth. At a frame rate other than the authored one this is failure mode 2 — "
            f"glTF stores key times in seconds, so the arc arrives compressed or stretched")
        return emit(record)

    record["verdict"] = "OK"
    record["reason"] = (
        f"the arc survived the round trip; worst gap {worst:.5f} m within limb radius "
        f"{record['limb_radius_m']}, displacement {record['displacement_m']:.5f} m")
    return emit(record)


if __name__ == "__main__":
    sys.exit(main())
