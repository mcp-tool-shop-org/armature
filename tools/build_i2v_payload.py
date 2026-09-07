#!/usr/bin/env python
r"""build_i2v_payload — E11's `WanImageToVideo` graph, built in this repo.

    python tools\build_i2v_payload.py --uploads=<uploads.json> --out=<dir> --subject=PERFORMER --no-canon
           --negative-source=<wan22_shared_config.py> --seeds-registry=specs\E11-seeds.json
           --e08-record=<E08-probe-payload-record.json>
           [--seed=2026081231 | --seeds-registry=specs\\E11-seeds.json]

The no-control route. A render of the performer is the first frame, a prompt describes the
shot, and **nothing else conditions the generation** — no pose sticks, no reference image,
no control video, no clip-vision embedding. Everything after frame 0 is the model's.

**Built here, never served.** Measured on this route 2026-08-12, and it is the third
instance of the pattern `docs/license-map.md` records as trap #3: the served
`video_wan2_2_14B_i2v` template at `main` presents **5 top-level nodes and hides 30 inside
a subgraph blueprint**, and what is hidden is the licence map's EXCLUDED lightx2v 4-step
tier — `wan2.2_i2v_lightx2v_4steps_lora_{high,low}_noise.safetensors` at strength 1.0,
4 steps, cfg 1.0, shift 5.0, with the high-noise sampler's `control_after_generate` set to
`randomize`. That graph could not pass Gate ROUTE or Gate S. A served template is a
reference, never a route.

--------------------------------------------------------------------------------
Where every number comes from

The trajectory is READ OFF the LoRA-free revision of the same template family, not solved
and not carried over from the Animate route. Two pinned commits of
`Comfy-Org/workflow_templates` (MIT — `docs/license-map.md`, *Services and tools*),
`templates/video_wan2_2_14B_i2v.json`, both fetched 2026-08-12 and banked with their
sha256 under `outputs/E11/route/`:

  * `5d6089c4250f` — 17 nodes, **no LoRA node of any kind anywhere in the file**. This is
    the revision the values come from.
  * `dcc00d29d79d` — carries the distilled path live and the non-distilled path bypassed
    (`mode = 4`). Its bypassed branch pins the SAME values, so the two revisions agree and
    the agreement is recorded rather than one being picked.

    steps 20 · split at step 10 · shift 8.0 · cfg 3.5 · euler · simple · fps 16

Its wiring was traced through the file's own `links` array in code rather than read off
node order, and it is the wiring built below: LoadImage -> WanImageToVideo.start_image;
both text encodes -> the conditioning node; the node's positive/negative to BOTH samplers
and its latent to the first; high-noise KSamplerAdvanced (add_noise enable, 0..split,
leftover enable) -> low-noise (add_noise disable, split..10000, leftover disable) ->
VAEDecode. `clip_vision_output` is unconnected there and is unconnected here.

--------------------------------------------------------------------------------
What is deliberately absent, and the andon that keeps it absent

`verify_topology` refuses the graph if it contains ANY conditioning class that can carry a
driving signal (`WanVaceToVideo`, `WanAnimateToVideo`, `Wan22FunControlToVideo`, ...), if
`clip_vision_output` is wired, or if any node other than the Gate B probe reads a second
uploaded image. E11's whole question is what the model does with no driving signal; a
graph that quietly acquired one would answer a different question and every other gate
would pass on it.

--------------------------------------------------------------------------------
"Pinned verbatim" is measured here, not asserted

The positive and negative are rebuilt from E08's own sources through E08's own code
(`build_animate_payload.identity_clause` / `read_negative`) and then compared **byte for
byte against E08's committed payload record**, which this tool requires as an input. If
either string has drifted by a character the build halts. The two-pipeline sheet's claim —
same prompt, different route — is the experiment's load-bearing comparability claim, and
E09's citation check already fired once on a negative somebody described from memory.

--------------------------------------------------------------------------------
The gates

* **Gate L** — `gates.g1_generator_legality` on the `wan-i2v` profile, raised in-tool
  before a single node is emitted.
* **Gate S** — `gates.gate_s_seed_registration` against `specs/E11-seeds.json`, committed
  before the first submission.
* **topology** — checked in code, because a `dry_run` PASS does not prove link sanity.
* **Gate ROUTE** — `route_gates.verify` on the graph this tool just built, with the frame
  supplied: `WanImageToVideo` sizes its own latent, and E08 measured what Gate L does on a
  graph whose latent it cannot find (it reported it legal having examined zero frames).
  It runs again, separately, on the saved file (`gate_saved_graph.py`).

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory. It submits nothing and spends nothing.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from canon_gate import canon_line, canon_spend  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.
from build_assembly_payload import (  # noqa: E402
    canonical_payload_digest, comfy_cloud_oss_disclosure, disclosure_lines,
    fetch_recipe, gate_create_video_fps, gate_output_not_overwritten,
    read_seed_registration, single_path_segment)

import build_animate_payload as E08  # noqa: E402  - the prompt's source of record

TOOL_VERSION = "E11.1"
EXPERIMENT = "E11"

#: E11's frame. 65 @ 16 fps is E08's, held deliberately: the deliverable this experiment
#: exists for is E08's painted probe beside E11's at true tempo, and a different length or
#: rate would put a second variable inside a comparison that already spans two models.
#: E10's ruling — "the more fps the better" — is a ruling about DRIVING density on the
#: skeletal route; there is no driving signal here, so it has nothing to move.
WIDTH, HEIGHT, LENGTH, FPS = 832, 480, 65, 16

#: Weights. Comfy-Org repacks of the Apache-2.0 Wan 2.2 I2V-A14B experts (map row fetched
#: 2026-08-12) — the 2026-08-11 repack ruling governs: the upstream grant applies and the
#: repack asserts nothing itself. umt5-xxl Apache-2.0; wan_2.1_vae is the Wan 2.1 tier.
#: The Kijai `Wan2_2-I2V-A14B-*_KJ` variants the catalog also serves are NOT used: they
#: are a third-party repack the map has no row for.
#: **NO LoRA of any kind is loaded** — see the trap above.
UNET_HIGH = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
UNET_LOW = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
CLIP_NAME = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE_NAME = "wan_2.1_vae.safetensors"

TEMPLATE_SOURCE = (
    "Comfy-Org/workflow_templates (MIT), templates/video_wan2_2_14B_i2v.json — the "
    "workflow served by https://docs.comfy.org/tutorials/video/wan/wan2_2, which the "
    "Wan-Video/Wan2.2 README itself designates as the ComfyUI reference. Fetched "
    "2026-08-12 at the two pinned commits below; NOT from `main`, which carries only the "
    "excluded lightx2v 4-step variant inside a subgraph blueprint")
TEMPLATE_PINS = ["5d6089c4250f", "dcc00d29d79d"]

#: Every sampling value with the source it came from. A value that cannot name its source
#: does not belong in the graph.
TRAJECTORY = {
    "steps": {"value": 20, "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.steps on both",
              "agrees_at": TEMPLATE_PINS},
    "split_step": {"value": 10,
                   "source": (f"{TEMPLATE_SOURCE}; the high-noise sampler runs "
                              f"start_at_step=0 end_at_step=10 and the low-noise one runs "
                              f"start_at_step=10 end_at_step=10000. READ OFF the workflow, "
                              f"not solved from a boundary"),
                   "agrees_at": TEMPLATE_PINS},
    "shift": {"value": 8.0,
              "source": (f"{TEMPLATE_SOURCE}; ModelSamplingSD3.shift on both branches "
                         f"(the file stores 8.000000000000002 on one and 8 on the other; "
                         f"they are the same value to float precision and 8.0 is used)"),
              "agrees_at": TEMPLATE_PINS},
    "cfg": {"value": 3.5, "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.cfg on both",
            "agrees_at": TEMPLATE_PINS},
    "sampler_name": {"value": "euler",
                     "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.sampler_name on both",
                     "agrees_at": TEMPLATE_PINS},
    "scheduler": {"value": "simple",
                  "source": f"{TEMPLATE_SOURCE}; KSamplerAdvanced.scheduler on both",
                  "agrees_at": TEMPLATE_PINS},
    "fps": {"value": FPS,
            "source": (f"{TEMPLATE_SOURCE}; CreateVideo.fps — which coincides with "
                       f"Wan-Video/Wan2.2 shared_config.sample_fps. Both are recorded, and "
                       f"it is also E08's rate, which is what the A/B needs"),
            "agrees_at": TEMPLATE_PINS},
}

#: What differs from E08's arm, enumerated so no reader has to reconstruct it. The spec
#: bounds this honestly as a ROUTE comparison, not a single-variable one; this table is
#: what that sentence means in numbers.
DELTA_FROM_E08 = [
    {"value": "conditioning node", "E08": "WanAnimateToVideo", "E11": "WanImageToVideo"},
    {"value": "diffusion weights", "E08": "wan2.2_animate_14B_bf16 (one expert)",
     "E11": "wan2.2_i2v_{high,low}_noise_14B_fp8_scaled (two experts, MoE)"},
    {"value": "text encoder", "E08": "umt5_xxl_fp16",
     "E11": "umt5_xxl_fp8_e4m3fn_scaled (the I2V reference workflow's own)"},
    {"value": "driving signal", "E08": "65 AAPose-20 stick frames on pose_video",
     "E11": "NONE — this is the experiment"},
    {"value": "identity conditioning", "E08": "letterboxed twin on reference_image",
     "E11": "the start frame itself; no reference socket exists on this node"},
    {"value": "sampler", "E08": "1 x KSampler, uni_pc/simple, 20 steps, cfg 6.0",
     "E11": "2 x KSamplerAdvanced, euler/simple, 20 steps split at 10, cfg 3.5"},
    {"value": "shift", "E08": "8.0 (inherited, undocumented for Animate)",
     "E11": "8.0 (read off the I2V reference workflow)"},
    {"value": "prompt / negative", "E08": "—", "E11": "byte-identical, checked in-tool"},
    {"value": "frame", "E08": "832x480x65 @ 16 fps", "E11": "832x480x65 @ 16 fps"},
]


class PayloadError(ArmatureError):
    """The payload could not be built as specified.

    Carries an optional evidence dict, the way `GateFailure` does. Wave 8 (F-bc806f79):
    `ledger_against_wave1` built a full evidence dict, wrote it into the payload record on
    the PASSING path, and then raised with a message and nothing else — so the failing
    measurement, the one worth having, reached no record at all. Four modules define this
    class; all four take the dict now, through the base's own constructor.

    **CORRECTION, wave 16 (F-c496fa48, rule 5).** This class used to define its own
    `__init__` normalising `evidence or {}`, under a note saying the single implementation
    "belongs beside `GateFailure` in `armature_core/errors.py`. That file is not this
    domain's to edit". Wave 14 put the constructor on the base and made a deliberate choice
    the four copies then overrode: `ArmatureError` STORES WHAT IT IS PASSED and normalises
    nothing, because `"evidence": null` beside `"gate": null` is the honest halt record for
    a refusal that carries no receipt. `GateFailure` is the one exemption - its clauses
    index into `ev` while they measure. `PayloadError` is not a gate, so the constructor is
    DELETED and the base's inherited: `PayloadError("m").evidence is None` and
    `PayloadError("m", d).evidence is d`, by identity.

    **WAVE 25, F-af838b99 — the class-level `gate`.** All thirteen tools in this domain
    print their halt line through `armature_core.parts.run_tool_main` now, which writes
    `getattr(exc, "gate", None)` into the record's `gate` key. `PayloadError` was the only
    class raised in this domain carrying none, so a payload refusal read `gate: null` from
    BOTH sources — the class attribute and, at the sites that pass no dict, the evidence —
    while fourteen raise sites were already writing `{"gate": "PAYLOAD"}` into their
    evidence literal. The id gets its owner, the way wave 18 gave `SAVED_ADMISSION` one.
    `gate` is a plain class attribute here and NOT a `GateFailure`: `__str__`'s `[gate]`
    prefix is defined on `GateFailure`, so no message text changes, and `halt_outcome`
    still reads this as "REFUSED — the tool declined to proceed" rather than as a gate
    that fired.
    """

    gate = "PAYLOAD"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description=(
            "Build and gate the plain i2v route's API graph: ONE start frame conditions the "
            "whole generation, with E08's prompt and negative pinned byte for byte. Writes "
            "the graph and its payload record; submits nothing."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
                "ROUTE: E11's i2v arm. The start frame IS this route's entire conditioning, so the tool hashes the local file rather than trusting a typed digest, and the prompt is compared against --e08-record byte for byte - 'pinned verbatim' is a measurement here, not a claim.\n"
                "\n"
                "WHAT A REFUSAL COSTS: nothing but your time; every gate runs before anything is submitted."))
    build_opts = ap.add_argument_group("build")
    output_opts = ap.add_argument_group("output")

    build_opts.add_argument("--uploads", required=True,
                    help="JSON: {start_frame: <server name>}")
    # Wave 10, F-531c5f1f. On this route the start frame IS the entire image conditioning
    # (see the module docstring: "nothing else conditions the generation"), and the record
    # named no local artifact for it at all — only `server_name`, a server-side
    # content-addressed name living in a separate uploads file, plus a prose `fit` string
    # about an image this tool never opened. Every `sha256` in this module was over a
    # STRING or the graph. CLAUDE.md: "Every generation records model id + version, the
    # full payload, the seed, and control-input hashes." The sibling
    # `build_camera_i2v_payload` grew these two flags in wave 8 (F-d342f393) for the same
    # artifact on the same class of route; they are CARRIED here, and so is its
    # `resolve_start_frame`, which hashes the file rather than trusting a typed digest.
    build_opts.add_argument("--start-frame", default=None,
                    help="the local re-authored start frame. REQUIRED: this route's whole "
                         "conditioning is this one image, and the tool hashes it so the "
                         "run can be reproduced from the record")
    build_opts.add_argument("--start-frame-sha256", default=None,
                    help="optional cross-check. It is compared against the digest the "
                         "tool computes from --start-frame, or the build halts")
    output_opts.add_argument("--out", required=True,
                    help="the directory the graph and its payload record are written into, "
                         "created below the last gate so a refusal leaves nothing behind; "
                         "an existing build there is refused unless --overwrite is passed")
    output_opts.add_argument("--overwrite", action="store_true",
                    help="replace an existing graph/record pair in --out. Without it a "
                         "rebuild over an earlier build refuses by name "
                         "(`output_already_exists`) and names both digests")
    build_opts.add_argument("--seed", type=int, default=None,
                    help="the seed to submit; omitted, the first seed in --seeds-registry "
                         "is used. Gate S refuses an unregistered number either way")
    build_opts.add_argument("--negative-source", default=None,
                    help="path to Wan's shared_config.py; the negative is READ from it "
                         "rather than retyped")
    build_opts.add_argument("--e08-record", required=True,
                    help="E08's committed payload record. The prompt and negative built "
                         "here are compared byte for byte against it and the build halts "
                         "on any drift — 'pinned verbatim' is a measurement, not a claim")
    build_opts.add_argument("--seeds-registry", default=None,
                    help="the committed seed registration Gate S checks --seed against, and "
                         "the list the default seed is taken from")
    build_opts.add_argument("--experiment", default=EXPERIMENT,
                    help="names the output files and the server-side filename prefixes "
                         "(default: %(default)s)")
    build_opts.add_argument("--length", type=int, default=LENGTH,
                    help="frame count, checked by Gate L and Gate ROUTE (argparse eats "
                         "leading minus signs, so pass flags as --flag=value) "
                         "(default: %(default)s)")
    build_opts.add_argument("--fps", type=float, default=FPS,
                    help="the CreateVideo rate (default: %(default)s). Presentation only - "
                         "it is downstream of VAEDecode and changes no generated pixel")
    add_spend_flags(ap)
    return ap.parse_args(argv)


def pin_against_e08(positive, negative, e08_record_path):
    """Gate PIN · ANDON — the strings are E08's, byte for byte. Raises on any drift.

    Both are rebuilt here from their own sources through E08's own code, so this is not a
    tautology: the identity clause is re-read from facet's twin JSON and the negative is
    re-parsed from the banked Wan config, and either file could have moved under the
    experiment. What this compares is *today's* rebuild against the string E08 actually
    submitted, which is the only object the A/B's "same prompt" claim can mean.
    """
    with open(e08_record_path, encoding="utf-8") as fh:
        rec = json.load(fh)
    ev = {"gate": "PIN", "e08_record": os.path.abspath(e08_record_path),
          "e08_experiment": rec.get("experiment"), "e08_seed": rec.get("seed")}
    problems = []
    for field, ours in (("positive", positive), ("negative", negative)):
        theirs = rec.get(field)
        ev[field] = {
            "sha256_built": hashlib.sha256(ours.encode("utf-8")).hexdigest(),
            "sha256_e08": (hashlib.sha256(theirs.encode("utf-8")).hexdigest()
                           if isinstance(theirs, str) else None),
            "len_built": len(ours),
            "len_e08": len(theirs) if isinstance(theirs, str) else None,
        }
        if not isinstance(theirs, str):
            problems.append(f"E08's record carries no {field} string to pin against")
        elif theirs != ours:
            problems.append(
                f"the {field} rebuilt here is not E08's: {len(ours)} chars against "
                f"{len(theirs)}, sha256 {ev[field]['sha256_built'][:16]} against "
                f"{ev[field]['sha256_e08'][:16]}")
    if problems:
        raise PayloadError(
            "the prompt this graph would submit is not the one E08 submitted, so the "
            "two-pipeline sheet would be comparing two prompts as well as two routes: "
            + "; ".join(problems),
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "prompt_is_not_the_e08_prompt", "problems": problems})
    ev["verdict"] = "positive and negative byte-identical to E08's submitted strings"
    return ev


def resolve_start_frame(path, declared_sha256=None):
    """The start frame's sha256, COMPUTED from the artifact — the sibling's clause, carried.

    `build_camera_i2v_payload.resolve_start_frame` is the implementation; it is imported
    HERE rather than at module scope because that module imports this one at module scope
    (`import build_i2v_payload as W1`, and it reads `W1.CLIP_NAME` while executing), so a
    top-level import in this direction is a cycle. The deferred import is the price of not
    writing a second copy of a gate.

    Its `PayloadError` is a different class from this module's, and every refusal this
    module makes is this module's `PayloadError`, so it is re-raised in this family with
    the sibling named in the evidence — the same carry shape `build_payload._carry` uses.

    ⚠ **It was NOT that shape, on the route whose entire conditioning is one image**
    (wave 18, F-c080a03f). The carry DISCARDED `exc.evidence` and built a fresh dict from
    the operator's inputs, while the exemplar it cites does the opposite — `_carry` is
    `dict(exc.evidence or {}, carried_from=...)`, evidence verbatim. Measured on the base
    tree against one JPEG-headed file:

        build_camera_i2v_payload.resolve_start_frame -> keys ['andon', 'bytes', 'clause',
            'first_8_bytes', 'flag', 'gate', 'path', 'read_by', 'sha256'],
            clause 'start_frame_not_a_png'
        build_i2v_payload.resolve_start_frame (SAME file) -> keys ['andon', 'carried_from',
            'declared_sha256', 'flag', 'gate', 'path'], clause None

    Every measured fact — the first eight bytes, the size, the digest and the clause name —
    was dropped and replaced by the path and the operator's `--start-frame-sha256`. An
    operator halted at the one input F-08853dfb established is the whole of this route's
    conditioning got a message with no machine-readable clause.

    The sibling's evidence rides verbatim now. The operator's inputs are kept as a FLOOR
    under it rather than in place of it, because two of the sibling's three refusals used to
    carry no evidence at all — they carry their own clauses as of the same wave, and every
    key they set wins over the floor.
    """
    import build_camera_i2v_payload as CAM  # noqa: PLC0415 - deferred: see the docstring

    try:
        return CAM.resolve_start_frame(path, declared_sha256)
    except CAM.PayloadError as exc:
        # The FLOOR carries a clause too (wave 25, F-d30bb5fb): the sibling's own keys
        # still win, so a refusal that names its clause keeps it, and one that does not
        # reaches the halt line with a word rather than with `clause` absent entirely.
        floor = {"gate": "PAYLOAD", "andon": "start_frame",
                 "clause": "start_frame_refused_by_the_sibling",
                 "flag": "--start-frame",
                 "path": path, "declared_sha256": declared_sha256}
        raise PayloadError(
            str(exc),
            dict(floor, **(exc.evidence or {}),
                 carried_from="build_camera_i2v_payload.resolve_start_frame")) from exc



#: The word a route uses when it asserts that NOTHING resamples the start frame. Both i2v
#: builders open their `fit` sentence with it ("native - authored at WxH ..."), and it is
#: the only declaration in this tree that claims an exact match; a letterbox or centre-crop
#: sentence claims something weaker and is recorded rather than gated.
NATIVE_FIT_WORD = "native"


def declares_native_fit(fit):
    """Does this route's own `fit` sentence assert an exact match?

    Read off the CALLER's sentence rather than off a constant here, so the gate below binds
    the claim the record makes instead of a resolution this module happens to know.
    """
    return str(fit or "").strip().lower().startswith(NATIVE_FIT_WORD)


def start_image_record(start_frame, server_name, width, height, fit, why=None, *,
                       declares_alpha=None):
    """The `start_image` block of an i2v payload record — ONE implementation, two routes.

    Wave 12, F-d979ec52. This shape existed twice and only one copy carried the comparison.
    `build_camera_i2v_payload`, the module that OWNS `png_header` and `resolve_start_frame`,
    wrote `{"server_name": …, "fit": "native — authored at 832x480, the same upload wave 1
    ran"}` — an assertion about wave 1's resolution in a record whose own
    `DELIBERATE_BREAKS["resolution"]` says the wave generates at 1024x576. Two fields of one
    provenance record disagreed about the load-bearing conditioning input, and the
    measurement that settles it was already in the tool, reaching only the ledger's evidence
    dict. Measured by grep 2026-09-04: `fit_agrees_with_the_file` occurred in this module and
    nowhere in the sibling that imports this module's resolver.

    It lives HERE rather than in the module that owns the resolver because that module
    imports this one at module scope (`import build_i2v_payload as W1`); the reverse
    direction is a cycle, which is why its resolver is imported lazily inside
    `resolve_start_frame` above.

    `fit` is the route's own sentence about how the frame meets the generation's frame.
    `fit_agrees_with_the_file` is the CHECK on it, and it is a boolean rather than a
    tri-state: `resolve_start_frame` refuses a file whose IHDR it could not read
    (F-08853dfb) and both builders refuse an evidence dict with no measurement, so the
    `None if not start_frame.get("image")` degradation — a null on exactly the input that
    most needs the comparison — has no input left to happen on.

    **CORRECTION, wave 14 (F-e17613c2).** The paragraph above described a comparison and
    called it a CHECK. It was not one. `fit_agrees_with_the_file` was computed, written into
    the record, and read by nothing: measured by grep over the tree 2026-09-04, the name
    occurs in this module, in the sibling that imports it, and in tests — and in no other
    file under `tools/`, `docs/` or `verify.ps1`. Two tests pinned the non-refusal, so the
    832x480 frame handed to a 1024x576 wave (this repo's own words for "the mutation that
    actually happened") built green and recorded `False`. The clause below is the andon on
    the direction the sibling clauses do not bound: they refuse a measurement that never
    arrived; this refuses one that arrived and disagreed. A diagnostic and a gate are
    different objects, and the object this route needed on the whole of its conditioning,
    one step before an irreversible spend, was the gate.

    **The SECOND correction, wave 16 (F-71ffdbfb).** `measured["alpha"]` was the same shape
    one field over: computed by `png_header`, written into every record, and read by
    nothing (measured by grep over `tools/`, `docs/` and `verify.ps1`, 2026-09-04). A flat
    RGB grey plate authored at the generation's exact size — the E11 baked-grey-void shape
    the Director's 2026-08-12 ruling exists to stop — was accepted with `alpha: False`
    recorded and nothing printed. `declares_alpha` is the route's own statement of which
    half of that ruling this file is: the authored RGBA master (`True`) or the recorded RGB
    composite (`False`). The file must be what the route says it is, in both directions,
    and a route that declares nothing is refused — a default that disarms a clause is the
    clause's deletion, not a default.
    """
    measured = start_frame["image"]
    agrees = [measured["width"], measured["height"]] == [width, height]
    # ---- ANDON, wave 14 (F-e17613c2). The comparison wave 12 built to replace an asserted
    # `fit` sentence with a measurement was COMPUTED and GATED NOTHING, on both i2v spend
    # builders, about the one input that is the whole of the route's conditioning. Measured
    # by grep 2026-09-04: `fit_agrees_with_the_file` occurs in the two writers and in tests,
    # and in nothing under tools/, docs/ or verify.ps1 — no caller reads it. Two tests PINNED
    # the non-refusal: the 832x480 frame handed to a 1024x576 wave (that module's own words,
    # "the mutation that actually happened") built green and recorded `False`. So a paid i2v
    # generation could go out on a start frame at the wrong resolution with every printed
    # gate line green and the disagreement visible only to someone who opened the JSON —
    # credits spent, and spent credits have no compensator.
    #
    # The clause keys on the CALLER'S OWN `fit` sentence, not on a constant here: a route
    # that declares a NATIVE fit is asserting an exact match, and a file that disagrees makes
    # the record's own sentence untrue. A future letterboxing or centre-crop route states its
    # own `fit` and passes this clause with its own sentence intact, which is why the gate is
    # written against the declaration rather than against the numbers alone.
    #
    # The sibling clauses one screen up already raise for a start frame with NO measurement
    # (build_i2v_payload:375) and one whose IHDR cannot be read
    # (build_camera_i2v_payload:577). This is the andon on the direction they do not bound:
    # a measurement that arrived and disagreed. A diagnostic and a gate are different objects.
    if declares_native_fit(fit) and not agrees:
        raise PayloadError(
            f"the route declares a NATIVE fit ({fit!r}) and the start frame is "
            f"{measured['width']}x{measured['height']} while this generation's frame is "
            f"{width}x{height}. `native` asserts that nothing resamples the image, so the "
            f"record's own `fit` sentence would be untrue and the whole of this route's "
            f"conditioning would be an image at the wrong size. Re-author the start frame "
            f"at {width}x{height}, or state the route's real fit (a letterbox or a "
            f"centre-crop sentence passes this clause with its own words)",
            {"gate": "PAYLOAD", "andon": "start_frame",
             "clause": "fit_disagrees_with_the_file", "flag": "--start-frame",
             "fit": fit, "declares_native_fit": True,
             "measured": [measured["width"], measured["height"]],
             "generation_frame": [width, height],
             "path": start_frame.get("path"), "sha256": start_frame.get("sha256")})
    # ---- ANDON, wave 16 (F-71ffdbfb). `measured["alpha"]` - the field that makes the
    # Director's 2026-08-12 alpha ruling machine-readable - was computed, written into
    # every i2v payload record, and READ BY NOTHING: the identical shape wave 14 corrected
    # one field over in this same dict. Measured by grep over the tree 2026-09-04, the
    # `alpha` produced by `png_header` occurred at its own line and at no other site under
    # `tools/`, `docs/` or `verify.ps1`. Measured end to end: a FLAT RGB grey plate authored
    # at the generation's exact size - the E11 baked-grey-void shape the ruling exists to
    # stop - was ACCEPTED with `measured.alpha: False` recorded and nothing printed.
    #
    # The ruling has two halves and the clause reads both. The authored master carries a
    # real alpha channel; **the RGB composite each route submits is a deliberate, recorded
    # choice**, because video VAEs are RGB and raw transparency cannot reach the model. So
    # the route DECLARES which of the two `--start-frame` names, and the file must be it -
    # a submitted composite that still carries the channel is transparency reaching an RGB
    # VAE, and an authored master that arrives flattened is the grey void arriving by
    # accident. Both directions refuse; a route's silence refuses too, because a default
    # that disarms a clause is not a default, it is the clause's deletion.
    measured_alpha = bool(measured.get("alpha"))
    if declares_alpha is None:
        raise PayloadError(
            f"this route wrote a `start_image` block without declaring what it submits: "
            f"`declares_alpha` is the route's own statement that {start_frame.get('path')!r} "
            f"is the authored RGBA master (True) or the recorded RGB composite (False). "
            f"The file measures alpha={measured_alpha}, and a silence read as agreement "
            f"with whatever the file happened to be is the ruling made unenforceable",
            {"gate": "PAYLOAD", "andon": "start_frame",
             "clause": "alpha_declaration_missing", "flag": "--start-frame",
             "declares_alpha": None, "measured_alpha": measured_alpha,
             "alpha_source": measured.get("alpha_source"),
             "path": start_frame.get("path"), "sha256": start_frame.get("sha256")})
    if bool(declares_alpha) != measured_alpha:
        was = ("an authored RGBA master" if declares_alpha
               else "the recorded RGB composite")
        raise PayloadError(
            f"the route declares this start frame is {was} and the file says otherwise: "
            f"alpha={measured_alpha}"
            + (f" (read off its {measured.get('alpha_source')})" if measured_alpha
               else " (no alpha channel and no tRNS chunk)")
            + f", colour type {measured.get('color_type')!r}. Video VAEs are RGB and raw "
            f"transparency cannot reach the model, so a submitted composite that still "
            f"carries the channel is not the artifact the record names; and a master that "
            f"arrives flattened is the grey previz void arriving by accident, which is the "
            f"defect the Director's 2026-08-12 ruling exists to stop. Composite the master "
            f"over its named plate before uploading, or state what this file is",
            {"gate": "PAYLOAD", "andon": "start_frame",
             "clause": "alpha_disagrees_with_the_file", "flag": "--start-frame",
             "declares_alpha": bool(declares_alpha), "measured_alpha": measured_alpha,
             "alpha_source": measured.get("alpha_source"),
             "color_type": measured.get("color_type"),
             "path": start_frame.get("path"), "sha256": start_frame.get("sha256")})
    rec = {
        "server_name": server_name,
        # ---- the LOCAL artifact, which these records could not name until wave 10.
        "path": start_frame["path"],
        "sha256": start_frame["sha256"],
        "bytes": start_frame["bytes"],
        "sha256_source": start_frame["source"],
        "declared_sha256": start_frame.get("declared_sha256"),
        # ---- and what it actually IS, read from the file's own header, so the `fit` line
        # is checkable instead of asserted. The alpha field is the Director's 2026-08-12
        # ruling made machine-readable: an authored input carries alpha, and the RGB
        # composite the route submits is a recorded choice, never an accident.
        "measured": measured,
        "fit": fit,
        "fit_agrees_with_the_file": agrees,
        # what the sentence above CLAIMS, so a reader of the record can see which clause
        # ran: a native declaration is gated, any other is recorded and not gated.
        "fit_declares_native": declares_native_fit(fit),
        # ---- and the alpha half of the same ruling, ARMED (wave 16, F-71ffdbfb). What the
        # route says this artifact is, and whether the file agrees. The comparison is a
        # refusal above; these two lines are what a reader of the record sees of it.
        "alpha_declared": bool(declares_alpha),
        "alpha_agrees_with_the_file": bool(declares_alpha) == bool(measured.get("alpha")),
        "generation_frame": [width, height],
    }
    if why:
        rec["why"] = why
    return rec


def build(uploads, seed, negative, positive, registry, experiment=EXPERIMENT,
          length=LENGTH, fps=FPS, start_frame=None):
    """The API-format graph, plus its meta. Gate L and Gate S raise before anything exists."""
    # ---- ANDON, wave 10 (F-531c5f1f). The start frame is this route's ENTIRE image
    # conditioning, and a record that cannot name its bytes is not a recipe. The clause
    # lives here rather than in `main` so an in-process caller cannot route around it.
    if not start_frame or not start_frame.get("sha256"):
        raise PayloadError(
            "build() needs the resolved start frame: on this route the start image is the "
            "whole of the conditioning, and `meta['start_image']` used to identify it only "
            "by a server-side content-addressed name in a separate uploads file. Call "
            "`resolve_start_frame(path, declared)` and pass its evidence",
            {"gate": "PAYLOAD", "andon": "start_frame",
             "clause": "start_frame_was_not_resolved", "flag": "--start-frame",
             "start_frame": start_frame})
    # ---- and the measurement, not only the digest (wave 12, F-08853dfb). A record whose
    # `fit` line is a sentence about an image nothing opened is the claim wave 10 set out to
    # replace with a measurement; `resolve_start_frame` refuses a file it cannot read, and
    # this refuses an evidence dict that reached here without one, so the comparison below
    # cannot degrade to a null on the input that most needs it.
    if not start_frame.get("image"):
        raise PayloadError(
            "the resolved start frame carries no measurement of its own pixels: this "
            "route's whole conditioning is that one image, and `fit_agrees_with_the_file` "
            "would be null on exactly the input the comparison exists for. Resolve it "
            "through `resolve_start_frame`, which reads the file's IHDR and refuses a file "
            "it cannot read",
            {"gate": "PAYLOAD", "andon": "start_frame", "clause": "start_frame_unmeasured",
             "flag": "--start-frame", "start_frame": start_frame})
    # ---- Gate ROUTE - ANDON on `CreateVideo.fps` (wave 10, F-29693a0e, family carry).
    # `--fps` reached the node with no clause in all five builders that take the flag,
    # while every one of their records states the node's measured contract as
    # "fps FLOAT (1-120)". One implementation, in `build_assembly_payload`, imported here.
    gate_create_video_fps(fps)
    # The default is resolved BEFORE Gate S, not after it. The old order put
    # `seed_used = seed if seed is not None else (sorted(registry)[0] if registry else 0)`
    # BELOW a gate that refuses a non-int first, so the fallback was dead code and the
    # usage block's optional `--seed` always halted on a message about NoneType — an
    # operator following the documented invocation got a halt naming the wrong problem.
    # The `else 0` branch was worse than dead: it read as a working default and would have
    # shipped an unregistered seed the moment the ordering changed.
    if seed is None and not registry:
        # ---- wave 22, F-87600738. This raise carried NO second argument at all, so under
        # the wave-16 rule-5 base (`armature_core/errors.py`: a bare message stores `None`)
        # the halt line printed `"evidence": null` and the refusal carried no `gate`, no
        # `andon` and no `clause`. RE-MEASURED on `e8263a3` by grep across `tools/`: the
        # string `no_seed_and_no_registration` occurred at exactly ONE site,
        # `build_t2v_payload.py`, while THREE builders — this one, `build_i2v_payload` and
        # `build_camera_i2v_payload` — raised the same refusal as a sentence. Confirmed by
        # calling `build(...)` with `seed=None` and an empty registry: `PayloadError`
        # raised, `evidence` None, `gate` None. So of the four callers that default a seed
        # off the registration, one was machine-readable and three were prose: the clause
        # census that wave 16 built to prove every refusal is reachable and NAMED saw 1 of
        # the 4 sites, and an operator hitting it on three of the four routes got a halt a
        # wrapper cannot classify.
        raise PayloadError(
            "no --seed and no --seeds-registry: this experiment pre-registered no seeds, "
            "so there is no committed number to default to, and Gate S refuses a seed "
            "varied without a registration. Pass --seeds-registry with the experiment's "
            "committed list, or pass --seed with a number that is on it",
            {"gate": "PAYLOAD", "andon": "seed_registration",
             "clause": "no_seed_and_no_registration", "flag": "--seeds-registry",
             "registered": list(registry or [])})
    seed_used = seed if seed is not None else sorted(registry)[0]
    gate_s = gates.gate_s_seed_registration(seed_used, registry, experiment,
                                            seed_was_explicit=seed is not None)
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, length, "wan-i2v")

    steps = TRAJECTORY["steps"]["value"]
    split = TRAJECTORY["split_step"]["value"]
    shift = TRAJECTORY["shift"]["value"]
    cfg = TRAJECTORY["cfg"]["value"]
    sampler = TRAJECTORY["sampler_name"]["value"]
    scheduler = TRAJECTORY["scheduler"]["value"]

    start_name = uploads["start_frame"]

    wf = {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": UNET_HIGH, "weight_dtype": "default"}},
        "11": {"class_type": "UNETLoader",
               "inputs": {"unet_name": UNET_LOW, "weight_dtype": "default"}},
        "12": {"class_type": "ModelSamplingSD3",
               "inputs": {"shift": shift, "model": ["10", 0]}},
        "13": {"class_type": "ModelSamplingSD3",
               "inputs": {"shift": shift, "model": ["11", 0]}},
        "20": {"class_type": "CLIPLoader",
               "inputs": {"clip_name": CLIP_NAME, "type": "wan", "device": "default"}},
        "21": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "30": {"class_type": "CLIPTextEncode",
               "inputs": {"text": positive, "clip": ["20", 0]}},
        "31": {"class_type": "CLIPTextEncode",
               "inputs": {"text": negative, "clip": ["20", 0]}},
        # The GLB, as an image. One frame, uploaded once.
        "40": {"class_type": "LoadImage", "inputs": {"image": start_name}},
        # Gate B probe: the start frame as the conditioning node receives it, saved so it
        # can be compared pixel for pixel against the local render. The local round trip
        # cannot prove the half that matters — that the SERVER decodes the upload the same
        # way — and on this route the start frame is the entire image conditioning.
        "41": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": f"{experiment}/probe/startprobe",
                          "images": ["40", 0]}},
        "50": {"class_type": "WanImageToVideo", "inputs": {
            "width": WIDTH, "height": HEIGHT, "length": length, "batch_size": 1,
            "positive": ["30", 0], "negative": ["31", 0], "vae": ["21", 0],
            "start_image": ["40", 0],
            # clip_vision_output is deliberately absent — unconnected in the documented
            # reference workflow too, and wiring it would add a second image-conditioning
            # channel to an experiment whose subject is having only one.
        }},
        # The high-noise expert carries the run's registered seed and adds the noise.
        "60": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": seed_used, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": 0, "end_at_step": split,
            "return_with_leftover_noise": "enable",
            "model": ["12", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["50", 2]}},
        # The low-noise expert continues the same trajectory: it adds no noise, so its own
        # seed draws nothing and is inert — Gate S reports it and does not demand it.
        "61": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "disable", "noise_seed": 0, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": split, "end_at_step": 10000,
            "return_with_leftover_noise": "disable",
            "model": ["13", 0], "positive": ["50", 0], "negative": ["50", 1],
            "latent_image": ["60", 0]}},
        "70": {"class_type": "VAEDecode",
               "inputs": {"samples": ["61", 0], "vae": ["21", 0]}},
        # THE LOSSLESS OUTPUT TAP — the frames CreateVideo is about to hand SaveVideo,
        # taken off VAEDecode before any codec touches them. Every measurement reads these.
        "71": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"{experiment}/probe/lossless", "images": ["70", 0]}},
        "80": {"class_type": "CreateVideo",
               "inputs": {"fps": fps, "bit_depth": 8, "images": ["70", 0]}},
        "81": {"class_type": "SaveVideo", "inputs": {
            "filename_prefix": f"video/{experiment}_probe", "format": "auto",
            "codec": "auto", "video": ["80", 0]}},
    }

    verify_topology(wf, start_name)

    gate_route = route_gates.verify(wf, frame=(WIDTH, HEIGHT, length))

    meta = {
        "experiment": experiment, "tool_version": TOOL_VERSION,
        "route": "no-control I2V — the GLB supplies the image, the model supplies the rest",
        "resolution": [WIDTH, HEIGHT], "length": length, "fps": fps,
        "seed": seed_used,
        "gate_S": gate_s,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "gate_ROUTE_built": gate_route,
        "models": {"unet_high_noise": UNET_HIGH, "unet_low_noise": UNET_LOW,
                   "clip": CLIP_NAME, "vae": VAE_NAME, "loras": []},
        "trajectory": TRAJECTORY,
        "two_expert_split": {
            "steps": steps, "split_step": split,
            "high_noise_steps": f"0..{split}", "low_noise_steps": f"{split}..{steps}",
            "origin": "READ OFF the documented reference workflow, not solved"},
        "positive": positive,
        "negative": negative,
        "start_image": start_image_record(
            start_frame, start_name, WIDTH, HEIGHT,
            fit=f"native — authored at {WIDTH}x{HEIGHT}",
            # What this route SUBMITS, declared rather than discovered (wave 16,
            # F-71ffdbfb). The Director's 2026-08-12 ruling: the master is authored RGBA
            # and the RGB composite the route uploads is a deliberate, recorded choice.
            # `--start-frame` names the uploaded file, so this route declares the
            # composite; a file that still carries the channel is refused above, because
            # raw transparency cannot reach an RGB video VAE.
            declares_alpha=False,
            why=("no letterbox and no centre-crop: the frame is rendered at the "
                 "generation's own size, so nothing resamples it. E08 measured what a "
                 "mismatched aspect costs on the other route — WanAnimateToVideo kept 204 "
                 "of its reference's 1024 rows")),
        "unconnected_inputs": {
            "clip_vision_output": ("unconnected in the documented reference workflow and "
                                   "unconnected here; a second image-conditioning channel "
                                   "would change what this experiment is measuring")},
        "no_driving_signal": (
            "checked in code by verify_topology: the graph contains no control-capable "
            "conditioning class, no second uploaded image outside the Gate B probe, and "
            "no clip-vision path. This is E11's defining property"),
        "delta_from_E08": DELTA_FROM_E08,
        # Wave 20, F-dba1bcd8: through the ONE shared derivation, not a copy
        # of the expression. Four builders each carried their own spelling of it
        # and `route_facts` carried a fifth, five places for the digest the gate
        # compares against to drift from the digest a record declares.
        "payload_sha256": canonical_payload_digest(wf),
    }
    disc = comfy_cloud_oss_disclosure(
        route_verdict=(meta.get("gate_ROUTE_built") or {}).get("verdict"))
    meta["disclosure"] = disc
    meta.update(fetch_recipe(
        node_map={"41": "startprobe", "71": "lossless"}, video_nodes=("81",),
        root_hint="outputs/E11/runs",
        taps=[{"node": "41", "class_type": "SaveImage", "subdir": "startprobe"},
              {"node": "71", "class_type": "SaveImage", "subdir": "lossless"},
              {"node": "81", "class_type": "SaveVideo", "subdir": None}]))
    return wf, meta


#: Conditioning classes that can carry a driving signal. Presence of any of them is the
#: end of E11 as an experiment, so the check is on the class list rather than on whether a
#: particular socket happens to be wired: a control node present but unfed is one edit
#: from being fed, and the map's own ruling on the licence tier is that presence is
#: presence.
CONTROL_CLASSES = ("WanVaceToVideo", "WanAnimateToVideo", "Wan22FunControlToVideo",
                   "WanFunControlToVideo", "WanCameraImageToVideo",
                   "WanFirstLastFrameToVideo", "WanPhantomSubjectToVideo",
                   "ControlNetApply", "ControlNetApplyAdvanced",
                   "ControlNetApplySD3", "ACN_AdvancedControlNetApply")


def verify_topology(wf, start_name):
    """Link topology, checked in code. A `dry_run` PASS does not prove link sanity."""
    problems = []

    node = wf.get("50")
    if not node or node["class_type"] != "WanImageToVideo":
        problems.append("node 50 is not the WanImageToVideo conditioning node")
    else:
        inp = node["inputs"]
        if inp.get("start_image") != ["40", 0]:
            problems.append("start_image is not fed by the start-frame LoadImage")
        if "clip_vision_output" in inp:
            problems.append(
                "clip_vision_output is connected; this wave's record says it is not, and "
                "a second image-conditioning channel would make the identity clause "
                "unattributable between the start frame and the embedding")

    # ---- the defining property, checked rather than trusted.
    for nid, n in wf.items():
        if n["class_type"] in CONTROL_CLASSES:
            problems.append(
                f"node {nid} is {n['class_type']}, a conditioning class that can carry a "
                f"driving signal. E11 is the no-control route; a graph with one answers a "
                f"different question and every other gate passes on it")
    loaders = [nid for nid, n in wf.items() if n["class_type"] == "LoadImage"]
    if loaders != ["40"]:
        problems.append(
            f"expected exactly one LoadImage (the start frame), found {loaders}. A second "
            f"uploaded image is a second conditioning channel however it is labelled")

    hi = wf.get("60", {}).get("inputs", {})
    lo = wf.get("61", {}).get("inputs", {})
    if hi.get("latent_image") != ["50", 2]:
        problems.append("the high-noise sampler does not take the conditioning node's latent")
    if lo.get("latent_image") != ["60", 0]:
        problems.append("the low-noise sampler does not continue the high-noise latent")
    for tag, ks, model in (("high", hi, ["12", 0]), ("low", lo, ["13", 0])):
        if ks.get("model") != model:
            problems.append(f"the {tag}-noise sampler does not take its own shifted expert")
        if ks.get("positive") != ["50", 0] or ks.get("negative") != ["50", 1]:
            problems.append(
                f"the {tag}-noise sampler does not take the conditioning node's "
                f"conditioning; text encodes wired straight to a sampler would drop the "
                f"start image's latent conditioning entirely and still generate a video")
    if hi.get("add_noise") != "enable" or lo.get("add_noise") != "disable":
        problems.append("the two-expert split's add_noise pair is not enable then disable")
    if hi.get("end_at_step") != lo.get("start_at_step"):
        problems.append(
            f"the experts do not hand over at the same step: high ends at "
            f"{hi.get('end_at_step')} and low starts at {lo.get('start_at_step')}, which "
            f"would silently skip or repeat part of the trajectory")

    if wf.get("41", {}).get("inputs", {}).get("images") != ["40", 0]:
        problems.append("the Gate B probe does not read the start-frame LoadImage directly")
    if wf.get("71", {}).get("inputs", {}).get("images") != ["70", 0]:
        problems.append("the lossless tap does not read VAEDecode directly")
    if wf.get("40", {}).get("inputs", {}).get("image") != start_name:
        problems.append("the LoadImage does not name the uploaded start frame")

    for nid, n in wf.items():
        for key, v in n["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in wf:
                problems.append(f"node {nid}.{key} links to missing node {v[0]}")

    for dead in ("DWPreprocessor", "OpenposePreprocessor", "SAM2", "LoadVideo",
                 "GetVideoComponents", "LoraLoaderModelOnly", "LoraLoader"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} is present; the licence map bans or excludes this tier")

    if problems:
        raise PayloadError(
            "the built graph is not the graph the spec describes: " + "; ".join(problems),
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "built_graph_is_not_the_spec_graph", "problems": problems})
    return True


def main(argv=None):
    a = parse_args(argv)
    # ---- ANDON, wave 22 (F-7e45e62b, sibling carry). `--experiment` is pasted into this tool's
    # written filenames with no clause, exactly as `fetch_run --run` was. Census over this
    # domain, 2026-09-05: FIVE free-string flags reach a written filename -- `--experiment`
    # in `build_animate_payload`, `build_i2v_payload` and `build_camera_i2v_payload`,
    # `--tag` in `build_t2v_payload` (whose own help says "goes in the written filenames"),
    # and `fetch_run --run`. `build_camera_i2v_payload --wave` also reaches a filename and
    # is ALREADY BOUNDED by `type=int` -- measured, argparse refuses `--wave=a/b` before
    # `main` is entered -- so it takes no clause of its own. The bounded convention already
    # exists in this domain: `build_payload --experiment` and `build_r2v` /
    # `build_lora_arm --arm` are `choices=`-bounded.
    #
    # The clause is `single_path_segment`'s, imported from its ONE home (SEAM 1): same
    # clause word `output_name_is_not_a_name`, same evidence keys.
    single_path_segment(a.experiment, "--experiment", PayloadError,
                        extra={"pasted_into": ["<out>/{experiment}-probe-i2v.api.json",
                                        "<out>/{experiment}-probe-payload-record.json",
                                        "the server-side filename prefixes"]})
    out = os.path.abspath(a.out)

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    if "start_frame" not in uploads:
        raise PayloadError(
            f"{a.uploads} carries no `start_frame` upload name",
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "uploads_carry_no_start_frame", "flag": "--uploads",
             "path": os.path.abspath(a.uploads)})

    registry = None
    if a.seeds_registry:
        # ONE reader, eight callers (wave 16, F-0682bd00). The bare `json.load(fh)["seeds"]`
        # this replaces raised a stdlib KeyError naming a key and nothing else on a
        # registration with no `seeds` key.
        registry = read_seed_registration(a.seeds_registry, flag="--seeds-registry")

    if not a.negative_source:
        raise PayloadError(
            "--negative-source is required: Wan's sample_neg_prompt is READ from the "
            "banked config, never retyped. E09's citation check fired on this string",
            {"gate": "PAYLOAD", "andon": "PayloadError",
             "clause": "negative_source_not_supplied", "flag": "--negative-source"})
    negative = E08.read_negative(a.negative_source)
    ident, ident_original, drops = E08.identity_clause()
    positive = ident + ". " + E08.SCENE_CLAUSE
    # The SHIPPED positive is what the router checks; `--canon-prompt` is compared
    # against it rather than substituted for it.
    canon_ev = canon_spend(a.subject, positive, no_canon=a.no_canon, out_dir=out,
                           canon_prompt=a.canon_prompt)

    gate_pin = pin_against_e08(positive, negative, a.e08_record)

    start_frame = resolve_start_frame(a.start_frame, a.start_frame_sha256)
    wf, meta = build(uploads, a.seed, negative, positive, registry,
                     experiment=a.experiment, length=a.length, fps=a.fps,
                     start_frame=start_frame)
    meta["gate_PIN"] = gate_pin
    meta["gate_CANON"] = canon_ev
    meta["prompt_record"] = {
        "identity_clause_source": E08.TWIN_PROMPT_JSON,
        "identity_clause_original": ident_original,
        "identity_clause_used": ident,
        "identity_drops": drops,
        "scene_clause": E08.SCENE_CLAUSE,
        "rebuilt_through": ("build_animate_payload.identity_clause / read_negative — E08's "
                            "own code, not a copy of its output"),
        "negative_source": os.path.abspath(a.negative_source),
        "negative_source_sha256": hashlib.sha256(
            open(a.negative_source, "rb").read()).hexdigest(),
    }

    gpath = os.path.join(out, f"{a.experiment}-probe-i2v.api.json")
    mpath = os.path.join(out, f"{a.experiment}-probe-payload-record.json")
    # Wave 35, F-0bd5c9c9: same overwrite shape as assembly/cascade.
    gate_overwrite = gate_output_not_overwritten(
        [gpath, mpath], out, a.overwrite, PayloadError, gate="PAYLOAD")
    meta["gates"] = dict(meta.get("gates") or {})
    meta["gates"]["PAYLOAD_overwrite"] = gate_overwrite
    meta["out_dir_pre_existed"] = gate_overwrite["out_dir_pre_existed"]
    meta["overwrote"] = gate_overwrite["overwrote"]
    os.makedirs(out, exist_ok=True)
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(canon_line(canon_ev))
    for line in disclosure_lines(meta["disclosure"]):
        print(line)
    print("BUILD_I2V_OK " + json.dumps({"path": gpath, 
        "graph": gpath, "record": mpath, "nodes": len(wf), "seed": meta["seed"],
        "length": meta["length"], "fps": meta["fps"],
        "split_step": meta["two_expert_split"]["split_step"],
        "payload_sha256": meta["payload_sha256"][:32],
        "start_frame_sha256": meta["start_image"]["sha256"][:32],
        "gate_PIN": gate_pin["verdict"],
        "gate_L": meta["gate_L"]["verdict"], "gate_S": meta["gate_S"].get("verdict"),
        "gate_ROUTE_built": meta["gate_ROUTE_built"]["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `BUILD_I2V_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "BUILD_I2V")

