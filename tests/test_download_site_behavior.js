'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {render, fixture} = require('./release_site_harness');
const data = () => ['sqlite','json','atomic'].map(f=>fixture(f));
test('complete SQLite release enables four matching download/checksum choices and selector changes',async()=>{
  const ui=await render([{data:data()}]);assert.equal(ui.inputs.filter(x=>!x.disabled).length,4);
  for(const input of ui.inputs){ui.inputs.forEach(i=>{i.checked=i===input;});input.change();assert.equal(ui.ids.checksum.href,ui.ids.download.href+'.sha256');assert.match(ui.ids.download.href,new RegExp(input.value==='sqlite'?'\\.sqlite$':'\\.'+input.value+'$'));}
});
test('no checksum sidecars disables every SQLite format',async()=>{
  const rows=data();rows[0].assets=rows[0].assets.filter(a=>!a.name.endsWith('.sha256'));
  const ui=await render([{data:rows}]);assert.equal(ui.inputs.filter(x=>!x.disabled).length,0);assert.equal(ui.ids.checksum.hidden,true);
});
test('missing selected checksum disables only that format and selects a paired alternative',async()=>{
  const rows=data();rows[0].assets=rows[0].assets.filter(a=>!a.name.endsWith('.sqlite.xz.sha256'));
  const ui=await render([{data:rows}]);assert.equal(ui.inputs[0].disabled,true);assert.equal(ui.inputs.filter(x=>!x.disabled).length,3);assert.match(ui.ids.download.href,/\.sqlite\.zst$/);
});
test('untrusted checksum cannot enable SQLite',async()=>{
  const rows=data();rows[0].assets.filter(a=>a.name.endsWith('.sha256')).forEach(a=>{a.browser_download_url='https://example.com/untrusted';});
  const ui=await render([{data:rows}]);assert.equal(ui.inputs.filter(x=>!x.disabled).length,0);
});
for(const code of [403,429,500]) test(`SQLite HTTP ${code} leaves a safe fallback`,async()=>{
  const ui=await render([{code}]);assert.match(ui.ids.status.textContent,/unknown|unavailable/i);assert.equal(ui.ids.download.href,'https://github.com/Dreadpool-87/MTGJSON-slim/releases');assert.equal(ui.ids.checksum.hidden,true);assert.equal(ui.inputs.filter(x=>!x.disabled).length,0);
});
test('SQLite damaged metadata is unavailable, not unpublished',async()=>{
  const ui=await render([{data:[{assets:[null]}]}]);assert.match(ui.ids.status.textContent,/unknown|unavailable/i);
});
