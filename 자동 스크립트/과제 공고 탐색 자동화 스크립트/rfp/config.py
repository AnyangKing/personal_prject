# -*- coding: utf-8 -*-
"""공고 수집기 설정. 동작을 바꾸고 싶으면 이 파일만 고치면 됩니다."""

from pathlib import Path

# rfp/config.py -> rfp/ -> 자동 스크립트/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "리포트"
SEEN_FILE = DATA_DIR / "rfp_seen.json"
LOG_FILE = DATA_DIR / "rfp_watch.log"

# ── 실행 옵션 ─────────────────────────────────────────────
HEADLESS = True          # False로 두면 브라우저 창이 보입니다(디버깅용)
NAV_TIMEOUT = 30000      # 페이지 이동 타임아웃(ms)
SITE_RETRY = 2           # 사이트당 실패 시 재시도 횟수
SEEN_KEEP_DAYS = 400     # 본 공고 기록 보관 기간
OPEN_REPORT = True       # 신규 공고가 있으면 리포트를 브라우저로 자동 열기
HIDE_EXPIRED = True        # 접수 마감일이 지난 공고는 리포트에서 제외
# 첨부 공고문에서 읽어낸 '추정' 마감일로도 숨길지 여부.
# 목록에 마감일이 아예 없는 게시판(KRIT·DAPA·ICMTC·IRIS)은 이걸 켜야 정리됩니다.
# 다만 추정을 잘못하면 살아 있는 공고가 사라지므로, 이상하면 False 로 끄세요.
HIDE_EXPIRED_GUESS = True

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# ── 관심도 채점 ───────────────────────────────────────────
# 연구실 분야: 수중통신 · 수중위치추정
#
# 3단계로 나눕니다. 이 분야는 전문 용어가 뚜렷해서, 일반어를 넣으면
# 신호가 아니라 잡음이 됩니다(예전에 '국방'이 16건, '通信'이 10건 걸렸습니다).
#
#   직결 — 이 단어가 나오면 사실상 확정
#   분야 — 맞는 영역이지만 그 자체로 확정은 아님
#   인접 — 같이 나올 뿐 기술이 아님 (잠수함은 플랫폼이지 수중통신이 아닙니다)
TOAST_MIN_SCORE = 3

DIRECT_POINT = 5
FIELD_POINT = 3
NEAR_POINT = 1
NEAR_MAX_POINTS = 2       # 인접어만으로는 임계값을 넘지 못하게 막습니다

DIRECT_KEYWORDS = [
    # 수중통신
    "수중음향", "수중 음향", "수중통신", "수중 통신", "음향통신", "음향 통신",
    "수중채널", "수중 채널", "다중경로", "전달손실", "전파손실", "음속구조",
    "채널추정", "채널 추정", "등화기",
    # 수중위치추정
    "수중측위", "수중 측위", "음향측위", "음향 측위", "수중항법", "수중 항법",
    "삼변측량", "USBL", "LBL", "SBL", "TDOA", "DVL",
    # 음향 센싱 하드웨어
    "소나", "소너", "음탐기", "음탐", "선배열", "예인배열", "예인음탐",
    "하이드로폰", "트랜스듀서", "소노부이", "TASS",
    # 영문
    "underwater acoustic", "acoustic communication", "hydrophone",
    "transducer", "sonar", "hydroacoustic",
    # 일본어
    "水中音響", "水中通信", "音響通信", "音響測位", "水中測位", "ソナー",
    "ハイドロホン", "曳航アレイ",
]

FIELD_KEYWORDS = [
    "수중", "음향", "음파", "천해", "해저", "실해역", "수중로봇", "해양관측",
    "무인잠수",          # 무인잠수정 — 소나를 싣는 수중 플랫폼이라 AUV/ROV와 같은 등급
    "AUV", "ROV", "UUV", "UWA", "IoUT",
    "underwater", "acoustic", "bathymetr",
    "水中", "音響", "音波", "浅海", "海底", "海中",
]

NEAR_KEYWORDS = [
    # 플랫폼·무기 — 함께 나오지만 기술 자체는 아닙니다
    "잠수함", "잠수정", "잠수", "어뢰", "무인수상정", "수상정",
    "USV", "심해", "해양로봇",
    # 일반 기술어
    "해양", "통신", "센서", "신호처리", "무인", "자율운항", "로봇",
    "탐지", "관측", "위치추정", "위치인식", "측위", "항법", "배열", "빔포밍",
    # 일본어
    "潜水", "魚雷", "深海", "海洋", "無人", "通信", "探知", "観測", "測位", "航法",
    # 영어
    "marine", "ocean", "maritime", "communication", "sensing",
    "navigation", "array", "beamforming", "localization",
]

# 첨부 본문 채점.
# 채용 공고 첨부에도 '잠수함'이 4번씩 나오므로 출현 횟수로는 갈리지 않습니다.
# 서로 다른 핵심어가 몇 종류나 나오는지가 확실한 판별자입니다.
#   신속시범사업 공모  → 수중·음향·음파·음탐  4종  (진짜)
#   화력사업부장 채용  → 잠수함 하나뿐        0종  (인접어는 본문에서 세지 않음)
BODY_DIRECT_POINT = 4
BODY_FIELD_POINT = 2
BODY_MIN_DISTINCT = 2       # 직결·분야가 이 종류 수 미만이면 첨부 점수 없음
BODY_MAX_POINTS = 10        # 한 문서가 순위를 독식하지 않도록
# 6만 자 문서에 분야어 두 개가 흩어져 있는 건 제목에 '수중'이 박힌 것보다
# 약한 증거입니다. 그래서 첨부 점수는 직결어를 요구합니다.
# 직결어가 없으면 분야어가 이 종류 수는 나와야 인정합니다.
BODY_MIN_FIELD_ONLY = 3

# 제목에 이 단어가 있으면 아예 제외 (채용·시설 등 잡음)
EXCLUDE_KEYWORDS = [
    # 채용·인사 공고 (첨부에 사업 분야 목록이 붙어 있어 키워드가 잘못 걸립니다)
    "공모직위", "개방형 직위", "대표이사", "소장 모집", "이사장 공모",
    "채용", "청소용역", "급식", "시설공사", "임대차", "인쇄물",
    "제세공과금", "기간제근로자", "청원경찰",
    "테스트", "(test)", "(TEST)",
    # 이미 끝난 공고의 결과 안내는 제안 대상이 아니므로 제외
    "審査結果", "選定結果", "落札結果",
    # 일본 사이트 소식성 항목 (공모가 아니라 결과·평가 안내)
    "採択課題", "事後評価", "中間評価", "採用状況", "終了しました", "심사결과", "선정결과", "결과 발표",
]

# ── 상세·첨부 확인 ───────────────────────────────────────
# 공고 제목은 사업명뿐인 경우가 많고 세부 과제 목록은 첨부 HWP 안에 있습니다.
# 아래 사이트는 상세를 열어 첨부 공고문 본문까지 읽어 채점합니다.
DETAIL_SITES = ["krit", "add", "icpc", "dapa", "iris",
                "jamstec", "atla"]   # 일본 — 공모 PDF를 직접 읽습니다
DETAIL_DELAY_MS = 900      # 상세 요청 사이 간격 (봇 차단을 유발하지 않도록)
DETAIL_RETRY = 3           # 첨부 읽기에 실패해도 이 횟수까지는 다시 시도
MAX_DETAIL_FETCH = 50       # 한 번 실행에서 열어볼 공고 수 (나머지는 다음 실행에서)


# ── grants.gov (미국 연방 연구비) ────────────────────────
# 한국 대학은 외국 기관이라, 미국 기관 한정 공고는 봐도 의미가 없습니다.
# 기본값은 '미국 한정이 명시된 것만 제외' 입니다.
# True 로 바꾸면 '외국 기관 허용이 명시된 것만' 남깁니다 — 다만 ONR·NRL 의
# 큰 BAA 는 자격이 첨부 문서 안에 있어 '불명'으로 나오므로 대부분 빠집니다.
GRANTS_STRICT = False
# 따옴표로 감싸면 구(phrase) 검색이 됩니다. 안 감싸면 단어 OR 로 걸려서
# 'underwater acoustic' 이 소아 재난의료 공고까지 끌고 옵니다(23건 → 2건).
GRANTS_KEYWORDS = [
    '"underwater acoustic"',
    '"ocean acoustics"',
    '"underwater communication"',
    '"undersea warfare"',
    "sonar",
    "hydrophone",
    "bathymetry",
]

# ── 감시 페이지 ──────────────────────────────────────────
# 연 1회 공모를 내는 곳은 새 글이 아니라 같은 주소의 내용이 바뀝니다.
# 본문을 저장해 두고 새로 생긴 줄이 있으면 공고 항목으로 만듭니다.
WATCH_PAGES = [
    {"id": "atla-koubo", "country": "JP",
     "name": "ATLA 안전보장기술연구추진제도 공모",
     "url": "https://www.mod.go.jp/atla/funding/koubo.html"},
    {"id": "atla-funding", "country": "JP",
     "name": "ATLA 펀딩 안내",
     "url": "https://www.mod.go.jp/atla/funding.html"},
    {"id": "jsps-kokusai", "country": "JP",
     "name": "JSPS 국제공동연구사업",
     "url": "https://www.jsps.go.jp/j-bottom/index.html"},
    {"id": "jsps-dfg", "country": "JP",
     "name": "JSPS 독일 JRP-LEAD with DFG 신청",
     "url": "https://www.jsps.go.jp/j-bottom/02_h_sinsei.html"},
    {"id": "jsps-snsf", "country": "JP",
     "name": "JSPS 스위스 JRPs with SNSF 신청",
     "url": "https://www.jsps.go.jp/j-bottom/02_g_sinsei.html"},
    {"id": "jsps-ukri", "country": "JP",
     "name": "JSPS 영국 JRP-LEAD with UKRI 신청",
     "url": "https://www.jsps.go.jp/j-bottom/02_i_sinsei.html"},
]

# ── 수집 대상 사이트 ──────────────────────────────────────
# rfp/sites/ 안의 모듈 id. 잠시 끄고 싶으면 앞에 # 을 붙이세요.
#
# 조달(입찰) 사이트는 넣지 않습니다 — 나라장터·KIOST 입찰정보·국방전자조달(d2b)은
# 물품·용역 발주라 연구 과제 공고가 아닙니다.
ENABLED_SITES = [
    # ── 국내: 국방·방위산업 ──
    "krit",      # 국방기술진흥연구소 — 국방 핵심기술/미래도전국방기술
    "add",       # 국방과학연구소 — 위탁연구 제안서 공모
    "icpc",      # 민군협력진흥원(ICMTC) — 민군겸용기술개발
    "dapa",      # 방위사업청 — 공지사항(정책·산학협력 공고)
    # ── 국내: 통합 포털 ──
    # KIMST·IITP·KEIT·NRF의 R&D 공고는 전부 IRIS로 통합 접수되므로
    # 기관별로 따로 긁지 않고 IRIS 한 곳에서 받습니다.
    "kriso",     # 선박해양플랜트연구소 — 무인잠수정·수중로봇, 위탁연구 제안공모
    "iris",      # 범부처통합연구지원시스템 — 접수중 사업공고 전체
    "ntis",      # 국가R&D통합정보서비스 — 부처 통합 공고
    # ── 일본 ──
    "erad",      # e-Rad — 일본 전 부처 공모일람
    "jst",       # 과학기술진흥기구 — CREST/SICORP/SATREPS
    "jsps",      # 일본학술진흥회 — 한일 국제공동연구
    "nedo",      # 신에너지·산업기술종합개발기구 — 실증 프로젝트
    "jamstec",   # 일본해양연구개발기구 — 심해·수중 기술제안공모
    "atla",      # 방위장비청 — 안전보장기술연구추진제도
    # ── 미국 ──
    "grants",    # grants.gov — ONR·NRL·NSWC 연구비 (수급 자격 판정 포함)
]
