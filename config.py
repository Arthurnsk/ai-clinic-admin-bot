import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID")) # Ваш ID в Telegram
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Новые настройки
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

TIMEZONE = os.getenv("TIMEZONE", "Asia/Novosibirsk")