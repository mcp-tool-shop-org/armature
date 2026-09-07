#!/usr/bin/env python
"""build_routes_payload — owned spend-path dispatcher and route catalog CLI.

    python tools/build_routes_payload.py list
    python tools/build_routes_payload.py show E10
    python tools/build_routes_payload.py dispatch E10 -- --out=... --uploads=...
    python tools/build_routes_payload.py admit -- --saved=... --api=... --seeds=... --out=...
    python tools/build_routes_payload.py fetch -- --dump=... --run=... --route=i2v

Wave 35, F-dfbc5d79 / F-fb6e1577. The nine builders + gate_saved_graph + two fetchers
had no owned umbrella that lists or forwards them. This CLI reads specs/routes.json and
either prints the catalog or execs the named tool. It spends nothing itself; forwarded
builders still refuse dry / gated paths.

OUT-OF-DOMAIN: armature_core/cli.py is the installed package front door — wire later.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "W35.1"
ROUTES_CATALOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "specs", "routes.json")


class RoutesGate(GateFailure):
    """Catalog / dispatcher refusal — nothing is forwarded."""

    gate = "ROUTES"


def load_catalog(path=None):
    """Read specs/routes.json through clauses rather than bare json.load."""
    path = path or ROUTES_CATALOG
    ev = {"gate": "ROUTES", "andon": "RoutesGate", "path": os.path.abspath(path)}
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        raise RoutesGate(
            f"routes catalog {path!r} cannot be opened ({exc.__class__.__name__}: {exc})",
            dict(ev, clause="catalog_missing", error=exc.__class__.__name__)) from exc
    except json.JSONDecodeError as exc:
        raise RoutesGate(
            f"routes catalog {path!r} is not readable JSON ({exc})",
            dict(ev, clause="catalog_unreadable", error=str(exc))) from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("routes"), list):
        raise RoutesGate(
            f"routes catalog {path!r} carries no `routes` list",
            dict(ev, clause="catalog_no_routes",
                 keys=sorted(doc) if isinstance(doc, dict) else None))
    return doc


def find_route(doc, route_id):
    """Return the route object for `route_id`, or raise."""
    rid = str(route_id)
    for row in doc["routes"]:
        if isinstance(row, dict) and row.get("id") == rid:
            return row
    known = sorted(r.get("id") for r in doc["routes"] if isinstance(r, dict))
    raise RoutesGate(
        f"route {rid!r} is not in {ROUTES_CATALOG}. Known: {known}",
        {"gate": "ROUTES", "andon": "RoutesGate", "clause": "unknown_route",
         "route": rid, "known": known})


def cmd_list(args):
    doc = load_catalog(args.catalog)
    rows = []
    for r in doc["routes"]:
        if not isinstance(r, dict):
            continue
        if args.live_only and r.get("status") != "live":
            continue
        rows.append({
            "id": r.get("id"),
            "status": r.get("status"),
            "builder": r.get("builder"),
            "seeds": r.get("seeds"),
            "fetch_profile": r.get("fetch_profile"),
            "admission": r.get("admission"),
        })
    print("ROUTES_LIST_OK " + json.dumps({
        "catalog": os.path.abspath(args.catalog or ROUTES_CATALOG),
        "n": len(rows), "routes": rows}, ensure_ascii=False))
    return 0


def cmd_show(args):
    doc = load_catalog(args.catalog)
    row = find_route(doc, args.route)
    print("ROUTES_SHOW_OK " + json.dumps(row, ensure_ascii=False))
    return 0


def _forward(script_rel, forward_argv, *, dry_run=False):
    """Exec an owned tools/*.py with the operator's remaining argv."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    script = script_rel
    if script.startswith("tools/") or script.startswith("tools\\"):
        script = script.split("/", 1)[-1].split("\\", 1)[-1]
    path = os.path.join(tools_dir, script)
    if not os.path.isfile(path):
        raise RoutesGate(
            f"builder {script_rel!r} is not a file under tools/ ({path})",
            {"gate": "ROUTES", "andon": "RoutesGate",
             "clause": "builder_missing", "builder": script_rel,
             "path": path})
    cmd = [sys.executable, path, *list(forward_argv or [])]
    if dry_run:
        print("ROUTES_DISPATCH_DRY_RUN " + json.dumps({
            "cmd": cmd, "builder": script_rel}, ensure_ascii=False))
        return 0
    # Forward exit code; child prints its own OK/HALT sentinel.
    proc = subprocess.run(cmd, check=False)
    return int(proc.returncode)


def cmd_dispatch(args):
    doc = load_catalog(args.catalog)
    row = find_route(doc, args.route)
    if row.get("status") == "narrative-only":
        raise RoutesGate(
            f"route {args.route!r} is narrative-only (no owned builder). See "
            f"docs/experiments/; do not invent a spend path from the catalog row",
            {"gate": "ROUTES", "andon": "RoutesGate",
             "clause": "route_narrative_only", "route": args.route,
             "notes": row.get("notes")})
    builder = row.get("builder")
    if not builder:
        raise RoutesGate(
            f"route {args.route!r} declares no builder",
            {"gate": "ROUTES", "andon": "RoutesGate",
             "clause": "route_has_no_builder", "route": args.route})
    forward = list(args.forward or [])
    # Seed default when the catalog names one and the operator did not.
    seeds = row.get("seeds")
    if seeds and not any(a.startswith("--seeds") for a in forward):
        # animate / i2v / camera_i2v / lora_arm take --seeds-registry; t2v / r2v take --seeds.
        base = os.path.basename(builder)
        if base in ("build_animate_payload.py", "build_i2v_payload.py",
                    "build_camera_i2v_payload.py", "build_lora_arm_payload.py"):
            flag = "--seeds-registry"
        else:
            flag = "--seeds"
        forward = [f"{flag}={seeds}", *forward]
    print("ROUTES_DISPATCH " + json.dumps({
        "route": args.route, "builder": builder, "seeds": seeds,
        "admission": row.get("admission"), "fetch_profile": row.get("fetch_profile"),
        "forward": forward}, ensure_ascii=False))
    return _forward(builder, forward, dry_run=args.dry_run)


def cmd_admit(args):
    return _forward("gate_saved_graph.py", args.forward, dry_run=args.dry_run)


def cmd_fetch(args):
    # Default to fetch_run; operator may pass --route=t2v which refuses toward fetch_t2v.
    tool = "fetch_run.py"
    forward = list(args.forward or [])
    if any(a == "--t2v" or a.startswith("--t2v=") for a in forward):
        tool = "fetch_t2v_run.py"
        forward = [a for a in forward if a != "--t2v" and not a.startswith("--t2v=")]
    return _forward(tool, forward, dry_run=args.dry_run)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "List and dispatch the owned spend-path CLIs from specs/routes.json. "
            "Submits nothing; forwarded tools keep their own gates and dry-run paths."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ROUTE: the owned umbrella for builders / admit / fetch (wave 35).\n"
            "\n"
            "WHAT A REFUSAL COSTS: nothing but your time; this tool never posts."))
    ap.add_argument("--catalog", default=None,
                    help=f"routes catalog JSON (default: {ROUTES_CATALOG})")
    sub = ap.add_subparsers(dest="cmd", required=True,
                            metavar="{list,show,dispatch,admit,fetch}")

    p = sub.add_parser("list", help="print every catalog row")
    p.add_argument("--live-only", action="store_true",
                   help="omit narrative-only and tool rows")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="print one catalog row")
    p.add_argument("route", help="route id (E08, E10, admit, …)")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser(
        "dispatch",
        help="forward remaining argv to the route's builder",
        description="Forward to the builder named by the catalog row. "
                    "Pass --dry-run before the route id.")
    p.add_argument("--dry-run", action="store_true",
                   help="print the command that would run; do not exec")
    p.add_argument("route", help="live experiment id (E08, E10, E11, …)")
    p.add_argument("forward", nargs=argparse.REMAINDER,
                   help="args after -- passed to the builder")
    p.set_defaults(func=cmd_dispatch)

    p = sub.add_parser("admit", help="forward to gate_saved_graph")
    p.add_argument("--dry-run", action="store_true",
                   help="print the command that would run; do not exec")
    p.add_argument("forward", nargs=argparse.REMAINDER,
                   help="args after -- passed to gate_saved_graph")
    p.set_defaults(func=cmd_admit)

    p = sub.add_parser("fetch", help="forward to fetch_run (or fetch_t2v_run with --t2v)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the command that would run; do not exec")
    p.add_argument("forward", nargs=argparse.REMAINDER,
                   help="args after -- passed to the fetcher")
    p.set_defaults(func=cmd_fetch)

    args = ap.parse_args(argv)
    # Strip a leading bare '--' used as an argv separator.
    if getattr(args, "forward", None) is not None and args.forward[:1] == ["--"]:
        args.forward = args.forward[1:]
    code = args.func(args)
    if code == 0 and args.cmd in ("list", "show"):
        pass
    elif code == 0 and args.cmd in ("dispatch", "admit", "fetch") and args.dry_run:
        print("ROUTES_OK " + json.dumps({"cmd": args.cmd, "dry_run": True,
                                         "tool_version": TOOL_VERSION}))
    elif code == 0:
        print("ROUTES_OK " + json.dumps({"cmd": args.cmd, "tool_version": TOOL_VERSION}))
    return code


if __name__ == "__main__":
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "ROUTES")
