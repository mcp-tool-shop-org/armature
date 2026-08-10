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
      customCss: ['./src/styles/starlight-custom.css'],
      disable404Route: true,
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
