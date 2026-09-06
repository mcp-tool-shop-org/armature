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
from armature_core.errors import GateCanon  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.


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
        # ---- wave 22, F-a22e9575. The evidence literal named neither the gate nor the
        # andon, so a triage or a wrapper keyed on `evidence["gate"]` at the spend boundary
        # read `None` — on the one andon standing between an operator pasting ratified
        # phrases into `--canon-prompt` and a paid generation going out on text no canon
        # governs. RE-MEASURED on `e8263a3` by calling
        # `gate_canon_ships_what_it_gated('a', 'b')`: GateCanon raised, `exc.evidence` keys
        # exactly ['canon_prompt', 'clause', 'shipped'] while `type(exc).gate` read
        # 'CANON'; the `__main__` block prints that dict verbatim under CANON_GATE_HALT.
        # The tree's law (`tests/test_core_solver_evidence.py`, and `cmd_resolve` twelve
        # lines down in THIS file) is that `ev["gate"]` is the raised class's own `.gate`
        # and `ev["andon"]` its class name. This is the most-reached raise in the file:
        # `canon_spend` calls it for all seven builders that arm Gate CANON.
        raise GateCanon(
            "--canon-prompt is not the text this payload ships. The router would have "
            "checked one string while the graph carried another, and every other gate "
            "would still be green. Either fix the shipped prompt or drop the flag",
            {"gate": "CANON", "andon": "GateCanon",
             "clause": "gated_text_is_not_shipped_text",
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
    ap = argparse.ArgumentParser(
        description=(
            "Gate CANON at the command line: resolve a subject to its canon, measure a "
            "canon's coverage, check a prompt against one, or run the SPEND gate every "
            "payload builder calls before it authors a submission."),
        epilog=(
            "ROUTE: Gate CANON, the check that a prompt about a character is grounded in "
            "that character's canon rather than improvised at the keyboard. `spend` is the "
            "subcommand the builders themselves call - what it refuses here, it refuses "
            "there. WHAT A REFUSAL COSTS: nothing but your time. Read the halt line's "
            "`clause`; a refusal is not worked around by pasting the refused phrases into "
            "--canon-prompt, because the SHIPPED prompt is what is gated."))
    ap.add_argument("--roots", action="append", default=None,
                    help="a canon root directory to search; repeatable. Omitted, this "
                         "tool's own recorded roots are used")
    ap.add_argument("--census", default=None, help="override census JSON")
    sub = ap.add_subparsers(dest="cmd", required=True,
                            metavar="{resolve,coverage,check,spend}")

    p = sub.add_parser(
        "resolve", help="name the canon file(s) a subject resolves to, and say why",
        description="Resolve a subject name to the canon documents that ground it.")
    p.add_argument("--subject", required=True,
                   help="the character whose canon is being resolved")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser(
        "coverage", help="report what a canon file covers, without judging a prompt",
        description="Measure one canon file's coverage of the census terms.")
    p.add_argument("--canon", required=True, help="the canon file to measure")
    p.set_defaults(func=cmd_coverage)

    p = sub.add_parser(
        "check", help="check a prompt against a canon and REPORT; spends nothing",
        description=("Check one prompt against a subject's canon and report the result. "
                     "This is the reporting form; `spend` is the gate."))
    p.add_argument("--subject", default=None,
                   help="the character the prompt is about; omitted, --canon names the "
                        "canon directly")
    p.add_argument("--canon", default=None,
                   help="the canon file to check against, instead of resolving --subject")
    p.add_argument("--prompt", required=True, help="the prompt text to check")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser(
        "spend", help="THE GATE every payload builder calls before authoring a submission",
        description=("Run Gate CANON in its spending form - the same call the payload "
                     "builders make. It refuses a prompt that is not grounded in the "
                     "subject's canon, and it gates the SHIPPED prompt, so a refusal "
                     "cannot be worked around with --canon-prompt."))
    C.add_spend_flags(p)
    p.add_argument("--prompt", dest="prompt", required=True,
                   help="the prompt that will actually be sent; this is what is gated")
    p.add_argument("--out", default=None,
                   help="a directory to write the canon evidence JSON into; omitted, the "
                        "evidence is printed and nothing is written")
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
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `CANON_GATE_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "CANON_GATE")
