> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — status: EXPERIMENTING. Nothing here is settled.

**Director, 2026-08-10: _"Let's not write anything in stone just yet, as we're experimenting."_**

That governs how the E02 documents are read. They record **measurements and working decisions**,
not doctrine. Specifically:

- The **bridge choice**, the **-1 acceptance**, the **noise floor**, and the **framing
  pre-registration** are all provisional. Any of them may be revised by a later arm without
  anyone having to justify a reversal.
- The **numbers stand** — 4 credits/generation, 32 of 33 frames differing at max delta 71,
  `out = max(src-1, 0)` — because those were measured. What is provisional is what they *mean*
  and what we do about them.
- **Nothing from E02 is promoted into CLAUDE.md or into a standing law until the arc closes.**
  Two laws did get amended today on evidence that is not E02-specific — `dry_run` proves
  nothing about runnability, and bytes are not content — and those stay, because they were
  earned outside this experiment's open questions.

The Gate 0 sheet for A1a has been seen by the Director and read as looking right, with the
explicit caveat that **A2 has not run**, so it is a demonstration and not yet evidence.

**Next, and it is four generations / ~16 credits inside a 12-generation ceiling:**

1. Add a lossless `SaveImage` tap on the `VAEDecode` output — no extra generation, the frames
   already exist in the graph.
2. A0: three identical submissions, floor characterised without codec noise.
3. A2: the no-control row. **This is the one that turns the sheet into evidence.**