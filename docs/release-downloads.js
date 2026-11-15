/* Release metadata only: checksums are verified by the downloader, not this page. */
(() => {
  'use strict';
  const repo = 'Dreadpool-87/MTGJSON-slim';
  const releases = 'https://github.com/' + repo + '/releases';
  const endpoint = 'https://api.github.com/repos/' + repo + '/releases';
  // GitHub emits canonical numeric repository URLs in its Link header.
  const apiPaths = ['/repos/' + repo + '/releases', '/repositories/1456666653/releases'];
  const maxPages = 5;
  const timeoutMs = 10000;
  const formats = ['xz', 'zst', 'zip', 'raw'];
  const families = {
    sqlite: {prefix: 'slim-', pattern: /^AllPrintings-slim-[0-9][A-Za-z0-9.+_-]*-profile-[0-9]+(?:\.[0-9]+)*\.sqlite$/, manifest: 'manifest.json'},
    json: {prefix: 'json-slim-', pattern: /^AllPrintings-slim-[0-9][A-Za-z0-9.+_-]*-json-deckbuilding-[0-9]+(?:\.[0-9]+)*\.json$/, manifest: 'json-manifest.json'},
    atomic: {prefix: 'atomic-slim-', pattern: /^AtomicCards-slim-[0-9][A-Za-z0-9.+_-]*-atomic-b1\.json$/, manifest: 'atomic-manifest.json'}
  };
  const bytes = size => (size / 1000000).toFixed(1) + ' MB';
  const suffix = format => format === 'raw' ? '' : '.' + format;
  const pathUrl = (tag, name) => releases + '/download/' + encodeURIComponent(tag) + '/' + encodeURIComponent(name);
  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) return false;
    const date = new Date(value);
    return Number.isFinite(date.getTime()) && date.toISOString() === value.replace('Z', '.000Z');
  }
  function validAsset(asset, tag) {
    return asset && typeof asset.name === 'string' && /^[A-Za-z0-9][A-Za-z0-9.+_-]*$/.test(asset.name) &&
      !asset.name.includes('..') && Number.isSafeInteger(asset.size) && asset.size > 0 && asset.state === 'uploaded' &&
      typeof asset.content_type === 'string' && /^(application\/(octet-stream|json|x-xz|zstd|zip)|text\/plain)(;.*)?$/.test(asset.content_type) &&
      asset.browser_download_url === pathUrl(tag, asset.name);
  }
  function candidate(item, family) {
    const policy = families[family];
    if (!item || item.draft !== false || item.prerelease !== false || typeof item.tag_name !== 'string' ||
      !item.tag_name.startsWith(policy.prefix) || !/^[A-Za-z0-9][A-Za-z0-9.+_-]*$/.test(item.tag_name) ||
      item.tag_name.includes('..') || !validDate(item.published_at) || !Array.isArray(item.assets) ||
      item.html_url !== releases + '/tag/' + encodeURIComponent(item.tag_name)) return null;
    const names = new Map();
    for (const asset of item.assets) {
      if (asset && typeof asset.name === 'string') names.set(asset.name, (names.get(asset.name) || 0) + 1);
    }
    const good = item.assets.filter(asset => validAsset(asset, item.tag_name) && names.get(asset.name) === 1);
    // A release with conflicting build stems must never be assembled into a mixed package.
    const stems = new Set(good.map(a => a.name.replace(/\.(xz|zst|zip)$/, '')).filter(name => policy.pattern.test(name)));
    const pairs = {};
    if (stems.size === 1) {
      const stem = [...stems][0];
      for (const format of formats) {
        const asset = good.find(a => a.name === stem + suffix(format));
        const sha = asset && good.find(a => a.name === asset.name + '.sha256');
        if (asset && sha) pairs[format] = {asset, sha};
      }
    }
    return {item, pairs, manifest: good.find(a => a.name === policy.manifest)};
  }
  function selection(items, family) {
    const candidates = items.map(item => candidate(item, family)).filter(Boolean)
      .sort((a,b) => b.item.published_at.localeCompare(a.item.published_at) || a.item.tag_name.localeCompare(b.item.tag_name));
    const latest = candidates[0];
    // Prefer one complete release. If none exists, retain only the latest publication's usable formats.
    const chosen = candidates.find(c => Object.keys(c.pairs).length === 4) || latest;
    return {latest, chosen};
  }
  function nextPage(header, current, visited) {
    if (!header) return null;
    if (typeof header !== 'string') throw new Error('Invalid pagination');
    const parts = header.split(',').map(part => part.trim());
    const matches = [];
    for (const part of parts) {
      const match = /^<([^<>]+)>;\s*rel="(next|prev|first|last)"$/.exec(part);
      if (!match) throw new Error('Invalid pagination');
      if (match[2] === 'next') matches.push(match[1]);
    }
    if (!matches.length) return null;
    if (matches.length !== 1) throw new Error('Ambiguous pagination');
    const raw = matches[0];
    const url = new URL(raw);
    const page = url.searchParams.get('page');
    const previous = new URL(current).searchParams.get('page') || '1';
    if (url.origin !== 'https://api.github.com' || !apiPaths.includes(url.pathname) ||
      url.username || url.password || url.hash || url.searchParams.get('per_page') !== '100' ||
      [...url.searchParams.keys()].length !== 2 || !/^[1-9][0-9]*$/.test(page || '') ||
      !Number.isSafeInteger(Number(page)) || Number(page) !== Number(previous) + 1 ||
      raw !== 'https://api.github.com' + url.pathname + '?per_page=100&page=' + page || visited.has(raw)) throw new Error('Unsafe pagination');
    return raw;
  }
  async function load() {
    const controller = new AbortController();
    const items = [];
    let partial = false;
    let timer;
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => {controller.abort(); reject(new Error('Timed out'));}, timeoutMs);
    });
    const scan = async () => {
      const visited = new Set();
      let url = endpoint + '?per_page=100';
      for (let page = 0; page < maxPages; page++) {
        if (controller.signal.aborted || visited.has(url)) throw new Error('Pagination stopped');
        visited.add(url);
        const response = await fetch(url, {headers: {'Accept': 'application/vnd.github+json'}, cache: 'no-store', redirect: 'error', signal: controller.signal});
        if (!response.ok) throw new Error('GitHub HTTP ' + response.status);
        const data = await response.json();
        if (controller.signal.aborted) throw new Error('Lookup aborted');
        if (!Array.isArray(data) || data.length > 100) throw new Error('Invalid GitHub response');
        // Ignore unusable entries, but never turn damaged metadata into proof of absence.
        if (data.some(item => !item || typeof item !== 'object' || typeof item.tag_name !== 'string' ||
          typeof item.draft !== 'boolean' || typeof item.prerelease !== 'boolean' || !Array.isArray(item.assets) || item.assets.some(a => !a || typeof a.name !== 'string' || typeof a.browser_download_url !== 'string' || !Number.isSafeInteger(a.size) || a.size <= 0))) partial = true;
        if (data.some(item => item && item.draft === false && item.prerelease === false &&
          Object.keys(families).some(family => typeof item.tag_name === 'string' && item.tag_name.startsWith(families[family].prefix) && !candidate(item, family)))) partial = true;
        items.push(...data);
        const next = nextPage(response.headers.get('Link'), url, visited);
        if (!next) return;
        if (Object.keys(families).every(family => {
          const s = selection(items, family); return s.chosen && Object.keys(s.chosen.pairs).length === 4;
        })) { partial = true; return; }
        if (page + 1 === maxPages) throw new Error('Pagination limit');
        url = next;
      }
    };
    try { await Promise.race([scan(), deadline]); }
    catch (_) { partial = true; controller.abort(); }
    finally { clearTimeout(timer); }
    return {items, partial};
  }
  function render(family, result) {
    const {latest, chosen} = selection(result.items, family);
    const status = document.getElementById(family === 'sqlite' ? 'status' : family + '-status');
    const releaseLink = document.getElementById(family + '-release');
    const manifestLink = document.getElementById(family + '-manifest');
    releaseLink.href = chosen ? chosen.item.html_url : releases;
    if (chosen && chosen.manifest) {manifestLink.href = chosen.manifest.browser_download_url; manifestLink.hidden = false;}
    const count = chosen ? Object.keys(chosen.pairs).length : 0;
    let message;
    if (!latest) message = result.partial ? 'Availability UNKNOWN: GitHub release details unavailable.' : 'No eligible published release found in the checked listing.';
    else {
      const label = c => c.item.tag_name + ' (' + c.item.published_at.slice(0,10) + ')';
      message = chosen !== latest ? 'Latest publication ' + label(latest) + ' is incomplete. Showing older complete release ' + label(chosen) + '. ' :
        label(latest) + (count < 4 ? ' is incomplete. ' : '. ');
      message += count + ' formats with matching checksum files in the checked listing.';
      if (result.partial) message += ' Further availability UNKNOWN: listing incomplete or temporarily unavailable.';
    }
    if (family === 'sqlite') {
      const button = document.getElementById('download');
      const checksum = document.getElementById('checksum');
      const note = document.getElementById('file-note');
      const inputs = [...document.querySelectorAll('input[name="format"]')];
      const pairFor = input => chosen && chosen.pairs[input.value === 'sqlite' ? 'raw' : input.value];
      for (const input of inputs) {
        const pair = pairFor(input); input.disabled = !pair;
        document.getElementById('size-' + input.value).textContent = pair ? bytes(pair.asset.size) : 'Not available';
      }
      if (!inputs.some(input => input.checked && !input.disabled)) inputs.forEach(input => {input.checked = false;});
      if (!inputs.some(input => input.checked)) {const first = inputs.find(input => !input.disabled); if (first) first.checked = true;}
      const refresh = () => {
        const input = inputs.find(input => input.checked && !input.disabled);
        const pair = input && pairFor(input);
        button.href = pair ? pair.asset.browser_download_url : releases;
        button.textContent = pair ? 'Download ' + input.value.toUpperCase() : 'Open Releases';
        checksum.hidden = !pair; checksum.href = pair ? pair.sha.browser_download_url : releases;
        note.textContent = pair ? pair.asset.name + ' · ' + bytes(pair.asset.size) : 'Use GitHub Releases to inspect files and manifests.';
      };
      inputs.forEach(input => input.addEventListener('change',refresh)); refresh();
      document.getElementById('status-dot').classList.add(count ? 'ready' : 'error');
    } else {
      const links = [...document.querySelectorAll('[data-' + family + '-extension]')];
      const shas = [...document.querySelectorAll('[data-' + family + '-sha]')];
      for (const link of links) {
        const ext = link.dataset[family + 'Extension'];
        const format = ext === '.json' ? 'raw' : ext.slice(6);
        const pair = chosen && chosen.pairs[format];
        const sha = shas.find(a => a.dataset[family + 'Sha'] === ext);
        if (pair && sha) {
          link.href = pair.asset.browser_download_url; link.removeAttribute('aria-disabled');
          sha.href = pair.sha.browser_download_url; sha.removeAttribute('aria-disabled');
          link.querySelector('span').textContent = bytes(pair.asset.size) + ' · Download';
        } else link.querySelector('span').textContent = result.partial ? 'Availability unknown' : 'No matching file/checksum';
      }
    }
    status.textContent = message;
  }
  // One promise, one initial request, and one bounded scan shared by all panels.
  const releaseDetails = load();
  releaseDetails.then(result => {for (const family of Object.keys(families)) render(family, result);});
})();
