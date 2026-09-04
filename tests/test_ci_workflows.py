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


@pytest.mark.parametrize("workflow", ["release.yml", "ci.yml"])
def test_a_job_that_checks_out_declares_contents_read(workflow):
    """A job-level `permissions:` block REPLACES the workflow-level grant; it does not add.

    So a job that declares only `id-token: write` has no `contents` scope at all, and its
    `actions/checkout` authenticates the clone with a token that cannot read a private
    repository. Jobs with no `permissions:` block of their own inherit and are not at issue.
    """
    text = _text(workflow)
    for name in job_names(text):
        body = "\n".join(_job_lines(text, name))
        if "actions/checkout" not in body:
            continue
        if re.search(r"(?m)^    permissions:\s*$", body) is None:
            continue  # inherits the workflow-level grant
        assert re.search(r"(?m)^\s+contents:\s*read\s*$", body), (
            f"{workflow} job {name!r} narrows its own permissions and then checks out; "
            "the checkout token has no contents scope"
        )


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


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_ci_runs_on_every_file_the_package_is_built_from(trigger):
    """pyproject names its own build inputs; every one of them must trigger a build.

    Read from pyproject rather than listed here, so renaming README.pypi.md moves the
    requirement with it instead of leaving this test asserting a filename nobody uses.
    """
    project = PYPROJECT["project"]
    inputs = {"pyproject.toml", project["readme"]}
    licence = project.get("license")
    if isinstance(licence, dict) and licence.get("file"):
        inputs.add(licence["file"])
    patterns = _paths_under(trigger)
    missing = [
        f
        for f in sorted(inputs)
        if not any(p == f or (p.endswith("/**") and f.startswith(p[:-3] + "/")) for p in patterns)
    ]
    assert missing == [], (
        f"{trigger} builds nothing when these build inputs change: {missing}; the first "
        "place that surfaces is the release job, after the tag exists"
    )


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
