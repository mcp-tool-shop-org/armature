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


class GateRRoundTrip(GateFailure):
    """The encoded control video did not decode back to the frames that went in.

    E02's andon on the upload bridge. It exists for a failure that is silent by
    construction: `-qp 0` is *luma*-lossless while x264 still defaults to `yuv420p`,
    which subsamples chroma 4:1. A grayscale channel (R=G=B) survives that untouched,
    so the corruption would appear only in the true-RGB normal channel — and the
    video would look correct either way.
    """

    gate = "R"


class SpecError(ArmatureError):
    """The shot spec is malformed, incomplete, or names something unknown."""


class NotInsideBlender(ArmatureError):
    """The render backend was needed but bpy is not importable.

    Raised *after* the gates, never before — so a gate failure is always reported
    as a gate failure even when the tool is exercised outside Blender.
    """
