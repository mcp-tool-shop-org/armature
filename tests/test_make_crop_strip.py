"""Tests for the crop-strip cutter.

The box parser is what is defended. A still published at 3x is the artifact identity gets
judged on, so where it was cut from has to be recoverable exactly — and a parser that
silently dropped a malformed entry would publish a strip missing the frame it was made to
show, with nothing saying so.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import make_crop_strip as C


def test_a_well_formed_box_list_parses_in_order():
    assert C.parse_boxes("0:1,2,3,4;32:10,20,30,40") == [
        (0, (1, 2, 3, 4)), (32, (10, 20, 30, 40))]


def test_trailing_and_empty_entries_are_tolerated():
    assert C.parse_boxes(" 0:1,2,3,4 ; ; ") == [(0, (1, 2, 3, 4))]


@pytest.mark.parametrize("bad", [
    "0-1,2,3,4",        # no colon
    "0:1,2,3",          # three coordinates
    "0:1,2,3,4,5",      # five
    "0:5,2,3,4",        # x1 <= x0
    "0:1,9,3,4",        # y1 <= y0
    "",                 # nothing at all
])
def test_a_malformed_entry_halts_rather_than_being_skipped(bad):
    with pytest.raises(SystemExit):
        C.parse_boxes(bad)


def test_a_zero_extent_box_is_refused_not_clamped():
    """A 0-pixel crop enlarges to nothing and pastes as a seam. Refusing is the only
    outcome that cannot be mistaken for a tile."""
    with pytest.raises(SystemExit):
        C.parse_boxes("4:100,100,100,140")
