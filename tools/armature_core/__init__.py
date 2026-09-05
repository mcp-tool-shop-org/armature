"""armature_core — the pieces of the control-sequence exporter.

Split by what changes together (DECOMPOSE_BY_SECRETS). **The module list lives in ONE
place: `armature_core.cli.SURFACE`** — `armature modules` prints it, `armature modules
--json` hands it to a machine, and `tests/test_cli.py` pins it against the directory on
disk in BOTH directions (no listed module without a file, no module on disk unlisted) plus
a clause asserting that a row may only name a gate the module beside it carries.

⚠ **This docstring used to enumerate seven modules and it had drifted.** Measured
2026-09-05: it named `errors, gates, shotspec, pngio, channels, openpose, blender_scene` as
what the package "is split by", while the package carries 30 content modules plus
`__init__.py` and `cli.py` — every gate module added since was absent (`route_gates`,
`rig_gates`, `donor_gate`, `canon`, `canon_census`, `subject`, `framing`, `turnaround`,
`startframe`, `landmarks`, `lift_solve`, `parts`, `assembly` and the rest). Its one row
that named gates was also wrong about its own module: it declared a G1-through-G5 RANGE for
`gates.py`, where that module
raises eight andon classes (the five numbered ones the package defines, plus R, B and S)
and the third number in that range does not exist anywhere in the tree. The range had been
wrong since G6 was added. A range cannot be checked against a set, which is why the census
that replaces it refuses one outright.

`cli.SURFACE` is census-pinned in both directions and this list was pinned by nothing,
which is why one drifted and the other did not. The enumeration is deleted rather than
re-typed: two hand-maintained copies of one list is the shape the drift came from. The cost
is a reader's, and it was the first file a session opens in this package describing a
smaller package than the one it is about to change.

Everything except `blender_scene` imports cleanly under a plain CPython, which is what lets
the gate tests run the real write path without Blender present. `blender_scene` is the only
module that imports `bpy`; `armature check` reports that as `needs-blender` rather than as a
defect, and reports every other unresolved row with the exception type and message that
caused it.
"""
