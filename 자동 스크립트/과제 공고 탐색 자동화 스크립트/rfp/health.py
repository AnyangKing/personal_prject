# -*- coding: utf-8 -*-
"""사이트별 수집량을 기억해 두고 이상 징후를 잡아냅니다.

사이트가 HTML 구조를 바꾸면 예외가 나지 않고 그냥 0건이 반환됩니다.
그대로 두면 몇 달째 못 받고 있어도 알 수 없으므로,
평소 건수(최근 기록의 중앙값)와 비교해 경고합니다.
"""

import json
import statistics

from . import config

HISTORY_FILE = config.DATA_DIR / "rfp_health.json"
KEEP = 7              # 사이트당 보관할 최근 실행 횟수
DROP_RATIO = 0.4      # 평소의 40% 미만이면 급감으로 봅니다
DROP_MIN_BASE = 5     # 평소 건수가 이보다 적으면 급감 판정은 하지 않습니다


def load():
    if not HISTORY_FILE.exists():
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def check(history, site_id, site_name, count):
    """오늘 건수를 평소와 비교해 경고 문구를 돌려줍니다. 이상 없으면 None."""
    rec = history.get(site_id) or {}
    past = [n for n in rec.get("counts", []) if isinstance(n, int)]
    if not past:
        return None                      # 첫 실행 — 비교할 기준이 없습니다

    typical = int(statistics.median(past))

    if count == 0 and typical > 0:
        days = rec.get("zero_days", 0) + 1
        streak = f" — {days}일째" if days > 1 else ""
        return (site_name,
                f"0건 (평소 {typical}건){streak}. 사이트 구조가 바뀌었을 수 있습니다.")

    if typical >= DROP_MIN_BASE and count < typical * DROP_RATIO:
        return (site_name,
                f"{count}건 (평소 {typical}건). 목록 일부만 읽힌 것으로 보입니다.")

    return None


def record(history, site_id, count):
    rec = history.setdefault(site_id, {"counts": [], "zero_days": 0})
    rec["counts"] = (rec.get("counts", []) + [count])[-KEEP:]
    rec["zero_days"] = rec.get("zero_days", 0) + 1 if count == 0 else 0
    return history


def save(history):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=1)
    tmp.replace(HISTORY_FILE)
