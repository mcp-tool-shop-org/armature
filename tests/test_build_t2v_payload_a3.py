"""A3's `reference` profile, checked before a credit is spent on it.

Every check asks CLAUDE.md's question — what would this look like if the code were wrong
in the specific way this check exists to catch — against a failure that has already
happened once. The 2026-08-11 probe ran a trajectory no document could be pointed at, and
when the donor came back near-still with the feet cropped away, the report could not say
whether the graph or the prompt produced it. The checks here are what make the next report
able to answer that: the values are verified against the banked bytes of the documents
they claim to come from, and the two profiles are verified to actually differ.
"""

import json
import os

import pytest

from conftest import TOOLS, REPO, requires_bank  # noqa: F401
import build_t2v_payload as B
from armature_core import route_gates as RG


SEEDS = json.load(open(os.path.join(REPO, "specs", "E09-seeds.json"), encoding="utf-8"))
A3_SEEDS = json.load(open(os.path.join(REPO, "specs", "E09-A3-seeds.json"),
                          encoding="utf-8"))
BANK = os.path.join(REPO, "outputs", "E09", "route2")

#: The banked documents are outputs, and `outputs/` is out of git. A checkout without them
#: must skip the byte-level citation checks rather than fail — but it must SAY it skipped,
#: which is what a skip reason is for.
_banked = os.path.isdir(BANK)
#: lever defaults inside `requires_bank`; do not re-spell `"outputs/"` here — the
#: output-path census treats a bare outputs string on this assignment as cwd-relative.
needs_bank = requires_bank(BANK)

def test_the_default_profile_is_the_one_a3_authorises():
    """A silent default that produced the superseded trajectory is exactly the defect this
    profile exists to end. An unqualified call must not be able to run it."""
    graph, t = B.build_graph(A3_SEEDS["seeds"][0])
    assert t["profile"] == "reference"
    assert graph["50"]["inputs"]["steps"] == 20


def test_the_reference_split_is_read_off_the_document_not_solved():
    """The whole point of the profile. If someone re-derives the split here, the value may
    even land in the same place one day and the provenance is still gone."""
    t = B.trajectory("reference")
    assert t["split_step"] == 10
    assert t["steps"] == 20
    assert "READ OFF" in t["split_origin"]
    assert "SOLVED" in B.trajectory("derived")["split_origin"]


def test_every_reference_value_names_a_document_and_two_agreeing_commits():
    for key, rec in B.COMFY_REFERENCE.items():
        assert "workflow_templates" in rec["source"], key
        assert rec["agrees_at"] == B.COMFY_PINS, key
    # ...and the two suspects A3 named are now sourced rather than excused
    for key in ("sampler_name", "scheduler"):
        assert "port necessity" not in B.COMFY_REFERENCE[key]["source"], key


@needs_bank
def test_the_two_pinned_revisions_actually_carry_these_values():
    """The citation is checked against the banked bytes, not trusted. A number that
    drifted out of the document it claims to come from fails here and names itself."""
    for sha in B.COMFY_PINS:
        doc = json.load(open(os.path.join(BANK, f"template_{sha}.json"), encoding="utf-8"))
        adv = [n for n in doc["nodes"] if n["type"] == "KSamplerAdvanced"]
        # The non-distilled pair carries cfg 3.5. The later pinned revision carries a
        # 4-step lightning pair alongside it, so SELECT the pair rather than assume the
        # file holds only two samplers — assuming is how the wrong pair gets quoted.
        full = [n["widgets_values"] for n in adv if n["widgets_values"][4] == 3.5]
        assert len(full) == 2, (sha, [n["widgets_values"] for n in adv])
        high = [w for w in full if w[0] == "enable"][0]
        low = [w for w in full if w[0] == "disable"][0]
        assert high[3] == low[3] == B.COMFY_REFERENCE["sample_steps"]["value"]
        assert high[4] == low[4] == B.COMFY_REFERENCE["cfg"]["value"]
        assert high[5] == low[5] == B.COMFY_REFERENCE["sampler_name"]["value"]
        assert high[6] == low[6] == B.COMFY_REFERENCE["scheduler"]["value"]
        assert high[7] == 0
        assert high[8] == low[7] == B.COMFY_REFERENCE["split_step"]["value"]
        shifts = {round(n["widgets_values"][0], 6) for n in doc["nodes"]
                  if n["type"] == "ModelSamplingSD3"}
        assert B.COMFY_REFERENCE["sample_shift"]["value"] in shifts, (sha, shifts)


@needs_bank
def test_the_reference_wiring_is_the_shape_this_graph_builds():
    """Traced through the `links` array, not read off node order — node order is not
    wiring, and a graph that pairs the low-noise expert with the first sampler would run
    the two experts backwards while every other check passed."""
    doc = json.load(open(os.path.join(BANK, "template_5d6089c4250f.json"), encoding="utf-8"))
    byid = {n["id"]: n for n in doc["nodes"]}
    links = {l[0]: l[1] for l in doc["links"]}

    def upstream(node, name):
        for i in node.get("inputs", []):
            if i["name"] == name and i.get("link") is not None:
                return byid[links[i["link"]]]
        return None

    for n in doc["nodes"]:
        if n["type"] != "KSamplerAdvanced":
            continue
        unet = upstream(upstream(n, "model"), "model")
        adds_noise = n["widgets_values"][0] == "enable"
        expected = "high_noise" if adds_noise else "low_noise"
        assert expected in unet["widgets_values"][0], (n["id"], unet["widgets_values"])


@needs_bank
def test_the_banked_main_revision_is_the_excluded_one_and_gate_route_says_so():
    """The reason the pins exist. If a later session re-fetches `main` believing it is the
    reference, this is the check that already wrote down why it is not."""
    doc = json.load(open(os.path.join(
        BANK, "comfy_template_video_wan2_2_14B_t2v.json"), encoding="utf-8"))
    excluded = [c for c in RG.components(doc) if "lightx2v" in c["file"]]
    assert excluded, "main was expected to carry the lightx2v LoRAs"
    assert all(c["ruling"]["verdict"] == "EXCLUDED" for c in excluded)
    with pytest.raises(RG.RouteGate, match=r"the graph loads .*lightx2v.*EXCLUDED"):
        RG.verify(doc)


def _negatives(sha):
    doc = json.load(open(os.path.join(BANK, f"template_{sha}.json"), encoding="utf-8"))
    return [n["widgets_values"][0] for n in doc["nodes"]
            if n["type"] == "CLIPTextEncode"
            and n["widgets_values"][0].startswith(B.REFERENCE_NEGATIVE[:8])]


@needs_bank
def test_the_earlier_pin_reproduces_wans_own_negative_byte_for_byte():
    assert B.REFERENCE_NEGATIVE in _negatives("5d6089c4250f")


@needs_bank
def test_the_later_pin_drifted_from_it_and_the_drift_is_recorded_not_inherited():
    """This test FAILED first, on a claim this seat wrote from a glance rather than a
    comparison: that both pinned revisions carried the same negative. They do not. The two
    agree on every sampling value and disagree here, `dcc00d29d79d` having appended two
    tokens. The graph keeps Wan's own upstream string; the difference stays in the tree so
    the next session does not get to rediscover it."""
    later = _negatives("dcc00d29d79d")
    assert later, "the later pin was expected to carry a Wan-descended negative"
    assert B.REFERENCE_NEGATIVE not in later
    for text in later:
        assert text.startswith(B.REFERENCE_NEGATIVE)          # an append, not a rewrite
        assert text[len(B.REFERENCE_NEGATIVE):] == "，裸露，NSFW"
    assert "NSFW" in B.NEGATIVE_DRIFT["dcc00d29d79d"]
    assert "NSFW" not in B.REFERENCE_NEGATIVE


def test_the_reference_graph_carries_the_documented_values_on_both_samplers():
    graph, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    hi, lo = graph["50"]["inputs"], graph["51"]["inputs"]
    assert hi["cfg"] == lo["cfg"] == 3.5          # symmetric, unlike Wan's native pair
    assert hi["sampler_name"] == lo["sampler_name"] == "euler"
    assert hi["scheduler"] == lo["scheduler"] == "simple"
    assert hi["steps"] == lo["steps"] == 20
    assert hi["start_at_step"] == 0 and hi["end_at_step"] == 10
    assert lo["start_at_step"] == 10 and lo["end_at_step"] >= 20
    assert graph["12"]["inputs"]["shift"] == graph["13"]["inputs"]["shift"] == 8.0


def test_the_two_profiles_actually_differ_where_the_delta_table_says_they_do():
    """A diagnostic whose independent variable did not move is not a diagnostic."""
    ref, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    der, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="derived")
    assert ref["50"]["inputs"]["steps"] != der["50"]["inputs"]["steps"]
    assert ref["50"]["inputs"]["end_at_step"] != der["50"]["inputs"]["end_at_step"]
    assert ref["12"]["inputs"]["shift"] != der["12"]["inputs"]["shift"]
    assert ref["50"]["inputs"]["cfg"] != der["50"]["inputs"]["cfg"]
    # ...and the FRACTION of steps on the high-noise expert, which is what a split is.
    # Two graphs could differ in every raw number above and still split at the same place.
    assert ref["50"]["inputs"]["end_at_step"] / ref["50"]["inputs"]["steps"] == 0.5
    assert der["50"]["inputs"]["end_at_step"] / der["50"]["inputs"]["steps"] == 26 / 40


def test_the_a3_prompt_answers_each_measured_failure_of_the_probe():
    """Not 'the prompt changed' — the specific clauses whose presence or absence the
    probe's own measurements pointed at."""
    p = B.PROMPT_A3.lower()
    assert "mid-shot" not in p              # the term of art that framed out the feet
    assert "slowly" not in p                # the clip measured 0.703/255 of motion
    assert "full-length wide shot" in p
    assert "feet on the floor" in p and "below her feet" in p
    assert "large, fast, sweeping movements" in p
    assert "clear of her torso" in p        # the B1/B2 occlusion finding, kept
    assert "one person only" in p and "camera does not move" in p
    assert len(B.PROMPT_CHANGE_LOG) >= 4
    for row in B.PROMPT_CHANGE_LOG:
        assert row["answers"], row


def test_the_probes_prompt_still_contains_the_clause_that_framed_out_the_feet():
    """The evidence for the change, kept runnable beside it. If this stops being true, the
    change log is describing a prompt that is not in the tree."""
    assert "mid-shot" in B.PROBE_PROMPT.lower()
    assert "slowly and evenly" in B.PROBE_PROMPT.lower()


def test_the_reference_graph_passes_all_three_admission_gates():
    graph, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    RG.verify(graph)
    RG.gate_s_registration(graph, A3_SEEDS["seeds"])
    assert RG.frame_legality(B.WIDTH, B.HEIGHT, B.LENGTH)["legal"]


def test_the_old_seed_list_no_longer_admits_the_a3_graph():
    """Gate S binds in both directions. An A3 graph running against the probe's list is a
    seed no committed list pre-registered FOR THIS RUN."""
    graph, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] Gate S: node 50 would run seed 2026081201, which"):
        RG.gate_s_registration(graph, SEEDS["seeds"])


def test_the_a3_seed_list_is_disjoint_from_the_probes():
    assert not set(A3_SEEDS["seeds"]) & set(SEEDS["seeds"])


def test_an_unknown_profile_raises_rather_than_silently_picking_one():
    with pytest.raises(RG.RouteGate, match=r"\[ROUTE\] unknown profile 'whatever'"):
        B.trajectory("whatever")


def test_the_boundary_cross_check_is_reported_and_gates_nothing():
    """The arithmetic that governed the probe is kept as a diagnostic here. It has to be
    visible in the record and it must not be able to stop the run — the documented value
    governs, and a disagreement with the arithmetic is a finding, not a fault."""
    x = B.trajectory("reference")["boundary_cross_check"]
    assert x["documented_split_step"] == 10
    assert x["step_wan_native_boundary_would_put_it_at"] == 11
    assert x["agree_within_one_step"] is True
    assert "not a gate" in x["status"].lower()


def test_the_lossless_tap_survives_the_profile_change():
    """The review is at 0.5x from lossless. A profile switch that quietly dropped the PNG
    tap would leave the Director judging an H.264 clip."""
    graph, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    save = [n for n in graph.values() if n["class_type"] == "SaveImage"]
    assert len(save) == 1 and save[0]["inputs"]["images"] == ["60", 0]
    assert graph["60"]["class_type"] == "VAEDecode"


def test_the_reference_graph_loads_no_lora_of_any_kind():
    """Not 'no excluded LoRA' — no LoRA. The document these values come from carries two
    of them at `main`, so this clause is doing live work."""
    graph, _ = B.build_graph(A3_SEEDS["seeds"][0], profile="reference")
    for node in graph.values():
        assert "lora" not in node["class_type"].lower(), node
        for v in node["inputs"].values():
            if isinstance(v, str):
                assert "lora" not in v.lower(), v


# ------------------------- `--canon-prompt` has one meaning (wave 6, F-b28837eb/F-c6580beb)


def _t2v_args(tmp_path, *extra):
    # PERFORMER is identity-only (surfaces=None); BLACKGUARD now has surfaces, so
    # --no-canon --subject BLACKGUARD is the checkbox refuse.
    return ["--out", str(tmp_path / "fresh"), "--subject", "PERFORMER", "--no-canon",
            "--tag", "probe", *extra]


def test_canon_prompt_cannot_change_the_text_this_builder_ships(tmp_path, capsys):
    """In the six sibling spend builders `--canon-prompt` is cross-checked against the
    shipped text by `canon_gate.gate_canon_ships_what_it_gated` and can do nothing but
    refuse. Here it was a PROMPT OVERRIDE — `prompt = a.canon_prompt or (...)` — while the
    shared `add_spend_flags` help string describes only the cross-check semantics ("text
    the router checks; default is the payload's positive"). Measured on today's tree: a
    `--canon-prompt` naming a sentence no canon governs printed `[canon] UNGATED:
    PERFORMER` and BUILD_T2V_OK, and node 30 of the emitted graph carried exactly that
    string. An operator who learned the flag on r2v or i2v, where passing it can only
    raise, silently changed the text a paid generation is made from."""
    from armature_core.errors import GateCanon

    out = tmp_path / "fresh"
    with pytest.raises(GateCanon) as exc:
        B.main(_t2v_args(tmp_path, "--canon-prompt",
                         "a completely different sentence that no canon governs"))
    assert exc.value.evidence["clause"] == "gated_text_is_not_shipped_text"
    assert not out.exists(), "a refused build created its output directory"
    assert "BUILD_T2V_OK" not in capsys.readouterr().out


@pytest.mark.parametrize("profile", ["reference", "derived"])
def test_the_profiles_own_prompt_passed_as_canon_prompt_still_builds(tmp_path, profile):
    """The mutation that must NOT fire it: the flag agreeing with the shipped text."""
    shipped = B.PROMPT_A3 if profile == "reference" else B.PROBE_PROMPT
    B.main(_t2v_args(tmp_path / profile, "--profile", profile,
                     "--canon-prompt", shipped))
    graph = json.load(open(os.path.join(str(tmp_path / profile / "fresh"),
                                        "E09-B2-probe-t2v.api.json"), encoding="utf-8"))
    assert graph["30"]["inputs"]["text"] == shipped


def test_a_refused_gate_below_canon_leaves_no_output_directory(tmp_path, capsys):
    """`os.makedirs` sat directly under `canon_spend` and ABOVE Gates ROUTE, S and L.
    Measured: `--seed 999999` raised "[ROUTE] Gate S: node 50 would run seed 999999, which
    the committed list does not pre-register" and left the output directory on disk, empty
    — to be read later as a run that happened. Every other builder in this tree was moved
    below its last in-tool gate in wave 3; build_payload.py states the invariant."""
    out = tmp_path / "fresh"
    with pytest.raises(RG.RouteGate) as exc:
        B.main(_t2v_args(tmp_path, "--seed", "999999"))
    assert "999999" in str(exc.value)
    assert not out.exists(), "a refused spend left an output directory behind"
    assert "BUILD_T2V_OK" not in capsys.readouterr().out


# ---------------------------------------------------------------------------------------
# wave 10, F-45bc4fbb — Gate L's raise had no failing input


def _skewed_latent(monkeypatch, **inputs):
    """Build the real A3 graph, then move node 40's latent out from under the constants."""
    real = B.build_graph

    def skew(*a, **k):
        graph, split = real(*a, **k)
        graph["40"]["inputs"].update(inputs)
        return graph, split

    monkeypatch.setattr(B, "build_graph", skew)


def test_the_standalone_gate_L_call_that_could_not_fail_is_gone():
    """`gate_l = RG.frame_legality(WIDTH, HEIGHT, LENGTH)` re-read the three module
    constants that also build the graph's only latent, two lines under a `RG.verify(graph)`
    that already reads that latent and raises on any illegal frame. Measured by rebinding
    the constants to 833/481/64: `verify` raised first and the standalone call evaluated
    `legal=False` on a line that is never reached. A check with no failing input is not a
    check, and the record's `gates.L` asserted its verdict anyway."""
    import ast
    import inspect

    src = inspect.getsource(B.main)
    calls = [n for n in ast.walk(ast.parse(src.lstrip()))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "frame_legality"]
    assert calls == [], "the unreachable standalone Gate L call is back"
    verify = [n for n in ast.walk(ast.parse(src.lstrip()))
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "verify"]
    assert len(verify) == 1
    assert any(kw.arg == "frame" for kw in verify[0].keywords), (
        "verify must be given the frame this tool believes it is generating, or the "
        "graph-vs-supplied contradiction clause has nothing to compare")


def test_a_graph_whose_latent_disagrees_with_the_module_constants_RAISES(
        tmp_path, monkeypatch):
    """The clause that binds now, and the input the old one could not have. 832x480x33 is
    perfectly LEGAL — a multiple of 16 and of the form 4n+1 — so no legality clause on
    either side fires. It simply is not the frame this tool says it generates, and one of
    the two numbers is the one the report would quote."""
    _skewed_latent(monkeypatch, length=33)
    with pytest.raises(RG.RouteGate, match="the graph's"):
        B.main(_t2v_args(tmp_path))
    assert not (tmp_path / "fresh").exists()


def test_an_illegal_latent_still_raises_through_the_same_call(tmp_path, monkeypatch):
    """The other direction: a latent that is illegal on the generator's own rules."""
    _skewed_latent(monkeypatch, length=64, width=833)
    with pytest.raises(RG.RouteGate, match="not of the form|multiple of 16"):
        B.main(_t2v_args(tmp_path))


def test_the_record_says_where_its_gate_L_verdict_came_from(tmp_path):
    """The record may not assert a Gate L verdict computed by a check with no failing
    input. It now names its source and carries the graph-read rows."""
    B.main(_t2v_args(tmp_path))
    rec = json.loads(next(iter(sorted((tmp_path / "fresh").glob("*payload-record.json"))))
                     .read_text(encoding="utf-8"))
    gate_l = rec["gates"]["L"]
    assert gate_l["legal"] is True
    assert "not re-derived from the module constants" in gate_l["source"]
    sources = sorted(f["source"] for f in gate_l["frame_legality"])
    assert sources == ["graph", "supplied"], sources
