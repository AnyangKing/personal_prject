# -*- coding: utf-8 -*-
"""공고 모니터 — 국내외 R&D 과제·사업 공고를 매일 모아 신규만 리포트로 뽑습니다.

사용법:
    python rfp_watch.py                 평소 실행 (신규만)
    python rfp_watch.py --site iris     특정 사이트만 시험 실행
    python rfp_watch.py --all           신규가 아니어도 전부 리포트에 담기
    python rfp_watch.py --show          브라우저 창을 띄워서 동작 확인
"""

import argparse
import io
import sys
import traceback
import webbrowser
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from rfp import config, detail, health, notify, report, score, store, watchpage
from rfp.fetch import browser_page, goto
from rfp.sites import load as load_site

# pythonw.exe(콘솔 없는 실행)로 돌리면 표준출력이 아예 없습니다.
# 작업 스케줄러에서 검은 창이 뜨지 않게 pythonw 로 돌리므로 여기서 막아 둡니다.
if sys.stdout is None:
    import os
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = sys.stdout
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def collect_site(page, site_id):
    """한 사이트를 수집합니다. 실패하면 설정된 횟수만큼 재시도."""
    module = load_site(site_id)
    meta = module.SITE
    last_err = None

    for attempt in range(1, config.SITE_RETRY + 1):
        try:
            items = module.collect(page, goto)
            for item in items:
                item["site"] = meta["id"]
                item["site_name"] = meta["name"]
                item["country"] = meta["country"]
                item["category"] = meta["category"]
                item.setdefault("org", "")
                item.setdefault("extra", "")
            return items, module, None
        except Exception as exc:
            last_err = f"{exc.__class__.__name__}: {exc}"
            log(f"    ! {meta['name']} 시도 {attempt} 실패 — {last_err[:120]}")
            page.wait_for_timeout(1500)

    return [], module, last_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", action="append", help="이 사이트만 수집 (여러 번 지정 가능)")
    ap.add_argument("--all", action="store_true", help="신규가 아닌 것도 리포트에 포함")
    ap.add_argument("--show", action="store_true", help="브라우저 창 표시")
    ap.add_argument("--no-open", action="store_true", help="리포트를 자동으로 열지 않음")
    ap.add_argument("--no-detail", action="store_true", help="상세·첨부를 읽지 않음(빠른 실행)")
    ap.add_argument("--no-watch", action="store_true", help="감시 페이지를 확인하지 않음")
    args = ap.parse_args()

    if args.show:
        config.HEADLESS = False

    targets = args.site or config.ENABLED_SITES
    log(f"=== 공고 수집 시작 — 대상 {len(targets)}개 사이트")

    all_items, errors, warnings = [], [], []
    seen = store.load()
    hist = health.load()
    dcache = detail.load()
    snaps = watchpage.load()

    with browser_page() as page:
        for site_id in targets:
            try:
                items, module, err = collect_site(page, site_id)
            except Exception as exc:
                errors.append((site_id, f"모듈 오류: {exc}"))
                log(f"  × {site_id} 모듈을 불러오지 못했습니다 — {exc}")
                continue

            if err:
                errors.append((module.SITE["name"], err))
                log(f"  × {module.SITE['name']} 수집 실패")
                continue

            # 상단 고정 공지가 목록에 두 번 나오는 게시판이 있어 같은 글번호는 하나로 합칩니다
            uniq, seen_ids = [], set()
            for item in items:
                if item["id"] in seen_ids:
                    continue
                seen_ids.add(item["id"])
                uniq.append(item)
            items = uniq

            # 마감 필터를 거치기 전의 '파싱된 행 수'로 건강 상태를 판정합니다.
            # (NTIS처럼 100건 받아 대부분 마감으로 걸러지는 건 정상이므로)
            raw_count = len(items)
            warn = health.check(hist, module.SITE["id"], module.SITE["name"], raw_count)
            if warn:
                warnings.append(warn)
                log(f"  ⚠ {warn[0]} — {warn[1]}")
            health.record(hist, module.SITE["id"], raw_count)

            log(f"  · {module.SITE['name']} {raw_count}건")
            all_items.extend(items)

            # 신규 공고만 상세를 열어 마감일 등을 보강
            if hasattr(module, "enrich"):
                fresh, _ = store.split_new(items, seen)
                for item in fresh[:15]:
                    try:
                        module.enrich(page, item, goto)
                    except Exception as exc:
                        log(f"    ~ 상세 조회 실패({item['title'][:20]}): {str(exc)[:60]}")

        # 내용이 바뀌는 감시 페이지 (연 1회 공모 사이트)
        if not args.no_watch and not args.site:
            try:
                changed = watchpage.check(page, goto, snaps, log)
                if changed:
                    log(f"=== 감시 페이지 변경 {len(changed)}건")
                all_items.extend(changed)
            except Exception as exc:
                log(f"=== 감시 확인 중단: {exc.__class__.__name__}: {str(exc)[:80]}")

        # 마감 지난 공고를 먼저 걸러낸 뒤, 남은 것의 첨부 공고문을 읽습니다.
        # (제목이 사업명뿐인 공모형 공고는 제목만으로는 판단이 안 됩니다)
        if config.HIDE_EXPIRED:
            today = datetime.now().strftime("%Y-%m-%d")
            before = len(all_items)
            all_items = [i for i in all_items
                         if not (i.get("deadline") and i["deadline"] < today)]
            if before != len(all_items):
                log(f"=== 마감 지난 공고 {before - len(all_items)}건 제외")

        if not args.no_detail:
            detail.apply_cache(all_items, dcache)
            try:
                done, failed = detail.run(page, all_items, dcache, goto, log, load_site)
                if done or failed:
                    log(f"=== 첨부 본문 확보 {done}건 / 읽기 실패 {failed}건")
            except Exception as exc:
                log(f"=== 상세 확인 중단: {exc.__class__.__name__}: {str(exc)[:80]}")

        # 추정 마감일은 첨부를 읽은 뒤에야 정해집니다.
        # 다만 추정은 틀릴 수 있으므로 **버리지 않고 표시만** 합니다.
        # 리포트 맨 아래 접이식 구역으로 내려가고, 토스트에는 세지 않습니다.
        # (목록에서 받은 '확정' 마감일로 거른 것은 위에서 이미 제외했습니다)
        if config.HIDE_EXPIRED and config.HIDE_EXPIRED_GUESS:
            today = datetime.now().strftime("%Y-%m-%d")
            n = 0
            for i in all_items:
                if i.get("deadline"):
                    continue
                past = ((i.get("deadline_guess") and i["deadline_guess"] < today)
                        or (i.get("event_date") and i["event_date"] < today))
                if past:
                    i["expired_guess"] = True
                    n += 1
            if n:
                log(f"=== 마감된 것으로 보이는 공고 {n}건 (추정 — 리포트 하단으로)")

    scored = score.apply(all_items)
    fresh, known = store.split_new(scored, seen)
    log(f"=== 수집 {len(scored)}건 / 신규 {len(fresh)}건 / 기존 {len(known)}건")

    shown = scored if args.all else fresh
    stats = {"sites_ok": len(targets) - len(errors), "sites_total": len(targets),
             "total": len(scored), "fresh": len(fresh)}
    path = report.build(shown, stats, errors, warnings)
    log(f"=== 리포트: {path}")

    store.save(seen, fresh)
    health.save(hist)
    detail.save(dcache)
    watchpage.save(snaps)

    live = [i for i in fresh if not i.get("expired_guess")]
    hot = [i for i in live if i["score"] >= config.TOAST_MIN_SCORE]
    if live:
        head = f"신규 공고 {len(live)}건 (관심 {len(hot)}건)"
        body = "\n".join(f"· {i['title'][:34]}" for i in (hot or fresh)[:3]) or "리포트를 확인하세요."
        if errors:
            body += f"\n(수집 실패 {len(errors)}개 사이트)"
        if warnings:
            body += f"\n(수집 이상 {len(warnings)}곳 — 점검 필요)"
        notify.notify("공고 모니터", f"{head}\n{body}", link=path)
        if config.OPEN_REPORT and not args.no_open:
            webbrowser.open(path.as_uri())
    else:
        msg = "오늘 새로 올라온 공고가 없습니다."
        if errors:
            msg += f"\n(수집 실패 {len(errors)}개 사이트 — 리포트 확인)"
        if warnings:
            msg += f"\n(수집 이상 {len(warnings)}곳 — 점검 필요)"
        notify.notify("공고 모니터", msg, link=path)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        detail = traceback.format_exc()
        log("치명적 오류:\n" + detail)
        try:
            notify.notify("공고 모니터 — 오류", detail.strip().splitlines()[-1][:160])
        except Exception:
            pass
        sys.exit(1)
