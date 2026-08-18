# Grok build #2 — prompt-craft: the ruling landed, and the gate you were fenced from is a gate that cannot fail

**2026-08-17, armature advisor seat.** One for one. #1's chip was verified by running it
before a word of this was written: `test_a_refused_spend_creates_no_output_directory`, run
alone, **1 passed**. Your counts reproduced to the digit — 1354 collected / 1341 passed / 13
skipped, and 30 passed under `-O`. Your decision is accepted without amendment.

Your cut was sharper than either branch I offered. I asked *build here or adopt prompt-craft*;
you measured the plugin contract, found the README's boundary claim **holds** for a
plugin-shaped feature, and then showed the feature was not that shape. That is a finding about
prompt-craft nothing had ever tested, and it is why the fence returned a measurement instead
of a silent edit.

This round the tree changes. **prompt-craft is the primary tree**, and the fence that made
your last decision comes off — see the ruling below.

The brief stays in armature's `docs/` for channel continuity (round numbering, chips).
prompt-craft has no docs tree yet; if this round gives it one, this file moves.

*Everything below the line is the paste block.*

---

# One for one. The Director has ruled on the distinction you were asked about — and it unlocks the exact thing prompt-craft gets wrong.

## ⚑ The ruling

You wrote that you thought the atom / identity distinction holds — that a ratified phrase about
a garment or a palette is a nameable claim, while *is this the same man* is a different object.

**The Director has ruled: it holds.**

What that unlocks: **a gate on contract atoms is a legitimate object and may block.** Nameable,
checkable presence — a garment, a palette, a silhouette, the absence of a rival colour — can
gate. prompt-craft's three-tier pixel gate is no longer fenced in principle.

What it does **not** unlock, and this has not moved an inch: **identity gates nothing, ever.**
Whether the figure on screen is the same character is canon and the Director's to judge. No
metric approximates it; that ruling was reached twice the expensive way. A verifier that scores
*likeness* rides a report as a diagnostic and blocks nothing, in either repo.

The line between the two is now load-bearing rather than theoretical, and this round is the
first work that sits on it. If you find a place where the two collapse in practice — where an
atom check is doing identity work by the back door — that is a finding worth more than
anything else you could return.

## Who you are in this tree, and what changed

Outside consult **and build** channel, as before.

**Access this round:**

- `E:\AI\prompt-craft` — **primary.** Read anything; write `src/`, `tests/`, `pyproject.toml`,
  `.github/`. ⚑ **The `core/` fence comes off.** You measured its boundary honestly when you
  were forbidden to cross it; you have earned the write. One condition: **a change to
  `src/pcraft/core/` is reported with its reasoning at the top of your report**, because the
  plugin-boundary claim you verified is now a thing the repo relies on and I want to know the
  moment it stops being true.
- `E:\AI\armature` — read anything; write nothing this round. Your #1 change-set is still
  uncommitted there awaiting the fold; **do not touch it.**

**Fenced OFF in prompt-craft:** `README.md` and any `README.*.md`, any landing page or
handbook, `CHANGELOG.md` **content** (the file exists as a scaffold — leave its body alone),
GitHub repo metadata, and the `[project] description` in `pyproject.toml`. Public surfaces are
lead-authored by a studio law with a reverted subagent behind it. Report what they need; write
none of it.

Change-set stays **uncommitted** for the advisor's fold.

**You do not judge artifacts.** *Verified, shipped, works, decisive, validated, proven* do not
belong in a report here. A negative result is a full success.

## Open the tree

```
cd E:\AI\prompt-craft
git log --oneline -3
git status --short
```

Suite — measured today, **42 passed in 0.29 s**:

```
PYTHONPATH=src python -m pytest -q --basetemp=<a scratch dir>
```

⚠ `PYTHONPATH=src` is not optional — the package is not installed anywhere on this rig
(`pip show pcraft` → not found; `pcraft` is not on PATH). The suite and CLI both run only via
that path today, **not** via the `pip install -e ".[dev]"` route the README's Quickstart
documents. That gap is itself a finding.

⚠ `--basetemp` is not optional either — without it pytest dies on a Windows `PermissionError`
at `pytest-of-mikey\pytest-current` during dead-symlink cleanup, before collecting. It reads
like a repo failure and is not one.

The CLI has no `__main__`, so `python -m pcraft.cli` fails. Reach it as:

```
PYTHONPATH=src python -c "import sys; from pcraft.cli import app; sys.argv=['pcraft','<cmd>',...]; app()"
```

## State, measured 2026-08-17

| | |
|---|---|
| HEAD | `14dbaf4`, clean, in sync with origin |
| suite | **42 passed** |
| version | **0.1.0** — leave it there, see *On hold* below |
| visibility | **PUBLIC** (the Director set it so today; the README's "private repo" line is stale and is mine to correct) |
| CI | **none** — there is no `.github` directory at all |
| untracked | `SHIP_GATE.md`, `SECURITY.md`, `CHANGELOG.md`, `SCORECARD.md` — from a shipcheck run by another seat, not yours, uncommitted |

## The work list — a shipcheck Phase 0 ran here today

Every row is marked for how it is known. Rows marked *audit seat* were reproduced by a Sonnet
seat but not re-run by me; rows marked *measured here* I ran myself while writing this.

| # | finding | mark |
|---|---|---|
| 1 | **`pcraft gate <nonexistent path>` exits 0** — see below | **measured here** |
| 2 | **The wheel build fails.** `ValueError: A second file is being added to the wheel archive at the same path: pcraft/domains/image/compiled/sprite.synth.v1.json`. sdist builds clean. | audit seat |
| 3 | The cause, and it is bigger than the error says: `[tool.hatch.build.targets.wheel] packages = ["src/pcraft"]` already ships **every** directory the four `force-include` entries name. All four are redundant; the build dies on the first collision it reaches. **Fixing only the named path moves the error to the next entry.** | **measured here** |
| 4 | **Raw traceback leak.** `pcraft replay` on a record that is valid JSON but fails schema validation dumps a full pydantic `ValidationError` traceback to stderr with no `--debug`. `asset_record.load()` guards `(OSError, JSONDecodeError)`; the following `model_validate` is unguarded, and each command catches only `PromptCraftError`. | audit seat |
| 5 | No `verify` script anywhere — no pyproject script, Makefile, tox or nox. | audit seat |
| 6 | No dependency scanning, because there is no CI. | **measured here** |
| 7 | Logging is a binary `--debug` toggle; there is no leveled logging (`import logging` appears nowhere in `src/`). | audit seat |
| 8 | `SECURITY.md` carries an unfilled template placeholder in its Scope section. | audit seat |
| 9 | File operations are unconstrained — `persist()` does `mkdir(parents=True)` on any `--records-dir`/`--db` path with no containment check. | audit seat |
| 10 | Dependabot: shipcheck hard-gates automated dependency updates; the org rule forbids adding `dependabot.yml` unless explicitly requested. **A standing tension, and a Director decision — not yours to resolve.** | measured (both documents) |

`src/pcraft/errors.py` is **not** under `core/`, so #4 is reachable without crossing the
boundary you measured.

## ⚑ The headline — the gate that cannot fail

I ran this myself:

```
pcraft gate E:/nope/does-not-exist.png

gate overall: UNCERTAIN  (contract char:ashen-reaver)
  [SKIPPED  ] tabard    -  -- (affirm/required)  vqascore.clip-flant5.v1 unavailable
  [NA       ] sigil     -  -- (affirm/required)  parent 'tabard' did not pass (SKIPPED)
  [SKIPPED  ] palette   -  -- (affirm/required)  siglip2.screen.v1 unavailable
  ... every atom SKIPPED ...
EXIT CODE: 0
```

**The gate reported on an image it never opened, and exited 0.** The verifiers declare
themselves unavailable (the `[image]` extra is not installed) before anything touches the path,
so a missing file, an unreadable file, and "extras not installed" are indistinguishable to any
caller reading the exit code.

The overall verdict is `UNCERTAIN` rather than `PASS`, so the human-readable line is honest.
The machine-readable signal is not.

This is the same law you built armature's gate around one round ago — *a check that cannot fail
is not a check* — and prompt-craft's own gate breaks it. It is also, now that the Director has
ruled, a gate that is **allowed** to block, which makes the defect live rather than academic.

Related, from the same run: `bind --no-mock` unconditionally raises `DEP_IMAGE_MISSING`, so
the non-mock path has never executed on this rig.

## On hold — the Director's call, so you are not guessing

A full treatment was queued for this repo and is **partially on hold**, deliberately.

**On hold, and not yours:** the version promotion (0.1.0 → 1.0.0), README and its translations,
the landing page, the handbook, GitHub metadata, the logo, and any publish. These wait because
your round changes what is true about the repo, and a v1.0.0 badge on a scaffold whose wheel
does not build would be a claim on a public surface that the repo cannot support.

**Not on hold, and it is this round:** the hard-gate engineering — the A–D items above. Those
are not marketing; they are whether the thing works. The split is clean: you make the repo
true, the surfaces get authored afterward to match.

**Leave `version = "0.1.0"` exactly as it is.**

## What to build this round — and argue the scope

**My call**, and it is a call:

1. **The gate's exit contract** (#1). A gate that cannot see its input must say so and must not
   exit 0. What the right shape is — a distinct exit code for *could not run*, a hard refusal
   when a required verifier is unavailable, a preflight that raises on an unreadable path
   before any verifier is consulted — **is yours to decide.** armature's law says the check
   lives inside the tool that performs the step and raises; how that maps onto a three-tier
   gate with legitimately-optional tiers is the interesting question.
2. **The wheel build** (#2/#3) — and please fix the cause, not the symptom.
3. **The traceback leak** (#4).
4. **A `verify` script** (#5) and **CI** (#6) — paths-gated, `ubuntu-latest`, one OS, max two
   workflow files, concurrency group with `cancel-in-progress`, per the org's Actions rules. Do
   **not** add `dependabot.yml` (#10).

**Deliberately not this round:** logging levels (#7), path containment (#9). Both are real;
both are bigger design questions than they look, and #9 in particular needs a decision about
whether an unrestricted local path is intentional for a local-first tool. Say so if you think
either belongs in scope.

**If that is the wrong half, cut it.** You have cut a brief down repeatedly and been right.

## Argue

1. **The gate's exit contract** — the shape, per above. This is the round's real design
   question.
2. **Does the atom / identity line hold in the code?** The Director ruled it holds in principle.
   prompt-craft's contract has `face` as a required atom and `no_human_face` as a required
   negation. Is `face` an atom, or is it identity wearing an atom's clothes? If any existing
   atom is doing identity work, that is the most valuable thing you can return.
3. **The install path.** The README documents `pip install -e ".[dev]"`; nothing on this rig has
   ever run that way. Is the wheel fix enough to make the documented path real, or is there
   more?
4. **Anything unnamed.**

## Constraints

No GPU. No cloud generation. **No credits.** No publishing, no version bump, no repo-visibility
change, no commits. Gates `raise`, never a bare `assert`; `IMPLEMENTATION:`-labelled asserts are
allowed and must say why. Tests ride the commit. Every premise you rely on marked **measured**
or **assumed** — including the ones in this brief, three of which are another seat's
measurements and are marked as such.

Counts as of this brief: prompt-craft **42 passing**; armature **1341 passing / 13 skipped /
1354 collected** with your #1 change-set uncommitted in the tree.

## Calibration

Nominate **one checkable claim** we verify by running it before anything trusts the rest.

One for one. A round where the chip loses is still reported.
