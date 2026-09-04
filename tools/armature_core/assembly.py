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


class CascadeGate(AssemblyGate):
    """Gate CASCADE — the cascade's own andons, under the id the receipt already used.

    F-fb4fc1c0: `gate_slot_ceiling` and `gate_cascade_topology` both set
    `ev["gate"] = "CASCADE"` and both raised `AssemblyGate`, whose class attribute is
    `gate = "ASSEMBLY"`. Measured 2026-09-04: `gate_slot_ceiling({}, cap=99)` raised with
    `.gate == "ASSEMBLY"`, `evidence["gate"] == "CASCADE"`, and `str(exc)` beginning
    `[ASSEMBLY]`. `stage_render.py` prints `exc.gate`, and the builders key the same
    evidence as `CASCADE_ceiling` / `CASCADE_topology`, so the record disagreed with
    itself about which andon pulled. Subclassing keeps every existing
    `except AssemblyGate` / `pytest.raises(AssemblyGate)` site catching these.
    """

    gate = "CASCADE"


#: The only classes this graph may contain. Every one re-measured `api_node: false` with
#: `get_node` on 2026-08-13. Widening this list is a deliberate diff, which is the point.
ALLOWED_CLASSES = ("LoadImage", "BatchImagesNode", "CreateVideo", "SaveVideo")

#: Substrings that mark a class as a paid partner node. The WEAK clause — see the module
#: docstring: its recall is unknown, and it is here to catch a careless widening of the
#: allowlist, never to be the thing standing between this graph and a credit.
API_MARKERS = ("api", "partner")


def gate_no_paid_nodes(graph, allowed=ALLOWED_CLASSES):
    """Gate ASSEMBLY - ANDON - nothing in this graph can bill a partner credit.

    Two independent clauses. The allowlist binds; the name pattern is a second opinion on
    the allowlist itself. Reported either way, so the evidence shows both ran.

    A node carrying **no** `class_type` is refused before anything is sorted. It used to
    contribute `None` to the class set, and `sorted()` then raised `TypeError: '<' not
    supported between instances of 'str' and 'NoneType'` - so the failure path was broken
    in exactly one class of malformed graph, and the caller got an untyped error with no
    gate id and no evidence where the andon belonged. `parts.py:155-159` records the
    identical defect being caught by its own test.
    """
    unnamed = sorted(str(nid) for nid, n in graph.items() if n.get("class_type") is None)
    classes = sorted(c for c in {n.get("class_type") for n in graph.values()}
                     if c is not None)
    ev = {"gate": "ASSEMBLY", "andon": "AssemblyGate",
          "classes": classes, "allowed": list(allowed),
          "n_nodes": len(graph), "nodes_without_class_type": unnamed}

    if unnamed:
        raise AssemblyGate(
            f"node(s) {unnamed} carry no `class_type`, so what they would execute is "
            f"unknown and the allowlist cannot name them. A graph this gate cannot read is "
            f"not a graph this gate can clear", ev)

    unexpected = [c for c in classes if c not in allowed]
    if unexpected:
        raise AssemblyGate(
            f"the assembly graph contains {unexpected}, which the allowlist does not name. "
            "This chain is supposed to cost nothing, and the way that is guaranteed is by "
            "the graph containing only classes measured `api_node: false` - not by hoping "
            "an unfamiliar class is free", ev)

    flagged = [c for c in allowed if any(m in c.lower() for m in API_MARKERS)]
    ev["name_pattern_flagged"] = flagged
    if flagged:
        raise AssemblyGate(
            f"the allowlist itself names {flagged}, which reads as a partner/API class. "
            "The allowlist is the binding clause, so widening it is the moment to look - "
            "this is that look", ev)

    ev["verdict"] = (f"{len(graph)} node(s) across {len(classes)} class(es), all named by "
                     f"the allowlist and none reading as a partner class")
    return ev


def batch_slot_keys(n):
    """The dotted COMFY_AUTOGROW_V3 slot keys for an `n`-image batch."""
    return [f"images.image{i}" for i in range(int(n))]


def _link(v):
    """A `[node_id, output_index]` link with its node id normalised to `str`, else None.

    Node ids arrive as `str` from a builder and as whatever a hand-written fixture used, so
    a raw `==` between two links can differ on type alone and report an ordering fault that
    is not one.
    """
    if isinstance(v, list) and len(v) == 2:
        return [str(v[0]), v[1]]
    return None


def _links_equal(got, want):
    """Do two links name the same node and output slot? Type-normalised, like `_link`.

    F-527b4284. `_link` exists precisely because "a raw `==` between two links can differ
    on type alone and report an ordering fault that is not one", and two of the seven link
    comparisons in this module went through it while five compared raw file values against
    `[str(x), 0]`. Measured on a 2-frame, group-size-1 cascade: with string node ids inside
    the links `gate_cascade_topology` PASSES; with the identical topology whose links carry
    INTEGER node ids it raises "the final batch's slots are [[10, 0], [11, 0]], not the
    group nodes in order [['10', 0], ['11', 0]] - the clip's frames would be assembled out
    of sequence", while the per-group slots (which do go through `_link`) pass on the same
    input. The direction is a false REFUSAL, so nothing is submitted wrong; the cost is a
    halt whose message misdescribes the graph, on the andon a builder is meant to trust
    before spending credits. All seven comparisons now read the same way.

    A missing or malformed link normalises to None and therefore never compares equal,
    which is the behaviour the raw `!=` already had for those cases.
    """
    a = _link(got)
    return a is not None and a == _link(want)


def gate_batch_topology(graph, n_frames, batch_id, video_id, save_id, *, expected_sources):
    """Gate ASSEMBLY - ANDON - all `n_frames` reach the batch in order, and it is wired.

    The clauses, each for a failure that is silent in the others' presence:

    * a bare `images` list instead of dotted keys - `dry_run` VALIDATES it (E02, measured);
    * the wrong NUMBER of slots - a 40-frame batch produces a shorter video and nothing errs;
    * two slots bound to the SAME `LoadImage` - the count is right and a frame is doubled;
    * a slot bound to the WRONG frame - the count is right, every source is distinct, and
      the clip plays in an order nobody chose. `expected_sources` is the caller's own
      per-frame `LoadImage` node ids IN FRAME ORDER and is **required**: measured
      2026-09-03, permuting slots 2 and 6 of an 8-frame batch passed with a full verdict,
      because sources were collected in slot order and then only tested for length and
      distinctness;
    * `CreateVideo` not fed by the batch, or `SaveVideo` not fed by `CreateVideo` - a graph
      that assembles something other than what was uploaded, or saves nothing.
    """
    n = int(n_frames)
    exp = [str(s) for s in expected_sources]
    ev = {"gate": "ASSEMBLY", "andon": "AssemblyGate",
          "n_frames": n, "batch_node": batch_id,
          "video_node": video_id, "save_node": save_id, "n_expected_sources": len(exp)}
    problems = []

    if n < 1:
        raise AssemblyGate(
            f"the batch was gated over {n} frame(s): every count clause would compare 0 to "
            f"0 and the verdict would report a wired chain over an empty clip. A comparison "
            f"over nothing must not report agreement", ev)
    if len(exp) != n:
        raise AssemblyGate(
            f"{len(exp)} expected per-frame source id(s) against {n} frame(s); the gate "
            f"cannot relate slot k to frame k on a list that is not the frame list", ev)
    if len(set(exp)) != len(exp):
        raise AssemblyGate(
            f"the {len(exp)} expected per-frame source id(s) are not distinct, so the "
            f"expectation itself already carries a duplicated frame", ev)

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
    else:
        got = [_link(bi[k]) for k in want]
        expect = [[e, 0] for e in exp]
        ev["slot_links"] = got
        if got != expect:
            bad = [j for j in range(n) if got[j] != expect[j]]
            j = bad[0]
            problems.append(
                f"batch slot images.image{j} is bound to {got[j]!r}, not frame {j}'s "
                f"LoadImage {expect[j]!r} ({len(bad)} slot(s) differ): the clip would play "
                f"its frames out of sequence while the count and the distinct-source "
                f"clause both still read right")
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
    elif not _links_equal(video["inputs"].get("images"), [str(batch_id), 0]):
        problems.append(
            f"CreateVideo.images is {video['inputs'].get('images')!r}, not the batch "
            f"node's output - the video would be assembled from something other than the "
            f"frames that were uploaded")

    save = graph.get(str(save_id))
    if save is None or save.get("class_type") != "SaveVideo":
        problems.append(f"node {save_id} is not a SaveVideo")
    elif not _links_equal(save["inputs"].get("video"), [str(video_id), 0]):
        problems.append(
            f"SaveVideo.video is {save['inputs'].get('video')!r}, not CreateVideo's "
            f"output; CreateVideo is `output_node: false`, so nothing would be saved at all")

    if problems:
        ev["problems"] = problems
        raise AssemblyGate("; ".join(problems), ev)

    ev["verdict"] = (f"{n} distinct LoadImage nodes -> batch -> CreateVideo -> SaveVideo, "
                     f"dotted slot keys, slot k bound to frame k, every link resolved")
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
        raise CascadeGate("group size must be at least 1",
                          {"gate": "CASCADE", "andon": "CascadeGate",
                           "group_size": group_size})
    return [(s, min(s + group_size, n)) for s in range(0, n, group_size)]


def _bare_images_arity(inputs):
    """How many images a bare `images` key carries, or None when there is no bare key.

    E02's shape is `{"images": [[node, 0], [node, 0], ...]}` — a LIST of links where the
    dotted `images.imageN` keys belong. `gate_batch_topology` and `gate_cascade_topology`
    refuse it outright on the nodes they are handed by name; `gate_slot_ceiling` walks the
    WHOLE graph and so is the only check that sees a batch node neither of them names.
    Counting only `images.image*` keys made such a node contribute ZERO slots (F-0f585645,
    measured 2026-09-04: an 81-link bare-`images` node passed with `per_node {"400": 0}`).

    A single link is `[node_id, slot]` — two scalars — and carries one image. A list of
    links carries one image per element.
    """
    if "images" not in inputs:
        return None
    value = inputs["images"]
    if not isinstance(value, list):
        return 1
    if value and all(isinstance(v, (list, tuple)) for v in value):
        return len(value)
    return 1 if value else 0


def gate_slot_ceiling(graph, group_size=None, cap=None):
    """Gate CASCADE - ANDON - no batch node carries more auto-grow slots than the ceiling.

    This is the andon on the direction the invariant does not bound. S03's 81-slot graph
    passed the round trip, passed Gate ROUTE, and passed pre-flight with zero warnings -
    and then failed at execution. Pre-flight cannot see this, so it is checked here, before
    a submission, in the tool that builds the graph.

    **The ceiling belongs to this module, not to the caller.** The signature was
    `cap=MAX_SLOTS_PER_NODE` and both production builders passed `cap=max(--group, 1)`, so
    the same number that widened the graph widened the ceiling with it and the gate could
    never see the widening: measured 2026-09-03, `--group 81` builds the byte-for-byte
    graph S03 watched pass pre-flight and die at execution, and it PASSED with the verdict
    "largest carries 81 slot(s), ceiling 81". A caller-supplied bound on a caller-supplied
    quantity is the shape `gates.py`'s own docstring rules out - "a skip flag wearing a
    schema's clothes".

    So `group_size` is the caller's DECLARED group size, checked AGAINST this module's
    constant, and `cap` may only TIGHTEN: asking for a ceiling above `MAX_SLOTS_PER_NODE`
    raises, which is what the module docstring already claimed happened.

    **What the ceiling counts, and refusing to count nothing** (F-0f585645, measured
    2026-09-04). The per-node count was `len([k for k in inputs if k.startswith(
    "images.image")])`, so a BatchImagesNode carrying the E02 bare-`images` list
    contributed ZERO: a graph whose single batch node held 81 links passed with
    `per_node {"400": 0}` and the verdict "1 batch node(s), largest carries 0 slot(s),
    ceiling 27". The topology gates do refuse a bare list, but only on the group and final
    nodes they are handed BY NAME, while this gate is the one that walks the whole graph —
    so any other batch node was covered by nothing. A bare `images` list is now counted at
    its real arity (`_bare_images_arity`). Measured separately: a graph with no batch node
    at all passed with "0 batch node(s), largest carries 0 slot(s)", so the empty
    population is now refused in this module's own words, the way `gate_batch_topology`
    and `gate_cascade_topology` already refuse a comparison over nothing.
    """
    ceiling = int(MAX_SLOTS_PER_NODE)
    ev = {"gate": "CASCADE", "andon": "CascadeGate",
          "module_ceiling": int(MAX_SLOTS_PER_NODE),
          "cap_requested": None if cap is None else int(cap),
          "declared_group_size": None if group_size is None else int(group_size),
          "ceiling": ceiling, "per_node": {}}

    if cap is not None:
        if int(cap) > ceiling:
            raise CascadeGate(
                f"a caller asked this gate to run with a ceiling of {int(cap)}, above the "
                f"module's own MAX_SLOTS_PER_NODE={ceiling}. `cap` may only TIGHTEN: a "
                f"ceiling the caller supplies is a ceiling the caller can raise, and a gate "
                f"whose ceiling grows with the graph it is measuring cannot see the growth. "
                f"The runtime cap is INFERRED at {INFERRED_SLOT_CAP} from a single error "
                f"message and was never measured at its boundary", ev)
        ceiling = int(cap)
        ev["ceiling"] = ceiling

    if group_size is not None and int(group_size) > ceiling:
        raise CascadeGate(
            f"the declared group size {int(group_size)} is above the ceiling {ceiling}. "
            f"The runtime cap is INFERRED at {INFERRED_SLOT_CAP} from a single error "
            f"message and was never measured at its boundary; a graph built above this "
            f"ceiling is a graph whose execution depends on that inference being exact", ev)

    over = []
    for nid, node in graph.items():
        if node.get("class_type") != "BatchImagesNode":
            continue
        inputs = node.get("inputs", {}) or {}
        k = len([key for key in inputs if key.startswith("images.image")])
        bare = _bare_images_arity(inputs)
        if bare is not None:
            ev.setdefault("bare_images_nodes", {})[nid] = bare
            k += bare
        ev["per_node"][nid] = k
        if k > ceiling:
            over.append((nid, k))

    if not ev["per_node"]:
        raise CascadeGate(
            "the graph carries no BatchImagesNode at all, so this gate walked every node "
            "and measured nothing: its verdict would read '0 batch node(s), largest "
            "carries 0 slot(s)' about a graph in which no slot exists to be over any "
            "ceiling. A comparison over nothing must not report agreement", ev)

    if over:
        ev["over"] = over
        raise CascadeGate(
            f"batch node(s) {over} carry more than {ceiling} auto-grow slot(s). The runtime "
            f"cap is INFERRED at {INFERRED_SLOT_CAP} from a single error message and was "
            f"never measured at its boundary; a graph built above this ceiling is a graph "
            f"whose execution depends on that inference being exact", ev)
    ev["verdict"] = (f"{len(ev['per_node'])} batch node(s), largest carries "
                     f"{max(ev['per_node'].values(), default=0)} slot(s), ceiling "
                     f"{ceiling} - this module's MAX_SLOTS_PER_NODE={MAX_SLOTS_PER_NODE}, "
                     f"never a number the caller supplied")
    return ev


def gate_cascade_topology(graph, n_frames, group_ids, final_id, video_id, consumer_id,
                          consumer_input="video", group_size=GROUP_SIZE, *,
                          expected_sources):
    """Gate CASCADE - ANDON - every frame reaches the video exactly once, in order.

    The flat gate above cannot describe this shape, and the failures it would miss are the
    ones a cascade adds:

    * a group dropped from the final batch - 54 frames instead of 81, no error anywhere;
    * groups wired to the final batch out of order - 81 frames, correct count, shuffled clip;
    * a frame in two groups and another in none - count right, clip wrong;
    * a frame in the WRONG SLOT of the right group - count right, every source distinct,
      the groups in order, and the clip playing its frames in an order nobody chose;
    * the final batch fed by a group's LoadImage rather than the group - silently short.

    `expected_sources` is the caller's own per-frame `LoadImage` node ids IN FRAME ORDER,
    and it is **required**. Until it existed this gate ended its verdict with "groups in
    frame order" while relating no slot to any frame: measured 2026-09-03 on an 81-frame
    cascade, swapping the LoadImage bound to `images.image0` with the one bound to
    `images.image20` inside group 0 passed with the verdict unchanged. A verdict that names
    a property no code checked is this repo's most expensive defect class, so the property
    is checked and the caller supplies what checking it needs - the builders already hold
    the ordered list, because it is the frame order they built the graph from.

    `consumer_id` / `consumer_input` name where the constructed VIDEO must go, because the
    cascade has two callers with different terminals: the Stage-0 probe saves it
    (`SaveVideo.video`), and E13's A2 arm feeds it to the generator's reference slot
    (`Wan2ReferenceVideoApi.model.reference_videos.video1`). Hard-coding `SaveVideo` here
    would have made this gate silently inapplicable to the arm that spends credits.
    """
    n = int(n_frames)
    exp = [str(s) for s in expected_sources]
    ev = {"gate": "CASCADE", "andon": "CascadeGate",
          "n_frames": n, "group_size": int(group_size),
          "group_nodes": [str(g) for g in group_ids],
          "final_node": str(final_id), "video_node": str(video_id),
          "consumer": {"node": str(consumer_id), "input": consumer_input},
          "n_expected_sources": len(exp)}

    if n < 1:
        raise CascadeGate(
            f"the cascade was gated over {n} frame(s): the plan is empty, the group loop "
            f"never runs, and every count clause would compare 0 to 0. A comparison over "
            f"nothing must not report agreement", ev)
    if len(exp) != n:
        raise CascadeGate(
            f"{len(exp)} expected per-frame source id(s) against {n} frame(s); the gate "
            f"cannot relate slot k to frame k on a list that is not the frame list", ev)
    if len(set(exp)) != len(exp):
        raise CascadeGate(
            f"the {len(exp)} expected per-frame source id(s) are not distinct, so the "
            f"expectation itself already carries a duplicated frame", ev)

    plan = cascade_plan(n, group_size)
    ev["n_groups"] = len(plan)
    ev["plan"] = [list(p) for p in plan]
    problems = []

    if len(group_ids) != len(plan):
        raise CascadeGate(
            f"{len(group_ids)} group node(s) for a plan that needs {len(plan)}", ev)

    # ---- each group: dotted keys, contiguous slot names, distinct LoadImage sources, and
    # slot k bound to FRAME start+k rather than to some other frame of the same clip.
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
        else:
            got = [_link(gi[k]) for k in want]
            expect = [[exp[start + j], 0] for j in range(stop - start)]
            if got != expect:
                bad = [j for j in range(len(want)) if got[j] != expect[j]]
                j = bad[0]
                problems.append(
                    f"group {gid} slot images.image{j} is bound to {got[j]!r}, not frame "
                    f"{start + j}'s LoadImage {expect[j]!r} ({len(bad)} slot(s) differ): "
                    f"the clip would play its frames out of sequence while the count, the "
                    f"distinct-source clause and the group order all still read right")
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
            got = [_link(fi[k]) for k in want]
            expect = [[str(g), 0] for g in group_ids]
            ev["final_links"] = got
            if got != expect:
                problems.append(
                    f"the final batch's slots are {got!r}, not the group nodes in order "
                    f"{expect!r} - the clip's frames would be assembled out of sequence "
                    f"while every count still read right")

    video = graph.get(str(video_id))
    if video is None or video.get("class_type") != "CreateVideo":
        problems.append(f"node {video_id} is not a CreateVideo")
    elif not _links_equal(video["inputs"].get("images"), [str(final_id), 0]):
        problems.append(
            f"CreateVideo.images is {video['inputs'].get('images')!r}, not the FINAL "
            f"batch's output - the video would carry one group instead of the clip")

    consumer = graph.get(str(consumer_id))
    if consumer is None:
        problems.append(f"the constructed VIDEO's consumer, node {consumer_id}, is not in "
                        f"the graph")
    elif not _links_equal(consumer["inputs"].get(consumer_input), [str(video_id), 0]):
        problems.append(
            f"{consumer.get('class_type')}.{consumer_input} is "
            f"{consumer['inputs'].get(consumer_input)!r}, not CreateVideo's output. "
            f"CreateVideo is `output_node: false`, so a VIDEO nothing consumes is a VIDEO "
            f"that never exists")

    if problems:
        ev["problems"] = problems
        raise CascadeGate("; ".join(problems), ev)

    ev["verdict"] = (f"{n} distinct LoadImage nodes -> {len(plan)} group batch(es) of at "
                     f"most {group_size} -> final batch -> CreateVideo -> "
                     f"{graph[str(consumer_id)].get('class_type')}.{consumer_input}, "
                     f"dotted slot keys, groups in frame order, slot k of each group bound "
                     f"to frame k of that group's range, every link resolved")
    return ev
