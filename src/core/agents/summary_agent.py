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
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
            ollama_host = "http://ollama:11434"
        else:
            ollama_host = "http://localhost:11434"
            
        self.client = ollama.AsyncClient(host=ollama_host)
        logger.info(f"SummaryAgent initialized with ollama host: {ollama_host}")
        
        # Оптимизированный системный промпт на английском
        self.system_prompt = """
        You are an expert academic paper summarizer. Create concise, informative summaries efficiently.
        
        Focus on:
        1. Main research objective and purpose
        2. Key methodology used
        3. Primary results and findings
        4. Practical significance
        
        Be precise and scholarly in your analysis.
        """
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует и суммаризирует текст статьи"""
        logger.info("Starting text summarization")
        
        try:
            # Проверяем входные данные
            if not text or not text.strip():
                logger.warning("Empty text provided for summarization")
                return {
                    "error": "Пустой текст для анализа",
                    "summary": "Текст для анализа отсутствует",
                    "key_topics": [],
                    "summary_length": 0,
                    "original_length": 0,
                }
            
            logger.info(f"Processing text snippet of {len(text)} chars (original: {len(text)})")
            
            # Генерируем суммаризацию через LLM
            summary_result = await self._generate_summary(text)
            
            # Извлекаем ключевые темы
            key_topics = self._extract_key_topics(summary_result)
            
            result = {
                "summary": summary_result.strip(),
                "key_topics": key_topics,
                "summary_length": len(summary_result),
                "original_length": len(text)
            }
            
            logger.info(f"Summarization completed. Summary length: {len(summary_result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}", exc_info=True)
            return {
                "error": str(e),
                "summary": "Ошибка при генерации резюме статьи",
                "key_topics": [],
                "summary_length": 0,
                "original_length": len(text) if text else 0
            }

    async def _generate_summary(self, text: str) -> str:
        """Быстрая генерация суммаризации через LLM"""
        
        # Компактный промпт для быстрой суммаризации
        prompt = f"""
        Summarize this academic paper focusing on key points:

        {text}

        Provide a structured summary covering:
        - Research objective and purpose
        - Methodology used
        - Main results and findings
        - Practical significance

        Keep it concise and informative.
        """
        
        try:
            response = await self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.2,  # Низкая температура для консистентности
                    "top_p": 0.8,
                    "num_predict": 400  # Ограничиваем для скорости
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error calling LLM for summarization: {e}")
            raise e
    
    def _assess_summary_quality(self, summary: str) -> str:
        """Быстрая оценка качества резюме"""
        if not summary or len(summary) < 50:
            return "poor"
        
        summary_words = len(summary.split())
        
        # Простые эвристики для быстрой оценки
        if summary_words >= 100:
            return "good"
        elif summary_words >= 50:
            return "fair"
        else:
            return "poor"
    
    def _extract_key_topics(self, summary: str) -> list:
        """Быстрое извлечение ключевых слов"""
        import re
        
        # Извлекаем значимые слова (3+ символа)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', summary.lower())
        
        # Простой подсчет частоты без стоп-слов
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Возвращаем топ-5 слов, встречающихся более 1 раза
        key_topics = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5] if freq > 1]
        return key_topics
    
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        return """
        Content Analysis Results:
        - Key topics: {key_topics}
        - Summary: {summary}
        """ 