import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import aiohttp

from database import init_db, get_client_info, set_ai_mode, update_scenario, save_message, get_chat_history
from ai_engine import generate_ai_reply, stt_whisper, tts_free
from scenarios import get_scenario_prompt

app = FastAPI()
templates = Jinja2Templates(directory="templates")
init_db()

# Конфигурация MAX берётся из переменных окружения
MAX_API_URL = os.getenv("MAX_API_URL", "https://api.max-messenger.ru/v1")
MAX_TOKEN = os.getenv("MAX_TOKEN", "")


# --- ЛОГИКА МЕССЕНДЖЕРА MAX ---

async def send_to_max(client_id, text):
    """Отправка сообщения обратно в MAX"""
    url = f"{MAX_API_URL}/messages/send"
    headers = {"Authorization": f"Bearer {MAX_TOKEN}"}
    payload = {"to": client_id, "text": text}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload, headers=headers)
    save_message(client_id, "bot", text)


@app.post("/webhook/max")
async def max_webhook(request: Request):
    data = await request.json()
    client_id = data.get("from_id")
    client_name = data.get("from_name", "Клиент")
    text = data.get("text", "")

    save_message(client_id, "client", text)
    ai_mode, _, scenario = get_client_info(client_id)

    if ai_mode == 1:
        prompt = get_scenario_prompt(scenario, {"name": client_name})
        ai_reply = await generate_ai_reply(prompt, text)
        await send_to_max(client_id, ai_reply)

    return {"status": "ok"}


# --- ВЕБ-АДМИНКА (Замена Telegram-боту) ---

@app.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Главная страница со списком чатов"""
    conn = sqlite3.connect('max_bot.db')
    clients = conn.execute("SELECT id, name, ai_mode, scenario FROM clients").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "clients": clients})


@app.get("/chat/{client_id}")
async def view_chat(client_id: str, request: Request):
    """Просмотр конкретного чата"""
    history = get_chat_history(client_id)
    ai_mode, name, scenario = get_client_info(client_id)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "client_id": client_id,
        "history": reversed(history),
        "ai_mode": ai_mode,
        "scenario": scenario
    })


@app.post("/action/{client_id}")
async def admin_action(client_id: str, action: str = Form(...), value: str = Form(None)):
    """Действия: переключить ИИ, сменить сценарий, отправить сообщение"""
    if action == "toggle_ai":
        set_ai_mode(client_id, int(value))
    elif action == "set_scenario":
        update_scenario(client_id, value)
    elif action == "send_manual":
        await send_to_max(client_id, value)
        set_ai_mode(client_id, 0)  # Выключаем ИИ при ручном ответе

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)