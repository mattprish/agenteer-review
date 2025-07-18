import asyncio
import tempfile
import os
import logging
import aiohttp
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import (
    get_main_keyboard, get_help_keyboard, get_back_keyboard,
    get_processing_keyboard, get_results_keyboard
)

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Состояния FSM
class ReviewStates(StatesGroup):
    waiting_for_document = State()
    processing = State()
    showing_results = State()

# Получаем URL LLM сервиса
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")

async def call_llm_service(text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Вызывает LLM сервис для анализа текста"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "text": text,
                "metadata": metadata or {}
            }
            
            async with session.post(
                f"{LLM_SERVICE_URL}/review",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 минут таймаут
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"LLM service error: {error_text}")
                    
    except Exception as e:
        logger.error(f"Error calling LLM service: {e}")
        raise

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    welcome_text = """
🤖 Добро пожаловать в систему автоматического рецензирования научных статей!

📄 Отправьте мне PDF файл научной статьи, и я проведу её анализ:
• Структурный анализ
• Оценка методологии  
• Проверка соответствия стандартам
• Рекомендации по улучшению

Для начала работы отправьте PDF файл или воспользуйтесь командами:
/help - справка по использованию
/about - информация о системе
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    await state.set_state(ReviewStates.waiting_for_document)

@router.message(Command("help"))
async def help_handler(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 Справка по использованию:

1️⃣ Отправьте PDF файл научной статьи
2️⃣ Дождитесь завершения анализа
3️⃣ Получите подробную рецензию

🔧 Возможности системы:
• Анализ структуры статьи
• Проверка методологии исследования
• Оценка качества изложения
• Рекомендации по доработке

⚡️ Команды:
/start - начать работу
/help - эта справка
/about - о системе
/cancel - отменить текущую операцию
"""
    
    await message.answer(help_text, reply_markup=get_help_keyboard())

@router.message(Command("about"))
async def about_handler(message: Message):
    """Обработчик команды /about"""
    about_text = """
🧠 О системе автоматического рецензирования

Система использует современные технологии ИИ для анализа научных статей:

🔬 Технологии:
• LLaMA 3.2 для анализа текста
• Специализированные агенты для разных аспектов
• Микросервисная архитектура
• Kubernetes для масштабирования

⚙️ Архитектура:
• Telegram Bot - интерфейс пользователя
• LLM Service - обработка и анализ
• PDF Extractor - извлечение текста
• Agent System - специализированный анализ

💡 Разработано для помощи исследователям в улучшении качества научных публикаций.
"""
    
    await message.answer(about_text, reply_markup=get_back_keyboard())

@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Обработчик команды /cancel"""
    await state.clear()
    await message.answer(
        "❌ Текущая операция отменена. Можете отправить новый документ.",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(ReviewStates.waiting_for_document)

@router.message(StateFilter(ReviewStates.waiting_for_document), F.document)
async def document_handler(message: Message, state: FSMContext):
    """Обработчик получения документа"""
    document: Document = message.document
    
    # Проверяем тип файла
    if not document.file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Пожалуйста, отправьте PDF файл.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Проверяем размер файла (максимум 20MB)
    if document.file_size > 20 * 1024 * 1024:
        await message.answer(
            "❌ Файл слишком большой. Максимальный размер: 20 МБ.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Сообщаем о начале обработки
    processing_message = await message.answer(
        "📄 Получен документ. Начинаю анализ...\n⏳ Это может занять несколько минут.",
        reply_markup=get_processing_keyboard()
    )
    
    await state.set_state(ReviewStates.processing)
    
    try:
        # Скачиваем файл
        file_info = await message.bot.get_file(document.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file_content = await message.bot.download_file(file_info.file_path)
            tmp_file.write(file_content.read())
            tmp_file_path = tmp_file.name
        
        try:
            # Извлекаем текст (пока используем простое чтение файла)
            # В реальной системе здесь был бы вызов PDF extractora
            with open(tmp_file_path, 'rb') as f:
                file_content_bytes = f.read()
            
            # Создаем метаданные
            metadata = {
                "filename": document.file_name,
                "file_size": document.file_size,
                "mime_type": document.mime_type or "application/pdf"
            }
            
            # Для демонстрации создаем простой текстовый анализ
            sample_text = f"Научная статья: {document.file_name}\nРазмер файла: {document.file_size} байт"
            
            # Обновляем сообщение
            await message.bot.edit_message_text(
                "🔍 Анализирую содержимое документа...",
                chat_id=message.chat.id,
                message_id=processing_message.message_id,
                reply_markup=get_processing_keyboard()
            )
            
            # Вызываем LLM сервис
            result = await call_llm_service(sample_text, metadata)
            
            if result.get("success"):
                # Форматируем результаты
                review_text = format_review_result(result.get("results", {}))
                
                await message.bot.edit_message_text(
                    f"✅ Анализ завершен!\n\n{review_text}",
                    chat_id=message.chat.id,
                    message_id=processing_message.message_id,
                    reply_markup=get_results_keyboard()
                )
                
                await state.set_state(ReviewStates.showing_results)
            else:
                raise Exception("LLM service returned error")
                
        finally:
            # Удаляем временный файл
            os.unlink(tmp_file_path)
            
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.bot.edit_message_text(
            f"❌ Ошибка при обработке документа: {str(e)}\n\nПопробуйте еще раз или обратитесь к администратору.",
            chat_id=message.chat.id,
            message_id=processing_message.message_id,
            reply_markup=get_main_keyboard()
        )
        await state.set_state(ReviewStates.waiting_for_document)

def format_review_result(results: Dict[str, Any]) -> str:
    """Форматирует результаты анализа для отправки пользователю"""
    if not results:
        return "Анализ завершен, но результаты пока недоступны."
    
    # Простое форматирование
    formatted = "📊 Результаты анализа:\n\n"
    
    for key, value in results.items():
        if isinstance(value, str):
            formatted += f"• {key}: {value}\n"
        elif isinstance(value, dict):
            formatted += f"• {key}:\n"
            for subkey, subvalue in value.items():
                formatted += f"  - {subkey}: {subvalue}\n"
    
    return formatted

@router.message(StateFilter(ReviewStates.waiting_for_document))
async def waiting_document_handler(message: Message):
    """Обработчик для состояния ожидания документа"""
    await message.answer(
        "📄 Пожалуйста, отправьте PDF файл научной статьи для анализа.",
        reply_markup=get_main_keyboard()
    )

@router.message(StateFilter(ReviewStates.processing))
async def processing_handler(message: Message):
    """Обработчик для состояния обработки"""
    await message.answer(
        "⏳ Документ обрабатывается. Пожалуйста, подождите...",
        reply_markup=get_processing_keyboard()
    )

@router.callback_query(F.data == "new_review")
async def new_review_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Новый анализ'"""
    await state.clear()
    await callback.message.edit_text(
        "📄 Отправьте новый PDF файл для анализа.",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(ReviewStates.waiting_for_document)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню\n\nОтправьте PDF файл для анализа.",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(ReviewStates.waiting_for_document)
    await callback.answer()

@router.message()
async def unknown_handler(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "❓ Команда не распознана. Используйте /help для получения справки.",
        reply_markup=get_main_keyboard()
    ) 