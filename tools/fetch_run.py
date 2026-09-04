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
    114 -> <name>_00000.mp4   the H.264 review copy

The node split is the whole point. The first noise floor was measured on frames that had
been through H.264 on both sides, so its deltas carried codec noise of unknown size on
top of model variance. Everything downstream of this reads `lossless/`.

**The map is a flag as of E11 (2026-08-12), and that is a fix rather than a feature.** It
was a module constant naming E02's node ids, so pointing this tool at any later
experiment's dump sorted every frame into the fallback branch and named them all after the
run — silently, with a plausible count printed. E10's closing lesson states the shape:
*a tool that names an experiment in a literal is a tool that will lie the first time it is
reused.* Pass `--node-map=41=startprobe,71=lossless` for a graph whose taps sit elsewhere.

--------------------------------------------------------------------------------
The three andons this tool carries, and why the flag alone was not the fix

Making the map a flag left the fallback branch in place: a dump whose source node the map
did not name still landed on a single path named after the run, once per file, while
`counts` was incremented per file. So the printed count was the PLANNED count and never
the file count. Measured 2026-09-03: a 5-frame dump from a graph whose tap is node 71,
run without `--node-map`, printed `by_node {"71": 5}` and left the run directory holding
only `urls.json`.

* **Gate FETCH · unmapped node.** A source node that neither `--node-map` nor
  `--video-nodes` names now HALTS. Forgetting the flag can no longer reproduce the
  original defect, because there is no branch left to fall back into. The video tap's
  outputs are indexed as well, so two files from one mapped node cannot overwrite either.
* **Gate FETCH · the download actually landed.** `subprocess.run` carried no `check=True`,
  its return code was never inspected, and nothing compared the plan to what reached disk.
  Measured with the call stubbed to return code 1: the tool printed `FETCH_RUN` and
  returned `None`, i.e. exit 0. Both directions are now checked — a non-zero downloader,
  and any planned file that is missing or zero-length. `--fail-with-body` means an HTTP
  error body lands at the `-o` path and counts as a file, so a matching count is not
  evidence the bytes are a generation; the zero-length clause is what catches the rest.
* **The manifest path travels in the ENVIRONMENT, never in the command.** It used to be
  interpolated into a single-quoted PowerShell literal, so `--run="r'; echo INJECTED; #"`
  closed the literal and the remainder parsed as separate statements. No privilege
  boundary is crossed — the operator already owns the command line — but an apostrophe in
  a run name mangled the command and every download failed silently. The command string
  is now a constant that no operator input can reach.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import GateFailure  # noqa: E402

NODE_DIR = {"301": "batchprobe", "302": "lossless"}

#: Source nodes whose files land beside the run directory rather than in a subdirectory —
#: E02's H.264 review tap. Named rather than implied by a fallback branch: the branch is
#: what wrote a clip's frames to one path and printed a plausible count.
VIDEO_NODES = ("114",)

#: The environment variable the downloader reads the manifest path out of. Nothing about
#: the operator's input reaches the command string.
MANIFEST_ENV = "ARMATURE_FETCH_MANIFEST"


class FetchHalt(GateFailure):
    """A retrieval did not happen, or did not happen the way the plan says.

    **The andon is on the direction the invariant does not bound.** Every count in this
    tool is computed from the dump, which is a description of what the cloud produced —
    nothing in it is evidence about the local disk. So the counts can all read correctly
    while the run directory is empty, holds error bodies, or holds one file where a clip
    should be. That is the direction this gate points.
    """

    gate = "FETCH"


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


def parse_video_nodes(text):
    """`"114,115"` -> `("114", "115")`. Same halt-rather-than-default rule as the map."""
    if text is None:
        return tuple(VIDEO_NODES)
    ids = tuple(s.strip() for s in text.split(",") if s.strip())
    if not ids:
        raise SystemExit(
            "--video-nodes parsed to nothing; a graph with no video tap is written as "
            "--video-nodes=none rather than as an empty string")
    if ids == ("none",):
        return ()
    return ids


def plan(results, base, run, node_dir, video_nodes):
    """Where each returned file lands, and the per-node count. Raises on an unnamed node.

    Returns `(jobs, counts)` where `jobs` is a list of `(url, out)` pairs. Every `out` is
    distinct by construction, and that property is asserted before returning: the defect
    this replaces produced N jobs sharing one path while `counts` read N.
    """
    named = set(node_dir) | set(video_nodes)
    unmapped = sorted({str(r["source_node_id"]) for r in results
                       if str(r["source_node_id"]) not in named})
    if unmapped:
        raise FetchHalt(
            f"the dump carries source node(s) {unmapped}, which neither --node-map "
            f"({sorted(node_dir)}) nor --video-nodes ({sorted(video_nodes)}) names. The "
            f"fallback this replaces wrote every such file to one path named after the "
            f"run and printed the planned count beside it, so a clip's frames became one "
            f"file and a later measurement was taken on a run that is not the run",
            {"unmapped": unmapped, "node_map": dict(node_dir),
             "video_nodes": list(video_nodes)})

    jobs, counts = [], {}
    for r in results:
        nid = str(r["source_node_id"])
        i = counts.get(nid, 0)
        counts[nid] = i + 1
        if nid in node_dir:
            out = os.path.join(base, node_dir[nid], f"{i:05d}.png")
        else:
            ext = os.path.splitext(r["filename"])[1] or ".bin"
            out = os.path.join(base, f"{run}_{i:05d}{ext}")
        jobs.append((r["url"], out))

    outs = [o for _, o in jobs]
    if len(set(outs)) != len(outs):
        dupes = sorted({o for o in outs if outs.count(o) > 1})
        raise FetchHalt(
            f"the plan writes {len(outs)} file(s) to {len(set(outs))} path(s); "
            f"{dupes} would be overwritten while every count still read right",
            {"n_jobs": len(outs), "n_paths": len(set(outs)), "collisions": dupes})
    return jobs, counts


def download(manifest_path):
    """pwsh + curl, with the manifest path in the environment and the exit code inspected.

    The command string below is a CONSTANT. Nothing derived from `--run`, `--root` or the
    dump is interpolated into it, which is the whole fix for the quoting defect: an
    apostrophe in a run name used to close the single-quoted literal and turn the rest of
    the line into separate PowerShell statements.
    """
    ps = (
        f"$j = Get-Content -LiteralPath $env:{MANIFEST_ENV} -Raw | ConvertFrom-Json; "
        "$j | ForEach-Object -Parallel "
        "{ curl.exe -sS -L --fail-with-body -o $_.out -- $_.url } "
        "-ThrottleLimit 12"
    )
    env = dict(os.environ)
    env[MANIFEST_ENV] = os.path.abspath(manifest_path)
    proc = subprocess.run(["pwsh", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise FetchHalt(
            f"the downloader exited {proc.returncode}. Nothing was compared to the plan "
            f"below this line before this gate existed, so the run reported FETCH_RUN "
            f"with an empty directory",
            {"returncode": proc.returncode,
             "stdout": (proc.stdout or "")[-2000:],
             "stderr": (proc.stderr or "")[-2000:]})
    return proc


def verify_downloads(jobs, directories=(), suffixes=(".png",)):
    """Gate FETCH · ANDON — the files on disk are the planned files, and nothing else.

    Three directions, and the third is wave 6's addition. Missing and zero-length bound
    the direction where the cloud's counts read right over an empty directory. The EXTRA
    direction bounds the opposite one: `main` used to count the mapped directory with
    `os.listdir` while `counts` counted the plan, and printed both numbers side by side
    with nothing comparing them. Measured 2026-09-04 with the downloader stubbed — a
    3-frame dump fetched into a run directory whose `lossless/` already held a stale
    `00099.png` printed `by_node {"302": 3}` beside `downloaded {"lossless": 4}` under a
    green `gate_FETCH`. The stray is not hypothetical downstream: `encode_control` and
    `invert_frames` build their frame populations with a bare listdir over this directory.

    `directories` is the mapped subdirectories the plan writes into; a file there carrying
    one of `suffixes` that no job planned raises. Directories are supplied by the caller
    rather than derived from the jobs, so a mapped directory the plan never wrote into is
    still swept.

    A job is either this tool's `(url, out)` pair or `fetch_t2v_run`'s dict carrying an
    `out` key — the two fetchers share ONE andon, so it reads both plan shapes rather than
    forcing one of them to be rewritten around the other.
    """
    outs = [j["out"] if isinstance(j, dict) else j[1] for j in jobs]
    planned = {os.path.abspath(o) for o in outs}
    missing = sorted(o for o in outs if not os.path.isfile(o))
    empty = sorted(o for o in outs
                   if os.path.isfile(o) and os.path.getsize(o) == 0)
    extra = []
    for d in directories:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p) or os.path.splitext(name)[1] not in suffixes:
                continue
            if os.path.abspath(p) not in planned:
                extra.append(p)
    ev = {"planned": len(outs), "missing": missing, "empty": empty, "extra": extra,
          "landed": len(outs) - len(missing),
          "swept_directories": [os.path.abspath(d) for d in directories]}
    if missing or empty or extra:
        raise FetchHalt(
            f"{len(outs)} file(s) were planned; {len(missing)} never landed, "
            f"{len(empty)} are zero length and {len(extra)} file(s) in the run directory "
            f"were planned by no job. The measurement taken from this directory would be "
            f"a measurement of a generation that was never retrieved, or of a population "
            f"that is not this run",
            ev)
    ev["verdict"] = (f"{len(outs)} planned file(s), all present and non-empty, and no "
                     f"unplanned file in {len(ev['swept_directories'])} swept directory(s)")
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--root", default="outputs/E02/runs")
    ap.add_argument("--node-map", default=None,
                    help="`<node id>=<subdir>` pairs, comma separated, e.g. "
                         "--node-map=41=startprobe,71=lossless. Defaults to E02's taps "
                         "(301=batchprobe,302=lossless); a source node named by neither "
                         "this flag nor --video-nodes HALTS")
    ap.add_argument("--video-nodes", default=None,
                    help="node ids whose files land beside the run directory as "
                         "<run>_<index><ext>, comma separated. Defaults to E02's H.264 "
                         "review tap (114); pass --video-nodes=none for a graph with no "
                         "video output")
    a = ap.parse_args(argv)
    node_dir = parse_node_map(a.node_map)
    video_nodes = parse_video_nodes(a.video_nodes)

    with open(a.dump, encoding="utf-8") as fh:
        results = json.load(fh)["results"]

    base = os.path.join(a.root, a.run)
    # The plan raises before anything is created, so a dump this tool cannot sort leaves
    # no run directory to be read later as a run that happened.
    jobs, counts = plan(results, base, a.run, node_dir, video_nodes)

    for _, out in jobs:
        os.makedirs(os.path.dirname(out), exist_ok=True)
    manifest = os.path.join(base, "urls.json")
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump([{"url": u, "out": os.path.abspath(o)} for u, o in jobs], fh, indent=1)

    download(manifest)
    mapped = sorted({os.path.join(base, sub) for sub in node_dir.values()})
    landed = verify_downloads(jobs, directories=mapped)

    # Counted from the PLAN, never from the directory. The two numbers used to be computed
    # from different populations and printed beside each other, so a re-fetch into a
    # non-cleaned run directory disagreed with itself in a green receipt and nobody was
    # asked to compare them. The stray that made that possible now raises above this line.
    got = {sub: 0 for sub in node_dir.values()}
    for _, out in jobs:
        sub = os.path.basename(os.path.dirname(os.path.abspath(out)))
        if sub in got:
            got[sub] += 1
    vids = sorted(n for n in os.listdir(base)
                  if os.path.splitext(n)[1] in (".mp4", ".webm", ".mkv"))
    print("FETCH_RUN " + json.dumps({
        "run": a.run, "dir": base, "by_node": counts, "downloaded": got, "video": vids,
        "gate_FETCH": landed["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
