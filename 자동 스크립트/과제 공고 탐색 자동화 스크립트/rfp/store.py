# -*- coding: utf-8 -*-
"""이미 본 공고 기록. 매일 '신규'만 골라내기 위한 저장소."""

import json
from datetime import datetime, timedelta

from . import config


def _key(item):
    return f"{item['site']}:{item['id']}"


def load():
    if not config.SEEN_FILE.exists():
        return {}
    try:
        with open(config.SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # 파일이 깨졌으면 처음부터 다시 (전부 신규로 잡히지만 동작은 유지)
        return {}


def split_new(items, seen):
    """수집한 공고를 (신규, 기존)으로 나눕니다."""
    fresh, known = [], []
    for item in items:
        (known if _key(item) in seen else fresh).append(item)
    return fresh, known


def save(seen, new_items):
    today = datetime.now().strftime("%Y-%m-%d")
    for item in new_items:
        seen[_key(item)] = {"first_seen": today, "title": item["title"]}

    cutoff = (datetime.now() - timedelta(days=config.SEEN_KEEP_DAYS)).strftime("%Y-%m-%d")
    seen = {k: v for k, v in seen.items() if v.get("first_seen", today) >= cutoff}

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.SEEN_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=1)
    tmp.replace(config.SEEN_FILE)   # 도중에 죽어도 기존 파일이 살아남도록
    return seen
