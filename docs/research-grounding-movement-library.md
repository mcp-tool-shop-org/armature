# Research grounding — movement-library sourcing survey

**Requested by the Director 2026-08-12** (the admin-shelf lever, on request per the E09
closing ruling). **Frame:** the ruling's two admission paths govern — (1) online sources
enter **only on fetched terms**, with a licence-map row before the first clip downloads;
(2) **the owned factory**: licence-clean donors lifted through the studio's own chain,
publishable by construction. A shortlist of 2D sprite frameworks accompanied the request
with search-engine licence claims attached; arm 5 evaluates it against documents.

**Method:** five parallel research agents (Sonnet), retrieval-required — every licence
claim quotes a document fetched 2026-08-12 with its URL; unretrievable = NOT RETRIEVED =
treated as NO. Fetch-call counts per arm: 36 · 51 · 47 · 29 · 17. Licences here are
**documents, never verdicts**: tags describe retrieved terms; nothing in this survey is
an adoption.

**Boundary:** this survey adopts nothing and creates no licence-map rows. At adoption
time each source gets its own fresh fetch into `docs/license-map.md` per the standing
gate (entries age; >90 days advisory). Survey-grade claims are pointers, not rows.

---

## 1 · The fetched-terms path: clip and mocap libraries

| Source | Terms retrieved (2026-08-12) | Tag |
|---|---|---|
| **100STYLE** (Zenodo 8127870) | "Creative Commons Attribution 4.0 International" | **CANDIDATE** — cleanest licence on the list; 100 locomotion styles, 4M+ frames, BVH; locomotion/idle only, no dance |
| **Adobe Mixamo** | "no licensing or royalty fees, for unlimited commercial or non commercial use"; but never "distribute the raw character and animation files"; ML-training use barred | **CANDIDATE** — broad free base layer; raw files can never sit in a repo; no training use (FAQ fetch timed out; clauses cross-confirmed via Adobe community thread — re-fetch at adoption) |
| **CMU Graphics Lab DB** | "free for use in research projects. You may include this data in commercially-sold products"; "you may not resell this data directly, even in converted form" | **CANDIDATE, flagged** — direct fetch failed on a TLS cert error twice; quotes came through the search layer; the cert failure also blocks scripted download |
| **MoCap Online** | commercial use while "your project stays under 1 million end users and $1 million revenue"; binary-only distribution, no as-is resale | **CONDITIONAL** (revenue/user ceiling; the agent's summary line disagreed with its quoted clause on the user cap — the quote governs; resolve at adoption) |
| **Reallusion ActorCore** | "provide, sell, and redistribute your creations with full ownership"; but "may NOT … distribute, or sublicense the Content to any third party" | **CONDITIONAL** — baked output open, source motion files never exposed |
| **Rokoko marketplace** | free clips "including for commercial use"; platform default "you may not reproduce, distribute, sublicense … any Rokoko Asset" | **CONDITIONAL** — real grant is per-clip per publisher; diligence per clip |
| **Truebones** | "absolutely royalty free … even commercial"; no as-is redistribution | **CONDITIONAL** — no canonical EULA document located, only recurring Gumroad statements; re-verify before any adoption |
| **SFU mocap** | "The data cannot be used for commercial products or resale, unfortunately." | **BANNED-here** |
| **Bandai Namco motion dataset** | "Attribution-NonCommercial 4.0 … NonCommercial purposes only" | **BANNED-here** — a GitHub-hosted dataset that reads "open" at a glance and is not |
| **AMASS / SMPL motion archive** | "any use for commercial purposes, is prohibited"; also bars training "for commercial use of any kind" | **BANNED-here** — the admission path's namesake lesson, now quoted from its own licence page |
| **LAFAN1 (Ubisoft La Forge)** | "CC Attribution-NonCommercial-**NoDerivatives** 4.0" | **BANNED-here** — ND would bar even retargeting onto our rig |

**The trap pattern, twice measured:** research releases hosted on GitHub (Bandai,
LAFAN1) look open and are NC or NC-ND. The gate's reflex — document before download —
is the only thing that catches this class.

## 2 · The owned-factory path: video→motion, re-validated

The wall, quoted from the documents:

- **SMPL body model** (MPI licence): prohibited "to train methods/algorithms/neural
  networks/etc. for commercial use of any kind"; commercial path exists only as a paid
  Meshcapade sublicense.
- **`smplx` loader library** — not MIT despite being "just a loader": "any use for
  commercial, pornographic, military, or surveillance, purposes is prohibited."
- **AMASS pretraining** reaches through released weights independently of wrapper-code
  licence (WHAM and GVHMR confirmed AMASS-pretrained).

Consequences, per tool: WHAM / TRAM / 4D-Humans carry MIT **code** but sit on
SMPL + AMASS + smplx at runtime — CONDITIONAL at best, blocked end-to-end today.
GVHMR (non-commercial code), NIKI (no licence file = all rights reserved), TokenHMR,
Multi-HMR — **BANNED-here**. SLAHMR and PromptHMR licence texts **NOT RETRIEVED** (= NO
pending direct confirmation).

**The studio's MediaPipe chain (Apache 2.0 at all three layers, exact in-house solver)
remains the only fully-owned route surveyed.** The E09 ruling's owned-factory path
stands re-validated by exhaustion, not assertion.

SaaS lifts exist as conditional adjuncts, none owned:

| Service | Operative clause | Tag |
|---|---|---|
| Move.ai (Move One) | Move AI "owns … the Motion Data, Output"; grants back "worldwide, royalty-free … sublicensable licence"; bans using Output "to train any AI System" | **CONDITIONAL** |
| DeepMotion Animate 3D | free tier "Non-Commercial License"; paid tier "perpetual … Commercial license" | **CONDITIONAL** |
| Plask | "You retain full ownership of all User IP"; commercial use gated to the Commercial plan | **CONDITIONAL** |
| Rokoko Video · Meshcapade | operative clauses **NOT RETRIEVED** (403 / not fetched) | NO until fetched |

## 3 · Generated motion (text/audio→motion): the negative result

**No open text-to-motion or audio-to-motion route traced clean end-to-end (code +
weights + training data) as of this check.** Every HumanML3D-trained model (MDM, MoMask,
T2M-GPT, MotionGPT, …) inherits AMASS's commercial-training ban through the data;
every AIST++-trained dance model (EDGE, Bailando) inherits the AIST Dance DB's
academic-only clause — Google's CC-BY annotation layer does not launder the underlying
licence. MotionLCM, EMDM, Bailando are additionally non-commercial in their own
code/licence files. This negative is a full result: the documents, not a mood.

- **Kinetix** is the one API tagged **CANDIDATE**: "the User may exploit the Outputs for
  any purpose, including commercial use" and retains Output IP. Export format not yet
  verified — NOT RETRIEVED.
- DeepMotion SayMotion (paid tier) and Krikey ($100K lifetime revenue cap; output may
  not train other models) — **CONDITIONAL**.
- A build path exists in principle: MDM/MoMask **code** is MIT/Apache and could be
  retrained on CC-BY-class motion data (100STYLE-shaped). No released clean checkpoint
  was found. A possibility on the shelf, not a plan.

## 4 · Retargeting shelf (for whenever clips arrive)

- Blender-native BVH/FBX/glTF importers are **loaders, not retargeters** — animation
  lands on the file's own armature; cross-skeleton mapping is left to bpy or an addon.
- Scriptable candidates with retrieved licences: **Keemap** (mapping files saved to
  disk — recipe-friendly), **ReNim**, and the extensions.blender.org **Retarget** listing
  (GPL-3.0+ required by platform policy). **Rokoko's Blender addon is LGPL-3.0 — not
  MIT as a search summary claimed.** Auto-Rig Pro: GPL `.py` + separately proprietary AI
  binaries, paid, headless remap API unverified. **Expy Kit: no licence file = NO.**
- **Root/hip translation is a retargeter setting, not a clip property.** BVH gives
  translation channels only to the root/hip joint by format; Auto-Rig Pro's remap doc:
  "Setting it as Root will retarget translation + rotation, while only rotation is used
  otherwise." The same clip can arrive with traversal intact or stripped. **This is the
  exact ambiguity under the foot-instrument lever** — the instrument must read the
  representation from provenance, never assume it.
- Foot sliding is corrected by a **second IK pass after retargeting** (Epic's "Speed
  Planting": pin IK goals below a speed threshold), not by the retarget step itself.

## 5 · The provided shortlist, against documents

All four items — Phaser, Pixi.js (+GSAP), Unity 2D Sprite Library/Resolver,
Canvas-Sprite-Animations — are 2D runtime/tween/engine-tooling layers operating on
sprite sheets and property tweens. **None has an import or export path for 3D skeletal
motion; none can supply clips for a GLB rig.** Where they'd belong instead: a web
build's UI/menu layer or a 2D game runtime.

Licence terms as fetched: Phaser MIT ("…and/or sell copies") · **Pixi.js MIT — the
search summary's "BSD-3" was wrong** · GSAP free ("GSAP is now 100% free for all
users") **with a named carve-out** (no use in no-code animation builders competing with
Webflow) that the summary elided · Unity free tier to a $200,000 trailing-12-month
revenue/funding threshold (Unity's own terms page 403'd; figure grounded via a
secondary market page + concurring search results — re-fetch at adoption if ever
relevant) · Canvas-Sprite-Animations (IceCreamYou repo) MIT.

Two live divergences between search-engine verdicts and fetched documents, on a
four-item sample — the documents-never-verdicts law earning its keep on this very
request.

## 6 · Design implications (each tied to a finding above)

1. **The library's provenance schema needs per-clip licence columns**: source, licence
   URL, fetch date, commercial grant, **redistribution class** (raw-file shippable vs
   baked-only), and **ML-training rights** (Mixamo bars training; Move.ai and Krikey bar
   training on outputs) — because the reach-through question will be asked of our own
   library one day. (§1, §2, §3)
2. **Raw external clips never enter git** — nearly every CANDIDATE/CONDITIONAL source
   bars raw redistribution; external clips are a baked-performance tier. Rhymes with the
   standing big-binaries rule. (§1)
3. **Publishable-by-construction remains the owned factory's property alone** — the
   external paths add coverage, never ownership. (§2, E09 ruling)
4. **The foot instrument reads hip-translation representation from provenance** — it is
   a retargeter setting, not a clip fact. (§4)
5. **Adoption ritual unchanged**: licence-map row from a fresh fetch BEFORE the first
   clip downloads, per source, every time — this survey does not substitute. (E09; §1's
   trap pattern)

## 7 · Verification state and residual debt

Every claim above was retrieval-grounded by the agent that made it, with per-arm fetch
counts recorded; two search-summary divergences were caught by document fetch (§5) and
one by licence-file fetch (Rokoko addon, §4). **NOT RETRIEVED this session (= NO until
fetched):** Rokoko Vision terms (403) · Meshcapade platform ToS · SLAHMR and PromptHMR
licence texts · Truebones' canonical EULA · CMU by direct fetch (TLS cert failure) ·
Kinetix export format · Adobe's own FAQ page (timeout; clauses cross-confirmed via an
Adobe community thread). Each is a re-fetch away; none blocks anything until an
adoption names it.
