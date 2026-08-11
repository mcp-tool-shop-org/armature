# E07 — the registered site list, and the discrepancy in what "18" denotes

**Registered 2026-08-11, before the first bone is placed and before any measurement of the
subject mesh was taken.** Committed on its own so its timestamp is git's and not a seat's.
A site list chosen after seeing what was easy to rig is name-shopping; this one was written
before the mesh had been imported once.

---

## What the spec instructed

> E01's report is re-read at build time. **If it enumerates the 18 sites, that list governs. If
> it does not, the executor registers a list before any rigging begins** … adjusted to whatever
> count E01's "18" actually denotes, with the discrepancy reported rather than reconciled
> silently.

E01's report was re-read. **It does not enumerate the sites.** It reports the count and the
per-file tally — `0 / 18` in all four files — and its prose says only *"zero of the 18 anatomical
sites are identifiable by name."*

**The enumeration exists, but in the instrument rather than the report:**
`tools/probe_glb.py`, `SITES`, lines 36–55 — the dict against which every `0 / 18` in E01's
report was actually computed. That is what "18" denotes here, it is retrievable, and it governs.

## Discrepancy 1 — E01's 18 are KEYPOINTS, not BONES. Different object counted.

`probe_glb.py::SITES` is a COCO-18-shaped list of **joint locations**:

```
nose · neck · shoulder.L/R · elbow.L/R · wrist.L/R · hip.L/R · knee.L/R · ankle.L/R
     · eye.L/R · ear.L/R
```

A bone is not a joint location. A bone is a **segment** with a head and a tail. Counting
"18 sites" and counting "18 bones" are counts of two different objects, and this repo has a
standing law about exactly that failure (*check the unit, the population, and the object being
counted before predicting*).

**The rule this list is registered under, stated before any bone exists:**

> A site is satisfied by **exactly one bone bearing that site's name, whose HEAD is placed at
> that anatomical location.** The bone's tail is wherever the skeleton's structure puts it.

Under that rule `shoulder.L` names the upper-arm bone (head at the shoulder), `elbow.L` names
the forearm (head at the elbow), `hip.L` names the thigh (head at the hip), and so on. The
mapping is one-to-one and total, and it is fixed here rather than at build time.

## Discrepancy 2 — the spec's own suggested convention is 19, not 18

The spec offers, parenthetically, *"hips, spine, chest, neck, head; L/R shoulder, upper_arm,
forearm, hand, thigh, shin, foot."* Counted: 5 centre + (7 × 2) = **19 bones**, and it is a
different set from E01's 18 — it has a torso chain and no face keypoints, where E01's list has
face keypoints and no torso chain. Neither list is a subset of the other. Reported, not
reconciled silently.

## Discrepancy 3 — 5 of E01's 18 are face keypoints, which the spec puts OUT OF SCOPE

`nose`, `eye.L`, `eye.R`, `ear.L`, `ear.R` are facial. The spec's out-of-scope section reads
*"Finger and face bones."*

**Resolution, registered here in advance rather than decided at build time:** those five exist
as bones so the naming gap E01 measured actually closes under E01's own instrument, and they are
created with **`use_deform = False`** — they are named markers, not deformers. No facial
deformation is authored, no vertex is weighted to them, and the out-of-scope line is respected
in the sense that matters (nothing rigs the face). The alternative — registering 13 of 18 —
would leave E07 unable to answer the gap it exists to close, measured by the instrument that
opened it.

**This is a reconciliation and it is disclosed as one.** The Director may rule it wrong; it is
recorded here so the ruling has something to rule on.

---

## THE REGISTERED LIST — 22 bones

### Table A — the 18 E01 sites (the gap-closing list). Gate N binds on all 18.

| # | site / bone name | head at | tail at | deform |
|---|---|---|---|---|
| 1 | `nose` | nose | forward of nose | **no** |
| 2 | `neck` | base of neck | base of skull | yes |
| 3 | `shoulder.L` | left shoulder | left elbow | yes |
| 4 | `shoulder.R` | right shoulder | right elbow | yes |
| 5 | `elbow.L` | left elbow | left wrist | yes |
| 6 | `elbow.R` | right elbow | right wrist | yes |
| 7 | `wrist.L` | left wrist | left hand end | yes |
| 8 | `wrist.R` | right wrist | right hand end | yes |
| 9 | `hip.L` | left hip | left knee | yes |
| 10 | `hip.R` | right hip | right knee | yes |
| 11 | `knee.L` | left knee | left ankle | yes |
| 12 | `knee.R` | right knee | right ankle | yes |
| 13 | `ankle.L` | left ankle | left toe | yes |
| 14 | `ankle.R` | right ankle | right toe | yes |
| 15 | `eye.L` | left eye | forward of it | **no** |
| 16 | `eye.R` | right eye | forward of it | **no** |
| 17 | `ear.L` | left ear | outward of it | **no** |
| 18 | `ear.R` | right ear | outward of it | **no** |

### Table B — the structural extension. 4 bones a keypoint list does not name and a deforming rig cannot omit.

E01's 18 contain **no torso chain and no skull**. A rig built from them alone would have the
entire trunk and head unweighted — every vertex between the hips and the neck would belong to
no bone. These four are registered here, before the first bone, for that reason and no other.

| # | bone name | head at | tail at | deform |
|---|---|---|---|---|
| 19 | `hips` | pelvis centre (ROOT) | spine base | yes |
| 20 | `spine` | spine base | chest base | yes |
| 21 | `chest` | chest base | neck base | yes |
| 22 | `head` | base of skull | top of skull | yes |

### Parent hierarchy, registered before placement

```
hips (root)
├─ spine → chest → neck → head
│                          ├─ nose      (no deform)
│                          ├─ eye.L/R   (no deform)
│                          └─ ear.L/R   (no deform)
├─ chest → shoulder.L → elbow.L → wrist.L
├─ chest → shoulder.R → elbow.R → wrist.R
├─ hip.L → knee.L → ankle.L
└─ hip.R → knee.R → ankle.R
```

## The E01-matcher re-check, registered as a named diagnostic

Beyond Gate N (exact names), the rigged output is run back through `probe_glb.py`'s own
`match_sites()` and the resulting `anatomical_sites_count` is reported. **E01 measured 0 / 18 on
four files.** Whatever this number comes back as, it is the same instrument on the same question,
and it is reported as a number, not as a verdict. It gates nothing — Gate N is the andon.

## What is NOT registered here

Finger bones, toe bones, facial deformation bones, twist bones, IK targets, weapon bones, a
retargeting map, or any second naming convention (Mixamo, VRM, Rigify) beside this one.
