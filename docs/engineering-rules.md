# Engineering Rules

The engineering rules enforced across `tools/`, `tests/`, and `specs/`. Each rule carries a stable anchor, a concise statement of the invariant, and the gate, function, or test that checks it.

---

<a id="scope-and-posture"></a>
## Scope and Posture

**Armature stages canonical character GLBs in headless Blender for arbitrary video footage rather than acting as a single-purpose turnaround generator.** Experiments prove or falsify routes under controlled runs, no route becomes canonical by momentum alone, and falsified or superseded tools remain runnable under `tools/superseded/` with their failure reason recorded so retired assumptions are not re-invented.

Where enforced: cited, not mechanically checked (`tests/test_instruments_amend_w28.py:53` verifies the `tools/superseded/` census population).

<a id="licence-gate"></a>
## Licence Gate

**No non-commercially-licensed model, weight, LoRA, preprocessor, font, or asset may enter the pipeline anywhere, including in experiments.** Components marked `UNVERIFIED` refuse as `NO`, `CONDITIONAL` components refuse without an explicit maintainer ruling carrying provenance, and `docs/license-map.md` rows older than 90 days become advisory until re-fetched.

Where enforced: `tools/armature_core/route_gates.py` (`licence_age_days` `:2180`, `licence_fetch_reading` `:2206`, `verify` `:4018`) and `tools/armature_core/measure_weights.py` (`MeasureWeightGate` `:38`, `gate_measurement_weight` `:575`), pinned by `tests/test_route_gates.py`.

<a id="served-templates-and-gate-route"></a>
## Served Templates Are References

**A served Comfy workflow template is a reference for inspection only, never an execution route.** Every graph submitted by this repository is constructed in-repo, checked for link topology in code (because a `dry_run` PASS validates schema without proving batch or link wiring), and cleared by Gate ROUTE prior to submission.

Where enforced: `tools/armature_core/route_gates.py` (`verify` `:4018`), `tools/build_submit_payload.py` (`gate_admission_matches` `:246`, `rearm_gates` `:314`), and `tools/gate_saved_graph.py` (`route_facts` `:806`).

<a id="licence-row-not-wiring-claim"></a>
## A Licence Row Is Not a Wiring Claim

**Recording a commercial licence grant in `docs/license-map.md` does not establish that a graph actually loads or wires those weights safely.** Conditioning nodes must pair with the exact weight family they require (Gate PAIR), and watermark or disclosure records must match actual node wiring rather than an unverified literal.

Where enforced: `tools/armature_core/route_gates.py` (`pairing` `:1370`, `verify` `:4018`).

<a id="per-route-disclosure"></a>
## Per-Route Disclosure

**Any route that transmits assets through a third-party hosted tier must carry that route's data-use, training-exposure, AI-disclosure, and watermark obligations in specs, payload records, and CLI submission output.** Local-only routes explicitly record that no assets leave the local machine.

Where enforced: `tools/build_assembly_payload.py` (`comfy_cloud_oss_disclosure` `:433`) and `tools/build_r2v_payload.py`, checked by `tests/test_amend_w14_builders.py` and `tests/test_amend_w28_builders.py`.

<a id="credit-ceilings-and-seeds"></a>
## Credit Ceilings and Registered Seeds

**Spent cloud credits have no undo compensator, so every credit-spending spec must declare machine-readable registered `seeds` and explicit `ceiling` bounds before any submission.** Payload builders validate selected seeds against the committed registration, and the submission gate enforces the ledger count against the ceiling before posting.

Where enforced: `tools/build_assembly_payload.py` (`read_seed_registration` `:192`, `read_seed_registration_budget` `:330`), `tools/armature_core/gates.py` (`gate_s_seed_registration` `:963`), `tools/build_submit_payload.py` (`gate_ceiling_budget` `:142`), and `tests/test_seeds_specs.py`.

<a id="gates-raise-inside-the-step"></a>
## Gates Raise Inside the Irreversible Step

**Every gate guarding an irreversible step executes inside the tool performing that step and raises a typed `ArmatureError` subclass carrying structured evidence — never a bare `assert`, shell-chain exit code, or `--allow-*` skip flag.** Each gate bounds the direction the invariant does not already constrain without relying on a sibling statement or downstream gate to mask a vacuous pass.

Where enforced: `tools/armature_core/errors.py` (`ArmatureError` `:10`), `tools/armature_core/donor_gate.py` (`gate_donor` `:424`), `tests/test_gates.py`, `tests/test_amend_w3_andons.py`, and CI's `-O` test leg in `.github/workflows/ci.yml`.

<a id="diagnostics-versus-gates"></a>
## Diagnostics Report; Visual Judgement Rules

**Diagnostics measure and report quantities without gating; qualitative identity and motion acceptance are decided by eye on clips in motion and full-size per-frame PNGs beside reference and provenance sheets.** Dedicated gates handle refusals, and numeric metrics on a subject require valid detections rather than empty-detection fallback scores.

Where enforced: cited in diagnostics design and tests (`tools/armature_core/shotdiag.py`, `tools/armature_core/framing.py`, `tools/encode_control.py`, `tools/extract_clip_frames.py`).

<a id="fixture-falsification-question"></a>
## Tests Pose the Falsification Question

**Every test fixture is designed by asking what the check would observe if the code under test were wrong in the exact way the check exists to catch.** Pass conditions must not depend on the artifact or output being judged or pass vacuously on empty inputs.

Where enforced: test suite assertions across `tests/test_gates.py`, `tests/test_gate_r.py`, `tests/test_walk.py`, and peer modules.

<a id="named-compensators"></a>
## Named Compensators

**Every script or module that writes files locally declares `NAMED_COMPENSATORS`, documenting what artifacts it creates under `outputs/` and how an operator reverts or cleans up those writes.**

Where enforced: `tests/test_instruments_amend_w25.py` (`COMPENSATOR_HEADING` `:562`, `test_every_instrument_declares_a_named_compensator_with_an_owner` `:577`).

<a id="pixel-comparison-not-file-hash"></a>
## Pixel Comparison for Renders

**A container or compressed file-hash mismatch is not evidence that a rendered image or frame sequence changed.** Compare decoded pixels when checking image or frame differences, reserving byte hashes for byte-contract artifacts.

Where enforced: `tools/armature_core/clipstats.py` (`distinct_frames` `:374`), `tools/armature_core/turnaround.py` (`gate_set_distinct` `:664`), `tools/check_relift.py`, and `tests/test_clipstats.py`.

<a id="reproducible-generation-records"></a>
## Reproducible Generation Records

**Every generation record logs the model identifier and version, full workflow payload, pinned seed, reference provenance (including fit parameters such as letterbox padding), and control-input hashes, stating explicitly where provider nondeterminism is unmeasured.** Saved workflow graphs are verified to round-trip without silent value or link drift.

Where enforced: `tools/armature_core/canon.py`, `tools/gate_saved_graph.py` (`main` `:1144`), and payload builders (`tools/build_animate_payload.py`, `tools/build_i2v_payload.py`, `tools/build_camera_i2v_payload.py`).

<a id="no-global-constant-for-local-feature"></a>
## No Global Constant for a Local Feature

**Tolerances, spatial bounds, schedules, and external subprocess timeouts derive from the local geometry scale, frame count, or payload size rather than arbitrary global constants.**

Where enforced: `tools/armature_core/gates.py:404`, `tools/armature_core/clipstats.py` (`scale_of` `:87`), and module tests (`tests/test_walk.py`, `tests/test_amend_w28_builders.py`, `tests/test_instruments_measure_amend_w28.py`).

<a id="grade-arm-on-what-it-moves"></a>
## Grade an Arm Only on What It Can Move

**An experiment arm is graded solely on measurements that respond to the lever that arm actually varies, rather than quantities held invariant by design.**

Where enforced: cited, not mechanically checked (`tests/test_clipstats.py:5`).

<a id="no-placeholder-evidence"></a>
## No Placeholders Shaped Like Evidence

**Verification sheets, provenance bands, and comparison reports never substitute dummy identifiers, zeroed fallback counts, or unmeasured guesses for missing evidence.** An unrun gate prints `NOT YET RUN`, and missing measurements refuse explicitly.

Where enforced: `tests/test_compare_runs.py` (`test_no_returned_report_can_carry_a_mismatch_count` `:242`) and `tests/test_e13_sheet.py`.

<a id="alpha-law"></a>
## Authored RGBA Alpha Law

**Authored character renders preserve a true RGBA alpha channel rather than baking in a flat grey studio void.** When a downstream route needs an RGB plate, compositing over a plate is an explicit, recorded per-route choice (`--alpha-over`), and consumers decode with `IMREAD_UNCHANGED` rather than dropping alpha.

Where enforced: `tools/armature_core/turnaround.py` (`gate_view_alpha` `:484`), `tools/fit_reference.py`, `tools/render_start_frame.py`, `tools/render_turnaround.py`, and `tests/test_alpha_law.py`.

<a id="generator-legal-frames"></a>
## Generator-Legal Frames and Dimensions

**Every video or image generation request must match the target model family's legality rules (such as width and height divisibility by 16 and `4k + 1` frame counts), recorded per model in specs and checked in-code before submission.**

Where enforced: `tools/armature_core/gates.py` (`GENERATOR_PROFILES` `:70`, `g1_generator_legality` `:210`) and `tools/armature_core/route_gates.py` (`frame_legality` `:3526`, `hosted_frame_legality` `:3784`).

<a id="neutral-public-prose"></a>
## Neutral Public Prose

**Public documentation, code comments, and emitted artifact manifests state technical facts and decisions in neutral engineering prose rather than quoting raw conversational transcripts or carrying internal role labels.**

Where enforced: `tests/test_retopo_and_bake.py` (`test_no_tool_writes_a_quoted_ruling_sentence_into_an_artifact` `:288`) and `tests/test_public_hygiene.py`.

<a id="platform-and-runtime-environment"></a>
## Platform and Runtime Environment

**Blender-based tools run headless only (`-b -P`), PowerShell verification and parallel download paths require PowerShell 7.4 (`#requires -Version 7.4`), and Windows/POSIX platform paths and netrc credential spellings (`_netrc` alongside `.netrc`) are handled explicitly without assuming a POSIX-only host.**

Where enforced: `verify.ps1:1`, `tools/fetch_run.py:556`, `.gitignore:134-135`, and `tests/test_packaging.py`.
