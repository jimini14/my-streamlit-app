"""S03 레이아웃 예제와 첨부 달력 코드를 바탕으로 한 화면 위젯."""

import calendar
from datetime import date

import streamlit as st

from meeting_planner import add_schedule, add_todo


def _move_month(offset: int) -> None:
    year = st.session_state.calendar_year
    month = st.session_state.calendar_month + offset
    if month < 1:
        year, month = year - 1, 12
    elif month > 12:
        year, month = year + 1, 1
    st.session_state.calendar_year = year
    st.session_state.calendar_month = month


def render_calendar() -> None:
    st.subheader("📅 일정 캘린더")
    year = st.session_state.calendar_year
    month = st.session_state.calendar_month
    previous, heading, following = st.columns([1, 4, 1])
    with previous:
        if st.button("◀", key="previous_month", use_container_width=True):
            _move_month(-1)
            st.rerun()
    with heading:
        st.markdown(f"### {year}년 {month}월")
    with following:
        if st.button("▶", key="next_month", use_container_width=True):
            _move_month(1)
            st.rerun()

    for column, weekday in zip(st.columns(7), ["월", "화", "수", "목", "금", "토", "일"]):
        column.markdown(f"**{weekday}**")

    scheduled_days = {item["date"] for item in st.session_state.schedules}
    for week in calendar.monthcalendar(year, month):
        for column, day in zip(st.columns(7), week):
            if day == 0:
                continue
            current = date(year, month, day)
            label = f"{day} 📌" if current.isoformat() in scheduled_days else str(day)
            with column:
                if st.button(label, key=f"date_{current}", use_container_width=True):
                    st.session_state.selected_date = current
                    st.rerun()

    selected = st.session_state.selected_date
    st.divider()
    st.subheader(f"📝 {selected.isoformat()} 일정")
    has_time = st.checkbox("시간 지정", key="schedule_has_time")
    with st.form("schedule_form", clear_on_submit=True):
        title = st.text_input("일정 내용")
        when = st.time_input("일정 시간") if has_time else None
        submitted = st.form_submit_button("일정 등록")
    if submitted:
        try:
            added = add_schedule(title, selected.isoformat(), when.strftime("%H:%M") if when else "")
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.success("일정이 등록되었습니다." if added else "이미 등록된 일정입니다.")

    for item in list(st.session_state.schedules):
        if item["date"] != selected.isoformat():
            continue
        info, action = st.columns([5, 1])
        details = " · ".join(part for part in [item.get("time"), item.get("assignee")] if part)
        parent = f"↳ {item['parent']} / " if item.get("parent") else ""
        with info:
            st.write(f"{parent}{item['schedule']}" + (f" ({details})" if details else ""))
        with action:
            if st.button("삭제", key=f"schedule_delete_{item['id']}"):
                st.session_state.schedules.remove(item)
                st.rerun()


def render_todos() -> None:
    st.subheader("✅ To-do List")
    with st.form("todo_form", clear_on_submit=True):
        title = st.text_input("새로운 할 일")
        submitted = st.form_submit_button("업무 추가")
    if submitted:
        try:
            added = add_todo(title)
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.success("할 일이 추가되었습니다." if added else "이미 등록된 할 일입니다.")

    total = len(st.session_state.todos)
    completed = sum(item["done"] for item in st.session_state.todos)
    st.caption(f"완료한 업무: {completed} / {total}")
    if total:
        st.progress(completed / total)

    for item in list(st.session_state.todos):
        info, action = st.columns([5, 1])
        parent = f"↳ {item['parent']} / " if item.get("parent") else ""
        label = parent + item["task"] + (f" · {item['assignee']}" if item.get("assignee") else "")
        with info:
            item["done"] = st.checkbox(label, value=item["done"], key=f"todo_{item['id']}")
        with action:
            if st.button("❌", key=f"todo_delete_{item['id']}"):
                st.session_state.todos.remove(item)
                st.rerun()
