"""Wave 35, F-e88e5724 — FakeComfy wired through fetch_run / fetch_t2v_run.

Wave 37, F-63df4a5a — banked spend-builder API graphs join the same path: load a
records/<route>/*.api.json → FakeComfy.queue_prompt(graph) → get_output → fetch_* SUCCESS,
asserting submitted graph identity (sha) and downloaded fixture bytes. FakeBackend stays
render-only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

import pytest

from conftest import (  # noqa: F401
    API_GRAPH_RECORDS, TOOLS, api_graph_record, load_ok_payload,
)
import fake_comfy as FC
import fetch_run as F
import fetch_t2v_run as T


def _load_api_graph(path):
    doc = json.loads(open(path, encoding="utf-8").read())
    if isinstance(doc, dict) and "prompt" in doc and isinstance(doc["prompt"], dict):
        if any(isinstance(v, dict) and "class_type" in v for v in doc["prompt"].values()):
            return doc["prompt"]
    return doc


def _graph_sha(graph):
    return hashlib.sha256(json.dumps(graph, sort_keys=True).encode("utf-8")).hexdigest()


def _save_node_id(graph):
    """Prefer a SaveImage-class node id; fall back to the first node."""
    for nid, node in graph.items():
        if isinstance(node, dict) and "Save" in str(node.get("class_type", "")):
            return str(nid)
    for nid, node in graph.items():
        if isinstance(node, dict) and "class_type" in node:
            return str(nid)
    return "302"


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


def test_fetch_run_joins_a_banked_api_graph_through_fake_comfy(tmp_path, comfy_download,
                                                                capsys):
    """Wave 37 F-63df4a5a: banked E02 payload graph → queue → dump → fetch_run SUCCESS."""
    path = api_graph_record("outputs/payload/E02-A0.api.json")
    graph = _load_api_graph(path)
    want_sha = _graph_sha(graph)
    # Node 302 is the lossless SaveImage tap fetch_run's default --node-map knows.
    node_id = "302"
    assert node_id in graph and "Save" in graph[node_id]["class_type"]
    fixture = FC.PNG_SIGNATURE + b"banked-fetch-run"
    c = FC.FakeComfy(fixture_bytes=fixture, node_id=node_id, n_frames=2)
    receipt = c.queue_prompt(graph)
    assert _graph_sha(c.submitted[0]) == want_sha
    assert c._by_prompt[receipt["prompt_id"]]["graph_sha256"] == want_sha
    dump = tmp_path / "get_output.json"
    dump.write_text(json.dumps(c.get_output(receipt["prompt_id"])), encoding="utf-8")
    root = tmp_path / "runs"
    assert F.main([f"--dump={dump}", "--run=banked", f"--root={root}"]) in (0, None)
    got = sorted(os.listdir(root / "banked" / "lossless"))
    assert got == ["00000.png", "00001.png"]
    payload = load_ok_payload(capsys.readouterr().out, "FETCH_RUN_OK")
    assert payload["by_node"][node_id] == 2
    for name in got:
        with open(root / "banked" / "lossless" / name, "rb") as fh:
            assert fh.read().startswith(FC.PNG_SIGNATURE)


def test_fetch_t2v_joins_a_banked_t2v_graph_through_fake_comfy(tmp_path, monkeypatch,
                                                                capsys):
    """Wave 37 F-63df4a5a: banked t2v graph → queue → dump → fetch_t2v_run SUCCESS."""
    from test_fetch_t2v_run import E09_ARRAY, E09_HASH, _ev, _exits_receipt

    path = api_graph_record("outputs/t2v/E09-B2-probe-t2v.api.json")
    graph = _load_api_graph(path)
    want_sha = _graph_sha(graph)
    node_id = _save_node_id(graph)
    c = FC.FakeComfy(node_id=node_id, n_frames=3)
    receipt = c.queue_prompt(graph)
    assert _graph_sha(c.submitted[0]) == want_sha
    dump = tmp_path / "dump.json"
    raw = c.get_output(receipt["prompt_id"])
    for r in raw["results"]:
        r["source_node_id"] = int(node_id) if str(node_id).isdigit() else node_id
        r["url"] = f"u{r['filename'][:4]}"
    dump.write_text(json.dumps(raw), encoding="utf-8")

    def fake_download(jobs, out=None):
        for j in jobs:
            os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
            with open(j["out"], "wb") as fh:
                fh.write(T.PNG_SIGNATURE + b"banked-t2v")
        return None, _exits_receipt(jobs)

    monkeypatch.setattr(T, "download", fake_download)
    monkeypatch.setattr(T, "order_evidence", lambda out: _ev(E09_ARRAY, E09_HASH))
    out = tmp_path / "t2v_banked"
    assert T.main([f"--dump={dump}", f"--out={out}"]) == 0
    payload = load_ok_payload(capsys.readouterr().out, "FETCH_T2V_OK")
    assert payload["frames"] == 3
    assert len(c.submitted) == 1
    assert API_GRAPH_RECORDS  # bank table still the nine-route census
