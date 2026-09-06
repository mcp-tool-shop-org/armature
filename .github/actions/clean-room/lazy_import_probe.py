"""Call every function-local third-party import of an INSTALLED armature-studio.

ONE TEXT, TWO CALLERS. `.github/actions/clean-room/action.yml` runs this file inside the
wheel room, and so does `verify.ps1`'s leg 3, whose DESCRIPTION says a green local run and a
green CI run are the same claim ABOUT WHAT RAN. It used to be two copies -- a bash heredoc in
the action and a PowerShell here-string in the script -- and no census could see the second
one: `tests/test_ci_workflows.py`'s lazy-import census derives the leg from
`_all_run_scripts()`, which walks `.github/` only. Measured on `e8263a3` in a `git archive`
scratch copy with the three calls replaced by `pass` inside verify.ps1's here-string ALONE:
`tests/test_verify_script.py` + `tests/test_ci_workflows.py` = 256 passed. The classifier
gate one directory over was made a FILE for exactly this reason and its docstring states the
law ("One text, two callers"); the probe two paragraphs away stayed duplicated. It does not
any more.

WHY THE PROBE CALLS FUNCTIONS AT ALL. `armature check` imports each surface module and
`armature modules` prints a table, so no function body runs and no lazy import is ever
reached. Measured in this exact clean room -- armature-studio and numpy only -- `armature
check` printed `all modules resolved` and exited 0 while cv2, matplotlib and PIL were absent
and both the drawing path and Gate DONOR raised ModuleNotFoundError on first call. The leg
was green on precisely the wheel defect it exists to catch.

WHY THE PRINTED LINE IS BUILT AND NOT WRITTEN, AND WHY NO FUNCTION IS NAMED IN PROSE HERE.
This file used to end with a `print` whose literal spelled out all three function names, and
`tests/test_ci_workflows.py::test_the_clean_room_leg_reaches_every_lazily_imported_dependency`
decides "the leg reaches this lazy dependency" with `any(fn in script for fn in fns)` over a
source with only `#` comment lines dropped. So all three names sat in the text whether or not
the calls happened, and the guard was satisfied by the probe's own ANNOUNCEMENT. Measured on
`e8263a3` with the three call sites replaced by `pass`: `tests/test_ci_workflows.py` = 216
passed, and the guard passed on its own (`-k clean_room_leg_reaches` -> 1 passed, 215
deselected). That is this repository's "placeholder shaped like evidence" rule broken by an
unconditional print claiming three calls ran.

`_ran` is the fix: each name appears in this file EXACTLY ONCE, as the function object handed
to the call that runs it, and the printed list is appended to by the call itself. Delete a
call site and the name leaves the source with it, so the census goes red -- and the line
cannot claim a function ran that did not. That is also why this docstring describes the three
function-local dependencies rather than listing them: `_code_only` strips comment lines and
not string literals, so a name written HERE would restore exactly the hole the printed
literal was.
"""

import json
import os
import sys
import tempfile

import numpy as np

from armature_core import aapose, donor_gate, pngio

# THE HALT CONTRACT IS IMPORTED, NOT SPELLED A THIRD TIME. WAVE 26 (ci-packaging,
# F-3b17a904). Until this line the premise guard below refused with a bare
# `raise SystemExit("clean-room probe imported the source tree: " + ...)`: no class, no
# clause, no evidence, and exit 1 -- the code this repository reserves for `this tool
# crashed`, pinned by `tests/test_packaging.py::
# test_a_gate_refusal_exits_2_with_its_sentinel_and_a_crash_exits_1`. Driven in a worktree
# with the repo venv before the fix, both directions: the refusal path
# (`PYTHONPATH=<worktree>/tools`, so `armature_core` resolves to the checkout) printed one
# line on stderr, no halt line, EXIT 1; a crash path (a stub `armature_core` under a
# directory named `site-packages` whose `blank_canvas` raises) printed a traceback, no halt
# line, EXIT 1. A refusal and a crash were byte-indistinguishable on the guard that decides
# whether the wheel room's verdict means anything -- while `release: published` has fired and
# both registries are waiting.
#
# `classifier_gate.py` sits in this directory and already holds the contract, spelled LOCALLY
# because `armature_core.parts.run_tool_main` is not importable in the clean room. That is a
# RECORDED EXCEPTION, not an invitation to a third copy: this file imports that function and
# passes its own tokens. Both callers run this file with its own directory on `sys.path[0]`
# (`.../clean-room/lazy_import_probe.py` under the action, the same absolute path under
# `verify.ps1`'s leg 3), so the import resolves with no packaging of any kind -- and
# `classifier_gate` now reads the trove list inside `main`, so importing it needs nothing but
# the stdlib, which is all this clean room has.
from classifier_gate import run_gate_main

#: The andon's name, carried in every halt record's `gate` field.
GATE = "LAZY_IMPORT"

#: The tool name, the stem, so a reader keying on the printed prefix and a reader keying on
#: the file agree -- `classifier_gate.py`'s rule, applied here.
TOOL = "lazy_import_probe"

#: The printed tokens. An operator (and `tests/test_instrument_exits.py`'s population, once
#: it reaches `.github/actions/**/*.py`) keys on these, never on prose.
HALT = "LAZY_IMPORT_PROBE_HALT "
OK = "LAZY_IMPORT_PROBE_OK "


class LazyImportProbeFailure(Exception):
    """A refusal this probe is responsible for. · ANDON

    The shape `ClassifierGateFailure` one file over has, for the reason recorded there:
    carries the clause that fired and the evidence it fired on, so the halt record names
    WHICH check refused and on WHAT.
    """

    def __init__(self, message, clause, evidence=None):
        super().__init__(message)
        self.gate = GATE
        self.clause = clause
        self.evidence = dict(evidence or {})
        self.evidence["clause"] = clause


#: The functions that actually ran, in order, appended by `_ran` AFTER each call returns.
RAN = []


def _ran(fn, *args):
    """Call `fn(*args)` and record its name. The record is a CONSEQUENCE of the call."""
    fn(*args)
    RAN.append(fn.__name__)


def main(argv):
    # `argv` is unread for the probe body — `run_gate_main` calls `fn(argv)` — but `-h` /
    # `--help` is answered here the same way `classifier_gate.py` answers it: a help request
    # is not a gate firing.
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(
            "Usage: python lazy_import_probe.py\n"
            "  %s<json> and exit 0 when every lazy third-party import ran against the "
            "installed wheel\n"
            "  %s<json> and exit 2 for a refusal; exit 1 for a crash\n"
            "  -h / --help prints this and exits 0"
            % (OK, HALT)
        )
        return 0
    # The leg's own premise, checked rather than assumed: this must be the wheel, not a
    # checkout sitting one directory up. `sys.path[0]` is this file's directory inside the
    # repository when `verify.ps1` runs it, so the check is load-bearing on the rig too.
    if "site-packages" not in aapose.__file__.replace("\\", "/"):
        raise LazyImportProbeFailure(
            "the clean-room probe imported the source tree rather than the installed "
            "wheel, so nothing below is a claim about the artifact: " + aapose.__file__,
            "probe-imported-the-source-tree",
            {"module": "armature_core.aapose", "resolved_to": aapose.__file__})

    canvas = aapose.blank_canvas(64, 64)
    body = np.zeros((aapose.KEYPOINT_COUNT, 3))
    body[:, :2] = 32.0
    body[:, 2] = 1.0
    _ran(aapose.draw_body, canvas, body)
    hand = np.zeros((aapose.HAND_KEYPOINT_COUNT, 3))
    hand[:, :2] = 32.0
    hand[:, 2] = 1.0
    _ran(aapose.draw_hand, canvas, hand)

    frames = tempfile.mkdtemp()
    paths = []
    for i in range(2):
        p = os.path.join(frames, "%05d.png" % i)
        pngio.write_png(p, np.full((8, 8, 3), i * 40, dtype=np.uint8))
        paths.append(p)
    _ran(donor_gate.mean_consecutive_frame_difference, paths)

    print("clean room: " + ", ".join(RAN) + " all ran")
    print(OK + json.dumps({"tool": TOOL, "gate": GATE, "ran": list(RAN)}))


if __name__ == "__main__":
    run_gate_main(main, sys.argv, tool=TOOL, gate=GATE, halt=HALT,
                  refusal_class=LazyImportProbeFailure)
