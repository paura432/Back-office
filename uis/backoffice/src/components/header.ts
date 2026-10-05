/**
 * Navigation bar component for TrackFlow Incident Manager.
 */

export function renderNav(currentPath: string): string {
  const links = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/list', label: 'Incidents' },
    { path: '/create', label: 'New Incident' },
    { path: '/inventory/items', label: 'Inventory' },
    { path: '/inventory/low-stock', label: 'Low Stock' },
  ];
  const items = links.map((l) => {
    const active = currentPath.startsWith(l.path) ? ' active' : '';
    return `<a href="${l.path}" class="${active}" data-nav>${l.label}</a>`;
  }).join('');
  return `
    <nav class="nav-links">
      <strong style="color:#2563eb;margin-right:0.75rem">TrackFlow</strong>
      ${items}
    </nav>`;
}

export function renderHeader(title: string): string {
  return `<header style="padding:1rem 1rem 0.5rem"><h1>${title}</h1></header>`;
}