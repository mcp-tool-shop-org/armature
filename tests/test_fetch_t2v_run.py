"""The T2V fetcher's andons — the order discriminator, the downloader, and the command.

Wave 3, F-2770135b / F-f7ba7452. The module docstring calls the 7.6x array-order vs
hash-order discriminator *the only evidence in the run directory that the order is right*
and then never compared it to anything: `main` wrote it to `frame_order_evidence.json`,
printed the ratio inside the FETCH_OK line, and returned 0. The zero-length-frame check
three lines above it raises, so the file already knew the difference between reporting and
gating. A shuffled clip would be written, FETCH_OK printed, and a ratio near 1.0 noticed
only if a human opened the JSON.

The second defect is in the same file's downloader: `curl.exe -sSL -o $x.out $x.url` put a
value read straight out of an operator-pasted dump in OPTION position with no `--`
terminator, and the sibling `fetch_run.py` had one.

Every fixture here asks CLAUDE.md's question of a fixture — what would this look like if
the code were wrong in the specific way this check exists to catch — so the ratios below
are E09's own measured numbers on one side and their degenerate cases on the other.
"""

import json
import os
import subprocess

import pytest

from conftest import TOOLS  # noqa: F401
import fetch_t2v_run as T


#: E09's probe: 0.703 in the results-array order, 5.314 sorted by content hash, 7.6x apart.
E09_ARRAY, E09_HASH = 0.703, 5.314


def _ev(array_mean, hash_mean):
    return {"results_array_order": {"mean": array_mean},
            "hash_sorted_order": {"mean": hash_mean}}


# ------------------------------------------------------------------ the order discriminator


def test_e09s_own_measurement_passes_the_gate():
    ev = T.gate_order_evidence(_ev(E09_ARRAY, E09_HASH))
    assert ev["ratio"] == pytest.approx(E09_HASH / E09_ARRAY)
    assert "verdict" in ev


def test_two_orderings_that_agree_do_not_print_fetch_ok():
    """The defect. A hash-sorted permutation that differences the SAME as the array order
    is a run whose order this tool cannot vouch for, and the docstring says so — while the
    code printed FETCH_OK and exit 0."""
    with pytest.raises(T.FetchHalt) as exc:
        T.gate_order_evidence(_ev(2.0, 2.0))
    assert "FETCH_ORDER_UNVOUCHED" in str(exc.value)
    assert exc.value.evidence["ratio"] == pytest.approx(1.0)


def test_a_hash_order_that_is_tighter_than_the_array_order_halts():
    """The inverted case: the array order is the WORSE ordering. Nothing in the old code
    could tell this apart from the good one."""
    with pytest.raises(T.FetchHalt):
        T.gate_order_evidence(_ev(5.314, 0.703))


def test_an_undefined_ratio_halts_rather_than_reporting_null():
    """`main` divided by the array mean and wrote `None` when it was zero — a null in the
    FETCH_OK line rather than a halt. All-identical frames decide nothing."""
    with pytest.raises(T.FetchHalt) as exc:
        T.gate_order_evidence(_ev(0.0, 0.0))
    assert exc.value.evidence["ratio"] is None


def test_the_boundary_is_the_sign_of_the_comparison_not_an_invented_floor():
    """No calibrated floor for this ratio has been measured on any provider, so the gate
    may not carry a magnitude: a pass condition invented while looking at the results it
    judges is the thing CLAUDE.md forbids. Just above 1 passes; just below refuses."""
    assert T.gate_order_evidence(_ev(1.0, 1.0001))["ratio"] > 1.0
    with pytest.raises(T.FetchHalt):
        T.gate_order_evidence(_ev(1.0, 0.9999))


# ------------------------------------------------------------------ the downloader


def _jobs(tmp_path, n=2):
    return [{"url": f"-oevil{i}", "cloud_name": f"{i:064x}.png", "array_index": i,
             "out": os.path.join(str(tmp_path), "lossless", f"{i:05d}.png")}
            for i in range(n)]


def test_the_url_sits_behind_a_terminator_and_errors_are_visible(tmp_path, monkeypatch):
    """A dump entry whose url begins with a dash is read by curl as an option, and both
    -o and -K (read a config file) are reachable that way. The sibling fetch_run.py had
    the terminator; this file did not."""
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = list(cmd)
        seen["env"] = kw.get("env")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(T.subprocess, "run", fake_run)
    T.download(_jobs(tmp_path))
    script = seen["cmd"][-1]
    assert "-- $x.url" in script, script
    assert "--fail-with-body" in script, script


def test_the_manifest_path_never_reaches_the_command_string(tmp_path, monkeypatch):
    """Same quoting defect as fetch_run.py's: an apostrophe in the path closed the
    single-quoted literal. The path travels in the environment instead."""
    seen = {}
    monkeypatch.setattr(T.subprocess, "run",
                        lambda cmd, **kw: (seen.update(cmd=list(cmd), env=kw.get("env")),
                                           subprocess.CompletedProcess(cmd, 0, "", ""))[1])
    odd = tmp_path / "it's a run"
    (odd / "lossless").mkdir(parents=True)
    jobs = [{"url": "https://example.invalid/0.png", "cloud_name": "a.png",
             "array_index": 0, "out": str(odd / "lossless" / "00000.png")}]
    T.download(jobs)
    assert str(odd) not in " ".join(seen["cmd"])
    assert T.MANIFEST_ENV in seen["cmd"][-1]
    assert seen["env"][T.MANIFEST_ENV].endswith("_urls.json")


def test_a_downloader_that_exits_nonzero_raises_with_its_output(tmp_path, monkeypatch):
    monkeypatch.setattr(T.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 7, "", "boom"))
    with pytest.raises(T.FetchHalt) as exc:
        T.download(_jobs(tmp_path))
    assert exc.value.evidence["returncode"] == 7
    assert "boom" in exc.value.evidence["stderr"]


# ------------------------------------------------------------------ the plan


def test_a_source_node_this_graph_does_not_emit_halts():
    with pytest.raises(SystemExit):
        T.plan([{"source_node_id": 99, "filename": "a.png", "url": "u"}], "out")


def test_the_array_position_is_the_frame_index():
    results = [{"source_node_id": 70, "filename": f"{i:064x}.png", "url": f"u{i}"}
               for i in range(3)]
    jobs = T.plan(results, "out")
    assert [j["array_index"] for j in jobs] == [0, 1, 2]
    assert [os.path.basename(j["out"]) for j in jobs] == [
        "00000.png", "00001.png", "00002.png"]


# ------------------------------------------------------------------ main, end to end


def _run_main(tmp_path, monkeypatch, ev):
    results = [{"source_node_id": 70, "filename": f"{i:064x}.png", "url": f"u{i}"}
               for i in range(3)]
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({"results": results}), encoding="utf-8")

    def fake_download(jobs):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            with open(j["out"], "wb") as fh:
                fh.write(b"\x89PNG\r\n")

    monkeypatch.setattr(T, "download", fake_download)
    monkeypatch.setattr(T, "order_evidence", lambda out: ev)
    return T.main([f"--dump={dump}", f"--out={tmp_path / 'run'}"])


def test_main_prints_fetch_ok_when_the_order_evidence_supports_the_order(
        tmp_path, monkeypatch, capsys):
    rc = _run_main(tmp_path, monkeypatch, _ev(E09_ARRAY, E09_HASH))
    assert rc == 0
    assert "FETCH_OK" in capsys.readouterr().out


def test_main_does_not_print_fetch_ok_on_an_unvouched_order(tmp_path, monkeypatch, capsys):
    """The whole finding in one fixture: the frames are all present and non-empty, every
    count is right, and the only thing wrong is that the order cannot be vouched for."""
    with pytest.raises(T.FetchHalt):
        _run_main(tmp_path, monkeypatch, _ev(2.0, 2.0))
    assert "FETCH_OK" not in capsys.readouterr().out


def test_the_evidence_file_is_still_written_when_the_order_gate_fires(
        tmp_path, monkeypatch):
    """The halt must leave the evidence behind. A gate that deletes what fired it makes
    the next session re-run a paid generation to see it."""
    with pytest.raises(T.FetchHalt):
        _run_main(tmp_path, monkeypatch, _ev(2.0, 2.0))
    p = tmp_path / "run" / "frame_order_evidence.json"
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8"))["results_array_order"]["mean"] == 2.0


def test_a_zero_length_frame_still_halts(tmp_path, monkeypatch, capsys):
    results = [{"source_node_id": 70, "filename": "a.png", "url": "u"}]
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({"results": results}), encoding="utf-8")

    def fake_download(jobs):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            open(j["out"], "wb").close()

    monkeypatch.setattr(T, "download", fake_download)
    monkeypatch.setattr(T, "order_evidence", lambda out: _ev(E09_ARRAY, E09_HASH))
    with pytest.raises(T.FetchHalt) as exc:
        T.main([f"--dump={dump}", f"--out={tmp_path / 'run'}"])
    assert "zero-length" in str(exc.value)
    assert "FETCH_OK" not in capsys.readouterr().out
