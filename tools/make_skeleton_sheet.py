"""make_skeleton_sheet — the Director's skeleton-approval sheet.

    blender -b --factory-startup -P tools\\make_skeleton_sheet.py -- --glb=<subject.glb> --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

Built for the judgement it exists to serve: **is every pivot on its sculpted ball?** The
Director caught the first skeleton at 1:1 — he saw it was not lined up properly —
so the joint insets are framed on the **ball centre**, identical camera before and after, and
rendered at native size so the two rows are the same zoom he was looking at.

Every camera is orthographic and every panel in a row shares one `ortho_scale`, so panel
scale is uniform by construction rather than by care. Rendered from the terracotta body with
material and light; the skeleton is a second pass composited over it, so a pivot can be seen
*inside* him rather than only where it breaks the silhouette.

No gate state is printed on this sheet, and no debug text.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import json  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import joints, landmarks, sitelist  # noqa: E402

FULL_W, FULL_H = 900, 1360
INSET = 620

#: Half the inset's world width, as a fraction of the figure's own height. Sized so the
#: LARGEST before-offset still lands inside the frame: the elbow pivot sat 0.074 from its
#: ball, and at the first zoom tried (0.115) it fell outside the panel entirely — the before
#: row showed a bone tube and no pivot at all, which reads as a missing render rather than
#: as the error it is. The comparison is only worth looking at if the miss is in shot.
INSET_HEIGHT_FRACTION = 0.20

BEFORE_RGB = (1.00, 0.42, 0.16)   # the heuristic placement
AFTER_RGB = (0.10, 0.85, 1.00)    # the placement measured off the sculpted balls

#: The six joints the insets show, in body order. One side only — the panels are already
#: six wide, and the offset table in the report carries both sides.
INSET_JOINTS = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bands", type=int, default=200)
    return p.parse_args(argv)


def emission(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*rgb, 1.0)
    em.inputs[1].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return mat


def overlay_from_marks(marks, height, rgb, tag):
    """Bone tubes and pivot balls straight from a landmark dict — no armature needed.

    Built from the landmarks rather than from a Blender armature so the *before* skeleton
    can be drawn without building a second rig, and so the two rows differ in exactly one
    thing: where the pivots are.
    """
    mat = emission(f"ov_{tag}", rgb)
    r_bone, r_pivot = 0.0035 * height, 0.0135 * height
    made = []
    for b in sitelist.BONES:
        head, tail = Vector(marks[b.head]), Vector(marks[b.tail])
        d = tail - head
        if d.length > 0:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r_bone, depth=d.length,
                                                location=head + d / 2.0)
            ob = bpy.context.active_object
            ob.name = f"ov_{tag}_bone_{b.name}"
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = d.to_track_quat("Z", "Y")
            ob.data.materials.append(mat)
            made.append(ob)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=10, radius=r_pivot,
                                             location=head)
        j = bpy.context.active_object
        j.name = f"ov_{tag}_pivot_{b.name}"
        j.data.materials.append(mat)
        made.append(j)
    for ob in made:
        ob.hide_render = True
    return made


def light_the_scene(scene):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.30, 0.30, 0.32, 1.0)
    bg.inputs[1].default_value = 1.0
    for name, energy, rot in (("key", 3.4, (52, 0, 26)), ("fill", 1.3, (62, 0, -134)),
                              ("rim", 2.1, (74, 0, 178))):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.rotation_euler = tuple(math.radians(a) for a in rot)


def ortho_camera(scene, name, target, azim_deg, ortho_scale, res):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    a = math.radians(azim_deg)
    cam.location = Vector(target) + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100


def shoot(scene, path, transparent):
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames = os.path.join(out, "frames")
    os.makedirs(frames, exist_ok=True)

    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=args.glb)
    mesh_obj = [o for o in bpy.data.objects if o.type == "MESH"][0]

    source = rig_character.world_verts(mesh_obj)
    lo, hi = source.min(axis=0), source.max(axis=0)
    height = float(hi[2] - lo[2])
    diagonal = float(((hi - lo) ** 2).sum() ** 0.5)
    centre = Vector(((lo + hi) / 2.0).tolist())

    lm = landmarks.derive(source, n_bands=args.bands)
    before_marks = dict(lm["landmarks"])
    balls, _ = rig_character.measure_joint_balls(mesh_obj, diagonal)
    after_marks, table = joints.snap_sites_to_balls(lm, balls)

    light_the_scene(scene)
    ov_before = overlay_from_marks(before_marks, height, BEFORE_RGB, "before")
    ov_after = overlay_from_marks(after_marks, height, AFTER_RGB, "after")

    def render(tag, target, azim, oscale, res, overlay):
        ortho_camera(scene, f"cam_{tag}", target, azim, oscale, res)
        for ob in ov_before + ov_after:
            ob.hide_render = True
        mesh_obj.hide_render = False
        body = shoot(scene, os.path.join(frames, f"{tag}_body.png"), False)
        if overlay is None:
            return body, None
        mesh_obj.hide_render = True
        for ob in overlay:
            ob.hide_render = False
        bones = shoot(scene, os.path.join(frames, f"{tag}_bones.png"), True)
        mesh_obj.hide_render = False
        return body, bones

    full_scale = height * 1.10
    full = {tag: render(tag, centre, azim, full_scale, (FULL_W, FULL_H), ov_after)
            for tag, azim in (("front", 0.0), ("side", 90.0))}

    # Insets framed on the BALL CENTRE, so the camera is identical before and after and the
    # only thing that moves between the two rows is the pivot.
    side = "L" if lm["facing"]["left_x_sign"] > 0 else "R"
    inset_scale = height * INSET_HEIGHT_FRACTION
    insets = {}
    for joint in INSET_JOINTS:
        site = f"{joint}_{side}"
        target = Vector(table[site]["after"])
        body_b, bones_b = render(f"inset_{joint}_before", target, 0.0, inset_scale,
                                 (INSET, INSET), ov_before)
        _, bones_a = render(f"inset_{joint}_after", target, 0.0, inset_scale,
                            (INSET, INSET), ov_after)
        insets[joint] = {"body": body_b, "before": bones_b, "after": bones_a,
                         "offset_frac": table[site]["offset_as_fraction_of_segment"]}

    spec = {
        "out": out,
        "filename": "E07-skeleton-approval.png",
        "title": "E07 — the skeleton, for approval",
        "subtitle": ("22 named bones · every limb pivot moved onto the mannequin's own "
                     f"sculpted ball-joint · insets are 1:1, character's {side} side, "
                     "same camera in both rows"),
        "rows": [
            {"title": "The figure, with the skeleton in place",
             "panels": [{"body": full["front"][0], "overlay": full["front"][1],
                         "label": "front"},
                        {"body": full["side"][0], "overlay": full["side"][1],
                         "label": "side"}]},
            {"title": "Before — pivots placed by proportion",
             "panels": [{"body": insets[j]["body"], "overlay": insets[j]["before"],
                         "label": j} for j in INSET_JOINTS]},
            {"title": "After — pivots placed on the sculpted ball",
             "panels": [{"body": insets[j]["body"], "overlay": insets[j]["after"],
                         "label": j} for j in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("PANELS_OK " + path)


if __name__ == "__main__":
    main()
