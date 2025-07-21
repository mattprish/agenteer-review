#!/usr/bin/env python3
"""
Основное приложение с FastAPI-сервером и Telegram-ботом в одном контейнере
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from api.llm_server import app as fastapi_app
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
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )

async def start_fastapi_server():
    """Запускает FastAPI сервер"""
    logger = logging.getLogger("fastapi")
    logger.info("Starting FastAPI server on port 8000...")
    
    config_uvicorn = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()

async def start_telegram_bot():
    """Запускает Telegram бота"""
    logger = logging.getLogger("telegram")
    
    # Проверяем наличие токена
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        sys.exit(1)
    
    # Создаем временные директории
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    
    # Инициализируем бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутер
    dp.include_router(router)
    
    try:
        # Удаляем webhook (если был установлен)
        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Telegram bot started successfully!")
        logger.info(f"Bot username: @{(await bot.get_me()).username}")
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        await bot.session.close()

async def main():
    """Главная функция - запускает оба сервиса параллельно"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Application with FastAPI server and Telegram bot...")
    
    # Запускаем оба сервиса параллельно
    await asyncio.gather(
        start_fastapi_server(),
        start_telegram_bot(),
        return_exceptions=True
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1) 