from playwright.sync_api import sync_playwright
from datetime import datetime
from winotify import Notification

ID = "20265596"
PW = "kms.3030303"
URL = "https://safety.hoseo.edu/mmbr/check/daily/main.do?labNo=346"

def notify(message):
    toast = Notification(app_id="연구실 안전점검", title="연구실 안전점검", msg=message, duration="short")
    toast.show()

class LoginFailed(Exception):
    """로그인 실패. 재시도하지 않고 즉시 중단합니다."""


class AlreadyLoggedIn(LoginFailed):
    """다른 브라우저에 로그인이 남아 있어 접속이 거부된 경우."""


def login(page, alerts):
    """학내구성원 포털 계정으로 로그인합니다.

    비밀번호가 틀리면 사이트가 '5회 틀릴 경우 접속이 차단됩니다' 라고 알립니다.
    그래서 **한 번만 시도하고, 실패하면 바로 멈춥니다.**
    예전에는 실패해도 한 번 더 시도한 뒤 그냥 진행해서,
    로그인이 안 된 상태로 '이미 점검 완료' 라는 잘못된 알림이 떴습니다.
    """
    page.wait_for_selector("input[type='text']#userId", state="visible", timeout=10000)
    page.fill("input[type='text']#userId", ID)
    page.fill("input[type='password']#userName", PW)
    page.wait_for_timeout(500)
    alerts.clear()
    page.click("#btnUser")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)

    # 로그인 폼이 그대로면 실패입니다
    if page.locator("input[type='text']#userId").count() > 0:
        reason = " ".join((alerts[0] if alerts else "").split())
        # 이 사이트는 동시 접속을 막습니다. 크롬 등에 로그인이 남아 있으면
        # 비밀번호가 맞아도 거부되므로, 비밀번호 오류와 구분해서 알립니다.
        if "다른 환경" in reason or "중복" in reason:
            raise AlreadyLoggedIn(reason)
        raise LoginFailed(reason or "아이디 또는 비밀번호를 확인해 주세요")

def close_popups(page):
    try:
        page.wait_for_selector(".ui-dialog-titlebar-close", state="visible", timeout=5000)
        close_btns = page.locator(".ui-dialog-titlebar-close")
        for i in range(close_btns.count()):
            try:
                close_btns.nth(i).click()
                page.wait_for_timeout(500)
            except:
                pass
    except:
        pass


# 달력은 상태를 아이콘으로 표시합니다.
#   dailycon_check.png (적합) · dailycon_cross.png (점검안함) · dailycon_na.png (N/A)
# 예전에는 글자색을 재서 빨간 날을 찾으려 했는데, 실제로는 색이 아니라
# 아이콘이라 한 번도 걸리지 않았습니다.
#
# 미래 날짜도 '점검안함'으로 뜨지만 클릭할 <a> 가 없습니다.
# 그래서 '아이콘이 X + 클릭 가능' 인 날만 골라내면 지난 미점검일과 오늘만 남습니다.
FIND_MISSED_JS = r"""() => {
    const out = [];
    document.querySelectorAll('table td').forEach(td => {
        const img = td.querySelector('img[alt="점검안함"], img[src*="dailycon_cross"]');
        const a = td.querySelector('a');
        if (!img || !a) return;
        const day = (td.innerText || '').trim().match(/^\d{1,2}/);
        if (!day) return;
        // 이번 달이 아닌 칸은 건너뜁니다
        if (/other-month/.test(td.className)) return;
        out.push(parseInt(day[0], 10));
    });
    return [...new Set(out)].sort((x, y) => x - y);   // 오래된 날짜부터
}"""


def find_missed(page):
    """점검하지 않은 날짜를 오래된 순으로 돌려줍니다."""
    return page.evaluate(FIND_MISSED_JS)


def open_day(page, day):
    """달력에서 해당 날짜를 선택합니다."""
    ok = page.evaluate(r"""(day) => {
        for (const td of document.querySelectorAll('table td')) {
            const a = td.querySelector('a');
            const m = (td.innerText || '').trim().match(/^\d{1,2}/);
            if (a && m && parseInt(m[0], 10) === day && !/other-month/.test(td.className)) {
                a.click();
                return true;
            }
        }
        return false;
    }""", day)
    page.wait_for_timeout(1800)
    return ok


def logout(page):
    """세션을 반납합니다.

    이 사이트는 동시 접속을 막습니다. 로그아웃하지 않고 브라우저만 닫으면
    서버에 세션이 남아, 다음 실행이 '다른 환경에서 로그인 되어 있습니다' 로
    거부됩니다. 그래서 끝날 때 반드시 로그아웃합니다.
    """
    try:
        link = page.locator("a:has(img[alt='로그아웃']), a:has-text('로그아웃')")
        if link.count():
            link.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(800)
            print("로그아웃 완료")
    except Exception as exc:
        print(f"로그아웃 실패(무시): {exc.__class__.__name__}")


def do_inspection(page):
    page.wait_for_timeout(1500)
    for cat in [1, 2, 3]:
        radios = page.locator(f"input[name='Proper_{cat}']")
        radios.first.click()
        page.wait_for_timeout(500)

    page.wait_for_timeout(500)
    save_btn = page.locator("a:has-text('저장'), button:has-text('저장'), "
                            "a:has-text('점검완료'), input[value='저장']")
    if save_btn.count() == 0:
        # 자동 실행에서는 사람이 없으므로 input() 으로 멈추면 안 됩니다.
        raise RuntimeError("저장 버튼을 찾지 못했습니다")
    save_btn.first.click()
    page.wait_for_timeout(1800)

today = datetime.now()
date_str = f"{today.month}월 {today.day}일"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    alerts = []
    page.on("dialog", lambda d: (alerts.append(d.message), d.accept()))

    try:
        page.goto(URL)
        page.wait_for_load_state("networkidle")

        login(page, alerts)
        print("로그인 완료")

        close_popups(page)
        print("팝업 닫기 완료")

        page.goto(URL)
        page.wait_for_load_state("networkidle")
        print("일상점검 페이지 이동 완료")

        missed = find_missed(page)
        print(f"미점검 날짜: {missed or '없음'}")

        if not missed:
            print("점검할 날짜가 없습니다.")
            logout(page)
            browser.close()
            notify(f"{date_str} 기준 미점검 날짜가 없습니다.")
        else:
            # 지난 날짜부터 순서대로 처리합니다.
            # 저장하면 달력이 새로 그려지므로 매번 다시 읽습니다.
            done, failed = [], []
            for day in list(missed):
                try:
                    if not open_day(page, day):
                        failed.append((day, "날짜를 선택하지 못함"))
                        continue

                    btn = page.locator("a.btn:has-text('점검')")
                    if btn.count() == 0:
                        failed.append((day, "점검 버튼 없음"))
                        continue
                    btn.first.click()

                    do_inspection(page)
                    done.append(day)
                    print(f"  {day}일 완료")
                except Exception as exc:
                    failed.append((day, exc.__class__.__name__))
                    print(f"  {day}일 실패 — {exc}")

                # 다음 날짜를 위해 달력을 다시 불러옵니다
                page.goto(URL)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1200)

            remaining = find_missed(page)
            print(f"처리 완료 {done} / 실패 {failed} / 남은 미점검 {remaining}")
            logout(page)
            browser.close()

            msg = f"점검 완료: {', '.join(f'{d}일' for d in done)}" if done else "점검한 날짜가 없습니다."
            if failed:
                msg += f"\n실패 {len(failed)}건: " + ", ".join(f"{d}일" for d, _ in failed)
            if remaining:
                msg += f"\n아직 남음: " + ", ".join(f"{d}일" for d in remaining)
            notify(msg)

    except AlreadyLoggedIn as e:
        # 브라우저에 로그인이 남아 있는 상태입니다. 비밀번호 문제가 아닙니다.
        print(f"동시 접속 차단: {e}")
        browser.close()
        notify("점검하지 못했습니다 — 다른 브라우저에 로그인이 남아 있습니다.\n"
               "안전관리시스템에서 로그아웃한 뒤 다시 실행해 주세요.")

    except LoginFailed as e:
        # 비밀번호가 바뀌면 여기로 옵니다.
        # 5회 틀리면 계정이 차단되므로 절대 재시도하지 않습니다.
        print(f"로그인 실패: {e}")
        browser.close()
        notify(f"로그인 실패 — 점검하지 못했습니다.\n{e}\n"
               "스크립트의 비밀번호를 확인해 주세요.")

    except Exception as e:
        print(f"오류 발생: {e}")
        logout(page)
        browser.close()
        notify(f"점검 중 오류가 발생했습니다.\n{str(e)[:100]}")
