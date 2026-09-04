"""The two version manifests must agree at every commit, not first at release time.

Named `test_version_agreement` rather than `test_packaging` because the ci-packaging
half of P8 lands its own `tests/test_packaging.py`; this is the standalone sibling that
answers the question without parsing a workflow file.

WHY THIS RIDES THE SUITE. The agreement between `pyproject.toml` and `npm/package.json`
is asserted in exactly one place — `.github/workflows/release.yml:72` — so it is checked
only when the release workflow runs. `ci.yml`, which runs on push and on pull request,
does not check it. A bump that touches one manifest and not the other therefore goes
green, sits on `main`, and surfaces as a halted release and a scramble to re-tag.

The gate at line 72 works; measured 2026-09-03, it is OUTSIDE the
`if [ "$event_name" = "release" ]` block, so even a `workflow_dispatch` compares the two
manifests and cannot be walked past. It fires late, and the suite is where it can fire
early. That is the whole of what this file adds.

STDLIB ONLY, and REPO-ANCHORED, for the reason `tests/test_record_index.py` states in as
many words: a check that needs an uninstalled sibling to run is a check that does not run,
and a check that reads a bare relative path is a check that reads whatever directory
pytest happened to be invoked from.
"""

import json
import os
import re

import pytest

from conftest import REPO

PYPROJECT = os.path.join(REPO, "pyproject.toml")
NPM_PACKAGE = os.path.join(REPO, "npm", "package.json")

SEMVER = re.compile(r"^\d+\.\d+\.\d+([-+].+)?$")


def pyproject_version(path=PYPROJECT):
    """`project.version`, via tomllib where it exists and a scanner where it does not.

    `tomllib` landed in 3.11, so whether this fallback is load-bearing or dead code is a
    question about `requires-python` — which this docstring used to answer by writing
    `>=3.10` down. It is derived instead, by
    `test_the_tomllib_fallbacks_premise_is_the_floor_pyproject_declares`, because a floor
    that moves leaves a typed one asserting a version nobody supports.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - 3.10 only
        tomllib = None

    if tomllib is not None:
        with open(path, "rb") as fh:
            return tomllib.load(fh)["project"]["version"]

    section, version = None, None  # pragma: no cover - 3.10 only
    with open(path, encoding="utf-8") as fh:  # pragma: no cover - 3.10 only
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1]
            elif section == "project" and stripped.startswith("version"):
                version = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if version is None:  # pragma: no cover - 3.10 only
        raise AssertionError(f"{path} declares no [project] version")
    return version


def requires_python_floor(path=PYPROJECT):
    """The minor version `requires-python` admits, read off pyproject rather than typed."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(r'requires-python\s*=\s*["\']>=\s*3\.(\d+)', text)
    assert match, "pyproject declares no `requires-python` floor of the form >=3.N"
    return int(match.group(1))


def test_the_tomllib_fallbacks_premise_is_the_floor_pyproject_declares():
    """The fallback above is either load-bearing or dead, and pyproject decides which.

    The docstring used to state the floor as `>=3.10`. A typed version number in a
    docstring is a claim nobody re-measures: it survived the floor moving, and a reader
    would have taken the fallback for coverage of an interpreter the project no longer
    admits. Stated as a derivation, both answers stay true as the floor moves.
    """
    floor = requires_python_floor()
    import importlib.util

    has_tomllib = importlib.util.find_spec("tomllib") is not None
    if floor >= 11:
        assert has_tomllib, (
            "requires-python admits only 3.11+, where tomllib is stdlib, yet this "
            "interpreter has none — the fallback below is the only path and is not dead")
    else:
        assert floor == 10, floor  # a floor below 3.10 is a change nobody has recorded


def npm_version(path=NPM_PACKAGE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["version"]


# ------------------------------------------------------------------ the two manifests

def test_both_manifests_are_present_where_the_release_workflow_looks_for_them():
    """The paths this file reads are the paths release.yml reads. If either moved, this
    check would silently be reading nothing, which is the failure mode a check has when it
    cannot fail."""
    assert os.path.isfile(PYPROJECT), PYPROJECT
    assert os.path.isfile(NPM_PACKAGE), NPM_PACKAGE


def test_the_python_and_npm_packages_declare_the_same_version():
    """The invariant: THE TWO MANIFESTS CARRY THE SAME VERSION AT EVERY COMMIT.

    What this looks like if it is wrong: a bump lands on `pyproject.toml` alone, CI is
    green because nothing in `ci.yml` compares them, and the divergence is discovered by
    `release.yml` at the moment someone cuts a tag.
    """
    py, npm = pyproject_version(), npm_version()
    assert py == npm, (
        f"pyproject.toml declares {py!r} and npm/package.json declares {npm!r}. "
        f"release.yml compares these two and halts on a mismatch; a divergence that "
        f"reaches main is a blocked release, and it is catchable here at the commit "
        f"that introduces it."
    )


@pytest.mark.parametrize("reader,path", [(pyproject_version, PYPROJECT),
                                         (npm_version, NPM_PACKAGE)])
def test_each_declared_version_is_a_version(reader, path):
    """Equality alone would be satisfied by two manifests that both say `""`."""
    v = reader()
    assert isinstance(v, str) and SEMVER.match(v), f"{path} declares {v!r}"


# ------------------------------------------------- the check itself, pushed red on purpose

def test_the_comparison_would_fail_on_a_divergence(tmp_path):
    """A check that only ever runs on agreeing inputs is unproven.

    Both readers are pointed at manifests written here that disagree, and the equality
    the test above makes is asserted to be false. If a later edit made either reader
    return a constant, or made the comparison compare a thing to itself, this fails.
    """
    py = tmp_path / "pyproject.toml"
    py.write_text('[project]\nname = "x"\nversion = "9.9.9"\n', encoding="utf-8")
    npm = tmp_path / "package.json"
    npm.write_text(json.dumps({"name": "x", "version": "0.0.1"}), encoding="utf-8")

    assert pyproject_version(str(py)) == "9.9.9"
    assert npm_version(str(npm)) == "0.0.1"
    assert pyproject_version(str(py)) != npm_version(str(npm))
