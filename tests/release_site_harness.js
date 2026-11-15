'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = () => fs.readFileSync(path.join(__dirname, '../docs/release-downloads.js'), 'utf8');
const repo = 'https://github.com/Dreadpool-87/MTGJSON-slim';
const api = 'https://api.github.com/repos/Dreadpool-87/MTGJSON-slim/releases?per_page=100';
const formats = ['xz','zst','zip','raw'];
function element(extra = {}) {
  return {href: null, hidden: false, disabled: true, textContent: '', dataset: {},
    classList: {add(name) {this[name] = true;}, contains(name) {return !!this[name];}}, addEventListener(event, callback) {this[event] = callback;},
    removeAttribute(name) {delete this[name];}, querySelector() {return this.span ||= element();}, ...extra};
}
function fixture(family, date = '2026-11-14T12:00:00Z', version = '5.3.0+20261114') {
  const tag = {sqlite: 'slim-', json: 'json-slim-', atomic: 'atomic-slim-'}[family] + version.replace('+', '-');
  const stem = family === 'atomic' ? `AtomicCards-slim-${version}-atomic-b1.json` :
    `AllPrintings-slim-${version}-${family === 'sqlite' ? 'profile-2.3.sqlite' : 'json-deckbuilding-1.0.json'}`;
  const asset = name => ({name, size: 100, state: 'uploaded', content_type: 'application/octet-stream',
    browser_download_url: `${repo}/releases/download/${tag}/${encodeURIComponent(name)}`});
  const assets = ['', '.xz', '.zst', '.zip'].flatMap(ext => [asset(stem + ext), asset(stem + ext + '.sha256')]);
  assets.push(asset({sqlite: 'manifest.json', json: 'json-manifest.json', atomic: 'atomic-manifest.json'}[family]));
  return {name: family, tag_name: tag, published_at: date, html_url: `${repo}/releases/tag/${tag}`, draft: false, prerelease: false, assets};
}
async function render(pages, options = {}) {
  const ids = Object.fromEntries(['status','status-dot','download','checksum','file-note',
    ...['json','atomic'].flatMap(f => [f+'-status',f+'-status-dot',f+'-download',f+'-checksum',f+'-file-note']),
    'sqlite-release','json-release','atomic-release','sqlite-manifest','json-manifest','atomic-manifest',
    ...['sqlite','xz','zst','zip'].map(x => 'size-' + x),
    ...['json','atomic'].flatMap(f => formats.map(fmt => f+'-size-'+fmt))].map(id => [id, element()]));
  const inputs = ['xz','zst','zip','sqlite'].map((value,i) => element({value, checked: i === 0}));
  const jsonInputs = formats.map((value,i) => element({value, checked: i === 0}));
  const atomicInputs = formats.map((value,i) => element({value, checked: i === 0}));
  const selectors = {'input[name="format"]': inputs, 'input[name="json-format"]': jsonInputs,
    'input[name="atomic-format"]': atomicInputs};
  const requests = []; let aborts = 0; let done;
  const finished = new Promise(resolve => {done = resolve;});
  // Signal completion on the last panel's live-region update; no wall-clock sleeps.
  Object.defineProperty(ids['atomic-status'], 'textContent', {get() {return this.text || '';}, set(v) {this.text = v; done();}});
  const document = {getElementById: id => {assert.ok(ids[id], id); return ids[id];}, querySelectorAll: selector => {assert.ok(selectors[selector], selector); return selectors[selector];}};
  const fetch = async (url, init) => {
    requests.push(url); assert.equal(init.redirect, 'error'); assert.ok(init.signal);
    init.signal.addEventListener('abort', () => aborts++);
    const page = pages[requests.length - 1];
    if (!page) throw new Error('Unexpected request');
    if (page.hang) return new Promise(() => {});
    if (page.network) throw new Error('offline');
    return {ok: !page.code || page.code === 200, status: page.code || 200,
      headers: {get: () => page.link || null}, json: async () => {if (page.invalid) throw new Error('JSON'); return page.data;}};
  };
  vm.runInNewContext(source(), {document, fetch, URL, AbortController, Date, Set, Map, Promise,
    setTimeout: options.timeout ? callback => setTimeout(callback, 5) : setTimeout, clearTimeout});
  await finished;
  // Compatibility snapshots are created by changing the real radio controls.
  // They verify the single download/checksum CTA for every selectable format,
  // not a fictional set of independent download anchors.
  const snapshot = family => {
    const group = family === 'json' ? jsonInputs : atomicInputs;
    const saved = group.map(item => item.checked);
    const output = group.map(input => {
      group.forEach(item => {item.checked = item === input;});
      input.change();
      return {href: input.disabled ? null : ids[family+'-download'].href,
        checksum: input.disabled || ids[family+'-checksum'].hidden ? null : ids[family+'-checksum'].href};
    });
    group.forEach((item,i) => {item.checked = saved[i];});
    group[0].change();
    return output;
  };
  const jsonPairs = snapshot('json'), atomicPairs = snapshot('atomic');
  return {ids, inputs, jsonInputs, atomicInputs,
    json:jsonPairs.map(x=>({href:x.href})), jsonSha:jsonPairs.map(x=>({href:x.checksum})),
    atomic:atomicPairs.map(x=>({href:x.href})), atomicSha:atomicPairs.map(x=>({href:x.checksum})),
    requests, get aborts() {return aborts;}};

}

module.exports = {render, fixture, api};
