"""AI 개인비서 '에이블' — 기능 고도화 최종본 (사이드바 없는 3단 대시보드)."""
import hashlib
import html
import os

import streamlit as st

from app_state import get_client, initialize_state, korea_today, reset_state, save_response
from assistant import ASSISTANT_BUILD, DEFAULT_SYS_ROLE
from audio_utils import text_to_speech
from calendar_ui_v2 import render_calendar, render_details
from command_service import MissingInputError, run_command
from meeting_planner import analyze_meeting, save_analysis
from meeting_utils import update_meeting_file
from todo_ui import render_todos
from ui_style import AVATAR_IMG, apply_style, avatar, render_hero

st.set_page_config(page_title="AI 개인비서 에이블", page_icon=str(AVATAR_IMG) if AVATAR_IMG.exists() else "🤖",
                   layout="wide")
initialize_state()
apply_style()

hero_slot = st.empty()          # 숫자가 최신이 되도록 맨 마지막에 채움
flash_slot = st.empty()
left, center, right = st.columns([1.05, 2.75, 1.2], gap="medium")


# ======================= 왼쪽: 회의록 · 명령 패널 =======================
def analyze_uploaded(meeting_content: str):
    file_key = hashlib.sha256(meeting_content.encode("utf-8")).hexdigest()
    if st.session_state.meeting_analysis_hash == file_key:
        return
    with st.spinner("회의록 분석 중..."):
        try:
            client = get_client()
            analysis = analyze_meeting(client, meeting_content)
        except Exception as exc:
            st.error(f"회의록 분석 오류: {exc}")
            return
        st.session_state.meeting_analysis = analysis
        st.session_state.meeting_analysis_hash = file_key
        st.session_state.meeting_summary = analysis.get("summary", "")
        st.session_state.meeting_questions = analysis.get("questions", [])
        added, _ = save_analysis(analysis, file_key)      # 날짜 있는 일정 → 캘린더 자동 등록
        try:                                               # 요약 음성 미리 생성 → 오른쪽에서 자동 재생
            st.session_state.summary_audio = text_to_speech(client, "회의 요약입니다. " + st.session_state.meeting_summary)
            st.session_state.summary_autoplay = True
        except Exception as exc:
            st.session_state.summary_audio = None
            st.warning(f"요약 음성 생성 오류: {exc}")
        st.session_state.flash = f"회의록 분석 완료! 일정 {added}건을 캘린더에 등록했어요."


with left:
    with st.container(border=True):
        st.markdown("**📥 회의록 업로드**")
        uploaded_file = st.file_uploader("회의록 텍스트 파일 (.txt)", type=["txt"],
                                         key=f"meeting_file_{st.session_state.upload_version}",
                                         label_visibility="collapsed")
        try:
            meeting_content = update_meeting_file(uploaded_file)
        except UnicodeDecodeError:
            meeting_content = ""
            st.error("UTF-8 형식의 TXT 파일을 올려 주세요.")
        if meeting_content:
            analyze_uploaded(meeting_content)
            if st.toggle("회의록 본문 보기", key="show_meeting_text"):
                st.text_area("회의록 본문", meeting_content, height=180, disabled=True,
                             label_visibility="collapsed")
        else:
            st.caption("TXT 회의록을 올리면 요약·일정·추천 할 일을 정리해요.")

    with st.container(border=True):
        st.markdown("**🎙️ 에이블에게 말하기**")
        with st.form("command_form", clear_on_submit=True, border=False):
            text_query = st.text_input("텍스트 명령", placeholder="예: 회의 요약을 메일로 보내 줘")
            audio_query = st.audio_input("음성 명령")
            submitted = st.form_submit_button("실행하기", type="primary", width="stretch")
        recipient_email = st.text_input("수신자 이메일", value=os.getenv("RECIPIENT_EMAIL", ""),
                                        placeholder="name@example.com")

    if "sys_role_value" not in st.session_state:
        st.session_state.sys_role_value = DEFAULT_SYS_ROLE
    if st.toggle("에이블 페르소나 수정", key="show_persona"):
        if "sys_role_input" not in st.session_state:
            st.session_state.sys_role_input = st.session_state.sys_role_value
        st.text_area("시스템 역할", key="sys_role_input", height=220, label_visibility="collapsed")
        st.session_state.sys_role_value = st.session_state.sys_role_input
    if st.button("대화 및 일정 초기화", width="stretch"):
        reset_state()
        st.rerun()

    if submitted:
        if not (text_query or "").strip() and audio_query is None:
            st.warning("텍스트를 입력하거나 음성을 녹음해 주세요.")
        else:
            with st.spinner("에이블이 처리 중입니다..."):
                try:
                    result = run_command(get_client(), text_query, audio_query, meeting_content,
                                         st.session_state.sys_role_value, st.session_state.messages,
                                         recipient_email)
                except MissingInputError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"명령 실행 오류: {exc}")
                else:
                    save_response(result.user_prompt, result.answer, result.audio_bytes)
                    if result.email_status:
                        (st.success if result.email_status.startswith("이메일 발송 완료") else st.error)(result.email_status)
                    if result.audio_error:
                        st.warning(f"음성 응답 생성 오류: {result.audio_error}")


# ======================= 가운데: 캘린더 · 상세 일정 =======================
with center:
    render_calendar()
    st.write("")
    render_details()


# ======================= 오른쪽: 회의 요약 · To-do =======================
with right:
    with st.container(border=True):
        st.subheader("📋 회의 요약")
        if st.session_state.meeting_summary:
            if st.session_state.summary_audio:
                # 분석 직후 한 번 자동 재생, 이후에는 ▶로 다시 듣기
                st.audio(st.session_state.summary_audio, format="audio/mp3",
                         autoplay=st.session_state.summary_autoplay)
                st.session_state.summary_autoplay = False
            st.write(st.session_state.meeting_summary)
            if st.session_state.meeting_questions:
                st.markdown("**확인 필요한 사항**")
                st.markdown("".join(f'<div style="line-height:1.6;">• {html.escape(q)}</div>'
                                    for q in st.session_state.meeting_questions), unsafe_allow_html=True)
        else:
            st.caption("회의록을 올리면 요약이 나타나고 바로 음성으로 읽어 드려요.")
    with st.container(border=True):
        render_todos()


# ======================= 하단: 에이블의 답변 (최신이 위) =======================
st.divider()
st.subheader("💬 에이블의 답변")
msgs = st.session_state.messages
if msgs:
    turns = [msgs[i:i + 2] for i in range(0, len(msgs), 2)]
    for n, turn in enumerate(reversed(turns)):
        if n == 0 and st.session_state.audio_bytes:
            st.audio(st.session_state.audio_bytes, format="audio/mp3")
        for m in turn:
            with st.chat_message(m["role"], avatar=avatar() if m["role"] == "assistant" else "🧑‍💼"):
                st.write(m["content"])
        if n < len(turns) - 1:
            st.markdown('<hr style="margin:4px 0 12px;border:none;border-top:1px solid #EEF0F4;">',
                        unsafe_allow_html=True)
else:
    st.caption("왼쪽에서 텍스트 또는 음성으로 명령하면 답변이 여기에 최신순으로 표시됩니다.")

st.caption(f"버전 {ASSISTANT_BUILD} · 일정·To-do는 현재 접속 세션에만 유지됩니다.")

# ======================= 마지막: 상단 영역 채우기 =======================
today, sch = korea_today(), st.session_state.schedules
prefix = f"{st.session_state.calendar_year}-{st.session_state.calendar_month:02d}-"
with hero_slot.container():
    render_hero(today_count=sum(e["date"] == today.isoformat() for e in sch),
                month_count=sum(e["date"].startswith(prefix) for e in sch),
                open_todos=sum(not t["done"] for t in st.session_state.todos))
if st.session_state.flash:
    flash_slot.success(st.session_state.flash)
    st.session_state.flash = None
