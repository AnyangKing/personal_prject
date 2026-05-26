from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("scratch/previews")
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
BG = "#0B1730"
INK = "#F8FBFF"
MUTED = "#AFC3DE"
CYAN = "#38BDF8"
GREEN = "#86EFAC"
AMBER = "#FBBF24"
RED = "#FB7185"
PANEL = "#0F2746"

FONT_DIR = Path("C:/Windows/Fonts")

def font(size, bold=False):
    candidates = ["malgunbd.ttf" if bold else "malgun.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    for name in candidates:
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

slides = [
    ("日本語\n마스터 AI", "기초 문자 학습부터 실전 회화까지 이어지는 AI 일본어 학습 웹앱", "AI 활용 경진대회", None),
    ("왜 만들었나", "기존 일본어 앱은 기초와 실전 사이의 연결이 약했습니다.", "문제 정의", None),
    ("시스템 구조", "HTML 단일 파일 + Cloud Functions + Vertex AI", "구조", None),
    ("기능 1 · 문자표와 발음 재생", "히라가나·가타카나·탁음·요음을 한 화면에서 탐색", "주요 기능", "스크린샷: 히라가나·가타카나 표"),
    ("기능 2 · 퀴즈 시스템", "객관식, 타이핑, AI 맞춤 복습", "주요 기능", "스크린샷: 퀴즈 화면"),
    ("기능 3 · AI 표현 생성기", "상황에 맞춰 바로 쓸 수 있는 일본어 표현 생성", "AI 기능", "스크린샷: AI 표현 생성기"),
    ("기능 4 · AI 대화 시뮬레이터", "역할 상황에서 AI와 짧게 주고받는 실전 연습", "AI 기능", "스크린샷: AI 대화 시뮬레이터"),
    ("학습 커리큘럼과 통계", "36단원 진행률과 XP/레벨 시스템", "학습 설계", "스크린샷: 커리큘럼·통계 화면"),
    ("개발 과정에서 해결한 문제", "Vertex AI 전환 · 응답 안정화 · 퀴즈 범위 확장", "개발 과정", None),
    ("마무리", "일본어를 외우는 앱에서, 일본어를 써보게 만드는 앱으로.", "END", None),
]

for idx, (title, sub, badge, shot) in enumerate(slides, 1):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    color = RED if badge == "END" else AMBER if "AI" in badge else GREEN if badge in ("구조", "개발 과정") else CYAN
    d.rounded_rectangle((W-420, 72, W-92, 126), radius=28, outline=color, width=3, fill="#102849")
    d.text((W-386, 86), badge, fill=color, font=font(24, True))
    y = 190 if idx != 1 else 245
    for line in title.split("\n"):
        d.text((94, y), line, fill=CYAN if line == "마스터 AI" else INK, font=font(118 if idx == 1 else 64, True))
        y += 128 if idx == 1 else 78
    d.text((96, y+12), sub, fill=MUTED, font=font(32))
    d.rounded_rectangle((96, y+92, 266, y+99), radius=5, fill=color)
    if shot:
        d.rounded_rectangle((96, 500, W-96, 930), radius=30, outline=CYAN, width=4, fill=PANEL)
        bbox = d.textbbox((0, 0), shot, font=font(44, True))
        d.text(((W-(bbox[2]-bbox[0]))/2, 685), shot, fill=MUTED, font=font(44, True))
    elif idx == 9:
        labels = ["Vertex AI 전환", "JSON 응답 안정화", "학습 범위 확장"]
        x = 96
        for label in labels:
            d.rounded_rectangle((x, 560, x+530, 850), radius=28, outline=CYAN, width=3, fill="#102849")
            d.text((x+42, 610), label, fill=INK, font=font(36, True))
            x += 590
    d.text((96, H-70), "2026-1학기 AI 활용 경진대회", fill="#7D94B4", font=font(18))
    d.text((W-130, H-70), f"{idx:02d}", fill="#7D94B4", font=font(18, True))
    img.save(OUT / f"slide-{idx:02d}.png")

print(OUT.resolve())
