#!/usr/bin/env python
"""probe_glb — measure what a GLB actually contains. Reads only; writes only JSON.

    blender -b -P tools\\probe_glb.py -- --out=<dir> --glb=<a.glb> --glb=<b.glb> ...

E01's premise 3 ("some of those GLBs carry a usable armature") is marked ASSUMED, and
P2 is the measurement that settles it. The conjunction it counts is *loads* AND *has
bones* AND *bones are usable*, so each clause is measured and reported separately —
a joined number with no clauses is a number that cannot be wrong in a useful way.

"Usable" here is the spec's word: **posable and named**. That is a mechanical property
and it is deliberately not the same question as whether the rig is any good. The
studio's June 2026 verdict (rigging abandoned — UniRig shreds faced characters) is
about rig *quality*; conflating the two would make this measurement answer a question
nobody asked.

P2b is the stricter, downstream-relevant count: whether bone names identify the
anatomical sites a body skeleton needs. `docs/research-grounding.md` F20 records
OpenPose-18's limbSeq and keypoint count but **not** the keypoint order or names, so
no complete COCO-18 map can be built from the retrieved record regardless of what the
names say; this reports which sites are findable, not that a map exists.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Euler  # noqa: E402

from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

# Token sets for the anatomical sites an 18-keypoint body skeleton needs. Matching is
# substring-on-lowercased-name, side-aware. These are naming conventions (Mixamo,
# Rigify, glTF/VRM humanoid), not a retrieved COCO-18 ordering.
SITES = {
    "nose": (("nose",), None),
    "neck": (("neck",), None),
    "shoulder.L": (("shoulder", "upperarm", "upper_arm", "arm"), "L"),
    "shoulder.R": (("shoulder", "upperarm", "upper_arm", "arm"), "R"),
    "elbow.L": (("elbow", "forearm", "lowerarm", "lower_arm"), "L"),
    "elbow.R": (("elbow", "forearm", "lowerarm", "lower_arm"), "R"),
    "wrist.L": (("wrist", "hand"), "L"),
    "wrist.R": (("wrist", "hand"), "R"),
    "hip.L": (("hip", "upleg", "upperleg", "upper_leg", "thigh"), "L"),
    "hip.R": (("hip", "upleg", "upperleg", "upper_leg", "thigh"), "R"),
    "knee.L": (("knee", "leg", "shin", "calf"), "L"),
    "knee.R": (("knee", "leg", "shin", "calf"), "R"),
    "ankle.L": (("ankle", "foot"), "L"),
    "ankle.R": (("ankle", "foot"), "R"),
    "eye.L": (("eye",), "L"),
    "eye.R": (("eye",), "R"),
    "ear.L": (("ear",), "L"),
    "ear.R": (("ear",), "R"),
}

#: Side markers, matched as whole NAME TOKENS rather than as substrings or as a last
#: character. MEASURED 2026-09-04: the superseded rule was
#:
#:     left  = any(t in low for t in ("left", "_l", ".l", "l_", "lft", "lf_")) or low.endswith("l")
#:     right = any(t in low for t in ("right", "_r", ".r", "r_", "rgt", "rt_")) or low.endswith("r")
#:
#: `mixamorig:LeftShoulder` set BOTH flags -- it contains "left" and ends in "r" -- and
#: returned None, so an industry-standard rig read as sideless. `Shoulder` returned "R",
#: `ear` returned "R", `heel` returned "L", and `upper_arm.L` returned None because
#: "upper_arm" contains the substring "r_". This is the instrument behind E01's headline
#: count and `P2b_all_18_sites_named` is read straight off it, so a donor GLB naming its
#: sites perfectly was recorded in the repo as missing them.
LEFT_TOKENS = ("l", "left", "lft", "lf")
RIGHT_TOKENS = ("r", "right", "rgt", "rt")

#: Split on separators AND camelCase, so `LeftShoulder`, `left_shoulder`, `shoulder.L` and
#: `DEF-upper_arm.R` all present their side marker as a token of its own.
_TOKEN_SPLIT = re.compile(
    r"[^A-Za-z0-9]+"                 # : - _ . and friends
    r"|(?<=[a-z0-9])(?=[A-Z])"       # LeftShoulder -> Left | Shoulder
    r"|(?<=[A-Z])(?=[A-Z][a-z])"     # IKLeftArm    -> IK | Left | Arm
)


def name_tokens(name):
    """The name's tokens, lowercased. `mixamorig:LeftUpLeg` -> [mixamorig, left, up, leg]."""
    return [t.lower() for t in _TOKEN_SPLIT.split(name) if t]


def _side_of(name):
    """"L", "R", or None when the name marks no side or marks both.

    A side marker must BE a token. A last character is not a boundary: `Shoulder`,
    `heel`, `Collar` and `Femur` name no side, and reporting one for them is how a
    symmetric rig produced a half-named verdict.
    """
    tokens = set(name_tokens(name))
    left = bool(tokens & set(LEFT_TOKENS))
    right = bool(tokens & set(RIGHT_TOKENS))
    if left and not right:
        return "L"
    if right and not left:
        return "R"
    return None


def _site_token_matches(site_token, tokens):
    """A site token must BE a name token, or a contiguous RUN of them.

    The separator-insensitive half is what makes the compound conventions work:
    `upper_arm` is `["upper", "arm"]` in `DEF-upper_arm.R` and `["upperarm"]` in
    `mixamorig:UpperArm`, and `upleg` is `["up", "leg"]` in `mixamorig:LeftUpLeg`. Both
    are the SAME site token once the separators are dropped, so the comparison is made on
    the joined run rather than on the raw string.
    """
    want = "".join(ch for ch in site_token.lower() if ch.isalnum())
    if not want:
        return False
    for i in range(len(tokens)):
        joined = ""
        for j in range(i, len(tokens)):
            joined += tokens[j]
            if joined == want:
                return True
            if len(joined) >= len(want):
                break
    return False


def match_sites(bone_names):
    """Which anatomical sites this bone list names, and which bones name them.

    MEASURED 2026-09-04 (F-d83052e8): site tokens used to be matched as bare SUBSTRINGS of
    the whole lowercased name (`any(t in low for t in tokens)`) while `_side_of` matched
    side markers as whole name TOKENS -- the boundary rule F-187f792c installed on the side
    half was never applied to the site half. On a standard 23-bone Mixamo skeleton that
    reported 15 of 18 sites found, two of them being

        ear.L -> ['mixamorig:LeftForeArm']    ear.R -> ['mixamorig:RightForeArm']

    because "ear" is a substring of "f-o-r-e-a-r-m". That skeleton has no ear bone, no eye
    bone and no nose bone; the true anatomical-site count on it is **13 of 18**, and the
    same forearm bone was simultaneously the correct `elbow.L` hit. `anatomical_sites_count`
    and `P2b_all_18_sites_named` are read straight off this dict, and E01's headline P2
    figures are summed from them.
    """
    found = {}
    for site, (tokens, side) in SITES.items():
        hits = []
        for name in bone_names:
            name_toks = name_tokens(name)
            if not any(_site_token_matches(t, name_toks) for t in tokens):
                continue
            if side is not None and _side_of(name) != side:
                continue
            hits.append(name)
        if hits:
            found[site] = sorted(hits)[:3]
    return found


def probe_one(path):
    rec = {"path": path, "exists": os.path.isfile(path)}
    if not rec["exists"]:
        rec["clause_A_loads"] = False
        rec["error"] = "file not found"
        return rec
    rec["bytes"] = os.path.getsize(path)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
        rec["clause_A_loads"] = True
    except Exception as exc:  # a failed import is a measurement, not a crash
        rec["clause_A_loads"] = False
        rec["error"] = f"{type(exc).__name__}: {exc}"
        return rec

    objs = list(bpy.data.objects)
    armatures = [o for o in objs if o.type == "ARMATURE"]
    meshes = [o for o in objs if o.type == "MESH"]

    rec["objects"] = len(objs)
    # A file whose name says `_rigged` but that carries no ARMATURE has to have put
    # its skeleton somewhere; the type histogram is what says where.
    types = {}
    for o in objs:
        types[o.type] = types.get(o.type, 0) + 1
    rec["object_types"] = types
    rec["empty_names_sample"] = sorted(o.name for o in objs if o.type == "EMPTY")[:12]
    rec["mesh_objects"] = len(meshes)
    rec["vertices"] = int(sum(len(o.data.vertices) for o in meshes))
    rec["materials"] = len(bpy.data.materials)
    rec["images"] = len(bpy.data.images)
    rec["actions"] = len(bpy.data.actions)
    rec["armature_objects"] = len(armatures)

    total_bones = sum(len(a.data.bones) for a in armatures)
    rec["bone_count"] = total_bones
    rec["clause_B_has_bones"] = len(armatures) > 0 and total_bones > 0

    bone_names = []
    for a in armatures:
        bone_names.extend(b.name for b in a.data.bones)
    rec["bone_names"] = bone_names
    rec["bone_names_nonempty"] = all(n.strip() for n in bone_names) if bone_names else False

    # clause C — posable: can a pose bone actually take a rotation?
    posable = False
    pose_error = None
    if rec["clause_B_has_bones"]:
        try:
            arm = armatures[0]
            pb = arm.pose.bones[0]
            before = pb.rotation_mode
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = Euler((0.1, 0.0, 0.0), "XYZ")
            bpy.context.view_layer.update()
            posable = abs(pb.rotation_euler.x - 0.1) < 1e-6
            pb.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
            pb.rotation_mode = before
        except Exception as exc:
            pose_error = f"{type(exc).__name__}: {exc}"
    rec["clause_C_posable_and_named"] = bool(posable and rec["bone_names_nonempty"])
    if pose_error:
        rec["pose_error"] = pose_error

    rec["P2_joined"] = bool(
        rec["clause_A_loads"] and rec["clause_B_has_bones"] and rec["clause_C_posable_and_named"]
    )

    # skinning: bones that actually deform something
    vgroups = set()
    for m in meshes:
        vgroups.update(g.name for g in m.vertex_groups)
    rec["vertex_groups"] = len(vgroups)
    rec["bones_with_matching_vertex_group"] = len(set(bone_names) & vgroups)

    sites = match_sites(bone_names)
    rec["anatomical_sites_found"] = sorted(sites)
    rec["anatomical_sites_count"] = len(sites)
    rec["anatomical_sites_detail"] = sites
    rec["P2b_all_18_sites_named"] = len(sites) == len(SITES)
    return rec


def parse_argv(argv, *, known=("out", "glb")):
    """`--out=<dir>` once and `--glb=<path>` one or more times. Anything else RAISES.

    MEASURED 2026-09-04 (F-f3cd559e). The loop this replaces was

        key, _, value = token[2:].partition("=")
        if key == "out": out_dir = value
        elif key == "glb": globs.append(value)

    which silently ignores what it does not recognise and silently ADMITS empty paths into
    the probed population. Measured on those lines verbatim: `--out=d --glb=a.glb --glb
    b.glb` (the space form) yields `['a.glb', '', '']` -- `--glb` alone gives key "glb"
    with value "", and `'b.glb'[2:]` is ALSO "glb", so the bare path contributes a second
    "" -- and the summary then reports `n_files` 3 for two files named. `--gbl=b.glb` (a
    typo) is dropped without a word; a bare positional adds another ""; `--help` is
    swallowed and the tool probes anyway. Each "" reaches `probe_one`, which records
    `{{"path": "", "exists": false, "clause_A_loads": false}}` -- a phantom member of a
    denominator that every number this tool exists to produce is computed over.

    `rig_character.parse_args` and `rig_parts.parse_args` already refuse an unknown token
    by name; this is that shape, carried.
    """
    out_dir, paths = None, []
    for token in argv:
        if not token.startswith("--"):
            raise ArmatureError(
                f"unexpected argument {token!r}: every value is attached to its flag with "
                f"'=' ({' '.join('--' + k + '=<value>' for k in known)}). The space form "
                f"is not accepted, because `token[2:]` on a bare path silently produced a "
                f"second empty member of the probed population")
        key, sep, value = token[2:].partition("=")
        key = key.replace("-", "_")
        if key not in known:
            raise ArmatureError(
                f"unknown argument {token!r}; known: {sorted(known)}")
        if not sep or not value:
            raise ArmatureError(
                f"{token!r} carries no value; an empty --{key} would join the population "
                f"as a file that does not exist and be counted in every denominator")
        if key == "out":
            if out_dir is not None:
                raise ArmatureError(
                    f"--out given twice ({out_dir!r} then {value!r}); one run writes one "
                    f"record")
            out_dir = value
        else:
            paths.append(value)
    if not out_dir or not paths:
        raise ArmatureError("usage: -- --out=<dir> --glb=<path> [--glb=<path> ...]")
    return out_dir, paths


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir, globs = parse_argv(argv)
    os.makedirs(out_dir, exist_ok=True)

    records = [probe_one(p) for p in globs]
    summary = {
        "n_files": len(records),
        "clause_A_loads": sum(1 for r in records if r.get("clause_A_loads")),
        "clause_B_has_bones": sum(1 for r in records if r.get("clause_B_has_bones")),
        "clause_C_posable_and_named": sum(1 for r in records if r.get("clause_C_posable_and_named")),
        "P2_joined": sum(1 for r in records if r.get("P2_joined")),
        "P2b_all_18_sites_named": sum(1 for r in records if r.get("P2b_all_18_sites_named")),
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
    }
    payload = {"summary": summary, "files": records}
    path = os.path.join(out_dir, "p2_armatures.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("PROBE_GLB_OK " + json.dumps({"summary": summary, "json": path}))


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
            "tool": "probe_glb", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "probe_glb", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("PROBE_GLB_HALT " + _line)
            sys.exit(_code)
