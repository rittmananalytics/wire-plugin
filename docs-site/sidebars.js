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
      ],
    },
    {
      type: 'category',
      label: 'Release Types',
      items: [
        'release-types/discovery-shape-up',
        'release-types/discovery-sop',
        'release-types/kickoff-deck',
        'release-types/full-platform',
        'release-types/pipeline-dbt',
        'release-types/dbt-development',
        'release-types/dashboard-extension',
        'release-types/dashboard-first',
        'release-types/enablement',
        'release-types/agentic-commerce',
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
        'advanced/autopilot',
        'advanced/wire-studio',
        'advanced/vscode-extension',
        'advanced/issue-tracking',
        'advanced/document-store',
        'advanced/extending',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/faq',
        'reference/troubleshooting',
        'reference/management-commands',
      ],
    },
  ],
};

export default sidebars;
