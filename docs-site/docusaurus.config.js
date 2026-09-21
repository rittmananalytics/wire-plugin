// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Wire Framework',
  tagline: 'AI-accelerated delivery for data platform engagements',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://wire-plugin.readthedocs.io',
  baseUrl: '/en/latest/',

  organizationName: 'rittmananalytics',
  projectName: 'wire-plugin',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },

  // The landing page design's type stacks name 'Google Sans' first, which is
  // Google-proprietary and not redistributed here. Inter is the next name in
  // those stacks, and IBM Plex Mono is what the terminal blocks call for, so
  // both are loaded and the stacks resolve to a designed face rather than to
  // system-ui.
  stylesheets: [
    {
      href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap',
      rel: 'stylesheet',
    },
  ],

  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/rittmananalytics/wire-plugin/tree/main/docs-site/',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Wire Framework',
        logo: {
          alt: 'Wire Framework',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'wireSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://github.com/rittmananalytics/wire-plugin',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {label: 'Getting Started', to: '/docs/using-wire/what-is-wire'},
              {label: 'Release Types', to: '/docs/release-types/discovery-shape-up'},
              {label: 'FAQ', to: '/docs/reference/faq'},
            ],
          },
          {
            title: 'Rittman Analytics',
            items: [
              {label: 'rittmananalytics.com', href: 'https://rittmananalytics.com'},
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Rittman Analytics. Built with Docusaurus.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'yaml', 'sql'],
      },
    }),
};

export default config;
