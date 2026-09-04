# DISPATCH — attribution repair: the phantom contributor on a public repo

**Written** 2026-09-03 by the advisor seat, from armature's own tree.
**For** the dogfood-swarm session holding armature.
**Status** READY — blocked on one precondition (§5), which the executor clears, not the advisor.

The Director found a third contributor on armature's public GitHub page and asked what it was.
It is our defect, not a stranger's commit. This dispatch removes it and closes the hole that
made it.

## 1. Trajectory

A public repo whose contributor graph credits an uninvolved third party misstates who authored
the record. armature's whole method is that the repo *is* the record — provenance that is wrong
about its own authorship undercuts every provenance claim the pipeline makes downstream. This
spend buys back the accuracy of the record's own byline. It advances no route and no gate; it
repairs the surface every route is published on.

## 2. The defect, measured

One commit carries a mistyped author identity.

| | |
|---|---|
| commit | `06c1caf` — *E02 bridge RULED: "lossless by construction" withdrawn…* |
| dated | 2026-08-10 18:16 -0400 |
| author + committer email | `64996708+mcp-tool-shop@users.noreply.github.com` |
| correct email | `64996768+mcp-tool-shop@users.noreply.github.com` |
| the error | two digits transposed, `68` becomes `08` |

GitHub resolves a `users.noreply.github.com` address by the **numeric id before the plus sign**,
not the login after it. Id `64996708` is a real, unrelated account (`Andres-cyber`, created
2020-05-08, one public repo, zero followers). GitHub therefore lists that account as a
contributor to a **public** repo, with one contribution.

The commit's content, message and tree are correct and untouched. Only the identity field is
wrong.

## 3. Root cause, and the rule that closes it

The session that made the commit was running out of a scratchpad worktree and passed the author
identity **inline on each commit command**, of the form:

    git -C <worktree> -c user.name=... -c user.email=<hand-typed address> commit -m ...

The same session typed that email by hand on every commit it made and got it right every other
time. The flag was never necessary: the rig's global git config already holds the correct
identity (verified 2026-09-03 — `user.email` is `64996768+…`, `user.name` is `mcp-tool-shop`).
Retyping a constant that config already supplies is a defect generator with no upside.

**Standing rule, to be added to CLAUDE.md by this dispatch (§7):** commits use the configured git
identity. Never pass `-c user.name` or `-c user.email` on a commit command. If a worktree lacks
an identity, fix the config once; do not retype it per call.

## 4. Scope — swept, not assumed

Every repo under `E:/AI` was swept for author emails carrying a numeric-id prefix other than the
canonical one (2026-09-03).

| finding | verdict |
|---|---|
| `64996708+…` in `armature` | **the defect** — 1 commit |
| `64996708+…` in `armature-E07 … S06` (15 dirs) | **same commit** — these are worktrees sharing armature's object database, not separate incidents |
| `dependabot[bot]`, `github-actions[bot]` in ~30 repos | expected bot identities, not defects |
| third-party ids in `ai-toolkit`, `llama.cpp-src` | upstream clones of other people's projects, not ours |

**One commit, one repo.** No other repo in the workspace carries a mistyped identity.

## 5. PRECONDITION — the gate this dispatch stops at

**A live dogfood swarm holds six worktrees in this tree.** Measured 2026-09-03:

- run `8481819-3690`, six worktrees under `.swarm/worktrees/` on branches `swarm/8481819-3690/w1-*`
- all six sit at `1789360` with **0 commits ahead of main** — no work is at risk yet
- local `main` is at `956ed0c`, **1 commit ahead of `origin/main`** and unpushed

A history rewrite re-parents every commit these worktrees are based on. **Do not begin §6 while
the swarm is running.** Clear all three of these first, then proceed:

1. The swarm run is finished or deliberately stopped, and its branches are merged or abandoned by
   the Director's word.
2. `git worktree list` shows no `.swarm/worktrees` entries (`git worktree remove` each, or
   `git worktree prune` after the swarm's own teardown).
3. `git push origin main` has landed `956ed0c`, so origin holds everything before the rewrite
   begins. Rewriting while origin is behind loses that commit.

If any of the three is unmet, **halt and report**. Do not improvise past this gate.

### 5a. AMENDMENT 2026-09-04 — the §5 measurement above is superseded

The paragraph above was measured at 2026-09-03 20:35 and was already stale within hours. It is
left standing rather than deleted, because the shape of the error is the lesson: **a precondition
measured against a moving run expires faster than the document that carries it.** Re-measure §5
yourself at execution time; do not inherit either block.

Re-measured 2026-09-04 01:50:

| | 2026-09-03 (above) | 2026-09-04 (now) |
|---|---|---|
| wave | `w1-*` | **`w5-*`** |
| worktrees | 6 | **7** (`w5-instruments-measure` is new) |
| worktree head | `1789360` | **`066db8d`**, 0 ahead of main, 1 behind |
| local `main` | `956ed0c` | **`d152380`** |
| `main` ahead of `origin/main` | 1 commit | **51 commits, all unpushed** |
| `origin/main` | `1789360` | **`1789360` — unchanged** |

Two consequences the original §5 did not anticipate:

1. **The swarm is merging into `main` continuously.** Waves 3 through 5 landed roughly fifty
   commits, including this dispatch's own base. The rewrite in §6 will re-parent every one of
   them. That is not a new hazard — it is the same hazard, now fifty times larger — and it is
   why §5.1 stands unchanged.
2. **`origin/main` has not moved since 2026-08-18.** The §6.2 scratch-run numbers (290 commits,
   5 tags, tree `1f2c70e7…`) were measured against origin and are therefore still exact. They
   describe the remote, not this working tree. **They will stop being exact the moment the swarm's
   fifty commits are pushed.** Re-run §6.1–6.2 against origin after the push and before the force
   push; do not carry today's table into a different remote.

§5.3 is unchanged in intent and larger in scope: push the swarm's full stack to `origin/main`
before the rewrite begins, not one commit.

## 6. The procedure — measured, not proposed

Run in a scratch mirror clone first; that is where the numbers below came from. The advisor ran
the whole of §6.1–§6.2 on 2026-09-03 against a fresh mirror of origin and pushed nothing.

### 6.1 Back up (this is the compensator — do not skip)

    git clone --mirror https://github.com/mcp-tool-shop-org/armature.git armature-backup-PRE-REWRITE.git

Keep it until §6.5 passes. It is the only undo.

### 6.2 Rewrite

    git clone --mirror https://github.com/mcp-tool-shop-org/armature.git armature-rewrite.git

Write the mailmap file (one line, exact, no wrapping):

    mcp-tool-shop <64996768+mcp-tool-shop@users.noreply.github.com> <64996708+mcp-tool-shop@users.noreply.github.com>

Then:

    cd armature-rewrite.git
    python -m git_filter_repo --mailmap ../armature.mailmap --force

`git-filter-repo` is present on this rig as a Python module (verified 2026-09-03). Invoke it as
`python -m git_filter_repo`; it is on the system Python, not the repo venv.

**Measured result of exactly this command:**

| check | before | after |
|---|---|---|
| commits reachable | 290 | **290** |
| identity fields carrying `64996708` | 2 (author + committer of one commit) | **0** |
| tags | 5 | **5** |
| `main` tree hash | `1f2c70e7…` | **`1f2c70e7…` — identical** |
| `main` commit sha | `1789360…` | `5b61204…` |

The repaired commit reads `mcp-tool-shop <64996768+mcp-tool-shop@users.noreply.github.com>` with
its message byte-for-byte unchanged.

### 6.3 What changes that you did not ask to change

**All 290 commit SHAs change, not only the 271 descendants of the defect.** The cause is measured,
not guessed: the root commit (`2aefc0b`, *Initial commit*) and `2c25b99` (*Update README.md*) were
created through the GitHub web UI and carry **GitHub's GPG signature**. `git-filter-repo` strips
signatures, because a signature over rewritten content would be invalid. Stripping the root's
signature changes the root's SHA, and that cascades through every commit.

The cost is **two "Verified" badges** on two trivial repository-creation commits. Their trees,
messages, authors and dates are unchanged — confirmed by direct object comparison.

**A narrower variant was tried and rejected on measurement, not taste.** Limiting the rewrite with
`--refs <parent>..<each branch tip>` plus `--partial` does preserve both signatures and touches
only 270 commits — but the five tags are not in that ref set, so they keep pointing into
unrewritten history, the defective commit stays reachable through them, and the contributor entry
survives. Measured: bad-identity fields after the partial run, **2**. It does not solve the
problem.

### 6.4 Push

Origin has no branch protection on `main` and **no open pull requests** (verified 2026-09-03), so
nothing is blocked and nothing is orphaned.

    cd armature-rewrite.git
    git push --force --mirror https://github.com/mcp-tool-shop-org/armature.git

This moves 7 branches (`main`, `E13-run`, `E14-run`, `S03-run` … `S06-run`) and re-points 5 tags:

| tag | old target | new target |
|---|---|---|
| v0.1.0 | `ff9021b` | `51f9407` |
| v0.1.1 | `e53fb29` | `e4520e4` |
| v0.2.0 | `72e6c2f` | `09bb6ef` |
| v0.2.1 | `5107b4e` | `703939d` |
| v0.3.0 | `c7549b9` | `dc0e66d` |

The local-only tag `swarm-save-1788481819` is not on origin and is not part of this.

### 6.5 Verify — every row, before declaring anything

1. `gh api repos/mcp-tool-shop-org/armature/contributors --jq '.[].login'` returns **only**
   `mcp-tool-shop`. GitHub's contributor list is cached; if `Andres-cyber` persists, re-check
   after a delay before concluding the rewrite failed. **Registry and API caching has produced a
   false failure verdict in this repo before** (HANDOFF §3).
2. `gh release list --repo mcp-tool-shop-org/armature` still shows all four releases
   (v0.1.0, v0.1.1, v0.2.1, v0.3.0). **This is an ASSUMED premise, not measured** — GitHub
   releases key on tag *name*, so a force-updated tag should carry its release with it, but the
   advisor did not test it. If a release detaches, it is recreatable from the new tag; record
   what actually happened.
3. `git log --all --format='%ae%n%ce' | grep -c 64996708` returns **0** on a fresh clone.
4. CI is green on the rewritten `main`.
5. The four release tags' trees match their pre-rewrite trees (they do in the scratch run —
   trees are untouched by identity edits).

### 6.6 Re-sync every local clone

Every worktree and clone on this rig is now based on abandoned history. After the push:

    git fetch --all --prune --force
    git reset --hard origin/main

The reset runs in `E:/AI/armature` only, and only after confirming nothing local is unpushed.
The 15 experiment worktrees (`E:/AI/armature-E07 … -S06`) hold closed arcs on branches that are
`gone` on origin. They are read-only history; leave them or remove them, but do not force-push
them back.

## 7. The prevention, which ships with the fix

Add to `CLAUDE.md` under Environment, in the same commit as the repair:

> **Commits use the configured git identity.** Never pass `-c user.name` or `-c user.email` on a
> commit command, in any worktree. The rig's global config holds the correct identity; retyping it
> per call is how a transposed digit put an unrelated GitHub account on this repo's public
> contributor graph on 2026-08-10, where it stayed for three weeks. If a worktree has no identity,
> fix the config once.

## 8. Compensators — irreversible actions in this dispatch

No skip is permitted on this table.

| irreversible action | compensator | post-rollback state | owner |
|---|---|---|---|
| `git push --force --mirror` over 7 branches + 5 tags | `git push --force --mirror` from `armature-backup-PRE-REWRITE.git` (§6.1) | origin restored to pre-rewrite SHAs exactly; the contributor entry returns | executor |
| GPG signatures stripped from `2aefc0b`, `2c25b99` | **none — permanent** | two "Verified" badges cannot be restored; GitHub alone holds those keys | accepted cost, §6.3 |
| local `git reset --hard` in §6.6 | none if §5.3 was honoured | unpushed local work is lost, which is why §5.3 gates it | executor |

The backup mirror is deleted only after §6.5 passes in full.

## 9. Credit ceiling

**Zero.** No generation, no provider, no partner tier. This dispatch spends no credits and touches
no model. Local git and the GitHub API only.

## 10. Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | Every command is written literally with its exact flags; the mailmap content is byte-exact; `git-filter-repo` is invoked by module path. The whole of §6.1–6.2 was executed once already and its outputs are recorded as the expected values. |
| ANDON_AUTHORITY | 3 | §5 is a hard halt with three named conditions and an explicit instruction not to improvise past it. §6.5 row 1 names the specific false-failure mode (API caching) that would otherwise trigger a wrong verdict. |
| NAMED_COMPENSATORS | 3 | §8 names an undo for each irreversible action, with post-rollback state and owner, and marks the one permanent loss as permanent rather than papering over it. The backup in §6.1 is ordered before the rewrite, not after. |
| DECOMPOSE_BY_SECRETS | 2 | The repair (§6) and the prevention (§7) are separated: one is a one-time history operation, the other a standing rule that outlives it. They ship together so the hole does not reopen. |
| UNCERTAINTY_GATED_HUMANS | 2 | The one unmeasured premise (release survival, §6.5 row 2) is marked ASSUMED in place rather than asserted. The Director has already ruled that the repair proceeds; what remains is execution, so no further checkpoint is inserted. |
| EXTERNAL_VERIFIER | 1 | The advisor seat wrote and also test-ran the procedure. That is the same family verifying its own work. Mitigated by the verification being mechanical — SHA counts, grep counts, tree hashes — rather than judgement, and by §6.5 requiring the executor to re-run every check against the real remote. **Remediation:** the executor reports §6.5 output verbatim; the advisor does not grade its own run. |

## 11. Out of scope

- Any change to commit **content**, message, date, or tree. Identity fields only.
- The other 289 commits' identities, which are correct.
- The bot identities in other repos (§4) — expected, not defects.
- Anything the live swarm is doing. This dispatch waits for it; it does not touch it.
