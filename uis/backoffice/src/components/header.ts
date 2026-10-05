/**
 * Navigation bar component for TrackFlow Incident Manager.
 */

export function renderNav(currentPath: string, lowStockCount: number = 0): string {
  const links: Array<{ path: string; label: string; badge?: number }> = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/list', label: 'Incidents' },
    { path: '/create', label: 'New Incident' },
    { path: '/inventory/items', label: 'Inventory' },
    { path: '/inventory/low-stock', label: 'Low Stock', badge: lowStockCount },
  ];
  const items = links.map((l) => {
    const active = currentPath.startsWith(l.path) ? ' active' : '';
    const badge = l.badge && l.badge > 0 ? ` <span class="badge" style="background:#dc2626;color:#fff;font-size:0.7rem">${l.badge}</span>` : '';
    return `<a href="${l.path}" class="${active}" data-nav>${l.label}${badge}</a>`;
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