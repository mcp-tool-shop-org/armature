"""The workflow files, read as code — because on release day they are the only code that runs.

Everything under `.github/workflows/` performs steps with no compensator: a version taken on
PyPI or npm is taken forever. The shell inside those steps is never exercised by any suite,
so it is exercised here — the tag gate's script is extracted from the YAML and RUN, with the
event and ref that were measured to walk straight past it.

What each group is here to catch, measured on this tree before the fix:

* **the tag gate** — the comparison was wrapped in `if [ "$EVENT" = "release" ]`, so a
  `workflow_dispatch` from any branch printed `tag=main pyproject=0.3.0` and PASSED, having
  compared nothing about the tag. Both downstream jobs then publish whatever the dispatched
  branch's manifests carry. The gate is now unconditional and this file drives it.
* **the npm job's permissions** — a job-level `permissions:` block replaces the workflow-level
  grant outright, so `id-token: write` alone leaves `contents` at none while step 1 is
  `actions/checkout`.
* **re-run behaviour** — the npm job asks the registry before publishing; the PyPI job did not,
  so the same re-run reported an honest notice on one side and a red 400 on the other.
* **run-time resolution** — `npm install -g npm@latest` installs whatever npm exists on
  release day, which is not the npm that was verified.
* **CI's own trigger paths** — the build inputs named by pyproject (`readme`, `license`) were
  not in the paths filter, so renaming one triggered no CI run and surfaced first in the
  release job, after the tag existed.
* **the clean-room leg** — it ran `armature check` and `armature modules --json`, neither of
  which executes a function body, so it was green on a wheel whose drawing path could not run.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib

import pytest

from conftest import REPO

from test_packaging import lazy_import_call_sites, lazy_third_party_roots

WORKFLOWS = os.path.join(REPO, ".github", "workflows")
TESTS_DIR = os.path.join(REPO, "tests")


# -- a small indentation reader (no PyYAML in this repo's install line) -------------------


def _text(name):
    with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as fh:
        return fh.read()


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def block_at(lines, index):
    """The lines nested under `lines[index]`, i.e. every following deeper-indented line."""
    base = _indent(lines[index])
    out = []
    for line in lines[index + 1 :]:
        if line.strip() and _indent(line) <= base:
            break
        out.append(line)
    return out


def named_block(text, name, indent):
    """The block under a `name:` key at exactly `indent` spaces."""
    lines = text.splitlines()
    head = " " * indent + name + ":"
    for i, line in enumerate(lines):
        if line.rstrip() == head or line.startswith(head + " "):
            return block_at(lines, i)
    raise AssertionError(f"no `{name}:` key at indent {indent}")


def step_containing(text, needle):
    """The one step (a `- ` list item) whose body contains `needle`."""
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if needle in line]
    assert len(hits) == 1, f"{needle!r} appears {len(hits)} times; expected exactly one"
    i = hits[0]
    while i >= 0 and not lines[i].lstrip().startswith("- "):
        i -= 1
    assert i >= 0, f"{needle!r} is not inside a step"
    base = _indent(lines[i])
    out = [lines[i]]
    for line in lines[i + 1 :]:
        if line.strip() and (_indent(line) <= base):
            break
        out.append(line)
    return "\n".join(out)


def run_script(step_text):
    """The shell script of a step's `run: |` block, dedented."""
    lines = step_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() in ("run: |", "run: |-"):
            body = block_at(lines, i)
            pad = min((_indent(x) for x in body if x.strip()), default=0)
            return "\n".join(x[pad:] for x in body)
        if line.strip().startswith("run: "):
            return line.strip()[len("run: ") :]
    raise AssertionError("that step has no `run:`")


# -- the tag gate, executed ---------------------------------------------------------------

RELEASE = _text("release.yml")
CI = _text("ci.yml")

with open(os.path.join(REPO, "pyproject.toml"), "rb") as _fh:
    PYPROJECT = tomllib.load(_fh)

TAG_STEP = step_containing(RELEASE, "The version in the tag must equal")
TAG_SCRIPT = run_script(TAG_STEP)

def _bash():
    r"""The bash that can run the workflow's own shell here.

    On Windows `shutil.which("bash")` can resolve to `C:\Windows\System32\bash.exe`, the WSL
    launcher: it runs a Linux userland that cannot see `sys.executable`'s Windows path, and it
    reads a CRLF-translated stdin as `case ... in<CR>`. Git for Windows' bash shares this
    filesystem and is preferred; with only the WSL launcher present the tests skip by name
    rather than fail for a reason that has nothing to do with the gate. On a POSIX runner
    this is simply /bin/bash.
    """
    if os.name == "nt":
        for candidate in (r"C:\Program Files\Git\bin\bash.exe",
                          r"C:\Program Files\Git\usr\bin\bash.exe"):
            if os.path.isfile(candidate):
                return candidate
        found = shutil.which("bash")
        if found and "system32" in found.lower():
            return None
        return found
    return shutil.which("bash")


BASH = _bash()

needs_shell = pytest.mark.skipif(
    BASH is None, reason="no bash that shares this filesystem to run the workflow's own shell with"
)
needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="the gate reads npm/package.json through node"
)


def _drive(ref, ref_name):
    """Run the tag gate's real script with a GitHub ref, exactly as the runner would.

    `python` is rewritten to this interpreter because a GitHub runner has one on PATH and a
    developer's shell may not; nothing else about the script is touched, and
    `test_the_tag_gate_is_the_script_this_test_runs` is what keeps that honest.
    """
    script = re.sub(r"(?m)^python ", f'"{sys.executable}" '.replace("\\", "/"), TAG_SCRIPT)
    env = dict(os.environ, GITHUB_REF=ref, GITHUB_REF_NAME=ref_name)
    # The script goes to bash on STDIN as BYTES with LF endings — not as a `-c` argument and
    # not through a text-mode pipe. On Windows the process command line re-quotes the step's
    # own nested `python -c "..."` (measured 2026-09-04 as `syntax error near unexpected
    # token`), and a text-mode pipe translates every newline to CRLF, which bash reads as
    # `in<CR>`. Bytes on stdin carry the script verbatim on every platform.
    proc = subprocess.run(
        [BASH, "-s"],
        input=script.replace("\r\n", "\n").encode("utf-8"),
        cwd=REPO,
        capture_output=True,
        env=env,
    )
    return subprocess.CompletedProcess(
        proc.args, proc.returncode,
        proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace"),
    )


def test_the_tag_gate_is_the_script_this_test_runs():
    """No GitHub expression may survive in that step.

    `${{ ... }}` is interpolated by the runner before the shell ever sees it, so a gate
    written with one is a gate this test could only pretend to exercise. The event
    conditional that made the step vacuous on `workflow_dispatch` was exactly such an
    expression.
    """
    assert "${{" not in TAG_SCRIPT, f"a runner-side expression is inside the gate:\n{TAG_SCRIPT}"
    assert "github.event_name" not in TAG_SCRIPT


@needs_shell
def test_the_tag_gate_refuses_a_workflow_dispatch_from_a_branch():
    """The measured hole: event=workflow_dispatch, ref=main -> exit 0, nothing compared."""
    got = _drive("refs/heads/main", "main")
    assert got.returncode != 0, (
        "release.yml's version gate passed on a branch ref; the pypi and npm jobs would "
        f"publish from an untagged commit.\nstdout: {got.stdout}\nstderr: {got.stderr}"
    )
    # The refusal carries the measurement that fired it, so the log says which ref it was.
    assert "refs/heads/main" in (got.stdout + got.stderr), got.stdout + got.stderr


@needs_shell
def test_the_tag_gate_refuses_a_dispatch_from_any_other_ref_shape():
    for ref, name in (
        ("refs/heads/feature/x", "feature/x"),
        ("refs/pull/12/merge", "12/merge"),
        ("", ""),
    ):
        got = _drive(ref, name)
        assert got.returncode != 0, f"ref {ref!r} reached the registries"


@needs_shell
@needs_node
def test_the_tag_gate_passes_on_the_tag_that_matches_the_package():
    version = PYPROJECT["project"]["version"]
    got = _drive(f"refs/tags/v{version}", f"v{version}")
    assert got.returncode == 0, f"stdout: {got.stdout}\nstderr: {got.stderr}"
    assert f"tag={version}" in got.stdout


@needs_shell
@needs_node
def test_the_tag_gate_refuses_a_tag_that_does_not_match_the_package():
    got = _drive("refs/tags/v9.9.9", "v9.9.9")
    assert got.returncode != 0
    assert "9.9.9" in (got.stdout + got.stderr)


# -- job permissions, re-run behaviour, and pinning ---------------------------------------


def _code_only(script):
    """The script with `#` comment lines dropped -- naming a module in a comment is not
    reaching it, and this test is about what the leg RUNS."""
    return "\n".join(
        line for line in script.splitlines() if not line.lstrip().startswith("#")
    )



def job_names(text):
    return [
        line.strip().rstrip(":")
        for line in named_block(text, "jobs", 0)
        if line.strip() and _indent(line) == 2 and line.rstrip().endswith(":")
    ]


def _job_lines(text, name):
    lines = text.splitlines()
    head = "  " + name + ":"
    for i, line in enumerate(lines):
        if line.rstrip() == head:
            return block_at(lines, i)
    raise AssertionError(f"no job named {name}")


# ---------------------------------------------------------- the checkout token, everywhere
#
# Wave 6, F-bc7bdca3. This check was one loop with two `continue`s and one assert, and
# nothing counted what the loop examined. Measured by instrumenting its own helpers over
# both parametrised workflows: release.yml resolves verify -> skipped (inherits), pypi ->
# skipped (no checkout), npm -> ASSERTED; ci.yml has NO workflow-level `permissions:` block
# at all and BOTH of its checkout jobs took the "inherits the workflow-level grant" branch.
# So the `ci.yml` parameter passed having asserted on zero jobs, and one job out of five
# across the two files was ever opened.
#
# The premise of that branch was false for ci.yml: there is nothing to inherit. Those jobs
# run on whatever the repository or organisation default token permission happens to be —
# the very thing a `contents: read` declaration exists to pin. And `pages.yml`, a third
# workflow whose `build` job also checks out, was not in the parametrised list at all.
#
# What replaces it enumerates the workflow files from disk, enumerates the checkout jobs in
# them, asserts that census, and then requires every one of those jobs to have a STATED
# contents scope — its own or a workflow-level block the file actually declares.

#: Every job that runs `actions/checkout`, per workflow file. Enumerated from the files and
#: asserted against this table, so a job that starts or stops checking out is a failure here
#: rather than a silent change in what the check below covers.
CHECKOUT_JOBS = {
    "ci.yml": ["launcher", "python-tests", "site-build"],
    "pages.yml": ["build"],
    "release.yml": ["npm", "verify"],
}


def workflow_files():
    return sorted(n for n in os.listdir(WORKFLOWS) if n.endswith((".yml", ".yaml")))


def _checkout_jobs(text):
    return sorted(name for name in job_names(text)
                  if "actions/checkout" in "\n".join(_job_lines(text, name)))


def _declares_contents_read(body):
    return re.search(r"(?m)^\s+contents:\s*read\s*$", body) is not None


def test_the_workflow_census_is_the_files_on_disk():
    """A fourth workflow added later joins these checks rather than escaping them."""
    assert workflow_files() == sorted(CHECKOUT_JOBS), (
        f"{WORKFLOWS} holds {workflow_files()}; the checks below cover "
        f"{sorted(CHECKOUT_JOBS)}")


@pytest.mark.parametrize("workflow", sorted(CHECKOUT_JOBS))
def test_the_checkout_job_census_is_the_jobs_in_the_file(workflow):
    """What the permissions check below examines, counted before it examines it."""
    assert _checkout_jobs(_text(workflow)) == CHECKOUT_JOBS[workflow]


@pytest.mark.parametrize("workflow", sorted(CHECKOUT_JOBS))
def test_every_job_that_checks_out_has_a_stated_contents_scope(workflow):
    """A job-level `permissions:` block REPLACES the workflow-level grant; it does not add.

    So a job that declares only `id-token: write` has no `contents` scope at all, and its
    `actions/checkout` authenticates the clone with a token that cannot read a private
    repository. A job with no block of its own inherits — but only if the FILE declares a
    workflow-level block; where it does not, the job runs on the repository or organisation
    default, which is exactly the thing `contents: read` exists to state.

    What this looks like if wrong: the loop `continue`s past every job and the parametrised
    case reports green having opened nothing. Hence `examined`, asserted against the census.
    """
    text = _text(workflow)
    workflow_level = re.search(r"(?m)^permissions:\s*$", text) is not None
    workflow_grant = "\n".join(named_block(text, "permissions", 0)) if workflow_level else ""

    examined, ungoverned = [], []
    for name in _checkout_jobs(text):
        examined.append(name)
        body = "\n".join(_job_lines(text, name))
        if re.search(r"(?m)^    permissions:\s*$", body) is not None:
            if not _declares_contents_read("\n".join(named_block(body, "permissions", 4))):
                ungoverned.append(
                    f"{name}: narrows its own permissions without `contents: read`, so the "
                    f"checkout token has no contents scope")
        elif not workflow_level:
            ungoverned.append(
                f"{name}: checks out with no permissions block of its own and no "
                f"workflow-level block in {workflow} to inherit, so the clone runs on the "
                f"repository or organisation default token permission")
        elif not _declares_contents_read(workflow_grant):
            ungoverned.append(
                f"{name}: inherits a workflow-level block that does not grant "
                f"`contents: read`")

    assert examined == CHECKOUT_JOBS[workflow], (
        f"{workflow}: examined {examined}, census says {CHECKOUT_JOBS[workflow]}; a "
        f"parametrised case that opens no job proves nothing")
    assert ungoverned == [], f"{workflow}:\n  " + "\n  ".join(ungoverned)


def test_a_narrowing_job_permissions_block_still_grants_contents_read():
    """The one job the old loop did reach, kept as its own fixture: release.yml's `npm`
    job declares `id-token: write` for trusted publishing and must re-declare
    `contents: read` beside it, because the block replaces rather than adds."""
    body = "\n".join(_job_lines(RELEASE, "npm"))
    assert re.search(r"(?m)^    permissions:\s*$", body), "the npm job stopped narrowing"
    block = "\n".join(named_block(body, "permissions", 4))
    assert _declares_contents_read(block), (
        f"the npm job narrows its permissions and then checks out:\n{block}")
    assert re.search(r"(?m)^\s+id-token:\s*write\s*$", block), (
        "the npm job no longer asks for id-token: write; this fixture is reading the "
        "wrong job")


def test_the_pypi_publish_reports_the_same_way_on_a_rerun_as_npm_does():
    """npm asks the registry first; PyPI must not fail red for having already succeeded."""
    step = step_containing(RELEASE, "pypa/gh-action-pypi-publish")
    assert re.search(r"(?m)^\s+skip-existing:\s*true\s*$", step), (
        "the pypi job has no skip-existing, so a re-run of a partially failed release "
        f"turns a completed publish into a red job:\n{step}"
    )


def test_the_publish_toolchain_is_not_resolved_on_release_day():
    """The one step with no compensator must run the code that was last verified."""
    code = _code_only(step_containing(RELEASE, "Upgrade npm for OIDC"))
    assert "npm@latest" not in code, f"npm is resolved at run time in the publish job:\n{code}"
    assert re.search(r"npm@(\^|~|=|\d)", code), f"no npm version constraint:\n{code}"


# -- CI's trigger paths and its clean-room leg --------------------------------------------


def _paths_under(trigger):
    lines = named_block(CI, "  " + trigger, 0)
    out, inside = [], False
    for line in lines:
        stripped = line.strip()
        if stripped == "paths:":
            inside = True
            continue
        if inside:
            if stripped.startswith("- "):
                out.append(stripped[2:].strip().strip('"').strip("'"))
            elif stripped and not stripped.startswith("#"):
                break
    return out


def _local_action_files():
    """Every composite action a workflow calls with `uses: ./...`, as repo-relative paths.

    Derived from the workflows themselves. `.github/actions/sheet-fonts/action.yml` is
    called by BOTH `ci.yml` and `release.yml`; editing it changes what two workflows do.
    """
    found = set()
    for name in sorted(os.listdir(WORKFLOWS)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as fh:
            for line in fh:
                m = re.search(r"uses:\s*\./(\S+)", line)
                if m:
                    found.add(m.group(1).rstrip("/"))
    out = set()
    for rel in found:
        base = os.path.join(REPO, rel.replace("/", os.sep))
        if os.path.isdir(base):
            for entry in sorted(os.listdir(base)):
                if entry in ("action.yml", "action.yaml"):
                    out.add(f"{rel}/{entry}")
        elif os.path.isfile(base):
            out.add(rel)
    return sorted(out)


def _repo_root_files_the_suite_reads():
    """Every repo-ROOT file named as a string literal by a test under `tests/`.

    The derivation is "every file the suite guards": if a test reads a file, editing that
    file can turn CI red, so editing it has to RUN CI. Matched against the real directory
    listing rather than `os.path.isfile`, because Windows would otherwise match `LICENSE`
    through the literal `license` and put a filename in the population that does not exist.
    """
    entries = {e for e in os.listdir(REPO) if os.path.isfile(os.path.join(REPO, e))}
    found = set()
    for name in sorted(os.listdir(TESTS_DIR)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(TESTS_DIR, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in entries:
                    found.add(node.value)
    return sorted(found)


def trigger_population():
    """THE DERIVATION (wave 8, F-0fac6017): every path the workflows and the suite consume.

    Until this wave the requirement was `{"pyproject.toml", project["readme"]}` plus the
    licence file — three paths, all of them already listed, so the test could not fail.
    Enumerated on 2026-09-04, three classes of file were consumed by CI and triggered
    nothing: the composite action BOTH workflows call, `verify.ps1` (whose behaviour
    `tests/test_verify_script.py` pins by lifting `Invoke-Leg` out of it), and `.gitignore`
    (whose content `tests/test_packaging.py` pins). A commit touching only one of those
    runs no CI at all, and the first surface where a breakage appears is the release job,
    after the tag exists.
    """
    project = PYPROJECT["project"]
    inputs = {"pyproject.toml", project["readme"]}
    licence = project.get("license")
    if isinstance(licence, dict) and licence.get("file"):
        inputs.add(licence["file"])
    inputs.update(_local_action_files())
    inputs.update(_repo_root_files_the_suite_reads())
    return sorted(inputs)


#: Derived on 2026-09-04. Equality, so a new composite action or a new repo-root file the
#: suite starts reading joins the requirement on the day it lands.
RECORDED_TRIGGER_POPULATION = [
    # `clean-room` joined at the wave-8 merge: ci-packaging lifted the clean-install leg into a
    # composite action called by ci.yml and release.yml (F-60ab1bd7); this census saw it
    # appear, which is the direction it exists for. `npm-clean-room` joined at wave 10 the
    # same way (F-3729edd4) — the npm package's half of that leg — and the census saw it too.
    ".github/actions/clean-room/action.yml", ".github/actions/npm-clean-room/action.yml",
    ".github/actions/sheet-fonts/action.yml",
    ".gitignore", "HANDOFF.md", "LICENSE", "MANIFEST.in", "README.md", "README.pypi.md",
    "pyproject.toml", "verify.ps1",
]


def test_the_trigger_population_is_derived_from_what_ci_and_the_suite_actually_consume():
    """Size and membership before the property. The old population was three paths read
    out of pyproject, every one of them already listed under both triggers — a test that
    could not fail."""
    pop = trigger_population()
    assert pop == RECORDED_TRIGGER_POPULATION, {
        "appeared": sorted(set(pop) - set(RECORDED_TRIGGER_POPULATION)),
        "vanished": sorted(set(RECORDED_TRIGGER_POPULATION) - set(pop)),
    }
    # two composite actions since the wave-8 merge (ci-packaging lifted the clean-room leg
    # beside the font step); this pin is the typed half the derived census above exists to
    # catch, and it caught this one at the merge.
    assert _local_action_files() == [".github/actions/clean-room/action.yml",
                                     ".github/actions/npm-clean-room/action.yml",
                                     ".github/actions/sheet-fonts/action.yml"]
    assert {"verify.ps1", ".gitignore"} <= set(_repo_root_files_the_suite_reads())
    #: the two enumerators must agree: `action_files()` walks `.github/actions/` off the
    #: disk, `_local_action_files()` reads what the workflows CALL. An action on disk that
    #: nothing calls is dead weight nobody would notice; one called but absent is a red
    #: workflow. Either way the disagreement is worth a name.
    on_disk = sorted(os.path.relpath(p, REPO).replace("\\", "/") for p in action_files())
    assert _local_action_files() == on_disk, {
        "called but not on disk": sorted(set(_local_action_files()) - set(on_disk)),
        "on disk but never called": sorted(set(on_disk) - set(_local_action_files())),
    }


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_ci_runs_on_every_file_the_package_is_built_from(trigger):
    """Every derived path must match a trigger path, not merely the three pyproject names.

    Read from the tree rather than listed here, so renaming README.pypi.md or adding a
    second composite action moves the requirement with it instead of leaving this test
    asserting a filename nobody uses.
    """
    patterns = _paths_under(trigger)
    missing = [
        f
        for f in trigger_population()
        if not any(p == f or (p.endswith("/**") and f.startswith(p[:-3] + "/")) for p in patterns)
    ]
    assert missing == [], (
        f"{trigger} builds nothing when these files change: {missing}; each is consumed "
        f"by a workflow or pinned by a test, and the first place a breakage surfaces is "
        f"the release job, after the tag exists"
    )


def test_the_trigger_census_can_see_a_path_that_is_not_listed(tmp_path):
    """The red direction: the matcher must actually reject an unlisted path, or the
    assertion above is a check that cannot fail. `.github/actions/**` covers the composite
    action; `.github/workflows/**` does not, which is the exact gap measured today."""
    patterns = [".github/workflows/**", "pyproject.toml"]

    def covered(f):
        return any(p == f or (p.endswith("/**") and f.startswith(p[:-3] + "/"))
                   for p in patterns)

    assert covered("pyproject.toml")
    assert covered(".github/workflows/ci.yml")
    assert not covered(".github/actions/sheet-fonts/action.yml")
    assert not covered("verify.ps1")
    assert covered(".github/actions/sheet-fonts/action.yml") is False


def _code_only(script):
    """The script with `#` comment lines dropped -- naming a module in a comment is not
    reaching it, and this test is about what the leg RUNS."""
    return "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))


def test_the_clean_room_leg_reaches_every_lazily_imported_dependency():
    """`armature check` executes no function body, so it is green on a wheel that cannot run.

    The requirement is derived from the source, not written here: for each function-local
    third-party import, the leg must CALL one of the functions that performs it. A new lazy
    dependency fails this test until the clean-room leg calls through to it.
    """
    script = _code_only(clean_room_script())
    sites = lazy_import_call_sites()
    assert set(sites) == set(lazy_third_party_roots()), (
        f"a lazy dependency has no located call site: {sorted(set(lazy_third_party_roots()) - set(sites))}"
    )
    unreached = [
        f"{root} (imported by {', '.join(sorted(set(fns)))})"
        for root, fns in sorted(sites.items())
        if not any(fn in script for fn in fns)
    ]
    assert unreached == [], (
        f"the clean-room leg calls nothing that reaches {unreached}; it would pass on a "
        "wheel whose drawing and donor paths raise ModuleNotFoundError on first call"
    )


# -- the census tests: what must be true of EVERY workflow, not just the one that broke ----
#
# Each block below was added because the guard that should have caught the defect was
# parametrized over a hand-written list, or read one step in one file. A list a new workflow
# is not on, and a step a rename moves, are guards that stop guarding without going red. The
# population is therefore enumerated from the directory on every run.


def workflow_files():
    """Every workflow in `.github/workflows/`, enumerated — never a written-down list."""
    return sorted(f for f in os.listdir(WORKFLOWS) if f.endswith((".yml", ".yaml")))


def _workflow_level_permissions(text):
    """The `permissions:` block at column 0, or None. Not the same object as a job's."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() == "permissions:" and _indent(line) == 0:
            return "\n".join(block_at(lines, i))
    return None


@pytest.mark.parametrize("workflow", workflow_files())
def test_every_checkout_job_runs_on_a_declared_token_scope(workflow):
    """A job may inherit a scope only if there is one to inherit.

    `test_a_job_that_checks_out_declares_contents_read` `continue`s past any job with no
    job-level block, on the premise that it inherits the workflow-level grant. ci.yml has no
    workflow-level grant, so for its two jobs that premise was false and the check was
    vacuous — in the workflow that runs the most third-party code (`npm ci` over site/'s whole
    lockfile and its lifecycle scripts, four `pip install` lines, an apt install) and handed
    all of it a token whose scope this repository never stated.

    The population is read from the directory, so a fourth workflow is covered the day it
    lands rather than the day someone remembers to add it to a list.
    """
    text = _text(workflow)
    workflow_level = _workflow_level_permissions(text)
    for name in job_names(text):
        body = "\n".join(_job_lines(text, name))
        if "actions/checkout" not in body:
            continue
        job_level = re.search(r"(?m)^    permissions:\s*$", body) is not None
        effective = body if job_level else workflow_level
        assert effective is not None, (
            f"{workflow} job {name!r} checks out with no permissions block of its own and "
            "none at workflow level to inherit; the token's scope is whatever the "
            "organisation default happens to be"
        )
        assert re.search(r"(?m)^\s+contents:\s*(read|write)\s*$", effective), (
            f"{workflow} job {name!r} checks out under a permissions block that grants no "
            f"contents scope:\n{effective}"
        )


ACTIONS = os.path.join(REPO, ".github", "actions")
SHEET_FONTS = "./.github/actions/sheet-fonts"


def action_files():
    """Every composite action in `.github/actions/`."""
    out = []
    for root, _dirs, files in os.walk(ACTIONS):
        for f in files:
            if f in ("action.yml", "action.yaml"):
                out.append(os.path.join(root, f))
    return sorted(out)


def _all_run_scripts():
    """(source, script) for every `run:` in `.github/` — workflows and composite actions.

    Enumerated rather than listed: a step added to a fourth workflow, or to a second action,
    is held to the same rules the day it lands.
    """
    out = []
    sources = [(n, _text(n)) for n in workflow_files()]
    for path in action_files():
        with open(path, encoding="utf-8") as fh:
            sources.append((os.path.relpath(path, REPO).replace("\\", "/"), fh.read()))
    for name, text in sources:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not line.strip().startswith("run:"):
                continue
            if line.strip() in ("run: |", "run: |-"):
                body = block_at(lines, i)
                pad = min((_indent(x) for x in body if x.strip()), default=0)
                out.append((name, "\n".join(x[pad:] for x in body)))
            else:
                out.append((name, line.strip()[len("run: ") :]))
    return out


def jobs_that_run_the_suite():
    """(workflow, job) for every job whose steps run pytest — read, never listed."""
    out = []
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if re.search(r"(?m)^\s*(-\s*(name|run):.*)?$", body) and "pytest" in _code_only(body):
                out.append((name, job))
    return out


@pytest.mark.parametrize("workflow,job", jobs_that_run_the_suite())
def test_every_job_that_runs_the_suite_installs_the_sheet_fonts(workflow, job):
    """ci.yml refused to inherit the runner image's fonts; release.yml's gate did inherit them.

    Two tests hard-require a resolvable permitted face and FAIL rather than skip without one
    (measured: `tests/test_sheet_compose.py` 29 passed -> 2 failed, 27 passed with the
    resolver pointed at dead directories). release.yml's Install step says in its own comment
    that the release gate runs the SAME suite CI runs, "so a shorter list here would mean the
    gate is a weaker check than the one that already passed on the same commit" — and the font
    was in one list and not the other. By then `release: published` has fired: the tag and the
    release object exist and both registries are waiting.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    assert SHEET_FONTS in body, (
        f"{workflow} job {job!r} runs the suite without {SHEET_FONTS}; the two sheet tests "
        "that FAIL rather than skip without a permitted face depend on whatever the runner "
        f"image happens to carry:\n{body}"
    )


def test_the_font_dependency_has_one_implementation():
    """A copied step is a second implementation of one dependency, and lists that are copied fork.

    The package name may appear only inside the shared action; a workflow that installs it
    directly has started the fork again.
    """
    offenders = [name for name in workflow_files() if "fonts-liberation" in _text(name)]
    assert offenders == [], (
        f"these workflows install the font themselves instead of calling {SHEET_FONTS}: "
        f"{offenders}; two copies of one dependency list is how release.yml came to run the "
        "suite without a font in the first place"
    )


def sheet_font_action_faces():
    """The faces the action's own andon checks for, read out of its `FACES=` line.

    Not "somewhere in the file": the header comment quotes a FontError that names
    `arialbd.ttf`, and a check that reads the whole text passes on the strength of a comment.
    What the step VERIFIES is the list it loops over, so that is what is read.
    """
    with open(os.path.join(ACTIONS, "sheet-fonts", "action.yml"), encoding="utf-8") as fh:
        action = fh.read()
    match = re.search(r'(?m)^\s*FACES="([^"]+)"\s*$', action)
    assert match, "the sheet-fonts action no longer declares a FACES list to check"
    return match.group(1).split()


def composer_font_aliases():
    """`sheet_compose.FONT_ALIASES`, parsed out of the source rather than imported.

    `sheet_compose` imports PIL at module level. Importing it here would mean a checkout
    without Pillow could not COLLECT this file at all — and this file holds the tag gate, the
    pinning census and the permissions census, none of which have anything to do with fonts.
    A guard that cannot be collected is a guard that is not running.
    """
    import ast

    with open(os.path.join(REPO, "tools", "sheet_compose.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "FONT_ALIASES" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("sheet_compose no longer declares FONT_ALIASES")


@pytest.mark.parametrize("alias", sorted(composer_font_aliases()))
def test_the_font_action_supplies_a_face_for_every_alias_the_composers_need(alias):
    """Read out of `sheet_compose.FONT_ALIASES`, not written here.

    Adding a third alias to the composers, or renaming a fallback face, moves this
    requirement with it instead of leaving the action installing a face nobody resolves.
    """
    installed = sheet_font_action_faces()
    faces = composer_font_aliases()[alias]
    assert any(face in installed for face in faces), (
        f"the sheet-fonts action installs {installed} and none of them is one of "
        f"{list(faces)}, so `{alias}` resolves on a Linux runner only if the image happened "
        "to carry a face the repo never asked for"
    )


@pytest.mark.parametrize("source,script", [(s, c) for s, c in _all_run_scripts() if "apt-get install" in c])
def test_every_apt_install_refreshes_the_index_first(source, script):
    """A cached Packages entry can name a .deb the mirror has already superseded.

    The hosted images are rebuilt on a slower cadence than the archive rotates versions, so
    `apt-get install` against a stale index 404s — and with no `update`, no retry and no
    `|| true` that turns the whole job red for a reason that has nothing to do with the
    commit. The refresh must be in the SAME script: a shell chain can walk past a failing
    exit code, and a step somewhere else in the file is not one this step's failure implicates.
    """
    install = script.index("apt-get install")
    update = script.find("apt-get update")
    assert update != -1 and update < install, (
        f"{source} installs an apt package without refreshing the index first:\n{script}"
    )


def uses_refs():
    """(source, owner/name, ref, whole line) for every `uses:` under `.github/`.

    Enumerated from the directory, workflows and composite actions alike. A fourth workflow,
    or a step added to an existing one, is held to the pinning law the day it lands rather
    than the day someone remembers to extend a list.
    """
    out = []
    sources = [(n, _text(n)) for n in workflow_files()]
    for path in action_files():
        with open(path, encoding="utf-8") as fh:
            sources.append((os.path.relpath(path, REPO).replace("\\", "/"), fh.read()))
    for name, text in sources:
        for line in text.splitlines():
            match = re.match(r"\s*-?\s*uses:\s*(\S+)", line)
            if not match:
                continue
            spec = match.group(1)
            if spec.startswith("./"):
                continue  # a path into this repo, resolved by the checkout it rides on
            action, _, ref = spec.partition("@")
            out.append((name, action, ref, line.strip()))
    return out


@pytest.mark.parametrize("source,action,ref,line", uses_refs())
def test_no_action_is_resolved_from_a_branch_ref(source, action, ref, line):
    """A branch ref resolves at run time, so the code that runs is not the code reviewed.

    `pypa/gh-action-pypi-publish@release/v1` was exactly this until 2026-09-04 — in the job
    that performs the one step with no compensator.
    """
    assert ref, f"{source}: `{line}` names no ref at all, so it resolves to the default branch"
    assert not re.match(r"^(main|master|develop|release/.*|.*-branch)$", ref), (
        f"{source} resolves {action} from the branch ref {ref!r}; the code performing the "
        f"step is whatever that branch holds on the day it runs:\n{line}"
    )


#: WAVE 8, F-7331baff — the pin used to be applied to
#: `[row for row in uses_refs() if not row[1].startswith("actions/")]`, an UNCOMMENTED
#: exemption the file's own reasoning does not support. Enumerated 2026-09-04: 16 `uses:`
#: refs across the three workflows, 15 of them `actions/*` on mutable TAGS (checkout@v4,
#: setup-python@v5, setup-node@v4, upload-artifact@v4, download-artifact@v4,
#: upload-pages-artifact@v3, deploy-pages@v4), leaving exactly ONE subject for the law.
#: Two of the exempted refs sit inside `release.yml`'s npm job — the job that performs the
#: publish, the step this file itself calls "the one step with no compensator". A tag is
#: mutable, so the sibling test's own rationale ("a branch ref resolves at run time, so
#: the code that runs is not the code reviewed") applies to them word for word. The
#: exemption is gone: the law covers every `uses:` ref, and this branch is red on the 15
#: `actions/*` rows until the ci-packaging amend pins them (its brief: "every `uses:`
#: pinned by SHA, including `actions/*`, comment the version").
ALL_USES = uses_refs()
THIRD_PARTY = [row for row in ALL_USES if not row[1].startswith("actions/")]


def test_the_repo_still_has_an_action_to_hold_to_the_pin():
    """The population may not empty itself silently, and may not shrink to the one row an
    uncommented exemption happened to leave behind.

    A test parametrized over an empty list reports green, and a pinning law with no subject
    is the shape four prior gates in this repo took: passing N/N because N was zero.
    """
    assert ALL_USES, (
        "no action is used anywhere under .github/ any more; if that is deliberate this "
        "test and its siblings have no subject and should be retired deliberately, not "
        "left reporting green"
    )
    #: 16 on the tests branch; 17 on the merged tree (measured at the wave-8 merge: ci.yml 8
    #: rows of which 2 are local `./.github/actions/*` calls, pages.yml 4, release.yml 9 of
    #: which 2 are local — 21 `uses:` lines, 17 external rows). ci-packaging's estimate was
    #: 18; the census read 17 on the tree it exists to measure, so 17 is what stands.
    assert len(ALL_USES) == 17, [(r[0], r[1]) for r in ALL_USES]
    assert len(THIRD_PARTY) == 1, [(r[0], r[1]) for r in THIRD_PARTY]
    assert THIRD_PARTY[0][1] == "pypa/gh-action-pypi-publish", THIRD_PARTY


def test_a_fourth_party_action_cannot_hide_under_an_actions_shaped_name():
    """The reason the `actions/`-prefix split was never a safe exemption: the prefix is a
    GitHub ORG name, and any account may be called that on another host. Nothing in a
    `uses:` line proves who owns the repository behind it, which is why the law now reads
    every row rather than every row that does not look official."""
    for source, action, ref, line in ALL_USES:
        assert "/" in action, f"{source}: `{line}` names no owner at all"
        if action.startswith("actions/"):
            assert action.count("/") == 1, (
                f"{source}: {action!r} is not an `actions/<repo>` action despite the "
                f"prefix; the prefix is not provenance")


@pytest.mark.parametrize("source,action,ref,line", ALL_USES)
def test_an_action_is_pinned_to_a_commit_and_says_which_version(source, action, ref, line):
    """The npm half of this law is pinned by a test; the PyPI half was pinned by a comment.

    `npm install -g npm@^11.5.1` is held to a constraint by
    `test_the_publish_toolchain_is_not_resolved_on_release_day`. The action beside it — which
    performs the upload itself, the step with no compensator — carried a 40-hex SHA and a
    comment ending "Bump deliberately, by re-resolving", and nothing anywhere asserted it:
    substituting the branch ref it held until 2026-09-04 left both guarding tests green.

    The trailing `# vX.Y.Z` is part of the requirement, not decoration: a bare hash is
    unreadable, and a bump is reviewed by comparing the version a human can read.
    """
    assert re.fullmatch(r"[0-9a-f]{40}", ref), (
        f"{source} pins {action} to {ref!r}, which is not a full commit SHA; a tag or branch "
        f"is re-resolved on the day the step runs:\n{line}"
    )
    assert re.search(r"#\s*v?\d+\.\d+(\.\d+)?", line), (
        f"{source} pins {action} to a bare hash with no version beside it; nobody can review "
        f"a bump they cannot read:\n{line}"
    )


# -- the dependency scan: does it run on every event a lockfile change can arrive on? -------
#
# `if: github.event_name != 'push'` skipped ci.yml's site-build on EVERY push, and the comment
# above it justified that as "pages.yml already builds site/ ... for no coverage." Enumerated:
# ci.yml's site-build runs `npm ci`, `npm audit --audit-level=high` and `npm run build`;
# pages.yml's build runs `npm ci` and `npm run build` and nothing else. The claim was false by
# exactly one step, and that step is the repo's only dependency scan — ci.yml says so itself:
# "The repo's only dependency manifest is site/ ... this is the whole scannable surface."

#: ci.yml's own scan command, read rather than typed: the two must not drift, and the shape
#: changed when the scan moved ahead of the install it scans.
SCAN = run_script(step_containing(CI, "scan site dependencies")).strip()
CHANGED = "site/package-lock.json"


def _on_block(text):
    """{event: {'branches': [...], 'paths': [...]}} read out of the `on:` key."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "on:")
    events, event, key = {}, None, None
    for line in block_at(lines, start):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _indent(line) == 2 and stripped.endswith(":"):
            event, key = stripped[:-1], None
            events[event] = {}
            continue
        if _indent(line) == 4 and event is not None:
            if stripped.endswith(":"):
                key = stripped[:-1]
                events[event][key] = []
            elif ":" in stripped:  # `branches: [main]` on one line
                k, _, v = stripped.partition(":")
                events[event][k.strip()] = [
                    x.strip().strip("[]").strip("\"'") for x in v.split(",") if x.strip().strip("[]")
                ]
                key = None
            continue
        if _indent(line) >= 6 and stripped.startswith("- ") and key is not None:
            events[event][key].append(stripped[2:].strip().strip("\"'"))
    return events


def _pattern_hits(patterns, path):
    return any(p == path or (p.endswith("/**") and path.startswith(p[:-3] + "/")) for p in patterns)


def _eval_if(expr, ctx):
    """Evaluate a workflow `if:` expression for one context.

    Only the operators these workflows actually use, and an unmodelled `github.*` reference
    raises rather than quietly deciding the answer — a truth table built on a silently
    mis-evaluated condition would be worse than no truth table.
    """
    body = expr.strip()
    if body.startswith("${{") and body.endswith("}}"):
        body = body[3:-2].strip()
    for name in sorted(ctx, key=len, reverse=True):
        body = body.replace(name, repr(ctx[name]))
    body = body.replace("||", " or ").replace("&&", " and ")
    assert "github." not in body, f"unmodelled context in an if-expression: {expr!r}"
    return bool(eval(body, {"__builtins__": {}}, {}))  # noqa: S307 - the input is this repo's own YAML


def _job_if(text, job):
    for line in _job_lines(text, job):
        if line.strip().startswith("if:"):
            return line.strip()[len("if:") :].strip()
    return None


def site_jobs():
    """(workflow, job) for every job anywhere that installs site/'s lockfile."""
    out = []
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if "npm ci" in body:
                out.append((name, job))
    return out


ARRIVALS = [
    ("a push to main", {"github.event_name": "push", "github.ref": "refs/heads/main"}),
    ("a push to a branch", {"github.event_name": "push", "github.ref": "refs/heads/topic"}),
    ("a pull request", {"github.event_name": "pull_request", "github.ref": "refs/pull/7/merge"}),
]


def _jobs_that_run(ctx):
    """Which site jobs actually run for one arrival of a change to site/package-lock.json."""
    running = []
    for workflow, job in site_jobs():
        text = _text(workflow)
        triggers = _on_block(text)
        event = triggers.get(ctx["github.event_name"])
        if event is None:
            continue
        branches = event.get("branches")
        if branches and ctx["github.ref"] not in [f"refs/heads/{b}" for b in branches]:
            continue
        paths = event.get("paths")
        if paths and not _pattern_hits(paths, CHANGED):
            continue
        condition = _job_if(text, job)
        if condition is not None and not _eval_if(condition, ctx):
            continue
        running.append((workflow, job, "\n".join(_job_lines(text, job))))
    return running


@pytest.mark.parametrize("arrival,ctx", ARRIVALS)
def test_a_lockfile_change_is_scanned_however_it_arrives(arrival, ctx):
    """site/ is the repo's whole scannable surface; the scan must run on every way in.

    Two measured holes, both on the direct-push path this repo actually uses: a push to main
    changing the lockfile ran pages.yml (build and deploy, no audit) and ci.yml with
    site-build skipped, so nothing scanned it; and a push to a non-main branch matched neither
    pages.yml's `branches: [main]` nor ci.yml's skipped job, so site/ was built nowhere at all
    until a PR was opened.
    """
    running = _jobs_that_run(ctx)
    assert running, f"on {arrival}, a change to {CHANGED} builds site/ in no job at all"
    scanned = [f"{w}:{j}" for w, j, body in running if SCAN in body]
    assert scanned, (
        f"on {arrival} the jobs that build site/ are "
        f"{[f'{w}:{j}' for w, j, _ in running]} and none of them runs `{SCAN}`; a lockfile "
        "bump carrying a high-severity advisory reaches main with no scan having run on it"
    )


# -- the scan runs BEFORE the install it scans (F-a495cc98) --------------------------------
#
# `npm ci` runs every lifecycle script in the resolved tree by default, so a scan that runs
# after it reports a compromised dependency that has already had a shell on the runner —
# in pages.yml's case with `pages: write` and `id-token: write` in the environment until the
# permissions were narrowed. ci.yml calls site/ "the whole scannable surface" and the scan
# "scanned rather than attested", which is true of the report and not of the ordering: the
# gate could name the finding but not stop it from having run.
#
# `npm audit --package-lock-only` reads the lockfile and needs no node_modules, so the scan
# can be the first thing that touches site/ instead of the third.

#: Every place site/'s lockfile is installed, as measured 2026-09-04 by `site_jobs()` plus
#: the local script. A fourth installer fails the census before it fails the ordering.
LOCKFILE_INSTALLERS_TODAY = [("ci.yml", "site-build"), ("pages.yml", "build")]


def test_the_lockfile_installer_census_is_the_jobs_in_the_files():
    """Walked out of the workflows, never listed: `npm ci` in a job body is an installer."""
    assert site_jobs() == LOCKFILE_INSTALLERS_TODAY, (
        f"the jobs that install site/'s lockfile are {site_jobs()}; this file was written "
        f"against {LOCKFILE_INSTALLERS_TODAY}")


def _order_in(body, first, second):
    """(index of `first`, index of `second`) inside a text, -1 where absent.

    Comment lines are dropped first: the steps explain each other, so both commands appear
    in the prose above them and a raw `find` would read the ordering off an explanation
    rather than off what the job RUNS.
    """
    body = _code_only(body)
    return body.find(first), body.find(second)


@pytest.mark.parametrize("workflow,job", site_jobs())
def test_the_dependency_scan_runs_before_the_install_that_executes_the_tree(workflow, job):
    """The one control this repo has over its only dependency graph must precede the shell.

    What this looks like if wrong: the audit step sits below `npm ci`, reports a
    high-severity advisory, and every preinstall/install/postinstall in the resolved tree has
    already run on the runner under whatever token that job holds.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    install, scan = _order_in(body, "npm ci", "npm audit")
    assert scan != -1, f"{workflow}:{job} installs site/'s lockfile and never scans it"
    assert scan < install, (
        f"{workflow}:{job} runs `npm ci` at character {install} and `npm audit` at {scan}; "
        "by the time the scan reports, every lifecycle script in the resolved tree has run")
    assert "--package-lock-only" in body, (
        f"{workflow}:{job} scans without `--package-lock-only`, so the scan needs the "
        "node_modules the install creates and cannot precede it")


def test_the_ordering_check_goes_red_on_a_body_that_scans_after_installing():
    """The mutation: the shape the fix replaced must still fail this check.

    A census that only ever sees corrected inputs proves nothing about the direction it
    guards, so the pre-fix ordering is fed to the same comparison here.
    """
    before = "      - run: npm ci\n      - run: npm audit --audit-level=high\n"
    install, scan = _order_in(before, "npm ci", "npm audit")
    assert not (scan < install), "the ordering comparison cannot fail on the pre-fix shape"


# -- the second direction of the permissions census (F-0f644506) --------------------------
#
# `test_every_checkout_job_runs_on_a_declared_token_scope` asserts only that a contents scope
# is PRESENT. It has no direction that fails on a grant BROADER than the job's steps need,
# and pages.yml declared `contents: read`, `pages: write` and `id-token: write` at WORKFLOW
# level, so both jobs carried all three. The `build` job is the one that runs `npm ci` over
# site/'s whole lockfile — every install lifecycle script in the resolved tree — and it needs
# `contents: read` and nothing else. ci.yml's own permissions comment names this exact threat
# model ("this is the workflow that executes the most third-party code"), and release.yml puts
# `id-token: write` on the two publish jobs alone; pages.yml is the file that skipped the
# narrowing. Worst realistic consequence: a compromised transitive dependency's install script
# runs on a runner holding a token that can create a Pages deployment.

#: What a job must contain for a scope beyond `contents` to be one it USES. `contents` is the
#: read-only baseline a checkout authenticates with and is not policed for use here.
#: Re-derive rather than extend blindly: each entry is a step that consumes the scope.
SCOPE_MARKERS = {
    "pages": ("actions/deploy-pages",),
    "id-token": ("actions/deploy-pages", "gh-action-pypi-publish", "--provenance"),
}
BASELINE_SCOPE = "contents"


def _scopes_in(block):
    """{scope: level} for a `permissions:` block's own lines."""
    return {m.group(1): m.group(2)
            for m in re.finditer(r"(?m)^\s+([a-z-]+):\s*(read|write|none)\s*$", block or "")}


def granted_scopes():
    """(workflow, job, {scope: level}) for every job in every workflow, effective grant.

    A job-level block REPLACES the workflow-level one, so the effective grant is the job's
    own block where it has one and the file's block where it does not. Walked out of the
    directory, so a fourth workflow is covered the day it lands.
    """
    out = []
    for name in workflow_files():
        text = _text(name)
        file_level = _workflow_level_permissions(text)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if re.search(r"(?m)^    permissions:\s*$", body):
                block = "\n".join(named_block(body, "permissions", 4))
            else:
                block = file_level
            out.append((name, job, _scopes_in(block)))
    return out


def test_every_scope_this_repo_grants_has_a_recorded_consumer():
    """Fail-closed: a scope nobody wrote a marker for is not silently exempt from the check."""
    seen = {scope for _w, _j, scopes in granted_scopes() for scope in scopes}
    assert seen, "no job in any workflow declares a permissions scope any more"
    unknown = sorted(seen - set(SCOPE_MARKERS) - {BASELINE_SCOPE})
    assert unknown == [], (
        f"{unknown} is granted somewhere and has no row in SCOPE_MARKERS, so nothing says "
        "which step consumes it and the check below would pass it by default")


@pytest.mark.parametrize("workflow,job,scopes", granted_scopes(),
                         ids=lambda v: v if isinstance(v, str) else "")
def test_a_job_is_granted_only_the_scopes_its_own_steps_use(workflow, job, scopes):
    """Least privilege, in the direction the present census does not bound.

    What this looks like if wrong: the job that executes the most third-party code holds a
    token that can replace the public front door.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    unused = [
        scope for scope, level in sorted(scopes.items())
        if scope != BASELINE_SCOPE and level != "none"
        and not any(marker in body for marker in SCOPE_MARKERS[scope])
    ]
    assert unused == [], (
        f"{workflow} job {job!r} is granted {unused} and runs no step that consumes "
        f"{'it' if len(unused) == 1 else 'them'}; the scope is available to every line of "
        "third-party code the job executes")


def test_the_least_privilege_check_goes_red_on_an_unused_scope():
    """The mutation: the pre-fix grant, fed to the same comparison.

    pages.yml's `build` job held `pages: write` with no deploy step in it; a check that
    cannot fail on that shape is not the check this finding asked for.
    """
    scopes = {"contents": "read", "pages": "write", "id-token": "write"}
    body = "      - uses: actions/checkout@abc\n      - run: npm ci\n"
    unused = [s for s, level in sorted(scopes.items())
              if s != BASELINE_SCOPE and level != "none"
              and not any(m in body for m in SCOPE_MARKERS[s])]
    assert unused == ["id-token", "pages"], unused


# -- the pinning law, applied to the owner it exempted (F-aac4e7ec) -----------------------
#
# `THIRD_PARTY` above filters `uses_refs()` with `not row[1].startswith("actions/")` — an
# uncommented filter that removes an entire owner — and its sibling
# `test_no_action_is_resolved_from_a_branch_ref` accepts any non-branch ref, a moving major
# tag included. Measured before the fix: every `uses:` under `.github/` except
# `pypa/gh-action-pypi-publish` resolved from a mutable tag, and among them were the
# `actions/checkout` and `actions/setup-node` that run in the SAME job as
# `npm publish --provenance` under `id-token: write`, and the `actions/deploy-pages` that
# performs the deployment. A moved v4 tag runs new code inside the job holding the OIDC
# minting scope, in the one step with no compensator.
#
# The exemption may have been a deliberate trust decision about GitHub-owned actions;
# nothing in the workflows or in this file recorded one, so it read as a gap. It is closed
# rather than documented: the same law, over every `uses:` in the tree.
#
# The population here is `uses_refs()` — walked from `.github/`, workflows and composite
# actions alike — and it is a SUPERSET of `THIRD_PARTY`, which keeps its own two tests. The
# overlap is deliberate: retiring the narrow pair would leave the "population may not empty
# itself" check with nothing to say about third-party actions specifically.

#: Every external action this repo uses, as measured 2026-09-04. Asserted so a new `uses:`
#: fails HERE — naming the action and the file — rather than joining a check silently.
EVERY_USE_TODAY = sorted({
    ("ci.yml", "actions/checkout"),
    ("ci.yml", "actions/setup-node"),
    ("ci.yml", "actions/setup-python"),
    ("pages.yml", "actions/checkout"),
    ("pages.yml", "actions/deploy-pages"),
    ("pages.yml", "actions/setup-node"),
    ("pages.yml", "actions/upload-pages-artifact"),
    ("release.yml", "actions/checkout"),
    ("release.yml", "actions/download-artifact"),
    ("release.yml", "actions/setup-node"),
    ("release.yml", "actions/setup-python"),
    ("release.yml", "actions/upload-artifact"),
    ("release.yml", "pypa/gh-action-pypi-publish"),
})


def test_the_pinning_census_is_every_external_action_in_the_tree():
    """Size and membership, before the property. `./` paths ride the checkout and are not refs."""
    seen = sorted({(source, action) for source, action, _ref, _line in uses_refs()})
    assert seen == EVERY_USE_TODAY, (
        "the set of external actions under .github/ has changed; each new one needs a SHA "
        "and a version comment before this list is updated:\n  "
        + "\n  ".join(f"{s}: {a}" for s, a in sorted(set(seen) ^ set(EVERY_USE_TODAY))))


@pytest.mark.parametrize("source,action,ref,line", uses_refs())
def test_every_action_is_pinned_to_a_commit_and_says_which_version(source, action, ref, line):
    """The law release.yml's PyPI comment states in general terms, applied generally.

    "A ref that resolves at run time means the code performing the step is not the code last
    reviewed" is a property of the ref, not of who owns the repository it points at. The
    trailing `# vX.Y.Z` is part of the requirement: a bare hash is unreadable, and a bump is
    reviewed by comparing the version a human can read.
    """
    assert re.fullmatch(r"[0-9a-f]{40}", ref), (
        f"{source} pins {action} to {ref!r}, which is not a full commit SHA; a tag is "
        f"re-resolved on the day the step runs — including inside the jobs that publish:\n{line}")
    assert re.search(r"#\s*v?\d+\.\d+(\.\d+)?", line), (
        f"{source} pins {action} to a bare hash with no version beside it; nobody can review "
        f"a bump they cannot read:\n{line}")


def test_the_pinning_check_goes_red_on_a_moving_major_tag():
    """The mutation: the shape every `actions/*` line held until today.

    `test_no_action_is_resolved_from_a_branch_ref` passes on `v4` — it only refuses branch
    refs — so the direction that matters here is exercised on its own.
    """
    assert not re.fullmatch(r"[0-9a-f]{40}", "v4"), "a major tag reads as a pinned commit"
    assert not re.search(r"#\s*v?\d+\.\d+(\.\d+)?", "      - uses: actions/checkout@v4"), (
        "an unpinned line reads as carrying a reviewable version comment")


# -- the clean-room leg, and the toolchain that builds it (F-60ab1bd7, F-7fa3017c) --------
#
# release.yml's verify job ran `python -m build` and `twine check dist/*` and nothing
# installed either artifact. ci.yml's python-tests ran the same build AND a clean venv
# install plus a probe that calls through to every function-local dependency; ci.yml's own
# comment records why the weaker form is not enough -- `armature check` printed "all modules
# resolved" and exited 0 on a wheel whose drawing and donor paths raised ModuleNotFoundError
# on first call. So the artifact handed to `pypa/gh-action-pypi-publish`, the one step in
# this repository with no compensator, was the one artifact never installed anywhere in the
# workflow that publishes it.
#
# The leg now lives in `.github/actions/clean-room` and both jobs call it. The population
# below is therefore every job that PRODUCES a distribution, walked out of the tree with
# local composite actions expanded -- not ci.yml alone, and not a list.


def _run_scripts_in(text):
    """Every `run:` script in a YAML text, dedented."""
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("run:"):
            continue
        if line.strip() in ("run: |", "run: |-"):
            body = block_at(lines, i)
            pad = min((_indent(x) for x in body if x.strip()), default=0)
            out.append("\n".join(x[pad:] for x in body))
        else:
            out.append(line.strip()[len("run: ") :])
    return out


def _local_action_scripts(ref):
    """The run scripts of a `uses: ./path` composite action in this repository."""
    base = os.path.join(REPO, ref[2:].replace("/", os.sep))
    for candidate in ("action.yml", "action.yaml"):
        path = os.path.join(base, candidate)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                return _run_scripts_in(fh.read())
    raise AssertionError(f"{ref} is used but no action file exists at {base}")


def job_scripts(workflow, job):
    """Every script a job RUNS, including the ones inside the local actions it calls.

    A step that moved into a composite action is still a step of the job; a check that reads
    only the job body would go quiet the day a leg was lifted, which is how the trigger-path
    hole opened one directory over.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    scripts = _run_scripts_in(body)
    for line in body.splitlines():
        match = re.match(r"\s*-?\s*uses:\s*(\./\S+)", line)
        if match:
            scripts.extend(_local_action_scripts(match.group(1)))
    return scripts


def clean_room_script():
    """The one script anywhere under `.github/` that builds a clean venv.

    Derived, so lifting the leg into an action (or back out of one) moves every check that
    reads it. Exactly one is required: two would be two implementations of one gate.
    """
    hits = [(source, script) for source, script in _all_run_scripts() if "-m venv" in script]
    assert len(hits) == 1, (
        f"{len(hits)} scripts under .github/ build a clean venv; the leg that catches a "
        f"wheel that cannot run must have one implementation: {[s for s, _ in hits]}")
    return hits[0][1]


def jobs_that_produce_a_distribution():
    """(workflow, job) for every job that builds a wheel or an sdist -- walked, not listed."""
    out = []
    for name in workflow_files():
        for job in job_names(_text(name)):
            if any("-m build" in _code_only(s) for s in job_scripts(name, job)):
                out.append((name, job))
    return out


#: Measured 2026-09-04. The release gate built a distribution and installed nothing.
DISTRIBUTION_JOBS_TODAY = [("ci.yml", "python-tests"), ("release.yml", "verify")]


def test_the_distribution_job_census_is_the_jobs_that_build_one():
    assert jobs_that_produce_a_distribution() == DISTRIBUTION_JOBS_TODAY, (
        f"the jobs that build a distribution are {jobs_that_produce_a_distribution()}; this "
        f"file was written against {DISTRIBUTION_JOBS_TODAY}")


@pytest.mark.parametrize("workflow,job", jobs_that_produce_a_distribution())
def test_every_job_that_builds_a_distribution_runs_it_from_a_clean_install(workflow, job):
    """A build and a metadata check are not a claim that the artifact works.

    What this looks like if wrong: a wheel whose console script is missing, or whose lazy
    imports are unsatisfiable, passes `twine check` and reaches a registry -- from the job
    whose whole purpose is to be the last gate before that happens.
    """
    scripts = "\n".join(job_scripts(workflow, job))
    assert "-m venv" in scripts, (
        f"{workflow}:{job} builds a distribution and never installs one; `twine check` reads "
        "the METADATA and no more")
    assert "site-packages" in scripts, (
        f"{workflow}:{job} installs into a clean venv without checking it imported the WHEEL; "
        "the checkout is sitting one directory up")


def test_the_clean_room_is_one_implementation_called_by_both():
    """A copied leg is a second implementation of one gate, and copies fork.

    `.github/actions/sheet-fonts` exists because the release gate ran the suite with no
    font: the dependency was in one list and not the other. The packaging leg was the same
    shape one step later -- present in ci.yml, absent from the job that publishes.
    """
    callers = sorted(
        (workflow, job)
        for workflow in workflow_files()
        for job in job_names(_text(workflow))
        if "./.github/actions/clean-room" in "\n".join(_job_lines(_text(workflow), job))
    )
    assert callers == DISTRIBUTION_JOBS_TODAY, (
        f"the clean-room action is called by {callers}; every job that builds a distribution "
        f"must call it, and today those are {DISTRIBUTION_JOBS_TODAY}")


# The toolchain that produces the artifact, held to a version the way npm already is.

def _install_tokens(script):
    """Package tokens of every `pip install` / `npm install -g` line in a script."""
    tokens = []
    for line in _code_only(script).splitlines():
        stripped = line.strip()
        if "pip install" not in stripped and "npm install" not in stripped:
            continue
        after = stripped.split("install", 1)[1]
        for raw in after.split():
            token = raw.strip("'").strip('"')
            if token.startswith("-"):
                continue
            # A local artifact path is not a registry resolution: `dist/*.whl` IS the thing
            # the constraint exists to protect, and pinning a filename would be nonsense.
            if "/" in token or token.endswith((".whl", ".tar.gz")):
                continue
            # Nor is a runner-side variable. `npm install --prefix "$PREFIX" "$TARBALL"` in
            # `.github/actions/npm-clean-room` expands to a scratch directory and to the
            # tarball just packed — the same "local artifact" exemption one substitution
            # later, and a `$` can never begin a package name.
            if token.startswith("$"):
                continue
            tokens.append(token)
    return tokens


def toolchain_tokens():
    """Every package installed by a job that produces or publishes a distribution.

    The population is the jobs, walked: the ones that build (above) plus the ones that hand
    an artifact to a registry. What is installed inside them is what runs on release day.
    """
    jobs = set(jobs_that_produce_a_distribution())
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if "npm publish" in body or "gh-action-pypi-publish" in body:
                jobs.add((name, job))
    tokens = {}
    for workflow, job in sorted(jobs):
        for script in job_scripts(workflow, job):
            for token in _install_tokens(script):
                tokens.setdefault(token, []).append(f"{workflow}:{job}")
    return tokens


#: Installed without a version constraint, deliberately, as of 2026-09-04. None of these
#: PRODUCES or UPLOADS the artifact: `pip` is the installer itself, and numpy/pillow/pytest
#: are the suite's own dependencies, whose byte-stable pins (opencv, matplotlib) carry `==`
#: where the golden frames need them. `build`, `twine` and `npm` are the three tools that
#: make or move the artifact, and all three are constrained.
UNCONSTRAINED_BY_DESIGN = {"pip", "numpy", "pillow", "pytest"}


def test_the_toolchain_exemptions_are_still_installed_somewhere():
    """An exemption for a package nobody installs is a row that stopped meaning anything."""
    stale = sorted(UNCONSTRAINED_BY_DESIGN - set(toolchain_tokens()))
    assert stale == [], (
        f"{stale} is exempt from the constraint rule and is installed by no job that "
        "produces or publishes a distribution")


def test_every_tool_that_makes_or_moves_the_artifact_is_held_to_a_version():
    """A tool resolved on the day is not the tool that was verified.

    release.yml already says this about npm -- a breaking major lands in the publish job
    with no local reproduction of the version that ran -- and `build` and `twine` sat in the
    same job under the same reasoning with nothing asserting a version. A `build` release
    that changed sdist file selection would change the published artifact between two runs
    of the same tag.
    """
    tokens = toolchain_tokens()
    unconstrained = sorted(
        token + " (" + ", ".join(sorted(set(where))) + ")"
        for token, where in tokens.items()
        if not re.search(r"[=<>~^@]", token) and token not in UNCONSTRAINED_BY_DESIGN
    )
    assert unconstrained == [], (
        f"these are resolved fresh in a job that produces or publishes the artifact: "
        f"{unconstrained}")


def test_the_constraint_check_goes_red_on_a_bare_build_tool():
    """The mutation: the pre-fix install line, fed to the same comparison."""
    before = "python -m pip install --upgrade build twine\n"
    bare = [t for t in _install_tokens(before)
            if not re.search(r"[=<>~^@]", t) and t not in UNCONSTRAINED_BY_DESIGN]
    assert bare == ["build", "twine"], bare


# -- the runtimes this package promises, and the ones it runs (F-e110bcf6) ----------------
#
# Six runtime configurations were declared and one was exercised. pyproject declared
# `requires-python = ">=3.10"` and classifiers for 3.10 through 3.13; npm/package.json
# declared `"node": ">=18"`. Enumerated across all three workflows: ci.yml pinned python
# "3.13" and node 22, release.yml pinned "3.13" and "22", and there was no matrix anywhere.
# So 3.10, 3.11, 3.12 and Node 18 were public promises nothing ran.
#
# The floor is the end that matters. A version BETWEEN two exercised versions is an
# interpolation; a version BELOW the exercised floor is an extrapolation, and the failure
# it hides is a user installing a package whose metadata promised support and hitting an
# error the repo has never run. So the rule here is: the declared floor runs, the declared
# ceiling runs, and nothing is claimed outside that interval.
#
# What moved rather than being covered: the Python floor came UP to 3.11, because two files
# in this suite (`tests/test_ci_workflows.py` and `tests/test_packaging.py`) import
# `tomllib`, which landed in 3.11 — the suite that would prove 3.10 cannot collect on it.
# Narrowing a promise to what is run is the honest half of this finding's fix.

with open(os.path.join(REPO, "npm", "package.json"), encoding="utf-8") as _fh:
    NPM_PACKAGE = json.load(_fh)


def _version_tuple(text):
    return tuple(int(part) for part in text.strip().split(".") if part.isdigit())


def declared_python_floor():
    """The `requires-python` floor, e.g. `>=3.11` -> (3, 11)."""
    spec = PYPROJECT["project"]["requires-python"]
    match = re.search(r">=\s*(\d+\.\d+)", spec)
    assert match, f"requires-python is {spec!r} and states no floor this check can read"
    return _version_tuple(match.group(1))


def classifier_pythons():
    """Every `Programming Language :: Python :: X.Y` version claimed, as tuples."""
    out = set()
    for row in PYPROJECT["project"]["classifiers"]:
        match = re.fullmatch(r"Programming Language :: Python :: (\d+\.\d+)", row)
        if match:
            out.add(_version_tuple(match.group(1)))
    return out


def declared_node_floor():
    """The npm launcher's `engines.node` floor, e.g. `>=18` -> (18,)."""
    spec = NPM_PACKAGE["engines"]["node"]
    match = re.search(r">=\s*(\d+(?:\.\d+)*)", spec)
    assert match, f"engines.node is {spec!r} and states no floor this check can read"
    return _version_tuple(match.group(1))


def _versions_declared_for(key):
    """Every literal value of `<key>-version:` anywhere in the workflows.

    Both forms are read: a scalar (`python-version: "3.13"`) and an inline matrix list
    (`python-version: ["3.11", "3.13"]`). A `${{ matrix.* }}` reference is a pointer, not a
    version, and is skipped — the list it points at is read where it is written.
    """
    out = set()
    for name in workflow_files():
        for line in _text(name).splitlines():
            match = re.search(key + r"-version:\s*(.+?)\s*$", line)
            if not match:
                continue
            value = match.group(1)
            if "${{" in value:
                continue
            for piece in value.strip("[]").split(","):
                piece = piece.strip().strip('"').strip("'")
                if re.fullmatch(r"\d+(\.\d+)*", piece):
                    out.add(_version_tuple(piece))
    return out


def test_the_declared_python_interval_is_the_one_ci_runs():
    """Floor and ceiling both exercised, and no classifier outside them.

    What this looks like if wrong: `requires-python = ">=3.10"` with a single 3.13 job — a
    promise about four interpreters, one of which has ever been run.
    """
    exercised = {v for v in _versions_declared_for("python") if v[0] == 3}
    assert exercised, "no workflow pins a python version this check can read"
    floor, ceiling = declared_python_floor(), max(classifier_pythons())
    assert floor in exercised, (
        f"requires-python declares a floor of {floor} and no job runs it; the versions run "
        f"are {sorted(exercised)}")
    assert ceiling in exercised, (
        f"the classifiers claim up to {ceiling} and no job runs it; the versions run are "
        f"{sorted(exercised)}")
    outside = sorted(v for v in classifier_pythons() if v < floor or v > ceiling)
    assert outside == [], (
        f"these classifiers claim versions outside the interval CI exercises: {outside}")
    below = sorted(v for v in classifier_pythons() if v < min(exercised))
    assert below == [], (
        f"these classifiers are BELOW the lowest version any job runs: {below}; a version "
        "under the exercised floor is an extrapolation, not an interpolation")


def test_the_launchers_declared_node_floor_is_the_one_ci_runs():
    """`engines.node` is what npm enforces at install time on a user's machine."""
    exercised = {v for v in _versions_declared_for("node")}
    assert exercised, "no workflow pins a node version this check can read"
    floor = declared_node_floor()
    assert floor in exercised, (
        f"npm/package.json declares engines.node {NPM_PACKAGE['engines']['node']!r} and no "
        f"job runs {floor[0]}; the versions run are {sorted(exercised)}")


def test_the_runtime_check_goes_red_on_a_floor_nothing_runs():
    """The mutation: the declaration this repo carried until today.

    A promise of 3.10 with only a 3.13 job must fail the same comparison, or the check is
    reporting green on the shape it was written to catch.
    """
    exercised = {(3, 13)}
    assert (3, 10) not in exercised, "the floor comparison cannot fail"
    assert sorted(v for v in {(3, 10), (3, 11)} if v < min(exercised)) == [(3, 10), (3, 11)]



# -- the OTHER build inputs: every file the suite opens by path (F-59883264) ---------------
#
# The census above reads pyproject's build inputs, which is the population of "files the
# PACKAGE is built from". The files the WORKFLOWS are built from were in no filter at all.
# Measured by evaluating `_on_block()` / `_pattern_hits()` over every workflow before the
# fix: `.github/actions/sheet-fonts/action.yml` -> NO WORKFLOW RUNS, `verify.ps1` -> NO
# WORKFLOW RUNS, `.gitignore` -> NO WORKFLOW RUNS. That is a seam wave 6 opened: the font
# install moved OUT of the two workflows INTO a composite action both now depend on, and it
# moved out from under the only filter that covered it. The guards that would catch a break
# all live under `tests/**`, so they do not run on the change they exist to guard.
#
# The population is therefore derived from the suite itself: every repo path a test module
# names as an `os.path.join` of string literals off a path constant it defines. That is what
# "the suite guards" means mechanically — if a test opens it, a change to it can turn the
# suite red, and CI must run.

TESTS_DIR = os.path.join(REPO, "tests")


def _joined_relpath(node, env):
    """`os.path.join(BASE, "a", "b")` -> `BASE/a/b`, or None if any part is not resolvable."""
    if not isinstance(node, ast.Call):
        return None
    fn = node.func
    if not (isinstance(fn, ast.Attribute) and fn.attr == "join"
            and isinstance(fn.value, ast.Attribute) and fn.value.attr == "path"):
        return None
    parts = []
    for i, arg in enumerate(node.args):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            parts.append(arg.value)
        elif i == 0 and isinstance(arg, ast.Name) and arg.id in env:
            if env[arg.id]:
                parts.append(env[arg.id])
        else:
            return None
    return "/".join(p.strip("/") for p in parts if p.strip("/"))


def paths_the_suite_guards():
    """Every existing repo path a test module names, walked out of `tests/**` by AST.

    Derivation, stated because a census whose population is typed is the defect class this
    file keeps finding: each test module is parsed; `REPO` seeds an environment of path
    constants; every `NAME = os.path.join(...)` of literals off a known constant extends it
    (two passes, so a constant defined below its first use still resolves); then every
    `os.path.join(...)` in the module is resolved the same way and kept if it exists on
    disk. Paths that resolve through a variable filename are not resolvable this way and are
    not claimed — this is a floor on what the suite reads, not a ceiling.
    """
    found = set()
    for name in sorted(os.listdir(TESTS_DIR)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(TESTS_DIR, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        env = {"REPO": ""}
        for _ in range(2):
            for node in ast.walk(tree):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)):
                    rel = _joined_relpath(node.value, env)
                    if rel is not None:
                        env[node.targets[0].id] = rel
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                rel = _joined_relpath(node, env)
                if rel and os.path.exists(os.path.join(REPO, rel)):
                    found.add(rel)
    return sorted(found)


#: The population as measured 2026-09-04 by the walk above. Asserted, so a test that starts
#: reading a new repo file fails HERE — naming the file and the filter it needs — rather
#: than reaching main green-by-absence.
GUARDED_TODAY = [
    ".github/actions",
    ".github/actions/sheet-fonts/action.yml",
    ".github/workflows",
    ".gitignore",
    # MANIFEST.in joined with the sdist fix-up (wave 8): tests/test_packaging.py opens it by
    # path, and a packaging input is a CI input — it is on both triggers.
    "MANIFEST.in",
    "docs/experiments/E04-the-between-generation-floor.md",
    "docs/index/armature.db",
    "npm/bin/armature.mjs",
    "npm/package.json",
    "pyproject.toml",
    "specs/E09-A3-seeds.json",
    "specs/E09-seeds.json",
    "specs/E13-prompt.json",
    "specs/E13-seeds.json",
    "tests",
    "tests/blender/check_floor_material.py",
    "tests/blender/check_ortho_convention.py",
    "tests/blender/check_plate_composite.py",
    "tests/blender/check_pose_arc_roundtrip.py",
    "tests/blender/check_visibility.py",
    "tests/blender/make_synthetic_run.py",
    "tools",
    "tools/armature_core",
    # the next two and `build_payload.py`/`fetch_run.py` joined at the wave-8 merge: sibling
    # branches' censuses open these sources by path (core-solvers' andon walk, builders' exit
    # convention). All under `tools/**`, which both triggers already carry.
    "tools/armature_core/framing.py",
    "tools/armature_core/walk.py",
    "tools/armature_index.py",
    "tools/build_payload.py",
    "tools/fetch_run.py",
    "tools/make_test_armature.py",
    "tools/sheet_compose.py",
    "verify.ps1",
]


def test_the_guarded_path_census_is_the_one_the_suite_actually_opens():
    """Size and membership before the property — a census that cannot grow is not one."""
    assert paths_the_suite_guards() == GUARDED_TODAY, (
        "the set of repo files the suite opens by path has changed; each new member needs a "
        "push and a pull_request filter that covers it before this list is updated:\n  "
        + "\n  ".join(sorted(set(paths_the_suite_guards()) ^ set(GUARDED_TODAY))))


def _probe_path(rel):
    """What a member of the population stands for when matched against a filter.

    A directory the suite walks stands for the files INSIDE it — a filter covers
    `tests/**`, never the bare string `tests` — so a directory member is probed as one file
    under it. A file member stands for itself.
    """
    return rel + "/x" if os.path.isdir(os.path.join(REPO, rel)) else rel


def _unfiltered(paths, trigger):
    """The members of `paths` that match no pattern in ci.yml's `trigger` filter."""
    patterns = _paths_under(trigger)
    return [p for p in paths if not _pattern_hits(patterns, _probe_path(p))]


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_ci_runs_on_every_file_the_suite_guards(trigger):
    """A file a test opens, that no filter covers, is a guard that cannot run on its subject."""
    missing = _unfiltered(paths_the_suite_guards(), trigger)
    assert missing == [], (
        f"{trigger} runs nothing when these change, and a test in tests/ reads every one of "
        f"them: {missing}; the guard does not run on the change it exists to guard"
    )


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_the_trigger_census_goes_red_on_a_guarded_file_no_filter_covers(trigger):
    """The mutation: a member added to the population without the property must fail.

    A census that reports green over a population it cannot fail on is the shape this wave
    exists to close, so the failing direction is exercised rather than assumed.
    """
    intruder = "no-such-directory-8481819/guarded.txt"
    assert _unfiltered([intruder], trigger) == [intruder], (
        f"the {trigger} filter claims to cover {intruder!r}; the check cannot fail")


# -- the npm half of the clean room (wave 10, F-3729edd4) ---------------------------------
#
# The Python wheel is built, installed into a clean venv and RUN from that install before it
# is published; `.github/actions/clean-room/action.yml` exists because "the artifact handed to
# publish was the one artifact never installed in the workflow that publishes it". The npm
# package is published irreversibly in the same workflow and was never packed, never
# installed and never run from an install anywhere in this repository. Its only coverage was
# `npm test` — `node bin/armature.mjs --node-selftest` — run from the CHECKOUT, which consults
# neither `bin` nor `files` nor the tarball.
#
# Measured 2026-09-04 on a scratch copy of npm/ with the `bin` map pointed at
# `bin/armature.msj`: `npm test` printed `armature launcher ok` and exited 0, `npm pack`
# produced the same four-file tarball, and `npm install --prefix <scratch> <tarball>` reported
# `added 1 package` while creating NO `node_modules/.bin` at all — the command the package
# exists to install did not exist, with every gate in the workflow green.
#
# THE NODE THIS CENSUS KEYS ON: `npm pack` inside a run script of a job, with local composite
# actions expanded. It does not key on the job's name, and it deliberately does not key on
# `npm test`, because running the launcher out of the checkout is exactly the coverage that
# was green on the defect.


def _job_needs(text, job):
    """The job names in a job's `needs:` key — scalar or inline list."""
    for line in _job_lines(text, job):
        stripped = line.strip()
        if stripped.startswith("needs:"):
            value = stripped[len("needs:") :].strip()
            return [
                piece.strip().strip("[]").strip("\"'")
                for piece in value.split(",")
                if piece.strip().strip("[]")
            ]
    return []


def npm_pack_jobs():
    """(workflow, job) for every job that packs the npm package — walked, never listed."""
    out = []
    for name in workflow_files():
        for job in job_names(_text(name)):
            if any("npm pack" in _code_only(s) for s in job_scripts(name, job)):
                out.append((name, job))
    return out


def npm_publish_jobs():
    """(workflow, job) for every job that hands the npm package to the registry."""
    out = []
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            if "npm publish" in _code_only("\n".join(_job_lines(text, job))):
                out.append((name, job))
    return out


#: Measured 2026-09-04. Before this wave `npm_pack_jobs()` was EMPTY — the census's own red
#: proof — while `npm_publish_jobs()` was already this.
NPM_PACK_JOBS_TODAY = [("ci.yml", "launcher"), ("release.yml", "verify")]
NPM_PUBLISH_JOBS_TODAY = [("release.yml", "npm")]


def test_the_npm_pack_and_publish_censuses_are_the_jobs_in_the_files():
    """Size and membership before the property, both directions."""
    assert npm_pack_jobs() == NPM_PACK_JOBS_TODAY, (
        f"the jobs that pack the npm package are {npm_pack_jobs()}; this file was written "
        f"against {NPM_PACK_JOBS_TODAY}")
    assert npm_publish_jobs() == NPM_PUBLISH_JOBS_TODAY, (
        f"the jobs that publish the npm package are {npm_publish_jobs()}; this file was "
        f"written against {NPM_PUBLISH_JOBS_TODAY}")


def npm_clean_room_script():
    """The one script anywhere under `.github/` that packs the npm package.

    Derived, so lifting the leg into an action (or back out of one) moves every check that
    reads it. Exactly one is required: two would be two implementations of one gate, which
    is how the font dependency and the packaging leg both forked.
    """
    hits = [(source, script) for source, script in _all_run_scripts()
            if "npm pack" in _code_only(script)]
    assert len(hits) == 1, (
        f"{len(hits)} scripts under .github/ pack the npm package; the leg that catches a "
        f"`bin`/`files` defect must have one implementation: {[s for s, _ in hits]}")
    return hits[0][1]


def _runs_the_installed_shim(script):
    """True when a script packs the package, installs THE TARBALL into a scratch prefix, and
    invokes the shim npm created there.

    All three clauses matter and each has a measured failure: `npm test` does none of them;
    packing without installing proves only that a tarball can be written; installing without
    invoking `node_modules/.bin/armature` is the exact state measured above, where npm
    reported `added 1 package` and created no bin directory at all.
    """
    code = _code_only(script)
    return (
        "npm pack" in code
        and re.search(r"npm\s+(install|i)\b[^\n]*--prefix", code) is not None
        and "node_modules/.bin/armature" in code
        and "--node-selftest" in code
    )


def test_the_npm_package_is_run_from_a_clean_install_before_it_is_published():
    """A published version is taken forever; a `bin` map nothing resolves is silent.

    What this looks like if wrong: `@mcptoolshop/armature-studio@X.Y.Z` lands on the
    registry, provenance attested, and `npx armature` provides no command.
    """
    assert _runs_the_installed_shim(npm_clean_room_script()), (
        "the npm leg does not pack, install and run the package from its tarball:\n"
        + npm_clean_room_script())


@pytest.mark.parametrize("workflow,job", npm_publish_jobs())
def test_every_job_that_publishes_the_npm_package_is_gated_by_the_pack_and_install_leg(workflow, job):
    """The gate must be upstream of the irreversible step, not beside it."""
    packers = {j for w, j in npm_pack_jobs() if w == workflow}
    reachable = set(_job_needs(_text(workflow), job)) | {job}
    assert packers & reachable, (
        f"{workflow}:{job} publishes the npm package and neither it nor any job it needs "
        f"({sorted(reachable)}) packs and installs the tarball first; the jobs that do are "
        f"{sorted(packers)}")


def test_the_npm_clean_room_check_goes_red_on_the_coverage_this_repo_had():
    """The mutation set: three scripts that must NOT satisfy the predicate.

    A check that cannot fail is not a check, so the shapes measured green-on-the-defect are
    fed to the same predicate the leg is judged by.
    """
    assert not _runs_the_installed_shim("npm test"), (
        "`npm test` reads as a clean install; it runs bin/armature.mjs out of the checkout")
    assert not _runs_the_installed_shim("npm pack\nnode bin/armature.mjs --node-selftest"), (
        "packing and then running the CHECKOUT reads as a clean install")
    assert not _runs_the_installed_shim(
        'npm pack\nnpm install --prefix "$RUNNER_TEMP/x" ./pkg.tgz'), (
        "installing without invoking node_modules/.bin/armature reads as a clean install; "
        "that is the exact state where npm reported `added 1 package` and made no bin")
    assert not _runs_the_installed_shim(
        '# npm pack\n# npm install --prefix x\n# node_modules/.bin/armature --node-selftest'), (
        "a commented-out leg reads as a leg that runs")


# -- the sdist assertions must RUN where they gate (wave 10, F-3abdf3a5) ------------------
#
# `tests/test_packaging.py` holds the two tests that pin what the published sdist carries —
# the whole point of the wave-8 MANIFEST.in fix-up — and neither could run in CI or in the
# release gate, because the tool they need was installed AFTER the suite. `_build_sdist`
# shells `[sys.executable, "-m", "build", "--sdist", ...]`; ci.yml installed
# `pip numpy pillow pytest opencv-python-headless matplotlib` and ran the suite twice, and
# only THEN reached `./.github/actions/clean-room`, whose script installs `build>=1.5,<2`.
# release.yml had the same order and the same gap.
#
# Measured both directions on this tree with the repo venv: with `build` shadowed by a module
# that exits non-zero, `pytest tests/test_packaging.py -k sdist -rs` reported `2 skipped`; with
# the real build 1.5.0 present, `2 passed`. The narrow half that held is that the first sdist
# test asserts MANIFEST.in exists BEFORE the skip, so DELETING the file was caught. Removing
# `prune tests` from it was not, and `twine check dist/*` reads metadata, never the archive.
#
# THE NODE THIS CENSUS KEYS ON: the ORDER of the run scripts written directly in a job body.
# Composite-action scripts are deliberately excluded — `job_scripts()` appends them after the
# body whatever line the `uses:` sits on, which is right for "does this job run X" and wrong
# for "does X run before Y", and getting that backwards is how the tool came to be installed
# after the suite that needs it.


def _body_scripts(workflow, job):
    """Every `run:` script written DIRECTLY in a job body, in file order."""
    return _run_scripts_in("\n".join(_job_lines(_text(workflow), job)))


def suite_modules_that_build_a_distribution():
    """Every test module that shells out to `python -m build` — walked over `tests/**`.

    Keyed on the argv LIST the module hands `subprocess`, not on the word `build` appearing
    in a file: `build` is also a directory, a `.gitignore` line and half the workflow
    vocabulary, and a census keyed on the word would be green on a file that only mentions it.
    """
    out = []
    for name in sorted(os.listdir(TESTS_DIR)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(TESTS_DIR, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.List):
                continue
            consts = [e.value for e in node.elts if isinstance(e, ast.Constant)]
            if "-m" in consts and "build" in consts:
                out.append(name)
                break
    return sorted(out)


#: Measured 2026-09-04. `test_packaging.py`'s `_build_sdist` is the only caller, and both
#: sdist tests go through it.
SUITE_MODULES_THAT_BUILD_TODAY = ["test_packaging.py"]

#: Every job whose steps run pytest, measured the same day. The suite is the same one in both
#: — release.yml's Install step says so in its own comment — so the toolchain must be too.
SUITE_JOBS_TODAY = [("ci.yml", "python-tests"), ("release.yml", "verify")]


def test_the_suite_build_censuses_are_what_the_tree_holds():
    assert suite_modules_that_build_a_distribution() == SUITE_MODULES_THAT_BUILD_TODAY, (
        f"the suite modules that shell out to `python -m build` are "
        f"{suite_modules_that_build_a_distribution()}; this file was written against "
        f"{SUITE_MODULES_THAT_BUILD_TODAY}")
    assert jobs_that_run_the_suite() == SUITE_JOBS_TODAY, (
        f"the jobs that run the suite are {jobs_that_run_the_suite()}; this file was written "
        f"against {SUITE_JOBS_TODAY}")


def _installs_the_build_tool(script):
    """True when a script installs the `build` frontend from an index (constrained or not)."""
    return any(re.fullmatch(r"build[<>=!~,.\d]*", token) for token in _install_tokens(script))


def _runs_pytest(script):
    """True when a script INVOKES pytest — not merely names it in an install line.

    Measured while writing this: `"pytest" in script` matched the dependency install step,
    so the ordering comparison was `0 < 0` and the check read the install as the run. The
    distinction between naming a tool and running it is the whole property here.
    """
    for line in _code_only(script).splitlines():
        stripped = line.strip()
        if "pip install" in stripped or "npm install" in stripped:
            continue
        if re.search(r"-m\s+pytest\b", stripped) or re.match(r"pytest\b", stripped):
            return True
    return False


def build_tool_specifiers():
    """{specifier: [sources]} for every `build` install token anywhere under `.github/`.

    One string, or the constraint has forked — which is the failure mode the clean-room
    action's own header names about the font step, one directory over.
    """
    found = {}
    for source, script in _all_run_scripts():
        for token in _install_tokens(script):
            if re.fullmatch(r"build[<>=!~,.\d]*", token):
                found.setdefault(token, []).append(source)
    return found


@pytest.mark.parametrize("workflow,job", jobs_that_run_the_suite())
def test_every_job_that_runs_the_suite_installs_build_before_it(workflow, job):
    """A test that skips itself is not a gate, and this one guards the published sdist.

    What this looks like if wrong: the sdist regresses to the F-4c607d79 shape — 112 test
    files that cannot collect — CI stays green because the check skipped, and the artifact
    reaches `release: published` and PyPI, where the version is taken forever.
    """
    scripts = _body_scripts(workflow, job)
    runs = [i for i, s in enumerate(scripts) if _runs_pytest(s)]
    assert runs, f"{workflow}:{job} is in the suite census and runs no pytest in its body"
    installs = [i for i, s in enumerate(scripts) if _installs_the_build_tool(s)]
    assert installs, (
        f"{workflow}:{job} runs the suite and installs no `build`; "
        f"{SUITE_MODULES_THAT_BUILD_TODAY} shells out to `python -m build` and converts its "
        "absence into a skip, so the two sdist assertions do not execute here")
    assert min(installs) < min(runs), (
        f"{workflow}:{job} installs `build` at step {min(installs)} and runs the suite at "
        f"step {min(runs)}; the clean-room action installs it AFTER the suite, which is the "
        "measured order that left the sdist unchecked")


def test_the_build_tool_has_one_constraint_wherever_it_is_installed():
    """Two copies of one version constraint is how the font dependency forked."""
    specs = build_tool_specifiers()
    listed = {spec: sorted(set(sources)) for spec, sources in specs.items()}
    assert len(specs) == 1, (
        f"`build` is installed under {len(specs)} different specifiers under .github/: {listed}")
    (spec, sources), = specs.items()
    assert re.search(r"[<>=~]", spec), (
        f"`build` is installed as {spec!r}, resolved fresh on the day the step runs")
    assert ".github/actions/clean-room/action.yml" in sources, (
        "the clean-room action no longer installs `build`; it is the constraint's home and "
        f"the sources today are {sorted(set(sources))}")


def test_the_build_ordering_check_goes_red_on_the_order_this_repo_had():
    """The mutation: ci.yml's own install line and step order, as they stood this morning.

    A census that cannot fail is the class this wave exists to close, so the pre-fix shape is
    fed to the same two predicates the jobs are judged by.
    """
    before = [
        "python -m pip install --upgrade pip numpy pillow pytest "
        "opencv-python-headless==5.0.0.93 matplotlib==3.11.1",
        "python -m pytest tests -q",
    ]
    assert [i for i, s in enumerate(before) if _installs_the_build_tool(s)] == [], (
        "the pre-fix install line reads as installing `build`; the check cannot fail")
    after_the_suite = ["python -m pytest tests -q", 'python -m pip install "build>=1.5,<2"']
    installs = [i for i, s in enumerate(after_the_suite) if _installs_the_build_tool(s)]
    runs = [i for i, s in enumerate(after_the_suite) if _runs_pytest(s)]
    assert not min(installs) < min(runs), (
        "installing the tool after the suite reads as installing it before")
    # And the third direction, the one that made this check compare a step with itself: an
    # install line that NAMES pytest is not a step that runs it.
    assert not _runs_pytest(before[0]), (
        "a `pip install ... pytest ...` line reads as a step that runs the suite")
    assert _runs_pytest(before[1])
