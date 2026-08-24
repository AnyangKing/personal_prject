# -*- coding: utf-8 -*-
"""e-Rad 府省共通研究開発管理システム — 公募一覧.

일본 전 부처의 R&D 공모가 등록되는 통합 포털입니다.
목록이 iframe 안에 들어 있어 iframe 주소로 바로 접근합니다.
상세는 폼 전송으로만 열려서 링크는 공모일람 페이지로 겁니다.

기본 표시가 10건뿐이라 그대로 두면 대부분을 놓칩니다(실측 60건 규모).
表示件数를 100으로 올린 뒤 검색을 눌러서 받아옵니다.
100건을 꽉 채우면 그 이상이 잘렸을 수 있으니 로그에 표시합니다.
"""

import re

from ..fetch import clean, parse_date

SITE = {
    "id": "erad",
    "name": "e-Rad 일본 부처공통 공모일람",
    "country": "JP",
    "category": "일본-통합포털",
    "url": "https://www.e-rad.go.jp/eRad/E1031S02?lang=ja",
}

PUBLIC_URL = "https://www.e-rad.go.jp/offer_list.html"

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[onclick]');
    return {cells: [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim()),
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : '',
            onclick: a ? (a.getAttribute('onclick') || '') : ''};
})"""


PAGE_SIZE = "0100"      # 表示件数 셀렉트 값 (0010/0025/0050/0075/0100)


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(3500)

    # 표시 건수를 100으로 올리고 다시 검색 (기본 10건이면 대부분 잘립니다)
    try:
        page.select_option('select[name="hyojiKensu"]', PAGE_SIZE)
        page.wait_for_timeout(600)
        page.locator("a:has-text('検索'), button:has-text('検索'), input[value='検索']").first.click()
        page.wait_for_timeout(4000)
    except Exception:
        pass        # 실패해도 기본 10건으로는 수집되도록 둡니다

    items = []
    for row in page.evaluate(ROWS_JS):
        cells, title = row["cells"], clean(row["title"])
        if len(cells) < 3 or not title:
            continue
        m = re.search(r"makeSendData\('([^']+)'\)", row["onclick"])
        items.append({
            "id": m.group(1) if m else title[:80],
            "title": title,
            "url": PUBLIC_URL,          # 상세는 폼 전송 전용 (직링크 불가)
            "posted": parse_date(cells[0]),
            "deadline": parse_date(cells[-1]) if len(cells) > 5 else "",
            "org": cells[1],
            "extra": "",
            "list_only": True,
        })

    if len(items) >= 100:
        print("    ! e-Rad 100건을 채웠습니다 — 그 이상이 잘렸을 수 있습니다")
    return items
