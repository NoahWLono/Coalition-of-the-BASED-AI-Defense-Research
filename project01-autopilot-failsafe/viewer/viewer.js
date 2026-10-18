(() => {
  'use strict';
  const theme = document.getElementById('theme');
  theme.value = window.flightLabTheme.get();
  theme.addEventListener('change', () => window.flightLabTheme.set(theme.value));
  document.getElementById('theme-control').hidden = false;
  const release = document.getElementById('release');
  const outcome = document.getElementById('outcome');
  const search = document.getElementById('search');
  const rows = [...document.querySelectorAll('#run-table tbody tr')];
  const count = document.getElementById('run-count');
  const empty = document.getElementById('empty');
  const update = () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      const match = (!release.value || row.dataset.release === release.value) &&
        (!outcome.value || row.dataset.outcome === outcome.value) &&
        (!query || row.textContent.toLocaleLowerCase().includes(query));
      row.hidden = !match;
      if (match) visible += 1;
    });
    count.textContent = `${visible} of ${rows.length} original runs shown`;
    empty.hidden = visible !== 0;
  };
  release.addEventListener('change', update);
  outcome.addEventListener('change', update);
  search.addEventListener('input', update);
  document.getElementById('reset').addEventListener('click', () => {
    release.value = ''; outcome.value = ''; search.value = ''; update(); search.focus();
  });
  document.getElementById('filters').hidden = false;
  update();
})();
