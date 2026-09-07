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
        timeout=30,
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


#: Quote runs a Python string literal can hide a name inside, longest first so a triple
#: quote is never read as an empty pair.
_QUOTES = ('"""', "'''", '"', "'")


def _strip_string_literals(text):
    """`text` with the CONTENTS of every quoted string replaced by spaces.

    WAVE 23, F-2cb02bed (tests' half; ci-packaging carries the pass-mutation fixture --
    coordinator ruling, wave-23 SEAM 3). `_code_only` dropped `#` comment lines and nothing
    else, so a name appearing in a DOCSTRING or any other string literal read as the leg
    reaching it. That is not hypothetical: ci-packaging measured it on the first draft of
    `.github/actions/clean-room/lazy_import_probe.py`, whose module docstring listed
    `draw_body`, `draw_hand` and `mean_consecutive_frame_difference` -- the lazy-import
    census went green over a probe that called none of them, because `_code_only` strips
    `#` lines and not docstrings.

    A character-scanner rather than a regex or a tokeniser: the input is a shell `run:`
    block, which is not Python and cannot be tokenised, and a regex over quotes cannot see
    that a `#` inside a string is not a comment. Length is preserved (contents become
    spaces, quotes are kept) so a caller can still report a line number.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        for q in _QUOTES:
            if text.startswith(q, i):
                out.append(q)
                i += len(q)
                start = i
                while i < n and not text.startswith(q, i):
                    if text[i] == "\\" and i + 1 < n:      # an escaped quote is content
                        i += 2
                        continue
                    i += 1
                out.append("".join(" " if c != "\n" else "\n"
                                   for c in text[start:i]))
                if i < n:
                    out.append(q)
                    i += len(q)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _code_only(script, *, strings=False):
    """The script with `#` comment lines dropped -- naming a module in a comment is not
    reaching it, and this test is about what the leg RUNS.

    `strings=True` ALSO blanks every string literal's contents, for a census over a PYTHON
    source. It is not the default and must not become one: most callers here read a shell
    `run:` block, where the quoted text IS the command -- `TARBALL="$PWD/$(ls -1 ./*.tgz |
    head -1)"`, `'build>=1.5,<2'`. Measured 2026-09-05: blanking strings unconditionally
    turned NINE tests in this file red, each of them correctly reading a quoted argument.
    Use `_python_code_only` for the Python case, so the distinction has a name rather than
    resting on a keyword nobody passes.
    """
    no_comments = "\n".join(
        line for line in script.splitlines() if not line.lstrip().startswith("#")
    )
    return _strip_string_literals(no_comments) if strings else no_comments


def _python_code_only(script):
    """`_code_only` for a PYTHON source: comments AND string literals blanked.

    The predicate the lazy-import census needs -- a function named in a docstring is not a
    function the leg calls.
    """
    return _code_only(script, strings=True)



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


#: The calls that CONSUME a path. A repo-root filename mentioned anywhere in `tests/` is a
#: string; a filename handed to one of these is a file the suite reads, and editing it can
#: turn CI red. The distinction is the whole of F-3a455e7d's second half: `".git"` appears at
#: `tests/test_packaging.py:1013` as a directory-walk SKIP token — a name the suite EXCLUDES,
#: never a path it opens — and the old constant-only walk could not tell the two apart.
_PATH_CONSUMING_CALLS = frozenset({
    "open", "join", "isfile", "isdir", "exists", "getsize", "relpath", "abspath",
    "Path", "read_text", "read_bytes", "samefile", "realpath",
})


def repo_root_tracked_files(root=None):
    """Repo-root files as GIT TRACKS them — the node a workflow `paths:` entry can name.

    THE NODE THIS KEYS ON (F-3a455e7d): a path under version control at the repo root.
    That is the node the property "a workflow can trigger on it" lives on. The old
    derivation keyed on the CHECKOUT — `os.listdir(REPO)` filtered by `os.path.isfile` —
    which is a different node and disagrees with itself between checkouts: in a linked
    `git worktree` `.git` is a 60-byte gitdir POINTER FILE, so it passed `os.path.isfile`,
    entered the population, and three tests in this file demanded CI trigger on `.git`, a
    path no workflow can ever list. Measured 2026-09-04 in
    `.swarm/worktrees/w10-tests-8481819-3690`: `3 failed, 3070 passed` off the main
    checkout, green on it. `git ls-files` gives the same answer from either, because a
    worktree and its main checkout share one index.

    `root` is a parameter so the derivation can be driven against a scratch tree (see
    `test_the_root_population_ignores_a_git_pointer_file`).
    """
    root = REPO if root is None else root
    try:
        proc = subprocess.run(["git", "-C", root, "ls-files", "-z", "--", ":(top)"],
                              capture_output=True, timeout=30)
    except OSError:  # pragma: no cover - git absent from PATH
        proc = None
    if proc is not None and proc.returncode == 0:
        return {e for e in proc.stdout.decode("utf-8").split(chr(0)) if e and "/" not in e}
    # git is unavailable (an unpacked sdist, a release tarball). Fall back to the listing
    # with VCS metadata excluded BY NAME, because `.git` is a directory on a normal
    # checkout and a FILE in a linked worktree — the exact asymmetry above.
    return {e for e in os.listdir(root)
            if e != ".git" and os.path.isfile(os.path.join(root, e))}


def _literals_used_as_paths(tests_dir=None):
    """Every string literal under `tests/` that is handed to a path-consuming call.

    Keys on the CALL, not on the constant: `ast.Constant` nodes reached as an argument of
    a call in `_PATH_CONSUMING_CALLS`, or as the right operand of a `/` against a name
    (the `tmp_path / "x"` form). A bare constant in a list, a message, or a skip set is
    not a path the suite reads.
    """
    tests_dir = TESTS_DIR if tests_dir is None else tests_dir
    found = set()

    def _consume(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)

    for name in sorted(os.listdir(tests_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(tests_dir, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
                if fname in _PATH_CONSUMING_CALLS:
                    for arg in node.args:
                        _consume(arg)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                _consume(node.right)
    return found


def _repo_root_files_the_suite_reads(root=None, tests_dir=None):
    """Every repo-ROOT TRACKED file the suite hands to a path-consuming call.

    The derivation is "every file the suite guards": if a test reads a file, editing that
    file can turn CI red, so editing it has to RUN CI. Both halves changed in wave 10
    (F-3a455e7d): the population comes from `git ls-files` rather than the checkout's
    directory listing, and the literal must be USED as a path rather than merely present
    as a constant.

    Measured 2026-09-04, what the second half removed: `HANDOFF.md` and `README.md` were
    in the old population through `tests/test_record_index_binding.py:105/119`, where they
    are payload strings inside a FAKE record — no test opens either file. `README.md` also
    reaches the workflows' paths filters on its own; nothing about this shrink removes a
    trigger, it removes two false claims about what the suite reads.
    """
    entries = repo_root_tracked_files(root)
    return sorted(entries & _literals_used_as_paths(tests_dir))


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
    # Read through `declared_licence_files()`, which understands PEP 639's `license-files`
    # as well as the deprecated `license = { file = ... }` table. This line WAS
    # `project["license"]["file"]`, keyed on the table's own key: moving to the PEP 639 form
    # would have made it return nothing and dropped the LICENSE trigger requirement in
    # silence, with the census still green because `_repo_root_files_the_suite_reads()`
    # finds `LICENSE` by an unrelated route (F-77a1c1b9).
    inputs.update(declared_licence_files())
    inputs.update(_local_action_files())
    inputs.update(_repo_root_files_the_suite_reads())
    return sorted(inputs)


#: Re-derived on 2026-09-04 (wave 10, F-3a455e7d). Equality, so a new composite action or a
#: new repo-root file the suite starts READING joins the requirement on the day it lands.
#: `HANDOFF.md` and `README.md` left at this re-derivation: both were admitted by the old
#: constant-only walk through `tests/test_record_index_binding.py:105/119`, where they are
#: payload strings inside a FAKE record — no test opens either file, so neither is a file
#: "the suite guards". `README.md` still matches both workflows' path filters on its own.
#: MERGE NOTE (wave 10): ci-packaging's branch adds
#: `.github/actions/npm-clean-room/action.yml` to this list and to the
#: `_local_action_files()` pin below, by the existing rule (a composite action both
#: workflows call). Both halves survive the merge — this derivation and that member.
RECORDED_TRIGGER_POPULATION = [
    # `clean-room` joined at the wave-8 merge: ci-packaging lifted the clean-install leg into a
    # composite action called by ci.yml and release.yml (F-60ab1bd7); this census saw it
    # appear, which is the direction it exists for. `npm-clean-room` joined at wave 10 the
    # same way (F-3729edd4) — the npm package's half of that leg — and the census saw it too.
    # WAVE-10 MERGE (coordinator, 2026-09-04): tests' derivation dropped HANDOFF.md and README.md
    # (they entered through a fake record's payload strings, not a path-consuming call).
    ".github/actions/clean-room/action.yml", ".github/actions/npm-clean-room/action.yml",
    ".github/actions/sheet-fonts/action.yml",
    ".gitignore", "LICENSE", "MANIFEST.in", "README.pypi.md",
    "pyproject.toml", "verify.ps1",
]


def test_the_trigger_population_is_derived_from_what_ci_and_the_suite_actually_consume():
    """Size and membership before the property.

    THE NODE: a repo-root path under version control that a test hands to a path-consuming
    call. Not `os.listdir(REPO)` (that is the checkout, and `.git` is a FILE in a linked
    worktree), and not "a constant that happens to equal a filename" (that is a string, and
    `".git"` is a directory-walk SKIP token at `tests/test_packaging.py:1013`)."""
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


def test_the_root_population_ignores_a_git_pointer_file(tmp_path):
    """The red proof for the FIRST half of F-3a455e7d, driven on a scratch tree.

    A linked `git worktree` writes `.git` as a 60-byte gitdir POINTER FILE. The old
    derivation was `{e for e in os.listdir(REPO) if os.path.isfile(...)}`, which admits it;
    this test builds that shape and shows the two rules disagree, so the new one cannot
    quietly revert to the old.
    """
    # every path below is built from a NAME, never from a literal handed to a path call:
    # `_literals_used_as_paths` walks this file too, and a literal `".git"` on the right of
    # a `/` here would put VCS metadata back into the population through this very test.
    vcs, proj, leg, pkg = ".git", "pyproject.toml", "verify.ps1", "tools"
    scratch = tmp_path / "worktree"
    scratch.mkdir()
    (scratch / vcs).write_text("gitdir: <the main checkout>/.git/worktrees/w10\n", encoding="utf-8")
    (scratch / proj).write_text("[project]\n", encoding="utf-8")
    (scratch / leg).write_text("# leg\n", encoding="utf-8")
    (scratch / pkg).mkdir()

    naive = {e for e in os.listdir(scratch) if os.path.isfile(os.path.join(scratch, e))}
    assert ".git" in naive, "the shape this test exists to catch is a .git FILE at the root"

    derived = repo_root_tracked_files(str(scratch))
    assert ".git" not in derived, f"VCS metadata entered the population: {sorted(derived)}"
    assert {"pyproject.toml", "verify.ps1"} <= derived

    # and on the tree this run is reading, whichever shape it has here
    assert ".git" not in repo_root_tracked_files(), (
        "`.git` is not a path any workflow `paths:` entry can list, and requiring CI to "
        "trigger on it is red in every linked worktree and green on the main checkout")


def test_a_root_filename_that_is_only_a_skip_token_is_not_a_file_the_suite_reads(tmp_path):
    """The red proof for the SECOND half: the walk keys on the CALL, not on the constant.

    `".git"` is present under `tests/` exactly once — `tests/test_packaging.py:1013`, in a
    directory-walk skip set. A name a test EXCLUDES is not a file a test READS, and the
    old constant-only walk could not tell them apart. The scratch tree below carries one
    of each; adding `dropped.txt` to the population is the mutation that must NOT happen.
    """
    scratch = tmp_path / "tests"
    scratch.mkdir()
    (scratch / "test_reads.py").write_text(
        "import os\n"
        "def test_a():\n"
        "    with open(os.path.join('/repo', 'kept.txt')) as fh:\n"
        "        assert fh.read()\n",
        encoding="utf-8")
    (scratch / "test_excludes.py").write_text(
        "def test_b():\n"
        "    skip = {'dropped.txt', 'node_modules'}\n"
        "    assert 'dropped.txt' in skip\n",
        encoding="utf-8")

    used = _literals_used_as_paths(str(scratch))
    assert "kept.txt" in used
    assert "dropped.txt" not in used, (
        "a bare constant is not a path use; that is how `.git` entered the trigger census")

    # The real tree: the skip token is present as a constant and absent from the population.
    # The suite files are opened by a LOOP variable, not by a literal, so this check does not
    # itself add a member to `paths_the_suite_guards()`.
    literals = set()
    for name in sorted(os.listdir(TESTS_DIR)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(TESTS_DIR, name), encoding="utf-8") as fh:
            for node in ast.walk(ast.parse(fh.read())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    literals.add(node.value)
    assert ".git" in literals, "the directory-walk skip set in test_packaging.py names `.git`"
    assert ".git" not in _literals_used_as_paths()


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


# -- the build inputs that do NOT live at the repo root (F-5d2c6d28, F-65828040) ----------
#
# THE NODE `trigger_population()` keys on is `git ls-files -- :(top)` -- a tracked file at the
# repo ROOT, an entry with no `/` in it. That is the right node for the population it derives
# and it can never hold anything the suite reads one directory down. Measured 2026-09-04 by
# resolving every `docs/` path expression under `tests/`: seven documents are consumed there
# and TWO matched no filter in either trigger list.
#
#   * `docs/research-grounding.md` -- `tests/test_openpose_convention.py:46-49` asserts the
#     document still carries F20's limbSeq verbatim, so an edit to it turns CI red. It matched
#     no filter, so the edit ran no CI at all and the red first surfaced on an unrelated push.
#   * `docs/assets/{logo-wide,mark-figure,E02-identity-sheet}.png` -- `tests/test_packaging.py`
#     asserts `.gitignore`'s `!docs/assets/**` negation still re-includes them AND that no
#     negation points at a path the tree does not have. A docs-only commit that removes that
#     directory kills the negation, and nothing ran.
#
# THE SPELLING THAT HIDES. The openpose document is reached as
# `os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs",
# "research-grounding.md")` -- the join is rooted at a CALL, not at a module-level path
# constant, so a walk keyed on "a join off a known root name" resolves nothing here. The
# derivation below keys on the constants INSIDE the join, from the `"docs"` segment onward,
# whatever the root expression is.

_DOCS_LITERAL = re.compile(r"""^docs/[^\s*?"']+\.[A-Za-z0-9]+$""")


def _trailing_constants(args, start):
    """`args[start:]` as strings, or None if any of them is not a string constant.

    A join whose tail is computed (`os.path.join(root, "docs", name)`) names no single
    document, and guessing one would put a path this suite never opens into the requirement.
    """
    out = []
    for arg in args[start:]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append(arg.value)
        else:
            return None
    return out


def _docs_paths_the_suite_reads(tests_dir=None):
    """Every repo path under `docs/` that a test resolves, by either spelling.

    Two shapes, because the two findings arrived in two shapes:

    * a join whose arguments carry `"docs"` followed by string constants, ROOTED ANYWHERE --
      a name, a call, a subscript; the root is not read at all, which is what makes this
      immune to the Call-rooted form that hides from a root-keyed walk;
    * a `docs/...`-prefixed literal naming a file, wherever it appears. `tests/test_packaging.py`
      holds the three committed figures in a module-level list and hands the LIST to
      `_check_ignore`, so no single constant is ever an argument of a path-consuming call --
      the repo-root census's `_PATH_CONSUMING_CALLS` rule would see none of them. A literal
      that spells a repo subdirectory and a file extension is a path claim about this tree.
    """
    tests_dir = TESTS_DIR if tests_dir is None else tests_dir
    found = set()
    for name in sorted(os.listdir(tests_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(tests_dir, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
                if fname == "join":
                    for i, arg in enumerate(node.args):
                        if isinstance(arg, ast.Constant) and arg.value == "docs":
                            tail = _trailing_constants(node.args, i)
                            if tail and len(tail) > 1:
                                found.add("/".join(tail))
                            break
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _DOCS_LITERAL.match(node.value):
                    found.add(node.value)
    return sorted(found)


def _covered(patterns, path):
    """Does `path` match one of a trigger list's `paths:` entries?"""
    return any(p == path or (p.endswith("/**") and path.startswith(p[:-3] + "/"))
               for p in patterns)


#: Derived 2026-09-04 (wave 12). Equality, so a test that starts reading an eighth document
#: under `docs/` joins the trigger requirement on the day it lands rather than being guarded
#: by a job that never runs on it.
RECORDED_DOCS_POPULATION = [
    "docs/assets/E02-identity-sheet.png",
    "docs/assets/logo-wide.png",
    "docs/assets/mark-figure.png",
    "docs/experiments/E04-the-between-generation-floor.md",
    "docs/index/armature.db",
    "docs/license-map.md",
    "docs/research-grounding.md",
]


def test_the_docs_population_is_derived_from_what_the_suite_resolves():
    """Size and membership before the property, and every member must be a file that exists.

    A resolved path that is not in the tree would be a requirement on a document nobody has,
    which is how a filter list fills with entries that guard nothing.
    """
    pop = _docs_paths_the_suite_reads()
    assert pop == RECORDED_DOCS_POPULATION, {
        "appeared": sorted(set(pop) - set(RECORDED_DOCS_POPULATION)),
        "vanished": sorted(set(RECORDED_DOCS_POPULATION) - set(pop)),
    }
    absent = [p for p in pop if not os.path.isfile(os.path.join(REPO, p.replace("/", os.sep)))]
    assert absent == [], f"the suite resolves these and the tree does not carry them: {absent}"


def test_the_docs_census_resolves_a_call_rooted_join(tmp_path):
    """The hidden spelling, shown unmatched: a join rooted at a CALL, in a scratch tests tree.

    This is the shape `tests/test_openpose_convention.py` uses and the shape a root-keyed walk
    cannot see. The fixture also carries the list-literal form, which reaches no path-consuming
    call at all, and a bare `'docs'` constant that names no file and must NOT enter. Both real
    shapes must be resolved, and both must then be REJECTED by the live filter lists -- a
    census whose members were all already covered would be a check that cannot fail.
    """
    # ASSEMBLED, never written as one literal: this module is itself walked by the census
    # under test, so a fixture path spelled as a single constant here would enter the REAL
    # population and demand a CI trigger for a document that does not exist. Neither half
    # matches on its own -- `docs/assets/` has no extension, `hidden-spelling.md` no prefix.
    # Neither fixture path may be one a live filter already covers, or the red direction
    # below is a check that cannot fail: `docs/assets/**` is now listed, so the list-literal
    # fixture takes a subdirectory nothing names.
    doc = "docs/" + "hidden-spelling.md"
    figure = "docs/" + "nested/hidden-figure.png"
    scratch = tmp_path / "tests"
    scratch.mkdir()
    (scratch / "test_call_rooted.py").write_text(
        "import os\n"
        "def test_a():\n"
        "    doc = os.path.join(os.path.dirname(os.path.abspath(__file__)), %r, %r)\n"
        "    with open(doc) as fh:\n"
        "        fh.read()\n" % tuple(doc.split("/")),
        encoding="utf-8",
    )
    (scratch / "test_list_literal.py").write_text(
        "FIGURES = [%r]\ndef test_b():\n    assert FIGURES\n" % figure,
        encoding="utf-8",
    )
    (scratch / "test_not_a_path.py").write_text(
        "SKIP = 'docs'\n"
        "def test_c():\n"
        "    assert SKIP\n",
        encoding="utf-8",
    )
    got = _docs_paths_the_suite_reads(str(scratch))
    assert got == sorted([figure, doc]), got
    for trigger in ("push", "pull_request"):
        uncovered = [p for p in got if not _covered(_paths_under(trigger), p)]
        assert uncovered == got, (
            "the requirement below cannot go red: this fixture's documents are already "
            f"covered by {trigger}'s filters"
        )


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_ci_runs_on_every_docs_file_the_suite_reads(trigger):
    """The property. A test reads it, so editing it can turn CI red, so editing it must run CI."""
    patterns = _paths_under(trigger)
    missing = [p for p in _docs_paths_the_suite_reads() if not _covered(patterns, p)]
    assert missing == [], (
        f"{trigger} builds nothing when these change: {missing}; each is resolved by a test "
        "in this suite, so the first place a breakage surfaces is an unrelated later push"
    )


# WAVE 23 (tests, F-2cb02bed): a SECOND, byte-identical `_code_only` was defined here and
# shadowed the one above it. Measured 2026-09-05 while widening that predicate to blank
# string literals: the widened version was written once, at its first home, and every test
# below this line kept the narrow one — including the lazy-import census the widening
# exists for, which went green over a docstring naming three functions the probe never
# called. Two definitions of one walk in one module is the shape `tests/_census_nodes.py`
# was created to end; the duplicate is deleted, not re-widened.


#: The probe the wheel room runs, lifted out of both callers in wave 23 (ci-packaging
#: `F-1c5dc527`). It was a bash heredoc in `.github/actions/clean-room/action.yml` and a
#: byte-identical PowerShell here-string in `verify.ps1`, and the census below could see only
#: the first: `_all_run_scripts()` walks `.github/`. Measured on `e8263a3` with the three
#: calls replaced by `pass` inside verify.ps1's copy ALONE — 256 tests still passed. One text,
#: two callers, and the census reads the text rather than either caller's quoting of it.
LAZY_IMPORT_PROBE = os.path.join(
    REPO, ".github", "actions", "clean-room", "lazy_import_probe.py")


def lazy_import_probe_source():
    """The probe file both clean-room callers run, read as text."""
    with open(LAZY_IMPORT_PROBE, encoding="utf-8") as fh:
        return fh.read()


def _clean_room_source():
    """Everything the wheel room RUNS: the action's script plus the probe file it invokes."""
    # WAVE-23 MERGE (coordinator, 2026-09-05): `_python_code_only` on BOTH sources, as tests' SEAM 6 asked —
    # the probe is a Python file and a function named in its docstring is not a function the leg calls;
    # the action script now only invokes that file, so blanking its string contents changes nothing the
    # predicate reads. Before the merge the two branches disagreed only on which predicate this line
    # applied; on the merged tree it is the widened one, over everything the wheel room runs.
    return _python_code_only(clean_room_script()) + "\n" + _python_code_only(lazy_import_probe_source())


def _unreached(script, sites):
    """The lazy roots `script` reaches nothing of — the census's predicate, lifted.

    Lifted so the red proof below can drive it on a mutated source without re-implementing
    the comparison it is proving.
    """
    return [
        f"{root} (imported by {', '.join(sorted(set(fns)))})"
        for root, fns in sorted(sites.items())
        if not any(fn in script for fn in fns)
    ]


def test_the_clean_room_leg_reaches_every_lazily_imported_dependency():
    """`armature check` executes no function body, so it is green on a wheel that cannot run.

    The requirement is derived from the source, not written here: for each function-local
    third-party import, the leg must CALL one of the functions that performs it. A new lazy
    dependency fails this test until the clean-room leg calls through to it.
    """
    script = _clean_room_source()
    sites = lazy_import_call_sites()
    assert set(sites) == set(lazy_third_party_roots()), (
        f"a lazy dependency has no located call site: {sorted(set(lazy_third_party_roots()) - set(sites))}"
    )
    unreached = _unreached(script, sites)
    assert unreached == [], (
        f"the clean-room leg calls nothing that reaches {unreached}; it would pass on a "
        "wheel whose drawing and donor paths raise ModuleNotFoundError on first call"
    )


def test_gutting_a_lazy_import_call_site_turns_the_census_red():
    """WAVE 23, ci-packaging `F-2cb02bed` — the guard was satisfied by an ANNOUNCEMENT.

    The probe used to end

        print("clean room: draw_body, draw_hand and mean_consecutive_frame_difference all ran")

    so all three names sat in the source whether or not the calls happened, and the census
    above — `any(fn in script for fn in fns)` — passed on the literal. Measured on `e8263a3`
    with all three call sites replaced by `pass`: `tests/test_ci_workflows.py` = 216 passed,
    and this census passed on its own (1 passed, 215 deselected).

    Both directions are asserted here. On the probe as it now stands, deleting ANY ONE call
    site takes that dependency's whole family of function names out of the source and the
    census goes red. On the shape it replaced — the same mutation plus the old printed
    literal — the census stays GREEN, which is the defect this proves is gone.
    """
    sites = lazy_import_call_sites()
    probe = lazy_import_probe_source()
    assert _unreached(_clean_room_source(), sites) == []

    reds = []
    for root, fns in sorted(sites.items()):
        mutated = probe
        for fn in sorted(set(fns)):
            mutated = re.sub(r"(?m)^(\s*)_ran\(\w+\.%s\b[^\n]*$" % re.escape(fn),
                             r"\1pass", mutated)
        assert mutated != probe, (
            f"no `_ran(<module>.<fn>, ...)` call site reaching {root} could be located; "
            "the mutation changed nothing, so this row asserts nothing")
        script = _code_only(clean_room_script()) + "\n" + _code_only(mutated)
        unreached = _unreached(script, sites)
        assert unreached, (
            f"the call sites reaching {root} were replaced by `pass` and the census is still "
            f"green; its answer does not depend on the calls running")
        assert any(u.startswith(root + " ") for u in unreached), (
            f"gutting {root}'s call sites turned the census red about something else: "
            f"{unreached}")
        reds.append(root)
    assert reds == sorted(lazy_third_party_roots()), (
        f"one red per lazily imported dependency was expected "
        f"({sorted(lazy_third_party_roots())}) and {reds} were proven; SEAM 3's contract "
        "is one red per name")

    # The shape that WAS green: the same gutted probe with the announcement put back.
    announcement = (
        'print("clean room: draw_body, draw_hand and '
        'mean_consecutive_frame_difference all ran")')
    gutted = re.sub(r"(?m)^(\s*)_ran\(\w+\.\w+[^\n]*$", r"\1pass", probe)
    before = _code_only(clean_room_script()) + "\n" + _code_only(gutted + announcement)
    assert _unreached(before, sites) == [], (
        "the pre-fix shape — every call gutted, the literal restored — now fails the census; "
        "this red proof no longer reproduces the defect it exists to describe")


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
            rest = _run_header(line)
            if rest is None:
                continue
            # WAVE 14 (ci-packaging seed, test_ci_workflows.py:1005): the block scalars were
            # `("run: |", "run: |-")` only. YAML has SIX headers here — `|`, `|-`, `|+`, `>`,
            # `>-`, `>+` — and a `run: >` step fell to the `else` branch, which took
            # `line.strip()[len("run: "):]` and yielded the string `">"`. Every rule in this
            # file that reads a run script would then have examined one character while the
            # step's actual commands went unread: no shell, no `set -euo pipefail`, no
            # `pip install`, no `npm publish`. There is no folded step on disk today, which
            # is exactly why the blindness was free to sit here; the red proof below plants
            # one.
            # …and a step whose FIRST key is `run:` reads `- run: …`, which
            # `line.strip().startswith("run:")` did not see at all — a second blindness in
            # the same three lines, and the reason `_run_header` exists.
            if rest in RUN_BLOCK_HEADERS:
                body = block_at(lines, i)
                pad = min((_indent(x) for x in body if x.strip()), default=0)
                out.append((name, "\n".join(x[pad:] for x in body)))
            else:
                out.append((name, rest))
    return out


def test_the_run_script_reader_sees_a_folded_scalar(tmp_path, monkeypatch):
    """RED on the spelling the reader could not see (wave 12, rule 2; wave 14 seed).

    A synthetic workflow whose only step uses `run: >` — the folded scalar — must have its
    commands read, and the pre-wave-14 reader is run beside it and shown to return `">"`, or
    the comparison this test makes says nothing.
    """
    import test_ci_workflows as SELF

    folded = (
        "name: probe\n"
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - name: install\n"
        "        run: >\n"
        "          pip install --quiet\n"
        "          armature-studio[dev]\n")
    (tmp_path / "probe.yml").write_text(folded, encoding="utf-8")
    monkeypatch.setattr(SELF, "WORKFLOWS", str(tmp_path))
    monkeypatch.setattr(SELF, "ACTIONS", str(tmp_path / "no-actions"))

    scripts = dict(_all_run_scripts())
    assert set(scripts) == {"probe.yml"}, sorted(scripts)
    assert "pip install --quiet" in scripts["probe.yml"], scripts
    assert "armature-studio[dev]" in scripts["probe.yml"], scripts

    def pre_wave_14(text):
        got = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not line.strip().startswith("run:"):
                continue
            if line.strip() in ("run: |", "run: |-"):
                body = block_at(lines, i)
                pad = min((_indent(x) for x in body if x.strip()), default=0)
                got.append("\n".join(x[pad:] for x in body))
            else:
                got.append(line.strip()[len("run: "):])
        return got

    assert pre_wave_14(folded) == [">"], (
        "the pre-wave-14 reader read the folded step's commands; it could not, and if it "
        "could this test would be comparing a reader with itself")

    # …and the spellings it COULD read are unchanged, so the widening did not trade one
    # blindness for another. The `- run:` forms are the SECOND blindness in the same three
    # lines: a step whose first key is `run:` was invisible to the reader entirely, so the
    # pre-wave-14 walk is shown returning nothing for them.
    for src, expected in (
            ("jobs:\n  b:\n    steps:\n      - name: x\n        run: |\n          echo hi\n",
             "echo hi"),
            ("jobs:\n  b:\n    steps:\n      - name: x\n        run: |-\n          echo hi\n",
             "echo hi"),
            ("jobs:\n  b:\n    steps:\n      - name: x\n        run: echo hi\n", "echo hi"),
            ("jobs:\n  b:\n    steps:\n      - run: |\n          echo hi\n", "echo hi"),
            ("jobs:\n  b:\n    steps:\n      - run: echo hi\n", "echo hi"),
    ):
        (tmp_path / "probe.yml").write_text(src, encoding="utf-8")
        assert dict(_all_run_scripts())["probe.yml"].strip() == expected, src
    for src in ("jobs:\n  b:\n    steps:\n      - run: |\n          echo hi\n",
                "jobs:\n  b:\n    steps:\n      - run: echo hi\n"):
        assert pre_wave_14(src) == [], (
            "the pre-wave-14 reader saw a `- run:` step; it did not, and if it could this "
            "half of the test compares a reader with itself")


# ------------------------------------------- the `-O` leg, and the env var that reaches it
#
# WAVE 14, ci-packaging's seam (F-a2a838c7). `release.yml`'s `Suite under -O` step ran
# `python -O -m pytest -q` with NO `env:` block at all, while `ci.yml`'s equivalent set
# `PYTHONOPTIMIZE: "1"` beside the flag. The difference is not cosmetic and ci-packaging
# measured it on this rig: a parent run as `python -O` spawning
# `subprocess.run([sys.executable, "-c", ...])` gives a CHILD with `__debug__ is True` and
# `PYTHONOPTIMIZE` unset; the same parent with `PYTHONOPTIMIZE=1` in the environment gives a
# child with `__debug__ is False`. There are subprocess call sites in `tests/**` that inherit
# the environment and pass no `-O`, so the flag alone does not reach them — and this repo's
# whole argument that gates still raise when asserts are deleted rests on that leg.
#
# Keyed on the ARGV, never on the step's name (wave-8 rule): the two spellings on disk are
# `Suite under -O` and `run tests under -O (gates must still raise)` and neither is read here,
# so a rename cannot delete the census. Driven from TEXT rather than from `WORKFLOWS`, so the
# red proof can run it over a reverted copy — which is the only way it goes red on the operand.


#: The six YAML block-scalar headers a `run:` may carry. The reader shipped with two.
RUN_BLOCK_HEADERS = ("|", "|-", "|+", ">", ">-", ">+", "")


def _run_header(line):
    """The text after `run:` on this line, or None — `- run:` counted as well as `run:`.

    A step's FIRST key may be `run:`, in which case the line reads `- run: …` and a
    `line.strip().startswith("run:")` test does not see it at all.
    """
    stripped = line.strip()
    if stripped.startswith("- "):
        stripped = stripped[2:].lstrip()
    if not stripped.startswith("run:"):
        return None
    return stripped[len("run:"):].strip()


def _step_blocks(body):
    """Every `steps:` entry in a job body, as a list of lines including its own `- ` line."""
    lines = [ln for ln in body.splitlines()]
    starts = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("- ")]
    out = []
    for n, i in enumerate(starts):
        base = _indent(lines[i])
        end = len(lines)
        for j in starts[n + 1:]:
            if _indent(lines[j]) <= base:
                end = j
                break
        out.append(lines[i:end])
    return out


def _run_script_of(step):
    """The `run:` script of one step block — folded and literal scalars alike, else None."""
    for i, line in enumerate(step):
        rest = _run_header(line)
        if rest is None:
            continue
        if rest in RUN_BLOCK_HEADERS:
            body = block_at(step, i)
            pad = min((_indent(x) for x in body if x.strip()), default=0)
            return "\n".join(x[pad:] for x in body)
        return rest
    return None


def _pythonoptimize_of(step):
    """The value of `PYTHONOPTIMIZE` in this step's own `env:` block, or None."""
    for i, line in enumerate(step):
        if line.strip() != "env:":
            continue
        for entry in block_at(step, i):
            key, _, value = entry.partition(":")
            if key.strip() == "PYTHONOPTIMIZE":
                return value.strip().strip('"').strip("'")
    return None


def optimized_suite_steps(body):
    """`[(run script, PYTHONOPTIMIZE value or None)]` for every step in `body` that runs the
    suite under `-O`.

    THE NODE: an invocation of pytest carrying the `-O` flag. Not the step's name, not the
    file it lives in.
    """
    out = []
    for step in _step_blocks(body):
        script = _run_script_of(step)
        if script is None:
            continue
        code = _code_only(script)
        if "pytest" not in code:
            continue
        if not re.search(r"(?m)(^|\s)-O(\s|$)", code):
            continue
        out.append((code, _pythonoptimize_of(step)))
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
def test_every_job_that_runs_the_suite_also_runs_it_under_optimize(workflow, job):
    """The population is the jobs that run pytest, derived — not a list of two file names.

    `python -O` deletes every `assert`, so a job that runs the suite only in its ordinary
    form proves nothing about whether the gates still raise; that is the whole argument
    `verify.ps1` and both workflows are built to make.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    steps = optimized_suite_steps(body)
    assert steps, (
        f"{workflow} job {job!r} runs pytest and never runs it under -O; the leg that shows "
        f"the andons survive `assert` deletion does not exist in this job")


@pytest.mark.parametrize("workflow,job", jobs_that_run_the_suite())
def test_every_optimize_leg_sets_pythonoptimize_in_its_environment(workflow, job):
    """The flag alone does not reach a child process; the environment variable does.

    ci-packaging measured it on this rig (F-a2a838c7): a parent run as `python -O` spawning
    `subprocess.run([sys.executable, "-c", ...])` gives a child with `__debug__ is True` and
    `PYTHONOPTIMIZE` unset, and the same parent with `PYTHONOPTIMIZE=1` in the environment
    gives a child with `__debug__ is False`. `tests/**` has subprocess call sites that
    inherit the environment and pass no `-O` of their own, so a `-O` leg without the variable
    exercises the parent only.
    """
    body = "\n".join(_job_lines(_text(workflow), job))
    for script, value in optimized_suite_steps(body):
        assert value == "1", (
            f"{workflow} job {job!r} runs the suite under -O with PYTHONOPTIMIZE={value!r}; "
            f"the flag reaches this process and not the ones the suite spawns:\n{script}")


def test_the_optimize_census_is_red_on_a_leg_that_drops_the_environment_block(tmp_path):
    """Rule 3, on the operand the finding named: a workflow whose `-O` step has no `env:`.

    The census is driven over TEXT, so the reverted copy is drivable — pointing it at
    `WORKFLOWS` only would make this test a re-implementation rather than a proof. Both the
    literal-block and the one-line `run:` spellings are exercised, because a workflow may use
    either and the census must not be keyed on the layout.
    """
    guarded = (
        "  verify:\n"
        "    steps:\n"
        "      - name: Suite\n"
        "        run: python -m pytest -q\n"
        "      - name: Suite under -O\n"
        "        run: python -O -m pytest -q\n"
        "        env:\n"
        '          PYTHONOPTIMIZE: "1"\n')
    reverted = guarded.replace("        env:\n", "").replace(
        '          PYTHONOPTIMIZE: "1"\n', "")
    assert "PYTHONOPTIMIZE" not in reverted

    assert [v for _s, v in optimized_suite_steps(guarded)] == ["1"]
    assert [v for _s, v in optimized_suite_steps(reverted)] == [None], (
        optimized_suite_steps(reverted))
    with pytest.raises(AssertionError):
        for _script, value in optimized_suite_steps(reverted):
            assert value == "1"

    # …and a step whose name never mentions -O is still found, or the census is keyed on the
    # spelling the wave-8 rule forbids.
    renamed = guarded.replace("- name: Suite under -O", "- name: second pass")
    assert [v for _s, v in optimized_suite_steps(renamed)] == ["1"], renamed

    # …and a job with no `-O` leg at all is reported as having none.
    assert optimized_suite_steps(
        "  verify:\n"
        "    steps:\n"
        "      - name: Suite\n"
        "        run: python -m pytest -q\n") == []


def test_the_verify_script_runs_the_same_optimize_leg_the_workflows_do():
    """The third copy. `verify.ps1` is the local equivalent of both jobs, and a rule that
    holds in CI and not on the rig is a rule contributors meet only after pushing."""
    with open(os.path.join(REPO, "verify.ps1"), encoding="utf-8") as fh:
        script = fh.read()
    assert re.search(r"-O\s+-m\s+pytest", script), (
        "verify.ps1 runs no `-O` pytest leg; the workflows do, so the rig and CI disagree "
        "about what a green verify means")
    assert re.search(r"\$env:PYTHONOPTIMIZE\s*=\s*'1'", script), (
        "verify.ps1's -O leg does not set PYTHONOPTIMIZE, so the subprocesses the suite "
        "spawns run with asserts ACTIVE while the parent runs with them deleted")
    assert "finally" in script, (
        "verify.ps1 sets PYTHONOPTIMIZE and does not restore it in a `finally`; every leg "
        "after the -O one would then run optimized without saying so")


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


# WAVE 26, F-dfdbcff1 — `test_the_repo_still_has_an_action_to_hold_to_the_pin` stood here and
# its three clauses now ride `test_the_pinning_census_is_every_external_action_in_the_tree`
# below, with their comments intact. Two near-identically named SHA-pinning censuses asserted
# the same two properties over the same population in the same file: the non-empty clause and
# the `len(ALL_USES) == 17` size pin here, membership there. Doubled parametrization inflated
# the count of a law with ONE subject and left it ambiguous which census a future edit was
# meant to keep in step. `ALL_USES` and `THIRD_PARTY` stay — the fourth-party-name test below
# reads them, and the size and identity clauses that used to live here now sit beside the
# membership set they were always about.


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


# WAVE 26, F-dfdbcff1 — `test_an_action_is_pinned_to_a_commit_and_says_which_version` stood
# here, parametrized over `ALL_USES` and asserting the same 40-hex clause and the same
# `# vX.Y.Z` clause, with the same two failure messages, as
# `test_every_action_is_pinned_to_a_commit_and_says_which_version` below over `uses_refs()`
# — the same population under a different spelling. Its docstring's own history (the npm half
# held by a test, the PyPI half held only by a comment, and the branch ref that left both
# guarding tests green until 2026-09-04) is preserved on the survivor.


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


#: The context objects GitHub exposes to an `if:` expression. The unmodelled-reference
#: guard below was keyed on the single literal `github.` until wave 18, so `inputs.rehearse`
#: — the one expression standing between a dispatched rehearsal and an irreversible publish
#: to two registries — reached `eval` as a bare name and raised `SyntaxError` for every
#: context, which is why the rehearsal truth table could not be written at all. The guard is
#: a PREFIX SET now: a reference this evaluator cannot resolve refuses by name whichever
#: context it comes from, rather than one context being modelled and eight being silent.
IF_CONTEXTS = ("github", "inputs", "env", "vars", "needs", "matrix", "secrets", "job",
               "steps", "runner", "strategy")

_IF_REFERENCE = re.compile(
    r"\b(?:" + "|".join(IF_CONTEXTS) + r")(?:\.[A-Za-z_*][A-Za-z0-9_-]*)*\b")

#: What `_if_reference` returns for a reference no context models. `None` cannot carry this,
#: because `None` is the value GitHub itself gives a MISSING property of a context that does
#: exist — the two are different answers and this guard turns on telling them apart.
_UNMODELLED = object()


def _if_reference(name, ctx):
    """The value of one `a.b.c` context reference, or `_UNMODELLED`.

    Two spellings of a context are accepted, because the workflows need both. A DOTTED LEAF
    key (`{"github.event_name": "push"}`) is how every caller before wave 18 spelled one. A
    whole context OBJECT (`{"inputs": {"rehearse": True}}`) is the only way to model the
    difference GitHub makes between `inputs.rehearse` being `false` and the `inputs` context
    having no `rehearse` in it at all: a property missing from a modelled context resolves
    to null, which is exactly what `release: published` feeds `!inputs.rehearse`, and
    reading that row as "unmodelled" would leave the real-release direction of the
    rehearsal truth table unassertable.
    """
    if name in ctx:
        return ctx[name]
    root, _, rest = name.partition(".")
    if isinstance(ctx.get(root), dict):
        value = ctx[root]
        for part in rest.split(".") if rest else []:
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value
    return _UNMODELLED


def _outside_string_literals(body, fn):
    """Apply `fn` to the parts of an expression that are NOT inside `'single quotes'`.

    GitHub's only string literal is single-quoted and its content must survive verbatim: a
    ref compared against `'refs/heads/main'` must not have the boolean or `!` substitutions
    run over it, and a literal that happens to spell a context root must not be resolved as
    one.
    """
    parts = re.split(r"('(?:[^']|'')*')", body)
    return "".join(part if index % 2 else fn(part) for index, part in enumerate(parts))


def _eval_if(expr, ctx):
    """Evaluate a workflow `if:` expression for one context.

    Only the operators these workflows actually use, and an unmodelled context reference
    raises rather than quietly deciding the answer — a truth table built on a silently
    mis-evaluated condition would be worse than no truth table.

    The refusal `raise`s rather than asserting. `python -O` deletes an `assert`, this suite
    runs an `-O` leg, and the deleted form of this particular check is an evaluator that
    decides a publish-or-skip question from whatever an unresolved name leaves behind.
    """
    body = expr.strip()
    if body.startswith("${{") and body.endswith("}}"):
        body = body[3:-2].strip()
    unmodelled = []

    def _substitute(chunk):
        chunk = chunk.replace("||", " or ").replace("&&", " and ")
        # GitHub's unary `!` is truthiness negation, and `!=` is a different operator that
        # shares its first character: the lookahead is the whole reason
        # `github.ref != 'refs/heads/main'` does not become ` not = `.
        chunk = re.sub(r"!(?!=)", " not ", chunk)
        # GitHub's expression language spells the booleans lowercase; `pages.yml`'s deploy
        # condition compares against a literal `false` and no caller had ever fed one of
        # those through here, so this substitution arrived with the first job that needed
        # it. It runs BEFORE the reference substitution so that it can never reach inside a
        # value this evaluator itself inserted.
        chunk = re.sub(r"\bfalse\b", "False", chunk)
        chunk = re.sub(r"\btrue\b", "True", chunk)

        def _one(match):
            value = _if_reference(match.group(0), ctx)
            if value is _UNMODELLED:
                unmodelled.append(match.group(0))
                return match.group(0)
            return repr(value)

        return _IF_REFERENCE.sub(_one, chunk)

    body = _outside_string_literals(body, _substitute)
    if unmodelled:
        raise AssertionError(
            f"unmodelled context in an if-expression: {expr!r} reads "
            f"{sorted(set(unmodelled))}, which this context does not model; the answer this "
            "evaluator would give is not the answer the runner would give")
    return bool(eval(body, {"__builtins__": {}}, {}))  # noqa: S307 - the input is this repo's own YAML


def _job_if(text, job):
    """A job's OWN `if:`, read at the job key's indent — never a step's.

    The indent is the entire difference between a job-level condition and a step-level one,
    and this reader is what the rehearsal truth table below asks whether a publish job runs.
    Read loosely, a job whose job-level `if:` had been DELETED — the exact edit that truth
    table exists to catch, and the shape release.yml carried on 041027c — would answer with
    the first `if:` of whatever step happened to carry one, and the deletion would read as a
    condition still in place.
    """
    for line in _job_lines(text, job):
        if _indent(line) == 4 and line.strip().startswith("if:"):
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
    """Size and membership, before the property. `./` paths ride the checkout and are not refs.

    WAVE 26, F-dfdbcff1 — the three clauses of the retired
    `test_the_repo_still_has_an_action_to_hold_to_the_pin` are folded in below, with their
    comments intact, so the law's size, its non-emptiness and its membership are asserted in
    ONE place rather than in two that a future edit could keep only half in step with.
    """
    seen = sorted({(source, action) for source, action, _ref, _line in uses_refs()})
    assert seen == EVERY_USE_TODAY, (
        "the set of external actions under .github/ has changed; each new one needs a SHA "
        "and a version comment before this list is updated:\n  "
        + "\n  ".join(f"{s}: {a}" for s, a in sorted(set(seen) ^ set(EVERY_USE_TODAY))))

    # The population may not empty itself silently, and may not shrink to the one row an
    # uncommented exemption happened to leave behind. A test parametrized over an empty list
    # reports green, and a pinning law with no subject is the shape four prior gates in this
    # repo took: passing N/N because N was zero.
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


@pytest.mark.parametrize("source,action,ref,line", uses_refs())
def test_every_action_is_pinned_to_a_commit_and_says_which_version(source, action, ref, line):
    """The law release.yml's PyPI comment states in general terms, applied generally.

    "A ref that resolves at run time means the code performing the step is not the code last
    reviewed" is a property of the ref, not of who owns the repository it points at. The
    trailing `# vX.Y.Z` is part of the requirement: a bare hash is unreadable, and a bump is
    reviewed by comparing the version a human can read.

    WAVE 26, F-dfdbcff1 — this is the law's ONE home in this file now, and it carries the
    history the retired duplicate above recorded: `npm install -g npm@^11.5.1` is held to a
    constraint by `test_the_publish_toolchain_is_not_resolved_on_release_day`; the action
    beside it — which performs the upload itself, the step with no compensator — carried a
    40-hex SHA and a comment ending "Bump deliberately, by re-resolving", and nothing
    anywhere asserted it, so substituting the branch ref it held until 2026-09-04 left both
    guarding tests green.
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


#: The build backend is not installed by any workflow line: `python -m build` resolves
#: `[build-system].requires` into an isolated environment of its own. Until wave 10 that put
#: the ONE tool that applies MANIFEST.in and selects sdist contents outside a census whose
#: whole subject is "what runs on release day" (F-fbf7020c).
BACKEND_SOURCE = "pyproject.toml:[build-system].requires"

#: `verify.ps1`'s DESCRIPTION says a green local run and a green CI run are the same claim,
#: and leg 3 produces a wheel and an sdist. That makes it a third place the artifact is
#: PRODUCED, and it was in no census at all: `toolchain_tokens()` walked `job_scripts()` over
#: `workflow_files()` only (F-da6b0457).
LOCAL_VERIFY_SOURCE = "verify.ps1"


def toolchain_tokens():
    """Every package a distribution's production or publication resolves.

    Two populations, both walked: the JOBS that build (above) plus the ones that hand an
    artifact to a registry, read for what they install — and `[build-system].requires`, read
    out of pyproject, because the backend is resolved by `python -m build` itself and appears
    in no install line anywhere.
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
    for requirement in PYPROJECT["build-system"]["requires"]:
        tokens.setdefault(requirement.strip(), []).append(BACKEND_SOURCE)
    with open(os.path.join(REPO, LOCAL_VERIFY_SOURCE), encoding="utf-8") as fh:
        for token in _install_tokens(fh.read()):
            tokens.setdefault(token, []).append(LOCAL_VERIFY_SOURCE)
    return tokens


#: Installed without a version constraint, deliberately, as of 2026-09-04. None of these
#: PRODUCES or UPLOADS the artifact: `pip` is the installer itself, and numpy/pillow/pytest
#: are the suite's own dependencies, whose byte-stable pins (opencv, matplotlib) carry `==`
#: where the golden frames need them. `build`, `twine`, `npm` and `setuptools` are the four
#: tools that make or move the artifact, and all four are constrained — `setuptools` since
#: wave 10, when the census learned to read the backend that PRODUCES the artifact and not
#: only the tools that invoke it.
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


def declared_python_ceiling():
    """The EXCLUSIVE upper bound `requires-python` states, e.g. `<3.15` -> (3, 15), or None.

    WAVE 23, `F-4a74acc0`. This census used to take its ceiling from
    `max(classifier_pythons())` — the `Programming Language :: Python :: 3.13` row — which is
    metadata pip reads for DISPLAY and never for resolution. `requires-python = ">=3.11"`
    stated a floor and no ceiling, so the interval the artifact actually promised was open at
    the top: pip would install this wheel on every future CPython, and the test could still
    assert `floor in exercised` and `ceiling in exercised` about a promise nothing bounded.
    The ceiling is now read from the field pip enforces.
    """
    spec = PYPROJECT["project"]["requires-python"]
    match = re.search(r"<\s*(\d+\.\d+)", spec)
    return _version_tuple(match.group(1)) if match else None


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
    """The interval pip enforces is BOUNDED at both ends, and the classifiers sit inside it.

    What this looks like if wrong: `requires-python = ">=3.10"` with a single 3.13 job — a
    promise about four interpreters, one of which has ever been run. And the half this test
    could not see until wave 23: `>=3.11` with no upper bound at all, where the CEILING it
    was comparing came from a classifier row pip never resolves against.
    """
    exercised = {v for v in _versions_declared_for("python") if v[0] == 3}
    assert exercised, "no workflow pins a python version this check can read"
    floor, ceiling = declared_python_floor(), declared_python_ceiling()
    assert ceiling is not None, (
        f"requires-python is {PYPROJECT['project']['requires-python']!r} and states no upper "
        "bound; pip installs this distribution on every future CPython, and no job here has "
        "run one. Decide the ceiling where pip reads it.")
    assert floor < ceiling, (
        f"requires-python declares {floor} <= python < {ceiling}, which is empty")
    assert floor in exercised, (
        f"requires-python declares a floor of {floor} and no job runs it; the versions run "
        f"are {sorted(exercised)}")
    top_claimed = max(classifier_pythons())
    assert top_claimed in exercised, (
        f"the classifiers claim up to {top_claimed} and no job runs it; the versions run are "
        f"{sorted(exercised)}")
    outside = sorted(v for v in classifier_pythons() if v < floor or v >= ceiling)
    assert outside == [], (
        f"these classifiers claim versions outside the interval requires-python promises "
        f"[{floor}, {ceiling}): {outside}")
    below = sorted(v for v in classifier_pythons() if v < min(exercised))
    assert below == [], (
        f"these classifiers are BELOW the lowest version any job runs: {below}; a version "
        "under the exercised floor is an extrapolation, not an interpolation")


def test_the_interval_check_goes_red_on_a_specifier_with_no_upper_bound():
    """The mutation: the declaration this file carried until wave 23.

    `>=3.11` alone must yield no ceiling, or the assertion above is decoration. The two
    bounded spellings are driven beside it so the reader is not proven red on a shape the
    parser simply cannot read.
    """
    unbounded = re.search(r"<\s*(\d+\.\d+)", ">=3.11")
    assert unbounded is None, "the ceiling reader finds a bound in a floor-only specifier"
    for spec, expected in ((">=3.11,<3.15", (3, 15)), (">=3.11, <4", None),
                           (">=3.11,<3.14", (3, 14))):
        match = re.search(r"<\s*(\d+\.\d+)", spec)
        got = _version_tuple(match.group(1)) if match else None
        assert got == expected, (spec, got, expected)


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


def _repo_root_expression(node, env):
    """`""` when `node` evaluates to the repository root, else None.

    WAVE 12, F-387eb031 — THE NODE this census could not resolve. `_joined_relpath` resolved
    a join's first argument only when it was a string literal or a `Name` already in the
    environment, so a join ROOTED IN A CALL was invisible. The repo's own idiom for "the
    repository root" is a call:

        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    which is exactly how `tests/test_openpose_convention.py:46-49` builds the path to
    `docs/research-grounding.md`, opens it, and asserts the document still carries F20's
    limbSeq verbatim — the pinning whose stated purpose is "if someone edits
    research-grounding.md's F20, this fails". Measured 2026-09-04: the file exists,
    `paths_the_suite_guards()` did not return it, it was absent from `GUARDED_TODAY`, and it
    matched none of ci.yml's push or pull_request filters. A PR editing only that file — the
    retrieved record the OpenPose convention is transcribed from — ran no CI job at all, and
    the test written to fail on that edit was green-by-absence on the PR.

    Three spellings of the same root are resolved, because the point is the root and not the
    spelling: the double `dirname` of `abspath(__file__)`, the double `dirname` of
    `__file__`, and `dirname(X)` where `X` already resolves to `tests`.
    """
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if not isinstance(node, ast.Call):
        return None
    fn = node.func
    if not (isinstance(fn, ast.Attribute) and fn.attr == "dirname"
            and isinstance(fn.value, ast.Attribute) and fn.value.attr == "path"):
        return None
    if len(node.args) != 1:
        return None
    inner = node.args[0]
    # `os.path.dirname(<something that resolves to a relative dir>)`
    resolved = _repo_root_expression(inner, env)
    if resolved is not None:
        parent = "/".join(resolved.strip("/").split("/")[:-1])
        return parent
    # `os.path.dirname(os.path.abspath(__file__))` / `os.path.dirname(__file__)` -> tests
    if isinstance(inner, ast.Name) and inner.id == "__file__":
        return "tests"
    if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "abspath"
            and isinstance(inner.func.value, ast.Attribute)
            and inner.func.value.attr == "path"
            and len(inner.args) == 1
            and isinstance(inner.args[0], ast.Name) and inner.args[0].id == "__file__"):
        return "tests"
    return None


def _joined_relpath(node, env):
    """`os.path.join(BASE, "a", "b")` -> `BASE/a/b`, or None if any part is not resolvable.

    The first argument may be a string literal, a `Name` in the environment, or — since wave
    12 — any expression `_repo_root_expression` can resolve, which is where the Call-rooted
    repo-root idiom enters.
    """
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
        elif i == 0:
            rooted = _repo_root_expression(arg, env)
            if rooted is None:
                return None
            if rooted:
                parts.append(rooted)
        else:
            return None
    return "/".join(p.strip("/") for p in parts if p.strip("/"))


def repo_paths_the_suite_opens(tests_dir=None, repo=None):
    """Every existing repo path a test module names, walked out of a tests tree by AST.

    WAVE 26, F-ec944439 — this walk was written out TWICE in this file, identically, once in
    `paths_the_suite_guards` and once in `paths_the_suite_opens_but_git_ignores`, so the two
    halves of a partition were two walks that happened to agree. It has one home now, and it
    takes `tests_dir` / `repo` so both halves can be driven against a scratch tree instead of
    only against the checkout the session happens to be running on.

    Derivation, stated because a census whose population is typed is the defect class this
    file keeps finding: each test module is parsed; `REPO` seeds an environment of path
    constants; every `NAME = os.path.join(...)` of literals off a known constant extends it
    (two passes, so a constant defined below its first use still resolves); then every
    `os.path.join(...)` in the module is resolved the same way and kept if it exists on
    disk. Paths that resolve through a variable filename are not resolvable this way and are
    not claimed — this is a floor on what the suite reads, not a ceiling.
    """
    tests_dir = TESTS_DIR if tests_dir is None else tests_dir
    repo = REPO if repo is None else repo
    found = set()
    for name in sorted(os.listdir(tests_dir)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(tests_dir, name), encoding="utf-8") as fh:
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
                if rel and os.path.exists(os.path.join(repo, rel)):
                    found.add(rel)
    return found


def paths_the_suite_guards(tests_dir=None, repo=None):
    """The half of the partition that a commit CAN carry a change to — see the walk above."""
    # WAVE-16 MERGE (coordinator, 2026-09-04): a path git IGNORES exists on this checkout (rig artifacts under
    # `outputs/`) and is opened by a test, but no commit can ever carry a change to it, so no
    # trigger filter can run on it — it is not a file the suite guards in the sense this census
    # measures. Partitioned into its own derived category (`paths_the_suite_opens_but_git_ignores`)
    # rather than dropped: the wave-16 tests amend anchored `E02_ROOT` through `conftest.repo_file`
    # and the walk found `outputs/E02/runs` for the first time.
    found = repo_paths_the_suite_opens(tests_dir, repo)
    return sorted(found - set(_git_ignored(found, repo)))


def _git_ignored(paths, repo=None):
    """The members of `paths` that `git check-ignore` says are ignored — asked of git, not typed."""
    repo = REPO if repo is None else repo
    paths = sorted(paths)
    if not paths:
        return []
    # NUL-terminated both ways (`-z`): text-mode stdin on Windows turns "\n" into "\r\n" and
    # git then echoes the path quoted with the CR inside it — measured on the first cut.
    proc = subprocess.run(["git", "-C", repo, "check-ignore", "--stdin", "-z"],
                          input=b"\0".join(x.encode("utf-8") for x in paths) + b"\0",
                          capture_output=True, timeout=30)
    # exit 0: some ignored; 1: none ignored; 128 with "not a git repository" is a synthetic
    # tree under tmp_path (the red proofs build one) and ignores nothing; anything else is a
    # git failure worth seeing.
    err = proc.stderr.decode("utf-8", "replace")
    if proc.returncode == 128 and "not a git repository" in err:
        return []
    assert proc.returncode in (0, 1), err
    return sorted(x.decode("utf-8") for x in proc.stdout.split(b"\0") if x)


def paths_the_suite_opens_but_git_ignores(tests_dir=None, repo=None):
    """The partition `paths_the_suite_guards` sets aside: repo paths a test opens that git ignores.

    ONE walk with its sibling (F-ec944439); the two used to be byte-identical copies, so the
    partition was two independent derivations that could drift apart without either half
    saying so.
    """
    return _git_ignored(repo_paths_the_suite_opens(tests_dir, repo), repo)


#: The population as measured 2026-09-04 by the walk above. Asserted, so a test that starts
#: reading a new repo file fails HERE — naming the file and the filter it needs — rather
#: than reaching main green-by-absence.
GUARDED_TODAY = [
    ".github/actions",
    # WAVE 23 (ci-packaging, F-1c5dc527 / F-481b512c / F-83ce864e): the clean room's two
    # FILES joined when this module started opening them by path -- the lifted lazy-import
    # probe (one text, two callers) and the classifier gate, whose exit codes and halt line
    # are now driven as a subprocess. Both are under `.github/actions/**`, which ci.yml
    # already carries on `push` and `pull_request`, so this is a census widening and not a
    # trigger gap. Re-derived branch-local with `==` in the commit that added the tests.
    ".github/actions/clean-room",
    ".github/actions/clean-room/classifier_gate.py",
    ".github/actions/clean-room/lazy_import_probe.py",
    ".github/actions/sheet-fonts/action.yml",
    ".github/workflows",
    ".gitignore",
    # MANIFEST.in joined with the sdist fix-up (wave 8): tests/test_packaging.py opens it by
    # path, and a packaging input is a CI input — it is on both triggers.
    "MANIFEST.in",
    "docs/experiments/E04-the-between-generation-floor.md",
    "docs/index/armature.db",
    # Joined at wave 10 (core-gates): `tests/test_route_gates.py` reads the licence map's
    # table rows to check that `RULED_COMPONENTS` — which calls itself a MIRROR of that
    # document — carries a row for every kill the map records. The licence gate is a
    # CLAUDE.md non-negotiable, so a re-fetch that adds or retires a kill is exactly the
    # change CI must run on. ⚠ SEAM, routed to ci-packaging: ci.yml's `push` and
    # `pull_request` filters carry `docs/experiments/**` and `docs/index/**` and DO NOT
    # cover this file, so `test_ci_runs_on_every_file_the_suite_guards` names it until the
    # line `- "docs/license-map.md"` is added under both triggers.
    "docs/license-map.md",
    # WAVE 12 (F-387eb031): JOINED when `_joined_relpath` learned to resolve a join ROOTED IN
    # A CALL — `os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    # "docs", "research-grounding.md")`, which is how `tests/test_openpose_convention.py`
    # opens the retrieved record it asserts F20's limbSeq against. It matches NO ci.yml
    # filter; the trigger half is ci-packaging's (F-5d2c6d28) and it is named in
    # `UNFILTERED_PENDING` below until that lands.
    "docs/research-grounding.md",
    # WAVE 23 (ci-packaging, F-9f395455): the `Publish` step's script reads
    # `./package.json`, so the harness that drives it with a stubbed registry runs from
    # `npm/`. Covered by ci.yml's existing `npm/**` filter on both triggers.
    "npm",
    "npm/bin/armature.mjs",
    "npm/package.json",
    "pyproject.toml",
    # WAVE 12 (F-387eb031): the same widening brought fifteen more members in, every one of
    # them already covered by an existing `specs/**`, `tests/**` or `tools/**` filter — they
    # were invisible for the same reason and were never a trigger gap.
    "specs",
    "specs/E01-anchor.json",
    "specs/E08-seeds.json",
    "specs/E09-A3-seeds.json",
    "specs/E09-seeds.json",
    "specs/E11-seeds.json",
    "specs/E12-seeds.json",
    "specs/E13-prompt.json",
    "specs/E13-seeds.json",
    "specs/E14-seeds.json",
    # WAVE 28 (builders, F-7ca576d2): the ONE home the eight seed specs' correction history
    # moved to. `tests/test_seeds_specs.py` opens it by path on every check — it resolves each
    # spec's pointer and then reads this file's seven `<file>.py:<line> (<function>)`
    # citations against the tree — and `tests/test_amend_w22_builders.py` opens it too. A
    # census widening, not a trigger gap: ci.yml already carries `specs/**` on `push` and
    # `pull_request` (:72 and :144), which the property below re-checks rather than assumes.
    # Re-derived branch-local with `==` in the commit that added the file: 70 -> 71.
    "specs/ceiling-why-machine-readable.md",
    "tests",
    "tests/blender/check_floor_material.py",
    "tests/blender/check_ortho_convention.py",
    "tests/blender/check_plate_composite.py",
    "tests/blender/check_pose_arc_roundtrip.py",
    "tests/blender/check_visibility.py",
    "tests/blender/make_synthetic_run.py",
    "tests/fake_backend.py",
    "tests/fixtures",
    "tests/fixtures/E12-w3-camera-i2v.api.json",
    "tests/fixtures/canon",
    "tests/fixtures/canon/probe.surfaces.json",
    # WAVE 26 (tests, F-4c22f096): the committed byte copies of two gitignored `outputs/`
    # RECORDS -- `tests/fixtures/records/E02/payloads/{A0,A1b}.json`, resolved by
    # `conftest.payload_record` so `test_gate_s.py`'s twelve-item E04-against-E02 comparison
    # stops skipping on every clone and every CI job. A census widening, not a trigger gap:
    # ci.yml already carries `tests/**` on push and pull_request, which the property below
    # re-checks rather than assumes. Re-derived branch-local with `==` in the commit that
    # added the fixtures: 69 -> 70.
    "tests/fixtures/records",
    "tests/fixtures/uploads",
    # my own new test opens this by path, to name the site the widening was written for
    "tests/test_openpose_convention.py",
    "tools",
    "tools/armature_core",
    # the next two and `build_payload.py`/`fetch_run.py` joined at the wave-8 merge: sibling
    # branches' censuses open these sources by path (core-solvers' andon walk, builders' exit
    # convention). All under `tools/**`, which both triggers already carry.
    # WAVE 12 (core-solvers, F-e2be2262): `blender_scene.py` is opened by path by the
    # wave-12 amend's docstring check — the `world_bounds` docstring asserted three live
    # naive call sites the tree does not have, and the correction is asserted rather than
    # trusted. Under `tools/**`, which both triggers already carry. (The list is SORTED;
    # this entry sits above `framing.py` for that reason, not by topic.)
    # WAVE 16 (core-solvers, SEAM 11 §5): four files their new tests open by path. All four
    # are under `tools/**`, which BOTH triggers already carry, so no `ci.yml` change is
    # needed — only this list. RED ON THE tests BRANCH ALONE: those tests live in
    # `tests/test_amend_w16_core_solvers.py`, which is not in this worktree, so
    # `paths_the_suite_guards()` reads 53 here and 57 on the merged tree. The list is
    # SORTED, so each entry sits by name and not by topic.
    "tools/armature_core/aapose.py",
    # WAVE 18 (core-solvers): `assembly.py` is opened by path by the wave-18 amend's AST
    # census over the three assembly gates' raises (F-8d0e4cf1) — the census keys on the
    # RESOLVED shape (an `ev["clause"] = ...` assignment immediately above each raise),
    # which means reading the module's source rather than importing it. Under `tools/**`,
    # which BOTH triggers already carry, so `ci.yml` needs no change and
    # `UNFILTERED_PENDING` stays empty. RE-DERIVED, not typed: this list is asserted with
    # `==` by the test below and was measured red at exactly this one member. (The list is
    # SORTED; this entry sits here for that reason, not by topic.)
    "tools/armature_core/assembly.py",
    "tools/armature_core/blender_scene.py",
    # WAVE-12 MERGE (coordinator, 2026-09-04): `canon.py` opened by path by a wave-12 test; under `tools/**`.
    "tools/armature_core/canon.py",
    # WAVE 22 (core-gates, F-682ce228): `tests/test_amend_w22_core_gates.py` opens
    # `canon_census.py` by path to assert that `gate_census_table()` is CALLED at import —
    # a run-time-only check is the half of the andon that a module read once does not
    # have, and asserting the call site means reading the source rather than importing it.
    # Under `tools/**`, which BOTH triggers already carry, so `ci.yml` needs no change and
    # `UNFILTERED_PENDING` stays empty. RE-DERIVED, not typed: this list is asserted with
    # `==` and was measured red at exactly this one member. (The list is SORTED; the entry
    # sits here for that reason, not by topic.)
    "tools/armature_core/canon_census.py",
    "tools/armature_core/framing.py",
    # WAVE-10 MERGE (coordinator, 2026-09-04): `glb.py` (core-solvers' MalformedGLB census) and
    # `render_pose_sticks.py` (instruments-measure's Gate COUNT census) are opened by path by
    # sibling branches' new tests; both under `tools/**`, which both triggers carry.
    "tools/armature_core/glb.py",
    # WAVE 22 (core-gates, F-f2808386): `tests/test_amend_w22_core_gates.py` parses
    # `route_gates.py`'s AST by path for the structural census over every function that
    # SUBSCRIPTS a widget list — the census keys on the resolved shape (a local bound from
    # `n.get("widgets_values")` that is then indexed) and on which shift andon each body
    # calls, which means reading the source rather than importing it. Two more tests in the
    # same module read it by path for the two prose invariants (`verify`'s "a returned
    # receipt never carries `clause`"). Under `tools/**`, which BOTH triggers already
    # carry, so `ci.yml` needs no change and `UNFILTERED_PENDING` stays empty. RE-DERIVED,
    # not typed: measured red at exactly this one member. (The list is SORTED; the entry
    # sits here for that reason, not by topic.)
    "tools/armature_core/route_gates.py",
    # WAVE 16 (core-solvers, SEAM 11 §5) — see the note above `aapose.py`.
    "tools/armature_core/sitelist.py",
    "tools/armature_core/walk.py",
    "tools/armature_index.py",
    # WAVE 16 (builders): five more sources joined, all opened by path by this wave's
    # censuses — the `PayloadError.__init__`/duplicate-method walk over the domain's owned
    # modules, the `["seeds"]`-reader walk, the `--frame` conversion walk, the r2v
    # gate-id walk and the two fetchers' `FetchHalt` key walk. Every one is under
    # `tools/**`, which both triggers already carry, so none of them is a trigger gap and
    # `UNFILTERED_PENDING` stays empty. (The list is SORTED; these sit here for that
    # reason, not by topic.)
    "tools/build_assembly_payload.py",
    "tools/build_i2v_payload.py",
    "tools/build_payload.py",
    "tools/build_r2v_payload.py",
    "tools/build_t2v_payload.py",
    "tools/encode_control.py",
    "tools/extract_clip_frames.py",
    "tools/fetch_run.py",
    # `fetch_t2v_run.py` is NOT here: the wave-16 fetcher census joins its path from a
    # variable (`for name in FETCHERS`), which this walk deliberately does not resolve —
    # "a floor on what the suite reads, not a ceiling". Recorded so the absence is a
    # measurement rather than an oversight.
    "tools/gate_saved_graph.py",
    "tools/make_crop_strip.py",
    "tools/make_overlay_sheet.py",
    "tools/make_test_armature.py",
    "tools/make_zoom_sheet.py",
    # WAVE 16 (core-solvers, SEAM 11 §5) — see the note above `aapose.py`.
    "tools/measure_cascade_clip.py",
    "tools/measure_floor.py",
    # WAVE 22 (instruments, F-7cd1b3b7 / F-f7d1f64f) added `tools/pack_pose_pack.py` here:
    # the amend module and `tests/conftest.py`'s SEAM-1 bridge opened it by path to read the
    # `single_path_segment` copy SEAM 1 homes in `armature_core.parts`. WAVE-22 MERGE
    # (coordinator, 2026-09-05): the seam landed, the bridge and the byte-equivalence check
    # were deleted with it, and the walk above no longer returns the file — MEASURED on the
    # merged tree (`paths_the_suite_guards() ^ GUARDED_TODAY == {'tools/pack_pose_pack.py'}`
    # before this line was removed, empty after). Recorded so the absence reads as a
    # measurement, the same way `fetch_t2v_run.py`'s does above.
    "tools/render_pose_sticks.py",
    # WAVE 16 (core-solvers, SEAM 11 §5) — see the note above `aapose.py`.
    "tools/render_start_frame.py",
    "tools/render_turnaround.py",
    "tools/rig_sheet_compose.py",
    "tools/sheet_compose.py",
    # WAVE 28 (instruments, F-2b8afc38): the falsified approaches kept runnable under
    # `tools/superseded/` are in that domain's globs and their parsers reach an operator
    # too, so `test_instruments_amend_w28.py` derives its parser population by LISTING that
    # directory rather than by naming three files -- a new superseded tool with a bare
    # parser then joins the census instead of sitting outside it. A census WIDENING, not a
    # trigger gap: `tools/**` is carried by ci.yml on both `push` and `pull_request`, which
    # the property below re-checks rather than assumes, so `UNFILTERED_PENDING` stays
    # empty. Re-derived branch-local with `==` in the commit that added the test: 70 -> 71.
    # (The list is SORTED; the entry sits here for that reason, not by topic.)
    "tools/superseded",
    "verify.ps1",
]

#: RE-DERIVED 2026-09-04 (wave 14, F-f70a495d) and EMPTY.
#:
#: What it held: `{"docs/research-grounding.md"}`, routed to ci-packaging in wave 12 as
#: F-5d2c6d28 ("add it to both trigger lists") under a SUBSET assertion so the entry would
#: become deletable rather than red once the filter landed. The filter landed —
#: `.github/workflows/ci.yml` lists `- "docs/research-grounding.md"` under both `push` and
#: `pull_request` — and `_unfiltered(paths_the_suite_guards(), …)` returns `[]` for both
#: triggers. But `test_ci_runs_on_every_file_the_suite_guards` subtracted this set
#: UNCONDITIONALLY, so deleting the ci.yml line again — in a filter-tidying PR, say — left
#: the test green, and the stale entry hid the exact regression its own comment described.
#:
#: The stake, unchanged: a PR editing only that file would run no CI job at all, and
#: `tests/test_openpose_convention.py:55`, whose whole purpose is "if someone edits
#: research-grounding.md's F20, this fails", is green-by-absence on the PR and first surfaces
#: on some later unrelated push, attributed to whatever that push touched.
#:
#: Re-derive with the suite interpreter (tests/conftest.py module docstring):
#:     .venv/Scripts/python.exe -c "import sys;sys.path[:0]=['tests','tools'];import test_ci_workflows as C;\
#:     print({t: C._unfiltered(C.paths_the_suite_guards(), t) \
#:            for t in ('push','pull_request')})"
UNFILTERED_PENDING = set()


def test_the_guarded_path_census_is_the_one_the_suite_actually_opens():
    """Size and membership before the property — a census that cannot grow is not one."""
    assert paths_the_suite_guards() == GUARDED_TODAY, (
        "the set of repo files the suite opens by path has changed; each new member needs a "
        "push and a pull_request filter that covers it before this list is updated:\n  "
        + "\n  ".join(sorted(set(paths_the_suite_guards()) ^ set(GUARDED_TODAY))))


def test_the_guarded_census_resolves_a_join_rooted_in_a_call(tmp_path, monkeypatch):
    """RED on the shape that hides from the name (wave 12, rule 2; F-387eb031).

    A synthetic tests/ module whose ONLY path join is Call-rooted — the repo-root idiom —
    must appear in the population, and the pre-wave-12 resolver must be shown blind to it in
    the same test, or the comparison says nothing.
    """
    import test_ci_workflows as SELF

    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "docs" / "research-grounding.md").write_text("F20 limbSeq", encoding="utf-8")
    (repo / "tests" / "test_probe.py").write_text(
        "import os\n"
        "def test_it():\n"
        "    p = os.path.join(\n"
        "        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),\n"
        "        'docs', 'research-grounding.md')\n"
        "    open(p).read()\n", encoding="utf-8")

    monkeypatch.setattr(SELF, "REPO", str(repo))
    monkeypatch.setattr(SELF, "TESTS_DIR", str(repo / "tests"))
    assert paths_the_suite_guards() == ["docs/research-grounding.md"], (
        paths_the_suite_guards())

    # …and the resolver as it stood before wave 12: first argument must be a literal or a
    # Name already in the environment, anything else returns None.
    def old_joined_relpath(node, env):
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

    tree = ast.parse((repo / "tests" / "test_probe.py").read_text(encoding="utf-8"))
    joins = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "join"]
    assert len(joins) == 1
    assert old_joined_relpath(joins[0], {"REPO": ""}) is None, (
        "the pre-wave-12 resolver resolved the Call-rooted join; if it could, the census "
        "would never have missed docs/research-grounding.md and this test compares nothing")
    assert _joined_relpath(joins[0], {"REPO": ""}) == "docs/research-grounding.md"


def test_the_real_openpose_pin_is_the_site_this_widening_was_written_for():
    """Named, on the real tree: the guard whose subject ran no CI job."""
    with open(os.path.join(TESTS_DIR, "test_openpose_convention.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    env = {"REPO": ""}
    resolved = {r for node in ast.walk(tree) if isinstance(node, ast.Call)
                for r in [_joined_relpath(node, env)] if r}
    assert "docs/research-grounding.md" in resolved, sorted(resolved)
    assert "docs/research-grounding.md" in GUARDED_TODAY


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
    # WAVE 14, F-f70a495d: the `if p not in UNFILTERED_PENDING` subtraction is gone with the
    # set it read. `_unfiltered` returns `[]` for both triggers on this tree, so the
    # assertion holds without it — and it starts covering `docs/research-grounding.md` again
    # the moment the filter line is removed.
    assert UNFILTERED_PENDING == set(), sorted(UNFILTERED_PENDING)
    missing = _unfiltered(paths_the_suite_guards(), trigger)
    assert missing == [], (
        f"{trigger} runs nothing when these change, and a test in tests/ reads every one of "
        f"them: {missing}; the guard does not run on the change it exists to guard"
    )


def _scratch_repo_with_an_ignored_path(tmp_path):
    """A `git init`-ed tree with a `.gitignore`, one ignored file and one tracked file, and a
    tests/ module that opens both by `os.path.join(REPO, ...)`.

    Built rather than found, so the partition can be exercised on a machine that carries no
    rig artifacts — which is every CI machine and every fresh clone.
    """
    repo = tmp_path / "scratch-repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "outputs" / "E99").mkdir(parents=True)
    (repo / "notes").mkdir()
    (repo / ".gitignore").write_text("outputs/\n", encoding="utf-8")
    (repo / "outputs" / "E99" / "run.json").write_text("{}", encoding="utf-8")
    (repo / "notes" / "kept.md").write_text("# kept\n", encoding="utf-8")
    (repo / "tests" / "test_scratch.py").write_text(
        "import os\n"
        "REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
        "def test_opens_both():\n"
        "    open(os.path.join(REPO, 'outputs', 'E99', 'run.json'))\n"
        "    open(os.path.join(REPO, 'notes', 'kept.md'))\n",
        encoding="utf-8")
    proc = subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return str(repo), str(repo / "tests")


def test_the_partition_puts_a_gitignored_path_on_one_side_and_only_one(tmp_path):
    """WAVE 26, F-ec944439 — the property, held on every machine instead of on one.

    What stood here was a `for rel in ignored:` loop plus an
    `if os.path.isdir(REPO/outputs/E02/runs): assert ...`. Measured on `81d6c07` in an
    isolated worktree: `paths_the_suite_opens_but_git_ignores()` returned `[]` and
    `outputs/E02/runs` did not exist, so the loop body never ran and the `if` was false —
    the test passed having evaluated no assertion. The same holds on every ubuntu-latest
    job, because a fresh clone carries no gitignored `outputs/`; only the main checkout,
    which carries the rig artifacts, exercised anything. CI is the one place this census
    exists to defend, and the partition was its blind spot there.

    So the partition is driven on a tree this test BUILDS: a `git init`-ed scratch repo
    with `outputs/` ignored, one ignored file and one tracked file, both opened by a
    test-shaped module. Both halves are the file's own walks, seamed on `(tests_dir, repo)`
    rather than reimplemented here.
    """
    repo, tests_dir = _scratch_repo_with_an_ignored_path(tmp_path)
    opened = repo_paths_the_suite_opens(tests_dir, repo)
    ignored = paths_the_suite_opens_but_git_ignores(tests_dir, repo)
    guarded = paths_the_suite_guards(tests_dir, repo)

    assert opened == {"outputs/E99/run.json", "notes/kept.md"}, sorted(opened)
    assert ignored == ["outputs/E99/run.json"], ignored
    assert guarded == ["notes/kept.md"], guarded
    # A partition, asserted as one: disjoint, and together the whole of what was opened.
    assert set(ignored).isdisjoint(guarded), (ignored, guarded)
    assert set(ignored) | set(guarded) == opened, (ignored, guarded, sorted(opened))


def test_the_partition_census_goes_red_when_an_ignored_path_reaches_the_guarded_half(tmp_path):
    """The mutation, on the same scratch tree: drop the `.gitignore` and the ignored file
    must MOVE to the guarded half rather than staying partitioned.

    Without this direction, a `paths_the_suite_guards` that had stopped subtracting the
    partition at all would still satisfy the test above's membership clauses only by
    accident; here the same path is required to answer differently when git's answer
    changes, which is the one thing the partition is for.
    """
    repo, tests_dir = _scratch_repo_with_an_ignored_path(tmp_path)
    assert paths_the_suite_opens_but_git_ignores(tests_dir, repo) == ["outputs/E99/run.json"]
    os.remove(os.path.join(repo, ".gitignore"))
    assert paths_the_suite_opens_but_git_ignores(tests_dir, repo) == []
    assert paths_the_suite_guards(tests_dir, repo) == ["notes/kept.md", "outputs/E99/run.json"]


def test_a_gitignored_path_a_test_opens_is_partitioned_not_filtered():
    """WAVE-16 MERGE (coordinator, 2026-09-04): the partition is DERIVED from git and asserted non-empty on a checkout
    that carries rig artifacts, so the category cannot silently become the whole census's blind spot.
    On a fresh worktree (no `outputs/`) the walk finds nothing to partition and the census is the
    same list — both directions are stated here.

    WAVE 26, F-ec944439 — kept as the REAL-TREE direction, and no longer the only one: on a
    machine with no rig artifacts its loop body does not run, which is why the two scratch-tree
    tests above exist. What it still adds is that the walk's answer on the actual checkout
    agrees with git's, over paths nobody wrote for a fixture.
    """
    ignored = paths_the_suite_opens_but_git_ignores()
    for rel in ignored:
        assert subprocess.run(
            ["git", "-C", REPO, "check-ignore", "-q", rel], timeout=30
        ).returncode == 0, rel
        assert rel not in paths_the_suite_guards(), rel
    if os.path.isdir(os.path.join(REPO, "outputs", "E02", "runs")):
        assert "outputs/E02/runs" in ignored, ignored


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
#: WAVE-34: python-tests also packs via npm-clean-room (node→python handoff). Re-measured
#: on merged main — do not drop the handoff to shrink this list.
NPM_PACK_JOBS_TODAY = [
    ("ci.yml", "python-tests"), ("ci.yml", "launcher"), ("release.yml", "verify"),
]
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


# -- the backend that MAKES the artifact (wave 10, F-fbf7020c) ----------------------------
#
# `requires = ["setuptools>=68", "wheel"]` had no upper bound, so the tool that actually
# produces the wheel and the sdist was resolved fresh from the index on release day, inside
# the isolated environment `python -m build` creates. The clean-room action pins `build` and
# `twine` under a header calling them "the two tools that PRODUCE the artifact published
# irreversibly", and release.yml pins `npm@^11.5.1` for the same stated reason. setuptools is
# the third tool in that sentence — it is what applies MANIFEST.in and selects sdist contents
# — and it was the one left unbounded, in the one file no census read.
#
# Measured on this tree 2026-09-04: `python -m build` resolved setuptools into
# `build-env-b1ne98lw` and then again into `build-env-uqzn12d8` — a fresh resolution per
# invocation — and the wheel it produced carries `Generator: setuptools (84.0.0)`.
#
# THE NODE THIS CENSUS KEYS ON: `[build-system].requires` in pyproject.toml, read as data.
# `toolchain_tokens()` walked workflow install lines only, so it could see every tool that
# INVOKES the build and none of the tool that performs it.


def build_backend_requirements():
    """`[build-system].requires` — what `python -m build` installs into its isolated env."""
    return list(PYPROJECT["build-system"]["requires"])


def _has_a_ceiling(spec):
    """True when a specifier bounds the version from ABOVE.

    A floor is not a pin. `setuptools>=68` carries a constraint character and no ceiling at
    all, which is exactly why the older check — whose predicate is "any of [=<>~^@]" — would
    have read it as held to a version the day it joined the population.
    """
    return bool(re.search(r"(<|==|~=|\^)\s*\d", spec))


def test_the_backend_that_produces_the_artifact_is_in_the_toolchain_population():
    """The census must contain the tool that MAKES the artifact, not only its callers."""
    tokens = toolchain_tokens()
    backend = [t for t in tokens if t.startswith("setuptools")]
    assert backend, (
        f"the toolchain census is {sorted(tokens)} and none of it is the build backend; "
        f"`[build-system].requires` is {build_backend_requirements()} and it is what applies "
        "MANIFEST.in and selects sdist contents")
    assert any(BACKEND_SOURCE in where for where in tokens.values()), (
        f"no token in the census is sourced from {BACKEND_SOURCE!r}")


def test_every_tool_that_makes_or_moves_the_artifact_is_bounded_from_above():
    """A new major of the build backend must not arrive by itself on release day.

    What this looks like if wrong: setuptools changes sdist file selection or metadata
    handling between two runs of the SAME tag and — with nothing in CI opening the sdist —
    the difference reaches PyPI unexamined; or the build simply fails inside the release job,
    after `release: published` has fired and both registries are waiting.
    """
    tokens = toolchain_tokens()
    unbounded = sorted(
        token + " (" + ", ".join(sorted(set(where))) + ")"
        for token, where in tokens.items()
        if not _has_a_ceiling(token) and token not in UNCONSTRAINED_BY_DESIGN
    )
    assert unbounded == [], (
        f"these can pick up a new major on the day the step runs, in a job that produces or "
        f"publishes the artifact: {unbounded}")


def test_the_ceiling_check_goes_red_on_the_requires_this_repo_had():
    """The mutation: `["setuptools>=68", "wheel"]`, fed to the same predicate.

    Both members must fail it — the floor-only one because a floor is not a ceiling, and the
    bare one because it carries no constraint at all — or the check is green on the shape it
    was written to catch.
    """
    before = ["setuptools>=68", "wheel"]
    assert [spec for spec in before if not _has_a_ceiling(spec)] == before
    assert _has_a_ceiling("setuptools>=70.1,<85")
    assert _has_a_ceiling("build>=1.5,<2")
    assert _has_a_ceiling("npm@^11.5.1")
    assert _has_a_ceiling("matplotlib==3.11.1")


# -- the licence declaration, and the reader that moves with it (wave 10, F-77a1c1b9) -----
#
# The build emitted two SetuptoolsDeprecationWarnings with a stated removal date, on every
# wheel and every sdist, and nothing recorded or gated them. Measured on this tree
# 2026-09-04 from one `python -m build`: `project.license` as a TOML table is deprecated —
# "By 2027-Feb-18, you need to update your project and remove deprecated calls"
# (`setuptools/config/_apply_pyprojecttoml.py:82`) — and `License classifiers are deprecated`
# (`_apply_pyprojecttoml.py:61` and `dist.py:765`), both fired twice, once per artifact.
# With the backend now bounded the removal cannot arrive by surprise, but the honest fix is
# to stop making the deprecated declaration: `license = "MIT"` plus `license-files`, and no
# `License :: OSI Approved ::` classifier. Re-measured after the change: zero
# SetuptoolsDeprecationWarnings in the whole build, and `twine check dist/*` PASSED on both.
#
# THE NODE THE TRIGGER DERIVATION KEYS ON: the licence FILES pyproject declares, in either
# form it can declare them. `trigger_population()` read `project['license']['file']` — the
# table's own key — so moving to PEP 639 would have made that reader return nothing and
# dropped the LICENSE trigger requirement silently, with the census still green because
# `_repo_root_files_the_suite_reads()` happens to find `LICENSE` by a different route.


def declared_licence_files(project=None):
    """Every licence file pyproject names, in either form it may be written in.

    PEP 639's `license-files` (glob patterns) is the form setuptools will still read after
    2027-Feb-18; `license = { file = "..." }` is the TOML table it deprecated. Both are read,
    so this derivation survives the move instead of silently returning nothing.
    """
    import glob as _glob

    project = PYPROJECT["project"] if project is None else project
    out = set()
    patterns = project.get("license-files")
    if isinstance(patterns, list):
        for pattern in patterns:
            for match in _glob.glob(pattern, root_dir=REPO):
                out.add(match.replace(os.sep, "/"))
    licence = project.get("license")
    if isinstance(licence, dict) and licence.get("file"):
        out.add(licence["file"])
    return sorted(out)


def test_the_licence_is_declared_in_the_form_setuptools_will_still_read():
    """The deprecated declaration is the thing removed, not the warning about it.

    What this looks like if wrong: on whichever release day CI resolves a setuptools that has
    dropped the deprecated form, the build fails inside release.yml's `verify` job — after
    `release: published` has fired, on a tag that is already cut and public, recoverable only
    by fixing forward and re-dispatching at the tag.
    """
    project = PYPROJECT["project"]
    licence = project.get("license")
    assert isinstance(licence, str), (
        f"`project.license` is {type(licence).__name__} ({licence!r}); the TOML table form is "
        "deprecated with a removal date of 2027-Feb-18")
    assert licence == "MIT", licence
    assert declared_licence_files(), (
        "`license` is an SPDX expression and no `license-files` names the text; the wheel "
        "METADATA would carry no licence file at all")
    deprecated = [row for row in project["classifiers"] if row.startswith("License ::")]
    assert deprecated == [], (
        f"licence classifiers are deprecated and these remain: {deprecated}; the SPDX "
        "expression in `license` is the replacement")


def test_the_licence_form_matches_the_backend_floor_the_build_resolves():
    """`license` as a string and `license-files` are PEP 639, which setuptools reads from 77.

    A declaration the pinned backend interval cannot parse is a build that fails everywhere
    at once, so the two are asserted together rather than left to agree by luck.
    """
    floor = re.search(r"setuptools>=\s*(\d+)", " ".join(build_backend_requirements()))
    assert floor, f"no setuptools floor in {build_backend_requirements()}"
    assert int(floor.group(1)) >= 77, (
        f"`license = {PYPROJECT['project']['license']!r}` and `license-files` are PEP 639, "
        f"which setuptools reads from 77; the pinned floor is {floor.group(1)}")


def test_the_trigger_derivation_reads_the_licence_file_whichever_form_declares_it():
    """The reader moved with the key, and the move is pinned in both directions.

    The third case is the silent drop this test exists for: the PEP 639 form WITHOUT
    `license-files` names no file at all, and the old reader would have returned the same
    empty answer on the correct declaration.
    """
    assert declared_licence_files({"license": {"file": "LICENSE"}}) == ["LICENSE"]
    assert declared_licence_files({"license": "MIT", "license-files": ["LICENSE"]}) == ["LICENSE"]
    assert declared_licence_files({"license": "MIT"}) == []
    assert declared_licence_files() == ["LICENSE"]
    assert "LICENSE" in trigger_population()


# -- fail closed on the ref, in every workflow that faces the public (wave 10, F-017f3cc2) -
#
# release.yml was hardened for exactly this shape at wave 8: `workflow_dispatch` stays
# re-runnable but the tag gate is unconditional and refuses a non-tag `GITHUB_REF` before any
# publishing job runs. pages.yml did not get the clause. Its push trigger is fenced to
# `branches: [main]`, but `workflow_dispatch` carries no ref condition and the `deploy` job's
# only guard was `if: github.event.repository.private == false` — so a dispatch at any branch
# built THAT branch's site/ and handed it to `actions/deploy-pages`, the step the file's own
# header calls "the step that replaces what the public sees".
#
# LOW, and recorded as such: dispatching needs repository write access, which is also enough
# to push to main, so this is a consistency gap against a stated repo precedent rather than a
# privilege escalation — and it is inert today, because the repo is private and `deploy` is
# skipped. The fix keeps the useful half (a dispatch from a branch still BUILDS) and closes
# the irreversible one.
#
# THE NODE THIS CENSUS KEYS ON: the steps that hand something to the public —
# `actions/deploy-pages`, `npm publish`, `pypa/gh-action-pypi-publish` — walked out of the
# job bodies. Not the job's name, and not the workflow's: `deploy`, `npm` and `pypi` are
# three names for one property, and a fourth surface added under a different name joins the
# requirement on the day it lands.


def jobs_that_replace_a_public_surface():
    """(workflow, job) for every job whose steps hand something to the public."""
    markers = ("actions/deploy-pages", "npm publish", "gh-action-pypi-publish")
    out = []
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if any(marker in _code_only(body) for marker in markers):
                out.append((name, job))
    return out


#: Measured 2026-09-04. Three surfaces: the Pages deployment and the two registries.
PUBLIC_SURFACE_JOBS_TODAY = [("pages.yml", "deploy"), ("release.yml", "pypi"),
                             ("release.yml", "npm")]


def _ref_refusal_mechanism(workflow, job):
    """How `job` refuses a dispatch from an arbitrary branch, or None if it does not.

    Two mechanisms are legitimate and both are named rather than assumed: a `github.ref`
    clause in the job's own `if:`, or an unconditional `GITHUB_REF` gate in a job it needs
    (release.yml's tag gate, which `test_the_tag_gate_refuses_*` above actually RUNS).
    """
    condition = _job_if(_text(workflow), job)
    if condition is not None and "github.ref" in condition:
        return "if"
    for upstream in sorted(set(_job_needs(_text(workflow), job))):
        body = "\n".join(_job_lines(_text(workflow), upstream))
        if "GITHUB_REF" in body and "refs/tags/" in body:
            return f"needs:{upstream}"
    return None


def test_the_public_surface_census_is_the_jobs_in_the_files():
    assert jobs_that_replace_a_public_surface() == PUBLIC_SURFACE_JOBS_TODAY, (
        f"the jobs that replace a public surface are {jobs_that_replace_a_public_surface()}; "
        f"this file was written against {PUBLIC_SURFACE_JOBS_TODAY}")


@pytest.mark.parametrize("workflow,job", jobs_that_replace_a_public_surface())
def test_every_job_that_replaces_a_public_surface_fails_closed_on_the_ref(workflow, job):
    """`workflow_dispatch` reaches every workflow here, from any ref the dispatcher picks."""
    mechanism = _ref_refusal_mechanism(workflow, job)
    assert mechanism is not None, (
        f"{workflow}:{job} performs an irreversible public step and neither its own `if:` "
        f"({_job_if(_text(workflow), job)!r}) nor any job it needs refuses a non-main, "
        "non-tag ref; a `workflow_dispatch` from any branch reaches it")


PAGES_DEPLOY_ARRIVALS = [
    ("a push to main on a public repo", "push", "refs/heads/main", False, True),
    ("a dispatch at main on a public repo", "workflow_dispatch", "refs/heads/main", False, True),
    ("a dispatch at a branch on a public repo", "workflow_dispatch", "refs/heads/topic", False, False),
    ("a dispatch at a tag on a public repo", "workflow_dispatch", "refs/tags/v0.3.0", False, False),
    ("a dispatch at main while private", "workflow_dispatch", "refs/heads/main", True, False),
]


@pytest.mark.parametrize("arrival,event,ref,private,deploys", PAGES_DEPLOY_ARRIVALS)
def test_the_pages_deploy_job_runs_only_at_main_on_a_public_repo(arrival, event, ref, private,
                                                                 deploys):
    """The truth table, evaluated against the file's own condition.

    The third row is the measured hole and the first two are the direction the fix must not
    break — a gate that cannot pass would take the site's deploys with it.
    """
    condition = _job_if(_text("pages.yml"), "deploy")
    assert condition is not None, "pages.yml's deploy job lost its condition entirely"
    got = _eval_if(condition, {
        "github.event_name": event,
        "github.ref": ref,
        "github.event.repository.private": private,
    })
    assert got is deploys, (
        f"on {arrival} the deploy job {'runs' if got else 'does not run'}; "
        f"expected {'runs' if deploys else 'does not run'}. Condition: {condition!r}")


def test_the_ref_clause_check_goes_red_on_the_condition_pages_had():
    """The mutation: the visibility guard alone, which is true at every ref.

    Both halves are exercised — the predicate that reads a condition for a ref clause, and
    the evaluator, which said `True` for a dispatch at a topic branch.
    """
    before = "github.event.repository.private == false"
    assert "github.ref" not in before
    assert _eval_if(before, {
        "github.event_name": "workflow_dispatch",
        "github.ref": "refs/heads/topic",
        "github.event.repository.private": False,
    }) is True, "the pre-fix condition reads as refusing a branch dispatch"


# -- the rehearsal reaches neither registry (wave 18, F-64d03112) --------------------------
#
# `release.yml` grew a `workflow_dispatch` rehearsal so that the roughly two hundred lines of
# release shell that have never executed in a `release: published` run could be exercised
# BEFORE the one path in this repository with no compensator runs them for real. The entire
# difference between a rehearsal and a release is one YAML expression, `if:
# ${{ !inputs.rehearse }}`, carried by both publish jobs.
#
# Measured 2026-09-04 on `6b984dd`: `grep -rn rehearse tests/` returned NOTHING. Not one test
# named the input, the condition or the truth table, and the helper that would have to
# evaluate it — `_eval_if` — raised on the expression for every context, because it modelled
# neither the `inputs.` context nor unary `!`. The worst realistic consequence of that
# silence is a rehearsal that publishes to PyPI and npm for real, irreversibly.
#
# BOTH directions are pinned here. The expression read wrong is one; the other is the shape
# the file actually had on 041027c, where neither publish job carried an `if:` at all — that
# shape is fed to this same truth table below and must fail it.
#
# THE POPULATION IS WALKED, NOT LISTED: `jobs_that_replace_a_public_surface()` finds these
# jobs by the step that hands something to a registry, so a third publish job added under any
# name joins this truth table on the day it lands rather than on the day someone remembers.
#
# THE SIBLING CONDITIONS, enumerated: `.github/workflows/` holds exactly four `if:` keys
# (`grep -n '^\s*if:' .github/workflows/*.yml`, 2026-09-04). ci.yml:204's site-build clause is
# driven by `test_a_lockfile_change_is_scanned_however_it_arrives`, pages.yml:112's deploy
# clause by `test_the_pages_deploy_job_runs_only_at_main_on_a_public_repo`, and the remaining
# two are the pypi and npm clauses this section drives. No `if:` in this repo is unexercised
# after this wave, and all four now go through the same evaluator.


def publish_jobs():
    """(workflow, job) for every job in release.yml whose steps reach a registry."""
    return [(w, j) for w, j in jobs_that_replace_a_public_surface() if w == "release.yml"]


def _job_runs(text, job, ctx):
    """Whether `job` runs for one arrival. A job with NO `if:` runs on every event.

    That default is the load-bearing half: the mutation this section proves red is the
    DELETION of a condition, and a reader that treated a missing condition as "cannot say"
    would report the deletion as green.
    """
    condition = _job_if(text, job)
    if condition is None:
        return True
    return _eval_if(condition, ctx)


#: The rehearsal truth table, as the expression is written (ci-packaging's SEAM 2, wave 18).
#: `inputs` is EMPTY on `release: published`, so `inputs.rehearse` is null there rather than
#: false — modelled as an `inputs` context object with no `rehearse` in it, which is the row
#: a dotted-leaf context cannot spell at all. The two `runs` rows are the direction the fix
#: must not break: a gate that cannot pass would take every real release with it.
REHEARSE_ARRIVALS = [
    ("a real release", {"github.event_name": "release", "inputs": {}}, True),
    ("a dispatch with the rehearse box left unchecked",
     {"github.event_name": "workflow_dispatch", "inputs": {"rehearse": False}}, True),
    ("a rehearsal", {"github.event_name": "workflow_dispatch", "inputs": {"rehearse": True}},
     False),
]


def test_the_rehearsal_truth_table_covers_every_registry_job_release_yml_has():
    """A parametrised test over an empty population passes having asserted nothing.

    The population is compared against the census this file already pins rather than against
    a second written-down list, so the two cannot drift into disagreeing about what a
    publish job is.
    """
    assert publish_jobs(), (
        "no job in release.yml reaches a registry, so the truth table below asserts nothing; "
        "either the publish jobs moved or the marker walk stopped seeing them")
    assert publish_jobs() == [(w, j) for w, j in PUBLIC_SURFACE_JOBS_TODAY if w == "release.yml"]


def test_both_publish_jobs_carry_the_same_rehearsal_clause():
    """One clause, twice, character for character — the asymmetric state is the hazard.

    A rehearsal that published to one registry and not the other leaves exactly the split
    the visibility gate was hoisted into `verify` to prevent: a version taken on one index
    and absent from the other, with no compensator on either side.
    """
    conditions = {job: _job_if(RELEASE, job) for _, job in publish_jobs()}
    assert all(c is not None for c in conditions.values()), (
        f"a job that reaches a registry carries no condition at all: {conditions}")
    assert len(set(conditions.values())) == 1, (
        f"the publish jobs guard themselves with different expressions: {conditions}; a "
        "rehearsal that skips one and publishes to the other is the state they exist to rule "
        "out")


def _rehearse_input():
    """The `rehearse:` input's own keys, read out of release.yml's `workflow_dispatch:`."""
    out = {}
    for line in named_block(RELEASE, "rehearse", 6):
        key, _, value = line.strip().partition(":")
        if value.strip():
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def test_the_rehearse_input_is_a_boolean_that_defaults_to_not_rehearsing():
    """The premise of the middle row: a dispatch that sets nothing publishes.

    A default of `true` would invert the file's whole failure direction — every dispatched
    re-run of a failed release job would silently skip the publish it was dispatched to
    perform, and the operator would read a green run as a completed release.
    """
    declared = _rehearse_input()
    assert declared.get("type") == "boolean", (
        f"the rehearse input is declared {declared}; a non-boolean input arrives as a string, "
        "and every non-empty string is truthy in GitHub's expression language")
    assert declared.get("default") == "false", (
        f"the rehearse input defaults to {declared.get('default')!r}; a dispatch that sets "
        "nothing must publish")


@pytest.mark.parametrize("workflow,job", publish_jobs())
@pytest.mark.parametrize("arrival,ctx,publishes", REHEARSE_ARRIVALS)
def test_a_rehearsal_reaches_neither_registry(workflow, job, arrival, ctx, publishes):
    """The truth table, evaluated against the file's own condition, over BOTH publish jobs."""
    got = _job_runs(_text(workflow), job, ctx)
    assert got is publishes, (
        f"on {arrival} the {job} job {'publishes' if got else 'does not publish'}; expected "
        f"{'publishes' if publishes else 'does not publish'}. Condition: "
        f"{_job_if(_text(workflow), job)!r}")


@pytest.mark.parametrize("arrival,ctx,publishes", REHEARSE_ARRIVALS)
def test_the_rehearsal_runs_the_gate_job_it_exists_to_exercise(arrival, ctx, publishes):
    """A rehearsal that skipped `verify` would exercise nothing and prove nothing.

    The rehearsal exists to RUN the never-executed half — the tag gate, the visibility gate,
    both clean rooms, the `-O` step — and skip only the irreversible half. A condition that
    arrived on `verify` would leave a dispatch that reports green having done neither.
    """
    assert _job_runs(RELEASE, "verify", ctx) is True, (
        f"on {arrival} release.yml's verify job does not run; the rehearsal would report on "
        f"gates it never executed. Condition: {_job_if(RELEASE, 'verify')!r}")


def test_the_rehearsal_truth_table_goes_red_on_the_shape_release_yml_had():
    """The mutation: the two `if:` keys deleted, which is what 041027c actually carried.

    A truth table that only ever sees the corrected file proves nothing about the direction
    it guards. This is the measured pre-fix shape, fed to the same reader and the same
    evaluator: a rehearsal reaches BOTH registries.
    """
    lines = RELEASE.splitlines()
    mutated = "\n".join(line for line in lines
                        if line.strip() != "if: ${{ !inputs.rehearse }}")
    assert len(lines) - len(mutated.splitlines()) == 2, (
        "the mutation removed a number of lines other than the two publish clauses; it is no "
        "longer the shape this red proof claims to be")
    rehearsal = dict(REHEARSE_ARRIVALS[-1][1])
    for _, job in publish_jobs():
        assert _job_if(mutated, job) is None
        assert _job_runs(mutated, job, rehearsal) is True, (
            f"with its condition deleted, {job} still reads as skipped on a rehearsal; the "
            "truth table cannot fail on the shape the fix replaced")


REHEARSE_EXPRESSION_CASES = [
    ("the inputs context is empty, as it is on `release: published`", {"inputs": {}}, True),
    ("the operator dispatched with the box unchecked", {"inputs": {"rehearse": False}}, True),
    ("the operator dispatched a rehearsal", {"inputs": {"rehearse": True}}, False),
    ("a dotted-leaf context, the spelling every caller before wave 18 used",
     {"inputs.rehearse": True}, False),
    # GitHub's falsy set is null, false, 0 and the empty string; the STRING 'false' is
    # truthy, so `!` on it is false and the job skips. That row is here because it is the one
    # the boolean substitution could steal: `false` -> `False` running AFTER the reference
    # substitution would have read this as a publish.
    ("an input delivered as the string 'false'", {"inputs": {"rehearse": "false"}}, False),
]


@pytest.mark.parametrize("case,ctx,runs", REHEARSE_EXPRESSION_CASES)
def test_the_evaluator_reads_the_inputs_context_and_unary_not(case, ctx, runs):
    """The helper itself, on the live expression, before any job is asked about it.

    Measured on `6b984dd`: this call raised `SyntaxError` for every one of these contexts,
    because `_eval_if` modelled neither `inputs.` nor `!` and handed both to `eval`.
    """
    assert _eval_if("${{ !inputs.rehearse }}", ctx) is runs, f"on {case}"


@pytest.mark.parametrize("expr,ctx", [
    ("${{ !inputs.rehearse }}", {"github.event_name": "release"}),
    ("${{ !inputs.rehearse }}", {}),
    ("github.event_name == 'push'", {"inputs": {}}),
    ("needs.verify.result == 'success'", {"github.event_name": "release"}),
])
def test_an_unmodelled_context_reference_refuses_rather_than_deciding(expr, ctx):
    """A reference no context models has no answer here, and silence is the wrong one.

    The guard was keyed on the single literal `github.`, so every other context — `inputs.`
    first among them — reached `eval` as a bare name. It is a prefix set now, and it
    `raise`s: an `assert` here is deleted by the `-O` leg this suite runs, and what the
    deletion leaves behind is an evaluator that answers a publish-or-skip question from
    whatever an unresolved name evaluates to.
    """
    with pytest.raises(AssertionError, match="unmodelled context"):
        _eval_if(expr, ctx)


def test_the_job_condition_reader_does_not_read_a_step_condition_as_the_jobs():
    """A step's `if:` is not the job's, and the difference is four spaces of indent.

    Read loosely, a job whose job-level condition had been deleted would answer with the
    first `if:` of whatever step carried one — and the deletion, which is the exact edit the
    truth table above exists to catch, would read as a condition still in place.
    """
    step_only = "\n".join([
        "jobs:",
        "  npm:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - name: publish",
        "        if: ${{ !inputs.rehearse }}",
        "        run: npm publish",
    ])
    assert _job_if(step_only, "npm") is None, (
        "a step-level condition was read as the job's; the job runs on every arrival and "
        "this reader says it is guarded")
    rehearsal = dict(REHEARSE_ARRIVALS[-1][1])
    assert _job_runs(step_only, "npm", rehearsal) is True


# -- the licence map is a CI input (wave 10, seam from core-gates) ------------------------
#
# `docs/license-map.md` is the verified map this repo's licence gate is written against, and
# the suite now OPENS it by path: core-gates' licence-table census parses its rows and
# resolves the Commercial column against `RULED_COMPONENTS`. `paths_the_suite_guards()` picks
# that up by AST the day the census lands, but the FILTER is in this domain's file, so the
# requirement is pinned here as well — a re-fetch that adds or retires a kill is exactly the
# change CI must run on, and a guard that does not run on the change it guards is the shape
# the trigger census exists to close.


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_ci_runs_on_the_licence_map(trigger):
    """The licence gate is a non-negotiable, so its map is a build input like any other."""
    licence_map = "docs/license-map.md"
    assert os.path.isfile(os.path.join(REPO, licence_map)), (
        f"{licence_map} no longer exists; this requirement and the census that reads it must "
        "be retired deliberately, not left green")
    assert _pattern_hits(_paths_under(trigger), licence_map), (
        f"{trigger} builds nothing when {licence_map} changes, and the suite reads it by "
        f"path; the filters are {_paths_under(trigger)}")


# -- the suite's dependency list, and the manifest's third copy of it (F-968c4c54) --------
#
# `[project.optional-dependencies] dev = ["pytest>=8.0"]` was the manifest's only published
# statement of how to set up to run this suite. Nothing installed it -- measured 2026-09-04
# by grepping `.github/**` and `verify.ps1` for a `pip install` of `.[dev]`: none -- and
# nothing checked it. Measured from a wheel built in this worktree, `METADATA` carried
# `Requires-Dist: pytest>=8.0; extra == "dev"` and nothing else for the extra, so an
# installer of `armature-studio[dev]` got pytest plus the four runtime deps at their FLOORS
# and no `build`. A contributor following the manifest then gets an opencv that is not the
# version the aapose golden frames were measured against and reads the resulting red as a
# code regression rather than a toolchain one; or `build` is absent and the two tests that
# pin what the published sdist carries SKIP -- the silent-skip the repo already paid to close
# in CI. The repo's own law is stated in `.github/actions/sheet-fonts/action.yml:9-12`: two
# copies of one dependency list is how the font dependency forked.
#
# THE NODE THIS CENSUS KEYS ON: the distributions installed into the RUNNER's interpreter
# BEFORE the step that runs pytest, in every job that runs the suite. Not "the install line
# in ci.yml" (that is one file), and not "the four names we know about" (a census that knows
# the answer cannot notice a fifth). Ordering is what separates the suite's environment from
# the clean room's: `.github/actions/clean-room` installs `build` and `twine` for the leg
# that runs AFTER the suite, and twine is an artifact-moving tool the suite never imports --
# it is held to a version by the toolchain census above, which is its own home.


def _suite_install_tokens(workflow, job):
    """Distributions installed into the runner's interpreter before this job runs pytest."""
    body = "\n".join(_job_lines(_text(workflow), job))
    tokens = []
    for script in _run_scripts_in(_code_only(body)):
        # The step that RUNS the suite ends the collection. Keyed on the script's own verb
        # and not on the token `pytest`: the install line NAMES pytest, so a search for the
        # word alone truncates the list in the middle of the line it exists to read.
        if "pytest" in script and "install" not in script:
            break
        tokens.extend(_install_tokens(script))
    return tokens


#: The installer itself, never a dependency of anything. Everything else on an install line
#: that precedes the suite is a distribution the suite runs against.
INSTALLER = {"pip"}

_REQUIREMENT = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(.*)$")


def _split_requirement(token):
    """`opencv-python-headless==5.0.0.93` -> ('opencv-python-headless', '==5.0.0.93')."""
    match = _REQUIREMENT.match(token)
    assert match, token
    return match.group(1).lower().replace("_", "-"), match.group(2).strip()


def manifest_requirements():
    """name -> set of specifiers, over the runtime deps and every extra pyproject declares."""
    project = PYPROJECT["project"]
    groups = [project.get("dependencies", [])]
    groups.extend(project.get("optional-dependencies", {}).values())
    out = {}
    for group in groups:
        for spec in group:
            name, clause = _split_requirement(spec.split(";")[0].strip())
            out.setdefault(name, set()).add(clause)
    return out


def test_the_suite_dependency_census_is_the_jobs_that_run_it():
    """Size and membership before the property, and the two lists must BE one list.

    Two jobs run the suite; both install before it; and the whole point of the finding is
    that a list with two copies forks. Comparing them here is what makes "one list" a
    mechanical claim rather than a comment in release.yml.
    """
    jobs = jobs_that_run_the_suite()
    assert sorted(jobs) == [("ci.yml", "python-tests"), ("release.yml", "verify")], jobs
    lists = {f"{w}:{j}": _suite_install_tokens(w, j) for w, j in jobs}
    assert all(lists.values()), lists
    # Sorted: the claim is the distributions and their specifiers, not the order pip is
    # handed them. Measured 2026-09-04, the two lines differ only in where `pytest` sits,
    # and asserting on that would be asserting something that is not load-bearing.
    distinct = {tuple(sorted(v)) for v in lists.values()}
    assert len(distinct) == 1, (
        f"the two jobs that run the suite install different things: {lists}; two copies of "
        "one dependency list is how the font dependency forked"
    )


def test_the_manifest_states_the_dependency_list_the_suite_runs_against():
    """Every distribution CI installs for the suite is required by the package, at CI's pin.

    The direction that costs: a contributor or a downstream packager follows the manifest,
    gets an opencv that is not the version the golden frames were measured against, and reads
    the red as a code regression. The extra is not installed by CI -- CI's line is the one
    that runs -- so this test is what stops the two from drifting, exactly as the `build`
    specifier is already held to one string across three files.
    """
    declared = manifest_requirements()
    problems = []
    for workflow, job in jobs_that_run_the_suite():
        for token in _suite_install_tokens(workflow, job):
            name, clause = _split_requirement(token)
            if name in INSTALLER:
                continue
            if name not in declared:
                problems.append(f"{workflow}:{job} installs {token!r}; pyproject requires no {name!r}")
            elif clause and clause not in declared[name]:
                problems.append(
                    f"{workflow}:{job} installs {token!r}; pyproject requires {name!r} at "
                    f"{sorted(declared[name])} -- the pin CI runs is not the one the manifest publishes"
                )
    assert problems == [], "; ".join(problems)


def test_the_dependency_census_goes_red_on_a_forked_pin_and_on_a_name_it_never_heard_of():
    """The two hidden spellings, both driven through the real comparison.

    A pin that MOVED in CI and a distribution CI installs that the manifest never names are
    different failures, and a census keyed on the four names it was written against would see
    neither. Driven on synthetic install lines rather than on the tree, because the tree is
    the state this test exists to keep green.
    """
    declared = manifest_requirements()

    def unstated(line):
        out = []
        for token in _install_tokens(line):
            name, clause = _split_requirement(token)
            if name in INSTALLER:
                continue
            if name not in declared or (clause and clause not in declared[name]):
                out.append(token)
        return out

    assert unstated("python -m pip install --upgrade pip\n") == []
    assert unstated("python -m pip install matplotlib==3.12.0\n") == ["matplotlib==3.12.0"]
    assert unstated("python -m pip install scipy==1.0\n") == ["scipy==1.0"]
    assert unstated("python -m pip install numpy pillow pytest\n") == []


# -- no CI step decides an answer with a pipeline that can be signalled (F-00cc7a26) ------
#
# `.github/actions/sheet-fonts/action.yml:38-39` already refuses to write one, and says why:
# "No pipelines: `shell: bash` runs with `-o pipefail`, and `find` over a directory that does
# not exist on this image would then decide the answer instead of the face." The npm clean
# room carried the one pipeline in the three composite actions --
# `TARBALL="$PWD/$(ls -1 ./*.tgz | head -1)"` -- under `shell: bash` (GitHub runs
# `bash --noprofile --norc -eo pipefail {0}`) plus its own `set -eu`.
#
# `head -1` closes the pipe after the first line, so `ls` can be signalled (141); under
# pipefail the command substitution then fails and `set -e` aborts the step with nothing said
# about tarballs. The window is small -- one short line usually clears the pipe buffer before
# `head` exits -- which is exactly what makes it the bad kind of failure: a rare red on the
# gate that stands between the npm package and an irreversible publish, indistinguishable
# from a real packaging break, green on the retry. WITHOUT pipefail the same shape is the
# other defect: the pipeline reports the READER's status and a failing writer is swallowed.
# Both directions are why the rule is "no short-circuiting reader at the end of a pipeline"
# rather than "no pipeline when pipefail is set".
#
# THE NODE THIS CENSUS KEYS ON: the LAST stage of every pipeline in every `run:` script under
# `.github/` -- workflows and composite actions both, enumerated by `_all_run_scripts()`, so
# a step added to a fourth workflow or a second action is held the day it lands. Not the
# token `head -1`: `head -n 1`, `grep -q`, `read` and `sed`'s `q` end a pipe the same way,
# and a census that recognised one spelling would have passed on the other three.

#: Readers that can close the pipe while the writer is still producing. Each ends the
#: pipeline early BY DESIGN -- that is what they are for -- so each can leave the writer with
#: SIGPIPE and the pipeline with a status that describes the plumbing rather than the work.
SHORT_CIRCUITING_READERS = frozenset({"head", "grep", "read", "sed", "first", "q"})


def _pipeline_last_stages(script):
    """(line, last stage) for every pipeline in a script, comment lines dropped.

    `||` is not a pipe and is not split on. A pipeline continued over a line break (a line
    ending in `|`) is joined first, because a census that read one physical line at a time
    would see the writer and never the reader.
    """
    joined, buffer = [], ""
    for raw in _code_only(script).splitlines():
        line = buffer + raw
        buffer = ""
        stripped = line.rstrip()
        if stripped.endswith("|") and not stripped.endswith("||"):
            buffer = stripped + " "
            continue
        joined.append(line)
    if buffer:
        joined.append(buffer)

    out = []
    for line in joined:
        stages, current, i = [], "", 0
        while i < len(line):
            if line[i] == "|":
                if i + 1 < len(line) and line[i + 1] == "|":
                    current += "||"
                    i += 2
                    continue
                stages.append(current)
                current = ""
                i += 1
                continue
            current += line[i]
            i += 1
        stages.append(current)
        if len(stages) > 1:
            out.append((line.strip(), stages[-1].strip()))
    return out


def _reader_word(stage):
    """The command word of a pipeline's last stage, unwrapped from `$( ... )` and quotes."""
    text = stage.strip().strip(")").strip('"').strip("'").strip()
    for token in text.split():
        word = token.strip("$(){}\"';").split("/")[-1]
        if word and not word.startswith("-"):
            return word
    return ""


def _signalling_pipelines(script):
    """Every pipeline in a script whose last stage is a short-circuiting reader."""
    return [line for line, last in _pipeline_last_stages(script)
            if _reader_word(last) in SHORT_CIRCUITING_READERS]


def test_the_pipeline_census_is_every_run_script_under_dot_github():
    """Size and membership before the property: the walk must see the actions, not just the
    workflows -- the one pipeline this finding named lived in a composite action."""
    sources = {source for source, _ in _all_run_scripts()}
    assert sources >= {
        "ci.yml", "release.yml",
        ".github/actions/npm-clean-room/action.yml",
        ".github/actions/sheet-fonts/action.yml",
    }, sorted(sources)
    assert len(_all_run_scripts()) >= 10, len(_all_run_scripts())


_RUN_SCRIPTS = _all_run_scripts()


@pytest.mark.parametrize(
    "source,script", _RUN_SCRIPTS,
    ids=[f"{source}#{i}" for i, (source, _) in enumerate(_RUN_SCRIPTS)],
)
def test_no_ci_step_reads_an_answer_off_a_pipeline_that_can_be_signalled(source, script):
    """The property, over every run script in the tree."""
    offenders = _signalling_pipelines(script)
    assert offenders == [], (
        f"{source} decides something with a pipeline whose reader can close the pipe: "
        f"{offenders}; under pipefail the writer's SIGPIPE aborts the step with nothing said "
        "about what it was doing, and without pipefail the writer's failure is swallowed"
    )


def test_the_pipeline_census_sees_the_spellings_it_was_not_written_against():
    """The hidden spellings, shown red; and the shapes that must NOT be flagged.

    `head -1` is the one the finding named. `head -n 1`, `grep -q`, a `read` at the end of a
    pipe and `sed` are the same behaviour under other spellings, and a pipeline continued
    across a line break hides the reader from any line-at-a-time walk. `||` is not a pipe,
    and a last stage that consumes its whole input (`sort`, `wc`) ends nothing early.
    """
    red = [
        'TARBALL="$PWD/$(ls -1 ./*.tgz | head -1)"',
        'X=$(ls | head -n 1)',
        'ls | grep -q armature',
        'printf x | read v',
        'cat f | sed -n 1p',
        'ls \\\n  | head -1',
        'ls |\n  head -1',
    ]
    for script in red:
        assert _signalling_pipelines(script), f"not seen as a signalling pipeline: {script!r}"
    green = [
        'ls -la "$PREFIX/node_modules/.bin" || echo "(no node_modules/.bin at all)"',
        'find /usr/share/fonts -iname "$1" -print -quit 2>/dev/null || true',
        'ls | sort',
        'npm pack',
        'set -- ./*.tgz',
        '# a comment naming ls | head -1',
    ]
    for script in green:
        assert _signalling_pipelines(script) == [], f"flagged wrongly: {script!r}"


# -- a workflow does not cancel a step it cannot take back (F-d43de3e8) -------------------
#
# `concurrency.cancel-in-progress` is WORKFLOW-level: a second push cancels the first run
# wherever it is, including inside the step that performs the act. pages.yml carried `true`
# over a job whose one step is `actions/deploy-pages` -- the step this file's own header
# calls "the step that replaces what the public sees" -- so two quick site pushes could leave
# a Pages deployment cancelled part-way, the live site on the older build, and the cancelled
# run GREY rather than red: a deploy that did not happen with nothing reporting a failure.
# release.yml already sets `false` on the workflow whose steps cannot be taken back, and no
# comment in pages.yml recorded a decision either way.
#
# A job-level `concurrency:` block does NOT close this: workflow-level cancellation cancels
# the whole run regardless, which is why the setting has to be decided where it is written.
#
# This is a deliberate-deviation question, not a rule violation. The studio Actions rule
# mandates the concurrency block with `cancel-in-progress: true`, and GitHub's own Pages
# guidance is the documented exception. So the rule below is the studio's, with the exception
# stated in terms of the ACT rather than the filename: a workflow that performs something
# irreversible queues, everything else cancels.
#
# THE NODE THIS CENSUS KEYS ON: the STEP that performs the act, in either spelling. A
# published npm package is `run: npm publish` (a script), a PyPI upload and a Pages deploy
# are `uses:` a third-party action. A census that recognised only `uses:` would pass on
# release.yml's npm job, and one that read only `run:` would pass on both of the others.

#: Acts with no compensator, by what they DO. `git push` is here for the tag half: a pushed
#: tag is what release.yml's whole gate ordering exists to protect.
IRREVERSIBLE_RUN_TOKENS = (
    "npm publish", "twine upload", "gh release create", "git push", "docker push",
)
IRREVERSIBLE_ACTIONS = ("actions/deploy-pages", "gh-action-pypi-publish")


def irreversible_steps(text):
    """Every step in a workflow that performs an act with no compensator, both spellings."""
    found = []
    for source in _run_scripts_in(text):
        for token in IRREVERSIBLE_RUN_TOKENS:
            if token in _code_only(source):
                found.append(token)
    for line in text.splitlines():
        match = re.search(r"uses:\s*(\S+)", line)
        if not match:
            continue
        for action in IRREVERSIBLE_ACTIONS:
            if action in match.group(1):
                found.append(action)
    return sorted(set(found))


def cancel_in_progress(text):
    """The workflow-level `cancel-in-progress` value, or None if the block does not set one."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() != "concurrency:":
            continue
        for entry in block_at(lines, i):
            match = re.match(r"\s*cancel-in-progress:\s*(\S+)", entry)
            if match:
                return match.group(1).strip().lower() == "true"
        return None
    return None


#: Re-derived 2026-09-04 (wave 12). Equality, so a workflow that starts publishing something
#: joins the requirement on the day the step lands.
RECORDED_IRREVERSIBLE_WORKFLOWS = {
    "ci.yml": [],
    "pages.yml": ["actions/deploy-pages"],
    "release.yml": ["gh-action-pypi-publish", "npm publish"],
}


def test_the_irreversible_step_census_is_the_acts_in_the_files():
    """Size and membership before the property, in both spellings.

    release.yml is the proof that both halves of the walk are live: its PyPI upload is a
    `uses:` and its npm publish is a `run:`, and a census that read one of the two would
    still have looked green here.
    """
    got = {name: irreversible_steps(_text(name)) for name in workflow_files()}
    assert got == RECORDED_IRREVERSIBLE_WORKFLOWS, got


@pytest.mark.parametrize("workflow", workflow_files())
def test_every_workflow_states_a_concurrency_decision(workflow):
    """The studio rule's block is mandatory, and a missing value is not a decision."""
    assert cancel_in_progress(_text(workflow)) is not None, (
        f"{workflow} has no workflow-level `cancel-in-progress`; the studio Actions rule "
        "requires the concurrency block, and an unset value is whatever GitHub defaults to"
    )


@pytest.mark.parametrize("workflow", workflow_files())
def test_a_workflow_that_cannot_take_a_step_back_queues_rather_than_cancels(workflow):
    """The property: irreversible work queues; everything else cancels, per the studio rule."""
    text = _text(workflow)
    acts = irreversible_steps(text)
    cancels = cancel_in_progress(text)
    if acts:
        assert cancels is False, (
            f"{workflow} performs {acts} and cancels itself in progress; a second push "
            "cancels the first run wherever it is, and a cancelled run is grey rather than "
            "red -- the act did not happen and nothing reports a failure"
        )
    else:
        assert cancels is True, (
            f"{workflow} takes nothing back and does not cancel in progress; the studio "
            "Actions rule mandates `cancel-in-progress: true` where it is safe, and CI "
            "minutes spent on a superseded commit are minutes"
        )


def test_the_concurrency_census_reads_both_spellings_and_the_setting_itself():
    """The hidden spellings, driven through the real functions on synthetic workflows."""
    as_action = (
        "name: x\nconcurrency:\n  group: g\n  cancel-in-progress: true\njobs:\n"
        "  deploy:\n    steps:\n      - uses: actions/deploy-pages@abc123 # v4.0.5\n"
    )
    as_script = (
        "name: x\nconcurrency:\n  group: g\n  cancel-in-progress: true\njobs:\n"
        "  publish:\n    steps:\n      - name: publish\n        run: |\n"
        "          npm publish --provenance\n"
    )
    commented = (
        "name: x\nconcurrency:\n  group: g\n  cancel-in-progress: true\njobs:\n"
        "  safe:\n    steps:\n      - name: safe\n        run: |\n"
        "          # npm publish is what release.yml does\n"
        "          echo nothing\n"
    )
    no_block = (
        "name: x\njobs:\n  safe:\n    steps:\n      - name: s\n        run: echo nothing\n"
    )
    assert irreversible_steps(as_action) == ["actions/deploy-pages"]
    assert irreversible_steps(as_script) == ["npm publish"]
    assert irreversible_steps(commented) == [], (
        "naming an act in a comment is not performing it")
    assert cancel_in_progress(as_action) is True
    assert cancel_in_progress(as_script.replace("true", "false")) is False
    assert cancel_in_progress(no_block) is None


# =========================================================================================
# WAVE 23 — ci-packaging's own contract, in one block (SEAM 1). Everything below pins a
# property of `.github/**`, `pyproject.toml` or `.gitignore` that a wave-21 finding measured
# missing. Kept together, and at the end of the file, because the tests domain edits this
# same module in the same wave.
# =========================================================================================


# -- F-e3e6bdc8: an install in an artifact job STATES what it resolved ---------------------
#
# `pip install --quiet dist/*.whl` in `.github/actions/clean-room/action.yml` carried no
# `--no-deps`, so numpy, opencv-python-headless, pillow and matplotlib were resolved from the
# index at the unbounded specifiers pyproject declares — and `--quiet` then removed the one
# line saying what came out. Measured on `e8263a3`: `pip install --quiet` into a scratch venv
# emitted nothing at all, while the same install without the flag printed
# `Successfully installed armature-studio-0.3.0`. So the clean room could go red on release
# day, after `release: published` had fired, without the log saying which numpy or which cv2
# the probe ran against — a dependency-day break and a wheel defect reading as one red, on
# the one step with no compensator.
#
# The coordinator's wave-23 ruling: the wheel room keeps resolving FRESH (that is a user's
# experience of `pip install armature-studio`, and the thing the room exercises) and RECORDS
# what it resolved. This census holds every install in a job that produces or publishes a
# distribution to that.

#: The flags that suppress pip's report.
QUIET_FLAGS = ("--quiet", "-q")


def _silenced_installs(script):
    """The `pip install` lines of one script that report nothing.

    An install line is acceptable if it does not silence pip, OR if the script also runs a
    `pip freeze` — the fuller answer, which names the whole resolved set rather than only the
    distribution that was asked for.
    """
    code = _code_only(script)
    if "pip freeze" in code:
        return []
    bad = []
    for line in code.splitlines():
        stripped = line.strip()
        if "pip install" not in stripped:
            continue
        if any(flag in stripped.split() for flag in QUIET_FLAGS):
            bad.append(stripped)
    return bad


def _artifact_jobs():
    """Every (workflow, job) that produces or publishes a distribution — both walked."""
    jobs = set(jobs_that_produce_a_distribution())
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if "npm publish" in _code_only(body) or "gh-action-pypi-publish" in body:
                jobs.add((name, job))
    return sorted(jobs)


def test_every_install_in_an_artifact_job_reports_what_it_installed():
    """A silenced install in the job that publishes is a resolution nobody can read back."""
    assert _artifact_jobs(), "no job produces or publishes a distribution; this asserts nothing"
    offenders = []
    for workflow, job in _artifact_jobs():
        for script in job_scripts(workflow, job):
            offenders += [f"{workflow}:{job}: {line}" for line in _silenced_installs(script)]
    assert offenders == [], (
        f"these installs silence pip in a job that produces or publishes the artifact, and "
        f"the script never runs `pip freeze` either: {offenders}")


def test_the_install_report_check_goes_red_on_the_line_the_clean_room_had():
    """The mutation: the wheel room's install exactly as it stood before wave 23."""
    before = (
        "python -m venv /tmp/cleanroom\n"
        "/tmp/cleanroom/bin/python -m pip install --quiet dist/*.whl\n"
    )
    assert _silenced_installs(before) == [
        "/tmp/cleanroom/bin/python -m pip install --quiet dist/*.whl"]
    assert _silenced_installs(before + "/tmp/cleanroom/bin/python -m pip freeze\n") == []
    assert _silenced_installs("/tmp/cleanroom/bin/python -m pip install dist/*.whl\n") == []


# -- F-351f15cb: `npm test` runs where this repository measured it running -----------------
#
# ci.yml's `launcher` comment said "release.yml runs the same command in its publish job".
# Re-measured on `63191ee`: `grep -n -E 'npm test|self-?test' .github/workflows/release.yml`
# returns COMMENT LINES ONLY — the `Launcher self-test` step was deleted when the rule "no
# gate lives downstream of the fork" landed, release.yml records that deletion in its own
# words, and the citation in the file that HOLDS the only copy did not move with it. The
# consequence is this repository's headline defect class sitting on a coverage claim: a later
# seat trimming ci.yml's `launcher` job under the CI-minutes rule reads that sentence,
# concludes release.yml still runs the self-test, and deletes the only checkout-level
# launcher coverage in the repository.
#
# The claim is derived rather than restated, and `_code_only` is what makes it a claim about
# what RUNS: naming `npm test` in a comment — which both files now do, at length — is not
# running it.

#: Measured 2026-09-05 on `63191ee` by walking `_all_run_scripts()`: the sources whose run
#: scripts actually execute `npm test`. release.yml was on this list until the `Launcher
#: self-test` step was deleted from its `npm` job; ci.yml's comment claimed it still was.
NPM_TEST_SOURCES_TODAY = ["ci.yml"]


def _sources_running(command):
    """Every source under `.github/` whose run scripts execute `command`, comments excluded."""
    out = set()
    for source, script in _all_run_scripts():
        for line in _code_only(script).splitlines():
            if re.match(r"^\s*%s(\s|$)" % re.escape(command), line):
                out.add(source)
    return sorted(out)


def test_npm_test_runs_only_where_it_is_measured_to_run():
    """The coverage claim, derived. ci.yml's `launcher` job is the only place it runs."""
    running = _sources_running("npm test")
    assert running == NPM_TEST_SOURCES_TODAY, (
        f"`npm test` runs in {running}, and this repository measured it running in "
        f"{NPM_TEST_SOURCES_TODAY}. ci.yml's launcher comment is the only place that "
        "coverage is described; if the population moved, move the sentence with it.")


def test_the_npm_test_census_reads_what_runs_and_not_what_is_named():
    """The red proof, in the direction the defect ran: naming it is not running it.

    ci.yml now names `npm test` in prose several times and release.yml names it in the
    comment recording the deletion. A census that counted those would report the pre-fix
    sentence as true.
    """
    assert "npm test" in _text("release.yml"), (
        "release.yml no longer mentions `npm test` at all; this proof's operand is gone")
    assert "release.yml" not in _sources_running("npm test"), (
        "release.yml is counted as running `npm test`, and its only occurrences are comment "
        "lines — the census is keying on the text rather than on the code")


# -- F-e3c42cc1: a GitHub pre-release reaches neither registry -----------------------------
#
# `on.release.types: [published]` is the whole trigger and nothing read
# `github.event.release.prerelease`. `npm publish` carries no `--tag`, so npm defaults to
# `latest`: a pre-release published through this workflow would serve itself to every
# `npm i @mcptoolshop/armature-studio` until somebody ran `npm dist-tag add`. The coordinator
# ruled the branch fails CLOSED — the studio publishes no pre-release channel — which also
# makes the unfetched GitHub-side premise (that `published` fires for a pre-release) moot:
# if it fires, this gate stops it; if it does not, this gate never sees one.

PRERELEASE_STEP = step_containing(RELEASE, "A pre-release must not reach either registry")
PRERELEASE_SCRIPT = run_script(PRERELEASE_STEP)


def test_the_prerelease_gate_is_the_script_this_test_runs():
    """No runner-side expression inside it — the tag gate's discipline, for its reason."""
    assert "${{" not in PRERELEASE_SCRIPT, (
        f"a runner-side expression is inside the gate:\n{PRERELEASE_SCRIPT}")
    assert "github.event.release.prerelease" in PRERELEASE_STEP, (
        "the gate no longer reads github.event.release.prerelease into env")


def _drive_prerelease(event_name, value):
    """Run the pre-release gate's real script with an arrival and a flag value."""
    env = dict(os.environ, GITHUB_EVENT_NAME=event_name, RELEASE_IS_PRERELEASE=value)
    proc = subprocess.run(
        [BASH, "-s"],
        input=PRERELEASE_SCRIPT.replace("\r\n", "\n").encode("utf-8"),
        cwd=REPO, capture_output=True, env=env,
    )
    return subprocess.CompletedProcess(
        proc.args, proc.returncode,
        proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace"))


#: (arrival, the value the runner would substitute, whether the run may continue). The
#: `workflow_dispatch` rows carry an EMPTY value because `github.event.release` does not
#: exist on a dispatch — refusing that would delete the documented rehearsal, which is the
#: only way to exercise this file before a tag is public.
PRERELEASE_ARRIVALS = [
    ("release", "false", True),
    ("release", "true", False),
    ("release", "", False),
    ("release", "maybe", False),
    ("release", "False", False),
    ("workflow_dispatch", "", True),
]


@needs_shell
@pytest.mark.parametrize("event_name,value,proceeds", PRERELEASE_ARRIVALS)
def test_a_pre_release_refuses_before_the_publish_fork(event_name, value, proceeds):
    """Driven on every value, including the two GitHub can actually deliver."""
    got = _drive_prerelease(event_name, value)
    if proceeds:
        assert got.returncode == 0, (
            f"{event_name} with prerelease={value!r} halted; the rehearsal and every normal "
            f"release run through this step.\n{got.stdout}\n{got.stderr}")
    else:
        assert got.returncode != 0, (
            f"{event_name} with prerelease={value!r} passed the gate; npm would publish it "
            f"to the `latest` dist-tag.\n{got.stdout}\n{got.stderr}")
        assert "::error::" in got.stdout, got.stdout


@needs_shell
def test_the_prerelease_gate_goes_red_on_the_shape_release_yml_had():
    """The mutation: no gate at all — every release, pre-release or not, reached both jobs."""
    absent = subprocess.run(
        [BASH, "-s"], input=b"exit 0\n", capture_output=True, timeout=30)
    assert absent.returncode == 0, (
        "the harness itself refuses, so the rows above prove nothing about the gate")
    assert _drive_prerelease("release", "true").returncode != 0, (
        "with the gate present a pre-release still reaches the fork; the fix is not armed")


# -- F-9f395455: the npm-view probe separates E404 from a transport failure ----------------
#
# `if npm view "$NAME@$VER" version >/dev/null 2>&1` sent both streams to /dev/null and
# branched on the exit code alone, and `npm view` exits 1 for BOTH `not on the registry`
# (E404) and `could not ask`. Measured on `e8263a3` with no external egress:
# `npm view ... --registry=http://127.0.0.1:1/` exits 1 with `npm error code ECONNREFUSED`,
# and the step's own `if` shape took the same branch — fall through to `npm publish` — on a
# transport failure as on an E404, with the reason discarded. A re-run of a release whose npm
# publish had already succeeded then meets a blip, publishes, and is refused a version that
# already exists: red for having already succeeded, which is the outcome the step's own
# comment says it exists to prevent.

PUBLISH_SCRIPT = run_script(step_containing(RELEASE, "repository is private — publishing"))


def _publish_room(tmp_path, npm_stdout, npm_code):
    """A directory holding a stubbed `npm` and `node`, first on PATH.

    `npm publish` must never really run here, so the stub answers `view` and announces
    anything else — a publish that happened would otherwise be invisible to this harness.
    """
    room = tmp_path / "bin"
    room.mkdir()
    (room / "npm").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "view" ]; then\n'
        "  printf '%s\\n' " + json.dumps(npm_stdout) + "\n"
        "  exit " + str(npm_code) + "\n"
        "fi\n"
        'echo "STUB-NPM-RAN: $*"\n'
        "exit 0\n", encoding="utf-8", newline="\n")
    (room / "node").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        "  *name*) echo '@mcptoolshop/armature-studio' ;;\n"
        "  *) echo '0.3.0' ;;\n"
        "esac\n", encoding="utf-8", newline="\n")
    for name in ("npm", "node"):
        os.chmod(room / name, 0o755)
    return room


def _drive_publish(tmp_path, npm_stdout, npm_code, private="false", script=None):
    """Run the Publish step's real script against the stubbed registry."""
    room = _publish_room(tmp_path, npm_stdout, npm_code)
    env = dict(os.environ,
               PATH=str(room).replace("\\", "/") + os.pathsep + os.environ.get("PATH", ""),
               REPOSITORY_IS_PRIVATE=private)
    body = PUBLISH_SCRIPT if script is None else script
    proc = subprocess.run(
        [BASH, "-s"],
        input=("set -e\n" + body).replace("\r\n", "\n").encode("utf-8"),
        cwd=os.path.join(REPO, "npm"), capture_output=True, env=env,
        timeout=30,
    )
    return subprocess.CompletedProcess(
        proc.args, proc.returncode,
        proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace"))


@needs_shell
def test_the_probe_reads_a_registry_answer_as_already_published(tmp_path):
    got = _drive_publish(tmp_path, "0.3.0", 0)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "already on the registry" in got.stdout, got.stdout
    assert "STUB-NPM-RAN: publish" not in got.stdout, (
        "the version is already on the registry and this step published anyway")


@needs_shell
def test_the_probe_reads_an_E404_as_not_published_and_publishes(tmp_path):
    got = _drive_publish(tmp_path, "npm error code E404\nnpm error 404 Not Found", 1)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "E404" in got.stdout, got.stdout
    assert "STUB-NPM-RAN: publish" in got.stdout, (
        "the registry said the version is absent and this step did not publish")


@needs_shell
def test_the_probe_refuses_a_transport_failure_instead_of_publishing(tmp_path):
    """The measured operand: ECONNREFUSED, which exits 1 exactly as an E404 does."""
    got = _drive_publish(
        tmp_path, "npm error code ECONNREFUSED\nnpm error network request to registry failed", 1)
    assert got.returncode != 0, (
        "a transport failure fell through to `npm publish`; the probe cannot tell 'not "
        f"published' from 'could not ask'.\n{got.stdout}\n{got.stderr}")
    assert "STUB-NPM-RAN: publish" not in got.stdout, got.stdout
    assert "ECONNREFUSED" in got.stdout, (
        "the refusal discards the registry's own message, so the log does not say why")


@needs_shell
def test_the_probe_check_goes_red_on_the_shape_the_publish_step_had(tmp_path):
    """The mutation: both streams discarded, branching on the exit code alone.

    Fed the same ECONNREFUSED stub, the pre-fix shape PUBLISHES. That is what makes the row
    above a proof rather than a description.
    """
    before = (
        'NAME=$(node -p "x.name")\n'
        'VER=$(node -p "x.version")\n'
        'if npm view "$NAME@$VER" version >/dev/null 2>&1; then\n'
        '  echo "::notice::already on the registry"\n'
        "else\n"
        "  npm publish --access public\n"
        "fi\n"
    )
    got = _drive_publish(
        tmp_path, "npm error code ECONNREFUSED\nnpm error network request to registry failed",
        1, script=before)
    assert got.returncode == 0 and "STUB-NPM-RAN: publish" in got.stdout, (
        "the pre-fix shape no longer publishes on a transport failure; this red proof no "
        f"longer reproduces the defect it describes.\n{got.stdout}\n{got.stderr}")


# -- F-2cb02bed / F-1c5dc527 / F-481b512c / F-83ce864e: the clean room's two files ---------
#
# The probe and the classifier gate are both FILES beside the action now, run by the action
# and by `verify.ps1`'s leg 3. The classifier gate's own contract — exit 2 for a refusal,
# 1 for a crash, a `CLASSIFIER_GATE_HALT ` line carrying gate, clause and evidence, a
# `CLASSIFIER_GATE_OK ` line stating judged AND skipped — is driven here as a subprocess,
# because the gate runs on a runner python with only `trove-classifiers` installed and cannot
# import `armature_core.parts.run_tool_main`.

CLEAN_ROOM_DIR = os.path.join(REPO, ".github", "actions", "clean-room")
CLASSIFIER_GATE = os.path.join(CLEAN_ROOM_DIR, "classifier_gate.py")

needs_trove = pytest.mark.skipif(
    __import__("importlib.util", fromlist=["util"]).find_spec("trove_classifiers") is None,
    reason="the classifier gate reads PyPI's own list through trove-classifiers")


def test_both_clean_room_callers_run_the_one_probe_file():
    """One text, two callers — the law the classifier gate beside it already followed."""
    with open(os.path.join(REPO, "verify.ps1"), encoding="utf-8") as fh:
        verify = fh.read()
    assert "lazy_import_probe.py" in clean_room_script(), (
        "the clean-room action no longer runs the probe FILE; a heredoc copy is a second "
        "implementation of one gate, and no census under `.github/` can see verify.ps1's")
    assert "lazy_import_probe.py" in verify, (
        "verify.ps1 no longer runs the probe file; its leg 3 mirrors the release gate and "
        "its DESCRIPTION equates a green local run to a green CI run")
    probe = lazy_import_probe_source()
    for caller, text in (("the clean-room action", clean_room_script()),
                         ("verify.ps1", verify)):
        assert "aapose.blank_canvas" not in _code_only(text), (
            f"{caller} carries an inline copy of the probe body again")
    assert "aapose.blank_canvas" in probe, "the probe file no longer holds the probe"


def _run_gate(dist_dir):
    return subprocess.run(
        [sys.executable, CLASSIFIER_GATE, str(dist_dir)],
        capture_output=True, text=True, cwd=REPO)


def _halt_record(stdout):
    """The strict-JSON record on the `CLASSIFIER_GATE_HALT ` line."""
    for line in stdout.splitlines():
        if line.startswith("CLASSIFIER_GATE_HALT "):
            return json.loads(line[len("CLASSIFIER_GATE_HALT "):])
    raise AssertionError(f"no halt line in:\n{stdout}")


def _wheel(path, rows):
    """A minimal `.whl` whose METADATA carries `rows`."""
    import zipfile as _zip
    body = "Metadata-Version: 2.1\nName: fake\nVersion: 0.1\n"
    body += "".join("Classifier: %s\n" % r for r in rows)
    with _zip.ZipFile(path, "w") as archive:
        archive.writestr("fake-0.1.dist-info/METADATA", body)
    return path


@needs_trove
def test_the_classifier_gate_passes_a_clean_dist_and_states_both_counts(tmp_path):
    """The success direction, and the sentinel earned by an effect."""
    dist = tmp_path / "dist"
    dist.mkdir()
    _wheel(dist / "fake-0.1-py3-none-any.whl", ["Development Status :: 4 - Beta"])
    got = _run_gate(dist)
    assert got.returncode == 0, got.stdout + got.stderr
    line = [x for x in got.stdout.splitlines() if x.startswith("CLASSIFIER_GATE_OK ")]
    assert len(line) == 1, got.stdout
    record = json.loads(line[0][len("CLASSIFIER_GATE_OK "):])
    assert record["judged"] == 1 and record["skipped"] == [], record


@needs_trove
def test_the_classifier_gate_refuses_the_row_pypi_400d_this_project_on(tmp_path):
    """The failure class this gate exists for, and the exit code the convention reserves."""
    dist = tmp_path / "dist"
    dist.mkdir()
    _wheel(dist / "fake-0.1-py3-none-any.whl",
           ["Development Status :: 4 - Beta", "Topic :: Scientific :: Image Processing"])
    got = _run_gate(dist)
    assert got.returncode == 2, (
        f"a refusal exited {got.returncode}; this repository's convention gives a deliberate "
        f"refusal 2 and reserves 1 for a crash.\n{got.stdout}\n{got.stderr}")
    record = _halt_record(got.stdout)
    assert record["gate"] == "CLASSIFIER", record
    assert record["evidence"]["clause"] == "classifier-row-pypi-does-not-have", record
    assert any("Image Processing" in r for r in record["evidence"]["rows"]), record


@needs_trove
def test_the_classifier_gate_refuses_an_empty_population(tmp_path):
    """An affirmative verdict over nothing, upstream of the publish fork."""
    dist = tmp_path / "dist"
    dist.mkdir()
    got = _run_gate(dist)
    assert got.returncode == 2, got.stdout + got.stderr
    assert _halt_record(got.stdout)["evidence"]["clause"] == "empty-population"


@needs_trove
def test_the_classifier_gate_refuses_a_file_it_cannot_read(tmp_path):
    """WAVE 23, `F-83ce864e` — the population is the DIRECTORY, not an extension.

    Measured on `e8263a3` with the pre-fix gate: a valid wheel beside a `fake-0.1.zip` whose
    PKG-INFO carried the banned row printed `every row present`, exited 0, and never
    mentioned the `.zip` — while `release.yml` uploads the whole of `dist/` and the publish
    action publishes that directory. `.zip` is in twine's own `DIST_EXTENSIONS`.
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    _wheel(dist / "fake-0.1-py3-none-any.whl", ["Development Status :: 4 - Beta"])
    (dist / "fake-0.1.zip").write_bytes(b"PK\x03\x04 not really")
    got = _run_gate(dist)
    assert got.returncode == 2, (
        f"a file this gate cannot read sat in dist/ and the gate exited {got.returncode}; "
        f"the publish step uploads the whole directory.\n{got.stdout}\n{got.stderr}")
    record = _halt_record(got.stdout)
    assert record["evidence"]["clause"] == "dist-holds-a-file-this-gate-cannot-read", record
    assert record["evidence"]["skipped"] == ["fake-0.1.zip"], record
    assert record["evidence"]["judged"] == 1, record


@needs_trove
def test_a_classifier_gate_crash_exits_1_and_a_refusal_exits_2(tmp_path):
    """THREE outcomes, not two — the shape `armature_core.parts.halt_outcome` defines."""
    dist = tmp_path / "dist"
    dist.mkdir()
    _wheel(dist / "fake-0.1-py3-none-any.whl", ["Development Status :: 4 - Beta"])
    crash = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys;sys.argv=['g','%s'];"
         "m=runpy.run_path(r'%s');"
         "m['run_gate_main'](lambda a: (_ for _ in ()).throw(ValueError('boom')), sys.argv)"
         % (str(dist).replace("\\", "/"), CLASSIFIER_GATE)],
        capture_output=True, text=True, cwd=REPO)
    assert crash.returncode == 1, crash.stdout + crash.stderr
    record = _halt_record(crash.stdout)
    assert record["error"] == "ValueError" and record["evidence"] is None, record
    assert record["outcome"].startswith("FAILED"), record


#: MEASURED at wave 26: the typed refusals each CPython file under `.github/actions/**`
#: carries. A FLOOR per file, never an equality, so a seventh refusal is welcome and a
#: deleted one is not — and the KEYS are asserted against the directory below, so the next
#: file to land there joins this census on that day rather than on the day someone
#: remembers. `classifier_gate.py`'s six are wave 23's; `lazy_import_probe.py`'s one is the
#: source-tree premise guard, which until wave 26 was a bare `SystemExit(<string>)` at exit
#: 1 — the code this repository reserves for `this tool crashed`, on the guard that decides
#: whether the wheel room's verdict means anything.
ANDON_REFUSALS_UNDER_ACTIONS = {
    "classifier_gate.py": 6,
    "lazy_import_probe.py": 1,
}


def cpython_files_under_actions():
    """Every `.py` under `.github/actions/`, enumerated off the disk — never a written list.

    WAVE 26, `F-3b17a904`: this census was keyed on ONE PATH CONSTANT (`CLASSIFIER_GATE`),
    so the second CPython file in that directory — added by the SAME wave, and already named
    in `GUARDED_TODAY` — joined the tree outside it and kept a bare refusal for three waves.
    """
    import glob

    return sorted(glob.glob(os.path.join(REPO, ".github", "actions", "**", "*.py"),
                            recursive=True))


def _local_exception_classes(tree):
    """The names of the Exception subclasses a module defines itself."""
    return {n.name for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef)
            and any(isinstance(b, ast.Name) and b.id.endswith(("Exception", "Error",
                                                               "Failure"))
                    for b in n.bases)}


def test_the_actions_cpython_population_is_the_directory_and_not_a_list():
    """The population before the property: the table's keys ARE the directory."""
    got = sorted(os.path.basename(p) for p in cpython_files_under_actions())
    assert got == sorted(ANDON_REFUSALS_UNDER_ACTIONS), (
        f"{got} sit under .github/actions/ and the refusal census names "
        f"{sorted(ANDON_REFUSALS_UNDER_ACTIONS)}; a file that joins that directory joins "
        "this census on the day it lands")


@pytest.mark.parametrize("path", cpython_files_under_actions(),
                         ids=lambda p: os.path.basename(p))
def test_the_classifier_gate_refuses_by_a_named_andon_and_never_by_a_bare_exit(path):
    """WAVE 23, `F-481b512c` — six bare `raise SystemExit("::error::...")` refusals.

    No class, no clause, no evidence, and exit 1 — the code
    `tests/test_packaging.py::test_a_gate_refusal_exits_2_with_its_sentinel_and_a_crash_exits_1`
    reserves for `this tool crashed`. Read by AST so a seventh refusal added in the old shape
    joins this census on the day it lands.

    WAVE 26, `F-3b17a904` — PARAMETRISED OVER THE DIRECTORY. The census opened
    `classifier_gate.py` alone, so `lazy_import_probe.py` beside it kept exactly the shape
    this test exists to refuse: `raise SystemExit("clean-room probe imported the source
    tree: " + ...)`. Driven in a worktree with the venv python before the fix, the refusal
    path and a crash path both printed one line and EXITED 1 — byte-indistinguishable, on
    the last packaging step of the release gate, while `release: published` has fired.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    bare = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        call = node.exc
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)):
            continue
        if call.func.id != "SystemExit" or not call.args:
            continue
        # `raise SystemExit(main(argv))` is the handler's own idiom, lifted from
        # `armature_core.parts.run_tool_main` -- an exit code, not a message. What this
        # census is looking for is the shape the six refusals had: a SystemExit carrying a
        # STRING, which is a refusal with no class, no clause and no evidence, exiting 1.
        arg = call.args[0]
        speaks = (isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                  or isinstance(arg, ast.JoinedStr)
                  or (isinstance(arg, ast.BinOp)
                      and isinstance(arg.left, ast.Constant)
                      and isinstance(arg.left.value, str)))
        if speaks:
            bare.append(getattr(node, "lineno", "?"))
    stem = os.path.basename(path)
    assert bare == [], (
        f"{stem} raises a bare SystemExit at lines {bare}; a refusal in this "
        "repository is a NAMED andon carrying a clause and evidence, and exits 2")
    local = _local_exception_classes(tree)
    assert local, f"{stem} defines no andon class of its own"
    raises = [n for n in ast.walk(tree)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
              and isinstance(n.exc.func, ast.Name)
              and n.exc.func.id in local]
    floor = ANDON_REFUSALS_UNDER_ACTIONS[stem]
    assert len(raises) >= floor, (
        f"{stem} carries {len(raises)} typed refusals and had {floor}; a refusal that "
        "leaves this file is a check that stopped checking")
    for node in raises:
        assert len(node.exc.args) >= 2, (
            f"the refusal at line {node.lineno} names no clause")
        assert isinstance(node.exc.args[1], ast.Constant), (
            f"the clause at line {node.lineno} is not a literal a reader can grep for")


# ===========================================================================
# WAVE 26 (ci-packaging) — the clean room's two files, and the two rooms
# ===========================================================================
#
# `F-3b17a904` (the probe's halt contract), `F-1d0f6c82` (the cleared-`dist/` invariant
# reaching the action) and `F-6e4d3b71` (the two scratch rooms). Everything below reads or
# drives files under `.github/`, which is what this module is for.

LAZY_IMPORT_PROBE_HALT_TOKEN = "LAZY_IMPORT_PROBE_HALT "
LAZY_IMPORT_PROBE_OK_TOKEN = "LAZY_IMPORT_PROBE_OK "


def _run_probe(env_extra=None):
    """Drive the probe as a subprocess, the way both of its callers do."""
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, LAZY_IMPORT_PROBE],
                          capture_output=True, text=True, cwd=REPO, env=env)


def _probe_halt_record(stdout):
    """The strict-JSON record on the probe's halt line."""
    for line in stdout.splitlines():
        if line.startswith(LAZY_IMPORT_PROBE_HALT_TOKEN):
            return json.loads(line[len(LAZY_IMPORT_PROBE_HALT_TOKEN):])
    raise AssertionError(f"no halt line in:\n{stdout}")


def test_the_probes_source_tree_premise_refuses_by_a_named_andon_and_exits_2():
    """RED before wave 26: one line on stderr, no halt line, exit 1.

    The premise this guard checks decides whether everything after it is a claim about the
    ARTIFACT or about the checkout sitting one directory up. With `tools/` on `PYTHONPATH`,
    `armature_core` resolves to the source tree and the guard must fire — as a refusal a
    reader can tell apart from a crash, on the last packaging step before an irreversible
    publish.
    """
    got = _run_probe({"PYTHONPATH": os.path.join(REPO, "tools")})
    assert got.returncode == 2, (
        f"the probe refused and exited {got.returncode}; this repository's convention gives "
        f"a deliberate refusal 2 and reserves 1 for a crash.\n{got.stdout}\n{got.stderr}")
    record = _probe_halt_record(got.stdout)
    assert record["gate"] == "LAZY_IMPORT", record
    assert record["evidence"]["clause"] == "probe-imported-the-source-tree", record
    assert record["evidence"]["resolved_to"].endswith("aapose.py"), record
    assert record["outcome"].startswith("HALTED"), record


def test_a_probe_crash_exits_1_and_is_told_apart_from_its_refusal():
    """THREE outcomes, not two — the shape the gate one file over already had.

    Before wave 26 a crash and a refusal were the same exit code AND the same shape, so `the
    probe ran against the checkout instead of the wheel` — a rig or runner configuration
    fault — was indistinguishable from `the wheel cannot call cv2`, the artifact fault the
    room exists to catch.
    """
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONPATH"] = os.path.join(REPO, "tools")
    crash = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys;sys.argv=['probe'];"
         # `runpy.run_path` does NOT put the file's directory on sys.path; `python <file>`,
         # which is what both callers run, does. Without this the probe's own
         # `from classifier_gate import run_gate_main` cannot resolve and this fixture would
         # report a crash it manufactured rather than the one it is driving.
         "sys.path.insert(0, r'%s');"
         "m=runpy.run_path(r'%s');"
         "m['run_gate_main'](lambda a: (_ for _ in ()).throw(ValueError('boom')), sys.argv,"
         " tool=m['TOOL'], gate=m['GATE'], halt=m['HALT'],"
         " refusal_class=m['LazyImportProbeFailure'])"
         % (CLEAN_ROOM_DIR.replace("\\", "/"),
            LAZY_IMPORT_PROBE.replace("\\", "/"))],
        capture_output=True, text=True, cwd=REPO, env=env)
    assert crash.returncode == 1, crash.stdout + crash.stderr
    record = _probe_halt_record(crash.stdout)
    assert record["error"] == "ValueError" and record["evidence"] is None, record
    assert record["outcome"].startswith("FAILED"), record
    assert record["tool"] == "lazy_import_probe", record


def test_the_probe_adopts_the_handler_beside_it_and_does_not_spell_a_third_one():
    """ADOPT THE HOME. `armature_core.parts.run_tool_main` is not importable in the clean
    room — that is the recorded exception `classifier_gate.py` was written under — and the
    answer to a second caller is to IMPORT that local handler, not to copy it.
    """
    with open(LAZY_IMPORT_PROBE, encoding="utf-8") as fh:
        probe = fh.read()
    tree = ast.parse(probe)
    imported = {alias.name for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module == "classifier_gate"
                for alias in node.names}
    assert "run_gate_main" in imported, (
        "the probe no longer imports the handler beside it; a copy of the halt contract "
        "here would be its THIRD spelling in this repository")
    assert "def run_gate_main" not in probe, (
        "the probe defines its own `run_gate_main`; that is the copy this rule forbids")
    for token in (LAZY_IMPORT_PROBE_HALT_TOKEN, LAZY_IMPORT_PROBE_OK_TOKEN):
        assert token in probe, f"the probe no longer prints {token!r}"
    assert "CLASSIFIER_GATE_HALT" not in probe, (
        "the probe prints the OTHER tool's halt prefix; an operator keying on the token "
        "would attribute its refusal to the classifier gate")


def test_the_halt_contract_module_imports_with_no_third_party_package_present():
    """The blocker that made `adopt the home` impossible until it was measured.

    `classifier_gate.py` read the trove list at MODULE scope, and the probe runs under the
    wheel clean room's interpreter — a venv holding armature-studio and its four runtime
    dependencies and nothing else. `import classifier_gate` there was a ModuleNotFoundError
    before a line of the handler was reachable. The import moved into `main`, which is the
    only thing that reads the list. Driven here with the name BLOCKED, so a module-level
    import added back fails on the day it lands rather than on release day inside the room.
    """
    probe = subprocess.run(
        [sys.executable, "-c",
         "import sys\n"
         "class Block:\n"
         "    def find_spec(self, name, path=None, target=None):\n"
         "        if name.split('.')[0] == 'trove_classifiers':\n"
         "            raise ModuleNotFoundError(name)\n"
         "        return None\n"
         "sys.meta_path.insert(0, Block())\n"
         "sys.path.insert(0, r'%s')\n"
         "import classifier_gate\n"
         "print('imported', classifier_gate.run_gate_main.__name__)\n"
         % CLEAN_ROOM_DIR.replace("\\", "/")],
        capture_output=True, text=True, cwd=REPO)
    assert probe.returncode == 0, (
        "classifier_gate.py cannot be imported without trove-classifiers, so the probe "
        f"beside it cannot adopt its handler in the clean room:\n{probe.stderr}")
    assert "imported run_gate_main" in probe.stdout, probe.stdout


def _scratch_dirs_created(script):
    """Every directory a composite action's script creates a virtual environment in."""
    return sorted(set(re.findall(r"(?m)^\s*[^#\n]*?-m venv\s+\"?([^\s\"]+)\"?", script)))


def test_every_scratch_room_a_composite_action_creates_is_removed_first():
    """WAVE 26, `F-6e4d3b71` — a room whose whole name is `clean` met a directory it did
    not create.

    Creating a virtual environment over an existing directory REUSES it rather than emptying
    it, so a fixed path with no removal first can hold a previous run's packages — and the
    room whose stated job is catching a wheel that installs but cannot run is then GREEN on
    a wheel missing a module the stale venv still carries. Derived over `action_files()`, so
    a third room anywhere under `.github/actions/` is held the day it lands. The sibling npm
    room already did both halves; this is the census that keeps them together.
    """
    for path in action_files():
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        rel = os.path.relpath(path, REPO).replace("\\", "/")
        rooms = _scratch_dirs_created(text)
        for room in rooms:
            assert "RUNNER_TEMP" in room or room.startswith("$"), (
                f"{rel} creates a scratch room at the fixed path {room!r}; the runner's own "
                "scratch directory is `$RUNNER_TEMP`, and the sibling npm clean room "
                "already reads it")
            assert re.search(r"rm -rf[^\n]*%s" % re.escape(room), text), (
                f"{rel} creates a scratch room at {room!r} and never removes one first; "
                "a venv built over an existing directory reuses it")


def test_the_scratch_room_census_can_see_a_room(  # noqa: D401
):
    """The direction the predicate must not bound: a walk that matched nothing would make
    the assertion above vacuously green."""
    assert _scratch_dirs_created(clean_room_script()), (
        "the clean-room action's rooms are invisible to this walk, so the census above "
        "asserts nothing about the action it exists for")
    assert _scratch_dirs_created("echo nothing here") == []


# The cleared-`dist/` invariant (`F-1d0f6c82`) is asserted of BOTH implementations in
# `tests/test_verify_script.py::test_the_clear_is_followed_by_a_check_before_anything_ranges_over_dist`,
# which is where the other four parity axes already live. A second spelling here is exactly
# what the finding was about, so there is not one.


def _action_names_its_artifacts(text):
    """Does the clean-room action NAME the two artifacts, or hand a glob to its tools?

    The question is the SELECTION, not a token: `dist/*.whl` and `dist/*.tar.gz` handed to
    pip are a selection nobody checked, and under `shell: bash` (`-eo pipefail`) plus the
    step's `set -eu` an unmatched glob reaches the tool as the literal pattern.

    `twine check dist/*` is deliberately NOT in this population, and neither is the
    classifier gate: both range over the DIRECTORY for the reason the gate's own docstring
    records — release.yml uploads the whole of `dist/` and the publish action publishes what
    it uploads, so the directory is the right population for a verdict. What must never be a
    glob is the selection handed to an INSTALL, which names one file.
    """
    derived = "tomllib" in text and "project" in text and "version" in text
    globbed = [line.strip() for line in text.splitlines()
               if not line.strip().startswith("#")
               and re.search(r"pip install[^\n]*dist[/\\]\*", line)]
    return derived, globbed


def test_the_clean_room_action_names_the_artifacts_it_installs_and_checks_its_shims():
    """WAVE 26, `F-2a90c1ee` — three implementations select the published artifacts and only
    two named what they were looking for.

    In this action nothing was checked before it was used: `twine check dist/*`,
    `pip install --no-deps dist/*.tar.gz`, `pip install dist/*.whl`, and an sdist console
    script run with NO existence check at all — the new half, since wave 14 added that room
    and wave 23 gave `verify.ps1` a by-name refusal for exactly it. The other two
    implementations already refuse by name: `verify.ps1`'s leg 3 derives both filenames from
    `project.name` / `project.version` by PEP 503/427 normalisation and lists what `dist/`
    holds, and `.github/actions/npm-clean-room/action.yml` refuses an unmatched glob and a
    missing shim in its own words.

    THE PARITY FRAMING IS NOT HERE, deliberately: tests' `F-1ebf099e` owns the two-text
    parity census in `tests/test_verify_script.py` (wave-26 SEAM 2), and this asserts the
    property of the action, which is ci-packaging's own file. One property, two anchors would
    be the second spelling this wave's method forbids; if the parity census lands with this
    axis in it, this test is subsumed and deletable.
    """
    action = clean_room_script()
    derived, globbed = _action_names_its_artifacts(action)
    assert derived, (
        "the clean-room action does not derive its artifact names from the manifest; a build "
        "that renames or drops one then fails with a message about a PATH, in the job whose "
        "whole purpose is to say what the artifact IS")
    assert globbed == [], (
        f"the action hands a glob to the tool that installs the artifact: {globbed}")
    code = _code_only(action)
    assert "the build produced no" in code, (
        "the action installs an artifact with no by-name refusal above it")
    install = re.search(r"pip install[^\n]*(\$SDIST|\$WHEEL|dist)", code)
    assert install and code.index("the build produced no") < install.start(), (
        "the action names its artifacts only AFTER installing them")
    #: the console script each room installs, checked before it is run. `verify.ps1` gained
    #: this refusal at wave 23 for the sdist room and this action did not move with it; a
    #: missing `[project.scripts]` entry point otherwise dies as a bash
    #: `No such file or directory` at exit 127, in the step with no compensator downstream.
    assert code.count("provides no armature command") == 2, (
        "both rooms must refuse by name when the install provides no console script; "
        f"{code.count('provides no armature command')} of them do")


def test_the_artifact_selection_census_goes_red_on_the_leg_this_action_had():
    """The direction the predicate must bound, on the real pre-fix text.

    A census that could not see `pip install dist/*.whl` would be green on the shape it
    exists to refuse, so the shape is driven rather than reasoned about.
    """
    before = ("        python -m build\n"
              "        python -m twine check dist/*\n"
              "        python -m venv /tmp/cleanroom-sdist\n"
              "        /tmp/cleanroom-sdist/bin/python -m pip install --no-deps dist/*.tar.gz\n"
              "        python -m venv /tmp/cleanroom\n"
              "        /tmp/cleanroom/bin/python -m pip install dist/*.whl\n")
    derived, globbed = _action_names_its_artifacts(before)
    assert not derived, "the pre-fix text reads as deriving its names; the census is blind"
    assert len(globbed) == 2, globbed
    assert "provides no armature command" not in before


# ===========================================================================
# WAVE 23 (tests) — `_code_only` also blanks STRING LITERALS  ·  F-2cb02bed
# ===========================================================================
#
# Coordinator ruling, wave-23 SEAM 3: ci-packaging carries the pass-mutation fixture beside
# `lazy_import_probe_source()` in its own commit (a fixture that reads a helper only one
# branch defines rides that branch); tests widens `_code_only`. This is that half.
#
# The measurement that motivates it is ci-packaging's, recorded here because the predicate
# is this file's: the first draft of `.github/actions/clean-room/lazy_import_probe.py`
# named all three lazily imported functions in its module DOCSTRING, and the lazy-import
# census went green over a probe that called none of them — `_code_only` stripped `#` lines
# and not docstrings. The probe was rewritten to describe them rather than list them, so
# each name occurs exactly once, at its call site; this widening means the census is right
# either way rather than right by that accident.


def test_code_only_blanks_a_name_that_only_appears_in_a_docstring():
    """The operand: the shape that went green."""
    prose_only = (
        '#!/usr/bin/env python\n'
        '"""Runs draw_body, draw_hand and mean_consecutive_frame_difference."""\n'
        'import aapose\n'
        'print("ok")\n'
    )
    code = _python_code_only(prose_only)
    for name in ("draw_body", "draw_hand", "mean_consecutive_frame_difference"):
        assert name not in code, (name, code)
    assert "import aapose" in code, code


def test_code_only_keeps_a_name_that_is_actually_called():
    """The direction the predicate must not bound: a census that blanked everything would
    report every dependency unreached."""
    real = (
        '"""A probe. It calls the lazily imported drawing helpers."""\n'
        'import aapose\n'
        '_ran(aapose.draw_body, canvas, body)\n'
        '_ran(aapose.draw_hand, canvas, hand)\n'
        '_ran(donor_gate.mean_consecutive_frame_difference, paths)\n'
        'print("clean room: " + ", ".join(RAN) + " all ran")\n'
    )
    code = _python_code_only(real)
    for name in ("draw_body", "draw_hand", "mean_consecutive_frame_difference"):
        assert name in code, (name, code)
    #: …and the printed sentence's own words are gone, so a message that merely SAYS the
    #: names ran cannot satisfy a census keyed on the calls.
    assert "all ran" not in code, code
    assert "clean room" not in code, code


def test_the_widened_predicate_leaves_line_numbers_where_they_were():
    """Contents become spaces, quotes are kept: a caller can still report a line number
    against the original text."""
    src = 'a = "one"\nb = 2\nc = """multi\nline\n"""\n'
    code = _python_code_only(src)
    assert len(code.splitlines()) == len(src.splitlines()), (src, code)
    assert code.splitlines()[1] == "b = 2"


def test_the_narrow_predicate_could_not_see_the_docstring():
    """The red proof, reconstructed rather than described: the pre-wave-23 `_code_only`,
    which dropped `#` lines only, reports the docstring's names as reached."""
    prose_only = (
        '"""Runs draw_body and draw_hand."""\n'
        'import aapose\n'
    )
    narrow = "\n".join(l for l in prose_only.splitlines()
                       if not l.lstrip().startswith("#"))
    assert "draw_body" in narrow, "the reconstruction does not carry the defect"
    assert "draw_body" not in _python_code_only(prose_only)


def test_a_hash_inside_a_string_is_not_a_comment():
    """The failure mode a regex over `#` would introduce: `"--tag #1"` is an argument, and
    blanking from the `#` to the end of the line would delete the rest of the command."""
    src = 'run("--tag #1", check=True)\nnext_call()\n'
    code = _python_code_only(src)
    assert "next_call()" in code, code
    assert "run(" in code and "check=True" in code, code


# ============================================================================ wave-23 merge
#
# WAVE-23 MERGE (coordinator, 2026-09-05). The tests domain found `_code_only` defined TWICE in this module, the second
# byte-identical and shadowing the first, which is why its first widening changed nothing (SEAM 6). At the merge the
# coordinator measured the same shape once more in the whole suite: `workflow_files` was defined at two sites in this
# file, the later one (with the docstring) shadowing the earlier. The earlier copy is deleted, and this census holds
# every module under tests/ to one definition per top-level name, so the third instance cannot land quietly.


def test_no_top_level_name_is_defined_twice_in_any_test_module():
    """RED on the wave-23 merge commit: {'test_ci_workflows.py': ['workflow_files']}; green after the deletion."""
    import ast
    import glob

    doubled = {}
    for path in sorted(glob.glob(os.path.join(TESTS_DIR, "*.py"))):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            doubled[os.path.basename(path)] = dup
    assert doubled == {}, (
        f"a top-level name defined twice in one module is a definition nobody reads (the second shadows the "
        f"first, byte-identical or not): {doubled}")


# ======================================================= wave 28, F-bbfe5ae4 — gates first
#
# THE THREE PURE-SHELL GATES IN `verify` RAN LAST. Measured on `3380ae2`, the job's twelve
# steps in file order were: checkout, setup-python, Install, sheet-fonts, Suite, Suite under
# -O, clean-room, npm-clean-room, TAG GATE, visibility gate, PRE-RELEASE GATE,
# upload-artifact. The three gates decide on `$GITHUB_REF`, two `env:` values and the two
# manifests, in milliseconds; the six steps that sat above them are two full pytest runs and
# three clean installs -- the whole cost of the job.
#
# Correctness was never at stake: `pypi` and `npm` both sit on `needs: verify`, so a refusal
# anywhere in this job is a refusal before either registry is reached, which is what the tag
# gate's own comment claims and all it claims. What the old order cost was a mis-dispatched
# run -- the one release.yml's rehearsal block actively invites an operator to attempt --
# burning both hosted runners' clocks through the entire gate job before printing a one-line
# refusal it could have printed first, against a studio rule whose stated purpose is that CI
# minutes are finite.
#
# THE NODE THIS CENSUS KEYS ON: what a step DOES, read out of its own text. Not its name, not
# its position, and not a written-down list of three step names -- a fourth gate added
# tomorrow joins the population without anyone remembering to add it here. WORK is a body
# step whose script installs, builds, packs, publishes or runs the suite, or a step that
# `uses:` one of this repository's OWN composite actions (each of the three installs, builds
# or packs). A GATE is a body step whose `run:` script can exit non-zero and which is not
# work. The job POPULATION is derived the same way -- `jobs_with_a_gate()` walks all three
# workflows -- and `actions/upload-artifact` is neither gate nor work, deliberately: it
# uploads what the clean room built, so it stays last and this census says nothing about it.
#
# THE SIBLING THAT MADE THE PREDICATES HONEST, enumerated before the property was written
# (wave 18, rule 2): the only other step in any workflow carrying `exit 1` in its script is
# release.yml's `Publish`. A first draft defining a gate as "installs nothing, runs no
# pytest" read that irreversible publish step as a pure-shell gate and duly reported the npm
# job as having a gate below its work -- a predicate that calls the publish step a gate is
# not measuring the arm. `npm publish` is on the work list for that reason, and
# `test_the_jobs_that_carry_a_gate_are_the_ones_this_file_thinks_they_are` pins the outcome.
#
# THE FLOOR IS NOT STEP 1, AND THE CENSUS SAYS SO. The tag gate reads `pyproject.toml` and
# `npm/package.json` (checkout) with `python` (setup-python) and the runner's own preinstalled
# `node` -- the argument `.github/actions/npm-clean-room/action.yml` already makes in its
# header for not installing a node of its own. So the gates may not be hoisted above
# `setup-python`, and a census that demanded step 1 would be demanding a broken workflow.

#: A `uses:` ref under this prefix is one of this repository's own composite actions, and
#: every one of them installs, builds or packs. A third-party `uses:` is not work by this
#: census's definition -- `actions/checkout` and `actions/setup-python` are the floor the
#: gates sit on, and `actions/upload-artifact` is downstream of the clean room.
LOCAL_COMPOSITE_PREFIX = "./.github/actions/"

#: The two `actions/*` refs that must precede the gates: the checkout that puts the manifests
#: on disk and the interpreter the version comparison runs in.
GATE_FLOOR_PREFIXES = ("actions/checkout", "actions/setup-")


def _step_keys(step):
    """The step's OWN mapping keys, `- key: value` included — never a nested block's.

    Measured while writing this: reading any `name:` in the block labelled
    `actions/upload-artifact` as `dist`, which is the name of the ARTIFACT inside its `with:`.
    A key one level down belongs to another mapping and is not this step's.
    """
    if not step:
        return []
    own = _indent(step[0]) + 2
    out = []
    for i, line in enumerate(step):
        stripped = line.strip()
        if i == 0 and stripped.startswith("- "):
            stripped = stripped[2:].lstrip()
        elif _indent(line) != own or stripped.startswith("- "):
            continue
        key, sep, value = stripped.partition(":")
        if sep and key and " " not in key:
            out.append((key, value.strip()))
    return out


def _step_uses(step):
    """The `uses:` ref of one step block, or None."""
    for key, value in _step_keys(step):
        if key == "uses":
            return value.split("#")[0].strip()
    return None


def _step_label(step):
    """A step's `name:` if it has one, else its `uses:` ref. For REPORTING, never for keying."""
    for key, value in _step_keys(step):
        if key == "name":
            return value
    return _step_uses(step)


#: The verbs that make a step WORK: it installs, builds, packs, publishes, or runs the suite.
#: Each either spends runner minutes at scale or reaches outside the runner, which is the
#: class of thing a gate exists to run BEFORE.
#:
#: `npm publish` is on this list because of a sibling the first draft of these predicates got
#: WRONG. Enumerated across all three workflows, the only other step in the tree carrying an
#: `exit 1` in its script is release.yml's `Publish` -- and an "installs nothing, runs no
#: pytest" definition read the irreversible publish step as a pure-shell gate, then reported
#: the npm job as having a gate below its work. A predicate that calls the publish step a
#: gate is not measuring the arm.
_WORK_VERBS = re.compile(
    r"(\bpip\s+install\b|\bnpm\s+(install|publish|pack)\b|\bpython\s+-m\s+build\b|\btwine\b)")


def _is_work(step):
    """A step that spends runner time, or reaches a registry, before anything is decided."""
    uses = _step_uses(step)
    if uses and uses.startswith(LOCAL_COMPOSITE_PREFIX):
        return True
    script = _run_script_of(step)
    if script is None:
        return False
    return bool(_WORK_VERBS.search(_code_only(script))) or _runs_pytest(script)


def _is_pure_shell_gate(step):
    """A step that can REFUSE, and that does no work while deciding."""
    script = _run_script_of(step)
    if script is None:
        return False
    if not re.search(r"\bexit\s+[1-9]", _code_only(script)):
        return False
    return not _is_work(step)


def gate_and_work_order(body):
    """`(labels, gate indices, work indices, floor indices)` over one job body's steps."""
    steps = _step_blocks(body)
    labels = [_step_label(s) for s in steps]
    gates = [i for i, s in enumerate(steps) if _is_pure_shell_gate(s)]
    work = [i for i, s in enumerate(steps) if _is_work(s)]
    floor = [i for i, s in enumerate(steps)
             if (_step_uses(s) or "").startswith(GATE_FLOOR_PREFIXES)]
    return labels, gates, work, floor


def _format_step_order(labels, gates, work, floor):
    """Fixed-width Order table: index, GATE/WORK/FLOOR/-, label (F-cb34c4cb)."""
    gate_set, work_set, floor_set = set(gates), set(work), set(floor)
    rows = []
    for i, label in enumerate(labels):
        if i in gate_set:
            kind = "GATE"
        elif i in work_set:
            kind = "WORK"
        elif i in floor_set:
            kind = "FLOOR"
        else:
            kind = "-"
        rows.append(f"{i:2d}  {kind:<5}  {label}")
    return "\n".join(rows)


def jobs_with_a_gate():
    """(workflow, job) for every job carrying a pure-shell gate — read, never written down."""
    out = []
    for name in workflow_files():
        text = _text(name)
        for job in job_names(text):
            body = "\n".join(_job_lines(text, job))
            if any(_is_pure_shell_gate(step) for step in _step_blocks(body)):
                out.append((name, job))
    return out


VERIFY_BODY = "\n".join(_job_lines(RELEASE, "verify"))


def test_the_release_gate_census_reads_the_job_it_claims_to_read():
    """Size and membership before the property: a walk that matched nothing would pass.

    The three gates are NAMED here only so a reader can see which steps the predicates
    resolved to. The predicates are what the property below is keyed on; if a fourth gate is
    added, this assertion is what forces someone to look at it.
    """
    labels, gates, work, floor = gate_and_work_order(VERIFY_BODY)
    # WAVE 35: +1 `audit Python dependencies` (pip-audit) between Install and sheet-fonts.
    assert len(labels) == 13, labels
    assert [labels[i] for i in gates] == [
        "The version in the tag must equal the version in the package",
        "The two workflows must read the same visibility",
        "A pre-release must not reach either registry",
    ], [labels[i] for i in gates]
    assert [labels[i] for i in work] == [
        "Install",
        "audit Python dependencies",
        "./.github/actions/sheet-fonts",
        "Suite",
        "Suite under -O",
        "./.github/actions/clean-room",
        "./.github/actions/npm-clean-room",
    ], [labels[i] for i in work]
    assert [labels[i] for i in floor] == [
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    ], [labels[i] for i in floor]
    # The thirteenth step is neither, and it is labelled by its OWN `uses:` -- not by the
    # `name:` inside its `with:` block, which is the name of the artifact and read `dist`
    # until `_step_keys` was taught the difference.
    assert labels[-1] == "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", (
        labels[-1])
    assert 12 not in gates and 12 not in work and 12 not in floor, (gates, work, floor)


def test_the_jobs_that_carry_a_gate_are_the_ones_this_file_thinks_they_are():
    """The population, derived off the tree, with the sibling that made the predicate honest.

    Enumerated across all three workflows. WAVE-34: `ci.yml:python-tests` carries the
    release.yml rehearsal STATUS pure-shell gate (moved before spend); `release.yml:verify`
    keeps its three version/visibility/pre-release gates. release.yml's `Publish` still
    reaches the registry — it is WORK, and a job whose only `exit` lives in its publish
    step has no gate to order.
    """
    assert jobs_with_a_gate() == [
        ("ci.yml", "python-tests"), ("release.yml", "verify"),
    ], jobs_with_a_gate()
    npm = "\n".join(_job_lines(RELEASE, "npm"))
    labels, gates, work, _floor = gate_and_work_order(npm)
    assert gates == [], [labels[i] for i in gates]
    assert [labels[i] for i in work] == ["Upgrade npm for OIDC", "Publish"], (
        [labels[i] for i in work])


@pytest.mark.parametrize("workflow,job", jobs_with_a_gate())
def test_a_job_with_a_gate_decides_before_it_spends(workflow, job):
    """The property: no job spends runner time while a gate below it may still refuse.

    What this looks like if wrong: a `workflow_dispatch` from a branch -- the mis-dispatch
    release.yml's own rehearsal block invites -- runs the suite twice and three clean installs
    on two hosted runners and then prints `release.yml requires a tag ref`, which it had
    everything it needed to print before the first `pip install`.
    """
    labels, gates, work, floor = gate_and_work_order("\n".join(_job_lines(_text(workflow), job)))
    assert gates and work, (labels, gates, work)
    assert max(gates) < min(work), (
        f"{workflow}:{job} runs {labels[min(work)]!r} at step {min(work)} and still has a "
        f"gate at step {max(gates)} ({labels[max(gates)]!r}); these gates decide on "
        f"$GITHUB_REF, an env value and the two manifests, so a run that is going to be "
        f"refused is refused after the whole job has been paid for. Order:\n"
        f"{_format_step_order(labels, gates, work, floor)}")


@pytest.mark.parametrize("workflow,job", jobs_with_a_gate())
def test_a_gate_sits_on_the_floor_it_actually_needs(workflow, job):
    """The direction the property above does not bound: hoisting them too far.

    The version comparison reads `pyproject.toml` and `npm/package.json` with `python`, so
    `actions/checkout` and `actions/setup-python` must precede it. A census that only pushed
    gates upward would be green on a workflow whose first step ran `python` on a runner that
    has none, in an empty directory.
    """
    labels, gates, work, floor = gate_and_work_order("\n".join(_job_lines(_text(workflow), job)))
    assert floor, labels
    assert max(floor) < min(gates), (
        f"{workflow}:{job} runs a gate at step {min(gates)} ({labels[min(gates)]!r}) before "
        f"{labels[max(floor)]!r} at step {max(floor)}; the version comparison needs the "
        f"checkout for the manifests and setup-python for the interpreter. Order:\n"
        f"{_format_step_order(labels, gates, work, floor)}")


def _verify_body_with_the_gates_last():
    """The REAL steps of `verify`, permuted back to the order measured on `3380ae2`.

    Not a hand-written toy job: the mutation moves the three gate blocks below the seven
    work steps and changes nothing else, so the predicates it is fed are the ones the
    property runs. WAVE 35: others 9 → 10 (+ `audit Python dependencies`).
    """
    lines = _job_lines(RELEASE, "verify")
    first = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("- ")][0]
    head = lines[:first]
    steps = _step_blocks("\n".join(lines))
    gates = [s for s in steps if _is_pure_shell_gate(s)]
    others = [s for s in steps if not _is_pure_shell_gate(s)]
    assert len(gates) == 3 and len(others) == 10, (len(gates), len(others))
    # Back where they were: after `npm-clean-room` and before `upload-artifact`, which is the
    # last of the ten.
    reordered = others[:-1] + gates + others[-1:]
    return "\n".join(head + [ln for step in reordered for ln in step])


def test_the_order_census_goes_red_on_the_order_this_job_had():
    """The red proof, driving the REAL predicates over the REAL steps in the pre-fix order.

    A red proof that re-implements the predicate inline is the shape wave 26 closed
    (`F-ab2c1d14`), so this one calls `gate_and_work_order` and nothing else.
    """
    before = _verify_body_with_the_gates_last()
    labels, gates, work, floor = gate_and_work_order(before)
    # The mutation carries the defect rather than deleting the subject: the same thirteen
    # steps, the same three gates, the same seven work steps, the same floor.
    # WAVE 35: 12 → 13 labels, 6 → 7 work (+ pip-audit); gates land at index 9 after the
    # seven work steps (was 8 when work was six).
    assert len(labels) == 13, labels
    assert len(gates) == 3 and len(work) == 7 and len(floor) == 2, (gates, work, floor)
    assert not max(gates) < min(work), (
        "the reverted order reads as gates-before-work; the property cannot fail")
    assert min(gates) == 9 and min(work) == 2, (
        f"the reconstruction is not the measured pre-fix order (tag gate tenth, Install "
        f"third): gates {gates}, work {work}. Order:\n"
        f"{_format_step_order(labels, gates, work, floor)}")
    # And the floor clause is unaffected by the mutation, so the two properties are separable.
    assert max(floor) < min(gates), (floor, gates)


def test_the_gate_and_work_predicates_do_not_read_each_other():
    """The two directions a mis-classification would hide, driven on the real steps.

    A step that installs is never a gate however many `exit` lines its script has, and a step
    that only refuses is never work. Both are asserted on the job's own text: `Install` and
    `Suite` are the two steps a naive predicate would misread.
    """
    steps = {_step_label(s): s for s in _step_blocks(VERIFY_BODY)}
    assert _is_work(steps["Install"]) and not _is_pure_shell_gate(steps["Install"])
    assert _is_work(steps["Suite"]) and not _is_pure_shell_gate(steps["Suite"])
    tag = steps["The version in the tag must equal the version in the package"]
    assert _is_pure_shell_gate(tag) and not _is_work(tag)
    # The tag gate's script RUNS `python` and `node`; that is not installing either of them.
    assert "python -c" in _code_only(_run_script_of(tag))
    assert _install_tokens(_run_script_of(tag)) == []
    # A gate that grew a `pip install` stops reading as a gate -- the mutation, driven.
    grown = list(tag) + ["          python -m pip install requests"]
    assert not _is_pure_shell_gate(grown) and _is_work(grown)
    # And the sibling that made the predicate honest: the step that reaches the registry has
    # an `exit 1` in it and is not a gate.
    publish = {_step_label(s): s for s in _step_blocks("\n".join(_job_lines(RELEASE, "npm")))}
    assert re.search(r"\bexit\s+[1-9]", _code_only(_run_script_of(publish["Publish"])))
    assert _is_work(publish["Publish"]) and not _is_pure_shell_gate(publish["Publish"])
