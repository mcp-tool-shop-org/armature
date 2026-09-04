#!/usr/bin/env python
"""canon_gate — resolve, cover, spend-check. Nothing here submits.

    python tools/canon_gate.py resolve --subject PERFORMER
    python tools/canon_gate.py check --subject PROBE --prompt "..." --roots tests/fixtures/canon
    python tools/canon_gate.py coverage --canon tests/fixtures/canon/probe.surfaces.json
    python tools/canon_gate.py spend --subject PERFORMER --no-canon --prompt "..."

The spend subcommand is the same helper the payload builders call. It
creates nothing.

--------------------------------------------------------------------------------
The spend helper the builders import, and the two defects it closes

`canon_spend` / `canon_line` below are what every `build_*payload` tool calls, and they
exist because of two measurements taken on 2026-09-03:

* **Every builder discarded `gate_write`'s return.** `require_canon` builds an evidence
  dict carrying the verdict (ARMED / UNGATED), the clause, and an `announcement` string
  that `armature_core.canon` says exists so the census escape announces itself. No builder
  printed it and no builder put a CANON entry in its record. Measured:
  `build_r2v_payload.py --subject=BLACKGUARD --no-canon` printed BUILD_R2V_OK with four
  gate lines and no canon line, and the written record's gates were exactly
  `CEILING_one_paid_node, L_hosted, ROUTE, S_build_time` — a payload record submitted as
  the provenance for a paid generation with no way to tell whether canon was armed or
  escaped. The same helper through this CLI DID print the announcement, so the escape was
  loud from the diagnostic and silent from the tool that authors the spend.
* **`--canon-prompt` was gated instead of the shipped text.** Measured against a census row
  carrying a surfaces file: without the flag the build was refused; with the flag set to a
  covering string the identical invocation printed BUILD_R2V_OK and the record's
  `payload["model.prompt"]` was the very text the gate had just refused. The builders now
  gate the string they ship, and a `--canon-prompt` that disagrees with it raises rather
  than being silently ignored.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import canon as C  # noqa: E402
from armature_core import canon_census  # noqa: E402
from armature_core.errors import GateCanon  # noqa: E402


def gate_canon_ships_what_it_gated(canon_prompt, shipped):
    """Gate CANON · ANDON — the text handed to the router IS the text being sent.

    **The andon is on the direction the invariant does not bound.** `require_canon`
    checks a string against a ratified statement; nothing in it can know whether that
    string is the one the payload carries. So the router passes, the record records a
    different prompt, and every other gate is green. The realistic path is not malice: an
    operator hits a canon refusal, pastes the ratified phrases into `--canon-prompt` to
    get moving, and a paid generation goes out on text no canon governs.
    """
    if canon_prompt is not None and canon_prompt != shipped:
        raise GateCanon(
            "--canon-prompt is not the text this payload ships. The router would have "
            "checked one string while the graph carried another, and every other gate "
            "would still be green. Either fix the shipped prompt or drop the flag",
            {"clause": "gated_text_is_not_shipped_text",
             "canon_prompt": canon_prompt, "shipped": shipped})


def canon_spend(subject, shipped_prompt, *, no_canon=False, out_dir=None,
                canon_prompt=None, census=None, search_roots=None):
    """The call every spend builder makes before mkdir. Returns the evidence dict.

    The SHIPPED prompt is the one gated. `canon_prompt` is only checked for agreement
    with it, so the flag can no longer change what the router examines.
    """
    ev = C.gate_write(subject, shipped_prompt, no_canon=no_canon, out_dir=out_dir,
                      census=census, search_roots=search_roots)
    gate_canon_ships_what_it_gated(canon_prompt, shipped_prompt)
    return ev


def canon_line(ev):
    """The one-line canon verdict a spend builder prints beside its other gate lines.

    `announcement` is `armature_core.canon`'s own string for the census escape, and it is
    used verbatim where present so the escape announces itself in the words the module
    wrote for it.
    """
    if ev.get("announcement"):
        return ev["announcement"]
    return f"[canon] {ev.get('verdict')}: {ev.get('subject')}"


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
    ev = canon_spend(
        args.subject,
        args.prompt,
        no_canon=args.no_canon,
        out_dir=args.out,
        canon_prompt=args.canon_prompt,
        census=_census(args),
        search_roots=_roots(args),
    )
    print(canon_line(ev))
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
    # There used to be a fallback here — `if args.cmd == "spend" and args.prompt is None:
    # args.prompt = args.canon_prompt` — describing a behaviour argparse forbids: the spend
    # subparser declares --prompt with required=True, so the branch could never run.
    # Measured: `canon_gate.py spend --subject BLACKGUARD --no-canon --canon-prompt x`
    # exits with argparse's "the following arguments are required: --prompt". The branch is
    # deleted rather than the requirement relaxed: --prompt is the string this CLI checks,
    # and `--canon-prompt` is now compared against it by `canon_spend` instead of quietly
    # standing in for it.
    try:
        return args.func(args)
    except GateCanon as err:
        print(f"CANON_REFUSE {err}", file=sys.stderr)
        if err.evidence:
            print(json.dumps(err.evidence, indent=2, default=str), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
