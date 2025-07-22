import logging
import os
import asyncio
from typing import Dict, Any
import ollama
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SummaryAgent(BaseAgent):
    """Агент для суммаризации научной статьи"""
    
    def __init__(self, model_name: str = "qwen3:4b"):
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
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> str:
        """Анализирует и суммаризирует текст статьи"""
        logger.info("Starting text summarization")
        
        try:
            # Проверяем входные данные
            if not text or not text.strip():
                logger.warning("Empty text provided for summarization")
                return "ERROR: Empty text provided for summarization"
            
            # Ограничиваем размер текста для быстрой обработки
            max_chars = 8000  # Значительно меньше для скорости
            if len(text) > max_chars:
                text = text[:max_chars] + "... [text truncated for faster processing]"
            
            logger.info(f"Processing text snippet of {len(text)} chars")
            
            # Генерируем суммаризацию через LLM с таймаутом
            summary_result = await self._generate_summary(text)
            
            logger.info(f"Summarization completed. Summary length: {len(summary_result)} chars")
            return summary_result
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}", exc_info=True)
            return f"ERROR: Summarization failed - {str(e)}"

    async def _generate_summary(self, text: str) -> str:
        """Быстрая генерация суммаризации через LLM"""
        
        # Компактный промпт для быстрой суммаризации
        prompt = f"""
        Summarize this academic paper briefly:

        {text}

        Provide:
        - Research objective
        - Methodology
        - Main results
        - Significance

        Keep it concise and informative.
        """
        
        try:
            # Добавляем агрессивный таймаут на вызов LLM
            response = await asyncio.wait_for(
                self.client.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    options={
                        "temperature": 0.2,  # Низкая температура для консистентности
                        "top_p": 0.8,
                        "num_predict": 300,  # Ограничиваем для скорости
                        "stop": ["\n\n\n"]  # Останавливаем на двойных переносах
                    }
                ),
                timeout=30.0  # 30 секунд максимум на LLM вызов
            )
            
            return response['message']['content']
            
        except asyncio.TimeoutError:
            logger.error("LLM call timeout in summarization")
            return "ERROR: Summarization timed out"
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