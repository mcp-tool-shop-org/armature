"""Wave 12 (core-gates): the licence receipt states three numbers, and four andons stop
stating verdicts over populations that are not there.

Ten approved findings, and the thread through them is one sentence this repo has written
before in four other places: **"nothing was checkable" and "everything checked out" may
not be the same verdict.** Gate L's latent clause learned it in E08, `g2_completeness`
learned it for channels, `gate_d_determinism` learned it for bones, the seed clause
learned it for samplers. The licence clause had never learned it at all — it counted what
it LOOKED AT and never what it CLASSIFIED — and four more clauses on three pages still
stated verdicts over an empty population or over a number that is not a number.

Every test here goes red on the tree at base `89269f1`; the red measurements are quoted on
each one.
"""

import json
import math
import os
import subprocess
import sys
import textwrap

import numpy as np
import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from conftest import TOOLS  # noqa: E402
from armature_core import canon, gates, rig_gates, shotspec  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import (  # noqa: E402
    G5ConventionConformance, GateBBatching, GateCanon, GateDDeterminism, GateNNames,
    GatePRestPose, SpecError,
)

BASE = "wan2.1_vace_14B_fp16.safetensors"
LORA_T = "wan22-14b-t2v-technically_color.safetensors"


def _graph(*weights, cls="LoraLoaderModelOnly", key="lora_name"):
    """An API graph loading exactly these weight files, one loader each."""
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}}}
    for i, w in enumerate(weights, start=2):
        g[str(i)] = {"class_type": cls, "inputs": {key: w, "strength_model": 1.0}}
    return g


def _verify(g, **kw):
    kw.setdefault("frame", (1024, 576, 81))
    kw.setdefault("carries_no_sampler", True)
    return RG.verify(g, **kw)


# ---------------------------------------------------------------- F-af8e097f · the
# CONDITIONAL licence tier. `docs/license-map.md:77` rules technically_color "YES — credit
# required" (allowNoCredit: false); the mirror recorded ALLOWED and buried CREDIT REQUIRED
# in free text no clause reads.


def test_the_map_s_credit_required_row_is_conditional_not_allowed():
    """RED on base: `RULED_COMPONENTS['technically_color']['verdict']` was 'ALLOWED' and
    the row carried no `condition` key at all, so a conditional grant and an unconditional
    one were the same object to every reader."""
    row = RG.RULED_COMPONENTS["technically_color"]
    assert row["verdict"] == "CONDITIONAL"
    cond = row["condition"]
    assert cond["kind"] == "credit"
    assert cond["creditor"] == "renderartist"
    assert cond["source"] == "CivitAI 2106471"
    assert cond["fetched"] == "2026-08-13"


def test_conditional_ranks_strictly_between_allowed_and_excluded():
    """RED on base: `VERDICT_RANK` was
    `{'BANNED': 3, 'EXCLUDED': 2, 'ALLOWED': 1, 'NOT IN THIS TABLE': 0}` — no CONDITIONAL
    tier for `rulings_for`'s strictest-match sort to rank, so precedence between a
    conditional row and a plain allowed one was an accident of typing order."""
    r = RG.VERDICT_RANK
    assert r["ALLOWED"] < r["CONDITIONAL"] < r["EXCLUDED"] < r["BANNED"]
    assert r["NOT IN THIS TABLE"] < r["ALLOWED"]


def test_the_strictest_match_sort_surfaces_conditional_over_a_plain_allowed():
    """A filename matching a CONDITIONAL row and an ALLOWED row is governed by the
    conditional one — the same argument `rulings_for` already makes for BANNED."""
    hits = RG.rulings_for("technically_color_smartphonesnapshot_merged.safetensors")
    assert [h["matched_on"] for h in hits] == ["technically_color", "smartphonesnapshot"]
    assert hits[0]["verdict"] == "CONDITIONAL"


def test_the_kills_still_outrank_a_conditional_row():
    """The wave-10 precedence pin, re-measured under the new tier: a conditional grant is
    a grant with an obligation, not a refusal, so a BANNED row still governs a name that
    matches both."""
    hits = RG.rulings_for("technically_color_instagirl_v2.safetensors")
    assert [h["matched_on"] for h in hits] == ["instagirl", "technically_color"]


def test_verify_refuses_a_conditional_component_the_record_does_not_credit():
    """RED on base: this exact graph returned
    '2 weight file(s), ... 1 frame(s) checked and generator-legal' and
    `[k for k in ev if 'cred' in k.lower()]` was `[]` — E14 arm T footage could be
    published uncredited with Gate ROUTE green."""
    with pytest.raises(RG.RouteGate) as exc:
        _verify(_graph(LORA_T))
    ev = exc.value.evidence
    assert ev["clause"] == "uncredited_conditional_component"
    assert "renderartist" in str(exc.value)
    [row] = ev["uncredited_conditional"]
    assert row["matched_on"] == "technically_color"
    assert row["credited"] is False
    assert row["condition"]["creditor"] == "renderartist"


def test_the_credit_entry_pays_the_condition_and_the_receipt_says_so():
    """The forward direction, and the entry is built FROM the row rather than typed."""
    entry = RG.attribution_entry_for("technically_color")
    assert entry == {"component": "technically_color", "creditor": "renderartist",
                     "source": "CivitAI 2106471",
                     "text": "Technically Color LoRA by renderartist (CivitAI)",
                     "kind": "credit"}
    ev = _verify(_graph(LORA_T), attribution=[entry])
    assert ev["components_conditional"] == 1
    assert ev["components_conditional_credited"] == 1
    assert "1 conditional (credited)" in ev["verdict"]
    assert ev["attribution"] == [entry]


def test_the_served_filename_credits_the_row_too():
    """A record written beside a graph naturally names the served file; a record written
    from the table names the row key. Both readings credit; neither is guessed at."""
    ev = _verify(_graph(LORA_T), attribution=[
        {"component": LORA_T, "creditor": "RenderArtist", "text": "credit line"}])
    assert ev["components_conditional_credited"] == 1


@pytest.mark.parametrize("entry", [
    {"component": "technically_color", "creditor": "somebody else"},
    {"component": "smartphonesnapshot", "creditor": "renderartist"},
    {"component": "technically_color"},
    {"creditor": "renderartist"},
    "a bare string",
])
def test_an_entry_that_does_not_name_the_row_and_its_creditor_credits_nothing(entry):
    """`attribution` is not a skip flag: the creditor must be the row's, and the component
    must be nameable by the row key or the served filename."""
    with pytest.raises(RG.RouteGate) as exc:
        _verify(_graph(LORA_T), attribution=[entry])
    assert exc.value.evidence["clause"] == "uncredited_conditional_component"


def test_attribution_cannot_wave_a_banned_row():
    """The clause it must NOT become. A credit line pays a stated obligation; it does not
    touch a licence kill, and the kill stays the headline."""
    with pytest.raises(RG.RouteGate) as exc:
        _verify(_graph("wan22-14b-t2v-80s_fantasy_movie.safetensors"),
                attribution=[{"component": "80s_fantasy", "creditor": "renderartist"}])
    assert "BANNED" in str(exc.value)


def test_the_condition_flipped_back_to_allowed_drops_out_of_the_receipt(monkeypatch):
    """**The RED direction, by mutation.** Restore the pre-fix row — verdict ALLOWED, no
    condition — and the obligation vanishes from the record: the graph verifies with no
    attribution at all and the receipt counts zero conditional components. That is the
    state this finding measured on base, reproduced deliberately so the fix cannot
    silently revert."""
    rows = dict(RG.RULED_COMPONENTS)
    rows["technically_color"] = {k: v for k, v in rows["technically_color"].items()
                                 if k != "condition"}
    rows["technically_color"]["verdict"] = "ALLOWED"
    monkeypatch.setattr(RG, "RULED_COMPONENTS", rows)
    ev = _verify(_graph(LORA_T))
    assert ev["components_conditional"] == 0
    assert "0 conditional (credited)" in ev["verdict"]


def test_conditional_component_keys_reads_the_obligation_off_the_graph():
    """The builder-facing half: a submitting tool asks the GRAPH which obligations it has
    picked up rather than remembering which arm carries which LoRA. Arm S's shape returns
    `[]` and needs no entry; arm T's returns the row key `attribution_entry_for` takes."""
    assert RG.conditional_component_keys(_graph(LORA_T)) == ["technically_color"]
    assert RG.conditional_component_keys(
        _graph("WAN2.2-HighNoise_SmartphoneSnapshotPhotoReality_v3.safetensors")) == []
    entries = [RG.attribution_entry_for(k)
               for k in RG.conditional_component_keys(_graph(LORA_T))]
    assert _verify(_graph(LORA_T), attribution=entries)["components_conditional_credited"] == 1


def test_attribution_entry_for_refuses_an_unconditional_row():
    """A credit line for a component that owes none would satisfy nothing while reading
    like a credit."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.attribution_entry_for("smartphonesnapshot")
    assert exc.value.evidence["clause"] == "attribution_for_unconditional_row"
    assert exc.value.evidence["conditional_rows"] == ["technically_color"]


def test_the_conditional_census_is_derived_from_the_table_and_goes_red_on_a_new_row(
        monkeypatch):
    """**Keyed on BEHAVIOUR, not on the row key**: a conditional row is one carrying a
    `condition` object, whatever it is called. The two readings — the verdict string and
    the presence of the condition — must agree in BOTH directions, so a row that gains a
    condition without the verdict (or the verdict without the condition) fails loudly.

    Red proved by adding a member under a spelling the fix never saw: a row keyed
    `some_future_lora` whose verdict says CONDITIONAL and which carries no condition
    object at all — the shape a licence-map re-fetch produces when an obligation is
    transcribed as prose."""
    def _split(rows):
        by_verdict = {k for k, r in rows.items() if r["verdict"] == "CONDITIONAL"}
        by_object = {k for k, r in rows.items() if r.get("condition")}
        return by_verdict, by_object

    by_verdict, by_object = _split(RG.RULED_COMPONENTS)
    assert by_verdict == by_object == {"technically_color"}
    for key in by_object:
        cond = RG.RULED_COMPONENTS[key]["condition"]
        assert set(cond) >= {"kind", "creditor", "source", "fetched"}

    rows = dict(RG.RULED_COMPONENTS)
    rows["some_future_lora"] = {"verdict": "CONDITIONAL", "licence": "x", "reason": "y"}
    monkeypatch.setattr(RG, "RULED_COMPONENTS", rows)
    red_verdict, red_object = _split(RG.RULED_COMPONENTS)
    assert red_verdict != red_object, "the census cannot see a condition-less CONDITIONAL"


# ---------------------------------------------------------------- F-23adfa35 · the
# licence clause is the one clause in `verify` with no count of what it could classify.


def test_the_licence_clause_reports_classified_unclassified_and_conditional():
    """RED on base: this graph's verdict read '3 weight file(s), 1 seed(s) all pinned, ...'
    while every one of the three rows read NOT IN THIS TABLE with matched_on None, and
    `sorted(ev)` carried no `components_classified`, `unclassified` or equivalent key — so
    the receipt could not distinguish 'every component is ruled clean' from 'the table
    classified none of them'.

    The shape is Gate L's, one clause over on the same line
    ('{checkable} of {n} latent(s) checkable')."""
    g = _graph("wan_2.1_vae.safetensors", "some_unknown_style_v3.safetensors")
    ev = _verify(g)
    assert ev["components_classified"] == 0
    assert ev["components_unclassified"] == 3
    # CORRECTED IN PLACE, wave 28 (F-1e1780ba). `unclassified` is built from
    # `_component_label`, which used to return a bare `repr(file)` and now spells the node
    # the component sits on (`{where}/{node_id}`, Gate PAIR's and Gate S's existing
    # spelling) — because the BANNED refusal built from the same helper demanded a node be
    # DELETED without saying which one. The COUNT this test is about is unmoved; the label
    # gained the level and the id, and the filename is still asserted inside it.
    assert ev["unclassified"] == [f"{repr(BASE)} at api/1",
                                  f"{repr('wan_2.1_vae.safetensors')} at api/2",
                                  f"{repr('some_unknown_style_v3.safetensors')} at api/3"]
    assert "0 of 3 component(s) classified, 3 unclassified" in ev["verdict"]
    assert "weight file(s)," not in ev["verdict"]


def test_the_classified_count_moves_zero_to_one_when_a_row_is_added(monkeypatch):
    """**The RED direction**: mutate one of those filenames into a RULED_COMPONENTS row
    and the count moves 0 -> 1. A number that cannot move is not a measurement."""
    g = _graph("some_unknown_style_v3.safetensors")
    assert _verify(g)["components_classified"] == 0
    rows = dict(RG.RULED_COMPONENTS)
    rows["some_unknown_style"] = {"verdict": "ALLOWED", "licence": "Apache-2.0",
                                  "reason": "added by the red direction of this test"}
    monkeypatch.setattr(RG, "RULED_COMPONENTS", rows)
    ev = _verify(g)
    assert ev["components_classified"] == 1
    assert ev["components_unclassified"] == 1
    assert "1 of 2 component(s) classified, 1 unclassified" in ev["verdict"]


def test_an_unclassified_component_is_still_reported_and_still_not_refused():
    """What this fix does NOT change, pinned beside what it does: the wave-10 ruling that
    UNKNOWN is reported rather than raised stands
    (`tests/test_route_gates.py::test_a_base_weight_reads_not_in_this_table_and_that_is_
    recorded_not_silent` — RE-ANCHORED on the symbol 2026-09-05, wave 25: the line this
    used to cite, `:1893`, moved when this domain's citation edit shifted the file, and it
    was already a recorded stale anchor). The
    receipt now says the question was asked; it does not answer it."""
    ev = _verify(_graph("some_unknown_style_v3.safetensors"))
    assert [c["verdict"] for c in ev["components"]] == ["NOT IN THIS TABLE"] * 2


def test_the_hosted_tier_receipt_carries_the_same_licence_phrase():
    """The other verdict string in this function — a receipt that reports one thing on one
    route and another on the next is two receipts."""
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
         "2": {"class_type": "Wan2ReferenceVideoApi",
               "inputs": {"model.resolution": "720P", "model.ratio": "16:9",
                          "model.duration": 5, "seed": 7,
                          "control_after_generate": "fixed"}}}
    ev = RG.verify(g, hosted_tier="wan2.7-r2v")
    assert "0 of 1 component(s) classified, 1 unclassified" in ev["verdict"]
    assert "0 conditional (credited)" in ev["verdict"]


# ---------------------------------------------------------------- F-f9394d6e · the
# save-format branch of the node walk guarded nothing.


@pytest.mark.parametrize("nodes,index", [
    (["x"], 0),
    ([None], 0),
    ([{"type": "UNETLoader", "widgets_values": [BASE]}, "stray"], 1),
    ([{"type": "UNETLoader", "widgets_values": [BASE]}, 7], 1),
])
def test_a_non_dict_in_the_save_format_nodes_array_is_a_typed_refusal(nodes, index):
    """RED on base: `components({'nodes': ['x']})` raised
    `AttributeError: 'str' object has no attribute 'get'`, `{'nodes': [None]}` the same,
    and one stray entry beside a well-formed `UNETLoader` took the whole licence, seed and
    frame walk with it. `AttributeError` is not an `ArmatureError`, so the halt contract's
    exit-2 / GATE_FAILURE + GATE_EVIDENCE receipt branch (`stage_render.py:514`) was
    bypassed and the run was classified as an unhandled error rather than as Gate ROUTE
    refusing a shape it cannot read."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components({"nodes": nodes})
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["index"] == index
    assert ev["entry_type"] == type(nodes[index]).__name__


def test_the_unreadable_node_refusal_reaches_the_halt_contract():
    """The whole point of the typed refusal: a caller catching the family catches this."""
    from armature_core.errors import ArmatureError
    with pytest.raises(ArmatureError, match=r"which is not a node"):
        RG.seeds({"nodes": [None]})
    with pytest.raises(ArmatureError, match=r"which is not a node"):
        RG.latents({"nodes": [None]})


def test_the_two_branches_that_already_guarded_still_skip_rather_than_raise():
    """The API branch and `_iter_definitions` skip a non-dict by design and are untouched:
    the change is on the ONE source that guarded nothing."""
    g = {"1": "not a node",
         "2": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}}}
    assert [c["file"] for c in RG.components(g)] == [BASE]


# ---------------------------------------------------------------- F-5bc15060 · Gate D
# scaled a tolerance by a `bbox_diagonal` nothing had refused, on the one route where the
# clauses that DO refuse never run.


def _pair_of_fingerprints():
    a = rig_gates.rig_fingerprint(
        {"b": {"head": (0.0, 0.0, 0.0), "tail": (0.0, 1.0, 0.0), "parent": None}}, {}, 0)
    b = rig_gates.rig_fingerprint(
        {"b": {"head": (0.0, 0.0, 0.0), "tail": (0.0, 5.0, 0.0), "parent": None}}, {}, 0)
    return a, b


VERTS_A = np.zeros((4, 3), dtype=np.float64)
VERTS_B = np.zeros((4, 3), dtype=np.float64) + 0.5

NON_FINITE = [float("nan"), float("inf"), float("-inf")]
DEGENERATE = [0.0, -1.0]


@pytest.mark.parametrize("diagonal", NON_FINITE + DEGENERATE)
def test_gate_d_refuses_a_diagonal_it_cannot_scale_a_tolerance_by(diagonal):
    """RED on base for nan/inf: measured 2026-09-04 on two fingerprints whose one bone's
    tail differs by 4.0 with both weight dicts empty, `bbox_diagonal=inf` returned verdict
    'two builds agree on bones and hierarchy over 1 bone(s); weights NOT COMPARED' with
    `length_tolerance` inf, and `nan` returned the same with a nan tolerance. Gate D was
    the only clause on its page deriving a tolerance from this quantity without first
    refusing a degenerate one — and `--mode=skeleton` is the route where neither Gate P
    clause runs, so nothing had looked at the number before it."""
    a, b = _pair_of_fingerprints()
    with pytest.raises(GateDDeterminism) as exc:
        rig_gates.gate_d_determinism(a, b, diagonal)
    ev = exc.value.evidence
    assert math.isnan(ev["bbox_diagonal"]) or ev["bbox_diagonal"] == diagonal
    assert "diagonal" in str(exc.value)


@pytest.mark.parametrize("diagonal", NON_FINITE)
def test_the_three_gate_p_clauses_refuse_an_infinite_diagonal_too(diagonal):
    """RED on base for inf (nan was already caught by `> 0`, inf was NOT): `inf > 0` is
    True, so an infinite diagonal walked straight through all three `not (bbox_diagonal >
    0)` guards into `epsilon_frac * inf`. On `gate_p_evaluation_is_live` that inverts the
    andon outright — an infinite floor makes `d.max() <= threshold` True for every real
    displacement, so the liveness gate fires on a mesh that DID move."""
    finite = r"bbox_diagonal=.* is not a finite number"
    with pytest.raises(GatePRestPose, match=finite):
        rig_gates.gate_p_rest_pose(VERTS_A, VERTS_A, diagonal)
    with pytest.raises(GatePRestPose, match=finite):
        rig_gates.gate_p_round_trip_positions(VERTS_A, VERTS_A, diagonal)
    with pytest.raises(GatePRestPose, match=finite):
        rig_gates.gate_p_evaluation_is_live(VERTS_A, VERTS_B, diagonal)


@pytest.mark.parametrize("diagonal", DEGENERATE)
def test_the_three_gate_p_clauses_keep_refusing_a_degenerate_diagonal(diagonal):
    """The direction that already bound, re-measured after routing through the helper —
    and each clause KEEPS ITS OWN WORDS for a degenerate diagonal. `require_finite` runs
    with `positive=False`, so a real 0 or -1 falls through to the sign clause that was
    already there; only a nan or an inf is answered by the shared helper. The three
    messages are distinguished here so a substituted clause cannot pass as its neighbour."""
    with pytest.raises(GatePRestPose, match=r"the threshold is a fraction of the mesh"):
        rig_gates.gate_p_rest_pose(VERTS_A, VERTS_A, diagonal)
    with pytest.raises(GatePRestPose, match=r"no threshold can be derived"):
        rig_gates.gate_p_round_trip_positions(VERTS_A, VERTS_A, diagonal)
    with pytest.raises(GatePRestPose, match=r"the liveness floor is a fraction"):
        rig_gates.gate_p_evaluation_is_live(VERTS_A, VERTS_B, diagonal)


def test_all_four_clauses_share_the_one_non_finite_helper():
    """One NaN family, one helper, four domains (wave 12's rule 5). The population is
    derived from the module's own source, not typed: every clause on this page that reads
    `bbox_diagonal` must reach `parts.require_finite`, and none may carry a second
    `math.isfinite`."""
    src = open(rig_gates.__file__, encoding="utf-8").read()
    assert src.count("require_finite(\"bbox_diagonal\"") == 4
    assert "math.isfinite" not in src.replace("second `math.isfinite`", "")
    from armature_core import parts
    assert rig_gates.require_finite is parts.require_finite


def test_gate_d_still_passes_on_a_finite_diagonal():
    """The SUCCESS direction: the helper refuses what is not a number and nothing else."""
    a, _ = _pair_of_fingerprints()
    ev = rig_gates.gate_d_determinism(a, a, 2.0)
    assert ev["length_tolerance"] == pytest.approx(
        rig_gates.DETERMINISM_LENGTH_FRAC * 2.0)
    assert "agree" in ev["verdict"]


# ---------------------------------------------------------------- F-d6e1d40f · Gate N
# stated a coverage verdict over an empty registry.


def test_gate_n_refuses_an_empty_registry():
    """RED on base: `gate_n_names([], [], 'the re-imported export')` returned
    `{'verdict': '0 / 0 registered sites map to one bone each', 'mapped': 0,
    'n_registered': 0, ...}` — a PASS having compared nothing, phrased as a coverage
    claim. Its two neighbours were given this refusal in wave 10 on this reasoning."""
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names([], [], "the re-imported export")
    ev = exc.value.evidence
    assert ev["n_registered"] == 0
    assert ev["where"] == "the re-imported export"
    assert "ZERO registered sites" in str(exc.value)


def test_gate_n_refuses_an_empty_registry_even_with_bones_present():
    """The other half of the same shape: bones observed against a registry of none is not
    'nothing to check', it is 'the committed list was emptied'."""
    with pytest.raises(GateNNames) as exc:
        rig_gates.gate_n_names(["bone_0", "bone_1"], [], "the built rig")
    assert exc.value.evidence["n_observed"] == 2


def test_gate_n_still_passes_on_a_registry_it_can_read():
    ev = rig_gates.gate_n_names(["a", "b"], ["a", "b"], "the built rig")
    assert ev["mapped"] == 2


# ---------------------------------------------------------------- F-70eda049 · the spec
# contract's positivity clause was `value <= 0`, which is False for NaN.


CAMERA_POSITIVE = ("radius", "lens_mm", "sensor_mm", "fit_margin", "clip_start",
                   "clip_end")
CAMERA_ANGLES = ("elevation_deg", "azimuth_start_deg", "azimuth_sweep_deg")


def _spec(**camera):
    cam = {"type": "orbit", "radius": 3.0}
    cam.update(camera)
    return {"spec_version": 1, "name": "w12", "generator": "wan",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 832, "height": 480},
            "frames": {"count": 33, "fps": 24},
            "channels": ["depth"], "camera": cam}


@pytest.mark.parametrize("key", CAMERA_POSITIVE + CAMERA_ANGLES)
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_camera_number_is_refused_by_name(key, bad):
    """RED on base: `normalise_spec` ACCEPTED and returned unchanged `camera.lens_mm = nan`,
    `lens_mm = inf`, `sensor_mm = nan`, `fit_margin = nan` and `radius = nan` — only
    `clip_start = nan` was caught, and by the separate `clip_start < clip_end` ordering
    clause, not by the positivity one. `nan <= 0` is False, so every non-finite number
    walked the clause whose whole job is to say a spec is well formed."""
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(_spec(**{key: bad}))
    assert f"camera.{key}" in str(exc.value)
    assert "finite" in str(exc.value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_the_int_typed_fields_were_already_closed_by_their_type_clause(bad):
    """**The bound on this fix, stated rather than assumed.** `frames.count`, `frames.fps`,
    `resolution.width` and `resolution.height` are `_require(..., int, ...)`, and a NaN is
    a float — so the type clause already refused them and the positivity clause never saw
    one. The hole was the CAMERA block, whose numbers are `(int, float)`. Pinned here so a
    later loosening of those type clauses cannot reopen it in silence."""
    for block, key in (("frames", "count"), ("frames", "fps"),
                       ("resolution", "width"), ("resolution", "height")):
        raw = _spec()
        raw[block][key] = bad
        with pytest.raises(SpecError) as exc:
            shotspec.normalise_spec(raw)
        assert "expected int" in str(exc.value)


def test_a_plain_zero_keeps_the_message_it_always_had():
    """The sign half is unchanged: the finiteness clause runs first and passes a real 0
    through to the words this function has always given it."""
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(_spec(lens_mm=0))
    assert "it must be positive" in str(exc.value)


def test_dump_spec_refuses_rather_than_writing_a_bare_nan(tmp_path):
    """RED on base: `dump_spec(spec, p)` wrote the literal line `"lens_mm": NaN,` —
    `json.dump` defaults to `allow_nan=True` — and `normalise_spec(json.load(open(p)))`
    read it back as nan, because `json.load` accepts the `NaN` / `Infinity` tokens too. A
    non-finite value survived a full write/read round trip of the file this module's
    opening line calls a contract, and the file is not RFC-8259 JSON: any non-Python
    reader of `specs/**` (a CI step, jq, the site) fails on it."""
    spec = shotspec.normalise_spec(_spec())
    spec["camera"]["lens_mm"] = float("nan")
    p = tmp_path / "shot.json"
    with pytest.raises(ValueError):
        shotspec.dump_spec(spec, p)
    if p.exists():
        assert "NaN" not in p.read_text(encoding="utf-8")


def test_a_clean_spec_still_round_trips(tmp_path):
    """The SUCCESS direction, so the refusal is shown to bound only what it names."""
    spec = shotspec.normalise_spec(_spec())
    p = tmp_path / "shot.json"
    shotspec.dump_spec(spec, p)
    back = shotspec.normalise_spec(json.loads(p.read_text(encoding="utf-8")))
    assert back["camera"]["lens_mm"] == spec["camera"]["lens_mm"]


# ---------------------------------------------------------------- F-26fd464d · `load`
# validated the two fields that OBLIGE and neither field that REFUSES.


def _doc(**over):
    doc = {"schema": 1,
           "surfaces": [{"id": "torso",
                         "occupant": {"kind": "prompt", "phrase": "black plate",
                                      "ratified": True}}],
           "legal_clauses": [{"id": "c1", "phrase": "cinematic", "class": "style"}]}
    doc.update(over)
    return doc


def _write(tmp_path, doc):
    p = tmp_path / "surfaces.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_a_blocked_addition_keyed_text_refuses_the_load(tmp_path):
    """RED on base: a doc whose `blocked_additions` is
    `[{'id': 'b1', 'text': 'glowing red halo'}]` — the phrase under the wrong key — loaded
    clean and `blocked_additions(doc)` returned `[]`, so the field this module's header
    calls 'a REFUSAL list, not a licence' declared a refusal that does not exist."""
    path = _write(tmp_path, _doc(blocked_additions=[{"id": "b1",
                                                     "text": "glowing red halo"}]))
    with pytest.raises(GateCanon) as exc:
        canon.load(path)
    ev = exc.value.evidence
    assert ev["clause"] == "blocked_addition_phrase"
    assert ev["index"] == 0
    assert ev["id"] == "b1"
    assert ev["keys"] == ["id", "text"]


@pytest.mark.parametrize("adds,clause", [
    ("glowing red halo", "blocked_additions_not_a_list"),
    ([42], "blocked_addition_shape"),
    ([None], "blocked_addition_shape"),
    (["   "], "blocked_addition_empty"),
    ([{"id": "b1", "phrase": ""}], "blocked_addition_phrase"),
])
def test_every_malformed_blocked_addition_shape_refuses(tmp_path, adds, clause):
    path = _write(tmp_path, _doc(blocked_additions=adds))
    with pytest.raises(GateCanon) as exc:
        canon.load(path)
    assert exc.value.evidence["clause"] == clause


def test_forbidden_written_as_a_bare_string_refuses_the_load(tmp_path):
    """RED on base: `occupant.forbidden` was read as `for word in occ.get('forbidden') or
    []` with no type check, so a string written where a list belongs iterates as single
    CHARACTERS — every letter becomes a forbidden word."""
    doc = _doc()
    doc["surfaces"][0]["occupant"]["forbidden"] = "gauntlet"
    path = _write(tmp_path, doc)
    with pytest.raises(GateCanon) as exc:
        canon.load(path)
    ev = exc.value.evidence
    assert ev["clause"] == "forbidden_not_a_list"
    assert ev["id"] == "torso"
    assert "CHARACTERS" in str(exc.value)


@pytest.mark.parametrize("word", [None, 7, ""])
def test_a_forbidden_entry_that_is_not_a_word_refuses(tmp_path, word):
    doc = _doc()
    doc["surfaces"][0]["occupant"]["forbidden"] = ["gauntlet", word]
    path = _write(tmp_path, doc)
    with pytest.raises(GateCanon) as exc:
        canon.load(path)
    assert exc.value.evidence["clause"] == "forbidden_word"
    assert exc.value.evidence["index"] == 1


def test_a_well_formed_refusal_file_still_loads(tmp_path):
    """The SUCCESS direction: both spellings `blocked_additions()` reads are accepted."""
    doc = _doc(blocked_additions=["glowing red halo", {"id": "b2", "phrase": "neon"}])
    doc["surfaces"][0]["occupant"]["forbidden"] = ["gauntlet"]
    loaded = canon.load(_write(tmp_path, doc))
    assert [b["phrase"] for b in canon.blocked_additions(loaded)] == [
        "glowing red halo", "neon"]


# ---------------------------------------------------------------- F-ce697ad9 · two
# populations of surfaces existed and the forward direction read the wrong one.


def _mesh_doc():
    return {"schema": 1,
            "surfaces": [
                {"id": "torso", "occupant": {"kind": "prompt", "phrase": "black plate",
                                             "ratified": True}},
                {"id": "skin", "occupant": {"kind": "mesh", "phrase": "weathered bronze",
                                            "ratified": True}}],
            "legal_clauses": [{"id": "c1", "phrase": "cinematic", "class": "style"}]}


def test_cover_and_coverage_agree_about_which_surfaces_the_prompt_must_name():
    """RED on base: `coverage` reported `prompt_surfaces: 1, ratified: 1` and
    `cover(doc, 'black plate')` raised '[CANON] forward cover failed: ratified phrases
    absent: weathered bronze' — a refusal of a prompt that covers 1 of 1 prompt surfaces,
    quoting a phrase the same module says is not a prompt phrase ('Occupants of kind mesh
    are spatial-only and stay out — they are numbers, not prompt phrases')."""
    doc = _mesh_doc()
    nums = canon.coverage(doc)
    assert nums["prompt_surfaces"] == 1 and nums["ratified"] == 1
    ev = canon.cover(doc, "black plate")
    assert ev["missing"] == []
    assert ev["prompt_surfaces"] == 1


def test_a_mesh_phrase_no_longer_licenses_residue_either():
    """The same population on both sides of the router. A mesh phrase neither obliges the
    prompt nor licenses text in it — reading two populations is what made a prompt
    covering 1 of 1 prompt surfaces refuse."""
    doc = _mesh_doc()
    assert "weathered bronze" not in canon.licensed_phrases(doc)
    with pytest.raises(GateCanon) as exc:
        canon.cover(doc, "black plate weathered bronze")
    assert exc.value.evidence["residue"]


def test_a_refusal_still_reads_every_surface_mesh_included():
    """The half that must NOT move: a refusal is a claim about the PROMPT, not about the
    occupant, so `forbidden` and `blocked_additions` keep reading every surface."""
    doc = _mesh_doc()
    doc["surfaces"][1]["occupant"]["forbidden"] = ["gauntlet"]
    with pytest.raises(GateCanon) as exc:
        canon.cover(doc, "black plate wearing a gauntlet")
    assert [f["surface"] for f in exc.value.evidence["forbidden"]] == ["skin"]


def test_a_ratified_prompt_phrase_is_still_obliged():
    """The andon this file exists for stays armed on the population it belongs to."""
    with pytest.raises(GateCanon) as exc:
        canon.cover(_mesh_doc(), "cinematic")
    assert [m["surface"] for m in exc.value.evidence["missing"]] == ["torso"]


# ---------------------------------------------------------------- F-a38c20b0 · Gate B
# stated 'batch intact' over zero images.


def test_gate_b_refuses_an_expectation_of_zero():
    """RED on base: `gate_b_batching(0, 0)` returned
    `{'gate': 'B', 'andon': 'GateBBatching', 'expected_frames': 0,
      'observed_batch_images': 0, 'verdict': 'batch intact'}`. The single call site is
    `gate_b_frames.py:119` over two `frame_paths()` listings, so two empty or mistyped
    directories give 0 == 0 — and the operator then read Gate B reporting the batch intact
    immediately above Gate R saying there were no frames at all."""
    with pytest.raises(GateBBatching) as exc:
        gates.gate_b_batching(0, 0)
    ev = exc.value.evidence
    assert ev["expected_frames"] == 0
    assert "empty population" in str(exc.value)


@pytest.mark.parametrize("expected", [-1, True, 2.0, None])
def test_gate_b_refuses_an_expectation_that_is_not_a_count(expected):
    with pytest.raises(GateBBatching, match=r"which is not a batching verdict"):
        gates.gate_b_batching(expected, 0)


def test_the_bool_clause_still_answers_first_for_a_zero_zero_false():
    """The ordering is deliberate: the observed value is the stronger defect and keeps its
    own message, so `gate_b_batching(0, False)` still refuses as 'not a count'."""
    with pytest.raises(GateBBatching) as exc:
        gates.gate_b_batching(0, False)
    assert "not a count" in str(exc.value)


def test_gate_b_still_passes_on_a_real_batch():
    assert gates.gate_b_batching(33, 33)["verdict"] == "batch intact"


# ---------------------------------------------------------------- F-147783a4 · G5 is
# dormant, vacuous over an empty population, and asserted PASS by a file that never calls
# it. The manifest half is `stage_render`'s and is routed to instruments-measure.


def test_g5_refuses_an_empty_reference():
    """RED on base: `g5_openpose_conformance(0, [], 0, [])` returned True having compared
    zero keypoints and zero limb pairs — the counts agreed because both were zero, the
    pair loop ran zero times, and `flat` was empty so the 1-indexing clause was skipped
    too. `g2_completeness` and `gate_r_round_trip` on the same page already carry this
    refusal."""
    with pytest.raises(G5ConventionConformance) as exc:
        gates.g5_openpose_conformance(0, [], 0, [])
    ev = exc.value.evidence
    assert ev["clause"] == "empty_reference"
    assert ev["n_reference_limb_pairs"] == 0


@pytest.mark.parametrize("ref_count,ref_seq", [(0, [[1, 2]]), (18, [])])
def test_g5_refuses_either_half_of_an_empty_reference(ref_count, ref_seq):
    with pytest.raises(G5ConventionConformance,
                       match=r"which is not a conformance verdict"):
        gates.g5_openpose_conformance(18, [[1, 2]], ref_count, ref_seq)


def test_g5_is_dormant_even_though_the_drawing_convention_is_retrieved():
    """**Dormancy re-measured after F-b08c0918 filled the palette.** G5 still has no
    production *call* that invokes `g5_openpose_conformance`: grepped across `tools/`,
    the name appears at its definition and in comments (`stage_render` records
    `gate_called: None`), nowhere as a Call. Wave 34 retrieved `PALETTE` and
    `KEYPOINT_NAMES` from ControlNet, so `require_drawing_convention()` now returns
    True — the old "constants are None" premise is overturned in place. The remaining
    commission is to wire this gate into the pose route and record ITS return rather
    than a NOT-RUN placeholder."""
    import ast
    import pathlib

    from armature_core import openpose

    assert openpose.PALETTE is not None and len(openpose.PALETTE) == openpose.KEYPOINT_COUNT
    assert openpose.KEYPOINT_NAMES is not None
    assert len(openpose.KEYPOINT_NAMES) == openpose.KEYPOINT_COUNT
    assert openpose.require_drawing_convention() is True

    tools = pathlib.Path(__file__).resolve().parents[1] / "tools"
    calls = []
    for path in tools.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name == "g5_openpose_conformance":
                calls.append(str(path.relative_to(tools.parent)))
    assert calls == [], (
        f"g5_openpose_conformance is now called from {calls}; update the G5 "
        f"manifest path and retire this dormancy pin in the same commit")


def test_g5_still_passes_against_the_retrieved_convention():
    """The SUCCESS direction, unmoved: the empty-population refusal bounds only the
    population, not the comparison."""
    from armature_core import openpose
    assert gates.g5_openpose_conformance(
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ,
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ)


# ---------------------------------------------------------------- the `-O` receipt for
# every refusal this wave adds. facet had 87 andons an environment variable could delete;
# this repo's standing answer is that a new refusal ships with the proof that `-O` does not
# take it away. A gate that raises only while `__debug__` is True is an `assert` wearing a
# raise's clothes.


_O_PROBE = textwrap.dedent("""
    import json, os, sys, tempfile
    sys.path.insert(0, sys.argv[1])
    import numpy as np
    from armature_core import canon, gates, rig_gates, shotspec
    from armature_core import route_gates as RG

    out = {"asserts_active": __debug__, "raised": {}}

    def probe(name, fn):
        try:
            fn()
        except Exception as err:
            out["raised"][name] = type(err).__name__
        else:
            out["raised"][name] = "NOT REFUSED"

    LORA = "wan22-14b-t2v-technically_color.safetensors"
    G = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.1_vace_14B_fp16.safetensors"}},
         "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": LORA}}}
    probe("uncredited_conditional_component",
          lambda: RG.verify(G, frame=(1024, 576, 81), carries_no_sampler=True))
    probe("unreadable_node", lambda: RG.components({"nodes": [None]}))
    probe("attribution_for_unconditional_row",
          lambda: RG.attribution_entry_for("smartphonesnapshot"))
    probe("gate_b_zero_expectation", lambda: gates.gate_b_batching(0, 0))
    probe("g5_empty_reference", lambda: gates.g5_openpose_conformance(0, [], 0, []))
    probe("gate_n_empty_registry", lambda: rig_gates.gate_n_names([], [], "the export"))

    fp = rig_gates.rig_fingerprint(
        {"b": {"head": (0, 0, 0), "tail": (0, 1, 0), "parent": None}}, {}, 0)
    v = np.zeros((4, 3))
    for label, d in (("nan", float("nan")), ("inf", float("inf")), ("zero", 0.0)):
        probe("gate_d_" + label, lambda d=d: rig_gates.gate_d_determinism(fp, fp, d))
        probe("gate_p_rest_" + label, lambda d=d: rig_gates.gate_p_rest_pose(v, v, d))
        probe("gate_p_round_" + label,
              lambda d=d: rig_gates.gate_p_round_trip_positions(v, v, d))
        probe("gate_p_live_" + label,
              lambda d=d: rig_gates.gate_p_evaluation_is_live(v, v + 0.5, d))

    SPEC = {"spec_version": 1, "name": "w12", "generator": "wan",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 832, "height": 480},
            "frames": {"count": 33, "fps": 24}, "channels": ["depth"],
            "camera": {"type": "orbit", "radius": 3.0}}
    for key in ("radius", "lens_mm", "sensor_mm", "fit_margin", "clip_start", "clip_end",
                "elevation_deg", "azimuth_start_deg", "azimuth_sweep_deg"):
        for label, bad in (("nan", float("nan")), ("inf", float("inf"))):
            raw = json.loads(json.dumps(SPEC))
            raw["camera"][key] = bad
            probe("spec_%s_%s" % (key, label),
                  lambda raw=raw: shotspec.normalise_spec(raw))
    spec = shotspec.normalise_spec(json.loads(json.dumps(SPEC)))
    spec["camera"]["lens_mm"] = float("nan")
    probe("dump_spec_nan",
          lambda: shotspec.dump_spec(spec, os.path.join(tempfile.mkdtemp(), "s.json")))

    DOC = {"schema": 1,
           "surfaces": [{"id": "torso",
                         "occupant": {"kind": "prompt", "phrase": "black plate",
                                      "ratified": True}}],
           "legal_clauses": [{"id": "c1", "phrase": "cinematic", "class": "style"}]}

    def write(doc):
        p = os.path.join(tempfile.mkdtemp(), "surfaces.json")
        open(p, "w", encoding="utf-8").write(json.dumps(doc))
        return p

    d1 = json.loads(json.dumps(DOC))
    d1["blocked_additions"] = [{"id": "b1", "text": "halo"}]
    probe("canon_blocked_addition", lambda: canon.load(write(d1)))
    d2 = json.loads(json.dumps(DOC))
    d2["surfaces"][0]["occupant"]["forbidden"] = "gauntlet"
    probe("canon_forbidden_string", lambda: canon.load(write(d2)))

    # The SUCCESS direction rides the same probe: a refusal sweep in which everything
    # refuses proves nothing about whether the gates can also pass.
    out["clean"] = "PASS" if RG.verify(
        G, frame=(1024, 576, 81), carries_no_sampler=True,
        attribution=[RG.attribution_entry_for("technically_color")])["verdict"] else "?"
    print(json.dumps(out))
""")


def _run_o_probe(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / "o_probe.py"
    script.write_text(_O_PROBE, encoding="utf-8")
    argv = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    env = dict(os.environ, PYTHONPATH=TOOLS)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    else:
        env.pop("PYTHONOPTIMIZE", None)
    res = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=str(tmp_path))
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("flag,env_var,label", [
    (False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1"),
])
def test_every_refusal_this_wave_adds_survives_optimization(tmp_path, flag, env_var, label):
    """Thirty-nine refusals across five modules, driven with no pytest in the loop.

    `assert` is deleted by `-O` and by `PYTHONOPTIMIZE=1`; every refusal here is a `raise`,
    and this is the receipt rather than the claim. The SUCCESS direction rides along, so a
    sweep in which everything refuses cannot read as a pass."""
    res = _run_o_probe(tmp_path, flag=flag, env_var=env_var)
    not_refused = sorted(k for k, v in res["raised"].items() if v == "NOT REFUSED")
    assert not_refused == [], f"{label}: {not_refused}"
    assert len(res["raised"]) == 39
    assert res["clean"] == "PASS", label


def test_the_optimization_actually_took_effect_for_this_wave(tmp_path):
    """A green sweep under an `-O` that never applied is a check that cannot fail."""
    assert _run_o_probe(tmp_path, flag=False)["asserts_active"] is True
    assert _run_o_probe(tmp_path, flag=True)["asserts_active"] is False
    assert _run_o_probe(tmp_path, env_var=True)["asserts_active"] is False
