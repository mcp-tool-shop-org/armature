"""Wave 29 — instruments-measure Stage D amend (six deferred findings).

Each test goes red on `a144540` without the fix and green beside it. Process claims are
driven as real subprocesses with this interpreter; in-process claims read the module the
worktree's PYTHONPATH resolves.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

sys.path.insert(0, TOOLS)
sys.path.insert(0, TESTS)

import encode_control as EC  # noqa: E402
import make_e08_sheet as M8  # noqa: E402
import make_gate0_sheet as G0  # noqa: E402
import measure_floor as MF  # noqa: E402


BARE_USAGE = (
    "analyze_p3", "armature_index", "compare_runs", "encode_control",
    "invert_frames", "lift_clip", "make_gate0_sheet", "make_identity_sheet",
    "make_lift_sheet", "make_review_clip", "make_sheet", "make_thesis_sheet",
    "measure_arm", "measure_floor", "measure_lift", "measure_tracking",
)

TEN_UNNAMED = (
    "composite_reference", "extract_clip_frames", "lift_clip", "make_e13_sheet",
    "make_identity_sheet", "make_lift_sheet", "make_pick_sheet", "make_review_clip",
    "measure_lift", "rig_sheet_compose",
)


def _run_tool(name, args, env=None):
    cmd = [sys.executable, os.path.join(TOOLS, f"{name}.py"), *args]
    e = os.environ.copy()
    e["PYTHONPATH"] = os.pathsep.join([REPO, TOOLS, e.get("PYTHONPATH", "")])
    if env:
        e.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=REPO, env=e, timeout=60)


def _png(path, colour=(10, 20, 30)):
    Image.fromarray(np.full((4, 4, 3), colour, dtype=np.uint8)).save(path)


# --------------------------------------------------------------------------- F-17905c61


@pytest.mark.parametrize("stem", BARE_USAGE)
def test_usage_lines_name_the_venv_python_not_a_bare_python(stem):
    """Usage examples start with `<venv-python>`, never a bare `python tools/`."""
    src = open(os.path.join(TOOLS, f"{stem}.py"), encoding="utf-8").read()
    # Module docstring usage lines only.
    m = re.match(r"(?s)^(?:#![^\n]*\n)?(r?)(\"\"\"|''')(.*?)(\2)", src)
    assert m, f"{stem}: no module docstring"
    doc = m.group(3)
    bare = re.findall(r"(?m)^[ \t]*python tools[/\\]", doc)
    assert bare == [], f"{stem}: bare python usage still present: {bare}"
    assert "<venv-python>" in doc, f"{stem}: missing <venv-python> usage marker"


# --------------------------------------------------------------------------- F-2ad4f715


def test_runtime_provenance_names_the_interpreter_and_imported_libs():
    block = EC.runtime_provenance({"numpy": np, "Pillow": Image})
    assert block["python_executable"] == sys.executable
    assert sys.version[:3] in block["python_version"]
    assert block["libraries"]["numpy"] == np.__version__
    assert "Pillow" in block["libraries"]


def test_encode_control_receipt_carries_runtime_beside_ffmpeg(tmp_path, monkeypatch):
    """A receipt names the Python that wrote it, not only the ffmpeg binary."""
    frames = tmp_path / "frames"
    frames.mkdir()
    for i in range(2):
        _png(frames / f"{i:05d}.png")
    out = tmp_path / "out.mkv"

    # Avoid a real ffmpeg round-trip: stub encode/decode/gate to the receipt writer.
    monkeypatch.setattr(EC, "read_frames", lambda *a, **k: (
        [f"{i:05d}.png" for i in range(2)],
        [np.zeros((4, 4, 3), dtype=np.uint8) for _ in range(2)],
        {"modes": ["RGB", "RGB"], "dtype": "uint8", "alpha_disposition": "none"},
    ))
    monkeypatch.setattr(EC, "encode", lambda *a, **k: None)
    monkeypatch.setattr(EC, "decode", lambda *a, **k: [
        np.zeros((4, 4, 3), dtype=np.uint8) for _ in range(2)
    ])
    monkeypatch.setattr(EC.gates, "gate_r_round_trip", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(EC, "ffmpeg_version", lambda: "stub")

    # write a fake video file for the sha
    out.write_bytes(b"fake-video")
    receipt = EC.build(str(frames), str(out), "ffv1-gbrp", fps=16)
    assert receipt["python_executable"] == sys.executable
    assert "libraries" in receipt
    assert "ffmpeg" in receipt


# --------------------------------------------------------------------------- F-5972c6dc


@pytest.mark.parametrize("stem", ("encode_control", "measure_floor", "compare_runs"))
def test_halt_contract_is_in_the_docstring_and_help_epilog(stem):
    src = open(os.path.join(TOOLS, f"{stem}.py"), encoding="utf-8").read()
    assert "Halt contract:" in src
    assert 'Reading a halt' in src
    assert "HALT_EPILOG" in src
    proc = _run_tool(stem, ["--help"])
    assert proc.returncode == 0
    assert "Halt contract:" in proc.stdout
    assert "Reading a halt" in proc.stdout


# --------------------------------------------------------------------------- F-6f968906


def test_gate0_provenance_prints_output_and_input_shas_or_not_recorded():
    lines = G0.provenance_lines({"payload_sha256": "abc" * 20})
    joined = "\n".join(lines)
    assert "output sha" in joined
    assert "control sha" in joined
    assert "reference sha" in joined
    assert "NOT RECORDED" in joined


def test_gate0_provenance_uses_record_and_overrides():
    lines = G0.provenance_lines(
        {"output_sha256": "out" * 20,
         "control": {"video_sha256": "ctl" * 20},
         "reference_image": {"sha256": "ref" * 20}},
        output_sha="OVERRIDE_OUT",
    )
    joined = "\n".join(lines)
    assert "OVERRIDE_OUT" in joined
    assert ("ctl" * 10)[:32] in joined or "ctlctl" in joined
    assert ("ref" * 10)[:32] in joined or "refref" in joined


def test_e08_provenance_prints_output_and_input_shas_or_not_recorded():
    lines = M8.provenance_lines({"payload_sha256": "abc" * 20, "experiment": "E08"})
    joined = "\n".join(lines)
    assert "output sha" in joined
    assert "control sha" in joined
    assert "reference sha" in joined
    assert "NOT RECORDED" in joined


# --------------------------------------------------------------------------- F-741a662f


@pytest.mark.parametrize("stem", TEN_UNNAMED)
def test_unnamed_tools_open_with_a_one_line_docstring_index_sentence(stem):
    """Code half: each of the ten carries a first-line docstring sentence (docs/tools.md source)."""
    src = open(os.path.join(TOOLS, f"{stem}.py"), encoding="utf-8").read()
    m = re.match(r"(?s)^(?:#![^\n]*\n)?(r?)(\"\"\"|''')(.*?)(\2)", src)
    assert m, f"{stem}: no module docstring"
    first = m.group(3).strip().splitlines()[0].strip()
    assert first, f"{stem}: empty first docstring line"
    assert stem.replace("_", "") in first.replace("_", "").lower() or stem.split("_")[0] in first.lower() or "—" in first or "-" in first


# --------------------------------------------------------------------------- F-a28128a4


def _two_runs(tmp_path, n=3):
    root = tmp_path / "runs"
    for name in ("r1", "r2"):
        d = root / name / "lossless"
        # measure_floor looks under run dir for numbered frames — use the helper path
        # the module's _stack expects. Mirror test_measure_floor layout.
        d = root / name
        d.mkdir(parents=True)
        for i in range(n):
            # Prefer lossless/ if the module expects it
            pass
    return root


def _floor_runs(tmp_path, names, n=3):
    root = tmp_path / "runs"
    for name in names:
        d = root / name / "lossless"
        d.mkdir(parents=True)
        for i in range(n):
            _png(d / f"{i:05d}.png", colour=(i * 10, 0, 0))
    return root


def test_measure_floor_refuses_to_overwrite_an_existing_record_without_the_flag(tmp_path):
    root = _floor_runs(tmp_path, ("r1", "r2"))
    out = tmp_path / "floor.json"
    rec1 = MF.main([f"--runs=r1,r2", f"--root={root}", f"--out={out}",
                    "--early=0-0", "--late=2-2"])
    assert out.is_file()
    assert rec1["runs"] == ["r1", "r2"]
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r1,r2", f"--root={root}", f"--out={out}",
                 "--early=0-0", "--late=2-2"])
    assert e.value.evidence["clause"] == "output_already_exists"
    kept = json.loads(out.read_text(encoding="utf-8"))
    assert kept["runs"] == ["r1", "r2"]


def test_measure_floor_overwrite_replaces_and_says_so(tmp_path, capsys):
    root = _floor_runs(tmp_path, ("r1", "r2", "r3"))
    out = tmp_path / "floor.json"
    MF.main([f"--runs=r1,r2,r3", f"--root={root}", f"--out={out}",
             "--early=0-0", "--late=2-2"])
    rec = MF.main([f"--runs=r1,r2", f"--root={root}", f"--out={out}",
                   "--early=0-0", "--late=2-2", "--overwrite"])
    assert rec["runs"] == ["r1", "r2"]
    assert rec["out_dir_pre_existed"] is True
    assert rec["overwrote"] == ["floor.json"]
    assert "python_executable" in rec
    printed = capsys.readouterr().out
    assert "replacing a record of runs=" in printed
    assert "n_frames=" in printed
    assert "wrote " in printed
