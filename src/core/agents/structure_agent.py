import logging
import os
import asyncio
from typing import Dict, Any
import ollama
from .base_agent import BaseAgent
TIMER_FOR_LLM_CALL = 180.0
NUM_PREDICT_FOR_LLM_CALL = 1000

logger = logging.getLogger(__name__)

class StructureAgent(BaseAgent):
    """Агент для анализа структуры научной статьи с использованием LLM"""
    
    def __init__(self, model_name: str = "qwen3:4b"):
        super().__init__("StructureAgent")
        self.model_name = model_name
        
        # Определяем хост для ollama в зависимости от окружения
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
            ollama_host = "http://ollama:11434"
        else:
            ollama_host = "http://localhost:11434"
            
        self.client = ollama.AsyncClient(host=ollama_host)
        logger.info(f"StructureAgent initialized with ollama host: {ollama_host}")
        
        # Оптимизированный системный промпт на английском
        self.system_prompt = """
        You are an expert academic paper structure analyzer. Evaluate paper organization efficiently.
        
        Analyze:
        1. Key sections presence (intro, methods, results, discussion, conclusion)
        2. Logical flow and coherence
        3. Academic standards compliance
        
        Be precise and structured in responses.
        """
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> str:
        """Анализирует структуру статьи с помощью LLM"""
        logger.info("Starting LLM-based structure analysis")
        
        try:
            # Проверяем входные данные
            if not text or not text.strip():
                logger.warning("Empty text provided for structure analysis")
                return "ERROR: Empty text provided for structure analysis"
            
            logger.info(f"Analyzing structure with LLM ({len(text)} chars)")
            
            # Генерируем анализ через LLM с таймаутом
            analysis_result = await self._analyze_with_llm(text)
            
            logger.info("Structure analysis completed")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in structure analysis: {e}", exc_info=True)
            return f"ERROR: Structure analysis failed - {str(e)}"
    
    async def _analyze_with_llm(self, text: str) -> str:
        """Оптимизированный анализ структуры с помощью LLM"""
        
        # Компактный промпт для быстрого анализа
        prompt = f"""
        Analyze this academic paper structure briefly:

        {text}

        Respond in this format:

        SECTIONS: list found sections
        MISSING: key missing sections
        QUALITY: excellent/good/fair/poor
        COHERENCE: 0.0-1.0
        RECOMMENDATIONS: 2-3 specific suggestions

        Be concise.
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
                        "temperature": 0.1,  # Очень низкая температура для скорости
                        "top_p": 0.7,
                        "num_predict": NUM_PREDICT_FOR_LLM_CALL,  # Еще меньше токенов для скорости
                        "stop": ["\n\n\n"]  # Останавливаем на двойных переносах
                    }
                ),
                timeout=TIMER_FOR_LLM_CALL
            )
            
            return response['message']['content']
            
        except asyncio.TimeoutError:
            logger.error("LLM call timeout in structure analysis")
            return "ERROR: Structure analysis timed out"
        except Exception as e:
            logger.error(f"Error calling LLM for structure analysis: {e}")
            raise e
    
    def get_prompt_template(self) -> str:
        """Возвращает шаблон промпта для оркестратора"""
        return """
        Structure Analysis Results:
        - Found sections: {found_sections}
        - Missing sections: {missing_sections} 
        - Quality: {structure_quality}
        - Coherence: {coherence_score}
        - Completeness: {completeness_score}
        - Recommendations: {recommendations}
        """ 