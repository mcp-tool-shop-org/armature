"""The registered site list, as DATA. No bpy, no numpy — importable anywhere.

Committed in `docs/experiments/E07-site-list.md` before the first bone was placed, and
this module is that document in machine-readable form. Adding a bone is a data change
here **and** an amendment there; the two must agree, and `tests/test_sitelist.py` is what
makes disagreement fail rather than drift.

**Why the list is data and not code.** A site list assembled inside the rigging routine
could be extended by whatever the rigging routine found convenient — which is exactly the
name-shopping the registration exists to prevent. Kept out here it can be diffed, and the
git timestamp on the registration precedes every artifact the list governs.

**The site→bone rule, fixed in the registration and restated here because Gate N enforces
it:** a site is satisfied by exactly one bone bearing that site's name, whose HEAD is
placed at that anatomical location. E01's 18 are keypoints — joint *locations*; a bone is
a segment. The two are different objects and the mapping between them is this rule.
"""

#: The 18 sites `tools/probe_glb.py::SITES` enumerates — the list every `0 / 18` in E01's
#: report was computed against, and the gap E07 exists to close.
E01_SITES = (
    "nose", "neck",
    "shoulder.L", "shoulder.R", "elbow.L", "elbow.R", "wrist.L", "wrist.R",
    "hip.L", "hip.R", "knee.L", "knee.R", "ankle.L", "ankle.R",
    "eye.L", "eye.R", "ear.L", "ear.R",
)

#: Bones E01's keypoint list does not name and a deforming rig cannot omit: those 18
#: contain no torso chain and no skull, so a rig built from them alone would leave every
#: vertex between the hips and the neck belonging to no bone at all.
STRUCTURAL = ("hips", "spine", "chest", "head")


class Bone:
    """One registered bone: its name, its parent, and the landmarks its ends sit on."""

    __slots__ = ("name", "parent", "head", "tail", "deform", "site")

    def __init__(self, name, parent, head, tail, deform, site):
        self.name = name
        self.parent = parent
        self.head = head
        self.tail = tail
        self.deform = deform
        self.site = site

    def as_dict(self):
        return {"name": self.name, "parent": self.parent, "head_landmark": self.head,
                "tail_landmark": self.tail, "use_deform": self.deform,
                "registered_as": "E01_SITE" if self.site else "STRUCTURAL"}


#: Parents precede children — the build walks this in order and never looks ahead.
BONES = (
    Bone("hips",       None,        "crotch",      "spine_base",  True,  False),
    Bone("spine",      "hips",      "spine_base",  "chest_base",  True,  False),
    Bone("chest",      "spine",     "chest_base",  "neck_base",   True,  False),
    Bone("neck",       "chest",     "neck_base",   "head_base",   True,  True),
    Bone("head",       "neck",      "head_base",   "head_top",    True,  False),

    # The five facial markers. use_deform is FALSE by registration: they name the sites
    # E01's instrument looks for without authoring any facial deformation, which is what
    # the spec puts out of scope. No vertex is weighted to any of them.
    Bone("nose",       "head",      "nose",        "nose_tip",    False, True),
    Bone("eye.L",      "head",      "eye_L",       "eye_L_tip",   False, True),
    Bone("eye.R",      "head",      "eye_R",       "eye_R_tip",   False, True),
    Bone("ear.L",      "head",      "ear_L",       "ear_L_tip",   False, True),
    Bone("ear.R",      "head",      "ear_R",       "ear_R_tip",   False, True),

    Bone("shoulder.L", "chest",     "shoulder_L",  "elbow_L",     True,  True),
    Bone("elbow.L",    "shoulder.L", "elbow_L",    "wrist_L",     True,  True),
    Bone("wrist.L",    "elbow.L",   "wrist_L",     "hand_end_L",  True,  True),
    Bone("shoulder.R", "chest",     "shoulder_R",  "elbow_R",     True,  True),
    Bone("elbow.R",    "shoulder.R", "elbow_R",    "wrist_R",     True,  True),
    Bone("wrist.R",    "elbow.R",   "wrist_R",     "hand_end_R",  True,  True),

    Bone("hip.L",      "hips",      "hip_L",       "knee_L",      True,  True),
    Bone("knee.L",     "hip.L",     "knee_L",      "ankle_L",     True,  True),
    Bone("ankle.L",    "knee.L",    "ankle_L",     "toe_L",       True,  True),
    Bone("hip.R",      "hips",      "hip_R",       "knee_R",      True,  True),
    Bone("knee.R",     "hip.R",     "knee_R",      "ankle_R",     True,  True),
    Bone("ankle.R",    "knee.R",    "ankle_R",     "toe_R",       True,  True),
)

#: Every name the rig is registered to carry. Gate N binds on this set in both directions.
ALL_NAMES = tuple(b.name for b in BONES)

#: The bone that drives the E03 probe arc. E03's `arm_r_raise` rotates the arm on the
#: **+X side** about +Y — its own docstring says so: "the arm named _r in the generator
#: (the +X side)". On the wire subject `_r` was a label on a planar T-pose, not anatomy.
#: Which of this character's arms sits on +X is a MEASURED property of this mesh
#: (`landmarks.facing`), so the probe binds to the +X side and the report names which arm
#: that turned out to be, rather than assuming the letter carried over.
PROBE_ARC_SIDE_X_SIGN = 1.0


def by_name():
    return {b.name: b for b in BONES}


def validate():
    """Internal consistency of the registration itself. Raises ValueError, never asserts."""
    problems = []
    seen = []
    for b in BONES:
        if b.name in seen:
            problems.append(f"duplicate bone name {b.name!r}")
        if b.parent is not None and b.parent not in seen:
            problems.append(
                f"{b.name!r} names parent {b.parent!r} which does not precede it; the "
                f"build walks BONES in order and never looks ahead"
            )
        seen.append(b.name)
        if b.head == b.tail:
            problems.append(f"{b.name!r} has head and tail on the same landmark {b.head!r}")

    missing_sites = [s for s in E01_SITES if s not in seen]
    if missing_sites:
        problems.append(f"registered E01 sites with no bone: {missing_sites}")
    extra = [n for n in seen if n not in E01_SITES and n not in STRUCTURAL]
    if extra:
        problems.append(f"bones registered under neither E01_SITES nor STRUCTURAL: {extra}")
    site_flagged = sorted(b.name for b in BONES if b.site)
    if site_flagged != sorted(E01_SITES):
        problems.append(
            f"the `site` flags disagree with E01_SITES: flagged {site_flagged}, "
            f"E01_SITES {sorted(E01_SITES)}"
        )
    if len(E01_SITES) != 18:
        problems.append(f"E01_SITES holds {len(E01_SITES)} entries, not the 18 E01 counted")

    if problems:
        raise ValueError("the registered site list is internally inconsistent: "
                         + "; ".join(problems))
    return True
