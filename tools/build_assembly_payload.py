#!/usr/bin/env python
"""build_assembly_payload — the frames->VIDEO chain, built in-repo. S03 Task C.

    <venv-python> tools\\build_assembly_payload.py --uploads=<uploads.json> \\
        --out=<dir> [--fps=16] [--prefix=video/S03_assembly]

Builds the API-format graph the halt ruling (R2) proposed as the rescue for the r2v tier's
unreachable video slot:

    81 x LoadImage -> BatchImagesNode -> CreateVideo(fps=16) -> SaveVideo

**That 81-slot chain is the shape S03 FALSIFIED**, and it is kept above as the historical
description rather than as a route. S03 executed this chain at 8 slots and it failed at 81
with `BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'`, after
passing the round trip, Gate ROUTE and pre-flight with zero warnings. `build_cascade_payload`
is the supported route for a clip of any length; this builder is bounded at
`MEASURED_FLAT_SLOT_MAX` (8) until someone measures where the boundary actually is.

**A served template is a reference, never a route** — so this graph is built here, from the
node contracts re-measured with `get_node` on 2026-08-13, and it passes Gate ROUTE and both
Gate ASSEMBLY clauses in code before anything is submitted. Nothing here submits anything.

`--uploads` is the JSON written by the upload step: local frame filename -> the server's
content-addressed name. Frames are ordered by their LOCAL name, which is the frame order;
the server's names are content-addressed and sort into a meaningless order, and sorting by
them would assemble the clip's 81 frames in an arbitrary sequence while every count in every
gate still read correctly.

--------------------------------------------------------------------------------
Why the key SHAPE is now refused rather than sorted, and why a slot knows its frame

"Ordered by their LOCAL name" was true of the maps this pipeline happened to write and
false of the sort it relied on. Measured 2026-09-03: an 81-entry map keyed `0.png` ..
`80.png` built cleanly and recorded a frame order running `0.png, 1.png, 10.png, 11.png`
… `8.png, 80.png, 9.png` — `10.png` in slot 2 — with every gate green; and a 4-frame map
carrying one extra `reference.png` key absorbed it as a fifth frame, `n_frames: 5`, same
green verdict. Lexicographic sorting of unpadded names does exactly the shuffle the
docstring above says sorting by server name would do.

So `frame_order` refuses any key that is not `^[0-9]{5}\\.png$` and any gap in `0..n-1`:
the map either carries a total order this tool can read or it halts. And because no gate
downstream related a batch SLOT index to a FRAME index — `gate_batch_topology` checks slot
names, distinctness and class, never position — `gate_slot_frame_index` closes that: slot
`k` of a batch node must hold the upload name of frame `k`. Both helpers are used by
`build_cascade_payload.py` and, through it, by the arm that spends.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory; owner: the executor session. The uploads it references have **no delete endpoint**
on this API surface — they are content-addressed and inert unless a graph names them (the
E12 w2/w3 §7 convention).
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import assembly as AS  # noqa: E402
from armature_core import canon_census  # noqa: E402  - the subject census
#   (wave 22, F-27f76c43): this chain arms no Gate CANON, so the census is read
#   here for the RECORD rather than for a refusal about the prompt.
from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.

TOOL_VERSION = "S03.2"

#: The largest flat batch anyone has SEEN EXECUTE, and the andon's bound.
#:
#: S03 executed this chain at **8 slots** and it failed at **81** with
#: `BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'`. Those
#: are the two measurements that exist. **The boundary between 8 and 81 has never been
#: located**: no submission was made at 49, 50 or 51 slots, so `assembly.INFERRED_SLOT_CAP`
#: (50) is an inference from one error message and not a number this gate may refuse
#: against — a threshold read off a single error string is a placeholder shaped like
#: evidence. The cascade's `MAX_SLOTS_PER_NODE` (27) is not it either: that is the group
#: size the cascade chose, and a global constant must not govern a local feature.
#:
#: So the bound is the measurement, and the evidence dict says the boundary is unlocated,
#: so the day someone measures it this number moves WITH that measurement.
MEASURED_FLAT_SLOT_MAX = 8

#: `CreateVideo`'s measured input contract, re-measured with `get_node` on 2026-08-13 and
#: recorded verbatim in this tool's own payload record under `node_contracts_measured`.
#: The record stated it; nothing read it. See `gate_create_video_fps`.
CREATE_VIDEO_FPS_RANGE = (1.0, 120.0)

#: The only shape a frame key in an upload map may take. Zero padded to five digits, so a
#: lexicographic sort of the keys IS the numeric order — the property the ordering rule
#: assumed and never checked.
#: An upload map key: five zero-padded digits, optionally suffixed `.png`.
#:
#: The suffix is matched case-INSENSITIVELY (wave 8, F-d85dafd9, routed from
#: instruments-measure). This was the `.png` case family's last builders site and the
#: only member keyed on an upload KEY rather than a directory listing. Measured before
#: the widening: a map keyed `00000.PNG` refused with "4 key(s) that are not a
#: zero-padded frame name" — safe, but through the wrong clause, telling an operator
#: their keys are not zero-padded frame names when they are, while every consumer of the
#: same frames (`encode_control.py:126`, `invert_frames.py:70`) and both fetchers'
#: EXTRA andon (`fetch_run.verify_downloads`, carried here) read `.PNG` as a frame.
FRAME_KEY = re.compile(r"^[0-9]{5}(\.png)?$", re.IGNORECASE)


class SeedRegistrationError(ArmatureError):
    """The committed seed registration is not a list of seeds this tool can read.

    A refusal about the OPERAND an operator supplied, not about a graph, so it carries no
    gate of its own beyond the `PAYLOAD` id the builders' own operand refusals use. It
    defines no `__init__`: the base stores what it is passed (wave 16, rule 5).
    """


def canonical_payload_digest(graph):
    """The ONE derivation of a payload record's `payload_sha256`.

    Wave 20, F-dba1bcd8. `gate_saved_graph.route_facts` ties the two facts that admit a paid
    submission — the credit that pays a CONDITIONAL licence row, and the no-sampler
    assertion — to the graph they were asserted about, by comparing the record's declared
    `payload_sha256` against `sha256(json.dumps(api_graph, sort_keys=True,
    separators=(",", ":")))`. Measured by driving all nine builders' own `main()` on
    2026-09-05: FOUR wrote that digest and FIVE did not, so on the hosted partner tier that
    bills per submission (`build_r2v_payload`), on the one arm whose graph loads a
    CONDITIONAL component (`build_lora_arm_payload`), and on `build_t2v_payload`,
    `build_assembly_payload` and `build_cascade_payload`, `route_facts` returned
    `payload_sha256: None`, `source` read "the facts below are NOT tied to the graph being
    admitted", and the wave-18 tie clause `record_describes_a_different_graph` could not
    fire at all.

    **The input is the graph as an OBJECT, not the file.** Two of the five wrote a digest of
    the PRETTY-PRINTED file under their own key names (`build_t2v_payload`'s `graph.sha256`,
    `build_lora_arm_payload`'s `graph_sha256`), and renaming those would not have closed it:
    measured on a one-node graph, the canonical digest is `15ea11c72a720cbb…` and the file
    digest `163ef2eefe7f1985…`. Both are kept — the file digests still name the bytes on
    disk — but only this one answers "is this record about this graph".

    **Why this function lives here** rather than beside `payload_digests`, its reader:
    `gate_saved_graph` imports `read_seed_registration` from this module at module level, so
    a builder importing `gate_saved_graph` would close a cycle that breaks
    `import build_assembly_payload` outright. This module is the one eight of the nine
    builders and `gate_saved_graph` itself already import; `gate_saved_graph` imports this
    name too, so the record's digest and the gate's comparison are the SAME function object.
    """
    return hashlib.sha256(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---- SEAM 1 (wave 22): `single_path_segment`'s ONE home is `armature_core.parts`. It is
# ADOPTED BY IMPORT, never spelled a third time -- instruments-measure held two copies
# (`pack_pose_pack.py`, `resample_motion.py`) and SEAM 1 retired both. On the branch this
# was written on the import fell back to the `resample_motion` copy; wave-22 merge (coordinator, 2026-09-05)
# deleted that fallback, because on the merged tree it named a function that no longer
# exists and would have turned a missing home into a second, unrelated ImportError.
from armature_core.parts import single_path_segment       # noqa: E402

# `single_path_segment` above is IMPORTED, never defined here, and is re-exported to the
# four sibling builders that paste a free string into a written filename
# (`build_animate_payload`, `build_i2v_payload`, `build_camera_i2v_payload`,
# `build_t2v_payload`). Every one of them already imports from this module, so the ONE home
# is reached through ONE shim rather than five.


def read_seed_registration(path, *, flag="--seeds"):
    """The committed seed list, READ through clauses rather than indexed.

    Wave 16, F-0682bd00. Every tool in this tree that reads a committed registration read
    it the same two ways and neither was a clause. Six sites indexed the document bare
    (`json.load(fh)["seeds"]` in `build_animate_payload`, `build_camera_i2v_payload`,
    `build_i2v_payload`, `build_r2v_payload`, `build_t2v_payload` and `gate_saved_graph`),
    so a registration JSON with no `seeds` key raised a stdlib `KeyError` naming a key and
    nothing else; `build_lora_arm_payload` carried the DISARMING form,
    `registry.get("seeds") or []`, which turns the same file into an empty list and then
    reports the operator's seed as unregistered rather than the file as unreadable — a
    default that answers a question the reader never asked.

    Measured 2026-09-04 as a subprocess against `{"seeds": []}`: `build_t2v_payload`
    printed `BUILD_T2V_HALT {"error": "IndexError", "message": "list index out of range",
    "evidence": null}` and exited **1** — the code its own `__main__` block reserves for
    "this tool crashed" — for an operator supplying an emptied registration file.

    **Emptiness is not this reader's clause.** A caller that was given an explicit `--seed`
    is not defaulting to anything and has nothing to index; the caller that DOES default
    raises `no_seed_and_no_registration` before its `sorted(registry)[0]`.

    ⚠ **CORRECTION, 2026-09-05 (wave 22, F-87600738), with the measurement that overturned
    it.** The sentence above used to close: "…the clause `build_animate_payload`,
    `build_i2v_payload` and `build_camera_i2v_payload` already carried before their
    `sorted(registry)[0]`. One reader, one wording, every caller." It asserted a family
    property the tree did not hold. RE-MEASURED by grep across `tools/` on `e8263a3`: the
    string `no_seed_and_no_registration` occurred at exactly ONE site,
    `build_t2v_payload.py`. The three siblings the sentence named each raised
    `PayloadError(<message>)` with NO second argument, which under the wave-16 rule-5 base
    stores `None` — so the halt line printed `"evidence": null` and the refusal carried no
    `gate`, no `andon` and no `clause`. Confirmed by calling
    `build_animate_payload.build(...)` with `seed=None` and an empty registry:
    `PayloadError` raised, `evidence` None, `gate` None.

    Nor was it "one wording": the three say `--seeds-registry` and `build_t2v_payload` says
    `--seeds`, which is correct PER FLAG and is not what the sentence claimed. All four
    sites carry the typed clause now — each naming the flag it actually reads — so the
    census sees four, and the wording claim is narrowed to what is true: one clause word,
    each site naming its own flag.

    One implementation, eight callers — the same rule `gate_create_video_fps` above states.
    """
    ev = {"gate": "PAYLOAD", "andon": "seed_registration", "flag": flag,
          "path": os.path.abspath(path)}
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        raise SeedRegistrationError(
            f"{flag} {path!r} cannot be opened ({exc.__class__.__name__}: {exc}). The "
            f"committed registration is the list git timestamps ahead of the artifacts it "
            f"governs, and a seed that is not read off it is a number nobody can hold this "
            f"run to",
            dict(ev, clause="registration_missing", error=exc.__class__.__name__)) from exc
    except json.JSONDecodeError as exc:
        raise SeedRegistrationError(
            f"{flag} {path!r} is not readable JSON ({exc}). A registration this tool "
            f"cannot parse is not a registration it can check a seed against",
            dict(ev, clause="registration_unreadable", error=str(exc))) from exc
    if not isinstance(doc, dict):
        raise SeedRegistrationError(
            f"{flag} {path!r} is a {type(doc).__name__}, not a JSON object with a `seeds` "
            f"key. The registration's shape is part of what is committed",
            dict(ev, clause="registration_not_a_mapping", read_as=type(doc).__name__))
    if "seeds" not in doc:
        raise SeedRegistrationError(
            f"{flag} {path!r} declares no `seeds` key; it carries {sorted(doc)}. The bare "
            f"index this replaces raised a stdlib KeyError naming the key and nothing "
            f"else — no flag, no file, no receipt",
            dict(ev, clause="registration_no_seeds_key", keys=sorted(doc)))
    seeds = doc["seeds"]
    if not isinstance(seeds, list):
        raise SeedRegistrationError(
            f"{flag} {path!r} declares `seeds` as a {type(seeds).__name__}, not a list. A "
            f"membership test against a non-list is a question with an accidental answer",
            dict(ev, clause="registration_seeds_not_a_list",
                 read_as=type(seeds).__name__))
    # ---- ANDON, wave 18 (F-3f285caa). The clause above refuses a non-list on the ground
    # that "a membership test against a non-list is a question with an accidental answer",
    # and then the list was returned with NO clause on its ELEMENTS — so the membership test
    # stayed accidental one level down. Measured on the base tree by calling this reader on
    # committed-shape files, all ACCEPTED: `["2026081351","2026081352"]`, `[[2026081351]]`,
    # `[{"seed": 2026081351}]`, `[2026081351, null]`, `[True, False]`, `[1.5]`. All eight
    # committed registrations under `specs/*seeds.json` are lists of ints, so the five
    # clauses above hold over the real population today — this is the direction they do not
    # bound.
    #
    # The three consequences, measured at the callers:
    #   * a QUOTED registration makes `2026081351 in ['2026081351','2026081352']` False, so
    #     `build_r2v_payload.gate_seed_registered` and `build_lora_arm_payload.gate_s`
    #     refuse the operator's seed as UNREGISTERED while the defect is the file's shape —
    #     a refusal naming the wrong problem, the exact complaint this docstring makes about
    #     the disarming `registry.get("seeds") or []`.
    #   * a MIXED list makes `sorted(registry)[0]` — the documented default path in
    #     `build_animate_payload:301`, `build_i2v_payload:539` and
    #     `build_camera_i2v_payload:880` — raise `TypeError: '<' not supported between
    #     instances of 'NoneType' and 'int'`, an untyped exit-1 crash: the family this
    #     reader was created to end.
    #   * `1 in [True]` is True in CPython, so a BOOLEAN registration admits an
    #     unregistered number.
    #
    # `bool` is excluded explicitly because `isinstance(True, int)` is True: the two
    # spellings are indistinguishable to a check that does not ask, which is the same
    # reason `gate_saved_graph._same_value` guards it.
    #
    # No numeric RANGE is invented here. This module records no measured bound for a seed's
    # magnitude, and CLAUDE.md forbids a global constant governing a local feature; the
    # generator-side enums that ARE measured live in `route_gates.HOSTED_TIER_RULES`. The
    # clause bounds the TYPE the callers index and test membership against, which is what
    # the five clauses above already promised.
    offending = [{"index": i, "value": repr(v), "type": type(v).__name__}
                 for i, v in enumerate(seeds)
                 if isinstance(v, bool) or not isinstance(v, int)]
    if offending:
        raise SeedRegistrationError(
            f"{flag} {path!r} declares {len(offending)} of {len(seeds)} `seeds` entries "
            f"that are not integers: "
            + "; ".join(f"index {o['index']} is a {o['type']} ({o['value']})"
                        for o in offending[:5])
            + ". The callers index this list and test membership against it, so a quoted "
              "or boxed seed makes the operator's number read as UNREGISTERED and a mixed "
              "list makes `sorted(registry)[0]` raise a stdlib TypeError. A boolean is "
              "refused for the same reason `1 in [True]` is True",
            dict(ev, clause="registration_seed_is_not_an_integer",
                 n_seeds=len(seeds), offending=offending,
                 read_as=sorted({type(v).__name__ for v in seeds})))
    return seeds


def read_seed_registration_budget(path, *, flag="--seeds"):
    """Seeds plus the ceiling/allocation a submitter counts against.

    Wave 34, F-43868378. `read_seed_registration` returns only the seeds list — eight
    callers still need that shape. The sanctioned submitter cannot see prior spends from a
    graph builder, so the budget half lives here as a sibling reader: same open/parse/shape
    clauses for `seeds`, then named clauses for `ceiling.submissions` (int > 0) and
    `allocation` (non-empty mapping). Returns
    `{"seeds", "ceiling", "allocation", "path", "flag"}`.
    """
    seeds = read_seed_registration(path, flag=flag)
    ev = {"gate": "PAYLOAD", "andon": "seed_registration_budget", "flag": flag,
          "path": os.path.abspath(path)}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    ceiling = doc.get("ceiling")
    if not isinstance(ceiling, dict):
        raise SeedRegistrationError(
            f"{flag} {path!r} declares `ceiling` as a "
            f"{type(ceiling).__name__ if ceiling is not None else 'missing key'}, not an "
            f"object carrying `submissions`. The number a submission step counts against "
            f"sits beside `note`; without it the bound is prose again",
            dict(ev, clause="registration_no_ceiling",
                 read_as=type(ceiling).__name__ if ceiling is not None else None,
                 keys=sorted(doc)))
    submissions = ceiling.get("submissions")
    if not isinstance(submissions, int) or isinstance(submissions, bool) or submissions < 1:
        raise SeedRegistrationError(
            f"{flag} {path!r} declares `ceiling.submissions` as "
            f"{submissions!r} ({type(submissions).__name__}); a submission step needs a "
            f"positive integer bound",
            dict(ev, clause="registration_ceiling_submissions_not_a_positive_int",
                 submissions=submissions,
                 read_as=type(submissions).__name__))
    allocation = doc.get("allocation")
    if not isinstance(allocation, dict) or not allocation:
        raise SeedRegistrationError(
            f"{flag} {path!r} declares `allocation` as a "
            f"{type(allocation).__name__ if allocation is not None else 'missing key'}, "
            f"not a non-empty object. The per-seed rows are the other half of the bound",
            dict(ev, clause="registration_no_allocation",
                 read_as=type(allocation).__name__ if allocation is not None else None,
                 keys=sorted(doc)))
    return {"seeds": seeds, "ceiling": ceiling, "allocation": allocation,
            "path": os.path.abspath(path), "flag": flag,
            "submissions": int(submissions)}


#: Comfy Cloud OSS-on-cloud disclosure — licence map "Comfy Cloud" ToS row
#: (https://www.comfy.org/terms-of-service), fetched into docs/license-map.md.
#: Wave 34, F-d092c186. Distinct from build_r2v_payload.TIER_DISCLOSURE (Wan partner).
COMFY_CLOUD_OSS_DISCLOSURE = {
    "surface": "Comfy Cloud (OSS weights / core nodes — no partner API node)",
    "provider_terms": "https://www.comfy.org/terms-of-service",
    "output_ownership": (
        "Customer retains all right, title, and interest in and to Output "
        "(Comfy Cloud ToS; docs/license-map.md Comfy Cloud row)"),
    "ruling": (
        "Generation runs on Comfy Cloud per Claude.md; this route loads commercially-"
        "cleared OSS weights and core nodes only. Disclosure is required because assets "
        "leave the rig"),
    "obligations": [
        {"kind": "data_use",
         "text": ("uploaded Input (prompts, start frames, references, control packs) and "
                  "Output leave this rig for Comfy Cloud execution. Comfy's ToS states it "
                  "'will not use Input or Output to train generative AI'"),
         "applies_to": "every asset and prompt this submission uploads",
         "source": "Comfy Cloud ToS; docs/license-map.md Comfy Cloud row"},
        {"kind": "training_use",
         "text": ("training posture on this surface is Comfy's 'will not use Input or "
                  "Output to train generative AI' clause — not the Wan partner SIII.6 "
                  "training licence. Partner-tier routes print their own block"),
         "applies_to": "Input and Output on this OSS-on-cloud route",
         "source": "Comfy Cloud ToS; docs/license-map.md Comfy Cloud row"},
        {"kind": "ai_content_disclosure",
         "text": ("footage from this route is AI-generated. Publish with clear disclosure "
                  "where a venue or contract requires it; this build does not remind you "
                  "at publish time"),
         "applies_to": "published footage from this route",
         "source": "studio per-route disclosure ruling (Claude.md); Comfy Cloud ToS"},
        {"kind": "watermark",
         "text": ("no watermark is promised by this OSS graph. If a mark or label is "
                  "present on returned frames, inspect before publishing rather than "
                  "assuming the cloud left none"),
         "applies_to": "the footage this submission returns",
         "source": "Comfy Cloud ToS; docs/license-map.md Comfy Cloud row"},
    ],
}

#: Shorter block for assembly/cascade — frames leave for CreateVideo/SaveVideo packing.
ASSEMBLY_LEAVE_DISCLOSURE = {
    "surface": "Comfy Cloud CreateVideo/SaveVideo packing (no sampler / no partner node)",
    "provider_terms": "https://www.comfy.org/terms-of-service",
    "ruling": (
        "This chain authors no generation sampler; frames still leave the rig for "
        "CreateVideo/SaveVideo on Comfy Cloud"),
    "obligations": [
        {"kind": "data_use",
         "text": ("uploaded frames leave this rig for CreateVideo/SaveVideo on Comfy "
                  "Cloud. Ordinary cloud compute may bill; no partner-credit node rides "
                  "this allowlist"),
         "applies_to": "every frame named by --uploads",
         "source": "Comfy Cloud ToS; docs/license-map.md Comfy Cloud row"},
    ],
}


def comfy_cloud_oss_disclosure(route_verdict=None):
    """Disclosure block for OSS-on-cloud generation builders (wave 34, F-d092c186)."""
    block = {
        "route": COMFY_CLOUD_OSS_DISCLOSURE["surface"],
        "provider_terms": COMFY_CLOUD_OSS_DISCLOSURE["provider_terms"],
        "output_ownership": COMFY_CLOUD_OSS_DISCLOSURE["output_ownership"],
        "ruling": COMFY_CLOUD_OSS_DISCLOSURE["ruling"],
        "obligations": [dict(o) for o in COMFY_CLOUD_OSS_DISCLOSURE["obligations"]],
        "route_verdict": route_verdict,
        "read_from": ("build_assembly_payload.COMFY_CLOUD_OSS_DISCLOSURE, mirrored from "
                      "docs/license-map.md's Comfy Cloud ToS row"),
        "checked_by": ("nothing in code gates publication duties; they are DISCLOSED at "
                       "the moment the spend is authored"),
    }
    return block


def assembly_leave_disclosure(route_verdict=None):
    """Shorter disclosure for assembly/cascade packing chains (wave 34, F-d092c186)."""
    return {
        "route": ASSEMBLY_LEAVE_DISCLOSURE["surface"],
        "provider_terms": ASSEMBLY_LEAVE_DISCLOSURE["provider_terms"],
        "ruling": ASSEMBLY_LEAVE_DISCLOSURE["ruling"],
        "obligations": [dict(o) for o in ASSEMBLY_LEAVE_DISCLOSURE["obligations"]],
        "route_verdict": route_verdict,
        "read_from": "build_assembly_payload.ASSEMBLY_LEAVE_DISCLOSURE",
        "checked_by": ("frames leave for CreateVideo/SaveVideo; disclosed rather than "
                       "gated"),
    }


def fetch_recipe(*, node_map, video_nodes=(), root_hint=None, taps=None):
    """Fetch recipe keys a payload record carries for fetch_run --record (F-dc84b444).

    `node_map` is {node_id_str: subdir}. `video_nodes` is an iterable of node id strings
    whose files land beside the run. `taps` is an optional list of
    {node, class_type, subdir|None} rows for readers that want class beside id.
    """
    nm = {str(k): str(v) for k, v in dict(node_map or {}).items()}
    vn = [str(x) for x in (video_nodes or ())]
    tap_rows = list(taps) if taps is not None else [
        {"node": nid, "class_type": "SaveImage", "subdir": sub} for nid, sub in nm.items()
    ] + [
        {"node": nid, "class_type": "SaveVideo", "subdir": None} for nid in vn
    ]
    return {
        "fetch": {
            "node_map": nm,
            "video_nodes": vn,
            "root_hint": root_hint,
            # `none` = explicitly empty (no SaveImage taps), not "fall back to E02".
            "node_map_flag": (",".join(f"{k}={v}" for k, v in sorted(nm.items()))
                              if nm else "none"),
            "video_nodes_flag": (",".join(vn) if vn else "none"),
        },
        "taps": tap_rows,
        "node_map": nm,
        "video_nodes": vn,
    }


def gate_output_not_overwritten(paths, out, overwrite, exc, gate="PAYLOAD"):
    """Gate <gate> · ANDON — a rebuild does not silently replace an earlier build's artefacts.

    Wave 28, F-5fd16451, and instruments' panel CRITICAL `F-8b7f48a8` is the same mechanism at
    a different anchor. MEASURED in this worktree before the fix: `build_assembly_payload.main`
    called twice into ONE `--out` with DIFFERENT upload maps replaced BOTH artefacts
    (`S03-assembly.api.json` sha256 2c986d17… -> b3e8f53f…, `S03-assembly-payload-record.json`
    f61a47b7… -> 80ad650f…) and the second run's stdout was BYTE-IDENTICAL to the first — nine
    lines, none naming an existing file, none carrying a digest or any other value that differs
    between two builds, so a scrollback of two runs cannot tell them apart. The mechanism is a
    family, censused across the nine builders: `os.path.exists` / `os.path.isfile` appeared ZERO
    times in seven of them and the three hits in the other two were INPUT checks; no builder
    checked its output path before `open(..., "w")`. `build_assembly_payload` and
    `build_cascade_payload` write FIXED filenames, so a rebuild always lands on the prior one.

    What that costs: a graph is submitted, a later build into the same `--out` — a re-run with
    a corrected upload map, a second arm, a repeated command from history — replaces the record
    whose `payload_sha256` was the only tie between the submitted graph and its inputs, and
    nothing said so. This repo's law is that a recipe which does not reproduce its output is not
    a recipe. The neighbouring invariant already lives on these paths ("a refuse must leave no
    output directory"); the write-over-an-existing-record case had no clause.

    **ONE shape across two domains, agreed in the relay before either edit**
    (`wave-28/seams-inbox.md`: instruments @ 13:20, the coordinator's ruling @ 13:2x). The flag
    is `--overwrite` (`store_true`, default off); the clause word is `output_already_exists`;
    the sentence is the one below with a subject slot; the evidence carries
    `{clause, out, already_present, planned}` — plus, here, the digest of each artefact that
    would be replaced, which is what makes a builders halt actionable. On `--overwrite` there is
    no refusal and the run SAYS SO, on stdout and in the record, under two keys spelled the same
    way in both domains: `out_dir_pre_existed` and `overwrote`.

    The helper lives HERE rather than in `armature_core.parts` for the reason the coordinator
    ruled: `parts.py` is core-solvers' file and carries no finding for this helper, so a helper
    there would be an unrequested edit to another domain's module. This module is already this
    domain's shared home — `gate_saved_graph` and eight of the nine builders import
    `read_seed_registration` / `canonical_payload_digest` from it — so the builders reach ONE
    implementation through the import they already have. instruments spells the same words
    locally in its three renderers; nobody spells a fourth.

    `exc` is the caller's own family class and `gate` its own gate id, exactly as
    `parts.single_path_segment` takes them — a shared refusal must not smuggle a foreign andon
    into a tool's halt line.

    Returns the receipt either way, so the record states what was found rather than being silent
    on a fresh directory: a measured "nothing was there", not an absence.
    """
    present = []
    for path in paths:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                present.append({"path": os.path.abspath(path),
                                "name": os.path.basename(path),
                                "sha256": hashlib.sha256(fh.read()).hexdigest(),
                                "bytes": os.path.getsize(path)})
    ev = {"gate": gate, "andon": exc.__name__, "out": os.path.abspath(out),
          "already_present": [p["name"] for p in present],
          "digests": {p["name"]: p["sha256"] for p in present},
          "planned": len(list(paths)),
          "out_dir_pre_existed": bool(present), "overwrote": [], "flag": "--overwrite"}
    if present and not overwrite:
        # Spelled as an ASSIGNMENT, not as `dict(ev, clause=...)`: `_census_nodes.
        # clause_literals` reads a dict-literal key or `ev["clause"] = ...` and nothing
        # else, and a keyword to `dict()` is invisible to it at 64 sites tree-wide (recorded
        # at the wave-25 merge). A new word spelled invisibly is a word no census can pin.
        ev["clause"] = "output_already_exists"
        subject = ", ".join(f"{p['name']} (sha256 {p['sha256'][:12]}…)" for p in present)
        raise exc(
            f"{subject}: already on disk from an earlier run; this run would replace what is there. "
            f"Pass --overwrite to replace it, or point --out at a directory of its own. The "
            f"payload record is the only tie between a submitted graph and the inputs it was "
            f"built from — its `payload_sha256` is what `gate_saved_graph.route_facts` "
            f"compares — so replacing one silently leaves a receipt that describes a graph "
            f"nobody can reproduce",
            dict(ev))
    if present:
        ev["overwrote"] = [p["name"] for p in present]
        ev["verdict"] = (
            f"--overwrite: {len(present)} artefact(s) from an earlier build were replaced "
            + "; ".join(f"{p['name']} was sha256 {p['sha256'][:12]}…" for p in present))
    else:
        ev["verdict"] = (f"{len(list(paths))} artefact(s) planned, none of them already "
                         f"present in {os.path.abspath(out)}")
    return ev


def _wrap_disclosure_line(line, width=78):
    """Wrap one disclosure line on ``; `` / `` - `` (else space) so col 80 never mid-words."""
    if len(line) <= width:
        return [line]
    hang = "    "
    out = []
    remaining = line
    while len(remaining) > width:
        window = remaining[: width + 1]
        break_at = max(window.rfind("; "), window.rfind(" - "))
        if break_at < width // 3:
            break_at = remaining.rfind(" ", 0, width)
        if break_at <= 0:
            break_at = width
        if remaining.startswith(hang) is False and break_at < len(remaining):
            if remaining[break_at: break_at + 3] == " - ":
                cut = break_at + 3
            elif remaining[break_at: break_at + 2] == "; ":
                cut = break_at + 2
            elif remaining[break_at] == " ":
                cut = break_at + 1
            else:
                cut = break_at
        else:
            cut = break_at
        out.append(remaining[:cut].rstrip())
        remaining = hang + remaining[cut:].lstrip()
    if remaining:
        out.append(remaining)
    return out


def disclosure_lines(block):
    """The operator-facing lines for a per-route disclosure block, one per obligation.

    Wave 28, F-2dcaf53a — lifted here from `build_lora_arm_payload`, where it was written in
    wave 14 (F-92f67091) for the E14 arm's ONE credits line. `build_r2v_payload` authors the
    only hosted-partner-tier spend in this repo and had no disclosure surface at all: its nine
    printed lines named no data-use posture, no AI-content disclosure duty and no watermark
    policy, and its payload record carried no disclosure key. That is the gap CLAUDE.md's
    per-route disclosure ruling exists to close, on the route the ruling was born on.

    So the renderer has ONE home and two callers, rather than a second spelling of a shape that
    already worked. Each obligation names its own `kind`, which becomes the line's label, so the
    E14 arm still prints `CREDIT OBLIGATION:` and the E13 route prints the words that belong to
    ITS tier. It returns lines rather than printing them so a test can read the words back
    without a capture — the property the original had and keeps.

    Wave 32, F-fd2be19e — long obligation strings wrap on ``; `` / `` - `` at ≤78 columns
    rather than mid-word at the terminal edge.
    """
    out = [f"  ROUTE: {block.get('route_verdict')}"]
    obligations = block.get("obligations") or []
    if not obligations:
        # The E14 arm's own wording, kept verbatim — a measured "none", not a silence.
        reason = block.get("empty_reason")
        if reason is None:
            reason = (f"the licence map rules no CONDITIONAL component in this arm's graph "
                      f"({(block.get('credit_obligation') or {}).get('text')})")
        out.extend(_wrap_disclosure_line(
            f"  {block.get('empty_label', 'CREDIT OBLIGATION')}: none - {reason}"))
        return out
    for ob in obligations:
        kind = str(ob.get("kind") or "obligation")
        if kind == "credit":
            raw = (
                f"  CREDIT OBLIGATION: this arm credits {ob['creditor']} - {ob['text']} "
                f"[{ob['kind']}; {ob['applies_to']}; source {ob['source']}; component "
                f"{ob['component']}]")
        else:
            raw = (
                f"  {kind.upper().replace('_', ' ')}: {ob['text']} "
                f"[{ob['applies_to']}; source {ob['source']}]")
        out.extend(_wrap_disclosure_line(raw))
    return out


def route_report_lines(gate_route):
    """The two Gate ROUTE lines the assembly builders print, saying what was JUDGED.

    Wave 28, F-8601de91. Both lines were raw Python reprs that named nothing they were about.
    MEASURED as printed output from a real run in this worktree before the fix:

        route components 0  seeds 0  latents 0
        frame legality   [True]

    The first is three zeros with no sentence saying whether zero means the gate examined an
    empty set — which it did; this chain loads no weights and carries no sampler — or found
    nothing to examine, which is the vacuous state `route_gates.verify` exists to refuse. The
    second is a bare list of booleans with no width, height or frame count beside it, so a
    reader cannot tell what shape was judged legal or how many latents were examined.

    The same information is rendered well one file over, on the paid route:
    `build_r2v_payload` prints `gate L (hosted)  720P 16:9 5s -> legal True`, naming the
    values judged. These are the graphs whose frames feed the paid A2 arm's reference video,
    so the reader of these lines is deciding whether to spend on what they describe.

    The wording precedent for the zero clause is this family's own `gate_pair_note` in
    `build_r2v_payload`'s record — "recorded as n/a, not skipped".

    Returns lines rather than printing them, so a test reads the words back without a
    capture — the shape `disclosure_lines` above already uses.
    """
    n_components = len(gate_route["components"])
    n_seeds = len(gate_route["seeds"])
    n_latents = len(gate_route["latents"])
    # Wave 32, F-8d31935f — same 17-col gutter as build_r2v_payload's `route` row.
    line = (f"route            components {n_components}  seeds {n_seeds}  "
            f"latents {n_latents}")
    if not (n_components or n_seeds or n_latents):
        line += ("  (each an EMPTY SET examined, not a check skipped: this chain loads no "
                 "weights, carries no sampler and pins no latent)")
    out = [line]
    rows = gate_route.get("frame_legality") or []
    if not rows:
        out.append("frame legality   no frame was checkable on this graph")
        return out
    for row in rows:
        out.append(
            f"frame legality   {row.get('width')}x{row.get('height')}x{row.get('length')} "
            f"({row.get('source', 'graph')}, {row.get('family')} "
            f"{row.get('frame_form')}) -> "
            + ("legal" if row.get("legal")
               else f"ILLEGAL: {'; '.join(row.get('problems') or [])}"))
    return out


def gate_create_video_fps(fps):
    """Gate ROUTE - ANDON: `CreateVideo.fps` is inside the contract the record states.

    `CreateVideo` takes `fps` as a FLOAT bounded 1..120 (measured with `get_node`,
    2026-08-13, and written into every record this family emits as
    `node_contracts_measured.CreateVideo`). Until wave 10 the flag was written straight
    into the node with no clause. Measured 2026-09-04 as subprocesses on an 81-entry padded
    map: `--fps=0`, `--fps=-5` and `--fps=999` each built the graph, passed all five gates
    including Gate ROUTE, and printed `BUILD_CASCADE_OK`. Contrast `--group` in the same
    file, which IS bounded in both directions, and `build_r2v_payload`'s hosted enums,
    where `--duration=99` raises. A tool that records a generator constraint and does not
    enforce it is exactly what CLAUDE.md's "generation frames must be generator-legal" rule
    exists to prevent: the clip is either rejected at submission after the upload round
    trip, or accepted at a rate the record then names as fact.

    **Non-finite first.** `nan > 120` and `nan < 1` are both False, so a range test written
    the obvious way admits NaN in both directions and the andon would report a legal rate
    for a number that is not one. It is refused by name, with the value in the evidence.

    One implementation, five callers: `build_animate_payload`, `build_assembly_payload`,
    `build_camera_i2v_payload`, `build_cascade_payload` and `build_i2v_payload` are every
    builder in the tree that takes a `--fps` flag and writes it into a `CreateVideo` node.
    They import this function; none of them carries a copy.
    """
    lo, hi = CREATE_VIDEO_FPS_RANGE
    ev = {"gate": "ROUTE", "andon": "CreateVideoFps", "clause": "create_video_fps",
          "fps": None, "range": [lo, hi],
          "contract": ("CreateVideo: images IMAGE + fps FLOAT (1-120, default 30), "
                       "optional audio and bit_depth INT (8-10) -> VIDEO; measured with "
                       "get_node 2026-08-13")}
    try:
        value = float(fps)
    except (TypeError, ValueError):
        raise RG.RouteGate(
            f"CreateVideo.fps {fps!r} is not a number; the node declares fps as a FLOAT "
            f"bounded {lo}-{hi} and this tool's own record states that contract",
            dict(ev, fps=repr(fps))) from None
    ev["fps"] = value
    if not math.isfinite(value):
        raise RG.RouteGate(
            f"CreateVideo.fps is {value}, which is not a finite number. A range test "
            f"admits it in BOTH directions ({value} > {hi} and {value} < {lo} are both "
            f"False), so the verdict would have been PASS on a rate that is not one", ev)
    if not (lo <= value <= hi):
        raise RG.RouteGate(
            f"CreateVideo.fps {value} is outside the node's measured contract {lo}-{hi}. "
            f"A clip assembled at an illegal frame rate is either rejected at submission "
            f"after the upload round trip, or accepted at a rate this record then names "
            f"as fact", ev)
    ev["verdict"] = f"fps {value} is inside CreateVideo's measured contract {lo}-{hi}"
    return ev


def gate_flat_slot_ceiling(graph, batch_id):
    """Gate FLAT_SLOT_CEILING - ANDON - the flat batch is no wider than anyone has run.

    Wave 10 (routed seed). Both cascade builders call `assembly.gate_slot_ceiling`; the
    flat path called no ceiling clause at all, so the one builder whose shape is a SINGLE
    batch node - the shape S03 watched pass pre-flight and die at execution - was the one
    with nothing bounding its width. Pre-flight cannot see this; it is checked here, in the
    tool that authors the graph, before any submission.

    It does NOT read the cascade's `MAX_SLOTS_PER_NODE`: that constant is the cascade's
    group size, and a global constant must not govern a local feature. It reads
    `MEASURED_FLAT_SLOT_MAX`, whose docstring names the run that measured it and states
    that the boundary between 8 and 81 is unlocated. `boundary_located: false` rides every
    verdict for the same reason.
    """
    node = (graph or {}).get(str(batch_id)) or {}
    inputs = node.get("inputs") or {}
    slots = len([k for k in inputs if k.startswith("images.image")])
    if not slots and isinstance(inputs.get("images"), list):
        slots = len(inputs["images"])
    ev = {"gate": "FLAT_SLOT_CEILING", "andon": "AssemblyGate",
          "batch_node": str(batch_id), "slots": slots,
          "measured_max": int(MEASURED_FLAT_SLOT_MAX), "measured_by": "S03",
          "inferred_cap": int(AS.INFERRED_SLOT_CAP), "boundary_located": False}
    if slots > MEASURED_FLAT_SLOT_MAX:
        ev["clause"] = "flat_slot_ceiling_exceeded"
        raise AS.AssemblyGate(
            f"the flat chain's batch node {batch_id} carries {slots} slot(s) and the "
            f"largest flat batch anyone has SEEN EXECUTE is "
            f"{MEASURED_FLAT_SLOT_MAX} (S03). The same chain failed at execution at 81 "
            f"with `images.image50` unexpected, AFTER passing the round trip, Gate ROUTE "
            f"and pre-flight with zero warnings - so nothing downstream would refuse this "
            f"graph and the credits would be spent. The boundary between the two "
            f"measurements has never been located (INFERRED_SLOT_CAP={AS.INFERRED_SLOT_CAP} "
            f"is read off one error message, not measured). Use "
            f"`build_cascade_payload.py`, which batches the batches and is the supported "
            f"route for a clip of any length", ev)
    ev["verdict"] = (f"the flat batch carries {slots} slot(s), within the "
                     f"{MEASURED_FLAT_SLOT_MAX} anyone has seen execute (S03); the "
                     f"boundary above it is NOT located")
    return ev


def frame_order(uploads):
    """The clip's local frame names in temporal order, or raise saying which key broke it.

    Two clauses, each for a failure that is silent in the other's presence:

    * a key that is not `NNNNN.png` — unpadded names sort lexicographically, so `10.png`
      lands in slot 2, and a key that is not a frame at all (`reference.png`) is absorbed
      as an extra frame and lengthens the clip;
    * a gap in `0..n-1` — every key well formed, the count reading right, and every frame
      after the hole off by one.

    Both were measured on this tool on 2026-09-03 producing a clean topology verdict.
    """
    keys = list(uploads)
    malformed = sorted(k for k in keys if not FRAME_KEY.match(str(k)))
    ev = {"gate": "ASSEMBLY", "andon": "AssemblyGate",
          "n_keys": len(keys), "malformed": malformed}
    if malformed:
        ev["clause"] = "frame_key_is_not_a_frame_name"
        raise AS.AssemblyGate(
            f"the upload map carries {len(malformed)} key(s) that are not a zero-padded "
            f"frame name — {malformed[:8]}{' …' if len(malformed) > 8 else ''}. Frame "
            f"order is taken from a sort of these keys, and an unpadded name sorts "
            f"lexicographically (10.png before 2.png) while a key that is not a frame at "
            f"all is absorbed as one. Both shuffle or lengthen the clip with every count "
            f"in every gate still reading right. Keys must match 00000..NNNNN or 00000.png..NNNNN.png",
            ev)
    # Wave-3 merge (coordinator, 2026-09-04): every upload map on this rig — eleven E02/E03
    # files — is keyed by the bare zero-padded index (`00000`), while the cascade route keys
    # its maps `00000.png`. The defect this gate exists for is UNPADDED names sorting
    # lexicographically; the five zero-padded digits catch that in either shape, so both are
    # accepted — but one map must use one shape, because `00000` sorts before `00000.png`
    # and a mixed map has no single order to check.
    #
    # Each key's suffix VERBATIM, not normalised. Widening the case above must not reach
    # this line: the invariant here is SORT ORDER, and '.PNG' sorts before '.png' in ASCII,
    # so a map mixing the two cases genuinely has no single order and must still refuse —
    # through the mixed-shape clause below, which is the sentence that describes it. Taking
    # the suffix verbatim also keeps `want` reconstructing the operator's own key spelling.
    suffixes = {str(k)[5:] for k in keys}
    if len(suffixes) > 1:
        # Written onto `ev` rather than merged with `dict(ev, ...)` at the raise (wave 25,
        # F-d30bb5fb): `test_gates._evidence_keys` follows a bare Name to its literal AND
        # collects the subscript writes above the raise, and cannot do either through a
        # `dict(ev, …)` call — so the merged form hid this refusal's whole key set.
        ev["clause"] = "frame_key_shapes_are_mixed"
        ev["suffixes"] = sorted(suffixes)
        raise AS.AssemblyGate(
            f"the upload map mixes frame-key shapes {sorted(suffixes)!r} (bare 00000, "
            f".png-suffixed, or a differently-CASED suffix); a mixed map has no single "
            f"sort order, and '.PNG' sorts before '.png'. Use one shape throughout",
            # `dict(ev, ...)` rather than `{**ev, ...}` (wave 25, F-d30bb5fb): the two are
            # the same object at runtime and NOT the same to the census —
            # `test_gates._evidence_keys` reads a `**spread` as AUGMENTED and cannot prove
            # the triple is present, so this one site was the only refusal in the function
            # the walk could not judge.
            ev)
    suffix = next(iter(suffixes)) if suffixes else ""
    ordered = sorted(keys)
    want = [f"{i:05d}{suffix}" for i in range(len(keys))]
    missing = [w for w in want if w not in uploads]
    ev["missing"] = missing
    if ordered != want:
        ev["clause"] = "frame_indices_have_a_hole"
        raise AS.AssemblyGate(
            f"the upload map's frame indices are not 0..{len(keys) - 1} with no gaps: "
            f"missing {missing[:8]}{' …' if len(missing) > 8 else ''}. A hole leaves every "
            f"frame after it off by one, and the count still reads right",
            ev)
    return ordered


def frame_source_ids(names, first_image_id):
    """The LoadImage node id holding each frame, in frame order.

    P3's other half: the shared topology gate is being taught to take these and compare
    slot k to frame k. Supplied by every caller here regardless of whether the gate it is
    handed to declares a parameter for them yet.
    """
    return [str(int(first_image_id) + i) for i in range(len(names))]


def gate_slot_frame_index(graph, names, slot_plan, first_image_id):
    """Gate ASSEMBLY · ANDON — batch slot k holds the upload name of the frame at k.

    `slot_plan` is `[(batch_node_id, first_frame_index, stop_frame_index), …]` in group
    order — the `(start, stop)` spans `cascade_plan` already produced, which every caller
    holds. Slot `k` of that node must resolve to a `LoadImage` carrying
    `names[first_frame_index + k]`, for every k in the span. The flat chain passes one
    entry; the cascade passes one per group.

    **The andon is on the direction the invariant does not bound.** `gate_batch_topology`
    and `gate_cascade_topology` check slot NAMES, source DISTINCTNESS and source CLASS, and
    (in the cascade) that the GROUP nodes appear in order. None of them relates a slot
    index to a frame index, so two slots swapped inside a batch leaves every count, every
    name and every group order correct and the clip out of sequence — the same defect
    `fetch_t2v_run.py` exists to catch on the way back, with no equivalent on the way out.

    **The population is the PLAN, and that is wave 6's correction.** Until 2026-09-04 the
    loop ran over `[k for k in inputs if k.startswith("images.image")]` — whatever dotted
    keys HAPPENED to exist on the node — while the verdict was built from `len(names)`, a
    number describing the clip rather than the inspection. Measured on a 6-frame assembly
    graph: the batch replaced by a bare `images` list PASSED with "6 frame(s) checked"
    having inspected zero slots; the tail dropped so only `image0..2` survived PASSED with
    the same verdict having inspected three; the batch node REMOVED from the graph
    entirely PASSED having inspected nothing, because `graph.get(str(nid)) or {}` turns an
    absent node into an empty inputs dict and an empty loop. A contiguous truncation could
    not fire it at any length, because dropping N keys also shortened the loop by N. The
    only missing-slot shape that fired it was a HOLE. All three vacuous shapes are caught
    upstream by `gate_batch_topology`, which runs first at every production call site
    today — but this gate is exported for standalone use, and a verdict naming a property
    no code checked is this repo's named worst class.
    """
    ev = {"gate": "ASSEMBLY_slot_frame_index", "andon": "slot_frame_index",
          "n_frames": len(names), "first_image_id": int(first_image_id),
          "slot_plan": [[str(nid), int(start), int(stop)] for nid, start, stop in slot_plan]}

    # ---- COVERAGE, wave 8 (F-ad45bc42). The population came from the CALLER's plan and no
    # clause required that plan to cover the clip, so the gate returned a PASS verdict
    # having inspected any number of slots INCLUDING ZERO — and the verdict string printed
    # both numbers side by side with nothing comparing them. Measured 2026-09-04 on the
    # real 81-frame cascade graph from `build_cascade_payload.build(names, fps=16.0,
    # group_size=AS.GROUP_SIZE)` (3 group nodes): the full plan returned "…81 slot(s)
    # inspected against a clip of 81 frame(s)"; `slot_plan=[]` returned "every slot across
    # 0 batch node(s) holds the upload name of its own frame index, 0 slot(s) inspected
    # against a clip of 81 frame(s)"; a ONE-GROUP plan returned the same green sentence at
    # 27 of 81; and a plan ONE GROUP SHORT — the shape an un-strict `zip` produces —
    # returned it at 54 of 81. No clause fired in any of the three. Both production call
    # sites build the plan through a `zip` (`build_cascade_payload.py:163`,
    # `build_r2v_payload.py:254`), which truncates to the shorter of `cascade_plan(...)` and
    # the group-id list rather than raising; both pass `strict=True` now, and this clause is
    # the andon that does not depend on them doing so.
    covered, overlapping, gaps = set(), set(), []
    cursor = 0
    for nid, start, stop in slot_plan:
        start, stop = int(start), int(stop)
        if stop <= start:
            gaps.append(f"node {nid} is planned an empty or reversed span [{start}, {stop})")
        if start != cursor:
            gaps.append(f"node {nid}'s span starts at {start}, and the plan's previous "
                        f"span ended at {cursor}; the plan is not contiguous")
        for frame in range(start, stop):
            (overlapping if frame in covered else covered).add(frame)
        cursor = max(cursor, stop)
    missing = sorted(set(range(len(names))) - covered)
    outside = sorted(f for f in covered if f >= len(names))
    if gaps or missing or overlapping or outside:
        ev.update({"frames_planned": len(covered), "frames_in_clip": len(names),
                   "frames_never_planned": missing[:12],
                   "frames_planned_twice": sorted(overlapping)[:12],
                   "frames_planned_past_the_clip": outside[:12],
                   "coverage_problems": gaps})
        ev["clause"] = "slot_plan_does_not_cover_the_clip"
        raise AS.AssemblyGate(
            f"the slot plan does not cover the clip: {len(covered)} of {len(names)} "
            f"frame(s) are planned onto a batch node"
            + (f", {len(missing)} never ({missing[:6]}…)" if missing else "")
            + (f", {len(overlapping)} twice" if overlapping else "")
            + (f", {len(outside)} past the end of the clip" if outside else "")
            + ("; " + "; ".join(gaps[:4]) if gaps else "")
            + ". A gate whose population is the caller's plan reports what it inspected, "
              "not what the clip needed, and a swap inside an unplanned group ships as an "
              "out-of-order clip", ev)

    problems, inspected = [], 0
    for nid, start, stop in slot_plan:
        span = int(stop) - int(start)
        node = graph.get(str(nid))
        if node is None:
            problems.append(f"node {nid} is not in the graph at all, so its {span} slot(s) "
                            f"were never inspected — an absent node used to read as an "
                            f"empty loop and pass")
            continue
        if node.get("class_type") != "BatchImagesNode":
            problems.append(f"node {nid} is a {node.get('class_type')!r}, not a "
                            f"BatchImagesNode; there are no slots on it to inspect")
            continue
        inputs = node.get("inputs") or {}
        want_keys = {f"images.image{k}" for k in range(span)}
        got_keys = {k for k in inputs if k == "images" or k.startswith("images.image")}
        if got_keys != want_keys:
            problems.append(
                f"node {nid} carries dotted keys {sorted(got_keys)}, and the plan puts "
                f"{span} frame(s) ({sorted(want_keys)}) on it. A bare `images` list or a "
                f"truncated tail used to SHORTEN the loop rather than fail it")
            continue
        for k in range(span):
            frame = int(start) + k
            inspected += 1
            link = inputs.get(f"images.image{k}")
            src = str(link[0]) if isinstance(link, list) and len(link) == 2 else None
            loader = graph.get(src) if src else None
            got = (loader.get("inputs") or {}).get("image") if loader else None
            want = names[frame] if frame < len(names) else None
            if got != want:
                problems.append(
                    f"node {nid} slot {k} resolves to {got!r} via {src!r}; frame {frame} "
                    f"of the clip is {want!r}")
    ev["slots_inspected"] = inspected
    ev["frames_in_clip"] = len(names)
    if inspected != len(names):
        problems.append(f"{inspected} slot(s) were inspected against a clip of "
                        f"{len(names)} frame(s); the two numbers are the gate's whole "
                        f"claim and they must be the same number")
    if problems:
        ev["problems"] = problems
        ev["clause"] = "slot_does_not_hold_its_frame"
        raise AS.AssemblyGate(
            "a batch slot does not hold the frame the clip's order puts there: "
            + "; ".join(problems[:6]) + (" …" if len(problems) > 6 else ""),
            ev)
    ev["verdict"] = (f"every slot across {len(slot_plan)} batch node(s) holds the upload "
                     f"name of its own frame index, {inspected} slot(s) inspected against "
                     f"a clip of {len(names)} frame(s)")
    return ev

#: Node ids. Kept away from 1..99 so the graph reads as its own thing beside E02's, which
#: used 200+ for its LoadImages and 300/301 for its batch and probe.
FIRST_IMAGE_ID = 200
BATCH_ID = 400
VIDEO_ID = 401
SAVE_ID = 402

#: The frame the uploaded clip actually is — 1024x576, 81 frames, measured off the PNGs
#: rather than carried from a spec. Supplied to Gate L so the clause is decided rather than
#: INDETERMINATE; see the report for what that clause does and does not prove here.
WIDTH, HEIGHT = 1024, 576


def build(names, fps=16.0, prefix="video/S03_assembly"):
    """The API-format graph. `names` is the server-side upload name per frame, IN ORDER."""
    # The gate lives inside the function that emits the node, so an in-process caller
    # cannot route around it the way a check in `main` would allow.
    gate_create_video_fps(fps)
    wf = {}
    batch_inputs = {}
    for i, name in enumerate(names):
        nid = str(FIRST_IMAGE_ID + i)
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
        batch_inputs[f"images.image{i}"] = [nid, 0]
    wf[str(BATCH_ID)] = {"class_type": "BatchImagesNode", "inputs": batch_inputs}
    wf[str(VIDEO_ID)] = {"class_type": "CreateVideo", "inputs": {
        "fps": float(fps), "bit_depth": 8, "images": [str(BATCH_ID), 0]}}
    wf[str(SAVE_ID)] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": prefix, "format": "auto", "codec": "auto",
        "video": [str(VIDEO_ID), 0]}}
    # ---- Gate FLAT_SLOT_CEILING, wave 12 (F-133f2bdc). It lives HERE, in the function that
    # emits the BatchImagesNode it judges, for the reason `gate_create_video_fps` states four
    # lines above: an in-process caller cannot route around a check inside the emitter the way
    # it can route around one in `main`. Measured before the move:
    # `build(["%064x.png" % i for i in range(81)])` returned an 84-node graph whose node 400
    # carried 81 `images.image*` slots and raised nothing — the exact flat chain S03 watched
    # pass pre-flight and die at execution — while the gate in `build_and_write` refused that
    # same graph. The gate's own docstring already claimed this placement.
    #
    # It is the LAST statement because it reads the emitted node; `build_and_write` re-runs it
    # for the RECORD, which is the pattern `gate_create_video_fps` already uses.
    gate_flat_slot_ceiling(wf, BATCH_ID)
    return wf


def subject_provenance(subject, census=None):
    """Whose frames these are, or an explicit `null` with the reason — never a silence.

    Wave 22, F-27f76c43. Shared by both assemblers so the two records answer the question
    the same way. The census is `armature_core.canon_census`'s, NAMED in the record, so a
    reader can see which table answered rather than inferring it.
    """
    table = canon_census.CENSUS if census is None else census
    if subject is None:
        return {
            "subject": None,
            "why_null": (
                "--subject was not supplied. This chain authors no generation, so Gate "
                "CANON is not armed here and nothing forces a subject; the record states "
                "the absence rather than omitting the key, so a reader of the assembled "
                "clip's provenance sees that the question was asked and not answered"),
            "census": "armature_core.canon_census.CENSUS",
            "census_subjects": sorted(table),
            "row": None,
        }
    row = canon_census.row(subject, census=table)
    if row is None:
        raise AS.AssemblyGate(
            f"--subject {subject!r} is in no canon census this invocation can see "
            f"({sorted(table)}). The record this build writes is the provenance of the "
            f"clip a Director opens, and a subject name it asserts that nothing backs is a "
            f"placeholder shaped like evidence. Pass a name the census carries, or omit "
            f"the flag and let the record state `subject: null` with its reason",
            {"gate": "ASSEMBLY", "andon": "AssemblyGate",
             "clause": "subject_not_in_the_canon_census", "flag": "--subject",
             "subject": subject, "census": "armature_core.canon_census.CENSUS",
             "census_subjects": sorted(table)})
    return {
        "subject": subject,
        "census": "armature_core.canon_census.CENSUS",
        "census_subjects": sorted(table),
        "row": row,
    }


def build_and_write(argv=None):
    """Build, gate, write — and hand the GRAPH back to an in-process caller.

    Split out of `main` in wave 10 (F-aa92660a). `main` used to end `return wf` under
    `raise SystemExit(main())`, so CPython printed the graph dict to stderr and exited 1
    on a fully gated success: measured as a subprocess on an 81-entry padded map, stdout
    ended `BUILD_ASSEMBLY_OK <path>` with all five gate lines green, stderr received 9,445
    bytes of the graph, and the exit code was 1 — the code this module's own comment calls
    "this tool crashed". The exit convention and the tests' need for the artifact are two
    different jobs and they get two functions.
    """
    ap = argparse.ArgumentParser(
        description=(
            "Build and gate the FLAT frames->VIDEO chain (LoadImage x N -> BatchImagesNode "
            "-> CreateVideo -> SaveVideo) from an upload map. Writes the API graph and its "
            "payload record; submits nothing and loads no weights."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ROUTE: S03 Task C, the assembly chain. It is BOUNDED at "
            f"{MEASURED_FLAT_SLOT_MAX} slots - the largest flat batch anyone has seen "
            "execute - because the 81-slot form was falsified after passing the round trip "
            "and Gate ROUTE with zero warnings. Use build_cascade_payload for a clip of any "
            "length.\n"
            "\n"
            "WHAT A REFUSAL COSTS: nothing but your time; the frames these graphs "
            "carry feed the paid E13 A2 arm's reference video, so every gate here runs "
            "before a credit is spent downstream."))
    build_opts = ap.add_argument_group("build")
    output_opts = ap.add_argument_group("output")
    build_opts.add_argument("--uploads", required=True,
                       help="the upload step's JSON: local frame filename -> the server's "
                            "content-addressed name. Keys must be zero-padded frame names "
                            "with no gaps; the LOCAL name is the frame order")
    output_opts.add_argument("--out", required=True,
                        help="the directory the graph and its payload record are written into. "
                             "Created below the last gate, so a refusal leaves nothing behind; "
                             "an existing build there is refused unless --overwrite is passed")
    output_opts.add_argument("--overwrite", action="store_true",
                        help="replace an existing graph/record pair in --out. Without it a "
                             "rebuild over an earlier build refuses by name "
                             "(`output_already_exists`) and names both digests")
    build_opts.add_argument("--fps", type=float, default=16.0,
                       help=f"the CreateVideo rate, inside its measured contract "
                            f"{CREATE_VIDEO_FPS_RANGE} (default: %(default)s). Presentation "
                            f"only - it is downstream of the frames and changes no pixel")
    build_opts.add_argument("--prefix", default="video/S03_assembly",
                       help="the server-side filename prefix for the saved video "
                            "(default: %(default)s)")
    build_opts.add_argument("--subject", default=None, help="the character whose frames these are. This chain authors no generation, so Gate CANON is not armed here (see the note above `--out`) - but the record is the provenance of the artefact a Director opens, and until wave 22 it could not say whose frames it held. Optional: omitted, the record states `subject: null` and WHY, which is a recorded fact rather than a silence")
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    # ⚠ **Not a PARTNER-CREDIT spend, which is narrower than "not a spend"** (wave 22,
    # F-27f76c43, second half). This comment used to read "Not a spend: Gate ASSEMBLY_paid
    # requires zero billable nodes." MEASURED by calling
    # `armature_core.assembly.gate_no_paid_nodes` on this assembler's own class set, the
    # verdict it returns is: "3 node(s) across 3 class(es), all named by the allowlist, all
    # 3 carrying a receipt whose recorded api_node value READS False (oldest reading 23
    # day(s) old, all within the 90-day window), none reading as a partner class; 0 of 3
    # class(es) are known to the licence map (so the licence clause ruled on nothing here)".
    # That is a proof about PARTNER-CREDIT nodes. Ordinary Comfy Cloud workflow compute is
    # outside everything it measures. So: **no partner-credit node (allowlist-enforced);
    # ordinary Comfy Cloud compute still bills.** The record itself was already honest — it
    # carries the verdict verbatim under `gates.ASSEMBLY_paid`; this comment was the half
    # that claimed more than the gate proves. Gate CANON lives in the builders that author a
    # generation, not in a frames->VIDEO pack; the subject rides the record instead (below).
    #
    # `os.makedirs` used to sit HERE, above --uploads being read and above every gate
    # below. A refused build therefore left an empty run directory beside real ones, to be
    # read later as a run that happened. It now sits below the last in-tool gate, matching
    # the invariant build_payload.py states for Gate CANON.

    # ---- wave 22, F-27f76c43. MEASURED on `e8263a3` by grep over `tools/`: the key
    # "subject" occurred in NONE of the nine builder records. The seven SPEND builders
    # nonetheless carry the subject through `gate_CANON` — `canon_spend`'s evidence, and
    # `armature_core.canon` refuses outright with clause `missing_subject` when no subject
    # is given (measured by calling `canon_spend(None, 'a prompt')`) — while this assembler
    # and `build_cascade_payload` arm no Gate CANON at all, and their records carried only
    # server-side upload names, `frame_order`, `frame_source_ids` and node contracts.
    # Nothing in either record named the character whose frames were assembled, so the
    # provenance chain from the CLIP back to a subject was broken at the assembly step —
    # and the clip is the artefact a Director opens.
    #
    # `--subject` is OPTIONAL and its absence is a RECORDED FACT with its reason, per the
    # coordinator's 2026-09-04 ruling under the Director's delegation: this chain has no
    # generation to gate, so requiring a subject here would be a gate wearing a provenance
    # field's clothes. A subject the census does not know IS refused, because a name the
    # record asserts and nothing backs is the placeholder-shaped-like-evidence shape.
    subject_block = subject_provenance(a.subject)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    order = frame_order(uploads)             # LOCAL names: 00000.png .. 00080.png
    names = [uploads[k] for k in order]
    if len(set(names)) != len(names):
        raise AS.AssemblyGate(
            f"the upload map carries {len(names)} frames but only {len(set(names))} "
            f"distinct server names: two local frames uploaded to the same object, so the "
            f"batch would carry a duplicate while every count still read right",
            {"gate": "ASSEMBLY", "andon": "AssemblyGate",
             "clause": "two_frames_share_one_server_name",
             "n": len(names), "distinct": len(set(names))})

    wf = build(names, fps=a.fps, prefix=a.prefix)

    # ---- the gates, in code, before anything is submitted.
    gate_paid = AS.gate_no_paid_nodes(wf)
    # Re-run for the RECORD. `build` already raised on an over-wide batch and on an illegal
    # rate; these are the evidence dicts, so the receipt states the contracts that were
    # checked rather than asserting numbers nothing read.
    gate_flat = gate_flat_slot_ceiling(wf, BATCH_ID)
    gate_fps = gate_create_video_fps(a.fps)
    ordered_ids = frame_source_ids(names, FIRST_IMAGE_ID)
    gate_topo = AS.gate_batch_topology(wf, len(names), BATCH_ID, VIDEO_ID, SAVE_ID,
                                       expected_sources=ordered_ids)
    gate_index = gate_slot_frame_index(wf, names, [(BATCH_ID, 0, len(names))],
                                      FIRST_IMAGE_ID)
    # Gate ROUTE. `carries_no_sampler=True` is the CHECKED form of the sentence this
    # comment used to make with `require_pinned_seeds=False` (wave 12, F-60a1222b): the flag
    # said "nobody looked", the sentence said "there is nothing to look at", and only one of
    # those is a claim about the graph. `verify` refuses the two keywords together, so this is
    # a swap. The record now reads "CHECKED — no sampler in this graph (asserted by the caller
    # and checked)", the unrecorded-seed-source andon runs, and a sampler spliced into this
    # graph refuses HERE — where before the direction was bounded only by
    # `AS.gate_no_paid_nodes`' allowlist one module over, which a widening would have opened.
    # The clauses that also bind: the licence one (no weights load, so none can be banned) and
    # Gate PAIR (no conditioning node, so none can be unpaired).
    gate_route = RG.verify(wf, family="wan", carries_no_sampler=True,
                           frame=(WIDTH, HEIGHT, len(names)))

    record = {
        "tool": "build_assembly_payload", "tool_version": TOOL_VERSION,
        # whose frames these are — or an explicit null with its reason (wave 22, F-27f76c43)
        "subject": subject_block,
        "chain": "LoadImage x N -> BatchImagesNode -> CreateVideo -> SaveVideo",
        "n_frames": len(names), "fps": float(a.fps),
        "resolution": [WIDTH, HEIGHT],
        "filename_prefix": a.prefix,
        "frame_order": order,
        "uploads": {k: uploads[k] for k in order},
        "node_ids": {"first_image": FIRST_IMAGE_ID, "batch": BATCH_ID,
                     "video": VIDEO_ID, "save": SAVE_ID},
        "node_contracts_measured": {
            "when": "2026-08-13, get_node",
            "BatchImagesNode": "images COMFY_AUTOGROW_V3 -> IMAGE; api_node false",
            "CreateVideo": ("images IMAGE + fps FLOAT (1-120, default 30), optional audio "
                            "and bit_depth INT (8-10) -> VIDEO; api_node false, "
                            "output_node false"),
            "SaveVideo": ("video VIDEO + filename_prefix STRING + format COMBO(auto,mp4) + "
                          "codec dynamic COMBO(auto,h264) -> VIDEO; api_node false, "
                          "output_node TRUE"),
            "LoadImage": "image COMBO -> IMAGE, MASK; api_node false",
        },
        "frame_source_ids": list(ordered_ids),
        "gates": {"ASSEMBLY_paid": gate_paid, "FLAT_SLOT_CEILING": gate_flat,
                  "CREATE_VIDEO_fps": gate_fps,
                  "ASSEMBLY_topology": gate_topo,
                  "ASSEMBLY_slot_frame_index": gate_index, "ROUTE": gate_route},
        # Wave 20, F-dba1bcd8. The tie between THIS record and the graph beside it, so the
        # `ROUTE` receipt above cannot be read as describing a different graph.
        "payload_sha256": canonical_payload_digest(wf),
    }
    # Wave 34, F-d092c186 / F-dc84b444 — leave-the-rig disclosure + fetch recipe.
    disc = assembly_leave_disclosure(route_verdict=gate_route.get("verdict"))
    record["disclosure"] = disc
    recipe = fetch_recipe(
        node_map={}, video_nodes=(str(SAVE_ID),),
        root_hint="outputs/S03/runs",
        taps=[{"node": str(SAVE_ID), "class_type": "SaveVideo", "subdir": None}])
    record.update(recipe)

    graph_path = os.path.join(out, "S03-assembly.api.json")
    record_path = os.path.join(out, "S03-assembly-payload-record.json")
    # ---- Gate PAYLOAD · ANDON, wave 28 (F-5fd16451). Both filenames are FIXED, so a
    # rebuild into the same `--out` always lands on the prior pair; see
    # `gate_output_not_overwritten` for the measurement and for the one shape both domains
    # spell. ABOVE `os.makedirs`, like every other refusal in this tool: a refuse leaves no
    # output directory, and `tests/test_instrument_write_ordering` holds that ratchet.
    gate_overwrite = gate_output_not_overwritten(
        [graph_path, record_path], out, a.overwrite, AS.AssemblyGate, gate="PAYLOAD")
    record["gates"]["PAYLOAD_overwrite"] = gate_overwrite
    record["out_dir_pre_existed"] = gate_overwrite["out_dir_pre_existed"]
    record["overwrote"] = gate_overwrite["overwrote"]

    # Below the last in-tool gate: a refuse leaves no output directory.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    with open(record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print(f"nodes            {len(wf)}")
    print(f"paid-node gate   {gate_paid['verdict']}")
    print(f"flat slot gate   {gate_flat['verdict']}")
    print(f"topology gate    {gate_topo['verdict']}")
    print(f"slot->frame gate {gate_index['verdict']}")
    for line in route_report_lines(gate_route):
        print(line)
    # Wave 28, F-5fd16451: the digest that ties this record to this graph, and the overwrite
    # receipt, so two runs into one `--out` are distinguishable in a scrollback.
    print(f"payload sha256   {record['payload_sha256']}")
    print(f"overwrite        {gate_overwrite['verdict']}")
    for line in disclosure_lines(disc):
        print(line)
    # Wave 32, F-3e310dc1 / F-8d31935f — same OK LOOK as the JSON family (`path` key).
    print("BUILD_ASSEMBLY_OK " + json.dumps({"path": graph_path}, ensure_ascii=False))
    return wf


def main(argv=None):
    """The process exit code, and nothing else. 0 = built; a gate raises."""
    build_and_write(argv)
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `BUILD_ASSEMBLY_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "BUILD_ASSEMBLY")

