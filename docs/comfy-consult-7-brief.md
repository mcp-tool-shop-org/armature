# Comfy Agent consult #7 — narrating a scene: directing time via prompt or node

**From:** the armature advisor seat, 2026-08-12 · **Relay:** the Director carries this brief
to the Comfy Agent and returns its answer · **Trigger:** the Director's direction — find the
ways a scene can be *narrated*: its unfolding directed over time, within a shot and across
shots, by prompt or by node · **Numbering:** the brief file series (01, 3, 5, 6 → 7); the
licence map separately cites a brief-less 2026-08-10 round as consult #7 — the file series
is what this number tracks, as recorded since brief #6.

---

## Context — what the studio is doing, and what "narrate" means here

armature puts one persistent character (a rigged GLB the studio owns) into model-painted
footage on Comfy Cloud. Two pipelines are live: a **driven route** (rig-rendered AAPose
sticks → `WanAnimateToVideo`, reference + prompt carrying identity and scene) and a
**no-control route** now being probed (a GLB-authored start frame → Wan 2.2 I2V, the model
generating all motion and scene). Shots are 65–81 frames at the Wan horizon, 832×480,
everything licence-mapped (Wan family Apache; core nodes; **a served template is a
reference, never a route**).

**"Narrate" means directing a shot like a director**: he enters frame, crosses to the bar,
orders; the bartender turns; the light warms; the crowd reacts — beats unfolding in order
inside one clip, and continuity of scene and story across chained clips. Today the studio
has ONE static prompt per generation and has measured its limits: on the Animate route
motion dominates text by design; scene composition under identical text moves wholesale
with the seed (our two-seed rule); the default negative suppresses background people.

**Licence gate, unchanged:** no non-commercial anything, UNVERIFIED = NO. **Do not rule
licences** — exact names, versions, and the URL of any licence document you can see; the
ruling is ours.

## Already verified or measured — do not re-derive

| item | state |
|---|---|
| Wan 2.2 T2V / I2V / Animate-14B weights · umt5 · Wan 2.1 VAE | licence-mapped Apache, commercial YES |
| ComfyUI core node code | GPL-3.0 fetched; narrow output clause; hosted execution |
| `WanAnimateToVideo` sockets incl. `continue_motion`, `continue_motion_max_frames`, `video_frame_offset` (chunked extension) | measured from schema + served tooltip |
| Motion-dominates-text on the Animate route; default negative excludes background crowds; scene composition is seed-volatile under identical text | measured, E08/E10 |
| "Wan Animate 2" (text-driven viewpoint control per its paper) and SCAIL-2 | UNVERIFIED = NO in our map — catalog knowledge about them is welcome; use enters only through licence rows |

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Which core conditioning-composition nodes are
served — `ConditioningCombine`, `ConditioningConcat`, `ConditioningSetTimestepRange`,
`ConditioningSetAreaStrength` or their current equivalents — and, precisely: on the Wan
video routes, does `ConditioningSetTimestepRange` partition **denoising steps** or **video
time**? *(We hold the schema answer from our own catalog access; this is the round's
cheap-verification anchor, and the denoise-time-vs-video-time distinction is the mechanism
this whole consult turns on.)*

**Q1 — narration WITHIN one clip, prompt-side.** What exists on Cloud to schedule text over
a single video generation: prompt-travel / prompt-scheduling nodes that work on the Wan
routes; per-segment or per-frame conditioning mechanisms that map to **video time** (not
denoise time); first/last-frame conditioning (`WanFirstLastFrameToVideo`) used as
beat-endpoint control; anything that lets "first A, then B, then C" actually land as A→B→C
in the output. For each: exact node/template names as saved, what it pairs with, and
whether it is core or a custom pack (pack name — licence document URL if visible).

**Q2 — narration ACROSS clips: chaining as storytelling.** The known machinery:
`continue_motion` chunk-extension on Animate, and last-frame→next-start-frame chaining on
I2V. The questions: (a) can each chunk carry a **different prompt** (that is a beat
structure); (b) what does the catalog hold that is *built* for sequential/extended
generation (video-extend templates, storyboard-ish workflows) — names as saved; (c) known
failure modes of chaining (drift, color shift, identity loss per hop) as the field
currently understands them — mark SPECULATION where it is not measurable from the catalog.

**Q3 — camera direction.** What camera-move control exists on the Wan stack: documented
prompt conventions the models actually honor (dolly / pan / orbit language — what does the
official prompting guidance say); camera-control LoRAs or nodes in the catalog (exact
names + base-model pairing + licence document URL — a LoRA inherits its base's licence but
carries its own too); and anything text-driven-viewpoint-shaped that is NOT the unverified
Animate-2 route.

**Q4 — holding the set while the beats move.** Mechanisms to keep the SCENE constant while
action changes: scene reference images (the VACE reference channel; `background_video` on
Animate; the I2V start frame as a set anchor); regional/spatial prompting on video routes
(does anything served do region-scoped text on Wan?); and population control — beyond
editing the default negative, does Wan honor emphasis/weighting syntax, and is there a
served mechanism for "this many people, here"?

**Q5 — the prompting guide itself.** What does the current official Wan prompting guidance
actually say about narrative structure: sequential-action language, recommended prompt
length and structure, negative-prompt discipline, and anything about multi-sentence
temporal ordering. Quote or link the guidance; where the guidance is silent, say so plainly
rather than extrapolating.

**Q6 — recommendation.** Rank the narration mechanisms that appear clean under our gate for
the two live routes, cheapest-to-try first. Then, per the calibration protocol, close with
**one cheap, checkable claim** we can verify locally before acting on anything expensive.

## Answer format requested

Q0 first. Exact names as saved in the catalog — named nodes and templates are not
substitutable. Mechanism over inventory: what pairs with what, and which timeline
(denoise vs video) each mechanism lives on. Anything uncertain is marked SPECULATION.
Deviations from the questions, listed at the top. Licence documents, never verdicts.

## Standing rules (abbreviated — this is a question brief, not a build order)

No builds, no tab creation or mutation, no workflow edits, no generations. This round
spends nothing.
