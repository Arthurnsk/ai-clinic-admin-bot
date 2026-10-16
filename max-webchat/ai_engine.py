import edge_tts
import os
from groq import Groq
from config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)

async def stt_whisper(file_path):
    """Голос в текст"""
    with open(file_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            response_format="text",
        )
    return transcription

async def generate_ai_reply(prompt, user_text):
    """Генерация ответа через Llama 3.3"""
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.7,
    )
    return completion.choices[0].message.content

async def tts_free(text, output_path):
    """Текст в голос (Microsoft Edge)"""
    # Выбрали приятный женский голос 'Svetlana'
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save(output_path)