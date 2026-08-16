# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

**Detected tags: `[all]`** — `shipcheck init`, run 2026-08-13 at the v0.1.0 treatment.

> **Why only `[all]`, and why that is the honest tag set rather than a convenient one.**
> armature publishes nothing. There is no `pyproject.toml`, no root `package.json`, no
> console script, no MCP server, no installer — it is a repository you clone and run, and
> the names reserved in [docs/publishing.md](docs/publishing.md) are unused. Every
> `[npm]` / `[pypi]` / `[mcp]` / `[cli]` / `[vsix]` / `[desktop]` line below is therefore
> skipped, and **each skip states its reason on the merits rather than on the tag** — so
> that the day a manifest lands, the reason expires visibly instead of the tag quietly
> hiding it. That is the failure mode the sibling repo hit when four tag families switched
> on at once.
>
> The version target is **v0.1.0**, by the Director's ruling of 2026-08-13, which overrides
> the studio's v1.0.0 floor for this repo. Nothing publishes; the version marks a state of
> the record.

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) (2026-08-13) — [SECURITY.md](SECURITY.md); report address, `main`-only support table, 48h / 7d / 30d timeline, and a threat model measured against the tree rather than asserted
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required) (2026-08-13) — README **Trust and threat model**, with the sharp edges disclosed rather than claimed away: file operations are not sandboxed, unexpected failures print a traceback, and absolute rig paths are baked in
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output (2026-08-13) — swept every tracked file (`git ls-files`) for provider-prefixed keys, `ghp_` / `github_pat_`, `xox[baprs]-`, `AKIA…`, private-key blocks, bearer tokens and inline `api_key` / `password` assignments: **zero matches**. No `.env`, `.pem`, `.key` or credential-shaped file is tracked, and those patterns are git-ignored besides. No tool prints a credential because no tool holds one
- [x] `[all]` No telemetry by default — state it explicitly even if obvious (2026-08-13) — none collected, none sent; stated in both README and SECURITY.md. Measured rather than assumed: **no Python networking library is imported anywhere in `tools/` or `tests/`** (`socket`, `requests`, `urllib`, `http.client`, `aiohttp`, `httpx` → zero import matches). The one egress shape is `tools/fetch_run.py` and `tools/fetch_t2v_run.py` shelling to `curl.exe` for URLs the operator pasted in, and it is named in SECURITY.md rather than claimed away

### Default safety posture

- [ ] `[cli|mcp|desktop]` SKIP: dangerous actions require an explicit `--allow-*` flag — **skipped on the merits and not on the tag**. Nothing here is an installed command, but the deeper reason is that the ruled design is the **opposite** of an opt-in flag. Where a tool performs an irreversible step, the gate lives *inside* that tool and `raise`s — no shell-chain separation (a chain can walk past a failing exit code), no `assert` (deleted by `-O`), and **no skip flag**. An `--allow-*` escape hatch would be a regression against that ruling rather than an improvement
- [ ] `[cli|mcp|desktop]` SKIP: file operations constrained to known directories. **They are not, and that is disclosed rather than skipped away.** These are research instruments invoked as `python tools/<name>.py` against paths the operator types; there is no allow-list and no confinement. SECURITY.md states it under "known sharp edges" and tells the reader to point them at scratch trees. Nothing is published, so no consumer inherits an unconstrained surface — this stays a property of the repo. Re-opens the moment anything here is packaged
- [ ] `[mcp]` SKIP: not an MCP server — no server, no transport, no tool surface
- [ ] `[mcp]` SKIP: not an MCP server

## B. Error Handling

- [ ] `[all]` SKIP: errors follow the Structured Error Shape (`code`, `message`, `hint`, `cause?`, `retryable?`). **There is no consumer for that contract.** Nothing here is installed, served, or imported by another program — every error is raised to an operator running a script in their own terminal. What exists instead is the research-instrument contract, and it is deliberate: `tools/armature_core/errors.py` defines a typed hierarchy (`ArmatureError` → `GateFailure`) where every gate failure carries its **gate id** and an `evidence` dict holding the measurement that fired it, and **none of them is an `AssertionError` or produced by an `assert`**, because `-O` deletes those. Retrofitting a code registry across the instruments that produced the accepted record would be a large change to accepted-artifact tooling bought for a checkbox. Disclosed in SECURITY.md; re-opens the day any of this is packaged for a caller
- [ ] `[cli]` SKIP: exit codes 0 / 1 / 2 / 3. No console script is installed and nothing is published, so there is no command whose exit contract a caller depends on. The instruments carry argparse help text, which is not the same thing as a shipped command surface
- [ ] `[cli]` SKIP: no raw stack traces without `--debug`. Same reason — and the honest half is stated rather than hidden: an unexpected exception in a research script **does** print a traceback, and SECURITY.md says so. Deliberate refusals do not: a fired gate leaves as a typed error carrying its measurement
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[desktop]` SKIP: not a desktop application — no UI of any kind
- [ ] `[vscode]` SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions (2026-08-13) — *what it does* and *usage* were already current and were refreshed the same day the repo went public. **What was missing was the platform and runtime half**, which is exactly the line this gate exists for: a **Running it** section now states that there is nothing to install, gives the three invocation shapes, and names Windows 11 on the rig / `ubuntu-latest` in CI, Python 3.13+ (3.14 on the rig venv), Blender 5.2 headless, Node 22 for the site, and where generation actually runs
- [x] `[all]` CHANGELOG.md (Keep a Changelog format) (2026-08-13) — [CHANGELOG.md](CHANGELOG.md), with a `v0.1.0` entry stating what the version marks (instruments, gates, routes, record, laws, public surfaces) **and what it deliberately does not** — including that arms and hands at speed still fail, and that the camera claim on photographic worlds is not made
- [x] `[all]` LICENSE file present and repo states support status (2026-08-13) — MIT, [LICENSE](LICENSE). Support status in both the README trust section and SECURITY.md: `main` is the only supported state, no release channel, no backport policy, no SLA. The licence of any *model* used through the pipeline is a separate question and lives in `docs/license-map.md`
- [ ] `[cli]` SKIP: `--help` accurate for all commands and flags. No console script is installed. The instruments do carry argparse help, and it is the operator's interface — but a checkbox asserting a *shipped command surface* would be asserting something that does not exist
- [ ] `[cli|mcp|desktop]` SKIP: logging levels silent / normal / verbose / debug, secrets redacted at all levels. There is no logging surface to level — the instruments print measurements, separators and verdicts to a terminal an operator is watching, and a gate's refusal is the loudest thing they emit by design. **Nothing is redacted because nothing sensitive is printed**, measured under A3: no tool holds a credential. Re-opens if anything here grows a log file or a daemon mode
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[complex]` SKIP: no daemon, no background service, no state files requiring recovery procedures. Every invocation is one-shot and operator-watched. (The Starlight handbook under `site/` is a *product* handbook, not a C7 operations runbook.)

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) (2026-08-13) — [`verify.ps1`](verify.ps1), three legs in one invocation, every leg run even when an earlier one fails so one call reports the whole picture: **1005 passed / 13 skipped**, then the same suite under `-O` with `PYTHONOPTIMIZE=1`, then `npm ci` + `npm run build` for the site. The `-O` leg is not a duplicate — it is what proves the gates are `raise`s and not `assert`s the interpreter is licensed to delete. Measured 2026-08-13: all three legs pass, exit 0. Mirrors `.github/workflows/ci.yml` leg for leg
- [x] `[all]` Version in manifest matches git tag (2026-08-15) — ⚑ **this SKIP re-opened exactly as its own text said it would, the moment a manifest existed.** It previously read "there is no manifest… re-opens the moment one exists"; `pyproject.toml` and `npm/package.json` now both declare `0.2.0`, and the check is mechanical rather than clerical: `.github/workflows/release.yml`'s `verify` job compares the git tag against both manifests and fails the release before either registry is reached, because a tag that disagrees with its metadata publishes a version nobody asked for
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) (2026-08-13) — `npm audit --audit-level=high` in the `site-build` job of `.github/workflows/ci.yml`, **executed locally before it was written**: 0 vulnerabilities, exit 0. ⚑ **Bounded, and the bound is the honest half:** `site/` is the repo's *only* dependency manifest. There is no Python manifest — CI installs a pinned list inline and nothing resolves a graph — so there is no Python surface for a scanner to read. If a `pyproject.toml` or `requirements.txt` ever lands, this line's second half opens with it
- [ ] `[all]` SKIP: automated dependency update mechanism. By the studio's own GitHub Actions rule — *do not add `dependabot.yml` unless explicitly requested*. This SKIP stands on that rule alone and re-opens on the Director's word
- [x] `[npm]` Publishes to npm (2026-08-15) — `armature-studio`, the Node launcher, at `npm/package.json`. The tarball surface is deliberately four files (`bin/armature.mjs`, `README.md`, `LICENSE`, `package.json`, 3.9 kB packed, measured by `npm pack --dry-run`): the package lives in its own directory precisely so npm ships and renders its own README rather than the repo's, whose relative links and language nav are meaningless on a registry page. `site/package.json` remains `private` build tooling and is still not published
- [x] `[npm]` `[pypi]` `engines.node` / `requires-python` (2026-08-15) — both fields now exist and both are declared: `requires-python = ">=3.10"` in `pyproject.toml`, `"node": ">=18"` in `npm/package.json`. CI continues to pin the versions it actually runs (`python-version: "3.13"`, `node-version: 22`), which is a narrower claim than the floors and is stated as such
- [x] `[npm]` Lockfile committed (2026-08-13) — `site/package-lock.json` is tracked, and both `ci.yml` and `pages.yml` run `npm ci` rather than `npm install`, so the build that runs in CI is the build verified on the rig; a lockfile mismatch is a red job rather than a silent resolve. ⚑ **The `[pypi]` half re-opened 2026-08-15**: a wheel and sdist are now built (`python -m build`) and checked (`twine check`) in `release.yml`'s gate before either registry is reached, and the wheel was installed into a clean venv on the rig before the first publish — `armature check` reported every module resolved from that install, not from the source tree. The launcher package carries no lockfile because it has **zero dependencies**, which is a stronger statement than a pinned graph
- [ ] `[vsix]` SKIP: not a VS Code extension
- [ ] `[desktop]` SKIP: not a desktop application

## E. Identity (soft gate — does not block ship)

- [x] `[all]` Logo in README header (2026-08-13) — the copper wire figure beside the wordmark, pushed to `mcp-tool-shop-org/brand/logos/armature/readme.png` (1600×540, manifest regenerated, `brand verify` clean at 222 assets) and referenced from the README at the brand raw URL, centred at width 820. Verified live: HTTP 200, `image/png`
- [x] `[all]` Translations (polyglot-mcp, 8 languages) — **landed 2026-08-13**, run by the advisor on the local model: seven `README.*.md` files committed together with the source's nav-bar update, before any tag exists. The ja canary was read at review — real prose, no degenerate output (one cosmetic brand-name transliteration wobble noted). The rule that put this line here stands: translations precede the tag because a tag is immutable
- [x] `[org]` Landing page (@mcptoolshop/site-theme) (2026-08-13) — `site/`, deployed to <https://mcp-tool-shop-org.github.io/armature/>, with a five-page Starlight handbook at `/handbook/` (index · the thesis · method · the license gate · roadmap) and a Pagefind search index. Build verified on the rig: 6 pages, `dist/index.html` + `dist/handbook/index.html` + `dist/pagefind/` all present
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
