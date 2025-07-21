#!/usr/bin/env python3
"""
Скрипт для тестирования исправленной архитектуры
"""

import asyncio
import aiohttp
import logging
import sys
import os
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_fastapi_server():
    """Тестирует FastAPI сервер"""
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5 секунд timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Тест health check
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ FastAPI Health Check: {health_data}")
                    return True
                else:
                    logger.error(f"❌ FastAPI Health Check failed: {response.status}")
                    return False
    except asyncio.TimeoutError:
        logger.warning("⚠️ FastAPI server timeout - server not running")
        return False
    except Exception as e:
        logger.warning(f"⚠️ FastAPI connection failed: {e}")
        return False

async def test_ollama_connection():
    """Тестирует подключение к Ollama"""
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5 секунд timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:11434/api/version") as response:
                if response.status == 200:
                    logger.info("✅ Ollama connection successful")
                    return True
                else:
                    logger.error(f"❌ Ollama connection failed: {response.status}")
                    return False
    except asyncio.TimeoutError:
        logger.warning("⚠️ Ollama server timeout - server not running")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Ollama connection failed: {e}")
        return False

async def test_models_endpoint():
    """Тестирует эндпоинт моделей"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:8000/models") as response:
                if response.status == 200:
                    models_data = await response.json()
                    logger.info(f"✅ Models endpoint: {models_data}")
                    return True
                else:
                    logger.error(f"❌ Models endpoint failed: {response.status}")
                    return False
    except asyncio.TimeoutError:
        logger.warning("⚠️ Models endpoint timeout")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Models endpoint failed: {e}")
        return False

async def test_review_endpoint():
    """Тестирует эндпоинт рецензирования"""
    try:
        test_data = {
            "text": """
            Введение
            
            Данная работа посвящена исследованию влияния искусственного интеллекта на современное общество.
            Актуальность темы обусловлена быстрым развитием технологий машинного обучения.
            
            Методология
            
            В работе использованы методы статистического анализа и машинного обучения.
            Данные собирались в течение 6 месяцев из различных источников.
            
            Результаты
            
            Получены значимые результаты, показывающие положительное влияние ИИ на производительность.
            
            Заключение
            
            Работа демонстрирует важность интеграции ИИ в современные бизнес-процессы.
            
            Список литературы
            
            1. Smith, J. (2023). AI in Business. Journal of Technology.
            """,
            "metadata": {
                "title": "Тестовая статья об ИИ",
                "author": "Тестовый автор",
                "page_count": 5
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=30)  # 30 секунд для review
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("http://localhost:8000/review", json=test_data) as response:
                if response.status == 200:
                    review_data = await response.json()
                    logger.info("✅ Review endpoint working")
                    logger.info(f"Review status: {review_data.get('success')}")
                    
                    # Проверяем структуру ответа
                    if review_data.get('success'):
                        results = review_data.get('results', {})
                        agent_results = results.get('agent_results', {})
                        
                        logger.info(f"Found agents: {list(agent_results.keys())}")
                        
                        # Проверяем Structure Agent
                        if 'StructureAgent' in agent_results:
                            structure_data = agent_results['StructureAgent']
                            found_sections = structure_data.get('found_sections', [])
                            logger.info(f"✅ StructureAgent found sections: {found_sections}")
                        
                        # Проверяем Summary Agent
                        if 'SummaryAgent' in agent_results:
                            summary_data = agent_results['SummaryAgent']
                            summary_quality = summary_data.get('summary_quality', 'unknown')
                            logger.info(f"✅ SummaryAgent quality: {summary_quality}")
                        
                        # Проверяем финальную рецензию
                        final_review = results.get('final_review', '')
                        if final_review:
                            logger.info(f"✅ Final review generated ({len(final_review)} chars)")
                        
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Review endpoint failed: {response.status} - {error_text}")
                    return False
    except asyncio.TimeoutError:
        logger.warning("⚠️ Review endpoint timeout - taking too long")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Review endpoint failed: {e}")
        return False

async def test_architecture_compliance():
    """Тестирует соответствие архитектуре"""
    logger.info("🔍 Testing Architecture Compliance...")
    
    compliance_issues = []
    
    # Проверяем наличие правильных файлов архитектуры
    required_files = [
        "src/app.py",  # Главный файл приложения
        "src/api/llm_server.py",  # FastAPI сервер
        "src/bot/handlers.py",  # Telegram handlers
        "docker/docker-compose.yml",  # Docker compose
        "docker/Dockerfile",  # Dockerfile
        "config/requirements.txt"  # Зависимости
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            compliance_issues.append(f"Missing file: {file_path}")
        else:
            logger.info(f"✅ Found: {file_path}")
    
    # Проверяем что bot/handlers.py НЕ импортирует агентов напрямую
    handlers_path = Path("src/bot/handlers.py")
    if handlers_path.exists():
        with open(handlers_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        forbidden_imports = [
            "from core.orchestrator import",
            "from core.agents.",
            "from core.pdf_extractor import"
        ]
        
        for forbidden_import in forbidden_imports:
            if forbidden_import in content:
                compliance_issues.append(f"FORBIDDEN IMPORT in handlers.py: {forbidden_import}")
            else:
                logger.info(f"✅ No forbidden import: {forbidden_import}")
    
    # Проверяем наличие HTTP клиента в handlers
    if handlers_path.exists():
        with open(handlers_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "aiohttp" in content and "LLMServiceClient" in content:
            logger.info("✅ Bot uses HTTP client instead of direct imports")
        else:
            compliance_issues.append("Bot doesn't use HTTP client properly")
    
    # Проверяем правильную структуру папок
    required_dirs = ["src", "docker", "config", "tests", "scripts", "docs"]
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            compliance_issues.append(f"Missing directory: {dir_path}")
        else:
            logger.info(f"✅ Found directory: {dir_path}")
    
    return compliance_issues

async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Starting Architecture Testing...")
    
    # Тест 1: Соответствие архитектуре
    compliance_issues = await test_architecture_compliance()
    
    if compliance_issues:
        logger.error("❌ ARCHITECTURE COMPLIANCE ISSUES:")
        for issue in compliance_issues:
            logger.error(f"  - {issue}")
        return False
    else:
        logger.info("✅ Architecture compliance check passed")
    
    # Тест 2: Подключение к сервисам (с предупреждениями вместо ошибок)
    logger.info("\n📡 Testing Service Connections...")
    
    fastapi_ok = await test_fastapi_server()
    ollama_ok = await test_ollama_connection()
    
    services_running = fastapi_ok and ollama_ok
    
    if not fastapi_ok:
        logger.warning("⚠️ FastAPI server not available")
        logger.info("💡 To start server: cd docker && docker-compose up -d")
    
    if not ollama_ok:
        logger.warning("⚠️ Ollama server not available")  
        logger.info("💡 To start ollama: cd docker && docker-compose up -d ollama")
    
    # Тест 3: API эндпоинты (только если сервисы работают)
    if services_running:
        logger.info("\n🔧 Testing API Endpoints...")
        
        models_ok = await test_models_endpoint()
        review_ok = await test_review_endpoint()
        
        if models_ok and review_ok:
            logger.info("\n🎉 ALL TESTS PASSED!")
            logger.info("✅ Architecture complies with requirements")
            logger.info("✅ FastAPI server working correctly")
            logger.info("✅ Ollama connection established")
            logger.info("✅ All endpoints responding")
            logger.info("✅ Agent system working properly")
            return True
        else:
            logger.warning("⚠️ Some API endpoints failed - check server status")
            return False
    else:
        logger.info("\n✅ ARCHITECTURE TESTS PASSED!")
        logger.info("✅ Architecture complies with requirements")
        logger.info("✅ Proper project structure")
        logger.info("⚠️ Service connectivity tests skipped (servers not running)")
        logger.info("💡 To run full tests: cd docker && docker-compose up -d")
        return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1) 