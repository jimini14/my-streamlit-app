# (출처: 6 - 미션 1. 이메일 발송 / 6 - 미션 7. 도구 사용)
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText


def send_email(to: str, subject: str, body: str) -> dict:
    """Gmail SMTP를 이용해 이메일을 전송합니다. (한글 제목·본문 UTF-8 처리)"""
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not password:
        return {"status": "failed", "error": "GMAIL 설정 정보(계정/앱비밀번호)가 누락되었습니다."}

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = to
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, [to], msg.as_string())
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# OpenAI Function Calling에 전달할 도구 명세 (출처: 6 - 미션 7)
EMAIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "사용자가 요약이나 회의 내용을 이메일로 전송해 달라고 요구할 때 호출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "이메일 제목"},
                    "body": {"type": "string", "description": "이메일 본문 내용"},
                },
                "required": ["subject", "body"],
            },
        },
    }
]
