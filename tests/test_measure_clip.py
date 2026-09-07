"""measure_clip — dedicated module home (wave 35, F-8c52638d).

Before this file the tool had library coverage only through
`tests/test_instruments_measure_amend_w14.py` (one-frame summary) and no durable
`test_measure_clip.py`. The argv SUCCESS fixture lives in
`tests/test_measure_argv_smoke.py`; this home pins the clip-stats contract the sheet
consumers read.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS  # noqa: F401
import measure_clip as MC


def _frames(tmp, n=3, size=(8, 6)):
    d = tmp / "frames"
    d.mkdir()
    for i in range(n):
        arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        arr[i % size[1], i % size[0]] = (200, 40, 40)
        Image.fromarray(arr).save(d / f"{i:05d}.png")
    return str(d)


def test_main_writes_measurements_and_prints_the_ok_sentinel(tmp_path, capsys):
    out = tmp_path / "m.json"
    assert MC.main([f"--frames={_frames(tmp_path)}", f"--out={out}"]) == 0
    assert out.is_file() and out.stat().st_size > 0
    assert "MEASURE_CLIP_OK" in capsys.readouterr().out
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["arms"][0]["n_frames"] == 3


def test_a_missing_frames_dir_raises_before_writing(tmp_path):
    out = tmp_path / "m.json"
    with pytest.raises(Exception):
        MC.main([f"--frames={tmp_path / 'missing'}", f"--out={out}"])
    assert not out.exists()
