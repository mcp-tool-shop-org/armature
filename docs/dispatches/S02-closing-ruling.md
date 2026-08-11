# S02 closing ruling — the index is merged, the package is published, and the five questions are ruled

**Seat:** advisor · **Ruled:** 2026-08-11 · **Dispatch:**
[S02-record-index-extraction.md](S02-record-index-extraction.md) · **Report:**
[S02-report.md](S02-report.md) · **Merged to main with this ruling.**

**Context at ruling time:** `record-index` 0.1.0 is live on PyPI (OIDC Trusted Publishing,
release v0.1.0, digital attestations), carrying its own 455-check suite built after the
Director gated publication on tests. armature's CI can now resolve the dependency, so this
merge proceeds. facet's push follows separately once its own moved-property test debt is
cleared (see Ruling 5).

## The five questions from the report's §7, ruled

1. **Should the vocabulary counters ever gate?** Not today, and not silently ever. They
   report. facet's own `law paid_for_by` would fail its verify on day one at 32/32 if they
   gated. A future spec may propose gating for a repo whose record is born under the counters
   — as a spec, with the day-one number measured first.
2. **facet's `PAID_RE` frozen at E01–E15** (half its law attributions silently null) — a real
   facet defect, surfaced by this build, assigned to the facet test-debt executor dispatched
   today alongside the re-homing work.
3. **The t30/t19 class re-homes into record-index's own suite.** Ruled and already executed:
   the package's 455-check suite carries the andon-under-`-O` proofs, the exception-type
   census, and the write-surface scan re-pointed at the package (three functions mutate a
   file; eight modules mutate nothing). facet keeps its adapter and instrument tests; its
   four stale AST-scan tests re-point or retire in the facet-side sweep.
4. **Publication unblocks the five wheel tests** — published. The tests additionally need
   their fixture to resolve dependencies inside its venv (measured today:
   `ModuleNotFoundError: record_index` inside the wheel venv, so the fixture installs
   without deps). Fixture fix rides the same facet-side sweep.
5. **The certificate duplication** (facet's server vs `record_index/certificate.py`) — the
   canonical implementation is the **package's**. facet consumes it in a future change,
   queued with record-index 0.1.1's four pinned defects. Not a blocker; exactly the "next
   version should not be far behind" shape the handoff predicted.

## What S02 delivered, now on main

`docs/index/armature.db` + paired certificate (SERVING) · `docs/index/conventions.json` —
armature's declaration, stated rather than inherited · `tools/armature_index.py` — the
adapter · 47 rulings indexed, 15/15 seed queries returning. The five extraction gates all
returned PASS at build time (G1 byte-identity 19/19 · G2 facet suite untouched · G3 zero
row-level diffs · G4 db+cert paired · G5 armature seeded).

**Standing rule inherited with the index:** the markdown stays canonical; the index is
derived and regenerated on fold; it is wrong by definition the day it is hand-edited.
