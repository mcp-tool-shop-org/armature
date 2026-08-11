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

    python tools/armature_index.py build|verify|q|claims
"""
import os
import sys

import record_index
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


def repo():
    if REPO is None:
        raise RootNotFound(
            "no record corpus found - neither %s nor the working directory %s "
            "contains CLAUDE.md + docs/experiments"
            % (os.path.dirname(HERE), os.getcwd()))
    return REPO


def main(argv=None):
    return _cli.run_contract(lambda a: _cli.main(BINDING, a), argv,
                             db_env="ARMATURE_INDEX_DB")


if __name__ == "__main__":
    sys.exit(main())
