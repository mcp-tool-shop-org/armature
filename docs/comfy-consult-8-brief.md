# Comfy Agent consult #8 — the Wan reference-to-video tier (the @-tag mode's API surface)

**From:** the armature advisor seat, 2026-08-12 · **Relay:** the Director carries this
brief to the Comfy Agent and returns its answer · **Trigger:** the Director's direction
to look into the `@`-tag identity-lock mode the official Wan guide documents (Wan
2.6+ "Starring Role / Reference Video"), which is a **new conditioning tier** — the
standing trigger for a brief · **Numbering:** file series (01, 3, 5, 6, 7 → 8).

**Round shape: knowledge only.** No tabs, no graph building, no generations, no credits
this round. Catalog facts and licence **documents** only — never licence verdicts; the
ruling is ours. UNVERIFIED = NO stands.

---

## Context — why this tier reached a brief

armature's product is one persistent main character in model-painted footage. The
official Wan guide documents an identity-lock mode (`@Character` tags, references held
consistent, dialogue-driven). We measured its API surface on Cloud ourselves today
(table below): it exists as core partner nodes for **wan2.6-r2v** and **wan2.7-r2v**,
where the app's `@`-tags become `character1` / `character2` **identifiers in the prompt
string**. The open questions are the tier's spatial contract (armature authors
everything spatial — what survives here?), its terms, and its price.

## Already verified or measured TODAY — do not re-derive (calibrate against it)

| item | state |
|---|---|
| `WanReferenceVideoApi` (core, api_node): model `wan2.6-r2v`; **reference_videos** (auto-grow, required); prompt tooltip: "Use identifiers such as `character1` and `character2`"; character AND voice consistency; sizes as exact pixel pairs (720p/1080p × 5 ratios); duration 5–10; seed 0–2147483647; `shot_type single\|multi`; watermark boolean, default false | measured via `get_node`, 2026-08-12 |
| `Wan2ReferenceVideoApi` (core, api_node): model `wan2.7-r2v`; **reference_images.image1–image5** AND **reference_videos.video1–video3** (both optional, auto-grow); same identifier convention; 720P/1080P; ratio combo; duration 2–10; seed; watermark default false; "person or object … single-character performances and multi-character interactions" | measured via `get_node`, 2026-08-12 |
| Sibling 2.7 nodes served: `Wan2TextToVideoApi` (`wan2.7-t2v`), `Wan2VideoEditApi` (`wan2.7-videoedit` — edit a video by text/reference/style) | measured via `search_nodes`, 2026-08-12 |
| Template `api_wan2_6_i2v` (Wan2.6 image-to-video, 1080P support) exists; a `wan2.6-i2v` line item billed on this workspace in July | template search + usage report, 2026-08-12 |
| Runtime changelog (docs.comfy.org/changelog, top version **v0.32.0**, 2026-08-11): **v0.31.0** "Native Wan-Animate2 with pose/reference controls and optional pose-branch cache"; **v0.29.0** "Uni3C ControlNet support for Wan models" | fetched 2026-08-12; the changelog is now a standing field-check source (the Director's pointer) |
| Licence map state: Wan 2.1/2.2 families Apache with rows; **no row exists for any Wan 2.6/2.7 variant** — UNVERIFIED = NO until documents are fetched | the map, 2026-08-12 |
| The DingTalk guides (video + 2.6 image) are distilled in-tree: `docs/wan-video-prompt-guide-notes.md`, `docs/wan26-image-guide-notes.md` | 2026-08-12 |

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Confirm `Wan2ReferenceVideoApi` currently
serves model option `wan2.7-r2v` with `model.reference_images.image1…image5` slots and
duration 2–10. We hold this from today's `get_node`; state any drift you see, and if you
see none, say so in one line.

**Q1 — the tier's spatial contract (the load-bearing question).** On `wan2.6-r2v` /
`wan2.7-r2v`, does ANY spatial conditioning exist — a start/first frame, camera control,
pose or driving input — or is composition wholly model-decided? Can r2v compose with any
camera-control mechanism at current catalog state (including the Uni3C tier from
v0.29.0)? Exact node/template names as saved, only what you can see served.

**Q2 — the identifier contract.** How do `characterN` identifiers bind to uploads
(order? one identity per reference? images and videos mixed for one character?). Any
stated character-count limit (the app guide says two). Anything the platform documents
about non-photoreal / stylized character references.

**Q3 — the terms surface (documents, never verdicts).** The exact URLs of the terms
documents visible from the platform for the Wan partner tier — Comfy's ToS
ownership/usage clauses and any Alibaba/DashScope terms it links for wan2.x partner
generations. Do not summarize their meaning; give locations and titles.

**Q4 — price.** The per-generation pricing signal for `wan2.6-r2v`, `wan2.7-r2v`, and
`wan2.6-i2v` — 720P/5s versus 1080P/10s — as the platform displays it (or
`estimate_credits` output if that is what you can see).

**Q5 — the changelog's two Wan items, for the shelf.** For native **Wan-Animate2**
(v0.31.0) and **Uni3C** (v0.29.0): exact served node names, the weight files they
require (our Gate PAIR needs conditioning-class ↔ weight-family pairings), and any
licence/provenance visible for Uni3C weights specifically.

## Halt conditions

Answer what the catalog and visible documents support; mark anything else NOT VISIBLE.
No speculation, no substitutions of "equivalent" models, no licence rulings. If a
question would require building or running anything, stop at naming what it would take.
