'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {render,fixture} = require('./release_site_harness');
async function message(family,page){const ui=await render([page]);return ui.ids[family+'-status'].textContent;}
for(const family of ['json','atomic']) {
  for(const code of [403,429,500]) test(`${family}: HTTP ${code} is unknown, not unpublished`,async()=>{
    const text=await message(family,{code});assert.match(text,/unknown|unavailable/i);assert.doesNotMatch(text,/no published|remain available/i);
  });
  test(`${family}: empty listing differs from failed request`,async()=>{assert.match(await message(family,{data:[]}),/no eligible.*checked listing/i);});
  for(const payload of [[null],[{}],[{tag_name:family+'-slim-test',draft:false,prerelease:false}], [{...fixture(family),assets:[null]}]]) test(`${family}: damaged array items are unavailable`,async()=>{
    assert.match(await message(family,{data:payload}),/unknown|unavailable/i);
  });
  test(`${family}: malformed payload is unavailable`,async()=>{assert.match(await message(family,{data:{message:'broken'}}),/unknown|unavailable/i);});
}
