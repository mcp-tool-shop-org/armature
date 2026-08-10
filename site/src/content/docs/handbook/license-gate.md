---
title: The license gate
description: No non-commercially licensed model, weight, adapter, preprocessor or dependency — including in experiments — and the two traps that stance caught on day one.
sidebar:
  order: 4
---

**No non-commercially licensed model, weight, LoRA, preprocessor or code dependency enters this
pipeline anywhere — including in experiments.** CC-BY-NC, research-only and academic-only are
banned outright.

The reason is not principle, it is waste. **An experiment concluded on a banned model is a
conclusion that has to be thrown away**, so it never starts. A licence check is minutes; a
discarded arc is a session.

This page summarizes the stance and the findings. The canonical, dated map is
[docs/license-map.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/license-map.md)
in the repo — every row there carries the URL of the actual licence document, the operative
clause, and the date it was fetched.

## How a dependency enters

1. Fetch the **actual licence document** — model card, `LICENSE` file, or official terms page.
   Not a blog summary, not a README badge.
2. Record name, version, licence name, URL, a short quote of the operative clause, and the fetch
   date.
3. Rule `COMMERCIAL: YES / NO / CONDITIONAL(<condition>)`.
4. `NO` → the dependency does not enter, and the spec names what replaces it.
5. `CONDITIONAL` → **a Director decision**, surfaced with its condition stated. Never a quiet yes.
6. `UNVERIFIED` → **treated as NO** until retrieved.

The check is recorded in the spec that introduces the dependency, and the row lands in the map.
**Entries older than 90 days are advisory until re-fetched** — licences in this space change.

And the rule that catches the most people: **the same family can split across variants.** Check
the exact variant and version you are about to run, not the family name.

## Two traps this caught immediately

Both are the kind of thing the gate exists for, and both are worth knowing whether or not you
ever touch armature.

**1. OpenPose is non-commercial.** The most widely used pose extractor in the entire ControlNet
ecosystem is under a CMU academic licence permitting use *for your own noncommercial internal
research purposes*. It is banned here. DWPose and RTMPose are Apache 2.0 and replace it.

**2. The Small/Large split is real.** Depth Anything V2 **Small is Apache 2.0**; Depth Anything
V2 **Large is CC-BY-NC-4.0**. Same family, same page structure, different licence. Depth Anything
V3's *code* is Apache while its **weights** are CC-BY-NC across the board — and the weights are
what a pipeline actually runs.

## The architectural consequence, which is the interesting part

armature renders depth from Blender's own Z-buffer, and can draw a skeleton from bone transforms
that are already known. Where it does that, **no depth or pose *estimator* is in the pipeline at
all.**

The entire banned preprocessor tier is sidestepped **by construction, not by substitution.** That
is a genuine advantage of CG-sourced control over video-extracted control, it was found by doing
the licence work rather than by design taste, and the first exporter is built to keep it.

One open question this raises, flagged for a later ruling: matching a pose ControlNet's expected
*drawing convention* is a format question, but the **conditioning model's own weights** carry
their own licence. Any pose or depth ControlNet checkpoint gets its own row before it runs.

## What the map says today

Fetched 2026-08-10.

**Generation models.** **Wan 2.x is the default route** — the only family that is
unconditionally Apache 2.0 across base, VACE and Fun-Control, and it explicitly disclaims rights
in generated outputs. Mochi 1 preview is Apache 2.0. LTX-Video 0.9.x is open-weights with no
revenue cap found.

**Conditional, and therefore a Director decision rather than a default.** LTX-2 requires a paid
licence above $10M annual revenue. HunyuanVideo's community licence **excludes the European
Union, the United Kingdom and South Korea by territory**, which makes it unusable for a game sold
internationally. CogVideoX-5b requires registration and caps traffic at one million visits per
month.

**Preprocessors, if one is ever needed.** DWPose, RTMPose/MMPose, SAM, SAM 2 and Depth Anything
V2 Small are Apache 2.0; BiRefNet is MIT. OpenPose and Depth Anything V2 Large / V3 weights are
banned. `rembg` is conditional — MIT covers the code, and its bundled weights carry separate
licences that have not been fetched.

**Services.** Comfy Cloud's terms state that the customer retains all right, title and interest
in outputs, and that inputs and outputs will not be used to train generative AI.

## Five items are unverified, and that is recorded rather than assumed

Each blocks the thing that depends on it:

| Item | Why unverified |
|---|---|
| Blender's GPL / output statement | blender.org returned HTTP 403 to the fetcher |
| Kling terms | HTTP 446, Cloudflare block, on two URLs |
| MiniMax terms | JavaScript-rendered page, no text returned |
| ByteDance / Seedance output ownership | the master terms contain no AI-output clause; the service-specific agreement was not located |
| `rembg` bundled weights (u2net / isnet) | individual model licences not fetched |

Blender's is the least consequential in practice — GPL covering software rather than output is
near-universal — but the primary source was **not retrieved**, so it is written as unverified
rather than asserted. The others are hard blocks: **Kling, MiniMax and Seedance may not be used
here until their terms are fetched.**

**Note the shape of those gaps.** Every unverified row is a partner API or a bundled weight;
every verified-clean row is open weights. Partner-API terms are the harder half of this map to
establish, which is itself an argument for the open-weights route being the default.

## No test exemption

"Just for a test" is a named drift tripwire in the [roadmap](/armature/handbook/roadmap/). The
gate has no test exemption, because the output of a test is a conclusion, and a conclusion drawn
on a banned model is one that has to be discarded.
