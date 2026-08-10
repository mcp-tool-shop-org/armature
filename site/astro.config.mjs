// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://mcp-tool-shop-org.github.io',
  base: '/armature',
  integrations: [
    starlight({
      title: 'armature',
      description: 'You block the shot. The model shoots it. — the handbook.',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/mcp-tool-shop-org/armature' },
      ],
      // NOT anchor's/facet's shape. Starlight 0.39.0 REMOVED the
      // `{ label, autogenerate }` shorthand those repos use; on 0.41 it is a
      // hard config error, not a deprecation warning. The autogenerate config
      // now has to sit inside an `items` array.
      sidebar: [
        {
          label: 'Handbook',
          items: [{ autogenerate: { directory: 'handbook' } }],
        },
      ],
      // The org-wide /favicon.svg 404 has a single cause, found 2026-08-10:
      // site-theme's BaseLayout.astro HARDCODES `<link rel="icon" href="{base}favicon.svg">`
      // with no prop and no head slot, so every repo on the theme points at a file
      // none of them ship. The fix is to ship one — see site/public/favicon.svg,
      // a purpose-drawn simplification of the mark (a 1300px wire render cannot be
      // downscaled to 32px; it turns to mush, measured).
      favicon: '/favicon.svg',
      head: [
        { tag: 'link', attrs: { rel: 'icon', href: '/armature/favicon.ico', sizes: '16x16 32x32 48x48 64x64' } },
        { tag: 'link', attrs: { rel: 'apple-touch-icon', href: '/armature/apple-touch-icon.png' } },
      ],
      customCss: ['./src/styles/starlight-custom.css'],
      disable404Route: true,
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
