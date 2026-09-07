"""A Comfy-Cloud double — queue prompt, serve fixture bytes, record submitted graphs.

Wave 35, F-e88e5724. `tests/fake_backend.py` is the arithmetic render backend for
`run_export` / stage_render gates. This sibling covers the cloud half of a paid route:
submit → prompt_id → signed URL → fetch, without network or credits.

Callable surface (no live HTTP required):

* `FakeComfy.queue_prompt(graph) -> {"prompt_id": ...}`
* `FakeComfy.get_output(prompt_id) -> dump shaped like fetch_run's --dump`
* `FakeComfy.url_bytes(url) -> bytes` for signed result URLs
* `FakeComfy.submitted` — list of graph dicts queued

An optional `serve()` context starts a stdlib `http.server` on localhost for tools that
must hit real URLs; most suite sites monkeypatch `subprocess.run` / `download` and only
need the callable half.
"""

from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class FakeComfy:
    """In-process Comfy Cloud double."""

    def __init__(self, *, fixture_bytes=None, node_id="302", n_frames=2):
        self.fixture_bytes = fixture_bytes if fixture_bytes is not None else (
            PNG_SIGNATURE + b"\x00" * 24)
        self.node_id = str(node_id)
        self.n_frames = n_frames
        self.submitted = []
        self._prompt_n = 0
        self._by_prompt = {}
        self.base_url = "http://127.0.0.1:0"  # rewritten by serve()

    def queue_prompt(self, graph):
        """Record `graph` and return a prompt_id receipt."""
        self._prompt_n += 1
        prompt_id = f"fake-prompt-{self._prompt_n:04d}"
        self.submitted.append(json.loads(json.dumps(graph)))
        results = []
        for i in range(self.n_frames):
            name = f"{i:064x}.png"
            url = f"{self.base_url}/result/{prompt_id}/{name}"
            results.append({
                "source_node_id": self.node_id,
                "filename": name,
                "url": url,
            })
        self._by_prompt[prompt_id] = {
            "prompt_id": prompt_id,
            "results": results,
            "graph_sha256": hashlib.sha256(
                json.dumps(graph, sort_keys=True).encode("utf-8")).hexdigest(),
        }
        return {"prompt_id": prompt_id, "id": prompt_id}

    def get_output(self, prompt_id):
        """Dump shaped like Comfy Cloud get_output / fetch_run --dump input."""
        if prompt_id not in self._by_prompt:
            raise KeyError(prompt_id)
        return {"results": list(self._by_prompt[prompt_id]["results"])}

    def url_bytes(self, url):
        """Bytes a signed result URL would return."""
        if "/result/" not in url:
            raise KeyError(url)
        return self.fixture_bytes

    def serve(self):
        """Context manager: bind a localhost HTTP server serving queue + result URLs."""
        return _FakeComfyServer(self)


class _FakeComfyServer:
    def __init__(self, comfy: FakeComfy):
        self.comfy = comfy
        self._httpd = None
        self._thread = None

    def __enter__(self):
        comfy = self.comfy

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                if self.path.rstrip("/").endswith("/prompt"):
                    graph = json.loads(body.decode("utf-8") or "{}")
                    # Accept either raw graph or {"prompt": graph}
                    if "prompt" in graph and isinstance(graph["prompt"], dict):
                        graph = graph["prompt"]
                    receipt = comfy.queue_prompt(graph)
                    payload = json.dumps(receipt).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                self.send_response(404)
                self.end_headers()

            def do_GET(self):
                if self.path.startswith("/result/"):
                    data = comfy.url_bytes(f"{comfy.base_url}{self.path}")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if "/history/" in self.path or self.path.startswith("/get_output"):
                    # /history/<prompt_id> or similar
                    prompt_id = self.path.rstrip("/").rsplit("/", 1)[-1]
                    try:
                        dump = comfy.get_output(prompt_id)
                    except KeyError:
                        self.send_response(404)
                        self.end_headers()
                        return
                    payload = json.dumps(dump).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                self.send_response(404)
                self.end_headers()

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        host, port = self._httpd.server_address
        comfy.base_url = f"http://{host}:{port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return comfy

    def __exit__(self, *exc):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        return False
