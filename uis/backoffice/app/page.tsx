type Team = { icon: string; title: string; detail: string; status: string; tone: 'green' | 'amber' | 'blue' };

const teams: Team[] = [
  { icon: '▤', title: 'Warehouse Operations', detail: 'Inventory visibility · Los Angeles + Zaragoza', status: 'NEEDS UNIFIED STOCK', tone: 'amber' },
  { icon: '⇢', title: 'Last Mile / Carriers', detail: '8 carrier partners across both markets', status: 'MANUAL TRACKING', tone: 'blue' },
  { icon: '↶', title: 'Reverse Logistics', detail: 'Returns reviewed by the team', status: 'HUMAN REVIEW', tone: 'amber' },
  { icon: '◎', title: 'Customer Experience', detail: 'Brand and recipient support · 15 agents', status: 'TICKETS NOT UNIFIED', tone: 'green' },
  { icon: '⌘', title: 'Technology', detail: 'Zaragoza · team of 7', status: 'TELEMETRY NEEDED', tone: 'blue' },
];

const priorities = [
  { id: '01', title: 'Unify inventory visibility', detail: 'Bring stock from both warehouse systems into a shared operational view.', area: 'WAREHOUSE OPERATIONS' },
  { id: '02', title: 'Connect carrier tracking', detail: 'Reduce the need to check multiple carrier portals shipment by shipment.', area: 'LAST MILE / CARRIERS' },
  { id: '03', title: 'Standardize return decisions', detail: 'Make return review more consistent while keeping the current human review in view.', area: 'REVERSE LOGISTICS' },
  { id: '04', title: 'Centralize service signals', detail: 'Give the technology team a clearer view when an endpoint or integration fails.', area: 'TECHNOLOGY' },
];

function TeamCard({ icon, title, detail, status, tone }: Team) {
  return <article className="team-card"><div className={`team-icon team-icon--${tone}`} aria-hidden="true">{icon}</div><div className="team-info"><h3>{title}</h3><p>{detail}</p></div><span className={`status-pill status-pill--${tone}`}><i></i>{status}</span><span className="card-chevron" aria-hidden="true">↗</span></article>;
}

function PriorityRow({ id, title, detail, area }: (typeof priorities)[number]) {
  return <article className="priority-row"><span className="priority-id">{id}</span><div className="priority-copy"><h3>{title}</h3><p>{detail}</p></div><span className="priority-area">{area}</span><span className="priority-arrow" aria-hidden="true">↗</span></article>;
}

export default function Backoffice() {
  return (
    <div id="app">
      <div className="app-shell">
        <aside className="sidebar">
          <a className="brand" href="#home" aria-label="TrackFlow operations home"><span className="brand-symbol"><i></i><i></i><i></i></span><span>trackflow<span className="brand-period">.</span></span></a>
          <div className="workspace-label">WORKSPACE</div><div className="workspace-select"><span className="workspace-avatar">T</span><span><b>TrackFlow</b><small>Operations workspace</small></span><span className="select-caret">⌄</span></div>
          <div className="sidebar-label">OVERVIEW</div><nav className="sidebar-nav" aria-label="Backoffice navigation"><a className="nav-item nav-item--active" href="#home"><span>▦</span>Dashboard</a><a className="nav-item" href="#warehouses"><span>▤</span>Warehouse operations</a><a className="nav-item" href="#carriers"><span>⇢</span>Last mile &amp; carriers</a><a className="nav-item" href="#returns"><span>↶</span>Reverse logistics</a><a className="nav-item" href="#customer-experience"><span>◎</span>Customer experience</a><a className="nav-item" href="#technology"><span>⌘</span>Technology</a></nav>
          <div className="sidebar-bottom"><div className="sidebar-label">LOCATIONS</div><div className="location-link"><span className="location-dot location-dot--la"></span>Los Angeles<span className="location-code">US</span></div><div className="location-link"><span className="location-dot location-dot--zg"></span>Zaragoza<span className="location-code">ES</span></div><div className="sidebar-profile"><span className="profile-avatar">TF</span><span><b>TrackFlow Team</b><small>Internal workspace</small></span><span className="profile-menu">···</span></div></div>
        </aside>
        <main className="main-panel" id="home">
          <header className="topbar"><div className="breadcrumb"><span>TrackFlow</span><i>/</i><b>Dashboard</b></div><div className="topbar-actions"><span className="context-badge"><i></i>CONTEXT OVERVIEW</span><button className="icon-button" aria-label="Notifications">♧<span className="notification-dot"></span></button><span className="top-avatar">TF</span></div></header>
          <div className="dashboard-content">
            <section className="welcome-row"><div><p className="date-line"><span className="date-square">◷</span> OPERATIONS OVERVIEW <span className="date-divider">/</span> UNITED STATES + SPAIN</p><h1>Operations Backoffice</h1><p className="welcome-copy">A shared view of the teams and operational priorities shaping TrackFlow.</p></div><div className="welcome-meta"><span className="meta-label">OPERATING LOCATIONS</span><div className="meta-locations"><span><i className="location-dot location-dot--la"></i>Los Angeles</span><span><i className="location-dot location-dot--zg"></i>Zaragoza</span></div></div></section>
            <section className="notice-banner"><span className="notice-icon">i</span><p><b>Operational context, not live telemetry.</b> This dashboard summarizes needs documented in the company brief. No live warehouse or carrier data is connected.</p><span className="notice-ref">SOURCE: CONTEXT.MD</span></section>
            <section className="overview-heading"><div><p className="section-label">TEAMS &amp; SYSTEMS</p><h2>Across the operation</h2></div><span className="overview-count">05 <i>AREAS</i></span></section>
            <section className="team-grid" aria-label="TrackFlow operational teams">{teams.map((team) => <TeamCard key={team.title} {...team} />)}</section>
            <section className="lower-grid"><div className="priorities-panel"><div className="panel-heading"><div><p className="section-label">WHAT NEEDS ATTENTION</p><h2>Operational priorities</h2></div><span className="priority-count">FROM COMPANY BRIEF</span></div><div className="priority-list">{priorities.map((priority) => <PriorityRow key={priority.id} {...priority} />)}</div><div className="panel-footnote"><span className="footnote-mark">↗</span> Priorities describe documented needs; they are not live incidents or assigned work.</div></div><aside className="locations-panel"><div className="panel-heading panel-heading--compact"><div><p className="section-label">TWO MARKETS</p><h2>Connected by design</h2></div><span className="globe-icon">◎</span></div><div className="location-card"><div className="location-card__top"><span className="location-flag location-flag--us">US</span><span className="location-region">NORTH AMERICA</span></div><h3>Los Angeles</h3><p>Warehouse operations<br />Company headquarters</p><span className="location-card__line"></span></div><div className="location-card"><div className="location-card__top"><span className="location-flag location-flag--es">ES</span><span className="location-region">EUROPE</span></div><h3>Zaragoza</h3><p>Warehouse operations<br />Technology office</p><span className="location-card__line"></span></div><div className="location-note"><span>↗</span> Two warehouse systems. No shared real-time inventory view today.</div></aside></section>
            <footer className="dashboard-footer"><span>TRACKFLOW OPERATIONS WORKSPACE</span><span>Based on the company context · No live operational data</span><span>LOS ANGELES <i>·</i> ZARAGOZA</span></footer>
          </div>
        </main>
      </div>
    </div>
  );
}