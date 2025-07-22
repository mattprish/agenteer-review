import logging
import os
from typing import Dict, Any
import ollama
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class StructureAgent(BaseAgent):
    """Агент для анализа структуры научной статьи с использованием LLM"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
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
    
    async def analyze(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует структуру статьи с помощью LLM"""
        logger.info("Starting LLM-based structure analysis")
        
        try:
            # Проверяем входные данные
            if not text or not text.strip():
                logger.warning("Empty text provided for structure analysis")
                return {
                    "error": "Пустой текст для анализа структуры",
                    "found_sections": [],
                    "missing_sections": [],
                    "structure_quality": "poor",
                    "coherence_score": 0.0,
                    "completeness_score": 0.0,
                    "recommendations": ["Загрузите текст статьи для анализа структуры"]
                }
            
            logger.info(f"Analyzing structure with LLM ({len(text)} chars from {len(text)} original)")
            
            # Генерируем анализ через LLM
            analysis_result = await self._analyze_with_llm(text)
            
            logger.info("Structure analysis completed")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in structure analysis: {e}", exc_info=True)
            return {
                "error": str(e),
                "found_sections": [],
                "missing_sections": [],
                "structure_quality": "poor",
                "coherence_score": 0.0,
                "completeness_score": 0.0,
                "recommendations": ["Произошла ошибка при анализе структуры"]
            }
    
    async def _analyze_with_llm(self, text: str) -> Dict[str, Any]:
        """Оптимизированный анализ структуры с помощью LLM"""
        
        # Компактный промпт для быстрого анализа
        prompt = f"""
        Analyze this academic paper structure:

        {text}

        Respond in exact format:

        FOUND_SECTIONS: list sections found (e.g., abstract,introduction,methods,results,discussion,conclusion,references)

        MISSING_SECTIONS: list key missing sections

        QUALITY: one word (excellent/good/fair/poor)

        COHERENCE: score 0.0-1.0

        COMPLETENESS: score 0.0-1.0

        RECOMMENDATIONS:
        - specific recommendation 1
        - specific recommendation 2
        """
        
        try:
            response = await self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.1,  # Очень низкая температура для скорости и консистентности
                    "top_p": 0.7,
                    "num_predict": 1000  # Сильно ограничиваем для скорости
                }
            )
            
            return response['message']['content']
            
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