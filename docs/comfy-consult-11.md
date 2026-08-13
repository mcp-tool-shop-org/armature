# Comfy Agent consult #11 — answer, calibration, ruling

**No brief file this round.** The Director ran the question directly with the agent and
relayed the exchange to the advisor seat for ruling, 2026-08-13. Subject: whether a
licence-safe, locally-available workflow can take a GLB and map out the shots for a
2.5D sprite — raised as a side capability, one more consumer of a GLB, explicitly not
the repo's main line — plus one completing question from the seat on Load3D camera
serialization. Round discipline held: knowledge only, zero credits, nothing adopted,
documents never verdicts.

The scope note, stated so the record cannot drift: this consult narrows nothing.
armature remains footage from a scene you own; a still shot-set is one more consumer
of the staged scene, not a new product line.

---

## The agent's findings (their catalog surface, two messages)

**Round 1 — the workflow question.**

> The local core catalog has exactly one node that renders a mesh to an image —
> **Load3D** (and its sibling Load3DAdvanced). Its camera is driven by the interactive
> 3D viewport widget, not by a wired `camera_info` input. The
> CreateCameraInfo → `camera_info` signal is accepted only by Preview/Save-3D nodes
> and by the splat renderer (RenderSplat, which needs a SPLAT, not a mesh). There is
> no headless "render this mesh from angle N" node locally; a wired multi-angle sweep
> exists only for splats, which would mean converting the GLB first — a different
> pipeline.
>
> Draft graph (committed to canvas as a draft, 5 nodes / 4 links, all core `3d` /
> `image` / `image/mask` categories, `partner_nodes` empty): Load3D →
> SaveImageAdvanced ×3 — beauty (`sprite/beauty`), normal (`sprite/normal`), mask via
> MaskToImage (`sprite/mask`) — PNG, 512×512.
>
> Shot map offered: the classic 8-direction set — yaw in 45° steps at one locked
> downward pitch (≈30°), orthographic projection so scale is constant across the
> sheet, power-of-two cells, beauty + mask (+ normal for dynamic 2.5D lighting) per
> view. Props often need only 4 directions; an animating character wants all 8.
>
> The manual step, disclosed plainly: because the camera is a viewport widget, each
> angle is hand-set in the Load3D viewer and the graph re-run per angle.

**Round 2 — the seat's completing question** (does the viewport camera pose serialize
into the saved workflow JSON: (a) does a saved graph re-render the identical angle
with no re-posing; (b) can the pose be set by editing the JSON directly?).

> **The schema fact stated with certainty:** Load3D declares the camera as node
> **state**, not as a link — the `image` input is typed `LOAD_3D` (the viewport
> widget) and the pose is a widget-state property of the node, the same class of
> thing as width/height, not an ephemeral render-time value.
>
> **Clause (a):** the mechanism for "authored once, recorded thereafter" is present —
> widget/property state is the class ComfyUI serializes on save. But whether the SAVE
> path writes the full pose (azimuth, pitch, distance/zoom, target, FOV) at fidelity,
> and whether LOAD re-hydrates it into an identical render, is round-trip behavior
> the catalog does not document. **NOT VISIBLE: the serialized field set and its
> round-trip fidelity.** Under the shop's standing law, UNVERIFIED reads NO until a
> save/reload byte-check confirms it.
>
> **Clause (b):** if the state serializes, the edit target is the Load3D node
> object's own properties / widget-values block in the workflow JSON — not the links
> array, and not the `camera_info` wire (an output that only carries the pose
> downstream). Exact key names, and human-editable floats versus an opaque blob:
> **NOT VISIBLE** without an empirical save-and-inspect.
>
> **A correction owned against the earlier message:** the round-1 note said the
> `image` input is "populated by loading the mesh in the UI." The schema splits
> that — `model_file` is the mesh combo; `image`/`LOAD_3D` is the viewport-and-camera
> state. The pose, if it serializes, lives in the latter.

## Calibration at ruling time (the advisor's own measurement, 2026-08-13)

| check | result |
|---|---|
| Load3D full schema via our uncapped `get_node` (single-name query per the #10 `LoadImage` trap) | **The load-bearing claim CONFIRMED on our instrument:** inputs are exactly `model_file` (COMBO), `image` (`LOAD_3D`), `width` (INT), `height` (INT) — **no wired camera input exists on the node**. `LOAD3D_CAMERA` appears only among the eight outputs (IMAGE, MASK, STRING, IMAGE, LOAD3D_CAMERA, VIDEO, FILE_3D, LOAD3D_MODEL_INFO), matching the agent's output inventory item for item. Core pack, category `3d`. |
| Surface note | The agent read a **local install**; our measurement is the **cloud catalog's serving of the same core pack**. The schema shape matched across the two surfaces. Round-trip serialization fidelity is measurable only on a local install and stays NOT VISIBLE from both surfaces — the two instruments agree about where their shared boundary is. |

Channel note: NOT VISIBLE boundaries marked unprompted, and a mid-round self-correction
owned without being asked — the channel behaving as designed.

## Ruling

1. **Reference, not route.** The canvas draft stays where it is; nothing adopts it. A
   hand-orbited viewport camera is the same disease as a live-GUI Blender session —
   artifacts with no recorded parameters — and a recipe that does not reproduce its
   output is not a recipe. Eight hand orbits also cannot hold exact 45° steps, matched
   pitch, and constant subject scale, and angular consistency is the property a
   directional sheet lives on.
2. **The catalog knowledge is banked:** the local core catalog has no headless
   mesh-camera render; the wired-camera path is splat-only; the Load3D camera is node
   state — the serializable class of thing — with round-trip fidelity NOT VISIBLE.
   Mechanism plausible; fidelity UNVERIFIED = NO under the standing law.
3. **The capability already lives on this shelf, headless and recorded:**
   `tools/render_turnaround.py` (N-view orbit, exact azimuths from `--views` /
   `--sweep`, `--elevation` pitch, radius solve holding subject height constant across
   views, RGBA under the alpha law, Gate ALPHA per view, provenance JSON recording
   every camera parameter — the kit the Director passed at S03), `tools/stage_render.py`
   (depth / normal / mask / edge passes), and the `sheet_compose` family for assembly.
   The one sprite-specific gap is **orthographic projection** — `render_turnaround`'s
   camera is lens/sensor perspective. Named as a candidate small instrument spec
   (S-series, zero credits, no new licence surface) on the Director's word; **not
   dispatched by this consult**. Until then, long-lens perspective is the stated
   approximation.
4. **Sequencing:** geometry, mask, and normal passes are indifferent to texture state;
   beauty-pass sprite quality inherits the texture, so painted-sprite output sequences
   behind facet's texture-hole repair — the studio's standing top priority.
5. **Licence surface: nothing adopted, so no licence-map rows are created**, and the
   draft's "all core nodes, clean" claim never became load-bearing. If this path is
   ever adopted, rows are fetched then, and the `camera_info`-consumability claim
   (Preview/Save-3D and RenderSplat only) — the one finding this round that neither
   instrument re-measured — is re-measured on ours before anything gates on it.
6. **The settling experiment is named, trigger-only, not scheduled:** save a posed
   Load3D graph, inspect the JSON for readable pose fields, reload, byte-check the
   re-render. It runs if and when the Comfy mesh path's standing ever matters, and it
   joins the channel's standing next-brief triggers as exactly that.
