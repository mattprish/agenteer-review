#!/usr/bin/env python3
"""
Основной файл для запуска системы автоматического рецензирования научных статей
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import router
from bot.config import config

# Настройка логирования
def setup_logging():
    """Настраивает логирование"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

async def main():
    """Основная функция запуска бота"""
    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Review Bot...")
    
    # Проверяем наличие токена
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        logger.error("Please set BOT_TOKEN environment variable")
        sys.exit(1)
    
    # Создаем временные директории
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    os.makedirs(config.MODEL_CACHE_DIR, exist_ok=True)
    
    # Инициализируем бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутер
    dp.include_router(router)
    
    try:
        # Удаляем webhook (если был установлен)
        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Bot started successfully!")
        logger.info(f"Bot username: @{(await bot.get_me()).username}")
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)
    
    finally:
        await bot.session.close()
        logger.info("Bot stopped")

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    try:
        import ollama
        import fitz  # PyMuPDF
        import transformers
        import aiogram
        logger = logging.getLogger(__name__)
        logger.info("All dependencies are available")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install all required packages from requirements.txt")
        return False

if __name__ == "__main__":
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)
