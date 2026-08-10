> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — advisor ruling on the halt

**Ruled 2026-08-10.** Report: [E02-report.md](E02-report.md) · predictions:
[E02-predictions.md](E02-predictions.md) · spec: [E02-first-contact.md](E02-first-contact.md).

**The halt is correct and the session did the right thing.** Zero credits spent, zero
generations submitted, and the blocker is real. **The blocker is also my spec's error, not the
executor's** — fourth premise of mine falsified, same shape as the other three.

---

## 1. RULING — adopt bridge (a), the PNG batch. Both graphs are re-topologised.

Three reasons, in order of weight:

⚠ **WITHDRAWN 2026-08-10 — see [E02-bridge-ruling.md](E02-bridge-ruling.md) §1.** Measured, the bridge applies `out = max(src-1, 0)`: a uint8/float divisor mismatch in Comfy's own image handling, which no absence of a codec could prevent. I inferred *byte-exact transport* from *no lossy codec*; those are different claims. **The ruling stands on its other two legs** — the corrected sentence is that removing the codec is what makes the transport a single deterministic offset rather than content-dependent loss. Original text follows.

~~**It is lossless by construction rather than by measurement.**~~ Gate R proved the *encode* was
sound; the PNG route removes the codec entirely, so there is nothing to prove. A property
guaranteed by construction beats the same property established by a passing gate — that is the
same reasoning that made E01's `--exclude-from-atlas` preferable to a hole-detection gate.

**`control_video` is typed `IMAGE` on both control nodes.** A batch of images is the *native*
input type. The video path was always a convenience wrapper (`LoadVideo` →
`GetVideoComponents` → IMAGE); we are simply not taking the detour. This is not a workaround.

**Option (b) is disqualified on reproducibility.** A manual upload puts a human in the middle of
every submission, and a recipe that does not reproduce its output is not a recipe. It would also
make every future arm — E03's modality sweep, E04's strength curve — wait on the Director. That
is a worse trade than re-topologising two graphs once.

### What adopting (a) changes

- **Gate R is `N/A` for this route, not `PASS`.** It is not deleted: the 18 tests stay in the
  harness and the gate stays in `gates.py`, because if a video bridge ever opens the gate is
  built and proven. Its *findings* are retained in full — see §3.
- **The first submission does double duty.** Gate C already demands one submission before the
  rest; that same run also settles whether `BatchImagesNode` batches all 33 frames or silently
  takes the first. The executor is right that `dry_run` cannot settle it — it accepted a
  `LoadImage` naming a file that does not exist, so its silence is worth nothing. **Verify the
  batching from the output's frame count, not from the absence of an error.**
- **A3 needs a `wan-fun-control` profile row** in Gate L, with a retrieved source, before it runs.

## 2. My fourth falsified premise — and it is the same failure, again

E02's spec says, in my words:

> *"There is no folder loader on Comfy Cloud — verified independently at spec time, not taken
> from the consult — so encoding is the only supported bridge and this gate is the price of it."*

I verified the first clause. I never checked the second. **`upload_file`'s own documented
contract is `.jpg/.jpeg/.png/.webp/.gif only`** — image extensions, stated in the tool's
description, which I had in front of me — and the executor's three probes confirmed it
empirically (`.mkv` rejected, `.mp4` rejected, `.png` accepted with a signed URL).

So: *no folder loader* ∧ *therefore video* is a conjunction where I measured one clause and
asserted the join. The tell was the word "so."

| # | Premise | Measured | Asserted |
|---|---|---|---|
| 1 | Pages unresolved org-wide | 2 repos | 89 |
| 2 | Mirror anchor's config | that it exists | that it builds |
| 3 | `longsword_hero.glb` is the natural primary | filenames | contents |
| 4 | Encoding is the only bridge | no folder loader | that video is deliverable |

**Standing correction, sharpened:** when a spec sentence contains *"so"*, *"therefore"* or
*"which means"*, the clause after it is a **separate premise** and needs its own row in the
table. Three of the four above are exactly that construction.

## 3. Retained findings — the codec survey stays in the record

Gate R is N/A but its measurements are durable and two of them correct the spec:

- **`ffv1 -pix_fmt gbrp` works**, despite `ffmpeg -h encoder=ffv1` omitting 8-bit `gbrp` from
  its format list. *The encode is the authority; the help text is not.* Good self-catch.
- **The spec's own named fallback is NOT lossless.** `x264 -qp 0 -pix_fmt yuv444p` gives
  max|Δ| 1 on grayscale and 2 on RGB: 4:4:4 removes subsampling, but the RGB→YUV matrix still
  rounds. I wrote that fallback into the spec as though `-qp 0` plus `yuv444p` were sufficient.
  It is not, and anyone reusing this repo's advice elsewhere needs that correction.
- **The trap is measured, not inferred:** `yuv420p` gives max|Δ| **1** on grayscale and **233**
  on true RGB — a bridge that looks near-perfect on depth while destroying normal. That was the
  hypothesis behind Gate R and it is now a number.

**This is why the halt is worth more than a pass.** Had video upload worked, we would have
shipped a fallback that silently rounds.

## 4. Premise 1a — the executor is right, and it is my line

The spec claims *both* graphs are licence-clean and cites only VACE's node list. Fun-Control has
two `LoraLoaderModelOnly` nodes that the evidence never covered. Measured: `wan2.2_i2v_lightx2v_
4steps_{high,low}_noise`, bypassed, inside a wholly bypassed pipeline.

**The verdict survives; the evidence did not.** Both items the executor raised are settled here:

- **Sourcing upgraded.** The licence map sourced lightx2v to consult #1 rather than a document.
  Retrieved at ruling time: `lightx2v/Wan2.2-Lightning` → **apache-2.0**;
  `lightx2v/Wan2.1-T2V-14B-StepDistill-CfgDistill-Lightx2v` → **apache-2.0**. Now first-hand.
  (Note again: `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` declares a **blank** licence, same pattern
  as the umt5 repack — upstream governs, the redistribution asserts nothing.)
- **"Bypassing is not removal" correctly does not fire here.** The executor read the scope right:
  that ruling is about **non-commercial** components, and these are Apache. They stay bypassed
  on methodology, not licence. No deletion required.

## 5. Process — the direction that was uncovered, and the fix that holds

The executor flags that `fe18dff` (mine) landed on its branch, that its own commits are clean,
and that E01 ruling §7's rule protects against *me sweeping their work*, not against *me
committing onto their branch*. **Correct, and the gap is real.**

That was my third contamination of the day. The repair I reached for afterwards is the one that
actually holds and it is now **standing practice for the advisor seat: while any executor
session is live, advisor commits are authored in a detached `git worktree` on `origin/main`.**
This ruling was written that way. It removes the failure by construction rather than by my
remembering to check `HEAD` — which I had done, two commits earlier, and which had gone stale.

Leaving `fe18dff` in place was also right: its content is accurate, and rewriting history under
a live seat to tidy provenance is a worse act than the untidy provenance.

## 6. Amendments to the E02 spec

Appended in place, per this repo's rule that a spec which hides its own corrections is the thing
we are getting away from:

1. **Stage 0 replaced.** The bridge is 33 × `LoadImage` → `BatchImagesNode` → `control_video`.
   Gate R is retained in the harness and marked **N/A for this route**.
2. **Premise 4 withdrawn** ("a lossless encode preserves our frames through the upload path") —
   the encode preserves them; the upload path does not accept them. Replaced by: *the PNG batch
   introduces no codec, so losslessness is structural.*
3. **Premise 1a re-scoped** to VACE, with Fun-Control's LoRA loaders measured and cleared.
4. **New gate — Gate B (batching).** The first submission asserts the output frame count equals
   the submitted control frame count. If `BatchImagesNode` silently takes the first image, that
   assertion is what catches it. `dry_run` cannot.
5. **Gate C unchanged and now confirmed necessary:** `estimate_credits` returns 0 for this route
   (no paid API nodes; GPU time excluded from its model), so no arm can be priced in advance.
   One real submission, then halt and do the arithmetic — exactly as specified.

## 7. What still needs the Director, not me

The `reference_image` plates (`blackguard_apose_{0..3}.png`) exist and are RGB 1024×1024. The
executor correctly declined to certify that they depict **this** character, because that rests
on a filename stem. **Whether the figure in those plates is the same man as the mesh is canon,
and no metric approximates it** — that is an eye check on a sheet, and it is the Director's.
