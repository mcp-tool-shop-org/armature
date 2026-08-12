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
