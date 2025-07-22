#!/usr/bin/env python3
"""
Тест для проверки извлечения финального ответа после тега </think>
"""

import sys
import os

# Добавляем src директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from core.orchestrator import Orchestrator

def test_extract_final_response():
    """Тестирует извлечение финального ответа"""
    
    print("🧪 Тестирование извлечения финального ответа")
    print("=" * 50)
    
    orchestrator = Orchestrator()
    
    # Тест 1: Ответ с тегом </think>
    content_with_think = """
    <think>
    Okay, let me analyze this paper carefully. I need to look at the structure, methodology, and results. The paper seems to be about machine learning applications...
    </think>
    
    Paper Analysis Report
    
    Overall assessment: This paper presents a solid contribution to the machine learning field with clear methodology and strong results.
    
    Strengths:
    - Well-structured experimental design
    - Comprehensive evaluation metrics
    - Clear presentation of results
    
    Weaknesses:
    - Limited discussion of limitations
    - Could benefit from more baseline comparisons
    
    Recommendations:
    - Add more detailed error analysis
    - Include computational complexity discussion
    - Expand the related work section
    """
    
    result1 = orchestrator._extract_final_response(content_with_think)
    
    expected_content = "Paper Analysis Report"
    if expected_content in result1 and "think>" not in result1:
        print("✅ Тест 1 пройден: Контент после </think> извлечен корректно")
        print(f"   Извлечено: {len(result1)} символов")
    else:
        print("❌ Тест 1 не пройден")
        print(f"   Ожидался контент содержащий: {expected_content}")
        print(f"   Получено: {result1[:100]}...")
    
    # Тест 2: Ответ без тега </think>
    content_without_think = """
    Paper Analysis Report
    
    Overall assessment: This paper presents innovative research methodology.
    
    Strengths:
    - Novel approach to data analysis
    - Strong theoretical foundation
    """
    
    result2 = orchestrator._extract_final_response(content_without_think)
    
    if result2 == content_without_think.strip():
        print("✅ Тест 2 пройден: Контент без </think> возвращен полностью")
    else:
        print("❌ Тест 2 не пройден")
    
    # Тест 3: Несколько тегов </think>
    content_multiple_think = """
    <think>
    First analysis pass...
    </think>
    
    Some intermediate content
    
    <think>
    Second analysis pass, deeper review...
    </think>
    
    Final Review:
    This is the actual review that should be shown to the user.
    """
    
    result3 = orchestrator._extract_final_response(content_multiple_think)
    
    if "Final Review:" in result3 and "First analysis" not in result3:
        print("✅ Тест 3 пройден: Извлечен контент после последнего </think>")
    else:
        print("❌ Тест 3 не пройден")
        print(f"   Результат: {result3}")
    
    # Тест 4: Пустой контент после </think>
    content_empty_after_think = """
    <think>
    Some analysis here...
    </think>
    """
    
    result4 = orchestrator._extract_final_response(content_empty_after_think)
    
    if "Some analysis here..." in result4:
        print("✅ Тест 4 пройден: При пустом контенте после </think> возвращен весь контент")
    else:
        print("❌ Тест 4 не пройден")
    
    print("\n🎯 Тестирование завершено!")

if __name__ == "__main__":
    test_extract_final_response() 