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

--------------------------------------------------------------------------------
What the discriminator DOES, recorded because for one arc it did nothing

Until 2026-09-03 the ratio was computed, written to `frame_order_evidence.json`, printed
inside the FETCH_OK line — and compared to nothing. No threshold, no raise. The
zero-length-frame check three lines below it raises, so the file already knew the
difference between reporting and gating; a shuffled clip would have been written, FETCH_OK
printed, and the ratio near 1.0 noticed only if a human opened the JSON.

**The choice made, and the one deliberately not made.** A numeric floor was refused: no
calibrated floor for this ratio has been measured on any provider, and inventing one here
would be a pass condition picked while looking at the results it judges. What the order
rule claims is DIRECTIONAL — if the array order is the temporal order, differencing it
gives a SMALLER number than differencing a hash-sorted permutation of the same frames. So
the boundary is the sign of that comparison and nothing else: `ratio > 1` is the claim,
`ratio <= 1` contradicts it, and an undefined ratio (all frames identical) decides
nothing. Anything but the first raises `FETCH_ORDER_UNVOUCHED` and FETCH_OK is not
printed. E09's measured 0.703 vs 5.314 is reported as a magnitude, never graded.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ONE FetchHalt and ONE plan-to-disk andon across the two fetchers, not two of each.
# `fetch_run` already carried both; this file carried a second exception class with the
# same gate id and no plan-to-disk check at all, under a comment claiming the two were the
# same fix. Wave 6: the sibling's implementation is imported rather than re-written.
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)
from fetch_run import FetchHalt, verify_downloads  # noqa: E402,F401

TOOL_VERSION = "E09.A3"

LOSSLESS_NODE = "70"
VIDEO_NODE = "81"

#: The environment variable the downloader reads the manifest path out of. The command
#: string is a constant; nothing derived from `--out` or from the dump is interpolated
#: into it. Same fix, same day, as `fetch_run.py`'s — and as of wave 6 the same
#: INTERPRETER too: this file shelled to `powershell` (Windows PowerShell 5.1) while the
#: sibling shelled to `pwsh` (PowerShell 7, the only cross-platform one) directly under a
#: comment asserting they were the same.
MANIFEST_ENV = "ARMATURE_FETCH_MANIFEST"


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
            # `fetch_run.plan` raises a typed FetchHalt with an evidence dict for this
            # exact clause. A SystemExit here left no machine-readable record and walked
            # straight past any caller catching GateFailure.
            raise FetchHalt(
                f"unexpected source node {nid}; this graph emits only "
                f"{LOSSLESS_NODE} (lossless) and {VIDEO_NODE} (video)",
                {"unexpected_node": nid, "known": [LOSSLESS_NODE, VIDEO_NODE]})
    return jobs


def download(jobs):
    """curl, behind a `--` terminator, with the manifest path in the environment.

    Two defects lived in the old three lines. A url read straight out of an
    operator-pasted dump sat in OPTION position with no terminator, so an entry beginning
    with a dash was read by curl as a flag — and both `-o` and `-K` (read a config file)
    are reachable that way; the sibling `fetch_run.py` already had the terminator. And the
    manifest path was interpolated into a single-quoted PowerShell literal, so an
    apostrophe anywhere in `--out` closed the literal and the remainder parsed as separate
    statements. The command string below is a CONSTANT.
    """
    for j in jobs:
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
    manifest = [{"url": j["url"], "out": os.path.abspath(j["out"])} for j in jobs]
    tmp = os.path.join(os.path.dirname(jobs[0]["out"]), "_urls.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    ps = (f"$j = Get-Content -LiteralPath $env:{MANIFEST_ENV} -Raw | ConvertFrom-Json; "
          "foreach ($x in $j) "
          "{ curl.exe -sS -L --fail-with-body -o $x.out -- $x.url }")
    env = dict(os.environ)
    env[MANIFEST_ENV] = os.path.abspath(tmp)
    proc = subprocess.run(["pwsh", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise FetchHalt(
            f"the downloader exited {proc.returncode}; the frames this run would be "
            f"measured on are not on disk",
            {"returncode": proc.returncode,
             "stdout": (proc.stdout or "")[-2000:],
             "stderr": (proc.stderr or "")[-2000:]})
    os.remove(tmp)
    return proc


def gate_order_evidence(ev):
    """Gate ORDER · ANDON — the discriminator must point the way the order rule claims.

    The boundary is the SIGN of the comparison and not a magnitude: see the module
    docstring for why no floor is invented here. Raises `FETCH_ORDER_UNVOUCHED` rather
    than letting `main` print FETCH_OK over an order this tool cannot vouch for.
    """
    array_mean = ev["results_array_order"]["mean"]
    hash_mean = ev["hash_sorted_order"]["mean"]
    ratio = (hash_mean / array_mean) if array_mean else None
    g = {"gate": "ORDER", "array_order_mean_diff": array_mean,
         "hash_sorted_mean_diff": hash_mean, "ratio": ratio,
         "boundary_is": (
             "the sign of the comparison, not a magnitude. No calibrated floor for this "
             "ratio has been measured on any provider, and a threshold invented while "
             "looking at the result it judges is the pass condition CLAUDE.md forbids. "
             "ratio > 1 is the order rule’s own directional claim; ratio <= 1 "
             "contradicts it; an undefined ratio decides nothing. E09 measured 0.703 vs "
             "5.314 (7.6x) and that magnitude is reported, never graded")}
    if ratio is None or not (ratio > 1.0):
        raise FetchHalt(
            "FETCH_ORDER_UNVOUCHED: differencing the results-array order gives "
            f"{array_mean!r} and differencing a hash-sorted permutation of the same "
            f"frames gives {hash_mean!r}. The array order is not the tighter one, so "
            f"this run’s temporal order has no evidence behind it and FETCH_OK is "
            f"not printed. The frames and the evidence file are left on disk",
            g)
    g["verdict"] = (f"the results-array order differences {ratio:.3g}x tighter than a "
                    f"hash-sorted permutation of the same frames")
    return g


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

    # Gate FETCH · ANDON, carried from `fetch_run.verify_downloads` rather than written a
    # second time. This tool had NO plan-to-disk check: the frame population came from
    # `os.listdir`, nothing compared it to `plan()` in either direction, and the VIDEO job
    # was never checked at all. Measured 2026-09-04 with `download` stubbed: a 4-frame dump
    # fetched into an --out whose lossless/ held one stale 00009.png printed FETCH_OK
    # {"frames": 5} with the stale frame in the sha256 manifest and inside both arms of
    # Gate ORDER; a dump whose frame 3 and video never landed printed FETCH_OK
    # {"frames": 4} with 00000,00001,00002,00004 differenced as if consecutive.
    #
    # Wave 8, F-d85dafd9: `root=a.out` as well. This tool passed the single lossless
    # directory and left `donor<ext>` in the root unswept for exactly the reason `fetch_run`
    # left its video tap unswept, so a re-fetch into a used --out kept a prior run's donor.
    # The root is swept for the VIDEO suffixes only, so the four JSON records this tool
    # writes beside it are not called strays.
    landed = verify_downloads(jobs, directories=[os.path.join(a.out, "lossless")],
                              root=a.out)

    # The frame population is the PLAN, never a directory listing.
    frames = [os.path.basename(j["out"]) for j in jobs if j["array_index"] is not None]
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
        raise FetchHalt(f"FETCH_HALT zero-length frames: {empty}",
                        {"zero_length": empty, "frames": len(frames)})

    # The evidence file is already on disk above, so a halt here leaves the measurement
    # that fired it behind rather than making the next session re-fetch to see it.
    order = gate_order_evidence(ev)

    print("FETCH_OK " + json.dumps({
        "frames": len(frames), "out": a.out,
        "array_order_mean_diff": order["array_order_mean_diff"],
        "hash_sorted_mean_diff": order["hash_sorted_mean_diff"],
        "ratio": order["ratio"], "gate_ORDER": order["verdict"],
        "gate_FETCH": landed["verdict"]}))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `FETCH_T2V_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("FETCH_T2V_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
