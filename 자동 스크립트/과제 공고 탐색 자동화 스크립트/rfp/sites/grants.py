# -*- coding: utf-8 -*-
"""grants.gov — 미국 연방정부 보조금 포털.

조달이 아니라 연구비입니다. ONR(미 해군연구청)·NRL·NSWC 가
수중음향·수중통신 연구를 여기에 BAA 로 올립니다.

공개 검색 API 를 씁니다(키 불필요). 브라우저가 필요 없어 page 는 쓰지 않습니다.

**수급 자격 판정이 이 모듈의 핵심입니다.**
한국 대학은 외국(non-U.S.) 기관이라, 미국 기관 한정 공고는 봐야 의미가 없습니다.
그런데 grants.gov 에는 '외국 기관' 코드가 따로 없어서 본문 문구로 판단합니다.

    가능 — 'Non-domestic (non-U.S.) Entities' 처럼 외국 기관 허용이 명시됨
    불가 — 'only to U.S. Institutions', 'must be U.S. citizens' 등 명시적 배제
    불명 — 요약에 언급 없음 (자격이 첨부 BAA 문서 안에 있는 경우가 많습니다)

기본값은 **불가로 판정된 것만 제외**합니다. ONR·NRL 의 큰 BAA 가 대부분
'불명'이라, 명시된 것만 남기면 정작 분야 적합도가 높은 공고가 전부 빠집니다.
엄격하게 보시려면 config.GRANTS_STRICT 를 True 로 바꾸세요.
"""

import json
import re
import time
import urllib.request
from datetime import datetime

from .. import config
from ..fetch import clean

SITE = {
    "id": "grants",
    "name": "grants.gov 미국 연방 연구비",
    "country": "US",
    "category": "해외",
    "url": "https://www.grants.gov/search-grants",
}

SEARCH = "https://api.grants.gov/v1/api/search2"
FETCH = "https://api.grants.gov/v1/api/fetchOpportunity"
DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"

REQUEST_GAP = 0.4        # 연방 API 에 부담을 주지 않도록
MAX_DETAIL = 40

# 외국 기관 허용이 명시된 표현
FOREIGN_OK = re.compile(
    r"non-domestic\s*\(non-U\.?S\.?\)\s*entit"
    r"|foreign\s+(institution|entit|organization|applicant|univer)"
    r"|non-U\.?S\.?[ -](institution|entit|organization)s?\s+(are|may)"
    r"|international\s+(applicant|organization|institution)", re.I)

# 미국 한정이 명시된 표현
US_ONLY = re.compile(
    r"only\s+to\s+U\.?S\.?"
    r"|must\s+be\s+(a\s+|an\s+)?U\.?S\.?\s*(citizen|institution|entit|organization)"
    r"|all\s+proposed\s+personnel\s+must\s+be\s+U\.?S\.?\s*citizen"
    r"|foreign\s+(entit|institution|organization)s?\s+are\s+not\s+eligible"
    r"|limited\s+to\s+U\.?S\.?\s*(institution|entit|organization)", re.I)


def _post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def _iso(mmddyyyy):
    try:
        return datetime.strptime(mmddyyyy, "%m/%d/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def _strip(html_text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text or "")).strip()


def judge(text):
    """(판정, 근거 문장). 판정은 '가능'·'불가'·'불명'."""
    ok, no = FOREIGN_OK.search(text), US_ONLY.search(text)
    if ok and not no:
        return "가능", text[max(0, ok.start() - 60):ok.end() + 90]
    if no and not ok:
        return "불가", text[max(0, no.start() - 60):no.end() + 90]
    if ok and no:
        # 둘 다 나오면 대개 '외국 기관도 신청 가능' 목록과 개별 제한이 함께 있는 경우입니다
        return "가능", text[max(0, ok.start() - 60):ok.end() + 90]
    return "불명", ""


def collect(page, goto):
    found = {}
    for kw in config.GRANTS_KEYWORDS:
        try:
            res = _post(SEARCH, {"keyword": kw, "oppStatuses": "forecasted|posted", "rows": 25})
        except Exception:
            continue
        for h in res.get("data", {}).get("oppHits", []):
            rec = found.setdefault(str(h["id"]), dict(h, _kw=[]))
            if kw not in rec["_kw"]:
                rec["_kw"].append(kw)
        time.sleep(REQUEST_GAP)

    items = []
    for n, (oid, h) in enumerate(found.items()):
        if n >= MAX_DETAIL:
            break
        syn = {}
        try:
            d = _post(FETCH, {"opportunityId": int(oid)})
            syn = d.get("data", {}).get("synopsis", {}) or {}
        except Exception:
            pass
        time.sleep(REQUEST_GAP)

        body = _strip((syn.get("applicantEligibilityDesc") or "") + " "
                      + (syn.get("synopsisDesc") or ""))

        # 우리가 도메인 키워드로 '검색해서' 찾은 것이므로, grants.gov 전문 검색이
        # 이 공고를 그 키워드로 판정했다는 사실 자체가 근거입니다.
        # 요약문에 그 단어가 없다고 0점 처리하면 ONR BAA 같은 게 통째로 묻힙니다.
        matched = h.get("_kw", [])
        scored_body = body + " | grants.gov 검색어: " + ", ".join(matched)
        verdict, why = judge(body)

        # 미국 기관 한정이 명시된 공고는 봐도 의미가 없으므로 버립니다
        if verdict == "불가":
            continue
        if config.GRANTS_STRICT and verdict != "가능":
            continue

        items.append({
            "id": oid,
            "title": clean(h.get("title", "")),
            "url": DETAIL_URL.format(id=oid),
            "posted": _iso(h.get("openDate")),
            "deadline": _iso(h.get("closeDate")),
            "org": clean(h.get("agency", "")),
            "extra": scored_body[:20000],   # 채점 대상
            "matched_kw": matched,
            "eligibility": verdict,
            "eligibility_why": why[:220],
        })
    return items
