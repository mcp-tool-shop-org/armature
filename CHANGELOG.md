# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

Nothing here is published to a registry. A version in this repo marks **a state of the
record** — which experiments are closed, which routes exist, and what the evidence behind
them is — not an artifact anyone installs.

## [Unreleased]

### Added

### Fixed

### Changed

## [0.1.0] — unreleased

The first marked state of the record. Founded 2026-08-10; twelve experiments closed and a
thirteenth dispatched by 2026-08-13.

### What this version marks

**The instruments.** Headless-Blender staging and render (`tools/stage_render.py` and the
scene layer under `tools/armature_core/`), the control-channel encoders, the payload
builders for each generation tier, the rig line (`rig_character.py`, `rig_repair.py`,
`rig_bake.py`) and the measurement and sheet-composition tools that every experiment is
read off. **1005 tests passing on the rig, 13 skipped** — rig-local tests skip visibly
rather than passing silently, and the suite runs a second time under `-O` so that gates
which must raise are proven not to be `assert`s the interpreter may delete.

**The gates.** G1 generator legality · G2 completeness · G4 bbox sanity · G5 convention
conformance · G6 subject motion · R control-video round-trip · B batching · S seed
registration · N rig names · P rest pose · D determinism · ROUTE subgraph blueprints ·
PAIR conditioning-class to weight-family · the break-aware LEDGER (named fields must
move, unnamed must hold) · BACKDROP (start-frame discrimination at measured thresholds).
Each was earned by a specific silent failure,
each raises rather than asserts, and each carries the story of what it exists to catch in
its own docstring.

**The routes.** Two, plus one under probe. The **driven route** — rig-rendered pose sticks
into the Animate tier — is proven at shot level and parked for AI-animation buildout. The
**free route** — a GLB-authored start frame into the I2V and camera tiers — holds identity
unanchored and, at the catalog's 6.0 / uni_pc baseline adopted in E12, holds a handed world
to the last frame on two seeds. The **composed route** — authored references into a hosted
identity-lock tier — is E13's probe, dispatched 2026-08-13 with its per-route disclosure
note in the spec.

**The record.** `docs/experiments/` carries E01–E13 as spec → report → ruling, amendments
appended in place with dates and reasons. `docs/license-map.md` carries a retrieved licence
document for every adopted dependency, with UNVERIFIED treated as NO. `docs/audit-first-arc.md`
audits the founding arc against itself. `docs/index/armature.db` is the derived record
index. Withdrawn and superseded approaches stay in the tree — `tools/superseded/`, runnable,
with the reason — because a falsified approach that leaves the tree becomes doctrine again.

**The laws that were paid for.** Per-route disclosure for any route through a third-party
tier (2026-08-12). A Trajectory row on every credit-spending spec. Authored image inputs
carry alpha rather than a baked void. A licence row is not a wiring claim — the graph must
be shown to load the weights the row names. Binding documents are read from `main` at
dispatch time. Each is recorded in CLAUDE.md next to the measurement that earned it.

**The public surfaces.** README, the landing page and the five-page handbook under `site/`,
deployed to GitHub Pages; SECURITY.md with a threat model measured against the tree; this
changelog; and SHIP_GATE.md carrying the hard-gate results as they actually stand.

### What this version deliberately does not mark

- **Not a release of software anyone installs.** Nothing publishes to npm or PyPI. The
  names are reserved (`docs/publishing.md`) and unused.
- **Not a claim that the pipeline is finished.** Arms and hands at speed still fail at f80
  on both seeds at both settings (E12), and the lever chosen is presentation-first staging
  with mesh surgery as the fallback.
- **Not a camera claim on photographic worlds.** The horizon instrument found no seam to
  measure across all four E12 clips; a seam-free camera instrument is owed before any
  camera number is read on a real room.
- **Not a stable API.** Tool flags, spec schemas and node maps have moved between
  experiments and will move again; the record documents each move rather than promising
  it will not happen.

### Not yet done at this version

- Translations of the README (eight languages, run locally) land before the release tag is
  cut, per the studio's release-ordering rule — a tag is immutable and stale translations
  under it are forever.
