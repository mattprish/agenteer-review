import asyncio
import tempfile
import os
import logging
from typing import Dict, Any
import aiohttp
import aiofiles

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.formatters import format_review, format_progress_message, truncate_text
from .keyboards import (
    get_main_keyboard, get_help_keyboard, get_back_keyboard,
    get_processing_keyboard, get_results_keyboard
)
from .config import config
from utils.pdf.pdf import async_extract_text_from_pdf
verbose = False

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Состояния FSM
class ProcessingState(StatesGroup):
    waiting_for_file = State()
    processing = State()

# HTTP клиент для взаимодействия с LLM сервисом
class LLMServiceClient:
    """Клиент для работы с FastAPI сервером"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
    
    async def health_check(self) -> bool:
        """Проверка доступности сервиса"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def upload_pdf(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Загрузка PDF файла на обработку"""
        try:
            with open(file_path, 'rb') as file:
                pdf_content = file.read()
                text = await async_extract_text_from_pdf(pdf_content)
                return {"success": True, "text": text}
        except Exception as e:
            logger.error(f"Error uploading PDF: {e}")
            return {"success": False, "error": str(e)}
    
    async def review_paper(self, text: str) -> Dict[str, Any]:
        """Отправка текста на рецензирование"""
        try:
            payload = {
                "text": text,
                "metadata": None
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/review", json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Error reviewing paper: {e}")
            return {"success": False, "error": str(e)}

# Глобальный клиент
llm_client = LLMServiceClient()

# Словарь для хранения активных задач обработки
active_tasks: Dict[int, asyncio.Task] = {}

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    welcome_text = """
🤖 *Добро пожаловать в систему автоматического рецензирования научных статей!*

Я помогу вам получить быструю и качественную рецензию на вашу научную работу.

📄 *Что я умею:*
• Анализ структуры научных статей
• Проверка содержания и методологии  
• Оценка качества изложения
• Генерация рекомендаций по улучшению

🚀 *Для начала работы:*
Отправьте мне PDF файл с вашей статьей или воспользуйтесь кнопками ниже.

⚠️ *Ограничения:*
• Максимальный размер файла: 10 МБ
• Поддерживаемые форматы: PDF
• Время обработки: 1-2 минуты
    """
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📄 Загрузить статью")
async def request_file(message: Message, state: FSMContext):
    """Запрос файла для анализа"""
    await state.set_state(ProcessingState.waiting_for_file)
    
    instruction_text = """
📄 *Загрузка статьи для анализа*

Пожалуйста, отправьте PDF файл с научной статьей.

📋 *Требования к файлу:*
• Формат: PDF
• Размер: до 10 МБ  
• Текст должен быть машиночитаемым (не скан)
• Язык: русский или английский

🔍 *Что будет проанализировано:*
• Структура и организация текста
• Качество изложения материала
• Соответствие научным стандартам
• Рекомендации по улучшению

Просто прикрепите файл к следующему сообщению!
    """
    
    await message.answer(
        instruction_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

@router.message(StateFilter(ProcessingState.waiting_for_file), F.document)
async def process_document(message: Message, state: FSMContext):
    """Обработка загруженного документа"""
    document: Document = message.document
    
    # Проверяем тип файла
    if not document.file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Поддерживаются только PDF файлы. Пожалуйста, отправьте файл в формате PDF.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Проверяем размер файла (10 МБ = 10 * 1024 * 1024 байт)
    if document.file_size > 10 * 1024 * 1024:
        await message.answer(
            "❌ Размер файла превышает 10 МБ. Пожалуйста, отправьте файл меньшего размера.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Проверяем доступность LLM сервиса
    if not await llm_client.health_check():
        await message.answer(
            "❌ Сервис анализа временно недоступен. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.set_state(ProcessingState.processing)
    
    # Отправляем сообщение о начале обработки
    progress_message = await message.answer(
        "🔄 *Начинаю обработку файла...*\n\n"
        "📄 Загружаю и анализирую документ\n"
        "⏱ Это может занять 1-2 минуты",
        parse_mode="Markdown",
        reply_markup=get_processing_keyboard()
    )
    
    # Создаем задачу обработки
    task = asyncio.create_task(
        process_file_async(message, document, progress_message, state, verbose=False)
    )
    active_tasks[message.from_user.id] = task

async def process_file_async(message: Message, document: Document, progress_message: Message, state: FSMContext, verbose: bool = False):
    """Асинхронная обработка файла"""
    user_id = message.from_user.id
    
    try:
        # Скачиваем файл
        await progress_message.edit_text(
            "🔄 *Обработка файла...*\n\n"
            "📥 Скачиваю файл...",
            parse_mode="Markdown",
            reply_markup=get_processing_keyboard()
        )
        
        file_info = await message.bot.get_file(document.file_id)
        
        # Создаем временный файл
        temp_dir = config.TEMP_DIR
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f"temp_{user_id}_{document.file_name}")
        
        # Скачиваем файл
        await message.bot.download_file(file_info.file_path, temp_file_path)
        
        # Обновляем прогресс
        await progress_message.edit_text(
            "🔄 *Обработка файла...*\n\n"
            "📄 Извлекаю текст из PDF...",
            parse_mode="Markdown",
            reply_markup=get_processing_keyboard()
        )
        
        # Загружаем PDF на обработку
        pdf_result = await llm_client.upload_pdf(temp_file_path, document.file_name)
        
        if not pdf_result.get("success", False):
            await progress_message.edit_text(
                f"❌ *Ошибка при обработке PDF*\n\n"
                f"Детали: {pdf_result.get('error', 'Неизвестная ошибка')}",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Обновляем прогресс
        await progress_message.edit_text(
            "🔄 *Анализирую содержание...*\n\n"
            "🤖 Агенты анализируют структуру и содержание\n"
            "⏱ Осталось около минуты...",
            parse_mode="Markdown",
            reply_markup=get_processing_keyboard()
        )
        
        # Отправляем на рецензирование
        review_result = await llm_client.review_paper(
            text=pdf_result["text"]
            # metadata=pdf_result["metadata"]
        )
        print(review_result)
        
        if not review_result.get("success", False):
            await progress_message.edit_text(
                f"❌ *Ошибка при анализе статьи*\n\n"
                f"Детали: {review_result.get('error', 'Неизвестная ошибка')}",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Форматируем и отправляем результат
        formatted_review = format_review(
            review_result["results"],
            None,
            verbose=verbose
        )
        
        await progress_message.edit_text(
            "✅ *Анализ завершен!*\n\n"
            "📋 Готовлю результаты...",
            parse_mode="Markdown"
        )
        
        # Отправляем результат (разбиваем на части если длинный)
        if len(formatted_review) > 4000:
            parts = [formatted_review[i:i+4000] for i in range(0, len(formatted_review), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    await message.answer(
                        part,
                        parse_mode="Markdown",
                        reply_markup=get_results_keyboard() if i == len(parts) - 1 else None
                    )
                else:
                    await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(
                formatted_review,
                parse_mode="Markdown",
                reply_markup=get_results_keyboard()
            )
        
        # Удаляем сообщение о прогрессе
        try:
            await progress_message.delete()
        except:
            pass
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await progress_message.edit_text(
            f"❌ *Произошла ошибка при обработке*\n\n"
            f"Попробуйте загрузить файл еще раз.\n"
            f"Если ошибка повторится, обратитесь к администратору.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
    
    finally:
        # Удаляем временный файл
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        # Удаляем задачу из активных
        if user_id in active_tasks:
            del active_tasks[user_id]
        
        # Сбрасываем состояние
        await state.clear()

@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    """Справка по использованию"""
    help_text = """
❓ *Справка по использованию*

🤖 *О системе:*
Это система автоматического рецензирования научных статей на основе ИИ. Она анализирует структуру, содержание и качество изложения вашей работы.

📖 *Как использовать:*
1. Нажмите "📄 Загрузить статью"
2. Отправьте PDF файл (до 10 МБ)
3. Дождитесь результатов анализа (1-2 минуты)
4. Получите детальную рецензию с рекомендациями

⚙️ *Что анализируется:*
• Структурная организация текста
• Качество изложения материала
• Соответствие научным стандартам
• Рекомендации по улучшению

🔧 *Технические детали и FAQ доступны в соответствующих разделах*
    """
    
    await message.answer(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_help_keyboard()
    )

@router.message(F.text == "⚙️ О системе")
async def cmd_about(message: Message):
    """Информация о системе"""
    about_text = """
⚙️ *О системе автоматического рецензирования*

🔬 *Версия:* 2.0 (Правильная архитектура)
🤖 *Агенты:* Structure Agent, Summary Agent
🧠 *ИИ модели:* Llama-3.2-3B

📊 *Текущие возможности:*
• Анализ структуры научных статей
• Суммаризация содержания
• Проверка наличия ключевых разделов
• Оценка качества организации текста
• Автоматическая генерация рецензий

🏗️ *Архитектура:*
• FastAPI сервер на порту 8000
• Telegram бот через HTTP API
• Ollama для LLM на порту 11434
• Модульная система агентов

👨‍💻 *Соответствует техническому заданию*
    """
    
    await message.answer(about_text, parse_mode="Markdown")

@router.callback_query(F.data == "cancel_processing")
async def cancel_processing(callback: CallbackQuery, state: FSMContext):
    """Отмена обработки"""
    user_id = callback.from_user.id
    
    # Отменяем активную задачу
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        del active_tasks[user_id]
    
    await state.clear()
    
    await callback.message.edit_text(
        "❌ *Обработка отменена*\n\n"
        "Вы можете загрузить другой файл или воспользоваться другими функциями.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "new_analysis")
async def new_analysis(callback: CallbackQuery, state: FSMContext):
    """Начать новый анализ"""
    await state.clear()
    await callback.message.edit_text(
        "📄 *Загрузка новой статьи*\n\n"
        "Отправьте PDF файл для анализа.",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(ProcessingState.waiting_for_file)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 *Главное меню*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# Обработчик неподдерживаемых сообщений
@router.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработка неподдерживаемых сообщений"""
    current_state = await state.get_state()
    
    if current_state == ProcessingState.waiting_for_file:
        await message.answer(
            "📄 Пожалуйста, отправьте PDF файл документом, а не текстом.",
            reply_markup=get_back_keyboard()
        )
    else:
        await message.answer(
            "🤔 Я не понимаю эту команду. Воспользуйтесь кнопками или отправьте /start",
            reply_markup=get_main_keyboard()
        ) 