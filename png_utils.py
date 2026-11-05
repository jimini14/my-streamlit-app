"""달력·To-do PNG 생성 (한글 폰트 자동 확보)."""
import calendar
import io
import os
import urllib.request
import zlib
from datetime import date

from PIL import Image, ImageDraw, ImageFont

# 달력 이벤트 색상 (참고 디자인의 보라·청록·파랑·분홍·주황)
PALETTE = ["#6C5DD3", "#16A9BC", "#3D5AFE", "#F0457E", "#F7943B", "#22B07D"]

_FONT_CANDIDATES = {
    "regular": [
        "fonts/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",          # packages.txt: fonts-nanum
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ],
    "bold": [
        "fonts/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ],
}
_FONT_URLS = {
    "regular": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
    "bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
}
_font_path_cache = {}


def _font_path(weight: str):
    """한글을 지원하는 폰트 파일 경로를 찾고, 없으면 내려받아 /tmp에 보관합니다."""
    if weight in _font_path_cache:
        return _font_path_cache[weight]
    found = next((p for p in _FONT_CANDIDATES[weight] if os.path.exists(p)), None)
    if found is None:
        target = f"/tmp/able_nanum_{weight}.ttf"
        if not os.path.exists(target):
            try:
                urllib.request.urlretrieve(_FONT_URLS[weight], target)
            except Exception:
                target = None
        found = target
    if found is None and weight == "bold":
        found = _font_path("regular")
    _font_path_cache[weight] = found
    return found


def font(size: int, bold: bool = False):
    path = _font_path("bold" if bold else "regular")
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def has_korean_font() -> bool:
    return _font_path("regular") is not None


def event_color(item: dict) -> str:
    key = (item.get("id") or item.get("schedule", "")).encode("utf-8")
    return PALETTE[zlib.crc32(key) % len(PALETTE)]


def _fit(draw, text: str, fnt, max_w: int) -> str:
    """주어진 폭에 맞게 글자를 자르고 말줄임표를 붙입니다."""
    text = str(text)
    if draw.textlength(text, font=fnt) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=fnt) > max_w:
        text = text[:-1]
    return text + "…"


def _label(e: dict) -> str:
    return (e.get("time", "") + " " + e["schedule"]).strip()


def _to_png(img) -> bytes:
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def calendar_png(year: int, month: int, events: list, today: date | None = None) -> bytes:
    """참고 디자인 스타일(다크 카드 + 색상 pill + 우측 이벤트 카드)의 달력 이미지."""
    weeks = calendar.Calendar(0).monthdatescalendar(year, month)
    cell_w, cell_h, left, top = 150, 128, 40, 190
    side_x = left + cell_w * 7 + 36
    width, height = side_x + 320 + 40, top + cell_h * len(weeks) + 60
    img = Image.new("RGB", (width, height), "#16171D")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, width - 20, height - 20), radius=26, fill="#1F2029")

    d.text((left, 48), f"{calendar.month_name[month]} {year}", font=font(42), fill="#FFFFFF")
    d.text((left + 4, 104), f"{year}년 {month}월 · ABLE 일정 캘린더", font=font(18), fill="#9CA0B0")

    names = ["월", "화", "수", "목", "금", "토", "일"]
    for j, name in enumerate(names):
        color = "#7FA8FF" if j == 5 else "#FF7A9C" if j == 6 else "#9CA0B0"
        d.text((left + j * cell_w + 12, top - 38), name, font=font(18, True), fill=color)

    month_events = {}
    for e in events:
        month_events.setdefault(e["date"], []).append(e)

    for i, week in enumerate(weeks):
        for j, day in enumerate(week):
            x, y = left + j * cell_w, top + i * cell_h
            bg = "#252631" if j < 5 else "#21222B"
            d.rectangle((x, y, x + cell_w, y + cell_h), fill=bg, outline="#30323E")
            in_month = day.month == month
            num_color = "#E8EAF2" if in_month else "#555866"
            if today and day == today:
                d.ellipse((x + 6, y + 6, x + 38, y + 38), fill="#F0457E")
                num_color = "#FFFFFF"
            d.text((x + 22, y + 22), str(day.day), font=font(17, True), fill=num_color, anchor="mm")
            if not in_month:
                continue
            items = sorted(month_events.get(day.isoformat(), []), key=lambda e: e.get("time") or "99")
            shown = items if len(items) <= 3 else items[:2]
            for k, e in enumerate(shown):
                py = y + 46 + k * 26
                d.rounded_rectangle((x + 6, py, x + cell_w - 6, py + 22), radius=11, fill=event_color(e))
                d.text((x + 14, py + 11), _fit(d, _label(e), font(13), cell_w - 26),
                       font=font(13), fill="#FFFFFF", anchor="lm")
            if len(items) > 3:
                d.text((x + 12, y + 46 + 2 * 26 + 11), f"+{len(items) - 2}개 더", font=font(12), fill="#9CA0B0", anchor="lm")

    # 우측 이벤트 카드 목록
    prefix = f"{year}-{month:02d}-"
    upcoming = sorted([e for e in events if e["date"].startswith(prefix)],
                      key=lambda e: (e["date"], e.get("time") or "99"))
    d.text((side_x, top - 40), "이번 달 일정", font=font(20, True), fill="#FFFFFF")
    if not upcoming:
        d.text((side_x, top + 4), "등록된 일정이 없습니다.", font=font(15), fill="#9CA0B0")
    max_cards = max(1, (height - top - 60) // 92)
    for k, e in enumerate(upcoming[:max_cards]):
        cy = top + k * 92
        d.rounded_rectangle((side_x, cy, side_x + 320, cy + 80), radius=12, fill=event_color(e))
        day = date.fromisoformat(e["date"])
        d.text((side_x + 40, cy + 40), str(day.day), font=font(34, True), fill="#FFFFFF", anchor="mm")
        d.text((side_x + 80, cy + 14), _fit(d, e["schedule"], font(17, True), 225), font=font(17, True), fill="#FFFFFF")
        sub = f"{day.month}월 {day.day}일 ({names[day.weekday()]})" + (f" · {e['time']}" if e.get("time") else "")
        d.text((side_x + 80, cy + 46), sub, font=font(13), fill="#F3F4FA")
    if len(upcoming) > max_cards:
        d.text((side_x, top + max_cards * 92), f"외 {len(upcoming) - max_cards}건", font=font(14), fill="#9CA0B0")
    return _to_png(img)


def todo_png(todos: list, today: date | None = None) -> bytes:
    """체크박스가 그려진 To-do 이미지."""
    row_h, top = 54, 150
    width = 900
    height = max(300, top + max(1, len(todos)) * row_h + 80)
    img = Image.new("RGB", (width, height), "#FFF8F1")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, width - 20, height - 20), radius=24, fill="#FFFFFF", outline="#F3D9C4", width=2)
    d.rounded_rectangle((20, 20, width - 20, 118), radius=24, fill="#F07C2A")
    d.rectangle((20, 90, width - 20, 118), fill="#F07C2A")
    d.text((50, 46), "My To-do List", font=font(34, True), fill="#FFFFFF")
    done = sum(t["done"] for t in todos)
    info = (today.isoformat() + "  ·  " if today else "") + f"완료 {done} / 전체 {len(todos)}"
    d.text((width - 50, 66), info, font=font(17), fill="#FFF3E8", anchor="rm")
    if not todos:
        d.text((50, top + 10), "등록된 할 일이 없습니다.", font=font(20), fill="#94A3B8")
    for i, t in enumerate(todos):
        y = top + i * row_h
        box = (50, y, 80, y + 30)
        if t["done"]:
            d.rounded_rectangle(box, radius=7, fill="#16A9BC")
            d.line((56, y + 15, 63, y + 23, 75, y + 8), fill="#FFFFFF", width=4, joint="curve")
        else:
            d.rounded_rectangle(box, radius=7, outline="#CBD5E1", width=3)
        fnt = font(21)
        text = _fit(d, t["task"], fnt, width - 160)
        color = "#94A3B8" if t["done"] else "#1F2937"
        d.text((100, y + 15), text, font=fnt, fill=color, anchor="lm")
        if t["done"]:
            tw = d.textlength(text, font=fnt)
            d.line((100, y + 16, 100 + tw, y + 16), fill="#94A3B8", width=2)
        if i < len(todos) - 1:
            d.line((50, y + row_h - 12, width - 50, y + row_h - 12), fill="#F1F5F9", width=1)
    return _to_png(img)
