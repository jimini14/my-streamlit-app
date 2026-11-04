"""AI 개인비서 에이블의 Streamlit 화면."""

import hashlib
import os

import streamlit as st
from openai import OpenAI

from app_state import initialize_state, reset_state, save_response
from assistant import ASSISTANT_BUILD, DEFAULT_SYS_ROLE
from calendar_ui import render_calendar, render_todos
from command_service import MissingInputError, run_command
from meeting_planner import analyze_meeting, save_analysis
from meeting_utils import update_meeting_file


st.set_page_config(page_title="AI 개인비서 에이블", page_icon="🤖", layout="wide")
initialize_state()

with st.sidebar:
    st.header("🤖 에이블")
    st.caption(f"메일 처리 버전: {ASSISTANT_BUILD}")
    st.subheader("📥 회의록과 명령")
    uploaded_file = st.file_uploader(
        "회의록 텍스트 파일 (.txt)", type=["txt"],
        key=f"meeting_file_{st.session_state.upload_version}",
    )
    try:
        meeting_content = update_meeting_file(uploaded_file)
    except UnicodeDecodeError:
        meeting_content = ""
        st.error("UTF-8 형식의 텍스트 파일을 업로드해 주세요.")

    if uploaded_file is None:
        st.info("회의록을 업로드하면 일정과 할 일을 자동으로 분석합니다.")
    elif meeting_content:
        st.caption(f"업로드: {uploaded_file.name}")
        with st.expander("회의록 본문 보기"):
            st.text_area("미팅 본문", meeting_content, height=180, disabled=True)

        file_key = hashlib.sha256(meeting_content.encode("utf-8")).hexdigest()
        if file_key not in st.session_state.analyzed_files:
            with st.spinner("회의록에서 일정과 할 일을 분석 중입니다..."):
                try:
                    analysis = analyze_meeting(OpenAI(), meeting_content)
                    schedule_count, todo_count = save_analysis(analysis, file_key)
                except Exception as exc:
                    st.error(f"회의록 분석 오류: {exc}")
                else:
                    st.success(f"캘린더 {schedule_count}건, To-do {todo_count}건 등록")

    st.divider()
    recipient_email = st.text_input("수신자 이메일 주소", value=os.getenv("GMAIL_ADDRESS", ""))
    with st.expander("에이블 페르소나 (프롬프트)"):
        sys_role = st.text_area("시스템 역할", value=DEFAULT_SYS_ROLE, height=220)
    if st.button("대화 및 일정 초기화", use_container_width=True):
        reset_state()
        st.rerun()

    with st.form("command_form"):
        text_query = st.text_input("텍스트 질문/명령")
        audio_query = st.audio_input("음성으로 질문하기")
        submitted = st.form_submit_button("실행하기", use_container_width=True)

if submitted:
    if not text_query.strip() and audio_query is None:
        st.warning("텍스트 입력 또는 음성 녹음이 필요합니다.")
    else:
        with st.spinner("에이블이 처리 중입니다..."):
            try:
                result = run_command(
                    OpenAI(), text_query, audio_query, meeting_content,
                    sys_role, st.session_state.messages, recipient_email,
                )
            except MissingInputError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"오류가 발생했습니다: {exc}")
            else:
                save_response(result.user_prompt, result.answer, result.audio_bytes)
                if result.email_status:
                    if result.email_status.startswith("이메일 발송 완료"):
                        st.success(result.email_status)
                    else:
                        st.error(result.email_status)
                if result.audio_error:
                    st.warning(f"음성 응답 생성 오류: {result.audio_error}")

st.title("📅 ABLE 일정 및 업무 관리")
st.caption("회의록을 업로드하면 날짜가 있는 업무는 캘린더에, 기한 없는 업무는 To-do List에 표시됩니다.")
calendar_column, summary_column = st.columns([2.4, 1], gap="large")

with calendar_column:
    render_calendar()

with summary_column:
    st.subheader("📋 회의 요약")
    if st.session_state.meeting_summary:
        st.write(st.session_state.meeting_summary)
    else:
        st.info("회의록을 업로드하면 요약이 여기에 표시됩니다.")
    if st.session_state.meeting_questions:
        with st.expander("확인 필요한 항목"):
            for question in st.session_state.meeting_questions:
                st.write(f"• {question}")

    st.divider()
    render_todos()

    st.divider()
    st.subheader("💬 에이블의 답변")
    if st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format="audio/mp3")
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    else:
        st.info("명령을 실행하면 답변이 여기에 표시됩니다.")
