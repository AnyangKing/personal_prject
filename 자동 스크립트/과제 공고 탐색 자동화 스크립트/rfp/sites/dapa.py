# -*- coding: utf-8 -*-
"""방위사업청(DAPA) — 공지사항.

방위사업 정책·산학협력 지원사업 공고가 올라오는 자체 게시판입니다.
'국방조달공고' 메뉴는 국방전자조달(d2b)로 넘어가는데 그쪽은
부대 이사용역·시설정비 같은 물품/용역 입찰이 대부분이라 쓰지 않습니다.

표준 전자정부 게시판이라 상세가 GET으로 열립니다(직접 링크 가능).
기본 10건이라 recordCountPerPage 로 50건까지 받아옵니다.
"""

import re

from ..fetch import clean, parse_date

SITE = {
    "id": "dapa",
    "name": "방위사업청(DAPA)",
    "country": "KR",
    "category": "국방",
    "url": ("https://www.dapa.go.kr/dapa/doc/selectDocList.do"
            "?menuSeq=3031&bbsSeq=443&recordCountPerPage=50"),
}

DETAIL = ("https://www.dapa.go.kr/dapa/doc/selectDoc.do"
          "?docSeq={doc}&menuSeq=3031&bbsSeq=443")

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a.subject-anchor, a[onclick*="fn_selectDoc"]');
    return {title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            onclick: a ? (a.getAttribute('onclick') || '') : '',
            cells: [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim())};
})"""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(2500)

    items = []
    for row in page.evaluate(ROWS_JS):
        title = clean(row["title"])
        m = re.search(r"fn_selectDoc\('(\d+)'\)", row["onclick"])
        if not title or not m:
            continue
        cells = row["cells"]
        # 컬럼: 번호 | 분류 | 제목 | 첨부파일 | 작성자 | 게시일 | 조회수
        posted = ""
        for c in reversed(cells):
            posted = parse_date(c)
            if posted:
                break
        items.append({
            "id": m.group(1),
            "title": title,
            "url": DETAIL.format(doc=m.group(1)),
            "posted": posted,
            "deadline": "",
            "org": cells[1] if len(cells) > 1 else "",
            "extra": "",
        })
    return items
