"""Read a workflow graph and answer, in code, whether it can carry an experiment.

No bpy, no network, no numpy — it parses JSON and reports. Written because
`docs/license-map.md` and CLAUDE.md both say the same thing in different words:

> A `dry_run` PASS does not prove link sanity. Submit saved workflow files verbatim and
> check link topology in code before submission.

and the check was being done by eye. Three questions get asked of every graph before a
credit is spent, and each is a question a served template can silently answer wrong:

* **which weights does it actually load** — the licence gate's population. A template's
  title says nothing about the LoRA wired inside its subgraph, and the map's own ruling is
  that a *bypassed* non-commercial node still counts as present. So the answer comes from
  the node list, not from the name.
* **is every seed pinned** — Gate S. A `KSamplerAdvanced` whose `control_after_generate`
  reads `randomize` produces a run whose seed no committed list pre-registered, and E04's
  andon exists because a seed chosen after seeing a result turns a measurement of the
  between-generation floor into a selection of it.
* **is the frame generator-legal** — Gate L, derive-then-round. Every video model
  constrains resolution and frame count; the constraint is recorded per model here rather
  than remembered per session.

Nothing here spends anything, and nothing here is a matter of taste. It reports what the
graph contains; the rulings about what may run are the Director's and the advisor's.
"""

import datetime
import hashlib
import json

from .canon import GRAPH_WRAPPER_KEYS
from .errors import GateFailure

TOOL_VERSION = "E09.1"

#: The wrapper keys `normalise_graph` (and therefore every gate here, and `load_graph`)
#: unwraps, published under this module's own name so a caller outside the package reads
#: the SAME list the loader uses instead of re-typing a subset of it. It is
#: `canon.GRAPH_WRAPPER_KEYS` — one tuple, two names, no second implementation.
WRAPPER_KEYS = GRAPH_WRAPPER_KEYS

#: Generator constraints, per model family, from the spec that first used each. Wan's are
#: the ones E02 and E08 measured: both dimensions divisible by 16, frame count of the form
#: 4n+1, and a trained horizon of 81 frames beyond which the model was never trained.
#:
#: Family keys only here — G1 profile names (`wan-vace`, `wan-i2v`, …) resolve onto these
#: rows inside `frame_legality` (F-a9e809dd). Builders that already pass `family='wan'`
#: keep working unchanged; a caller that hands a profile name no longer gets a false
#: `unknown_generator_family` halt.
GENERATOR_RULES = {
    "wan": {"dim_multiple": 16, "frame_form": "4n+1", "max_frames": 81},
}

#: G1 profile name → family key in GENERATOR_RULES. Every current profile inherits Wan's
#: row; a new family gets its own RULES entry and a mapping here when G1 grows a profile.
PROFILE_FAMILY = {
    "wan-vace": "wan",
    "wan-fun-control": "wan",
    "wan-animate": "wan",
    "wan-i2v": "wan",
    "wan-fun-camera": "wan",
}

#: How old a licence ruling may be before `docs/license-map.md`'s own rule calls it
#: advisory. The map states the law in its header — "**Entries older than 90 days are
#: advisory until re-fetched** — licenses in this space change" — and CLAUDE.md repeats it
#: ("entries older than 90 days are advisory until re-fetched"). It is a NUMBER here, and
#: `fetched` is a FIELD on every row below, because a rule expressed only in prose cannot
#: be administered by the gate that applies the rulings.
LICENCE_ADVISORY_DAYS = 90

#: Components the repo has already ruled on, keyed by a substring of the file name. This is
#: a MIRROR of `docs/license-map.md`, not a second authority: the map is the record and
#: this is what lets a script fail on it. A component absent from this table is UNKNOWN,
#: which is reported, never silently treated as clean.
#:
#: ⚠ **Every row carries `fetched` and `source`, the two fields the map's own governing
#: rule is written in.** Measured 2026-09-05 before the fix: `verify()` on an API graph
#: loading the smartphone-snapshot LoRA returned a 29-key receipt in which
#: `json.dumps(ev)` contained none of `fetched`, `2026-08`, `stale`, `advisory` or `90`,
#: and the BANNED refusal on `causvid_x.safetensors` quoted verdict, licence and reason
#: and named no date and no document. The rows were fetched 2026-08-10 and 2026-08-13 and
#: go advisory 2026-11-08 and 2026-11-11; on that day every receipt and every refusal
#: would have read exactly as it did before, and neither the operator about to spend nor a
#: later reader of a stored receipt could tell an in-date ruling from a lapsed one — on the
#: gate CLAUDE.md calls non-negotiable. This module's own docstring sets the standard the
#: omission missed ("This is a MIRROR of `docs/license-map.md`, not a second authority"):
#: a mirror that omits the field the authority's rule is expressed in cannot administer
#: that rule.
#:
#: `source` is the URL of the fetched licence DOCUMENT, and it is `None` — never a
#: plausible-looking URL — on the three rows the map itself records as unretrieved
#: (`causvid` "not independently retrieved", `dwpose` weights "not fetched",
#: `vintage_film_grain` "source unlocated"). `fetched` on those three is the date the map
#: recorded the NON-retrieval, which is what an UNVERIFIED verdict is dated by.
#: **Whether a lapsed ruling also refuses is the Director's call, not this gate's** — the
#: gate says so in the sentence and in the receipt.
RULED_COMPONENTS = {
    "lightx2v": {
        "verdict": "EXCLUDED",
        "licence": "Apache-2.0 — commercially clean",
        "fetched": "2026-08-10",
        "source": "https://huggingface.co/lightx2v/Wan2.2-Lightning",
        "reason": ("excluded on METHODOLOGY grounds by the licence map, not on licence "
                   "grounds: a 4-step / cfg-1 distilled trajectory is a different sampler "
                   "trajectory from the one every other arm is measured on"),
    },
    "causvid": {
        "verdict": "BANNED",
        "licence": "CC-BY-NC",
        "fetched": "2026-08-10",
        "source": None,
        "reason": ("non-commercial; the map's ruling is delete, not bypass. Flagged by "
                   "Comfy consult #1 and NOT independently retrieved — the map records "
                   "the non-retrieval, and an unretrievable licence is treated as NO"),
    },
    "openpose": {"verdict": "BANNED", "licence": "CMU Academic / Non-Commercial",
                 "fetched": "2026-08-10",
                 "source": ("https://raw.githubusercontent.com/CMU-Perceptual-Computing-"
                            "Lab/openpose/master/LICENSE"),
                 "reason": "non-commercial preprocessor tier"},
    "dwpose": {"verdict": "BANNED", "licence": "weights not fetched",
               "fetched": "2026-08-10",
               "source": None,
               "reason": ("UNVERIFIED weights tier — treated as NO. The Apache row the "
                          "map carries is the CODE's; the WEIGHTS are a separate grant "
                          "and were never fetched")},

    # ---- the E14 style-LoRA field, mirrored from the licence map's 2026-08-13 fetch pass.
    # Four of these are kills. They are entered BECAUSE they are dead: an absent row reads
    # "NOT IN THIS TABLE", which is a shrug, and the point of a mirror is that naming a
    # gate-dead file in a graph halts instead of shrugging.
    "technically_color": {
        # ⚠ **CONDITIONAL, not ALLOWED — and the difference is machine-readable now.**
        # `docs/license-map.md:77` rules this file "YES — credit required", grounded in the
        # API-fetched CivitAI grant matrix (`allowNoCredit: false`), and states the
        # obligation in the map's own words: "published footage from this LoRA credits the
        # creator — a credits-line obligation riding the disclosure note". This row
        # mirrored that as an unconditional ALLOWED and buried CREDIT REQUIRED inside the
        # free-text `reason`, which no clause reads. Measured 2026-09-04 before the fix:
        # `rulings_for(...)[0]["verdict"]` was 'ALLOWED', `verify()` on a graph loading it
        # returned a clean verdict, and `[k for k in ev if 'cred' in k.lower()]` was `[]` —
        # so E14 arm T footage could be published uncredited with Gate ROUTE green and
        # nothing in the record that a human reviewing the spend could read the obligation
        # off. CLAUDE.md's licence gate names the vocabulary
        # `COMMERCIAL: YES / NO / CONDITIONAL(<condition>)` and rules that a CONDITIONAL is
        # a Director decision surfaced contrastively; the condition was accepted as the map
        # already records it (coordinator ruling, delegated by the Director 2026-09-04) and
        # becomes load-bearing HERE rather than in prose.
        #
        # `condition` is structured because a receipt has to be able to say what was owed
        # and whether it was paid. `verify` refuses a graph carrying this component unless
        # the SUBMITTING RECORD carries an `attribution` entry naming it and its creditor
        # (clause `uncredited_conditional_component`), and builders build that entry from
        # this row through `attribution_entry_for` rather than typing the words again.
        "verdict": "CONDITIONAL",
        "condition": {
            "kind": "credit",
            "creditor": "renderartist",
            "source": "CivitAI 2106471",
            "fetched": "2026-08-13",
            "text": "Technically Color LoRA by renderartist (CivitAI)",
        },
        "fetched": "2026-08-13",
        "source": "https://civitai.com/api/v1/models/2106471",
        "licence": "CivitAI grant matrix ['RentCivit', 'Rent', 'Image'], allowNoCredit false",
        "reason": ("E14 arm T. Third-party-service use and image-commercial both granted. "
                   "⚠ CREDIT REQUIRED: published footage from this LoRA credits renderartist. "
                   "The page's 'Apache 2.0' badge is the BASE MODEL's, not this file's — "
                   "reading it as the grant is a mistake this map made and corrected"),
    },
    "smartphonesnapshot": {
        "verdict": "ALLOWED",
        "fetched": "2026-08-13",
        "source": "https://civitai.com/api/v1/models/1834338",
        "licence": ("CivitAI grant matrix ['Image', 'RentCivit', 'Rent', 'Sell'], "
                    "allowNoCredit true, allowDerivatives true"),
        "reason": ("E14 arm S — the most permissive grant in the field. Served as a "
                   "tier-labelled HIGH/LOW pair; the HIGH file's doubled .safetensors "
                   "suffix is a Cloud provisioning artifact and is part of its served name"),
    },
    "candid_photography": {
        "verdict": "BANNED",
        "fetched": "2026-08-13",
        "source": "https://civitai.com/api/v1/models/1925758",
        "licence": "CivitAI grant matrix ['RentCivit'] ONLY",
        "reason": ("withdrawn from E14 before it ran. No image-commercial right and no "
                   "third-party-service right — both rights this route needs are withheld. "
                   "Its first YES was read off the base model's Apache badge"),
    },
    "80s_fantasy": {
        "verdict": "BANNED",
        "fetched": "2026-08-13",
        "source": "https://civitai.com/api/v1/models/789313",
        "licence": "CivitAI grant matrix ['RentCivit', 'Image'], allowDerivatives false",
        "reason": ("image-commercial granted but 'Rent' — third-party generation-service "
                   "use — is WITHHELD, and generation through Comfy Cloud is exactly that "
                   "use. Revival would take the creator's grant, not a re-fetch"),
    },
    "instareal": {
        "verdict": "BANNED",
        "fetched": "2026-08-13",
        "source": ("https://huggingface.co/Instara/instareal-wan-2.2/raw/main/"
                   "LICENSE.txt"),
        "licence": "Instara Fair Use License",
        "reason": ("prohibits use on any image/video generation service, platform or API; "
                   "this route IS that use. `instagirl` is the same house and inherits it"),
    },
    "instagirl": {
        "verdict": "BANNED",
        "fetched": "2026-08-13",
        "source": ("https://huggingface.co/Instara/instareal-wan-2.2/raw/main/"
                   "LICENSE.txt"),
        "licence": "Instara Fair Use License (same house as instareal)",
        "reason": "inherits the instareal row's verdict per the licence map",
    },
    "vintage_film_grain": {
        "verdict": "BANNED",
        "fetched": "2026-08-13",
        "source": None,
        "licence": "source unlocated — NOT RETRIEVED",
        "reason": ("a licence that cannot be retrieved is treated as NO. Revivable only if "
                   "a source page is found and fetched"),
    },
}

#: Node classes that carry a seed, and where it lives in `widgets_values`.
#:
#: `add_noise` is the third entry and it is per-class rather than assumed: `KSamplerAdvanced`
#: carries the switch as its first widget, and **`KSampler` has no such input at all** — it
#: always adds noise. Reading widget 0 for both (which this table let a caller do until
#: 2026-08-12) asks a `KSampler` whether its SEED equals "disable"; the answer is right for
#: the wrong reason on every graph, and would be wrong outright on a class whose first
#: widget happened to be a disabling literal.
#: ⚠ **A class absent from this table disarms Gate S silently.** E13's halt-era executor
#: measured exactly that and refused to record it as a pass: on a `wan2.7-r2v` graph
#: `seeds()` returned empty and `gate_s_registration` reported "0 noise-bearing seed(s),
#: all pinned" — a green verdict having checked nothing. The halt ruling (R6) ruled the
#: refusal correct and owed the row to **the first spec that arms this tier**, which is
#: E13's re-arm.
#:
#: `Wan2ReferenceVideoApi` is a hosted partner node, not a sampler: it carries no
#: `add_noise` input at all, so that entry is `None` for the same reason `KSampler`'s is.
#: Its save-format widget indices are **READ OFF the file the cloud converted**, 2026-08-13,
#: not derived — the standard the camera rows were held to. Both readings (the `get_node`
#: declaration order, and the converted file's own `widgets_values`) are recorded in the
#: E13 run report and required to agree.
SEED_NODES = {
    "KSampler": {"seed": 0, "control": 1, "add_noise": None},
    "KSamplerAdvanced": {"seed": 1, "control": 2, "add_noise": 0},
    "Wan2ReferenceVideoApi": {"seed": 6, "control": 7, "add_noise": None},
}

#: What a *hosted* tier constrains, where a local generator constrains pixels.
#:
#: ⚠ Gate L's `wan` rules describe a dim multiple of 16 and a 4n+1 frame count. **They do
#: not describe this tier at all** — `wan2.7-r2v` takes a resolution enum, a ratio enum and
#: an integer duration in seconds, and never receives a pixel dimension from us. Running the
#: pixel rules against it was the second vacuous gate the E13 halt report recorded, and the
#: halt ruling owed this table to the first spec that arms the tier. A check that cannot
#: fail is not a check.
#:
#: **This table is the sole hosted envelope (F-83facf0b).** `hosted_enums`,
#: `hosted_frame_legality`, and `verify(..., hosted_tier=)` all read it and nothing else.
#: A second hosted partner tier does not invent a parallel check: it adds a row here — with
#: every key in `HOSTED_TIER_ROW_KEYS` — in the same change that wires its builder. String
#: literals passed as `hosted_tier=` across the tree are censused by
#: `hosted_tier_string_literals`; every literal must be a key of this table.
HOSTED_TIER_ROW_KEYS = ("resolutions", "ratios", "duration_s", "measured")

HOSTED_TIER_RULES = {
    "wan2.7-r2v": {
        "resolutions": ("720P", "1080P"),
        "ratios": ("16:9", "9:16", "1:1", "4:3", "3:4"),
        "duration_s": (2, 10),
        "measured": ("get_node('Wan2ReferenceVideoApi'), 2026-08-12, re-measured "
                     "byte-consistent 2026-08-13"),
    },
}


def _assert_hosted_tier_table():
    """Every HOSTED_TIER_RULES row carries the envelope keys the legality clause reads."""
    for tier, row in HOSTED_TIER_RULES.items():
        if not isinstance(row, dict):
            raise RuntimeError(
                f"HOSTED_TIER_RULES[{tier!r}] must be a mapping of envelope keys; "
                f"got {type(row).__name__}")
        missing = [k for k in HOSTED_TIER_ROW_KEYS if k not in row]
        if missing:
            raise RuntimeError(
                f"HOSTED_TIER_RULES[{tier!r}] is missing required envelope key(s) "
                f"{missing}; every hosted tier records resolutions, ratios, "
                f"duration_s and measured in this one table")


_assert_hosted_tier_table()


def known_hosted_tiers():
    """Sorted names of hosted tiers that have an envelope row."""
    return sorted(HOSTED_TIER_RULES)


def hosted_tier_string_literals(paths):
    """Every string-literal `hosted_tier=` kwarg in the given Python source paths.

    Returns a list of `{"path", "lineno", "tier"}` rows. A suite (or builders pin) that
    wants every call site to name a RULES key filters `tier not in HOSTED_TIER_RULES`.
    Variable / attribute kwargs are invisible here by design — only literals can be
    checked without executing the call.
    """
    import ast
    import os

    rows = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg != "hosted_tier":
                    continue
                val = kw.value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    rows.append({"path": os.path.normpath(path), "lineno": node.lineno,
                                 "tier": val.value})
    return rows

#: Node classes that size a video latent, and where width/height/length live in save
#: format's positional `widgets_values`.
#:
#: ⚠ **A conditioning node can size a latent too, and forgetting that disarms Gate L
#: silently.** Added 2026-08-12 (E08): `WanAnimateToVideo` emits its own zeroed latent from
#: its own width/height/length inputs, so an Animate graph contains no `Empty*LatentVideo`
#: node at all — and this table drove `latents()`, which drove `frame_legality()`. On the
#: first E08 graph Gate L therefore examined ZERO latents and reported the graph legal
#: without checking anything, which is the failure mode CLAUDE.md names outright: a check
#: that cannot fail is not a check. Any future conditioning node that sizes a latent belongs
#: here the day it is first used.
#:
#: ⚠ **Adding a class to this table fixes one graph; it does not fix the shape of that
#: failure.** The next unrecorded latent-sizing node would disarm Gate L exactly the same
#: way, and this table can only ever be complete about nodes somebody already met. So the
#: gate no longer trusts the table to be complete: `verify` distinguishes "nothing was
#: checkable" from "everything checked out" and raises on the first (E08 closing ruling's
#: commission, shipped E10 2026-08-12).
#:
#: Widget order for `WanAnimateToVideo` is read from its `define_schema` declaration order,
#: keeping only the non-link inputs: width, height, length, batch_size,
#: continue_motion_max_frames, video_frame_offset.
#:
#: `WanImageToVideo` and `WanFirstLastFrameToVideo` were added 2026-08-12 (E11) under the
#: warning above — the day the first of them was used, not the day one of them broke
#: something. Both size their own latent from their own width/height/length exactly as
#: `WanAnimateToVideo` does, so an I2V graph likewise contains no `Empty*LatentVideo` node
#: at all. Widget order measured two ways and required to agree: `get_node`'s
#: `input_details` order (positive, negative, vae, width, height, length, batch_size) with
#: the link inputs dropped, and the served template's own `widgets_values` for that node,
#: `[640, 640, 81, 1]`. `WanFirstLastFrameToVideo` shares the declaration order and is
#: entered here now because it is the same object one socket wider — not used by E11.
#: `WanCameraImageToVideo` was added 2026-08-12 (E11 wave 2) under the same warning — the
#: day it was first used. It sizes its own latent from its own width/height/length exactly
#: as the three above do, so a camera-route graph likewise contains no `Empty*LatentVideo`
#: node at all, and leaving it out would have put Gate L back in the vacuous state E08
#: measured.
#:
#: ⚠ **Only ONE reading of its widget order was available, and that is recorded rather than
#: dressed up as two.** The convention above is to measure widget order two ways and require
#: agreement; here the second source does not exist. `get_node`'s `input_details` order
#: (positive, negative, vae, width, height, length, batch_size, then the optional
#: clip_vision_output / start_image / camera_conditions links) with the link inputs dropped
#: gives width, height, length, batch_size — the first reading. `search_templates` was
#: searched for a served workflow wiring this class on 2026-08-12 and **none of the 201
#: templates wires the Fun-Camera tier at all**, so no `widgets_values` reading exists to
#: check it against. The exposure is bounded: widget order is irrelevant in API format,
#: where inputs are keyed by name, and matters only when re-reading the SAVED file. So the
#: second reading is taken empirically there instead — `camera_widget_order_evidence`
#: reports the values standing at these indices on the converted file.
#:
#: ⚠ **The sentence that used to end this paragraph — "and the builder's saved-graph step
#: requires them to be the ones it set" — described a confirmation that was being taken by
#: a DIFFERENT implementation.** Measured by grep across the worktree on `e8263a3`: the
#: only references to `camera_widget_order_evidence` outside its own definition were four
#: in `tests/test_route_gates.py` (550-568); no builder and no gate called it, and the
#: saved-graph step reads `gate_saved_graph.WIDGET_INDEX` (`:41`, read at `:141`) — a
#: second copy of the same table. So the empirical second reading this note claims was
#: taken by code that does not read this table, and the function the note names was dead.
#: A clause with no caller is armed or deleted: `verify` is its production caller now (see
#: the andon near the end of that function), so every save-format graph that reaches Gate
#: ROUTE with a frame to check against records the values standing at these indices, and a
#: disagreement halts. Routed to builders as SEAM 5 §2: whether `WIDGET_INDEX`'s camera row
#: is retired in favour of this one is theirs to decide, in their own file.
LATENT_NODES = {
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2},
    "EmptyLatentVideo": {"width": 0, "height": 1, "length": 2},
    "WanVaceToVideo": {"width": 0, "height": 1, "length": 2},
    "WanAnimateToVideo": {"width": 0, "height": 1, "length": 2},
    "WanImageToVideo": {"width": 0, "height": 1, "length": 2},
    "WanFirstLastFrameToVideo": {"width": 0, "height": 1, "length": 2},
    "WanCameraImageToVideo": {"width": 0, "height": 1, "length": 2},
}

#: Nodes that solve a CAMERA TRAJECTORY from their own width/height/length. These do **not**
#: size the video latent — they emit a `WAN_CAMERA_EMBEDDING` — so they do not belong in
#: `LATENT_NODES`, and Gate L must not count them among the frames it checked. They get
#: their own table because of a failure mode nothing above can see.
#:
#: ⚠ **A camera embedding solved for a different frame than the one being generated passes
#: every other gate in this file.** Gate L would find the conditioning node's 832x480x65
#: legal and report a PROVEN frame; the seed clause would find every seed pinned; the
#: licence clause would find no banned weights. Meanwhile the trajectory steering the camera
#: would have been solved for, say, 81 frames, and the run would generate 65 frames of a
#: camera path computed for a clip a quarter longer — silently, with a clean receipt.
#: `WanCameraEmbedding` **defaults to length 81 while this route runs 65**, so the defect is
#: one omitted argument away rather than hypothetical. `verify` therefore checks agreement
#: rather than trusting that whoever wired the graph passed the same numbers twice.
#:
#: Widget order from `get_node` `input_details`, fetched 2026-08-12: camera_pose, width,
#: height, length, then the optional speed / fx / fy / cx / cy floats. Every input is a
#: literal — there are no link inputs to drop — so save-format indices are 1, 2, 3.
CAMERA_NODES = {
    "WanCameraEmbedding": {"width": 1, "height": 2, "length": 3},
}

#: Widget values that name a weight file. Anything ending in one of these is a component.
#:
#: ⚠ **It stopped being the licence walk's DENOMINATOR on 2026-09-05 (wave 25,
#: F-ebb1ebb4).** `components()` read `if not v.lower().endswith(WEIGHT_SUFFIXES):
#: continue` BEFORE `rulings_for` was ever consulted, so a hand-maintained tuple of seven
#: extensions decided which names the licence table was allowed to rule on. Measured in
#: this worktree on `580af47` on an API graph of `UNETLoader(wan2.2_t2v_high_noise_14B_
#: fp8_scaled.safetensors)` + `KSampler(seed 7, fixed)` + `LoraLoaderModelOnly(<name>)`:
#: with `causvid_x.safetensors` (BANNED, CC-BY-NC) `verify(g, frame=(832,480,81))` raised
#: naming the file; with the SAME file spelled `causvid_x.bin` — and identically with
#: `causvid_x`, `causvid_x.onnx` and `lightx2v_lora.bin` — `verify` RETURNED "0 of 1
#: component(s) classified, 1 unclassified, … 1 frame(s) checked and generator-legal",
#: `ev["unclassified"]` named only the `UNETLoader`, and `json.dumps(ev)` contained
#: "causvid" zero times. `rulings_for('causvid_x.bin')` returns the BANNED row: the ruling
#: existed and the walk never asked for it.
#:
#: The order is inverted now — **the table is asked first** (`_component_hits`), and this
#: tuple is only the predicate for "this UNRULED string looks like a weight file, so count
#: it as unclassified". A ruled name wearing an unrecorded suffix is refused BY NAME in
#: `verify` (`clause: ruled_name_with_unknown_suffix`) rather than dropped, so the
#: extension list can never again decide a licence verdict.
#:
#: `model_weights` (Gate PAIR) keeps reading this tuple, deliberately: its two readers fail
#: in OPPOSITE directions, and PAIR's is CLOSED — a diffusion model it cannot see leaves
#: `families_present` empty and PAIR raises INDETERMINATE or CONTRADICTED. The licence
#: walk's was the one that failed OPEN. `test_amend_w25_core_gates.py` pins that
#: `components()`' weight population is a SUPERSET of `model_weights`', so the two can no
#: longer diverge in the direction that matters.
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".sft", ".gguf", ".task")

#: Extra node-CLASS-NAME substrings that identify a `RULED_COMPONENTS` row, beyond the
#: row key itself. Lower-cased substring test, exactly as `rulings_for` matches a file.
#:
#: ⚠ **A banned tier can enter a graph as a NODE CLASS carrying no weight filename at
#: all.** Every clause of the licence gate read `widgets_values` for something ending in
#: a weight suffix, so a `DWPreprocessor` — the served Animate template's detector, whose
#: `dwpose` row in `RULED_COMPONENTS` reads BANNED / "weights not fetched" — contributed
#: nothing to `components()` and `verify()` reported the graph clean. The detector fetches
#: its own weights at run time; there is no filename in the graph for the file clause to
#: see. A licence row is not a wiring claim, and a wiring claim is not always a filename.
#:
#: This table only ADDS aliases: the row key is always a pattern, so a row absent here is
#: not silently exempt — it is matched on its own name. The two entries below are the
#: preprocessor tier, whose ComfyUI class names do not contain their row key
#: (`DWPreprocessor` does not contain "dwpose"). Measured against the served Animate
#: template, which wires `DWPreprocessor` and `OpenposePreprocessor`.
#:
#: ⚠ **The KEYS are `RULED_COMPONENTS` row keys, and nothing checked that they still name
#: rows.** `class_patterns_for` is only ever reached through `rulings_for_class`, which
#: iterates `RULED_COMPONENTS.items()` — so an alias entry whose key is no longer a row is
#: never consulted and never reported. Measured 2026-09-04: on a save-format graph
#: carrying one `DWPreprocessor`, `ruled_node_classes` returned one row (BANNED); renaming
#: the row key "dwpose" to "dwpose_ts" while leaving the alias under "dwpose" made
#: `ruled_node_classes` return [] and `class_patterns_for("dwpose_ts")` return only
#: ("dwpose_ts",) — the class clause silently fell back to matching the row key literally,
#: which is precisely the state this header describes as the defect the table was built to
#: close. The forward direction (every row matched on its own key) was pinned in the
#: suite; the reverse was pinned nowhere, and this table is a MIRROR of
#: docs/license-map.md, where a re-fetch renaming or retiring a row is a normal edit.
#: `gate_alias_table` is the mechanical form, and it runs at import and inside `verify`.
RULED_COMPONENT_CLASSES = {
    "dwpose": ("dwpreprocessor", "dwposeestimator"),
    "openpose": ("openposepreprocessor", "openpose_preprocessor"),
}

# =======================================================================================
# GATE PAIR — does the model this graph loads have a channel for the conditioning wired
# at it? Commissioned by the E11 wave-2 ruling (R3), 2026-08-12, and paid for by one
# generation of pure noise.
#
# **What happened, because the gate exists to stop it happening again.** Wave 2 wired
# `WanCameraImageToVideo` + `WanCameraEmbedding` — both core, both correctly schema-checked
# via `get_node` before building — over the plain Wan 2.2 I2V experts. The camera tier is a
# SEPARATE set of weights (`wan2.2_fun_camera_*`, a derivative of Wan2.2-I2V-A14B trained
# for camera synthesis). The base has no channel for a camera embedding. Every check in this
# file went green: the licence clause found no banned weights, Gate S found every seed
# pinned, Gate L proved 832x480x65, the camera/frame andon found the trajectory solved for
# the generated frame, the saved-file round trip compared 51 values and 23 links. The job
# succeeded. The frames contained no subject after f1.
#
# The suite checked everything about the graph except **whether the model could receive what
# was wired at it**, and no amount of care inside the other clauses would ever have caught
# it: they are all questions about the graph's internal consistency, and this graph was
# internally consistent. The missing question is about the relationship between two things
# each of which was individually correct.
#
# ⚠ **A licence row is not a wiring claim** (now also a CLAUDE.md law). The wave-2 dispatch
# said "weights mapped Apache" and that was TRUE — of weights the graph never loaded.

#: Weight-file substrings that identify a model family, lower-cased. A file may match more
#: than one and every match is recorded; the gate asks whether the REQUIRED family is among
#: those present, never whether it is the only one.
WEIGHT_FAMILIES = {
    "fun_camera": ("fun_camera", "fun-camera", "control_camera", "control-camera"),
    "fun_control": ("fun_control", "fun-control"),
    "vace": ("vace",),
    "animate": ("animate",),
    "phantom": ("phantom",),
    "i2v": ("i2v",),
    "t2v": ("t2v",),
}

#: Weight-file substrings that identify the GENERATOR family whose `GENERATOR_RULES` row
#: grades a frame — a DIFFERENT question from `WEIGHT_FAMILIES`, which answers "which
#: conditioning variant is this" (i2v / t2v / vace / fun_camera) for Gate PAIR.
#:
#: ⚠ **Gate L's generator family was ASSERTED by the caller and reconciled against
#: nothing.** `verify(graph, *, family='wan', ...)` forwards `family` straight to
#: `frame_legality`, whose `GENERATOR_RULES.get(family)` raises `unknown_generator_family`
#: only for a name absent from the table — and the table has exactly one row, so the
#: keyword default is always accepted and that refusal cannot fire on any caller that
#: leaves it alone. Measured 2026-09-05 in this worktree on `580af47`: nothing in `verify`,
#: `frame_legality` or `_frame_form` read `components()`, `model_weights()` or
#: `families_of()` when choosing the rules, and no map anywhere in the module took a loaded
#: weight name to a GENERATOR family. So the divisibility rule, the frame form and the
#: trained horizon a submission is graded on were chosen by an ARGUMENT rather than by the
#: model, and on the first non-wan route the receipt would name family 'wan' beside a
#: weight file that is not wan.
#:
#: The module already refuses the two sibling shapes of this question by name — an unknown
#: hosted tier (`unknown_hosted_tier`) and an unparseable frame form (`frame_form`, added
#: because "a second family declaring 8n+1 would have been graded on wan's temporal rule
#: while its own row said otherwise, and nothing would have printed differently").
GENERATOR_FAMILIES = {
    "wan": ("wan",),
}

#: Conditioning class -> the weight family the loaded model MUST belong to.
#:
#: `WanFirstLastFrameToVideo` pairs with `i2v` on the same grounds as `WanImageToVideo`: it
#: is the I2V conditioning shape one socket wider. It is entered here unused, deliberately —
#: the cost of a row is nothing and the cost of its absence is measured above.
CONDITIONING_WEIGHT_FAMILY = {
    "WanCameraImageToVideo": "fun_camera",
    "WanAnimateToVideo": "animate",
    "WanVaceToVideo": "vace",
    "Wan22FunControlToVideo": "fun_control",
    "WanFunControlToVideo": "fun_control",
    "WanPhantomSubjectToVideo": "phantom",
    "WanImageToVideo": "i2v",
    "WanFirstLastFrameToVideo": "i2v",
}

#: Conditioning classes that pair with NO diffusion-model family, recorded explicitly rather
#: than by omission. ControlNet appliers carry their own weights, which the licence clause
#: already populates; they attach to a base rather than requiring a variant of it.
#:
#: The two tables are exhaustive TOGETHER: `pairing` raises on a conditioning class it finds
#: in neither, so the next new class announces itself instead of slipping through. That is
#: the `gate_saved_graph` fail-closed pattern, which stopped this same wave twice.
CONDITIONING_FAMILY_EXEMPT = {
    "ControlNetApply", "ControlNetApplyAdvanced", "ControlNetApplySD3",
    "ACN_AdvancedControlNetApply",
}

#: Node classes that load the DIFFUSION MODEL — the thing that either has the channel or
#: does not. Deliberately not every loader: a VAE or a text encoder says nothing about
#: whether the denoiser was trained on camera conditions, and counting `wan_2.1_vae` or
#: `umt5_xxl` as evidence of a family would make this gate answer the wrong question.
MODEL_LOADER_CLASSES = ("UNETLoader", "CheckpointLoaderSimple", "CheckpointLoader",
                        "UnetLoaderGGUF", "DiffusersLoader")


class PairGate(GateFailure):
    """A conditioning node was wired at a model with no channel for it."""

    gate = "PAIR"


#: Class-name suffixes that mark a node as *conditioning a video model* — the role Gate
#: PAIR needs a row for. Matched by ROLE, not by vendor prefix.
#:
#: ⚠ The fail-closed clause used to read `startswith("Wan") and endswith("ToVideo")`,
#: which a class name disarmed outright: measured 2026-09-03, a graph loading
#: `wan2.2_t2v_high_noise.safetensors` and wiring `HunyuanImageToVideo` returned
#: "0 conditioning node(s) paired against 1 model file(s)" — green, with
#: `conditioning_nodes == []` — while renaming that same node `WanSomethingNewToVideo`
#: raised. The gate exists because a licence row is not a wiring claim; a gate that only
#: recognises one vendor's naming is a licence row of its own. The E11 wave-2 failure
#: (65 frames, no subject after f1, every other gate green) would repeat unseen on any
#: non-Wan tier, which the note at the head of `LATENT_NODES` already predicts.
CONDITIONING_CLASS_SUFFIXES = ("ToVideo", "ToVideoLatent")


def _looks_like_conditioning(cls):
    """Does this class name declare the conditioning role, whoever built it?"""
    return isinstance(cls, str) and cls.endswith(CONDITIONING_CLASS_SUFFIXES)


def families_of(filename):
    """Every family a weight filename matches, lower-cased substring test."""
    low = str(filename).lower()
    return sorted(fam for fam, pats in WEIGHT_FAMILIES.items()
                  if any(p in low for p in pats))


def generator_families_of(filename):
    """Every GENERATOR family a weight filename matches. See `GENERATOR_FAMILIES`."""
    low = str(filename).lower()
    return sorted(fam for fam, pats in GENERATOR_FAMILIES.items()
                  if any(p in low for p in pats))


def generator_family_reading(graph):
    """What the LOADED diffusion weights say Gate L's generator family is.

    Three answers, never two — the shape every other clause on this page has:

    * `PROVEN`     at least one loaded diffusion weight names a recorded generator family;
                   `families` lists them.
    * `INDETERMINATE` diffusion weights are loaded and none of their names matches any
                   recorded family. The reading cannot contradict the caller and says so.
    * `not_applicable` the graph loads no diffusion model this gate can read at all — the
                   assemblers' shape (`build_assembly_payload`, `build_cascade_payload`
                   call `verify(..., carries_no_sampler=True)` on LoadImage /
                   BatchImagesNode / CreateVideo / SaveVideo graphs).

    `verify` RAISES on a contradiction and RECORDS the other two. Why the unproven
    directions are recorded rather than refused, measured rather than preferred: on
    `580af47` the two assemblers above reach `verify` with `model_weights(graph) == []`,
    so an INDETERMINATE refusal would halt two production builders on correct work — and
    "an andon that fires on correct work is the andon nobody keeps" is this package's own
    rule (see `cover`'s prompt-population note). The direction the invariant does not bound
    is the CONTRADICTION: a weight naming a family the caller did not declare, graded on
    the caller's rules with a receipt naming the caller's family. That one raises.
    """
    loaded = model_weights(graph)
    rows = [{"file": w["file"], "node_id": w["node_id"], "class": w["class"],
             "where": w["where"], "generator_families": generator_families_of(w["file"])}
            for w in loaded]
    families = sorted({f for r in rows for f in r["generator_families"]})
    if not rows:
        verdict = "not_applicable — the graph loads no diffusion model this gate can read"
    elif not families:
        verdict = ("INDETERMINATE — none of the loaded diffusion weight names matches a "
                   "recorded generator family")
    else:
        verdict = "PROVEN — read off the loaded diffusion weight name(s)"
    return {"verdict": verdict, "families_read": families,
            "model_weights": rows, "recorded_families": sorted(GENERATOR_FAMILIES)}


def model_weights(graph):
    """Every DIFFUSION-model weight file the graph loads, with the families it matches."""
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        if n.get("type") not in MODEL_LOADER_CLASSES:
            continue
        for v in (n.get("widgets_values") or []):
            if isinstance(v, str) and v.lower().endswith(WEIGHT_SUFFIXES):
                out.append({"file": v, "node_id": n.get("id"), "class": n.get("type"),
                            "where": where, "families": families_of(v)})
    return out


def pairing(graph):
    """Gate PAIR · ANDON — every conditioning class is paired with a model that can take it.

    Raises when a graph wires a conditioning class whose required weight family is absent
    from the models it loads. Also raises, rather than passing quietly, when it cannot tell:
    a conditioning class it has never met, or a graph that wires one and loads no diffusion
    model this gate can read. "Nothing to check" and "everything checked out" are different
    verdicts here for the same reason they are in `verify`.
    """
    graph = normalise_graph(graph)
    loaded = model_weights(graph)
    present = sorted({fam for w in loaded for fam in w["families"]})
    # ⚠ **`where` — Gate PAIR's rows were the one row family on this page that never
    # carried it.** The comprehension read `for _, n in _iter_nodes(graph)` and discarded
    # the level the walk yields, beside `components`, `ruled_node_classes`,
    # `model_weights`, `seeds`, `latents`, `cameras` and `camera_widget_order_evidence`,
    # every one of which records `"where": where`. Measured 2026-09-05 in this worktree on
    # a save-format graph carrying a top-level `WanImageToVideo` id 3 and a blueprint
    # `WanImageToVideo` id 3: the CONTRADICTED refusal read "node 3 is WanImageToVideo ...;
    # node 3 is WanImageToVideo ..." and `conditioning_nodes` carried two rows keyed 3 and
    # 3 — the same duplicate-id tell the wave-18 Gate S fix removed from its own verdict
    # by printing `level/id`. Node identity in this walk is the PAIR `(where, id)`, because
    # blueprint ids are a separate namespace. No verdict was wrong (`missing` is computed
    # per row rather than by a lookup), so what this closes is the RECEIPT and the refusal
    # an operator reads.
    cond = [(where, str(n.get("id")), n.get("type")) for where, n in _iter_nodes(graph)
            if n.get("type") in CONDITIONING_WEIGHT_FAMILY
            or n.get("type") in CONDITIONING_FAMILY_EXEMPT]

    ev = {"gate": "PAIR", "andon": "PairGate",
          "model_weights": loaded, "families_present": present,
          "conditioning_nodes": [{"where": w, "node_id": i, "class": c,
                                  "requires": CONDITIONING_WEIGHT_FAMILY.get(c)}
                                 for w, i, c in cond]}

    unknown = sorted({n.get("type") for _, n in _iter_nodes(graph)
                      if _looks_like_conditioning(n.get("type"))
                      and n["type"] not in CONDITIONING_WEIGHT_FAMILY
                      and n["type"] not in CONDITIONING_FAMILY_EXEMPT})
    if unknown:
        ev["verdict"] = "INDETERMINATE"
        ev["clause"] = "unknown_conditioning_class"
        raise PairGate(
            f"conditioning class(es) {', '.join(unknown)} are in neither "
            f"CONDITIONING_WEIGHT_FAMILY nor CONDITIONING_FAMILY_EXEMPT, so this gate "
            f"cannot say whether the loaded model can receive them. Add a row rather than "
            f"letting a new class through — the class this gate was built for passed every "
            f"other check in this file", ev)

    required = [(w, i, c, CONDITIONING_WEIGHT_FAMILY[c]) for w, i, c in cond
                if c in CONDITIONING_WEIGHT_FAMILY]
    if required and not loaded:
        ev["verdict"] = "INDETERMINATE"
        ev["clause"] = "no_readable_model"
        raise PairGate(
            f"the graph wires {len(required)} conditioning node(s) "
            f"({', '.join(f'{w}/{i}' for w, i, _c, _f in required)}) but loads no "
            f"diffusion model this gate can read ({', '.join(MODEL_LOADER_CLASSES)}), so "
            f"the pairing is UNPROVEN. A check that cannot fail is not a check", ev)

    missing = [(w, i, c, fam) for w, i, c, fam in required if fam not in present]
    if missing:
        ev["verdict"] = "CONTRADICTED"
        ev["clause"] = "conditioning_family_absent"
        raise PairGate(
            "; ".join(
                f"node {w}/{i} is {c}, which requires a {fam!r} model, but the graph "
                f"loads {', '.join(x['file'] for x in loaded) or 'nothing'} "
                f"(families present: {present or 'none'})" for w, i, c, fam in missing) +
            ". Measured 2026-08-12: this exact pairing produced 65 frames with no subject "
            "after the first, and every other gate in this file passed on it", ev)

    ev["verdict"] = (f"{len(required)} conditioning node(s) paired against "
                     f"{len(loaded)} model file(s); families present {present}")
    return ev


class RouteGate(GateFailure):
    """A graph was about to run that the repo's own record says it must not."""

    gate = "ROUTE"


def _shape_of(doc):
    """`'api'`, `'save'`, or `None` when this mapping is neither. Decides nothing."""
    if not isinstance(doc, dict):
        return None
    if isinstance(doc.get("nodes"), list):
        return "save"
    if any(isinstance(v, dict) and "class_type" in v for v in doc.values()):
        return "api"
    return None


def _one_graph_declaration(doc):
    """The ONE wrapper key `doc` declares a graph under, or Gate ROUTE's refusal.

    Returns `None` when the mapping declares none — the ordinary "this is not an envelope"
    answer `normalise_graph` breaks its loop on.

    ⚠ **A document declaring TWO graphs was resolved by wrapper-key ORDER, and the second
    declaration was recorded nowhere.** `next((doc[k] for k in GRAPH_WRAPPER_KEYS if
    isinstance(doc.get(k), dict)), None)` takes the first of `('prompt', 'workflow_json',
    'workflow')` that is a mapping. Measured 2026-09-05 in this worktree on
    `{"prompt": <API graph, clean>, "workflow": <save-format graph loading
    causvid_x.safetensors>}` — the shape a ComfyUI queue/history record carries:
    `_shape_of(doc)` returned `None`, `components(doc)` returned only the API half's one
    weight, and `verify(doc, frame=(832,480,81))` RETURNED the verdict "0 of 1
    component(s) classified, ... 1 frame(s) checked and generator-legal" with the BANNED
    CC-BY-NC file named nowhere in the receipt and no key naming a second declaration.
    `load_graph` of the same document written to disk returned a graph equal to the API
    half. Reversing the two keys in the document changed nothing: the TUPLE is the
    selector, not dict order, so this is not a shape a caller can spell around.

    Bounded as the auditor filed it: `gate_saved_graph.round_trip(api, load_graph(<that
    file>))` still refused with `SavedAdmission` "the saved graph argument is not a
    save-format graph", so what was open is any caller handing such a document straight to
    `verify` / `components` / `is_api_format`, and the receipt's silence about the choice.

    It REFUSES rather than recording the choice, which is what this module does with
    ambiguity everywhere else in exactly this family: `duplicate_subgraph_id` and
    `duplicate_subgraph_label` here, `duplicate_link_id` and `duplicate_socket_name` in
    `gate_saved_graph.link_table`, `node_map_duplicate_id` in `fetch_run.parse_node_map`.
    Two declarations are two different graphs and one of them is what would run.
    """
    declaring = [k for k in GRAPH_WRAPPER_KEYS if isinstance(doc.get(k), dict)]
    if not declaring:
        return None
    if len(declaring) > 1:
        raise RouteGate(
            f"this document declares {len(declaring)} graphs — {declaring!r} — and the "
            f"loader would have taken {declaring[0]!r} by the order of "
            f"{list(GRAPH_WRAPPER_KEYS)}, reading nothing at all from the other(s). Two "
            f"declarations are two different graphs and one of them is what runs; a "
            f"licence, seed and frame walk that reads one of them reports a verdict about "
            f"a graph the submission may not carry",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "multiple_graph_declarations",
             "declaring_keys": declaring, "would_have_taken": declaring[0],
             "wrapper_keys": list(GRAPH_WRAPPER_KEYS),
             "top_level_keys": sorted(map(str, doc)),
             "shapes": {k: _shape_of(doc[k]) for k in declaring}})
    return declaring[0]


def normalise_graph(graph):
    """THE loader. Every gate in this module reads its graph through this one function.

    Returns the graph in the shape the walk understands — API format (node-id keyed,
    `class_type` per value) or save format (a `nodes` list) — unwrapping a submission
    envelope named in `canon.GRAPH_WRAPPER_KEYS` when it finds one, and RAISING
    `RouteGate` on a mapping it cannot recognise at all.

    ⚠ **"This graph has no nodes" and "I cannot read this shape" were the same answer,
    and the second one arrived under a green receipt.** Measured 2026-09-03 on the
    standard ComfyUI submission envelope `{"prompt": <api graph>}` wrapping a graph that
    loads `causvid_x.safetensors` (BANNED, CC-BY-NC) and a `KSamplerAdvanced` at
    noise_seed 999999: bare, `verify(g, frame=(832, 480, 81))` raised naming the banned
    file; wrapped, `components()`, `seeds()` and `latents()` all returned `[]` and
    `verify` returned "0 weight file(s), 0 seed(s) all pinned, 0 of 0 latent(s)
    checkable, 1 frame(s) checked and generator-legal", with pairing reporting "0
    conditioning node(s) paired against 0 model file(s)". `gate_s_registration(wrapped,
    [7])` likewise reported every seed pinned and registered. Gate ROUTE reported a graph
    clean on licence, seeds and pairing having read zero nodes.

    (The quoted verdict is the 2026-09-03 measurement and is left as measured. **Dated
    note, 2026-09-05:** the licence half of that string is no longer spelled
    `"{n} weight file(s)"` — wave 12 replaced it with the three-number form
    `"{classified} of {n} component(s) classified, {u} unclassified, {c} conditional
    (credited), {a} attribution entr(y|ies) matching no loaded component"`, because a count
    of what was LOOKED AT with no count of what was CLASSIFIED made "every component is
    ruled clean" and "the table classified none of them" the same receipt. The seed, latent
    and frame clauses of the quote are unchanged. Routed here from builders' F-c222d9ba,
    whose own two copies of the stale quote carry the same dated note.)

    This is verbatim the fix wave 3 applied to `canon.texts_from_api_graph` — "'No text
    here' and 'I did not recognise this shape' are different answers" — carried into the
    module where the spend gates live, as ONE loader rather than a second implementation:
    the wrapper-key tuple is `canon.GRAPH_WRAPPER_KEYS`, so the comment beside it and the
    behaviour here cannot drift apart again.
    """
    doc = graph
    for _ in range(len(GRAPH_WRAPPER_KEYS) + 1):
        if _shape_of(doc) is not None:
            return doc
        inner = None
        if isinstance(doc, dict):
            # · ANDON — TWO declarations, before either is taken. See
            # `_one_graph_declaration`; the selector is this tuple and not dict order, so
            # reversing the keys in the document changes nothing and the ambiguity is not
            # a property a caller can spell their way out of.
            declaring = _one_graph_declaration(doc)
            inner = doc[declaring] if declaring is not None else None
        if inner is None:
            break
        doc = inner
    raise RouteGate(
        f"this is not a graph this module can read: a {type(doc).__name__} that is "
        f"neither API format (node-id keyed values carrying `class_type`) nor save "
        f"format (a `nodes` list), and that carries no wrapper key from "
        f"{list(GRAPH_WRAPPER_KEYS)}. A shape that cannot be read is not an empty "
        f"graph, and every clause of this module would otherwise report its "
        f"zero-population verdict as a pass",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_shape",
         "type": type(doc).__name__,
         "top_level_keys": sorted(map(str, doc)) if isinstance(doc, dict) else None,
         "wrapper_keys": list(GRAPH_WRAPPER_KEYS)})


def is_api_format(graph):
    """API format is node-id keyed with `class_type`; save format has a `nodes` array.

    Reads through `normalise_graph`, so an unrecognised shape raises here too rather
    than answering `False` and sending the caller down the save-format branch to walk a
    `nodes` list that does not exist.
    """
    return _shape_of(normalise_graph(graph)) == "api"


def _iter_nodes(graph):
    """Every node in the graph, read through `normalise_graph`. See `_walk_nodes`."""
    return _walk_nodes(normalise_graph(graph))


def _walk_nodes(graph):
    """Every node in the graph, INCLUDING the ones inside subgraph definitions.

    The clause that matters. A served template can present four nodes at the top level and
    hide thirty inside a subgraph blueprint, and a check that walked only the top level
    would report a clean graph while the excluded LoRA sat two levels down. Measured on
    `video_wan2_2_14B_t2v`, 2026-08-11: 4 nodes visible, 30 hidden.

    Yields `(where, node)` with the node normalised to `{id, type, widgets, inputs}`, so
    the same three questions can be asked of a hand-built API graph and of a served
    save-format one. **Both formats matter here**: we build in API format and the cloud is
    handed a saved file, so the gate has to be able to read what we wrote AND what came
    back.

    ⚠ **The recursion is the clause, not the loop.** Until 2026-09-03 this walked
    `definitions.subgraphs[*].nodes` and stopped, so a definition carrying its own
    `definitions` hid everything inside it. Measured: a graph whose outer subgraph
    contains a nested subgraph holding a `LoraLoaderModelOnly` for `causvid_x.safetensors`
    returned `['base.safetensors', 'clean.safetensors']` from `components()` — the BANNED
    file two levels down was missed and `verify` would have reported the graph clean.
    That is this function's own docstring one level further down. NOT measured: whether
    Comfy's served save format ever nests definitions rather than hoisting them, so this
    closed a hole in the walk rather than a demonstrated escape. A recursion PATH keyed on
    OBJECT identity stands against a blueprint that references itself: the gate before a
    spend must halt or answer, never hang. (This used to read "a `visited` set of
    definition ids". It was a set keyed on the blueprint's `id` VALUE, it was doing double
    duty as a dedup, and it dropped the second of two blueprints declaring one id — see
    `_iter_definitions`, which now separates the cycle guard from the ambiguity refusal.)
    """
    if _shape_of(graph) == "api":
        for node_id, node in graph.items():
            # · ANDON — see `_api_entry_kind`. A dict that is node-shaped and carries no
            # `class_type` is a node whose class was lost, and it used to be dropped by a
            # bare `continue` on the format every builder submits.
            if _api_entry_kind(node_id, node, graph) == "metadata":
                continue
            # · ANDON — the node's own container, before `.values()` is called on it. See
            # `_readable_containers`: a list here used to raise a bare `AttributeError`,
            # which is not an `ArmatureError` and so bypasses the halt contract entirely.
            _readable_containers("api", node, population=len(graph), api=True,
                                 node_id=node_id)
            inputs = node.get("inputs") or {}
            # A link is [node_id, slot]; anything else is a literal this graph pins.
            widgets = [v for v in inputs.values() if not isinstance(v, list)]
            # ⚠ **An API entry that declares its OWN `widgets_values` had it DISCARDED.**
            # This branch synthesised the node's widgets from `inputs.values()` alone and
            # `NODE_CONTAINERS[True]` recorded only `("inputs", dict)`, so a value spelled
            # there was neither read nor refused. Measured 2026-09-05 in this worktree on
            # an API graph of `UNETLoader(wan2.2_t2v_high_noise_14B_fp8_scaled)` +
            # `KSampler(seed 7, fixed)` + `{"class_type": "LoraLoaderModelOnly",
            # "inputs": {}, "widgets_values": ["causvid_x.safetensors", 1.0]}` (BANNED,
            # CC-BY-NC): `components()` named ONLY the UNETLoader, `verify(g,
            # frame=(832,480,81))` RETURNED "0 of 1 component(s) classified, 1
            # unclassified, ... 1 frame(s) checked and generator-legal",
            # `json.dumps(ev)` contained "causvid" zero times, and `walk_census.
            # n_nodes_walked` read 3. The control — the same file spelled in the API
            # `inputs` mapping — raised naming it. That is the wave-20 CRITICAL
            # F-f9ab0645 one container over, on the format every builder submits.
            #
            # It is READ rather than refused, because a converter that emits `class_type`
            # beside `widgets_values` is producing a node whose values ARE pinned and the
            # honest reading is to test them; the SHAPE is refused instead, by the
            # `widgets_values` row now in `NODE_CONTAINERS[True]`, so a mapping or a bare
            # string here meets `unreadable_node` exactly as it does in save format.
            # The `inputs` literals keep the positions they had, and the declared values
            # are appended: nothing in API format is positional (every reader keys inputs
            # by NAME — see `seeds`, `latents`, `cameras`, `hosted_enums`), so the union
            # adds a population to the weight and class readers without moving an index.
            declared = node.get("widgets_values") or []
            yield ("api", {"id": node_id, "type": node["class_type"],
                           "widgets_values": widgets + list(declared),
                           "inputs": inputs})
        return
    for i, n in enumerate(graph.get("nodes") or []):
        # · ANDON — the save-format branch used to yield whatever the array held, and it
        # is the ONE of the three node sources that guarded nothing: the API branch skips
        # a non-dict (`if not isinstance(node, dict) or "class_type" not in node`) and
        # `_iter_definitions` skips a non-dict definition. Measured 2026-09-04 in this
        # worktree: `components({"nodes": ["x"]})` raised
        # `AttributeError: 'str' object has no attribute 'get'`, `{"nodes": [None]}` the
        # same, and one stray entry beside a well-formed `UNETLoader` took the whole
        # licence, seed and frame walk with it. `AttributeError` is not an `ArmatureError`,
        # so the halt contract's exit-2 receipt branch — the six-key `<TOOL>_HALT` line;
        # this comment used to name the deleted `GATE_FAILURE` + `GATE_EVIDENCE` pair, and
        # the citation is corrected here — was BYPASSED and the run was classified as an
        # unhandled error rather than as
        # Gate ROUTE refusing a shape it cannot read — which is exactly what `load_graph`'s
        # docstring and `normalise_graph`'s refusal clause promise for this input class.
        #
        # It RAISES rather than skipping, matching `normalise_graph`'s stance that an
        # unreadable shape is not an empty graph: a skipped node is a node no clause
        # examined, and this file's whole argument is that "nothing was checkable" and
        # "everything checked out" may not be the same verdict. `load_graph` reads the
        # save-format file the cloud converted and handed back, and any operator-supplied
        # `--saved` file; a JSON null or a string inside `nodes` is an ordinary converter
        # or hand-edit artifact, not an exotic input.
        yield ("top", _readable_node("top", n, i, len(graph.get("nodes") or [])))
    yield from _iter_definitions(graph, set(), {})


#: Top-level keys an API-format submission legitimately carries BESIDE its nodes. The
#: standard ComfyUI envelope writes `last_node_id` / `last_link_id` / `version` beside the
#: node map, `extra_data` and `extra_pnginfo` ride a saved prompt, and `client_id`,
#: `prompt_id` and `number` ride a queue record. F-85d2b7a3 made the walk tolerate them;
#: this names WHICH, so tolerance stops being "anything the walk did not recognise".
API_ENVELOPE_KEYS = ("client_id", "extra_data", "extra_pnginfo", "last_link_id",
                     "last_node_id", "number", "prompt_id", "version")


def _api_entry_kind(key, value, graph=None):
    """`"node"` or `"metadata"` for one top-level API entry, or Gate ROUTE's refusal.

    ⚠ **The two node sources answered a malformed entry with opposite verdicts, and the
    API branch — the format every builder submits — was the one that skipped in silence.**
    Save format raises: `_readable_node` refuses a non-dict entry with `unreadable_node`,
    and `_iter_definitions` refuses an unreadable container, both on the stated ground
    that "a skipped node is a node no clause examined, and this file's whole argument is
    that 'nothing was checkable' and 'everything checked out' may not be the same
    verdict". The API branch read `if not isinstance(node, dict) or "class_type" not in
    node: continue` — and nothing anywhere counted what it dropped.

    Measured 2026-09-04 in this worktree on an API graph of `UNETLoader` + `KSampler` +
    a `LoraLoaderModelOnly` carrying `causvid_x.safetensors` (BANNED, CC-BY-NC): with
    `class_type` present, `verify(g, frame=(832,480,81))` raised naming the banned file;
    with the `class_type` key removed from that ONE node and everything else identical,
    `components()` returned only the UNETLoader's weight and `verify` RETURNED "0 of 1
    component(s) classified, 1 unclassified, ... 1 frame(s) checked and generator-legal",
    with no key in the receipt recording that a mapping entry existed and was not read.
    The same stray in save format raises `unreadable_node`.

    The skip is not gratuitous — an API graph legitimately carries non-node top-level
    metadata, which is why F-85d2b7a3 made the walk tolerate it. So the split is by SHAPE
    rather than by tolerance: a value that is not a dict is metadata; a dict under one of
    the named `API_ENVELOPE_KEYS` is metadata; a dict under any other key with no
    `class_type` is a node whose class was lost, and it raises the SAME `unreadable_node`
    clause both formats now answer with. Whatever stays skipped is counted and named by
    `api_walk_census`, so the licence clause's `of {len(comp)}` denominator can be
    reconciled against what the walk entered.

    Bounded honestly: the seven `build_*_payload` tools construct their API graphs
    in-repo with `class_type` on every node, so this was the guard direction unbounded
    rather than a demonstrated escape. The input class is a builder, a converter or a
    hand-edit that loses one node's class.
    """
    if not isinstance(value, dict):
        return "metadata"
    if "class_type" in value:
        return "node"
    if str(key) in API_ENVELOPE_KEYS:
        return "metadata"
    raise RouteGate(
        f"this API-format graph carries a mapping at key {str(key)!r} with no "
        f"`class_type` and no envelope meaning: {sorted(map(str, value))!r}. That is a "
        f"node whose class was lost, not submission metadata — a licence, seed and frame "
        f"walk cannot read it, and skipping it would leave a node no clause examined "
        f"inside a graph reported clean. The envelope keys this walk tolerates are "
        f"{list(API_ENVELOPE_KEYS)}",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_node",
         "where": "api", "key": str(key), "index": None,
         "entry_type": type(value).__name__, "entry": repr(value),
         "entry_keys": sorted(map(str, value)),
         "envelope_keys": list(API_ENVELOPE_KEYS),
         "n_nodes": len(graph) if isinstance(graph, dict) else None})


def api_walk_census(graph):
    """What `_walk_nodes` entered and what it skipped, on an API-format graph.

    `None` on save format, because a census reporting zero skipped keys about a branch
    that never ran is a number about a walk that did not happen — the same reason
    `camera_widget_order_evidence` answers `not_applicable` rather than PASS.

    Written because the count was the half of F-7eb1ba2a that the refusal alone does not
    close: `verify`'s licence clause states `{classified} of {len(comp)}`, and until this
    existed there was no way to reconcile that denominator against the population the walk
    entered. Refuses on the same clause `_api_entry_kind` does, so the census and the walk
    cannot disagree about what a node is.
    """
    graph = normalise_graph(graph)
    if _shape_of(graph) != "api":
        return None
    kinds = [(str(k), _api_entry_kind(k, v, graph)) for k, v in graph.items()]
    skipped = sorted(k for k, kind in kinds if kind == "metadata")
    return {"format": "api", "n_top_level_values": len(kinds),
            "n_nodes_walked": sum(1 for _, kind in kinds if kind == "node"),
            "n_skipped_non_node_keys": len(skipped),
            "skipped_non_node_keys": skipped,
            "envelope_keys": list(API_ENVELOPE_KEYS)}


def _readable_node(where, n, index, population):
    """`n` if it is a node this walk can read, else Gate ROUTE's `unreadable_node`.

    ⚠ **The guard used to live inline in the save-format top-level loop and nowhere
    else**, which is the wave-12 fix landing one LEVEL away from the hole its own comment
    calls "the clause, not the loop": `_iter_definitions` guarded the DEFINITION dict and
    yielded whatever its `nodes` array held. Measured 2026-09-04 on a save-format graph
    carrying one well-formed `UNETLoader` plus a subgraph definition whose `nodes` array
    holds a string or a JSON null, `components()`, `seeds()`, `latents()` and `verify()`
    all raised `AttributeError: 'NoneType' object has no attribute 'get'`, while the SAME
    stray entry at the top level raised `RouteGate` with `clause: unreadable_node`.

    `AttributeError` is not an `ArmatureError`, so the halt contract's exit-2 /
    six-key `<TOOL>_HALT` receipt branch is bypassed and the run is classified
    as an unhandled crash rather than as Gate ROUTE refusing a shape it cannot read. The
    input class is the one `load_graph` is pointed at — the save-format file the cloud
    converted and handed back, or an operator's `--saved` file — and a converter or a
    hand-edit that leaves a null inside a subgraph blueprint is ordinary, not exotic.
    Definitions are walked in SAVE format only (the API branch returns early), which is
    exactly the format this path reads.

    One implementation, both call sites, so the two levels cannot drift apart again;
    `where` names which one, and it is the definition's own name or id for a nested node.

    ⚠ **It guarded the node ENTRY and left the node's OWN CONTAINERS unguarded** — the
    level below the one wave 18 closed for `definitions` / `definitions.subgraphs` and the
    one wave 14 closed for the `nodes` array. Every weight read on this page is
    `for v in (n.get("widgets_values") or [])` (`components`, `model_weights`), which
    iterates the KEYS of a mapping and the CHARACTERS of a string, so no value inside
    either shape is ever tested against `WEIGHT_SUFFIXES`. Measured 2026-09-05 in this
    worktree on a save-format graph of `UNETLoader` + pinned `KSampler` +
    `WanImageToVideo(832,480,81,1)` + a `LoraLoaderModelOnly` carrying
    `causvid_x.safetensors` (BANNED, CC-BY-NC): with `widgets_values` as the ordinary LIST
    `components()` returned that file with verdict BANNED and `verify(g)` raised naming
    it; with the SAME node's `widgets_values` spelled as the mapping
    `{"lora_name": "causvid_x.safetensors", "strength_model": 1.0}`, and again as the bare
    string `"causvid_x.safetensors"`, `components()` returned only the `UNETLoader`'s
    weight and `verify(g)` RETURNED "0 of 1 component(s) classified, 1 unclassified, …
    1 frame(s) checked and generator-legal". No key in the receipt recorded that a node's
    widget container had been entered and read as empty.

    The node's `inputs` is guarded on the same clause because the converted-widget reading
    the shift andons rest on is taken from it: `_save_format_input_names` and
    `_save_format_converted_widget_names` iterate `node.get("inputs") or []`, and a mapping
    there yields its string keys, every one of which fails `isinstance(slot, dict)` — so
    the answer "this node has no converted widgets" is returned about a container nobody
    read. `None` and an absent key stay the ordinary spelling of "no widgets" / "no
    inputs", exactly as an absent `definitions` stays the spelling of "no blueprints".

    NOT MEASURED, and stated as this module states its siblings: whether Comfy's own
    exporter ever emits a non-list `widgets_values`. The input class is the one
    `load_graph`'s docstring names — the save-format file the cloud converted and handed
    back, an operator's `--saved` file, a converter or a hand-edit artifact.
    """
    if not isinstance(n, dict):
        raise RouteGate(
            f"this graph's save-format `nodes` array holds a "
            f"{type(n).__name__} at index {index} ({n!r}), which is not a node "
            f"(in {where!r}). A licence, seed and frame walk cannot read it, and skipping "
            f"it would leave a node no clause examined inside a graph reported clean",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_node",
             "index": index, "entry_type": type(n).__name__, "entry": repr(n),
             "where": where, "n_nodes": population})
    # · ANDON — the node's own containers, on the level the wave-14 fix did not reach.
    _readable_containers(where, n, index=index, population=population, api=False)
    return n


#: What each node container is spelled as, per format. Save format spells `inputs` as a
#: LIST of slot dicts (`{"name", "type", "link"}`, plus `{"widget": {...}}` on a converted
#: widget) and `widgets_values` as a LIST of positional values; API format keys `inputs` by
#: NAME and carries no `widgets_values` at all — `_walk_nodes` synthesises one from the
#: literal inputs, so only `inputs` is read there.
#: The "caller said nothing" sentinel, distinct from a node id that is legitimately `None`.
_UNSET = object()

NODE_CONTAINERS = {
    False: (("widgets_values", list, "a list of widget values"),
            ("inputs", list, "a list of save-format input slots")),
    # ⚠ `widgets_values` joined the API row 2026-09-05 (F-ddfb61e6). The comment above
    # read "API format ... carries no `widgets_values` at all", and that is what the
    # standard envelope carries — but a converter or a hand-edit that emits `class_type`
    # BESIDE a `widgets_values` array produced a node whose declared values were neither
    # read by the walk nor refused by this table, and a BANNED weight inside one reached
    # a green `verify`. `_walk_nodes` now unions the declared values into the widgets it
    # synthesises from the literal inputs, and this row is what refuses the container
    # shapes that cannot be read (a mapping yields its KEYS, a string its CHARACTERS).
    True: (("inputs", dict, "a mapping of API input name to literal-or-link"),
           ("widgets_values", list, "a list of widget values")),
}


def _readable_containers(where, node, *, index=None, population=None, api=False,
                         node_id=_UNSET):
    """Gate ROUTE's `unreadable_node`, raised for a node's OWN container.

    One implementation, both formats and both save-format call sites, for the reason
    `_unreadable_level` gives one level up: a reader keyed on the clause has one question —
    *did this walk enter everything it reported on?* — and three spellings of the answer
    would be three things to remember. `container` names which one and `entry_type` carries
    the shape that arrived, so the receipt says what was refused rather than only that
    something was.

    The API half is the same defect wearing the crash hat. `_walk_nodes`' API branch reads
    `inputs.values()`, so an `inputs` spelled as a LIST raised a bare
    `AttributeError: 'list' object has no attribute 'values'` — measured 2026-09-05 on the
    API mirror of the graph in `_readable_node`'s note. An `AttributeError` is not an
    `ArmatureError`, so the halt contract's exit-2 six-key `<TOOL>_HALT` branch is bypassed
    and Gate ROUTE refusing a shape it cannot read is recorded as an unhandled crash.

    `node_id` is passed explicitly by the API branch, where a node's id is the MAPPING KEY
    and never a field inside the entry — an evidence record naming `None` as the operand
    would name nothing an operator could find in the file.
    """
    if node_id is _UNSET:
        node_id = node.get("id")
    for name, shape, expected in NODE_CONTAINERS[bool(api)]:
        value = node.get(name)
        if value is None or isinstance(value, shape):
            continue
        raise RouteGate(
            f"this graph's node {node_id!r} (in {where!r}) carries a "
            f"{type(value).__name__} as its `{name}` ({value!r}), which is not "
            f"{expected}. Every clause on this page reads that container by iterating or "
            f"indexing it, and a mapping yields its KEYS while a string yields its "
            f"CHARACTERS — so a weight, a seed or a frame count inside it is tested "
            f"against nothing and the node is reported clean having been read as empty",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_node",
             "container": name, "expected": expected, "where": where,
             "node_id": node_id, "class": node.get("type"),
             "entry_type": type(value).__name__, "entry": repr(value),
             "index": index, "n_nodes": population})


def _unreadable_level(where, value, expected, index=None, population=None, extra=None):
    """Gate ROUTE's `unreadable_node`, raised for a CONTAINER rather than for an entry.

    One clause across every level of the save-format walk, because a reader keyed on the
    clause has one question — *did this walk enter everything it reported on?* — and three
    spellings of the answer would be three things to remember. `where` names the level
    (`"definitions"`, `"definitions.subgraphs"`) exactly as it names the blueprint for an
    entry, and `entry_type` carries the shape that arrived.
    """
    ev = {"gate": "ROUTE", "andon": "RouteGate", "clause": "unreadable_node",
          "index": index, "entry_type": type(value).__name__, "entry": repr(value),
          "where": where, "n_nodes": population, "expected": expected}
    if extra:
        ev.update(extra)
    raise RouteGate(
        (f"this graph's {where} holds a {type(value).__name__} at index {index} "
         f"({value!r}), which is not {expected}"
         if index is not None else
         f"this graph's {where} is a {type(value).__name__} ({value!r}), which is not "
         f"{expected}") +
        ". A licence, seed and frame walk cannot enter a container it cannot read, and "
        "reading past it would leave every node inside it unexamined inside a graph "
        "reported clean", ev)


#: The level labels `_walk_nodes` emits for the graph's OWN node sources. A blueprint may
#: not declare one of them, because node identity in this walk is the pair `(where, id)`
#: and a blueprint named `top` puts its nodes in the top level's namespace.
#:
#: `api` cannot collide inside a single graph today — `_walk_nodes`' API branch returns
#: before `_iter_definitions` runs — and it is recorded here explicitly rather than by
#: omission, the way `CONDITIONING_FAMILY_EXEMPT` records the conditioning classes that
#: pair with no model family.
RESERVED_LEVEL_LABELS = {
    "top": {"what": "the save-format graph's own top-level `nodes` array"},
    "api": {"what": "an API-format graph's node map"},
}


def _iter_definitions(container, path=None, declared=None):
    """Every node inside `container`'s subgraph definitions, to any depth.

    ⚠ **The cycle guard was keyed on the blueprint's `id` VALUE, so a duplicate id
    silently dropped the second blueprint.** The loop read
    `key = id(d) if d.get("id") is None else ("id", d["id"])` followed by
    `if key in visited: continue`, so two DISTINCT definitions declaring one id collapsed
    to one and every node inside the second was never walked by any clause in this module.
    A duplicate id is not a cycle: the guard's own docstring stands against "a blueprint
    that references itself", and it was doing double duty as a dedup over a field nothing
    validates. Measured 2026-09-04 in this worktree on a save-format graph with
    `definitions.subgraphs` holding two definitions BOTH with `id: "bp"` — the first
    (`name: "first"`) carrying `clean_style.safetensors`, the second (`name: "second"`)
    carrying `causvid_x.safetensors` (BANNED, CC-BY-NC): `components()` returned only
    `['wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors', 'clean_style.safetensors']` and
    `verify(g, frame=(832,480,81))` RETURNED GREEN. Two controls: renaming the second
    blueprint `bp2` raised naming the banned file, and deleting `id` from BOTH (so the
    `id(d)` object-identity fallback was used) also found it.

    **The two jobs are separated.** Cycle protection is the recursion PATH — a set of
    OBJECT identities added on the way down and removed on the way back up — so a
    blueprint that references itself is entered once and terminates, and a blueprint
    legitimately reachable from two different parents is still walked. Ambiguity is a
    REFUSAL by name: `duplicate_subgraph_id`, worded from the precedent this module
    already sets one level over. `gate_saved_graph.link_table` raises `duplicate_link_id`
    because "a file that is ambiguous about where its conditioning comes from is not a
    file this gate can vouch for", and `fetch_run.parse_node_map` raises
    `node_map_duplicate_id` citing it; the blueprint-id table is the third member of that
    family and was the one that silently dropped instead.

    NOT MEASURED: whether Comfy's exporter ever emits duplicate blueprint ids. The input
    class is the one `load_graph` documents — an operator's `--saved` file, a converter or
    hand-edit artifact, or two workflows merged — so this closed the guard direction that
    was unbounded rather than a demonstrated escape. The id is compared as `str(bid)`,
    which is the strict direction: a file declaring `1` and `"1"` is ambiguous about which
    runs, and refusing is the answer this module gives to ambiguity everywhere else.

    ⚠ **The walk guarded the node ARRAY and left its own CONTAINER unguarded**, one level
    above the hole wave 14 closed in `_readable_node`. The loop header used to read
    `for d in (container.get("definitions") or {}).get("subgraphs") or []:` and skipped a
    non-dict definition with `continue`. Measured 2026-09-04 in this worktree on
    save-format graphs carrying one well-formed `UNETLoader` plus a pinned `KSampler`:

      * with `definitions.subgraphs` spelled as a MAPPING keyed by blueprint id, iterating
        the dict yields its string KEYS, every one fails `isinstance(d, dict)` and is
        `continue`d — so `components()` returned only the top-level weight and `verify()`
        returned GREEN, with a CC-BY-NC LoRA sitting inside a blueprint the walk never
        entered, on the last gate before a paid submission. The SAME graph with
        `subgraphs` as a LIST raised `RouteGate` naming the weight BANNED;
      * with `definitions` itself a non-dict truthy value (`[{"nodes": []}]`, or the string
        `"x"`), `components()` raised a bare `AttributeError: 'list' object has no
        attribute 'get'`. `AttributeError` is not an `ArmatureError`, so the halt
        contract's exit-2 six-key `<TOOL>_HALT` receipt branch is bypassed and Gate ROUTE
        refusing a shape it cannot read is recorded as an unhandled crash.

    NOT MEASURED: whether Comfy's own exporter ever emits a mapping-shaped `subgraphs`. The
    shape was constructed here; what makes it ordinary rather than exotic is the input class
    `load_graph` documents — an operator's `--saved` file, a converter or a hand-edit
    artifact. `None` and an absent key stay the ordinary spelling of "no blueprints" and
    are read as such; every other shape refuses.

    A non-dict DEFINITION now raises rather than being skipped, for the reason
    `_readable_node`'s own comment gives about its array: a skipped blueprint is a
    blueprint no clause examined, and "nothing was checkable" and "everything checked out"
    may not be the same verdict.

    ⚠ **The id clause bounded one field over from the invariant Gate S rests on, and the
    LABEL this walk emits was left unbounded.** The refusal above is keyed on `id` on the
    stated ground that "the `where` label a duplicate-id blueprint would carry is ambiguous
    by construction" — and nothing refused a duplicate `name`, or two blueprints declaring
    NEITHER field, both of which collapse that same label. `gate_s_registration` resolves
    each seed record to its node with `next(... if (w, str(x.get("id"))) == (s["where"],
    str(s["node_id"])))`, which is TOTAL but not UNIQUE, so the second colliding record
    reads its `add_noise` off the FIRST node the walk yielded.

    Measured 2026-09-05 in this worktree on a save-format graph carrying a live top-level
    `KSamplerAdvanced` id 2 (`add_noise=enable`, seed 7) plus two blueprints with DISTINCT
    ids `bp1`/`bp2` and the SAME `name: "expert"`, the first holding `KSamplerAdvanced`
    id 3 (`add_noise=disable`, seed 7) and the second holding `KSamplerAdvanced` id 3
    (`add_noise=ENABLE`, seed 999999999): `seeds()` correctly returned
    `[('top',2,7), ('expert',3,7), ('expert',3,999999999)]` and `gate_s_registration(g,
    [7])` RETURNED with `seeds_noise_bearing: 1 of 3` and the verdict "… 2 exempted by
    add_noise=disable (node(s) expert/3, expert/3)". Seed 999999999 was never graded, and
    the receipt's own tell — one identity printed twice, which the wave-18 fix added
    `seeds_exempt_nodes` and the `level/id` wording to remove — was back verbatim. Two
    more spellings of the same collapse: NO `name` and NO `id` on either blueprint (both
    labels fall to the literal `"subgraph"`, and the `bid is not None` guard skips the id
    clause entirely), and a single blueprint NAMED `top`, which is the label `_walk_nodes`
    gives the graph's own `nodes` array.

    **The label is refused, not rewritten.** The other available fix — emitting `where`
    keyed on the definition's position as well as its label — would have moved every Gate
    S receipt string, the `level/id` verdict wording, `seeds_exempt_nodes`' `{where,
    node_id}` pairs and the `where` recorded by `components`, `model_weights`, `seeds`,
    `latents`, `cameras` and `camera_widget_order_evidence`, on every graph including the
    ones that were never ambiguous. A refusal leaves all of that byte-identical and states
    the invariant where the label is BUILT. It is also the answer this module gives to
    ambiguity everywhere else: `duplicate_subgraph_id` here, `link_table`'s
    `duplicate_link_id`, `fetch_run.parse_node_map`'s `node_map_duplicate_id`.

    The two ledgers are separate namespaces inside one `declared` dict (`("id", …)` and
    `("label", …)`), because a blueprint whose `id` is `"x"` and a later blueprint NAMED
    `"x"` are not ambiguous with each other and a single key space would have refused
    them. NOT MEASURED: whether Comfy's exporter ever emits two blueprints under one
    `name`. The cost of the refusal is a halt an operator reads and re-exports past; the
    cost of its absence is the green PASS measured above.
    """
    path = set() if path is None else path
    declared = {} if declared is None else declared
    defs = container.get("definitions")
    if defs is not None and not isinstance(defs, dict):
        _unreadable_level(
            "definitions", defs, "the mapping this walk reads blueprints out of",
            extra={"container_keys": sorted(container)})
    subs = (defs or {}).get("subgraphs")
    if subs is not None and not isinstance(subs, list):
        _unreadable_level(
            "definitions.subgraphs", subs, "a list of subgraph definitions",
            extra={"definitions_keys": sorted(defs)})
    subs = subs or []
    for i, d in enumerate(subs):
        if not isinstance(d, dict):
            _unreadable_level(
                "definitions.subgraphs", d, "a subgraph definition", index=i,
                population=len(subs))
        # Cycle protection, and ONLY cycle protection: this exact blueprint object is
        # already on the recursion path, so entering it again would not terminate. Keyed
        # on object identity because that is the only thing that makes a self-reference a
        # self-reference; the blueprint's `id` field is a value nothing validates.
        if id(d) in path:
            continue
        where = d.get("name") or d.get("id") or "subgraph"
        bid = d.get("id")
        if bid is not None:
            # · ANDON — ambiguity, which is a different fact from a cycle and gets a
            # different answer. See this function's docstring.
            prev = declared.get(("id", str(bid)))
            if prev is not None:
                raise RouteGate(
                    f"this graph declares two subgraph blueprints under one id "
                    f"({bid!r}): {prev!r} and {where!r}. A file that declares two "
                    f"different blueprints under one id is ambiguous about which one "
                    f"runs, and a walk that deduplicated them would leave every node "
                    f"inside the second unexamined inside a graph reported clean — which "
                    f"is what this walk did until 2026-09-04, with a CC-BY-NC LoRA in the "
                    f"second blueprint and a green receipt on the last gate before a paid "
                    f"submission",
                    {"gate": "ROUTE", "andon": "RouteGate",
                     "clause": "duplicate_subgraph_id", "subgraph_id": bid,
                     "declared_by": [prev, where], "index": i,
                     "n_subgraphs": len(subs), "where": where})
            declared[("id", str(bid))] = where
        # · ANDON — the LABEL this walk emits, which is the half of node identity the id
        # clause above does not bound. See this function's docstring.
        collides = (RESERVED_LEVEL_LABELS.get(str(where))
                    or declared.get(("label", str(where))))
        if collides is not None:
            reserved = str(where) in RESERVED_LEVEL_LABELS
            raise RouteGate(
                f"this graph declares a subgraph blueprint whose level label is "
                f"{str(where)!r}, which "
                + (f"is the label this walk already gives {collides['what']}"
                   if reserved else
                   f"blueprint #{collides['index']} (id {collides['id']!r}) already "
                   f"declared")
                + f". Node identity in this walk is the PAIR (where, id) — blueprint ids "
                f"are a separate namespace — so two levels emitting one label make that "
                f"pair total but not unique, and the SECOND record then reads its node's "
                f"fields off the FIRST node the walk yielded. Measured 2026-09-05 with "
                f"two blueprints under one name: Gate S RETURNED a PASS naming "
                f"'expert/3, expert/3' while a blueprint node ran an unregistered seed",
                {"gate": "ROUTE", "andon": "RouteGate",
                 "clause": "duplicate_subgraph_label", "label": str(where),
                 "collides_with": (dict(collides, kind="reserved_level_label")
                                   if reserved else
                                   {"kind": "subgraph", "index": collides["index"],
                                    "id": collides["id"]}),
                 "declared_by": [None if reserved else collides["id"], bid],
                 "index": i, "n_subgraphs": len(subs), "where": where,
                 "reserved_level_labels": sorted(RESERVED_LEVEL_LABELS)})
        declared[("label", str(where))] = {"index": i, "id": bid}
        path.add(id(d))
        try:
            nodes = d.get("nodes") or []
            for j, n in enumerate(nodes):
                # · ANDON — the same refusal the top-level array carries, on the level the
                # wave-12 fix did not reach. See `_readable_node`.
                yield (where, _readable_node(where, n, j, len(nodes)))
            yield from _iter_definitions(d, path, declared)
        finally:
            path.discard(id(d))


#: Verdict precedence, strictest first. A filename that matches more than one row in
#: `RULED_COMPONENTS` is governed by the STRICTEST match, never by whichever row happens
#: to have been typed into the dict first.
#:
#: ⚠ **`CONDITIONAL` sits between `ALLOWED` and `EXCLUDED`**, added 2026-09-04 with the
#: `technically_color` row above. Without a tier of its own a conditional grant and an
#: unconditional one were the SAME OBJECT to every reader of this table, so a filename
#: matching a conditional row and a plain allowed row could be sorted either way by
#: whichever was typed first — the accident `rulings_for` exists to remove. It ranks below
#: the two kills because a condition is a grant with an obligation attached, not a refusal:
#: a BANNED or EXCLUDED row still governs a name that matches both.
VERDICT_RANK = {"BANNED": 4, "EXCLUDED": 3, "CONDITIONAL": 2, "ALLOWED": 1,
                "NOT IN THIS TABLE": 0}

#: The verdicts that carry an obligation rather than a refusal. `verify` refuses a graph
#: carrying one of these unless the submitting record credits it — see
#: `uncredited_conditional_components`.
CONDITIONAL_VERDICTS = ("CONDITIONAL",)


def _today():
    """Today, as a `datetime.date`. One seam, so a test can state its own date.

    Every age question below takes `today=` explicitly; this is only the default. It is a
    function rather than a module constant because a constant would freeze at import and a
    long-lived process would then age its rulings against the day it started.
    """
    return datetime.date.today()


def licence_age_days(fetched, today=None):
    """How many days ago `fetched` (an ISO date string) was retrieved, or None.

    None for a row with no date at all — which is a different answer from "old", and the
    caller says which it is rather than defaulting one into the other.
    """
    if not fetched:
        return None
    try:
        when = datetime.date.fromisoformat(str(fetched))
    except ValueError:
        return None
    return ((today or _today()) - when).days


def licence_advisory_after(fetched):
    """The ISO date on which `docs/license-map.md`'s 90-day rule makes this row advisory."""
    if not fetched:
        return None
    try:
        when = datetime.date.fromisoformat(str(fetched))
    except ValueError:
        return None
    return (when + datetime.timedelta(days=LICENCE_ADVISORY_DAYS)).isoformat()


def licence_fetch_reading(comp, today=None):
    """What the APPLIED licence rulings say about their own age.

    `comp` is a `components()` list. Reads the `fetched` date off every ruling the table
    actually matched — the rows that DECIDED this graph, not the whole table — and answers
    four things: the oldest applied fetch date, the date that row goes advisory, the rows
    already past `LICENCE_ADVISORY_DAYS`, and the applied rows carrying no date at all.

    It REPORTS and never raises. Whether a lapsed ruling refuses is the Director's call
    (CLAUDE.md: CONDITIONAL and re-fetch decisions are his), and a gate that invented that
    refusal for itself would be this repo's own "a global constant governs a local
    feature". What the gate owes is that no receipt and no refusal can be read without the
    age of the ruling it applied.
    """
    today = today or _today()
    applied = []
    for c in comp or []:
        for m in ((c.get("ruling") or {}).get("matches") or
                  ([{"matched_on": (c.get("ruling") or {}).get("matched_on")}]
                   if (c.get("ruling") or {}).get("matched_on") else [])):
            key = m.get("matched_on")
            row = RULED_COMPONENTS.get(key)
            if row is None:
                continue
            applied.append({"matched_on": key, "verdict": row["verdict"],
                            "fetched": row.get("fetched"),
                            "source": row.get("source"),
                            "advisory_after": licence_advisory_after(row.get("fetched")),
                            "age_days": licence_age_days(row.get("fetched"), today)})
    seen, rows = set(), []
    for r in applied:
        if r["matched_on"] in seen:
            continue
        seen.add(r["matched_on"])
        rows.append(r)
    rows.sort(key=lambda r: (r["fetched"] or "", r["matched_on"]))
    dated = [r for r in rows if r["fetched"]]
    undated = [r["matched_on"] for r in rows if not r["fetched"]]
    stale = [r for r in dated if (r["age_days"] or 0) > LICENCE_ADVISORY_DAYS]
    return {
        "as_of": today.isoformat(),
        "advisory_days": LICENCE_ADVISORY_DAYS,
        "applied_rows": rows,
        "oldest_fetched": dated[0]["fetched"] if dated else None,
        "advisory_after": dated[0]["advisory_after"] if dated else None,
        "advisory_rows": [r["matched_on"] for r in stale],
        "undated_rows": undated,
    }


def licence_phrase_for(reading):
    """The clause the verdict and the refusals both quote about ruling age."""
    if reading["oldest_fetched"] is None:
        return ("no applied licence ruling carries a fetch date"
                if reading["applied_rows"] else "no licence ruling applied")
    base = (f"licence rulings applied were fetched no earlier than "
            f"{reading['oldest_fetched']} (advisory after {reading['advisory_after']} "
            f"under the map's {reading['advisory_days']}-day rule)")
    if reading["advisory_rows"]:
        base += (f"; ADVISORY — past {reading['advisory_days']} days as of "
                 f"{reading['as_of']}: {reading['advisory_rows']}, re-fetch before "
                 f"reading this verdict as current")
    if reading["undated_rows"]:
        base += f"; UNDATED rows applied: {reading['undated_rows']}"
    return base


def _row_provenance(key):
    """`(fetched=…, source=…)` for a `RULED_COMPONENTS` key, for a refusal sentence."""
    row = RULED_COMPONENTS.get(key) or {}
    fetched = row.get("fetched")
    src = row.get("source")
    return (f"map row {key!r} fetched {fetched or 'NEVER'}"
            + (f", {src}" if src else ", document NOT RETRIEVED")
            + (f", advisory after {licence_advisory_after(fetched)}" if fetched else ""))


def graph_digest(graph):
    """A stable sha256 over the NORMALISED graph, so a stored receipt names what it ruled.

    Written for the other half of the reproducibility question `TOOL_VERSION` answers: two
    Gate ROUTE receipts in `outputs/<experiment>/` said which clauses passed and named
    neither the version that ruled nor the graph it ruled on. Computed after
    `normalise_graph`, so the same graph inside two different wrappers digests the same;
    `default=repr` because a hand-built graph may carry a value JSON cannot encode and a
    digest that raises is worse than a digest of a repr.
    """
    return hashlib.sha256(
        json.dumps(normalise_graph(graph), sort_keys=True, default=repr,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def attribution_entry_for(key):
    """The `attribution` record entry a submitting tool must carry for row `key`.

    **Built FROM the row, never typed in a builder.** The words in a credit line are the
    licence map's, and a literal retyped at the call site is a second authority that drifts
    the first time the map is re-fetched. A builder writes
    `attribution=[route_gates.attribution_entry_for("technically_color")]` into its payload
    record and its provenance JSON and passes the same list to `verify`.

    Raises rather than returning None for a row that carries no condition: asking for the
    credit line of an unconditional component is a caller bug, and a silent empty entry
    would satisfy nothing while looking like a credit.
    """
    rec = RULED_COMPONENTS.get(key)
    if rec is None or not rec.get("condition"):
        raise RouteGate(
            f"{key!r} is not a CONDITIONAL row in RULED_COMPONENTS, so it has no credit "
            f"line to write. An attribution entry for an unconditional component would "
            f"satisfy no obligation while reading like one",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "attribution_for_unconditional_row", "key": key,
             "conditional_rows": sorted(
                 k for k, r in RULED_COMPONENTS.items() if r.get("condition"))})
    cond = rec["condition"]
    return {"component": key, "creditor": cond["creditor"],
            "source": cond.get("source"), "text": cond.get("text"),
            "kind": cond.get("kind", "credit")}


def _credits(entry, row_key, filename):
    """Does this attribution entry credit the component `row_key` (served as `filename`)?

    The creditor must match the row's condition — an entry naming somebody else is not a
    credit — and the component must be nameable either by the ROW KEY or by the served
    filename, because a record written beside a graph naturally carries the filename while
    a record written from the table carries the key. Both readings are accepted; neither
    is guessed at.
    """
    if not isinstance(entry, dict):
        return False
    cond = RULED_COMPONENTS.get(row_key, {}).get("condition") or {}
    creditor = str(entry.get("creditor") or "").strip().lower()
    if not creditor or creditor != str(cond.get("creditor") or "").strip().lower():
        return False
    named = str(entry.get("component") or "").strip().lower()
    if not named:
        return False
    return (named == row_key.lower()
            or row_key.lower() in named
            or (bool(filename) and named in str(filename).lower()))


def conditional_rows_of(c):
    """Every CONDITIONAL row key this component matched — not only the strictest one.

    ⚠ **The CONDITIONAL tier read `hits[0]` and nothing else**, so a weight filename that
    ALSO matched a waivable EXCLUDED row lost its credit obligation entirely. `verdict` at
    a component's top level is `components()`'s copy of `hits[0]["verdict"]`, while
    `ruling["matches"]` — which records every row hit, and which the banned/excluded clause
    already prints — went unread here. Measured 2026-09-04 on
    `technically_color_lightx2v_merge.safetensors`: `rulings_for` returns
    `[('lightx2v','EXCLUDED'), ('technically_color','CONDITIONAL')]`;
    `conditional_component_keys(graph)` returned `[]`, so a builder asking the graph what
    obligations it had picked up was told none; and
    `verify(graph, frame=(832,480,33), allow=('lightx2v',))` returned GREEN with the
    receipt "1 of 1 component(s) classified, 0 unclassified, 0 conditional (credited) ...
    WAIVED components ['lightx2v']".

    Footage generated from a stacked or merged LoRA whose grant is conditional on
    crediting its author would then be submitted, recorded and published with no
    attribution anywhere and a receipt affirmatively stating zero conditional components —
    the inverse of the harm the row exists to prevent, on the one graph shape
    `rulings_for`'s own docstring argues is the realistic one ("Stacked and merged LoRA
    names are concatenations"). `allow=('lightx2v',)` is a live methodology waiver, not a
    hypothetical.

    This is the correction `rulings_for` already applied to the licence clause, carried to
    the obligation clause: a strictest-match VERDICT is the right rule for a kill (a
    BANNED row must govern a name that matches both) and the wrong rule for an OBLIGATION,
    because an obligation is not overridden by a stricter one — it is still owed.
    """
    matches = (c.get("ruling") or {}).get("matches") or [c.get("ruling") or {}]
    return [m for m in matches
            if m.get("verdict") in CONDITIONAL_VERDICTS and m.get("matched_on")]


def conditional_component_keys(graph):
    """The `RULED_COMPONENTS` row keys of every CONDITIONAL component this graph loads.

    The builder-facing half of `attribution_entry_for`: a submitting tool asks the GRAPH
    which obligations it has picked up, rather than remembering which arm carries which
    LoRA. Arm S's graph returns `[]` and needs no entry; a future conditional row is picked
    up without editing any builder. It refuses nothing — `verify` is the andon — because a
    helper that both discovers and halts would put the gate somewhere other than inside the
    function performing the irreversible step.

    Reads EVERY matching row, not `hits[0]` — see `conditional_rows_of`.
    """
    return sorted({m["matched_on"] for c in components(graph)
                   for m in conditional_rows_of(c)})


def uncredited_conditional_components(comp, attribution):
    """The CONDITIONAL components in `comp` that `attribution` does not credit.

    Reads the components list `components()` returns and the `attribution` list the
    submitting record carries. A row is credited by ONE matching entry; every conditional
    row is examined and reported, so the evidence names what was owed as well as what was
    unpaid.

    One entry per CONDITIONAL ROW MATCHED, not per component: a single merged filename can
    owe two creditors, and `matched_on` says which row each obligation came from — see
    `conditional_rows_of`.
    """
    entries = list(attribution or [])
    out = []
    for c in comp:
        for m in conditional_rows_of(c):
            key = m["matched_on"]
            cond = (RULED_COMPONENTS.get(key) or {}).get("condition") or {}
            credited = any(_credits(e, key, c.get("file")) for e in entries)
            out.append({"label": _component_label(c), "file": c.get("file"),
                        "class_type": c.get("class_type"), "matched_on": key,
                        "kind": c.get("kind"), "condition": cond, "credited": credited,
                        "strictest_verdict": c.get("verdict")})
    return out


def unmatched_attribution_entries(comp, attribution):
    """The `attribution` entries that credit NO component this graph loads.

    ⚠ **`verify` checked one direction only.** Every CONDITIONAL component the graph loads
    had to be credited, and no clause ever asked the converse — that every credit the
    record carries names a component the graph actually loads — while `verify` copied the
    unmatched entries verbatim into the evidence a builder stores. Measured 2026-09-04 on
    an API graph loading only `wan2.1_vace_14B_fp16.safetensors` plus a pinned KSampler,
    called with `attribution=[attribution_entry_for('technically_color')]`: ACCEPTED, with
    `ev['attribution']` carrying the full credit line "Technically Color LoRA by
    renderartist (CivitAI)" beside `ev['verdict']` reading "0 of 1 component(s)
    classified, 1 unclassified, 0 conditional (credited)" — a receipt whose count and
    whose attribution list describe different populations, with nothing reconciling them.

    Under the per-route disclosure ruling this row was written to serve, the consequence is
    the inverse of the harm the row prevents: a builder that keeps the entry after
    switching arms publishes footage crediting a creator whose LoRA was not used, on a
    public disclosure surface, and a later reader of the provenance record cannot tell from
    the record whether the credited component was ever loaded.

    A credit is matched against the same `_credits` reading the forward clause uses, over
    every conditional row every component matched, so the two directions cannot disagree
    about what "credits" means.
    """
    entries = list(attribution or [])
    keyed = [(c, m["matched_on"]) for c in comp for m in conditional_rows_of(c)]
    return [e for e in entries
            if not any(_credits(e, key, c.get("file")) for c, key in keyed)]


def rulings_for(filename):
    """EVERY `RULED_COMPONENTS` row this weight filename matches, strictest first.

    ⚠ **`components()` used to take the FIRST match in dict-insertion order and record
    no other.** `families_of()` on the same page deliberately does the opposite and its
    table's comment says why: "A file may match more than one and every match is
    recorded." The licence clause — the one CLAUDE.md calls a non-negotiable — got the
    weaker rule. Measured 2026-09-03: `technically_color_instagirl_v2.safetensors`
    matches `technically_color` (ALLOWED, typed in at index 4) and `instagirl` (BANNED,
    Instara Fair Use — "prohibits use on any image/video generation service", index 9),
    and `components()` returned verdict ALLOWED, matched_on technically_color, with the
    BANNED row named nowhere in the evidence; `verify()` on a graph loading it returned
    green. The precedence was an accident of typing order. Stacked and merged LoRA names
    are concatenations, and the served style field this table mirrors is exactly where
    those names come from.
    """
    low = str(filename).lower()
    hits = [dict(rec, matched_on=key) for key, rec in RULED_COMPONENTS.items()
            if key in low]
    hits.sort(key=lambda r: -VERDICT_RANK.get(r["verdict"], 0))
    return hits


def class_patterns_for(key):
    """Every class-name substring that identifies the `RULED_COMPONENTS` row `key`.

    The key itself is always one of them, so a row that names no alias is still matched
    on its own name rather than silently exempted.
    """
    return tuple(sorted({str(key).lower()}
                        | {str(a).lower() for a in RULED_COMPONENT_CLASSES.get(key, ())}))


def orphaned_component_class_aliases():
    """Alias keys in `RULED_COMPONENT_CLASSES` that name no `RULED_COMPONENTS` row.

    Derived from the two tables, never typed: `set(RULED_COMPONENT_CLASSES) -
    set(RULED_COMPONENTS)`. An orphan is unreachable — `rulings_for_class` iterates the
    ROWS — so it is invisible in exactly the direction the class clause exists to see.
    """
    return sorted(set(RULED_COMPONENT_CLASSES) - set(RULED_COMPONENTS))


def gate_alias_table():
    """· ANDON — the class-alias table names rows that exist.

    Raises rather than returning a flag, and runs where a wrong table is loudest: at
    IMPORT (below), so a licence-map re-fetch that renames a row halts every tool that
    reads this module, and again inside `verify`, so a table mutated at run time cannot
    verify a graph either. The direction it bounds is the one no other clause does: the
    forward reading (a row absent from the alias table is matched on its own name) is
    already safe by construction, while an orphaned ALIAS is silent — the class-level
    licence clause simply stops seeing the tier it was added for while every gate reports
    green.
    """
    orphaned = orphaned_component_class_aliases()
    if orphaned:
        raise RouteGate(
            "RULED_COMPONENT_CLASSES names " + ", ".join(repr(k) for k in orphaned) +
            ", which is not a RULED_COMPONENTS row. An alias whose key names no row is "
            "never consulted — `rulings_for_class` iterates the ROWS — so the node "
            "classes it exists to catch (the banned preprocessor tier) contribute "
            "nothing to `components()` and `verify()` reports the graph clean. This "
            "table mirrors docs/license-map.md; a row renamed or retired by a re-fetch "
            "takes its aliases with it",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "orphaned_component_class_alias",
             "orphaned": orphaned,
             "alias_keys": sorted(RULED_COMPONENT_CLASSES),
             "row_keys": sorted(RULED_COMPONENTS)})
    return {"gate": "ROUTE", "andon": "RouteGate",
            "clause": "orphaned_component_class_alias",
            "n_alias_keys": len(RULED_COMPONENT_CLASSES),
            "n_rows": len(RULED_COMPONENTS),
            "verdict": (f"every alias key names a row: "
                        f"{len(RULED_COMPONENT_CLASSES)} of {len(RULED_COMPONENTS)}")}


gate_alias_table()


def rulings_for_class(class_type):
    """EVERY `RULED_COMPONENTS` row this NODE CLASS name matches, strictest first.

    The class-name twin of `rulings_for`, and it is a separate reading because the thing
    being read is different: a weight file is a value inside `widgets_values`, a class is
    the node's own type. A banned preprocessor tier appears only as the second.
    """
    low = str(class_type).lower()
    hits = []
    for key, rec in RULED_COMPONENTS.items():
        pat = next((c for c in class_patterns_for(key) if c in low), None)
        if pat is not None:
            hits.append(dict(rec, matched_on=key, matched_class_pattern=pat))
    hits.sort(key=lambda r: -VERDICT_RANK.get(r["verdict"], 0))
    return hits


def ruled_node_classes(graph):
    """Every node whose CLASS NAME the licence map has already ruled on.

    Reads in either format and through the subgraph walk, like every other clause here.
    Each row carries `class_type`, `verdict`, `licence` and `reason` at the top level for
    a caller that wants the ruling without unpacking, and the full `ruling` (strictest
    row, with `matches` naming every row hit) beside them.

    These rows are also returned by `components()`, so a caller already filtering that
    list on BANNED picks them up without a second call. `verify` refuses them exactly as
    it refuses a banned weight file.
    """
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        if not isinstance(cls, str):
            continue
        hits = rulings_for_class(cls)
        if not hits:
            continue
        ruling = dict(hits[0])
        ruling["matches"] = [{"matched_on": h["matched_on"], "verdict": h["verdict"],
                              "licence": h.get("licence"),
                              "matched_class_pattern": h["matched_class_pattern"]}
                             for h in hits]
        out.append({"kind": "class", "file": None, "class_type": cls,
                    "class": cls, "node_id": n.get("id"), "where": where,
                    "verdict": ruling["verdict"], "licence": ruling.get("licence"),
                    "reason": ruling.get("reason"),
                    "matched_on": ruling.get("matched_on"), "ruling": ruling})
    return out


def _is_name_shaped(value):
    """Could this widget value be a component NAME rather than prose?

    A widget list holds prompts as well as filenames, and `rulings_for` is a SUBSTRING
    test over the licence map's row keys — so "a candid_photography of a knight" typed
    into a `CLIPTextEncode` would match a row. A name has no whitespace in it; prose does.
    Used only to decide whether an UNRULED-suffix string is worth asking the table about,
    never to decide a verdict.
    """
    return (isinstance(value, str) and bool(value.strip())
            and not any(ch.isspace() for ch in value))


def _component_hits(value):
    """`(hits, looks_like_a_weight_file)` for one widget value — the table asked FIRST.

    See `WEIGHT_SUFFIXES` for the measurement this inversion closes. `hits` is
    `rulings_for(value)` for any name-shaped string; the suffix test is only the predicate
    for counting an UNRULED string as an unclassified component.
    """
    if not isinstance(value, str):
        return [], False
    looks_like_weight = value.lower().endswith(WEIGHT_SUFFIXES)
    hits = rulings_for(value) if (looks_like_weight or _is_name_shaped(value)) else []
    return hits, looks_like_weight


def components(graph):
    """Every ruled thing the graph carries: weight files loaded, and ruled node CLASSES.

    The ruling is the STRICTEST row the name matches, and `ruling["matches"]` names
    every row it matched — see `rulings_for` and `rulings_for_class`.

    Rows carry `kind`: `"weight"` for a file named in `widgets_values`, `"class"` for a
    node class the licence map rules on (see `ruled_node_classes` — a `DWPreprocessor`
    brings no filename with it and was invisible to every clause here until 2026-09-04).
    Both carry `verdict` at the top level as well as inside `ruling`, so one filter
    reads both kinds.

    ⚠ **The ruling is asked FIRST and the suffix tuple no longer decides membership** —
    see `WEIGHT_SUFFIXES` for the measurement (`causvid_x.bin`, BANNED, returned a green
    `verify` and was named nowhere in the receipt). A row carries `suffix_recorded`, which
    is False for a ruled name wearing an unrecorded extension; `verify` refuses those by
    name (`ruled_name_with_unknown_suffix`) after the licence kill, so a BANNED row stays
    the headline and an ALLOWED one still cannot enter on an extension nobody recorded.
    """
    graph = normalise_graph(graph)
    out = []
    for where, n in _iter_nodes(graph):
        for v in (n.get("widgets_values") or []):
            hits, looks_like_weight = _component_hits(v)
            if not hits and not looks_like_weight:
                continue
            ruling = dict(hits[0]) if hits else {"verdict": "NOT IN THIS TABLE",
                                                 "reason": "check docs/license-map.md"}
            ruling["matches"] = [{"matched_on": h["matched_on"], "verdict": h["verdict"],
                                  "licence": h.get("licence")} for h in hits]
            out.append({"kind": "weight", "file": v, "node_id": n.get("id"),
                        "class": n.get("type"), "where": where,
                        "suffix_recorded": looks_like_weight,
                        "verdict": ruling["verdict"], "licence": ruling.get("licence"),
                        "reason": ruling.get("reason"),
                        "matched_on": ruling.get("matched_on"), "ruling": ruling})
    out.extend(ruled_node_classes(graph))
    return out


def _component_label(rec):
    """What to call a component in a refusal: its name AND the node it sits on.

    ⚠ **It named the file and threw away the node.** Until 2026-09-05 this returned
    `repr(rec.get("file"))` or `f"node class {rec['class_type']!r}"` and read neither
    `node_id` nor `where`, though `components()` records both on every row — and it is
    what the BANNED/EXCLUDED refusal, the uncredited-CONDITIONAL refusal,
    `ev["banned_or_excluded"]` and `ev["unclassified"]` are all built from. Measured in a
    worktree on a save-format graph whose banned LoRA sits inside a blueprint:
    `components()` returned `causvid_x.safetensors -> node_id: 42, where: style_stack`,
    and `verify(g, frame=(832,480,81))` raised "[ROUTE] the graph loads
    'causvid_x.safetensors' (BANNED: …)" with neither `42` nor `style_stack` anywhere in
    the message. The refusal's required action is to DELETE a node, and the sentence
    demanding it did not say which node or which subgraph level to open — on a graph that
    can carry blueprints, a converted canvas file, or two loaders of the same filename.

    The precedent was already in this module twice: `hosted_enums` gained the level
    because "the per-node billing andon and the enum refusal above it cannot name which
    node", and Gate PAIR's rows gained `where` because "its receipt and its refusal cannot
    name which node they are about". Those two fixes reached the ROWS; this SENTENCE was
    not carried with them. The spelling is `{where}/{node_id}`, which is Gate PAIR's, Gate
    S's and the generator-family refusal's already.

    A record carrying neither field (a caller's synthetic row) still gets its name back,
    so a label is never a sentence about nothing.
    """
    what = (f"node class {rec['class_type']!r}" if rec.get("kind") == "class"
            else repr(rec.get("file")))
    where, node_id = rec.get("where"), rec.get("node_id")
    if where is None and node_id is None:
        return what
    return f"{what} at {where}/{node_id}"


#: The input names a seed lives under in API format, per node class.
SEED_INPUTS = {"KSampler": "seed", "KSamplerAdvanced": "noise_seed",
               "Wan2ReferenceVideoApi": "seed"}

#: Input names that ARE a seed, whatever class carries them, and class-name suffixes that
#: declare a sampling or noise role. Used only by `unrecorded_seed_sources` — the andon
#: that answers "this table does not know that class" instead of answering "no seeds".
SEED_INPUT_NAMES = ("seed", "noise_seed", "rand_seed")
SEED_CLASS_SUFFIXES = ("Sampler", "Noise")

#: Class-name suffixes that mark a HOSTED / partner node, whose save-format
#: `widgets_values` this repo cannot interpret without a recorded widget-index row.
#:
#: ⚠ Used by `unrecorded_seed_sources` in BOTH FORMATS. In save format the values are
#: positional and nothing names them, so a vendor node's widget list is exactly the
#: direction no other clause bounds — and save format is the format the cloud hands back
#: and the one `load_graph` / `gate_saved_graph` read before submission. Measured
#: 2026-09-04 on `{"nodes": [KSampler(seed 7, "fixed"), KlingVideoApi(widgets
#: [..., 999999999]), ...]}`: `unrecorded_seed_sources` returned [], `gate_s_registration`
#: reported "1 noise-bearing seed(s), all pinned and all drawn from the committed list of
#: 1", and node 4's 999999999 was never examined. `Wan2ReferenceVideoApi` carries a
#: `SEED_NODES` row and so is read rather than flagged — which is what the andon asks
#: for: a row, in the spec that arms the tier.
#:
#: ⚠ **It ran in save format ONLY until 2026-09-04, and API is the format every builder
#: submits.** The clause was written `if why is None and not api and cls.endswith(...)`,
#: on the stated ground that "in API format inputs are keyed by name and the input-name
#: clause already answers". That ground holds only while a vendor spells its seed input
#: exactly seed/noise_seed/rand_seed — and this repo's own hosted node namespaces every
#: other input under `model.` (`build_r2v_payload.py:79-83` writes model.prompt /
#: model.resolution / model.ratio / model.duration). Measured on ONE graph written in both
#: formats — UNETLoader + WanImageToVideo + KSampler(seed 7, "fixed") + a `KlingVideoApi`
#: with no SEED_NODES row: SAVE raised on both readers; the SAME graph in API returned
#: `unrecorded_seed_sources() == []` and `seed_clause_verdict = "CHECKED — 1 seed(s) all
#: pinned"`, repeated with an explicit `model.seed` of 999999999 that was never examined.
#: In API format the reading needs no widget indices to state: a class whose name ends in
#: Api/API with no `SEED_NODES` row.
HOSTED_API_CLASS_SUFFIXES = ("Api", "API")


def _save_format_input_names(node):
    """Every input NAME a save-format node declares, converted widgets included.

    Save format spells `inputs` as a LIST of slot dicts (`{"name", "type", "link"}`); a
    widget converted to an input also carries `{"widget": {"name": ...}}`. API format
    spells it as a mapping, which the caller reads directly.
    """
    out = []
    for slot in node.get("inputs") or []:
        if not isinstance(slot, dict):
            continue
        if isinstance(slot.get("name"), str):
            out.append(slot["name"])
        widget = slot.get("widget")
        if isinstance(widget, dict) and isinstance(widget.get("name"), str):
            out.append(widget["name"])
    return out


def _save_format_converted_widget_names(node):
    """Every widget this save-format node has had CONVERTED to an input, by name.

    A slot carrying a `widget` dict is a converted widget: it once occupied a position in
    `widgets_values` and now arrives over a link, so every positional index at or after it
    is shifted. A slot with no `widget` key is an ordinary input socket that never
    occupied a widget position and shifts nothing — the distinction
    `_save_format_input_names` does not draw, because its caller does not need it.
    """
    out = []
    for slot in node.get("inputs") or []:
        if not isinstance(slot, dict):
            continue
        widget = slot.get("widget")
        if isinstance(widget, dict) and isinstance(widget.get("name"), str):
            out.append(widget["name"])
        elif isinstance(widget, dict) and isinstance(slot.get("name"), str):
            out.append(slot["name"])
    return out


def known_widget_indices(cls):
    """Every save-format widget position this module has RECORDED for `cls`.

    The union of the tables that carry a positional index for the class:
    `HOSTED_ENUM_WIDGETS`, `SEED_NODES` (`seed`, `control_after_generate`, `add_noise`),
    `LATENT_NODES` and `CAMERA_NODES`. Published as one function because a caller asking
    "where does this widget sit" should not have to know which of four tables happens to
    hold the row, and because a name that is in NONE of them has an unknown position —
    which is a third answer, not a zero.
    """
    out = {}
    spec = SEED_NODES.get(cls) or {}
    for name, key in (("seed", "seed"), ("control_after_generate", "control"),
                      ("add_noise", "add_noise")):
        if isinstance(spec.get(key), int):
            out[name] = spec[key]
    for table in (LATENT_NODES, CAMERA_NODES, HOSTED_ENUM_WIDGETS):
        for name, i in (table.get(cls) or {}).items():
            if isinstance(i, int):
                out[name] = i
    return out


def unrecorded_seed_sources(graph):
    """Nodes that look like they carry a seed and have NO `SEED_NODES` row.

    ⚠ **A class absent from `SEED_NODES` used to disarm Gate S in the affirmative.**
    `seeds()` returns [] for it, and both readers then reported green. Measured
    2026-09-03 on an API graph wiring `SamplerCustomAdvanced` fed by `RandomNoise` at
    `noise_seed=123456789`: `seeds()` returned [], `verify(g, family="wan")` reported
    "0 seed(s) all pinned" with `seed_clause_verdict = "CHECKED — 0 seed(s) all pinned"`,
    and `gate_s_registration(g, [7])` reported "0 noise-bearing seed(s), all pinned and
    all drawn from the committed list of 1" — while the seed that would actually run was
    123456789 and the committed list was [7].

    That is the shape the E13 halt-era executor refused to record as a pass, and the
    remedy taken then was to add one row to `SEED_NODES` — which is exactly what the
    `LATENT_NODES` note says is not a fix: "Adding a class to this table fixes one graph;
    it does not fix the shape of that failure." So the shape is fixed here instead, the
    way Gate L and Gate PAIR already answer: "nothing was checkable" is a third answer,
    and it raises.

    Detection is by the thing being read, not by a vendor prefix: an input named
    `seed`/`noise_seed`/`rand_seed` on a class with no row; or a class name ending in
    `Sampler` or `Noise` with no row. `endswith` rather than a substring on purpose —
    `KSamplerSelect` picks a scheduler and carries no seed, and an andon that fires on a
    correct graph is not one anybody keeps.

    ⚠ **The input-name half used to run in API FORMAT ONLY, and the two formats then
    gave opposite answers about the same graph.** Line `if api:` gated it, and in save
    format only the class-name suffix survived — so a hosted or vendor node carrying a
    seed widget was invisible. Measured 2026-09-04 on the save-format graph `{"nodes":
    [KSampler(seed 7, control "fixed"), KlingVideoApi(widgets [..., 999999999]),
    UNETLoader, WanImageToVideo]}`: this function returned [], `seeds()` returned only
    the KSampler, `gate_s_registration(g, [7])` returned "1 noise-bearing seed(s), all
    pinned and all drawn from the committed list of 1", and `verify(g,
    frame=(832,480,81))` returned "CHECKED — 1 seed(s) all pinned" — while node 4's seed
    999999999 was never examined and no committed list pre-registers it. The same node in
    API format WAS caught. Save format is the format the cloud hands back and the one
    `load_graph` / `gate_saved_graph` read before submission.

    Save format names inputs too — as a list of slot dicts, converted widgets included —
    so the input-name clause now runs in both, reading each format's own spelling
    (`_save_format_input_names`). The third clause is `HOSTED_API_CLASS_SUFFIXES`: a
    partner node this repo has no recorded row for, which is the KlingVideoApi shape
    above.

    ⚠ **The hosted clause ran in save format only, and API is the format every builder
    submits.** Measured 2026-09-04 on ONE graph written in both formats — UNETLoader +
    WanImageToVideo(832,480,81) + KSampler(seed 7, "fixed") + `KlingVideoApi` with no
    `SEED_NODES` row: SAVE gave one row here and both `gate_s_registration(g, [7])` and
    `verify(g, frame=(832,480,81))` raised; the SAME graph in API gave [] here, "1
    noise-bearing seed(s), all pinned and all drawn from the committed list of 1", and
    `seed_clause_verdict = "CHECKED — 1 seed(s) all pinned"`. Repeated with an explicit
    `model.seed` of 999999999: API still green, that seed never examined. It now runs in
    both, stating the reading each format supports — and the input-name clause reads a
    key's LAST DOTTED SEGMENT, because this repo's own hosted node namespaces every input
    under `model.`.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        if not isinstance(cls, str) or cls in SEED_NODES:
            continue
        names = (list(n.get("inputs") or {}) if api
                 else _save_format_input_names(n))
        why = None
        # The LAST DOTTED SEGMENT, not the whole key: a hosted node namespaces its inputs
        # (`model.seed`), and reading only the bare spelling made the input-name clause
        # blind to exactly the tier the hosted clause below exists for.
        hit = sorted({k for k in names
                      if str(k).rsplit(".", 1)[-1] in SEED_INPUT_NAMES})
        if hit:
            why = f"carries seed-shaped input(s) {', '.join(hit)}"
        if why is None and cls.endswith(SEED_CLASS_SUFFIXES):
            why = "the class name declares a sampling or noise role"
        if why is None and cls.endswith(HOSTED_API_CLASS_SUFFIXES):
            why = (
                (f"it is a hosted/partner node with no SEED_NODES row: {cls!r} ends in "
                 f"{HOSTED_API_CLASS_SUFFIXES}, and a partner tier that draws its own "
                 f"noise is one this module can say nothing about — `seeds()` returns "
                 f"nothing for it and every reader then reports green")
                if api else
                (f"it is a hosted/partner node whose save-format widgets are "
                 f"positional and this module has no recorded widget row for "
                 f"{cls!r}, so a seed among its {len(n.get('widgets_values') or [])} "
                 f"widget value(s) cannot be read at all")
            )
        if why:
            out.append({"node_id": n.get("id"), "class": cls, "where": where, "why": why})
    return out


def _seed_population_andon(graph, found, ev, carries_no_sampler):
    """The third answer, shared by `verify`'s seed clause and `gate_s_registration`.

    Raises unless the seed population is one this module can honestly describe. The
    caller may assert `carries_no_sampler=True` — and that assertion is CHECKED, not
    obeyed: it raises if a seed or an unrecorded seed source turns up under it, which is
    what keeps it from being a skip flag.
    """
    # The caller's evidence dict is the one that will be raised, and the andon that
    # raises from here is `RouteGate` whatever clause called in. Written as plain
    # assignments so the receipt names its own id even when this helper is reached from
    # a caller that built its dict differently.
    ev["gate"] = "ROUTE"
    ev["andon"] = "RouteGate"
    unrecorded = unrecorded_seed_sources(graph)
    ev["unrecorded_seed_sources"] = unrecorded
    ev["carries_no_sampler_asserted"] = bool(carries_no_sampler)
    if unrecorded:
        ev["seed_clause_verdict"] = "INDETERMINATE"
        ev["clause"] = "unrecorded_seed_source"
        raise RouteGate(
            "the seed clause is INDETERMINATE: " + "; ".join(
                f"node {u['node_id']} is {u['class']}, which has no SEED_NODES row and "
                f"{u['why']}" for u in unrecorded) +
            ". `seeds()` reports nothing for such a class and every reader then reports "
            "green — the affirmative form of the failure Gate S exists to prevent. Add "
            "the class's row in the spec that first arms the tier", ev)
    if carries_no_sampler:
        if found:
            ev["seed_clause_verdict"] = "CONTRADICTED"
            ev["clause"] = "sampler_assertion_contradicted"
            raise RouteGate(
                f"the caller asserted this graph carries no sampler and it carries "
                f"{len(found)} seed-bearing node(s): " + ", ".join(
                    f"node {s['node_id']} ({s['class']})" for s in found) +
                ". The assertion is checked, not obeyed", ev)
        return
    if not found:
        ev["seed_clause_verdict"] = "INDETERMINATE"
        ev["clause"] = "no_seed_population"
        raise RouteGate(
            "the seed clause is INDETERMINATE on this graph and therefore UNPROVEN: it "
            "found no seed at all, and 'no seed was found' and 'every seed is pinned' "
            "are not the same verdict — the second is what this module used to print. "
            "Pass carries_no_sampler=True if the graph really carries none (the "
            "assertion is checked), or add the sampler class's SEED_NODES row", ev)


def seeds(graph):
    """Every seed in the graph and whether it is pinned.

    **Pinned means something different in each format, and both meanings are the honest
    one.** In save format the UI widget `control_after_generate` decides the next run's
    seed, so `randomize` is not pinned however concrete the current number looks. In API
    format that widget does not exist at all: a seed is pinned when it is a literal, and
    unpinned when it arrives over a link from a node that could compute anything.

    **A third state exists and it used to read as the first.** `literal = not
    isinstance(value, list)` is True for a key that is not there at all, so an API
    `KSampler` carrying no `seed` input was recorded `seed=None, seed_is_literal=True,
    pinned=True` — measured 2026-09-03, `verify` reported "1 seed(s) all pinned" on it.
    An absent seed is not a pinned one: nothing in the graph says what will run, which is
    the same thing a link says and worse. It is now `seed_is_literal=False,
    pinned=False`, carrying `seed_input_present=False` so a reader can tell the missing
    key from the link. (`gate_s_registration` did fail closed on the same graph, so this
    was confined to `verify`'s pinned clause and its verdict string.)
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        cls = n.get("type")
        spec = SEED_NODES.get(cls)
        if not spec:
            continue
        if api:
            key = SEED_INPUTS[cls]
            inputs = n.get("inputs") or {}
            present = key in inputs
            value = inputs.get(key)
            literal = present and not isinstance(value, list)
            out.append({"node_id": n.get("id"), "class": cls, "where": where,
                        "seed": value if literal else None,
                        "control_after_generate": None,
                        "seed_input_present": present,
                        "seed_is_literal": literal, "pinned": literal})
            continue
        wv = n.get("widgets_values") or []
        # The save-format branch answered `seed_is_literal: True` unconditionally —
        # including when `widgets_values` is shorter than the class's seed slot and `seed`
        # is therefore `None` — and emitted no `seed_input_present` key at all, so the two
        # formats' records did not answer the same question. Nothing gates on the field
        # (`pinned` is derived independently from `control_after_generate == "fixed"`, and
        # is correctly False on a short widget list), but the value is quoted verbatim in
        # Gate S's own refusal message (`literal={s['seed_is_literal']}`), so an operator
        # reading a Gate S halt on a truncated save-format sampler was told the seed is a
        # literal beside a `seed` of None. Mirrored on the API branch above: an absent seed
        # is not a literal one.
        # · ANDON — the positional read is cross-checked against the node's own declared
        # input names before it is trusted. See `_converted_widget_shift_andon`: a
        # converted `add_noise` left this function reading the seed as the string
        # `'fixed'`. `add_noise` rides the index set because `gate_s_registration` reads it
        # off this same widget list, and the andon must bound every index the family reads.
        _converted_widget_shift_andon(
            n, {name: spec[key] for name, key in
                (("seed", "seed"), ("control_after_generate", "control"),
                 ("add_noise", "add_noise")) if isinstance(spec.get(key), int)},
            wv, "SEED_NODES")
        present = len(wv) > spec["seed"]
        control = wv[spec["control"]] if len(wv) > spec["control"] else None
        out.append({"node_id": n.get("id"), "class": cls, "where": where,
                    "seed": wv[spec["seed"]] if present else None,
                    "control_after_generate": control,
                    "seed_input_present": present,
                    "seed_is_literal": present, "pinned": control == "fixed"})
    return out


def latents(graph):
    """Every video latent's width, height and frame count.

    Each record carries `checkable`: whether all three numbers are literals this graph
    pins. A dimension arriving over a link, or missing from a short `widgets_values`, is
    `None` — and a `None` is not a small frame, it is **no answer**. `verify` counts the
    checkable ones, because a list whose entries answer nothing is the shape the E08 defect
    wore.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        spec = LATENT_NODES.get(n.get("type"))
        if not spec:
            continue
        rec = {"node_id": n.get("id"), "class": n.get("type"), "where": where}
        if api:
            inp = n.get("inputs") or {}
            for key in ("width", "height", "length"):
                v = inp.get(key)
                rec[key] = v if not isinstance(v, list) else None
        else:
            wv = n.get("widgets_values") or []
            # · ANDON — the auditor's operand: a converted `length` widget left this
            # function reading the batch_size slot and Gate L reporting PROVEN. See
            # `_converted_widget_shift_andon`.
            _converted_widget_shift_andon(
                n, {k: spec[k] for k in ("width", "height", "length")}, wv,
                "LATENT_NODES")
            for key in ("width", "height", "length"):
                i = spec[key]
                rec[key] = wv[i] if len(wv) > i else None
        rec["checkable"] = None not in (rec["width"], rec["height"], rec["length"])
        out.append(rec)
    return out


def cameras(graph):
    """Every camera-trajectory node's width, height and frame count.

    Shaped exactly like `latents()` — including the `checkable` flag, for the same reason: a
    dimension arriving over a link is `None`, and a `None` is no answer rather than a small
    number. These records are reported separately from the latents so that Gate L's count of
    "frames checked" cannot be inflated by a node that sizes no frame at all.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        spec = CAMERA_NODES.get(n.get("type"))
        if not spec:
            continue
        rec = {"node_id": n.get("id"), "class": n.get("type"), "where": where}
        if api:
            inp = n.get("inputs") or {}
            for key in ("width", "height", "length"):
                v = inp.get(key)
                rec[key] = v if not isinstance(v, list) else None
        else:
            wv = n.get("widgets_values") or []
            # · ANDON — sibling 2 of the four positional tables. See
            # `_converted_widget_shift_andon`.
            _converted_widget_shift_andon(
                n, {k: spec[k] for k in ("width", "height", "length")}, wv,
                "CAMERA_NODES")
            for key in ("width", "height", "length"):
                i = spec[key]
                rec[key] = wv[i] if len(wv) > i else None
        rec["checkable"] = None not in (rec["width"], rec["height"], rec["length"])
        out.append(rec)
    return out


def camera_widget_order_evidence(graph, expect):
    """The empirical SECOND reading of `CAMERA_NODES` widget order, on a save-format graph.

    `CAMERA_NODES` and the camera entry of `LATENT_NODES` were each derived from a single
    source — the `get_node` schema — because no served template wires this tier to check
    them against. Positional indices derived once and never confirmed are exactly what the
    `LATENT_NODES` warning is about, so the confirmation is taken here instead: read the
    values standing at those indices on the file the cloud will actually execute, and hand
    back what was found. `expect` is `{"width": .., "height": .., "length": ..}` — the
    numbers the builder set.

    Returns evidence with `agrees` per node. It reports; the caller decides whether a
    disagreement halts, because on an API-format graph there is nothing positional to
    confirm and the honest answer there is `not_applicable`, not `PASS`.
    """
    graph = normalise_graph(graph)
    # `gate`/`andon` ride the report because a caller raises RouteGate with it as the evidence
    # (found by the tests domain's evidence walk at the wave-8 merge; core-gates' own census
    # keyed on raise sites and could not see a dict returned to one).
    ev = {"gate": "ROUTE", "andon": "RouteGate", "clause": "camera_widget_order",
          "check": "camera widget order (empirical second reading)", "expect": dict(expect),
          "nodes": []}
    if is_api_format(graph):
        ev["verdict"] = "not_applicable — API format keys inputs by name, nothing positional"
        return ev
    for where, n in _iter_nodes(graph):
        spec = CAMERA_NODES.get(n.get("type")) or LATENT_NODES.get(n.get("type"))
        if not spec or n.get("type") not in set(CAMERA_NODES) | {"WanCameraImageToVideo"}:
            continue
        wv = n.get("widgets_values") or []
        # · ANDON — sibling 3 of the four positional tables, and the one where a shift is
        # least visible: this function REPORTS a disagreement with the builder's numbers,
        # which says nothing at all when the shifted values happen to equal what the
        # builder set. A reading taken off shifted slots is not the empirical second
        # reading `LATENT_NODES`' warning says is owed. It raises here for the same reason
        # its nearest sibling `hosted_enums` raises while returning values.
        _converted_widget_shift_andon(
            n, {k: spec[k] for k in ("width", "height", "length")}, wv,
            "CAMERA_NODES" if n.get("type") in CAMERA_NODES else "LATENT_NODES")
        found = {k: (wv[spec[k]] if len(wv) > spec[k] else None)
                 for k in ("width", "height", "length")}
        ev["nodes"].append({
            "node_id": n.get("id"), "class": n.get("type"), "where": where,
            "indices": {k: spec[k] for k in ("width", "height", "length")},
            "found": found, "widgets_values": wv,
            "agrees": all(found[k] == expect[k] for k in ("width", "height", "length")),
        })
    # · ANDON (reported, not raised — this function reports and the caller decides) — the
    # last member of the empty-population family this repo has closed five times.
    # `disagree` is empty when `ev["nodes"]` is empty, so this used to return
    # `agrees: True` with the verdict "the declared indices carry the builder's numbers on
    # 0 node(s)". Measured 2026-09-04 in this worktree: a save-format graph of
    # `UNETLoader` + `KSampler` and NO camera node returned that affirmative, and so did a
    # graph whose camera node's CLASS had been renamed (`WanCameraImageToVideoV2`) — which
    # is the drift this function exists to catch. Its siblings all refuse an empty
    # declared population: `g2_completeness`, `gate_b_batching`,
    # `gate_s_seed_registration`, `g5_openpose_conformance`, `rig_gates.gate_n_names`.
    #
    # This function is the empirical SECOND reading the `LATENT_NODES` warning says is
    # owed for `CAMERA_NODES`' positional indices, so an affirmative over an empty
    # population is a confirmation that the indices were never read. `agrees` is `None`
    # rather than `False` because nothing was contradicted either; a caller taking this as
    # its confirmation must not read a third answer as the first, and `None` is the value
    # `if ev["agrees"]` and `if not ev["agrees"]` disagree about.
    #
    # It is NOT the API branch's `not_applicable`, which is a different fact: there, there
    # is nothing positional to confirm at all. Bounded honestly: there is no production
    # call site today (grep across tools/ finds it only at its definition), so no spend is
    # affected now; the cost falls on the first caller that wires it.
    if not ev["nodes"]:
        ev["verdict"] = ("INDETERMINATE — no node in this graph carries a recorded "
                         "widget-index row, so the declared indices were never read and "
                         "'nothing was checkable' is not 'the indices agree'")
        ev["agrees"] = None
        ev["classes_with_a_recorded_row"] = sorted(
            set(CAMERA_NODES) | {"WanCameraImageToVideo"})
        ev["classes_in_this_graph"] = sorted(
            {str(n.get("type")) for _, n in _iter_nodes(graph)})
        return ev
    disagree = [n for n in ev["nodes"] if not n["agrees"]]
    ev["verdict"] = (
        "CONTRADICTED — the declared indices do not carry the builder's numbers"
        if disagree else
        f"the declared indices carry the builder's numbers on {len(ev['nodes'])} node(s)")
    ev["agrees"] = not disagree
    return ev


def _camera_widget_order_receipt(graph, ev, supplied):
    """`camera_widget_order_evidence` for `verify`, or a row saying why it was not taken.

    The `expect` this reading is checked against is the frame the run is being graded on:
    the caller's supplied triple when there is one, otherwise the single frame the graph
    itself pins. When the graph pins several different frames there is no one thing to
    confirm the indices against — `verify`'s own clash clause is what answers that — and a
    row saying so is recorded rather than a verdict over a number nobody chose.
    """
    frames = {(f["width"], f["height"], f["length"])
              for f in ev["frame_legality"] if f["source"] == "graph"}
    if supplied is not None:
        target = (supplied["width"], supplied["height"], supplied["length"])
    elif len(frames) == 1:
        target = next(iter(frames))
    else:
        return {"gate": "ROUTE", "andon": "RouteGate", "clause": "camera_widget_order",
                "verdict": ("NOT TAKEN — the second reading needs one frame to check the "
                            "declared indices against, and this call supplied none while "
                            f"the graph pins {sorted(frames)}"),
                "nodes": [], "agrees": None, "expect": None,
                "graph_frames": sorted(frames)}
    return camera_widget_order_evidence(
        graph, {"width": target[0], "height": target[1], "length": target[2]})


def _frame_triple(frame):
    """`(width, height, length)` from a tuple or a mapping, or raise saying what arrived.

    ⚠ **It used to COERCE, in front of a guard whose whole job was to refuse.** Wave 8
    added `frame_legality`'s int-type refusal with the reason written out — "a wrong TYPE
    is a malformed question and raises" — and it could not fire on the only path a caller
    supplies a frame, because both return paths here read `int(...)` first. Measured
    2026-09-04: `_frame_triple((832.9, 480.4, 81))` returned `(832, 480, 81)` and
    `_frame_triple(('832','480','81'))` returned `(832, 480, 81)` — a float truncated and
    a string parsed, both silently, so the guard downstream saw ints on every call. A
    builder that derived a non-integer frame (a division that did not floor) had it
    truncated, and `verify`'s evidence and the `SAVED_ADMISSION_OK` line then quoted a
    frame that is not the number the builder computed — while the supplied-vs-graph clash
    clause compared the TRUNCATED value and could not see the difference either.

    The values are now passed through untouched, so `frame_legality` states the ONE
    refusal for a malformed frame. Nothing in `tools/` supplies anything but ints today
    (read at the seven `verify(..., frame=...)` call sites).
    """
    if isinstance(frame, dict):
        try:
            return frame["width"], frame["height"], frame["length"]
        except KeyError as exc:
            raise RouteGate(
                f"the supplied frame is missing {exc.args[0]!r}; Gate L needs all three of "
                f"width, height and length, and two out of three proves nothing",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_triple",
                 "supplied": frame}) from None
    if isinstance(frame, (list, tuple)) and len(frame) == 3:
        return frame[0], frame[1], frame[2]
    raise RouteGate(
        f"the supplied frame {frame!r} is not (width, height, length) or a mapping "
        f"carrying those three keys",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_triple",
         "supplied": frame})


def _frame_form(rules, family):
    """`(modulus, residue)` parsed out of a family's declared `frame_form`.

    The rule is DATA — `GENERATOR_RULES['wan']['frame_form'] == '4n+1'` — and the code
    used to test `(length - 1) % 4` against a literal 4, so the declared field was never
    read. A second family declaring `8n+1` would have been graded on wan's temporal rule
    while its own row said otherwise, and nothing would have printed differently.
    `gates.GeneratorProfile` already stores modulus and residue separately; this parses
    the same two numbers out of the string form this table uses.
    """
    form = rules.get("frame_form")
    try:
        mod, res = str(form).split("n+")
        return int(mod), int(res)
    except (AttributeError, TypeError, ValueError):
        raise RouteGate(
            f"generator family {family!r} declares frame_form {form!r}, which is not of "
            f"the form '<modulus>n+<residue>'. The rule is data and it is read; a family "
            f"whose row cannot be parsed is graded on nobody's rule rather than silently "
            f"on wan's",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_form",
             "family": family, "rules": rules}) from None


def _family_rules(family):
    """Resolve a family or G1 profile name to `(rules_key, rules)`.

    `family='wan'` hits GENERATOR_RULES directly. A G1 profile name (`wan-vace`, …) maps
    through PROFILE_FAMILY onto the same row so Gate L and G1 share one vocabulary
    (F-a9e809dd). Unknown names still raise `unknown_generator_family`.
    """
    rules = GENERATOR_RULES.get(family)
    if rules is not None:
        return family, rules
    mapped = PROFILE_FAMILY.get(family)
    if mapped is not None:
        rules = GENERATOR_RULES.get(mapped)
        if rules is not None:
            return mapped, rules
    known = sorted(set(GENERATOR_RULES) | set(PROFILE_FAMILY))
    raise RouteGate(f"no recorded frame rules for generator family {family!r}; the "
                    f"constraint is recorded per model in the spec that first uses it",
                    {"gate": "ROUTE", "andon": "RouteGate",
                     "clause": "unknown_generator_family",
                     "family": family, "known": known})


def frame_legality(width, height, length, family="wan"):
    """Gate L, standalone: is this frame legal for that generator? Derive, then round.

    Returns the verdict and, when illegal, the nearest legal value in each direction — so a
    caller rounds to a stated number instead of guessing one.

    **Zero and negative are illegal, and they used not to be.** Measured 2026-09-03,
    `frame_legality(0, 0, 1)` and `frame_legality(-16, -16, 1)` both returned
    `legal=True` with no problems, because 0 and -16 are multiples of 16 and (1-1) is a
    multiple of 4: a builder whose frame derivation returned 0 got a green Gate L. A
    non-integer dimension raised a bare `TypeError` from the modulo, which is not an
    exception any caller of a gate is catching — that now raises `RouteGate` naming the
    value. The split is deliberate: a wrong TYPE is a malformed question and raises; a
    wrong VALUE is an illegality and is reported through `problems` like every other,
    so `verify` halts on it with the whole evidence dict rather than a bare error.
    """
    rules_key, rules = _family_rules(family)
    for axis, value in (("width", width), ("height", height), ("length", length)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise RouteGate(
                f"{axis} {value!r} is not an int ({type(value).__name__}); Gate L "
                f"compares it against a divisibility rule and would otherwise raise a "
                f"bare TypeError out of the modulo",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "frame_type",
                 "family": family, "width": width, "height": height, "length": length})
    m = rules["dim_multiple"]
    modulus, residue = _frame_form(rules, rules_key)
    problems = []
    for axis, value in (("width", width), ("height", height)):
        if value <= 0:
            problems.append(f"{axis} {value} is not positive")
        elif value % m:
            problems.append(f"{axis} {value} is not a multiple of {m} "
                            f"(nearest: {m * round(value / m)})")
    if length <= 0:
        problems.append(f"length {length} is not positive")
    elif (length - residue) % modulus:
        problems.append(
            f"length {length} is not of the form {modulus}n+{residue} "
            f"(nearest: {modulus * round((length - residue) / modulus) + residue})")
    if length > rules["max_frames"]:
        problems.append(f"length {length} exceeds the {rules['max_frames']}-frame "
                        f"trained horizon")
    return {"gate": "L", "family": family, "width": width, "height": height,
            "length": length, "rules": rules, "frame_form": f"{modulus}n+{residue}",
            "problems": problems, "legal": not problems}


#: Where a hosted tier's enum values sit in SAVE format's positional `widgets_values`.
#: Read off the file the cloud converted, 2026-08-13, and required to agree with the
#: `get_node` declaration order — the same two-reading standard the camera rows carry.
#: `gate_saved_graph.WIDGET_INDEX` holds the full row for the same class; this is the
#: subset Gate L needs, kept here so `route_gates` does not import the gate that imports it.
HOSTED_ENUM_WIDGETS = {
    "Wan2ReferenceVideoApi": {"resolution": 3, "ratio": 4, "duration": 5},
}


def hosted_enums(graph):
    """EVERY hosted node's `(where, node_id, resolution, ratio, duration)`, EITHER format.

    Found by the field rather than by the class name in API format, because the thing being
    read is the field. In save format there are no field names at all — the values are
    positional — so the class-keyed table above is the only way in, and a class missing
    from it contributes nothing rather than guessing an index.

    ⚠ **It returns a LIST because it used to return the first match.** Measured
    2026-09-03 on a save-format graph with two `Wan2ReferenceVideoApi` nodes — the first
    at ('720P', '16:9', 5) and the second at ('4K', '99:1', 900) — this function returned
    the first and `verify`'s hosted branch checked only that tuple, reporting "hosted tier
    wan2.7-r2v at 720P 16:9 5s — enum-legal". The illegal second node was named nowhere
    in the evidence, so a two-shot hosted graph could carry an out-of-contract resolution,
    ratio or duration under a green Gate L receipt.

    ⚠ **The tuple gained `where` 2026-09-05 (F-2fa07723) and its arity changed from 4 to
    5.** The loop read `for _where, n in _iter_nodes(graph)` and DISCARDED the level, so
    the per-node billing andon and the enum refusal above it could not name which node they
    were about — on the one tier that bills per node. Measured in this worktree on a
    save-format graph carrying a top-level `Wan2ReferenceVideoApi` id 6 and a blueprint
    (`name: 'inner'`) `Wan2ReferenceVideoApi` id 6, both at ('720P','16:9',5): this
    function returned `[(6,'720P','16:9',5), (6,'720P','16:9',5)]`, `verify(g,
    hosted_tier='wan2.7-r2v')` raised "the graph carries 2 wan2.7-r2v node(s) (6, 6)", and
    the two rows in `hosted_frame_legality_nodes` were keyed `node_id: 6` and `node_id: 6`
    and carried no `where`; making the blueprint node illegal instead produced "Gate L
    (hosted tier): node 6: resolution 4K is not one of ...", which does not say which node
    6. Node identity in this walk is the PAIR `(where, id)` (wave 18) — what every DICT
    row family on this page already records, and this was the one TUPLE family that did
    not. The only consumer is `verify`'s hosted branch, in this module.
    """
    graph = normalise_graph(graph)
    api = is_api_format(graph)
    out = []
    for where, n in _iter_nodes(graph):
        if api:
            inp = n.get("inputs") or {}
            if "model.resolution" in inp:
                out.append((where, n.get("id"), inp.get("model.resolution"),
                            inp.get("model.ratio"), inp.get("model.duration")))
        else:
            idx = HOSTED_ENUM_WIDGETS.get(n.get("type"))
            if idx:
                wv = n.get("widgets_values") or []
                # · ANDON — the positional read is cross-checked against the node's own
                # declared input names before it is trusted. See `_hosted_enum_shift_andon`.
                _hosted_enum_shift_andon(n, idx, wv)
                out.append((where, n.get("id"), wv[idx["resolution"]], wv[idx["ratio"]],
                            wv[idx["duration"]]))
    return out


def _shifted_widget_names(node, highest):
    """The converted widgets that may have SHIFTED a positional read up to `highest`.

    ONE reading, shared by `_hosted_enum_shift_andon` and `_converted_widget_shift_andon`,
    so the hosted enum block and the three other positional tables cannot disagree about
    what a shift is. A converted widget shifts a read unless its own slot is KNOWN to sit
    above every index the reader touches; a name this repo has no recorded index for has an
    UNKNOWN position, and an unknown position is not evidence of no shift — the third
    answer, the same one `latents()` gives a dimension arriving over a link.
    """
    known = known_widget_indices(node.get("type"))
    return sorted({name for name in _save_format_converted_widget_names(node)
                   if known.get(name) is None or known[name] <= highest})


def _converted_widget_shift_andon(node, indices, wv, table):
    """Refuse a save-format node whose recorded widget positions cannot be trusted.

    ⚠ **The shift clause existed for ONE of the four positional tables.** Wave 18 gave
    `HOSTED_ENUM_WIDGETS` `_hosted_enum_shift_andon`, whose own honesty note says "a future
    `HOSTED_ENUM_WIDGETS` row whose seed slot is not last would not be [caught]" — and the
    siblings were never enumerated. `latents()` over `LATENT_NODES`, `cameras()` and
    `camera_widget_order_evidence()` over `CAMERA_NODES`, and `seeds()` over `SEED_NODES`
    all read `wv[spec[key]]` positionally with no shift clause, although
    `known_widget_indices(cls)` — built in the same wave, over all four tables — is the
    reading that detects it.

    Measured 2026-09-05 in this worktree on a save-format graph of
    `UNETLoader('wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors')` + pinned `KSampler` +
    `WanImageToVideo`: honest widgets `[832, 480, 81, 1]` gave `latents()` width 832,
    height 480, length 81 and `verify(g)` PROVEN. Converting the `length` widget to an
    input — an ordinary ComfyUI edit, after which the save format DROPS that value from
    `widgets_values` and declares the slot as `{"name":"length","widget":{"name":"length"}}`
    — leaves widgets `[832, 480, 1]`; `_save_format_converted_widget_names` returned
    `['length']` and `known_widget_indices('WanImageToVideo')` returned
    `{'width':0,'height':1,'length':2}`, so the shift was fully readable, yet `latents()`
    returned `{'width': 832, 'height': 480, 'length': 1, 'checkable': True}` — the
    batch_size slot read as the frame count — and `verify(g)` RETURNED PROVEN with
    `frame_legality` `length: 1, legal: true`, "1 frame(s) checked and generator-legal".
    That is the vacuous Gate L state E08 paid for, on the last gate before a paid
    submission, re-entered through a widget conversion.

    `length` is the one conversion of the four that fails OPEN: converting `width` or
    `height` shifts a non-multiple-of-16 into the dimension slots and Gate L refuses, while
    1 is a legal 4n+1 count. The other three tables were caught only by NEIGHBOURING
    clauses answering about slots nobody read — a converted `camera_pose` left `cameras()`
    reporting width 480 / height 81 / length None (caught by `checkable` falling to False),
    and a converted `add_noise` left `seeds()` reading the seed as the string `'fixed'`
    (caught by Gate S's "not pinned"). A refusal by name is not a neighbour's accident.

    It keeps its OWN clause word rather than reusing the hosted one: the hosted refusal's
    receipts, its `highest_enum_index` evidence key and wave 18's `HALT_ROUTES` all carry
    `converted_widget_shifts_enum_indices`, and "enum indices" is not what `LATENT_NODES`
    records. Both read the same converted names through `_shifted_widget_names`.

    Save format only. In API format inputs are keyed by NAME, there is nothing positional
    to shift, and inventing a refusal there would be the category error
    `camera_widget_order_evidence` answers `not_applicable` on.
    """
    shifting = _shifted_widget_names(node, max(indices.values()))
    if not shifting:
        return
    raise RouteGate(
        f"node {node.get('id')} ({node.get('type')}) declares {shifting} as a CONVERTED "
        f"widget, so this class's recorded widget indices {indices} (from {table}) no "
        f"longer address the fields they name — every value at or after the converted "
        f"slot is shifted, and a name with no recorded index could sit anywhere. Reading "
        f"them anyway would grade a number that is not the field it is quoted as, on the "
        f"gates that stand before a paid submission",
        {"gate": "ROUTE", "andon": "RouteGate",
         "clause": "converted_widget_shifts_recorded_indices",
         "node_id": node.get("id"), "class": node.get("type"),
         "converted": shifting, "indices": dict(indices), "table": table,
         "recorded_widget_indices": known_widget_indices(node.get("type")),
         "highest_index_read": max(indices.values()),
         "declared_input_names": sorted(set(_save_format_input_names(node))),
         "widgets_values": wv})


def _hosted_enum_shift_andon(n, idx, wv):
    """Refuse a save-format hosted node whose positional enum indices cannot be trusted.

    ⚠ **The save-format branch read the hosted tier's three enum values purely
    positionally** — `if len(wv) > max(idx.values()): out.append((id, wv[3], wv[4],
    wv[5]))` — with no check that the widget list had not been SHIFTED, which is the
    ordinary consequence of a widget being converted to an input in Comfy's save format.
    This module already knows converted widgets exist and reads them:
    `_save_format_input_names` exists precisely to pull `slot['widget']['name']` out of
    the save-format `inputs` list.

    Measured 2026-09-04 in this worktree on a two-node `Wan2ReferenceVideoApi` graph using
    the repo's own fixture widget layout (model, prompt, negative, resolution, ratio,
    duration, seed, control), where node 2's `duration` widget had been converted to an
    input: `hosted_enums` returned `[(1,'720P','16:9',5), (2,'720P','16:9',7)]` — node 2's
    duration read off the SEED slot, a value legal under
    `HOSTED_TIER_RULES['wan2.7-r2v']['duration_s'] == (2, 10)` and not the number that
    runs, which arrives over the link. Converting `prompt`, which sits BELOW all three
    enum indices, shifted every one: `[(4,'16:9',5,7)]`.

    The truncation direction is the same defect wearing the other hat: a node whose widget
    list falls below the highest index contributed NOTHING to `found`, in silence, and
    `verify`'s per-node billing clause ("one submission carrying two billable nodes is two
    charges against a ceiling counted per submission") then counted a population the graph
    does not have. Both answer with a refusal here rather than with a number nobody read.

    Bounded honestly: for `Wan2ReferenceVideoApi` the seed and control widgets sit at the
    two highest indices, so any shift also breaks `seeds()`' `control_after_generate` read
    and Gate S refuses first — measured, `verify` on the shifted graph raised "Gate S
    cannot be armed on this graph: node 2 ... control_after_generate=None". Today the
    escape is caught by a neighbouring clause; a future `HOSTED_ENUM_WIDGETS` row whose
    seed slot is not last would not be, and this clause is on the direction that bounds.
    """
    highest = max(idx.values())
    known = known_widget_indices(n.get("type"))
    # A converted widget shifts the enum block unless its own slot is KNOWN to sit above
    # every enum index. ONE reading, shared with `_converted_widget_shift_andon` — see
    # `_shifted_widget_names`.
    shifting = _shifted_widget_names(n, highest)
    if shifting:
        raise RouteGate(
            f"node {n.get('id')} ({n.get('type')}) declares {shifting} as a CONVERTED "
            f"widget, so this class's positional enum indices {idx} no longer address the "
            f"fields they name — every value at or after the converted slot is shifted, "
            f"and a name with no recorded index could sit anywhere. Reading them anyway "
            f"would grade a number that is not the field it is quoted as, on a tier that "
            f"bills per node",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "converted_widget_shifts_enum_indices",
             "node_id": n.get("id"), "class": n.get("type"),
             "converted": shifting, "indices": dict(idx),
             "recorded_widget_indices": known,
             "highest_enum_index": highest,
             "declared_input_names": sorted(set(_save_format_input_names(n))),
             "widgets_values": wv})
    if len(wv) <= max(idx.values()):
        raise RouteGate(
            f"node {n.get('id')} ({n.get('type')}) carries {len(wv)} widget value(s) and "
            f"this class's enum indices reach {max(idx.values())}, so its resolution, "
            f"ratio and duration cannot be read at all. Dropping it from the population "
            f"in silence is what this clause replaces: Gate L's per-node billing count "
            f"then describes a graph with fewer billable nodes than the one submitted",
            {"gate": "ROUTE", "andon": "RouteGate",
             "clause": "hosted_enum_widgets_truncated",
             "node_id": n.get("id"), "class": n.get("type"),
             "n_widgets": len(wv), "highest_index_required": max(idx.values()),
             "indices": dict(idx), "widgets_values": wv})


def hosted_frame_legality(resolution, ratio, duration, tier):
    """Gate L, for a tier that constrains by enum rather than by pixels.

    The clause `frame_legality` above cannot express: `wan2.7-r2v` never receives a width,
    a height or a frame count from us, so asking whether 1024 is a multiple of 16 answers
    a question this route does not pose. What it does constrain is a resolution enum, a
    ratio enum and an integer number of seconds — and every one of those has an illegal
    value the submission would be refused for, which is what makes this a gate and the
    pixel clause a category error here.

    Returns the same shape `frame_legality` does, so a caller reports both the same way.
    """
    rules = HOSTED_TIER_RULES.get(tier)
    if rules is None:
        raise RouteGate(
            f"no recorded tier rules for {tier!r}; a hosted tier's constraints are recorded "
            f"in the spec that first uses it, from that tier's own node contract",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unknown_hosted_tier",
             "known": sorted(HOSTED_TIER_RULES)})
    problems = []
    if resolution not in rules["resolutions"]:
        problems.append(f"resolution {resolution!r} is not one of {rules['resolutions']}")
    if ratio not in rules["ratios"]:
        problems.append(f"ratio {ratio!r} is not one of {rules['ratios']}")
    lo, hi = rules["duration_s"]
    if not isinstance(duration, int) or isinstance(duration, bool):
        problems.append(f"duration {duration!r} is not an integer number of seconds")
    elif not lo <= duration <= hi:
        problems.append(f"duration {duration} is outside {lo}..{hi} seconds")
    return {"gate": "L", "tier": tier, "resolution": resolution, "ratio": ratio,
            "duration_s": duration, "rules": {k: list(v) if isinstance(v, tuple) else v
                                              for k, v in rules.items()},
            "problems": problems, "legal": not problems}


def gate_s_registration(graph, registered, *, carries_no_sampler=False):
    """Gate S · ANDON — every seed about to run was pre-registered in a committed list.

    E04's andon, and it guards a failure with no technical symptom at all: every other gate
    passes on a seed-shopped run, and what is wrong is epistemic. A rule forbids; a list
    removes the possibility, and git timestamps the list ahead of the artifacts it governs.

    It binds in **both** directions. An unregistered seed is the obvious clause. A
    registered list that the graph does not draw from is the second: a graph running some
    other number while a tidy list sits in the repo is the same defect wearing a receipt.

    **The population it grades is stated, and an empty one refuses.** The registration
    clause grades `live` — the seeds whose node adds noise — because the second expert of a
    two-expert split runs `add_noise=disable` and its seed draws nothing. That filter can
    empty the population, and the verdict then stated a property of the committed list over
    nothing at all (measured 2026-09-04; see the andon below). A graph whose every sampler
    declines noise is refused, and the PASS verdict now carries both counts and names the
    exempted nodes, so a record where one sampler was exempted cannot be read as one where
    every seed found was checked.
    """
    graph = normalise_graph(graph)
    found = seeds(graph)
    reg = list(registered or [])
    # The evidence's `gate` is the id of the andon that will raise, which is
    # `RouteGate.gate` == "ROUTE". It used to read "S": the halt record carries the gate id
    # beside the evidence JSON (two separate lines when this was written; one six-key
    # `<TOOL>_HALT` line since the wave-12 merge — citation corrected 2026-09-04),
    # so a receipt for this clause said ROUTE on one and S on the other — and "S" is
    # already the id of a DIFFERENT andon (`errors.GateSSeedRegistration`), carrying
    # different evidence keys, so a reader resolving the id landed on the wrong class.
    # The clause's own name rides beside it instead. `pairing` on this page already does
    # it this way (`ev["gate"] == "PAIR"` and it raises `PairGate`).
    ev = {"gate": "ROUTE", "andon": "RouteGate", "clause": "gate_s_registration",
          "registered": reg, "seeds": found}
    # · ANDON — the third answer. See `_seed_population_andon`: a sampler class with no
    # SEED_NODES row makes `seeds()` return [] and this function then reported "0
    # noise-bearing seed(s), all pinned and all drawn from the committed list".
    _seed_population_andon(graph, found, ev, carries_no_sampler)
    if not reg:
        raise RouteGate(
            "Gate S: no seed list was pre-registered, so no seed may be varied at all. "
            "Commit the list before the first submission — that is what makes it a "
            "registration rather than a note", ev)
    loose = [s for s in found if not s["pinned"]]
    if loose:
        raise RouteGate(
            "Gate S: " + ", ".join(
                f"node {s['node_id']} ({s['class']}) is not pinned "
                f"(control_after_generate={s['control_after_generate']!r}, "
                f"literal={s['seed_is_literal']})" for s in loose), ev)
    # add_noise="disable" samplers take no noise from their seed; theirs is inert and is
    # reported rather than demanded, so a two-expert split does not need a second entry.
    #
    # **The two formats spell `inputs` differently and that is not cosmetic.** In API format
    # it is a mapping of name -> literal-or-link; in save format it is a LIST of slot dicts.
    # Calling `.get` on the list raised outright on the first save-format graph whose
    # sampler had any connected input (measured 2026-08-12, E10): E09's saved samplers had
    # empty input arrays, `or {}` swallowed them, and the defect waited for a graph with
    # links. It is a crash rather than a wrong answer, which is the good kind of latent bug.
    #
    # ⚠ **The record was resolved back to its node by NODE ID ALONE, and `where` — which
    # `seeds()` records for exactly this purpose — was discarded.** Subgraph blueprints
    # carry their own node-id namespace, so a blueprint node sharing an id with a
    # top-level node is ordinary; `_walk_nodes`' own docstring records a served template
    # presenting 4 nodes at the top level and hiding 30 inside a blueprint. Every
    # colliding record therefore read its `add_noise` off the FIRST node the walk yielded
    # — always the top-level one — and the `adds_noise` filter that decides which seeds
    # the registration clause grades was answered about the wrong node.
    #
    # Measured 2026-09-04 in this worktree on a save-format graph carrying the two-expert
    # split this gate documents — `KSamplerAdvanced` id 2 (`add_noise=enable`, seed 7),
    # `KSamplerAdvanced` id 3 (`add_noise=disable`, seed 7, legitimately exempt) — plus
    # one blueprint holding its OWN `KSamplerAdvanced` id 3 with `add_noise=enable` and
    # seed 999999999: `seeds()` correctly returned `[('top',2,7), ('top',3,7),
    # ('inner',3,999999999)]`, and this function RETURNED with `seeds_noise_bearing: 1`
    # and `seeds_exempt_add_noise_disable: [3, 3]`. The identical graph with the blueprint
    # node renumbered to 9 REFUSED. The wave-16 `found and not live` andon does not save
    # this shape — it fires only when EVERY seed is exempted, and the live top-level
    # sibling keeps `live` non-empty.
    #
    # Node identity is the PAIR `(where, id)`, and the resolution is TOTAL: a record whose
    # node cannot be re-found raises rather than defaulting `adds = True`, because the
    # default silently decides which population the registration clause grades.
    api = is_api_format(graph)
    live = []
    for s in found:
        n = next((x for w, x in _iter_nodes(graph)
                  if (w, str(x.get("id"))) == (s.get("where"), str(s["node_id"]))), None)
        if n is None:
            raise RouteGate(
                f"Gate S cannot resolve the seed record for node {s['node_id']} at level "
                f"{s.get('where')!r} back to a node in this graph, so the `add_noise` "
                f"reading that decides whether its seed is graded has no operand. A "
                f"default here would put a seed into — or out of — the registration "
                f"clause's population under a receipt that cannot say which node it came "
                f"from, and node identity in this walk is the pair (where, id) because "
                f"blueprint ids are a separate namespace",
                dict(ev, clause="seed_node_unresolvable",
                     unresolved={"where": s.get("where"), "node_id": s["node_id"],
                                 "class": s.get("class")},
                     levels=sorted({str(w) for w, _ in _iter_nodes(graph)})))
        slot = SEED_NODES[s["class"]].get("add_noise")
        adds = True
        if slot is not None:
            if api:
                adds = (n.get("inputs") or {}).get("add_noise", "enable") \
                    not in ("disable", False)
            else:
                wv = n.get("widgets_values") or []
                # · ANDON — the positional read, cross-checked in THIS function's own body.
                # ⚠ Wave 20 wired `_converted_widget_shift_andon` into four readers by hand
                # and nothing required the fifth. Measured 2026-09-05 by walking this
                # module's AST for subscripts of a widget list: six functions index widget
                # values positionally — `seeds`, `latents`, `cameras`,
                # `camera_widget_order_evidence`, `hosted_enums` and this one — and this
                # one called no shift andon at all. Its `add_noise` read was bounded only
                # TRANSITIVELY, by a hand-maintained index set two functions away
                # (`seeds()` passes `add_noise` into the andon's index dict with the
                # comment "`add_noise` rides the index set because `gate_s_registration`
                # reads it off this same widget list"), and by the fact that this
                # function's population comes from `seeds()`. No shifted graph escaped —
                # the gap was that the coverage was a comment plus a hand-kept dict, on the
                # walk that decides whether credits are spent, and the next positional
                # table or the next reader joined the population only if someone
                # remembered. The read is behind the andon now, so no exemption is needed
                # and `tests/test_amend_w22_core_gates.py`'s structural census can require
                # every member of the family to call one in its own body.
                _converted_widget_shift_andon(n, {"add_noise": slot}, wv, "SEED_NODES")
                adds = (wv[slot] if len(wv) > slot else "enable") not in ("disable", False)
        s["adds_noise"] = adds
        if adds:
            live.append(s)
    inert = [s for s in found if not s["adds_noise"]]
    ev["seeds_found"] = len(found)
    ev["seeds_noise_bearing"] = len(live)
    ev["seeds_exempt_add_noise_disable"] = [s["node_id"] for s in inert]
    # The receipt's own tell for the wrong-node read above was a duplicate id printed
    # twice in the line above, which a reader had to notice to catch it. Node identity is
    # the pair, so the exempt population is also recorded as pairs — this key cannot
    # repeat an identity, and the bare-id list is kept because reports quote it.
    ev["seeds_exempt_nodes"] = [{"where": s.get("where"), "node_id": s["node_id"]}
                                for s in inert]
    # · ANDON — the population the `adds_noise` filter above can empty. `_seed_population_
    # andon` supplies the third answer only when `seeds()` itself is empty; nothing bounded
    # the case where seeds were FOUND and every one of them was exempted. Measured
    # 2026-09-04 in this worktree on a save-format graph whose only sampler is a
    # `KSamplerAdvanced` with `add_noise="disable"` carrying 999999999: `seeds()` returned
    # that record, `unrecorded_seed_sources` was empty, and this function RETURNED with the
    # verdict "0 noise-bearing seed(s), all pinned and all drawn from the committed list of
    # 1" — a receipt asserting the committed list [7] governed the run. The spend record
    # then cannot be told apart from one where every seed found was checked, which is the
    # epistemic failure with no technical symptom that `GateSSeedRegistration`'s docstring
    # says this gate exists for. Gate S's own empty-registry clause and the four sibling
    # clauses on these two pages (`g2_completeness`, `g5_openpose_conformance`,
    # `gate_b_batching`, `rig_gates.gate_n_names`) all refuse an empty declared population.
    #
    # It refuses rather than reporting: the exemption is legitimate for the SECOND expert of
    # a two-expert split, where a live sampler is graded beside it, and a graph in which
    # nothing draws noise at all is a graph Gate S cannot grade. `carries_no_sampler=` is
    # not the answer for it either — that assertion is CONTRADICTED here, correctly, because
    # the graph does carry samplers.
    if found and not live:
        ev["seed_clause_verdict"] = "INDETERMINATE"
        raise RouteGate(
            "Gate S is INDETERMINATE on this graph and therefore UNPROVEN: it found "
            f"{len(found)} seed-bearing node(s) and every one of them declines noise "
            "(add_noise=disable), so the registration clause would grade an EMPTY "
            "population and then state a property of the committed list over it — " +
            ", ".join(f"node {s['node_id']} ({s['class']}) carries seed {s['seed']}"
                      for s in found) +
            f", against the committed list {reg}. 'No seed was graded' and 'every seed "
            f"was drawn from the list' are not the same verdict", ev)
    unregistered = [s for s in live if s["seed"] not in reg]
    if unregistered:
        raise RouteGate(
            "Gate S: " + ", ".join(
                f"node {s['node_id']} would run seed {s['seed']}" for s in unregistered) +
            f", which the committed list {reg} does not pre-register. A seed chosen after "
            f"seeing a result turns a measurement into a selection of one", ev)
    # The verdict states the POPULATION it graded, not only the part of it that passed. It
    # used to read "{live} noise-bearing seed(s), all pinned and all drawn from the
    # committed list of {reg}" — a record in which one of two samplers was exempted read
    # exactly like a record in which every seed found was checked. The leading count is
    # unchanged, because the repo's reports and `docs/experiments/*` quote that prefix.
    ev["verdict"] = (
        f"no sampler in this graph (asserted by the caller and checked), so no seed was "
        f"drawn against the committed list of {len(reg)}" if not found else
        f"{len(live)} noise-bearing seed(s) of {len(found)} seed(s) found, all pinned and "
        f"all drawn from the committed list of {len(reg)}"
        # The exempted nodes are named by the pair `(where, id)`, printed `level/id`. A
        # bare id is not an identity in this walk — the same receipt used to read
        # "node(s) 3, 3" for a top-level node and a blueprint node, which was the only
        # visible tell of the wrong-node read the lookup above now makes impossible.
        + (f"; {len(inert)} exempted by add_noise=disable (node(s) "
           + ", ".join(f"{s.get('where')}/{s['node_id']}" for s in inert) + ")"
           if inert else ""))
    return ev


def verify(graph, *, family="wan", require_pinned_seeds=True, allow=(), frame=None,
           hosted_tier=None, carries_no_sampler=False, attribution=()):
    """The three questions at once. Raises on anything the record already ruled against.

    `allow` names component keys the caller has an explicit ruling for — it is not a skip
    flag, because a component named here still appears in the returned evidence with its
    verdict, so the report cannot omit that it ran.

    `attribution` is what the SUBMITTING RECORD carries about credit: a sequence of
    `{"component", "creditor", "source", "text"}` entries, built from the table through
    `attribution_entry_for`. It is not a skip flag either — it cannot wave a BANNED or
    EXCLUDED row, it only PAYS a CONDITIONAL row's stated obligation, every conditional
    component is reported in the evidence whether credited or not, and an entry naming the
    wrong creditor credits nothing. A graph carrying a CONDITIONAL component that this list
    does not credit is refused with clause `uncredited_conditional_component`.

    **The licence clause states three numbers, not one.** It used to say
    `"{len(comp)} weight file(s)"` — a count of what was LOOKED AT with no count of what
    was CLASSIFIED — so 'every component is ruled clean' and 'the table classified none of
    them' were the same receipt. Measured 2026-09-04 on a graph loading
    `wan2.1_vace_14B_fp16` + `wan_2.1_vae` + `some_unknown_style_v3`: the verdict read
    "3 weight file(s), …" while all three rows read NOT IN THIS TABLE, and across the nine
    distinct `.safetensors` names the seven `build_*_payload` tools submit the table
    classifies ONE. Gate L's own clause on the same line already carries the shape
    ("{checkable} of {n} latent(s) checkable"); the licence clause now carries it too, and
    the unclassified components are named in `ev["unclassified"]`. What is NOT changed
    here: an unclassified component is still not refused — the wave-10 pin that UNKNOWN is
    reported rather than raised stands, and which map row governs which served filename is
    a spec's decision. The receipt now says the question was asked.

    `hosted_tier` names a tier from `HOSTED_TIER_RULES` whose graph carries **no pixel
    dimension at all** — `wan2.7-r2v` takes a resolution enum, a ratio enum and an integer
    duration, and never receives a width or a frame count from us. On such a graph the
    pixel clause is not merely unproven, it is INAPPLICABLE, and the enum clause is the one
    that binds. It is not a skip flag: the tier must be a recorded one (an unknown name
    raises), the enum values are checked exactly as the pixel rules would be, an illegal
    one raises here, and the evidence carries both the enum verdict and the reason the
    pixel clause did not apply — so a report cannot omit that the substitution happened.
    Passing `frame` and `hosted_tier` together is refused: they are two answers to one
    question. Owed to this tier by the E13 halt ruling (R6), which measured Gate L's `wan`
    rules unable to describe it.

    `frame` is `(width, height, length)`, or a mapping carrying those keys, for the caller
    that KNOWS the shape it is about to generate — the builder of the graph. It is not a
    skip flag either: a supplied frame is checked against the generator's rules exactly as
    a graph-read one is, it is labelled `supplied` in the evidence, and where the graph
    also pins a checkable latent the two must agree or the gate raises.

    **Why a caller may need to supply it — the E08 catch, 2026-08-12.** Gate L examined
    ZERO latents on the first Animate graph and reported it legal: `WanAnimateToVideo`
    emits its own latent, so no `Empty*LatentVideo` node existed and `latents()` came back
    empty. Adding that class to the table fixed THAT graph. It did not fix the shape of the
    failure, which is that "no latent was found" and "every latent found is legal" were the
    same verdict. They are now different: with nothing checkable and nothing supplied the
    frame-legality clause is **INDETERMINATE — unproven — and raises**, because a check
    that cannot fail is not a check.
    """
    # · ANDON, before anything is read — the licence clause below asks
    # `RULED_COMPONENTS` a question, and an orphaned alias makes it the wrong question.
    gate_alias_table()
    graph = normalise_graph(graph)
    if hosted_tier is not None and frame is not None:
        raise RouteGate(
            "verify() was given both a hosted tier and a pixel frame; they are two answers "
            "to the same question and one of them would be the number nobody checked",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "two_answers",
             "hosted_tier": hosted_tier, "frame": frame})
    comp = components(graph)
    sd = seeds(graph)
    lat = latents(graph)
    legality = [dict(frame_legality(l["width"], l["height"], l["length"], family),
                     source="graph", node_id=l["node_id"], node_class=l["class"])
                for l in lat if l["checkable"]]
    supplied = None
    if frame is not None:
        w, h, n = _frame_triple(frame)
        supplied = dict(frame_legality(w, h, n, family), source="supplied")
        legality.append(supplied)
    # `receipt` DECLARES what this dict is, and the two fact keys below describe THE CALL
    # rather than which clauses ran.
    #
    # ⚠ **A `verify` receipt was identified downstream by its CONTENT, and one of the two
    # content keys was conditional on a public keyword argument of this function.**
    # `gate_saved_graph.VERIFY_RECEIPT_KEYS` is `("attribution",
    # "carries_no_sampler_asserted")`, both required; `ev["attribution"]` was written on
    # every path, while `ev["carries_no_sampler_asserted"]` was written inside
    # `_seed_population_andon`, which this function calls ONLY under
    # `if require_pinned_seeds:`. Measured 2026-09-04 in this worktree on a graph carrying
    # one `UNETLoader` and one pinned `KSampler` at frame (832, 480, 81): with the default
    # flag both keys were present; with `require_pinned_seeds=False` the returned evidence
    # carried `attribution` and NOT `carries_no_sampler_asserted`. A payload record whose
    # Gate ROUTE receipt was produced with the seed clause declared NOT CHECKED was then
    # read by `gate_saved_graph --record` as carrying no verify receipt at all, and the run
    # halted with `record_carries_no_verify_receipt` naming the wrong defect — a false
    # refusal at the spend boundary. No live builder passes `require_pinned_seeds=False`
    # today, so the exposure was latent and fail-closed; it is fixed because the key that
    # IDENTIFIES the receipt may not depend on which clauses ran.
    #
    # Both keys are written here, before the first clause can raise, so every receipt this
    # function returns — and every refusal evidence it raises — answers the same questions.
    # `_seed_population_andon` still writes `carries_no_sampler_asserted` for its own other
    # caller (`gate_s_registration`), with the same value.
    #
    # ⚠ **THE INVARIANT THAT TELLS A RETURNED RECEIPT FROM A CAUGHT REFUSAL: a receipt this
    # function RETURNS never carries `clause`; only a refusal it RAISES does.** Both are
    # stamped `gate: "ROUTE"`, `andon: "RouteGate"`, `receipt: "verify"` and both fact keys,
    # written in this literal before the first clause can raise — so the ONLY thing
    # separating them downstream is the absence of `clause`.
    #
    # It is stated here because it is read there and was written down nowhere on this page.
    # `gate_saved_graph.route_facts` reads `refusals = [r for r in receipts if
    # r.get("clause")]` and raises `record_carries_a_caught_refusal` on a hit; the sentence
    # that says a returned receipt never carries `clause` lives at `gate_saved_graph.py`,
    # in another domain's file, and in `tests/test_amend_w18_builders.py`. Re-measured
    # 2026-09-05 on `e8263a3`: a passing `verify` returns with `"clause" in ev` False and
    # `receipt == "verify"`, and a caught refusal (an `attribution` naming a component the
    # graph does not load) raises with evidence carrying `receipt: "verify"`, both fact keys
    # AND `clause: "orphan_attribution"` — told apart by an absence nothing in this module
    # pinned.
    #
    # Three OTHER dicts in this module stamped `gate: "ROUTE", andon: "RouteGate"` DO carry
    # `clause` on a pass — `gate_s_registration` (`clause: "gate_s_registration"`),
    # `camera_widget_order_evidence` (`clause: "camera_widget_order"`) and
    # `gate_alias_table` (`clause: "orphaned_component_class_alias"`). Measured,
    # `gate_saved_graph.verify_receipts` admits none of the three, but only because it ALSO
    # requires `receipt == "verify"` or both fact keys. So the day a clause name is added to
    # THIS literal for symmetry with those three, every builder's payload record starts
    # refusing at the last gate before a paid submission with
    # `record_carries_a_caught_refusal` naming the wrong defect. Do not add one.
    #
    # ⚠ **`tool_version` and `graph_sha256` are written HERE, before the first clause can
    # raise, for the same reason both fact keys are: a receipt that identifies neither the
    # version that ruled nor the graph it ruled on cannot be read back. Measured
    # 2026-09-05: this receipt had 29 keys and `json.dumps(ev)` contained none of
    # `TOOL_VERSION`, `tool_version`, `E09`, a graph hash or a graph path, while
    # `donor_gate` (:458) and `lift_solve` (:627) write their `TOOL_VERSION` into the
    # record they emit and all ten payload builders record their own. Gate ROUTE's clause
    # set moved materially in waves 25 and 26 (a hosted-tier ruling-table check, four new
    # `SavedAdmission` clause words, the licence walk's name-shaped-widget pass, the
    # blueprint level-label andon), so two receipts stored in `outputs/<experiment>/` from
    # either side of those waves were indistinguishable in the record — which is the
    # reproducibility claim CLAUDE.md makes of every generation record. Neither key is a
    # `clause`, so the invariant above is untouched.
    ev = {"gate": "ROUTE", "andon": "RouteGate", "receipt": "verify",
          "tool_version": TOOL_VERSION,
          "graph_sha256": graph_digest(graph),
          "carries_no_sampler_asserted": bool(carries_no_sampler),
          "require_pinned_seeds": bool(require_pinned_seeds),
          "attribution": [dict(e) if isinstance(e, dict) else e
                          for e in (attribution or [])],
          # What the walk ENTERED, so the licence clause's `of {len(comp)}` denominator
          # can be reconciled against it. `None` on save format — see `api_walk_census`,
          # and F-7eb1ba2a for the receipt that counted a population a silent `continue`
          # had already excluded a banned LoRA from.
          "walk_census": api_walk_census(graph),
          "components": comp, "seeds": sd, "latents": lat,
          "latents_checkable": sum(1 for l in lat if l["checkable"]),
          "frame_legality": legality}

    # · The AGE of the rulings this graph is about to be judged by, written before the
    # first licence clause can raise so a REFUSAL carries it too. `docs/license-map.md`
    # states the law this reads — "Entries older than 90 days are advisory until
    # re-fetched" — and until 2026-09-05 no receipt and no refusal at the spend boundary
    # could say how old the ruling it applied was. It reports; it does not raise. Whether
    # a lapsed ruling also refuses is the Director's call, not this gate's.
    ev["licence_fetch"] = licence_fetch_reading(comp)

    # `allow` may wave a METHODOLOGY ruling. It may not wave a LICENCE one. The filter
    # used to treat the two verdicts as one class, so `allow=('causvid',)` moved a
    # CC-BY-NC weight through and returned a green verdict that said nothing about the
    # waiver — measured 2026-09-03. CLAUDE.md's licence gate is a non-negotiable: no
    # non-commercially-licensed weight anywhere in the pipeline, experiments included.
    # An attempt to allow one is refused here rather than obeyed, and it is refused even
    # on a graph that does not load it, because the call itself is the defect.
    banned_allowed = sorted(k for k in allow
                            if RULED_COMPONENTS.get(k, {}).get("verdict") == "BANNED")
    if banned_allowed:
        # The operand rides `ev` rather than a `dict(ev, ...)` wrapper: the suite's one
        # evidence judge resolves `ev["k"] = ...` writes only when the raise is handed the
        # NAME (`_evidence_name` returns None for `dict(ev, …)`), so the wrapper hid the
        # clause word from the census that exists to police it. Mutating here is safe
        # because the next statement raises — the receipt this function RETURNS never
        # reaches a mutation (see the invariant note above the `ev` literal).
        ev["clause"] = "conditional_allow_on_a_banned_row"
        ev["allow"] = list(allow)
        raise RouteGate(
            "allow= names " + ", ".join(
                f"{k!r} ({RULED_COMPONENTS[k]['licence']}: "
                f"{RULED_COMPONENTS[k]['reason']})" for k in banned_allowed) +
            ". A BANNED row is a LICENCE ruling and no keyword argument waves one; "
            "`allow` exists for the EXCLUDED rows, which are methodology rulings",
            ev)

    bad = [c for c in comp
           if c["ruling"]["verdict"] in ("BANNED", "EXCLUDED")
           and c["ruling"].get("matched_on") not in allow]
    if bad:
        ev["clause"] = "banned_or_excluded_component"
        ev["banned_or_excluded"] = [_component_label(c) for c in bad]
        raise RouteGate(
            "the graph loads " + ", ".join(
                f"{_component_label(c)} ({c['ruling']['verdict']}: "
                f"{c['ruling']['reason']}; "
                f"{_row_provenance(c['ruling'].get('matched_on'))})"
                + (f" [this {'class name' if c.get('kind') == 'class' else 'filename'}"
                   f" also matches "
                   + ", ".join(f"{m['matched_on']}={m['verdict']}"
                               for m in c["ruling"]["matches"][1:]) + "]"
                   if len(c["ruling"].get("matches") or []) > 1 else "")
                for c in bad) +
            ". The licence map's ruling is that presence is presence — a bypassed node "
            "still counts, and these are not even bypassed. Delete the node named above; "
            + licence_phrase_for(ev["licence_fetch"]),
            ev)

    # · ANDON — the direction `WEIGHT_SUFFIXES` leaves unbounded, placed AFTER the licence
    # kill so a BANNED row stays the headline. A name the table rules on that wears an
    # extension this repo has not recorded is refused BY NAME rather than classified on
    # trust: the seven-suffix tuple used to decide which names the table was allowed to
    # rule on at all (see `WEIGHT_SUFFIXES` for the `causvid_x.bin` measurement), and a
    # ruled name in an unrecorded artifact format is exactly the input class that walked
    # past it. Refusing here means the extension list is extended deliberately, in a
    # commit, rather than by a converter's choice of filename.
    unrecorded_suffix = [c for c in comp
                         if c.get("kind") == "weight" and not c.get("suffix_recorded")]
    if unrecorded_suffix:
        ev["clause"] = "ruled_name_with_unknown_suffix"
        ev["ruled_names_with_unknown_suffix"] = [c["file"] for c in unrecorded_suffix]
        ev["recorded_suffixes"] = list(WEIGHT_SUFFIXES)
        raise RouteGate(
            "the graph loads " + ", ".join(
                f"{c['file']!r} (the licence map rules on {c['ruling']['matched_on']!r}: "
                f"{c['ruling']['verdict']})" for c in unrecorded_suffix) +
            f", whose name the licence table rules on but whose extension is not one of "
            f"{list(WEIGHT_SUFFIXES)}. The suffix list is not a licence authority: until "
            f"this clause existed it decided which names the table was allowed to rule "
            f"on, and a BANNED weight spelled `.bin` returned a green receipt naming it "
            f"nowhere. Record the extension in WEIGHT_SUFFIXES, in a commit, if this "
            f"artifact format is one this pipeline loads",
            ev)

    # · ANDON — a CONDITIONAL grant is a grant with an obligation attached, and the
    # obligation is checked here rather than remembered. `docs/license-map.md` rules
    # `technically_color` "YES — credit required" (`allowNoCredit: false`); this table
    # mirrored it as an unconditional ALLOWED until 2026-09-04 and the condition survived
    # only as prose no clause read. Placed AFTER the banned/excluded clause (a kill stays
    # the headline) and BEFORE the receipt is composed, because the number the receipt
    # quotes has to be a number something checked.
    conditional = uncredited_conditional_components(comp, attribution)
    ev["conditional_components"] = conditional
    # `ev["attribution"]` is written with the rest of the receipt's call-describing keys at
    # the top of this function — see the comment there. It used to be written here, which
    # made a receipt's identity depend on reaching this line.
    uncredited = [c for c in conditional if not c["credited"]]
    if uncredited:
        raise RouteGate(
            "the graph loads " + ", ".join(
                f"{c['label']} (CONDITIONAL: {c['condition'].get('kind', 'credit')} — "
                f"{c['condition'].get('text') or c['condition'].get('creditor')}; "
                f"{_row_provenance(c.get('matched_on'))})"
                for c in uncredited) +
            ", and the submitting record carries no attribution entry crediting "
            + ", ".join(sorted({str(c["condition"].get("creditor")) for c in uncredited}))
            + ". The licence map's grant for this component is conditional on the credit; "
            "a spend recorded without it is a spend whose one governing clause nothing in "
            "the record says was met. Build the entry from the row with "
            "`route_gates.attribution_entry_for(<key>)` and pass it as attribution=",
            dict(ev, clause="uncredited_conditional_component",
                 uncredited_conditional=uncredited))

    # · ANDON — the CONVERSE of the clause above, which nothing checked. `attribution` is
    # copied into the evidence a builder stores and a provenance sheet prints, so an entry
    # that credits nothing this graph loads becomes a published credit for a creator whose
    # weights were not used — the inverse of the harm the conditional row exists to
    # prevent. See `unmatched_attribution_entries` for the measurement.
    #
    # It REFUSES rather than only reporting. The alternative — record the orphans and
    # proceed — leaves the spend to happen with a record that is wrong in a direction no
    # later reader can detect, and this is the last gate before a paid submission. The
    # count is recorded either way, so the receipt states a property something checked.
    unmatched = unmatched_attribution_entries(comp, attribution)
    ev["attribution_unmatched"] = unmatched
    if unmatched:
        raise RouteGate(
            f"the submitting record carries {len(unmatched)} attribution entr"
            f"{'y' if len(unmatched) == 1 else 'ies'} that credit no component this graph "
            f"loads: " + ", ".join(repr(e) for e in unmatched) +
            ". A credit line rides the provenance record and the public disclosure "
            "surface, so an entry left behind after an arm switch publishes a credit to a "
            "creator whose weights were never loaded — and the record then cannot be read "
            "back to tell which. Build entries from the graph with "
            "`route_gates.conditional_component_keys(graph)`",
            dict(ev, clause="orphan_attribution",
                 attribution_unmatched=unmatched))

    # A waived component appears in `components` with its verdict, but the string a
    # builder stores and a provenance sheet prints is `verdict` — so the waiver is named
    # there too. A receipt that omits it is a receipt that reads clean.
    waived = sorted({c["ruling"]["matched_on"] for c in comp
                     if c["ruling"]["verdict"] == "EXCLUDED"
                     and c["ruling"].get("matched_on") in allow})
    ev["waived"] = waived

    # The licence clause's own three answers, in the shape Gate L's latent clause already
    # uses. `classified` is the population the table actually ruled on; `unclassified`
    # NAMES the rest rather than counting them away.
    classified = [c for c in comp if c["ruling"].get("matched_on")]
    unclassified = [_component_label(c) for c in comp
                    if not c["ruling"].get("matched_on")]
    ev["components_classified"] = len(classified)
    ev["components_unclassified"] = len(unclassified)
    ev["unclassified"] = unclassified
    ev["components_conditional"] = len(conditional)
    ev["components_conditional_credited"] = sum(1 for c in conditional if c["credited"])
    ev["attribution_unmatched_count"] = len(unmatched)
    licence_phrase = (
        f"{len(classified)} of {len(comp)} component(s) classified, "
        f"{len(unclassified)} unclassified, "
        f"{len(conditional)} conditional (credited), "
        f"{len(unmatched)} attribution entr"
        f"{'y' if len(unmatched) == 1 else 'ies'} matching no loaded component, "
        # The AGE of the rulings the three numbers above were computed under. A verdict
        # that states what was classified and not when the classification was fetched
        # reads identically on the day the map's 90-day rule makes it advisory.
        + licence_phrase_for(ev["licence_fetch"]))

    # · ANDON — Gate PAIR. Placed after the licence clause (a banned weight stays the
    # headline) and before everything else, because every clause below is a question about
    # the graph's internal consistency and this one is the only question about whether the
    # model can receive what the graph wires at it. Wave 2 was internally consistent.
    ev["pairing"] = pairing(graph)

    # · ANDON — the generator family Gate L is about to grade this frame on, RECONCILED
    # against the weights the graph actually loads instead of taken from the caller's
    # keyword default. See `GENERATOR_FAMILIES` for the measurement: `family='wan'` was an
    # assertion nothing checked, `GENERATOR_RULES` has one row so the default could never
    # be refused, and `families_of` / `WEIGHT_FAMILIES` answers the OTHER question (the
    # conditioning variant Gate PAIR needs). The reading's three answers all ride the
    # receipt; only the contradiction raises — the unproven directions would halt the two
    # assemblers, which reach here with no diffusion model at all.
    generator = generator_family_reading(graph)
    ev["generator_family"] = dict(generator, declared=family)
    if generator["families_read"] and family not in generator["families_read"]:
        ev["clause"] = "generator_family_contradicted"
        ev["declared_family"] = family
        ev["families_read"] = generator["families_read"]
        ev["recorded_families"] = sorted(GENERATOR_FAMILIES)
        raise RouteGate(
            f"verify() was called with family={family!r} and the graph loads " +
            ", ".join(f"{r['file']!r} ({r['where']}/{r['node_id']}, families "
                      f"{r['generator_families']})"
                      for r in generator["model_weights"]
                      if r["generator_families"]) +
            f". Gate L's divisibility rule, frame form and trained horizon come from "
            f"GENERATOR_RULES[{family!r}], so the frame would be graded against one "
            f"generator's constraints while a different one runs, and the receipt would "
            f"name family {family!r} beside a weight file that is not it",
            ev)

    # The verdict must describe what RAN. `require_pinned_seeds=False` skipped the clause
    # and still returned "N seed(s) all pinned" — the string `build_t2v_payload` and
    # `gate_saved_graph` store in the spend meta and `make_startframe_sheet` renders onto
    # the provenance sheet. Measured 2026-09-03 on a graph whose only sampler carries
    # control_after_generate='randomize'. A record may not assert a property nobody
    # checked, so the skip is named in the verdict rather than hidden by it.
    if require_pinned_seeds:
        # · ANDON — the third answer the other three clauses in this file already have
        # (Gate L latent, Gate L hosted, Gate PAIR). A sampler class absent from
        # SEED_NODES makes `seeds()` return [] and this clause used to print "0 seed(s)
        # all pinned" over it. See `_seed_population_andon`.
        _seed_population_andon(graph, sd, ev, carries_no_sampler)
    elif carries_no_sampler:
        ev["clause"] = "sampler_assertion_unchecked"
        raise RouteGate(
            "verify() was given carries_no_sampler=True with require_pinned_seeds=False; "
            "one asserts a property of the graph and the other says nobody looked, and "
            "the assertion would go unchecked", ev)

    if not require_pinned_seeds:
        ev["seed_clause_verdict"] = "NOT CHECKED (require_pinned_seeds=False)"
        seed_phrase = (f"{len(sd)} seed(s) NOT CHECKED for pinning "
                       f"(require_pinned_seeds=False)")
    elif not sd:
        ev["seed_clause_verdict"] = (
            "CHECKED — no sampler in this graph (asserted by the caller and checked)")
        seed_phrase = "no sampler (asserted and checked), so no seed to pin"
    else:
        ev["seed_clause_verdict"] = f"CHECKED — {len(sd)} seed(s) all pinned"
        seed_phrase = f"{len(sd)} seed(s) all pinned"

    if require_pinned_seeds:
        loose = [s for s in sd if not s["pinned"]]
        if loose:
            ev["clause"] = "seed_not_pinned"
            raise RouteGate(
                "Gate S cannot be armed on this graph: " + ", ".join(
                    f"node {s['node_id']} ({s['class']}) has control_after_generate="
                    f"{s['control_after_generate']!r}" for s in loose) +
                ". A seed that randomises is a seed no committed list pre-registered, and "
                "the experiment's number would be quoted against a run nobody can repeat",
                ev)

    illegal = [f for f in ev["frame_legality"] if not f["legal"]]
    if illegal:
        ev["clause"] = "frame_illegal"
        raise RouteGate(
            "Gate L: " + "; ".join("; ".join(f["problems"]) for f in illegal), ev)

    # A supplied frame that disagrees with a frame the graph itself pins is not a small
    # discrepancy to average over: one of the two is what will run, and the report would
    # quote the other. Both are legal at this point, so nothing else in the chain looks.
    if supplied is not None:
        want = (supplied["width"], supplied["height"], supplied["length"])
        clash = [f for f in ev["frame_legality"] if f["source"] == "graph"
                 and (f["width"], f["height"], f["length"]) != want]
        if clash:
            ev["frame_legality_verdict"] = "CONTRADICTED"
            ev["clause"] = "supplied_frame_contradicts_graph"
            raise RouteGate(
                "Gate L: the caller supplied {}x{}x{} and the graph's {} node {} pins "
                "{}x{}x{}. Both are legal, so nothing downstream would notice that the "
                "number in the report is not the number that runs".format(
                    *want, clash[0]["node_class"], clash[0]["node_id"],
                    clash[0]["width"], clash[0]["height"], clash[0]["length"]), ev)

    # · ANDON — a camera trajectory solved for a frame other than the one being generated.
    # See CAMERA_NODES: this defect passes every other clause in this function, and the
    # node's own default length (81) is not this route's (65), so it is one omitted argument
    # away. The andon is put on the direction the other clauses do not bound.
    cams = cameras(graph)
    ev["cameras"] = cams
    if cams:
        graph_frames = {(f["width"], f["height"], f["length"])
                        for f in ev["frame_legality"] if f["source"] == "graph"}
        target = None
        if supplied is not None:
            target = (supplied["width"], supplied["height"], supplied["length"])
        elif len(graph_frames) == 1:
            target = next(iter(graph_frames))

        unchecked = [c for c in cams if not c["checkable"]]
        if unchecked:
            ev["camera_agreement_verdict"] = "INDETERMINATE"
            ev["clause"] = "camera_frame_unreadable"
            raise RouteGate(
                "the camera trajectory's frame is UNPROVEN: " + ", ".join(
                    f"node {c['node_id']} ({c['class']}) does not pin width, height and "
                    f"length as literals" for c in unchecked) +
                ". A trajectory whose frame cannot be read cannot be shown to match the "
                "one being generated, and every other clause here passes either way", ev)
        if target is None:
            ev["camera_agreement_verdict"] = "INDETERMINATE"
            ev["clause"] = "camera_frame_has_no_target"
            raise RouteGate(
                f"the graph carries {len(cams)} camera-trajectory node(s) but no single "
                f"frame to check them against: the graph pins {sorted(graph_frames)} and "
                f"the caller supplied none. Pass frame=(width, height, length) — the "
                f"agreement is the whole point of the check", ev)
        off = [c for c in cams
               if (c["width"], c["height"], c["length"]) != target]
        if off:
            ev["camera_agreement_verdict"] = "CONTRADICTED"
            ev["clause"] = "camera_frame_contradicted"
            raise RouteGate(
                "the camera trajectory is solved for a different frame than the one being "
                "generated: " + "; ".join(
                    f"node {c['node_id']} ({c['class']}) is {c['width']}x{c['height']}x"
                    f"{c['length']} against the generated {target[0]}x{target[1]}x"
                    f"{target[2]}" for c in off) +
                ". The run would still produce video, and every other gate would pass on "
                "it", ev)
        ev["camera_agreement_verdict"] = "AGREES"

    # The empirical SECOND reading of the recorded widget indices, RECORDED on the graph
    # that is about to be graded. `camera_widget_order_evidence` is the function the
    # `LATENT_NODES` note says takes this confirmation, and until 2026-09-05 nothing in
    # `tools/` called it at all (see that note for the grep, and for the second copy of the
    # table that was taking the reading instead). This is its production caller.
    #
    # **It is RECORDED and does not raise, and that is a measurement rather than a
    # preference.** Measured 2026-09-05 in this worktree: every disagreement this reading
    # can report on a save-format graph is ALREADY refused, earlier, by a clause above —
    # a `LATENT_NODES` row whose indices are wrong makes `latents()` read the wrong
    # dimensions, which the supplied-vs-graph clash clause refuses (operand: swapping
    # `WanCameraImageToVideo`'s width/height indices on a graph verified at (832, 480, 81)
    # raised "Gate L: the caller supplied 832x480x81 and the graph's WanCameraImageToVideo
    # node 3 pins 480x832x81"), and a `CAMERA_NODES` row's is refused by the camera
    # agreement clause on the same operand. A raise here would be a check that cannot fail,
    # which is the thing this file refuses to ship. What the receipt adds is the reading
    # itself — the values standing at the declared indices, per node, with `where` — so the
    # confirmation the `LATENT_NODES` note promises is in the record an operator reads
    # instead of in a function nobody called.
    #
    # Its three answers all ride: the reading, `INDETERMINATE` when no node in the graph
    # carries a recorded widget-index row, and `not_applicable` in API format where nothing
    # is positional. Routed to builders as SEAM 5 §2: adopting this function in
    # `gate_saved_graph`'s camera step — where a disagreement WOULD be the only reading of
    # it — is theirs, in their file.
    ev["camera_widget_order"] = _camera_widget_order_receipt(graph, ev, supplied)

    # · ANDON — the CONVERSE of the hosted block below, which nothing checked. The block's
    # own inside bounds ONE direction ("verify() was told this is hosted tier X, but no node
    # in the graph carries that tier's enum inputs … which is the vacuous state this
    # argument exists to remove"); the other direction — the graph carries hosted nodes and
    # the CALLER said nothing — reached the PIXEL clause instead, which this function's own
    # inapplicability text calls a category error on such a tier.
    #
    # Measured 2026-09-05 in this worktree on `580af47`: a save-format graph whose one node
    # is `Wan2ReferenceVideoApi` with `widgets_values` placing the enums at ('4K', '99:1',
    # 900) — every one illegal against `HOSTED_TIER_RULES['wan2.7-r2v']` — returned from
    # `verify(g, frame=(832,480,81), require_pinned_seeds=False)` with
    # `frame_legality_verdict: 'PROVEN'`, the verdict "… 1 frame(s) checked and
    # generator-legal", and NO key beginning `hosted_` in the evidence at all, while
    # `hosted_enums(g)` on the same graph returned `[('top', 1, '4K', '99:1', 900)]`. The
    # values were readable and no clause read them; the tier's per-node billing clause never
    # ran either, so a two-node hosted graph was two charges under one unexamined verdict.
    # `tools/gate_saved_graph.py` declares `--hosted-tier` with `default=None` as an ordinary
    # optional flag, so the omission is one keystroke at the last gate before a paid
    # submission. Posted to builders in the wave-25 inbox before this landed.
    #
    # It sits HERE, last of the clauses that can raise, rather than at the top of the
    # function: measured on `tests/test_route_gates.py::test_one_graph_two_formats_gets_one_
    # verdict_on_an_unrecorded_hosted_node`, the top placement made the API spelling of that
    # graph refuse on THIS clause while the save spelling refused on the seed andon — one
    # graph, two formats, two different verdicts, which is the exact property that test
    # exists to pin. Ordering is the licence kill, then the seeds, then Gate L; this is a
    # Gate L clause and it raises in Gate L's place.
    if hosted_tier is None:
        declared = hosted_enums(graph)
        if declared:
            tiers = sorted(HOSTED_TIER_RULES)
            classes = {(w, str(n.get("id"))): n.get("type")
                       for w, n in _iter_nodes(graph)}
            rows = [{"where": w, "node_id": i,
                     "class": classes.get((w, str(i))),
                     "resolution": r, "ratio": ra, "duration": d}
                    for w, i, r, ra, d in declared]
            ev["clause"] = "hosted_nodes_without_a_tier"
            ev["hosted_nodes_without_a_tier"] = rows
            ev["recorded_hosted_tiers"] = tiers
            raise RouteGate(
                f"the graph carries {len(rows)} hosted partner node(s) carrying a tier's "
                f"enum inputs — " + ", ".join(
                    f"{r['where']}/{r['node_id']} ({r['class']}) at "
                    f"{r['resolution']!r} {r['ratio']!r} {r['duration']!r}" for r in rows) +
                f" — and verify() was not told which tier they are. The enum clause that "
                f"decides legality on such a tier (resolution, ratio and duration — the "
                f"three things it bills and refuses on) is then not posed at all, and the "
                f"graph is graded on the pixel rules of family {family!r} instead, which "
                f"this function's own inapplicability text calls a category error on a "
                f"hosted tier. Pass hosted_tier=<tier> (recorded tiers: {tiers})", ev)

    # · ANDON — the clause E08 found passing vacuously. "Nothing to check" and "everything
    # checked out" must not be the same verdict. On a hosted tier the honest third answer
    # is INAPPLICABLE: there is no pixel dimension in the graph to check, and the enum
    # clause below is what decides legality instead. It still raises on an illegal enum.
    if hosted_tier is not None:
        if lat:
            ev["clause"] = "hosted_tier_with_latent_nodes"
            ev["hosted_tier"] = hosted_tier
            raise RouteGate(
                f"verify() was told this is hosted tier {hosted_tier!r}, but the graph "
                f"carries {len(lat)} latent-sizing node(s). One of those two is wrong, and "
                f"the pixel clause would go unchecked either way", ev)
        found = hosted_enums(graph)
        if not found:
            ev["clause"] = "hosted_tier_without_hosted_nodes"
            ev["hosted_tier"] = hosted_tier
            raise RouteGate(
                f"verify() was told this is hosted tier {hosted_tier!r}, but no node in the "
                f"graph carries that tier's enum inputs. Gate L would then have nothing to "
                f"decide in EITHER clause, which is the vacuous state this argument exists "
                f"to remove", ev)
        # EVERY hosted node is graded, and every one is recorded, before anything raises.
        # `hosted_enums` used to return the first match and this branch checked only that
        # tuple: a second node at an illegal resolution, ratio or duration was named
        # nowhere in the evidence.
        # `where` rides every row: node identity in this walk is the pair, and both
        # refusals below print `level/id`. See `hosted_enums` for the measurement.
        rows = [dict(hosted_frame_legality(res, ratio, dur, hosted_tier),
                     source="graph", where=where, node_id=nid)
                for where, nid, res, ratio, dur in found]
        ev["hosted_frame_legality_nodes"] = rows
        ev["frame_legality_verdict"] = "INAPPLICABLE — hosted tier, enum clause instead"
        ev["frame_legality_inapplicable_reason"] = (
            f"{hosted_tier} receives no width, height or frame count from this graph; the "
            f"pixel rules of family {family!r} decide nothing here, so the tier's own enum "
            f"constraints are checked instead and are reported in `hosted_frame_legality`")
        illegal_rows = [r for r in rows if not r["legal"]]
        if illegal_rows:
            ev["clause"] = "hosted_frame_illegal"
            raise RouteGate(
                "Gate L (hosted tier): " + "; ".join(
                    f"node {r['where']}/{r['node_id']}: " + "; ".join(r["problems"])
                    for r in illegal_rows), ev)
        if len(rows) > 1:
            # Both legal is not the same as one checked. This tier bills per node, so a
            # graph carrying two of them is one submission and two charges, and a single
            # tier verdict would be the number nobody checked — the argument this
            # function already makes for `frame` and `hosted_tier` together.
            ev["clause"] = "hosted_multiple_billable_nodes"
            raise RouteGate(
                f"the graph carries {len(rows)} {hosted_tier} node(s) "
                f"({', '.join(str(r['where']) + '/' + str(r['node_id']) for r in rows)}); "
                f"every one is legal and "
                f"reported in `hosted_frame_legality_nodes`, but one submission carrying "
                f"two billable nodes is two charges against a ceiling counted per "
                f"submission, and one tier verdict cannot describe both", ev)
        tier_ev = rows[0]
        ev["hosted_frame_legality"] = tier_ev
        ev["verdict"] = (
            f"{licence_phrase}, {seed_phrase}, hosted tier "
            f"{hosted_tier} at {tier_ev['resolution']} {tier_ev['ratio']} "
            f"{tier_ev['duration_s']}s — enum-legal; the pixel clause is inapplicable"
            + (f"; WAIVED components {waived}" if waived else ""))
        return ev

    if not ev["frame_legality"]:
        ev["frame_legality_verdict"] = "INDETERMINATE"
        ev["clause"] = "frame_legality_indeterminate"
        raise RouteGate(
            f"Gate L is INDETERMINATE on this graph and therefore UNPROVEN: none of its "
            f"{len(lat)} latent-sizing node(s) pins width, height and length as literals, "
            f"and the caller supplied no frame. Measured on E08, 2026-08-12: a graph in "
            f"this state was reported LEGAL having examined zero frames. Pass "
            f"frame=(width, height, length) if you know the shape being generated — the "
            f"gate then checks it against the generator's rules like any other", ev)

    ev["frame_legality_verdict"] = "PROVEN"
    ev["verdict"] = (f"{licence_phrase}, {seed_phrase}, "
                     f"{ev['latents_checkable']} of {len(lat)} latent(s) checkable, "
                     f"{len(ev['frame_legality'])} frame(s) checked and generator-legal"
                     + (f", {len(cams)} camera trajectory(s) on the generated frame"
                        if cams else "")
                     + (f"; WAIVED components {waived}" if waived else ""))
    return ev


def load_graph(path):
    """A graph from disk, read through the one loader.

    ⚠ **This function used to unwrap `workflow_json` and `workflow` and NOT `prompt` —
    the standard submission envelope.** A file left inside that envelope was returned
    whole, and every clause of `verify` then reported its zero-population verdict as a
    pass (the measurement is on `normalise_graph`). `gate_saved_graph.round_trip` died
    on the same file with `KeyError: 'nodes'`, which is a crash rather than a wrong
    answer and so the good kind of latent bug.

    The unwrap list is now `WRAPPER_KEYS` (== `canon.GRAPH_WRAPPER_KEYS`) and it is read
    through `normalise_graph`, so a file whose shape this module cannot read raises
    `RouteGate` naming the top-level keys instead of being handed on as an empty graph.
    """
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    # The parse used to sit OUTSIDE the try below, so this function's own docstring
    # promise — "raises RouteGate naming the top-level keys" — did not hold for a file
    # that is not JSON at all. Measured 2026-09-04: a file containing `{ not json at all }`
    # raised `json.JSONDecodeError('Expecting property name enclosed in double quotes')`
    # with the path nowhere in the message, and an EMPTY file raised
    # `JSONDecodeError('Expecting value')` because `find` and `rfind` both return -1 and
    # the slice is ''. Neither is an `ArmatureError`, so a caller catching `GateFailure`
    # around a submission step did not catch it and the operator saw a decoder error with
    # no filename.
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise RouteGate(
            f"{path}: contains no JSON object at all "
            f"({len(raw)} character(s) read, no '{{' ... '}}' pair). An empty or "
            f"brace-free file is refused by name rather than parsed as ''",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unparseable_file",
             "path": str(path), "n_chars": len(raw)})
    try:
        doc = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as err:
        raise RouteGate(
            f"{path}: could not parse as JSON: {err}",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unparseable_file",
             "path": str(path), "error": str(err),
             "line": err.lineno, "column": err.colno}) from None
    try:
        return normalise_graph(doc)
    except RouteGate as exc:
        raise RouteGate(
            f"{path}: {exc}",
            dict(exc.evidence or {}, gate="ROUTE", andon="RouteGate",
                 path=str(path))) from None


# Publish spend-boundary classes into the errors catalog once this module has
# finished loading (F-77ed7f42). Safe no-op if errors is absent from sys.modules.
def _publish_gates_to_errors_catalog():
    import sys
    err = sys.modules.get("armature_core.errors")
    if err is None:
        return
    err.RouteGate = RouteGate
    err.PairGate = PairGate


_publish_gates_to_errors_catalog()
