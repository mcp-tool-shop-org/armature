"""Exception types for the exporter.

Every gate raises one of these. **None of them is an AssertionError**, and none of
them is produced by an `assert` statement — CLAUDE.md: an `assert` is deleted by
`-O` or `PYTHONOPTIMIZE=1`, and 87 of facet's ANDONs turned out to be removable by
an environment variable. A `raise` is not.
"""


class ArmatureError(RuntimeError):
    """Base for every error this tool raises deliberately."""


class GateFailure(ArmatureError):
    """A gate fired. The run halts here; the caller reports evidence and stops.

    Subclasses carry the gate id so a report can name which andon pulled.
    """

    gate = "G?"

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}

    def __str__(self):  # pragma: no cover - formatting only
        base = super().__str__()
        return f"[{self.gate}] {base}"


class G1GeneratorLegality(GateFailure):
    """Frame dimensions or frame count are not legal for the target generator."""

    gate = "G1"


class G2Completeness(GateFailure):
    """An emitted channel is short, empty, or a frame file is zero-length."""

    gate = "G2"


class G4BboxSanity(GateFailure):
    """The mask's bounding box disagrees with the mesh's projected bounding box."""

    gate = "G4"


class G5ConventionConformance(GateFailure):
    """The emitted skeleton does not match the retrieved OpenPose-18 convention."""

    gate = "G5"


class G6SubjectMotion(GateFailure):
    """A spec asked for a performance and the subject did not move.

    E03's andon, and it stands on a failure that is **silent in every other check**.
    E01 renders an existing pose, so `configure_render` pinned the scene to frame 1 and
    an animated asset could not move. E03 authors a performance instead, which means the
    animation now has to survive an export to glTF, a re-import, and a frame-rate mapping
    from seconds back to frames — any one of which can drop it.

    If it does drop, **every other gate still passes**: the frames are legal (G1), all 33
    are written and non-empty (G2), and the mask agrees with the projected mesh at every
    frame (G4) because a static mesh projects consistently. Gate B would count 33 images in
    the batch. The run would produce a perfectly well-formed control sequence of a figure
    standing still, be submitted, and cost credits — and the experiment would conclude that
    authored motion does not transfer, when what actually happened is that no motion was
    ever authored into the frames.

    **The andon is on the direction the invariant does not bound.** Nothing else in this
    tool looks at whether the geometry changes between frames, so that is what this checks:
    in `per_frame` mode, the subject's evaluated vertices must differ across the shot.
    """

    gate = "G6"


class GateRRoundTrip(GateFailure):
    """The encoded control video did not decode back to the frames that went in.

    E02's andon on the upload bridge. It exists for a failure that is silent by
    construction: `-qp 0` is *luma*-lossless while x264 still defaults to `yuv420p`,
    which subsamples chroma 4:1. A grayscale channel (R=G=B) survives that untouched,
    so the corruption would appear only in the true-RGB normal channel — and the
    video would look correct either way.
    """

    gate = "R"


class GateBBatching(GateFailure):
    """The control batch that reached the sampler was not the batch we submitted.

    E02's andon on the PNG-batch bridge. `BatchImagesNode` takes an auto-grow list of
    IMAGE links; if that list were mis-encoded so only the first link bound, the run
    would proceed on a 1-frame control and nothing would error.

    **Why this gate does not count output frames.** `WanVaceToVideo` pads a short
    `control_video` up to `length` and emits `length` frames regardless, so the output
    is 33 frames whether the control batch held 33 images or 1. Counting the output
    would be a check that cannot fail. This gate counts the **batch itself**, saved
    straight off the batch node, which is the only quantity the defect actually moves.
    """

    gate = "B"


class GateSSeedRegistration(GateFailure):
    """A seed was about to be submitted that no committed list pre-registered.

    E04's andon, and it guards a failure with no technical symptom at all. Every other
    gate in this tool passes on a seed-shopped run: the frame is legal, the batch is
    intact, the topology verifies, the lossless tap is wired. The output is a perfectly
    well-formed generation. What is wrong is *epistemic* — a seed chosen after seeing a
    result turns a measurement of the between-generation floor into a selection of it,
    and the resulting number would be quoted forever as the denominator every later arm
    comparison is read against.

    **Why a committed list rather than a rule against seed-shopping.** A rule forbids;
    a list removes the possibility. The seeds are written into the spec in the commit
    that opens the experiment, before the first submission, so git timestamps the
    registration ahead of every artifact it governs.

    **The andon is on the direction the invariant does not bound.** Nothing else here
    looks at *which* seed is used — the seed was a module constant that no flag could
    move, so varying it at all is the new freedom, and this gate is what bounds it. It
    therefore binds in both directions: an experiment that pre-registered seeds must use
    one of them, and an experiment that pre-registered none may not vary its seed at all.
    """

    gate = "S"


class SpecError(ArmatureError):
    """The shot spec is malformed, incomplete, or names something unknown."""


class NotInsideBlender(ArmatureError):
    """The render backend was needed but bpy is not importable.

    Raised *after* the gates, never before — so a gate failure is always reported
    as a gate failure even when the tool is exercised outside Blender.
    """
