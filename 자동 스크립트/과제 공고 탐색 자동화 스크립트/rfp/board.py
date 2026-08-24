# -*- coding: utf-8 -*-
"""여러 사이트가 공유하는 단순 목록형 게시판 수집기.

'날짜 + 제목 링크'가 반복되는 흔한 구조를 한 함수로 처리합니다.
사이트별 모듈은 선택자만 넘기면 됩니다.
"""

import re
from urllib.parse import urljoin

from .fetch import clean, parse_date

ROWS_JS = r"""(sel) => [...document.querySelectorAll(sel)].map(el => {
    const a = el.querySelector('a[href]');
    return {href: a ? a.getAttribute('href') : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            text: (el.innerText || '').replace(/\s+/g, ' ').trim()};
})"""


def simple_list(page, goto, site, row_sel, org="", min_title=8):
    """row_sel 로 잡은 각 행에서 링크·제목·날짜를 뽑아냅니다."""
    goto(page, site["url"])
    page.wait_for_timeout(2500)

    items = []
    for row in page.evaluate(ROWS_JS, row_sel):
        href, title = row["href"], clean(row["title"])
        if not href or len(title) < min_title:
            continue
        url = urljoin(page.url, href)
        # 링크 경로를 그대로 고유 id 로 사용 (게시글 번호가 없는 사이트가 많습니다)
        ident = re.sub(r"^https?://[^/]+/", "", url).strip("/") or url
        items.append({
            "id": ident[:180],
            "title": title,
            "url": url,
            "posted": parse_date(row["text"]),
            "deadline": "",
            "org": org or site["name"],
            "extra": "",
        })
    return items
