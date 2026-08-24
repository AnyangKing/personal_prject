# -*- coding: utf-8 -*-
"""JST 과학기술진흥기구 — 公募中情報一覧.

CREST/PRESTO(さきがけ)/Moonshot, 국제공동연구(SICORP/SATREPS) 공모가 올라옵니다.
목록에 마감일(締切)과 게재일(掲載日)이 함께 있습니다.
"""

import re
from urllib.parse import urljoin

from ..fetch import clean, parse_date

SITE = {
    "id": "jst",
    "name": "JST 과학기술진흥기구",
    "country": "JP",
    "category": "일본-전략기술",
    "url": "https://www.jst.go.jp/bosyu/bosyu.html",
}

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[href]');
    return {href: a ? a.href : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            text: (tr.innerText || '').replace(/\s+/g, ' ').trim(),
            cells: [...tr.querySelectorAll('td,th')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim())};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2500)

    items = []
    for row in page.evaluate(ROWS_JS):
        href, text = row["href"], row["text"]
        if not href or not row["title"] or len(row["title"]) < 6:
            continue
        # 마감일이 적힌 행만 공모로 취급 (지원·상담 안내 행 제외)
        deadline = parse_date(row["cells"][0]) if row["cells"] else ""
        posted = ""
        mp = re.search(r"掲載日\s*[：:]\s*([^）)]+)", text)
        if mp:
            posted = parse_date(mp.group(1))
        if not deadline and not posted:
            continue

        items.append({
            "id": re.sub(r"^https?://(www\.)?jst\.go\.jp/", "", urljoin(SITE["url"], href)).strip("/"),
            "title": clean(row["title"]),
            "url": urljoin(SITE["url"], href),
            "posted": posted,
            "deadline": deadline,
            "org": "JST",
            "extra": row["cells"][1] if len(row["cells"]) > 1 else "",
        })
    return items
