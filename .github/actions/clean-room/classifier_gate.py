"""Refuse a classifier PyPI does not have, before the publish fork.

THE FAILURE CLASS THIS EXISTS FOR, and the only one in this repository that has already
been paid for once. `pyproject.toml:70-72` records it in its own words: `Topic ::
Scientific :: Image Processing` does not exist, PyPI rejected the first upload with a 400
on it, and `twine check` had passed -- twine validates metadata STRUCTURE, not classifier
membership. Re-measured 2026-09-04 on a `git archive` copy of this tree with that exact row
added back beside the valid ones: `python -m build` produced both artifacts with no
warning, and `python -m twine check dist/*` printed PASSED for the wheel AND the sdist and
exited 0.

WHERE THAT LANDS IF IT IS NOT CAUGHT HERE. `release: published` has fired, the tag is cut
and public, and the 400 arrives inside `pypa/gh-action-pypi-publish` -- while the `npm`
job, a sibling on `needs: verify` running in PARALLEL, publishes successfully. That is the
asymmetric one-registry-ahead state release.yml's visibility gate was hoisted upstream into
`verify` to prevent, reached by the metadata path instead. This gate runs upstream of the
same fork, for the same reason.

WHY `trove-classifiers` AND NOT `twine check --strict`. Measured 2026-09-04: `grep -rn
'trove|--strict'` over this repository's `.py`, `.yml`, `.toml`, `.ps1` and `.json` returns
NOTHING -- neither existed here, so there was nothing to prefer. And `--strict` would not
have helped: it promotes the README RENDER warnings to errors and still reads no classifier
list. `trove-classifiers` IS the list PyPI validates against, published by PyPA.

WHY THIS IS A FILE AND NOT TWO HEREDOCS. `.github/actions/clean-room/action.yml`'s own
header states the law: copying a leg into a second caller is a second implementation of one
gate, and copies fork -- which is how the font dependency forked one directory over, and how
the sdist room sat in the action and not in `verify.ps1` for two waves. The action calls
this file and so does `verify.ps1`'s leg 3, whose DESCRIPTION equates a green local run to a
green CI run. One text, two callers. (`lazy_import_probe.py` beside this file is the same
law applied to the probe two paragraphs away, which stayed duplicated until wave 23.)

THE POPULATION IS THE DIRECTORY, NOT AN EXTENSION. `classifier_rows` returns None for any
path that is neither `.whl` nor `.tar.gz`, `main` used to `continue` past those silently,
and the success line said `every row present` without ever naming what it had SKIPPED --
while `release.yml:305-308` uploads the whole of `dist/` and the publish action publishes
that directory. Re-measured on `e8263a3` with no network: a synthetic `dist/` holding a
valid `fake-0.1-py3-none-any.whl` (clean rows) beside `fake-0.1.zip` whose PKG-INFO carried
the banned row -- `.zip` is in twine's own `DIST_EXTENSIONS` -- printed `classifiers: 1
artifact(s) judged against trove-classifiers, every row present`, exited 0, and never
mentioned the `.zip`. Not reachable from today's `python -m build`, which is exactly what
makes it a population keyed on a spelling rather than on what gets published. So an
unreadable file in `dist/` is now a REFUSAL, by name, and the success line states judged AND
skipped counts so a reader can reconcile them against what the upload step carries.

THE HALT CONTRACT, AND WHY IT IS SPELLED HERE RATHER THAN IMPORTED. Every gate under
`tools/**` raises a typed `GateFailure` from `armature_core.errors` and its `__main__`
prints `<PREFIX>_HALT <strict json>` through `armature_core.parts.run_tool_main`, exiting 2
for a refusal and 1 for a crash. This gate's six refusals were bare
`raise SystemExit("::error::...")` -- no class, no clause, no evidence, and exit 1, the code
this repository's convention reserves for `this tool crashed` (measured on `e8263a3`: the
empty-population refusal and the banned-row refusal both exited 1, against
`tests/test_packaging.py::test_a_gate_refusal_exits_2_with_its_sentinel_and_a_crash_exits_1`).
It cannot import the shared handler: the step that runs it installs `trove-classifiers` and
nothing else, `armature_core` is not on the path of the runner's python, and this file must
keep working with no repository checkout beyond `$GITHUB_ACTION_PATH`. So the contract is
reproduced here, in the same shape and with the same key order, and the classes are local.

Usage: `python classifier_gate.py [dist-dir]` (default `dist`). `CLASSIFIER_GATE_OK <json>`
and exit 0 when every row of every readable artifact is in the trove list and nothing in the
directory was unreadable; `CLASSIFIER_GATE_HALT <json>` and exit 2 for any refusal, exit 1
for a crash.
"""

import email.parser
import glob
import json
import os
import sys
import tarfile
import traceback
import zipfile

from trove_classifiers import classifiers as TROVE

#: The andon's name, carried in every halt record's `gate` field.
GATE = "CLASSIFIER"

#: The tool name, carried in every halt record's `tool` field. The stem, so a reader keying
#: on the printed prefix and a reader keying on the file agree.
TOOL = "classifier_gate"

#: The printed tokens. An operator (and `tests/test_instrument_exits.py`'s population, once
#: it reaches `.github/actions/**/*.py`) keys on these, never on prose.
HALT = "CLASSIFIER_GATE_HALT "
OK = "CLASSIFIER_GATE_OK "

# THE GATE'S OWN PREMISE, CHECKED RATHER THAN ASSUMED. A check that cannot fail is not a
# check: an import that returned an empty set, or a day on which the exact spelling this
# project already paid for became real, would make every artifact below pass and this gate
# decoration.
SENTINEL = "Topic :: Scientific :: Image Processing"


class ClassifierGateFailure(Exception):
    """A refusal this gate is responsible for. · ANDON

    Carries the clause that fired and the evidence it fired on, the way every
    `armature_core.errors.GateFailure` subclass does, so the halt record names WHICH check
    refused and on WHAT -- rather than leaving a reader to parse an `::error::` string.
    """

    def __init__(self, message, clause, evidence=None):
        super().__init__(message)
        self.gate = GATE
        self.clause = clause
        self.evidence = dict(evidence or {})
        self.evidence["clause"] = clause


def classifier_rows(path):
    """The `Classifier:` rows of a built artifact's OWN metadata, or None if not one.

    Read from the artifacts rather than from `project.classifiers`, because these two files
    are what PyPI receives and validates -- a backend that injected, dropped or rewrote a
    row would be invisible to a pyproject read, and the calling action's header states the
    law it runs under: the artifact handed to publish is the thing to check.
    """
    if path.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ClassifierGateFailure(
                    "%s holds %d dist-info/METADATA members; exactly one is readable "
                    "metadata" % (path, len(names)),
                    "artifact-metadata-member-count",
                    {"artifact": os.path.basename(path), "members": len(names)})
            text = archive.read(names[0]).decode("utf-8")
    elif path.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            names = [n for n in archive.getnames() if n.endswith("/PKG-INFO")]
            if not names:
                raise ClassifierGateFailure(
                    "%s holds no PKG-INFO" % path,
                    "artifact-has-no-pkg-info",
                    {"artifact": os.path.basename(path)})
            text = archive.extractfile(min(names, key=len)).read().decode("utf-8")
    else:
        return None
    return email.parser.Parser().parsestr(text).get_all("Classifier") or []


def main(argv):
    dist = argv[1] if len(argv) > 1 else "dist"
    if len(TROVE) < 100:
        raise ClassifierGateFailure(
            "the trove list loaded %d rows; refusing to judge an artifact against it"
            % len(TROVE),
            "trove-list-too-small",
            {"rows": len(TROVE)})
    if SENTINEL in TROVE:
        raise ClassifierGateFailure(
            "%r is a real classifier now; this gate's self-test needs a new sentinel"
            % SENTINEL,
            "sentinel-is-real",
            {"sentinel": SENTINEL})

    judged, skipped, bad = 0, [], []
    for path in sorted(glob.glob(os.path.join(dist, "*"))):
        name = os.path.basename(path)
        rows = classifier_rows(path)
        if rows is None:
            # NAMED, NOT SKIPPED SILENTLY. `release.yml` uploads this whole directory and the
            # publish action publishes it, so a file this gate cannot read is a file that
            # reaches PyPI unjudged.
            skipped.append(name)
            continue
        if not rows:
            raise ClassifierGateFailure(
                "%s carries no Classifier row at all; this gate would then pass on any "
                "spelling, so it refuses rather than reporting a vacuous PASS" % name,
                "artifact-carries-no-classifier-row",
                {"artifact": name})
        judged += 1
        for row in rows:
            if row not in TROVE:
                bad.append((name, row))
                print("::error::%s: %r is not a PyPI classifier. `twine check` validates "
                      "metadata STRUCTURE, not membership; PyPI answers this with a 400 at "
                      "upload, after the tag is cut and public." % (name, row))
        print("%s: %d classifier rows, %d unknown"
              % (name, len(rows), sum(1 for n, _ in bad if n == name)))
    if judged == 0:
        raise ClassifierGateFailure(
            "no wheel or sdist in %s to read classifiers from; this gate is upstream of the "
            "publish fork and refuses rather than passing on an empty population" % dist,
            "empty-population",
            {"dist": dist, "skipped": sorted(skipped)})
    if skipped:
        raise ClassifierGateFailure(
            "%d file(s) in %s carry metadata this gate cannot read, and the publish step "
            "uploads the whole directory: %s" % (len(skipped), dist, ", ".join(sorted(skipped))),
            "dist-holds-a-file-this-gate-cannot-read",
            {"dist": dist, "judged": judged, "skipped": sorted(skipped)})
    if bad:
        raise ClassifierGateFailure(
            "%d classifier row(s) PyPI does not have, across %d artifact(s); refusing before "
            "the publish fork." % (len(bad), judged),
            "classifier-row-pypi-does-not-have",
            {"judged": judged, "rows": ["%s: %s" % (n, r) for n, r in bad]})
    print(OK + json.dumps({
        "tool": TOOL, "gate": GATE, "dist": dist,
        "judged": judged, "skipped": sorted(skipped),
    }))


def run_gate_main(fn, argv):
    """Run `fn(argv)` under the halt contract and exit. NEVER RETURNS.

    The shape of `armature_core.parts.run_tool_main`, reproduced rather than imported for
    the reason the module docstring records: the step that runs this file installs
    `trove-classifiers` alone. Exit 2 for a refusal this gate is responsible for, 1 for
    anything else -- and the record is printed either way, because the caller's `set -eu`
    fails the step on both and the distinction would otherwise live nowhere.
    """
    try:
        raise SystemExit(fn(argv))
    except SystemExit:
        raise
    except BaseException as exc:                 # noqa: BLE001 -- the halt must be loud
        refusal = isinstance(exc, ClassifierGateFailure)
        code = 2 if refusal else 1
        outcome = ("HALTED — a gate fired" if refusal else "FAILED — an unhandled error")
        sentinel = {
            "tool": TOOL, "outcome": outcome, "gate": GATE,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        line = json.dumps(sentinel)
        try:
            traceback.print_exc()
            detail = getattr(exc, "evidence", None)
            sentinel = {
                "tool": TOOL, "outcome": outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": detail if isinstance(detail, dict) else None}
            line = json.dumps(sentinel, default=str, allow_nan=False)
        except BaseException:                                          # noqa: BLE001
            pass
        finally:
            print("::error::" + str(exc))
            print(HALT + line)
            sys.exit(code)


if __name__ == "__main__":
    run_gate_main(main, sys.argv)
