# -*- coding: utf-8 -*-
"""JSPS 일본학술진흥회 — 国際共同研究事業 공모.

한국연구재단(NRF)과 연계되는 한-일 양자 협력 공동연구가 이 사업에서 나옵니다.

예전에는 첫 화면의 신착 소식을 긁었는데, 그 목록은 대부분
'採択課題を掲載しました'(선정 결과)·'事後評価' 같은 소식이라
공고가 아니었습니다. 13건을 가져와도 쓸모가 없었습니다.

지금은 **프로그램별 申請手続き 페이지**를 봅니다. 각 프로그램 페이지에
그 해 공모가 열려 있는지, 마감이 언제인지가 적혀 있습니다.
'募集は終了' 이라고 적힌 프로그램은 내보내지 않습니다.

공모는 연 1회라 같은 주소가 해마다 갱신됩니다. 그래서 id 에 연도를 넣어
새 해 공모가 열리면 새 공고로 잡히게 합니다.
"""

import re
from urllib.parse import urljoin

from ..deadline import guess

INDEX = "https://www.jsps.go.jp/j-bottom/index.html"

SITE = {
    "id": "jsps",
    "name": "JSPS 일본학술진흥회",
    "country": "JP",
    "category": "일본-국제공동연구",
    "url": INDEX,
}

CLOSED = re.compile(r"募集(は|を)?終了|公募(は|を)?終了|受付(は|を)?終了")
YEAR = re.compile(r"令和\s*(\d{1,2})\s*[（(]?\s*(\d{4})?")

PATHS_JS = """() => [...document.querySelectorAll('a[href*="_sinsei.html"]')]
    .map(a => a.getAttribute('href'))"""


def _program_name(title):
    """'申請手続き｜스위스와의 …｜国際共同研究事業' 에서 프로그램명만."""
    parts = [x.strip() for x in (title or "").split("｜")]
    return parts[1] if len(parts) > 1 else (title or "")[:60]


def _year(body):
    m = YEAR.search(body or "")
    if not m:
        return ""
    if m.group(2):
        return m.group(2)
    return str(2018 + int(m.group(1)))      # 令和 N년 = 2018 + N


def collect(page, goto):
    goto(page, INDEX)
    page.wait_for_timeout(2000)

    paths = []
    for href in page.evaluate(PATHS_JS):
        if href and href not in paths:
            paths.append(href)

    items = []
    for href in paths:
        url = urljoin(INDEX, href)
        try:
            goto(page, url)
            page.wait_for_timeout(1400)
            title = page.title()
            body = page.inner_text("body")
        except Exception:
            continue

        if CLOSED.search(re.sub(r"\s+", " ", body)):
            continue                    # 이번 해 공모가 이미 끝난 프로그램

        prog = _program_name(title)
        year = _year(body)
        slug = href.rsplit("/", 1)[-1].replace(".html", "")
        deadline, _ = guess(body, "")

        items.append({
            "id": f"{slug}:{year}" if year else slug,
            "title": f"{prog} 공모" if year == "" else f"[{year}년도] {prog} 공모",
            "url": url,
            "posted": "",
            "deadline": deadline,
            "org": "日本学術振興会",
            "extra": re.sub(r"\s+", " ", body)[:20000],
        })
    return items
