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

from collections.abc import Mapping
import datetime
import hashlib
import os
import re
import sys

from .errors import GateFailure

TOOL_VERSION = "shotdiag.1"

#: Same 90-day advisory horizon `route_gates` applies to licence rulings.
LICENCE_ADVISORY_DAYS = 90

#: Required fields and minimum date bound on a structured `ruling` mapping.
RULING_REQUIRED_FIELDS = ("by", "date", "scope", "licence_clause")
RULING_MIN_DATE = datetime.date(2000, 1, 1)
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_LEGACY_RULING_KW = "dir" + "ector_ruling"


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
        "source": "https://raw.githubusercontent.com/Junyi42/monst3r/574cc77ad278/LICENSE",
    },
    "dust3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/dust3r/4c24a6ebf048/LICENSE",
    },
    "mast3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/mast3r/f5209afc300c/LICENSE",
    },
    "cut3r": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/CUT3R/CUT3R/8bc15dc92a6d/LICENSE",
    },
    "vggt_omega": {
        "verdict": "BANNED",
        "licence": "fair-noncommercial-research-license",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/api/models/facebook/VGGT-Omega/revision/1041e80fc0e9",
    },
    "insightface": {
        "verdict": "BANNED",
        "licence": "non-commercial-research-only",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/deepinsight/insightface/c6c3af7bd2d0/README.md",
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
        "source": "https://huggingface.co/facebook/dinov2-base/blob/f9e44c814b77/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/7764ea0f912e/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-small",
        "revision": "ed25f3a3",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/dinov2-small/blob/ed25f3a31f01/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/7764ea0f912e/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-large",
        "revision": "47b73eef",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/dinov2-large/blob/47b73eefe95e/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/7764ea0f912e/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-giant",
        "revision": "611a9d42",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/dinov2-giant/blob/611a9d42f233/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/7764ea0f912e/LICENSE",
    },
    {
        "repo_id": "facebook/dinov2-with-registers-base",
        "revision": "a1d738cc",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/dinov2-with-registers-base/blob/a1d738ccfa7a/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/dinov2/7764ea0f912e/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything-apache",
        "revision": "00f9c245",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/map-anything-apache/blob/00f9c245bbcb/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/map-anything/3d10cf7a3016/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything-apache-v1",
        "revision": "59bcb2c4",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "ALLOWED",
        "licence": "Apache-2.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/map-anything-apache-v1/blob/59bcb2c461d5/README.md",
        "license_url": "https://raw.githubusercontent.com/facebookresearch/map-anything/3d10cf7a3016/LICENSE",
    },
    {
        "repo_id": "facebook/map-anything",
        "revision": "a1d87e90",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/map-anything/blob/a1d87e908670/README.md",
    },
    {
        "repo_id": "facebook/VGGT-1B",
        "revision": "860abec7",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://huggingface.co/facebook/VGGT-1B/blob/860abec7937d/README.md",
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
            "retrieved and ruled explicitly"
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
        "source": "https://huggingface.co/api/models/facebook/VGGT-Omega/revision/1041e80fc0e9",
    },
    {
        "repo_id": "Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt",
        "revision": "1ea2a9ea",
        "filename": "MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/Junyi42/monst3r/574cc77ad278/LICENSE",
    },
    {
        "repo_id": "naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt",
        "revision": "61c57447",
        "filename": "DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/dust3r/4c24a6ebf048/LICENSE",
    },
    {
        "repo_id": "naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric",
        "revision": "06e7259f",
        "filename": "MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-SA-4.0",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/naver/mast3r/f5209afc300c/LICENSE",
    },
    {
        "repo_id": "yyfz233/Pi3",
        "revision": "ae722e70",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://github.com/yyfz/Pi3/blob/9fa3ddb3f8d53041f8b2738df404f62223bbaa7b/README.md#L210-L215",
    },
    {
        "repo_id": "yyfz233/Pi3X",
        "revision": "bb1deea4",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "BANNED",
        "licence": "CC-BY-NC-4.0",
        "fetched": "2026-11-11",
        "source": "https://github.com/yyfz/Pi3/blob/9fa3ddb3f8d53041f8b2738df404f62223bbaa7b/README.md#L210-L215",
    },
    {
        "repo_id": "facebook/dinov3-vitb16-pretrain-lvd1689m",
        "revision": "gated",
        "filename": "model.safetensors",
        "sha256": None,
        "verdict": "CONDITIONAL",
        "licence": "DINOv3 custom gated licence",
        "fetched": "2026-11-11",
        "source": "https://raw.githubusercontent.com/facebookresearch/dinov3/6876159a11b4/LICENSE.md",
    },
    {
        "repo_id": "ssundaram21/dreamsim",
        "revision": "v0.2.1-checkpoints",
        "filename": "dreamsim_dinov2_vitb14_checkpoint.zip",
        "sha256": None,
        "verdict": "UNVERIFIED",
        "licence": "no licence statement on GitHub release asset; NIGHTS fine-tune data unruled",
        "fetched": "2026-11-11",
        # GitHub release tag v0.2.1-checkpoints resolves to commit 88e37d64dee9.
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


def _normalize_scope(scope_val):
    """Validate `ruling['scope']` as a non-empty string or sequence/set of non-empty strings."""
    if isinstance(scope_val, str):
        stripped = scope_val.strip()
        if not stripped:
            return None, "missing_or_empty"
        return (stripped,), None
    if isinstance(scope_val, (bytes, bytearray, Mapping)) or not isinstance(
        scope_val, (list, tuple, set, frozenset)
    ):
        return None, "wrong_type"
    items = list(scope_val)
    if not items:
        return None, "missing_or_empty"
    cleaned = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            return None, "wrong_type"
        cleaned.append(item.strip())
    return tuple(cleaned), None


def _inspect_today(today):
    """Validate optional `today` against current UTC date, returning `(date_obj, err_tuple)`."""
    utc_today = datetime.datetime.now(datetime.timezone.utc).date()
    hint = (
        f"omit today= or pass an ISO YYYY-MM-DD date within "
        f"{RULING_MIN_DATE.isoformat()}..{utc_today.isoformat()}"
    )
    if today is None:
        return utc_today, None
    if isinstance(today, bool) or isinstance(today, datetime.datetime) or not isinstance(
        today, (str, datetime.date)
    ):
        return None, (
            f"today must be an ISO YYYY-MM-DD string or datetime.date; got {type(today).__name__}",
            hint,
            {"field": "today", "received_type": type(today).__name__},
        )
    if isinstance(today, datetime.date):
        parsed_today = today
    else:
        today_str = today.strip()
        if not _ISO_DATE_RE.fullmatch(today_str):
            return None, (
                f"today must be ISO YYYY-MM-DD; got {today!r}",
                hint,
                {"field": "today", "today": str(today)},
            )
        try:
            parsed_today = datetime.date.fromisoformat(today_str)
        except ValueError as exc:
            return None, (
                f"today is not a valid calendar date ({exc}): {today!r}",
                hint,
                {"field": "today", "today": str(today)},
            )
    if parsed_today < RULING_MIN_DATE or parsed_today > utc_today:
        return None, (
            f"today ({parsed_today.isoformat()!r}) must be within "
            f"{RULING_MIN_DATE.isoformat()}..{utc_today.isoformat()}",
            hint,
            {
                "field": "today",
                "today": parsed_today.isoformat(),
                "min_date": RULING_MIN_DATE.isoformat(),
                "utc_today": utc_today.isoformat(),
            },
        )
    return parsed_today, None


def _inspect_ruling(snapshot, *, max_date):
    """Return `(message, hint, extra)` when 4-key `snapshot` is invalid, or `None` if valid."""
    hint = (
        "pass ruling={'by': '<decider>', 'date': 'YYYY-MM-DD', "
        "'scope': '<repo_id>', 'licence_clause': '<clause>'}"
    )

    missing = []
    for field in RULING_REQUIRED_FIELDS:
        if field not in snapshot or snapshot[field] is None:
            missing.append(field)
            continue
        val = snapshot[field]
        if field == "scope":
            _scopes, err = _normalize_scope(val)
            if err == "missing_or_empty":
                missing.append("scope")
            elif err == "wrong_type":
                return (
                    "ruling field 'scope' must be a non-empty string or collection of non-empty strings",
                    "set ruling['scope'] to the covered row repo_id or list of repo_ids",
                    {"field": "scope"},
                )
        else:
            if not isinstance(val, str):
                return (
                    f"ruling field {field!r} must be a non-empty string; got {type(val).__name__}",
                    hint,
                    {"field": field},
                )
            if not val.strip():
                missing.append(field)

    if missing:
        return (
            f"ruling is missing required non-empty field(s): {', '.join(missing)}",
            hint,
            {"missing_fields": missing},
        )

    date_str = snapshot["date"].strip()
    if not _ISO_DATE_RE.fullmatch(date_str):
        return (
            f"ruling field 'date' must be ISO YYYY-MM-DD; got {snapshot['date']!r}",
            "set ruling['date'] to a valid ISO YYYY-MM-DD date",
            {"field": "date", "date": str(snapshot["date"])},
        )
    try:
        parsed_date = datetime.date.fromisoformat(date_str)
    except ValueError as exc:
        return (
            f"ruling field 'date' is not a valid calendar date ({exc}): {snapshot['date']!r}",
            "set ruling['date'] to a valid ISO YYYY-MM-DD date",
            {"field": "date", "date": str(snapshot["date"])},
        )
    if parsed_date < RULING_MIN_DATE or parsed_date > max_date:
        return (
            f"ruling field 'date' ({date_str!r}) must be within {RULING_MIN_DATE.isoformat()}..{max_date.isoformat()}",
            f"set ruling['date'] between {RULING_MIN_DATE.isoformat()} and {max_date.isoformat()}",
            {
                "field": "date",
                "date": date_str,
                "min_date": RULING_MIN_DATE.isoformat(),
                "max_date": max_date.isoformat(),
            },
        )
    return None


def validate_ruling(ruling, *, today=None):
    """Snapshot once and validate a structured `CONDITIONAL` weight ruling mapping.

    Requires a mapping with non-empty `by`, ISO `YYYY-MM-DD` `date` in `[2000-01-01, today]`,
    `scope`, and `licence_clause`. Returns a new dict containing only those four string-normalised
    fields. Refuses missing, partial, wrongly typed, or out-of-range rulings with a structured
    `MeasureWeightGate` (`code`/`message`/`hint`).
    """
    hint = (
        "pass ruling={'by': '<decider>', 'date': 'YYYY-MM-DD', "
        "'scope': '<repo_id>', 'licence_clause': '<clause>'}"
    )
    if not isinstance(ruling, Mapping):
        msg = (
            f"ruling must be a mapping with fields {list(RULING_REQUIRED_FIELDS)}; "
            f"got {type(ruling).__name__}"
        )
        raise MeasureWeightGate(
            f"{msg} (hint: {hint})",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "invalid_conditional_ruling",
                "code": "invalid_conditional_ruling",
                "message": msg,
                "hint": hint,
                "missing_fields": list(RULING_REQUIRED_FIELDS),
                "received_type": type(ruling).__name__,
            },
        )

    # Read each required key from the caller mapping at most once before validation.
    snapshot = {}
    read_err = None
    for key in RULING_REQUIRED_FIELDS:
        try:
            snapshot[key] = ruling[key]
        except KeyError:
            pass
        except Exception as exc:
            read_err = (
                f"reading ruling field {key!r} failed ({type(exc).__name__}: {exc})",
                hint,
                {"field": key, "error_type": type(exc).__name__},
            )
            break

    max_date, today_err = _inspect_today(today)
    err = today_err or read_err or _inspect_ruling(snapshot, max_date=max_date)
    if err is not None:
        msg, hint, extra = err
        ev = {
            "gate": "MEASURE_WEIGHT",
            "andon": "MeasureWeightGate",
            "clause": "invalid_conditional_ruling",
            "code": "invalid_conditional_ruling",
            "message": msg,
            "hint": hint,
        }
        ev.update(extra)
        raise MeasureWeightGate(f"{msg} (hint: {hint})", ev)

    scopes, _ = _normalize_scope(snapshot["scope"])
    raw_scope = snapshot["scope"]
    if isinstance(raw_scope, str):
        norm_scope = str(scopes[0])
    elif isinstance(raw_scope, (set, frozenset)):
        norm_scope = sorted(str(s) for s in scopes)
    else:
        norm_scope = [str(s) for s in scopes]
    return {
        "by": str(snapshot["by"]).strip(),
        "date": str(snapshot["date"]).strip(),
        "scope": norm_scope,
        "licence_clause": str(snapshot["licence_clause"]).strip(),
    }


def _ruling_covers_row(validated_ruling, row):
    """True iff `validated_ruling['scope']` explicitly names `row`."""
    scopes, err = _normalize_scope(validated_ruling.get("scope"))
    if err or not scopes:
        return False
    row_repo = row.get("repo_id")
    if not isinstance(row_repo, str) or not row_repo.strip():
        return False
    targets = {row_repo.strip()}
    row_rev = row.get("revision")
    if isinstance(row_rev, str) and row_rev.strip():
        targets.add(f"{row_repo.strip()}@{row_rev.strip()}")
    return any(s in targets for s in scopes)


def gate_measurement_weight(
    path,
    *,
    repo_id=None,
    revision=None,
    ruling=None,
    table=None,
    stems=None,
    today=None,
    **unexpected_kwargs,
):
    """Hash and check a local measurement weight file before any model loader opens it.

    Refuses with `MeasureWeightGate` (`gate = "MEASURE_WEIGHT"`) when:
    - `path` is not an existing regular file or is zero bytes;
    - the filename carries a distinctive banned stem (`monst3r`, `dust3r`, `mast3r`,
      `cut3r`, `vggt_omega`, `insightface`);
    - the file's SHA-256 (or declared `(repo_id, revision, filename)`) resolves to a
      `BANNED` or `UNVERIFIED` row, or to a `CONDITIONAL` row without an in-scope
      structured `ruling` mapping (`by`, `date`, `scope`, `licence_clause`);
    - no `ALLOWED` (or explicitly ruled `CONDITIONAL`) row in `MEASUREMENT_WEIGHTS`
      pins the file's exact 64-character SHA-256 digest.
    """
    if _LEGACY_RULING_KW in unexpected_kwargs:
        msg = f"legacy keyword {_LEGACY_RULING_KW!r} has been removed; pass structured ruling= instead"
        hint = "pass ruling={'by': '<decider>', 'date': 'YYYY-MM-DD', 'scope': '<repo_id>', 'licence_clause': '<clause>'}"
        raise MeasureWeightGate(
            f"{msg} (hint: {hint})",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "legacy_ruling_keyword_removed",
                "code": "legacy_ruling_keyword_removed",
                "message": msg,
                "hint": hint,
                "field": "ruling",
            },
        )
    if unexpected_kwargs:
        bad_keys = sorted(str(k) for k in unexpected_kwargs)
        msg = f"gate_measurement_weight() got unexpected keyword argument(s): {', '.join(bad_keys)}"
        hint = "valid keyword arguments are repo_id, revision, ruling, table, stems, today"
        raise MeasureWeightGate(
            f"{msg} (hint: {hint})",
            {
                "gate": "MEASURE_WEIGHT",
                "andon": "MeasureWeightGate",
                "clause": "unexpected_keyword_argument",
                "code": "unexpected_keyword_argument",
                "message": msg,
                "hint": hint,
                "unexpected_keywords": bad_keys,
            },
        )

    resolved_today, today_err = _inspect_today(today)
    if today_err is not None:
        msg, hint, extra = today_err
        ev = {
            "gate": "MEASURE_WEIGHT",
            "andon": "MeasureWeightGate",
            "clause": "invalid_conditional_ruling",
            "code": "invalid_conditional_ruling",
            "message": msg,
            "hint": hint,
        }
        ev.update(extra)
        raise MeasureWeightGate(f"{msg} (hint: {hint})", ev)
    today_iso = resolved_today.isoformat()

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
                "licence_age": licence_age_reading(stem_row, today=today_iso),
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
    validated_ruling = None
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
                    "licence_age": licence_age_reading(row, today=today_iso),
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
                    "licence_age": licence_age_reading(row, today=today_iso),
                },
            )

    if ruling is not None:
        validated_ruling = validate_ruling(ruling, today=resolved_today)

    for row in candidates:
        if (repo_id is not None and row.get("repo_id") != repo_id) or (
            revision is not None and row.get("revision") != revision
        ):
            continue
        if row.get("verdict") == "CONDITIONAL":
            if validated_ruling is None:
                raise MeasureWeightGate(
                    f"measurement weight {basename!r} ({row.get('repo_id')} @ "
                    f"{row.get('revision')}) is CONDITIONAL ({row.get('licence')}) and "
                    f"carries no structured ruling (missing fields: {', '.join(RULING_REQUIRED_FIELDS)})",
                    {
                        "gate": "MEASURE_WEIGHT",
                        "andon": "MeasureWeightGate",
                        "clause": "weight_conditional_unaccepted",
                        "code": "weight_conditional_unaccepted",
                        "message": (
                            f"CONDITIONAL weight {row.get('repo_id')!r} requires a structured ruling"
                        ),
                        "hint": (
                            f"pass ruling={{'by': '<decider>', 'date': 'YYYY-MM-DD', "
                            f"'scope': {row.get('repo_id')!r}, 'licence_clause': '<clause>'}}"
                        ),
                        "missing_fields": list(RULING_REQUIRED_FIELDS),
                        "repo_id": row.get("repo_id"),
                        "revision": row.get("revision"),
                        "filename": basename,
                        "sha256": digest,
                        "licence": row.get("licence"),
                        "licence_age": licence_age_reading(row, today=today),
                    },
                )
            if not _ruling_covers_row(validated_ruling, row):
                msg = (
                    f"ruling field 'scope' ({validated_ruling['scope']!r}) does not cover "
                    f"CONDITIONAL weight {row.get('repo_id')!r} ({row.get('revision')!r})"
                )
                hint = f"set ruling['scope'] to include {row.get('repo_id')!r}"
                raise MeasureWeightGate(
                    f"{msg} (hint: {hint})",
                    {
                        "gate": "MEASURE_WEIGHT",
                        "andon": "MeasureWeightGate",
                        "clause": "ruling_out_of_scope",
                        "code": "ruling_out_of_scope",
                        "message": msg,
                        "hint": hint,
                        "field": "scope",
                        "scope": validated_ruling["scope"],
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
        if (
            r.get("verdict") == "ALLOWED"
            or (
                r.get("verdict") == "CONDITIONAL"
                and validated_ruling is not None
                and _ruling_covers_row(validated_ruling, r)
            )
        )
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
        "ruling": dict(validated_ruling) if validated_ruling is not None else None,
        "licence_age": licence_age_reading(chosen, today=today_iso),
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
