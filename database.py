import aiosqlite
import os
from datetime import datetime

DB_PATH = "clinic_bot.db"

async def init_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT,
                ai_mode INTEGER DEFAULT 1,
                scenario TEXT DEFAULT 'new_lead',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                sender TEXT,
                text TEXT,
                timestamp DATETIME
            )
        ''')
        await db.commit()

async def get_client_info(client_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ai_mode, name, scenario FROM clients WHERE telegram_id = ?", (client_id,)) as cursor:
            res = await cursor.fetchone()
            if res:
                return res
            await db.execute("INSERT INTO clients (telegram_id, name, ai_mode) VALUES (?, ?, 1)", (client_id, f"Клиент_{client_id}"))
            await db.commit()
            return 1, f"Клиент_{client_id}", "new_lead"

async def save_message(client_id, sender, text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (client_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
                         (client_id, sender, text, datetime.now()))
        await db.commit()

async def get_chat_history(client_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sender, text FROM messages WHERE client_id = ? ORDER BY id DESC LIMIT ?", (client_id, limit)) as cursor:
            return await cursor.fetchall()


async def get_logs(client_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT sender, text, timestamp FROM messages WHERE client_id = ? ORDER BY id DESC LIMIT 15",
                (client_id,)
        ) as cursor:
            history = await cursor.fetchall()

    if not history: return "История пуста"

    lines = []
    for h in reversed(history):
        role = "👤" if h[0] == "user" else "🤖"
        # Берем только часы и минуты из таймстампа
        time_str = h[2].split()[1][:5] if ' ' in str(h[2]) else ""
        lines.append(f"<code>[{time_str}]</code> {role}: {h[1]}")

    return "\n".join(lines)

async def set_ai_mode(client_id, mode: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clients SET ai_mode = ? WHERE telegram_id = ?", (mode, client_id))
        await db.commit()

async def update_scenario(client_id, scenario: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clients SET scenario = ? WHERE telegram_id = ?", (scenario, client_id))
        await db.commit()

async def update_client_name(client_id, new_name):
    """Обновляет техническое имя на реальное ФИО"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clients SET name = ? WHERE telegram_id = ?", (new_name, client_id))
        await db.commit()