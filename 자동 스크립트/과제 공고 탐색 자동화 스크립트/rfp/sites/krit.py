# -*- coding: utf-8 -*-
"""국방기술진흥연구소(KRIT) 공지사항.

국방 핵심기술 연구개발, 미래도전국방기술 등 과제 공고가 이 게시판에 올라옵니다.
상세 페이지가 CSRF 토큰이 붙은 POST로만 열려서 직접 링크를 만들 수 없습니다.
그래서 링크는 목록 페이지로 걸고, 제목으로 찾아 들어가도록 했습니다.
"""

import re

from ..fetch import clean

SITE = {
    "id": "krit",
    "name": "국방기술진흥연구소(KRIT)",
    "country": "KR",
    "category": "국방",
    "url": "https://www.krit.re.kr/krit/bbs/notice_list.do?gotoMenuNo=05010000",
}

ROWS_JS = r"""() => [...document.querySelectorAll('ul.listType > li')].map(li => {
    const a = li.querySelector('a[onclick]');
    const d = li.querySelector('li.date');
    return {title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            onclick: a ? (a.getAttribute('onclick') || '') : '',
            date: d ? (d.innerText || '') : ''};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2000)

    items = []
    for row in page.evaluate(ROWS_JS):
        m = re.search(r"fnView\('[^']*','[^']*','(\d+)'", row["onclick"])
        if not m:
            continue
        title = clean(row["title"])
        # 목록 앞에 붙는 '공지' 배지와 글번호 제거
        title = re.sub(r"^(공지|\d+)\s*", "", title).strip()
        if not title:
            continue
        posted = ""
        md = re.search(r"(\d{4}-\d{2}-\d{2})", row["date"])
        if md:
            posted = md.group(1)
        items.append({
            "id": m.group(1),
            "title": title,
            "url": SITE["url"],          # 상세 직링크 불가 (POST + CSRF)
            "posted": posted,
            "deadline": "",
            "org": "국방기술진흥연구소",
            "extra": "",
            "list_only": True,
        })
    return items


def open_detail(page, item, goto):
    """상세가 CSRF POST 전용이라 목록에서 fnView 로 들어갑니다."""
    if not page.url.startswith(SITE["url"].split("?")[0]):
        goto(page, SITE["url"])
        page.wait_for_timeout(800)
    page.evaluate("(id) => fnView('notice', '', id, '1', '', '')", item["id"])
    page.wait_for_load_state("domcontentloaded")
