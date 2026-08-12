# Video-provider field notes — Kling · MiniMax H3 · Seedance (lead sheet)

**Provenance.** Retrieved by the Director on 2026-08-12 as
`Video_AI_Provider_Guides_Comprehensive.md` — an **AI-consolidated aggregation** citing
third-party blogs, vendor marketing pages, one news outlet, a YouTube video and an
Instagram reel. **Source tier: LEAD SHEET.** Nothing in it is a document for the
licence gate; every load-bearing claim needs its own retrieval before anything relies
on it. It covers exactly the three providers whose terms rows sit blocked in
`docs/license-map.md` (Kling HTTP 446 · MiniMax JS-rendered · Seedance no-AI-clause),
which is what makes the leads worth keeping.

**One claim already corrected against its primary source (2026-08-12):** the document
states MiniMax H3 "is distributed as an open-weights asset capable of running locally
inside ComfyUI via INT8/INT4." MiniMax's own announcement (minimax.io/blog/minimax-h3,
dated 2026-07-31) says only: **"we plan to open up the model weights in the coming
days, subject to applicable laws and regulations"** — announced intent, **no licence
named, no variant split documented.** Whether weights have actually shipped since
2026-07-31, and under what licence, is unverified. The document's INT8/INT4 detail may
also be conflated with unrelated runtime features. Treat "H3 open-weights local" as a
**watch item**, not a fact.

## Cross-checks against this repo's own measurements

| claim | our measurement | verdict |
|---|---|---|
| H3 omni-reference: up to 9 images + 3 videos + 3 audio | `video_minimax_h3_r2v` template description, consult #8 catalog sweep: "up to nine images, three videos, and three audio clips" | **CORROBORATED** (the doc adds a 12-file cumulative cap and a 15 s/clip audio cap — plausible, unmeasured by us) |
| Seedance 2.5 accepts "up to 50 multi-modal reference assets" | `api_seedance2_5_r2v` template, same sweep: "up to 20 images, 6 video clips, and 6 audio clips" | **DISCREPANCY** — 50 vs 20/6/6. Possibly Dreamina-app surface vs Comfy-template surface; unresolved, recorded, neither number trusted past its own surface |
| H3 open-weights local | vendor's own blog: intent only, 2026-07-31 | **CORRECTED** (above) |

## Per-provider distillation (as the document claims — lead tier throughout)

**Kling (1.5–3.0 Elements).** Five-part segmented prompt (subject / action / camera /
lighting / render style), verb-first action language, **2,500-character API prompt
cap** (silent truncation beyond it). Claims: native 4K via cloud upscaling; an
**"Elements 3.0" asset library with local character-dataset training via LoRA** — an
identity-lock lead in the same product territory as Wan's r2v tier; ~10 credits/1080p
vs ~40/4K per invocation; "paid subscriptions strip watermarks and grant full IP
rights" — a **verdict-class claim** that only the Kling terms document can ground (the
map's row remains blocked; fresh lead URL: kling.ai/blog).

**MiniMax H3 / Hailuo.** `@`-anchor reference tags (`@Image1 represents the hero…`) —
the same identifier-binding family as Wan r2v's `characterN`; quoted dialogue tied to
anchors invokes speech; audio references reportedly degrade past ~8 s (community
benchmark tier — drop audio anchors when tracking drifts). Claims "thin refusal walls"
and watermark-free paid tiers — terms document still unfetched (lead: hailuoai.video).

**Seedance (1.5–2.5 / Dreamina).** Text-semantic layer separated from **physical
motion maps** (bounding-box paths, optical-flow inputs, brush-drawn trajectories) — a
spatial-control-shaped surface worth a catalog check if Seedance ever reaches a brief.
Version branching: 1.5/2.5 tuned for humans/faces/cloth, 2.0 for environments and
mechanics. **2026 guardrails (news-sourced, Deadline): real-face uploads blocked;
Hollywood-IP prompts refused; C2PA metadata and permanent AI labels baked into every
output.** The C2PA point is load-bearing for published studio art if Seedance is ever
considered — a Director-level consideration recorded now so it is not discovered at a
spec. Third-party hosting pricing quoted up to $0.682/s at 1080p (fal.ai, lead tier).

## What this feeds, and what it does not

- **The three blocked map rows gain fresh fetch targets** (recorded here, rows
  unchanged): kling.ai blog/terms · hailuoai.video · the Deadline Seedance piece ·
  minimax.io/blog/minimax-h3. The Director's browser-export path remains the cure for
  JS-walled pages.
- **E13 peer context:** if the composed route ever graduates past its probe, H3-r2v
  and Seedance-r2v are the measured-on-catalog peers, and H3's `@`-anchor grammar is
  the closest sibling to `characterN`. The doc's prompt formulas join the prompting
  shelf at the same advisory tier as the Wan guide notes.
- **The H3 watch item:** if H3 weights actually ship under a fetchable licence, an
  open-weights reference-video tier would sit better with this map than any partner
  tier — "every verified-clean row is open weights" is the map's own observed shape.
  Watch, verify, then row — in that order.
- **Nothing gates on this document.** No adoptions, no rows, no spec changes. E12 and
  E13 are untouched.
