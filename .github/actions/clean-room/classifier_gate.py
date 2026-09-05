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
green CI run. One text, two callers.

Usage: `python classifier_gate.py [dist-dir]` (default `dist`). Exit 0 when every row of
every artifact's own metadata is in the trove list; non-zero, naming the row, otherwise.
"""

import email.parser
import glob
import os
import sys
import tarfile
import zipfile

from trove_classifiers import classifiers as TROVE

# THE GATE'S OWN PREMISE, CHECKED RATHER THAN ASSUMED. A check that cannot fail is not a
# check: an import that returned an empty set, or a day on which the exact spelling this
# project already paid for became real, would make every artifact below pass and this gate
# decoration.
SENTINEL = "Topic :: Scientific :: Image Processing"


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
                raise SystemExit(
                    "::error::%s holds %d dist-info/METADATA members" % (path, len(names)))
            text = archive.read(names[0]).decode("utf-8")
    elif path.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            names = [n for n in archive.getnames() if n.endswith("/PKG-INFO")]
            if not names:
                raise SystemExit("::error::%s holds no PKG-INFO" % path)
            text = archive.extractfile(min(names, key=len)).read().decode("utf-8")
    else:
        return None
    return email.parser.Parser().parsestr(text).get_all("Classifier") or []


def main(argv):
    dist = argv[1] if len(argv) > 1 else "dist"
    if len(TROVE) < 100:
        raise SystemExit(
            "::error::the trove list loaded %d rows; refusing to judge an artifact "
            "against it" % len(TROVE))
    if SENTINEL in TROVE:
        raise SystemExit(
            "::error::%r is a real classifier now; this gate's self-test needs a new "
            "sentinel" % SENTINEL)

    judged, bad = 0, []
    for path in sorted(glob.glob(os.path.join(dist, "*"))):
        rows = classifier_rows(path)
        if rows is None:
            continue
        name = os.path.basename(path)
        if not rows:
            raise SystemExit(
                "::error::%s carries no Classifier row at all; this gate would then pass on "
                "any spelling, so it refuses rather than reporting a vacuous PASS" % name)
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
        raise SystemExit(
            "::error::no wheel or sdist in %s to read classifiers from; this gate is "
            "upstream of the publish fork and refuses rather than passing on an empty "
            "population" % dist)
    if bad:
        raise SystemExit(
            "::error::%d classifier row(s) PyPI does not have, across %d artifact(s); "
            "refusing before the publish fork." % (len(bad), judged))
    print("classifiers: %d artifact(s) judged against trove-classifiers, every row present"
          % judged)


if __name__ == "__main__":
    main(sys.argv)
