#!/usr/bin/env python
"""canon_gate — resolve, cover, spend-check. Nothing here submits.

    python tools/canon_gate.py resolve --subject PERFORMER
    python tools/canon_gate.py check --subject PROBE --prompt "..." --roots tests/fixtures/canon
    python tools/canon_gate.py coverage --canon tests/fixtures/canon/probe.surfaces.json
    python tools/canon_gate.py spend --subject PERFORMER --no-canon --prompt "..."

The spend subcommand is the same helper the payload builders call. It
creates nothing.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import canon as C  # noqa: E402
from armature_core import canon_census  # noqa: E402
from armature_core.errors import GateCanon  # noqa: E402


def _roots(args):
    if args.roots:
        return args.roots
    return None


def _census(args):
    if not args.census:
        return None
    with open(args.census, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_resolve(args):
    rec = canon_census.row(args.subject, census=_census(args))
    if rec is None:
        print(f"UNKNOWN {args.subject}")
        return 2
    if rec.get("surfaces") is None:
        print(f"IDENTITY_ONLY {args.subject}")
        if rec.get("reason"):
            print(rec["reason"])
        return 0
    doc = C.resolve(args.subject, census=_census(args), search_roots=_roots(args))
    print(f"RESOLVED {args.subject} {doc['_path']}")
    print(json.dumps(C.coverage(doc), indent=2))
    return 0


def cmd_coverage(args):
    doc = C.load(args.canon)
    print(json.dumps(C.coverage(doc), indent=2))
    return 0


def cmd_check(args):
    if args.canon:
        doc = C.load(args.canon)
    else:
        doc = C.resolve(args.subject, census=_census(args), search_roots=_roots(args))
    ev = C.cover(doc, args.prompt)
    print(json.dumps({k: ev[k] for k in ev if k != "prompt"}, indent=2))
    return 0


def cmd_spend(args):
    ev = C.gate_write(
        args.subject,
        args.prompt,
        no_canon=args.no_canon,
        out_dir=args.out,
        census=_census(args),
        search_roots=_roots(args),
    )
    print(json.dumps(ev, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", action="append", default=None)
    ap.add_argument("--census", default=None, help="override census JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("resolve")
    p.add_argument("--subject", required=True)
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("coverage")
    p.add_argument("--canon", required=True)
    p.set_defaults(func=cmd_coverage)

    p = sub.add_parser("check")
    p.add_argument("--subject", default=None)
    p.add_argument("--canon", default=None)
    p.add_argument("--prompt", required=True)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("spend")
    C.add_spend_flags(p)
    p.add_argument("--prompt", dest="prompt", required=True)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_spend)

    args = ap.parse_args(argv)
    # spend flags use --canon-prompt; the spend subcommand uses --prompt.
    if args.cmd == "spend" and args.prompt is None:
        args.prompt = args.canon_prompt
    try:
        return args.func(args)
    except GateCanon as err:
        print(f"CANON_REFUSE {err}", file=sys.stderr)
        if err.evidence:
            print(json.dumps(err.evidence, indent=2, default=str), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
