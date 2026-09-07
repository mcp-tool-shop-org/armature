#!/usr/bin/env python
"""submit_comfy_cloud — the ONE in-repo tool that may spend Comfy Cloud credits.

    <venv-python> tools\\submit_comfy_cloud.py \\
        --api=<api.json> --saved=<saved.json> --admission=<admission.json> \\
        --seeds=specs/E09-A3-seeds.json [--record=<payload-record.json>] \\
        [--ledger=<path>] --dry-run

Placement (b) from docs/grok-consult-1-brief.md. Build-time gates alone are not enough:
a hand-edited or stale graph can still be submitted outside every Gate ROUTE/S/L this
repo already enforces. This tool refuses unless the admission record's digests match the
files on disk, re-runs verify + Gate S (+ Gate L via verify) inside THIS process, counts
the spend ledger against `ceiling.submissions`, and only then POSTs via curl.exe.

`--dry-run` arms every gate and prints what would be submitted; it never POSTs and never
appends a live ledger entry. Tests and CI must use `--dry-run` (or the refuse-without-
admission path). Live egress shells to curl.exe the same way fetch_run does — no Python
networking library is imported here (SECURITY.md).

Compensator: ledger append / cloud job. Owner: the executor session. Spent credits have
no compensator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import route_gates as RG  # noqa: E402
from armature_core.route_gates import RouteGate  # noqa: E402
from build_assembly_payload import (  # noqa: E402
    canonical_payload_digest, read_seed_registration, read_seed_registration_budget)
from gate_saved_graph import (  # noqa: E402
    _as_api_graph, _as_saved_graph, route_facts)

TOOL_VERSION = "W34.1"
DEFAULT_BASE_URL = "https://cloud.comfy.org"
DEFAULT_API_KEY_ENV = "COMFY_CLOUD_API_KEY"


class SubmitGate(RouteGate):
    """Gate SUBMIT — refusals at the irreversible spend boundary."""

    gate = "SUBMIT"


class CeilingBudget(RouteGate):
    """Gate CEILING_BUDGET — next submission would exceed ceiling.submissions."""

    gate = "CEILING_BUDGET"


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_ledger_path(seeds_path):
    """Beside the seeds file: <stem>-spend-ledger.json."""
    abs_seeds = os.path.abspath(seeds_path)
    stem, _ = os.path.splitext(os.path.basename(abs_seeds))
    return os.path.join(os.path.dirname(abs_seeds), f"{stem}-spend-ledger.json")


def load_ledger(path):
    """Return the ledger document; missing file is an empty submissions list."""
    if not os.path.isfile(path):
        return {"submissions": [], "path": os.path.abspath(path), "missing": True}
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise CeilingBudget(
            f"--ledger {path!r} cannot be read as JSON ({type(exc).__name__}: {exc}). "
            f"A ledger this tool cannot parse is not a count it can hold a spend to",
            {"gate": "CEILING_BUDGET", "andon": "CeilingBudget",
             "clause": "ledger_unreadable", "path": os.path.abspath(path),
             "error": type(exc).__name__}) from exc
    if not isinstance(doc, dict):
        raise CeilingBudget(
            f"--ledger {path!r} is a {type(doc).__name__}, not an object with "
            f"`submissions`",
            {"gate": "CEILING_BUDGET", "andon": "CeilingBudget",
             "clause": "ledger_not_a_mapping", "path": os.path.abspath(path),
             "read_as": type(doc).__name__})
    subs = doc.get("submissions")
    if subs is None:
        doc = dict(doc, submissions=[])
        subs = doc["submissions"]
    if not isinstance(subs, list):
        raise CeilingBudget(
            f"--ledger {path!r} declares `submissions` as a {type(subs).__name__}, "
            f"not a list",
            {"gate": "CEILING_BUDGET", "andon": "CeilingBudget",
             "clause": "ledger_submissions_not_a_list",
             "path": os.path.abspath(path), "read_as": type(subs).__name__})
    doc["path"] = os.path.abspath(path)
    doc["missing"] = False
    return doc


def live_submission_count(ledger):
    """Count spends that actually left the rig (exclude dry_run rows)."""
    n = 0
    for row in ledger.get("submissions") or []:
        if isinstance(row, dict) and row.get("dry_run"):
            continue
        n += 1
    return n


def gate_ceiling_budget(budget, ledger):
    """Refuse when the next live submission would exceed ceiling.submissions."""
    ceiling = int(budget["submissions"])
    spent = live_submission_count(ledger)
    remaining = ceiling - spent
    ev = {"gate": "CEILING_BUDGET", "andon": "CeilingBudget",
          "ceiling_submissions": ceiling, "submissions_spent": spent,
          "remaining_before": remaining, "ledger": ledger.get("path"),
          "seeds": budget["path"]}
    if remaining < 1:
        raise CeilingBudget(
            f"ceiling.submissions is {ceiling} and the ledger at {ledger.get('path')!r} "
            f"already records {spent} live submission(s); the next spend would exceed the "
            f"bound. Spent credits have no compensator",
            dict(ev, clause="ceiling_exhausted"))
    ev["clause"] = "ceiling_allows"
    ev["verdict"] = (
        f"{spent} of {ceiling} submission(s) spent; {remaining} remain before this one")
    return ev


def gate_admission_matches(admission_path, api_path, saved_path, api_graph):
    """Refuse unless the admission record's digests match the files about to run."""
    path = os.path.abspath(admission_path)
    try:
        with open(path, encoding="utf-8") as fh:
            admission = json.load(fh)
    except OSError as exc:
        raise SubmitGate(
            f"--admission {admission_path!r} cannot be opened ({type(exc).__name__}: "
            f"{exc}). Without a matching admission record this tool refuses rather than "
            f"spend",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "admission_missing", "path": path,
             "error": type(exc).__name__}) from exc
    except json.JSONDecodeError as exc:
        raise SubmitGate(
            f"--admission {admission_path!r} is not readable JSON ({exc})",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "admission_unreadable", "path": path, "error": str(exc)}) from exc
    if not isinstance(admission, dict):
        raise SubmitGate(
            f"--admission {admission_path!r} is a {type(admission).__name__}, not an "
            f"admission object",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "admission_not_a_mapping", "path": path,
             "read_as": type(admission).__name__})

    api_sha = _file_sha256(api_path)
    saved_sha = _file_sha256(saved_path)
    api_block = admission.get("api_file") or {}
    saved_block = admission.get("saved_file") or {}
    declared_api = api_block.get("sha256") if isinstance(api_block, dict) else None
    declared_saved = saved_block.get("sha256") if isinstance(saved_block, dict) else None
    ev = {"gate": "SUBMIT", "andon": "SubmitGate", "admission": path,
          "api_sha256": api_sha, "saved_sha256": saved_sha,
          "admission_api_sha256": declared_api,
          "admission_saved_sha256": declared_saved}

    if not declared_api or not declared_saved:
        raise SubmitGate(
            f"--admission {admission_path!r} carries no api_file.sha256 / saved_file.sha256 "
            f"pair; refuse-without-admission rather than spend on an unverified file",
            dict(ev, clause="admission_missing_digests",
                 api_keys=sorted(api_block) if isinstance(api_block, dict) else None,
                 saved_keys=sorted(saved_block) if isinstance(saved_block, dict) else None))
    if declared_api != api_sha or declared_saved != saved_sha:
        raise SubmitGate(
            f"--admission digests do not match the files on disk: api "
            f"{declared_api!r} vs {api_sha!r}; saved {declared_saved!r} vs {saved_sha!r}. "
            f"A stale or hand-edited graph is refused here, not submitted",
            dict(ev, clause="admission_digest_mismatch"))

    payload = canonical_payload_digest(api_graph)
    facts = admission.get("route_facts") or {}
    declared_payload = facts.get("payload_sha256") if isinstance(facts, dict) else None
    if declared_payload and declared_payload != payload:
        raise SubmitGate(
            f"--admission route_facts.payload_sha256 {declared_payload!r} is not the "
            f"canonical digest of --api ({payload!r})",
            dict(ev, clause="admission_payload_digest_mismatch",
                 payload_sha256=payload,
                 admission_payload_sha256=declared_payload))
    ev["clause"] = "admission_matches"
    ev["payload_sha256"] = payload
    ev["verdict"] = "admission api_file/saved_file digests match; payload digest tied"
    return admission, ev


def rearm_gates(saved, api, seeds_path, record_path=None, hosted_tier=None, frame=None):
    """Re-run verify + Gate S (+ L via verify) inside the submitting process."""
    registered = read_seed_registration(seeds_path, flag="--seeds")
    facts = (route_facts(record_path, api) if record_path else
             {"record": None, "n_verify_receipts": 0, "carries_no_sampler": False,
              "attribution": [], "payload_sha256": None, "api_payload_sha256": None,
              "source": "no --record; route_gates.verify defaults"})
    gate_route = RG.verify(
        saved, frame=frame, hosted_tier=hosted_tier,
        carries_no_sampler=facts["carries_no_sampler"],
        attribution=facts["attribution"])
    gate_s = RG.gate_s_registration(
        saved, registered, carries_no_sampler=facts["carries_no_sampler"])
    return {"ROUTE": gate_route, "S": gate_s, "route_facts": facts}


def append_ledger(path, entry, *, dry_run):
    """Append one submission row. Dry-run rows are marked and ignored by the counter."""
    doc = load_ledger(path)
    if doc.get("missing"):
        doc = {"submissions": [], "tool": "submit_comfy_cloud",
               "tool_version": TOOL_VERSION}
    row = dict(entry)
    if dry_run:
        row["dry_run"] = True
    doc.setdefault("submissions", []).append(row)
    doc["tool"] = "submit_comfy_cloud"
    doc["tool_version"] = TOOL_VERSION
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    return doc


def post_prompt(api_graph, *, base_url, api_key, body_path):
    """POST API graph to Comfy Cloud /api/prompt via curl.exe. Returns parsed JSON."""
    payload = {"prompt": api_graph}
    with open(body_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)
    url = base_url.rstrip("/") + "/api/prompt"
    # curl.exe egress — same shape as fetch_run. Key rides the header for this process
    # only; nothing stores it. SECURITY.md: no Python networking library here.
    cmd = [
        "curl.exe", "-sS", "-L", "--fail-with-body",
        "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-H", f"X-API-Key: {api_key}",
        "--data-binary", f"@{body_path}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SubmitGate(
            f"Comfy Cloud POST {url!r} failed (curl exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '')[:500]}",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "cloud_post_failed", "url": url,
             "curl_exit": proc.returncode,
             "stderr": (proc.stderr or "")[:500],
             "stdout": (proc.stdout or "")[:500]})
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SubmitGate(
            f"Comfy Cloud POST returned non-JSON ({exc}): {(proc.stdout or '')[:300]}",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "cloud_post_unreadable", "url": url,
             "stdout": (proc.stdout or "")[:500]}) from exc


def parse_frame(text):
    if text is None:
        return None
    raw = [v.strip() for v in text.split(",")]
    parts, bad = [], []
    for v in raw:
        try:
            parts.append(int(v))
        except (TypeError, ValueError):
            bad.append(v)
    if len(raw) != 3 or len(parts) != 3:
        raise SubmitGate(
            f"--frame={text!r} is not width,height,length",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "frame_not_three_integers", "supplied": text,
             "parts": raw, "unreadable": bad})
    return tuple(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Submit an admitted API graph to Comfy Cloud after re-arming Gates ROUTE/S/L "
            "and counting the spend against ceiling.submissions. The irreversible step "
            "lives here — not in a session MCP call outside the tree."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ROUTE: the sanctioned spend path — admission digest match, in-process "
            "re-arm of verify+Gate S/L, ceiling.submissions ledger, then curl POST.\n"
            "\n"
            "WHAT A REFUSAL COSTS: no credit is spent and no live ledger row is written. "
            "Use --dry-run to rehearse every gate without POSTing."))
    ap.add_argument("--api", required=True,
                    help="API-format graph this repo built (the prompt body)")
    ap.add_argument("--saved", required=True,
                    help="SAVE-format graph the cloud converted; re-gated here")
    ap.add_argument("--admission", required=True,
                    help="gate_saved_graph admission JSON whose digests must match "
                         "--api/--saved")
    ap.add_argument("--seeds", required=True,
                    help="committed seed registration; also supplies ceiling.submissions")
    ap.add_argument("--record", default=None,
                    help="builder payload record for route_facts (attribution / "
                         "carries_no_sampler)")
    ap.add_argument("--ledger", default=None,
                    help="spend ledger JSON (default: <seeds-stem>-spend-ledger.json "
                         "beside --seeds)")
    ap.add_argument("--dry-run", action="store_true",
                    help="arm every gate and print the receipt; do NOT POST and do NOT "
                         "append a live ledger row")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"Comfy Cloud base URL (default: {DEFAULT_BASE_URL})")
    ap.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV,
                    help=f"env var holding the X-API-Key (default: {DEFAULT_API_KEY_ENV})")
    ap.add_argument("--hosted-tier", default=None,
                    help="hosted tier name for Gate L when the graph has no pixels")
    ap.add_argument("--frame", default=None,
                    help="width,height,length for Gate L when the latent is not readable "
                         "(--frame=832,480,81)")
    ap.add_argument("--seed", type=int, default=None,
                    help="recorded on the ledger row; optional")
    a = ap.parse_args(argv)

    ledger_path = os.path.abspath(a.ledger or default_ledger_path(a.seeds))
    frame = parse_frame(a.frame)

    for flag, path in (("--api", a.api), ("--saved", a.saved),
                       ("--admission", a.admission), ("--seeds", a.seeds)):
        if not os.path.isfile(path):
            raise SubmitGate(
                f"{flag} {path!r} is not a file",
                {"gate": "SUBMIT", "andon": "SubmitGate",
                 "clause": "input_missing", "flag": flag,
                 "path": os.path.abspath(path)})

    api = _as_api_graph(RG.load_graph(a.api), path=a.api)
    saved = _as_saved_graph(RG.load_graph(a.saved), path=a.saved)

    admission, admission_ev = gate_admission_matches(
        a.admission, a.api, a.saved, api)
    budget = read_seed_registration_budget(a.seeds, flag="--seeds")
    ledger = load_ledger(ledger_path)
    ceiling_ev = gate_ceiling_budget(budget, ledger)
    gates = rearm_gates(
        saved, api, a.seeds, record_path=a.record,
        hosted_tier=a.hosted_tier, frame=frame)

    receipt = {
        "tool": "submit_comfy_cloud", "tool_version": TOOL_VERSION,
        "dry_run": bool(a.dry_run),
        "api": os.path.abspath(a.api),
        "saved": os.path.abspath(a.saved),
        "admission": os.path.abspath(a.admission),
        "seeds": os.path.abspath(a.seeds),
        "ledger": ledger_path,
        "gates": {
            "ADMISSION": admission_ev,
            "CEILING_BUDGET": ceiling_ev,
            "ROUTE": gates["ROUTE"],
            "S": gates["S"],
        },
        "payload_sha256": canonical_payload_digest(api),
        "experiment": admission.get("experiment"),
        "stage": admission.get("stage"),
    }

    if a.dry_run:
        print("SUBMIT_COMFY_CLOUD_OK")
        print(json.dumps({
            "path": ledger_path,
            "dry_run": True,
            "would_post": a.base_url.rstrip("/") + "/api/prompt",
            "payload_sha256": receipt["payload_sha256"],
            "ceiling": ceiling_ev["verdict"],
            "admission": admission_ev["verdict"],
            "gate_ROUTE": gates["ROUTE"].get("verdict"),
            "gate_S": gates["S"].get("verdict"),
            "prompt_id": None,
        }, indent=2, ensure_ascii=False))
        return 0

    api_key = os.environ.get(a.api_key_env) or ""
    if not api_key.strip():
        raise SubmitGate(
            f"env {a.api_key_env!r} is empty; a live submit needs the Comfy Cloud API key. "
            f"Pass --dry-run to rehearse without spending",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "api_key_missing", "api_key_env": a.api_key_env})

    # Count again immediately before POST — refuse if another spend landed.
    ledger = load_ledger(ledger_path)
    ceiling_ev = gate_ceiling_budget(budget, ledger)

    with tempfile.TemporaryDirectory(prefix="armature-submit-") as tmp:
        body_path = os.path.join(tmp, "prompt.json")
        response = post_prompt(
            api, base_url=a.base_url, api_key=api_key, body_path=body_path)

    prompt_id = response.get("prompt_id") or response.get("id")
    if not prompt_id:
        raise SubmitGate(
            f"Comfy Cloud response carried no prompt_id: {sorted(response)[:20]}",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "cloud_response_no_prompt_id",
             "keys": sorted(map(str, response))[:40]})

    entry = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_id": prompt_id,
        "api_sha256": _file_sha256(a.api),
        "payload_sha256": receipt["payload_sha256"],
        "admission": os.path.abspath(a.admission),
        "seeds": os.path.abspath(a.seeds),
        "seed": a.seed,
        "base_url": a.base_url.rstrip("/"),
    }
    append_ledger(ledger_path, entry, dry_run=False)
    receipt["prompt_id"] = prompt_id
    receipt["gates"]["CEILING_BUDGET"] = ceiling_ev

    print("SUBMIT_COMFY_CLOUD_OK")
    print(json.dumps({
        "path": ledger_path,
        "dry_run": False,
        "prompt_id": prompt_id,
        "payload_sha256": receipt["payload_sha256"],
        "ceiling": ceiling_ev["verdict"],
        "admission": admission_ev["verdict"],
        "gate_ROUTE": gates["ROUTE"].get("verdict"),
        "gate_S": gates["S"].get("verdict"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "SUBMIT_COMFY_CLOUD")
