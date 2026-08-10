#!/usr/bin/env python
"""fetch_run — turn a get_output dump into a run directory on disk.

    python tools/fetch_run.py --dump=<get_output.txt> --run=<name> [--arm=A1a]

`get_output` returns one record per file, and a run with the lossless tap emits 67 of
them (33 batch-probe + 33 lossless + 1 video). That is far past what belongs in a
context window, so the dump is parsed here and only the counts come back.

Files are sorted into `outputs/E02/runs/<name>/` by **source node id**, not by filename:

    301 -> batchprobe/   the control batch as the sampler received it
    302 -> lossless/     VAEDecode frames, no codec anywhere in the path
    114 -> <name>.mp4    the H.264 review copy

The node split is the whole point. The first noise floor was measured on frames that had
been through H.264 on both sides, so its deltas carried codec noise of unknown size on
top of model variance. Everything downstream of this reads `lossless/`.
"""

import argparse
import json
import os
import subprocess

NODE_DIR = {"301": "batchprobe", "302": "lossless"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--root", default="outputs/E02/runs")
    a = ap.parse_args()

    with open(a.dump, encoding="utf-8") as fh:
        results = json.load(fh)["results"]

    base = os.path.join(a.root, a.run)
    jobs, counts = [], {}
    for r in results:
        nid = str(r["source_node_id"])
        if nid in NODE_DIR:
            d = os.path.join(base, NODE_DIR[nid])
            os.makedirs(d, exist_ok=True)
            i = counts.get(nid, 0)
            counts[nid] = i + 1
            jobs.append((r["url"], os.path.join(d, f"{i:05d}.png")))
        else:
            os.makedirs(base, exist_ok=True)
            ext = os.path.splitext(r["filename"])[1] or ".bin"
            counts[nid] = counts.get(nid, 0) + 1
            jobs.append((r["url"], os.path.join(base, f"{a.run}{ext}")))

    manifest = os.path.join(base, "urls.json")
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump([{"url": u, "out": o} for u, o in jobs], fh, indent=1)

    ps = (
        f"$j = Get-Content '{os.path.abspath(manifest)}' -Raw | ConvertFrom-Json; "
        "$j | ForEach-Object -Parallel { curl.exe -sS -L --fail-with-body -o $_.out -- $_.url 2>$null } "
        "-ThrottleLimit 12"
    )
    subprocess.run(["pwsh", "-NoProfile", "-Command", ps], capture_output=True)

    got = {}
    for nid, sub in NODE_DIR.items():
        d = os.path.join(base, sub)
        got[sub] = len([n for n in os.listdir(d) if n.endswith(".png")]) if os.path.isdir(d) else 0
    vids = [n for n in os.listdir(base) if n.endswith(".mp4")] if os.path.isdir(base) else []
    print("FETCH_RUN " + json.dumps({
        "run": a.run, "dir": base, "by_node": counts, "downloaded": got, "video": vids}))


if __name__ == "__main__":
    main()
