# -*- coding: utf-8 -*-
"""ATLA 방위장비청 — 安全保障技術研究推進制度.

수중 음향 탐지·수중 통신·센서 신호처리 과제를 대학/연구소 대상으로 정기 공모합니다.
공모는 보통 연 1회라 상시 목록 대신 제도 페이지의 갱신 소식을 감시합니다.
(공모 개시 공지가 이 목록에 뜹니다)
"""

from .. import board

SITE = {
    "id": "atla",
    "name": "ATLA 방위장비청",
    "country": "JP",
    "category": "일본-안보",
    "url": "https://www.mod.go.jp/atla/funding.html",
}


def collect(page, goto):
    return board.simple_list(page, goto, SITE, "ul.news-list li", org="防衛装備庁")


KOUBO_URL = "https://www.mod.go.jp/atla/funding/koubo.html"


def detail_url(item):
    """4개 항목이 모두 같은 공모 페이지를 가리킵니다 (요청을 한 번으로 합칩니다)."""
    return KOUBO_URL


def open_detail(page, item, goto):
    """항목 링크는 같은 페이지의 앵커뿐이라, 공모요령이 있는 공모 페이지를 엽니다."""
    goto(page, KOUBO_URL)
