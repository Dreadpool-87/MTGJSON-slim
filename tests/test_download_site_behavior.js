'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../docs/index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
const prefix = 'https://github.com/Dreadpool-87/MTGJSON-slim/releases/download/test/';
function element(extra = {}) {
  return {href: null, hidden: false, disabled: false, textContent: '',
    classList: {add() {}}, addEventListener() {}, ...extra};
}
function release() {
  const assets = [];
  for (const suffix of ['.sqlite', '.sqlite.xz', '.sqlite.zst', '.sqlite.zip']) {
    const name = 'AllPrintings-slim-test' + suffix;
    assets.push({name, size: 100, browser_download_url: prefix + name});
    assets.push({name: name + '.sha256', size: 64, browser_download_url: prefix + name + '.sha256'});
  }
  return {name: 'Verified fixture', tag_name: 'slim-test', draft: false, assets};
}
async function render(fixture) {
  const ids = Object.fromEntries(['status', 'status-dot', 'download', 'checksum', 'file-note',
    ...['sqlite', 'xz', 'zst', 'zip'].map(x => 'size-' + x)].map(id => [id, element()]));
  const inputs = ['xz', 'zst', 'zip', 'sqlite'].map((value, i) => element({value, checked: i === 0}));
  const document = {getElementById: id => ids[id], querySelectorAll: selector => {
    assert.equal(selector, 'input[name="format"]'); return inputs;
  }};
  vm.runInNewContext(script, {document, fetch: async () => ({ok: true, json: async () => fixture})});
  await new Promise(resolve => setImmediate(resolve));
  return {ids, inputs};
}
test('complete release enables four matching download/checksum choices', async () => {
  const {ids, inputs} = await render(release());
  assert.equal(inputs.filter(x => !x.disabled).length, 4);
  assert.equal(ids.checksum.href, ids.download.href + '.sha256');
  assert.equal(ids.checksum.hidden, false);
});
test('no checksum sidecars disables every SQLite format', async () => {
  const r = release(); r.assets = r.assets.filter(a => !a.name.endsWith('.sha256'));
  const {ids, inputs} = await render(r);
  assert.equal(inputs.filter(x => !x.disabled).length, 0);
  assert.equal(ids.checksum.hidden, true);
});
test('missing selected checksum disables only that format and selects a verified alternative', async () => {
  const r = release(); r.assets = r.assets.filter(a => !a.name.endsWith('.sqlite.xz.sha256'));
  const {ids, inputs} = await render(r);
  assert.equal(inputs.find(x => x.value === 'xz').disabled, true);
  assert.equal(inputs.filter(x => !x.disabled).length, 3);
  assert.equal(ids.download.href, prefix + 'AllPrintings-slim-test.sqlite.zst');
  assert.equal(ids.checksum.href, ids.download.href + '.sha256');
});
test('a checksum outside the approved release prefix cannot enable a format', async () => {
  const r = release();
  for (const a of r.assets) if (a.name.endsWith('.sha256')) a.browser_download_url = 'https://example.com/untrusted';
  const {inputs} = await render(r);
  assert.equal(inputs.filter(x => !x.disabled).length, 0);
});
