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
    "AbstractAgent": "find abdstract",
    "MethodologyAgent": "print methodology",
    "ResultsAgent": "PROMPT 3",
    "LanguageAgent": "PROMPT 4",
    "CitationAgent": "PROMPT 5",
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
    model_url = "https://70941f5dfbfb.ngrok-free.app"
    model_name = "qwen/qwen3-4b"
    logger.info(f"Using CUSTOM url: {model_url} (model: {model_name})")

    # Инициализация агентов и оркестратора
    agents = [
        BaseAgent_v2("AbstractAgent", model_url, model_name, agents_prompts["AbstractAgent"]),
        # BaseAgent_v2("MethodologyAgent", model_url, model_name, agents_prompts["MethodologyAgent"])
        # BaseAgent_v2("ResultsAgent", model_url, model_name, agents_prompts["ResultsAgent"]),
        # BaseAgent_v2("LanguageAgent", model_url, model_name, agents_prompts["LanguageAgent"]),
        # BaseAgent_v2("CitationAgent", model_url, model_name, agents_prompts["CitationAgent"]),
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
