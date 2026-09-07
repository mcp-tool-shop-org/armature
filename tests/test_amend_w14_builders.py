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

    ⚠ CORRECTED 2026-09-05 (wave 25, F-2c15e4e8). This fixture omitted `payload_sha256`,
    and no builder in the tree does: RE-DERIVED on this branch, `grep -c payload_sha256`
    over the nine returns 2 / 4 / 2 / 1 / 2 / 1 / 3 / 2 / 1 — non-zero in every one, and
    `test_amend_w18_builders::test_every_builder_writes_the_field_this_legacy_fixture_omits`
    derives the same thing from the tree. So the fixture was modelling a record shape this
    repo has not written since wave 20, and the untied branch it exercised is a REFUSAL
    now. The digest is computed by the builders' own one derivation,
    `canonical_payload_digest`, not retyped.
    """
    from build_assembly_payload import canonical_payload_digest

    # Wave 35: admission labels come from the payload when --record is passed.
    # Fixture records must carry usable experiment/stage strings (no E09/B2 silent
    # defaults on the gate). Callers may override via verify_kwargs pop-outs.
    experiment = verify_kwargs.pop("experiment", "E09")
    stage = verify_kwargs.pop("stage", "B2")
    return {"tool": "a builder",
            "experiment": experiment,
            "stage": stage,
            "payload_sha256": canonical_payload_digest(api_graph),
            "gates": {"ROUTE": RG.verify(api_graph, **verify_kwargs)}}


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
    from conftest import load_ok_payload
    printed = load_ok_payload(capsys.readouterr().out)
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

    from conftest import load_ok_payload
    printed = load_ok_payload(capsys.readouterr().out)
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


# ===========================================================================
# F-e17613c2 — the i2v `fit` comparison GATES, on both spend builders.
# ===========================================================================

import build_i2v_payload as W1  # noqa: E402
import build_camera_i2v_payload as CAM  # noqa: E402


def _png(tmp_path, name, size):
    """A real PNG at `size`, so the IHDR the builders read is the file's own."""
    import struct
    import zlib

    w, h = size
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    doc = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw))
           + chunk(b"IEND", b""))
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(doc)
    return p


def test_a_native_fit_that_disagrees_with_the_file_is_a_REFUSAL(tmp_path):
    """F-e17613c2 · operand: `fit_agrees_with_the_file`, the value no caller read.

    reverted-red: yes. On the reverted tree this call RETURNS a record whose
    `fit_agrees_with_the_file` is False and whose `fit` sentence says "native", and nothing
    anywhere reads it — the disagreement is visible only to someone who opens the JSON.
    """
    ev = W1.resolve_start_frame(str(_png(tmp_path, "wrong.png", (1024, 576))))
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(ev, "server.png", 832, 480,
                              fit="native — authored at 832x480")
    e = exc.value.evidence
    assert e["clause"] == "fit_disagrees_with_the_file"
    assert e["measured"] == [1024, 576]
    assert e["generation_frame"] == [832, 480]


def test_a_route_that_declares_its_own_non_native_fit_still_passes(tmp_path):
    """F-e17613c2 · the clause keys on the CALLER's sentence, not on the numbers alone.

    A future letterboxing route states its own fit and is recorded, not refused — which is
    why the gate is written against the declaration.
    """
    ev = W1.resolve_start_frame(str(_png(tmp_path, "wide.png", (1024, 576))))
    # `declares_alpha` is the route's statement of what it submits, required since wave 16
    # (F-71ffdbfb); `_png` writes colour type 2, the recorded RGB composite.
    rec = W1.start_image_record(ev, "server.png", 832, 480,
                                fit="letterboxed — 1024x576 padded into 832x480",
                                declares_alpha=False)
    assert rec["fit_agrees_with_the_file"] is False
    assert rec["fit_declares_native"] is False


def test_the_i2v_builder_refuses_the_wrong_sized_start_frame_and_writes_nothing(tmp_path):
    """F-e17613c2 · the gate is inside `build`, so an in-process caller cannot route past it,
    and a refused build leaves no output directory (the repo's standing invariant)."""
    wrong = W1.resolve_start_frame(str(_png(tmp_path, "wrong.png",
                                            (W1.WIDTH + 192, W1.HEIGHT + 96))))
    out = tmp_path / "fresh" / "run"
    with pytest.raises(W1.PayloadError) as exc:
        W1.build({"start_frame": "s.png"}, None, "neg", "pos", [1],
                 start_frame=wrong)
    assert exc.value.evidence["clause"] == "fit_disagrees_with_the_file"
    assert not out.exists()


def test_the_camera_i2v_builder_carries_the_same_refusal(tmp_path):
    """F-e17613c2 · the family: ONE implementation, two routes.

    The sibling calls `W1.start_image_record` with its own wave's frame, so the fix reaches
    it through the same function. Red on wave 1's 832x480 frame handed to a 1024x576 wave —
    the module's own words, "the mutation that actually happened".
    """
    p1 = _png(tmp_path, "w1.png", (832, 480))
    import hashlib
    sha = hashlib.sha256(p1.read_bytes()).hexdigest()
    wrong = CAM.resolve_start_frame(str(p1), sha)
    with pytest.raises(W1.PayloadError) as exc:
        W1.start_image_record(wrong, "server.png", CAM.WIDTH, CAM.HEIGHT,
                              fit=f"native — authored at {CAM.WIDTH}x{CAM.HEIGHT}")
    assert exc.value.evidence["clause"] == "fit_disagrees_with_the_file"
    assert exc.value.evidence["generation_frame"] == [CAM.WIDTH, CAM.HEIGHT]


def test_the_matching_start_frame_still_builds(tmp_path):
    """F-e17613c2 · the direction the gate must NOT fire on."""
    right = W1.resolve_start_frame(str(_png(tmp_path, "ok.png", (W1.WIDTH, W1.HEIGHT))))
    rec = W1.start_image_record(right, "server.png", W1.WIDTH, W1.HEIGHT,
                                fit=f"native — authored at {W1.WIDTH}x{W1.HEIGHT}",
                                declares_alpha=False)
    assert rec["fit_agrees_with_the_file"] is True
    assert rec["fit_declares_native"] is True


# ===========================================================================
# F-b5db1a40 — "no exit was recorded for this job" is not "this job exited
#              zero", and a malformed record is a FETCH clause, not a crash.
# F-a3ba416b — the sibling fetcher gets the SAME per-job exit record, because
#              its `foreach` shape reports only the LAST job's code.
# ===========================================================================

import fetch_run as FR  # noqa: E402
import fetch_t2v_run as FT  # noqa: E402


def _fetch_run_dump(tmp_path, n):
    """A get_output dump for `n` lossless frames, in `fetch_run`'s own shape."""
    doc = {"results": [{"source_node_id": "302", "filename": f"{i:05d}.png",
                        "url": f"https://example.invalid/{i}"} for i in range(n)]}
    p = tmp_path / "dump.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def _stub_downloader(monkeypatch, module, rows_for, write=b"", returncode=0,
                     exits_text=None):
    """A downloader that writes what a real one would and records what we tell it to.

    It reads the manifest and the exits path out of the ENVIRONMENT the module builds, so
    the stub cannot drift from the command the tool actually assembles.
    """
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env[FR.MANIFEST_ENV], encoding="utf-8") as fh:
            jobs = json.load(fh)
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(write)
        target = env.get(FR.EXITS_ENV)
        if target:
            with open(target, "w", encoding="utf-8") as fh:
                if exits_text is not None:
                    fh.write(exits_text)
                else:
                    json.dump(rows_for(jobs), fh)
        return subprocess.CompletedProcess(cmd, returncode, "", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)


def test_a_job_whose_exit_was_never_recorded_is_refused_by_its_own_clause(
        tmp_path, monkeypatch):
    """F-b5db1a40 · operand: the row whose `code` is JSON `null`.

    reverted-red: yes. `failed = [r for r in rows if int(r.get("code") or 0) != 0]` reads a
    null as 0, the row count matches the plan so `downloader_exits_incomplete` does not fire
    either, and Gate EXITS returns "2 download(s), each recording its own exit, all zero".
    Measured on this rig with the module's exact command shape and an unlaunchable
    downloader: process exit 0 and BOTH rows carrying a null code and an empty message — the
    CommandNotFound error goes to the runspace's error stream, not into the captured output.

    The case `verify_downloads` does not backstop is a re-fetch into a re-used run directory
    whose planned frames are already present from a PRIOR run, so the write below is a valid
    PNG: every planned file present, non-empty and PNG-signed, no stray.
    """
    _stub_downloader(
        monkeypatch, FR,
        rows_for=lambda jobs: [{"out": j["out"], "url": j["url"], "code": None,
                                "message": ""} for j in jobs],
        write=FR.PNG_SIGNATURE + b"IHDR-and-the-rest")
    dump = _fetch_run_dump(tmp_path, 2)
    with pytest.raises(FR.FetchHalt) as exc:
        FR.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    ev = exc.value.evidence
    assert ev["clause"] == "downloader_job_exit_unrecorded"
    assert len(ev["unrecorded"]) == 2
    assert ev["unrecorded"][0]["job"].endswith("00000.png"), "the clause names the job"


def test_a_code_that_is_not_a_number_is_unrecorded_too(tmp_path, monkeypatch):
    """F-b5db1a40 · `int()` is kept only for values that are actually present."""
    _stub_downloader(
        monkeypatch, FR,
        rows_for=lambda jobs: [{"out": j["out"], "url": j["url"], "code": "",
                                "message": ""} for j in jobs],
        write=FR.PNG_SIGNATURE + b"IHDR")
    dump = _fetch_run_dump(tmp_path, 1)
    with pytest.raises(FR.FetchHalt) as exc:
        FR.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    assert exc.value.evidence["clause"] == "downloader_job_exit_unrecorded"


def test_a_malformed_exit_record_is_a_FETCH_clause_not_a_crash(tmp_path, monkeypatch):
    """F-b5db1a40 · the second gap in the same reader.

    reverted-red: yes — `json.load` raised a bare `JSONDecodeError`, which left the halt
    block printing exit 1 ("this tool crashed") rather than a FETCH clause with the record
    path a reader could open.
    """
    _stub_downloader(monkeypatch, FR, rows_for=lambda jobs: [],
                     write=FR.PNG_SIGNATURE, exits_text="{not json")
    dump = _fetch_run_dump(tmp_path, 1)
    with pytest.raises(FR.FetchHalt) as exc:
        FR.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    ev = exc.value.evidence
    assert ev["clause"] == "downloader_exits_unreadable"
    assert ev["exits_record"].endswith(FR.EXITS_NAME)


def test_a_record_of_real_zeroes_still_passes(tmp_path, monkeypatch):
    """F-b5db1a40 · the direction the new clause must NOT fire on."""
    _stub_downloader(
        monkeypatch, FR,
        rows_for=lambda jobs: [{"out": j["out"], "url": j["url"], "code": 0,
                                "message": ""} for j in jobs],
        write=FR.PNG_SIGNATURE + b"IHDR")
    dump = _fetch_run_dump(tmp_path, 2)
    assert FR.main(["--dump", dump, "--run", "r",
                    "--root", str(tmp_path / "runs")]) == 0


# ---------------------------------------------------------------- the sibling

def _t2v_dump(tmp_path, n):
    doc = {"results": [{"source_node_id": FT.LOSSLESS_NODE, "filename": f"{i:012x}.png",
                        "url": f"https://example.invalid/{i}"} for i in range(n)]}
    p = tmp_path / "dump.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_the_t2v_fetcher_observes_a_MID_LOOP_download_failure(tmp_path, monkeypatch):
    """F-a3ba416b · operand: a non-zero exit on a job that is NOT the last one.

    reverted-red: yes. The only downloader gate in this fetcher read the pwsh PROCESS code,
    and under its `foreach` shape that code reflects only the LAST native command in the
    loop. Re-measured on this rig 2026-09-04 with a three-element loop: the failure on
    element 1 leaves the process at exit 0; the same loop with the failure on the LAST
    element exits 1. So `if proc.returncode != 0` could not fire on any download failure
    except one in the final job.
    """
    def rows(jobs):
        return [{"out": j["out"], "code": 22 if i == 0 else 0,
                 "message": "curl: (22) 403"} for i, j in enumerate(jobs)]

    _stub_downloader(monkeypatch, FR, rows_for=rows, write=FR.PNG_SIGNATURE,
                     returncode=0)
    with pytest.raises(FR.FetchHalt) as exc:
        FT.main(["--dump", _t2v_dump(tmp_path, 3), "--out", str(tmp_path / "run")])
    ev = exc.value.evidence
    assert ev["clause"] == "downloader_job_exit_nonzero"
    assert ev["process_returncode"] == 0, (
        "the halt must say the PROCESS reported nothing wrong")


def test_the_t2v_fetcher_records_no_signed_url_on_disk(tmp_path, monkeypatch):
    """F-a3ba416b · the sibling's record, carried — WITHOUT carrying its urls.

    `fetch_run`'s `urls.json` is durable by design; this fetcher's `_urls.json` is deleted
    on every path precisely because it holds signed download links (wave 12, F-8ccedf71).
    Its exit record is the same object with the same exposure, so this fetcher asks the
    downloader for the rows and not the urls, and the exposure the earlier fix closed is
    not re-opened by the fix that carries the record.
    """
    def rows(jobs):
        return [{"out": j["out"], "code": 0, "message": ""} for j in jobs]

    _stub_downloader(monkeypatch, FR, rows_for=rows, write=FR.PNG_SIGNATURE + b"IHDR")
    out = tmp_path / "run"
    dump = json.loads(open(_t2v_dump(tmp_path, 2), encoding="utf-8").read())
    jobs = FT.plan(dump["results"], str(out))
    FT.download(jobs, out=str(out))
    assert not (out / "lossless" / "_urls.json").exists()
    record = out / FR.EXITS_NAME
    assert record.exists(), "the per-job exit record this fetcher was left without"
    text = record.read_text(encoding="utf-8")
    assert "url" not in json.loads(text)[0]
    assert "example.invalid" not in text


def test_the_two_fetchers_share_one_downloader_implementation():
    """F-a3ba416b · "carry the sibling's fix rather than a second shape".

    Keyed on BEHAVIOUR — `fetch_t2v_run.download` reaches the sibling's implementation —
    rather than on the word `foreach`, which is the spelling that hid the defect.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(FT))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "download")
    # The DOCSTRING is excluded on purpose: it records the pwsh measurement that made this
    # fix necessary, and a census that read it would refuse the very evidence it rests on.
    # This keys on the CODE — the calls the function makes and the strings it builds.
    body = [st for st in fn.body if not (isinstance(st, ast.Expr)
                                         and isinstance(st.value, ast.Constant)
                                         and isinstance(st.value.value, str))]
    module = ast.Module(body=body, type_ignores=[])
    literals = [n.value for n in ast.walk(module)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("ForEach-Object" in v or "foreach (" in v or "$LASTEXITCODE" in v
                   for v in literals), "a second downloader shape is back"
    called = {n.func.id for n in ast.walk(module)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "fetch_download" in called, (
        "this fetcher builds its own downloader again instead of calling the sibling's")
    assert FT.fetch_download is FR.download


# ===========================================================================
# F-eec3f145 — Gate CEILING counts billable nodes by BEHAVIOUR, not by one
#              hard-coded class spelling.
# ===========================================================================

import build_r2v_payload as R2V  # noqa: E402


def test_gate_ceiling_sees_a_partner_node_it_was_not_spelled_for():
    """F-eec3f145 · operand: the hosted population, on the graph the auditor measured.

    reverted-red: yes. `paid = [... if n.get("class_type") == "Wan2ReferenceVideoApi"]`
    returned `n_paid: 1`, `paid_nodes: ['1']` and the full green verdict "one billable node
    (1); one submission is one charge" on this exact graph, while
    `route_gates.HOSTED_API_CLASS_SUFFIXES` — written to catch "a partner tier that draws
    its own seed" — matches BOTH nodes. The verdict stated a fact about a population it did
    not measure, on the gate standing in front of the repo's one unrecoverable resource.
    """
    graph = {"1": {"class_type": "Wan2ReferenceVideoApi", "inputs": {}},
             "2": {"class_type": "KlingVideoApi", "inputs": {}}}
    with pytest.raises(RG.RouteGate) as exc:
        R2V.gate_one_paid_node(graph)
    ev = exc.value.evidence
    assert ev["clause"] == "hosted_population_is_not_the_expected_node"
    assert ev["n_hosted"] == 2 and ev["n_paid"] == 1
    assert ev["hosted_nodes"] == ["1", "2"]
    assert "KlingVideoApi" in ev["hosted_classes"]


def test_gate_ceiling_quotes_both_numbers_on_the_graph_this_tool_builds():
    """F-eec3f145 · the direction it must not fire on, and the verdict says what it counted."""
    ev = R2V.gate_one_paid_node({"1": {"class_type": R2V.R2V_CLASS, "inputs": {}},
                                 "2": {"class_type": "SaveVideo", "inputs": {}}})
    assert ev["n_paid"] == 1 and ev["n_hosted"] == 1
    assert "HOSTED_API_CLASS_SUFFIXES" in ev["counted_by"]
    assert "one submission is one charge" in ev["verdict"]


def test_gate_ceiling_still_refuses_two_of_the_expected_class():
    """F-eec3f145 · the clause the gate already had, unchanged in behaviour."""
    with pytest.raises(RG.RouteGate) as exc:
        R2V.gate_one_paid_node({"1": {"class_type": R2V.R2V_CLASS, "inputs": {}},
                                "2": {"class_type": R2V.R2V_CLASS, "inputs": {}}})
    assert exc.value.evidence["clause"] == "not_exactly_one_billable_node"


# ===========================================================================
# F-bf18bca8 — an arm that belongs to another experiment is refused by name,
#              not by a KeyError wearing a halt record.
# ===========================================================================

import build_payload as BP  # noqa: E402


def test_an_arm_from_another_experiment_is_refused_by_name(tmp_path):
    """F-bf18bca8 · operand: the (experiment, arm) pairing argparse cannot narrow.

    reverted-red: yes. Measured as a subprocess on the reverted tree:
    `--experiment=E02 --arm=B1` exits 1 having printed
    `BUILD_PAYLOAD_HALT {"error": "KeyError", "message": "'B1'", "evidence": null}` — a
    stdlib key name standing in for a sentence, under the code this file's own `__main__`
    block reserves for "this tool crashed".
    """
    with pytest.raises(BP.PayloadError) as exc:
        BP.main([f"--out={tmp_path / 'p.json'}", "--experiment=E02", "--arm=B1",
                 "--subject", "BLACKGUARD", "--no-canon"])
    ev = exc.value.evidence
    assert ev["clause"] == "arm_not_in_experiment"
    assert ev["experiment"] == "E02" and ev["arm"] == "B1"
    assert ev["arms_for_experiment"] == sorted(BP.EXPERIMENTS["E02"]["arms"])
    assert "B1" in ev["arms_across_experiments"], "the union argparse advertises"
    assert not (tmp_path / "p.json").exists()


def test_the_pairing_gate_is_the_same_one_an_in_process_caller_meets():
    """F-bf18bca8 · ONE implementation: `build` and `main` come through the same check."""
    with pytest.raises(BP.PayloadError) as exc:
        BP.build("B1", experiment="E02")
    assert exc.value.evidence["clause"] == "arm_not_in_experiment"


def test_the_arm_flags_help_says_its_choices_are_the_union(capsys):
    """F-bf18bca8 · `--help` named arms that are not runnable with the chosen experiment.

    Measured in this worktree: EXPERIMENTS carries 4 experiments with 10 arms between
    them, so 30 of the 40 (experiment, arm) pairs argparse accepts are invalid. The
    numbers are derived here, not typed, so the sentence stays true as the table grows.
    """
    pairs = sum(len(e["arms"]) for e in BP.EXPERIMENTS.values())
    union = len({a for e in BP.EXPERIMENTS.values() for a in e["arms"]})
    assert pairs < union * len(BP.EXPERIMENTS), (
        "if every experiment carried every arm there would be nothing to refuse")
    with pytest.raises(SystemExit):
        BP.main(["--help"])
    out = capsys.readouterr().out
    assert "UNION" in out and "gate_experiment_arm" in out


# ===========================================================================
# F-ec454582 — the docstring's closing claim, measured.
# ===========================================================================

def test_only_ONE_of_the_two_root_exemptions_is_bound_to_the_run():
    """F-ec454582 · operand: pattern 1, which carries no run token at all.

    reverted-red: yes on the docstring half — the function's closing sentence read "Bound to
    the run name, so another run's clip left in this directory still raises", and this
    measurement contradicts it for the second pattern. The behaviour is unchanged and
    deliberately so: binding pattern 1 to the run needs `make_review_clip.clip_name` to
    carry a run token, and that tool belongs to instruments-measure.
    """
    run_bound, unbound = FR.derived_root_artifacts("A2")
    assert run_bound.match("A2_review_8fps.mp4"), "pattern 0 IS bound to the run"
    assert not run_bound.match("A0r1_review_8fps.mp4"), "another run's clip is not exempt"
    assert not unbound.match("A0r1_review_8fps.mp4")
    # …and the second pattern exempts a name carrying no run identity whatever, so ANY
    # run's review clip matches it.
    assert unbound.match("review_0.50x_8fps.mp4")
    assert unbound.match("review_1.00x_24fps.webp")
    assert FR.derived_root_artifacts("SOME-OTHER-RUN")[1].match("review_0.50x_8fps.mp4"), (
        "the second pattern is identical for every run, which is the whole finding")


def test_the_docstring_no_longer_claims_both_patterns_are_run_bound():
    """F-ec454582 · the claim is corrected IN PLACE, with the measurement that overturned it.

    A report may not contain a placeholder shaped like evidence, and a docstring may not
    contain a claim the code contradicts; this reads the sentence back.
    """
    doc = FR.derived_root_artifacts.__doc__
    assert "CORRECTION" in doc
    assert "review_0.50x_8fps.mp4" in doc, "the measurement, not a summary of it"
    assert "make_review_clip.clip_name" in doc, "and the reason it cannot be otherwise here"
