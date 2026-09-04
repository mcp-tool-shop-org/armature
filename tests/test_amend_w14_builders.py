"""Wave 14, builders — the guards land on the operand the finding named.

Each block below names the finding, the operand, and the mutation that makes the guard
fire. Every fixture here was run once with the fix REVERTED (`git stash`), and the
`reverted-red` note in each block records what the reverted tree did.

The rule this wave adds: a guard's red proof exercises the guard, not its neighbour. So a
receipt is proven by READING THE PRINTED LINE BACK; a ceiling by the measured number and
equality; a per-job exit reader by a row whose exit was never recorded; a fit comparison by
a file whose IHDR disagrees with the frame the graph generates.
"""

import json
import os
import subprocess
import sys

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import route_gates as RG
from armature_core.errors import ArmatureError

import gate_saved_graph as GSG


# ===========================================================================
# F-2da88c51 — the LAST gate before a paid submission passes the two facts
#              every builder passes, read off the record beside the graph.
# ===========================================================================

#: The free assembly chain's classes, exactly the four
#: `build_assembly_payload.build([...])` emits (measured 2026-09-04:
#: ['BatchImagesNode', 'CreateVideo', 'LoadImage', 'SaveVideo']). It carries NO sampler,
#: which is the fact `verify` refuses to guess at.
ASSEMBLY_API = {
    "1": {"class_type": "LoadImage", "inputs": {"image": "00000.png"}},
    "2": {"class_type": "LoadImage", "inputs": {"image": "00001.png"}},
    "10": {"class_type": "BatchImagesNode",
           "inputs": {"images.image0": ["1", 0], "images.image1": ["2", 0]}},
    "20": {"class_type": "CreateVideo",
           "inputs": {"fps": 8, "bit_depth": 8, "images": ["10", 0]}},
    "30": {"class_type": "SaveVideo",
           "inputs": {"filename_prefix": "S03/assembly", "format": "auto",
                      "codec": "auto", "video": ["20", 0]}},
}

ASSEMBLY_LINKS = [[1, 1, 0, 10, 0, "IMAGE"], [2, 2, 0, 10, 1, "IMAGE"],
                  [3, 10, 0, 20, 0, "IMAGE"], [4, 20, 0, 30, 0, "VIDEO"]]

ASSEMBLY_SAVED = {"nodes": [
    {"id": 1, "type": "LoadImage", "inputs": [], "widgets_values": ["00000.png"]},
    {"id": 2, "type": "LoadImage", "inputs": [], "widgets_values": ["00001.png"]},
    {"id": 10, "type": "BatchImagesNode", "widgets_values": [],
     "inputs": [{"name": "images.image0", "type": "IMAGE", "link": 1},
                {"name": "images.image1", "type": "IMAGE", "link": 2}]},
    {"id": 20, "type": "CreateVideo", "widgets_values": [8, 8],
     "inputs": [{"name": "images", "type": "IMAGE", "link": 3},
                {"name": "audio", "type": "AUDIO", "link": None}]},
    {"id": 30, "type": "SaveVideo", "widgets_values": ["S03/assembly", "auto", "auto"],
     "inputs": [{"name": "video", "type": "VIDEO", "link": 4}]},
], "links": [list(r) for r in ASSEMBLY_LINKS]}


#: The CONDITIONAL component arm T wires (`build_lora_arm_payload.ARMS['T']`), served
#: through a class this tool already carries a widget row for. The licence map rules it
#: CONDITIONAL and `verify` refuses it uncredited — that refusal is CORRECT, and the point
#: of the fix is that a correctly credited record can now say so at this gate.
TECHNICALLY_COLOR = "wan22-14b-t2v-technically_color.safetensors"

CREDIT_API = {
    "75": {"class_type": "UNETLoader",
           "inputs": {"unet_name": TECHNICALLY_COLOR, "weight_dtype": "default"}},
    "81": {"class_type": "KSamplerAdvanced",
           "inputs": {"add_noise": "enable", "noise_seed": 2026081233, "steps": 8,
                      "cfg": 3.5, "sampler_name": "euler", "scheduler": "simple",
                      "start_at_step": 0, "end_at_step": 4,
                      "return_with_leftover_noise": "enable", "model": ["75", 0]}},
}

CREDIT_SAVED = {"nodes": [
    {"id": 75, "type": "UNETLoader", "inputs": [],
     "widgets_values": [TECHNICALLY_COLOR, "default"]},
    # save format inserts `control_after_generate` at index 2
    {"id": 81, "type": "KSamplerAdvanced",
     "inputs": [{"name": "model", "type": "MODEL", "link": 5}],
     "widgets_values": ["enable", 2026081233, "fixed", 8, 3.5, "euler", "simple",
                        0, 4, "enable"]},
], "links": [[5, 75, 0, 81, 0, "MODEL"]]}


def _write(tmp_path, name, doc):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def _builder_record(api_graph, **verify_kwargs):
    """A payload record shaped like the builders': the gate's own receipt, under `gates`.

    Built by CALLING `verify`, not by typing a receipt — the facts this admission reads
    back are the facts the builder's own gate recorded.
    """
    return {"tool": "a builder", "gates": {"ROUTE": RG.verify(api_graph, **verify_kwargs)}}


def test_assembly_route_reaches_admission_when_the_record_says_no_sampler(tmp_path, capsys):
    """F-2da88c51 · operand: `carries_no_sampler`, on the free assembly chain.

    reverted-red: yes. Without `--record` (and without the plumbing behind it) this exact
    invocation raises RouteGate — "the seed clause is INDETERMINATE on this graph and
    therefore UNPROVEN ... Pass carries_no_sampler=True if the graph really carries none"
    — i.e. the last gate before a paid submission refuses a CORRECT configuration.
    """
    api = _write(tmp_path, "in/g.api.json", ASSEMBLY_API)
    saved = _write(tmp_path, "in/g.saved.json", ASSEMBLY_SAVED)
    seeds = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    record = _write(tmp_path, "in/payload-record.json", _builder_record(
        ASSEMBLY_API, family="wan", carries_no_sampler=True, frame=(832, 480, 81)))
    out = tmp_path / "out" / "admission.json"

    assert GSG.main([f"--saved={saved}", f"--api={api}", f"--seeds={seeds}",
                     f"--out={out}", f"--record={record}", "--frame=832,480,81"]) == 0

    # The receipt is read BACK off the printed line, not off the return value.
    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("SAVED_ADMISSION_OK ")][0]
    printed = json.loads(line[len("SAVED_ADMISSION_OK "):])
    assert printed["route_facts"]["carries_no_sampler"] is True
    assert printed["route_facts"]["record"] == os.path.abspath(str(record))
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["route_facts"]["carries_no_sampler"] is True
    assert written["gates"]["ROUTE"]["carries_no_sampler_asserted"] is True


def test_conditional_component_is_admitted_on_the_credit_its_builder_recorded(
        tmp_path, capsys):
    """F-2da88c51 · operand: `attribution`, on a graph loading the CONDITIONAL row.

    reverted-red: yes. Without the fix this invocation raises RouteGate clause
    `uncredited_conditional_component` however correct the builder's record is, because the
    CLI had no way to hand the credit to the gate that checks it.
    """
    entry = RG.attribution_entry_for("technically_color")
    api = _write(tmp_path, "in/g.api.json", CREDIT_API)
    saved = _write(tmp_path, "in/g.saved.json", CREDIT_SAVED)
    seeds = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    record = _write(tmp_path, "in/payload-record.json", _builder_record(
        CREDIT_API, frame=(832, 480, 81), attribution=[entry]))
    out = tmp_path / "out" / "admission.json"

    assert GSG.main([f"--saved={saved}", f"--api={api}", f"--seeds={seeds}",
                     f"--out={out}", f"--record={record}", "--frame=832,480,81"]) == 0

    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("SAVED_ADMISSION_OK ")][0]
    printed = json.loads(line[len("SAVED_ADMISSION_OK "):])
    assert printed["route_facts"]["attribution"] == ["technically_color"]
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["route_facts"]["attribution"] == [entry]
    # the credit reached the gate that checks it, and the gate says the row was paid
    conditional = written["gates"]["ROUTE"]["conditional_components"]
    assert [c["credited"] for c in conditional] == [True]


def test_without_the_record_the_assembly_route_is_still_refused(tmp_path):
    """F-2da88c51 · the fact is load-bearing, and the flag is the only way to supply it.

    This pins WHY the fix is a fix: with no `--record` the facts are `verify`'s defaults
    and the free assembly chain — a correct configuration this repo's own builder emits —
    is refused by the last gate before a paid submission. It is the pre-fix behaviour of
    every invocation, kept as a permanent measurement rather than a memory.
    """
    api = _write(tmp_path, "in/g.api.json", ASSEMBLY_API)
    saved = _write(tmp_path, "in/g.saved.json", ASSEMBLY_SAVED)
    seeds = _write(tmp_path, "in/seeds.json", {"seeds": [2026081233]})
    out = tmp_path / "out" / "admission.json"
    with pytest.raises(RG.RouteGate) as exc:
        GSG.main([f"--saved={saved}", f"--api={api}", f"--seeds={seeds}",
                  f"--out={out}", "--frame=832,480,81"])
    assert "INDETERMINATE" in str(exc.value)
    assert not out.parent.exists()


def test_a_record_with_no_verify_receipt_is_refused_by_name(tmp_path):
    """F-2da88c51 · the "refuses when the record lacks them" half.

    The fixture is `gate_base_licence`'s evidence dict, which carries the SAME
    gate=ROUTE / andon=RouteGate pair and NEITHER fact — the exact shape a reader keyed on
    the gate id would have accepted as a source of facts it does not hold.
    """
    record = _write(tmp_path, "in/rec.json", {"gates": {"BASE_LICENCE": {
        "gate": "ROUTE", "andon": "RouteGate", "clause": "banned_component_in_base",
        "banned": [], "n_components_examined": 3}}})
    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(str(record))
    assert exc.value.evidence["clause"] == "record_carries_no_verify_receipt"


def test_an_unreadable_record_is_a_refusal_not_a_crash(tmp_path):
    """F-2da88c51 · a record that cannot be read supplies neither fact."""
    p = tmp_path / "rec.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(str(p))
    assert exc.value.evidence["clause"] == "record_unreadable"


def test_two_receipts_that_disagree_about_the_sampler_are_refused(tmp_path):
    """F-2da88c51 · one of them describes the graph and this gate cannot tell which."""
    yes = dict(RG.verify(ASSEMBLY_API, family="wan", carries_no_sampler=True,
                         frame=(832, 480, 81)))
    no = dict(RG.verify(CREDIT_API, frame=(832, 480, 81),
                        attribution=[RG.attribution_entry_for("technically_color")]))
    record = _write(tmp_path, "rec.json", {"gates": {"ROUTE": yes, "ROUTE_2": no}})
    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(str(record))
    assert exc.value.evidence["clause"] == "record_route_facts_disagree"


# ===========================================================================
# F-b7e7c5c0 — `gate_base_licence`'s receipt distinguishes "nothing banned"
#              from "the table ruled nothing".
# ===========================================================================

import build_lora_arm_payload as BLA  # noqa: E402

#: Three weight files the licence map has never seen. `route_gates.components()` returns
#: three rows all reading verdict `NOT IN THIS TABLE` with `matched_on: None` — the table
#: RULED none of them, which is the operand.
UNKNOWN_BASE = {
    "1": {"class_type": "LoraLoaderModelOnly",
          "inputs": {"lora_name": "some_unknown_style_v3.safetensors",
                     "strength_model": 1.0}},
    "2": {"class_type": "VAELoader", "inputs": {"vae_name": "mystery_vae_xyz.safetensors"}},
    "3": {"class_type": "CLIPLoader",
          "inputs": {"clip_name": "nobody_knows_clip.safetensors", "type": "wan"}},
}


def test_base_licence_receipt_separates_classified_from_merely_examined():
    """F-b7e7c5c0 · operand: a baseline whose three components the table RULED NONE of.

    reverted-red: yes. On the reverted tree `gate_base_licence(UNKNOWN_BASE)` returns
    "3 ruled component(s) read off the baseline, none BANNED and none EXCLUDED" and an
    evidence dict whose keys are ['andon','banned','clause','gate','n_components_examined',
    'path','refused_verdicts','verdict'] — no `classified`, no `unclassified`, nothing a
    reader can use to tell a clean baseline from an unknown one.
    """
    ev = BLA.gate_base_licence(UNKNOWN_BASE)
    assert ev["n_components_examined"] == 3
    assert ev["n_components_classified"] == 0
    assert ev["n_components_unclassified"] == 3
    assert sorted(ev["unclassified"]) == sorted(
        [c for c in ev["unclassified"]]), "the NAMES, not a count"
    joined = " ".join(ev["unclassified"])
    assert "some_unknown_style_v3.safetensors" in joined
    assert "mystery_vae_xyz.safetensors" in joined
    assert "nobody_knows_clip.safetensors" in joined
    # the verdict may not assert that the table ruled what it did not rule
    assert "3 ruled component(s)" not in ev["verdict"]
    assert "0 of 3" in ev["verdict"]
    assert "3 unclassified" in ev["verdict"]


def test_base_licence_receipt_counts_a_conditional_row_it_actually_ruled():
    """F-b7e7c5c0 · the same receipt on a baseline the table DOES rule, incl. CONDITIONAL."""
    ev = BLA.gate_base_licence({
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": TECHNICALLY_COLOR, "weight_dtype": "default"}}})
    assert ev["n_components_examined"] == 1
    assert ev["n_components_classified"] == 1
    assert ev["n_components_unclassified"] == 0
    assert ev["n_components_conditional"] == 1
    assert ev["unclassified"] == []
    assert "1 of 1" in ev["verdict"] and "1 conditional" in ev["verdict"]


def test_base_licence_still_refuses_a_banned_component():
    """F-b7e7c5c0 · the receipt changed; the kill did not. Red on the BANNED direction."""
    with pytest.raises(RG.RouteGate) as exc:
        BLA.gate_base_licence({"900": {"class_type": "DWPreprocessor", "inputs": {}}})
    assert exc.value.evidence["clause"] == "banned_component_in_base"


# ===========================================================================
# F-92f67091 — the CONDITIONAL obligation is said out loud at the moment it
#              is incurred, and rides the record's disclosure block.
# ===========================================================================

def _lora_arm_cli(tmp_path):
    """arm T on the repo's own pinned E12 baseline — the arm that incurs the obligation."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(BLA.__file__)))
    fixture = os.path.join(root, "tests", "fixtures", "E12-w3-camera-i2v.api.json")
    registry = os.path.join(root, "specs", "E14-seeds.json")
    seed = json.loads(open(registry, encoding="utf-8").read())["seeds"][0]
    out = tmp_path / "fresh" / "run"
    return [f"--base={fixture}", "--arm=T", f"--out={out}",
            f"--seeds-registry={registry}", f"--seed={seed}",
            "--subject", "PERFORMER", "--no-canon"], out


def test_the_credit_obligation_is_printed_at_the_moment_it_is_incurred(tmp_path, capsys):
    """F-92f67091 · operand: the OPERATOR-FACING lines of the tool that authors the spend.

    reverted-red: yes. On the reverted tree the success block prints the canon line, the
    ledger verdict, one line per LoRA insertion, PAIR_TIER, the graph path, the record path
    and BUILD_LORA_ARM_OK — and `credit_obligation`, `attribution` and the ROUTE verdict
    appear only inside the JSON. The obligation this grant is conditional on was never said
    out loud, so footage could be taken forward without it.

    The receipt is read BACK off stdout, not off the record.
    """
    argv, out = _lora_arm_cli(tmp_path)
    assert BLA.main(argv) == 0
    printed = capsys.readouterr().out

    assert "CREDIT OBLIGATION" in printed
    # in the ROW's own words, not this builder's
    row = RG.RULED_COMPONENTS["technically_color"]["condition"]
    assert row["creditor"] in printed
    assert row["text"] in printed
    assert "credits" in printed.lower()
    # and the ROUTE verdict, which lived only in the JSON
    record = json.loads(
        (out / "E14-T-payload-record.json").read_text(encoding="utf-8"))
    assert record["gates"]["ROUTE"]["verdict"] in printed


def test_the_record_carries_a_disclosure_block_naming_the_obligation(tmp_path):
    """F-92f67091 · per-route disclosure (CLAUDE.md): the obligation rides the provenance.

    reverted-red: yes — `disclosure` is not a key of the record on the reverted tree.
    """
    argv, out = _lora_arm_cli(tmp_path)
    assert BLA.main(argv) == 0
    record = json.loads(
        (out / "E14-T-payload-record.json").read_text(encoding="utf-8"))
    d = record["disclosure"]
    assert d["conditional_components"] == ["technically_color"]
    assert d["obligations"], "an arm with a CONDITIONAL row states its obligation"
    assert d["obligations"][0]["creditor"] == "renderartist"
    assert d["obligations"][0]["applies_to"] == "published footage from this arm"
    assert d["route_verdict"] == record["gates"]["ROUTE"]["verdict"]


def test_an_arm_with_no_conditional_row_says_so_rather_than_saying_nothing(tmp_path,
                                                                          capsys):
    """F-92f67091 · arm S carries no CONDITIONAL row: the disclosure states that, in words.

    A silent absence and a measured "none" are different receipts; this is the second one.
    """
    argv, out = _lora_arm_cli(tmp_path)
    argv = [("--arm=S" if a == "--arm=T" else a) for a in argv]
    assert BLA.main(argv) == 0
    printed = capsys.readouterr().out
    assert "CREDIT OBLIGATION" in printed
    record = json.loads(
        (out / "E14-S-payload-record.json").read_text(encoding="utf-8"))
    assert record["disclosure"]["conditional_components"] == []
    assert record["disclosure"]["obligations"] == []
