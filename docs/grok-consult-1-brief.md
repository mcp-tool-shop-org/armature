# Grok build #1 — armature: the canon router, the spend gate, and a decision that is yours to make

**2026-08-17, armature advisor seat.** This is **round one in this tree**. The channel you
hold in facet is twenty-two rounds deep and ten-for-ten on nominated chips; none of that
history exists here, and you arrive with no armature context. The paste block below is
therefore heavier on ground truth than a facet brief would be, and deliberately so.

Everything in the state and enumeration sections was **measured today by running it**, not
inherited. Where this seat carries a claim it did not verify, the claim says so. The transfer
document that prompted this round is itself the reason for that discipline: three of its rows
did not survive re-measurement, one was a unit error — a *collected* test count quoted against
a *passing* test count and read as drift — and it omitted the single most relevant existing
asset in the studio, which is now the subject of the decision this round hands you.

**The Director has delegated that decision to you**, on one standard: what is best for
armature. This seat does not hold a reserved veto over it.

*Everything below the line is the paste block.*

---

# Round one in a new tree. One feature, one structural fact that shapes it — and one decision that is yours, not mine.

## Who you are in this tree

Outside consult **and build** channel, the same seat you hold in facet. armature is a
different repo with a different law surface, a different product, and no chip history.

**Access — two trees this round, because the decision below needs both to be real.**

- `E:\AI\armature` — read anything; write `tools/` and `tests/`; run the suite.
- `E:\AI\prompt-craft` — read anything; write `src/pcraft/domains/**` and `tests/**`.
  ⚠ **`src/pcraft/core/**` is fenced.** That repo's own README claims adding a new domain
  changes nothing in `core/`. If you find that claim is false, **that is a finding to report,
  not a licence to edit** — and it is one of the more valuable things you could return this
  round, because it decides whether its plugin boundary actually holds.

Change-sets stay **uncommitted** for the advisor's fold, and the two repos are separate
change-sets — do not let one tree's work ride in the other's.

**Fenced OFF this round, in armature:** `docs/experiments/**`, `docs/dispatches/**`, every
`README*.md` and its seven translations, `CHANGELOG.md`, `CLAUDE.md`, `SHIP_GATE.md`,
`SCORECARD.md`. Public surfaces are lead-authored here — a studio law with a scar behind it,
not a preference. `outputs/` is the artifact archive: read it, write none of it. `E:\AI\facet`
and `E:\AI\training\` are **READ ONLY in both directions** — armature never writes into
facet's tree and facet never writes into ours.

**You do not judge artifacts.** The words *verified, shipped, works, decisive, validated,
proven* do not belong in a report, a docstring, or a commit message in this repo. Produce
measurements; the Director judges. A negative result is a full success — say so plainly and
stop, rather than tuning toward a number.

## Open the tree

```
cd E:\AI\armature
git log --oneline -3
git status -sb
```

Python is `E:\AI\armature\.venv\Scripts\python.exe` — absolute, always.

Suite:

```
.venv\Scripts\python.exe -m pytest -q --basetemp=<a scratch dir>
```

⚠ **`--basetemp` is not optional on this rig.** Without it pytest dies with a Windows
`PermissionError` on `pytest-of-mikey\pytest-current` during dead-symlink cleanup, before it
collects anything. It reads like a repo failure and is not one.

prompt-craft's suite runs from its own root with `PYTHONPATH=src` and the same `--basetemp`
caveat. Measured today: **42 passed in 0.29 s**.

Record index:

```
PYTHONPATH=E:/AI/record-index .venv\Scripts\python.exe tools/armature_index.py verify
```

⚠ The `PYTHONPATH` is not optional either — `record_index` is a **sibling repo**
(`E:\AI\record-index`), not installed into this venv, so a plain invocation dies at
`ModuleNotFoundError: No module named 'record_index'`.

⚠ And it currently **FAILS**, measured today: `VERIFY FAILED - 2`, **6 dangling artifact
pointers of 107 rows**, with fts mirroring the same 6. Rulings (47), laws (38) and
experiments (6) are all clean at zero dangling. **Not yours to fix this round** — stated only
so you do not read it as damage from your own change-set.

## State, measured 2026-08-17 — reconcile nothing you did not move

| | |
|---|---|
| HEAD | `ea5c8fd`, main **ahead 1** of origin (an unpushed handoff commit) |
| suite | **1311 passed, 13 skipped** — 1324 collected |
| CI | green, run `31921018467` |
| published | npm `@mcptoolshop/armature-studio` 0.2.1 and PyPI `armature-studio` 0.2.1, both live |
| worktrees | 14 (E07–E14 incl. E08b, S02–S06) — the artifact archive; deleting one deletes unreproducible evidence |
| record index | verify FAILS, 6 dangling artifact pointers (above) |

⚠ **The trap that caught this project's own handoff, stated so it does not catch your
change-set:** 1324 is the **collected** count; 1311 is the **passing** count; the public
surfaces quote passing. They are different objects and neither is stale. State what your
change-set assumes.

**Every skip in this tree is asset-presence gating on git-ignored `outputs/`.** That is why
the number rises in a worktree — 48 skips in `armature-S06` against 13 on main — each tree
resolves `outputs/` to its own. The design working, not flake. (Measured today; the S06 tree
also sits at an older commit, so the exact delta at equal commits is unmeasured.)

## What armature is — read this before proposing anything

**armature is image-to-video with a GLB instead of an image.** Block the shot in headless
Blender — character, pose, camera — render per-frame control sequences and reference stacks,
and a video-diffusion model paints life over it, so the footage keeps **one persistent main
character** whose position and pose are known every frame.

Movies, game cutscenes, character performance, any footage at all. The scope has been shrunk
twice by seats in this repo and corrected twice by the Director, so: **describing armature by
a use-case is the drift signature.** If anything you write names a narrower product than
*footage from a scene you own*, that is the tell.

armature sits **downstream of facet**: facet cuts and paints the figure, armature stages and
performs it.

## The law that binds a build here

- **Gates raise; they never `assert`.** A check that decides whether an irreversible step
  proceeds lives **inside the tool performing that step** and `raise`s — no shell-chain
  separation (a chain walks past a failing exit code), no `assert` (deleted by `-O` or
  `PYTHONOPTIMIZE=1`), no skip flag. `IMPLEMENTATION:`-labelled asserts are allowed and must
  say why. **Put the andon on the direction the invariant does not bound.** A check that
  cannot fail is not a check; a diagnostic and a gate are different objects.
- **Tests ride the commit that touches the code.** Ask of every fixture: what would this look
  like if the code were wrong in the specific way this check exists to catch?
- **Every premise is marked measured or assumed.** An inherited claim is a hypothesis wearing
  a fact's clothes — and this binds hardest on the premises of *your own dispatch*, including
  every premise in this brief.
- **Enumerate the resource before commissioning one.** One grep separates a commission from a
  thing already built; the commission is always the expensive branch.
- ⚑ **Identity is the product, and no metric approximates it.** Whether the figure on screen
  **is the same character** is canon and the Director's to judge. Identity and quality
  diagnostics ride reports **as diagnostics and may gate nothing.** A standing ruling, reached
  twice the expensive way — once with high-pass statistics for material identity, once with
  silhouette IoU for character identity. It is the single most load-bearing constraint on this
  round, and it is **not** delegated.
- **Credits are bounded and spent credits have no compensator.**
- **The licence gate:** no non-commercially-licensed model, weight, LoRA, preprocessor or code
  dependency anywhere, including experiments. UNVERIFIED is treated as NO.

## ⚑ The decision this round hands you

**Does armature's canon and its spend gate get built here, or as a video domain inside
`prompt-craft`?**

**You decide.** The Director has delegated it, on one standard — **what is best for
armature** — and this seat holds no reserved veto. Not best for the studio's tidiness, not
cheapest to write, not whichever preserves an existing plan. Best for this repo, whose product
is one persistent character across footage and whose mistakes cost credits.

Decide it **before** you build, state the decision and the reasoning at the top of your
report, and then build in the tree you chose. If the honest answer is a third road neither of
us has named — a thin canon here now with an adoption path later, or something else — take it
and say why.

Below is everything I have that bears on it, both directions. I have tried not to weight it.

### What exists in prompt-craft, measured today

`E:\AI\prompt-craft`, private, under `mcp-tool-shop-org`. **42 tests pass in 0.29 s** with
`PYTHONPATH=src` — I ran it rather than trusting its README.

The studio constitution — the Director-ratified map, which outranks any handoff or session
record — carries it as **Stage 1b of the production spine**: *typed depictable contracts →
constrained synth → cross-family gate; the discipline the generate and eval stages run under.*
Status `built`.

What it is: a typed depictable **contract** → constrained **synthesizer** (every token traces
to a depictable atom) → **different-family gate** → retry/repair → **bind**, split by Parnas
secret into a domain-agnostic GPU-free `core/` and per-domain plugins. Its README states that
adding **video** is a new sibling under `domains/` with **nothing in `core/` changing**, and
the GPU-free core suite is offered as the proof that boundary holds.

Already in that core — each one a thing an armature-side build would have to write:

- a **fail-closed** faction→character contract loader that `raise`s (a child may raise a
  requirement, never drop or relax an inherited one)
- a **canonical provenance hash** over the contract
- a **NAMED_COMPENSATORS** registry
- a replayable per-asset **receipt**
- a **pre-generation Assert before any GPU spend** — every required atom must have a
  non-empty coverage phrase or it backtracks

### What cuts toward adopting it

- *Enumerate before commissioning* is the local law, and this is the case it was written for.
- The constitution places it **on the spine**, not off to one side — and flags that it was
  **missed entirely by an earlier memory**, with the correction *manifest beats memory*. The
  transfer document that prompted this round made the identical miss: it proposed armature
  build a canon router from scratch and never mentions prompt-craft. Twice now, the same asset
  has gone unseen by exactly this kind of document.
- The studio's named anti-pattern is **`built` but never `filled`** — a tool built and never
  used on a real consumer. Moving `built` to `filled` requires a real consumer, not a test
  count. prompt-craft is `built`. armature would be what fills it.

### What cuts against

- It is a **SCAFFOLD at v0.1.0**. Core and the image/sprite reference plugin are wired and
  **mock-tested against a deliberately generic, non-canon example contract**. Its core has
  **never run against a real canon.**
- Binding it to any real canon is separately **gated on the Director** by its own README —
  which is a gate on *its* canon binding, and you should read it and judge whether armature's
  use crosses it.
- Adopting makes armature simultaneously its **first real consumer** and its **first video
  domain** — two unproven boundaries crossed in one change-set, in the repo where a mistake
  costs credits.
- Its architecture ends in a **pixel gate that blocks**, which collides with armature's
  identity ruling. See the constraint below; that part is fenced regardless of which tree you
  choose, so it should not by itself decide the location.
- Its constitutional verified date is 2026-06-09 — under the studio freshness rule, **advisory
  until re-measured**. The suite run above is my re-measurement of the code, not of the design.

### What the choice does not change

The **feature** is the same either way, and it is described in location-neutral terms below.
The **fences** are the same either way: no credits, no submissions, no pixel-blocking gate.
And armature's law binds your change-set in both trees — gates `raise`, tests ride the commit,
premises marked measured or assumed.

## Two more things already here, whichever tree you choose

**`tools/armature_core/route_gates.py`, 1002 lines.** Gate ROUTE walks subgraph blueprints
before submission; Gate PAIR pairs each conditioning class with the weight family that can
receive it; Gate S proves every seed pinned; Gate L proves the frame generator-legal. These
`raise`. **This is the shape a spend gate here must match**, and the file's own comments
record, per gate, how it was once silently disarmed — a class absent from a table; a
conditioning node that sizes a latent, leaving Gate L examining zero latents while reporting
the graph legal. Read those comments before designing. They are the failure catalogue for
exactly the thing you are being asked to build.

**`tools/armature_core/subject.py`.** What a subject asset *is*, as a number: bounding-box
arithmetic and nothing more. **Deliberately no thresholds, no verdict, no `is_character`
boolean** — because whether a figure is the right character is canon and the Director's to
judge, while what a mesh's proportions are is a number. It exists because a spec once called a
sword "a facet-finished character asset" and the name was believed through an entire dispatch;
measured afterwards, the asset had aspect ratio 15.8. It is the local precedent for how far a
tool may go toward judging identity: not far.

## The structural fact that shapes the spend gate

**Nothing in armature submits.** Grepped today: no armature tool makes a network call. The
`tools/build_*_payload.py` family **builds payload files**; the submission is an MCP call made
by a **session**, outside the repo entirely.

So armature's own law — *the gate lives inside the tool performing the irreversible step* —
currently has **no home here**, because the tool performing the irreversible step is not in
the tree. Today's bound on spend is a sentence in a spec, honoured by a seat reading it. That
is the same failure mode facet measured: a gate written `if args.canon:` never arms when the
caller omits the flag, and nothing says so.

Three placements:

- **(a) At build time.** Every payload builder refuses to *write* a payload it cannot check,
  and never creates the output directory. Fully inside armature's law. Weakness: a payload can
  still be hand-built, or an older file re-submitted.
- **(b) A sanctioned submitter in-repo.** armature grows the one tool that submits, and the
  gate lives inside it. Strongest form of the law. Weakness: new surface, duplicating a
  capability the MCP already provides, and it must not become a worse client than the one it
  replaces.
- **(c) A signed payload.** The builder stamps a gate verdict into the payload; the session
  checks it before submitting. Weakness: the check is again a discipline *outside* the tool —
  which is the thing we are trying to stop relying on.

Your location decision may force one of these. Where it does, that placement follows with it
and is yours too. Where it genuinely leaves the choice open, argue it.

## What facet built, and its honest limits

facet's Grok round #18 landed a **canon router**: resolve, cover **both directions**, scope,
schema, and a gate in front of the cloud spend path. The load-bearing half is *both
directions* — checking that the prompt covers the canon finds a thin prompt; checking that
everything in the prompt **is** canon is what caught a phrase naming something the character
does not have, and that reverse direction was the only one that discriminated in their chip.

Two limits, carried honestly:

- **Canon binds 0.00% of the figure spatially.** The router knows what material belongs on
  `torso`; nothing in that repo knows which pixels are `torso`. The nameable half works; the
  spatial half is unbuilt and labelled as such.
- **A correction dated 2026-08-17** that the transfer document I inherited did not carry: the
  twin prompt in question carries **16 of 17** elements and misses only one, and the "six"
  figure quoted against it is a **brush default in a profile file** — a different object
  entirely. Build on the *shape* of that finding, not on its three-number story.

## Does the prompt studio apply?

My call: **as a question, not as an import** — and I hold this loosely.

facet's #19 density findings are T2I measurements on CLIP-family encoders (a per-component
inclusion cost; an effective reading length near 20 tokens). armature's text encoder is
**umt5-xxl** — licence map row, Apache-2.0, both graphs — and the models are Wan-family
**video**. That round's own F8 already reserves "our encoder is not CLIP, so this may not
transfer"; here the reservation applies with more force, not less.

armature's version of the question is sharper anyway: **here the prompt is not the only
identity carrier.** Every route pairs it with a control sequence and a reference plate, which
is precisely prompt-craft's *identity is conditioning, not tokens*. So the armature question
is not "how many elements before the prompt degrades" but **"how much identity load is the
text carrying at all, given the conditioning beside it"** — and that looks measurable for free
on payloads already banked under `outputs/`, without a single credit.

## What to build this round — location-neutral, and argue the scope

**The feature, wherever you decide it lives:**

1. **A machine-readable statement of what armature's character IS** — keyed on surface, with a
   hole expressible as a row rather than an absence, so that what is missing can be seen. An
   element list cannot show what it omits.
2. **A router over it, both directions** — that the submission covers the canon, and that
   everything in the submission is canon. The reverse direction is the one that discriminates.
3. **A gate in front of the spend that fails closed** — given no canon, it refuses and creates
   nothing. Any escape for a subject that genuinely has no canon must be backed by something a
   subject with canon cannot wear.

**Deliberately NOT the pixel-gate tiers, in either tree** — and this is where armature and
prompt-craft genuinely collide, so I would rather name it than let it surface mid-build.
prompt-craft's architecture ends in a gate that verifies contract atoms **on the pixels** and
**blocks bind**. armature's standing ruling is that identity diagnostics **may gate nothing**.

Those reconcile only if a *contract atom* — a nameable, checkable presence: a garment, a
palette, a silhouette — is a genuinely different object from *is this the same character*,
which is canon and the Director's. **I believe it is.** But that is a Director-level
reconciliation, it is not delegated to either of us, and nothing pixel-blocking gets built
until he has ruled it. **If you think the distinction does not hold, that is among the most
useful things you could tell me this round** — it would mean the adopt branch carries a
conflict deeper than a fence can hold.

**If the scope is the wrong half, cut it.** You have cut a brief down repeatedly in the other
tree and been right; there is no reason this seat's first armature call should be the
exception.

## Argue

1. **The gate's home** — (a), (b), (c) above, or a fourth I have not seen, where your location
   decision leaves it open.
2. **What does a canon element key on here?** facet's canon binds nothing spatially. armature's
   subject is a **GLB with named materials and a skeleton**, and the pipeline already renders
   per-frame control sequences from it. Is there a spatial binding available in this tree that
   facet never had — material name, bone, or rendered region — and does that change the schema?
   This is the genuinely new question armature can answer and facet cannot.
3. **The prompt-studio question** — is there a free measurement on banked payloads that settles
   how much identity load the text is carrying?
4. **Anything unnamed.**

## Constraints

No GPU. No cloud generation. **No credits and no submissions of any kind.** Gates `raise`,
never a bare `assert`. Tests ride the commit, in whichever tree the code lands.

`src/pcraft/core/**` is fenced — a needed change there is a **finding**, not an edit.

Test files in armature are **descriptively named** — `tests/test_<thing>.py`, 76 of them.
There is no `t`-number namespace in this tree; do not import facet's. Follow prompt-craft's
own conventions if you build there.

Counts as of this brief: armature **1311 passing / 13 skipped / 1324 collected**; prompt-craft
**42 passing**.

## Calibration

Nominate **one checkable claim** we verify by running it before anything trusts the rest.

This is round one here, so there is no streak to protect — and a chip that **loses** in round
one is worth more to this tree than a chip that wins.
