"""공통 스타일과 캐릭터 영역.

글자 겹침 방지 원칙
- 화면 전체 글꼴을 바꾸지 않습니다. (아이콘 글꼴이 덮어써지면 'keyboard_double…' 같은 글자가 보임)
- 사이드바·접기 메뉴(expander)처럼 아이콘 글꼴에 의존하는 요소를 쓰지 않습니다.
- 캐릭터·달력은 inline style HTML로 그려 CSS 적용 여부와 관계없이 같은 모양이 나옵니다.
"""
import base64
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
CHARACTER_IMG = BASE_DIR / "able_character.png"
AVATAR_IMG = BASE_DIR / "able_avatar.png"

CSS = """
<style>
/* 아이콘 글꼴을 한 번 더 불러와 아이콘이 글자로 보이지 않게 합니다. */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
.block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
/* 우측 상단 Deploy·메뉴, 제목 옆 링크 아이콘 숨김 */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stHeaderActionElements"] { display: none !important; }
/* 파일 업로더의 아이콘(업로드 구름, add)은 숨기고 글자 버튼만 사용 */
[data-testid="stFileUploader"] [data-testid="stIconMaterial"] { display: none !important; }
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def avatar():
    """답변 말풍선 아바타: 캐릭터 이미지 (없으면 이모지)."""
    return str(AVATAR_IMG) if AVATAR_IMG.exists() else "🤖"


def render_hero(today_count: int, month_count: int, open_todos: int) -> None:
    """상단 캐릭터 인사 영역. 이미지 배경색과 같은 톤으로 이어지게 그립니다."""
    src = _data_uri(CHARACTER_IMG)
    img = (f'<img src="{src}" alt="에이블" style="width:260px;max-width:34%;height:auto;flex:0 0 auto;'
           f'-webkit-mask-image:radial-gradient(ellipse 85% 85% at 50% 50%,#000 70%,transparent 100%);'
           f'mask-image:radial-gradient(ellipse 85% 85% at 50% 50%,#000 70%,transparent 100%);">') if src else ""

    def chip(num, label, color):
        return (f'<div style="background:#fff;border-radius:14px;padding:8px 16px;min-width:96px;'
                f'box-shadow:0 2px 8px rgba(31,41,55,.07);">'
                f'<div style="font-size:1.4rem;font-weight:800;line-height:1.25;color:{color};">{num}</div>'
                f'<div style="font-size:.8rem;line-height:1.3;color:#6B7280;">{label}</div></div>')

    st.markdown(
        '<div style="display:flex;align-items:center;gap:18px;padding:8px 24px 8px 8px;border-radius:22px;'
        'background:linear-gradient(90deg,#E0DBE0 0%,#E0DBE0 22%,#EEEBF1 45%,#FFF4EA 100%);border:1px solid #ECE4DD;">'
        f'{img}'
        '<div style="min-width:0;">'
        '<div style="font-size:1.5rem;font-weight:800;line-height:1.35;color:#1F2937;word-break:keep-all;">'
        '안녕하세요, 김 대리님! 저는 <span style="color:#F07C2A;">에이블</span>이에요</div>'
        '<div style="font-size:.95rem;line-height:1.5;color:#4B5563;margin:4px 0 12px;word-break:keep-all;">'
        '회의록을 올려 주시면 요약을 읽어 드리고, 일정은 캘린더에, 할 일은 To-do에 정리해 드릴게요.</div>'
        '<div style="display:flex;gap:10px;flex-wrap:wrap;">'
        + chip(today_count, "오늘 일정", "#F0457E") + chip(month_count, "이번 달 일정", "#16A9BC")
        + chip(open_todos, "남은 할 일", "#F07C2A") +
        '</div></div></div>',
        unsafe_allow_html=True,
    )
