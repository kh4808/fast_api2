# app/chat/service/tts_service.py
import os
from groq import Groq
from pydub import AudioSegment
from io import BytesIO
import base64

client = Groq(api_key=os.environ["GROQ_API_KEY"])

voice_map = {
    "Host": "Fritz-PlayAI",   # 낮고 차분한 남성
    "Guest": "Mason-PlayAI",  # 밝고 친근한 여성
}

def generate_tts_audio(script: str) -> str:
    """
    Host/Guest 구분하여 Groq TTS로 오디오 합성 후 base64로 반환
    """
    if not script.strip():
        raise ValueError("[WARNING] Empty script. Nothing to synthesize.")

    lines = [line.strip() for line in script.split("\n") if line.strip()]
    segments = []

    for i, line in enumerate(lines):
        if ":" not in line:
            continue

        speaker, text = line.split(":", 1)
        speaker = speaker.strip()
        text = text.strip()
        voice = voice_map.get(speaker, "Fritz-PlayAI")

        print(f"[TTS] {speaker}: {text[:40]}... → {voice}")

        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            input=text,
            response_format="wav"
        )

        seg = AudioSegment.from_file(BytesIO(response.read()), format="wav")
        segments.append(seg + AudioSegment.silent(duration=250))

    if not segments:
        raise ValueError("[WARNING] No valid lines for TTS conversion")

    final_audio = AudioSegment.silent(duration=500)
    for seg in segments:
        final_audio += seg

    # WAV를 메모리에 바로 저장 (ffmpeg 불필요)
    buffer = BytesIO()
    final_audio.export(buffer, format="wav")

    audio_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    print("[OK] Generated podcast audio (WAV base64)")
    return audio_base64
