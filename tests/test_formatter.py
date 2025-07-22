#!/usr/bin/env python3
"""
Тест для проверки форматирования рецензий
"""

import sys
import os

# Добавляем src директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from utils.formatters import format_review

def test_review_formatting():
    """Тестирует форматирование рецензий"""
    
    print("🧪 Тестирование форматирования рецензий")
    print("=" * 50)
    
    # Тест 1: Базовое форматирование с финальной рецензией
    results_with_review = {
        "processing_status": "success",
        "final_review": "This is a test review with detailed analysis and recommendations.",
        "agent_results": {
            "StructureAgent": {
                "status": "success",
                "result": "Structure analysis completed successfully"
            }
        }
    }
    
    metadata = {
        "title": "Test Paper",
        "author": "Test Author",
        "page_count": 10
    }
    
    # Тест с verbose=False (по умолчанию)
    formatted_basic = format_review(results_with_review, metadata, verbose=False)
    
    if "This is a test review" in formatted_basic and "📝 *Рецензия:*" in formatted_basic:
        print("✅ Тест 1 пройден: Финальная рецензия отображается в базовом режиме")
    else:
        print("❌ Тест 1 не пройден: Финальная рецензия не отображается")
        print(f"   Результат: {formatted_basic}")
    
    # Тест 2: Проверяем, что без рецензии не падает
    results_no_review = {
        "processing_status": "success",
        "final_review": "",
        "agent_results": {}
    }
    
    formatted_no_review = format_review(results_no_review, metadata, verbose=False)
    
    if "📄 *Автоматическая рецензия" in formatted_no_review:
        print("✅ Тест 2 пройден: Форматирование работает без рецензии")
    else:
        print("❌ Тест 2 не пройден")
    
    # Тест 3: Проверяем verbose режим
    formatted_verbose = format_review(results_with_review, metadata, verbose=True)
    
    if "🔍 *Детальный анализ агентов:*" in formatted_verbose and "This is a test review" in formatted_verbose:
        print("✅ Тест 3 пройден: Verbose режим работает корректно")
    else:
        print("❌ Тест 3 не пройден")
    
    # Тест 4: Ошибка обработки
    results_error = {
        "processing_status": "error",
        "error": "Test error message"
    }
    
    formatted_error = format_review(results_error, metadata)
    
    if "❌ *Произошла ошибка" in formatted_error and "Test error message" in formatted_error:
        print("✅ Тест 4 пройден: Ошибки форматируются корректно")
    else:
        print("❌ Тест 4 не пройден")
    
    print("\n🎯 Тестирование форматирования завершено!")

if __name__ == "__main__":
    test_review_formatting() 