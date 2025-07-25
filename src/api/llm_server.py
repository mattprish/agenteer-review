#!/usr/bin/env python3
"""
FastAPI сервер для обработки запросов на анализ научных статей
Взаимодействует только с ollama-сервером на порту 11434
"""
import os
import ollama
import logging
from typing import Dict, Any, List
import asyncio
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from core_v2.agentlib.orchestrator import Orchestrator as Orchestrator_v2
from core_v2.agentlib.base_agent import BaseAgent as BaseAgent_v2

from core.orchestrator import Orchestrator
from core.agents.structure_agent import StructureAgent
from core.agents.summary_agent import SummaryAgent

# --- НАСТРОЙКА: просто меняйте этот флаг для переключения ---
USE_OLLAMA = False  # True — использовать Ollama, False — кастомный url

# Пример ваших промптов для агентов
agents_prompts = {
    "AbstractAgent": """
        Analyze the abstract and introduction of the provided scientific paper. Assess the clarity of the research question, the novelty of the work, and the significance of the stated contributions. Provide a score from 0 to 10 for each of these three aspects (Clarity, Novelty, Significance), where 0 is poor, 4-7 is average, and 8-10 is excellent. Summarize your findings in a short paragraph.
    """,
    "MethodologyAgent": """
        Examine the methodology section of the paper. Evaluate the clarity and completeness of the described methods. Assess whether the experimental setup is sound and if the work appears to be reproducible based on the information provided. Provide a score from 0 to 10 for both Clarity of Methods and Reproducibility, where 0 is poor, 4-7 is average, and 8-10 is excellent. List any identified flaws or areas needing further clarification.
    """,
    "ResultsAgent": """
        Analyze the results and discussion sections. Assess whether the presented results are clearly explained and logically support the paper's main claims. Evaluate the quality of the discussion in interpreting the results and contextualizing them within the broader field. Provide a score from 0 to 10 for both Clarity of Results and Quality of Discussion, where 0 is poor, 4-7 is average, and 8-10 is excellent. Highlight any inconsistencies or unsupported claims.
    """,
    "LanguageAgent": """
        Perform a thorough check of the entire paper for grammatical errors, spelling mistakes, and awkward phrasing. Identify sentences or paragraphs that are unclear due to poor language. Provide a score from 0 to 10 for the overall linguistic quality of the paper, where 0 is poor, 4-7 is average, and 8-10 is excellent. List the most significant grammatical issues found.
    """,
    "CitationAgent": """
        Verify the formatting and consistency of the citations and reference list. Check for any obvious errors in the references, such as missing information or incorrect formatting. Assess whether the references are relevant and up-to-date. Provide a score from 0 to 10 for the quality of citations and referencing, where 0 is poor, 4-7 is average, and 8-10 is excellent.
    """
}

app = FastAPI()
logger = logging.getLogger(__name__)

# --- Pydantic модели запроса/ответа ---
class ReviewRequest(BaseModel):
    text: str

class ReviewResponseNew(BaseModel):
    success: bool
    results: str


class ReviewResponseOld(BaseModel):
    success: bool
    results: Dict[str, Any] = {}
    error: str = ""

ReviewResponce = ReviewResponseOld

async def ollama_start():
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        ollama_host = "http://ollama:11434"
    else:
        ollama_host = "http://localhost:11434"
    
    # Проверяем доступность Ollama
    try:
        client = ollama.AsyncClient(host=ollama_host)
        models = await client.list()
        logger.info(f"Available models: {[m['name'] for m in models['models']]}")
        logger.info(f"Using ollama host: {ollama_host}")
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
    
    # Регистрируем агентов в оркестраторе
    try:
        # Инициализируем агентов с одной моделью для консистентности
        model_name = "qwen3:4b"
        structure_agent = StructureAgent(model_name=model_name)
        summary_agent = SummaryAgent(model_name=model_name)
        
        app.state.orchestrator = Orchestrator()
        app.state.orchestrator.register_agent("StructureAgent", structure_agent)
        app.state.orchestrator.register_agent("SummaryAgent", summary_agent)
        ReviewResponce = ReviewResponseOld
        logger.info(f"Agents registered successfully with model: {model_name}")
    except Exception as e:
        logger.error(f"Error registering agents: {e}")

async def new_start():
    model_url = "http://84.201.137.113:8000"
    model_name = "Qwen/Qwen3-4B"
    logger.info(f"Using CUSTOM url: {model_url} (model: {model_name})")

    # Инициализация агентов и оркестратора
    agents = [
        BaseAgent_v2("AbstractAgent", model_url, model_name, agents_prompts["AbstractAgent"]),
        BaseAgent_v2("MethodologyAgent", model_url, model_name, agents_prompts["MethodologyAgent"]),
        BaseAgent_v2("ResultsAgent", model_url, model_name, agents_prompts["ResultsAgent"]),
        BaseAgent_v2("LanguageAgent", model_url, model_name, agents_prompts["LanguageAgent"]),
        BaseAgent_v2("CitationAgent", model_url, model_name, agents_prompts["CitationAgent"])
    ]
    ReviewResponce = ReviewResponseNew
    orchestrator = Orchestrator_v2(model_url, model_name, agents)
    app.state.orchestrator = orchestrator

@app.on_event("startup")
async def startup_event():
    """Инициализация агентов и оркестратора"""

    # Выбор URL и модели по флагу
    if USE_OLLAMA:
        await ollama_start()
    else:
        await new_start()

    logger.info("Orchestrator initialized and ready.")

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "llm-service"}

@app.post("/review", response_model=ReviewResponce)
async def review_paper(request: ReviewRequest):
    try:
        orchestrator = app.state.orchestrator
        print(type(request.text))
        results = await orchestrator.run(request.text)
        
        return ReviewResponce(success=True, results=results)
    except Exception as e:
        logger.error(f"Error in review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
