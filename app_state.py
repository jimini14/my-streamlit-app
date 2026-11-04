"""Streamlit 세션 상태를 관리합니다. (S04 상태 관리 예제 응용)"""

import streamlit as st
from datetime import datetime, timedelta, timezone


def korea_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def initialize_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "meeting_content" not in st.session_state:
        st.session_state.meeting_content = ""
    if "meeting_file_id" not in st.session_state:
        st.session_state.meeting_file_id = None
    if "audio_bytes" not in st.session_state:
        st.session_state.audio_bytes = None
    if "upload_version" not in st.session_state:
        st.session_state.upload_version = 0
    if "schedules" not in st.session_state:
        st.session_state.schedules = []
    if "todos" not in st.session_state:
        st.session_state.todos = []
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = korea_today()
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = korea_today().year
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = korea_today().month
    if "meeting_summary" not in st.session_state:
        st.session_state.meeting_summary = ""
    if "meeting_analysis" not in st.session_state:
        st.session_state.meeting_analysis = None
    if "meeting_analysis_hash" not in st.session_state:
        st.session_state.meeting_analysis_hash = None
    if "calendar_recommendations" not in st.session_state:
        st.session_state.calendar_recommendations = []
    if "meeting_questions" not in st.session_state:
        st.session_state.meeting_questions = []
    if "analyzed_files" not in st.session_state:
        st.session_state.analyzed_files = set()


def reset_state() -> None:
    st.session_state.messages.clear()
    st.session_state.meeting_content = ""
    st.session_state.meeting_file_id = None
    st.session_state.audio_bytes = None
    st.session_state.upload_version += 1
    st.session_state.schedules.clear()
    st.session_state.todos.clear()
    st.session_state.meeting_summary = ""
    st.session_state.meeting_analysis = None
    st.session_state.meeting_analysis_hash = None
    st.session_state.calendar_recommendations = []
    st.session_state.meeting_questions = []
    st.session_state.analyzed_files.clear()
    today = korea_today()
    st.session_state.selected_date = today
    st.session_state.calendar_year = today.year
    st.session_state.calendar_month = today.month


def save_response(user_prompt: str, answer: str, audio_bytes: bytes | None) -> None:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.audio_bytes = audio_bytes
