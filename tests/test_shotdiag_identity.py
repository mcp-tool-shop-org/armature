"""Synthetic CPU tests for masked subject identity diagnostics (`I1`–`I6` + refusals).

Loads zero learned models: all embedding tests inject a deterministic numpy patch/CLS
embedder, and the DINOv2 loader path is tested for its `"weights not present"` refusal,
its `MeasureWeightGate` handoff, and its missing-runtime refusal (`docs/dispatches/shot-diagnostics-design.md` §5).
"""

import hashlib
import json

import numpy as np
import pytest

from armature_core import measure_weights as MW
from armature_core import pngio
from armature_core import shotdiag as SD
from armature_core.errors import GateFailure
from armature_core.measure_weights import MeasureWeightGate
from armature_core.shotdiag import ShotDiagError
import measure_shot as MS
import sheet_compose as SC


# ---------------------------------------------------------------------------
# Deterministic CPU stand-in embedder and synthetic RGBA / frame builders
# ---------------------------------------------------------------------------


def _patch_descriptor(patch_14x14):
    """9-D colour/texture descriptor orthogonal to `IDENTITY_PLATE_RGB = (154, 154, 157)`."""
    p = np.asarray(patch_14x14, dtype=np.float64)
    plate = np.array([154.0, 154.0, 157.0], dtype=np.float64)
    d = p - plate.reshape(1, 1, 3)
    max_dev = float(np.max(np.abs(d)))
    if max_dev < 1.0:
        # Pure neutral-plate token points along dedicated axis 8 so non-plate tokens have 0 dot with plate.
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float64)

    dx = float(np.mean(np.abs(np.diff(p, axis=1))))
    dy = float(np.mean(np.abs(np.diff(p, axis=0))))
    vec = np.array(
        [
            float(np.mean(d[:, :, 0])),
            float(np.mean(d[:, :, 1])),
            float(np.mean(d[:, :, 2])),
            float(np.std(p[:, :, 0])),
            float(np.std(p[:, :, 1])),
            float(np.std(p[:, :, 2])),
            dx,
            dy,
            0.0,
        ],
        dtype=np.float64,
    )
    norm = float(np.linalg.norm(vec))
    return vec / (norm if norm > 1e-12 else 1.0)


def _deterministic_embedder(rgb_224):
    """Stand-in `(224, 224, 3) -> {'cls': (9,), 'patches': (256, 9)}` embedder on CPU."""
    arr = np.asarray(rgb_224, dtype=np.uint8)
    ps = SD.DINOV2_PATCH_SIZE
    side = SD.DINOV2_GRID_SIDE
    patches = np.zeros((side * side, 9), dtype=np.float64)
    non_plate = []
    idx = 0
    for gy in range(side):
        for gx in range(side):
            tile = arr[gy * ps : (gy + 1) * ps, gx * ps : (gx + 1) * ps]
            desc = _patch_descriptor(tile)
            patches[idx] = desc
            if desc[8] < 0.5:
                non_plate.append(desc)
            idx += 1
    if non_plate:
        cls_raw = np.mean(np.vstack(non_plate), axis=0)
    else:
        cls_raw = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float64)
    cls_norm = float(np.linalg.norm(cls_raw))
    return {
        "cls": cls_raw / (cls_norm if cls_norm > 1e-12 else 1.0),
        "patches": patches,
    }


def _make_rgba_character(primary_rgb, accent_rgb, *, size=128):
    """Authored RGBA character icon with real alpha silhouette and internal stripe texture."""
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    y0, y1 = 20, size - 20
    x0, x1 = 24, size - 24
    rgba[y0:y1, x0:x1, :3] = np.asarray(primary_rgb, dtype=np.uint8)
    rgba[y0:y1:8, x0:x1, :3] = np.asarray(accent_rgb, dtype=np.uint8)
    rgba[y0:y1, x0:x1:10, :3] = np.asarray(accent_rgb, dtype=np.uint8)
    rgba[y0:y1, x0:x1, 3] = 255
    return rgba


def _paint_frame_with_character(
    bg_rgb,
    bg_stripe_rgb,
    char_primary_rgb,
    char_accent_rgb,
    *,
    height=192,
    width=256,
    box=(48, 76, 144, 176),
):
    """Build `(frame_rgb, mask_bool)` with structured background and an in-mask character."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = np.asarray(bg_rgb, dtype=np.uint8)
    frame[::12, :] = np.asarray(bg_stripe_rgb, dtype=np.uint8)

    y0, x0, y1, x1 = box
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    frame[y0:y1, x0:x1] = np.asarray(char_primary_rgb, dtype=np.uint8)
    frame[y0:y1:8, x0:x1] = np.asarray(char_accent_rgb, dtype=np.uint8)
    frame[y0:y1, x0:x1:10] = np.asarray(char_accent_rgb, dtype=np.uint8)
    return frame, mask


# ---------------------------------------------------------------------------
# I1–I6 + presence / runtime / shape refusals
# ---------------------------------------------------------------------------


def test_i1_changing_background_moves_whole_frame_cosine_but_leaves_masked_score_unchanged():
    """I1: Fails if background pixels outside the Blender mask leak into the masked crop."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))

    f_green_bg, m0 = _paint_frame_with_character(
        (36, 112, 48), (24, 84, 34), (228, 52, 38), (245, 205, 45)
    )
    f_cyan_bg, m1 = _paint_frame_with_character(
        (30, 195, 235), (18, 130, 210), (228, 52, 38), (245, 205, 45)
    )

    ident = SD.measure_masked_identity(
        [f_green_bg, f_cyan_bg],
        [m0, m1],
        [subj_ref],
        [decoy_ref],
        embedder=_deterministic_embedder,
    )
    whole = SD.whole_frame_cosine_series(
        [f_green_bg, f_cyan_bg], [subj_ref], _deterministic_embedder
    )

    assert ident["n_fired"] == 2
    s0 = ident["per_frame"][0]["score"]
    s1 = ident["per_frame"][1]["score"]
    assert abs(s0 - s1) < 1e-12
    assert abs(whole[0] - whole[1]) > 0.08


def test_i2_changing_subject_inside_identical_background_drops_masked_score():
    """I2: Fails if the masked identity score is insensitive to the character region inside the mask."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))

    f_match, m0 = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )
    # Drift the character toward muted olive-ochre while keeping it above decoy/bg floors.
    f_drifted, m1 = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (170, 166, 86), (160, 168, 118)
    )

    ident = SD.measure_masked_identity(
        [f_match, f_drifted],
        [m0, m1],
        [subj_ref],
        [decoy_ref],
        embedder=_deterministic_embedder,
    )
    assert ident["per_frame"][0]["fired"] is True
    assert ident["per_frame"][1]["fired"] is True
    assert ident["per_frame"][0]["score"] > ident["per_frame"][1]["score"] + 0.12


def test_i3_sub_patch_mask_and_floor_dominated_crop_report_not_fired_with_null_score():
    """I3: Fails if a number is quoted when the mask is <1 patch (14x14) or <= its floor maximum."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))

    # Frame 0: tiny 9x9 px mask (< 14x14 full patch) -> BELOW ONE PATCH, score: None.
    f_tiny, _ = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )
    tiny_mask = np.zeros(f_tiny.shape[:2], dtype=bool)
    tiny_mask[80:89, 100:109] = True

    # Frame 1: character region actually holds the DECOY character -> subject score <= decoy floor -> NOT SEPARABLE.
    f_decoy_in_mask, normal_mask = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (28, 88, 226), (45, 212, 215)
    )

    ident = SD.measure_masked_identity(
        [f_tiny, f_decoy_in_mask],
        [tiny_mask, normal_mask],
        [subj_ref],
        [decoy_ref],
        embedder=_deterministic_embedder,
    )
    assert ident["n_fired"] == 0
    assert ident["score"]["n"] == 0
    assert ident["score"]["median"] is None
    assert ident["patch_score"]["median"] is None

    row0, row1 = ident["per_frame"]
    assert row0["fired"] is False
    assert row0["status"] == "BELOW ONE PATCH"
    assert row0["score"] is None
    assert row0["patch_score"] is None

    assert row1["fired"] is False
    assert row1["status"] == "NOT SEPARABLE"
    assert row1["score"] is None
    assert row1["patch_score"] is None
    assert row1["floors"]["decoy"] is not None
    assert row1["floors"]["max_floor"] >= row1["floors"]["decoy"]


def test_i4_decoy_self_comparison_and_missing_reference_refusals(tmp_path):
    """I4: Fails if subject and decoy references can be the same character image, or lack real RGBA alpha."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_same = subj_ref.copy()
    frame, mask = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )

    with pytest.raises(ShotDiagError) as exc:
        SD.measure_masked_identity(
            [frame],
            [mask],
            [subj_ref],
            [decoy_same],
            embedder=_deterministic_embedder,
        )
    assert exc.value.evidence["clause"] == "decoy_matches_subject_reference"

    # Non-RGBA (3-channel RGB) reference -> `reference_missing_alpha`.
    rgb_only_path = tmp_path / "rgb_ref.png"
    pngio.write_png(str(rgb_only_path), frame)
    with pytest.raises(ShotDiagError) as exc:
        SD.load_rgba_references(str(rgb_only_path))
    assert exc.value.evidence["clause"] == "reference_missing_alpha"

    # All-zero alpha RGBA reference -> `reference_alpha_empty`.
    empty_rgba = np.zeros((64, 64, 4), dtype=np.uint8)
    with pytest.raises(ShotDiagError) as exc:
        SD.crop_rgba_reference(empty_rgba)
    assert exc.value.evidence["clause"] == "reference_alpha_empty"

    # Missing subject / decoy / mask refusals on core and CLI.
    with pytest.raises(ShotDiagError) as exc:
        SD.measure_masked_identity([frame], [mask], [], [subj_ref], embedder=_deterministic_embedder)
    assert exc.value.evidence["clause"] == "missing_subject_reference"

    with pytest.raises(ShotDiagError) as exc:
        SD.measure_masked_identity([frame], [mask], [subj_ref], [], embedder=_deterministic_embedder)
    assert exc.value.evidence["clause"] == "missing_decoy_reference"

    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    pngio.write_png(str(frames_dir / "00000.png"), frame)
    pngio.write_png(str(frames_dir / "00001.png"), frame)
    subj_path = tmp_path / "subj.png"
    decoy_path = tmp_path / "decoy.png"
    pngio.write_png(str(subj_path), subj_ref)
    pngio.write_png(str(decoy_path), _make_rgba_character((28, 88, 226), (45, 212, 215)))

    with pytest.raises(ShotDiagError) as exc:
        MS.main(
            [
                "--frames",
                str(frames_dir),
                "--static",
                "--reference",
                str(subj_path),
                "--decoy-reference",
                str(decoy_path),
                "--out",
                str(tmp_path / "out.json"),
            ]
        )
    assert exc.value.evidence["clause"] == "missing_subject_mask"


def test_i5_catastrophically_low_identity_score_returns_normally_and_module_defines_no_gate():
    """I5: Fails if a low identity score raises/gates or if `armature_core.shotdiag` defines a `GateFailure`."""
    for name, obj in vars(SD).items():
        if isinstance(obj, type) and obj is not GateFailure:
            assert not issubclass(obj, GateFailure), (
                f"shotdiag must define zero GateFailure subclasses; found {name}"
            )

    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))
    # Anti-correlated colour inside mask produces negative cosine similarity (-0.8 range).
    anti_frame, mask = _paint_frame_with_character(
        (154, 154, 157), (154, 154, 157), (25, 220, 235), (15, 240, 250)
    )

    # Also test a fired-but-very-negative score via a stand-in embedder where floors are -0.99 and subject is -0.80.
    call_idx = {"n": 0}

    def _low_score_embedder(_rgb):
        call_idx["n"] += 1
        k = call_idx["n"]
        # 1=subj_ref, 2=decoy_ref, 3=plate, 4=bg, 5=subj_crop
        vecs = {
            1: [1.0, 0.0, 0.0],
            2: [0.80, 0.0, -0.60],
            3: [-0.99, 0.141, 0.0],
            4: [-0.99, -0.141, 0.0],
            5: [-0.80, 0.0, 0.60],
        }
        v = np.asarray(vecs.get(k, [-0.80, 0.0, 0.60]), dtype=np.float64)
        v = v / np.linalg.norm(v)
        return {"cls": v, "patches": np.tile(v, (256, 1))}

    ident = SD.measure_masked_identity(
        [anti_frame],
        [mask],
        [subj_ref],
        [decoy_ref],
        embedder=_low_score_embedder,
    )
    assert ident["n_fired"] == 1
    assert ident["score"]["median"] < -0.75
    assert ident["status"] == "DIAGNOSTIC — every number here gates nothing"


def test_i6_record_shape_refusal_and_camera_first_ordering_in_json_and_sheet_lines():
    """I6: Fails if an identity block can exist without a camera block or print ahead of camera."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))
    frame, mask = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )
    ident = SD.measure_masked_identity(
        [frame], [mask], [subj_ref], [decoy_ref], embedder=_deterministic_embedder
    )

    # 1. `build_shot_record` refuses identity without camera.
    with pytest.raises(ShotDiagError) as exc:
        SD.build_shot_record(None, ident)
    assert exc.value.evidence["clause"] == "identity_without_camera_block"

    # 2. `sheet_compose.diagnostic_lines` refuses a malformed record carrying identity without camera.
    with pytest.raises(ShotDiagError) as exc:
        SC.diagnostic_lines({"tool": "measure_shot", "identity": ident})
    assert exc.value.evidence["clause"] == "identity_without_camera_block"

    # 3. A NOT FIRED camera block IS accepted alongside identity, and `camera` comes before `identity`
    #    both in serialized JSON key order and in `sheet_compose.diagnostic_lines` (even when a
    #    `measure_clip` record is passed earlier in `*records`).
    eye = np.eye(3, dtype=np.float64)
    zero = np.zeros(3, dtype=np.float64)
    not_fired_cam = SD.score_camera_trajectory(
        [(eye, zero), (eye, zero)],
        [{"fired": False, "n_matches": 2, "n_inliers": 0, "model": "none"}],
    )
    assert not_fired_cam["n_fired"] == 0

    rec = SD.build_shot_record(not_fired_cam, ident, label="shot")
    serialized = json.dumps(rec, allow_nan=False)
    assert serialized.index('"camera"') < serialized.index('"identity"')

    clip_rec = {
        "tool": "measure_clip",
        "arms": [
            {
                "n_frames": 2,
                "distinct": {"n_distinct": 2},
                "frame_deltas": {"stats": {"median": 4.2}},
            }
        ],
    }
    lines = SC.diagnostic_lines(clip_rec, rec)
    non_header = [ln for ln in lines if ln and not ln.startswith("MEASURED")]
    cam_indices = [idx for idx, ln in enumerate(non_header) if ln.startswith("shot.camera")]
    id_indices = [idx for idx, ln in enumerate(non_header) if ln.startswith("shot.identity")]
    clip_indices = [idx for idx, ln in enumerate(non_header) if ln.startswith("measure_clip.")]

    assert cam_indices[0] == 0, f"camera must be printed first in every report; got {non_header}"
    assert max(cam_indices) < min(id_indices)
    assert max(cam_indices) < min(clip_indices)
    assert any("NOT FIRED" in non_header[i] for i in cam_indices)
    assert any("judged by eye on the sheet above" in non_header[i] for i in id_indices)


def test_weights_not_present_and_dinov2_loader_handoff_refusals(tmp_path, monkeypatch):
    """Fails if missing DINOv2 weights attempt a download or bypass `weights_not_present` / `MeasureWeightGate`."""
    missing_weights = tmp_path / "no_such_model.safetensors"

    # 1. Missing path -> `weights_not_present` (`ShotDiagError`, `gate: None`), never downloads.
    with pytest.raises(ShotDiagError) as exc:
        SD.load_dinov2_vitb14_embedder(str(missing_weights))
    assert exc.value.evidence["clause"] == "weights_not_present"
    assert exc.value.evidence["gate"] is None

    with pytest.raises(ShotDiagError) as exc:
        SD.load_dinov2_vitb14_embedder(None)
    assert exc.value.evidence["clause"] == "weights_not_present"

    # 2. CLI `measure_shot` with `--reference` and omitted `--dinov2-weights` -> `weights_not_present`
    #    before creating any output file or directory.
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))
    frame, mask = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )
    frames_dir = tmp_path / "frames"
    masks_dir = tmp_path / "masks"
    frames_dir.mkdir()
    masks_dir.mkdir()
    mask_u8 = np.where(mask, 255, 0).astype(np.uint8)
    mask_rgb = np.stack([mask_u8, mask_u8, mask_u8], axis=-1)
    for idx in range(2):
        pngio.write_png(str(frames_dir / f"{idx:05d}.png"), frame)
        pngio.write_png(str(masks_dir / f"{idx:05d}.png"), mask_rgb)
    subj_path = tmp_path / "subj.png"
    decoy_path = tmp_path / "decoy.png"
    pngio.write_png(str(subj_path), subj_ref)
    pngio.write_png(str(decoy_path), decoy_ref)

    out_path = tmp_path / "uncreated" / "shot.json"
    with pytest.raises(ShotDiagError) as exc:
        MS.main(
            [
                "--frames",
                str(frames_dir),
                "--static",
                "--masks",
                str(masks_dir),
                "--reference",
                str(subj_path),
                "--decoy-reference",
                str(decoy_path),
                "--dinov2-weights",
                str(missing_weights),
                "--out",
                str(out_path),
            ]
        )
    assert exc.value.evidence["clause"] == "weights_not_present"
    assert not out_path.parent.exists()

    # 3. Existing local `model.safetensors` with unpinned digest hits `MeasureWeightGate`
    #    before any ML import.
    dummy_weights = tmp_path / "model.safetensors"
    dummy_bytes = b"synthetic-safetensors-header-bytes"
    dummy_weights.write_bytes(dummy_bytes)
    with pytest.raises(MeasureWeightGate) as gate_exc:
        SD.load_dinov2_vitb14_embedder(str(dummy_weights))
    assert gate_exc.value.evidence["gate"] == "MEASURE_WEIGHT"
    assert gate_exc.value.evidence["clause"] == "weight_hash_unverified"

    # 4. When `weight_table` pins the exact sha256 as ALLOWED, `MeasureWeightGate` passes
    #    and missing `torch` raises `dinov2_runtime_unavailable` cleanly.
    pinned_digest = hashlib.sha256(dummy_bytes).hexdigest()
    pinned_table = (
        {
            "repo_id": SD.DINOV2_REPO_ID,
            "revision": SD.DINOV2_REVISION,
            "filename": "model.safetensors",
            "sha256": pinned_digest,
            "verdict": "ALLOWED",
            "licence": "Apache-2.0",
            "fetched": "2026-11-11",
            "source": "https://huggingface.co/api/models/facebook/dinov2-base",
        },
    )
    real_import_module = SD.importlib.import_module

    def _missing_torch_import(name, package=None):
        if name.split(".")[0] in {"torch", "safetensors", "transformers"}:
            raise ImportError(f"No module named {name!r}")
        return real_import_module(name, package)

    monkeypatch.setattr(SD.importlib, "import_module", _missing_torch_import)
    with pytest.raises(ShotDiagError) as runtime_exc:
        SD.load_dinov2_vitb14_embedder(str(dummy_weights), weight_table=pinned_table)
    assert runtime_exc.value.evidence["clause"] == "dinov2_runtime_unavailable"


def test_i7_identity_provenance_records_weight_receipt_and_labels_stand_in(tmp_path):
    """I7 (N2): Fails if stand-in runs claim `dinov2-base` or if a gated embedder's `weight_receipt` is dropped."""
    subj_ref = _make_rgba_character((228, 52, 38), (245, 205, 45))
    decoy_ref = _make_rgba_character((28, 88, 226), (45, 212, 215))
    frame, mask = _paint_frame_with_character(
        (42, 98, 54), (28, 72, 38), (228, 52, 38), (245, 205, 45)
    )

    stand_in = SD.measure_masked_identity(
        [frame], [mask], [subj_ref], [decoy_ref], embedder=_deterministic_embedder
    )
    assert stand_in["variant"] == "injected_stand_in"
    assert stand_in["weight_receipt"] is None

    ckpt_bytes = b"synthetic-dinov2-vitb14-safetensors-bytes"
    ckpt_sha = hashlib.sha256(ckpt_bytes).hexdigest()
    ckpt_file = tmp_path / "model.safetensors"
    ckpt_file.write_bytes(ckpt_bytes)
    table = (
        {
            "repo_id": SD.DINOV2_REPO_ID,
            "revision": SD.DINOV2_REVISION,
            "filename": "model.safetensors",
            "sha256": ckpt_sha,
            "verdict": "ALLOWED",
            "licence": "Apache-2.0",
            "fetched": "2026-11-11",
            "source": "https://huggingface.co/api/models/facebook/dinov2-base",
        },
    )
    receipt = MW.gate_measurement_weight(
        str(ckpt_file),
        repo_id=SD.DINOV2_REPO_ID,
        revision=SD.DINOV2_REVISION,
        table=table,
        today="2026-11-15",
    )

    def _gated_embedder(rgb_224):
        return _deterministic_embedder(rgb_224)

    _gated_embedder.weight_receipt = receipt
    gated = SD.measure_masked_identity(
        [frame], [mask], [subj_ref], [decoy_ref], embedder=_gated_embedder
    )
    assert gated["variant"] == f"{SD.DINOV2_REPO_ID}@{SD.DINOV2_REVISION}"
    assert gated["weight_receipt"] == receipt
    assert gated["weight_receipt"]["sha256"] == ckpt_sha
