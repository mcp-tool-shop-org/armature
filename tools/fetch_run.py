#!/usr/bin/env python
"""fetch_run — turn a get_output dump into a run directory on disk.

    python tools/fetch_run.py --dump=<get_output.txt> --run=<name> [--node-map=41=a,71=b]

(`[--arm=A1a]` stood here until wave 12, F-4150910d. No parser in this file declares
`--arm`; the documented line exited 2 on argparse's "unrecognized arguments", which
is the code this module reserves for a gate refusal, with no FETCH_RUN_HALT line for
a wrapper to key on. The optional flag this tool actually takes is `--node-map`.)

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

from armature_core.errors import GateFailure  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.

# ---- SEAM 1 (wave 22): `single_path_segment`'s ONE home is `armature_core.parts`. It is
# ADOPTED BY IMPORT, never spelled a third time -- instruments-measure held two copies
# (`pack_pose_pack.py`, `resample_motion.py`) and SEAM 1 retired both. On the branch this
# was written on the import fell back to the `resample_motion` copy; wave-22 merge (coordinator, 2026-09-05)
# deleted that fallback, because on the merged tree it named a function that no longer
# exists and would have turned a missing home into a second, unrelated ImportError.
from armature_core.parts import single_path_segment       # noqa: E402

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

#: What the first bytes of a planned output must look like, keyed on the suffix the PLAN
#: wrote. Wave 18 (F-0124c714): this was a single `.png` branch, so the content clause —
#: the one that exists because `curl --fail-with-body` WRITES an HTTP error body to the
#: `-o` path — was bounded to the FRAME population and never reached the video tap, which
#: is the whole product of the generation.
#:
#: Each entry is `(offset, magic, human name)`: the bytes at `offset` must equal `magic`.
#:   * PNG        — the 8-byte signature at 0.
#:   * MP4 / MOV  — ISO base media: a box length, then the `ftyp` type at offset 4. The
#:     length varies, so only the type is asserted.
#:   * WebM / MKV — the EBML header `1A 45 DF A3` at 0.
#:   * WebP       — `RIFF` at 0, and the `WEBP` form type at 8 as a second entry.
CONTENT_SIGNATURES = {
    ".png": ((0, PNG_SIGNATURE, "png"),),
    ".mp4": ((4, b"ftyp", "mp4"),),
    ".m4v": ((4, b"ftyp", "m4v"),),
    ".mov": ((4, b"ftyp", "mov"),),
    ".webm": ((0, b"\x1a\x45\xdf\xa3", "webm"),),
    ".mkv": ((0, b"\x1a\x45\xdf\xa3", "mkv"),),
    ".webp": ((0, b"RIFF", "webp"), (8, b"WEBP", "webp")),
}

#: The bytes a JSON document can begin with. The cheap floor under every suffix the table
#: has no row for: `--fail-with-body` bodies are JSON, and a planned artifact never is.
JSON_FIRST_BYTES = (b"{", b"[")


class FetchHalt(GateFailure):
    """A retrieval did not happen, or did not happen the way the plan says.

    **The andon is on the direction the invariant does not bound.** Every count in this
    tool is computed from the dump, which is a description of what the cloud produced —
    nothing in it is evidence about the local disk. So the counts can all read correctly
    while the run directory is empty, holds error bodies, or holds one file where a clip
    should be. That is the direction this gate points.
    """

    gate = "FETCH"


#: Every key a `get_output` result row must carry for a planner to read it, and what each
#: one is used for. Both planners index all three: `fetch_run.plan` reads `source_node_id`
#: and `url` for every row and `filename` for a video tap; `fetch_t2v_run.plan` reads all
#: three for EVERY row (`cloud_name` is `r["filename"]`, and Gate ORDER's manifest is keyed
#: on it). Written out rather than implied by the index that raises, so a refusal names the
#: key and what it is for.
RESULT_ROW_KEYS = {
    "source_node_id": "the tap this file came from, which is what decides where it lands",
    "url": "where the file is fetched from",
    "filename": "the cloud-side name, whose suffix names the artifact's type and which "
                "Gate ORDER's manifest is keyed on",
}


def read_results_dump(path, *, flag="--dump", exc=None):
    """The pasted `get_output` dump, READ through clauses rather than indexed. · ANDON

    Wave 22, F-2380aca9. The ONE operator-supplied input both fetchers take reached the
    operator as a bare stdlib traceback: `json.load(fh)["results"]` with no clause, in a
    module whose own `__main__` comment tells wrappers to key on the `FETCH_RUN_HALT`
    sentinel and whose every other refusal is a typed `FetchHalt` with a clause.
    RE-MEASURED on `e8263a3` as five subprocesses of `fetch_run` — every one exit 1, the
    code this module reserves for "this tool crashed", with `"evidence": null`:

      * `--dump` naming no file        -> FETCH_RUN_HALT error `FileNotFoundError`
      * a dump with no `results` key   -> `KeyError: 'results'`
      * a dump that is not JSON        -> `JSONDecodeError`
      * a result row with no `url`     -> `KeyError: 'url'`
      * `results` holding strings      -> `TypeError: string indices must be integers`

    The sibling `fetch_t2v_run` carried the identical two lines and RE-MEASURED identically:
    a non-JSON dump -> `FETCH_T2V_HALT` `JSONDecodeError` evidence null; a dump with no
    `results` -> `FETCH_T2V_HALT` `KeyError: 'results'` evidence null.

    This is the same crash-where-a-clause-belongs shape wave 18 closed one tool over for
    `--saved` / `--api` (`graph_file_missing`) and `--frame`; the fetchers' `--dump` was not
    in that entry's sibling enumeration. The shape is
    `build_assembly_payload.read_seed_registration`'s — the reader that already models this
    for the committed seed registration: open, parse, shape, key, element, each its own
    clause word, one implementation and both callers.

    `exc` is the andon class the CALLER raises under, so each fetcher's halt names its own
    class; it defaults to this module's `FetchHalt`.
    """
    exc = FetchHalt if exc is None else exc
    ev = {"gate": "FETCH", "andon": exc.__name__, "flag": flag,
          "path": os.path.abspath(path)}
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as err:
        raise exc(
            f"{flag} {path!r} cannot be opened ({err.__class__.__name__}: {err}). The dump "
            f"is the one operator-supplied input this fetcher takes, and a path that names "
            f"nothing supplies no run to fetch",
            dict(ev, clause="dump_missing", error=err.__class__.__name__,
                 exists=os.path.exists(path), is_dir=os.path.isdir(path))) from err
    except json.JSONDecodeError as err:
        raise exc(
            f"{flag} {path!r} is not readable JSON ({err}). A dump this tool cannot parse "
            f"is not a description of a generation it can retrieve",
            dict(ev, clause="dump_unreadable", error=str(err))) from err
    if not isinstance(doc, dict):
        raise exc(
            f"{flag} {path!r} is a {type(doc).__name__}, not a JSON object with a "
            f"`results` key. `get_output` returns one record per file inside that key, and "
            f"the shape is part of what an operator pastes",
            dict(ev, clause="dump_not_a_mapping", read_as=type(doc).__name__))
    if "results" not in doc:
        raise exc(
            f"{flag} {path!r} declares no `results` key; it carries {sorted(map(str, doc))}. "
            f"The bare index this replaces raised a stdlib KeyError naming the key and "
            f"nothing else — no flag, no file, no receipt",
            dict(ev, clause="dump_no_results_key", keys=sorted(map(str, doc))))
    results = doc["results"]
    if not isinstance(results, list):
        raise exc(
            f"{flag} {path!r} declares `results` as a {type(results).__name__}, not a list. "
            f"Both planners iterate it and index each member; a non-list is a population "
            f"with an accidental answer",
            dict(ev, clause="dump_results_not_a_list",
                 read_as=type(results).__name__))
    bad_rows = [{"index": i, "type": type(r).__name__, "value": repr(r)[:80]}
                for i, r in enumerate(results) if not isinstance(r, dict)]
    if bad_rows:
        raise exc(
            f"{flag} {path!r} carries {len(bad_rows)} of {len(results)} `results` entries "
            f"that are not objects: "
            + "; ".join(f"index {b['index']} is a {b['type']} ({b['value']})"
                        for b in bad_rows[:5])
            + ". The planners index each row by name, so a string member raised "
              "`TypeError: string indices must be integers` at the exit code this module "
              "reserves for a crash",
            dict(ev, clause="dump_result_row_not_a_mapping", n_results=len(results),
                 offending=bad_rows))
    missing = [{"index": i, "missing": sorted(k for k in RESULT_ROW_KEYS if k not in r),
                "keys": sorted(map(str, r))}
               for i, r in enumerate(results)
               if any(k not in r for k in RESULT_ROW_KEYS)]
    if missing:
        raise exc(
            f"{flag} {path!r} carries {len(missing)} of {len(results)} `results` entries "
            f"missing a key the planners index: "
            + "; ".join(f"index {m['index']} lacks {m['missing']}" for m in missing[:5])
            + ". "
            + "; ".join(f"`{k}` is {why}" for k, why in RESULT_ROW_KEYS.items())
            + ". A row this tool cannot read is a file it would either lose or fetch to a "
              "path nothing planned",
            dict(ev, clause="dump_result_row_missing_a_key", n_results=len(results),
                 required_keys=sorted(RESULT_ROW_KEYS), offending=missing))
    return results


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
                {"gate": "FETCH", "andon": "FetchHalt", "clause": "node_map_entry_shape",
                 "entry": part, "text": text})
        nid, sub = (s.strip() for s in part.split("="))
        if not nid or not sub:
            raise FetchHalt(
                f"--node-map entry {part!r} has an empty side",
                {"gate": "FETCH", "andon": "FetchHalt", "clause": "node_map_entry_empty_side",
                 "entry": part, "text": text, "node_id": nid, "directory": sub})
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
            {"gate": "FETCH", "andon": "FetchHalt", "clause": "node_map_empty",
             "entry": None, "text": text})
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
            {"gate": "FETCH", "andon": "FetchHalt", "clause": "video_nodes_empty",
             "entry": None, "text": text})
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
            {"gate": "FETCH", "andon": "FetchHalt",
             "clause": "unexpected_source_node",
             "unmapped": unmapped, "node_map": dict(node_dir),
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
            {"gate": "FETCH", "andon": "FetchHalt", "clause": "plan_paths_collide",
             "n_jobs": len(outs), "n_paths": len(set(outs)),
             "collisions": dupes})
    return jobs, counts


#: The downloader command, as a CONSTANT (see `download`). Each runspace records its own
#: `$LASTEXITCODE` because a native non-zero exit inside `ForEach-Object -Parallel` does not
#: reach the pwsh process code — measured on this rig, 2026-09-04.
DOWNLOAD_PS = (
    f"$j = Get-Content -LiteralPath $env:{MANIFEST_ENV} -Raw | ConvertFrom-Json; "
    "$r = $j | ForEach-Object -Parallel "
    "{ $o = & curl.exe -sS -L --fail-with-body -o $_.out -- $_.url 2>&1; "
    "[pscustomobject]@{ out = $_.out; url = $_.url; code = $LASTEXITCODE; "
    "message = ($o | Out-String).Trim() } } "
    "-ThrottleLimit 12; "
    f"ConvertTo-Json -InputObject @($r) -Depth 3 | "
    f"Set-Content -LiteralPath $env:{EXITS_ENV} -Encoding utf8"
)

#: The same command with the URL left OUT of each row. `out` identifies a job uniquely —
#: `plan` refuses a plan whose paths collide — so nothing the gate reads is lost, and a
#: caller whose urls are signed does not gain a durable file naming them.
DOWNLOAD_PS_NO_URLS = (
    f"$j = Get-Content -LiteralPath $env:{MANIFEST_ENV} -Raw | ConvertFrom-Json; "
    "$r = $j | ForEach-Object -Parallel "
    "{ $o = & curl.exe -sS -L --fail-with-body -o $_.out -- $_.url 2>&1; "
    "[pscustomobject]@{ out = $_.out; code = $LASTEXITCODE; "
    "message = ($o | Out-String).Trim() } } "
    "-ThrottleLimit 12; "
    f"ConvertTo-Json -InputObject @($r) -Depth 3 | "
    f"Set-Content -LiteralPath $env:{EXITS_ENV} -Encoding utf8"
)


def download(manifest_path, exits_path=None, record_urls=True):
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
    code, so every curl in a fetch could fail and this tool would print FETCH_RUN_OK. This
    is not the closed F-61771e61 ("the returncode is never inspected"); the inspection
    existed and was structurally unreachable.

    ⚠ **CORRECTION, wave 14 (F-a3ba416b).** This paragraph used to close: "The sibling
    `fetch_t2v_run`'s `foreach ($x in $j)` shape exits 1 on the identical inner command —
    the two fetchers' identically-worded gates disagreed about whether they could fire at
    all." That is true only of a single-job run or a failure in the LAST job. RE-MEASURED
    ON THIS RIG 2026-09-04:

        pwsh -NoProfile -Command '$j = @(1,2,3); foreach ($x in $j)
            { cmd.exe /c "exit $(if($x -eq 1){22}else{0})" }'      -> process exit 0
        ...the same loop with the failure on the LAST element      -> process exit 1

    A `foreach` loop's process code reflects only the last native command, so the sibling's
    gate could not fire on a mid-loop failure either — and that claim is the reason the
    sibling was left without this per-job record. It has it now: `fetch_t2v_run.download`
    calls THIS function (one implementation, not a second shape).

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
    # TWO constants, selected by a boolean — not one string with a value interpolated into
    # it. Nothing derived from a run name, a path or a dump reaches the command line, which
    # is the whole of the quoting fix above; a caller's choice between two literals cannot
    # reopen it. `record_urls=False` exists for `fetch_t2v_run`, whose `_urls.json` is
    # deleted on every path BECAUSE it holds signed download links (wave 12, F-8ccedf71):
    # the exit record is the same object with the same exposure, so that fetcher asks for
    # the rows without the urls rather than gaining a durable file the earlier fix removed.
    ps = DOWNLOAD_PS if record_urls else DOWNLOAD_PS_NO_URLS
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
    # ---- wave 14, F-b5db1a40. A malformed or truncated record used to raise a bare
    # `JSONDecodeError` here, which left the `__main__` halt block printing exit 1 ("this
    # tool crashed") rather than a FETCH clause naming the record a reader could open.
    try:
        with open(exits_abs, encoding="utf-8") as fh:
            rows = json.load(fh)
    except (OSError, ValueError) as exc:
        raise FetchHalt(
            f"the downloader's exit record at {exits_abs!r} could not be read "
            f"({type(exc).__name__}: {exc}). The record IS the evidence this gate decides "
            f"on — the process code cannot see a failed curl in a -Parallel runspace — so "
            f"an unreadable one is a gate that has not run, not a gate that passed",
            dict(base, clause="downloader_exits_unreadable",
                 error=type(exc).__name__)) from exc
    rows = rows if isinstance(rows, list) else [rows]
    if len(rows) != len(planned):
        raise FetchHalt(
            f"the downloader recorded {len(rows)} job exit(s) for {len(planned)} planned "
            f"download(s). The record is not evidence about this plan, and the clause that "
            f"reads it would be deciding on a population that is not the one fetched",
            dict(base, clause="downloader_exits_incomplete", recorded=len(rows)))
    # ---- wave 14, F-b5db1a40. This read `int(r.get("code") or 0) != 0`, which collapses
    # "no exit was recorded for this job" into "this job exited zero" — contradicting this
    # function's own rule that a gate whose evidence never arrived has not run. Measured on
    # this rig with the command shape above and an UNLAUNCHABLE downloader: process exit 0
    # and every row `"code": null, "message": ""`, because a CommandNotFound error goes to
    # the runspace's error stream and not into the captured output. The row COUNT matches
    # the plan, so `downloader_exits_incomplete` does not fire either, and the verdict below
    # read "N download(s), each recording its own exit, all zero". `verify_downloads`
    # backstops the empty-directory case; what it does not backstop is a re-fetch into a
    # re-used run directory whose planned frames are already present from a PRIOR run.
    #
    # `int()` is kept only for values that are actually PRESENT: a null, an empty string, or
    # anything that will not parse is `unrecorded`, in a clause of its own, naming the job.
    # Wave 16, the readability half of F-dc32fa9d. The absent-code branch used to be
    # spelled `raise ValueError("no exit was recorded")` INSIDE this function's own `try`,
    # caught two lines down by the same handler that catches a `code` that will not parse.
    # It never left the loop and it was never a refusal - three jury seats read it as an
    # untyped refusal in a file where every refusal is a typed `FetchHalt`, which is the
    # whole reason it is written as a predicate now. The behaviour is unchanged and the
    # test below pins that: absent, blank and unparseable codes are all `unrecorded`.
    unrecorded, failed = [], []
    for i, row in enumerate(rows):
        row = row if isinstance(row, dict) else {"out": None, "code": None, "row": row}
        job = row.get("out") or f"<row {i}, no `out` recorded>"
        code = row.get("code")
        if code is None or (isinstance(code, str) and not code.strip()):
            unrecorded.append({"job": job, "code": row.get("code"),
                               "message": row.get("message")})
            continue
        try:
            code = int(code)
        except (TypeError, ValueError):
            unrecorded.append({"job": job, "code": row.get("code"),
                               "message": row.get("message")})
            continue
        if code != 0:
            failed.append(dict(row, code=code))
    if failed:
        raise FetchHalt(
            f"{len(failed)} of {len(rows)} download(s) exited non-zero: "
            + "; ".join(f"{os.path.basename(str(r.get('out')))} -> {r.get('code')} "
                        f"{str(r.get('message') or '')[:120]}" for r in failed[:5])
            + ". The pwsh process itself exited "
            f"{proc.returncode}, because a native non-zero exit inside a -Parallel runspace "
            f"does not reach it; without this record every curl in a fetch could fail under "
            f"a printed FETCH_RUN_OK",
            dict(base, clause="downloader_job_exit_nonzero", failed=failed,
                 unrecorded=unrecorded))
    if unrecorded:
        raise FetchHalt(
            f"{len(unrecorded)} of {len(rows)} download(s) recorded NO exit at all: "
            + "; ".join(f"{os.path.basename(str(u['job']))} -> code={u['code']!r}"
                        for u in unrecorded[:5])
            + ". A job whose exit was never observed is not a job that exited zero, and "
            f"this gate's own rule is that evidence which never arrived has not run. The "
            f"downloader itself may not have launched — a CommandNotFound inside a "
            f"-Parallel runspace goes to that runspace's error stream and leaves the row's "
            f"code null while the pwsh process exits 0",
            dict(base, clause="downloader_job_exit_unrecorded", unrecorded=unrecorded))
    return proc, {"gate": "FETCH", "clause": "downloader_job_exits",
                  "record": exits_abs, "jobs": len(rows),
                  "n_recorded": len(rows) - len(unrecorded), "n_unrecorded": 0,
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

    ⚠ **CORRECTION, wave 14 (F-ec454582).** This paragraph used to close: "Bound to the run
    name, so another run's clip left in this directory still raises: that is a file about a
    generation this fetch is not retrieving." That holds for the FIRST pattern and not the
    second. Measured in this worktree with `derived_root_artifacts('A2')`:
    `A2_review_8fps.mp4` matches pattern 0; `A0r1_review_8fps.mp4` matches neither (correct
    — another run's clip does raise); and `review_0.50x_8fps.mp4` matches pattern 1, a name
    carrying no run identity at all, so ANY run's review clip is exempted by it.
    RE-MEASURED on `e8263a3`, unchanged, plus the third row the wave-14 note did not take:
    `A2_review_0.50x_8fps.mp4` matches pattern 0, and `A0r1_review_0.50x_8fps.mp4` — another
    run's TOKENED clip — matches neither and correctly raises.

    ⚠⚠ **The wave-14 paragraph's PREMISE is stale, and this is its correction in place
    (wave 22, F-a25a7db9).** It closed "It cannot be otherwise from here:
    `make_review_clip.clip_name` returns `review_{rate:.2f}x_{fps}fps.<ext>` with no run
    token, and that tool is not this one's to change." READ in this worktree at
    `tools/make_review_clip.py:144-160`: `clip_name(fps, source_fps, run=None)` returns
    `f"{run}_{stem}"` when a token is KNOWN, and `run_token` (`:68-93`) derives one from
    `--frames`' own run root. That landed in wave 16 (F-78f49c7c), whose docstring names
    this function as the beneficiary. So the condition the block said blocked the fix was
    removed two waves before the block was read, and a session reading the correction was
    being told not to try.

    **What is NOT stale is the residue.** An UN-TOKENED clip is still produced whenever no
    token can be derived, so an exemption for that name is still needed — and it cannot be
    bound to a run, because the name carries no run. The fix is therefore not to delete it
    but to stop it being SILENT: `derived_root_artifact_rules` labels each rule, and
    `verify_downloads` records `root_exempt_matched_by`, so a reader of the receipt sees
    that a tolerated file was tolerated by a rule that could not tell which run produced it.
    `VIDEO_SUFFIXES` re-read on `e8263a3` as ('.mp4', '.webm', '.mkv'), so the canonical
    `.webp` clip still never reaches the sweep and today's live consequence remains nil; the
    pattern exists to survive a change of suffix, and on that day the receipt says which
    rule tolerated what. `tests/test_amend_w14_builders.py` pins the three measurements so
    the claim cannot drift back.
    """
    return tuple(rx for _label, _bound, rx in derived_root_artifact_rules(run))


#: The two exemption rules, each with the sentence a receipt records when it fires and
#: whether it can tell WHICH run produced the file it tolerated. Wave 22 (F-a25a7db9): the
#: second rule cannot, because `make_review_clip.clip_name` still returns an UN-TOKENED name
#: when no run token can be derived — and an exemption that cannot say which run it is about
#: may be kept only if the receipt says so.
def derived_root_artifact_rules(run):
    """`[(label, run_bound, compiled)]` — the exemptions, each able to name itself.

    `derived_root_artifacts` above returns just the patterns, for the callers that only
    need to match; `main` passes THESE, so the receipt records which rule tolerated what.
    """
    return (
        ("this run's own review clip, bound to the run token", True,
         re.compile(r"^" + re.escape(str(run)) + r"_review[_.].*$", re.IGNORECASE)),
        ("an UN-TOKENED review clip: `make_review_clip.clip_name` returns "
         "`review_<rate>x_<fps>fps.<ext>` with no run token when none can be derived from "
         "`--frames`, so this rule CANNOT tell which run produced the file it tolerated",
         False,
         re.compile(r"^review_[0-9.]+x_[0-9]+fps\.[a-z0-9]+$", re.IGNORECASE)),
    )


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
    extra, exempted, exempted_by = [], [], []
    # Wave 22 (F-a25a7db9): a rule may arrive as a bare compiled pattern (the wave-10 shape,
    # still used by every caller that only needs to match) or as
    # `(label, run_bound, compiled)` from `derived_root_artifact_rules`. Normalised here so
    # the receipt can name the rule that tolerated a file rather than only the file.
    exempt_rules = [r if isinstance(r, tuple) else (None, None, r)
                    for r in root_exempt]
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
            fired = ([(label, bound, rx) for label, bound, rx in exempt_rules
                      if rx.match(name)]
                     if root_abs is not None and os.path.abspath(d) == root_abs else [])
            if fired:
                label, bound, _rx = fired[0]
                exempted.append(p)
                exempted_by.append({"path": p, "rule": label, "run_bound": bound})
                continue
            extra.append(p)
    # ---- ANDON, wave 12 (F-ef81516f). "Present and non-empty" is satisfied by an HTTP
    # error body: curl runs `--fail-with-body`, which WRITES the body to the `-o` path.
    # Measured before this clause: three planned frames replaced by 35-byte
    # `{"error":"AccessDenied","code":403}` bodies returned missing=[], empty=[], extra=[]
    # and the verdict "3 planned file(s), all present and non-empty" — and a measurement
    # taken from that directory is a measurement of a paid generation that was never
    # retrieved.
    #
    # ⚠ **It reached the FRAMES and not the VIDEO** (wave 18, F-0124c714). The branch was
    # `if os.path.splitext(o)[1].lower() != ".png": continue`, while `plan` writes the video
    # result to `<run>_<index><ext>` with `ext` taken from the result filename — `.mp4`,
    # `.webm`, `.mkv` or `.bin`. Measured on the base tree: a two-job plan whose `.png`
    # carries a real PNG signature and whose `E13_00000.mp4` holds the same 35-byte
    # `{"error":"AccessDenied","code":403}` body returned a full PASS — "2 planned file(s),
    # all present and non-empty, 1 of them PNG-signature checked, and no unplanned file in 2
    # swept directory(s)", `wrong_type: []`. The gap was NAMED in prose one file over
    # (`fetch_t2v_run.download`), and naming a defect in prose is how it is RECORDED, not
    # how it is closed. In the scenario that module's own comment says is unbackstopped —
    # a re-fetch into a re-used run directory whose planned frames are already present from
    # a PRIOR run — the clip a measurement or a review sheet is built from is an error body
    # under a green gate_FETCH.
    #
    # Two readings, so a suffix with no row is still bounded:
    #   1. the SIGNATURE table, keyed on the suffix the plan wrote;
    #   2. the JSON floor, applied to every planned output whatever its suffix — a planned
    #      artifact never begins `{` or `[`, and an HTTP error body does.
    #
    # ⚠ **"Counted, not judged" was not true either.** `content_checked` carried a single
    # `png` key, so a non-PNG output incremented nothing and the receipt had NO key naming
    # the population that was never judged. It is per-suffix now, and each entry states both
    # halves: `{"checked": n, "unjudged": m}`.
    wrong_type, content_checked = [], {}
    for o in outs:
        if not os.path.isfile(o):
            continue
        if os.path.getsize(o) == 0:
            continue          # the `empty` clause below names that better than this one
        suffix = os.path.splitext(o)[1].lower()
        rules = CONTENT_SIGNATURES.get(suffix)
        cell = content_checked.setdefault(suffix, {"checked": 0, "unjudged": 0})
        with open(o, "rb") as fh:
            head = fh.read(16)
        if rules is None:
            # No signature for this suffix — the floor is all this tool can say, and the
            # receipt records that the rest of the question went unanswered.
            cell["unjudged"] += 1
            if head[:1] in JSON_FIRST_BYTES:
                wrong_type.append({"out": os.path.abspath(o),
                                   "expected": "not a JSON error body",
                                   "suffix": suffix, "first_8_bytes": head[:8].hex(),
                                   "bytes": os.path.getsize(o)})
            continue
        cell["checked"] += 1
        if any(head[off:off + len(magic)] != magic for off, magic, _n in rules):
            wrong_type.append({"out": os.path.abspath(o), "expected": rules[0][2],
                               "suffix": suffix, "first_8_bytes": head[:8].hex(),
                               "bytes": os.path.getsize(o)})
    n_checked = sum(c["checked"] for c in content_checked.values())
    n_unjudged = sum(c["unjudged"] for c in content_checked.values())

    ev = {"gate": "FETCH", "andon": "FetchHalt",
          "planned": len(outs), "missing": missing, "empty": empty,
          "extra": extra,
          "wrong_type": wrong_type, "content_checked": content_checked,
          "content_signature_suffixes": sorted(CONTENT_SIGNATURES),
          "root_exempt_matched": exempted,
          # Wave 22 (F-a25a7db9): WHICH rule tolerated each file, and whether that rule can
          # tell which run produced it. An exemption a receipt cannot attribute is the
          # thing the correction block above is about.
          "root_exempt_matched_by": exempted_by,
          "root_exempt_patterns": [rx.pattern for _l, _b, rx in exempt_rules],
          "root_exempt_rules": [{"rule": label, "run_bound": bound,
                                 "pattern": rx.pattern}
                                for label, bound, rx in exempt_rules],
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
            dict(ev, clause="downloaded_population_is_not_the_planned_one"))
    if wrong_type:
        raise FetchHalt(
            f"{len(wrong_type)} of the {len(outs)} planned file(s) on disk are not the "
            f"content type the plan asked for: "
            + "; ".join(f"{os.path.basename(w['out'])} begins {w['first_8_bytes']!r} "
                        f"({w['bytes']} bytes, expected {w['expected']})"
                        for w in wrong_type[:5])
            + ". curl runs --fail-with-body, so an HTTP error body lands at the -o path and "
              "satisfies `present and non-empty`. A measurement taken from this directory "
              "would be a measurement of a generation that was never retrieved",
            dict(ev, clause="downloaded_body_is_not_the_planned_type"))
    ev["verdict"] = (f"{len(outs)} planned file(s), all present and non-empty, "
                     f"{n_checked} of them content-signature checked"
                     + (f", {n_unjudged} unjudged beyond the JSON floor "
                        f"({sorted(k for k, c in content_checked.items() if c['unjudged'])})"
                        if n_unjudged else "")
                     + f", and no "
                     f"unplanned file in {len(ev['swept_directories'])} swept directory(s)"
                     + (f"; {len(exempted)} derived artifact(s) were tolerated by name: "
                        + "; ".join(
                            f"{os.path.basename(x['path'])} "
                            + ("(this run's own)" if x["run_bound"] else
                               "(an UN-TOKENED name: the rule cannot say which run "
                               "produced it)")
                            for x in exempted_by)
                        if exempted else ""))
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
    # ---- ANDON, wave 22 (F-7e45e62b), bounded where `--run` is READ: above the join into
    # the run root, above the paste into the video tap's filename, above the first
    # `os.makedirs`. `--run` was joined into `base` (`os.path.join(a.root, a.run)`) AND
    # pasted into `f"{run}_{i:05d}{ext}"` with no validation anywhere. MEASURED in this
    # worktree with the downloader stubbed to write the planned bytes:
    #   `--run=sub/dir --root=runs` -> exit 0 and `FETCH_RUN_OK {"run": "sub/dir",
    #   "dir": "runs\\sub/dir", "by_node": {"302": 1, "114": 1}, "video": [],
    #   "gate_FETCH": "2 planned file(s), all present and non-empty, ... and no unplanned
    #   file in 3 swept directory(s)"}`
    # while the video was written to `runs/sub/dir/sub/dir_00000.mp4`. `vids` is computed as
    # `dirname(abspath(o)) == abspath(base)`, so the nested path DROPS OUT of the reported
    # population, and `verify_downloads`' root sweep lists `base` itself, so the file is not
    # called a stray either: a tool reporting a population that is not the population on
    # disk, under its own success sentinel. Measured on `plan` alone, `--run=../../escaped`
    # sends the frames to `outputs/escaped/lossless/` and the video to `escaped_00000.mp4`
    # in the PROCESS CWD, outside the run root entirely; `..\..\win` the same.
    single_path_segment(a.run, "--run", FetchHalt,
                        extra={"root": os.path.abspath(a.root),
                               "pasted_into": ["<root>/<run>/ (the run directory)",
                                               "<run>_<index><ext> (the video tap)"]})
    node_dir = parse_node_map(a.node_map)
    video_nodes = parse_video_nodes(a.video_nodes)

    # ONE reader, both fetchers (wave 22, F-2380aca9): the bare `json.load(fh)["results"]`
    # this replaces reached the operator as a stdlib traceback at exit 1 with
    # `"evidence": null`, in the module whose own `__main__` comment tells wrappers to key
    # on the FETCH_RUN_HALT sentinel.
    results = read_results_dump(a.dump, flag="--dump")

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
    # The LABELLED rules (wave 22, F-a25a7db9), so the receipt records which exemption
    # tolerated what and whether that rule can name the run it is about.
    landed = verify_downloads(jobs, directories=mapped, root=base,
                              root_exempt=derived_root_artifact_rules(a.run))

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
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `FETCH_RUN_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "FETCH_RUN")
