#!/usr/bin/env python
"""fetch_run — turn a get_output dump into a run directory on disk.

    python tools/fetch_run.py --dump=<get_output.txt> --run=<name> [--arm=A1a]

`get_output` returns one record per file, and a run with the lossless tap emits 67 of
them (33 batch-probe + 33 lossless + 1 video). That is far past what belongs in a
context window, so the dump is parsed here and only the counts come back.

Files are sorted into `<root>/<name>/` by **source node id**, not by filename. E02's map,
which is still the default:

    301 -> batchprobe/   the control batch as the sampler received it
    302 -> lossless/     VAEDecode frames, no codec anywhere in the path
    114 -> <name>.mp4    the H.264 review copy

The node split is the whole point. The first noise floor was measured on frames that had
been through H.264 on both sides, so its deltas carried codec noise of unknown size on
top of model variance. Everything downstream of this reads `lossless/`.

**The map is a flag as of E11 (2026-08-12), and that is a fix rather than a feature.** It
was a module constant naming E02's node ids, so pointing this tool at any later
experiment's dump sorted every frame into the fallback branch and named them all after the
run — silently, with a plausible count printed. E10's closing lesson states the shape:
*a tool that names an experiment in a literal is a tool that will lie the first time it is
reused.* Pass `--node-map=41=startprobe,71=lossless` for a graph whose taps sit elsewhere.
"""

import argparse
import json
import os
import subprocess

NODE_DIR = {"301": "batchprobe", "302": "lossless"}


def parse_node_map(text):
    """`"41=startprobe,71=lossless"` -> `{"41": "startprobe", ...}`, or raise saying why.

    A malformed map must not fall back to the default: the caller would get E02's mapping
    applied to somebody else's graph, every frame would land in the video branch, and the
    only symptom would be a directory of files with the wrong names.
    """
    if not text:
        return dict(NODE_DIR)
    out = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if part.count("=") != 1:
            raise SystemExit(
                f"--node-map entry {part!r} is not `<node id>=<directory>`; a map that "
                f"cannot be read must halt rather than quietly leave E02's default in "
                f"place over another experiment's graph")
        nid, sub = (s.strip() for s in part.split("="))
        if not nid or not sub:
            raise SystemExit(f"--node-map entry {part!r} has an empty side")
        out[nid] = sub
    if not out:
        raise SystemExit("--node-map parsed to nothing")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--root", default="outputs/E02/runs")
    ap.add_argument("--node-map", default=None,
                    help="`<node id>=<subdir>` pairs, comma separated, e.g. "
                         "--node-map=41=startprobe,71=lossless. Defaults to E02's taps "
                         "(301=batchprobe,302=lossless); anything not named lands beside "
                         "them as <run><ext>")
    a = ap.parse_args()
    node_dir = parse_node_map(a.node_map)

    with open(a.dump, encoding="utf-8") as fh:
        results = json.load(fh)["results"]

    base = os.path.join(a.root, a.run)
    jobs, counts = [], {}
    for r in results:
        nid = str(r["source_node_id"])
        if nid in node_dir:
            d = os.path.join(base, node_dir[nid])
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
    for nid, sub in node_dir.items():
        d = os.path.join(base, sub)
        got[sub] = len([n for n in os.listdir(d) if n.endswith(".png")]) if os.path.isdir(d) else 0
    vids = [n for n in os.listdir(base) if n.endswith(".mp4")] if os.path.isdir(base) else []
    print("FETCH_RUN " + json.dumps({
        "run": a.run, "dir": base, "by_node": counts, "downloaded": got, "video": vids}))


if __name__ == "__main__":
    main()
