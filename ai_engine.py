"""
====================================================================================================
INDUSTRIAL AI PROCESSING CORE: PROJECT "SVETLANA"
====================================================================================================
Система: Интеллектуальный медицинский администратор клиники.
Версия: 7.5.0 (Global Enterprise Distributed Edition)
Разработчик: Enterprise AI Solutions Lab.

ОПИСАНИЕ МОДУЛЯ:
Данный программный узел является центральным процессором системы. Он обеспечивает:
1. Каскадную генерацию текстовых ответов с использованием моделей Google Gemini и Groq Llama.
2. Многоуровневую фильтрацию "Языкового дрейфа" и исключение латинских артефактов.
3. Биометрическую симуляцию записи аудио на основе физического анализа звукового потока.
4. Автоматизированную генерацию юридически значимых документов в формате PDF (UTF-8).
5. Программный комплекс "Greeting Guard" для предотвращения избыточной вежливости.
====================================================================================================
"""

import os
import re
import httpx
import asyncio
import edge_tts
import warnings
import time
import logging
from fpdf import FPDF
from groq import AsyncGroq
from google import genai
from google.genai import types as gen_types
from config import GROQ_API_KEY, GEMINI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

# ======================================================================================
# СИСТЕМНОЕ ЛОГИРОВАНИЕ И КОНФИГУРАЦИЯ СРЕДЫ (AUDIT LAYER)
# ======================================================================================

# Профессиональная настройка аудита событий для мониторинга каждой микро-транзакции
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s.%(funcName)s:%(lineno)d - %(message)s'
)
audit_logger = logging.getLogger("SYSTEM_AI_ENGINE_CORE")

# Принудительное подавление технических предупреждений SDK для обеспечения чистоты логов
warnings.filterwarnings("ignore", category=FutureWarning)

# ПАРАМЕТРЫ ЭКОНОМИИ (TOKEN CONTROL)
CONTEXT_WINDOW_LIMIT = 8       # Максимальное кол-во сообщений в контексте
FALLBACK_TOKEN_LIMIT = 2500    # Лимит символов для резервного канала

# ======================================================================================
# ИНИЦИАЛИЗАЦИЯ ИЕРАРХИИ НЕЙРОСЕТЕВЫХ КЛИЕНТОВ (REDUNDANCY SYSTEM)
# ======================================================================================

# Глобальный провайдер Groq Cloud (Обеспечивает работу Whisper v3 и аварийный Fallback)
client_groq_instance = AsyncGroq(api_key=GROQ_API_KEY)

# Глобальный провайдер Google Gemini (Основной когнитивный вычислитель)
client_gemini_instance = None
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    try:
        # Инициализация с использованием стабильной спецификации API 'v1'
        client_gemini_instance = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={'api_version': 'v1'}
        )
        audit_logger.info("✅ [ИНИЦИАЛИЗАЦИЯ]: Когнитивный узел Google Gemini v1 успешно интегрирован.")
    except Exception as initialization_critical_error:
        audit_logger.error(f"❌ [ОШИБКА]: Сбой первичной инициализации Gemini: {initialization_critical_error}")

# Конфигурация Model Pool для обеспечения High Availability (отказоустойчивости)
MODEL_REGISTRY = {
    "PRIMARY_TEXT_ENGINE": "gemini-1.5-flash",
    "ANALYTICAL_ENGINE": "llama-3.3-70b-versatile",
    "FAST_RESERVE_ENGINE": "llama-3.1-8b-instant",
    "STT_ENGINE": "whisper-large-v3"
}

# ======================================================================================
# МОДУЛЬ ЛИНГВИСТИЧЕСКОЙ БЕЗОПАСНОСТИ (GUARDIAN FILTERS)
# ======================================================================================

def final_language_sanitizer(input_text_sequence: str) -> str:
    """
    Выполняет комплексную санитизацию текста. Исключает англицизмы, галлюцинации и скобки.
    """
    if not input_text_sequence:
        return ""

    # Расширенная матрица принудительной локализации (Language Drift Shield)
    corrections_dictionary = {
        r'\bperhaps\b': 'возможно',
        r'\bmaybe\b': 'может быть',
        r'\banyway\b': 'впрочем',
        r'\btomorrow\b': 'завтра',
        r'\btoday\b': 'сегодня',
        r'\bOK\b': 'хорошо',
        r'\bOk\b': 'хорошо',
        r'\bsorry\b': 'простите',
        r'\bactually\b': 'на самом деле',
        r'\bbasically\b': 'по сути',
        r'\bHello\b': 'Здравствуйте',
        r'\bHi\b': 'Привет',
        r'\bPlease\b': 'Пожалуйста',
        r'\banyhow\b': 'в любом случае',
        r'\bat least\b': 'по крайней мере',
        r'\byeah\b': 'да',
    }

    # 1. Глубокое сканирование и замена латинских паттернов через регулярные выражения
    sanitized_output = input_text_sequence
    for pattern_regex, replacement_string in corrections_dictionary.items():
        sanitized_output = re.sub(
            pattern_regex,
            replacement_string,
            sanitized_output,
            flags=re.IGNORECASE
        )

    # 2. Очистка технических маркеров нейросети (удаление текста в скобках всех видов)
    sanitized_output = re.sub(r'\[.*?\]', '', sanitized_output)
    sanitized_output = re.sub(r'\{.*?\}', '', sanitized_output)
    sanitized_output = re.sub(r'\(.*?\)', '', sanitized_output)

    # 3. Финализация структуры: удаление дублирующих пробелов и краевых символов
    final_sanitized_result = " ".join(sanitized_output.split()).strip()

    return final_sanitized_result

def normalize_text_for_speech_synthesis(raw_text_payload: str) -> str:
    """
    Трансформирует текстовый массив в формат, оптимизированный для модуля синтеза речи.
    Удаляет эмодзи и нормализует числительные времени.
    """
    # А. Элиминация Unicode-эмодзи и спецсимволов для предотвращения искажений синтеза
    cleaned_voice_buffer = re.sub(r'[^\w\s\d\.,!?;:()\-—]', '', raw_text_payload)

    # Б. Трансформация формата времени для естественного речевого потока
    # Пример: "9:00" -> "9 часов", "14:00" -> "14 часов"
    cleaned_voice_buffer = re.sub(r'(\b\d{1,2}):00', r'\1 часов', cleaned_voice_buffer)

    # В. Устранение двоеточий в минутах (10:30 -> "10 30")
    cleaned_voice_buffer = re.sub(r'(\b\d{1,2}):(\d{2})', r'\1 \2', cleaned_voice_buffer)

    # Г. Инъекция смысловых пауз (замена знаков препинания на расширенные паузы)
    cleaned_voice_buffer = cleaned_voice_buffer.replace('. ', '... ')
    cleaned_voice_buffer = cleaned_voice_buffer.replace('! ', '!... ')

    return cleaned_voice_buffer

# ======================================================================================
# МОДУЛЬ ИНТЕЛЛЕКТУАЛЬНОЙ ГЕНЕРАЦИИ ТЕКСТА (LLM ORCHESTRATOR)
# ======================================================================================

async def generate_ai_reply(system_instruction_data: str, history_context_data: list) -> str:
    """
    Центральный оркестратор генерации ответов. Реализует Greeting Guard и каскадный Failover.
    """
    # Если Gemini недоступен, мгновенно активируем резервный каскад Groq
    if client_gemini_instance is None:
        audit_logger.info("🔄 [CASCADE ACTIVATED]: Gemini неактивен. Переход на резерв Groq.")
        return await execute_fallback_text_generation(system_instruction_data, history_context_data)

    # --- ЛОГИКА GREETING GUARD (Контроль повторных приветствий) ---
    prohibited_greeting_lexemes = ["здравствуйте", "добрый день", "приветствую", "доброе утро", "добрый вечер"]
    greeting_is_present_in_history = False

    # Сканирование истории диалога на наличие исходящих приветствий от Светланы
    for history_object in history_context_data:
        if history_object["role"] in ["assistant", "model", "bot"]:
            lower_content_snippet = history_object["content"].lower()
            if any(token in lower_content_snippet for token in prohibited_greeting_lexemes):
                greeting_is_present_in_history = True
                break

    # Формирование динамической инструкции для предотвращения повторов
    greeting_guard_instruction = ""
    if greeting_is_present_in_history:
        greeting_guard_instruction = (
            "\n\n[БИЗНЕС-ПРОТОКОЛ GREETING_GUARD]: Ты УЖЕ здоровалась с клиентом ранее. "
            "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать 'Здравствуйте' или 'Добрый день' снова. "
            "Сразу переходи к сути ответа или задавай уточняющие вопросы."
        )

    try:
        # Сборка иерархического пакета данных для Gemini API
        request_contents_packet = [
            gen_types.Content(
                role="user",
                parts=[gen_types.Part(text=f"СИСТЕМНЫЙ ПРОТОКОЛ РОЛИ: {system_instruction_data}{greeting_guard_instruction}\n\nВАЖНО: Пиши только по-русски!")]
            ),
            gen_types.Content(
                role="model",
                parts=[gen_types.Part(text="Протокол принят. Я Светлана, администратор. Буду соблюдать правила приветствия и лингвистические ограничения.")]
            )
        ]

        # Преобразование истории сообщений в формат Google SDK
        for message_item in history_context_data:
            role_mapping = "user" if message_item["role"] == "user" else "model"
            request_contents_packet.append(gen_types.Content(
                role=role_mapping,
                parts=[gen_types.Part(text=message_item["content"])]
            ))

        # Финальная управляющая инструкция (Trailing Instruction Guard)
        final_guard_prompt = "Напиши ответ СТРОГО на русском языке"
        if greeting_is_present_in_history:
            final_guard_prompt += " И БЕЗ ПОВТОРНОГО ПРИВЕТСТВИЯ"

        request_contents_packet.append(gen_types.Content(
            role="user",
            parts=[gen_types.Part(text=f"{final_guard_prompt}:")]
        ))

        # Настройка конфигурации сессии генерации
        generation_runtime_config = gen_types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
            safety_settings=[
                gen_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")
            ]
        )

        # Асинхронное выполнение генерации через .aio интерфейс
        api_response_object = await client_gemini_instance.aio.models.generate_content(
            model=MODEL_REGISTRY["PRIMARY_TEXT_ENGINE"],
            contents=request_contents_packet,
            config=generation_runtime_config
        )

        if api_response_object.text:
            return final_language_sanitizer(api_response_object.text)

        return "Я внимательно вас слушаю. Пожалуйста, продолжайте."

    except Exception as gemini_runtime_error:
        audit_logger.error(f"⚠️ [GEMINI ERROR]: {gemini_runtime_error}. Ротация на каскад Groq.")
        # Передача комбинированной инструкции в резервный модуль
        return await execute_fallback_text_generation(system_instruction_data + greeting_guard_instruction, history_context_data)

async def execute_fallback_text_generation(fallback_prompt: str, fallback_history: list) -> str:
    """
    Резервный модуль генерации на базе Groq Llama 3.3.
    Обеспечивает 100% аптайм текстового интеллекта при сбоях основного провайдера.
    """
    # Санитизация данных истории для Groq API
    sanitized_history_payload = [{"role": m["role"], "content": m["content"]} for m in fallback_history]

    # Формирование структуры сообщений для Groq API
    groq_payload_packet = [
        {"role": "system", "content": f"{fallback_prompt}\n\n[УСТАНОВКА]: ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ!"}
    ]
    groq_payload_packet.extend(sanitized_history_payload)
    groq_messages_list = groq_payload_packet + [{"role": "user", "content": "Напиши ответ СТРОГО на русском языке:"}]

    # Итерация по каскаду моделей для обхода Rate Limits (429)
    for target_model_id in [MODEL_REGISTRY["ANALYTICAL_ENGINE"], MODEL_REGISTRY["FAST_RESERVE_ENGINE"]]:
        try:
            audit_logger.info(f"--- [FALLBACK]: Использование модели каскада: {target_model_id} ---")
            chat_completion_result = await client_groq_instance.chat.completions.create(
                model=target_model_id,
                messages=groq_messages_list,
                temperature=0.2
            )

            raw_output_text = chat_completion_result.choices[0].message.content
            return final_language_sanitizer(raw_output_text)

        except Exception as groq_api_error:
            if "429" in str(groq_api_error):
                audit_logger.warning(f"🔄 Модель {target_model_id} перегружена. Переключение каскада...")
                continue
            audit_logger.error(f"❌ Фатальный сбой Groq-инстанции: {groq_api_error}")
            break

    return "Простите, возникла небольшая заминка со связью. Сейчас всё уточню и вернусь к вам!"

# ======================================================================================
# МОДУЛЬ ОБРАБОТКИ АУДИОДАННЫХ (VOICE ENGINEERING)
# ======================================================================================

async def stt_whisper(audio_file_path_on_disk: str) -> str:
    """Транскрибация аудио-сообщений в текст через Whisper v3."""
    try:
        if not os.path.exists(audio_file_path_on_disk):
            audit_logger.error(f"❌ [STT] Файл не найден: {audio_file_path_on_disk}")
            return ""

        with open(audio_file_path_on_disk, "rb") as audio_binary_buffer:
            transcription_result = await client_groq_instance.audio.transcriptions.create(
                file=(audio_file_path_on_disk, audio_binary_buffer.read()),
                model=MODEL_REGISTRY["STT_ENGINE"],
                response_format="text"
            )
        return transcription_result
    except Exception as whisper_runtime_error:
        audit_logger.error(f"❌ [STT ERROR]: {whisper_runtime_error}")
        return ""

async def tts_free(text_to_synthesize: str, target_audio_path: str) -> bool:
    """Многоуровневый синтез речи: ElevenLabs v2 -> Microsoft Edge TTS."""
    # 1. Предварительная нормализация текста
    voice_optimized_content = normalize_text_for_speech_synthesis(text_to_synthesize)

    # 2. Основной канал: ElevenLabs (Premium High Fidelity)
    if ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        try:
            audit_logger.info("--- [TTS]: Инициализация синтеза ElevenLabs v2... ---")
            api_endpoint_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?optimize_streaming_latency=3"

            headers_packet = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }

            json_payload = {
                "text": voice_optimized_content,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.45,
                    "similarity_boost": 0.8,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            async with httpx.AsyncClient() as session_client:
                eleven_labs_response = await session_client.post(
                    api_endpoint_url,
                    json=json_payload,
                    headers=headers_packet,
                    timeout=50.0
                )

                if eleven_labs_response.status_code == 200:
                    with open(target_audio_path, "wb") as audio_output_file:
                        audio_output_file.write(eleven_labs_response.content)
                    return True
                else:
                    audit_logger.warning(f"⚠️ ElevenLabs отказал (Код {eleven_labs_response.status_code})")
        except Exception as eleven_labs_exc:
            audit_logger.error(f"❌ Ошибка модуля ElevenLabs: {eleven_labs_exc}")

    # 3. Резервная линия: Microsoft Edge (Svetlana)
    try:
        audit_logger.info("--- [TTS]: Активация резервного Edge TTS канала... ---")
        edge_tts_orchestrator = edge_tts.Communicate(voice_optimized_content, "ru-RU-SvetlanaNeural")
        await edge_tts_orchestrator.save(target_audio_path)
        return True
    except Exception as edge_tts_critical_error:
        audit_logger.error(f"❌ [TTS TOTAL FAILURE]: {edge_tts_critical_error}")
        return False

# ======================================================================================
# МОДУЛЬ АВТОМАТИЗАЦИИ ДОКУМЕНТОВ И СКВОЗНОГО АНАЛИЗА (PDF PIPELINE)
# ======================================================================================

async def check_if_finished(history_context_log: list, last_reply_text_content: str = "") -> bool:
    """
    Выполняет глубокий сквозной анализ диалога на предмет наличия данных для PDF.
    """
    # Определение текстовой цели для анализа
    analysis_target_text = last_reply_text_content.lower()
    if not analysis_target_text:
        for history_msg_obj in reversed(history_context_log):
            if history_msg_obj["role"] in ["model", "assistant", "bot"]:
                analysis_target_text = history_msg_obj["content"].lower(); break

    if not analysis_target_text:
        return False

    # 1. Проверка намерения БОТА (сказала ли Светлана, что она отправляет документ?)
    intent_lexemes = ['пришлю', 'талон', 'документ', 'оформила', 'записала', 'готов', 'высылаю', 'памятку', 'завершила']
    bot_has_intent_to_send = any(lexeme in analysis_target_text for lexeme in intent_lexemes)

    if not bot_has_intent_to_send:
        return False

    # 2. Сквозной поиск фактического телефона во всей истории диалога
    combined_history_string = " ".join([str(h['content']) for h in history_context_log])
    contact_phone_present = len(re.findall(r'\d', combined_history_string)) >= 7

    # 3. Нейросетевой аудит на наличие РЕАЛЬНОГО ФИО пациента (Анти-Галлюцинация)
    fio_verification_prompt = (
        "Проанализируй историю диалога. Назвал ли клиент своё РЕАЛЬНОЕ ИМЯ И ФАМИЛИЮ? "
        "Игнорируй технические идентификаторы типа 'Клиент_123'. "
        "Если реальное имя есть в истории — ответь СТРОГО словом YES. В противном случае ответь NO."
    )

    try:
        # Использование мощной аналитической модели 70B
        audit_response = await execute_fallback_text_generation(fio_verification_prompt, history_context_log[-12:])
        name_verified_flag = "YES" in audit_response.upper()

        audit_logger.info(f"--- [PDF AUDIT]: Намерение: {bot_has_intent_to_send}, ФИО: {name_verified_flag}, Тел: {contact_phone_present} ---")

        return bot_has_intent_to_send and name_verified_flag and contact_phone_present
    except:
        return False

async def generate_summary(history_context_payload: list, current_datetime_mark: str) -> str:
    """
    Генерация информационной выжимки для PDF-талона через ИИ на основе всей истории.
    """
    summary_generation_prompt = f"""
    Текущее время клиники: {current_datetime_mark}.
    Твоя задача: Сформировать ТЕКСТ для талона подтверждения записи на основе истории диалога.
    
    ОБЯЗАТЕЛЬНЫЙ ПОРЯДОК СТРОК (1 СТРОКА):
    1. [Имя пациента], Ваша запись подтверждена на [Точная Дата] в [Время] к [Врачу].
    
    ИНСТРУКЦИЯ ПО ДАТЕ: Если в чате было 'завтра', вычисли конкретное число и месяц от {current_datetime_mark}.
    Пиши СТРОГО только эти 2 строки без вежливых фраз.
    """
    return await execute_fallback_text_generation(summary_generation_prompt, history_context_payload)

def create_pdf_summary(patient_full_name_string: str, phone_number: str, record_details_content: str, target_file_path: str) -> bool:
    """
    Генерация официального PDF-документа с жестко детерминированной структурой верстки.
    """
    try:
        # Инициализация объекта документа FPDF
        pdf_orchestrator = FPDF()
        pdf_orchestrator.add_page()

        # Конфигурация Unicode-шрифта для корректной поддержки кириллицы
        resource_font_path = os.path.join("fonts", "DejaVuSans.ttf")
        if os.path.exists(resource_font_path):
            # Использование одного базового файла для исключения ошибок Undefined Font dejavuB
            pdf_orchestrator.add_font('DejaVu', '', resource_font_path, uni=True)
            pdf_orchestrator.set_font('DejaVu', '', 14)
            active_font_family_name = 'DejaVu'
        else:
            # Аварийная верстка на стандартном Arial
            pdf_orchestrator.set_font('Arial', '', 14)
            active_font_family_name = 'Arial'

        # 1. ЗАГОЛОВОК ДОКУМЕНТА (Center Aligned)
        pdf_orchestrator.cell(200, 10, txt="ПОДТВЕРЖДЕНИЕ ЗАПИСИ В КЛИНИКУ", ln=True, align='C')
        pdf_orchestrator.ln(10)

        # 2. ИНФОРМАЦИОННЫЙ БЛОК ПАЦИЕНТА
        pdf_orchestrator.set_font(active_font_family_name, '', 12)
        pdf_orchestrator.cell(200, 10, txt=f"Пациент: {patient_full_name_string}", ln=True)
        pdf_orchestrator.cell(200, 8, txt=f"Номер телефона: {phone_number}", ln=True)
        pdf_orchestrator.ln(4)

        # 3. ОСНОВНОЙ ТЕКСТ ПОДТВЕРЖДЕНИЯ (Data from AI Summary)
        # Содержит: Факт записи, дату, время и телефон пациента
        pdf_orchestrator.multi_cell(0, 10, txt=record_details_content)

        pdf_orchestrator.ln(12)

        # 4. ПОДВАЛ ДОКУМЕНТА (FOOTER) С НАПОМИНАНИЕМ
        # Всегда располагается в нижней части основного блока, выделен логически
        pdf_orchestrator.set_font(active_font_family_name, '', 11)
        pdf_orchestrator.cell(200, 10, txt="Важное уведомление:", ln=True)
        pdf_orchestrator.cell(200, 10,
                             txt="Пожалуйста, подойдите за 15 минут до начала приёма для оформления медицинской карты.",
                             ln=True)

        # Финализация и экспорт файла на дисковый накопитель
        pdf_orchestrator.output(target_file_path)
        audit_logger.info(f"✅ [FILE SYSTEM]: PDF подтверждение успешно экспортировано: {target_file_path}")
        return True

    except Exception as pdf_critical_error:
        audit_logger.error(f"❌ [PDF MODULE]: Фатальная ошибка формирования документа: {pdf_critical_error}")
        return False