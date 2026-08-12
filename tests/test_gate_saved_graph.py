"""The saved-file admission, against a save/convert round trip that changed something.

The cloud does not run the API graph this repo builds; it runs the saved file. Everything
here is about the gap between those two objects.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import gate_saved_graph as GSG
from armature_core import route_gates as RG


API = {
    "49": {"class_type": "WanAnimateToVideo",
           "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1,
                      "continue_motion_max_frames": 5, "video_frame_offset": 0,
                      "positive": ["6", 0], "vae": ["105", 0], "pose_video": ["200", 0]}},
    "68": {"class_type": "CreateVideo",
           "inputs": {"fps": 20, "bit_depth": 8, "images": ["8", 0]}},
}


def saved(length=81, fps=20, extra_link=None, drop_link=False):
    animate_inputs = [
        {"name": "positive", "type": "CONDITIONING", "link": None if drop_link else 10},
        {"name": "vae", "type": "VAE", "link": 12},
        {"name": "pose_video", "type": "IMAGE", "link": 14},
        {"name": "background_video", "type": "IMAGE", "link": extra_link},
    ]
    return {"nodes": [
        {"id": 49, "type": "WanAnimateToVideo", "inputs": animate_inputs,
         "widgets_values": [832, 480, length, 1, 5, 0]},
        {"id": 68, "type": "CreateVideo",
         "inputs": [{"name": "images", "type": "IMAGE", "link": 17},
                    {"name": "audio", "type": "AUDIO", "link": None}],
         "widgets_values": [fps, 8]},
    ]}


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
    assert ev["n_values_compared"] == 8      # 6 Animate widgets + fps + bit_depth


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
