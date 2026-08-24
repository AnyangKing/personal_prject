# -*- coding: utf-8 -*-
"""내용이 바뀌는 감시 페이지.

ATLA·JSPS 처럼 **연 1회 공모**를 내는 곳은 새 글이 올라오는 게 아니라
같은 주소의 페이지 내용이 바뀝니다. '새 글번호 = 신규' 방식으로는
공모가 열려도 알 수가 없습니다.

그래서 본문을 저장해 두고 다음 실행에서 비교합니다.
**새로 생긴 줄**이 있으면 그것을 하나의 공고 항목으로 만들어
기존 채점·리포트·알림 흐름에 그대로 태웁니다.
(변경분이 채점 대상이므로 '水中'이 새로 등장하면 바로 점수를 받습니다)
"""

import hashlib
import json
import re
from datetime import datetime

from . import config, deadline

SNAP_FILE = config.DATA_DIR / "rfp_pages.json"

MIN_NEW_CHARS = 25          # 이보다 적게 바뀌면 잡음으로 봅니다
KEEP_LINES = 400            # 페이지당 보관할 줄 수
MAX_SHOW = 6                # 리포트에 보여 줄 변경 줄 수

# 매번 달라져서 변경으로 오인되는 것들
VOLATILE = re.compile(
    r"Ray ID\S*|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*\d{1,2}:\d{2}"
    r"|조회\s*\d+|アクセス数\s*\d+|\bsessionid=\S+", re.I)

BOT_WALL = re.compile(
    r"보안 확인|Ray ID|Just a moment|Checking your browser"
    r"|Cloudflare|セキュリティ確認|アクセスが拒否")


def load():
    if not SNAP_FILE.exists():
        return {}
    try:
        with open(SNAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(snaps):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SNAP_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snaps, f, ensure_ascii=False, indent=1)
    tmp.replace(SNAP_FILE)


def normalize(text):
    """비교에 쓸 줄 목록. 공백과 변동 요소를 정리합니다."""
    out = []
    for raw in (text or "").split("\n"):
        line = VOLATILE.sub(" ", re.sub(r"\s+", " ", raw)).strip()
        if len(line) >= 4:
            out.append(line)
    return out[:KEEP_LINES]


def check(page, goto, snaps, log):
    """감시 페이지를 훑어 변경분을 공고 항목으로 만들어 돌려줍니다."""
    items = []
    for cfg in config.WATCH_PAGES:
        try:
            goto(page, cfg["url"])
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
        except Exception as exc:
            log(f"    ~ 감시 실패 {cfg['name'][:20]} — {exc.__class__.__name__}")
            continue

        if BOT_WALL.search(body) and len(body) < 1200:
            log(f"    ~ 감시 보류 {cfg['name'][:20]} — 봇 차단 화면")
            continue

        lines = normalize(body)
        if not lines:
            continue

        prev = snaps.get(cfg["id"], {})
        old = set(prev.get("lines", []))
        snaps[cfg["id"]] = {
            "lines": lines,
            "at": datetime.now().strftime("%Y-%m-%d"),
        }

        if not prev:
            log(f"    · 감시 시작 {cfg['name'][:24]} ({len(lines)}줄 기준 저장)")
            continue

        fresh = [ln for ln in lines if ln not in old]
        if sum(len(x) for x in fresh) < MIN_NEW_CHARS:
            continue

        body_new = "\n".join(fresh)
        digest = hashlib.sha1(body_new.encode("utf-8")).hexdigest()[:10]
        today = datetime.now().strftime("%Y-%m-%d")
        dl, _ = deadline.guess(body_new, today)

        items.append({
            "site": "watch",
            "site_name": cfg["name"],
            "country": cfg.get("country", "JP"),
            "category": "감시 페이지",
            "id": f"{cfg['id']}:{digest}",
            "title": f"[내용 변경] {cfg['name']}",
            "url": cfg["url"],
            "posted": today,
            "deadline": "",
            "deadline_guess": dl,
            "org": "",
            "extra": body_new,          # 변경분이 채점 대상입니다
            "changed": fresh[:MAX_SHOW],
            "changed_total": len(fresh),
        })
        log(f"    ! 변경 감지 {cfg['name'][:24]} — 새 줄 {len(fresh)}개")

    return items
