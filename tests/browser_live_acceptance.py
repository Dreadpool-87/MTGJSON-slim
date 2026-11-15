#!/usr/bin/env python3
"""Read-only GitHub Release browser acceptance for immutable MTGJSON-slim PR heads.

Runs the checked-out docs/ website using a localhost server in real Chromium.
The page's browser requests must reach GitHub's *real* public API: no route overrides,
mock responses, tokens inside the page, or data publication.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from threading import Thread
from datetime import datetime, timezone
import traceback
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

PREFIX = 'https://github.com/Dreadpool-87/MTGJSON-slim/releases/download/'
API_PREFIX = 'https://api.github.com/repos/Dreadpool-87/MTGJSON-slim/releases'
SAFE_RESPONSE_HEADERS = (
    'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset',
    'x-ratelimit-resource', 'x-ratelimit-used', 'retry-after',
    'x-github-request-id',
)
EXPECTED = {
    27: '3833539171eb19c7dca2a7b6f083ee1323a51e7e',
    29: 'e76605c8c4e1d39d47e47a3cfb872d76aedc5a8e',
}


def verify_download(url: str, sidecar: str) -> None:
    assert url.startswith(PREFIX), f'Untrusted download URL: {url}'
    assert sidecar == url + '.sha256', f'Sidecar mismatch: {url} vs {sidecar}'
    for value in (url, sidecar):
        parsed = urlparse(value)
        assert parsed.scheme == 'https' and parsed.netloc == 'github.com'
        assert not parsed.query and not parsed.fragment and not parsed.username


def response_diagnostics(response) -> dict:
    """Record bounded, sanitized evidence; never store request headers or credentials."""
    hdr = response.headers
    record = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'url': response.url, 'status': response.status,
        'headers': {key: hdr[key] for key in SAFE_RESPONSE_HEADERS if key in hdr},
    }
    if response.status != 200:
        try:
            body = response.text()[:512]
            body = re.sub(r'(?i)Bearer\s+[^\s",}]+', 'Bearer [REDACTED]', body)
            body = re.sub(r'gh[pousr]_[A-Za-z0-9_]+', '[REDACTED]', body)
            record['body_excerpt'] = body
        except Exception as exc:
            record['body_excerpt_error'] = type(exc).__name__
    return record


def inspect(page, pr: int, mobile: bool, out: Path, evidence: dict) -> dict:
    """Open an unmodified page with the *real* browser network."""
    errors: list[str] = []
    requests: list[str] = evidence['apiRequests']
    responses: list[dict] = evidence['apiResponses']
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.on('request', lambda req: requests.append(req.url) if req.url.startswith(API_PREFIX) else None)
    page.on('response', lambda res: responses.append(response_diagnostics(res)) if res.url.startswith(API_PREFIX) else None)
    page.goto('http://127.0.0.1:' + os.environ['MTG_TEST_PORT'] + '/', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_function('''() => ['status','json-status','atomic-status'].every(id => {
        const node = document.getElementById(id);
        return node && !node.textContent.trim().startsWith('Checking');
    })''', timeout=20000)
    page.wait_for_timeout(450)
    state = page.evaluate('''() => ({
        language: document.documentElement.lang,
        title: document.title,
        heading: document.getElementById('atomic-title')?.innerText,
        bodyWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        sqliteStatus: document.getElementById('status')?.innerText,
        jsonStatus: document.getElementById('json-status')?.innerText,
        atomicStatus: document.getElementById('atomic-status')?.innerText,
        sqlite: [...document.querySelectorAll('input[name="format"]')].map(x => ({format:x.value,disabled:x.disabled,checked:x.checked})),
        download: document.getElementById('download')?.href,
        checksum: document.getElementById('checksum')?.hidden ? null : document.getElementById('checksum')?.href,
        json: [...document.querySelectorAll('[data-json-extension]')].map(x => ({fmt:x.dataset.jsonExtension,disabled:x.getAttribute('aria-disabled')==='true',url:x.href || null,checksum:document.querySelector('[data-json-sha="'+x.dataset.jsonExtension+'"]')?.href || null})),
        atomic: [...document.querySelectorAll('[data-atomic-extension]')].map(x => ({fmt:x.dataset.atomicExtension,disabled:x.getAttribute('aria-disabled')==='true',url:x.href || null,checksum:document.querySelector('[data-atomic-sha="'+x.dataset.atomicExtension+'"]')?.href || null})),
        releaseLinks: [...document.querySelectorAll('a[id$="-release"]')].map(x => x.href)
    })''')
    out.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out), full_page=True, animations='disabled')
    assert not errors, f'Uncaught JavaScript exceptions: {errors}'
    assert state['heading'] == 'AtomicCards Slim — Card Lookup', state['heading']
    assert state['language'] == 'en'
    assert state['bodyWidth'] <= state['viewportWidth'] + 1, f'Horizontal overflow {state["bodyWidth"]}>{state["viewportWidth"]}'
    assert len(state['json']) == len(state['atomic']) == len(state['sqlite']) == 4
    assert requests and responses, f'No real GitHub API calls observed: {requests}'
    assert len(responses) == len(requests), f'GitHub API requests not completed: {requests} {responses}'
    assert all(x['status'] == 200 for x in responses), f'GitHub API unavailable: {responses}'
    if pr == 29:
        assert len(requests) == 1, f'Expected one shared API call for current 4 releases: {requests}'
        assert requests[0] == API_PREFIX + '?per_page=100', requests
        for family in ('json', 'atomic'):
            for choice in state[family]:
                assert not choice['disabled'], f'{family} format missing despite publicly released 4-format asset set: {choice}'
                verify_download(choice['url'], choice['checksum'])
        for choice in state['sqlite']:
            assert not choice['disabled'], f'SQLite format missing in current public release: {choice}'
        assert state['checksum'] is not None
        verify_download(state['download'], state['checksum'])
        # Real click/selection; no download of the large artifact occurs.
        page.locator('input[name="format"][value="zip"]').check(force=True)
        new_urls = page.evaluate('''() => ({data: document.getElementById('download').href,
            sha: document.getElementById('checksum').href})''')
        assert new_urls['data'].endswith('.sqlite.zip')
        verify_download(new_urls['data'], new_urls['sha'])
        state['sqliteZipInteraction'] = new_urls
    else:
        assert len(requests) == 3, f'Expected PR27 original 3 separate API calls: {requests}'
        for family in ('json', 'atomic'):
            for choice in state[family]:
                if not choice['disabled']:
                    verify_download(choice['url'], choice['checksum'])
    return {'platform': 'mobile-emulation' if mobile else 'desktop', 'status': 'PASS', 'state': state, 'apiRequests': requests, 'apiResponses': responses, 'jsExceptions': errors, 'screenshot':str(out)}


def check_nojs(browser, base: str, out: Path) -> dict:
    ctx = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
    page = ctx.new_page()
    page.goto(base, wait_until='domcontentloaded', timeout=15000)
    info = page.evaluate('''() => ({visible:!!document.querySelector('noscript'),
        links:[...document.querySelectorAll('noscript a')].map(x => x.href),
        statuses: ['status','json-status','atomic-status'].map(id => document.getElementById(id)?.textContent)})''')
    page.screenshot(path=str(out), full_page=True, animations='disabled')
    assert info['visible'] and len(info['links']) >= 4
    assert all(url.startswith('https://github.com/Dreadpool-87/MTGJSON-slim/releases') for url in info['links'])
    ctx.close()
    return {'platform':'mobile-no-js','status':'PASS','state':info,'screenshot':str(out)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site-dir', type=Path, default=Path('docs'))
    parser.add_argument('--pr', type=int, required=True, choices=[27, 29])
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    assert args.expected_head == EXPECTED[args.pr], 'Unexpected PR head: gate refuses changed code'
    assert (args.site_dir / 'index.html').is_file()
    if args.pr == 29:
        assert (args.site_dir / 'release-downloads.js').is_file()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, fmt, *values):
            pass
    handler = partial(Quiet, directory=str(args.site_dir.resolve()))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    os.environ['MTG_TEST_PORT'] = str(server.server_address[1])
    t = Thread(target=server.serve_forever, daemon=True);t.start()
    result = {'pr':args.pr,'head':args.expected_head,'date_utc':datetime.now(timezone.utc).isoformat(),
              'real_browser':True,'live_github_api':True,'api_mocked':False,
              'physical_android':False,
              'github_run_id':os.environ.get('GITHUB_RUN_ID'),
              'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
              'github_job':os.environ.get('GITHUB_JOB'),
              'runner_name':os.environ.get('RUNNER_NAME'),
              'cases':[]}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for label, mobile, vp in [('desktop',False,{'width':1366,'height':768}),('mobile',True,{'width':390,'height':844})]:
                    ctx = browser.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                    evidence = {'apiRequests': [], 'apiResponses': []}
                    try:
                        item=inspect(ctx.new_page(), args.pr, mobile, args.out_dir / f'pr{args.pr}_{label}.png', evidence)
                        result['cases'].append(item)
                        print(f'PASS PR #{args.pr} {label}: {len(item["apiRequests"])} real GitHub API requests')
                    except Exception:
                        result['cases'].append({'platform':label, 'status':'FAIL',
                                                'diagnostics':evidence,
                                                'error':traceback.format_exc()})
                        print(f'FAIL PR #{args.pr} {label}: see JSON diagnostics')
                    finally:
                        ctx.close()
                try:
                    result['cases'].append(check_nojs(browser,'http://127.0.0.1:'+os.environ['MTG_TEST_PORT']+'/',args.out_dir / f'pr{args.pr}_nojs.png'))
                    print(f'PASS PR #{args.pr} no-JS fallback')
                except Exception:
                    result['cases'].append({'platform':'mobile-no-js', 'status':'FAIL',
                                            'error':traceback.format_exc()})
                    print(f'FAIL PR #{args.pr} no-JS: see JSON diagnostics')
            finally:
                browser.close()
    except Exception:
        result['error']=traceback.format_exc()
        print(result['error'])
    finally:
        server.shutdown();server.server_close()
        result['passed']=bool(result['cases']) and len(result['cases'])==3 and all(c['status']=='PASS' for c in result['cases']) and 'error' not in result
        (args.out_dir / f'pr{args.pr}_result.json').write_text(json.dumps(result, indent=2,ensure_ascii=False)+'\n', encoding='utf-8')
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()