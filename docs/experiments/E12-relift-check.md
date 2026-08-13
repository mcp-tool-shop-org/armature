# E12 — the re-lift check: both E09 pins are what their recorded inputs still produce

**Executor seat, 2026-08-12, branch `E12-run`, before the close-merge.** Owed since the wave-3
report named it outstanding; run here as the first item of the close, per the Director's order.
**Result: MATCH on both pins. No halt.**

## The question

Every E11 and E12 generation was conditioned on a start frame rendered from an E09 GLB that has
sat on disk since it was lifted. If the solver that produced it is not deterministic — or if the
file drifted — then the arc's conditioning image has an **unrecorded ancestor**, and every
identity claim resting on it rests on a file nobody re-derived. The failure is silent by
construction: a stale or drifted pin loads, renders, gates and generates exactly like a fresh one.

## What was run

The lift was re-solved from the **pinned motion records** through the same solver, into a fresh
output, and the result compared against the on-disk GLB. Inputs read from each pin's own
`*.lift.json`, never retyped:

| | b2-lifted | b2-a3-lifted |
|---|---|---|
| source GLB | `asset/performer_auto.glb` (`7f56c9ac…`) | same file, same hash |
| manifest | `asset/rig_manifest_auto.json` | same |
| motion record | `b2-measure/lifted_ema.motion.json` | `b2-a3-measure/lifted_ema.motion.json` |
| fps / frames | 16 / 65 | 16 / 65 |
| solver version | E09.1 | E09.1 |

Both re-solves passed their own in-tool gate on the way out — `gate_ARRIVED` max **5.348e-06**
(b2) and **7.368e-06** (b2-a3) over 65 frames.

## The comparison, and why it is geometry

`tools/check_relift.py` (new, with `armature_core.glb.compare_signatures` as its bpy-free
arithmetic and `tests/test_check_relift.py` as its fixtures) compares **per-frame evaluated
world-space geometry** — what the renderer would actually draw, following the imported action —
rather than file bytes. CLAUDE.md's law is that a file-hash mismatch is not evidence a render
changed: glTF export can reorder buffers or embed a generator string without a vertex moving.

Per **frame**, not per file, because a lift shares its rest pose with the file it was solved
from: frame 0 agrees even when the performance does not, so a check that compared only the first
frame would pass on every stale pin there is.

## Result

| pin | frames compared | frames differing | geometry | bytes |
|---|---|---|---|---|
| **b2-lifted** | 65 | **0** | all 65 frames identical | **identical** — `9aebeeb8e60da914aa0a2a49541bab7de60768dfc2f2ef25052529ed9dda0e93` |
| **b2-a3-lifted** | 65 | **0** | all 65 frames identical | **identical** — `cd4e2f6ee85ef536130cebe27fe2282f1bb1eba02a6c410d999e4f2351ea0c17` |

**The stale-pin question is closed.** The E09 lift solver is deterministic across a re-run on
this rig, and both on-disk GLBs are byte-for-byte what their recorded inputs still produce.

Byte-identity is *sufficient* here and was not assumed to be *necessary*: identical bytes cannot
decode to different geometry, so the geometry comparison could only have confirmed it — but the
instrument was pointed at geometry first, because had the bytes differed, bytes alone would have
proved nothing either way.

**`cd4e2f6ee85ef536…` is the GLB E12's own start frame was rendered from** — the same hash
recorded in E11 w3's start-frame provenance and re-checked at the head of E12 wave 1. That pin is
now confirmed at both ends of the arc: the file matches its record, and the record matches what
the solver produces today.

## Artifacts

```
outputs/E12/relift/b2-lifted.glb            the re-solve, b2
outputs/E12/relift/b2-lifted.lift.json      its sidecar, with gate_ARRIVED
outputs/E12/relift/b2-a3-lifted.glb         the re-solve, b2-a3
outputs/E12/relift/b2-a3-lifted.lift.json   its sidecar
outputs/E12/relift/relift-b2.json           the comparison record
outputs/E12/relift/relift-b2-a3.json        the comparison record
```

Compensator: delete `outputs/E12/relift/`; owner: the executor session. Both pinned GLBs and
every E09 input were opened **read-only**.

Suite at the time of this check: **970 passed, 48 skipped**.
