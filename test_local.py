#!/usr/bin/env python3
"""
🏠 Тесты для локальной разработки
Быстрые тесты которые можно запускать во время разработки
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalTestRunner:
    """Тестер для локальной разработки"""
    
    def __init__(self):
        self.start_time = time.time()
        self.passed = 0
        self.failed = 0
    
    def test_result(self, test_name: str, success: bool, message: str = ""):
        """Записывает результат теста"""
        if success:
            self.passed += 1
            logger.info(f"✅ {test_name}")
        else:
            self.failed += 1
            logger.error(f"❌ {test_name}: {message}")
    
    async def test_imports(self):
        """Быстрый тест импортов"""
        try:
            # Основные модули
            from core.orchestrator import Orchestrator
            from core.pdf_extractor import PDFExtractor
            from core.agents.structure_agent import StructureAgent
            from core.agents.base_agent import BaseAgent
            
            # Конфигурация
            from bot.config import config
            
            self.test_result("Core imports", True)
            
        except Exception as e:
            self.test_result("Core imports", False, str(e))
    
    async def test_config(self):
        """Тест конфигурации"""
        try:
            from bot.config import config
            
            # Проверяем наличие обязательных настроек
            required_attrs = ['TEMP_DIR', 'MAX_FILE_SIZE']
            
            for attr in required_attrs:
                if not hasattr(config, attr):
                    raise Exception(f"Missing config attribute: {attr}")
            
            # Проверяем что директории существуют
            temp_dir = Path(config.TEMP_DIR)
            if not temp_dir.exists():
                temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.test_result("Configuration", True)
            
        except Exception as e:
            self.test_result("Configuration", False, str(e))
    
    async def test_pdf_extractor_basic(self):
        """Базовый тест PDF экстрактора"""
        try:
            from core.pdf_extractor import PDFExtractor
            
            extractor = PDFExtractor()
            
            # Тесты валидации
            assert extractor.validate_file_extension("test.pdf") == True
            assert extractor.validate_file_extension("test.txt") == False
            assert extractor.validate_file_size(1024) == True
            assert extractor.validate_file_size(50 * 1024 * 1024) == False
            
            self.test_result("PDF extractor basic", True)
            
        except Exception as e:
            self.test_result("PDF extractor basic", False, str(e))
    
    async def test_structure_agent_basic(self):
        """Базовый тест структурного агента"""
        try:
            from core.agents.structure_agent import StructureAgent
            
            agent = StructureAgent()
            
            # Простой тест с минимальным текстом
            test_text = """
            Abstract
            This is a test.
            
            Introduction
            This is introduction.
            
            Conclusion
            This is conclusion.
            """
            
            # Мокаем LLM вызов если Ollama недоступен
            with patch('ollama.AsyncClient') as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value = mock_instance
                
                # Настраиваем мок ответ
                mock_instance.generate.return_value = {
                    'response': '{"found_sections": ["Abstract", "Introduction", "Conclusion"], "structure_quality": "good"}'
                }
                
                results = await agent.analyze(test_text, {"title": "Test"})
                
                # Проверяем результат
                assert isinstance(results, dict)
                assert "found_sections" in results
                
            self.test_result("Structure agent basic", True)
            
        except Exception as e:
            self.test_result("Structure agent basic", False, str(e))
    
    async def test_orchestrator_basic(self):
        """Базовый тест оркестратора"""
        try:
            from core.orchestrator import Orchestrator
            from core.agents.structure_agent import StructureAgent
            
            orchestrator = Orchestrator()
            agent = StructureAgent()
            
            # Регистрируем агента
            orchestrator.register_agent("TestAgent", agent)
            
            # Проверяем регистрацию
            assert "TestAgent" in orchestrator.agents
            
            self.test_result("Orchestrator basic", True)
            
        except Exception as e:
            self.test_result("Orchestrator basic", False, str(e))
    
    async def test_bot_handlers_import(self):
        """Тест импорта обработчиков бота"""
        try:
            import bot_service_handlers
            from bot.keyboards import get_main_keyboard
            
            # Проверяем что router существует
            assert hasattr(bot_service_handlers, 'router')
            
            # Проверяем клавиатуру
            keyboard = get_main_keyboard()
            assert keyboard is not None
            
            self.test_result("Bot handlers import", True)
            
        except Exception as e:
            self.test_result("Bot handlers import", False, str(e))
    
    async def test_llm_service_import(self):
        """Тест импорта LLM сервиса"""
        try:
            import llm_service
            
            # Проверяем что FastAPI app существует
            assert hasattr(llm_service, 'app')
            
            self.test_result("LLM service import", True)
            
        except Exception as e:
            self.test_result("LLM service import", False, str(e))
    
    async def test_file_structure(self):
        """Тест структуры файлов"""
        try:
            required_files = [
                "bot_service.py",
                "llm_service.py", 
                "core/orchestrator.py",
                "core/pdf_extractor.py",
                "core/agents/base_agent.py",
                "core/agents/structure_agent.py",
                "bot/config.py",
                "bot/keyboards.py",
                "requirements.txt",
                "Dockerfile.bot",
                "Dockerfile.llm",
                "docker-compose.production.yml"
            ]
            
            missing_files = []
            for file_path in required_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                raise Exception(f"Missing files: {missing_files}")
            
            self.test_result("File structure", True)
            
        except Exception as e:
            self.test_result("File structure", False, str(e))
    
    async def test_dependencies(self):
        """Тест зависимостей"""
        try:
            import aiogram
            import aiohttp
            import fastapi
            import uvicorn
            import ollama
            import pydantic
            
            self.test_result("Dependencies", True)
            
        except ImportError as e:
            self.test_result("Dependencies", False, f"Missing dependency: {e}")
        except Exception as e:
            self.test_result("Dependencies", False, str(e))
    
    async def run_all(self):
        """Запускает все локальные тесты"""
        logger.info("🏠 Запуск локальных тестов для разработки")
        logger.info("=" * 50)
        
        # Быстрые тесты
        await self.test_imports()
        await self.test_config()
        await self.test_file_structure()
        await self.test_dependencies()
        
        # Тесты компонентов
        await self.test_pdf_extractor_basic()
        await self.test_structure_agent_basic()
        await self.test_orchestrator_basic()
        
        # Тесты модулей
        await self.test_bot_handlers_import()
        await self.test_llm_service_import()
        
        # Результаты
        duration = time.time() - self.start_time
        total = self.passed + self.failed
        
        print("\n" + "=" * 50)
        print("📊 РЕЗУЛЬТАТЫ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ")
        print("=" * 50)
        
        if self.failed == 0:
            print(f"✅ Все тесты пройдены: {self.passed}/{total} за {duration:.2f}s")
            print("🎉 Код готов для коммита!")
        else:
            print(f"❌ Есть проблемы: {self.passed}/{total} тестов пройдено")
            print(f"💥 Не прошло: {self.failed} тестов")
            print("🔧 Исправьте ошибки перед коммитом")
        
        print("=" * 50)
        
        return self.failed == 0

async def main():
    """Основная функция локального тестирования"""
    runner = LocalTestRunner()
    
    try:
        success = await runner.run_all()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано")
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 