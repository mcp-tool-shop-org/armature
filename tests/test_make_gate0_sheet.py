"""The gate-0 sheet's panel, after the third stale-literal sighting (E11).

The defect class: a tool that names an experiment's settings in literals lies the first
time it is reused. This file holds the same line `test_make_startframe_sheet` holds for
its tool: every value on the panel comes from the run's own record, and a value the
record does not carry prints NOT RECORDED.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import make_gate0_sheet as G


FULL = {
    "experiment": "E99", "arm": "A1", "prompt_id": "pid-42",
    "models": {"unet": "unet-x.safetensors", "clip": "clip-x.safetensors",
               "vae": "vae-x.safetensors"},
    "resolution": [640, 360], "length": 33, "fps": 12, "seed": 777,
    "sampler_name": "res_2s", "scheduler": "beta", "steps": 24, "cfg": 4.5,
    "payload_sha256": "e" * 64,
    "control": {"bridge": "pose-v2", "normalization": "unit",
                "polarity": "white-on-black", "distinct_images": 33, "total_images": 65,
                "bridge_fidelity": "out = src, measured"},
    "reference_image": "ref.png",
    "gate_L": {"verdict": "PASS"}, "gate_R": "PASS (codec in path)",
}

#: Metas that carry NONE of the old panel's baked values. Rendered against these, the
#: panel must contain none of the literals below — that is what makes it reusable
#: without lying.
BARE = ({}, {"arm": "X"}, {"arm": "X", "control": {}})


def text(meta):
    return "\n".join(G.provenance_lines(meta))


def everything(meta):
    return "\n".join([G.header_text(meta), G.output_heading(meta), text(meta),
                      "\n".join(G.reference_absent_lines(meta)), G.frame_caption(3)])


def test_every_recorded_value_reaches_the_panel():
    out = text(FULL)
    for expected in ("A1", "pid-42", "unet-x.safetensors", "clip-x.safetensors",
                     "vae-x.safetensors", "777", "res_2s", "beta", "24", "4.5",
                     "pose-v2", "unit", "white-on-black", "of 65", "ref.png",
                     "out = src, measured"):
        assert expected in out, expected


def test_a_value_the_record_does_not_carry_prints_not_recorded():
    """A blank cell, a dash or a zero would be an assertion about the run; NOT RECORDED
    is the only honest thing to print for something nobody recorded."""
    out = text({"arm": "X", "control": {}})
    assert out.count(G.MISSING) >= 8
    assert "None" not in out


@pytest.mark.parametrize("literal", [
    "E02", "E03", "Wan 2.1", "VACE", "uni_pc", "30 steps", "cfg 6", "of 33",
    "max(src-1", "N/A for this route",
])
def test_no_e02_era_literal_survives_anywhere_on_the_panel(literal):
    """The regression that matters. Each string here was baked into the old panel, its
    header, its reference column or its default caption."""
    for meta in BARE:
        assert literal not in everything(meta)


def test_the_header_never_invents_an_experiment_name():
    assert "E02" not in G.header_text({})
    assert G.MISSING in G.header_text({})
    assert "E99 A1" in G.header_text(FULL)


def test_the_output_heading_carries_the_recorded_model_or_says_so():
    assert "unet-x.safetensors" in G.output_heading(FULL)
    assert G.MISSING in G.output_heading({})


def test_the_default_caption_claims_no_azimuth():
    """The old default computed an azimuth from the frame count — E02's orbit baked into
    the tool. A run that does not orbit must not get angles that never happened."""
    assert G.frame_caption(7) == "f007"
    assert "az" not in G.frame_caption(7)
    assert G.frame_caption(7, {7: "az 210d"}) == "f007  az 210d"
    assert G.frame_caption(7, {3: "elsewhere"}) == "f007"


def test_gate_r_derives_from_the_record_rather_than_asserting_a_route():
    assert "PASS (codec in path)" in text(FULL)
    bare = [ln for ln in G.provenance_lines({"arm": "X"}) if ln.startswith("Gate R")]
    assert bare and G.MISSING in bare[0]


def test_an_unrun_gate_reads_not_yet_run_rather_than_passing():
    out = text({"arm": "X"})
    assert "NOT YET RUN" in out
    lines = G.provenance_lines({"arm": "X"})
    assert any(ln.startswith("Gate B") and "NOT YET RUN" in ln for ln in lines)
    assert any(ln.startswith("Gate C") and "NOT YET RUN" in ln for ln in lines)


def test_the_bridge_fidelity_line_exists_only_when_a_control_channel_does():
    """Printing 'bridge fidelity NOT RECORDED' on a control-less run would imply a
    bridge existed. The line exists only when the record carries a control channel."""
    assert "bridge fidelity" not in text({"arm": "X"})
    assert "bridge fidelity out = src, measured" in text(FULL)
    assert "bridge fidelity " + G.MISSING in text({"arm": "X", "control": {}})


def test_the_reference_absent_reason_comes_from_the_record():
    told = "\n".join(G.reference_absent_lines({"reference_absent_reason": "no identity"}))
    assert "no identity" in told
    assert G.MISSING in "\n".join(G.reference_absent_lines({}))
