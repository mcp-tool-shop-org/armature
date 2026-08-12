# Wan 2.6 image guide — distilled notes (Director-retrieved DingTalk export)

**Provenance.** Retrieved by the Director on 2026-08-12 as a Markdown export
(`Wan 2.6-Image Creation Guide.md`) of the official Wan 2.6 image documentation on
DingTalk (`alidocs.dingtalk.com`) — the same document family as the still-unfetched
official **video** prompt guide. This is the **image** sibling: text-to-image plus
image-edit guidance. The export path that produced this file is the first working route
into that family; the video sibling remains the open admin-shelf item.

**Scope and admission.** Wan 2.6 is a newer family than the 2.2 tiers our routes run,
and **no Wan 2.6 variant has a licence-map row**. The family-splits law applies: nothing
here is admission. Before any armature generation on 2.6 (it is live on Comfy Cloud —
a `wan2.6-i2v` line item billed on this account in July, pre-armature): licence/terms
row per the exact variant, and partner output-ownership terms before the first credit.
These notes are knowledge, not a route.

## Text-to-image (part 1 of the export)

- Formula: `[Subject Description] + [Style Setting] + [Detail Requirements] +
  [Visual Atmosphere] + [Resolution/Ratio]`.
- A large style prompt bank follows (photography/lens/lighting language, painting
  styles, 3D/CG, scene and environment design, posters with legible text, multi-panel
  storyboards). **Quality note:** the bank is a mixed cookbook — a number of its
  entries are plainly video prompts ("optimized for immersive video generation",
  camera-move-at-24fps language) sitting in the image bank. Treat entries as patterns,
  not gospel.

## Image edit (part 2 — the load-bearing half for this repo)

The edit grammar, as the document states it:

- **Directive edits:** `[Edit command] + [Edit object]` — eliminate / add / modify /
  replace / reference; drift in untouched regions is countered by appending
  **"keeping XX unchanged"**.
- **Lens and light control on an existing image:** zoom in/out; close-up / wide /
  overhead; **generate front, side and back views of a subject**; day/night, weather,
  warm/cold tone, add/remove sunlight — stated as consistency-preserving.
- **Multi-picture reference:** `[picture as subject/background] + [reference method] +
  [command]` — fusion ("the boy in Figure 1 … in the scene in Figure 3"), reference
  (pose / material / style taken from another image), replacement.
- **Scene re-dress on a figure:** "replace the background with a brightly lit
  ballroom … warm golden lights naturally sprinkled on the characters" — background
  replacement with light harmonization onto the subject.
- **Line-draft rendering:** "color the line draft and turn it into a professional and
  real scene map" (architecture/interior demos).
- Also present: text editing inside images, style transformation, cutout-to-transparent,
  detect/segment.

## Untested connections to the standing levers (knowledge only; every one needs a spec,
a licence row, and the Director's word before anything runs)

1. **The scene-bearing start frame** (the camera-tier lever, w3's direct answer). The
   ruled mechanism is the deterministic alpha-law composite — our authored RGBA render
   over a real bar plate. This grammar adds candidate mechanisms at the PLATE stage:
   generating a bar plate (T2I scene design), or **relighting/harmonizing** a composite
   after the deterministic paste. UNTESTED here.
2. **A fork to surface, not decide:** multi-picture fusion ("character from Figure 1 in
   the scene of Figure 2") is a **generative** composite — the model repaints the
   character's pixels at the image stage. The alpha law exists because authored pixels
   are the identity anchor. Whether any generative composite is ever admitted for a
   start frame is the Director's route call, contrastively surfaced, never a default.
3. **Previz → plate:** line-draft rendering rhymes with E06 (reference onto schematic) —
   a staged Blender scene render as the "draft" a real plate is derived from, keeping
   authored geometry in charge of composition. UNTESTED; would need its own arms.
4. **"Keeping XX unchanged"** is the document's own identity-preservation reinforcement;
   if an edit path is ever specced, that clause pattern rides in the prompt design.
5. Front/side/back view generation of a subject touches turnaround territory — facet's
   lane, noted for the twin's pipeline rather than armature's.

## What this document is not

Not the video prompt guide (the admin shelf item stays open — the video sibling lives
in the same DingTalk space this export came from), not a licence, and not a measured
armature result. Wan 2.1 video-prompt notes: `docs/wan21-prompt-guide-notes.md`.
