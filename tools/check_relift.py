#!/usr/bin/env python
r"""check_relift — is a re-solved lift the same performance as the pinned one?

    blender -b -P tools\check_relift.py -- --pinned=<a.glb> --fresh=<b.glb>
            --out=<record.json> [--frames=65] [--fps=16] [--label=b2]

The stale-pin question, made mechanical. Every E11 and E12 generation was conditioned on a
start frame rendered from an E09 GLB that has sat on disk since it was lifted. If the solver
that produced it is not deterministic — or if the file drifted — then the arc's conditioning
image has an unrecorded ancestor and every identity claim in it rests on a file nobody
re-derived.

**Geometry, not bytes.** A byte-identical pair settles the question outright, because
identical bytes cannot decode to different geometry; but the converse does not hold, and
CLAUDE.md's law is explicit that a file-hash mismatch is not evidence a render changed. glTF
export can reorder buffers or embed a generator string without a vertex moving. So the
comparison here is per-frame **evaluated world-space geometry** — what the renderer would
actually draw, following the imported action — and the byte hash rides the record as a
second, independent fact rather than as the verdict.

Per frame, because a single-frame match proves only that the rest pose survived. The whole
point of a lift is the frames after it -- and HOW MANY of them is read off the assets, not
off a flag: `--frames` is checked against each GLB's own keyed action range, and a request
that overruns either one, or a pair whose ranges disagree, refuses rather than comparing
held poses (`gate_relift_window`).

Prints `CHECK_RELIFT_OK` or raises. A crashed `blender -b -P` exits 0, so the sentinel is the
contract and `$LASTEXITCODE` proves nothing.

Compensator (NAMED_COMPENSATORS): writes one JSON. Compensator: delete it; owner: the
executor session. Both GLBs are opened read-only.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from armature_core import blender_scene  # noqa: E402
from armature_core.glb import ReliftMismatch, compare_signatures  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
# CARRIED, not copied: `render_start_frame.action_frame_range` is the sibling instrument
# that already reads the imported actions' keyed span, under a docstring recording why it
# has to (`frame_set` past the end of an action holds the last pose and renders it without
# complaint). The same idiom as `make_rig_sheet` importing `make_parts_sheet.shoot` and
# `rig_repair` importing `rig_character`. Stage B: it belongs in `armature_core`.
from render_start_frame import action_frame_range  # noqa: E402

TOOL_VERSION = "E12.1"


class ReliftError(ArmatureError):
    """A relift comparison cannot be set up from what this run was given.

    Wave 25, F-3b71c0aa. Three refusals here raised the family BASE with no evidence at
    all -- a subject that imports no render-visible mesh, a `--pinned`/`--fresh` path
    that is not a file, and a `--frames` count with nothing to compare. `ArmatureError`
    is the family; a site that raises it names nothing about which andon pulled, which
    is what `errors.ArmatureError`'s own docstring says the wave-14 constructor is NOT a
    licence for. Each of the three now names this class and its own `clause`."""


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class ReliftSelfComparison(GateFailure):
    """`--pinned` and `--fresh` name ONE file, so the comparison has no two sides.

    F-94657d8e, wave 14, measured on this tool's own pure functions with one window and one
    signature list used for both sides: `gate_relift_window(w, dict(w), 65)` returns
    `clause: None`; `compare_signatures(sigs, list(sigs))` returns `n_frames_compared: 65,
    n_frames_differing: 0` and the verdict "all 65 frames of evaluated geometry identical";
    and `bytes_identical` is `pinned_sha == fresh_sha`, so it is true as well. Every gate
    green, and `what_this_settles` then publishes "whether the E09 lift solver is
    deterministic" off a comparison of one decode against itself. The two GLBs this tool is
    run on live one directory apart.

    The refusal is on IDENTITY OF FILE (`os.path.samefile`, so a `./`-prefixed alias, a
    relative path and a symlink are all caught) and never on content: two byte-identical
    GLBs produced by two independent solves are the strongest determinism result there is,
    and refusing them would delete the finding this tool exists to make. The sibling clause
    is `measure_floor.check_runs` — "a pair of a run with itself is bit-identical by
    construction and would be published as a zero floor" — carried here rather than
    reinvented, on the one instrument whose whole output is a claim about determinism.
    """

    gate = "RELIFT_SIDES"


class ReliftWindow(GateFailure):
    """The two GLBs do not present the same performance to compare over.

    F-6ee68fc0. `--frames` defaulted to the literal 65 and `main` passed that same number to
    both calls, so `len(pinned_sigs) == len(fresh_sigs) == a.frames` for EVERY input pair
    that exists and `compare_signatures`' frame-count clause -- "a lift that dropped or
    gained a frame is not the same performance however well the frames it kept agree" --
    was structurally unreachable from its only production caller. Nothing read either
    asset's keyed range: `signatures` discarded `_info`, never touched `frame_range` and
    never set `frame_start`/`frame_end`. A re-solve producing 40 frames against a 65-frame
    pin was therefore compared as 65-vs-65 with frames 40..64 HELD at the last key on both
    sides, and if the shared 40 agreed the record said `n_frames_compared: 65`,
    `n_frames_differing: 0`, "all 65 frames of evaluated geometry identical" -- about
    frames that were never animated.
    """

    gate = "RELIFT"


def keyed_window(glb, span, frames):
    """What one GLB offers the comparison: its keyed span and the frames to be read.

    `span` is `(first, last)` in SCENE frames or None. Control frames are 0-based and scene
    frames 1-based (`blender_scene.set_scene_frame`), so a span of (1.0, 65.0) is 65 keyed
    control frames.

    **F-4d9161df, wave 12 - the window is ABSOLUTE now, not a length.** This function used
    to compute `keyed = int(hi) - int(lo) + 1` and throw `lo` away, and `signatures` then
    sampled `range(window["sampled"])` through `set_scene_frame`, which maps control frame
    i to SCENE frame 1 + i. So the comparison always began at scene frame 1 whatever the
    action keyed. MEASURED: with both GLBs keying (10.0, 74.0) and `--frames=65`,
    `gate_relift_window` returned clause None and the verdict "both GLBs key [10.0, 74.0]
    and the requested 65 frames sit inside it" - while the sampler read scene frames 1..65,
    of which 1..9 are BEFORE the first key and 66..74 were never read at all. Blender holds
    the nearest pose outside an action's range and reports nothing, so a re-solve that
    drifted only in its last frames read as identical: `n_frames_differing: 0` about a
    window whose head is the held first pose on both sides and whose tail was never
    compared. The sibling instrument this file imports from checks BOTH ends for exactly
    this reason (`render_start_frame.py:441`).

    `sampled_scene_frames` is `[first, last]` INCLUSIVE, in scene frames, and is what
    `scene_frames_to_sample` and `gate_relift_window` both read. `sampled` is kept as the
    count, because the record and the gate's verdict quote it.
    """
    if span is None:
        return {"glb": os.path.abspath(glb), "action_frame_range": None,
                "keyed_frames": 0, "requested": int(frames), "sampled": 0,
                "first_keyed_scene_frame": None, "last_keyed_scene_frame": None,
                "sampled_scene_frames": None}
    lo, hi = float(span[0]), float(span[1])
    first, last = int(lo), int(hi)
    keyed = last - first + 1
    sampled = min(int(frames), max(keyed, 0))
    return {"glb": os.path.abspath(glb), "action_frame_range": [lo, hi],
            "keyed_frames": keyed, "requested": int(frames), "sampled": sampled,
            "first_keyed_scene_frame": first, "last_keyed_scene_frame": last,
            "sampled_scene_frames": ([first, first + sampled - 1] if sampled > 0
                                     else None)}


def scene_frames_to_sample(window):
    """The SCENE frames `signatures` reads, from the window's own recorded ends.

    One function, so the frames the gate certifies and the frames the sampler reads cannot
    be two different derivations - which is what F-4d9161df was.
    """
    span = window.get("sampled_scene_frames")
    if not span:
        return []
    return list(range(int(span[0]), int(span[1]) + 1))


def gate_relift_window(pinned, fresh, frames):
    """The compared window is derived from the assets, or the comparison does not happen.

    Two clauses, both of which the old code could not state:

    * the two GLBs' keyed ranges DIFFER -- the dropped-or-gained-frame case. Refused here
      rather than downstream: `compare_signatures`' length clause is the same refusal, but
      it can only see it once both lists have been sampled, and sampling both at `--frames`
      is exactly what hid it. That clause therefore remains unreachable FROM THIS TOOL, now
      by construction and for a stated reason, and stays exercised on hand-built pairs in
      the suite.
    * `--frames` overruns the keyed range -- Blender holds the last pose past the end of an
      action and reports nothing, so those frames would enter the denominator as agreement
      about a moment the performance never had.

    Pure, so both clauses are testable without Blender.
    """
    ev = {"gate": "RELIFT", "andon": "ReliftWindow", "requested_frames": int(frames),
          "pinned": pinned, "fresh": fresh}
    if pinned["action_frame_range"] is None or fresh["action_frame_range"] is None:
        ev["clause"] = "no_keyed_action"
        raise ReliftWindow(
            "one of the two GLBs carries no keyed action, so every sampled frame would be "
            "the same held pose and a PASS would be agreement about a still", ev)
    if pinned["action_frame_range"] != fresh["action_frame_range"]:
        ev["clause"] = "ranges_differ"
        raise ReliftWindow(
            f"the two GLBs key different windows: pinned "
            f"{pinned['action_frame_range']} ({pinned['keyed_frames']} frames), fresh "
            f"{fresh['action_frame_range']} ({fresh['keyed_frames']} frames). A lift that "
            f"dropped or gained a frame is not the same performance however well the "
            f"frames it kept agree", ev)
    shared = min(pinned["keyed_frames"], fresh["keyed_frames"])
    if int(frames) > shared:
        ev["clause"] = "request_overruns_the_performance"
        ev["shared_keyed_frames"] = shared
        raise ReliftWindow(
            f"--frames={int(frames)} overruns the {shared} keyed frames both GLBs carry. "
            f"Blender holds the last pose past the end of an action and renders it without "
            f"complaint, so frames {shared}..{int(frames) - 1} would enter the denominator "
            f"as agreement about a moment neither performance has", ev)
    # F-4d9161df - the clause a COUNT cannot state. A window can be short enough to fit
    # inside the keyed span and still sit outside it: the old code certified "the requested
    # 65 frames sit inside [10.0, 74.0]" over a sampler that read scene frames 1..65. Both
    # ends of what is actually SAMPLED are checked against both ends of the keys, which is
    # the check `render_start_frame.py:441` already carries one instrument over.
    first = min(pinned["first_keyed_scene_frame"], fresh["first_keyed_scene_frame"])
    last = max(pinned["last_keyed_scene_frame"], fresh["last_keyed_scene_frame"])
    outside = [w["sampled_scene_frames"] for w in (pinned, fresh)
               if not w["sampled_scene_frames"]
               or not (first <= w["sampled_scene_frames"][0]
                       and w["sampled_scene_frames"][1] <= last)]
    if outside:
        ev["clause"] = "sampled_window_outside_the_keys"
        ev["keyed_scene_frames"] = [first, last]
        ev["sampled_outside"] = outside
        raise ReliftWindow(
            f"the frames this comparison would read, {outside}, do not lie inside the "
            f"keyed scene frames [{first}, {last}]. Blender holds the nearest pose outside "
            f"an action's range and reports nothing, so those frames would enter the "
            f"denominator as agreement about a moment neither performance has", ev)
    ev["clause"] = None
    ev["shared_keyed_frames"] = shared
    ev["sampled_scene_frames"] = pinned["sampled_scene_frames"]
    ev["keyed_scene_frames"] = [first, last]
    ev["verdict"] = (
        f"both GLBs key {pinned['action_frame_range']} and the {int(frames)} frames this "
        f"comparison reads are scene frames "
        f"{pinned['sampled_scene_frames'][0]}..{pinned['sampled_scene_frames'][1]}, "
        f"inside it")
    return ev


def signatures(glb, frames, fps):
    """Per-frame evaluated-geometry signatures for one GLB, in its own fresh scene.

    Returns `(signatures, window)`. The window is measured off the asset -- the keyed span
    of its own actions -- so `gate_relift_window` can say whether the two GLBs are even
    comparable before any number is quoted about them.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, fps)
    meshes, _arms, _info = blender_scene.import_glb(glb, expected_fps=fps)
    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise ReliftError(f"{glb} imported no render-visible mesh",
            {"clause": "import_has_no_render_visible_mesh", "andon": "ArmatureError",
             "glb": glb, "mesh_objects": [o.name for o in meshes]})
    window = keyed_window(glb, action_frame_range(), frames)
    # F-33fb7947: the selection is named in the record, not left to a reader of the
    # argument. The call below passes `scene=` as well - idempotent, because `subject` is
    # already the filtered list, and a statement rather than a behaviour change.
    window["selection"] = "render_visible_meshes"
    out = []
    # F-4d9161df: the frames come from the window's own recorded ends, not from a count.
    # `set_scene_frame` takes a 0-based CONTROL frame and adds 1, so a scene frame f is
    # asked for as f - 1.
    for scene_frame in scene_frames_to_sample(window):
        blender_scene.set_scene_frame(scene, scene_frame - 1)
        out.append(blender_scene.evaluated_geometry_signature(subject, scene=scene))
    return out, window


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/check_relift.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pinned", default=None,
                    help="the GLB that has been on disk since it was lifted -- the one a "
                         "prior generation was conditioned on (GLB mode)")
    ap.add_argument("--fresh", default=None,
                    help="a GLB re-solved from the same inputs, to compare against it "
                         "(GLB mode)")
    ap.add_argument("--pinned-motion", default=None,
                    help="pinned lift_solve motion-record JSON (F-6a7e819f); mutually "
                         "exclusive with --pinned GLB mode unless both layers are compared")
    ap.add_argument("--fresh-motion", default=None,
                    help="fresh lift_solve motion-record JSON (F-6a7e819f)")
    ap.add_argument("--out", required=True,
                    help="the JSON record to write. Compensator: delete it; owner: the "
                         "executor session")
    ap.add_argument("--frames", type=int, default=65,
                    help="how many frames to compare (argparse eats leading minus signs: "
                         "pass flags as --flag=value)")
    ap.add_argument("--fps", type=int, default=16,
                    help="frame rate both GLBs are read at (default 16); glTF key times "
                         "are SECONDS, so a mismatch samples different poses")
    ap.add_argument("--label", default=None,
                    help="a name for the FRESH arm in the record (default: none), so two "
                         "re-solves can be told apart by a reader")
    return ap.parse_args(argv[argv.index("--") + 1:] if "--" in argv else [])


def motion_channel_signatures(path, frames):
    """Per-frame digests of local rotation channels (pure; F-6a7e819f)."""
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    rows = list(rec.get("frames") or [])
    if not rows:
        raise ReliftError(
            f"motion record {path!r} carries no frames",
            {"clause": "motion_record_has_no_frames", "path": os.path.abspath(path)})
    n = min(int(frames), len(rows))
    sigs = []
    for i in range(n):
        fr = rows[i]
        local = fr.get("local") or {}
        # Stable digest: sorted bone -> flattened 3x3 + root.
        parts = []
        for bone in sorted(local):
            m = local[bone]
            flat = ",".join(f"{float(v):.9g}" for row in m for v in row)
            parts.append(f"{bone}:{flat}")
        root = fr.get("root") or [0.0, 0.0, 0.0]
        parts.append("root:" + ",".join(f"{float(v):.9g}" for v in root))
        blob = "|".join(parts).encode("utf-8")
        sigs.append({"frame": i, "sha256": hashlib.sha256(blob).hexdigest(),
                     "n_bones": len(local)})
    window = {
        "glb": os.path.abspath(path), "action_frame_range": [0.0, float(len(rows) - 1)],
        "keyed_frames": len(rows), "requested": int(frames), "sampled": n,
        "first_keyed_scene_frame": 0, "last_keyed_scene_frame": len(rows) - 1,
        "sampled_scene_frames": [0, n - 1] if n > 0 else None,
        "layer": "motion_local",
    }
    return sigs, window


def compare_motion_signatures(pinned_sigs, fresh_sigs, label=None):
    """Same shape as compare_signatures, over motion-channel digests."""
    n = min(len(pinned_sigs), len(fresh_sigs))
    differing = []
    for i in range(n):
        if pinned_sigs[i]["sha256"] != fresh_sigs[i]["sha256"]:
            differing.append(i)
    if len(pinned_sigs) != len(fresh_sigs):
        return {
            "verdict": (f"frame counts differ: pinned {len(pinned_sigs)} vs "
                        f"fresh {len(fresh_sigs)}"),
            "n_frames_compared": n, "n_frames_differing": len(differing) + 1,
            "differing_frames": differing, "label": label, "layer": "motion_local",
            "clause": "motion_frame_counts_differ",
        }
    if differing:
        return {
            "verdict": f"{len(differing)} of {n} motion frames differ in local channels",
            "n_frames_compared": n, "n_frames_differing": len(differing),
            "differing_frames": differing, "label": label, "layer": "motion_local",
        }
    return {
        "verdict": f"all {n} frames of local rotation channels identical",
        "n_frames_compared": n, "n_frames_differing": 0,
        "differing_frames": [], "label": label, "layer": "motion_local",
    }


def main():
    a = parse_args(sys.argv)
    glb_mode = bool(a.pinned or a.fresh)
    motion_mode = bool(a.pinned_motion or a.fresh_motion)
    if not glb_mode and not motion_mode:
        raise ReliftError(
            "pass --pinned/--fresh (GLB) and/or --pinned-motion/--fresh-motion",
            {"clause": "relift_sides_required"})
    if glb_mode and (not a.pinned or not a.fresh):
        raise ReliftError(
            "GLB mode needs both --pinned and --fresh",
            {"clause": "glb_pair_incomplete",
             "pinned": a.pinned, "fresh": a.fresh})
    if motion_mode and (not a.pinned_motion or not a.fresh_motion):
        raise ReliftError(
            "motion mode needs both --pinned-motion and --fresh-motion",
            {"clause": "motion_pair_incomplete",
             "pinned_motion": a.pinned_motion, "fresh_motion": a.fresh_motion})

    if a.frames < 1:
        raise ReliftError(f"--frames={a.frames}: there is nothing to compare",
            {"clause": "frames_is_not_a_comparable_count", "andon": "ArmatureError",
             "flag": "--frames", "frames": a.frames})

    rec = {
        "tool": "check_relift", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "label": a.label,
        "frames": a.frames, "fps": a.fps,
    }
    ok_payload = {"label": a.label, "record": a.out}

    if glb_mode:
        for p in (a.pinned, a.fresh):
            if not os.path.isfile(p):
                raise ReliftError(f"no such GLB: {p}",
                    {"clause": "glb_is_not_a_file", "andon": "ArmatureError",
                     "glb": os.path.abspath(p)})
        if os.path.samefile(a.pinned, a.fresh):
            raise ReliftSelfComparison(
                f"--pinned and --fresh name the same file "
                f"({os.path.realpath(a.pinned)}); a comparison of a decode with itself "
                f"reports every frame identical and every byte identical by construction, "
                f"and this tool's record would publish that as the verdict that the E09 "
                f"lift solver is deterministic",
                {"clause": "pinned_and_fresh_are_the_same_file",
                 "gate": "RELIFT_SIDES", "andon": "ReliftSelfComparison",
                 "pinned": os.path.abspath(a.pinned), "fresh": os.path.abspath(a.fresh),
                 "pinned_realpath": os.path.realpath(a.pinned),
                 "fresh_realpath": os.path.realpath(a.fresh),
                 "compared_on": "os.path.samefile (identity of file, never content)"})
        pinned_sha, fresh_sha = _sha256(a.pinned), _sha256(a.fresh)
        pinned_sigs, pinned_window = signatures(a.pinned, a.frames, a.fps)
        fresh_sigs, fresh_window = signatures(a.fresh, a.frames, a.fps)
        window = gate_relift_window(pinned_window, fresh_window, a.frames)
        ev = compare_signatures(pinned_sigs, fresh_sigs, label=a.label)
        ev["window"] = window
        rec.update({
            "pinned": {"path": os.path.abspath(a.pinned), "sha256": pinned_sha,
                       "realpath": os.path.realpath(a.pinned)},
            "fresh": {"path": os.path.abspath(a.fresh), "sha256": fresh_sha,
                      "realpath": os.path.realpath(a.fresh)},
            "sides_are_distinct_files": (
                "refused before either import by gate RELIFT_SIDES, on os.path.samefile"),
            "bytes_identical": pinned_sha == fresh_sha,
            "frames_source": (
                "--frames, checked against both GLBs' own keyed action ranges by "
                "gate_RELIFT.window; a request that overruns either one refuses"),
            "gate_RELIFT": ev,
            "signature_selection": (
                "render_visible_meshes - every digest above was taken over the "
                "RENDER-VISIBLE meshes of each import"),
            "what_this_settles": (
                "whether the E09 lift solver is deterministic and the on-disk GLB is what "
                "the recorded inputs still produce"),
        })
        ok_payload.update({
            "frames_compared": ev["n_frames_compared"],
            "frames_differing": ev["n_frames_differing"],
            "bytes_identical": rec["bytes_identical"],
            "verdict": ev["verdict"],
        })

    if motion_mode:
        for p in (a.pinned_motion, a.fresh_motion):
            if not os.path.isfile(p):
                raise ReliftError(f"no such motion record: {p}",
                    {"clause": "motion_is_not_a_file", "andon": "ArmatureError",
                     "motion": os.path.abspath(p)})
        if os.path.samefile(a.pinned_motion, a.fresh_motion):
            raise ReliftSelfComparison(
                f"--pinned-motion and --fresh-motion name the same file "
                f"({os.path.realpath(a.pinned_motion)})",
                {"clause": "pinned_and_fresh_motion_are_the_same_file",
                 "gate": "RELIFT_SIDES", "andon": "ReliftSelfComparison",
                 "pinned_motion": os.path.abspath(a.pinned_motion),
                 "fresh_motion": os.path.abspath(a.fresh_motion)})
        p_sigs, p_win = motion_channel_signatures(a.pinned_motion, a.frames)
        f_sigs, f_win = motion_channel_signatures(a.fresh_motion, a.frames)
        # Reuse window gate over motion lengths.
        window_m = gate_relift_window(p_win, f_win, a.frames)
        ev_m = compare_motion_signatures(p_sigs, f_sigs, label=a.label)
        ev_m["window"] = window_m
        rec["pinned_motion"] = {
            "path": os.path.abspath(a.pinned_motion),
            "sha256": _sha256(a.pinned_motion),
        }
        rec["fresh_motion"] = {
            "path": os.path.abspath(a.fresh_motion),
            "sha256": _sha256(a.fresh_motion),
        }
        rec["gate_RELIFT_motion"] = ev_m
        rec["motion_layer"] = (
            "local rotation channels + root; same --frames/--fps window gates as GLB mode "
            "(F-6a7e819f)")
        ok_payload["motion_frames_compared"] = ev_m["n_frames_compared"]
        ok_payload["motion_frames_differing"] = ev_m["n_frames_differing"]
        ok_payload["motion_verdict"] = ev_m["verdict"]
        if not glb_mode:
            ok_payload.update({
                "frames_compared": ev_m["n_frames_compared"],
                "frames_differing": ev_m["n_frames_differing"],
                "bytes_identical": (rec["pinned_motion"]["sha256"]
                                    == rec["fresh_motion"]["sha256"]),
                "verdict": ev_m["verdict"],
            })

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)

    print("CHECK_RELIFT_OK " + json.dumps(ok_payload))
    return 0


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
            "tool": "check_relift", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "check_relift", "outcome": _outcome,
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
            print("CHECK_RELIFT_HALT " + _line)
            sys.exit(_code)
