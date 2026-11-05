"""Streamlit 세션 상태를 관리합니다. (S04 상태 관리 예제 응용)"""

import streamlit as st
from datetime import datetime, timedelta, timezone


def korea_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


DEFAULTS = {
    "messages": list,
    "meeting_content": lambda: "",
    "meeting_file_id": lambda: None,
    "audio_bytes": lambda: None,
    "upload_version": lambda: 0,
    "schedules": list,
    "todos": list,
    "meeting_summary": lambda: "",
    "meeting_analysis": lambda: None,
    "meeting_analysis_hash": lambda: None,
    "calendar_recommendations": list,
    "meeting_questions": list,
    "analyzed_files": set,
    # 회의 요약 음성(TTS) 자동 재생
    "summary_audio": lambda: None,
    "summary_autoplay": lambda: False,
    # 상세 일정 / To-do 음성 입력(STT)
    "voice_versions": dict,     # 녹음 위젯 초기화용 키 버전
    "processed_voice": set,     # 이미 처리한 녹음(중복 등록 방지)
    "voice_notice": dict,       # 음성 처리 결과 메시지
}


def initialize_state() -> None:
    for key, factory in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = factory()
    today = korea_today()
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = today
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = today.year
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = today.month


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
    st.session_state.summary_audio = None
    st.session_state.summary_autoplay = False
    st.session_state.processed_voice.clear()
    st.session_state.voice_notice.clear()
    today = korea_today()
    st.session_state.selected_date = today
    st.session_state.calendar_year = today.year
    st.session_state.calendar_month = today.month


def save_response(user_prompt: str, answer: str, audio_bytes: bytes | None) -> None:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.audio_bytes = audio_bytes
