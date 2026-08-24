# -*- coding: utf-8 -*-
"""선박해양플랜트연구소(KRISO) — 공지사항.

국내 무인잠수정·수중로봇 연구의 중심 기관입니다.
위탁연구·용역 제안공모가 이 게시판으로 나갑니다.

메뉴가 JS 라 게시판 주소가 겉으로 안 보이는데,
실제 목록은 board.es 로 직접 열립니다. 상세도 GET 이라 직접 링크가 됩니다.
"""

import re

from ..fetch import clean, parse_date

BASE = "https://www.kriso.re.kr"

SITE = {
    "id": "kriso",
    "name": "선박해양플랜트연구소(KRISO)",
    "country": "KR",
    "category": "해양",
    "url": f"{BASE}/board.es?mid=a10401000000&bid=0010&nPage=1",
}

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[href]');
    return {href: a ? (a.getAttribute('href') || '') : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            cells: [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim())};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2200)

    items = []
    for row in page.evaluate(ROWS_JS):
        title = clean(row["title"])
        m = re.search(r"list_no=(\d+)", row["href"])
        if not title or not m:
            continue
        cells = row["cells"]
        posted = ""
        for c in reversed(cells):
            posted = parse_date(c)
            if posted:
                break
        items.append({
            "id": m.group(1),
            "title": title,
            "url": BASE + row["href"] if row["href"].startswith("/") else row["href"],
            "posted": posted,
            "deadline": "",
            "org": cells[1] if len(cells) > 1 else "",
            "extra": "",
        })
    return items
