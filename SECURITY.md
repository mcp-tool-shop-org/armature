# Security Policy

## What armature is, for the purposes of this policy

armature is a set of local Python instruments plus headless Blender scenes that stage a
canonical character mesh, render per-frame control sequences and reference plates from it,
and measure what comes back from a video model. It is a repository you clone and run — not
a published package, not a service, not a daemon. Every tool is invoked as
`python tools/<name>.py` (or `blender -b -P tools/<name>.py -- …`) against paths the
operator types.

Generation itself runs on Comfy Cloud and is submitted by the operator from outside these
scripts. **No credential for that service, or any other, lives in this repo.**

That shapes the whole policy below: the attack surface is the surface of *running these
scripts on your own machine against your own files*, and this document's job is to say
exactly what they do.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` | Yes — the record is the product; `main` is the only supported state |

`main` carries the current state of every instrument and the evidence behind it. There is
no release channel, no backport policy and no SLA. See [CHANGELOG.md](CHANGELOG.md) for
what `v0.2.0` marks and what it deliberately does not.

**Published packages.** `armature-previz` (PyPI) and `@mcptoolshop/armature` (npm) are built
and published by GitHub Actions from a tagged release, authenticated by **OIDC Trusted
Publishing**: no long-lived registry token exists in this repository, in its secrets, or on any
developer machine. npm carries build provenance. A release is gated on the suite passing —
including under `-O`, where a check written as `assert` would vanish — and on the git tag,
`pyproject.toml` and `npm/package.json` agreeing on the version.

## Reporting a vulnerability

Email: **64996768+mcp-tool-shop@users.noreply.github.com**

Include:

- Description of the vulnerability
- Steps to reproduce
- The commit sha affected
- Potential impact

### Response timeline

| Action | Target |
|--------|--------|
| Acknowledge report | 48 hours |
| Assess severity | 7 days |
| Release fix | 30 days |

## Threat model — measured, not asserted

Every claim below was checked against the tree rather than assumed, on 2026-08-13. The
commands are given where a reader would want to re-run them.

### Data touched

- **Meshes, renders, videos, images and JSON on local disk**, at paths the operator passes
  on the command line. The tools read and write freely inside whatever directory you name.
  Generated artifacts land under `outputs/`, which is git-ignored — the record this repo
  keeps is specs, reports, provenance JSON and sha256 manifests, never the binaries.
- **`docs/index/armature.db`** — a SQLite+FTS5 index *derived* from this repo's own
  markdown, with its sidecar certificate. It holds no input that did not come from files
  already in this repo, and `tools/armature_index.py` regenerates it from scratch.
- **Read-only sibling trees.** Canonical assets are consumed from `E:\AI\facet\…` and
  `E:\AI\training\…` and are never written to.

### Data NOT touched

- **No credentials of any kind.** The tools do not read, store or transmit tokens, keys or
  passwords, and none are present in the tree. Swept every tracked file for
  provider-prefixed keys, `ghp_` / `github_pat_`, Slack tokens, AWS access-key ids, private
  key blocks, bearer tokens and inline `api_key` / `password` assignments: **zero matches**.
  `git ls-files` carries no `.env`, `.pem`, `.key` or credential-shaped file, and those
  patterns are git-ignored besides.
- **No telemetry, analytics, crash reporting or usage counting.** None is collected and
  none is sent. There is no opt-out because there is nothing to opt out of.

### Network egress

**No Python networking library is imported anywhere in `tools/` or `tests/`** — grepping
the tree for `socket`, `requests`, `urllib`, `http.client`, `aiohttp` and `httpx` imports
returns zero matches, and no tool opens a socket directly.

Egress exists in exactly one shape, and it is worth naming precisely rather than claiming
it away:

| tool | what it does |
|---|---|
| `tools/fetch_run.py` | shells out to `pwsh` → `curl.exe` to download the files listed in an operator-supplied `get_output` dump |
| `tools/fetch_t2v_run.py` | the same, via `powershell` → `curl.exe` |

Both fetch **URLs the operator pasted in**, from a dump the operator obtained by submitting
a generation themselves. Neither tool discovers a host, holds a credential, or contacts
anything the operator did not name. Nothing else in the repo makes a network call.

### Other processes invoked

`blender` (18 call sites — headless only, `-b -P`), `ffmpeg` (encode/decode of control
video, with a round-trip gate on the result), and `pwsh` / `powershell` for the two fetch
tools above. All are expected on `PATH` or given as absolute paths by the operator.

### Permissions required

Ordinary user permissions. No elevation, no service installation, no registry or
system-settings writes, no scheduled tasks. The tools need read/write on the directories
you point them at, a GPU for the render stage, and Blender for the staging and render
stages.

### Known sharp edges, disclosed rather than claimed away

- **File operations are not sandboxed.** There is no allow-list of directories and no
  confinement — a tool writes wherever its arguments say. Treat these as research
  instruments you are running deliberately, not as a hardened CLI. Point them at scratch
  trees.
- **Absolute local paths are baked into many tools and docs** (`E:\AI\…` — 82 occurrences
  across 36 tracked files). They are not secrets, but they do disclose one machine's
  directory layout, and they mean most tools will not run unmodified on another rig.
- **Unexpected failures surface as Python tracebacks.** Deliberate refusals do not: every
  gate raises a typed `ArmatureError` subclass carrying the measurement that fired it
  (`tools/armature_core/errors.py`), and **none of them is an `assert`** — an `assert` is
  deleted by `-O` or `PYTHONOPTIMIZE=1`, so the suite is run a second time under `-O` in CI
  to prove the gates still raise. But an *unexpected* exception in a research script prints
  a raw traceback, and there is no `--debug` flag gating that, because nothing here is an
  installed command with a user-facing error contract.
- **No `--allow-*` escape hatches, and that is the ruling, not an omission.** Where a tool
  performs an irreversible step, the gate lives *inside* that tool and raises — no shell
  chain separation, no skip flag. An opt-in override would be a regression against that
  ruling rather than an improvement.
- **Third-party generation tiers carry their own terms.** Any route that sends assets
  through a hosted tier documents what rides with it — the providers' data-use and training
  posture, AI-content disclosure duties and watermark policy — in that route's spec and
  route docs, grounded in the fetched documents in `docs/license-map.md`. Fully-local routes
  state that nothing leaves the rig.

## Scope

In scope: the instruments in `tools/`, the test suite in `tests/`, the site under `site/`,
and the CI workflows.

Out of scope: the third-party models, services and runtimes the pipeline invokes (Blender,
ComfyUI / Comfy Cloud, ffmpeg, and every generation model). Their commercial-use and
licence positions are tracked in `docs/license-map.md`; their security is theirs.
