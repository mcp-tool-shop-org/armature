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

from .errors import ArmatureError


class SiteListError(ArmatureError):
    """The registration is internally inconsistent — the andon on the registration itself.

    A deliberate refusal, and it used to be a bare `ValueError` (F-9fab7829, wave 12). The
    docstring on `validate` already said "Raises ValueError, never asserts": the intent was
    a refusal, only the class was wrong.

    **The caller population, as the tree actually has it** (F-69733981, corrected in place
    2026-09-04). This read "called by three production Blender tools
    (`tools/rig_character.py:1135`, `tools/rig_parts.py:480`,
    `tools/project_pose_keypoints.py:229`)". Re-derived by grep: `validate()` has TWO direct
    callers — `tools/rig_character.py::validate_sitelist` and
    `tools/project_pose_keypoints.py::main` — and ONE indirect, `tools/rig_parts.py::main`,
    which calls `rig_character.validate_sitelist()` and reaches this refusal through it.
    Two direct and one through the wrapper, then — the re-classing argument below is
    unaffected and reads stronger for being the tree's own count.

    **The correction's own citation went stale, and this is the second correction**
    (F-b3ff3a57, wave 22). The paragraph above used to end "Of the three line numbers, only
    `project_pose_keypoints.py:229` was right; the other two landed on a docstring line and
    on a `np.linalg.norm` call". MEASURED on `e8263a3`: `tools/project_pose_keypoints.py:229`
    is now the middle of a `ProjectGate` refusal message (`'span_stats was given no frames;
    a min/median/max over an empty keypoint '`), and `grep -n validate
    tools/project_pose_keypoints.py` returns exactly one line — `sitelist.validate()`, and
    not that one. The wave-16 constructor deletions moved it, so the wave-15 correction that
    quoted it as the surviving-correct citation is itself now wrong. A session sent to that
    line to re-derive the caller population opens an unrelated refusal string, cannot confirm
    the count, and either re-files the finding this paragraph was written to close or
    distrusts the paragraph entirely.

    **So the citations are on the SYMBOL and the line numbers are gone.** That is the general
    form, and it is the same fix `lift_solve.py`'s three `lift_clip.py` citations take in
    this wave: a line citation does not survive an edit above it, a symbol does, and prose
    that cites functions needs no census to keep it true. A CENSUS over all 17
    `<file>.py:<line>` prose citations in this domain's 21 modules resolved 14 to a non-blank
    line and found 3 pointing at blank lines — all three of which the surrounding prose
    already names as blank and re-anchors on the symbol, so the correction discipline held
    everywhere except here, on the one line whose own purpose was to correct a stale
    citation.

    The 21-tool halt contract classifies on the
    `ArmatureError` family, so measured 2026-09-04 by driving that classifier with the
    exception `validate()` raises on a duplicated registration: ('FAILED - an unhandled
    error', exit 1, gate None, evidence None). The tool wrote a halt record asserting an
    unhandled error in the rigging code when what happened is the registration refusing to
    proceed — the false-record class arriving from the other direction, and an executor
    reading it goes looking for a bug in the rigging routine instead of at the site list
    and its E07 registration document disagreeing.

    Carries an `evidence` dict; a plain refusal writes `gate: None` + `andon` + `clause`.

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
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

#: Optional articulated hand chain (F-f821776d). Not in default `BONES` — mitten wrists
#: remain the registered product — but available when a subject carries finger deform
#: bones. validate() does not walk this table; `bones_for(hand_mode=...)` does.
HAND_CHAIN = (
    Bone("thumb.L",  "wrist.L", "wrist_L",  "thumb_L",  True, False),
    Bone("index.L",  "wrist.L", "wrist_L",  "index_L",  True, False),
    Bone("middle.L", "wrist.L", "wrist_L",  "middle_L", True, False),
    Bone("ring.L",   "wrist.L", "wrist_L",  "ring_L",   True, False),
    Bone("pinky.L",  "wrist.L", "wrist_L",  "pinky_L",  True, False),
    Bone("thumb.R",  "wrist.R", "wrist_R",  "thumb_R",  True, False),
    Bone("index.R",  "wrist.R", "wrist_R",  "index_R",  True, False),
    Bone("middle.R", "wrist.R", "wrist_R",  "middle_R", True, False),
    Bone("ring.R",   "wrist.R", "wrist_R",  "ring_R",   True, False),
    Bone("pinky.R",  "wrist.R", "wrist_R",  "pinky_R",  True, False),
)

HAND_MODES = ("mitten", "articulated")


def bones_for(hand_mode="mitten"):
    """Registered bones, optionally extended with the articulated hand chain."""
    if hand_mode not in HAND_MODES:
        raise SiteListError(
            f"hand_mode={hand_mode!r} is not one of {list(HAND_MODES)}",
            {"gate": None, "andon": "SiteListError", "clause": "unknown_hand_mode",
             "hand_mode": hand_mode, "known": list(HAND_MODES)})
    if hand_mode == "mitten":
        return BONES
    return BONES + HAND_CHAIN


def hand_chain_names():
    return tuple(b.name for b in HAND_CHAIN)

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
    """Internal consistency of the registration itself. Raises `SiteListError`, never asserts.

    See `SiteListError` for why the class is not `ValueError` any more.
    """
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
        raise SiteListError(
            f"the registered site list is internally inconsistent over {len(BONES)} "
            f"registered bone(s) and {len(E01_SITES)} E01 site(s): " + "; ".join(problems),
            {"gate": None, "andon": "SiteListError",
             "clause": "registration_inconsistent",
             "problems": problems, "n_bones": len(BONES),
             "n_e01_sites": len(E01_SITES)})
    return True
