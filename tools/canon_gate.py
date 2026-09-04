#!/usr/bin/env python
"""canon_gate — resolve, cover, spend-check. Nothing here submits.

    python tools/canon_gate.py resolve --subject PERFORMER
    python tools/canon_gate.py --roots tests/fixtures/canon check --subject PROBE \
        --prompt "..."
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
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateCanon, GateFailure)


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
        # A REFUSAL, raised (wave 10, F-55e6d1cb). This used to `print("UNKNOWN …")` and
        # `return 2` — the code this CLI's own convention reserves for "a gate refused" —
        # with no `CANON_GATE_HALT` line and no evidence, so a wrapper obeying the module's
        # documented rule read it as one of argparse's usage errors, which also exit 2.
        raise GateCanon(
            f"unknown subject {args.subject!r}: it is in no canon census this invocation "
            f"can see, so nothing can be resolved for it",
            {"gate": "CANON", "andon": "GateCanon", "clause": "unknown_subject",
             "subject": args.subject, "census": args.census, "roots": args.roots})
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
    # ⚠ There used to be an `except GateCanon` here that printed `CANON_REFUSE …` plus the
    # evidence to STDERR and returned 2. `raise SystemExit(2)` is then re-raised by the
    # `except SystemExit: raise` in the `__main__` block below, so the
    # `print("CANON_GATE_HALT " + …)` line that block exists to emit NEVER RAN on this
    # tool's PRIMARY refusal. Measured 2026-09-04: `canon_gate.py --roots … spend
    # --subject PROBE --prompt hello` printed `CANON_REFUSE [CANON] unknown subject 'PROBE'`
    # on stderr and exited 2 with no `CANON_GATE_HALT` anywhere, while `--census <missing
    # file>` — a plain FileNotFoundError, not a gate at all — DID print the sentinel and
    # exit 1. The convention was inverted: crashes got the machine-readable line, gate
    # refusals did not, and this module's own comment tells callers to key on the sentinel.
    #
    # The gate now reaches the `__main__` handler, which prints `CANON_GATE_HALT` with the
    # evidence dict on STDOUT — where the other twelve tools put it — and picks 2 for any
    # ArmatureError. In-process callers get the typed `GateCanon` instead of a bare 2.
    code = args.func(args)
    if code == 0:
        # The SUCCESS half of the exit convention (wave 10): `<PREFIX>_OK `, the same
        # prefix the `__main__` block prints on a halt. This tool printed no success
        # sentinel at all.
        print("CANON_GATE_OK " + json.dumps({"cmd": args.cmd, "code": code}))
    return code


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `CANON_GATE_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("CANON_GATE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
