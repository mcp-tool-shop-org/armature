# THE HANDOFF — armature advisor seat, 2026-08-18

Supersedes the 2026-08-17 handoff (git history holds it). Written from armature's own seat at the
close of the session that shipped **v0.3.0** and took the sibling repo `prompt-craft` from
scaffold to published.

§3 is measured at write time with the commands named. **Verify it again; do not inherit it.** The
previous handoff's §3 carried three stale rows, and one of them was a unit error that survived
into a dispatch — see §8.

## 1. Read first, in this order

`CLAUDE.md` — the scope block, THE POSTURE, the non-negotiables (licence gate · identity is the
product · per-route disclosure · credits are bounded · judging artifacts) → this file → **verify
§3 with your own commands** → the memory store's session-end entries.

The portable core of the law lives in facet's `CLAUDE.md` and armature's own file says so. Still
true.

## 2. The frame, unchanged

armature is **image-to-video with a GLB instead of an image** — block the shot in headless
Blender (character, pose, camera), render per-frame control sequences, and the video model paints
life over it. Footage of every kind; **describing it by a use-case is the drift signature.**

THE POSTURE: experiments exist to learn; the monorepo redefines itself as experiments prove
paths; no route is canon by momentum; dated field checks keep technique fresh.

**Identity is the product, and no metric approximates it.** Identity diagnostics ride reports and
gate nothing. That ruling was re-affirmed by the Director on 2026-08-17 in its sharper form — see
§4.

## 3. State at write time — measured 2026-08-18, verify again

| | |
|---|---|
| HEAD | `c7549b9`, main **clean and in sync** with origin |
| suite | **1351 passed, 14 skipped** (`1364` collected) — ⚠ collected ≠ passing, see §8 |
| published | PyPI `armature-studio` **0.3.0** · npm `@mcptoolshop/armature-studio` **0.3.0** |
| release | [v0.3.0](https://github.com/mcp-tool-shop-org/armature/releases/tag/v0.3.0) — verify · pypi · npm all green, OIDC, no long-lived token |
| CI | green on main (ci · pages · dependency-graph) |
| record index | **verify PASSES all four legs**, 139-file corpus, rebuilt 2026-08-18 |
| arcs | E01–E14 closed; S01–S06 closed; **S07 standing by** for facet's v3 performer |
| credits | pool anchor 12,962 at 2026-08-12 evening; **the attribution pass is still open** |

Commands: `git status -sb` · `.venv\Scripts\python.exe -m pytest -q --basetemp=<scratch>` ·
`PYTHONPATH=E:/AI/record-index .venv\Scripts\python.exe tools/armature_index.py verify` ·
`npm view @mcptoolshop/armature-studio version` · the PyPI JSON API.

⚠ Two traps this session hit, both worth inheriting:
- `--basetemp` is **not optional** on this rig — without it pytest dies on a Windows
  `PermissionError` before collecting, and it reads like a repo failure.
- `PYTHONPATH=E:/AI/record-index` is **not optional** — `record_index` is a sibling repo.
- **Registry APIs cache.** PyPI showed `0.2.1` for minutes after `0.3.0` was live. Check the
  version-specific endpoint before concluding a publish failed.

## 4. What shipped, and what it means

**Gate CANON** (`tools/armature_core/canon.py`, `tools/canon_gate.py`). A machine-readable
statement of what a subject **is**, keyed on surface, where a **null occupant is a hole rather
than an absence** — an element list cannot show what it omitted. Both directions are checked; the
reverse one (everything in the prompt *is* canon) is the one that discriminates.

Three structural facts worth carrying:

- **Nothing in this repo submits.** No tool makes a network call; the payload builders write files
  and a *session* submits them. So the irreversible step this tree owns is **writing a payload**,
  and the gate raises before `os.makedirs` in all seven spend builders. A refusal leaves no
  directory behind.
- **The escape is census-backed.** `--no-canon` on a subject that *has* canon raises `checkbox`;
  with no subject at all, `escape_no_subject`; a file whose every occupant is unratified,
  `unratified_only`. A check that cannot fail is not a check.
- **A deliberate tripwire.** Four r2v tests carry `--subject=PERFORMER --no-canon` permanently.
  Correct while PERFORMER is identity-only; the day it gains a ratified surfaces file those four
  will raise `checkbox` and fail loudly. **That is the design, not a regression.**

**The Director's ruling, 2026-08-17 — the atom / identity distinction HOLDS.** A gate on
*nameable attribute presence* (a garment, a palette, a silhouette, the absence of a rival colour)
is a legitimate object and may block. **Identity — whether the figure is the same character —
gates nothing, ever.** This is not yet written into `CLAUDE.md` beside the identity
non-negotiable, and it should be. It currently exists only in commit messages, the Grok briefs
and `docs/research-grounding-verification-gates.md`.

## 5. What is actually open

1. **The credits attribution pass** — real drawdown against `prompt_id`s, unreconciled, and it
   has more to reconcile than the last handoff said.
2. **A mechanical post-translation count assertion** — *owed, and the highest-value small item in
   this list.* See §8; four languages shipped stale across two tags before this was caught by
   hand.
3. **The composed route's three follow-ons** (E13 closing R8): steering under the two-seed law,
   the subject-scoped clause, reference count.
4. **The driven unpark** — licence-clear; needs its spec on the three measured questions plus a
   movement-library adoption row.
5. **Owed instruments** — the seam-free camera instrument (E12 R5) · the foot instrument's
   hip-origin condition · the builder's stale fit string.
6. **S07** stands by for facet's v3 performer.
7. **Record-index items not acted on** (published sibling, shared with facet): a false docstring
   claim, and leg 3's number meaning "parser defect" on a fresh DB but "documents edited since
   build" on a stale one, with nothing distinguishing them.

**Closed this session, do not re-open:** the worktree suite-skew (every skip in every tree is
asset-presence gating on gitignored `outputs/`; each tree reads its own) and the six dangling
index pointers (the index was six days old against a corpus grown 45 → 139 files; three of the six
described *facet's* files under armature-relative paths).

## 6. The sibling repos

**facet** — unchanged in kind: armature supports with evidence and sequencing, never edits
facet's tree, and the reverse holds. If you survey a facet asset, carry the **date** of its
ruling, not the word "accepted" — acceptance there is a ruling on an artifact at a date.

**prompt-craft** — new relationship, and it is now a real one. armature evaluated adopting it as
the home for Gate CANON and **declined on measurement**: its plugin contract exports
`Generator + Verifier[] + encoder_rules_path`, and a character statement plus a spend refusal is
neither. The README's "add a domain, core does not change" claim **holds for a plugin-shaped
feature**; this feature was not one. That finding came back *because* `core/` was fenced rather
than granted. prompt-craft shipped v0.2.1 to both registries the same day; a dogfood-swarm kickoff
for it is at `memory/prompt-craft-dogfood-swarm-kickoff.md`.

## 7. The outside build channel — use it

Four Grok rounds ran this session (`docs/grok-consult-1-brief.md` … `-4-brief.md`), four for four
on nominated chips, every chip verified **by running it** before anything trusted the round.

What the channel is worth, stated concretely: **three rounds running, the best finding was the
one the brief did not ask for.** It corrected my Nagios suggestion (3 was already taken by
`PARTIAL_UNCONFIRMED`, so could-not-run went to 4); it found the transcript-level twin of a defect
I had only asked it to fix at the exit code; and it found a substring back door routing garment
claims to identity repair that a study-swarm independently surfaced from the literature the same
afternoon.

**The form that works:** a brief carries measured state with commands, marks every premise
*measured* or *assumed*, names what is fenced and why, gives a real decision rather than a
rubber-stamp, and ends with a nominated chip. Round 1 handed it a genuine decision with no
reserved veto, and the answer was better than either branch offered.

Also live: the Comfy consult channel — `docs/comfy-consult-12-brief.md` is **written and
unsent**, asking whether the served platform has a verifier tier at all.

## 8. Seat calibration — errors this seat made, so you know what to distrust

| error | what it means for you |
|---|---|
| Inherited a handoff row claiming the suite "drifted 1311 → 1324" and nearly built a swarm phase on it. **1311 passing + 13 skipped = 1324 collected** — different objects, nothing had moved | Re-measure §3. Always ask what one of the counted thing *is* before quoting a number |
| Told a subagent to expect only section-E items outstanding on a shipcheck audit. **11 of 15 remaining were hard-gate A–D** | My predictions about another repo's state were wrong by a factor of three |
| Asserted "nothing in armature submits" as fact in a dispatch. The executor correctly marked it **assumed**; I re-grepped afterwards and it held | Mark your own premises. The seat with least reason to doubt them is the one writing them |
| Probed `family_guard` with a bare string where `list[str]` was expected, read the vacuous pass as a broken guard, and was wrong — Python was iterating characters | The slip found a real latent hole, but the first reading was mine and it was incorrect |
| **Published prompt-craft with no npm README and a PyPI page whose logo and seven language links were dead.** shipcheck read 100% throughout | The studio checklist names both failures. I adapted armature's `release.yml` and skipped armature's *packaging*. Run `npm pack --dry-run` **before** the release commit |
| Ran `npm deprecate` on a placeholder off a playbook note, solving nothing, and handed the OTP failure back to the Director as a to-do | Do not perform a step because a playbook mentions it. Ask what it fixes here |

**What held:** every chip and every subagent claim verified by running it before it was trusted;
the release ordering caught four stale translations before an immutable tag; and the citation gate
was fixed and re-run rather than reported as a verdict when its verifier was unreachable.

## 9. ⚑ The pattern this session found seven times

A tool reporting **success while doing nothing**. Written out because it is the most transferable
thing here:

1. `pcraft gate` scored an image it never opened and exited 0.
2. `prism verify` exited 0 while refusing to run on a missing signing key.
3. Its groundedness lens returned a top-level `revise` verdict while **all fifteen lenses** had
   failed on an unreachable provider.
4. A stale `.pyc` ran a predicate contradicting its source; the suite stayed green.
5. `armature_index.py build` never wrote a certificate, despite the library's own docstring
   claiming no such path existed.
6. The record index verified against a corpus six days out of date.
7. **The translator reported `ok` for seven languages** while four carried a count from two
   releases earlier.

Every one is the same shape as the defect Gate CANON exists to prevent. **The generalisation:
check the thing, not the report about the thing** — read `lens_results`, tarball contents, the
registry's version-specific endpoint, the actual numbers in the actual files.

## 10. What to do first

1. Read §1's documents in order; **verify §3 with your own commands.**
2. Write the Director's atom/identity ruling into `CLAUDE.md` beside the identity non-negotiable
   (§4). It binds both repos and currently lives only in commit messages.
3. Build the **post-translation count assertion** (§5.2). It is small, it is owed, and it is the
   one that nearly put four stale languages on an immutable tag.
4. Everything else is the Director's call on sequencing.

Marathon, not a race. **Do not end a session the Director has not ended.**
