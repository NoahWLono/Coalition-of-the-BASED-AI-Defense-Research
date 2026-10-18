(() => {
  'use strict';
  const key = 'geolab-theme';
  const allowed = ['dark', 'light', 'system'];
  let preference = 'dark';
  try {
    const saved = localStorage.getItem(key);
    if (allowed.includes(saved)) preference = saved;
  } catch (_) { /* The theme still works when browser storage is disabled. */ }
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  function apply() {
    document.documentElement.dataset.theme = preference === 'system'
      ? (system.matches ? 'dark' : 'light') : preference;
  }
  apply();
  system.addEventListener('change', () => { if (preference === 'system') apply(); });
  document.addEventListener('DOMContentLoaded', () => {
    const control = document.getElementById('theme');
    control.value = preference;
    control.addEventListener('change', () => {
      preference = allowed.includes(control.value) ? control.value : 'dark';
      try { localStorage.setItem(key, preference); } catch (_) { /* Optional persistence. */ }
      apply();
    });
  });
})();
