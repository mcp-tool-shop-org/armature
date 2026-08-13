---
title: The thesis
description: Why control sequences rendered from geometry — the argument, and what the published evidence does and does not support.
sidebar:
  order: 2
---

## One paragraph

A video model can produce motion, light and life that no renderer can. It cannot be told *who is
on screen and where they are standing*. armature stages a canonical character mesh in headless
Blender and turns the render into a per-frame **control sequence** the video model must obey.
You block the shot; the model shoots it. Structure comes from geometry we own; life comes from
the model; **identity is a named, versioned thing that rides in the prompt and the reference
stack, never an accident of a lucky frame.** The deliverable is footage — film, cutscenes,
character performance, anything image-to-video can make, made from a scene you own. A game is
one consumer, not the boundary.

**That thesis is now measured.** The mechanism first — as of 2026-08-11, across 22 generations
in five closed experiments:

- a rendered control sequence **governs where the figure is, at what scale, and when it moves**;
- it **governs authored subject motion** — an 85.0° arm sweep against 0.062° when the same control
  is held still;
- **control owns the outline and the reference owns surface, material and costume**, with the
  reference able to *extend* a silhouette only where the control is silent;
- and inverting the depth control end-to-end **does not break tracking**, so the model is reading
  geometry rather than tone.

**The two questions that were open then have since been answered at product level.** The rigged
character mesh exists — E07 rebuilt the rig and the Director approved the skeleton by eye — and
identity has held through paint at the judging eye three times: driven from the rig (E08),
unanchored with no reference and no driving signal at all (E11 wave 1), and through the camera
tier, where a handed world also holds to the last frame on two seeds (E12). What remains open is
route-shaped, not thesis-shaped — and E13 answered it on 2026-08-13, its whole arc
(dispatch, a zero-spend halt on two structural premise failures, a repair arc that rebuilt
the reference kit with true alpha, re-arm, four generations) inside one date: **identity
survives a hosted, human-trained tier fed nothing but authored references**, both arms,
both seeds, at the Director's eye — and the reference's own ground steers the model-decided
world. Full detail in `docs/experiments/`; every claim above is traceable to a numbered
ruling.

What follows is the published evidence that made the thesis worth testing, gathered by a founding
research swarm on 2026-08-10 and recorded in
[docs/research-grounding.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/research-grounding.md).
Findings are cited by their number there.

## How much to trust each finding

The grounding pass has a stated ceiling, and it matters more than any individual number.

**Existence** was checked for all 34 arXiv identifiers by a deterministic retrieval oracle rather
than by model memory: **34 of 34 resolved, zero fabricated.** First authors and years were
checked against the oracle's returned metadata, and one attribution error was caught and
corrected that way (F9 was reported as 2026; the oracle returns 2025-04).

**Groundedness** — whether a paper's abstract actually supports the claim attributed to it — was
run by two decorrelated non-Claude model families, reasoning-stripped, on the two claims that
decide the first experiment's architecture. **Not on all 34.** Findings marked
*unverified-groundedness* below have confirmed existence and correct attribution but no second
check; they may inform a design and may not carry it alone.

That distinction did real work immediately. **F2 was downgraded** from load-bearing to diagnostic
because both checkers returned NOT_IN_ABSTRACT — its numbers live in a table, not the abstract,
and the table has not been retrieved. It is not used as a design constraint here.

## The core claim: dense guidance rendered from a body model beats a 2D skeleton

**F1 — the only finding confirmed by both groundedness checkers.** Champ (Zhu et al. 2024,
[arXiv:2403.14781](https://arxiv.org/abs/2403.14781)) compared dense 3D-parametric guidance —
depth, normal and semantic maps rendered from a posed parametric body — against a 2D skeleton
alone:

| | Skeleton-only | Dense 3D-parametric |
|---|---|---|
| FVD (lower better) | 192.34 | **170.20** |
| SSIM (higher better) | 0.672 | **0.773** |
| LPIPS (lower better) | 0.296 | **0.235** |

And the ablation that matters most: **dropping the skeleton entirely still beat skeleton-only on
FVD, at 184.24.** The skeleton is a small additive term, not the backbone.

**This is armature's thesis, measured by someone else.** It also names a starting channel set —
depth, normal and semantic, with a skeleton optional — rather than leaving it to taste.

**F21**, from the same paper, is the closest published precedent to armature's exact move: Champ
renders those maps from a 3D parametric body and **explicitly bypasses video-based pose
detection**. No 2D estimator in the loop. That is the same architectural decision, taken for the
same reason, and it is why armature is not a wrapper around a pose extractor.

What none of this establishes: Champ's subject matter is not stylized game characters, and its
generator is not the one armature will probe. Whether the result transfers is the question the
repo's first generation experiment exists to ask, not something this page can answer.

## Where the risk actually sits

**F6 (unverified-groundedness).** VACE (Jiang et al. 2025,
[arXiv:2503.07598](https://arxiv.org/abs/2503.07598)) accepts depth, pose, scribble, gray,
layout, flow, spatiotemporal masks and reference images, and beats task-specific baselines on
depth and pose control — but **loses reference-to-video** to Vidu 2.0 (3.40 vs 3.84).

Read the two halves together: **structure control is the solved leg; identity is the weak one.**
That is armature's risk profile precisely, and it is why identity gets phases of its own rather
than a paragraph.

**F8 (unverified-groundedness).** Even the strongest current reference-to-video methods reach
only modest face similarity — FaceSim-Arc 0.571 for the proposed method in Xu et al. 2026
([arXiv:2607.20247](https://arxiv.org/abs/2607.20247)), with VACE-14B at 0.531 and Phantom-14B at
0.495. **Visible identity drift is the default, not the exception.** Any prediction written here
starts from that.

**F13 (unverified-groundedness).** Multi-shot benchmarks measure character-recurrence gaps across
as many as 48 shots and report that naive multi-shot systems introduce extra characters, with
semantic drift and identity inconsistency (He et al. 2026,
[arXiv:2605.15199](https://arxiv.org/abs/2605.15199); Zhang et al. 2025,
[arXiv:2512.12372](https://arxiv.org/abs/2512.12372)). **Identity is not free across a cut.** It
needs an explicit mechanism, and finding out which one is a phase in the arc.

**F10 (unverified-groundedness).** Reference sets spanning diverse subject orientations produced
substantially stronger identity coherence than a single canonical view (Zeng et al. 2026,
[arXiv:2604.07823](https://arxiv.org/abs/2604.07823)). If that holds here, the right input is a
**full turnaround rather than one hero frame** — and a turnaround is exactly what the sibling
tool upstream already produces. Whether it holds here is a measurement nobody has taken.

**F5 (unverified-groundedness).** Control-scale curves are non-monotonic: past a threshold,
dynamics *decrease* as motion degenerates into abrupt cuts. Rotation is far harder to control
than translation — leakage 1.08 versus 6.04 (Hou & Rupprecht 2026,
[arXiv:2605.14815](https://arxiv.org/abs/2605.14815)). The uncomfortable implication: **an
orbiting camera is the obvious first shot to try and may be the hardest regime there is.**

**F4 (unverified-groundedness).** Control held at full strength is a named failure mode, not a
theoretical one — a ControlNet scale pinned at 1.0 produces a walk described as rigid and
translational rather than a natural gait; annealing the scale over early denoising steps restores
it (Zhou et al. 2026, [arXiv:2603.15614](https://arxiv.org/abs/2603.15614)). Whatever the right
control strength turns out to be, it is likely a *schedule* rather than a constant.

## Why a shot, and not a continuous roll

**F14 (unverified-groundedness).** Open-weight native lengths are short and set by the training
horizon — HunyuanVideo 129 frames, Wan 2.2 optimal at or below 120 frames, LTX-2 10 seconds
standard. **The shot is already the native unit.** Staging per shot matches the engines rather
than fighting them.

**F15 (unverified-groundedness).** This is the strongest quantitative support for armature's
overall shape. Anchor-bounded generation measurably suppresses drift: plain autoregressive
rollout swings 5.94–6.54 VBench Imaging Quality points at each chunk boundary versus 1.23–1.50
for anchor-bounded, and scores 6.2–6.6 points higher in aggregate over a thirty-minute horizon
(Bendel et al. 2026, [arXiv:2605.20476](https://arxiv.org/abs/2605.20476)). **A shot bounded by
fixed staged state is an easier problem than free-running continuation.**

**F16 and F18 (unverified-groundedness).** Autoregressive degradation has a formal account —
cumulative per-step error, with more conditioning frames monotonically reducing forgetting
without removing degradation. And every long-form system found decomposes into shots or keyframe
anchors plus assembly; none is one continuous roll. **Shots plus cuts is the working grammar**,
which is convenient, because shots plus cuts is also how films are made.

## Format is not a detail

Getting the output *conventions* wrong would silently invalidate every later experiment, so they
are grounded rather than guessed.

**F19 (unverified-groundedness).** ControlNet-family depth conditioning is inverse relative depth
— near is bright — normalized per frame, and hard-capped at 8-bit because the conditioning image
is an RGB PNG with R=G=B. A proposal to pack more precision across channels was never adopted
upstream. Sixteen-bit buys these consumers nothing.

**F20 — verified by direct source retrieval**, not by model memory. The OpenPose-18 skeleton is
fully code-specified: 18 keypoints, a fixed 19-pair limb sequence, and an 18-colour per-limb
palette. The pair list was fetched and read at ruling time, and it is **1-indexed** — a live trap
for anyone writing a renderer from scratch, along with the fact that the target is COCO-18, not
COCO-17 and not Body25.

**F24 (unverified-groundedness).** Wan and VACE require width and height divisible by 16 and
frame counts of the form 4n+1. A frame size that is not generator-legal breaks every downstream
pairing, and it fails *quietly* — which is the worst way for a constraint to fail.

**F22 (unverified-groundedness).** A rendered geometric edge pass sidesteps Canny's per-image
dual-threshold tuning, which does not generalize across shots and is contrast-sensitive. So
rendered edges *should* be more temporally consistent than Canny run over rendered RGB — stated
here as a testable claim, not an assumption.

## The gaps, named so silence is not mistaken for evidence

The research swarm was explicit about what it could not answer:

- **No quantitative strength-versus-identity-drift curve exists anywhere.** There is no prior to
  predict against; that curve has to be measured here.
- **No clean single-architecture ablation isolating the number of reference views** against an
  identity metric. The closest (F10) comes from a different application.
- **No study compares per-character adapters against zero-shot conditioning on stylized game art
  specifically** — every quantified comparison found used photoreal subjects.
- **No head-to-head of depth versus pose versus segmentation on a single identity metric.**
- **No controlled study isolating bounded versus unbounded drift on the same model.**
- **No primary technical reports for Kling, Seedance or Veo 3** — closed systems, no papers.

## One thing no metric will decide

Whether the figure on screen **is the same character** is canon, and no metric approximates it.
The repo learned this secondhand from facet, which established it twice — once with high-pass
statistics for material identity, once with silhouette IoU for character identity.

There is a sharper version for this domain. **F12 (unverified-groundedness):** standard
face-recognition embeddings hold roughly 0.76–0.78 true-positive rate in-distribution but
collapse to 0.372 on unseen stylization, mistaking a style shift for an identity change (Yun et
al. 2026, [arXiv:2604.21689](https://arxiv.org/abs/2604.21689)), corroborated by a
5,013-identity cartoon benchmark showing photo-trained recognizers transfer poorly (Zheng et al.
2019, [arXiv:1907.13394](https://arxiv.org/abs/1907.13394)).

So ArcFace-family metrics **cannot gate identity on stylized game art**, and a diagnostic that
returns a number on a face its detector never found is noise wearing a unit. Identity and quality
diagnostics ride reports as diagnostics and gate nothing. The Director's eye is the judge.
