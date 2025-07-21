import logging
import os
from typing import Dict, Any
import ollama
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SummaryAgent(BaseAgent):
    """Агент для суммаризации научной статьи"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        super().__init__("SummaryAgent")
        self.model_name = model_name
        
        # Определяем хост для ollama в зависимости от окружения
        # В Docker используем ollama:11434, локально - localhost:11434
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
            ollama_host = "http://ollama:11434"
        else:
            ollama_host = "http://localhost:11434"
            
        self.client = ollama.AsyncClient(host=ollama_host)
        logger.info(f"SummaryAgent initialized with ollama host: {ollama_host}")
        
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
            # Умное ограничение текста: берем первые 6000 символов и последние 2000
            # Это сохраняет введение и выводы
            if len(text) > 8000:
                text_for_summary = text[:6000] + "\n\n...[текст сокращен]...\n\n" + text[-2000:]
            else:
                text_for_summary = text
            
            # Подготавливаем промпт для суммаризации
            prompt = self._build_summarization_prompt(text_for_summary, metadata)
            
            # Отправляем запрос к LLM
            summary = await self._call_llm(prompt)
            
            # Простая оценка качества резюме
            summary_quality = self._assess_summary_quality(summary)
            
            # Извлекаем ключевые темы простым способом
            key_topics = self._extract_key_topics(summary)
            
            result = {
                "summary": summary,
                "summary_quality": summary_quality,
                "key_topics": key_topics,
                "summary_length": len(summary),
                "original_length": len(text),
                "compression_ratio": round(len(summary) / len(text) if len(text) > 0 else 0, 3)
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
                "compression_ratio": 0
            }
    
    def _build_summarization_prompt(self, text: str, metadata: Dict[str, Any]) -> str:
        """Строит промпт для суммаризации"""
        title = metadata.get('title', 'Научная статья')
        author = metadata.get('author', 'Автор не указан')
        
        prompt = f"""
        Проанализируй и создай качественное резюме следующей научной статьи:
        
        Название: {title}
        Автор: {author}
        
        Текст статьи:
        {text}
        
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
                    "num_predict": 800  # Ограничиваем длину ответа
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error calling LLM for summarization: {e}")
            raise e
    
    def _assess_summary_quality(self, summary: str) -> str:
        """Простая оценка качества резюме"""
        if not summary or len(summary) < 50:
            return "poor"
        
        summary_words = len(summary.split())
        
        # Проверяем наличие ключевых научных слов
        key_indicators = [
            "исследование", "результат", "вывод", "метод", "анализ",
            "цель", "задача", "работа", "данные", "показать"
        ]
        
        found_indicators = sum(1 for indicator in key_indicators 
                             if indicator in summary.lower())
        
        # Простая оценка на основе длины и ключевых слов
        if summary_words >= 150 and found_indicators >= 4:
            return "excellent"
        elif summary_words >= 100 and found_indicators >= 3:
            return "good"
        elif summary_words >= 50 and found_indicators >= 2:
            return "fair"
        else:
            return "poor"
    
    def _extract_key_topics(self, summary: str) -> list:
        """Простое извлечение ключевых слов из резюме"""
        # Убираем стоп-слова и короткие слова
        stop_words = {
            'что', 'как', 'это', 'был', 'были', 'была', 'было', 'есть', 'будет', 
            'может', 'должен', 'также', 'более', 'менее', 'очень', 'довольно'
        }
        
        import re
        words = re.findall(r'\b[а-яё]{4,}\b', summary.lower())
        
        # Подсчитываем частоту значимых слов
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Возвращаем топ-5 ключевых слов
        key_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in key_topics if freq > 1]  # Только слова, встречающиеся более 1 раза
    
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        return """
        Based on the summary analysis:
        - Summary: {summary}
        - Summary quality: {summary_quality}
        - Key topics: {key_topics}
        - Compression ratio: {compression_ratio}
        
        Evaluate the content and clarity of this academic paper summary.
        """ 