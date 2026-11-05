"""회의록 업로드 파일을 읽고 보관합니다. (S05 파일 업로드 예제 응용)"""

import streamlit as st


def _clear_analysis() -> None:
    st.session_state.meeting_analysis = None
    st.session_state.meeting_summary = ""
    st.session_state.meeting_analysis_hash = None
    st.session_state.meeting_questions = []
    st.session_state.summary_audio = None
    st.session_state.summary_autoplay = False


def update_meeting_file(uploaded_file) -> str:
    if uploaded_file is None:
        st.session_state.meeting_content = ""
        st.session_state.meeting_file_id = None
        _clear_analysis()
        return ""

    file_id = getattr(uploaded_file, "file_id", None) or uploaded_file.name
    if file_id != st.session_state.meeting_file_id:
        try:
            content = uploaded_file.getvalue().decode("utf-8-sig")
        except UnicodeDecodeError:
            st.session_state.meeting_content = ""
            st.session_state.meeting_file_id = None
            raise
        st.session_state.meeting_content = content
        st.session_state.meeting_file_id = file_id
        _clear_analysis()
    return st.session_state.meeting_content
