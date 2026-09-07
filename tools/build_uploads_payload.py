#!/usr/bin/env python
"""upload_assets — author the --uploads map six builders already require.

    <venv-python> tools\\upload_assets.py --route=i2v --start-frame=<start.png> \\
        --out=<uploads.json> --dry-run

    <venv-python> tools\\upload_assets.py --route=assembly --frames-dir=<dir> \\
        --out=<uploads.json> --dry-run

Six builders declare `--uploads` and none authored that map in-repo (wave 34,
F-cc2dff5c). This tool emits the schema each builder already validates:

* i2v / camera_i2v — `{start_frame: <server name>}`
* animate — `{reference, pose_pack, pose_frames}`
* assembly / cascade / r2v_a2 — zero-padded frame keys -> server names
* r2v_a1 uses `--refs` (reference record), not this map

`--dry-run` writes the map without contacting the cloud: each server name is
`sha256(file bytes) + extension`, the content-addressed shape Comfy Cloud returns
and the fixtures under tests/fixtures/uploads/ already use. Live mode POSTs via
curl.exe multipart (no Python networking library — SECURITY.md).

Builders stay offline; this is the only network writer beside submit_comfy_cloud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.route_gates import RouteGate  # noqa: E402
from build_assembly_payload import (  # noqa: E402
    FRAME_KEY, frame_order, gate_output_not_overwritten)

TOOL_VERSION = "W37.1"
DEFAULT_BASE_URL = "https://cloud.comfy.org"
DEFAULT_API_KEY_ENV = "COMFY_CLOUD_API_KEY"

ROUTES = ("i2v", "camera_i2v", "animate", "assembly", "cascade", "r2v_a2")


class UploadGate(RouteGate):
    """Gate UPLOAD — refusals while authoring the uploads map."""

    gate = "UPLOAD"


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def content_addressed_name(path):
    """sha256 hex + original extension — the dry-run / fixture shape."""
    ext = os.path.splitext(path)[1].lower() or ".png"
    return file_sha256(path) + ext


def list_frame_files(frames_dir):
    """Local frame files whose basenames are valid assembly/cascade keys."""
    if not os.path.isdir(frames_dir):
        raise UploadGate(
            f"--frames-dir {frames_dir!r} is not a directory",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "frames_dir_missing",
             "path": os.path.abspath(frames_dir)})
    names = []
    for name in sorted(os.listdir(frames_dir)):
        path = os.path.join(frames_dir, name)
        if not os.path.isfile(path):
            continue
        if FRAME_KEY.match(name):
            names.append(name)
    if not names:
        raise UploadGate(
            f"--frames-dir {frames_dir!r} holds no zero-padded frame files "
            f"(00000 / 00000.png)",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "frames_dir_empty",
             "path": os.path.abspath(frames_dir)})
    return names


def curl_upload(path, *, base_url, api_key):
    """Multipart upload via curl.exe. Returns the server-side name."""
    url = base_url.rstrip("/") + "/api/upload/image"
    cmd = [
        "curl.exe", "-sS", "-L", "--fail-with-body",
        "-X", "POST", url,
        "-H", f"X-API-Key: {api_key}",
        "-F", f"image=@{os.path.abspath(path)}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise UploadGate(
            f"upload of {path!r} failed (curl exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '')[:400]}",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "cloud_upload_failed", "path": os.path.abspath(path),
             "curl_exit": proc.returncode,
             "stderr": (proc.stderr or "")[:400]})
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise UploadGate(
            f"upload of {path!r} returned non-JSON ({exc}): "
            f"{(proc.stdout or '')[:300]}",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "cloud_upload_unreadable",
             "path": os.path.abspath(path)}) from exc
    name = doc.get("name")
    if not isinstance(name, str) or not name.strip():
        raise UploadGate(
            f"upload of {path!r} returned no `name`: keys {sorted(doc)[:20]}",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "cloud_upload_no_name",
             "path": os.path.abspath(path), "keys": sorted(map(str, doc))[:40]})
    return name


def resolve_name(path, *, dry_run, base_url, api_key):
    if dry_run:
        return content_addressed_name(path)
    return curl_upload(path, base_url=base_url, api_key=api_key)


def build_map(a):
    dry = bool(a.dry_run)
    key_env = a.api_key_env
    api_key = (os.environ.get(key_env) or "").strip()
    if not dry and not api_key:
        raise UploadGate(
            f"env {key_env!r} is empty; live upload needs the Comfy Cloud API key. "
            f"Pass --dry-run to author the map from local sha256 names",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "api_key_missing", "api_key_env": key_env})

    route = a.route
    uploads = {}
    meta = {"route": route, "dry_run": dry, "tool": "upload_assets",
            "tool_version": TOOL_VERSION, "files": {}}

    def one(local_key, path):
        if not path or not os.path.isfile(path):
            raise UploadGate(
                f"route {route!r} needs file for `{local_key}` at {path!r}",
                {"gate": "UPLOAD", "andon": "UploadGate",
                 "clause": "asset_missing", "key": local_key,
                 "path": path})
        name = resolve_name(path, dry_run=dry, base_url=a.base_url, api_key=api_key)
        uploads[local_key] = name
        meta["files"][local_key] = {
            "path": os.path.abspath(path),
            "sha256": file_sha256(path),
            "server_name": name,
            "bytes": os.path.getsize(path),
        }
        return name

    if route in ("i2v", "camera_i2v"):
        one("start_frame", a.start_frame)
    elif route == "animate":
        one("reference", a.reference)
        one("pose_pack", a.pose_pack)
        if a.pose_frames is None:
            raise UploadGate(
                "--pose-frames is required for --route=animate (integer frame count "
                "checked against the shot length by build_animate_payload)",
                {"gate": "UPLOAD", "andon": "UploadGate",
                 "clause": "pose_frames_missing"})
        uploads["pose_frames"] = int(a.pose_frames)
        meta["files"]["pose_frames"] = {"value": int(a.pose_frames)}
    elif route in ("assembly", "cascade", "r2v_a2"):
        if not a.frames_dir:
            raise UploadGate(
                f"--frames-dir is required for --route={route}",
                {"gate": "UPLOAD", "andon": "UploadGate",
                 "clause": "frames_dir_required", "route": route})
        for name in list_frame_files(a.frames_dir):
            path = os.path.join(a.frames_dir, name)
            server = resolve_name(
                path, dry_run=dry, base_url=a.base_url, api_key=api_key)
            uploads[name] = server
            meta["files"][name] = {
                "path": os.path.abspath(path),
                "sha256": file_sha256(path),
                "server_name": server,
                "bytes": os.path.getsize(path),
            }
        # Validate the key shape the builders will re-check.
        frame_order(uploads)
    else:
        raise UploadGate(
            f"--route={route!r} is not one of {list(ROUTES)}",
            {"gate": "UPLOAD", "andon": "UploadGate",
             "clause": "route_unknown", "route": route, "known": list(ROUTES)})
    return uploads, meta


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Author the --uploads JSON six payload builders require. Dry-run writes "
            "content-addressed names from local file digests; live mode uploads via "
            "curl.exe."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ROUTE: the upload step that used to be operator craft upstream of Gate L.\n"
            "\n"
            "WHAT A REFUSAL COSTS: no file leaves the rig on --dry-run; a live refusal "
            "leaves partial cloud objects content-addressed and inert unless a graph "
            "names them."))
    ap.add_argument("--route", required=True, choices=ROUTES,
                    help="which builder schema to emit")
    ap.add_argument("--out", required=True,
                    help="path of the uploads JSON this tool writes; an existing file is "
                         "refused unless --overwrite is passed (wave 37, F-7bdf1b38)")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing uploads map at --out. Without it a re-author "
                         "refuses by name (`output_already_exists`)")
    ap.add_argument("--dry-run", action="store_true",
                    help="emit sha256+ext server names without contacting the cloud")
    ap.add_argument("--start-frame", default=None,
                    help="i2v / camera_i2v: local start-frame image")
    ap.add_argument("--reference", default=None,
                    help="animate: local reference image")
    ap.add_argument("--pose-pack", default=None,
                    help="animate: local lossless animated WebP pose pack")
    ap.add_argument("--pose-frames", type=int, default=None,
                    help="animate: frame count declared by the pose pack")
    ap.add_argument("--frames-dir", default=None,
                    help="assembly / cascade / r2v_a2: directory of zero-padded frames")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"Comfy Cloud base URL (default: {DEFAULT_BASE_URL})")
    ap.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV,
                    help=f"env var holding the X-API-Key (default: {DEFAULT_API_KEY_ENV})")
    ap.add_argument("--meta-out", default=None,
                    help="optional provenance JSON beside the uploads map")
    a = ap.parse_args(argv)

    uploads, meta = build_map(a)
    out = os.path.abspath(a.out)
    paths = [out]
    if a.meta_out:
        paths.append(os.path.abspath(a.meta_out))
    gate_overwrite = gate_output_not_overwritten(
        paths, os.path.dirname(out) or ".", a.overwrite, UploadGate, gate="UPLOAD")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(uploads, fh, indent=2, ensure_ascii=False)
    if a.meta_out:
        meta_path = os.path.abspath(a.meta_out)
        os.makedirs(os.path.dirname(meta_path) or ".", exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)

    print("UPLOAD_ASSETS_OK")
    print(json.dumps({
        "path": out,
        "route": a.route,
        "dry_run": bool(a.dry_run),
        "n_keys": len(uploads),
        "keys": sorted(uploads, key=lambda k: (str(k),)),
        "out_dir_pre_existed": gate_overwrite["out_dir_pre_existed"],
        "overwrote": gate_overwrite["overwrote"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "UPLOAD_ASSETS")
