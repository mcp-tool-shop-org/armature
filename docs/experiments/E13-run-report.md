# E13 (re-armed) — the run report

**Executor session, 2026-08-13.** Worktree `E:\AI\armature-E13`, branch `E13-run`.
Spec: [E13-composed-route-probe.md](E13-composed-route-probe.md) with its RE-ARM
amendment. Predictions: [E13-rerun-predictions.md](E13-rerun-predictions.md), committed
at `d46d3fe` **before the probe was built and before any reference was composited**.

**This report is appended BESIDE the halt record, not over it.**
[E13-report.md](E13-report.md) and [E13-predictions.md](E13-predictions.md) are the
halt-era session's and are untouched. Nothing in either file is rewritten, rescored, or
softened by anything here.

**Nothing in this report is a judgement of output quality.** The Director's eye is the
verdict; every number here is a diagnostic and gates nothing.

---

## 0. Dispatch checks, in the order the dispatch ordered them

| check | result |
|---|---|
| `git merge origin/main` in the worktree | **done** — 23 files, docs-only as expected (translations, SECURITY/SCORECARD/SHIP_GATE, the S03 dispatch + ruling, the E13 halt ruling, licence-map and publishing edits) |
| the branched spec contains the RE-ARM amendment | **yes** — `grep -c "RE-ARM"` → 1 |
| binding documents read from `main`, not the worktree | CLAUDE.md blob `b6b9c61d…` is byte-identical between `main` and the merged worktree (the whole-file `diff` is CRLF in the checkout against LF in the object store, the same artefact the halt report recorded). Read in full: CLAUDE.md · the E13 spec with all four amendments · [E13-halt-ruling.md](E13-halt-ruling.md) · [S03-ruling.md](../dispatches/S03-ruling.md) · the S03 report from `S03-run` · E12 w2/w3 §7 |
| VRAM watchdog | **alive** at session start (heartbeat fresh, 6951/32607 MiB, 24249 below the 31200 ceiling). No GPU work ran this session — no Blender, no local weights; compositing and measurement are CPU |
| `E:\AI\armature-S03`, `E:\AI\armature-E12`, `E:\AI\training`, `E:\AI\facet` | **read only.** Nothing written to any of them |

## 1. The fresh credit re-estimate — the ordered first act

Run before anything was built and before any submission, as the dispatch requires.

| | |
|---|---|
| instrument | `estimate_credits`, template `api_wan2_7_r2v` |
| result | **106–211 credits per generation** (1 paid API node: `Wan2ReferenceVideoApi`) |
| four submissions | **424–844** |
| two submissions (the stills-only branch) | **212–422** |
| the 900-credit halt | **RAN — did not fire** under either branch |
| meter artifact | **none on this path.** The dispatch pre-ruled a `0` reading a meter artifact; this path returned the bracket, as it did for the halt-era session. The four-submission ceiling binds regardless |

Bounded the same way the halt report bounded it: this is a template-resolved figure, not an
override-exact one. The spec's pins (720P · 16:9 · duration 5) include the node's own
default duration of 5, and the per-generation bracket has not moved from the bundled
catalog's 2026-08-12 figure.

## 2. The node contract, re-measured

`Wan2ReferenceVideoApi` re-measured with `get_node`, 2026-08-13, because it is the contract
any graph is built against and a premise of this seat's own dispatch. **Byte-consistent
with the spec's premise row and with the halt report's re-measurement:** `model.prompt`,
`model.negative_prompt`, `model.resolution` ∈ {720P, 1080P}, `model.ratio` ∈ {16:9, 9:16,
1:1, 4:3, 3:4}, `model.duration` INT default 5 (min 2, max 10), `model.reference_images.
image1…image5`, `model.reference_videos.video1…video3`, `seed` INT (max 2147483647),
`watermark` BOOLEAN default false, one `VIDEO` output, `api_node: true`,
`output_node: false`.

**One measurement artefact, recorded because it nearly became a finding.** `get_node` on
five classes at once returned `LoadImage`'s `image` COMBO with an **empty** option list;
`get_node` on `LoadImage` alone returned a populated list of several hundred
content-addressed uploads. The empty list is a property of the multi-name query, not
evidence that uploads were purged. Recorded so the next seat does not read a batched query
as an outage.

---

## 3. Stage 0 — the cascade-batch probe

**Zero partner credits.** The RE-ARM amendment's deterministic branch selector: can 81
frames reach `CreateVideo` if no single `BatchImagesNode` is loaded above the cap S03's
failure implies?

### The instrument

`tools/build_cascade_payload.py` (`E13.1`) and the cascade half of
`tools/armature_core/assembly.py`, merged from `S03-run` rather than re-written — see §8.

    81 x LoadImage -> 3 x BatchImagesNode(27) -> BatchImagesNode(3)
                   -> CreateVideo(fps=16) -> SaveVideo

87 nodes, four classes, all `api_node: false`. The graph is built in-repo; the served
template is a reference, never a route.

**The cap is treated as the inference it is.** S03's error named `images.image50` as
unexpected and 8 slots executed, which reads as `image0…image49`. No submission was made
at 49, 50 or 51, so the boundary is **not located**. The cascade therefore builds to 27
and the gate's ceiling sits at 27, not at 50: a gate placed on an inferred number inherits
that number's uncertainty. The payload record carries the cap as `INFERRED … not a
measurement`, and a test pins that wording.

### Gates, before submission

| gate | status |
|---|---|
| **ASSEMBLY (paid nodes)** | **PASSED** — 87 nodes across 4 classes, all named by the allowlist, none reading as a partner class. The allowlist is the binding clause; the name pattern is a second opinion on the allowlist, and its recall is unknown and stated as such |
| **CASCADE (slot ceiling)** | **PASSED** — 4 batch nodes, largest carries 27 slots, ceiling 27. New this run; the andon points UPWARD, which is the direction the invariant does not bound |
| **CASCADE (topology)** | **PASSED** — 81 distinct `LoadImage` nodes across 3 groups in frame order, dotted slot keys, groups wired to the final batch in order, every link resolved |
| **ROUTE** | **PASSED** — 0 components, 0 seeds, 0 latents; frame legality decided on the supplied (1024, 576, 81) |
| **ROUTE / licence clause** | ran on an empty set: the graph loads **no weights**, so none can be banned. Reported for what it examined, not as a green tick |
| **ROUTE / Gate PAIR** | ran on an empty set: **no conditioning node**, so none can be unpaired |
| **Gate S (seed registration)** | **n/a — not claimed as passed.** No noise-bearing node exists in this graph, so `require_pinned_seeds=False` was passed deliberately. A green "0 seeds, all pinned" here is the vacuous shape the halt-era executor was ruled right to refuse |
| **Gate L (frame legality)** | ran on a **supplied** frame, not a graph-read one — this graph pins no latent. It decides 1024×576×81 legal for the `wan` rules; it does not check the graph |
| **Credit-ceiling halt (> 0 partner credits)** | **RAN — did not fire.** `estimate_credits` on this exact 87-node graph: *"0 credits - no paid API nodes found in this workflow"* |
| **Round-trip table** | **no new class to teach.** The cascade re-uses the five classes S03 already taught (`LoadImage`, `BatchImagesNode`, `CreateVideo`, `SaveVideo` — `BatchImagesNode` is S03's `{}` row). A test asserts every class in the built graph has a row rather than adding a row for its own sake; the table is looked up with `is None`, so an absent class halts |

### Pre-flight, recorded as a diagnostic and not as a gate

`dry_run` returned `{"status":"validated","warnings":[]}` — **zero warnings, exactly as
S03's 81-slot flat graph did before dying at execution.** It is recorded here for one
narrow reason: it is the same signal that preceded the failure this probe exists to route
around, and the standing law that a `dry_run` PASS does not prove link sanity is what
makes it a diagnostic rather than evidence.

One weak reading rides along, marked weak: zero warnings means no COMBO advisory fired on
any of the 81 upload names, which is consistent with S03's uploads still being resolvable.
Pre-flight validates against a bundled catalog that can lag the cloud, so this is
consistent-with, not established-by.

### The submission

`prompt_id` **`c3547512-a5e3-4953-9875-3313a7bce0ed`** — status `completed`, zero
warnings, zero partner credits. One output: `6a143745b3…mp4`, downloaded to
`outputs/E13/route/cascade81.mp4`, 1,118,346 bytes, sha256
`a65f0bf31ea062b773b54a4a1d32213ab70d78ca92f4dc89cb251a91134a5f16`.

### The decode comparison

`tools/measure_cascade_clip.py` (`E13.1`) against the same 81 source frames S03 pinned
(`E:\AI\armature-E12\outputs\E12\probe\w3-seed1\lossless`, read-only), with the repo's
pinned ffmpeg. Full record: `outputs/E13/route/cascade_decode_compare.json`.

| | measured |
|---|---|
| stream | **h264 (High), yuv420p (progressive), 1024×576, 1732 kb/s, 16 fps** |
| decoded frame count | **81** for 81 submitted |
| frames bit-exact against source | **0 of 81** |
| mean absolute error per frame | **2.1795 … 2.4190**; largest single-pixel delta 83 |
| gradient split, frame 0 | top-decile gradient **4.05** against flat-half **1.76** |
| gradient split, frame 40 | top-decile gradient **4.23** against flat-half **1.67** |
| frame order | **81 of 81 on the diagonal**, 0 displaced; min margin 4.599, median 6.619 |

**One honest difference from S03, not smoothed.** S03 reported 12.19 against 5.28 on
frame 0 of its 8-frame probe; this run reads 4.05 against 1.76 on the same source frame.
The *ratio* is nearly identical (2.31 against 2.30), the absolute values are not. The two
numbers come from **different instruments** — S03's was computed inline, this one by
`clipcompare.gradient_split` — and no attempt was made to reconcile them by tuning either.
Recorded as a discrepancy between instruments, not as a reproduction and not as a
contradiction. The median-formula trap S03 recorded is the standing reason a number that
nearly matches is not treated as a match.

### Predictions, scored

| id | prediction | outcome |
|---|---|---|
| Q1 | the cascade executes | **HELD** — completed, no execution error |
| Q2 | a batch node concatenates an already-batched input | **HELD** — the clause with no prior measurement |
| Q3 | 81 decoded frames | **HELD** — exactly 81 |
| Q4 | 16 fps | **HELD** — 16 fps read off the stream |
| Q5 | frame order preserved | **HELD** — 81/81 on the diagonal |
| Q6 | not bit-exact, error structured at edges | **HELD** — 0 of 81 identical; 4.05 vs 1.76 |
| Q7 | `estimate_credits` reads 0 | **HELD** — "no paid API nodes found" |

### THE BRANCH, SELECTED AND RECORDED BEFORE ANY SUBMISSION

**The probe passed.** Per the RE-ARM amendment's first branch, **E13 runs two arms × two
seeds = 4 submissions**, with A2 = the constructed VIDEO into
`model.reference_videos.video1`. Credit bracket **424–844**, halt above 900 unchanged.
The stills-only branch (2 submissions, 212–422) is **not** taken, and the ambiguous-error
halt did not arise: every clause of the probe returned a clean, classifiable result.

**What the probe does NOT settle.** Whether `reference_videos.video1` accepts a VIDEO
constructed this way **at runtime** remains the link S03 left ASSUMED. It is typed-
compatible and has never been executed. It is prediction S1, and only the first A2
submission can answer it.
