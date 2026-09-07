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

TOOL_VERSION = "W37.1"
DEFAULT_BASE_URL = "https://cloud.comfy.org"
DEFAULT_API_KEY_ENV = "COMFY_CLOUD_API_KEY"
DEFAULT_WAIT_TIMEOUT_S = 900
DEFAULT_WAIT_INTERVAL_S = 5


class SubmitGate(RouteGate):
    """Gate SUBMIT — refusals at the irreversible spend boundary."""

    gate = "SUBMIT"


class CeilingBudget(RouteGate):
    """Gate CEILING_BUDGET — next submission would exceed ceiling.submissions / per_arm."""

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


def live_submission_count(ledger, *, arm=None):
    """Count spends that actually left the rig (exclude dry_run rows).

    Wave 37, F-fcc2d66d: when `arm` is given, count only rows whose `arm` matches so
    ceiling.per_arm can bound one arm without inventing a second ledger.
    """
    n = 0
    for row in ledger.get("submissions") or []:
        if not isinstance(row, dict) or row.get("dry_run"):
            continue
        if arm is not None and row.get("arm") != arm:
            continue
        n += 1
    return n


def per_arm_map(budget):
    """Return ceiling.per_arm when it is a non-empty mapping of arm -> positive int."""
    ceiling = budget.get("ceiling") if isinstance(budget, dict) else None
    if not isinstance(ceiling, dict):
        return None
    raw = ceiling.get("per_arm")
    if not isinstance(raw, dict) or not raw:
        return None
    return raw


def gate_ceiling_budget(budget, ledger, arm=None):
    """Refuse when the next live submission would exceed ceiling.submissions / per_arm.

    Wave 37, F-fcc2d66d: total submissions stay the outer bound; when ceiling.per_arm is
    present the caller must name `--arm` and that arm's live count is checked too.
    """
    ceiling = int(budget["submissions"])
    spent = live_submission_count(ledger)
    remaining = ceiling - spent
    arms = per_arm_map(budget)
    ev = {"gate": "CEILING_BUDGET", "andon": "CeilingBudget",
          "ceiling_submissions": ceiling, "submissions_spent": spent,
          "remaining_before": remaining, "ledger": ledger.get("path"),
          "seeds": budget["path"], "arm": arm,
          "per_arm": dict(arms) if arms else None}
    if arms is not None and arm is None:
        raise CeilingBudget(
            f"ceiling.per_arm is declared ({sorted(arms)}) and --arm was not given. "
            f"Without an arm this tool cannot tell which per-arm bound the next spend "
            f"counts against; pass --arm=<id> (one of {sorted(arms)})",
            dict(ev, clause="arm_required_when_per_arm_present",
                 known_arms=sorted(arms)))
    if arms is not None and arm not in arms:
        raise CeilingBudget(
            f"--arm={arm!r} is not a key of ceiling.per_arm ({sorted(arms)}). "
            f"A spend against an unnamed arm cannot be held to the per-arm bound",
            dict(ev, clause="arm_not_in_per_arm", known_arms=sorted(arms),
                 supplied_arm=arm))
    if remaining < 1:
        raise CeilingBudget(
            f"ceiling.submissions is {ceiling} and the ledger at {ledger.get('path')!r} "
            f"already records {spent} live submission(s); the next spend would exceed the "
            f"bound. Spent credits have no compensator",
            dict(ev, clause="ceiling_exhausted"))
    if arms is not None:
        arm_ceiling = arms[arm]
        if (not isinstance(arm_ceiling, int) or isinstance(arm_ceiling, bool)
                or arm_ceiling < 1):
            raise CeilingBudget(
                f"ceiling.per_arm[{arm!r}] is {arm_ceiling!r} "
                f"({type(arm_ceiling).__name__}); a per-arm bound must be a positive int",
                dict(ev, clause="per_arm_ceiling_not_a_positive_int",
                     arm_ceiling=arm_ceiling))
        arm_spent = live_submission_count(ledger, arm=arm)
        arm_remaining = arm_ceiling - arm_spent
        ev["arm_ceiling"] = arm_ceiling
        ev["arm_submissions_spent"] = arm_spent
        ev["arm_remaining_before"] = arm_remaining
        if arm_remaining < 1:
            raise CeilingBudget(
                f"ceiling.per_arm[{arm!r}] is {arm_ceiling} and the ledger already "
                f"records {arm_spent} live submission(s) for that arm; the next spend "
                f"would exceed the per-arm bound (total remaining {remaining}). Spent "
                f"credits have no compensator",
                dict(ev, clause="per_arm_ceiling_exhausted"))
        ev["clause"] = "ceiling_allows"
        ev["verdict"] = (
            f"{spent} of {ceiling} submission(s) spent ({remaining} remain); "
            f"arm {arm!r}: {arm_spent} of {arm_ceiling} ({arm_remaining} remain)")
        return ev
    ev["clause"] = "ceiling_allows"
    ev["verdict"] = (
        f"{spent} of {ceiling} submission(s) spent; {remaining} remain before this one")
    return ev


def ledger_report(budget, ledger, *, arm=None):
    """Read-only ceiling / remaining view for the operator-facing ledger command."""
    arms = per_arm_map(budget)
    spent = live_submission_count(ledger)
    ceiling = int(budget["submissions"])
    report = {
        "ledger": ledger.get("path"),
        "seeds": budget.get("path"),
        "missing_ledger": bool(ledger.get("missing")),
        "ceiling_submissions": ceiling,
        "submissions_spent": spent,
        "remaining": ceiling - spent,
        "per_arm": None,
        "arm": arm,
    }
    if arms:
        per = {}
        for name, bound in arms.items():
            n = live_submission_count(ledger, arm=name)
            per[name] = {"ceiling": bound, "spent": n,
                         "remaining": (bound - n) if isinstance(bound, int) else None}
        report["per_arm"] = per
        if arm is not None and arm in per:
            report["arm_view"] = per[arm]
    # Re-use the gate for the same evidence shape; dry view never raises on exhausted
    # when we only want the numbers — call gate only when remaining allows, else copy.
    try:
        ev = gate_ceiling_budget(budget, ledger, arm=arm)
        report["ceiling_gate"] = {"clause": ev.get("clause"), "verdict": ev.get("verdict")}
    except CeilingBudget as exc:
        report["ceiling_gate"] = {
            "clause": (exc.evidence or {}).get("clause"),
            "verdict": str(exc),
            "exhausted": True,
        }
    return report


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


def _curl_get_json(url, *, api_key):
    """GET JSON via curl.exe — same egress style as POST; no Python networking."""
    cmd = [
        "curl.exe", "-sS", "-L", "--fail-with-body",
        "-X", "GET", url,
        "-H", f"X-API-Key: {api_key}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SubmitGate(
            f"Comfy Cloud GET {url!r} failed (curl exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '')[:500]}",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "cloud_history_get_failed", "url": url,
             "curl_exit": proc.returncode,
             "stderr": (proc.stderr or "")[:500],
             "stdout": (proc.stdout or "")[:500]})
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SubmitGate(
            f"Comfy Cloud GET returned non-JSON ({exc}): {(proc.stdout or '')[:300]}",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "cloud_history_unreadable", "url": url,
             "stdout": (proc.stdout or "")[:500]}) from exc


def history_entry_complete(entry):
    """True when a /api/history/{prompt_id} entry looks finished."""
    if not isinstance(entry, dict):
        return False
    status = entry.get("status")
    if isinstance(status, dict):
        if status.get("completed") is True:
            return True
        if str(status.get("status_str") or "").lower() in ("success", "error", "failed"):
            return True
    if entry.get("outputs"):
        return True
    return False


def poll_history(prompt_id, *, base_url, api_key, timeout_s, interval_s):
    """Bounded poll of /api/history/{prompt_id} via curl.exe (wave 37, F-0fc24d24)."""
    import time

    url = base_url.rstrip("/") + f"/api/history/{prompt_id}"
    deadline = time.monotonic() + max(1, int(timeout_s))
    interval = max(1, int(interval_s))
    polls = 0
    last = None
    while True:
        polls += 1
        last = _curl_get_json(url, api_key=api_key)
        entry = None
        if isinstance(last, dict):
            entry = last.get(prompt_id) if prompt_id in last else last
        if history_entry_complete(entry):
            return {"prompt_id": prompt_id, "url": url, "polls": polls,
                    "completed": True, "history": last,
                    "verdict": f"history complete after {polls} poll(s)"}
        if time.monotonic() >= deadline:
            raise SubmitGate(
                f"--wait: /api/history/{prompt_id} did not complete within "
                f"{timeout_s}s ({polls} poll(s)). The spend already left the rig; "
                f"re-poll by hand or fetch once a dump exists. No automatic retry "
                f"beyond this bound",
                {"gate": "SUBMIT", "andon": "SubmitGate",
                 "clause": "wait_exceeded_the_time_bound",
                 "prompt_id": prompt_id, "url": url, "polls": polls,
                 "timeout_s": timeout_s, "interval_s": interval})
        time.sleep(interval)


def default_spend_receipt_path(record_path, ledger_path, prompt_id):
    """Sibling spend receipt beside --record when given, else beside the ledger."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(prompt_id))[:80]
    if record_path:
        stem, _ = os.path.splitext(os.path.abspath(record_path))
        return f"{stem}-spend-{safe}.json"
    parent = os.path.dirname(os.path.abspath(ledger_path)) or "."
    return os.path.join(parent, f"spend-{safe}.json")


def write_spend_receipt(path, receipt):
    """Write the post-credit spend receipt (prompt_id + dump hint) to disk."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, ensure_ascii=False)
    return os.path.abspath(path)


def merge_spend_into_record(record_path, spend_block):
    """Merge `spend` onto the builder payload record (wave 37, F-b64e4ff5)."""
    path = os.path.abspath(record_path)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SubmitGate(
            f"--write-record cannot read --record {record_path!r} "
            f"({type(exc).__name__}: {exc})",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "write_record_unreadable", "path": path,
             "error": type(exc).__name__}) from exc
    if not isinstance(doc, dict):
        raise SubmitGate(
            f"--write-record: --record {record_path!r} is a {type(doc).__name__}, "
            f"not an object that can carry a spend/ key",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "write_record_not_a_mapping", "path": path,
             "read_as": type(doc).__name__})
    doc = dict(doc)
    doc["spend"] = dict(spend_block)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    return path


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


def cmd_ledger(argv):
    """Read-only ledger / remaining view — never POSTs, never appends (F-39aabdbf)."""
    ap = argparse.ArgumentParser(
        prog="build_submit_payload.py ledger",
        description=(
            "Show spend-ledger counts against ceiling.submissions / per_arm. "
            "Read-only: never POSTs and never appends."))
    ap.add_argument("--seeds", required=True,
                    help="committed seed registration that declares ceiling.*")
    ap.add_argument("--ledger", default=None,
                    help="spend ledger JSON (default: <seeds-stem>-spend-ledger.json)")
    ap.add_argument("--arm", default=None,
                    help="optional arm id when ceiling.per_arm is declared")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.seeds):
        raise SubmitGate(
            f"--seeds {a.seeds!r} is not a file",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "input_missing", "flag": "--seeds",
             "path": os.path.abspath(a.seeds)})
    budget = read_seed_registration_budget(a.seeds, flag="--seeds")
    ledger_path = os.path.abspath(a.ledger or default_ledger_path(a.seeds))
    ledger = load_ledger(ledger_path)
    report = ledger_report(budget, ledger, arm=a.arm)
    print("SUBMIT_LEDGER_OK")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Wave 37, F-39aabdbf: read-only ledger subcommand (never POST / never append).
    if argv[:1] == ["ledger"]:
        return cmd_ledger(argv[1:])

    ap = argparse.ArgumentParser(
        description=(
            "Submit an admitted API graph to Comfy Cloud after re-arming Gates ROUTE/S/L "
            "and counting the spend against ceiling.submissions / per_arm. The irreversible "
            "step lives here — not in a session MCP call outside the tree. "
            "Subcommand: `ledger` shows remaining budget without spending."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ROUTE: the sanctioned spend path — admission digest match, in-process "
            "re-arm of verify+Gate S/L, ceiling.submissions (+ per_arm) ledger, then "
            "curl POST; optional --wait polls /api/history/{prompt_id}.\n"
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
                    help="committed seed registration; also supplies ceiling.submissions "
                         "/ ceiling.per_arm")
    ap.add_argument("--record", default=None,
                    help="builder payload record for route_facts (attribution / "
                         "carries_no_sampler); also the target for --write-record")
    ap.add_argument("--ledger", default=None,
                    help="spend ledger JSON (default: <seeds-stem>-spend-ledger.json "
                         "beside --seeds)")
    ap.add_argument("--arm", default=None,
                    help="arm id counted against ceiling.per_arm when that map is "
                         "present (wave 37, F-fcc2d66d); required then, recorded on "
                         "every live ledger row")
    ap.add_argument("--dry-run", action="store_true",
                    help="arm every gate and print the receipt; do NOT POST and do NOT "
                         "append a live ledger row / spend receipt")
    ap.add_argument("--wait", action="store_true",
                    help="after a live POST, poll /api/history/{prompt_id} via curl.exe "
                         "until complete or --wait-timeout (wave 37, F-0fc24d24). "
                         "Default off so dry-run/CI stay offline")
    ap.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT_S,
                    help=f"seconds to poll under --wait (default: {DEFAULT_WAIT_TIMEOUT_S})")
    ap.add_argument("--wait-interval", type=int, default=DEFAULT_WAIT_INTERVAL_S,
                    help=f"seconds between history polls (default: {DEFAULT_WAIT_INTERVAL_S})")
    ap.add_argument("--write-record", action="store_true",
                    help="merge prompt_id / dump hint into --record under spend/ "
                         "(wave 37, F-b64e4ff5). A sibling spend receipt is always "
                         "written on a live success; dry-run touches neither")
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
    if a.write_record and not a.record:
        raise SubmitGate(
            "--write-record needs --record (the builder payload record to merge "
            "spend/ onto)",
            {"gate": "SUBMIT", "andon": "SubmitGate",
             "clause": "write_record_needs_record", "flag": "--write-record"})

    api = _as_api_graph(RG.load_graph(a.api), path=a.api)
    saved = _as_saved_graph(RG.load_graph(a.saved), path=a.saved)

    admission, admission_ev = gate_admission_matches(
        a.admission, a.api, a.saved, api)
    budget = read_seed_registration_budget(a.seeds, flag="--seeds")
    ledger = load_ledger(ledger_path)
    ceiling_ev = gate_ceiling_budget(budget, ledger, arm=a.arm)
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
        "arm": a.arm,
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
            "arm": a.arm,
            "wait": bool(a.wait),
            "write_record": bool(a.write_record),
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
    ceiling_ev = gate_ceiling_budget(budget, ledger, arm=a.arm)

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

    wait_ev = None
    dump_hint = (
        f"{a.base_url.rstrip('/')}/api/history/{prompt_id} "
        f"(save the JSON dump, then fetch_run --dump=<that> --record=...)")
    if a.wait:
        wait_ev = poll_history(
            prompt_id, base_url=a.base_url, api_key=api_key,
            timeout_s=a.wait_timeout, interval_s=a.wait_interval)
        dump_hint = (
            f"history complete; dump from {wait_ev['url']} then "
            f"fetch_run/--record against that dump")

    entry = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_id": prompt_id,
        "api_sha256": _file_sha256(a.api),
        "payload_sha256": receipt["payload_sha256"],
        "admission": os.path.abspath(a.admission),
        "seeds": os.path.abspath(a.seeds),
        "seed": a.seed,
        "arm": a.arm,
        "base_url": a.base_url.rstrip("/"),
        "dump_hint": dump_hint,
    }
    append_ledger(ledger_path, entry, dry_run=False)
    receipt["prompt_id"] = prompt_id
    receipt["dump_hint"] = dump_hint
    receipt["gates"]["CEILING_BUDGET"] = ceiling_ev
    if wait_ev is not None:
        receipt["wait"] = {
            "polls": wait_ev["polls"], "url": wait_ev["url"],
            "verdict": wait_ev["verdict"]}

    spend_block = {
        "prompt_id": prompt_id,
        "utc": entry["utc"],
        "arm": a.arm,
        "payload_sha256": receipt["payload_sha256"],
        "ledger": ledger_path,
        "dump_hint": dump_hint,
        "base_url": a.base_url.rstrip("/"),
        "tool": "submit_comfy_cloud",
        "tool_version": TOOL_VERSION,
    }
    receipt_path = write_spend_receipt(
        default_spend_receipt_path(a.record, ledger_path, prompt_id), spend_block)
    receipt["spend_receipt"] = receipt_path
    if a.write_record:
        merge_spend_into_record(a.record, spend_block)
        receipt["record_spend_merged"] = os.path.abspath(a.record)

    print("SUBMIT_COMFY_CLOUD_OK")
    print(json.dumps({
        "path": ledger_path,
        "dry_run": False,
        "prompt_id": prompt_id,
        "arm": a.arm,
        "payload_sha256": receipt["payload_sha256"],
        "ceiling": ceiling_ev["verdict"],
        "admission": admission_ev["verdict"],
        "gate_ROUTE": gates["ROUTE"].get("verdict"),
        "gate_S": gates["S"].get("verdict"),
        "dump_hint": dump_hint,
        "spend_receipt": receipt_path,
        "wait": receipt.get("wait"),
        "record_spend_merged": receipt.get("record_spend_merged"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "SUBMIT_COMFY_CLOUD")
