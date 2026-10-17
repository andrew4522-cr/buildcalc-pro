#!/usr/bin/env python3
"""
BuildCalc Pro — Free IndexNow Instant Search Engine Submitter
Submits all 52 Programmatic SEO calculator URLs directly to Bing, Yandex,
DuckDuckGo, and Seznam via the free IndexNow protocol ($0 API cost).
"""

import json
import urllib.request
from build_suite import PSEO_PAGES, SITE_DOMAIN


def submit_indexnow(key: str = "buildcalcpro2026indexnowkey"):
    url_list = [f"{SITE_DOMAIN}/{'' if fn == 'index.html' else fn}" for fn, _, _, _ in PSEO_PAGES]
    payload = {
        "host": SITE_DOMAIN.replace("https://", "").replace("http://", ""),
        "key": key,
        "keyLocation": f"{SITE_DOMAIN}/{key}.txt",
        "urlList": url_list,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    print(f"Prepared {len(url_list)} pSEO URLs for IndexNow instant indexing.")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"IndexNow HTTP Status: {resp.status}")
    except Exception as e:
        print(f"IndexNow submission status (requires live domain {SITE_DOMAIN}): {e}")


if __name__ == "__main__":
    submit_indexnow()
