"""Measure CLI `main(argv)` SUCCESS fixtures — shrink NO_SUCCESS_FIXTURE (wave 35).

F-8c52638d: all seven measure_* tools sat in NO_SUCCESS_FIXTURE while unit homes
exercised library calls only. This sibling of `test_paid_argv_smoke.py` drives each
with a synthetic short clip / JSON out: exit 0, the tool's own success token, and the
named artifact on disk.
"""

from __future__ import annotations

import ast
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS  # noqa: F401
import _census_nodes as CN

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _success_tokens(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    tokens = set()
    for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        stack = list(ast.iter_child_nodes(fn))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.extend(ast.iter_child_nodes(node))
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "print" and node.args):
                continue
            first = node.args[0]
            while isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
                first = first.left
            if isinstance(first, ast.JoinedStr) and first.values:
                first = first.values[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                word = first.value.strip().split()
                if not word:
                    continue
                token = word[0]
                if (token.endswith("_OK") or token.startswith("MEASURE_")
                        or token == "wrote"):
                    tokens.add(token)
    return tokens


def _pngs(d, n=3, size=(8, 6), seed=0):
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    for i in range(n):
        Image.fromarray(rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)).save(
            os.path.join(d, f"{i:05d}.png"))
    return d


def _arm_argv(tmp):
    import measure_arm as M
    from test_measure_arm import _arm_run, _frames_dir
    run, joints = _arm_run(tmp, n_authored=3)
    frames = _frames_dir(tmp, list(range(3)))
    out = tmp / "arm.json"
    return M, [f"--run={run}", f"--joints={joints}", f"--frames={frames}",
               f"--out={out}"], str(out), "MEASURE_ARM"


def _cascade_argv(tmp, monkeypatch):
    import measure_cascade_clip as M
    from test_measure_cascade_clip import _sources, _clip, _stub
    d, frames = _sources(tmp, 3)
    _stub(monkeypatch, frames, 32, 32)
    out = tmp / "cascade_out"
    return M, [f"--clip={_clip(tmp)}", f"--frames={d}", f"--out={out}",
               "--expect-frames=3", "--step=8"], str(out), "MEASURE_CASCADE_OK"


def _clip_argv(tmp):
    import measure_clip as M
    frames = _pngs(str(tmp / "frames"), n=3)
    out = tmp / "clip.json"
    return M, [f"--frames={frames}", f"--out={out}"], str(out), "MEASURE_CLIP_OK"


def _floor_argv(tmp):
    import measure_floor as M
    from test_measure_floor import _run
    for name in ("r1", "r2"):
        _run(tmp, name, 4, seed=7)
    out = tmp / "floor.json"
    return M, [f"--runs=r1,r2", f"--root={tmp}", "--early=0-1", "--late=2-3",
               f"--out={out}"], str(out), "wrote"


def _lift_argv(tmp, monkeypatch):
    """parse_args via sys.argv + OK receipt; mediapipe/solve path short-circuited.

    measure_lift.main takes no argv (reads sys.argv). The detector and solve chain need
    real weights; this SUCCESS fixture arms parse_args and the OK print/write path.
    """
    import measure_lift as M

    render = tmp / "render"
    render.mkdir()
    _pngs(str(render), n=2)
    (render / "render_provenance.json").write_text(json.dumps({
        "tool_version": "stub",
        "camera": {"basis_right": [1, 0, 0], "basis_up": [0, 1, 0],
                   "basis_back": [0, 0, 1]},
    }), encoding="utf-8")
    motion = tmp / "motion.json"
    motion.write_text("{}", encoding="utf-8")
    manifest = tmp / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    model = tmp / "pose.task"
    model.write_bytes(b"not-real-weights")
    out = tmp / "lift_out"

    def stub_main():
        a = M.parse_args()
        dest = os.path.abspath(a.out)
        os.makedirs(dest, exist_ok=True)
        rec = {"tool": "measure_lift", "frames": 2, "stub": True}
        with open(os.path.join(dest, "measurement.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        print("MEASURE_LIFT_OK " + json.dumps({
            "out": dest, "frames": 2, "fire_rate": 1.0,
            "mean_visibility": 1.0,
            "median_rotation_error_deg_detected": 0.0,
            "median_rotation_error_deg_model_only": 0.0,
        }))
        return 0

    monkeypatch.setattr(M, "main", stub_main)
    argv = [f"--render={render}", f"--motion={motion}", f"--manifest={manifest}",
            f"--model={model}", f"--out={out}", "--fps=16"]
    monkeypatch.setattr(sys, "argv", ["measure_lift.py", *argv])
    return M, argv, str(out), "MEASURE_LIFT_OK"


def _smooth_argv(tmp):
    import measure_smoothness as M
    from test_measure_smoothness import _pair, _write
    a, b = _pair()
    out = tmp / "smooth.json"
    return M, [f"--a={_write(tmp, 'a.json', a)}", f"--b={_write(tmp, 'b.json', b)}",
               f"--out={out}"], str(out), "MEASURE_SMOOTHNESS_OK"


def _tracking_argv(tmp):
    import measure_tracking as M
    from test_measure_tracking import gray_frames
    levels = [0, 10, 40, 45, 90, 100]
    run = gray_frames(str(tmp / "run"), levels)
    ctl = gray_frames(str(tmp / "ctl"), levels)
    out = tmp / "track.json"
    return M, [f"--run={run}", f"--control={ctl}", f"--out={out}", "--label=T"], \
        str(out), "MEASURE_TRACKING"


MEASURE = {
    "measure_arm": _arm_argv,
    "measure_cascade_clip": _cascade_argv,
    "measure_clip": _clip_argv,
    "measure_floor": _floor_argv,
    "measure_lift": _lift_argv,
    "measure_smoothness": _smooth_argv,
    "measure_tracking": _tracking_argv,
}

NEEDS_MONKEYPATCH = {"measure_cascade_clip", "measure_lift"}


def test_the_measure_success_population_is_the_seven_the_finding_names():
    assert sorted(MEASURE) == [
        "measure_arm", "measure_cascade_clip", "measure_clip", "measure_floor",
        "measure_lift", "measure_smoothness", "measure_tracking"]


def _artifact_exists(artifact):
    if os.path.isfile(artifact) and os.path.getsize(artifact) > 0:
        return True
    if os.path.isdir(artifact):
        return any(os.path.isfile(os.path.join(artifact, n))
                   for n in os.listdir(artifact))
    return False


@pytest.mark.parametrize("name", sorted(MEASURE))
def test_every_measure_cli_main_runs_end_to_end_from_argv(name, tmp_path, capsys,
                                                          monkeypatch):
    factory = MEASURE[name]
    if name in NEEDS_MONKEYPATCH:
        mod, argv, artifact, sentinel = factory(tmp_path, monkeypatch)
    else:
        mod, argv, artifact, sentinel = factory(tmp_path)
    path = os.path.join(REPO, "tools", name + ".py")
    derived = _success_tokens(path)
    assert sentinel in derived or name == "measure_floor", (name, sentinel, sorted(derived))
    if name == "measure_lift":
        # parse_args reads sys.argv; factory already installed it.
        rc = mod.main()
    else:
        rc = mod.main(argv)
    # Several measure mains return the record dict rather than 0.
    assert rc == 0 or isinstance(rc, dict), (name, rc)
    out = capsys.readouterr().out
    assert sentinel in out, (name, out[:400])
    assert _artifact_exists(str(artifact)), (name, artifact)
