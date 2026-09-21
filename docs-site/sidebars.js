// @ts-check

// Two parts. Part 1 is read in order and uses plain language only: no agent
// names or release-type identifiers until chapter 6, and Wire command names
// only where Wire itself says them (the Running:/Ran: line on each reply, and
// the command beside each step of a plan), never in the prose.
// Part 2 is the technical reference, kept at its existing paths so links from
// the 3.x docs still resolve.

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  wireSidebar: [
    {
      type: 'category',
      label: 'Part 1: Using Wire',
      collapsed: false,
      items: [
        'using-wire/what-is-wire',
        'using-wire/getting-started',
        'using-wire/data-modelling-and-transformation',
        'using-wire/working-a-ticket',
        'using-wire/running-discovery',
        'using-wire/how-wire-works',
        'using-wire/a-full-platform-build',
      ],
    },
    {
      type: 'category',
      label: 'Part 2: Technical Reference',
      collapsed: false,
      link: {
        type: 'generated-index',
        title: 'Technical Reference',
        description: 'The reference half of the guide: setting up, every release type, command-level tutorials, the advanced topics and the command and integration references.',
        slug: '/technical-reference',
      },
      items: [
        {
          type: 'category',
          label: 'Introduction',
          link: {type: 'generated-index', title: 'Introduction', slug: '/technical-reference/introduction'},
          items: [
            'intro',
            'getting-started/installation',
            'getting-started/upgrading-from-3x',
            'getting-started/engagements-releases',
            'getting-started/release-types',
            'getting-started/core-concepts',
            'getting-started/how-wire-works',
          ],
        },
        {
          type: 'category',
          label: 'Release Types',
          link: {type: 'generated-index', title: 'Release Types', slug: '/technical-reference/release-types'},
          items: [
            'release-types/discovery-shape-up',
            'release-types/discovery-sop',
            'release-types/full-platform',
            'release-types/pipeline-dbt',
            'release-types/dbt-development',
            'release-types/dashboard-extension',
            'release-types/dashboard-first',
            'release-types/enablement',
            'release-types/platform-migration',
            'release-types/tenant-carveout',
            'release-types/bi-migration',
            'release-types/agentic-data-stack',
            'release-types/droughty',
            'release-types/custom',
          ],
        },
        {
          type: 'category',
          label: 'Tutorials',
          link: {type: 'generated-index', title: 'Tutorials', description: 'Command-level walkthroughs of every release type, showing the commands Wire runs at each step.', slug: '/technical-reference/tutorials'},
          items: [
            'tutorials/index',
            'tutorials/full-platform',
            'tutorials/dbt-development',
            'tutorials/pipeline-dbt',
            'tutorials/discovery-shape-up',
            'tutorials/discovery-sop',
            'tutorials/dashboard-extension',
            'tutorials/dashboard-first',
            'tutorials/enablement',
            'tutorials/platform-migration',
            'tutorials/platform-migration-tenant-carveout',
            'tutorials/looker-to-omni-migration',
            'tutorials/looker-to-omni-real-run',
            'tutorials/agentic-data-stack',
            'tutorials/droughty',
            'tutorials/custom',
            'tutorials/installing-and-upgrading',
            'tutorials/joining-mid-release',
            'tutorials/upgrading-your-release',
            'tutorials/data-model-registry',
            'tutorials/dbt-charts',
          ],
        },
        {
          type: 'category',
          label: 'Advanced',
          link: {type: 'generated-index', title: 'Advanced', slug: '/technical-reference/advanced'},
          items: [
            'advanced/worked-example',
            'advanced/release-director',
            'advanced/wire-agent-architecture',
            'advanced/wire-agents',
            'advanced/autopilot',
            'advanced/model-routing',
            'advanced/dbt-charts',
            'advanced/agents-schema',
            'advanced/vscode-extension',
            'advanced/issue-tracking',
            'advanced/document-store',
            'advanced/extending',
            'advanced/registries',
            'advanced/tracing',
            'advanced/fathom-sync',
            'advanced/modality-models',
            'advanced/business-rules',
          ],
        },
        {
          type: 'category',
          label: 'Reference',
          link: {type: 'generated-index', title: 'Reference', slug: '/technical-reference/reference'},
          items: [
            'reference/commands',
            'reference/skills',
            'reference/mcp-servers',
            'reference/faq',
            'reference/troubleshooting',
            'reference/management-commands',
            'reference/release-notes',
            'reference/testing',
          ],
        },
      ],
    },
  ],
};

export default sidebars;
