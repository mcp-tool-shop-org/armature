# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

**Detected tags: `[all]`** — `shipcheck init`, run 2026-08-13 at the v0.1.0 treatment.

> **Why only `[all]`, and why that is the honest tag set rather than a convenient one.**
> ~~armature publishes nothing. There is no `pyproject.toml`, no root `package.json`, no
> console script, no MCP server, no installer — it is a repository you clone and run, and
> the names reserved in [docs/publishing.md](docs/publishing.md) are unused.~~ **Corrected
> 2026-09-06:** that premise expired on 2026-08-15. `pyproject.toml` and `npm/package.json`
> exist, `armature` is a console script, and **v0.5.0 is on PyPI and npm** (this release),
> 2026-09-06). The `[npm]` / `[pypi]` / `[cli]` lines below that re-opened on their own
> merits stay checked; each remaining skip still states its reason on the merits rather
> than on the tag — so that the day a new surface lands, the reason expires visibly
> instead of the tag quietly hiding it. That is the failure mode the sibling repo hit when
> four tag families switched on at once.
>
> The version target is **v0.x** (first marked state v0.1.0, current **v0.5.0**), which
> overrides the studio's v1.0.0 floor for this repo. A version here still marks a state of
> the record; since 2026-08-15 it also installs.

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) (2026-08-13) — [SECURITY.md](SECURITY.md); report address, `main`-only support table, 48h / 7d / 30d timeline, and a threat model measured against the tree rather than asserted
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required) (2026-08-13) — README **Trust and threat model**, with the sharp edges disclosed rather than claimed away: file operations are not sandboxed, unexpected failures print a traceback, and absolute rig paths are baked in
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output (2026-08-13) — swept every tracked file (`git ls-files`) for provider-prefixed keys, `ghp_` / `github_pat_`, `xox[baprs]-`, `AKIA…`, private-key blocks, bearer tokens and inline `api_key` / `password` assignments: **zero matches**. No `.env`, `.pem`, `.key` or credential-shaped file is tracked, and those patterns are git-ignored besides. No tool prints a credential because no tool holds one
- [x] `[all]` No telemetry by default — state it explicitly even if obvious (2026-08-13) — none collected, none sent; stated in both README and SECURITY.md. Measured rather than assumed: **no Python networking library is imported anywhere in `tools/` or `tests/`** (`socket`, `requests`, `urllib`, `http.client`, `aiohttp`, `httpx` → zero import matches). The one egress shape is `tools/fetch_run.py` and `tools/fetch_t2v_run.py` shelling to `curl.exe` for URLs the operator pasted in, and it is named in SECURITY.md rather than claimed away

### Default safety posture

- [ ] `[cli|mcp|desktop]` SKIP: dangerous actions require an explicit `--allow-*` flag — **skipped on the merits and not on the tag**. The ruled design is the **opposite** of an opt-in flag. Where a tool performs an irreversible step, the gate lives *inside* that tool and `raise`s — no shell-chain separation (a chain can walk past a failing exit code), no `assert` (deleted by `-O`), and **no skip flag**. An `--allow-*` escape hatch would be a regression against that ruling rather than an improvement. *The 2026-08-13 clause "nothing here is an installed command" expired on 2026-08-15; the skip stands on the design, not on that premise.*
- [ ] `[cli|mcp|desktop]` SKIP: file operations constrained to known directories. **They are not, and that is disclosed rather than skipped away.** These are research instruments invoked as `python tools/<name>.py` against paths the operator types; there is no allow-list and no confinement. SECURITY.md states it under "known sharp edges" and tells the reader to point them at scratch trees. The package that installs is `armature_core` (gates, solvers, builders); the unconstrained file surface stays a property of the clone-and-run instruments and is disclosed, not skipped away.
- [ ] `[mcp]` SKIP: not an MCP server — no server, no transport, no tool surface
- [ ] `[mcp]` SKIP: not an MCP server

## B. Error Handling

- [ ] `[all]` SKIP: errors follow the Structured Error Shape (`code`, `message`, `hint`, `cause?`, `retryable?`). **There is no consumer for that contract as a shipped API.** What exists instead is the research-instrument contract, and it is deliberate: `tools/armature_core/errors.py` defines a typed hierarchy (`ArmatureError` → `GateFailure`) where every gate failure carries its **gate id** and an `evidence` dict holding the measurement that fired it, and **none of them is an `AssertionError` or produced by an `assert`**, because `-O` deletes those. The halt line an operator reads is the six-key `<TOOL>_HALT` record (`tool` / `outcome` / `gate` / `error` / `message` / `evidence`); `evidence.clause` is the word a caller branches on. Retrofitting a code registry across the instruments that produced the accepted record would be a large change to accepted-artifact tooling bought for a checkbox. Disclosed in SECURITY.md and README "Reading a halt". *The 2026-08-13 clause "nothing here is installed" expired on 2026-08-15; the skip stands on the contract shape, not on that premise.*
- [x] `[cli]` exit codes 0 / 1 / 2 / 3. *Corrected 2026-09-05: the SKIP premise ("no console script is installed and nothing is published") expired on 2026-08-15 — `armature = "armature_core.cli:main"` is installed by the package and the package is on PyPI and npm.* Every CPython instrument exits 0 on success, 2 on a deliberate refusal and 1 on a crash through one handler (`armature_core.parts.run_tool_main`, 50 adopters of a population of 54 on `bfe5ed7`); the contract is stated in README "Reading a halt" and driven by `tests/test_instrument_exits.py`
- [ ] `[cli]` SKIP: no raw stack traces without `--debug`. Same reason — and the honest half is stated rather than hidden: an unexpected exception in a research script **does** print a traceback, and SECURITY.md says so. Deliberate refusals do not: a fired gate leaves as a typed error carrying its measurement
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[desktop]` SKIP: not a desktop application — no UI of any kind
- [ ] `[vscode]` SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions (2026-08-13) — *what it does* and *usage* were already current and were refreshed the same day the repo went public. **What was missing was the platform and runtime half**, which is exactly the line this gate exists for: a **Running it** section names Windows 11 on the rig / `ubuntu-latest` in CI, Python `>=3.11,<3.15` (CI 3.11 and 3.13, the rig venv 3.14), Blender 5.2 headless, Node 18 and 22 for the launcher, Node 22 for the site, and where generation actually runs. ⚑ **Corrected 2026-09-06:** the 2026-08-13 text said "there is nothing to install" and "Python 3.13+"; both expired — `pip install armature-studio` is the install, and the declared interval is `>=3.11,<3.15` (`pyproject.toml:60`)
- [x] `[all]` CHANGELOG.md (Keep a Changelog format) (2026-08-13) — [CHANGELOG.md](CHANGELOG.md), with a `v0.1.0` entry stating what the version marks (instruments, gates, routes, record, laws, public surfaces) **and what it deliberately does not** — including that arms and hands at speed still fail, and that the camera claim on photographic worlds is not made
- [x] `[all]` LICENSE file present and repo states support status (2026-08-13) — MIT, [LICENSE](LICENSE). Support status in both the README trust section and SECURITY.md: `main` is the only supported state, no release channel, no backport policy, no SLA. The licence of any *model* used through the pipeline is a separate question and lives in `docs/license-map.md`
- [x] `[cli]` `--help` accurate for all commands and flags (2026-09-06) — ⚑ **this SKIP re-opened:** the 2026-08-13 premise ("no console script is installed") expired on 2026-08-15, and the Stage C pass filled the surface — every CPython instrument's `--help` opens with one sentence saying what the tool does and carries text on every flag (69 parsers gained a description; more than 400 flags gained help text). The four tools that spend or gate a spend carry an epilogue naming the route and what a refusal costs. Five instruments parse `--key=value` by hand (`stage_render`, `make_sheet`, `analyze_p3`, `rig_sheet_compose`, `sheet_compose`) and refuse an unknown token by name with their own flag set in the refusal. Stated in README "Reading a halt" / "Running it" and `docs/tools.md`
- [ ] `[cli|mcp|desktop]` SKIP: logging levels silent / normal / verbose / debug, secrets redacted at all levels. There is no logging surface to level — the instruments print measurements, separators and verdicts to a terminal an operator is watching, and a gate's refusal is the loudest thing they emit by design. **Nothing is redacted because nothing sensitive is printed**, measured under A3: no tool holds a credential. Re-opens if anything here grows a log file or a daemon mode
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[complex]` SKIP: no daemon, no background service, no state files requiring recovery procedures. Every invocation is one-shot and operator-watched. (The Starlight handbook under `site/` is a *product* handbook, not a C7 operations runbook.)

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) (2026-08-13) — [`verify.ps1`](verify.ps1), three legs in one invocation, every leg run even when an earlier one fails so one call reports the whole picture: **1005 passed / 13 skipped**, then the same suite under `-O` with `PYTHONOPTIMIZE=1`, then `npm ci` + `npm run build` for the site. The `-O` leg is not a duplicate — it is what proves the gates are `raise`s and not `assert`s the interpreter is licensed to delete. Measured 2026-08-13: all three legs pass, exit 0. Mirrors `.github/workflows/ci.yml` leg for leg. ⚑ **Re-measured 2026-09-04 at the first health pass:** four legs now (tests · tests under `-O` · wheel + sdist + `twine check` + two clean-room installs + launcher self-test · site), each recording an **explicit outcome** — an absent command is a FAIL, not the previous leg's zero, which is exactly what the old `$LASTEXITCODE` capture reported — plus an exit-2 ANDON when `node`/`npm` are missing for the selected legs. **1781 passed / 13 skipped** on the rig; the three `-NoSite` legs PASS on `a9b6aa9`. ⚑ **Re-measured 2026-09-06 at v0.4.0:** **7538 passed / 64 skipped** on `4d43ac2`; `verify.ps1 -NoSite` all run legs PASS. ⚑ **Re-measured 2026-09-07 after feature-execute:** **8051 passed / 59 skipped** on the pin-fixed tree; rehearsal **34098347849** ran the same suite plus `-O` and both clean rooms with publish jobs skipped
- [x] `[all]` Version in manifest matches git tag (2026-08-15) — ⚑ **this SKIP re-opened exactly as its own text said it would, the moment a manifest existed.** It previously read "there is no manifest… re-opens the moment one exists"; `pyproject.toml` and `npm/package.json` now both declare **0.5.0** (this release; they declared 0.2.0 on the day this line first opened), and the check is mechanical rather than clerical: `.github/workflows/release.yml`'s `verify` job compares the git tag against both manifests and fails the release before either registry is reached, because a tag that disagrees with its metadata publishes a version nobody asked for
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) (2026-08-13) — `npm audit --audit-level=high` in the `site-build` job of `.github/workflows/ci.yml`, **executed locally before it was written**: 0 vulnerabilities, exit 0. ⚑ **Corrected 2026-09-06:** `pyproject.toml` exists (since 2026-08-15); `site/` is no longer the only manifest. The Python graph is declared there; CI still pins its install list inline, and the three deliberate differences between the `dev` extra and the two CI install lines are named in the `pyproject.toml` preamble
- [x] `[all]` automated dependency update mechanism (2026-09-07) — `.github/dependabot.yml` landed with the confirming feature-execute: `github-actions` weekly, `pip` monthly. The prior SKIP stood on "do not add unless requested"; the Director approved the finding that requested it. `pip-audit` is a separate gate on python-tests and the release verify job (setuptools `>=83.0.0,<84`)
- [x] `[npm]` Publishes to npm (2026-08-15) — `armature-studio`, the Node launcher, at `npm/package.json`. The tarball surface is deliberately four files (`bin/armature.mjs`, `README.md`, `LICENSE`, `package.json`, 3.9 kB packed, measured by `npm pack --dry-run`): the package lives in its own directory precisely so npm ships and renders its own README rather than the repo's, whose relative links and language nav are meaningless on a registry page. `site/package.json` remains `private` build tooling and is still not published
- [x] `[npm]` `[pypi]` `engines.node` / `requires-python` (2026-08-15) — both fields now exist and both are declared: `requires-python = ">=3.11,<3.15"` in `pyproject.toml` (⚑ **corrected 2026-09-06:** the 2026-08-15 reading was `>=3.10`; the floor moved for `tomllib` and the ceiling is the half pip enforces), `"node": ">=18"` in `npm/package.json`. CI runs Python 3.11 and 3.13 and Node 18 and 22, which is a narrower claim than the declared interval and is stated as such
- [x] `[npm]` Lockfile committed (2026-08-13) — `site/package-lock.json` is tracked, and both `ci.yml` and `pages.yml` run `npm ci` rather than `npm install`, so the build that runs in CI is the build verified on the rig; a lockfile mismatch is a red job rather than a silent resolve. ⚑ **The `[pypi]` half re-opened 2026-08-15**: a wheel and sdist are now built (`python -m build`) and checked (`twine check`) in `release.yml`'s gate before either registry is reached, and the wheel was installed into a clean venv on the rig before the first publish — `armature check` reported every module resolved from that install, not from the source tree. The launcher package carries no lockfile because it has **zero dependencies**, which is a stronger statement than a pinned graph
- [ ] `[vsix]` SKIP: not a VS Code extension
- [ ] `[desktop]` SKIP: not a desktop application

## E. Identity (soft gate — does not block ship)

- [x] `[all]` Logo in README header (2026-08-13) — the copper wire figure beside the wordmark, pushed to `mcp-tool-shop-org/brand/logos/armature/readme.png` (1600×540, manifest regenerated, `brand verify` clean at 222 assets) and referenced from the README at the brand raw URL, centred at width 820. Verified live: HTTP 200, `image/png`
- [x] `[all]` Translations (polyglot-mcp, 8 languages) — **landed 2026-08-13**, run by the advisor on the local model: seven `README.*.md` files committed together with the source's nav-bar update, before any tag exists. The ja canary was read at review — real prose, no degenerate output (one cosmetic brand-name transliteration wobble noted). The rule that put this line here stands: translations precede the tag because a tag is immutable
- [x] `[org]` Landing page (@mcptoolshop/site-theme) (2026-08-13) — `site/`, deployed to <https://mcp-tool-shop-org.github.io/armature/>, with a six-page Starlight handbook at `/handbook/` (index · the thesis · method · reading a halt · the license gate · roadmap) and a Pagefind search index. ⚑ **Corrected 2026-09-06:** `reading-a-halt` landed with v0.4.0; the 2026-08-13 count was five. Build verified on the rig: `dist/index.html` + `dist/handbook/index.html` + `dist/handbook/reading-a-halt/index.html` + `dist/pagefind/` all present
- [x] `[all]` GitHub repo metadata: description, homepage, topics (2026-08-13) — **already in place before this treatment and verified by read-back rather than re-set**: the description carries the full scope (image-to-video with a GLB instead of an image; film, cutscenes, character performance, any footage), `homepage` → the live Pages URL, and **thirteen topics** (`ai-video`, `blender`, `character-consistency`, `comfyui`, `controlnet`, `cutscenes`, `diffusion-models`, `film`, `game-development`, `image-to-video`, `previz`, `python`, `video-generation`). The treatment made no mutation here, so there is nothing to compensate

---

## Gate Rules

**Hard gate (A–D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."

**Checking off:**
```
- [x] `[all]` SECURITY.md exists (2026-02-27)
```

**Skipping:**
```
- [ ] `[pypi]` SKIP: not a Python project
```
