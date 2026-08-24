# -*- coding: utf-8 -*-
"""공고 상세 페이지와 첨부 공고문을 읽어 채점 대상 본문을 넓힙니다.

제목만 채점하면 '미래도전국방기술 산학연 주관 제안서 공모' 처럼
사업명만 적힌 공고가 낮은 점수로 묻힙니다. 실제 세부 과제 목록은
첨부 HWP 안에 있으므로, 상세를 열어 본문과 첨부를 함께 읽습니다.

한 번 읽은 공고는 data/rfp_detail.json 에 남겨 다시 받지 않습니다.
한 번에 처리할 수 있는 양이 정해져 있어(config.MAX_DETAIL_FETCH)
남은 것은 다음 실행에서 이어서 처리합니다.
"""

import json
import pathlib
import re
from datetime import datetime

from . import attach, config, deadline

CACHE_FILE = config.DATA_DIR / "rfp_detail.json"

MAX_ATTACH = 2          # 공고 하나당 열어볼 첨부 개수
DOWNLOAD_TIMEOUT = 25000


def load():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(cache):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    tmp.replace(CACHE_FILE)


def key_of(item):
    return f"{item['site']}:{item['id']}"


def pending(items, cache):
    """아직 상세를 안 읽은 공고를 골라냅니다(마감일이 가까운 순)."""
    def needs(i):
        if i["site"] not in config.DETAIL_SITES:
            return False
        rec = cache.get(key_of(i))
        if rec is None:
            return True
        # 실패한 건 일시적 오류일 수 있으니 정해진 횟수까지 다시 시도합니다
        return not rec.get("ok") and rec.get("tries", 1) < config.DETAIL_RETRY

    todo = [i for i in items if needs(i)]
    todo.sort(key=lambda i: (i.get("deadline") or "9999", i.get("posted") or ""))
    return todo


def _attachments(page):
    """첨부 링크를 공고문일 가능성이 높은 순서로 돌려줍니다."""
    raw = page.evaluate(
        r"""() => [...document.querySelectorAll('a')].map((a, i) => ({
              i: i, t: (a.innerText || a.getAttribute('title') || '')
                        .replace(/\s+/g, ' ').trim()}))
            .filter(x => /\.(hwp|hwpx|pdf|txt)\b/i.test(x.t))"""
    )
    out = []
    for a in raw:
        name = a["t"].split(" (")[0].strip()
        if attach.is_supported(name):
            out.append({"idx": a["i"], "name": name, "label": a["t"]})
    out.sort(key=lambda a: attach.rank(a["name"]))
    return out[:MAX_ATTACH]


DOC_URL = re.compile(r"\.(pdf|hwpx?|docx?|txt)(\?|$)", re.I)

# 봇 차단 페이지 문구 (한/영/일)
BOT_WALL = re.compile(
    r"보안 확인|Ray ID|Just a moment|Checking your browser"
    r"|Cloudflare|セキュリティ確認|アクセスが拒否"
)


def fetch_one(page, item, module, goto):
    """(본문 텍스트, 실패 사유 목록)."""
    notes = []

    # 항목 자체가 문서 링크인 경우(JAMSTEC의 공모 PDF 등).
    # 브라우저로 이동하면 다운로드가 시작돼 goto 가 실패하므로 직접 받습니다.
    if DOC_URL.search(item.get("url", "")):
        try:
            resp = page.context.request.get(item["url"], timeout=DOWNLOAD_TIMEOUT)
            name = item["url"].split("?")[0].rsplit("/", 1)[-1]
            text, err = attach.extract(name, resp.body())
            return (text, []) if text else ("", [f"{name[:40]} — {err}"])
        except Exception as exc:
            return "", [f"문서 내려받기 실패: {exc.__class__.__name__}"]

    # 사이트가 자체 방식으로 상세를 열 수 있으면 그쪽을 씁니다(KRIT 등 POST 전용)
    opener = getattr(module, "open_detail", None)
    try:
        if opener:
            opener(page, item, goto)
        else:
            goto(page, item["url"])
        page.wait_for_timeout(1200)
    except Exception as exc:
        return "", [f"상세 열기 실패: {exc.__class__.__name__}"]

    try:
        body = page.inner_text("body")
    except Exception:
        body = ""

    # 사이트가 봇 차단 화면을 띄운 경우. 우회하지 않고 그대로 실패로 남깁니다.
    if BOT_WALL.search(body) and len(body) < 1200:
        return "", ["사이트가 봇 차단 화면을 표시했습니다 — 잠시 후 다시 시도합니다"]

    texts = [body]
    try:
        files = _attachments(page)
    except Exception:
        files = []

    for f in files:
        try:
            link = page.locator("a").nth(f["idx"])
            with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl:
                link.click()
            got = dl.value
            data = pathlib.Path(got.path()).read_bytes()
            text, err = attach.extract(got.suggested_filename or f["name"], data)
            if text:
                texts.append(text)
            elif err:
                notes.append(f"{f['name'][:40]} — {err}")
            got.delete()
        except Exception as exc:
            notes.append(f"{f['name'][:40]} — {exc.__class__.__name__}")

    return "\n".join(t for t in texts if t), notes


def run(page, items, cache, goto, log, load_site):
    """상세 읽기를 수행하고 item['extra'] 에 본문을 채웁니다."""
    todo = pending(items, cache)
    if not todo:
        return 0, 0

    budget = config.MAX_DETAIL_FETCH
    done = failed = 0
    log(f"=== 상세·첨부 확인 {min(len(todo), budget)}건 (대기 {len(todo)}건)")

    by_url = {}          # 같은 상세 페이지를 여러 항목이 가리키면 한 번만 받습니다
    for n, item in enumerate(todo[:budget]):
        try:
            module = load_site(item["site"])
        except Exception:
            continue
        if n:
            page.wait_for_timeout(config.DETAIL_DELAY_MS)   # 사이트에 부담을 주지 않도록

        # 여러 항목이 같은 상세 페이지를 가리키면(ATLA 앵커 등) 한 번만 받습니다
        resolve = getattr(module, "detail_url", None)
        url_key = (item["site"], resolve(item) if resolve else item.get("url", ""))
        if url_key in by_url:
            text, notes = by_url[url_key]
        else:
            text, notes = fetch_one(page, item, module, goto)
            by_url[url_key] = (text, notes)
        ok = len(text) > 200
        # 본문 전체는 너무 크므로, 채점에 쓰이는 핵심어만 남깁니다.
        # 이게 없으면 다음 실행 때 제목 점수로 되돌아갑니다.
        low = text.lower()
        vocab = (config.DIRECT_KEYWORDS + config.FIELD_KEYWORDS + config.NEAR_KEYWORDS)
        core = [kw for kw in vocab if kw.lower() in low]

        # 목록에 마감일 컬럼이 없는 게시판(KRIT·DAPA·ICMTC)을 위해
        # 공고문 본문에서 접수 마감일을 추정합니다.
        guess_dl, evidence = ("", "")
        event_dt, event_why = ("", "")
        if ok and not item.get("deadline"):
            guess_dl, evidence = deadline.guess(text, item.get("posted", ""))
            # 설명회처럼 '개최'인 공고는 접수기간 대신 행사일이 기준입니다
            if deadline.EVENT_TITLE.search(item.get("title", "")):
                event_dt, event_why = deadline.event(text, item.get("posted", ""))

        rec = cache.get(key_of(item)) or {}
        # 봇 차단은 일시적인 상태입니다. 재시도 한도를 깎으면 영구 포기가 되므로
        # 시도 횟수를 올리지 않고 다음 실행에서 다시 열어 봅니다.
        transient = any("봇 차단" in n for n in notes)
        tries = rec.get("tries", 0) if transient else rec.get("tries", 0) + 1
        cache[key_of(item)] = {
            "at": datetime.now().strftime("%Y-%m-%d"),
            "chars": len(text),
            "hits": core[:30],
            "notes": notes[:3],
            "ok": ok,
            "tries": tries,
            "deadline_guess": guess_dl,
            "deadline_why": evidence,
            "event_date": event_dt,
            "event_why": event_why,
        }
        if ok:
            item["extra"] = text
            if guess_dl:
                item["deadline_guess"] = guess_dl
                item["deadline_why"] = evidence
            if event_dt:
                item["event_date"] = event_dt
                item["event_why"] = event_why
            done += 1
        else:
            item["detail_failed"] = True
            item["detail_note"] = "; ".join(notes)[:160] or "본문을 읽지 못했습니다"
            failed += 1

    return done, failed


def apply_cache(items, cache):
    """이전 실행에서 읽어 둔 결과를 다시 적용합니다.

    본문 전체는 보관하지 않으므로, 그때 찾은 핵심어만 되살려
    채점이 제목 점수로 되돌아가지 않게 합니다.
    """
    for item in items:
        rec = cache.get(key_of(item))
        if not rec:
            continue
        if rec.get("ok"):
            if rec.get("deadline_guess") and not item.get("deadline"):
                item["deadline_guess"] = rec["deadline_guess"]
                item["deadline_why"] = rec.get("deadline_why", "")
            if rec.get("event_date"):
                item["event_date"] = rec["event_date"]
                item["event_why"] = rec.get("event_why", "")
            if rec.get("hits") and not item.get("extra"):
                # 공백으로 이으면 '수중'+'음향'이 붙어 '수중 음향'(직결어)으로
                # 잘못 매칭됩니다. 구분자를 넣어 문구가 만들어지지 않게 합니다.
                item["extra"] = " | ".join(rec["hits"])
        else:
            item["detail_failed"] = True
            item.setdefault("detail_note",
                            "; ".join(rec.get("notes", []))[:160] or "본문을 읽지 못했습니다")
