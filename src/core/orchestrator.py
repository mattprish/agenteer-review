import asyncio
import logging
import json
import os
from typing import Dict, Any, List
import ollama
from .agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """Оркестратор для управления процессом рецензирования"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name
        self.agents: Dict[str, BaseAgent] = {}
        
        # Определяем хост для ollama в зависимости от окружения
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
            ollama_host = "http://ollama:11434"
        else:
            ollama_host = "http://localhost:11434"
            
        self.client = ollama.AsyncClient(host=ollama_host)
        logger.info(f"Orchestrator initialized with model: {model_name}, ollama host: {ollama_host}")
        
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
        Write the review in Russian language.
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
            # 1. Запуск всех зарегистрированных агентов параллельно
            agent_results = await self._run_agents_parallel(text, metadata)
            
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
    
    async def _run_agents_parallel(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запускает всех агентов параллельно для повышения производительности
        
        Args:
            text: Текст статьи
            metadata: Метаданные
            
        Returns:
            Dict: Результаты работы всех агентов
        """
        logger.info(f"Running {len(self.agents)} agents in parallel")
        
        if not self.agents:
            logger.warning("No agents registered")
            return {}
        
        # Создаем задачи для всех агентов
        tasks = []
        agent_names = []
        
        for name, agent in self.agents.items():
            task = asyncio.create_task(
                self._run_single_agent(agent, text, metadata, name)
            )
            tasks.append(task)
            agent_names.append(name)
        
        # Ждем завершения всех задач
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты
        agent_results = {}
        for i, (name, result) in enumerate(zip(agent_names, results)):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} failed: {result}")
                agent_results[name] = {
                    "error": str(result),
                    "status": "failed"
                }
            else:
                agent_results[name] = result
                agent_results[name]["status"] = "success"
        
        logger.info(f"Completed {len(agent_results)} agent tasks")
        return agent_results
    
    async def _run_single_agent(self, agent: BaseAgent, text: str, metadata: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """
        Запускает отдельного агента
        
        Args:
            agent: Экземпляр агента
            text: Текст для анализа
            metadata: Метаданные
            agent_name: Имя агента для логирования
            
        Returns:
            Dict: Результат работы агента
        """
        try:
            logger.info(f"Starting agent: {agent_name}")
            result = await agent.analyze(text, metadata)
            logger.info(f"Agent {agent_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            raise e
    
    async def _generate_final_review(self, agent_results: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        Генерирует финальную рецензию на основе результатов агентов
        
        Args:
            agent_results: Результаты работы агентов
            metadata: Метаданные статьи
            
        Returns:
            str: Финальная рецензия
        """
        logger.info("Generating final review")
        
        try:
            # Подготавливаем данные для промпта
            summary_data = self._prepare_agent_summary(agent_results)
            
            # Создаем промпт для финальной рецензии
            prompt = self._build_final_review_prompt(summary_data, metadata)
            
            # Генерируем рецензию через LLM
            review = await self._call_llm_for_review(prompt)
            
            return review
            
        except Exception as e:
            logger.error(f"Error generating final review: {e}")
            return f"Ошибка при генерации финальной рецензии: {str(e)}"
    
    def _prepare_agent_summary(self, agent_results: Dict[str, Any]) -> str:
        """
        Подготавливает сводку результатов агентов для финального промпта
        
        Args:
            agent_results: Результаты работы агентов
            
        Returns:
            str: Сводка результатов
        """
        summary_parts = []
        
        for agent_name, result in agent_results.items():
            if result.get("status") == "failed":
                summary_parts.append(f"• {agent_name}: Анализ не удался - {result.get('error', 'Неизвестная ошибка')}")
                continue
            
            if agent_name == "StructureAgent":
                structure_score = result.get("structure_score", "unknown")
                missing_sections = result.get("missing_sections", [])
                summary_parts.append(f"• Структурный анализ: оценка {structure_score}/10")
                if missing_sections:
                    summary_parts.append(f"  - Отсутствующие разделы: {', '.join(missing_sections)}")
            
            elif agent_name == "SummaryAgent":
                summary_quality = result.get("summary_quality", "unknown")
                key_topics = result.get("key_topics", [])
                summary_parts.append(f"• Анализ содержания: качество резюме - {summary_quality}")
                if key_topics:
                    summary_parts.append(f"  - Ключевые темы: {', '.join(key_topics[:3])}")
        
        return "\n".join(summary_parts)
    
    def _build_final_review_prompt(self, agent_summary: str, metadata: Dict[str, Any]) -> str:
        """
        Строит промпт для генерации финальной рецензии
        
        Args:
            agent_summary: Сводка результатов агентов
            metadata: Метаданные статьи
            
        Returns:
            str: Промпт для LLM
        """
        title = metadata.get("title", "Научная статья")
        
        prompt = f"""
        На основе анализа научной статьи "{title}" различными специализированными агентами, 
        создай структурированную рецензию.

        Результаты анализа:
        {agent_summary}

        Создай профессиональную рецензию, включающую:
        1. Общую оценку работы (1-2 предложения)
        2. Сильные стороны (2-3 пункта)
        3. Слабые стороны и проблемы (2-3 пункта)
        4. Конкретные рекомендации по улучшению (2-3 пункта)

        Рецензия должна быть конструктивной, профессиональной и написана на русском языке.
        """
        
        return prompt
    
    async def _call_llm_for_review(self, prompt: str) -> str:
        """
        Вызывает LLM для генерации финальной рецензии
        
        Args:
            prompt: Промпт для LLM
            
        Returns:
            str: Сгенерированная рецензия
        """
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
                    "num_predict": 1000
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error calling LLM for final review: {e}")
            raise e
    
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
            test_response = await self._call_llm_for_review("Test message")
            health_status["llm"] = "ok"
        except Exception as e:
            health_status["llm"] = f"error: {e}"
        
        return health_status 