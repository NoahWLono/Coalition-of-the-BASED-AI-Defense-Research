/* Appearance only: never reads evidence, changes records, or contacts a server. */
(() => {
  'use strict';
  const key = 'cedar-theme';
  const allowed = new Set(['dark', 'light', 'system']);
  const root = document.documentElement;
  let preference = 'dark';
  let system = null;
  try { system = window.matchMedia('(prefers-color-scheme: dark)'); } catch (_) {}
  try {
    const saved = localStorage.getItem(key);
    if (allowed.has(saved)) preference = saved;
  } catch (_) { /* Restricted file origins/private storage keep an in-memory choice. */ }

  function apply() {
    const resolved = preference === 'system' ? (system?.matches ? 'dark' : 'light') : preference;
    root.dataset.theme = resolved;
    root.dataset.themePreference = preference;
    root.style.colorScheme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = resolved === 'dark' ? '#0d1822' : '#f3f6f8';
    document.querySelectorAll('[data-theme-control]').forEach(control => { control.value = preference; });
  }
  // This script is deliberately synchronous in the head, before styles and paint.
  apply();
  if (system?.addEventListener) system.addEventListener('change', () => { if (preference === 'system') apply(); });
  else if (system?.addListener) system.addListener(() => { if (preference === 'system') apply(); });
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = allowed.has(event.newValue) ? event.newValue : 'dark';
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.querySelectorAll('[data-theme-control]').forEach(control => {
      control.addEventListener('change', () => {
        preference = allowed.has(control.value) ? control.value : 'dark';
        try { localStorage.setItem(key, preference); } catch (_) {}
        apply();
      });
    });
  });
})();
