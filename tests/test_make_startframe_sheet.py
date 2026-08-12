"""Tests for the no-control Gate 0 sheet's provenance column.

Only one thing here is really being defended, and it is the reason the tool exists: **the
sheet must not print a value the run did not produce.** `make_gate0_sheet` carries E02-era
literals in its provenance panel (a model name, a sampler line, "of 33"), so pointing it at
a later run prints another experiment's settings beside this run's seed. E10 shipped that
exact defect once already — `make_e08_sheet` quoting E08's prompt_id and "832x480x65 @ 16
fps" over an E10 run — and the correction was "every value comes from the run's own payload
record". These fixtures hold that line for the new tool from its first commit.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import make_startframe_sheet as S


FULL = {
    "experiment": "E11",
    "route": "no-control I2V",
    "resolution": [832, 480], "length": 65, "fps": 16, "seed": 2026081231,
    "models": {"unet_high_noise": "high.safetensors", "unet_low_noise": "low.safetensors",
               "clip": "umt5.safetensors", "vae": "vae.safetensors", "loras": []},
    "trajectory": {"steps": {"value": 20}, "split_step": {"value": 10},
                   "cfg": {"value": 3.5}, "shift": {"value": 8.0},
                   "sampler_name": {"value": "euler"}, "scheduler": {"value": "simple"}},
    "start_image": {"server_name": "abc.png", "fit": "native"},
    "payload_sha256": "d" * 64,
    "gate_PIN": {"verdict": "pinned"}, "gate_S": {"verdict": "registered"},
    "gate_L": {"verdict": "PASS"}, "gate_ROUTE_built": {"verdict": "clean"},
}


def text(meta, **kw):
    return "\n".join(S.provenance_lines(meta, **kw))


def test_every_recorded_value_reaches_the_column():
    out = text(FULL, prompt_id="abc-123")
    for expected in ("E11", "high.safetensors", "low.safetensors", "umt5.safetensors",
                     "2026081231", "abc-123", "euler", "simple", "abc.png", "native"):
        assert expected in out, expected
    assert "20" in out and "10" in out and "3.5" in out and "8.0" in out


def test_a_value_the_record_does_not_carry_prints_not_recorded():
    """The whole point. A blank cell, a dash or a zero would be an assertion about the run;
    `NOT RECORDED` is the only honest thing to print for something nobody measured."""
    out = text({"experiment": "E11"})
    assert out.count(S.MISSING) >= 8
    assert "None" not in out


def test_the_prompt_id_is_not_recorded_until_the_run_exists():
    """It cannot come from the payload record: the record is written before submission and
    the id does not exist until after it."""
    assert S.MISSING in text(FULL)
    assert "abc-123" in text(FULL, prompt_id="abc-123")


def test_an_unrun_gate_reads_not_yet_run_rather_than_passing():
    """A gate with no verdict must never render as one. `Gate B` has not run when the sheet
    is first built, and a sheet that showed it blank would read as clean."""
    out = text(FULL)
    assert "Gate B         NOT YET RUN" in out
    assert "Gate B         PASS" not in out


@pytest.mark.parametrize("literal", [
    "VACE", "uni_pc", "of 33", "Wan 2.1", "30 steps", "cfg 6", "832x480", "E08", "E10",
])
def test_no_model_sampler_or_frame_literal_is_baked_into_the_column(literal):
    """The regression that matters. Rendered against a record carrying NONE of these, the
    column must contain none of them — that is what makes the sheet reusable without
    lying. Each string here appears in `make_gate0_sheet`'s panel as a literal."""
    assert literal not in text({"experiment": "X"})


def test_the_absence_of_a_driving_signal_is_stated_on_the_sheet():
    """A reader of the sheet must not have to infer the route's defining property from a
    missing column, and a missing column reads identically to a forgotten one."""
    out = text(FULL)
    assert "NO DRIVING SIGNAL" in out
    assert "verify_topology" in out


def test_measurements_are_labelled_as_diagnostics_when_present():
    out = text(FULL, measurements={"corr to f0": -0.198})
    assert "gate nothing" in out
    assert "-0.198" in out


def test_measurements_are_absent_when_not_supplied():
    assert "MEASURED" not in text(FULL)
