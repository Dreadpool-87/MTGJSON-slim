'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {render, fixture} = require('./release_site_harness');

const releases = 'https://github.com/Dreadpool-87/MTGJSON-slim/releases';
const families = ['json', 'atomic'];
const data = () => ['sqlite','json','atomic'].map(f => fixture(f));
const expectedFormats = ['xz','zst','zip','raw'];

test('every dataset has one independent selector, download CTA and checksum CTA', async () => {
  const ui = await render([{data:data()}]);
  assert.equal(ui.requests.length, 1);
  for (const family of families) {
    const group = ui[family+'Inputs'];
    assert.deepEqual(group.map(input=>input.value), expectedFormats);
    assert.equal(group.filter(input=>!input.disabled).length, 4);
    assert.equal(group.filter(input=>input.checked).length, 1);
    assert.equal(group[0].checked, true);
    assert.equal(ui.ids[family+'-status-dot'].classList.contains('ready'), true);
    assert.equal(ui.ids[family+'-status-dot'].classList.contains('error'), false);
    assert.equal(ui.ids[family+'-checksum'].hidden, false);
    assert.equal(ui.ids[family+'-checksum'].href, ui.ids[family+'-download'].href + '.sha256');
    assert.ok(ui.ids[family+'-download'].href.endsWith('.json.xz'));
    assert.equal(ui.ids[family+'-download'].textContent, 'Download XZ');
    assert.ok(!group.some(input => input.href), 'radio options must not be direct download links');
  }
  assert.equal(ui.ids['status-dot'].classList.contains('ready'), true);
});

for (const family of families) test(family + ' selecting all four formats updates the one CTA without starting a download',async()=>{
  const ui = await render([{data:data()}]);
  const group = ui[family+'Inputs'];
  const cta = ui.ids[family+'-download'], sha = ui.ids[family+'-checksum'];
  const initialRequests = ui.requests.length;
  for(const input of group) {
    group.forEach(element => {element.checked = element === input;});
    input.change();
    const ext = input.value === 'raw' ? '.json' : '.json.' + input.value;
    assert.ok(cta.href.endsWith(ext), cta.href);
    assert.equal(sha.href, cta.href + '.sha256');
    assert.equal(sha.hidden, false);
    assert.match(ui.ids[family+'-file-note'].textContent, /\.json/);
    assert.equal(cta.textContent, input.value === 'raw' ? 'Download JSON' : 'Download ' + input.value.toUpperCase());
    assert.equal(ui.requests.length, initialRequests, 'format choice must not request or download any file');
  }
});

for (const family of families) test(family + ' disabled XZ checksum switches to valid Zstandard sidecar',async()=>{
  const rows=data(), familyRow=rows[family==='json'?1:2];
  familyRow.assets=familyRow.assets.filter(asset => !asset.name.endsWith('.json.xz.sha256'));
  const ui=await render([{data:rows}]);
  assert.equal(ui[family+'Inputs'][0].disabled,true);
  assert.equal(ui[family+'Inputs'][1].checked,true);
  assert.ok(ui.ids[family+'-download'].href.endsWith('.json.zst'));
  assert.equal(ui.ids[family+'-checksum'].href,ui.ids[family+'-download'].href+'.sha256');
  assert.equal(ui.ids[family+'-status-dot'].classList.contains('ready'),true);
});

for (const family of families) test(family + ' missing all matching checksums cannot enable downloads',async()=>{
  const rows=data(), familyRow=rows[family==='json'?1:2];
  familyRow.assets=familyRow.assets.filter(asset => !asset.name.endsWith('.sha256'));
  const ui=await render([{data:rows}]);
  assert.equal(ui[family+'Inputs'].filter(x=>!x.disabled).length,0);
  assert.equal(ui.ids[family+'-download'].href,releases);
  assert.equal(ui.ids[family+'-download'].textContent,'Open Releases');
  assert.equal(ui.ids[family+'-checksum'].hidden,true);
  assert.equal(ui.ids[family+'-status-dot'].classList.contains('error'),true);
  assert.equal(ui.ids[family+'-status-dot'].classList.contains('ready'),false);
});

for (const code of [403,429,500]) test('HTTP '+code+' shows safe fallback and warning dots in all panels',async()=>{
  const ui=await render([{code}]);
  for(const family of families){
    assert.equal(ui.ids[family+'-download'].href,releases);
    assert.equal(ui.ids[family+'-checksum'].hidden,true);
    assert.equal(ui.ids[family+'-status-dot'].classList.contains('error'),true);
    assert.match(ui.ids[family+'-status'].textContent,/unknown|unavailable/i);
  }
  assert.equal(ui.ids['status-dot'].classList.contains('error'),true);
});

test('missing JSON family does not block SQLite or AtomicCards',async()=>{
  const rows=data().filter(item => !item.tag_name.startsWith('json-slim-'));
  const ui=await render([{data:rows}]);
  assert.equal(ui.ids['json-status-dot'].classList.contains('error'),true);
  assert.equal(ui.ids['json-download'].href,releases);
  assert.equal(ui.ids['atomic-status-dot'].classList.contains('ready'),true);
  assert.ok(ui.ids['atomic-download'].href.endsWith('.json.xz'));
  assert.equal(ui.ids['status-dot'].classList.contains('ready'),true);
});

test('a hostile AtomicCards checksum URL never becomes the CTA target',async()=>{
  const rows=data();
  for(const a of rows[2].assets.filter(a=>a.name.endsWith('.sha256')))
    a.browser_download_url='https://example.invalid/evil';
  const ui=await render([{data:rows}]);
  assert.equal(ui.ids['atomic-status-dot'].classList.contains('error'),true);
  assert.equal(ui.ids['atomic-download'].href,releases);
  assert.equal(ui.ids['atomic-checksum'].hidden,true);
  assert.equal(ui.ids['json-status-dot'].classList.contains('ready'),true);
});
