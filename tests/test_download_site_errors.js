'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../docs/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
async function status(family, response) {
  const target = {textContent: ''};
  const document = {getElementById: () => target, querySelectorAll: selector => selector.includes('extension') ? [{dataset: {jsonExtension: '.json', atomicExtension: '.json'}}] : []};
  vm.runInNewContext(scripts[family === 'json' ? 1 : 2], {document, fetch: async () => response});
  await new Promise(setImmediate);
  return target.textContent;
}
for (const family of ['json', 'atomic']) {
  for (const code of [403, 429, 500]) test(`${family}: HTTP ${code} is unknown, not unpublished`, async () => {
    const message = await status(family, {ok: false, status: code});
    assert.match(message, /unavailable/i);
    assert.doesNotMatch(message, /not.*published|no verified|remain available/i);
  });
  test(`${family}: successful empty listing is distinct from request failure`, async () => {
    assert.match(await status(family, {ok: true, json: async () => []}), /no published/i);
  });
  for (const payload of [[null], [{}], [{tag_name: family === 'json' ? 'json-slim-test' : 'atomic-slim-test', draft: false, prerelease: false}], [{tag_name: family === 'json' ? 'json-slim-test' : 'atomic-slim-test', draft: false, prerelease: false, assets: [null]}]]) test(`${family}: damaged array items are unavailable`, async () => {
    assert.match(await status(family, {ok: true, json: async () => payload}), /unavailable/i);
  });
  test(`${family}: malformed payload is unavailable`, async () => {
    assert.match(await status(family, {ok: true, json: async () => ({message: 'broken'})}), /unavailable/i);
  });
}
