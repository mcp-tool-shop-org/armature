# E08 first route — halted tooling (superseded)

Archived byte-faithful from `E08-run` @ `8399d5a` on 2026-08-12, before that branch's
ref was retired from origin. The local `E08-run` branch and the `armature-E08` worktree
remain on the rig, pinning the halt commits and outputs; the undo for the origin
retirement is `git push origin E08-run`.

Files:

- `make_shot_spec.py`
- `render_reference.py`
- `E08-bar-approach.json` · `E08-bar-approach.az205.json` ·
  `E08-bar-approach.framing.json` · `E08-bar-approach.framing.az205.json`

**Why superseded:** this is the shot tooling of E08's first route, which halted twice at
zero credits (the halt commits on the local branch carry the reasons; the E08 spec's
appended rewrite and `docs/experiments/E08-closing-ruling.md` carry the record). The
shot that ran came from the rewritten route via `E08-shot`, which is merged. The E09
closing ruling's retirement condition — "bank fully subsumed" — was verified on
2026-08-12 and ran short at file level: the bank's artifacts had reached main, these six
files had not. Kept per the standing law: failures stay in the repo, runnable, with the
reason.
