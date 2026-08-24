# -*- coding: utf-8 -*-
"""JAMSTEC 일본해양연구개발기구 — 調達情報 お知らせ.

심해 음향, 수중 로봇(AUV), 관측망 관련 기술제안공모(技術提案公募)가
조달정보 알림란에 게시됩니다. 각 항목 링크 글머리에 날짜가 붙어 있습니다.
"""

import re
from urllib.parse import urljoin

from ..fetch import clean, parse_date

SITE = {
    "id": "jamstec",
    "name": "JAMSTEC 일본해양연구개발기구",
    "country": "JP",
    "category": "일본-해양",
    "url": "https://www.jamstec.go.jp/j/about/procurement/",
}

# 링크 글자가 '2026.06.24 ...' 처럼 날짜로 시작하는 것만 공고로 봅니다
ROWS_JS = r"""() => [...document.querySelectorAll('a[href]')]
    .map(a => ({text: (a.innerText || '').replace(/\s+/g, ' ').trim(), href: a.getAttribute('href') || ''}))
    .filter(x => /^20\d{2}[.\-\/]\d{1,2}[.\-\/]\d{1,2}/.test(x.text))"""

DATE_HEAD = re.compile(r"^20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}\s*")


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2500)

    items, seen = [], set()
    for row in page.evaluate(ROWS_JS):
        posted = parse_date(row["text"])
        title = clean(DATE_HEAD.sub("", row["text"]))
        if len(title) < 8:
            continue
        url = urljoin(page.url, row["href"])
        ident = re.sub(r"^https?://[^/]+/", "", url).strip("/")[:180]
        if ident in seen:
            continue
        seen.add(ident)
        items.append({
            "id": ident,
            "title": title,
            "url": url,
            "posted": posted,
            "deadline": "",
            "org": "海洋研究開発機構",
            "extra": "",
        })
    return items
