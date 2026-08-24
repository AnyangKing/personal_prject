# -*- coding: utf-8 -*-
"""민군협력진흥원(ICMTC) 공지사항.

민군겸용기술개발사업, 민군기술이전·적용·실용화 과제의 연구개발계획서 공모가
이 게시판에 올라옵니다. (사용자가 알려준 icpc.re.kr 은 현재 icmtc.re.kr 입니다)
"""

import re

from ..fetch import clean

SITE = {
    "id": "icpc",
    "name": "민군협력진흥원(ICMTC)",
    "country": "KR",
    "category": "국방",
    "url": "https://www.icmtc.re.kr/board?menuId=MENU00333",
}

BASE = "https://www.icmtc.re.kr"

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[href]');
    return {href: a ? (a.getAttribute('href') || '') : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            text: (tr.innerText || '').replace(/\s+/g, ' ')};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2500)

    items = []
    for row in page.evaluate(ROWS_JS):
        m = re.search(r"linkId=(\d+)", row["href"])
        if not m or not row["title"]:
            continue
        md = re.search(r"(\d{4}-\d{2}-\d{2})", row["text"])
        items.append({
            "id": m.group(1),
            "title": clean(row["title"]),
            "url": BASE + row["href"] if row["href"].startswith("/") else row["href"],
            "posted": md.group(1) if md else "",
            "deadline": "",
            "org": "민군협력진흥원",
            "extra": "",
        })
    return items
