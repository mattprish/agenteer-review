import asyncio
import tempfile
import os
import logging
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.orchestrator import Orchestrator
from core.pdf_extractor import PDFExtractor
from core.agents.structure_agent import StructureAgent
from utils.formatters import format_review, format_progress_message, truncate_text
from .keyboards import (
    get_main_keyboard, get_help_keyboard, get_back_keyboard,
    get_processing_keyboard, get_results_keyboard
)
from .config import config

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Состояния FSM
class ProcessingState(StatesGroup):
    waiting_for_file = State()
    processing = State()

# Инициализация компонентов
orchestrator = Orchestrator(config.ORCHESTRATOR_MODEL)
pdf_extractor = PDFExtractor()
structure_agent = StructureAgent()

# Регистрируем агентов
orchestrator.register_agent("StructureAgent", structure_agent)

# Словарь для хранения активных задач обработки
active_tasks: Dict[int, asyncio.Task] = {}

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    welcome_text = """
🤖 *Добро пожаловать в систему автоматического рецензирования научных статей!*

📋 *Что я умею:*
• Анализировать структуру научных статей
• Проверять наличие обязательных разделов
• Давать рекомендации по улучшению
• Генерировать автоматические рецензии

📄 *Чтобы начать:*
Просто отправьте мне PDF файл с научной статьей, и я проанализирую его структуру и содержание.

💡 *Максимальный размер файла:* 10 МБ
🕐 *Время обработки:* обычно 1-2 минуты
    """
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📄 Загрузить статью")
async def request_file(message: Message, state: FSMContext):
    """Запрос на загрузку файла"""
    await state.set_state(ProcessingState.waiting_for_file)
    
    await message.answer(
        "📎 Отправьте PDF файл с научной статьей для анализа.\n\n"
        "⚠️ *Требования к файлу:*\n"
        "• Формат: PDF\n"
        "• Размер: до 10 МБ\n"
        "• Язык: русский или английский",
        parse_mode="Markdown"
    )

@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Обработчик команды помощи"""
    help_text = """
ℹ️ *Справка по использованию системы*

Выберите раздел для получения подробной информации:
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

🔬 *Версия:* 1.0 (Бейзлайн)
🤖 *Агенты:* Structure Agent
🧠 *ИИ модели:* Llama-3.2-3B, SciBERT

📊 *Текущие возможности:*
• Анализ структуры научных статей
• Проверка наличия ключевых разделов
• Оценка качества организации текста
• Автоматическая генерация рецензий

🚀 *В разработке:*
• Анализ содержания и методологии
• Проверка цитирования и ссылок
• Оценка новизны исследования
• Многоязычная поддержка

👨‍💻 *Разработано как базовый пайплайн для масштабирования*
    """
    
    await message.answer(about_text, parse_mode="Markdown")

@router.callback_query(F.data == "help_usage")
async def help_usage(callback: CallbackQuery):
    """Помощь по использованию"""
    usage_text = """
📖 *Как использовать систему*

1️⃣ *Подготовка файла:*
   • Убедитесь, что статья в формате PDF
   • Размер файла не превышает 10 МБ
   • Текст должен быть машиночитаемым

2️⃣ *Загрузка:*
   • Нажмите "📄 Загрузить статью"
   • Отправьте PDF файл как документ

3️⃣ *Ожидание:*
   • Дождитесь завершения анализа (1-2 минуты)
   • Система покажет прогресс обработки

4️⃣ *Результат:*
   • Получите структурированную рецензию
   • Ознакомьтесь с рекомендациями
   • При необходимости загрузите новую статью
    """
    
    await callback.message.edit_text(
        usage_text,
        # parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "help_tech")
async def help_tech(callback: CallbackQuery):
    """Технические требования"""
    tech_text = """
🔧 *Технические требования*

📄 *Поддерживаемые форматы:*
   • PDF (приоритет)
   • Машиночитаемый текст

📏 *Ограничения:*
   • Максимальный размер: 10 МБ
   • Максимальное время обработки: 2 минуты
   • Количество страниц: до 50

🌐 *Языки:*
   • Русский ✅
   • Английский ✅
   • Другие языки ⚠️ (частично)

⚡ *Производительность:*
   • Время анализа: 30-120 сек
   • Параллельная обработка: до 5 файлов
   • Доступность: 24/7

🔒 *Безопасность:*
   • Файлы не сохраняются после обработки
   • Конфиденциальность данных гарантирована
    """
    
    await callback.message.edit_text(
        tech_text,
        # parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "help_faq")
async def help_faq(callback: CallbackQuery):
    """FAQ"""
    faq_text = """
❓ *Часто задаваемые вопросы*

❓ *Что делать, если файл не обрабатывается?*
   • Проверьте формат файла (должен быть PDF)
   • Убедитесь в корректности файла
   • Попробуйте загрузить повторно

❓ *Почему анализ занимает много времени?*
   • Размер файла влияет на скорость
   • Сложность текста требует больше времени
   • Серверная нагрузка может замедлять процесс

❓ *Насколько точны результаты?*
   • Система находится в стадии бейзлайна
   • Точность структурного анализа: ~80%
   • Рекомендуется экспертная проверка

❓ *Сохраняются ли мои файлы?*
   • Нет, файлы удаляются после обработки
   • Конфиденциальность полностью защищена

❓ *Можно ли анализировать статьи на других языках?*
   • Основная поддержка: русский и английский
   • Другие языки: частичная поддержка
    """
    
    await callback.message.edit_text(
        faq_text,
        # parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "back_to_help")
async def back_to_help(callback: CallbackQuery):
    """Возврат к помощи"""
    help_text = """
ℹ️ *Справка по использованию системы*

Выберите раздел для получения подробной информации:
    """
    
    await callback.message.edit_text(
        help_text,
        # parse_mode="Markdown",
        reply_markup=get_help_keyboard()
    )

@router.message(F.document, StateFilter(ProcessingState.waiting_for_file))
async def handle_document(message: Message, state: FSMContext):
    """Обработчик загруженного документа"""
    document: Document = message.document
    
    # Проверяем тип файла
    if not pdf_extractor.validate_file_extension(document.file_name):
        await message.answer(
            "❌ Неподдерживаемый формат файла!\n\n"
            "📎 Пожалуйста, отправьте файл в формате PDF.",
            # parse_mode="Markdown"
        )
        return
    
    # Проверяем размер файла
    if not pdf_extractor.validate_file_size(document.file_size, config.MAX_FILE_SIZE):
        size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"❌ Файл слишком большой!\n\n"
            f"📏 Максимальный размер: {size_mb:.1f} МБ\n"
            f"📎 Размер вашего файла: {document.file_size / (1024 * 1024):.1f} МБ",
            # parse_mode="Markdown"
        )
        return
    
    # Переходим в состояние обработки
    await state.set_state(ProcessingState.processing)
    
    # Создаем задачу обработки
    task = asyncio.create_task(
        process_document(message, document)
    )
    
    # Сохраняем задачу
    active_tasks[message.from_user.id] = task
    
    try:
        await task
    finally:
        # Удаляем завершенную задачу
        active_tasks.pop(message.from_user.id, None)
        await state.clear()

async def process_document(message: Message, document: Document):
    """Асинхронная обработка документа"""
    user_id = message.from_user.id
    
    try:
        # Показываем прогресс
        progress_msg = await message.answer(
            format_progress_message("downloading"),
            reply_markup=get_processing_keyboard()
        )
        
        # Скачиваем файл
        file = await message.bot.download(document.file_id)
        
        # Обновляем прогресс
        await progress_msg.edit_text(
            format_progress_message("extracting"),
            reply_markup=get_processing_keyboard()
        )
        
        # Извлекаем текст
        text, metadata = await pdf_extractor.extract_from_bytes(file.read())
        
        # Обновляем прогресс
        await progress_msg.edit_text(
            format_progress_message("analyzing_structure"),
            reply_markup=get_processing_keyboard()
        )
        
        # Добавляем имя файла в метаданные
        metadata["filename"] = document.file_name
        
        # Запускаем анализ
        results = await orchestrator.process_paper(text, metadata)
        
        # Обновляем прогресс
        await progress_msg.edit_text(
            format_progress_message("finalizing"),
            reply_markup=get_processing_keyboard()
        )
        
        # Форматируем результат
        formatted_review = format_review(results)
        
        # Обрезаем текст если необходимо
        formatted_review = truncate_text(formatted_review)
        
        # Отправляем результат
        await progress_msg.edit_text(
            formatted_review,
            # parse_mode="Markdown",
            reply_markup=get_results_keyboard()
        )
        
        logger.info(f"Successfully processed document for user {user_id}")
        
    except asyncio.CancelledError:
        await message.answer(
            "⏹ Обработка отменена пользователем.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Processing cancelled by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing document for user {user_id}: {e}")
        
        error_msg = f"❌ Произошла ошибка при обработке файла:\n\n{str(e)}"
        
        try:
            await progress_msg.edit_text(
                error_msg,
                reply_markup=get_main_keyboard()
            )
        except:
            await message.answer(
                error_msg,
                reply_markup=get_main_keyboard()
            )

@router.callback_query(F.data == "cancel_processing")
async def cancel_processing(callback: CallbackQuery, state: FSMContext):
    """Отмена обработки"""
    user_id = callback.from_user.id
    
    # Отменяем задачу если она существует
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        active_tasks.pop(user_id, None)
    
    await state.clear()
    
    await callback.message.edit_text(
        "⏹ Обработка отменена.",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "new_paper")
async def new_paper(callback: CallbackQuery, state: FSMContext):
    """Загрузка новой статьи"""
    await state.set_state(ProcessingState.waiting_for_file)
    
    await callback.message.edit_text(
        "📎 Отправьте новый PDF файл с научной статьей для анализа.\n\n"
        "⚠️ *Требования к файлу:*\n"
        "• Формат: PDF\n"
        "• Размер: до 10 МБ\n"
        "• Язык: русский или английский",
        # parse_mode="Markdown"
    )

@router.callback_query(F.data == "detailed_report")
async def detailed_report(callback: CallbackQuery):
    """Подробный отчет"""
    await callback.answer(
        "🚧 Функция подробного отчета будет добавлена в следующих версиях системы.",
        show_alert=True
    )

@router.message(StateFilter(ProcessingState.processing))
async def processing_state_handler(message: Message):
    """Обработчик сообщений во время обработки"""
    await message.answer(
        "⏳ Ваш файл обрабатывается. Пожалуйста, дождитесь завершения анализа.\n\n"
        "Для отмены нажмите кнопку ⏹ Отменить.",
        reply_markup=get_processing_keyboard()
    )

@router.message()
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "🤔 Я не понимаю это сообщение.\n\n"
        "📄 Для анализа статьи отправьте PDF файл.\n"
        "ℹ️ Для получения помощи используйте кнопки меню.",
        reply_markup=get_main_keyboard()
    ) 