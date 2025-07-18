#!/usr/bin/env python3
"""
Telegram бот для автоматического рецензирования научных статей
Работает с отдельным LLM сервисом через HTTP API
"""

import asyncio
import logging
import sys
import os
import aiohttp
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot_service_handlers import router
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

class LLMClient:
    """Клиент для работы с LLM сервисом"""
    
    def __init__(self, llm_service_url: str):
        self.llm_service_url = llm_service_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self):
        """Проверка доступности LLM сервиса"""
        try:
            async with self.session.get(f"{self.llm_service_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logging.error(f"LLM service health check failed: {e}")
            return None
    
    async def review_paper(self, text: str, metadata: dict = None):
        """Отправляет статью на рецензирование"""
        try:
            payload = {
                "text": text,
                "metadata": metadata or {}
            }
            
            async with self.session.post(
                f"{self.llm_service_url}/review",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"LLM service error: {error_text}")
                    
        except Exception as e:
            logging.error(f"Error calling LLM service: {e}")
            raise

# Глобальный клиент LLM
llm_client = None

async def get_llm_client():
    """Получает клиент LLM сервиса"""
    global llm_client
    if llm_client is None:
        llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")
        llm_client = LLMClient(llm_service_url)
    return llm_client

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
    
    # Инициализируем бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутер
    dp.include_router(router)
    
    # Инициализируем LLM клиент
    global llm_client
    llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")
    llm_client = LLMClient(llm_service_url)
    
    try:
        # Проверяем подключение к LLM сервису
        async with llm_client as client:
            health = await client.health_check()
            if health:
                logger.info(f"LLM service is healthy: {health}")
            else:
                logger.warning("LLM service health check failed, but continuing...")
        
        # Удаляем webhook (если был установлен)
        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Bot started successfully!")
        logger.info(f"Bot username: @{(await bot.get_me()).username}")
        logger.info(f"LLM service URL: {llm_service_url}")
        
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
        import aiogram
        import aiohttp
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