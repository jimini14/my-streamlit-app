
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


# ==================================================
# 추가 기능: 캘린더 + To-do List + 키워드 등록
# ==================================================

import calendar
import re
from datetime import date, datetime, time
from uuid import uuid4

# 상태 초기화
if "schedules" not in st.session_state:
    st.session_state.schedules = []

if "todos" not in st.session_state:
    st.session_state.todos = []

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = date.today().year

if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = date.today().month


# ==================================================
# 1. 텍스트 및 음성 명령 분석 함수
# ==================================================

def register_command(text):

    text = text.strip()

    # 캘린더 등록 명령
    # 형식: 일정 등록 2026-11-05 14:00 15:00 팀 회의
    calendar_match = re.fullmatch(
        r"일정\s*등록\s+"
        r"(\d{4}-\d{2}-\d{2})\s+"
        r"(\d{2}:\d{2})\s+"
        r"(\d{2}:\d{2})\s+(.+)",
        text
    )

    if calendar_match:
        day, start, end, title = calendar_match.groups()

        try:
            schedule_date = date.fromisoformat(day)
            start_time = time.fromisoformat(start)
            end_time = time.fromisoformat(end)
        except ValueError:
            return "날짜 또는 시간 형식이 올바르지 않습니다."

        if start_time >= end_time:
            return "종료 시간은 시작 시간보다 늦어야 합니다."

        st.session_state.schedules.append({
            "id": str(uuid4()),
            "date": str(schedule_date),
            "start": start,
            "end": end,
            "schedule": title.strip()
        })

        return f"캘린더에 '{title}' 일정이 등록되었습니다."

    # To-do List 등록 명령
    # 형식: 할 일 추가 2026-11-06 18:00 발표 자료 제출
    todo_match = re.fullmatch(
        r"할\s*일\s*추가\s+"
        r"(\d{4}-\d{2}-\d{2})\s+"
        r"(\d{2}:\d{2})\s+(.+)",
        text
    )

    if todo_match:
        day, deadline_time, task = todo_match.groups()

        try:
            deadline = datetime.strptime(
                f"{day} {deadline_time}",
                "%Y-%m-%d %H:%M"
            )
        except ValueError:
            return "마감 날짜 또는 시간이 올바르지 않습니다."

        st.session_state.todos.append({
            "id": str(uuid4()),
            "task": task.strip(),
            "deadline": deadline.isoformat(timespec="minutes"),
            "done": False
        })

        return f"To-do List에 '{task}' 업무가 추가되었습니다."

    # 키워드는 있지만 등록 정보가 부족한 경우
    if re.match(r"^(일정\s*등록|할\s*일\s*추가)", text):
        return "등록할 날짜, 시간, 내용을 정확하게 입력해 주세요."

    return "등록 명령이 아닙니다."


# ==================================================
# 2. 캘린더 및 To-do List 화면
# ==================================================

st.divider()
st.title("📅 ABLE 일정 및 업무 관리")

col1, col2 = st.columns([2, 1])


# ==================================================
# 3. 캘린더 (수정본)
# ==================================================

import html

# 프로젝트별 색상
PROJECT_COLORS = {
    "일반": "#64748b",
    "프로젝트 A": "#2563eb",
    "프로젝트 B": "#16a34a",
    "프로젝트 C": "#9333ea",
    "개인 일정": "#ea580c"
}

# 추천 To-do 임시 상태
if "calendar_recommendations" not in st.session_state:
    st.session_state.calendar_recommendations = []

with col1:

    st.subheader("📅 캘린더")

    year = st.session_state.calendar_year
    month = st.session_state.calendar_month

    # ----------------------------------------------
    # 월 이동
    # ----------------------------------------------

    c1, c2, c3 = st.columns([1, 4, 1])

    with c1:
        if st.button("◀", key="prev_month"):
            if month == 1:
                st.session_state.calendar_year -= 1
                st.session_state.calendar_month = 12
            else:
                st.session_state.calendar_month -= 1

            st.rerun()

    with c2:
        st.markdown(f"### {year}년 {month}월")

    with c3:
        if st.button("▶", key="next_month"):
            if month == 12:
                st.session_state.calendar_year += 1
                st.session_state.calendar_month = 1
            else:
                st.session_state.calendar_month += 1

            st.rerun()

    # ----------------------------------------------
    # 프로젝트 색상 범례
    # ----------------------------------------------

    st.markdown("**프로젝트 구분**")

    legend = "　".join(
        f'<span style="color:{color};font-weight:bold;">'
        f'● {html.escape(name)}</span>'
        for name, color in PROJECT_COLORS.items()
    )

    st.markdown(legend, unsafe_allow_html=True)

    # ----------------------------------------------
    # 요일 출력
    # ----------------------------------------------

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]

    cols = st.columns(7)

    for i, weekday in enumerate(weekdays):
        cols[i].write(weekday)

    # ----------------------------------------------
    # 월간 달력
    # ----------------------------------------------

    weeks = calendar.monthcalendar(year, month)

    for week in weeks:

        cols = st.columns(7)

        for i, day in enumerate(week):

            if day == 0:
                continue

            current_date = date(year, month, day)
            current_date_str = str(current_date)

            # 해당 날짜 일정
            daily_schedules = [
                item
                for item in st.session_state.schedules
                if item["date"] == current_date_str
            ]

            daily_schedules.sort(
                key=lambda x: x["start"]
            )

            # 해당 날짜 마감 To-do
            daily_todos = [
                item
                for item in st.session_state.todos
                if item["deadline"][:10] == current_date_str
            ]

            # 마우스 오버 시 표시할 내용
            tooltip_lines = []

            for item in daily_schedules:
                tooltip_lines.append(
                    f"일정: {item['start']}~{item['end']} "
                    f"{item['schedule']}"
                )

            for item in daily_todos:
                status = "완료" if item["done"] else "미완료"

                tooltip_lines.append(
                    f"To-do: {item['task']} ({status})"
                )

            tooltip = "\n\n".join(tooltip_lines)

            if not tooltip:
                tooltip = "등록된 일정과 업무가 없습니다."

            # 날짜 버튼
            with cols[i]:

                if st.button(
                    str(day),
                    key=f"date_{current_date}",
                    help=tooltip,
                    use_container_width=True
                ):
                    st.session_state.selected_date = current_date
                    st.rerun()

                # 일정 제목을 글자로 표시
                for item in daily_schedules[:2]:

                    project = item.get("project", "일반")

                    color = PROJECT_COLORS.get(
                        project, "#64748b"
                    )

                    title = html.escape(
                        item["schedule"][:12]
                    )

                    st.markdown(
                        f'<div style="'
                        f'color:{color};'
                        f'font-size:11px;'
                        f'font-weight:600;'
                        f'overflow-wrap:anywhere;'
                        f'">'
                        f'• {title}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                if len(daily_schedules) > 2:
                    st.caption(
                        f"+{len(daily_schedules) - 2}개"
                    )

    # ----------------------------------------------
    # 선택한 날짜의 일정 및 To-do
    # ----------------------------------------------

    selected_date = st.session_state.selected_date

    st.divider()
    st.subheader(f"📆 {selected_date} 상세 일정")

    daily_schedules = [
        item
        for item in st.session_state.schedules
        if item["date"] == str(selected_date)
    ]

    daily_schedules.sort(
        key=lambda x: x["start"]
    )

    if not daily_schedules:
        st.info("등록된 일정이 없습니다.")

    for item in daily_schedules:

        project = item.get("project", "일반")

        color = PROJECT_COLORS.get(
            project, "#64748b"
        )

        c1, c2 = st.columns([5, 1])

        with c1:
            st.markdown(
                f'<span style="color:{color};">'
                f'● {html.escape(project)}</span>',
                unsafe_allow_html=True
            )

            st.write(
                f"⏰ {item['start']} ~ {item['end']}"
                f" | {item['schedule']}"
            )

        with c2:
            if st.button(
                "삭제",
                key=f"schedule_delete_{item['id']}"
            ):
                st.session_state.schedules = [
                    x
                    for x in st.session_state.schedules
                    if x["id"] != item["id"]
                ]

                st.rerun()

    # 해당 날짜 To-do 표시
    st.markdown("#### ✅ 해당 날짜 마감 To-do")

    daily_todos = [
        item
        for item in st.session_state.todos
        if item["deadline"][:10] == str(selected_date)
    ]

    if not daily_todos:
        st.caption("해당 날짜에 마감되는 업무가 없습니다.")

    for item in daily_todos:

        status = "✅ 완료" if item["done"] else "⬜ 미완료"

        st.write(
            f"{status} | {item['task']} "
            f"| {item['deadline'][11:16]}"
        )

    # ----------------------------------------------
    # 일정 수동 등록
    # ----------------------------------------------

    st.divider()
    st.subheader("➕ 일정 등록")

    with st.form("schedule_form", clear_on_submit=True):

        project = st.selectbox(
            "프로젝트 선택",
            list(PROJECT_COLORS.keys())
        )

        schedule = st.text_input(
            "일정 내용",
            placeholder="예: 프로젝트 팀 회의"
        )

        start_time = st.time_input(
            "시작 시간",
            value=time(9, 0)
        )

        end_time = st.time_input(
            "종료 시간",
            value=time(10, 0)
        )

        schedule_submit = st.form_submit_button(
            "일정 등록"
        )

    if schedule_submit:

        if not schedule.strip():
            st.warning("일정 내용을 입력하세요.")

        elif start_time >= end_time:
            st.error(
                "종료 시간은 시작 시간보다 늦어야 합니다."
            )

        else:
            # 캘린더 일정 저장
            st.session_state.schedules.append({
                "id": str(uuid4()),
                "date": str(selected_date),
                "start": start_time.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
                "schedule": schedule.strip(),
                "project": project
            })

            st.success("캘린더에 일정이 등록되었습니다.")

            # --------------------------------------
            # 등록 일정 관련 추천 To-do 생성
            # --------------------------------------

            recommendations = []

            schedule_text = schedule.strip()

            if "회의" in schedule_text:
                recommendations = [
                    "회의 안건 정리",
                    "회의 자료 준비",
                    "회의 참석자 확인"
                ]

            elif "발표" in schedule_text:
                recommendations = [
                    "발표 자료 제작",
                    "발표 대본 작성",
                    "발표 리허설"
                ]

            elif "보고서" in schedule_text:
                recommendations = [
                    "자료 조사",
                    "보고서 초안 작성",
                    "보고서 최종 검토"
                ]

            elif "프로젝트" in schedule_text:
                recommendations = [
                    "프로젝트 진행 상황 점검",
                    "담당 업무 확인",
                    "필요 자료 정리"
                ]

            # 추천은 자동으로 To-do에 저장하지 않음
            st.session_state.calendar_recommendations = [
                {
                    "id": str(uuid4()),
                    "task": task,
                    "deadline": (
                        f"{selected_date} "
                        f"{start_time.strftime('%H:%M')}"
                    )
                }
                for task in recommendations
            ]

    # ----------------------------------------------
    # 추천 To-do 표시 및 선택적 추가
    # ----------------------------------------------

    if st.session_state.calendar_recommendations:

        st.divider()
        st.subheader("💡 추천 To-do List")

        st.caption(
            "등록한 일정과 관련된 추천 업무입니다. "
            "필요한 항목만 선택해 추가하세요."
        )

        for item in st.session_state.calendar_recommendations:

            c1, c2 = st.columns([5, 1])

            with c1:
                st.write(f"• {item['task']}")

                st.caption(
                    f"권장 마감: {item['deadline']}"
                )

            with c2:
                if st.button(
                    "추가",
                    key=f"recommend_add_{item['id']}"
                ):

                    deadline = datetime.strptime(
                        item["deadline"],
                        "%Y-%m-%d %H:%M"
                    )

                    st.session_state.todos.append({
                        "id": str(uuid4()),
                        "task": item["task"],
                        "deadline": deadline.isoformat(
                            timespec="minutes"
                        ),
                        "done": False
                    })

                    st.session_state.calendar_recommendations = [
                        x
                        for x in st.session_state.calendar_recommendations
                        if x["id"] != item["id"]
                    ]

                    st.rerun()


# ==================================================
# 4. To-do List
# ==================================================

with col2:

    st.subheader("✅ To-do List")

    # 업무 등록
    with st.form("todo_form", clear_on_submit=True):

        task = st.text_input("할 일")

        deadline_date = st.date_input(
            "마감 날짜",
            value=date.today()
        )

        deadline_time = st.time_input(
            "마감 시간",
            value=time(18, 0)
        )

        todo_submit = st.form_submit_button("업무 추가")

    if todo_submit:

        if not task.strip():
            st.warning("할 일을 입력하세요.")

        else:
            deadline = datetime.combine(
                deadline_date,
                deadline_time
            )

            st.session_state.todos.append({
                "id": str(uuid4()),
                "task": task.strip(),
                "deadline": deadline.isoformat(timespec="minutes"),
                "done": False
            })

            st.success("업무가 추가되었습니다.")

    st.divider()

    # 완료 현황
    total = len(st.session_state.todos)

    completed = sum(
        item["done"]
        for item in st.session_state.todos
    )

    st.write(f"업무 완료: {completed} / {total}")

    if total > 0:
        st.progress(completed / total)

    # 업무 목록
    for item in st.session_state.todos:

        c1, c2 = st.columns([5, 1])

        deadline = datetime.fromisoformat(item["deadline"])

        with c1:
            done = st.checkbox(
                item["task"],
                value=item["done"],
                key=f"todo_{item['id']}"
            )

            item["done"] = done

            if done:
                st.success("완료")
            elif deadline < datetime.now():
                st.error("마감기한 초과")
            else:
                st.caption(
                    "마감: " +
                    deadline.strftime("%Y-%m-%d %H:%M")
                )

        with c2:
            if st.button(
                "❌",
                key=f"todo_delete_{item['id']}"
            ):
                st.session_state.todos = [
                    x for x in st.session_state.todos
                    if x["id"] != item["id"]
                ]
                st.rerun()


# ==================================================
# 5. 텍스트 명령으로 일정 및 업무 등록
# ==================================================

st.divider()
st.subheader("💬 텍스트 일정 등록")

st.caption(
    "일정 등록 예시: "
    "일정 등록 2026-11-05 14:00 15:00 팀 회의"
)

st.caption(
    "업무 추가 예시: "
    "할 일 추가 2026-11-06 18:00 발표 자료 제출"
)

with st.form("command_form"):

    command_text = st.text_input(
        "등록 명령어를 입력하세요"
    )

    command_submit = st.form_submit_button("명령 실행")

if command_submit:

    result = register_command(command_text)
    st.info(result)

st.divider()
st.subheader("🎤 AI 음성 비서")


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
    
    # 음성 인식 결과 출력
st.write("🎤 인식된 음성:", transcript.text)

# 음성 명령 분석 및 일정·업무 등록
command_result = register_command(transcript.text)

if command_result != "등록 명령이 아닙니다.":
    st.info(command_result)

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
