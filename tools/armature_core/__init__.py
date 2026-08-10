"""armature_core — the pieces of the control-sequence exporter.

Split by what changes together (DECOMPOSE_BY_SECRETS):

  errors.py    the exception types the gates raise
  gates.py     G1..G5 — pure predicates that RAISE; no bpy, no I/O
  shotspec.py  the shot-spec contract: schema, load, resolve, hash
  pngio.py     a dependency-free PNG writer (Blender's python has no Pillow)
  channels.py  numpy channel maths: normalization, edge derivation, encoding
  openpose.py  the OpenPose-18 convention as retrieved in F20
  blender_scene.py   the only module that imports bpy

Everything except `blender_scene` imports cleanly under a plain CPython, which is
what lets the gate tests run the real write path without Blender present.
"""
