"""Wave 34 — instruments-measure feature-execute (five HIGH findings).

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

import compare_runs as CR  # noqa: E402
import encode_control as EC  # noqa: E402
import make_ab_clip as AB  # noqa: E402
import make_review_clip as MRC  # noqa: E402
import measure_floor as MF  # noqa: E402


def _png(path, size=(16, 12), colour=(10, 20, 30)):
    Image.fromarray(np.full((*size[::-1], 3), colour, dtype=np.uint8)).save(path)


def _gray_png(path, size=(16, 12), value=40):
    Image.fromarray(np.full(size[::-1], value, dtype=np.uint8), mode="L").save(path)


def _flat_frames(tmp, name, n=3, colour=(10, 20, 30)):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        _png(d / f"{i:05d}.png", colour=colour)
    return str(d)


def _lossless_run(tmp, name, n=4, seed=0):
    d = tmp / name / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    for i in range(n):
        Image.fromarray(rng.integers(0, 256, (8, 8, 3), dtype=np.uint8)).save(
            d / f"{i:05d}.png")
    return name


# --------------------------------------------------------------------------- F-38b79919


def test_seed_spread_mode_labels_the_record_and_requires_seeds(tmp_path):
    """F-38b79919 — seed-spread is a first-class quantity, not the fixed-seed floor."""
    for name, seed in (("s1", 1), ("s2", 2)):
        _lossless_run(tmp_path, name, n=4, seed=seed)
    out = tmp_path / "seed_spread.json"
    with pytest.raises(MF.FloorError) as e:
        MF.main(["--mode=seed-spread", f"--root={tmp_path}", f"--out={out}"])
    assert e.value.evidence["clause"] == "seeds_required_for_seed_spread"
    assert not out.exists()

    rec = MF.main([
        "--mode=seed-spread", "--seeds=s1,s2", f"--root={tmp_path}",
        "--early=0-1", "--late=2-3", f"--out={out}",
    ])
    assert rec["mode"] == "seed-spread"
    assert rec["quantity"] == "seed_spread"
    assert rec["runs"] == ["s1", "s2"]
    assert "window_source" in rec
    assert "python_executable" in rec
    assert out.exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["quantity"] == "seed_spread"


def test_fixed_seed_mode_refuses_seeds_flag(tmp_path):
    """F-38b79919 — --seeds cannot silently ride a fixed-seed record."""
    for name in ("r1", "r2"):
        _lossless_run(tmp_path, name, n=3, seed=0)
    with pytest.raises(MF.FloorError) as e:
        MF.main(["--mode=fixed-seed", "--runs=r1,r2", "--seeds=r1,r2",
                 f"--root={tmp_path}", f"--out={tmp_path / 'f.json'}"])
    assert e.value.evidence["clause"] == "seeds_not_valid_for_fixed_seed"


# --------------------------------------------------------------------------- F-b8bf8e7d


def test_channel_pixel_mode_distinguishes_gray_from_rgb(tmp_path):
    """F-b8bf8e7d — pack codec safety keys off measured channel pixels."""
    gray = tmp_path / "depth"
    rgb = tmp_path / "normal"
    gray.mkdir()
    rgb.mkdir()
    _gray_png(gray / "00000.png")
    _png(rgb / "00000.png", colour=(10, 200, 30))
    assert EC.channel_pixel_mode(str(gray)) == "gray"
    assert EC.channel_pixel_mode(str(rgb)) == "rgb"


def test_trap_codec_refused_for_rgb_channel_by_survey(tmp_path):
    """F-b8bf8e7d — x264-qp0-yuv420 is unsafe for rgb per --survey."""
    # Synthetic survey row matching the live trap shape without re-running ffmpeg.
    rows = [{
        "codec": "x264-qp0-yuv420",
        "grayscale": "max|delta|=1",
        "rgb": "max|delta|=233",
        "note": "THE TRAP",
        "container": ".mp4",
    }, {
        "codec": "ffv1-gbrp",
        "grayscale": "lossless",
        "rgb": "lossless",
        "note": "ok",
        "container": ".mkv",
    }]
    with pytest.raises(EC.EncodeFailure) as e:
        EC.gate_codec_safe_for_mode("x264-qp0-yuv420", "rgb", survey_rows=rows)
    assert e.value.evidence["clause"] == "codec_unsafe_for_channel_mode"
    assert e.value.evidence["mode"] == "rgb"
    ok = EC.gate_codec_safe_for_mode("ffv1-gbrp", "rgb", survey_rows=rows)
    assert ok["verdict"] == "PASS"


def test_run_pack_reads_channel_dirs_and_writes_pack_receipt(tmp_path, monkeypatch):
    """F-b8bf8e7d — --run encodes each channel_dirs entry into one pack receipt."""
    run = tmp_path / "stage"
    depth = run / "depth"
    normal = run / "normal"
    depth.mkdir(parents=True)
    normal.mkdir()
    for i in range(2):
        _gray_png(depth / f"{i:05d}.png", value=20 + i)
        _png(normal / f"{i:05d}.png", colour=(i + 1, 40, 200))
    manifest = {
        "tool": "stage_render",
        "tool_version": "test",
        "channel_dirs": {"depth": "depth", "normal": "normal"},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fake_receipt = {
        "video_sha256": "ab" * 32,
        "source_frames_sha256": "cd" * 32,
        "n_frames": 2,
        "gate_R": {"verdict": "PASS", "evidence": {}},
    }

    def fake_build(frames_dir, out_path, codec, invert=False, fps=16, expect=None,
                   alpha_over=None, progress=None):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(b"fake-video")
        with open(out_path + ".receipt.json", "w", encoding="utf-8") as fh:
            json.dump(fake_receipt, fh)
        return {**fake_receipt, "video": out_path, "frames_dir": frames_dir,
                "alpha_disposition": "none"}

    monkeypatch.setattr(EC, "build", fake_build)
    monkeypatch.setattr(EC, "survey_codecs", lambda: [
        {"codec": "ffv1-gbrp", "grayscale": "lossless", "rgb": "lossless",
         "note": "ok", "container": ".mkv"},
    ])
    monkeypatch.setattr(EC, "ffmpeg_version", lambda: "test-ffmpeg")
    monkeypatch.setattr(EC, "gate_ffmpeg_binary", lambda: None)
    monkeypatch.setattr(EC, "gate_encode_rate", lambda fps: fps)

    pack = EC.build_control_pack(str(run), "ffv1-gbrp", survey_rows=[
        {"codec": "ffv1-gbrp", "grayscale": "lossless", "rgb": "lossless",
         "note": "ok", "container": ".mkv"},
    ])
    assert pack["kind"] == "control_pack"
    assert sorted(pack["channels"]) == ["depth", "normal"]
    assert pack["channels"]["depth"]["mode"] == "gray"
    assert pack["channels"]["normal"]["mode"] == "rgb"
    assert pack["gate_R_all"]["verdict"] == "PASS"
    pack_path = run / "control_pack.receipt.json"
    assert pack_path.is_file()
    assert (run / "control_videos" / "depth.mkv").is_file()
    assert (run / "control_videos" / "normal.mkv").is_file()


def test_run_pack_refuses_trap_codec_before_encode(tmp_path, monkeypatch):
    """F-b8bf8e7d — mixed-fidelity pack cannot form around the trap codec."""
    run = tmp_path / "stage"
    normal = run / "normal"
    normal.mkdir(parents=True)
    _png(normal / "00000.png", colour=(10, 200, 30))
    (run / "manifest.json").write_text(json.dumps({
        "tool": "stage_render",
        "channel_dirs": {"normal": "normal"},
    }), encoding="utf-8")
    called = {"build": 0}

    def boom(*_a, **_k):
        called["build"] += 1
        raise AssertionError("build must not run after codec safety refusal")

    monkeypatch.setattr(EC, "build", boom)
    with pytest.raises(EC.EncodeFailure) as e:
        EC.build_control_pack(str(run), "x264-qp0-yuv420", survey_rows=[{
            "codec": "x264-qp0-yuv420",
            "grayscale": "max|delta|=1",
            "rgb": "max|delta|=233",
            "note": "TRAP",
            "container": ".mp4",
        }])
    assert e.value.evidence["clause"] == "codec_unsafe_for_channel_mode"
    assert called["build"] == 0
    assert not (run / "control_pack.receipt.json").exists()


# --------------------------------------------------------------------------- F-cdd95afb


def _detection_rows(n=3, w=16, h=16):
    """Minimal detector rows: 33 landmarks, nose at top-centre, wrists/ankles elsewhere."""
    rows = []
    for i in range(n):
        image = [[0.5, 0.5]] * 33
        image[0] = [0.5, 0.15]   # nose / face
        image[15] = [0.2, 0.7]   # hand_L
        image[16] = [0.8, 0.7]   # hand_R
        image[27] = [0.3, 0.9]   # foot_L
        image[28] = [0.7, 0.9]   # foot_R
        rows.append({
            "file": f"{i:05d}.png",
            "fired": True,
            "image": image,
        })
    return rows


def test_review_clip_default_targets_include_face_with_detection(tmp_path, capsys):
    """F-cdd95afb — face (nose) is in the default still population when detection fires."""
    frames = _flat_frames(tmp_path, "lossless", n=3)
    det_path = tmp_path / "detection_raw.json"
    det_path.write_text(json.dumps({"rows": _detection_rows(3)}), encoding="utf-8")
    out = tmp_path / "review"
    assert MRC.main([
        f"--frames={frames}", f"--out={out}", f"--detection={det_path}",
        "--stills=0,2", "--crop=8",
    ]) == 0
    assert "MAKE_REVIEW_CLIP_OK " in capsys.readouterr().out
    stills = sorted(n for n in os.listdir(out) if n.startswith("still_"))
    assert any("_face.png" in n for n in stills), stills
    # 2 frames × 5 targets (hands, feet, face)
    assert len(stills) == 10, stills
    man = json.loads((out / "review_manifest.json").read_text(encoding="utf-8"))
    assert "face" in man["targets"]
    assert man["target_landmarks"]["face"] == 0


def test_review_clip_targets_flag_is_operator_extensible(tmp_path):
    """F-cdd95afb — --targets=face alone cuts only face stills."""
    frames = _flat_frames(tmp_path, "lossless", n=2)
    det_path = tmp_path / "detection_raw.json"
    det_path.write_text(json.dumps({"rows": _detection_rows(2)}), encoding="utf-8")
    out = tmp_path / "review"
    assert MRC.main([
        f"--frames={frames}", f"--out={out}", f"--detection={det_path}",
        "--stills=0", "--crop=8", "--targets=face",
    ]) == 0
    stills = sorted(n for n in os.listdir(out) if n.startswith("still_"))
    assert stills == ["still_f000_face.png"]


def test_review_clip_targets_without_detection_is_refused(tmp_path):
    frames = _flat_frames(tmp_path, "lossless", n=2)
    out = tmp_path / "review"
    with pytest.raises(MRC.ReviewClipError) as e:
        MRC.main([f"--frames={frames}", f"--out={out}", "--stills=0",
                  "--crop=8", "--targets=face"])
    assert e.value.evidence["clause"] == "targets_require_detection"


# --------------------------------------------------------------------------- F-f174c9e2


def test_gate0_mode_requires_meta_and_matched_fps(tmp_path):
    """F-f174c9e2 — Gate 0 motion binds control|output under provenance + matched fps."""
    ctl = _flat_frames(tmp_path, "ctl", n=3, colour=(5, 5, 5))
    outf = _flat_frames(tmp_path, "out", n=3, colour=(50, 60, 70))
    with pytest.raises(AB.ABClipError) as e:
        AB.main(["--mode=gate0", f"--a={ctl}", f"--b={outf}",
                 "--a-fps=16", "--b-fps=16", f"--out={tmp_path / 'g.webp'}"])
    assert e.value.evidence["clause"] == "gate0_meta_required"

    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "arm": "A1", "seed": 7, "prompt_id": "p",
        "resolution": [16, 12], "length": 3, "fps": 16,
    }), encoding="utf-8")
    with pytest.raises(AB.ABClipError) as e2:
        AB.main(["--mode=gate0", f"--a={ctl}", f"--b={outf}",
                 "--a-fps=16", "--b-fps=20", f"--meta={meta}",
                 f"--out={tmp_path / 'g.webp'}"])
    assert e2.value.evidence["clause"] == "gate0_fps_mismatch"


def test_gate0_mode_writes_provenance_sidecar_with_sha_populations(tmp_path, capsys):
    """F-f174c9e2 — sidecar lists control/output sha populations + provenance lines."""
    ctl = _flat_frames(tmp_path, "ctl", n=3, colour=(5, 5, 5))
    outf = _flat_frames(tmp_path, "out", n=3, colour=(50, 60, 70))
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "experiment": "E99", "arm": "A1", "seed": 7, "prompt_id": "abc",
        "resolution": [16, 12], "length": 3, "fps": 16,
        "models": {"unet": "test-unet"},
    }), encoding="utf-8")
    clip = tmp_path / "gate0.webp"
    assert AB.main([
        "--mode=gate0", f"--a={ctl}", f"--b={outf}",
        "--a-fps=16", "--b-fps=16", f"--meta={meta}", f"--out={clip}",
    ]) == 0
    assert "MAKE_AB_CLIP_OK " in capsys.readouterr().out
    assert clip.is_file()
    side = tmp_path / "gate0_manifest.json"
    man = json.loads(side.read_text(encoding="utf-8"))
    assert man["mode"] == "gate0"
    assert man["a"]["label"] == "control"
    assert man["b"]["label"] == "output"
    assert "gate0" in man
    assert "NOT RECORDED" in "\n".join(man["gate0"]["provenance_lines"])
    assert len(man["gate0"]["control_sha_population"]) == 3
    assert len(man["gate0"]["output_sha_population"]) == 3
    assert man["composite"]["gate_TIMELINE"]["a"]["verdict"].startswith("contiguous")


# --------------------------------------------------------------------------- F-fd89dddf


def test_frames_mode_compares_flat_lossless_dirs(tmp_path, capsys):
    """F-fd89dddf — --mode=frames exposes compare_channel on flat generation dirs."""
    a = _flat_frames(tmp_path, "A", n=3, colour=(10, 20, 30))
    b = _flat_frames(tmp_path, "B", n=3, colour=(10, 20, 31))  # one channel off by 1
    out = tmp_path / "report.json"
    # Default channels mode still andons on flat dirs.
    with pytest.raises(CR.CompareError, match="share no comparable channel"):
        CR.compare_runs(a, b)

    report = CR.compare_frames(a, b)
    assert report["mode"] == "frames"
    assert list(report["channels"]) == ["lossless"]
    assert report["verdict_inputs"]["max_abs_diff_any_channel"] == 1
    assert report["verdict_inputs"]["frames_compared"] == 3

    assert CR.main(["--mode=frames", f"--a={a}", f"--b={b}", f"--out={out}"]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("COMPARE_RUNS_OK ")
    line = json.loads(printed[len("COMPARE_RUNS_OK "):])
    assert line["mode"] == "frames"
    assert line["max_abs_diff_any_channel"] == 1
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["mode"] == "frames"
    assert saved["channels"]["lossless"]["max_abs_diff"] == 1
    assert saved["channels"]["lossless"]["worst_frame"] is not None


def test_channels_mode_keeps_channel_layout_andon(tmp_path):
    """F-fd89dddf — channels mode still refuses two flat dirs."""
    a = _flat_frames(tmp_path, "A", n=2)
    b = _flat_frames(tmp_path, "B", n=2)
    with pytest.raises(CR.CompareError) as e:
        CR.main(["--mode=channels", f"--a={a}", f"--b={b}"])
    assert e.value.evidence.get("hint") == "--mode=frames" or "shared" in e.value.evidence
