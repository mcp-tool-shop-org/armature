#!/usr/bin/env python
r"""make_e08_sheet — the Gate 0 sheet: previz | control | output | reference | provenance.

    python tools\make_e08_sheet.py --previz=<dir> --out=outputs/E08/sheets/E08-gate0.png

facet ran four arms and two gates before it built a sheet like this, and when the sheet
finally existed the Director read the whole thesis off one panel. So it is built BEFORE any
number is quoted, and it carries its own provenance rather than depending on a caption.

Five columns per sampled frame, left to right in the order the shot was made:

  E09 previz     the rig performing the baseline dance — the motion's ground truth
  control        the AAPose-20 sticks this experiment rendered from that rig
  painted        what the model returned
  reference      the identity seed (one panel, it does not vary by frame)
  provenance     hashes, seeds, gates, meters

--------------------------------------------------------------------------------
Every line of the provenance panel is read from the record

An earlier comment in this file asserted that already and named the correction "E10,
2026-08-12". It was not true for five lines: the Gate L verdict, the control channel's
convention and origin, the whole reference description, and the meter were string
literals. Measured 2026-09-03 — a synthetic record with `length: 50` (not 4n+1) and no
reference at all still produced a panel asserting Gate L legal and naming a letterbox that
never happened. That is the repo's named *placeholder shaped like evidence*, on the surface
the Director reads a verdict off. `provenance_lines` now derives every line through the
`_get`/`NOT RECORDED` convention `make_startframe_sheet` already implements, and the
function is separable from cv2 so a test can read what the panel says.

`--previz` is REQUIRED. Its default was an absolute path inside a different working tree
(`armature-E09`), which is where an unreadable-tile traceback would have come from on any
other machine or once that scratch tree was gone. Every tile is read through `_imread`,
which raises naming the path, as `make_overlay_sheet`, `make_zoom_sheet` and `make_plate`
already do.

Compensator: writes one PNG under `outputs/`; delete it. Inputs are read-only.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

TILE_W = 416

#: What a line prints when the record does not carry it. A string that cannot be mistaken
#: for a measurement — a plausible default here is the defect this file was written around.
MISSING = "NOT RECORDED"


class SheetInputError(ArmatureError):
    """A tile could not be read. Names the path, which an AttributeError did not."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _get(meta, *path, default=MISSING):
    """Walk a path through the record, or return `NOT RECORDED`."""
    cur = meta
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur if cur is not None else default


def _imread(path, cv2, what):
    img = cv2.imread(path)
    if img is None:
        raise SheetInputError(
            f"{what}: could not read {path}. A sheet built around a tile that is not "
            f"there would show a column of something else",
            {"input": what, "path": os.path.abspath(path)})
    return img


def provenance_lines(rec, prompt_id=None, seeds_file=None, gates=None):
    """Every line of the provenance panel, derived from the record. No literals.

    The two values that are not in the payload record are the `prompt_id` (which does not
    exist until the run is submitted) and the `seeds_file` the seed was drawn from; both
    are passed in and print `NOT RECORDED` when they are not.
    """
    res = _get(rec, "resolution")
    wh = f"{res[0]}x{res[1]}" if isinstance(res, (list, tuple)) and len(res) == 2 else MISSING
    models = _get(rec, "models", default={})
    models = models if isinstance(models, dict) else {}
    sampler = _get(rec, "sampler", default={})
    sampler = sampler if isinstance(sampler, dict) else {}
    unconnected = ", ".join(sorted(_get(rec, "unconnected_inputs", default={}) or {})) or MISSING
    sha = _get(rec, "payload_sha256", default="")
    meter = _get(rec, "meters", "estimate_credits")
    if meter is MISSING:
        meter = _get(rec, "estimate_credits")

    return [
        f"{_get(rec, 'experiment')} PROBE - provenance",
        f"prompt_id           {prompt_id or MISSING}",
        f"seed                {_get(rec, 'seed')}   ({seeds_file or MISSING})",
        f"model               {models.get('unet', MISSING)}",
        f"clip / vae          {models.get('clip', MISSING)} / {models.get('vae', MISSING)}",
        f"sampler             {sampler.get('steps', MISSING)} steps, "
        f"cfg {sampler.get('cfg', MISSING)}, "
        f"{sampler.get('sampler_name', MISSING)}/{sampler.get('scheduler', MISSING)}, "
        f"shift {sampler.get('shift', MISSING)}",
        f"frame               {wh}x{_get(rec, 'length')} @ {_get(rec, 'fps')} fps",
        f"Gate L              {_get(rec, 'gate_L', 'verdict')}",
        f"payload sha256      {str(sha)[:48] if sha else MISSING}",
        f"control             {_get(rec, 'pose_video', 'declared_frames')} frames, "
        f"convention {_get(rec, 'pose_video', 'convention')}",
        f"                    source {_get(rec, 'pose_video', 'source')}",
        f"reference           {_get(rec, 'reference_image', 'server_name')}, "
        f"fit {_get(rec, 'reference_image', 'fit')}",
        f"unconnected         {unconnected}",
        f"gates               {gates or MISSING}",
        f"meters              estimate_credits {meter}",
    ]


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sticks", default="outputs/E08/sticks")
    ap.add_argument("--painted", default="outputs/E08/probe/lossless")
    ap.add_argument("--reference", default="outputs/E08/reference/twin_r3_v0_fit_832x480.png")
    ap.add_argument("--previz", required=True,
                    help="the previz frames this sheet's left column shows. Required, and "
                         "NOT defaulted: the old default named a directory in a different "
                         "working tree, so the failure arrived from somewhere nobody named")
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
    with open(a.provenance, encoding="utf-8") as fh:
        rec = json.load(fh)
    ref = fit(_imread(a.reference, cv2, "reference"), cv2)

    rows = []
    for i in idx:
        pv = _imread(os.path.join(a.previz, f"{i:05d}.png"), cv2, f"previz frame {i}")
        ct = _imread(os.path.join(a.sticks, f"{i:05d}.png"), cv2, f"control frame {i}")
        pt = _imread(os.path.join(a.painted, f"{i:05d}.png"), cv2, f"painted frame {i}")
        tiles = [label(fit(pv, cv2), f"f{i}  {a.previz_label}", cv2),
                 label(fit(ct, cv2), f"f{i}  control: AAPose-20 sticks", cv2),
                 label(fit(pt, cv2), f"f{i}  painted output", cv2),
                 label(ref, "reference (letterboxed twin)", cv2)]
        h = max(t.shape[0] for t in tiles)
        tiles = [np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0))) for t in tiles]
        rows.append(np.concatenate(tiles, axis=1))

    body = np.concatenate(rows, axis=0)

    # Every line below IS read from the run's own record — see `provenance_lines`, and the
    # docstring for what the five literals that used to live here asserted about runs they
    # had never consulted.
    lines = provenance_lines(rec, prompt_id=a.prompt_id, seeds_file=a.seeds_file,
                             gates=a.gates)
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
