
import os
import base64
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client =

# 페이지 설정
st.set_page_config(텍스트 음성 변환 서비스)
st.title(글을 소리로)
st.write("텍스트를 작성하시면 음성으로 변환시켜드립니다.")

# 텍스트 입력
text = st.text_area(
    "읽을 텍스트를 입력하세요",
    "안녕하세요. OpenAI 텍스트 음성 변환 실습입니다."
)

# 버튼
if st.button(음성으로 변환하기):
    if text.strip() == "":
        st.warning(변환할 텍스트를 입력해주세요.)
    else:
        # TTS 생성
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=text
        )
        audio_bytes = audio_buffer.getvalue()

        # 음성 출력
        st.markdown("### 🔊 음성 재생")
        st.audio(speech.content, format="audio/mp3")
