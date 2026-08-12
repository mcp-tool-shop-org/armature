#!/usr/bin/env python
"""make_e08_sheet — the Gate 0 sheet: previz | control | output | reference | provenance.

    python tools\make_e08_sheet.py --out=outputs/E08/sheets/E08-gate0.png

facet ran four arms and two gates before it built a sheet like this, and when the sheet
finally existed the Director read the whole thesis off one panel. So it is built BEFORE any
number is quoted, and it carries its own provenance rather than depending on a caption.

Five columns per sampled frame, left to right in the order the shot was made:

  E09 previz     the rig performing the baseline dance — the motion's ground truth
  control        the AAPose-20 sticks this experiment rendered from that rig
  painted        what the model returned
  reference      the identity seed (one panel, it does not vary by frame)
  provenance     hashes, seeds, gates, meters

Compensator: writes one PNG under `outputs/`; delete it. Inputs are read-only.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TILE_W = 416
PREVIZ = r"E:\AI\armature-E09\outputs\E09\b2-a3-render-lifted"


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sticks", default="outputs/E08/sticks")
    ap.add_argument("--painted", default="outputs/E08/probe/lossless")
    ap.add_argument("--reference", default="outputs/E08/reference/twin_r3_v0_fit_832x480.png")
    ap.add_argument("--previz", default=PREVIZ)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,16,32,48,64")
    ap.add_argument("--provenance", default="outputs/E08/route/E08-probe-payload-record.json")
    ap.add_argument("--prompt-id", required=True,
                    help="the run this sheet shows. Required, and NOT defaulted: a sheet "
                         "whose provenance block names another run's id is a placeholder "
                         "shaped like evidence")
    ap.add_argument("--seeds-file", required=True,
                    help="the committed seed registry this run's seed was drawn from")
    ap.add_argument("--previz-label", default="previz (motion ground truth)")
    ap.add_argument("--gates", default=None,
                    help="one line naming the gate states this run actually recorded")
    return ap.parse_args(argv)


def label(img, text, cv2):
    o = img.copy()
    cv2.rectangle(o, (0, 0), (o.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(o, text, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                cv2.LINE_AA)
    return o


def fit(img, cv2, w=TILE_W):
    h = int(round(img.shape[0] * w / img.shape[1]))
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def main(argv=None):
    a = parse_args(argv)
    import cv2

    idx = [int(v) for v in a.frames.split(",")]
    rec = json.load(open(a.provenance, encoding="utf-8"))
    ref = fit(cv2.imread(a.reference), cv2)

    rows = []
    for i in idx:
        pv = cv2.imread(os.path.join(a.previz, f"{i:05d}.png"))
        ct = cv2.imread(os.path.join(a.sticks, f"{i:05d}.png"))
        pt = cv2.imread(os.path.join(a.painted, f"{i:05d}.png"))
        tiles = [label(fit(pv, cv2), f"f{i}  {a.previz_label}", cv2),
                 label(fit(ct, cv2), f"f{i}  control: AAPose-20 sticks", cv2),
                 label(fit(pt, cv2), f"f{i}  painted output", cv2),
                 label(ref, "reference (letterboxed twin)", cv2)]
        h = max(t.shape[0] for t in tiles)
        tiles = [np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0))) for t in tiles]
        rows.append(np.concatenate(tiles, axis=1))

    body = np.concatenate(rows, axis=0)

    # Every number below is READ from the run's own payload record. The first version of
    # this block hardcoded E08's prompt_id, frame count, fps and gate line as string
    # literals, so pointing the tool at another run produced a sheet that quoted one run's
    # seed beside another run's identifiers — a report carrying a placeholder shaped like
    # evidence, which is the thing CLAUDE.md names outright. Corrected E10, 2026-08-12.
    w, h = rec["resolution"]
    unconnected = ", ".join(sorted(rec.get("unconnected_inputs") or {}))
    lines = [
        f"{rec['experiment']} PROBE - provenance",
        f"prompt_id           {a.prompt_id}",
        f"seed                {rec['seed']}   ({a.seeds_file}, committed pre-submission)",
        f"model               {rec['models']['unet']}",
        f"clip / vae          {rec['models']['clip']} / {rec['models']['vae']}",
        f"sampler             {rec['sampler']['steps']} steps, cfg {rec['sampler']['cfg']}, "
        f"{rec['sampler']['sampler_name']}/{rec['sampler']['scheduler']}, shift {rec['sampler']['shift']}",
        f"frame               {w}x{h}x{rec['length']} @ {rec['fps']} fps   "
        f"(Gate L: legal, 4n+1, <=81)",
        f"payload sha256      {rec['payload_sha256'][:48]}",
        f"control             {rec['pose_video']['declared_frames']} AAPose-20 stick frames, "
        f"Wan convention @ 29d4a35d,",
        "                    rendered from the E09 A3 rig - no detector anywhere",
        "reference           twin_r3_v0.png letterboxed 352x1024 -> 832x480 (Director ruling)",
        f"unconnected         {unconnected}",
        f"gates               {a.gates or 'NOT RECORDED — pass --gates'}",
        "meters              estimate_credits 0 (no paid API nodes); GPU time is the meter",
    ]
    panel = np.zeros((26 * len(lines) + 24, body.shape[1], 3), np.uint8)
    panel[:] = (18, 18, 20)
    for k, t in enumerate(lines):
        cv2.putText(panel, t, (12, 30 + k * 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (235, 235, 235), 1, cv2.LINE_AA)

    sheet = np.concatenate([body, panel], axis=0)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cv2.imwrite(a.out, sheet)
    print("E08_SHEET_OK " + json.dumps({"out": os.path.abspath(a.out),
                                        "size": [sheet.shape[1], sheet.shape[0]],
                                        "frames": idx}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
