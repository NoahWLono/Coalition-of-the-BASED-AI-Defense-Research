// Loaded as a blocking classic script before CSS so the saved theme applies before paint.
(() => {
  const storageKey = 'ground-control-lab-theme';
  const choices = ['dark', 'light', 'system'];
  let preference = 'dark';
  try {
    const saved = window.localStorage.getItem(storageKey);
    if (choices.includes(saved)) preference = saved;
  } catch { /* A blocked storage area must not prevent local replay. */ }

  const system = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null;
  const apply = () => {
    document.documentElement.dataset.theme = preference === 'system'
      ? (system ? (system.matches ? 'dark' : 'light') : 'dark')
      : preference;
  };
  apply();
  const followSystem = () => { if (preference === 'system') apply(); };
  if (system?.addEventListener) system.addEventListener('change', followSystem);
  else if (system?.addListener) system.addListener(followSystem);

  document.addEventListener('DOMContentLoaded', () => {
    const control = document.getElementById('theme');
    if (!control) return;
    control.value = preference;
    control.addEventListener('change', () => {
      if (!choices.includes(control.value)) return;
      preference = control.value;
      apply();
      try { window.localStorage.setItem(storageKey, preference); }
      catch { /* The selected theme still works for this page session. */ }
    });
  }, { once: true });
})();
