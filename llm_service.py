#!/usr/bin/env python3
"""
LLM сервис для обработки запросов на анализ научных статей
"""

import logging
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
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

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервиса"""
    logger.info("Starting LLM Service...")
    
    # Проверяем доступность Ollama
    try:
        models = await ollama.AsyncClient().list()
        logger.info(f"Available models: {[m['name'] for m in models['models']]}")
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
    
    # Регистрируем агентов в оркестраторе
    try:
        structure_agent = StructureAgent()
        summary_agent = SummaryAgent()
        
        orchestrator.register_agent("StructureAgent", structure_agent)
        orchestrator.register_agent("SummaryAgent", summary_agent)
        
        logger.info("Agents registered successfully")
    except Exception as e:
        logger.error(f"Error registering agents: {e}")

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "llm-service"}

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

@app.post("/extract-pdf")
async def extract_pdf_text(file_content: bytes):
    """
    Извлекает текст из PDF файла
    
    Args:
        file_content: Содержимое PDF файла
        
    Returns:
        Dict: Извлеченный текст и метаданные
    """
    try:
        logger.info("Extracting text from PDF...")
        
        # Временно сохраняем файл для обработки
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Извлекаем текст
            text, metadata = await pdf_extractor.extract_text_and_metadata(temp_file_path)
            
            return {
                "success": True,
                "text": text,
                "metadata": metadata
            }
            
        finally:
            # Удаляем временный файл
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting PDF: {str(e)}"
        )

@app.get("/models")
async def list_models():
    """Возвращает список доступных моделей"""
    try:
        client = ollama.AsyncClient()
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