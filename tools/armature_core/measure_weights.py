"""Gate MEASURE_WEIGHT — licence load gate for local measurement weights.

Local Python measurement tools (such as masked-identity embedding in `shotdiag`) do not
submit a ComfyUI graph, so `route_gates.RULED_COMPONENTS` — which matches Comfy node
weight strings by filename substring — never sees them and could not rule them safely if
it did: `facebook/dinov2-base` (Apache-2.0, ALLOWED), `facebook/map-anything-apache`
(Apache-2.0, ALLOWED), `facebook/map-anything` (CC-BY-NC-4.0, BANNED), and
`facebook/VGGT-1B` (CC-BY-NC-4.0, BANNED) all publish a file named `model.safetensors`.

This module keys rulings on `(repo_id, revision, filename, sha256)` and hashes candidate
bytes on disk with stdlib `hashlib.sha256` before any model-loading library is imported.
An unknown or unpinned digest refuses: under `CLAUDE.md`, UNVERIFIED is NO, and a row
whose bytes have not yet been hashed under a weight-download grant carries `sha256: None`
so no unverified local `model.safetensors` can slip past on its filename alone.
"""

import datetime
import hashlib
import os
import sys

from .errors import GateFailure

TOOL_VERSION = "shotdiag.1"

#: Same 90-day advisory horizon `route_gates` applies to licence rulings.
LICENCE_ADVISORY_DAYS = 90


class MeasureWeightGate(GateFailure):
    """A measurement weight file was refused before any model loader opened it."""

    gate = "MEASURE_WEIGHT"


#: Distinctive filename stems of non-commercial measurement models. Checked before hash
#: lookup so published checkpoints with distinctive filenames report `weight_banned`
#: directly. Deliberately omits a bare `"vggt"` stem because `vggt_1B_commercial.pt`
#: belongs to `facebook/VGGT-1B-Commercial` (UNVERIFIED behind a manual gate, not
#: CC-BY-NC-4.0); a bare family stem would misclassify the commercial filename as BANNED.
DISTINCTIVE_BANNED_STEMS = {
    "monst3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/Junyi42/monst3r/main/LICENSE",
    },
    "dust3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/dust3r/main/LICENSE",
    },
    "mast3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/mast3r/main/LICENSE",
    },
    "cut3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/CUT3R/CUT3R/main/LICENSE",
    },
    "vggt_omega": {
        "verdict": "BANNED",
        "licence": "fair-noncommercial-research-license",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/VGGT-Omega",
    },
    "insightface": {
        "verdict": "BANNED",
        "licence": "non-commercial-research-only",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/deepinsight/insightface/master/README.md",
    },
}


#: Measurement weight rulings fetched 2026-11-11 (`docs/dispatches/shot-diagnostics-design.md` §4).
#: `sha256` is `None` until a weight-download grant reads and pins the exact checkpoint bytes;
#: `None` never matches a candidate file digest, keeping unpinned files fail-closed.
MEASUREMENT_WEIGHTS = (
    {
        "repo_id": "facebook/dinov2-base",
        "revision": "f9e44c81",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/dinov2-base",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-small",
        "revision": "ed25f3a3",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/dinov2-small",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-large",
        "revision": "47b73eef",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/dinov2-large",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-giant",
        "revision": "611a9d42",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/dinov2-giant",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-with-registers-base",
        "revision": "a1d738cc",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/dinov2-with-registers-base",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything-apache",
        "revision": "00f9c245",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/map-anything-apache",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/map-anything/main/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything-apache-v1",
        "revision": "59bcb2c4",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/map-anything-apache-v1",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/map-anything/main/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything",
        "revision": "a1d87e90",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/map-anything",
    },
    {
        "repo_id": "facebook/VGGT-1B",
        "revision": "860abec7",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/VGGT-1B/raw/main/README.md",
    },
    {
        "repo_id": "facebook/VGGT-1B-Commercial",
        "revision": "ebb29a53",
        "filename": "vggt_1B_commercial.pt",
        "sha256": None,
        "verdict": "UNVERIFIED",
        "licence": "vggt-aup-license (checkpoint LICENSE returned HTTP 401 behind manual gate)",
        "fetched": "2026-11-11",
        "source": None,
        "non_retrieval_reason": (
            "checkpoint LICENSE file at huggingface.co/facebook/VGGT-1B-Commercial "
            "returned HTTP 401 behind a manual approval gate; treated as NO until "
            "retrieved and ruled by the Director"
        ),
    },
    {
        "repo_id": "facebook/VGGT-Omega",
        "revision": "gated",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "fair-noncommercial-research-license",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/VGGT-Omega",
    },
    {
        "repo_id": "Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt",
        "revision": "1ea2a9ea",
        "filename": "MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/Junyi42/monst3r/main/LICENSE",
    },
    {
        "repo_id": "naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt",
        "revision": "61c57447",
        "filename": "DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/dust3r/main/LICENSE",
    },
    {
        "repo_id": "naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric",
        "revision": "06e7259f",
        "filename": "MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/mast3r/main/LICENSE",
    },
    {
        "repo_id": "yyfz233/Pi3",
        "revision": "ae722e70",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "CONDITIONAL",
        "licence": "BSD-2-Clause (training-data composition not yet audited)",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/yyfz/Pi3/main/LICENSE",
    },
    {
        "repo_id": "facebook/dinov3-vitb16-pretrain-lvd1689m",
        "revision": "gated",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "CONDITIONAL",
        "licence": "DINOv3 custom gated licence",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/facebookresearch/dinov3/main/LICENSE.md",
    },
    {
        "repo_id": "ssundaram21/dreamsim",
        "revision": "v0.2.1-checkpoints",
        "filename": "dreamsim_dinov2_vitb14_checkpoint.zip",
        "sha256": None,
        "verdict": "UNVERIFIED",
        "licence": "no licence statement on GitHub release asset; NIGHTS fine-tune data unruled",
        "fetched": "2026-11-11",
        "source": "https://api.github.com/repos/ssundaram21/dreamsim/releases/tags/v0.2.1-checkpoints",
    },
)


def licence_advisory_after(fetched):
    """ISO date 90 days after `fetched`, or `None` if `fetched` is unreadable."""
    if not fetched:
        return None
    try:
        when = datetime.date.fromisoformat(str(fetched))
    except ValueError:
        return None
    return (when + datetime.timedelta(days=LICENCE_ADVISORY_DAYS)).isoformat()


def licence_age_reading(row, today=None):
    """Advisory-age metadata for one applied measurement-weight ruling."""
    today_iso = today or datetime.date.today().isoformat()
    fetched = row.get("fetched")
    advisory_after = licence_advisory_after(fetched)
    past_advisory = bool(advisory_after and today_iso > advisory_after)
    return {
        "fetched": fetched,
        "advisory_after": advisory_after,
        "today": today_iso,
        "past_advisory_days": past_advisory,
        "source": row.get("source"),
    }


def classify_weight_stem(filename, stems=None):
    """Return `(stem, row)` if `filename` matches a distinctive banned stem, else `None`.

    Note that no bare `"vggt"` stem exists in `DISTINCTIVE_BANNED_STEMS`, so
    `vggt_1B_commercial.pt` is not classified as stem-banned here.
    """
    active = DISTINCTIVE_BANNED_STEMS if stems is None else stems
    low = os.path.basename(str(filename)).lower()
    for stem, row in sorted(active.items()):
        if stem in low:
            return stem, dict(row)
    return None


def sha256_file_bytes(path):
    """Compute SHA-256 hex digest of `path` using stdlib `hashlib` only."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def gate_measurement_weight(
    path,
    *,
    repo_id=None,
    revision=None,
    director_ruling=None,
    table=None,
    stems=None,
    today=None,
):
    """Hash and check a local measurement weight file before any model loader opens it.

    Refuses with `MeasureWeightGate` (`gate = "MEASURE_WEIGHT"`) when:
    - `path` is not an existing regular file or is zero bytes;
    - the filename carries a distinctive banned stem (`monst3r`, `dust3r`, `mast3r`,
      `cut3r`, `vggt_omega`, `insightface`);
    - the file's SHA-256 (or declared `(repo_id, revision, filename)`) resolves to a
      `BANNED` or `UNVERIFIED` row, or to a `CONDITIONAL` row without `director_ruling`;
    - no `ALLOWED` (or Director-accepted `CONDITIONAL`) row in `MEASUREMENT_WEIGHTS`
      pins the file's exact 64-character SHA-256 digest.
    """
    if not path or not os.path.isfile(path):
        raise MeasureWeightGate(
            f"measurement weight path {path!r} is not an existing file on disk",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "weight_path_not_a_file",
                "path": str(path) if path is not None else None,
            },
        )

    size_bytes = os.path.getsize(path)
    if size_bytes <= 0:
        raise MeasureWeightGate(
            f"measurement weight file {path!r} is zero bytes",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "weight_file_empty",
                "path": os.path.abspath(path),
                "size_bytes": int(size_bytes),
            },
        )

    basename = os.path.basename(path)
    digest = sha256_file_bytes(path)
    stem_hit = classify_weight_stem(basename, stems=stems)
    if stem_hit is not None:
        stem, stem_row = stem_hit
        raise MeasureWeightGate(
            f"measurement weight {basename!r} matches banned model stem {stem!r} "
            f"({stem_row.get('licence')}); non-commercial weights are forbidden",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "weight_banned",
                "matched_stem": stem,
                "filename": basename,
                "sha256": digest,
                "licence": stem_row.get("licence"),
                "licence_age": licence_age_reading(stem_row, today=today),
            },
        )

    rows = MEASUREMENT_WEIGHTS if table is None else table
    digest_matches = [
        r for r in rows
        if isinstance(r.get("sha256"), str)
        and len(r["sha256"]) == 64
        and r["sha256"].lower() == digest.lower()
    ]
    declared_matches = [
        r for r in rows
        if (repo_id is not None and r.get("repo_id") == repo_id)
        and (revision is None or r.get("revision") == revision)
        and r.get("filename") == basename
    ]

    # Check explicit digest matches first: bytes govern over any filename collision
    # (`model.safetensors` is shared across Apache-2.0 and CC-BY-NC-4.0 checkpoints).
    candidates = digest_matches if digest_matches else declared_matches
    for row in candidates:
        verdict = row.get("verdict")
        if verdict == "BANNED":
            raise MeasureWeightGate(
                f"measurement weight {basename!r} ({row.get('repo_id')} @ "
                f"{row.get('revision')}) is BANNED under {row.get('licence')}",
                {
                    "gate": "MEASURE_WEIGHT",
                    "andon": "MeasureWeightGate",
                    "clause": "weight_banned",
                    "repo_id": row.get("repo_id"),
                    "revision": row.get("revision"),
                    "filename": basename,
                    "sha256": digest,
                    "licence": row.get("licence"),
                    "licence_age": licence_age_reading(row, today=today),
                },
            )
        if verdict == "UNVERIFIED":
            raise MeasureWeightGate(
                f"measurement weight {basename!r} ({row.get('repo_id')} @ "
                f"{row.get('revision')}) is UNVERIFIED — treated as NO until its "
                f"licence document is retrieved and ruled",
                {
                    "gate": "MEASURE_WEIGHT",
                    "andon": "MeasureWeightGate",
                    "clause": "weight_unverified",
                    "repo_id": row.get("repo_id"),
                    "revision": row.get("revision"),
                    "filename": basename,
                    "sha256": digest,
                    "licence": row.get("licence"),
                    "licence_age": licence_age_reading(row, today=today),
                },
            )
        if verdict == "CONDITIONAL" and not director_ruling:
            raise MeasureWeightGate(
                f"measurement weight {basename!r} ({row.get('repo_id')} @ "
                f"{row.get('revision')}) is CONDITIONAL ({row.get('licence')}) and "
                f"carries no recorded Director ruling",
                {
                    "gate": "MEASURE_WEIGHT",
                    "andon": "MeasureWeightGate",
                    "clause": "weight_conditional_unaccepted",
                    "repo_id": row.get("repo_id"),
                    "revision": row.get("revision"),
                    "filename": basename,
                    "sha256": digest,
                    "licence": row.get("licence"),
                    "licence_age": licence_age_reading(row, today=today),
                },
            )

    admitted = [
        r for r in digest_matches
        if r.get("verdict") == "ALLOWED"
        or (r.get("verdict") == "CONDITIONAL" and bool(director_ruling))
        if (repo_id is None or r.get("repo_id") == repo_id)
        and (revision is None or r.get("revision") == revision)
    ]
    if not admitted:
        raise MeasureWeightGate(
            f"measurement weight {basename!r} (sha256={digest[:16]}...) matches no "
            f"sha256-pinned ALLOWED entry in MEASUREMENT_WEIGHTS; unknown or unpinned "
            f"weights are treated as UNVERIFIED -> NO",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "weight_hash_unverified",
                "repo_id": repo_id,
                "revision": revision,
                "filename": basename,
                "sha256": digest,
            },
        )

    chosen = admitted[0]
    return {
        "gate": "MEASURE_WEIGHT",
        "verdict": chosen["verdict"],
        "repo_id": chosen["repo_id"],
        "revision": chosen["revision"],
        "filename": basename,
        "sha256": digest,
        "size_bytes": int(size_bytes),
        "licence": chosen["licence"],
        "director_ruling": director_ruling,
        "licence_age": licence_age_reading(chosen, today=today),
        "tool_version": TOOL_VERSION,
    }


def _publish_gate_to_errors_catalog():
    """Publish MeasureWeightGate into `armature_core.errors` so `GATE_BY_ID` resolves it."""
    err = sys.modules.get("armature_core.errors")
    if err is None:
        return
    err.MeasureWeightGate = MeasureWeightGate
    if hasattr(err, "refresh_gate_by_id"):
        err.refresh_gate_by_id()


_publish_gate_to_errors_catalog()
