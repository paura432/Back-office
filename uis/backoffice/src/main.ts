import './styles.css';

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

function teamCard(team: Team): string {
  return `<article class="team-card"><div class="team-icon team-icon--${team.tone}" aria-hidden="true">${team.icon}</div><div class="team-info"><h3>${team.title}</h3><p>${team.detail}</p></div><span class="status-pill status-pill--${team.tone}"><i></i>${team.status}</span><span class="card-chevron" aria-hidden="true">↗</span></article>`;
}

function priorityRow(item: (typeof priorities)[number]): string {
  return `<article class="priority-row"><span class="priority-id">${item.id}</span><div class="priority-copy"><h3>${item.title}</h3><p>${item.detail}</p></div><span class="priority-area">${item.area}</span><span class="priority-arrow" aria-hidden="true">↗</span></article>`;
}

function renderDashboard(): string {
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <a class="brand" href="#home" aria-label="TrackFlow operations home"><span class="brand-symbol"><i></i><i></i><i></i></span><span>trackflow<span class="brand-period">.</span></span></a>
        <div class="workspace-label">WORKSPACE</div><div class="workspace-select"><span class="workspace-avatar">T</span><span><b>TrackFlow</b><small>Operations workspace</small></span><span class="select-caret">⌄</span></div>
        <div class="sidebar-label">OVERVIEW</div><nav class="sidebar-nav" aria-label="Backoffice navigation"><a class="nav-item nav-item--active" href="#home"><span>▦</span>Dashboard</a><a class="nav-item" href="#warehouses"><span>▤</span>Warehouse operations</a><a class="nav-item" href="#carriers"><span>⇢</span>Last mile & carriers</a><a class="nav-item" href="#returns"><span>↶</span>Reverse logistics</a><a class="nav-item" href="#customer-experience"><span>◎</span>Customer experience</a><a class="nav-item" href="#technology"><span>⌘</span>Technology</a></nav>
        <div class="sidebar-bottom"><div class="sidebar-label">LOCATIONS</div><div class="location-link"><span class="location-dot location-dot--la"></span>Los Angeles<span class="location-code">US</span></div><div class="location-link"><span class="location-dot location-dot--zg"></span>Zaragoza<span class="location-code">ES</span></div><div class="sidebar-profile"><span class="profile-avatar">TF</span><span><b>TrackFlow Team</b><small>Internal workspace</small></span><span class="profile-menu">···</span></div></div>
      </aside>
      <main class="main-panel" id="home">
        <header class="topbar"><div class="breadcrumb"><span>TrackFlow</span><i>/</i><b>Dashboard</b></div><div class="topbar-actions"><span class="context-badge"><i></i>CONTEXT OVERVIEW</span><button class="icon-button" aria-label="Notifications">♧<span class="notification-dot"></span></button><span class="top-avatar">TF</span></div></header>
        <div class="dashboard-content">
          <section class="welcome-row"><div><p class="date-line"><span class="date-square">◷</span> OPERATIONS OVERVIEW <span class="date-divider">/</span> UNITED STATES + SPAIN</p><h1>Operations Backoffice</h1><p class="welcome-copy">A shared view of the teams and operational priorities shaping TrackFlow.</p></div><div class="welcome-meta"><span class="meta-label">OPERATING LOCATIONS</span><div class="meta-locations"><span><i class="location-dot location-dot--la"></i>Los Angeles</span><span><i class="location-dot location-dot--zg"></i>Zaragoza</span></div></div></section>
          <section class="notice-banner"><span class="notice-icon">i</span><p><b>Operational context, not live telemetry.</b> This dashboard summarizes needs documented in the company brief. No live warehouse or carrier data is connected.</p><span class="notice-ref">SOURCE: CONTEXT.MD</span></section>
          <section class="overview-heading"><div><p class="section-label">TEAMS & SYSTEMS</p><h2>Across the operation</h2></div><span class="overview-count">05 <i>AREAS</i></span></section>
          <section class="team-grid" aria-label="TrackFlow operational teams">${teams.map(teamCard).join('')}</section>
          <section class="lower-grid"><div class="priorities-panel"><div class="panel-heading"><div><p class="section-label">WHAT NEEDS ATTENTION</p><h2>Operational priorities</h2></div><span class="priority-count">FROM COMPANY BRIEF</span></div><div class="priority-list">${priorities.map(priorityRow).join('')}</div><div class="panel-footnote"><span class="footnote-mark">↗</span> Priorities describe documented needs; they are not live incidents or assigned work.</div></div><aside class="locations-panel"><div class="panel-heading panel-heading--compact"><div><p class="section-label">TWO MARKETS</p><h2>Connected by design</h2></div><span class="globe-icon">◎</span></div><div class="location-card"><div class="location-card__top"><span class="location-flag location-flag--us">US</span><span class="location-region">NORTH AMERICA</span></div><h3>Los Angeles</h3><p>Warehouse operations<br>Company headquarters</p><span class="location-card__line"></span></div><div class="location-card"><div class="location-card__top"><span class="location-flag location-flag--es">ES</span><span class="location-region">EUROPE</span></div><h3>Zaragoza</h3><p>Warehouse operations<br>Technology office</p><span class="location-card__line"></span></div><div class="location-note"><span>↗</span> Two warehouse systems. No shared real-time inventory view today.</div></aside></section>
          <footer class="dashboard-footer"><span>TRACKFLOW OPERATIONS WORKSPACE</span><span>Based on the company context · No live operational data</span><span>LOS ANGELES <i>·</i> ZARAGOZA</span></footer>
        </div>
      </main>
    </div>
  `;
}

const root = document.querySelector<HTMLDivElement>('#app');
if (!root) throw new Error('App root #app was not found');
root.innerHTML = renderDashboard();
