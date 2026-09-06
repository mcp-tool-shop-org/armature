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
inside the FETCH_T2V_OK line — and compared to nothing. No threshold, no raise. The
zero-length-frame check three lines below it raises, so the file already knew the
difference between reporting and gating; a shuffled clip would have been written, FETCH_T2V_OK
printed, and the ratio near 1.0 noticed only if a human opened the JSON.

**The choice made, and the one deliberately not made.** A numeric floor was refused: no
calibrated floor for this ratio has been measured on any provider, and inventing one here
would be a pass condition picked while looking at the results it judges. What the order
rule claims is DIRECTIONAL — if the array order is the temporal order, differencing it
gives a SMALLER number than differencing a hash-sorted permutation of the same frames. So
the boundary is the sign of that comparison and nothing else: `ratio > 1` is the claim,
`ratio <= 1` contradicts it, and an undefined ratio (all frames identical) decides
nothing. Anything but the first raises `FETCH_ORDER_UNVOUCHED` and FETCH_T2V_OK is not
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
# WAVE 25, F-af838b99: this file's `__main__` block named `GateFailure` and
# `ArmatureError` to pick its own exit code. That choice belongs to
# `armature_core.parts.halt_outcome` now and no other line here names either,
# so the import is dropped rather than left dangling.
from fetch_run import (  # noqa: E402,F401
    EXITS_NAME, FetchHalt, PNG_SIGNATURE, gate_downloader_shell, verify_downloads)
from fetch_run import download as fetch_download  # noqa: E402
# The ONE dump reader (wave 22, F-2380aca9). This module carried the identical two lines and
# RE-MEASURED identically on `e8263a3`: a non-JSON dump -> FETCH_T2V_HALT `JSONDecodeError`
# `"evidence": null`; a dump with no `results` -> `KeyError: 'results'`, same shape.
from fetch_run import read_results_dump  # noqa: E402

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
    """Where each returned file lands. Array position IS the frame index.

    ⚠ **An empty `results` is refused here** (wave 12, F-4421d98f) — the sibling's clause,
    one wording, both planners. `download` computed
    `os.path.join(os.path.dirname(jobs[0]["out"]), "_urls.json")` with no clause on `jobs`
    being non-empty, and `main` created `--out` and wrote `download_manifest.json` before
    calling it. Measured with `{"results": []}`: `IndexError: list index out of range`, and
    `run/` left on disk holding the manifest — a half-built run directory a later session
    reads as a run that happened, under a halt line carrying `error: "IndexError"` and
    `evidence: null`, where every FetchHalt in this file carries a gate id and a
    measurement.
    """
    if not results:
        raise FetchHalt(
            "the dump carries no results at all. A job that has returned nothing is not a "
            "run to fetch, and continuing would leave a directory a later session reads as "
            "a run that happened",
            {"gate": "FETCH", "andon": "FetchHalt", "clause": "empty_results",
             "n_results": 0, "out": os.path.abspath(out)})
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
                {"gate": "FETCH", "andon": "FetchHalt", "clause": "unexpected_source_node",
                 "unexpected_node": nid,
                 "known": [LOSSLESS_NODE, VIDEO_NODE]})
    return jobs


def download(jobs, out=None):
    """The sibling's downloader, called — ONE implementation, not a second shape.

    Two defects lived in the original three lines. A url read straight out of an
    operator-pasted dump sat in OPTION position with no terminator, so an entry beginning
    with a dash was read by curl as a flag — and both `-o` and `-K` (read a config file)
    are reachable that way. And the manifest path was interpolated into a single-quoted
    PowerShell literal, so an apostrophe anywhere in `--out` closed the literal and the
    remainder parsed as separate statements. Both are fixed in `fetch_run.download`, whose
    command string is a CONSTANT and which is what runs now.

    ⚠ **The third defect, and why this function no longer builds a command at all**
    (wave 14, F-a3ba416b). This fetcher's ONLY downloader gate read the pwsh PROCESS code,
    under a `foreach ($x in $j) { curl.exe ... }` loop — and that code reflects only the
    LAST native command in the loop. MEASURED ON THIS RIG 2026-09-04:

        pwsh -NoProfile -Command '$j = @(1,2,3); foreach ($x in $j)
            { cmd.exe /c "exit $(if($x -eq 1){22}else{0})" }'      -> process exit 0
        ...the same loop with the failure on the LAST element      -> process exit 1

    So `if proc.returncode != 0` could not fire on any download failure except one in the
    final job. `fetch_run.download`'s own docstring asserted the opposite as a measured
    fact, and that claim is corrected in place there; it is also the reason this fetcher was
    left without the per-job `download_exits.json` record the sibling gained.

    The backstop was only partial, and this paragraph used to record that and stop there.
    `verify_downloads` PNG-signature-checked every planned `.png`, so a mid-loop FRAME
    failure that lands a `--fail-with-body` HTTP error body still raised — but the VIDEO
    job's `donor<ext>` carried a suffix the clause had no signature for, so a failed donor
    download that lands a 35-byte error body read as present, non-empty, no stray, and
    FETCH_T2V_OK was printed. **Naming a defect in prose is how it is RECORDED, not how it
    is closed** (wave 18, F-0124c714): `fetch_run.CONTENT_SIGNATURES` now carries `.mp4`,
    `.m4v`, `.mov`, `.webm`, `.mkv` and `.webp` beside `.png`, and every planned output
    whatever its suffix is refused if its first bytes parse as the start of a JSON document.
    A suffix with no signature row is now COUNTED as unjudged in the receipt's own
    `content_checked[<suffix>]` rather than being absent from every key — the sentence
    "counted, not judged" was not true of the old receipt either.

    `record_urls=False`: the exit record lands in the run directory as the sibling's does,
    but WITHOUT the urls. `_urls.json` is deleted on every path here precisely because it
    holds signed download links (wave 12, F-8ccedf71), and a per-job record naming the same
    urls would reopen exactly what that fix closed. `out` identifies a job uniquely, so the
    gate reads everything it needs.
    """
    for j in jobs:
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
    manifest = [{"url": j["url"], "out": os.path.abspath(j["out"])} for j in jobs]
    manifest_dir = os.path.dirname(os.path.abspath(jobs[0]["out"]))
    # The exit record belongs in the run ROOT, beside the frame directories rather than
    # inside one: `verify_downloads`' root sweep judges only VIDEO_SUFFIXES there, and a
    # mapped frame directory refuses every file the plan did not name. `out` is the
    # `--out` `plan` was given; the fallback keeps an in-process caller working.
    run_root = os.path.abspath(out) if out else manifest_dir
    tmp = os.path.join(manifest_dir, "_urls.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    # ---- wave 12, F-8ccedf71. `os.remove(tmp)` sat BELOW the refusal, so it ran only on
    # the success path: a halt on a non-zero downloader left `_urls.json` — every result URL
    # the operator pasted, signed download links included — in the run directory, where this
    # tool's own root sweep does not call it a stray (`root_suffixes` is VIDEO_SUFFIXES only)
    # and nothing later removes it. The sibling's `urls.json` is DURABLE by design and is
    # kept deliberately; this file's `_urls.json` is a temporary whose deletion is the
    # intended behaviour on every path, including one where `subprocess.run` itself raises.
    try:
        proc, exits = fetch_download(
            tmp, exits_path=os.path.join(run_root, EXITS_NAME), record_urls=False)
    finally:
        if os.path.isfile(tmp):
            os.remove(tmp)
    return proc, exits


def gate_order_evidence(ev):
    """Gate ORDER · ANDON — the discriminator must point the way the order rule claims.

    The boundary is the SIGN of the comparison and not a magnitude: see the module
    docstring for why no floor is invented here. Raises `FETCH_ORDER_UNVOUCHED` rather
    than letting `main` print FETCH_T2V_OK over an order this tool cannot vouch for.
    """
    array_mean = ev["results_array_order"]["mean"]
    hash_mean = ev["hash_sorted_order"]["mean"]
    ratio = (hash_mean / array_mean) if array_mean else None
    g = {"gate": "ORDER", "andon": "FetchHalt", "clause": "order_unvouched",
         "array_order_mean_diff": array_mean,
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
            f"this run’s temporal order has no evidence behind it and FETCH_T2V_OK is "
            f"not printed. The frames and the evidence file are left on disk",
            g)
    g["verdict"] = (f"the results-array order differences {ratio:.3g}x tighter than a "
                    f"hash-sorted permutation of the same frames")
    return g


def order_evidence(out):
    """The 7.6x discriminator, recomputed on this run's own frames.

    Wave 12, F-bd2ace34. The sort key used to be `lambda p: _hash_name(p, out)`, and
    `_hash_name` OPENED and parsed `download_manifest.json` on every call — several hundred
    parses of one file on the 81-frame clip this tool is written for. Worse, it ended
    `return os.path.basename(path)` when no row matched: the local frames are named
    `00000.png` onward, so a lookup that failed for EVERY frame made the hash-sorted
    permutation byte-identical to the array order, ratio exactly 1.0, and Gate ORDER raised
    FETCH_ORDER_UNVOUCHED. It failed closed — but the halt named an unvouched ORDER when the
    real fault was an unreadable manifest, and the two are different repairs. The map is read
    once, and a frame the manifest does not name is its own refusal.
    """
    from armature_core import donor_gate as DG

    d = os.path.join(out, "lossless")
    array_order = DG.frame_paths(d)                       # 00000.png ... , i.e. as returned
    names = cloud_names(out)
    unnamed = [p for p in array_order if os.path.abspath(p) not in names]
    if unnamed:
        raise FetchHalt(
            f"download_manifest.json names no cloud filename for {len(unnamed)} of the "
            f"{len(array_order)} frame(s) on disk: "
            f"{[os.path.basename(p) for p in unnamed[:5]]}. The permutation this gate "
            f"differences against would fall back to the LOCAL names, which are already the "
            f"array order — the two arms would be the same list, the ratio exactly 1.0, and "
            f"the halt would name an unvouched ORDER when the manifest is what cannot be "
            f"read",
            {"gate": "FETCH", "andon": "FetchHalt",
             "clause": "frame_absent_from_manifest", "unnamed": unnamed,
             "n_frames": len(array_order), "n_named": len(names),
             "manifest": os.path.join(os.path.abspath(out), "download_manifest.json")})
    by_hash = sorted(array_order, key=lambda p: names[os.path.abspath(p)])
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


def cloud_names(out):
    """`{abspath: cloud_name}` read ONCE from this run's own download manifest."""
    with open(os.path.join(out, "download_manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    return {os.path.abspath(j["out"]): j["cloud_name"] for j in m["files"]}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Retrieve one t2v generation's frames and donor video into a run directory, "
            "prove that what landed is what the dump planned, and vouch for the frames' "
            "temporal ORDER before printing a receipt. Runs AFTER the credits are spent."),
        epilog=(
            "ROUTE: the t2v retrieval. The cloud's filenames are content hashes, so sorting "
            "them shuffles the clip - the results ARRAY's order is the temporal order, and "
            "Gate ORDER measures that claim against a hash-sorted permutation of the same "
            "frames rather than asserting it. WHAT A REFUSAL COSTS: the generation is "
            "already billed; a refusal costs only the fetch, and the frames plus the "
            "evidence file are left on disk so the measurement that fired it can be read "
            "without re-fetching. It never retries for you."))
    ap.add_argument("--dump", required=True,
                    help="the results JSON the cloud returned for this prompt; every "
                         "download is planned from it and from nothing else")
    ap.add_argument("--out", required=True,
                    help="the run directory. Frames land in <out>/lossless/, the donor "
                         "video beside them, and the four JSON records this tool writes in "
                         "the root. A re-fetch into a used --out is refused by the plan-"
                         "to-disk clause rather than blended with the earlier run")
    ap.add_argument("--prompt-id", default=None,
                    help="the cloud prompt id, recorded in download_manifest.json so a run "
                         "directory can be tied back to the submission that produced it")
    a = ap.parse_args(argv)

    results = read_results_dump(a.dump, flag="--dump", exc=FetchHalt)
    try:
        jobs = plan(results, a.out)
    except FetchHalt as exc:
        # The operator's own input, named in the receipt: the halt is about THIS dump.
        exc.evidence["dump"] = os.path.abspath(a.dump)
        raise
    # ---- Gate FETCH · ANDON, wave 25 (F-edf3a80b). The sibling's ONE implementation,
    # imported like `download` itself rather than spelled again, armed above the first
    # `os.makedirs` so a rig with no downloader leaves no run directory behind.
    gate_downloader_shell()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "download_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"tool": "fetch_t2v_run", "tool_version": TOOL_VERSION,
                   "prompt_id": a.prompt_id, "n_results": len(results),
                   "order_rule": ("the results array's order is the temporal order; the "
                                  "cloud filenames are content hashes and sorting them "
                                  "shuffles the clip"),
                   "files": [{k: v for k, v in j.items() if k != "url"} for j in jobs]},
                  fh, indent=2)
    # ---- wave 22, F-894dffb2. Both return values were DISCARDED. `fetch_run.download`
    # returns `(proc, {"gate": "FETCH", "clause": "downloader_job_exits", "record": ...,
    # "jobs": n, "verdict": ...})` and the sibling prints it as `gate_EXITS` in FETCH_RUN_OK
    # (`fetch_run.py`), while FETCH_T2V_OK carried `gate_ORDER` and `gate_FETCH` and no
    # `gate_EXITS`, and nothing wrote the receipt into any of the four JSON records this
    # tool leaves in the run root. Stated as the bound: the gate itself still RAISES inside
    # `download`, so this was a missing RECEIPT rather than a missing check — but the two
    # fetchers printed different evidence for the same shared andon, and this module's own
    # docstring explains at length that the pwsh process code CANNOT see a failed curl in a
    # `-Parallel` runspace and that the per-job record is therefore the only evidence the
    # gate decides on. A later session reading this run's receipts could not tell a gate
    # that passed from a gate that was never run.
    _proc, gate_exits = download(jobs, out=a.out)
    # The receipt SURVIVES THE PROCESS. The manifest is written above rather than here so it
    # outlives a halt inside `download`; the gates block is added once the gate has actually
    # run, which is the only moment it can be recorded honestly.
    manifest_path = os.path.join(a.out, "download_manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest_doc = json.load(fh)
    manifest_doc["gates"] = {"EXITS": gate_exits}
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest_doc, fh, indent=2)

    # Gate FETCH · ANDON, carried from `fetch_run.verify_downloads` rather than written a
    # second time. This tool had NO plan-to-disk check: the frame population came from
    # `os.listdir`, nothing compared it to `plan()` in either direction, and the VIDEO job
    # was never checked at all. Measured 2026-09-04 with `download` stubbed: a 4-frame dump
    # fetched into an --out whose lossless/ held one stale 00009.png printed FETCH_T2V_OK
    # {"frames": 5} with the stale frame in the sha256 manifest and inside both arms of
    # Gate ORDER; a dump whose frame 3 and video never landed printed FETCH_T2V_OK
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

    # ---- wave 22, F-c03a23c5. A `zero_length_frames` clause stood here and COULD NOT FIRE.
    # `verify_downloads(jobs, directories=[...], root=a.out)` above already raises when any
    # planned output has `os.path.getsize(o) == 0`, across the frame jobs AND the video job;
    # `manifest` is built from a strict subset of the same planned frames
    # (`j["array_index"] is not None`), read from the same paths, and nothing between the
    # two lines writes to them. RE-MEASURED on `e8263a3` by calling
    # `fetch_run.verify_downloads` directly on a single planned zero-byte
    # `lossless/00000.png`: it raised `FetchHalt` with clause
    # `downloaded_population_is_not_the_planned_one` before any manifest existed. By the
    # time the deleted branch ran, every entry it inspected had already been shown non-zero
    # by a raise-or-return above it, so no input could reach it.
    #
    # It read as a live zero-length safety check sitting between the andon and Gate ORDER,
    # and a later session could have deleted the REAL one believing the coverage lived here.
    # The tree's own rule decides: a check that cannot fail is not a check. THE COVERAGE
    # LIVES IN `verify_downloads` ABOVE — its `empty` list, its clause
    # `downloaded_population_is_not_the_planned_one`, over a WIDER population than this
    # branch ever saw (the video job included).

    # The evidence file is already on disk above, so a halt here leaves the measurement
    # that fired it behind rather than making the next session re-fetch to see it.
    order = gate_order_evidence(ev)

        # The SUCCESS half of the exit convention (wave 10). `<PREFIX>_OK ` uses the SAME
    # prefix this file's `__main__` block prints on a halt, so one AST read of that block
    # derives both directions of the census. The tree spelled this four ways before.
    print("FETCH_T2V_OK " + json.dumps({
        "frames": len(frames), "out": a.out,
        "array_order_mean_diff": order["array_order_mean_diff"],
        "hash_sorted_mean_diff": order["hash_sorted_mean_diff"],
        "ratio": order["ratio"], "gate_ORDER": order["verdict"],
        "gate_FETCH": landed["verdict"],
        # wave 22, F-894dffb2: the same gate key the sibling fetcher prints, off the same
        # shared andon, so a reader can reconcile the two tools' receipts against each other.
        "gate_EXITS": gate_exits["verdict"]}))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `FETCH_T2V_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "FETCH_T2V")
