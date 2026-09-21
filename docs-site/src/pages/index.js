import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import '../css/wire-landing.css';

// Ported from the Claude Design handoff "Wire Docs Landing Redesign".
//
// The design ships its own nav and footer, so Layout is given noFooter and the
// Docusaurus navbar is hidden for this page in wire-landing.css. Absolute
// readthedocs URLs in the mock are replaced with <Link to>, so the page works on
// any deployment and in local development.

const Arrow = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

const Tick = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <polyline points="4 12 10 18 20 6" />
  </svg>
);

const cards = [
  {
    title: 'Say what you want, not which command',
    body: (
      <>
        Wire has 313 commands. You do not have to know them. Say what you want
        done and Wire works out which command that is, names it before it runs,
        runs it, and stops where a decision is yours. Typing commands still
        works, always.
      </>
    ),
    icon: (
      <>
        <path d="M4 6h16M4 12h10M4 18h7" />
        <path d="M15 17l3 3 5-6" />
      </>
    ),
    link: {to: '/docs/advanced/release-director', text: 'The release director model'},
  },
  {
    title: 'Automatic validation',
    body: (
      <>
        Generate runs its own validate step when it finishes and folds the PASS or
        FAIL into its output. Review still requires a passing validate either way.
      </>
    ),
    icon: <path d="M20 6L9 17l-5-5" />,
  },
  {
    title: 'Meeting transcripts auto-sync',
    body: (
      <>
        Wire pulls new Fathom call transcripts for the engagement's client into{' '}
        <code>.wire/engagement/calls/</code> automatically, once per session, with
        an analytical findings write-up per call.
      </>
    ),
    icon: (
      <>
        <path d="M23 7l-7 5 7 5V7z" />
        <rect x="1" y="5" width="15" height="14" rx="2" />
      </>
    ),
  },
  {
    title: 'Agree what the numbers mean first',
    body: (
      <>
        An optional first step records, per business domain, every competing
        definition of a metric, the file it came from, what they disagree on, and
        who approved the decision. Disputed rules generate a reconciliation query
        that runs immediately rather than surfacing in testing.
      </>
    ),
    icon: (
      <>
        <path d="M9 7h9M9 12h9M9 17h9" />
        <circle cx="5" cy="7" r="1.3" />
        <circle cx="5" cy="12" r="1.3" />
        <circle cx="5" cy="17" r="1.3" />
      </>
    ),
    link: {to: '/docs/advanced/business-rules', text: 'Business rules discovery'},
  },
  {
    title: 'Start from a model that already exists',
    body: (
      <>
        Where a client models their data in Modality, Wire reads the entities,
        sources and relationships from it instead of deriving them again. The
        requirements are still read, and the difference between the two is raised
        as a finding.
      </>
    ),
    icon: (
      <>
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M7.5 8l3.2 7M16.5 8l-3.2 7M8.5 6h7" />
      </>
    ),
    link: {to: '/docs/advanced/modality-models', text: 'Reading a Modality model'},
  },
];

const stats = [
  {
    lead: '3',
    accent: '13',
    title: '313 slash commands',
    body:
      'A complete command set covering every phase of a data platform engagement, from problem definition through to enablement. A command stops if the step it depends on is not finished — and from 4.0 you can direct the work in plain language instead of typing them.',
  },
  {
    lead: '1',
    accent: '2',
    title: '12 release types',
    body:
      'Discovery (diagnostic or modelling-led), dbt development, full platform, platform migration, droughty, and more. Each one carries a machine-readable definition of its own workflow.',
  },
  {
    lead: '×',
    accent: '2',
    title: 'Works in Claude Code and Gemini CLI',
    body:
      'The same commands run on both runtimes. Install the Wire plugin for Claude Code or the Wire extension for Gemini CLI — specs are shared between them.',
  },
];

function Nav() {
  return (
    <nav className="nav">
      <div className="nav-in">
        <span className="nav-brand">
          <img src={useBaseUrl('/img/wire_white.svg')} alt="Wire" />
          <span className="ver">v4.0</span>
        </span>
        <div className="nav-links">
          <Link to="/docs/using-wire/what-is-wire">Documentation</Link>
          <a
            className="nav-gh"
            href="https://github.com/rittmananalytics/wire-plugin">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
            </svg>
            GitHub
          </a>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <header className="hero">
      <div className="wrap hero-in">
        <div>
          <p className="hero-eyebrow">
            <span className="dot" />
            New in 4.0 — direct the work, Wire runs the commands
          </p>
          <h1>Wire Framework</h1>
          <p className="sub">
            AI-accelerated delivery for data platform engagements
          </p>
          <div className="cta-row">
            <Link className="btn btn-pri" to="/docs/using-wire/what-is-wire">
              Get started
              <Arrow />
            </Link>
            <Link className="btn btn-sec" to="/docs/getting-started/installation">
              Installation
            </Link>
          </div>
          <div className="hero-install">
            <span className="p">$</span>
            <span className="cmd">/plugin install wire@rittmananalytics</span>
          </div>
        </div>
        <div className="heroterm">
          <div className="win">
            <div className="bar">
              <i />
              <i />
              <i />
              <span>claude — acme-analytics</span>
            </div>
            <pre>
              <span className="c">&gt;</span> run what&apos;s next
              {'\n\n'}
              <span className="d">
                dashboard_first · 03-store-dashboards · requirements approved
              </span>
              {'\n'}
              <span className="d">
                two runnable, no dependency between them
              </span>
              {'\n\n'}
              <span className="y">conceptual_model-generate</span>
              <span className="d"> — lane · business_rules waived by R-1</span>
              {'\n'}
              <span className="y">mockups-generate</span>
              <span className="d"> — foreground, needs you</span>
              {'\n\n'}
              <span className="g">✓ 7 entities · validate: PASS</span>
              {'\n\n'}
              <span className="r">1 decision waiting</span>
              {'\n'}
              {'  conceptual_model — approve now, changes, or park?'}
              {'\n'}
            </pre>
          </div>
        </div>
      </div>
    </header>
  );
}

function Stats() {
  return (
    <section className="stats">
      <div className="wrap stats-in">
        {stats.map((s) => (
          <div className="stat" key={s.title}>
            <div className="n">
              {s.lead}
              <em>{s.accent}</em>
            </div>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function WhatsNew() {
  return (
    <section className="four">
      <div className="wrap four-in">
        <div className="four-head">
          <span className="eyebrow">Release 4.0</span>
          <h2>New in 4.0</h2>
          <p className="lede">
            The rules for how a delivery engagement runs used to live inside
            Wire's own source, as prose. They are now data the framework reads
            and enforces.
          </p>
        </div>
        <div className="cards">
          {cards.map((c) => (
            <div className="card" key={c.title}>
              <span className="ic">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  {c.icon}
                </svg>
              </span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
              {c.link && (
                <Link className="lnk" to={c.link.to}>
                  {c.link.text}
                  <Arrow />
                </Link>
              )}
            </div>
          ))}
        </div>
        <p className="four-notes">
          <Link to="/docs/reference/release-notes">
            Read the full release notes
            <Arrow />
          </Link>
        </p>
      </div>
    </section>
  );
}

function HowItRuns() {
  return (
    <section className="how">
      <div className="wrap how-in">
        <div>
          <span className="eyebrow">The process is enforced, not described</span>
          <h2>A machine-readable definition of every release type.</h2>
          <p className="lede">
            Every release type has a machine-readable definition of its phases
            and what depends on what. A shared gate reads it and stops a command
            whose prerequisites are not met.{' '}
            <strong>Overriding takes your name and a reason, both recorded.</strong>
          </p>
          <ul>
            <li>
              <span className="mk">
                <Tick />
              </span>
              <span>A command stops if the step it depends on is not finished.</span>
            </li>
            <li>
              <span className="mk">
                <Tick />
              </span>
              <span>
                Each one carries a machine-readable definition of its own
                workflow.
              </span>
            </li>
            <li>
              <span className="mk">
                <Tick />
              </span>
              <span>Specs are shared between Claude Code and Gemini CLI.</span>
            </li>
          </ul>
        </div>
        <div className="win">
          <div className="bar">
            <i />
            <i />
            <i />
            <span>release-types/full_platform.yaml</span>
          </div>
          <pre>
            <span className="c">release_type:</span> full_platform
            {'\n'}
            <span className="c">phases:</span>
            {'\n  - '}
            <span className="c">name:</span> foundation
            {'\n    '}
            <span className="c">artifacts:</span>
            {'\n      - '}
            <span className="c">id:</span> requirements
            {'\n      - '}
            <span className="c">id:</span> conceptual_model
            {'\n        '}
            <span className="c">depends_on:</span>
            {'\n          '}
            <span className="c">artifact:</span> requirements
            {'\n          '}
            <span className="c">step:</span>     review
            {'\n          '}
            <span className="c">status:</span>   <span className="g">approved</span>
            {'\n      - '}
            <span className="c">id:</span> data_model
            {'\n        '}
            <span className="c">depends_on:</span>
            {'\n          '}
            <span className="c">artifact:</span> conceptual_model
            {'\n          '}
            <span className="c">step:</span>     review
            {'\n          '}
            <span className="c">status:</span>   <span className="g">approved</span>
            {'\n        '}
            <span className="c">gate:</span> <span className="y">blocking</span>{'  '}
            <span className="d"># name + reason</span>
          </pre>
        </div>
      </div>
    </section>
  );
}

function Runtimes() {
  return (
    <section className="run">
      <div className="wrap run-in">
        <div>
          <h2>Works in Claude Code and Gemini CLI.</h2>
          <p>
            The same commands run on both runtimes. Install the Wire plugin for
            Claude Code or the Wire extension for Gemini CLI — specs are shared
            between them.
          </p>
        </div>
        <div className="run-logos">
          <div className="run-chip">
            <img src={useBaseUrl('/img/logo-claude.png')} alt="" />
            <span>Claude Code</span>
          </div>
          <div className="run-chip">
            <img src={useBaseUrl('/img/logo-gemini.png')} alt="" />
            <span>Gemini CLI</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="foot">
      <div className="wrap foot-in">
        <div className="foot-grid">
          <div className="foot-brand">
            <img src={useBaseUrl('/img/wire_white.svg')} alt="Wire" />
          </div>
          <div className="foot-col">
            <div>
              <h4>Documentation</h4>
              <ul>
                <li>
                  <Link to="/docs/using-wire/what-is-wire">Getting Started</Link>
                </li>
                <li>
                  <Link to="/docs/release-types/discovery-shape-up">
                    Release Types
                  </Link>
                </li>
                <li>
                  <Link to="/docs/reference/faq">FAQ</Link>
                </li>
              </ul>
            </div>
            <div>
              <h4>Rittman Analytics</h4>
              <ul>
                <li>
                  <a href="https://rittmananalytics.com">rittmananalytics.com</a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div className="foot-base">
          <span>Copyright © 2026 Rittman Analytics.</span>
          <span />
        </div>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <Layout
      noFooter
      title="Wire Framework"
      description="AI-accelerated delivery for data platform engagements — Wire Framework documentation">
      <div className="wireLanding">
        <Nav />
        <Hero />
        <Stats />
        <WhatsNew />
        <HowItRuns />
        <Runtimes />
        <Footer />
      </div>
    </Layout>
  );
}
