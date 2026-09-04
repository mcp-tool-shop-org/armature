"""Tests for the run fetcher's node map.

The map was a module constant naming E02's tap node ids, which meant pointing the tool at
any later experiment's dump sorted every frame into the fallback branch and printed a
plausible count. E10's closing lesson names the shape — *a tool that names an experiment
in a literal is a tool that will lie the first time it is reused* — and these fixtures
hold the flag that replaced it.
"""

import json
import os
import subprocess

import pytest

from conftest import TOOLS  # noqa: F401
import fetch_run as F


def test_no_map_keeps_the_default_taps():
    """E02, E08 and E10 all call this tool without the flag; their behaviour must not
    move because a later experiment needed a different mapping."""
    assert F.parse_node_map(None) == F.NODE_DIR
    assert F.parse_node_map("") == F.NODE_DIR
    assert F.parse_node_map(None) is not F.NODE_DIR, "callers must not mutate the default"


def test_a_map_replaces_the_taps_it_names():
    assert F.parse_node_map("41=startprobe,71=lossless") == {
        "41": "startprobe", "71": "lossless"}


def test_whitespace_and_trailing_commas_are_tolerated():
    assert F.parse_node_map(" 41 = startprobe , 71 = lossless , ") == {
        "41": "startprobe", "71": "lossless"}


@pytest.mark.parametrize("bad", ["41", "41=a=b", "=lossless", "71=", ","])
def test_a_malformed_map_halts_rather_than_falling_back_to_the_default(bad):
    """The dangerous outcome is not a crash. It is E02's mapping applied silently to
    another experiment's graph: every frame lands in the video branch, the files are
    named after the run, and the printed count looks entirely reasonable."""
    with pytest.raises(SystemExit):
        F.parse_node_map(bad)


# ------------------------------------------------------------------ the fallback branch
#
# Wave 3, F-183c8222 / F-61771e61 / F-dc669dd4. Three defects sat in one place: every
# result whose source node the map does not name was written to ONE path named after the
# run, the downloader's exit code was never inspected, and the manifest path was
# interpolated into a single-quoted PowerShell string.


def _dump(tmp_path, results):
    p = tmp_path / "get_output.json"
    p.write_text(json.dumps({"results": results}), encoding="utf-8")
    return str(p)


def _result(nid, i, ext=".png"):
    return {"source_node_id": nid, "filename": f"{i:064x}{ext}",
            "url": f"https://example.invalid/{i}{ext}"}


@pytest.fixture()
def stub_download(monkeypatch):
    """A downloader that writes one byte per planned output, and records its call."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "kw": kw})
        env = kw.get("env") or {}
        manifest = env.get("ARMATURE_FETCH_MANIFEST")
        if manifest and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                for job in json.load(fh):
                    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                    with open(job["out"], "wb") as out:
                        out.write(b"\x89PNG")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    return calls


def test_no_two_planned_results_ever_share_an_output_path():
    """The measured defect: a 5-frame dump from a graph whose tap is node 71, run without
    --node-map, printed by_node {"71": 5} and left one file. The printed count was the
    PLANNED count; the files had overwritten each other. `plan` is where that is decided,
    so the distinctness is pinned there, on every branch it can take."""
    results = ([_result("302", i) for i in range(3)]
               + [_result("114", i, ".mp4") for i in range(2)])
    jobs, counts = F.plan(results, "base", "r", F.NODE_DIR, F.VIDEO_NODES)
    outs = [o for _, o in jobs]
    assert len(set(outs)) == len(outs) == 5, outs
    assert counts == {"302": 3, "114": 2}


def test_an_unmapped_source_node_raises_fetchhalt_naming_the_node(tmp_path, stub_download):
    dump = _dump(tmp_path, [_result("71", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert "71" in str(exc.value)
    assert exc.value.evidence["unmapped"] == ["71"]
    assert not (tmp_path / "runs" / "r").exists(), "a halt must leave no run directory"


def test_the_same_dump_passes_once_the_map_names_the_node(tmp_path, stub_download):
    """The mutation that turns the gate green again — proof it is not always-on."""
    dump = _dump(tmp_path, [_result("71", 0), _result("71", 1)])
    root = tmp_path / "runs"
    F.main([f"--dump={dump}", "--run=r", f"--root={root}", "--node-map=71=lossless"])
    got = sorted(os.listdir(root / "r" / "lossless"))
    assert got == ["00000.png", "00001.png"]


def test_the_video_tap_is_indexed_so_two_videos_cannot_overwrite(tmp_path, stub_download):
    dump = _dump(tmp_path, [_result("114", 0, ".mp4"), _result("114", 1, ".mp4")])
    root = tmp_path / "runs"
    F.main([f"--dump={dump}", "--run=r", f"--root={root}"])
    vids = sorted(n for n in os.listdir(root / "r") if n.endswith(".mp4"))
    assert vids == ["r_00000.mp4", "r_00001.mp4"]


def test_a_downloader_that_fails_halts_instead_of_printing_fetch_run(tmp_path, monkeypatch,
                                                                    capsys):
    """Measured on today's tree with subprocess.run stubbed to returncode 1: the tool
    printed FETCH_RUN {"by_node": {...}, "downloaded": {"lossless": 0}} and returned None,
    i.e. exit 0. The planned count was never compared to what landed."""
    monkeypatch.setattr(F.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    dump = _dump(tmp_path, [_result("302", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert exc.value.evidence["returncode"] == 1
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_a_download_that_lands_nothing_halts(tmp_path, monkeypatch, capsys):
    """curl runs with --fail-with-body, so an error body lands at the -o path and counts.
    A silent no-op is the other half, and it exits 0 today."""
    monkeypatch.setattr(F.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "", ""))
    dump = _dump(tmp_path, [_result("302", 0), _result("302", 1)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert exc.value.evidence["planned"] == 2
    assert len(exc.value.evidence["missing"]) == 2
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_a_zero_length_file_halts_even_though_the_count_matches(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            for job in json.load(fh):
                os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                open(job["out"], "wb").close()
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert len(exc.value.evidence["empty"]) == 1


@pytest.mark.parametrize("run_name", ["plain", "r'; echo INJECTED; #", "a b'c"])
def test_the_command_shape_does_not_move_with_the_run_name(tmp_path, stub_download,
                                                           run_name):
    """Measured: --run=\"r'; echo INJECTED; #\" closed the single-quoted literal and the
    remainder became separate PowerShell statements. The manifest path now travels in the
    environment, so the command string is a constant no operator input can reach."""
    dump = _dump(tmp_path, [_result("302", 0)])
    F.main([f"--dump={dump}", f"--run={run_name}", f"--root={tmp_path / 'runs'}"])
    cmd = stub_download[-1]["cmd"]
    assert run_name not in " ".join(cmd)
    assert "ARMATURE_FETCH_MANIFEST" in cmd[-1]
    assert stub_download[-1]["kw"]["env"]["ARMATURE_FETCH_MANIFEST"].endswith("urls.json")


def test_every_command_shape_is_byte_identical_across_run_names(tmp_path, stub_download):
    for name in ("plain", "r'; echo INJECTED; #"):
        dump = _dump(tmp_path, [_result("302", 0)])
        F.main([f"--dump={dump}", f"--run={name}", f"--root={tmp_path / 'runs'}"])
    assert stub_download[0]["cmd"] == stub_download[1]["cmd"]
