import type { DefaultSiteConfig } from '@mcptoolshop/site-theme';

// Every claim on this page traces to docs/research-grounding.md, docs/license-map.md,
// docs/ROADMAP.md or README.md in this repo — or it says plainly that it has not been
// measured. There is no install section because there is nothing to install.

export const config: DefaultSiteConfig = {
  template: 'default',
  title: 'armature — You block the shot. The model shoots it.',
  description:
    'Stage your character in Blender. Render the control sequence. Let the video model paint the life over it. Twelve experiments in, the thesis is measured at product level.',
  logoBadge: 'AR',
  brandName: 'armature',
  repoUrl: 'https://github.com/mcp-tool-shop-org/armature',
  footerText:
    'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>. Founded 2026-08-10; the record is the repo’s docs tree.',

  hero: {
    badge: 'v0.1.0 released 2026-08-13 · twelve experiments closed · the thesis is measured at product level',
    headline: 'armature —',
    headlineAccent: 'You block the shot. The model shoots it.',
    description:
      'Stage your character in Blender. Render the control sequence. Let the video model paint the life over it.',
    primaryCta: { href: '#where-this-is', label: 'Where this actually is' },
    secondaryCta: { href: 'handbook/', label: 'Read the handbook' },
    previews: [],
  },

  sections: [
    {
      kind: 'features',
      id: 'the-problem',
      title: 'The problem',
      features: [
        {
          title: 'A video model gives you what no renderer can',
          desc: 'Motion, light, weight, the way a coat swings and a face catches a lamp. That is the expensive half of animation, and a video model produces it directly.',
        },
        {
          title: 'It cannot be told who is on screen',
          desc: 'Or where they are standing. Prompt a character and you get a character; prompt again and you get a different one. There is no handle for this person, here, facing that way, in frame 47.',
        },
        {
          title: 'armature is the handle',
          desc: 'The previz scene is ground truth. A canonical mesh is staged and animated, and the render becomes a per-frame control sequence the video model works inside. Twelve experiments in, the idea holds at product level — and every claim behind that sentence traces to a numbered experiment in the repo.',
        },
      ],
    },

    {
      kind: 'features',
      id: 'how-it-works',
      title: 'How it works',
      subtitle:
        'Three steps. Structure comes from geometry you own; life comes from the model.',
      features: [
        {
          title: '1 — Stage',
          desc: 'A canonical character mesh is posed, animated and framed in headless Blender. You block the shot: where the character stands, how they move, what the camera does.',
        },
        {
          title: '2 — Render the control sequence',
          desc: 'Per-frame control channels come out of the staged scene — depth, normal, mask, edge, and optionally a skeleton drawn from bone transforms that are already known. Rendered from geometry, never estimated from footage.',
        },
        {
          title: '3 — Generate inside the structure',
          desc: 'The control sequence and a reference stack go to a video model, which generates within them. Identity is meant to be a named, versioned thing that rides in the prompt and the references — not an accident of a lucky frame.',
        },
      ],
    },

    {
      kind: 'data-table',
      id: 'where-this-is',
      title: 'Where this is',
      subtitle:
        'armature was founded on 2026-08-10. The thesis it exists to test — does a CG-rendered control sequence hold a character through a video model — is now measured at product level across twelve closed experiments, judged by the Director’s eye, and a negative result remains a full success here. The counters below are dated; README.md in the repo carries the live ones.',
      columns: ['Counter', 'As of 2026-08-13'],
      rows: [
        [
          'Experiments',
          '12 closed (one more withdrawn un-run on a falsified premise); E13 — the composed-route probe — dispatched, halted at zero spend for a repair arc, and re-armed, all 2026-08-13',
        ],
        [
          'Routes',
          'Two, plus one under probe: driven (rig-rendered pose → Animate; proven at shot level, parked), free (authored start frame → camera tier at the 6.0 / uni_pc baseline), composed (authored references into a hosted identity-lock tier — E13)',
        ],
        [
          'Spend',
          'Founding arc: 22 probes at 4 credits each; the E08–E12 arc metered 0 at every submission (GPU-hour billing) under per-experiment ceilings',
        ],
        [
          'License map',
          'Every adopted dependency carries a retrieved licence document; UNVERIFIED is treated as NO; third-party-tier routes carry per-route disclosure (ruled 2026-08-12)',
        ],
        [
          'Research grounding',
          '24 findings; 34 of 34 citations resolved against a retrieval oracle, zero fabricated',
        ],
        [
          'The founding thesis',
          'MEASURED — identity holds driven (E08) and unanchored (E11); the camera obeys authored control to one pixel (E11); a handed world holds to the last frame on two seeds (E12)',
        ],
        [
          'What exists today',
          'v0.1.0 — the first marked state of the record — plus the routes, the instrument shelf, the licence map, the experiment record E01–E13, and this page',
        ],
      ],
    },

    {
      kind: 'features',
      id: 'established',
      title: 'What is already established',
      subtitle:
        'Three things here are evidenced. None of them was measured in this repo — they were measured elsewhere and retrieved, and that is exactly why they are the only things stated as fact.',
      features: [
        {
          title: 'The closest published precedent',
          desc: 'Champ (Zhu et al. 2024, arXiv:2403.14781) compared dense 3D-parametric guidance — depth, normal and semantic maps rendered from a posed body model — against a 2D skeleton alone. FVD 192.34 to 170.20, SSIM 0.672 to 0.773, LPIPS 0.296 to 0.235. Dropping the skeleton entirely still beat skeleton-only on FVD, at 184.24. That is armature’s thesis, measured by someone else, on someone else’s subject matter.',
        },
        {
          title: 'The licensing finding',
          desc: 'OpenPose — the most widely used pose extractor in the ControlNet ecosystem — is CMU non-commercial, and is banned here. Depth Anything V2 Small is Apache 2.0 while Large is CC-BY-NC: same family, same page layout, different licence. Rendering control from geometry removes that entire tier by construction rather than by substitution.',
        },
        {
          title: 'What nobody has measured',
          desc: 'No quantitative curve exists anywhere for control strength against identity drift. No study compares per-character LoRA against zero-shot conditioning on stylized game art. No head-to-head of depth versus pose versus segmentation on one identity metric. Those gaps are why this repo has an experiment arc instead of a feature list.',
        },
      ],
    },

    {
      kind: 'data-table',
      id: 'how-this-repo-works',
      title: 'How this repo works',
      subtitle:
        'Three seats, and the separation is the point: the session that designs an experiment does not grade its results, and the session that runs it does not decide their meaning. Every non-trivial change runs as a numbered experiment — spec written before the work, report written after, advisor ruling last. Metrics are diagnostics; the Director’s eye is the judge.',
      columns: ['Seat', 'Does', 'Must not'],
      rows: [
        ['Director', 'Sets direction; judges every artifact by eye', '—'],
        [
          'Advisor',
          'Writes specs, rules on reports, folds findings into the repo',
          'Execute, or grade its own rulings',
        ],
        [
          'Executor',
          'Runs the spec, measures, reports evidence',
          'Decide what results mean, or judge quality',
        ],
      ],
    },
  ],
};
