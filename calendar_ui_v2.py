"""캘린더(회의/마감 색 구분), 상세 일정·To-do 음성 등록, 추천 To-do, 한글 PNG 저장."""
import calendar
import hashlib
import html
import io
import os
import tempfile
import urllib.request
from datetime import date, time
from functools import lru_cache
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from audio_utils import transcribe_audio
from command_service import parse_spoken_item
from meeting_planner import SCHEDULE_KINDS, add_schedule, add_todo, focus_date, kind_of

WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']
KIND_OPTIONS = {'회의': 'meeting', '마감기한': 'deadline', '일반': 'general'}


# ---------------- 한글 폰트 (PNG 한글 깨짐 해결) ----------------
# 1순위: 저장소의 fonts/NanumGothic.ttf  2순위: packages.txt로 설치되는 fonts-nanum
# 3순위: 그 밖의 CJK 폰트  4순위: Google Fonts에서 나눔고딕을 한 번 내려받아 임시 폴더에 보관
_FONT_CANDIDATES = (
    str(Path(__file__).with_name('fonts') / 'NanumGothic.ttf'),
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
)
_FONT_URL = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf'


@lru_cache(maxsize=1)
def _font_path():
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    target = Path(tempfile.gettempdir()) / 'NanumGothic-Regular.ttf'
    if not target.exists():
        try:
            with urllib.request.urlopen(_FONT_URL, timeout=15) as resp:
                target.write_bytes(resp.read())
        except Exception:
            return None
    return str(target)


@lru_cache(maxsize=32)
def _font(size):
    path = _font_path()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _fit(draw, text, font, max_width):
    """칸 너비를 넘는 글자는 잘리지 않도록 '…'로 줄입니다."""
    text = str(text)
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + '…', font=font) > max_width:
        text = text[:-1]
    return text + '…'


def _wrap(draw, text, font, max_width):
    """긴 할 일은 이미지 밖으로 잘리지 않도록 여러 줄로 나눕니다."""
    lines, current = [], ''
    for ch in str(text):
        if current and draw.textlength(current + ch, font=font) > max_width:
            lines.append(current)
            current = ch.lstrip()
        else:
            current += ch
    lines.append(current)
    return lines


def _to_png(image):
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def calendar_png(year, month, events):
    weeks = calendar.monthcalendar(year, month)
    cw, ch, top = 160, 125, 110
    img = Image.new('RGB', (cw * 7, top + len(weeks) * ch + 55), 'white')
    d = ImageDraw.Draw(img)
    d.text((20, 15), f'ABLE 캘린더 {year}년 {month}월', font=_font(28), fill='#1f2937')
    for j, wd in enumerate(WEEKDAYS):
        color = '#dc2626' if j == 6 else '#2563eb' if j == 5 else '#475569'
        d.text((j * cw + 10, 74), wd, font=_font(18), fill=color)
    small = _font(14)
    for i, week in enumerate(weeks):
        for j, day in enumerate(week):
            x, y = j * cw, top + i * ch
            d.rectangle((x, y, x + cw - 1, y + ch - 1), outline='#cbd5e1')
            if not day:
                continue
            d.text((x + 8, y + 5), str(day), font=_font(18), fill='#0f172a')
            day_string = f'{year}-{month:02d}-{day:02d}'
            matches = sorted((e for e in events if e['date'] == day_string), key=lambda e: e.get('time', ''))
            for k, e in enumerate(matches[:3]):
                color = SCHEDULE_KINDS[kind_of(e)]['color']
                ty = y + 34 + k * 26
                d.rectangle((x + 8, ty + 2, x + 12, ty + 16), fill=color)
                label = (e.get('time', '') + ' ' + e['schedule']).strip()
                d.text((x + 17, ty), _fit(d, label, small, cw - 25), font=small, fill=color)
            if len(matches) > 3:
                d.text((x + 8, y + ch - 20), f'외 {len(matches) - 3}개', font=_font(12), fill='#64748b')
    # 범례
    ly, lx = top + len(weeks) * ch + 18, 20
    for info in SCHEDULE_KINDS.values():
        d.rectangle((lx, ly + 3, lx + 14, ly + 17), fill=info['color'])
        d.text((lx + 20, ly), info['label'], font=_font(16), fill='#334155')
        lx += 40 + int(d.textlength(info['label'], font=_font(16)))
    return _to_png(img)


def todo_png(todos):
    width, pad, line_h = 950, 30, 30
    font, title_font = _font(18), _font(28)
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    text_x = pad + 34
    rows = []
    for item in todos:
        label = item['task'] + (f" (담당: {item['assignee']})" if item.get('assignee') else '')
        rows.append((item['done'], _wrap(measure, label, font, width - text_x - pad)))
    height = max(190, 105 + sum(len(lines) * line_h + 12 for _, lines in rows) + pad)
    img = Image.new('RGB', (width, height), 'white')
    d = ImageDraw.Draw(img)
    d.text((pad, 22), 'My To-do List', font=title_font, fill='#1f2937')
    done_count = sum(1 for done, _ in rows if done)
    d.text((pad, 62), f'완료 {done_count}/{len(rows)}', font=_font(16), fill='#64748b')
    y = 100
    if not rows:
        d.text((pad, y), '등록된 할 일이 없습니다.', font=font, fill='#64748b')
    for done, lines in rows:
        # 체크박스를 글자 대신 도형으로 그려 기호가 잘리거나 깨지지 않게 합니다.
        d.rectangle((pad, y + 4, pad + 20, y + 24), outline='#334155', width=2,
                    fill='#dcfce7' if done else 'white')
        if done:
            d.line([(pad + 4, y + 14), (pad + 9, y + 19), (pad + 17, y + 8)], fill='#16a34a', width=3)
        for i, line in enumerate(lines):
            d.text((text_x, y + i * line_h), line, font=font, fill='#94a3b8' if done else '#1f2937')
        y += len(lines) * line_h + 12
    return _to_png(img)


def _safe_download(container, label, builder, file_name):
    try:
        data = builder()
    except Exception as exc:
        container.caption(f'PNG 생성 오류: {exc}')
        return
    # on_click='ignore' : 다운로드 클릭 시 앱을 다시 실행하지 않습니다.
    container.download_button(label, data, file_name=file_name, mime='image/png', on_click='ignore')


# ---------------- 음성 입력(STT) 공통 ----------------
def _voice_text(label, key, get_client):
    """새로 녹음된 음성만 한 번 텍스트로 변환합니다. 반환: (텍스트, 오류)"""
    versions = st.session_state.voice_versions
    audio = st.audio_input(label, key=f'{key}_{versions.get(key, 0)}')
    if audio is None:
        return None, None
    data = audio.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if digest in st.session_state.processed_voice:
        return None, None
    st.session_state.processed_voice.add(digest)
    versions[key] = versions.get(key, 0) + 1   # 다음 실행에서 녹음 위젯을 비웁니다.
    try:
        with st.spinner('음성을 인식하는 중...'):
            return transcribe_audio(get_client(), data).strip(), None
    except Exception as exc:
        return None, f'음성 인식 오류: {exc}'


def _show_notice(key):
    notice = st.session_state.voice_notice.pop(key, None)
    if notice:
        (st.success if notice[0] == 'ok' else st.warning)(notice[1])


def _kind_badge(kind):
    info = SCHEDULE_KINDS[kind]
    return (f"<span style='background:{info['color']};color:white;border-radius:4px;"
            f"padding:0 6px;font-size:0.75rem;margin-right:6px'>{info['label']}</span>")


def _recommended(title):
    if '회의' in title:
        return ['회의 안건 정리', '회의 자료 준비', '참석자 확인']
    if '발표' in title:
        return ['발표 자료 작성', '발표 대본 준비', '발표 리허설']
    if '보고서' in title:
        return ['자료 조사', '보고서 초안 작성', '최종 검토']
    return [f'{title} 준비 사항 확인']


# ---------------- 캘린더 ----------------
def render_calendar():
    st.subheader('📅 일정 캘린더')
    year, month = st.session_state.calendar_year, st.session_state.calendar_month
    a, b, c, d = st.columns([1, 3, 1, 2])
    if a.button('◀', key='prev_month'):
        month -= 1
        if month < 1:
            month, year = 12, year - 1
        st.session_state.calendar_year, st.session_state.calendar_month = year, month
        st.rerun()
    b.markdown(f'### {year}년 {month}월')
    if c.button('▶', key='next_month'):
        month += 1
        if month > 12:
            month, year = 1, year + 1
        st.session_state.calendar_year, st.session_state.calendar_month = year, month
        st.rerun()
    events = [dict(e) for e in st.session_state.schedules]
    _safe_download(d, '📥 달력 PNG', lambda: calendar_png(year, month, events), f'calendar_{year}_{month:02d}.png')

    legend = ' '.join(_kind_badge(k) for k in SCHEDULE_KINDS)
    st.markdown(legend, unsafe_allow_html=True)

    for col, wd in zip(st.columns(7), WEEKDAYS):
        col.markdown(f'**{wd}**')
    for week in calendar.monthcalendar(year, month):
        for col, day in zip(st.columns(7, gap='small'), week):
            if not day:
                col.write(' ')
                continue
            current = date(year, month, day)
            matches = sorted((e for e in st.session_state.schedules if e['date'] == current.isoformat()),
                             key=lambda e: e.get('time', ''))
            with col:
                if st.button(str(day), key=f'date_{current}', use_container_width=True,
                             type='primary' if current == st.session_state.selected_date else 'secondary'):
                    st.session_state.selected_date = current
                    st.rerun()
                for item in matches[:3]:
                    color = SCHEDULE_KINDS[kind_of(item)]['color']
                    text = html.escape((item.get('time', '') + ' ' + item['schedule']).strip())
                    st.markdown(
                        f"<div style='font-size:0.78rem;line-height:1.3;color:{color};"
                        f"border-left:3px solid {color};padding-left:4px;margin-bottom:2px;"
                        f"word-break:break-all'>{text}</div>",
                        unsafe_allow_html=True)
                if len(matches) > 3:
                    st.caption(f'외 {len(matches) - 3}개')


# ---------------- 상세 일정 + 추천 To-do ----------------
def render_details(get_client):
    selected = st.session_state.selected_date
    left, right = st.columns([1.1, 1], gap='medium')
    with left:
        st.subheader(f'📝 {selected.isoformat()} 상세 일정')
        _show_notice('schedule')
        matches = sorted((x for x in st.session_state.schedules if x['date'] == selected.isoformat()),
                         key=lambda e: e.get('time', ''))
        if not matches:
            st.info('선택한 날짜의 일정이 없습니다.')
        for item in list(matches):
            a, b = st.columns([5, 1], vertical_alignment='center')
            text = html.escape((item.get('time', '') + ' ' + item['schedule']).strip())
            a.markdown(_kind_badge(kind_of(item)) + text, unsafe_allow_html=True)
            if b.button('삭제', key=f'del_schedule_{item["id"]}'):
                st.session_state.schedules.remove(item)
                st.rerun()

        # 음성으로 일정 등록 (예: "오후 3시 팀 회의", "금요일까지 보고서 제출")
        spoken, error = _voice_text('🎙️ 음성으로 일정 등록', 'voice_schedule', get_client)
        if error:
            st.session_state.voice_notice['schedule'] = ('warn', error)
            st.rerun()
        if spoken:
            try:
                parsed = parse_spoken_item(get_client(), spoken, 'schedule', selected.isoformat())
                title = str(parsed.get('title') or spoken).strip()
                day = parsed.get('date') or selected.isoformat()
                added = add_schedule(title, day, parsed.get('time', ''), kind=parsed.get('kind', 'general'))
                if added:
                    focus_date(date.fromisoformat(day))
                    st.session_state.calendar_recommendations = _recommended(title)
                    notice = ('ok', f"🎙️ \"{spoken}\" → {day} '{title}' 일정을 등록했습니다.")
                else:
                    notice = ('warn', '이미 등록된 일정입니다.')
            except Exception as exc:
                notice = ('warn', f'음성 일정 등록 실패: {exc}')
            st.session_state.voice_notice['schedule'] = notice
            st.rerun()

        has_time = st.checkbox('시간 지정', key='has_time')
        with st.form('schedule_form', clear_on_submit=True):
            title = st.text_input('일정 내용')
            kind_label = st.radio('일정 종류', list(KIND_OPTIONS), horizontal=True)
            when = st.time_input('일정 시간', value=time(9, 0)) if has_time else None
            submitted = st.form_submit_button('선택한 날짜에 등록')
        if submitted:
            try:
                if add_schedule(title, selected.isoformat(), when.strftime('%H:%M') if when else '',
                                kind=KIND_OPTIONS[kind_label]):
                    st.session_state.calendar_recommendations = _recommended(title)
                    st.rerun()
                st.info('이미 등록된 일정입니다.')
            except ValueError as exc:
                st.warning(str(exc))

    with right:
        st.subheader('💡 추천 To-do List')
        analysis = st.session_state.get('meeting_analysis') or {}
        recs = [{'title': x['title'], 'assignee': x.get('assignee', ''), 'parent': x.get('parent', '')}
                for x in analysis.get('todos', [])]
        recs += [{'title': x, 'assignee': '', 'parent': ''} for x in st.session_state.calendar_recommendations]
        existing = {x['task'] for x in st.session_state.todos}
        seen, visible = set(), []
        for item in recs:
            if item['title'] not in existing and item['title'] not in seen:
                seen.add(item['title'])
                visible.append(item)
        if not visible:
            st.caption('회의록 분석 또는 일정 등록 후 추천이 나타납니다.')
        for item in visible:
            a, b = st.columns([5, 1], vertical_alignment='center')
            a.write('• ' + item['title'])
            key = hashlib.md5(item['title'].encode('utf-8')).hexdigest()[:12]
            if b.button('추가', key=f'add_rec_{key}'):
                add_todo(item['title'], item['assignee'], item['parent'])
                st.rerun()


# ---------------- My To-do ----------------
def render_todos(get_client):
    st.subheader('✅ My To-do List')
    _show_notice('todo')

    # 음성으로 할 일 추가 (예: "고객사 견적서 보내기 추가해 줘")
    spoken, error = _voice_text('🎙️ 음성으로 할 일 추가', 'voice_todo', get_client)
    if error:
        st.session_state.voice_notice['todo'] = ('warn', error)
        st.rerun()
    if spoken:
        try:
            parsed = parse_spoken_item(get_client(), spoken, 'todo')
            title = str(parsed.get('title') or spoken).strip()
            notice = ('ok', f"🎙️ '{title}'를 추가했습니다.") if add_todo(title) else ('warn', '이미 등록된 할 일입니다.')
        except Exception as exc:
            notice = ('warn', f'음성 할 일 추가 실패: {exc}')
        st.session_state.voice_notice['todo'] = notice
        st.rerun()

    with st.form('todo_form', clear_on_submit=True):
        title = st.text_input('새로운 할 일')
        submit = st.form_submit_button('업무 추가')
    if submit:
        try:
            if add_todo(title):
                st.rerun()
        except ValueError as exc:
            st.warning(str(exc))

    total = len(st.session_state.todos)
    done = sum(x['done'] for x in st.session_state.todos)
    st.caption(f'완료 {done}/{total}')
    for item in list(st.session_state.todos):
        # 좁은 오른쪽 영역에서도 삭제 버튼이 잘리지 않도록 여백 없는 버튼을 사용합니다.
        a, b = st.columns([0.82, 0.18], vertical_alignment='center')
        item['done'] = a.checkbox(item['task'], value=item['done'], key=f'todo_{item["id"]}')
        if b.button('✕', key=f'del_todo_{item["id"]}', type='tertiary', help='삭제'):
            st.session_state.todos.remove(item)
            st.rerun()
    todos = [dict(x) for x in st.session_state.todos]
    _safe_download(st, '📥 To-do PNG', lambda: todo_png(todos), 'todos.png')
