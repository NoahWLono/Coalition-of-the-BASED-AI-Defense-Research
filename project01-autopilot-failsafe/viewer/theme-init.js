(() => {
  'use strict';
  const key = 'failsafelab-theme';
  const modes = new Set(['dark', 'light', 'system']);
  const media = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  let preference = 'dark';
  try {
    const saved = window.localStorage.getItem(key);
    if (modes.has(saved)) preference = saved;
  } catch (_) { /* Storage can be unavailable for local files or private contexts. */ }
  const apply = () => {
    const theme = preference === 'system' ? (media && media.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  };
  apply();
  const systemChanged = () => { if (preference === 'system') apply(); };
  if (media && media.addEventListener) media.addEventListener('change', systemChanged);
  else if (media && media.addListener) media.addListener(systemChanged);
  window.flightLabTheme = {
    get: () => preference,
    set: (value) => {
      if (!modes.has(value)) return;
      preference = value;
      apply();
      try { window.localStorage.setItem(key, value); } catch (_) { /* Keep the session choice. */ }
    }
  };
})();
