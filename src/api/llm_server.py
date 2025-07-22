#!/usr/bin/env python3
"""
FastAPI сервер для обработки запросов на анализ научных статей
Взаимодействует только с ollama-сервером на порту 11434
"""

import logging
import asyncio
import tempfile
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import ollama

from core.orchestrator import Orchestrator
from core.pdf_extractor import PDFExtractor
from core.agents.structure_agent import StructureAgent
from core.agents.summary_agent import SummaryAgent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Academic Review LLM Service")

# Инициализируем компоненты
orchestrator = Orchestrator()
pdf_extractor = PDFExtractor()

class ReviewRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

class ReviewResponse(BaseModel):
    success: bool
    results: Dict[str, Any] = {}
    error: str = ""

class PDFUploadResponse(BaseModel):
    success: bool
    text: str = ""
    metadata: Dict[str, Any] = {}
    error: str = ""

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервиса"""
    logger.info("Starting LLM Service...")
    
    # Определяем хост для ollama в зависимости от окружения
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
        
        orchestrator.register_agent("StructureAgent", structure_agent)
        orchestrator.register_agent("SummaryAgent", summary_agent)
        
        logger.info(f"Agents registered successfully with model: {model_name}")
    except Exception as e:
        logger.error(f"Error registering agents: {e}")

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "llm-service"}

@app.post("/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Загружает PDF файл и извлекает из него текст
    
    Args:
        file: PDF файл
        
    Returns:
        PDFUploadResponse: Извлеченный текст и метаданные
    """
    try:
        logger.info(f"Processing PDF file: {file.filename}")
        
        # Читаем содержимое файла
        content = await file.read()
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Извлекаем текст и метаданные
            text, metadata = await pdf_extractor.extract(temp_file_path)
            
            logger.info(f"PDF processed successfully. Text length: {len(text)}")
            
            return PDFUploadResponse(
                success=True,
                text=text,
                metadata=metadata
            )
            
        finally:
            # Удаляем временный файл
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return PDFUploadResponse(
            success=False,
            error=f"Error processing PDF: {str(e)}"
        )

@app.post("/review", response_model=ReviewResponse)
async def review_paper(request: ReviewRequest):
    """
    Анализирует научную статью и возвращает рецензию
    
    Args:
        request: Запрос с текстом статьи и метаданными
        
    Returns:
        ReviewResponse: Результаты анализа
    """
    try:
        logger.info("Processing review request...")
        
        # Обрабатываем статью через оркестратор
        results = await orchestrator.process_paper(
            text=request.text,
            metadata=request.metadata
        )
        
        logger.info("Review completed successfully")
        
        return ReviewResponse(
            success=True,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error processing review: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing review: {str(e)}"
        )

@app.get("/models")
async def list_models():
    """Возвращает список доступных моделей"""
    try:
        # Определяем хост для ollama в зависимости от окружения
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
            ollama_host = "http://ollama:11434"
        else:
            ollama_host = "http://localhost:11434"
            
        client = ollama.AsyncClient(host=ollama_host)
        models = await client.list()
        return {
            "success": True,
            "models": [m['name'] for m in models['models']]
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {
            "success": False,
            "error": str(e),
            "models": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 