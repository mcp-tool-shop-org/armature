# E02 — ruling on the bridge findings and the second halt

**Ruled 2026-08-10.** Report: [E02-report.md](E02-report.md) part 2. Supersedes one line of
[E02-halt-ruling.md](E02-halt-ruling.md) §1, corrected in place below.

**The bridge choice stands. Its stated rationale was one-third wrong and is corrected here.**
Three answers below; one of them costs nothing and one is not mine to give.

---

## 1. CORRECTION — "lossless by construction" is withdrawn as written

My halt ruling gave three reasons for bridge (a), and led with:

> *"It is lossless by construction rather than by measurement. Gate R proved the encode was
> sound; the PNG route removes the codec entirely, so there is nothing to prove."*

**The first sentence is false and the executor measured it false.** 33 of 33 probe frames differ
from source at max |Δ| 1, deltas strictly in {−1, 0}, never +1: background (0) 100.000%
unchanged, subject (>0) 100.000% exactly one lower. The relation is
`out = max(src − 1, 0)`, a pure function of source value.

**The precise error is a conflation, and it is worth naming because it is reusable.** I inferred
*byte-exact transport* from *no lossy codec in the path*. Those are different claims. The path
genuinely has no codec — that part holds. It also has a uint8↔float divisor mismatch somewhere
in Comfy's own image handling, which no absence of a codec could have prevented.

**Verified independently at ruling time**, because I have asserted unchecked arithmetic before:
`max(v−1,0) ≡ floor(255·v/256)` for all 256 values, exactly. And the executor's own falsified
hypothesis reproduces too — float32 `v/255×255` recovers all 256 values, so truncation there was
correctly killed. Their characterisation is right in both directions.

### Does the ruling survive the correction?

**Yes, and the corrected rationale is stronger than the original.** The three legs were:

| leg | status |
|---|---|
| lossless by construction | **FALSIFIED** |
| `control_video` is typed `IMAGE`, so a batch is the native input | holds |
| (b) manual upload breaks reproducibility | holds |

And the falsified leg does not favour (b) either: the −1 lives in Comfy's image handling, not in
a codec, so a `LoadVideo → GetVideoComponents → IMAGE` path would very likely cross the **same**
conversion **plus** a codec. Bridge (a) remains the better of the two on the surviving legs.

**The honest replacement sentence:** *the PNG route removes the codec, which is what makes the
transport's behaviour a single deterministic offset rather than content-dependent loss.*

## 2. RULING — accept the −1. Do NOT spend a synthetic-ramp run.

The executor correctly identified that it cannot separate *ingest* (the sampler received
`src−1`) from *save* (the sampler received `src`; the probe shifted), because the probe is the
only window onto the batch and cannot observe itself. That is a real epistemic limit, honestly
stated.

**It does not need separating, because the answer changes no decision.** The offset is uniform
and deterministic, so every gradient and every boundary survives exactly; only absolute level
moves by 1/255 = 0.4%. Whether the sampler saw that 0.4% or not, no arm of E02 reads absolute
level — A1a/A1b compare polarities, A2 compares presence against absence, A3 compares
implementations. A constant offset is common-mode to all of them.

⚠ **One correction to my own first instinct, caught before it went in:** I nearly wrote that
per-frame min-max normalisation *removes* the offset. It does not. Our normalisation happens
**upstream in the exporter**, before upload; the −1 lands **downstream**. So it arrives at the
model as a genuine 0.4% level shift, not something already cancelled. The conclusion survives —
common-mode, structure-preserving — but by a different argument than the one I first reached for.

### The one place it is not cosmetic — measured, free, and small

A source pixel of value **1** becomes **0**, which is background's value. In a near-bright depth
map those are the *farthest* subject surfaces, so a hairline of the back edge acquires
background depth while the mask still marks it as subject. Counted across all 33 frames:

| channel | non-zero px | at value 1 | share of subject |
|---|---|---|---|
| `depth_pershot` | 960,148 | **37** | 0.0039% |
| `depth_perframe` | 960,041 | **180** | 0.0187% |
| `edge` | 270,095 | **0** | 0 |
| `mask` | 960,183 | **0** | 0 |

**37 and 180 pixels across 33 frames.** The mask and edge channels are untouched because neither
carries a value of 1 anywhere. This is recorded so nobody rediscovers it as a mystery, and it is
far too small to act on.

**Pre-registered:** if a later experiment reads **absolute** depth level — a metric depth
consumer, or an arm that compares brightness across runs rather than structure within one — the
ramp run becomes necessary and this ruling does not cover it.

## 3. Gate C — the observation is the Director's, not the executor's

The executor did the right thing three times over: it refused to invent a figure, refused to
estimate from an adjacent day (a per-day total with an unknown run count is not this run's
cost), and confirmed the run really did hold a GPU for ~5 minutes so the absence is a reporting
lag rather than a free run.

**Ruling: Gate C stays HELD, and it is closed by an observation the executor cannot make.**
`estimate_credits` returns 0 because Wan's entire cost is GPU time, which that estimator
excludes by design; the invoice surface lags and carries no 2026-08-10 bucket; and no
cost, credit or duration field exists on the job record. There is no programmatic surface.

**So it routes to the Director:** one look at Comfy Cloud's billing page for job
`382dbb1f-57e6-47b2-a80b-2e675b35db11` yields a real number, and the 12-generation projection
follows from it in one multiplication. That is a thirty-second human action producing a measured
value, which beats any amount of cleverness on our side.

**Until that number exists, no further generation runs.** The gate is doing exactly what it was
written to do — the ceiling exists so a run cannot become eleven runs before anyone prices one.

## 4. Gate B — the executor was right and my gate could not fire

I specified: *"the first submission asserts the OUTPUT frame count equals the submitted control
frame count."* The executor traced the mechanism before implementing and found that
`WanVaceToVideo` truncates or pads `control_video` to `length` — so a 1-image batch and a
33-image batch **both** emit 33 output frames. **The quantity does not move when the defect is
present.**

That is *a check that cannot fail is not a check*, applied to a gate I wrote one ruling earlier,
and found by reading the mechanism rather than by running it. The replacement — saving off
`BatchImagesNode` itself, binding both directions with `!=` rather than `<` — keeps the
principle I actually meant (verify from an output, never from the absence of an error) on a
quantity that can move, inside the single submission already authorised. **Accepted as
specified-by-the-executor.**

`test_the_rejected_check_could_not_fire` pinning the reasoning is the right instinct: it stops
the weaker check returning as an apparent simplification.

## 5. `dry_run`'s third and hardest failure

Not a missing file this time. A **structurally invalid graph** — `BatchImagesNode` requires
dotted auto-grow keys (`images.image0`…), and the bare-list form returned
`{"status":"validated","warnings":[]}` before being rejected at prompt validation.

The repo's standing line was *"a `dry_run` PASS does not prove link sanity."* That is now too
weak. **Amended: a `dry_run` PASS proves nothing about a graph's runnability. It is not evidence
and may not be cited as any.** The only cost of learning it was zero — the rejection happened
before the worker ran — which is the second time today a halt has been cheaper than a pass.

## 6. Accepted without change

- **The `wan-fun-control` profile row, with provenance stated as DERIVED.** Both graphs load the
  same `wan_2.1_vae.safetensors` (measured), and 4n+1 / divisible-by-16 are properties of that
  VAE — so the constraint transfers **on a shared component, not on a family name**. That
  distinction is exactly right, and asserting the source string in a test so it keeps saying
  "derived" is better discipline than I asked for.
- **Content-addressed upload names**, established by re-uploading frame 00000 and getting
  `2d276aa6…` back. That makes uploads idempotent, made the nine lost URLs cost nothing, and the
  33-distinct-names check was the right paranoia — identical frames would have silently merged
  and shrunk the batch.
- **Gate R retained and marked N/A**, 18 tests kept.

## 7. What the next session does

1. **Wait on Gate C** — the Director's billing observation. No generation until it lands.
2. Then the arithmetic against the 12-generation ceiling, and if it clears, **A0's three
   identical submissions** — the noise floor, which everything else is read against.
3. The −1 is settled; do not re-open it without an absolute-level consumer.
