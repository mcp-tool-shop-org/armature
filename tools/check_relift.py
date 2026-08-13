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
point of a lift is the 65 frames after it.

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

TOOL_VERSION = "E12.1"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def signatures(glb, frames, fps):
    """Per-frame evaluated-geometry signatures for one GLB, in its own fresh scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, fps)
    meshes, _arms, _info = blender_scene.import_glb(glb, expected_fps=fps)
    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise ArmatureError(f"{glb} imported no render-visible mesh")
    out = []
    for i in range(frames):
        blender_scene.set_scene_frame(scene, i)
        out.append(blender_scene.evaluated_geometry_signature(subject))
    return out


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

    pinned_sha, fresh_sha = _sha256(a.pinned), _sha256(a.fresh)
    pinned_sigs = signatures(a.pinned, a.frames, a.fps)
    fresh_sigs = signatures(a.fresh, a.frames, a.fps)
    ev = compare_signatures(pinned_sigs, fresh_sigs, label=a.label)

    rec = {
        "tool": "check_relift", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "label": a.label,
        "pinned": {"path": os.path.abspath(a.pinned), "sha256": pinned_sha},
        "fresh": {"path": os.path.abspath(a.fresh), "sha256": fresh_sha},
        "bytes_identical": pinned_sha == fresh_sha,
        "frames": a.frames, "fps": a.fps,
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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("CHECK_RELIFT_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
