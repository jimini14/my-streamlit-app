"""Compact calendar with event labels, manual registration, recommendations and PNG."""
import calendar
import io
import os
from datetime import date, time

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from meeting_planner import add_schedule, add_todo


def _font(size):
    for name in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def _png(lines, title):
    image = Image.new("RGB", (950, max(190, 110 + len(lines)*36)), "white")
    draw = ImageDraw.Draw(image)
    draw.text((25,25), title, font=_font(27), fill="#1f2937")
    for i, line in enumerate(lines):
        draw.text((25,90+i*36),str(line)[:85],font=_font(17),fill="#334155")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def calendar_png(year, month, events):
    weeks = calendar.monthcalendar(year,month)
    img = Image.new('RGB',(1120,110+len(weeks)*125),'white')
    d=ImageDraw.Draw(img)
    d.text((20,15),f'ABLE Calendar {year}-{month:02d}',font=_font(28),fill='#1f2937')
    for j,wd in enumerate(['월','화','수','목','금','토','일']):
        d.text((j*160+10,74),wd,font=_font(18),fill='#475569')
    for i,week in enumerate(weeks):
        for j,day in enumerate(week):
            x,y=j*160,110+i*125
            d.rectangle((x,y,x+159,y+124),outline='#cbd5e1')
            if day:
                day_string=f'{year}-{month:02d}-{day:02d}'
                d.text((x+8,y+5),str(day),font=_font(18),fill='#0f172a')
                matches=[e for e in events if e['date']==day_string]
                for k,e in enumerate(matches[:3]):
                    d.text((x+8,y+32+k*27),(e.get('time','')+' '+e['schedule']).strip()[:12],font=_font(14),fill='#2563eb')
    out=io.BytesIO()
    img.save(out,format='PNG')
    return out.getvalue()


def _recommended(title):
    if '회의' in title:
        return ['회의 안건 정리','회의 자료 준비','참석자 확인']
    if '발표' in title:
        return ['발표 자료 작성','발표 대본 준비','발표 리허설']
    if '보고서' in title:
        return ['자료 조사','보고서 초안 작성','최종 검토']
    return [f'{title} 준비 사항 확인']


def render_calendar():
    st.subheader('📅 일정 캘린더')
    year,month=st.session_state.calendar_year,st.session_state.calendar_month
    a,b,c,d=st.columns([1,3,1,2])
    if a.button('◀',key='prev_month'):
        month-=1
        if month<1:month,year=12,year-1
        st.session_state.calendar_year,st.session_state.calendar_month=year,month
        st.rerun()
    b.markdown(f'### {year}년 {month}월')
    if c.button('▶',key='next_month'):
        month+=1
        if month>12:month,year=1,year+1
        st.session_state.calendar_year,st.session_state.calendar_month=year,month
        st.rerun()
    d.download_button('📥 달력 PNG',calendar_png(year,month,st.session_state.schedules),file_name='calendar.png',mime='image/png')

    for col,wd in zip(st.columns(7),['월','화','수','목','금','토','일']):
        col.markdown(f'**{wd}**')
    for week in calendar.monthcalendar(year,month):
        for col,day in zip(st.columns(7,gap='small'),week):
            if not day:
                col.write(' ')
                continue
            current=date(year,month,day)
            matches=[e for e in st.session_state.schedules if e['date']==current.isoformat()]
            with col:
                if st.button(str(day),key=f'date_{current}',use_container_width=True):
                    st.session_state.selected_date=current
                    st.rerun()
                for item in matches[:3]:
                    st.caption('📌 '+(item.get('time','')+' '+item['schedule']).strip())
                if len(matches)>3:st.caption(f'외 {len(matches)-3}개')


def render_details():
    selected=st.session_state.selected_date
    left,right=st.columns([1.1,1],gap='medium')
    with left:
        st.subheader(f'📝 {selected.isoformat()} 상세 일정')
        matches=[x for x in st.session_state.schedules if x['date']==selected.isoformat()]
        if not matches:st.info('선택한 날짜의 일정이 없습니다.')
        for item in list(matches):
            a,b=st.columns([5,1])
            a.write('• '+(item.get('time','')+' '+item['schedule']).strip())
            if b.button('삭제',key=f'del_schedule_{item["id"]}'):
                st.session_state.schedules.remove(item)
                st.rerun()
        has_time=st.checkbox('시간 지정',key='has_time')
        with st.form('schedule_form',clear_on_submit=True):
            title=st.text_input('일정 내용')
            when=st.time_input('일정 시간',value=time(9,0)) if has_time else None
            submitted=st.form_submit_button('선택한 날짜에 등록')
        if submitted:
            try:
                if add_schedule(title,selected.isoformat(),when.strftime('%H:%M') if when else ''):
                    st.session_state.calendar_recommendations=_recommended(title)
                    st.rerun()
                st.info('이미 등록된 일정입니다.')
            except ValueError as exc:
                st.warning(str(exc))
    with right:
        st.subheader('💡 추천 To-do List')
        analysis=st.session_state.get('meeting_analysis') or {}
        recs=[{'title':x['title'],'assignee':x.get('assignee',''),'parent':x.get('parent','')} for x in analysis.get('todos',[])]
        recs += [{'title':x,'assignee':'','parent':''} for x in st.session_state.calendar_recommendations]
        if not recs:st.caption('회의록 분석 또는 일정 등록 후 추천이 나타납니다.')
        for i,item in enumerate(recs):
            a,b=st.columns([5,1])
            a.write('• '+item['title'])
            if b.button('추가',key=f'add_rec_{i}'):
                add_todo(item['title'],item['assignee'],item['parent'])
                st.rerun()
        st.divider()
        st.subheader('📄 회의록 분석 결과')
        if not analysis:
            st.info('회의록을 올리면 분석 결과가 여기에 표시됩니다.')
        else:
            st.write(analysis.get('summary',''))
            st.markdown('**캘린더 등록 후보**')
            for i,item in enumerate(analysis.get('schedules',[])):
                a,b=st.columns([5,1])
                a.write(f"{item['date']} · {item['title']}")
                if b.button('등록',key=f'meeting_schedule_{i}'):
                    try:
                        add_schedule(item['title'],item['date'],item.get('time',''),item.get('assignee',''),item.get('parent',''))
                        st.rerun()
                    except (ValueError,TypeError) as exc:
                        st.warning(str(exc))
            if analysis.get('questions'):
                with st.expander('확인 필요한 사항'):
                    for question in analysis['questions']:st.write('• '+question)


def render_todos():
    st.subheader('✅ My To-do List')
    with st.form('todo_form',clear_on_submit=True):
        title=st.text_input('새로운 할 일')
        submit=st.form_submit_button('업무 추가')
    if submit:
        try:
            if add_todo(title):st.rerun()
        except ValueError as exc:st.warning(str(exc))
    total=len(st.session_state.todos)
    done=sum(x['done'] for x in st.session_state.todos)
    st.caption(f'완료 {done}/{total}')
    if total:st.progress(done/total)
    for item in list(st.session_state.todos):
        a,b=st.columns([5,1])
        item['done']=a.checkbox(item['task'],value=item['done'],key=f'todo_{item["id"]}')
        if b.button('❌',key=f'del_todo_{item["id"]}'):
            st.session_state.todos.remove(item)
            st.rerun()
    lines=[('[완료]' if x['done'] else '[미완료]')+' '+x['task'] for x in st.session_state.todos]
    st.download_button('📥 To-do PNG',_png(lines,'My To-do List'),file_name='todos.png',mime='image/png')
