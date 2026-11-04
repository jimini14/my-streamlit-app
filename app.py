
import os, base64, json, requests
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client = OpenAI()

# 페이지 설정
st.set_page_config(page_title="음성 AI 서비스", page_icon="🤖", layout="wide")
st.title("음성 인식 AI 서비스")
st.write("음성으로 질문하시면 답변해 드립니다.")

# 역할 지정
sys_role = """
당신은 다양한 업무를 처리하는 AI 서비스입니다.
개인 비서처럼 친절하게 응대합니다.
"""

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 캘린더 + To-do List
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📅 캘린더")

    year = st.session_state.calendar_year
    month = st.session_state.calendar_month

    # 월 이동
    c1, c2, c3 = st.columns([1, 4, 1])

    with c1:
        if st.button("◀"):
            if month == 1:
                st.session_state.calendar_year -= 1
                st.session_state.calendar_month = 12
            else:
                st.session_state.calendar_month -= 1
            st.rerun()

    with c2:
        st.markdown(f"### {year}년 {month}월")

    with c3:
        if st.button("▶"):
            if month == 12:
                st.session_state.calendar_year += 1
                st.session_state.calendar_month = 1
            else:
                st.session_state.calendar_month += 1
            st.rerun()

    # 요일 표시
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    cols = st.columns(7)

    for i, day_name in enumerate(weekdays):
        cols[i].write(day_name)

    # 월간 달력 표시
    weeks = calendar.monthcalendar(year, month)

    for week in weeks:
        cols = st.columns(7)

        for i, day in enumerate(week):
            if day != 0:
                current_date = date(year, month, day)

                has_schedule = any(
                    item["date"] == str(current_date)
                    for item in st.session_state.schedules
                )

                label = f"{day} 📌" if has_schedule else str(day)

                with cols[i]:
                    if st.button(
                        label,
                        key=f"date_{current_date}",
                        use_container_width=True
                    ):
                        st.session_state.selected_date = current_date
                        st.rerun()

    # 일정 등록
    st.divider()

    selected_date = st.session_state.selected_date
    st.subheader(f"📝 {selected_date} 일정")

    with st.form("schedule_form", clear_on_submit=True):
        schedule = st.text_input("일정 내용")
        schedule_time = st.time_input("일정 시간")

        schedule_submit = st.form_submit_button("일정 등록")

    if schedule_submit:
        if schedule.strip():
            st.session_state.schedules.append({
                "date": str(selected_date),
                "time": str(schedule_time),
                "schedule": schedule.strip()
            })
            st.success("일정이 등록되었습니다.")
        else:
            st.warning("일정 내용을 입력하세요.")

    # 일정 조회 및 삭제
    for i, item in enumerate(st.session_state.schedules):
        if item["date"] == str(selected_date):

            c1, c2 = st.columns([5, 1])

            with c1:
                st.write(f"⏰ {item['time']} - {item['schedule']}")

            with c2:
                if st.button("삭제", key=f"schedule_delete_{i}"):
                    st.session_state.schedules.pop(i)
                    st.rerun()


# 지시 영역
with st.form("task_form"):
    uploaded_file = st.file_uploader("텍스트 파일 업로드", type=["txt"])
    audio_value = st.audio_input("무엇을 도와드릴까요?")
    submit = st.form_submit_button("실행")

# 버튼을 눌렀을 때만 실행
if submit:
    # 업로드 된 파일이 있으면 디코딩
    text = ""
    if uploaded_file is not None:
        text = uploaded_file.read().decode("utf-8")

    # 녹음이 없으면 녹음 요청
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # 시스템 메세지
    system_content = sys_role
    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"
    input_messages = [{"role": "system", "content": system_content}]

    # STT: 음성 → 텍스트
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.wav", audio_value, "audio/wav"))

    # 사용자 메시지
    input_messages.append({"role": "user", "content": transcript.text})

    # LLM 호출 및 응답 듣기
    with st.spinner("답변을 준비하고 있습니다..."):
        # LLM 호출
        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages
        )
        answer = response.output_text

        # 응답 출력
        st.subheader("AI 답변")
        st.write(answer)
