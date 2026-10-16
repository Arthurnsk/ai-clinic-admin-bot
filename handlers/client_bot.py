"""
====================================================================================================
INDUSTRIAL SYSTEM ORCHESTRATOR: CLIENT BOT HANDLER
====================================================================================================
Система: Медицинский ИИ-администратор "Светлана"
Версия: 7.6.0 (Enterprise Error-Free Edition)
Описание: Главный диспетчер логики. Исправлены синтаксические ошибки, расширена имитация действий.
====================================================================================================
"""

import os
import asyncio
import time
import logging
import re
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import html_decoration as hd
from pydub import AudioSegment

# Импорт внутренних подсистем проекта
from ai_engine import (
    stt_whisper, generate_ai_reply, tts_free,
    check_if_finished, generate_summary, create_pdf_summary,
    execute_fallback_text_generation
)
from database import get_client_info, save_message, get_chat_history, set_ai_mode, update_client_name
from scenarios import get_scenario_prompt

# Инструментарий для работы с временными зонами
from datetime import datetime
import pytz
from config import TIMEZONE

# Инициализация высокодетального регистратора событий
orchestrator_logger = logging.getLogger("CLIENT_ORCHESTRATOR")

async def handle_client_message(message_object: types.Message, bot_instance: Bot, admin_bot_instance: Bot, ADMIN_ID: int):
    """
    Центральный обработчик входящих коммуникаций.
    Обеспечивает жизненный цикл сообщения от приема до генерации PDF.
    """

    # Идентификация уникального ID пользователя
    user_telegram_uid = message_object.from_user.id

    # 1. СЛОЙ ДАННЫХ: ЗАГРУЗКА ПРОФИЛЯ КЛИЕНТА
    # Получаем режим ИИ, текущее имя в БД и активный сценарий
    ai_status_mode, current_name_in_crm, active_scenario_type = await get_client_info(user_telegram_uid)

    # 2. СЛОЙ ВРЕМЕНИ: СИНХРОНИЗАЦИЯ С ЛОКАЛЬНЫМ ЧАСОВЫМ ПОЯСОМ
    try:
        target_timezone_object = pytz.timezone(TIMEZONE)
        local_clinic_now = datetime.now(target_timezone_object)
        # Формирование расширенной временной метки для ИИ (важно для расчета дат)
        time_context_payload = local_clinic_now.strftime("%A, %d %B %Y, %H:%M")
    except Exception as timezone_sync_error:
        orchestrator_logger.error(f"⚠️ Критическая ошибка синхронизации времени: {timezone_sync_error}")
        time_context_payload = "Время в данный момент уточняется"

    # Обработка технического имени для промпта (защита от обращения 'Клиент_ID')
    if current_name_in_crm.startswith("Клиент_") or not current_name_in_crm:
        ai_safe_name_for_prompt = "неизвестно"
    else:
        ai_safe_name_for_prompt = current_name_in_crm

    orchestrator_logger.info(f"--- [INBOUND TRANSACTION] UID: {user_telegram_uid} | Name: {current_name_in_crm} ---")

    # 3. МУЛЬТИМОДАЛЬНЫЙ СЛОЙ: ОБРАБОТКА ВХОДЯЩЕГО КОНТЕНТА
    user_final_text_content = message_object.text
    input_is_voice_message_flag = bool(message_object.voice)

    if input_is_voice_message_flag:
        orchestrator_logger.info(f"--- [VOICE INTERCEPTED]: Начата расшифровка для UID {user_telegram_uid} ---")
        temp_audio_file_path = f"temp/v_{user_telegram_uid}_{message_object.voice.file_id}.ogg"

        # Пошаговая загрузка аудио-данных
        audio_metadata = await bot_instance.get_file(message_object.voice.file_id)
        await bot_instance.download_file(audio_metadata.file_path, temp_audio_file_path)

        # Конвертация через Whisper v3 (Groq)
        user_final_text_content = await stt_whisper(temp_audio_file_path)

        # Гарантированная очистка временного файла
        if os.path.exists(temp_audio_file_path):
            os.remove(temp_audio_file_path)

    # Санитизация пустого ввода
    if not user_final_text_content:
        user_final_text_content = "[Клиент отправил медиа-вложение или стикер]"

    # Фиксация входящего события в базе данных истории диалогов
    await save_message(user_telegram_uid, "user", user_final_text_content)

    # 4. АДМИНИСТРАТИВНЫЙ СЛОЙ: УВЕДОМЛЕНИЕ ОПЕРАТОРА
    # Исправленная логика определения активности ИИ
    is_ai_orchestrator_active = (ai_status_mode == 1 or ai_status_mode == "active" or ai_status_mode == "1")

    # Сборка интерактивного пульта управления
    admin_kb_builder_obj = InlineKeyboardBuilder()

    # Явное определение текста статуса для исключения ошибок синтаксиса
    if is_ai_orchestrator_active:
        ai_status_label = "🤖 ИИ: АКТИВЕН"
    else:
        ai_status_label = "👤 РЕЖИМ: РУЧНОЙ"

    admin_kb_builder_obj.button(text=ai_status_label, callback_data=f"toggle_ai_{user_telegram_uid}")
    admin_kb_builder_obj.button(text="🎯 СМЕНИТЬ СЦЕНАРИЙ", callback_data=f"scen_menu_{user_telegram_uid}")
    admin_kb_builder_obj.button(text="📜 ЛОГИ ДИАЛОГА", callback_data=f"logs_{user_telegram_uid}")
    admin_kb_builder_obj.adjust(1, 2)

    # Визуальное разграничение типов сообщений
    message_source_marker = "🎙 <b>ГОЛОСОВОЕ СООБЩЕНИЕ</b>" if input_is_voice_message_flag else "💬 <b>ТЕКСТ</b>"

    notification_card_body = (
        f"🔔 <b>НОВОЕ ОБРАЩЕНИЕ В КЛИНИКУ</b>\n\n"
        f"👤 <b>Клиент:</b> {hd.quote(current_name_in_db := current_name_in_crm)}\n"
        f"🆔 <b>ID:</b> <code>{user_telegram_uid}</code>\n"
        f"📍 <b>Тип:</b> {message_source_marker}\n"
        f"📝 <b>Текст:</b> <i>{hd.quote(user_final_text_content)}</i>"
    )

    await admin_bot_instance.send_message(
        ADMIN_ID,
        notification_card_body,
        reply_markup=admin_kb_builder_obj.as_markup(),
        parse_mode="HTML"
    )

    # 5. ИСПОЛНИТЕЛЬНЫЙ СЛОЙ: ГЕНЕРАЦИЯ ОТВЕТА СВЕТЛАНЫ
    if is_ai_orchestrator_active:
        # Инициация визуального статуса в Telegram (Typing)
        await bot_instance.send_chat_action(user_telegram_uid, "typing")

        # Получение расширенного контекста диалога (15 записей)
        raw_history_data_rows = await get_chat_history(user_telegram_uid, limit=5)
        formatted_context_history_list = [
            {"role": ("user" if row[0] == "user" else "assistant"), "content": row[1]}
            for row in reversed(raw_history_data_rows)
        ]

        # А. ГЕНЕРАЦИЯ ИНТЕЛЛЕКТУАЛЬНОГО ТЕКСТА
        final_reply_text_payload = await generate_ai_reply(
            get_scenario_prompt(active_scenario_type, {"name": ai_safe_name_for_prompt}, time_context_payload),
            formatted_context_history_list
        )

        # Б. КОМПЛЕКСНАЯ СИМУЛЯЦИЯ ЧЕЛОВЕЧЕСКОЙ ДЕЯТЕЛЬНОСТИ
        if input_is_voice_message_flag:
            # --- ПОДМОДУЛЬ: ИМИТАЦИЯ ЗАПИСИ ГОЛОСА ЛЮБОЙ ДЛИТЕЛЬНОСТИ ---
            v_output_file_disk_path = f"temp/ans_{user_telegram_uid}.mp3"

            # Генерация аудио-потока
            await tts_free(final_reply_text_payload, v_output_file_disk_path)

            try:
                # Физический анализ длины аудио через AudioSegment
                audio_stream_segment = AudioSegment.from_file(v_output_file_disk_path)
                calculated_duration_seconds = len(audio_stream_segment) / 1000.0
                # Время имитации = фактическая длина аудио + техническая задержка
                total_imitation_delay = calculated_duration_seconds + 1.6
                orchestrator_logger.info(f"--- [SIMULATION]: Длина аудио {calculated_duration_seconds:.1f} сек. Удержание статуса... ---")
            except Exception as audio_err:
                orchestrator_logger.warning(f"⚠️ Ошибка замера аудио: {audio_err}")
                total_imitation_delay = 9.0 # Резервное время

            # Цикл активного поддержания статуса 'record_voice' (обновление каждые 4 сек)
            imitation_start_timestamp = time.time()
            while time.time() - imitation_start_timestamp < total_imitation_delay:
                await bot_instance.send_chat_action(user_telegram_uid, "record_voice")
                await asyncio.sleep(4)

            # Доставка голосового ответа клиенту
            await message_object.answer_voice(voice=types.FSInputFile(v_output_file_disk_path))
            if os.path.exists(v_output_file_disk_path):
                os.remove(v_output_file_disk_path)
        else:
            # --- ПОДМОДУЛЬ: ИМИТАЦИЯ НАБОРА ТЕКСТА ---
            await bot_instance.send_chat_action(user_telegram_uid, "typing")
            # Расчет времени: 18 знаков в секунду, но не более 25 секунд общего ожидания
            typing_duration_seconds_limit = min(len(final_reply_text_payload) // 18, 25)
            orchestrator_logger.info(f"--- [SIMULATION]: Печать текста {typing_duration_seconds_limit} сек. ---")

            typing_start_timestamp = time.time()
            while time.time() - typing_start_timestamp < typing_duration_seconds_limit:
                await bot_instance.send_chat_action(user_telegram_uid, "typing")
                await asyncio.sleep(4)

            # Доставка текстового ответа клиенту
            await message_object.answer(final_reply_text_payload)

        # Регистрация ответа ИИ в базе данных
        await save_message(user_telegram_uid, "bot", final_reply_text_payload)
        # Отправка дубликата в админ-бот для мониторинга качества
        await admin_bot_instance.send_message(ADMIN_ID, f"🤖 <b>Светлана ответила:</b>\n{final_reply_text_payload}", parse_mode="HTML")

        # 6. СЛОЙ ЗАВЕРШЕНИЯ ТРАНЗАКЦИИ: АВТОМАТИЗАЦИЯ PDF И ФИО
        # Интеллектуальный аудит готовности к отправке подтверждающего документа
        if await check_if_finished(formatted_context_history_list, last_reply_text_content=final_reply_text_payload):
            orchestrator_logger.info("--- [PDF PIPELINE]: Инициализирован процесс формирования документа... ---")
        #АВТОИЗВЛЕЧЕНИЕ НОМЕРА ТЕЛЕФОНА
            history_blob = " ".join(
                [str(h['content']) for h in formatted_context_history_list]) + " " + user_final_text_content
            phone_match = re.search(
                r'(\+7|7|8)[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}|[0-9]{10,11}',
                history_blob)
            extracted_phone = phone_match.group(0) if phone_match else "не указан"
            # ---------------------------------------------

            # А. АВТОМАТИЧЕСКОЕ ИЗВЛЕЧЕНИЕ РЕАЛЬНОГО ФИО ИЗ КОНТЕКСТА ВСЕЙ ИСТОРИИ
            extraction_prompt_directive = (
                "Проанализируй диалог и вытащи ПОЛНОЕ ФИО пациента (Фамилия Имя Отчество). "
                "Пиши строго только ФИО. Если данных нет или это технический ID - напиши 'Клиент'."
            )
            extracted_real_fio_string = await execute_fallback_text_generation(
                extraction_prompt_directive,
                formatted_context_history_list + [{"role": "user", "content": user_final_text_content}]
            )
            extracted_real_fio_string = extracted_real_fio_string.strip().replace(".", "")

            # Синхронизация данных с CRM-базой (замена Клиент_ID на реальное имя)
            if len(extracted_real_fio_string.split()) >= 2:
                await update_client_name(user_telegram_uid, extracted_real_fio_string)
                current_name_in_db = extracted_real_fio_string # Обновление переменной для документа
                orchestrator_logger.info(f"--- [CRM SYNC]: Имя клиента обновлено на {extracted_real_fio_string} ---")

            # Б. ФОРМИРОВАНИЕ И ЭКСПОРТ ТАЛОНА
            await bot_instance.send_chat_action(user_telegram_uid, "upload_document")

            # Генерация текста выжимки по строгому шаблону
            pdf_summary_body_text_content = await generate_summary(
                formatted_context_history_list + [{"role": "assistant", "content": final_reply_text_payload}],
                time_context_payload
            )

            final_target_pdf_file_path = f"temp/order_{user_telegram_uid}.pdf"

            # Генерация PDF и отправка пользователю
            if create_pdf_summary(current_name_in_db, extracted_phone, pdf_summary_body_text_content, final_target_pdf_file_path):
                await message_object.answer_document(
                    document=types.FSInputFile(final_target_pdf_file_path),
                    caption=f"✅ {current_name_in_db}, я подготовила подтверждающий талон Вашей записи. До встречи в клинике!"
                )
                # Финальный аудит-лог для администратора
                await admin_bot_instance.send_message(ADMIN_ID, f"💰 СДЕЛКА ЗАКРЫТА\nПациент: {current_name_in_db}\nДокументация доставлена успешно.")

                # Удаление временного файла из системы
                if os.path.exists(final_target_pdf_file_path):
                    os.remove(final_target_pdf_file_path)
            else:
                orchestrator_logger.error("--- [PDF ERROR]: Сбой формирования файла в модуле FPDF. ---")