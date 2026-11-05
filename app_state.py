"""Streamlit 세션 상태를 관리합니다. (S04 상태 관리 예제 응용)"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from openai import OpenAI


def korea_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


@st.cache_resource
def get_client() -> OpenAI:
    """OpenAI 클라이언트를 한 번만 만들어 재사용합니다."""
    return OpenAI()


DEFAULTS = {
    "messages": list,
    "meeting_content": lambda: "",
    "meeting_file_id": lambda: None,
    "audio_bytes": lambda: None,
    "upload_version": lambda: 0,
    "schedules": list,
    "todos": list,
    "selected_date": korea_today,
    "calendar_year": lambda: korea_today().year,
    "calendar_month": lambda: korea_today().month,
    "meeting_summary": lambda: "",
    "meeting_analysis": lambda: None,
    "meeting_analysis_hash": lambda: None,
    "calendar_recommendations": list,
    "meeting_questions": list,
    "analyzed_files": set,
    # [고도화] 회의 요약 음성 자동 재생
    "summary_audio": lambda: None,
    "summary_autoplay": lambda: False,
    # [고도화] 음성 입력 위젯 초기화·중복 처리 방지
    "voice_version": lambda: 0,
    "processed_voice": set,
    # 음성 처리 후 화면 상단에 한 번 보여줄 알림
    "flash": lambda: None,
}


def initialize_state() -> None:
    for key, factory in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = factory()


def reset_state() -> None:
    upload_version = st.session_state.upload_version + 1
    voice_version = st.session_state.voice_version + 1
    for key, factory in DEFAULTS.items():
        st.session_state[key] = factory()
    st.session_state.upload_version = upload_version
    st.session_state.voice_version = voice_version


def save_response(user_prompt: str, answer: str, audio_bytes: bytes | None) -> None:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.audio_bytes = audio_bytes
