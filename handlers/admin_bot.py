import os
from aiogram import Bot, types, F, Dispatcher
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import html_decoration as hd
from database import set_ai_mode, update_scenario, get_logs, get_client_info


def register_admin_handlers(dp: Dispatcher, client_bot: Bot):
    # Вспомогательная функция для генерации клавиатуры (синхронная, так как не делает запросов)
    def get_manage_kb(cid, ai_mode):
        kb = InlineKeyboardBuilder()
        # Проверяем режим (учитываем и 1, и "active")
        is_on = (ai_mode == 1 or ai_mode == "active")
        status = "🤖 ИИ: ВКЛ" if is_on else "👤 РЕЖИМ: РУЧНОЙ"

        kb.button(text=status, callback_data=f"toggle_ai_{cid}")
        kb.button(text="🎯 Сценарий", callback_data=f"scen_menu_{cid}")
        kb.button(text="📜 Логи", callback_data=f"logs_{cid}")
        kb.adjust(1, 2)
        return kb.as_markup()

    @dp.callback_query(F.data.startswith("back_"))
    async def back_to_main(cb: types.CallbackQuery):
        cid = int(cb.data.split("_")[-1])
        ai_mode, name, scenario = await get_client_info(cid)

        await cb.message.edit_text(
            f"⚙️ <b>Управление клиентом</b>\n"
            f"👤 Имя: {hd.quote(name)}\n"
            f"🆔 ID: <code>{cid}</code>\n"
            f"🎭 Сценарий: <code>{scenario}</code>",
            reply_markup=get_manage_kb(cid, ai_mode),
            parse_mode="HTML"
        )
        await cb.answer()

    @dp.callback_query(F.data.startswith("toggle_ai_"))
    async def toggle(cb: types.CallbackQuery):
        cid = int(cb.data.split("_")[-1])
        ai_mode, name, scenario = await get_client_info(cid)

        new_mode = 0 if (ai_mode == 1 or ai_mode == "active") else 1
        await set_ai_mode(cid, new_mode)

        await cb.message.edit_reply_markup(reply_markup=get_manage_kb(cid, new_mode))
        await cb.answer(f"Режим изменен")

    @dp.callback_query(F.data.startswith("scen_menu_"))
    async def scen_menu(cb: types.CallbackQuery):
        cid = cb.data.split("_")[-1]
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 Реактивация", callback_data=f"set_sc_{cid}_reactivation")
        kb.button(text="💎 Новый Лид", callback_data=f"set_sc_{cid}_new_lead")
        kb.button(text="⭐ NPS", callback_data=f"set_sc_{cid}_nps")
        kb.button(text="⬅️ Назад", callback_data=f"back_{cid}")
        kb.adjust(1)
        await cb.message.edit_text("🎯 <b>Выберите сценарий:</b>", reply_markup=kb.as_markup(), parse_mode="HTML")

    @dp.callback_query(F.data.startswith("set_sc_"))
    async def set_sc(cb: types.CallbackQuery):
        parts = cb.data.split("_")
        cid, sc = int(parts[2]), parts[3]
        await update_scenario(cid, sc)

        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Назад", callback_data=f"back_{cid}")
        await cb.message.edit_text(f"✅ Сценарий <b>{sc}</b> установлен.", reply_markup=kb.as_markup(),
                                   parse_mode="HTML")

    @dp.callback_query(F.data.startswith("logs_"))
    async def show_logs(cb: types.CallbackQuery):
        cid = int(cb.data.split("_")[-1])
        # Функция get_logs должна быть асинхронной!
        logs = await get_logs(cid)

        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Назад", callback_data=f"back_{cid}")

        # Ограничиваем длину логов для Telegram (макс 4096 символов)
        safe_logs = logs[-3500:] if len(logs) > 3500 else logs

        await cb.message.edit_text(
            f"📜 <b>История последних сообщений:</b>\n\n{safe_logs}",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

    @dp.message()
    async def admin_reply(msg: types.Message):
        """Ручной ответ админа. Срабатывает при ответе (Reply) на сообщение бота."""
        if msg.reply_to_message and "🆔 ID:" in msg.reply_to_message.text:
            try:
                raw_text = msg.reply_to_message.text
                # Извлекаем ID из текста сообщения
                cid_str = raw_text.split("ID:")[1].split("\n")[0].strip()
                cid = int(''.join(filter(str.isdigit, cid_str)))

                # Отправляем сообщение клиенту через КЛИЕНТСКОГО бота
                await client_bot.send_message(cid, msg.text)

                # При ручном ответе отключаем ИИ
                await set_ai_mode(cid, 0)

                await msg.answer(f"✅ Сообщение отправлено клиенту <code>{cid}</code>. ИИ переведен в ручной режим.",
                                 parse_mode="HTML")
            except Exception as e:
                await msg.answer(f"❌ Ошибка парсинга ID: {e}")