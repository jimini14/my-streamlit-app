"""한 번의 사용자 명령을 처리하는 절차입니다."""

from dataclasses import dataclass

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
