# -*- coding: utf-8 -*-
"""IRIS 범부처통합연구지원시스템 — 접수중 사업공고.

국내 부처 R&D 공고는 대부분 IRIS로 통합 접수됩니다.
한국연구재단(NRF), 해양수산과학기술진흥원(KIMST), 정보통신기획평가원(IITP),
한국산업기술기획평가원(KEIT), 국방기술품질원 공고가 모두 여기로 올라옵니다.
"""

import re

from ..fetch import clean

SITE = {
    "id": "iris",
    "name": "IRIS 범부처통합연구지원시스템",
    "country": "KR",
    "category": "통합포털",
    "url": "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do",
}

VIEW_URL = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId={}"
MAX_PAGES = 5

ROWS_JS = r"""() => [...document.querySelectorAll('ul.dbody > li')].map(li => {
    const a = li.querySelector('a[onclick]');
    const oc = a ? (a.getAttribute('onclick') || '') : '';
    return {text: (li.innerText || '').replace(/\r/g, ''), onclick: oc};
})"""


def _parse(row):
    text = row["text"]
    m = re.search(r"'(\d+)'", row["onclick"])
    if not m:
        return None
    ancm_id = m.group(1)

    lines = [clean(l) for l in text.split("\n") if clean(l)]
    org = next((l for l in lines if ">" in l), "")
    # 기관 라인 다음 줄이 공고명
    title = ""
    if org in lines:
        idx = lines.index(org)
        if idx + 1 < len(lines):
            title = lines[idx + 1]
    if not title:
        title = lines[0] if lines else ""

    posted = ""
    mo = re.search(r"공고일자\s*:?\s*(\d{4}-\d{2}-\d{2})", text)
    if mo:
        posted = mo.group(1)

    no = ""
    mn = re.search(r"공고번호\s*:?\s*(\S+)", text)
    if mn:
        no = mn.group(1)

    return {
        "id": ancm_id,
        "title": title,
        "url": VIEW_URL.format(ancm_id),
        "posted": posted,
        "deadline": "",
        "org": org,
        "extra": f"{org} {no}",
    }


def collect(page, goto):
    goto(page, SITE["url"])
    page.wait_for_timeout(3000)

    items, seen_ids = [], set()
    for pageno in range(1, MAX_PAGES + 1):
        if pageno > 1:
            try:
                page.evaluate(f"() => f_bsnsAncmBtinSituListForm_search({pageno})")
                page.wait_for_timeout(2500)
            except Exception:
                break
        rows = page.evaluate(ROWS_JS)
        if not rows:
            break
        added = 0
        for row in rows:
            item = _parse(row)
            if item and item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                items.append(item)
                added += 1
        if added == 0:          # 같은 페이지가 반복되면 중단
            break
    return items


def enrich(page, item, goto):
    """신규 공고만 상세를 열어 접수기간(마감일)을 채웁니다."""
    goto(page, item["url"])
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    m = re.search(r"접수기간\s*\|?\s*(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})", text)
    if not m:
        m = re.search(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        item["deadline"] = m.group(2)
    return item
