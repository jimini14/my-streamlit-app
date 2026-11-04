"""ABLE calendar and todo UI, session-scoped, based on 강지민 notebook."""
import calendar
import html
import re
from datetime import date, datetime, time
from uuid import uuid4
import streamlit as st

PROJECT_COLORS = {
    '일반': '#64748b',
    '프로젝트 A': '#2563eb',
    '프로젝트 B': '#16a34a',
    '프로젝트 C': '#9333ea',
    '개인 일정': '#ea580c',
}


def init_schedule_state():
    defaults = {
        'schedules': [], 'todos': [], 'selected_date': date.today(),
        'calendar_year': date.today().year, 'calendar_month': date.today().month,
        'calendar_recommendations': [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _add_schedule(title, day, start, end, project='일반'):
    st.session_state.schedules.append({
        'id': str(uuid4()), 'date': str(day), 'start': start,
        'end': end, 'schedule': title.strip(), 'project': project,
    })


def _add_todo(task, deadline):
    st.session_state.todos.append({
        'id': str(uuid4()), 'task': task.strip(),
        'deadline': deadline.isoformat(timespec='minutes'), 'done': False,
    })


def register_command(text):
    """Only add explicitly formatted commands; other speech/chat stays a question."""
    text = text.strip()
    match = re.fullmatch(
        r'일정\s*등록\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+(.+)', text
    )
    if match:
        day, start, end, title = match.groups()
        try:
            day = date.fromisoformat(day)
            start = time.fromisoformat(start)
            end = time.fromisoformat(end)
        except ValueError:
            return '날짜 또는 시간 형식을 확인하세요.'
        if start >= end:
            return '종료 시간은 시작 시간보다 늦어야 합니다.'
        _add_schedule(title, day, start.strftime('%H:%M'), end.strftime('%H:%M'))
        return f'캘린더에 {title} 일정이 등록되었습니다.'

    match = re.fullmatch(
        r'할\s*일\s*추가\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.+)', text
    )
    if match:
        day, at, task = match.groups()
        try:
            deadline = datetime.strptime(f'{day} {at}', '%Y-%m-%d %H:%M')
        except ValueError:
            return '마감 날짜 또는 시간 형식을 확인하세요.'
        _add_todo(task, deadline)
        return f'To-do List에 {task} 업무가 추가되었습니다.'

    if re.match(r'^(일정\s*등록|할\s*일\s*추가)', text):
        return '등록 명령에는 날짜, 시간, 내용을 명확히 입력하세요.'
    return None


def _recommend_tasks(title, day, start):
    mapping = {
        '회의': ['회의 안건 정리', '회의 자료 준비', '회의 참석자 확인'],
        '발표': ['발표 자료 제작', '발표 대본 작성', '발표 리허설'],
        '보고서': ['자료 조사', '보고서 초안 작성', '보고서 최종 검토'],
        '프로젝트': ['프로젝트 진행 상황 점검', '담당 업무 확인', '필요 자료 정리'],
    }
    suggestions = []
    for word, tasks in mapping.items():
        if word in title:
            suggestions = tasks
            break
    st.session_state.calendar_recommendations = [
        {'id': str(uuid4()), 'task': task, 'deadline': f'{day} {start}'}
        for task in suggestions
    ]


def show_calendar():
    st.subheader('📅 캘린더')
    year = st.session_state.calendar_year
    month = st.session_state.calendar_month
    left, center, right = st.columns([1, 4, 1])
    with left:
        if st.button('◀', key='prev_month'):
            if month == 1:
                st.session_state.calendar_year -= 1
                st.session_state.calendar_month = 12
            else:
                st.session_state.calendar_month -= 1
            st.rerun()
    with center:
        st.markdown(f'### {year}년 {month}월')
    with right:
        if st.button('▶', key='next_month'):
            if month == 12:
                st.session_state.calendar_year += 1
                st.session_state.calendar_month = 1
            else:
                st.session_state.calendar_month += 1
            st.rerun()

    legend = '　'.join(
        f'<span style="color:{color};font-weight:600">● {html.escape(project)}</span>'
        for project, color in PROJECT_COLORS.items()
    )
    st.markdown(legend, unsafe_allow_html=True)
    cols = st.columns(7)
    for i, weekday in enumerate(['월', '화', '수', '목', '금', '토', '일']):
        cols[i].write(weekday)

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                continue
            current = date(year, month, day)
            daily = sorted(
                (x for x in st.session_state.schedules if x['date'] == str(current)),
                key=lambda x: x['start'],
            )
            todos = [x for x in st.session_state.todos if x['deadline'][:10] == str(current)]
            tips = [f"일정: {x['start']}~{x['end']} {x['schedule']}" for x in daily]
            tips += [f"To-do: {x['task']} ({'완료' if x['done'] else '미완료'})" for x in todos]
            with cols[i]:
                if st.button(str(day), key=f'date_{current}',
                             help='\n\n'.join(tips) if tips else '등록된 일정과 업무가 없습니다.',
                             use_container_width=True):
                    st.session_state.selected_date = current
                    st.rerun()
                for item in daily[:2]:
                    color = PROJECT_COLORS.get(item.get('project', '일반'), '#64748b')
                    st.markdown(
                        f'<div style="color:{color};font-size:11px;overflow-wrap:anywhere">'
                        f'• {html.escape(item["schedule"][:12])}</div>',
                        unsafe_allow_html=True,
                    )
                if len(daily) > 2:
                    st.caption(f'+{len(daily)-2}개')

    selected = st.session_state.selected_date
    st.divider()
    st.subheader(f'📆 {selected} 상세 일정')
    daily = sorted(
        (x for x in st.session_state.schedules if x['date'] == str(selected)),
        key=lambda x: x['start'],
    )
    if not daily:
        st.info('등록된 일정이 없습니다.')
    for item in daily:
        c1, c2 = st.columns([5, 1])
        with c1:
            project = item.get('project', '일반')
            color = PROJECT_COLORS.get(project, '#64748b')
            st.markdown(f'<span style="color:{color}">● {html.escape(project)}</span>', unsafe_allow_html=True)
            st.write(f"⏰ {item['start']} ~ {item['end']} | {item['schedule']}")
        with c2:
            if st.button('삭제', key=f"schedule_delete_{item['id']}"):
                st.session_state.schedules = [x for x in st.session_state.schedules if x['id'] != item['id']]
                st.rerun()

    st.markdown('#### ✅ 해당 날짜 마감 To-do')
    due = [x for x in st.session_state.todos if x['deadline'][:10] == str(selected)]
    if not due:
        st.caption('해당 날짜에 마감되는 업무가 없습니다.')
    for item in due:
        st.write(f"{'✅ 완료' if item['done'] else '⬜ 미완료'} | {item['task']} | {item['deadline'][11:16]}")

    st.divider()
    st.subheader('➕ 일정 등록')
    with st.form('schedule_form', clear_on_submit=True):
        project = st.selectbox('프로젝트 선택', list(PROJECT_COLORS))
        title = st.text_input('일정 내용', placeholder='예: 프로젝트 팀 회의')
        start = st.time_input('시작 시간', value=time(9, 0))
        end = st.time_input('종료 시간', value=time(10, 0))
        submitted = st.form_submit_button('일정 등록')
    if submitted:
        if not title.strip():
            st.warning('일정 내용을 입력하세요.')
        elif start >= end:
            st.error('종료 시간은 시작 시간보다 늦어야 합니다.')
        else:
            _add_schedule(title, selected, start.strftime('%H:%M'), end.strftime('%H:%M'), project)
            _recommend_tasks(title, selected, start.strftime('%H:%M'))
            st.success('캘린더에 일정이 등록되었습니다.')

    if st.session_state.calendar_recommendations:
        st.divider()
        st.subheader('💡 일정 관련 추천 To-do')
        st.caption('추천된 업무는 자동 등록되지 않습니다. 마감시간을 확인한 뒤 추가하세요.')
        for item in st.session_state.calendar_recommendations:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write('• ' + item['task'])
                st.caption('임시 권장 마감: ' + item['deadline'])
            with c2:
                if st.button('추가', key=f"recommend_add_{item['id']}"):
                    _add_todo(item['task'], datetime.strptime(item['deadline'], '%Y-%m-%d %H:%M'))
                    st.session_state.calendar_recommendations = [
                        x for x in st.session_state.calendar_recommendations if x['id'] != item['id']
                    ]
                    st.rerun()


def show_todo():
    st.subheader('✅ My To-do List')
    with st.form('todo_form', clear_on_submit=True):
        task = st.text_input('할 일')
        due_date = st.date_input('마감 날짜', value=date.today())
        due_time = st.time_input('마감 시간', value=time(18, 0))
        submitted = st.form_submit_button('업무 추가')
    if submitted:
        if task.strip():
            _add_todo(task, datetime.combine(due_date, due_time))
            st.success('업무가 추가되었습니다.')
        else:
            st.warning('할 일을 입력하세요.')
    st.divider()
    total = len(st.session_state.todos)
    completed = sum(x['done'] for x in st.session_state.todos)
    st.write(f'업무 완료: {completed} / {total}')
    if total:
        st.progress(completed / total)
    for item in sorted(st.session_state.todos, key=lambda x: x['deadline']):
        c1, c2 = st.columns([5, 1])
        with c1:
            checked = st.checkbox(item['task'], value=item['done'], key=f"todo_{item['id']}")
            item['done'] = checked
            deadline = datetime.fromisoformat(item['deadline'])
            if checked:
                st.success('완료')
            elif deadline < datetime.now():
                st.error('마감기한 초과')
            else:
                st.caption('마감: ' + deadline.strftime('%Y-%m-%d %H:%M'))
        with c2:
            if st.button('❌', key=f"todo_delete_{item['id']}"):
                st.session_state.todos = [x for x in st.session_state.todos if x['id'] != item['id']]
                st.rerun()


def show_command_input():
    st.divider()
    st.subheader('💬 텍스트 일정 등록')
    st.caption('일정 등록 2026-11-05 14:00 15:00 팀 회의')
    st.caption('할 일 추가 2026-11-06 18:00 발표 자료 제출')
    with st.form('calendar_command_form'):
        command = st.text_input('등록 명령어를 입력하세요')
        submitted = st.form_submit_button('명령 실행')
    if submitted:
        outcome = register_command(command)
        st.info(outcome or '등록 명령이 아닙니다.')


def show_calendar_todo():
    init_schedule_state()
    st.header('📅 ABLE 일정 및 업무 관리')
    left, right = st.columns([2, 1])
    with left:
        show_calendar()
    with right:
        show_todo()
    show_command_input()
