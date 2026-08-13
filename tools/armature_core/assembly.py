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


# --------------------------------------------------------------------------------
# The cascade — E13's re-arm, 2026-08-13
#
# S03 measured the flat chain above executing at 8 slots and failing at 81 with
# `BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'`. The cap
# is a runtime property of the node's signature: the catalog declares no maximum, and S03
# made no boundary-hunting submission, so **50 is INFERRED from one error message and is
# not a measured boundary.** Everything below treats it as the untrustworthy number it is.
#
# The cascade batches the batches: groups of `GROUP_SIZE`, then one batch over the groups.
# The invariant it needs is "no node carries more slots than the node signature accepts",
# and the direction that invariant does not bound is UPWARD — a group size edited larger,
# a frame count grown, an off-by-one in the last group. So the andon is a ceiling, and it
# is deliberately set well below the inferred cap rather than at it: a gate placed exactly
# on an inferred number inherits that number's uncertainty.

#: What one error message implies about `BatchImagesNode.execute()`'s arity: it named
#: `images.image50` as unexpected and 8 slots execute, so image0..image49 is the reading.
#: INFERRED, never measured — no submission was made at 49, 50 or 51 slots.
INFERRED_SLOT_CAP = 50

#: The ceiling the cascade actually builds to. Well under INFERRED_SLOT_CAP on purpose:
#: the cap is one error message's implication, and a design that sits on it is a design
#: that fails if the implication is off by one.
GROUP_SIZE = 27

#: The gate's ceiling. Equal to GROUP_SIZE, so any widening of the group is a deliberate
#: diff in both places rather than a number quietly growing toward a cap nobody measured.
MAX_SLOTS_PER_NODE = GROUP_SIZE


def cascade_plan(n, group_size=GROUP_SIZE):
    """Contiguous, ascending, exhaustive frame ranges — one per group node.

    Returns a list of `(start, stop)` half-open ranges. Contiguity and ascent are the
    whole point: the frames are a clip, and a cascade is exactly where an ordering bug
    hides while every count still reads correctly.
    """
    n, group_size = int(n), int(group_size)
    if group_size < 1:
        raise AssemblyGate("group size must be at least 1", {"group_size": group_size})
    return [(s, min(s + group_size, n)) for s in range(0, n, group_size)]


def gate_slot_ceiling(graph, cap=MAX_SLOTS_PER_NODE):
    """Gate CASCADE · ANDON — no batch node carries more auto-grow slots than the ceiling.

    This is the andon on the direction the invariant does not bound. S03's 81-slot graph
    passed the round trip, passed Gate ROUTE, and passed pre-flight with zero warnings —
    and then failed at execution. Pre-flight cannot see this, so it is checked here, before
    a submission, in the tool that builds the graph.
    """
    ev = {"gate": "CASCADE", "cap": int(cap), "per_node": {}}
    over = []
    for nid, node in graph.items():
        if node.get("class_type") != "BatchImagesNode":
            continue
        k = len([key for key in node.get("inputs", {}) if key.startswith("images.image")])
        ev["per_node"][nid] = k
        if k > cap:
            over.append((nid, k))
    if over:
        ev["over"] = over
        raise AssemblyGate(
            f"batch node(s) {over} carry more than {cap} auto-grow slot(s). The runtime cap "
            f"is INFERRED at {INFERRED_SLOT_CAP} from a single error message and was never "
            f"measured at its boundary; a graph built above this ceiling is a graph whose "
            f"execution depends on that inference being exact", ev)
    ev["verdict"] = (f"{len(ev['per_node'])} batch node(s), largest carries "
                     f"{max(ev['per_node'].values(), default=0)} slot(s), ceiling {cap}")
    return ev


def gate_cascade_topology(graph, n_frames, group_ids, final_id, video_id, save_id,
                          group_size=GROUP_SIZE):
    """Gate CASCADE · ANDON — every frame reaches the video exactly once, in order.

    The flat gate above cannot describe this shape, and the failures it would miss are the
    ones a cascade adds:

    * a group dropped from the final batch — 54 frames instead of 81, no error anywhere;
    * groups wired to the final batch out of order — 81 frames, correct count, shuffled clip;
    * a frame in two groups and another in none — count right, clip wrong;
    * the final batch fed by a group's LoadImage rather than the group — silently short.
    """
    n = int(n_frames)
    plan = cascade_plan(n, group_size)
    ev = {"gate": "CASCADE", "n_frames": n, "group_size": int(group_size),
          "n_groups": len(plan), "group_nodes": [str(g) for g in group_ids],
          "final_node": str(final_id), "video_node": str(video_id),
          "save_node": str(save_id), "plan": [list(p) for p in plan]}
    problems = []

    if len(group_ids) != len(plan):
        raise AssemblyGate(
            f"{len(group_ids)} group node(s) for a plan that needs {len(plan)}", ev)

    # ---- each group: dotted keys, contiguous slot names, distinct LoadImage sources.
    seen_sources, per_group = [], []
    for (start, stop), gid in zip(plan, group_ids):
        g = graph.get(str(gid))
        if g is None or g.get("class_type") != "BatchImagesNode":
            problems.append(f"group node {gid} is not a BatchImagesNode")
            per_group.append([])
            continue
        gi = g["inputs"]
        want = batch_slot_keys(stop - start)
        if "images" in gi:
            problems.append(f"group {gid} uses a bare `images` list; dry_run does NOT catch "
                            f"this (measured, E02)")
        if sorted(gi) != sorted(want):
            problems.append(f"group {gid} has {len(gi)} slot(s), expected {stop - start} "
                            f"named images.image0..images.image{stop - start - 1}")
        srcs = [gi[k][0] for k in want if isinstance(gi.get(k), list) and len(gi[k]) == 2]
        per_group.append(srcs)
        seen_sources.extend(srcs)
        for src in srcs:
            node = graph.get(str(src))
            if node is None:
                problems.append(f"group {gid} names missing node {src}")
            elif node.get("class_type") != "LoadImage":
                problems.append(f"group {gid} names {node.get('class_type')} node {src}, "
                                f"not a LoadImage")

    ev["n_sources"] = len(seen_sources)
    ev["n_distinct_sources"] = len(set(seen_sources))
    if len(seen_sources) != n:
        problems.append(f"the groups carry {len(seen_sources)} frame slot(s) for {n} frames")
    elif len(set(seen_sources)) != n:
        problems.append(f"the groups' {len(seen_sources)} slot(s) name only "
                        f"{len(set(seen_sources))} distinct LoadImage node(s): a frame is "
                        f"duplicated and another is missing while the count reads right")

    # ---- the final batch: one slot per group, IN GROUP ORDER.
    final = graph.get(str(final_id))
    if final is None or final.get("class_type") != "BatchImagesNode":
        problems.append(f"node {final_id} is not a BatchImagesNode")
    else:
        fi = final["inputs"]
        want = batch_slot_keys(len(plan))
        if sorted(fi) != sorted(want):
            problems.append(f"the final batch has {len(fi)} slot(s), expected {len(plan)}")
        else:
            got = [fi[k] for k in want]
            expect = [[str(g), 0] for g in group_ids]
            ev["final_links"] = got
            if got != expect:
                problems.append(
                    f"the final batch's slots are {got!r}, not the group nodes in order "
                    f"{expect!r} — the clip's frames would be assembled out of sequence "
                    f"while every count still read right")

    video = graph.get(str(video_id))
    if video is None or video.get("class_type") != "CreateVideo":
        problems.append(f"node {video_id} is not a CreateVideo")
    elif video["inputs"].get("images") != [str(final_id), 0]:
        problems.append(
            f"CreateVideo.images is {video['inputs'].get('images')!r}, not the FINAL batch's "
            f"output — the video would carry one group instead of the clip")

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

    ev["verdict"] = (f"{n} distinct LoadImage nodes -> {len(plan)} group batch(es) of at "
                     f"most {group_size} -> final batch -> CreateVideo -> SaveVideo, "
                     f"dotted slot keys, groups in frame order, every link resolved")
    return ev
