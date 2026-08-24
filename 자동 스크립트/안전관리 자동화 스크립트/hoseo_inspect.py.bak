from playwright.sync_api import sync_playwright
from datetime import datetime
from winotify import Notification

ID = "20265596"
PW = "kms3030303"
URL = "https://safety.hoseo.edu/mmbr/check/daily/main.do?labNo=346"

def notify(message):
    toast = Notification(app_id="연구실 안전점검", title="연구실 안전점검", msg=message, duration="short")
    toast.show()

def login(page):
    page.wait_for_selector("input[type='text']#userId", state="visible", timeout=10000)
    page.fill("input[type='text']#userId", ID)
    page.fill("input[type='password']#userName", PW)
    page.wait_for_timeout(1000)
    page.click("#btnUser")
    page.wait_for_load_state("networkidle")

    if page.locator("input[type='text']#userId").count() > 0:
        print("로그인 재시도...")
        page.wait_for_timeout(1500)
        page.fill("input[type='text']#userId", ID)
        page.fill("input[type='password']#userName", PW)
        page.click("#btnUser")
        page.wait_for_load_state("networkidle")

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

def do_inspection(page):
    page.wait_for_timeout(1500)
    for cat in [1, 2, 3]:
        radios = page.locator(f"input[name='Proper_{cat}']")
        radios.first.click()
        page.wait_for_timeout(500)

    page.wait_for_timeout(500)
    save_btn = page.locator("a:has-text('저장'), button:has-text('저장'), a:has-text('완료'), a:has-text('점검완료'), input[value='저장']")
    if save_btn.count() > 0:
        save_btn.first.click()
    else:
        print("  ⚠ 저장 버튼을 찾지 못했습니다. 브라우저를 확인해 주세요.")
        input("  수동으로 저장 후 Enter: ")

    page.wait_for_timeout(1000)

today = datetime.now()
date_str = f"{today.month}월 {today.day}일"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.on("dialog", lambda dialog: dialog.accept())

    try:
        page.goto(URL)
        page.wait_for_load_state("networkidle")

        login(page)
        print("로그인 완료")

        close_popups(page)
        print("팝업 닫기 완료")

        page.goto(URL)
        page.wait_for_load_state("networkidle")
        print("일상점검 페이지 이동 완료")

        # 점검 버튼 존재 여부 확인 (이미 완료됐으면 버튼 없음)
        inspect_btn = page.locator("a.btn.dark.outer:has-text('점검')")
        if inspect_btn.count() == 0:
            print("이미 오늘 점검이 완료되어 있습니다.")
            browser.close()
            notify(f"{date_str} 연구실 안전점검이 이미 완료되어 있습니다!")
        else:
            red_dates = page.evaluate("""() => {
                const dates = [];
                document.querySelectorAll('#ui-datepicker-div td:not(.ui-datepicker-other-month)').forEach(td => {
                    const a = td.querySelector('a');
                    if (!a) return;
                    const tdStyle = window.getComputedStyle(td);
                    const aStyle = window.getComputedStyle(a);
                    const inlineColor = a.style.color || td.style.backgroundColor || '';
                    const colors = [tdStyle.backgroundColor, tdStyle.color, aStyle.color, aStyle.backgroundColor, inlineColor];
                    const isRed = colors.some(c =>
                        c.includes('255, 0, 0') || c.includes('220, 0') || c.includes('200, 0') ||
                        c === 'red' || c === '#ff0000'
                    );
                    const hasRedClass = td.className.toLowerCase().includes('red') ||
                                        td.className.includes('miss') ||
                                        td.className.includes('no');
                    if (isRed || hasRedClass) {
                        dates.push(a.innerText.trim());
                    }
                });
                return dates;
            }""")

            print(f"감지된 미점검 날짜: {red_dates}")

            if not red_dates:
                print("오늘 날짜 점검 시작...")
                inspect_btn.click()
                do_inspection(page)
            else:
                for date_text in red_dates:
                    print(f"{date_text}일 점검 시작...")
                    page.click(f"#ui-datepicker-div td:not(.ui-datepicker-other-month) a:has-text('{date_text}')")
                    page.wait_for_timeout(1000)
                    page.click("a.btn.dark.outer:has-text('점검')")
                    do_inspection(page)
                    print(f"  {date_text}일 완료")

            print("점검 완료!")
            browser.close()
            notify(f"{date_str} 연구실 안전점검이 완료되었습니다!")

    except Exception as e:
        print(f"오류 발생: {e}")
        browser.close()
        notify(f"점검 중 오류가 발생했습니다.\n{str(e)[:100]}")
