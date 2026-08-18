# Comfy Agent consult #12 — brief: is there a VERIFIER tier on the served platform, or only a generator tier?

**From:** the armature advisor seat, 2026-08-17 · **Relay:** the Director carries this brief to
the Comfy Agent and returns its answer · **Trigger:** the Director ruled today that a gate on
**nameable attribute presence** may block an asset, while character identity may never be
gated. That unlocks a verification tier we have never built and have never inventoried. A new
model class is the standing brief trigger. · **Numbering:** file series (…10, 11 → 12).

**Round shape: knowledge only.** No tabs, no graph building, no generations, no credits.
Catalog facts, node schemas and licence **documents** only — never verdicts; UNVERIFIED = NO
stands. **All model ids, node names and filenames in plain text, not code spans** (the #8
relay-mangling lesson). Mark NOT VISIBLE what the catalog does not say.

---

## Context — what this feeds

We are building a gate that reads a generated image and checks **named, checkable claims** on
it: a garment is present, a palette holds, a silhouette reads, a forbidden colour is absent.
The gate may block. It is explicitly **not** an identity check — whether a figure is the same
character is a human judgment here and no metric is permitted to gate it.

The design names three tiers, cheapest first: a zero-shot **discriminative** screen for
presence/closed-set claims, a **VQA-style** scorer for compositional claims, and a
dependency-ordered question DAG to localise which claim failed. A hard rule says the verifier
must be a **different model family from the generator**, and a generative VLM is never its own
gate.

The problem this brief exists to solve: **we do not know whether the served platform can run a
verification pass at all.** Everything we have inventoried there generates.

## Already measured — calibrate against, do not re-derive

| item | state |
|---|---|
| Our local model KB holds **119 models across 9 categories** | measured today — the categories are image base models, image control/utility, video generation, 3D asset generation, audio generation, local LLM + vision, ComfyUI + workflows, image editing, captioning/tagging. **There is no verifier or evaluation category.** |
| SigLIP2 appears in that KB **only as a component inside generative captioners** | measured today — JoyCaption Beta One (LLaVA, Llama 3.1 8B + SigLIP2-so400m-patch14-384) and MiniCPM-V 4.5 (Qwen3-8B + SigLIP2-400M). No standalone entry. Both are generative, which our rule bars from being the gate. |
| Wan family, Qwen, TRELLIS, SDXL-class licences | already mapped in our licence map; not this round's object |
| The gate's own tooling has never executed here | measured — its optional image extra is not installed on this rig, so the non-mock path has never run |

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Name one served node that takes an IMAGE input
and returns a numeric score or a classification label rather than an image, and give its exact
node name and its output socket types. If no such node is served, say NOT VISIBLE in one line —
that answer is as useful as a name and it bounds everything below.

**Q1 — the discriminative-screen inventory (the load-bearing question).** Does the platform
serve any **discriminative** image-text scoring model as a loadable model — SigLIP or SigLIP2
family, CLIP variants, or equivalents — usable to ask "is X present in this image" and get a
score back? Exact model file names as saved, plain text. If the only vision models served are
generative captioners or VLM chat models, say so plainly; that is the finding.

**Q2 — the node surface for scoring.** List the served nodes that **evaluate** rather than
generate: image-text similarity, zero-shot classification, VQA, aesthetic or quality scoring,
any comparator. For each, exact node name, input sockets, output sockets. If a category is
absent, mark it NOT VISIBLE rather than proposing a substitute.

**Q3 — VQA on the served tier.** Is there any served path to ask a natural-language question
about an image and get a constrained answer — a yes/no, a label, or a probability — as opposed
to free-form caption text? Name the mechanism and whether the answer is constrained or free
text. The distinction matters to us: a free-text caption is not a gate.

**Q4 — partner-API evaluators.** Do any partner providers expose an **evaluation or scoring**
endpoint (image-text alignment, safety/attribute classification, moderation-style labels), as
distinct from generation? Name provider and endpoint exactly. For any named, quote what the
provider's terms say about using outputs for automated decisions — and give the URL of the
document, not a summary.

**Q5 — licences for everything named above.** For each model or component named in Q1–Q4:
declared licence, the URL of the actual licence document, and the operative clause on
commercial use. A blank or absent licence field is itself the answer and should be reported as
blank, never inferred from a sibling repo.

**Q6 — the honest bound.** If the platform is generation-only and carries no verification tier,
say that in one sentence. We will build the verifier elsewhere and we would rather know now
than discover it in a graph.

## Halt conditions

Answer what the catalog and visible documents support; mark everything else NOT VISIBLE. No
speculation, no substituting an "equivalent" model for one that is not served, no licence
verdicts, no builds, no runs. If a question would require building or running anything, stop at
naming what it would take.
