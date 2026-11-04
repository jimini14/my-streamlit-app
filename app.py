
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

# 인적사항 기입란
st.divider()
st.subheader("👤 사용자 인적사항")

# 사용자 정보 초기화
if "profile" not in st.session_state:
    st.session_state.profile = {}

profile = st.session_state.profile

# 인적사항 입력
with st.form("profile_form"):

    name = st.text_input(
        "이름",
        value=profile.get("name", "")
    )

    department = st.text_input(
        "부서",
        value=profile.get("department", "")
    )

    position = st.text_input(
        "직책",
        value=profile.get("position", "")
    )

    email = st.text_input(
        "이메일",
        value=profile.get("email", "")
    )

    phone = st.text_input(
        "연락처",
        value=profile.get("phone", "")
    )

    profile_submit = st.form_submit_button("인적사항 저장")

# 정보 저장
if profile_submit:

    st.session_state.profile = {
        "name": name,
        "department": department,
        "position": position,
        "email": email,
        "phone": phone
    }

    st.success("인적사항이 저장되었습니다.")

# 저장된 정보 확인
if st.session_state.profile:

    st.subheader("📋 저장된 인적사항")

    st.write(st.session_state.profile)

# 키워드 분석 및 분류 코드
st.divider()
st.subheader("🔍 키워드 분석 및 분류")

# 키워드 분류 함수
def classify_keyword(text):

    keyword_dict = {
        "캘린더": ["일정", "캘린더", "예약", "회의 시간"],
        "To-do List": ["할 일", "업무", "과제", "작업"],
        "이메일": ["이메일", "메일", "발송", "보내줘"],
        "회의록 요약": ["회의록", "요약", "회의 내용"],
        "인적사항": ["이름", "부서", "직책", "연락처"]
    }

    result = []
    found_keywords = []

    for category, keywords in keyword_dict.items():

        for keyword in keywords:

            if keyword in text:
                found_keywords.append(keyword)

                if category not in result:
                    result.append(category)

    if not result:
        result = ["일반 질문"]

    return result, found_keywords


# 분석할 문장 입력
keyword_text = st.text_area(
    "분석할 문장을 입력하세요",
    placeholder="예: 내일 회의 일정을 등록하고 이메일을 보내줘"
)

# 분석 버튼
if st.button("키워드 분석"):

    if keyword_text.strip():

        categories, keywords = classify_keyword(keyword_text)

        st.subheader("📊 분석 결과")

        st.write("분류 결과:", ", ".join(categories))

        st.write(
            "추출된 키워드:",
            ", ".join(keywords) if keywords else "없음"
        )

    else:
        st.warning("분석할 문장을 입력하세요.")

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
