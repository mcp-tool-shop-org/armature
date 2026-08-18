#!/usr/bin/env python
"""armature_index - armature's binding of the shared record index.

armature is the SECOND repo to adopt these conventions, and its adoption was the
condition the extraction was gated on. What that means concretely: this file is
four lines of wiring, and everything that is true about armature's record lives
in `docs/index/conventions.json` - a full declaration, validated at load, with
no default inherited from facet for anything it does not state.

WHAT THIS REPO'S DECLARATION SAYS THAT FACET'S DOES NOT, all of it measured:

  * TWO ruling-header forms. The closing rulings write `## Ruling N`; the early
    ones (E01, E02-bridge, E02-halt) write `## N. RULING - ...`. Running facet's
    single-pattern parser here left three ruling documents at zero rows and said
    nothing about it.
  * VIDEO artifact kinds. facet's extension map has no `.mp4` or `.mkv`, so its
    parser dropped six artifact mentions here in silence - in the repo whose
    entire product is video.
  * NO profiles, NO prose-file list, NO experiments table, NO phenomenon
    markers. Each declared EMPTY rather than omitted, because "armature has none
    of these" is a statement and a missing key is not.

`arc` stays the document stem. armature carries four E02 ruling documents and
they are four arcs numbering from 1 independently; the `E\\d\\d` prefix lives in
the `experiment` column, where grouping belongs and identity does not.

WHAT THIS BINDING ADDS TO THE SHARED VERB SURFACE. Two verbs, each closing a
hole measured on 2026-08-18, the day six artifact rows were found dangling:

  * `build` CERTIFIES. The shared CLI's `build` calls the builder and returns
    EXIT_OK unconditionally, writing a db and leaving whatever certificate was
    already beside it. `certificate.py` states the invariant it exists to hold -
    that there is no path which writes a db without writing a certificate for it
    - and the shared `build` verb is a path that does. Measured: `build` into an
    empty directory produced `fresh.db` and no `fresh.db.cert.json`. Here
    `build` routes through `certificate.build_and_certify`, so the db and its
    certificate move together, and a build whose own verify failed returns
    EXIT_REFUSED rather than EXIT_OK.
  * `health` ASKS WHETHER THE INDEX IS CURRENT. `certificate.health` already
    computes SERVING / STALE / the three refusals, and no verb reached it. So
    the first thing a session learned about a six-day-old index was `verify`
    failing on dangling pointers - the late symptom, named after the parser
    rather than after the corpus drift that produced it. STALE keeps `serving`
    true and exits OK, because the library rules bounded staleness the normal
    state of a record whose db commits at session boundaries rather than at
    every fold; the three refusals exit 4.

    python tools/armature_index.py build|verify|q|claims|health
"""
import os
import sys

import record_index
from record_index import certificate as _cert
from record_index import cli as _cli

BINDING = record_index.bind(__file__, name="armature",
                            db_rel="docs/index/armature.db",
                            db_env="ARMATURE_INDEX_DB")

globals().update(BINDING.exports())

RootNotFound = record_index.RootNotFound
run_contract = _cli.run_contract

HERE = os.path.dirname(os.path.abspath(__file__))

REPO = BINDING.root
BINDING.set_root_provider(lambda: globals().get("REPO"))

#: The verbs this file implements itself, and the ones it hands to the shared
#: CLI unchanged. Kept as data rather than as an `if` chain because a test pins
#: DELEGATED_VERBS against the shared parser's own choices: a verb added
#: upstream then fails here instead of silently going unoffered.
OWNED_VERBS = ("build", "health")
DELEGATED_VERBS = ("verify", "q", "claims")
VERBS = ("build", "verify", "q", "claims", "health")


def repo():
    if REPO is None:
        raise RootNotFound(
            "no record corpus found - neither %s nor the working directory %s "
            "contains CLAUDE.md + docs/experiments"
            % (os.path.dirname(HERE), os.getcwd()))
    return REPO


def _resolve_db(explicit):
    """The shared CLI's precedence, mirrored for the verbs this file owns: an
    explicit --db wins over the env var, which wins over the record's own
    tracked index. Pinned against the shared implementation by a test."""
    return explicit or os.environ.get(DB_ENV) or BINDING.db_default()      # noqa: F821


def _peek_verb(argv):
    """The first non-flag token. Read before parsing, because which parser runs
    depends on it."""
    for a in argv:
        if not a.startswith("-"):
            return a
    return None


def _print_help():
    print("usage: %s {%s} [term] [--db PATH] [--limit N] [--table T] [--debug]"
          % (_cli.prog_name(), ",".join(VERBS)))
    print("\nthe derived SQLite+FTS5 index over the armature record\n")
    print("verbs:")
    print("  build     rebuild the index AND write its certificate - one verb")
    print("  verify    the four legs, against an index already on disk")
    print("  q TERM    query the index")
    print("  claims    the claims sweep")
    print("  health    SERVING / STALE / the refusal that says why")


def _build_and_certify(db_path):
    doc = _cert.build_and_certify(BINDING, db_path)
    print("\n[certificate] %s" % _cert.cert_path(db_path))
    print("  state            %s" % doc["state"])
    print("  verify exit      %d" % doc["verify_exit_code"])
    print("  db               %d bytes  %s" % (doc["db"]["bytes"],
                                               doc["db"]["sha256"]))
    print("  corpus           %d files  %s" % (doc["corpus"]["files"],
                                               doc["corpus"]["id"]))
    # A build whose own verify refused is not a build that succeeded. The shared
    # verb returned EXIT_OK here and left the reader to notice the transcript.
    return EXIT_OK if doc["verify_exit_code"] == EXIT_OK else EXIT_REFUSED  # noqa: F821


def _health(db_path):
    h = _cert.health(BINDING, db_path)
    print("%-16s %s" % ("state", h["state"]))
    print("%-16s %s" % ("serving", "yes" if h["serving"] else "no"))
    if h.get("why"):
        print("%-16s %s" % ("why", h["why"]))
    if h.get("moved_total"):
        print("%-16s %d file(s) moved since this index was built; first %d:"
              % ("corpus", h["moved_total"], len(h["moved"])))
        for rel in h["moved"]:
            print("    %s" % rel)
        print("%-16s %s build" % ("rebuild with", _cli.prog_name()))
    # STALE SERVES AND EXITS OK. The library rules bounded staleness the normal
    # state of a record whose db commits at session boundaries, and a refusal
    # here would fire on correct work. The three refusals do not serve, and say
    # which one it is.
    return EXIT_OK if h["serving"] else EXIT_REFUSED                       # noqa: F821


def _dispatch(argv):
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = _peek_verb(argv)
    if verb is None:
        _print_help()
        return EXIT_OK if ("-h" in argv or "--help" in argv) else EXIT_USER  # noqa: F821
    if verb not in VERBS:
        # NAMED HERE RATHER THAN DELEGATED. The shared parser's `choices` do not
        # carry this binding's two verbs, so handing it an unknown verb produced
        # an error message that offered four of the five that work.
        return _cli.user_error(
            "invalid choice: %r (choose from %s)"
            % (verb, ", ".join(repr(v) for v in VERBS)),
            "%s --help" % _cli.prog_name())
    if verb not in OWNED_VERBS:
        return _cli.main(BINDING, argv)
    ap = _cli.ContractParser(
        prog=_cli.prog_name(),
        description="the derived SQLite+FTS5 index over the armature record")
    ap.add_argument("verb", choices=OWNED_VERBS)
    ap.add_argument("--db", default=None,
                    help="the index to work against (default %s under the "
                         "record's root, or $%s)" % (DB_REL, DB_ENV))      # noqa: F821
    ap.add_argument("--debug", action="store_true", help=_cli.DEBUG_HELP)
    args = ap.parse_args(argv)
    survivable_stdout()                                                    # noqa: F821
    db_path = _resolve_db(args.db)
    return _build_and_certify(db_path) if args.verb == "build" else _health(db_path)


def main(argv=None):
    return _cli.run_contract(_dispatch, argv, db_env="ARMATURE_INDEX_DB")


if __name__ == "__main__":
    sys.exit(main())
