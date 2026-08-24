# -*- coding: utf-8 -*-
"""NTIS 국가R&D통합정보서비스 — 국가 R&D 통합 공고.

부처별 공고가 한곳에 모이고 접수 상태·마감일·D-day까지 목록에 나옵니다.
IRIS와 겹치는 공고도 있지만 NTIS에만 올라오는 부처 공고가 있어 함께 봅니다.
"""

import re

from ..fetch import clean

SITE = {
    "id": "ntis",
    "name": "NTIS 국가R&D통합공고",
    "country": "KR",
    "category": "통합포털",
    "url": "https://www.ntis.go.kr/rndgate/eg/un/ra/mng.do",
}

VIEW_URL = "https://www.ntis.go.kr/rndgate/eg/un/ra/view.do?roRndUid={}&flag=rndList"

ROWS_JS = r"""() => [...document.querySelectorAll('table tbody tr')].map(tr => {
    const a = tr.querySelector('a[onclick]');
    return {cells: [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim()),
            onclick: a ? (a.getAttribute('onclick') || '') : '',
            title: a ? (a.innerText || '').replace(/\s+/g, ' ').trim() : ''};
})"""

DATE = re.compile(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})")


def _norm(text):
    m = DATE.search(text or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(3000)

    # 기본 10건만 나오므로 한 페이지에 100건을 받도록 바꿔 다시 조회합니다
    try:
        page.evaluate("""() => {
            const sel = document.querySelector('[name=pageUnit]');
            if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
            if (typeof fn_search === 'function') fn_search(1);
        }""")
        page.wait_for_timeout(3500)
    except Exception:
        pass          # 실패해도 기본 10건으로 계속 진행

    items = []
    for row in page.evaluate(ROWS_JS):
        m = re.search(r"fn_view\('(\d+)'\)", row["onclick"])
        if not m or not row["title"]:
            continue
        cells = row["cells"]
        dates = [_norm(c) for c in cells if DATE.search(c)]
        org = ""
        for c in cells:
            if c.endswith(("부", "청", "처", "위원회")) and len(c) <= 20:
                org = c
                break
        status = cells[1] if len(cells) > 1 and "접수" in cells[1] else ""

        items.append({
            "id": m.group(1),
            "title": clean(row["title"]),
            "url": VIEW_URL.format(m.group(1)),
            "posted": dates[0] if dates else "",
            "deadline": dates[1] if len(dates) > 1 else "",
            "org": org,
            "extra": status,
        })
    return items
