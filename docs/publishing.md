# Publishing

## Names claimed

| Surface | Name | Status |
|---|---|---|
| GitHub | `mcp-tool-shop-org/armature` | live, public, `main` (re-measured 2026-09-06: `gh repo view` reports PUBLIC) |
| PyPI | **`armature-studio`** | Trusted Publisher configured 2026-08-10; **published** — 0.2.1, 0.3.0, 0.4.0 and **0.5.0** on the index |
| npm | **`@mcptoolshop/armature-studio`** | **published** — latest **0.5.0** on the registry. *Corrected 2026-09-05: this row read `@mcptoolshop/armature`, "not yet claimed"; the package that shipped carries the `-studio` suffix like the PyPI project (`npm/package.json`).* |

Bare `armature` was unavailable on both PyPI (a 0.0.1 "Config package" stub) and npm (an
abandoned `1.0.0-alpha4`), which is why the PyPI project carries the `-studio` suffix.
`armature-mcp`, `armature-cli` and `armature-render` were also free at the time of checking.

## ⚠ PyPI Trusted Publishing — the config the CI must match

Registered on PyPI 2026-08-10 as a **pending publisher**:

| Field | Value |
|---|---|
| PyPI Project Name | `armature-studio` |
| Owner | `mcp-tool-shop-org` |
| Repository | `armature` |
| **Workflow name** | **`release.yml`** |
| Environment name | *(any)* |

**The workflow filename is load-bearing.** OIDC publishing authenticates the *workflow*, so the
publish job must live in `.github/workflows/release.yml` exactly. A workflow named `publish.yml`
or `ci-release.yml` will be rejected by PyPI no matter how correct the rest of the build is —
and the failure surfaces at publish time, after everything else has passed.

~~The project does not yet exist on PyPI. Under the current bootstrap path, the first successful
OIDC publish **creates** it; no `v0.0.0` placeholder is required.~~ **Corrected 2026-09-05:** the first OIDC
publish created it on 2026-08-15 (`release.yml` records the date beside its publish step). **Re-measured
2026-09-06:** the index holds 0.2.1, 0.3.0 and 0.4.0. The bootstrap sentence is kept struck because it
was the plan until it ran.

**The release rehearsal, in order** (the ordering `release.yml` carries as a comment beside its steps, written
here so a reader does not have to open the workflow): (1) `verify.ps1` green on the rig, (2) the tag pushed and the
GitHub release published, which is the only trigger `release.yml` answers to, (3) the workflow's `verify` job — the
suite on both CI Pythons, the two clean rooms, the classifier gate; its three pure-shell gates (tag/ref, visibility,
pre-release) run immediately after `setup-python`, so a dispatch from a branch is refused in seconds rather than after
two suite runs and three clean installs (reordered 2026-09-06) — before the publish job runs. A rehearsal that
skips (1) tests the workflow on a tree the rig never verified.

## Standing rules that apply here

- **Two workflow files maximum** per repo (the studio's GitHub Actions rule) was the plan; the repo carries
  **three** (`ci.yml`, `release.yml`, and `pages.yml` for the site — measured 2026-09-05). The publish path is
  `release.yml`, spoken for by the TP registration; `pages.yml` fires only on `site/**` and itself.
- `release.yml` triggers on `release: published` only — never on push.
- `ci.yml` is paths-gated and carries the required concurrency block.
- Runner is `ubuntu-latest`. Blender-dependent tests cannot run there; keep them marked and run
  them on this rig, and do not weaken a test to make CI green — facet's rule is that narrowing
  a test to turn a red gate green is forbidden whichever kind of gate fired.
- ~~Version floor at ship time is **v1.0.0** minimum, per the shipcheck product standard.~~
  **Corrected 2026-08-13: the version target for this repo is `v0.x`,
  overriding the studio's v1.0.0 floor.** The struck line is left visible rather than deleted
  because it was the standing rule until it was not. A version here still marks a state of the
  record; since 2026-08-15 it also installs — see [CHANGELOG.md](../CHANGELOG.md). npm
  provenance is attested only from a public repository (`release.yml` branches on
  `github.event.repository.private`).

## Before the first publish

Shipcheck hard gates A–D pass, then the full treatment.

**Both ran on 2026-08-13**, at the v0.1.0 treatment: hard gates A–D are every line checked with
its evidence or skipped with the reason on its merits ([SHIP_GATE.md](../SHIP_GATE.md)), and the
treatment's phases landed the security policy, the changelog, the verify script, dependency
scanning on the one manifest that exists, the brand logo, the badges, and the repo-knowledge
entry. *The prior text read: "Neither has run — this repo is at day zero and the roadmap puts
publishing at P02, after the thesis has been tested."* The day-zero half has expired; the
roadmap half has since expired too — **v0.1.0, v0.1.1, v0.2.1, v0.3.0 and v0.4.0 are published
releases (2026-08-13 to 2026-09-06), `armature-studio` is on PyPI and `@mcptoolshop/armature-studio`
on npm** (re-measured 2026-09-06 against both registry APIs). *The prior text read: "nothing has
been published, and the names above remain unused."*
