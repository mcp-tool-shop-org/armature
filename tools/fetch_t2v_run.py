#!/usr/bin/env python
"""fetch_t2v_run — a get_output dump for the in-repo T2V graph, onto disk, in ORDER.

    python tools/fetch_t2v_run.py --dump=<get_output.txt> --out=outputs/E09/b2-a3

`fetch_run.py` serves E02's control-sequence graph and keys on ITS node ids (301/302/114).
This graph's ids are ours: 70 = the lossless SaveImage tap, 81 = the convenience video.

**The clause this file exists for.** `get_output` returns content-addressed filenames —
`00f09b64…`, `0211117d…` — so sorting them is sorting hashes, which is a random permutation
of the clip. E09's first download did exactly that, and it was caught by measurement rather
than by noticing: mean consecutive-frame difference was 0.703 in the results-array order and
5.314 sorted, 7.6x apart. Every count would have been right, every gate would have passed,
and the lift would have been measured on a shuffled clip with the resulting jitter read as
detector noise.

So: **the results array's order is the temporal order**, frames are renumbered `00000.png`
onward on the way in, and the same 7.6x discriminator is recomputed here and written beside
them. The discriminator is not decoration — it is the only evidence in the run directory
that the order is right, and a clip whose two orderings agree closely is a clip this tool
says so about rather than one it silently blesses.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOOL_VERSION = "E09.A3"

LOSSLESS_NODE = "70"
VIDEO_NODE = "81"


def plan(results, out):
    """Where each returned file lands. Array position IS the frame index."""
    jobs, i = [], 0
    for r in results:
        nid = str(r["source_node_id"])
        if nid == LOSSLESS_NODE:
            jobs.append({"url": r["url"], "cloud_name": r["filename"], "array_index": i,
                         "out": os.path.join(out, "lossless", f"{i:05d}.png")})
            i += 1
        elif nid == VIDEO_NODE:
            ext = os.path.splitext(r["filename"])[1] or ".mp4"
            jobs.append({"url": r["url"], "cloud_name": r["filename"], "array_index": None,
                         "out": os.path.join(out, f"donor{ext}")})
        else:
            raise SystemExit(f"unexpected source node {nid}; this graph emits only "
                             f"{LOSSLESS_NODE} (lossless) and {VIDEO_NODE} (video)")
    return jobs


def download(jobs):
    for j in jobs:
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
    manifest = [{"url": j["url"], "out": os.path.abspath(j["out"])} for j in jobs]
    tmp = os.path.join(os.path.dirname(jobs[0]["out"]), "_urls.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    ps = (f"$j = Get-Content '{os.path.abspath(tmp)}' -Raw | ConvertFrom-Json; "
          f"foreach ($x in $j) {{ curl.exe -sSL -o $x.out $x.url }}")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    os.remove(tmp)


def order_evidence(out):
    """The 7.6x discriminator, recomputed on this run's own frames."""
    from armature_core import donor_gate as DG

    d = os.path.join(out, "lossless")
    array_order = DG.frame_paths(d)                       # 00000.png ... , i.e. as returned
    by_hash = sorted(array_order, key=lambda p: _hash_name(p, out))
    return {
        "results_array_order": {k: v for k, v in
                                DG.mean_consecutive_frame_difference(array_order).items()
                                if k != "per_pair"},
        "hash_sorted_order": {k: v for k, v in
                              DG.mean_consecutive_frame_difference(by_hash).items()
                              if k != "per_pair"},
        "what_this_shows": (
            "if the array order is temporal, differencing it gives a much SMALLER number "
            "than differencing a hash-sorted permutation of the same frames. E09's probe "
            "measured 0.703 vs 5.314. A run where the two are close is a run whose order "
            "this tool cannot vouch for, and the report must say so"),
    }


def _hash_name(path, out):
    """The cloud filename this local frame came from — the permutation being tested."""
    with open(os.path.join(out, "download_manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    for j in m["files"]:
        if os.path.abspath(j["out"]) == os.path.abspath(path):
            return j["cloud_name"]
    return os.path.basename(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt-id", default=None)
    a = ap.parse_args(argv)

    with open(a.dump, encoding="utf-8") as fh:
        results = json.load(fh)["results"]
    jobs = plan(results, a.out)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "download_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"tool": "fetch_t2v_run", "tool_version": TOOL_VERSION,
                   "prompt_id": a.prompt_id, "n_results": len(results),
                   "order_rule": ("the results array's order is the temporal order; the "
                                  "cloud filenames are content hashes and sorting them "
                                  "shuffles the clip"),
                   "files": [{k: v for k, v in j.items() if k != "url"} for j in jobs]},
                  fh, indent=2)
    download(jobs)

    frames = sorted(f for f in os.listdir(os.path.join(a.out, "lossless"))
                    if f.endswith(".png"))
    manifest = {}
    for f in frames:
        p = os.path.join(a.out, "lossless", f)
        manifest[f] = {"sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
                       "bytes": os.path.getsize(p)}
    with open(os.path.join(a.out, "lossless_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    ev = order_evidence(a.out)
    with open(os.path.join(a.out, "frame_order_evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(ev, fh, indent=2)

    empty = [f for f, m in manifest.items() if m["bytes"] == 0]
    if empty:
        raise SystemExit(f"FETCH_HALT zero-length frames: {empty}")

    print("FETCH_OK " + json.dumps({
        "frames": len(frames), "out": a.out,
        "array_order_mean_diff": ev["results_array_order"]["mean"],
        "hash_sorted_mean_diff": ev["hash_sorted_order"]["mean"],
        "ratio": (ev["hash_sorted_order"]["mean"] / ev["results_array_order"]["mean"]
                  if ev["results_array_order"]["mean"] else None)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
