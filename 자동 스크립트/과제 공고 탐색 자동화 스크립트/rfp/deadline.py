# -*- coding: utf-8 -*-
"""첨부 공고문 본문에서 접수 마감일을 추정합니다.

KRIT·DAPA·ICMTC 같은 게시판은 목록에 마감일 컬럼이 아예 없어서
언제까지 내야 하는지 알 수가 없습니다. 접수기간은 공고문 안에 있으므로
이미 받아 둔 본문에서 뽑아냅니다.

추정값은 화면에 '(추정)'으로 점선 표시하고, 마우스를 올리면 근거 문장이 보입니다.
`config.HIDE_EXPIRED_GUESS` 가 켜져 있으면 이 추정으로도 지난 공고를 걸러냅니다.
잘못 읽으면 살아 있는 공고가 사라지므로, 이상하면 그 설정을 끄세요.

설명회처럼 '접수'가 아니라 '개최'인 공고는 event() 로 행사일을 뽑습니다.
그 날이 지났으면 지난 공고입니다.
"""

import re
from datetime import date

# 전각 숫자를 반각으로 (일본 공고문은 ９月３０日 처럼 씁니다)
ZEN = str.maketrans("０１２３４５６７８９", "0123456789")

# 접수 마감을 가리키는 표현
KEY = re.compile(
    r"(접수|신청|제출|공모|응모|등록)\s*(기간|기한|마감|일정|기일|일자|일시|일)"
    r"|마감\s*(일시|일자|일)"
    # 일본어
    r"|締切|締め切り|〆切|応募期限|提出期限|受付期限|申請期限"
    r"|(受付|応募|公募|提出|申請)\s*期間"
)

# 마감일이 아닌 '까지'. 이런 동작을 가리키면 버립니다.
# ('설명회 장소에 입장 ... 까지', '다음 해 3월 31일까지 통보' 등)
NOT_DEADLINE = re.compile(
    r"입장|참석|참가|통보|보고|점검|열람|공개|게시|배포"
    r"|掲載しました|公表|採択課題|審査結果|終了しました"
)

# 2026. 9. 11. / 2026-09-11 / 2026년 9월 11일 / ’26년 9월 11일 / 9.11. / 2026年9月11日
FULL = re.compile(
    r"(?:(\d{2,4})\s*[.\-년年]\s*)?(\d{1,2})\s*[.\-월月]\s*(\d{1,2})\s*[.일日]?")

# 令和8年9月30日 → 2026-09-30 (令和 N년 = 2018 + N)
WAREKI = re.compile(r"令和\s*(\d{1,2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?")
REIWA_BASE = 2018

MAX_LINE = 200
MAX_AHEAD_DAYS = 730     # 이보다 먼 미래는 오독으로 봅니다

# 날짜로 오독되는 것들: 이메일·URL·전화번호·시각
# (a07-10186@mnd.go.kr 의 '07-10' 이 7월 10일로 읽힌 적이 있습니다)
NOISE = re.compile(
    r"[\w.+-]+@[\w.-]+"
    r"|https?://\S+"
    r"|\d{2,4}-\d{3,4}-\d{4}"
    r"|\d{1,2}\s*:\s*\d{2}"
)


def _normalize_jp(text):
    """전각 숫자를 반각으로, 和暦을 서기로 바꿉니다."""
    text = text.translate(ZEN)
    return WAREKI.sub(
        lambda m: f"{REIWA_BASE + int(m.group(1))}年{m.group(2)}月{m.group(3)}日", text)


def _norm_year(y, month, day, base):
    """연도가 없거나 두 자리면 공고일 기준으로 채웁니다."""
    if y is None:
        year = base.year
    else:
        y = int(y)
        year = y if y >= 1000 else 2000 + y
    try:
        got = date(year, int(month), int(day))
    except ValueError:
        return None
    # 연도를 추정한 경우, 공고일보다 과거로 나오면 이듬해로 봅니다
    if y is None and got < base:
        try:
            got = date(year + 1, int(month), int(day))
        except ValueError:
            return None
    return got


def guess(text, posted=""):
    """(YYYY-MM-DD, 근거 문장). 못 찾으면 ("", "")."""
    if not text:
        return "", ""

    try:
        base = date.fromisoformat(posted) if posted else date.today()
    except ValueError:
        base = date.today()

    text = _normalize_jp(text)
    lines = [NOISE.sub(" ", re.sub(r"\s+", " ", ln)).strip()
             for ln in text.split("\n")]
    # HWP 표는 '접수기간 :' 라벨과 날짜가 서로 다른 줄로 쪼개집니다.
    # 그래서 앞줄에 라벨이 있으면 이 줄도 마감일 후보로 봅니다.
    keyed, loose = [], []
    for i, ln in enumerate(lines):
        if not (6 < len(ln) < MAX_LINE) or not re.search(r"\d", ln):
            continue
        if NOT_DEADLINE.search(ln):
            continue
        prev = lines[i - 1] if i else ""
        if KEY.search(ln) or (KEY.search(prev) and len(prev) < MAX_LINE):
            keyed.append(ln)
        elif "까지" in ln or "まで" in ln:
            loose.append(ln)

    for group in (keyed, loose):
        for line in group:
            found = FULL.findall(line)
            # 날짜처럼 보이는 것만 남깁니다 (월 1~12, 일 1~31)
            cand = []
            for y, m, d in found:
                if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                    got = _norm_year(y or None, m, d, base)
                    if got:
                        cand.append(got)
            if not cand:
                continue
            # 기간 표현이면 '읽는 순서상 마지막'이 마감입니다.
            # max() 를 쓰면 뒤에 섞인 엉뚱한 숫자에 끌려갑니다.
            end = cand[-1]
            if end < base:
                continue
            if (end - base).days > MAX_AHEAD_DAYS:
                continue
            return end.isoformat(), line[:120]

    return "", ""


# 설명회·간담회처럼 '접수'가 아니라 '개최'인 공고
EVENT_TITLE = re.compile(r"설명회|간담회|공청회|개최\s*안내|세미나|워크숍|説明会")
EVENT_LINE = re.compile(r"일\s*시|개최\s*일|日\s*時")


def event(text, posted=""):
    """설명회 등의 개최일. 이 날이 지났으면 그 공고는 지난 것입니다."""
    if not text:
        return "", ""
    try:
        base = date.fromisoformat(posted) if posted else date.today()
    except ValueError:
        base = date.today()

    text = text.translate(ZEN)
    text = WAREKI.sub(
        lambda m: f"{REIWA_BASE + int(m.group(1))}年{m.group(2)}月{m.group(3)}日", text)
    for raw in text.split("\n"):
        line = NOISE.sub(" ", re.sub(r"\s+", " ", raw)).strip()
        if not (6 < len(line) < MAX_LINE) or not EVENT_LINE.search(line):
            continue
        for y, m, d in FULL.findall(line):
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                got = _norm_year(y or None, m, d, base)
                if got and (got - base).days <= MAX_AHEAD_DAYS:
                    return got.isoformat(), line[:120]
    return "", ""
