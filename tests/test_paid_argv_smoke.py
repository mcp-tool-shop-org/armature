"""Paid CLI `main(argv)` SUCCESS fixtures — shrink NO_SUCCESS_FIXTURE (wave 34).

F-fbe68663: the suite's only end-to-end SUCCESS fixtures were five plate sheets, so every
spend builder / fetcher / pre-submit gate could still ship a `main(argv)` that dies before
writing a receipt while unit homes stayed green — the gate0 class. This sibling of
`test_sheet_argv_smoke.py` drives each of the fifteen paid members with a minimal tempfile
fixture: exit 0, the tool's own OK sentinel, and the named artifact on disk.
"""

from __future__ import annotations

import ast
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS, FIXTURES  # noqa: F401
import _census_nodes as CN

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESCAPE = ["--subject", "PERFORMER", "--no-canon"]
STUB_IDENTITY = "a jointed clay mannequin"


def _success_tokens(path):
    """Success sentinel(s) printed on the SUCCESS path.

    Sheet tools print inside `main`; several paid builders print from `build_and_write`
    (or a sibling) that `main` returns. Walk every module-level function's `print` calls
    so a delegated OK token is still derived from source rather than typed twice.
    """
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
                if token.endswith("_OK") or token == "ENCODE_CONTROL":
                    tokens.add(token)
    return tokens


def _authored_png(path, size):
    from armature_core import pngio
    pngio.write_png(str(path), np.zeros((size[1], size[0], 3), dtype="uint8"))
    return path


def _neg(tmp):
    p = tmp / "shared_config.py"
    p.write_text("sample_neg_prompt = 'blurry, low quality'", encoding="utf-8")
    return p


def _assembly_argv(tmp):
    import build_assembly_payload as B
    n = 5
    up = tmp / "uploads.json"
    up.write_text(json.dumps({f"{i:05d}.png": f"{i:064x}.png" for i in range(n)}),
                  encoding="utf-8")
    out = tmp / "assembly_out"
    return B, [f"--uploads={up}", f"--out={out}"], str(out / "S03-assembly.api.json"), \
        "BUILD_ASSEMBLY_OK"


def _cascade_argv(tmp):
    import build_cascade_payload as B
    n = 9
    up = tmp / "uploads.json"
    up.write_text(json.dumps({f"{i:05d}.png": f"{i:064x}.png" for i in range(n)}),
                  encoding="utf-8")
    out = tmp / "cascade_out"
    return B, [f"--uploads={up}", f"--out={out}", "--group=3"], \
        str(out / "E13-cascade.api.json"), "BUILD_CASCADE_OK"


def _t2v_argv(tmp):
    import build_t2v_payload as B
    seeds = tmp / "seeds.json"
    seeds.write_text(json.dumps({"seeds": [2026081201]}), encoding="utf-8")
    out = tmp / "t2v_out"
    return B, [f"--seeds={seeds}", f"--out={out}", *ESCAPE], out, "BUILD_T2V_OK"


def _payload_argv(tmp):
    import build_payload as B
    out = tmp / "run" / "B2.json"
    return B, ["--experiment", "E03", "--arm", "B2", "--out", str(out), *ESCAPE], \
        str(out), "BUILD_PAYLOAD_OK"


def _lora_argv(tmp):
    import build_lora_arm_payload as B
    base = os.path.join(FIXTURES, "E12-w3-camera-i2v.api.json")
    out = tmp / "lora_out"
    registry = os.path.join(REPO, "specs", "E14-seeds.json")
    return B, [f"--base={base}", "--arm=T", f"--out={out}",
               f"--seeds-registry={registry}", "--seed=2026081233", *ESCAPE], \
        out, "BUILD_LORA_ARM_OK"


def _r2v_argv(tmp):
    import build_r2v_payload as B
    from test_r2v_payload import NEG, PROMPT, REFS, SEEDS
    seeds = tmp / "seeds.json"
    seeds.write_text(json.dumps({"seeds": SEEDS}), encoding="utf-8")
    prompt = tmp / "prompt.json"
    prompt.write_text(json.dumps({"prompt": PROMPT, "negative_prompt": NEG}),
                      encoding="utf-8")
    refs = tmp / "refs.json"
    refs.write_text(json.dumps({"views": [
        {"slot": f"image{i + 1}", "view": f"turn_{i}", "upload_name": REFS[i]}
        for i in range(4)]}), encoding="utf-8")
    out = tmp / "r2v_out"
    return B, ["--arm=A1", f"--seed={SEEDS[0]}", f"--seeds={seeds}",
               f"--prompt-file={prompt}", f"--refs={refs}", f"--out={out}", *ESCAPE], \
        out, "BUILD_R2V_OK"


def _animate_argv(tmp, monkeypatch):
    import build_animate_payload as B
    monkeypatch.setattr(B, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _neg(tmp)
    up = tmp / "uploads.json"
    up.write_text(json.dumps({"reference": "r.png", "pose_pack": "p.png",
                              "pose_frames": 65}), encoding="utf-8")
    out = tmp / "animate_out"
    registry = os.path.join(REPO, "specs", "E08-seeds.json")
    return B, [f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
               "--seed=2026081211", f"--seeds-registry={registry}", *ESCAPE], \
        out, "BUILD_ANIMATE_OK"


def _i2v_argv(tmp, monkeypatch):
    import build_animate_payload as E08
    import build_i2v_payload as B
    monkeypatch.setattr(E08, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _neg(tmp)
    up = tmp / "uploads.json"
    up.write_text(json.dumps({"start_frame": "start.png"}), encoding="utf-8")
    e08 = tmp / "E08-record.json"
    e08.write_text(json.dumps({
        "experiment": "E08", "seed": 2026081211,
        "positive": STUB_IDENTITY + ". " + E08.SCENE_CLAUSE,
        "negative": E08.read_negative(str(neg))}), encoding="utf-8")
    start = tmp / "start.png"
    _authored_png(start, (B.WIDTH, B.HEIGHT))
    out = tmp / "i2v_out"
    registry = os.path.join(REPO, "specs", "E11-seeds.json")
    return B, [f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
               f"--e08-record={e08}", f"--start-frame={start}",
               f"--seeds-registry={registry}", *ESCAPE], out, "BUILD_I2V_OK"


def _camera_argv(tmp, monkeypatch):
    import build_animate_payload as E08
    import build_camera_i2v_payload as B
    from test_build_camera_i2v_payload import w1_record
    monkeypatch.setattr(E08, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _neg(tmp)
    up = tmp / "uploads.json"
    up.write_text(json.dumps({"start_frame": "w3_start.png"}), encoding="utf-8")
    w1 = tmp / "E11-probe-payload-record.json"
    w1.write_text(json.dumps(w1_record()), encoding="utf-8")
    start = tmp / "w3_start.png"
    _authored_png(start, (B.WIDTH, B.HEIGHT))
    out = tmp / "camera_out"
    registry = os.path.join(REPO, "specs", "E12-seeds.json")
    return B, [f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
               f"--w1-record={w1}", f"--start-frame={start}",
               f"--seeds-registry={registry}", *ESCAPE], out, "BUILD_CAMERA_I2V_OK"


def _canon_gate_argv(tmp):
    import canon_gate as B
    from test_canon import COVERED, FIXTURES as CANON_FIX
    census = tmp / "census.json"
    census.write_text('{"PROBE": {"surfaces": "probe.surfaces.json"}}', encoding="utf-8")
    out = tmp / "canon_ok"
    return B, ["--roots", CANON_FIX, "--census", str(census),
               "spend", "--subject", "PROBE", "--prompt", COVERED, "--out", str(out)], \
        str(out), "CANON_GATE_OK"


def _gate_b_argv(tmp):
    import gate_b_frames as B
    sticks = tmp / "sticks"
    batch = tmp / "batch"
    sticks.mkdir()
    batch.mkdir()
    for i in range(4):
        a = np.zeros((4, 6, 3), dtype=np.uint8)
        a[i % 4, i % 6] = (200, 30, 40)
        Image.fromarray(a).save(sticks / f"{i:05d}.png")
        Image.fromarray(a.copy()).save(batch / f"{i:05d}.png")
    out = tmp / "gate_b.json"
    return B, [f"--sticks={sticks}", f"--batchprobe={batch}", f"--out={out}"], \
        str(out), "GATE_B_OK"


def _gate_saved_argv(tmp):
    import gate_saved_graph as B
    from test_amend_w14_builders import ASSEMBLY_API, ASSEMBLY_SAVED, _builder_record
    d = tmp / "in"
    d.mkdir()
    (d / "g.api.json").write_text(json.dumps(ASSEMBLY_API), encoding="utf-8")
    (d / "g.saved.json").write_text(json.dumps(ASSEMBLY_SAVED), encoding="utf-8")
    (d / "seeds.json").write_text(json.dumps({"seeds": [2026081233]}), encoding="utf-8")
    rec = d / "payload-record.json"
    rec.write_text(json.dumps(_builder_record(
        ASSEMBLY_API, family="wan", carries_no_sampler=True, frame=(832, 480, 81))),
        encoding="utf-8")
    out = tmp / "out" / "admission.json"
    return B, [f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
               f"--seeds={d / 'seeds.json'}", f"--out={out}", f"--record={rec}",
               "--frame=832,480,81"], str(out), "SAVED_ADMISSION_OK"


def _fetch_run_argv(tmp, monkeypatch):
    import fetch_run as F
    import subprocess

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        manifest = env.get(F.MANIFEST_ENV)
        rows = []
        if manifest and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                for job in json.load(fh):
                    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                    body = bytearray(b"\x00" * 32)
                    body[0:8] = F.PNG_SIGNATURE
                    with open(job["out"], "wb") as out:
                        out.write(bytes(body))
                    rows.append({"out": job["out"], "url": job["url"], "code": 0,
                                 "message": ""})
        exits = env.get(F.EXITS_ENV)
        if exits:
            with open(exits, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = tmp / "get_output.json"
    dump.write_text(json.dumps({"results": [
        {"source_node_id": "302", "filename": f"{i:064x}.png",
         "url": f"https://example.invalid/{i}.png"} for i in range(2)]}),
        encoding="utf-8")
    root = tmp / "runs"
    return F, [f"--dump={dump}", "--run=r", f"--root={root}"], \
        str(root / "r" / "lossless"), "FETCH_RUN_OK"


def _fetch_t2v_argv(tmp, monkeypatch):
    import fetch_t2v_run as T
    from test_fetch_t2v_run import E09_ARRAY, E09_HASH, _ev, _exits_receipt

    dump = tmp / "dump.json"
    dump.write_text(json.dumps({"results": [
        {"source_node_id": 70, "filename": f"{i:064x}.png", "url": f"u{i}"}
        for i in range(3)]}), encoding="utf-8")

    def fake_download(jobs, out=None):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            with open(j["out"], "wb") as fh:
                fh.write(T.PNG_SIGNATURE)
        return None, _exits_receipt(jobs)

    monkeypatch.setattr(T, "download", fake_download)
    monkeypatch.setattr(T, "order_evidence", lambda out: _ev(E09_ARRAY, E09_HASH))
    out = tmp / "t2v_run"
    return T, [f"--dump={dump}", f"--out={out}"], str(out), "FETCH_T2V_OK"


def _encode_control_argv(tmp, monkeypatch):
    import encode_control as EC

    def fake_encode(frames, path, codec, fps=16):
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"".join(f.tobytes() for f in frames))
        fake_encode.frames = [f.copy() for f in frames]
        return path

    monkeypatch.setattr(EC, "encode", fake_encode)
    monkeypatch.setattr(EC, "decode", lambda path, w, h: fake_encode.frames)
    monkeypatch.setattr(EC, "gate_ffmpeg_binary", lambda: None)
    d = tmp / "frames"
    d.mkdir()
    for i in range(3):
        Image.fromarray(np.zeros((8, 6), dtype=np.uint8)).save(d / f"{i:05d}.png")
    out = tmp / "out" / "control.mkv"
    return EC, [f"--frames={d}", f"--out={out}"], str(out), "ENCODE_CONTROL"


#: name -> factory(tmp[, monkeypatch]) -> (mod, argv, artifact, sentinel)
#: Factories that need monkeypatch take it as a second positional.
PAID = {
    "build_assembly_payload": _assembly_argv,
    "build_cascade_payload": _cascade_argv,
    "build_t2v_payload": _t2v_argv,
    "build_payload": _payload_argv,
    "build_lora_arm_payload": _lora_argv,
    "build_r2v_payload": _r2v_argv,
    "build_animate_payload": _animate_argv,
    "build_i2v_payload": _i2v_argv,
    "build_camera_i2v_payload": _camera_argv,
    "canon_gate": _canon_gate_argv,
    "gate_b_frames": _gate_b_argv,
    "gate_saved_graph": _gate_saved_argv,
    "fetch_run": _fetch_run_argv,
    "fetch_t2v_run": _fetch_t2v_argv,
    "encode_control": _encode_control_argv,
}

NEEDS_MONKEYPATCH = {
    "build_animate_payload", "build_i2v_payload", "build_camera_i2v_payload",
    "fetch_run", "fetch_t2v_run", "encode_control",
}


def test_the_paid_success_population_is_the_fifteen_the_finding_names():
    assert sorted(PAID) == [
        "build_animate_payload", "build_assembly_payload", "build_camera_i2v_payload",
        "build_cascade_payload", "build_i2v_payload", "build_lora_arm_payload",
        "build_payload", "build_r2v_payload", "build_t2v_payload", "canon_gate",
        "encode_control", "fetch_run", "fetch_t2v_run", "gate_b_frames",
        "gate_saved_graph"]


def _artifact_exists(artifact):
    if os.path.isfile(artifact) and os.path.getsize(artifact) > 0:
        return True
    if os.path.isdir(artifact):
        return any(os.path.isfile(os.path.join(artifact, n))
                   for n in os.listdir(artifact))
    # Some builders write a glob of *.api.json under the out dir
    parent = os.path.dirname(artifact) if not os.path.isdir(artifact) else artifact
    if os.path.isdir(parent):
        return any(n.endswith(".api.json") or n.endswith(".json") or n.endswith(".mkv")
                   for n in os.listdir(parent))
    return False


@pytest.mark.parametrize("name", sorted(PAID))
def test_every_paid_cli_main_runs_end_to_end_from_argv(name, tmp_path, capsys, monkeypatch):
    """SUCCESS direction: exit 0, the tool's own sentinel, and an artifact on disk."""
    factory = PAID[name]
    if name in NEEDS_MONKEYPATCH:
        mod, argv, artifact, sentinel = factory(tmp_path, monkeypatch)
    else:
        mod, argv, artifact, sentinel = factory(tmp_path)
    path = os.path.join(REPO, "tools", name + ".py")
    derived = _success_tokens(path)
    assert sentinel in derived, (name, sentinel, sorted(derived))
    assert mod.main(argv) == 0, name
    out = capsys.readouterr().out
    assert sentinel in out, (name, out[:400])
    assert _artifact_exists(str(artifact)), (name, artifact)
