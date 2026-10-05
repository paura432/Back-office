/**
 * Main entry point for TrackFlow Incident Manager Backoffice.
 * Simple client-side router that renders pages into #app.
 */

import { renderDashboard } from './pages/dashboard.ts';
import { renderList } from './pages/list.ts';
import { renderCreate, handleCreateSubmit } from './pages/create.ts';
import { renderDetail, handleTransitionClick } from './pages/detail.ts';
import { renderEdit, handleEditSubmit } from './pages/edit.ts';
import { renderInventoryDashboard } from './pages/inventory-dashboard.ts';
import { renderInventoryList } from './pages/inventory-list.ts';
import { renderInventoryCreate, handleInventoryCreateSubmit } from './pages/inventory-create.ts';
import { renderInventoryEdit, handleInventoryEditSubmit } from './pages/inventory-edit.ts';
import { renderInventoryDetail, handleInventoryDeleteClick } from './pages/inventory-detail.ts';
import { renderInventoryLowStock } from './pages/inventory-low-stock.ts';
import { handleMovementSubmit } from './pages/inventory-movement.ts';

// ──────────────────────── Router ────────────────────────

async function route(path: string, search: string) {
  const params = new URLSearchParams(search);
  const app = document.getElementById('app')!;
  app.innerHTML = '<div class="loading">Loading…</div>';

  try {
    let html: string;
    if (path === '/' || path === '/dashboard') {
      html = await renderDashboard();
    } else if (path === '/list') {
      html = await renderList(params);
    } else if (path === '/create') {
      html = renderCreate();
    } else if (path === '/detail') {
      const id = params.get('id');
      if (!id) { html = '<div class="error-box">Missing id parameter</div>'; } else { html = await renderDetail(id); }
    } else if (path === '/edit') {
      const id = params.get('id');
      if (!id) { html = '<div class="error-box">Missing id parameter</div>'; } else { html = await renderEdit(id); }
    } else if (path === '/inventory') {
      html = await renderInventoryDashboard();
    } else if (path === '/inventory/items') {
      html = await renderInventoryList(params);
    } else if (path === '/inventory/create') {
      html = renderInventoryCreate();
    } else if (path === '/inventory/detail') {
      const id = params.get('id');
      if (!id) { html = '<div class="error-box">Missing id parameter</div>'; } else { html = await renderInventoryDetail(id); }
    } else if (path === '/inventory/edit') {
      const id = params.get('id');
      if (!id) { html = '<div class="error-box">Missing id parameter</div>'; } else { html = await renderInventoryEdit(id); }
    } else if (path === '/inventory/low-stock') {
      html = await renderInventoryLowStock();
    } else {
      html = '<div class="error-box">Page not found</div>';
    }
    app.innerHTML = html;
    attachEventListeners();
  } catch (err) {
    app.innerHTML = `<div class="error-box">${escape(String(err))}</div>`;
  }
}

function escape(s: string): string {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}

// ──────────────────────── Event wiring ────────────────────────

function attachEventListeners() {
  // Navigation links
  for (const a of document.querySelectorAll('a[data-nav]')) {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const href = (a as HTMLAnchorElement).getAttribute('href') || '/dashboard';
      navigate(href);
    });
  }

  // Navigation forms (filter submit) — incidents
  for (const f of document.querySelectorAll('form[data-nav-form]')) {
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      const form = f as HTMLFormElement;
      const fd = new FormData(form);
      const params = new URLSearchParams();
      for (const [k, v] of fd.entries()) {
        if (v) params.set(k, v as string);
      }
      navigate(`/list?${params.toString()}`);
    });
  }

  // Navigation forms (filter submit) — inventory
  for (const f of document.querySelectorAll('form[data-nav-form-inventory]')) {
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      const form = f as HTMLFormElement;
      const fd = new FormData(form);
      const params = new URLSearchParams();
      for (const [k, v] of fd.entries()) {
        if (v) params.set(k, v as string);
      }
      navigate(`/inventory/items?${params.toString()}`);
    });
  }

  // Create form
  const createForm: HTMLElement | null = document.querySelector('form[data-form="create"]');
  if (createForm) {
    createForm.addEventListener('submit', ((e: SubmitEvent) => handleCreateSubmit(e)) as unknown as EventListener);
  }

  // Edit form
  const editForm: HTMLElement | null = document.querySelector('form[data-form="edit"]');
  if (editForm) {
    editForm.addEventListener('submit', ((e: SubmitEvent) => handleEditSubmit(e)) as unknown as EventListener);
  }

  // Transition buttons
  for (const btn of document.querySelectorAll('[data-action="transition"]')) {
    btn.addEventListener('click', ((e: MouseEvent) => handleTransitionClick(e)) as EventListener);
  }

  // Inventory create form
  const invCreateForm: HTMLElement | null = document.querySelector('form[data-form="inventory-create"]');
  if (invCreateForm) {
    invCreateForm.addEventListener('submit', ((e: SubmitEvent) => handleInventoryCreateSubmit(e)) as unknown as EventListener);
  }

  // Inventory edit form
  const invEditForm: HTMLElement | null = document.querySelector('form[data-form="inventory-edit"]');
  if (invEditForm) {
    invEditForm.addEventListener('submit', ((e: SubmitEvent) => handleInventoryEditSubmit(e)) as unknown as EventListener);
  }

  // Inventory delete buttons
  for (const btn of document.querySelectorAll('[data-action="inventory-delete"]')) {
    btn.addEventListener('click', ((e: MouseEvent) => handleInventoryDeleteClick(e)) as EventListener);
  }

  // Inventory movement form
  const movementForm: HTMLElement | null = document.querySelector('form[data-form="movement"]');
  if (movementForm) {
    movementForm.addEventListener('submit', ((e: SubmitEvent) => handleMovementSubmit(e)) as unknown as EventListener);
  }
}

// ──────────────────────── Navigation ────────────────────────

function navigate(path: string) {
  const [p, q] = path.split('?', 2);
  history.pushState(null, '', path);
  route(p, q || '');
}

// ──────────────────────── Init ────────────────────────

// Listen for programmatic navigation
window.addEventListener('navigate', ((e: CustomEvent) => {
  navigate(e.detail);
}) as EventListener);

// Initial render
const initialPath = window.location.pathname || '/dashboard';
const initialSearch = window.location.search.slice(1);
route(initialPath, initialSearch);