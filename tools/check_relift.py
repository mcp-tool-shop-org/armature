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


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
    """What one GLB offers the comparison: its keyed span and how much of it was asked for.

    `span` is `(first, last)` in SCENE frames or None. Control frames are 0-based and scene
    frames 1-based (`blender_scene.set_scene_frame`), so a span of (1.0, 65.0) is 65 keyed
    control frames.
    """
    if span is None:
        return {"glb": os.path.abspath(glb), "action_frame_range": None,
                "keyed_frames": 0, "requested": int(frames), "sampled": 0}
    lo, hi = float(span[0]), float(span[1])
    keyed = int(hi) - int(lo) + 1
    return {"glb": os.path.abspath(glb), "action_frame_range": [lo, hi],
            "keyed_frames": keyed, "requested": int(frames),
            "sampled": min(int(frames), max(keyed, 0))}


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
    ev["clause"] = None
    ev["shared_keyed_frames"] = shared
    ev["verdict"] = (f"both GLBs key {pinned['action_frame_range']} and the requested "
                     f"{int(frames)} frames sit inside it")
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
        raise ArmatureError(f"{glb} imported no render-visible mesh")
    window = keyed_window(glb, action_frame_range(), frames)
    out = []
    for i in range(window["sampled"]):
        blender_scene.set_scene_frame(scene, i)
        out.append(blender_scene.evaluated_geometry_signature(subject))
    return out, window


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", required=True)
    ap.add_argument("--fresh", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=65,
                    help="how many frames to compare (argparse eats leading minus signs: "
                         "pass flags as --flag=value)")
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--label", default=None)
    return ap.parse_args(argv[argv.index("--") + 1:] if "--" in argv else [])


def main():
    a = parse_args(sys.argv)
    for p in (a.pinned, a.fresh):
        if not os.path.isfile(p):
            raise ArmatureError(f"no such GLB: {p}")

    if a.frames < 1:
        raise ArmatureError(f"--frames={a.frames}: there is nothing to compare")

    pinned_sha, fresh_sha = _sha256(a.pinned), _sha256(a.fresh)
    pinned_sigs, pinned_window = signatures(a.pinned, a.frames, a.fps)
    fresh_sigs, fresh_window = signatures(a.fresh, a.frames, a.fps)
    # The window andon runs BEFORE any verdict is computed: a comparison over a window the
    # assets do not both have is not a weaker comparison, it is a different question.
    window = gate_relift_window(pinned_window, fresh_window, a.frames)
    ev = compare_signatures(pinned_sigs, fresh_sigs, label=a.label)
    ev["window"] = window

    rec = {
        "tool": "check_relift", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "label": a.label,
        "pinned": {"path": os.path.abspath(a.pinned), "sha256": pinned_sha},
        "fresh": {"path": os.path.abspath(a.fresh), "sha256": fresh_sha},
        "bytes_identical": pinned_sha == fresh_sha,
        "frames": a.frames, "fps": a.fps,
        "frames_source": ("--frames, checked against both GLBs' own keyed action ranges by "
                          "gate_RELIFT.window; a request that overruns either one refuses"),
        "gate_RELIFT": ev,
        "what_this_settles": (
            "whether the E09 lift solver is deterministic and the on-disk GLB is what the "
            "recorded inputs still produce. Geometry is the verdict; the byte hashes are a "
            "second independent fact, because identical bytes cannot decode to different "
            "geometry while differing bytes need not mean anything moved"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)

    print("CHECK_RELIFT_OK " + json.dumps({
        "label": a.label, "frames_compared": ev["n_frames_compared"],
        "frames_differing": ev["n_frames_differing"],
        "bytes_identical": rec["bytes_identical"],
        "verdict": ev["verdict"], "record": a.out}))
    return 0


def _halt_keysafe(value):
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
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v) for v in value]
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
        traceback.print_exc()
        _detail = getattr(exc, "evidence", None)
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _sentinel = {
            "tool": "check_relift",
            "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                        else "REFUSED — the tool declined to proceed"
                        if isinstance(exc, ArmatureError)
                        else "FAILED — an unhandled error"),
            "gate": getattr(exc, "gate", None),
            "error": type(exc).__name__, "message": str(exc),
            "evidence": _halt_keysafe(_detail) if isinstance(_detail, dict) else None}
        # The sentinel and the exit code are the contract, and NEITHER may be deleted by a
        # failure to serialise the sentinel itself. `_code` is computed before anything that
        # can raise and delivered from a `finally`; the fallback line carries only values
        # that are already strings, so it cannot fail in turn.
        try:
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            _line = json.dumps({
                "tool": _sentinel["tool"], "outcome": _sentinel["outcome"], "gate": None,
                "error": _sentinel["error"], "message": _sentinel["message"],
                "evidence": None})
        finally:
            print("CHECK_RELIFT_HALT " + _line)
            sys.exit(_code)
