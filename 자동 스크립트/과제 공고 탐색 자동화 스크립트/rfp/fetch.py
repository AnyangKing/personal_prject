# -*- coding: utf-8 -*-
"""Playwright 브라우저 관리 및 공용 수집 헬퍼."""

import re
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from . import config


@contextmanager
def browser_page():
    """설정대로 브라우저를 열고 페이지 하나를 넘겨줍니다."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        ctx = browser.new_context(
            user_agent=config.USER_AGENT,
            locale="ko-KR",
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
            accept_downloads=True,      # 첨부 공고문을 받아 본문까지 읽습니다
        )
        ctx.set_default_timeout(config.NAV_TIMEOUT)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.dismiss())
        try:
            yield page
        finally:
            ctx.close()
            browser.close()


def goto(page, url, wait="domcontentloaded"):
    page.goto(url, wait_until=wait, timeout=config.NAV_TIMEOUT)
    page.wait_for_timeout(1200)


DATE_RE = re.compile(
    r"(20\d{2})\s*[.\-/년年]\s*(\d{1,2})\s*[.\-/월月]\s*(\d{1,2})"
)


def parse_date(text):
    """'2026.08.20', '2026-8-3', '2026年8月3日' 등을 YYYY-MM-DD로."""
    if not text:
        return ""
    m = DATE_RE.search(text)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def parse_period(text):
    """'2026.08.01 ~ 2026.09.01' 처럼 두 날짜가 있으면 뒤엣것이 마감일."""
    if not text:
        return ""
    found = DATE_RE.findall(text)
    if len(found) >= 2:
        y, mo, d = found[-1]
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()
