"""My To-do List: 텍스트·음성 추가, 체크, 삭제, 한글 PNG (진행 슬라이드 없음)."""
import streamlit as st

from app_state import get_client, korea_today
from meeting_planner import add_todo
from png_utils import todo_png
from voice_utils import finish_voice, take_new_voice, voice_to_todos


def _todo_voice():
    audio = st.audio_input("🎙️ 음성으로 할 일 추가", key=f"todo_voice_{st.session_state.voice_version}")
    data = take_new_voice(audio)
    if data is None:
        return
    with st.spinner("음성을 할 일로 바꾸는 중..."):
        try:
            text, tasks = voice_to_todos(get_client(), data)
        except Exception as exc:
            st.error(f"음성 처리 오류: {exc}")
            return
    added = [t for t in tasks if add_todo(t)]
    st.session_state.flash = ("✅ 할 일 추가: " + ", ".join(added)) if added else f"'{text}'에서 새 할 일을 찾지 못했어요."
    finish_voice()
    st.rerun()


def render_todos():
    st.subheader("✅ My To-do List")
    with st.form("todo_form", clear_on_submit=True, border=False):
        a, b = st.columns([3, 1.3], vertical_alignment="bottom")
        title = a.text_input("새로운 할 일", placeholder="예: 발표 자료 작성")
        submit = b.form_submit_button("추가", type="primary", width="stretch")
    if submit:
        try:
            if add_todo(title):
                st.rerun()
            st.info("이미 등록된 할 일입니다.")
        except ValueError as exc:
            st.warning(str(exc))
    _todo_voice()

    todos = st.session_state.todos
    if not todos:
        st.info("할 일을 입력하거나 음성으로 추가해 보세요.")
    for item in list(todos):
        a, b = st.columns([4, 1.3], vertical_alignment="center")
        item["done"] = a.checkbox(item["task"], value=item["done"], key=f"todo_{item['id']}")
        if b.button("삭제", key=f"del_todo_{item['id']}", width="stretch"):
            todos.remove(item)
            st.rerun()
    if todos:
        st.caption(f"완료 {sum(x['done'] for x in todos)} / 전체 {len(todos)}")
    st.download_button("📥 To-do PNG", todo_png(todos, korea_today()), file_name="todos.png",
                       mime="image/png", key="todo_png", on_click="ignore", width="stretch")
