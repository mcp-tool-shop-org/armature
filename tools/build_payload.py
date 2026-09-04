#!/usr/bin/env python
"""build_payload — assemble a submission, with the gates that must fire first.

    python tools/build_payload.py --experiment=E02 --arm=A1a --out=<payload.json>
    python tools/build_payload.py --experiment=E03 --arm=B1  --out=<payload.json>
    python tools/build_payload.py --experiment=E06 --arm=D1  --out=<payload.json>

Emits ComfyUI **API format**. The bridge is the one ruled in `E02-halt-ruling.md`:
33 x `LoadImage` -> `BatchImagesNode` -> `control_video`. There is no encoder anywhere in
it, which is the whole point — losslessness is structural rather than measured, and Gate R
is **N/A for this route, not deleted** (it and its 18 tests stay in the tree for the day a
video bridge opens).

Two things this refuses to emit a payload without:

* **Gate L** (`g1_generator_legality`) is called here, in the function that builds the
  thing that gets submitted — not chained behind a shell `&&`, which can walk past a
  failing exit code. Illegal frames never reach the wire.
* **Link topology is verified in code.** CLAUDE.md is explicit that a `dry_run` PASS does
  not prove link sanity, and E02 measured why: `dry_run` accepted a `LoadImage` naming a
  file that does not exist, without a warning.

**The Gate B probe.** A `SaveImage` hangs off `BatchImagesNode`'s output. It is not
decoration — it is the only way to observe the batch the sampler actually received.
Counting *output video* frames cannot work: `WanVaceToVideo` pads a short `control_video`
up to `length`, so a 1-image batch and a 33-image batch both yield 33 frames. See
`GateBBatching`.

--------------------------------------------------------------------------------
Two experiments, one builder (E03, 2026-08-10)

E03 varies the *subject's* motion instead of the camera's, so it needs a different prompt,
a different control source and — measured, not assumed — **no `reference_image` at all**
(`get_node WanVaceToVideo`: `reference_image` is `required: false`). Rather than fork a
second 240-line builder, the parts that differ are data in `EXPERIMENTS` and the emitted
graph shape is shared. **The E02 rows are pinned by payload sha256 in
`tests/test_build_payload.py`**, so a refactor that moved E02's bytes fails a test rather
than quietly re-topologising an experiment that has already been run and reported.

**The distinct-name check binds in both directions now.** Server names are
content-addressed, so E02 could demand 33 distinct names from 33 frames and catch a
collapsed batch. E03's B3 arm is *defined* as one held pose repeated 33 times — 33 frames
with exactly ONE distinct name — so a hard "must be 33 distinct" check would refuse the
arm. The expectation is therefore computed from the local frames' own content hashes and
compared: a moving control that collapsed raises, and a static arm that did not collapse
raises too.

--------------------------------------------------------------------------------
A third experiment, and it needed no new gate (E06, 2026-08-10)

E06 re-runs B1's control byte-identical WITH E02's reference plate, to separate the two
things that differ between A1a (a painted knight) and B1 (a black stick figure). Its only
axis is reference presence — and `verify_topology(expects_reference=...)`, written for E03
so a reference could not silently appear or vanish between arms of one experiment, already
binds that axis in both directions. **Enumerating the file first turned a commission into a
config entry**, which is the cheaper branch and the reason to look before building.

The one structural addition is a **per-arm `positive` override**, because E06's D1 and D2
differ in exactly the prompt. D1 carries no override and therefore inherits E03's positive
literally rather than by copy — a retyped prompt is a second variable that no report would
catch. No E02 or E03 arm carries an override, so their bytes cannot move through it.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import assembly as AS  # noqa: E402
from armature_core import gates  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from canon_gate import (  # noqa: E402
    canon_line, canon_spend, gate_canon_ships_what_it_gated)
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)
# The control-order clauses, CARRIED from the sibling that already owns them rather than
# reimplemented (wave 10, F-6cbb7b35). `build_assembly_payload` grew `frame_order` and
# `gate_slot_frame_index` in wave 8 for exactly the two defects measured here, and
# `build_cascade_payload` already imports them from that module; this is the third caller,
# not a third implementation.
from build_assembly_payload import (  # noqa: E402
    frame_order, gate_slot_frame_index)

WIDTH, HEIGHT, LENGTH, FPS = 480, 832, 33, 16
SEED = 654654950714624  # pinned from the saved graph, so A0's three repeats are identical

POSITIVE = (
    "A lone armored warrior stands in place and turns slowly on the spot. Dark plate "
    "armor, horned helm, heavy cloak. Neutral studio background, even lighting."
)
NEGATIVE = (
    "blurry, low quality, jpeg artifacts, extra limbs, deformed hands, deformed face, "
    "text, watermark, still image, static"
)


class PayloadError(ArmatureError):
    """The payload could not be built as specified.

    Carries an optional evidence dict, the way `GateFailure` does. Wave 8 (F-bc806f79):
    `ledger_against_wave1` built a full evidence dict, wrote it into the payload record on
    the PASSING path, and then raised with a message and nothing else — so the failing
    measurement, the one worth having, reached no record at all. Four modules define this
    class; all four take the dict now.

    ⚠ Four identical implementations of three lines is three lines too many: the single one
    belongs beside `GateFailure` in `armature_core/errors.py`. That file is not this
    domain's to edit, so the duplication is RECORDED here rather than hidden.
    """

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _carry(gate, *args, **kwargs):
    """Run a gate carried from `build_assembly_payload` and re-raise in THIS tool's family.

    The clause is the sibling's — one implementation, imported, per the family rule — but
    every refusal `_load_uploads` and `verify_topology` have ever raised is a
    `PayloadError`, and a caller that catches this module's error type must keep catching
    every refusal this module makes. The original is preserved as `__cause__` and its
    evidence is carried verbatim with `carried_from` naming the sibling, so the receipt
    still says which gate fired and where the code lives.
    """
    try:
        return gate(*args, **kwargs)
    except AS.AssemblyGate as exc:
        raise PayloadError(
            str(exc),
            dict(exc.evidence or {},
                 carried_from=f"build_assembly_payload.{gate.__name__}")) from exc


# A1b is the polarity arm. Its control is a full-image `255-x` of A1a's, which is ALSO the
# semantically correct near-dark map: E01's exporter writes BACKGROUND_DEPTH = 0.0 (black =
# far) and subject near = bright, so inverting sends the background to 255, which still
# reads "far" under the near-dark convention. One transform on identical geometry, so the
# two arms differ by exactly one thing.
UPLOAD_MAP = {
    "A1a": "outputs/E02/uploads_depth_pershot.json",
    "A1b": "outputs/E02/uploads_depth_pershot_inverted.json",
}

# E03's prompt pair. Two departures from E02's, both executor choices the spec did not arm
# and both flagged in the report:
#
#  1. **The positive names no motion.** E02's said "turns slowly on the spot", which is fine
#     when the control IS a turn. Here the whole question is whether authored motion
#     transfers, so a prompt asking for the motion would hand B2 and B3 a reason to produce
#     it and the discriminator would be measuring the prompt, not the control.
#  2. **The negative drops "still image, static".** Keeping it would pay the model to move
#     under B3 — the exact arm whose job is to show what happens when the control does NOT
#     move. Whatever motion appears is then not something we asked for.
#
# It names no material and no costume, so P3 ("does it keep the wire look") is not answered
# by the prompt — though it does say there is a figure, which bounds that read.
E03_POSITIVE = (
    "A single figure stands in the centre of an empty studio. Plain grey seamless "
    "background, even neutral lighting, full body in frame."
)
E03_NEGATIVE = (
    "blurry, low quality, jpeg artifacts, extra limbs, deformed hands, deformed face, "
    "text, watermark"
)

# E06's D2 prompt. D1 reuses E03_POSITIVE verbatim, so the pair differs in exactly one
# clause — the subject — and the second sentence is byte-identical between them.
#
# **Executor choice, flagged for the advisor to overrule.** "Names the character" could mean
# a bare proper name; a bare proper name is not a canon element to a text encoder, which
# resolves tokens and not lore. So this names the character AND the attributes E02's own
# prompt named for the same subject (dark plate, horned helm, cloak) — the ones the
# Director's canon ruling read off the identity sheet: horned helm, tattered cape,
# segmented pauldrons. Naming only "blackguard" would test whether one token means anything
# to umt5, which is not the question E06 asks.
#
# It still names NO motion, holding E03's discriminator hygiene constant across D1 and D2.
E06_D2_POSITIVE = (
    "The blackguard, a lone armored warrior in dark plate armor, horned helm and heavy "
    "cloak, stands in the centre of an empty studio. Plain grey seamless "
    "background, even neutral lighting, full body in frame."
)

# E04's pre-registered seeds. **Committed in the spec that opens the experiment, before the
# first submission** — `docs/experiments/E04-the-between-generation-floor.md`, section
# "Pre-registered seeds". Gate S reads this list; it is the list, not a copy of it, and the
# spec and this constant are checked against each other by `tests/test_gate_s.py` so the
# two cannot drift apart into a registry that registers nothing.
#
# The first entry is E02's pinned seed: A0 (= A1a's payload plus the lossless tap) and A1b
# both ran on it, and those two runs join E04 as seed 1 of their respective conditions.
E04_SEEDS = (
    654654950714624,
    654654950714625,
    654654950715624,
    654654950724624,
    654654950814624,
    654654951714624,
)

#: Per-experiment configuration. An arm whose `uploads` is None carries no control video.
#: `source_dir` is the LOCAL directory the uploads came from; it is what the distinct-name
#: check derives its expectation from, so it is not decoration.
EXPERIMENTS = {
    "E02": {
        "positive": POSITIVE,
        "negative": NEGATIVE,
        "reference": ("outputs/E02/uploads_reference.json", "reference_apose_0"),
        "arms": {
            "A1a": {"uploads": UPLOAD_MAP["A1a"],
                    "source_dir": "outputs/E02/control_480x832/depth_pershot",
                    "normalization": "per-shot",
                    "polarity": "near-bright (as rendered, F19)"},
            "A1b": {"uploads": UPLOAD_MAP["A1b"],
                    "source_dir": "outputs/E02/control_480x832_inverted/depth_pershot",
                    "normalization": "per-shot",
                    "polarity": "near-dark (full-image 255-x of A1a)"},
            "A2": {"uploads": None},
        },
    },
    "E03": {
        "positive": E03_POSITIVE,
        "negative": E03_NEGATIVE,
        # NO reference image, held constant (absent) across all three arms. Measured legal:
        # `get_node WanVaceToVideo` reports reference_image as `required: false`. The E03
        # subject carries no identity, so a reference plate would inject one the experiment
        # is not asking about.
        "reference": None,
        "arms": {
            "B1": {"uploads": "outputs/E03/uploads_posearc.json",
                   "source_dir": "outputs/E03/control_posearc/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)"},
            "B2": {"uploads": None},
            "B3": {"uploads": "outputs/E03/uploads_static.json",
                   "source_dir": "outputs/E03/control_static/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)"},
        },
    },
    # E06 changes ONE of the two things that separate A1a (painted knight) from B1 (black
    # stick figure): it takes B1's control byte-identical and adds E02's reference plate.
    # Same uploads manifest, same source_dir, same pinned depth window, same seed, same
    # negative — so `verify_topology(expects_reference=True)` is guarding the only axis
    # this experiment moves, which is why E06 commissions no gate of its own.
    "E06": {
        "positive": E03_POSITIVE,     # D1: B1's prompt, unchanged
        "negative": E03_NEGATIVE,
        "reference": ("outputs/E02/uploads_reference.json", "reference_apose_0"),
        "arms": {
            # D1 carries no `positive` override, so it inherits E03's word for word. That
            # is the mechanism by which "prompt unchanged" is enforced rather than retyped:
            # a typo in a copied prompt would be a second variable nothing would report.
            "D1": {"uploads": "outputs/E03/uploads_posearc.json",
                   "source_dir": "outputs/E03/control_posearc/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)"},
            "D2": {"uploads": "outputs/E03/uploads_posearc.json",
                   "source_dir": "outputs/E03/control_posearc/depth_pershot",
                   "normalization": "per-shot, window PINNED to [3.181118, 3.363516]",
                   "polarity": "near-bright (as rendered; the convention A1a ran on)",
                   "positive": E06_D2_POSITIVE},
        },
    },
    # E04 — the between-generation floor. Both conditions REUSE E02's uploaded control
    # frames and E02's prompts, reference and models byte-for-byte, because a floor
    # measured under any other conditions is not the floor under E02's numbers. The only
    # field that varies is the KSampler seed, and `seed_registry` is what makes that
    # freedom bounded rather than open.
    #
    # Verified before this row was written, by diffing the on-disk payloads: node 3's
    # `seed` is the ONLY seed-bearing field in either graph (48 and 49 nodes), so varying
    # it varies nothing else. E04 premise 2, marked ASSUMED in the spec, MEASURED here.
    "E04": {
        "positive": POSITIVE,
        "negative": NEGATIVE,
        "reference": ("outputs/E02/uploads_reference.json", "reference_apose_0"),
        "seed_registry": E04_SEEDS,
        "arms": {
            # C-bright is A1a's condition. Its base payload on disk is **A0.json**, not
            # A1a.json: A1a ran before the lossless tap existed and its payload carries no
            # node 302, so it cannot produce the frames this experiment's statistic is
            # defined on. A0 is A1a's payload plus the tap and nothing else — diffed, node
            # 302 is the sole difference — and A0r1's frames are what E02's published
            # +0.521 was actually computed from.
            "C-bright": {"uploads": UPLOAD_MAP["A1a"],
                         "source_dir": "outputs/E02/control_480x832/depth_pershot",
                         "normalization": "per-shot",
                         "polarity": "near-bright (as rendered, F19)"},
            # E02's A1b row names `control_480x832_inverted/depth_pershot`, which does not
            # exist on disk — so its distinct-name check silently degrades to "at least one
            # distinct image" and cannot catch a collapsed batch. That row is E02's, has
            # already run, and is not edited here. This row names the directory that IS on
            # disk, so the check binds at 33 for E04's own submissions.
            "C-dark": {"uploads": UPLOAD_MAP["A1b"],
                       "source_dir": "outputs/E02/control_480x832_neardark/depth_pershot",
                       "normalization": "per-shot",
                       "polarity": "near-dark (full-image 255-x of C-bright)"},
        },
    },
}


def _distinct_source_frames(source_dir):
    """How many distinct images the LOCAL control directory holds — an INT, or None.

    Three states, and they are distinguishable now:

    * `None` — there is no directory to bind against: `source_dir` is None, or the path
      does not exist. The caller has no local expectation and says so in the record.
    * `0` — the directory IS there and holds no `.png` at all. The caller REFUSES.
    * a positive int — the expectation the upload count is compared against.

    ⚠ **`return len(digests) or None` collapsed the first two into one sentinel**, and the
    caller's `expected is None` branch degrades the check to "at least one distinct server
    name". Measured 2026-09-04: a directory that exists and is empty returned None, a
    directory that does not exist returned None, `source_dir=None` returned None, and a
    directory holding only non-PNG files returned None. So an arm whose frames had been
    cleaned up, moved, renamed or converted out of `.png` silently lost the distinct-frame
    binding the comment in `_load_uploads` says exists precisely so a collapsed batch
    cannot pass — all 33 uploads mapping to ONE server name would have been admitted.
    """
    if not source_dir or not os.path.isdir(source_dir):
        return None
    digests = set()
    for n in sorted(os.listdir(source_dir)):
        if n.lower().endswith(".png"):
            with open(os.path.join(source_dir, n), "rb") as fh:
                digests.add(hashlib.sha256(fh.read()).hexdigest())
    return len(digests)


def _load_uploads(arm="A1a", experiment="E02"):
    cfg = EXPERIMENTS[experiment]
    arm_cfg = cfg["arms"][arm]
    with open(arm_cfg["uploads"], encoding="utf-8") as fh:
        control = json.load(fh)

    ref = None
    if cfg["reference"]:
        path, key = cfg["reference"]
        with open(path, encoding="utf-8") as fh:
            ref = json.load(fh)[key]

    # ---- the CONTROL ORDER, wave 10 (F-6cbb7b35). This was `keys = sorted(control)` with
    # no clause on the key SHAPE and no clause on gaps — the defect `build_assembly_payload`
    # and `build_cascade_payload` were given `frame_order` for in wave 8 (F-4a64a24e), and
    # this was the one spend builder in the tree that had neither. Measured 2026-09-04 by
    # pointing E03/B1 at two synthetic maps: an UNPADDED 33-entry map keyed `0.png..32.png`
    # was ACCEPTED and ordered `['0.png', '1.png', '10.png', '11.png', …]` — `10.png` in
    # slot 2 — and a map of 32 padded frames plus one `reference.png` key was ACCEPTED as
    # 33 frames with the non-frame key sorting last and becoming frame 32. Both pass the
    # count clause below (33 == 33) and both pass `verify_topology`, which checks the
    # dotted slot NAMES, their count and double-binding, and never relates a slot index to
    # a frame index. The control batch for E02/E03/E04/E06 would have assembled shuffled or
    # lengthened while every count in every gate still read right.
    #
    # The clause is the sibling's, imported. Its two halves are the key shape
    # (`^[0-9]{5}(\.png)?$`, one spelling per map) and the gap check over `0..n-1`.
    keys = _carry(frame_order, control)
    if len(keys) != LENGTH:
        raise PayloadError(f"expected {LENGTH} uploaded control frames, have {len(keys)}")
    names = [control[k] for k in keys]

    # Server names are content-addressed (measured: re-uploading a frame returns the same
    # name), so the number of DISTINCT names is the number of distinct images the batch will
    # carry. E02 could demand 33 from 33 and catch a collapsed batch. E03's B3 arm is
    # *defined* as one held pose repeated 33 times — 33 frames, exactly ONE distinct name —
    # so a hard "must be 33 distinct" check would refuse the arm it was written to protect.
    #
    # The expectation is therefore taken from the LOCAL frames' own content hashes and
    # compared. It binds in both directions: a moving control that collapsed on upload
    # raises, and a static arm that did NOT collapse raises too, because it would not be the
    # arm it claims to be. Caught here rather than by Gate B after a spend.
    #
    # Which of the three branches ran is RECORDED, because until 2026-09-04 a payload
    # record read the same whether the check bound at 33 or degraded to 1: `meta['control']`
    # carried the distinct SERVER-name count — the unchecked side — and never the locally
    # measured expectation nor whether the directory was readable at all.
    source_dir = arm_cfg.get("source_dir")
    expected = _distinct_source_frames(source_dir)
    got = len(set(names))
    if expected == 0:
        raise PayloadError(
            f"{source_dir} is present and holds no `.png` frames at all, so the number of "
            f"distinct images this arm's control was rendered as is unknown and the "
            f"{got} distinct server name(s) in the upload map are bound to nothing. A "
            f"directory whose frames were cleaned up, moved, renamed or converted is not "
            f"an arm with one held pose, and a check that cannot tell them apart is the "
            f"one that lets a collapsed batch through"
        )
    if expected is None:
        if got < 1:
            raise PayloadError("no uploaded control frames at all")
        comparison = (f"{got} distinct server name(s) >= 1 — DEGRADED: {source_dir!r} is "
                      f"not on this rig, so nothing local bounds the batch. The check is "
                      f"'at least one distinct server name' and no more")
    elif got != expected:
        raise PayloadError(
            f"{LENGTH} uploaded frames map to {got} distinct server name(s), but "
            f"{source_dir} holds {expected} distinct image(s); the batch the "
            f"sampler receives would not be the control that was rendered"
        )
    else:
        comparison = (f"{got} distinct server name(s) == {expected} distinct local "
                      f"image(s)")
    control_check = {"source_dir_present": expected is not None,
                     "source_dir_distinct_images": expected,
                     "comparison": comparison}
    return keys, names, ref, control_check


def build(arm, experiment="E02", seed=None):
    if experiment not in EXPERIMENTS:
        raise PayloadError(f"unknown experiment {experiment!r}; known: {sorted(EXPERIMENTS)}")
    cfg = EXPERIMENTS[experiment]
    if arm not in cfg["arms"]:
        raise PayloadError(f"unknown arm {arm!r} for {experiment}; known: {sorted(cfg['arms'])}")

    # ---- Gate S · ANDON — the seed was pre-registered. Deliberately the FIRST gate in
    # this function: it is the only one guarding a defect that leaves no trace in the
    # artifact. An illegal frame (Gate L) fails loudly downstream; a seed nobody committed
    # to in advance produces a flawless generation and a number whose meaning is gone.
    # Nothing is read from disk and nothing is emitted before it.
    seed_used = SEED if seed is None else seed
    gate_s = gates.gate_s_seed_registration(
        seed_used, cfg.get("seed_registry"), experiment, seed_was_explicit=seed is not None)


    # The prompt is per-experiment with a per-ARM override, because E06's two arms differ in
    # exactly the prompt and nothing else. An arm that carries no override inherits the
    # experiment's, so **no E02 or E03 arm's bytes can move through this**: none of them
    # carries one. `tests/test_build_payload.py` pins E02's sha256 against exactly that.
    arm_cfg = cfg["arms"][arm]
    POSITIVE_TEXT = arm_cfg.get("positive", cfg["positive"])
    NEGATIVE_TEXT = arm_cfg.get("negative", cfg["negative"])
    use_control = arm_cfg["uploads"] is not None
    if use_control:
        keys, control_names, ref_name, control_check = _load_uploads(arm, experiment)
    else:
        keys, control_names, ref_name, control_check = [], [], None, {}
        if cfg["reference"]:
            path, key = cfg["reference"]
            with open(path, encoding="utf-8") as fh:
                ref_name = json.load(fh)[key]

    # ---- Gate L · ANDON. First statement that matters; nothing is emitted if it raises.
    profile = gates.g1_generator_legality(WIDTH, HEIGHT, LENGTH, "wan-vace")

    wf = {
        "106": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "wan2.1_vace_14B_fp16.safetensors", "weight_dtype": "default"}},
        "105": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "110": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "umt5_xxl_fp16.safetensors", "type": "wan", "device": "default"}},
        "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8.0, "model": ["106", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "text": POSITIVE_TEXT, "clip": ["110", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "text": NEGATIVE_TEXT, "clip": ["110", 0]}},
    }

    vace_inputs = {
        "width": WIDTH, "height": HEIGHT, "length": LENGTH, "batch_size": 1, "strength": 1.0,
        "positive": ["6", 0], "negative": ["7", 0], "vae": ["105", 0],
    }
    if ref_name is not None:
        wf["134"] = {"class_type": "LoadImage", "inputs": {"image": ref_name}}
        vace_inputs["reference_image"] = ["134", 0]

    # Where an experiment varies its seed, the seed has to reach the output names too, or
    # six submissions of one arm would overwrite each other on the server and the run that
    # came back would not be the run that was asked for. For every experiment WITHOUT a
    # seed registry this is exactly `arm`, so E02's and E03's emitted bytes are untouched
    # — pinned by `test_E02_payload_bytes_have_not_moved`.
    run_tag = arm if not cfg.get("seed_registry") else f"{arm}-s{gate_s['registry_index'] + 1}"

    if use_control:
        # COMFY_AUTOGROW_V3 slots are DOTTED keys — `images.image0`, `images.image1`, ...
        # A list of links under a bare `images` key is rejected by the server with
        # `required_input_missing: images.image0`. That form was tried first and
        # `dry_run` VALIDATED it with zero warnings; only a real submission refused it.
        # Third measured instance in E02 of dry_run passing something broken.
        batch_inputs = {}
        for i, name in enumerate(control_names):
            nid = str(200 + i)
            wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
            batch_inputs[f"images.image{i}"] = [nid, 0]
        wf["300"] = {"class_type": "BatchImagesNode", "inputs": batch_inputs}
        # Gate B probe: the batch as the sampler receives it, saved so it can be counted
        # and compared pixel-for-pixel against the local source frames.
        wf["301"] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"{experiment}/{run_tag}/batchprobe", "images": ["300", 0]}}
        vace_inputs["control_video"] = ["300", 0]

    wf["49"] = {"class_type": "WanVaceToVideo", "inputs": vace_inputs}
    wf["3"] = {"class_type": "KSampler", "inputs": {
        "seed": seed_used, "steps": 30, "cfg": 6, "sampler_name": "uni_pc",
        "scheduler": "simple",
        "denoise": 1, "model": ["48", 0], "positive": ["49", 0], "negative": ["49", 1],
        "latent_image": ["49", 2]}}
    wf["58"] = {"class_type": "TrimVideoLatent", "inputs": {
        "samples": ["3", 0], "trim_amount": ["49", 3]}}
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["58", 0], "vae": ["105", 0]}}
    wf["68"] = {"class_type": "CreateVideo", "inputs": {
        "fps": FPS, "bit_depth": 8, "images": ["8", 0]}}
    wf["114"] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": f"video/{experiment}_{run_tag}", "format": "auto", "codec": "auto",
        "video": ["68", 0]}}
    # ---- THE LOSSLESS OUTPUT TAP. Costs no extra generation: these are the same frames
    # `CreateVideo` is about to hand to `SaveVideo`, taken off `VAEDecode` before any
    # codec touches them. The first noise floor was measured through H.264 on BOTH sides,
    # so its deltas carried codec noise of unknown size on top of model variance. A floor
    # measured through an uncharacterised codec is a moving denominator, which is the
    # thing this repo keeps paying for. Everything downstream reads these, not the video.
    wf["302"] = {"class_type": "SaveImage", "inputs": {
        "filename_prefix": f"{experiment}/{run_tag}/lossless", "images": ["8", 0]}}

    verify_topology(wf, arm, use_control, expects_reference=cfg["reference"] is not None,
                    control_names=control_names)
    # ---- Gate ROUTE · ANDON, wave 10 (F-9ee7536d). This was the ONLY one of the nine
    # builders that never called `route_gates.verify`, so no licence clause of any kind
    # examined the graph it emits — neither the weight-file rows nor wave 8's node-CLASS
    # rows — and `verify_topology` carries no banned-class tuple, unlike the three siblings
    # that do (build_animate_payload, build_camera_i2v_payload, build_i2v_payload).
    # Measured 2026-09-04 in this worktree: `route_gates.components(build('B2','E03')[0])`
    # returned three rows (wan2.1_vace_14B_fp16, wan_2.1_vae, umt5_xxl_fp16), each
    # 'NOT IN THIS TABLE', and splicing a `DWPreprocessor` node into the emitted graph was
    # accepted by `verify_topology` without comment while `route_gates.ruled_node_classes`
    # reads that same class as BANNED. Four experiments (E02/E03/E04/E06) carry no licence
    # evidence in their payload records at all as a result.
    #
    # `family="wan"`, not "wan-vace": `GENERATOR_RULES` has no `wan-vace` row, and
    # `frame_legality` raises `unknown_generator_family` on one. The VACE route's frame
    # rules ARE wan's — `gates.g1_generator_legality(…, "wan-vace")` above grades the same
    # three numbers — and adding a row to `GENERATOR_RULES` is core-gates' file, not this
    # domain's. Recorded here rather than hidden, and named in the evidence.
    gate_route = RG.verify(wf, family="wan", frame=(WIDTH, HEIGHT, LENGTH))
    gate_route["generator_family_note"] = (
        "verify() was called with family='wan'. This route is wan-vace; "
        "route_gates.GENERATOR_RULES carries no 'wan-vace' row and frame_legality raises "
        "on an unknown family, while gates.g1_generator_legality does carry one and grades "
        "the identical 16/4n+1/81 rules. The two names are one rule set here; a "
        "'wan-vace' row in GENERATOR_RULES belongs to core-gates.")
    meta = {
        "experiment": experiment,
        "arm": arm,
        "resolution": [WIDTH, HEIGHT],
        "length": LENGTH,
        "fps": FPS,
        "seed": seed_used,
        "run_tag": run_tag,
        "gate_S": gate_s,
        "gate_L": {"verdict": "PASS", "profile": profile.as_dict()},
        "gate_ROUTE_built": gate_route,
        "control": "none (the null — no control_video)" if not use_control else {
            "bridge": "33 x LoadImage -> BatchImagesNode",
            "source_dir": arm_cfg["source_dir"],
            "normalization": arm_cfg["normalization"],
            "polarity": arm_cfg["polarity"],
            "distinct_images": len(set(control_names)),
            # `distinct_images` above is the SERVER-name count — the side the check is
            # comparing, not the side it compares against. These three say which branch of
            # `_load_uploads` ran, so a reader of this record can tell a check that bound
            # at 33 from one that degraded to "at least one".
            **control_check,
            "frame_keys": keys,
            "server_names": control_names,
        },
        "reference_image": ref_name,
        "positive": POSITIVE_TEXT,
        "negative": NEGATIVE_TEXT,
        "models": {
            "unet": "wan2.1_vace_14B_fp16.safetensors",
            "clip": "umt5_xxl_fp16.safetensors",
            "vae": "wan_2.1_vae.safetensors",
        },
        "payload_sha256": hashlib.sha256(
            json.dumps(wf, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    return wf, meta


def verify_topology(wf, arm, use_control, expects_reference=None, control_names=None):
    """Check every link resolves, and that the arm is actually the arm it claims to be.

    `expects_reference` binds the reference image in BOTH directions, which matters now
    that E03 deliberately runs without one. Passing None keeps the historical behaviour of
    not checking it at all — but every call site inside this module passes a value, so a
    reference that silently appeared or vanished between arms of one experiment cannot get
    past here. An arm whose reference differs from its siblings' is not the arm it claims
    to be, and that is exactly the kind of difference a report would never notice.

    `control_names` is the clip's server-side upload names **in frame order**, and it is
    REQUIRED on a control arm (wave 10, F-6cbb7b35). The clauses below check the dotted
    slot NAMES, that there are `LENGTH` of them, and that no source node is bound twice —
    none of which relates a batch SLOT index to a FRAME index, so a permutation of the 33
    links leaves every name, every count and every link resolvable and ships the control
    out of sequence. `gate_slot_frame_index` (carried from `build_assembly_payload`, where
    wave 8 wrote it) is the clause that fires on it, and it needs the frame order, which
    lives in the upload map and not in the graph. It is not optional on a control arm: a
    caller allowed to omit it holds a skip flag for the andon, and an omitted population is
    how the same gate returned green having inspected zero slots in wave 6.
    """
    # A malformed QUESTION, refused before any answer is collected: a control arm with no
    # frame order cannot be checked for slot->frame agreement, and a caller allowed to omit
    # it holds a skip flag for the andon below.
    if use_control and control_names is None:
        raise PayloadError(
            f"[{arm}] verify_topology was called on a control arm without "
            f"`control_names`. Slot k of node 300 must hold frame k of the clip, and the "
            f"frame order lives in the upload map, not in the graph - with no names the "
            f"slot->frame andon inspects nothing and returns green",
            {"gate": "PAYLOAD", "andon": "slot_frame_index_population",
             "arm": arm, "use_control": True, "control_names": None})

    problems = []
    for nid, node in wf.items():
        for k, v in node["inputs"].items():
            cands = v if (isinstance(v, list) and v and isinstance(v[0], list)) else [v]
            for c in cands:
                if isinstance(c, list) and len(c) == 2 and isinstance(c[0], str):
                    if c[0] not in wf:
                        problems.append(f"{nid}.{k} -> missing node {c[0]}")

    if use_control:
        bi = wf["300"]["inputs"]
        if "images" in bi:
            problems.append(
                "batch uses a bare `images` list; COMFY_AUTOGROW_V3 needs dotted "
                "`images.image<N>` keys (dry_run does NOT catch this)"
            )
        expected_keys = [f"images.image{i}" for i in range(LENGTH)]
        if sorted(bi) != sorted(expected_keys):
            problems.append(
                f"batch slot keys are wrong: {len(bi)} keys, expected {LENGTH} named "
                f"images.image0..images.image{LENGTH - 1}"
            )
        srcs = [v[0] for v in bi.values()]
        if len(set(srcs)) != LENGTH:
            problems.append("a batch link is bound twice")
        if wf["49"]["inputs"].get("control_video") != ["300", 0]:
            problems.append("control_video is not fed by the batch node")
        if wf["301"]["inputs"]["images"] != ["300", 0]:
            problems.append("the Gate B probe is not wired to the batch node")
    else:
        if "control_video" in wf["49"]["inputs"]:
            problems.append(
                f"{arm} is the null arm and must have NO control_video; "
                f"the arm would not be the arm"
            )
        if any(n["class_type"] == "BatchImagesNode" for n in wf.values()):
            problems.append(f"{arm} is the null arm and still carries a batch node")

    if expects_reference is not None:
        has_ref = "reference_image" in wf["49"]["inputs"]
        if has_ref != expects_reference:
            problems.append(
                f"reference_image is {'present' if has_ref else 'absent'} but this "
                f"experiment expects it {'present' if expects_reference else 'absent'}; "
                f"a reference that differs between arms is a second variable"
            )
        if has_ref and wf["49"]["inputs"]["reference_image"] != ["134", 0]:
            problems.append("reference_image is not fed by the reference LoadImage node")
        if not has_ref and "134" in wf:
            problems.append("a reference LoadImage node is present but nothing consumes it")

    if wf.get("302", {}).get("inputs", {}).get("images") != ["8", 0]:
        problems.append(
            "the lossless tap is not wired to VAEDecode (node 8); the floor would be "
            "measured through the H.264 path again"
        )

    for dead in ("LoadVideo", "GetVideoComponents", "Canny"):
        if any(n["class_type"] == dead for n in wf.values()):
            problems.append(f"{dead} present; the video bridge was not removed")

    if problems:
        raise PayloadError(f"[{arm}] link topology is wrong: " + "; ".join(problems))

    # ---- ANDON, on the direction none of the clauses above bounds: slot k of the batch
    # node holds the upload name of frame k. Everything above reads names, counts and
    # distinctness, all of which a permutation preserves. Carried from
    # `build_assembly_payload.gate_slot_frame_index`, which `build_cascade_payload` and
    # `build_r2v_payload` already call; the flat chain passes ONE span, the whole clip on
    # node 300 starting at LoadImage id 200.
    if use_control:
        _carry(gate_slot_frame_index, wf, list(control_names),
               [("300", 0, len(control_names))], 200)
    return True


#: The record's suffix. A module constant so the census below and the tests can name the
#: one place it is spelled, and so a caller can prove the collision clause fires.
META_SUFFIX = ".meta.json"


class PayloadOutHalt(GateFailure):
    """The two artifacts this tool writes would not land at two distinct paths.

    Wave 12, F-4f72af05. The meta path was `a.out.replace(".json", ".meta.json")` — a
    substring rewrite of the WHOLE path, on a `--out` whose spelling argparse constrains in
    no way. Measured twice in a worktree:

    * `--out=<dir>/payload` (no extension): `replace` is a no-op, so the graph was written
      and then OVERWRITTEN by the record at the same path. Exactly one file existed
      afterwards, carrying the RECORD's keys, and stdout still ended `BUILD_PAYLOAD_OK {…
      "out": ".../payload"}` with exit 0 — the file an operator points a submission step at
      held the record, and the graph whose sha256 that record names reached no disk at all.
    * `--out=<dir>/run.json.d/A.json`: `str.replace` rewrites EVERY occurrence, so the
      record was aimed at `<dir>/run.meta.json.d/A.meta.json`, a directory that does not
      exist. The graph was already on disk, the tool died `FileNotFoundError`, printed
      `BUILD_PAYLOAD_HALT` with `evidence: null` and exited 1 — a partial write reported as
      a crash.

    The derivation is now the six siblings' (`os.path.splitext(out)[0] + <suffix>`:
    `author_walk:655`, `lift_solve:345`, `make_ab_clip:181`, `make_crop_strip:244`,
    `make_lift_sheet:283`, `make_pick_sheet:311`), which touches only the last component's
    extension. **The andon is on the direction that derivation does not bound**: it cannot
    rewrite a directory, but nothing in it forbids the two names COLLIDING, and a collision
    is silent — one artifact replaces the other under a green OK line. So the equality is
    checked, in the tool that performs the write, before either write and before
    `os.makedirs`, so a refusal leaves no output directory.
    """

    gate = "OUT"


def gate_out_paths(out, meta_suffix=None):
    """`(graph_path, record_path)` for `--out`, or raise saying why there is only one.

    Called before `os.makedirs`: a refuse must leave no output directory, the invariant
    this file already states for Gate CANON.
    """
    suffix = META_SUFFIX if meta_suffix is None else meta_suffix
    graph = os.path.abspath(out)
    meta = os.path.splitext(graph)[0] + suffix
    ev = {"gate": "OUT", "andon": "PayloadOutHalt", "clause": "meta_path_equals_graph_path",
          "out": graph, "meta": meta, "meta_suffix": suffix,
          "derived_by": "os.path.splitext(out)[0] + META_SUFFIX"}
    if meta == graph:
        raise PayloadOutHalt(
            f"the graph and its record would both be written to {graph!r}: the second "
            f"write would overwrite the first and the file --out names would hold the "
            f"RECORD, while the graph whose payload_sha256 that record states reached no "
            f"disk anywhere. Give --out a name whose stem plus {suffix!r} is a different "
            f"path", ev)
    if os.path.dirname(meta) != os.path.dirname(graph):
        raise PayloadOutHalt(
            f"the record would be written to {meta!r}, which is not the directory the "
            f"graph goes to ({os.path.dirname(graph)!r}). The two artifacts of one build "
            f"belong beside each other",
            dict(ev, clause="meta_leaves_the_graphs_directory"))
    ev["verdict"] = (f"the graph and its record are two distinct paths in one directory: "
                     f"{os.path.basename(graph)} and {os.path.basename(meta)}")
    return graph, meta, ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="E02", choices=sorted(EXPERIMENTS))
    ap.add_argument("--arm", required=True,
                    choices=sorted({a for e in EXPERIMENTS.values() for a in e["arms"]}))
    ap.add_argument("--out", required=True)
    # Gate S is what makes this flag safe to exist. Any seed given here is checked against
    # the experiment's committed list before a payload is built, and an experiment that
    # pre-registered no seeds refuses the flag outright.
    ap.add_argument("--seed", type=int, default=None,
                    help="pre-registered seed; refused by Gate S if not on the "
                         "experiment's committed list")
    add_spend_flags(ap)
    a = ap.parse_args(argv)

    # ---- Gate OUT · ANDON, before Gate CANON's own "leaves no output directory" clause
    # and before anything is created. The two artifacts of one build are two paths.
    gpath, mpath, gate_out = gate_out_paths(a.out)

    cfg = EXPERIMENTS[a.experiment]
    arm_cfg = cfg["arms"][a.arm]
    # The SHIPPED positive, derived exactly as `build()` derives it. `--canon-prompt`
    # used to stand in for it here while `build()` re-derived the payload's positive from
    # EXPERIMENTS regardless, so the flag could never be the text that went out — only the
    # text the router examined. It is now compared against the shipped string instead.
    positive = (
        arm_cfg.get("positive", cfg["positive"]) if isinstance(arm_cfg, dict)
        else cfg["positive"]
    )
    # Gate CANON fires before mkdir. A refuse must leave no output directory.
    canon_ev = canon_spend(
        a.subject, positive, no_canon=a.no_canon,
        out_dir=os.path.dirname(os.path.abspath(a.out)),
        canon_prompt=a.canon_prompt,
    )

    wf, meta = build(a.arm, a.experiment, seed=a.seed)
    # The graph exists now, so the claim is checkable rather than mirrored: the text the
    # router checked is the text the payload carries.
    gate_canon_ships_what_it_gated(positive, meta.get("positive"))
    meta["gate_CANON"] = canon_ev
    meta["gate_OUT"] = gate_out
    os.makedirs(os.path.dirname(gpath), exist_ok=True)
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(canon_line(canon_ev))
    # The SUCCESS half of the exit convention (wave 10). The failure half already agrees
    # across all 13 CPU tools — `<PREFIX>_HALT` and 2-vs-1 — while the success line was
    # spelled four different ways. It is `<PREFIX>_OK ` now, with the SAME prefix this
    # file's `__main__` block prints on a halt, so one AST read of that block derives both
    # directions of the census.
    print("BUILD_PAYLOAD_OK " + json.dumps({
        "experiment": a.experiment, "arm": a.arm, "nodes": len(wf), "gate_L": "PASS",
        "reference": meta["reference_image"],
        "control_distinct_images": (
            meta["control"]["distinct_images"] if isinstance(meta["control"], dict) else None),
        "sha256": meta["payload_sha256"][:16], "out": gpath, "record": mpath}))
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `BUILD_PAYLOAD_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_PAYLOAD_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
