"""The review clip's own label. A filename the Director opens is evidence.

The tool wrote `review_0.5x_8fps.webp` whatever the flags said. That literal was true only
while every source ran at 16 fps; against E10's 20 fps source the same file is 0.40x at
8 fps, and the name asserted otherwise.
"""

from conftest import TOOLS  # noqa: F401
import make_review_clip as MRC


def test_the_name_carries_the_rate_that_was_actually_used():
    assert MRC.clip_name(8, 16) == "review_0.50x_8fps.webp"
    assert MRC.clip_name(10, 20) == "review_0.50x_10fps.webp"


def test_eight_fps_against_a_twenty_fps_source_is_not_called_half_speed():
    """The exact case E10 produced: 8 fps is 0.5x of 16 and 0.4x of 20, and the old literal
    would have shipped a clip claiming the wrong one."""
    assert MRC.clip_name(8, 20) == "review_0.40x_8fps.webp"
    assert "0.50x" not in MRC.clip_name(8, 20)


def test_full_speed_is_named_full_speed():
    assert MRC.clip_name(20, 20) == "review_1.00x_20fps.webp"


# ------------------------------- the review pass does not write into the run it is reading
#
# `main` did `os.makedirs(a.out, exist_ok=True)` and then wrote the clip plus one
# `still_f###_<target>.png` per requested index per target into `a.out`, with no refusal
# against an `--out` that already holds a numbered frame population.
#
# Measured 2026-09-04 in this worktree: `--frames=<dir> --out=<same dir>` on a 5-frame
# `lossless/` with `--stills=0,4` exited 0 and left `review_0.50x_8fps.webp`,
# `review_manifest.json` and EIGHT `still_f00*.png` beside `00000..00004.png`.
# `measure_floor.frame_population` then REFUSED that directory ("holds 8 PNG(s) that are not
# numbered frames") and `measure_clip.frame_paths` silently dropped all eight — so a review
# pass pointed at a run's own fetched frames leaves that population unusable for every
# stray-refusing instrument, and halts a later `verify_downloads` re-check on files the
# fetcher cannot attribute to anything.
#
# On the naming question this refutes rather than confirms: the canonical name is today's
# `review_<rate>x_<fps>fps.webp` under a dedicated review directory, which is what the record
# shows (E09-report.md:544,583,786-788; E10-report.md:311; E11-report.md:452 — never a run
# root and never `.mp4`). The three `*_review_8fps.mp4` in outputs/E02/runs are a superseded
# generation's artifacts left in the run ROOT, and teaching the fetcher's root sweep to
# tolerate them would teach it to accept a file that does not belong there. So the fix is
# here: refuse rather than register.

import os  # noqa: E402

import pytest  # noqa: E402
from PIL import Image  # noqa: E402


def _frames(tmp, n=5, name="lossless"):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        Image.new("RGB", (16, 16), (10 + i, 20, 30)).save(d / f"{i:05d}.png")
    return str(d)


def test_out_equal_to_frames_is_refused_and_leaves_nothing_behind(tmp_path):
    """THE fixture: the measured case, exactly."""
    frames = _frames(tmp_path)
    before = sorted(os.listdir(frames))
    with pytest.raises(MRC.ReviewClipError, match=r"--out .* is the frames directory") as e:
        MRC.main([f"--frames={frames}", f"--out={frames}", "--stills=0,4", "--crop=8"])
    assert e.value.evidence["gate"] == "OUT"
    assert sorted(os.listdir(frames)) == before


def test_an_out_that_already_holds_numbered_frames_is_refused(tmp_path):
    """Not only the same path: any directory carrying a run's own frame population. The
    stills would sort in beside them and every stray-refusing instrument would halt."""
    frames = _frames(tmp_path)
    other = _frames(tmp_path, n=3, name="another_run")
    with pytest.raises(MRC.ReviewClipError, match=r"already holds") as e:
        MRC.main([f"--frames={frames}", f"--out={other}", "--stills=0,4", "--crop=8"])
    assert e.value.evidence["numbered_frames"] == ["00000.png", "00001.png", "00002.png"]
    assert not os.path.exists(os.path.join(other, "review_manifest.json"))


def test_an_out_holding_a_urls_json_is_refused_as_a_run_root(tmp_path):
    """`urls.json` is the fetcher's own record; a directory carrying one is a run root,
    and `fetch_run.verify_downloads` sweeps it."""
    frames = _frames(tmp_path)
    root = tmp_path / "runroot"
    root.mkdir()
    (root / "urls.json").write_text("{}", encoding="utf-8")
    with pytest.raises(MRC.ReviewClipError, match=r"already holds"):
        MRC.main([f"--frames={frames}", f"--out={root}", "--stills=0,4", "--crop=8"])


def test_a_fresh_review_directory_still_writes_the_clip_and_the_stills(tmp_path, capsys):
    """The guard the other way, and the SUCCESS direction: exit 0, the sentinel, the clip
    under its canonical name, and the stills beside it."""
    frames = _frames(tmp_path)
    out = tmp_path / "review"
    assert MRC.main([f"--frames={frames}", f"--out={out}", "--stills=0,4",
                     "--crop=8"]) == 0
    assert "MAKE_REVIEW_CLIP_OK " in capsys.readouterr().out
    written = sorted(os.listdir(out))
    # WAVE 16 (F-78f49c7c): the clip's name now carries the RUN TOKEN when one can be
    # derived, so a run-root sweep can bind its exemption to the run instead of exempting
    # every run's review clip. `_frames` builds `<tmp>/lossless/`, so the derived token is
    # the tmp directory's own name; the rate half of the name is unchanged and is what this
    # assertion was written for.
    clip = [n for n in written if n.endswith(".webp")]
    assert len(clip) == 1, written
    assert clip[0].endswith("review_0.50x_8fps.webp"), clip
    assert "review_manifest.json" in written
    assert sum(1 for n in written if n.startswith("still_f")) == 8


def test_the_out_andon_survives_python_optimize(tmp_path):
    import subprocess
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frames = _frames(tmp_path)
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import make_review_clip as MRC\n"
        "try:\n"
        "    MRC.main(['--frames=%s', '--out=%s', '--stills=0,4', '--crop=8'])\n"
        "except MRC.ReviewClipError:\n"
        "    print('OUT_RAISED')\n"
    ) % (os.path.join(root, "tools"), frames.replace("\\", "/"), frames.replace("\\", "/"))
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "OUT_RAISED" in res.stdout, res.stdout + res.stderr
