# (출처: 6 - 미션 4. STT / 6 - 미션 5. TTS / 7 - 2. 음성 처리 로직)
from openai import OpenAI

def transcribe_audio(client: OpenAI, audio_file) -> str:
    """
    사용자의 음성 입력(audio_input 또는 오디오 파일)을 텍스트로 변환(STT)합니다.
    """
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.wav", audio_file, "audio/wav")
    )
    return transcript.text

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
