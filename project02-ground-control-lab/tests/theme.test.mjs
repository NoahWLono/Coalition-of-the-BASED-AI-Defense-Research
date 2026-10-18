import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

// Browser APIs are bounded adapters here; browser rendering is checked separately.
async function loadTheme({ saved = null, darkSystem = false, blockedStorage = false, media = true } = {}) {
  const source = await readFile(new URL('../src/theme.mjs', import.meta.url), 'utf8').catch(error => {
    if (error.code === 'ENOENT') return '';
    throw error;
  });
  const root = { dataset: {} };
  const handlers = {};
  const select = { value: '', addEventListener: (type, callback) => { handlers[type] = callback; } };
  const document = { documentElement: root, getElementById: () => select, addEventListener: (type, callback) => { handlers[type] = callback; } };
  let stored = saved;
  const localStorage = {
    getItem() { if (blockedStorage) throw new Error('Storage disabled'); return stored; },
    setItem(key, value) { if (blockedStorage) throw new Error('Storage disabled'); stored = value; }
  };
  let mediaChange;
  const query = { matches: darkSystem, addEventListener: (type, callback) => { mediaChange = callback; } };
  const window = { localStorage, ...(media ? { matchMedia: () => query } : {}) };
  runInNewContext(source, { document, window });
  return {
    root, select, get stored() { return stored; },
    ready() { handlers.DOMContentLoaded?.(); },
    choose(value) { select.value = value; handlers.change?.(); },
    system(value) { query.matches = value; mediaChange?.({ matches: value }); }
  };
}

test('new visits use dark before controls are ready, regardless of a light system preference', async () => {
  const page = await loadTheme();
  assert.equal(page.root.dataset.theme, 'dark');
  page.ready();
  assert.equal(page.select.value, 'dark');
});

test('saved light preference is applied before controls are ready and a new choice persists', async () => {
  const page = await loadTheme({ saved: 'light', darkSystem: true });
  assert.equal(page.root.dataset.theme, 'light');
  page.ready();
  assert.equal(page.select.value, 'light');
  page.choose('dark');
  assert.equal(page.root.dataset.theme, 'dark');
  assert.equal(page.stored, 'dark');
});

test('system theme follows preference changes only while system is selected', async () => {
  const page = await loadTheme({ saved: 'system' });
  assert.equal(page.root.dataset.theme, 'light');
  page.ready();
  assert.equal(page.select.value, 'system');
  page.system(true);
  assert.equal(page.root.dataset.theme, 'dark');
  page.choose('light');
  page.system(true);
  assert.equal(page.root.dataset.theme, 'light');
  page.choose('system');
  assert.equal(page.root.dataset.theme, 'dark');
  assert.equal(page.stored, 'system');
});

test('unavailable storage does not prevent selecting or following a theme', async () => {
  const page = await loadTheme({ blockedStorage: true });
  assert.equal(page.root.dataset.theme, 'dark');
  page.ready();
  page.choose('light');
  assert.equal(page.root.dataset.theme, 'light');
  page.choose('system');
  page.system(true);
  assert.equal(page.root.dataset.theme, 'dark');
});

test('invalid saved values and missing media support have a usable dark fallback', async () => {
  const invalid = await loadTheme({ saved: 'unexpected' });
  assert.equal(invalid.root.dataset.theme, 'dark');
  const noMedia = await loadTheme({ saved: 'system', media: false });
  assert.equal(noMedia.root.dataset.theme, 'dark');
  noMedia.ready();
  noMedia.choose('light');
  assert.equal(noMedia.root.dataset.theme, 'light');
});
