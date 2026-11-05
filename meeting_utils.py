"""회의록 업로드 파일을 읽고 보관합니다. (S05 파일 업로드 예제 응용)"""

import hashlib
import streamlit as st


def update_meeting_file(uploaded_file) -> str:
    if uploaded_file is None:
        st.session_state.meeting_content = ""
        st.session_state.meeting_file_id = None
        st.session_state.meeting_analysis = None
        st.session_state.meeting_summary = ""
        st.session_state.meeting_summary_audio = None
        st.session_state.meeting_summary_audio_error = ""
        st.session_state.meeting_summary_autoplay = False
        st.session_state.meeting_analysis_hash = None
        return ""

    file_bytes = uploaded_file.getvalue()
    file_id = hashlib.sha256(file_bytes).hexdigest()
    if file_id != st.session_state.meeting_file_id:
        try:
            content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            st.session_state.meeting_content = ""
            st.session_state.meeting_file_id = None
            raise
        st.session_state.meeting_content = content
        st.session_state.meeting_file_id = file_id
        st.session_state.meeting_analysis = None
        st.session_state.meeting_summary = ""
        st.session_state.meeting_summary_audio = None
        st.session_state.meeting_summary_audio_error = ""
        st.session_state.meeting_summary_autoplay = False
        st.session_state.meeting_analysis_hash = None
    return st.session_state.meeting_content
