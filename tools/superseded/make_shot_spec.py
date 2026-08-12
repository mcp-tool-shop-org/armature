#!/usr/bin/env python
"""make_shot_spec — compose E08's shot and write the spec `stage_render` will run.

    python tools/make_shot_spec.py --motion=<walk.motion.json> --glb=<walk.glb>
                                   --out=specs/E08-bar-approach.json

Reads the authored ground truth, solves the camera with `armature_core.framing`, and
emits a shot spec whose `camera.target` and `camera.radius` are **pinned numbers**. No
bpy: this is arithmetic, and keeping it out of Blender means the composition can be
checked against the render's own measured bbox afterwards instead of being taken on faith.

Why the camera is pinned rather than auto-fitted is in `framing`'s module docstring: an
`auto` radius fits the union of every frame, and this subject walks 1.27 of his own
heights, so auto-fit would frame three bodies' worth of empty floor and shrink him to a
doll. E03 pinned target and radius for a different reason and the mechanism is the same.

The camera is STATIC. The spec allowed "static or a slight push-in"; a push-in would need
a per-frame radius, which `stage_render` does not carry, and adding one is a tool change
this experiment did not ask for. Recorded as a choice, not delivered as a silence.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import framing, shotspec  # noqa: E402

#: The shot, as composed. Every one of these is a decision and belongs in the report.
#:
#: **Azimuth was 205 and is 225; changed after LOOKING at the preview, before any credit.**
#: The camera sits at `az` around a performer who faces -Y, so `-sin(az)` is how far
#: round toward his front it is and `-cos(az)` is how much of his walk reads as screen
#: travel. 205 deg is 65 deg off his front — near profile — and the preview showed exactly
#: that: a silhouette. Identity is the thing the Director judges by eye and no metric
#: approximates, and a profile denies him the evidence. 225 deg is a true three-quarter
#: front (45 deg off) and costs 22% of the lateral travel (x0.707 against x0.906), which
#: partly returns as a free push-in because he now walks toward the lens as well as across
#: it. The superseded composition and its render are kept beside this one.
AZIMUTH_DEG = 225.0      # front three-quarter from his right; he walks screen-right
ELEVATION_DEG = 6.0      # just above his eyeline's height, near enough to standing
LENS_MM = 50.0
SENSOR_MM = 36.0
WIDTH, HEIGHT = 832, 480     # the 480p landscape bucket, both divisible by 16
FRAMES, FPS = 65, 16         # 4n+1, inside the 81-frame trained horizon
HEIGHT_FRAC = 0.72           # of the frame, over the union INCLUDING the raised hand
END_X_FRAC = 0.66            # he arrives on the right third
TARGET_Y_FRAC = 0.54         # union centred just below middle, leaving headroom above


def body_cloud(world, bbox_lo, bbox_hi):
    """Points that must stay in frame for one authored frame.

    The ground truth carries landmarks, and landmarks under-report the SILHOUETTE: head
    top and toes do bound this character vertically (measured — both sit exactly on the
    rest bbox), but his torso is 0.075 wider on each side than his shoulder landmarks. So
    the torso's own measured half-extents are hung on the hips as a bound. Under-reporting
    here would frame him correctly on paper and clip his shoulder in the render.
    """
    pts = [tuple(v) for v in world.values() if isinstance(v, list) and len(v) == 3]
    hx = 0.5 * (bbox_hi[0] - bbox_lo[0])
    hy = 0.5 * (bbox_hi[1] - bbox_lo[1])
    hips = tuple(world["hips"])
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pts.append((hips[0] + sx * hx, hips[1] + sy * hy, hips[2]))
    return pts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--motion", required=True)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="E08-bar-approach")
    a = ap.parse_args(argv)

    with open(a.motion, encoding="utf-8") as fh:
        motion = json.load(fh)
    gt = motion["ground_truth"]
    if len(gt) != FRAMES:
        raise SystemExit(
            f"the motion record carries {len(gt)} frames and the shot is {FRAMES}; "
            f"framing a shot against a different performance is not a composition")

    with open(os.path.join(os.path.dirname(os.path.abspath(a.motion)), os.pardir,
                           "asset", "rig_manifest_auto.json"), encoding="utf-8") as fh:
        rig = json.load(fh)
    lo, hi = rig["bbox"]["lo"], rig["bbox"]["hi"]

    all_points, end_points = [], []
    for rec in gt:
        pts = body_cloud(rec["world"], lo, hi)
        all_points.extend(pts)
        if rec["frame"] == FRAMES - 1:
            end_points = pts

    sol = framing.solve_camera(
        all_points, end_points, AZIMUTH_DEG, ELEVATION_DEG, LENS_MM, SENSOR_MM,
        WIDTH, HEIGHT, height_frac=HEIGHT_FRAC, end_x_frac=END_X_FRAC,
        target_y_frac=TARGET_Y_FRAC)
    if not sol["in_frame"]:
        raise SystemExit(
            f"the solved composition puts part of the performance outside the frame: "
            f"x {sol['achieved']['union_x']} y {sol['achieved']['union_y']}. A shot that "
            f"clips the performer is not the shot that was blocked.")

    start_x = framing.project(tuple(gt[0]["world"]["hips"]), sol["target"], sol["radius"],
                              AZIMUTH_DEG, ELEVATION_DEG, LENS_MM, SENSOR_MM,
                              WIDTH, HEIGHT)[0]
    end_x = framing.project(tuple(gt[-1]["world"]["hips"]), sol["target"], sol["radius"],
                            AZIMUTH_DEG, ELEVATION_DEG, LENS_MM, SENSOR_MM,
                            WIDTH, HEIGHT)[0]

    spec = {
        "spec_version": shotspec.SPEC_VERSION,
        "name": a.name,
        "generator": "wan-vace",
        "asset": {"path": os.path.abspath(a.glb), "sha256": motion["output"]["sha256"]},
        "resolution": {"width": WIDTH, "height": HEIGHT},
        "frames": {"count": FRAMES, "fps": FPS},
        "channels": ["depth", "mask"],
        "subject": {"animation": "per_frame"},
        "depth": {"window": "per_shot"},
        "camera": {
            "type": "orbit",
            "target": [round(v, 9) for v in sol["target"]],
            "radius": round(sol["radius"], 9),
            "elevation_deg": ELEVATION_DEG,
            "azimuth_start_deg": AZIMUTH_DEG,
            "azimuth_sweep_deg": 0.0,
            "lens_mm": LENS_MM,
            "sensor_mm": SENSOR_MM,
            "clip_start": 0.05,
            "clip_end": 1000.0,
        },
        "render": {"engine": "BLENDER_EEVEE", "samples": 1, "filter_size": 0.01,
                   "film_transparent": True},
        "gates": {"g4_tolerance_px": 2},
    }
    shotspec.normalise_spec(spec)     # refuse to write a spec the renderer would reject
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2, sort_keys=True)
        fh.write("\n")

    side = os.path.splitext(a.out)[0] + ".framing.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({"solution": sol, "hips_screen_x": {"frame_0": start_x,
                                                      "frame_last": end_x},
                   "motion": os.path.abspath(a.motion)}, fh, indent=2)

    print("SHOT_SPEC_OK " + json.dumps({
        "out": os.path.abspath(a.out), "framing": os.path.abspath(side),
        "radius": round(sol["radius"], 4),
        "target": [round(v, 4) for v in sol["target"]],
        "union_height_frac": round(sol["achieved"]["union_height_frac"], 4),
        "union_x": [round(v, 4) for v in sol["achieved"]["union_x"]],
        "union_y": [round(v, 4) for v in sol["achieved"]["union_y"]],
        "hips_x_start": round(start_x, 4), "hips_x_end": round(end_x, 4),
        "in_frame": sol["in_frame"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
