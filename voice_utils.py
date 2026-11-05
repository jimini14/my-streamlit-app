"""[고도화] 음성(STT)으로 To-do·상세 일정을 등록하는 도우미."""
import hashlib
import json
from datetime import date

import streamlit as st

from audio_utils import transcribe_audio


def take_new_voice(audio) -> bytes | None:
    """같은 녹음을 rerun마다 다시 처리하지 않도록 새 녹음일 때만 bytes를 돌려줍니다."""
    if audio is None:
        return None
    data = audio.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if digest in st.session_state.processed_voice:
        return None
    st.session_state.processed_voice.add(digest)
    return data


def finish_voice() -> None:
    """녹음 위젯을 비우기 위해 key 버전을 올립니다."""
    st.session_state.voice_version += 1


def _ask_json(client, system: str, text: str) -> dict:
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
    )
    return json.loads(res.choices[0].message.content or "{}")


def voice_to_todos(client, audio_bytes: bytes) -> tuple[str, list[str]]:
    """녹음 → 텍스트 → 할 일 제목 목록."""
    text = transcribe_audio(client, audio_bytes)
    parsed = _ask_json(
        client,
        "사용자의 음성 메모에서 To-do 항목만 추출하세요. "
        '{"tasks": ["짧은 할 일 제목", ...]} 형식의 JSON만 반환합니다. '
        "'추가해 줘', '등록해 줘' 같은 명령어는 제목에서 빼고, 할 일이 없으면 빈 목록을 반환하세요.",
        text,
    )
    tasks = [str(t).strip() for t in parsed.get("tasks", []) if str(t).strip()]
    return text, tasks


def voice_to_schedule(client, audio_bytes: bytes, base_day: date) -> tuple[str, dict]:
    """녹음 → 텍스트 → {title, date, time}. 날짜 언급이 없으면 선택한 날짜를 사용합니다."""
    text = transcribe_audio(client, audio_bytes)
    parsed = _ask_json(
        client,
        f"사용자가 선택한 날짜는 {base_day.isoformat()}({'월화수목금토일'[base_day.weekday()]}요일)입니다. "
        "음성 메모에서 일정 하나를 추출해 "
        '{"title": "일정 제목", "date": "YYYY-MM-DD", "time": "HH:MM 또는 빈 문자열"} JSON만 반환하세요. '
        "날짜 언급이 없으면 선택한 날짜를, '내일'·'다음 주 금요일' 같은 표현은 선택한 날짜 기준으로 계산하세요. "
        "시간이 언급되지 않았으면 time은 빈 문자열입니다. '오후 3시'는 15:00처럼 24시간제로 씁니다.",
        text,
    )
    return text, parsed
