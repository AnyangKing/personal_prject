# -*- coding: utf-8 -*-
"""NEDO 신에너지·산업기술종합개발기구 — 公募一覧.

해양 무인이동체, 통신 네트워크 등 산업 적용형 실증 프로젝트 공모가 올라옵니다.
공모일람 표에는 공모개시일과 마감일(締切日)이 함께 있습니다.
"""

import re
from urllib.parse import urljoin

from ..fetch import clean, parse_date

SITE = {
    "id": "nedo",
    "name": "NEDO 신에너지·산업기술종합개발기구",
    "country": "JP",
    "category": "일본-실증",
    "url": "https://www.nedo.go.jp/form/event.php?f=koubo.html&state=10000174",
}

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[href]');
    return {href: a ? a.href : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            cells: [...tr.querySelectorAll('td,th')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim())};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(3000)

    items = []
    for row in page.evaluate(ROWS_JS):
        if not row["href"] or not row["title"]:
            continue
        cells = row["cells"]
        dates = [d for d in (parse_date(c) for c in cells) if d]
        m = re.search(r"/([A-Za-z0-9_]+)\.html", row["href"])
        items.append({
            "id": m.group(1) if m else row["href"],
            "title": clean(row["title"]),
            "url": urljoin(SITE["url"], row["href"]),
            "posted": dates[0] if dates else "",
            "deadline": dates[1] if len(dates) > 1 else "",
            "org": "NEDO",
            "extra": cells[1] if len(cells) > 1 else "",
        })
    return items
