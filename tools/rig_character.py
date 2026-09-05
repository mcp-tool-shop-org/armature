"""rig_character — give a canonical character mesh a rig whose bones carry anatomical names.

    blender -b --factory-startup -P tools\\rig_character.py -- --glb=<in.glb> --out=<dir>
    blender -b --factory-startup -P tools\\rig_character.py -- --glb=<in.glb> --out=<dir> --measure-only

E01 measured the whole reason this exists: four rigged GLBs on this machine, every one of
them naming its bones `bone_0 … bone_N`, **zero of 18 anatomical sites findable by name in
any of them**. Nothing about those files reports a problem — they import, they carry a skin,
they pose. They simply cannot be posed *on purpose*, because nothing in them says which bone
is the shoulder. E03 was designed to route around that gap and E06 measured that it cannot be
routed around. So this tool closes it: it places bones from landmarks measured on the mesh,
names them from a list committed before the first bone, skins with `ARMATURE_AUTO`, authors
E03's arm arc as a probe, and exports.

**The gates raise from inside this file**, before the manifest that would make a run look
finished — never behind a shell `&&`, never through an `assert`, with no skip flag anywhere:

* **Gate N** — every registered site names exactly one bone, and the rig carries nothing
  unregistered. Run twice: on the built armature, and again on the **re-imported export**,
  because the names that matter are the ones a consumer reads out of the GLB and
  `export_def_bones` alone would silently drop every non-deforming marker.
* **Gate P** — binding the mesh did not move it, within 1e-4 of the mesh's own bbox diagonal.
* **Gate D** — a second build from the same inputs produced the same rig, compared as parsed
  objects and never as bytes.

**Deformation under pose is NOT a gate.** Per-structure displacement statistics are written
to the manifest as diagnostics. Whether the deform is acceptable — whether he still looks
like *him* when his arm comes up — is the Director's judgement on the sheet, at his zoom, and
no number here approximates it.
"""

import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from armature_core import (  # noqa: E402
    binding, blender_scene, joints, landmarks, parts, posearc, rig_gates, sitelist)
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "1.1.0"

#: Weld distance for the throwaway copy the joint-ball search runs on, as a fraction of the
#: subject's own bbox diagonal. glTF splits a vertex at every UV and normal seam, so the
#: duplicates sit at *identical* positions and any tiny epsilon recovers the asset's real
#: shells. Expressed per-structure so it is not a length in metres.
BALL_WELD_FRACTION = 1e-6

#: E03's authored arc, reused verbatim so E08 compares character-control against
#: wire-control on the same authored transform: rotate about +Y by -theta, 0 -> 90 degrees,
#: 33 keys, 16 fps. `arm_r_raise`'s own docstring defines the moving limb as "the arm named
#: _r in the generator (the +X side)" -- a label on a planar wire figure, not anatomy. Which
#: of this character's arms lies on +X is measured (`landmarks.facing`) and reported.
PROBE_ARC = "arm_r_raise"
PROBE_FRAMES = 33
PROBE_FPS = 16
PROBE_START_DEG = 0.0
PROBE_END_DEG = 90.0


#: Gate P's round-trip probe cap, passed EXPLICITLY at the call site rather than inherited
#: from `rig_gates.gate_p_round_trip_positions`' declared default. MEASURED 2026-09-04
#: (F-2d1fd05e): the call passed three positional arguments, so the cap was taken silently.
#: This subject comes back from a glTF round trip as 399,140 source vertices against
#: 399,903 exported, with 149,643 unique positions -- an order of magnitude above the cap.
#: When the cap bites, the gate sets `probe_truncated_at`, keeps `pts[:max_probe]` (numpy's
#: lexicographic order, i.e. the smallest-x positions) and still reaches its pass verdict;
#: a repo-wide grep for `probe_truncated_at` returned exactly one hit, the gate's own write.
#: The value is unchanged from the inherited default so this fix moves no measurement; what
#: changes is that the choice is stated here and the flag is READ BACK below.
ROUND_TRIP_MAX_PROBE = 20000


class GateObjects(GateFailure):
    """Gate OBJ - the export would carry an object nobody registered.

    MEASURED 2026-09-04 (F-2ef09fa0): the refusal raised the bare `ArmatureError`, so the
    object table the gate had just assembled -- every object with its type, collections and
    effective render visibility, i.e. exactly the "whether it originates in the file or in
    Blender's importer" the docstring says the gate records rather than assumes -- was
    neither passed nor returned on the raising path. `_write_halt` then wrote `"gate": "?"`
    and `"evidence": {}`, in the tool that produces the rigged GLB.
    """

    gate = "OBJ"


class GateSubject(GateFailure):
    """The subject cannot be identified without guessing which mesh is the character."""

    gate = "SUBJECT"


class GateMode(GateFailure):
    """A named route this tool does not have."""

    gate = "MODE"


class GateSubjectDegenerate(GateFailure):
    """Gate SCALE - the subject's own bbox diagonal is not a number to divide by.

    MEASURED 2026-09-04 (F-940b0800). `build_pass` derived the tolerance SCALE for the
    whole build as `float(np.linalg.norm(hi - lo))` over the raw imported mesh, with no
    finiteness clause anywhere on the path: `grep` for `isfinite`/`isnan`/`isinf`/
    `require_finite` across this file, `rig_gates.py`, `landmarks.py` and `joints.py`
    returned ZERO hits. One NaN vertex gives a NaN diagonal, hence a NaN tolerance, and
    `rig_gates.gate_d_determinism` then returns "two builds agree on bones and hierarchy"
    with a 4.0-unit `worst_bone_delta` in the same evidence dict, because `nan > x` is
    False in both directions. One `+inf` vertex does the same.

    It matters most on the SKELETON route: `run_skeleton` calls `build_pass(..., bind=False)`
    twice, `gate_p` is left None when nothing is bound, and `gate_n_names` runs after Gate D
    and compares names only — so Gate D is the FIRST gate that sees geometry, and nothing
    between `blender_scene.import_glb` and it examines a coordinate. The artifact that
    reaches the Director is `<name>_skeleton.glb` beside a manifest recording
    `bbox.diagonal: NaN` and `gates.D_determinism: PASS`.

    The refusal belongs at the SOURCE rather than at the gate: `measure_joint_balls` divides
    by this diagonal, `landmarks.derive` consumes the same array, and both run before Gate D.
    Its own id ("SCALE") rather than GateSubject's, because a subject that cannot be
    identified and a subject whose coordinates are not numbers send a session to two
    different places — and `tests/test_gates.py::test_no_new_andon_takes_an_id_another_andon
    _already_uses` is the standing check that two andons never share one.
    """

    gate = "SCALE"


def subject_scale(source, where):
    """`(diagonal, lo, hi)` for a subject whose coordinates are numbers, else raise.

    The one place in this module a bbox diagonal is derived. `require_finite`'s default
    refuses zero and negatives in the same clause, which also catches the all-coincident
    and single-vertex subjects before `measure_joint_balls(mesh_obj, diagonal)` divides by
    it. The per-vertex clause is the stronger form and names WHICH vertex, because "the
    subject carries a NaN" is not an actionable sentence and "vertex 41,207 axis 1" is.
    """
    n = int(source.shape[0])
    ev = {"gate": "SCALE", "andon": "GateSubjectDegenerate", "where": where,
          "n_vertices": n}
    if not n:
        raise GateSubjectDegenerate(
            f"the subject carries no vertices at all, so it has no scale of its own for "
            f"any tolerance in this build to be a fraction of", ev)
    bad = np.argwhere(~np.isfinite(source))
    if bad.size:
        i, axis = int(bad[0][0]), int(bad[0][1])
        ev["first_non_finite_vertex"] = {
            "index": i, "axis": axis, "value": repr(float(source[i][axis])),
            "n_non_finite_components": int(bad.shape[0])}
        raise GateSubjectDegenerate(
            f"the subject carries {bad.shape[0]} non-finite coordinate component(s); the "
            f"first is vertex {i} axis {axis} = {float(source[i][axis])!r}. Every "
            f"tolerance in this build is a fraction of this subject's own bbox diagonal, "
            f"and a NaN diagonal makes every one of them NaN — which fires no bound at "
            f"all, because `nan > x` and `nan < x` are both False. A rig built on it "
            f"passes Gate D with an agreement verdict about a build that did not agree",
            ev)
    lo, hi = source.min(axis=0), source.max(axis=0)
    ev.update({"bbox_lo": lo.tolist(), "bbox_hi": hi.tolist()})
    diagonal = parts.require_finite(
        "bbox_diagonal", float(np.linalg.norm(hi - lo)), GateSubjectDegenerate, ev)
    return diagonal, lo, hi


class SiteListInvalid(ArmatureError):
    """The site registration table itself is inconsistent - a refusal, not a crash.

    F-61671cb3, wave 12. `sitelist.validate()` audits this repo's own literal registration
    table (duplicate names, forward parents, head == tail, the `site` flags against
    `E01_SITES`, the count of 18), so on an unmodified sitelist it CANNOT fire. It is
    reachable in exactly the situation it exists for: a session editing the site list -
    which is the case `rig_character` and `rig_parts` invoke it to catch.

    What that session saw, MEASURED 2026-09-04 by driving both `__main__` handlers with a
    `ValueError` carrying a real sitelist message: `RIG_CHARACTER_HALT {"outcome": "FAILED
    - an unhandled error", "gate": null, "evidence": null}` at exit **1**, and the identical
    shape for `RIG_PARTS_HALT`. `ValueError` is outside the `ArmatureError` family, so the
    three-outcome branch classified the repo's own registration validator refusing as a
    crash in the rigging code. That is F-c3f86abc's harm inverted: that finding removed a
    crash being recorded as a fired gate; this one removes a deliberate refusal being
    recorded as an unhandled error - and the `halt.json` the five rig writers produce said
    the same, sending a session that had just edited `sitelist.py` to the rigging
    arithmetic instead of to the table it had edited.

    A refusal with no gate behind it, so a bare `ArmatureError` and not a `GateFailure`:
    the halt contract answers 2 and "REFUSED - the tool declined to proceed" for both, and
    the three-outcome vocabulary is what distinguishes them.

    The cleanest home for this is `armature_core.sitelist` itself, raising a typed refusal
    so no caller needs a wrapper at all; that module is another domain's in the frozen map
    and the change is in flight there (SEAM 1, core-solvers). `validate_sitelist` below
    re-types only what is NOT already in the `ArmatureError` family, so their class reaches
    the halt line as itself the moment it lands.

    WAVE 16, RULE 5 (SEAM 1). This class held the family's one tool-local normalising
    constructor - `self.evidence = evidence or {}` - and it is DELETED. The base
    `ArmatureError.__init__` stores what it is passed; `GateFailure` is the single
    exemption that normalises, because its clauses index into `ev` while they measure; a
    subclass outside that subtree defines no `__init__` at all, since inheritance already
    gives it the two-argument shape. Both raise sites in this file pass a dict, so no halt
    line changes today; a future bare-message raise now records `"evidence": null`
    honestly instead of an empty dict that claims a receipt was built.
    """


class GateGlbWritten(GateFailure):
    """Gate GLB - an exported GLB reached disk and is not zero bytes.

    F-9b2d4106, wave 12. `bpy.ops.export_scene.gltf(...)` has the same property
    `bpy.ops.render.render` has and that F-13bd448d was closed for on the four RENDERERS:
    it returns an operator STATUS SET and can return `{'CANCELLED'}` without raising. An
    AST scan pairing every `bpy.ops.export_scene.gltf` call site against a later existence
    or size check found eight tools that export a GLB, of which six at least materialise
    the file afterwards (`os.path.getsize`, `sha256_file`, or a re-import - each of which
    raises on an absent file) and two - `make_test_armature.py` and `rig_retopo.py`'s outer
    shell - did neither. NONE of the eight refused a ZERO-BYTE export: the six record the
    byte count as a number and never compare it, where the renderer family raises on
    `getsize(p) == 0`.

    The shape is `preview_glb.gate_previews_written`'s - missing AND zero-byte, naming the
    path - carried rather than reinvented, and it lives here because every rig tool already
    imports this module. It returns the digest so the caller records the file it actually
    confirmed, rather than hashing the path a second time.

    WAVE 14, F-6a9a0f72 - THE OPERAND. The class above named the status set in its own
    docstring and its own refusal message; the gate never read one. The whole check was
    `os.path.isfile` then `getsize == 0`, two properties a PREVIOUS run's GLB at the same
    path satisfies. Measured: 4,004 bytes written to `<tmp>/hero_bone_heat.glb` with plain
    Python, then `gate_glb_written(p, what='the rigged GLB')` in a process that had exported
    nothing returned a PASS record with a sha256 - a digest, a byte count and a verdict for
    a file that process never wrote. Nine `bpy.ops.export_scene.gltf` sites and fourteen
    `bpy.ops.render.render` sites in `tools/` discarded their return value; the correct
    shape sat twenty-five lines above one of them (`rig_bake.py:260`,
    `if 'FINISHED' not in result: raise BakeEmpty(...)` on `bpy.ops.object.bake`).

    So the gate now takes two REQUIRED keyword arguments and there are no defaults for
    them - a default is exactly the hole this finding is about:

    * `result` - the operator status set the export returned. Clause 1 refuses anything
      that is not a readable set containing `FINISHED`, with the set in the evidence.
    * `before` - `export_target_snapshot(path)` taken BEFORE the export ran. Clause 4
      refuses a file whose size AND `mtime_ns` are unchanged, which is the previous run's
      GLB sitting where this run's was supposed to land.
    """

    gate = "GLB"


def export_target_snapshot(path):
    """What is at `path` before an export runs, so a file this run did not write is visible.

    Taken BEFORE `bpy.ops.export_scene.gltf`, and read by `gate_glb_written`'s fourth
    clause. `mtime_ns` rather than `mtime`: the float seconds a `stat` reports are rounded,
    and two writes inside one tick would compare equal.
    """
    p = os.path.abspath(path)
    if not os.path.isfile(p):
        return {"path": p, "existed": False, "bytes": None, "mtime_ns": None}
    st = os.stat(p)
    return {"path": p, "existed": True, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}


def render_target_snapshot(path):
    """What is at `path` before a RENDER runs. `export_target_snapshot`'s twin.

    F-a2630f86, wave 22. Wave 16 made the pre-export snapshot REQUIRED (`gate_glb_written`
    clause 0) on the stated ground that every OTHER clause in Gate GLB "passes on that
    file" -- a previous run's artefact at the same path -- so the stale-target clause 4 had
    to be un-skippable. The RENDER half of the same premise had no clause 4 at all.
    RE-ENUMERATED on `e8263a3` by walking `tools/`: `export_target_snapshot` had NINE call
    sites (author_walk, lift_solve, make_test_armature, rig_bake, rig_character, rig_parts,
    rig_repair, rig_retopo x2) and ZERO callers outside the export family, while the render
    write sites -- `preview_glb.gate_previews_written`, `render_turnaround`'s per-view
    clause, `preview_walk`, `render_performer` and `render_start_frame` -- read exactly the
    three properties Gate GLB's own docstring names as insufficient (`FINISHED` in the
    status set, `os.path.isfile`, `getsize == 0`) and none measured the target before the
    write. The operator-status clause covers the CANCELLED direction; nothing covered "the
    operator reported FINISHED and the bytes at that path did not move", which is the
    direction clause 4 exists for.

    Consequence is bounded -- no realistic FINISHED-without-write was constructed on this
    rig -- so this is the POPULATION half of the wave-16 fix rather than a live defect. It
    is the same measurement either way, which is why it is the same function: one
    implementation, `mtime_ns` and not `mtime`, because the float seconds a `stat` reports
    are rounded and two writes inside one tick compare equal.
    """
    return export_target_snapshot(path)


def require_render_target_moved(path, before, gate_cls, ev=None,
                                what="the rendered frame"):
    """Raise `gate_cls` unless the bytes at `path` MOVED across this render. · ANDON

    Called after the caller's own `FINISHED` and existence clauses, so what is left is the
    one direction they cannot see. Two clauses, both keyed on the VALUE of the snapshot and
    never on whether one was passed (`gate_glb_written`'s clause 0, carried):

    * `no_pre_render_snapshot` -- `before` is not a `render_target_snapshot()` record
      carrying a boolean `existed`. A caller that took no snapshot has not measured the
      thing the clause below rules on, and a gate that answers anything in that state is
      answering about a run it cannot see.
    * `stale_render_target` -- the file's size AND nanosecond mtime are both what they were
      before the render. That is the previous run's file, and every consumer downstream
      reads the path.

    Returns the after-snapshot so a caller can put it in a record.
    """
    p = os.path.abspath(path)
    ev = dict(ev or {})
    ev.update({"andon": gate_cls.__name__, "what": what, "path": p, "before": before})
    if (not isinstance(before, dict) or "existed" not in before
            or not isinstance(before.get("existed"), bool)):
        ev["clause"] = "no_pre_render_snapshot"
        raise gate_cls(
            f"no pre-render snapshot was taken for {what} at {p}: `before` is {before!r}, "
            f"not a `render_target_snapshot()` record carrying a boolean `existed`. The "
            f"stale-target clause is the only one that can tell this run's frame from the "
            f"PREVIOUS run's file at the same path, and every other clause at this write "
            f"site passes on that file", ev)
    if not os.path.isfile(p):
        ev["clause"] = "render_target_missing"
        raise gate_cls(
            f"{what} at {p} does not exist after a render that reported FINISHED", ev)
    st = os.stat(p)
    after = {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
    ev["after"] = after
    if (before["existed"] and before.get("bytes") == after["bytes"]
            and before.get("mtime_ns") == after["mtime_ns"]):
        ev["clause"] = "stale_render_target"
        raise gate_cls(
            f"{what} at {p} is byte-for-byte the file that was already there before this "
            f"render ran (same size, same mtime to the nanosecond), on an operator that "
            f"reported FINISHED. A record naming its sha256 would describe a frame this "
            f"process never drew, and every instrument downstream would measure it", ev)
    return after


def gate_glb_written(path, *, result, before, what="the exported GLB"):
    """`{"path", "bytes", "sha256", "status", "verdict"}` for a GLB this run wrote, else raise.

    `result` is the export operator's status set and `before` is
    `export_target_snapshot(path)` taken before it ran. Both are required: see the class
    docstring above for why neither has a default.

    WAVE 16, F-8548f859 — THE DEFAULT THAT DISARMED THE CLAUSE. Wave 14 removed the
    keyword DEFAULTS and stopped there; the fourth clause was still guarded by
    `if (before and before.get("existed") and ...)`, so a falsy `before` skipped it
    without a word. MEASURED under the stub: 4,004 bytes written to `<tmp>/hero.glb` with
    plain Python, then this gate called with `before=export_target_snapshot(p)` REFUSES
    (`stale_target`), while `before=None`, `before={}` and `before={"existed": False}`
    each returned a PASS record carrying `bytes: 4004` and a sha256 for a file the process
    never wrote — the exact record F-6a9a0f72 was filed to stop. `result` is not disarmable
    the same way (an unreadable value becomes `status=None` and fails clause 1), so the
    asymmetry was in `before` alone; an optional-shaped argument IS a skip flag
    (F-abcb06a8), and the two wave-14 censuses read only the SIGNATURE and the export
    call's return value, never the `before=` argument at any of the nine call sites. So
    the falsy snapshot is now clause 0, `no_pre_export_snapshot`, and it KEYS ON THE VALUE
    — a mapping carrying an `existed` key whose value is a bool — never on the presence of
    the argument.
    """
    p = os.path.abspath(path)
    try:
        status = sorted(str(s) for s in result)
    except TypeError:
        status = None
    ev = {"gate": "GLB", "andon": "GateGlbWritten", "what": what, "path": p,
          "status": status, "before": before}
    # CLAUSE 0 - the snapshot itself. It runs FIRST, above the status clause, because a
    # caller that hands no snapshot has not measured the thing clause 4 rules on, and a
    # gate that answers anything at all in that state is answering about a run it cannot
    # see. `existed` must be a bool: `{"existed": None}` is a snapshot that was not taken.
    if (not isinstance(before, dict) or "existed" not in before
            or not isinstance(before.get("existed"), bool)):
        ev["clause"] = "no_pre_export_snapshot"
        raise GateGlbWritten(
            f"no pre-export snapshot was taken for {what} at {p}: `before` is "
            f"{before!r}, not an `export_target_snapshot()` record carrying a boolean "
            f"`existed`. The stale-target clause is the only one that can tell this "
            f"run's GLB from the PREVIOUS run's file at the same path, and every other "
            f"clause here passes on that file, so a falsy `before` would hand back a "
            f"byte count and a sha256 for a file this process never wrote", ev)
    # A DIAGNOSTIC, not a clause. A snapshot of a DIFFERENT path is a snapshot of a
    # different file, and clause 4 would then be comparing this export against something
    # it never overwrote. It rides the evidence rather than raising because one existing
    # fixture deliberately snapshots `<path>.absent` to obtain an `existed: False` record,
    # and that fixture is another domain's to move; a diagnostic and a gate are different
    # objects (CLAUDE.md).
    ev["snapshot_is_of_this_path"] = (before.get("path") == p)
    # CLAUSE 1 - the operator's own verdict, which this gate named and never read. The
    # shape is `rig_bake.py`'s `if 'FINISHED' not in result` on `bpy.ops.object.bake`.
    if status is None or "FINISHED" not in status:
        raise GateGlbWritten(
            f"the export of {what} to {p} did not report FINISHED; it returned "
            f"{status!r}. `bpy.ops.export_scene.gltf` returns an operator status set and "
            f"can return CANCELLED without raising, and an existing file at this path is "
            f"then the PREVIOUS run's GLB", ev)
    if not os.path.isfile(p):
        raise GateGlbWritten(
            f"{what} never reached disk at {p}. `bpy.ops.export_scene.gltf` returns an "
            f"operator status set and can return CANCELLED without raising, so a run that "
            f"exported nothing would otherwise name this file in its own record", ev)
    n = os.path.getsize(p)
    ev["bytes"] = n
    if n == 0:
        raise GateGlbWritten(
            f"{what} at {p} is zero bytes. A file that exists and holds nothing is the "
            f"shape a cancelled export leaves behind, and every consumer downstream reads "
            f"the path rather than the size", ev)
    # CLAUSE 4 - the weaker guard that costs nothing. A file whose size AND nanosecond
    # mtime are both what they were before the export is the file that was already there.
    after_mtime_ns = os.stat(p).st_mtime_ns
    ev["after"] = {"bytes": n, "mtime_ns": after_mtime_ns}
    # `before` is a validated snapshot by the time execution reaches here (clause 0), so
    # this reads the VALUE of `existed` and nothing about whether the caller passed one.
    if (before["existed"]
            and before.get("bytes") == n and before.get("mtime_ns") == after_mtime_ns):
        ev["clause"] = "stale_target"
        raise GateGlbWritten(
            f"{what} at {p} is byte-for-byte the file that was already there before this "
            f"export ran (same size, same mtime to the nanosecond). A manifest naming its "
            f"sha256 would describe a pairing that was never built together, and every "
            f"downstream instrument would measure that pairing", ev)
    digest = sha256_file(p)
    return {"path": p, "bytes": n, "sha256": digest, "status": status,
            "verdict": f"{what} is {n:,} bytes on disk"}


def validate_sitelist():
    """`sitelist.validate()`, with its refusal inside the `ArmatureError` family.

    The handler is `ValueError` and nothing broader, deliberately:
    `tests/test_rig_character_dispatch.py::test_nothing_between_the_landmark_solve_and_the
    _manifest_catches_a_gate` holds that the ONLY broad handlers in this file are the two in
    the `__main__` block, because a `FacingGate` caught anywhere else would never reach
    `halt.json` or the exit code. A first draft of this wrapper caught `ArmatureError` (to
    re-raise it) and `Exception`, and that census was right to refuse it. `sitelist.validate`
    documents `ValueError` in its own docstring, so that is the whole surface; the
    `isinstance` guard below keeps a typed refusal from the core intact even if it should
    ever arrive as a `ValueError` subclass.
    """
    try:
        sitelist.validate()
    except ValueError as exc:
        if isinstance(exc, ArmatureError):
            raise
        raise SiteListInvalid(
            f"the site registration table is inconsistent, so nothing built from it would "
            f"mean what its names say: {exc}",
            {"gate": None, "andon": "SiteListInvalid",
             "clause": "site_registration_invalid",
             "source": "sitelist.validate", "raised": type(exc).__name__,
             "problems": str(exc)}) from exc


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"glb": None, "out": None, "measure_only": False, "bands": 200,
            "name": "performer", "mode": "skeleton", "binding": "rigid",
            "envelope_radii": "measured"}
    for token in argv:
        if token == "--measure-only":
            args["measure_only"] = True
            continue
        key, _, value = token[2:].partition("=")
        key = key.replace("-", "_")
        if key not in args:
            raise ArmatureError(f"unknown argument {token!r}; known: {sorted(args)}")
        args[key] = int(value) if key == "bands" else value
    if not args["glb"] or not args["out"]:
        raise ArmatureError("usage: -- --glb=<path> --out=<dir> [--measure-only] [--bands=N]")
    return args


# --------------------------------------------------------------------------- scene


def fresh_scene(fps):
    """Empty the scene and set the frame rate BEFORE anything else happens.

    **The fps-ordering law, E03 closing Ruling 9.** `prepare()` imported a GLB before the
    frame rate was set, so a 33-key action authored at 16 fps landed on frames 1-49 at
    Blender's default 24 and the render captured two thirds of the arc. glTF stores key
    times in *seconds*; every conversion between seconds and frames in this process reads
    `scene.render.fps`, so it is set first, on an empty scene, and nothing that follows can
    be authored against the wrong one.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = PROBE_FRAMES
    scene.frame_set(1)
    return scene


def world_verts(ob, mesh=None):
    me = mesh if mesh is not None else ob.data
    n = len(me.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", flat)
    co = flat.reshape(n, 3)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return co @ m[:3, :3].T + m[:3, 3]


def evaluated_world_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        return world_verts(ev, me)
    finally:
        ev.to_mesh_clear()


def measure_subject(ob):
    """Premises 2 and 6, measured on import rather than inherited from the dispatch."""
    me = ob.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.edges.ensure_lookup_table()
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    edges = np.array([[e.verts[0].index, e.verts[1].index] for e in bm.edges], dtype=np.int64)
    bm.free()

    # Union-find over the edge graph: how many disconnected shells the skinning solve
    # actually has to spread heat across. This is the premise the dispatch handed over as
    # "67 interior shells", and it is measured here rather than carried.
    n = len(me.vertices)
    parent = np.arange(n, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    roots = np.array([find(i) for i in range(n)], dtype=np.int64)
    uniq, shell_id, sizes = np.unique(roots, return_inverse=True, return_counts=True)

    return {
        "object_name": ob.name,
        "vertices": n,
        "triangles": len(me.loop_triangles),
        "polygons": len(me.polygons),
        "edges": len(me.edges),
        "shells": int(len(uniq)),
        "non_manifold_edges": int(non_manifold),
        "boundary_edges": int(boundary),
        "watertight": bool(non_manifold == 0 and boundary == 0),
        "largest_shell_vertices": int(sizes.max()),
        "largest_shell_fraction": float(sizes.max() / n),
        "shells_over_1pct": int((sizes > 0.01 * n).sum()),
        "pre_existing_vertex_groups": len(ob.vertex_groups),
        "pre_existing_modifiers": [m.type for m in ob.modifiers],
        "matrix_world_is_identity": bool(ob.matrix_world == Matrix.Identity(4)),
    }, shell_id, sizes


def measure_joint_balls(ob, diagonal):
    """The subject's own sculpted ball-joints, found on a THROWAWAY welded copy.

    The mesh handed to the rig is never touched: `bmesh.from_mesh` reads into a private
    bmesh, the weld happens there, and it is freed without `to_mesh`. The balls come back as
    world-space points, which is all the skeleton needs — nothing downstream depends on the
    welded topology existing.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=BALL_WELD_FRACTION * diagonal)
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    parent = np.arange(n, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[b] = a
    labels = np.array([find(i) for i in range(n)], dtype=np.int64)
    co = np.empty((n, 3), dtype=np.float64)
    for i, v in enumerate(bm.verts):
        co[i] = v.co
    bm.free()

    m = np.array(ob.matrix_world, dtype=np.float64)
    world = co @ m[:3, :3].T + m[:3, 3]
    shells = joints.describe_shells(world, labels)
    return joints.candidate_balls(shells), shells


def build_armature(scene, marks, name):
    arm_data = bpy.data.armatures.new(f"{name}_armature")
    arm_obj = bpy.data.objects.new(f"{name}_rig", arm_data)
    scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    try:
        for b in sitelist.BONES:
            head, tail = marks[b.head], marks[b.tail]
            eb = arm_data.edit_bones.new(b.name)
            eb.head = Vector(head)
            eb.tail = Vector(tail)
            eb.roll = 0.0
            eb.use_deform = b.deform
            if b.parent is not None:
                eb.parent = made[b.parent]
                eb.use_connect = False
            made[b.name] = eb
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")

    # Blender deletes zero-length bones on leaving edit mode without raising. Gate N would
    # catch the result as a missing site; naming it here makes the evidence legible.
    lengths = {b.name: float(b.length) for b in arm_data.bones}
    return arm_obj, lengths


#: Weight quantisation for the procedural arm. Only the blend band carries fractional
#: weights — rigid vertices are exactly 1.0 — and Blender's armature modifier normalises by
#: the accumulated weight, so this cannot move the bind pose. Recorded because it is a
#: property of the arm, not an implementation detail.
RIGID_WEIGHT_QUANTISATION = 1e-3


def _parent_to(mesh_obj, arm_obj, kind):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type=kind)


def _set_envelopes(arm_obj, radii, distance_multiple):
    """Envelope radii from the MEASURED cross-section of the structure each bone runs through.

    Blender's defaults are absolute lengths — 0.1 head/tail radius, 0.25 envelope distance —
    on a figure 1.0 units tall. That is a global constant governing a local feature, and it
    is why the mechanism sweep measured a mean of 7.4 bone influences per vertex on this
    subject. Sized from the mesh instead; the multiple applied to the falloff is declared
    here rather than tuned against a coverage number.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    applied = {}
    try:
        for eb in arm_obj.data.edit_bones:
            r = radii.get(eb.name)
            if r is None:                       # the non-deforming facial markers
                eb.head_radius = eb.tail_radius = 0.0
                eb.envelope_distance = 0.0
                applied[eb.name] = {"deform": False, "head_radius": 0.0,
                                    "tail_radius": 0.0, "envelope_distance": 0.0}
                continue
            eb.head_radius = eb.tail_radius = float(r)
            eb.envelope_distance = float(r) * distance_multiple
            applied[eb.name] = {"deform": True, "head_radius": float(r),
                                "tail_radius": float(r),
                                "envelope_distance": float(r) * distance_multiple}
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    return applied


def _write_weights(mesh_obj, weights, quantisation):
    """Push computed weights into vertex groups.

    Rigid vertices (weight exactly 1.0) go in one call per bone; only the blend band is
    quantised, and it is the small minority. A per-vertex loop over 400k vertices would move
    the same numbers far more slowly.
    """
    groups = {g.name: g for g in mesh_obj.vertex_groups}
    written = 0
    for name, w in weights.items():
        group = groups.get(name)
        if group is None:
            raise ArmatureError(
                f"no vertex group named {name!r} on the mesh; the armature was parented "
                f"without empty groups and there is nowhere to write weights"
            )
        full = np.flatnonzero(w >= 1.0)
        if len(full):
            group.add(full.tolist(), 1.0, "REPLACE")
            written += len(full)
        partial = np.flatnonzero((w > 0.0) & (w < 1.0))
        if len(partial):
            q = np.round(w[partial] / quantisation) * quantisation
            for value in np.unique(q):
                sel = partial[q == value]
                group.add(sel.tolist(), float(value), "REPLACE")
                written += len(sel)
    return written


def normalise_weights(mesh_obj):
    """Make every weighted vertex's influences sum to exactly 1.

    Bone heat does not guarantee it. MEASURED on this subject before normalisation:
    **20,171 of 39,707 vertices summed below 0.999**, the lowest at **0.8961**. A vertex whose
    weights sum to 0.90 is skinned at 90 % — it lags the bone it belongs to by a tenth of
    every motion, which reads as a soft, rubbery joint rather than as an obvious bug.

    ``vertex_group_normalize_all`` with ``lock_active=False`` divides each vertex's weights by
    their sum. Vertices with no weight at all are left alone, so this cannot invent a binding
    where bone heat found none — which is exactly the failure Gate P's liveness clause exists
    to catch, and it must stay catchable.
    """
    def _sums(table):
        # read_weights returns {group name: per-vertex array}, not a matrix.
        return (np.sum(list(table.values()), axis=0) if table
                else np.zeros(len(mesh_obj.data.vertices)))

    sums_before = _sums(read_weights(mesh_obj, len(mesh_obj.data.vertices)))
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    sums_after = _sums(read_weights(mesh_obj, len(mesh_obj.data.vertices)))
    weighted = sums_after > 1e-6
    return {
        "operator": "bpy.ops.object.vertex_group_normalize_all(lock_active=False)",
        "vertices": int(len(sums_after)),
        "unweighted_left_alone": int((~weighted).sum()),
        "before": {"min": float(sums_before.min()), "mean": float(sums_before.mean()),
                   "below_0.999": int((sums_before < 0.999).sum())},
        "after": {"min": float(sums_after[weighted].min()) if weighted.any() else 0.0,
                  "mean": float(sums_after[weighted].mean()) if weighted.any() else 0.0,
                  "max": float(sums_after[weighted].max()) if weighted.any() else 0.0,
                  "below_0.999": int((sums_after[weighted] < 0.999).sum()),
                  "above_1.001": int((sums_after[weighted] > 1.001).sum())},
    }


def gate_objects_registered(scene, subject, armature):
    """Nothing rides along into the export that nobody registered.

    Gate N refuses an unregistered BONE name; this is the same andon for OBJECTS, and it
    exists because a decoy leaked once. An 80-face ``Icosphere`` reached a delivered GLB and
    this round's sheet mistook it for the character, reporting that the arc had not survived.
    Whether it originates in the file or in Blender's importer is recorded by the gate rather
    than assumed: the evidence lists every object with its collection and render visibility.
    """
    registered = {subject.name, armature.name}
    # WAVE 16, F-94a7d14d -- THE CANONICAL WALK. This gate decided render visibility with
    # `ob.hide_render or any(c.hide_render for c in ob.users_collection)`, a ONE-LEVEL
    # predicate, where `blender_scene.render_visible_meshes` answers the same question
    # through `collection_render_flags`, which walks the LAYER-collection tree and picks up
    # both `exclude` and an ancestor's `hide_render` (`blender_scene.py:165-171`: plain
    # collection flags do not carry `exclude`). MEASURED under the stub on two scenes: a
    # mesh in `Debris` nested inside `Props(hide_render=True)`, and a mesh in a collection
    # whose layer-collection is `exclude=True`. `render_visible_meshes` returns [] for
    # both; the one-level expression returned `effectively_hidden = False` for both. So a
    # decoy parked one collection deeper than the importer's own `glTF_not_exported` was
    # listed as a STRAY and this gate halted the central export on a scene the renderer
    # would draw correctly -- a false andon on the tool whose halt is the most expensive in
    # the tree. One question, one implementation.
    reachable, hidden_collections = blender_scene.collection_render_flags(scene)
    drawable = reachable - hidden_collections
    seen = []
    for ob in scene.objects:
        cols = [c.name for c in ob.users_collection]
        hidden = ob.hide_render or not any(c in drawable for c in cols)
        seen.append({"name": ob.name, "type": ob.type, "hide_render": bool(ob.hide_render),
                     "collections": cols,
                     "effectively_hidden": bool(hidden)})
    strays = [o for o in seen
              if o["name"] not in registered and not o["effectively_hidden"]
              and o["type"] in {"MESH", "ARMATURE"}]
    record = {"gate": "OBJ", "registered": sorted(registered), "objects": seen,
              "strays": strays,
              # WHICH visibility notion this gate ruled on, stated rather than assumed --
              # the other half of F-94a7d14d: `export_rigged`'s operator arguments name
              # `use_selection=False` and no visibility key at all, so what the exporter
              # does with a hidden object is not what this exemption reads.
              "visibility": ("blender_scene.collection_render_flags: ob.hide_render OR no "
                             "users_collection reachable in the view layer and not hidden "
                             "from render (ancestor hide_render and exclude included)"),
              "collections_reachable": sorted(reachable),
              "collections_hidden": sorted(hidden_collections),
              "verdict": (f"{len(seen)} object(s) in the scene, none unregistered and "
                          f"render-visible" if not strays else "STRAY OBJECTS")}
    if strays:
        raise GateObjects(
            f"the export would carry {len(strays)} object(s) nobody registered: "
            f"{[o['name'] for o in strays]}. Gate N refuses an unregistered bone; an "
            f"unregistered object is the same defect one level up, and one already leaked "
            f"into a delivered GLB.",
            record)
    return record


def apply_binding(mesh_obj, arm_obj, mode, source, radii, envelope_distance_multiple=1.0,
                  envelope_radii="measured"):
    """Bind the mesh by one named route. Returns (seconds, a record of what was applied)."""
    t0 = time.time()
    if mode == "auto":
        # FALSIFIED on this subject in round 1. Kept runnable, with the reason attached.
        _parent_to(mesh_obj, arm_obj, "ARMATURE_AUTO")
        rec = {"binding": "auto", "operator": "parent_set(ARMATURE_AUTO)",
               "note": ("Blender bone-heat weighting. Measured on this subject to produce "
                        "ZERO weights across all 17 deform groups — see E07 round 1.")}
    elif mode == "envelope":
        # TWO configurations, both runnable, because they are genuinely different arms and
        # the difference was measured rather than argued:
        #
        #   measured — head/tail radius from the structure's own cross-section, falloff a
        #     declared multiple of it. 1.88 bone influences per vertex, and **1,162 of
        #     399,140 vertices (0.29 %) left unweighted**, all in the fingers and toes that
        #     stick out past every envelope. glTF then adds a `neutral_bone` to hold them
        #     and **Gate N fires** on the unregistered name.
        #   default — Blender's own absolute radii, untouched. 100 % coverage, and 9.86
        #     influences per vertex against a weight sum of 7.7.
        #
        # The advisor's ruling named "ARMATURE_ENVELOPE (measured 100% coverage)", which is
        # the DEFAULT configuration as the mechanism sweep ran it. This seat substituted
        # measured radii on the global-constant law without flagging it first; both are run
        # and reported rather than one being quietly chosen.
        if envelope_radii == "measured":
            applied = _set_envelopes(arm_obj, radii, envelope_distance_multiple)
            source_note = ("measured cross-section of the structure each bone runs through "
                           "(landmarks.bone_radii); falloff a declared multiple of it")
        elif envelope_radii == "default":
            applied = {b.name: {"deform": bool(b.use_deform),
                                "head_radius": float(b.head_radius),
                                "tail_radius": float(b.tail_radius),
                                "envelope_distance": float(b.envelope_distance)}
                       for b in arm_obj.data.bones}
            source_note = ("Blender's own defaults, untouched — absolute lengths on a figure "
                           "1.0 units tall, which is a global constant governing a local "
                           "feature and is recorded as such")
        else:
            raise GateMode(
                f"unknown --envelope-radii={envelope_radii!r}; known: measured, default",
                {"envelope_radii": envelope_radii, "known": ["measured", "default"]})
        _parent_to(mesh_obj, arm_obj, "ARMATURE_ENVELOPE")
        rec = {
            "binding": "envelope", "operator": "parent_set(ARMATURE_ENVELOPE)",
            "envelope_radii": envelope_radii,
            "radii_source": source_note,
            "envelope_distance_multiple_of_bone_radius":
                envelope_distance_multiple if envelope_radii == "measured" else None,
            "envelopes_applied": applied,
            "smoothing_applied": False,
            "smoothing_note": ("No vertex-group smoothing was run. Envelope weights are "
                               "already a distance falloff, and whether an additional blur "
                               "improves the read is a judgement this seat does not make."),
        }
    elif mode == "rigid":
        _parent_to(mesh_obj, arm_obj, "ARMATURE_NAME")
        bones = [{"name": b.name, "head": tuple(b.head_local), "tail": tuple(b.tail_local),
                  "parent": b.parent.name if b.parent else None}
                 for b in arm_obj.data.bones if b.use_deform]
        weights, diag = binding.rigid_segment_weights(source, bones, radii)
        written = _write_weights(mesh_obj, weights, RIGID_WEIGHT_QUANTISATION)
        rec = {"binding": "rigid",
               "operator": "parent_set(ARMATURE_NAME) + computed weights",
               "assignment": diag, "weight_entries_written": written,
               "weight_quantisation": RIGID_WEIGHT_QUANTISATION,
               "radii_source": "measured cross-section (landmarks.bone_radii)"}
    else:
        raise GateMode(f"unknown binding {mode!r}; known: auto, envelope, rigid",
                       {"binding": mode, "known": ["auto", "envelope", "rigid"]})
    return time.time() - t0, rec


def read_weights(ob, n_verts):
    """Per-vertex-group weight arrays, plus the sums that a failed heat solve shows up in."""
    idx_to_name = {g.index: g.name for g in ob.vertex_groups}
    w = {name: np.zeros(n_verts, dtype=np.float64) for name in idx_to_name.values()}
    for i, v in enumerate(ob.data.vertices):
        for ge in v.groups:
            name = idx_to_name.get(ge.group)
            if name is not None:
                w[name][i] = ge.weight
    return w


def bone_table(arm_obj):
    return {b.name: {"head": tuple(b.head_local), "tail": tuple(b.tail_local),
                     "roll": 0.0, "parent": b.parent.name if b.parent else None,
                     "use_deform": bool(b.use_deform)}
            for b in arm_obj.data.bones}


def weld_seam_splits(mesh_obj):
    """Merge the vertices glTF split at every UV and normal seam. **Not optional.**

    MEASURED 2026-08-11, and it overturns the headline of E03. A glTF file stores one vertex
    per (position, uv, normal) combination, so a mesh of 39,707 vertices comes back as
    **164,152** with **164,152 boundary edges** — every UV island edge is a hole as far as
    Blender is concerned. Bone heat solves a diffusion problem on that surface and cannot:
    binding the file as imported gives **0 of 17 bones any weight and leaves 100 % of
    vertices unweighted**, which is exactly the result E03 recorded and attributed to the
    character. Welding the coincident vertices first, on the same file, gives **17 of 17 bones
    live, 0 % unweighted, weight sum 0.9909, 1.69 influences per vertex**.

    The weld is safe for the atlas: Blender stores UVs **per loop**, not per vertex, so
    merging two coincident vertices that carry different UVs keeps both faces' coordinates.
    Verified by rendering the welded mesh textured.
    """
    import bmesh as _bmesh
    src = world_verts(mesh_obj)
    # SIBLING CARRIED under F-6a9a0f72 (wave 14). Gate SCALE, at the fourth of six
    # bbox-diagonal derivations -- the weld distance below is a fraction of this number.
    diagonal, _lo, _hi = subject_scale(src, "atlas_safe_weld")
    bm = _bmesh.new()
    bm.from_mesh(mesh_obj.data)
    before_v = len(bm.verts)
    before_boundary = sum(1 for e in bm.edges if e.is_boundary)
    _bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6 * diagonal)
    after_boundary = sum(1 for e in bm.edges if e.is_boundary)
    after_nm = sum(1 for e in bm.edges if not e.is_manifold)
    rec = {"verts_before": before_v, "verts_after": len(bm.verts),
           "verts_merged": before_v - len(bm.verts),
           "boundary_edges_before": before_boundary, "boundary_edges_after": after_boundary,
           "non_manifold_edges_after": after_nm,
           "closed_manifold_after": after_boundary == 0 and after_nm == 0,
           "merge_distance": 1e-6 * diagonal,
           "why": "glTF splits a vertex per (position, uv, normal); bone heat cannot solve "
                  "on a surface whose every UV island edge is a boundary"}
    bm.to_mesh(mesh_obj.data)
    bm.free()
    mesh_obj.data.update()
    return rec


def build_pass(glb_path, name, bands, label, bind, envelope_radii="measured"):
    """One complete build, from a fresh scene to a rig.

    `bind` is REQUIRED and has no default. MEASURED 2026-09-04: it defaulted to `True`,
    and `True` is the one value `apply_binding` cannot accept -- its third positional
    parameter is `mode`, dispatched on "auto" / "envelope" / "rigid", with an `else` that
    raises `ArmatureError("unknown binding True; ...")`. The `--measure-only` path was the
    only caller that let the default through, so the documented invocation could not run
    at all and halted naming a binding mode the executor never asked for.

    With `bind=False` the mesh is never parented to the armature: the skeleton is placed and
    exported, and nothing is attached to it. That is the **skeleton-approval** mode the
    Director gated the experiment at — nothing moves forward until he approves the
    skeleton. Gate P's liveness clause deliberately does not run there, because there is no
    binding for it to be about; a liveness reading on an unbound mesh would be a check
    reporting on a thing that does not exist yet.
    """
    scene = fresh_scene(PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(meshes) != 1:
        raise GateSubject(
            f"expected exactly one mesh object in the subject, found {len(meshes)}: "
            f"{[o.name for o in meshes]}. Which one carries the character is a question "
            f"this tool will not answer by picking the biggest",
            {"glb": glb_path, "mesh_objects": [o.name for o in meshes],
             "armatures": [o.name for o in armatures]}
        )
    mesh_obj = meshes[0]
    weld = weld_seam_splits(mesh_obj)
    premise2 = {
        "pre_existing_armatures": [o.name for o in armatures],
        "pre_existing_empties": [o.name for o in bpy.data.objects if o.type == "EMPTY"],
        "pre_existing_actions": [a.name for a in bpy.data.actions],
        "carries_a_rig": bool(armatures) or any(o.type == "EMPTY" for o in bpy.data.objects),
    }
    premise6, shell_id, shell_sizes = measure_subject(mesh_obj)

    source = world_verts(mesh_obj)
    # F-940b0800: the refusal sits HERE, above `landmarks.derive` and
    # `measure_joint_balls`, because both consume this array and Gate D — the first gate
    # that sees geometry on the `bind=False` skeleton route — reads a tolerance scaled by
    # this number. See `subject_scale`.
    diagonal, lo, hi = subject_scale(source, label)

    t0 = time.time()
    lm = landmarks.derive(source, n_bands=bands)
    t_landmarks = time.time() - t0

    # The subject's own sculpted ball-joints, and the pivots moved onto them. Placement by
    # proportion is the fallback for sites that carry no marker, never the default: this
    # mannequin sculpts a ball at every limb joint and those balls are the ground truth.
    t0 = time.time()
    balls, shells = measure_joint_balls(mesh_obj, diagonal)
    heuristic_marks = dict(lm["landmarks"])
    snapped, offsets = joints.snap_sites_to_balls(lm, balls)
    lm["landmarks"] = snapped
    t_balls = time.time() - t0
    ruling = joints.verdict(offsets)

    arm_obj, bone_lengths = build_armature(scene, snapped, name)
    radii = landmarks.bone_radii(lm, sitelist.BONES)

    gate_p, weights, t_skin, bind_record, normalisation = None, {}, None, None, None
    if bind:
        t_skin, bind_record = apply_binding(mesh_obj, arm_obj, bind, source, radii,
                                            envelope_radii=envelope_radii)
        # Normalise BEFORE liveness and Gate P, so both read the weights that ship. This
        # cannot manufacture a binding: a vertex with no influences is left untouched, and
        # the liveness clause below still fails on a dead bind.
        normalisation = normalise_weights(mesh_obj)
        # Liveness BEFORE Gate P, so Gate P's reading is known to be about a bound mesh and
        # not about an evaluation that never carried the modifier. Restored immediately; no
        # keyframe exists yet, so nothing survives the restore.
        bpy.context.view_layer.update()
        rest_before = evaluated_world_verts(mesh_obj)
        pb = arm_obj.pose.bones["shoulder.L"]
        saved = pb.matrix_basis.copy()
        pb.matrix_basis = Matrix.Rotation(math.radians(30.0), 4, "Y")
        bpy.context.view_layer.update()
        probed = evaluated_world_verts(mesh_obj)
        pb.matrix_basis = saved
        bpy.context.view_layer.update()

        liveness = rig_gates.gate_p_evaluation_is_live(rest_before, probed, diagonal)
        bound = evaluated_world_verts(mesh_obj)
        gate_p = rig_gates.gate_p_rest_pose(source, bound, diagonal)
        gate_p["evaluation_liveness"] = liveness
        weights = read_weights(mesh_obj, len(source))

    fingerprint = rig_gates.rig_fingerprint(bone_table(arm_obj), weights, len(source))

    return {
        "label": label, "scene": scene, "mesh": mesh_obj, "armature": arm_obj,
        "source": source, "diagonal": diagonal, "landmarks": lm, "weights": weights,
        "fingerprint": fingerprint, "gate_p": gate_p, "premise2": premise2,
        "weld_on_import": weld, "normalisation": normalisation,
        "premise6": premise6, "shell_id": shell_id, "shell_sizes": shell_sizes,
        "bone_lengths": bone_lengths, "bbox_lo": lo.tolist(), "bbox_hi": hi.tolist(),
        "heuristic_landmarks": heuristic_marks, "joint_balls": balls, "shells": shells,
        "offset_table": offsets, "placement_ruling": ruling, "bound": bind or False,
        "bone_radii": radii, "binding_record": bind_record,
        "timings": {"landmarks_s": t_landmarks, "joint_balls_s": t_balls,
                    "bind_s": t_skin},
    }


# ----------------------------------------------------------------------- the probe


def author_probe(ctx):
    """E03's arc on a bone: rotate the +X-side arm about +Y, 0 -> 90 deg, 33 keys @ 16 fps.

    The rotation is E03's, applied to a pose bone instead of a joined cylinder group, so
    E08 compares character-control against wire-control on the same authored transform.
    What differs is the rest pose it acts on: E03's wire figure was T-posed, so the arc
    read as horizontal -> overhead; this character stands with his arms down, so the same
    rotation reads as arm-at-side -> arm-horizontal. Reported, not silently rescaled.

    `matrix_basis` is computed in closed form rather than assigned through `pose_bone.matrix`,
    which would need a depsgraph settle per frame — 33 evaluations of a 400k-vertex armature
    deform, and a value that depends on when the settle happened is not a recipe.
    """
    arm_obj, scene = ctx["armature"], ctx["scene"]
    arc = posearc.resolve_arc(PROBE_ARC)
    readout = posearc.arc_readout(arc, PROBE_FRAMES, PROBE_START_DEG, PROBE_END_DEG)

    left_sign = ctx["landmarks"]["facing"]["left_x_sign"]
    side = "L" if left_sign * sitelist.PROBE_ARC_SIDE_X_SIGN > 0 else "R"
    bone_name = f"shoulder.{side}"

    bpy.context.view_layer.objects.active = arm_obj
    pb = arm_obj.pose.bones[bone_name]
    pb.rotation_mode = "QUATERNION"
    rest = arm_obj.data.bones[bone_name].matrix_local.copy()
    pivot = rest.to_translation()
    to_pivot = Matrix.Translation(pivot)
    from_pivot = Matrix.Translation(-pivot)
    rest_inv = rest.inverted()

    keyed = []
    for i in range(PROBE_FRAMES):
        theta = posearc.angle_at_frame(i, PROBE_FRAMES, PROBE_START_DEG, PROBE_END_DEG)
        applied = arc["sign"] * theta
        rot = Matrix.Rotation(math.radians(applied), 4, arc["axis"])
        target = to_pivot @ rot @ from_pivot @ rest
        pb.matrix_basis = rest_inv @ target
        pb.keyframe_insert(data_path="rotation_quaternion", frame=1 + i)
        pb.keyframe_insert(data_path="location", frame=1 + i)
        keyed.append({"frame": 1 + i, "index": i, "angle_deg": round(theta, 9),
                      "applied_deg": round(applied, 9)})

    action = arm_obj.animation_data.action if arm_obj.animation_data else None
    n_fcurves = 0
    for fc in _action_fcurves(action) if action else []:
        n_fcurves += 1
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    scene.frame_set(1)
    bpy.context.view_layer.update()
    return {
        "arc": PROBE_ARC, "bone": bone_name,
        "which_arm_is_on_plus_x": ("the character's LEFT" if left_sign > 0
                                   else "the character's RIGHT"),
        "axis": arc["axis"], "sign": arc["sign"],
        "start_deg": PROBE_START_DEG, "end_deg": PROBE_END_DEG,
        "frames": PROBE_FRAMES, "fps": PROBE_FPS,
        "scene_fps_at_authoring": scene.render.fps,
        "action": action.name if action else None,
        "n_fcurves": n_fcurves, "readout": readout, "keys": keyed,
        "note": ("The authored transform is E03's exactly. The rest pose it acts on is not: "
                 "E03's wire subject was T-posed so the arc read horizontal -> overhead; "
                 "this character stands with his arms down so the same rotation reads "
                 "arm-at-side -> arm-horizontal."),
    }


def _action_fcurves(action):
    """Both Action APIs. Blender 5.2's slotted actions replaced the flat `fcurves` list
    with layers -> strips -> channelbags; the attribute's absence is the discriminator,
    measured on this rig 2026-08-10 in `make_test_armature.py` and reused rather than
    re-derived."""
    flat = getattr(action, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                out.extend(cbag.fcurves)
    return out


# ------------------------------------------------------------------- diagnostics


def deformation_diagnostics(ctx, probe):
    """Per-structure displacement under the probe arc. DIAGNOSTIC — gates nothing.

    Reported per bone rather than as one number for the figure, because a global statistic
    over a character is exactly the quantity that hides a shredded shoulder inside an
    otherwise still body: 400k vertices barely move, so any mesh-wide mean is dominated by
    the parts that were never asked to.
    """
    scene, mesh_obj = ctx["scene"], ctx["mesh"]
    weights = ctx["weights"]
    n = len(ctx["source"])
    diagonal = ctx["diagonal"]

    scene.frame_set(1)
    bpy.context.view_layer.update()
    rest = evaluated_world_verts(mesh_obj)
    scene.frame_set(PROBE_FRAMES)
    bpy.context.view_layer.update()
    end = evaluated_world_verts(mesh_obj)
    d = np.linalg.norm(end - rest, axis=1)

    stack = np.zeros((len(weights), n), dtype=np.float64)
    names = sorted(weights)
    for i, name in enumerate(names):
        stack[i] = weights[name]
    total = stack.sum(axis=0)
    dominant = np.argmax(stack, axis=0)
    dominant[total <= 0] = -1

    per_bone = {}
    for i, name in enumerate(names):
        sel = dominant == i
        cnt = int(sel.sum())
        rec = {"vertices_dominated": cnt,
               "vertices_with_any_weight": int((stack[i] > 0).sum()),
               "mean_weight_where_present": float(stack[i][stack[i] > 0].mean())
               if (stack[i] > 0).any() else 0.0}
        if cnt:
            dd = d[sel]
            rec.update({
                "displacement_max": float(dd.max()),
                "displacement_mean": float(dd.mean()),
                "displacement_p95": float(np.percentile(dd, 95)),
                "displacement_max_frac_of_diagonal": float(dd.max() / diagonal),
            })
        per_bone[name] = rec

    unweighted = int((total <= 1e-9).sum())
    short = int((total < 0.999).sum())
    over = int((total > 1.001).sum())

    shell_id, shell_sizes = ctx["shell_id"], ctx["shell_sizes"]
    n_shells = len(shell_sizes)
    split = 0
    for s in range(n_shells):
        sel = shell_id == s
        if sel.sum() < 2:
            continue
        if len(np.unique(dominant[sel])) > 1:
            split += 1

    return {
        "unit": "world units (the subject stands 1.0 tall)",
        "bbox_diagonal": diagonal,
        "frames_compared": [1, PROBE_FRAMES],
        "probe_bone": probe["bone"],
        "per_bone": per_bone,
        "weight_sums": {
            "vertices_total": n,
            "vertices_with_no_weight_at_all": unweighted,
            "vertices_with_weight_sum_below_0.999": short,
            "vertices_with_weight_sum_above_1.001": over,
            "min_weight_sum": float(total.min()),
            "mean_weight_sum": float(total.mean()),
            "note": ("A partially failed bone-heat solve shows up here and nowhere else. "
                     "Rest-pose identity is Gate P's business; these are the sums that "
                     "would break it."),
        },
        "shells": {
            "n_shells": n_shells,
            "shells_spanning_more_than_one_dominant_bone": split,
            "note": ("A shell weighted to a different bone than the skin around it is what "
                     "pushes an interior shard through the surface when the pose changes. "
                     "Counted, not judged."),
        },
        "whole_mesh": {
            "displacement_max": float(d.max()),
            "displacement_mean": float(d.mean()),
            "vertices_moving_more_than_1pct_of_diagonal":
                int((d > 0.01 * diagonal).sum()),
            "note": ("Present for completeness and deliberately not headline: a mesh-wide "
                     "mean over a figure where only one arm was asked to move is dominated "
                     "by the parts that were not."),
        },
    }


# ----------------------------------------------------------------------- export


def qualify_truncated_round_trip(ev):
    """Gate P's round-trip evidence, with a truncated probe SAID rather than buried.

    MEASURED 2026-09-04 (F-2d1fd05e). `rig_gates.gate_p_round_trip_positions` caps the
    nearest-neighbour probe at `max_probe`; when the cap bites it writes
    `probe_truncated_at` into the evidence, keeps `pts[:max_probe]` — `np.unique`'s
    lexicographic order, i.e. the smallest-x positions — and still reaches the verdict
    `"positions agree within <threshold>"`. A repo-wide grep for `probe_truncated_at`
    returned exactly one hit: the gate's own write. No tool, no test and no doc read it.
    `rig_character` embeds the whole evidence dict into the manifest under
    `gates.P_rest_pose_round_trip`, so the key IS in the file when it fires — sitting
    beside an unqualified pass verdict, with neither the printed OK line nor the manifest's
    summary fields mentioning it.

    This does not re-run the comparison and does not move a measurement. It rewrites the
    verdict so a reader cannot mistake a comparison made over a prefix of the difference
    set for a comparison made over all of it — the `NOT YET RUN` convention this file
    already uses three times in the same manifest, applied to a partial clause.

    ROUTED, and landed in the same wave: core-gates' half of this finding makes Gate P
    REFUSE a probe it cannot finish rather than return a truncated pass, so on the merged
    tree this function is the second line and should never fire — a truncated comparison
    arrives here as a `GatePRestPose` halt carrying `probe_truncated_at`, and the halt
    contract exits 2 with the evidence. It stays because the shape it guards against (a
    partial clause reaching a manifest wearing an unqualified verdict) is the one this
    file's manifest is read for, and a gate that changes its mind later must not silently
    re-open it.
    """
    if not isinstance(ev, dict) or "probe_truncated_at" not in ev:
        return ev
    rec = dict(ev)
    cap = rec["probe_truncated_at"]
    differing = (int(rec.get("positions_only_in_source", 0))
                 + int(rec.get("positions_only_in_roundtrip", 0)))
    rec["verdict_before_qualification"] = rec.get("verdict")
    rec["verdict"] = (
        f"TRUNCATED — the nearest-neighbour probe compared at most {cap} of the "
        f"{differing} differing position(s), taken in lexicographic order, so "
        f"{rec.get('max_deviation')} is the worst deviation over that PREFIX and not over "
        f"the difference set. This clause is NOT a pass over the whole surface.")
    rec["probe_truncated_reason"] = (
        f"max_probe={cap} was passed explicitly by rig_character "
        f"(ROUND_TRIP_MAX_PROBE); the difference set is larger than the cap")
    return rec


def export_rigged(ctx, probe, out_path, animated=True):
    """Export, then Gate N on the RE-IMPORTED result. Raises before any manifest exists.

    The re-import also re-reads the mesh, so Gate P's fidelity clause runs on the round trip
    itself: whatever else the exporter did, the vertices a consumer loads must be the
    vertices that went in. In skeleton mode that is the *whole* of the rest-pose path,
    because nothing is bound — see `build_pass`.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wanted = {
        "filepath": out_path, "export_format": "GLB", "use_selection": False,
        "export_yup": True, "export_animations": animated,
        "export_frame_range": animated,
        "export_animation_mode": "ACTIONS", "export_skins": True,
        # export_def_bones=True would drop every non-deforming marker and fire Gate N.
        "export_def_bones": False, "export_apply": False, "export_materials": "EXPORT",
    }
    gate_obj = gate_objects_registered(ctx["scene"], ctx["mesh"], ctx["armature"])
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in wanted.items() if k in props}
    dropped = sorted(set(wanted) - set(kwargs))
    # WAVE 14, F-6a9a0f72: snapshot before, status set captured. This is the export whose
    # manifest is the tree's central artefact -- a PASS record here names the sha256 and
    # byte count every downstream instrument measures against.
    before_glb = export_target_snapshot(out_path)
    export_result = bpy.ops.export_scene.gltf(**kwargs)
    written = gate_glb_written(out_path, result=export_result, before=before_glb,
                               what="the rigged GLB")

    # Re-import into a throwaway scene and read the names a consumer would actually get.
    fresh_scene(PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=out_path)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    reimported = sorted(b.name for a in arms for b in a.data.bones)
    gate_n_post = rig_gates.gate_n_names(reimported, sitelist.ALL_NAMES,
                                         "the re-imported exported GLB")

    # MEASURED 2026-08-11, and it was a gate silently not running. Selecting the re-imported
    # subject by `type == "MESH"` returns TWO objects: `geometry_0` and an `Icosphere` — the
    # decoy Blender's glTF importer drops into its hidden `glTF_not_exported` collection,
    # the same decoy E01's G4 fired on. The first version of this code skipped Gate P when
    # the count was not 1, so the round-trip clause reported `null` and the manifest carried
    # a gate that had quietly declined to run. Selection is now render-visibility, and an
    # ambiguous subject **raises** rather than returning None: a gate that opts out is worse
    # than one that fails, because nothing downstream can tell the difference.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(bpy.context.scene, meshes)
    if len(visible) != 1:
        raise GateSubject(
            f"the re-imported export presents {len(visible)} render-visible mesh object(s) "
            f"({[o.name for o in visible]}, from {[o.name for o in meshes]}); Gate P's "
            f"round-trip clause cannot say which one is the subject, and guessing would "
            f"make it report on geometry nobody asked about",
            {"glb": out_path, "mesh_objects_all": [o.name for o in meshes],
             "mesh_objects_render_visible": [o.name for o in visible]}
        )
    # `max_probe` passed EXPLICITLY — see ROUND_TRIP_MAX_PROBE for why the choice is stated
    # here rather than inherited from the gate's declared default.
    gate_p_round_trip = qualify_truncated_round_trip(
        rig_gates.gate_p_round_trip_positions(
            ctx["source"], world_verts(visible[0]), ctx["diagonal"],
            max_probe=ROUND_TRIP_MAX_PROBE))
    actions = [a.name for a in bpy.data.actions]
    return {
        "export_kwargs": {k: v for k, v in kwargs.items() if k != "filepath"},
        "requested_but_not_supported_by_this_blender": dropped,
        "reimported_armatures": [a.name for a in arms],
        "reimported_bone_names": reimported,
        "reimported_mesh_objects": [o.name for o in meshes],
        "reimported_actions": actions,
        "gate_n_post": gate_n_post, "gate_obj": gate_obj,
        "gate_p_round_trip": gate_p_round_trip,
        # F-9b2d4106: the export reached disk and is not zero bytes, recorded rather than
        # assumed. The re-import below it would raise on an ABSENT file, but not on an
        # empty one, and nothing published the byte count it confirmed.
        "gate_glb_written": written,
    }


def unbound_determinism_record(gate_d, fp_a, fp_b, expect_weights=None):
    """Gate D's evidence, with its weights clause written NOT YET RUN when there are none.

    MEASURED 2026-09-04. On the skeleton-only route both `build_pass` calls pass
    `bind=False`, so `weights` keeps the `{}` it starts as and `rig_gates.rig_fingerprint`
    stores an empty weight map in BOTH fingerprints. `gate_d_determinism` then walks its
    weight clause over nothing -- `set(wa) != set(wb)` is `set() != set()`, the loop never
    executes, and `worst_weight_delta` is written `{group: null, max_abs: 0.0,
    n_differing: 0}`: a zero indistinguishable from the zero a perfect agreement produces.
    The gate returned "two builds agree on bones, hierarchy and weights" and `run_skeleton`
    wrote that string into `skeleton_manifest.json` under `gates.D_determinism`.

    The gate is NOT vacuous here -- its bones clause compares heads, tails, rolls, parents
    and deform flags across all 22 bones, which is the whole content of a skeleton build.
    Only the weights clause and the verdict string over-claim. The same manifest already
    writes `P_evaluation_liveness`, `probe_action` and `deformation_diagnostics` as NOT YET
    RUN / NOT AUTHORED with a reason; this is that convention applied to the one clause
    that reported agreement instead.

    `expect_weights=False` is the caller DECLARING that nothing was bound. Declaring it
    over a pair that carries weights raises, because that would erase a real comparison.
    """
    has_weights = bool(fp_a.get("weights")) or bool(fp_b.get("weights"))
    if expect_weights is False and has_weights:
        raise ArmatureError(
            f"the caller declared this build unbound, but the fingerprints carry weight "
            f"groups ({sorted(set(fp_a.get('weights', {})) | set(fp_b.get('weights', {})))[:8]}). "
            f"Rewriting the weights clause as NOT YET RUN would delete a comparison that "
            f"actually ran")
    if has_weights:
        return gate_d

    rec = dict(gate_d)
    rec["verdict"] = "two builds agree on bones and hierarchy"
    rec["weights_clause"] = {
        "verdict": "NOT YET RUN",
        "reason": ("nothing is bound in skeleton mode, so both fingerprints carry an empty "
                   "weight map and the clause compared nothing. The zero in "
                   "worst_weight_delta is an absence, not an agreement."),
        "worst_weight_delta_as_reported": gate_d.get("worst_weight_delta"),
    }
    rec["worst_weight_delta"] = None
    return rec


def run_skeleton(args, out_dir, source_sha, started):
    """Skeleton-approval mode. Places the pivots, gates the names, exports, and stops.

    **Nothing is bound.** The Director gated the experiment here — nothing moves forward
    until he approves the skeleton — so the binding arms do not run and Gate P's liveness
    clause is NOT YET RUN by design, not by omission.
    """
    first = build_pass(args["glb"], args["name"], args["bands"], "determinism-probe",
                       bind=False)
    fp_first, offsets_first = first["fingerprint"], first["offset_table"]
    del first

    ctx = build_pass(args["glb"], args["name"], args["bands"], "kept", bind=False)
    gate_d = unbound_determinism_record(
        rig_gates.gate_d_determinism(fp_first, ctx["fingerprint"], ctx["diagonal"]),
        fp_first, ctx["fingerprint"], expect_weights=False)
    gate_n_pre = rig_gates.gate_n_names(
        [b.name for b in ctx["armature"].data.bones], sitelist.ALL_NAMES,
        "the built armature, before export")

    # F-244b2ad5: both `build_pass` calls above refuse an ambiguous or non-finite subject
    # and neither needs a directory; this is the route whose only artefact the Director
    # approves the skeleton on. Created here, below the last refusal.
    os.makedirs(out_dir, exist_ok=True)

    out_glb = os.path.join(out_dir, f"{args['name']}_skeleton.glb")
    export = export_rigged(ctx, None, out_glb, animated=False)

    manifest = {
        "tool": "rig_character", "tool_version": TOOL_VERSION, "mode": "skeleton",
        "tool_sha256": _tool_hashes(),
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_s": round(time.time() - started, 2),
        "source": {"path": args["glb"], "sha256": source_sha,
                   "bytes": os.path.getsize(args["glb"])},
        "output": {"path": out_glb, "sha256": sha256_file(out_glb),
                   "bytes": os.path.getsize(out_glb)},
        "site_to_bone_map": {b.name: b.as_dict() for b in sitelist.BONES},
        "registered_site_count": len(sitelist.ALL_NAMES),
        "premise_2_pre_existing_rig": ctx["premise2"],
        "weld_on_import": ctx["weld_on_import"],
        "weight_normalisation": ctx.get("normalisation"),
        "premise_6_skinnability": ctx["premise6"],
        "bbox": {"lo": ctx["bbox_lo"], "hi": ctx["bbox_hi"], "diagonal": ctx["diagonal"]},
        "facing": ctx["landmarks"]["facing"],
        "regions": ctx["landmarks"]["regions"],
        "landmarks_after_snap": ctx["landmarks"]["landmarks"],
        "landmarks_before_snap": ctx["heuristic_landmarks"],
        "landmark_provenance": ctx["landmarks"]["provenance"],
        "joint_ball_offset_table": ctx["offset_table"],
        "placement_ruling": ctx["placement_ruling"],
        "joint_balls_detected": ctx["joint_balls"],
        "offset_table_reproduced_by_second_build":
            offsets_first == ctx["offset_table"],
        "bone_lengths": ctx["bone_lengths"],
        "gates": {
            "N_pre_export": gate_n_pre,
            "N_post_export": export["gate_n_post"],
            "OBJ_registered_objects": export["gate_obj"],
            "P_rest_pose_round_trip": export["gate_p_round_trip"],
            "P_evaluation_liveness": {
                "verdict": "NOT YET RUN",
                "reason": ("nothing is bound in skeleton mode, so there is no deform for a "
                           "liveness clause to be about. It runs when a binding arm runs."),
            },
            "D_determinism": gate_d,
        },
        "export": {k: v for k, v in export.items()
                   if k not in ("gate_n_post", "gate_p_round_trip", "gate_obj")},
        "probe_action": {"verdict": "NOT AUTHORED",
                         "reason": "an arc on an unbound skeleton moves no geometry"},
        "deformation_diagnostics": {
            "verdict": "NOT YET RUN",
            "reason": "no binding exists; deformation statistics require weights",
        },
        "timings": ctx["timings"],
        "note": ("Skeleton-approval mode. The Director approves the skeleton before any "
                 "binding arm runs; no metric here approximates that judgement."),
    }
    path = os.path.join(out_dir, "skeleton_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("RIG_CHARACTER_OK " + json.dumps(
        {"mode": "skeleton", "glb": out_glb,
         "sha256": manifest["output"]["sha256"], "manifest": path}))


def _tool_hashes():
    here = os.path.dirname(os.path.abspath(__file__))
    return {os.path.basename(p): sha256_file(p) for p in [
        os.path.abspath(__file__),
        os.path.join(here, "armature_core", "sitelist.py"),
        os.path.join(here, "armature_core", "landmarks.py"),
        os.path.join(here, "armature_core", "joints.py"),
        os.path.join(here, "armature_core", "rig_gates.py"),
    ]}


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    validate_sitelist()

    started = time.time()
    source_sha = sha256_file(args["glb"])

    if args["measure_only"]:
        # The binding the CLI declares (`--binding`, default "rigid"), stated rather than
        # left to a default. This call used to pass four positional arguments and let
        # `bind` fall through to `True`, which `apply_binding` refuses by design.
        ctx = build_pass(args["glb"], args["name"], args["bands"], "measure",
                         bind=args["binding"], envelope_radii=args["envelope_radii"])
        rec = {
            "tool": "rig_character", "tool_version": TOOL_VERSION, "mode": "measure-only",
            # WAVE 14, F-252f399d -- see the note on the sibling manifests above.
            "blender": blender_scene.blender_provenance(),
            "source": args["glb"],
            "source_sha256": source_sha,
            "premise_2_pre_existing_rig": ctx["premise2"],
        "weld_on_import": ctx["weld_on_import"],
        "weight_normalisation": ctx.get("normalisation"),
            "premise_6_skinnability": ctx["premise6"],
            "landmarks": ctx["landmarks"]["landmarks"],
            "landmark_provenance": ctx["landmarks"]["provenance"],
            "facing": ctx["landmarks"]["facing"],
            "regions": ctx["landmarks"]["regions"],
            "bone_lengths": ctx["bone_lengths"],
            "binding": args["binding"],
            "envelope_radii": args["envelope_radii"],
            # A bare `null` beside a gate name is a placeholder shaped like evidence. When
            # the pass really did bind, this is the gate's own record; when it did not, the
            # record says so in the manifest's own NOT YET RUN convention.
            "gate_p": ctx["gate_p"] if ctx["gate_p"] is not None else {
                "verdict": "NOT YET RUN",
                "reason": ("this measure pass bound nothing, so there is no bind-pose "
                           "displacement for Gate P to be about")},
            "timings": ctx["timings"],
        }
        # F-244b2ad5: the output directory used to be created at the top of `main`, above
        # every `build_pass` in every branch — and `build_pass` refuses an ambiguous subject,
        # a non-finite one (`subject_scale`) and an unknown binding mode, none of which needs
        # a directory. It is created per branch, below the last refusal and above the first
        # byte. A halt still leaves a record: `_write_halt` makes the directory itself and
        # writes `halt.json` into it, so what a reader finds is a refusal, never an empty
        # directory. Corrected shape carried from `render_performer.py:319`.
        os.makedirs(out_dir, exist_ok=True)

        path = os.path.join(out_dir, "measure.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        print("RIG_CHARACTER_OK " + json.dumps({"mode": "measure", "record": path}))
        return

    if args["mode"] == "skeleton":
        run_skeleton(args, out_dir, source_sha, started)
        return
    if args["mode"] != "full":
        raise GateMode(f"unknown --mode={args['mode']!r}; known: skeleton, full",
                       {"mode": args["mode"], "known": ["skeleton", "full"]})

    # Two full builds from the same input. The second is the one kept; Gate D compares.
    mode = args["binding"]
    first = build_pass(args["glb"], args["name"], args["bands"], "determinism-probe",
                       bind=mode, envelope_radii=args["envelope_radii"])
    fp_first = first["fingerprint"]
    gate_p_first = first["gate_p"]
    del first

    ctx = build_pass(args["glb"], args["name"], args["bands"], "kept", bind=mode,
                     envelope_radii=args["envelope_radii"])
    gate_d = unbound_determinism_record(
        rig_gates.gate_d_determinism(fp_first, ctx["fingerprint"], ctx["diagonal"]),
        fp_first, ctx["fingerprint"], expect_weights=False)

    gate_n_pre = rig_gates.gate_n_names(
        [b.name for b in ctx["armature"].data.bones], sitelist.ALL_NAMES,
        "the built armature, before export")

    probe = author_probe(ctx)
    diagnostics = deformation_diagnostics(ctx, probe)

    # F-244b2ad5: the output directory used to be created at the top of `main`, above
    # every `build_pass` in every branch — and `build_pass` refuses an ambiguous subject,
    # a non-finite one (`subject_scale`) and an unknown binding mode, none of which needs
    # a directory. It is created per branch, below the last refusal and above the first
    # byte. A halt still leaves a record: `_write_halt` makes the directory itself and
    # writes `halt.json` into it, so what a reader finds is a refusal, never an empty
    # directory. Corrected shape carried from `render_performer.py:319`.
    os.makedirs(out_dir, exist_ok=True)

    tag = mode if mode != "envelope" else f"envelope_{args['envelope_radii']}"
    out_glb = os.path.join(out_dir, f"{args['name']}_{tag}.glb")
    export = export_rigged(ctx, probe, out_glb)
    out_sha = sha256_file(out_glb)

    manifest = {
        "tool": "rig_character",
        "tool_version": TOOL_VERSION,
        "mode": "full",
        "binding": mode,
        "binding_record": ctx["binding_record"],
        "bone_radii_measured": ctx["bone_radii"],
        "joint_ball_offset_table": ctx["offset_table"],
        "placement_ruling": ctx["placement_ruling"],
        "tool_sha256": _tool_hashes(),
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_s": round(time.time() - started, 2),
        "source": {"path": args["glb"], "sha256": source_sha,
                   "bytes": os.path.getsize(args["glb"])},
        "output": {"path": out_glb, "sha256": out_sha, "bytes": os.path.getsize(out_glb)},
        "site_to_bone_map": {b.name: b.as_dict() for b in sitelist.BONES},
        "registered_site_count": len(sitelist.ALL_NAMES),
        "e01_site_count": len(sitelist.E01_SITES),
        "premise_2_pre_existing_rig": ctx["premise2"],
        "weld_on_import": ctx["weld_on_import"],
        "weight_normalisation": ctx.get("normalisation"),
        "premise_6_skinnability": ctx["premise6"],
        "bbox": {"lo": ctx["bbox_lo"], "hi": ctx["bbox_hi"], "diagonal": ctx["diagonal"]},
        "facing": ctx["landmarks"]["facing"],
        "regions": ctx["landmarks"]["regions"],
        "landmarks": ctx["landmarks"]["landmarks"],
        "landmark_provenance": ctx["landmarks"]["provenance"],
        "bone_lengths": ctx["bone_lengths"],
        "probe_action": probe,
        "gates": {
            "N_pre_export": gate_n_pre,
            "N_post_export": export["gate_n_post"],
            "OBJ_registered_objects": export["gate_obj"],
            "P_rest_pose_kept_build": ctx["gate_p"],
            "P_rest_pose_first_build": gate_p_first,
            "D_determinism": gate_d,
        },
        "export": {k: v for k, v in export.items() if k != "gate_n_post"},
        "deformation_diagnostics": diagnostics,
        "timings": ctx["timings"],
        "note": ("Deformation statistics are DIAGNOSTICS and gate nothing. Whether the "
                 "deform is acceptable, and whether the figure is still the same "
                 "character, are the Director's on the sheet at his zoom. No number here "
                 "approximates either."),
    }
    path = os.path.join(out_dir, f"rig_manifest_{tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("RIG_CHARACTER_OK " + json.dumps({"mode": "full", "binding": tag,
                                            "glb": out_glb, "sha256": out_sha,
                                            "manifest": path}))


def halt_outcome(exc):
    """Which of the three things happened — the wave-8 halt contract's vocabulary.

    MEASURED 2026-09-04 (F-c3f86abc): `_write_halt` hard-coded `"outcome": "HALTED — a
    gate fired"` with no branch, and every refusal in this 1229-line file raised a bare
    `ArmatureError`, so `getattr(exc, "gate", "?")` wrote `"?"` for every halt this tool
    could produce. Driving the file's own `__main__` block with `ValueError("a bug, not a
    gate")` and with `ArmatureError("the export would carry 1 object(s) nobody
    registered")` produced records differing only in `"exception"`: both said an andon
    fired, both exited 1. A crash in the rigging code wrote a record asserting a gate
    stopped the run, beside a note explaining that gates after the one that fired are NOT
    YET RUN — about a run in which no gate fired at all.

    Three states, because there are three. A typed `GateFailure` is an andon that names
    itself; a bare `ArmatureError` is a deliberate refusal with no andon behind it (an
    unknown flag, an unknown `--mode=`); anything else is a crash.
    """
    if isinstance(exc, GateFailure):
        return "HALTED — a gate fired"
    if isinstance(exc, ArmatureError):
        return "REFUSED — the tool declined to proceed"
    return "FAILED — an unhandled error"


def _write_halt(out_dir, exc, source_sha, glb):
    """Record what stopped the run where it can be read back.

    A gate that halts and leaves nothing behind makes the executor the only witness. The
    evidence dict each gate carries is the measurement that stopped the run, so it is
    written beside the outputs the run did not produce — and the process still exits
    non-zero, because a halt that returns success is not a halt.
    """
    outcome = halt_outcome(exc)
    gate = getattr(exc, "gate", None)
    rec = {
        "tool": "rig_character", "tool_version": TOOL_VERSION,
        "outcome": outcome,
        "gate": gate,
        "exception": type(exc).__name__,
        "message": str(exc),
        "evidence": getattr(exc, "evidence", None),
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "source": {"path": glb, "sha256": source_sha},
        "outputs_not_produced": ["<name>_rigged.glb", "rig_manifest.json"],
        "note": (("Nothing downstream of the gate ran. No rigged GLB exists, no manifest "
                  "was written, and no export was attempted. Gates after the one that "
                  "fired are NOT YET RUN, not passed.") if gate is not None else
                 ("The run stopped here. No rigged GLB exists, no manifest was written, "
                  "and no export was attempted. No gate is named because none fired: "
                  "every gate is NOT YET RUN, not passed and not failed.")),
    }
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "halt.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, default=str)
    return path


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
    #
    # `_write_halt` carries the same three-state vocabulary onto disk. The exit code is
    # computed BEFORE anything that can fail and delivered from a `finally`: `parse_args`
    # raises on an unknown flag and `sha256_file` on a mistyped path, and that second
    # exception used to leave the whole `try` statement with `sys.exit` never reached.
    try:
        main()
    except BaseException as exc:                                      # noqa: BLE001
        import traceback
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
        _outcome = halt_outcome(exc)
        _sentinel = {
            "tool": "rig_character", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "rig_character", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        try:
            _args = parse_args()
            try:
                # A mistyped `--glb` is an ordinary mistake and used to delete the whole
                # halt record with a FileNotFoundError raised inside this block.
                _sha = sha256_file(_args["glb"])
            except BaseException:                                     # noqa: BLE001
                _sha = None
            _write_halt(os.path.abspath(_args["out"]), exc, _sha, _args["glb"])
        except BaseException:                                         # noqa: BLE001
            # The halt record is a courtesy; the sentinel and the exit code are
            # the contract. Even this diagnostic is guarded (F-586822bf):
            # nothing in this handler may reach the `finally` before `sys.exit`.
            try:
                traceback.print_exc()
            except BaseException:                                     # noqa: BLE001
                pass
        finally:
            print("RIG_CHARACTER_HALT " + _line)
            sys.exit(_code)
