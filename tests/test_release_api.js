'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {render, fixture, api} = require('./release_site_harness');
const all = () => ['sqlite','json','atomic'].map(f => fixture(f));
const page2 = '<' + api + '&page=2>; rel="next"';
test('one shared request enables all genuine-family formats and same-release checksums', async () => {
  const ui = await render([{data: all()}]);
  assert.deepEqual(ui.requests, [api]);
  assert.equal(ui.inputs.filter(x => !x.disabled).length, 4);
  for (const [links, shas] of [[ui.json,ui.jsonSha],[ui.atomic,ui.atomicSha]]) links.forEach((a,i) => {
    assert.ok(a.href); assert.equal(shas[i].href, a.href + '.sha256');
  });
  assert.equal(ui.ids.checksum.href, ui.ids.download.href + '.sha256');
  assert.match(ui.ids['atomic-manifest'].href, /atomic-manifest.json$/);
});
test('stops after first page when all three families are complete, even with next link', async () => {
  const ui = await render([{data: all(), link: page2}]); assert.equal(ui.requests.length, 1);
  assert.match(ui.ids.status.textContent, /checked listing/i);
});
test('family beyond release #100 is found on second page', async () => {
  const first = Array.from({length: 98}, (_,i) => ({tag_name: 'other-' + i})).concat(all().slice(0,2));
  const ui = await render([{data: first, link: page2}, {data: [fixture('atomic')]}]);
  assert.equal(ui.requests.length, 2); assert.ok(ui.atomic.every(a => a.href));
});
for (const code of [403,429,500]) test(`HTTP ${code}: all families are unknown, not unpublished`, async () => {
  const ui = await render([{code}]); assert.equal(ui.requests.length, 1);
  for (const id of ['status','json-status','atomic-status']) {
    assert.match(ui.ids[id].textContent, /unavailable|unknown/i); assert.doesNotMatch(ui.ids[id].textContent, /no published/i);
  }
  assert.equal(ui.inputs.filter(x => !x.disabled).length, 0);
});
for (const bad of [{invalid:true}, {data:{}}, {network:true}]) test('damaged/network response stays unavailable', async () => {
  const ui = await render([bad]); assert.match(ui.ids['atomic-status'].textContent, /unavailable|unknown/i);
});
test('absent family only after exhausted listing is stated as no eligible publication in checked listing', async () => {
  const ui = await render([{data: []}]); assert.match(ui.ids['atomic-status'].textContent, /no eligible.*checked listing/i);
});
test('five-page cap is unknown, with no sixth request', async () => {
  const pages = Array.from({length: 5}, (_,i) => ({data: [], link: `<${api}&page=${i+2}>; rel="next"`}));
  const ui = await render(pages); assert.equal(ui.requests.length,5); assert.match(ui.ids.status.textContent,/unknown|unavailable/i);
});
for (const link of [
  '<https://evil.example/releases?page=2>; rel="next"',
  '<http://api.github.com/repos/Dreadpool-87/MTGJSON-slim/releases?per_page=100&page=2>; rel="next"',
  `<${api}&page=1>; rel="next"`, `<${api}&page=2&token=secret>; rel="next"`,
  '<https://api.github.com/repos/other/repo/releases?per_page=100&page=2>; rel="next"',
  '<https://api.github.com:443/repos/Dreadpool-87/MTGJSON-slim/releases?per_page=100&page=2>; rel="next"',
  `<${api}&page=2>; rel="next", <${api}&page=3>; rel="next"`, 'broken'
]) test('hostile/cyclic/malformed pagination cannot initiate an unsafe request: ' + link, async () => {
  const ui = await render([{data:[],link}]); assert.equal(ui.requests.length,1); assert.match(ui.ids.status.textContent,/unknown|unavailable/i);
});
test('cycle after second page is bounded without repeat requests', async () => {
  const ui=await render([{data:[],link:page2},{data:[],link:page2}]);assert.equal(ui.requests.length,2);
});
test('total timeout aborts a hanging fetch and updates every panel', async () => {
  const ui = await render([{hang:true}], {timeout:true}); assert.equal(ui.aborts,1); assert.match(ui.ids.status.textContent,/unknown|unavailable/i);
});
for (const mutate of [r=>{r.draft=true;},r=>{r.prerelease=true;},r=>{delete r.draft;},r=>{r.published_at='2026-02-30T12:00:00Z';},
 r=>{r.published_at='not a date';},r=>{r.tag_name='other-' + r.tag_name;},r=>{r.html_url='https://evil.example/';},r=>{r.assets=null;}]) test('ineligible release metadata never enables downloads',async()=>{
  const data=all();mutate(data[2]); const ui=await render([{data}]);assert.ok(ui.atomic.every(a=>!a.href));
});
for (const mutate of [a=>{a.browser_download_url=a.browser_download_url.replace('https:', 'http:');},
 a=>{a.browser_download_url=a.browser_download_url.replace('github.com/', 'github.com.evil/');},
 a=>{a.browser_download_url=a.browser_download_url.replace('/releases/download/', '/releases/tag/');},
 a=>{a.browser_download_url+='?token=x';},a=>{a.browser_download_url+='#fake';},
 a=>{a.browser_download_url=a.browser_download_url.replace('%2B','%252B');},
 a=>{a.browser_download_url=a.browser_download_url.replace('/AtomicCards','/%2FAtomicCards');},
 a=>{a.browser_download_url=a.browser_download_url.replace('https://github.com/', 'https://user@github.com/');},
 a=>{a.name='../escape.json';},a=>{a.size=-1;},a=>{a.size='100';},a=>{a.content_type='text/html';},a=>{a.state='new';}]) test('unsafe data or sidecar metadata cannot enable a format',async()=>{
  const data=all();data[2].assets.forEach(mutate);const ui=await render([{data}]);assert.ok(ui.atomic.every(a=>!a.href));
});
test('missing selected SQLite checksum selects an available paired alternative', async () => {
  const data=all();data[0].assets=data[0].assets.filter(a=>!a.name.endsWith('.sqlite.xz.sha256'));
  const ui=await render([{data}]);assert.equal(ui.inputs[0].disabled,true);assert.match(ui.ids.download.href,/\.sqlite\.zst$/);
});
test('wrong-name or foreign-release sidecars are not paired',async()=>{
  const data=all();for(const a of data[2].assets.filter(a=>a.name.endsWith('.sha256'))) a.browser_download_url=a.browser_download_url.replace(data[2].tag_name,'atomic-slim-other');
  const ui=await render([{data}]);assert.ok(ui.atomic.every(a=>!a.href));
});
test('newest incomplete publication labels an older complete fallback, with version and date',async()=>{
  const old=fixture('atomic','2026-11-01T12:00:00Z','5.3.0+20261101');const latest=fixture('atomic');latest.assets=latest.assets.filter(a=>!a.name.endsWith('.json.xz.sha256'));
  const ui=await render([{data:[...all().slice(0,2),old,latest]}]);
  assert.match(ui.ids['atomic-status'].textContent,/latest.*incomplete.*older/i);assert.match(ui.ids['atomic-status'].textContent,/20261101/);assert.match(ui.ids['atomic-status'].textContent,/2026-11-01/);
  assert.ok(ui.atomic.every(a=>a.href.includes('20261101')));
});
test('latest partial remains useful when no complete fallback exists; no cross-release mixing',async()=>{
  const newer=fixture('atomic');newer.assets=newer.assets.filter(a=>a.name.endsWith('.json')||a.name.endsWith('.json.sha256'));
  const older=fixture('atomic','2026-10-01T12:00:00Z','5.3.0+20261001');older.assets=older.assets.filter(a=>!a.name.endsWith('.json'));
  const ui=await render([{data:[...all().slice(0,2),older,newer]}]);
  assert.equal(ui.atomic.filter(a=>a.href).length,1);assert.ok(ui.atomic.find(a=>a.href).href.includes('20261114'));
});
test('duplicate and conflicting-build assets are rejected rather than mixed',async()=>{
  const data=all();const extra=fixture('atomic',undefined,'5.3.0+20261001');extra.assets.forEach(a=>{a.browser_download_url=a.browser_download_url.replace(extra.tag_name,data[2].tag_name);});data[2].assets.push(...extra.assets);
  const ui=await render([{data}]);assert.ok(ui.atomic.every(a=>!a.href));
});
test('known complete families survive a later-page API failure, with an explicit unknown caveat',async()=>{
  const ui=await render([{data:all().slice(0,2),link:page2},{code:429}]);
  assert.ok(ui.json.every(a=>a.href));assert.match(ui.ids['json-status'].textContent,/unknown|unavailable/i);assert.ok(ui.atomic.every(a=>!a.href));
});
test('malformed array entries never prove absence',async()=>{
  for (const data of [[null],[{}],[{tag_name:'atomic-slim-broken',draft:false,prerelease:false,assets:[],published_at:'invalid'}]]) {
    const ui=await render([{data}]);assert.match(ui.ids['atomic-status'].textContent,/unknown|unavailable/i);
  }
});
if (process.env.RELEASE_FIXTURE) test('captured genuine GitHub releases retain all current formats and exact URLs',async()=>{
  const data=JSON.parse(fs.readFileSync(process.env.RELEASE_FIXTURE,'utf8'));
  const ui=await render([{data}]);assert.ok(ui.json.every(a=>a.href));assert.ok(ui.atomic.every(a=>a.href));
  assert.equal(ui.inputs.filter(i=>!i.disabled).length,4);assert.equal(ui.requests.length,1);
  const known=new Set(data.flatMap(r=>r.assets.map(a=>a.browser_download_url)));
  [ui.ids.download,ui.ids.checksum,...ui.json,...ui.jsonSha,...ui.atomic,...ui.atomicSha].forEach(a=>assert.ok(known.has(a.href),a.href));
});
for (const bad of ['http://github.com/', 'https://github.com.evil/', 'https://user@github.com/']) test('unsafe sidecar alone cannot enable formats: '+bad,async()=>{
  const data=all();data[2].assets.filter(a=>a.name.endsWith('.sha256')).forEach(a=>{a.browser_download_url=a.browser_download_url.replace('https://github.com/',bad);});
  const ui=await render([{data}]);assert.ok(ui.atomic.every(a=>!a.href));
});
test('one missing Atomic checksum disables only that option and never borrows a sidecar',async()=>{
  const data=all();data[2].assets=data[2].assets.filter(a=>!a.name.endsWith('.json.xz.sha256'));
  const ui=await render([{data}]);assert.equal(ui.atomic.filter(a=>a.href).length,3);assert.equal(ui.atomic[0].href,null);assert.equal(ui.atomicSha[0].href,null);
});
test('duplicate matching asset names cannot enable that format',async()=>{
  const data=all();data[2].assets.push({...data[2].assets.find(a=>a.name.endsWith('.json.xz'))});
  const ui=await render([{data}]);assert.equal(ui.atomic[0].href,null);assert.equal(ui.atomic.filter(a=>a.href).length,3);
});

test('GitHub canonical numeric-repository Link pages are followed for this repository only',async()=>{
  const next='https://api.github.com/repositories/1456666653/releases?per_page=100&page=2';
  const ui=await render([{data:all().slice(0,2),link:`<${next}>; rel="next", <${next}>; rel="last"`},{data:[fixture('atomic')]}]);
  assert.deepEqual(ui.requests,[api,next]);assert.ok(ui.atomic.every(a=>a.href));
});
test('numeric Link path for another repository cannot be fetched',async()=>{
  const ui=await render([{data:[],link:'<https://api.github.com/repositories/999/releases?per_page=100&page=2>; rel="next"'}]);
  assert.equal(ui.requests.length,1);assert.match(ui.ids.status.textContent,/unknown|unavailable/i);
});
