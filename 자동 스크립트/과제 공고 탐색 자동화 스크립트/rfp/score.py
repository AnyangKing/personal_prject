# -*- coding: utf-8 -*-
"""공고 제목과 첨부 공고문 본문으로 관심도 점수를 매깁니다.

연구실 분야(수중통신·수중위치추정)는 전문 용어가 뚜렷해서
키워드를 3단계로 나눕니다.

    직결(5점)  수중음향, 음향측위, USBL, 소나, 음탐기 …
    분야(3점)  수중, 음향, 해저, AUV …
    인접(1점)  잠수함, 어뢰, 해양, 통신 … (최대 2점)

인접어에 상한을 두는 이유: 잠수함은 플랫폼이지 수중통신 기술이 아닙니다.
상한이 없으면 '잠수함 + 해양 + 통신' 조합만으로 임계값을 넘어버립니다.

첨부 본문에서는 **인접어를 아예 세지 않습니다.** 수만 자짜리 공고문에
'잠수함'이 몇 번 나오는 건 아무 의미가 없기 때문입니다.
(실제로 채용 공고 첨부에 '잠수함'이 4회 나와 오탐이 났습니다)

또한 첨부 점수는 **직결어를 요구합니다.** 직결어가 없으면 분야어가
3종 이상 나와야 인정합니다. 분야어 두 개가 긴 문서에 흩어져 있는 건
제목에 '수중'이 박힌 것(3점)보다 약한 증거이기 때문입니다.
"""

from . import config


def _distinct(words):
    """다른 단어에 포함되는 것은 뺍니다.

    '잠수함'이 걸리면 '잠수'도 자동으로 걸리는데, 이걸 두 종류로 세면
    핵심어 하나뿐인 공고가 기준을 통과해 버립니다.
    """
    out = []
    for w in words:
        if not any(w != o and w.lower() in o.lower() for o in words):
            out.append(w)
    return out


def _found(words, text, skip):
    return [w for w in words if w.lower() not in skip and w.lower() in text]


def score(item):
    """(점수, 걸린 키워드 목록)을 돌려줍니다. 제외 대상은 -1."""
    title = (item.get("title") or "").lower()
    body = (item.get("extra") or "").lower()

    for bad in config.EXCLUDE_KEYWORDS:
        if bad.lower() in title:
            return -1, [bad]

    hits, total = [], 0
    taken = set()

    # ── 제목 ──────────────────────────────────────────────
    for kw in _distinct(_found(config.DIRECT_KEYWORDS, title, taken)):
        hits.append(kw)
        total += config.DIRECT_POINT
        taken.add(kw.lower())

    for kw in _distinct(_found(config.FIELD_KEYWORDS, title, taken)):
        hits.append(kw)
        total += config.FIELD_POINT
        taken.add(kw.lower())

    near = _distinct(_found(config.NEAR_KEYWORDS, title, taken))
    if near:
        hits.extend(near)
        total += min(len(near) * config.NEAR_POINT, config.NEAR_MAX_POINTS)
        taken.update(k.lower() for k in near)

    # ── 첨부 본문 (직결·분야만) ────────────────────────────
    if body:
        b_direct = _found(config.DIRECT_KEYWORDS, body, taken)
        b_field = _found(config.FIELD_KEYWORDS, body, taken)
        kept = _distinct(b_direct + b_field)
        direct_set = {k.lower() for k in config.DIRECT_KEYWORDS}
        n_direct = sum(1 for k in kept if k.lower() in direct_set)
        # 직결어가 하나라도 있거나, 없으면 분야어가 충분히 많아야 인정합니다
        strong = n_direct >= 1 or len(kept) >= config.BODY_MIN_FIELD_ONLY
        if len(kept) >= config.BODY_MIN_DISTINCT and strong:
            points = sum(config.BODY_DIRECT_POINT if k.lower() in direct_set
                         else config.BODY_FIELD_POINT for k in kept)
            total += min(points, config.BODY_MAX_POINTS)
            item["body_hits"] = kept[:12]
            hits.extend(f"{kw}(첨부)" for kw in kept)

    return total, hits


def apply(items):
    """점수를 채워 넣고 높은 순으로 정렬합니다. 제외 대상은 걸러냅니다."""
    kept = []
    for item in items:
        pts, hits = score(item)
        if pts < 0:
            continue
        item["score"] = pts
        item["hits"] = hits
        kept.append(item)
    kept.sort(key=lambda i: (-i["score"], i.get("posted") or "", i["title"]))
    return kept
