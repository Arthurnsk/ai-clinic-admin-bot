# AI Clinic Administrator Bot

Telegram bot that works as a virtual front-desk administrator for a medical clinic:
it answers patients, handles objections, books appointments and hands the conversation
to a human when needed. A second bot gives the clinic staff control over every chat.

The persona ("Svetlana") and the clinic are fictional; this is a demo MVP.

## Features

**Client bot**
- Natural conversation in Russian; LLM via Groq (Llama 3.3 70B) with Gemini as an option.
- **Voice messages**: speech-to-text with Whisper large-v3, spoken replies with
  ElevenLabs or free Edge TTS.
- Booking flow that ends with a **PDF confirmation ticket** (fpdf2, Cyrillic fonts).
- Scenarios with separate prompts: new lead, reactivation of past patients, NPS survey.
- Knows the clinic's local time to suggest realistic slots.

**Admin bot**
- Notification about every new patient request.
- Per-chat controls: switch AI on/off, change scenario, read the conversation log.
- The administrator can reply to a patient manually from the admin bot.

**`max-webchat/`** — an early variant of the same assistant for the MAX messenger:
FastAPI web chat and an admin page (Jinja2 templates).

## Stack

Python · aiogram 3 · Groq API (Llama 3.3, Whisper) · Google Gemini · ElevenLabs / Edge TTS ·
fpdf2 · SQLite (aiosqlite) · FastAPI (web chat)

## Run

```bash
cp .env.example .env        # bot tokens from @BotFather, your Telegram ID, API keys
pip install -r requirements.txt
python main.py
```

## Notes

MVP built with an AI-assisted workflow (Cursor, Claude Code). Fonts: DejaVu (see `fonts/`).

## Кратко

ИИ-администратор клиники в Telegram: отвечает пациентам текстом и голосом, записывает
на приём и присылает PDF-талон. Второй бот — для персонала: уведомления, включение и
выключение ИИ, смена сценария, ручные ответы. Персонаж и клиника вымышленные.

License: MIT
