# E13 — the composed-route probe (report)

**Status: HALTED before the first submission. Zero credits spent. Zero generations
submitted. Zero uploads accepted.**

Executor session, 2026-08-13, worktree `E:\AI\armature-E13`, branch `E13-run`, cut from
`main` at `eb7a0ae`. Spec: [E13-composed-route-probe.md](E13-composed-route-probe.md).
Predictions committed before any submission: [E13-predictions.md](E13-predictions.md).

Two of the spec's premises are measured false. Both are structural — neither is a parameter
that could be changed and re-run — and together they mean the experiment as specced cannot
be executed. Nothing was adapted around; the run stopped where it stands, which is before
anything irreversible.

**Nothing in this report is a judgement of output quality.** No output exists.

---

## 0. Dispatch checks, in the order the dispatch ordered them

| check | result |
|---|---|
| Worktree exists at `E:\AI\armature-E13`, branch `E13-run` at `eb7a0ae` | present, clean |
| Branched spec contains both 2026-08-13 amendments (`grep "Amendment — 2026-08-13"` → 2) | **2 hits** — the disclosure note (line 84) and the DISPATCH amendment (line 216) |
| Binding documents read from `main`, not the worktree | done — and the two were compared. `docs/license-map.md`, `docs/comfy-consult-8.md`, the E13 spec and both E12 reports are **byte-identical between `main` and `E13-run`** (git blob hashes equal; the apparent whole-file `diff` is CRLF in the worktree checkout against LF in the object store) |
| Terms gate | **CLEARED** at the licence map's wan2.x partner-tier row (Director's CONDITIONAL, 2026-08-12). Not re-litigated |
| A2 clip sha256 against the pin | **MATCHES** — `b3b43e23f9bc5fb4e173d22815a12eb536e1e456510bf41700fe17e04eb9bd27`, recomputed on `E:\AI\armature-E12\outputs\E12\probe\w3-seed1\w3-seed1.mp4` (1,102,939 bytes). The E12 worktree was read and not written |

## 1. The fresh credit re-estimate — the executor's ordered first act

Run before any submission, as the dispatch requires.

| | |
|---|---|
| instrument | `estimate_credits`, template `api_wan2_7_r2v` |
| result | **106–211 credits per generation** (1 paid API node: `Wan2ReferenceVideoApi`) |
| four submissions | **424–844 credits** |
| the 900-credit halt | **DID NOT FIRE** — the re-estimated total sits inside the spec's own bracket |
| meter artifact | **none observed.** The dispatch anticipated a `0` reading (as at every E12 submission) and pre-ruled it a meter artifact. This path returned a real bracket instead, equal to the bundled-catalog figure the spec carried from 2026-08-12 |

**Bounded honestly:** this is a template-resolved estimate, not an override-exact one. The
tool states that overrides passed at submission are not reflected in its figure, so an
override-exact estimate requires the in-repo graph, which was not built (§4). The spec's pins
(720P · 16:9 · duration 5) include the node's own default duration of 5, and the per-
generation bracket did not move from the spec's, so the operative estimate is unchanged. The
four-submission ceiling binds regardless of what the meter says.

## 2. The node contract, re-measured

`Wan2ReferenceVideoApi` was re-measured with `get_node` at the start of this session, because
it is the contract any graph would be built against and it is a premise of this seat's own
dispatch. **It returns byte-consistent with the spec's premise row:** `model.prompt`,
`model.negative_prompt`, `model.resolution` ∈ {720P, 1080P}, `model.ratio` ∈ {16:9, 9:16,
1:1, 4:3, 3:4}, `model.duration` INT default 5 (min 2, max 10), `model.reference_images.
image1…image5`, `model.reference_videos.video1…video3`, `seed` INT (max 2147483647),
`watermark` BOOLEAN default false, one `VIDEO` output.

Two properties of that schema matter below and are recorded here rather than in prose:

- **`output_node: false`** — the node emits a VIDEO but does not save it, so any graph
  needs its own save class. `SaveVideo` already carries a row in `gate_saved_graph.WIDGET_INDEX`.
- **The reference slots are typed `IMAGE` and `VIDEO`** — they are *connection* inputs fed
  by an upstream loader, not literals. That is what makes §3 binding rather than cosmetic.

## 3. FINDING 1 — the A2 arm cannot be submitted: there is no video bridge

**`model.reference_videos.video1` requires a `VIDEO`, and no route exists to put our clip
behind one.**

Measured this session, on the Director's pinned clip:

| probe | result |
|---|---|
| `upload_file` ← `w3-seed1.mp4` (the pinned A2 clip) | **`{"status":"tool_error","error_type":"validation.input"}`** |
| `get_node("LoadVideo")` | one required input `file`, a COMBO whose **option list is empty** — it selects from server-side files, and there are none |
| `search_nodes(output_type="VIDEO")`, 124 matches surveyed | **no URL loader and no path loader in core.** Every VIDEO input in the catalog is fed from another node's VIDEO output |
| `upload_file` documented allowlist | `.jpg/.jpeg/.png/.webp/.gif` only |

**This is not a new discovery; it is a re-measurement of a halt this repo already recorded.**
[E02-report.md §7](E02-report.md) halted at this exact bridge and enumerated the same
alternatives, receiving `validation.input` for an FFV1 `.mkv` and an H.264 `.mp4` and
acceptance for a `.png`. Today's `error_type` on the mp4 is identical to the one recorded
there.

**Discrimination — "the upload path is broken" versus "video is refused".** The error is
`validation.input`, an input-validation class rather than a transport or auth class, and it
matches the documented extension allowlist. `get_node("LoadImage")` returned a populated
option list of several hundred content-addressed uploads, which is the image path's own
receipt. **I did not re-run E02's PNG control upload**, because A1 was halted independently
(§4) and an upload on this surface has no delete; that probe is therefore recorded as NOT
RUN rather than described as passed.

**Disposition.** The dispatch's instruction for this event is explicit — a platform rejection
of the clip slot is a finding, recorded, with that arm halted and no adaptation around it.
A2 is halted. The PNG-batch bridge that rescued E02 does not apply: `reference_videos.video1`
is typed `VIDEO`, not `IMAGE`, so a batch of stills cannot stand in for it the way
`control_video` allowed.

**The premise that was false.** The spec's premise row reads *"Reference-clip format/length
constraints on the video slots — NOT VISIBLE — a platform rejection is a finding, not a
failure."* That row anticipated the slot rejecting a clip's **format or length**. The binding
constraint is one layer earlier and is not about the clip at all: **no clip of any format or
length can reach the slot**, and the repo had already measured that. The spec was written
against a bridge whose absence was on the record.

## 4. FINDING 2 — the A1 references as specced do not exist

The spec's premise row reads: *"A1 references: facet's canonical turnaround renders (consumed
READ-ONLY from facet's tree …) — **MEASURED** (facet canon exists)."*

**Measured this session: facet's tree contains no turnaround of this character.**

| location | contents | bearing on A1 |
|---|---|---|
| `E:\AI\facet\canon\` | `twin_front.png` (RGB, 752×1024, `a6158790…`) and `twin_back.png` (RGB, `a2be5213…`) — **front and back only**, of a **bearded armoured warrior** | not the A1 set: two views, neither three-quarter nor profile — and **not this character** (below) |
| whole `E:\AI\facet` tree | 18 PNGs total; the two above are the only ones named for a view | no turnaround set exists in facet's tree |
| `E:\AI\training\facet_E33\turn_final\` | **8 views, `armfinal_0…7`**, RGBA 352×1024 — the performer mannequin, textured | the only real turnaround of the A2 clip's character; **not in facet's tree**, and defective (below) |
| `E:\AI\training\facet_E33\turn_clay\`, `turn_clay_300k\` | the same 8 views, untextured grey clay | geometry only — not the character's appearance |

**The character mismatch, settled by looking.** I extracted frames 0/30/60/80 from the pinned
A2 clip. It carries a **wooden/clay jointed lay-figure mannequin** dancing in a bar. facet's
`twin_front.png` / `twin_back.png` carry a **bearded warrior in green knit and gold pauldrons
with a greatsword** — a different subject entirely. Pairing A1 against facet's canon pair
would have put a different character in each arm, which makes "identity" meaningless across
the comparison the experiment exists to run.

facet's own `canon/MANIFEST.md` independently bars that pair from this use: it records the
role change to *specification source* and states plainly not to project from them, because
they register against a mesh whose silhouette they under-fill and the body they show is not
the mesh's body.

**The turnaround set that does exist is defective in two ways, both looked at, not inferred.**

1. **Texture-projection holes on exactly the views the spec requires.** The spec asks for
   front, three-quarter and profile at minimum. Inspected at full size: `armfinal_0` (front)
   and `armfinal_4` (back) are largely clean, with small white nicks at the hands.
   `armfinal_1` (three-quarter), `armfinal_2` (profile), `armfinal_3`, `armfinal_5`,
   `armfinal_6` and `armfinal_7` carry **white unpainted patches** across head, neck,
   shoulder, torso, hands, legs and feet; the profile is the worst affected, with blotches
   over the skull, jaw, spine and both hands.
2. **A baked grey void with no real alpha.** All eight are RGBA in mode, and every one has
   **alpha extrema (255, 255)** — fully opaque everywhere. The background is a flat grey
   baked into the RGB. This is the precise failure the Director ruled against on 2026-08-12
   after the E11 probe's grey studio bled through frame 0, and which CLAUDE.md records as the
   standing suspect for E08's washed bands. An RGBA file whose alpha is flat 255 is a baked
   void wearing an alpha channel; it does not satisfy the authored-RGBA law, and there is no
   deliberate RGB-composite choice to record because there is no alpha to composite from.

**Disposition.** A1 is halted. Choosing a substitute reference set, or re-rendering one,
would change what the experiment measures, and that is a spec amendment rather than an
executor's improvisation.

## 5. What exists for the unpark, reported not proposed

Enumerated so the advisor rules on measured options rather than on a search:

- **The performer GLBs are on the rig**: `E:\AI\training\facet_E33\performer_300k.glb`
  (12.75 MB) and `performer_raw.glb` (36.19 MB); `E:\AI\armature-E09\outputs\E09\
  b2-a3-lifted\performer_dance_ema.glb` (13.00 MB) is the one E11 begins from.
- **The renderers exist in-repo**: `tools/stage_render.py` (the control-sequence exporter,
  GLB + shot spec → per-frame channels with a manifest) and `tools/render_performer.py` (a
  shaded pass of the performer). Blender is headless-only here and renders with a true alpha
  channel natively.
- `asset/` in this worktree is empty; the GLBs live outside it.

Whether a re-rendered, real-alpha turnaround is the right A1 reference — and whether A1 alone
is worth 2 of the 4 budgeted submissions once the stills-versus-clip comparison is gone — are
both rulings, not measurements. They are not made here.

## 6. Gate status — what ran and what did not

Written as gates that have not run, never as a plausible verdict beside an identifier.

| gate | status |
|---|---|
| Terms gate | **CLEARED** — the Director's CONDITIONAL, licence map, 2026-08-12 |
| Credit-ceiling halt (>900) | **RAN — did not fire.** 424–844 estimated for four |
| Gate ROUTE | **NOT YET RUN** — no graph was built |
| Gate S (seed registration) | **NOT YET RUN** — no seeds were minted or registered, because no submission was reached |
| Gate L (frame legality) | **NOT YET RUN** |
| Gate PAIR | **n/a on this tier** — hosted partner API, no local diffusion weights load. Recorded as n/a, not skipped silently, per the spec |
| Saved-graph round trip | **NOT YET RUN** |

**The round-trip table was not taught, and that is deliberate.** The dispatch required
teaching `gate_saved_graph.WIDGET_INDEX` the `Wan2ReferenceVideoApi` and save/output classes
with tests riding the same commit. That work is only meaningful attached to a graph that will
run; with both arms halted, adding a table row and a test for a route that submits nothing
would put a green check next to an untravelled path. Two observations from the survey are
recorded so the work is cheap when it is wanted:

- `SaveVideo` **already has a row** — `{"filename_prefix": 0, "format": 1, "codec": 2}`.
- Two andon-shaped gaps would need closing before this route could arm, and neither is a
  table row: **`route_gates.SEED_NODES` knows only `KSampler`/`KSamplerAdvanced`**, so on an
  r2v graph `seeds()` returns empty and `gate_s_registration` reports "0 noise-bearing
  seed(s), all pinned" — a pass having checked nothing, which is the vacuous shape CLAUDE.md
  names. And **Gate L's `wan` rules (dim multiple 16, 4n+1 frames, 81-frame horizon) do not
  describe this tier at all**, which constrains by resolution enum, ratio enum and an integer
  duration in seconds. Both are gates that cannot fail as they stand.

## 7. Uploads, saved cloud workflows, and their deletes

| artifact | delete |
|---|---|
| **none** | no upload was accepted (the only attempt, the A2 mp4, was refused at validation), no workflow was saved to the cloud, and no job was submitted. There is nothing to compensate |

For the record, the standing convention that would have applied: uploads on this API surface
have **no delete endpoint** — they are content-addressed and inert unless a graph names them,
and they persist service-side (E12 w2/w3 §7). Saved cloud workflows delete via the workflows
UI/API, owner the executor session.

Local artifacts created this session: frame extractions from the A2 clip under the session
scratchpad only. Nothing was written into `E:\AI\facet`, `E:\AI\training`, or the E12
worktree.

## 8. What was looked at, at full size

Recorded because nothing here is described unlooked-at:

- A2 clip frames 0, 30, 60, 80 (extracted with the repo's pinned ffmpeg).
- `facet/canon/twin_front.png`, `twin_back.png`.
- `facet_E33/twins/twin_r1_v0.png`, `twin_r2_v0.png`, `twin_r3_v0.png`.
- `facet_E33/turn_final/armfinal_0, _1, _2, _4, _7`; `turn_clay/armclay_2`.

## 9. The negative result, stated plainly

**The composed route could not be probed, and that is a full result rather than a failed
session.** It cost zero credits to establish, and both findings are structural facts about
the route that hold regardless of prompt, seed, or reference choice:

1. **The r2v tier's video slot is unreachable from this pipeline.** The identity-lock surface
   consult #8 measured as "spatially opaque except for the references themselves" is, in
   practice, **stills-only** for us — half its reference contract is behind a bridge that does
   not exist on this API surface.
2. **The character has no clean, real-alpha turnaround.** The 8-view set that exists is holed
   on the non-front views and carries the baked grey void the Director ruled out.

Because A2 is unreachable, **the one-variable comparison the spec was built on — stills versus
clip, everything else pinned — cannot be run on this tier at all.** That is not a result A1
alone can supply, and it is the reason this halts rather than proceeding with half the design.

## 10. The meters

| | |
|---|---|
| `estimate_credits` | **106–211 per generation** (no `0` meter artifact on this path) |
| generations submitted | **0 of 4** |
| credits spent | **0** |
| uploads accepted | **0** (one attempt, refused at validation) |
| suite (this worktree) | **970 passed, 48 skipped** |

**One discrepancy in the suite, recorded rather than smoothed.** The handoff's rig run
reported 1005 passed / 13 skipped; this worktree reports 970 / 48. **The collected total is
identical (1018)** — 35 tests that execute on `main` skip here. That is the shape of
rig-local asset gating (the spec's own A1 premise row notes these skip visibly), but the
cause was not chased down, because no code changed in this branch and nothing in this run
depended on those 35. Flagged for the advisor rather than asserted as benign.

## 11. Owed to the Director and the advisor

- Whether E13 re-scopes to a stills-only probe (2 submissions), waits for a real-alpha
  turnaround re-render, or is withdrawn from this tier. **The spend decision is his**, and it
  is a different decision from the one taken at dispatch.
- The spec's A1 and A2 premise rows need correcting in place with the measurements above,
  per the advisor's rule 2 — the corrections are more useful than the original rows.
- If the route is ever armed, the two vacuous-gate gaps in §6 close first, with tests, before
  a submission — not as a table row afterwards.
