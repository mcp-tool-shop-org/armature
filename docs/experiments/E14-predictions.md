# E14 — the executor's predictions, committed BEFORE the first submission

**Executor seat, 2026-08-13, branch `E14-run`.** Written and committed **before any E14
graph was built or submitted**, and before any E14 artifact exists.

**Blindness disclosed.** These are blind in the only sense available: no E14 output exists
to have seen. They are **not independent** of the advisor's H-E14a–d — I read the spec
first, as the dispatch requires. Where I agree I say so; where I disagree with the
advisor's blind prediction I say that too, because a prediction that only ever echoes the
spec cannot be scored against it.

The Director judges. Nothing below is a quality claim, and no word here rules on an output.

## What the arms are

| arm | LoRA file(s), verbatim as served | attachment |
|---|---|---|
| **T** | `wan22-14b-t2v-technically_color.safetensors` | the SAME single file on BOTH expert lines |
| **S** | `WAN2.2-HighNoise_SmartphoneSnapshotPhotoReality_v3_by-AI_Characters.safetensors.safetensors` | high-noise expert |
| | `WAN2.2-LowNoise_SmartphoneSnapshotPhotoReality_v3_by-AI_Characters.safetensors` | low-noise expert |

The HIGH file's double `.safetensors` and the LOW file's single one are **both verbatim**,
re-measured this session via `search_models` (2 hits, exact). The asymmetry is real and is
not a typo in this document.

## The predictions

| id | clause | my prediction | confidence |
|---|---|---|---|
| **P1** | arm T produces a look transform legible to the Director | **YES, strongly.** The terracotta reads more saturated and pushed toward orange-red; the bar's warm key separates harder from its shadows; blacks deepen | high |
| **P2** | arm S produces a look transform legible to the Director | **YES, and I predict it is NOT the subtler of the two** | medium |
| **P3** | the Static camera hold survives | **YES on both.** The camera rides a separate conditioning channel (`WanCameraEmbedding` → `WanCameraImageToVideo`); a LoRA patches denoiser weights. Different channels | high |
| **P4** | the transfer premise binds (visible effect on Fun-Camera derivative weights) | **YES on both.** Fun-Camera is a fine-tune of the same Wan 2.2 14B architecture, so rank-decomposed deltas still land on tensors that exist | T ~75%, S ~65% |
| **P5** | arm T shows a tier-mismatch artifact | **UNRESOLVED, named in advance.** T's origin is a HN/LN pair; the Cloud serves one file of unknown tier, loaded on BOTH experts. One of T's two attachments is necessarily tier-mismatched | — |

## Where I disagree with the advisor, and why

**H-E14a predicts S is "subtle — candid-phone realism is closer to the baseline's look
than Technicolor is." I predict the opposite ordering on the SUBJECT**, and the same
ordering on the world.

The reasoning is the subject, not the world. The baseline's positive prompt asks for *a
slender jointed clay mannequin… unglazed terracotta, matte sculpted clay*. A
photo-realism LoRA is trained to push toward photographic skin, real lens behavior and
camera-sensor texture. That is not a neutral look layer sitting beside the prompt — it
pulls on exactly the property the prompt is holding. Technicolor, by contrast, is a
**grading** transform: it re-colors whatever is there without arguing about what the
surface is made of.

So my ordering:

- **on the world** — T's transform is the more legible of the two (agreeing with H-E14a)
- **on the subject** — **S applies the greater identity pressure**, and if either arm
  dissolves the clay, it is S. A grading LoRA re-colors clay; a photoreality LoRA has a
  documented reason to want it to be skin

This makes H-E14b's "the crowd re-styles before the subject does" the clause I am least
confident in **for S specifically**. For T I expect it to hold as written.

## The null, owned in advance

If either arm returns no visible change, that is **the tier-transfer finding** — the
central measured question resolving negative — and it is a full result, not a defect. It
would say a T2V-trained style LoRA does not bind usefully on Fun-Camera derivative
weights, which prices the whole lever honestly and is worth knowing before the studio
trains its own. I am not tuning toward a visible effect, and there are no re-runs to tune
with: the ceiling is two generations.

## What would make me wrong in an uninteresting way

Recorded so it is not mistaken for a finding: a **crossed pair on S** (HIGH file on the
low-noise expert or LOW on high) would be a wiring error of the E11-w2 class, not a
result about LoRA transfer. The ledger record makes the attachment visible per arm
precisely so this is separable from a real null.
