# (출처: 6 - 미션 2. 기본 응답 / 6 - 미션 3. 미팅 요약 / 6 - 미션 6. 대화 결합 / 6 - 미션 7. 도구 실행)
import json
from openai import OpenAI
from email_utils import send_email, EMAIL_TOOLS

# 기본 개인비서 '에이블' 페르소나 (출처: 6 - 미션 3)
DEFAULT_SYS_ROLE = """당신은 '김 대리'의 개인 비서 '에이블'입니다.
김 대리의 요청에 친절하고 정중하게 한국어로 답변합니다.
담당 업무:
1. 미팅 내용을 읽고 핵심 내용을 간결하게 요약합니다.
2. 미팅에서 김 대리에게 배정된 업무가 있으면 업무 내용, 기한, 관련자를 상세히 정리합니다.
3. 배정된 업무가 없으면 "배정된 업무가 없습니다"라고 안내합니다.
4. 미팅 내용에 없는 사실은 지어내지 않습니다.
5. 이메일 발송 요청이 있을 경우에만 send_email 도구를 호출합니다."""

def build_user_prompt(user_query: str, meeting_text: str = "") -> str:
    """
    사용자 지시사항과 업로드된 미팅 파일 내용을 하나로 결합합니다. (출처: 6 - 미션 3, 4)
    """
    if meeting_text.strip():
        return f"{user_query}\n\n[미팅 내용]\n{meeting_text}"
    return user_query

def run_assistant(client: OpenAI, sys_role: str, conversation_history: list, current_prompt: str, default_recipient: str = ""):
    """
    LLM 호출 및 Function Calling(이메일 발송) 여부를 확인하고 처리합니다.
    반환값: (답변 텍스트, 이메일 발송 상태 메시지)
    """
    messages = [{"role": "system", "content": sys_role}]

    # 이전 대화 기록 누적 (출처: 2 - 5. 리스트 상태 관리)
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # 현재 턴의 최종 프롬프트 추가
    messages.append({"role": "user", "content": current_prompt})

    # LLM 1차 호출 (도구 호출 여부 확인)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=EMAIL_TOOLS,
        tool_choice="auto"
    )

    response_msg = response.choices[0].message
    email_status_msg = None

    # 이메일 도구 호출이 발생한 경우 (출처: 6 - 미션 7)
    if response_msg.tool_calls:
        for tool_call in response_msg.tool_calls:
            if tool_call.function.name == "send_email":
                args = json.loads(tool_call.function.arguments)
                target_to = args.get("to") or default_recipient

                # 메일 전송 실행 (출처: 6 - 미션 1)
                result = send_email(
                    to=target_to,
                    subject=args.get("subject", "미팅 요약 및 업무 보고"),
                    body=args.get("body", "")
                )

                if result.get("status") == "success":
                    email_status_msg = f"이메일 발송 완료: {target_to}"
                else:
                    email_status_msg = f"이메일 발송 실패: {result.get('error')}"

                # 도구 실행 결과를 LLM에 전달하여 최종 답변 도출
                messages.append(response_msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

                second_res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages
                )
                return second_res.choices[0].message.content, email_status_msg

    # 일반 응답 반환
    return response_msg.content, email_status_msg
