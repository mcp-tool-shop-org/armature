# The instruments — every `tools/*.py`, by how it runs

Generated 2026-09-06 from each module's own first docstring line on `ea64b18` (76 tools: 55 CPython, 21 Blender-side). A tool that imports `bpy` runs only inside Blender, headless: `blender -b -P tools/<name>.py -- <args>`; `python tools/<name>.py` on one of those fails with `ModuleNotFoundError: No module named 'bpy'`. Every other tool runs on the repo venv: `python tools/<name>.py --help`. Regenerate this page from the docstrings rather than editing a row by hand — a row that drifts from its module is worse than no row.

Every tool under `tools/` answers for itself: `python tools/<name>.py --help` prints what it does, and for the four that spend or gate a spend — `build_r2v_payload`, `build_lora_arm_payload`, `gate_saved_graph`, `canon_gate` — an epilogue naming the route and what a refusal costs. Five instruments parse `--key=value` by hand rather than through argparse — `stage_render`, `make_sheet`, `analyze_p3`, `rig_sheet_compose` and `sheet_compose` — so `--help` is not a route they serve; each refuses an unknown token by name and prints its own flag set in the refusal, and every other instrument's `--help` opens with one sentence saying what the tool does and carries text on every flag (measured on the Stage C amend: instruments-measure 36 parsers / 36 descriptions, 253 flags / 253 help strings; builders 13 / 13 and 103 / 103; instruments 20 parsers with a description, 83 flags gaining help).

## CPython instruments (`python tools/<name>.py --help`)

| tool | what its docstring says |
|---|---|
| `analyze_p3.py` | analyze_p3 — the sign and shape of the normalization difference. |
| `armature_index.py` | armature_index - armature's binding of the shared record index. |
| `build_animate_payload.py` | build_animate_payload — E08's `WanAnimateToVideo` graph, built in this repo. |
| `build_assembly_payload.py` | build_assembly_payload — the frames->VIDEO chain, built in-repo. S03 Task C. |
| `build_camera_i2v_payload.py` | build_camera_i2v_payload — E11's camera-held graph, built in this repo. |
| `build_cascade_payload.py` | build_cascade_payload — the frames->VIDEO chain, batched in a cascade. E13 re-arm, Stage 0. |
| `build_i2v_payload.py` | build_i2v_payload — E11's `WanImageToVideo` graph, built in this repo. |
| `build_lora_arm_payload.py` | build_lora_arm_payload — E14's bake-off arms, built in this repo from E12's pinned graph. |
| `build_payload.py` | build_payload — assemble a submission, with the gates that must fire first. |
| `build_r2v_payload.py` | build_r2v_payload — the composed route's graph, built in-repo. E13's re-arm. |
| `build_t2v_payload.py` | build_t2v_payload — E09 B2's graph, built in-repo from pieces the licence map covers. |
| `canon_gate.py` | canon_gate — resolve, cover, spend-check. Nothing here submits. |
| `compare_runs.py` | compare_runs — G3's instrument. Compares two run directories **pixel by pixel**. |
| `composite_reference.py` | composite_reference — authored RGBA masters into the RGB plates a hosted tier receives. |
| `encode_control.py` | encode_control — build the control video and prove the bridge is lossless. |
| `extract_clip_frames.py` | extract_clip_frames — a generated clip to lossless per-frame PNGs, with its stream facts. |
| `fetch_run.py` | fetch_run — turn a get_output dump into a run directory on disk. |
| `fetch_t2v_run.py` | fetch_t2v_run — a get_output dump for the in-repo T2V graph, onto disk, in ORDER. |
| `fit_reference.py` | fit_reference — put a reference image into a generator's frame without losing the figure. |
| `gate_b_frames.py` | gate_b_frames — did the driving signal reach the model exactly as it was drawn? |
| `gate_saved_graph.py` | gate_saved_graph — run admission on the SAVED file, and compare it to what we built. |
| `invert_frames.py` | invert_frames — write the near-dark polarity of a rendered control channel. |
| `lift_clip.py` | lift_clip — a generated clip through the detector and the solver. No ground truth. |
| `make_ab_clip.py` | make_ab_clip — two clips at their OWN true tempos, side by side in one file. |
| `make_cast_sheet.py` | Cast-survey sheet: one row per subject — full 3/4 front, full back, head front, |
| `make_crop_strip.py` | make_crop_strip — named native-resolution crops across frames, in one strip. |
| `make_e08_sheet.py` | make_e08_sheet — the Gate 0 sheet: previz \| control \| output \| reference \| provenance. |
| `make_e13_sheet.py` | make_e13_sheet — the composed route's panel: references \| output \| provenance. |
| `make_gate0_sheet.py` | make_gate0_sheet — the control \| output \| reference \| provenance panel. |
| `make_hole_survey.py` | make_hole_survey — the old turnaround beside the new one, per view, at full size. |
| `make_identity_sheet.py` | make_identity_sheet — put the candidate reference plates beside the mesh. |
| `make_lift_sheet.py` | make_lift_sheet — source \| what the detector saw \| the rig performing the lift. |
| `make_overlay_sheet.py` | make_overlay_sheet — the pose sticks composited onto the render they claim to describe. |
| `make_pick_sheet.py` | make_pick_sheet — Gate PLATE's instrument: candidate plates, side by side, for the eye. |
| `make_plate.py` | make_plate — turn a picked still into the plate that stands behind the performer. |
| `make_review_clip.py` | make_review_clip — the motion review, and the stills where structure is hardest. |
| `make_sheet.py` | make_sheet — the panel the Director reads the run off. |
| `make_shotset_sheet.py` | make_shotset_sheet — the ortho shot-set as a sheet, and beside its perspective sibling. |
| `make_startframe_sheet.py` | make_startframe_sheet — Gate 0 for a route whose only conditioning is one image. |
| `make_thesis_sheet.py` | make_thesis_sheet — control vs controlled-output vs no-control-output, one panel. |
| `make_zoom_sheet.py` | make_zoom_sheet — native-resolution crops where structure is hardest, with their boxes. |
| `measure_arm.py` | measure_arm — where is the arm, frame by frame, in image space. |
| `measure_cascade_clip.py` | measure_cascade_clip — decode a cascade-assembled clip and compare it to its sources. |
| `measure_clip.py` | measure_clip — the numbers a generated clip can be quoted by. |
| `measure_floor.py` | measure_floor — the provider's repeat variance, per frame index. |
| `measure_lift.py` | measure_lift — the detector, then the solve, then the numbers. In that order. |
| `measure_smoothness.py` | measure_smoothness — how big a step the driving signal takes, per keypoint, per frame. |
| `measure_tracking.py` | measure_tracking — the timing-correlation statistic, as an instrument. |
| `pack_pose_pack.py` | pack_pose_webp — the pose-stick frames as ONE lossless animated WebP. |
| `project_pose_keypoints.py` | project_pose_keypoints — the rig's AAPose-20 keypoints, per frame, in pixels. |
| `render_pose_sticks.py` | render_pose_sticks — the AAPose-20 driving frames, drawn to the pinned Wan convention. |
| `resample_motion.py` | resample_motion — the same dance, more in-betweens. |
| `rig_sheet_compose.py` | rig_sheet_compose — assemble the panels `make_rig_sheet.py` rendered into the sheet. |
| `sheet_compose.py` | sheet_compose — assemble rendered panels into a dailies sheet. |
| `stage_render.py` | stage_render — the control-sequence exporter. |

## Blender-side instruments (`blender -b -P tools/<name>.py -- <args>`)

| tool | what its docstring says |
|---|---|
| `author_walk.py` | author_walk — E08's commission: the performance, keyed onto E07's skeleton. |
| `check_relift.py` | check_relift — is a re-solved lift the same performance as the pinned one? |
| `diagnose_bone_heat.py` | diagnose_bone_heat — why `ARMATURE_AUTO` produced no weights on the E07 subject. |
| `lift_solve.py` | lift_solve — key a solved lift onto the performer's rig and write a GLB. |
| `make_binding_sheet.py` | make_binding_sheet — arm (a) beside arm (b), for the Director's eye to pick the binding. |
| `make_parts_sheet.py` | make_parts_sheet — the dailies sheet for E07 arm (c), the rigid-parts armature. |
| `make_rig_sheet.py` | The arm (d) comparison sheet — a SKINNED figure, judged beside the mesh it replaced. |
| `make_skeleton_sheet.py` | make_skeleton_sheet — the Director's skeleton-approval sheet. |
| `make_test_armature.py` | Generate the wire-armature test subject — the instrument, not a character. |
| `preview_glb.py` | Headless GLB preview: import, measure, render 2 full views + 2 head crops. |
| `preview_walk.py` | preview_walk — a shaded pass at the shot camera, so the walk can be LOOKED at. |
| `probe_glb.py` | probe_glb — measure what a GLB actually contains. Reads only; writes only JSON. |
| `probe_subject.py` | probe_subject — open a GLB and report what it is. Reads only; writes only JSON. |
| `render_performer.py` | render_performer — a shaded 1080p pass of the performer performing, for the detector. |
| `render_start_frame.py` | render_start_frame — the one frame E11 hands an image-to-video model. |
| `render_turnaround.py` | render_turnaround — an RGBA-true N-view turnaround of a static character GLB. |
| `rig_bake.py` | Arm (d) stage 2 — new UVs on the retopologised mesh, and the terracotta atlas baked |
| `rig_character.py` | rig_character — give a canonical character mesh a rig whose bones carry anatomical names. |
| `rig_parts.py` | rig_parts — E07 arm (c): a real stop-motion armature in software. |
| `rig_repair.py` | Arm (d), the route that actually works — **repair the shell, do not resample it**. |
| `rig_retopo.py` | Arm (d) stage 1 — strip the interior wall, then retopologise with **stock Blender only**. |

The halt contract every one of these follows — exit codes, the `<TOOL>_HALT` line, the success sentinel — is in [README.md](../README.md) under "Reading a halt".
