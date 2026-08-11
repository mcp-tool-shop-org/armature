# Research grounding — the E08 study-swarm (the two generative slots)

Run 2026-08-11 by the advisor seat at the Director's word, after consult #6 confirmed SLOT 1
(prompt → skeletal motion) unfilled on Cloud. Five parallel research lanes on Sonnet
executors: the SLOT-1 field · monocular motion lift · the driving-signal convention ·
cross-shot identity · retargeting practice. Protocol:
`research-grounded-advisor-protocol.md` (canonical memory store). Findings are cited by
**G-number**; the founding swarm's F-numbers ([research-grounding.md](research-grounding.md))
remain separately citable.

## Verification record (the gate this passed)

**Stage 1 — existence, deterministic retrieval oracle.** The arXiv batch API returned
**HTTP 429 three times** (the founding swarm's exact transient — never read as fabrication).
Fallback: per-paper `abs` pages. **10 of 10 load-bearing ids RESOLVED** with matching
titles/first-authors/years: 2509.14055 · 2608.06009 · 2605.15199 · 2312.07531 · 2409.06662 ·
2206.11678 · 2412.09349 · 2408.16506 · 2411.17697 · 2406.13272. Champ (2403.14781) carries
the founding swarm's verification. Two attributions corrected against the oracle: BlazePose
GHUM Holistic's first author is **Grishchenko** (lane reported Bazarevsky); Wan-Animate-2's
first author is **Guangyuan Wang** (lane reported the lab). Three non-paper sources fetched
**directly** (deterministic self-oracle): the Wan2.2 convention file
`human_visualization.py`, the AMASS licence page, and the Wan2.2 repo `LICENSE.txt`.

**Stage 2 — groundedness, two decorrelated non-Claude families, reasoning-stripped**
(mistral-small:24b / Mistral · granite4.1:30b / IBM Granite, both local, bare claim +
abstract only), on the three load-bearing paper claims:

| Claim | mistral-small:24b | granite4.1:30b | Disposition |
|---|---|---|---|
| C1 — Wan-Animate: skeleton signals for body, implicit face features for expression | SUPPORTED (`run_…22-40-44_2658aa`) | SUPPORTED (`run_…22-41-40_afa205`) | **admitted, load-bearing** |
| C2 — Wan-Animate-2 names extraction errors + identity drift in explicit-skeleton methods; consumes driving video directly | SUPPORTED on corrected wording (`run_…22-42-36_ee5d33`); original wording drew NOT_IN_ABSTRACT with a justification contradicting the handed text — wording corrected once per the protocol's correct-once path | SUPPORTED | **admitted, load-bearing** |
| C3 — EntityBench: cross-shot consistency degrades with recurrence distance; persistent per-entity reference memory wins | SUPPORTED | SUPPORTED | **admitted, load-bearing** |

**Instrument incident, recorded as law:** the first groundedness pass silently **degraded
both families to one model** — the envelope's `model` field read `hermes3:8b`
(`degrade_reason: cloud_model_missing`) against requests for the 24B/30B — and that single
8B then rejected sentences present near-verbatim in its sources. No ensemble existed and the
verdicts were noise. Caught by reading the served-model field, fixed by pinning
`backend: local` and warming the models. **A family-lens run records the SERVED model from
the response envelope, never the requested name.** Second incident: 20 s tier budget cannot
cold-load a 24B/30B (`TIER_TIMEOUT`) — warm via `ollama run` first.

**Honest ceiling:** 17 supporting ids (the MDM/MoMask/T2M-GPT/OmniControl/OMG line, Motion-X,
AnyTop, TRAM, WATCH, 4D-Humans, SMPLer-X, LoBSTr, PhysCap, AnyID, AniCrafter, MuSS, NKN,
OmniRetarget, the in-betweening paper) were retrieved live by the research lanes but **not
oracle-confirmed this session** (API 429) — they inform as **advisory** and are not
load-bearing. Licence texts cited by lanes (SMPL, MediaPipe, vendor terms) are
**agent-retrieved claims with URLs**; each becomes a licence-map row only through the map's
own fetch procedure before any dependency is adopted.

---

## The findings

### SLOT 1 — the motion generator

**G1. The AMASS licence prohibits using the dataset to train models for commercial use —
fetched verbatim: "This license also prohibits the use of the Dataset to train
methods/algorithms/neural networks/etc. for commercial use of any kind."**
(amass.is.tue.mpg.de/license.html, fetched 2026-08-11, deterministic oracle.)
→ The entire AMASS/HumanML3D-trained open-weight text-to-motion line — MDM, MotionGPT,
MoMask, T2M-GPT, OmniControl, OMG (advisory tier, MIT **code** throughout) — is closed to
this pipeline at the weights layer regardless of code licence. **SLOT 1 has no self-hosted
open-weight filler from the research line.** Motion-X is independently non-commercial;
AnyTop (off-AMASS, creature domain) reports its own data licence unresolved.

**G2. SMPL/SMPL-X body-model licences carry the same clause family (research-only;
commercial via Meshcapade)** — agent-retrieved from smpl.is.tue.mpg.de/modellicense.html and
smpl-x.is.tue.mpg.de/modellicense.html; **advisory pending the map's own fetch.**
→ The body-model layer gates the SMPL-based lift line independently of each project's code
licence.

**G3. Every surveyed SMPL-line video→motion candidate is gated at least once: WHAM / TRAM /
4D-Humans are MIT code that require the SMPL weight file at inference; GVHMR and SMPLer-X
are explicitly non-commercial at the code licence itself.** — Shin et al. 2023
(arXiv:2312.07531, WHAM: EMDB WA-MPJPE100 135.6 mm, jitter 22.5, foot-slide 4.4 mm); Shen et
al. 2024 (arXiv:2409.06662, GVHMR: 111.0 mm, jitter 16.7, foot-slide 3.5 mm, ~7× faster —
the best measured of the group and the most explicitly closed). Existence oracle-confirmed
for both; licence texts advisory.
→ Measured quality and licence cleanliness point in opposite directions across the whole
SMPL line. None enters this pipeline as-is.

**G4. MediaPipe Pose Landmarker is the lone surveyed self-hosted candidate whose shipped
inference path avoids the research-licensed tier: Apache-2.0 repo, 33 3D world landmarks
regressed directly, GHUM used only for training-time pseudo-ground-truth — at a measured
accuracy tier below the SMPL line (BlazePose GHUM Holistic: MPJPE-PA 78 mm vs WHAM's
50.4 mm, differing protocols), with no published jitter metric and no published
production case of driving a full character rig.** — Grishchenko et al. 2022
(arXiv:2206.11678, existence oracle-confirmed); licence + no-GHUM-at-inference
agent-retrieved (github.com/google-ai-edge/mediapipe LICENSE; docs). **Advisory pending the
map's fetch.**
→ A licence-clean lift exists, with an unmeasured quality gap. If adopted it is a
calibration experiment first, never an assumption.

**G5. Hosted text-to-motion APIs (DeepMotion SayMotion, Uthana, Cartwheel) grant commercial
rights to generated output by contract; none discloses its training-data chain.** —
agent-retrieved from vendor pages (deepmotion.com/saymotion, uthana.com, Cartwheel press),
2026-08-11. → The only present-day prompt→skeletal-motion path that requires no build.
Enters, if at all, through the map's partner-API procedure: terms fetched per vendor, ruled
CONDITIONAL at most, **Director decision by definition**.

### SLOT 2 — the performer (Wan-Animate route)

**G6. The driving convention is code-defined in an Apache-2.0 repo and is exactly
matchable: `draw_aapose_by_meta_new` in `wan/modules/animate/preprocess/
human_visualization.py` (Wan-Video/Wan2.2) — zeroed-black canvas; the 20-entry OpenPose
rainbow palette ([255,0,0], [255,85,0] … [100,100,0]); the classic 18-point `limbSeq`
including five head keypoints (neck-nose, nose-eyes, eyes-ears: [2,1],[1,15],[15,17],
[1,16],[16,18]); `stickwidth = max(int(min(H,W)/200) − 1, 1)`; hands drawn separately by
`draw_handpose_new` (red joints, HSV-rainbow edges). The officially pinned detector variant
is ViTPose-H wholebody.** (File + repo LICENSE fetched 2026-08-11 — Apache-2.0, so reading
and matching this source is licence-clean; convention detail deterministic-oracle-confirmed;
detector pin agent-retrieved from `UserGuider.md`.)
→ **The pose-render commission has an exact specification**: wholebody-class keypoints
derived from the rig (including nose/eyes/ears markers from the head, and hand sticks —
the mannequin's mitten hands render as static hand skeletons), drawn to this palette,
topology and width formula, pinned to the repo file at a commit sha. The DWPose drawing
codepath that ComfyUI tutorials default to is a **different implementation** — no
equivalence is documented; do not conflate them.

**G7. Wan-Animate drives the body from spatially-aligned skeleton signals and the face from
implicit features extracted from source images — not from skeleton keypoints.** — Cheng et
al. 2025 (arXiv:2509.14055). **✅ groundedness-confirmed, two families (C1).**
→ The graph feeds `face_video` from face-crop renders of the performer as its own channel;
the skeleton render carries only the five head keypoints, no facial detail.

**G8. Wan-Animate's internal retargeting is per-limb bone-length-ratio rescaling between
driving and reference skeletons.** — same paper, full-text section (agent-retrieved;
*advisory — not abstract-verifiable*).
→ Rendering pose from the character's own rig makes driving and reference proportions
identical by construction — the retarget stage's job is pre-done at authoring time. Render
at true proportions; never adapt toward "average human."

**G9. The vendor's own successor paper names the failure axis of the explicit-skeleton
paradigm: extraction errors and identity drift; Wan-Animate-2 deletes the extractor tier
and consumes driving video directly.** — Wang et al. 2026 (arXiv:2608.06009).
**✅ groundedness-confirmed, two families (C2, wording corrected once).**
→ Two consequences: (a) E08's probe explicitly measures identity fidelity under the
skeleton route — the risk is vendor-named, not hypothetical; our route removes the
*extraction-error* half by construction (no detector — rendered ground truth) while the
*out-of-distribution skeleton proportions* half remains and is what the probe measures;
(b) Animate-2 wants a real performance video, not a pose render — it is a candidate for a
**different, later route** (and stays UNVERIFIED = NO in the map until identified).

**G10. Sparse-skeleton ambiguity and shape misalignment degrade pose-guided generation
silently — denser conditioning worsens it when shapes diverge, and misalignment costs
appearance fidelity without erroring.** — Li et al. 2024 (arXiv:2412.09349, DisPose); Jin
et al. 2024 (arXiv:2408.16506). Existence oracle-confirmed; findings advisory (abstract-level
lens not run).
→ Pre-registered: a weak or off-convention render fails silently. Gate 0's sheet carries
motion-adherence panels; no parameter is retuned past a soft result without a ruling.

**G11. Rendering the driving signal from a 3D body beats detecting it from video —
armature's thesis, measured by others (founding F1, Champ, arXiv:2403.14781, two-family
verified 2026-08-10).** → E08 extends a published pattern to Wan-Animate specifically; the
lanes found **no prior published case** of a CG-rendered `pose_video` into this exact model —
the probe is a genuine first measurement, and is framed as such.

### Identity across shots

**G12. Identity machinery is measured to matter in this model class: CSIM spans 0.805 vs
0.242–0.347 across sibling methods; ablations — removing face masking −16.6 % CSIM,
removing the dedicated face encoder −26.2 %.** — Tu et al. 2024 (arXiv:2411.17697,
StableAnimator). Existence oracle-confirmed; numbers advisory.
→ Arm `character_mask` and the face channel in the E08 graph; they are the two levers the
literature prices.

**G13. Stylized and 3D-rendered references are a documented degraded class for identity
binding relative to photographs.** — Chen et al. 2024 (arXiv:2406.13272, AniFaceDiff).
Existence oracle-confirmed; finding advisory.
→ Budget a lower identity floor for the mannequin than photoreal benchmarks suggest; when
identity wobbles in the probe, reference class ranks **above** convention error in the
candidate-cause list. The Director's eye remains the verifier of record.

**G14. Cross-shot consistency degrades sharply with recurrence distance; a persistent,
locked per-entity reference memory yields the highest character fidelity (Cohen's
d = +2.33).** — He et al. 2026 (arXiv:2605.15199, EntityBench).
**✅ groundedness-confirmed, two families (C3).**
→ **One canonical reference-render set of the performer, hashed, reused verbatim across
every shot and wave.** References are never regenerated per shot. This is the multi-shot
strategy, and it is now evidence, not preference.

**G15. The model card's own guidance recommends a default text prompt — the motion signal
is designed to dominate text.** — Wan-Animate model card/paper (agent-retrieved; advisory).
→ The scene-from-prompt clause is **at risk on this route**: the probe measures how much
bar the prompt actually paints. If weak, the levers are `background_video` or scene-bearing
staging in a later wave — measured before promised.

### Retargeting (live only if a SLOT-1 arm lands motion on the rig)

**G16. Practice is layered, not single-method: IK endpoint matching on
proportion-normalized skeletons (Choi & Ko 2000; Monzani et al. 2000), explicit foot-lock
(Kovar et al. 2002), and — for position-only streams — a separate rotation solve, since
positions underdetermine twist (two-bone analytic IK + pole/twist references; MediaPipe
world landmarks are additionally hip-origin, so global root translation needs its own
recovery).** — classic line agent-retrieved with URLs; advisory.
→ The solver commission, if Arm B is picked: two-bone IK + pole conventions + foot-lock +
root-motion recovery, its tests riding the commit. Not a weekend script; spec'd as a tool.

**G17. Foot-contact cleanup needs contact labels the dance case degrades: ~95 %+ label
accuracy required, ~85–90 % measured on complex dance; kinematic-only retargeting yields
severe skating vs near-zero for contact-aware methods.** — LoBSTr / PhysCap /
UnderPressure / OmniRetarget line (advisory tier).
→ For a **dance** first shot via the lift arm, foot artifacts are the expected defect
class: graded on the sheet at the Director's zoom, never tuned past silently.

---

## Connections — where each E08 spec choice gets its floor

| Spec choice | Grounding |
|---|---|
| Pose render matches `draw_aapose_by_meta_new` exactly (palette, 18-pt topology + head points, width formula, separate hand sticks), pinned to repo file + sha | G6, G10 |
| Render at the character's true proportions; no humanization | G8, G9 |
| `face_video` = face-crop renders; skeleton carries no facial detail | G7, G12 |
| `character_mask` armed | G12 |
| One locked, hashed reference-render set reused across all shots | G14 |
| Probe measures scene-from-prompt strength explicitly | G15 |
| Probe measures identity fidelity as its own clause; stylized-reference floor expected lower | G9, G13, G11 |
| SLOT-1 fork is a Director decision (hosted contract vs clean-lift build) | G1–G5, G16, G17 |

## The SLOT-1 verdict this grounding supports

The open-weight research line is closed by the data tier itself (G1); the SMPL lift line is
closed at code or body-model layer (G2, G3). What remains: **Arm A** — a hosted
text-to-motion API under per-vendor contract terms (G5; partner-API procedure, CONDITIONAL
at most, Director's call on whether an undisclosed training chain is acceptable at all);
**Arm B** — the fully self-hosted clean chain: Wan T2V (Apache, outputs owned) generates a
performance clip → MediaPipe (G4, licence pending the map's fetch) lifts world landmarks →
our own solver (G16, G17) lands them on the rig — quality unmeasured, calibration
experiment first. Both arms' next step is a zero-credit licence/terms fetch; neither is
adopted here. The spec rewrite waits on the Director's pick.
