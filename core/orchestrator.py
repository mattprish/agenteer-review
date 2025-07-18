import asyncio
import logging
import json
from typing import Dict, Any, List
import ollama
from .agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """Оркестратор для управления процессом рецензирования"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name
        self.agents: Dict[str, BaseAgent] = {}
        self.client = ollama.AsyncClient()
        logger.info(f"Orchestrator initialized with model: {model_name}")
        
        # Системный промпт для оркестратора
        self.system_prompt = """
        You are an academic paper review coordinator. Your task is to:
        1. Analyze results from specialized agents
        2. Generate a concise, constructive review
        3. Provide specific recommendations
        
        Format your response as a structured review with:
        - Overall Assessment (1-2 sentences)
        - Strengths (2-3 bullet points)
        - Weaknesses (2-3 bullet points)
        - Specific Recommendations (2-3 actionable items)
        
        Be constructive and professional in your feedback.
        """
    
    def register_agent(self, name: str, agent: BaseAgent):
        """Регистрирует агента в системе"""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    async def process_paper(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной метод обработки статьи
        
        Args:
            text: Текст статьи
            metadata: Метаданные статьи
            
        Returns:
            Dict: Результаты анализа и рецензия
        """
        logger.info("Starting paper processing")
        
        try:
            # 1. Запуск всех зарегистрированных агентов
            agent_results = await self._run_agents(text, metadata)
            
            # 2. Генерация финального отчета
            final_review = await self._generate_final_review(agent_results, metadata)
            
            # 3. Формирование результата
            result = {
                "agent_results": agent_results,
                "final_review": final_review,
                "metadata": metadata,
                "processing_status": "success"
            }
            
            logger.info("Paper processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in paper processing: {e}")
            return {
                "agent_results": {},
                "final_review": f"Ошибка при обработке статьи: {str(e)}",
                "metadata": metadata,
                "processing_status": "error",
                "error": str(e)
            }
    
    async def _run_agents(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает всех зарегистрированных агентов параллельно"""
        if not self.agents:
            logger.warning("No agents registered")
            return {}
        
        logger.info(f"Running {len(self.agents)} agents")
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        agent_names = []
        
        for name, agent in self.agents.items():
            task = asyncio.create_task(agent.analyze(text, metadata))
            tasks.append(task)
            agent_names.append(name)
        
        # Ждем завершения всех задач
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты
        agent_results = {}
        for name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} failed: {result}")
                agent_results[name] = {"error": str(result)}
            else:
                agent_results[name] = result
                logger.info(f"Agent {name} completed successfully")
        
        return agent_results
    
    async def _generate_final_review(self, agent_results: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Генерирует финальную рецензию на основе результатов агентов"""
        logger.info("Generating final review")
        
        try:
            # Формируем промпт для LLM
            prompt = self._build_review_prompt(agent_results, metadata)
            
            # Отправляем запрос к LLM
            response = await self._call_llm(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating final review: {e}")
            return self._generate_fallback_review(agent_results)
    
    def _build_review_prompt(self, agent_results: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Строит промпт для генерации финальной рецензии"""
        prompt_parts = [
            "Please generate a comprehensive review of this academic paper based on the following analysis:",
            f"\nPaper metadata:",
            f"- Title: {metadata.get('title', 'Unknown')}",
            f"- Pages: {metadata.get('page_count', 'Unknown')}",
            f"- Author: {metadata.get('author', 'Unknown')}",
        ]
        
        # Добавляем результаты агентов
        for agent_name, results in agent_results.items():
            if "error" not in results:
                prompt_parts.append(f"\n{agent_name.upper()} ANALYSIS:")
                
                if agent_name == "StructureAgent":
                    prompt_parts.append(f"- Found sections: {results.get('found_sections', [])}")
                    prompt_parts.append(f"- Missing sections: {results.get('missing_sections', [])}")
                    prompt_parts.append(f"- Structure quality: {results.get('structure_quality', 'unknown')}")
                    prompt_parts.append(f"- Completeness score: {results.get('completeness_score', 0):.2f}")
                    prompt_parts.append(f"- Recommendations: {results.get('recommendations', [])}")
                
                elif agent_name == "SummaryAgent":
                    prompt_parts.append(f"- Summary: {results.get('summary', 'No summary available')}")
                    prompt_parts.append(f"- Summary quality: {results.get('summary_quality', 'unknown')}")
                    prompt_parts.append(f"- Key topics: {results.get('key_topics', [])}")
                    prompt_parts.append(f"- Compression ratio: {results.get('compression_ratio', 0):.2f}")
                    prompt_parts.append(f"- Readability score: {results.get('readability_score', 0):.2f}")
        
        prompt_parts.append("\nGenerate a professional academic review.")
        
        return "\n".join(prompt_parts)
    
    async def _call_llm(self, prompt: str) -> str:
        """Вызывает LLM для генерации ответа"""
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
                    "max_tokens": 1000
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise e
    
    def _generate_fallback_review(self, agent_results: Dict[str, Any]) -> str:
        """Генерирует базовую рецензию без использования LLM"""
        logger.info("Generating fallback review")
        
        review_parts = ["# Автоматическая рецензия статьи\n"]
        
        # Анализируем результаты Structure Agent
        if "StructureAgent" in agent_results:
            structure_results = agent_results["StructureAgent"]
            
            if "error" not in structure_results:
                review_parts.append("## Анализ структуры")
                
                found_sections = structure_results.get('found_sections', [])
                missing_sections = structure_results.get('missing_sections', [])
                quality = structure_results.get('structure_quality', 'unknown')
                
                review_parts.append(f"**Найденные разделы:** {', '.join(found_sections) if found_sections else 'Не найдены'}")
                review_parts.append(f"**Отсутствующие разделы:** {', '.join(missing_sections) if missing_sections else 'Все основные разделы присутствуют'}")
                review_parts.append(f"**Качество структуры:** {quality}")
                
                recommendations = structure_results.get('recommendations', [])
                if recommendations:
                    review_parts.append("\n**Рекомендации по структуре:**")
                    for rec in recommendations:
                        review_parts.append(f"- {rec}")
        
        # Анализируем результаты Summary Agent
        if "SummaryAgent" in agent_results:
            summary_results = agent_results["SummaryAgent"]
            
            if "error" not in summary_results:
                review_parts.append("\n## Анализ содержания")
                
                summary = summary_results.get('summary', '')
                quality = summary_results.get('summary_quality', 'unknown')
                key_topics = summary_results.get('key_topics', [])
                compression_ratio = summary_results.get('compression_ratio', 0)
                
                if summary:
                    review_parts.append("**Резюме статьи:**")
                    review_parts.append(summary)
                
                review_parts.append(f"\n**Качество изложения:** {quality}")
                review_parts.append(f"**Ключевые темы:** {', '.join(key_topics) if key_topics else 'Не определены'}")
                review_parts.append(f"**Сжатие текста:** {compression_ratio:.1%}")
        
        # Общие выводы
        review_parts.append("\n## Общие выводы")
        review_parts.append("Статья была проанализирована автоматической системой. Для полной оценки рекомендуется дополнительная экспертная проверка.")
        
        return "\n".join(review_parts)
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверяет работоспособность системы"""
        health_status = {
            "orchestrator": "ok",
            "agents": {},
            "llm": "unknown"
        }
        
        # Проверяем агентов
        for name, agent in self.agents.items():
            try:
                # Простая проверка агента
                health_status["agents"][name] = "ok"
            except Exception as e:
                health_status["agents"][name] = f"error: {e}"
        
        # Проверяем LLM
        try:
            test_response = await self._call_llm("Test message")
            health_status["llm"] = "ok"
        except Exception as e:
            health_status["llm"] = f"error: {e}"
        
        return health_status 