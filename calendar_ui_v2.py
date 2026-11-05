"""진짜 달력 같은 다크 캘린더(참고 디자인) + 상세 일정(텍스트·음성) + 추천 To-do."""
import calendar
import html
from datetime import date, time

import streamlit as st

from app_state import get_client, korea_today
from meeting_planner import add_schedule, add_todo
from png_utils import calendar_png, event_color
from voice_utils import finish_voice, take_new_voice, voice_to_schedule

WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


# ---------------------------------------------------------------- 공통 도우미
def _label(item):
    return (item.get("time", "") + " " + item["schedule"]).strip()


def _sorted(items):
    return sorted(items, key=lambda e: (e["date"], e.get("time") or "99"))


def _select_day(day: date):
    st.session_state.selected_date = day
    st.session_state.calendar_year, st.session_state.calendar_month = day.year, day.month


def _move_month(step):
    y, m = st.session_state.calendar_year, st.session_state.calendar_month + step
    if m < 1:
        y, m = y - 1, 12
    elif m > 12:
        y, m = y + 1, 1
    st.session_state.calendar_year, st.session_state.calendar_month = y, m


def _go_today():
    _select_day(korea_today())


def _on_pick():
    _select_day(st.session_state.pick_date)


@st.cache_data(show_spinner=False)
def _png_cached(year, month, events_key, today):
    events = [dict(zip(("id", "date", "time", "schedule"), e)) for e in events_key]
    return calendar_png(year, month, events, today)


# ---------------------------------------------------------------- 달력 HTML
def calendar_html(year, month, events, today, selected) -> str:
    """inline style만 사용한 다크 달력. 한 줄 문자열로 만들어 마크다운 해석을 피합니다."""
    esc = html.escape
    by_day = {}
    for e in events:
        by_day.setdefault(e["date"], []).append(e)

    head = "".join(
        f'<div style="padding:0 0 8px 8px;font-size:12px;font-weight:700;letter-spacing:.06em;'
        f'color:{"#7FA8FF" if i == 5 else "#FF7A9C" if i == 6 else "#9CA0B0"};">{w}</div>'
        for i, w in enumerate(WEEKDAYS))

    cells = []
    for week in calendar.Calendar(0).monthdatescalendar(year, month):
        for d in week:
            inside = d.month == month
            bg = "#262733" if d.weekday() < 5 else "#21222B"
            border = "2px solid #16A9BC" if d == selected else "1px solid #30323E"
            num_style = "color:#E6E8F0;" if inside else "color:#5A5D6B;"
            if d == today:
                num_style = "color:#fff;background:#F0457E;border-radius:999px;padding:1px 7px;"
            items = sorted(by_day.get(d.isoformat(), []), key=lambda e: e.get("time") or "99") if inside else []
            shown = items if len(items) <= 3 else items[:2]
            pills = "".join(
                f'<div title="{esc(_label(e))}" style="background:{event_color(e)};color:#fff;font-size:11px;'
                f'font-weight:600;line-height:1.5;border-radius:999px;padding:1px 7px;margin-top:3px;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(e["schedule"])}</div>'
                for e in shown)
            if len(items) > len(shown):
                pills += f'<div style="color:#9CA0B0;font-size:11px;margin-top:3px;padding-left:4px;">+{len(items) - len(shown)}개 더</div>'
            cells.append(
                f'<div style="background:{bg};border:{border};border-radius:10px;min-height:92px;padding:6px;'
                f'min-width:0;overflow:hidden;box-sizing:border-box;">'
                f'<span style="font-size:13px;font-weight:700;line-height:1.6;{num_style}">{d.day}</span>{pills}</div>')

    month_items = _sorted([e for e in events if e["date"].startswith(f"{year}-{month:02d}-")])
    cards = []
    for e in month_items[:8]:
        d = date.fromisoformat(e["date"])
        meta = f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})" + (f" · {e['time']}" if e.get("time") else "")
        cards.append(
            f'<div style="display:flex;gap:12px;align-items:center;background:{event_color(e)};border-radius:12px;'
            f'padding:10px 12px;min-width:0;">'
            f'<div style="font-size:26px;font-weight:800;color:#fff;min-width:34px;text-align:center;line-height:1;">{d.day}</div>'
            f'<div style="min-width:0;"><div style="color:#fff;font-weight:700;font-size:14px;line-height:1.4;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(e["schedule"])}</div>'
            f'<div style="color:rgba(255,255,255,.88);font-size:12px;line-height:1.4;">{meta}</div></div></div>')
    if not month_items:
        cards.append('<div style="color:#9CA0B0;font-size:13px;line-height:1.6;">등록된 일정이 없습니다.</div>')
    elif len(month_items) > 8:
        cards.append(f'<div style="color:#9CA0B0;font-size:12px;align-self:center;">외 {len(month_items) - 8}건</div>')

    return (
        '<div style="background:#1F2029;border-radius:20px;padding:20px 20px 18px;'
        'box-shadow:0 10px 28px rgba(17,18,26,.22);">'
        f'<div style="color:#fff;font-size:28px;font-weight:300;line-height:1.2;">{calendar.month_name[month]} {year}</div>'
        f'<div style="color:#9CA0B0;font-size:13px;line-height:1.5;margin:2px 0 14px;">{year}년 {month}월</div>'
        f'<div style="display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;">{head}{"".join(cells)}</div>'
        '<div style="color:#fff;font-weight:700;font-size:15px;margin:18px 0 10px 2px;">이번 달 일정</div>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px;">'
        f'{"".join(cards)}</div></div>'
    )


# ---------------------------------------------------------------- 캘린더
def render_calendar():
    year, month = st.session_state.calendar_year, st.session_state.calendar_month
    today, selected = korea_today(), st.session_state.selected_date
    events = st.session_state.schedules

    # 날짜 선택 위젯을 선택 날짜와 맞춰 둠 (위젯 생성 전에만 값 변경 가능)
    if st.session_state.get("pick_date") != selected:
        st.session_state.pick_date = selected

    st.subheader("📅 일정 캘린더")
    c1, c2, c3, c4, c5 = st.columns([0.7, 0.9, 0.7, 2.2, 1.6], vertical_alignment="bottom")
    c1.button("◀", key="nav_prev", on_click=_move_month, args=(-1,), help="이전 달", width="stretch")
    c2.button("오늘", key="nav_today", on_click=_go_today, width="stretch")
    c3.button("▶", key="nav_next", on_click=_move_month, args=(1,), help="다음 달", width="stretch")
    c4.date_input("날짜 선택", key="pick_date", on_change=_on_pick, format="YYYY-MM-DD",
                  label_visibility="collapsed")
    try:
        key = tuple((e["id"], e["date"], e.get("time", ""), e["schedule"]) for e in events)
        c5.download_button("📥 달력 PNG", _png_cached(year, month, key, today),
                           file_name=f"calendar_{year}_{month:02d}.png", mime="image/png",
                           key="cal_png", on_click="ignore", width="stretch")
    except Exception as exc:
        c5.caption(f"PNG 생성 오류: {exc}")

    st.markdown(calendar_html(year, month, events, today, selected), unsafe_allow_html=True)


# ---------------------------------------------------------------- 상세 일정
def _recommended(title):
    if "회의" in title:
        return ["회의 안건 정리", "회의 자료 준비", "참석자 확인"]
    if "발표" in title:
        return ["발표 자료 작성", "발표 대본 준비", "발표 리허설"]
    if "보고서" in title:
        return ["자료 조사", "보고서 초안 작성", "최종 검토"]
    return [f"{title} 준비 사항 확인"]


def _schedule_voice(selected: date):
    audio = st.audio_input("🎙️ 음성으로 일정 추가 (예: 내일 오후 3시 고객사 미팅)",
                           key=f"schedule_voice_{st.session_state.voice_version}")
    data = take_new_voice(audio)
    if data is None:
        return
    with st.spinner("음성을 일정으로 바꾸는 중..."):
        try:
            text, parsed = voice_to_schedule(get_client(), data, selected)
        except Exception as exc:
            st.error(f"음성 처리 오류: {exc}")
            return
    title = str(parsed.get("title", "")).strip()
    day, when = str(parsed.get("date") or selected.isoformat()), str(parsed.get("time") or "")
    try:
        added = add_schedule(title, day, when)
    except ValueError:
        st.warning(f"'{text}'에서 일정을 찾지 못했습니다. 다시 말씀해 주세요.")
        return
    if added:
        st.session_state.calendar_recommendations = _recommended(title)
        _select_day(date.fromisoformat(day))
        st.session_state.flash = f"🗓️ '{title}' 일정을 {day} {when}에 등록했어요.".replace("  ", " ")
    else:
        st.session_state.flash = "이미 등록된 일정입니다."
    finish_voice()
    st.rerun()


def render_details():
    selected = st.session_state.selected_date
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.subheader(f"📝 {selected.month}월 {selected.day}일 ({WEEKDAYS[selected.weekday()]}) 상세 일정")
        matches = _sorted([x for x in st.session_state.schedules if x["date"] == selected.isoformat()])
        if not matches:
            st.info("선택한 날짜의 일정이 없습니다.")
        for item in matches:
            a, b = st.columns([5, 1], vertical_alignment="center")
            extra = " · ".join(v for v in (item.get("assignee", ""), item.get("parent", "")) if v)
            a.markdown(
                f'<div style="line-height:1.5;"><span style="display:inline-block;width:10px;height:10px;'
                f'border-radius:50%;background:{event_color(item)};margin-right:8px;"></span>'
                f'<b>{html.escape(_label(item))}</b>'
                + (f' <span style="color:#7B8394;font-size:.85rem;">({html.escape(extra)})</span>' if extra else "")
                + "</div>", unsafe_allow_html=True)
            if b.button("삭제", key=f"del_schedule_{item['id']}", width="stretch"):
                st.session_state.schedules.remove(item)
                st.rerun()

        with st.container(border=True):
            st.markdown("**➕ 일정 추가**")
            has_time = st.toggle("시간 지정", key="has_time")
            with st.form("schedule_form", clear_on_submit=True, border=False):
                title = st.text_input("일정 내용", placeholder="예: 주간 보고 회의")
                f1, f2 = st.columns(2)
                day = f1.date_input("날짜", value=selected, format="YYYY-MM-DD")
                when = f2.time_input("시간", value=time(9, 0), step=600) if has_time else None
                submitted = st.form_submit_button("일정 등록", type="primary", width="stretch")
            if submitted:
                try:
                    if add_schedule(title, day.isoformat(), when.strftime("%H:%M") if when else ""):
                        st.session_state.calendar_recommendations = _recommended(title)
                        _select_day(day)
                        st.rerun()
                    st.info("이미 등록된 일정입니다.")
                except ValueError as exc:
                    st.warning(str(exc))
            _schedule_voice(selected)

    with right:
        st.subheader("💡 추천 To-do")
        analysis = st.session_state.get("meeting_analysis") or {}
        recs = [{"title": x["title"], "assignee": x.get("assignee", ""), "parent": x.get("parent", "")}
                for x in analysis.get("todos", [])]
        recs += [{"title": x, "assignee": "", "parent": ""} for x in st.session_state.calendar_recommendations]
        existing, seen, unique = {t["task"] for t in st.session_state.todos}, set(), []
        for r in recs:
            if r["title"] not in existing and r["title"] not in seen:
                seen.add(r["title"])
                unique.append(r)
        if not unique:
            st.caption("회의록 분석 또는 일정 등록 후 추천이 나타납니다.")
        for i, item in enumerate(unique):
            a, b = st.columns([4, 1.3], vertical_alignment="center")
            sub = f' <span style="color:#7B8394;font-size:.85rem;">· {html.escape(item["assignee"])}</span>' if item["assignee"] else ""
            a.markdown(f'<div style="line-height:1.5;">• {html.escape(item["title"])}{sub}</div>', unsafe_allow_html=True)
            if b.button("추가", key=f"add_rec_{i}", width="stretch"):
                add_todo(item["title"], item["assignee"], item["parent"])
                st.rerun()
