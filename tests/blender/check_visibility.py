"""Render-visibility selection, checked inside Blender. Prints; asserts nothing.

This is the fixture for the defect G4 caught on 2026-08-10. The question CLAUDE.md asks
of every fixture — *what would this look like if the code were wrong in the specific way
this check exists to catch?* — has a concrete answer here: a `type == "MESH"` filter
returns 3 meshes instead of 1, and the reported bounds balloon from the subject's own
size to the decoy's.

Case 1 reproduces the real thing: a collection named `glTF_not_exported` with
`hide_render=True`, which is what Blender's own glTF importer creates.
Case 2 is the case `visible_get()` would get wrong: hidden in render, visible in the
viewport. If the predicate were viewport-based, this decoy would survive.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))

import bpy  # noqa: E402

from armature_core import blender_scene as bs  # noqa: E402


def cube(name, size, location):
    mesh = bpy.data.meshes.new(name)
    s = size / 2.0
    verts = [(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    ob.location = location
    return ob


scene = bs.reset_scene()
subject = cube("subject", 1.0, (0, 0, 0))
scene.collection.objects.link(subject)

# Case 1 — the real one: hidden collection, exactly as the glTF importer makes it.
gltf_decoy = cube("gltf_decoy", 4.0, (0, 0, 0))
hidden_coll = bpy.data.collections.new("glTF_not_exported")
hidden_coll.hide_render = True
hidden_coll.hide_viewport = True
scene.collection.children.link(hidden_coll)
hidden_coll.objects.link(gltf_decoy)

# Case 2 — hidden in render only; the viewport still shows it.
render_only_coll = bpy.data.collections.new("render_hidden_only")
render_only_coll.hide_render = True
render_only_coll.hide_viewport = False
scene.collection.children.link(render_only_coll)
viewport_visible_decoy = cube("viewport_visible_decoy", 6.0, (0, 0, 0))
render_only_coll.objects.link(viewport_visible_decoy)

# Case 3 — object-level hide_render.
obj_hidden = cube("obj_hidden", 8.0, (0, 0, 0))
obj_hidden.hide_render = True
scene.collection.objects.link(obj_hidden)

all_meshes = [o for o in bpy.data.objects if o.type == "MESH"]
visible = bs.render_visible_meshes(scene, all_meshes)

naive_bounds = bs.world_bounds(all_meshes)
filtered_bounds = bs.world_bounds(visible)

print("VISIBILITY " + json.dumps({
    "all_mesh_names": sorted(o.name for o in all_meshes),
    "render_visible_names": sorted(o.name for o in visible),
    "viewport_visible_get": {o.name: bool(o.visible_get()) for o in all_meshes},
    "naive_sphere_radius": round(float(naive_bounds[2]), 6),
    "filtered_sphere_radius": round(float(filtered_bounds[2]), 6),
}))
