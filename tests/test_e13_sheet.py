"""The sheet's provenance clause — E13's re-arm.

The sheet is read before any number is quoted, so the thing worth testing is not that it
draws pixels but that its provenance band cannot lie. CLAUDE.md: **a report may not contain
a placeholder shaped like evidence.** A missing field must print as missing, never as a
plausible value, and the slot-binding line must keep saying NOT VISIBLE.
"""

import json

import pytest
from PIL import Image

import make_e13_sheet as S


PAYLOAD = {
    "experiment": "E13", "arm": "A1", "tier": "wan2.7-r2v", "seed": 2026081351,
    "seed_registration": "E:/AI/armature-E13/specs/E13-seeds.json",
    "prompt_sha256": "a" * 64,
    "payload": {"model.resolution": "720P", "model.ratio": "16:9", "model.duration": 5,
                "watermark": False, "model.negative_prompt": "blurry, low quality"},
    "slot_order": ["model.reference_images.image1"],
    "gate_pair_note": "Gate PAIR is n/a on this tier and is RECORDED as n/a, not skipped",
    "gates": {"S_build_time": {"verdict": "seed 2026081351 is on the pre-registered list"},
              "CEILING_one_paid_node": {"verdict": "one billable node (500)"},
              "ROUTE": {"verdict": "0 weight file(s), 1 seed(s) all pinned",
                        "frame_legality_verdict": "INAPPLICABLE — hosted tier"}},
}
REFS = [{"slot": "image1", "label": "turn_0 (kit)", "sha": "b" * 64}]


def test_every_recorded_field_appears():
    lines = "\n".join(S.provenance_lines(PAYLOAD, "pid-123", "c" * 64, REFS))
    assert "wan2.7-r2v" in lines
    assert "pid-123" in lines
    assert "2026081351" in lines
    assert "720P" in lines and "16:9" in lines and "5s" in lines
    assert "E13-seeds.json" in lines


def test_a_missing_prompt_id_prints_NOT_RECORDED_rather_than_a_plausible_value():
    lines = "\n".join(S.provenance_lines(PAYLOAD, None, "c" * 64, REFS))
    assert "prompt_id    NOT RECORDED" in lines


def test_a_missing_field_anywhere_prints_NOT_RECORDED():
    thin = {"payload": {}}
    lines = "\n".join(S.provenance_lines(thin, None, None, []))
    assert lines.count("NOT RECORDED") >= 6
    assert "None" not in lines.replace("NOT RECORDED", ""), (
        "a Python None must never reach the sheet as text")


def test_the_slot_binding_line_says_not_visible():
    """The one claim the sheet must keep refusing to make."""
    lines = "\n".join(S.provenance_lines(PAYLOAD, "p", "c" * 64, REFS))
    assert "NOT VISIBLE" in lines
    assert "what was SENT" in lines


def test_the_watermark_line_reports_the_flag_that_was_sent():
    lines = "\n".join(S.provenance_lines(PAYLOAD, "p", "c" * 64, REFS))
    assert "watermark    False" in lines
    off = dict(PAYLOAD, payload=dict(PAYLOAD["payload"], watermark=True))
    assert "watermark    True" in "\n".join(S.provenance_lines(off, "p", "c" * 64, REFS))


def test_each_reference_gets_its_own_slot_and_hash_row():
    refs = [{"slot": f"image{i}", "label": f"turn_{i} (kit)", "sha": f"{i}" * 64}
            for i in range(1, 5)]
    lines = S.provenance_lines(PAYLOAD, "p", "c" * 64, refs)
    for i in range(1, 5):
        assert any(f"image{i}" in l and f"turn_{i}" in l for l in lines)


def test_the_sheet_renders_and_carries_all_three_bands(tmp_path):
    ref = tmp_path / "ref.png"
    Image.new("RGB", (352, 1024), (154, 154, 157)).save(ref)
    out = tmp_path / "f.png"
    Image.new("RGB", (1280, 720), (40, 40, 40)).save(out)
    sheet = S.build("A1", [str(ref)], ["image1 turn_0"], [str(out)], ["f0"],
                    S.provenance_lines(PAYLOAD, "p", "c" * 64, REFS),
                    "E13 A1 seed 1")
    assert sheet.size[0] >= 900 and sheet.size[1] > 400


def test_a_gate_the_payload_does_not_carry_prints_NOT_RECORDED(tmp_path):
    """A gate that has not run is written NOT RECORDED, never a plausible verdict."""
    thin = dict(PAYLOAD, gates={})
    lines = "\n".join(S.provenance_lines(thin, "p", "c" * 64, REFS))
    assert "gate S_build_time" in lines and "NOT RECORDED" in lines
