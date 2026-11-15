#!/usr/bin/env python3
"""Real Chromium acceptance of the three equivalent, accessible download selectors.

Network: only localhost content and explicitly mocked GitHub Releases metadata.
No production download, release mutation, login, or GitHub credentials.
"""
import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import quote

from playwright.sync_api import sync_playwright

REPO = "Dreadpool-87/MTGJSON-slim"
RELEASES = f"https://github.com/{REPO}/releases"
API_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=100"
FORMATS = ("xz", "zst", "zip", "raw")
FAMILIES = ("sqlite", "json", "atomic")


def releases():
    output = []
    for family in FAMILIES:
        prefix = {"sqlite": "slim-", "json": "json-slim-", "atomic": "atomic-slim-"}[family]
        stem = {
            "sqlite": "AllPrintings-slim-5.3.0+20261114-profile-2.3.sqlite",
            "json": "AllPrintings-slim-5.3.0+20261114-json-deckbuilding-1.0.json",
            "atomic": "AtomicCards-slim-5.3.0+20261114-atomic-b1.json",
        }[family]
        tag = prefix + "2026-11-14-test123"
        def asset(name):
            return {"name": name, "state": "uploaded", "size": 123456,
                    "content_type": "text/plain" if name.endswith(".sha256") else "application/octet-stream",
                    "browser_download_url": f"{RELEASES}/download/{quote(tag,safe='')}/{quote(name,safe='')}"}
        assets = []
        for ext in ("", ".xz", ".zst", ".zip"):
            assets.extend([asset(stem + ext), asset(stem + ext + ".sha256")])
        assets.append(asset({"sqlite":"manifest.json","json":"json-manifest.json","atomic":"atomic-manifest.json"}[family]))
        output.append({"tag_name": tag, "draft": False, "prerelease": False,
                       "published_at": "2026-11-14T12:00:00Z", "html_url": f"{RELEASES}/tag/{quote(tag,safe='')}",
                       "assets": assets})
    return output


def settled(page):
    page.wait_for_function("""() => ['status','json-status','atomic-status'].every(id => {
        const el = document.getElementById(id);
        return el && !el.textContent.startsWith('Checking');
    })""", timeout=15000)


def take_state(page):
    return page.evaluate("""() => ({
        width: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        panels: ['sqlite','json','atomic'].map(f => {
            const name = f === 'sqlite' ? 'format' : f+'-format';
            const prefix = f === 'sqlite' ? '' : f+'-';
            return {
                family:f,
                dot:document.getElementById(f === 'sqlite' ? 'status-dot' : f+'-status-dot').className,
                formatOptions:[...document.querySelectorAll('input[name="'+name+'"]')].map(x => ({value:x.value,disabled:x.disabled,checked:x.checked})),
                download:document.getElementById(prefix+'download').href,
                sha:document.getElementById(prefix+'checksum').href,
                shaHidden:document.getElementById(prefix+'checksum').hidden
            }
        })
    })""")


def check_site(browser, base, out, mobile=False):
    width = 390 if mobile else 1366
    context = browser.new_context(viewport={"width":width,"height":844 if mobile else 768},
                                  is_mobile=mobile,has_touch=mobile,device_scale_factor=2 if mobile else 1)
    page = context.new_page()
    fetches = []
    errors = []
    data = releases()
    page.on("pageerror", lambda e: errors.append(str(e)))
    def respond(route):
        fetches.append(route.request.url)
        assert route.request.url == API_URL, route.request.url
        route.fulfill(status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},
                      body=json.dumps(data))
    page.route("https://api.github.com/**",respond)
    page.goto(base,wait_until="domcontentloaded")
    settled(page)
    assert fetches == [API_URL], fetches
    assert not errors,errors
    state=take_state(page)
    assert state["scrollWidth"] <= state["width"]+1, state
    for p in state["panels"]:
        assert "ready" in p["dot"],p
        assert len(p["formatOptions"])==4,p
        assert all(not x["disabled"] for x in p["formatOptions"]),p
        assert p["formatOptions"][0]["checked"],p
        assert p["sha"] == p["download"]+".sha256",p
    for family in FAMILIES:
        name = "format" if family=="sqlite" else family+"-format"
        prefix = "" if family=="sqlite" else family+"-"
        for fmt in FORMATS:
            value = "sqlite" if fmt=="raw" and family=="sqlite" else fmt
            input_control = page.locator(f'input[name="{name}"][value="{value}"]')
            choice = page.locator(f'label.format:has(input[name="{name}"][value="{value}"])')
            if mobile:
                choice.tap()
            else:
                choice.click()
            assert input_control.is_checked(), (family, value, "format selection failed")
            href=page.locator("#"+prefix+"download").get_attribute("href")
            sha=page.locator("#"+prefix+"checksum").get_attribute("href")
            ext=(".sqlite" if family=="sqlite" else ".json") + ("" if fmt=="raw" else "."+fmt)
            assert href.endswith(ext),(family,fmt,href)
            assert sha==href+".sha256",(family,fmt,sha,href)
            assert page.url==base, "radio selection initiated navigation or download"
    assert fetches == [API_URL],fetches
    page.screenshot(path=str(out / ("mobile.png" if mobile else "desktop.png")),full_page=True)
    context.close()
    return {"device":"mobile emulation 390px" if mobile else "desktop 1366px","status":"PASS",
            "requests":fetches,"initial":state}


def check_403(browser,base):
    context=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
    page=context.new_page()
    page.route("https://api.github.com/**",lambda route:route.fulfill(
        status=403,content_type="application/json",headers={"access-control-allow-origin":"*"},
        body='{"message":"API rate limit exceeded"}'))
    page.goto(base)
    settled(page)
    state=take_state(page)
    for p in state["panels"]:
        assert "error" in p["dot"],p
        assert all(x["disabled"] for x in p["formatOptions"]),p
        assert p["download"] == RELEASES,p
        assert p["shaHidden"],p
    context.close()
    return {"scenario":"HTTP 403 simulated","status":"PASS"}


def check_missing_sha(browser,base):
    context=browser.new_context(viewport={"width":390,"height":844})
    page=context.new_page()
    data=releases()
    data[1]["assets"]=[a for a in data[1]["assets"] if not a["name"].endswith(".json.xz.sha256")]
    page.route("https://api.github.com/**",lambda route:route.fulfill(
        status=200,content_type="application/json",headers={"access-control-allow-origin":"*"},body=json.dumps(data)))
    page.goto(base)
    settled(page)
    state=take_state(page)
    p=state["panels"][1]
    assert "ready" in p["dot"],p
    assert p["formatOptions"][0]["disabled"] and p["formatOptions"][1]["checked"],p
    assert p["download"].endswith(".json.zst"),p
    assert p["sha"]==p["download"]+".sha256",p
    context.close()
    return {"scenario":"missing JSON XZ checksum simulated","status":"PASS"}


def check_no_js(browser,base,out):
    context=browser.new_context(java_script_enabled=False,viewport={"width":390,"height":844})
    page=context.new_page()
    page.goto(base)
    assert page.locator("noscript").is_visible()
    assert page.locator("noscript").bounding_box()["y"] < page.locator("#formats").bounding_box()["y"]
    for name in ("format","json-format","atomic-format"):
        assert page.locator('input[name="'+name+'"]').count()==4
        assert page.locator('input[name="'+name+'"]:disabled').count()==4
    page.screenshot(path=str(out/"no-javascript.png"),full_page=True)
    context.close()
    return {"scenario":"no JavaScript fallback","status":"PASS"}


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--out",type=Path,required=True)
    arg=args.parse_args()
    out=arg.out
    out.mkdir(parents=True,exist_ok=True)
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_):
            pass
    handler=partial(Quiet,directory=str((Path.cwd()/"docs").resolve()))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base="http://127.0.0.1:"+str(server.server_address[1])+"/"
    result={"date":datetime.now(timezone.utc).isoformat(),"api_transport":"mocked fixture; never real GitHub",
            "real_chromium":True,"physical_android":False,"cases":[]}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                for f in (lambda:check_site(browser,base,out),lambda:check_site(browser,base,out,True),
                          lambda:check_403(browser,base),lambda:check_missing_sha(browser,base),
                          lambda:check_no_js(browser,base,out)):
                    result["cases"].append(f())
            finally:
                browser.close()
    except Exception as exc:
        result["error"]=repr(exc)
        raise
    finally:
        server.shutdown()
        server.server_close()
        (out/"results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("PASS real Chromium browser selector cases:",len(result["cases"]))


if __name__=="__main__":
    main()
