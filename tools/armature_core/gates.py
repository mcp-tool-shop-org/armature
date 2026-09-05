"""The gates.

Every function here **raises**. None of them uses `assert`, none of them consults an
environment variable, and none of them takes a `skip` argument. They are called from
inside the function that performs the write, in the same process — never chained
behind a shell `&&`, because a chain can walk past a failing exit code.

Why the generator constraints are constants here and not fields in the shot spec:
a spec-supplied `dim_divisor` is a skip flag wearing a schema's clothes — a spec
could set it to 1 and walk straight past G1. So the spec may only *name* a
generator profile, and an unrecognised name raises. **The andon is on the direction
the invariant does not bound:** an unknown generator is the case where nothing is
checked at all, so that is the case that halts.
"""

import os

from .errors import (
    G1GeneratorLegality,
    G2Completeness,
    G4BboxSanity,
    G5ConventionConformance,
    G6SubjectMotion,
    GateBBatching,
    GateRRoundTrip,
    GateSSeedRegistration,
)
from .parts import require_finite
#: G6's vocabulary is `shotspec`'s, imported rather than re-typed here — one home for the
#: set of animation modes, so a third mode cannot be added to the contract and join G6's
#: passing side unexamined. `shotspec` imports only `errors` and `parts`, so this is not a
#: cycle; `normalise_spec` refuses a value outside the tuple, and G6 now refuses one too.
from .shotspec import ANIMATION_MODES


class GeneratorProfile:
    """A generator's legality constraints, pinned to a retrieved source."""

    def __init__(self, name, dim_divisor, frame_modulus, frame_residue, source):
        self.name = name
        self.dim_divisor = dim_divisor
        self.frame_modulus = frame_modulus
        self.frame_residue = frame_residue
        self.source = source

    def as_dict(self):
        return {
            "name": self.name,
            "dim_divisor": self.dim_divisor,
            "frame_form": f"{self.frame_modulus}n+{self.frame_residue}",
            "source": self.source,
        }


# F24 (docs/research-grounding.md): "width and height must be divisible by 16;
# frame count follows 4n+1 (temporal compression factor 4, first frame padded)".
# Status in the spec's premise table: RETRIEVED from ComfyUI docs, not tested here.
GENERATOR_PROFILES = {
    "wan-vace": GeneratorProfile(
        name="wan-vace",
        dim_divisor=16,
        frame_modulus=4,
        frame_residue=1,
        source="F24 / docs.comfy.org tutorials/video/wan/vace, fetched 2026-08-10",
    ),
    # A3's row. Its provenance is DERIVED, and the derivation is stated rather than
    # dressed up as a separate retrieval, because there is no Fun-Control-specific
    # document behind it.
    #
    # What is measured: both saved E02 graphs load the SAME VAE file,
    # `wan_2.1_vae.safetensors` (armature-E02-vace-control node 105 and
    # armature-E02-funcontrol node 92, widget values read 2026-08-10). The 4n+1 frame
    # form is a property of that VAE's temporal compression factor of 4, and the /16
    # divisor of the spatial compression plus patch size — so both constraints follow
    # from the component the two routes share, not from the route.
    #
    # What is NOT measured: `Wan22FunControlToVideo`'s own schema enforces neither
    # (length min 1 max 16384, dims min 16 max 16384, measured via get_node), so
    # nothing upstream will catch an illegal frame count on this route either.
    "wan-fun-control": GeneratorProfile(
        name="wan-fun-control",
        dim_divisor=16,
        frame_modulus=4,
        frame_residue=1,
        source=(
            "DERIVED 2026-08-10 from the shared VAE: both E02 graphs load "
            "wan_2.1_vae.safetensors (measured widget values), and 4n+1 / div-16 are "
            "properties of that VAE's temporal and spatial compression, so F24's "
            "constraint transfers on a measured shared component rather than on the "
            "family name. No Fun-Control-specific document was retrieved."
        ),
    ),
    # E08's row, and the first whose constraints come from the node's OWN schema rather
    # than from a tutorial or a shared component. `get_node("WanAnimateToVideo")`, measured
    # 2026-08-12, declares `width`/`height` with step=16 and `length` with step=4 default
    # 77; the node's source computes `latent_length = ((length - 1) // 4) + 1`, which is the
    # 4n+1 form written as arithmetic. The 81-frame trained horizon is NOT in the schema —
    # `length` accepts up to 16384 — and is carried from the Wan family's own record
    # (consult #3), so that half is inherited and is marked as such.
    "wan-animate": GeneratorProfile(
        name="wan-animate",
        dim_divisor=16,
        frame_modulus=4,
        frame_residue=1,
        source=(
            "MEASURED 2026-08-12 from the WanAnimateToVideo schema (width/height step=16, "
            "length step=4 default 77) and its source arithmetic "
            "latent_length = ((length - 1) // 4) + 1. The trained-horizon bound is "
            "inherited from the Wan family record (consult #3), not from this schema, "
            "which accepts length up to 16384 and would enforce nothing."
        ),
    ),
    # E11's row. Its provenance is DERIVED and the derivation is written out rather than
    # borrowed from the sibling row above, because `WanImageToVideo`'s schema does NOT
    # carry the step fields `WanAnimateToVideo`'s does — measured via `get_node`
    # 2026-08-12, it declares width/height/length as plain INT with min 16/16/1 and max
    # 16384 and would enforce nothing at all.
    #
    # What IS measured, three ways that agree:
    #   * the shared VAE. This route loads `wan_2.1_vae.safetensors`, the same file the
    #     E02 graphs load, and 4n+1 / div-16 are properties of that VAE's temporal
    #     compression factor of 4 and its spatial compression plus patch size. This is the
    #     identical transfer the `wan-fun-control` row above records, on a measured shared
    #     component rather than on a family name.
    #   * the node's own declared defaults: width 832, height 480, length 81 — each of
    #     which already satisfies the constraint being claimed.
    #   * the documented reference workflow's latent, 640x640x81, likewise.
    #
    # The 81-frame trained horizon is inherited from the Wan family record (consult #3),
    # exactly as the `wan-animate` row inherits it, and is marked as inherited here too.
    "wan-i2v": GeneratorProfile(
        name="wan-i2v",
        dim_divisor=16,
        frame_modulus=4,
        frame_residue=1,
        source=(
            "DERIVED 2026-08-12 (E11) from the shared VAE — this route loads "
            "wan_2.1_vae.safetensors, and 4n+1 / div-16 are properties of that VAE's "
            "temporal and spatial compression — and CONFIRMED against two independent "
            "readings: the WanImageToVideo schema's own defaults (832x480x81, get_node "
            "2026-08-12) and the documented reference workflow's latent (640x640x81, "
            "Comfy-Org/workflow_templates video_wan2_2_14B_i2v.json @ 5d6089c4250f). The "
            "schema itself declares only min/max and would enforce neither constraint. "
            "The trained-horizon bound is inherited from the Wan family record "
            "(consult #3), not measured here."
        ),
    ),
    # E11 wave 3's row. Same VAE as `wan-i2v` above — the Fun-Camera checkpoint is a
    # DERIVATIVE of Wan2.2-I2V-A14B and loads `wan_2.1_vae.safetensors`, so div-16 and 4n+1
    # carry over unchanged. It gets its own row rather than borrowing the I2V one because
    # its trained envelope is stated on its OWN card and differs from the I2V default: a
    # route running the camera weights reads its constraints from the camera model's
    # document, not from a neighbour's. Wave 2 is the whole argument for that distinction.
    "wan-fun-camera": GeneratorProfile(
        name="wan-fun-camera",
        dim_divisor=16,
        frame_modulus=4,
        frame_residue=1,
        source=(
            "DERIVED 2026-08-12 (E11 wave 3) from the shared VAE — this route loads "
            "wan_2.1_vae.safetensors and div-16 / 4n+1 are properties of that VAE's "
            "spatial and temporal compression, identical to the wan-i2v row above. The "
            "model's OWN envelope is quoted verbatim from "
            "huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera README_en.md, "
            "fetched 2026-08-12: 'multi-resolution (512, 768, 1024) video prediction, "
            "trained with 81 frames at 16 FPS'. Those tiers are the TRAINED envelope, not "
            "limits any node enforces — the schema declares only min/max — so they bound "
            "in-distribution CHOICE rather than legality, and the frame is derived against "
            "them in build_camera_i2v_payload.FRAME_DERIVATION."
        ),
    ),
}


def resolve_generator(name):
    """Look up a generator profile by name, or raise G1.

    An unknown generator is a G1 failure rather than a spec error on purpose: the
    consequence of proceeding is an illegal frame that fails *quietly* downstream,
    which is exactly what G1 exists to prevent.
    """
    profile = GENERATOR_PROFILES.get(name)
    if profile is None:
        raise G1GeneratorLegality(
            f"unknown generator profile {name!r}; no legality constraints are known "
            f"for it, so nothing would be checked",
            {"gate": "G1", "andon": "G1GeneratorLegality", "clause": "unknown_generator_profile",
             "generator": name, "known": sorted(GENERATOR_PROFILES)},
        )
    return profile


def g1_generator_legality(width, height, frame_count, generator):
    """G1 · ANDON — generator legality. Raises before any frame is written.

    width and height divisible by the profile's divisor; frame count congruent to
    the profile's residue modulo its modulus.
    """
    profile = resolve_generator(generator)
    problems = []

    for axis, value in (("width", width), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool):
            problems.append(f"{axis} must be an int, got {type(value).__name__}")
        elif value <= 0:
            problems.append(f"{axis} must be positive, got {value}")
        elif value % profile.dim_divisor != 0:
            problems.append(
                f"{axis}={value} is not divisible by {profile.dim_divisor} "
                f"(remainder {value % profile.dim_divisor})"
            )

    if not isinstance(frame_count, int) or isinstance(frame_count, bool):
        problems.append(f"frame count must be an int, got {type(frame_count).__name__}")
    elif frame_count <= 0:
        problems.append(f"frame count must be positive, got {frame_count}")
    elif frame_count % profile.frame_modulus != profile.frame_residue:
        problems.append(
            f"frame count={frame_count} is not of the form "
            f"{profile.frame_modulus}n+{profile.frame_residue} "
            f"(remainder {frame_count % profile.frame_modulus}, "
            f"want {profile.frame_residue})"
        )

    if problems:
        raise G1GeneratorLegality(
            "frame is not legal for generator "
            f"{profile.name!r}: " + "; ".join(problems),
            {
                "gate": "G1",
                "andon": "G1GeneratorLegality", "clause": "frame_not_generator_legal",
                "width": width,
                "height": height,
                "frame_count": frame_count,
                "profile": profile.as_dict(),
                "problems": problems,
            },
        )
    return profile


def g2_completeness(run_dir, expected, frame_count):
    """G2 · ANDON — completeness. Raises before the manifest is written.

    `expected` maps a channel directory name to the list of file names that channel
    must contain. Every directory must hold exactly those files, each of them
    non-empty. A partial export must never look like a finished one, so this runs
    *before* the manifest — the manifest is the thing that makes a run look finished.

    **The population is the DIRECTORY, not the expectation.** Iterating `expected`
    can only ever discover absence: a stale frame left behind by a longer previous
    run into an uncleaned `run_dir` is present, correctly named and out of range, and
    a count built from the expectation cannot see it. The extra file is reachable —
    `encode_control.load_frames` and `gate_b_frames.frame_paths` both build their
    populations with `os.listdir` over the channel directory — so the encoder would
    carry a frame count G1 never declared legal, on a green G2. `gate_b_batching`
    already makes this argument for its own quantity ("a batch larger than submitted
    is as wrong as a smaller one"); the andon is on the direction the invariant does
    not bound, and here that direction is *surplus*.

    Only files whose extension one of the expected names carries are counted: a
    channel's population is its frames, and a sidecar of another extension beside them
    is not a frame. When `expected` names no files at all, every entry counts.
    """
    # · ANDON — completeness over zero channels is not a completeness verdict.
    #
    # The loop iterates `expected`, so an empty mapping walked no channels and this
    # function returned {} — a PASS having examined nothing, with no statement anywhere
    # that nothing was examined. Measured 2026-09-03: g2_completeness(<empty tmpdir>, {},
    # 33) returned {}. The population argument this function already makes for SURPLUS
    # ("the andon is on the direction the invariant does not bound") was never put under
    # the channel population itself. `normalise_spec` refuses an empty channels list, so
    # an empty mapping needs a caller bug to arrive here — and this gate runs immediately
    # before the manifest that makes a run look finished.
    if not expected:
        raise G2Completeness(
            "G2 was asked to check completeness over ZERO channels, which is not a "
            "completeness verdict: nothing would be examined and the manifest written "
            "after it would report a finished run. The caller built its channel "
            "expectation wrongly — spec.channels cannot be empty",
            {"gate": "G2", "andon": "G2Completeness", "clause": "completeness_over_zero_channels",
             "run_dir": run_dir, "frame_count": frame_count, "expected_channels": [],
             "channels": {}},
        )

    problems = []
    detail = {}

    for channel, filenames in sorted(expected.items()):
        cdir = os.path.join(run_dir, channel)
        if not os.path.isdir(cdir):
            problems.append(f"{channel}: directory missing")
            detail[channel] = {"present": 0, "expected": frame_count,
                               "missing": [], "empty": [], "unexpected": []}
            continue

        present, empty, missing = [], [], []
        for fname in filenames:
            path = os.path.join(cdir, fname)
            if not os.path.isfile(path):
                missing.append(fname)
                continue
            present.append(fname)
            if os.path.getsize(path) == 0:
                empty.append(fname)

        exts = {os.path.splitext(f)[1].lower() for f in filenames}
        on_disk = [f for f in sorted(os.listdir(cdir))
                   if os.path.isfile(os.path.join(cdir, f))
                   and (not exts or os.path.splitext(f)[1].lower() in exts)]
        unexpected = [f for f in on_disk if f not in set(filenames)]

        detail[channel] = {
            "present": len(present),
            "expected": frame_count,
            "missing": missing[:8],
            "empty": empty[:8],
            "unexpected": unexpected[:8],
            "on_disk": len(on_disk),
        }
        if len(present) != frame_count:
            problems.append(
                f"{channel}: {len(present)} frames present, expected {frame_count}"
                + (f" (missing e.g. {missing[:3]})" if missing else "")
            )
        if unexpected:
            problems.append(
                f"{channel}: {len(unexpected)} unexpected file(s) in the directory, "
                f"e.g. {unexpected[:3]} — a frame nobody declared is a frame the "
                f"encoder would still pick up"
            )
        if empty:
            problems.append(f"{channel}: {len(empty)} zero-length file(s), e.g. {empty[:3]}")

    if problems:
        raise G2Completeness(
            "export is incomplete: " + "; ".join(problems),
            {"gate": "G2", "andon": "G2Completeness", "clause": "export_incomplete",
             "run_dir": run_dir, "frame_count": frame_count, "channels": detail},
        )
    return detail


#: G4's tolerance, in pixels. A module constant for the same reason the generator
#: profiles are: a spec-supplied number is a skip flag wearing a schema's clothes, and
#: a caller-supplied one is the same flag wearing an argument's. It used to arrive
#: through `spec.gates.g4_tolerance_px`, which `normalise_spec` validated in no way at
#: all — measured 2026-09-03, the values 1000000000, -5, 'off' and None were every one
#: accepted, and `g4_bbox_sanity(0, (0,0,10,10), (5000,5000,5010,5010), 10**9, ...)`
#: returned deltas of 5000 px without raising. A mask that is not the subject would then
#: be rendered, submitted and receipted with G4 green. The spec now refuses the key.
G4_TOLERANCE_PX = 2

#: Why this number is global where CLAUDE.md warns against a global constant governing a
#: local feature: the quantity it bounds is not a property of the structure. The
#: projected bbox is every mesh vertex pushed through the camera matrix and clipped to
#: the frame, so for a polygonal mesh it IS the expected silhouette bbox exactly, and the
#: only slack the gate owes is rasterisation — half a pixel per edge, independent of how
#: large the subject is. Scaling it with the bbox would loosen the gate precisely on the
#: subjects that fill the frame. The evidence reports the projected bbox's own size
#: beside the deltas so a reader can see what the operation changed per structure.
G4_TOLERANCE_SOURCE = (
    "gates.G4_TOLERANCE_PX — rasterisation slack, not a per-shot parameter; the spec "
    "may not carry it (see normalise_spec) and no caller may widen it"
)


def g4_bbox_sanity(frame_index, mask_bbox, projected_bbox, width, height):
    """G4 · Bbox sanity — the check that catches a channel rendering the wrong thing.

    `mask_bbox` and `projected_bbox` are (x0, y0, x1, y1) inclusive pixel bounds, or
    None for empty. The projected bbox is the bbox of every mesh vertex pushed
    through the camera matrix, clipped to the frame — for a polygonal mesh that is
    the exact expected silhouette bbox, so the tolerance is tight and the check
    binds in **both** directions: a mask far larger than the mesh (facet's 751-px
    mask around a 388-px mesh) and a mask that has collapsed to nothing.

    The tolerance is `G4_TOLERANCE_PX` and there is no argument for it. See that
    constant for what a settable one cost.
    """
    tolerance_px = G4_TOLERANCE_PX
    ev = {
        "gate": "G4",
        "andon": "G4BboxSanity",
        "frame": frame_index,
        "mask_bbox": mask_bbox,
        "projected_bbox": projected_bbox,
        "tolerance_px": tolerance_px,
        "tolerance_source": G4_TOLERANCE_SOURCE,
        "resolution": [width, height],
    }

    # · ANDON — the FRAME, before either box is read against it. The containment clause
    # below is the first thing on this page to READ `width` and `height` rather than
    # transcribe them into the receipt, and a resolution that is not two positive integers
    # would disarm it in silence — which is the disease this whole finding is about. A
    # check that can be switched off by an unreadable argument is not a check, so the
    # argument is refused by name (wave 10's rule: a disarming default is a refusal).
    for name, value in (("width", width), ("height", height)):
        if (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            ev["clause"] = "resolution_is_not_a_frame_size"
            ev["offending_field"] = name
            ev["offending_value"] = repr(value)
            raise G4BboxSanity(
                f"frame {frame_index}: {name} is {value!r}, which is not a positive "
                f"integer pixel dimension. G4 reads the resolution to decide whether a "
                f"bbox lies inside the frame at all; an unreadable one would leave that "
                f"clause silently disarmed while the receipt still recorded a resolution",
                ev,
            )

    # A bbox that is not four numbers is a malformed question, not a small disagreement.
    #
    # `zip(mask_bbox, projected_bbox)` truncates to the SHORTER sequence, so a bbox with
    # fewer than four edges was compared on only the edges it has and the gate passed on
    # the rest. Measured 2026-09-03: g4_bbox_sanity(0, (10, 10), (10, 10, 500, 500), 832,
    # 480) returned [0, 0] — a PASS having compared two of four edges against a projected
    # box 490 px wider. `startframe.mask_bbox` returns a 4-tuple or None on every path
    # today, so no production caller can produce a short bbox; a future mask source that
    # returns a 2- or 3-element bound would get a silent partial comparison from the gate
    # whose whole job is catching a channel that rendered the wrong thing. Refused by
    # name, the way `route_gates._frame_triple` refuses a frame that is not three numbers.
    for label, box in (("mask_bbox", mask_bbox), ("projected_bbox", projected_bbox)):
        if box is None:
            continue
        if (not isinstance(box, (list, tuple)) or len(box) != 4
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in box)):
            ev["clause"] = "bbox_is_not_four_numbers"
            raise G4BboxSanity(
                f"frame {frame_index}: {label} is {box!r}, which is not four numbers "
                f"(x0, y0, x1, y1). Two out of four edges compared is not a comparison, "
                f"and the surplus edges would have passed unexamined",
                ev,
            )
        # · ANDON — and the four numbers are NUMBERS. The clause above says `float`, and
        # `float('nan')` is a float, so the one `>` comparison on this page that the
        # non-finite family did not reach is `max(deltas) > tolerance_px`. A NaN disables
        # the WHOLE comparison rather than a quarter of it, because `max()` returns the
        # NaN when it is first and `nan > tolerance_px` is False. Measured 2026-09-04:
        # `g4_bbox_sanity(0, (nan,nan,nan,nan), (10,10,500,500), 832, 480)` returned
        # `[nan,nan,nan,nan]` — a PASS — and `g4_bbox_sanity(0, (10,10,20,20),
        # (nan,10,500,500), 832, 480)` returned `[nan, 0, 480, 480]`, also a PASS, on a
        # mask disagreeing with the projected mesh by 480 px on two of four edges.
        #
        # Bounded honestly: no production caller can produce this today —
        # `blender_scene.projected_bbox_px` returns ints and drops non-finite points at
        # its `inside` mask, and `startframe.mask_bbox` returns integer pixel bounds — so
        # this is the same latent class as the short-bbox case above, filed because a
        # future mask source, or a bbox read back out of a JSON record (where the bare
        # token `NaN` parses), arrives through the same argument.
        #
        # Through `parts.require_finite` — the repo's ONE non-finite helper — so this page
        # does not grow its own spelling of it. `positive=False`: a bbox edge may sit at 0
        # and a projected one may sit off-frame at a negative pixel.
        for edge, v in zip(("x0", "y0", "x1", "y1"), box):
            require_finite(f"{label}.{edge}", v, G4BboxSanity, ev, positive=False)
        # · ANDON — the third and fourth properties of the same four numbers. Arity has a
        # clause, member type has a clause, finiteness has a clause; ORDERING and
        # CONTAINMENT did not, and containment's two parameters were already in the
        # signature. Measured 2026-09-05 in this worktree on `580af47`: inside this
        # function the names `width` and `height` occurred exactly ONCE each, both inside
        # `ev['resolution'] = [width, height]` — written into the receipt and deciding
        # nothing. `g4_bbox_sanity(0, (5000,5000,5010,5010), (5002,5002,5012,5012), 832,
        # 480)` returned `[2,2,2,2]`, a PASS on two boxes entirely off an 832x480 frame;
        # `(-900,-900,-880,-880)` against itself returned `[0,0,0,0]`; and
        # `(500,400,10,10)` against itself returned `[0,0,0,0]` with
        # `ev['projected_bbox_size_px']` composed as `[-490, -390]` — a receipt asserting
        # the projected silhouette is negative on both axes.
        #
        # The docstring declares both contracts these violate: "(x0, y0, x1, y1) INCLUSIVE
        # pixel bounds", and a projected bbox that is every mesh vertex "clipped to the
        # frame". Bounded honestly: `blender_scene.projected_bbox_px` clips and returns
        # ints and `startframe.mask_bbox` returns ordered integer bounds, so no production
        # caller can produce either today — the input class is a future mask source, a
        # bbox read back out of a JSON manifest, or a camera change that moves the subject
        # off frame. That is the same class the arity and finiteness clauses above were
        # written for, on the gate whose stated job is catching a channel rendering the
        # wrong thing.
        x0, y0, x1, y1 = box
        if x1 < x0 or y1 < y0:
            ev["clause"] = "bbox_corners_out_of_order"
            ev["offending_bbox"] = list(box)
            ev["offending_label"] = label
            ev["failed_edges"] = [e for e, bad in (("x", x1 < x0), ("y", y1 < y0)) if bad]
            raise G4BboxSanity(
                f"frame {frame_index}: {label} is {tuple(box)}, whose corners are out of "
                f"order — (x0, y0, x1, y1) are inclusive bounds, so x1 >= x0 and "
                f"y1 >= y0. A reversed box makes every delta below a comparison between "
                f"two different questions, and the receipt would record a silhouette size "
                f"of {[x1 - x0, y1 - y0]}, which is not a size",
                ev,
            )
        outside = [name for name, bad in (
            ("x1 < 0", x1 < 0), ("y1 < 0", y1 < 0),
            (f"x0 > {width - 1}", x0 > width - 1),
            (f"y0 > {height - 1}", y0 > height - 1)) if bad]
        if outside:
            ev["clause"] = "bbox_outside_the_frame"
            ev["offending_bbox"] = list(box)
            ev["offending_label"] = label
            ev["failed_edges"] = outside
            raise G4BboxSanity(
                f"frame {frame_index}: {label} is {tuple(box)}, which lies wholly outside "
                f"the {width}x{height} frame ({', '.join(outside)}). The projected bbox is "
                f"clipped to the frame by definition and a mask is read out of it, so a "
                f"box with no pixel inside the image is a channel that rendered the wrong "
                f"thing — the failure this gate exists to catch, and the one it passed on "
                f"whenever the mask and the projection agreed with each other off-frame",
                ev,
            )

    if projected_bbox is None:
        ev["clause"] = "projected_bbox_is_empty"
        raise G4BboxSanity(
            f"frame {frame_index}: no mesh vertex projects into the frame, so the "
            f"expected silhouette is undefined",
            ev,
        )
    if mask_bbox is None:
        ev["clause"] = "mask_bbox_is_empty"
        raise G4BboxSanity(
            f"frame {frame_index}: mask is empty, but the mesh projects to "
            f"{projected_bbox}",
            ev,
        )

    deltas = [abs(a - b) for a, b in zip(mask_bbox, projected_bbox)]
    ev["deltas_px"] = deltas
    # Per-structure, so a reader sees what the operation changed on THIS bbox rather
    # than only a global number: the projected silhouette's own width and height.
    ev["projected_bbox_size_px"] = [projected_bbox[2] - projected_bbox[0],
                                    projected_bbox[3] - projected_bbox[1]]
    if max(deltas) > tolerance_px:
        ev["clause"] = "mask_disagrees_with_projection"
        raise G4BboxSanity(
            f"frame {frame_index}: mask bbox {tuple(mask_bbox)} disagrees with the "
            f"projected mesh bbox {tuple(projected_bbox)} by {deltas} px "
            f"(tolerance {tolerance_px} px)",
            ev,
        )
    return deltas


def g5_openpose_conformance(keypoint_count, limb_seq, reference_count, reference_limb_seq):
    """G5 · Convention conformance — only reached when `pose` is actually emitted.

    Compared element for element against the **retrieved** reference (F20), not
    against memory, and including its 1-indexing: F20 records `limbSeq` as 19 pairs
    that index keypoints from 1, which is a live trap for a from-scratch renderer.

    ⚠ **DORMANT — this gate has NO production call site anywhere in the tree, and it stays
    dormant until the drawing convention is retrieved.** Grepped 2026-09-04 across `tools/`
    and `tests/`: `g5_openpose_conformance` appears at this definition, in `cli.SURFACE`'s
    gate list, and in `tests/test_gates.py` — and nowhere else. The pose channel cannot be
    emitted today: `stage_render.py:281-284` calls `openpose.require_drawing_convention()`
    whenever `pose` is requested and that function raises unconditionally, because
    `openpose.PALETTE` and `openpose.KEYPOINT_NAMES` are both None. So there is nothing to
    wire this to yet, and wiring it to a channel that cannot exist would be a call site
    that can never run.

    **What that does NOT license is a manifest asserting a verdict this gate never
    computed.** `stage_render.py:470-471` writes
    `"G5": {"verdict": "NOT RUN -- pose was not emitted"} if "pose" not in requested else
    {"verdict": "PASS"}` — a literal PASS for a gate the file never invokes, beside
    G1/G2/G4/G6 verdicts that are all read back from gates that did run. The day the
    convention is retrieved and the pose channel is enabled, that manifest asserts G5 PASS
    on the first run and this andon — the one that exists because F20's retrieved `limbSeq`
    is 1-indexed while a from-scratch renderer will emit 0-indexed pairs — never fires. The
    manifest half is `stage_render`'s (instruments-measure domain, routed 2026-09-04); the
    half that lives here is this record and the empty-population refusal below.
    """
    # · ANDON — a conformance verdict over ZERO keypoints and ZERO limb pairs is not a
    # verdict. Measured 2026-09-04: `g5_openpose_conformance(0, [], 0, [])` returned True
    # having compared nothing — the counts agreed because both were zero, the pair loop
    # ran zero times, and `flat` was empty so the 0-indexing clause was skipped too. Its
    # siblings on this page carry exactly this refusal for exactly this reason
    # (`g2_completeness` on an empty channel mapping, `gate_r_round_trip` on an empty
    # frame pair), and this gate needs it MORE than they do, not less: the population it
    # would be handed on the first live run comes from a renderer that does not exist yet,
    # and an empty skeleton is the shape a stub emits.
    if not reference_count or not list(reference_limb_seq):
        raise G5ConventionConformance(
            f"G5 was asked to check conformance against a reference of "
            f"{reference_count!r} keypoint(s) and {len(list(reference_limb_seq))} limb "
            f"pair(s), which is not a conformance verdict: with an empty reference the "
            f"count clause agrees because both sides are zero, the pair loop runs zero "
            f"times and the 1-indexing clause has no index to read. F20's retrieved "
            f"convention is 18 keypoints and 19 limb pairs; an empty one means the "
            f"reference was never loaded",
            {"gate": "G5", "andon": "G5ConventionConformance",
             "clause": "empty_reference",
             "keypoint_count": keypoint_count,
             "reference_count": reference_count,
             "n_limb_pairs": len(list(limb_seq)),
             "n_reference_limb_pairs": len(list(reference_limb_seq))},
        )

    problems = []
    if keypoint_count != reference_count:
        problems.append(f"keypoint count {keypoint_count} != {reference_count}")

    ours = [list(p) for p in limb_seq]
    theirs = [list(p) for p in reference_limb_seq]
    if len(ours) != len(theirs):
        problems.append(f"limb pair count {len(ours)} != {len(theirs)}")
    else:
        for i, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                problems.append(f"limb pair {i}: {a} != reference {b}")

    flat = [v for pair in ours for v in pair]
    if flat and min(flat) == 0:
        problems.append(
            "limb pairs are 0-indexed; F20's retrieved limbSeq is 1-indexed"
        )

    if problems:
        raise G5ConventionConformance(
            "emitted skeleton does not match the retrieved OpenPose-18 convention: "
            + "; ".join(problems),
            {
                "gate": "G5",
                "andon": "G5ConventionConformance", "clause": "openpose_convention_mismatch",
                "keypoint_count": keypoint_count,
                "reference_count": reference_count,
                "problems": problems,
            },
        )
    return True


def g6_subject_motion(frame_signatures, animation_mode):
    """G6 · ANDON — a spec that asked for a performance got one. Raises.

    `frame_signatures` is one hashable value per frame, derived from the subject's
    **evaluated** world-space vertices (so it follows modifiers, parenting and the
    imported glTF action, not the authored intent). `animation_mode` is the spec's
    `subject.animation`.

    **Only `per_frame` is checked, and that is the point.** In `static` mode a constant
    subject is correct — E01 pins the scene to frame 1 deliberately so P3 measures
    normalisation on geometry that does not move — so checking it there would be a check
    that cannot fail. In `per_frame` mode the spec has asserted that the subject performs,
    and every other gate in this tool is blind to whether it did: legality, completeness
    and bbox sanity all pass on 33 identical frames.

    **What it does NOT claim.** A partially-broken action — some frames moving, some not —
    is not caught, because the failure this exists for is binary: the glTF round trip
    either carried the action or it did not. The per-frame displacement diagnostic in the
    manifest is where a weak or truncated arc shows itself, and it gates nothing.

    Raising on *all* frames identical rather than on *any* adjacent pair identical is
    deliberate: a slow arc can legitimately hold still between two frames, and a gate that
    fired on that would be a gate that fails on correct work.
    """
    ev = {
        "gate": "G6",
        "andon": "G6SubjectMotion",
        "animation_mode": animation_mode,
        "n_frames": len(frame_signatures),
        "distinct_signatures": len(set(frame_signatures)),
    }
    # · ANDON — the answer is split THREE ways, not two. This clause read
    # `if animation_mode != 'per_frame': return N/A`, an inequality against ONE literal
    # rather than membership in the recorded vocabulary, so the gate disarmed itself IN
    # THE AFFIRMATIVE on any mode it did not recognise. Measured 2026-09-05 in this
    # worktree on `580af47`: `g6_subject_motion(['a'] * 33, 'per-frame')` and
    # `g6_subject_motion(['a'] * 33, None)` both RETURNED the N/A verdict over 33
    # identical signatures — the exact input this gate exists to refuse — quoting the
    # unrecognised value back as if it were a mode.
    #
    # The vocabulary is `shotspec.ANIMATION_MODES`, imported rather than re-typed: a third
    # mode added there must have its G6 semantics chosen, and until it is chosen it joins
    # on the REFUSING side rather than silently on the passing one. `normalise_spec`
    # refuses a value outside the tuple, so the live path through `stage_render` is
    # bounded; the exposure is a caller that does not normalise first, a spec dict mutated
    # after normalisation, or that third mode. Every neighbouring "value I do not
    # recognise" in this package already raises — `route_gates.pairing` on a conditioning
    # class in neither table, `hosted_frame_legality` on an unrecorded tier,
    # `frame_legality` on an unrecorded generator family — and G6 was the one whose "not
    # applicable" answer was reachable by a typo.
    if animation_mode not in ANIMATION_MODES:
        ev["clause"] = "unknown_animation_mode"
        ev["animation_modes"] = list(ANIMATION_MODES)
        raise G6SubjectMotion(
            f"subject.animation is {animation_mode!r}, which is not one of "
            f"{list(ANIMATION_MODES)}. G6 cannot say whether a performance was asked for, "
            f"and answering 'not applicable' would report the failure this gate exists to "
            f"catch — {len(frame_signatures)} frame(s), "
            f"{len(set(frame_signatures))} distinct — as a mode it does not check",
            ev,
        )
    if animation_mode != "per_frame":
        ev["verdict"] = f"N/A — subject.animation is {animation_mode!r}, not 'per_frame'"
        return ev

    if len(frame_signatures) < 2:
        ev["clause"] = "motion_undefined_over_one_frame"
        raise G6SubjectMotion(
            f"subject.animation is 'per_frame' but the shot is {len(frame_signatures)} "
            f"frame(s) long; motion is undefined over fewer than two frames",
            ev,
        )
    if ev["distinct_signatures"] == 1:
        ev["clause"] = "subject_never_moved"
        raise G6SubjectMotion(
            f"subject.animation is 'per_frame' but the subject's evaluated geometry is "
            f"IDENTICAL at all {len(frame_signatures)} frames — the authored performance "
            f"did not reach the render. Every other gate passes on this: the frames are "
            f"legal, complete, and the mask matches the projected mesh, because a static "
            f"mesh projects consistently. Check that the GLB carries an action, that the "
            f"scene frame range spans the shot, and that export fps matches render fps",
            ev,
        )
    ev["verdict"] = "subject moved"
    return ev


def gate_r_round_trip(source, decoded, source_label="source PNGs", decoded_label="decoded video"):
    """Gate R · ANDON — the encode/decode round trip. Raises before any credit is spent.

    `source` and `decoded` are equal-length sequences of uint8 arrays, each either
    (H, W) or (H, W, 3). Raises `GateRRoundTrip` unless every pixel of every frame is
    identical.

    **Per-channel, deliberately.** The failure this gate exists to catch is chroma
    subsampling, which touches only the colour-difference channels — so a scalar mean
    over a grayscale (R=G=B) sequence is exactly zero whether or not the encoder is
    subsampling, and a gate reporting that scalar would read green on a pipeline that
    silently destroys the normal channel. The report therefore names *which channel*
    differs, and the caller is expected to run this on the channel that can actually
    fail rather than only on one that cannot.

    Frame count is checked first and separately: a decode that returns fewer frames
    than went in is the single most likely bridge failure (a frame-count form the
    muxer rounds), and it would otherwise surface as a confusing shape error.

    **The dtype is checked, and it is not paperwork.** The comparison is
    `astype(np.int16)`, which truncates: measured 2026-09-03, a float32 source of 0.4
    against a float32 decode of 0.6 both truncate to 0 and the gate returned
    `identical` on a 50 % per-pixel error, while uint8 200 against 201 correctly
    raised. A round trip over an array that is not 8 bits proves nothing about the
    8-bit bridge, so the wrong dtype halts here rather than answering the question it
    was not asked.
    """
    import numpy as np

    ev = {
        "gate": "R",
        "andon": "GateRRoundTrip",
        "n_source": len(source),
        "n_decoded": len(decoded),
        "source": source_label,
        "decoded": decoded_label,
    }

    if len(source) != len(decoded):
        ev["clause"] = "frame_count_changed_through_the_bridge"
        raise GateRRoundTrip(
            f"frame count changed through the bridge: {len(source)} in, "
            f"{len(decoded)} out",
            ev,
        )
    if not source:
        ev["clause"] = "round_trip_over_zero_frames"
        raise GateRRoundTrip("no frames to compare; the round trip proves nothing", ev)

    wrong_dtype = []
    for label, seq in ((source_label, source), (decoded_label, decoded)):
        for i, f in enumerate(seq):
            dt = np.asarray(f).dtype
            if dt != np.uint8:
                wrong_dtype.append({"side": label, "frame": i, "dtype": str(dt)})
    if wrong_dtype:
        ev["dtypes"] = wrong_dtype[:8]
        seen = sorted({d["dtype"] for d in wrong_dtype})
        ev["clause"] = "round_trip_dtype_not_uint8"
        raise GateRRoundTrip(
            f"the round trip was handed {', '.join(seen)} arrays where it documents "
            f"uint8: {len(wrong_dtype)} frame(s), e.g. {wrong_dtype[0]}. The "
            f"comparison truncates to int16, so a float pair differing by half a "
            f"level reads as identical — a green verdict about an 8-bit bridge that "
            f"was never crossed",
            ev,
        )

    problems, per_frame = [], []
    for i, (a, b) in enumerate(zip(source, decoded)):
        a = np.asarray(a)
        b = np.asarray(b)
        if a.shape != b.shape:
            problems.append(f"frame {i}: shape {a.shape} in, {b.shape} out")
            continue
        d = np.abs(a.astype(np.int16) - b.astype(np.int16))
        if d.any():
            rec = {
                "frame": i,
                "max_abs": int(d.max()),
                "mean_abs": float(d.mean()),
                "n_px_differing": int((d != 0).any(axis=-1).sum() if d.ndim == 3 else (d != 0).sum()),
            }
            if d.ndim == 3:
                rec["per_channel_max_abs"] = [int(d[..., c].max()) for c in range(d.shape[2])]
                rec["per_channel_mean_abs"] = [float(d[..., c].mean()) for c in range(d.shape[2])]
            per_frame.append(rec)
            problems.append(
                f"frame {i}: max |delta| {rec['max_abs']} over "
                f"{rec['n_px_differing']} px"
            )

    if problems:
        ev["frames_differing"] = len(per_frame)
        ev["detail"] = per_frame[:8]
        ev["clause"] = "round_trip_not_lossless"
        raise GateRRoundTrip(
            f"the encode/decode round trip is not lossless: "
            + "; ".join(problems[:6])
            + (f" (+{len(problems) - 6} more frames)" if len(problems) > 6 else ""),
            ev,
        )

    ev["verdict"] = "identical"
    return ev


def gate_b_batching(expected_frames, observed_batch_images, evidence=None):
    """Gate B · ANDON — the control batch actually carried every frame. Raises.

    `observed_batch_images` is the count of images returned by a save node wired
    directly to the batch node's output — the batch as the sampler received it, not the
    generated video. See `GateBBatching` for why the output frame count is the wrong
    quantity: `WanVaceToVideo` pads a short control up to `length`, so the video is 33
    frames either way and a check on it could never fire.

    **The andon is on the direction the invariant does not bound.** A batch larger than
    submitted is as wrong as a smaller one — duplicated links, or an auto-grow slot
    bound twice — and `!=` catches both, where `<` would wave the duplicate through.
    """
    ev = dict(evidence or {})
    ev.update({"gate": "B", "andon": "GateBBatching",
               "expected_frames": expected_frames,
               "observed_batch_images": observed_batch_images})

    # `bool` is a subclass of `int`, so the guard accepted True: measured 2026-09-03,
    # gate_b_batching(1, True) returned "batch intact" and gate_b_batching(0, False)
    # likewise. A caller that reduces the save node's output to a truthiness, or a JSON
    # `true` parsed out of a run record, passed Gate B on a one-frame expectation with
    # the evidence recording observed_batch_images: true — which is exactly what this
    # message calls "the batch was not observed". `g1_generator_legality` (above) and
    # `gate_s_seed_registration` (below) already close the hole this way; the clause is
    # theirs, carried here rather than written again.
    if (not isinstance(observed_batch_images, int)
            or isinstance(observed_batch_images, bool)
            or observed_batch_images < 0):
        ev["clause"] = "batch_count_is_not_a_count"
        raise GateBBatching(
            f"batch image count is not a count: {observed_batch_images!r}; the batch "
            f"was not observed, so batching is unverified rather than verified",
            ev,
        )

    # · ANDON — "batch intact" over ZERO submitted images is not a batching verdict.
    #
    # Measured 2026-09-04: `gate_b_batching(0, 0)` returned
    # `{'gate': 'B', ..., 'expected_frames': 0, 'observed_batch_images': 0,
    #   'verdict': 'batch intact'}`. This gate's own docstring makes the population
    # argument for the SURPLUS direction ("a batch larger than submitted is as wrong as a
    # smaller one") and never put it under the population itself; `g2_completeness` on
    # this page raises on an empty expectation for exactly that reason, in these words.
    # The single call site is `gate_b_frames.py:119`,
    # `gates.gate_b_batching(len(src_paths), len(got_paths))` over two `frame_paths()`
    # listings, so two empty or mistyped directories give 0 == 0.
    #
    # Bounded honestly: the very next statement in that tool is
    # `gates.gate_r_round_trip(src, got, ...)` (:122), which raises "no frames to compare;
    # the round trip proves nothing" on the same input before any record is written — so
    # the false verdict never reached a file. What it cost was the halt output: an operator
    # read Gate B reporting the batch intact immediately above Gate R saying there were no
    # frames at all, and spent the debugging time on the wrong bridge. It is placed BELOW
    # the bool clause so `gate_b_batching(0, False)` still refuses as "not a count" — the
    # observed value is the stronger defect and keeps its own message.
    if (not isinstance(expected_frames, int) or isinstance(expected_frames, bool)
            or expected_frames <= 0):
        ev["clause"] = "batch_expectation_is_not_a_count"
        raise GateBBatching(
            f"Gate B was asked to check a batch against an expectation of "
            f"{expected_frames!r} image(s), which is not a batching verdict: nothing was "
            f"submitted to compare against, and 'batch intact' would be a statement about "
            f"an empty population. g2_completeness refuses an empty channel expectation on "
            f"the same grounds",
            ev,
        )

    if observed_batch_images != expected_frames:
        short = observed_batch_images < expected_frames
        ev["clause"] = "batch_image_count_disagrees"
        raise GateBBatching(
            f"the control batch carried {observed_batch_images} image(s), not "
            f"{expected_frames}"
            + (
                " — BatchImagesNode bound only part of its auto-grow list, and the run "
                "would have proceeded on a padded control with no error anywhere"
                if short
                else " — more images than were submitted; a link is bound twice"
            ),
            ev,
        )
    ev["verdict"] = "batch intact"
    return ev


def gate_s_seed_registration(seed, registry, experiment, seed_was_explicit):
    """Gate S · ANDON — the seed was pre-registered. Raises before a payload exists.

    `registry` is the experiment's committed seed list, or None for an experiment that
    pre-registered none. `seed_was_explicit` says whether a caller *chose* this seed
    rather than inheriting the module's pinned constant.

    **It binds in both directions, and the second direction is the one that is easy to
    miss.** An experiment WITH a registry must draw from it — that is the obvious clause,
    and it stops a seed being picked after a result is seen. An experiment WITHOUT a
    registry may not vary its seed *at all* — because the moment a `--seed` flag exists,
    every experiment that never pre-registered anything becomes shoppable, and a gate
    that checked only registered experiments would have opened that door itself. E02 and
    E03 ran on a pinned constant no flag could move; that property has to survive the
    flag being added.

    Returns a verdict record for the meta file; the only paths out are that record or a
    raise. There is no argument that disables it, no environment variable, and no
    `assert` — see `GateSSeedRegistration` for what it is actually protecting, which is
    not a technical property of the output but the meaning of the number computed from it.
    """
    ev = {
        "gate": "S",
        "andon": "GateSSeedRegistration",
        "experiment": experiment,
        "seed": seed,
        "seed_was_explicit": bool(seed_was_explicit),
        "registry_size": len(registry) if registry is not None else 0,
        "registry_declared": registry is not None,
    }

    if not isinstance(seed, int) or isinstance(seed, bool):
        ev["clause"] = "seed_is_not_an_int"
        raise GateSSeedRegistration(
            f"seed must be an int, got {type(seed).__name__} ({seed!r}); a seed that is "
            f"not an integer cannot be compared against the committed list at all",
            ev,
        )

    # · `None` and `[]` are two different facts and this branch used to collapse them.
    # `None` is the documented meaning "this experiment pre-registered no seeds", which
    # the docstring above draws and the code did not; `[]` is "a list was declared and it
    # came back empty", which is not a registration at all.
    if registry is None:
        if seed_was_explicit:
            ev["clause"] = "experiment_has_no_seed_registry"
            raise GateSSeedRegistration(
                f"{experiment} has no pre-registered seed list, so its seed may not be "
                f"varied; {seed} was supplied explicitly. Pre-register the seeds in the "
                f"spec, in the commit that opens the experiment, before the first "
                f"submission — a seed chosen after a result is seen is seed-shopping, "
                f"and no later check can tell the difference",
                ev,
            )
        ev["verdict"] = f"N/A — {experiment} pre-registered no seeds and did not vary its own"
        return ev

    # · ANDON — a verdict over an EMPTY declared population, which is the refusal the four
    # siblings on these two pages were already given (`g2_completeness`,
    # `g5_openpose_conformance`, `gate_b_batching`, `rig_gates.gate_n_names`) and Gate S
    # was the clause that still stated one. Measured 2026-09-04:
    # `gate_s_seed_registration(7, [], 'E14', False)` returned `registry_size: 0` with
    # verdict "N/A — E14 pre-registered no seeds and did not vary its own" — a PASS whose
    # verdict asserts a property of a spec this call never read.
    #
    # The direction nothing else bounds: an experiment whose spec DOES carry a committed
    # list, whose list is dropped or mis-keyed on the way here (a renamed spec field, a
    # `.get('seeds', [])`), submits any seed at all with Gate S reporting N/A. Gate S
    # guards a failure with NO technical symptom, so nothing downstream contradicts it and
    # the number is quoted forever against a run nobody registered.
    if not registry:
        ev["clause"] = "seed_registry_is_empty"
        raise GateSSeedRegistration(
            f"{experiment} declared a seed registry and it is EMPTY ({registry!r}), so "
            f"there is no committed list to check {seed} against. An empty list is not "
            f"the same fact as no list: 'N/A — pre-registered no seeds' over it is a "
            f"statement about a spec this call never read, and the shape that produces it "
            f"is a renamed spec field or a `.get('seeds', [])` default — exactly the "
            f"silent drop the committed list exists to make impossible. Pass None to mean "
            f"'this experiment pre-registered none', or fix the read that emptied the list",
            ev,
        )

    # · ANDON — the gate guarded the SEED's type and never the COMMITTED LIST's, and the
    # committed list is the object the whole andon rests on. The clause above refuses a
    # non-int seed with the reason written out — "a seed that is not an integer cannot be
    # compared against the committed list at all" — and the membership test below is a
    # bare `in`, which is `==` membership, so `bool` and `float` members compare equal to
    # ints. Measured 2026-09-04 in this worktree:
    # `gate_s_seed_registration(1, [True], 'E14', True)` returned verdict "seed is
    # pre-registered" with `registry_index: 0`; `(0, [False], ...)` likewise;
    # `(1, [1.0], ...)` likewise. Wave 16 closed exactly this bool-is-an-int hole on
    # `gate_b_batching`'s `observed_batch_images` and on this gate's own `seed`, with the
    # comment "a JSON `true` parsed out of a run record" naming the producer; the registry
    # arrives by the same route — a spec field, a `.get('seeds')`, a JSON list — and got
    # no clause. A spec whose committed list was written or parsed as `[true]` or `[7.0]`
    # pre-registers nothing, and Gate S returned a verdict stating a property of a
    # registry this module never read as a registry, on the andon whose whole point is
    # that a list removes the possibility a rule only forbids.
    #
    # It also closes the bare `TypeError` the last line of this function used to raise:
    # `sorted(registry).index(seed)` on a registry of mixed unorderable types is not an
    # `ArmatureError`, so the halt contract's exit-2 receipt branch was bypassed and a
    # refusal from this gate was recorded as an unhandled crash.
    #
    # Bounded honestly: no live caller in tools/ passes a non-int registry today (the
    # registries are module constants and spec fields), so this was the guard direction
    # unbounded rather than a live escape.
    bad_members = [(i, m) for i, m in enumerate(registry)
                   if not isinstance(m, int) or isinstance(m, bool)]
    if bad_members:
        raise GateSSeedRegistration(
            f"{experiment}'s committed seed list is not a list of integers: "
            + ", ".join(f"index {i} is a {type(m).__name__} ({m!r})"
                        for i, m in bad_members)
            + f". A member that is not an integer cannot be compared against {seed} at "
              f"all — `in` is `==` membership, so a JSON `true` or a `7.0` parsed out of "
              f"a spec field compares EQUAL to an int and pre-registers nothing while "
              f"reading like a registration. Fix the read that produced the list; this "
              f"gate guards a failure with no technical symptom, so nothing downstream "
              f"contradicts a verdict taken from a registry nobody validated",
            dict(ev, clause="registry_member_not_an_int",
                 offending_members=[{"index": i, "type": type(m).__name__, "value": repr(m)}
                                    for i, m in bad_members],
                 registry=[repr(m) for m in registry]),
        )

    if seed not in registry:
        ev["clause"] = "seed_not_registered"
        ev["registry"] = sorted(registry)
        raise GateSSeedRegistration(
            f"seed {seed} is not in {experiment}'s pre-registered list of "
            f"{len(registry)} seed(s). The list is committed in the spec before the "
            f"first submission precisely so this cannot be decided now: registered "
            f"{sorted(registry)}",
            ev,
        )

    ev["verdict"] = "seed is pre-registered"
    ev["registry_index"] = sorted(registry).index(seed)
    return ev
