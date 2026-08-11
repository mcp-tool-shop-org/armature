"""make_rig_sheet — the E07 dailies sheet: the character, the skeleton on him, the arc.

    blender -b --factory-startup -P tools\\make_rig_sheet.py -- --glb=<subject.glb> --out=<dir>

Rendered from the character with material and light, never as a schematic. The bone
overlay is a second render pass composited over the lit body so the Director can see where
each bone actually sits *inside* him; the body panels beside it carry no overlay so he can
judge the figure itself.

**Uniform panel scale is enforced by construction, not by care.** Every camera is
orthographic and every panel in a row shares one `ortho_scale`, so a millimetre of character
is the same number of pixels in every panel of that row. The four joint insets are rendered
at their native size and never resampled — that is what "at 1:1" means here.

This sheet is rendered from the state E07 actually reached. What that state is belongs in
the report; this file draws it and prints no verdict on it.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import landmarks, sitelist  # noqa: E402

FULL_W, FULL_H = 760, 1180
INSET = 560
PAD, LABEL_H, TITLE_H = 26, 54, 150
BG, INK, SUB = (22, 22, 24), (238, 238, 240), (166, 166, 172)

BONE_RGB = (0.10, 0.85, 1.00)      # deforming bones
MARKER_RGB = (1.00, 0.62, 0.12)    # the non-deforming facial markers


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


def bone_overlay(arm_obj, height):
    """Emissive tubes along every bone, plus a ball at every bone head."""
    r_bone, r_joint = 0.0045 * height, 0.0105 * height
    mats = {True: emission("bone_deform", BONE_RGB),
            False: emission("bone_marker", MARKER_RGB)}
    made = []
    for b in arm_obj.data.bones:
        head, tail = Vector(b.head_local), Vector(b.tail_local)
        d = tail - head
        if d.length <= 0:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=r_bone, depth=d.length,
                                            location=head + d / 2.0)
        ob = bpy.context.active_object
        ob.name = f"ov_bone_{b.name}"
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = d.to_track_quat("Z", "Y")
        ob.data.materials.append(mats[bool(b.use_deform)])
        made.append(ob)

        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=r_joint,
                                             location=head)
        j = bpy.context.active_object
        j.name = f"ov_joint_{b.name}"
        j.data.materials.append(mats[bool(b.use_deform)])
        made.append(j)
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
    for name, energy, rot in (("key", 3.4, (50, 0, 28)), ("fill", 1.3, (62, 0, -132)),
                              ("rim", 2.0, (74, 0, 178))):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.rotation_euler = tuple(math.radians(a) for a in rot)


def ortho_camera(scene, name, target, azim_deg, ortho_scale, res, elev_deg=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    dist = 6.0
    cam.location = Vector(target) + Vector((
        dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a),
        dist * math.sin(e)))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    return cam


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
    centre = Vector(((lo + hi) / 2.0).tolist())

    lm = landmarks.derive(source, n_bands=args.bands)
    arm_obj, _ = rig_character.build_armature(scene, lm["landmarks"], "performer")
    rig_character.skin(mesh_obj, arm_obj)
    probe = rig_character.author_probe(
        {"armature": arm_obj, "scene": scene, "landmarks": lm})

    light_the_scene(scene)
    overlay = bone_overlay(arm_obj, height)
    arm_obj.hide_render = True

    def render_pair(tag, target, azim, oscale, res, elev=0.0):
        ortho_camera(scene, f"cam_{tag}", target, azim, oscale, res, elev)
        for ob in overlay:
            ob.hide_render = True
        body = shoot(scene, os.path.join(frames, f"{tag}_body.png"), False)
        mesh_obj.hide_render = True
        for ob in overlay:
            ob.hide_render = False
        bones = shoot(scene, os.path.join(frames, f"{tag}_bones.png"), True)
        mesh_obj.hide_render = False
        return body, bones

    full_scale = height * 1.12
    views = [("front", 0.0, "front"), ("threeq", 38.0, "three-quarter"),
             ("side", 90.0, "side")]
    scene.frame_set(1)
    bpy.context.view_layer.update()
    full = {tag: render_pair(tag, centre, azim, full_scale, (FULL_W, FULL_H))
            for tag, azim, _ in views}

    # The arc, body only: the Director judges the figure, not the diagram.
    arc_panels = {}
    for f in (1, rig_character.PROBE_FRAMES):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        ortho_camera(scene, f"cam_arc{f}", centre, 0.0, full_scale, (FULL_W, FULL_H))
        for ob in overlay:
            ob.hide_render = True
        arc_panels[f] = shoot(scene, os.path.join(frames, f"arc_f{f:02d}.png"), False)

    # Four joint insets, one ortho_scale for all of them: 1:1 and comparable by construction.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    marks = lm["landmarks"]
    side = "L" if lm["facing"]["left_x_sign"] > 0 else "R"
    inset_scale = height * 0.26
    joints = [("shoulder", marks[f"shoulder_{side}"]), ("elbow", marks[f"elbow_{side}"]),
              ("hand", marks[f"wrist_{side}"]), ("hip", marks[f"hip_{side}"])]
    insets = {name: render_pair(f"inset_{name}", Vector(p), 0.0, inset_scale,
                                (INSET, INSET))
              for name, p in joints}

    # Blender's bundled Python carries no PIL, so compositing lives in its own module run
    # under the repo's venv. A two-step is fine here and would not be for a gate: this is
    # a sheet builder, and nothing irreversible waits on the second step.
    import json
    panels = {
        "out": out,
        "full": {tag: list(full[tag]) for tag in full},
        "arc": {str(k): v for k, v in arc_panels.items()},
        "insets": {k: list(v) for k, v in insets.items()},
        "views": views,
        "joint_order": [n for n, _ in joints],
        "side": side,
        "probe": {"which_arm_is_on_plus_x": probe["which_arm_is_on_plus_x"],
                  "frames": probe["frames"], "fps": probe["fps"]},
        "geometry": {"full_w": FULL_W, "full_h": FULL_H, "inset": INSET,
                     "pad": PAD, "label_h": LABEL_H, "title_h": TITLE_H,
                     "probe_frames": rig_character.PROBE_FRAMES},
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(panels, fh, indent=2)
    print("PANELS_OK " + path)


if __name__ == "__main__":
    main()
