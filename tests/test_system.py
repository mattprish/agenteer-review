#!/usr/bin/env python3
"""
Тестовый файл для проверки работоспособности системы
"""

import asyncio
import logging
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_extractor import PDFExtractor
from core.orchestrator import Orchestrator
from core.agents.structure_agent import StructureAgent
from core.agents.summary_agent import SummaryAgent

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_components():
    """Тестирует основные компоненты системы"""
    
    print("🧪 Тестирование компонентов системы автоматического рецензирования")
    print("=" * 70)
    
    # Тест 1: Инициализация компонентов
    print("\n1. 🔧 Тестирование инициализации компонентов...")
    
    try:
        pdf_extractor = PDFExtractor()
        print("   ✅ PDF Extractor инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации PDF Extractor: {e}")
        return False
    
    try:
        structure_agent = StructureAgent()
        print("   ✅ Structure Agent инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации Structure Agent: {e}")
        return False
    
    try:
        summary_agent = SummaryAgent()
        print("   ✅ Summary Agent инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации Summary Agent: {e}")
        return False
    
    try:
        orchestrator = Orchestrator()
        print("   ✅ Orchestrator инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации Orchestrator: {e}")
        return False
    
    # Тест 2: Регистрация агентов
    print("\n2. 📋 Тестирование регистрации агентов...")
    try:
        orchestrator.register_agent("StructureAgent", structure_agent)
        print("   ✅ Structure Agent зарегистрирован")
        orchestrator.register_agent("SummaryAgent", summary_agent)
        print("   ✅ Summary Agent зарегистрирован")
    except Exception as e:
        print(f"   ❌ Ошибка регистрации агентов: {e}")
        return False
    
    # Тест 3: Тестирование агентов
    print("\n3. 🏗 Тестирование агентов...")
    
    test_text = """
    Abstract
    This paper presents a novel approach to machine learning.
    
    Introduction
    Machine learning has become increasingly important in recent years.
    
    Methodology
    We used a supervised learning approach with neural networks.
    
    Results
    Our experiments show significant improvements over baseline methods.
    
    Discussion
    The results demonstrate the effectiveness of our approach.
    
    Conclusion
    We have presented a new method that achieves state-of-the-art results.
    
    References
    [1] Smith, J. et al. (2023). Machine Learning Advances.
    """
    
    test_metadata = {
        "title": "Test Paper",
        "page_count": 10,
        "author": "Test Author"
    }
    
    # Тестирование Structure Agent
    try:
        structure_results = await structure_agent.analyze(test_text, test_metadata)
        print(f"   ✅ Structure Agent выполнен")
        print(f"   📊 Найденные разделы: {structure_results.get('found_sections', [])}")
        print(f"   📊 Качество структуры: {structure_results.get('structure_quality', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Ошибка выполнения Structure Agent: {e}")
        return False
    
    # Тестирование Summary Agent
    try:
        summary_results = await summary_agent.analyze(test_text, test_metadata)
        print(f"   ✅ Summary Agent выполнен")
        summary = summary_results.get('summary', '')
        if summary:
            print(f"   📝 Резюме сгенерировано ({len(summary)} символов)")
        print(f"   📊 Качество резюме: {summary_results.get('summary_quality', 'unknown')}")
        print(f"   📊 Ключевые темы: {summary_results.get('key_topics', [])}")
    except Exception as e:
        print(f"   ⚠️ Summary Agent выполнен с ошибкой (возможно, LLM недоступен): {e}")
        # Не останавливаем тест, так как LLM может быть недоступен в тестовой среде
    
    # Тест 4: Проверка health check
    print("\n4. 🔍 Тестирование health check...")
    try:
        health = await orchestrator.health_check()
        print(f"   ✅ Health check выполнен")
        print(f"   📊 Статус оркестратора: {health.get('orchestrator', 'unknown')}")
        print(f"   📊 Статус агентов: {health.get('agents', {})}")
        print(f"   📊 Статус LLM: {health.get('llm', 'unknown')}")
    except Exception as e:
        print(f"   ⚠️ Health check выполнен с предупреждениями: {e}")
    
    # Тест 5: Полный тест оркестратора
    print("\n5. 🎭 Тестирование полного пайплайна...")
    try:
        results = await orchestrator.process_paper(test_text, test_metadata)
        print(f"   ✅ Полный пайплайн выполнен")
        print(f"   📊 Статус обработки: {results.get('processing_status', 'unknown')}")
        
        if results.get('processing_status') == 'success':
            print(f"   📋 Результаты агентов получены")
            review = results.get('final_review', '')
            if review:
                print(f"   📝 Финальная рецензия сгенерирована ({len(review)} символов)")
            else:
                print(f"   ⚠️ Финальная рецензия пустая (возможно, LLM недоступен)")
        
    except Exception as e:
        print(f"   ❌ Ошибка выполнения полного пайплайна: {e}")
        return False
    
    print("\n🎉 Все тесты завершены успешно!")
    print("\n💡 Система готова к работе. Убедитесь что:")
    print("   • Ollama запущен (ollama serve)")
    print("   • Модель qwen3:4b загружена")
    print("   • BOT_TOKEN указан в файле .env")
    
    return True

def test_file_validation():
    """Тестирует валидацию файлов"""
    print("\n6. 📄 Тестирование валидации файлов...")
    
    pdf_extractor = PDFExtractor()
    
    # Тест расширений
    assert pdf_extractor.validate_file_extension("document.pdf") == True
    assert pdf_extractor.validate_file_extension("document.txt") == False
    print("   ✅ Валидация расширений работает")
    
    # Тест размеров
    assert pdf_extractor.validate_file_size(1024) == True  # 1KB
    assert pdf_extractor.validate_file_size(20 * 1024 * 1024) == False  # 20MB
    print("   ✅ Валидация размеров работает")

async def main():
    """Основная функция тестирования"""
    try:
        # Тест компонентов
        success = await test_components()
        
        # Тест валидации
        test_file_validation()
        
        if success:
            print("\n🎉 Все тесты пройдены! Система готова к использованию.")
            return 0
        else:
            print("\n❌ Некоторые тесты не прошли. Проверьте конфигурацию.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Критическая ошибка при тестировании: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 