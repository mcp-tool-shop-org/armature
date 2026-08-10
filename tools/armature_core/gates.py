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
    GateBBatching,
    GateRRoundTrip,
)


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
            {"generator": name, "known": sorted(GENERATOR_PROFILES)},
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
    must contain. Every directory must hold exactly `frame_count` files, each of
    them non-empty. A partial export must never look like a finished one, so this
    runs *before* the manifest — the manifest is the thing that makes a run look
    finished.
    """
    problems = []
    detail = {}

    for channel, filenames in sorted(expected.items()):
        cdir = os.path.join(run_dir, channel)
        if not os.path.isdir(cdir):
            problems.append(f"{channel}: directory missing")
            detail[channel] = {"present": 0, "expected": frame_count, "empty": []}
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

        detail[channel] = {
            "present": len(present),
            "expected": frame_count,
            "missing": missing[:8],
            "empty": empty[:8],
        }
        if len(present) != frame_count:
            problems.append(
                f"{channel}: {len(present)} frames present, expected {frame_count}"
                + (f" (missing e.g. {missing[:3]})" if missing else "")
            )
        if empty:
            problems.append(f"{channel}: {len(empty)} zero-length file(s), e.g. {empty[:3]}")

    if problems:
        raise G2Completeness(
            "export is incomplete: " + "; ".join(problems),
            {"run_dir": run_dir, "frame_count": frame_count, "channels": detail},
        )
    return detail


def g4_bbox_sanity(frame_index, mask_bbox, projected_bbox, tolerance_px, width, height):
    """G4 · Bbox sanity — the check that catches a channel rendering the wrong thing.

    `mask_bbox` and `projected_bbox` are (x0, y0, x1, y1) inclusive pixel bounds, or
    None for empty. The projected bbox is the bbox of every mesh vertex pushed
    through the camera matrix, clipped to the frame — for a polygonal mesh that is
    the exact expected silhouette bbox, so the tolerance is tight and the check
    binds in **both** directions: a mask far larger than the mesh (facet's 751-px
    mask around a 388-px mesh) and a mask that has collapsed to nothing.
    """
    ev = {
        "frame": frame_index,
        "mask_bbox": mask_bbox,
        "projected_bbox": projected_bbox,
        "tolerance_px": tolerance_px,
        "resolution": [width, height],
    }

    if projected_bbox is None:
        raise G4BboxSanity(
            f"frame {frame_index}: no mesh vertex projects into the frame, so the "
            f"expected silhouette is undefined",
            ev,
        )
    if mask_bbox is None:
        raise G4BboxSanity(
            f"frame {frame_index}: mask is empty, but the mesh projects to "
            f"{projected_bbox}",
            ev,
        )

    deltas = [abs(a - b) for a, b in zip(mask_bbox, projected_bbox)]
    ev["deltas_px"] = deltas
    if max(deltas) > tolerance_px:
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
    """
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
                "keypoint_count": keypoint_count,
                "reference_count": reference_count,
                "problems": problems,
            },
        )
    return True


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
    """
    import numpy as np

    ev = {
        "n_source": len(source),
        "n_decoded": len(decoded),
        "source": source_label,
        "decoded": decoded_label,
    }

    if len(source) != len(decoded):
        raise GateRRoundTrip(
            f"frame count changed through the bridge: {len(source)} in, "
            f"{len(decoded)} out",
            ev,
        )
    if not source:
        raise GateRRoundTrip("no frames to compare; the round trip proves nothing", ev)

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
    ev.update({"expected_frames": expected_frames, "observed_batch_images": observed_batch_images})

    if not isinstance(observed_batch_images, int) or observed_batch_images < 0:
        raise GateBBatching(
            f"batch image count is not a count: {observed_batch_images!r}; the batch "
            f"was not observed, so batching is unverified rather than verified",
            ev,
        )
    if observed_batch_images != expected_frames:
        short = observed_batch_images < expected_frames
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
