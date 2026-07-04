// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  wireSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/engagements-releases',
        'getting-started/release-types',
        'getting-started/installation',
        'getting-started/core-concepts',
        'getting-started/how-wire-works',
      ],
    },
    {
      type: 'category',
      label: 'Release Types',
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
        'release-types/agentic-data-stack',
        'release-types/droughty',
        'release-types/custom',
      ],
    },
    {
      type: 'category',
      label: 'Advanced',
      items: [
        'advanced/worked-example',
        'advanced/wire-agents',
        'advanced/autopilot',
        'advanced/vscode-extension',
        'advanced/issue-tracking',
        'advanced/document-store',
        'advanced/extending',
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
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
        'tutorials/agentic-data-stack',
        'tutorials/droughty',
        'tutorials/custom',
        'tutorials/installing-and-upgrading',
        'tutorials/joining-mid-release',
        'tutorials/upgrading-your-release',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/commands',
        'reference/skills',
        'reference/mcp-servers',
        'reference/faq',
        'reference/troubleshooting',
        'reference/management-commands',
        'reference/release-notes',
      ],
    },
  ],
};

export default sidebars;
