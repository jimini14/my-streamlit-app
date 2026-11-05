"""호준님 비서 로직 + 개선된 일정/To-do 화면의 통합 진입점."""
import hashlib
import os

import streamlit as st
from openai import OpenAI

from app_state import initialize_state, reset_state, save_response
from assistant import ASSISTANT_BUILD, DEFAULT_SYS_ROLE
from audio_utils import text_to_speech
from calendar_ui_v2 import render_calendar, render_details, render_todos
from command_service import MissingInputError, run_command
from meeting_planner import analyze_meeting, save_analysis
from meeting_utils import update_meeting_file

st.set_page_config(page_title="AI 개인비서 에이블",page_icon="🤖",layout="wide")
initialize_state()


@st.cache_resource
def get_client():
    return OpenAI()


# 호준님 파일의 사이드바·멀티턴 처리 방식을 유지합니다.
with st.sidebar:
    if os.path.exists("able_character.png"):
        st.image("able_character.png")  # 에이블 캐릭터
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
        st.info("회의록을 올리면 일정이 캘린더에 바로 등록되고 요약을 음성으로 들려 드립니다.")
    elif meeting_content:
        st.caption(f"업로드: {uploaded_file.name}")
        with st.expander("회의록 본문 보기"):
            st.text_area("미팅 본문",meeting_content,height=180,disabled=True)
        file_key=hashlib.sha256(meeting_content.encode('utf-8')).hexdigest()
        if st.session_state.get('meeting_analysis_hash') != file_key:
            with st.spinner('회의록 분석 및 캘린더 등록 중...'):
                try:
                    analysis=analyze_meeting(get_client(),meeting_content)
                except Exception as exc:
                    st.error(f'회의록 분석 오류: {exc}')
                else:
                    st.session_state.meeting_analysis=analysis
                    st.session_state.meeting_analysis_hash=file_key
                    # 회의록의 일정을 캘린더에 바로 등록 (회의/마감기한 색 구분)
                    added=save_analysis(analysis,file_key)
                    # 회의 요약을 음성으로 만들어 오른쪽 상단에서 자동 재생
                    summary=st.session_state.meeting_summary
                    if summary:
                        try:
                            st.session_state.summary_audio=text_to_speech(get_client(),'회의 요약입니다. '+summary)
                            st.session_state.summary_autoplay=True
                        except Exception as exc:
                            st.session_state.summary_audio=None
                            st.warning(f'요약 음성 생성 오류: {exc}')
                    st.success(f'분석 완료! 일정 {added}건을 캘린더에 등록했습니다.')

    st.divider()
    recipient_email=st.text_input("수신자 이메일 주소",value=os.getenv('RECIPIENT_EMAIL',''))
    with st.expander('에이블 페르소나 (프롬프트)'):
        sys_role=st.text_area('시스템 역할',value=DEFAULT_SYS_ROLE,height=220)
    if st.button('대화 및 일정 초기화',use_container_width=True):
        reset_state()
        st.session_state.meeting_analysis_hash=None
        st.rerun()
    # 텍스트 명령: 입력 후 '실행하기'
    with st.form('command_form',clear_on_submit=True):
        text_query=st.text_input('텍스트 질문/명령')
        submitted=st.form_submit_button('실행하기',use_container_width=True)

    # 음성 명령: 폼 밖에 두어 녹음을 멈추면 바로 실행됩니다.
    # (폼 안에 있으면 '실행하기'를 눌러야만 전송되고, 이전 녹음이 남아 다시 쓰이는 문제가 있었습니다.)
    voice_version=st.session_state.voice_versions.get('voice_command',0)
    voice_query=st.audio_input('🎙️ 음성으로 질문하기 (녹음을 멈추면 바로 실행)',key=f'voice_command_{voice_version}')
    st.caption('마이크 아이콘을 눌러 말하고, 다시 눌러 녹음을 멈추세요. 브라우저의 마이크 권한을 허용해야 합니다.')

    # 직전 실행 결과(인식된 문장, 오류 등) 표시
    for level,text in st.session_state.voice_notice.pop('command',[]):
        getattr(st,level)(text)

voice_bytes=None
if voice_query is not None:
    data=voice_query.getvalue()
    digest=hashlib.sha256(data).hexdigest()
    if digest not in st.session_state.processed_voice:   # 같은 녹음을 두 번 처리하지 않습니다.
        st.session_state.processed_voice.add(digest)
        st.session_state.voice_versions['voice_command']=voice_version+1   # 다음 화면에서 녹음기를 비웁니다.
        voice_bytes=data

if voice_bytes is not None or submitted:
    notices=[]
    if voice_bytes is None and not text_query.strip():
        notices.append(('warning','텍스트 입력 또는 음성 녹음이 필요합니다.'))
    else:
        with st.spinner('에이블이 처리 중입니다...'):
            try:
                result=run_command(get_client(),text_query,voice_bytes,meeting_content,sys_role,st.session_state.messages,recipient_email)
            except MissingInputError as exc:
                notices.append(('warning',str(exc)))
            except Exception as exc:
                notices.append(('error',f'명령 실행 오류: {exc}'))
            else:
                save_response(result.user_prompt,result.answer,result.audio_bytes)
                if voice_bytes is not None:
                    notices.append(('success',f'🎙️ 인식된 질문: {result.user_prompt}'))
                if result.email_status:
                    notices.append(('success' if result.email_status.startswith('이메일 발송 완료') else 'error',result.email_status))
                if result.audio_error:
                    notices.append(('warning',f'음성 응답 생성 오류: {result.audio_error}'))
    st.session_state.voice_notice['command']=notices
    st.rerun()

st.title('🗓️ ABLE 일정 및 업무 관리')
st.caption('회의록을 업로드하면 일정이 캘린더에 바로 등록되고(회의=파랑, 마감기한=빨강), 오른쪽 위에서 회의 요약이 음성으로 재생됩니다.')

# 왼쪽 사이드바 / 가운데 넓은 영역 / 오른쪽 좁은 영역
main,right=st.columns([3.6,1.15],gap='large')
with right:
    st.subheader('📋 회의 요약')
    if st.session_state.summary_audio:
        # 업로드 직후 한 번만 자동 재생합니다. (이후에는 재생 버튼으로 다시 듣기)
        st.audio(st.session_state.summary_audio,format='audio/mp3',autoplay=st.session_state.summary_autoplay)
        st.session_state.summary_autoplay=False
    if st.session_state.meeting_summary:
        st.write(st.session_state.meeting_summary)
    else:
        st.info('회의록을 업로드하면 요약이 바로 나타나고 음성으로 재생됩니다.')
    if st.session_state.meeting_questions:
        with st.expander('확인 필요한 사항'):
            for question in st.session_state.meeting_questions:
                st.write('• '+question)
    st.divider()
    render_todos(get_client)
with main:
    render_calendar()
    st.divider()
    render_details(get_client)

st.divider()
st.subheader('💬 에이블의 답변')
messages=st.session_state.messages
if messages:
    # 최신 답변이 위로 오도록 (질문, 답변) 묶음을 역순으로 표시합니다.
    pairs=[messages[i:i+2] for i in range(0,len(messages),2)]
    for index,pair in enumerate(reversed(pairs)):
        if index==0 and st.session_state.audio_bytes:
            st.audio(st.session_state.audio_bytes,format='audio/mp3')
        for message in pair:
            with st.chat_message(message['role']):
                st.write(message['content'])
        if index==0 and len(pairs)>1:
            st.caption('▼ 이전 대화')
else:
    st.info('사이드바에서 텍스트 또는 음성 명령을 실행하면 답변이 표시됩니다.')

st.caption('일정·To-do는 현재 접속 세션에만 유지되며 서버 재시작 후 사라질 수 있습니다.')
