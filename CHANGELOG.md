# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

A version here marks **a state of the record** — which experiments are closed, which routes
exist, and what the evidence behind them is. ⚑ **Corrected at 0.2.0:** this line used to read
"nothing here is published to a registry… not an artifact anyone installs", which stopped
being true the moment `armature_core` was packaged. The record is still the point; it now also
installs.

## [Unreleased]

**The first health pass: 89 defects, most of them a check that reported safety it never
verified.** A dogfood swarm audited the tree in six domains, a cross-family panel re-rated the
findings, a family-different jury corroborated the wave, and six amend agents fixed every
approved finding with a test that was seen red first. The suite grew from 1359 to 1781 tests.

### Added

- **Every spend builder prints `[canon] ARMED|UNGATED: <subject>` and records the verdict under
  `gates.CANON`.** Gate CANON's escape was silent from the seven tools that author a spend and
  loud only from the diagnostic CLI; a record could not say whether canon was armed or escaped.
  `--canon-prompt` must now be the text the builder ships — gating a string other than the one
  shipped was a working skip.
- **The cascade and batch topology gates check that slot *k* carries frame *k*.** They required
  the caller's ordered per-frame source ids; an upload map keyed by unpadded names put `10.png`
  in slot 2 with "groups in frame order" printed. Upload maps must be keyed `00000`… or
  `00000.png`…, one shape per map, with no gaps.
- **G2 reports `unexpected` files beside `missing` and `empty`, and raises on them.** It counted
  expected filenames only, so a stale frame from a longer earlier run passed a shorter run's
  completeness check and reached the encoder.
- **`encode_control` refuses RGBA and non-8-bit frames** (`--alpha-over=R,G,B` makes a composite an
  explicit, recorded choice) and takes its frame population from the shot spec, not a bare
  directory listing. `--expect` checks the count.
- **Gate DONOR's framing clause counts the clip**, not only the frames the detector fired on, and
  the `thresholds=` parameter that let a caller disarm the andon is gone.
- **Gate ROUTE's verdict says what ran**: `N seed(s) NOT CHECKED for pinning` when the seed clause
  is skipped, and `WAIVED components [...]` when a licence row was waved — and only `EXCLUDED`
  rows can be waved; a `BANNED` (non-commercial) weight can no longer pass with one keyword.
  Gate PAIR's unknown-class detector keys on the `*ToVideo` role, not the `Wan` prefix. Every
  hosted node in a graph is graded, not the first one found. Nested subgraph definitions are
  walked.
- **The G4 tolerance is the gate's** (`gates.G4_TOLERANCE_PX`), no longer a shot-spec field a
  spec could widen to disarm it; **`asset.sha256` is required** in every shot spec, so a spec
  pins the bytes it was written against. Five committed specs lost their `gates` row (every
  value was the default) and the two E03 specs gained the hash their run manifests recorded.
- **The gait refuses every `stance_frac` but 0.5**, the one value the model represents; the
  integrator's ±1 stance endpoints and the literal half-cycle offset were valid only there, and at
  0.4 the hips travelled backward for a frame while the character walked forward.
- **`armature check` resolves function-local imports** and exits 1 with `needs-cv2` / `needs-PIL`
  on an install that cannot run its drawing functions; **the wheel declares its real runtime
  dependencies** (opencv-python-headless, Pillow, matplotlib) instead of numpy alone.
- **`release.yml`'s tag gate is unconditional** — a `workflow_dispatch` from a branch fails
  closed instead of reaching both registries with the tag comparison skipped; the manifests'
  version agreement is now also a test. The PyPI publish action is pinned to a commit SHA.
- **`verify.ps1` records an explicit outcome per leg**: an absent command is a FAIL, not the
  previous leg's zero; two legs added (clean-venv install-and-run, `npm audit`); an ANDON when
  `node`/`npm` are missing for the selected legs.
- **The sheet composers find a licence-verified font or refuse by name** (Arial → Liberation Sans
  → Noto Sans); `C:\Windows\Fonts` is no longer hard-coded, and CI installs Liberation
  explicitly so 23 sheet tests that always skipped there now run.
- Instruments stopped reporting what they had not measured: `measure_floor` refuses unequal or
  duplicate runs instead of truncating with `zip`; `compare_runs` refuses empty channel
  directories instead of printing `max_abs_diff 0`; `measure_cascade_clip` decodes at the
  stream's dimensions and refuses a mismatch; the E08 sheet renders every panel line from the
  record. `fetch_run` inspects curl's return code, indexes fallback paths, and halts on an
  unmapped source node.
- Tests: the E02 payload byte pins run everywhere on a committed fixture; a `-O` receipt for the
  gate every submitted graph passes; the pose-arc round-trip check gained the pytest wrapper its
  siblings had; twenty guards that depended on the caller's working directory are anchored.

### Fixed

- `build_camera_i2v_payload` requires `--start-frame` and hashes it (the sha256 flag was an
  optional ledger entry); the three animate/i2v builders resolve the seed default before Gate S.
- `gate_saved_graph.link_round_trip` walks both socket lists, so a socket the save/convert round
  trip dropped is a refusal, not a silent pass.
- `clipcompare.frame_fidelity` counts differing pixels, not channels ×3; `compare_runs` likewise.
- `glb.gate_atlas_untouched` reports `K unhashable` images instead of silently comparing only the
  hashable ones; `normalize_depth` reserves byte 0 for background — geometry starts at 1/255.
- `assembly.gate_no_paid_nodes` raises the gate, not a `TypeError`, on a node with no `class_type`.
- `lift_solve.round_trip_report` lost the `raise_on_fail` keyword that let a caller disarm it.

### Changed

- **Shot-spec contract:** no `gates` block; `asset.sha256` required. **Gait:** `GaitParams` accepts
  `stance_frac == 0.5` only. **Records:** the `ceiling` field in `specs/*seeds.json` is an object
  (`ceiling.note` carries the prose); assembly records name whose frames they hold.
- Verdict strings changed in `gate_atlas_untouched`, the CASCADE ceiling and topology gates, and
  Gate ROUTE; `compare_runs` renames `mean_abs_diff` → `mean_abs_diff_per_sample`;
  `measure_cascade_clip` names `first_frame` / `mid_frame` with a `frame_index`.
- `tests/blender/check_pose_arc_roundtrip.py` signals by a printed `POSE_ARC <json>` record, not
  an exit code, and accepts `--fps N`.
- `ci.yml` also triggers on `README.pypi.md` and `LICENSE` (they ride the sdist).

## [0.3.0] — 2026-08-18

**A spend that cannot name its subject creates nothing, and the index verifies itself.**

### Added

- **Gate CANON** — `armature_core.canon` plus the `canon_gate` tool. A machine-readable
  statement of what a subject **is**, keyed on surface, where a null occupant is a **hole rather
  than an absence** — an element list cannot show what it omitted. The router checks **both
  directions**: that the submission covers the canon, and that everything in the submission *is*
  canon. The reverse direction is the one that discriminates.
- **The gate fires before the output directory exists**, inside each of the **seven** payload
  builders that author a spend. Nothing in this repository submits — the payload builders write
  files and a session submits them — so the irreversible step this tree owns is *writing a
  payload*, and that is where the check lives. It `raise`s; it is not an `assert`, and the suite
  runs again under `-O` to prove it still fires.
- **A census-backed escape.** `--no-canon` on a subject that *has* canon is refused as a
  checkbox; with no subject at all it is refused as a skip flag; a canon file whose every
  occupant is unratified is refused outright, because a check that cannot fail is not a check.
- **Spatial binding in the schema** — a surface may name a bone, validated against the real
  sitelist census. Material and region bindings are carried and **labelled unbound** rather than
  implied.
- **Eighteen tests over the record index**, ten of them stdlib-only so they run in every CI job
  rather than skipping where the sibling library is absent. There were none before.

### Fixed

- **`armature_index.py build` never wrote a certificate**, despite the library's own docstring
  stating no such path existed. It now routes through `build_and_certify` and returns non-zero
  when its own verify refuses.
- **`health()` had no verb reaching it.** It computes the early, actionable form of a stale
  index — the signal that would have caught six dangling pointers days before `verify` failed.
- The index itself, rebuilt: it was six days old against a corpus that had grown from 45 files
  to 139. Three of its six dangling rows described **another repository's files** under
  armature-relative paths.

### Changed

- The front door loses a self-contradiction carried since v0.2.0 — it claimed *no package on any
  registry* three sections below `pip install armature-studio`.

**The registry names, corrected before the first publish.** `v0.2.0` was tagged and pushed
under the working names `armature-previz` / `@mcptoolshop/armature`; the Director's trusted
publisher was registered for **`armature-studio`** with workflow **`release.yml`**, and a
publisher that does not match the manifest and workflow filename byte-for-byte does not
publish at all. Renamed rather than force-moving a pushed tag: `v0.2.0` stands as a tag that
was cut and never released, and **nothing was ever published under the old names.**

- PyPI project: **`armature-studio`**, matching the registered pending publisher.
- npm package: **`@mcptoolshop/armature-studio`**, under the studio's existing scope rather
  than a new one — the org already exists, so no org has to be created for this package to
  have a home.
- `.github/workflows/publish.yml` → **`.github/workflows/release.yml`**, matching the
  registered publisher's workflow filename exactly.

## [0.2.0] — 2026-08-15 (tagged, never released)

**The record becomes an installable toolkit.** Until now a version here marked a state of the
record and nothing more — `SHIP_GATE.md` said so plainly, because there was no manifest and
nothing was published. There is now.

### Added

- **`armature-studio` on PyPI** — `armature_core` packaged: the gates (`gates`, `route_gates`,
  `rig_gates`, `donor_gate`), the framing and turnaround solvers (`framing`, `turnaround`,
  `startframe`), the control-channel maths (`channels`, `openpose`, `aapose`, `landmarks`,
  `lift_solve`), the rig and mesh modules, and the contracts. numpy is the only runtime
  dependency; Python 3.10+.
- **`@mcptoolshop/armature-studio` on npm** — a **launcher, not a port**. It forwards the `armature`
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
- **`.github/workflows/release.yml`** — publishing on `release: published` only, by **OIDC
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

