import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Get started
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            style={{marginLeft: '1rem'}}
            to="/docs/getting-started/installation">
            Installation
          </Link>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    title: '50+ slash commands',
    description:
      'A complete command set covering every phase of a data platform engagement — from problem definition through to enablement. No command runs without the previous one completing.',
  },
  {
    title: '12 release types',
    description:
      'Discovery, dbt development, full platform, platform migration, droughty, and more. Each release type encodes the right workflow for the job.',
  },
  {
    title: 'Works in Claude Code and Gemini CLI',
    description:
      'The same commands run on both runtimes. Install the Wire plugin for Claude Code or the Wire extension for Gemini CLI — specs are shared between them.',
  },
];

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="padding-horiz--md padding-vert--lg">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="AI-accelerated delivery for data platform engagements — Wire Framework documentation">
      <HomepageHeader />
      <main>
        <section style={{padding: '3rem 0'}}>
          <div className="container">
            <div className="row">
              {features.map((props, idx) => (
                <Feature key={idx} {...props} />
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
