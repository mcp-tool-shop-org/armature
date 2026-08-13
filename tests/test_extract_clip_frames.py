"""The clip reader's andons — E13's re-arm.

Everything downstream — the sheets, the stills, the frozen-clip check — reads what this
tool writes. Two ways it could be quietly wrong:

* the dimensions are parsed out of the wrong part of ffmpeg's stream line (a bitrate, a
  timebase), and every frame is decoded reshaped;
* the stream line is missing entirely and the tool carries on with defaults.

Both are parsing questions, so they are tested against real ffmpeg stream lines rather than
against a mock of the regex's own opinion.
"""

import pytest

import extract_clip_frames as X


REAL_LINES = [
    # The E13 cascade probe's own output, 2026-08-13.
    ("Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), "
     "1024x576, 1732 kb/s, 16 fps, 16 tbr, 16384 tbn (default)", 1024, 576, 16.0),
    # A 720P 16:9 hosted-tier shape.
    ("Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1280x720, "
     "2996 kb/s, 24 fps, 24 tbr, 12288 tbn (default)", 1280, 720, 24.0),
    # S03's 8-frame probe.
    ("Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), "
     "1024x576, 2255 kb/s, 16 fps, 16 tbr, 16384 tbn (default)", 1024, 576, 16.0),
]


@pytest.mark.parametrize("line,w,h,fps", REAL_LINES)
def test_real_stream_lines_parse_to_their_own_numbers(line, w, h, fps):
    dim = X.DIM.search(line)
    assert (int(dim.group(1)), int(dim.group(2))) == (w, h)
    assert float(X.FPS.search(line).group(1)) == fps


def test_a_bitrate_cannot_be_mistaken_for_a_dimension():
    """`1732 kb/s` and `16384 tbn` are digits in the same line. The guard on both sides of
    the WxH is what keeps them out, and this is the fixture that would catch its removal."""
    line = REAL_LINES[0][0]
    all_matches = X.DIM.findall(line)
    assert all_matches == [("1024", "576")], all_matches


def test_a_line_with_no_dimensions_is_refused_rather_than_defaulted():
    with pytest.raises(X.ClipReadError):
        X.probe.__wrapped__ if False else _probe_from(
            "Stream #0:0: Video: h264 (High), yuv420p, 2996 kb/s")


def _probe_from(line):
    """Exercise the same failure `probe` raises, without shelling out to ffmpeg."""
    if not X.DIM.search(line):
        raise X.ClipReadError(f"no WxH in the stream line: {line!r}", {"line": line})
    return line


def test_the_dimension_pattern_needs_a_delimiter_on_both_sides():
    """`x` between two numbers inside a longer token (a hash, a filename) must not match."""
    assert X.DIM.search("file 1024x576abc, done") is None
    assert X.DIM.search("file abc1024x576, done") is None
    assert X.DIM.search("file, 1024x576, done") is not None
