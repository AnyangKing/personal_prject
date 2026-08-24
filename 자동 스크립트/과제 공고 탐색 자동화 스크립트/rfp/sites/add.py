# -*- coding: utf-8 -*-
"""국방과학연구소(ADD) 공모안내.

위탁연구기관 선정을 위한 제안서 공모, 특화연구실/특화연구센터 공모가 게시됩니다.
"""

import re

from ..fetch import clean

SITE = {
    "id": "add",
    "name": "국방과학연구소(ADD)",
    "country": "KR",
    "category": "국방",
    "url": "https://www.add.re.kr/kps/publicNtis/ntisList?menuId=MENU02201",
}

BASE = "https://www.add.re.kr"

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[href]');
    return {text: (tr.innerText || '').replace(/\r/g, ''),
            href: a ? (a.getAttribute('href') || '') : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            cells: [...tr.querySelectorAll('td')].map(td => (td.innerText || '').trim())};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2500)

    items = []
    for row in page.evaluate(ROWS_JS):
        href = row["href"]
        m = re.search(r"titleId=(\d+)", href)
        if not m or not row["title"]:
            continue
        cells = row["cells"]
        dates = re.findall(r"(\d{4}-\d{2}-\d{2})", row["text"])
        items.append({
            "id": m.group(1),
            "title": clean(row["title"]),
            "url": BASE + href if href.startswith("/") else href,
            "posted": dates[0] if dates else "",
            "deadline": dates[-1] if len(dates) >= 2 else "",
            "org": "국방과학연구소",
            "extra": cells[0] if cells else "",
        })
    return items
