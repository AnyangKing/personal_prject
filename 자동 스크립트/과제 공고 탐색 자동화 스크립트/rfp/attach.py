# -*- coding: utf-8 -*-
"""첨부 공고문에서 본문 텍스트를 뽑아냅니다.

공고 제목은 대개 사업명뿐이고, 실제 세부 과제 목록(RFP)은 첨부 HWP 안에 있습니다.
제목만 채점하면 '미래도전국방기술 산학연 주관 제안서 공모' 같은 공고가
1점짜리로 묻히므로, 첨부를 열어 본문까지 채점 대상에 넣습니다.

지원 형식: .hwp(한글 바이너리) · .hwpx(압축 XML) · .pdf · .txt
"""

import io
import re
import zipfile
import zlib

MAX_BYTES = 12 * 1024 * 1024      # 이보다 큰 첨부는 건너뜁니다
MAX_CHARS = 60000                 # 추출 결과 상한 (채점에는 이 정도면 충분합니다)

WANTED_EXT = (".hwp", ".hwpx", ".pdf", ".txt", ".docx")

# 공고문 본문일 가능성이 높은 파일명 (양식·서식은 뒤로 미룹니다)
PREFER = re.compile(r"공고|공모|안내|계획|RFP|제안요청|과제목록|명세", re.I)
AVOID = re.compile(r"양식|서식|신청서|동의서|서약|様式|FAQ|매뉴얼|증빙", re.I)


def is_supported(name):
    return name.lower().endswith(WANTED_EXT)


def rank(name):
    """어떤 첨부부터 열어볼지 우선순위. 낮을수록 먼저."""
    score = 0
    if AVOID.search(name):
        score += 10
    if PREFER.search(name):
        score -= 5
    if name.lower().endswith((".hwp", ".hwpx")):
        score -= 1        # 공고문은 대개 한글 파일입니다
    return score


# ── HWP 5.0 (OLE 복합문서) ────────────────────────────────
def _hwp_text(data):
    import olefile

    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        if not ole.exists("FileHeader"):
            return ""
        header = ole.openstream("FileHeader").read()
        # 헤더 36바이트째 플래그의 0번 비트가 압축 여부입니다
        compressed = bool(header[36] & 1) if len(header) > 36 else True

        sections = sorted(
            ("/".join(p) for p in ole.listdir() if p[0] == "BodyText"),
            key=lambda s: int(re.sub(r"\D", "", s.split("Section")[-1]) or 0),
        )
        chunks = []
        for name in sections:
            raw = ole.openstream(name).read()
            if compressed:
                try:
                    raw = zlib.decompress(raw, -15)
                except zlib.error:
                    continue
            chunks.append(_hwp_records(raw))
        return "\n".join(c for c in chunks if c)
    finally:
        ole.close()


def _hwp_records(buf):
    """섹션 스트림의 레코드를 훑어 문단 텍스트(태그 67)만 모읍니다."""
    out, pos, size = [], 0, len(buf)
    while pos + 4 <= size:
        header = int.from_bytes(buf[pos:pos + 4], "little")
        tag = header & 0x3FF
        length = (header >> 20) & 0xFFF
        pos += 4
        if length == 0xFFF:                      # 확장 길이
            if pos + 4 > size:
                break
            length = int.from_bytes(buf[pos:pos + 4], "little")
            pos += 4
        chunk = buf[pos:pos + length]
        pos += length
        if tag != 67:                            # HWPTAG_PARA_TEXT
            continue
        out.append(_hwp_chars(chunk))
    return "\n".join(t for t in out if t.strip())


def _hwp_chars(chunk):
    """UTF-16LE 문단에서 제어문자(확장 8바이트)를 건너뛰며 글자만 뽑습니다."""
    text, i = [], 0
    while i + 2 <= len(chunk):
        code = int.from_bytes(chunk[i:i + 2], "little")
        i += 2
        if code in (10, 13):
            text.append("\n")
        elif code < 32:
            # 1,2,3,11,12,14~23 은 뒤에 12바이트가 더 붙는 확장 제어문자입니다
            if code in (1, 2, 3, 11, 12) or 14 <= code <= 23:
                i += 14
        else:
            text.append(chr(code))
    return "".join(text)


# ── HWPX (ZIP + XML) ─────────────────────────────────────
def _hwpx_text(data):
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if re.search(r"Contents/section\d+\.xml$", n)]
        for name in sorted(names):
            xml = z.read(name).decode("utf-8", "ignore")
            out.extend(re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", xml, re.S))
    text = "\n".join(out)
    return re.sub(r"<[^>]+>", "", text)


# ── DOCX (ZIP + XML) ─────────────────────────────────────
def _docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n")
    parts = re.findall(r"<w:t[^>]*>(.*?)</w:t>|(\n)", xml, re.S)
    return "".join(a or b for a, b in parts)


# ── PDF ──────────────────────────────────────────────────
def _pdf_text(data):
    import pdfplumber

    out = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:40]:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def extract(name, data):
    """(추출된 텍스트, 실패 사유). 성공하면 사유는 빈 문자열입니다."""
    if not data:
        return "", "내용 없음"
    if len(data) > MAX_BYTES:
        return "", f"파일이 너무 큼({len(data) // 1024 // 1024}MB)"

    low = name.lower()
    try:
        if low.endswith(".hwpx"):
            text = _hwpx_text(data)
        elif low.endswith(".hwp"):
            # 확장자가 .hwp 라도 실제로는 HWPX(ZIP)인 경우가 있습니다
            text = _hwpx_text(data) if data[:2] == b"PK" else _hwp_text(data)
        elif low.endswith(".pdf"):
            text = _pdf_text(data)
        elif low.endswith(".docx"):
            text = _docx_text(data)
        elif low.endswith(".txt"):
            text = data.decode("utf-8", "ignore")
        else:
            return "", "지원하지 않는 형식"
    except Exception as exc:
        return "", f"{exc.__class__.__name__}: {exc}"[:120]

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 30:
        return "", "본문을 읽지 못함(이미지 문서일 수 있음)"
    return text[:MAX_CHARS], ""
