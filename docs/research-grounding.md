# Research grounding — the founding study-swarm

Run 2026-08-10 by the advisor seat, before any architecture was fixed. Five parallel research
lanes; every finding carries a resolvable identifier. Specs cite these **by number**.

## Verification record (the gate this passed)

**Stage 1 — existence, by deterministic retrieval oracle (not model memory): 34 / 34 arXiv ids
RESOLVED. Zero fabricated.** Resolved against the arXiv API, with the three that survived rate
limiting confirmed against their `abs` pages. First authors and years were checked against the
oracle's returned metadata.

> ⚠ **The oracle's own first run returned 0/34 and was wrong.** Known-real papers (VBench,
> iCartoonFace) failed alongside everything else, which is the signature of a broken instrument
> rather than fabricated citations — a check that rejects everything is measuring itself. The
> defect was XML parsing in the harness; corrected, the same ids resolved 31/34, and the
> remaining 3 were arXiv rate-limiting (HTTP-level), never fabrication. Recorded because the
> first result was one careless step from becoming a false halt on the entire swarm.

**Stage 2 — groundedness, two decorrelated non-Claude families (mistral-small:24b / Mistral and
granite4.1:30b / IBM Granite), reasoning-stripped**, run on the load-bearing architectural
claims:

| Claim | mistral-small:24b | granite4.1:30b | Disposition |
|---|---|---|---|
| F1 (Champ — 3D-parametric guidance beats skeleton-only) | SUPPORTED | SUPPORTED | **load-bearing, admitted** |
| F2 (Ctrl-Adapter — multi-condition compounding, depth-vs-canny split) | NOT_IN_ABSTRACT | NOT_IN_ABSTRACT | **downgraded to diagnostic** — the numbers live in a table, not the abstract; not admitted as load-bearing until full text is retrieved |

**One attribution error found and corrected:** finding F9 was reported as *Kim et al. 2026*;
the oracle returns **2025-04**. Corrected below.

**Honest ceiling:** groundedness was run on the two claims that decide E01's architecture, not
on all 34. Findings marked *(unverified-groundedness)* have confirmed existence and correct
attribution but no second-family support check — they may inform, and may not be load-bearing
without one.

---

## Lane 1 — Control signals

**F1. Dense 3D-parametric guidance (depth + normal + semantic rendered from a body model) beats
2D skeleton-only decisively: FVD 192.34 → 170.20, SSIM 0.672 → 0.773, LPIPS 0.296 → 0.235; and
dropping the skeleton entirely still beats skeleton-only on FVD (184.24).** — Zhu et al. 2024,
*Champ* (arXiv:2403.14781). **✅ groundedness-confirmed, two families.**
→ **This is armature's thesis, measured by someone else.** A render from a posed mesh
outperforms a 2D skeleton, and the skeleton is a small additive term rather than the backbone.
It also tells us the *channel set*: depth + normal + semantic, with skeleton optional.

**F2. Multi-condition control compounds but saturates: depth alone → flow error 3.20 / FID 7.43;
depth+canny → 2.84; four conditions → 2.40; seven → 2.48 with FID degrading to 8.18–9.48. On one
backbone depth wins spatial control (3.20 vs 3.37) while canny wins visual quality (FID 6.42 vs
7.43).** — Lin et al. 2024, *Ctrl-Adapter* (arXiv:2404.09967). *(groundedness NOT_IN_ABSTRACT ×2
— diagnostic only, not load-bearing.)*
→ Suggests a small channel set beats a large one, but **not admitted as a design constraint**
until the table is retrieved.

**F3. Training-free comparison: depth beats canny on both temporal consistency (97.22% vs
96.83%) and prompt consistency (31.81% vs 30.75%).** — Zhang et al. 2023, *ControlVideo*
(arXiv:2305.13077). *(unverified-groundedness.)* → A second, independent vote for depth primary.

**F4. Control held at full strength is a named failure: ControlNet scale pinned at 1.0 makes a
walk "rigid… translational rather than a natural gait"; annealing 1.0 → 0.005 over the first 10
of 50 denoising steps restores the gait.** — Zhou et al. 2026, *Tri-Prompting*
(arXiv:2603.15614). *(unverified-groundedness; the source's own evidence is qualitative.)*
→ E04's strength arm should test a *schedule*, not only a constant.

**F5. Control-scale curves are non-monotonic — past a threshold, dynamics decrease as motion
degenerates into abrupt cuts; rotation is far harder to control than translation (leakage 1.08
vs 6.04).** — Hou & Rupprecht 2026 (arXiv:2605.14815). *(unverified-groundedness.)*
→ **Orbiting cameras are the weakest control regime.** Directly relevant: an orbit is the
obvious first shot and may be the hardest one.

**F6. VACE accepts depth, pose, scribble, gray, layout, flow, spatiotemporal masks and reference
images, and beats task-specific baselines on depth and pose control — but loses
reference-to-video to Vidu 2.0 (3.40 vs 3.84).** — Jiang et al. 2025, *VACE*
(arXiv:2503.07598). *(unverified-groundedness.)*
→ **Structure control is the solved leg; identity is the weak one.** That is armature's risk
profile exactly, and it is why identity gets its own phase.

**F7. Decoupling control guidance from text CFG raised motion magnitude 1.565 → 6.450 while
*improving* translation error 0.640 → 0.577; sparse camera conditioning works to 93%
sparsity.** — Cheong et al. 2024 (arXiv:2410.10802). *(unverified-groundedness.)*

## Lane 2 — Identity

**F8. Even the best current reference-to-video methods reach only modest face similarity
(FaceSim-Arc 0.571 for the proposed method; VACE-14B 0.531; Phantom-14B 0.495).** — Xu et al.
2026, *Vera* (arXiv:2607.20247). *(unverified-groundedness.)*
→ **Expect visible identity drift as the default, not the exception.** This calibrates E05's
predictions before they are written.

**F9. Zero-shot reference conditioning — identity injection learned from image pairs, motion
priors left to the pretrained backbone — matched large trained baselines (VACE, Phantom) at
roughly 0.4–2.8% of their GPU-hours.** — Kim et al. **2025** (arXiv:2504.17816) *(year corrected
from the lane's "2026" by the oracle; unverified-groundedness.)*
→ **E06 (per-character LoRA) may be the expensive, less-justified path.** The roadmap already
made E06 conditional; this is why.

**F10. Reference sets spanning diverse subject orientations produced substantially stronger
identity coherence than a single canonical view.** — Zeng et al. 2026, *LPM 1.0*
(arXiv:2604.07823). *(unverified-groundedness.)*
→ Feed the **8-view turnaround**, not one hero frame. The sibling tool's output is the right
input.

**F11. VBench scores subject consistency with DINO embeddings rather than CLIP, specifically
because CLIP is trained toward within-class invariance while DINO is sensitive to identity
difference.** — Huang et al. 2023/CVPR 2024, *VBench* (arXiv:2311.17982).
*(unverified-groundedness.)* → If a diagnostic is wanted, DINO cosine — not CLIP-I.

**F12. Standard face-recognition embeddings hold ~0.76–0.78 TPR in-distribution but collapse to
0.372 TPR on unseen stylization, mistaking style shifts for identity change.** — Yun et al.
2026, *StyleID* (arXiv:2604.21689). Corroborated independently by a 5,013-identity cartoon
benchmark showing photo-trained recognizers transfer poorly — Zheng et al. 2019,
*iCartoonFace* (arXiv:1907.13394). *(unverified-groundedness.)*
→ **ArcFace-family metrics cannot gate identity on stylized game art.** This is now written into
CLAUDE.md as a rule: a diagnostic that returns numbers on a face it cannot find is noise wearing
a unit.

**F13. Multi-shot narrative benchmarks measure character-recurrence gaps up to 48 shots, and
naive multi-shot systems "incorrectly introduce extra characters, leading to semantic drift and
identity inconsistency."** — He et al. 2026, *EntityBench* (arXiv:2605.15199); Zhang et al.
2025, *STAGE* (arXiv:2512.12372). *(unverified-groundedness.)*
→ Identity is **not free across cuts**; it needs an explicit mechanism. That is E07.

## Lane 3 — Shot length and drift

**F14. Open-weight native lengths are short and set by the training horizon: HunyuanVideo 129
frames (~5 s), Wan 2.2 optimal ≤120 frames (~5 s), LTX-2 10 s standard.** — Kong et al. 2024
(arXiv:2412.03603); Wan-Video 2025; Lightricks 2026. *(unverified-groundedness.)*
→ **The shot is already the native unit.** armature's per-shot staging matches the engines
rather than fighting them.

**F15. Anchor-bounded generation measurably suppresses drift: plain autoregressive rollout swings
5.94–6.54 VBench Imaging Quality points per chunk boundary versus 1.23–1.50 for anchor-bounded,
and scores 6.2–6.6 points higher in aggregate over a 30-minute horizon.** — Bendel et al. 2026,
*Goodbye Drift* (arXiv:2605.20476). *(unverified-groundedness.)*
→ **The strongest quantitative support for armature's shape:** a shot bounded by fixed staged
state is an easier problem than free-running continuation.

**F16. Autoregressive degradation has a formal account — cumulative per-step error, with
history-forgetting quantifiable; more conditioning frames monotonically reduces forgetting but
does not remove degradation.** — Wang et al. 2025 (arXiv:2503.10704). *(unverified-groundedness.)*
→ Extension drift is a property of the formulation, not a bug more context fixes.

**F17. First/last-frame conditioning is a deliberately built branch precisely because
forward-only continuation drifts — models fuse forward and backward motion instead of
extrapolating one direction.** — Wan2.1 FLF2V 2025; Wang et al. 2024, *Framer*
(arXiv:2410.18978); Wang et al. 2025, *KeyVID* (arXiv:2504.09656). *(unverified-groundedness.)*

**F18. Long-form systems all decompose into shots or keyframe anchors plus assembly, never one
continuous roll** — StreamingT2V re-anchors each chunk to the first; VideoDirectorGPT plans
multi-scene before generating; MovieDreamer predicts keyframe anchors then renders; STAGE writes
a shot-by-shot storyboard and generates between each shot's start/end pair. — Henschel et al.
2024 (arXiv:2403.14773); Lin et al. 2023 (arXiv:2309.15091); Zhao et al. 2024
(arXiv:2407.16655); Zhang et al. 2025 (arXiv:2512.12372). *(unverified-groundedness.)*
→ Converging architectural evidence that **shots-plus-cuts is the working grammar**.

## Lane 4 — Control-render conventions (E01's output spec)

**F19. ControlNet-family depth conditioning is inverse relative depth (near = bright), per-frame
min-max normalized, and hard-capped at 8-bit because the conditioning image is an RGB PNG with
R=G=B — a proposal to pack more precision across channels was never adopted upstream.** —
lllyasviel, ControlNet depth model card + Discussion #410, 2023
(https://huggingface.co/lllyasviel/control_v11f1p_sd15_depth). *(unverified-groundedness.)*
→ **E01 renders near-bright, normalizes per frame, exports 8-bit.** 16-bit buys these consumers
nothing — but see the spec's amendment note on keeping a lossless master.

**F20. The OpenPose-18 skeleton is fully code-specified: 18 keypoints, a fixed 19-pair `limbSeq`,
and an 18-colour per-limb palette in `draw_bodypose()` — the de facto target for pose ControlNets
and animation models.** — lllyasviel/ControlNet `annotator/openpose/util.py`, 2023.
**✅ verified by direct source retrieval** — `limbSeq` fetched and read at ruling time; it is
19 pairs, **1-indexed**: `[[2,3],[2,6],[3,4],[4,5],[6,7],[7,8],[2,9],[9,10],[10,11],[2,12],
[12,13],[13,14],[2,1],[1,15],[15,17],[1,16],[16,18],[3,17],[6,18]]`.
→ E01 must reproduce COCO-18 indexing, this pair list and the palette — **not COCO-17, not
Body25.** The 1-indexing is a live trap for a from-scratch renderer.

**F21. Direct precedent for rendering control from known 3D joints with no 2D detector in the
loop: Champ renders depth, normal and semantic maps from a 3D parametric body, explicitly
bypassing video-based pose detection.** — Zhu et al. 2024 (arXiv:2403.14781).
→ Same source as F1, and it is the closest existing precedent to E01's exact move.

**F22. A rendered geometric edge pass sidesteps Canny's per-image dual-threshold tuning problem,
which does not generalize across shots and is contrast-sensitive.** — lllyasviel/ControlNet
README + sd-controlnet-canny card, 2023. *(unverified-groundedness.)*
→ Rendered edges should be **more temporally consistent** than Canny run over rendered RGB.
A testable claim, not an assumption.

**F23. Generative Rendering drives video diffusion from a deliberately low-fidelity rigged mesh
via injected 3D correspondence; later analysis attributes its flickering and texture-sliding to
correspondence not tracking RGB space precisely.** — Cai et al. 2024, SIGGRAPH
(arXiv:2312.01409); flicker analysis, Huang et al. 2026 (arXiv:2604.02329).
*(unverified-groundedness; ⚠ the second id's title is "Generative World Renderer" — its
characterization as a flicker analysis is the lane's summary and is NOT confirmed.)*
→ Validates the **low-fidelity mesh premise** while favouring explicit per-frame maps over
implicit correspondence.

**F24. Wan/VACE constraints: width and height must be divisible by 16; frame count follows
4n+1 (temporal compression factor 4, first frame padded); Wan2.1-Fun-Control documents 512/768/
1024 at ≤81 frames @16 fps with Canny/Depth/OpenPose/MLSD as named control types.** — ComfyUI
docs, 2026 (https://docs.comfy.org/tutorials/video/wan/vace). *(unverified-groundedness.)*
→ **E01 rounds dimensions to /16 and emits 4n+1 frame counts.** facet's law applies: a frame
that is not generator-legal breaks every downstream pairing, and it fails *quietly*.

## Lane 5 — Licensing

Full map in [license-map.md](license-map.md), all rows fetched 2026-08-10. Load-bearing results:
**OpenPose is CMU non-commercial and therefore banned here**; **Depth Anything V2 Small is Apache
while Large is CC-BY-NC** (same family, different licence); **Wan 2.x is unconditionally Apache
2.0 across base, VACE and Fun-Control** and is the default route; HunyuanVideo excludes the EU,
UK and South Korea by territory. Five items could not be retrieved and are treated as NO.

→ **The architectural consequence:** rendering depth from Blender's Z-buffer and drawing the
skeleton from known bone transforms removes the entire banned preprocessor tier **by
construction**, not by substitution.

---

## What the swarm did NOT answer

Named so no later session mistakes silence for evidence:

- **No quantitative strength-vs-identity-drift curve exists anywhere.** E04 has no prior to
  predict against; it must measure its own.
- **No clean single-architecture ablation isolating "N reference views"** against an identity
  metric. F10 is the closest and comes from a different application.
- **No study compares per-character LoRA against zero-shot conditioning on stylized game art
  specifically** — every quantified comparison found used photoreal subjects.
- **No head-to-head of depth vs pose vs segmentation on a single identity metric.**
- **No controlled study isolates FLF-bounded vs unbounded drift on the same model** — F17 is
  architectural, not one head-to-head number.
- **No primary technical reports for Kling, Seedance or Veo 3** (closed, no papers).
