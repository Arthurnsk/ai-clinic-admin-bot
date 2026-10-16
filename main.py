import asyncio
import os
import logging
import shutil
from aiogram import Bot, Dispatcher, types
from config import CLIENT_BOT_TOKEN, ADMIN_BOT_TOKEN, ADMIN_ID
from handlers.client_bot import handle_client_message
from handlers.admin_bot import register_admin_handlers
from database import init_database

# Настройка логирования, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)


async def main():
    # Очистка папки temp при каждом запуске
    if os.path.exists('temp'):
        shutil.rmtree('temp')
    os.makedirs('temp')

    # 2. Инициализируем базу данных (ОБЯЗАТЕЛЬНО через await)
    await init_database()
    print("✅ База данных готова.")

    # 3. Инициализация ботов и диспетчеров
    client_bot = Bot(token=CLIENT_BOT_TOKEN)
    admin_bot = Bot(token=ADMIN_BOT_TOKEN)

    dp_client = Dispatcher()
    dp_admin = Dispatcher()

    # Регистрация обработчика клиентского бота
    @dp_client.message()
    async def client_handler(msg: types.Message):
        await handle_client_message(msg, client_bot, admin_bot, ADMIN_ID)

    # Регистрация обработчиков админ-бота
    register_admin_handlers(dp_admin, client_bot)

    print("🚀 Система запущена!")
    print("Напишите что-нибудь клиентскому боту для начала проверки.")

    # 4. Запуск обоих ботов в параллельном режиме
    try:
        await asyncio.gather(
            dp_client.start_polling(client_bot),
            dp_admin.start_polling(admin_bot)
        )
    finally:
        await client_bot.session.close()
        await admin_bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🆘 Система остановлена пользователем")