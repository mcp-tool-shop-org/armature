"""Tests for the run fetcher's node map.

The map was a module constant naming E02's tap node ids, which meant pointing the tool at
any later experiment's dump sorted every frame into the fallback branch and printed a
plausible count. E10's closing lesson names the shape — *a tool that names an experiment
in a literal is a tool that will lie the first time it is reused* — and these fixtures
hold the flag that replaced it.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import fetch_run as F


def test_no_map_keeps_the_default_taps():
    """E02, E08 and E10 all call this tool without the flag; their behaviour must not
    move because a later experiment needed a different mapping."""
    assert F.parse_node_map(None) == F.NODE_DIR
    assert F.parse_node_map("") == F.NODE_DIR
    assert F.parse_node_map(None) is not F.NODE_DIR, "callers must not mutate the default"


def test_a_map_replaces_the_taps_it_names():
    assert F.parse_node_map("41=startprobe,71=lossless") == {
        "41": "startprobe", "71": "lossless"}


def test_whitespace_and_trailing_commas_are_tolerated():
    assert F.parse_node_map(" 41 = startprobe , 71 = lossless , ") == {
        "41": "startprobe", "71": "lossless"}


@pytest.mark.parametrize("bad", ["41", "41=a=b", "=lossless", "71=", ","])
def test_a_malformed_map_halts_rather_than_falling_back_to_the_default(bad):
    """The dangerous outcome is not a crash. It is E02's mapping applied silently to
    another experiment's graph: every frame lands in the video branch, the files are
    named after the run, and the printed count looks entirely reasonable."""
    with pytest.raises(SystemExit):
        F.parse_node_map(bad)
