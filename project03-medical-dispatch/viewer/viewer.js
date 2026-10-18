'use strict';
(() => {
  const root = document.documentElement;
  const theme = document.getElementById('theme');
  const system = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null;
  let preference = root.dataset.themePreference || 'dark';
  const applyTheme = () => { root.dataset.theme = preference === 'system' ? (system && system.matches ? 'dark' : 'light') : preference; };
  theme.value = preference;
  theme.addEventListener('change', () => {
    preference = theme.value;
    root.dataset.themePreference = preference;
    try { localStorage.setItem('medical-dispatch-theme', preference); } catch (_) {}
    applyTheme();
  });
  if (system) {
    if (system.addEventListener) system.addEventListener('change', applyTheme);
    else if (system.addListener) system.addListener(applyTheme);
  }
  const data = JSON.parse(document.getElementById('evidence-data').textContent);
  const names = {fcfs:'FCFS', edf:'Earliest deadline', milp:'Offline MILP', rolling_milp:'Rolling MILP'};
  const number = (value, digits = 0) => Number(value).toLocaleString('en-US', {minimumFractionDigits:digits, maximumFractionDigits:digits});
  const cell = (value, tag = 'td') => { const element = document.createElement(tag); element.textContent = value; if (tag === 'th') element.scope = 'row'; return element; };
  const row = (values) => { const element = document.createElement('tr'); values.forEach((value, i) => element.append(cell(value, i ? 'td' : 'th'))); return element; };
  const percent = (value) => number(Number(value) * 100, 2) + '%';
  function render(information) {
    const selected = data.baseline.filter(item => item.information === information);
    const outcomes = document.getElementById('outcomes');
    const table = document.getElementById('baseline-table');
    outcomes.replaceChildren(); table.replaceChildren();
    for (const item of selected) {
      const line = document.createElement('div'); line.className = 'outcome-row';
      const label = document.createElement('div'); label.className = 'policy-label'; label.textContent = names[item.policy];
      const bar = document.createElement('div'); bar.className = 'outcome-bar'; bar.setAttribute('role', 'img');
      bar.setAttribute('aria-label', `${names[item.policy]}: ${item.on_time} on time, ${item.late_requests} served late, ${item.rejected} rejected, out of ${item.eligible} eligible requests.`);
      for (const [key, className] of [['on_time', 'on-time'], ['late_requests', 'late'], ['rejected', 'rejected']]) {
        const segment = document.createElement('span'); segment.className = className;
        segment.style.width = `${100 * Number(item[key]) / Number(item.eligible)}%`;
        segment.textContent = item[key]; segment.setAttribute('aria-hidden', 'true'); bar.append(segment);
      }
      line.append(label, bar); outcomes.append(line);
      table.append(row([names[item.policy], `${item.served} / ${item.eligible}`, item.on_time, number(item.lateness_minutes), number(item.objective, 2), item.lower_bound ? number(item.lower_bound, 2) : 'Not claimed', item.relative_gap !== '' ? percent(item.relative_gap) : 'Not claimed']));
    }
    document.getElementById('information-note').textContent = information === 'offline'
      ? 'Offline policies know the full demand fixture at time zero, subject to release constraints. FCFS and EDF use their myopic queue rules; MILP can plan for future releases.'
      : 'Online policies see requests only at release and share the known availability calendar. Rolling MILP commits current starts and preserves executed history. No global online optimum or gap is claimed.';
    const distributionHead = document.getElementById('distribution-head'); distributionHead.replaceChildren();
    ['Group', ...selected.map(item => names[item.policy])].forEach(value => { const th = document.createElement('th'); th.scope = 'col'; th.textContent = value; distributionHead.append(th); });
    const distributionTable = document.getElementById('distribution-table'); distributionTable.replaceChildren();
    const distributions = data.distributions.filter(item => item.information === information);
    const groups = distributions.filter(item => item.policy === selected[0].policy);
    for (const group of groups) {
      const values = selected.map(policy => {
        const item = distributions.find(item => item.policy === policy.policy && item.dimension === group.dimension && item.group === group.group);
        return `${number(Number(item.service_rate) * 100, 1)}% (${item.served}/${item.eligible})`;
      });
      distributionTable.append(row([`${group.dimension === 'region' ? 'Region' : 'Category'}: ${group.group}`, ...values]));
    }
    document.getElementById('tradeoff-text').textContent = information === 'offline'
      ? 'Offline MILP reduces the objective to 1,663 and raises on-time service to 9 requests. Dune’s service rate falls from 60% under both heuristics to 40%; the protected category falls from 60% to 50%. Aggregate improvement does not imply improvement for every group.'
      : 'The online comparison has a different information boundary. Compare each group’s service rate below alongside the 1,793 rolling-MILP objective and its 5 on-time requests. A lower aggregate objective does not guarantee better outcomes for every group.';
    document.getElementById('comparison-status').textContent = `${information === 'offline' ? 'Offline' : 'Online'} baseline comparison displayed for three policies.`;
  }
  document.querySelectorAll('input[name="information"]').forEach(input => input.addEventListener('change', () => { if (input.checked) render(input.value); }));
  const sensitivity = document.getElementById('sensitivity-table');
  for (const item of data.sensitivity.filter(item => item.policy === 'milp')) {
    const policies = data.sensitivity.filter(candidate => candidate.case === item.case);
    const entry = row([item.case.replaceAll('_', ' '), number(policies.find(candidate => candidate.policy === 'fcfs').objective, 2), number(policies.find(candidate => candidate.policy === 'edf').objective, 2), number(item.objective, 2), number(item.lower_bound, 2), percent(item.relative_gap), item.served]);
    if (item.optimal !== 'True') { entry.className = 'limited'; const label = document.createElement('span'); label.className = 'limited-label'; label.textContent = 'Time limit reached'; entry.firstChild.append(label); }
    sensitivity.append(entry);
  }
  const hashes = document.getElementById('source-hashes');
  for (const [file, hash] of Object.entries(data.sources)) { const name = document.createElement('dt'); name.textContent = file; const value = document.createElement('dd'); value.textContent = hash; hashes.append(name, value); }
  render('offline');
})();
