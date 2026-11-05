# (출처: 6 - 미션 4. STT / 6 - 미션 5. TTS / 7 - 2. 음성 처리 로직)
from openai import OpenAI

# 1순위 모델이 실패하면 다음 모델로 다시 시도합니다.
STT_MODELS = ("gpt-4o-mini-transcribe", "whisper-1")


def _audio_bytes(audio_file) -> bytes:
    """st.audio_input 결과(UploadedFile), 파일 객체, bytes 모두 bytes로 바꿉니다."""
    if isinstance(audio_file, (bytes, bytearray)):
        return bytes(audio_file)
    if hasattr(audio_file, "getvalue"):
        return audio_file.getvalue()
    if hasattr(audio_file, "seek"):
        audio_file.seek(0)
    return audio_file.read()


def _file_tuple(data: bytes):
    """녹음 파일의 실제 형식에 맞는 이름과 MIME 타입을 붙입니다."""
    if data[:4] == b"RIFF":
        return ("audio.wav", data, "audio/wav")
    if data[:4] == b"\x1aE\xdf\xa3":
        return ("audio.webm", data, "audio/webm")
    if data[:4] == b"OggS":
        return ("audio.ogg", data, "audio/ogg")
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
        return ("audio.mp3", data, "audio/mpeg")
    if data[4:8] == b"ftyp":
        return ("audio.m4a", data, "audio/mp4")
    return ("audio.wav", data, "audio/wav")


def transcribe_audio(client: OpenAI, audio_file) -> str:
    """
    사용자의 음성 입력(audio_input 또는 오디오 파일)을 텍스트로 변환(STT)합니다.
    """
    data = _audio_bytes(audio_file)
    if not data or len(data) < 1000:
        raise ValueError("녹음된 소리가 너무 짧습니다. 다시 녹음해 주세요.")
    last_error = None
    for model in STT_MODELS:
        try:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=_file_tuple(data),
                language="ko",   # 한국어 인식 정확도 향상
            )
            return (transcript.text or "").strip()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"음성 인식에 실패했습니다: {last_error}")


def text_to_speech(client: OpenAI, text: str) -> bytes:
    """
    LLM의 텍스트 응답을 음성 바이너리 데이터(MP3)로 변환(TTS)합니다.
    """
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text[:1000]  # 브라우저 재생 지연 방지를 위해 최대 1000자 제한
    )
    return response.content
