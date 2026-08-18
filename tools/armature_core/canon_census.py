"""Which subjects have a surfaces file, as DATA.

A subject absent from this table has no answer. A subject whose
``surfaces`` is None has identity and no file — the escape
``--no-canon --subject NAME`` is the only way a spend of that name
proceeds, and it announces itself. ``--no-canon`` on a subject that
HAS a surfaces path is refused: that is the checkbox trap facet
measured.

Adding a subject is a data change here. The file a path names is
loaded from the search roots ``canon.resolve`` is given; the default
root is ``tools/armature_core/canon/``.

No row here is a verdict that a figure is the right character.
"""

# surfaces: relative path under a search root, or None (identity-only).
# reason: why a None row is None — recorded so a hole is a row.
CENSUS = {
    "PERFORMER": {
        "surfaces": None,
        "reason": (
            "the live staged figure; identity exists; no ratified surfaces "
            "file. A Director ratifies occupants, this seat does not."
        ),
    },
    "BLACKGUARD": {
        "surfaces": None,
        "reason": (
            "E01/E02 armored warrior. Named in prompts (plate, helm, cloak) "
            "but no surfaces file has been ratified."
        ),
    },
    "WIRE": {
        "surfaces": None,
        "reason": (
            "E03 procedural wire figure. The E03 prompt names no material "
            "and no costume on purpose."
        ),
    },
}


def row(subject, census=None):
    """The census row for `subject`, or None if the name is unknown."""
    table = CENSUS if census is None else census
    return table.get(subject)
