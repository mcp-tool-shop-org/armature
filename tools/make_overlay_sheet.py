#!/usr/bin/env python
"""make_overlay_sheet — the pose sticks composited onto the render they claim to describe.

    python tools\\make_overlay_sheet.py --keypoints=<keypoints.json> --render=<frame dir>
           --out=<sheet.png> [--frames=0,16,32,48,64]

A DIAGNOSTIC. It gates nothing, decides nothing and is never quoted as a number. What it
does is put the driving signal and the previz of the same performance in the same pixels, so
a wrong keypoint is visible instead of arguable.

**Why it earns its place before any credit is spent.** Every check in the pose-stick chain
so far is internally consistent: the counts agree, the frames are legal, nothing lands off
canvas, no frame is blank, the convention matches its source byte for byte. All of that is
equally true of a skeleton with its left and right arms swapped, its eyes placed on the back
of the skull, or its toes taken from the wrong end of the ankle bone. Those are errors of
*correspondence*, and the only instrument that sees them is the body itself.

This requires the keypoints to have been projected through the SAME camera the render used
— `project_pose_keypoints --camera-json=<that render's provenance>`, whose loader refuses a
record that disagrees about any angle.

Compensator: writes one PNG under `outputs/`; delete the file. Inputs are read-only.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from armature_core import aapose  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
from sheet_compose import PAD as SHEET_PAD  # noqa: E402

#: Gutter between overlay tiles — same PAD dailies sheets use (F-5b24109f).
TILE_GUTTER = SHEET_PAD
#: Dark bar under the frame caption, matching `make_e08_sheet.label` (F-f79959ea).
LABEL_BAR_H = 26
GUTTER_RGB = (18, 18, 20)


HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class OverlaySheetError(ArmatureError):
    """This overlay sheet cannot be produced as asked. One typed refusal for this tool.

    WARNING - **the paragraph that used to stand here is CORRECTED, not deleted.** It read:
    "The three bare `FileNotFoundError` / `RuntimeError` / `ValueError` raises above it are
    a separate family (wave 8's typed-refusal sweep did not reach this file) and are left
    where they are; what this class exists for is the WRITE". Measured on `580af47` by AST
    walk over this module: 5 raises, 1 with an evidence dict - so three of five refusals in
    a file that defines its own family class raised builtins with no evidence, eleven lines
    above a correct use of the family with a full dict. "A separate family" was a
    description of the defect, written as though it were a design.

    Worst realistic consequence, and it is the mismatch clause that carries it: the sheet
    that shows the projected keypoints drawn over the previz frames - the panel a reader
    uses to decide whether the driving signal lands on the body - refused on a resolution
    disagreement (the refusal whose own message says "an overlay across resolutions proves
    nothing") through an exception class that no halt reader, no `RECORDED_ANDON_CLASSES`
    member and no clause-vocabulary consumer can see. The two resolutions and the frame that
    disagreed are the measurement worth keeping, and they reached nothing.

    All five refusals raise this class now, each with the evidence its message already named
    in prose. F-a3160731, wave 25.
    """


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="draw the pose sticks over the render they claim to describe, so the "
                    "driving signal is seen landing on the body or not",
        epilog=HALT_EPILOG)
    ap.add_argument("--keypoints", required=True,
                    help="the projected keypoints record whose body points are drawn")
    ap.add_argument("--render", required=True, help="directory of NNNNN.png previz frames")
    ap.add_argument("--out", required=True, help="the overlay sheet image to write")
    ap.add_argument("--frames", default="0,16,32,48,64",
                    help="comma-separated frame indices (argparse eats leading minus signs)")
    ap.add_argument("--scale", type=float, default=0.5,
                    help="how far each panel is scaled down for the sheet; the markers are "
                         "sized in SOURCE pixels, so this does not change what is drawn")
    ap.add_argument("--dot", type=int, default=5, help="marker radius in source pixels")
    return ap.parse_args(argv)


def gate_frame_indices(text, rec):
    """ANDON - `--frames` is a list of frame indices this keypoint record HOLDS.

    F-a3160731's two adjacent argument holes, closed by one guard (wave 25). `idx = [int(v)
    for v in a.frames.split(",") if v.strip() != ""]` was unvalidated, and `rec["body"][i]`
    below indexed the keypoint record by the same unbounded `i` - so a non-integer token
    died as a bare `ValueError` from inside a list comprehension and an out-of-range index
    reached the record as an `IndexError`, on a tool that has a family class of its own.
    Python's own negative indexing is the sharper half: `--frames=-1` reaches
    `rec["body"][-1]` and draws the LAST frame's keypoints under the caption `frame -1`,
    over a previz file named `-0001.png` - so the refusal it produced named a missing file
    rather than the flag that was wrong.
    """
    parts = [t.strip() for t in str(text).split(",") if t.strip() != ""]
    if not parts:
        raise OverlaySheetError(
            f"--frames={text!r} names no frame; there is nothing to draw",
            {"gate": "ARGS", "andon": "OverlaySheetError",
             "clause": "frame_list_is_empty", "flag": "--frames", "supplied": text})
    unreadable = [t for t in parts if not t.lstrip("-").isdigit() or t.lstrip("-") == ""]
    if unreadable:
        raise OverlaySheetError(
            f"--frames={text!r} is a comma-separated list of frame indices; "
            f"{', '.join(repr(u) for u in unreadable)} is not one",
            {"gate": "ARGS", "andon": "OverlaySheetError",
             "clause": "frame_index_not_an_integer", "flag": "--frames",
             "supplied": text, "unreadable": unreadable})
    idx = [int(t) for t in parts]
    n = len(rec.get("body") or [])
    out_of_range = [i for i in idx if not 0 <= i < n]
    if out_of_range:
        raise OverlaySheetError(
            f"--frames={text!r} names frame(s) {out_of_range} and the keypoint record "
            f"holds {n} frame(s) (0..{n - 1}); an out-of-range index reaches "
            f"rec['body'][i], and Python's negative indexing would draw a DIFFERENT "
            f"frame's keypoints under the caption the reader is given",
            {"gate": "ARGS", "andon": "OverlaySheetError",
             "clause": "frame_index_outside_the_record", "flag": "--frames",
             "supplied": text, "out_of_range": out_of_range, "n_frames": n})
    return idx


def main(argv=None):
    a = parse_args(argv)
    import cv2

    with open(a.keypoints, encoding="utf-8") as fh:
        rec = json.load(fh)
    width, height = rec["resolution"]
    idx = gate_frame_indices(a.frames, rec)

    tiles = []
    for i in idx:
        src = os.path.join(a.render, f"{i:05d}.png")
        if not os.path.isfile(src):
            raise OverlaySheetError(
                f"no previz frame at {src}; the overlay is the panel a reader uses to "
                f"decide whether the driving signal lands on the body, and a frame that "
                f"is not there cannot be one of its tiles",
                {"gate": "INPUT", "andon": "OverlaySheetError",
                 "clause": "previz_frame_is_not_on_disk",
                 "frame": i, "file": src, "render": a.render, "frames": idx})
        img = cv2.imread(src)
        if img is None:
            raise OverlaySheetError(
                f"cv2 could not read {src}; a frame that decodes to nothing would be "
                f"drawn as an empty tile beside tiles that carry a body",
                {"gate": "INPUT", "andon": "OverlaySheetError",
                 "clause": "previz_frame_could_not_be_decoded",
                 "frame": i, "file": src, "render": a.render, "frames": idx})
        if (img.shape[1], img.shape[0]) != (width, height):
            raise OverlaySheetError(
                f"{src} is {img.shape[1]}x{img.shape[0]} and the keypoints were projected "
                f"at {width}x{height}; an overlay across resolutions proves nothing",
                {"gate": "INPUT", "andon": "OverlaySheetError",
                 "clause": "render_and_keypoints_disagree_on_resolution",
                 "frame": i, "file": src,
                 "render_size": [int(img.shape[1]), int(img.shape[0])],
                 "keypoints_size": [int(width), int(height)]})

        # The sticks, drawn full-strength, then screened over the render so the body stays
        # readable underneath. Additive rather than alpha: a stick over a light backdrop
        # must not disappear into it, and the render here is a pale studio plate.
        sticks = aapose.draw_frame(height, width, rec["body"][i],
                                   left_hand=rec["left_hand"][i],
                                   right_hand=rec["right_hand"][i])[..., ::-1]
        over = np.maximum(img.astype(np.int16), sticks.astype(np.int16))
        over = np.clip(over, 0, 255).astype(np.uint8)

        # Ringed markers on the 20 body keypoints, so a joint landing off the body is
        # visible as a ring in empty air rather than hidden inside a stick. Dark halo
        # behind the index so it stays readable on the pale studio plate (F-f79959ea).
        for j, (x, y, _c) in enumerate(rec["body"][i]):
            jx, jy = int(round(x)) + a.dot + 2, int(round(y)) - 2
            cv2.circle(over, (int(round(x)), int(round(y))), a.dot, (255, 255, 255), 1)
            cv2.putText(over, str(j), (jx, jy), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(over, str(j), (jx, jy), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1, cv2.LINE_AA)

        # Black caption bar then white text — `make_e08_sheet.label` LOOK (F-f79959ea).
        cv2.rectangle(over, (0, 0), (over.shape[1], LABEL_BAR_H), (0, 0, 0), -1)
        cv2.putText(over, f"frame {i}", (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(cv2.resize(over, (int(width * a.scale), int(height * a.scale)),
                                interpolation=cv2.INTER_AREA))

    # F-5b24109f: gutter between tiles so an edge stick does not read across frames.
    if len(tiles) == 1:
        sheet = tiles[0]
    else:
        h = tiles[0].shape[0]
        gap = np.full((h, TILE_GUTTER, 3), GUTTER_RGB, dtype=np.uint8)
        parts = []
        for i, t in enumerate(tiles):
            if i:
                parts.append(gap)
            parts.append(t)
        sheet = np.concatenate(parts, axis=1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    # `cv2.imwrite` returns a BOOL on failure and raises NOTHING -- measured 2026-09-04
    # with this venv's OpenCV 5.0.0: an --out naming an existing DIRECTORY returned False,
    # wrote nothing and printed only a WARN on stderr, while the sentinel below carried
    # that path as though the sheet were there. The shape is fit_reference.py:212's
    # (RE-MEASURED wave 16: it cited 216 before that class lost a normalising
    # `__init__` four lines up).
    if not cv2.imwrite(a.out, sheet):
        raise OverlaySheetError(
            f"cv2 refused to write {os.path.abspath(a.out)}; the sentinel line would name "
            f"a file that is not there, and that line is the receipt a later session cites",
            {"gate": "WRITE", "out": os.path.abspath(a.out),
             "size": [int(sheet.shape[1]), int(sheet.shape[0])], "frames": idx})
    print("OVERLAY_SHEET_OK " + json.dumps({
        "out": os.path.abspath(a.out), "frames": idx,
        "tile": [int(width * a.scale), int(height * a.scale)],
        "keypoint_names": list(aapose.KEYPOINT_NAMES)}))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_OVERLAY_SHEET")
