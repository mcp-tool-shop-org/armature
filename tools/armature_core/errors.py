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


class GateNNames(GateFailure):
    """The rig that was about to ship does not name every registered site. E07's andon.

    **The invariant unbounded elsewhere: nothing else prevents a half-named rig from
    shipping.** E01 measured the whole problem — four rigged GLBs on this machine, every
    one of them naming its bones `bone_0 … bone_N`, zero of 18 anatomical sites findable
    in any of them. Not one of those files reports anything wrong. They import, they
    carry a skin, they pose. The defect is entirely in the names, and a name is exactly
    the kind of thing every other check is blind to: rest-pose fidelity is unaffected by
    what a bone is called, determinism reproduces a wrong name perfectly, and a render
    looks identical. A rig that skins beautifully and names nothing is E01's result
    reproduced with more steps.

    **It binds in both directions.** A missing site is the obvious clause. An
    *unregistered* bone is the second, and it is the one that is easy to miss: the site
    list is committed before the first bone precisely so the rig cannot acquire a bone
    that no list registered, and a gate checking only coverage would have left that door
    open itself.

    **It is checked on the re-imported export, not only on the in-memory armature.**
    The names that matter are the ones a downstream consumer reads out of the GLB. An
    in-memory armature naming all 22 bones proves nothing about what the glTF exporter
    wrote — `export_def_bones` alone would silently drop every non-deforming marker.
    """

    gate = "N"


class GatePRestPose(GateFailure):
    """Skinning is not the identity at the bind pose. E07's andon on silent collapse.

    Linear-blend skinning evaluated at the rest pose is the identity map *when the
    weights on each vertex sum to 1* — every bone contributes its own rest matrix, and
    the weighted sum reduces to the vertex's original position no matter what the
    weights are. So this gate does not test whether the weighting is any good. It tests
    the one thing that must hold regardless: that binding the mesh did not move it.

    **What it catches that nothing else does.** A partially failed bone-heat solve
    leaves vertices whose weights sum to less than 1; those vertices contract toward
    the origin the instant the modifier is live, and a vertex weighted to nothing at all
    may collapse to the object origin outright. Blender reports bone-heat failure as an
    *info message*, not an error. The export succeeds, the manifest is written, the
    names all check out, determinism reproduces the collapse exactly — and the character
    ships with a dent in him that no other check in this tool can see.

    Bounded by the mesh's own bbox diagonal rather than by a constant in metres, because
    a global constant must not govern a local feature.
    """

    gate = "P"


class GateDDeterminism(GateFailure):
    """Two builds from identical inputs produced different rigs. E07's andon on recipe.

    *A recipe that does not reproduce its output is not a recipe.* Everything downstream
    of this tool — E08's authored performance, every control sequence rendered from it,
    every comparison drawn against those — is quoted against a rig. If the rig is not
    reproducible then none of those numbers has a fixed referent, and the failure is
    silent in every direction: one run is as plausible as another, and the difference
    only ever surfaces as an unexplained shift in a later experiment.

    **Compared as parsed objects, never bytes.** A GLB carries timestamps, exporter
    version strings and float noise that differ between byte-identical *rigs*; a hash
    mismatch would therefore fire on runs that are the same and, worse, a hash *match*
    would be quoted as proof of a property it never tested. This gate compares bone
    heads, tails, rolls, parents, deform flags and per-vertex weight vectors — the
    quantities that are actually the contract.
    """

    gate = "D"


class SpecError(ArmatureError):
    """The shot spec is malformed, incomplete, or names something unknown."""


class LandmarkError(ArmatureError):
    """The mesh does not present the anatomy the landmark derivation requires.

    Raised rather than guessed. A silhouette that does not resolve into a trunk, two
    arms and two legs is a subject this derivation cannot place bones on, and placing
    them anyway would produce a rig whose joints are in invented positions while every
    gate downstream reports green — the names would check out, the rest pose would be
    preserved, and the build would be perfectly deterministic. Halting is the only
    signal that survives.
    """


class NotInsideBlender(ArmatureError):
    """The render backend was needed but bpy is not importable.

    Raised *after* the gates, never before — so a gate failure is always reported
    as a gate failure even when the tool is exercised outside Blender.
    """
