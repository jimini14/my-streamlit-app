"""한 번의 사용자 명령(텍스트·음성)을 처리하는 절차입니다."""
import json
import re
from dataclasses import dataclass

from app_state import korea_today
from assistant import build_user_prompt, is_email_request, run_assistant
from audio_utils import text_to_speech, transcribe_audio
from meeting_planner import add_schedule, add_todo

_PLAN_TARGET = re.compile(r"(일정|캘린더|투두|to.?do|할\s*일)", re.IGNORECASE)
_PLAN_ACTION = re.compile(r"(등록|추가|넣어|적어)")


class MissingInputError(ValueError):
    pass


@dataclass
class CommandResult:
    user_prompt: str
    answer: str
    email_status: str | None
    audio_bytes: bytes | None
    audio_error: str | None = None


def _speak(client, text):
    try:
        return (text_to_speech(client, text) if text else None), None
    except Exception as exc:
        return None, str(exc)


def _planner(client, user_prompt: str) -> str:
    """'11월 10일 발표 일정 등록해 줘', '보고서 작성 할 일 추가해 줘' 처리."""
    extraction = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                f"오늘 한국 날짜는 {korea_today()}입니다. 사용자가 등록을 요청한 내용을 JSON으로 추출하세요: "
                '{"kind":"schedule 또는 todo 또는 question","title":"업무명",'
                '"date":"YYYY-MM-DD 또는 빈 문자열","time":"HH:MM 또는 빈 문자열","answer":"확인할 질문"}. '
                "날짜가 명확하지 않은 캘린더 일정은 question으로 분류하고 추측하지 마세요."
            )},
            {"role": "user", "content": user_prompt},
        ],
    )
    parsed = json.loads(extraction.choices[0].message.content or "{}")
    kind, title = parsed.get("kind"), str(parsed.get("title", "")).strip()
    if kind == "schedule" and parsed.get("date") and title:
        try:
            added = add_schedule(title, parsed["date"], parsed.get("time", ""))
            return f"캘린더 {parsed['date']}에 '{title}' 일정을 등록했습니다." if added else "이미 등록된 일정입니다."
        except ValueError:
            return "날짜 형식이 불명확해 등록하지 못했습니다. 날짜를 확인해 주세요."
    if kind == "todo" and title:
        return f"To-do List에 '{title}'를 추가했습니다." if add_todo(title) else "이미 등록된 할 일입니다."
    return parsed.get("answer") or "등록할 내용을 구체적으로 알려 주세요."


def run_command(client, text_query: str, audio_query, meeting_content: str, sys_role: str,
                messages: list, recipient_email: str) -> CommandResult:
    # 음성이 있으면 STT, 없으면 텍스트 사용
    if audio_query is not None:
        data = audio_query.getvalue() if hasattr(audio_query, "getvalue") else audio_query
        user_prompt = transcribe_audio(client, data).strip()
    else:
        user_prompt = (text_query or "").strip()
    if not user_prompt:
        raise MissingInputError("텍스트 입력 또는 음성 녹음이 필요합니다.")

    # 1) 이메일 요청: 텍스트·음성 모두 도구 호출을 강제 (음성 메일 미발송 문제 해결)
    if is_email_request(user_prompt):
        if not recipient_email.strip():
            answer = "메일을 보낼 수신자 이메일 주소를 먼저 입력해 주세요."
            audio, err = _speak(client, answer)
            return CommandResult(user_prompt, answer, "이메일 발송 실패: 수신자 이메일 주소가 없습니다.", audio, err)
        answer, status = run_assistant(client, sys_role, messages, build_user_prompt(user_prompt, meeting_content),
                                       default_recipient=recipient_email, force_email=True)
        audio, err = _speak(client, answer.split("\n\n메일 내용:")[0])
        return CommandResult(user_prompt, answer, status, audio, err)

    # 2) 일정·할 일 등록 명령
    if _PLAN_TARGET.search(user_prompt) and _PLAN_ACTION.search(user_prompt):
        answer = _planner(client, user_prompt)
        audio, err = _speak(client, answer)
        return CommandResult(user_prompt, answer, None, audio, err)

    # 3) 일반 질문 (멀티턴)
    answer, status = run_assistant(client, sys_role, messages, build_user_prompt(user_prompt, meeting_content),
                                   default_recipient=recipient_email)
    audio, err = _speak(client, answer)
    return CommandResult(user_prompt, answer, status, audio, err)
