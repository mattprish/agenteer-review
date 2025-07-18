import logging
from typing import Dict, Any
import ollama
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SummaryAgent(BaseAgent):
    """Агент для суммаризации научной статьи"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        super().__init__("SummaryAgent")
        self.model_name = model_name
        self.client = ollama.AsyncClient()
        
        # Системный промпт для суммаризации
        self.system_prompt = """
        Ты - эксперт по анализу научных статей. Твоя задача - создать качественное резюме научной статьи на русском языке.
        
        Резюме должно включать:
        1. Основную тему и цель исследования
        2. Ключевые методы исследования
        3. Главные результаты и выводы
        4. Практическую значимость работы
        
        Резюме должно быть:
        - Кратким (2-4 абзаца)
        - Точным и информативным
        - Написанным научным стилем
        - На русском языке
        
        Избегай:
        - Повторения деталей
        - Слишком технических терминов без объяснения
        - Субъективных оценок
        """
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует и суммаризирует текст статьи"""
        logger.info("Starting text summarization")
        
        try:
            # Подготавливаем промпт для суммаризации
            prompt = self._build_summarization_prompt(text, metadata)
            
            # Отправляем запрос к LLM
            summary = await self._call_llm(prompt)
            
            # Анализируем качество резюме
            summary_quality = self._assess_summary_quality(summary, text)
            
            # Определяем ключевые темы
            key_topics = self._extract_key_topics(summary)
            
            result = {
                "summary": summary,
                "summary_quality": summary_quality,
                "key_topics": key_topics,
                "summary_length": len(summary),
                "original_length": len(text),
                "compression_ratio": len(summary) / len(text) if len(text) > 0 else 0,
                "readability_score": self._calculate_readability_score(summary)
            }
            
            logger.info(f"Summarization completed. Summary length: {len(summary)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}")
            return {
                "error": str(e),
                "summary": "Ошибка при генерации резюме статьи",
                "summary_quality": "poor",
                "key_topics": [],
                "summary_length": 0,
                "compression_ratio": 0,
                "readability_score": 0.0
            }
    
    def _build_summarization_prompt(self, text: str, metadata: Dict[str, Any]) -> str:
        """Строит промпт для суммаризации"""
        title = metadata.get('title', 'Научная статья')
        author = metadata.get('author', 'Автор не указан')
        page_count = metadata.get('page_count', 'неизвестно')
        
        prompt = f"""
        Проанализируй и создай качественное резюме следующей научной статьи:
        
        Название: {title}
        Автор: {author}
        Количество страниц: {page_count}
        
        Текст статьи:
        {text[:8000]}  # Ограничиваем длину для эффективности
        
        Создай структурированное резюме, которое поможет читателю быстро понять:
        - О чем эта статья и зачем она написана
        - Какие методы использовались в исследовании
        - Какие получены результаты и выводы
        - В чем практическая ценность работы
        
        Резюме должно быть написано на русском языке в научном стиле.
        """
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Вызывает LLM для генерации резюме"""
        try:
            response = await self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 800
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error calling LLM for summarization: {e}")
            raise e
    
    def _assess_summary_quality(self, summary: str, original_text: str) -> str:
        """Оценивает качество резюме"""
        if not summary or len(summary) < 50:
            return "poor"
        
        # Простая эвристика на основе длины и структуры
        summary_words = len(summary.split())
        original_words = len(original_text.split())
        
        if summary_words == 0:
            return "poor"
        
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        # Проверяем структурированность (наличие ключевых слов)
        key_indicators = [
            "исследование", "результат", "вывод", "метод", "анализ",
            "цель", "задача", "практический", "значимость", "работа"
        ]
        
        found_indicators = sum(1 for indicator in key_indicators 
                             if indicator in summary.lower())
        
        # Оценка качества
        if (0.05 <= compression_ratio <= 0.3 and 
            found_indicators >= 3 and 
            summary_words >= 100):
            return "excellent"
        elif (0.03 <= compression_ratio <= 0.4 and 
              found_indicators >= 2 and 
              summary_words >= 50):
            return "good"
        elif summary_words >= 30 and found_indicators >= 1:
            return "fair"
        else:
            return "poor"
    
    def _extract_key_topics(self, summary: str) -> list:
        """Извлекает ключевые темы из резюме"""
        # Простое извлечение ключевых слов
        import re
        
        # Удаляем стоп-слова и короткие слова
        stop_words = {
            'в', 'на', 'с', 'по', 'для', 'из', 'к', 'о', 'и', 'а', 'но', 'или',
            'что', 'как', 'это', 'того', 'этого', 'была', 'были', 'было', 'есть',
            'будет', 'может', 'должен', 'должна', 'должно', 'также', 'более',
            'менее', 'очень', 'весьма', 'довольно', 'совсем'
        }
        
        words = re.findall(r'\b[а-яё]+\b', summary.lower())
        
        # Фильтруем и подсчитываем частоту
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Возвращаем топ-5 ключевых слов
        key_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in key_topics]
    
    def _calculate_readability_score(self, text: str) -> float:
        """Вычисляет простую оценку читаемости"""
        if not text:
            return 0.0
        
        # Простая эвристика на основе длины предложений и слов
        sentences = text.split('.')
        words = text.split()
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Нормализуем оценку (оптимальная длина предложения 15-20 слов, слова 5-7 букв)
        sentence_score = max(0, 1 - abs(avg_sentence_length - 17.5) / 17.5)
        word_score = max(0, 1 - abs(avg_word_length - 6) / 6)
        
        return (sentence_score + word_score) / 2
    
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        return """
        Based on the summary analysis:
        - Summary: {summary}
        - Summary quality: {summary_quality}
        - Key topics: {key_topics}
        - Compression ratio: {compression_ratio:.2f}
        - Readability score: {readability_score:.2f}
        
        Evaluate the content and clarity of this academic paper summary.
        """ 