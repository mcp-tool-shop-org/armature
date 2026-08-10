# Publishing

## Names claimed

| Surface | Name | Status |
|---|---|---|
| GitHub | `mcp-tool-shop-org/armature` | live, public, `main` |
| PyPI | **`armature-studio`** | Trusted Publisher configured 2026-08-10 |
| npm | `@mcptoolshop/armature` | available via the scope; not yet claimed |

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

The project does not yet exist on PyPI. Under the current bootstrap path, the first successful
OIDC publish **creates** it; no `v0.0.0` placeholder is required.

## Standing rules that apply here

- **Two workflow files maximum** per repo (the studio's GitHub Actions rule), so this repo gets
  `ci.yml` and `release.yml` — the publish path is already spoken for by the TP registration.
- `release.yml` triggers on `release: published` only — never on push.
- `ci.yml` is paths-gated and carries the required concurrency block.
- Runner is `ubuntu-latest`. Blender-dependent tests cannot run there; keep them marked and run
  them on this rig, and do not weaken a test to make CI green — facet's rule is that narrowing
  a test to turn a red gate green is forbidden whichever kind of gate fired.
- Version floor at ship time is **v1.0.0** minimum, per the shipcheck product standard.

## Before the first publish

Shipcheck hard gates A–D pass, then the full treatment. Neither has run — this repo is at day
zero and the roadmap puts publishing at P02, after the thesis has been tested.
