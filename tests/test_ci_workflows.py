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
    "ci.yml": ["python-tests", "site-build"],
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
    ".github/actions/sheet-fonts/action.yml", ".gitignore", "HANDOFF.md", "LICENSE",
    "README.md", "README.pypi.md", "pyproject.toml", "verify.ps1",
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
    assert _local_action_files() == [".github/actions/sheet-fonts/action.yml"]
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
    script = _code_only(run_script(step_containing(CI, "run it from a clean install")))
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
    #: 16 on this branch; 18 on the merged tree, where ci-packaging's new `launcher` job
    #: adds a checkout and a setup-node. Recorded as the merged number, so this assertion
    #: is red here and green there — the same treatment every incoming population gets.
    assert len(ALL_USES) == 18, [(r[0], r[1]) for r in ALL_USES]
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

SCAN = "npm audit --audit-level=high"
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
