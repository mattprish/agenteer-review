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
        
        # Оптимизированный системный промпт для финальной рецензии на русском
        self.system_prompt = """
        You are an academic paper review coordinator. Create a comprehensive review in English for Telegram bot users.
        
        Structure your review as:
        1. Overall assessment (1-2 sentences)
        2. Strengths (2-3 bullet points)  
        3. Weaknesses (2-3 bullet points)
        4. Recommendations (2-3 actionable items)
        
        Write the entire review. Be constructive and professional.
        """
    
    def register_agent(self, name: str, agent: BaseAgent):
        """Регистрирует агента в системе"""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    async def process_paper(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Основной метод обработки статьи с максимальной оптимизацией"""
        logger.info("Starting optimized paper processing")
        
        try:
            # Проверяем входные данные
            if not text or not text.strip():
                raise ValueError("Текст статьи не может быть пустым")
            
            logger.info(f"Processing text of length: {len(text)} chars")
            
            # Оптимизация: передаем пустые метаданные всем агентам (не используются)
            empty_metadata = {}
            
            # 1. Запуск всех агентов параллельно с агрессивными таймаутами
            agent_results = await self._run_agents_parallel(text, empty_metadata)
            logger.info(f"Agent analysis completed")
            
            # 2. Быстрая генерация финального отчета на русском
            final_review = await self._generate_final_review(agent_results)
            logger.info(f"Final review generated")
            
            # 3. Минимальный результат
            result = {
                "agent_results": agent_results,
                "final_review": final_review,
                "processing_status": "success"
            }
            
            # Включаем метаданные только если переданы
            if metadata:
                result["metadata"] = metadata
            
            logger.info("Paper processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in paper processing: {e}", exc_info=True)
            return {
                "agent_results": {},
                "final_review": f"Ошибка при обработке статьи: {str(e)}",
                "processing_status": "error",
                "error": str(e)
            }
    
    async def _run_agents_parallel(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает всех агентов параллельно с агрессивными таймаутами"""
        logger.info(f"Running {len(self.agents)} agents in parallel")
        
        if not self.agents:
            logger.warning("No agents registered")
            return {}
        
        # Создаем задачи для всех агентов одновременно
        tasks = []
        agent_names = []
        
        for name, agent in self.agents.items():
            task = asyncio.create_task(
                self._run_single_agent(agent, text, metadata, name)
            )
            tasks.append(task)
            agent_names.append(name)
        
        # Агрессивные таймауты для максимальной скорости
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=90.0  # 1.5 минуты максимум на все агенты
            )
        except asyncio.TimeoutError:
            logger.error("Agent processing timeout")
            return {"error": "Превышено время ожидания анализа"}
        
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
                if isinstance(result, dict):
                    agent_results[name] = result
                    agent_results[name]["status"] = "success"
                else:
                    agent_results[name] = {
                        "result": result,
                        "status": "success"
                    }
        
        logger.info(f"Completed {len(agent_results)} agent tasks")
        return agent_results
    
    async def _run_single_agent(self, agent: BaseAgent, text: str, metadata: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """Запускает отдельного агента с агрессивным таймаутом"""
        try:
            logger.info(f"Starting agent: {agent_name}")
            
            # Агрессивный таймаут для каждого агента
            result = await asyncio.wait_for(
                agent.analyze(text, metadata),
                timeout=45.0  # 45 секунд на агента
            )
            
            logger.info(f"Agent {agent_name} completed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Agent {agent_name} timeout")
            raise Exception(f"Агент {agent_name} превысил время ожидания")
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            raise e
    
    async def _generate_final_review(self, agent_results: Dict[str, Any]) -> str:
        """Генерирует финальную рецензию на русском языке"""
        logger.info("Generating final review")
        
        try:
            # Быстрая подготовка сводки на английском для LLM
            summary_data = self._prepare_english_summary(agent_results)
            
            # Компактный промпт для быстрой генерации
            prompt = self._build_review_prompt(summary_data)
            
            # Генерируем рецензию с агрессивными ограничениями
            review = await self._call_llm_for_review(prompt)
            
            return review
            
        except Exception as e:
            logger.error(f"Error generating final review: {e}")
            return f"Ошибка при генерации рецензии: {str(e)}"
    
    def _prepare_english_summary(self, agent_results: Dict[str, Any]) -> str:
        """Быстрая подготовка сводки на английском для LLM"""
        summary_parts = []
        
        for agent_name, result in agent_results.items():
            if result.get("status") == "failed":
                summary_parts.append(f"• {agent_name}: analysis failed")
                continue
            
            if agent_name == "StructureAgent":
                quality = result.get("structure_quality", "unknown")
                completeness = result.get("completeness_score", 0)
                coherence = result.get("coherence_score", 0)
                missing = result.get("missing_sections", [])
                
                summary_parts.append(f"• Structure: {quality} quality")
                summary_parts.append(f"  Completeness: {completeness:.1%}, Coherence: {coherence:.1%}")
                if missing:
                    summary_parts.append(f"  Missing: {', '.join(missing[:3])}")
            
            elif agent_name == "SummaryAgent":
                quality = result.get("summary_quality", "unknown")
                topics = result.get("key_topics", [])
                compression = result.get("compression_ratio", 0)
                
                summary_parts.append(f"• Content: {quality} summary quality")
                summary_parts.append(f"  Compression: {compression:.1%}")
                if topics:
                    summary_parts.append(f"  Key topics: {', '.join(topics[:3])}")
        
        return "\n".join(summary_parts) if summary_parts else "Analysis incomplete"
    
    def _build_review_prompt(self, agent_summary: str) -> str:
        """Компактный промпт для быстрой генерации рецензии на русском"""
        prompt = f"""
        Academic paper analysis results:
        {agent_summary}

        Create a comprehensive review with this structure:

        Overall assessment: (1-2 sentences overall assessment)

        Strengths:
        - strength 1
        - strength 2

        Weaknesses:
        - issue 1
        - issue 2

        Recommendations:
        - recommendation 1
        - recommendation 2

        Write entire review. Be specific and constructive.
        """
        
        return prompt
    
    async def _call_llm_for_review(self, prompt: str) -> str:
        """Оптимизированный вызов LLM для финальной рецензии"""
        try:
            response = await asyncio.wait_for(
                self.client.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    options={
                        "temperature": 0.3,  # Низкая температура для консистентности
                        "top_p": 0.8,
                        "num_predict": 400  # Ограничиваем для скорости
                    }
                ),
                timeout=25.0  # 25 секунд максимум на финальную рецензию
            )
            
            return response['message']['content']
            
        except asyncio.TimeoutError:
            logger.error("LLM timeout for final review")
            return "Превышено время ожидания при генерации рецензии"
        except Exception as e:
            logger.error(f"Error calling LLM for final review: {e}")
            raise e
    
    async def health_check(self) -> Dict[str, Any]:
        """Быстрая проверка работоспособности системы"""
        health_status = {
            "orchestrator": "ok",
            "agents": {},
            "llm": "unknown"
        }
        
        # Быстрая проверка агентов
        for name in self.agents.keys():
            health_status["agents"][name] = "registered"
        
        # Быстрая проверка LLM
        try:
            test_response = await asyncio.wait_for(
                self._call_llm_for_review("Test"),
                timeout=10.0
            )
            health_status["llm"] = "ok"
        except Exception as e:
            health_status["llm"] = f"error: {str(e)[:100]}"
        
        return health_status 