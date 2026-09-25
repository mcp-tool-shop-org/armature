# armature: how it works

Mapped at 2026-09-25 from commit f57d428.

## What this is

8 parts, mostly Python (320 files), JavaScript (2) and TypeScript (2). Work enters through 4 doors; the busiest is ci, which reaches 4 parts. It publishes to PyPI and @mcptoolshop/armature-studio (npm) to npm. People run armature.

## What changed since the last map

This is the first map.

## What comes in

1. **ci.** On a pull request touching 21 paths; on a push touching 21 paths; or by hand. Runs npm/bin/armature.mjs, tests/, site/astro.config.mjs and 2 more.
2. **release.** When a release is published; or by hand. Runs tests/.
3. **pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
4. **armature** (a command people run). Runs tools/armature_core/cli.py.

## What happens through ci

1. The workflow runs npm/bin/armature.mjs in npm, site/astro.config.mjs and site/src/ in the site, and tests/ in tests.
   1. Inside tests/test_ci_workflows.py, step containing does, in order: splitlines and lstrip.
   2. Inside tests/test_instruments_measure_amend_w14.py, test a near opaque master completes with n a and the token last does, in order: setattr and readouterr.
2. That reaches tools (2 files).

## Who reads the results

ci writes nothing this map can see.

## The other doors

**release** runs tests/, reaches tools, and publishes to PyPI and @mcptoolshop/armature-studio (npm) to npm (on a run by hand, only with rehearse false).

**pages** runs site/astro.config.mjs and site/src/, and deploys the site on main.

**armature** (a command people run) runs tools/armature_core/cli.py.

## What breaks what

- **tools** is imported only from tests, by 1 part (tests), and sits on the path of 3 doors.
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

- **npm** is imported by no test.

## Written but never read

No place this map can see is written, so none goes unread.

## Helpers that look duplicated

No two parts export a helper that looks alike.

## Generated, never hand-edited

Nothing in this repository writes to a tracked place this map can see.

## Hand-authored

People write .github/, docs/, the repository root, site/ and specs/; 141 writes with paths built at run time may land here.

## Where to start

tools/armature_core/cli.py

Read those in order to follow one run of armature end to end. This path follows armature (a command people run) from its entry, since ci runs only tests and scripts that import no code here.

## What this map cannot see

- 1629 import sites could not be resolved.
- 141 writes and 181 reads use paths built at run time and are not named here.
- 43 writes and 7 reads go to a path their caller passes, not to this repository.
- 10 writes go to the directory the command is run in, not to this repository.
- 3 commands are built at run time and not followed.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
