"""한 번의 사용자 명령을 처리하는 절차입니다."""

from dataclasses import dataclass
import json
import re
from app_state import korea_today
from meeting_planner import add_schedule, add_todo

from assistant import build_user_prompt, run_assistant
from audio_utils import transcribe_audio, text_to_speech


class MissingInputError(ValueError):
    pass


@dataclass
class CommandResult:
    user_prompt: str
    answer: str
    email_status: str | None
    audio_bytes: bytes | None
    audio_error: str | None = None


def run_command(
    client,
    text_query: str,
    audio_query,
    meeting_content: str,
    sys_role: str,
    messages: list,
    recipient_email: str,
) -> CommandResult:
    if audio_query is not None:
        user_prompt = transcribe_audio(client, audio_query)
    else:
        user_prompt = text_query.strip()

    if not user_prompt.strip():
        raise MissingInputError("텍스트 입력 또는 음성 녹음이 필요합니다.")

    # Explicit scheduling commands work with text or STT voice transcription.
    # Non-planner questions continue through Hojun's multiturm assistant below.
    if re.search(r"(일정|캘린더|투두|to.?do|할\s*일)", user_prompt, re.IGNORECASE) and re.search(r"(등록|추가|넣어|적어)", user_prompt):
        extraction = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":(
                    f"오늘 한국 날짜는 {korea_today()}입니다. 사용자가 등록을 명시적으로 요청한 내용을 "
                    "JSON으로 추출하세요: {\"kind\":\"schedule 또는 todo 또는 question\","
                    "\"title\":\"업무명\",\"date\":\"YYYY-MM-DD 또는 빈 문자열\","
                    "\"time\":\"HH:MM 또는 빈 문자열\",\"answer\":\"확인할 질문\"}. "
                    "날짜가 명확하지 않은 캘린더 일정은 question으로 분류하고 추측하지 마세요."
                )},
                {"role":"user","content":user_prompt},
            ],
        )
        parsed = json.loads(extraction.choices[0].message.content or '{}')
        kind = parsed.get('kind')
        title = str(parsed.get('title','')).strip()
        if kind == 'schedule' and parsed.get('date') and title:
            try:
                added = add_schedule(title,parsed['date'],parsed.get('time',''))
                answer = f"캘린더에 '{title}' 일정을 등록했습니다." if added else "이미 등록된 일정입니다."
            except ValueError:
                answer = "날짜 형식이 불명확해 등록하지 못했습니다. 날짜를 확인해 주세요."
        elif kind == 'todo' and title:
            added = add_todo(title)
            answer = f"To-do List에 '{title}'를 추가했습니다." if added else "이미 등록된 할 일입니다."
        else:
            answer = parsed.get('answer') or "등록할 내용을 구체적으로 알려 주세요."
        try:
            speech = text_to_speech(client,answer)
            speech_error = None
        except Exception as exc:
            speech,speech_error = None,str(exc)
        return CommandResult(user_prompt,answer,None,speech,speech_error)

    final_prompt = build_user_prompt(user_prompt, meeting_content)
    answer, email_status = run_assistant(
        client=client,
        sys_role=sys_role,
        conversation_history=messages,
        current_prompt=final_prompt,
        default_recipient=recipient_email,
    )
    answer = answer or ""

    try:
        audio_bytes = text_to_speech(client, answer) if answer else None
        audio_error = None
    except Exception as exc:
        audio_bytes = None
        audio_error = str(exc)

    return CommandResult(user_prompt, answer, email_status, audio_bytes, audio_error)
