# (출처: 1 - 레이아웃, 2 - 상태관리, 3 - 파일업로드, 7 - UI 구현)
import os
import streamlit as st
from openai import OpenAI

# 분리된 모듈 함수 임포트
from assistant import DEFAULT_SYS_ROLE, build_user_prompt, run_assistant
from audio_utils import transcribe_audio, text_to_speech
from calendar_todo import show_calendar_todo, register_command

# (출처: 4 - 4) 브라우저 레이아웃 설정
st.set_page_config(page_title="AI 개인비서 에이블", page_icon="🤖", layout="wide")

client = OpenAI()

# (출처: 2 - 4) 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "meeting_content" not in st.session_state:
    st.session_state.meeting_content = ""
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# (출처: 1 - 4, 5) 사이드바 설정 영역
with st.sidebar:
    st.header("⚙️ 비서 설정")
    recipient_email = st.text_input("수신자 이메일 주소", value=os.getenv("GMAIL_ADDRESS", ""))

    # (출처: 1 - 7) Expander를 통한 시스템 페르소나 설정
    with st.expander("에이블 페르소나 (프롬프트)"):
        sys_role = st.text_area("시스템 역할", value=DEFAULT_SYS_ROLE, height=220)

    # (출처: 2 - 3) 세션 초기화 버튼
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.messages.clear()
        st.session_state.audio_bytes = None
        st.session_state.meeting_content = ""
        st.rerun()

# 메인 타이틀 및 구분선 (출처: 1 - 8)
st.title("🤖 AI 개인비서 '에이블'")
st.markdown("회의록 업로드, 텍스트/음성 지시, 미팅 요약 및 이메일 발송 기능을 수행합니다.")
st.markdown("---")

# 강지민: 캘린더와 To-do List (기존 에이블 기능과 독립적으로 동작)
show_calendar_todo()
st.markdown("---")

# 좌우 1:1 분할 레이아웃 (출처: 1 - 2)
col1, col2 = st.columns([1, 1])

# [좌측] 입력 패널
with col1:
    st.subheader("📥 입력 영역")

    # 파일 업로드 (출처: 3 - 3, 7)
    uploaded_file = st.file_uploader("미팅 내용 파일 업로드 (.txt)", type=["txt"])
    if uploaded_file is not None:
        st.session_state.meeting_content = uploaded_file.read().decode("utf-8")
        st.success(f"파일 로드 완료: {uploaded_file.name}")
        with st.expander("미팅 내용 본문 보기"):
            st.text_area("미팅 본문", st.session_state.meeting_content, height=140, disabled=True)
    else:
        st.info("회의록 텍스트(.txt)를 업로드하면 미팅 내용과 연동됩니다.")

    # 폼 이벤트 묶기 (출처: 2 - 7 / 7 - 2)
    with st.form("command_form", clear_on_submit=False):
        text_query = st.text_input("텍스트 질문/명령")
        audio_query = st.audio_input("음성으로 녹음하여 질문하기")
        submit_btn = st.form_submit_button("실행하기", use_container_width=True)

# 명령 처리 로직
if submit_btn:
    user_prompt = ""

    # 1. 음성 입력 우선 전사 (STT) (출처: 6 - 미션 4)
    if audio_query is not None:
        with st.spinner("음성을 텍스트로 변환 중입니다..."):
            try:
                user_prompt = transcribe_audio(client, audio_query)
            except Exception as e:
                st.error(f"STT 오류: {e}")
                st.stop()
    elif text_query.strip():
        user_prompt = text_query.strip()
    else:
        st.warning("텍스트 입력 또는 음성 녹음이 필요합니다.")
        st.stop()

    # 강지민: 명확한 등록 명령인 경우에만 일정/To-do에 반영
    registration_result = register_command(user_prompt)
    if registration_result:
        st.info(registration_result)

    # 2. 미팅 내용과 결합한 프롬프트 생성 (출처: 6 - 미션 3)
    final_prompt = build_user_prompt(user_prompt, st.session_state.meeting_content)

    # 3. LLM 호출 및 도구 실행 (출처: 6 - 미션 2, 7)
    with st.spinner("에이블이 처리 중입니다..."):
        try:
            answer_text, email_result = run_assistant(
                client=client,
                sys_role=sys_role,
                conversation_history=st.session_state.messages,
                current_prompt=final_prompt,
                default_recipient=recipient_email
            )

            # 상태 저장 (출처: 2 - 5)
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            st.session_state.messages.append({"role": "assistant", "content": answer_text})

            if email_result:
                if "완료" in email_result:
                    st.success(email_result)
                else:
                    st.error(email_result)

            # 4. 음성 응답 합성 (TTS) (출처: 6 - 미션 5)
            st.session_state.audio_bytes = text_to_speech(client, answer_text)

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# [우측] 결과 출력 패널
with col2:
    st.subheader("📤 결과 및 대화 기록")

    # 음성 답변 재생 (출처: 6 - 미션 5, 6)
    if st.session_state.audio_bytes:
        st.write("🔊 **에이블의 음성 답변:**")
        st.audio(st.session_state.audio_bytes, format="audio/mp3")

    # 대화 히스토리 출력 (출처: 2 - 미니 실습 2)
    if st.session_state.messages:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    else:
        st.info("명령을 실행하면 결과가 이곳에 출력됩니다.")
