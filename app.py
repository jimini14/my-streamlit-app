"""호준님 비서 로직 + 개선된 일정/To-do 화면의 통합 진입점."""
import hashlib
import os

import streamlit as st
from openai import OpenAI

from app_state import initialize_state, reset_state, save_response
from assistant import ASSISTANT_BUILD, DEFAULT_SYS_ROLE
from calendar_ui_v2 import render_calendar, render_details, render_todos
from command_service import MissingInputError, run_command
from meeting_planner import analyze_meeting
from meeting_utils import update_meeting_file

st.set_page_config(page_title="AI 개인비서 에이블",page_icon="🤖",layout="wide")
initialize_state()

# 호준님 파일의 사이드바·멀티턴 처리 방식을 유지합니다.
with st.sidebar:
    st.header("🤖 에이블")
    st.caption(f"메일 처리 버전: {ASSISTANT_BUILD}")
    st.subheader("📥 회의록과 명령")
    uploaded_file=st.file_uploader("회의록 텍스트 파일 (.txt)",type=["txt"],key=f"meeting_file_{st.session_state.upload_version}")
    try:
        meeting_content=update_meeting_file(uploaded_file)
    except UnicodeDecodeError:
        meeting_content=""
        st.error("UTF-8 형식의 TXT 파일을 업로드해 주세요.")

    if uploaded_file is None:
        st.info("회의록을 올리면 요약과 일정·To-do 추천을 분석합니다.")
    elif meeting_content:
        st.caption(f"업로드: {uploaded_file.name}")
        with st.expander("회의록 본문 보기"):
            st.text_area("미팅 본문",meeting_content,height=180,disabled=True)
        file_key=hashlib.sha256(meeting_content.encode('utf-8')).hexdigest()
        if st.session_state.get('meeting_analysis_hash') != file_key:
            with st.spinner('회의록 분석 중...'):
                try:
                    analysis=analyze_meeting(OpenAI(),meeting_content)
                    st.session_state.meeting_analysis=analysis
                    st.session_state.meeting_summary=analysis.get('summary','')
                    st.session_state.meeting_questions=analysis.get('questions',[])
                    st.session_state.meeting_analysis_hash=file_key
                    st.success('분석 완료! 가운데 추천 목록을 확인해 주세요.')
                except Exception as exc:
                    st.error(f'회의록 분석 오류: {exc}')

    st.divider()
    recipient_email=st.text_input("수신자 이메일 주소",value=os.getenv('RECIPIENT_EMAIL',''))
    with st.expander('에이블 페르소나 (프롬프트)'):
        sys_role=st.text_area('시스템 역할',value=DEFAULT_SYS_ROLE,height=220)
    if st.button('대화 및 일정 초기화',use_container_width=True):
        reset_state()
        st.session_state.meeting_analysis_hash=None
        st.rerun()
    with st.form('command_form'):
        text_query=st.text_input('텍스트 질문/명령')
        audio_query=st.audio_input('음성으로 질문하기')
        submitted=st.form_submit_button('실행하기',use_container_width=True)

if submitted:
    if not text_query.strip() and audio_query is None:
        st.warning('텍스트 입력 또는 음성 녹음이 필요합니다.')
    else:
        with st.spinner('에이블이 처리 중입니다...'):
            try:
                result=run_command(OpenAI(),text_query,audio_query,meeting_content,sys_role,st.session_state.messages,recipient_email)
            except MissingInputError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f'명령 실행 오류: {exc}')
            else:
                save_response(result.user_prompt,result.answer,result.audio_bytes)
                if result.email_status:
                    if result.email_status.startswith('이메일 발송 완료'):
                        st.success(result.email_status)
                    else:
                        st.error(result.email_status)
                if result.audio_error:
                    st.warning(f'음성 응답 생성 오류: {result.audio_error}')

st.title('🗓️ ABLE 일정 및 업무 관리')
st.caption('회의록을 업로드하면 오른쪽에 요약, 가운데에 마감 일정 후보와 추천 To-do가 표시됩니다.')

# 왼쪽 사이드바 / 가운데 넓은 영역 / 오른쪽 좁은 영역
main,right=st.columns([3.6,1.15],gap='large')
with main:
    render_calendar()
    st.divider()
    render_details()
with right:
    st.subheader('📋 회의 요약')
    if st.session_state.meeting_summary:
        st.write(st.session_state.meeting_summary)
    else:
        st.info('회의록을 업로드하면 요약이 바로 나타납니다.')
    st.divider()
    render_todos()

st.divider()
st.subheader('💬 에이블의 답변')
if st.session_state.audio_bytes:
    st.audio(st.session_state.audio_bytes,format='audio/mp3')
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.write(message['content'])
else:
    st.info('사이드바에서 텍스트 또는 음성 명령을 실행하면 답변이 표시됩니다.')

st.caption('일정·To-do는 현재 접속 세션에만 유지되며 서버 재시작 후 사라질 수 있습니다.')
