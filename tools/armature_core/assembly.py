"""The assembly graph: frames in, one VIDEO out, and nothing that costs a partner credit.

No bpy. S03 Task C builds the chain the halt ruling (R2) proposed as the rescue for a route
whose video slot has no loader:

    uploaded PNG frames -> BatchImagesNode -> CreateVideo(fps) -> SaveVideo

Every node in it is `api_node: false` — re-measured with `get_node` 2026-08-13 — so it
executes as ordinary workflow compute and spends no partner credits. This module is where
that claim is made checkable instead of asserted.

--------------------------------------------------------------------------------
Why the class allowlist is the andon, and the name pattern is only its second clause

The halt this graph runs under is "any partner-credit estimate above 0". `estimate_credits`
is the empirical instrument for that and it is called before submission — but it is a
*remote* answer about a graph that has already been built, and the thing worth preventing is
building a graph that could cost anything at all.

The obvious check — refuse class names that look like API nodes — is weak, and it is worth
writing down why rather than shipping it as though it were strong. Comfy's paid classes are
not uniformly named: `Wan2ReferenceVideoApi` ends in `Api`, and plenty of partner nodes do
not end in anything in particular. A pattern check therefore has unknown recall, and a gate
with unknown recall reads as protection while providing an unknown amount of it.

So the binding clause is an **allowlist**: this graph may contain these four classes and
nothing else. That has perfect recall by construction — a partner node cannot be in the
allowlist without somebody putting it there in a diff — and it cannot be tuned by anyone who
does not like the result. The name pattern rides along as an independent second clause,
because the two fail differently: the allowlist catches an unexpected class, and the pattern
catches somebody widening the allowlist without reading what they widened it to.

--------------------------------------------------------------------------------
Why the batch topology gets its own gate

`GateBBatching` already exists for the quantity that moves when `BatchImagesNode`'s auto-grow
list mis-binds — but it is measured on the batch as SAVED OFF the node at run time, which
needs a submission. This one is structural and runs before any submission: `n` dotted slot
keys, each bound to a distinct `LoadImage`. E02 measured the failure mode it exists for and
CLAUDE.md records the receipt: a bare `images` list VALIDATED under `dry_run` with zero
warnings and was refused only by a real submission. A `dry_run` PASS does not prove link
sanity, so the link topology is checked in code.
"""

from .errors import GateFailure


class AssemblyGate(GateFailure):
    """The assembly graph is not the free, four-class chain it is supposed to be."""

    gate = "ASSEMBLY"


#: The only classes this graph may contain. Every one re-measured `api_node: false` with
#: `get_node` on 2026-08-13. Widening this list is a deliberate diff, which is the point.
ALLOWED_CLASSES = ("LoadImage", "BatchImagesNode", "CreateVideo", "SaveVideo")

#: Substrings that mark a class as a paid partner node. The WEAK clause — see the module
#: docstring: its recall is unknown, and it is here to catch a careless widening of the
#: allowlist, never to be the thing standing between this graph and a credit.
API_MARKERS = ("api", "partner")


def gate_no_paid_nodes(graph, allowed=ALLOWED_CLASSES):
    """Gate ASSEMBLY · ANDON — nothing in this graph can bill a partner credit.

    Two independent clauses. The allowlist binds; the name pattern is a second opinion on
    the allowlist itself. Reported either way, so the evidence shows both ran.
    """
    classes = sorted({n.get("class_type") for n in graph.values()})
    ev = {"gate": "ASSEMBLY", "classes": classes, "allowed": list(allowed),
          "n_nodes": len(graph)}

    unexpected = [c for c in classes if c not in allowed]
    if unexpected:
        raise AssemblyGate(
            f"the assembly graph contains {unexpected}, which the allowlist does not name. "
            "This chain is supposed to cost nothing, and the way that is guaranteed is by "
            "the graph containing only classes measured `api_node: false` — not by hoping "
            "an unfamiliar class is free", ev)

    flagged = [c for c in allowed if any(m in c.lower() for m in API_MARKERS)]
    ev["name_pattern_flagged"] = flagged
    if flagged:
        raise AssemblyGate(
            f"the allowlist itself names {flagged}, which reads as a partner/API class. "
            "The allowlist is the binding clause, so widening it is the moment to look — "
            "this is that look", ev)

    ev["verdict"] = (f"{len(graph)} node(s) across {len(classes)} class(es), all named by "
                     f"the allowlist and none reading as a partner class")
    return ev


def batch_slot_keys(n):
    """The dotted COMFY_AUTOGROW_V3 slot keys for an `n`-image batch."""
    return [f"images.image{i}" for i in range(int(n))]


def gate_batch_topology(graph, n_frames, batch_id, video_id, save_id):
    """Gate ASSEMBLY · ANDON — all `n_frames` reach the batch, and the chain is wired.

    The clauses, each for a failure that is silent in the others' presence:

    * a bare `images` list instead of dotted keys — `dry_run` VALIDATES it (E02, measured);
    * the wrong NUMBER of slots — a 40-frame batch produces a shorter video and nothing errs;
    * two slots bound to the SAME `LoadImage` — the count is right and a frame is doubled;
    * `CreateVideo` not fed by the batch, or `SaveVideo` not fed by `CreateVideo` — a graph
      that assembles something other than what was uploaded, or saves nothing.
    """
    n = int(n_frames)
    ev = {"gate": "ASSEMBLY", "n_frames": n, "batch_node": batch_id,
          "video_node": video_id, "save_node": save_id}
    problems = []

    batch = graph.get(str(batch_id))
    if batch is None or batch.get("class_type") != "BatchImagesNode":
        raise AssemblyGate(f"node {batch_id} is not a BatchImagesNode", ev)
    bi = batch["inputs"]
    ev["n_slot_keys"] = len(bi)

    if "images" in bi:
        problems.append(
            "the batch uses a bare `images` list; COMFY_AUTOGROW_V3 needs dotted "
            "`images.image<N>` keys, and dry_run does NOT catch this (measured, E02)")
    want = batch_slot_keys(n)
    if sorted(bi) != sorted(want):
        problems.append(
            f"batch slot keys are wrong: {len(bi)} key(s), expected {n} named "
            f"images.image0..images.image{n - 1}")
    sources = [v[0] for v in bi.values() if isinstance(v, list) and len(v) == 2]
    ev["distinct_sources"] = len(set(sources))
    if len(sources) != len(bi):
        problems.append("a batch slot is not bound to a link at all")
    elif len(set(sources)) != n:
        problems.append(
            f"the batch's {len(bi)} slot(s) name only {len(set(sources))} distinct "
            f"LoadImage node(s): a link is bound twice and a frame is duplicated while "
            f"the count still reads right")
    for src in sources:
        node = graph.get(str(src))
        if node is None:
            problems.append(f"batch slot names missing node {src}")
        elif node.get("class_type") != "LoadImage":
            problems.append(f"batch slot names {node.get('class_type')} node {src}, "
                            f"not a LoadImage")

    video = graph.get(str(video_id))
    if video is None or video.get("class_type") != "CreateVideo":
        problems.append(f"node {video_id} is not a CreateVideo")
    elif video["inputs"].get("images") != [str(batch_id), 0]:
        problems.append(
            f"CreateVideo.images is {video['inputs'].get('images')!r}, not the batch node's "
            f"output — the video would be assembled from something other than the frames "
            f"that were uploaded")

    save = graph.get(str(save_id))
    if save is None or save.get("class_type") != "SaveVideo":
        problems.append(f"node {save_id} is not a SaveVideo")
    elif save["inputs"].get("video") != [str(video_id), 0]:
        problems.append(
            f"SaveVideo.video is {save['inputs'].get('video')!r}, not CreateVideo's output; "
            f"CreateVideo is `output_node: false`, so nothing would be saved at all")

    if problems:
        ev["problems"] = problems
        raise AssemblyGate("; ".join(problems), ev)

    ev["verdict"] = (f"{n} distinct LoadImage nodes -> batch -> CreateVideo -> SaveVideo, "
                     f"dotted slot keys, every link resolved")
    return ev
