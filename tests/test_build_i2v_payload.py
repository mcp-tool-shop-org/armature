"""The no-control I2V graph builder, against the ways E11 stops being E11.

E11's defining property is a NEGATIVE — nothing conditions the generation but one image
and one prompt — and a negative property is exactly the kind that decays without anybody
noticing: a control node added later still generates a video, still passes Gate L, Gate S,
Gate ROUTE and the saved round trip, and still costs the same. So most of what is checked
here is the absence, and each fixture builds the presence and shows it refused.

Nothing here touches the network, and `build` takes its prompts as arguments, so every
fixture is arithmetic on a dict.
"""

import copy
import json
import os

import pytest

from conftest import TOOLS, REPO  # noqa: F401
import build_i2v_payload as B
from armature_core import errors as E
from armature_core import gates as G
from armature_core import route_gates as RG


UPLOADS = {"start_frame": "start.png"}
POS, NEG = "a jointed clay mannequin dancing in a bar", "blurry, low quality"
E11_SEEDS = [2026081231, 2026081232, 2026081233]


#: A resolved start frame, so every fixture below carries the control-input hash wave 10
#: made mandatory (F-531c5f1f). The digest is over a real file rather than a typed constant,
#: because the whole point of the clause is that the tool hashes the artifact.
#:
#: Wave 12, F-08853dfb: the file is a real PNG now, resolved through the tool's own
#: resolver. It used to be 33 bytes of ASCII with `image: None` typed beside it — a fixture
#: standing in for the entire conditioning of an i2v route, shaped exactly like the input
#: the resolver now refuses, and the reason every `built()` record in this module carried
#: `fit_agrees_with_the_file: null` without a single test noticing.
_RESOLVED = {}


def _authored_start_frame(tmp_path, name="start.png", size=(832, 480)):
    """A real PNG on disk, written by the repo's own dependency-free writer."""
    import numpy as np

    from armature_core import pngio

    path = os.path.join(str(tmp_path), name)
    pngio.write_png(path, np.zeros((size[1], size[0], 3), dtype="uint8"))
    return path


def _resolved_start_frame(size=(B.WIDTH, B.HEIGHT)):
    import tempfile

    if size not in _RESOLVED:
        d = tempfile.mkdtemp()
        _RESOLVED[size] = B.resolve_start_frame(
            _authored_start_frame(d, f"start_{size[0]}x{size[1]}.png", size))
    return _RESOLVED[size]


def built(**kw):
    kw.setdefault("registry", E11_SEEDS)
    kw.setdefault("start_frame", _resolved_start_frame())
    return B.build(UPLOADS, kw.pop("seed", E11_SEEDS[0]), kw.pop("negative", NEG),
                   kw.pop("positive", POS), kw.pop("registry"), **kw)


# ------------------------------------------------------------------- the shot's shape

def test_the_defaults_build_e08s_frame_because_the_ab_needs_them_to():
    """65 @ 16 fps is E08's, and the deliverable is the two probes side by side at true
    tempo. A different length or rate here would put a third variable into a comparison
    that already spans two models and two conditioning routes."""
    wf, meta = built()
    assert (meta["resolution"], meta["length"], meta["fps"]) == ([832, 480], 65, 16)
    assert wf["50"]["inputs"]["length"] == 65
    assert wf["80"]["inputs"]["fps"] == 16


def test_the_two_experts_are_both_loaded_and_neither_is_a_lora():
    wf, meta = built()
    unets = sorted(n["inputs"]["unet_name"] for n in wf.values()
                   if n["class_type"] == "UNETLoader")
    assert unets == sorted([B.UNET_HIGH, B.UNET_LOW])
    assert meta["models"]["loras"] == []
    assert not any(n["class_type"].startswith("LoraLoader") for n in wf.values())


def test_the_trajectory_values_are_the_ones_the_record_claims():
    wf, _ = built()
    hi, lo = wf["60"]["inputs"], wf["61"]["inputs"]
    assert (hi["steps"], hi["cfg"], hi["sampler_name"], hi["scheduler"]) == \
        (20, 3.5, "euler", "simple")
    assert (hi["start_at_step"], hi["end_at_step"]) == (0, 10)
    assert (lo["start_at_step"], lo["end_at_step"]) == (10, 10000)
    assert wf["12"]["inputs"]["shift"] == wf["13"]["inputs"]["shift"] == 8.0


# ---------------------------------------------------- the defining property: no control

@pytest.mark.parametrize("cls", ["WanVaceToVideo", "WanAnimateToVideo",
                                 "Wan22FunControlToVideo", "ControlNetApplyAdvanced"])
def test_any_control_capable_conditioning_class_refuses_the_graph(cls):
    """The failure this exists for is not an error — it is a different experiment wearing
    E11's file names. A control node present is one edit from being fed, and the licence
    map's own ruling on a bypassed node is that presence is presence."""
    wf, _ = built()
    wf["99"] = {"class_type": cls, "inputs": {}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert cls in str(exc.value)


def test_a_second_uploaded_image_refuses_the_graph():
    """A reference image, a scene plate, a last frame — whatever it is labelled, a second
    LoadImage is a second conditioning channel, and E11's question is what one channel
    does on its own."""
    wf, _ = built()
    wf["42"] = {"class_type": "LoadImage", "inputs": {"image": "reference.png"}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "second uploaded image" in str(exc.value)


def test_wiring_clip_vision_refuses_the_graph():
    wf, _ = built()
    wf["50"]["inputs"]["clip_vision_output"] = ["45", 0]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "clip_vision_output" in str(exc.value)


def test_a_sampler_fed_straight_from_the_text_encode_refuses_the_graph():
    """The silent one. Wire the text encodes to the samplers instead of to the
    conditioning node's outputs and the graph still runs, still costs the same, and still
    returns 65 frames — of a video the start image never conditioned. Nothing else in the
    chain looks at which CONDITIONING a sampler received."""
    wf, _ = built()
    wf["60"]["inputs"]["positive"] = ["30", 0]
    wf["60"]["inputs"]["negative"] = ["31", 0]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "conditioning" in str(exc.value)


def test_the_experts_must_hand_over_at_the_same_step():
    """A gap repeats part of the trajectory and an overlap skips part of it. Both produce
    a complete, well-formed clip at the same price."""
    wf, _ = built()
    wf["61"]["inputs"]["start_at_step"] = 12
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "hand over" in str(exc.value)


def test_the_low_noise_expert_must_continue_the_high_noise_latent():
    wf, _ = built()
    wf["61"]["inputs"]["latent_image"] = ["50", 2]
    with pytest.raises(B.PayloadError,
                       match=r"low-noise sampler does not continue the high-noise latent"):
        B.verify_topology(wf, "start.png")


def test_the_gate_b_probe_must_read_the_upload_directly():
    """A probe reading anything but the LoadImage output proves nothing about what the
    server decoded, which is the only half the local round trip cannot check."""
    wf, _ = built()
    wf["41"]["inputs"]["images"] = ["70", 0]
    with pytest.raises(B.PayloadError,
                       match=r"Gate B probe does not read the start-frame LoadImage"):
        B.verify_topology(wf, "start.png")


def test_the_lossless_tap_must_read_the_decode_directly():
    wf, _ = built()
    wf["71"]["inputs"]["images"] = ["40", 0]
    with pytest.raises(B.PayloadError,
                       match=r"lossless tap does not read VAEDecode directly"):
        B.verify_topology(wf, "start.png")


def test_a_link_to_a_node_that_does_not_exist_refuses_the_graph():
    wf, _ = built()
    wf["70"]["inputs"]["samples"] = ["999", 0]
    with pytest.raises(B.PayloadError,
                       match=r"node 70\.samples links to missing node 999"):
        B.verify_topology(wf, "start.png")


# ------------------------------------------------------------------------- Gate L / S

@pytest.mark.parametrize("length", [64, 66, 85])
def test_gate_l_raises_on_an_illegal_frame_count(length):
    """64 and 66 are not 4n+1; 85 is past the trained horizon. Each would generate."""
    with pytest.raises((E.G1GeneratorLegality, RG.RouteGate)):
        built(length=length)


def test_gate_l_accepts_the_lengths_this_route_is_documented_at():
    for length in (65, 81):
        wf, meta = built(length=length)
        assert meta["gate_L"]["verdict"] == "PASS"


def test_gate_s_raises_on_a_seed_the_committed_list_does_not_carry():
    with pytest.raises(E.GateSSeedRegistration,
                       match=r"\[S\] seed 1234 is not in E11's pre-registered list of 3"):
        built(seed=1234)


def test_gate_s_raises_when_a_seed_is_varied_with_no_registry_at_all():
    """An experiment that pre-registered nothing may not vary its seed — the clause that
    stops a `--seed` flag turning every unregistered experiment into a shoppable one."""
    with pytest.raises(E.GateSSeedRegistration,
                       match=r"\[S\] E11 has no pre-registered seed list, so its seed may"):
        built(seed=2026081231, registry=None)


# -------------------------------------------------------------------- Gate ROUTE / L

def test_gate_route_finds_the_latent_without_being_handed_the_frame():
    """The load-bearing half of the LATENT_NODES addition.

    `WanImageToVideo` sizes its own latent, so this graph contains no `Empty*LatentVideo`
    node. Without the table entry Gate L examines zero latents — the exact E08 defect —
    and with `frame=` supplied that stays invisible, because the supplied number passes on
    its own. So this asks the gate the question with nothing supplied.
    """
    wf, _ = built()
    ev = RG.verify(wf)
    assert ev["latents_checkable"] == 1
    assert ev["frame_legality_verdict"] == "PROVEN"
    assert [(f["width"], f["height"], f["length"]) for f in ev["frame_legality"]] \
        == [(832, 480, 65)]


def test_without_the_table_entry_gate_l_goes_indeterminate_and_raises():
    """The companion, reconstructing the pre-fix world. If someone removes the entry as
    'unused', this fails rather than the gate quietly passing on nothing."""
    wf, _ = built()
    saved = RG.LATENT_NODES.pop("WanImageToVideo")
    try:
        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(wf)
        assert "INDETERMINATE" in str(exc.value)
    finally:
        RG.LATENT_NODES["WanImageToVideo"] = saved


def test_gate_route_refuses_a_graph_carrying_the_excluded_speed_lora():
    """The served template at `main` wires exactly this, at strength 1.0, inside a
    subgraph blueprint. The route gate is what stands between that file and a run."""
    wf, _ = built()
    wf["101"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
        "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
        "strength_model": 1.0, "model": ["12", 0]}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(832, 480, 65))
    assert "lightx2v" in str(exc.value)


def test_a_supplied_frame_that_disagrees_with_the_graph_raises():
    """Both numbers would be legal, so nothing downstream would notice that the number in
    the report is not the number that ran."""
    wf, _ = built()
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(832, 480, 81))
    assert "pins" in str(exc.value)


# ---------------------------------------------------------------------------- Gate PIN

def _fake_e08(tmp_path, positive=POS, negative=NEG):
    p = tmp_path / "E08-probe-payload-record.json"
    p.write_text(json.dumps({"experiment": "E08", "seed": 2026081211,
                             "positive": positive, "negative": negative}),
                 encoding="utf-8")
    return str(p)


def test_gate_pin_passes_when_the_strings_are_byte_identical(tmp_path):
    ev = B.pin_against_e08(POS, NEG, _fake_e08(tmp_path))
    assert ev["verdict"].startswith("positive and negative byte-identical")
    assert ev["positive"]["sha256_built"] == ev["positive"]["sha256_e08"]


@pytest.mark.parametrize("field", ["positive", "negative"])
def test_gate_pin_fires_on_a_single_character_of_drift(field):
    """One character. The A/B's whole claim is 'same prompt, different route', and a
    prompt that drifted by a word would make the sheet a comparison of two prompts as
    well — with no symptom anywhere, because both strings encode fine."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        kw = {field: (POS if field == "positive" else NEG) + "."}
        rec = _fake_e08(__import__("pathlib").Path(d), **kw)
        with pytest.raises(B.PayloadError) as exc:
            B.pin_against_e08(POS, NEG, rec)
        assert field in str(exc.value)


def test_gate_pin_fires_when_the_record_carries_no_string_at_all(tmp_path):
    """A missing field must not read as agreement — the failure mode this repo's stale
    labels keep producing."""
    p = tmp_path / "rec.json"
    p.write_text(json.dumps({"experiment": "E08"}), encoding="utf-8")
    with pytest.raises(B.PayloadError,
                       match=r"record carries no positive string to pin against"):
        B.pin_against_e08(POS, NEG, str(p))


# ------------------------------------------- the citation check, against the banked file

BANKED = os.path.join(REPO, "outputs", "E11", "route",
                      "i2v_template_5d6089c4250f.json")


@pytest.mark.skipif(not os.path.exists(BANKED),
                    reason="the banked template lives under gitignored outputs/")
def test_every_trajectory_value_is_actually_in_the_file_it_cites():
    """E09's citation check, pointed at E11's numbers.

    A source string in a record is a claim about a file. This reads the file. The failure
    it catches is the one that fired in E09 — a seat describing a banked source from
    memory — and the reason it matters here is that these six numbers are the entire
    difference between running the documented trajectory and running an invented one.
    """
    doc = json.load(open(BANKED, encoding="utf-8"))
    by_type = {}
    for n in doc["nodes"]:
        by_type.setdefault(n["type"], []).append(n)

    assert len(by_type["LoraLoaderModelOnly"] if "LoraLoaderModelOnly" in by_type
               else []) == 0, "the cited revision is supposed to carry no LoRA at all"

    samplers = sorted(by_type["KSamplerAdvanced"],
                      key=lambda n: n["widgets_values"][7])          # by start_at_step
    hi, lo = (n["widgets_values"] for n in samplers)
    assert hi[3] == lo[3] == B.TRAJECTORY["steps"]["value"]
    assert hi[4] == lo[4] == B.TRAJECTORY["cfg"]["value"]
    assert hi[5] == lo[5] == B.TRAJECTORY["sampler_name"]["value"]
    assert hi[6] == lo[6] == B.TRAJECTORY["scheduler"]["value"]
    assert hi[8] == lo[7] == B.TRAJECTORY["split_step"]["value"]

    shifts = [n["widgets_values"][0] for n in by_type["ModelSamplingSD3"]]
    assert all(abs(s - B.TRAJECTORY["shift"]["value"]) < 1e-9 for s in shifts), shifts

    assert by_type["CreateVideo"][0]["widgets_values"][0] == B.TRAJECTORY["fps"]["value"]

    unets = sorted(n["widgets_values"][0] for n in by_type["UNETLoader"])
    assert unets == sorted([B.UNET_HIGH, B.UNET_LOW])
    assert by_type["CLIPLoader"][0]["widgets_values"][0] == B.CLIP_NAME
    assert by_type["VAELoader"][0]["widgets_values"][0] == B.VAE_NAME


@pytest.mark.skipif(not os.path.exists(BANKED),
                    reason="the banked template lives under gitignored outputs/")
def test_the_cited_revision_leaves_clip_vision_unconnected_too():
    doc = json.load(open(BANKED, encoding="utf-8"))
    node = next(n for n in doc["nodes"] if n["type"] == "WanImageToVideo")
    slot = next(i for i in node["inputs"] if i["name"] == "clip_vision_output")
    assert slot["link"] is None
    start = next(i for i in node["inputs"] if i["name"] == "start_image")
    assert start["link"] is not None


# ------------------------------------------------------------------ the seed default
#
# Wave 3, F-8898e2da — the same dead fallback, in the same shape, on this tool.


def test_omitting_the_seed_builds_on_the_first_registered_seed():
    wf, meta = built(seed=None)
    assert meta["seed"] == sorted(E11_SEEDS)[0]
    assert meta["gate_S"]["seed_was_explicit"] is False


def test_omitting_the_seed_with_no_registry_names_the_missing_flag():
    with pytest.raises(B.PayloadError) as exc:
        built(seed=None, registry=None)
    assert "--seed" in str(exc.value)


# =======================================================================================
# wave 10, F-531c5f1f — the one image this route conditions on is now IN the record
# =======================================================================================
#
# On E11's route the start frame IS the entire image conditioning (this module's own
# docstring: "nothing else conditions the generation"), and the payload record named no
# local artifact for it. Measured by walking both siblings' argparse trees on 2026-09-04:
# `build_camera_i2v_payload` declares `--start-frame` and `--start-frame-sha256` and hashes
# the file in `resolve_start_frame`; `build_i2v_payload` declared NEITHER. Its only image
# input was `--uploads`, and `meta['start_image']` carried a server-side content-addressed
# `server_name`, a prose `fit` string ("native — authored at 832x480") and a `why`
# paragraph. Every `sha256` in the module was over a STRING or the graph. So an E11 record
# could not be re-run from, and a re-authored or re-composited start frame left no trace
# that would show a run was not comparable to the previous one.


def test_omitting_the_start_frame_flag_RAISES(tmp_path):
    """The sibling's clause, carried: a record that cannot name the bytes of the one image
    the generation is conditioned on is not a recipe."""
    with pytest.raises(B.PayloadError, match="--start-frame is required"):
        B.resolve_start_frame(None)


def test_a_start_frame_path_that_is_not_a_file_RAISES(tmp_path):
    with pytest.raises(B.PayloadError, match="is not a file"):
        B.resolve_start_frame(str(tmp_path / "never-authored.png"))


def test_a_declared_digest_that_disagrees_with_the_bytes_HALTS(tmp_path):
    """A declared digest is a cross-check, never the record's source. One of the two names
    a different artifact and the record may not carry a digest the bytes do not support."""
    path = _authored_start_frame(tmp_path)
    with pytest.raises(B.PayloadError, match="does not hash to the file"):
        B.resolve_start_frame(str(path), "0" * 64)


def test_the_carried_refusal_names_the_sibling_it_came_from(tmp_path):
    """One implementation, imported. The receipt says where the clause lives."""
    with pytest.raises(B.PayloadError) as exc:
        B.resolve_start_frame(None)
    assert exc.value.evidence["carried_from"] == (
        "build_camera_i2v_payload.resolve_start_frame")
    assert exc.value.evidence["flag"] == "--start-frame"


def test_a_declared_digest_that_AGREES_is_recorded_as_confirmed(tmp_path):
    """The mutation that must not fire it."""
    import hashlib

    path = _authored_start_frame(tmp_path)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    ev = B.resolve_start_frame(str(path), digest.upper())
    assert ev["sha256"] == digest
    assert ev["source"].endswith("confirmed_against_the_declared_value")


def test_build_refuses_to_emit_a_payload_with_no_resolved_start_frame():
    """The gate lives inside `build`, not in `main`, so an in-process caller cannot route
    around it."""
    with pytest.raises(B.PayloadError, match="needs the resolved start frame"):
        B.build(UPLOADS, E11_SEEDS[0], NEG, POS, E11_SEEDS, start_frame=None)


def test_the_record_carries_the_local_path_hash_and_size(tmp_path):
    path = _authored_start_frame(tmp_path)
    ev = B.resolve_start_frame(str(path))
    _wf, meta = built(start_frame=ev)
    start = meta["start_image"]
    assert start["sha256"] == ev["sha256"] and len(start["sha256"]) == 64
    assert start["path"] == os.path.abspath(str(path))
    assert start["bytes"] == os.path.getsize(str(path))
    assert start["server_name"] == UPLOADS["start_frame"], "the server name still rides"


def test_the_asserted_fit_is_now_checkable_against_the_file(tmp_path):
    """`fit: "native — authored at 832x480"` was an assertion about an image the tool never
    opened, so nothing could contradict it. It sits beside a measurement now."""
    ev = B.resolve_start_frame(str(_authored_start_frame(tmp_path)))
    start = built(start_frame=ev)[1]["start_image"]
    assert start["measured"]["width"] == B.WIDTH
    assert start["measured"]["height"] == B.HEIGHT
    assert start["fit_agrees_with_the_file"] is True

    # …and on the input it exists to catch — a start frame authored at the wrong size — it
    # REFUSES. Wave 14, F-e17613c2: this assertion used to read
    # `assert built(start_frame=wrong)[1]["start_image"]["fit_agrees_with_the_file"] is
    # False`, and it PINNED the non-refusal. The comparison was computed, written into the
    # record, and read by nothing: measured by grep 2026-09-04, `fit_agrees_with_the_file`
    # occurs in the two writers and in tests, and nowhere under tools/, docs/ or verify.ps1.
    # A paid i2v generation could therefore go out on a start frame at the wrong resolution
    # with every printed gate line green, on the one input that is the whole of this route's
    # conditioning — and spent credits have no compensator. A diagnostic and a gate are
    # different objects; this is the gate.
    wrong = B.resolve_start_frame(str(_authored_start_frame(
        tmp_path, name="wrong.png", size=(1024, 576))))
    with pytest.raises(B.PayloadError, match=r"declares a NATIVE fit") as exc:
        built(start_frame=wrong)
    assert exc.value.evidence["clause"] == "fit_disagrees_with_the_file"
    assert exc.value.evidence["measured"] == [1024, 576]
    assert exc.value.evidence["generation_frame"] == [B.WIDTH, B.HEIGHT]


def test_the_record_says_whether_the_authored_input_carried_ALPHA(tmp_path):
    """The Director's 2026-08-12 ruling, made machine-readable: an authored input carries
    alpha and the RGB composite a route submits is a recorded choice. The colour type comes
    from the file's own IHDR, so a flattened re-author is visible in the record."""
    ev = B.resolve_start_frame(str(_authored_start_frame(tmp_path)))
    measured = built(start_frame=ev)[1]["start_image"]["measured"]
    assert measured["color_type"] == "rgb"
    assert measured["alpha"] is False
    assert "no image library" in measured["read_by"]


def test_the_png_header_reader_refuses_to_guess_at_a_non_png(tmp_path):
    """A file that is not a PNG returns None rather than a plausible dict — an absent
    measurement, not an invented one.

    **Wave 12, F-08853dfb — the second half of this test used to be the defect.** It read
    `assert built(start_frame=ev)[1]["start_image"]["fit_agrees_with_the_file"] is None`:
    the reader declined to guess, the resolver stored the None with no clause, and the build
    PROCEEDED, so a file with a JPEG header rode this route as the whole of its conditioning
    under a printed BUILD_I2V_OK while the record's asserted `fit` sentence stood beside a
    null comparison. The reader's job is unchanged; the RESOLVER refuses now."""
    import build_camera_i2v_payload as CAM

    junk = tmp_path / "not.png"
    junk.write_bytes(b"this is not a png" * 4)
    assert CAM.png_header(str(junk)) is None
    with pytest.raises(B.PayloadError, match="is not a PNG this tool can read") as exc:
        B.resolve_start_frame(str(junk))
    assert exc.value.evidence["carried_from"] == (
        "build_camera_i2v_payload.resolve_start_frame")


def test_a_start_frame_the_tool_could_not_open_never_reaches_a_RECORD(tmp_path):
    """The whole chain, on the input the finding measured: a 403-byte file whose first
    bytes are a JPEG header. It used to be ACCEPTED, with `image: None` in the evidence and
    a null in the record."""
    junk = tmp_path / "start.png"
    junk.write_bytes(bytes.fromhex("ffd8ffe0") + b"0123456789" * 40)
    with pytest.raises(B.PayloadError, match="is not a PNG this tool can read"):
        B.resolve_start_frame(str(junk))


def test_build_refuses_an_evidence_dict_that_carries_no_measurement():
    """The in-process door the resolver's refusal does not cover. `build`'s only start-frame
    requirement was `start_frame.get("sha256")`."""
    unmeasured = dict(_resolved_start_frame(), image=None)
    with pytest.raises(B.PayloadError, match="carries no measurement") as exc:
        built(start_frame=unmeasured)
    assert exc.value.evidence["clause"] == "start_frame_unmeasured"


def test_the_record_never_carries_a_NULL_agreement_flag(tmp_path):
    """`None if not start_frame.get("image") else [...]` degraded the one comparison on
    exactly the input that most needed it. With both doors closed the flag is a boolean."""
    assert built()[1]["start_image"]["fit_agrees_with_the_file"] in (True, False)


def test_both_i2v_builders_declare_the_same_two_start_frame_flags():
    """The family, derived from the parsers rather than from the docstrings: every builder
    whose graph conditions on ONE uploaded start image declares `--start-frame` and
    `--start-frame-sha256`. `build_i2v_payload` declared neither until wave 10."""
    import ast

    family = []
    for name in ("build_i2v_payload.py", "build_camera_i2v_payload.py"):
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        flags = {n.args[0].value for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "add_argument" and n.args
                 and isinstance(n.args[0], ast.Constant)}
        family.append((name, {"--start-frame", "--start-frame-sha256"} <= flags))
    assert family == [("build_i2v_payload.py", True),
                      ("build_camera_i2v_payload.py", True)], family
