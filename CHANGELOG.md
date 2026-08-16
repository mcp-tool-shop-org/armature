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

## [0.2.0] — 2026-08-15

**The record becomes an installable toolkit.** Until now a version here marked a state of the
record and nothing more — `SHIP_GATE.md` said so plainly, because there was no manifest and
nothing was published. There is now.

### Added

- **`armature-previz` on PyPI** — `armature_core` packaged: the gates (`gates`, `route_gates`,
  `rig_gates`, `donor_gate`), the framing and turnaround solvers (`framing`, `turnaround`,
  `startframe`), the control-channel maths (`channels`, `openpose`, `aapose`, `landmarks`,
  `lift_solve`), the rig and mesh modules, and the contracts. numpy is the only runtime
  dependency; Python 3.10+.
- **`@mcptoolshop/armature` on npm** — a **launcher, not a port**. It forwards the `armature`
  command verbatim to the Python that holds the truth, because re-implementing a threshold in
  a second language is how a threshold drifts. It will not install Python and will not
  `pip install` anything on your behalf: it distinguishes *no interpreter* from *an interpreter
  without the package*, prints the one command that fixes each, and exits non-zero.
- **The `armature` command** — `check` (imports every module and exits non-zero if any is
  missing), `modules` (what each is for, `--json` for machines), `where` (the docs, and the
  Blender invocation that actually works). Ten tests ride it, including the red case where a
  broken install must not exit 0, and both directions of the module-table check — a name with
  no file behind it, and a shipped module the table forgets. The second direction failed on
  first run and caught nine real omissions.
- **`.github/workflows/publish.yml`** — publishing on `release: published` only, by **OIDC
  Trusted Publishing**, so no long-lived registry token exists anywhere. Both registries sit
  behind one gate: the suite, the suite again under `-O`, `twine check`, and a version-agreement
  check across the git tag, `pyproject.toml` and `npm/package.json`.

### Changed

- The rendering scripts are documented as **deliberately not console entry points**. They run
  inside Blender's own interpreter; a console script on the user's Python could not import
  `bpy` and would fail on its first line, so shipping one would be a promise the package cannot
  keep. `blender_scene` is packaged and reports `needs-blender` rather than counting as a
  defect.
- README, handbook and landing surfaces carry install instructions; `SHIP_GATE.md`'s
  no-manifest skip is retired by the manifest existing.

## [0.1.1] — 2026-08-13

A patch-scale state of the record, cut the same day as v0.1.0: the fourteenth experiment
closed and the free route's LoRA scene-lever priced live.

### Added

- **E14 closed — the LoRA scene-lever bake-off**
  ([spec](docs/experiments/E14-lora-scene-lever.md) →
  [report](docs/experiments/E14-report.md) →
  [closing ruling](docs/experiments/E14-closing-ruling.md), with both seats' predictions
  committed before the first submission). Two arms against the byte-pinned E12 wave-3
  graph, two generations at a ceiling reached exactly, zero partner credits. The transfer
  premise — the experiment's central ASSUMED question — resolved live on both arms: a
  T2V-trained style LoRA binds visibly on the Fun-Camera derivative weights. The verdicts
  of record: the style transform held on both arms; the character held on
  `technically_color` and failed on the SmartphoneSnapshot pair. The winner carries two
  standing caveats, recorded where they bind: the served single file's expert tier is
  unresolvable in-graph (Gate PAIR reports NOT VISIBLE rather than a pass no gate
  verified), and the `technically_color` grant sets `allowNoCredit: false` — published
  footage from that arm carries a credits line for renderartist.
- **`tools/build_lora_arm_payload.py`** — the in-repo arm builder: the LoRA insertion
  point measured from the served template's walked subgraph rather than inherited from
  convention, Gate LEDGER's break-aware boxes declared before the diff runs, and
  **Gate PAIR_TIER**, which raises on a crossed tier-labeled pair and reports NOT VISIBLE
  for an unlabeled single file. 32 tests, including the red test for the crossed pair the
  spec named in advance.
- **Consult #11** ([docs/comfy-consult-11.md](docs/comfy-consult-11.md)) — the
  GLB→2.5D-sprite side question ruled reference-not-route: the local catalog's honest
  limit banked (no headless mesh-camera render; the wired-camera path is splat-only;
  Load3D's camera is serializable node state with round-trip fidelity NOT VISIBLE), the
  capability located on the existing headless shelf, and orthographic projection named as
  the one genuine gap — a candidate small spec, not dispatched.
- `specs/E14-seeds.json` and the byte-pinned E12 wave-3 fixture
  (`tests/fixtures/E12-w3-camera-i2v.api.json`), so the arms rebuild from the repo alone.

### Fixed

- **`make_thesis_sheet.py` stopped lying twice** — both defects the repo's named class, a
  literal that lies when reused: the reference plate was silently dropped for any first
  row not labelled `CONTROL`, and default captions fabricated a turnaround azimuth for
  video frames. Four regression tests ride the fix; E03's socket prose removed from the
  shared composer.

### Changed

- The grading law gains its complement, written in the E14 closing ruling: no seat's
  frame-read approximates identity either — an identity prediction is graded only by the
  eye that holds the canon, and grading waits for the verdict.
- The seat-boundary law gains its mechanical form after a disclosed, ruled deviation: an
  executor who finds binding documents self-contradictory halts and reports, the way a
  gate fires; seat identity comes from the dispatch mechanics, never a session's
  self-impression.
- Front door, handbook and landing surfaces carry fourteen closed, three routes measured,
  and the winner's caveats. Suite at the close-merge: **1183 passed, 13 skipped** on the
  rig.

## [0.1.0] — 2026-08-13

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

**The public surfaces.** README with its seven translations — landed before this tag was
cut, per the release-ordering rule that a tag is immutable and stale translations under it
are forever; the landing page and the five-page handbook under `site/`, deployed to GitHub
Pages; SECURITY.md with a threat model measured against the tree; this changelog; and
SHIP_GATE.md carrying the hard-gate results as they actually stand — `shipcheck audit`
exits 0 at this version.

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

