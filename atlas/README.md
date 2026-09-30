# armature: how it works

Mapped at 2026-09-30 from commit 7a70d6f by Atlas 1.24.0.

## What this is

8 parts, mostly Python (320 files), CSS (2), JavaScript (2), TypeScript (2), Astro (1) and PowerShell (1). Work enters through 5 doors; the busiest is ci, which reaches 4 parts. It publishes to PyPI and @mcptoolshop/armature-studio to npm. It deploys a site to GitHub Pages. People run armature.

## What changed since 2026-09-25 (f57d428)

- .github now imports tools.
- ci now also runs tools/armature_core/cli.py.
- ci now also checks tools/.
- release now also runs tools/armature_core/cli.py.
- And 2 more changes to doors.
- MANIFEST.in is now also read by .github/workflows/ci.yml and .github/workflows/release.yml.
- pyproject.toml is now also read by .github/workflows/ci.yml.
- tests/ is now also read by tests/test_refusal_clauses.py.
- And 4 more new writers and readers of places.
- tests/test_amend_w12_core_gates.py now starts at `test_the_three_gate_p_clauses_refuse_an_infinite_diagonal_too`; it started at `test_the_condition_flipped_back_to_allowed_drops_out_of_the_receipt`.
- In tests/test_amend_w12_core_solvers.py, `test_gate_conv_refuses_when_the_modules_tables_drift_from_the_recorded_reference` gained a step, `setattr`, before `setattr`.
- In tests/test_amend_w12_core_solvers.py, `test_gate_conv_refuses_when_the_modules_tables_drift_from_the_recorded_reference` gained a step, `setattr`, before `setattr`.
- And 9 more changes to the order of work.
- 1 file changed content, across 1 part.

## What comes in

1. **ci.** On a pull request touching 21 paths; on a push touching 21 paths; or by hand. Runs npm/bin/armature.mjs, tests/, tools/armature_core/cli.py and 3 more; checks tools/.
2. **release.** When a release is published; or by hand. Runs tools/armature_core/cli.py and tests/; checks tools/.
3. **pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
4. **armature** (a command people run, from npm/package.json). Runs npm/bin/armature.mjs.
5. **armature** (a command people run, from pyproject.toml). Runs tools/armature_core/cli.py.

## What happens through ci

1. The workflow runs npm/bin/armature.mjs in npm, site/astro.config.mjs and site/src/ in the site, tests/ in tests, and tools/armature_core/cli.py in tools; it checks tools/ in tools.
   1. Inside tests/test_amend_w12_core_gates.py, `test_the_three_gate_p_clauses_refuse_an_infinite_diagonal_too` does, in order: `__init__.py` (tools, 3 steps).
   2. Inside tests/test_amend_w6_andons.py, `test_load_pinned_camera_refuses_to_run_with_no_expectation` does, in order: `__init__.py` (tools, 3 steps).
   3. Inside tests/test_assembly.py, `test_the_slot_index_gate_catches_a_permuted_slot_that_topology_calls_clean` does, in order: `build` (tools), `gate_batch_topology`, `gate_slot_frame_index`, `gate_batch_topology` and `gate_slot_frame_index`.
   4. Inside tests/test_cascade.py, `test_a_within_group_slot_swap_is_caught_by_the_index_gate` does, in order: `build` (tools), `cascade_plan`, `gate_slot_frame_index`, `gate_cascade_topology` and `gate_slot_frame_index`.
   5. **`build`** (tools) runs, in order: `gate_create_video_fps` and `cascade_plan`.
   6. Inside tests/test_donor_gate.py, `test_the_motion_threshold_bites_at_the_stated_number` does, in order: `__init__.py` (tools, 8 steps).
   7. Inside tests/test_instruments_amend_w18_optics.py, `test_every_float_flag_in_both_parsers_is_bounded_by_name` does, in order: `_fn` and `read_source`.
   8. Inside tools/armature_core/cli.py, `main` does, in order: `add_spend_flags`, `known_hosted_tiers`, `parts.py` (3 steps), `load_graph` and `verify`.

## Who reads the results

ci writes nothing this map can see.

## The other doors

**release** runs tools/armature_core/cli.py and tests/, checks tools/, and publishes to PyPI and @mcptoolshop/armature-studio to npm (on a run by hand, only with rehearse false).

**pages** runs site/astro.config.mjs and site/src/, and deploys the site on main.

**armature** (a command people run, from npm/package.json) runs npm/bin/armature.mjs.

**armature** (a command people run, from pyproject.toml) runs tools/armature_core/cli.py.

## What breaks what

- **tools** is imported by 1 part (.github), and by 1 more only from tests; it sits on the path of 3 doors.
- **npm** is imported by no other part and sits on the path of 2 doors.
- **the site** is imported by no other part and sits on the path of 2 doors.
- **tests** is imported by no other part and sits on the path of 2 doors.

## What tends to change together

- **tools/author_walk.py** and **tools/lift_solve.py** changed together in 16 of 20 commits, inside the tools part.
- **tools/make_binding_sheet.py** and **tools/make_parts_sheet.py** changed together in 16 of 20 commits, inside the tools part.
- **tools/build_camera_i2v_payload.py** and **tools/build_i2v_payload.py** changed together in 22 of 28 commits, inside the tools part.
- **tools/preview_walk.py** and **tools/render_performer.py** changed together in 16 of 22 commits, inside the tools part.
- **tools/rig_bake.py** and **tools/rig_repair.py** changed together in 13 of 19 commits, inside the tools part.

Window: 180 days; a pair counts from 10 shared commits, since 102 source files reach 10 revisions; the floor falls to 3 when fewer than 20 do.

## What no test touches

Every code part is touched by at least one test.

npm is tested only by its package's own test script, which a workflow runs.

## Written but never read

No place this map can see is written, so none goes unread.

## Helpers that look duplicated

No two parts export a helper that looks alike.

## Generated, never hand-edited

Nothing in this repository writes to a tracked place this map can see.

## Hand-authored

People write .github/, docs/, the repository root, site/ and specs/; 116 writes with paths built at run time may land here.

## Where to start

.github/workflows/ci.yml → tools/armature_core/cli.py → tools/armature_core/route_gates.py → tools/armature_core/parts.py

Read those in order to follow one pull request end to end.

## What this map cannot see

- 43 imports could not be resolved: `tests/blender/test_check_pack.py` imports `conftest`, which is no module on its import path and no declared dependency; `tests/blender_stub.py` imports a path built at run time; `tests/conftest.py` imports a path built at run time; and 40 more.
- 116 writes and 73 reads use paths built at run time and are not named here.
- 80 writes and 156 reads go to a path their caller passes, not to this repository.
- 3 writes go to the directory the command is run in, not to this repository.
- 3 commands are built at run time and not followed.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
