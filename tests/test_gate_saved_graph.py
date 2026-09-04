"""The saved-file admission, against a save/convert round trip that changed something.

The cloud does not run the API graph this repo builds; it runs the saved file. Everything
here is about the gap between those two objects.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import gate_saved_graph as GSG
from armature_core import route_gates as RG


API = {
    # The origin nodes are carried here (and in `saved` below) because a save-format file
    # declares every node a link comes FROM, and wave 6 taught `link_round_trip` to resolve
    # the saved link table and compare origins. A fixture whose links pointed at nodes
    # neither document declared could not exercise that clause.
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a positive prompt"}},
    "105": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
    "200": {"class_type": "LoadImage", "inputs": {"image": "pose_pack.webp"}},
    "8": {"class_type": "VAEDecode", "inputs": {}},
    "49": {"class_type": "WanAnimateToVideo",
           "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                      "continue_motion_max_frames": 5, "video_frame_offset": 0,
                      "positive": ["6", 0], "vae": ["105", 0], "pose_video": ["200", 0]}},
    "68": {"class_type": "CreateVideo",
           "inputs": {"fps": 20, "bit_depth": 8, "images": ["8", 0]}},
}

#: `[id, origin_node, origin_slot, target_node, target_slot, type]` — the converter's own
#: shape, read off a save-format file.
LINKS = [[10, 6, 0, 49, 0, "CONDITIONING"],
         [12, 105, 0, 49, 1, "VAE"],
         [14, 200, 0, 49, 2, "IMAGE"],
         [17, 8, 0, 68, 0, "IMAGE"],
         [99, 200, 0, 49, 3, "IMAGE"]]


def saved(length=81, fps=20, extra_link=None, drop_link=False, links=LINKS):
    animate_inputs = [
        {"name": "positive", "type": "CONDITIONING", "link": None if drop_link else 10},
        {"name": "vae", "type": "VAE", "link": 12},
        {"name": "pose_video", "type": "IMAGE", "link": 14},
        {"name": "background_video", "type": "IMAGE", "link": extra_link},
    ]
    return {"nodes": [
        {"id": 6, "type": "CLIPTextEncode", "inputs": [],
         "widgets_values": ["a positive prompt"]},
        {"id": 105, "type": "VAELoader", "inputs": [],
         "widgets_values": ["wan_2.1_vae.safetensors"]},
        {"id": 200, "type": "LoadImage", "inputs": [], "widgets_values": ["pose_pack.webp"]},
        {"id": 8, "type": "VAEDecode", "inputs": [], "widgets_values": []},
        {"id": 49, "type": "WanAnimateToVideo", "inputs": animate_inputs,
         "widgets_values": [832, 480, length, 1, 5, 0]},
        {"id": 68, "type": "CreateVideo",
         "inputs": [{"name": "images", "type": "IMAGE", "link": 17},
                    {"name": "audio", "type": "AUDIO", "link": None}],
         "widgets_values": [fps, 8]},
    ], "links": [list(row) for row in links]}


# ---------------------------------------------------------- the camera tier (E11 wave 2)

CAMERA_API = {
    "45": {"class_type": "WanCameraEmbedding",
           "inputs": {"camera_pose": "Static", "width": 832, "height": 480, "length": 65,
                      "speed": 1.0, "fx": 0.5, "fy": 0.5, "cx": 0.5, "cy": 0.5}},
    "50": {"class_type": "WanCameraImageToVideo",
           "inputs": {"width": 832, "height": 480, "length": 65, "batch_size": 1,
                      "positive": ["30", 0], "negative": ["31", 0], "vae": ["21", 0],
                      "start_image": ["40", 0], "camera_conditions": ["45", 0]}},
}


def camera_saved(pose="Static", cam_length=65, gen_length=65):
    """The shape the cloud's converter actually emitted, 2026-08-12."""
    return {"nodes": [
        {"id": 45, "type": "WanCameraEmbedding", "inputs": [],
         "widgets_values": [pose, 832, 480, cam_length, 1, 0.5, 0.5, 0.5, 0.5]},
        {"id": 50, "type": "WanCameraImageToVideo",
         "inputs": [{"name": "positive", "type": "CONDITIONING", "link": 6},
                    {"name": "clip_vision_output", "type": "CLIP_VISION_OUTPUT",
                     "link": None},
                    {"name": "start_image", "type": "IMAGE", "link": 9},
                    {"name": "camera_conditions", "type": "WAN_CAMERA_EMBEDDING",
                     "link": 10}],
         "widgets_values": [832, 480, gen_length, 1]},
    ]}


def test_the_camera_tier_round_trips():
    """The rows these two classes needed were written after this check HALTED wave 2 on its
    own hole — the second sighting of that species, both times before a credit was spent."""
    ev = GSG.round_trip(CAMERA_API, camera_saved())
    assert ev["all_equal"] is True
    assert ev["n_values_compared"] == 13


def test_a_camera_pose_changed_by_the_round_trip_is_caught():
    """`camera_pose` sits at widget 0 and is the whole lever; a converter that dropped or
    re-defaulted it would leave a graph that still generates video."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(CAMERA_API, camera_saved(pose="Zoom In"))
    assert "camera_pose" in str(exc.value)


def test_a_camera_length_changed_by_the_round_trip_is_caught():
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(CAMERA_API, camera_saved(cam_length=81))
    assert "45.length" in str(exc.value)


def test_the_generated_length_changed_by_the_round_trip_is_caught():
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(CAMERA_API, camera_saved(gen_length=81))
    assert "50.length" in str(exc.value)


def test_an_unrecorded_class_still_halts_rather_than_being_skipped():
    """The fail-closed lookup that produced both rows above. `is None` halts; `{}` passes."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip({"99": {"class_type": "WanSomethingNobodyHasMet", "inputs": {"a": 1}}},
                       {"nodes": [{"id": 99, "type": "WanSomethingNobodyHasMet",
                                   "widgets_values": [1]}]})
    assert "add one rather than skipping the node" in str(exc.value)


# ------------------------------------------------------------------- the value half

def test_a_faithful_round_trip_compares_every_pinned_value():
    ev = GSG.round_trip(API, saved())
    assert ev["all_equal"] is True
    # 6 Animate widgets + fps + bit_depth + the three literals on the origin nodes the
    # fixture now declares (text, vae_name, image), which a save-format file always carries.
    assert ev["n_values_compared"] == 11


def test_a_frame_count_that_changed_in_the_save_is_caught():
    """Both numbers legal; only this comparison notices which one will run."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(API, saved(length=65))
    assert "built 81, saved 65" in str(exc.value)


def test_a_presentation_rate_that_changed_in_the_save_is_caught():
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(API, saved(fps=16))
    assert "68.fps" in str(exc.value)


def test_a_class_with_no_recorded_widget_index_halts_rather_than_being_skipped():
    """The table is looked up with `is None`, so a class nobody recorded is a halt and a
    class with genuinely no literal widgets is an explicit empty entry."""
    api = dict(API, **{"9": {"class_type": "SomeNodeNobodyIndexed",
                             "inputs": {"threshold": 0.5}}})
    sv = saved()
    sv["nodes"].append({"id": 9, "type": "SomeNodeNobodyIndexed", "inputs": [],
                        "widgets_values": [0.5]})
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(api, sv)
    assert "no widget index recorded" in str(exc.value)


def test_the_animate_route_classes_are_all_in_the_table():
    for cls in ("KSampler", "WanAnimateToVideo", "LoadImage", "TrimVideoLatent",
                "CreateVideo", "SaveVideo", "SaveImage", "VAEDecode"):
        assert cls in GSG.WIDGET_INDEX, cls


def test_the_ksampler_widget_offsets_account_for_control_after_generate():
    """Save format inserts the widget API format has no slot for; every index after the
    seed shifts by one, and a positional zip sails past exactly that."""
    idx = GSG.WIDGET_INDEX["KSampler"]
    wv = [2026081221, "fixed", 20, 6.0, "uni_pc", "simple", 1.0]
    assert wv[idx["seed"]] == 2026081221
    assert wv[idx["steps"]] == 20 and wv[idx["cfg"]] == 6.0
    assert wv[idx["sampler_name"]] == "uni_pc" and wv[idx["denoise"]] == 1.0
    assert "control_after_generate" not in idx


# ---------------------------------------------------------------- the topology half

def test_a_faithful_round_trip_compares_every_link_and_every_empty_socket():
    ev = GSG.link_round_trip(API, saved())
    assert ev["n_links"] == 4
    assert ev["optional_sockets_empty_in_both"] == ["49.background_video", "68.audio"]


def test_a_socket_the_save_wired_that_we_left_empty_is_caught():
    """THE clause. A `background_video` appearing in the save/convert round trip would
    produce a graph that runs, costs the same, and makes the scene clause unmeasurable —
    with every widget value still matching."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(API, saved(extra_link=99))
    assert "the saved file wired it and we left it empty" in str(exc.value)
    assert "background_video" in str(exc.value)


def test_a_link_the_save_lost_is_caught_too():
    """It binds in both directions: a dropped conditioning link is a different defect and
    a value-only comparison passes on it just as happily."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(API, saved(drop_link=True))
    assert "we wired it and the saved file carries no link" in str(exc.value)


def test_a_socket_the_save_REMOVED_entirely_is_caught(tmp_path):
    """Wave 3, F-3be7aebb. The comparison iterated the SAVED node's socket list, so a
    socket we wired that the round trip removed outright was never visited and the
    "we wired it and the saved file carries no link" branch never ran. `round_trip` does
    not cover it either — it skips list-valued inputs as links.

    Measured on this exact fixture before the fix: with the socket present and its link
    null the gate RAISED; with the socket ABSENT, `link_round_trip` returned
    {n_links: 0, links: [], optional_sockets_empty_in_both: []} and `round_trip` returned
    n_values_compared=4, all_equal=True — both clean, on a graph the cloud would execute
    with a conditioning link missing.
    """
    api = {"49": {"class_type": "WanAnimateToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                             "continue_motion_max_frames": 5, "video_frame_offset": 0,
                             "control_video": ["200", 0]}}}
    sv = {"nodes": [{"id": 49, "type": "WanAnimateToVideo",
                     "inputs": [{"name": "vae", "type": "VAE", "link": 12}],
                     "widgets_values": [832, 480, 81, 1, 5, 0]}]}
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(api, sv)
    assert "control_video" in str(exc.value)
    assert "no socket" in str(exc.value)


def test_the_removed_socket_clause_does_not_fire_on_a_literal_we_wrote():
    """The mutation that must NOT fire it: `width` is a literal, not a link, and the value
    round trip owns it. A clause that fired here would refuse every faithful graph."""
    api = {"49": {"class_type": "WanAnimateToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                             "continue_motion_max_frames": 5, "video_frame_offset": 0}}}
    sv = {"nodes": [{"id": 49, "type": "WanAnimateToVideo", "inputs": [],
                     "widgets_values": [832, 480, 81, 1, 5, 0]}]}
    ev = GSG.link_round_trip(api, sv)
    assert ev["n_links"] == 0


def test_the_union_visits_both_sides_at_once():
    """One graph carrying both defects: a socket we wired that the save removed, and a
    socket the save wired that we left empty. Both must be reported, not the first."""
    api = {"49": {"class_type": "WanAnimateToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                             "continue_motion_max_frames": 5, "video_frame_offset": 0,
                             "control_video": ["200", 0]}}}
    sv = {"nodes": [{"id": 49, "type": "WanAnimateToVideo",
                     "inputs": [{"name": "background_video", "type": "IMAGE", "link": 99}],
                     "widgets_values": [832, 480, 81, 1, 5, 0]}]}
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(api, sv)
    problems = exc.value.evidence["problems"]
    assert any("control_video" in p for p in problems)
    assert any("background_video" in p for p in problems)


# ---------------------------------------------------------- a refuse leaves no directory


def test_a_refused_admission_leaves_no_output_directory(tmp_path):
    """Wave 3, F-451d9008. `os.makedirs` sat above every check in this tool, so a halted
    admission left an empty directory beside real ones, read later as a run that happened.
    build_payload.py states the repo's invariant — a refuse must leave no output directory
    — and it held for Gate CANON only."""
    import json

    api_path = tmp_path / "in" / "g.api.json"
    saved_path = tmp_path / "in" / "g.saved.json"
    seeds_path = tmp_path / "in" / "seeds.json"
    api_path.parent.mkdir(parents=True)
    api_path.write_text(json.dumps({
        "49": {"class_type": "WanAnimateToVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                          "continue_motion_max_frames": 5, "video_frame_offset": 0}}}),
        encoding="utf-8")
    saved_path.write_text(json.dumps({"nodes": [
        {"id": 49, "type": "WanAnimateToVideo", "inputs": [],
         "widgets_values": [832, 480, 65, 1, 5, 0]}]}), encoding="utf-8")   # 65, not 81
    seeds_path.write_text(json.dumps({"seeds": [1]}), encoding="utf-8")

    out = tmp_path / "fresh" / "admission.json"
    with pytest.raises(RG.RouteGate):
        GSG.main([f"--saved={saved_path}", f"--api={api_path}",
                  f"--seeds={seeds_path}", f"--out={out}"])
    assert not out.exists()
    assert not out.parent.exists(), "a refused admission created its output directory"


# ------------------------------------------- the link TABLE, resolved (wave 6, F-004403e2)

#: Two same-type CONDITIONING links into one node. The only thing that differs between the
#: as-built save and the crossed one is WHICH of the two link ids each socket carries — and
#: the saved file's own link table says so. Every widget value is identical in both.
CROSS_API = {
    "30": {"class_type": "CLIPTextEncode", "inputs": {"text": "the positive"}},
    "31": {"class_type": "CLIPTextEncode", "inputs": {"text": "the negative"}},
    "50": {"class_type": "WanCameraImageToVideo",
           "inputs": {"width": 832, "height": 480, "length": 65, "batch_size": 1,
                      "positive": ["30", 0], "negative": ["31", 0]}},
}


def cross_saved(crossed=False, links=True, table=None):
    """The converter's own shape: sockets carrying link IDS, and a top-level link table."""
    pos, neg = (7, 6) if crossed else (6, 7)
    doc = {"nodes": [
        {"id": 30, "type": "CLIPTextEncode", "inputs": [],
         "widgets_values": ["the positive"]},
        {"id": 31, "type": "CLIPTextEncode", "inputs": [],
         "widgets_values": ["the negative"]},
        {"id": 50, "type": "WanCameraImageToVideo",
         "inputs": [{"name": "positive", "type": "CONDITIONING", "link": pos},
                    {"name": "negative", "type": "CONDITIONING", "link": neg}],
         "widgets_values": [832, 480, 65, 1]},
    ]}
    if table is not None:
        doc["links"] = table
    elif links:
        doc["links"] = ([[6, 30, 0, 50, 1, "CONDITIONING"],
                         [7, 31, 0, 50, 0, "CONDITIONING"]] if crossed else
                        [[6, 30, 0, 50, 0, "CONDITIONING"],
                         [7, 31, 0, 50, 1, "CONDITIONING"]])
    return doc


def test_the_as_built_save_resolves_every_link_to_the_node_we_wired():
    ev = GSG.link_round_trip(CROSS_API, cross_saved())
    assert ev["n_links"] == 2
    assert ev["links"] == ["50.negative", "50.positive"]


def test_two_conditioning_links_crossed_in_the_save_are_caught():
    """The finding. `slot.get("link") is not None` is satisfied by ANY link id, so the
    as-built file and the crossed one produced byte-identical gate output: n_links 5 with
    the identical `links` list, and `round_trip` all_equal on both. A conditioning swap is
    the most expensive thing this comparison can miss, on the last gate before credits."""
    assert GSG.round_trip(CROSS_API, cross_saved(crossed=True))["all_equal"] is True
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, cross_saved(crossed=True))
    problems = exc.value.evidence["problems"]
    assert any("50.positive" in p for p in problems), problems
    assert any("50.negative" in p for p in problems), problems
    assert any("31" in p for p in problems), problems


def test_a_link_id_the_saved_table_does_not_carry_is_its_own_clause():
    doc = cross_saved(table=[[6, 30, 0, 50, 0, "CONDITIONING"]])   # link 7 unlisted
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, doc)
    assert "link 7" in str(exc.value)


def test_a_link_whose_origin_node_the_saved_file_does_not_declare_is_its_own_clause():
    doc = cross_saved(table=[[6, 30, 0, 50, 0, "CONDITIONING"],
                             [7, 999, 0, 50, 1, "CONDITIONING"]])
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, doc)
    assert "999" in str(exc.value)


def test_an_origin_slot_that_moved_is_caught():
    """Same origin node, different output slot: a value-only comparison passes and so does
    a comparison that only asks whether a link id is present."""
    doc = cross_saved(table=[[6, 30, 1, 50, 0, "CONDITIONING"],
                             [7, 31, 0, 50, 1, "CONDITIONING"]])
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, doc)
    assert "slot" in str(exc.value)


def test_a_saved_file_that_carries_links_but_no_link_table_is_refused_by_name():
    """Nothing can be resolved, so no origin claim is checkable and the verdict may not
    say the topology is the topology this repo built."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, cross_saved(links=False))
    assert "link table" in str(exc.value)


def test_a_malformed_link_table_entry_halts_rather_than_being_skipped():
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_round_trip(CROSS_API, cross_saved(table=[[6, 30, 0], "nonsense"]))
    assert "link table" in str(exc.value)


# ------------------------------------- a wrapped save-format file (wave 6, F-2b80fb89)


def _wrapped_case(tmp_path, wrapper):
    import json as _json

    d = tmp_path / "in"
    d.mkdir(parents=True)
    graph = {"nodes": [{"id": 49, "type": "WanAnimateToVideo", "inputs": [],
                        "widgets_values": [832, 480, 81, 1, 5, 0]}]}
    (d / "g.saved.json").write_text(_json.dumps({wrapper: graph}), encoding="utf-8")
    (d / "g.api.json").write_text(_json.dumps({
        "49": {"class_type": "WanAnimateToVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                          "continue_motion_max_frames": 5, "video_frame_offset": 0}}}),
        encoding="utf-8")
    (d / "seeds.json").write_text(_json.dumps({"seeds": [1]}), encoding="utf-8")
    return d


#: Wrapper keys that are NOT in the loader's unwrap list, computed rather than typed:
#: core-gates owns that list (wave 6 publishes `route_gates.WRAPPER_KEYS` and adds
#: `prompt` to it), and a fixture that hard-coded a key which later became recognised
#: would test the opposite of what it says.
UNRECOGNISED_WRAPPERS = [w for w in ("prompt", "output", "some_surface_nobody_mapped")
                         if w not in GSG.UNWRAPPED_BY_LOAD_GRAPH]


@pytest.mark.parametrize("wrapper", UNRECOGNISED_WRAPPERS)
def test_a_wrapped_saved_file_is_refused_by_a_gate_not_by_a_stdlib_key(tmp_path, wrapper):
    """`load_graph` unwraps a known key list and returns anything else as the wrapper dict,
    so `round_trip`'s first statement raised a bare `KeyError: 'nodes'` with no gate id and
    no evidence — while Gate ROUTE and Gate S both return GREEN verdicts over zero nodes on
    the same doc, because `_iter_nodes` reads a wrapper-key doc as no nodes. The KeyError
    was the only thing standing between a wrapped file and a SAVED_ADMISSION_OK over a
    graph nothing examined.

    SEAM: which layer refuses is core-gates' to decide — its wave-6 `load_graph` refuses an
    unrecognised mapping by name itself, and this tool's own boundary check refuses
    whatever the loader hands back without a `nodes` list. This fixture pins the invariant
    both must keep: a RouteGate, and no output directory."""
    d = _wrapped_case(tmp_path, wrapper)
    out = tmp_path / "fresh" / "admission.json"
    with pytest.raises(RG.RouteGate):
        GSG.main([f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
                  f"--seeds={d / 'seeds.json'}", f"--out={out}"])
    assert not out.parent.exists(), "a refused admission created its output directory"


def test_an_api_format_graph_passed_as_saved_is_refused_by_name(tmp_path):
    """The doc that reaches THIS tool's boundary check whichever loader is in front of it:
    a mapping the loader recognises and hands back, that is simply not save format. The
    halt says the argument is not a save-format graph rather than naming a dict key."""
    import json as _json

    d = _wrapped_case(tmp_path, "workflow")
    api_as_saved = d / "api-as-saved.json"
    api_as_saved.write_text((d / "g.api.json").read_text(encoding="utf-8"),
                            encoding="utf-8")
    out = tmp_path / "fresh" / "admission.json"
    with pytest.raises(RG.RouteGate) as exc:
        GSG.main([f"--saved={api_as_saved}", f"--api={d / 'g.api.json'}",
                  f"--seeds={d / 'seeds.json'}", f"--out={out}"])
    assert "save-format graph" in str(exc.value)
    assert exc.value.evidence["top_level_keys"] == ["49"]
    assert exc.value.evidence["unwrapped_by_load_graph"]
    assert not out.parent.exists(), "a refused admission created its output directory"
    assert _json.loads(api_as_saved.read_text(encoding="utf-8"))


def test_the_wrappers_load_graph_does_unwrap_still_admit(tmp_path):
    """The mutation that must NOT fire it: every key the loader unwraps."""
    for wrapper in GSG.UNWRAPPED_BY_LOAD_GRAPH:
        d = _wrapped_case(tmp_path / wrapper, wrapper)
        loaded = RG.load_graph(str(d / "g.saved.json"))
        assert [n["id"] for n in loaded["nodes"]] == [49]


# ------------------- the value round trip compares EXACTLY (wave 8, F-a3c3daf8)

#: A `Wan2ReferenceVideoApi` node in this repo's own API shape — the hosted tier whose
#: widget row `WIDGET_INDEX` carries, and the one class here that pins a seed as a literal
#: rather than a link. Built from the table's own row so the fixture cannot drift from it.
REF_API = {
    "80": {"class_type": "Wan2ReferenceVideoApi",
           "inputs": {"model": "wan2.7-r2v", "model.prompt": "a prompt",
                      "model.negative_prompt": "a negative", "model.resolution": "720P",
                      "model.ratio": "16:9", "model.duration": 5,
                      "seed": 2026081351, "watermark": False}},
}


def ref_saved(seed=2026081351, watermark=False):
    """The converted shape: `control_after_generate` inserted at 7, watermark at 8."""
    return {"nodes": [
        {"id": 80, "type": "Wan2ReferenceVideoApi", "inputs": [],
         "widgets_values": ["wan2.7-r2v", "a prompt", "a negative", "720P", "16:9", 5,
                            seed, "fixed", watermark]},
    ]}


def test_the_reference_tier_round_trips_when_nothing_moved():
    """The mutation that must NOT fire the exact comparison: a faithful save."""
    ev = GSG.round_trip(REF_API, ref_saved())
    assert ev["all_equal"] is True
    assert ev["n_values_compared"] == 8


def test_a_64_bit_seed_that_moved_by_one_is_caught():
    """The finding. The predicate carried a `float()` clause, and `float()` on an integer
    above 2**53 loses the low bits: measured, built 18446744073709551615 against saved
    18446744073709551614 gave `got == value` False and `float(got) == float(value)` True,
    so `same` was True and the function returned n_values_compared=3, all_equal=True with
    {'input': 'seed', 'built': ...615, 'saved': ...614, 'equal': True} in its own evidence.
    ComfyUI seeds are 64-bit, so the last gate before a paid submission would report every
    value round-tripped while the seed the cloud executes is not the seed the record names.
    """
    built = 2 ** 64 - 1
    api = {"80": dict(REF_API["80"], inputs=dict(REF_API["80"]["inputs"], seed=built))}
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(api, ref_saved(seed=built - 1))
    assert "80.seed" in str(exc.value)
    assert str(built) in str(exc.value)


def test_a_bool_saved_as_an_int_is_not_read_as_equal():
    """The second half of the same predicate. `False` built against `0` saved compared
    equal under both clauses; `True` against `1` still does under plain `==`. The two
    spellings do not mean the same thing to every converter, and a round trip that
    re-typed a switch is a change this gate exists to see."""
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(REF_API, ref_saved(watermark=0))
    assert "80.watermark" in str(exc.value)

    api = {"80": dict(REF_API["80"], inputs=dict(REF_API["80"]["inputs"], watermark=True))}
    with pytest.raises(RG.RouteGate) as exc:
        GSG.round_trip(api, ref_saved(watermark=1))
    assert "80.watermark" in str(exc.value)


def test_an_int_and_the_same_value_as_a_float_still_compare_equal():
    """The bound on the fix: dropping `float()` must not start refusing a converter that
    wrote `832.0` where we pinned `832` — plain `==` compares int against float EXACTLY in
    Python, which is the property the widening clause was standing in for."""
    api = {"49": {"class_type": "WanAnimateToVideo",
                  "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                             "continue_motion_max_frames": 5, "video_frame_offset": 0}}}
    sv = {"nodes": [{"id": 49, "type": "WanAnimateToVideo", "inputs": [],
                     "widgets_values": [832.0, 480, 81, 1, 5, 0]}]}
    assert GSG.round_trip(api, sv)["all_equal"] is True


# ------------- the link table is checked against ITSELF (wave 8, F-c78a122c)


def test_a_link_id_declared_twice_with_different_origins_halts():
    """The finding, one level below the crossed-links family. `table[str(lid)] = (...)` was
    a last-write-wins assignment with no duplicate clause, so a file declaring link 6 first
    from the NEGATIVE encoder and then from the positive resolved to whichever entry came
    last and discarded the other unexamined. Measured on this fixture before the clause:
    {'n_links': 2, 'links': ['50.negative', '50.positive'], ...} with no halt — a file that
    is ambiguous about where its conditioning comes from, admitted by the last gate before
    credits are spent."""
    doc = cross_saved(table=[[6, 31, 0, 50, 0, "CONDITIONING"],
                             [6, 30, 0, 50, 0, "CONDITIONING"],
                             [7, 31, 0, 50, 1, "CONDITIONING"]])
    with pytest.raises(RG.RouteGate) as exc:
        GSG.link_table(doc)
    assert "6" in str(exc.value)
    ev = exc.value.evidence
    assert ev["link_id"] == "6"
    assert sorted(map(list, ev["origins"])) == [["30", 0], ["31", 0]]
    assert ev["andon"] == "duplicate_link_id"


def test_the_duplicate_clause_reaches_the_topology_gate_too():
    doc = cross_saved(table=[[6, 31, 0, 50, 0, "CONDITIONING"],
                             [6, 30, 0, 50, 0, "CONDITIONING"],
                             [7, 31, 0, 50, 1, "CONDITIONING"]])
    with pytest.raises(RG.RouteGate, match=r"declares link .* TWICE with different"):
        GSG.link_round_trip(CROSS_API, doc)


def test_a_link_id_repeated_with_the_SAME_origin_is_not_a_defect():
    """The mutation that must NOT fire it: a converter that wrote the same edge twice says
    nothing ambiguous, and a clause that refused it would refuse a faithful file."""
    doc = cross_saved(table=[[6, 30, 0, 50, 0, "CONDITIONING"],
                             [6, 30, 0, 50, 0, "CONDITIONING"],
                             [7, 31, 0, 50, 1, "CONDITIONING"]])
    assert GSG.link_round_trip(CROSS_API, doc)["n_links"] == 2


# ------------- BOTH graph arguments read through the ONE loader (wave 8, F-4c5f67de)


def test_a_wrapped_api_file_is_unwrapped_rather_than_dying_on_a_stdlib_key(tmp_path):
    """`--api` was a bare `json.load` with no format check at all, two lines below a
    `--saved` that goes through `RG.load_graph` and is refused BY NAME. Measured before the
    fix: an api file wrapped as {'prompt': {...}} — the standard submission envelope, and a
    shape the loader knows how to unwrap — raised `KeyError: 'class_type'` out of
    `round_trip`, reported as SAVED_ADMISSION_HALT with "error": "KeyError", "message":
    "'class_type'" — a stdlib key name standing in for a sentence, on the last gate before
    a paid submission."""
    import json as _json

    d = _wrapped_case(tmp_path, "workflow")
    api = _json.loads((d / "g.api.json").read_text(encoding="utf-8"))
    (d / "g.api.json").write_text(_json.dumps({"prompt": api}), encoding="utf-8")

    # The unwrap itself, at the level that used to die: both exported comparisons read the
    # envelope and find the graph inside it.
    saved_doc = _json.loads((d / "g.saved.json").read_text(encoding="utf-8"))
    assert GSG.round_trip({"prompt": api}, saved_doc)["all_equal"] is True
    assert GSG.link_round_trip({"prompt": api}, saved_doc)["n_links"] == 0

    # And through `main`: whatever this one-node fixture halts on downstream, it is a NAMED
    # gate carrying evidence, never `KeyError: 'class_type'` with a dict key for a sentence.
    out = tmp_path / "fresh" / "admission.json"
    with pytest.raises(Exception) as exc:
        GSG.main([f"--saved={d / 'g.saved.json'}", f"--api={d / 'g.api.json'}",
                  f"--seeds={d / 'seeds.json'}", f"--out={out}"])
    assert not isinstance(exc.value, (KeyError, TypeError)), exc.value
    assert exc.value.evidence.get("gate"), exc.value
    assert "class_type" not in str(exc.value)


def test_a_save_format_file_passed_as_api_is_refused_by_a_named_format_clause(tmp_path):
    """The mirror of the `--saved` boundary block. Measured before the fix: a save-format
    doc passed as `--api` raised `TypeError: list indices must be integers or slices, not
    str` out of `round_trip`."""
    d = _wrapped_case(tmp_path, "workflow")
    swapped = d / "saved-as-api.json"
    swapped.write_text((d / "g.saved.json").read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "fresh" / "admission.json"
    with pytest.raises(RG.RouteGate) as exc:
        GSG.main([f"--saved={d / 'g.saved.json'}", f"--api={swapped}",
                  f"--seeds={d / 'seeds.json'}", f"--out={out}"])
    assert "API-format graph" in str(exc.value)
    assert exc.value.evidence["clause"] == "not_an_api_format_graph"
    assert not out.parent.exists(), "a refused admission created its output directory"


@pytest.mark.parametrize("wrapper", ["workflow", "prompt"])
def test_round_trip_and_link_round_trip_normalise_their_own_saved_argument(wrapper):
    """The divergence the wave-6 loader left behind, live for any direct caller (the tests
    are the only ones today, and the pipeline's next tool need not be). Measured before the
    fix: `round_trip({'workflow': <save doc>}, ...)` and the identical read inside
    `link_round_trip` each raised a bare `KeyError: 'nodes'`, while `route_gates`'
    `normalise_graph` unwraps both wrappers to a readable save-format graph. Two exported
    functions and the module's own loader disagreed on the same input."""
    assert GSG.round_trip(CROSS_API, {wrapper: cross_saved()})["all_equal"] is True
    assert GSG.link_round_trip(CROSS_API, {wrapper: cross_saved()})["n_links"] == 2


def test_an_api_format_doc_passed_as_the_saved_argument_is_refused_by_name():
    """The direct-call mirror of the `main` boundary block: a mapping the loader recognises
    and hands back, that is simply not save format. Before the fix this was
    `KeyError: 'nodes'` from both functions."""
    for fn in (GSG.round_trip, GSG.link_round_trip):
        with pytest.raises(RG.RouteGate) as exc:
            fn(CROSS_API, CROSS_API)
        assert "save-format graph" in str(exc.value)
        assert exc.value.evidence["clause"] == "not_a_save_format_graph"
