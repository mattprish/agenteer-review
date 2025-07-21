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

# Добавляем src директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

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

    async def test_configuration(self):
        """Тест конфигурации"""
        try:
            from bot.config import config
            
            # Проверяем основные настройки
            assert hasattr(config, 'BOT_TOKEN')
            assert hasattr(config, 'LOG_LEVEL')
            assert hasattr(config, 'TEMP_DIR')
            
            self.test_result("Configuration", True)
            
        except Exception as e:
            self.test_result("Configuration", False, str(e))
    
    async def test_file_structure(self):
        """Тест структуры файлов для новой архитектуры"""
        try:
            required_files = [
                "src/app.py",  # Главное приложение
                "src/api/llm_server.py",  # FastAPI сервер
                "src/core/orchestrator.py",
                "src/core/pdf_extractor.py",
                "src/core/agents/base_agent.py",
                "src/core/agents/structure_agent.py",
                "src/core/agents/summary_agent.py",
                "src/bot/config.py",
                "src/bot/keyboards.py",
                "src/bot/handlers.py",
                "config/requirements.txt",
                "docker/Dockerfile",
                "docker/docker-compose.yml"
            ]
            
            missing_files = []
            for file_path in required_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                self.test_result("File structure", False, f"Missing files: {missing_files}")
            else:
                self.test_result("File structure", True)
                
        except Exception as e:
            self.test_result("File structure", False, str(e))
    
    async def test_dependencies(self):
        """Тест зависимостей"""
        try:
            # Проверяем основные пакеты
            import aiohttp
            import aiogram
            import fastapi
            import uvicorn
            import ollama
            import fitz  # PyMuPDF
            
            self.test_result("Dependencies", True)
            
        except Exception as e:
            self.test_result("Dependencies", False, str(e))
    
    async def test_pdf_extractor_basic(self):
        """Базовый тест PDF экстрактора"""
        try:
            from core.pdf_extractor import PDFExtractor
            
            extractor = PDFExtractor()
            
            # Проверяем что extractor создается
            assert extractor is not None
            
            self.test_result("PDF extractor basic", True)
            
        except Exception as e:
            self.test_result("PDF extractor basic", False, str(e))
    
    async def test_structure_agent_basic(self):
        """Базовый тест агента структуры"""
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
        """Тест импорта обработчиков бота (новая архитектура)"""
        try:
            from bot.handlers import router, LLMServiceClient
            from bot.keyboards import get_main_keyboard
            
            # Проверяем что router существует
            assert router is not None
            
            # Проверяем HTTP клиент
            client = LLMServiceClient()
            assert client is not None
            
            # Проверяем клавиатуру
            keyboard = get_main_keyboard()
            assert keyboard is not None
            
            self.test_result("Bot handlers import", True)
            
        except Exception as e:
            self.test_result("Bot handlers import", False, str(e))
    
    async def test_llm_service_import(self):
        """Тест импорта FastAPI сервера"""
        try:
            from api.llm_server import app
            
            # Проверяем что FastAPI app существует
            assert app is not None
            
            self.test_result("FastAPI service import", True)
            
        except Exception as e:
            self.test_result("FastAPI service import", False, str(e))

    async def test_summary_agent_basic(self):
        """Базовый тест агента суммаризации"""
        try:
            # Мокаем ollama клиент ДО создания агента
            with patch('ollama.AsyncClient') as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value = mock_instance
                
                # Настраиваем мок ответ для chat метода
                mock_instance.chat.return_value = {
                    'message': {
                        'content': 'This paper presents a new AI method achieving 95% accuracy. The work demonstrates effectiveness in AI analysis applications.'
                    }
                }
                
                from core.agents.summary_agent import SummaryAgent
                agent = SummaryAgent()
                
                # Простой тест с минимальным текстом
                test_text = """
                Abstract: This paper presents a new method for AI analysis.
                Introduction: AI is important for modern research.
                Results: We achieved 95% accuracy.
                Conclusion: The method is effective.
                """
                
                results = await agent.analyze(test_text, {"title": "Test AI Paper"})
                
                # Проверяем результат
                assert isinstance(results, dict)
                assert "summary" in results
                
            self.test_result("Summary agent basic", True)
            
        except Exception as e:
            self.test_result("Summary agent basic", False, str(e))

    def print_results(self):
        """Выводит финальные результаты"""
        total = self.passed + self.failed
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*50)
        print("📊 РЕЗУЛЬТАТЫ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ")
        print("="*50)
        
        if self.failed == 0:
            print(f"🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ: {self.passed}/{total}")
            print(f"⏱️ Время выполнения: {elapsed:.1f}с")
            print("✅ Готово к коммиту!")
        else:
            print(f"❌ Есть проблемы: {self.passed}/{total} тестов пройдено")
            print(f"💥 Не прошло: {self.failed} тестов")
            print("🔧 Исправьте ошибки перед коммитом")
            
        print("="*50)

async def main():
    """Главная функция тестирования"""
    logger.info("🏠 Запуск локальных тестов для разработки")
    logger.info("="*50)
    
    runner = LocalTestRunner()
    
    # Запускаем все тесты
    await runner.test_imports()
    await runner.test_configuration()
    await runner.test_file_structure()
    await runner.test_dependencies()
    await runner.test_pdf_extractor_basic()
    await runner.test_structure_agent_basic()
    await runner.test_orchestrator_basic()
    await runner.test_bot_handlers_import()
    await runner.test_llm_service_import()
    await runner.test_summary_agent_basic()
    
    # Выводим результаты
    runner.print_results()
    
    # Возвращаем код выхода
    return 0 if runner.failed == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nТестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 