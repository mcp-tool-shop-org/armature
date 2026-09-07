"""Wave 35 — instruments-measure feature-execute (five MEDIUM findings).

Each test goes red without the fix and green beside it. In-process claims read the
module the worktree's PYTHONPATH resolves.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

sys.path.insert(0, TOOLS)
sys.path.insert(0, TESTS)

import fit_reference as FR  # noqa: E402
import make_gate0_sheet as G0  # noqa: E402
import make_sheet as MS  # noqa: E402
import measure_floor as MF  # noqa: E402

from armature_core.gates import G1GeneratorLegality  # noqa: E402


def _png(path, size=(16, 12), colour=(10, 20, 30)):
    Image.fromarray(np.full((*size[::-1], 3), colour, dtype=np.uint8)).save(path)


def _lossless_run(tmp, name, n=4, seed=0, colour=None):
    d = tmp / name / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    for i in range(n):
        if colour is None:
            arr = rng.integers(0, 256, (8, 8, 3), dtype=np.uint8)
        else:
            arr = np.full((8, 8, 3), colour, dtype=np.uint8)
        Image.fromarray(arr).save(d / f"{i:05d}.png")
    return name


def _flat_frames(tmp, name, n=3, colour=(10, 20, 30)):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        _png(d / f"{i:05d}.png", colour=colour)
    return str(d)


# --------------------------------------------------------------------------- F-d5940490


def test_measure_floor_root_is_required_no_e02_default():
    """F-d5940490 — omitting --root must refuse, not silently use outputs/E02/runs."""
    with pytest.raises(SystemExit) as e:
        MF.main(["--runs=r1,r2", "--out=floor.json"])
    assert e.value.code == 2  # argparse missing --root


def test_measure_floor_out_defaults_beside_root(tmp_path):
    """F-d5940490 — omitted --out lands at <root>/floor.json, not outputs/E02/."""
    for name in ("r1", "r2"):
        _lossless_run(tmp_path, name, n=4, seed=0, colour=(11, 22, 33))
    rec = MF.main(["--runs=r1,r2", f"--root={tmp_path}", "--early=0-1", "--late=2-3"])
    assert rec["runs"] == ["r1", "r2"]
    out = tmp_path / "floor.json"
    assert out.is_file(), "default --out must be <root>/floor.json"
    assert "E02" not in str(out)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["quantity"] == "fixed_seed_floor"


def test_measure_floor_seed_spread_out_defaults_beside_root(tmp_path):
    """F-d5940490 — seed-spread default is <root>/seed_spread.json."""
    for name, seed in (("s1", 1), ("s2", 2)):
        _lossless_run(tmp_path, name, n=4, seed=seed)
    MF.main([
        "--mode=seed-spread", "--seeds=s1,s2", f"--root={tmp_path}",
        "--early=0-1", "--late=2-3",
    ])
    assert (tmp_path / "seed_spread.json").is_file()
    assert not (tmp_path / "floor.json").exists()


# --------------------------------------------------------------------------- F-88c4045d


def test_floor_sheet_puts_reruns_beside_provenance(tmp_path, capsys):
    """F-88c4045d — floor sheet tiles re-run frames and prints window_source + pairs."""
    for name, colour in (("r1", (10, 20, 30)), ("r2", (10, 20, 30)), ("r3", (40, 50, 60))):
        _lossless_run(tmp_path, name, n=4, seed=0, colour=colour)
    floor_path = tmp_path / "floor.json"
    MF.main([
        "--runs=r1,r2,r3", f"--root={tmp_path}", "--early=0-1", "--late=2-3",
        f"--out={floor_path}",
    ])
    sheet_out = tmp_path / "floor_sheet.png"
    rec = MF.main([
        "--sheet", f"--floor={floor_path}", f"--root={tmp_path}",
        "--frames=0,2", f"--out={sheet_out}",
    ])
    assert sheet_out.is_file()
    assert rec["frames"] == [0, 2]
    assert "FLOOR_SHEET " in capsys.readouterr().out
    floor_rec = json.loads(floor_path.read_text(encoding="utf-8"))
    lines = "\n".join(MF.floor_provenance_lines(floor_rec))
    assert "window_source" in lines
    assert "bit-identical" in lines or "overall=" in lines
    assert "r1|r2" in lines or "r1|r3" in lines


def test_floor_sheet_requires_floor_flag(tmp_path):
    """F-88c4045d — --sheet without --floor is a typed refusal."""
    with pytest.raises(MF.FloorError) as e:
        MF.main(["--sheet", f"--root={tmp_path}", f"--out={tmp_path / 's.png'}"])
    assert e.value.evidence["clause"] == "sheet_requires_floor"


# --------------------------------------------------------------------------- F-e2e302b5


def test_gate0_measurements_print_under_provenance():
    """F-e2e302b5 — measure_clip headlines reach Gate 0 provenance as diagnostics."""
    meta = {"arm": "A1", "control": {}}
    measurements = {"d(frame) med": 1.25, "corr to f0": 0.5, "r=": 0.91}
    text = "\n".join(G0.provenance_lines(meta, measurements=measurements))
    assert "MEASURED (diagnostics; they gate nothing)" in text
    assert "d(frame) med" in text and "1.25" in text
    assert "r=" in text and "0.91" in text


def test_gate0_measurements_absent_when_not_supplied():
    """F-e2e302b5 — without --measurements the MEASURED block is not invented."""
    assert "MEASURED" not in "\n".join(G0.provenance_lines({"arm": "X"}))


def test_gate0_load_measurements_round_or_none_and_tracking(tmp_path):
    """F-e2e302b5 — loader uses round_or_none; tracking contributes r=."""
    clip = {
        "arms": [{
            "n_frames": 2,
            "distinct": {"n_distinct": 2},
            "frame_deltas": {"stats": {"median": None}},
            "luma": {"stats": {"median": 1.5}},
            "similarity_to_first": {"per_frame_correlation": [1.0, 0.25]},
            "horizon": {"n_found": 1},
        }]
    }
    clip_path = tmp_path / "clip.json"
    clip_path.write_text(json.dumps(clip), encoding="utf-8")
    loaded = G0.load_measurements(str(clip_path))
    assert loaded["d(frame) med"] is None  # round_or_none on null
    assert loaded["corr to f0"] == 0.25
    track_path = tmp_path / "track.json"
    track_path.write_text(json.dumps({"timing_correlation": 0.876543}), encoding="utf-8")
    track = G0.load_measurements(str(track_path))
    assert track["r="] == 0.8765


def test_gate0_main_accepts_measurements_flag(tmp_path, capsys):
    """F-e2e302b5 — CLI --measurements binds numbers onto the written sheet."""
    ctl = _flat_frames(tmp_path, "control", n=3, colour=(1, 2, 3))
    out_frames = _flat_frames(tmp_path, "frames", n=3, colour=(4, 5, 6))
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps({"arm": "A9", "experiment": "E99", "control": {}}),
                         encoding="utf-8")
    clip = {
        "arms": [{
            "n_frames": 3,
            "distinct": {"n_distinct": 3},
            "frame_deltas": {"stats": {"median": 2.0}},
            "luma": {"stats": {"median": 3.0}},
            "similarity_to_first": {"per_frame_correlation": [1.0, 0.9, 0.8]},
            "horizon": {"n_found": 0},
        }]
    }
    mpath = tmp_path / "m.json"
    mpath.write_text(json.dumps(clip), encoding="utf-8")
    sheet = tmp_path / "g0.png"
    assert G0.main([
        f"--run={ctl}", f"--frames-dir={out_frames}", "--reference=none",
        f"--meta={meta_path}", f"--out={sheet}", "--frames=0,1",
        f"--measurements={mpath}",
    ]) == 0
    assert sheet.is_file()
    assert "GATE0_SHEET " in capsys.readouterr().out
    # provenance_lines path already covered; CLI smoke is the flag wiring.


# --------------------------------------------------------------------------- F-c3572bf5


def test_fit_reference_route_refuses_illegal_width(tmp_path):
    """F-c3572bf5 — --route=wan-animate + width 831 raises G1 before write."""
    src = tmp_path / "twin.png"
    _png(src, size=(64, 128), colour=(20, 30, 40))
    out = tmp_path / "fit"
    with pytest.raises(G1GeneratorLegality) as e:
        FR.main([
            f"--src={src}", f"--out={out}", "--width=831", "--height=480",
            "--route=wan-animate",
        ])
    assert e.value.evidence["gate"] == "G1"
    assert not out.exists() or not any(out.iterdir()) if out.exists() else True


def test_fit_reference_route_records_profile_in_provenance(tmp_path):
    """F-c3572bf5 — legal --route writes generator_route into provenance JSON."""
    src = tmp_path / "twin.png"
    _png(src, size=(64, 128), colour=(20, 30, 40))
    out = tmp_path / "fit"
    assert FR.main([
        f"--src={src}", f"--out={out}", "--width=832", "--height=480",
        "--route=wan-animate", "--length=81",
    ]) == 0
    prov = next(out.glob("*_fit_provenance.json"))
    rec = json.loads(prov.read_text(encoding="utf-8"))
    assert rec["generator_route"]["route"] == "wan-animate"
    assert rec["generator_route"]["g1"] == "checked"
    assert rec["generator_route"]["length_checked"] == 81
    assert rec["generator_route"]["length_source"] == "caller"
    assert "profile_source" in rec["generator_route"]


def test_fit_reference_without_route_still_allows_exploratory_size(tmp_path):
    """F-c3572bf5 — bare --width/--height stay ungated for exploratory fits."""
    src = tmp_path / "twin.png"
    _png(src, size=(32, 64), colour=(5, 6, 7))
    out = tmp_path / "fit"
    assert FR.main([
        f"--src={src}", f"--out={out}", "--width=831", "--height=480",
    ]) == 0
    assert list(out.glob("*_fit_*.png"))


# --------------------------------------------------------------------------- F-ca0f0408


def _varied_frames(tmp, name, levels=(10, 20, 80)):
    """Frames whose inter-frame energy is non-constant so measure_tracking can correlate.

    Equal steps make a constant profile and pearson refuses; uneven steps are the point.
    """
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i, level in enumerate(levels):
        _png(d / f"{i:05d}.png", colour=(level, level // 2, level // 3))
    return str(d)


def test_dailies_manifest_builds_gate0_before_measure(tmp_path, capsys):
    """F-ca0f0408 — one manifest invocation yields GATE0 then MEASURE products."""
    ctl = _varied_frames(tmp_path, "control", levels=(10, 20, 80))
    frames = _varied_frames(tmp_path, "frames", levels=(12, 30, 90))
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps({
        "arm": "A1", "experiment": "E99", "control": {"polarity": "white-on-black"},
        "models": {"unet": "u.safetensors"},
    }), encoding="utf-8")
    out_dir = tmp_path / "dailies"
    man = {
        "control_dir": ctl,
        "frames_dir": frames,
        "reference": "none",
        "meta": str(meta_path),
        "out_dir": str(out_dir),
        "frames": "0,1",
        "stills": "0,1",
        "measure_clip": True,
        "measure_tracking": True,
        "review_clip": True,
        "ab_clip": False,
        "gate0_with_measurements": True,
    }
    man_path = tmp_path / "run.json"
    man_path.write_text(json.dumps(man), encoding="utf-8")
    assert MS.main([f"--dailies-manifest={man_path}"]) == 0
    out = capsys.readouterr().out
    assert "DAILIES_OK " in out
    assert (out_dir / "gate0_sheet.png").is_file()
    assert (out_dir / "measure_clip.json").is_file()
    assert (out_dir / "measure_tracking.json").is_file()
    assert (out_dir / "gate0_sheet_measured.png").is_file()
    # Gate 0 must appear before measure OK in the transcript.
    assert out.index("GATE0_SHEET ") < out.index("MEASURE_CLIP_OK ")


def test_dailies_manifest_missing_keys_refused(tmp_path):
    """F-ca0f0408 — incomplete manifest refuses before invoking tools."""
    man_path = tmp_path / "bad.json"
    man_path.write_text(json.dumps({"control_dir": "x"}), encoding="utf-8")
    with pytest.raises(MS.MakeSheetError) as e:
        MS.main([f"--dailies-manifest={man_path}"])
    assert e.value.evidence["clause"] == "dailies_manifest_missing_keys"
