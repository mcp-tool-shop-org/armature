"""Wave 35, F-e88e5724 — FakeComfy wired through fetch_run / fetch_t2v_run.

One integration test per fetch tool: queue → dump → fetch main SUCCESS, with submitted
graph bytes recorded for assertions. FakeBackend stays focused on render/export.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from conftest import TOOLS, load_ok_payload  # noqa: F401
import fake_comfy as FC
import fetch_run as F
import fetch_t2v_run as T


def test_queue_prompt_records_the_graph_and_returns_a_prompt_id():
    c = FC.FakeComfy(n_frames=2)
    receipt = c.queue_prompt({"1": {"class_type": "Stub", "inputs": {}}})
    assert receipt["prompt_id"].startswith("fake-prompt-")
    assert len(c.submitted) == 1
    assert c.submitted[0]["1"]["class_type"] == "Stub"
    dump = c.get_output(receipt["prompt_id"])
    assert len(dump["results"]) == 2
    assert all(r["url"].startswith(c.base_url) for r in dump["results"])


def test_serve_hands_out_fixture_bytes_over_http():
    c = FC.FakeComfy(fixture_bytes=FC.PNG_SIGNATURE + b"abcd", n_frames=1)
    with c.serve() as live:
        receipt = live.queue_prompt({"n": {}})
        dump = live.get_output(receipt["prompt_id"])
        url = dump["results"][0]["url"]
        import urllib.request
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.read() == FC.PNG_SIGNATURE + b"abcd"


def _body_for(path):
    suffix = os.path.splitext(path)[1].lower()
    rules = F.CONTENT_SIGNATURES.get(suffix)
    if rules is None:
        return b"\x00\x01\x02\x03"
    body = bytearray(b"\x00" * 32)
    for offset, magic, _name in rules:
        body[offset:offset + len(magic)] = magic
    return bytes(body)


@pytest.fixture()
def comfy_download(monkeypatch):
    """Downloader that lands FakeComfy fixture bytes via the fetch_run subprocess seam."""

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        manifest = env.get(F.MANIFEST_ENV)
        rows = []
        if manifest and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                for job in json.load(fh):
                    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                    with open(job["out"], "wb") as out:
                        out.write(_body_for(job["out"]))
                    rows.append({"out": job["out"], "url": job["url"], "code": 0,
                                 "message": ""})
        exits = env.get(F.EXITS_ENV)
        if exits:
            with open(exits, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)


def test_fetch_run_succeeds_from_a_fake_comfy_dump(tmp_path, comfy_download, capsys):
    c = FC.FakeComfy(node_id="302", n_frames=2)
    receipt = c.queue_prompt({"302": {"class_type": "SaveImage", "inputs": {}}})
    dump = tmp_path / "get_output.json"
    dump.write_text(json.dumps(c.get_output(receipt["prompt_id"])), encoding="utf-8")
    root = tmp_path / "runs"
    assert F.main([f"--dump={dump}", "--run=r", f"--root={root}"]) in (0, None)
    assert (root / "r" / "lossless").is_dir()
    got = sorted(os.listdir(root / "r" / "lossless"))
    assert got == ["00000.png", "00001.png"]
    payload = load_ok_payload(capsys.readouterr().out, "FETCH_RUN_OK")
    assert payload["by_node"]["302"] == 2
    assert c.submitted and "302" in c.submitted[0]


def test_fetch_t2v_succeeds_from_a_fake_comfy_dump(tmp_path, monkeypatch, capsys):
    from test_fetch_t2v_run import E09_ARRAY, E09_HASH, _ev, _exits_receipt

    c = FC.FakeComfy(node_id="70", n_frames=3)
    receipt = c.queue_prompt({"70": {"class_type": "SaveImage", "inputs": {}}})
    dump = tmp_path / "dump.json"
    # Remap results to int node ids the way fetch_t2v fixtures do.
    raw = c.get_output(receipt["prompt_id"])
    for r in raw["results"]:
        r["source_node_id"] = 70
        r["url"] = f"u{r['filename'][:4]}"
    dump.write_text(json.dumps(raw), encoding="utf-8")

    def fake_download(jobs, out=None):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            with open(j["out"], "wb") as fh:
                fh.write(T.PNG_SIGNATURE)
        return None, _exits_receipt(jobs)

    monkeypatch.setattr(T, "download", fake_download)
    monkeypatch.setattr(T, "order_evidence", lambda out: _ev(E09_ARRAY, E09_HASH))
    out = tmp_path / "t2v_run"
    assert T.main([f"--dump={dump}", f"--out={out}"]) == 0
    payload = load_ok_payload(capsys.readouterr().out, "FETCH_T2V_OK")
    assert payload["frames"] == 3
    assert len(c.submitted) == 1
