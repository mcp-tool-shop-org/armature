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
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)

NODE_DIR = {"301": "batchprobe", "302": "lossless"}

#: Source nodes whose files land beside the run directory rather than in a subdirectory —
#: E02's H.264 review tap. Named rather than implied by a fallback branch: the branch is
#: what wrote a clip's frames to one path and printed a plausible count.
VIDEO_NODES = ("114",)

#: The environment variable the downloader reads the manifest path out of. Nothing about
#: the operator's input reaches the command string.
MANIFEST_ENV = "ARMATURE_FETCH_MANIFEST"

#: Where each parallel job writes its OWN exit code, and the variable the command string
#: reads that path out of — for the same reason the manifest path is in the environment:
#: nothing derived from the operator's input is interpolated into the command.
EXITS_ENV = "ARMATURE_FETCH_EXITS"
EXITS_NAME = "download_exits.json"

#: The eight bytes every PNG begins with. `--fail-with-body` writes an HTTP error body to
#: the `-o` path, so "present and non-empty" is satisfied by a 35-byte JSON refusal; the
#: content clause in `verify_downloads` is what tells the two apart. Read from the format
#: spec, the same source `build_camera_i2v_payload.png_header` reads its IHDR layout from.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\x0a"


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

    WARNING These were `raise SystemExit(<str>)` until wave 10 (F-af78df0f). CPython
    renders that as a bare stderr line and exit code **1** - the code this module's own
    comment reserves for "this tool crashed" - and `except SystemExit: raise` in the
    `__main__` block carries it straight past the handler, so no `FETCH_RUN_HALT` line and
    no evidence dict was produced for what the docstring above calls a halt. Measured
    2026-09-04: `fetch_run.py --dump=nonexistent.json --run=r --node-map=bogus` printed the
    sentence and exited 1; `--video-nodes=,` did the same. The typed path one screen down -
    `plan`'s unmapped-node clause - raises `FetchHalt` with an evidence dict and reaches
    the operator as exit 2 plus the sentinel. Wave 8 closed this class in the sibling
    (`fetch_t2v_run.plan`, F-e3af7342); these four were left behind.
    """
    if not text:
        return dict(NODE_DIR)
    out = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if part.count("=") != 1:
            raise FetchHalt(
                f"--node-map entry {part!r} is not `<node id>=<directory>`; a map that "
                f"cannot be read must halt rather than quietly leave E02's default in "
                f"place over another experiment's graph",
                {"clause": "node_map_entry_shape", "entry": part, "text": text})
        nid, sub = (s.strip() for s in part.split("="))
        if not nid or not sub:
            raise FetchHalt(
                f"--node-map entry {part!r} has an empty side",
                {"clause": "node_map_entry_empty_side", "entry": part, "text": text,
                 "node_id": nid, "directory": sub})
        # ---- ANDON, wave 12 (F-a72178c2). `out[nid] = sub` was last-write-wins with no
        # clause, in the function whose docstring states that a malformed map must not fall
        # back silently. Measured: `parse_node_map("301=batchprobe,301=lossless")` returned
        # {"301": "lossless"} with no halt, so a clip's frames landed in a directory named
        # for another tap while every count in the receipt read right — `got` and `vids` are
        # both derived from the plan, so nothing downstream could see it. The same shape one
        # door over is already refused: `gate_saved_graph.link_table` raises on a link id
        # declared twice, because which one a socket resolves to is an accident of order.
        if nid in out:
            raise FetchHalt(
                f"--node-map names node {nid} twice, as {out[nid]!r} and {sub!r}. Which "
                f"directory that tap's frames land in would be an accident of the order the "
                f"pairs were typed in, and the only symptom would be a directory of files "
                f"with the wrong names under counts that all read right",
                {"gate": "FETCH", "andon": "FetchHalt", "clause": "node_map_duplicate_id",
                 "node_id": nid, "duplicates": {nid: [out[nid], sub]}, "text": text})
        out[nid] = sub
    if not out:
        raise FetchHalt(
            "--node-map parsed to nothing",
            {"clause": "node_map_empty", "entry": None, "text": text})
    return out


def parse_video_nodes(text):
    """`"114,115"` -> `("114", "115")`. Same halt-rather-than-default rule as the map.

    Typed for the same reason as `parse_node_map` above (wave 10, F-af78df0f).
    """
    if text is None:
        return tuple(VIDEO_NODES)
    ids = tuple(s.strip() for s in text.split(",") if s.strip())
    if not ids:
        raise FetchHalt(
            "--video-nodes parsed to nothing; a graph with no video tap is written as "
            "--video-nodes=none rather than as an empty string",
            {"clause": "video_nodes_empty", "entry": None, "text": text})
    if ids == ("none",):
        return ()
    return ids


def plan(results, base, run, node_dir, video_nodes):
    """Where each returned file lands, and the per-node count. Raises on an unnamed node.

    Returns `(jobs, counts)` where `jobs` is a list of `(url, out)` pairs. Every `out` is
    distinct by construction, and that property is asserted before returning: the defect
    this replaces produced N jobs sharing one path while `counts` read N.
    """
    # ---- ANDON, wave 12 (F-4421d98f). An operator pastes a dump for a job that has
    # returned nothing yet. `plan` returned `([], {})`, `main` then wrote `urls.json` into a
    # directory the (empty) job loop never created, and the tool died `FileNotFoundError`
    # with `evidence: null` — a crash where a clause belongs, on the one input an operator
    # is most likely to produce by accident. The sibling `fetch_t2v_run` reached an
    # `IndexError` one step earlier and left a half-built run directory behind. One clause,
    # one wording, both planners; it raises before anything is created.
    if not results:
        raise FetchHalt(
            "the dump carries no results at all. A job that has returned nothing is not a "
            "run to fetch, and continuing would leave a directory a later session reads as "
            "a run that happened",
            {"gate": "FETCH", "andon": "FetchHalt", "clause": "empty_results",
             "n_results": 0, "run": run, "base": os.path.abspath(base)})

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


def download(manifest_path, exits_path=None):
    """pwsh + curl, with each job's own exit code recorded where this process can read it.

    The command string below is a CONSTANT. Nothing derived from `--run`, `--root` or the
    dump is interpolated into it, which is the whole fix for the quoting defect: an
    apostrophe in a run name used to close the single-quoted literal and turn the rest of
    the line into separate PowerShell statements.

    ⚠ **Why the exit is recorded per job rather than read off the process** (wave 12,
    F-ef81516f). The refusal below used to be `if proc.returncode != 0`, under a
    `ForEach-Object -Parallel` block. MEASURED ON THIS RIG 2026-09-04:

        pwsh -NoProfile -Command '$j = @(1,2); $j | ForEach-Object -Parallel
            { cmd.exe /c "exit 22" } -ThrottleLimit 12'          -> process exit 0

    A native non-zero exit inside a `-Parallel` runspace does not reach the pwsh process
    code, so every curl in a fetch could fail and this tool would print FETCH_RUN_OK. The
    sibling `fetch_t2v_run`'s `foreach ($x in $j)` shape exits 1 on the identical inner
    command — the two fetchers' identically-worded gates disagreed about whether they could
    fire at all. This is not the closed F-61771e61 ("the returncode is never inspected");
    the inspection existed and was structurally unreachable.

    And the backstop did not cover the gap it left: curl runs `--fail-with-body`, which
    writes the HTTP error body to the `-o` path, so three planned frames replaced by 35-byte
    `{"error":"AccessDenied","code":403}` bodies gave `missing=[] empty=[] extra=[]` and a
    green verdict. `verify_downloads` carries a content clause now.

    So each runspace records its own `$LASTEXITCODE` and curl's message into a JSON array,
    and this process reads it. Measured with the new shape and `cmd.exe /c "exit 22"` in
    curl's place: process exit 0, record `[{"out":…,"code":22,"message":"boom"}]`. **A
    missing or short record is a refusal too** — a gate whose evidence never arrived has not
    run, which is the exact shape this finding is about.
    """
    manifest_abs = os.path.abspath(manifest_path)
    exits_abs = os.path.abspath(
        exits_path or os.path.join(os.path.dirname(manifest_abs), EXITS_NAME))
    ps = (
        f"$j = Get-Content -LiteralPath $env:{MANIFEST_ENV} -Raw | ConvertFrom-Json; "
        "$r = $j | ForEach-Object -Parallel "
        "{ $o = & curl.exe -sS -L --fail-with-body -o $_.out -- $_.url 2>&1; "
        "[pscustomobject]@{ out = $_.out; url = $_.url; code = $LASTEXITCODE; "
        "message = ($o | Out-String).Trim() } } "
        "-ThrottleLimit 12; "
        f"ConvertTo-Json -InputObject @($r) -Depth 3 | "
        f"Set-Content -LiteralPath $env:{EXITS_ENV} -Encoding utf8"
    )
    env = dict(os.environ)
    env[MANIFEST_ENV] = manifest_abs
    env[EXITS_ENV] = exits_abs
    with open(manifest_abs, encoding="utf-8") as fh:
        planned = json.load(fh)
    proc = subprocess.run(["pwsh", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, env=env)
    base = {"gate": "FETCH", "andon": "FetchHalt", "process_returncode": proc.returncode,
            # the key wave 8's halt carried; kept so a reader of an older receipt and a
            # reader of this one are looking at the same field name
            "returncode": proc.returncode,
            "exits_record": exits_abs, "planned": len(planned),
            "stdout": (proc.stdout or "")[-2000:], "stderr": (proc.stderr or "")[-2000:]}
    # The process code is still read: it catches pwsh itself failing to start, or the
    # command string failing to parse. It is no longer the only thing read.
    if proc.returncode != 0:
        raise FetchHalt(
            f"the downloader process exited {proc.returncode}. Nothing was compared to the "
            f"plan below this line before this gate existed, so the run reported FETCH_RUN "
            f"with an empty directory",
            dict(base, clause="downloader_process_exit_nonzero"))
    if not os.path.isfile(exits_abs):
        raise FetchHalt(
            f"the downloader recorded no per-job exit at {exits_abs!r}. Its `-Parallel` "
            f"block does not propagate a native non-zero exit to the process code — "
            f"measured on this rig — so with no record there is nothing that could have "
            f"observed a failed curl, and a green line here would mean only that pwsh ran",
            dict(base, clause="downloader_exits_unobserved"))
    with open(exits_abs, encoding="utf-8") as fh:
        rows = json.load(fh)
    rows = rows if isinstance(rows, list) else [rows]
    if len(rows) != len(planned):
        raise FetchHalt(
            f"the downloader recorded {len(rows)} job exit(s) for {len(planned)} planned "
            f"download(s). The record is not evidence about this plan, and the clause that "
            f"reads it would be deciding on a population that is not the one fetched",
            dict(base, clause="downloader_exits_incomplete", recorded=len(rows)))
    failed = [r for r in rows if int(r.get("code") or 0) != 0]
    if failed:
        raise FetchHalt(
            f"{len(failed)} of {len(rows)} download(s) exited non-zero: "
            + "; ".join(f"{os.path.basename(str(r.get('out')))} -> {r.get('code')} "
                        f"{str(r.get('message') or '')[:120]}" for r in failed[:5])
            + ". The pwsh process itself exited "
            f"{proc.returncode}, because a native non-zero exit inside a -Parallel runspace "
            f"does not reach it; without this record every curl in a fetch could fail under "
            f"a printed FETCH_RUN_OK",
            dict(base, clause="downloader_job_exit_nonzero", failed=failed))
    return proc, {"gate": "FETCH", "clause": "downloader_job_exits",
                  "record": exits_abs, "jobs": len(rows),
                  "verdict": f"{len(rows)} download(s), each recording its own exit, "
                             f"all zero"}


#: The extensions a video tap lands under. The run ROOT is swept for these — a frame
#: suffix set would not see them, and a root swept for `.png` would call this tool's own
#: `urls.json` / `*_manifest.json` / `frame_order_evidence.json` strays. Compared
#: case-INSENSITIVELY, like `SWEEP_FRAME_SUFFIXES`.
VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv")


def derived_root_artifacts(run):
    """The names THIS pipeline's own downstream tools write into a run root.

    Named, dated exemption (wave 10, F-eff94830, 2026-09-04), and re-derived rather than
    asserted: the two spellings below are the review clip's, and each is checked against
    the tool that writes it by `tests/test_fetch_run.py`.

    * `review_<rate>x_<fps>fps.webp` - `make_review_clip.clip_name`'s CURRENT output. It is
      a `.webp` and `VIDEO_SUFFIXES` is (.mp4, .webm, .mkv), so the canonical name never
      reaches the root sweep at all; it is listed so the exemption survives a change of
      suffix rather than depending on one.
    * `<run>_review_*.mp4` - a SUPERSEDED generation's name, and the only spelling that
      actually fires today. Measured read-only against the rig's real run directories by
      replaying each committed `urls.json` plan back through `verify_downloads`: 17 of the
      20 non-recovered runs PASS, and three raise with missing=0, empty=0 and
      extra=['A0r1_review_8fps.mp4'] / ['A1b_review_8fps.mp4'] / ['A2_review_8fps.mp4'] -
      outputs/E02/runs/A0r1, .../A1b and .../A2.

    Why an exemption and not a narrower sweep: the misreporting the root sweep was added to
    prevent is separately closed one screen below - `vids` is derived from the PLAN, not
    from a listdir, so a stray root video can no longer be printed as this run's `video`.
    What the sweep adds on top of that is a REFUSAL, and its first three real inputs were
    artifacts this pipeline itself produced. An andon whose documented workaround is
    "delete a legitimate derived file" is how an operator learns to work around an andon.

    Bound to the run name, so another run's clip left in this directory still raises: that
    is a file about a generation this fetch is not retrieving.
    """
    return (re.compile(r"^" + re.escape(str(run)) + r"_review[_.].*$", re.IGNORECASE),
            re.compile(r"^review_[0-9.]+x_[0-9]+fps\.[a-z0-9]+$", re.IGNORECASE))


def verify_downloads(jobs, directories=(), suffixes=(".png",), root=None,
                     root_suffixes=VIDEO_SUFFIXES, root_exempt=()):
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

    ⚠ **Two populations sat outside the EXTRA direction until wave 8 (F-d85dafd9).**

    (1) `directories` was only the mapped frame subdirectories, and the VIDEO tap lands in
    the run ROOT as `<run>_<index><ext>`, which is never among them. Measured 2026-09-04
    against this rig's real run directories, read-only, by replaying each committed
    `urls.json` plan back through this function: all 20 non-recovered runs under
    `outputs/**` PASS a re-fetch of their own plan, and three of them —
    `outputs/E02/runs/A0r1`, `.../A1b`, `.../A2` — hold an unplanned `*_review_8fps.mp4` in
    the run root that `main` would report as THIS run's `video` under a green gate_FETCH.
    `root` closes it, swept for `root_suffixes` so the tool's own JSON records are not
    called strays. `fetch_t2v_run` left `donor<ext>` unswept for the identical reason.

    (2) The suffix test was `os.path.splitext(name)[1] not in suffixes` — case SENSITIVE —
    while both frame consumers match case-insensitively (`encode_control.py:126` and
    `invert_frames.py:70` use `n.lower().endswith('.png')`). Measured with a stubbed run
    directory: a stale `00099.PNG` beside two planned frames gave `extra=[]` and the
    verdict "no unplanned file in 1 swept directory(s)", while the consumers' population
    read `['00000.png', '00001.png', '00099.PNG']`. The andon and its consumers share one
    population rule now.
    """
    outs = [j["out"] if isinstance(j, dict) else j[1] for j in jobs]
    planned = {os.path.abspath(o) for o in outs}
    missing = sorted(o for o in outs if not os.path.isfile(o))
    empty = sorted(o for o in outs
                   if os.path.isfile(o) and os.path.getsize(o) == 0)
    swept = [(d, tuple(s.lower() for s in suffixes)) for d in directories]
    if root:
        swept.append((root, tuple(s.lower() for s in root_suffixes)))
    extra, exempted = [], []
    root_abs = os.path.abspath(root) if root else None
    for d, want in swept:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p) or os.path.splitext(name)[1].lower() not in want:
                continue
            if os.path.abspath(p) in planned:
                continue
            # The exemption applies to the run ROOT only, and it is RECORDED, never silent:
            # a reader of this evidence sees which files were tolerated and by which rule.
            if (root_abs is not None and os.path.abspath(d) == root_abs
                    and any(rx.match(name) for rx in root_exempt)):
                exempted.append(p)
                continue
            extra.append(p)
    # ---- ANDON, wave 12 (F-ef81516f). "Present and non-empty" is satisfied by an HTTP
    # error body: curl runs `--fail-with-body`, which WRITES the body to the `-o` path.
    # Measured before this clause: three planned frames replaced by 35-byte
    # `{"error":"AccessDenied","code":403}` bodies returned missing=[], empty=[], extra=[]
    # and the verdict "3 planned file(s), all present and non-empty" — and a measurement
    # taken from that directory is a measurement of a paid generation that was never
    # retrieved. The clause binds only what the PLAN named: a `.png` output must begin with
    # the PNG signature. Suffixes this tool has no signature for are counted, not judged.
    wrong_type, content_checked = [], {"png": 0}
    for o in outs:
        if os.path.splitext(o)[1].lower() != ".png" or not os.path.isfile(o):
            continue
        if os.path.getsize(o) == 0:
            continue          # the `empty` clause below names that better than this one
        content_checked["png"] += 1
        with open(o, "rb") as fh:
            head = fh.read(8)
        if head != PNG_SIGNATURE:
            wrong_type.append({"out": os.path.abspath(o), "expected": "png",
                               "first_8_bytes": head.hex(),
                               "bytes": os.path.getsize(o)})

    ev = {"planned": len(outs), "missing": missing, "empty": empty, "extra": extra,
          "wrong_type": wrong_type, "content_checked": content_checked,
          "root_exempt_matched": exempted,
          "root_exempt_patterns": [rx.pattern for rx in root_exempt],
          "landed": len(outs) - len(missing),
          "swept_directories": [os.path.abspath(d) for d, _ in swept],
          "swept_suffixes": {os.path.abspath(d): list(w) for d, w in swept}}
    if missing or empty or extra:
        raise FetchHalt(
            f"{len(outs)} file(s) were planned; {len(missing)} never landed, "
            f"{len(empty)} are zero length and {len(extra)} file(s) in the run directory "
            f"were planned by no job. The measurement taken from this directory would be "
            f"a measurement of a generation that was never retrieved, or of a population "
            f"that is not this run",
            ev)
    if wrong_type:
        raise FetchHalt(
            f"{len(wrong_type)} of the {content_checked['png']} planned .png file(s) on "
            f"disk are not the content type the plan asked for: "
            + "; ".join(f"{os.path.basename(w['out'])} begins {w['first_8_bytes']!r} "
                        f"({w['bytes']} bytes)" for w in wrong_type[:5])
            + ". curl runs --fail-with-body, so an HTTP error body lands at the -o path and "
              "satisfies `present and non-empty`. A measurement taken from this directory "
              "would be a measurement of a generation that was never retrieved",
            dict(ev, clause="downloaded_body_is_not_the_planned_type"))
    ev["verdict"] = (f"{len(outs)} planned file(s), all present and non-empty, "
                     f"{content_checked['png']} of them PNG-signature checked, and no "
                     f"unplanned file in {len(ev['swept_directories'])} swept directory(s)"
                     + (f"; {len(exempted)} derived artifact(s) of this run's own were "
                        f"tolerated by name: "
                        f"{[os.path.basename(x) for x in exempted]}" if exempted else ""))
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

    _proc, gate_exits = download(manifest)
    mapped = sorted({os.path.join(base, sub) for sub in node_dir.values()})
    landed = verify_downloads(jobs, directories=mapped, root=base,
                              root_exempt=derived_root_artifacts(a.run))

    # Counted from the PLAN, never from the directory. The two numbers used to be computed
    # from different populations and printed beside each other, so a re-fetch into a
    # non-cleaned run directory disagreed with itself in a green receipt and nobody was
    # asked to compare them. The stray that made that possible now raises above this line.
    got = {sub: 0 for sub in node_dir.values()}
    for _, out in jobs:
        sub = os.path.basename(os.path.dirname(os.path.abspath(out)))
        if sub in got:
            got[sub] += 1
    # From the PLAN, like `got` above. This was the last population in this tool read from
    # the directory: a bare `os.listdir(base)` filtered to the video extensions, so a prior
    # run's video left in a re-used --out was printed as THIS run's. The video jobs are the
    # ones the plan writes to the run root itself rather than into a mapped subdirectory.
    vids = sorted(os.path.basename(o) for _, o in jobs
                  if os.path.dirname(os.path.abspath(o)) == os.path.abspath(base))
    # The SUCCESS half of the exit convention (wave 10). `<PREFIX>_OK ` uses the SAME
    # prefix this file's `__main__` block prints on a halt, so one AST read of that block
    # derives both directions of the census. The tree spelled this four ways before.
    print("FETCH_RUN_OK " + json.dumps({
        "run": a.run, "dir": base, "by_node": counts, "downloaded": got, "video": vids,
        "gate_FETCH": landed["verdict"], "gate_EXITS": gate_exits["verdict"]}))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `FETCH_RUN_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("FETCH_RUN_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
